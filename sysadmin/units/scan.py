"""Systemd unit discovery — read the installed units, match them to projects.

Tier 1 of Session 26.  The problem this solves is bookkeeping rot: every
new service under ``~/projects`` has to be hand-registered in
``services.yaml``, nobody remembers, and a unit that was never wired
looks identical to one that is working fine.  Worse in
the other direction — a retired project leaves its units installed, and
they either fail on every start or silently do nothing.

The module is **pure**: no DB, no FastAPI, no subprocesses.  Give it two
directories and a list of projects, get a list of findings.  That is not
architectural tidiness for its own sake — it is what lets the tests build
a fake estate under ``tmp_path`` and assert on real parsing rather than
on mocks, which is the lesson Sessions 23 and 24 both paid for.

Four categories, and the boundary between them is the whole point:

``monitored``
    The unit (or, for a ``Type=oneshot`` service, its timer) is
    already declared in ``services.yaml``.  Nothing to do.

``unmonitored``
    The unit maps to a project that still exists, and nothing wires it.
    This is the case the session was asked for.  Advice: a
    ``services.yaml`` snippet carrying the project's manifest id.

``orphaned``
    The unit's own declared path is gone — the project was archived,
    moved or deleted and the unit stayed behind.  A unit like this is
    not merely unwatched, it is broken: ``WorkingDirectory`` pointing at
    a missing directory makes systemd fail the start job outright.
    Advice: remove it.

    An orphan that is also **enabled** is reported as ``armed``, and
    that flag is what the agent alerts on individually.  A disabled
    orphan is debt; an armed one fails on every trigger and, if its
    restart loop can never reach the start limit
    (:func:`restart_is_bounded`), does so for ever without systemd ever
    marking it ``failed``.  Both signals are read off the filesystem —
    an enablement symlink and four keys of unit text — so this module
    keeps its promise of no subprocesses.

``host``
    Hand-written, maps to no project — ``pgbackrest-backup``,
    ``ethernet-optimise``.  These are real infrastructure and a silent
    stop matters (a backup that stopped a month ago looks exactly like
    one that ran), but they have no project directory, so a snippet
    naming a ``project:`` would be a lie — and an id resolving to nothing
    fails ``services.yaml`` at load.  Advice: an entry without one.

Distro units are excluded rather than categorised.  The test is
``is_symlink()``: ``systemctl enable`` installs a symlink into
``/usr/lib/systemd/system``, so on this box every packaged unit in
``/etc/systemd/system`` is a link and every hand-written one is a real
file.  That happens to be exactly the distinction we want and costs no
subprocess — the ``pacman -Qo`` ownership query it replaces would have
worked only on Arch.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, NamedTuple

# Categories.  Strings rather than an enum because they cross a JSONB
# column and an HTTP boundary, and both ends already speak strings.
MONITORED = "monitored"
UNMONITORED = "unmonitored"
ORPHANED = "orphaned"
HOST = "host"

#: Order findings are reported in — broken first, then unwired, then the
#: merely-undocumented.  ``monitored`` is not reported at all, only counted.
CATEGORY_ORDER = (ORPHANED, UNMONITORED, HOST)

#: The restart-limit family (SNAG-UNITS-002).  Deliberately **not** in
#: :data:`CATEGORY_ORDER`: the four categories above partition every
#: scanned unit and ``units_scanned`` is their sum, which is the one
#: arithmetic property :class:`~sysadmin.core.contracts.UnitScanSummary`
#: exists to make auditable.  A unit that is unbounded is *also*
#: monitored or host, so a fifth bucket would double-count it.  The same
#: shape ``armed`` already takes: a subset reported beside the sum, never
#: inside it.
RESTART_UNBOUNDED = "restart"

# Characters systemd allows in front of an ExecStart executable
# (``-`` ignore failure, ``@`` set argv[0], ``+``/``!``/``!!`` privilege
# escapes).  They are not part of the path and must come off before any
# filesystem test.
_EXEC_PREFIX_CHARS = "-@+!:"

# A unit whose name ends ``@.service`` is a *template*, instantiated as
# ``foo@arg.service``.  The template file itself runs nothing and has no
# project of its own.
_TEMPLATE_RE = re.compile(r"@\.[a-z]+$")

_SECTION_RE = re.compile(r"^\[(?P<name>[^\]]+)\]\s*$")

#: Unit suffixes worth scanning.  Sockets, paths and targets exist on this
#: box only as distro units, and a socket has no project of its own — it
#: hands off to a service that does.
UNIT_SUFFIXES = (".service", ".timer")


#: systemd's own defaults for the start rate limiter, from
#: ``systemd-system.conf(5)``: ``DefaultStartLimitIntervalSec=10s`` and
#: ``DefaultStartLimitBurst=5``.  Hard-coded rather than read from
#: ``systemctl show``, which would cost this module its purity for a
#: number that has not moved in a decade.  Confirmed against this box on
#: 2026-08-14; a host that overrides them in ``system.conf`` would make
#: :func:`restart_is_bounded` optimistic, which is the safe direction —
#: see its docstring.
DEFAULT_START_LIMIT_INTERVAL = 10.0
DEFAULT_START_LIMIT_BURST = 5

#: systemd's default ``RestartSec``, 100ms.  It matters more than it
#: looks: a unit declaring nothing but ``Restart=always`` restarts every
#: 100ms, so five starts fit inside the ten-second window easily and the
#: loop *does* terminate.  A rule that flagged every unguarded
#: ``Restart=`` would therefore be wrong about the majority of units it
#: fired on.
DEFAULT_RESTART_SEC = 0.1

#: Multipliers for systemd time-span suffixes (``systemd.time(7)``).
#: Longest first, so ``ms`` is not matched as ``m``.
_TIMESPAN_UNITS: tuple[tuple[str, float], ...] = (
    ("usec", 1e-6),
    ("us", 1e-6),
    ("msec", 1e-3),
    ("ms", 1e-3),
    ("seconds", 1.0),
    ("second", 1.0),
    ("sec", 1.0),
    ("s", 1.0),
    ("minutes", 60.0),
    ("minute", 60.0),
    ("min", 60.0),
    ("m", 60.0),
    ("hours", 3600.0),
    ("hour", 3600.0),
    ("hr", 3600.0),
    ("h", 3600.0),
    ("days", 86400.0),
    ("day", 86400.0),
    ("d", 86400.0),
    ("weeks", 604800.0),
    ("week", 604800.0),
    ("w", 604800.0),
)

_TIMESPAN_TOKEN = re.compile(r"(\d+(?:\.\d+)?)\s*([a-z]*)")


def parse_timespan(value: str | None) -> float | None:
    """A systemd time span in seconds, or ``None`` if it cannot be read.

    ``None`` is returned for anything unparseable **and is not the same
    as zero** — every caller treats "cannot read this" as "make no
    claim", which is the direction :mod:`sysadmin.monitor.collation`
    settled on for the same kind of question: a false positive here
    sends someone to rewrite a unit file that is fine.

    Handles the compound form (``1min 30s``) because systemd does, bare
    numbers as seconds because systemd does, and ``infinity``.
    """
    if value is None:
        return None
    text = value.strip().lower()
    if not text:
        return None
    if text in {"infinity", "inf"}:
        return float("inf")

    total = 0.0
    matched = False
    position = 0
    for token in _TIMESPAN_TOKEN.finditer(text):
        if token.start() != position and text[position : token.start()].strip():
            # Junk between tokens — refuse the whole value rather than
            # silently reading the half that parsed.
            return None
        position = token.end()
        number, suffix = token.group(1), token.group(2)
        if not suffix:
            multiplier = 1.0
        else:
            multiplier = next(
                (m for name, m in _TIMESPAN_UNITS if suffix == name), 0.0
            )
            if multiplier == 0.0:
                return None
        total += float(number) * multiplier
        matched = True

    if not matched or text[position:].strip():
        return None
    return total


def restart_is_bounded(
    restart: str | None,
    restart_sec: float | None,
    start_limit_interval: float | None,
    start_limit_burst: int | None,
) -> bool:
    """Whether a restart loop in this unit would ever reach ``failed``.

    **This is arithmetic, not the presence of a setting**, and the
    difference is the whole finding.  The obvious rule — "``Restart=``
    with no ``StartLimitBurst=`` is a runaway" — is wrong in both
    directions, and the live estate proves both:

    - ``personalassistant-backend.service`` declares no start limit, so
      systemd's default 5-starts-in-10s applies.  It also sets
      ``RestartSec=10``, which puts its starts ten seconds apart: the
      window can never hold five of them, the limit is unreachable, and
      the unit restarted **34,517 times** without once entering
      ``failed``.  A rule reading "no ``StartLimitBurst=``" gets the
      right answer here for the wrong reason, and would keep getting it
      until someone added a ``StartLimitBurst=`` that changed nothing.
    - A unit declaring only ``Restart=always`` restarts every 100ms
      (:data:`DEFAULT_RESTART_SEC`), so five starts fit in the ten-second
      window and the loop *is* terminal.  The naive rule calls this
      dangerous and it is not.

    So: the burst-th start happens ``restart_sec * (burst - 1)`` after
    the first, and the limiter fires only if that lands inside
    ``start_limit_interval``.  This is the same arithmetic Session 39
    did by hand for ``sysadmin.service`` — ``StartLimitIntervalSec=600``
    against ``RestartSec=10`` gives 40s < 600s, which is why that fix
    works.

    Returns ``True`` when the unit does not restart at all, and ``True``
    when a value could not be read: **not knowing is not an accusation**.
    """
    if restart is None or restart.strip().lower() in {"", "no"}:
        return True

    interval = (
        DEFAULT_START_LIMIT_INTERVAL
        if start_limit_interval is None
        else start_limit_interval
    )
    burst = DEFAULT_START_LIMIT_BURST if start_limit_burst is None else start_limit_burst

    # systemd documents either being zero as "rate limiting off".  A unit
    # that turns the limiter off and restarts for ever is the runaway in
    # its purest form, and it is a deliberate setting rather than an
    # oversight — which does not make it safe on a unit whose start job
    # cannot succeed.
    if interval <= 0 or burst <= 0:
        return False

    cadence = DEFAULT_RESTART_SEC if restart_sec is None else restart_sec
    if cadence == float("inf"):
        return False
    if burst == 1:
        # One start allowed in the window: the second start trips it
        # whenever it happens.
        return True
    return cadence * (burst - 1) < interval


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def parse_unit_text(text: str) -> dict[str, list[tuple[str, str]]]:
    """Parse unit-file text into ``{section: [(key, value), ...]}``.

    Not ``configparser``: systemd allows a key to repeat within a section
    and the repeats are *cumulative*, which ``configparser`` silently
    collapses.  ``ethernet-optimise.service`` has two ``ExecStart=``
    lines and dropping either would misreport what it runs.

    Backslash line-continuations are joined, comments (``#``, ``;``) at
    the start of a line are dropped, and anything before the first
    section header is ignored.
    """
    sections: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    pending: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if pending is not None:
            # Mid-continuation: comments are not recognised here, systemd
            # treats the joined result as one logical line.
            pending = f"{pending} {line.rstrip(chr(92))}".strip()
            if line.endswith("\\"):
                continue
            line, pending = pending, None
        else:
            if not line or line[0] in "#;":
                continue
            match = _SECTION_RE.match(line)
            if match:
                current = match.group("name")
                sections.setdefault(current, [])
                continue
            if line.endswith("\\"):
                pending = line[:-1].strip()
                continue

        if current is None or "=" not in line:
            continue
        key, _, value = line.partition("=")
        sections.setdefault(current, []).append((key.strip(), value.strip()))

    return sections


def expand_specifiers(value: str, home: str) -> str:
    """Expand the systemd specifiers that appear in a path.

    Only ``%h`` (home) and ``%%`` (a literal percent) are handled, and
    ``%h`` only meaningfully for user units — for a system unit it means
    the home of whatever ``User=`` names, which we cannot resolve without
    a passwd lookup.  Callers pass ``home=""`` for system scope, which
    leaves ``%h`` in place; the path test then fails and the unit falls
    through to name matching rather than matching something wrong.

    Every other specifier is left alone deliberately.  A half-expanded
    ``%i`` would produce a path that looks real and is not.
    """
    if "%" not in value:
        return value
    out = value.replace("%%", "\0")
    if home:
        out = out.replace("%h", home)
    return out.replace("\0", "%")


def _exec_paths(exec_line: str, home: str) -> list[str]:
    """Absolute paths mentioned in one ``ExecStart=`` line.

    Both the executable and its arguments count: ``ticktick-sync`` runs
    ``.../venv/bin/python3 .../sync_ticktick.py`` and the second path is
    the one that identifies the project.  Tokens that do not start with
    ``/`` after expansion are skipped, which drops flags, URLs and the
    ``%h``-in-a-system-unit case in one test.

    ``Environment=`` lines are *not* mined, though several carry project
    paths.  A ``PATH=`` value contains ``/usr/bin`` and friends, so
    harvesting it would match a project only by accident and match the
    wrong thing regularly.
    """
    tokens = exec_line.split()
    if not tokens:
        return []
    tokens[0] = tokens[0].lstrip(_EXEC_PREFIX_CHARS)

    paths: list[str] = []
    for token in tokens:
        candidate = expand_specifiers(token.strip("\"'"), home)
        if candidate.startswith("/"):
            paths.append(candidate)
    return paths


class UnitRelation(NamedTuple):
    """One ``[Unit]`` relation, as declared.

    A :class:`~typing.NamedTuple` rather than a dataclass so a
    :class:`UnitFile` stays hashable and a relation can be compared
    against a plain ``(directive, unit)`` tuple in a test without
    importing this class.
    """

    #: The directive verbatim — ``After``, ``Requires``, ``OnFailure``…
    directive: str
    #: The unit named, qualified to a full unit name.
    unit: str


#: ``[Unit]`` directives that assert one unit has something to do with
#: another, and which this module records.
#:
#: All nine express a relation systemd acts on when a unit starts, stops
#: or fails, which is the only property :func:`declared_relations` needs:
#: it answers "is there a declared reason these two units would fail in
#: the same breath", never "what exactly would systemd do".  Grading them
#: — treating ``Requires=`` as stronger evidence than ``Wants=`` — was
#: refused on measurement rather than on principle: the one live relation
#: on this box declares **both** (``estate-broker-provision.service``
#: carries ``After=mosquitto.service`` and ``Wants=mosquitto.service``),
#: so a grading would have no case that distinguishes it and would be a
#: rule tuned against zero observations, which is
#: ``units/ports.py`` rule 6's objection.
#:
#: ``Conflicts=`` is deliberately absent.  It is the one relation that is
#: *negative* — it says two units may not run together, so systemd stops
#: one to start the other — and a stop it performed on purpose is the
#: opposite of a fault propagating.  Including it would correlate a
#: successful handover with a crash.
RELATION_DIRECTIVES = (
    "After",
    "Before",
    "Requires",
    "Requisite",
    "Wants",
    "BindsTo",
    "PartOf",
    "Upholds",
    "OnFailure",
)


def qualify_unit(name: str) -> str:
    """A dependency name as systemd would resolve it.

    Bare stems are qualified to ``.service``, systemd's own default for
    an unsuffixed unit name.  Being wrong here is cheap in one direction
    only, which is why it is done at all: a name that resolves to
    nothing simply yields no relation, where leaving it unqualified
    would miss a real one.
    """
    return name if "." in name else f"{name}.service"


@dataclass(frozen=True)
class UnitFile:
    """One parsed unit file.

    Frozen because a unit file is a fact read off disk — nothing
    downstream has any business editing it, and immutability lets
    findings hold a reference rather than a copy.
    """

    name: str
    scope: str  # "user" | "system"
    path: str
    description: str | None = None
    service_type: str = "simple"
    working_directory: str | None = None
    exec_paths: tuple[str, ...] = ()
    exec_start: tuple[str, ...] = ()
    user: str | None = None
    #: For a ``.timer``: the unit it starts.  ``Unit=`` when given,
    #: otherwise systemd's default of the same stem with ``.service``.
    triggers: str | None = None
    #: No ``[Install]`` section — the unit cannot be enabled and is
    #: started by something else (a timer, or by hand).
    static: bool = True
    #: An enablement symlink for this unit exists under a ``*.wants/`` or
    #: ``*.requires/`` directory in its own scope — systemd will start it
    #: without anyone asking.  Read off the filesystem rather than from
    #: ``systemctl is-enabled``, which keeps this module free of
    #: subprocesses; the two agreed on all six live orphans when checked
    #: on 2026-08-14.
    enabled: bool = False
    #: ``Restart=`` verbatim, ``None`` when unset.
    restart: str | None = None
    #: ``RestartSec=`` in seconds, ``None`` when unset or unparseable.
    restart_sec: float | None = None
    #: ``StartLimitIntervalSec=`` in seconds and ``StartLimitBurst=``,
    #: ``None`` when unset.  Both are read from ``[Unit]`` *and*
    #: ``[Service]``: systemd moved them to ``[Unit]`` in v229 and still
    #: accepts the old placement, and a unit written before that move
    #: would otherwise read as declaring no limit at all.
    start_limit_interval: float | None = None
    start_limit_burst: int | None = None
    #: Every ``[Unit]`` relation this file declares, as
    #: ``(directive, unit name)`` pairs in the order read — see
    #: :data:`RELATION_DIRECTIVES`.  Pairs rather than one flat set of
    #: names because the directive is what a reader needs to see: being
    #: told two units are related is worth much less than being told one
    #: declares ``Requires=`` on the other.
    #:
    #: Read from ``[Unit]`` only, unlike ``StartLimit*`` two fields up.
    #: systemd has never accepted these anywhere else, so widening the
    #: read would invent a placement to be tolerant of.
    relations: tuple[UnitRelation, ...] = ()

    @property
    def restart_bounded(self) -> bool:
        """Whether a restart loop here would ever reach ``failed``.

        Thin wrapper over :func:`restart_is_bounded` so the arithmetic
        has one home; the finding, the alert and the API all read this.
        """
        return restart_is_bounded(
            self.restart,
            self.restart_sec,
            self.start_limit_interval,
            self.start_limit_burst,
        )

    @property
    def stem(self) -> str:
        return self.name.rsplit(".", 1)[0]

    @property
    def suffix(self) -> str:
        return "." + self.name.rsplit(".", 1)[-1]

    @property
    def is_timer(self) -> bool:
        return self.name.endswith(".timer")

    @property
    def is_oneshot(self) -> bool:
        return self.service_type == "oneshot"

    @property
    def declared_paths(self) -> tuple[str, ...]:
        """Paths this unit asserts must exist, ``WorkingDirectory`` first.

        Ordered because the first entry is what a dead-path finding
        quotes, and ``WorkingDirectory`` is the more specific claim: an
        ``ExecStart`` binary may legitimately live outside the project
        (``/usr/bin/curl``) while a ``WorkingDirectory`` never does.
        """
        paths: list[str] = []
        if self.working_directory:
            paths.append(self.working_directory)
        paths.extend(p for p in self.exec_paths if p not in paths)
        return tuple(paths)


def load_unit(path: Path, scope: str, home: str) -> UnitFile:
    """Read and parse one unit file.  Unreadable files parse as empty."""
    try:
        text = path.read_text(errors="replace")
    except OSError:
        text = ""

    sections = parse_unit_text(text)

    def first(section: str, key: str) -> str | None:
        for k, v in sections.get(section, []):
            if k == key:
                return v
        return None

    def every(section: str, key: str) -> list[str]:
        return [v for k, v in sections.get(section, []) if k == key]

    exec_lines = every("Service", "ExecStart")
    paths: list[str] = []
    for line in exec_lines:
        for candidate in _exec_paths(line, home):
            if candidate not in paths:
                paths.append(candidate)

    working_dir = first("Service", "WorkingDirectory")
    if working_dir:
        working_dir = expand_specifiers(working_dir, home)
        if not working_dir.startswith("/"):
            # Unexpanded specifier, or a relative path against RootDirectory.
            # Either way it is not a claim we can test.
            working_dir = None

    def either(key: str) -> str | None:
        """A key systemd accepts in ``[Unit]`` or (historically) ``[Service]``."""
        return first("Unit", key) or first("Service", key)

    burst_text = either("StartLimitBurst")
    try:
        burst = int(burst_text) if burst_text is not None else None
    except ValueError:
        burst = None

    name = path.name
    triggers = None
    if name.endswith(".timer"):
        triggers = first("Timer", "Unit") or f"{name.rsplit('.', 1)[0]}.service"

    # An *empty* assignment resets the list systemd has accumulated so
    # far, so it is honoured rather than read as "declares nothing".  It
    # cannot matter with one file and no drop-ins, and it is two lines;
    # dropping it would make this parse quietly wrong the day a drop-in
    # is read, which is the direction this module's other blind spots
    # already fail in.
    relations: list[UnitRelation] = []
    for key, value in sections.get("Unit", []):
        if key not in RELATION_DIRECTIVES:
            continue
        if not value.strip():
            relations = [r for r in relations if r.directive != key]
            continue
        for named in value.split():
            relation = UnitRelation(key, qualify_unit(named))
            if relation not in relations:
                relations.append(relation)

    return UnitFile(
        name=name,
        scope=scope,
        path=str(path),
        description=first("Unit", "Description"),
        service_type=(first("Service", "Type") or "simple"),
        working_directory=working_dir,
        exec_paths=tuple(paths),
        exec_start=tuple(exec_lines),
        user=first("Service", "User"),
        triggers=triggers,
        static="Install" not in sections,
        restart=first("Service", "Restart"),
        restart_sec=parse_timespan(first("Service", "RestartSec")),
        start_limit_interval=parse_timespan(
            either("StartLimitIntervalSec") or either("StartLimitInterval")
        ),
        start_limit_burst=burst,
        relations=tuple(relations),
    )


def enablement_links(base: Path) -> set[str]:
    """Unit names systemd has been told to start, from the symlinks alone.

    ``systemctl enable`` writes a symlink into ``<target>.wants/`` (or
    ``.requires/``) beside the unit directory, which is why
    :func:`sysadmin.units.recommendations.removal_command` disables
    before it deletes.  Reading those directories is therefore an exact
    answer to "will systemd start this on its own", with no subprocess —
    the same trade :func:`discover_units` already makes with
    ``is_symlink()`` for distro ownership.

    Matched on the **link name**, not its target.  An alias symlink can
    point at a differently-named unit, and following targets would make
    this depend on filesystem layout the sweep otherwise never touches.
    Checked against ``systemctl is-enabled`` on all six live orphans
    (2026-08-14): they agreed.
    """
    names: set[str] = set()
    if not base.is_dir():
        return names
    for wants in sorted(base.glob("*.wants")) + sorted(base.glob("*.requires")):
        if not wants.is_dir():
            continue
        for link in wants.iterdir():
            if link.name.endswith(UNIT_SUFFIXES):
                names.add(link.name)
    return names


def discover_units(
    user_dir: Path | str | None,
    system_dir: Path | str | None,
    home: str,
) -> tuple[list[UnitFile], list[str]]:
    """Load every hand-written unit from both scopes.

    Returns ``(units, excluded)``.  ``excluded`` holds the names filtered
    out as distro-owned or template units — reported as a count rather
    than discarded silently, because "we looked at 40 units and skipped
    6" is a checkable claim and "we found 34 units" is not.
    """
    units: list[UnitFile] = []
    excluded: list[str] = []

    for directory, scope, scope_home in (
        (user_dir, "user", home),
        # ``%h`` in a system unit means the ``User=``'s home, which needs
        # a passwd lookup this module will not do.  Left unexpanded.
        (system_dir, "system", ""),
    ):
        if not directory:
            continue
        base = Path(directory)
        if not base.is_dir():
            continue
        enabled = enablement_links(base)
        for entry in sorted(base.iterdir()):
            if not entry.name.endswith(UNIT_SUFFIXES):
                continue
            if _TEMPLATE_RE.search(entry.name):
                excluded.append(entry.name)
                continue
            if entry.is_symlink():
                # An enablement/alias symlink into /usr/lib — packaged.
                excluded.append(entry.name)
                continue
            if not entry.is_file():
                continue
            unit = load_unit(entry, scope, scope_home)
            # ``replace`` rather than a parameter on ``load_unit``: that
            # function's job is to turn text into a UnitFile, and
            # enablement is a fact about the *directory*, read once per
            # scope rather than once per unit.
            units.append(replace(unit, enabled=entry.name in enabled))

    return units, excluded


def declared_relations(
    units: Iterable[UnitFile],
) -> dict[tuple[str, str], frozenset[str]]:
    """The declared dependency graph, ``(scope, unit) -> related units``.

    Built for ``GET /api/logs/actions``, which uses it to decide that two
    units failing in the same breath are one incident rather than two
    (``SNAG-LOG-001``).  It reads nothing this module does not already
    open: :func:`discover_units` parses these files for ``ExecStart`` and
    ``Restart=`` on every sweep, so the graph costs one more pass over
    text already in memory and :func:`scan_units`'s no-subprocess promise
    is untouched.

    Four rules, three of them the opposite of the obvious implementation
    and all four settled against this box rather than by argument:

    1. **Both ends need not be readable, so reading only the sweep's own
       directories is enough.**  A relation is declared by the unit that
       *depends*, and on this estate that unit is always the
       hand-written one: ``estate-broker-provision.service`` in
       ``/etc/systemd/system`` carries ``After=mosquitto.service``, while
       ``mosquitto.service`` itself is a packaged file in
       ``/usr/lib/systemd/system`` that :func:`discover_units` excludes
       as distro-owned.  Measured 2026-08-18: parsing ``/usr/lib``
       as well reads **629 further unit files and yields zero further
       relations** between the fourteen declared log sources.  The
       obvious implementation widens the walk, pays 16x the file reads
       and learns nothing.

    2. **The map is symmetric, because only one side ever declares.**
       Nothing in ``mosquitto.service`` mentions the provisioner, so a
       lookup keyed on the *declaring* unit alone answers "what is
       mosquitto related to" with nothing — which is the direction an
       incident is actually read in, since the dependency is what fails
       first.  Each pair is therefore recorded from both ends.

    3. **The relation takes the scope of the unit that declares it, and
       never crosses.**  systemd does not order across managers — a user
       unit naming a system unit in ``After=`` is inert, which
       ``alfred-backend.service``'s own comment on this box records
       ("alfred-backend is a *user* unit and systemd never orders across
       managers").  So a declaration in a user unit can only mean the
       user-scope unit of that name, and the key carries the scope
       rather than resolving it: ``deadlock-api-ingest.service`` is
       installed in **both** scopes here running two different binaries,
       and a name-only key would silently merge them.

    4. **A unit is never related to itself.**  ``PartOf=`` a target and
       an ``OnFailure=`` pointing back at the same unit are both legal
       and would make every signature in one unit correlate through a
       self-edge — true, useless, and it would hide that same-source
       grouping is a separate rule with a separate justification.

    Its one honest limit is **drop-ins**: ``/etc/systemd/system/foo.service.d/``
    can add relations and :func:`discover_units` does not read those
    directories.  Measured on this box, both existing drop-in
    directories declare only ``Restart``/``StartLimit`` keys and **no
    relation at all**, so the population is empty today — but the gap is
    real and shared with ``restart_bounded``, and is filed as
    ``SNAG-UNITS-006`` rather than left implied.
    """
    by_scope: dict[tuple[str, str], set[str]] = {}
    for unit in units:
        for relation in unit.relations:
            if relation.unit == unit.name:
                continue  # Rule 4.
            by_scope.setdefault((unit.scope, unit.name), set()).add(relation.unit)
            by_scope.setdefault((unit.scope, relation.unit), set()).add(unit.name)
    return {key: frozenset(value) for key, value in by_scope.items()}


# --------------------------------------------------------------------------
# Matching
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProjectRef:
    """A project as the matcher needs to see it."""

    name: str
    path: str
    status: str = "active"

    @property
    def is_live(self) -> bool:
        """Whether a unit pointing here is worth wiring up.

        ``dormant`` counts as live: it is resting on purpose and may be
        woken.  ``archived`` does not — a unit for a retired project is
        an orphan even when the directory still exists under
        ``archive/``, because retirement is the point.
        """
        return self.status != "archived"


def normalise(text: str) -> str:
    """Fold a unit or project name for prefix comparison.

    Drops ``-``, ``_``, ``.`` and case, so ``SportsAnalyser``,
    ``sports_analyser`` and ``sportsanalyser`` are one string.  The
    naming on this box is inconsistent in exactly that way, which is why
    the path test runs first and this only catches what path matching
    cannot.
    """
    return re.sub(r"[-_.\s]", "", text).casefold()


def _under(path: str, root: str) -> bool:
    """Whether ``path`` is ``root`` or lies beneath it.

    String comparison on normalised absolute paths rather than
    ``Path.is_relative_to`` on resolved ones: the paths being tested
    frequently do not exist (that is the orphan case), and ``resolve()``
    on a missing path cannot follow the symlinks that would make the
    comparison meaningful anyway.
    """
    a = path.rstrip("/")
    b = root.rstrip("/")
    return a == b or a.startswith(b + "/")


@dataclass(frozen=True)
class UnitMatch:
    """The outcome of matching one unit against the project list."""

    project: ProjectRef | None = None
    matched_by: str | None = None  # "path" | "name"
    dead_paths: tuple[str, ...] = ()

    @property
    def matched(self) -> bool:
        return self.project is not None


def match_unit(
    unit: UnitFile,
    projects: Sequence[ProjectRef],
    path_exists: Any = None,
) -> UnitMatch:
    """Match one unit to a project, path first then name.

    Path first because the naming on this box breaks heuristics: the
    units are ``sportsanalyser-*`` while the directory is
    ``SportsAnalyser``, and ``sportsanalyser-pipeline.service`` runs
    ``/usr/bin/curl`` against an HTTP endpoint, so it has no project path
    at all and *only* the name test can catch it.  Neither test alone
    covers the estate.

    Name matching is a **prefix** test on the normalised strings, with
    the longest matching project winning.  That resolves the one real
    ambiguity here: ``alfred-inference`` prefix-matches the ``alfred``
    project but not ``alfred-glance`` (``alfredinference`` does not start
    with ``alfredglance``), so the longer-wins rule never has to guess.

    ``path_exists`` is injected so tests can describe an estate without
    creating it; it defaults to :meth:`Path.exists`.
    """
    exists = path_exists if path_exists is not None else (lambda p: Path(p).exists())

    # --- Path match: longest project root wins, so a project nested
    # under a category directory beats the category itself.
    best: ProjectRef | None = None
    for candidate in projects:
        for declared in unit.declared_paths:
            if _under(declared, candidate.path):
                if best is None or len(candidate.path) > len(best.path):
                    best = candidate
                break
    if best is not None:
        return UnitMatch(project=best, matched_by="path")

    # --- Dead paths.  Only ``WorkingDirectory`` is a hard claim; an
    # ExecStart binary under /usr may be missing for a dozen reasons that
    # are not "the project moved".  A dead WorkingDirectory, though, makes
    # systemd fail the start job — this unit cannot ever have run since.
    dead = tuple(
        p for p in ([unit.working_directory] if unit.working_directory else []) if not exists(p)
    )

    # --- Name prefix match, longest project first.
    unit_key = normalise(unit.stem)
    name_best: ProjectRef | None = None
    for candidate in projects:
        key = normalise(candidate.name) or normalise(Path(candidate.path).name)
        if key and unit_key.startswith(key):
            if name_best is None or len(key) > len(normalise(name_best.name)):
                name_best = candidate
    if name_best is not None:
        return UnitMatch(project=name_best, matched_by="name", dead_paths=dead)

    return UnitMatch(dead_paths=dead)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------


@dataclass
class UnitFinding:
    """One unit, classified, with everything a recommendation needs."""

    unit: str
    scope: str
    category: str
    path: str
    description: str | None = None
    project: str | None = None
    project_path: str | None = None
    matched_by: str | None = None
    #: The unit you would actually put in the config.  Differs from
    #: ``unit`` for a ``Type=oneshot`` service with a timer: the service
    #: is inactive/dead between runs by design, so monitoring it would
    #: alert continuously.  This is the rule config.yaml already records
    #: by hand for ``alfred-evaluate``.
    monitor_unit: str = ""
    dead_path: str | None = None
    #: A oneshot service with no timer and no [Install] — started by
    #: hand, so "not monitored" is not a defect.
    manual: bool = False
    reason: str = ""
    #: systemd will start this without anyone asking — an enablement
    #: symlink exists for the unit, or for the timer named in
    #: ``monitor_unit``.  The timer counts because a folded oneshot is
    #: started *by* its timer: disabling the service and leaving the
    #: timer enabled changes nothing.
    enabled: bool = False
    #: ``Restart=`` verbatim, and whether a loop here would ever reach
    #: ``failed`` (:func:`restart_is_bounded`).  Recorded on every
    #: finding, not only the ones that alert, because the question
    #: "which units on this box can loop for ever" has no other home
    #: and was answerable nowhere before this.
    restart: str | None = None
    restart_bounded: bool = True
    #: The three numbers ``restart_bounded`` was computed from, ``None``
    #: where the unit declares nothing and systemd's own default applies.
    #: Carried so the verdict is **checkable**: a boolean on its own asks
    #: the reader to trust arithmetic they cannot see, and the whole
    #: family exists because the obvious rule ("no ``StartLimitBurst=``")
    #: is wrong in both directions.  They are also the inputs
    #: :func:`~sysadmin.units.recommendations.suggested_start_limit_interval`
    #: needs to name a value that actually fixes *this* unit.
    restart_sec: float | None = None
    start_limit_interval: float | None = None
    start_limit_burst: int | None = None

    @property
    def armed(self) -> bool:
        """An orphan systemd will start: broken *and* scheduled to run.

        The distinction this whole family turns on.  A disabled orphan
        is filing debt — it cannot start itself, and the roll-up alert
        is the right home for it.  An enabled one is a fault in
        progress: every trigger fails, and because nothing monitors it,
        silently.  SNAG-ESTATE-001 ran for eight days as the second kind
        reported as the first.
        """
        return self.category == ORPHANED and self.enabled

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit": self.unit,
            "scope": self.scope,
            "category": self.category,
            "path": self.path,
            "description": self.description,
            "project": self.project,
            "project_path": self.project_path,
            "matched_by": self.matched_by,
            "monitor_unit": self.monitor_unit,
            "dead_path": self.dead_path,
            "manual": self.manual,
            "reason": self.reason,
            "enabled": self.enabled,
            "restart": self.restart,
            "restart_bounded": self.restart_bounded,
            "restart_sec": self.restart_sec,
            "start_limit_interval": self.start_limit_interval,
            "start_limit_burst": self.start_limit_burst,
            "armed": self.armed,
        }


def _wired_key(unit: str, scope: str) -> str:
    return f"{scope}:{unit}"


def wired_units(services: Iterable[Any] = ()) -> set[str]:
    """The set of units already registered, as ``"<scope>:<unit>"`` keys.

    One source now. This used to read projects.yaml as well, because half
    the estate's units were declared there and half in config.yaml, and a
    sweep that consulted only one would have reported the other half as
    unmonitored.

    Scope is part of the key on purpose.  ``deadlock-api-ingest.service``
    is installed in *both* scopes on this box, running two different
    binaries; wiring the user one says nothing about the system one, and
    a scope-blind key would report the pair as covered.
    """
    wired: set[str] = set()
    for service in services or ():
        unit = getattr(service, "systemd_unit", None)
        if unit:
            scope = "user" if getattr(service, "user", False) else "system"
            wired.add(_wired_key(unit, scope))
    return wired


def fold_timers(units: Sequence[UnitFile]) -> tuple[set[str], dict[str, str]]:
    """Pair each ``Type=oneshot`` service with the timer that starts it.

    Returns ``(folded_timer_keys, service_key -> timer_name)``.

    A oneshot service is ``inactive (dead)`` between runs *by design*, so
    monitoring the service alerts continuously — config.yaml already
    records this rule by hand for ``alfred-evaluate``.  The timer is the
    thing to watch, but the *service* is what carries
    ``WorkingDirectory`` and ``ExecStart``, so the finding is reported
    under the service with the timer named as ``monitor_unit``, and the
    timer suppressed.  One schedule, one finding — the de-duplication
    SNAG-AGENT-002 records the log aggregator failing to do.

    Split out of :func:`classify_units` so :func:`scan_units` can use the
    same pairing for its arithmetic instead of re-deriving it.  The first
    version inferred "monitored" as "produced no finding", which quietly
    counted these suppressed timers as monitored and reported 20 where
    the truth was 12.
    """
    by_key = {_wired_key(u.name, u.scope): u for u in units}
    folded: set[str] = set()
    timer_for: dict[str, str] = {}

    for unit in units:
        if not unit.is_timer or not unit.triggers:
            continue
        target = by_key.get(_wired_key(unit.triggers, unit.scope))
        if target is not None and target.is_oneshot:
            folded.add(_wired_key(unit.name, unit.scope))
            timer_for[_wired_key(target.name, target.scope)] = unit.name

    return folded, timer_for


def is_wired(
    unit: UnitFile, wired: set[str], timer_for: Mapping[str, str]
) -> bool:
    """Whether either end of a service/timer pair is already registered.

    Either end counts: ``services.yaml`` records ``alfred-evaluate``
    under its *timer* while recording other services under the service
    unit itself, and a unit registered under one name is not unmonitored
    because the other name is absent.
    """
    key = _wired_key(unit.name, unit.scope)
    if key in wired:
        return True
    monitor_unit = timer_for.get(key)
    if monitor_unit is None:
        return False
    return _wired_key(monitor_unit, unit.scope) in wired


def classify_units(
    units: Sequence[UnitFile],
    projects: Sequence[ProjectRef],
    wired: set[str],
    path_exists: Any = None,
) -> list[UnitFinding]:
    """Classify every discovered unit.  Returns findings worth acting on.

    ``monitored`` units are dropped from the result — they are counted by
    the caller, not listed, because a list of things that are fine is
    noise the reader has to filter every time.
    """
    folded, timer_for = fold_timers(units)
    by_key = {_wired_key(u.name, u.scope): u for u in units}
    findings: list[UnitFinding] = []

    for unit in units:
        key = _wired_key(unit.name, unit.scope)
        if key in folded:
            continue
        if is_wired(unit, wired, timer_for):
            continue

        monitor_unit = timer_for.get(key, unit.name)
        match = match_unit(unit, projects, path_exists=path_exists)
        # A folded oneshot is started by its timer, so the timer's
        # enablement is the one that decides whether anything runs.
        # Reading only the service would report the PersonalAssistant
        # shape as dormant whenever the schedule lived in the timer.
        timer_unit = by_key.get(_wired_key(monitor_unit, unit.scope))
        finding = UnitFinding(
            unit=unit.name,
            scope=unit.scope,
            category=HOST,
            path=unit.path,
            description=unit.description,
            monitor_unit=monitor_unit,
            matched_by=match.matched_by,
            dead_path=match.dead_paths[0] if match.dead_paths else None,
            manual=unit.is_oneshot and monitor_unit == unit.name and unit.static,
            enabled=unit.enabled or bool(timer_unit and timer_unit.enabled),
            restart=unit.restart,
            restart_bounded=unit.restart_bounded,
            restart_sec=unit.restart_sec,
            start_limit_interval=unit.start_limit_interval,
            start_limit_burst=unit.start_limit_burst,
        )
        if match.project is not None:
            finding.project = match.project.name
            finding.project_path = match.project.path

        _assign_category(finding, unit, match)
        findings.append(finding)

    findings.sort(key=lambda f: (CATEGORY_ORDER.index(f.category), f.scope, f.unit))
    return findings


def _assign_category(finding: UnitFinding, unit: UnitFile, match: UnitMatch) -> None:
    """Decide the category and write the human-readable reason.

    Order matters.  A dead ``WorkingDirectory`` beats every other signal:
    it does not matter which project the name resembles if the directory
    systemd would ``chdir`` into is gone — the unit is already broken.
    """
    if finding.dead_path:
        finding.category = ORPHANED
        finding.reason = (
            f"WorkingDirectory {finding.dead_path} does not exist — "
            "systemd fails the start job, so this unit cannot run"
        ) + _arming_clause(finding)
        return

    if match.project is not None and not match.project.is_live:
        finding.category = ORPHANED
        finding.reason = (
            f"belongs to {match.project.name}, which is archived — "
            "the project was retired but its unit was left installed"
        ) + _arming_clause(finding)
        return

    if match.project is not None:
        finding.category = UNMONITORED
        via = (
            f"its path is under {match.project.path}"
            if match.matched_by == "path"
            else f"its name matches the {match.project.name} project"
        )
        finding.reason = (
            f"{via}, but no services.yaml entry monitors it"
        )
        return

    finding.category = HOST
    finding.reason = (
        "hand-written unit that maps to no project — real infrastructure "
        "with nothing watching it"
    )


def _arming_clause(finding: UnitFinding) -> str:
    """The half of an orphan's reason that says whether it is running.

    Written into ``reason`` rather than left for the alert to assemble,
    because ``reason`` is what the drill-down and the recommendation
    detail both render.  SNAG-ESTATE-001's diagnosis was already
    "complete, correct, machine-readable and eight days old" — what it
    never said is that two of those seventeen findings were *live*.
    """
    if not finding.enabled:
        return ". It is disabled, so nothing starts it"
    if finding.restart_bounded:
        return (
            ". It is enabled, so systemd starts it and the start fails "
            "every time"
        )
    return (
        f". It is enabled and sets Restart={finding.restart} with a start "
        "limit it can never reach, so the failed starts repeat for ever "
        "without the unit entering `failed` — nothing can fire OnFailure= "
        "and `systemctl is-failed` says it is fine"
    )


def restart_risk_findings(
    units: Sequence[UnitFile],
    findings: Sequence[UnitFinding],
    projects: Sequence[ProjectRef],
    path_exists: Any = None,
) -> list[UnitFinding]:
    """Units whose restart loop can never reach ``failed`` (SNAG-UNITS-002).

    A **second pass over the same units**, not a fifth category, and it
    is a second pass for a reason worth stating: 11 of the 13 units this
    returns on the live box are ``monitored``, and
    :func:`classify_units` drops those before they exist as findings.
    The question "which units on this box can loop for ever" was
    therefore answerable for the six units the sweep already described
    and invisible for every live service on it — which is the whole of
    the snag.

    Three rules, two of them the opposite of the obvious version:

    1. **Orphans are excluded, not included.**  The obvious reading is
       that a broken unit which also loops is the worst case and belongs
       here twice over.  It cannot be: an orphan's recommendation is
       *remove it*, and advising someone to add a start limit to a file
       they should delete is two contradictory instructions for one
       unit.  The fact is not lost — an orphan that loops is exactly
       what :func:`sysadmin.units.agent.armed_alert_severity` promotes
       to ``critical``, so it is already being said, louder, by the
       family that owns it.
    2. **A unit with no ``Restart=`` is never here**, because
       :func:`restart_is_bounded` returns ``True`` for it.  "Does not
       restart" and "restarts safely" are the same answer to the only
       question being asked, and separating them would report every
       oneshot on the box as a finding.
    3. **Not knowing is not an accusation**, inherited from
       :func:`restart_is_bounded`: an unparseable ``RestartSec=`` reads
       as bounded, so a false *negative* is possible and a false
       positive is not.  A reader sent to rewrite a unit that is fine
       stops trusting the family.

    Findings the sweep already produced are reused via ``replace`` rather
    than rebuilt, so a unit's project, description and arming state
    cannot disagree between the two lists.
    """
    classified = {_wired_key(f.unit, f.scope): f for f in findings}
    folded, timer_for = fold_timers(units)
    by_key = {_wired_key(u.name, u.scope): u for u in units}

    risky: list[UnitFinding] = []
    for unit in units:
        if unit.restart_bounded:
            continue
        key = _wired_key(unit.name, unit.scope)

        existing = classified.get(key)
        if existing is not None and existing.category == ORPHANED:
            continue
        if existing is not None:
            risky.append(
                replace(
                    existing,
                    category=RESTART_UNBOUNDED,
                    reason=_restart_reason(existing),
                )
            )
            continue

        # Monitored (or a folded timer): no finding exists, so build one.
        monitor_unit = timer_for.get(key, unit.name)
        match = match_unit(unit, projects, path_exists=path_exists)
        timer_unit = by_key.get(_wired_key(monitor_unit, unit.scope))
        finding = UnitFinding(
            unit=unit.name,
            scope=unit.scope,
            category=RESTART_UNBOUNDED,
            path=unit.path,
            description=unit.description,
            monitor_unit=monitor_unit,
            matched_by=match.matched_by,
            dead_path=match.dead_paths[0] if match.dead_paths else None,
            manual=unit.is_oneshot and monitor_unit == unit.name and unit.static,
            enabled=unit.enabled or bool(timer_unit and timer_unit.enabled),
            restart=unit.restart,
            restart_bounded=unit.restart_bounded,
            restart_sec=unit.restart_sec,
            start_limit_interval=unit.start_limit_interval,
            start_limit_burst=unit.start_limit_burst,
        )
        if match.project is not None:
            finding.project = match.project.name
            finding.project_path = match.project.path
        finding.reason = _restart_reason(finding)
        risky.append(finding)

    risky.sort(key=lambda f: (f.scope, f.unit))
    return risky


def _restart_reason(finding: UnitFinding) -> str:
    """Why this unit is in the restart family, in the reader's terms.

    States the *consequence* rather than the arithmetic.  The numbers
    that produced the verdict are on the finding already
    (``restart``, and the unit file itself), and a reason reading
    "RestartSec × (burst − 1) ≥ StartLimitIntervalSec" tells someone who
    has not read :func:`restart_is_bounded` nothing they can act on.
    """
    return (
        f"sets Restart={finding.restart} with a start limit its restart "
        "cadence can never reach, so failed starts repeat for ever without "
        "the unit entering `failed` — no OnFailure= can fire and "
        "`systemctl is-failed` reports it as fine"
    )


@dataclass
class UnitScan:
    """The whole sweep: what was looked at, and what came back."""

    findings: list[UnitFinding] = field(default_factory=list)
    #: Hand-written units read off disk.  ``units_scanned`` is the sum of
    #: ``monitored_count``, ``timers_folded`` and ``len(findings)`` — the
    #: three buckets are exhaustive on purpose, so the arithmetic is
    #: checkable rather than merely plausible.
    units_scanned: int = 0
    units_excluded: int = 0
    monitored_count: int = 0
    timers_folded: int = 0
    excluded_units: list[str] = field(default_factory=list)
    #: Units whose restart loop can never reach ``failed``
    #: (:func:`restart_risk_findings`).  A **parallel list**, not part of
    #: ``findings``: its members are mostly ``monitored`` units, which
    #: ``findings`` deliberately never holds, and adding them there would
    #: break both ``units_scanned``'s arithmetic and ``actionable``'s
    #: meaning — the latter drives the roll-up alert's threshold, so 13
    #: latent risks would read as 13 new gaps to wire up.
    restart_findings: list[UnitFinding] = field(default_factory=list)
    #: ``"<scope>:<unit>"`` → the name of the project the unit belongs to,
    #: for **every** unit the sweep looked at rather than only the ones
    #: that became findings.  Session 26c's port check needs to ask "who
    #: owns the unit holding port 8100", and 8100's unit is ``monitored``
    #: — the one bucket ``findings`` deliberately never lists.  Built
    #: here rather than in :mod:`sysadmin.units.ports` so there is one
    #: definition of what matching a unit to a project means; a second
    #: one would drift in the direction where a port is attributed to the
    #: wrong repository and nothing reports the disagreement.
    unit_projects: dict[str, str] = field(default_factory=dict)

    def count(self, category: str) -> int:
        return sum(1 for f in self.findings if f.category == category)

    @property
    def armed(self) -> list[UnitFinding]:
        """Orphans systemd will start — the findings that get their own alert.

        A list rather than a count because every caller wants the units:
        the alert names them one at a time, which is the entire point of
        the family.
        """
        return [f for f in self.findings if f.armed]

    @property
    def actionable(self) -> int:
        """Findings that are defects or gaps — everything reported."""
        return len(self.findings)

    def as_findings_blob(self, limit: int = 200) -> dict[str, Any]:
        """The JSONB payload stored on the audit row.

        Grouped by category rather than stored flat: every consumer wants
        one category at a time, and a flat list makes the reader filter
        before they can count.  ``limit`` caps each list — Session 24's
        hard lesson was that a truncated list must never be the source of
        a count, so the counts live in their own columns and
        :meth:`count` reads the untruncated in-memory list.
        """
        blob: dict[str, Any] = {
            "units_scanned": self.units_scanned,
            "units_excluded": self.units_excluded,
            "monitored_count": self.monitored_count,
            "timers_folded": self.timers_folded,
            "excluded_units": self.excluded_units[:limit],
            # A scalar, deliberately, and stored beside the counts rather
            # than derived from the truncated ``orphaned`` list below.
            # ``unit_audits`` has a column per category and this one has
            # none; putting the number in the blob keeps Session 24's
            # rule (a truncated list is never the source of a count)
            # without a migration for a figure that is a subset of a
            # column already stored.
            "armed_count": len(self.armed),
            # Same rule as ``armed_count``: the scalar is the count, the
            # list below is capped.  Unlike ``armed`` this one has no
            # column on ``unit_audits`` at all, so the blob is the only
            # home — and a count taken from the truncated list would be a
            # lower bound that reads like a total.
            "restart_unbounded_count": len(self.restart_findings),
            RESTART_UNBOUNDED: [f.as_dict() for f in self.restart_findings][:limit],
        }
        for category in CATEGORY_ORDER:
            blob[category] = [
                f.as_dict() for f in self.findings if f.category == category
            ][:limit]
        return blob


def scan_units(
    user_dir: Path | str | None,
    system_dir: Path | str | None,
    home: str,
    projects: Sequence[ProjectRef],
    wired: set[str],
    path_exists: Any = None,
) -> UnitScan:
    """Run the whole sweep.  The one entry point the agent calls."""
    units, excluded = discover_units(user_dir, system_dir, home)
    findings = classify_units(units, projects, wired, path_exists=path_exists)
    restart_risks = restart_risk_findings(
        units, findings, projects, path_exists=path_exists
    )

    folded, timer_for = fold_timers(units)
    monitored = sum(
        1
        for u in units
        if _wired_key(u.name, u.scope) not in folded and is_wired(u, wired, timer_for)
    )

    unit_projects: dict[str, str] = {}
    for unit in units:
        match = match_unit(unit, projects, path_exists=path_exists)
        if match.project is not None:
            unit_projects[_wired_key(unit.name, unit.scope)] = match.project.name

    return UnitScan(
        findings=findings,
        restart_findings=restart_risks,
        units_scanned=len(units),
        units_excluded=len(excluded),
        monitored_count=monitored,
        timers_folded=len(folded),
        excluded_units=excluded,
        unit_projects=unit_projects,
    )


def project_refs(
    snapshots: Iterable[Mapping[str, Any]] | Iterable[Any],
) -> list[ProjectRef]:
    """Build match targets from project snapshots (rows or dicts).

    Accepts either so the agent can pass ORM rows and the tests can pass
    plain dicts without a fixture.
    """
    refs: list[ProjectRef] = []
    for item in snapshots:
        if isinstance(item, Mapping):
            name = item.get("project_name") or item.get("name")
            path = item.get("project_path") or item.get("path")
            findings = item.get("findings") or {}
            status = item.get("status") or findings.get("status") or "active"
        else:
            name = getattr(item, "project_name", None) or getattr(item, "name", None)
            path = getattr(item, "project_path", None) or getattr(item, "path", None)
            findings = getattr(item, "findings", None) or {}
            status = findings.get("status", "active") if isinstance(findings, dict) else "active"
        if not name or not path:
            continue
        refs.append(ProjectRef(name=str(name), path=str(path), status=str(status)))
    return refs
