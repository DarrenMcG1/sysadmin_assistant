"""Re-measure the claims the open snag entries make about this box.

``docs/roadmap/snag_list.md`` is the second document a sitting reads and
the only one nothing has ever checked.  :mod:`sysadmin.ops_claims` gave
``STATUS.md`` a reader on 2026-08-24 because all three ops actions its
opening block carried had already been done; **Session 82 then measured
all thirty open snag entries by hand and found five dead on the box —
three of them ``P1``, and three fixed for between nine and thirteen
days.**  That is ``SNAG-ESTATE-008`` one document over, at five times the
size, and the hand sweep that found it is not repeatable: it cost a whole
sitting and it is out of date the moment the next fix lands.

This module is what goes between the entry and the reader.  An entry
names the check that would refute it, in its own body; the check runs at
the start and the close of every sitting, beside its sibling.

Eight rules, four of them the opposite of the obvious implementation:

1. **A check tests the entry's *mechanism*, never its *population*.**
   This is Session 83's rule read as an instruction to the check author,
   and getting it wrong would make the machinery close the one entry the
   last two sittings argued must stay open.  ``SNAG-LOG-013``'s
   population is empty at the live endpoint **and it is open**, because
   an empty population refills; ``SNAG-ESTATE-008`` closed on an empty
   *residue*, which cannot.  So :func:`check_dropin_blind_spot` asks
   whether the sweep still fails to read a drop-in — which it answers by
   building one — and never whether a drop-in happens to sit on a swept
   unit today, which is the entry's own measured-empty population.

2. **A refuted claim is a candidate for closure and never a closure.**
   :mod:`sysadmin.ops_claims`' rule 6 for its reason: a check that edits
   the document it reads becomes a second author of the claim, and the
   next sitting cannot tell a measured entry from a written one.  The
   remedy differs from that module's too, and the report says so — a
   stale ops claim is reworded, a refuted snag is *judged*, and Session
   83 spent a sitting on one such judgement.

3. **The marker lives in the entry's body and never in its title.**  The
   title is another repository's input: estate-manager's ``read_snags``
   takes the whole heading text, and ``_trailing_parenthetical`` requires
   it to end in ``)`` before it will look for a closure clause at all.  A
   marker appended to a title would change what the board publishes about
   this repository, which is the cross-repo write the estate rules
   forbid, arriving inside a local convenience.

4. **The marker names a check and the check names its entry — a pin, not
   a restatement.**  Every :class:`Check` carries the ``SNAG`` id it is
   about, and the entry carrying the marker must be that entry.  Rule 7
   of :mod:`sysadmin.ops_claims` refuses a marker that restates a
   *value*; an id is not a value, it is the other end of a binding, and a
   binding with only one end is what a copy-pasted body bullet produces.
   :func:`sysadmin.core.logging_setup.syslog_priority`'s treatment
   against ``journal.PRIORITY_MAP``: not asserted on each side, pinned.

5. **Every way of not-knowing is ``unknown``, never ``match``** —
   imported wholesale from :mod:`sysadmin.core.schema_guard` along with
   the verdicts and the exit map, because a claim nobody managed to test
   and a claim that still holds are the two answers a hand sweep cannot
   tell apart and the reason the sweep was worth automating.

6. **An entry with no check is the finding, not the silence.**
   ``SNAG-ESTATE-012`` records that a sentence with no pattern and no
   marker is invisible; here the equivalent is an open entry no check
   names, and it is *counted and named* rather than left out of the
   report.  Sixteen of the twenty-four open entries are in that state as
   this ships, which is the honest starting position and the same one
   :mod:`sysadmin.ops_claims` shipped in.

7. **The instrument is chosen per claim, and a grep is almost never it.**
   A claim about what the source *says* — an unread config leaf, a count
   of call sites — is an ``ast`` walk, because ``ast.Attribute.attr`` is
   an exact string where a grep is a substring: ``grep review_hour``
   matches ``log_review_hour``, ``disk_review_hour`` and
   ``health_review_hour``, and would report ``SNAG-CFG-002`` refuted on
   the first run.  That is the instrument that mis-ranked Session 81's
   sweep and mis-scoped ``SNAG-DOCS-002`` before it, now for the third
   time.  A claim about what the code *does* is driven instead — this
   module is a composition root and may import any domain.

8. **The open set is read here and pinned against its owner.**
   ``read_snags`` lives in ``estate_service`` rather than in
   ``estate-lib``, so it cannot be imported; the closure rule below is
   therefore a second implementation of somebody else's fact, which this
   repository refuses everywhere it can.  It is narrowed to under-report
   closure — an entry counts as open unless its trailing parenthetical
   declares otherwise at a clause start — so the error direction is
   *more* entries reported unchecked rather than fewer, and
   ``tests/test_snag_claims.py`` drives both readers over the real file
   whenever estate-manager's venv is present.  Filed as cross-repo
   friction rather than absorbed.

**This module sits beside main.py** for the reason :mod:`sysadmin.reload`,
:mod:`sysadmin.metadata` and :mod:`sysadmin.ops_claims` do.  It imports a
domain today (``units.scan``, to reproduce a sweep) and the next check
written will import another, so a ``core/snag_claims.py`` would break the
rule that makes every other boundary real the first time anyone extended
it.  ``tests/test_import_boundary.py`` names it as the fifth composition
root.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess  # noqa: S404 — one read-only `systemctl show`
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.schema_guard import EXIT_STATUS, SchemaVerdict

#: The same three words and the same exit map as the schema check and the
#: ops claims, imported rather than restated.  ``mismatch`` is a claim the
#: box no longer supports; ``unknown`` is a claim nobody managed to test.
type Verdict = SchemaVerdict

SNAG_PATH = REPO_ROOT / "docs" / "roadmap" / "snag_list.md"

#: estate-manager's port registry, read read-only.  ``SNAG-ESTATE-005`` is
#: a claim about a row in it, so the claim cannot be tested from inside
#: this repository at all — which is a property of the entry rather than a
#: reason to leave it unchecked.
ESTATE_REGISTRY = (
    Path.home() / "projects" / "estate-manager" / "docs" / "guides" / "monitorable-project.md"
)

#: How many unchecked entry ids are named before the rest are counted.
#: ``SNAG-ESTATE-001``'s rule — a roll-up that cannot name anything is the
#: defect, so the overflow is stated rather than dropped.
MAX_NAMED_ENTRIES = 8

#: ``<!--check:key-->`` in an entry's body.  An HTML comment because the
#: document is read by people first, and deliberately without an argument:
#: :mod:`sysadmin.ops_claims` needs one for ``expires`` because a
#: prediction's instant is stated nowhere else, and an entry states
#: everything about itself in its own body.
MARKER_RE = re.compile(r"<!--\s*check:\s*([a-z0-9_]+)\s*-->")

#: A markdown inline code span, closed by a backtick run of the **same
#: length** that opened it.  Markdown's own rule, and load-bearing rather
#: than pedantic: a span quoting a marker that itself contains backticks
#: is written with a doubled fence, and a pattern that closed on *any*
#: run would stop at the inner single backtick and leave the marker bare.
#: Found by writing exactly that sentence into ``SNAG-DOCS-005``'s body
#: and watching the check report the marker it was describing — the
#: second of the two things about this convention that could only have
#: been learned by running it.  See :func:`strip_code_spans`.
CODE_SPAN_RE = re.compile(r"(`+)[\s\S]*?\1")

#: A snag id, in this document's dialect.
SNAG_ID_RE = re.compile(r"\b(SNAG-(?:[A-Z]+-)?\d+)\b")

#: A bracketed priority, recorded as written.
PRIORITY_RE = re.compile(r"\[(P\d)\]")

#: Rule 8's narrowed closure rule.  A completion word that **opens a
#: clause** of the title's trailing parenthetical, which is the half of
#: estate-manager's rule that stops ``SNAG-AGENT-004`` — *"26,270 alert
#: rows … can never be resolved or purged"* — from reading as closed.
DONE_WORD_RE = re.compile(
    r"^(fixed|closed|resolved|complete|completed|done|shipped|superseded"
    r"|won'?t\s*fix|no\s*longer)\b",
    re.IGNORECASE,
)

#: Where one clause of a provenance parenthetical ends and the next opens.
CLAUSE_RE = re.compile(r"[,;:()—–]|\band\b", re.IGNORECASE)

#: Leading punctuation, emphasis and tick marks before a clause's first
#: word.  ``**FIXED 2026-08-24**`` is the live shape.
DRESSING_RE = re.compile(r"^[^A-Za-z]+")

#: A heading that files entries as finished.  A section counts as open
#: unless it names closure — estate-manager's exclusion, kept because this
#: document's own ``## Fixed Issues`` is the thing it excludes.
CLOSED_HEADING_WORDS = ("fixed", "closed", "resolved", "done", "complete", "shipped")

#: A section that is a worked example rather than a list of real entries.
TEMPLATE_HEADING_WORDS = ("creating", "template", "example")


# ---------------------------------------------------------------------------
# Reading the document
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Entry:
    """One snag entry as the document has it.

    Attributes:
        snag_id: the id in the title, upper-cased, or ``None``.
        priority: ``P0``–``P3`` as written, or ``None``.
        title: the entry's first line, verbatim.
        body: the indented bullets beneath it, joined.
        is_open: rule 8's narrowed reading — open unless the title's
            trailing parenthetical declares closure at a clause start.
        markers: every check the body names, in the order it names them.
    """

    snag_id: str | None
    priority: str | None
    title: str
    body: str
    is_open: bool
    markers: tuple[str, ...] = ()


def trailing_parenthetical(title: str) -> str | None:
    """The contents of the title's final bracket, or ``None``.

    Balanced from the right, because this document's provenance brackets
    nest: ``(2026-08-16, **scope corrected the same sitting** — filed for
    one stale action, measured at three of three, …)``.
    """
    stripped = title.rstrip()
    if not stripped.endswith(")"):
        return None
    depth = 0
    for index in range(len(stripped) - 1, -1, -1):
        if stripped[index] == ")":
            depth += 1
        elif stripped[index] == "(":
            depth -= 1
            if depth == 0:
                return stripped[index + 1 : -1]
    return None


def closure_declared(title: str) -> bool:
    """Does the entry's own title report it as finished?

    Read from the trailing provenance parenthetical only, and within it
    only where a completion word opens a clause.  Both halves are
    load-bearing against this very file and in opposite directions:
    ``SNAG-AGENT-004``'s title says *"can never be resolved or purged"*
    and a search over the whole title closes an entry that was open for
    thirteen days, while ``SNAG-DB-002``'s reads ``check half **fixed
    2026-08-13**`` and stays open because the clause opens with "check".

    Under-reports by construction and never invents — rule 8's stated
    direction, because an entry wrongly reported *unchecked* costs a
    reader a glance and one wrongly reported *closed* removes it from the
    population this module exists to sweep.
    """
    parenthetical = trailing_parenthetical(title)
    if parenthetical is None:
        return False
    for clause in CLAUSE_RE.split(parenthetical):
        stripped = clause.strip()
        dressing = DRESSING_RE.match(stripped)
        head = stripped[len(dressing.group(0)) :] if dressing else stripped
        if DONE_WORD_RE.match(head):
            return True
    return False


def open_sections(document: str) -> list[list[str]]:
    """The lines of every ``##`` section that files entries as outstanding.

    Stated as an exclusion for estate-manager's reason: a list of
    open-sounding words would have to guess, and every document on this
    box names its *closed* section explicitly.
    """
    sections: list[list[str]] = []
    current: list[str] | None = None
    for line in document.splitlines():
        if line.startswith("## "):
            heading = line[3:].strip().lower()
            template = any(word in heading for word in TEMPLATE_HEADING_WORDS)
            closed = any(word in heading for word in CLOSED_HEADING_WORDS)
            current = None if (template or closed) else []
            if current is not None:
                sections.append(current)
            continue
        if current is not None:
            current.append(line)
    return sections


def read_entries(document: str) -> list[Entry]:
    """Every entry under an open heading, with its body and its markers.

    A top-level ``- `` bullet opens an entry and everything indented
    beneath it is that entry's body, which is this document's dialect and
    the one ``read_snags`` calls ``bullet``.
    """
    entries: list[Entry] = []
    for lines in open_sections(document):
        title: str | None = None
        body: list[str] = []
        for line in [*lines, "- "]:  # a sentinel bullet flushes the last entry
            if line.startswith("- "):
                if title is not None:
                    entries.append(_entry(title, body))
                title, body = line, []
            elif title is not None:
                body.append(line)
        if title is not None and title != "- ":
            entries.append(_entry(title, body))
    return entries


def strip_code_spans(text: str) -> str:
    """The text with every markdown code span removed.

    **A quoted marker is a quotation, not a marker**, and this is the one
    rule of the convention that could only have been learned by running
    it.  The first live run reported two checks nobody implements,
    ``helth`` and ``routes``, both "named by ``SNAG-ESTATE-011``" — an
    entry that names neither.  What it does is *discuss* the convention:
    its body carries ``` `<!--check:routes-->` is not that ``` and
    ``` `<!--check:helth-->` produced *two* findings ```, the second of
    which is a deliberately misspelled example.  This document is the one
    place on the box that writes *about* markers, so a marker syntax with
    no way to be quoted cannot be used in it.

    A code span is the right boundary rather than a heuristic over
    surrounding words: backticks are markdown's own way of saying "this is
    text about text", and every one of the four live quotations is inside
    one.  Deliberately not shared with
    :func:`sysadmin.ops_claims.read_markers`, which has the same hazard
    with — measured 2026-08-25 — an empty population: nine markers in
    ``STATUS.md``'s printed region and no quoted one.  Filed as
    ``SNAG-DOCS-005`` rather than fixed here, because a composition root
    importing another composition root to share a regex is a coupling
    worth more than the copy.
    """
    return CODE_SPAN_RE.sub(" ", text)


def _entry(title: str, body_lines: list[str]) -> Entry:
    body = "\n".join(body_lines)
    id_match = SNAG_ID_RE.search(title)
    priority_match = PRIORITY_RE.search(title)
    return Entry(
        snag_id=id_match.group(1).upper() if id_match else None,
        priority=priority_match.group(1).upper() if priority_match else None,
        title=title.strip(),
        body=body,
        is_open=not closure_declared(title),
        markers=tuple(
            match.group(1) for match in MARKER_RE.finditer(strip_code_spans(body))
        ),
    )


def load_entries(path: Path | None = None) -> tuple[list[Entry], str]:
    """:func:`read_entries` of the snag list on disk, or ``[]`` and why not."""
    target = path or SNAG_PATH
    try:
        document = target.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"{target} could not be read ({exc.__class__.__name__})"
    entries = read_entries(document)
    if not entries:
        return [], f"{target} has no open section holding '- ' entries"
    return entries, ""


# ---------------------------------------------------------------------------
# Instruments
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Measurement:
    """What a check found: a verdict, a sentence, and the evidence."""

    verdict: Verdict
    note: str = ""
    detail: tuple[str, ...] = ()


def _parse(path: Path) -> ast.Module | None:
    """A source file as a tree, or ``None`` when it will not read.

    Never an import.  Rule 7's second half is about the *claim*, and every
    claim in this registry about what the source says is answered by what
    the source says — importing would additionally run module-level code
    at the top of every sitting, which a report has no business doing.
    """
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return None


def _python_files(roots: Iterable[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file():
            found.append(root)
            continue
        found.extend(p for p in sorted(root.rglob("*.py")) if "__pycache__" not in p.parts)
    return found


def attribute_reads(attrs: frozenset[str], roots: Iterable[Path]) -> list[str]:
    """Every ``something.attr`` *load* of one of ``attrs``, as file:line.

    Rule 7.  ``ast.Attribute.attr`` is the exact final segment, so
    ``schedules.log_review_hour`` does not answer for
    ``schedules.review_hour`` — which a substring search cannot avoid and
    which is the whole reason this is not three lines of ``grep``.  A
    field's *definition* is an ``AnnAssign`` over a ``Name`` and falls out
    for free, so the declaring module does not count as its own reader.
    """
    hits: list[str] = []
    for path in _python_files(roots):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr in attrs
                and isinstance(node.ctx, ast.Load)
            ):
                hits.append(f"{_rel(path)}:{node.lineno}")
    return hits


def method_calls(path: Path, name: str) -> list[int]:
    """The line of every call to ``<anything>.name(...)`` in one file.

    A call, never a mention: the ``def`` that declares it, the docstring
    that names it and the comment above the caller are all excluded
    without a special case, which is ``test_contract_reachability``'s rule
    read for a different question.
    """
    tree = _parse(path)
    if tree is None:
        return []
    return sorted(
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
    )


def discarded_tasks(path: Path, coroutine: str) -> list[int]:
    """Bare ``asyncio.create_task(x.<coroutine>(...))`` statements.

    "Bare" is the load-bearing word and the reason this is not a search
    for ``create_task``: the defect ``SNAG-LOG-006`` describes is a task
    nobody keeps a reference to, and ``sysadmin/core/event_bus.py`` calls
    the same function two lines under a comment explaining why it assigns
    the result.  An ``ast.Expr`` wrapper is exactly "the value was
    discarded", so the distinction is structural rather than a heuristic
    over names.
    """
    tree = _parse(path)
    if tree is None:
        return []
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            continue
        call = node.value
        if not (isinstance(call.func, ast.Attribute) and call.func.attr == "create_task"):
            continue
        if not call.args or not isinstance(call.args[0], ast.Call):
            continue
        inner = call.args[0].func
        if isinstance(inner, ast.Attribute) and inner.attr == coroutine:
            lines.append(node.lineno)
    return sorted(lines)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def unit_load_state(unit: str) -> str:
    """``LoadState`` for one unit, or a word saying why there is none.

    ``systemctl show`` answers for a unit that does not exist and exits
    ``0`` — :class:`sysadmin.ops_claims.UnitState` records the same trap —
    so ``not-found`` here is a real measurement and not an absence.
    """
    try:
        result = subprocess.run(
            ["systemctl", "show", unit, "-p", "LoadState"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return f"unmeasured ({exc.__class__.__name__})"
    for line in result.stdout.splitlines():
        if line.startswith("LoadState="):
            return line.split("=", 1)[1].strip()
    return "unmeasured (no LoadState)"


def query_one(statement: str) -> tuple[object | None, str]:
    """One scalar off a short-lived sync connection, or ``None`` and why not.

    :func:`sysadmin.core.schema_guard.live_revision_sync`'s pattern for
    its reason: every caller of this module runs outside a running
    application, so ``get_engine()`` would raise before any query ran.
    """
    config = get_config()
    engine = create_engine(config.database.sync_url)
    try:
        with engine.connect() as conn:
            return conn.execute(text(statement)).scalar(), ""
    except Exception as exc:  # noqa: BLE001 — an unreachable database is "unknown"
        return None, f"the database did not answer ({exc.__class__.__name__})"
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------

#: The unit file whose ordering ``SNAG-SYSD-003`` is about, and the unit
#: it names that no longer exists.
SYSADMIN_UNIT = REPO_ROOT / "systemd" / "sysadmin.service"
RETIRED_UNIT = "ollama.service"

#: ``SNAG-AGENT-007``'s figure, in its own words: *"four unbounded reads
#: of the alerts table per 300-second run"*.  Call sites, which is what
#: the entry enumerates — ``_check_anomalies``, ``_check_agent_health``,
#: ``_check_collation`` and ``_execute``'s dedup snapshot.
AGENT_PATH = REPO_ROOT / "sysadmin" / "monitor" / "agent.py"
EXPECTED_ACTIVE_ALERTS_CALLS = 4

#: ``SNAG-LOG-006``'s two composition roots, and the count it measured.
MANUAL_RUN_PATHS = (
    REPO_ROOT / "sysadmin" / "main.py",
    REPO_ROOT / "sysadmin" / "files" / "router.py",
)
EXPECTED_DISCARDED_RUNS = 5

#: ``SNAG-CFG-002``'s two leaves.  The sibling leaves that *are* read
#: (``review_day_of_week``, and the three ``*_review_hour`` pairs) are the
#: reason rule 7 refuses a substring search.
REVIEW_SCHEDULE_LEAVES = frozenset({"review_hour", "review_minute"})
REVIEW_SCHEDULE_YAML_RE = re.compile(r"(?m)^\s*review_(?:hour|minute)\s*:")

#: ``SNAG-DOCS-003``'s five names and the module holding them.
DEPRECATED_MODULE = REPO_ROOT / "sysadmin_tray" / "_deprecated_contracts.py"
DEPRECATED_NAMES = frozenset(
    {
        "RecommendationInfo",
        "ProjectRecommendationsResponse",
        "PortfolioAction",
        "PortfolioActionsResponse",
        "ProjectReviewResponse",
    }
)

#: ``SNAG-ESTATE-005``'s row and the name it gives the port.
ESTATE_PORT = "8500"
ESTATE_PORT_CLAIMANT = "sysadmin-service"


def check_sysd_ollama_ordering() -> Measurement:
    """``SNAG-SYSD-003`` — a retired unit still named in ``After=``.

    Two halves, and they are reported apart because they refute the entry
    for opposite reasons: the ordering line losing ``ollama.service`` is
    the *fix*, and ``ollama.service`` coming back is the claim's premise
    dying while the line stands.  A single boolean would report a
    reinstalled Ollama as a job well done.
    """
    try:
        unit_text = SYSADMIN_UNIT.read_text(encoding="utf-8")
    except OSError as exc:
        return Measurement("unknown", f"{_rel(SYSADMIN_UNIT)} ({exc.__class__.__name__})")
    ordering = [line for line in unit_text.splitlines() if line.startswith("After=")]
    if not ordering:
        return Measurement("unknown", f"{_rel(SYSADMIN_UNIT)} declares no After=")
    named = any(RETIRED_UNIT in line for line in ordering)
    state = unit_load_state(RETIRED_UNIT)
    detail = (f"{ordering[0]}", f"{RETIRED_UNIT} LoadState={state}")
    if state.startswith("unmeasured"):
        return Measurement("unknown", f"systemd would not answer for {RETIRED_UNIT}", detail)
    if named and state == "not-found":
        return Measurement("match", "", detail)
    if not named:
        return Measurement(
            "mismatch",
            f"the After= line no longer names {RETIRED_UNIT} — the entry describes an "
            "ordering that has been edited",
            detail,
        )
    return Measurement(
        "mismatch",
        f"{RETIRED_UNIT} is {state} rather than not-found — the ordering is stale "
        "prose no longer, it is a live dependency, and the entry's remedy is wrong",
        detail,
    )


def check_run_status_cancelled() -> Measurement:
    """``SNAG-DB-006`` — a constraint value nothing writes.

    Both halves again, and again for opposite reasons: the constraint
    losing ``cancelled`` is one of the entry's two named fixes, and a row
    appearing is the other.
    """
    definition, problem = query_one(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'chk_run_status'"
    )
    if problem:
        return Measurement("unknown", problem)
    if definition is None:
        return Measurement("unknown", "no constraint named chk_run_status exists")
    admitted = "cancelled" in str(definition)
    written, problem = query_one(
        f"SELECT count(*) FROM {get_config().database.schema_}.agent_runs "  # noqa: S608
        "WHERE status = 'cancelled'"
    )
    if problem:
        return Measurement("unknown", problem)
    detail = (f"chk_run_status admits 'cancelled': {admitted}", f"rows written: {written}")
    if admitted and written == 0:
        return Measurement("match", "", detail)
    if not admitted:
        return Measurement(
            "mismatch",
            "chk_run_status no longer admits 'cancelled' — the value was dropped, "
            "which is the first of the entry's two opposite fixes",
            detail,
        )
    return Measurement(
        "mismatch",
        f"{written} agent_runs row(s) carry status='cancelled' — something writes it now, "
        "which is the second of the entry's two opposite fixes",
        detail,
    )


def check_review_schedule_unread() -> Measurement:
    """``SNAG-CFG-002`` — two config leaves parsed and read by nothing.

    Rule 7's founding case.  ``grep review_hour`` matches
    ``log_review_hour``, ``disk_review_hour`` and ``health_review_hour``
    on this checkout and would report the entry refuted the first time it
    ran; ``ast.Attribute.attr`` is the exact segment and matches none of
    them.
    """
    readers = attribute_reads(
        REVIEW_SCHEDULE_LEAVES,
        (REPO_ROOT / "sysadmin", REPO_ROOT / "sysadmin_tray", REPO_ROOT / "tests"),
    )
    config_path = REPO_ROOT / "config.yaml"
    try:
        if REVIEW_SCHEDULE_YAML_RE.search(config_path.read_text(encoding="utf-8")):
            readers.append(f"{_rel(config_path)}: sets one of the leaves")
    except OSError as exc:
        return Measurement("unknown", f"config.yaml could not be read ({exc.__class__.__name__})")
    if not readers:
        return Measurement("match", "", ("no reader of schedules.review_hour/review_minute",))
    return Measurement(
        "mismatch",
        f"{len(readers)} reader(s) of schedules.review_hour/review_minute — the leaves "
        "drive something now, or the entry's remedy has already been taken",
        tuple(readers[:MAX_NAMED_ENTRIES]),
    )


def check_active_alerts_reads() -> Measurement:
    """``SNAG-AGENT-007`` — four unbounded reads of ``alerts`` per run.

    Counts *call sites*, which is what the entry enumerates, and says so
    on both verdicts: a caller inside a branch is still one site, and the
    entry's own claim is about how many places issue the query rather
    than how many times one run happens to take a branch.
    """
    lines = method_calls(AGENT_PATH, "_active_alerts")
    detail = (f"{_rel(AGENT_PATH)} call sites: " + ", ".join(str(n) for n in lines),)
    if len(lines) == EXPECTED_ACTIVE_ALERTS_CALLS:
        return Measurement("match", "", detail)
    direction = "fewer" if len(lines) < EXPECTED_ACTIVE_ALERTS_CALLS else "more"
    return Measurement(
        "mismatch",
        f"{len(lines)} call sites, not {EXPECTED_ACTIVE_ALERTS_CALLS} — {direction} than the "
        "entry counts, so its figure is stale whichever way it moved",
        detail,
    )


def check_manual_run_unawaited() -> Measurement:
    """``SNAG-LOG-006`` — manual runs started by a task nobody holds.

    The check is structural rather than nominal: a bare ``ast.Expr``
    around ``create_task`` *is* the discard, so
    ``sysadmin/core/event_bus.py``'s deliberate ``task = loop.create_task(…)``
    two lines under a comment explaining itself is excluded by the
    grammar rather than by a name.
    """
    found: list[str] = []
    for path in MANUAL_RUN_PATHS:
        found.extend(f"{_rel(path)}:{line}" for line in discarded_tasks(path, "run"))
    if len(found) == EXPECTED_DISCARDED_RUNS:
        return Measurement("match", "", tuple(found))
    return Measurement(
        "mismatch",
        f"{len(found)} discarded agent-run task(s), not {EXPECTED_DISCARDED_RUNS} — a "
        "reference is kept somewhere the entry says none is, or a trigger was added",
        tuple(found[:MAX_NAMED_ENTRIES]),
    )


def check_deprecated_contracts() -> Measurement:
    """``SNAG-DOCS-003`` — five deprecated models with no reader here.

    The entry's closure needs an *operational* fact this repository cannot
    check — where the wheel went — so what is measurable is the other
    half: that the five are still defined and still unread inside this
    checkout.  A check that cannot answer the whole question answers the
    part it can and says which part, which is ``ports_checked``'s rule.
    """
    tree = _parse(DEPRECATED_MODULE)
    if tree is None:
        return Measurement(
            "mismatch",
            f"{_rel(DEPRECATED_MODULE)} does not parse or is gone — the removal the entry "
            "describes may already have happened",
        )
    defined = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    missing = DEPRECATED_NAMES - defined
    if missing:
        return Measurement(
            "mismatch",
            f"{len(missing)} of the five names are no longer defined — the shim has been "
            "trimmed and the entry's population has moved",
            tuple(sorted(missing)),
        )
    readers = [
        f"{_rel(path)}"
        for path in _python_files((REPO_ROOT / "sysadmin", REPO_ROOT / "sysadmin_tray"))
        if path not in (DEPRECATED_MODULE, REPO_ROOT / "sysadmin_tray" / "models.py")
        and _names_used(path) & DEPRECATED_NAMES
    ]
    if not readers:
        return Measurement("match", "", (f"five names defined in {_rel(DEPRECATED_MODULE)}",))
    return Measurement(
        "mismatch",
        f"{len(readers)} module(s) name one of the five — the entry's *"
        "nothing reads any of the five* no longer holds",
        tuple(sorted(set(readers))[:MAX_NAMED_ENTRIES]),
    )


def _names_used(path: Path) -> set[str]:
    """Every identifier a module *uses*, imports excluded.

    ``test_contract_reachability``'s rule 2, borrowed whole: a name in an
    import list is not a reader, and a docstring is an ``ast.Constant``
    that falls out for free — which is exactly what made
    ``RecommendationInfo`` look alive off one line of prose the last time
    this question was asked.
    """
    tree = _parse(path)
    if tree is None:
        return set()
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    return used


def check_estate_port_8500() -> Measurement:
    """``SNAG-ESTATE-005`` — the port registry's row for 8500.

    The claim is entirely about another repository's document, which is
    why the entry is delegated and why the check reads that document
    read-only.  It answers "does the row still say this", never "should
    it" — the estate owns the fix, and a consumer that judged the wording
    would be the second owner the estate rules exist to prevent.
    """
    try:
        registry = ESTATE_REGISTRY.read_text(encoding="utf-8")
    except OSError as exc:
        return Measurement(
            "unknown", f"{ESTATE_REGISTRY} could not be read ({exc.__class__.__name__})"
        )
    rows = [
        line
        for line in registry.splitlines()
        if line.startswith("|") and line.split("|")[1].strip() == ESTATE_PORT
    ]
    if not rows:
        return Measurement(
            "mismatch",
            f"the registry has no row for {ESTATE_PORT} — the row the entry is about is gone",
        )
    claimant = rows[0].split("|")[2].strip()
    detail = (rows[0].strip(),)
    if claimant == ESTATE_PORT_CLAIMANT:
        return Measurement("match", "", detail)
    return Measurement(
        "mismatch",
        f"the {ESTATE_PORT} row now names '{claimant}' rather than "
        f"'{ESTATE_PORT_CLAIMANT}' — estate-manager has edited it",
        detail,
    )


def check_dropin_blind_spot() -> Measurement:
    """``SNAG-UNITS-006`` — the sweep cannot read a drop-in.

    **Rule 1's founding case, and the one check here that had to be
    driven rather than read.**  The entry's population is measured empty
    on this box — zero of the 38 swept units has a drop-in — so a check
    that looked for one would report the entry refuted on the day it was
    filed, which is exactly the reading Session 83 refused for
    ``SNAG-LOG-013``.  What the entry claims is a *mechanism*, so the
    mechanism is reproduced: a synthetic unit with a drop-in that sets
    ``RestartSec=``, swept, and the parsed value compared against what
    the drop-in says.  Session 82's ``SNAG-ROADMAP-001`` treatment —
    reproduced rather than reasoned about.
    """
    from sysadmin.units.scan import discover_units

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "snagcheck.service").write_text(
            "[Unit]\nDescription=drop-in probe\n\n"
            "[Service]\nExecStart=/bin/true\nRestart=always\nRestartSec=1\n\n"
            "[Install]\nWantedBy=default.target\n",
            encoding="utf-8",
        )
        dropin = root / "snagcheck.service.d"
        dropin.mkdir()
        (dropin / "override.conf").write_text(
            "[Service]\nRestartSec=99\n", encoding="utf-8"
        )
        units, _ = discover_units(root, None, str(Path.home()))

    probe = next((unit for unit in units if unit.name == "snagcheck.service"), None)
    if probe is None:
        return Measurement(
            "unknown",
            "the sweep did not return the probe unit at all — its exclusion rules have "
            "moved and this check no longer measures what it claims to",
        )
    detail = (f"drop-in sets RestartSec=99; the sweep read restart_sec={probe.restart_sec}",)
    if probe.restart_sec == 1.0:
        return Measurement("match", "", detail)
    if probe.restart_sec == 99.0:
        return Measurement(
            "mismatch",
            "the sweep now reads drop-in directories — the blind spot the entry describes "
            "is closed",
            detail,
        )
    return Measurement(
        "unknown",
        f"the sweep read restart_sec={probe.restart_sec}, which is neither the unit's 1 "
        "nor the drop-in's 99 — the probe no longer isolates the question",
        detail,
    )


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    """One check, and the entry it is about.

    Attributes:
        key: what a marker names.  A name, never a value, and never the
            snag id — the id is the *other end* of the binding, and rule 4
            pins them against each other rather than deriving one from the
            other.
        snag: the entry this check refutes.  Pinned against the entry
            carrying the marker.
        subject: what is being claimed, in words.
        run: the measurement.
    """

    key: str
    snag: str
    subject: str
    run: Callable[[], Measurement]


CHECKS: dict[str, Check] = {
    check.key: check
    for check in (
        Check(
            "sysd_ollama_ordering",
            "SNAG-SYSD-003",
            "sysadmin.service orders after a retired unit",
            check_sysd_ollama_ordering,
        ),
        Check(
            "run_status_cancelled",
            "SNAG-DB-006",
            "chk_run_status admits a value nothing writes",
            check_run_status_cancelled,
        ),
        Check(
            "review_schedule_unread",
            "SNAG-CFG-002",
            "schedules.review_hour/minute drive nothing",
            check_review_schedule_unread,
        ),
        Check(
            "active_alerts_reads",
            "SNAG-AGENT-007",
            "_active_alerts is read four times a run",
            check_active_alerts_reads,
        ),
        Check(
            "manual_run_unawaited",
            "SNAG-LOG-006",
            "manual agent runs are started and discarded",
            check_manual_run_unawaited,
        ),
        Check(
            "deprecated_contracts",
            "SNAG-DOCS-003",
            "five deprecated models, no reader here",
            check_deprecated_contracts,
        ),
        Check(
            "estate_port_8500",
            "SNAG-ESTATE-005",
            "the estate's 8500 row names no project id",
            check_estate_port_8500,
        ),
        Check(
            "dropin_blind_spot",
            "SNAG-UNITS-006",
            "the unit sweep cannot read a drop-in",
            check_dropin_blind_spot,
        ),
    )
}


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One line of the report.

    Attributes:
        key: the check key, or a ``convention:`` identifier.
        snag: the entry the line is about, where there is one.
        subject: what is being claimed, in words.
        kind: ``"claim"`` when an entry's claim was measured,
            ``"convention"`` when the finding is about the pairing between
            document and registry.  Rule 2 — the remedies differ, so the
            kinds do.
        verdict: see :data:`Verdict`.
        note: one sentence naming the fault and its direction.
        detail: the evidence.
    """

    key: str
    snag: str | None
    subject: str
    kind: str
    verdict: Verdict
    note: str = ""
    detail: tuple[str, ...] = field(default_factory=tuple)


def _convention(key: str, subject: str, note: str, detail: tuple[str, ...] = ()) -> Finding:
    return Finding(key, None, subject, "convention", "unknown", note, detail)


def run_check(check: Check) -> Finding:
    """One check, with any fault inside it reported rather than raised.

    A check that raises is a check that did not run, which is ``unknown``
    — rule 5.  Letting it propagate would take the whole report down with
    it and hand a sitting *no* answer about the other seven, which is the
    outcome a report exists to prevent.
    """
    try:
        measurement = check.run()
    except Exception as exc:  # noqa: BLE001 — a check that raises is a check that did not run
        measurement = Measurement("unknown", f"the check raised {exc.__class__.__name__}: {exc}")
    return Finding(
        check.key,
        check.snag,
        check.subject,
        "claim",
        measurement.verdict,
        measurement.note,
        measurement.detail,
    )


def check_convention(entries: list[Entry], entries_problem: str) -> list[Finding]:
    """The three ways the document and the registry can fall out of step.

    **A marker naming no check** is a typo, a rename, or a check deleted
    out from under the entry that relies on it.  All three end the same
    way: the entry looks verified and is not, which is worse than an
    unchecked entry, because an unchecked entry does not claim to have
    been looked at.

    **A check whose entry does not carry its marker** is rule 4's pin
    failing.  Two shapes reach it — a marker on the wrong entry, which is
    what a copy-pasted body bullet produces, and a check outliving the
    entry it was written for, which is what closing an entry produces if
    nobody removes the check.

    **Open entries no check names** is rule 6, and it is the number the
    hand sweep was.  Reported as a count with the ids named, because a
    count that cannot name anything is ``SNAG-ESTATE-001``'s defect and
    this document is where that was learned.
    """
    if entries_problem:
        return [_convention("convention:document", "Snag list", entries_problem)]

    findings: list[Finding] = []
    marked: dict[str, list[str]] = {}
    for entry in entries:
        for key in entry.markers:
            marked.setdefault(key, []).append(entry.snag_id or entry.title[:40])

    for key in sorted(set(marked) - set(CHECKS)):
        findings.append(
            _convention(
                f"marker:{key}",
                f"Entry names check '{key}'",
                f"nothing implements '{key}' — the entry relying on it is unchecked "
                f"(known: {', '.join(sorted(CHECKS))})",
                tuple(f"named by {snag}" for snag in marked[key]),
            )
        )

    for key, check in sorted(CHECKS.items()):
        carriers = marked.get(key, [])
        if check.snag in carriers:
            continue
        findings.append(
            _convention(
                f"pin:{key}",
                f"Check '{key}' names {check.snag}",
                f"{check.snag} does not carry <!--check:{key}--> — the check and the entry "
                "have come apart, so the entry reads as unchecked and the check as orphaned"
                + (f" (carried by {', '.join(carriers)} instead)" if carriers else ""),
            )
        )

    checked = {check.snag for check in CHECKS.values()}
    unchecked = [
        entry.snag_id or entry.title[:40]
        for entry in entries
        if entry.is_open and (entry.snag_id or "") not in checked
    ]
    if unchecked:
        named = tuple(unchecked[:MAX_NAMED_ENTRIES])
        if len(unchecked) > MAX_NAMED_ENTRIES:
            named = (*named, f"… and {len(unchecked) - MAX_NAMED_ENTRIES} more")
        findings.append(
            _convention(
                "convention:unchecked",
                "Open entries no check names",
                f"{len(unchecked)} of {sum(1 for e in entries if e.is_open)} open entries "
                "carry no check — their claims are only as fresh as the last hand sweep",
                named,
            )
        )
    return findings


def check_all(path: Path | None = None) -> list[Finding]:
    """Every check, then the convention findings.

    The convention findings run even when the document cannot be read at
    all: a missing snag list is a reason to know less about the entries,
    never a reason to stop measuring the claims — the same split
    :func:`sysadmin.ops_claims.check_all` makes for its state checks.
    """
    entries, problem = load_entries(path)
    return [
        *(run_check(CHECKS[key]) for key in sorted(CHECKS)),
        *check_convention(entries, problem),
    ]


def overall(findings: list[Finding]) -> Verdict:
    """``mismatch`` outranks ``unknown``, which outranks ``match``.

    :func:`sysadmin.ops_claims.overall`'s rule and its reason: not
    ``max()`` over :data:`EXIT_STATUS`, which would rank a check that
    failed to run above a claim measured false.
    """
    verdicts = {finding.verdict for finding in findings}
    if "mismatch" in verdicts:
        return "mismatch"
    if "unknown" in verdicts:
        return "unknown"
    return "match"


MARKERS: dict[str, str] = {"match": "ok", "mismatch": "no", "unknown": "??"}

#: What ``match`` means here, spelled out, because it is the opposite of
#: what it means one module over: a snag claim that holds is a bug that is
#: still real, and the good news is the *red* line.
WORDING: dict[str, str] = {
    "match": "still holds",
    "mismatch": "refuted",
    "unknown": "not measured",
}


def render(findings: list[Finding]) -> list[str]:
    """The report as lines, marker first so a shell caller can colour it."""
    lines = []
    for finding in findings:
        head = f"{MARKERS[finding.verdict]} "
        if finding.snag:
            head += f"{finding.snag}: {finding.subject} — {WORDING[finding.verdict]}"
        else:
            head += finding.subject
        if finding.note:
            head += f" — {finding.note}"
        lines.append(head)
        lines.extend(f"   {item}" for item in finding.detail)
    return lines


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-check-snags`` — do the open entries still describe this box?

    Exit status is :data:`sysadmin.core.schema_guard.EXIT_STATUS`: ``0``
    every claim still holds, ``1`` at least one is refuted, ``2`` at least
    one could not be tested and none is refuted.  ``1`` is deliberately
    not a failure — a refuted claim is an entry to *judge*, and rule 2 is
    why nothing here decides that.
    """
    parser = argparse.ArgumentParser(
        description="Re-measure the claims docs/roadmap/snag_list.md's open entries make."
    )
    parser.add_argument(
        "--snag-file",
        type=Path,
        default=None,
        help=f"the document to read entries from (default {SNAG_PATH})",
    )
    args = parser.parse_args(argv)

    findings = check_all(args.snag_file)
    for line in render(findings):
        print(line)
    return EXIT_STATUS[overall(findings)]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
