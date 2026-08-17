"""Log Aggregator API endpoints — log viewing, filtering, summaries."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    LogActionsResponse,
    LogsResponse,
    LogStatsResponse,
    LogTrendsResponse,
)
from sysadmin.core.database import get_db_session
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.monitor.log_actions import recommend
from sysadmin.monitor.log_trends import (
    MessageGroup,
    WindowCoverage,
    build_report,
)
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.services import get_services, log_sources

router = APIRouter(prefix="/api/logs", tags=["logs"])

#: The severities the trend covers.  Wider than the alert family's
#: ``error``/``critical``, because Tier 2's question is "this *warning*
#: appeared 400x — noise or fault?", and a severity the trend cannot see
#: is a question it cannot answer.
TREND_SEVERITIES = ("warning", "error", "critical")


@router.get("/recent", response_model=LogsResponse)
async def get_recent_logs(
    hours: int = Query(default=1, le=168),
    source: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, le=2000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
):
    """Get recent log entries with optional filters.

    Night Worker uses ``hours=24&severity=all&limit=2000`` for deep analysis.
    Pass ``severity=all`` to explicitly include all severity levels.
    """
    since = datetime.now(UTC) - timedelta(hours=hours)

    query = (
        select(LogEntry)
        .where(LogEntry.logged_at >= since)
        .order_by(desc(LogEntry.logged_at))
        .offset(offset)
        .limit(limit)
    )

    if source:
        query = query.where(LogEntry.source == source)
    if severity and severity != "all":
        query = query.where(LogEntry.severity == severity)

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "entries": [
            {
                "id": str(r.id),
                "source": r.source,
                "severity": r.severity,
                "message": r.message,
                "logged_at": r.logged_at.isoformat() if r.logged_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/errors")
async def get_errors(
    hours: int = Query(default=24, le=168),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    """Get error and critical log entries."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    query = (
        select(LogEntry)
        .where(
            LogEntry.logged_at >= since,
            LogEntry.severity.in_(["error", "critical"]),
        )
        .order_by(desc(LogEntry.logged_at))
        .limit(limit)
    )

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "errors": [
            {
                "id": str(r.id),
                "source": r.source,
                "severity": r.severity,
                "message": r.message,
                "logged_at": r.logged_at.isoformat() if r.logged_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/summary")
async def get_latest_summary(session: AsyncSession = Depends(get_db_session)):
    """Get the latest LLM-generated log summary."""
    query = (
        select(LogSummary)
        .order_by(desc(LogSummary.created_at))
        .limit(1)
    )
    result = await session.execute(query)
    summary = result.scalar_one_or_none()

    if not summary:
        return {"message": "No log summaries yet"}

    return {
        "summary": summary.summary,
        "period_start": summary.period_start.isoformat() if summary.period_start else None,
        "period_end": summary.period_end.isoformat() if summary.period_end else None,
        "model_used": summary.model_used,
        "entry_count": summary.entry_count,
        "error_count": summary.error_count,
        "sources": summary.sources,
        "created_at": summary.created_at.isoformat() if summary.created_at else None,
    }


@router.get("/summary/history")
async def get_summary_history(
    limit: int = Query(default=10, le=50),
    session: AsyncSession = Depends(get_db_session),
):
    """Get past log summaries."""
    query = (
        select(LogSummary)
        .order_by(desc(LogSummary.created_at))
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "summaries": [
            {
                "id": str(r.id),
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "summary": r.summary[:200] + "..." if len(r.summary) > 200 else r.summary,
                "entry_count": r.entry_count,
                "error_count": r.error_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/stats", response_model=LogStatsResponse)
async def get_log_stats(
    hours: int = Query(default=24, le=168),
    session: AsyncSession = Depends(get_db_session),
):
    """Get log statistics — volume and error rates by source."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    # Count by source and severity
    query = (
        select(
            LogEntry.source,
            LogEntry.severity,
            func.count().label("count"),
        )
        .where(LogEntry.logged_at >= since)
        .group_by(LogEntry.source, LogEntry.severity)
        .order_by(LogEntry.source, LogEntry.severity)
    )

    result = await session.execute(query)
    rows = result.all()

    # Reshape into per-source stats
    stats: dict[str, dict[str, int]] = {}
    for source, severity, count in rows:
        if source not in stats:
            stats[source] = {"total": 0}
        stats[source][severity] = count
        stats[source]["total"] += count

    return {
        "period_hours": hours,
        "sources": stats,
    }


@router.get("/trends", response_model=LogTrendsResponse)
async def get_log_trends(
    days: int | None = Query(default=None, ge=1, le=30),
    session: AsyncSession = Depends(get_db_session),
):
    """Week-on-week error trends, keyed on fault signature (Session 27, Tier 1).

    **Computed live, never read back** — ``GET /api/services/reliability``'s
    rule, and it costs about the same: the grouped query measures 91 ms
    over 626,906 rows on this box.  A stored trend would be up to a day
    stale and would 404 before the first run of whatever wrote it.

    Three things about the query are load-bearing, and each is the
    opposite of the shorter version:

    1. **One pass, two conditional aggregates.**  Two window queries can
       each be capped independently, so a signature ranked first this
       week and five-hundredth last week would read its previous count as
       zero — a truncation artefact indistinguishable from a genuinely
       new fault.
    2. **No lower bound on ``logged_at``.**  ``first_seen`` has to span
       *all* retained history, because "new" means a first sighting
       inside the current window and not merely "absent last week"
       (:mod:`sysadmin.monitor.log_trends`, rule 2).  Retention bounds
       the scan at 30 days — which is true again as of ``SNAG-DB-004``,
       fixed the same day as this endpoint was written and for that
       reason: the purge had silently deleted nothing since 2026-08-08,
       so the table was growing without a ceiling underneath a feature
       whose window depends on there being one.
    3. **The grouping is by exact message and the signature is applied in
       Python.**  Normalising in SQL would be a second implementation of
       the identity the alert family is keyed on.  See the module
       docstring for the measurement that makes this affordable.

    The cap's honest limit: groups are taken by total volume, so a very
    quiet new signature could in principle be cut before it is seen.  It
    cannot happen on this box — 44 groups against a cap of 2000 — and
    ``truncated`` says so rather than leaving it to be inferred.
    """
    report = await _build_trend_report(session, days)
    return _serialise_report(report)


async def _build_trend_report(session: AsyncSession, days: int | None):
    """The grouped query and the fold, shared by ``/trends`` and ``/actions``.

    Factored out rather than duplicated because the advice must be
    computed off *the same* report the trend serves — two callers running
    two queries a moment apart could rank a signature as new on one
    surface and established on the other, which is the kind of
    disagreement ``COLLISION_KINDS`` lives in ``ports.py`` to prevent.
    """
    config = get_config().agents.log_aggregator
    window_days = days or config.trend_window_days
    cap = config.trend_max_groups

    now = datetime.now(UTC)
    window_start = now - timedelta(days=window_days)
    previous_start = now - timedelta(days=window_days * 2)

    grouped = await session.execute(
        select(
            LogEntry.source,
            LogEntry.severity,
            LogEntry.message,
            func.count()
            .filter(LogEntry.logged_at >= window_start)
            .label("current"),
            func.count()
            .filter(
                LogEntry.logged_at >= previous_start,
                LogEntry.logged_at < window_start,
            )
            .label("previous"),
            func.count().label("total"),
            func.min(LogEntry.logged_at).label("first_seen"),
            func.max(LogEntry.logged_at).label("last_seen"),
        )
        .where(LogEntry.severity.in_(TREND_SEVERITIES))
        .group_by(LogEntry.source, LogEntry.severity, LogEntry.message)
        .order_by(desc(func.count()))
        # One over the cap, so hitting it is observed rather than assumed
        # from a length that happens to equal the limit.
        .limit(cap + 1)
    )
    rows = grouped.all()
    truncated = len(rows) > cap

    groups = [
        MessageGroup(
            source=r.source,
            severity=r.severity,
            message=r.message,
            current=r.current,
            previous=r.previous,
            total=r.total,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
        )
        for r in rows[:cap]
    ]

    return build_report(
        groups,
        window_days=window_days,
        window_start=window_start,
        previous_start=previous_start,
        generated_at=now,
        coverage=await _trend_coverage(session, previous_start, window_days),
        truncated=truncated,
    )


@router.get("/actions", response_model=LogActionsResponse)
async def get_log_actions(
    days: int | None = Query(default=None, ge=1, le=30),
    session: AsyncSession = Depends(get_db_session),
):
    """Ranked, executable advice off the trend (Session 27, Tier 2).

    The mirror of ``GET /api/units/actions`` and ``GET /api/files/actions``,
    and **GET-only for the reason the unit pair is**: every remedy here is
    either a human reading a journal or an edit to a hand-curated YAML
    file whose ``reason`` field carries the justification.  Neither is
    something a scheduled agent should do on its own — and unlike the
    unit sweep, the edit this one recommends takes effect without a
    restart, so there is no privilege argument for automating it either.

    ``declared_noise`` is served alongside so an empty list can be read.
    Nothing to do and everything already silenced are different states,
    and a bare ``[]`` cannot tell them apart — ``ports_checked``'s rule,
    third outing.
    """
    config = get_config().agents.log_aggregator
    report = await _build_trend_report(session, days)
    declared = {(n.source, n.signature) for n in config.known_noise}

    return {
        "recommendations": [
            {
                "kind": str(r.kind),
                "severity": r.severity,
                "title": r.title,
                "detail": r.detail,
                "action": r.action,
                "source": r.source,
                "signature": r.signature,
                "alert_title": r.alert_title,
                "occurrences": r.occurrences,
                "snippet": r.snippet,
            }
            for r in recommend(report, declared, _log_source_scopes())
        ],
        "confidence": str(report.confidence),
        "window_days": report.window_days,
        "generated_at": report.generated_at.isoformat(),
        "declared_noise": len(declared),
    }


async def _trend_coverage(
    session: AsyncSession, since: datetime, window_days: int
) -> WindowCoverage:
    """How thoroughly the agent polled across both windows.

    ``runs_expected`` is derived from the live poll interval rather than
    written down, so changing the interval moves it without anyone having
    to remember — ``JOB_CONFIG_PATHS``'s rule, one domain over.

    A run counts as truncated when it reported any source at its read
    ceiling.  That is the field that decides confidence, because it is
    the only one that means data was actually lost: a merely missed poll
    is caught up by the journal cursor on the next one.
    """
    agent_config = get_config().agents.log_aggregator
    result = await session.execute(
        select(
            func.count().label("runs"),
            func.count()
            .filter(
                AgentRun.details["truncated_sources"].as_string() != "[]",
            )
            .label("truncated"),
        ).where(
            AgentRun.agent == "log_aggregator",
            AgentRun.started_at >= since,
        )
    )
    row = result.one()
    interval = max(1, agent_config.poll_interval_seconds)
    expected = int(window_days * 2 * 86400 / interval)
    return WindowCoverage(
        runs_observed=row.runs or 0,
        runs_expected=expected,
        runs_truncated=row.truncated or 0,
    )


def _log_source_scopes() -> dict[str, bool]:
    """Unit name -> is it a user unit, from ``services.yaml``.

    Read here rather than in :mod:`sysadmin.monitor.log_actions` so that
    module stays pure.  Keyed on ``unit`` rather than the source's
    ``name``, because ``log_entries.source`` stores the unit — the two
    differ for most entries (``alfred`` vs ``alfred-backend.service``)
    and keying on the wrong one silently yields an empty map, which reads
    as "every source is a system unit".
    """
    return {
        source.unit: bool(source.user)
        for source in log_sources(get_services())
        if source.unit
    }


def _signature_payload(trend) -> dict:
    return {
        "signature": trend.signature,
        "alert_title": trend.alert_title,
        "source": trend.source,
        "severity": trend.severity,
        "sample": trend.sample,
        "current": trend.current,
        "previous": trend.previous,
        "total": trend.total,
        "first_seen": trend.first_seen.isoformat() if trend.first_seen else None,
        "last_seen": trend.last_seen.isoformat() if trend.last_seen else None,
        "change": str(trend.change),
        "ratio": round(trend.ratio, 2) if trend.ratio is not None else None,
    }


def _serialise_report(report) -> dict:
    return {
        "window_days": report.window_days,
        "window_start": report.window_start.isoformat(),
        "previous_start": report.previous_start.isoformat(),
        "generated_at": report.generated_at.isoformat(),
        "confidence": str(report.confidence),
        "signatures": [_signature_payload(t) for t in report.signatures],
        "new_signatures": [
            _signature_payload(t) for t in report.new_signatures
        ],
        "sources": [
            {
                "source": s.source,
                "current_errors": s.current_errors,
                "previous_errors": s.previous_errors,
                "current_warnings": s.current_warnings,
                "previous_warnings": s.previous_warnings,
                "error_delta": s.error_delta,
                "signatures": s.signatures,
                "new_signatures": s.new_signatures,
            }
            for s in report.sources
        ],
        "coverage": {
            "runs_observed": report.coverage.runs_observed,
            "runs_expected": report.coverage.runs_expected,
            "runs_truncated": report.coverage.runs_truncated,
            "fraction": round(report.coverage.fraction, 3),
        },
        "truncated": report.truncated,
        "groups_read": report.groups_read,
    }


@router.get("/{source}")
async def get_logs_by_source(
    source: str,
    hours: int = Query(default=1, le=48),
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """Get log entries for a specific source."""
    since = datetime.now(UTC) - timedelta(hours=hours)

    query = (
        select(LogEntry)
        .where(LogEntry.source == source, LogEntry.logged_at >= since)
        .order_by(desc(LogEntry.logged_at))
        .limit(limit)
    )

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "source": source,
        "entries": [
            {
                "id": str(r.id),
                "severity": r.severity,
                "message": r.message,
                "logged_at": r.logged_at.isoformat() if r.logged_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }
