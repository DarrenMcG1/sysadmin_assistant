"""Shared API contracts between the backend and the tray app.

Single source of truth for the response shapes of every endpoint the
tray consumes (root cause fix for SNAG-TRAY-005 — the tray previously
hand-copied these shapes as dataclasses which silently drifted).

Usage:
    - Backend routers set these as ``response_model=`` so the wire format
      is enforced server-side.
    - The tray imports them (via ``sysadmin_tray.models``) and parses
      responses with ``Model.from_dict(payload)``.

IMPORTANT — keep this module dependency-light: pydantic and stdlib ONLY.
The tray imports it at runtime and must not pull in FastAPI, SQLAlchemy,
or any other heavy backend dependency.

Parsing is deliberately defensive (Session 11 behaviour preserved):
    - unknown fields are ignored (``extra="ignore"``)
    - missing fields fall back to defaults
    - a payload that cannot be parsed raises ``pydantic.ValidationError``,
      which is a ``ValueError`` — the tray's fetch paths already catch
      that and mark the connection lost.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ── Base ─────────────────────────────────────────────────────────────


class Contract(BaseModel):
    """Base for all shared response models — tolerant of unknown fields."""

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def from_dict(cls, data: dict) -> Contract:
        """Parse a decoded JSON payload. Raises ValidationError (a ValueError)."""
        return cls.model_validate(data)


def _fill_count(data: Any, key: str) -> Any:
    """Default a missing ``count`` field to ``len(data[key])``."""
    if isinstance(data, dict) and "count" not in data:
        items = data.get(key)
        if isinstance(items, list):
            data = {**data, "count": len(items)}
    return data


# ── /health ──────────────────────────────────────────────────────────


class HealthResponse(Contract):
    status: str = ""
    service: str = ""
    version: str = ""


# ── /api/sysadmin/status ─────────────────────────────────────────────


class ServiceStatus(Contract):
    name: str = ""
    status: str = "unknown"  # "ok" | "degraded" | "unreachable" | "error"
    response_time_ms: float | None = None
    details: dict[str, Any] | str | None = None
    checked_at: str | None = None
    systemd_unit: str | None = None
    controllable: bool = True


class StatusResponse(Contract):
    services: list[ServiceStatus] = Field(default_factory=list)
    all_healthy: bool = True


# ── /api/sysadmin/resources ──────────────────────────────────────────
#
# Parse-side contract only (no response_model): the endpoint returns
# ``{"message": "No resource data yet"}`` when no snapshot exists, and
# serialises disk usage as a dict keyed by mount point. The tray wants
# a sorted list, so a before-validator reshapes it.


class RamInfo(Contract):
    used_mb: int = 0
    total_mb: int = 0
    percent: float = 0.0

    @field_validator("used_mb", "total_mb", "percent", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class DiskInfo(Contract):
    mount: str = "/"
    total_gb: float = 0.0
    used_gb: float = 0.0
    free_gb: float = 0.0
    percent: float = 0.0

    @field_validator("total_gb", "used_gb", "free_gb", "percent", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class ResourceResponse(Contract):
    cpu_percent: float = 0.0
    ram: RamInfo = Field(default_factory=RamInfo)
    disk: list[DiskInfo] = Field(default_factory=list)
    recorded_at: str | None = None

    @field_validator("cpu_percent", mode="before")
    @classmethod
    def _none_cpu_to_zero(cls, v: Any) -> Any:
        return 0.0 if v is None else v

    @model_validator(mode="before")
    @classmethod
    def _reshape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "message" in data and "cpu_percent" not in data:
            # "No resource data yet" response
            return {}
        disk_raw = data.get("disk")
        if isinstance(disk_raw, dict):
            disks = [
                {**(info if isinstance(info, dict) else {}), "mount": mount}
                for mount, info in disk_raw.items()
            ]
            # Sort by mount point for consistent display — root first
            disks.sort(key=lambda d: d["mount"])
            data = {**data, "disk": disks}
        elif disk_raw is None:
            data = {**data, "disk": []}
        return data


# ── /api/sysadmin/resources/history ──────────────────────────────────


class ResourceHistorySnapshot(Contract):
    cpu_percent: float | None = None
    ram_percent: float | None = None
    load_avg_1m: float | None = None
    disk_usage: dict[str, Any] | None = None
    recorded_at: str | None = None


class ResourceHistoryResponse(Contract):
    period_hours: int = 24
    count: int = 0
    snapshots: list[ResourceHistorySnapshot] = Field(default_factory=list)


# ── /api/sysadmin/alerts ─────────────────────────────────────────────


class AlertInfo(Contract):
    id: str = ""
    agent: str = ""
    severity: str = "info"  # "info" | "warning" | "critical"
    title: str = ""
    message: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    created_at: str | None = None

    @field_validator("details", mode="before")
    @classmethod
    def _none_details_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v

    @property
    def service_name(self) -> str | None:
        """Extract service_name from details, if present."""
        return self.details.get("service_name")


class AlertsResponse(Contract):
    alerts: list[AlertInfo] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "alerts")

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "critical")

    @property
    def warning_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == "info")


# ── /api/logs/recent + /api/logs/stats ───────────────────────────────


class LogEntryInfo(Contract):
    id: str = ""
    source: str = ""
    severity: str = "info"
    message: str = ""
    logged_at: str | None = None


class LogsResponse(Contract):
    entries: list[LogEntryInfo] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "entries")


class LogStatsResponse(Contract):
    period_hours: int = 24
    sources: dict[str, dict[str, int]] = Field(default_factory=dict)


# ── /api/projects/overview ───────────────────────────────────────────


class ProjectOverviewEntry(Contract):
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

    @field_validator(
        "health_score",
        "branch_count",
        "stale_branch_count",
        "todo_count",
        "total_size_mb",
        mode="before",
    )
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class ProjectOverviewResponse(Contract):
    projects: list[ProjectOverviewEntry] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "projects")


# ── /api/projects/managed ────────────────────────────────────────────


class ManagedServiceInfo(Contract):
    name: str = ""
    status: str = "unknown"
    response_time_ms: float | None = None


class ProjectHealthInfo(Contract):
    health_score: int = 0
    scanned_at: str | None = None


class ManagedProjectInfo(Contract):
    name: str = ""
    path: str = ""
    services: list[ManagedServiceInfo] = Field(default_factory=list)
    project_health: ProjectHealthInfo | None = None
    all_services_healthy: bool | None = None


class ManagedProjectsResponse(Contract):
    projects: list[ManagedProjectInfo] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "projects")


# ── /api/sysadmin/services/{name}/details ────────────────────────────
#
# Parse-side contract only: the endpoint returns raw ``systemctl show``
# properties (string values, ``"[not set]"`` sentinels), plus ``unit``
# and ``is_active`` keys. Aliased fields + validators normalise them.


def _int_or_zero(v: Any) -> int:
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


class ServiceDetailInfo(Contract):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    unit: str = ""
    active_state: str = Field(default="", alias="ActiveState")
    sub_state: str = Field(default="", alias="SubState")
    main_pid: int = Field(default=0, alias="MainPID")
    memory_current: int = Field(default=0, alias="MemoryCurrent")
    cpu_usage_nsec: int = Field(default=0, alias="CPUUsageNSec")
    load_state: str = Field(default="", alias="LoadState")
    is_active: bool = False

    @field_validator("main_pid", "memory_current", "cpu_usage_nsec", mode="before")
    @classmethod
    def _coerce_int(cls, v: Any) -> int:
        return _int_or_zero(v)


# ── /api/sysadmin/dnd ────────────────────────────────────────────────


class DndWindow(Contract):
    start: str = ""
    end: str = ""


class DndStatusResponse(Contract):
    active: bool = False
    manual_override: bool | None = None
    config_enabled: bool = False
    allow_critical: bool = True
    schedule: list[DndWindow] = Field(default_factory=list)


# ── /api/sysadmin/self ───────────────────────────────────────────────


class AgentSelfHealth(Contract):
    """One agent's run health, derived from the ``agent_runs`` table."""

    name: str = ""
    enabled: bool = True
    job_id: str = ""
    interval_seconds: int = 0
    stall_window_seconds: float = 0.0
    last_run_at: str | None = None
    last_status: str = "never"  # "completed" | "failed" | "running" | "never"
    last_run_type: str | None = None
    last_duration_seconds: float | None = None
    seconds_since_last_run: float | None = None
    expected_next_run_at: str | None = None
    runs_considered: int = 0
    consecutive_failures: int = 0
    recent_durations: list[float] = Field(default_factory=list)
    mean_duration_seconds: float | None = None
    duration_trend: str = "unknown"  # "rising" | "falling" | "steady" | "unknown"
    stalled: bool = False
    stall_reason: str | None = None


class SelfMonitorResponse(Contract):
    """GET /api/sysadmin/self — is the service still doing its job?"""

    agents: list[AgentSelfHealth] = Field(default_factory=list)
    count: int = 0
    stalled_count: int = 0
    failing_count: int = 0
    healthy: bool = True
    generated_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "agents")


# ── /api/sysadmin/events (SSE) ───────────────────────────────────────
#
# Serialise-side contract: not a JSON body but the payload of each
# ``data:`` line on the event stream.


class EventMessage(Contract):
    """One Server-Sent Event payload pushed to clients."""

    event: str = ""  # "connected" | "alert.raised" | "alert.resolved" | "agent.run" | …
    data: dict[str, Any] = Field(default_factory=dict)
    ts: str | None = None

    @field_validator("data", mode="before")
    @classmethod
    def _none_data_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


# ── Action responses ─────────────────────────────────────────────────


class ServiceActionResponse(Contract):
    """POST /api/sysadmin/services/{name}/{action}."""

    success: bool = False
    message: str = ""


class AlertAckResponse(Contract):
    """POST /api/sysadmin/alerts/{id}/ack."""

    status: str = ""
    id: str = ""


class ScanAllResponse(Contract):
    """POST /api/sysadmin/scan-all."""

    status: str = ""


# ── /api/files/* mutating actions ────────────────────────────────────
#
# Shared manifest shape for organise / duplicate cleanup / downloads
# cleanup.  Every one of those endpoints is a dry run unless the request
# body sets ``confirm: true``, and the response is the same either way:
# ``dry_run`` says whether the manifest was carried out, and each
# operation's ``status`` says what happened to it.


class FileOperation(Contract):
    """One file the action would touch (or did touch)."""

    action: str = ""  # "move" | "trash" | "delete"
    source: str = ""
    destination: str | None = None
    category: str | None = None
    size_bytes: int = 0
    status: str = "planned"  # "planned" | "done" | "skipped" | "failed"
    reason: str | None = None
    # Duplicate cleanup only — the copy deliberately retained
    keep_path: str | None = None


class FileFlag(Contract):
    """A file surfaced for human review but never acted on automatically."""

    path: str = ""
    kind: str = ""  # "loose_code"
    reason: str = ""
    size_bytes: int = 0


class FileActionResponse(Contract):
    """POST /api/files/organise and /api/files/clean/{duplicates,downloads}."""

    operation: str = ""  # "organise" | "clean_duplicates" | "clean_downloads"
    dry_run: bool = True
    scan_root: str = ""
    operations: list[FileOperation] = Field(default_factory=list)
    flagged: list[FileFlag] = Field(default_factory=list)
    planned_count: int = 0
    done_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    total_bytes: int = 0
    truncated: bool = False  # manifest hit actions.max_operations
    message: str = ""


# ─────────────────────────────────────────────────────────────────────
# Session 19 additions — /api/files/* and /api/projects/{name} GET
# shapes consumed by the dashboard's Files tab and trend charts.
#
# These are PARSE-SIDE ONLY: the routers are not annotated with
# ``response_model=`` (the endpoints were owned by another session), so
# the tray parses defensively and the models tolerate both the populated
# payload and the "no data yet" / 404 shapes.
#
# Keep this whole block together — it is appended, never interleaved.
# ─────────────────────────────────────────────────────────────────────


class FileQuickWins(Contract):
    """``findings.quick_wins`` — one-click-fixable counts."""

    empty_dirs: int = 0
    stale_caches: int = 0
    stale_cache_mb: float = 0.0

    @field_validator("empty_dirs", "stale_caches", "stale_cache_mb", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v

    @property
    def total(self) -> int:
        """Number of individually actionable items."""
        return self.empty_dirs + self.stale_caches


class FileAuditSummary(Contract):
    """The ``summary`` block of GET /api/files/status."""

    similar_folders: int = 0
    misplaced_files: int = 0
    old_downloads: int = 0
    large_files: int = 0
    duplicate_groups: int = 0
    empty_dirs: int = 0
    stale_project_dirs: int = 0
    stale_files: int = 0


class FileStatusResponse(Contract):
    """GET /api/files/status — latest filesystem audit summary.

    Returns ``{"message": "No audit data yet…"}`` before the first scan;
    that shape parses to ``has_data is False`` with zeroed counts.
    """

    scan_root: str = ""
    scanned_at: str | None = None
    summary: FileAuditSummary = Field(default_factory=FileAuditSummary)
    reclaimable_mb: float = 0.0
    quick_wins: FileQuickWins = Field(default_factory=FileQuickWins)
    message: str = ""

    @field_validator("reclaimable_mb", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0.0 if v is None else v

    @field_validator("summary", "quick_wins", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v

    @property
    def has_data(self) -> bool:
        """True once at least one scan has been recorded."""
        return bool(self.scanned_at or self.scan_root)


class LargeFileInfo(Contract):
    """One entry of ``findings.large_files``."""

    path: str = ""
    size_mb: float = 0.0

    @field_validator("size_mb", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0.0 if v is None else v


class LargeFilesResponse(Contract):
    """GET /api/files/large."""

    large_files: list[LargeFileInfo] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "large_files")


class DuplicateGroupInfo(Contract):
    """One group of byte-identical files."""

    hash: str = ""
    files: list[str] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "files")


class DuplicatesResponse(Contract):
    """GET /api/files/duplicates."""

    duplicate_groups: list[DuplicateGroupInfo] = Field(default_factory=list)
    count: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "duplicate_groups")


class MisplacedFilesResponse(Contract):
    """GET /api/files/misplaced — category → list of paths."""

    misplaced_files: dict[str, list[str]] = Field(default_factory=dict)
    count: int = 0

    @field_validator("misplaced_files", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        if isinstance(data, dict) and "count" not in data:
            groups = data.get("misplaced_files")
            if isinstance(groups, dict):
                total = sum(
                    len(v) for v in groups.values() if isinstance(v, list)
                )
                data = {**data, "count": total}
        return data


class FileTrendScan(Contract):
    """One historical scan row from GET /api/files/trends."""

    scanned_at: str | None = None
    similar_folders: int = 0
    misplaced_files: int = 0
    old_downloads: int = 0
    large_files: int = 0
    duplicate_groups: int = 0
    empty_dirs: int = 0
    stale_project_dirs: int = 0
    reclaimable_mb: float = 0.0

    @field_validator("reclaimable_mb", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0.0 if v is None else v


class FileTrendForecast(Contract):
    """The ``forecast`` block of GET /api/files/trends.

    With fewer than two scans the backend returns
    ``{"insufficient_data": true}`` and nothing else.
    """

    insufficient_data: bool = False
    growth_rate_mb_per_day: float = 0.0
    current_reclaimable_mb: float = 0.0
    data_points: int = 0
    projected_milestones: dict[str, str] = Field(default_factory=dict)

    @field_validator("projected_milestones", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


class FileTrendsResponse(Contract):
    """GET /api/files/trends."""

    scans: list[FileTrendScan] = Field(default_factory=list)
    count: int = 0
    forecast: FileTrendForecast = Field(default_factory=FileTrendForecast)

    @field_validator("forecast", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "scans")


class CleanResultResponse(Contract):
    """POST /api/files/clean/stale-caches."""

    status: str = ""
    message: str = ""
    removed_caches: int = 0
    removed_empty_dirs: int = 0
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("details", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


class ProjectHistoryPoint(Contract):
    """One point of the ``history`` list from GET /api/projects/{name}."""

    health_score: int = 0
    scanned_at: str | None = None

    @field_validator("health_score", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class ProjectDetailResponse(Contract):
    """GET /api/projects/{name} — latest snapshot plus score history.

    ``history`` arrives newest-first (the router orders by
    ``scanned_at DESC``); consumers that plot it must reverse.
    """

    name: str = ""
    current: dict[str, Any] = Field(default_factory=dict)
    history: list[ProjectHistoryPoint] = Field(default_factory=list)

    @field_validator("current", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


# ─────────────────────────────────────────────────────────────────────
# Session 20 additions — branch hygiene
#
# POST /api/projects/{name}/branches/prune returns the same manifest
# whether it ran as a dry run or for real, so a client can preview and
# then confirm against an identical shape.  Enforced server-side with
# ``response_model=``.
#
# Keep this whole block together — it is appended, never interleaved.
# ─────────────────────────────────────────────────────────────────────


class BranchInfo(Contract):
    """One local branch considered by a prune, acted on or not.

    ``status`` is ``planned`` (would be / was eligible), ``deleted``,
    ``skipped`` (ineligible — ``reason`` says why) or ``failed``.
    ``last_commit_sha`` is recorded so a deletion stays recoverable with
    ``git branch <name> <sha>`` while the commit is still in the reflog.
    """

    name: str = ""
    last_commit_at: str | None = None
    last_commit_sha: str = ""
    days_stale: int = 0
    merged: bool = False
    upstream: str | None = None
    ahead: int | None = 0
    status: str = "skipped"
    reason: str = ""


class BranchCleanupResponse(Contract):
    """POST /api/projects/{name}/branches/prune.

    ``default_branch`` empty means it could not be determined; in that
    case nothing is ever planned, because "merged" has no meaning
    without it.
    """

    project: str = ""
    repo_path: str = ""
    default_branch: str = ""
    dry_run: bool = True
    stale_days: int = 0
    max_deletions: int = 0
    include_unmerged: bool = False
    branches: list[BranchInfo] = Field(default_factory=list)
    total_branches: int = 0
    planned_count: int = 0
    deleted_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    truncated: bool = False  # the max_deletions cap bit
    message: str = ""
