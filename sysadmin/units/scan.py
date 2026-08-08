"""Systemd unit discovery — read the installed units, match them to projects.

Tier 1 of Session 26.  The problem this solves is bookkeeping rot: every
new service under ``~/projects`` has to be hand-registered in
``projects.yaml`` or ``config.yaml``, nobody remembers, and a unit that
was never wired looks identical to one that is working fine.  Worse in
the other direction — a retired project leaves its units installed, and
they either fail on every start or silently do nothing.

The module is **pure**: no DB, no FastAPI, no subprocesses.  Give it two
directories and a list of projects, get a list of findings.  That is not
architectural tidiness for its own sake — it is what lets the tests build
a fake estate under ``tmp_path`` and assert on real parsing rather than
on mocks, which is the lesson Sessions 23 and 24 both paid for.

Four categories, and the boundary between them is the whole point:

``monitored``
    The unit (or, for a ``Type=oneshot`` service, its timer) already
    appears as a ``systemd_unit`` in projects.yaml or config.yaml.
    Nothing to do.

``unmonitored``
    The unit maps to a project that still exists, and nothing wires it.
    This is the case the session was asked for.  Advice: a projects.yaml
    snippet.

``orphaned``
    The unit's own declared path is gone — the project was archived,
    moved or deleted and the unit stayed behind.  A unit like this is
    not merely unwatched, it is broken: ``WorkingDirectory`` pointing at
    a missing directory makes systemd fail the start job outright.
    Advice: remove it.

``host``
    Hand-written, maps to no project — ``pgbackrest-backup``,
    ``ethernet-optimise``.  These are real infrastructure and a silent
    stop matters (a backup that stopped a month ago looks exactly like
    one that ran), but they have no project directory, so a projects.yaml
    snippet would be a lie.  Advice: a config.yaml ``services:`` entry.

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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Categories.  Strings rather than an enum because they cross a JSONB
# column and an HTTP boundary, and both ends already speak strings.
MONITORED = "monitored"
UNMONITORED = "unmonitored"
ORPHANED = "orphaned"
HOST = "host"

#: Order findings are reported in — broken first, then unwired, then the
#: merely-undocumented.  ``monitored`` is not reported at all, only counted.
CATEGORY_ORDER = (ORPHANED, UNMONITORED, HOST)

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

    name = path.name
    triggers = None
    if name.endswith(".timer"):
        triggers = first("Timer", "Unit") or f"{name.rsplit('.', 1)[0]}.service"

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
    )


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
            units.append(load_unit(entry, scope, scope_home))

    return units, excluded


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

    Either end counts: config.yaml records ``alfred-evaluate.timer``
    while projects.yaml records services, and a unit registered under
    one name is not un-monitored because the other name is absent.
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
    findings: list[UnitFinding] = []

    for unit in units:
        key = _wired_key(unit.name, unit.scope)
        if key in folded:
            continue
        if is_wired(unit, wired, timer_for):
            continue

        monitor_unit = timer_for.get(key, unit.name)
        match = match_unit(unit, projects, path_exists=path_exists)
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
        )
        return

    if match.project is not None and not match.project.is_live:
        finding.category = ORPHANED
        finding.reason = (
            f"belongs to {match.project.name}, which is archived — "
            "the project was retired but its unit was left installed"
        )
        return

    if match.project is not None:
        finding.category = UNMONITORED
        via = (
            f"its path is under {match.project.path}"
            if match.matched_by == "path"
            else f"its name matches the {match.project.name} project"
        )
        finding.reason = (
            f"{via}, but no projects.yaml or config.yaml entry monitors it"
        )
        return

    finding.category = HOST
    finding.reason = (
        "hand-written unit that maps to no project — real infrastructure "
        "with nothing watching it"
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

    def count(self, category: str) -> int:
        return sum(1 for f in self.findings if f.category == category)

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

    folded, timer_for = fold_timers(units)
    monitored = sum(
        1
        for u in units
        if _wired_key(u.name, u.scope) not in folded and is_wired(u, wired, timer_for)
    )

    return UnitScan(
        findings=findings,
        units_scanned=len(units),
        units_excluded=len(excluded),
        monitored_count=monitored,
        timers_folded=len(folded),
        excluded_units=excluded,
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
