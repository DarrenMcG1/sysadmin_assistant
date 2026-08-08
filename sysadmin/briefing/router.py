"""The digest endpoints built for consumers outside this service.

Both routes join several domains into one payload, which is why they live
above the domains rather than inside one of them. ``/api/sysadmin/status``
would have to reach into project state to answer either, and the monitor
is not allowed to do that.

Paths are unchanged from before the Phase 2 move: ``/api/summary`` is the
single-call digest, and ``/api/sysadmin/briefing/preview`` keeps its
sysadmin-namespaced path because Alfred already pulls it.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.briefing.data import generate_briefing_data
from sysadmin.core.config import get_config
from sysadmin.core.database import get_db_session
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.dnd import dnd_manager
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.projects.models.project_snapshot import ProjectSnapshot

router = APIRouter(prefix="/api", tags=["integration"])


@router.get("/sysadmin/briefing/preview")
async def preview_briefing(session: AsyncSession = Depends(get_db_session)):
    """Preview the morning briefing data without sending it."""
    return await generate_briefing_data(session)


@router.get("/summary")
async def get_summary(session: AsyncSession = Depends(get_db_session)):
    """Single-call digest of system state for PA consumption.

    Returns service health, active alerts, latest resource snapshot
    (including GPU and disk), DND status, and project health scores.
    """
    # --- Services: latest status per configured service ---
    config = get_config()
    configured_names = {s.name for s in config.agents.sysadmin.services}

    svc_subq = (
        select(
            ServiceHealth.service_name,
            func.max(ServiceHealth.checked_at).label("max_checked"),
        )
        .group_by(ServiceHealth.service_name)
        .subquery()
    )
    svc_query = (
        select(ServiceHealth)
        .join(
            svc_subq,
            (ServiceHealth.service_name == svc_subq.c.service_name)
            & (ServiceHealth.checked_at == svc_subq.c.max_checked),
        )
        .where(ServiceHealth.service_name.in_(configured_names))
    )
    svc_result = await session.execute(svc_query)
    svc_rows = svc_result.scalars().all()

    services = []
    all_healthy = True
    for r in svc_rows:
        entry = {
            "name": r.service_name,
            "status": r.status,
            "response_time_ms": r.response_time_ms,
        }
        if r.status != "ok":
            all_healthy = False
        services.append(entry)

    # --- Active alerts ---
    alert_query = (
        select(Alert)
        .where(Alert.resolved.is_(False))
        .order_by(desc(Alert.created_at))
        .limit(20)
    )
    alert_result = await session.execute(alert_query)
    alert_rows = alert_result.scalars().all()

    alerts = [
        {
            "severity": a.severity,
            "title": a.title,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alert_rows
    ]

    # --- Latest resource snapshot ---
    res_query = (
        select(ResourceSnapshot)
        .order_by(desc(ResourceSnapshot.recorded_at))
        .limit(1)
    )
    res_result = await session.execute(res_query)
    snapshot = res_result.scalar_one_or_none()

    resources = None
    if snapshot:
        resources = {
            "cpu_percent": float(snapshot.cpu_percent) if snapshot.cpu_percent else None,
            "ram_percent": float(snapshot.ram_percent) if snapshot.ram_percent else None,
            "disk": snapshot.disk_usage,
            "gpu": snapshot.gpu_usage,
            "load_avg_1m": float(snapshot.load_avg_1m) if snapshot.load_avg_1m else None,
            "recorded_at": snapshot.recorded_at.isoformat() if snapshot.recorded_at else None,
        }

    # --- Project health: latest score per project ---
    proj_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )
    proj_query = (
        select(ProjectSnapshot)
        .join(
            proj_subq,
            (ProjectSnapshot.project_name == proj_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == proj_subq.c.max_scanned),
        )
        .order_by(desc(ProjectSnapshot.health_score))
    )
    proj_result = await session.execute(proj_query)
    proj_rows = proj_result.scalars().all()

    projects = [
        {
            "name": r.project_name,
            "health_score": r.health_score,
            "todo_count": r.todo_count,
            "stale_branches": r.stale_branch_count,
        }
        for r in proj_rows
    ]

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "services": {
            "all_healthy": all_healthy,
            "items": services,
        },
        "alerts": {
            "count": len(alerts),
            "items": alerts,
        },
        "resources": resources,
        "dnd": dnd_manager.get_status(),
        "projects": {
            "count": len(projects),
            "items": projects,
        },
    }
