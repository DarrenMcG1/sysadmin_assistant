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
file-audit agent died three days ago serves a payload one second old
containing three-day-old figures.  ``measured_at`` per source is what
makes that visible, and :func:`summarise` states it in words.

**The project half is gone** (Session 4 cutover, ADR-0005): "Project
Health", "Pick This Up" and "Weekly Project Review" now come from the
estate's own producer (``GET :8400/api/estate/briefing``), which Alfred
pulls separately (its ADR-0070).  This module keeps the machine
sections — Infrastructure, Overnight Logs, Filesystem, Weekly Disk
Review — and the alert digest, so the alerting path never routes
through the estate.
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
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.monitor.services import SKIPPED

logger = logging.getLogger(__name__)

#: Bumped when a key changes meaning or disappears — never for an addition,
#: which by construction cannot break a consumer that ignores unknown keys.
SCHEMA_VERSION = 1

SOURCE = "sysadmin-service"

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


def _period_start(now: datetime) -> datetime:
    """The most recent scheduled briefing boundary at or before ``now``.

    Extracted from :func:`_period` when ``_gather_logs`` began counting
    over the same span the envelope declares.  A second boundary
    computed beside this one is two statements of one fact that can
    disagree, and the disagreement would be invisible: the payload would
    declare a window and carry a count taken over a different one.
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
    return boundary.astimezone(UTC)


def _period(now: datetime) -> dict[str, str]:
    """The span this briefing reports on: since the previous scheduled one.

    ``anchor`` is in the payload because the alternative reading — since
    the previous *pull* — is the one a consumer would otherwise assume,
    and the two differ by however often it happens to poll.
    """
    return {
        "from": _period_start(now).isoformat(),
        "to": now.isoformat(),
        "anchor": "schedule",
    }


# ---------------------------------------------------------------------------
# Gathering — every query in this module lives below this line
# ---------------------------------------------------------------------------


async def _gather(session: AsyncSession, now: datetime) -> dict[str, Any]:
    """Run every query the briefing needs, once each."""
    from sysadmin.files.models.disk_review import DiskReview
    from sysadmin.monitor.models.log_review import LogReview

    return {
        "services": await _gather_services(session),
        "logs": await _gather_logs(session, now),
        "filesystem": await _gather_filesystem(session),
        "alerts": await _gather_alerts(session),
        "disk_review": await _gather_review(session, now, DiskReview),
        "log_review": await _gather_review(session, now, LogReview),
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


async def _gather_logs(session: AsyncSession, now: datetime) -> dict[str, Any]:
    """Overnight error volume, counted live over the briefing's own period.

    **It used to read the newest ``log_summaries`` row**, which was the
    output of ``LogAggregatorAgent.summarise()`` — a method with no
    caller anywhere.  The table has held exactly one row since
    2026-07-24 and the twelve-hour freshness window meant this block was
    absent from every briefing for the twenty-five days before Session
    69, silently: ``_logs_clause`` returns ``None`` for a missing block
    and the summary simply had one sentence fewer.

    Counting here rather than restoring a producer keeps the daily and
    the weekly halves apart, which is the split that makes both honest.
    Volume is a *count* — cheap, exact, and meaningful every morning.
    The narrative is a *weekly* judgement and is the "Weekly Log Review"
    section, generated Monday off a seven-day window; asking a 3B model
    to say something new about one night, six mornings out of seven,
    is prose about nothing.

    The window is the briefing's own period rather than a fixed twelve
    hours, so the count and the ``period`` block in the same payload
    cannot describe different spans.

    **It never returns ``None``, and that is the half that matters.**  A
    count query always yields a row, so the block is always present and
    the section always renders — including at zero.  The old version
    returned ``None`` when no summary row existed, ``_logs_clause``
    returns ``None`` for a missing block, and the summary simply lost a
    sentence: a quiet night and a dead producer rendered *identically*,
    as nothing at all.  That is precisely how twenty-five days of
    absence went unremarked.  ``ports_checked``'s rule — zero because
    clean must never be served as the same answer as zero because
    blind — and here the two are told apart by ``entries``.
    """
    since = _period_start(now)
    result = await session.execute(
        select(
            func.count().label("entries"),
            func.count()
            .filter(LogEntry.severity.in_(("error", "critical")))
            .label("errors"),
            func.count(func.distinct(LogEntry.source)).label("sources"),
        ).where(LogEntry.logged_at >= since)
    )
    row = result.one()
    return {
        "entries": row.entries or 0,
        "errors": row.errors or 0,
        "sources": row.sources or 0,
        # Counted at request time over a declared window, so the honest
        # stamp is now: unlike an audit row, there is no earlier moment
        # at which this was measured.
        "measured_at": _iso(now),
    }


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

    Parametrised on ``model`` from the days it served ``ProjectReview``
    too (that review moved to the estate, ADR-0005); today its one
    caller passes ``DiskReview``, and the freshness rule stays here.
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
        # `skipped` is a declared non-check — a GUI unit bound to
        # graphical-session.target, a service marked `monitor: false` with
        # a reason.  Counting it as failing reports a *decision* as a
        # fault, and names units as "down" that are running.  Four of the
        # estate's 40 live rows are skipped.
        watched = [s for s in items if s["status"] != SKIPPED]
        failing = [s["name"] for s in watched if s["status"] != "ok"]
        facts["services"] = {
            "total": len(watched),
            "healthy": len(watched) - len(failing),
            "failing": failing,
            "unmonitored": len(items) - len(watched),
            "measured_at": services["measured_at"],
        }

    facts["logs"] = dict(gathered["logs"])

    filesystem = gathered["filesystem"]
    if filesystem:
        facts["filesystem"] = dict(filesystem)

    alerts = gathered["alerts"]
    facts["alerts"] = {
        "open": alerts["open"],
        "incidents": alerts["incidents"],
        "shown": alerts["shown"],
        "by_severity": alerts["by_severity"],
    }

    # Reviews sit outside the staleness check on purpose: they are
    # weekly, so "older than 26 hours" is their normal state for six
    # mornings out of seven and flagging it would train the reader to
    # ignore the one line that means something.
    facts["reviews"] = {
        "disk": _iso(getattr(gathered["disk_review"], "generated_at", None)),
        "logs": _iso(getattr(gathered["log_review"], "generated_at", None)),
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
    for name in ("services", "filesystem", "logs"):
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


def _logs_clause(facts: dict[str, Any] | None) -> str | None:
    """Say what the night held — and say when nothing was read at all.

    Three outcomes, not two.  No entries is a statement about the
    *aggregator*, not about the box: a night that produced no log line
    on a machine running fourteen declared sources means the ingest
    stopped, and reporting it as "no errors" is the reassuring version
    of a fault.
    """
    if not facts or facts.get("errors") is None:
        return None
    if not facts.get("entries"):
        return "No log entries were ingested overnight — the aggregator read nothing."
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
                    # A `skipped` row is a declared non-check, not a
                    # failure.  Before this it dragged the flag
                    # permanently false: four units on this estate are
                    # skipped by design, so Alfred's grid could never
                    # read healthy however well the box was running.
                    "all_services_healthy": all(
                        s["status"] in ("ok", SKIPPED) for s in items
                    ),
                    "services": items,
                },
            }
        )

    # Unconditional, unlike every other section here: a count is always
    # available and zero is an answer.  See :func:`_gather_logs`.
    logs = gathered["logs"]
    sections.append(
        {
            "title": "Overnight Logs",
            "type": "metrics",
            "data": {
                "Entries": logs["entries"],
                "Errors": logs["errors"],
                "Sources": logs["sources"],
            },
        }
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

    log_review = gathered["log_review"]
    if log_review is not None:
        sections.append(
            {"title": "Weekly Log Review", "type": "text", "data": log_review.narrative}
        )

    disk_review = gathered["disk_review"]
    if disk_review is not None:
        sections.append(
            {"title": "Weekly Disk Review", "type": "text", "data": disk_review.narrative}
        )

    return sections


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------


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
