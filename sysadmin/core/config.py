"""Configuration loader — YAML file validated through Pydantic models."""

import logging
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from sysadmin.core.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT

logger = logging.getLogger(__name__)


# --- Nested config sections ---


class ApiConfig(BaseModel):
    """API authentication settings.

    ``auth_token`` unset/empty → auth disabled (backwards compatible);
    a warning is logged at startup.  When set, state-changing endpoints
    require ``Authorization: Bearer <token>``.
    """

    auth_token: str | None = None


class ServiceConfig(BaseModel):
    name: str = "sysadmin-service"
    port: int = DEFAULT_API_PORT
    host: str = DEFAULT_API_HOST
    log_level: str = "info"
    log_format: str = "json"  # json | text
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://gaddi@localhost:5432/projects"
    sync_url: str = "postgresql+psycopg2://gaddi@localhost:5432/projects"
    schema_: str = Field(default="sysadmin", alias="schema")

    model_config = {"populate_by_name": True}


class PersonalAssistantConfig(BaseModel):
    """Outbound integration with the PersonalAssistant app (retired 2026-07-24).

    PA is gone and Alfred, its replacement, exposes no inbox — no
    notification, briefing or digest endpoint.  Setting ``enabled: false``
    (as config.yaml now does) makes :class:`~sysadmin.monitor.notifier.Notifier`
    skip both the morning-briefing POST and the v2 notification sends
    without emitting a warning or an alert per attempt.

    The default stays ``True`` so a config predating this flag behaves
    exactly as before.  The code and its tests are kept deliberately: this
    is a dormant feature flag, not a deletion, so it can be repointed at
    Alfred if Alfred ever grows an inbox.
    """

    enabled: bool = True
    url: str = "http://localhost:8000"
    api_prefix: str = "/api"
    notify_endpoint: str = "/api/v2/notifications/send"
    briefing_endpoint: str = "/api/v2/intelligence/briefing/data"


class LLMConfig(BaseModel):
    """llama.cpp (llama-server) settings — OpenAI-compatible API.

    llama-server serves a single loaded model, so ``model`` is largely
    informational (recorded with summaries, passed through in requests).
    """

    url: str = "http://localhost:8081"
    model: str = "dria-agent-a-3b.Q4_K_M.gguf"
    timeout_seconds: float = 120.0


# --- Agent sub-configs ---


class Thresholds(BaseModel):
    disk_warning_percent: int = 80
    disk_critical_percent: int = 90
    ram_warning_percent: int = 85
    cpu_sustained_percent: int = 90
    cpu_sustained_minutes: int = 10
    gpu_temp_warning_c: int = 90
    gpu_vram_warning_percent: int = 90


class AnomalyConfig(BaseModel):
    """Z-score anomaly detection over ``resource_snapshots`` history.

    Complements the fixed :class:`Thresholds` — flags values that are
    unusual *for this machine* even when they sit below a hard limit.

    - ``window_days``   — how much history the rolling mean/stdev uses
    - ``min_samples``   — cold-start guard; fewer snapshots → no flagging
    - ``min_stdev``     — near-constant series would produce huge/infinite
      z-scores, so a series flatter than this is skipped entirely
    """

    enabled: bool = True
    window_days: int = 7
    z_threshold: float = 3.0
    min_samples: int = 30
    min_stdev: float = 1.0
    severity: str = "warning"


class ReliabilityGradeBands(BaseModel):
    """Score thresholds mapping a reliability score (0-100) to a grade.

    Set higher than :class:`HealthGradeBands` on purpose.  A repository
    scoring 80 is tidy enough; a service that was unavailable for a fifth
    of the week is not "healthy" by any reading, so the reliable band
    starts at 95 — roughly "no more than one bad check-run this week".
    """

    reliable_min: int = 95
    degraded_min: int = 85
    unreliable_min: int = 60


class ReliabilityConfig(BaseModel):
    """Per-service reliability scoring (Session 25, Tier 1).

    ``window_days`` is capped in practice by ``service_health``'s
    retention (30 days by default): a longer window silently narrows to
    however much history survives the nightly purge, so widening this
    means widening retention too.
    """

    enabled: bool = True
    window_days: int = 7
    grade_bands: ReliabilityGradeBands = Field(default_factory=ReliabilityGradeBands)


class SysAdminAgentConfig(BaseModel):
    """Monitoring agent settings.

    The service list is deliberately absent. Per-service topology lives in
    services.yaml, keyed by project id — see
    :mod:`sysadmin.monitor.services`. It was in two places before this
    (here and projects.yaml), which is how seven project units ended up
    filed under "sysadmin" with comments explaining why.
    """

    enabled: bool = True
    health_check_interval_seconds: int = 300
    thresholds: Thresholds = Field(default_factory=Thresholds)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    reliability: ReliabilityConfig = Field(default_factory=ReliabilityConfig)


class HealthGradeBands(BaseModel):
    """Score thresholds mapping ``health_score`` (0-100) to a grade.

    score >= healthy_min          → "healthy"
    score >= needs_attention_min  → "needs_attention"
    score >= neglected_min        → "neglected"
    otherwise                     → "abandoned"
    """

    healthy_min: int = 80
    needs_attention_min: int = 60
    neglected_min: int = 40


class BranchActionsConfig(BaseModel):
    """Stale-branch pruning (``POST /api/projects/{name}/branches/prune``).

    Deleting a branch can destroy unmerged work, so this mirrors the file
    actions' safety model: dry run unless the request says ``confirm``,
    and the genuinely dangerous case needs *two* flags.

    - ``enabled`` — master kill switch; false → the endpoint 409s
    - ``protected_branches`` — glob patterns never deleted, whatever their
      age or merge state (the detected default branch is protected too,
      even when it is not listed here)
    - ``allow_unmerged_delete`` — defence in depth.  A branch that is not
      an ancestor of the default branch is *reported only* unless the
      request sets ``include_unmerged: true`` **and** this flag is true
    - ``max_deletions`` — hard cap per call.  A request may ask for fewer,
      never for more
    - ``min_stale_days`` — floor on the staleness window a request may
      ask for, so ``stale_days: 0`` cannot sweep up today's work
    """

    enabled: bool = True
    protected_branches: list[str] = Field(
        default_factory=lambda: ["main", "master", "develop", "release/*"]
    )
    allow_unmerged_delete: bool = False
    max_deletions: int = 20
    min_stale_days: int = 7


class ProjectOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 6
    projects_root: str = "/home/gaddi/projects"
    # How deep discovery may look for project markers. 1 = the old
    # behaviour (immediate children of projects_root only); 2 lets a
    # *category* directory (one with no markers of its own, e.g. apps/)
    # hold projects.  Directories that ARE projects are never descended
    # into, whatever the depth — a repo's vendored sub-repos are its own
    # business.
    discovery_depth: int = 2
    stale_branch_days: int = 30
    track_todos: bool = True
    todo_patterns: list[str] = Field(
        default_factory=lambda: ["TODO", "FIXME", "HACK", "XXX"]
    )
    grade_bands: HealthGradeBands = Field(default_factory=HealthGradeBands)
    # Global health-score floor below which a project raises an alert.
    # A project may override this in projects.yaml (``alert_threshold``).
    alert_threshold: int = 40
    # Weekly LLM-narrated portfolio review (Session 23).  Generation
    # falls back to a deterministic digest when llama-server is down, so
    # disabling this stops the *schedule*, not just the inference.
    weekly_review: bool = True
    # Ceiling on the TODO/FIXME deduction (5 points per 10 markers).
    # Uncapped, a 300-TODO project pins at 0 forever and the score stops
    # reporting anything about the rest of its health.  ``None`` = no cap.
    max_todo_penalty: int | None = 30
    branch_actions: BranchActionsConfig = Field(default_factory=BranchActionsConfig)


class FileActionsConfig(BaseModel):
    """Mutating filesystem actions (``POST /api/files/organise``, ``/clean/*``).

    Every action defaults to a dry run; the caller must send ``confirm: true``
    to touch the filesystem.  These settings bound *what* an action may do:

    - ``enabled`` — master kill switch; false → every action endpoint 409s
    - ``category_folders`` — category → destination folder, relative to the
      agent's ``scan_root`` (absolute paths are also accepted).  Retarget a
      category here rather than in code.
    - ``allow_permanent_delete`` — defence in depth.  Deletion normally means
      "move to the XDG trash".  When the trash is unusable (e.g. the file is
      on another filesystem) the operation is *skipped* unless the request
      sets ``force_delete: true`` **and** this flag is true.
    - ``max_operations`` — hard cap on the size of a single action's manifest.
    """

    enabled: bool = True
    category_folders: dict[str, str] = Field(
        default_factory=lambda: {
            "images": "Pictures",
            "videos": "Videos",
            "documents": "Documents",
            "audio": "Music",
            "books": "Books",
            "archives": "Archives",
        }
    )
    downloads_dir: str = "Downloads"
    archive_dir: str = "Archives/Downloads"
    duplicate_strategy: str = "newest"  # newest | largest
    # PDF routing heuristic — see sysadmin/services/file_actions.py
    pdf_book_min_pages: int = 50
    pdf_book_min_mb: float = 5.0
    max_operations: int = 200
    allow_permanent_delete: bool = False
    # Freedesktop trash location. Empty → <scan_root>/.local/share/Trash,
    # the spec default for $XDG_DATA_HOME/Trash (no env vars are read).
    trash_dir: str | None = None
    # Code files sitting loose in the scan root are *flagged only*, never moved
    code_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".cpp",
            ".h", ".hpp", ".java", ".rb", ".sh", ".php", ".lua", ".sql",
        ]
    )


class FileOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 24
    scan_root: str = "/home/gaddi"
    output_dir: str = "/home/gaddi/Documents/DMDocs/Self/Briefings/Audits"
    stale_days: int = 180
    downloads_stale_days: int = 30
    large_file_mb: int = 100
    similarity_threshold: float = 0.75
    # Weekly LLM-narrated disk review (Session 24 Tier 3).  Generation
    # falls back to a deterministic digest when llama-server is down, so
    # disabling this stops the *schedule*, not just the inference.
    weekly_review: bool = True
    # Reclaimable-space milestones (MB) for the /api/files/trends forecast —
    # the endpoint projects the date each one will be reached
    reclaimable_milestones_mb: list[int] = Field(
        default_factory=lambda: [1024, 5120, 10240]
    )
    skip_dirs: list[str] = Field(
        default_factory=lambda: [
            ".git", ".cache", ".local", ".config", ".var",
            ".mozilla", ".steam", "node_modules", "__pycache__", ".venv",
        ]
    )
    actions: FileActionsConfig = Field(default_factory=FileActionsConfig)


class ServiceDiscoveryConfig(BaseModel):
    """Session 26 — cross-reference installed units against the estate.

    ``alert_threshold`` is a count of *actionable* findings (orphaned +
    unmonitored + host), and the alert it governs is a single rolled-up
    one, re-raised only when the count changes.  Per-unit alerts would
    repeat SNAG-AGENT-002.  Set to 0 to record findings and never alert
    — the Session 28 posture for a new detector whose first run lands
    twenty findings at once.
    """

    enabled: bool = True
    scan_interval_hours: int = 6
    user_unit_dir: str = "~/.config/systemd/user"
    # /etc/systemd/system only.  /usr/lib/systemd/system is the package
    # manager's territory and nothing there is ours to wire up; the
    # sweep additionally skips symlinks, which is how an *enabled* distro
    # unit appears in /etc.
    system_unit_dir: str = "/etc/systemd/system"
    alert_threshold: int = 5


class LogSource(BaseModel):
    name: str
    type: str  # journalctl | file
    unit: str | None = None
    user: bool = False  # journal of a *user* unit (journalctl --user)
    path: str | None = None
    severity_filter: str = "warning"


class LogAggregatorConfig(BaseModel):
    enabled: bool = True
    poll_interval_seconds: int = 60
    sources: list[LogSource] = Field(default_factory=list)
    retention_days: int = 30
    summarise_with_llm: bool = True


# --- Managed projects (projects.yaml) ---


class ProjectEndpointLog(BaseModel):
    """Log source config for a project endpoint.

    ``user`` selects ``journalctl --user`` for a *user* unit's journal.
    Left unset it inherits the owning :class:`ProjectEndpoint`'s ``user``,
    since an endpoint's unit and that unit's journal live in the same
    systemd scope in every realistic case.
    """

    type: str = "journalctl"
    unit: str | None = None
    user: bool | None = None
    path: str | None = None
    severity_filter: str = "warning"


class ProjectEndpoint(BaseModel):
    """A backend or frontend endpoint within a managed project.

    ``user`` marks ``systemd_unit`` as a *user* unit, so health checks,
    service actions and log reads use ``systemctl --user`` /
    ``journalctl --user``.  Without it a user unit looks permanently
    unknown to the system-scope ``systemctl``, which fails silently.
    """

    url: str | None = None
    port: int | None = None
    systemd_unit: str | None = None
    user: bool = False
    log: ProjectEndpointLog | None = None


class ManagedProject(BaseModel):
    """A project with associated endpoints and metadata."""

    name: str
    path: str | None = None
    backend: ProjectEndpoint | None = None
    frontend: ProjectEndpoint | None = None
    # Health-score floor for *this* project. Absent → the global
    # ``agents.project_organiser.alert_threshold``.  A long-lived archive
    # can be given 0 (never alert) and a flagship project 70.
    alert_threshold: int | None = None
    # Declared intent, which the organiser folds into scoring:
    # ``dormant`` — deliberately resting, staleness is not a defect;
    # ``archived`` — retired, git hygiene no longer matters and no alert
    # is raised unless an explicit ``alert_threshold`` says otherwise.
    # Absent → inferred: paths under <projects_root>/archive/ are
    # ``archived``, everything else is ``active``.
    status: Literal["active", "dormant", "archived"] | None = None

    # to_monitored_services / to_log_sources were removed with the
    # services.yaml move: this file no longer contributes anything to
    # monitoring. What remains — status and alert_threshold — is project
    # state, read by the organiser until Phase 4 retires the file.


class ProjectsConfig(BaseModel):
    """Root model for projects.yaml."""

    projects: list[ManagedProject] = Field(default_factory=list)

    def _setting_for(self, name: str, path: str | None, field: str):
        """The value of ``field`` for one scanned project, or None.

        The scanner names a project after its *directory* while
        projects.yaml names it however the user likes
        (``personal-assistant`` vs ``PersonalAssistant``), so matching
        tries three keys, most specific first:

        1. the resolved filesystem path,
        2. the managed project's ``name``,
        3. the basename of the managed project's ``path``.

        Entries where ``field`` is unset are ignored entirely, so a
        projects.yaml written before an option existed keeps the global
        default for every project.
        """
        resolved: str | None = None
        if path:
            try:
                resolved = str(Path(path).expanduser().resolve())
            except OSError:  # pragma: no cover - resolve() is non-strict
                resolved = None

        by_name = None
        by_basename = None

        for project in self.projects:
            value = getattr(project, field)
            if value is None:
                continue
            if resolved and project.path:
                try:
                    if str(Path(project.path).expanduser().resolve()) == resolved:
                        return value
                except OSError:  # pragma: no cover
                    pass
            if by_name is None and project.name == name:
                by_name = value
            if by_basename is None and project.path and Path(project.path).name == name:
                by_basename = value

        return by_name if by_name is not None else by_basename

    def alert_threshold_for(
        self,
        name: str,
        path: str | None = None,
        default: int = 40,
    ) -> int:
        """The health-score alert floor for one scanned project."""
        value = self._setting_for(name, path, "alert_threshold")
        return default if value is None else value

    def status_for(self, name: str, path: str | None = None) -> str | None:
        """The declared status for one scanned project, or None.

        None means projects.yaml says nothing — the caller decides how to
        infer a status (the organiser treats paths under
        ``<projects_root>/archive/`` as ``archived``, all else ``active``).
        """
        return self._setting_for(name, path, "status")

    def has_explicit_alert_threshold(
        self, name: str, path: str | None = None
    ) -> bool:
        """Whether projects.yaml pins an alert floor for this project.

        Needed because ``archived`` suppresses the *default* floor but
        must not override a floor the user set deliberately.
        """
        return self._setting_for(name, path, "alert_threshold") is not None


class DndScheduleWindow(BaseModel):
    """A time window during which DND is automatically active."""

    start: str = "23:00"  # HH:MM (24h)
    end: str = "07:00"


class DndConfig(BaseModel):
    """Do Not Disturb configuration."""

    enabled: bool = False  # manual toggle default (runtime-overridable)
    schedule: list[DndScheduleWindow] = Field(default_factory=list)
    allow_critical: bool = True  # critical alerts break through DND


class DesktopNotificationsConfig(BaseModel):
    enabled: bool = True
    min_severity: str = "warning"  # info | warning | critical


class PaNotificationsConfig(BaseModel):
    enabled: bool = True
    min_severity: str = "critical"


class TrayNotificationsConfig(BaseModel):
    """The slice of ``notifications.tray:`` the *backend* needs.

    The tray owns this section and parses config.yaml itself
    (``sysadmin_tray/config.py``); its calm tunables — flap cooldown,
    escalation polls, digest mode — are presentation and never reach the
    backend, so they are deliberately absent here and ignored on load.

    ``mute_services`` is the exception.  It is not merely a toast
    suppressor: it is the only place a service contributed by
    projects.yaml can be declared *expected down*, because those entries
    are generated by ``ManagedProject.to_monitored_services`` and have no
    ``mute`` flag of their own.  Reliability scoring waives deductions
    for an expected-down service, so it has to read this list or half the
    estate could never be waived.
    """

    mute_services: list[str] = Field(default_factory=list)


class NotificationsConfig(BaseModel):
    desktop: DesktopNotificationsConfig = Field(
        default_factory=DesktopNotificationsConfig
    )
    tray: TrayNotificationsConfig = Field(default_factory=TrayNotificationsConfig)
    pa_notify: PaNotificationsConfig = Field(
        default_factory=PaNotificationsConfig
    )
    dnd: DndConfig = Field(default_factory=DndConfig)


class SchedulesConfig(BaseModel):
    """Local times (server timezone) for the daily cron jobs in main.py."""

    briefing_hour: int = 6
    briefing_minute: int = 0
    retention_hour: int = 3
    retention_minute: int = 0
    # Weekly project review — before the Monday briefing so the briefing
    # can carry the fresh narrative.
    review_day_of_week: str = "mon"
    review_hour: int = 5
    review_minute: int = 30
    # Weekly disk review — after the project review rather than beside
    # it, so the 3B model does one generation at a time; still ahead of
    # the 06:00 briefing, which carries both narratives.
    disk_review_hour: int = 5
    disk_review_minute: int = 45
    # Daily reliability snapshot — 02:00, an hour ahead of the 03:00
    # retention purge so the day's score is written before anything is
    # deleted from under it. Nothing reads these rows to serve a request
    # (GET /api/services/reliability recomputes live); they exist so the
    # score becomes trendable.
    reliability_hour: int = 2
    reliability_minute: int = 0
    # APScheduler's IntervalTrigger puts the *first* fire at now + interval,
    # so an agent whose interval exceeds the service's uptime between
    # restarts never runs at all (this is why file_organiser, at 24h, had
    # zero recorded runs). Hours-scale agents therefore get an explicit
    # first run shortly after startup.
    agent_first_run_delay_seconds: int = 60


class SelfMonitorConfig(BaseModel):
    """Self-monitoring of the agents themselves (``/api/sysadmin/self``).

    An agent is considered *stalled* when the time since its last recorded
    run exceeds ``interval × stall_grace_multiplier`` (floored at
    ``min_stall_grace_seconds`` so short-interval agents are not flagged
    by a single restart). The interval comes from each agent's own config
    section — the same values ``main.py`` registers with the scheduler.
    """

    enabled: bool = True
    stall_grace_multiplier: float = 3.0
    min_stall_grace_seconds: int = 300
    recent_runs: int = 10


class EventsConfig(BaseModel):
    """Server-Sent Events stream (``GET /api/sysadmin/events``).

    ``heartbeat_seconds`` sets how often an SSE comment is written to an
    idle stream so proxies and clients do not drop it. ``max_queued_events``
    bounds each connected client's buffer — a client that cannot keep up
    loses its oldest events rather than stalling the publisher.
    """

    heartbeat_seconds: float = 20.0
    max_queued_events: int = 100
    retry_ms: int = 5000


class AgentsConfig(BaseModel):
    sysadmin: SysAdminAgentConfig = Field(default_factory=SysAdminAgentConfig)
    project_organiser: ProjectOrganiserConfig = Field(default_factory=ProjectOrganiserConfig)
    file_organiser: FileOrganiserConfig = Field(default_factory=FileOrganiserConfig)
    log_aggregator: LogAggregatorConfig = Field(default_factory=LogAggregatorConfig)
    service_discovery: ServiceDiscoveryConfig = Field(
        default_factory=ServiceDiscoveryConfig
    )


# --- Root config ---


class AppConfig(BaseModel):
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    personal_assistant: PersonalAssistantConfig = Field(default_factory=PersonalAssistantConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    schedules: SchedulesConfig = Field(default_factory=SchedulesConfig)
    self_monitor: SelfMonitorConfig = Field(default_factory=SelfMonitorConfig)
    events: EventsConfig = Field(default_factory=EventsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    projects: ProjectsConfig = Field(default_factory=ProjectsConfig, exclude=True)


# --- Merge logic ---


def _merge_projects_config(config: AppConfig, projects_path: Path) -> None:
    """Load projects.yaml and inject entries into agent configs."""
    if not projects_path.exists():
        return  # Backward-compatible: no projects.yaml is fine

    try:
        with open(projects_path) as f:
            raw = yaml.safe_load(f) or {}

        config.projects = ProjectsConfig.model_validate(raw)
    except Exception:
        logger.warning("failed to load %s, skipping", projects_path, exc_info=True)
        return

    # Endpoints are no longer injected from here. services.yaml owns every
    # service and every journal source attached to one; this file is read
    # only for the project-side settings the organiser still uses
    # (``status``, ``alert_threshold``) until Phase 4 retires it.


# --- Singleton loader ---

_config: AppConfig | None = None


#: Repository root — this module sits at ``<root>/sysadmin/core/config.py``,
#: so config.yaml and projects.yaml are two levels up.  Kept as a named
#: constant because the depth changed when core/ was introduced and a bare
#: chain of ``.parent`` gives no clue what it is counting.
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load and validate config from YAML file."""
    global _config

    if config_path is None:
        config_path = REPO_ROOT / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    _config = AppConfig.model_validate(raw or {})

    # Merge projects.yaml (sibling of config.yaml)
    projects_path = config_path.parent / "projects.yaml"
    _merge_projects_config(_config, projects_path)

    return _config


def get_config() -> AppConfig:
    """Get the loaded config, loading from default path if needed."""
    global _config
    if _config is None:
        return load_config()
    return _config
