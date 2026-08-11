"""The morning briefing — its envelope, the facts under it, and the prose over them.

Generated on schedule at 06:00 and, since PA was retired on 2026-07-24,
read by being **pulled**: Alfred fetches
``GET /api/sysadmin/briefing/preview`` when it composes its own digest.
That one word shapes most of what follows.

**The envelope is additive, not a replacement.**  ``sections`` and
``generated_at`` are exactly what they were, because Alfred's
``adapt_sysadmin`` reads both and returns a red error section if either
is missing.  Alfred owns the *section* contract (its ADR-0063 §2 says so,
and normalises every producer into it); this service owns the envelope
around it.  The two are not competing, which is why the spec's phrase
"prose is what Alfred surfaces, ``facts`` is the deterministic input the
prose was written from" resolves cleanly: ``sections`` **are** the prose.
A second envelope-native endpoint was rejected — two payloads where one
gets updated is the drift this repository keeps filing snags about.

There is deliberately **no ``generated`` key beside ``generated_at``**.
Two stamps holding the same value are a fork waiting to happen, and the
existing name is the one a live consumer already reads.

**``facts`` is a projection, not a copy.**  It carries counts and
identifiers, never the full rows the sections render.  A facts block
containing the whole payload cannot be diffed usefully — which is the
entire reason the block exists, since a summary that drifts from its
inputs is only detectable by comparing the two.

**``period`` is anchored to the schedule, never to the last pull.**  Two
consumers polling would each shorten the other's window, and storing a
row per pull turns this endpoint into a pull log.  ``schedules.briefing_hour``
already declares the cadence, so "since the previous briefing" means the
most recent 06:00 boundary — the same span whoever asks, and no storage.

**Every fact carries when it was measured**, which is the one thing the
envelope adds that a consumer cannot compute.  Alfred *does* enforce
staleness — ``_producer_timestamp`` reads ``generated_at`` into
``produced_at`` and its digest flags a 12-hour gap — but that check can
never fire here, because a pulled payload is stamped at the moment it is
answered.  ``generated_at`` says when the phone was picked up; it says
nothing about the age of the data recited into it.  A service whose
organiser timer died three days ago serves a payload one second old
containing three-day-old projects.  ``measured_at`` per source is what
makes that visible, and :func:`summarise` states it in words.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import psutil
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.models.alert import Alert
from sysadmin.core.text import truncate_at_word
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.snapshots import latest_snapshot_query

logger = logging.getLogger(__name__)

#: Bumped when a key changes meaning or disappears — never for an addition,
#: which by construction cannot break a consumer that ignores unknown keys.
SCHEMA_VERSION = 1

SOURCE = "sysadmin-service"

#: How many rows either project table may carry.  Shared by "Project
#: Health" and "Pick This Up" so one payload cannot give two answers to
#: "how much of the estate am I being shown" — half of SNAG-BRIEF-001.
_BOARD_LIMIT = 5

#: The documented cap on a next action.  Documented is the operative word:
#: SNAG-BRIEF-002 was a bare ``[:180]`` slice that the integration guide
#: never mentioned, so a consumer had no way to know a cut had happened.
NEXT_ACTION_CHARS = 180

#: Distinct alert titles carried in the envelope.  The *counts* beside it
#: are exact — see :func:`_gather_alerts`.
_ALERT_LIMIT = 10

#: A review still counts as this week's at 8 days rather than 7, so a
#: briefing generated an hour after the Monday review stays fresh across
#: DST shifts and slow starts.
_REVIEW_FRESH_DAYS = 8


# ---------------------------------------------------------------------------
# The envelope
# ---------------------------------------------------------------------------


async def generate_briefing_data(session: AsyncSession) -> dict[str, Any]:
    """Generate the full morning briefing envelope."""
    now = datetime.now(UTC)

    gathered = await _gather(session, now)
    facts = build_facts(gathered, now)

    return {
        "schema": SCHEMA_VERSION,
        "source": SOURCE,
        "generated_at": now.isoformat(),
        "period": _period(now),
        "summary": summarise(facts),
        "alerts": gathered["alerts"]["items"],
        "facts": facts,
        "sections": render_sections(gathered),
    }


def _period(now: datetime) -> dict[str, str]:
    """The span this briefing reports on: since the previous scheduled one.

    ``anchor`` is in the payload because the alternative reading — since
    the previous *pull* — is the one a consumer would otherwise assume,
    and the two differ by however often it happens to poll.
    """
    schedules = get_config().schedules
    local = now.astimezone()
    boundary = local.replace(
        hour=schedules.briefing_hour,
        minute=schedules.briefing_minute,
        second=0,
        microsecond=0,
    )
    if boundary > local:
        boundary -= timedelta(days=1)

    return {
        "from": boundary.astimezone(UTC).isoformat(),
        "to": now.isoformat(),
        "anchor": "schedule",
    }


# ---------------------------------------------------------------------------
# Gathering — every query in this module lives below this line
# ---------------------------------------------------------------------------


async def _gather(session: AsyncSession, now: datetime) -> dict[str, Any]:
    """Run every query the briefing needs, once each.

    The project snapshots used to be fetched **twice** — "Project Health"
    and "Pick This Up" both issued :func:`latest_snapshot_query`, differing
    only in an ``ORDER BY`` that Python can do for free.  Two reads of the
    same table in one payload is also two chances to disagree.
    """
    from sysadmin.files.models.disk_review import DiskReview
    from sysadmin.projects.models.project_review import ProjectReview

    return {
        "services": await _gather_services(session),
        "logs": await _gather_logs(session, now),
        "filesystem": await _gather_filesystem(session),
        "projects": await _gather_projects(session),
        "alerts": await _gather_alerts(session),
        "project_review": await _gather_review(session, now, ProjectReview),
        "disk_review": await _gather_review(session, now, DiskReview),
    }


async def _gather_services(session: AsyncSession) -> dict[str, Any] | None:
    """Latest health check per service."""
    latest_subq = (
        select(
            ServiceHealth.service_name,
            func.max(ServiceHealth.checked_at).label("max_checked"),
        )
        .group_by(ServiceHealth.service_name)
        .subquery()
    )

    query = select(ServiceHealth).join(
        latest_subq,
        (ServiceHealth.service_name == latest_subq.c.service_name)
        & (ServiceHealth.checked_at == latest_subq.c.max_checked),
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    if not rows:
        return None

    services = []
    for r in rows:
        entry: dict[str, Any] = {"name": r.service_name, "status": r.status}
        if r.details:
            note = r.details.get("reason") or r.details.get("error")
            if note:
                entry["note"] = note
        services.append(entry)

    return {
        "items": services,
        "measured_at": _newest(r.checked_at for r in rows),
    }


async def _gather_logs(session: AsyncSession, now: datetime) -> LogSummary | None:
    """The most recent overnight log summary, if one was written."""
    query = (
        select(LogSummary)
        .where(LogSummary.created_at >= now - timedelta(hours=12))
        .order_by(desc(LogSummary.created_at))
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def _gather_filesystem(session: AsyncSession) -> dict[str, Any] | None:
    """Latest filesystem audit, plus live disk occupancy."""
    query = select(FilesystemAudit).order_by(desc(FilesystemAudit.scanned_at)).limit(1)
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        return None

    # Occupancy is read live rather than from the audit: it is the one
    # figure that moves between scans and the one a reader acts on.
    disk_percent = None
    try:
        disk_percent = psutil.disk_usage("/").percent
    except OSError:
        pass

    return {
        "disk_used_percent": disk_percent,
        "reclaimable_mb": audit.total_reclaimable_mb,
        "empty_dirs": audit.empty_dirs_count,
        "stale_project_dirs": audit.stale_project_dirs_count,
        "duplicate_groups": audit.duplicate_groups_count,
        "measured_at": _iso(audit.scanned_at),
    }


async def _gather_projects(session: AsyncSession) -> dict[str, Any]:
    """Latest snapshot per project, filtered to what is actually on this box.

    **The status filter is the fix for SNAG-BRIEF-001.**  "Project Health"
    published every project ever scanned — 26 rows including
    ``PersonalAssistant``, retired 2026-07-24, and four near-duplicate
    casings of the same work — while "Pick This Up" in the same payload
    listed 5 and ``GET /api/projects/board`` returned 6.  One payload,
    three answers to "what is on this box".

    ``status == "active"`` rather than ``ACTIVELY_SCORED``: the board and
    ``/api/projects/next`` both draw the line there, and the whole defect
    was two sections in one document disagreeing.  Declaring a project
    dormant is supposed to suppress it everywhere at once — that is the
    highest-leverage line in the monitorable-project contract, and it
    held everywhere except the one section a human reads each morning.
    """
    from sysadmin.projects.recommendations import STALLED_HANDOFF_DAYS

    result = await session.execute(latest_snapshot_query())
    rows = [r for r in result.scalars().all() if _status_of(r) == "active"]

    return {
        "health": _project_health_rows(rows),
        "actions": _next_action_rows(rows, STALLED_HANDOFF_DAYS),
        "scored": len(rows),
        "measured_at": _newest(r.scanned_at for r in rows),
    }


async def _gather_alerts(session: AsyncSession) -> dict[str, Any]:
    """Open alerts, grouped by incident rather than listed by row.

    The same rule the desktop notifier learned the hard way: this table
    holds one row *per failed check*, so an unresolved
    ``Log error: kernel`` accounts for 547,814 of them.  Listing rows
    would put one incident in the envelope ten times and crowd out nine
    others.

    Grouping happens in SQL and the cap in Python, in that order, so the
    counts stay **exact** while the list stays bounded.  Capping in SQL
    would silently make ``open`` mean "open, of the ten I looked at".
    """
    query = (
        select(
            Alert.severity,
            Alert.title,
            func.count().label("occurrences"),
            func.max(Alert.created_at).label("latest"),
        )
        .where(Alert.resolved.is_(False))
        .group_by(Alert.severity, Alert.title)
        .order_by(desc("latest"))
    )
    result = await session.execute(query)
    rows = result.all()

    counts = {"critical": 0, "warning": 0, "info": 0}
    total = 0
    for row in rows:
        total += row.occurrences
        if row.severity in counts:
            counts[row.severity] += row.occurrences

    items = [
        {
            "severity": row.severity,
            "title": row.title,
            "occurrences": row.occurrences,
            "latest": _iso(row.latest),
        }
        for row in rows[:_ALERT_LIMIT]
    ]

    return {
        "items": items,
        "open": total,
        "incidents": len(rows),
        "shown": len(items),
        "by_severity": counts,
    }


async def _gather_review(session: AsyncSession, now: datetime, model: Any) -> Any | None:
    """The latest review of one kind, if it is still this week's.

    ``model`` is ``ProjectReview`` or ``DiskReview`` — separate tables
    with identical shapes, so the freshness rule lives here once rather
    than being copied per review kind.
    """
    query = select(model).order_by(desc(model.generated_at)).limit(1)
    result = await session.execute(query)
    review = result.scalars().first()

    if review is None:
        return None
    if now - _aware(review.generated_at) > timedelta(days=_REVIEW_FRESH_DAYS):
        return None
    return review


# ---------------------------------------------------------------------------
# Project rows — shared by the facts block and the two project sections
# ---------------------------------------------------------------------------


def _project_health_rows(rows: list[ProjectSnapshot]) -> list[dict[str, Any]]:
    """Health rows, **worst first** and capped.

    Ascending by score is the other half of SNAG-BRIEF-001's fix: sorting
    by score descending — as it did — puts the 100s at the top, so a cap
    would have shown exactly the rows carrying no information.  A briefing
    is read for what needs attention.
    """
    entries = []
    for r in rows:
        entry: dict[str, Any] = {"project": r.project_name, "score": r.health_score}
        notes = []
        if r.stale_branch_count and r.stale_branch_count > 0:
            notes.append(f"{r.stale_branch_count} stale branches")
        if r.todo_count and r.todo_count > 20:
            notes.append(f"{r.todo_count} TODOs")
        if notes:
            entry["note"] = ", ".join(notes)
        entries.append(entry)

    entries.sort(key=lambda e: (e["score"] if e["score"] is not None else 0, e["project"]))
    return entries[:_BOARD_LIMIT]


def _next_action_rows(rows: list[ProjectSnapshot], stalled_days: int) -> list[dict[str, Any]]:
    """One next action per active project, ranked by how long it has sat.

    Deliberately **not** a list of everything outstanding.  The health
    table already reports 400 TODOs across the portfolio, and a longer
    list is more to avoid rather than less.

    Projects with no next action are omitted entirely — a row saying
    "nothing recorded" is noise in a document whose whole job is to be
    short.  Stalled entries are marked rather than dropped, because
    "decide whether to park this" is itself the action.
    """
    ranked: list[tuple[int, dict[str, Any]]] = []
    for r in rows:
        findings = r.findings or {}
        roadmap = findings.get("roadmap") or {}
        action = roadmap.get("next_action")
        source = roadmap.get("next_action_source")
        if not action and findings.get("last_commit_subject"):
            action, source = str(findings["last_commit_subject"]), "git"
        if not action:
            continue

        age = roadmap.get("handoff_age_days")
        entry: dict[str, Any] = {
            "project": r.project_name,
            "next": truncate_at_word(str(action), NEXT_ACTION_CHARS),
            "source": source,
        }
        if isinstance(age, int) and age > stalled_days:
            entry["note"] = f"stalled {age} days — resume or park"
        ranked.append((age if isinstance(age, int) else -1, entry))

    ranked.sort(key=lambda pair: -pair[0])
    return [entry for _, entry in ranked[:_BOARD_LIMIT]]


# ---------------------------------------------------------------------------
# The facts block
# ---------------------------------------------------------------------------


def build_facts(gathered: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Counts and identifiers, small enough that two briefings can be diffed.

    Everything here is derived from what the sections render, never
    measured separately — a facts block computed by its own queries would
    be a second producer able to disagree with the first.
    """
    facts: dict[str, Any] = {}

    services = gathered["services"]
    if services:
        items = services["items"]
        failing = [s["name"] for s in items if s["status"] != "ok"]
        facts["services"] = {
            "total": len(items),
            "healthy": len(items) - len(failing),
            "failing": failing,
            "measured_at": services["measured_at"],
        }

    logs = gathered["logs"]
    if logs is not None:
        facts["logs"] = {
            "entries": logs.entry_count,
            "errors": logs.error_count,
            "sources": len(logs.sources or []),
            "measured_at": _iso(logs.created_at),
        }

    filesystem = gathered["filesystem"]
    if filesystem:
        facts["filesystem"] = dict(filesystem)

    projects = gathered["projects"]
    if projects["scored"]:
        health = projects["health"]
        threshold = get_config().agents.project_organiser.grade_bands.needs_attention_min
        below = [e for e in health if (e["score"] or 0) < threshold]
        actions = projects["actions"]
        facts["projects"] = {
            "active": projects["scored"],
            "shown": len(health),
            "omitted": max(0, projects["scored"] - len(health)),
            "below_threshold": len(below),
            "threshold": threshold,
            "lowest": health[0] if health else None,
            "actions_outstanding": len(actions),
            "actions_stalled": sum(1 for e in actions if "note" in e),
            "measured_at": projects["measured_at"],
        }

    alerts = gathered["alerts"]
    facts["alerts"] = {
        "open": alerts["open"],
        "incidents": alerts["incidents"],
        "shown": alerts["shown"],
        "by_severity": alerts["by_severity"],
    }

    facts["reviews"] = {
        "project": _iso(getattr(gathered["project_review"], "generated_at", None)),
        "disk": _iso(getattr(gathered["disk_review"], "generated_at", None)),
    }

    facts["stale_sources"] = _stale_sources(facts, now)
    return facts


#: How far behind a source may fall before the summary says so.  A day,
#: because the organiser and the file audit both run daily — anything
#: inside that is the normal gap between a scan and the briefing after it.
_STALE_AFTER = timedelta(hours=26)


def _stale_sources(facts: dict[str, Any], now: datetime) -> list[str]:
    """Which facts were measured too long ago to be called current.

    This is the check Alfred cannot make.  Its staleness rule reads
    ``generated_at``, which on a pulled payload is always seconds old
    however dead the agent behind it is.
    """
    stale = []
    for name in ("services", "filesystem", "projects", "logs"):
        block = facts.get(name)
        measured = block.get("measured_at") if isinstance(block, dict) else None
        if not measured:
            continue
        if now - datetime.fromisoformat(measured) > _STALE_AFTER:
            stale.append(name)
    return stale


# ---------------------------------------------------------------------------
# The prose
# ---------------------------------------------------------------------------


def summarise(facts: dict[str, Any]) -> str:
    """One paragraph, assembled from :func:`build_facts` and nothing else.

    Deterministic on purpose.  The two weekly reviews are LLM-narrated
    and pay for it with a figure-free prompt, a deterministic facts
    prepend and a markdown stripper, because the model restates numbers
    it was told not to and invents quotients it was never given.  A
    summary that is *only* numbers has nothing to gain from that and a
    06:00 path has plenty to lose: llama-server being down would take the
    briefing with it.

    Every clause is skipped rather than filled when its facts are absent,
    so a briefing generated before the first scan says less rather than
    saying zero.
    """
    clauses = [
        _services_clause(facts.get("services")),
        _alerts_clause(facts.get("alerts")),
        _filesystem_clause(facts.get("filesystem")),
        _projects_clause(facts.get("projects")),
        _logs_clause(facts.get("logs")),
        _staleness_clause(facts.get("stale_sources")),
    ]
    said = [c for c in clauses if c]
    if not said:
        return "Nothing has been measured yet — no agent has completed a run."
    return " ".join(said)


def _services_clause(facts: dict[str, Any] | None) -> str | None:
    if not facts:
        return None
    failing = facts["failing"]
    if not failing:
        return f"All {facts['total']} services healthy."
    named = ", ".join(failing[:3])
    if len(failing) > 3:
        named += f" and {len(failing) - 3} more"
    return f"{facts['healthy']} of {facts['total']} services healthy; {named} down."


def _alerts_clause(facts: dict[str, Any] | None) -> str | None:
    if not facts or not facts["incidents"]:
        return None
    by_severity = facts["by_severity"]
    # Incidents, not rows: "4 open alerts" beside 547,814 rows would be a
    # lie in one direction and unreadable in the other.
    parts = [
        f"{by_severity[level]} {level}"
        for level in ("critical", "warning", "info")
        if by_severity[level]
    ]
    incidents = facts["incidents"]
    noun = "incident" if incidents == 1 else "incidents"
    return f"{incidents} open alert {noun} ({', '.join(parts)} rows)."


def _filesystem_clause(facts: dict[str, Any] | None) -> str | None:
    if not facts:
        return None
    parts = []
    if facts.get("disk_used_percent") is not None:
        parts.append(f"Disk at {facts['disk_used_percent']:.0f}%")
    if facts.get("reclaimable_mb"):
        parts.append(f"{facts['reclaimable_mb']} MB reclaimable")
    if not parts:
        return None
    return f"{', '.join(parts)}."


def _projects_clause(facts: dict[str, Any] | None) -> str | None:
    if not facts:
        return None
    parts = [f"{facts['active']} active projects"]
    if facts["below_threshold"]:
        parts.append(f"{facts['below_threshold']} below {facts['threshold']}")
    if facts["omitted"]:
        parts.append(f"showing the {facts['shown']} lowest")
    sentence = f"{', '.join(parts)}."

    if facts["actions_outstanding"]:
        stalled = facts["actions_stalled"]
        tail = f"{facts['actions_outstanding']} next actions outstanding"
        if stalled:
            tail += f", {stalled} stalled"
        sentence += f" {tail}."
    return sentence


def _logs_clause(facts: dict[str, Any] | None) -> str | None:
    if not facts or facts.get("errors") is None:
        return None
    errors = facts["errors"]
    if not errors:
        return "No errors in the overnight logs."
    noun = "error" if errors == 1 else "errors"
    return f"{errors} {noun} in the overnight logs."


def _staleness_clause(stale: list[str] | None) -> str | None:
    """The clause that exists because ``generated_at`` cannot say this."""
    if not stale:
        return None
    named = ", ".join(sorted(stale))
    verb = "is" if len(stale) == 1 else "are"
    return f"Note: {named} {verb} over a day old — the agent behind it may have stopped."


# ---------------------------------------------------------------------------
# The sections — Alfred's contract, unchanged
# ---------------------------------------------------------------------------


def render_sections(gathered: dict[str, Any]) -> list[dict[str, Any]]:
    """Alfred's four section types, in the order it renders them.

    Shapes are frozen by ``adapt_sysadmin``: a section is
    ``{title, type, data}`` and ``type`` is one of
    ``status_grid | text | metrics | table``.  Sections with nothing to
    say are **omitted rather than emitted empty** — the producer-side
    half of the rule Alfred documents, and it does not conflict with
    Alfred's always-emit rule, which binds Alfred to its own planned
    sections rather than to ours.
    """
    sections: list[dict[str, Any]] = []

    services = gathered["services"]
    if services:
        items = services["items"]
        sections.append(
            {
                "title": "Infrastructure Status",
                "type": "status_grid",
                "data": {
                    "all_services_healthy": all(s["status"] == "ok" for s in items),
                    "services": items,
                },
            }
        )

    logs = gathered["logs"]
    if logs is not None:
        sections.append(
            {"title": "Overnight Log Summary", "type": "text", "data": logs.summary}
        )

    filesystem = gathered["filesystem"]
    if filesystem:
        sections.append(
            {
                "title": "Filesystem",
                "type": "metrics",
                "data": {
                    key: value
                    for key, value in filesystem.items()
                    if key != "measured_at"
                },
            }
        )

    projects = gathered["projects"]
    if projects["health"]:
        sections.append(
            {"title": "Project Health", "type": "table", "data": projects["health"]}
        )
    if projects["actions"]:
        sections.append(
            {"title": "Pick This Up", "type": "table", "data": projects["actions"]}
        )

    for review, title in (
        (gathered["project_review"], "Weekly Project Review"),
        (gathered["disk_review"], "Weekly Disk Review"),
    ):
        if review is not None:
            sections.append({"title": title, "type": "text", "data": review.narrative})

    return sections


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


def _status_of(row: ProjectSnapshot) -> str:
    findings = row.findings or {}
    return str(findings.get("status", "active"))


def _aware(stamp: datetime) -> datetime:
    """A naive stamp out of the database is UTC — it was written as UTC."""
    return stamp if stamp.tzinfo is not None else stamp.replace(tzinfo=UTC)


def _iso(stamp: datetime | None) -> str | None:
    return _aware(stamp).isoformat() if stamp is not None else None


def _newest(stamps: Any) -> str | None:
    present = [_aware(s) for s in stamps if s is not None]
    return max(present).isoformat() if present else None


# ---------------------------------------------------------------------------
# The scheduled send (dormant)
# ---------------------------------------------------------------------------


async def send_morning_briefing() -> None:
    """Generate and send the morning briefing to PA. Called by scheduler at 06:00.

    PA was retired on 2026-07-24 and Alfred exposes no inbox, so the send
    short-circuits in :class:`~sysadmin.monitor.notifier.Notifier`.
    Generation is left running deliberately: it is the part worth reusing
    if the integration is ever repointed, and it is what
    ``/api/sysadmin/briefing/preview`` serves on the pull path Alfred
    actually uses.
    """
    from sysadmin.monitor.notifier import Notifier

    async with get_scheduler_session() as session:
        briefing = await generate_briefing_data(session)

    notifier = Notifier()
    await notifier.startup()
    try:
        success = await notifier.send_briefing_data(briefing["sections"])
        if success:
            logger.info("morning_briefing_sent")
        elif not get_config().personal_assistant.enabled:
            # PA retired — a suppressed send is the expected steady state,
            # so it must not look like a daily delivery failure.
            logger.debug("morning_briefing_skipped: PA integration disabled")
        else:
            logger.warning("morning_briefing_delivery_failed")
    finally:
        await notifier.shutdown()
