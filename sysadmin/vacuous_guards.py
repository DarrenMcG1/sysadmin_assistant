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

**The count it cannot judge is stated on every run, and that is
deliberately not a fourth exit status.**  Line coverage is structurally
blind to ``assert all(f(x) for x in live)``: the comprehension is ``True``
over an empty ``live`` and the assert line *executes*.  Measured here at
314 of 6300 asserts across 52 files, unmoved across three sittings — a
property of the *measure* and permanent, so a status firing on it fires
for ever, which is ``SNAG-LOG-002``'s binary ``LOW`` confidence and a
permanent warning nothing can clear.  0/1/2 keeps ``check-migrations.sh``'s
meaning, each a property of *this* run a sitting can act on, and the blind
population rides on every report instead: Session 128's rule 4, uniform on
every row with the value carrying the news.
"""

from __future__ import annotations

import argparse
import ast
import json
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

#: The comprehension node types whose truth over an empty iterable is
#: ``True`` (or, for the dict and set forms, whose emptiness is
#: indistinguishable from a satisfied population at the assert line).
#: ``ast.Assert.test`` only: a comprehension inside the *message* cannot
#: decide whether the guard held.
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
class Sweep:
    """What one coverage report says about ``tests/``.

    ``findings`` is the answer; everything else is the reading it was
    made under, which is why the blind population and the declared set
    are fields rather than a branch.
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

    @property
    def verdict(self) -> Verdict:
        """``unknown`` outranks ``mismatch``, which is the reverse of the
        usual ordering here and is forced by what the two mean.

        A sweep that could not read part of ``tests/`` has not found
        "no findings and one blind spot" — its finding count is a lower
        bound taken over an unknown fraction of the suite, so reporting
        it as a mismatch would put a number on a reading that has none.
        """
        if self.problem is not None or self.unmeasured or self.unparsed or self.moved:
            return "unknown"
        if self.findings:
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


def _comment_block_above(node: ast.Assert, lines: list[str]) -> list[int]:
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


def _declared_reason(node: ast.Assert, lines: list[str]) -> str | None:
    """What the file declares about this assert, or ``None``.

    Read from the comment block above the ``assert`` or from any line of
    the statement itself.  Both spellings mean one thing, so both are
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
        _, marker, rest = lines[index].partition(DECLARATION)
        if not marker:
            continue
        parts = [rest.strip()]
        for following in block[position + 1 :]:
            parts.append(lines[following].strip().lstrip("#").strip())
        return " ".join(part for part in parts if part) or None

    statement = range(node.lineno - 1, min(node.end_lineno or node.lineno, len(lines)))
    for index in statement:
        _, marker, rest = lines[index].partition(DECLARATION)
        if marker:
            return rest.strip() or None
    return None


def _guards(path: Path, source: str, executed: set[int]) -> tuple[list[Guard], list[Guard]]:
    """Every ``assert`` in one file, and the subset carrying a comprehension."""
    tree = ast.parse(source)
    lines = source.splitlines()
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


def sweep(report: Path, tests_root: Path | None = None) -> Sweep:
    """Join a coverage report to an AST walk of ``tests/``."""
    root = tests_root if tests_root is not None else TESTS_ROOT
    read = read_report(report)
    if read is None:
        return Sweep(problem=f"{report} is not a coverage json report")
    executed, measured_at = read

    findings: list[Guard] = []
    declared: list[Guard] = []
    stale: list[Guard] = []
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
            guards, file_blind = _guards(path, source, executed.get(resolved, set()))
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

    # Report order is the reader's, not ``ast.walk``'s.  That walk is
    # breadth-first, so an assert nested two blocks deep is listed after a
    # top-level one written below it — three of this repository's six live
    # findings came out 166, 167, 147.
    def _order(guard: Guard) -> tuple[str, int]:
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

    # The standing declaration.  Printed on every run whatever the verdict,
    # because it describes the measure and not this run: `ports_checked`
    # literally, a field on every payload carrying whether the measure
    # looked.
    lines.append(
        f"{len(result.comprehension)} of {result.asserts} asserts across "
        f"{result.comprehension_files} files carry a comprehension in their test, and "
        "this measure cannot judge them: `assert all(f(x) for x in live)` executes its "
        "line and is True over an empty `live`"
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

    There is no fourth status for the comprehension half.  That reading
    is printed on every run instead — see the module docstring.
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
        "--tests-root",
        type=Path,
        default=None,
        help=f"the tree to walk (default {TESTS_ROOT})",
    )
    args = parser.parse_args(argv)

    result = sweep(args.report, args.tests_root)
    for line in render(result):
        print(line)
    return EXIT_STATUS[result.verdict]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
