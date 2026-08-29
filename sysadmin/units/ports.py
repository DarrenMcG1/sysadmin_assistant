"""Who actually holds each port, and where that disagrees with the record.

Session 26c.  The third scorer of the units tier's questions, and the
only one on this box that needs a subprocess — which is why it is a
sibling of :mod:`sysadmin.units.scan` rather than part of it.  That
module's no-subprocess promise is load-bearing and was re-verified in
Session 46; a check that shells out belongs beside it, not inside it.

**There are three port registries on this box and only one of them
cannot lie.**  That is the whole argument for this module existing here
rather than in estate-manager:

1. The estate's hand-maintained markdown table
   (``docs/guides/monitorable-project.md`` §2.1) — 18 rows, project
   granularity, no units.
2. This repository's ``services.yaml`` — 11 entries carrying **both**
   ``port:`` and ``systemd: {unit, scope}``, which is a hand-declared
   port↔unit pair nothing has ever checked.
3. The kernel, via ``ss`` and ``/proc/<pid>/cgroup``.

estate-manager compares (1) against (3) and is **structurally blocked
from the interesting half**: its ``live_listeners()`` runs ``ss -H
-tln`` deliberately without ``-p``, so it can say a port is taken and
never by whom.  Its own docstring gives the reason — *"process names
need privileges for other users' sockets"* — and that reason is true
only for *other users'* sockets.  Measured 2026-08-15 as ``gaddi``:
``ss -H -ltnp`` attributes 8080, 8081, 8082, 8100, 8200, 8300, 8384,
8400, 8500, 8600, 3100 and 3200 — every registry-relevant port on the
box — and comes back blank only for the root-owned and containerised
ones (5432, 1883, 631, 139/445, and **8601**, the SearXNG container).

Four comparisons, in two families that surface differently, and the
split is the one this repository keeps re-deriving:

**Live collisions** — the box disagrees with itself *now*:

- ``wrong_unit``: ``services.yaml`` declares port P is unit U; the
  cgroup holding P is unit V.  The ``kind: http`` check is green while
  the unit it names is dead — a check that records less than the reader
  believes (``SNAG-SYSD-002``'s shape), and the tray's start/stop
  buttons act on the wrong process.
- ``port_shared``: two distinct units hold one port.  One of them lost
  the bind, or both set ``SO_REUSEPORT`` and traffic is being split.

**Registry disagreements** — a document is wrong, nothing is broken
yet:

- ``duplicate_claim``: two rows of the estate's table claim one port.
  Invisible to their check because ``claimed_ports`` is a ``set``.
- ``wrong_project``: the table says port P belongs to project X; the
  unit holding P matches project Y on disk.  The attribution nobody
  else can make.

The first family alerts (one row per port); the second is advice under
``GET /api/units/actions``.  That is the armed-orphan split applied
again: a fault in progress gets a row, accumulated debt gets ranked
text.  Stated here rather than left implicit because "collision
detection" reads as one thing and is two.

**Not-knowing is never a finding.**  A listener with no attribution
(root-owned, containerised) is reported as ``unattributed`` and
compared against nothing.  Deliberately the same posture as
:mod:`sysadmin.monitor.collation` and the opposite of
:mod:`sysadmin.core.schema_guard`: a false positive here sends someone
hunting a collision that does not exist, and 8601 alone would produce
one on every sweep.

**A failed observation is not an empty one.**  If ``ss`` cannot be run,
:func:`observe_listeners` returns a report carrying the error and *no*
listeners, and the caller must neither judge nor sweep — the estate
judge's rule 2, for its reason: a sweep scoped to a payload nobody
received closes every row on the strength of not having looked.

Pure below :func:`observe_listeners`: give it listeners, declarations
and claims, get findings.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sysadmin.units.scan import normalise

logger = logging.getLogger(__name__)

Runner = Callable[..., "subprocess.CompletedProcess[str]"]

#: ``users:(("uvicorn",pid=1057804,fd=15))`` — one group per socket
#: holder.  Two groups on one line is normal (a forking server), so the
#: pid is extracted per group rather than once per line.
_USERS = re.compile(r'\("([^"]*)",pid=(\d+),fd=\d+\)')

#: The last path segment of a cgroup line that names a systemd unit.
_UNIT_SUFFIXES = (".service", ".socket", ".scope", ".mount", ".slice")

#: ``| 8080 | venture-assistant | llama-server chat … |``.  The same
#: shape estate-manager's ``parse_registry`` matches, and deliberately
#: no stricter — see :func:`parse_port_registry` for why this is a
#: second parser rather than a shared one.
_ROW = re.compile(r"^\|\s*(\d{2,5})\s*\|([^|]*)\|([^|]*)\|")
_UNALLOCATED = re.compile(r"_?free\b", re.IGNORECASE)

SCOPE_USER = "user"
SCOPE_SYSTEM = "system"

#: Where each manager serialises the units it was asked to create at
#: runtime.  Listed, never a ``systemctl show -p Transient``: the same
#: class of signal :func:`~sysadmin.units.scan.discover_units` reads for
#: enablement, so the signal stays inside what the swept modules can
#: themselves see and costs no second subprocess beside ``ss``.
#:
#: **Scope decides the directory, and both are populated here.**  The
#: user manager writes under ``$XDG_RUNTIME_DIR``; the system manager
#: under ``/run/systemd``, which is world-readable and on 2026-08-28
#: held ``dbus-:1.2-org.kde.kameleon.qmk.helper@0.service`` — so a
#: system-scope per-launch listener is a real shape on this box and not
#: a hypothetical.
SYSTEM_TRANSIENT_DIR = Path("/run/systemd/transient")

#: The registry's jurisdiction, as a *fallback* for callers with no
#: config — every production path passes
#: :attr:`~sysadmin.core.config.PortCheckConfig.audited_ranges` instead.
#:
#: It exists because this module is pure below :func:`observe_listeners`
#: and may not read ``config.yaml`` to find out what it governs.  That
#: makes it a second statement of one fact, so it is **pinned** to the
#: config default by ``tests/test_unit_ports.py`` rather than trusted —
#: ``syslog_priority`` against ``journal.PRIORITY_MAP``'s treatment.
#: Import where you can, pin where you cannot; the failure mode of
#: neither is silent drift, which is ``SNAG-PORT-001`` inside one
#: repository instead of across two.
DEFAULT_AUDITED_RANGES: tuple[tuple[int, int], ...] = (
    (1000, 1999),
    (3000, 3999),
    (8000, 8999),
)

#: Finding kinds.  The first two alert, the last two advise.
WRONG_UNIT = "wrong_unit"
PORT_SHARED = "port_shared"
DUPLICATE_CLAIM = "duplicate_claim"
WRONG_PROJECT = "wrong_project"

#: Kinds that describe a live disagreement rather than a stale document.
#: The alert family is exactly this set, and it is defined here rather
#: than in the agent so the two surfaces cannot come to disagree about
#: which findings are faults.
COLLISION_KINDS: frozenset[str] = frozenset({WRONG_UNIT, PORT_SHARED})

#: Rank order within the advice family, worst first.
KIND_ORDER = (WRONG_UNIT, PORT_SHARED, DUPLICATE_CLAIM, WRONG_PROJECT)


# --------------------------------------------------------------------------
# Observation — the impure half
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Listener:
    """One TCP port in LISTEN state, attributed as far as we can see.

    ``unit`` and ``scope`` are ``None`` together: either the cgroup was
    read and named a unit, or nothing is claimed.  ``process`` can be
    set while ``unit`` is not — a bare process outside any unit — which
    is a different state from no attribution at all and is why both
    fields are kept.
    """

    port: int
    pid: int | None = None
    process: str | None = None
    unit: str | None = None
    scope: str | None = None
    cgroup: str | None = None
    runtime_created: bool = False

    @property
    def attributed(self) -> bool:
        return self.unit is not None

    @property
    def transient(self) -> bool:
        """A per-launch identity rather than one worth comparing to a registry.

        Named because it looks like an attribution and is not one: the id
        in it changes on every launch, so a finding built on it would
        never dedup and its remedy would name a unit nobody can find.

        **Two signals, because one shape was mistaken for the family**
        (``SNAG-PORT-003``, closed 2026-08-28).  The suffix test was
        written in Session 57 against ``app-code-oss-26348.scope`` — the
        editor dev servers — and a ``.scope`` is per-launch by
        construction, since systemd has no persistent scope files.  What
        it misses is every runtime-created ``.service``, and this box
        holds eight: ``dbus-:1.2-org.kde.kdeconnect@0.service`` and two
        siblings carry a bus-unique connection name, and
        ``app-steam@455b2e51…service``, ``app-firefox@d50574d5…service``
        and four more carry a 32-hex per-launch id and no colon at all.

        That count is what refused both fixes the entry proposed.  A
        ``dbus-`` prefix reaches 3 of the 8 and a ``:N.N`` pattern 2 (the
        box carries ``:1.21`` beside ``:1.2``), while both leave the two
        ``app-*@<id>`` units that were *holding ports at the time* —
        steam on four, appimagekit on one — reading as stable identities.
        The entry called the missing evidence "a second instance to tell
        a rule from a coincidence"; the second instance was a different
        shape, so a rule tuned to the first would have been the
        coincidence.  Nor is there a name rule that could have worked:
        ``app-steam@455b….service`` and ``syncthing@gaddi.service`` are
        the same shape, and separating them means deciding that a 32-hex
        instance is special — ``systemd-run``'s convention, which is the
        format-someone-else-owns objection the entry raised against
        ``:N.N``, met from the other side.

        :attr:`runtime_created` is stamped by :func:`observe_listeners`
        from the manager's own transient directory rather than derived
        from the name, so this property stays pure and a stored
        observation keeps answering what it answered when it was taken.
        Deriving it here would make an in-memory value's attribute depend
        on the filesystem at access time and would put an impure read
        below :func:`observe_listeners`, which this module promises at the
        top not to do.
        """
        if not self.unit:
            return False
        return self.unit.endswith(".scope") or self.runtime_created

    def as_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "pid": self.pid,
            "process": self.process,
            "unit": self.unit,
            "scope": self.scope,
            "attributed": self.attributed,
        }


@dataclass(frozen=True)
class ListenerReport:
    """What one ``ss`` run saw, or why it saw nothing.

    ``error`` and ``listeners`` are not merely independent — an error
    means the caller must not treat the empty list as *"nothing is
    listening"*.  Every consumer here checks ``ok`` before judging.
    """

    listeners: tuple[Listener, ...] = ()
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def unattributed(self) -> tuple[int, ...]:
        """Ports seen with nobody named — evidence, never a finding."""
        return tuple(sorted({x.port for x in self.listeners if not x.attributed}))


def _unit_from_cgroup(cgroup: str) -> tuple[str | None, str | None]:
    """``(unit, scope)`` from a ``/proc/<pid>/cgroup`` line.

    Scope comes from the *path*, not from the unit name: a user unit
    lives under ``…/user@1000.service/app.slice/`` and a system one
    under ``/system.slice/``.  That is the scope-aware identity
    ``services.yaml`` already keys on, and getting it free is the reason
    ``/proc`` beat ``systemctl show -p MainPID`` — which needs to know
    the scope *before* it can ask (``sysadmin.service`` returns
    ``MainPID=0`` on the user bus, being a system unit).

    **The line is split on its first two colons, never its last.**
    ``cgroup(5)`` is ``hierarchy-ID:controller-list:cgroup-path`` and
    only the first two fields are colon-free — the *path* may contain
    as many as it likes, because systemd escapes a unit name's ``/``
    and leaves its ``:`` alone.  ``rpartition`` was the obvious reading
    and is wrong for exactly the units that have one: a D-Bus activated
    service sits at
    ``…/user@1000.service/app.slice/app-dbus\\x2d:1.2\\x2dorg.kde.kdeconnect.slice/dbus-:1.2-org.kde.kdeconnect@0.service``,
    where taking the last field drops the ``dbus-`` prefix from the unit
    **and** the whole ``/user@1000.service/`` prefix from the path, so
    the scope test below cannot see it and stamps a user unit
    ``system``.  Found 2026-08-27 by ``SNAG-PORT-001``'s live drive:
    1716 is the first mis-parsed listener to fall inside an audited
    band, so the widening is what made a five-month-old parse visible.
    """
    line = cgroup.strip().rsplit("\n", 1)[-1]
    path = line.split(":", 2)[2] if line.count(":") >= 2 else line
    segment = path.rstrip("/").rsplit("/", 1)[-1]
    if not segment.endswith(_UNIT_SUFFIXES):
        return None, None
    scope = SCOPE_USER if "/user@" in path else SCOPE_SYSTEM
    return segment, scope


def _read_cgroup(pid: int) -> str | None:
    try:
        return Path(f"/proc/{pid}/cgroup").read_text(encoding="utf-8")
    except OSError:
        # The process exited between ``ss`` printing it and us reading,
        # or it belongs to another user with a hidepid mount.  Both are
        # "no attribution", not an error for the run.
        return None


def _list_names(directory: Path) -> Iterable[str]:
    """Every entry in ``directory``, by name.  Raises ``OSError`` if it cannot."""
    return [entry.name for entry in directory.iterdir()]


def runtime_unit_names(
    lister: Callable[[Path], Iterable[str]] = _list_names,
) -> tuple[dict[str, frozenset[str]], tuple[str, ...]]:
    """Units each systemd manager created at runtime, by scope.

    **A proxy for ``Transient=yes``, and it under-reports — which is the
    whole reason this is added to the ``.scope`` suffix rather than
    substituted for it.**  Measured 2026-08-28: ``init.scope`` reports
    ``Transient=yes`` from *both* managers and appears in *neither*
    directory, so a rule that replaced the suffix test with this listing
    would stop recognising it.  Additive cannot subtract — the posture
    ``ops_claims`` rule 1 takes for its markers — and on this box the
    union is exactly complete: the suffix catches ``init.scope`` and the
    two app scopes, the listing catches the eight ``app-*@<id>`` and
    ``dbus-:N.N-*`` services, and together they are every
    ``Transient=yes`` unit observed.

    **The names need no unescaping.**  systemd writes the escaped unit
    name as the filename and the same escaped name into the cgroup path,
    so the string :func:`_unit_from_cgroup` returns compares directly —
    ``\\x2d``, ``@`` and ``:`` included.  Measured against the live box:
    of 14 attributed user listeners exactly 4 match a transient file, and
    they are exactly the four per-launch holders
    (``app-code-oss-112152.scope``, ``app-steam@…service``,
    ``app-appimagekit_…@…service``, ``dbus-:1.2-org.kde.kdeconnect@0.service``);
    the ten hand-written services match nothing.

    **An unreadable directory degrades to the suffix rule and says so.**
    That is the *noisy* direction — fewer units recognised as transient
    means more findings — and it is chosen deliberately: claiming
    transience on a failed read would suppress a genuine collision on the
    strength of not having looked, which is the estate judge's rule 2.
    The problems are returned rather than swallowed, so a caller can put
    "we could not tell" where it belongs instead of serving it as
    "nothing was transient".
    """
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime) if runtime else Path("/run/user") / str(os.getuid())
    user_dir = base / "systemd" / "transient"
    names: dict[str, frozenset[str]] = {}
    problems: list[str] = []
    for scope, directory in (
        (SCOPE_USER, user_dir),
        (SCOPE_SYSTEM, SYSTEM_TRANSIENT_DIR),
    ):
        try:
            names[scope] = frozenset(lister(directory))
        except OSError as exc:
            names[scope] = frozenset()
            problems.append(
                f"{directory} would not list ({exc.__class__.__name__}: {exc})"
            )
    return names, tuple(problems)


def observe_listeners(
    runner: Runner = subprocess.run,
    cgroup_reader: Callable[[int], str | None] = _read_cgroup,
    runtime_reader: Callable[
        [], tuple[dict[str, frozenset[str]], tuple[str, ...]]
    ] = runtime_unit_names,
) -> ListenerReport:
    """Every listening TCP port, with the unit holding it where visible.

    ``ss -H -ltnp``: ``-p`` is the whole difference from estate-manager's
    call and costs nothing unprivileged for our own processes.  A port
    bound on both IPv4 and IPv6 prints twice with the same pid, so
    ``(port, pid)`` is deduplicated — otherwise ``port_shared`` would
    fire on every dual-stack server on the box.

    The transient directories are listed **once per sweep** and not once
    per listener: the answer is a property of the box at this instant,
    and re-reading it per port would let two listeners in one report
    disagree about the same unit.  A directory that would not list costs
    :attr:`Listener.runtime_created` and nothing else — see
    :func:`runtime_unit_names` for why that degrades toward noise rather
    than toward silence.
    """
    try:
        completed = runner(
            ["ss", "-H", "-ltnp"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return ListenerReport(error=f"could not run ss: {exc}")

    if completed.returncode != 0:
        detail = (completed.stderr or "").strip() or "no stderr"
        return ListenerReport(error=f"ss exited {completed.returncode}: {detail}")

    runtime_names, runtime_problems = runtime_reader()
    for problem in runtime_problems:
        logger.warning("transient_dir_unreadable", extra={"detail": problem})

    seen: set[tuple[int, int | None]] = set()
    cgroups: dict[int, str | None] = {}
    listeners: list[Listener] = []

    for line in (completed.stdout or "").splitlines():
        fields = line.split()
        if len(fields) < 4:
            continue
        # 0.0.0.0:8080, [::]:8080, *:8080, 127.0.0.1:8400
        port_text = fields[3].rpartition(":")[2]
        if not port_text.isdigit():
            continue
        port = int(port_text)

        holders = _USERS.findall(line)
        if not holders:
            if (port, None) not in seen:
                seen.add((port, None))
                listeners.append(Listener(port=port))
            continue

        for process, pid_text in holders:
            pid = int(pid_text)
            if (port, pid) in seen:
                continue
            seen.add((port, pid))
            if pid not in cgroups:
                cgroups[pid] = cgroup_reader(pid)
            raw = cgroups[pid]
            unit, scope = _unit_from_cgroup(raw) if raw else (None, None)
            listeners.append(
                Listener(
                    port=port,
                    pid=pid,
                    process=process,
                    unit=unit,
                    scope=scope,
                    cgroup=(raw.strip().rsplit("\n", 1)[-1] if raw else None),
                    runtime_created=bool(
                        unit and unit in runtime_names.get(scope or "", frozenset())
                    ),
                )
            )

    return ListenerReport(listeners=tuple(listeners))


# --------------------------------------------------------------------------
# The estate's registry table
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PortClaim:
    """One row of the estate's port registry table.

    ``line`` is carried so a duplicate can name *both* offending rows.
    A finding that says "port 8100 is claimed twice" without saying
    where is a count again, which is the thing Session 46 spent itself
    removing.
    """

    port: int
    project: str
    role: str
    line: int


def parse_port_registry(document: str) -> list[PortClaim]:
    """Claimed rows from the markdown table, **duplicates preserved**.

    This is a second parser of a document estate-manager already
    parses, and that is a cost worth naming rather than hiding.  Theirs
    lives in ``estate_service.audit.checks.ports``, which is the
    *service* and not ``estate-lib`` — the only estate package this
    repository depends on — so it cannot be imported here.  The reply
    to "then share it" is that the two parsers answer different
    questions: theirs folds rows into ``claimed_ports``, a ``set``,
    which is precisely why a duplicate row has always been invisible to
    it.  A shared parser would have to return the thing their check
    discards.

    Kept deliberately no stricter than theirs on everything except the
    port number: the table is prose-heavy and a parser demanding a
    shape breaks the moment someone writes a useful sentence in it.
    Rows claiming nothing (``_free — next frontend allocation_``) are
    skipped, as there.
    """
    claims: list[PortClaim] = []
    for number, raw in enumerate(document.splitlines(), start=1):
        match = _ROW.match(raw.strip())
        if not match:
            continue
        port_text, project, role = match.groups()
        project = project.strip()
        if not project or _UNALLOCATED.search(project):
            continue
        claims.append(
            PortClaim(
                port=int(port_text),
                project=project,
                role=role.strip(),
                line=number,
            )
        )
    return claims


def _registry_project_key(project: str) -> str:
    """Fold a registry project cell for comparison.

    The cell is markdown prose: ``_syncthing_`` carries italics,
    ``Alfred`` and ``SportsAnalyser`` carry the case of a directory
    name, and nothing in the table promises to be an id.  Emphasis
    markers are stripped before :func:`~sysadmin.units.scan.normalise`
    because ``_syncthing_`` and ``syncthing`` are the same claim.
    """
    return normalise(project.strip().strip("*_`"))


# --------------------------------------------------------------------------
# Declarations from services.yaml
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DeclaredPort:
    """A ``services.yaml`` entry asserting that a port belongs to a unit.

    The pair is the thing nothing has ever checked.  ``services.yaml``
    has carried ``port:`` beside ``systemd: {unit, scope}`` since
    Session 35 and the two have only ever been read separately — the
    port by the ``http``/``tcp`` check, the unit by the ``systemd``
    one — so a health check could be green against a process the tray's
    restart button would never touch.
    """

    name: str
    port: int
    unit: str
    scope: str
    project: str | None = None


def declared_ports(services: Iterable[Any]) -> list[DeclaredPort]:
    """The ``services.yaml`` entries that assert a port↔unit pair.

    Entries missing either half are skipped rather than half-checked:
    a ``kind: http`` entry with no ``systemd`` block claims nothing
    about a unit, and asserting one for it would be this module
    inventing the thing it exists to verify.
    """
    declared: list[DeclaredPort] = []
    for entry in services:
        port = getattr(entry, "port", None)
        unit = getattr(entry, "unit", None)
        if not port or not unit:
            continue
        declared.append(
            DeclaredPort(
                name=getattr(entry, "name", "") or "",
                port=int(port),
                unit=unit,
                scope=getattr(entry, "scope", SCOPE_USER) or SCOPE_USER,
                project=getattr(entry, "project", None),
            )
        )
    return declared


# --------------------------------------------------------------------------
# Findings — the pure half
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PortFinding:
    """One disagreement about one port.

    ``port`` is the identity, not ``kind``: two kinds landing on one
    port are one thing to look at, and a title carrying the kind would
    fork the alert row the day a second kind arrives for the same port.
    That is :mod:`sysadmin.estate.judgements` rule 5 and Session 46's
    naming rule, arriving at the same place from opposite directions.
    """

    port: int
    kind: str
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def is_collision(self) -> bool:
        return self.kind in COLLISION_KINDS

    def as_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "kind": self.kind,
            "summary": self.summary,
            "detail": dict(self.detail),
            "collision": self.is_collision,
        }


@dataclass(frozen=True)
class PortReport:
    """Everything the port check saw and concluded in one sweep."""

    findings: tuple[PortFinding, ...] = ()
    listeners: tuple[Listener, ...] = ()
    error: str | None = None
    #: Registry rows whose project cell names nothing declared under
    #: ``~/projects``.  Evidence rather than a finding — see
    #: :func:`judge_ports`.
    unknown_registry_projects: tuple[str, ...] = ()
    registry_document: str | None = None
    registry_rows: int = 0
    #: Why the two *document* comparisons did not run, when the two
    #: *live* ones did.  A separate field from ``error`` because the two
    #: halves fail independently and a partial run must not read as a
    #: total one: ``ss`` answering while the registry document has moved
    #: is a real and unremarkable state, and reporting "no duplicate
    #: rows" off an unread table is the check quietly switching itself
    #: off.  ``ok`` stays true — the run judged something and may sweep
    #: what it judged.
    registry_error: str | None = None
    #: The registry's jurisdiction this run used, carried so
    #: :meth:`unit_ports` can answer "one port *that the registry
    #: governs*" without the caller re-reading config.  A unit holding
    #: 8100 and an ephemeral 45312 holds one port worth advising on.
    audited_ranges: tuple[tuple[int, int], ...] = ()

    @property
    def ok(self) -> bool:
        return self.error is None

    @property
    def collisions(self) -> tuple[PortFinding, ...]:
        """The findings that alert — a live disagreement, not a stale row."""
        return tuple(f for f in self.findings if f.is_collision)

    @property
    def advice(self) -> tuple[PortFinding, ...]:
        return tuple(f for f in self.findings if not f.is_collision)

    def unit_ports(self, audited_only: bool = False) -> dict[str, list[int]]:
        """``"scope:unit"`` → the ports it holds, ascending.

        The map ``SNAG-UNITS-001``'s fix reads: a unit holding exactly
        one port in the audited range can be advised as ``kind: http``
        with a real url instead of the liveness-only ``kind: systemd``
        the sweep has always emitted.  Transient session scopes are
        excluded — ``app-code-oss-26348.scope`` holds four ports and is
        nobody's service.

        ``audited_only`` is what the snippet uses.  A backend also
        holding an ephemeral debug port would otherwise fall through to
        the weaker advice for a reason that has nothing to do with the
        port anyone cares about — and the range is the registry's own
        statement of which ports are services.
        """
        held: dict[str, set[int]] = {}
        for listener in self.listeners:
            if not listener.attributed or listener.transient:
                continue
            if audited_only and not in_range(listener.port, self.audited_ranges):
                continue
            key = f"{listener.scope}:{listener.unit}"
            held.setdefault(key, set()).add(listener.port)
        return {key: sorted(ports) for key, ports in sorted(held.items())}

    def transient_ports(self) -> dict[str, list[int]]:
        """``"scope:unit"`` → the ports a *session scope* holds, ascending.

        The complement of :meth:`unit_ports`, and it exists because that
        method's exclusion is correct for its consumer and blinding for
        another.  :mod:`sysadmin.units.recommendations` reads
        ``unit_ports`` to decide whether a unit can be advised as ``kind:
        http``; a session scope is nobody's service and emitting a health
        check for one would be this module inventing the thing it exists
        to verify.  The estate judge reads the same map to answer *who
        holds a breached port*, and there "an editor's dev server" is the
        single most useful thing that can be said about it.

        **A separate key rather than a flag inside ``unit_ports``.**  One
        field whose two consumers want opposite safe defaults is Session
        48's ``UnitFinding.enabled`` trap — absent evidence must read as
        "not armed" for one and "suppress the advice" for the other — and
        widening ``unit_ports`` would make the snippet gate learn about
        transience in order to keep behaving exactly as it does now.

        The holder key is stored **as observed**, scope number and all
        (``user:app-code-oss-26348.scope``).  That is evidence and never
        an identity: :attr:`Listener.transient` exists precisely because
        the number changes on every login, so nothing downstream may
        dedup, title or resolve on it.
        """
        held: dict[str, set[int]] = {}
        for listener in self.listeners:
            if not listener.attributed or not listener.transient:
                continue
            key = f"{listener.scope}:{listener.unit}"
            held.setdefault(key, set()).add(listener.port)
        return {key: sorted(ports) for key, ports in sorted(held.items())}

    def as_blob(self, limit: int = 200) -> dict[str, Any]:
        """The JSONB payload stored under ``findings['ports']``.

        Counts are scalars beside the truncated lists, Session 24's
        rule: a count summed from a capped list is a lower bound that
        reads like a total.
        """
        return {
            "ok": self.ok,
            "error": self.error,
            "registry_document": self.registry_document,
            "registry_rows": self.registry_rows,
            "registry_error": self.registry_error,
            "findings_count": len(self.findings),
            "collisions_count": len(self.collisions),
            "advice_count": len(self.advice),
            "listeners_count": len(self.listeners),
            "attributed_count": sum(1 for x in self.listeners if x.attributed),
            "unattributed_ports": sorted(
                {x.port for x in self.listeners if not x.attributed}
            )[:limit],
            "unknown_registry_projects": list(self.unknown_registry_projects)[:limit],
            "findings": [f.as_dict() for f in self.findings][:limit],
            "unit_ports": self.unit_ports(),
            "unit_audited_ports": self.unit_ports(audited_only=True),
            # Neither ``unit_ports`` nor ``unattributed_ports`` could
            # hold these: a session scope *is* attributed, so it fell
            # out of both and the port vanished from the record
            # entirely. A consumer then could not tell "nobody is
            # attributable" (5432, 8601 — root-owned, containerised)
            # from "attributable, and to something we chose not to write
            # down", which is ``ports_checked``'s rule one layer down.
            "transient_ports": self.transient_ports(),
        }


@dataclass(frozen=True)
class PortAttribution:
    """Who held each port, as of one stored sweep.

    Built from the sweep's blob rather than by running ``ss`` again,
    which is the whole reason it is a value: the estate judge runs
    hourly and the sweep every six hours, so a second call would give
    two answers to one question at two different moments and neither
    surface would say which it used.  ``observed_at`` carries the
    sweep's own timestamp so a consumer can see the age instead of
    assuming it is now — the rule
    ``GET /api/sysadmin/briefing/preview`` learned the hard way, where
    ``generated_at`` stamped the request and could never express
    staleness.
    """

    holders: Mapping[int, str] = field(default_factory=dict)
    #: Ports whose holder is a session scope, kept in their own map
    #: rather than flagged inside ``holders`` so that a consumer which
    #: never asks about transience cannot silently start receiving it.
    transient_holders: Mapping[int, str] = field(default_factory=dict)
    observed_at: str | None = None
    #: Ports the sweep **saw listening** and could not name a holder for
    #: — root-owned and containerised sockets, 5432 and 8601 on this box.
    #:
    #: ``None`` means the stored sweep cannot answer the question at all:
    #: there was no row, or ``observe_listeners`` failed and returned no
    #: listeners, or the blob predates the key.  That is a third state
    #: and not an empty set, for :meth:`reading`'s reason.
    unattributed: frozenset[int] | None = None

    def of(self, port: int) -> dict[str, Any] | None:
        """``{"unit", "scope", "transient", "observed_at"}``, or ``None``.

        ``transient`` is always present and always a bool, never absent
        on the common path: a caller writing ``holder.get("transient")``
        against a dict that omits the key on real units would read
        every service on the box as non-transient *by accident* rather
        than by observation, which is the distinction this field was
        added to make.
        """
        holder = self.holders.get(port)
        transient = False
        if not holder:
            holder = self.transient_holders.get(port)
            transient = bool(holder)
        if not holder:
            return None
        scope, _, unit = holder.partition(":")
        return {
            "unit": unit,
            "scope": scope,
            "transient": transient,
            "observed_at": self.observed_at,
        }

    def reading(self, port: int) -> dict[str, Any]:
        """What the sweep knew about this port — always an answer.

        :meth:`of` answers *who held it* and returns ``None`` for four
        different reasons.  This answers *what the evidence says*, and
        it exists because those four reasons are not one fact:

        ``held``
            a real unit holds it.
        ``transient``
            a session scope holds it — an editor's dev server.
        ``unattributed``
            the sweep **saw** the port listening and could not name a
            holder.  Root-owned and containerised sockets; the estate's
            own check is blind here too, since it runs ``ss`` without
            ``-p``.
        ``unswept``
            the sweep observed successfully and **did not see this port
            at all**, so the listener started after it ran.  This is the
            state ``SNAG-ESTATE-009`` is about, and until 2026-08-29 it
            was indistinguishable from ``unattributed``.
        ``unknown``
            there is no usable sweep: no stored row, a failed
            observation, or a blob written before the key existed.

        **This is ``ports_checked``'s rule, and it is the sibling of the
        collapse Session 57 fixed one field over.**  The comment above
        :meth:`transient_ports` in this module records that a session
        scope fell out of both stored maps, so ``holder`` came back
        ``None`` and a consumer could not tell *nobody is attributable*
        from *attributable, and to something we chose not to write
        down*.  Fixing that left the other half standing: a consumer
        still could not tell *nobody is attributable* from *the sweep
        never looked*.  The discriminator — ``unattributed_ports`` — has
        been in the blob since Session 26c and no consumer read it.

        ``observed_at`` rides along because it is the age of whatever
        this says, and a reading with no date is a claim with no
        evidence behind it.  It is the same value :meth:`of` carries and
        cannot disagree with it: both are read off one attribution in
        one call.

        The stated limit: ``unattributed_ports`` is truncated at the
        blob's ``limit``, so a box with more unattributable listeners
        than that would report some of them ``unswept``.  That fails
        towards *"the evidence is silent"* rather than towards a false
        claim of having looked, which is the direction
        :mod:`sysadmin.core.schema_guard` fails in and the opposite of
        the direction that would matter here.
        """
        if port in self.holders:
            state = "held"
        elif port in self.transient_holders:
            state = "transient"
        elif self.unattributed is None:
            state = "unknown"
        elif port in self.unattributed:
            state = "unattributed"
        else:
            state = "unswept"
        return {"reading": state, "observed_at": self.observed_at}


def attribution_from_blob(
    blob: Mapping[str, Any] | None, observed_at: str | None = None
) -> PortAttribution:
    """Invert a stored sweep's holder maps into port → holder.

    Defensive throughout: both keys are absent on every sweep written
    before Session 26c, ``transient_ports`` on every sweep written
    before Session 57, and a port held by two units is dropped rather
    than attributed to whichever sorted first — that case has its own
    finding (``port_shared``) and a guess here would contradict it.

    **The ambiguity rule spans both maps.**  A dev server and a real
    service on one port is exactly the state a reader needs told, and
    naming either one of them as *the* holder would be this function
    answering a question :func:`judge_ports` deliberately reports as a
    disagreement.  So the count is taken across the union and a port
    with two names is dropped whichever map each name came from.
    """
    if not blob:
        return PortAttribution(observed_at=observed_at)

    counts: dict[int, list[str]] = {}
    transient: set[int] = set()
    for key, is_transient in (("unit_ports", False), ("transient_ports", True)):
        raw = blob.get(key)
        if not isinstance(raw, dict):
            continue
        for holder, held in raw.items():
            if not isinstance(held, list):
                continue
            for port in held:
                try:
                    number = int(port)
                except (TypeError, ValueError):
                    continue
                counts.setdefault(number, []).append(str(holder))
                if is_transient:
                    transient.add(number)

    unique = {port: names[0] for port, names in counts.items() if len(names) == 1}
    return PortAttribution(
        holders={p: n for p, n in unique.items() if p not in transient},
        transient_holders={p: n for p, n in unique.items() if p in transient},
        observed_at=observed_at,
        unattributed=_seen_unattributed(blob),
    )


def _seen_unattributed(blob: Mapping[str, Any]) -> frozenset[int] | None:
    """The ports the sweep saw and could not name, or ``None``.

    **Gated on the sweep's own ``ok``, which is the half that is easy to
    miss.**  A failed :func:`observe_listeners` returns the error and
    *no* listeners, so ``unattributed_ports`` serialises as ``[]`` — and
    an empty list read as evidence would make every breached port
    ``unswept``, which is a confident statement about a sweep that never
    looked.  ``ports_checked``'s rule at the size of one key:
    zero-because-clean must not be served as zero-because-blind.

    ``None`` for a blob written before Session 26c as well, where the
    key is simply absent and the question is equally unanswerable.
    """
    if not blob.get("ok"):
        return None
    raw = blob.get("unattributed_ports")
    if not isinstance(raw, list):
        return None
    seen: set[int] = set()
    for port in raw:
        # `isinstance(True, int)` is True, so a bool would land as port 1
        # and read a live listener as unattributable. Refused explicitly,
        # `judge_audit_findings` rule 3's treatment of the same trap.
        if isinstance(port, bool):
            continue
        try:
            seen.add(int(port))
        except (TypeError, ValueError):
            continue
    return frozenset(seen)


def in_range(port: int, ranges: Sequence[tuple[int, int]]) -> bool:
    """Whether the registry governs this port at all.

    The same jurisdiction estate-manager's check uses, and duplicated
    here for the reason ``EstateJudgeConfig.base_url`` is duplicated:
    deriving it across a repository boundary would make this check go
    quiet when the other side is renamed.  A test asserts the two agree.
    """
    return any(low <= port <= high for low, high in ranges)


def judge_ports(
    report: ListenerReport,
    declared: Sequence[DeclaredPort],
    claims: Sequence[PortClaim],
    unit_projects: Mapping[str, str],
    project_aliases: Mapping[str, Sequence[str]],
    *,
    audited_ranges: Sequence[tuple[int, int]] = DEFAULT_AUDITED_RANGES,
    ignore_ports: Sequence[int] = (),
    registry_document: str | None = None,
    registry_error: str | None = None,
) -> PortReport:
    """The four comparisons, in one pass, on data somebody else fetched.

    Pure: every input is a value.  ``report`` carries its own failure,
    and a failed observation produces a report with the error and **no
    findings** — never an empty success, because the caller sweeps on
    the strength of what it judged.

    ``unit_projects`` maps ``"scope:unit"`` to a project *name* and comes
    from the sweep that already computed it (:func:`scan_units`);
    ``project_aliases`` maps that name to every string the estate might
    call it by — the directory name and the manifest id, which differ
    for a third of the projects on this box (``SportsAnalyser`` /
    ``sports-analyser``).
    """
    if not report.ok:
        return PortReport(
            error=report.error,
            registry_document=registry_document,
            registry_rows=len(claims),
            registry_error=registry_error,
        )

    ignored = set(ignore_ports)
    findings: list[PortFinding] = []

    # --- Live: two units on one port -------------------------------------
    holders: dict[int, dict[str, Listener]] = {}
    for listener in report.listeners:
        if not listener.attributed or listener.transient:
            continue
        holders.setdefault(listener.port, {})[
            f"{listener.scope}:{listener.unit}"
        ] = listener

    for port in sorted(holders):
        if port in ignored:
            continue
        keys = sorted(holders[port])
        if len(keys) < 2:
            continue
        findings.append(
            PortFinding(
                port=port,
                kind=PORT_SHARED,
                summary=(
                    f"port {port} is held by {len(keys)} different units "
                    f"({', '.join(keys)}); one of them lost the bind, or both "
                    "set SO_REUSEPORT and traffic is being split"
                ),
                detail={
                    "port": port,
                    "units": keys,
                    "pids": sorted(
                        x.pid for x in holders[port].values() if x.pid is not None
                    ),
                },
            )
        )

    # --- Live: services.yaml names the wrong unit -------------------------
    for entry in declared:
        if entry.port in ignored:
            continue
        seen = holders.get(entry.port)
        if not seen:
            # Nothing attributed is listening.  Silence is availability's
            # question and it already has an owner — the sysadmin agent's
            # ``% unreachable`` family and the estate's
            # ``claimed_but_silent`` warn.  A second owner closes a row
            # while the first still holds it true.
            continue
        expected = f"{entry.scope}:{entry.unit}"
        if expected in seen:
            continue
        actual = sorted(seen)
        findings.append(
            PortFinding(
                port=entry.port,
                kind=WRONG_UNIT,
                summary=(
                    f"services.yaml checks port {entry.port} as "
                    f"{entry.name!r} and says the unit behind it is "
                    f"{entry.unit} ({entry.scope}), but the port is held by "
                    f"{', '.join(actual)}"
                ),
                detail={
                    "port": entry.port,
                    "service": entry.name,
                    "declared_unit": entry.unit,
                    "declared_scope": entry.scope,
                    "actual_units": actual,
                    "project": entry.project,
                },
            )
        )

    # --- Document: one port, two registry rows ----------------------------
    by_port: dict[int, list[PortClaim]] = {}
    for claim in claims:
        by_port.setdefault(claim.port, []).append(claim)

    for port in sorted(by_port):
        rows = by_port[port]
        if port in ignored or len(rows) < 2:
            continue
        findings.append(
            PortFinding(
                port=port,
                kind=DUPLICATE_CLAIM,
                summary=(
                    f"port {port} is claimed by {len(rows)} rows of the port "
                    f"registry ({', '.join(sorted({r.project for r in rows}))}); "
                    "the audit folds the table into a set, so it cannot see this"
                ),
                detail={
                    "port": port,
                    "rows": [
                        {"line": r.line, "project": r.project, "role": r.role}
                        for r in rows
                    ],
                },
            )
        )

    # --- Document: the registry names the wrong project --------------------
    alias_keys = {
        name: {normalise(a) for a in aliases if a}
        for name, aliases in project_aliases.items()
    }
    every_alias = {key for keys in alias_keys.values() for key in keys}
    unknown: set[str] = set()

    for port in sorted(by_port):
        if port in ignored or not in_range(port, audited_ranges):
            continue
        seen = holders.get(port)
        if not seen:
            continue
        # One holder only: with two, ``port_shared`` above is the finding
        # and attributing the row to either would be a guess.
        keys = sorted(seen)
        if len(keys) != 1:
            continue
        owner = unit_projects.get(keys[0])
        if not owner:
            # The unit matched no project on disk.  Not knowing is not a
            # mismatch — :mod:`sysadmin.monitor.collation`'s rule 1.
            continue
        owner_keys = alias_keys.get(owner) or {normalise(owner)}
        for claim in by_port[port]:
            claimed = _registry_project_key(claim.project)
            if not claimed or claimed in owner_keys:
                continue
            if claimed not in every_alias:
                # The row names something that is not a project here at
                # all — a third-party daemon, or a name that has drifted
                # from its manifest.  Recorded as evidence, because
                # "wrong project" and "not a project" are different
                # faults and only the first is this check's business.
                unknown.add(claim.project)
                continue
            findings.append(
                PortFinding(
                    port=port,
                    kind=WRONG_PROJECT,
                    summary=(
                        f"the port registry gives {port} to {claim.project}, but "
                        f"the unit holding it ({keys[0]}) belongs to {owner}"
                    ),
                    detail={
                        "port": port,
                        "registry_project": claim.project,
                        "registry_line": claim.line,
                        "holding_unit": keys[0],
                        "actual_project": owner,
                    },
                )
            )

    findings.sort(key=lambda f: (KIND_ORDER.index(f.kind), f.port))
    return PortReport(
        findings=tuple(findings),
        listeners=report.listeners,
        unknown_registry_projects=tuple(sorted(unknown)),
        registry_document=registry_document,
        registry_rows=len(claims),
        registry_error=registry_error,
        audited_ranges=tuple(tuple(r) for r in audited_ranges),  # type: ignore[misc]
    )
