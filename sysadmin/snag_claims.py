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
import asyncio
import inspect
import json
import logging
import re
import subprocess  # noqa: S404 — a read-only `systemctl show`, and estate-manager's own venv
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.escalation import humanise_hours
from sysadmin.core.schema_guard import EXIT_STATUS, SchemaVerdict
from sysadmin.core.text import strip_markdown
from sysadmin.ops_claims import EXPIRY_FORMAT, check_expiry, read_markers

if TYPE_CHECKING:  # pragma: no cover — annotations only
    from collections.abc import Awaitable, Mapping

    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession

    from sysadmin.estate.agent import EstateJudgeAgent
    from sysadmin.monitor.services import ServiceEntry

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
#: been learned by running it.  It is also what separated the two
#: candidate fixes for that entry: the naive ``` `[^`]+` ``` handles the
#: single fence and leaks the doubled one, which is why the entry closed
#: on the same-length pattern and not on the obvious one.  See
#: :func:`strip_code_spans`.
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
    one.

    **Still a copy rather than an import**, and the reason survived the
    entry it was filed under.  ``SNAG-DOCS-005`` recorded the hazard here
    against an empty population in :mod:`sysadmin.ops_claims` — nine
    markers in ``STATUS.md``'s printed region on 2026-08-25 and no quoted
    one — and that module gained :data:`sysadmin.ops_claims.CODE_SPAN_RE`
    on 2026-08-26, closing it.  Sharing one pattern would have a
    composition root import another to borrow a regex, and it would put
    this document's parser at the mercy of an edit made for the
    dashboard's.  The two are pinned on *behaviour* instead, by
    ``tests/test_ops_claims.py``: import where you can, pin where you
    cannot.
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
        markers=tuple(match.group(1) for match in MARKER_RE.finditer(strip_code_spans(body))),
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


def _called_name(node: ast.Call) -> str | None:
    """The final segment of a call's callee, for a ``Name`` or an ``Attribute``.

    ``unwrap_json_message(...)`` and ``journal.unwrap_json_message(...)``
    are the same call site under two import styles, and a check that saw
    only one of them would report a backfill absent because whoever wrote
    it imported the module rather than the name.
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def call_sites(name: str, roots: Iterable[Path]) -> list[tuple[str, str]]:
    """Every call to ``name``, as ``(file:line, enclosing def)``.

    The **enclosing function is the half that carries the claim**, and it
    is why this is not :func:`method_calls` with a wider net.
    ``SNAG-LOG-008`` says the unwrap happens at read time; a call that
    moved out of ``read_journal`` into a query path or a migration is the
    same count of call sites and a different mechanism, so a check
    counting them alone would report a landed fix as unchanged.

    ``<module>`` names a call at module scope — a one-off backfill's
    likeliest shape outside ``alembic/`` — so it is a value the caller can
    act on rather than an absence.  Nested definitions take the innermost
    name, which falls out of descending rather than walking.
    """
    found: list[tuple[str, int, str]] = []
    for path in _python_files(roots):
        tree = _parse(path)
        if tree is None:
            continue
        rel = _rel(path)

        def descend(node: ast.AST, enclosing: str, rel: str = rel) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                    descend(child, child.name)
                    continue
                if isinstance(child, ast.Call) and _called_name(child) == name:
                    found.append((rel, child.lineno, enclosing))
                descend(child, enclosing)

        descend(tree, "<module>")
    # Sorted on the line *number*, not on the rendered ``file:line`` — a
    # string sort files line 10 before line 9, which is a report that
    # reads as unordered rather than as ordered by something else.
    return [(f"{rel}:{line}", enclosing) for rel, line, enclosing in sorted(found)]


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

#: ``SNAG-ESTATE-002``'s subject is estate-manager's own code, reachable
#: only by running it: ``estate_service`` is not installed here and is not
#: in ``estate-lib``, so the instrument is their interpreter, the same one
#: ``tests/test_snag_claims.py`` already drives ``read_snags`` with.  Held
#: as a package root rather than as one module path because the check that
#: first needed it — ``SNAG-ROADMAP-001``'s, removed with its entry on
#: 2026-08-26 — was about a single module and this one is about two.
ESTATE_SERVICE = Path.home() / "projects" / "estate-manager" / "service"
ESTATE_PYTHON = ESTATE_SERVICE / ".venv" / "bin" / "python"
ESTATE_PROBE_TIMEOUT = 60

#: The two modules ``SNAG-ESTATE-002`` spans: the dataclass that computes
#: a nudge's wording, and the route that serialises it.  **Both** are
#: named because the entry's candidate remedies land in different files —
#: converting the properties is ``nudges.py``, augmenting the payload
#: beside the ``asdict`` call is ``oversight.py`` — so a checkout state
#: read for one of them would say nothing about a fix landing in the
#: other, which is the half of ``ports_checked``'s rule that bites when
#: the thing being reported on is somebody else's tree.
ESTATE_NUDGE_MODULES = (
    Path("estate_service") / "projects" / "nudges.py",
    Path("estate_service") / "projects" / "oversight.py",
)

#: The three properties the entry says never reach the wire.  ``details``
#: is the third and went unmentioned when the entry was filed; it is
#: included because the entry's own body says a fix converting ``title``
#: and ``message`` and stopping there "leaves the same defect one field
#: over", and a check that could not see that would report such a fix as
#: a clean closure.
NUDGE_WORDING = ("title", "message", "details")


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
        (dropin / "override.conf").write_text("[Service]\nRestartSec=99\n", encoding="utf-8")
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


#: ``SNAG-LOG-013``'s probe, and the live record shape it reproduces.
#: This box's one JSON-writing journal source puts a whole record on a
#: line (``SNAG-LOG-008``), so nine of its signatures agree as far as
#: ``"logger": "sysadmin.core.agent", "message": "alert_raised`` and
#: diverge only past the cap.
PROBE_SOURCE = "snagcheck.service"
PROBE_RECORD_HEAD = (
    '{"timestamp": "N-N-NTN:N:N.N", "level": "ERROR", '
    '"logger": "sysadmin.core.agent", "message": "alert_raised", "detail": "'
)
PROBE_FILLER = "field value "

#: The offsets the two halves put between the probe's first sightings,
#: both derived from ``INCIDENT_WINDOW_SECONDS`` rather than picked: one
#: comfortably inside the window, one comfortably outside it.  The
#: constant is derived from a *gap* in the live separations (349 ms
#: against 64.4 s), so anything within an order of magnitude of it is a
#: number this check would have to keep in step by hand.
PROBE_INSIDE_FRACTION = 0.1
PROBE_OUTSIDE_MULTIPLE = 2.0


def probe_signatures(cap: int) -> tuple[str, str]:
    """Two signatures that agree past ``cap`` and diverge only after it.

    **Derived from the constant rather than written beside it** —
    :func:`sysadmin.core.journal.max_priority_for` against
    ``PRIORITY_MAP``, and load-bearing here in a way it is not in most of
    this registry.  ``SNAG-LOG-013`` says in its own body that *raising
    the cap is not the fix*, because any bound is defeated by two records
    that differ past it and a larger number only moves where.  A probe
    with a hard-coded prefix would therefore report the entry refuted the
    day somebody moved
    :data:`~sysadmin.monitor.log_actions.SIGNATURE_DETAIL_CHARS` to 400 —
    reporting a fix in the one remedy the entry argues against.
    """
    filler = PROBE_FILLER * (cap // len(PROBE_FILLER) + 2)
    prefix = (PROBE_RECORD_HEAD + filler)[: cap * 2]
    return f'{prefix}alpha"}}', f'{prefix}bravo"}}'


def check_capped_signature_collides() -> Measurement:
    """``SNAG-LOG-013`` — a capped signature can name two faults at once.

    **Rule 1's second case, and the entry Session 83 kept open to state
    the rule.**  Its population is empty at the live endpoint — all ten
    raw-JSON rows were ingested inside eleven minutes on 2026-08-17 and
    left the seven-day ``current`` window the same afternoon it was filed
    — so a check that asked *does any pair collide today* would report it
    refuted for the reason that mis-ranked its parent ``SNAG-LOG-010``.
    What the entry claims is a mechanism, so the mechanism is driven:
    two signatures that agree past the cap, through the real
    :func:`~sysadmin.monitor.log_actions.recommend`, twice.

    **Two halves, and they are reported apart because they fail to
    different fixes.**  The entry's title is a conjunction — capping *can*
    put two rows back where ``SNAG-LOG-010`` found them, and inside one
    roll-up it *already has* — so the halves are the two clauses:

    - **grouped**, where the pair lands inside
      ``INCIDENT_WINDOW_SECONDS`` and the roll-up's own member lines are
      compared.  This is the "one level down it is already visible"
      bullet, and it is the half a divergence-aware cap would close.
    - **apart**, where the same pair lands outside the window and becomes
      two rows whose *titles* are compared.  This is the headline, and it
      is the half a disambiguator in
      :func:`~sysadmin.monitor.log_actions.quoted_signature` would close
      while leaving the roll-up naming none of its members.

    The probe varies **only the signature**.  The first draft of the
    second half used two different sources, and the titles came apart —
    ``_new_recommendation`` opens a title with the source name, so the
    fixture reported the claim refuted for a reason that has nothing to
    do with the cap.  A check whose fixture moves two things at once
    cannot say which one it measured.

    What it cannot reach is the entry's first candidate fix: making the
    signature readable at the producer removes the *population* and
    leaves the mechanism exactly as it is, so this check would go on
    reporting *still holds*.  That is rule 1 rather than a gap —
    ``SNAG-LOG-008``'s fix retires the class on this box and not the
    property — and it is why the live table is deliberately not consulted
    here at all.
    """
    from sysadmin.monitor.log_actions import (
        INCIDENT_WINDOW_SECONDS,
        SIGNATURE_DETAIL_CHARS,
        capped_signature,
        recommend,
    )
    from sysadmin.monitor.log_trends import (
        ChangeKind,
        Confidence,
        LogTrendReport,
        SignatureTrend,
    )

    first, second = probe_signatures(SIGNATURE_DETAIL_CHARS)
    if capped_signature(first) == first:
        return Measurement(
            "unknown",
            "the probe's signatures come back uncapped, so it no longer isolates the "
            "truncation the entry is about",
        )

    anchor = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

    def _rows(offset: float):
        def _trend(signature: str, seconds: float) -> SignatureTrend:
            seen = anchor + timedelta(seconds=seconds)
            return SignatureTrend(
                signature=signature,
                alert_title=f"Log error: {PROBE_SOURCE}",
                source=PROBE_SOURCE,
                severity="error",
                sample=signature,
                current=1,
                previous=0,
                total=1,
                first_seen=seen,
                last_seen=seen,
                change=ChangeKind.NEW,
            )

        return recommend(
            LogTrendReport(
                window_days=7,
                window_start=anchor - timedelta(days=7),
                previous_start=anchor - timedelta(days=14),
                generated_at=anchor,
                confidence=Confidence.HIGH,
                signatures=[_trend(first, 0.0), _trend(second, offset)],
            )
        )

    grouped = _rows(INCIDENT_WINDOW_SECONDS * PROBE_INSIDE_FRACTION)
    apart = _rows(INCIDENT_WINDOW_SECONDS * PROBE_OUTSIDE_MULTIPLE)

    if len(grouped) != 1 or len(grouped[0].members) != 2:
        return Measurement(
            "unknown",
            f"the probe's pair produced {len(grouped)} row(s) inside the incident window "
            "rather than one roll-up of two — the grouping rule has moved and this half "
            "no longer measures the cap",
        )
    if len(apart) != 2:
        return Measurement(
            "unknown",
            f"the probe's pair produced {len(apart)} row(s) outside the incident window "
            "rather than two — the grouping rule has moved and this half no longer "
            "measures the cap",
        )

    members = [line for line in grouped[0].detail.splitlines() if line.startswith("  - ")]
    if len(members) != 2:
        return Measurement(
            "unknown",
            f"the roll-up named {len(members)} member line(s) rather than two — its detail "
            "no longer names what it swallows, which is a different entry",
        )
    members_collide = members[0] == members[1]
    titles_collide = apart[0].title == apart[1].title

    detail = (
        f"cap {SIGNATURE_DETAIL_CHARS}; the pair agrees over "
        f"{len(probe_signatures(SIGNATURE_DETAIL_CHARS)[0]) - len('alpha"}')} characters",
        f"roll-up member lines identical: {members_collide}",
        f"separate rows' titles identical: {titles_collide}",
        f"as rendered: {members[0].strip()}",
    )

    if members_collide and titles_collide:
        return Measurement("match", "", detail)
    if members_collide:
        return Measurement(
            "mismatch",
            "two separate rows no longer share a title — the headline half is closed and "
            "the roll-up still names none of its members, so the entry needs narrowing "
            "rather than closing",
            detail,
        )
    if titles_collide:
        return Measurement(
            "mismatch",
            "the roll-up now distinguishes its members — the entry's second candidate fix "
            "has landed for the detail and not for the titles",
            detail,
        )
    return Measurement(
        "mismatch",
        "neither half collides — two signatures that agree past the cap now render "
        "apart, which is the divergence-aware cap the entry asks for",
        detail,
    )


def estate_module_state(modules: Iterable[Path]) -> str:
    """Whether the modules the probe just ran are committed over there.

    ``ports_checked``'s rule applied to somebody else's repository.  A
    ``mismatch`` measured against a **committed** fix means close the
    entry; one measured against an edit in flight means wait, and the two
    have opposite remedies — so the verdict alone is not enough and the
    difference is carried as evidence rather than left for the reader to
    go and find.

    The sitting that wrote this needed it within the hour: estate-manager
    was mid-fix in the exact file ``SNAG-ROADMAP-001`` turned on, so the
    first ``mismatch`` this module ever produced was off an uncommitted
    edit — and the *next* sitting closed that entry on this sentence
    changing, which is the only trigger either of them had.

    **Committed is not deployed, and the wording says ``committed`` for
    that reason.**  The first draft said "not released", which reads as a
    claim about what is *running* over there; it is not one.  When
    ``SNAG-ROADMAP-001`` was closed on 2026-08-26 their fix had been
    committed at 22:42 the previous evening and the daemon on 8400 had
    last started at 11:35, eleven hours before it — so the committed fix
    was demonstrably not the code being served.  That gap is
    estate-manager's deploy state rather than a fact about the claim, and
    judging it here is the second owner the estate rules exist to
    prevent, so it is named and never measured.

    The dirty paths are **named** rather than counted, this document's own
    rule about a roll-up that cannot say what it swallowed.  Read-only,
    and never a reason to fail — an unanswerable question yields a
    sentence saying so.
    """
    paths = [str(ESTATE_SERVICE / module) for module in modules]
    if not paths:
        return "no estate-manager module was named, so its checkout state was not read"
    try:
        result = subprocess.run(  # noqa: S603 — a read-only `git status` over there
            ["git", "-C", str(ESTATE_SERVICE), "status", "--porcelain", "--", *paths],
            capture_output=True,
            text=True,
            timeout=ESTATE_PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return "estate-manager's checkout state could not be read"
    if result.returncode != 0:
        return "estate-manager's checkout state could not be read"
    dirty = sorted({line[3:].strip() for line in result.stdout.splitlines() if line[3:].strip()})
    if not dirty:
        return (
            "measured against estate-manager's committed tree — committed, which is not "
            "the same as deployed on 8400"
        )
    return (
        "measured against uncommitted edits in estate-manager's tree — not released: "
        + ", ".join(dirty)
    )


def estate_probe(script: str) -> tuple[dict[str, object] | None, str]:
    """Run ``script`` in estate-manager's interpreter and read its JSON.

    Returns the payload and a problem sentence, one of which is always
    empty.  **Every way of not running is a problem rather than an
    answer** — rule 5, and this is the one instrument in the registry
    that can fail for reasons having nothing to do with the claim.

    The interpreter is theirs because ``estate_service`` is neither
    installed here nor in ``estate-lib``, which is the same wall
    :data:`tests.test_snag_claims` hits driving ``read_snags`` and the
    same one rule 8 files as cross-repo friction rather than absorbing.
    Read-only in both directions: nothing is written into their tree, and
    the script is handed on ``-c`` rather than left in it.
    """
    if not ESTATE_PYTHON.exists():
        return None, (
            f"estate-manager's interpreter is not at {ESTATE_PYTHON} — the module this "
            "entry is about cannot be run from here"
        )
    try:
        result = subprocess.run(  # noqa: S603 — a fixed interpreter, a literal script
            [str(ESTATE_PYTHON), "-c", script],
            capture_output=True,
            text=True,
            timeout=ESTATE_PROBE_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"estate-manager's interpreter would not run ({exc.__class__.__name__})"
    if result.returncode != 0:
        tail = " ".join(result.stderr.split())[-200:]
        return None, f"estate-manager's parser would not import or run: {tail}"
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        return None, "estate-manager's parser answered something that is not JSON"
    if not isinstance(payload, dict):
        return None, "estate-manager's parser answered JSON that is not an object"
    return payload, ""


#: The probe handed to :func:`estate_probe`.  It builds one ``Nudge``,
#: reads the wording the producer computes off it, and serialises it the
#: way ``GET /api/projects/attention`` does.
#:
#: **Nothing private is touched, and nothing is typed that the producer
#: can restate.**  ``SNAG-ROADMAP-001``'s check learned that the hard way
#: — its first draft named a private helper whose rename was the fix it
#: existed to notice — so the specimen's arguments come from
#: ``dataclasses.fields(Nudge)`` rather than from a literal field list
#: here.  That is what lets the *first* candidate remedy be seen at all:
#: converting ``title`` and ``message`` from properties into fields
#: changes the constructor's signature, and a probe holding its own copy
#: of that signature would raise ``TypeError`` and report ``unknown`` for
#: ever, structurally unable to witness the closure it exists to notice.
#:
#: ``textwrap.dedent`` rather than ``inspect.cleandoc``: ``cleandoc``
#: treats the block as a docstring and dedents every line *after* the
#: first, which happens to be a no-op on a module-level function and
#: mangles every other kind.  The real route is module-level, so the
#: wrong tool agreed with the only specimen it was tried against —
#: caught by driving the detector at a nested function instead.
NUDGE_PROBE = '''\
import ast, dataclasses, inspect, json, sys, textwrap
sys.path.insert(0, {service!r})
from dataclasses import asdict
from estate_service.projects import nudges, oversight

FILLER = {{"str": "probe", "int": 7, "bool": False}}


def filler_for(annotation):
    """A value for one field, whichever form the annotation survives as.

    ``dataclasses.fields(...).type`` is the annotation *string* under
    ``from __future__ import annotations`` and the type *object* without
    it.  The producer uses the future import and a stub need not, so both
    are read rather than the live form being assumed.
    """
    name = annotation if isinstance(annotation, str) else getattr(annotation, "__name__", "")
    return FILLER.get(name)


def specimen():
    """A Nudge built from whatever fields the dataclass declares today."""
    kwargs = {{}}
    for field in dataclasses.fields(nudges.Nudge):
        kwargs[field.name] = filler_for(field.type)
    return nudges.Nudge(**kwargs)


def payload_is_bare_asdict(func):
    """Does the route serialise a nudge with an unaugmented asdict()?"""
    tree = ast.parse(textwrap.dedent(inspect.getsource(func)))
    for node in ast.walk(tree):
        elt = getattr(node, "elt", None)
        if not isinstance(node, ast.ListComp) or not isinstance(elt, ast.Call):
            continue
        if (
            isinstance(elt.func, ast.Name)
            and elt.func.id == "asdict"
            and len(elt.args) == 1
            and isinstance(elt.args[0], ast.Name)
            and not elt.keywords
        ):
            return True
    return False


nudge = specimen()
offered, raised = {{}}, []
for name in {wording!r}:
    try:
        offered[name] = str(getattr(nudge, name))
    except AttributeError:
        continue
    except Exception as exc:
        raised.append(name + ": " + exc.__class__.__name__)

print(json.dumps({{
    "offered": sorted(offered),
    "raised": raised,
    "title": offered.get("title"),
    "message": offered.get("message"),
    "published": sorted(asdict(nudge)),
    "route_bare_asdict": payload_is_bare_asdict(oversight.attention),
}}))
'''


def _probe_names(value: object) -> list[str]:
    """One list of names out of a probe's JSON, or none at all.

    :func:`estate_probe` guarantees an object and nothing about what is
    inside it, because the producer is another repository's — so a key
    that has stopped being a list is read as absent rather than iterated.
    That direction is deliberate: an empty list flows into the verdicts
    below and is *answered*, where a ``TypeError`` here would be caught
    by :func:`run_check` and reported as ``unknown`` with a traceback
    class name in place of the sentence a sitting needs.
    """
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def check_nudge_wording_unpublished() -> Measurement:
    """``SNAG-ESTATE-002`` — a wording the producer computes and drops.

    ``Nudge.title``, ``.message`` and ``.details`` are ``@property``;
    ``GET /api/projects/attention`` serialises with
    ``dataclasses.asdict``, which emits **fields only**.  So the
    producer's single source of truth for a nudge's wording is
    unreachable from the consumer that renders it, and
    :mod:`sysadmin.estate.judgements` built its own — the copy-drift
    estate-manager exists to remove, in the one place both repositories
    carry a comment claiming otherwise.

    **The mechanism is asked, never the population** — rule 1, and this
    entry is the one where getting it wrong would be cheapest to do.
    ``/api/projects/attention`` has answered ``{"health": [], "nudges":
    []}`` on every occasion anyone has looked, twice after an overnight
    scheduled scan, so a check reading the live route would report *no
    nudges* and could never distinguish that from *no wording on the
    nudges there are*.  A specimen is built instead, exactly as
    :func:`check_dropin_blind_spot` builds a unit it could not find.

    **All three of the entry's candidate remedies are reachable, and
    that is what decided the shape.**  The entry offers publishing the
    properties as fields, augmenting the payload beside the ``asdict``
    call, or deleting the properties and the "one place" comment so the
    producer stops claiming a role it does not fill.  The first shows up
    as the wording appearing in ``asdict``; the third as the wording
    being *absent from the object*, which is a refutation and not a
    failure to measure, because the entry's complaint is that both sides
    think they own the format and neither says so — a producer that has
    stopped claiming it has answered that.  The second cannot be seen in
    ``asdict`` at all, so the route's serialisation is read as well, and
    a route that no longer hands the list straight out of a bare
    ``asdict`` is ``unknown`` rather than ``match``: the probe has
    stopped isolating the question and saying so is rule 5.

    **A partial fix is ``mismatch`` with the residue named.**  The entry
    says in its own body that converting ``title`` and ``message`` and
    stopping there "leaves the same defect one field over", so a check
    reporting that state as ``match`` would hide the fix and one
    reporting it as a clean refutation would hide the residue.  It is a
    candidate for closure — rule 2 hands the judgement to a sitting
    either way — and what that sitting needs is the name of the field
    still being dropped, which the note carries.

    Delegated, so what is measured is the **producer**, never this
    repository's consumer: :func:`check_estate_port_8500`'s refusal in
    writing, and ``SNAG-ROADMAP-001``'s. Whether
    :mod:`sysadmin.estate.judgements` should keep its own title is a
    separate question the entry already answers *yes* to, and a check
    that folded it in would be judging a decision rather than a claim.
    """
    payload, problem = estate_probe(
        NUDGE_PROBE.format(service=str(ESTATE_SERVICE), wording=NUDGE_WORDING)
    )
    if payload is None:
        return Measurement("unknown", problem)

    #: Ordered by :data:`NUDGE_WORDING` rather than alphabetically, so a
    #: note reading "title, message now reach the wire and details still
    #: do not" names the fields in the order the entry argues about them.
    seen = set(_probe_names(payload.get("offered")))
    offered = [name for name in NUDGE_WORDING if name in seen]
    raised = _probe_names(payload.get("raised"))
    published = _probe_names(payload.get("published"))
    bare = payload.get("route_bare_asdict")
    dropped = [name for name in offered if name not in published]
    carried = [name for name in offered if name in published]
    detail = (
        f"Nudge offers {', '.join(offered) or 'none of ' + ', '.join(NUDGE_WORDING)}",
        f"the route's asdict() publishes {', '.join(published)}",
        f"producer's title: {payload.get('title')!r}",
        f"producer's message: {payload.get('message')!r}",
        f"attention() serialises with a bare asdict(): {bare}",
        estate_module_state(ESTATE_NUDGE_MODULES),
    )

    if raised:
        return Measurement(
            "unknown",
            "the specimen no longer satisfies the wording it is asked for "
            f"({'; '.join(raised)}) — the probe has stopped isolating the question",
            detail,
        )
    if not offered:
        return Measurement(
            "mismatch",
            "the producer no longer computes a title, message or details at all — the "
            "entry's delete remedy, which ends the two-owners problem rather than the "
            "publishing one",
            detail,
        )
    if carried and not dropped:
        return Measurement(
            "mismatch",
            "the wording the producer computes now reaches the wire — "
            f"{', '.join(carried)} are serialised, which is the outcome the entry asks for",
            detail,
        )
    if carried:
        return Measurement(
            "mismatch",
            f"{', '.join(carried)} now reach the wire and {', '.join(dropped)} still "
            "do not — the partial fix this entry warned of, so the residue is what needs "
            "judging rather than the closure",
            detail,
        )
    if bare is not True:
        return Measurement(
            "unknown",
            "attention() no longer serialises a nudge with a bare asdict(), so a fix "
            "augmenting the payload at the call site would not show here — the probe no "
            "longer isolates what reaches the wire",
            detail,
        )
    return Measurement("match", "", detail)


#: ``SNAG-LOG-008``'s subject.  The entry is about the one JSON-writing
#: journal source on this box — the fact Sessions 61 and 64 both leant on,
#: read here a third way: it is the only source whose records the two
#: declarations can disagree about, so it is the only source at which the
#: entry's mechanism is observable at all.
UNWRAP_UNIT = "sysadmin.service"

#: The window and floor the probe reads at.  ``info`` rather than the
#: source's declared ``warning`` because the population wanted is *any*
#: record this daemon wrote, and its access log is the only line it emits
#: reliably; a floor matching the declaration would make the probe depend
#: on the daemon having had a bad day.
UNWRAP_PROBE_SINCE = "1 day ago"
UNWRAP_PROBE_SEVERITY = "info"
UNWRAP_PROBE_LIMIT = 50

#: The two declarations that bracket the defect: what ``services.yaml``
#: said before the Session 64 deploy, and what it says now.  Passed to the
#: same function in the same process, minutes apart, so the *only*
#: variable between the two reads is the declaration.
UNWRAP_BEFORE = "text"
UNWRAP_AFTER = "json"

#: Where a backfill could land.  ``alembic/`` because this repository puts
#: data migrations there and Session 67 already ran one, and ``sysadmin/``
#: because a serve-time unwrap in ``log_query`` or ``log_trends`` would
#: answer the entry just as well.  ``tests/`` is deliberately absent: the
#: five direct calls there exercise the function and reshape nothing.
UNWRAP_FUNCTION = "unwrap_json_message"
UNWRAP_READER = "read_journal"
UNWRAP_BACKFILL_ROOTS = (REPO_ROOT / "sysadmin", REPO_ROOT / "alembic")


def envelope_message(raw_message: str) -> str | None:
    """The ``message`` a record's envelope carries, or ``None``.

    ``raw_message`` is journald's own ``MESSAGE``, taken from the verbatim
    record rather than from either read, so the population this decides is
    the same one under both declarations.

    **Deliberately this module's own reading of "an envelope" rather than
    a call to** :func:`~sysadmin.monitor.journal.unwrap_json_message`,
    which is the function under test.  Using it to decide the population
    would make the probe agree with the code under test by construction —
    a check that cannot fail is the defect
    :mod:`sysadmin.ops_claims`' third rule recorded one day before this
    was written, where a pin searched a region containing its own marker
    and passed whatever the sentence said.

    So it is a second implementation of somebody else's fact, which this
    repository refuses everywhere it can, and it is admitted here for the
    one reason that survives: the two must be able to **disagree**.  It is
    narrowed to under-report — an envelope counts only when the whole
    record parses and yields a non-empty string ``message`` — so its error
    direction is a smaller population and never a false one.
    """
    if not raw_message.startswith("{"):
        return None
    try:
        payload = json.loads(raw_message)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    inner = payload.get("message")
    return inner if isinstance(inner, str) and inner else None


def record_identity(raw_line: str) -> tuple[str, str] | None:
    """A journal record's own identity, from the verbatim line, or ``None``.

    **Not ``raw_line`` itself, and that correction is the one thing about
    this check a live run had to supply.**  The first draft paired the two
    reads on ``raw_line`` and argued for it well: it is the field
    :func:`~sysadmin.monitor.journal.unwrap_json_message`'s own rule 3
    promises is kept *verbatim*, so the code under test guarantees the
    key.  Driven at the real journal it paired **0 of 50** records —
    ``journalctl -o json`` emits a record's fields in an order that is not
    stable between invocations, so two reads of one record return two
    byte-different lines that parse to the identical dict.  The rule
    promises the record's *content* survives the unwrap; the draft read a
    content guarantee as an identity guarantee.

    ``__REALTIME_TIMESTAMP`` and ``MESSAGE`` are journald's own, are
    unmoved by the declaration, and separate the eight ``alert_raised``
    records this daemon can write inside one millisecond, which a
    timestamp alone does not.  ``__CURSOR`` would be the single-field
    answer and is refused: ``raw_line`` is capped at 2000 characters and
    the field order that broke the first draft decides whether the cursor
    falls inside it — ``SNAG-LOG-008``'s own body records that truncation
    hiding a ``__CURSOR`` once already.
    """
    try:
        record = json.loads(raw_line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    stamp, message = record.get("__REALTIME_TIMESTAMP"), record.get("MESSAGE")
    if not isinstance(stamp, str) or not isinstance(message, str):
        return None
    return stamp, message


def read_at_both_declarations() -> tuple[list[tuple[str, str, str]], str]:
    """The same journal records read twice, paired by record identity.

    Returns ``(paired, problem)``, each pair being the record's own
    ``MESSAGE`` and the two reads' ``message`` fields.

    Two reads a moment apart are two journalctl invocations and need not
    return the same set — a line arrives, the newest ``-n`` window slides
    — so "the same record" needs a key, and :func:`record_identity`
    carries both the key and why it is not the obvious one.

    The population is decided from that verbatim ``MESSAGE`` rather than
    from either read's output, so what counts as an envelope does not
    depend on the declaration being tested.
    """
    from sysadmin.monitor.journal import read_journal

    async def both() -> tuple[list[dict], list[dict]]:
        reads = []
        for declaration in (UNWRAP_BEFORE, UNWRAP_AFTER):
            read = await read_journal(
                UNWRAP_UNIT,
                since=UNWRAP_PROBE_SINCE,
                severity_filter=UNWRAP_PROBE_SEVERITY,
                user=False,
                limit=UNWRAP_PROBE_LIMIT,
                log_format=declaration,
            )
            reads.append(read.entries)
        return reads[0], reads[1]

    try:
        before, after = asyncio.run(both())
    except Exception as exc:  # noqa: BLE001 — a read that would not run is "unknown"
        return [], f"the journal read did not complete ({exc.__class__.__name__})"

    # ``read_journal`` returns no entries both when journalctl is missing
    # and when the window is empty, so the two are not distinguishable
    # here and the note says so rather than picking one.
    if not before or not after:
        return [], (
            f"reading {UNWRAP_UNIT} returned {len(before)} records declared "
            f"{UNWRAP_BEFORE} and {len(after)} declared {UNWRAP_AFTER} — either "
            "journalctl did not answer or the window held nothing"
        )

    shaped: dict[tuple[str, str], str] = {}
    for entry in after:
        identity = record_identity(str(entry["raw_line"]))
        if identity is not None:
            shaped[identity] = str(entry["message"])

    paired: list[tuple[str, str, str]] = []
    for entry in before:
        identity = record_identity(str(entry["raw_line"]))
        if identity is None or identity not in shaped:
            continue
        inner = envelope_message(identity[1])
        if inner is None:
            continue
        paired.append((inner, str(entry["message"]), shaped[identity]))
    if not paired:
        return [], (
            f"none of the {len(before)} records read is a JSON envelope both reads "
            "returned — the probe measured nothing about the declaration"
        )
    return paired, ""


def check_unwrap_is_read_time() -> Measurement:
    """``SNAG-LOG-008`` — a stored row's shape was fixed when it was read.

    **Reproduced rather than counted, and the entry is the clearest case
    for rule 1 this registry has had.**  Its population is ten stored rows
    ingested inside one ten-minute window on 2026-08-17; the endpoint that
    surfaces them computes over seven days, so they left it on 2026-08-24
    with nothing fixed and the retention purge takes the rows themselves
    at thirty.  A check that counted them would report the entry refuted
    by the calendar — ``SNAG-LOG-013``'s reading, refused twice already.

    What the entry claims is a mechanism in two halves, and both are
    measured because a fix can only land in the second:

    1. **The shape is decided at read time**, by the declaration the
       caller passes.  Reproduced by reading this daemon's own journal
       twice in one process, minutes apart, at the two declarations that
       bracket the Session 64 deploy — so a row's ``message`` was settled
       by what ``services.yaml`` said at the moment it was ingested, and
       no later read revisits it.
    2. **Nothing re-derives a stored row's message.**  The unwrap has
       exactly one production call site and it is inside ``read_journal``.
       That is where the entry's *"no read will ever unwrap them"* is
       falsifiable: a backfill migration, or a serve-time unwrap in a
       query path, is a second caller, and this is the only half of the
       mechanism a fix can move.

    Half 1 alone could never refute the entry — it reproduces the cause,
    not the remedy — so a check built from the reproduction alone would
    be one that can only ever say ``match``, which is the shape rule 2
    exists to keep out of this registry.
    """
    # The call-site half is settled first and on purpose.  It needs no
    # subprocess, so a box where journalctl will not answer still reports
    # a landed backfill rather than an ``unknown`` that hides one — and
    # the reproduction below is two 30-second reads not worth spending
    # once the answer is known.
    sites = call_sites(UNWRAP_FUNCTION, UNWRAP_BACKFILL_ROOTS)
    site_detail = tuple(
        f"{UNWRAP_FUNCTION} called at {where} in {enclosing}()" for where, enclosing in sites
    )

    if not sites:
        return Measurement(
            "unknown",
            f"nothing under {', '.join(_rel(root) for root in UNWRAP_BACKFILL_ROOTS)} "
            f"calls {UNWRAP_FUNCTION} at all — it has been renamed or inlined, and this "
            "check no longer measures what it claims to",
        )

    elsewhere = [site for site in sites if site[1] != UNWRAP_READER]
    if elsewhere:
        return Measurement(
            "mismatch",
            f"{UNWRAP_FUNCTION} is called outside {UNWRAP_READER}() — "
            f"{', '.join(f'{where} in {enclosing}()' for where, enclosing in elsewhere)} — "
            "which is where a backfill or a serve-time unwrap lands, so the entry's "
            "'no read will ever unwrap them' has a candidate answer",
            site_detail,
        )

    paired, problem = read_at_both_declarations()
    if problem:
        return Measurement("unknown", problem, site_detail)

    divergent = [pair for pair in paired if pair[1] != pair[2]]
    detail = (
        f"{len(paired)} JSON-enveloped records read at both declarations, "
        f"{len(divergent)} shaped differently by the declaration alone",
        *site_detail,
    )
    if not divergent:
        return Measurement(
            "mismatch",
            f"every record read came back identical under {UNWRAP_BEFORE} and "
            f"{UNWRAP_AFTER} — the reader no longer shapes a record by the source's "
            "declaration, so what a stored row holds was not settled by the "
            "declaration in force when it was ingested",
            detail,
        )
    if len(divergent) < len(paired):
        return Measurement(
            "unknown",
            f"{len(divergent)} of {len(paired)} enveloped records were shaped by the "
            "declaration and the rest were not — the probe is reading a mixture and no "
            "longer isolates the question",
            detail,
        )
    specimen = divergent[0]
    return Measurement(
        "match",
        "",
        (
            *detail,
            f"specimen: declared {UNWRAP_BEFORE} it reads {specimen[1][:90]!r}",
            f"specimen: declared {UNWRAP_AFTER} it reads {specimen[2][:90]!r}",
        ),
    )


# ---------------------------------------------------------------------------
# SNAG-LOG-012 — the model's code spans reach the briefing verbatim
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarkdownForm:
    """One markdown form the entry drove, and what it says becomes of it.

    Attributes:
        label: the form, in words, for the note.
        line: the specimen line carrying it.
        token: what makes the form visible in a rendered line.  Present in
            the output means the form survived the strip.
        survives: what ``strip_markdown`` does with it today, as the
            entry's own driven literal records.
    """

    label: str
    line: str
    token: str
    survives: bool


#: The entry's driven literal, spread over the lines a narrative would
#: actually use.  Four **controls** the entry records as removed and two
#: **subjects** it records as kept, because a probe carrying only the
#: subject reports ``match`` against a ``strip_markdown`` that has stopped
#: stripping anything at all — backticks survive an identity function, and
#: reporting that as evidence for the entry would hide a much larger
#: fault.  The controls are what make the surviving backticks mean
#: something.
#:
#: **The doubled fence is not an invented form.**  ``SNAG-DOCS-005``
#: closed on exactly this distinction one module over, on 2026-08-26: the
#: naive ``` `[^`]+` ``` strips the single fence and *leaks* the doubled
#: one, which is why :data:`CODE_SPAN_RE` closes on a run of the same
#: length.  So the two subject lines are the two candidate fixes told
#: apart — the residue this repository has already paid to learn about,
#: pre-staged against a library that has not met it yet.
STRIPPER_FORMS: tuple[MarkdownForm, ...] = (
    MarkdownForm("an ATX heading", "### Overnight log review", "###", False),
    MarkdownForm("a bullet", "- Nothing else moved overnight.", "- ", False),
    MarkdownForm("an ordered item", "1. The daemon restarted once.", "1. ", False),
    MarkdownForm("bold emphasis", "The run wrote **eight** alert lines.", "**", False),
    MarkdownForm(
        "an inline code span",
        "The `sysadmin.service` unit was the loudest source.",
        "`",
        True,
    ),
    MarkdownForm(
        "a doubled code fence",
        "Its sibling ``estate-broker-provision.service`` failed once.",
        "`",
        True,
    ),
)

#: One narrative, built from the forms rather than written beside them —
#: a specimen and a list of what is in it are two statements of one fact.
STRIP_SPECIMEN = "\n".join(form.line for form in STRIPPER_FORMS)

#: Where the consequence lands.  The entry says "**Both** consumers here"
#: and names two; there are **three** — :mod:`sysadmin.monitor.health_review`
#: was written on 2026-08-25, the day *after* the entry was filed, and
#: calls the same function into the same briefing.  Re-measured on every
#: run rather than written down, because that is how the two became three.
#:
#: **This module is excluded and only a live run said it had to be.**  The
#: first drive reported *five* callers, two of them this check's own probe
#: — so the count was inflated by the instrument, and worse, the "nothing
#: calls it" limb could never have fired, because the check calls it.  A
#: probe counting itself as a consumer is the same shape as a pin
#: searching a region containing its own marker (:mod:`sysadmin.ops_claims`
#: rule 3), reached from the other side.
STRIPPER_NAME = "strip_markdown"
STRIPPER_CONSUMER_ROOT = REPO_ROOT / "sysadmin"
STRIPPER_PROBE = "sysadmin/snag_claims.py"


def stripper_implementation() -> str | None:
    """The file the ``strip_markdown`` this repository's callers reach lives in.

    ``sysadmin/core/text.py`` re-exports ``estate.text``; the two names
    are the same function object, so driving the re-export measures the
    **producer** while still being the object the three reviews call.
    That is the property the whole check rests on, so it is measured and
    not assumed — :func:`check_estate_port_8500` refuses in writing to
    measure a delegated claim at this repository's consumer, and a copy
    landing in ``core/text.py`` is precisely how this check would quietly
    start doing that.
    """
    try:
        return inspect.getsourcefile(strip_markdown)
    except TypeError:  # pragma: no cover — a builtin rebound over the name
        return None


def strip_forms() -> tuple[dict[str, str], str]:
    """Each form's specimen line as the strip leaves it, keyed by label.

    ``strip_markdown`` transforms a narrative line by line and joins, so
    input line *i* pairs with output line *i*.  That pairing is the whole
    instrument and it is checked rather than trusted: a fix that reflowed
    or dropped a line would keep every token in the blob while making
    "which form moved" unanswerable, and a probe that cannot say which
    form moved must say so rather than average over them.

    The **line** is returned rather than a survived/not verdict, so the
    caller's evidence and the caller's judgement are read off one value.
    Two lists — what survived, and what it now reads as — is the
    ``SNAG-DB-003`` shape at the size of a return type.
    """
    lines = strip_markdown(STRIP_SPECIMEN).split("\n")
    if len(lines) != len(STRIPPER_FORMS):
        return {}, (
            f"the strip returned {len(lines)} lines for a {len(STRIPPER_FORMS)}-line "
            "narrative — it no longer maps a line to a line, so which form moved "
            "cannot be read off the output"
        )
    return {form.label: line for form, line in zip(STRIPPER_FORMS, lines, strict=True)}, ""


def check_code_spans_survive() -> Measurement:
    """``SNAG-LOG-012`` — inline code spans reach the briefing verbatim.

    **The first check in this registry that is pre-staged against another
    repository's fix rather than a read of their tree.**  The tenth and
    eleventh shell into estate-manager's venv to drive their code; this
    one needs no cross-repo access at all, because ``estate-lib`` is an
    *editable* install here — ``strip_markdown`` resolves to a file in
    their working tree, so the day they land the fix this check flips to
    ``mismatch`` on the next run with nothing synced and nothing told.
    That is measured rather than assumed: the resolved path is in the
    detail, and a re-pin to a wheel would show up there as a path this
    repository would then lag behind.

    It also refutes, in passing, a rule this document states about
    itself.  The note under ``SNAG-ESTATE-014`` gives *"delegated… so a
    check would be a cross-repo read of a thing that repository is
    already fixing"* as the reason five entries carry none, and
    ``SNAG-LOG-012`` is one of the five it names.  Session 88 broke that
    once with :func:`check_nudge_wording_unpublished`, which was still a
    cross-repo read; this breaks it the other way, and more cheaply —
    being delegated is what makes a check *worth* writing, because the
    closing move happens in a tree nothing here watches, and it need not
    cost a cross-repo read to notice.

    Three limbs, and the order is *is this still the right subject* before
    *does the claim hold* — the thirteenth check's ordering for its
    reason, with the halves a fix can move settled last:

    1. **Whose implementation is this.**  Outside this repository, or the
       entry's "not ours to fix" has moved and the check has started
       measuring a consumer.  ``mismatch``, not ``unknown``: a copy
       landing here is a measurement and not a failure to measure, and
       the note names *which* limb moved so the judging sitting is not
       told the behaviour changed when it did not.
    2. **Does the consequence still have a path.**  Nothing in
       ``sysadmin/`` calling it means no narrative is stripped at all,
       which is a different and larger fault wearing this entry's
       symptom.
    3. **Do the code spans survive**, against controls.  The reading this
       refuses is the obvious one — ``"`" in strip_markdown("a `x`")`` is
       ``True`` for a function that strips *nothing*, so the four control
       forms are what make the surviving backticks evidence rather than
       coincidence.  A control that survives is ``unknown``: the probe
       has stopped isolating the question, which is rule 5.

    A **partial** fix is ``mismatch`` with the residue named, the eleventh
    check's treatment.  Here the residue has a name already: the single
    fence stripped and the doubled one left is the naive pattern
    ``SNAG-DOCS-005`` rejected in this very module a day before this was
    written, so the note can say which fix landed rather than only that
    one did.
    """
    where = stripper_implementation()
    if where is None:
        return Measurement(
            "unknown",
            f"the source file of {STRIPPER_NAME} cannot be resolved, so this cannot say "
            "whose implementation the reviews are calling",
        )
    resolved = Path(where).resolve()
    if resolved.is_relative_to(REPO_ROOT):
        return Measurement(
            "mismatch",
            f"{STRIPPER_NAME} is implemented at {_rel(resolved)}, inside this repository — "
            "the entry's 'it is not this repository's to fix' has moved, and the copy that "
            "moved it is the drift estate-manager ADR-0006 exists to prevent. The behaviour "
            "limb is untouched and unmeasured: this is the delegation limb alone",
        )

    consumers = [
        site
        for site in call_sites(STRIPPER_NAME, (STRIPPER_CONSUMER_ROOT,))
        if not site[0].startswith(STRIPPER_PROBE)
    ]
    evidence = (
        f"{STRIPPER_NAME} is implemented at {resolved}",
        f"{len(consumers)} caller(s) under {_rel(STRIPPER_CONSUMER_ROOT)}: "
        + ", ".join(f"{site} in {enclosing}()" for site, enclosing in consumers),
    )
    if not consumers:
        return Measurement(
            "unknown",
            f"nothing under {_rel(STRIPPER_CONSUMER_ROOT)} calls {STRIPPER_NAME} — no "
            "narrative is stripped at all here, so what it leaves behind no longer "
            "decides what reaches a briefing",
            evidence[:1],
        )

    left, problem = strip_forms()
    if problem:
        return Measurement("unknown", problem, evidence)

    survived = {form.label: form.token in left[form.label] for form in STRIPPER_FORMS}
    kept_controls = [
        form.label for form in STRIPPER_FORMS if not form.survives and survived[form.label]
    ]
    if kept_controls:
        return Measurement(
            "unknown",
            f"{', '.join(kept_controls)} survived the strip — the controls are what make a "
            "surviving backtick mean something, and a stripper that leaves them is not the "
            "one the entry measured, so this no longer isolates the question",
            evidence,
        )

    subjects = [form for form in STRIPPER_FORMS if form.survives]
    gone = [form.label for form in subjects if not survived[form.label]]
    kept = [form.label for form in subjects if survived[form.label]]
    specimen = (
        *evidence,
        *(f"{form.label}: {form.line!r} -> {left[form.label]!r}" for form in subjects),
    )
    if not gone:
        return Measurement("match", "", specimen)
    if kept:
        return Measurement(
            "mismatch",
            f"the strip no longer leaves {', '.join(gone)} and still leaves "
            f"{', '.join(kept)} — a partial fix, and the residue has a name: stripping "
            "the single fence and leaking the doubled one is the naive pattern "
            "SNAG-DOCS-005 rejected in this module, so the library took the fix this "
            "repository already refused",
            specimen,
        )
    return Measurement(
        "mismatch",
        f"the strip no longer leaves {', '.join(gone)} — the library has landed the fix "
        "this entry recommends and the code spans no longer reach a briefing verbatim",
        specimen,
    )


#: The producer stamp ``SNAG-ESTATE-013`` quotes, verbatim from its own
#: body — ``started_at: "2026-08-25T03:32:17.538288+00:00"``.  The entry's
#: specimen rather than an invented one, because the defect is a *copy*: a
#: human reads an estate surface, takes the wall clock out of it and
#: writes that into the marker.  Both stamps this check drives are
#: rendered from this one value, so the naive form and the aware form
#: cannot come to name two different instants the way two typed literals
#: would.
EXPIRY_PRODUCER_STAMP = "2026-08-25T03:32:17.538288+00:00"

#: How the block has rendered every ``expires`` instant it has ever
#: written: a wall clock with no offset.  **Owned here rather than
#: imported from :mod:`sysadmin.ops_claims`, and only a falsification said
#: it had to be.**  The first draft rendered the naive stamp with that
#: module's ``EXPIRY_FORMAT``; driven against a fix that moves it to
#: ``%Y-%m-%dT%H:%M%z``, the "naive" drive silently starts rendering an
#: *offset-bearing* stamp and the probe's own control moves with the thing
#: it is controlling for — so the landed fix comes back looking like no
#: fix at all.  This is a fact about what the *document* wrote, which is
#: not the same fact as what the module accepts, and keeping them apart is
#: what lets the two be compared.  The module's constant is still read,
#: for the evidence line: a change to it is the offset half arriving and
#: should be visible rather than inferred from four drives.
EXPIRY_NAIVE_FORMAT = "%Y-%m-%dT%H:%M"

#: What the marker says it is about, after the instant.  ``check_expiry``
#: splits the argument once, so this is the label that reaches the
#: report's subject line.
EXPIRY_SUBJECT = "the estate scan row clears"

#: A block carrying one prediction, in the shape ``STATUS.md``'s
#: sub-session blockquote actually writes them.
#:
#: **It names both wall clocks on purpose, and that is not padding.**
#: Rule 9 of :mod:`sysadmin.ops_claims` pins the marker's instant against
#: the prose beside it, and a fix that taught the marker an offset would
#: have to choose which clock to render back out — ``03:32`` if it keeps
#: rendering UTC, ``04:32`` if it renders local.  The pin is not the thing
#: being measured here, so the region satisfies it in advance for *both*
#: readings; otherwise a landed fix would come back as a pin failure and
#: this check would report the wrong limb moved.
EXPIRY_REGION = (
    "> **The estate scan row is the one thing outstanding.**\n"
    "> {marker} The producer's stored scan started at 03:32 today, so the\n"
    "> row clears with nothing done; the timer itself fired at 04:32.\n"
)


@dataclass(frozen=True)
class ExpiryReading:
    """What :func:`sysadmin.ops_claims.check_expiry` made of one marker.

    Attributes:
        label: which drive this is, for the note.
        argument: the marker argument, as the block would carry it.
        now: the wall clock the module was asked to judge it against.
        verdict: what it returned.
        measured: what it says of the prediction, or ``None`` when it got
            no instant out of the marker at all.
        note: its sentence, empty on a standing prediction.
    """

    label: str
    argument: str
    now: str
    verdict: str
    measured: str | None
    note: str
    aware_clock: bool = False

    @property
    def parsed(self) -> bool:
        """Whether an instant came out of the marker.

        **Deliberately not the verdict**, and that distinction is the
        entry's own title read as an instruction to its checker.  A naive
        stamp read an hour early and an aware stamp the module cannot
        parse at all are *both* ``unknown``, so both print ``??`` and the
        report cannot tell a mis-timed prediction from a rejected marker.
        ``measured`` is the field that separates them: the timing paths
        fill it and :func:`sysadmin.ops_claims._convention` leaves it
        ``None``.
        """
        return self.measured is not None

    def line(self) -> str:
        """One evidence row."""
        clock = " (aware clock)" if self.aware_clock else ""
        return (
            f"{self.label}: <!--check:expires {self.argument} …--> at {self.now}{clock} "
            f"-> {self.verdict}, {self.measured or self.note}"
        )


def expiry_reading(label: str, argument: str, now: datetime) -> tuple[ExpiryReading | None, str]:
    """Drive one marker through the real reader and the real timer.

    ``read_markers`` first rather than handing :func:`check_expiry` a
    :class:`~sysadmin.ops_claims.Marker` built here — the argument is the
    part of the convention this entry is about, and a check that
    constructed the parsed form would be measuring its own split rather
    than the module's.  It also keeps the offset-bearing form honest:
    ``MARKER_RE``'s argument group stops at ``>``, and ``+00:00`` survives
    that today, which is a fact about the reader and not one to assume.

    **The naive clock is retried aware, and that retry is what keeps this
    probe alive through the fix it watches for.**  The entry's proposed
    remedy has two halves and the natural way to land them is together:
    teach the marker an offset, and make ``now`` an aware instant so the
    two can be subtracted.  A probe that passed only a naive ``now`` would
    then hit ``TypeError`` on the *offset-bearing* drive — the one drive
    that had just started working — and report the fix as a crash.  So a
    refusal of the naive clock is recorded and the drive is repeated,
    which turns the module's own fail-closed step into evidence instead of
    a dead end.  :func:`check_code_spans_survive`'s pre-staging, arrived at
    from the other side: there the fix lands in a tree nothing here
    watches, here it lands in the function being called.
    """
    region = EXPIRY_REGION.format(
        marker=f"<!--check:expires {argument} {EXPIRY_SUBJECT}-->"
    )
    markers = [marker for marker in read_markers(region) if marker.key == "expires"]
    if not markers:
        return None, (
            f"the {label} marker '{argument}' is not read as an expires marker at all — "
            "ops_claims.read_markers no longer sees the form the block writes"
        )
    aware_clock = False
    try:
        claim = check_expiry(markers[0], region, now)
    except TypeError:
        aware_clock = True
        try:
            claim = check_expiry(markers[0], region, now.astimezone())
        except Exception as exc:  # noqa: BLE001 — a drive that will not run is not a verdict
            return None, (
                f"check_expiry refused the {label} drive at both a naive and an aware clock "
                f"({exc.__class__.__name__}: {exc}) — it no longer judges a prediction the "
                "way this entry describes, and this probe can no longer reach it"
            )
    except ValueError as exc:
        return None, (
            f"check_expiry raised on the {label} drive ({exc.__class__.__name__}: {exc}) — "
            "a malformed instant is reported rather than raised today, so the parse has "
            "stopped failing the way rule 8 requires"
        )
    return (
        ExpiryReading(
            label, argument, now.strftime("%Y-%m-%d %H:%M:%S"),
            claim.verdict, claim.measured, claim.note, aware_clock,
        ),
        "",
    )


def check_expiry_naive_instant() -> Measurement:
    """``SNAG-ESTATE-013`` — an ``expires`` marker takes a zoneless instant.

    **The fifteenth check, and the first whose subject is this
    repository's own claims machinery.**  Every other entry in this
    registry is measured against the box, against another repository's
    tree, or against a domain module; this one drives
    :mod:`sysadmin.ops_claims`, the sibling composition root that reads
    ``STATUS.md`` at both ends of a sitting.  It needs no database, no
    subprocess and no cross-repo read — which is why it was written before
    the entries that need all three.

    The module is **imported and driven**, never reimplemented.  Rule 7's
    second half, and here it is not a preference: the claim *is* what
    ``check_expiry`` does with a marker, so a copy of the parse would
    measure the copy.  Same argument :func:`check_code_spans_survive`
    makes for resolving ``strip_markdown`` through the re-export rather
    than pinning a literal.

    **The population is empty and the mechanism is built.**  ``STATUS.md``
    carries no live ``expires`` marker today — the one that ever existed
    is the block that opened this entry, since reworded.  Rule 1 forbids
    reading that as health, so the check writes a block in the shape the
    sub-session blockquote uses, the way
    :func:`check_dropin_blind_spot` builds the drop-in it needs.

    **The instrument is a pair of straddles, and the obvious single one is
    wrong in half the world.**  Written first as *"judged a minute before
    the event, does it already say expired"* — which is the defect as
    ``SNAG-ESTATE-013`` observed it here, and it holds only east of
    Greenwich.  Driven at ``America/New_York`` the same marker names an
    instant four hours *after* its subject, so the prediction **outlives**
    what it predicted and the early-expiry test reports the module
    correct.  That is ``SNAG-LOG-009``'s own asymmetry — *"the rule is N
    hours late at UTC−N"* — arriving one document over, and it was found
    by running the probe in three zones rather than by reasoning about it.

    So what is measured is the **displacement of the boundary**, whose
    sign the offset decides and whose existence it does not:

    * ``at the marker`` — one minute either side of the instant the
      marker's own text names, read as local.
    * ``at the event`` — one minute either side of the instant the
      producer actually stamped.
    * ``at the event`` itself — the error in the module's own words
      rather than in this check's.
    * ``aware`` — the stamp the entry's proposed fix would write,
      ``+00:00`` and all.  Not understood today, and not understood as a
      *malformed marker* rather than as an unsupported one.

    **The magnitude is this box's UTC offset, so a box at zero cannot
    demonstrate the fault and must say so.**  At UTC+00:00 the two stamps
    name one instant, both straddles collapse onto the same pair of wall
    clocks, and a zone-blind reading is indistinguishable from a correct
    one — a false refutation of a mechanism that is still there.
    ``unknown``, ``ports_checked``'s rule: zero-because-blind is never
    served as zero-because-clean.

    **Which straddle the timer flips across is the whole verdict, and
    neither straddle is a control for the other.**  The first draft made
    the marker pair a control — *must give to run then passed, or the
    probe has stopped isolating the question* — and a stand-in modelling
    the fix refuted that too: a timer that read the zoneless stamp as the
    moment it was **stamped** moves its boundary onto the event, fails the
    control, and comes back ``unknown`` when it should come back
    ``mismatch``.  A control that a landed fix breaks is not a control, it
    is the unfixed behaviour asserted twice.  So the boundary is
    *located* rather than assumed: flipping at the producer's instant is
    the defect gone by a route neither half of the entry's fix names,
    flipping at the marker's text is the defect standing, and flipping at
    neither is the only reading this probe declines.

    Either half of the entry's proposed fix refutes it, and the note names
    which landed, because they can land apart: teaching the marker an
    offset makes the ``aware`` drive parse, and refusing a zoneless
    instant makes the rest stop parsing.  A partial fix is ``mismatch``
    with the residue named — the eleventh check's treatment, and the
    fourteenth's.
    """
    producer = datetime.fromisoformat(EXPIRY_PRODUCER_STAMP)
    here = producer.astimezone()
    offset = here.utcoffset() or timedelta(0)
    naive_arg = producer.strftime(EXPIRY_NAIVE_FORMAT)
    aware_arg = producer.isoformat(timespec="minutes")
    # Where the module puts the boundary, and where the event actually is.
    read_as_local = producer.replace(tzinfo=None, second=0, microsecond=0)
    true_local = here.replace(tzinfo=None)
    minute = timedelta(minutes=1)

    zone = (
        f"this box is {here.tzname()} (UTC{here:%z}) at the producer's stamp; "
        f"{EXPIRY_PRODUCER_STAMP} is {true_local:%m-%d %H:%M:%S} here, the marker says "
        f"{read_as_local:%m-%d %H:%M}, and ops_claims accepts {EXPIRY_FORMAT!r}"
    )
    if not offset:
        return Measurement(
            "unknown",
            "this box is at UTC+00:00, so a zoneless instant and an offset-bearing one "
            "name the same moment here and the two stamps cannot be told apart — the "
            "mechanism is untouched and this probe cannot demonstrate it",
            (zone,),
        )

    drives = (
        ("before the marker", naive_arg, read_as_local - minute),
        ("after the marker", naive_arg, read_as_local + minute),
        ("before the event", naive_arg, true_local - minute),
        ("after the event", naive_arg, true_local + minute),
        ("at the event", naive_arg, true_local),
        ("aware", aware_arg, true_local),
    )
    readings: list[ExpiryReading] = []
    for label, argument, now in drives:
        reading, problem = expiry_reading(label, argument, now)
        if reading is None:
            return Measurement("mismatch", problem, (zone, *(r.line() for r in readings)))
        readings.append(reading)

    by_label = {reading.label: reading for reading in readings}
    at_event, aware = by_label["at the event"], by_label["aware"]
    evidence = (zone, *(reading.line() for reading in readings))

    moved = []
    if aware.parsed:
        moved.append(
            f"an offset-bearing instant now parses ({aware.measured}) — the marker has "
            "learned a zone, which is the first half of the entry's proposed fix"
        )
    if not at_event.parsed:
        moved.append(
            "a zoneless instant is no longer read as a moment — the parse fails closed, "
            "which is the second half of the entry's proposed fix"
        )
    elif any(reading.aware_clock for reading in readings):
        moved.append(
            "a zoneless instant still parses, and the module now refuses to judge one "
            "against a naive wall clock — half of the fail-closed half, and the residue "
            "is that the marker itself may still be written without an offset"
        )
    if moved:
        return Measurement("mismatch", "; ".join(moved), evidence)

    def flips_at(pair: str) -> bool:
        """Whether the timer changes its answer across this straddle."""
        return (
            by_label[f"before the {pair}"].verdict == "match"
            and by_label[f"after the {pair}"].verdict != "match"
        )

    at_marker, at_producer = flips_at("marker"), flips_at("event")
    if at_producer:
        return Measurement(
            "mismatch",
            "the boundary straddles the producer's instant rather than the marker's own "
            "text — the timer reads the zoneless stamp as the moment it was stamped, and "
            "the entry's defect is gone by a route neither half of its fix names",
            evidence,
        )
    if not at_marker:
        return Measurement(
            "unknown",
            "the timer flips at neither straddle "
            f"(before/after the marker: {by_label['before the marker'].verdict}/"
            f"{by_label['after the marker'].verdict}) — its boundary cannot be located, so "
            "where the producer's instant falls relative to it says nothing and this probe "
            "has stopped isolating the question",
            evidence,
        )

    early = offset > timedelta(0)
    displacement = humanise_hours(abs(offset.total_seconds()) / 3600)
    direction = (
        f"expires {displacement} before its subject occurs"
        if early
        else f"outlives its subject by {displacement}"
    )
    return Measurement(
        "match",
        "",
        (
            *evidence,
            f"the prediction {direction} — the boundary sits at the marker's text read as "
            f"local, {displacement} from the instant the producer stamped",
            "both readings report `unknown`, so the report prints ?? whether the "
            "prediction was mis-timed or the marker could not be parsed at all",
        ),
    )

# ---------------------------------------------------------------------------
# SNAG-UNITS-003 — the emitted health path is a guess, not an observation
# ---------------------------------------------------------------------------

#: The synthetic unit the snippet generator is driven at.  A name no unit
#: on this box carries and a path that does not exist: nothing is swept,
#: read or written, because the ranker takes a finding rather than a
#: directory.  :func:`check_dropin_blind_spot` has to build a unit tree
#: because the sweep is what it measures; here the sweep's *output* is
#: the input, so the tree would be scenery.
HEALTH_PROBE_UNIT = "snagcheck-health.service"
HEALTH_PROBE_SCOPE = "user"

#: Where a probe may send a request.  The population below is filtered to
#: entries carrying a port **and** a unit, which already excludes the one
#: off-box url in ``services.yaml`` — ``internet``, which declares
#: neither — so this guard is not what keeps today's run local.  It is
#: what keeps it local on the day somebody adds a remote entry that does
#: carry both.  A check that runs at the start and the close of every
#: sitting must not be *able* to reach off this machine, and "it happens
#: not to today" is not that guarantee.
LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

#: ``    url: <url>   # comment`` in a generated services.yaml entry.
#: ``\S+`` stops at the whitespace before the trailing comment, which is
#: the shape the generator emits and the only shape this reads.
SNIPPET_URL_RE = re.compile(r"(?m)^\s*url:\s*(\S+)")


@dataclass(frozen=True)
class PathProbe:
    """One declared service, and what answered on its port.

    ``emitted`` is the url the unit sweep's advice would have a reader
    paste for this port; ``declared`` is the url ``services.yaml``
    already carries.  Both are read through the **same** production
    check, so the pair is a comparison rather than two measurements
    taken different ways — the difference between them is the only thing
    this check draws a conclusion from.
    """

    name: str
    port: int
    emitted: str
    emitted_well: bool
    emitted_status: str
    declared: str | None
    declared_well: bool
    declared_status: str
    problem: str = ""

    @property
    def measured(self) -> bool:
        """Did something answer at the url this service's own entry declares?

        The control.  A guess that does not answer says nothing about
        the *path* when nothing answers on that port at all, so a
        service that fails its own declared url is evidence about
        neither.
        """
        return not self.problem and bool(self.declared) and self.declared_well

    @property
    def guess_right(self) -> bool:
        return self.measured and self.emitted_well

    @property
    def guess_wrong(self) -> bool:
        return self.measured and not self.emitted_well

    @property
    def declared_path(self) -> str:
        return urlsplit(self.declared).path if self.declared else ""

    @property
    def is_witness(self) -> bool:
        """A port at which a generator that *looked* could not have emitted this.

        The emitted path does not answer here and the service's own
        declared path does — so an implementation that probed before
        emitting had somewhere else to go and did not take it.  Without
        at least one of these, a constant emitted path is
        indistinguishable from an implementation that probed, found
        nothing, and fell back to the same default: the two frontends that
        declare no path at all are exactly that case, which is why they
        are excluded from the witnesses while still counting in the
        population.
        """
        return self.guess_wrong and bool(self.declared_path.strip("/"))

    @property
    def reading(self) -> str:
        declared = _render_path(self.declared_path)
        return (
            f"{self.name}:{self.port} declares {declared} ({self.declared_status}); "
            f"the emitted url reads {self.emitted_status}"
        )


def _render_path(path: str) -> str:
    """A url path as a reader can see it.

    An empty path is a real answer and two services here declare one —
    the entry counts them as *"both frontends with no path at all"*.
    Joined into a list it renders as nothing, so a note saying four
    paths names three and the reader is left to notice the gap.
    ``SNAG-BRIEF-002``'s rule at the size of a list separator.
    """
    return path or "(no path)"


def health_path_population() -> tuple[list[ServiceEntry], str]:
    """The ``services.yaml`` entries ``SNAG-UNITS-003`` counted.

    "Declaring a port and a unit", in the entry's own words, and read
    off the file rather than restated: the entry's **11** appears
    nowhere in this module, because a constant here would be a second
    statement of the document's own sentence and free to agree with the
    box while the entry disagrees with both.
    :mod:`sysadmin.ops_claims`' rule 7, one document over.
    """
    from sysadmin.monitor.services import default_services_path, load_services

    try:
        services = load_services(default_services_path())
    except Exception as exc:  # noqa: BLE001 — an unreadable services.yaml is "unknown"
        return [], f"services.yaml would not load ({exc.__class__.__name__}: {exc})"
    return [
        entry
        for entry in services.services
        if entry.port is not None and entry.unit is not None
    ], ""


def generated_health_url(port: int) -> str | None:
    """The url the sweep's advice would have a reader paste for ``port``.

    Driven through the **public** :func:`recommendations_for_scan`
    rather than the private ``_services_yaml_snippet`` it ends in.  The
    entry's own candidate fix is *"probe once when the snippet is
    generated"*, and "when it is generated" is a moment on that whole
    path — a probe in the caller, passing the answering path down, fixes
    the entry and leaves the innermost function emitting the same
    literal.  A check bound to that function would report such a fix as
    no change at all, which is
    ``a-control-a-fix-breaks-is-not-a-control`` met from its other side.
    """
    from sysadmin.units.recommendations import recommendations_for_scan
    from sysadmin.units.scan import UNMONITORED, UnitFinding

    finding = UnitFinding(
        unit=HEALTH_PROBE_UNIT,
        scope=HEALTH_PROBE_SCOPE,
        category=UNMONITORED,
        path=f"/nonexistent/{HEALTH_PROBE_UNIT}",
        description="health path probe",
        monitor_unit=HEALTH_PROBE_UNIT,
        enabled=True,
    )
    blob = {
        "unit_audited_ports": {f"{HEALTH_PROBE_SCOPE}:{HEALTH_PROBE_UNIT}": [port]}
    }
    for recommendation in recommendations_for_scan([finding], None, blob):
        match = SNIPPET_URL_RE.search(recommendation.snippet or "")
        if match:
            return match.group(1)
    return None


def _loopback(url: str) -> bool:
    return urlsplit(url).hostname in LOOPBACK_HOSTS


def probe_health_paths(
    population: list[ServiceEntry], emitted: dict[int, str]
) -> tuple[list[PathProbe], str]:
    """Ask each port whether the emitted url and its own declared url answer.

    **The fourth instrument, and what makes it a measurement rather than
    a fetch.**  The three before it are an ``ast`` walk, a driven
    function and another repository's interpreter; this one sends a
    request, and the answer it needs is not a status code but *would a
    monitor pasting this url report the service well* — which is a
    reading :mod:`sysadmin.monitor.agent` already owns.  So the probe
    **is** ``SysAdminAgent._check_http``, under ``_http.scoped()`` as a
    real run does, and its verdict is classified by
    :func:`~sysadmin.monitor.models.service_health.is_fault` off the
    CHECK constraint's own map.  Nothing here compares a status to
    ``"ok"`` by hand: ``SNAG-API-004`` is what that costs, and this is
    the fourth module to be told.

    The one limit worth stating: a 200 that takes over five seconds
    reads as a fault, ``_check_http``'s own rule.  It applies to both
    halves of the pair, so a loaded box makes services *unmeasured*
    rather than *wrong* — the direction that under-reports the entry
    rather than confirming it by accident.
    """
    from sysadmin.monitor.agent import SysAdminAgent
    from sysadmin.monitor.models.service_health import is_fault

    async def drive() -> list[PathProbe]:
        agent = SysAdminAgent()
        probes: list[PathProbe] = []
        async with agent._http.scoped():  # noqa: SLF001 — the production shape, driven
            for entry in population:
                assert entry.port is not None  # the population filter guarantees it
                guess = emitted[entry.port]
                if not _loopback(guess):
                    probes.append(
                        PathProbe(
                            entry.name, entry.port, guess, False, "not-probed",
                            entry.url, False, "not-probed",
                            f"the emitted url {guess} is not on this machine",
                        )
                    )
                    continue
                guess_status, _, _ = await agent._check_http(  # noqa: SLF001
                    entry.model_copy(update={"url": guess})
                )
                if not entry.url or not _loopback(entry.url):
                    probes.append(
                        PathProbe(
                            entry.name, entry.port, guess,
                            not is_fault(guess_status), guess_status,
                            entry.url, False, "not-probed",
                            "declares no url on this machine to compare against",
                        )
                    )
                    continue
                declared_status, _, _ = await agent._check_http(entry)  # noqa: SLF001
                probes.append(
                    PathProbe(
                        entry.name,
                        entry.port,
                        guess,
                        not is_fault(guess_status),
                        guess_status,
                        entry.url,
                        not is_fault(declared_status),
                        declared_status,
                    )
                )
        return probes

    try:
        return asyncio.run(drive()), ""
    except Exception as exc:  # noqa: BLE001 — a probe that would not run is "unknown"
        return [], f"the health probe would not run ({exc.__class__.__name__}: {exc})"


def _named(items: Iterable[str]) -> tuple[str, ...]:
    """Up to :data:`MAX_NAMED_ENTRIES` of them, with the rest counted.

    ``SNAG-ESTATE-001``'s rule, the same overflow
    :func:`check_convention` applies to the unchecked entries.
    """
    listed = list(items)
    named = tuple(listed[:MAX_NAMED_ENTRIES])
    if len(listed) > MAX_NAMED_ENTRIES:
        named = (*named, f"… and {len(listed) - MAX_NAMED_ENTRIES} more")
    return named


def check_health_path_guess() -> Measurement:
    """``SNAG-UNITS-003`` — the generated ``kind: http`` url guesses the path.

    **The entry makes two claims and only one of them is a mechanism,
    which is why both are measured.**  Its body claims that
    ``_services_yaml_snippet`` emits a health path it never fetched; its
    *title* claims that on this box the guess is "wrong more often than
    right", counted at 4 right and 7 wrong of 11 on 2026-08-15 by an
    author whose first draft said "two of twelve".  Rule 1 says a check
    tests the mechanism rather than the population — and here the
    population is the sentence in the title, so it is a claim like any
    other.  The two refute the entry for opposite reasons and the notes
    say which: the generator learning to *look* is the **fix**, while
    the box's services converging on the contract's path is the claim's
    **premise** dying with the generator unchanged.
    :func:`check_sysd_ollama_ordering`'s split, one entry over.

    **The counted figures are re-measured and never restated.**  4, 7
    and 11 appear nowhere here.  What stops the entry's figure
    fossilising is not a constant to compare against but the recount
    printed in ``detail`` at both ends of every sitting — and a drift
    that keeps the *direction* is deliberately **not** a mismatch, or
    adding one service to ``services.yaml`` would send a sitting to
    judge an entry whose substance nothing had touched.

    Four rules, three of them the opposite of the obvious
    implementation:

    1. **The guess is read off the generator, never written down here.**
       The check probes the url the advice would have a human paste, so
       a rename of the default path moves the probe with it instead of
       leaving a check measuring a path nothing emits.  It also settles
       part of the mechanism half with no network at all: a generator
       emitting *different* paths for different ports is observing
       something, whatever those paths are.
    2. **Every probe is paired with a control, and the control is the
       service's own declared url.**  A guess that does not answer says
       nothing about the path when nothing answers on that port — a
       stopped service reports every path wrong, so a check without the
       control would report this entry holding hardest on the morning
       the box came up.  A service failing its own url is *unmeasured*
       and named, never counted as evidence: ``ports_checked``'s rule,
       and the reason "wrong" here is a claim about a path rather than
       about a service.
    3. **A constant path is not by itself evidence that nothing looked,
       so the refutation needs a witness.**  An implementation that
       probed, found nothing answering and fell back to the same default
       emits the same constant — and the two frontends that declare no
       path at all are exactly that case, since no probing
       implementation would emit a bare url either.  A **witness** is a port where the emitted path
       fails and the service's own declared path answers: somewhere else
       to go, not taken.  With no witness the verdict is ``unknown``
       rather than ``match``, which is also how this degrades when the
       box is offline — so the offline behaviour is a case of the rule
       and not a special case bolted onto it.
    4. **The population half is decided on the direction, the mechanism
       half on the paths.**  ``wrong <= right`` refutes the title
       whatever the generator does; a moved path refutes the body
       whatever the box answers.  Reported in that order — a landed fix
       is the larger news — with the recount carried on both.
    """
    population, problem = health_path_population()
    if problem:
        return Measurement("unknown", problem)
    if not population:
        return Measurement(
            "unknown",
            "no services.yaml entry declares both a port and a unit — the population the "
            "entry counted is gone, and this check no longer measures what it claims to",
        )

    emitted: dict[int, str] = {}
    for entry in population:
        assert entry.port is not None  # the population filter guarantees it
        url = generated_health_url(entry.port)
        if url is None:
            return Measurement(
                "unknown",
                f"the sweep's advice emits no kind: http url for a unit holding one port "
                f"({entry.port}) — the snippet's shape has moved, so this check is reading "
                "a different function from the one the entry is about",
            )
        emitted[entry.port] = url

    paths = sorted({urlsplit(url).path for url in emitted.values()})
    port_detail = tuple(f"port {port} → {url}" for port, url in sorted(emitted.items()))
    if len(paths) > 1:
        return Measurement(
            "mismatch",
            f"the advice emits {len(paths)} different health paths across the declared "
            f"ports ({', '.join(_render_path(path) for path in paths)}) — it is deciding "
            "the path per port rather than "
            "emitting the contract's default, which is the fix the entry names",
            _named(port_detail),
        )
    guess = paths[0]
    shown = _render_path(guess)

    probes, problem = probe_health_paths(population, emitted)
    if problem:
        return Measurement("unknown", problem, (f"the advice emits {shown} for every port",))

    right = [probe for probe in probes if probe.guess_right]
    wrong = [probe for probe in probes if probe.guess_wrong]
    unmeasured = [probe for probe in probes if not probe.measured]
    measured = len(right) + len(wrong)
    detail = (
        f"the advice emits {shown} for all {len(population)} ports declared with a unit",
        f"{len(right)} of {measured} measured services answer it, {len(wrong)} do not"
        + (f"; {len(unmeasured)} unmeasured" if unmeasured else ""),
        *_named(probe.reading for probe in wrong),
        *_named(
            f"{probe.name}:{probe.port} unmeasured — {probe.problem or probe.declared_status}"
            for probe in unmeasured
        ),
    )

    if not measured:
        return Measurement(
            "unknown",
            "no service answered the url its own services.yaml entry declares, so nothing "
            f"here can tell a wrong path from a stopped service — {shown} failing "
            "everywhere is evidence about the box, not about the path",
            detail,
        )
    if not wrong:
        return Measurement(
            "mismatch",
            f"{shown} answers on all {measured} services this could measure — the entry's "
            "'wrong more often than right' no longer describes this box, and the guess it "
            "calls a guess is now right everywhere it was checked",
            detail,
        )
    if len(wrong) <= len(right):
        return Measurement(
            "mismatch",
            f"{shown} is right for {len(right)} of {measured} and wrong for {len(wrong)} — "
            "still a guess, but no longer wrong more often than right, which is what the "
            "entry's title claims",
            detail,
        )

    witnesses = [probe for probe in wrong if probe.is_witness]
    witness_ports = sorted(probe.port for probe in witnesses)
    if not witnesses:
        return Measurement(
            "unknown",
            f"{shown} is wrong for {len(wrong)} of {measured}, but every one of them "
            "declares a bare path of its own — so an implementation that probed, found "
            "nothing and fell back to the default would emit exactly what this one does, "
            "and the constant path proves nothing",
            detail,
        )
    return Measurement(
        "match",
        "",
        (
            *detail,
            f"{len(witnesses)} witness port(s) where {shown} fails and the service's own "
            f"path answers: {', '.join(str(port) for port in sorted(witness_ports))}",
        ),
    )


# ---------------------------------------------------------------------------
# Driving the estate judge against the live database
# ---------------------------------------------------------------------------

#: What a probe writes into every alert row it opens by hand.
#:
#: Nothing either probe writes is ever committed, so this is what a row
#: that somehow escaped a rollback would say about where it came from.
#: It names the *script* rather than an entry, so one query finds a
#: leak from either probe — and it is deliberately **not** what the rows
#: a probe *raises* carry, since ``raise_alert`` is handed the
#: judgement's message and those rows come out wearing the estate's own
#: ``summary``.  A guard keyed on this string alone was blind to exactly
#: the rows the probes exist to produce until a committing stand-in
#: leaked one past it.
PROBE_MESSAGE = "sysadmin-check-snags probe row — never committed"


def findings_transport(
    payload: Mapping[str, object],
) -> Callable[[httpx.Request], httpx.Response]:
    """Answer ``audit_findings`` with ``payload``; decline the other four.

    ``503`` rather than an empty payload, because *unread* and
    *read-but-clean* are the two states
    :attr:`~sysadmin.estate.client.SurfaceResult.read` exists to keep
    apart, and only the first keeps the run's sweep away from rows the
    probe did not open.  ``_resolve_gone`` is scoped per surface, so a
    probe that answered all five would resolve every genuinely-open
    estate row inside its own transaction.  Rolled back either way — and
    a probe that can decline the blast should not spend the rollback
    instead.
    """
    import httpx

    from sysadmin.estate.client import SURFACE_PATHS

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == SURFACE_PATHS["audit_findings"]:
            return httpx.Response(200, json=payload)
        return httpx.Response(503, text="not served to the probe")

    return handler


def mounted_judge(
    handler: Callable[[httpx.Request], httpx.Response],
) -> tuple[EstateJudgeAgent | None, str]:
    """The real judge, pointed at ``handler`` rather than at 8400.

    The substitution is made at the **client factory**, so the
    production :func:`~sysadmin.estate.client.pull_all` runs the whole
    way down: path dispatch, ``raise_for_status``, the JSON parse and the
    per-surface ``read`` flag are the ones the box uses.  A probe that
    stubbed ``pull_all`` instead would be measuring its own fixture.

    The :class:`LoopBoundClient` test is a precondition rather than a
    formality.  A judge that had gained a second route to the estate
    would reach the live service from a probe that believes it is
    answering every request itself, and the first thing a reader would
    know about it is a finding raised on somebody else's data.
    """
    import httpx

    from sysadmin.core.async_http import LoopBoundClient
    from sysadmin.estate.agent import EstateJudgeAgent

    agent = EstateJudgeAgent()
    if not isinstance(getattr(agent, "_http", None), LoopBoundClient):
        return None, (
            "EstateJudgeAgent no longer reaches 8400 through a LoopBoundClient, so this "
            "probe cannot answer for it without touching the live estate"
        )
    agent._pending_events = []  # noqa: SLF001 — `run()` sets this; buffer, never publish
    agent._http = LoopBoundClient(  # noqa: SLF001 — the factory `scoped()` calls
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=5.0)
    )
    return agent, ""


def rolled_back_drive[ProbeT](
    work: Callable[[AsyncSession], Awaitable[ProbeT]],
) -> tuple[ProbeT | None, str]:
    """Run ``work(session)`` against the live database, then roll it back.

    Every row either probe writes lands inside this transaction and the
    rollback sits in a ``finally``, so a drive that raised leaks no more
    than one that returned.  That property is what makes writing to the
    live database allowable at all, and it is asserted by tests of its
    own rather than promised in this sentence.

    The run is also **silenced**.  It writes ``alert_raised`` at WARNING
    and one ``estate_surface_unread`` per declined surface, all of which
    are true of the probe and false of the box — and this script prints
    its report to a terminal at both ends of every sitting, where a log
    line announcing an alert on a port nothing is listening to is a
    worse artefact than noise.  The previous level is restored in a
    ``finally`` too; note that a test cannot witness that from inside
    ``caplog.at_level``, which restores it regardless.

    Every failure is ``unknown``: a drive that would not run has
    measured nothing, which is rule 5.
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import NullPool

    config = get_config()

    async def drive() -> ProbeT:
        engine = create_async_engine(
            config.database.url,
            poolclass=NullPool,
            connect_args={
                "server_settings": {"search_path": f"{config.database.schema_},public"}
            },
        )
        try:
            factory = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            async with factory() as session:
                try:
                    return await work(session)
                finally:
                    # Before `engine.dispose()`, and unconditional: a
                    # rollback is the only reason these probes are
                    # allowed to write to the live database at all.
                    await session.rollback()
        finally:
            await engine.dispose()

    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        return asyncio.run(drive()), ""
    except Exception as exc:  # noqa: BLE001 — a drive that would not run is "unknown"
        return None, (
            "the judge would not run against the live database "
            f"({exc.__class__.__name__}: {exc})"
        )
    finally:
        logging.disable(previous)


# ---------------------------------------------------------------------------
# SNAG-ESTATE-010 — a quieter judgement cannot reach a row already open
# ---------------------------------------------------------------------------

#: The two ports the probe has the estate report as breached.
#:
#: Far above the registry's audited range and adjacent to nothing, so
#: neither title can collide with a live row.  The probe *opens* one of
#: them itself, and a collision would have it deduplicate against
#: somebody else's standing fault and read the result as its own.
QUIETEN_OPEN_PORT = 65010
QUIETEN_FRESH_PORT = 65011
QUIETEN_PORTS = (QUIETEN_OPEN_PORT, QUIETEN_FRESH_PORT)

#: The session scope the probe's synthetic sweep attributes both to.
#:
#: Transience is decided by *which map* a holder sits in — ``transient_ports``
#: rather than ``unit_ports``, :func:`~sysadmin.units.ports.attribution_from_blob`'s
#: rule — and never by the name, so the ``.scope`` suffix here is
#: legibility for a reader and not the signal being tested.
QUIETEN_HOLDER = "user:snag-claims-probe.scope"

def quieten_finding(port: int) -> dict[str, object]:
    """One unclaimed-listener breach, in the shape 8400 serves.

    ``check`` and ``severity`` are the constants the *consumer* filters
    on rather than strings typed here: a payload built from literals
    would keep matching a filter that had moved, and the probe would
    report the entry holding while judging nothing at all.
    ``syslog_priority`` against ``journal.PRIORITY_MAP``, one payload
    over.
    """
    from sysadmin.estate.judgements import JUDGED_AUDIT_CHECK, JUDGED_AUDIT_SEVERITY

    return {
        "check": JUDGED_AUDIT_CHECK,
        "severity": JUDGED_AUDIT_SEVERITY,
        "subject": f"port {port}",
        "summary": f"port {port} is listening inside the registry's range",
        "fingerprint": f"ports:port {port}:unclaimed_listener",
        # No ``code`` key, deliberately: the producer computes one and
        # ``AuditFinding`` has no column for it, so it never reaches the
        # wire (SNAG-ESTATE-006). A literal inventing a field the
        # producer drops is what `tests/test_estate_surface_payloads.py`
        # exists to stop, and this payload is held to the same rule.
        "detail": {"port": port},
        "standing_days": 0.0,
        "runs_observed": 1,
        "age_truncated": False,
    }


@dataclass(frozen=True)
class QuietenReading:
    """One judge run over a fault it has already raised, and one it has not.

    Both ports are judged by the **same** ``_execute`` call against the
    same payload and the same attribution, so the pair differs in
    exactly one thing: whether a row was already open under that title.
    Two runs would differ in the clock, in what the sweep said and in
    what else the estate was serving.
    """

    #: What the pure judgement computes for both ports — read off
    #: :func:`~sysadmin.estate.judgements.judge_audit_findings`, never
    #: written down here.
    expected_severity: str
    #: The rung the standing row was opened at, and the one it holds after.
    open_before: str
    open_after: str
    #: ``details['holder']`` on the standing row afterwards.  The two
    #: rows the entry was filed from carry ``null``.
    open_holder: object
    open_resolved: bool
    #: How many rows carry the standing title afterwards.  Two is the
    #: resolve-and-re-raise shape the entry's fourth bullet names.
    open_rows: int
    fresh_severity: str | None
    fresh_holder: object
    fresh_rows: int
    raised: int

    @property
    def witnessed(self) -> bool:
        """Did this run raise the quieter row where nothing stood open?

        The control, and it carries the whole verdict.  A standing row
        that did not move is evidence only if the run genuinely had
        something quieter to move it *to*: a judge that had stopped
        computing ``info``, or a sweep whose attribution no longer
        reached the family, would leave the row exactly as untouched and
        look identical.  ``a-check-needs-a-discriminating-witness``,
        which this registry has now had to apply at every scale from an
        ``ast`` walk to an outbound request.
        """
        return (
            self.fresh_rows == 1
            and self.fresh_severity == self.expected_severity
            and isinstance(self.fresh_holder, dict)
            and bool(self.fresh_holder.get("transient"))
        )

    @property
    def reached(self) -> bool:
        """Did anything about the standing row move?

        Deliberately **reach**, not rung.  The entry's fourth bullet
        records that resolve-and-re-raise on a severity mismatch is the
        obvious fix and rebuilds ``monitor/collation.py``'s flip-flop, so
        a fix may legitimately land as an in-place rung, as a second row,
        or as the blob alone — and a check watching only the severity
        column would report two of those three as no change.
        """
        return (
            self.open_rows != 1
            or self.open_resolved
            or self.open_after != self.open_before
            or self.open_holder is not None
        )

    @property
    def moved(self) -> tuple[str, ...]:
        """What moved, in words, for the note."""
        out: list[str] = []
        if self.open_rows != 1:
            out.append(f"{self.open_rows} rows now carry the standing title")
        if self.open_resolved:
            out.append("the standing row is resolved")
        if self.open_after and self.open_after != self.open_before:
            out.append(f"its severity went {self.open_before} → {self.open_after}")
        if self.open_holder is not None:
            out.append(f"details['holder'] is now {self.open_holder!r}")
        return tuple(out)


def quietened_judgement_reading() -> tuple[QuietenReading | None, str]:
    """Judge two synthetic breaches against the live database, then roll back.

    **The instrument is the agent's own ``_execute``, and it has to be.**
    The claim is about a branch three statements into that method — a
    judgement whose title is already open is skipped *before* anything
    looks at its severity or its details — and every fix the entry
    contemplates lands in the same loop.  Driving
    :func:`~sysadmin.estate.judgements.judge_audit_findings` alone would
    measure the half that was never in doubt.

    Three things are supplied to it and nothing else is touched:

    - **the estate's answer**, through an :class:`httpx.MockTransport`
      handed to the agent's own client factory, so the real
      :func:`~sysadmin.estate.client.pull_all` runs against it — path
      dispatch, ``raise_for_status``, the JSON parse and the per-surface
      ``read`` flag are the production ones;
    - **the sweep's attribution**, as a ``unit_audits`` row inserted
      inside the transaction, so ``_attribution`` reads it the way it
      reads a real sweep.  This is what makes both ports *transient* and
      therefore quiet — the same route Session 57's fix takes;
    - **one already-open row**, at the loud rung with ``holder: null``,
      which is the state the entry was filed from.

    The transport, the mounted judge and the rolled-back transaction are
    :func:`findings_transport`, :func:`mounted_judge` and
    :func:`rolled_back_drive` — shared with
    :func:`unswept_judgement_reading`, which drives the same three
    against the *other* half of Session 57's fix.  What is local to this
    reading is the blob, the standing row and what is read back.
    """
    from sqlalchemy import select

    from sysadmin.core.models.alert import Alert
    from sysadmin.estate.agent import SURFACE_DETAIL_KEY
    from sysadmin.estate.judgements import DEFAULT_SEVERITY, judge_audit_findings
    from sysadmin.units.models import UnitAudit
    from sysadmin.units.ports import attribution_from_blob

    config = get_config()
    payload = {"findings": [quieten_finding(port) for port in QUIETEN_PORTS]}
    blob = {"transient_ports": {QUIETEN_HOLDER: list(QUIETEN_PORTS)}}
    attribution = attribution_from_blob(blob, datetime.now(UTC).isoformat())

    # What the run *ought* to produce, computed purely and before any
    # row exists. The titles come from here rather than from a format
    # string: a title written down would stop matching the day the
    # producer's wording moves, and the probe would then open a row the
    # run never judges and report the entry refuted by a rename.
    judged = judge_audit_findings(
        payload, config.agents.estate_judge.port_breach_max_rows, attribution
    )
    by_port = {judgement.details.get("port"): judgement for judgement in judged}
    if set(by_port) != set(QUIETEN_PORTS):
        return None, (
            f"judging two synthetic breaches yielded {len(judged)} judgement(s) rather "
            f"than one per port — the family has rolled them up or stopped emitting "
            "them, and this probe is no longer holding one variable"
        )
    expected = {judgement.severity for judgement in judged}
    if len(expected) != 1:
        return None, (
            "the two synthetic breaches are judged at different rungs "
            f"({', '.join(sorted(expected))}) — they differ only in port number, so the "
            "probe is no longer comparing like with like"
        )
    quiet = expected.pop()
    if quiet == DEFAULT_SEVERITY:
        return None, (
            f"a transient holder is now judged {quiet}, the same rung an ordinary breach "
            "gets — there is no quieter rung for a fix to deliver, so nothing here "
            "discriminates"
        )
    open_title = by_port[QUIETEN_OPEN_PORT].title
    fresh_title = by_port[QUIETEN_FRESH_PORT].title

    agent, problem = mounted_judge(findings_transport(payload))
    if agent is None:
        return None, problem

    async def drive(session) -> QuietenReading:
        session.add(
            Alert(
                agent=agent.name,
                severity=DEFAULT_SEVERITY,
                title=open_title,
                message=PROBE_MESSAGE,
                details={
                    SURFACE_DETAIL_KEY: by_port[QUIETEN_OPEN_PORT].surface,
                    "port": QUIETEN_OPEN_PORT,
                    # The rows the entry was filed from carry
                    # `holder: null` — raised before the sweep's
                    # attribution reached this family at all. Modelled
                    # rather than left absent, so "the blob did not
                    # arrive" is a value that did not change and not a
                    # key missing for two possible reasons.
                    "holder": None,
                },
            )
        )
        session.add(UnitAudit(scanned_at=datetime.now(UTC), findings={"ports": blob}))
        await session.flush()

        result = await agent._execute(session)  # noqa: SLF001
        await session.flush()
        session.expire_all()

        rows = list(
            (
                await session.execute(
                    select(Alert).where(
                        Alert.agent == agent.name,
                        Alert.title.in_([open_title, fresh_title]),
                    )
                )
            )
            .scalars()
            .all()
        )
        standing = [row for row in rows if row.title == open_title]
        fresh = [row for row in rows if row.title == fresh_title]
        after = standing[0] if len(standing) == 1 else None
        new_row = fresh[0] if len(fresh) == 1 else None
        return QuietenReading(
            expected_severity=quiet,
            open_before=DEFAULT_SEVERITY,
            open_after=after.severity if after is not None else "",
            open_holder=(
                (after.details or {}).get("holder") if after is not None else None
            ),
            open_resolved=bool(after.resolved) if after is not None else False,
            open_rows=len(standing),
            fresh_severity=new_row.severity if new_row is not None else None,
            fresh_holder=(
                (new_row.details or {}).get("holder") if new_row is not None else None
            ),
            fresh_rows=len(fresh),
            raised=result.alerts_raised,
        )

    return rolled_back_drive(drive)


def check_quietened_judgement_reach() -> Measurement:
    """``SNAG-ESTATE-010`` — a quieter judgement cannot reach an open row.

    **The entry's stated population has resolved, and a check that
    looked for it would be refuted by somebody closing an editor.**  It
    is filed off two live rows — ``Estate port 3110 registry breach`` and
    ``Estate port 8110 registry breach``, both VS Code dev servers,
    standing at ``warning`` with ``details['holder']`` null while
    Session 57's fix ran three lines away.  The entry says in its own
    third bullet that it self-clears: close the window and the listeners
    go, the sweep resolves both rows, and the next dev server is judged
    by the new code.  So counting those two rows measures whether an
    editor is open — rule 1, refused for the fourth time in this
    registry and the first time against an entry that predicted its own
    population away.

    What is left is a mechanism, and it is drivable end to end with
    instruments this repository already owns: an
    :class:`httpx.MockTransport` for the estate's answer, a
    ``unit_audits`` row for the sweep's attribution, and a rolled-back
    transaction on the live database for everything else.  One
    ``_execute`` call judges two synthetic breaches — one with a row
    already open under its title, one without — and the pair differs in
    exactly that.

    Four rules, three of them the opposite of the obvious
    implementation:

    1. **The assertion is *reach*, never the rung.**  The entry's fourth
       bullet records that resolve-and-re-raise on a severity mismatch is
       the obvious fix and rebuilds the flip-flop
       ``monitor/collation.py`` refuses, so a real fix may land as an
       in-place rung, as a resolved row plus a fresh one, or as the
       ``holder`` blob alone with the severity unmoved.  A check watching
       the severity column would report two of those three as no change —
       ``a-control-a-fix-breaks-is-not-a-control`` met from the side
       where the fix is the *unexpected* one.
    2. **The quiet rung is read off the judgement, never written down.**
       ``judge_audit_findings`` is run purely first, on the same payload
       and the same attribution, and its answer is what the run is
       measured against.  A constant here would be a second statement of
       :data:`~sysadmin.estate.judgements.TRANSIENT_HOLDER_SEVERITY`
       free to agree with the box while the family disagreed with both.
       The **titles** come from the same place and for a sharper reason:
       a title written as a format string would stop matching the day the
       producer's wording moves, and the probe would then open a row the
       run never judges and report a rename as the fix.
    3. **The unmoved row is evidence only beside a row that moved.**  A
       judge that had stopped computing ``info`` at all, or a sweep whose
       attribution no longer reached this family, leaves the standing row
       exactly as untouched as the dedup does.  So the same run judges a
       second port with nothing open under it, and that row must land at
       the quieter rung carrying a transient holder before either verdict
       means anything.  Without the witness the verdict is ``unknown``,
       which is also how this degrades when the database will not answer.
    4. **Nothing is committed, and the surfaces are declined rather than
       emptied.**  The four surfaces other than ``audit_findings`` answer
       ``503``, so ``read`` holds one id and the run's sweep cannot reach
       a row this probe did not open.  Rolled back either way; a probe
       that can narrow its blast radius should not spend the rollback
       instead.
    """
    reading, problem = quietened_judgement_reading()
    if reading is None:
        return Measurement("unknown", problem)

    detail = (
        f"the judgement computes {reading.expected_severity} for a transient holder, "
        f"against {reading.open_before} for an ordinary breach",
        f"port {QUIETEN_OPEN_PORT} stood open at {reading.open_before}; after the run "
        f"{reading.open_rows} row(s) carry its title, severity {reading.open_after or '—'}, "
        f"resolved={reading.open_resolved}, holder={reading.open_holder!r}",
        f"port {QUIETEN_FRESH_PORT} stood open at nothing; after the run "
        f"{reading.fresh_rows} row(s) carry its title, severity "
        f"{reading.fresh_severity or '—'}, holder={reading.fresh_holder!r}",
        f"the run reports alerts_raised={reading.raised}",
    )

    if not reading.witnessed:
        return Measurement(
            "unknown",
            f"the same run did not raise port {QUIETEN_FRESH_PORT} at "
            f"{reading.expected_severity} with a transient holder, and nothing stood open "
            "under its title — so a standing row that did not move is evidence about this "
            "probe rather than about the dedup",
            detail,
        )
    if reading.reached:
        return Measurement(
            "mismatch",
            f"the quieter judgement reached the standing row: {'; '.join(reading.moved)} — "
            "a reclassification now applies to a fault that was already open, which is "
            "what the entry says nothing does",
            detail,
        )
    return Measurement("match", "", detail)


# ---------------------------------------------------------------------------
# SNAG-ESTATE-009 — the quietening is only as good as the sweep's age
# ---------------------------------------------------------------------------

#: The port the stored sweep did **not** see, and the subject of the claim.
#:
#: The entry's dev server, modelled as the one thing that distinguishes
#: it from an attributable one: absence from the blob.  A dev server
#: started at 09:00 against a 06:07 sweep holds a socket the sweep has
#: no row for, which is this port exactly.
UNSWEPT_PORT = 65009

#: The port the sweep *did* see, and the witness.
#:
#: The same dev server started an hour earlier.  It carries the whole
#: verdict: without it, a run in which Session 57's quietening had been
#: reverted, or the blob key renamed, or ``attribution_from_blob``
#: broken, would raise the unswept port loudly for a reason that has
#: nothing to do with the window — and would look identical.
SWEPT_PORT = 65008

#: Sorted, because ``judge_audit_findings`` sorts its breaches by port
#: and a reader comparing this tuple against a payload should not have
#: to hold an ordering in their head.
UNSWEPT_PORTS = (SWEPT_PORT, UNSWEPT_PORT)

#: The session scope the probe's synthetic sweep attributes the swept
#: port to.  Distinct from :data:`QUIETEN_HOLDER` so that a leaked row
#: from either probe names which probe leaked it — the two write to the
#: same table and a shared string would make the residue ambiguous.
UNSWEPT_HOLDER = "user:snag-claims-window-probe.scope"


@dataclass(frozen=True)
class UnsweptReading:
    """One judge run over two breaches, one of which the sweep missed.

    Both are judged by the **same** ``_execute`` call, against the same
    payload, the same stored sweep and the same clock, so the pair
    differs in exactly one thing: whether the blob names the port.  Two
    runs would differ in three more.
    """

    #: The rung a *transiently held* breach is judged at, read off
    #: :func:`~sysadmin.estate.judgements.judge_audit_findings` run
    #: purely against an attribution covering **both** ports — never
    #: written down here, and never the same object as the measurement.
    quiet: str
    #: The rung an ordinary unclaimed listener gets.
    loud: str
    #: What ``EstateJudgeAgent._attribution`` returned for each port,
    #: read from the same session the run used.  The claim's first half
    #: is that the unswept one is ``None``.
    attributed_unswept: object
    attributed_swept: object
    #: How old the sweep ``_attribution`` read was, in hours, measured
    #: off the stamp it put on the attribution rather than off the clock
    #: this module used to write the row.  A probe that rebuilt the blob
    #: locally would report ``0``.
    attribution_age_hours: float | None
    unswept_severity: str | None
    unswept_holder: object
    unswept_rows: int
    unswept_detail_keys: tuple[str, ...]
    swept_severity: str | None
    swept_holder: object
    swept_rows: int
    swept_detail_keys: tuple[str, ...]
    raised: int

    @property
    def witnessed(self) -> bool:
        """Did the quietening work at all on this run?

        The control, and it carries the whole verdict.  The claim is
        that a port is loud *because the sweep missed it*, and the only
        thing that can tell that apart from a family which has stopped
        quietening anything is a port the same sweep caught, judged in
        the same breath, coming out quiet.
        ``a-check-needs-a-discriminating-witness``, which this registry
        has now had to apply at every scale from an ``ast`` walk to a
        rolled-back transaction — and here with the polarity inverted
        from the sitting before it, where the witness was a row that
        *moved* beside one that did not.
        """
        return (
            self.swept_rows == 1
            and self.swept_severity == self.quiet
            and isinstance(self.swept_holder, dict)
            and bool(self.swept_holder.get("transient"))
            and isinstance(self.attributed_swept, dict)
        )

    @property
    def annotated(self) -> bool:
        """Does the unswept row carry a key its swept sibling does not?

        The third shape a fix could take, and the only one that leaves
        both the rung and the holder alone: telling the reader that the
        evidence has a window.  The entry's "Why P3" bullet is that
        ``details['holder']['observed_at']`` already says how old the
        evidence is — which is true of an *attributed* port and vacuous
        here, because ``holder`` is ``None`` and carries no
        ``observed_at`` to read.

        Detected by comparing the two rows against each other rather
        than against a field name written down here.  A name would be a
        second statement of a producer's fact, free to go stale the day
        the fix picks a different one; the sibling comparison needs no
        name and stays true through a restructuring that moves both.
        """
        return self.unswept_detail_keys != self.swept_detail_keys

    @property
    def reached(self) -> bool:
        """Has anything told the unswept port apart from an ordinary breach?

        Deliberately wider than the rung.  "Reads as an ordinary
        unclaimed listener" is the entry's own phrasing and it is a claim
        about *indistinguishability*, so a fix lands whether the judge
        learned to quieten the port unattributed, the sweep learned to
        name its holder, or the row merely gained something saying the
        evidence is six hours wide.  Three limbs, and each has a
        falsification in which it is the **only** one that fires.

        :attr:`attributed_unswept` was a fourth and was **measured
        unreachable and removed** rather than shipped.  It is
        ``_attribution``'s answer read directly; ``unswept_holder`` is
        the same answer read off the row the run raised, and inside this
        probe the two cannot disagree — both come from the newest
        ``unit_audits`` row and the transaction writes no second one.  So
        every state that sets it also sets the rung or the holder, and no
        stand-in could make it decide anything: driven as a
        falsification, removing it left
        ``test_a_judge_that_runs_ss_itself_is_a_mismatch`` **passing
        against the broken code**.  It stays in the report, where naming
        what the sweep knew is the sharpest description of a landed fix,
        and out of the verdict, where it was a second statement of a
        fact ``unswept_holder`` already carries.
        """
        return (
            self.unswept_severity != self.loud
            or self.unswept_holder is not None
            or self.annotated
        )

    @property
    def moved(self) -> tuple[str, ...]:
        """What told them apart, in words, for the note."""
        out: list[str] = []
        if self.unswept_severity != self.loud:
            out.append(
                f"it is judged {self.unswept_severity or '—'} rather than {self.loud}"
            )
        if self.unswept_holder is not None:
            named = " — _attribution named it" if self.attributed_unswept is not None else ""
            out.append(f"details['holder'] is {self.unswept_holder!r}{named}")
        elif self.attributed_unswept is not None:
            # Unreachable inside this probe by construction, and reported
            # rather than dropped: the two readings come from one
            # `unit_audits` row, so a run in which they disagree is a
            # fix that took a live look and declined to publish it, and
            # a reader deserves to be told which of the two moved.
            out.append(
                f"_attribution holds {self.attributed_unswept!r} for it, though the row "
                "does not carry it"
            )
        if self.annotated:
            extra = set(self.unswept_detail_keys) - set(self.swept_detail_keys)
            missing = set(self.swept_detail_keys) - set(self.unswept_detail_keys)
            out.append(
                "its details differ from its swept sibling's "
                f"(extra={sorted(extra)}, absent={sorted(missing)})"
            )
        return tuple(out)


def unswept_judgement_reading() -> tuple[UnsweptReading | None, str]:
    """Judge one breach the sweep saw and one it missed, then roll back.

    **The instrument is the agent's own ``_execute``, and the sweep's
    own stored row.**  The claim is not about
    :func:`~sysadmin.estate.judgements.judge_audit_findings`, which is
    given an attribution and does as it is told — it is about where that
    attribution comes from.  ``EstateJudgeAgent._attribution`` reads the
    newest ``unit_audits`` row and nothing else, by a decision
    :meth:`~sysadmin.estate.agent.EstateJudgeAgent._attribution` argues
    for in writing, and that read is the six-hour window.  So the probe
    supplies a sweep that names one of its two ports and lets the
    production path do the rest.

    Three things are supplied and nothing else is touched — the same
    three as :func:`quietened_judgement_reading`, differing only in the
    blob:

    - **the estate's answer**, an :class:`httpx.MockTransport` behind
      the real :func:`~sysadmin.estate.client.pull_all`;
    - **the sweep's attribution**, a ``unit_audits`` row naming
      :data:`SWEPT_PORT` alone, which is a sweep that ran before the
      second dev server started;
    - **nothing standing open**, which is where this differs from the
      sitting before it: both ports are fresh, so the dedup branch that
      probe exists to measure is not in the path at all.

    ``_attribution`` is then called once more, on the same session, for
    the report.  It cannot disagree with the call ``_execute`` made:
    both read the newest ``unit_audits`` row and the transaction has
    written no second one.
    """
    from sysadmin.estate.judgements import DEFAULT_SEVERITY, judge_audit_findings
    from sysadmin.units.models import UnitAudit
    from sysadmin.units.ports import attribution_from_blob

    config = get_config()
    max_rows = config.agents.estate_judge.port_breach_max_rows
    payload = {"findings": [quieten_finding(port) for port in UNSWEPT_PORTS]}

    # Stamped **now**, and the obvious alternative was driven and
    # refuted. Backdating the row by one `scan_interval_hours` models the
    # entry's own arithmetic — the judge is hourly, the sweep six-hourly,
    # so the oldest evidence a judgement can rest on is one interval old
    # — and it puts the row *behind the box's own newest sweep*, which
    # `_attribution` then reads instead. Driven: at a 6 h backdate the
    # real sweep 1.21 h old won, `attribution.of(SWEPT_PORT)` came back
    # `None`, the witness failed and the verdict was `unknown`. The probe
    # has to own the newest row or it is not holding the variable, and
    # `attribution_age_hours` is what makes that visible rather than
    # assumed — it is ~0 while the probe's row wins and jumps the moment
    # a real sweep lands mid-drive.
    swept_at = datetime.now(UTC)
    observed_at = swept_at.isoformat()

    #: What the *stored sweep* will say: the swept port and not the other.
    blob = {"transient_ports": {UNSWEPT_HOLDER: [SWEPT_PORT]}}

    # The quiet rung, derived rather than written down — and derived
    # from an attribution the drive never uses, so the expectation and
    # the measurement cannot be one object read twice. Importing
    # `TRANSIENT_HOLDER_SEVERITY` would be a second statement of the
    # family's own constant, free to agree with this module while the
    # family disagreed with both.
    both = attribution_from_blob(
        {"transient_ports": {UNSWEPT_HOLDER: list(UNSWEPT_PORTS)}}, observed_at
    )
    fully_judged = judge_audit_findings(payload, max_rows, both)
    rungs = {judgement.severity for judgement in fully_judged}
    if len(fully_judged) != len(UNSWEPT_PORTS) or len(rungs) != 1:
        return None, (
            f"judging two attributed breaches yielded {len(fully_judged)} judgement(s) at "
            f"{len(rungs)} rung(s) rather than one row per port at one rung — the family "
            "has rolled them up or stopped emitting them, and this probe is no longer "
            "holding one variable"
        )
    quiet = rungs.pop()
    if quiet == DEFAULT_SEVERITY:
        return None, (
            f"a transient holder is now judged {quiet}, the same rung an ordinary breach "
            "gets — Session 57's quietening is what this entry is a limit on, and with no "
            "quieter rung there is nothing for the window to withhold"
        )

    # The titles come from the producer for the reason the rung does: a
    # format string here would stop matching the day the wording moves,
    # and the probe would read every row back as absent.
    #
    # Taken from the judgements above rather than from a second call
    # against the partial blob, which was written first and **measured
    # unreachable**: a roll-up depends on the breach count against
    # `max_rows`, which is the same for both attributions, so the guard
    # beside it could never fire once this one had passed — driven, and
    # `test_a_rolled_up_payload_is_unknown` passed against the broken
    # code. A title that came to depend on the holder would then part
    # from what the run raises for the *unswept* port alone, and the row
    # would read back absent, which is the direction a check should fail
    # in: that fix has told the two apart.
    titles = {
        judgement.details["port"]: judgement.title for judgement in fully_judged
    }

    agent, problem = mounted_judge(findings_transport(payload))
    if agent is None:
        return None, problem

    async def drive(session) -> UnsweptReading:
        from sqlalchemy import select

        from sysadmin.core.models.alert import Alert

        session.add(UnitAudit(scanned_at=swept_at, findings={"ports": blob}))
        await session.flush()

        result = await agent._execute(session)  # noqa: SLF001
        await session.flush()
        session.expire_all()

        attribution = await agent._attribution(session)  # noqa: SLF001
        rows = list(
            (
                await session.execute(
                    select(Alert).where(
                        Alert.agent == agent.name,
                        Alert.title.in_(list(titles.values())),
                    )
                )
            )
            .scalars()
            .all()
        )

        def one(port: int):
            held = [row for row in rows if row.title == titles[port]]
            return (held[0] if len(held) == 1 else None), len(held)

        unswept, unswept_rows = one(UNSWEPT_PORT)
        swept, swept_rows = one(SWEPT_PORT)

        def keys(row) -> tuple[str, ...]:
            return tuple(sorted((row.details or {}).keys())) if row is not None else ()

        return UnsweptReading(
            quiet=quiet,
            loud=DEFAULT_SEVERITY,
            attributed_unswept=attribution.of(UNSWEPT_PORT),
            attributed_swept=attribution.of(SWEPT_PORT),
            attribution_age_hours=(
                (datetime.now(UTC) - datetime.fromisoformat(attribution.observed_at))
                / timedelta(hours=1)
                if attribution.observed_at
                else None
            ),
            unswept_severity=unswept.severity if unswept is not None else None,
            unswept_holder=(
                (unswept.details or {}).get("holder") if unswept is not None else None
            ),
            unswept_rows=unswept_rows,
            unswept_detail_keys=keys(unswept),
            swept_severity=swept.severity if swept is not None else None,
            swept_holder=(
                (swept.details or {}).get("holder") if swept is not None else None
            ),
            swept_rows=swept_rows,
            swept_detail_keys=keys(swept),
            raised=result.alerts_raised,
        )

    return rolled_back_drive(drive)


def check_unswept_port_is_loud() -> Measurement:
    """``SNAG-ESTATE-009`` — a port the stored sweep missed is judged loudly.

    **The population is a timing accident and no count can reach it.**
    The entry is about a dev server started *between* sweeps: the sweep
    runs six-hourly and the judge hourly, so whether a given listener is
    attributed depends on which side of a six-hour boundary somebody
    opened an editor.  Counting today's rows measures when a window was
    opened, not whether the window exists — rule 1, refused for the
    fifth time in this registry and the fourth entry in a row to run
    into it.  The two rows its sibling ``SNAG-ESTATE-010`` was filed
    from are the same two rows, and they have since resolved.

    So the mechanism is driven, and it is drivable exactly because
    ``_attribution`` reads one stored row: a sweep that names one of two
    ports **is** a sweep taken before the second dev server started.
    One ``_execute`` call judges both, and the pair differs in that and
    in nothing else.

    Four rules, three of them the opposite of the obvious
    implementation:

    1. **The witness runs the other way round from the sitting before
       it.**  ``SNAG-ESTATE-010``'s probe needed a row that *moved*
       beside one that did not; this one needs a row that is *quiet*
       beside one that is loud.  Without it, a family whose quietening
       had been reverted — Session 57 backed out, the blob key renamed,
       ``attribution_from_blob`` broken — raises the unswept port loudly
       for a reason that has nothing to do with the window and looks
       identical.  Without the witness the verdict is ``unknown``, which
       is also how this degrades when the database will not answer.
    2. **The claim is indistinguishability, so the assertion is wider
       than the rung.**  "Reads as an ordinary unclaimed listener" is the
       entry's own phrasing.  A fix lands if the sweep learns to see the
       port, if the judge learns to quieten it unattributed, *or* if the
       row merely gains something saying the evidence is six hours wide —
       the last being what the entry's "Why P3" bullet gestures at, and
       vacuous today because ``holder`` is ``None`` and ``observed_at``
       lives inside it.  The third is detected by comparing the two rows'
       detail keys **against each other** rather than against a field
       name written down here, which would be a second statement of a
       producer's fact.
    3. **The quiet rung is derived from an attribution the drive never
       uses.**  Judging the same payload against a blob naming *both*
       ports gives what a transiently-held breach is worth, and that is
       what the run is measured against.  A constant here would be
       :data:`~sysadmin.estate.judgements.TRANSIENT_HOLDER_SEVERITY`
       written twice; taking it from the run's own swept row would make
       the expectation and the measurement one object, so the witness
       could never fail.
    4. **Nothing stands open, which is what separates this probe from
       its sibling.**  Both ports are fresh, so the dedup branch
       ``SNAG-ESTATE-010`` measures is not in this path at all and the
       two checks cannot report each other's fault.  Everything written
       is rolled back, and the four surfaces other than
       ``audit_findings`` are declined rather than emptied.
    """
    reading, problem = unswept_judgement_reading()
    if reading is None:
        return Measurement("unknown", problem)

    detail = (
        f"a transiently held breach is judged {reading.quiet}, against {reading.loud} "
        "for an ordinary unclaimed listener",
        f"port {SWEPT_PORT} is named by the stored sweep: _attribution holds "
        f"{reading.attributed_swept!r}, and {reading.swept_rows} row(s) carry its title "
        f"at severity {reading.swept_severity or '—'}",
        "the sweep _attribution read was "
        + (
            f"{reading.attribution_age_hours:.2f}h old"
            if reading.attribution_age_hours is not None
            else "undated"
        ),
        f"port {UNSWEPT_PORT} is not named by it: _attribution holds "
        f"{reading.attributed_unswept!r}, and {reading.unswept_rows} row(s) carry its "
        f"title at severity {reading.unswept_severity or '—'}, holder="
        f"{reading.unswept_holder!r}",
        "both rows carry the same detail keys: "
        f"{reading.unswept_detail_keys == reading.swept_detail_keys}",
        f"the run reports alerts_raised={reading.raised}",
    )

    if not reading.witnessed:
        return Measurement(
            "unknown",
            f"the same run did not raise port {SWEPT_PORT} at {reading.quiet} with a "
            "transient holder, though the stored sweep names it — so a loud unswept port "
            "is evidence that the quietening is not working at all, rather than evidence "
            "about the sweep's age",
            detail,
        )
    if reading.reached:
        return Measurement(
            "mismatch",
            f"the sweep missed port {UNSWEPT_PORT} and something told it apart from an "
            f"ordinary unclaimed listener anyway: {'; '.join(reading.moved)} — which is "
            "what the entry says the six-hour window prevents",
            detail,
        )
    return Measurement("match", "", detail)


# ---------------------------------------------------------------------------
# SNAG-TRAY-008 — the understudy restates only what it announced itself
# ---------------------------------------------------------------------------

#: The fault raised while the tray was watching, so the understudy was
#: correctly silent about it and never recorded it as spoken.  The
#: entry's **first** face: when the tray then goes away, this one is
#: never restated, because the sweep's population is what *this process*
#: said rather than what is open.
UNHEARD_TITLE = "sysadmin-check-snags probe: a fault raised while the tray was watching"

#: The fault the first notifier announced itself.  It is the **witness**
#: for the first sweep and the *subject* of the second: a fault announced
#: before the restart, which the restarted instance has never heard of.
#: One row carries both roles because the entry's second face is about
#: which instance spoke, and nothing else — a fourth title would differ
#: in more than the thing being held.
ANNOUNCED_TITLE = "sysadmin-check-snags probe: a fault the first notifier announced"

#: The fault the restarted notifier announced, and the second sweep's
#: witness.
RESTARTED_TITLE = "sysadmin-check-snags probe: a fault the restarted notifier announced"

#: In the order the timeline opens them.
UNDERSTUDY_TITLES = (UNHEARD_TITLE, ANNOUNCED_TITLE, RESTARTED_TITLE)


def supplied_presence(elapsed: Callable[[], float]):
    """The tray gate with its one clock reading supplied rather than slept.

    :class:`~sysadmin.monitor.desktop.TrayPresence` is deliberately
    monotonic and takes no clock parameter — its own docstring argues for
    both — so a probe cannot build a tray that went away thirty hours ago
    by waiting for one.  One leaf is overridden and every gate above it
    is the module's own: ``is_watching`` is **inherited**, and still
    computes ``elapsed <= grace_seconds`` against the live
    ``tray_grace_seconds``.

    ``mark_seen()`` is called, so ``ever_seen`` is ``True``.  That is not
    cosmetic.  The base class keeps "never saw a tray" and "saw one long
    ago" apart on purpose, and the entry's first face is a tray that was
    *here and left*; a probe that had simply never marked one would be
    modelling a daemon that started before the tray, which a fix keyed on
    how long the tray has been absent could legitimately decline to adopt
    from — ``a-control-a-fix-breaks-is-not-a-control``.
    """
    from sysadmin.monitor.desktop import TrayPresence

    class SuppliedPresence(TrayPresence):
        def __init__(self) -> None:
            super().__init__()
            self.mark_seen()

        def seconds_since_seen(self) -> float:
            return elapsed()

    return SuppliedPresence()


def recorded_notifier(session, clock: Callable[[], float]):
    """The real understudy, with ``notify-send`` replaced by a list.

    Exactly one leaf is overridden.
    :meth:`~sysadmin.monitor.desktop.DesktopNotifier.send` is the
    transport — it shells out to ``notify-send`` and returns whether the
    toast landed — and this entry is about *which faults reach it*, never
    about how one is drawn.  Every gate, the spoken set, the roll-up, the
    ``_still_open`` query and the clock above it are production.

    It returns ``True``, which is the module's word for "it landed".  A
    transport that failed would leave nothing recorded as spoken (that
    module's rule 4), and the probe would then be measuring a daemon with
    no session bus rather than the population question.
    """
    from sysadmin.monitor.desktop import DesktopNotifier

    class RecordedNotifier(DesktopNotifier):
        def __init__(self) -> None:
            super().__init__(session_factory=lambda: _SharedSession(session), clock=clock)
            self.sent: list[tuple[str, str, str]] = []

        async def send(self, severity: str, title: str, body: str) -> bool:
            self.sent.append((severity, title, body))
            return True

    return RecordedNotifier()


class _SharedSession:
    """Hand the notifier the drive's session without letting it close one.

    ``_is_new_incident`` and ``_still_open`` each do ``async with
    factory() as session``, which against a real ``async_sessionmaker``
    opens a session and closes it on the way out — and closing this one
    would end the transaction every row the probe wrote lives in.  So the
    factory yields the drive's session and declines to close it: the
    rollback stays where :func:`rolled_back_drive` puts it, in one
    ``finally`` owning the whole drive.
    """

    def __init__(self, session) -> None:
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc: object) -> bool:
        return False


def quietest_admitted_rung(min_severity: str) -> str | None:
    """The quietest rung the understudy would speak at, off its own map.

    Derived rather than written down — :data:`~sysadmin.monitor.desktop
    .SEVERITY_LEVELS` and its ``1`` default are the module's own, so a
    probe and a gate cannot come to disagree about which rungs pass.

    Derived **quiet** rather than loud, which is the part worth stating.
    ``critical`` clears gate 3 on this box whatever ``min_severity``
    says, because ``dnd.allow_critical`` lets it through a Do Not Disturb
    window — so a probe that picked it would be arranging to pass a gate
    instead of measuring one.  The quietest admitted rung is the rung a
    fault here actually has to clear.
    """
    from sysadmin.monitor.desktop import SEVERITY_LEVELS

    threshold = SEVERITY_LEVELS.get(min_severity, 1)
    admitted = [rung for rung, level in SEVERITY_LEVELS.items() if level >= threshold]
    if not admitted:
        return None
    return min(admitted, key=lambda rung: SEVERITY_LEVELS[rung])


def restated(sent: Iterable[tuple[str, str, str]], title: str) -> bool:
    """Did *title* reach a screen in any of *sent*?

    Two shapes are read, because
    :meth:`~sysadmin.monitor.desktop.DesktopNotifier._restate` folds at
    ``_ROLLUP_THRESHOLD``: a lone reminder carries the fault's own title,
    and a roll-up carries ``"N faults still open"`` and names its members
    in the body.

    The roll-up half is load-bearing rather than defensive.  A fix that
    adopted one further fault would push the very run this probe drives
    over the fold, so a probe reading only titles would report a landed
    fix as **silence** — the check coupled to the unfixed behaviour,
    which is ``a-control-a-fix-breaks-is-not-a-control`` read at the
    level of a string comparison.
    """
    return any(title == sent_title or title in body for _, sent_title, body in sent)


def _rendered(sent: Iterable[tuple[str, str, str]]) -> tuple[str, ...]:
    """What a sweep said, flattened onto one line each for the report."""
    return tuple(
        f"{severity}: {title!r} / {body!r}".replace("\n", " ⏎ ")
        for severity, title, body in sent
    )


@dataclass(frozen=True)
class UnderstudyReading:
    """One understudy's timeline: a tray that left, and a restart.

    Three faults are opened against the live table and one notifier
    speaks for two of them.  The pair that matters differ in exactly one
    thing each: :data:`UNHEARD_TITLE` from :data:`ANNOUNCED_TITLE` only
    in whether the tray was watching when it was raised, and
    :data:`ANNOUNCED_TITLE` at the second sweep from
    :data:`RESTARTED_TITLE` only in which instance announced it.
    """

    #: The live reminder interval, in hours, and the rung derived from
    #: the live ``min_severity``.  Both in the report because both decide
    #: what the run could have said.
    interval_hours: float
    severity: str
    #: Titles that already had an unresolved row before the probe wrote
    #: anything.  A collision makes ``_is_new_incident`` count two and
    #: the understudy stay silent, so the probe would measure gate 2.
    pre_existing: tuple[str, ...]
    #: The premises.  The first must be ``False`` and the other two
    #: ``True``, or the probe never built the state the entry describes.
    spoke_while_watched: bool
    spoke_unwatched: bool
    spoke_after_restart: bool
    #: What the first sweep restated: its own fault (the witness) and the
    #: one the tray was watching for (the entry's first face).
    witness_first: bool
    unheard_adopted: bool
    #: What the sweep after the restart restated: its own fault (the
    #: second witness) and its predecessor's (the entry's second face).
    witness_second: bool
    remembered: bool
    first_count: int
    second_count: int
    first_sent: tuple[str, ...]
    second_sent: tuple[str, ...]
    #: Which of the three titles the database still reports unresolved
    #: when the drive ends, read straight rather than through the
    #: notifier — a fault that had resolved would go unrestated for a
    #: reason that has nothing to do with the population.
    still_open: tuple[str, ...]

    @property
    def refusal(self) -> str:
        """Why this run measured nothing, or ``""`` — the witness, with a reason.

        Its sibling checks carry a bare ``witnessed`` bool.  This probe
        has five distinguishable ways to fail to hold its variables, and
        a reader handed ``unknown`` off a bool cannot tell a colliding
        title from a broken sweep — which is rule 5's own argument (a
        claim nobody managed to test and a claim that still holds are the
        two answers a hand sweep could not tell apart) applied one level
        down, to the reasons rather than to the verdict.

        The last limb is the control proper.  **A notifier that had
        stopped sweeping at all looks exactly like one obeying the
        entry**: nothing is restated either way.  So a fault each
        instance *did* announce is swept in the same call it is measured
        by, and it must come back out.
        """
        if self.pre_existing:
            return (
                "a live unresolved row already carries "
                f"{', '.join(repr(t) for t in self.pre_existing)}, so gate 2 counts two "
                "open rows and the understudy stays silent for a reason that is not this "
                "entry's"
            )
        if self.spoke_while_watched:
            return (
                "the understudy announced a fault raised while the tray was watching, so "
                "the probe cannot build the thing the entry is about — a standing fault "
                "this process never announced"
            )
        if not (self.spoke_unwatched and self.spoke_after_restart):
            return (
                "the understudy announced nothing with the tray away "
                f"(first={self.spoke_unwatched}, after the restart={self.spoke_after_restart}), "
                "so no fault entered the spoken set and the sweep had no population at all"
            )
        if set(self.still_open) != set(UNDERSTUDY_TITLES):
            missing = sorted(set(UNDERSTUDY_TITLES) - set(self.still_open))
            return (
                "the probe's rows did not all stay open "
                f"({', '.join(repr(t) for t in missing)} resolved mid-drive), and a fault "
                "that has cleared is dropped from the spoken set rather than withheld"
            )
        if not (self.witness_first and self.witness_second):
            return (
                "the same runs did not restate the faults each instance had announced "
                f"(first sweep={self.witness_first}, sweep after the restart="
                f"{self.witness_second}) — so silence about the other two is evidence "
                "that reminders have stopped working at all, rather than evidence about "
                "which faults the sweep can see"
            )
        return ""

    @property
    def reached(self) -> bool:
        """Has the entry been refuted — **both** faces, never one?

        The entry's own warning, turned into the verdict rule: *"a fix
        that addresses only the second half leaves the first looking
        fixed"*.  Persisting the spoken set across a restart is the
        obvious fix and closes the second face alone; the first is a
        scoping question and would still stand, so the entry would still
        be open and ``mismatch`` — a candidate for closure, rule 2 —
        would be wrong.  A half is reported in the note of a ``match``
        instead, where it is news without being a closure.
        """
        return self.unheard_adopted and self.remembered

    @property
    def moved(self) -> tuple[str, ...]:
        """Which faces moved, in words, for the note."""
        out: list[str] = []
        if self.unheard_adopted:
            out.append(
                "the sweep restated a fault this process never announced — the one raised "
                "while the tray was watching"
            )
        if self.remembered:
            out.append(
                "the sweep after the restart restated a fault only the instance before it "
                "had announced"
            )
        return tuple(out)


async def _unresolved_titles(session, titles: Iterable[str]) -> tuple[str, ...]:
    """Which of *titles* have an unresolved row, read on the drive's session.

    Deliberately **not** through
    :meth:`~sysadmin.monitor.desktop.DesktopNotifier._still_open`, though
    it answers the same question: that method is bounded by the spoken
    set, which is the very thing under measurement, so asking it would
    make the probe's control a reading of the behaviour it is
    controlling for.
    """
    from sqlalchemy import select

    from sysadmin.core.models.alert import Alert

    rows = await session.scalars(
        select(Alert.title)
        .where(Alert.title.in_(list(titles)), Alert.resolved.is_(False))
        .distinct()
    )
    return tuple(sorted(rows))


async def _opened(agent, session, severity: str, title: str) -> dict[str, object]:
    """Write one alert row and take the event the producer publishes for it.

    The event is never typed out here.  ``BaseAgent.raise_alert`` builds
    the ``alert.raised`` payload the bus carries and the understudy is
    subscribed to, so a literal would keep matching a shape that had
    moved and the probe would measure a notifier declining an event
    nothing sends — :func:`quieten_finding`'s rule, one producer over.

    ``_pending_events`` is a list rather than ``None`` so the event
    buffers on the agent instead of reaching the live bus, which is
    :func:`mounted_judge`'s move one subscriber over: a probe that
    published would hand the *real* ``desktop_notifier`` an alert about a
    fault nobody has.
    """
    await agent.raise_alert(session, severity, title, PROBE_MESSAGE)
    queued = agent._pending_events[-1] if agent._pending_events else None  # noqa: SLF001
    if queued is None or queued[1].get("title") != title:
        raise RuntimeError(
            "raise_alert no longer buffers an event carrying the title it wrote, so this "
            "probe cannot hand the understudy the payload the bus would"
        )
    return queued[1]


def understudy_sweep_reading() -> tuple[UnderstudyReading | None, str]:
    """Drive one understudy across a tray outage and a restart, then roll back.

    **The instrument is the module's own subscriber and its own sweep**,
    with two leaves supplied: the transport (a list rather than
    ``notify-send``) and the two clock readings (the notifier's injected
    ``clock``, and the tray's elapsed time, which
    :class:`~sysadmin.monitor.desktop.TrayPresence` takes no parameter
    for).  Everything the entry is about sits above both — the gates,
    ``_spoken``, ``_still_open``'s bounded query and the roll-up.

    Two faces need two drives, and the entry says why in its own body:
    *"a fix that addresses only the second half leaves the first looking
    fixed"*.  So a check that only restarted the notifier would report
    the whole entry refuted the day the spoken set was persisted.  They
    are driven as two sweeps on one timeline rather than two probes,
    because that is what the box would do — the second instance **is**
    the first one restarted, and the fault it has forgotten is the one
    the first announced and restated, which is the strongest available
    evidence that it was genuinely announced before the restart.

    The timeline, every offset off the live config:

    1. the tray is watching (elapsed ``0``); :data:`UNHEARD_TITLE` is
       raised and the understudy is correctly silent;
    2. the tray goes away (elapsed past ``tray_grace_seconds``);
       :data:`ANNOUNCED_TITLE` is raised and the understudy speaks;
    3. a full ``reminder_hours`` passes and the first sweep runs — the
       witness, and the first face;
    4. the daemon restarts (a second instance, same clock, same
       session); :data:`RESTARTED_TITLE` is raised and it speaks;
    5. another full interval passes and the second sweep runs — the
       second witness, and the second face.

    By step 5 the tray has been absent for over two intervals, which is
    deliberate: the fix the entry itself sketches adopts a fault *"only
    when the tray has been absent for a full ``reminder_hours``"*, so a
    probe whose tray had merely gone quiet a moment ago would refuse that
    fix its own precondition and read it as unfixed.
    """
    from sysadmin.monitor import desktop as understudy
    from sysadmin.monitor.agent import SysAdminAgent
    from sysadmin.monitor.dnd import dnd_manager

    config = get_config().notifications.desktop
    if not config.enabled:
        return None, (
            "notifications.desktop.enabled is false on this box, so the understudy speaks "
            "for nothing and there is no population for a reminder to be withheld from"
        )
    interval = config.reminder_hours * 3600
    if interval <= 0:
        return None, (
            f"notifications.desktop.reminder_hours is {config.reminder_hours}, which "
            "disables the reminder sweep — the mechanism this entry is a limit on is "
            "switched off, not narrowed"
        )
    severity = quietest_admitted_rung(config.min_severity)
    if severity is None:
        return None, (
            f"notifications.desktop.min_severity is {config.min_severity!r}, which admits "
            "no rung the understudy knows, so nothing it is handed can pass gate 3"
        )
    if dnd_manager.should_suppress(severity):
        return None, (
            f"Do Not Disturb is suppressing {severity} right now, so the opening "
            "notification would not land and nothing would be recorded as spoken — the "
            "probe would measure gate 3 rather than the sweep's population"
        )

    async def drive(session) -> UnderstudyReading:
        agent = SysAdminAgent()
        agent._pending_events = []  # noqa: SLF001 — buffer, never publish

        pre_existing = await _unresolved_titles(session, UNDERSTUDY_TITLES)

        # One fake timeline in seconds, monotonic-shaped like the clock
        # it replaces, with the tray last seen at its origin.
        now = [0.0]

        def clock() -> float:
            return now[0]

        presence = supplied_presence(clock)
        standing = understudy.tray_presence
        # The module resolves `tray_presence` from its own globals at
        # call time, which is what makes this substitution reach both
        # gates without touching either. Restored in the `finally`
        # below: this module is imported by the test suite, where the
        # real object is shared process-wide.
        understudy.tray_presence = presence
        try:
            first = recorded_notifier(session, clock)

            async def announce(notifier, title: str) -> tuple[tuple[str, str, str], ...]:
                event = await _opened(agent, session, severity, title)
                before = len(notifier.sent)
                await notifier.on_alert_raised(event)
                return tuple(notifier.sent[before:])

            # 1 — the tray is watching, so the understudy defers to it.
            watched = await announce(first, UNHEARD_TITLE)

            # 2 — the tray goes away, and this one the understudy owns.
            now[0] = config.tray_grace_seconds + 1.0
            unwatched = await announce(first, ANNOUNCED_TITLE)

            # 3 — a full interval later, the sweep the entry is about.
            now[0] += interval + 1.0
            before = len(first.sent)
            first_count = await first.sweep_reminders()
            first_sent = tuple(first.sent[before:])

            # 4 — the daemon restarts. Same clock and same session: the
            # only thing the new instance lacks is what the old one said.
            second = recorded_notifier(session, clock)
            after_restart = await announce(second, RESTARTED_TITLE)

            # 5 — and a full interval after *that*.
            now[0] += interval + 1.0
            before = len(second.sent)
            second_count = await second.sweep_reminders()
            second_sent = tuple(second.sent[before:])
        finally:
            understudy.tray_presence = standing

        return UnderstudyReading(
            interval_hours=config.reminder_hours,
            severity=severity,
            pre_existing=pre_existing,
            spoke_while_watched=bool(watched),
            spoke_unwatched=bool(unwatched),
            spoke_after_restart=bool(after_restart),
            witness_first=restated(first_sent, ANNOUNCED_TITLE),
            unheard_adopted=restated(first_sent, UNHEARD_TITLE),
            witness_second=restated(second_sent, RESTARTED_TITLE),
            remembered=restated(second_sent, ANNOUNCED_TITLE),
            first_count=first_count,
            second_count=second_count,
            first_sent=_rendered(first_sent),
            second_sent=_rendered(second_sent),
            still_open=await _unresolved_titles(session, UNDERSTUDY_TITLES),
        )

    return rolled_back_drive(drive)


def check_understudy_forgets() -> Measurement:
    """``SNAG-TRAY-008`` — the reminder sweep restates only what it said itself.

    **The population is zero and no count can reach it.**  The entry's
    own last bullet says so: it was filed *"as the stated cost of
    ``SNAG-TRAY-007``'s rule 1 rather than by observation"* — the
    understudy speaks only when nothing is polling the alerts route, and
    the tray on this box does.  So there is nothing to count, and rule 1
    for the fifth entry running says to drive the mechanism instead.

    It is the cheapest mechanism left in the register.  No subprocess, no
    outbound request and no scheduler: ``DesktopNotifier`` already takes
    an injected ``clock``, the reminder population is exactly the keys of
    an in-memory dict, and a restart is a second instance.

    Four rules, three of them the opposite of the obvious
    implementation:

    1. **Two faces, two sweeps, and neither alone is the entry.**  The
       entry names a fault raised while the tray was up (never adopted)
       and a restart (everything forgotten), and warns in its own body
       that a fix for the second leaves the first *looking* fixed.  A
       check driving only the restart would therefore close the entry on
       the day half of it was fixed, which is the entry's warning turned
       into an instruction for the checker.  So ``reached`` is a
       conjunction, and a half-fix is reported in the note of a
       ``match``.
    2. **The witness is a fault the instance did announce, swept in the
       same call.**  Both faces are measured as *silence*, and a notifier
       that had stopped sweeping at all — a broken ``_still_open``, a
       disabled job, a transport that never lands — is silent in exactly
       the same way.  Each sweep therefore has to produce something
       before its silences mean anything.
    3. **The rows are real and the transaction is rolled back.**  A fake
       session answering ``IN (:spoken)`` would be a control the fix
       breaks: the shape the entry itself proposes reads the *open* rows
       and caps them, so it would query for something a stub built
       around the unfixed query could not answer.  Real unresolved rows
       answer any query a fix cares to write.
    4. **The clock is supplied twice and nothing is slept.**  The
       notifier takes a ``clock`` parameter; ``TrayPresence`` takes none,
       so its single reading is overridden and every gate above it —
       ``is_watching`` against the live ``tray_grace_seconds`` —
       stays the module's own.
    """
    reading, problem = understudy_sweep_reading()
    if reading is None:
        return Measurement("unknown", problem)

    detail = (
        f"the understudy speaks at {reading.severity} and restates after "
        f"{reading.interval_hours:g}h",
        f"raised while the tray was watching: announced={reading.spoke_while_watched}; "
        f"raised with the tray away: announced={reading.spoke_unwatched}",
        f"the first sweep restated {reading.first_count} fault(s): "
        + ("; ".join(reading.first_sent) or "nothing"),
        f"it restated the fault it had announced: {reading.witness_first}; the one it had "
        f"not: {reading.unheard_adopted}",
        f"the sweep after the restart restated {reading.second_count} fault(s): "
        + ("; ".join(reading.second_sent) or "nothing"),
        f"it restated the fault it had announced: {reading.witness_second}; its "
        f"predecessor's: {reading.remembered}",
        f"all three rows were still open at the end: "
        f"{set(reading.still_open) == set(UNDERSTUDY_TITLES)}",
    )

    if reading.refusal:
        return Measurement("unknown", reading.refusal, detail)
    if reading.reached:
        return Measurement(
            "mismatch",
            "the sweep's population is no longer only what this process announced: "
            + "; ".join(reading.moved),
            detail,
        )
    if reading.moved:
        return Measurement(
            "match",
            "and one of its two faces has moved — "
            + "; ".join(reading.moved)
            + " — which the entry warns leaves the other looking fixed, so it is news "
            "rather than a closure",
            detail,
        )
    return Measurement("match", "", detail)


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
        Check(
            "capped_signature_collides",
            "SNAG-LOG-013",
            "a capped signature can name two faults at once",
            check_capped_signature_collides,
        ),
        Check(
            "nudge_wording_unpublished",
            "SNAG-ESTATE-002",
            "the estate's nudge wording never reaches the wire",
            check_nudge_wording_unpublished,
        ),
        Check(
            "unwrap_is_read_time",
            "SNAG-LOG-008",
            "a stored row's shape was fixed when it was read",
            check_unwrap_is_read_time,
        ),
        Check(
            "code_spans_survive",
            "SNAG-LOG-012",
            "strip_markdown leaves the model's inline code spans",
            check_code_spans_survive,
        ),
        Check(
            "health_path_guess",
            "SNAG-UNITS-003",
            "the emitted kind: http url guesses the health path",
            check_health_path_guess,
        ),
        Check(
            "expiry_naive_instant",
            "SNAG-ESTATE-013",
            "check:expires reads a zoneless instant as local",
            check_expiry_naive_instant,
        ),
        Check(
            "unswept_port_is_loud",
            "SNAG-ESTATE-009",
            "a port the stored sweep missed is judged loudly",
            check_unswept_port_is_loud,
        ),
        Check(
            "quietened_judgement_reach",
            "SNAG-ESTATE-010",
            "a quieter judgement cannot reach an open row",
            check_quietened_judgement_reach,
        ),
        Check(
            "understudy_forgets",
            "SNAG-TRAY-008",
            "the reminder sweep restates only what it announced",
            check_understudy_forgets,
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
