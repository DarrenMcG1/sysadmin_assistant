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
from estate.registry import Registry
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from sysadmin.core.config import LogFormat, LogSource
from sysadmin.monitor.models.service_health import SKIPPED as _SKIPPED

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

Kind = Literal["http", "tcp", "systemd", "timer", "oneshot", "static"]

Scope = Literal["user", "system"]

#: Kinds that assert nothing about a unit's running state.
QUIET_KINDS: frozenset[str] = frozenset({"oneshot", "static"})

#: Status recorded for a service the configuration says not to check.
#: Distinct from ``error`` (the check failed) and from ``critical``
#: (the service is down) — see migration 009.
#:
#: Re-exported rather than restated (``SNAG-API-004``).  The one
#: statement of this vocabulary is the ``chk_health_status`` CHECK
#: constraint, so the string is owned beside it and the classification
#: that reads it cannot fall behind the writers that produce it.
SKIPPED = _SKIPPED


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
    """Where this service's logs come from, and how they are encoded.

    ``unit`` is optional: a journalctl source almost always reads the
    journal of the unit the service already names, so leaving it unset
    inherits ``systemd.unit`` rather than repeating it.

    ``format`` is the other half and is **a declaration, not a guess**
    (``SNAG-LOG-003``).  This daemon logs one JSON document per record, so
    journald's ``MESSAGE`` is the whole document and ``alert_title`` built
    a 252-character title out of it that reached a notification body
    verbatim.  The obvious fix — sniff a leading ``{`` in
    :func:`~sysadmin.monitor.journal.read_journal` — puts a special case
    for one source into a reader serving fifteen, keyed on this
    application's own log format; that is precisely the coupling
    ``SNAG-AGENT-008``'s priority half was sent to the producer to avoid.
    Declaring it here makes the reader honour a statement the source has
    made about itself, which is the shape ``kind`` already has two fields
    up.

    The vocabulary lives on :data:`~sysadmin.core.config.LogFormat`, not
    beside this field, because config.yaml's ``LogSource`` carries the
    same one.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = "journalctl"
    unit: str | None = None
    path: str | None = None
    severity_filter: str = "warning"
    format: LogFormat = "text"


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
    #: The agent whose work this timer runs, when a scheduled job has
    #: been moved out of this process (``SNAG-SVC-002``).  Declared here
    #: rather than beside the agent because this entry is what an author
    #: *adds* during the move and the agent side is what they delete —
    #: see :mod:`sysadmin.monitor.handover`, which reads it.  A name from
    #: ``self_monitor.AGENT_NAMES``; a name this daemon still schedules
    #: and has enabled means the job runs twice.
    agent: str | None = None
    mute: bool = False
    controllable: bool = True
    auto_restart: bool = False
    auto_restart_after_checks: int = 3
    #: This service holds GPU memory that a card reset destroys, so a
    #: process started before the last reset is serving from a context
    #: that no longer exists (`ADR-0007`, ``SNAG-GPU-001``).  Read by
    #: :mod:`sysadmin.monitor.gpu_context` through
    #: :meth:`~sysadmin.monitor.agent.SysAdminAgent._check_http_and_unit`.
    #:
    #: **A declaration and not a role**, which is the measurement that
    #: decided it: ``role: inference`` names four services here, and
    #: ``venture-embed`` runs with no offloaded layers and served 267 of
    #: its 823 successful embeddings while the predicate was true.  Keyed
    #: on the role this ships 267 false alarms about a server that was
    #: working throughout.
    #:
    #: Default ``False``, and the polarity is the safe one in both
    #: directions — an omission costs a term nobody asked for rather than
    #: arming one nobody wrote, and the reading it gates is a *fault*.
    #: That is ``UnitFinding.enabled``'s trap answered on the correct
    #: side: there, absent evidence had to be quiet for one consumer and
    #: loud for another, and here there is one consumer and quiet is what
    #: an undeclared service means.
    holds_vram: bool = False

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
        if self.agent and self.kind != "timer":
            # A handover replaces a *schedule*, so only the thing that
            # holds one can stand in for it. A oneshot is inactive
            # between runs by design and this file already watches it
            # through its timer; a `systemd` entry asserts a running
            # process, which is not a firing.
            raise ValueError(
                f"{self.name}: agent: is only meaningful on kind timer, "
                f"got kind {self.kind}"
            )
        if self.holds_vram and not (self.kind == "http" and self.systemd):
            # The predicate needs both halves and exactly one check path
            # evaluates it. `ActiveEnterTimestamp` comes from the unit,
            # so a declaration without one cannot be answered at all; and
            # `_check_http_and_unit` is the only reader, so a declaration
            # on any other kind would parse, ship, and silently never be
            # evaluated — SNAG-CFG-001's shape at the size of one leaf.
            # Refused at load rather than discouraged in a comment, which
            # is `spawn_manual_run` hard-coding "manual" for its reason.
            # Widening the reading to another check path widens this
            # clause in the same commit.
            raise ValueError(
                f"{self.name}: holds_vram requires kind http with a systemd "
                f"unit — it is evaluated only by the http-and-unit check, "
                f"and it needs the unit's start instant; got kind "
                f"{self.kind} with systemd "
                f"{'declared' if self.systemd else 'absent'}"
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
                format=entry.log.format,
            )
        )
    return sources


def composed_log_sources(agent_config) -> list[LogSource]:
    """Every journal source this daemon ingests — both files, one list.

    services.yaml first, then the config.yaml entries that belong to no
    service (the kernel journal has no unit to hang off).  A config.yaml
    entry duplicating a service is dropped and logged, because a journal
    read twice costs nothing but shows up as doubled error counts.

    Lifted out of ``LogAggregatorAgent._sources`` in Session 75, when
    ``GET /api/logs/{source}`` gained a validator and became the second
    caller.  It is one function rather than two because the set the route
    admits must equal the set the agent ingests — a route validating
    against a set built from one file would 404 ``kernel``, which is
    451,319 of the 451,569 rows in ``log_entries`` on this box.
    """
    sources = log_sources(get_services())
    seen = {s.name for s in sources}
    by_unit = {(s.unit, s.user) for s in sources if s.unit}
    for extra in agent_config.sources:
        if extra.name in seen:
            logger.warning(
                "duplicate_log_source_name",
                extra={"source": extra.name, "kept": "services.yaml"},
            )
            continue
        if extra.unit and (extra.unit, extra.user) in by_unit:
            logger.warning(
                "duplicate_log_source_unit",
                extra={"source": extra.name, "unit": extra.unit,
                       "kept": "services.yaml"},
            )
            continue
        sources.append(extra)
        seen.add(extra.name)
    return sources


def stored_source_name(source: LogSource) -> str | None:
    """What a source's rows carry in ``log_entries.source``, or ``None``.

    **One column, two producers, two identities** — which is why this is
    a function and not an attribute read.  A journal source is stamped
    with its **unit** (``_read_journal_source`` -> ``journal.py``, where
    ``entry["source"]`` is the unit name); a file source is stamped with
    its **name**, because ``_read_log_file`` is handed ``source.name``
    and has no unit to use.  ``log_source_scopes`` already records the
    first half of this trap from the other side: keying on ``name`` where
    the column holds the unit yields an empty map that reads as "every
    source is a system unit".

    The branch structure mirrors ``LogAggregatorAgent._execute``'s
    dispatch exactly, including the ``else: continue`` — a source that
    declares neither a unit nor a path is never read, so it can produce
    no rows and must not be admitted as though it could.  ``None`` is
    that case, distinct from a name, so a caller cannot silently union it
    into a set.

    Written from the producer rather than from the data on purpose: every
    declared source on this box is ``type: journalctl`` today, so a rule
    derived from the live table would omit the file branch and be green
    in every test until the first file source was declared.
    """
    if source.type == "journalctl" and source.unit:
        return source.unit
    if source.type == "file" and source.path:
        return source.name
    return None


_services: ServicesFile | None = None


def set_services(services: ServicesFile) -> ServicesFile:
    """Install an already-validated file into the process-wide slot.

    Exists for the reload path (:mod:`sysadmin.reload`), which validates
    both configuration files before installing either. :func:`load_services`
    is already pure — it returns rather than assigns — so the split costs
    nothing here; the singleton is the only mutable half.
    """
    global _services
    _services = services
    return _services


def load_services_singleton(
    path: Path | str | None = None, registry: Registry | None = None
) -> ServicesFile:
    """Load services.yaml into the process-wide slot and return it."""
    return set_services(load_services(path or default_services_path(), registry))


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
