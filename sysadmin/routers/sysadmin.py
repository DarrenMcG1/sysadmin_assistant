"""SysAdmin API endpoints — service status, resources, alerts, ports."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.agents.sysadmin_agent import SysAdminAgent
from sysadmin.auth import require_auth
from sysadmin.config import get_config
from sysadmin.contracts import (
    AlertAckResponse,
    AlertsResponse,
    DndStatusResponse,
    ResourceHistoryResponse,
    ServiceActionResponse,
    StatusResponse,
)
from sysadmin.database import get_db_session
from sysadmin.models.alert import Alert
from sysadmin.models.resource_snapshot import ResourceSnapshot
from sysadmin.models.service_health import ServiceHealth
from sysadmin.services.briefing import generate_briefing_data
from sysadmin.services.dnd import dnd_manager
from sysadmin.utils.systemd import get_unit_status, restart_unit, start_unit, stop_unit

router = APIRouter(prefix="/api/sysadmin", tags=["sysadmin"])


@router.get("/status", response_model=StatusResponse)
async def get_all_statuses(session: AsyncSession = Depends(get_db_session)):
    """Get the latest health status for all monitored services."""
    # Subquery: latest checked_at per service
    latest_subq = (
        select(
            ServiceHealth.service_name,
            func.max(ServiceHealth.checked_at).label("max_checked"),
        )
        .group_by(ServiceHealth.service_name)
        .subquery()
    )

    # Filter to currently-configured services only (excludes stale DB records)
    config = get_config()
    configured_names = {s.name for s in config.agents.sysadmin.services}

    query = (
        select(ServiceHealth)
        .join(
            latest_subq,
            (ServiceHealth.service_name == latest_subq.c.service_name)
            & (ServiceHealth.checked_at == latest_subq.c.max_checked),
        )
        .where(ServiceHealth.service_name.in_(configured_names))
        .order_by(ServiceHealth.service_name)
    )

    result = await session.execute(query)
    rows = result.scalars().all()
    unit_map = {
        s.name: s.systemd_unit
        for s in config.agents.sysadmin.services
    }

    # Map service name → controllable flag from config
    controllable_map = {
        s.name: s.controllable
        for s in config.agents.sysadmin.services
    }

    return {
        "services": [
            {
                "name": r.service_name,
                "status": r.status,
                "response_time_ms": r.response_time_ms,
                "details": r.details,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
                "systemd_unit": unit_map.get(r.service_name),
                "controllable": controllable_map.get(r.service_name, True),
            }
            for r in rows
        ],
        "all_healthy": all(r.status == "ok" for r in rows),
    }


@router.get("/status/{service}")
async def get_service_status(
    service: str,
    limit: int = Query(default=10, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """Get health check history for a specific service."""
    query = (
        select(ServiceHealth)
        .where(ServiceHealth.service_name == service)
        .order_by(desc(ServiceHealth.checked_at))
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "service": service,
        "checks": [
            {
                "status": r.status,
                "response_time_ms": r.response_time_ms,
                "details": r.details,
                "checked_at": r.checked_at.isoformat() if r.checked_at else None,
            }
            for r in rows
        ],
    }


@router.get("/services/{service_name}/details")
async def get_service_details(service_name: str):
    """Get detailed systemd unit status for a monitored service."""
    config = get_config()
    svc_map = {s.name: s for s in config.agents.sysadmin.services}

    if service_name not in svc_map:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    svc = svc_map[service_name]
    unit = svc.systemd_unit
    if not unit:
        raise HTTPException(
            status_code=400,
            detail=f"Service '{service_name}' has no systemd_unit configured",
        )

    return await get_unit_status(unit, user=svc.user)


_ACTION_FNS = {
    "restart": restart_unit,
    "start": start_unit,
    "stop": stop_unit,
}


@router.post(
    "/services/{service_name}/{action}",
    dependencies=[Depends(require_auth)],
    response_model=ServiceActionResponse,
)
async def service_action(
    service_name: str,
    action: Literal["restart", "start", "stop"],
):
    """Restart, start, or stop a monitored service via systemd."""
    config = get_config()
    svc_map = {s.name: s for s in config.agents.sysadmin.services}

    if service_name not in svc_map:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    svc = svc_map[service_name]

    if not svc.controllable:
        raise HTTPException(
            status_code=403,
            detail=f"Service '{service_name}' is not controllable",
        )

    if not svc.systemd_unit:
        raise HTTPException(
            status_code=400,
            detail=f"Service '{service_name}' has no systemd_unit configured",
        )

    fn = _ACTION_FNS[action]
    success, message = await fn(svc.systemd_unit, user=svc.user)
    return {"success": success, "message": message}


@router.get("/resources")
async def get_resources(session: AsyncSession = Depends(get_db_session)):
    """Get the latest resource snapshot."""
    query = (
        select(ResourceSnapshot)
        .order_by(desc(ResourceSnapshot.recorded_at))
        .limit(1)
    )
    result = await session.execute(query)
    row = result.scalar_one_or_none()

    if not row:
        return {"message": "No resource data yet"}

    return {
        "cpu_percent": float(row.cpu_percent) if row.cpu_percent else None,
        "ram": {
            "used_mb": row.ram_used_mb,
            "total_mb": row.ram_total_mb,
            "percent": float(row.ram_percent) if row.ram_percent else None,
        },
        "swap": {
            "used_mb": row.swap_used_mb,
            "total_mb": row.swap_total_mb,
        },
        "disk": row.disk_usage,
        "gpu": row.gpu_usage,
        "load_avg": {
            "1m": float(row.load_avg_1m) if row.load_avg_1m else None,
            "5m": float(row.load_avg_5m) if row.load_avg_5m else None,
            "15m": float(row.load_avg_15m) if row.load_avg_15m else None,
        },
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
    }


@router.get("/resources/history", response_model=ResourceHistoryResponse)
async def get_resource_history(
    hours: int | None = Query(default=None, le=720),
    days: int | None = Query(default=None, le=30),
    session: AsyncSession = Depends(get_db_session),
):
    """Get resource snapshot history for the given time window.

    Night Worker uses ``days=7`` for capacity forecasting.
    Specify either ``hours`` or ``days``; defaults to 24 hours.
    """
    if days is not None:
        total_hours = days * 24
    elif hours is not None:
        total_hours = hours
    else:
        total_hours = 24

    since = datetime.now(UTC) - timedelta(hours=total_hours)

    query = (
        select(ResourceSnapshot)
        .where(ResourceSnapshot.recorded_at >= since)
        .order_by(ResourceSnapshot.recorded_at)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "period_hours": total_hours,
        "count": len(rows),
        "snapshots": [
            {
                "cpu_percent": float(r.cpu_percent) if r.cpu_percent else None,
                "ram_percent": float(r.ram_percent) if r.ram_percent else None,
                "disk_usage": r.disk_usage,
                "load_avg_1m": float(r.load_avg_1m) if r.load_avg_1m else None,
                "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
            }
            for r in rows
        ],
    }


@router.get("/alerts", response_model=AlertsResponse)
async def get_alerts(
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, le=200),
    session: AsyncSession = Depends(get_db_session),
):
    """Get alerts, optionally filtered to active (unresolved) only."""
    query = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
    if active_only:
        query = query.where(Alert.resolved.is_(False))

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "alerts": [
            {
                "id": str(r.id),
                "agent": r.agent,
                "severity": r.severity,
                "title": r.title,
                "message": r.message,
                "details": r.details,
                "acknowledged": r.acknowledged,
                "resolved": r.resolved,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.post(
    "/alerts/{alert_id}/ack",
    dependencies=[Depends(require_auth)],
    response_model=AlertAckResponse,
)
async def acknowledge_alert(
    alert_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Acknowledge an alert."""
    query = select(Alert).where(Alert.id == alert_id)
    result = await session.execute(query)
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    alert.acknowledged = True
    alert.acknowledged_at = datetime.now(UTC)
    return {"status": "acknowledged", "id": str(alert.id)}


@router.get("/briefing/preview")
async def preview_briefing(session: AsyncSession = Depends(get_db_session)):
    """Preview the morning briefing data without sending it."""
    return await generate_briefing_data(session)


@router.get("/dnd", response_model=DndStatusResponse)
async def get_dnd_status():
    """Get current Do Not Disturb status."""
    return dnd_manager.get_status()


class DndToggleRequest(BaseModel):
    enabled: bool | None = None  # True=on, False=off, None=revert to schedule


@router.post("/dnd", dependencies=[Depends(require_auth)], response_model=DndStatusResponse)
async def toggle_dnd(body: DndToggleRequest):
    """Toggle Do Not Disturb mode.

    - ``enabled: true`` — force DND on
    - ``enabled: false`` — force DND off
    - ``enabled: null`` — revert to schedule-only
    """
    dnd_manager.set_manual_override(body.enabled)
    return dnd_manager.get_status()


@router.get("/ports")
async def get_ports():
    """Get current listening port usage map."""
    ports = await asyncio.to_thread(SysAdminAgent.get_port_usage)
    return {"ports": ports, "count": len(ports)}
