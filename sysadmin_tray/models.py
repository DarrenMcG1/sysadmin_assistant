"""API response models for the tray app.

The response shapes are imported from :mod:`sysadmin.core.contracts` — the
shared pydantic contracts module used by the backend as ``response_model``
on the same endpoints. The tray no longer hand-copies these shapes
(root cause of SNAG-TRAY-005).

``sysadmin.core.contracts`` is dependency-light (pydantic + stdlib only), so
importing it here does not pull FastAPI or SQLAlchemy into the tray.

Defensive parsing behaviour is preserved: unknown fields are ignored,
missing fields fall back to defaults, and unparseable payloads raise
``pydantic.ValidationError`` (a ``ValueError``) which the client's fetch
paths catch and treat as connection lost.

This module keeps only tray-side presentation logic: icon states/colours
and the pure ``compute_icon_state`` function.
"""

from __future__ import annotations

from enum import Enum

# Re-exported shared contracts (imported by client, dashboard, widgets, tests)
from sysadmin.core.contracts import (  # noqa: F401
    AlertInfo,
    AlertsResponse,
    CleanResultResponse,
    DiskInfo,
    DiskReviewResponse,
    DiskThresholdInfo,
    DuplicateGroupInfo,
    DuplicatesResponse,
    FileActionsResponse,
    FileAuditSummary,
    FileQuickWins,
    FileRecommendationInfo,
    FileStatusResponse,
    FileTrendForecast,
    FileTrendScan,
    FileTrendsResponse,
    LargeFileInfo,
    LargeFilesResponse,
    LogEntryInfo,
    LogsResponse,
    LogStatsResponse,
    ManagedProjectInfo,
    ManagedProjectsResponse,
    ManagedServiceInfo,
    MisplacedFilesResponse,
    ProjectDetailResponse,
    ProjectHealthInfo,
    ProjectHistoryPoint,
    ProjectOverviewEntry,
    ProjectOverviewResponse,
    RamInfo,
    ReliabilityDeduction,
    ReliabilityResponse,
    ReliabilitySummary,
    ResourceHistoryResponse,
    ResourceHistorySnapshot,
    ResourceResponse,
    ServiceActionsResponse,
    ServiceDetailInfo,
    ServiceRecommendationInfo,
    ServiceReliabilityInfo,
    ServiceStatus,
    StatusResponse,
    UnitActionsResponse,
    UnitFindingInfo,
    UnitRecommendationInfo,
    UnitScanResponse,
    UnitScanSummary,
)

# ── Icon states ──────────────────────────────────────────────────────


class IconState(Enum):
    """Visual state of the tray icon."""

    HEALTHY = "healthy"          # green
    WARNING = "warning"          # amber
    CRITICAL = "critical"        # red
    DISCONNECTED = "disconnected"  # grey


ICON_COLOURS = {
    IconState.HEALTHY: "#27ae60",
    IconState.WARNING: "#f39c12",
    IconState.CRITICAL: "#e74c3c",
    IconState.DISCONNECTED: "#95a5a6",
}


# ── Icon state computation (pure function) ───────────────────────────


def compute_icon_state(
    status: StatusResponse | None,
    alerts: AlertsResponse | None,
    backend_reachable: bool,
) -> IconState:
    """Determine the tray icon colour from current data.

    This is a pure function with no side effects — easy to test.
    """
    if not backend_reachable:
        return IconState.DISCONNECTED

    # Check service statuses
    if status:
        for svc in status.services:
            if svc.status in ("unreachable", "error"):
                return IconState.CRITICAL
        for svc in status.services:
            if svc.status == "degraded":
                return IconState.WARNING

    # Check unacknowledged alerts
    if alerts:
        unacked_critical = sum(
            1 for a in alerts.alerts
            if a.severity == "critical" and not a.acknowledged
        )
        if unacked_critical > 0:
            return IconState.CRITICAL

        unacked_warning = sum(
            1 for a in alerts.alerts
            if a.severity == "warning" and not a.acknowledged
        )
        if unacked_warning > 0:
            return IconState.WARNING

    return IconState.HEALTHY
