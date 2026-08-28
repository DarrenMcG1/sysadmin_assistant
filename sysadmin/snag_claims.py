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
from sqlalchemy.engine import make_url

from sysadmin import ops_claims
from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.escalation import humanise_hours
from sysadmin.core.schema_guard import EXIT_STATUS, SchemaVerdict
from sysadmin.core.text import strip_markdown

if TYPE_CHECKING:  # pragma: no cover — annotations only
    from collections.abc import Awaitable, Mapping

    import httpx
    from sqlalchemy.ext.asyncio import AsyncSession

    from sysadmin.core.contracts import ServiceRecommendationInfo
    from sysadmin.estate.agent import EstateJudgeAgent
    from sysadmin.monitor.log_actions import LogRecommendation
    from sysadmin.monitor.log_trends import ChangeKind, SignatureTrend
    from sysadmin.monitor.reliability import HealthPoint, ReliabilityScore
    from sysadmin.monitor.service_recommendations import AdviceReport, TimerSeries
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
    is why this is not a bare count of call sites — the shape
    ``SNAG-AGENT-007``'s check used, removed with that entry on
    2026-08-27.  ``SNAG-LOG-008`` says the unwrap happens at read time; a call that
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


#: ``SNAG-LOG-014``'s subject.  The two rows are ``sysadmin.service``'s,
#: which is not a coincidence: the mechanism needs a restart that re-read
#: its own resume boundary, and the only one on record is the 19:50:19
#: deploy of this daemon's own ``format: json`` declaration.
DUPLICATE_INGEST_SOURCE = "sysadmin.service"

#: Duplicate *groups*, never duplicate rows.  A group of three would be
#: one record ingested three times and is still one fault; counting rows
#: would report it as two.
DUPLICATE_GROUPS_SQL = """
    SELECT count(*) FROM (
        SELECT source FROM sysadmin.log_entries
        GROUP BY source, logged_at, message HAVING count(*) > 1
    ) d
"""

DUPLICATE_GROUPS_ELSEWHERE_SQL = """
    SELECT count(*) FROM (
        SELECT source FROM sysadmin.log_entries
        WHERE source <> :source
        GROUP BY source, logged_at, message HAVING count(*) > 1
    ) d
""".replace(":source", f"'{DUPLICATE_INGEST_SOURCE}'")

SOURCE_ROWS_SQL = (
    "SELECT count(*) FROM sysadmin.log_entries "
    f"WHERE source = '{DUPLICATE_INGEST_SOURCE}'"
)


def check_duplicate_ingest_residue() -> Measurement:
    """``SNAG-LOG-014`` — two journal records are stored twice.

    **The witness is the source still having rows**, and it is not
    optional.  This entry's population empties by *retention* on
    2026-09-16 with nothing done, so a check that read "no duplicate
    groups" as a refutation would report the entry dead on the morning
    the last row aged out — ``SNAG-LOG-013``'s reading, refused here for
    the fourth time in this registry.  An empty source is ``unknown``:
    the claim was about rows, and there are no rows to be about.

    **The count is over every source, not over the one the entry
    names.**  Scoping to ``sysadmin.service`` would make the entry's
    strongest claim — that these are the *only* duplicate pairs in
    ``log_entries`` at all — unmeasurable by the check that exists to
    measure it, and would hide a second occurrence of the mechanism
    somewhere else, which is the shape a fix would need to know about.

    **Grouped rather than counted in rows.**  One record ingested three
    times is one fault; two rows of arithmetic would call it two.
    """
    here, problem = query_one(DUPLICATE_GROUPS_SQL)
    if problem:
        return Measurement("unknown", problem)
    rows, problem = query_one(SOURCE_ROWS_SQL)
    if problem:
        return Measurement("unknown", problem)
    elsewhere, problem = query_one(DUPLICATE_GROUPS_ELSEWHERE_SQL)
    if problem:
        return Measurement("unknown", problem)

    detail = (
        f"{here} duplicate group(s) across log_entries, "
        f"{elsewhere} of them outside {DUPLICATE_INGEST_SOURCE}",
        f"{DUPLICATE_INGEST_SOURCE} holds {rows} row(s) in the retention window",
    )
    if not rows:
        return Measurement(
            "unknown",
            f"{DUPLICATE_INGEST_SOURCE} has no rows left — retention has emptied "
            "the window the claim was about, so an absence of duplicates says "
            "nothing about whether they were ever there",
            detail,
        )
    if not here:
        return Measurement(
            "mismatch",
            "no duplicate group remains in log_entries while the source still "
            "carries rows — the pair has been removed or has aged out, and the "
            "entry has nothing left to describe",
            detail,
        )
    return Measurement("match", "", detail)


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
        entry for entry in services.services if entry.port is not None and entry.unit is not None
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
    blob = {"unit_audited_ports": {f"{HEALTH_PROBE_SCOPE}:{HEALTH_PROBE_UNIT}": [port]}}
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
                            entry.name,
                            entry.port,
                            guess,
                            False,
                            "not-probed",
                            entry.url,
                            False,
                            "not-probed",
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
                            entry.name,
                            entry.port,
                            guess,
                            not is_fault(guess_status),
                            guess_status,
                            entry.url,
                            False,
                            "not-probed",
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
            connect_args={"server_settings": {"search_path": f"{config.database.schema_},public"}},
        )
        try:
            # **The transaction is the connection's, not the session's,
            # and the session joins it by savepoint.**  A plain session
            # rolled back in a ``finally`` holds only as long as nothing
            # inside the drive commits — and code under probe is allowed
            # to own its own transaction: ``DesktopNotifier._remember``
            # does, because a store write with no commit is a store write
            # that did not happen.  Under the old shape that ``commit()``
            # ended the drive's transaction and every row it had written
            # became permanent, with the ``finally`` rolling back
            # nothing.  ``join_transaction_mode="create_savepoint"``
            # turns an inner commit into a savepoint release, so the
            # outer rollback below is still the only writer of record.
            #
            # A harness that cannot survive the code it drives is a
            # control the next fix breaks.
            async with engine.connect() as connection:
                outer = await connection.begin()
                factory = async_sessionmaker(
                    bind=connection,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                )
                async with factory() as session:
                    try:
                        return await work(session)
                    finally:
                        # Before `engine.dispose()`, and unconditional: a
                        # rollback is the only reason these probes are
                        # allowed to write to the live database at all.
                        await session.rollback()
                        await outer.rollback()
        finally:
            await engine.dispose()

    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        return asyncio.run(drive()), ""
    except Exception as exc:  # noqa: BLE001 — a drive that would not run is "unknown"
        return None, (
            f"the judge would not run against the live database ({exc.__class__.__name__}: {exc})"
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

        Deliberately **reach**, not rung: the entry's fourth bullet
        records that resolve-and-re-raise on a severity mismatch is the
        obvious fix and rebuilds ``monitor/collation.py``'s flip-flop, so
        a fix may land as an in-place rung *or* as a second row, and a
        check watching the severity column alone would report the second
        as no change.

        **Two of the entry's three shapes are left, because the third
        landed** (2026-08-28, ``SNAG-AGENT-009``).  A held judgement now
        rewrites the standing row's ``message`` and ``details``, so
        ``details['holder']`` reaches a row that is already open and
        ``open_holder is not None`` is the *expected* reading rather than
        a fix signal — driven live the run gives ``holder`` arrived,
        severity ``warning`` → ``warning``, one row, unresolved.  Keeping
        the clause would report the entry refuted on the strength of a
        different entry's fix and stop discriminating the moment it
        landed: the verdict would be ``mismatch`` whatever happened to
        the rung, which is a control a fix broke.

        The blob is still carried in ``detail`` and is still read by
        :attr:`open_holder`, because "the correction reached the row and
        the rung stayed put" is a stronger statement of the surviving
        claim than "nothing happened", and a reader of the note needs to
        be able to tell those apart.
        """
        return self.open_rows != 1 or self.open_resolved or self.open_after != self.open_before

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
        # `open_holder` is deliberately absent: since SNAG-AGENT-009 the
        # blob arriving is what a correct run does, so naming it here
        # would put an expected observation in a note that lists what
        # refutes the entry.
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
            open_holder=((after.details or {}).get("holder") if after is not None else None),
            open_resolved=bool(after.resolved) if after is not None else False,
            open_rows=len(standing),
            fresh_severity=new_row.severity if new_row is not None else None,
            fresh_holder=((new_row.details or {}).get("holder") if new_row is not None else None),
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
       where the fix is the *unexpected* one.  **The third shape landed
       on 2026-08-28**: ``SNAG-AGENT-009``'s remedy rewrites a held row's
       ``message`` and ``details``, so the blob now arrives on every run
       and :attr:`QuietenReading.reached` stopped reading it — keeping
       the clause would have reported this entry refuted by a different
       entry's fix and returned ``mismatch`` whatever the rung did.  What
       is still filed is the half Session 39 keeps shut on purpose.
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
            self.unswept_severity != self.loud or self.unswept_holder is not None or self.annotated
        )

    @property
    def moved(self) -> tuple[str, ...]:
        """What told them apart, in words, for the note."""
        out: list[str] = []
        if self.unswept_severity != self.loud:
            out.append(f"it is judged {self.unswept_severity or '—'} rather than {self.loud}")
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
    titles = {judgement.details["port"]: judgement.title for judgement in fully_judged}

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
            unswept_holder=((unswept.details or {}).get("holder") if unswept is not None else None),
            unswept_rows=unswept_rows,
            unswept_detail_keys=keys(unswept),
            swept_severity=swept.severity if swept is not None else None,
            swept_holder=((swept.details or {}).get("holder") if swept is not None else None),
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
# The twentieth check — a sentence nothing can reach
# ---------------------------------------------------------------------------

#: The figure the specimen's *marked* half states.  Any value would do —
#: ``documented`` is whatever the region says — so it is deliberately not
#: this box's real route count, because a witness that happens to agree
#: with the live figure cannot be told apart from one read off the real
#: ``STATUS.md`` by a probe that lost its own document.
INVISIBLE_ROUTES = "7"

#: ``SNAG-ESTATE-012``'s specimen: a printed region cut down to the two
#: sentences the entry is about.  ``printed_region`` runs from the top of
#: the file to the heading *after* ``## Quick Status``, so the block above
#: the table is what a sitting reads and what this document supplies.
#:
#: The marked sentence sits **first** and the unmarked one after it.  A
#: markdown code span closes on a backtick run of its own length
#: (:data:`CODE_SPAN_RE`), and two of the entry's three sentences carry a
#: balanced pair — so an unmarked sentence placed *above* the marker could
#: in principle swallow it and the probe would report invisibility caused
#: by its own layout.  It cannot reach backwards from below, and the
#: witness would catch it either way.
INVISIBLE_DOCUMENT = """\
# Status — a printed region built by sysadmin-check-snags

> **Two sentences, and only one of them is a claim anything here can reach.**
> <!--check:routes--> The application serves **{routes} routes**.
{sentence}
## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Probe | green | the printed region ends at the heading above |
"""

#: The entry's own three instances, verbatim from its ``Symptom`` bullet.
#: Not invented specimens: the defect is a human writing an English claim
#: into the block, so a sentence this repository made up for the occasion
#: would be measuring a hypothetical one — :meth:`TestTheExpiryCheck.
#: test_the_producer_stamp_is_the_entrys_own`'s rule, one entry over.
#:
#: They are three rather than one because they fail differently: an
#: imperative with no figure in it at all, a bare number beside a port,
#: and a snag id with a count spelled as a word.  A pattern family added
#: later would plausibly reach the second and not the first.
INVISIBLE_SENTENCES = (
    "ask estate-manager the Session 33 question",
    "8400 answers `200` now",
    "`SNAG-ROADMAP-002` has published wrong board movement for seven consecutive sittings",
)

#: What counts as a word the report could only have got from the sentence.
#: Subtracted from the base document *and* from the baseline report, so
#: what survives both is distinctive by construction rather than by a
#: hand-written list somebody has to keep in step — and a word already in
#: the baseline proves nothing, since the two drives differ by the
#: sentence alone.
#:
#: **Four characters, and the boundary was set by running it at five.**
#: At five the middle sentence yielded *nothing*: ``8400`` is four
#: characters and ``answers`` is already in the baseline report, as the
#: subject of the ``/health`` claim.  So the quotation instrument was
#: dead for one of the three specimens and silently — which is this
#: entry's own symptom arriving inside its own check.  Three is refused
#: in the other direction: ``the``/``has``/``for`` appear in almost any
#: note, and although the subtraction would remove them from the baseline
#: it would not remove them from a live alert title arriving in the
#: second drive only.
INVISIBLE_WORD_RE = re.compile(r"[A-Za-z0-9-]{4,}")


def invisible_document(sentence: str = "") -> str:
    """The specimen, with or without the unmarked sentence."""
    line = f"> {sentence}\n" if sentence else ""
    return INVISIBLE_DOCUMENT.format(routes=INVISIBLE_ROUTES, sentence=line)


def ops_report(document: str) -> tuple[list[ops_claims.Claim], str]:
    """Drive the real ops-claims reader over one synthetic document.

    :func:`sysadmin.ops_claims.check_all` takes the *document* rather than
    a region, so the specimen is written to a file and the module does its
    own :func:`~sysadmin.ops_claims.printed_region` cut.  Handing it a
    region would skip the one step this entry's siblings are built on and
    would measure this check's idea of where the block ends.

    The state checks run against this box either way, which is the point
    at which this probe borrows somebody else's traffic; they are compared
    across the two drives rather than read, and see the check's own note
    for what a difference between them is allowed to mean.

    **Reached through the module rather than imported by name**, which is
    the one thing ``SNAG-ESTATE-013``'s check had to learn twice before it
    retired with its entry.  It imported ``ops_claims.EXPIRY_FORMAT`` by
    name, so the constant lived in two namespaces; a stand-in modelling a
    landed fix patched only the owner and passed against the code it was
    written to break — a guard asserting a *value* where it meant
    *provenance*.  ``ops_claims.check_all`` has exactly one home, so a
    stand-in cannot patch the wrong one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "STATUS.md"
        path.write_text(document, encoding="utf-8")
        try:
            return list(ops_claims.check_all(path)), ""
        except Exception as exc:  # noqa: BLE001 — a reader that raises is a reader that did not run
            return [], (
                f"ops_claims.check_all raised {exc.__class__.__name__}: {exc} — the reader "
                "this entry is about no longer runs over a document at all"
            )


def claim_text(claim: ops_claims.Claim) -> str:
    """Every word one claim puts in front of a reader, as one string."""
    parts = (
        claim.key,
        claim.subject,
        claim.kind,
        claim.documented,
        claim.measured,
        claim.verdict,
        claim.note,
        *claim.detail,
    )
    return " ".join(str(part) for part in parts if part)


def claim_projection(claims: Iterable[ops_claims.Claim]) -> dict[str, str | None]:
    """The part of a report that can only have come from the document.

    ``key`` is decided by which families ran and ``documented`` by what
    each read out of the region; both are answers about the block.
    ``measured``, ``verdict`` and ``note`` are answers about the box and
    are deliberately out, because two drives 0.4 s apart can honestly
    disagree about them — see the check's ``other`` branch.
    """
    return {claim.key: claim.documented for claim in claims}


@dataclass(frozen=True)
class SentenceReading:
    """What one unmarked sentence did to the report.

    Attributes:
        sentence: the specimen, as the entry writes it.
        added: keys the report gained when the sentence was added.
        removed: keys it lost.
        newly_read: keys whose ``documented`` went from nothing to
            something — a family that could not read the block before and
            can now.
        now_unreadable: keys whose ``documented`` went the other way.  The
            sentence collided with a figure the block already stated, and
            :func:`~sysadmin.ops_claims.read_claim` refuses two distinct
            matches rather than resolving them — so this is the same
            sentence being read, arriving as a refusal.
        moved: keys whose ``documented`` changed while both sides stated
            one.
        quoted: words the report carries that it could only have taken
            from the sentence.
        unquotable: the sentence has no word the baseline report does not
            already carry, so the quotation instrument cannot look at it
            and only the projection covers it.  Named rather than left to
            be inferred — ``ports_checked``'s rule, and the shape this
            entry is about.
        refusal: why the drive could not be made at all.
    """

    sentence: str
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    newly_read: tuple[str, ...] = ()
    now_unreadable: tuple[str, ...] = ()
    moved: tuple[str, ...] = ()
    quoted: tuple[str, ...] = ()
    unquotable: bool = False
    refusal: str = ""

    @property
    def visible(self) -> tuple[str, ...]:
        """Every way this sentence reached the report, in words.

        **Directional, and that is what separates the two branches.**  A
        sentence added to a block can only ever *change what of it can be
        read* — it cannot restate a figure the block already carries as a
        different figure.  So a key appearing, a key disappearing, a
        ``None -> value`` and a ``value -> None`` are all attributable to
        the sentence, and a figure that merely *moved* between two values
        is the box moving underneath the probe.
        """
        reasons = []
        if self.added:
            reasons.append(f"the report gained {', '.join(self.added)}")
        if self.removed:
            reasons.append(f"the report lost {', '.join(self.removed)}")
        if self.newly_read:
            reasons.append(f"{', '.join(self.newly_read)} now reads a figure out of the block")
        if self.now_unreadable:
            reasons.append(
                f"{', '.join(self.now_unreadable)} stopped reading the block — the sentence "
                "collides with a figure it already stated"
            )
        if self.quoted:
            reasons.append(f"the report quotes the sentence ({', '.join(self.quoted)})")
        return tuple(reasons)

    def line(self) -> str:
        """One evidence row."""
        if self.refusal:
            return f"{self.sentence!r}: not driven — {self.refusal}"
        if self.visible:
            return f"{self.sentence!r}: reached the report — {'; '.join(self.visible)}"
        if self.moved:
            return (
                f"{self.sentence!r}: no finding of its own, but {', '.join(self.moved)} "
                "moved between the two drives"
            )
        blind = " (no word the baseline lacks — projection only)" if self.unquotable else ""
        return f"{self.sentence!r}: absent from every family{blind}"


def witness_problem(claims: list[ops_claims.Claim]) -> str:
    """Why the marked half is not evidence that the region was read, or ``""``.

    **The whole design turns on this function.**  A reader that had
    stopped parsing the region — a moved heading, a
    :func:`~sysadmin.ops_claims.printed_region` returning ``None``, a
    module that no longer opens the file — reports the unmarked sentence
    *exactly* as a working reader does: absent from every family.  So the
    silence this check is looking for is only evidence when something in
    the same region would have forced a different observation, and the
    marked sentence is that something.

    Both halves of the convention are witnessed, because they can fail
    apart.  ``documented`` coming back as the figure the block states is
    :func:`~sysadmin.ops_claims.read_claim` reaching the prose; the
    absence of an ``unclaimed:routes`` finding is
    :func:`~sysadmin.ops_claims.read_markers` reaching the marker beside
    it.  A probe that checked only the first would call a broken marker
    reader a working one, and the marker half is the half the entry's two
    refused remedies would both have had to extend.

    **Established on the baseline alone, and re-witnessing each specimen
    was a defect a falsification found.**  The obvious version witnessed
    every drive, and a stand-in modelling a sentence that *collides* with
    the marked figure — :func:`~sysadmin.ops_claims.read_claim` refuses
    two distinct matches rather than resolving them — tripped that witness
    and came back ``unknown`` as *"the probe could not be driven"*.  The
    two documents differ by the sentence and by nothing else, so once the
    baseline has witnessed the reader, a witness that fails on the
    specimen is the **sentence being read**, not the reader breaking.
    That is the whole of :attr:`SentenceReading.now_unreadable`, and it is
    reachable by a landed fix as well as by a collision: a remedy that
    refused a region carrying an unmarked paragraph lands there exactly.
    """
    routes = next((claim for claim in claims if claim.key == "routes"), None)
    if routes is None:
        return "the baseline report has no 'routes' claim at all"
    if routes.documented != INVISIBLE_ROUTES:
        return (
            f"the baseline report read routes={routes.documented!r} where the specimen "
            f"states {INVISIBLE_ROUTES!r}"
        )
    if any(claim.key == "unclaimed:routes" for claim in claims):
        return (
            "the baseline report calls the specimen's routes figure unclaimed — the marker "
            "beside it was not read"
        )
    return ""


def check_unmarked_sentence_invisible() -> Measurement:
    """``SNAG-ESTATE-012`` — a block sentence with no pattern and no marker.

    **The twentieth check, and the second whose subject is this
    repository's own claims machinery** — ``SNAG-ESTATE-013``'s was the
    other, and the two are opposites.  That one drove a family that exists
    and asked whether it reads its input correctly (it did not: a zoneless
    instant was read as local, fixed 2026-08-28, and the check retired
    with the entry); this one asks whether an input reaches *any* family,
    and the answer the entry claims is that it reaches none.

    **It is a check that the invisibility holds, and never a marker built
    to close it.**  The entry names both obvious remedies and refuses both
    by name: requiring every blockquote paragraph to carry a marker turns
    the ranked recommendation and the blocked list into claims they are
    not, and a ``<!--check:none-->`` marker is one whose absence is
    indistinguishable from forgetting it — the thing it exists to detect.
    Rule 2 forbids this module authoring the document in any case, so what
    is measured is the mechanism as the entry describes it.

    **Rule 1, and the population is live rather than empty for once.**
    Today's block still carries such sentences, so a check counting them
    would return a number — and it would fall to zero the next time
    somebody reworded the block, reporting a fix that is a paragraph edit.
    What the entry claims is that nothing *reaches* such a sentence, so a
    specimen is built: a printed region carrying one sentence a pattern
    can reach, marked, and one sentence that is a claim to a human and
    matches nothing.

    **The absence is not the evidence — the marked half is.**  A reader
    that had stopped parsing the region at all reports the unmarked
    sentence exactly as a working reader does, so a probe asserting
    silence alone would report this entry holding hardest on the morning
    :func:`~sysadmin.ops_claims.printed_region` broke.
    :func:`witness_problem` is the discriminating observation, and it
    witnesses both halves of the convention because they fail apart.

    **Two instruments, because a fix can land in two shapes and each is
    invisible to the other.**  A remedy that reported *"blockquote
    paragraph 2 carries no marker"* names no sentence and would slip past
    a text search; a remedy that folded the sentence into an existing
    claim's note adds no key and would slip past a projection.  So the
    report is compared as a projection of what only the document decides —
    which keys ran, and what each read out of the region — and separately
    searched for words it could only have taken from the sentence.

    **A difference the sentence cannot explain is ``unknown``, never
    ``mismatch``.**  ``open_titles`` states its ``documented`` as *"N
    named"* over the live alert table, so two drives a second apart can
    honestly disagree about it, and a probe that read that as a landed fix
    would be reporting this repository's own traffic.  The direction rule
    is what makes the split safe rather than a shrug: a sentence added to
    a block can only make more of it readable, so ``None -> value`` is
    attributable to the sentence and ``value -> other value`` is not.

    The blind spot is stated rather than implied: a fix that changed an
    existing claim's *verdict* on account of the sentence while neither
    quoting it nor adding a key of its own is unreachable from here.  It
    is also close to unbuildable — a finding about a sentence that never
    names the sentence is a count that cannot name anything, which is
    ``SNAG-ESTATE-001``'s defect and the shape this whole convention was
    written against.
    """
    base = invisible_document()
    baseline, problem = ops_report(base)
    if problem:
        return Measurement("unknown", problem)
    blind = witness_problem(baseline)
    if blind:
        return Measurement(
            "unknown",
            f"{blind} — the marked half of the specimen is the only thing that can tell a "
            "reader which read nothing from one which read the region and found no claim, "
            "so the unmarked sentence's absence says nothing",
        )

    seen = frozenset(INVISIBLE_WORD_RE.findall(base)) | frozenset(
        word for claim in baseline for word in INVISIBLE_WORD_RE.findall(claim_text(claim))
    )
    before = claim_projection(baseline)

    readings: list[SentenceReading] = []
    for sentence in INVISIBLE_SENTENCES:
        claims, refusal = ops_report(invisible_document(sentence))
        if refusal:
            readings.append(SentenceReading(sentence, refusal=refusal))
            continue
        after = claim_projection(claims)
        shared = sorted(set(before) & set(after))
        text = " ".join(claim_text(claim) for claim in claims)
        distinctive = sorted(frozenset(INVISIBLE_WORD_RE.findall(sentence)) - seen)
        readings.append(
            SentenceReading(
                sentence,
                added=tuple(sorted(set(after) - set(before))),
                removed=tuple(sorted(set(before) - set(after))),
                newly_read=tuple(
                    key for key in shared if before[key] is None and after[key] is not None
                ),
                now_unreadable=tuple(
                    key for key in shared if before[key] is not None and after[key] is None
                ),
                moved=tuple(
                    key
                    for key in shared
                    if before[key] != after[key]
                    and before[key] is not None
                    and after[key] is not None
                ),
                quoted=tuple(word for word in distinctive if word in text),
                unquotable=not distinctive,
            )
        )

    detail = (
        f"witness: the marked half reads routes={INVISIBLE_ROUTES} and carries its marker, "
        f"so the reader parsed the region ({len(baseline)} claim(s))",
        *(reading.line() for reading in readings),
    )

    refused = [reading for reading in readings if reading.refusal]
    if refused:
        return Measurement(
            "unknown",
            "the specimen could not be driven for "
            f"{len(refused)} of {len(readings)} sentence(s): "
            + "; ".join(reading.refusal for reading in refused),
            detail,
        )
    reached = [reading for reading in readings if reading.visible]
    if reached:
        return Measurement(
            "mismatch",
            "a sentence carrying no pattern and no marker now reaches the report — "
            + "; ".join(
                f"{reading.sentence!r}: {'; '.join(reading.visible)}" for reading in reached
            ),
            detail,
        )
    if all(reading.unquotable for reading in readings):
        return Measurement(
            "unknown",
            "no specimen carries a word the baseline report does not already use, so the "
            "quotation instrument cannot look at any of them and only the projection is "
            "left — half the check's reach is gone and the silence is that much weaker",
            detail,
        )
    unstable = [reading for reading in readings if reading.moved]
    if unstable:
        return Measurement(
            "unknown",
            "the two drives disagreed about a figure the sentence cannot have moved "
            f"({', '.join(sorted({key for r in unstable for key in r.moved}))}) — the box "
            "changed underneath the probe, so this run cannot isolate the sentence",
            detail,
        )
    return Measurement("match", "", detail)


#: ``SNAG-SVC-002``'s synthetic subject: a scheduled job that is an agent
#: *and* a systemd timer.  The name is shared across both drives so the
#: report reads as one subject, and **the sharing is not what makes it
#: one** — the two families would key on different strings on a real box
#: (``AGENT_NAMES`` against a ``services.yaml`` entry).  What makes it one
#: subject is that both drives are handed the same fact: one schedule, one
#: last-run instant, one cadence.
TIMER_AGENT_NAME = "snagcheck_timer_agent"

#: Firings the probe records before the schedule goes quiet.  Derived from
#: the timer module's own floor rather than restated beside it:
#: :func:`~sysadmin.monitor.service_recommendations._observed_cadence`
#: refuses to claim a cadence below ``MIN_CADENCE_SAMPLES + 1`` fires, and
#: one spare keeps a single discarded interval from taking the probe under
#: that floor.  ``max_priority_for`` against ``PRIORITY_MAP``'s treatment.
PROBE_FIRE_SPARE = 1

#: Multiples of ``self_monitor.escalate_after_hours`` between the fresh
#: drive and the aged one.  **Derived from the sibling family's own gap**,
#: which is the whole point: a rung on the advice family would have
#: nothing else to derive its own gap from — ``stalls.py``'s is the only
#: escalation gap on this box, and Session 53's ``reminder_hours`` already
#: reuses it — so the aged drive is taken two of them past the fresh one
#: and a ladder using that gap cannot sit between the two.
PROBE_LADDER_MULTIPLE = 2.0

#: How far past the later of the two thresholds the *fresh* fault stands:
#: one check interval, the smallest amount by which this monitor is
#: capable of observing a threshold crossed at all.
#:
#: **It is small on purpose, and the first draft had it at one cadence,
#: where the ladder half of this check was blind to most of what it was
#: looking for.**  A rung on the advice family would have to run its clock
#: from the fault's own age — the family is stateless and recomputed per
#: request, so unlike ``stalls.py`` it has no "when the alarm rang" to
#: measure from.  The two drives therefore straddle a rung only when its
#: gap falls in ``[overshoot, overshoot + 2 x escalate_after_hours)``, and
#: the arithmetic is exact: at one cadence that window is **24h to 72h**
#: on this box, so every rung shorter than a day read loud at *both*
#: drives, the check saw no movement, and it passed against code
#: deliberately given a ladder.  At one check interval the window is **5
#: minutes to 48 hours**, and a rung below the monitor's own resolution is
#: one it could not observe in any case.  Found by driving a stand-in that
#: added a rung at half the escalation gap; the two figures are printed by
#: ``tests/test_snag_claims.py`` rather than asserted here, since both are
#: derived from config and would move with it.
PROBE_FRESH_OVERSHOOT_INTERVALS = 1

#: The two modules the entry names, as import targets.  Read as *modules*
#: rather than as file paths because that is what an importer names, and
#: the failing shape this looks for — a third module composing the two —
#: is invisible in either file.
STALL_MODULE = "sysadmin.monitor.stalls"
TIMER_ADVICE_MODULE = "sysadmin.monitor.service_recommendations"


def imported_modules(path: Path) -> set[str]:
    """Every module one file imports, dotted, both statement forms.

    The exact opposite selection from :func:`_names_used`, and
    deliberately: that function excludes imports because a name in an
    import list is not a *reader*, and this one keeps only imports because
    a module that has wired two families together has to have named both
    of them at the top of the file.

    Absolute imports only.  A relative one cannot be resolved to a dotted
    name without knowing the package root, and this repository writes none
    — so the alternative to skipping them is guessing.
    """
    tree = _parse(path)
    if tree is None:
        return set()
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module)
            found.update(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def importers_of(module: str, paths: Iterable[Path]) -> list[Path]:
    """The files importing ``module`` or anything under it."""
    return [
        path
        for path in paths
        if any(name == module or name.startswith(f"{module}.") for name in imported_modules(path))
    ]


def timer_agent_series(
    cadence: float,
    fires: int,
    silent_seconds: float,
    check_interval_seconds: int,
    last_result: str,
    now: datetime,
) -> TimerSeries:
    """One timer's observations: ``fires`` firings a cadence apart, then quiet.

    Points are spaced at the *live* check interval, which is not a
    decoration:
    :func:`~sysadmin.monitor.service_recommendations._series_holes` calls
    any gap wider than ``SERIES_HOLE_FACTOR`` intervals a hole in the
    monitor's series and discards every cadence sample spanning it, so a
    series sampled more coarsely than the box samples would yield no
    cadence at all and the probe would report silence it had manufactured.
    """
    from sysadmin.monitor.service_recommendations import TimerPoint, TimerSeries

    start = now - timedelta(seconds=cadence * (fires - 1) + silent_seconds)
    fire_at = [start + timedelta(seconds=cadence * i) for i in range(fires)]
    step = timedelta(seconds=check_interval_seconds)

    points: list[TimerPoint] = []
    token = 0
    pending = 1  # the first point cannot be a fire — there is nothing before it
    at = start
    while at <= now:
        while pending < len(fire_at) and at >= fire_at[pending]:
            token += 1
            pending += 1
        points.append(
            TimerPoint(checked_at=at, last_run=f"trigger-{token}", last_result=last_result)
        )
        at += step
    return TimerSeries(service=TIMER_AGENT_NAME, unit=f"{TIMER_AGENT_NAME}.timer", points=points)


def timer_agent_rows(
    series: TimerSeries, check_interval_seconds: int, now: datetime
) -> list[ServiceRecommendationInfo]:
    """What the advice family says about one timer series.

    Reached through :func:`~sysadmin.monitor.service_recommendations.recommend`
    rather than through ``_timer_rows``, so the confidence gate is on the
    path.  ``timer_stale`` is ``RATE_ARGUED`` and is withheld below
    ``confidence: high``, and the score is **earned** from a full clean
    health window by the real scorer rather than default-constructed —
    a ``ReliabilityScore(service=…)`` asserts the confidence this row
    needs instead of demonstrating it, and the probe would then go on
    passing on the day the gate moved.
    """
    from sysadmin.monitor.reliability import HealthPoint, score_service
    from sysadmin.monitor.service_recommendations import recommend

    config = get_config()
    window_days = config.agents.sysadmin.reliability.window_days
    health = [
        HealthPoint(checked_at=now - timedelta(seconds=check_interval_seconds * i), status="ok")
        for i in range(int(window_days * 86400 / check_interval_seconds))
    ]
    score = score_service(
        TIMER_AGENT_NAME,
        health,
        window_days=window_days,
        check_interval_seconds=check_interval_seconds,
        now=now,
    )
    report = recommend(
        [score],
        config.agents.sysadmin.service_actions,
        timers=[series],
        check_interval_seconds=check_interval_seconds,
        now=now,
    )
    return report.recommendations


@dataclass(frozen=True)
class TimerAgentReading:
    """One schedule, put to both families in each one's own vocabulary.

    Attributes:
        cadence_seconds: the subject's schedule.
        stall_window_seconds: ``interval x stall_grace_multiplier``,
            floored — when the stall family calls it stalled.
        timer_threshold_seconds: ``cadence x timer_stale_multiplier`` —
            when the advice family calls it stale.  Equal to the stall
            window by construction today, which is the entry's stated
            mitigation and is reported rather than assumed.
        silent_seconds: how long the fresh fault has stood.
        overshoot_seconds: by how much that clears the later of the two
            thresholds.  Carried rather than recomputed for the evidence
            line, because both thresholds render as the same round figure
            as the elapsed does and a reader would otherwise have no way
            to see that the fault is past them at all.
        stall_title: the row the stall family raised, or ``""``.
        stall_severity: the rung it opened on.
        escalated_severity: the rung it moved to once the quiet row had
            stood ``escalate_after_hours``.
        timer_title: the row the advice family raised, or ``""``.
        timer_severity: its severity.
        aged_timer_severity: the same family's severity once the fault had
            stood :data:`PROBE_LADDER_MULTIPLE` further escalation gaps.
        aged_timer_rows: how many rows the aged drive produced, so a
            second row appearing beside the first is not read as silence.
        escalate_after_hours: the sibling family's gap, echoed so the
            evidence line can name the span the aged drive was taken over
            rather than leaving a reader to reconstruct it.
        joint_importers: modules in ``sysadmin/`` importing both families.
    """

    cadence_seconds: float
    stall_window_seconds: float
    timer_threshold_seconds: float
    silent_seconds: float
    overshoot_seconds: float
    stall_title: str
    stall_severity: str
    escalated_severity: str
    timer_title: str
    timer_severity: str
    aged_timer_severity: str
    aged_timer_rows: int
    escalate_after_hours: float
    joint_importers: tuple[str, ...]

    @property
    def both_speak(self) -> bool:
        return bool(self.stall_title) and bool(self.timer_title)

    @property
    def timer_has_ladder(self) -> bool:
        """The advice family's rung moved with the age of the fault."""
        return self.aged_timer_severity != self.timer_severity


def timer_agent_reading() -> tuple[TimerAgentReading | None, str]:
    """Drive both families over one synthetic timer-backed agent.

    Two witnesses first, because a family that has gone silent and a
    family the probe can no longer reach report identically — Session
    98's rule, and this check needs it twice because it drives two
    modules.  A *fresh* schedule must come back not-stalled, which is the
    stall side reading the subject rather than defaulting; and a timer
    still firing whose last run **failed** must yield a ``timer_failed``
    row, which is the advice side reachable through the same call, the
    same series shape and the same confidence gate that
    ``timer_stale`` has to clear.
    """
    from sysadmin.core.models.agent_run import AgentRun
    from sysadmin.monitor import stalls
    from sysadmin.monitor.self_monitor import AgentSchedule, stall_window_seconds, summarise_agent
    from sysadmin.monitor.service_recommendations import MIN_CADENCE_SAMPLES

    config = get_config()
    self_monitor = config.self_monitor
    advice = config.agents.sysadmin.service_actions
    check_interval = config.agents.sysadmin.health_check_interval_seconds

    # The subject is a daily job, which is `file_organiser`'s and
    # `service_discovery`'s interval and the cadence every daily timer on
    # this box derives.  Read from config rather than written here: a
    # constant would go on describing a schedule nobody runs.
    cadence = float(config.agents.file_organiser.scan_interval_hours * 3600)
    if cadence <= 0 or check_interval <= 0:
        return None, (
            f"the probe's schedule is not positive (cadence {cadence}s, check interval "
            f"{check_interval}s) — the synthetic subject cannot be built from this config"
        )

    now = datetime.now(UTC)
    schedule = AgentSchedule(
        name=TIMER_AGENT_NAME,
        enabled=True,
        interval_seconds=int(cadence),
        job_id=f"{TIMER_AGENT_NAME}_job",
    )
    stall_window = stall_window_seconds(schedule, self_monitor)
    timer_threshold = cadence * advice.timer_stale_multiplier
    overshoot = float(check_interval * PROBE_FRESH_OVERSHOOT_INTERVALS)
    silent = max(stall_window, timer_threshold) + overshoot

    def ran(seconds_ago: float) -> list[AgentRun]:
        return [
            AgentRun(
                agent=TIMER_AGENT_NAME,
                run_type="scheduled",
                status="completed",
                duration_seconds=1.0,
                started_at=now - timedelta(seconds=seconds_ago),
            )
        ]

    fresh_entry = summarise_agent(schedule, ran(cadence), self_monitor, now)
    if fresh_entry["stalled"]:
        return None, (
            "a schedule that ran one cadence ago is already reported stalled — the stall "
            "side of the probe cannot tell a working schedule from a stopped one, so its "
            "silence about anything would say nothing"
        )

    fires = MIN_CADENCE_SAMPLES + 1 + PROBE_FIRE_SPARE
    witness = timer_agent_rows(
        timer_agent_series(cadence, fires, 0.0, check_interval, "exit-code", now),
        check_interval,
        now,
    )
    if not any(row.kind == "timer_failed" for row in witness):
        return None, (
            "a timer still firing whose last run failed produced no timer_failed row, so "
            "the advice family is not reachable through this probe at all — its timer half "
            "may have been removed, which is the entry's own fix and is worth a look, or "
            "this probe's series may no longer satisfy it; the two are indistinguishable "
            "from here, and a timer_stale row's absence below would be the probe's rather "
            "than the box's either way"
        )

    stalled_entry = summarise_agent(schedule, ran(silent), self_monitor, now)
    raised = stalls.evaluate(
        [stalled_entry] if stalled_entry["stalled"] else [],
        {},
        escalate_after_hours=self_monitor.escalate_after_hours,
        now=now,
    )
    escalated = stalls.evaluate(
        [stalled_entry] if stalled_entry["stalled"] else [],
        {
            TIMER_AGENT_NAME: stalls.OpenStall(
                alert_id=None,
                severity=raised[0].severity if raised else "warning",
                created_at=now - timedelta(hours=self_monitor.escalate_after_hours + 1),
            )
        },
        escalate_after_hours=self_monitor.escalate_after_hours,
        now=now,
    )

    fresh_rows = timer_agent_rows(
        timer_agent_series(cadence, fires, silent, check_interval, "success", now),
        check_interval,
        now,
    )
    stale = next((row for row in fresh_rows if row.kind == "timer_stale"), None)
    aged_silent = silent + self_monitor.escalate_after_hours * 3600 * PROBE_LADDER_MULTIPLE
    aged_rows = [
        row
        for row in timer_agent_rows(
            timer_agent_series(cadence, fires, aged_silent, check_interval, "success", now),
            check_interval,
            now,
        )
        if row.kind == "timer_stale"
    ]

    sources = [
        path
        for path in _python_files((REPO_ROOT / "sysadmin",))
        if path != REPO_ROOT / "sysadmin" / "snag_claims.py"
    ]
    joint = sorted(
        {
            _rel(path)
            for path in importers_of(STALL_MODULE, sources)
            if path in set(importers_of(TIMER_ADVICE_MODULE, sources))
        }
    )

    return (
        TimerAgentReading(
            cadence_seconds=cadence,
            stall_window_seconds=stall_window,
            timer_threshold_seconds=timer_threshold,
            silent_seconds=silent,
            overshoot_seconds=overshoot,
            stall_title=raised[0].title if raised else "",
            stall_severity=raised[0].severity if raised else "",
            escalated_severity=escalated[0].severity if escalated else "",
            timer_title=stale.title if stale else "",
            timer_severity=stale.severity if stale else "",
            aged_timer_severity=aged_rows[0].severity if aged_rows else "",
            aged_timer_rows=len(aged_rows),
            escalate_after_hours=self_monitor.escalate_after_hours,
            joint_importers=tuple(joint),
        ),
        "",
    )


def check_timer_agent_two_owners() -> Measurement:
    """``SNAG-SVC-002`` — one schedule, judged by two families that do not know each other.

    **The twenty-first check, and the third built on a synthetic subject.**
    :func:`check_dropin_blind_spot` builds a drop-in and
    :func:`check_unmarked_sentence_invisible` builds a block sentence;
    this builds an *agent whose schedule is a systemd timer*, which is the
    one thing on this box that does not exist.

    **Rule 1 is the whole difficulty here, and it is why this entry has
    been runner-up three times without being taken.**  The obvious check
    measures the disjointness the entry reports — no agent on this box is
    a timer, so no subject reaches both families — and that is a property
    of *this box*, not of the design.  A rewritten ``services.yaml`` or a
    scheduled job moved to a ``oneshot`` + ``.timer``, which
    ``monitorable-project.md`` requires of every new one, would flip such
    a check to "refuted" with nobody having touched either module; the
    entry says so in its own second bullet.  What the entry *claims* is a
    mechanism — that a timer-backed schedule would be spoken about by both
    families at once — so the mechanism is reproduced rather than looked
    for.

    **One fact, two vocabularies, and the shared name is not the point.**
    The subject is a daily schedule whose last run was long enough ago to
    cross both thresholds.  It is handed to
    :func:`~sysadmin.monitor.self_monitor.summarise_agent` as an agent
    that has not run, and to
    :func:`~sysadmin.monitor.service_recommendations.recommend` as a timer
    whose ``LastTriggerUSec`` stopped moving.  Both drives use one name so
    the evidence reads as one subject; on a real box the two families
    would key on different strings, and what makes it one subject is the
    single schedule and the single last-run instant behind both.

    **The two thresholds are the same number, and that is derived rather
    than arranged.**  ``timer_stale_multiplier`` *is*
    ``stall_grace_multiplier``'s 3.0, imported as an argument and
    documented as such in ``config.py`` — the entry's own stated
    mitigation.  So one elapsed value crosses both, which is not a
    convenience of the probe but the reason the two families speak
    *simultaneously* rather than merely both being capable of speaking.
    Both are reported, so the day they diverge the evidence says so.

    **Four claims, three instruments, and the halves are reported apart
    because two of them refute the entry in opposite directions.**

    1. *Both families speak.*  The mechanism.  One of them going silent
       for this subject is the fix the entry names — "give one module the
       question and the other the subject" — and the note says which
       ceded.
    2. *The advice family's rung does not move with the age of the
       fault.*  Driven at a fault that has stood
       :data:`PROBE_LADDER_MULTIPLE` further escalation gaps, against a
       stall row that goes ``warning`` -> ``critical`` over the same span.
       A rung appearing here is the fix the entry **forbids** by name
       ("that is the second owner arriving with more machinery"), and a
       check that could not see it would let the wrong fix land in
       silence.  This is the half that cannot be inferred from the first:
       both families would go on speaking either way.
    3. *Nothing joins them.*  The entry's headline is that neither knows
       the other exists, and its recommended fix is a caller feeding
       ``_observed_fires`` into the stall family — which need not touch
       either file.  So the instrument is the *importer sets*: today they
       are disjoint, ``monitor/agent.py`` against ``health_review.py``,
       ``reliability_history.py`` and ``routers/services.py``.  A module
       importing both is the shape every fix in that direction has to
       take, whichever file it lands in.
    4. Rule 7 for the fourth time: ``service_recommendations.py`` already
       contains the word ``stalls``, in ``_timer_stale_row``'s own
       docstring, so a grep reports the cross-reference as already
       existing.  A docstring is an ``ast.Constant`` and an import walk
       never sees it.

    **This module is excluded from its own population, which is not
    bookkeeping.**  Driving both families means importing both, so the
    only thing in this repository that knows the two exist is the check
    reporting that nothing does.

    **What is out of reach, stated rather than implied.**  A fix that
    taught ``recommend`` to decline a timer whose service is an agent
    would need to be *told* which services those are, and this probe
    declares nothing of the kind — so it would go on producing a
    ``timer_stale`` row here and half 1 would read unchanged.  Half 3 is
    what covers that case: no such fix can be written without one module
    naming both families.
    """
    reading, problem = timer_agent_reading()
    if reading is None:
        return Measurement("unknown", problem)

    detail = (
        f"subject: a schedule every {humanise_hours(reading.cadence_seconds / 3600)}, quiet "
        f"for {humanise_hours(reading.silent_seconds / 3600)} — "
        f"{reading.overshoot_seconds:.0f}s past the later threshold",
        f"thresholds: stall window {humanise_hours(reading.stall_window_seconds / 3600)}, "
        f"timer staleness {humanise_hours(reading.timer_threshold_seconds / 3600)}",
        f"stalls.py: {reading.stall_title or '(silent)'} "
        f"[{reading.stall_severity or '-'} -> {reading.escalated_severity or '-'}]",
        f"service_recommendations.py: {reading.timer_title or '(silent)'} "
        f"[{reading.timer_severity or '-'}]",
        f"the same timer fault aged a further "
        f"{humanise_hours(reading.escalate_after_hours * PROBE_LADDER_MULTIPLE)}: "
        f"{reading.aged_timer_rows} row(s) at "
        f"[{reading.aged_timer_severity or '-'}]",
        "modules importing both families: "
        + (", ".join(reading.joint_importers) if reading.joint_importers else "none"),
    )

    faults: list[str] = []
    if not reading.stall_title and not reading.timer_title:
        faults.append(
            "neither family speaks about the subject any more — the entry describes two "
            "owners of one question and there are now none, which is a different fault "
            "rather than this one fixed"
        )
    elif not reading.timer_title:
        faults.append(
            "the advice family no longer speaks about a timer-backed schedule while the "
            "stall family does — the entry's own fix, with the question left where the "
            "ladder already is"
        )
    elif not reading.stall_title:
        faults.append(
            "the stall family no longer speaks about the subject while the advice family "
            "does — the entry's fix taken in the direction it argues against, since the "
            "ladder is the expensive half and it lives in stalls.py"
        )
    if reading.timer_has_ladder:
        faults.append(
            f"the timer_stale row moved {reading.timer_severity} -> "
            f"{reading.aged_timer_severity} as the fault aged — this family has a rung now, "
            "which is the fix the entry forbids by name rather than the one it asks for"
        )
    if reading.joint_importers:
        faults.append(
            f"{', '.join(reading.joint_importers)} imports both families — something joins "
            "them now, so the entry's *neither knows the other exists* no longer holds"
        )

    if faults:
        return Measurement("mismatch", "; ".join(faults), detail)
    return Measurement("match", "", detail)


#: ``SNAG-ESTATE-007``'s two engines, which is where a fix to either half
#: would land: the queue's psycopg pool and the project domain's
#: SQLAlchemy engine.  Both are named for :data:`ESTATE_NUDGE_MODULES`'
#: reason — a fix landing in one says nothing about the other, and this
#: entry is precisely a claim that the two disagree.  ``api.py`` is named
#: as well because the surface is what is measured and the route's
#: serialiser is the third place a rendering could be decided.
ESTATE_QUEUE_MODULES = (
    Path("estate_service") / "db.py",
    Path("estate_service") / "api.py",
    Path("estate_service") / "projects" / "db.py",
)

#: Two instants six months apart, and the pair is the instrument rather
#: than a redundancy.
#:
#: The entry quotes one rendered string, ``"2026-08-16T09:31:01+01:00"``,
#: and a check reading one instant is a check that **agrees with itself
#: only in summer**: this box runs ``Europe/London``, which renders
#: ``+00:00`` from late October to late March, so a single-instant probe
#: would report the entry refuted every winter with nothing having
#: changed and re-report it true every spring.  That is rule 1's warning
#: arriving as a *seasonal* population rather than a countable one, and
#: it was found by rendering both instants rather than by reasoning about
#: the zone.
#:
#: A session pinned to UTC renders every instant at ``+00:00`` by
#: construction, so "both offsets are zero" is a property of the
#: *connection* and not of the calendar.  The summer instant is the
#: entry's own, to the second, so the evidence line can be read against
#: the sentence that filed it.
QUEUE_WINTER_INSTANT = "2026-01-15 09:31:01+00"
QUEUE_SUMMER_INSTANT = "2026-08-16 09:31:01+00"

#: The two ``timestamptz`` fields ``active_lease`` publishes.  Read from
#: the payload rather than typed as a schema: the probe seeds one row and
#: these are the columns the surface hands back, so a field that stops
#: being published is an absence the check reports rather than a
#: ``KeyError`` inside it.
QUEUE_LEASE_STAMPS = ("granted_at", "hold_deadline")

#: ``pg_settings.source`` values meaning *this connection inherited the
#: box's timezone*.  The distinction is the entry's cause, driven: a
#: connection that asked for a zone reports ``client`` — which is exactly
#: what ``options: -c timezone=utc`` in the pool's kwargs produces, and
#: therefore what their fix would produce — and one that took the
#: cluster's default reports ``configuration file``.  Measured against
#: both connection shapes before it was written down.
QUEUE_INHERITED_SOURCES = frozenset({"default", "configuration file"})

#: ``pg_settings.source`` when a connection asked for the setting itself.
QUEUE_DECLARED_SOURCE = "client"

#: The probe handed to :func:`estate_probe`.  It builds a lease the
#: surface can publish, drives the estate's own ``Arbiter.invariants()``
#: and then the route object mounted at the queue's published path, and
#: hands back the strings that came out alongside the timezone reading
#: that says where they came from.
#:
#: **Nothing of the estate's is read or written, and that is a rule
#: rather than a courtesy.**  ``create_pool`` is a factory taking a DSN,
#: so it is pointed at *this* repository's database — the estate rules
#: forbid one application reading another's, not even once, and a check
#: that ran at both ends of every sitting would be the most regular
#: breach of it on the box.  The substitution is sound only while the
#: timezone is a cluster-wide setting, which is not assumed: ``source``
#: reads ``configuration file`` when it is, and ``database`` or ``user``
#: when it is not, and the caller sends the second case back as
#: ``unknown``.  So the reading that discriminates cause from fix is the
#: same one that validates the stand-in.
#:
#: **Nothing private is touched.**  ``create_pool``, ``Arbiter``,
#: ``create_app``, ``load_settings``, ``UserSystemd`` and
#: ``create_engine_and_session`` are theirs and public; ``_public`` — the
#: serialiser that renders the wire string — is not, and is reached only
#: by *calling the route mounted at the published path*, which is
#: Session 87's rule read past the symbol names it was written about.
#: The path comes from :data:`sysadmin.estate.client.SURFACE_PATHS`,
#: this repository's own record of the surface it already pulls hourly,
#: rather than being typed here a second time.
#:
#: ``UserSystemd`` is constructed with a runner that raises, so the probe
#: **cannot** stop or start a unit even if a future ``invariants()``
#: grew a call that tried; and ``sampler`` is a constant, so no GPU
#: counter is read.  The lease lives in a ``TEMPORARY`` table, which
#: leaves this repository's database exactly as it found it without
#: needing a rollback anybody could forget.  It is deliberately **this
#: module's** fixture and not their ``schema.sql``: applying real DDL
#: here to get a faithful table would write the estate's schema into a
#: database this repository owns the moment a search-path assumption
#: slipped, and a query that outgrows the fixture fails loudly into
#: ``unknown`` instead.
QUEUE_TIMEZONE_PROBE = '''\
import asyncio, dataclasses, json, sys
sys.path.insert(0, {service!r})
from estate_service.api import create_app
from estate_service.arbiter import Arbiter
from estate_service.config import load_settings
from estate_service.db import create_pool
from estate_service.projects.db import create_engine_and_session
from estate_service.systemd import UserSystemd
from sqlalchemy import text

DSN = {dsn!r}
WINTER = {winter!r}
SUMMER = {summer!r}
ROUTE = {route!r}
STAMPS = list({stamps!r})

SETTING = "SELECT setting, source FROM pg_settings WHERE name = 'TimeZone'"
FIXTURE = (
    "CREATE TEMPORARY TABLE gpu_leases ("
    " id bigint, profile text, requester text, state text,"
    " requested_at timestamptz, granted_at timestamptz, hold_deadline timestamptz)"
)
SEED = (
    "INSERT INTO gpu_leases"
    " (id, profile, requester, state, requested_at, granted_at, hold_deadline)"
    " VALUES (1, 'snagcheck', 'snagcheck', 'granted',"
    " CAST(%s AS timestamptz), CAST(%s AS timestamptz), CAST(%s AS timestamptz))"
)
PAIR = (
    "SELECT CAST(:winter AS timestamptz) AS granted_at,"
    " CAST(:summer AS timestamptz) AS hold_deadline"
)


async def refuse(*args, **kwargs):
    """The probe never drives systemd, and cannot."""
    raise RuntimeError("the snag check never runs systemctl")


def rendered(value):
    """Whatever the surface published, as the string a consumer reads."""
    return value if isinstance(value, str) else value.isoformat()


async def main():
    out = {{"problem": ""}}
    settings = dataclasses.replace(load_settings(), db_dsn=DSN)
    pool = create_pool(DSN)
    await pool.open(wait=True, timeout=10)
    try:
        async with pool.connection() as conn:
            row = await (await conn.execute(SETTING)).fetchone()
            out["queue_setting"], out["queue_source"] = row["setting"], row["source"]
            await conn.execute(FIXTURE)
            await conn.execute(SEED, (SUMMER, WINTER, SUMMER))
        arbiter = Arbiter(
            pool,
            {{}},
            UserSystemd(runner=refuse),
            gpu_pci_slot=settings.gpu_pci_slot,
            gpu_busy_threshold=settings.gpu_busy_threshold,
            sampler=lambda: None,
        )
        lease = (await arbiter.invariants()).get("active_lease")
        if lease is None:
            out["problem"] = "lease_invisible"
            print(json.dumps(out))
            return
        out["arbiter"] = {{name: rendered(lease[name]) for name in STAMPS if name in lease}}
        app = create_app(settings, arbiter=arbiter)
        endpoint = None
        for route in app.routes:
            if getattr(route, "path", None) == ROUTE:
                endpoint = route.endpoint
        if endpoint is None:
            out["problem"] = "route_absent"
            print(json.dumps(out))
            return
        async with app.router.lifespan_context(app):
            served = await endpoint()
        active = (served or {{}}).get("active_lease") or {{}}
        out["served"] = {{name: rendered(active[name]) for name in STAMPS if name in active}}
    finally:
        await pool.close()

    engine, _ = create_engine_and_session(DSN)
    try:
        async with engine.connect() as conn:
            row = (await conn.execute(text(SETTING))).mappings().one()
            out["sibling_setting"], out["sibling_source"] = row["setting"], row["source"]
            row = (
                await conn.execute(text(PAIR), {{"winter": WINTER, "summer": SUMMER}})
            ).mappings().one()
            out["sibling"] = {{name: rendered(row[name]) for name in STAMPS if name in row}}
    finally:
        await engine.dispose()
    print(json.dumps(out))


asyncio.run(main())
'''


#: The queue surface's published path comes from this repository's own
#: record of the surfaces it already pulls hourly, never typed a second
#: time here: the estate judge would stop reading a moved path while this
#: check went on driving the old one, which is two statements of one fact
#: that can disagree — ``SNAG-DB-003``'s shape arriving in a route.
def queue_route() -> str:
    """The queue surface's path, from :data:`sysadmin.estate.client.SURFACE_PATHS`."""
    from sysadmin.estate.client import SURFACE_PATHS

    return SURFACE_PATHS["queue_invariants"]


def libpq_dsn(url: str) -> str:
    """A SQLAlchemy URL as the libpq conninfo psycopg's pool wants.

    The estate's own ``sqlalchemy_dsn`` converts in the other direction
    and this is its inverse, done with SQLAlchemy's parser rather than a
    string edit: ``config.database.sync_url`` names ``psycopg2``, which
    is this repository's sync driver and not a wire format, and handing
    it to ``create_pool`` would fail on the driver name before any
    timezone was read.
    """
    return make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)


@dataclass(frozen=True)
class StampReading:
    """One surface's rendering of the probe's two instants.

    Attributes:
        rendered: what the surface published, per field, verbatim.
        offsets: the UTC offset each field carried, in seconds.
        zoneless: fields the surface published with no offset at all.
    """

    rendered: dict[str, str]
    offsets: dict[str, int]
    zoneless: tuple[str, ...]

    @property
    def complete(self) -> bool:
        """Both instants came back, and both carried an offset.

        The pair *is* the instrument, so a reading holding half of it is
        not a weaker reading — it is a different one.
        """
        return set(self.offsets) == set(QUEUE_LEASE_STAMPS)

    @property
    def stamps_utc(self) -> bool:
        """**Both** instants came back at a zero offset.

        The completeness half is load-bearing rather than defensive, and
        a stand-in found that out: a surface publishing only
        ``granted_at`` satisfies *every offset is zero* through a
        ``Europe/London`` connection, because the winter instant renders
        ``+00:00`` there — which is the seasonal defect
        :data:`QUEUE_WINTER_INSTANT` exists to prevent, arriving by a
        dropped field instead of by the calendar.  A session pinned to
        UTC agrees with itself in January and in August; one that was
        only ever asked about January has not been asked.
        """
        return self.complete and set(self.offsets.values()) == {0}

    def render(self) -> str:
        """The published strings, in the order the surface names them."""
        return ", ".join(f"{name} {value}" for name, value in self.rendered.items()) or "nothing"


def stamp_reading(value: object) -> StampReading | None:
    """One surface's published instants, or ``None`` when it published none.

    Tolerant for :func:`_probe_names`' reason — the payload is another
    repository's, so a field that has stopped being a parseable instant
    is carried as *zoneless* or dropped rather than raised over.  The two
    are kept apart because they mean opposite things: a dropped field is
    a surface that stopped publishing it, and a zoneless one is a surface
    still publishing it with the offset removed, which is neither of the
    two renderings this entry compares and must not be read as either.
    """
    if not isinstance(value, dict):
        return None
    rendered: dict[str, str] = {}
    offsets: dict[str, int] = {}
    zoneless: list[str] = []
    for name in QUEUE_LEASE_STAMPS:
        published = value.get(name)
        if not isinstance(published, str):
            continue
        rendered[name] = published
        try:
            moment = datetime.fromisoformat(published)
        except ValueError:
            zoneless.append(name)
            continue
        offset = moment.utcoffset()
        if offset is None:
            zoneless.append(name)
            continue
        offsets[name] = int(offset.total_seconds())
    if not rendered:
        return None
    return StampReading(rendered, offsets, tuple(zoneless))


def zone_stamps_utc(name: str) -> bool | None:
    """Would a session in this named zone render both instants at ``+00:00``?

    Derived rather than compared against a vocabulary.  ``"UTC"``,
    ``"Etc/UTC"`` and ``"utc"`` are three spellings PostgreSQL will
    return for one setting, and a list of the ones somebody thought of is
    :mod:`sysadmin.core.logging_setup`'s ``syslog_priority`` written the
    way that module refuses to write it — so the name is *resolved* and
    the same two instants are put through it.  ``None`` when the zone
    will not resolve at all, which is a reading rather than a default:
    PostgreSQL and :mod:`zoneinfo` share the IANA database, so a name
    neither can place is one this check has no business interpreting.

    This is what separates *the fix landed above the connection* from
    *the box's default moved*, and the two are indistinguishable at the
    wire: both publish ``+00:00`` twice.  What tells them apart is that
    the connection is still in a local zone in the first case.
    """
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        zone = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return None
    return all(
        datetime.fromisoformat(instant).astimezone(zone).utcoffset() == timedelta(0)
        for instant in (QUEUE_WINTER_INSTANT, QUEUE_SUMMER_INSTANT)
    )


def live_queue_lease() -> str:
    """What the running 8400 surface says about a granted lease, in words.

    **Evidence, never the verdict** — rule 1, and this entry is where the
    distinction is cheapest to get wrong.  Its own body says
    ``active_lease`` has read ``null`` on every occasion anyone has
    looked, so a check that measured the live surface would be measuring
    whether somebody happens to hold the GPU, which is a fact about the
    afternoon rather than about how the estate stamps a timestamp.  It is
    read because the entry states it and it is the number that moves: the
    day a lease is live, the rendering the entry describes is visible on
    the real wire and the line below quotes it.

    This is the estate's **API**, which is the one way the estate rules
    permit data to cross — and it is a surface this repository already
    pulls hourly, so the path and the base URL come from
    :mod:`sysadmin.estate.client` and the config rather than being typed
    here.  Every failure is a sentence: 8400 being down is not this
    entry's business, and :mod:`sysadmin.estate.client`'s own docstring
    refuses to judge it.
    """
    import httpx

    base = get_config().agents.estate_judge.base_url
    url = f"{base.rstrip('/')}{queue_route()}"
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:  # noqa: BLE001 — the live surface is evidence, never a gate
        return f"the live queue surface was not read ({exc.__class__.__name__}) — evidence only"
    if not isinstance(payload, dict):
        return "the live queue surface answered something that is not an object"
    lease = payload.get("active_lease")
    if lease is None:
        return (
            "live population: active_lease is null, as the entry says it has been on every "
            "occasion anyone has looked"
        )
    reading = stamp_reading(lease)
    if reading is None:
        return "live population: a lease is granted and publishes neither timestamp"
    return f"live population: a lease is granted, and the wire carries {reading.render()}"


def check_queue_stamps_local() -> Measurement:
    """``SNAG-ESTATE-007`` — one estate surface renders a timestamp locally.

    ``GET :8400/api/queue/invariants`` publishes ``active_lease`` with
    ``granted_at`` and ``hold_deadline`` rendered in the connection's
    timezone, which on this box is ``Europe/London``; the three project
    and audit surfaces render ``+00:00``.  Same process, same database,
    two renderings — and the cause is one ``kwargs`` entry, because
    ``estate_service/projects/db.py`` builds its engine with
    ``connect_args={"options": "-c timezone=utc"}`` and the queue's pool
    passes only ``row_factory``.

    **The fifth check across a repository boundary and the second whose
    subject is what another repository *publishes*.**  ``SNAG-ESTATE-004``
    was the first, and the rule it settled applies twice over here: the
    fix could land in the pool's kwargs, in ``invariants()``, or in the
    route's serialiser, so an ``ast`` walk for the ``options`` entry the
    entry's own cause bullet names would report *still holds* for two of
    the three.  What is read instead is the **string on the wire**, taken
    by calling the route object mounted at the queue's published path.

    **Its population is empty by construction, which is rule 1's shape
    for the fourth time.**  ``active_lease`` has read ``null`` on every
    occasion anyone has looked — the entry says so and
    :func:`live_queue_lease` re-reads it every run as evidence — so there
    is no live rendering to inspect and the lease is *built*, exactly as
    the entry's own "observed rather than reasoned about" bullet says it
    was when the defect was found.  A check waiting for a granted lease
    would measure whether somebody happens to be holding the GPU this
    afternoon.

    **The obvious instrument agrees with itself only in summer.**  The
    entry quotes ``"2026-08-16T09:31:01+01:00"``, so reading one rendered
    offset is the first thing anyone would write.  ``Europe/London``
    renders ``+00:00`` from late October to late March: such a check
    reports the entry refuted every winter and true again every spring,
    having measured nothing.  :data:`QUEUE_WINTER_INSTANT` and
    :data:`QUEUE_SUMMER_INSTANT` are both driven through every surface,
    and ``stamps UTC`` means **both** came back at zero — which a session
    pinned to UTC satisfies by construction and a local one cannot.

    **The cause is driven rather than read, and the same reading
    validates the stand-in.**  ``pg_settings.source`` says where the
    connection's ``TimeZone`` came from: ``client`` when the connection
    asked — which is precisely what the entry's proposed fix produces —
    and ``configuration file`` when it inherited the cluster's.  Measured
    against both pool shapes before it was written down.  That is what
    separates *their fix landed* from *the box's default moved to UTC*,
    which renders identically and leaves the mechanism intact; the second
    is ``unknown``, because ``match`` would assert a local rendering this
    check did not see.  It is also what makes pointing their pool at this
    repository's database legitimate rather than merely convenient: a
    setting sourced from the configuration file is cluster-wide, and a
    ``database`` or ``user`` source says it is not, at which point the
    substitution is unsound and the check says so instead of answering.

    **The complaint and the premise refute the entry for opposite
    reasons**, so they are reported apart —
    :func:`check_sysd_ollama_ordering`'s rule, which
    ``SNAG-ESTATE-004``'s check also carried until it left the registry
    with its entry on 2026-08-27.  The queue starting to stamp
    UTC is the fix.  The *sibling* engine ceasing to is the entry's
    premise dying with its complaint intact — the two surfaces would
    agree again, at the wrong end — and a single boolean would file that
    as a job well done.

    Delegated, so what is measured is the estate's surface and never this
    repository's opinion of it, :func:`check_estate_port_8500`'s refusal
    in writing.  What is deliberately **not** measured is whether
    ``judge_queue_invariants`` would now misread the field: it carries
    ``active_lease`` into ``details`` verbatim and parses none of it, so
    the entry's own "costs nothing here" bullet is a statement about this
    repository's code that nothing over there can change.
    """
    route = queue_route()
    live = live_queue_lease()
    payload, problem = estate_probe(
        QUEUE_TIMEZONE_PROBE.format(
            service=str(ESTATE_SERVICE),
            dsn=libpq_dsn(get_config().database.sync_url),
            winter=QUEUE_WINTER_INSTANT,
            summer=QUEUE_SUMMER_INSTANT,
            route=route,
            stamps=QUEUE_LEASE_STAMPS,
        )
    )
    if payload is None:
        return Measurement("unknown", problem, (live,))

    reported = str(payload.get("problem") or "")
    if reported == "lease_invisible":
        return Measurement(
            "unknown",
            "the surface published no active lease over the probe's own granted row — "
            "the fixture no longer reaches the query invariants() runs, so nothing was "
            "rendered to read",
            (live,),
        )
    if reported == "route_absent":
        return Measurement(
            "unknown",
            f"nothing is mounted at {route} any more — the queue surface this entry "
            "is about has moved, which is a different claim",
            (live,),
        )

    served = stamp_reading(payload.get("served"))
    arbiter = stamp_reading(payload.get("arbiter"))
    sibling = stamp_reading(payload.get("sibling"))
    source = str(payload.get("queue_source") or "")
    setting = str(payload.get("queue_setting") or "")
    sibling_setting = str(payload.get("sibling_setting") or "")

    where = "unmeasured"
    if served is not None and arbiter is not None:
        if arbiter.stamps_utc and served.stamps_utc:
            where = "UTC at both layers, so the rendering is decided at or below invariants()"
        elif served.stamps_utc:
            where = (
                "invariants() hands a local instant up and the route publishes UTC, so the "
                "rendering is decided in the route's serialisation"
            )
        elif arbiter.stamps_utc:
            where = (
                "invariants() hands UTC up and the route publishes a local instant, which "
                "is neither layer doing what it says"
            )
        else:
            where = "local at both layers, which is the entry as filed"

    detail = (
        f"the queue surface published {served.render() if served else 'nothing'}"
        + (f" (no offset on {', '.join(served.zoneless)})" if served and served.zoneless else ""),
        f"Arbiter.invariants() handed up {arbiter.render() if arbiter else 'nothing'}",
        f"the same two instants through the project engine: "
        f"{sibling.render() if sibling else 'nothing'}",
        f"TimeZone on the queue pool's connection: {setting or '(unread)'} "
        f"(source: {source or 'unread'}); on the project engine's: "
        f"{sibling_setting or '(unread)'} (source: {payload.get('sibling_source') or 'unread'})",
        f"where the rendering is decided: {where}",
        live,
        estate_module_state(ESTATE_QUEUE_MODULES),
    )

    if served is None or arbiter is None or sibling is None:
        return Measurement(
            "unknown",
            "one of the three surfaces published neither timestamp, so the two renderings "
            "the entry compares were not both observed",
            detail,
        )
    if served.zoneless or arbiter.zoneless or sibling.zoneless:
        return Measurement(
            "unknown",
            "an instant reached the wire with no offset at all — that is neither of the "
            "two renderings this entry compares, and reading it as either would be a "
            "guess about which",
            detail,
        )
    if not (served.complete and arbiter.complete and sibling.complete):
        return Measurement(
            "unknown",
            "a surface published only one of the two instants, so it was compared on one "
            "season — which is the reading this check exists to refuse, whether the half "
            "went missing by the calendar or by a field",
            detail,
        )
    if source not in QUEUE_INHERITED_SOURCES and source != QUEUE_DECLARED_SOURCE:
        return Measurement(
            "unknown",
            f"the connection's TimeZone is sourced from {source!r}, which is per-database "
            "or per-role rather than cluster-wide — this repository's database cannot "
            "stand in for the estate's while that is true",
            detail,
        )

    declared = source == QUEUE_DECLARED_SOURCE
    connection_utc = zone_stamps_utc(setting)
    if connection_utc is None:
        return Measurement(
            "unknown",
            f"the connection reports its timezone as {setting!r}, which does not resolve "
            "to a zone — whether the surface publishes UTC because it was asked to cannot "
            "be told from whether it inherited one",
            detail,
        )
    if served.stamps_utc and not connection_utc:
        where_fixed = (
            "in the route's serialisation"
            if not arbiter.stamps_utc
            else "in invariants(), above a connection that is still local"
        )
        return Measurement(
            "mismatch",
            f"the queue surface publishes UTC at both instants off a connection still in "
            f"{setting} — the rendering is normalised {where_fixed}, which is the entry's "
            "complaint answered somewhere its cause bullet does not look",
            detail,
        )
    if served.stamps_utc and declared:
        return Measurement(
            "mismatch",
            f"the queue pool now asks for its own timezone ({setting}) and the surface "
            "publishes UTC at both instants — the entry's fix, in the place it names",
            detail,
        )
    if served.stamps_utc:
        return Measurement(
            "unknown",
            f"the surface publishes UTC at both instants on a connection that still "
            f"inherits its timezone ({setting}, source {source}) — the box's default has "
            "moved rather than the pool, so the entry's mechanism is intact and its "
            "symptom is not observable here",
            detail,
        )
    if arbiter.stamps_utc:
        return Measurement(
            "unknown",
            "invariants() hands UTC up and the route publishes a local instant — the two "
            "layers disagree about one fact, which is a different fault rather than this "
            "one holding",
            detail,
        )
    if declared:
        return Measurement(
            "mismatch",
            f"the queue pool declares a timezone now and it is not UTC ({setting}) — the "
            "entry's cause has gone while its symptom stands, which is a closure to judge "
            "and not a fix to record",
            detail,
        )
    if not sibling.stamps_utc:
        return Measurement(
            "mismatch",
            f"the project engine no longer stamps UTC either ({sibling_setting}) — the two "
            "surfaces agree again, at the wrong end, so the entry's premise has gone "
            "rather than its complaint",
            detail,
        )
    return Measurement("match", "", detail)


# ---------------------------------------------------------------------------
# SNAG-SVC-001 — advice that reduces observation, and the rule that forbids it
# ---------------------------------------------------------------------------

#: The synthetic service the advice half is driven at.  It is in no config
#: file and has no health rows: the entry's population is empty on this
#: box — ``searxng`` is the only service whose episodes are all
#: single-check and it has 2 against a threshold of 3 — so rule 1 says
#: build the subject rather than wait for one.
BLIP_SERVICE = "snagcheck-blip"

#: The synthetic journal source the ``known_noise`` half is driven at.
BLIP_NOISE_SOURCE = "snagcheck-noise.service"
BLIP_NOISE_SIGNATURE = "snagcheck probe fault N"

#: How many checks the *witness* episode lasts.  Two is the smallest
#: number that is not one, which is the whole of the narrowing being
#: driven: :func:`~sysadmin.monitor.reliability._outage_episodes` dates an
#: episode to its last **failing** check, so one sample spans zero seconds
#: and two span one interval.
BLIP_WITNESS_EPISODE_CHECKS = 2

#: Occurrences for the loud signatures, as a multiple of
#: :data:`~sysadmin.monitor.log_actions.NOISE_MIN_OCCURRENCES`.  Taken from
#: that constant rather than written here: it is invented and says so, so
#: a probe carrying its own copy would go on describing a floor nobody
#: uses.
BLIP_NOISE_MULTIPLE = 2

#: The file whose row the entry is about.
BLIP_ADVICE_PATH = REPO_ROOT / "sysadmin" / "monitor" / "service_recommendations.py"

#: The families holding the evidence the entry says this row has not got
#: — *"a correlation between the blips and the service's own logs, which
#: is ``log_actions.group_incidents``' machinery pointed at a different
#: table"*.  Both are named for :data:`ESTATE_NUDGE_MODULES`' reason: the
#: correlation could be built off the trend or off the incident grouping,
#: and a fix reaching one says nothing about the other.
BLIP_LOG_MODULES = (
    "sysadmin.monitor.log_actions",
    "sysadmin.monitor.log_trends",
)

#: What the row declares it argues from.  ``rate`` is "N blips per
#: window", which is the volume the conflict is about.
BLIP_RATE_EVIDENCE = "rate"

BLIP_ROW_KIND = "check_interval"


@dataclass(frozen=True)
class BlipContentionReading:
    """One drive of each side of ``SNAG-SVC-001``'s conflict."""

    episodes: int
    check_interval_seconds: int
    window_days: int

    # --- the advice half, at episodes that each lasted one check ---
    blip_title: str
    blip_evidence: str
    blip_points: int
    #: The witness: the same episode count, each lasting
    #: :data:`BLIP_WITNESS_EPISODE_CHECKS` checks.
    witness_row: bool
    witness_longest_minutes: float
    confidence: str
    suppressed: int

    # --- the ``known_noise`` half, four drives at one signature ---
    noise_on_loud_and_new: bool
    noise_on_loud_and_surged: bool
    noise_on_quiet_and_flat: bool
    loud_new_kind: str
    loud_surged_kind: str
    occurrences: int
    noise_floor: int

    #: Which of :data:`BLIP_LOG_MODULES` the advice module imports.
    log_reach: tuple[str, ...]

    @property
    def blip_row_fires(self) -> bool:
        return bool(self.blip_title)


def blip_health_points(
    episodes: int,
    episode_checks: int,
    window_days: int,
    check_interval_seconds: int,
    now: datetime,
) -> list[HealthPoint]:
    """A fully-covered window carrying ``episodes`` outages of a fixed length.

    Sampled at the **live** check interval across the whole window, which
    is not decoration.  The row is ``RATE_ARGUED``, so
    :func:`~sysadmin.monitor.service_recommendations.recommend` drops it
    unless the score's confidence is ``high``, and confidence is
    ``coverage_percent`` measured against ``checks_expected`` — itself
    derived from that same interval.  A series sampled at the probe's own
    convenience is suppressed before the row is built, and the probe then
    reports a silence it manufactured: :func:`timer_agent_series`' trap
    arriving through a different gate.

    Episodes are spread evenly rather than placed adjacent, because
    ``_outage_episodes`` collapses *consecutive* failing checks — two
    probe episodes one check apart are one episode of three, which is the
    witness rather than the subject.
    """
    from sysadmin.monitor.reliability import HealthPoint

    total = int(window_days * 86400 / check_interval_seconds)
    bad: set[int] = set()
    for index in range(episodes):
        start = int(total * (index + 1) / (episodes + 1))
        bad.update(range(start, start + episode_checks))
    return [
        HealthPoint(
            checked_at=now - timedelta(seconds=check_interval_seconds * (total - n)),
            status="unreachable" if n in bad else "ok",
        )
        for n in range(total)
    ]


def blip_noise_trend(
    change: ChangeKind,
    first_seen: datetime,
    current: int,
    previous: int,
    now: datetime,
) -> SignatureTrend:
    """One synthetic signature, in the shape ``log_actions.recommend`` reads."""
    from sysadmin.monitor.log_trends import SignatureTrend

    return SignatureTrend(
        signature=BLIP_NOISE_SIGNATURE,
        alert_title=f"Log error: {BLIP_NOISE_SOURCE} — {BLIP_NOISE_SIGNATURE}",
        source=BLIP_NOISE_SOURCE,
        severity="error",
        sample=BLIP_NOISE_SIGNATURE.replace("N", "1"),
        current=current,
        previous=previous,
        total=current + previous,
        first_seen=first_seen,
        last_seen=now,
        change=change,
    )


def blip_contention_reading() -> tuple[BlipContentionReading | None, str]:
    """Drive both sides of the conflict, over subjects this box has not got.

    **Two witnesses, because on each side a rule that has been removed
    and a producer the probe can no longer reach report identically** —
    Session 98's rule, needed twice here for the reason
    :func:`timer_agent_reading` needed it twice.  On the advice side the
    witness is an episode two checks long, which must produce **no** row;
    on the noise side it is the same loud signature made old and flat,
    which **must** produce one.
    """
    from sysadmin.monitor import log_actions, service_recommendations
    from sysadmin.monitor.log_trends import ChangeKind, Confidence, LogTrendReport
    from sysadmin.monitor.reliability import score_service

    config = get_config()
    settings = config.agents.sysadmin.service_actions
    interval = config.agents.sysadmin.health_check_interval_seconds
    window_days = config.agents.sysadmin.reliability.window_days
    episodes = settings.flap_min_episodes

    if interval <= 0 or window_days <= 0 or episodes <= 0:
        return None, (
            f"the probe's window is not positive (check interval {interval}s, window "
            f"{window_days}d, flap threshold {episodes}) — the synthetic subject cannot be "
            "built from this config"
        )

    now = datetime.now(UTC)

    def drive(episode_checks: int) -> tuple[ReliabilityScore, AdviceReport]:
        score = score_service(
            BLIP_SERVICE,
            blip_health_points(episodes, episode_checks, window_days, interval, now),
            window_days=window_days,
            check_interval_seconds=interval,
            now=now,
        )
        return score, service_recommendations.recommend(
            [score], settings, check_interval_seconds=interval, now=now
        )

    subject_score, subject = drive(1)
    if subject_score.outage_episodes != episodes:
        return None, (
            f"the probe built {subject_score.outage_episodes} episodes where it meant "
            f"{episodes} — the scorer no longer collapses failing checks the way this series "
            "assumes, so neither drive below is about the shape the entry describes"
        )
    if subject_score.confidence != "high":
        return None, (
            f"a fully-covered synthetic window scored {subject_score.confidence} confidence "
            f"({subject_score.coverage_percent:g}% of expected checks across "
            f"{subject_score.observed_days:g} days) — every RATE_ARGUED row is suppressed "
            "before it is built, so the advice side is unreachable through this probe"
        )

    witness_score, witness = drive(BLIP_WITNESS_EPISODE_CHECKS)
    if witness_score.longest_outage_minutes <= 0:
        return None, (
            f"an episode of {BLIP_WITNESS_EPISODE_CHECKS} consecutive failing checks still "
            "measures zero duration, so the probe cannot build the one shape the narrowing "
            "excludes and its control below would be the subject over again"
        )

    blip = next((r for r in subject.recommendations if r.kind == BLIP_ROW_KIND), None)

    loud = log_actions.NOISE_MIN_OCCURRENCES * BLIP_NOISE_MULTIPLE
    old = now - timedelta(days=window_days * 4)

    def noise_drive(
        change: ChangeKind, first_seen: datetime, current: int
    ) -> list[LogRecommendation]:
        previous = 0 if change is ChangeKind.NEW else current
        return log_actions.recommend(
            LogTrendReport(
                window_days=window_days,
                window_start=now - timedelta(days=window_days),
                previous_start=now - timedelta(days=window_days * 2),
                generated_at=now,
                confidence=Confidence.HIGH,
                signatures=[blip_noise_trend(change, first_seen, current, previous, now)],
            )
        )

    def is_noise(rows: list[LogRecommendation]) -> bool:
        return any(row.kind is log_actions.RecommendationKind.NOISE for row in rows)

    if not is_noise(noise_drive(ChangeKind.STEADY, old, loud)):
        return None, (
            "a loud, old and flat signature produced no noise row, so the family "
            "known_noise rule 3 belongs to is not reachable through this probe at all — its "
            "silence about the loud *new* signature would then be the probe's rather than "
            "the rule's, and the two are indistinguishable from here"
        )

    quiet_flat = noise_drive(ChangeKind.STEADY, old, log_actions.NOISE_MIN_OCCURRENCES - 1)
    if is_noise(quiet_flat):
        return None, (
            f"a signature at {log_actions.NOISE_MIN_OCCURRENCES - 1} occurrences — below "
            "the family's own floor — is recommended as noise, so volume no longer gates "
            "the rule at all.  The loud *new* drive below would then be silent because of "
            "its change kind and never because of its volume, and the conflict this entry "
            "states is about volume: the rule it is measured against has changed shape "
            "under it, which is neither verdict"
        )

    new_loud = noise_drive(ChangeKind.NEW, now - timedelta(days=1), loud)
    surged_loud = noise_drive(ChangeKind.SURGED, old, loud)

    return (
        BlipContentionReading(
            episodes=episodes,
            check_interval_seconds=interval,
            window_days=window_days,
            blip_title=blip.title if blip else "",
            blip_evidence=blip.evidence if blip else "",
            blip_points=blip.recoverable_points if blip else 0,
            witness_row=any(r.kind == BLIP_ROW_KIND for r in witness.recommendations),
            witness_longest_minutes=witness_score.longest_outage_minutes,
            confidence=subject_score.confidence,
            suppressed=subject.suppressed_by_confidence,
            noise_on_loud_and_new=is_noise(new_loud),
            noise_on_loud_and_surged=is_noise(surged_loud),
            noise_on_quiet_and_flat=is_noise(quiet_flat),
            loud_new_kind=new_loud[0].kind.value if new_loud else "",
            loud_surged_kind=surged_loud[0].kind.value if surged_loud else "",
            occurrences=loud,
            noise_floor=log_actions.NOISE_MIN_OCCURRENCES,
            log_reach=tuple(
                module for module in BLIP_LOG_MODULES if importers_of(module, [BLIP_ADVICE_PATH])
            ),
        ),
        "",
    )


def check_check_interval_looks_away() -> Measurement:
    """``SNAG-SVC-001`` — a row that answers volume by observing less.

    **The twenty-fourth check, the fourth built on a synthetic subject,
    and the first whose claim is a conflict between two rules rather than
    a fact about one.**  :func:`check_dropin_blind_spot` builds a
    drop-in, :func:`check_unmarked_sentence_invisible` a block sentence
    and :func:`check_timer_agent_two_owners` a timer-backed agent; this
    builds *a service whose every outage lasted one poll*, which is the
    shape this box has not produced.

    **Rule 1, and the entry states its own population for the checker.**
    "Zero on this box today, measured" — ``searxng`` is the only service
    whose episodes are all single-check and it has 2 against a threshold
    of 3.  A check that looked for the row would report the entry refuted
    on every day the box behaved, which is every day so far, and would
    report it live the first afternoon a health path went slow.  So the
    contention is **built**: a fully-covered window carrying exactly
    ``flap_min_episodes`` outages of one check each, scored by the real
    :func:`~sysadmin.monitor.reliability.score_service` and passed to the
    real :func:`~sysadmin.monitor.service_recommendations.recommend`.

    **What is reported, and what is deliberately not.**  The entry's own
    body reserves the decision: *"the honest resolutions are two and both
    are the owner's — delete the kind, or give it evidence it currently
    has not got"*.  So this reports **whether the conflict is still
    live** and, when it is not, **which side moved** — a verdict about
    the box, which is what every entry in this registry gets.  It
    recommends neither resolution, and it cannot: the two are opposite
    edits to the same row and nothing measurable here prefers one.

    **Three claims, three instruments, and they refute the entry in three
    different directions.**

    1. *The row still fires on volume alone.*  ``recoverable_points`` is
       ``0`` and ``evidence`` is ``rate`` — the row's own statement that
       it argues from "N blips per window" and recovers nothing.  Its
       absence is the first resolution, taken.
    2. *Nothing correlates the blips with the service's own logs.*  The
       second resolution names ``log_actions.group_incidents``' machinery
       pointed at a different table, and a correlation cannot be computed
       by a module that has not got the data — so the instrument is the
       advice module's **import set**, which any such fix has to move
       whichever file it lands in.  Rule 7 for the fifth time, and the
       sharpest instance yet: ``service_recommendations.py`` names
       ``log_actions`` twice in its module docstring, ``log_trends`` in
       :func:`~sysadmin.monitor.service_recommendations._flapping_row`'s
       and ``known_noise`` in the very docstring that files this snag, so
       a grep reports every one of them as already wired.  An ``ast``
       import walk sees none: a docstring is an ``ast.Constant``.
    3. *The rule it conflicts with still says the opposite.*  Driven, not
       read: one synthetic signature at
       :data:`BLIP_NOISE_MULTIPLE` times ``NOISE_MIN_OCCURRENCES`` is
       offered to :func:`~sysadmin.monitor.log_actions.recommend` three
       times.  Old and flat it **is** recommended as noise (the witness —
       the family is reachable); *new* at the same volume it is **not**
       (rule 3: volume is not evidence of harmlessness); quiet and flat
       it is not either (volume is *necessary*, so rule 3 holds because
       loudness is insufficient rather than because it is ignored).  That
       third drive is what makes the second mean anything.

    **A third way for this entry to stop being true, which it does not
    anticipate.**  Claims 1 and 2 are the two resolutions it names; claim
    3 is the *other* party.  ``known_noise`` rule 3 relaxing would
    dissolve the conflict without anyone touching the row — the entry
    would be refuted by a change in the module it is measured against,
    which is not a fix and must not read as one.  The note says which
    side moved for exactly that reason.

    **The witness is why this is not simply "the row exists".**  The same
    three episodes made :data:`BLIP_WITNESS_EPISODE_CHECKS` checks long
    must produce **no** row, because ``longest_outage_minutes`` is then
    positive and the narrowing excludes it.  If both drives produce a
    row the narrowing has gone, and that is reported ``unknown`` rather
    than either verdict: the entry's headline claim would be *more* true
    and its third bullet false, so "still live" understates it and
    "refuted" is plainly wrong.  A check cannot rewrite the entry it
    measures; it can decline to grade one that has moved underneath it.
    """
    reading, problem = blip_contention_reading()
    if reading is None:
        return Measurement("unknown", problem)

    detail = (
        f"subject: {BLIP_SERVICE}, {reading.episodes} outages in a "
        f"{reading.window_days}-day window at {reading.confidence} confidence, each lasting "
        f"one {reading.check_interval_seconds}s check",
        f"advice row: {reading.blip_title or '(silent)'} "
        f"[evidence {reading.blip_evidence or '-'}, {reading.blip_points} points recoverable]",
        f"witness — the same {reading.episodes} outages "
        f"{BLIP_WITNESS_EPISODE_CHECKS} checks long "
        f"({reading.witness_longest_minutes:g} min): "
        + ("a row" if reading.witness_row else "no row"),
        f"known_noise rule 3 at {reading.occurrences} occurrences "
        f"(floor {reading.noise_floor}): old and flat -> noise, "
        f"new -> {reading.loud_new_kind or '(silent)'}, "
        f"surged -> {reading.loud_surged_kind or '(silent)'}, "
        f"quiet and flat -> " + ("noise" if reading.noise_on_quiet_and_flat else "(silent)"),
        "advice module importing a log family: "
        + (", ".join(reading.log_reach) if reading.log_reach else "none"),
    )

    if reading.witness_row:
        return Measurement(
            "unknown",
            (
                f"an outage lasting {BLIP_WITNESS_EPISODE_CHECKS} checks "
                f"({reading.witness_longest_minutes:g} min) still produced a "
                f"{BLIP_ROW_KIND} row, so the narrowing the entry's third bullet describes "
                "is gone — its headline claim is more true than when it was filed and its "
                "own account of what was done instead is not, which is an entry to rewrite "
                "rather than a verdict to grade"
            ),
            detail,
        )

    faults: list[str] = []
    if not reading.blip_row_fires:
        faults.append(
            f"no {BLIP_ROW_KIND} row is offered for {reading.episodes} single-check outages "
            "— the kind no longer fires for the shape it was narrowed to, which is the "
            "first of the two resolutions the entry leaves to the owner"
        )
    elif reading.blip_evidence != BLIP_RATE_EVIDENCE:
        faults.append(
            f"the row now declares evidence '{reading.blip_evidence}' rather than "
            f"'{BLIP_RATE_EVIDENCE}' — it is arguing from something other than the blip "
            "count, which is the second resolution's shape stated by the producer itself"
        )
    if reading.log_reach:
        faults.append(
            f"{BLIP_ADVICE_PATH.name} imports {', '.join(reading.log_reach)} — the advice "
            "has the service's own log data now, which is the evidence the entry says it "
            "has not got"
        )
    loud_but_not_flat = [
        label
        for label, seen in (
            ("first seen inside the window", reading.noise_on_loud_and_new),
            ("surging", reading.noise_on_loud_and_surged),
        )
        if seen
    ]
    if loud_but_not_flat:
        faults.append(
            f"a signature {' and one '.join(loud_but_not_flat)} is recommended as noise at "
            f"{reading.occurrences} occurrences — known_noise rule 3 no longer refuses "
            "volume alone, so the conflict has dissolved from the other side and nobody has "
            "touched the row this entry is about"
        )
    if faults:
        return Measurement("mismatch", "; ".join(faults), detail)
    return Measurement("match", "", detail)


# ---------------------------------------------------------------------------
# SNAG-ESTATE-006 — a finding's `code` reaches no published key
# ---------------------------------------------------------------------------

#: The three modules ``SNAG-ESTATE-006`` spans, named for
#: :data:`ESTATE_NUDGE_MODULES`' reason and with one more file than that
#: entry needs.  The dataclass computes ``code`` and folds it into
#: ``fingerprint``; the ORM model is where it is lost, having no column;
#: the route is where a key would appear.  A fix can land in any one of
#: the three and a checkout state read for one says nothing about the
#: other two.
ESTATE_AUDIT_MODULES = (
    Path("estate_service") / "audit" / "finding.py",
    Path("estate_service") / "audit" / "models.py",
    Path("estate_service") / "audit" / "router.py",
)

#: The field the entry is about, typed here for :data:`NUDGE_WORDING`'s
#: reason: it is the *entry's* subject rather than a copy of the
#: producer's schema, and the check reads whether the producer still
#: computes it rather than assuming it does.  Nothing else about the
#: producer's shape is written down — the specimen is built from the
#: fields and columns their code declares today, so a fix that publishes
#: ``code`` is seen without this module being edited.
AUDIT_FINDING_CODE = "code"

#: The surface id in :data:`sysadmin.estate.client.SURFACE_PATHS`.  Taken
#: from this repository's own record of what it pulls hourly rather than
#: typed as a path, which is ``check_queue_stamps_local``'s rule and the
#: reason a renamed route reports a read failure rather than a refutation.
AUDIT_SURFACE = "audit_findings"

#: The probe handed to :func:`estate_probe`.  It builds a finding out of
#: whatever the producer's model declares, drives the producer's own
#: ``findings()`` route function at it, and hands back four key sets: the
#: fields the dataclass computes, the keys its bus payload publishes, the
#: columns the table stores, and the keys the route serialises.
#:
#: **No database is opened, in either repository, and that is a rule
#: rather than a courtesy.**  The estate rules forbid one application
#: reading another's database — not even read-only, not even once — and a
#: check that ran at both ends of every sitting would be the most regular
#: breach of it on the box.  ``check_queue_stamps_local`` obeys that by
#: pointing their pool at *this* repository's database; this route needs
#: no database at all, because the key set is decided by a literal dict in
#: their serialiser and not by anything a row can carry.  So the session
#: is a stand-in and ``get_db_session`` is **poisoned before the router is
#: imported**, which is the ``UserSystemd(runner=refuse)`` move in
#: ``QUEUE_TIMEZONE_PROBE``: the probe cannot read their database even if
#: a future ``findings()`` grew a call that tried.
#:
#: **Dispatch is on the statement's own ``column_descriptions``**, which
#: is SQLAlchemy's public account of what a select asks for, rather than
#: on call order.  Order-based dispatch answers a *reordered* route
#: wrongly and silently; this raises, which :func:`run_check` reports as
#: ``unknown`` — rule 5, and the direction that matters when the thing
#: being driven belongs to somebody else.
#:
#: **Nothing private is touched.**  ``findings``, ``Finding``,
#: ``AuditFinding`` and ``AuditRun`` are theirs and public; ``_run_payload``
#: and ``_streak_starts`` are not, and are reached only by calling the
#: route that calls them — Session 87's rule.
AUDIT_CODE_PROBE = '''\
import asyncio, dataclasses, datetime, json, sys, uuid
sys.path.insert(0, {service!r})

from estate_service.projects import db as projects_db


async def refuse(*args, **kwargs):
    """The probe never opens a session of theirs, and cannot."""
    raise RuntimeError("the snag check never reads estate-manager's database")


projects_db.get_db_session = refuse

from estate_service.audit import router as audit_router
from estate_service.audit.finding import Finding
from estate_service.audit.models import AuditFinding, AuditRun

CODE = {code!r}
NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
TEXT = "specimen"


def column_value(column):
    """A value for one column, read off the type it declares."""
    name = column.type.__class__.__name__.lower()
    if "uuid" in name:
        return uuid.uuid4()
    if "datetime" in name:
        return NOW
    if "json" in name:
        return {{}}
    if "int" in name:
        return 1
    if "bool" in name:
        return False
    return TEXT


def stored(model, **over):
    """One row of an ORM model, filled from the columns it declares today."""
    kwargs = {{column.key: column_value(column) for column in model.__table__.columns}}
    kwargs.update(over)
    return model(**kwargs)


class Answer:
    """One prepared result, in each shape the route asks it for."""

    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def scalars(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None


class Session:
    """A session that answers from the specimen and never from a database."""

    def __init__(self, run, finding):
        self._run, self._finding = run, finding

    async def execute(self, statement):
        asked = tuple(item["name"] for item in statement.column_descriptions)
        if asked == ("AuditRun",):
            return Answer([self._run])
        if asked == ("AuditFinding",):
            return Answer([self._finding])
        if asked == ("id", "started_at"):
            return Answer([(self._run.id, self._run.started_at)])
        if asked == ("fingerprint", "run_id"):
            return Answer([(self._finding.fingerprint, self._run.id)])
        raise RuntimeError("the audit route asked for " + repr(asked))


columns = sorted(column.key for column in AuditFinding.__table__.columns)
run = stored(AuditRun)
finding = stored(AuditFinding, run_id=run.id)
if CODE in columns:
    setattr(finding, CODE, CODE)

served = asyncio.run(audit_router.findings(session=Session(run, finding)))
published = (served.get("findings") or [{{}}])[0]

computed = Finding(**{{field.name: None for field in dataclasses.fields(Finding)}})

print(json.dumps({{
    "computed": sorted(field.name for field in dataclasses.fields(Finding)),
    "offers_code": hasattr(computed, CODE),
    "bus": sorted(computed.as_payload()),
    "columns": columns,
    "route": sorted(published),
    "route_detail": sorted(published.get("detail") or {{}}),
    "served": len(served.get("findings") or []),
}}))
'''


def audit_wire_client() -> httpx.AsyncClient:
    """The client :func:`live_audit_findings` reads the estate with.

    A factory rather than a client, because the substitution a probe
    needs is made **here** and nowhere lower: patching it leaves the
    production :func:`sysadmin.estate.client.pull_all` running the whole
    way down — path dispatch, ``raise_for_status``, the JSON parse and
    the per-surface ``read`` flag — which is :func:`mounted_judge`'s rule
    and its reason.  A test that stubbed the reader instead would be
    measuring its own fixture.
    """
    import httpx

    return httpx.AsyncClient(timeout=10.0)


@dataclass(frozen=True)
class WireReading:
    """What the deployed findings surface published, as key sets.

    Attributes:
        keys: every key any finding carried.  The union rather than the
            intersection, because the entry claims ``code`` reaches *no*
            payload and one payload carrying it refutes that.
        detail_keys: every key any finding's ``detail`` blob carried.
        findings: how many findings the surface served.
    """

    keys: frozenset[str]
    detail_keys: frozenset[str]
    findings: int


def live_audit_findings() -> tuple[WireReading | None, str]:
    """The deployed surface's key sets, or the reason there are none.

    Read through :func:`sysadmin.estate.client.pull_all` rather than with
    an HTTP call of this module's own: that is the call
    :class:`sysadmin.estate.agent.EstateJudgeAgent` makes hourly, so the
    path, the base URL, the timeout and the treatment of a failure are
    the consumer's rather than a second set that can disagree with them.
    The four other surfaces come along because the function reads all
    five; they are the same four the judge reads anyway.

    This is the estate's **API**, which is the one way the estate rules
    permit data to cross.

    **The wire can refute and cannot confirm**, which is why this returns
    evidence rather than a verdict.  A ``code`` key here kills the claim
    whatever any checkout says.  Its *absence* is one release behind by
    construction — ``estate_module_state``'s "committed is not deployed",
    read the other way — and goes blind altogether on a clean audit,
    which is the estate's goal rather than a remote possibility.
    """
    from sysadmin.estate import client
    from sysadmin.estate.client import SurfaceResult

    base = get_config().agents.estate_judge.base_url

    async def drive() -> dict[str, SurfaceResult]:
        async with audit_wire_client() as http:
            return await client.pull_all(http, base)

    try:
        results = asyncio.run(drive())
    except Exception as exc:  # noqa: BLE001 — the live surface is evidence, never a gate
        return None, f"the live surface was not read ({exc.__class__.__name__})"
    result = results.get(AUDIT_SURFACE)
    if result is None or not result.read:
        reason = (result.error if result is not None else None) or "no result"
        return None, f"the live surface was not read ({reason})"
    payload = result.payload or {}
    served = payload.get("findings")
    if not isinstance(served, list):
        return None, "the live surface published no findings list"
    findings = [item for item in served if isinstance(item, dict)]
    keys: set[str] = set()
    detail_keys: set[str] = set()
    for item in findings:
        keys.update(str(key) for key in item)
        detail = item.get("detail")
        if isinstance(detail, dict):
            detail_keys.update(str(key) for key in detail)
    return WireReading(frozenset(keys), frozenset(detail_keys), len(findings)), ""


def check_audit_code_unpublished() -> Measurement:
    """``SNAG-ESTATE-006`` — a code the producer computes and no key carries.

    ``estate_service.audit.finding.Finding`` has a real ``code`` field and
    folds it into ``fingerprint`` as that string's last ``:``-separated
    segment.  ``AuditFinding`` has no ``code`` column, so ``_record``
    cannot store one, and ``GET :8400/api/audit/findings`` builds each
    finding from a literal dict of eleven keys that does not include it.
    :func:`sysadmin.estate.judgements.judge_audit_findings` reads
    ``finding.get("code")`` and gets ``None`` every time.

    **The entry's own *not worked around here* bullet is what this check
    respects, and it is a constraint on the instrument rather than a note
    beside it.**  The only workaround available is splitting
    ``fingerprint`` on its last colon, which is this repository parsing an
    identity format the estate owns — so nothing here splits it, and what
    is read is the set of **published keys**.  A test pins that: the
    module's own source is walked for a split of ``fingerprint``, because
    the cheapest way for a later sitting to make this check "better" is
    the one thing the entry forbids.

    **Two instruments, and the second exists because the first goes blind
    at the finish line.**  The live wire is what the entry measured and
    what the consumer reads; across **135 audit runs it has never once
    been clean**, minimum one finding, so its population is not the
    weather in the way ``/api/projects/attention``'s was for
    :func:`check_nudge_wording_unpublished`.  But an audit that finds
    nothing publishes ``"findings": []``, and a route that has never
    served a finding says nothing about its own key set — so a wire-only
    check reports ``unknown`` on precisely the morning the estate becomes
    conformant.  The specimen answers whatever the audit found, and it is
    built the way that check builds a ``Nudge``: from the fields and
    columns the producer declares today, never from a list typed here.

    **The wire can refute and cannot confirm.**  A ``code`` key on a
    served finding kills the claim whether or not their checkout has
    moved; its absence is one deploy behind and is carried as evidence,
    with :func:`estate_module_state` naming the checkout state — the
    distinction that function was written for, and the reason a fix
    committed at 22:42 and served from an 11:35 process is not judged
    here.

    **Four remedies are reachable and they are four different notes.**
    Publishing ``code`` as a route key is the complete fix and needs no
    change here.  Publishing it inside ``detail`` is a fix on the
    producer's side that our consumer still reads past, because
    ``judge_audit_findings`` reads it at the top level — the residue
    shape ``check_nudge_wording_unpublished`` reports for ``details``, one
    surface over, and the one place a ``mismatch`` here owes this
    repository a line.  Adding the column without publishing a key is the
    storage half of the cause landing while the claim stands, so it is
    ``match`` **with the residue named**: a check that reported it as
    silence would let a fix in flight look like nothing happening.  And
    the producer dropping ``code`` from the dataclass altogether ends the
    two-owners problem rather than the publishing one, which is that
    check's delete remedy and is a refutation for its reason.

    **What the sitting found that the entry does not say**: ``code`` is
    not computed-and-dropped everywhere.  ``Finding.as_payload`` — the
    form published on ``estate/audit/findings/{check}`` — carries it.  So
    the producer already has a published shape holding the field, and the
    entry's "publishes a finding's ``code`` nowhere" is true of the one
    surface this repository reads and false of the bus.  It is carried in
    the evidence rather than folded into the verdict, because the claim
    that matters is about the surface ``judge_audit_findings`` pulls.
    """
    wire, wire_problem = live_audit_findings()
    payload, problem = estate_probe(
        AUDIT_CODE_PROBE.format(service=str(ESTATE_SERVICE), code=AUDIT_FINDING_CODE)
    )

    wire_line = (
        f"the live surface served {wire.findings} findings publishing "
        f"{', '.join(sorted(wire.keys)) or 'no keys'}, whose detail blobs carry "
        f"{', '.join(sorted(wire.detail_keys)) or 'no keys'}"
        if wire is not None
        else f"live population: {wire_problem}"
    )
    if wire is not None and AUDIT_FINDING_CODE in (wire.keys | wire.detail_keys):
        owed = (
            ""
            if AUDIT_FINDING_CODE in wire.keys
            else " inside a finding's detail blob, which judge_audit_findings reads past "
            "because it reads the top level — so one line is owed here"
        )
        return Measurement(
            "mismatch",
            f"the deployed findings surface publishes {AUDIT_FINDING_CODE!r}{owed} — the "
            "claim is dead on the surface the judge reads, whatever the checkout says",
            (wire_line, estate_module_state(ESTATE_AUDIT_MODULES)),
        )
    if payload is None:
        return Measurement("unknown", problem, (wire_line,))

    computed = _probe_names(payload.get("computed"))
    columns = _probe_names(payload.get("columns"))
    route = _probe_names(payload.get("route"))
    route_detail = _probe_names(payload.get("route_detail"))
    bus = _probe_names(payload.get("bus"))
    offers = payload.get("offers_code") is True
    detail = (
        f"Finding computes {', '.join(computed) or 'no fields'}",
        f"its bus payload publishes {', '.join(bus) or 'no keys'}",
        f"audit_findings stores {', '.join(columns)}",
        f"the findings route publishes {', '.join(route) or 'no keys'}",
        f"its detail blob carries {', '.join(route_detail) or 'no keys'}",
        wire_line,
        estate_module_state(ESTATE_AUDIT_MODULES),
    )

    if not route:
        return Measurement(
            "unknown",
            "the producer's findings route served no finding for a specimen row — the "
            "probe has stopped isolating the question",
            detail,
        )
    if AUDIT_FINDING_CODE in route:
        return Measurement(
            "mismatch",
            f"the findings route now publishes {AUDIT_FINDING_CODE!r} — the fix the entry "
            "waits for, and judge_audit_findings starts working with no change here",
            detail,
        )
    if AUDIT_FINDING_CODE in route_detail:
        return Measurement(
            "mismatch",
            f"{AUDIT_FINDING_CODE!r} now reaches the wire inside the finding's detail blob "
            "and not as a key of its own — the producer has published it and "
            "judge_audit_findings reads it at the top level, so one line is owed here",
            detail,
        )
    if not offers:
        return Measurement(
            "mismatch",
            f"the producer no longer computes a {AUDIT_FINDING_CODE!r} at all — the delete "
            "remedy, which ends the two-owners problem rather than the publishing one",
            detail,
        )
    if AUDIT_FINDING_CODE in columns:
        return Measurement(
            "match",
            f"audit_findings now carries a {AUDIT_FINDING_CODE!r} column and the route "
            "still publishes no such key — the storage half of the cause has landed and "
            "the claim is unmoved",
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
            "duplicate_ingest_residue",
            "SNAG-LOG-014",
            "two journal records are stored twice",
            check_duplicate_ingest_residue,
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
            "unmarked_sentence_invisible",
            "SNAG-ESTATE-012",
            "a block sentence with no pattern and no marker reaches nothing",
            check_unmarked_sentence_invisible,
        ),
        Check(
            "queue_stamps_local",
            "SNAG-ESTATE-007",
            "one estate surface renders a timestamp in local time",
            check_queue_stamps_local,
        ),
        Check(
            "timer_agent_two_owners",
            "SNAG-SVC-002",
            "a timer-backed agent is judged by two families at once",
            check_timer_agent_two_owners,
        ),
        Check(
            "check_interval_looks_away",
            "SNAG-SVC-001",
            "advice that answers a flap by observing it less often",
            check_check_interval_looks_away,
        ),
        Check(
            "audit_code_unpublished",
            "SNAG-ESTATE-006",
            "the audit's findings surface publishes no code key",
            check_audit_code_unpublished,
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


def _convention(
    key: str,
    subject: str,
    note: str,
    detail: tuple[str, ...] = (),
    verdict: Verdict = "unknown",
) -> Finding:
    """One convention finding, ``unknown`` unless the caller says otherwise.

    **Two of the three families are faults by construction.**  A marker
    naming no check, and a check whose entry does not carry it, are both
    the document and the registry out of step; neither has a state of the
    world in which the line is good news, so neither is ever emitted
    holding and both keep the default.  Rule 5 with them.

    **The third can hold, and giving it a verdict is what ``SNAG-DOCS-006``
    cost.**  A finding published in *every* state needs an answer for the
    state where nothing is wrong, or publishing it pins
    ``sysadmin-check-snags`` at exit ``2`` for ever — and
    :data:`sysadmin.core.schema_guard.EXIT_STATUS` gives ``unknown`` its
    own rung precisely so a check that could not run is told apart from
    one that failed.  So the parameter is here rather than the verdict
    being widened for all three: what changed is what *one* family can
    report, not what a convention finding means.
    """
    return Finding(key, None, subject, "convention", verdict, note, detail)


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

    **That third line is published in every state, which is
    ``SNAG-DOCS-006``** — ``ports_checked``'s rule arriving at this
    repository's own claims register.  It was appended inside ``if
    unchecked:`` until 2026-08-28, so a register in which every open
    entry carried a check said *nothing* about the convention, and a
    reader could not tell that from the finding having been deleted,
    renamed, or failing to run.  Emitting the line only when the set is
    empty is the mirror of the same defect and was refused with it.

    Three states, and the third is the one the fix could most easily have
    got wrong.  A non-empty set is ``unknown`` and unchanged — an entry
    nobody checks is a claim nobody has tested, which is rule 5.  An
    empty set **over a population** is ``match``: something in the
    register could have forced the other answer and did not.  An empty
    set over **no open entries at all** is ``unknown`` again, because
    nothing could have made it non-zero — zero-because-blind served as
    zero-because-clean is the defect being fixed, one level in, and a
    constant observation is not evidence without a witness that could
    have differed.  Reachable and empty today: a document whose entries
    are all closed parses cleanly, so :func:`load_entries` reports no
    problem and the count is vacuous rather than good.
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
    open_total = sum(1 for entry in entries if entry.is_open)
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
                f"{len(unchecked)} of {open_total} open entries "
                "carry no check — their claims are only as fresh as the last hand sweep",
                named,
            )
        )
    elif open_total:
        findings.append(
            _convention(
                "convention:unchecked",
                "Open entries no check names",
                f"0 of {open_total} open entries carry no check — every one names a check, "
                "and the lines above are what those checks found",
                verdict="match",
            )
        )
    else:
        findings.append(
            _convention(
                "convention:unchecked",
                "Open entries no check names",
                "the document holds no open entry, so nothing could have been reported "
                "unchecked — the absence of a population, not a clean one",
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
