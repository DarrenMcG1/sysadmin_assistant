"""Dataclasses matching the sysadmin-service API response shapes.

These are intentionally *not* Pydantic — they're lightweight containers
for data that's already been validated by the backend.  Using dataclasses
keeps the import cost low and avoids pulling Pydantic into the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

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


# ── Service status ───────────────────────────────────────────────────


@dataclass
class ServiceStatus:
    name: str
    status: str            # "ok" | "degraded" | "unreachable" | "error"
    response_time_ms: float | None = None
    details: str | None = None
    checked_at: str | None = None
    systemd_unit: str | None = None


@dataclass
class StatusResponse:
    services: list[ServiceStatus] = field(default_factory=list)
    all_healthy: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> StatusResponse:
        services = [
            ServiceStatus(**svc) for svc in data.get("services", [])
        ]
        return cls(services=services, all_healthy=data.get("all_healthy", True))


# ── Resources ────────────────────────────────────────────────────────


@dataclass
class RamInfo:
    used_mb: int = 0
    total_mb: int = 0
    percent: float = 0.0


@dataclass
class DiskInfo:
    mount: str = "/"
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    percent: float = 0.0


@dataclass
class ResourceResponse:
    cpu_percent: float = 0.0
    ram: RamInfo = field(default_factory=RamInfo)
    disk: list[DiskInfo] = field(default_factory=list)
    recorded_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> ResourceResponse:
        if "message" in data:
            # "No resource data yet" response
            return cls()

        ram_raw = data.get("ram", {})
        ram = RamInfo(
            used_mb=ram_raw.get("used_mb", 0) or 0,
            total_mb=ram_raw.get("total_mb", 0) or 0,
            percent=float(ram_raw.get("percent", 0) or 0),
        )

        # disk_usage is a dict keyed by mount point
        disk_raw = data.get("disk", {}) or {}
        disks = []
        for mount, info in disk_raw.items():
            disks.append(DiskInfo(
                mount=mount,
                total_gb=info.get("total_gb", 0),
                used_gb=info.get("used_gb", 0),
                free_gb=info.get("free_gb", 0),
                percent=info.get("percent", 0),
            ))
        # Sort by mount point for consistent display — root first
        disks.sort(key=lambda d: d.mount)

        return cls(
            cpu_percent=float(data.get("cpu_percent", 0) or 0),
            ram=ram,
            disk=disks,
            recorded_at=data.get("recorded_at"),
        )


# ── Alerts ───────────────────────────────────────────────────────────


@dataclass
class AlertInfo:
    id: str = ""
    agent: str = ""
    severity: str = "info"       # "info" | "warning" | "critical"
    title: str = ""
    message: str | None = None
    acknowledged: bool = False
    resolved: bool = False
    created_at: str | None = None


@dataclass
class AlertsResponse:
    alerts: list[AlertInfo] = field(default_factory=list)
    count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> AlertsResponse:
        alerts = []
        for a in data.get("alerts", []):
            alerts.append(AlertInfo(
                id=a.get("id", ""),
                agent=a.get("agent", ""),
                severity=a.get("severity", "info"),
                title=a.get("title", ""),
                message=a.get("message"),
                acknowledged=a.get("acknowledged", False),
                resolved=a.get("resolved", False),
                created_at=a.get("created_at"),
            ))
        return cls(alerts=alerts, count=data.get("count", len(alerts)))

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "info")


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
