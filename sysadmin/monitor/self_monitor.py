"""Self-monitoring — is the service still doing its job?

Every agent run is recorded to ``agent_runs`` by ``BaseAgent.run()``. This
module turns that table into a per-agent health picture: last run and its
status, a duration trend, consecutive failures, and whether the agent looks
*stalled* (has silently stopped running).

"Expected next run" is derived from configuration, never hardcoded — the
intervals here mirror exactly what ``main.py`` registers with the scheduler,
so changing ``config.yaml`` changes the stall window too.

Used by:
    - ``GET /api/sysadmin/self`` (the report)
    - ``SysAdminAgent`` (raises an alert for stalled agents)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from sysadmin.core.config import AppConfig, SelfMonitorConfig
from sysadmin.core.models.agent_run import AgentRun

#: Agent identifiers, matching the ``chk_alert_agent`` DB constraint.
#:
#: **This is not the set of agents this daemon runs**, and stopped being
#: it on 2026-08-13 when ``project_organiser`` moved to the estate's 8400
#: service (ADR-0005). The two answer different questions:
#:
#: - ``AGENT_NAMES`` — agents the ``alerts`` table admits, *ever*. The
#:   constraint is add-only and historical rows carry retired names, so
#:   nothing may be removed from here without a migration that would
#:   orphan them.
#: - :func:`agent_schedules` — agents this daemon schedules *today*.
#:
#: They were identical until that cutover, which is why one name served
#: both. ``tests/test_self_monitor.py`` now asserts containment rather
#: than equality, and ``tests/test_units_api.py`` still pins this tuple
#: to migration 007.
AGENT_NAMES = (
    "sysadmin",
    "project_organiser",
    "file_organiser",
    "log_aggregator",
    "service_discovery",
)

#: Minimum recent runs needed before a duration trend is meaningful.
MIN_TREND_SAMPLES = 4

#: Ratios of recent-half mean vs older-half mean that count as a real change.
TREND_RISING_RATIO = 1.25
TREND_FALLING_RATIO = 0.80

_STATUS_NEVER = "never"


@dataclass(frozen=True)
class AgentSchedule:
    """How an agent is scheduled — read from config, mirrors ``main.py``."""

    name: str
    enabled: bool
    interval_seconds: int
    job_id: str


def agent_schedules(config: AppConfig) -> dict[str, AgentSchedule]:
    """Build each agent's schedule from config.

    Mirrors the ``scheduler.schedule_interval`` calls in ``main.py`` — if a
    job is added or its interval source changes there, change it here too
    (``tests/test_self_monitor.py`` pins the pairing).

    **A subset of :data:`AGENT_NAMES`, not an alias for it.**
    ``project_organiser`` is absent because the agent left this
    repository for the estate's 8400 service on 2026-08-13 (ADR-0005),
    and an entry here would mean the self-monitor watching an agent that
    can never run: a ``project_organiser agent stalled`` row that nothing
    can resolve, escalating to ``critical`` and staying on screen, since
    ``_resolve_recovered`` excludes the stall family by design.

    Removing it rather than relying on ``agents.project_organiser.enabled:
    false`` is deliberate. That flag did hold the fault off — the stall
    test gates on ``schedule.enabled`` — but it made a config line
    load-bearing for a structural fact, and its own comment justified it
    by a reason (double-scanning against ``sysadmin-organiser.timer``)
    that the cutover retired. A config value is the wrong place to record
    "this agent does not exist here".

    The ``agents.project_organiser`` config block survives as recorded
    debt per ADR-0005; nothing in self-monitoring reads it any more.
    """
    agents = config.agents
    return {
        "sysadmin": AgentSchedule(
            name="sysadmin",
            enabled=agents.sysadmin.enabled,
            interval_seconds=agents.sysadmin.health_check_interval_seconds,
            job_id="sysadmin_health_check",
        ),
        "file_organiser": AgentSchedule(
            name="file_organiser",
            enabled=agents.file_organiser.enabled,
            interval_seconds=agents.file_organiser.scan_interval_hours * 3600,
            job_id="file_organiser_scan",
        ),
        "log_aggregator": AgentSchedule(
            name="log_aggregator",
            enabled=agents.log_aggregator.enabled,
            interval_seconds=agents.log_aggregator.poll_interval_seconds,
            job_id="log_aggregator_poll",
        ),
        "service_discovery": AgentSchedule(
            name="service_discovery",
            enabled=agents.service_discovery.enabled,
            interval_seconds=agents.service_discovery.scan_interval_hours * 3600,
            job_id="service_discovery_scan",
        ),
    }


def stall_window_seconds(schedule: AgentSchedule, config: SelfMonitorConfig) -> float:
    """How long the agent may go quiet before it counts as stalled."""
    return max(
        schedule.interval_seconds * config.stall_grace_multiplier,
        float(config.min_stall_grace_seconds),
    )


def _failure_streak(runs: list[AgentRun]) -> tuple[int, str | None]:
    """The run of failures at the head of ``runs``, and what it says.

    Returns ``(count, last_error)`` from **one** walk rather than two.
    The count and the error have to agree about where the streak ends,
    and a second function walking the same list would agree today and
    diverge the first time someone changes how a ``running`` row is
    treated — surfacing as an alert that says "failed 3 runs in a row"
    beside an error text from a different incident.

    In-flight ("running") records are skipped rather than breaking the
    streak: a run that is still going has not failed yet.  They cannot
    supply the error either, so the text comes from the newest run whose
    status is actually ``failed``.

    ``last_error`` is ``str(e)`` as ``BaseAgent.run`` recorded it in
    ``agent_runs.details['error']``, or ``None`` when the streak is
    empty — or when the failure predates Session 41, whose three-
    transaction split is what made a ``failed`` row survive the failure
    it records at all.
    """
    count = 0
    last_error: str | None = None
    for run in runs:
        if run.status == "running":
            continue
        if run.status == "failed":
            count += 1
            if last_error is None:
                error = (run.details or {}).get("error")
                last_error = str(error) if error else None
            continue
        break
    return count, last_error


def _duration_trend(durations: list[float]) -> str:
    """Compare the newer half of the durations against the older half.

    ``durations`` is newest-first. Returns "rising" / "falling" / "steady",
    or "unknown" when there is too little data to say.
    """
    if len(durations) < MIN_TREND_SAMPLES:
        return "unknown"

    half = len(durations) // 2
    recent = mean_or_none(durations[:half])
    older = mean_or_none(durations[half:])
    if recent is None or older is None or older <= 0:
        return "unknown"

    ratio = recent / older
    if ratio >= TREND_RISING_RATIO:
        return "rising"
    if ratio <= TREND_FALLING_RATIO:
        return "falling"
    return "steady"


def mean_or_none(values: list[float]) -> float | None:
    """Mean of a list, or ``None`` when empty."""
    if not values:
        return None
    return sum(values) / len(values)


def summarise_agent(
    schedule: AgentSchedule,
    runs: list[AgentRun],
    config: SelfMonitorConfig,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Build one agent's health entry. ``runs`` must be newest-first.

    Pure function — no DB access, so the stall/trend/failure logic is
    directly unit-testable.

    An agent with *no* recorded runs is reported as ``last_status:
    "never"`` but is **not** flagged as stalled: a fresh install is
    indistinguishable from a stopped agent, and the daily agents would
    otherwise alert on their first day.
    """
    now = now or datetime.now(UTC)
    window = stall_window_seconds(schedule, config)

    durations = [
        float(r.duration_seconds)
        for r in runs
        if r.duration_seconds is not None
    ]

    consecutive_failures, last_error = _failure_streak(runs)

    last = runs[0] if runs else None
    last_run_at = last.started_at if last else None
    if last_run_at is not None and last_run_at.tzinfo is None:
        last_run_at = last_run_at.replace(tzinfo=UTC)

    age_seconds = (now - last_run_at).total_seconds() if last_run_at else None

    stalled = False
    stall_reason: str | None = None
    if schedule.enabled and age_seconds is not None and age_seconds > window:
        stalled = True
        stall_reason = (
            f"no run for {int(age_seconds)}s — expected every "
            f"{schedule.interval_seconds}s (stall window {int(window)}s)"
        )

    return {
        "name": schedule.name,
        "enabled": schedule.enabled,
        "job_id": schedule.job_id,
        "interval_seconds": schedule.interval_seconds,
        "stall_window_seconds": round(window, 1),
        "last_run_at": last_run_at.isoformat() if last_run_at else None,
        "last_status": last.status if last else _STATUS_NEVER,
        "last_run_type": last.run_type if last else None,
        "last_duration_seconds": (
            float(last.duration_seconds)
            if last is not None and last.duration_seconds is not None
            else None
        ),
        "seconds_since_last_run": round(age_seconds, 1) if age_seconds is not None else None,
        "expected_next_run_at": (
            (last_run_at + timedelta(seconds=schedule.interval_seconds)).isoformat()
            if last_run_at
            else None
        ),
        "runs_considered": len(runs),
        "consecutive_failures": consecutive_failures,
        "last_error": last_error,
        "recent_durations": [round(d, 2) for d in durations],
        "mean_duration_seconds": (
            round(m, 2) if (m := mean_or_none(durations)) is not None else None
        ),
        "duration_trend": _duration_trend(durations),
        "stalled": stalled,
        "stall_reason": stall_reason,
    }


async def load_recent_runs(
    session: AsyncSession, limit_per_agent: int
) -> dict[str, list[AgentRun]]:
    """Fetch the most recent runs for every agent, newest-first.

    One query: a ``row_number()`` window partitioned by agent keeps the
    newest N rows per agent, so an agent that stopped running months ago
    still yields its last run (a plain time window would hide it, and a
    plain ``LIMIT`` would let a chatty agent crowd it out).
    """
    ranked = (
        select(
            AgentRun.id,
            func.row_number()
            .over(
                partition_by=AgentRun.agent,
                order_by=AgentRun.started_at.desc(),
            )
            .label("rn"),
        )
        .subquery()
    )

    query = (
        select(AgentRun)
        .join(ranked, AgentRun.id == ranked.c.id)
        .where(ranked.c.rn <= limit_per_agent)
        .order_by(AgentRun.agent, AgentRun.started_at.desc())
    )

    result = await session.execute(query)

    runs_by_agent: dict[str, list[AgentRun]] = {}
    for run in result.scalars().all():
        runs_by_agent.setdefault(run.agent, []).append(run)

    # Defensive: the ORDER BY already sorts newest-first per agent, but the
    # summary logic depends on it, so do not rely on the DB alone.
    for runs in runs_by_agent.values():
        runs.sort(key=lambda r: r.started_at, reverse=True)

    return runs_by_agent


async def build_self_report(
    session: AsyncSession,
    config: AppConfig,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Assemble the ``/api/sysadmin/self`` payload."""
    now = now or datetime.now(UTC)
    self_config = config.self_monitor
    schedules = agent_schedules(config)

    runs_by_agent = await load_recent_runs(session, self_config.recent_runs)

    agents = [
        summarise_agent(schedule, runs_by_agent.get(name, []), self_config, now)
        for name, schedule in schedules.items()
    ]

    stalled = [a for a in agents if a["stalled"]]
    failing = [a for a in agents if a["consecutive_failures"] > 0]

    return {
        "agents": agents,
        "count": len(agents),
        "stalled_count": len(stalled),
        "failing_count": len(failing),
        "healthy": not stalled and not failing,
        "generated_at": now.isoformat(),
    }
