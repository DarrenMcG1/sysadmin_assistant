"""Configuration loader — YAML file validated through Pydantic models."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


# --- Nested config sections ---


class ServiceConfig(BaseModel):
    name: str = "sysadmin-service"
    port: int = 8500
    host: str = "127.0.0.1"
    log_level: str = "info"


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://gaddi@localhost:5432/projects"
    sync_url: str = "postgresql+psycopg2://gaddi@localhost:5432/projects"
    schema_: str = Field(default="sysadmin", alias="schema")

    model_config = {"populate_by_name": True}


class PersonalAssistantConfig(BaseModel):
    url: str = "http://localhost:8000"
    api_prefix: str = "/api"
    notify_endpoint: str = "/api/notifications"
    briefing_endpoint: str = "/api/briefing/data"


class OllamaConfig(BaseModel):
    url: str = "http://localhost:11434"
    model: str = "qwen2.5:14b"
    night_model: str = "qwen3:72b"


# --- Agent sub-configs ---


class MonitoredService(BaseModel):
    name: str
    type: str  # http | tcp | systemd
    url: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    systemd_unit: Optional[str] = None


class Thresholds(BaseModel):
    disk_warning_percent: int = 80
    disk_critical_percent: int = 90
    ram_warning_percent: int = 85
    cpu_sustained_percent: int = 90
    cpu_sustained_minutes: int = 10


class SysAdminAgentConfig(BaseModel):
    enabled: bool = True
    health_check_interval_seconds: int = 300
    services: list[MonitoredService] = Field(default_factory=list)
    thresholds: Thresholds = Field(default_factory=Thresholds)


class ProjectOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 6
    projects_root: str = "/home/gaddi/projects"
    stale_branch_days: int = 30
    orphan_detection: bool = True
    track_todos: bool = True
    todo_patterns: list[str] = Field(
        default_factory=lambda: ["TODO", "FIXME", "HACK", "XXX"]
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
    skip_dirs: list[str] = Field(
        default_factory=lambda: [
            ".git", ".cache", ".local", ".config", ".var",
            ".mozilla", ".steam", "node_modules", "__pycache__", ".venv",
        ]
    )


class LogSource(BaseModel):
    name: str
    type: str  # journalctl | file
    unit: Optional[str] = None
    path: Optional[str] = None
    severity_filter: str = "warning"


class LogAggregatorConfig(BaseModel):
    enabled: bool = True
    poll_interval_seconds: int = 60
    sources: list[LogSource] = Field(default_factory=list)
    retention_days: int = 30
    summarise_with_llm: bool = True


class AgentsConfig(BaseModel):
    sysadmin: SysAdminAgentConfig = Field(default_factory=SysAdminAgentConfig)
    project_organiser: ProjectOrganiserConfig = Field(default_factory=ProjectOrganiserConfig)
    file_organiser: FileOrganiserConfig = Field(default_factory=FileOrganiserConfig)
    log_aggregator: LogAggregatorConfig = Field(default_factory=LogAggregatorConfig)


# --- Root config ---


class AppConfig(BaseModel):
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    personal_assistant: PersonalAssistantConfig = Field(default_factory=PersonalAssistantConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)


# --- Singleton loader ---

_config: Optional[AppConfig] = None


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    """Load and validate config from YAML file."""
    global _config

    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    _config = AppConfig.model_validate(raw or {})
    return _config


def get_config() -> AppConfig:
    """Get the loaded config, loading from default path if needed."""
    global _config
    if _config is None:
        return load_config()
    return _config
