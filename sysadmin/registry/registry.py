"""The registry — project identity, and nothing else.

Depends on neither the monitor nor the organiser.  It answers one
question, "which projects exist and what are they called", and refuses to
answer it vaguely: a project that has not declared itself is reported as
``undeclared`` rather than assumed to be active, and a reference to an id
nobody claims is an error at load rather than a lookup that returns None
somewhere deep in a scan.
"""

import logging
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from sysadmin.registry.discovery import (
    DEFAULT_DEPTH,
    DEFAULT_ROOT,
    derive_category,
    derive_id,
    discover_repositories,
    relative_path,
    under_archive,
)
from sysadmin.registry.errors import (
    DuplicateProjectIdError,
    ManifestError,
    UnknownProjectError,
)
from sysadmin.registry.manifest import (
    ProjectManifest,
    Status,
    describe_error,
    read_manifest,
)

logger = logging.getLogger(__name__)

FINDING_UNDECLARED = "undeclared"
FINDING_PROVISIONAL_COLLISION = "provisional_id_collision"


@dataclass(frozen=True)
class RegistryFinding:
    """Something worth reporting that is not worth refusing to load over."""

    kind: str
    subject: str
    message: str


@dataclass(frozen=True)
class ProjectEntry:
    """One repository, as the registry sees it."""

    path: Path
    relative: str
    provisional_id: str
    category: str | None
    status: Status
    manifest: ProjectManifest | None = None

    @property
    def declared(self) -> bool:
        """Whether a manifest claims this repository's identity."""
        return self.manifest is not None

    @property
    def id(self) -> str:
        """The declared id, or the provisional one when undeclared."""
        return self.manifest.id if self.manifest else self.provisional_id

    @property
    def name(self) -> str:
        return self.manifest.name if self.manifest else self.path.name

    @property
    def alert_threshold(self) -> int | None:
        return self.manifest.alert_threshold if self.manifest else None


@dataclass(frozen=True)
class Registry:
    """Every repository under one root, indexed by declared id."""

    root: Path
    entries: tuple[ProjectEntry, ...] = ()
    findings: tuple[RegistryFinding, ...] = ()

    _by_id: dict[str, ProjectEntry] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __iter__(self) -> Iterator[ProjectEntry]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self.entries)

    @property
    def ids(self) -> tuple[str, ...]:
        """Declared ids only, sorted.  Provisional ids are not resolvable."""
        return tuple(sorted(self._by_id))

    @property
    def paths_by_id(self) -> Mapping[str, Path]:
        """The id → path map."""
        return {project_id: entry.path for project_id, entry in self._by_id.items()}

    @property
    def declared(self) -> tuple[ProjectEntry, ...]:
        return tuple(entry for entry in self.entries if entry.declared)

    @property
    def undeclared(self) -> tuple[ProjectEntry, ...]:
        """Repositories with no manifest.

        A reportable state in its own right, not a synonym for inactive
        and not a synonym for active.  These are the repositories nobody
        has made a decision about.
        """
        return tuple(entry for entry in self.entries if not entry.declared)

    def resolve(self, project_id: str) -> ProjectEntry | None:
        """The entry for ``project_id``, or None."""
        return self._by_id.get(project_id)

    def require(self, project_id: str, referenced_by: str) -> ProjectEntry:
        """The entry for ``project_id``, or raise ``UnknownProjectError``."""
        entry = self._by_id.get(project_id)
        if entry is None:
            raise UnknownProjectError([project_id], referenced_by, self.ids)
        return entry

    def assert_known(self, project_ids: Iterable[str], referenced_by: str) -> None:
        """Raise once, listing every id ``referenced_by`` got wrong.

        The entry point for anything that references projects by id —
        services.yaml in particular.  Checking the whole reference set at
        load beats discovering a typo when a check silently never runs.
        """
        unknown = [pid for pid in dict.fromkeys(project_ids) if pid not in self._by_id]
        if unknown:
            raise UnknownProjectError(unknown, referenced_by, self.ids)


def effective_status(
    manifest: ProjectManifest | None, path: Path, root: Path
) -> Status:
    """The status to act on, as opposed to the status as written.

    A declared status always wins.  Failing one, location decides:
    anything under ``<root>/archive/`` is archived, which preserves the
    inference the organiser already makes.  Everything else stays
    ``undeclared`` — the point of the registry is that nothing becomes
    active by default.
    """
    declared: Status = manifest.status if manifest else "undeclared"
    if declared != "undeclared":
        return declared
    return "archived" if under_archive(path, root) else "undeclared"


def build_entry(path: Path, root: Path, manifest: ProjectManifest | None) -> ProjectEntry:
    """Assemble one entry from a repository path and its manifest."""
    return ProjectEntry(
        path=path,
        relative=relative_path(path, root),
        provisional_id=derive_id(path.name),
        category=(manifest.category if manifest and manifest.category else None)
        or derive_category(path, root),
        status=effective_status(manifest, path, root),
        manifest=manifest,
    )


def load_registry(
    root: Path | str = DEFAULT_ROOT, depth: int = DEFAULT_DEPTH
) -> Registry:
    """Scan ``root`` and build the registry, failing loudly and completely.

    Failures are checked in a fixed order — manifests, then duplicate
    ids, then references — and each check reports every instance it
    finds.  One pass per class of problem, rather than one pass per
    problem.
    """
    root_path = Path(root).expanduser()
    repositories = discover_repositories(root_path, depth)

    manifests: dict[Path, ProjectManifest | None] = {}
    problems: list[tuple[Path, str]] = []

    for repository in repositories:
        try:
            manifests[repository] = read_manifest(repository)
        except Exception as exc:  # noqa: BLE001 - reported, not swallowed
            problems.append((repository, describe_error(exc)))

    if problems:
        raise ManifestError(problems)

    entries = tuple(
        build_entry(repository, root_path, manifests[repository])
        for repository in repositories
    )

    by_id: dict[str, ProjectEntry] = {}
    collisions: dict[str, list[Path]] = {}
    for entry in entries:
        if entry.manifest is None:
            continue
        existing = by_id.get(entry.manifest.id)
        if existing is not None:
            collisions.setdefault(entry.manifest.id, [existing.path]).append(entry.path)
            continue
        by_id[entry.manifest.id] = entry

    if collisions:
        raise DuplicateProjectIdError(collisions)

    registry = Registry(
        root=root_path,
        entries=entries,
        findings=_findings(entries),
        _by_id=by_id,
    )

    _assert_supersedes_known(registry)

    logger.info(
        "registry_loaded",
        extra={
            "root": str(root_path),
            "repositories": len(entries),
            "declared": len(registry.declared),
            "undeclared": len(registry.undeclared),
        },
    )
    return registry


def _findings(entries: Iterable[ProjectEntry]) -> tuple[RegistryFinding, ...]:
    """What the sweep noticed but will not refuse to load over."""
    entries = tuple(entries)
    findings: list[RegistryFinding] = [
        RegistryFinding(
            kind=FINDING_UNDECLARED,
            subject=entry.relative,
            message=(
                f"no manifest; would be reported as {entry.status}. "
                f"Provisional id {entry.provisional_id!r} is not resolvable."
            ),
        )
        for entry in entries
        if not entry.declared
    ]

    seen: dict[str, list[ProjectEntry]] = {}
    for entry in entries:
        if not entry.declared:
            seen.setdefault(entry.provisional_id, []).append(entry)

    findings.extend(
        RegistryFinding(
            kind=FINDING_PROVISIONAL_COLLISION,
            subject=provisional_id,
            message=(
                "several undeclared repositories derive the same id: "
                + ", ".join(sorted(e.relative for e in group))
                + ". Declaring them resolves it."
            ),
        )
        for provisional_id, group in sorted(seen.items())
        if len(group) > 1
    )

    return tuple(findings)


def _assert_supersedes_known(registry: Registry) -> None:
    """Every ``supersedes:`` entry must name a project the registry knows.

    A dangling supersedes is the same defect as a dead path in
    projects.yaml, one indirection further along: it reads as a recorded
    decision while pointing at nothing.
    """
    referenced: list[str] = []
    for entry in registry.declared:
        assert entry.manifest is not None
        referenced.extend(entry.manifest.supersedes)

    if referenced:
        registry.assert_known(referenced, "a .project.yaml supersedes: field")
