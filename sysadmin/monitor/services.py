"""services.yaml — what this host runs, and how each thing is checked.

Replaces the runtime half of projects.yaml and the ``agents.sysadmin.services``
block in config.yaml. Three properties are the point of the format:

**No paths.** A service is attached to a project by *id*, resolved through
:mod:`estate.registry`. A path can rot without anything noticing — twice
already, once from a case mismatch and once from a directory deleted during
a reorganisation. An id cannot: an unknown one fails at load.

**No one-backend-one-frontend limit.** projects.yaml modelled exactly two
endpoints per project, which is why seven units ended up exiled to
config.yaml with comments explaining that they belonged to a project the
file could not express. A project has N services here.

**``kind`` decides the check**, replacing a set of rules that previously
lived only in prose. The comment in config.yaml explaining that
``alfred-evaluate`` is a oneshot and must be watched through its timer was
correct, hand-maintained, and invisible to the code; it is now a field.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from sysadmin.core.config import LogSource
from estate.registry import Registry

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

Kind = Literal["http", "tcp", "systemd", "timer", "oneshot", "static"]

Scope = Literal["user", "system"]

#: Kinds that assert nothing about a unit's running state.
QUIET_KINDS: frozenset[str] = frozenset({"oneshot", "static"})

#: Status recorded for a service the configuration says not to check.
#: Distinct from ``error`` (the check failed) and from ``critical``
#: (the service is down) — see migration 009.
SKIPPED = "skipped"


class ServicesError(Exception):
    """services.yaml is unreadable, invalid, or references a missing project."""


class SystemdRef(BaseModel):
    """The unit behind a service.

    ``scope`` defaults to ``user`` because most units on this box are user
    units and the previous default was the other way round — an omitted
    ``user: true`` sent the check to the system bus, where the unit is
    simply unknown and the failure is silent. A wrong ``system`` here is
    loud; a wrong ``user`` was not.
    """

    model_config = ConfigDict(extra="forbid")

    unit: str
    scope: Scope = "user"


class LogRef(BaseModel):
    """Where this service's logs come from.

    ``unit`` is optional: a journalctl source almost always reads the
    journal of the unit the service already names, so leaving it unset
    inherits ``systemd.unit`` rather than repeating it.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = "journalctl"
    unit: str | None = None
    path: str | None = None
    severity_filter: str = "warning"


class ServiceEntry(BaseModel):
    """One service on this host."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Kind
    project: str | None = None
    role: str | None = None
    url: str | None = None
    host: str | None = None
    port: int | None = None
    systemd: SystemdRef | None = None
    log: LogRef | None = None
    monitor: bool = True
    reason: str | None = None
    mute: bool = False
    controllable: bool = True
    auto_restart: bool = False
    auto_restart_after_checks: int = 3

    @model_validator(mode="after")
    def _consistent(self) -> "ServiceEntry":
        if not self.monitor and not self.reason:
            raise ValueError(
                f"{self.name}: monitor: false requires a reason — a service "
                "excluded from checking without one is indistinguishable "
                "from one that was forgotten"
            )
        if self.kind == "http" and not self.url:
            raise ValueError(f"{self.name}: kind http requires a url")
        if self.kind == "tcp" and not (self.host and self.port):
            raise ValueError(f"{self.name}: kind tcp requires host and port")
        if self.kind in ("systemd", "timer", "oneshot", "static") and not self.systemd:
            raise ValueError(f"{self.name}: kind {self.kind} requires a systemd unit")
        if self.kind == "timer" and self.systemd and not self.systemd.unit.endswith(".timer"):
            raise ValueError(
                f"{self.name}: kind timer must name a .timer unit, got "
                f"{self.systemd.unit!r}"
            )
        return self

    @property
    def scope(self) -> Scope:
        return self.systemd.scope if self.systemd else "user"

    @property
    def unit(self) -> str | None:
        return self.systemd.unit if self.systemd else None

    @property
    def systemd_unit(self) -> str | None:
        """Alias for :attr:`unit`, under the name every consumer already uses."""
        return self.unit

    @property
    def user(self) -> bool:
        """Whether the unit lives in the user scope.

        The boolean the systemd helpers take. ``scope`` is the field
        because "user" and "system" say which one; ``user: false`` never
        said "system", it only said "not user", which is how an omission
        became a silent system-bus query.
        """
        return self.scope == "user"

    @property
    def log_unit(self) -> str | None:
        """The unit whose journal to read, inherited from ``systemd`` if unset."""
        if self.log is None:
            return None
        return self.log.unit or self.unit


class ServicesFile(BaseModel):
    """Root model for services.yaml."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: int = Field(alias="schema")
    services: list[ServiceEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _checked(self) -> "ServicesFile":
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"unsupported schema {self.schema_version}, this reader "
                f"handles schema {SCHEMA_VERSION}"
            )
        seen: dict[str, int] = {}
        for entry in self.services:
            seen[entry.name] = seen.get(entry.name, 0) + 1
        duplicates = sorted(name for name, count in seen.items() if count > 1)
        if duplicates:
            raise ValueError(
                "service names must be unique — a duplicate silently wins or "
                f"loses depending on load order: {', '.join(duplicates)}"
            )
        return self

    @property
    def project_ids(self) -> list[str]:
        """Every project id referenced, in first-seen order."""
        return list(dict.fromkeys(e.project for e in self.services if e.project))

    def for_project(self, project_id: str) -> list[ServiceEntry]:
        return [e for e in self.services if e.project == project_id]

    @property
    def host_services(self) -> list[ServiceEntry]:
        """Services belonging to no project.

        ``postgresql``, ``NetworkManager`` and the internet reachability
        probe are real services that no repository owns. The unit sweep
        already calls these host units; the schema agrees with it rather
        than forcing an invented owner.
        """
        return [e for e in self.services if not e.project]


@dataclass(frozen=True)
class CheckPlan:
    """What checking one service actually involves.

    Derived from ``kind`` so the decision is made once, here, rather than
    by a chain of conditionals inside the agent.
    """

    poll_url: bool = False
    connect: bool = False
    assert_active: bool = False
    inspect_timer: bool = False

    @property
    def checks_nothing(self) -> bool:
        return not (self.poll_url or self.connect or self.assert_active)


def check_plan(entry: ServiceEntry) -> CheckPlan:
    """The checks ``entry``'s kind calls for.

    ``http`` asserts the unit only when one is declared: the internet
    probe polls a URL that belongs to no unit on this machine, and
    demanding one would make the schema unable to express a reachability
    check at all.
    """
    if not entry.monitor or entry.kind in QUIET_KINDS:
        return CheckPlan()
    if entry.kind == "http":
        return CheckPlan(poll_url=True, assert_active=entry.systemd is not None)
    if entry.kind == "tcp":
        return CheckPlan(connect=True)
    if entry.kind == "timer":
        return CheckPlan(assert_active=True, inspect_timer=True)
    return CheckPlan(assert_active=True)


def parse_services(raw: Any) -> ServicesFile:
    """Validate an already-decoded services.yaml mapping."""
    if not isinstance(raw, dict):
        raise ValueError("services.yaml must be a YAML mapping")
    return ServicesFile.model_validate(raw)


def load_services(
    path: Path | str, registry: Registry | None = None
) -> ServicesFile:
    """Read, validate, and resolve services.yaml.

    When ``registry`` is supplied every ``project:`` reference is checked
    against it and an unknown id raises. That is the whole point of keying
    on ids: the failure lands at load, naming every bad reference at once,
    rather than as a check that silently never runs.

    A registry that has declared *nothing* is treated as an un-migrated
    estate rather than as evidence that every reference is wrong — it logs
    once and skips the id check. One manifest anywhere makes it strict.
    """
    path = Path(path).expanduser()
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ServicesError(f"{path}: unreadable — {exc}") from exc

    try:
        parsed = parse_services(raw)
    except (ValidationError, ValueError) as exc:
        raise ServicesError(f"{path}: invalid — {exc}") from exc

    if registry is not None:
        if not registry.ids:
            logger.warning(
                "services_project_ids_unchecked",
                extra={
                    "reason": "registry has no declared projects",
                    "root": str(registry.root),
                    "hint": "run scripts/migrate_registry.py --apply",
                },
            )
        else:
            registry.assert_known(parsed.project_ids, str(path))

    return parsed


def services_by_project(services: ServicesFile) -> dict[str, list[str]]:
    """Project id → the names of its services, in declaration order.

    Names only. estate.json publishes which services a project owns, not
    where they listen — embedding urls and units would make it a second
    place to edit when a port moves.
    """
    grouped: dict[str, list[str]] = {}
    for entry in services.services:
        if entry.project:
            grouped.setdefault(entry.project, []).append(entry.name)
    return grouped


def log_sources(services: ServicesFile) -> list[LogSource]:
    """The journal sources declared alongside the services that emit them.

    A service and its logs were previously described in two files that had
    to agree by hand: config.yaml listed ``sysadmin.service`` under the
    name ``sysadmin`` while projects.yaml generated ``sysadmin-service``
    for the same unit, so the journal was ingested twice under two names
    and neither file said so.
    """
    sources: list[LogSource] = []
    for entry in services.services:
        if entry.log is None:
            continue
        sources.append(
            LogSource(
                name=entry.name,
                type=entry.log.type,
                unit=entry.log_unit,
                user=entry.user,
                path=entry.log.path,
                severity_filter=entry.log.severity_filter,
            )
        )
    return sources


_services: ServicesFile | None = None


def load_services_singleton(
    path: Path | str | None = None, registry: Registry | None = None
) -> ServicesFile:
    """Load services.yaml into the process-wide slot and return it."""
    global _services
    _services = load_services(path or default_services_path(), registry)
    return _services


def get_services() -> ServicesFile:
    """The loaded services.yaml, reading it on first use.

    Mirrors ``get_config`` so callers do not have to thread the file
    through. Loaded without a registry here: the id check belongs to
    startup, where a failure can stop the service, not to whichever
    request happened to touch this first.
    """
    global _services
    if _services is None:
        _services = load_services(default_services_path())
    return _services


def default_services_path() -> Path:
    """services.yaml beside config.yaml, at the repository root."""
    from sysadmin.core.config import REPO_ROOT

    return REPO_ROOT / "services.yaml"
