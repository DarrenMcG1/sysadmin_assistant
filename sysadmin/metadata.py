"""Every mapped table, in one import.

``Base.metadata`` is only complete once each model module has been
imported, and after Phase 2 those modules live in six packages. Alembic
autogenerate and the schema-drift test both need the whole set, so the
aggregation lives here rather than being repeated in each — a table
missing from one copy and not the other is exactly the silent drift the
drift test exists to catch.

This module sits beside ``main.py`` on purpose. Both are composition
roots: they are allowed to import every domain, and no domain imports
them.
"""

from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.alert import Alert
from sysadmin.core.models.base import Base
from sysadmin.core.models.retention_config import RetentionConfig
from sysadmin.files.models.disk_review import DiskReview
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.models.reliability_score import ReliabilityScore
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.projects.models.project_review import ProjectReview
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.units.models import UnitAudit

ALL_MODELS = (
    AgentRun,
    Alert,
    DiskReview,
    FilesystemAudit,
    LogEntry,
    LogSummary,
    ProjectReview,
    ProjectSnapshot,
    ReliabilityScore,
    ResourceSnapshot,
    RetentionConfig,
    ServiceHealth,
    UnitAudit,
)

__all__ = ["ALL_MODELS", "Base", *sorted(model.__name__ for model in ALL_MODELS)]
