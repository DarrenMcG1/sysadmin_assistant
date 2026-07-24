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

from sysadmin.config import AppConfig, SelfMonitorConfig
from sysadmin.models.agent_run import AgentRun

#: Agent identifiers, matching the ``chk_alert_agent`` DB constraint.
AGENT_NAMES = ("sysadmin", "project_organiser", "file_organiser", "log_aggregator")

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
    """
    agents = config.agents
    return {
        "sysadmin": AgentSchedule(
            name="sysadmin",
            enabled=agents.sysadmin.enabled,
            interval_seconds=agents.sysadmin.health_check_interval_seconds,
            job_id="sysadmin_health_check",
        ),
        "project_organiser": AgentSchedule(
            name="project_organiser",
            enabled=agents.project_organiser.enabled,
            interval_seconds=agents.project_organiser.scan_interval_hours * 3600,
            job_id="project_organiser_scan",
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
    }


def stall_window_seconds(schedule: AgentSchedule, config: SelfMonitorConfig) -> float:
    """How long the agent may go quiet before it counts as stalled."""
    return max(
        schedule.interval_seconds * config.stall_grace_multiplier,
        float(config.min_stall_grace_seconds),
    )


def _consecutive_failures(runs: list[AgentRun]) -> int:
    """Count failed runs from the newest backwards, stopping at a success.

    In-flight ("running") records are skipped rather than breaking the
    streak — a run that is still going has not failed yet.
    """
    count = 0
    for run in runs:
        if run.status == "running":
            continue
        if run.status == "failed":
            count += 1
            continue
        break
    return count


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
        "consecutive_failures": _consecutive_failures(runs),
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
