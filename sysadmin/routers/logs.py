"""Log Aggregator API endpoints — log viewing, filtering, summaries."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.database import get_db_session
from sysadmin.models.log_entry import LogEntry
from sysadmin.models.log_summary import LogSummary

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/recent")
async def get_recent_logs(
    hours: int = Query(default=1, le=48),
    source: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """Get recent log entries with optional filters."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    query = (
        select(LogEntry)
        .where(LogEntry.logged_at >= since)
        .order_by(desc(LogEntry.logged_at))
        .limit(limit)
    )

    if source:
        query = query.where(LogEntry.source == source)
    if severity:
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
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

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


@router.get("/stats")
async def get_log_stats(
    hours: int = Query(default=24, le=168),
    session: AsyncSession = Depends(get_db_session),
):
    """Get log statistics — volume and error rates by source."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

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


@router.get("/{source}")
async def get_logs_by_source(
    source: str,
    hours: int = Query(default=1, le=48),
    limit: int = Query(default=100, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """Get log entries for a specific source."""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

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
