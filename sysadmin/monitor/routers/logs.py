"""Log Aggregator API endpoints — log viewing, filtering, trends, advice, review."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.auth import require_auth
from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    LogActionsResponse,
    LogReviewResponse,
    LogsResponse,
    LogStatsResponse,
    LogTrendsResponse,
)
from sysadmin.core.database import get_db_session
from sysadmin.monitor import log_review as log_review_module
from sysadmin.monitor.log_actions import recommend
from sysadmin.monitor.log_query import (
    build_trend_report,
    declared_source_names,
    log_source_scopes,
    unit_relations,
)
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.log_review import LogReview

router = APIRouter(prefix="/api/logs", tags=["logs"])


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
    report = await build_trend_report(session, days)
    return _serialise_report(report)


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
    report = await build_trend_report(session, days)
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
                "members": [
                    {
                        "source": m.source,
                        "signature": m.signature,
                        "alert_title": m.alert_title,
                        "occurrences": m.occurrences,
                    }
                    for m in r.members
                ],
            }
            for r in recommend(
                report, declared, log_source_scopes(), unit_relations()
            )
        ],
        "confidence": str(report.confidence),
        "window_days": report.window_days,
        "generated_at": report.generated_at.isoformat(),
        "declared_noise": len(declared),
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
            "runs_instrumented": report.coverage.runs_instrumented,
            "truncated_fraction": round(report.coverage.truncated_fraction, 4),
            "fraction": round(report.coverage.fraction, 3),
        },
        "truncated": report.truncated,
        "groups_read": report.groups_read,
    }


def _review_payload(review: LogReview) -> dict:
    return {
        "generated_at": (
            review.generated_at.isoformat() if review.generated_at else None
        ),
        "period_days": review.period_days,
        "narrative": review.narrative,
        "llm_used": review.llm_used,
        "model_used": review.model_used,
        "confidence": review.confidence,
        "stats": review.stats,
    }


@router.get("/review", response_model=LogReviewResponse)
async def get_log_review(session: AsyncSession = Depends(get_db_session)):
    """The latest stored weekly log review (Session 27, Tier 3).

    **Read back rather than computed live**, which is the opposite call
    from its two neighbours on this router and is the right one for the
    opposite reason.  ``/trends`` and ``/actions`` recompute because a
    stored answer would be stale and because the computation is 91 ms.
    A narrative costs a GPU generation measured in minutes, cannot be
    produced inside a request, and is *about* a period rather than about
    now — so it is written weekly and served as written.

    404 is "no review has been generated yet", which is why
    ``log_reviews`` is in ``KEEP_LATEST_PER``: a purge that emptied the
    table would turn "none lately" into "none ever".
    """
    result = await session.execute(
        select(LogReview).order_by(desc(LogReview.generated_at)).limit(1)
    )
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="No log review generated yet")
    return _review_payload(review)


@router.post(
    "/review/generate",
    response_model=LogReviewResponse,
    dependencies=[Depends(require_auth)],
)
async def generate_log_review(session: AsyncSession = Depends(get_db_session)):
    """Generate a log review now.  Authenticated; the LLM is optional.

    Returns 404 when the trend holds no signatures at all — nothing was
    observed, which is not the same as nothing happening and must not be
    served as an empty review.
    """
    review = await log_review_module.generate_review(session)
    if review is None:
        raise HTTPException(status_code=404, detail="No log data to review")
    payload = _review_payload(review)
    await session.commit()
    return payload


#: What a retired single-segment path is told.  Named rather than
#: inlined because both tombstones below say the same thing and a second
#: wording would let them disagree about one fact.
_SUMMARY_GONE = (
    "GET /api/logs/summary and /api/logs/summary/history were removed in "
    "Session 69, and the table behind them, sysadmin.log_summaries, was "
    "dropped by migration 014. The weekly narrative is GET /api/logs/review; "
    "the counts are GET /api/logs/stats."
)


@router.get("/summary", include_in_schema=False)
@router.get("/summary/history", include_in_schema=False)
async def _summary_gone():
    """410 for the two paths Session 69 removed (``SNAG-LOG-011``).

    **Declared above the catch-all, and that ordering is the whole
    mechanism** — FastAPI matches in declaration order, so a tombstone
    below ``/{source}`` would never be reached.

    410 rather than 404 because the two states are different and a
    caller cannot tell them apart otherwise: ``/summary`` *was* a route
    and was deliberately removed, while ``/nonsense`` never was.  That
    is ``ports_checked``'s rule — zero-because-clean must not be served
    as zero-because-blind — one status code up.  Before this existed the
    answer was worse than either: ``200`` with an empty list, the
    catch-all matching ``summary`` as though it were a log source, so a
    caller was told "no summaries" about a schema object that no longer
    exists.

    ``/summary/history`` already 404'd, because the catch-all takes one
    path segment.  It is named here anyway so the pair answers with one
    voice — a client that gets ``410`` from one and ``404`` from the
    other would reasonably conclude the second is a typo.

    Out of the schema deliberately.  The audience is a caller holding a
    stale client, who reads the status code and not ``/docs``; listing a
    dead path in the schema would advertise it to everyone else.  These
    are debt with a date on them — delete both once no stale client can
    exist, which is a judgement about consumers rather than about time.
    """
    raise HTTPException(status_code=410, detail=_SUMMARY_GONE)


@router.get("/{source}")
async def get_logs_by_source(
    source: str,
    hours: int = Query(default=1, le=48),
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """Log entries for one declared source.  404 if it is not one.

    **The validator is what removes the class the tombstones above only
    patch** (``SNAG-LOG-011``).  Without it, any single-segment path
    under ``/api/logs`` that is added and later removed silently
    acquires a ``200`` with an empty list — the route has been last in
    this router since it was written, which is what makes it work at all
    and is exactly why it cannot simply move.  An unknown segment is now
    a 404, so the next removal needs no tombstone to be honest, only to
    be *specific*.

    Two things the validated set is keyed on, both measured rather than
    assumed:

    1. **Units, not source names**, because that is what
       ``log_entries.source`` holds — and for a ``type: file`` source it
       is the name instead, which is why the rule lives in
       :func:`~sysadmin.monitor.services.stored_source_name` beside the
       loop that stamps it.  Passing ``alfred`` used to return an empty
       list; it now 404s and the detail names the units, which is the
       same defect one level down being answered rather than inherited.
    2. **Both configuration files.**  ``kernel`` is declared in
       config.yaml because it belongs to no service, and it is 451,319
       of the 451,569 rows in this table.  A set built from
       services.yaml alone passes every fixture on this box and rejects
       99.9 % of the data.

    The stated cost: a source removed from ``services.yaml`` keeps 30
    days of rows this route will no longer serve.  Empty population
    today — all 9 distinct values in ``log_entries.source`` are declared
    — and the rows stay reachable through
    ``GET /api/logs/recent?source=``, which has no validator because its
    job is history rather than a live source's tail.
    """
    declared = declared_source_names()
    if source not in declared:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Unknown log source {source!r}. "
                f"Declared sources: {', '.join(sorted(declared))}"
            ),
        )

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
