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


# ── /api/logs/trends ─────────────────────────────────────────────────


class LogSignatureTrendInfo(Contract):
    """One fault signature across the current and previous windows.

    ``alert_title`` is carried so a reader can match this row against the
    ``alerts`` table without re-deriving the identity — the signature
    lives in the alert title by ``log_signature``'s rule 2, and repeating
    the derivation here would be a second implementation of it.
    """

    signature: str = ""
    alert_title: str = ""
    source: str = ""
    severity: str = "info"
    sample: str = ""
    current: int = 0
    previous: int = 0
    total: int = 0
    first_seen: str | None = None
    last_seen: str | None = None
    # new | returned | surged | rising | steady | falling | gone
    change: str = "steady"
    #: ``None`` when either window is too thin for a ratio to mean
    #: anything, which is a different statement from ``1.0``.
    ratio: float | None = None

    @field_validator("current", "previous", "total", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class LogSourceTrendInfo(Contract):
    """Per-source volume.

    Errors and warnings stay separate: a source whose warnings doubled
    while its errors vanished has not "got worse by 50 %", and one
    number cannot say so.
    """

    source: str = ""
    current_errors: int = 0
    previous_errors: int = 0
    current_warnings: int = 0
    previous_warnings: int = 0
    error_delta: int = 0
    signatures: int = 0
    new_signatures: int = 0

    @field_validator(
        "current_errors",
        "previous_errors",
        "current_warnings",
        "previous_warnings",
        "error_delta",
        "signatures",
        "new_signatures",
        mode="before",
    )
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class LogTrendCoverageInfo(Contract):
    """How much of the period the agent actually observed.

    ``runs_truncated`` is the decisive field and ``runs_observed`` the
    suspicious one — a missed poll normally costs nothing, because the
    journal cursor resumes where it stopped.

    ``truncated_fraction`` is ``runs_truncated / runs_instrumented``, and
    the second denominator is carried beside it because it is **not**
    ``runs_observed``: only runs that recorded
    ``details['truncated_sources']`` could have reported truncation, and
    on this box that field starts on 2026-08-12.  A consumer computing
    the ratio from ``runs_observed`` gets a number 2.5x too small.
    """

    runs_observed: int = 0
    runs_expected: int = 0
    runs_truncated: int = 0
    runs_instrumented: int = 0
    fraction: float = 0.0
    truncated_fraction: float = 0.0


class LogTrendsResponse(Contract):
    """GET /api/logs/trends.

    ``truncated`` says the grouped query hit its cap, so the rankings are
    over a subset — ``ports_checked``'s rule, because zero new
    signatures because clean must not read the same as zero because
    blind.
    """

    window_days: int = 7
    window_start: str | None = None
    previous_start: str | None = None
    generated_at: str | None = None
    confidence: str = "low"
    signatures: list[LogSignatureTrendInfo] = Field(default_factory=list)
    sources: list[LogSourceTrendInfo] = Field(default_factory=list)
    new_signatures: list[LogSignatureTrendInfo] = Field(default_factory=list)
    coverage: LogTrendCoverageInfo = Field(default_factory=LogTrendCoverageInfo)
    truncated: bool = False
    groups_read: int = 0
    count: int = 0

    @field_validator("coverage", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "signatures")


# ── /api/logs/actions ────────────────────────────────────────────────


class LogIncidentMemberInfo(Contract):
    """One signature an incident row stands for.

    Present only on the roll-up rows ``SNAG-LOG-001`` introduced, and it
    is what keeps that roll-up legitimate: a collapsed row must **name**
    every signature it swallowed, never merely count them
    (``SNAG-ESTATE-001``).  A consumer that ignores this field still sees
    a correct row about the fault that happened first, because
    ``LogRecommendationInfo``'s own ``source``/``signature`` stay the
    anchor's.
    """

    source: str = ""
    signature: str = ""
    alert_title: str = ""
    occurrences: int = 0


class LogRecommendationInfo(Contract):
    """One ranked, executable piece of log advice.

    A third sibling of ``RecommendationInfo`` (health-score points) and
    ``FileRecommendationInfo`` (reclaimable megabytes), with its own
    currency again: ``occurrences``.  One ``points`` field meaning three
    units decided by the producer would be unreadable at the call site,
    which is the argument ``FileRecommendationInfo`` already makes.

    ``snippet`` is populated only for the kind whose remedy *is* a config
    edit.  A row without one never tells the reader to paste anything —
    Session 48's rule, learned from a row promising an absent snippet
    that no execution sitting could close.
    """

    # new_signature | surge | noise
    kind: str = ""
    # risk | advice
    severity: str = "advice"
    title: str = ""
    detail: str = ""
    action: str = ""
    source: str = ""
    signature: str = ""
    alert_title: str = ""
    occurrences: int = 0
    snippet: str | None = None
    #: Every signature this row covers when it is an incident roll-up,
    #: ordered by first sighting so the anchor is first.  Empty on the
    #: ordinary one-signature rows.
    members: list[LogIncidentMemberInfo] = Field(default_factory=list)

    @field_validator("occurrences", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class LogActionsResponse(Contract):
    """GET /api/logs/actions.

    ``confidence`` is echoed from the trend it was computed off, because
    every ``noise`` row is an argument from a count and a consumer acting
    on one needs to know how complete that count is.
    """

    recommendations: list[LogRecommendationInfo] = Field(default_factory=list)
    count: int = 0
    confidence: str = "low"
    window_days: int = 7
    generated_at: str | None = None
    #: Pairs already declared in ``agents.log_aggregator.known_noise``,
    #: reported so "nothing to do" can be told apart from "everything is
    #: already silenced".
    declared_noise: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "recommendations")


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
    #: ``str(e)`` from the newest failed run, or None when the streak is
    #: 0. Carried so the alert message can name the fault rather than
    #: only counting it — the full text stays in ``agent_runs.details``.
    last_error: str | None = None
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


class ReloadResponse(Contract):
    """POST /api/sysadmin/reload — what the reload did and could not do.

    Answered **200 whatever the outcome**, with ``ok`` carrying it. An
    invalid config.yaml is an operator's typo, not a server fault, and a
    4xx would make a client discard the body — which is the whole product
    here. Same rule as ``GET /api/projects/next`` returning 200 with a null
    project rather than 404: a status code that collapses two meanings
    costs more than it saves.

    ``ok: false`` means **nothing** was installed. The two files are
    validated before either is swapped, so a refusal leaves the running
    configuration untouched rather than half-replaced.

    ``requires_restart`` is the honest half: fields that changed in
    config.yaml and are read once, at startup — the socket, the logging
    setup and the engine. Everything an agent reads is re-read per run and
    is live the moment this returns. A reader who ignores this list is
    running a config.yaml the process is not fully obeying, which is
    precisely what the field exists to prevent.

    The scheduler's triggers used to be on that list, and taking them off
    it is Session 50 (``SNAG-RELOAD-001``): a reload now re-times the
    running jobs rather than reporting, once, that it had not. ``ok: true``
    with an empty ``requires_restart`` is therefore the ordinary outcome
    rather than the lucky one.

    ``jobs_synced`` is the field a reader must not skip past.
    ``jobs_retimed: []`` means "nothing needed re-timing" when it is true
    and "the scheduler was never looked at" when it is false — the same
    distinction ``UnitScanResponse.ports_checked`` draws between
    zero-because-clean and zero-because-blind.
    """

    ok: bool = False
    reloaded_at: str | None = None  # ISO-8601, like every other stamp here
    error: str | None = None
    requires_restart: list[str] = Field(default_factory=list)
    services_total: int = 0
    services_added: list[str] = Field(default_factory=list)
    services_removed: list[str] = Field(default_factory=list)
    services_changed: list[str] = Field(default_factory=list)
    #: Agent name -> service/source names whose in-memory state was
    #: dropped. Names rather than a count: which one lost its resume
    #: cursor or its degraded streak is what decides whether it matters.
    pruned: dict[str, list[str]] = Field(default_factory=dict)
    #: Whether the running scheduler was reconciled with the new config.
    #: Read this before reading the three lists below.
    jobs_synced: bool = False
    #: Scheduled jobs added, unscheduled, and re-timed. A job whose trigger
    #: did not move is in none of them, and was deliberately left alone:
    #: re-timing recomputes the next fire from now, so re-applying an
    #: identical trigger would postpone every job on every reload.
    jobs_added: list[str] = Field(default_factory=list)
    jobs_removed: list[str] = Field(default_factory=list)
    jobs_retimed: list[str] = Field(default_factory=list)


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


class FileRecommendationInfo(Contract):
    """One actionable filesystem finding.

    Deliberately *not* a :class:`RecommendationInfo`.  That model's
    ``points`` means "health score recovered"; the file organiser has no
    score, and its currency is disk space.  Overloading one field with
    two units decided by the producer would make ``points`` unreadable
    at the call site, so this is a separate model with an honest name.

    ``reclaimable_mb`` is 0.0 for tidiness items — moving a misplaced
    file or removing an empty directory frees no space — so those rank
    below anything with real megabytes behind it.  ``item_count`` is
    what tidiness items are judged on instead.

    ``severity`` is ``advice`` or ``risk``.  The one risk is a projected
    disk-threshold crossing: it reclaims nothing by itself but ranks
    above every byte total, mirroring how ``no_remote`` outranks score
    arithmetic in the project recommendations.
    """

    # risk | duplicates | downloads | stale_caches | large_files
    # | misplaced | empty_dirs | similar_folders
    kind: str = ""
    severity: str = "advice"
    title: str = ""
    detail: str = ""
    reclaimable_mb: float = 0.0
    item_count: int = 0
    action: str = ""

    @field_validator("reclaimable_mb", mode="before")
    @classmethod
    def _none_to_zero_float(cls, v: Any) -> Any:
        return 0.0 if v is None else v

    @field_validator("item_count", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class DiskThresholdInfo(Contract):
    """A projected disk-usage threshold crossing.

    ``state`` is ``projected`` (a date was computed), ``exceeded`` (the
    latest reading is already past it) or ``not_growing`` (flat or
    shrinking).  ``days_from_now``/``date`` are set only when
    ``projected``.
    """

    percent: float = 0.0
    state: str = ""
    days_from_now: float | None = None
    date: str | None = None


class FileActionsResponse(Contract):
    """GET /api/files/actions — top disk wins across the scan root.

    Ranked risk-first, then by reclaimable megabytes, then by item
    count.  ``count`` is what was returned after ``limit``,
    ``total_available`` what existed before it.

    ``disk_forecast`` is the soonest projected threshold crossing from
    ``resource_snapshots`` — a different table from the audit, because
    junk accumulation and disk occupancy are different series and only
    the latter answers "when does the disk fill up".  ``None`` when
    there is too little history to fit a line.
    """

    actions: list[FileRecommendationInfo] = Field(default_factory=list)
    count: int = 0
    total_available: int = 0
    total_reclaimable_mb: float = 0.0
    scanned_at: str | None = None
    disk_forecast: DiskThresholdInfo | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "actions")


class DiskReviewResponse(Contract):
    """GET /api/files/review — the latest stored weekly disk review.

    Same shape as :class:`ProjectReviewResponse` but a distinct model,
    matching the distinct table: the two reviews answer different
    questions and their ``stats`` blobs share no keys.

    ``llm_used`` False means llama-server was unavailable and
    ``narrative`` is the deterministic digest, not prose.  ``stats`` is
    the structured input the narrative was written from — occupancy
    delta, audit deltas and per-kind reclaim.
    """

    generated_at: str | None = None
    period_days: int = 7
    narrative: str = ""
    llm_used: bool = False
    model_used: str | None = None
    stats: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stats", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


class LogReviewResponse(Contract):
    """GET /api/logs/review — the latest stored weekly log review.

    A distinct model matching a distinct table, the call
    :class:`DiskReviewResponse` already made for the same reason: the
    three reviews answer different questions and their ``stats`` blobs
    share no keys.

    It carries one field its two siblings do not.  ``confidence`` is the
    trend report's own verdict on how much of the window was actually
    read, and it is promoted out of ``stats`` because a consumer decides
    whether to *show* the review on it — a narrative written across a
    truncated window reads exactly like one that was not, so the
    qualifier must be as reachable as the prose.  ``ports_checked``'s
    rule, fourth outing.

    ``llm_used`` False means llama-server was unavailable and
    ``narrative`` is the deterministic digest, not prose.
    """

    generated_at: str | None = None
    period_days: int = 7
    narrative: str = ""
    llm_used: bool = False
    model_used: str | None = None
    confidence: str = "high"
    stats: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stats", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


class HealthReviewResponse(Contract):
    """GET /api/sysadmin/review — the latest stored weekly system health review.

    The **third** review model matching the third review table, the call
    :class:`DiskReviewResponse` and :class:`LogReviewResponse` already
    made for the same reason: the reviews answer different questions and
    their ``stats`` blobs share no keys.

    It carries ``confidence`` for :class:`LogReviewResponse`'s reason,
    sharpened by what this review is made of.  Every headline figure here
    is a comparison of two windows, and ``confidence`` says whether the
    monitor watched enough of *this* one to describe it at all.  The
    companion fact — whether the two windows were watched *equally*, and
    so whether the week-on-week figures mean anything — lives at
    ``stats["comparable"]`` rather than being promoted alongside it,
    because a consumer that shows or hides the review decides on the
    first and a consumer reading the prose is already told the second in
    words.

    ``llm_used`` False means llama-server was unavailable and
    ``narrative`` is the deterministic digest, not prose.
    """

    generated_at: str | None = None
    period_days: int = 7
    narrative: str = ""
    llm_used: bool = False
    model_used: str | None = None
    confidence: str = "high"
    stats: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stats", mode="before")
    @classmethod
    def _none_to_empty(cls, v: Any) -> Any:
        return {} if v is None else v


class ProjectHistoryPoint(Contract):
    """One point of the ``history`` list from GET /api/projects/{name}.

    Carries the *narrative* state as well as the score.  The organiser has
    written the whole roadmap findings block into ``project_snapshots``
    since Session 28 (2026-08-06) and nothing read it back: ninety days of
    next actions sat in JSONB with no endpoint over them, which is why
    Session 32's start-versus-finish accounting was recorded as blocked on
    a document format when the data already existed.

    ``next_action`` is ``None`` on snapshots taken before 2026-08-06, and
    on any project whose scan resolved no next action at all.  The two
    cases are indistinguishable here on purpose — both mean "this point
    cannot tell you what was next".
    """

    health_score: int = 0
    scanned_at: str | None = None
    next_action: str | None = None
    next_action_source: str | None = None
    #: Whether ``next_action`` differs from the *older* neighbouring point.
    #: ``True`` marks a finish (work moved on), a run of ``False`` measures
    #: how long one action stayed open.  ``None`` on the oldest point in
    #: the window, where there is nothing to compare against — that is
    #: "not knowable from this response", **not** "unchanged", and a
    #: consumer that renders it as unchanged will report a false streak
    #: every time the window slides.
    next_action_changed: bool | None = None

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


# ── Service discovery (Session 26) ───────────────────────────────────


class UnitFindingInfo(Contract):
    """One installed systemd unit that is broken, unwired or undocumented.

    ``category`` is ``orphaned`` (the unit's own declared path is gone,
    so systemd fails its start job), ``unmonitored`` (maps to a live
    project, no services.yaml entry watches it) or
    ``host`` (hand-written, maps to no project — real infrastructure with
    nothing watching it).  Units that are already monitored are counted,
    never listed: a list of things that are fine is noise every reader
    has to filter.

    ``scope`` is part of a unit's identity, not decoration.
    ``deadlock-api-ingest.service`` is installed as *both* a user unit and
    a system unit here, running two different binaries; wiring one says
    nothing about the other.

    ``monitor_unit`` differs from ``unit`` for a ``Type=oneshot`` service
    that has a timer.  A oneshot is ``inactive (dead)`` between runs by
    design, so monitoring the service alerts continuously — the timer is
    what stays active while armed.  The finding is reported under the
    service (which holds the paths and description) with the timer named
    here.

    ``enabled``, ``restart`` and ``restart_bounded`` say whether the unit
    is merely *installed* or actually *running*, which is the difference
    SNAG-ESTATE-001 turned on: an orphan nothing starts is debt, and an
    orphan systemd starts is a fault in progress.  ``armed`` is the pair
    of them (``category == "orphaned" and enabled``) and is the only
    field the agent alerts on per-unit.

    ``restart_bounded`` is **arithmetic, not the presence of a
    setting**: false means the unit's ``RestartSec`` is wide enough that
    ``StartLimitBurst`` starts can never fit inside
    ``StartLimitIntervalSec``, so a crash loop never reaches ``failed``,
    no ``OnFailure=`` can fire, and ``systemctl is-failed`` reports
    nothing wrong.  ``true`` is also what a unit that does not restart
    at all reports, and what an unreadable value reports — not knowing
    is not an accusation.
    """

    unit: str = ""
    scope: str = "system"  # user | system
    category: str = "host"  # orphaned | unmonitored | host
    path: str = ""
    description: str | None = None
    project: str | None = None
    project_path: str | None = None
    matched_by: str | None = None  # path | name | None
    monitor_unit: str = ""
    enabled: bool = False
    restart: str | None = None
    restart_bounded: bool = True
    #: The inputs to ``restart_bounded``, ``null`` where the unit
    #: declares nothing and systemd's manager default applies
    #: (``RestartSec=100ms``, ``StartLimitIntervalSec=10s``,
    #: ``StartLimitBurst=5``).  Present so a consumer can check the
    #: verdict rather than take it: the boolean is the conclusion of an
    #: arithmetic the naive reading gets wrong in both directions.
    restart_sec: float | None = None
    start_limit_interval: float | None = None
    start_limit_burst: int | None = None
    armed: bool = False
    dead_path: str | None = None
    manual: bool = False
    reason: str = ""


class UnitRecommendationInfo(Contract):
    """One actionable service-discovery finding.

    Deliberately carries **no score or size field**, unlike
    :class:`RecommendationInfo` (health-score points) and
    :class:`FileRecommendationInfo` (reclaimable megabytes).  Both of
    those rank by something directly measurable; there is no equivalent
    here, and nothing makes two host units meaningfully "twice" one
    orphan.  Ranking is by ``kind`` alone — ``orphan``, then ``restart``,
    then ``unmonitored``, then ``host``.

    ``snippet`` is ready-to-paste text and ``snippet_target`` names the
    file it belongs in — services.yaml for anything being wired up, and
    the **absolute path of the unit file** for a ``restart`` finding,
    which is the one kind whose fix is not a config edit here.  It is
    text for a human either way: the YAML is hand-curated and its
    comments carry reasoning, and the unit file usually belongs to
    another repository.  Nothing in this service ever writes to either.
    An empty ``snippet`` with a null ``snippet_target`` means there is
    nothing to paste — an orphan (remove it instead), a hand-started
    oneshot with no steady state to check, or a restart cadence so wide
    that no window would fix it.
    """

    kind: str = ""  # orphan | restart | unmonitored | host
    severity: str = "advice"  # risk (orphan) | advice
    unit: str = ""
    scope: str = "system"
    project: str | None = None
    monitor_unit: str = ""
    title: str = ""
    detail: str = ""
    action: str = ""
    snippet: str = ""
    snippet_target: str | None = None  # projects.yaml | config.yaml | None


class UnitScanSummary(Contract):
    """The arithmetic of one sweep.

    ``units_scanned`` equals ``monitored + timers_folded + orphaned +
    unmonitored + host``.  The buckets are exhaustive on purpose: a count
    that sums is one a reader can audit, and the first version of this
    scan reported 20 monitored where the truth was 12 precisely because
    it inferred the number instead of adding it up.

    ``units_excluded`` counts distro-owned and template units filtered
    out before classification.  Reported rather than dropped silently, so
    "we looked at 44 and skipped 6" stays checkable.

    ``armed`` is a **subset of ``orphaned``**, not a sixth bucket, and is
    therefore excluded from the sum above deliberately — adding it would
    break the one arithmetic property this model exists to make
    auditable.  It counts the orphans systemd will actually start, each
    of which has its own alert row.

    ``port_findings`` and ``port_collisions`` are not units at all and
    are the third thing here outside the sum: they count *ports* where
    the box and the estate's registry disagree (Session 26c).
    ``port_collisions`` is a subset of ``port_findings`` — the live half
    (a ``services.yaml`` entry naming a unit that does not hold the port
    it checks, or two units on one port), each of which has its own
    alert row.  The remainder is registry advice under
    ``GET /api/units/actions``.

    ``ports_checked`` is **false when the check could not run** — ``ss``
    missing, or the port check disabled — and both counts are then zero
    for a reason that is not "nothing is wrong".  Reported as its own
    field rather than left to be inferred, because a zero that means
    "clean" and a zero that means "did not look" are the pair this
    repository keeps filing snags about.

    ``restart_unbounded`` is the same shape for the same reason and cuts
    across the buckets rather than sitting beside them: on this box 11 of
    its 13 members are ``monitored``, which is precisely the bucket
    ``findings`` never lists.  It counts units whose crash loop can never
    reach ``failed`` (SNAG-UNITS-002).  **Orphans are excluded from it**
    — their advice is "remove the unit", and a start limit on a file you
    should delete is a contradiction, so the number is smaller than a
    naive sweep of the box would give.  The units themselves are named
    only by ``GET /api/units/actions``; this endpoint gives the count.
    """

    units_scanned: int = 0
    units_excluded: int = 0
    monitored: int = 0
    timers_folded: int = 0
    orphaned: int = 0
    unmonitored: int = 0
    host: int = 0
    armed: int = 0
    restart_unbounded: int = 0
    port_findings: int = 0
    port_collisions: int = 0
    ports_checked: bool = False


class UnitScanResponse(Contract):
    """GET /api/units/status — the latest stored unit sweep."""

    scanned_at: str | None = None
    summary: UnitScanSummary = Field(default_factory=UnitScanSummary)
    findings: list[UnitFindingInfo] = Field(default_factory=list)
    count: int = 0
    #: Unit names installed in both scopes — two units, one name, two
    #: different binaries.  Named explicitly so the pair does not read as
    #: one item reported twice.
    duplicate_units: list[str] = Field(default_factory=list)


class UnitActionsResponse(Contract):
    """GET /api/units/actions — ranked service-discovery advice."""

    scanned_at: str | None = None
    recommendations: list[UnitRecommendationInfo] = Field(default_factory=list)
    count: int = 0
    total_available: int = 0
    #: How many were dropped by ``limit``, keyed by ``kind``.  Without it
    #: a saturated list looks like "that is all there is" — the failure
    #: /api/projects/actions hit in Session 28.
    dropped_by_kind: dict[str, int] = Field(default_factory=dict)


# ── Service reliability (Session 25) ──────────────────────────────────


class ReliabilityDeduction(Contract):
    """One attributable subtraction from a service's reliability score.

    ``kind`` is ``downtime`` ("it was not there") or ``instability``
    ("it keeps bouncing").  They are separate because they are separate
    failures: retry logic survives one long outage and dies on three
    short ones, so a service that dropped out repeatedly must not outrank
    one that dropped out once for longer merely because it was up more of
    the time.

    ``waived`` deductions were computed and are reported, but were not
    applied — an expected-down service (``mute: true``) is scored rather
    than skipped, so the reader can still see what it would have cost.
    """

    kind: str = ""  # downtime | instability
    points: int = 0
    detail: str = ""
    waived: bool = False


class ServiceReliabilityInfo(Contract):
    """One service's reliability over the scoring window.

    ``coverage_percent`` and ``confidence`` are the honesty fields.  A
    gap in the check series means the *monitor* was down, not the
    service, so it never costs ``score`` — it lowers ``confidence``
    instead.  A consumer ranking by ``score`` alone will therefore put a
    thinly-observed service alongside a well-observed one; anything that
    recommends action off the back of this must read ``confidence`` too.
    """

    service: str = ""
    score: int = 100
    grade: str = "reliable"  # reliable | degraded | unreliable | failing

    uptime_percent: float = 100.0
    checks_recorded: int = 0
    #: Recorded checks minus unmeasurable ones — the denominator of every
    #: rate here.  An ``error`` check means the check itself failed, so
    #: the service's state is unknown rather than bad.
    checks_measured: int = 0
    failed_checks: int = 0
    error_checks: int = 0
    #: Checks ``services.yaml`` declared away with ``monitor: false``.
    #: Excluded from every rate here alongside ``error_checks`` and
    #: counted apart from them, because "the check failed" and "nobody
    #: looked, by choice" are different claims about the same absence.
    #: Until 2026-08-25 these were scored as **outages**, which put three
    #: declared-unmonitored services on this box at ``failing`` / 35.
    skipped_checks: int = 0
    #: Runs of consecutive failing checks, not failing checks.  One
    #: outage is one episode however long it lasts.
    outage_episodes: int = 0
    longest_outage_minutes: float = 0.0
    #: ``None`` below two episodes — one incident establishes no interval.
    mean_hours_between_incidents: float | None = None

    checks_expected: int = 0
    coverage_percent: float = 0.0
    observed_days: float = 0.0
    confidence: str = "high"  # high | low
    confidence_reason: str | None = None

    window_days: int = 7
    window_start: str | None = None
    first_check_at: str | None = None
    last_check_at: str | None = None
    muted: bool = False
    waived_points: int = 0
    deductions: list[ReliabilityDeduction] = Field(default_factory=list)


class ReliabilitySummary(Contract):
    """Estate-level totals for one reliability computation.

    ``services_scored`` counts every configured service, including those
    with no checks at all — a configured service the monitor has never
    reached is the most important row on the page, not an absence.
    """

    services_scored: int = 0
    reliable: int = 0
    degraded: int = 0
    unreliable: int = 0
    failing: int = 0
    #: Scores built on a thin or gappy window.  Reported separately
    #: because "nothing is wrong" and "we cannot yet tell" are different
    #: answers and must not average into one number.
    low_confidence: int = 0
    #: Mean score across services, low-confidence ones included.  A blunt
    #: instrument, kept because a single trendable figure is what a
    #: weekly review needs; per-service scores are where the meaning is.
    mean_score: float = 100.0


class ReliabilityResponse(Contract):
    """GET /api/services/reliability — computed live, worst service first."""

    computed_at: str | None = None
    window_days: int = 7
    summary: ReliabilitySummary = Field(default_factory=ReliabilitySummary)
    services: list[ServiceReliabilityInfo] = Field(default_factory=list)
    count: int = 0


# ── /api/services/actions (Session 25, Tier 2) ────────────────────────


class ServiceRecommendationInfo(Contract):
    """One ranked, executable piece of service-reliability advice.

    The **fourth** sibling, and the fourth currency.  ``points`` in the
    project recommendations meant health score, ``reclaimable_mb`` means
    megabytes, ``occurrences`` means log lines, and this means
    reliability points.  One field whose unit is decided by the producer
    is unreadable at the call site — the argument
    ``FileRecommendationInfo`` made and ``LogRecommendationInfo``
    repeated — so this is its own model rather than a reuse of the
    ``RecommendationInfo`` that was deleted with the project routes on
    2026-08-25 (``SNAG-DOCS-002``).

    ``recoverable_points`` differs from its siblings in **tense**, which
    is the thing most likely to be misread.  Reclaimable megabytes are
    freed the moment the duplicate is deleted; reliability points are
    charged for failures already inside the window and lapse only as
    those failures age out of it.  So this is what stops being deducted
    once a fix has held for ``window_days`` — a forecast, not a payoff —
    and every ``detail`` on a points-bearing row says so in words rather
    than leaving the reader to infer the tense from a number.

    Rows that map to no deduction carry ``0`` and rank beneath anything
    with real points, exactly as tidiness items rank beneath reclaimable
    megabytes.  No figure is invented to make the two tiers comparable.

    ``evidence`` is the field the confidence gate turns on, and it is
    reported rather than kept private because a consumer needs to know
    which kind of claim it is reading:

    ``event``
        An observed failure.  A gap in the check series can only have
        hidden more of them, so the count is a floor and the row is
        produced at any ``confidence``.
    ``rate`` / ``absence``
        A per-window rate, or a thing not happening.  A gappy window
        makes the first meaningless and the second indistinguishable
        from nobody looking, so these rows appear only at
        ``confidence: high``.

    ``confidence`` is echoed from the score this row was computed off,
    for the reason ``LogActionsResponse`` echoes its own: every row here
    is an argument from recorded checks, and a consumer acting on one
    needs to know how complete that record is.  ``ServiceReliabilityInfo``
    says in writing that anything recommending action off it must read
    ``confidence``; this is that field, carried through.
    """

    # outage | flapping | timer_failed | timer_stale | check_interval
    kind: str = ""
    # risk | advice
    severity: str = "advice"
    service: str = ""
    title: str = ""
    detail: str = ""
    action: str = ""
    #: Deduction points that lapse once the fix has held for a full
    #: window.  0 for rows that map to no deduction.
    recoverable_points: int = 0
    #: The scorer's own band for this service — never a second threshold
    #: computed here, so a service is judged unreliable in one place.
    grade: str = "reliable"
    confidence: str = "high"  # high | low
    outage_episodes: int = 0
    # event | rate | absence
    evidence: str = "event"

    @field_validator("recoverable_points", "outage_episodes", mode="before")
    @classmethod
    def _none_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class ServiceActionsResponse(Contract):
    """GET /api/services/actions — ranked service-reliability advice.

    Three counts sit beside the list because an empty one is ambiguous
    in three directions, and a consumer that cannot tell them apart will
    read the worst case as the best.  ``muted_skipped`` is
    ``LogActionsResponse.declared_noise``'s rule — "nothing to do" must
    be distinguishable from "everything is already declared expected-down".
    ``suppressed_by_confidence`` is ``ports_checked``'s — a window too
    gappy to support a rate must not serve zero rows as though it had
    looked and found nothing.

    ``window_days`` and ``computed_at`` come from the same live
    computation ``GET /api/services/reliability`` serves; nothing is read
    back from ``reliability_scores``, so the advice and the score can
    never disagree about the window they describe.
    """

    computed_at: str | None = None
    window_days: int = 7
    recommendations: list[ServiceRecommendationInfo] = Field(default_factory=list)
    count: int = 0
    total_available: int = 0
    total_recoverable_points: int = 0
    #: Services scored but declared expected-down, so never advised on.
    muted_skipped: int = 0
    #: Rate- and absence-argued rows withheld because their service's
    #: window was too gappy to support the claim.
    suppressed_by_confidence: int = 0
    #: Services actually considered — scored, minus muted.
    services_considered: int = 0

    @model_validator(mode="before")
    @classmethod
    def _default_count(cls, data: Any) -> Any:
        return _fill_count(data, "recommendations")
