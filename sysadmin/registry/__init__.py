"""Project identity for the estate.

The registry owns one question — which projects exist and what are they
called — and is depended on by both the monitor and the organiser while
depending on neither.

Public surface::

    from sysadmin.registry import load_registry

    registry = load_registry("~/projects")
    registry.paths_by_id["sports-analyser"]
    registry.assert_known(ids_from_services_yaml, "services.yaml")
    registry.undeclared
"""

from sysadmin.registry.discovery import (
    DEFAULT_DEPTH,
    DEFAULT_ROOT,
    PRUNE_DIRS,
    derive_category,
    derive_id,
    discover_repositories,
    is_repository,
    should_prune,
)
from sysadmin.registry.errors import (
    DuplicateProjectIdError,
    ManifestError,
    RegistryError,
    UnknownProjectError,
)
from sysadmin.registry.manifest import (
    MANIFEST_NAME,
    SCHEMA_VERSION,
    STATUSES,
    Decision,
    ProjectManifest,
    Status,
    has_manifest,
    manifest_path,
    read_manifest,
)
from sysadmin.registry.registry import (
    FINDING_PROVISIONAL_COLLISION,
    FINDING_UNDECLARED,
    ProjectEntry,
    Registry,
    RegistryFinding,
    effective_status,
    load_registry,
)

__all__ = [
    "DEFAULT_DEPTH",
    "DEFAULT_ROOT",
    "FINDING_PROVISIONAL_COLLISION",
    "FINDING_UNDECLARED",
    "MANIFEST_NAME",
    "PRUNE_DIRS",
    "SCHEMA_VERSION",
    "STATUSES",
    "Decision",
    "DuplicateProjectIdError",
    "ManifestError",
    "ProjectEntry",
    "ProjectManifest",
    "Registry",
    "RegistryError",
    "RegistryFinding",
    "Status",
    "UnknownProjectError",
    "derive_category",
    "derive_id",
    "discover_repositories",
    "effective_status",
    "has_manifest",
    "is_repository",
    "load_registry",
    "manifest_path",
    "read_manifest",
    "should_prune",
]
