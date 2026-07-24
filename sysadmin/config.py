"""Configuration loader — YAML file validated through Pydantic models."""

import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from sysadmin.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT

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


class MonitoredService(BaseModel):
    name: str
    type: str  # http | tcp | systemd
    url: str | None = None
    host: str | None = None
    port: int | None = None
    systemd_unit: str | None = None
    user: bool = False  # systemd unit is a *user* unit (systemctl --user)
    controllable: bool = True
    auto_restart: bool = False
    auto_restart_after_checks: int = 3


class Thresholds(BaseModel):
    disk_warning_percent: int = 80
    disk_critical_percent: int = 90
    ram_warning_percent: int = 85
    cpu_sustained_percent: int = 90
    cpu_sustained_minutes: int = 10
    gpu_temp_warning_c: int = 90
    gpu_vram_warning_percent: int = 90


class SysAdminAgentConfig(BaseModel):
    enabled: bool = True
    health_check_interval_seconds: int = 300
    services: list[MonitoredService] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)


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


class ProjectOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 6
    projects_root: str = "/home/gaddi/projects"
    stale_branch_days: int = 30
    track_todos: bool = True
    todo_patterns: list[str] = Field(
        default_factory=lambda: ["TODO", "FIXME", "HACK", "XXX"]
    )
    grade_bands: HealthGradeBands = Field(default_factory=HealthGradeBands)


class FileOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 24
    scan_root: str = "/home/gaddi"
    output_dir: str = "/home/gaddi/Documents/DMDocs/Self/Briefings/Audits"
    stale_days: int = 180
    downloads_stale_days: int = 30
    large_file_mb: int = 100
    similarity_threshold: float = 0.75
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
    """Log source config for a project endpoint."""

    type: str = "journalctl"
    unit: str | None = None
    path: str | None = None
    severity_filter: str = "warning"


class ProjectEndpoint(BaseModel):
    """A backend or frontend endpoint within a managed project."""

    url: str | None = None
    port: int | None = None
    systemd_unit: str | None = None
    log: ProjectEndpointLog | None = None


class ManagedProject(BaseModel):
    """A project with associated endpoints and metadata."""

    name: str
    path: str | None = None
    backend: ProjectEndpoint | None = None
    frontend: ProjectEndpoint | None = None

    def to_monitored_services(self) -> list[MonitoredService]:
        """Generate MonitoredService entries for health checking."""
        services = []
        if self.backend and self.backend.url:
            services.append(MonitoredService(
                name=self.name,
                type="http",
                url=self.backend.url,
                systemd_unit=self.backend.systemd_unit,
            ))
        if self.frontend and self.frontend.url:
            services.append(MonitoredService(
                name=f"{self.name}-frontend",
                type="http",
                url=self.frontend.url,
                systemd_unit=self.frontend.systemd_unit,
            ))
        return services

    def to_log_sources(self) -> list[LogSource]:
        """Generate LogSource entries for log aggregation."""
        sources = []
        for label, endpoint in [("backend", self.backend), ("frontend", self.frontend)]:
            if endpoint and endpoint.log:
                log = endpoint.log
                sources.append(LogSource(
                    name=self.name if label == "backend" else f"{self.name}-{label}",
                    type=log.type,
                    unit=log.unit,
                    path=log.path,
                    severity_filter=log.severity_filter,
                ))
        return sources


class ProjectsConfig(BaseModel):
    """Root model for projects.yaml."""

    projects: list[ManagedProject] = Field(default_factory=list)


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


class NotificationsConfig(BaseModel):
    desktop: DesktopNotificationsConfig = Field(
        default_factory=DesktopNotificationsConfig
    )
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


class AgentsConfig(BaseModel):
    sysadmin: SysAdminAgentConfig = Field(default_factory=SysAdminAgentConfig)
    project_organiser: ProjectOrganiserConfig = Field(default_factory=ProjectOrganiserConfig)
    file_organiser: FileOrganiserConfig = Field(default_factory=FileOrganiserConfig)
    log_aggregator: LogAggregatorConfig = Field(default_factory=LogAggregatorConfig)


# --- Root config ---


class AppConfig(BaseModel):
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    personal_assistant: PersonalAssistantConfig = Field(default_factory=PersonalAssistantConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    schedules: SchedulesConfig = Field(default_factory=SchedulesConfig)
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

    existing_svc_names = {s.name for s in config.agents.sysadmin.services}
    existing_src_names = {s.name for s in config.agents.log_aggregator.sources}

    for project in config.projects.projects:
        for svc in project.to_monitored_services():
            if svc.name not in existing_svc_names:
                config.agents.sysadmin.services.append(svc)
                existing_svc_names.add(svc.name)

        for src in project.to_log_sources():
            if src.name not in existing_src_names:
                config.agents.log_aggregator.sources.append(src)
                existing_src_names.add(src.name)


# --- Singleton loader ---

_config: AppConfig | None = None


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load and validate config from YAML file."""
    global _config

    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

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
