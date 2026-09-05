"""``SNAG-TEST-006`` — the asserts a green suite never evaluated.

A test looping over a live artefact's members is green while that
population is empty, because an empty ``for`` completes.  Review does not
catch it — the code reads correctly — and the suite cannot report it,
because passing is exactly what it does.  The founding instance,
``TestTheConventionAgainstTheRealDocument``'s prediction guard, shipped
2026-08-24 and ran its body for the first time on 2026-09-04.

The measure is coverage over a green full suite joined to an AST walk of
``tests/``: an ``assert`` whose line never executed is a guard that
asserted nothing.  Five rules, three of them the opposite of the obvious
implementation.

**It reads a coverage report; it never imports coverage.**  ``coverage``
is not a dependency here and stays out of ``.venv`` —
:file:`scripts/check-vacuous-guards.sh` runs the suite under an ephemeral
``uv run --with`` overlay, which the entry's shape-of-fix verified leaves
the lock and the 122 installed packages untouched.  So the join is done
over the JSON report with :mod:`json` and :mod:`ast` alone, which is also
what lets this module's own tests run on a box where coverage is not
installed.

**A red suite cannot answer the question**, so the shell owns that gate
and this module never sees a failing run.  An ``assert`` not reached
because an earlier one blew up is not a guard that asserted nothing, and
scoring it as one would make the gate loudest exactly when the suite is
already telling the operator something truer.

**Zero findings from a report that measured nothing is not zero
findings.**  A test file on disk carrying an ``assert`` and absent from
the report was never imported — a broken ``--source``, a file added since
the run — so the sweep answers ``unknown`` and names them.
``ports_checked``'s rule: zero-because-blind must never be served as
zero-because-clean.

**A guard that cannot evaluate on a healthy run is declared, never
deleted and never silently skipped.**  Three of this repository's six
live findings are branches on intermittent live state (an idle estate, a
wiring check with no whole-file finding) and two are deadline guards
inside polling helpers that a fast box satisfies before the loop turns
once.  None is a defect and none can be restructured into evaluating, so
each carries a :data:`DECLARATION` comment with a reason —
``known_noise``'s rule 2 exactly: quietened, never suppressed.  The
declared set is **named on every run** whatever the verdict, because a
declaration nothing reports is a decision taken with nothing recording
that it was taken, which is ``SNAG-CFG-001``'s shape.  A declaration
carrying no reason is not a declaration and the assert stays a finding —
``known_noise``'s ``reason`` is a required field for the same reason, and
the refusal is reported rather than swallowed.

**A guard that ran over nothing is the second half, and it is read from
arcs rather than from lines.**  Line coverage is structurally blind to
``assert all(f(x) for x in live)``: the comprehension is ``True`` over an
empty ``live`` and the assert line *executes*.  Three sittings recorded
that as a permanent property of the measure, and it is a property of
*line* coverage alone — CPython compiles a comprehension to a real loop,
and ``coverage run --branch`` records its back-edge as an arc whatever
coverage's static analysis believes about branch points.  So there is no
second pass and no ``sys.monitoring``: one flag on the run the gate
already makes, measured at 90.2 s against 88.3 s (``SNAG-TEST-009``).

**``coverage json`` erases exactly that, so the arcs are read from the
SQLite data file with :mod:`sqlite3`.**  Coverage does not model a
comprehension as a branch point, so a file whose only loops are
comprehensions reports ``num_branches: 0`` with an empty
``executed_branches``, and the report lists only *statement* lines, so a
comprehension's element expression never appears in it either — line
coverage answers **none** of them rather than some.  Reading
:file:`.coverage` directly keeps the rule above intact: still no
``import coverage``, still testable on a box that has never installed it.

**The two halves take different markers, because they are different
claims.**  :data:`DECLARATION` says an assert may not *run*;
:data:`LOOP_DECLARATION` says a comprehension may legitimately turn
*zero times*.  One marker for both would report every loop declaration as
stale the moment its assert evaluated — which is always, since a loop
cannot turn without its statement running — and ``noise_reason`` against
``covered_by`` is this repository's rule for the shape: an operator's
judgement and a structural fact are different claims, and one field
holding both is ``UnitFinding.enabled``'s trap.

**An undecidable site is named and never guessed at, and it does not move
the verdict.**  Two written shapes leave arcs that a turning loop and an
empty one produce identically — see :func:`_loop_turned` — so they are
reported as their own population rather than resolved by a guess in
either direction: ``ports_checked``'s rule at the size of a comprehension.
They stay out of the exit status because the remedy is reformatting a
test rather than fixing a guard, and a gate that is permanently yellow is
``SNAG-LOG-002``'s binary ``LOW`` confidence, read by nobody for fourteen
days.  0/1/2 keeps ``check-migrations.sh``'s meaning throughout, each a
property of *this* run a sitting can act on.
"""

from __future__ import annotations

import argparse
import ast
import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS, SchemaVerdict

#: The same three words and the same exit map as the schema check, the ops
#: claims and the snag claims, imported rather than restated.
type Verdict = SchemaVerdict

TESTS_ROOT = REPO_ROOT / "tests"

#: How a test declares that one of its asserts may legitimately not
#: evaluate.  The reason is required and is carried in the report, so the
#: declaration is a claim a later reader can check rather than a way to go
#: quiet — ``known_noise``'s ``reason`` field, spelled for a source file.
DECLARATION = "may-not-evaluate:"

#: How a test declares that one of its comprehensions may legitimately
#: turn zero times — an empty population that is the asserted-healthy
#: state.  Deliberately **not** :data:`DECLARATION`: see the module
#: docstring, and note that the two are also read at different anchors,
#: the assert for one and the comprehension's enclosing statement for the
#: other, because a comprehension is judged wherever it is written.
LOOP_DECLARATION = "may-not-turn:"

#: The comprehension node types whose truth over an empty iterable is
#: ``True`` (or, for the dict and set forms, whose emptiness is
#: indistinguishable from a satisfied population at the assert line).
_COMPREHENSIONS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


@dataclass(frozen=True)
class Guard:
    """One ``assert`` under ``tests/``, and what the run did with it.

    Attributes:
        path: repository-relative path, so a report line is clickable.
        line: the ``assert`` keyword's line.  This is the join: coverage
            attributes a multi-line statement to its first line and
            :attr:`ast.Assert.lineno` is that same line — verified live
            against ``tests/test_arbitrated_stops_live.py``'s four-line
            assert, which the report misses as line 147 alone.
        source: the ``assert`` line as written, stripped, for the report.
        reason: what the file declares, or ``None`` where it declares
            nothing.  An empty reason is not a declaration.
        evaluated: whether the run executed the line.
    """

    path: str
    line: int
    source: str
    reason: str | None
    evaluated: bool

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class Loop:
    """One comprehension under ``tests/``, and what the run did with it.

    Attributes:
        path: repository-relative path, so a report line is clickable.
        line: the comprehension's own first line, which is where a reader
            has to look — deliberately not the enclosing statement's, so
            a site inside a multi-line assert names itself.
        statement: the first line of the statement the comprehension sits
            in.  The declaration anchor, and what
            :attr:`Sweep.loop_findings` reads to tell a loop that never
            turned from one whose statement never ran at all.
        source: the comprehension's first line as written, stripped.
        reason: what the file declares with :data:`LOOP_DECLARATION`, or
            ``None``.  An empty reason is not a declaration.
        turned: ``True`` where the loop ran its element expression at
            least once, ``False`` where it did not, ``None`` where the
            arcs cannot say — never a guess.
        undecidable: why, where :attr:`turned` is ``None``.
        reached: whether the enclosing statement executed at all.  A
            comprehension in a skipped test did not turn *and* has
            nothing to do with an empty population, so the two are not
            served as one answer.
    """

    path: str
    line: int
    statement: int
    source: str
    reason: str | None
    turned: bool | None
    undecidable: str | None
    reached: bool

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class Sweep:
    """What one coverage report says about ``tests/``.

    ``findings`` and ``loop_findings`` are the answer; everything else is
    the reading it was made under, which is why the undecidable set, the
    declared sets and the blind population are fields rather than a
    branch.
    """

    findings: tuple[Guard, ...] = ()
    declared: tuple[Guard, ...] = ()
    stale: tuple[Guard, ...] = ()
    unmeasured: tuple[str, ...] = ()
    unparsed: tuple[str, ...] = ()
    moved: tuple[str, ...] = ()
    asserts: int = 0
    comprehension: tuple[Guard, ...] = ()
    comprehension_files: int = 0
    measured_at: str = ""
    problem: str | None = None
    loops_measured: bool = False
    loops: int = 0
    loops_turned: int = 0
    loop_findings: tuple[Loop, ...] = ()
    loop_declared: tuple[Loop, ...] = ()
    loop_stale: tuple[Loop, ...] = ()
    loop_undecidable: tuple[Loop, ...] = ()

    @property
    def verdict(self) -> Verdict:
        """``unknown`` outranks ``mismatch``, which is the reverse of the
        usual ordering here and is forced by what the two mean.

        A sweep that could not read part of ``tests/`` has not found
        "no findings and one blind spot" — its finding count is a lower
        bound taken over an unknown fraction of the suite, so reporting
        it as a mismatch would put a number on a reading that has none.

        :attr:`loop_undecidable` is deliberately **not** in the first
        branch.  It is a property of how a handful of comprehensions are
        *written* rather than of this run, so a sitting cannot clear it
        and a status firing on it would never go out — the standing
        declaration carries it instead.
        """
        if self.problem is not None or self.unmeasured or self.unparsed or self.moved:
            return "unknown"
        if self.findings or self.loop_findings:
            return "mismatch"
        return "match"


def read_report(path: Path) -> tuple[dict[Path, set[int]], str] | None:
    """Executed lines per file from a ``coverage json`` report.

    Keyed on the resolved path, because coverage records whatever the
    run's working directory made relative and this module is reached
    from a shell script that ``cd``s to the repository root.
    """
    try:
        document = json.loads(path.read_text())
        files = document["files"]
        executed = {
            (Path(name) if Path(name).is_absolute() else REPO_ROOT / name).resolve(): set(
                entry["executed_lines"]
            )
            for name, entry in files.items()
        }
    except (OSError, ValueError, KeyError, TypeError):
        return None
    stamp = document.get("meta", {}).get("timestamp")
    # A non-string stamp is *absent*, never ``str(stamp)``.  ``str(None)``
    # is ``"None"``, which is truthy, so coercing sent a missing timestamp
    # down the unparseable road instead — two roads to one reading, with
    # a test covering whichever it happened to take.
    return executed, stamp if isinstance(stamp, str) else ""


def read_arcs(path: Path) -> dict[Path, set[tuple[int, int]]] | None:
    """Executed arcs per file from a ``coverage run --branch`` data file.

    ``None`` on every way of not being able to answer, and the important
    one is not an error: a data file written *without* ``--branch`` opens
    cleanly, has the ``arc`` table, and holds **no rows**.  Read as
    evidence that would be zero back-edges for the whole suite — every
    comprehension under ``tests/`` reported as having run over nothing,
    a gate that fabricates hundreds of findings out of a missing flag.
    So ``meta.has_arcs`` is the gate, and it is checked rather than
    inferred from the row count: ``ports_checked``'s rule, with the
    fail-closed direction chosen because the alternative here is not a
    quiet false negative but a loud false positive.

    Keyed on the resolved path for :func:`read_report`'s reason.  The
    query is the whole of the dependency on coverage's schema — no
    ``import coverage``, so this module and its tests still run on a box
    where coverage has never been installed.
    """
    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            if dict(db.execute("select key, value from meta")).get("has_arcs") != "1":
                return None
            rows = db.execute(
                "select f.path, a.fromno, a.tono from arc a join file f on f.id = a.file_id"
            ).fetchall()
    except (sqlite3.Error, OSError, TypeError, ValueError):
        return None
    arcs: dict[Path, set[tuple[int, int]]] = {}
    for name, start, end in rows:
        resolved = (Path(name) if Path(name).is_absolute() else REPO_ROOT / name).resolve()
        arcs.setdefault(resolved, set()).add((start, end))
    return arcs


def _relative(path: Path) -> str:
    """A path as a report line names it.

    Repository-relative where it can be, so a finding is clickable, and
    the absolute path otherwise.  ``--tests-root`` may name a tree
    outside this checkout — every one of this module's own tests does —
    and ``relative_to`` raises rather than declining, which would make
    the sweep die on the input it was given a flag to accept.
    """
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _report_taken_at(measured_at: str) -> float | None:
    """When the report was written, as a POSIX timestamp, or ``None``.

    ``None`` where the stamp is missing or will not parse, and that fails
    **open** — the reverse of this module's other not-knowing, and
    deliberately.  Every other blind spot here is about ``tests/``, where
    a silent skip would understate the finding count; this one is about
    the report's own metadata, and refusing every sweep because a future
    coverage release renamed a key would take the gate off the close path
    for a fact it can live without.
    """
    if not measured_at:
        return None
    try:
        return datetime.fromisoformat(measured_at).timestamp()
    except ValueError:
        return None


def _comment_block_above(node: ast.stmt | ast.expr, lines: list[str]) -> list[int]:
    """The contiguous run of comment lines directly above the ``assert``.

    **The whole run, not the line above**, and that was settled by the
    first live run rather than by argument: this module's own six
    declarations went in as comment blocks of one, two and three lines,
    the marker sitting at the *top* of each, and a one-line lookback read
    **one** of the six.  A rule that silently drops a declaration whose
    reason needed a second line is worse than no rule, because its author
    watched themselves write it.  Every synthetic fixture used a
    single-line comment, so nothing here could have caught it.
    """
    block: list[int] = []
    index = node.lineno - 2
    while index >= 0 and lines[index].strip().startswith("#"):
        block.append(index)
        index -= 1
    return list(reversed(block))


def _declared_reason(
    node: ast.stmt | ast.expr,
    lines: list[str],
    marker: str = DECLARATION,
    last: int | None = None,
) -> str | None:
    """What the file declares about this statement, or ``None``.

    Read from the comment block above ``node`` or from any line of it up
    to ``last``, which defaults to the node's own end.  The loop half
    passes ``last=node.lineno``, so a marker inside a *nested*
    comprehension cannot be read as a declaration about the one wrapping
    it.  Both spellings mean one thing, so both are
    accepted rather than one being made canonical and the other silently
    ignored — an unread declaration is worse than none, because its
    author believes it landed.

    The reason **continues onto the following comment lines** of the same
    block, so it is reported as written rather than truncated at the
    marker's own line.  A one-line reason is the common case and is
    unaffected; what this buys is that a declaration is never quietly
    read as half of itself.
    """
    block = _comment_block_above(node, lines)
    for position, index in enumerate(block):
        _, found, rest = lines[index].partition(marker)
        if not found:
            continue
        parts = [rest.strip()]
        for following in block[position + 1 :]:
            parts.append(lines[following].strip().lstrip("#").strip())
        return " ".join(part for part in parts if part) or None

    end = last if last is not None else (node.end_lineno or node.lineno)
    statement = range(node.lineno - 1, min(end, len(lines)))
    for index in statement:
        _, found, rest = lines[index].partition(marker)
        if found:
            return rest.strip() or None
    return None


def _element_line(node: ast.expr) -> int:
    """The first line of the expression a turn of the loop evaluates.

    The element, and for a dict comprehension the earlier of key and
    value.  It is the *element* rather than the ``for`` clause because a
    comprehension is written element-first, so the arc a turn leaves runs
    from the iteration back to this line — backwards in line numbers even
    though it is forwards in execution.
    """
    if isinstance(node, ast.DictComp):
        return min(node.key.lineno, node.value.lineno)
    assert isinstance(node, ast.ListComp | ast.SetComp | ast.GeneratorExp)
    return node.elt.lineno


def _loop_turned(
    node: ast.expr, arcs: set[tuple[int, int]], siblings: list[ast.expr]
) -> tuple[bool | None, str | None]:
    """Did this comprehension evaluate its element expression at all?

    Three rules, and the first two were the opposite of what the entry
    that ordered this fix wrote down — every wrong version of the
    detector returned a plausible number, so all three were settled
    against controlled fixtures driven at 0, 1 and 2 iterations rather
    than by reading bytecode.

    **1. The arc is the one that reaches the element line, not "any arc
    running backwards inside the span".**  ``SNAG-TEST-009`` records the
    wider rule and it reports a loop that turned zero times as having
    turned: a generator expression exhausting its iterator emits a
    *return* arc from the ``for`` line to the frame's own first line,
    which is inside the span and runs backwards.  Requiring the target to
    be the element line separates them — except when the element sits on
    that first line, where the two arcs are spelled identically and the
    answer is ``None``.  A multi-line statement carries the same shape
    for an inlined list comprehension, so the refusal is not specific to
    generators and is not conditioned on the node type.

    The one arc excluded is ``(first, element)``: entering the
    comprehension reaches the element line without any turn having
    happened.  It is excluded only where the element sits *below* the
    first line, because where they coincide no such arc exists — a
    forward jump within one line raises no trace event — and excluding it
    would discard the self-arc that is the whole signal.

    **2. A short-circuited generator emits neither the back-edge nor an
    exit arc**, so entered-and-never-returned means it yielded at least
    once.  ``any(...)`` and ``next(...)`` abandon the frame mid-yield;
    without this rule every one of them reads as empty.  It is needed
    only for the single-line case — a multi-line generator has already
    reached its element line by rule 1 — but it is applied to both,
    because narrowing it to single-line would make the rule depend on how
    the call happens to be wrapped.

    **3. List, set and dict comprehensions are inlined (PEP 709) and have
    no frame at all**, so rule 2 has nothing to read for them and they
    cannot short-circuit anyway.  The back-edge alone decides them, which
    falls out of rule 2 being asked only of :class:`ast.GeneratorExp`
    rather than being written as a separate branch.

    Returns ``(turned, why_not_decidable)``.  ``None`` is never a guess in
    either direction: a wrong "turned" hides a finding and a wrong "did
    not" fabricates one, and the two shapes below can produce either.
    """
    first = node.lineno
    last = node.end_lineno or first
    element = _element_line(node)

    if element == first and last > first:
        return None, "its element sits on the comprehension's own first line"
    for other in siblings:
        if other is node:
            continue
        # Two comprehensions whose element expressions share a line share
        # every arc that could decide either — nested (`all(any(...) for
        # ...)`) or merely adjacent (`[a for a in x] == [b for b in y]`).
        # Attributing one loop's turn to the other is exactly the guess
        # this function refuses to make.
        if _element_line(other) == element:
            return None, "another comprehension shares its element line"
        if isinstance(node, ast.GeneratorExp) and isinstance(other, ast.GeneratorExp):
            if other.lineno == first:
                return None, "another generator expression shares its frame line"

    for start, end in arcs:
        if end != element or not (first <= start <= last):
            continue
        if element > first and start == first:
            continue
        return True, None

    if isinstance(node, ast.GeneratorExp):
        entered = (-first, first) in arcs
        returned = any(end == -first for _, end in arcs)
        if entered and not returned:
            return True, None
    return False, None


def _comprehension_sites(tree: ast.AST) -> list[tuple[ast.expr, ast.stmt, bool]]:
    """Every comprehension in one file, with its statement and whether it
    sits in an ``assert``'s *message*.

    A comprehension is judged wherever it is written, not only inside
    ``ast.Assert.test`` — ``SNAG-TEST-009`` measured seven live sites that
    bind the comprehension to a local and assert on the *name*, which an
    assert-only walk cannot see and which are guard claims all the same.

    What stays excluded is the message, which is evaluated only when the
    assert has already failed, so its loop turning zero times on a green
    run is the definition of a healthy run rather than a finding.  That
    is why the recursion is hand-written instead of :func:`ast.walk`:
    the distinction is a matter of *which field* a node hangs from, and
    ``ast.walk`` discards exactly that.
    """
    found: list[tuple[ast.expr, ast.stmt, bool]] = []

    def visit(node: ast.AST, statement: ast.stmt | None, in_message: bool) -> None:
        if isinstance(node, ast.stmt):
            statement = node
        if isinstance(node, _COMPREHENSIONS) and statement is not None:
            found.append((node, statement, in_message))
        if isinstance(node, ast.Assert):
            visit(node.test, statement, in_message)
            if node.msg is not None:
                visit(node.msg, statement, True)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, statement, in_message)

    visit(tree, None, False)
    return found


def _loops(
    path: Path,
    tree: ast.AST,
    lines: list[str],
    arcs: set[tuple[int, int]],
    executed: set[int],
) -> list[Loop]:
    """Judge every comprehension in one file."""
    relative = _relative(path)
    sites = _comprehension_sites(tree)
    siblings = [node for node, _, _ in sites]
    judged: list[Loop] = []
    for node, statement, in_message in sites:
        if in_message:
            continue
        turned, undecidable = _loop_turned(node, arcs, siblings)
        judged.append(
            Loop(
                path=relative,
                line=node.lineno,
                statement=statement.lineno,
                source=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                # Anchored on the comprehension, never on the statement,
                # and that was settled by running it rather than by
                # argument.  A `return {...}` in
                # `tests/test_message_backfill_live.py` holds six of
                # them, so a statement-anchored read attached one comment
                # to all six — one declaration covering five sites its
                # author never looked at, which is `UnitFinding.enabled`'s
                # trap.  It shipped *green*, because a stale declaration
                # moves no verdict; only the stale report named it.
                # ``last`` stops there too, so a marker written inside a
                # nested comprehension is not read as a claim about the
                # one wrapping it.
                reason=_declared_reason(
                    node, lines, LOOP_DECLARATION, last=node.lineno
                ),
                turned=turned,
                undecidable=undecidable,
                reached=statement.lineno in executed,
            )
        )
    return judged


def _guards(
    path: Path, tree: ast.AST, lines: list[str], executed: set[int]
) -> tuple[list[Guard], list[Guard]]:
    """Every ``assert`` in one file, and the subset carrying a comprehension.

    Takes the parsed tree rather than the source, so one file is parsed
    once and :func:`_loops` reads the same tree — two parses of one file
    is two statements of what it says.
    """
    relative = _relative(path)
    guards: list[Guard] = []
    blind: list[Guard] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert):
            continue
        guard = Guard(
            path=relative,
            line=node.lineno,
            source=lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
            reason=_declared_reason(node, lines),
            evaluated=node.lineno in executed,
        )
        guards.append(guard)
        if any(isinstance(child, _COMPREHENSIONS) for child in ast.walk(node.test)):
            blind.append(guard)
    return guards, blind


def sweep(
    report: Path, tests_root: Path | None = None, arcs: Path | None = None
) -> Sweep:
    """Join a coverage report to an AST walk of ``tests/``.

    ``arcs`` is the ``coverage run --branch`` data file the same run
    wrote.  It is optional so that ``--report`` alone keeps working for a
    caller holding a fresh JSON report and nothing else; what an absent
    one costs is the comprehension half, and the report *says* it went
    unjudged rather than printing a zero — a sweep that never looked must
    not read like a sweep that found nothing.
    """
    root = tests_root if tests_root is not None else TESTS_ROOT
    read = read_report(report)
    if read is None:
        return Sweep(problem=f"{report} is not a coverage json report")
    executed, measured_at = read

    turns: dict[Path, set[tuple[int, int]]] | None = None
    if arcs is not None:
        turns = read_arcs(arcs)
        if turns is None:
            # Asked for and unreadable is a broken invocation, where
            # *not* asked for is a narrower measure.  Collapsing them
            # would let a data file written without ``--branch`` report
            # every comprehension in the suite as having run over
            # nothing — a missing flag fabricating hundreds of findings.
            return Sweep(
                problem=f"{arcs} carries no branch arcs — was the run made with --branch?"
            )

    findings: list[Guard] = []
    declared: list[Guard] = []
    stale: list[Guard] = []
    loop_findings: list[Loop] = []
    loop_declared: list[Loop] = []
    loop_stale: list[Loop] = []
    loop_undecidable: list[Loop] = []
    loops = 0
    loops_turned = 0
    blind: list[Guard] = []
    unmeasured: list[str] = []
    unparsed: list[str] = []
    moved: list[str] = []
    total = 0
    blind_files: set[str] = set()

    taken = _report_taken_at(measured_at)
    for path in sorted(root.rglob("*.py")):
        resolved = path.resolve()
        try:
            source = path.read_text()
            tree = ast.parse(source)
            lines = source.splitlines()
            guards, file_blind = _guards(path, tree, lines, executed.get(resolved, set()))
        except (OSError, SyntaxError, ValueError):
            unparsed.append(_relative(path))
            continue
        # Counted before any of the three skips below, because the blind
        # population is a property of the *tree* and the skips are
        # properties of the *run*.  Counting it after would let the
        # standing declaration shrink exactly when the measure went
        # blind, which reads as a suite with fewer unjudgeable asserts
        # rather than as a sweep that stopped looking — ``ports_checked``'s
        # rule turned on this module's own report.  Measured while
        # writing it: the three files this fix declared came back
        # ``moved`` and the count fell 314 → 312.
        total += len(guards)
        blind.extend(file_blind)
        if file_blind:
            blind_files.add(file_blind[0].path)
        if taken is not None and path.stat().st_mtime > taken:
            # The join is line numbers against line numbers, so a file
            # edited since the run is being read at somebody else's
            # offsets.  Adding a comment moves every assert below it
            # without changing one statement, which is exactly the shape
            # a digest of the executed set would miss — and exactly what
            # this module's own declarations did to three test files.
            moved.append(_relative(path))
            continue
        if resolved not in executed:
            # Never imported by the measured run.  Its asserts are
            # unevaluated for a reason that is about the measure, so they
            # are not findings and their absence is not health.
            if guards:
                unmeasured.append(_relative(path))
            continue
        for guard in guards:
            if guard.evaluated:
                if guard.reason is not None:
                    stale.append(guard)
            elif guard.reason is not None:
                declared.append(guard)
            else:
                findings.append(guard)

        if turns is None:
            continue
        for loop in _loops(
            path, tree, lines, turns.get(resolved, set()), executed.get(resolved, set())
        ):
            loops += 1
            if loop.turned is None:
                loop_undecidable.append(loop)
            elif loop.turned:
                loops_turned += 1
                if loop.reason is not None:
                    loop_stale.append(loop)
            elif not loop.reached:
                # Its statement never ran, so the loop turning zero times
                # says nothing about the population — the assert half
                # already owns "this never executed", and reporting it
                # here too would give one fault two speakers.
                continue
            elif loop.reason is not None:
                loop_declared.append(loop)
            else:
                loop_findings.append(loop)

    # Report order is the reader's, not ``ast.walk``'s.  That walk is
    # breadth-first, so an assert nested two blocks deep is listed after a
    # top-level one written below it — three of this repository's six live
    # findings came out 166, 167, 147.
    def _order(guard: Guard | Loop) -> tuple[str, int]:
        return (guard.path, guard.line)

    return Sweep(
        findings=tuple(sorted(findings, key=_order)),
        declared=tuple(sorted(declared, key=_order)),
        stale=tuple(sorted(stale, key=_order)),
        unmeasured=tuple(unmeasured),
        unparsed=tuple(unparsed),
        moved=tuple(moved),
        asserts=total,
        comprehension=tuple(blind),
        comprehension_files=len(blind_files),
        measured_at=measured_at,
        loops_measured=turns is not None,
        loops=loops,
        loops_turned=loops_turned,
        loop_findings=tuple(sorted(loop_findings, key=_order)),
        loop_declared=tuple(sorted(loop_declared, key=_order)),
        loop_stale=tuple(sorted(loop_stale, key=_order)),
        loop_undecidable=tuple(sorted(loop_undecidable, key=_order)),
    )


MARKERS: dict[str, str] = {"match": "ok", "mismatch": "no", "unknown": "??"}


def render(result: Sweep) -> list[str]:
    """The report as lines, marker first so a shell caller can colour it.

    ``check-ops-claims.sh``'s three markers, so ``claude-postflight.sh``
    colours this with the loop it already has rather than a fourth
    spelling of one convention.
    """
    lines: list[str] = []
    if result.problem is not None:
        lines.append(f"?? {result.problem}")
    if result.unmeasured:
        lines.append(
            f"?? {len(result.unmeasured)} test files carrying asserts were not measured, "
            "so a clean sweep here would be zero-because-blind"
        )
        lines.extend(f"   {name}" for name in result.unmeasured)
    if result.unparsed:
        lines.append(f"?? {len(result.unparsed)} test files would not parse")
        lines.extend(f"   {name}" for name in result.unparsed)
    if result.moved:
        lines.append(
            f"?? {len(result.moved)} test files were edited after the coverage run, so "
            "their asserts sit at line numbers this report does not describe"
        )
        lines.extend(f"   {name}" for name in result.moved)

    if result.findings:
        lines.append(
            f"no {len(result.findings)} asserts under tests/ were never evaluated by a "
            "green suite — each asserted nothing on this run"
        )
        lines.extend(f"   {guard.where}  {guard.source}" for guard in result.findings)
        lines.append(
            f"   Fix it, or declare it: a `# {DECLARATION} <reason>` comment on the "
            "assert or the line above says why it cannot evaluate on a healthy run"
        )
    elif result.verdict == "match":
        lines.append(f"ok every evaluable assert under tests/ ran ({result.asserts} asserts)")

    if result.declared:
        lines.append(
            f"ok {len(result.declared)} declared may-not-evaluate, and did not — "
            "reported rather than suppressed, so a growing set is visible"
        )
        lines.extend(f"   {guard.where}  {guard.reason}" for guard in result.declared)
    if result.stale:
        lines.append(
            f"ok {len(result.stale)} declared may-not-evaluate and evaluated anyway — "
            "not a fault, and a candidate for deletion once it evaluates every run"
        )
        lines.extend(f"   {guard.where}  {guard.reason}" for guard in result.stale)

    if result.loop_findings:
        lines.append(
            f"no {len(result.loop_findings)} comprehensions under tests/ turned zero "
            "times on a green suite — each ran over an empty population"
        )
        lines.extend(f"   {loop.where}  {loop.source}" for loop in result.loop_findings)
        lines.append(
            f"   Fix it, or declare it: a `# {LOOP_DECLARATION} <reason>` comment on the "
            "statement or the line above says why empty is the healthy state"
        )
    if result.loop_declared:
        lines.append(
            f"ok {len(result.loop_declared)} declared may-not-turn, and did not — "
            "reported rather than suppressed, so a growing set is visible"
        )
        lines.extend(f"   {loop.where}  {loop.reason}" for loop in result.loop_declared)
    if result.loop_stale:
        lines.append(
            f"ok {len(result.loop_stale)} declared may-not-turn and turned anyway — "
            "not a fault, and a candidate for deletion once it turns every run"
        )
        lines.extend(f"   {loop.where}  {loop.reason}" for loop in result.loop_stale)

    # The standing declaration.  Printed on every run whatever the verdict,
    # because it describes the measure and not this run: `ports_checked`
    # literally, a field on every payload carrying whether the measure
    # looked.  Which of the two it prints is the whole of what `--arcs`
    # buys, so the two spellings sit together rather than in two branches
    # of the caller.
    if not result.loops_measured:
        lines.append(
            f"{len(result.comprehension)} of {result.asserts} asserts across "
            f"{result.comprehension_files} files carry a comprehension in their test, "
            "and no branch data was given, so this run did not judge them: "
            "`assert all(f(x) for x in live)` executes its line and is True over an "
            "empty `live`.  Pass --arcs <.coverage from a --branch run>"
        )
    else:
        lines.append(
            f"{result.loops_turned} of {result.loops} comprehension sites under tests/ "
            "turned at least once on this run"
        )
        if result.loop_undecidable:
            lines.append(
                f"{len(result.loop_undecidable)} of them cannot be decided either way "
                "from arcs, and are not counted as either — the shape is the reader's "
                "to change, not this run's"
            )
            lines.extend(
                f"   {loop.where}  {loop.undecidable}"
                for loop in result.loop_undecidable
            )
    if result.measured_at:
        lines.append(f"measured from coverage taken at {result.measured_at}")
    return lines


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-check-guards`` — did every assert under ``tests/`` evaluate?

    Written for a shell caller, so the report is plain text and the
    verdict is in the exit status:

    ==========  ========  ===================================================
    exit        verdict   meaning
    ==========  ========  ===================================================
    ``0``       match     every evaluable assert ran on this suite run
    ``1``       mismatch  at least one asserted nothing and declares no reason
    ``2``       unknown   the measure did not cover ``tests/``
    ==========  ========  ===================================================

    ``mismatch`` covers both halves — an assert that never ran and a
    comprehension that ran over nothing are one claim, *this guard
    asserted nothing*, and giving them two statuses would make the
    remedy depend on which spelling the author happened to use.  There is
    still no fourth status for the sites the arcs cannot decide: that
    reading is printed on every run instead — see the module docstring.
    """
    parser = argparse.ArgumentParser(
        description="Refuse an assert under tests/ that a green suite never evaluated."
    )
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="a `coverage json` report over a green run of the suite",
    )
    parser.add_argument(
        "--arcs",
        type=Path,
        default=None,
        help="the `.coverage` data file of the same run, made with --branch",
    )
    parser.add_argument(
        "--tests-root",
        type=Path,
        default=None,
        help=f"the tree to walk (default {TESTS_ROOT})",
    )
    args = parser.parse_args(argv)

    result = sweep(args.report, args.tests_root, args.arcs)
    for line in render(result):
        print(line)
    return EXIT_STATUS[result.verdict]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
