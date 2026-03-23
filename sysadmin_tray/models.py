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
    controllable: bool = True


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
    details: dict = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    created_at: str | None = None

    @property
    def service_name(self) -> str | None:
        """Extract service_name from details, if present."""
        return self.details.get("service_name")


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
                details=a.get("details") or {},
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


# ── Resource history ────────────────────────────────────────────────


@dataclass
class ResourceHistorySnapshot:
    cpu_percent: float | None = None
    ram_percent: float | None = None
    load_avg_1m: float | None = None
    recorded_at: str | None = None


@dataclass
class ResourceHistoryResponse:
    period_hours: int = 24
    count: int = 0
    snapshots: list[ResourceHistorySnapshot] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> ResourceHistoryResponse:
        snapshots = [
            ResourceHistorySnapshot(**s) for s in data.get("snapshots", [])
        ]
        return cls(
            period_hours=data.get("period_hours", 24),
            count=data.get("count", 0),
            snapshots=snapshots,
        )


# ── Log entries ─────────────────────────────────────────────────────


@dataclass
class LogEntryInfo:
    id: str = ""
    source: str = ""
    severity: str = "info"
    message: str = ""
    logged_at: str | None = None


@dataclass
class LogsResponse:
    entries: list[LogEntryInfo] = field(default_factory=list)
    count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> LogsResponse:
        entries = [
            LogEntryInfo(
                id=e.get("id", ""),
                source=e.get("source", ""),
                severity=e.get("severity", "info"),
                message=e.get("message", ""),
                logged_at=e.get("logged_at"),
            )
            for e in data.get("entries", [])
        ]
        return cls(entries=entries, count=data.get("count", len(entries)))


@dataclass
class LogStatsResponse:
    period_hours: int = 24
    sources: dict[str, dict[str, int]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> LogStatsResponse:
        return cls(
            period_hours=data.get("period_hours", 24),
            sources=data.get("sources", {}),
        )


# ── Project data ────────────────────────────────────────────────────


@dataclass
class ProjectOverviewEntry:
    name: str = ""
    health_score: int = 0
    grade: str = ""
    last_commit_at: str | None = None
    branch_count: int = 0
    stale_branch_count: int = 0
    todo_count: int = 0
    has_readme: bool = False
    has_claude_md: bool = False
    total_size_mb: float = 0.0
    scanned_at: str | None = None


@dataclass
class ProjectOverviewResponse:
    projects: list[ProjectOverviewEntry] = field(default_factory=list)
    count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> ProjectOverviewResponse:
        projects = [
            ProjectOverviewEntry(**p) for p in data.get("projects", [])
        ]
        return cls(projects=projects, count=data.get("count", len(projects)))


@dataclass
class ManagedServiceInfo:
    name: str = ""
    status: str = "unknown"
    response_time_ms: float | None = None


@dataclass
class ProjectHealthInfo:
    health_score: int = 0
    scanned_at: str | None = None


@dataclass
class ManagedProjectInfo:
    name: str = ""
    path: str = ""
    services: list[ManagedServiceInfo] = field(default_factory=list)
    project_health: ProjectHealthInfo | None = None
    all_services_healthy: bool | None = None


@dataclass
class ManagedProjectsResponse:
    projects: list[ManagedProjectInfo] = field(default_factory=list)
    count: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> ManagedProjectsResponse:
        projects = []
        for p in data.get("projects", []):
            services = [
                ManagedServiceInfo(**s) for s in p.get("services", [])
            ]
            health_raw = p.get("project_health")
            health = ProjectHealthInfo(**health_raw) if health_raw else None
            projects.append(ManagedProjectInfo(
                name=p.get("name", ""),
                path=p.get("path", ""),
                services=services,
                project_health=health,
                all_services_healthy=p.get("all_services_healthy"),
            ))
        return cls(projects=projects, count=data.get("count", len(projects)))


# ── Service detail (systemd unit info) ──────────────────────────────


@dataclass
class ServiceDetailInfo:
    unit: str = ""
    active_state: str = ""
    sub_state: str = ""
    main_pid: int = 0
    memory_current: int = 0
    cpu_usage_nsec: int = 0
    load_state: str = ""
    is_active: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> ServiceDetailInfo:
        pid_raw = data.get("MainPID", "0")
        try:
            pid = int(pid_raw)
        except (ValueError, TypeError):
            pid = 0

        mem_raw = data.get("MemoryCurrent", "0")
        try:
            mem = int(mem_raw) if mem_raw != "[not set]" else 0
        except (ValueError, TypeError):
            mem = 0

        cpu_raw = data.get("CPUUsageNSec", "0")
        try:
            cpu = int(cpu_raw) if cpu_raw != "[not set]" else 0
        except (ValueError, TypeError):
            cpu = 0

        return cls(
            unit=data.get("unit", ""),
            active_state=data.get("ActiveState", ""),
            sub_state=data.get("SubState", ""),
            main_pid=pid,
            memory_current=mem,
            cpu_usage_nsec=cpu,
            load_state=data.get("LoadState", ""),
            is_active=data.get("is_active", False),
        )
