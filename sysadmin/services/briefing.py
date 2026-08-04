"""Morning briefing data generator.

Collects data from all agents and builds the structured briefing payload
that was POSTed to PersonalAssistant at 06:00 daily.

PA was retired on 2026-07-24 (``personal_assistant.enabled: false``), so
the payload is still generated on schedule but the send short-circuits in
:class:`~sysadmin.services.notifier.Notifier`.  Generation is deliberately
left running: it is the part worth reusing if the integration is ever
repointed at a replacement inbox.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import psutil
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.config import get_config
from sysadmin.database import get_scheduler_session
from sysadmin.models.filesystem_audit import FilesystemAudit
from sysadmin.models.log_summary import LogSummary
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.models.service_health import ServiceHealth

logger = logging.getLogger(__name__)


async def generate_briefing_data(session: AsyncSession) -> dict[str, Any]:
    """Generate the full morning briefing payload."""
    now = datetime.now(UTC)

    sections = []

    # 1. Infrastructure status
    infra_section = await _build_infrastructure_section(session)
    if infra_section:
        sections.append(infra_section)

    # 2. Overnight log summary
    log_section = await _build_log_section(session, now)
    if log_section:
        sections.append(log_section)

    # 3. Filesystem status
    fs_section = await _build_filesystem_section(session)
    if fs_section:
        sections.append(fs_section)

    # 4. Project health
    project_section = await _build_project_section(session)
    if project_section:
        sections.append(project_section)

    # 5. Weekly portfolio review, while it is fresh
    review_section = await _build_review_section(session, now)
    if review_section:
        sections.append(review_section)

    return {
        "source": "sysadmin-service",
        "generated_at": now.isoformat(),
        "sections": sections,
    }


async def _build_infrastructure_section(session: AsyncSession) -> dict | None:
    """Build the infrastructure status section from latest health checks."""
    # Get latest status per service
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
        entry = {"name": r.service_name, "status": r.status}
        if r.details:
            note = r.details.get("reason") or r.details.get("error")
            if note:
                entry["note"] = note
        services.append(entry)

    return {
        "title": "Infrastructure Status",
        "type": "status_grid",
        "data": {
            "all_services_healthy": all(s["status"] == "ok" for s in services),
            "services": services,
        },
    }


async def _build_log_section(session: AsyncSession, now: datetime) -> dict | None:
    """Build the overnight log summary section."""
    since = now - timedelta(hours=12)

    query = (
        select(LogSummary)
        .where(LogSummary.created_at >= since)
        .order_by(desc(LogSummary.created_at))
        .limit(1)
    )
    result = await session.execute(query)
    summary = result.scalar_one_or_none()

    if not summary:
        return None

    return {
        "title": "Overnight Log Summary",
        "type": "text",
        "data": summary.summary,
    }


async def _build_filesystem_section(session: AsyncSession) -> dict | None:
    """Build the filesystem section from latest audit."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        return None

    # Disk usage from psutil
    disk_percent = None
    try:
        usage = psutil.disk_usage("/")
        disk_percent = usage.percent
    except OSError:
        pass

    return {
        "title": "Filesystem",
        "type": "metrics",
        "data": {
            "disk_used_percent": disk_percent,
            "reclaimable_mb": audit.total_reclaimable_mb,
            "empty_dirs": audit.empty_dirs_count,
            "stale_project_dirs": audit.stale_project_dirs_count,
            "duplicate_groups": audit.duplicate_groups_count,
        },
    }


async def _build_project_section(session: AsyncSession) -> dict | None:
    """Build the project health table from latest snapshots."""
    # Get latest snapshot per project
    latest_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )

    query = select(ProjectSnapshot).join(
        latest_subq,
        (ProjectSnapshot.project_name == latest_subq.c.project_name)
        & (ProjectSnapshot.scanned_at == latest_subq.c.max_scanned),
    ).order_by(desc(ProjectSnapshot.health_score))
    result = await session.execute(query)
    rows = result.scalars().all()

    if not rows:
        return None

    projects = []
    for r in rows:
        entry = {
            "project": r.project_name,
            "score": r.health_score,
        }
        # Note about issues
        notes = []
        if r.stale_branch_count and r.stale_branch_count > 0:
            notes.append(f"{r.stale_branch_count} stale branches")
        if r.todo_count and r.todo_count > 20:
            notes.append(f"{r.todo_count} TODOs")
        if notes:
            entry["note"] = ", ".join(notes)
        projects.append(entry)

    return {
        "title": "Project Health",
        "type": "table",
        "data": projects,
    }


async def _build_review_section(
    session: AsyncSession, now: datetime
) -> dict | None:
    """Latest weekly portfolio review, if it is under 8 days old.

    8 rather than 7 so a briefing generated an hour after the weekly
    review still counts it as fresh across DST shifts and slow starts.
    """
    from sysadmin.models.project_review import ProjectReview

    query = (
        select(ProjectReview)
        .order_by(desc(ProjectReview.generated_at))
        .limit(1)
    )
    result = await session.execute(query)
    review = result.scalars().first()

    if review is None:
        return None
    generated_at = review.generated_at
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=UTC)
    if now - generated_at > timedelta(days=8):
        return None

    return {
        "title": "Weekly Project Review",
        "type": "text",
        "data": review.narrative,
    }


async def send_morning_briefing() -> None:
    """Generate and send the morning briefing to PA. Called by scheduler at 06:00."""
    from sysadmin.services.notifier import Notifier

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
