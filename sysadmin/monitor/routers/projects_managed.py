"""The one project-prefixed route that stayed behind.

Relocated at the Session 4 cutover (ADR-0005): every other
``/api/projects/*`` route moved with the scanner to the estate's 8400
service, but ``/managed`` is service-health substance — the monitor's
data, joined to registry identity the shared library now supplies — so
it lives with the monitor and keeps its path. The tray keeps its URL.
"""

from typing import Any

from estate.registry import load_registry
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.contracts import ManagedProjectsResponse
from sysadmin.core.database import get_db_session
from sysadmin.monitor.models.service_health import ServiceHealth, is_fault
from sysadmin.monitor.services import get_services

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/managed", response_model=ManagedProjectsResponse)
async def get_managed_projects(session: AsyncSession = Depends(get_db_session)):
    """List projects from the registry with live service health status."""
    config = get_config()
    registry = load_registry(config.agents.project_organiser.projects_root)

    # Fetch latest health check per service
    latest_health_subq = (
        select(
            ServiceHealth.service_name,
            func.max(ServiceHealth.checked_at).label("max_checked"),
        )
        .group_by(ServiceHealth.service_name)
        .subquery()
    )
    health_query = (
        select(ServiceHealth)
        .join(
            latest_health_subq,
            (ServiceHealth.service_name == latest_health_subq.c.service_name)
            & (ServiceHealth.checked_at == latest_health_subq.c.max_checked),
        )
    )
    result = await session.execute(health_query)
    health_map = {r.service_name: r for r in result.scalars().all()}

    # Services come from services.yaml, resolved by project id. projects.yaml
    # used to generate them from its own backend/frontend blocks, which is
    # why it could only ever report two per project — Alfred has four.
    declared = get_services()

    projects_out = []
    for mp in registry.declared:
        svc_entries = declared.for_project(mp.id)
        services = []
        all_healthy = True
        for svc in svc_entries:
            h = health_map.get(svc.name)
            entry: dict[str, Any] = {"name": svc.name, "status": h.status if h else "unknown"}
            if h and h.response_time_ms is not None:
                entry["response_time_ms"] = h.response_time_ms
            services.append(entry)
            # Two different absences, and only one of them is a fault.
            # A ``skipped`` row is a *recorded decision* not to look, so
            # it cannot make a project unhealthy — ``!= "ok"`` said it
            # could, and this route reported ``venture-assistant`` and
            # ``sysadmin_assistant`` unhealthy with every real service
            # ``ok`` (``SNAG-API-004``; unlike its two siblings this one
            # was never masked, it was simply wrong on the page).  A
            # *missing* row is the other case and stays unhealthy on
            # purpose: nobody declared anything, so there is no evidence
            # to claim health from.  Empty population today — every
            # managed service has a row.
            if h is None or is_fault(h.status):
                all_healthy = False

        projects_out.append({
            "name": mp.name,
            "path": str(mp.path),
            "services": services,
            # Health scores moved with the scanner to the 8400 service;
            # the contract's optional project_health block is simply no
            # longer populated here (ADR-0005).
            "project_health": None,
            "all_services_healthy": all_healthy if services else None,
        })

    return {"projects": projects_out, "count": len(projects_out)}
