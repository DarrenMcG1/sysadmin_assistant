"""SysAdmin API endpoints — service status, resources, alerts, ports."""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.auth import require_auth
from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    AlertAckResponse,
    AlertsResponse,
    DndStatusResponse,
    HealthReviewResponse,
    ResourceHistoryResponse,
    SelfMonitorResponse,
    ServiceActionResponse,
    StatusResponse,
)
from sysadmin.core.database import get_db_session
from sysadmin.core.models.alert import Alert
from sysadmin.monitor import health_review as health_review_module
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.desktop import tray_presence
from sysadmin.monitor.dnd import dnd_manager
from sysadmin.monitor.models.health_review import HealthReview
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth, is_fault
from sysadmin.monitor.self_monitor import build_self_report
from sysadmin.monitor.services import get_services
from sysadmin.monitor.sse import event_broadcaster, event_stream
from sysadmin.monitor.systemd import (
    SystemdQueryError,
    get_unit_status,
    restart_unit,
    start_unit,
    stop_unit,
)

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
    configured_names = {s.name for s in get_services().services}

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
        for s in get_services().services
    }

    # Map service name → controllable flag from config
    controllable_map = {
        s.name: s.controllable
        for s in get_services().services
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
        # Not ``== "ok"``: three of this box's services are declared
        # ``monitor: false`` and stored ``skipped``, so that phrasing
        # read False on every healthy day from migration 009 until
        # 2026-08-25 (``SNAG-API-004``).  It was masked throughout by
        # something genuinely being down.  ``is_fault`` is the one
        # statement of which statuses are faults.
        "all_healthy": not any(is_fault(r.status) for r in rows),
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
    svc_map = {s.name: s for s in get_services().services}

    if service_name not in svc_map:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

    svc = svc_map[service_name]
    unit = svc.systemd_unit
    if not unit:
        raise HTTPException(
            status_code=400,
            detail=f"Service '{service_name}' has no systemd_unit configured",
        )

    try:
        return await get_unit_status(unit, user=svc.user)
    except SystemdQueryError as e:
        # systemctl could not be queried (typically the user session bus is
        # out of reach) — a 503 says "ask again later", where the old bare
        # 500 said "the server is broken".
        raise HTTPException(status_code=503, detail=str(e)) from e


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
    svc_map = {s.name: s for s in get_services().services}

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
    """Get alerts, optionally filtered to active (unresolved) only.

    Polling this route is what tells the daemon somebody is already
    watching, which keeps its own desktop notifier quiet — see
    :mod:`sysadmin.monitor.desktop`.  Marked here rather than in
    middleware because this is the *only* route the tray's notification
    loop depends on: a client fetching ``/status`` for a dashboard is not
    going to show anyone an alert, and treating it as presence would
    silence the daemon for a reader that never sees alerts at all.
    """
    tray_presence.mark_seen()

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


@router.get("/self", response_model=SelfMonitorResponse)
async def get_self_status(session: AsyncSession = Depends(get_db_session)):
    """Self-monitoring — per-agent run health from the ``agent_runs`` table.

    Reports each agent's last run and status, recent durations plus their
    trend, consecutive failures, and whether it looks *stalled* (no run
    within a multiple of its configured schedule interval).
    """
    return await build_self_report(session, get_config())


@router.get("/events")
async def stream_events():
    """Server-Sent Events stream of status/alert changes.

    Lets clients (the tray) stop polling: agents publish to the internal
    event bus and every connected stream gets the change pushed. An SSE
    comment is written every ``events.heartbeat_seconds`` so idle streams
    survive proxies and NAT timeouts, and the path is excluded from the
    access log (as ``/health`` is) so long-lived streams add no log noise.
    """
    config = get_config().events

    return StreamingResponse(
        event_stream(
            event_broadcaster,
            heartbeat_seconds=config.heartbeat_seconds,
            retry_ms=config.retry_ms,
            max_queue=config.max_queued_events,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable proxy buffering (nginx)
        },
    )


@router.get("/ports")
async def get_ports():
    """Get current listening port usage map."""
    ports = await asyncio.to_thread(SysAdminAgent.get_port_usage)
    return {"ports": ports, "count": len(ports)}


# ── Weekly system health review (Session 25, Tier 3) ──────────────────


def _health_review_payload(review: HealthReview) -> dict:
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


@router.get("/review", response_model=HealthReviewResponse)
async def get_health_review(session: AsyncSession = Depends(get_db_session)):
    """The latest stored weekly system health review (Session 25, Tier 3).

    **It lives here rather than under ``/api/services``**, which is the
    one place this tier departs from its three siblings' naming, and the
    departure is what keeps a guard honest.  ``/api/services`` carries a
    test asserting that no non-GET route exists anywhere beneath it —
    the promise that the reliability score is not a control surface — and
    a ``POST .../review/generate`` there could only ship by narrowing
    that test to admit the route being added.  The content agrees with
    the move: three of this review's four inputs are alert volume,
    resource anomalies and resource trend, all of which are already
    served from this prefix, and only the fourth is service reliability.

    **Read back rather than computed live**, the call
    ``GET /api/logs/review`` makes for its reason: a narrative costs a
    GPU generation measured in minutes, cannot be produced inside a
    request, and is *about* a period rather than about now.

    404 is "no review has been generated yet", which is why
    ``health_reviews`` is in ``KEEP_LATEST_PER``: a purge that emptied
    the table would turn "none lately" into "none ever".
    """
    result = await session.execute(
        select(HealthReview).order_by(desc(HealthReview.generated_at)).limit(1)
    )
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="No health review generated yet")
    return _health_review_payload(review)


@router.post(
    "/review/generate",
    response_model=HealthReviewResponse,
    dependencies=[Depends(require_auth)],
)
async def generate_health_review(session: AsyncSession = Depends(get_db_session)):
    """Generate a system health review now.  Authenticated; the LLM is optional.

    Returns 404 when the monitor recorded no runs in either period —
    nothing was observed, which is not the same as nothing happening and
    must not be served as an empty review.
    """
    review = await health_review_module.generate_review(session)
    if review is None:
        raise HTTPException(status_code=404, detail="No monitoring data to review")
    payload = _health_review_payload(review)
    await session.commit()
    return payload
