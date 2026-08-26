"""Re-measure the operational claims the session-opening block prints.

``SNAG-ESTATE-008``.  ``docs/roadmap/STATUS.md`` opens with a block that
tells the next sitting what is owed — a restart, a migration, an alert row
waiting on someone.  Nothing has ever checked it.  Measured on 2026-08-16,
**all three actions it carried had already been done**, two of them by a
party that never touched the document, and the block went on asking for
them for five sittings; on 2026-08-24 the same file asserted a retention
boundary three hours before it happened.  Six consecutive sittings have
paid for this.

The previous ranking demoted the fix for having "no obvious enforcement
point, since these claims live in prose".  That is the part that stopped
being true rather than the part that is hard: ``scripts/claude-preflight.sh``
already runs at the start of every sitting and already prints those
claims — it just prints them *from the prose*, with nothing between the
document and the reader.  This module is what goes between.

Six rules, three of them the opposite of the obvious implementation:

1. **The parsed region is exactly the region preflight prints.**  Not the
   whole file, which restates old figures on purpose ("44 before Session
   27") and would make every claim ambiguous, and not a machine-readable
   marker either — an ``<!-- routes=46 -->`` comment beside the sentence
   is a second statement of one fact that can disagree with the first,
   which is ``SNAG-DB-003``'s shape arriving in a document.  The prose
   *is* the artefact under test, so the prose is what is read.

2. **Every way of not-knowing is ``unknown``, never ``match``.**  A claim
   whose pattern finds nothing, a claim the block states two ways, a
   database that will not answer and a unit systemd has never heard of
   are four different faults and none of them is agreement —
   ``UnitScanResponse.ports_checked``'s rule, and the reason the verdicts
   and the exit statuses are :mod:`sysadmin.core.schema_guard`'s three
   rather than a boolean.  Note the second of those: two *different*
   values for one claim inside the printed block is drift with both
   halves in one file, which is worth naming rather than resolving by
   taking the first match.

3. **Two kinds of check, and conflating them would have you edit the
   wrong artefact.**  A ``claim`` compares the document against the box —
   a mismatch means the *document* is stale.  A ``state`` check compares
   the box against this checkout — a mismatch means the *box* is stale,
   and no wording in STATUS.md would fix it.  They print together because
   they are read together at the top of a sitting, and they are separate
   fields because the remedies are opposites.

4. **The deploy check compares file mtimes, never commit times**, and the
   obvious version is wrong on this box *today*.  The daemon entered
   active at 09:58:28 and the newest commit touching ``sysadmin/`` landed
   at 10:05:22, so a commit-time rule reports a restart owed; the content
   is identical, because this repository restarts to verify and commits
   afterwards.  The newest ``.py`` on disk was written 09:57:46, 42
   seconds *before* the start, which is the question actually being
   asked: is the running process serving what is on disk.  The cost is
   stated rather than hidden — a checkout or a rebase rewrites mtimes, so
   this can report a restart owed for an edit that changed nothing back,
   and so can a file the daemon never imports — this one, the moment it
   is written.  It fails in the direction that costs a needless
   ``kill -TERM``, which on this box is not privileged and takes a
   second.

5. **The unresolved-alert count is a gauge, and both directions are news
   in opposite ways.**  A *rise* is a row the block does not account for.
   A *fall* is the case this snag was filed for: ``SNAG-DB-002``'s eight
   collation rows resolved themselves at 18:01:48 when estate-manager ran
   the ``REINDEX``, this application observed the remedy land, and four
   documents went on asking for it for three days.  So the open titles
   are named rather than counted — ``details['truncated_sources']``'s
   rule, in the surface that sets the agenda.

6. **Nothing here writes to a document.**  A check that corrects the file
   it reads becomes a second author of the claim, and the next sitting
   cannot tell a measured number from a written one.  It reports; the
   sitting edits.  For the same reason there is no ``--quiet``: the one
   flag :mod:`sysadmin.core.schema_guard` needed has three shell callers
   asking for it, this has none, and an option nothing passes is the
   ``SNAG-CFG-001`` shape at the size of a flag.

``SNAG-ESTATE-011`` added three more, and the first is the one that
decides whether a marker beside prose is a defect or a convention:

7. **A marker names a check; it never restates a value.**  Rule 1 refuses
   ``<!-- routes=46 -->`` beside a sentence, and it is right to: a marker
   holding a *figure* can agree with the box while the prose beside it
   says something else, and nothing notices — ``SNAG-DB-003``'s two
   statements of one fact, arriving in a document.  ``<!--check:routes-->``
   is not that.  There is still exactly one figure in the document, the
   one in the prose, and the named check reads it from there.  So the two
   can never disagree about a fact, because the marker states none.  It
   buys the enforcement point the convention had no way to have: a figure
   this module can test that no line claims is reported, which is
   ``SNAG-ESTATE-008``'s *"every ops action names the check that closes
   it"* with something behind it.  The marker is **additive and cannot
   subtract** — every pattern-bearing claim runs whether or not a marker
   names it — because a marker that gated a check would make "delete the
   marker" a way to retire one, which is rule 2's silent retirement
   wearing the fix for it.

8. **A prediction is timed, not measured.**  ``SNAG-ESTATE-011`` was
   opened by a block asserting a retention boundary three hours before it
   happened.  Nothing about that sentence was wrong when written and
   nothing about it was measurable when written, so no amount of pattern
   reaches it; ``<!--check:expires …-->`` is the one family whose members
   the *document* declares rather than this module.  Before its moment the
   claim stands; after its moment it is ``unknown``, never ``mismatch`` —
   the prediction may well have come true, and "nobody went back" is
   exactly what rule 2 reserves ``unknown`` for.

9. **The one fact stated twice is pinned rather than trusted.**  An
   ``expires`` marker must carry a *date*, because the prose does not —
   "clears at 03:32" names a wall clock and no day, and a pattern that
   guessed the day would be wrong once per prediction.  That makes the
   instant the single exception to rule 7, so it is handled the way
   :func:`sysadmin.core.logging_setup.syslog_priority` is handled against
   ``journal.PRIORITY_MAP``: not asserted on each side, *pinned* — the
   wall clock the marker renders must appear in the block, or the claim is
   ``unknown`` and says which two moments disagree.  The pin is against
   the whole region rather than the marker's own sentence, which is the
   weaker half and is stated rather than hidden: a block naming ``03:32``
   twice for two different reasons would satisfy it.

**This module sits beside main.py** for the reason :mod:`sysadmin.reload`
and :mod:`sysadmin.metadata` do: it composes ``core`` with every domain
(the route count comes from :func:`sysadmin.main.create_app`, which
imports all of them), so a ``core/ops_claims.py`` would break the rule
that makes every other boundary real.  ``tests/test_import_boundary.py``
now names it as the fourth composition root.
"""

from __future__ import annotations

import argparse
import re
import subprocess  # noqa: S404 — one read-only `systemctl show`
import sys
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.escalation import humanise_hours
from sysadmin.core.schema_guard import (
    EXIT_STATUS,
    SchemaVerdict,
    schema_status,
)
from sysadmin.core.unit_failure import OWN_UNIT

#: The same three words and the same exit map as the schema check, imported
#: rather than restated.  ``mismatch`` is a claim that is false; ``unknown``
#: is a claim nobody managed to test, and rule 2 is the whole reason those
#: are not one verdict.
type Verdict = SchemaVerdict

STATUS_PATH = REPO_ROOT / "docs" / "roadmap" / "STATUS.md"

#: How many open alert titles are printed before the rest are counted.
#: A cap that drops rows silently is the roll-up defect ``SNAG-ESTATE-001``
#: names, so the overflow is stated.
MAX_NAMED_ALERTS = 5

#: One pattern per claim, anchored on the emphasis this file uses for a
#: figure it has measured.  The bold is load-bearing: it is what separates
#: the current number from the history the same sentence carries.
#:
#: The spaces are literal because :func:`flatten` has already run — see
#: there for why that is not a tidying step.
CLAIM_PATTERNS: dict[str, str] = {
    "routes": r"\*\*(\d+) routes\*\*",
    "tables": r"\*\*(\d+) tables\*\*",
    "migration_head": r"head \*\*(\d+)\*\*",
    "alerts": r"holds \*\*(\d+)\*\* unresolved",
    "daemon_start": r"restarted at \*\*(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\*\*",
    "health": r"`/health` answers \*\*(\d+)\*\*",
}

#: Checks a marker may name that carry no pattern of their own, and why
#: each one has none.  ``schema`` and ``deploy`` test the box against this
#: checkout, so there is no sentence to read (rule 3).  ``open_titles`` is
#: answered from the alert table against the whole block rather than from
#: one figure.  ``expires`` is the one family whose *members* are declared
#: by the marker rather than by this module — rule 8.
KEYLESS_CHECKS: frozenset[str] = frozenset({"schema", "deploy", "open_titles", "expires"})

#: Every name a marker may carry, **derived** from the two sets above
#: rather than written beside them — ``max_priority_for`` against
#: ``PRIORITY_MAP``'s rule, and for its reason: a third list is a third
#: thing to forget.  A marker naming anything else is reported rather than
#: ignored, because a check nobody implements is silence wearing a
#: convention's clothes.
CHECK_KEYS: frozenset[str] = frozenset(CLAIM_PATTERNS) | KEYLESS_CHECKS

#: ``<!--check:key-->``, optionally with an argument: ``<!--check:expires
#: 2026-08-25T03:32 the estate scan row-->``.  An HTML comment because it
#: must not render — the document is read by people first — and matched
#: after :func:`flatten`, so a marker may wrap onto its own line.
MARKER_RE = re.compile(r"<!--\s*check:\s*([a-z_]+)\s*([^>]*?)\s*-->")

#: A markdown code span, closing on a backtick run of its **own length**.
#: ``SNAG-DOCS-005``: a marker inside one is a *quotation*, and reading it
#: as a claim fails quietly in both directions — a quoted key nothing
#: implements is reported as a broken marker, and a quoted key that *is*
#: implemented silences the ``unclaimed`` finding beside a sentence that
#: claims nothing.
#:
#: The same-length run is what separates this fix from the naive
#: ``` `[^`]+` ``` and it was settled by running it rather than by
#: argument.  Markdown writes a span that itself contains one with a
#: doubled fence — ``the `<!--check:routes-->` marker`` — which is a live
#: shape in ``snag_list.md``; the naive pattern closes at the *inner*
#: backtick and leaves the marker bare.  ``SNAG-DOCS-005``'s check was
#: built to tell the two apart before either was written, and it did:
#: driven against the naive pattern it reported the entry *narrowed*, and
#: against this one *refuted*.  So the entry closed on a run rather than
#: on the argument this comment is making, and the check left the
#: registry with it.
#:
#: Copied in shape from :func:`sysadmin.snag_claims.strip_code_spans`
#: rather than imported.  That module is the other composition root, so
#: an import would couple two of them to share a regex, and it would put
#: a snag-list parse at the mercy of an edit made for this dashboard.
#: Behaviour is pinned across the two by ``tests/test_ops_claims.py``
#: instead: import where you can, pin where you cannot.
CODE_SPAN_RE = re.compile(r"(`+)[\s\S]*?\1")

#: The instant an ``expires`` marker carries.  Local, minute resolution,
#: and unambiguous about the *date* — which is the whole reason the marker
#: carries an instant the prose does not: "clears at 03:32" names a wall
#: clock and no day, and a pattern that guessed the day would be wrong
#: exactly once per prediction.
EXPIRY_FORMAT = "%Y-%m-%dT%H:%M"

#: How the pinned wall clock is rendered back out of an ``expires``
#: instant, to be looked for in the prose.  Rule 9.
EXPIRY_CLOCK_FORMAT = "%H:%M"


@dataclass(frozen=True)
class Claim:
    """One line of the report.

    Attributes:
        key: the identifier used in :data:`CLAIM_PATTERNS` and in tests.
        subject: what is being claimed, in words.
        kind: ``"claim"`` when the document is being tested against the
            box, ``"state"`` when the box is being tested against this
            checkout.  Rule 3 — the remedies are opposites.
        documented: what the block says, or ``None``.  On a ``claim`` that
            means the sentence could not be read; on a ``state`` check
            there is no sentence to read, which is why ``kind`` is a field
            and not an inference from this one.
        measured: what the box says, or ``None`` when it could not be
            measured.
        verdict: see :data:`Verdict`.
        note: one sentence naming the fault, its direction and its remedy.
            Empty only on ``match``.
        detail: evidence too long for ``note`` — the open alert titles,
            the file whose mtime is newer than the daemon.
    """

    key: str
    subject: str
    kind: str
    documented: str | None
    measured: str | None
    verdict: Verdict
    note: str = ""
    detail: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Reading the document
# ---------------------------------------------------------------------------


def printed_region(document: str) -> str | None:
    """The part of STATUS.md the session-opening banner shows.

    From the top of the file through the end of the Quick Status table —
    the sub-session block, the ranked recommendation and the table, which
    together are what a sitting reads before it decides anything.  Rule 1.

    Returns ``None`` when the table's heading is absent, because a region
    guessed from a file whose shape has changed would silently narrow to
    nothing and report every claim as unreadable for the wrong reason.
    """
    lines = document.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.strip().startswith("## Quick Status")),
        None,
    )
    if start is None:
        return None
    end = next(
        (i for i, line in enumerate(lines[start + 1 :], start + 1) if line.startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[:end])


def flatten(region: str) -> str:
    """The region as one line of prose, decoration removed.

    Blockquote markers stripped and every run of whitespace collapsed to a
    single space.  **This is not a tidying step, and skipping it retires
    claims silently.**  The first rewrite of the block under this check
    wrapped ``holds **2**`` and ``unresolved`` onto two lines with a ``>``
    between them, and the claim came back *unreadable* — correct by rule 2
    and useless, because ``unknown`` for a reason no reader would guess is
    how a check goes quiet.  A paragraph reflow must not be able to do
    that, so the patterns are matched against prose rather than against
    markdown.
    """
    stripped = [re.sub(r"^\s*>\s?", "", line) for line in region.splitlines()]
    return re.sub(r"\s+", " ", " ".join(stripped))


def read_claim(region: str, key: str) -> tuple[str | None, str]:
    """The value the block states for ``key``, or ``None`` and why not.

    Two distinct matches are refused rather than resolved: a block that
    states one figure two ways has already drifted, and taking the first
    would report agreement with whichever half happened to be written
    first (rule 2).
    """
    pattern = CLAIM_PATTERNS[key]
    found = {match.group(1) for match in re.finditer(pattern, flatten(region))}
    if not found:
        return None, f"the block states no figure matching /{pattern}/"
    if len(found) > 1:
        stated = ", ".join(sorted(found))
        return None, f"the block states {len(found)} different figures ({stated})"
    return found.pop(), ""


@dataclass(frozen=True)
class Marker:
    """One ``<!--check:…-->`` the block carries.

    Attributes:
        key: the check the sentence stands behind.  A name, never a value
            — see rule 7 for why that distinction is the whole design.
        argument: whatever followed it, empty for every check but
            ``expires``.
    """

    key: str
    argument: str


def read_markers(region: str) -> list[Marker]:
    """Every marker in the printed region, in the order it states them.

    Read off the *flattened* region for :func:`flatten`'s reason: a marker
    that wrapped onto its own line behind a ``>`` would otherwise stop
    being a marker, which is the silent retirement rule 2 exists to
    prevent, arriving through the mechanism meant to prevent it.

    **Code spans are removed before the read** — ``SNAG-DOCS-005``.  A
    marker between backticks is a sentence *about* the convention rather
    than a line using it, and this block is the likeliest place on the box
    for such a sentence: it carried *"One thing this block deliberately
    does not do: quote a marker"* for as long as this function could not
    tell the two apart, which made the emptiness of the entry's population
    an avoidance rather than a measurement.  See :data:`CODE_SPAN_RE` for
    why the pattern closes on a run of its own length, and why it is a
    copy rather than an import.
    """
    return [
        Marker(match.group(1), match.group(2).strip())
        for match in MARKER_RE.finditer(CODE_SPAN_RE.sub(" ", flatten(region)))
    ]


def prose_without_markers(region: str) -> str:
    """The flattened region with every marker removed.

    Rule 9 pins an ``expires`` instant against the sentence beside it, and
    a pin that searches text *containing the marker* matches the marker's
    own copy of the instant — so it passes whatever the prose says, which
    is the check agreeing with itself by construction.  Found by driving
    a reworded block through the real script rather than a fixture: the
    fixture in :class:`TestExpiry` happens to strip the marker and so was
    green throughout.
    """
    return MARKER_RE.sub(" ", flatten(region))


def load_region(path: Path | None = None) -> tuple[str | None, str]:
    """:func:`printed_region` of STATUS.md on disk, or ``None`` and why not."""
    target = path or STATUS_PATH
    try:
        document = target.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"{target} could not be read ({exc.__class__.__name__})"
    region = printed_region(document)
    if region is None:
        return None, f"{target} has no '## Quick Status' heading"
    return region, ""


# ---------------------------------------------------------------------------
# Measuring the box
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitState:
    """What systemd says about :data:`OWN_UNIT`.

    ``loaded`` is a separate field for a reason worth stating: ``systemctl
    show`` answers for a unit that does not exist, exits ``0``, and prints
    ``ActiveState=inactive`` — "nobody looked" rendered as a measurement,
    which is the exact shape this module exists to remove.  Every consumer
    gates on ``loaded`` before reading anything else.
    """

    loaded: bool
    active_state: str
    entered_at: float | None
    main_pid: str = ""
    problem: str = ""


def measure_unit(unit: str = OWN_UNIT) -> UnitState:
    """``systemctl show`` for the daemon, as data.

    ``--timestamp=unix`` is asked for rather than the default rendering,
    which is a local wall clock with an abbreviated zone name
    (``Mon 2026-08-24 09:58:28 BST``) that ``strptime`` cannot read back
    unambiguously.  ``SNAG-LOG-009``'s rule, met from the reading side:
    an epoch carries no zone, so nothing has to agree about one.
    """
    try:
        result = subprocess.run(
            [
                "systemctl",
                "show",
                unit,
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "ActiveEnterTimestamp",
                "-p",
                "MainPID",
                "--timestamp=unix",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return UnitState(
            False, "", None, problem=f"systemctl could not be run ({exc.__class__.__name__})"
        )

    props = dict(
        line.split("=", 1) for line in result.stdout.splitlines() if "=" in line
    )
    if props.get("LoadState") != "loaded":
        state = props.get("LoadState") or "no answer"
        return UnitState(False, "", None, problem=f"systemd reports {unit} as {state}")

    stamp = props.get("ActiveEnterTimestamp", "").lstrip("@")
    entered = float(stamp) if stamp.isdigit() else None
    return UnitState(True, props.get("ActiveState", ""), entered, props.get("MainPID", ""))


def measure_routes() -> tuple[int | None, str]:
    """How many routes this checkout's application declares.

    ``APIRoute`` rather than ``app.routes``, which is four longer: FastAPI
    adds ``/openapi.json``, ``/docs``, ``/docs/oauth2-redirect`` and
    ``/redoc`` as plain Starlette routes of its own.  The block's figure
    has always been the routes this repository writes, and counting
    FastAPI's would move it by four the first sitting anybody looked.
    """
    try:
        from fastapi.routing import APIRoute

        from sysadmin.main import create_app

        app = create_app()
    except Exception as exc:  # noqa: BLE001 — any import-time fault is "unknown"
        return None, f"create_app() raised {exc.__class__.__name__}"
    return len([route for route in app.routes if isinstance(route, APIRoute)]), ""


def measure_health() -> tuple[str | None, str]:
    """The status code ``GET /health`` answers with, as a string.

    A different fact from :func:`check_deploy`'s, and the pair is why both
    are worth having: systemd reporting ``active`` says the *process* is
    up, and this says the *application* is serving.  ``SNAG-DB-005`` is
    the case where they part company — the daemon was dead for 23 hours
    while ``systemctl`` had plenty to say about it, and the block's own
    sentence is about the route rather than the unit.

    Loopback rather than ``service.host``, which is ``0.0.0.0`` here and
    is a bind address rather than somewhere to send a request.
    """
    config = get_config()
    url = f"http://127.0.0.1:{config.service.port}/health"
    try:
        response = httpx.get(url, timeout=5.0)
    except Exception as exc:  # noqa: BLE001 — a daemon that will not answer is "unknown"
        return None, f"{url} did not answer ({exc.__class__.__name__})"
    return str(response.status_code), ""


@dataclass(frozen=True)
class DatabaseFacts:
    """The two counts one connection can answer, plus the open titles."""

    tables: int | None
    unresolved: int | None
    open_titles: tuple[str, ...]
    problem: str = ""


def measure_database() -> DatabaseFacts:
    """Table count and unresolved alerts, on one short-lived connection.

    The sync engine that exists for Alembic, opened and disposed —
    :func:`sysadmin.core.schema_guard.live_revision_sync`'s pattern, and
    for its reason: every caller of this module runs outside a running
    application, so ``get_engine()`` would raise before any query ran.

    ``alembic_version`` is excluded from the table count because the
    *document* excludes it — the Database row reads "14 tables (15
    counting ``alembic_version``)", so the figure being tested is the one
    without it.
    """
    config = get_config()
    schema = config.database.schema_
    engine = create_engine(config.database.sync_url)
    try:
        with engine.connect() as conn:
            tables = conn.execute(
                text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema = :schema AND table_name <> 'alembic_version'"
                ),
                {"schema": schema},
            ).scalar_one()
            rows = conn.execute(
                text(  # noqa: S608 — the schema name is configuration, not input
                    f"SELECT severity, title FROM {schema}.alerts "
                    "WHERE resolved IS false ORDER BY created_at DESC"
                )
            ).fetchall()
    except Exception as exc:  # noqa: BLE001 — an unreachable database is "unknown"
        return DatabaseFacts(
            None, None, (), f"the database did not answer ({exc.__class__.__name__})"
        )
    finally:
        engine.dispose()

    titles = tuple(f"{severity}: {title}" for severity, title in rows)
    return DatabaseFacts(int(tables), len(titles), titles)


def newest_source(package: Path | None = None) -> tuple[Path, float] | None:
    """The most recently written ``.py`` under ``sysadmin/``, and when.

    Rule 4.  This is what the daemon read at start, so it is what decides
    whether the running process is serving the checkout.  ``__pycache__``
    is skipped: it is written *by* the run, so including it would make
    every daemon look one import older than itself.
    """
    root = package or (REPO_ROOT / "sysadmin")
    newest: tuple[Path, float] | None = None
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        stamp = path.stat().st_mtime
        if newest is None or stamp > newest[1]:
            newest = (path, stamp)
    return newest


# ---------------------------------------------------------------------------
# The checks
# ---------------------------------------------------------------------------


def _local(stamp: float) -> str:
    """An epoch as the local wall clock the block writes its times in.

    The measurement is the epoch; this is only how it is rendered to sit
    beside a sentence a human wrote in local time.  ``SNAG-LOG-009``
    forbids a rendered local time *in a command*, where the reader's zone
    is unknown; here the reader is the document, whose zone is this box's.
    """
    return datetime.fromtimestamp(stamp).strftime("%Y-%m-%d %H:%M:%S")


def compare_claim(
    key: str,
    subject: str,
    documented: str | None,
    doc_problem: str,
    measured: str | None,
    measure_problem: str,
    note: str = "",
) -> Claim:
    """One document-against-box comparison, with rule 2's tri-state.

    Both sides must be present to compare.  When either is missing the
    verdict is ``unknown`` and the note names *which* side failed, because
    "the sentence has been reworded" and "PostgreSQL is down" call for
    entirely different responses from the sitting reading this.
    """
    if documented is None or measured is None:
        problems = [problem for problem in (doc_problem, measure_problem) if problem]
        return Claim(
            key, subject, "claim", documented, measured, "unknown", "; ".join(problems)
        )
    if documented == measured:
        return Claim(key, subject, "claim", documented, measured, "match")
    return Claim(key, subject, "claim", documented, measured, "mismatch", note)


def check_routes(region: str, region_problem: str) -> Claim:
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "routes")
    count, measure_problem = measure_routes()
    measured = None if count is None else str(count)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"create_app() declares {measured} routes, not {documented} — "
            "the Quick Status table is stale"
        )
    return compare_claim(
        "routes", "API routes", documented, doc_problem, measured, measure_problem, note
    )


def check_tables(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "tables")
    measured = None if facts.tables is None else str(facts.tables)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"the sysadmin schema holds {measured} tables, not {documented} "
            "(alembic_version excluded on both sides)"
        )
    return compare_claim(
        "tables", "Database tables", documented, doc_problem, measured, facts.problem, note
    )


def check_migration_head(region: str, region_problem: str, head: str | None) -> Claim:
    """The head the document names against the head this checkout packages.

    Deliberately not the same question as :func:`check_schema` below, and
    the pair is what makes the answer complete: this one catches a
    migration written since the table row was, and that one catches a
    migration nobody applied.  A document, a checkout and a database are
    three parties and two comparisons.
    """
    documented, doc_problem = (
        (None, region_problem) if not region else read_claim(region, "migration_head")
    )
    note = ""
    if documented is not None and head is not None and documented != head:
        note = f"this checkout's migrations end at {head}, not {documented}"
    return compare_claim(
        "migration_head",
        "Alembic head (documented)",
        documented,
        doc_problem,
        head,
        "the packaged head could not be read",
        note,
    )


def check_alerts(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    """Rule 5 — the count, its direction, and the titles behind it."""
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "alerts")
    measured = None if facts.unresolved is None else str(facts.unresolved)
    note = ""
    if documented is not None and measured is not None and documented != measured:
        moved = int(measured) - int(documented)
        if moved > 0:
            note = (
                f"{moved} more unresolved row(s) than the block accounts for — "
                "something opened since it was written"
            )
        else:
            note = (
                f"{-moved} fewer unresolved row(s) than the block accounts for — "
                "a row it treats as open has resolved, so an action it asks for "
                "may already be done (SNAG-ESTATE-008's founding case)"
            )
    detail: tuple[str, ...] = ()
    if facts.open_titles:
        named = facts.open_titles[:MAX_NAMED_ALERTS]
        detail = named
        if len(facts.open_titles) > MAX_NAMED_ALERTS:
            detail = (*named, f"… and {len(facts.open_titles) - MAX_NAMED_ALERTS} more")
    claim = compare_claim(
        "alerts", "Unresolved alerts", documented, doc_problem, measured, facts.problem, note
    )
    return replace(claim, detail=detail)


def check_daemon_start(region: str, region_problem: str, unit: UnitState) -> Claim:
    documented, doc_problem = (
        (None, region_problem) if not region else read_claim(region, "daemon_start")
    )
    measured = _local(unit.entered_at) if unit.entered_at is not None else None
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"{OWN_UNIT} has been active since {measured}, not {documented} — "
            "it has restarted since the block was written, and nothing recorded why"
        )
    return compare_claim(
        "daemon_start",
        "Daemon start time",
        documented,
        doc_problem,
        measured,
        unit.problem or f"{OWN_UNIT} reports no ActiveEnterTimestamp",
        note,
    )


def check_schema(status_verdict: Verdict, current: str | None, problem: str | None) -> Claim:
    """Is the live database at this checkout's head — the box, not the block.

    ``SNAG-DB-005`` ran for 23 hours because nothing asked this until a
    restart did.  The pre-commit hook blocks on it and postflight warns;
    this is the third moment, and it is the earliest one: a sitting that
    opens with the database behind is a sitting whose first restart kills
    the daemon.
    """
    return Claim(
        "schema",
        "Live schema at packaged head",
        "state",
        None,
        current,
        status_verdict,
        problem or "",
    )


def check_deploy(unit: UnitState) -> Claim:
    """Is the running daemon serving the code on disk — rule 4."""
    newest = newest_source()
    if not unit.loaded or unit.entered_at is None:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            None,
            "unknown",
            unit.problem or f"{OWN_UNIT} reports no ActiveEnterTimestamp",
        )
    if newest is None:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            None,
            "unknown",
            f"no .py found under {REPO_ROOT / 'sysadmin'}",
        )
    path, stamp = newest
    if stamp <= unit.entered_at:
        return Claim(
            "deploy",
            "Daemon serves the code on disk",
            "state",
            None,
            f"active since {_local(unit.entered_at)}",
            "match",
        )
    remedy = f"kill -TERM {unit.main_pid}" if unit.main_pid not in ("", "0") else "restart it"
    return Claim(
        "deploy",
        "Daemon serves the code on disk",
        "state",
        None,
        f"active since {_local(unit.entered_at)}",
        "mismatch",
        f"the running process predates the newest source edit — {remedy} "
        "(Restart=always brings it straight back, no sudo)",
        (f"{path.relative_to(REPO_ROOT)} written {_local(stamp)}",),
    )


def check_health(region: str, region_problem: str) -> Claim:
    """The status code the block says ``/health`` answers with."""
    documented, doc_problem = (None, region_problem) if not region else read_claim(region, "health")
    measured, measure_problem = measure_health()
    note = ""
    if documented is not None and measured is not None and documented != measured:
        note = (
            f"GET /health answers {measured}, not {documented} — the daemon is "
            "up enough for systemd and not serving"
        )
    return compare_claim(
        "health", "/health answers", documented, doc_problem, measured, measure_problem, note
    )


def check_open_titles(region: str, region_problem: str, facts: DatabaseFacts) -> Claim:
    """Is every unresolved row named somewhere in the block?

    :func:`check_alerts` compares the *count*, which is what moves when a
    row opens or closes.  This asks the finer question the count cannot:
    a swap — one row resolving as another opens — holds the total still
    while the block's sentence about *which* rows are open goes silently
    wrong.  Today's block names both of its two and explains why each is
    expected; the count alone would agree with a block naming neither.

    **One direction only, and the other has an owner.**  A row the block
    names that has since resolved is ``SNAG-ESTATE-008``'s founding case
    and is already reported, by :func:`check_alerts`'s *fall* note.  What
    that note cannot say is that a row nobody wrote about is open, so this
    is the direction taken here — and a title is matched as a substring
    because the block quotes it inside backticks and prose around it.
    """
    if facts.open_titles is None or facts.unresolved is None:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", None, None, "unknown",
            facts.problem,
        )
    if not region:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", None,
            f"{facts.unresolved} open", "unknown", region_problem,
        )
    prose = flatten(region)
    # ``open_titles`` are rendered "severity: title" for the alert report;
    # the block quotes the title alone, so the severity is dropped before
    # the substring test rather than being written into the document.
    unnamed = tuple(
        entry for entry in facts.open_titles if entry.split(": ", 1)[-1] not in prose
    )
    documented = f"{len(facts.open_titles) - len(unnamed)} named"
    measured = f"{len(facts.open_titles)} open"
    if not unnamed:
        return Claim(
            "open_titles", "Open rows named in the block", "claim", documented, measured, "match"
        )
    return Claim(
        "open_titles",
        "Open rows named in the block",
        "claim",
        documented,
        measured,
        "mismatch",
        f"{len(unnamed)} unresolved row(s) the block does not mention — a row "
        "nobody wrote about is the one a sitting will not account for",
        tuple(f"unnamed: {title}" for title in unnamed),
    )


def _convention(key: str, subject: str, note: str) -> Claim:
    """A finding about the block's own bookkeeping — rule 7's third kind.

    Neither the document's figures nor the box are wrong; what is wrong is
    the pairing between them, and the remedy is a marker rather than a
    reworded sentence or a ``kill -TERM``.  Rule 3 keeps ``claim`` and
    ``state`` apart because their remedies are opposites; this is a third
    remedy, so it is a third kind rather than a flavour of either.
    """
    return Claim(key, subject, "convention", None, None, "unknown", note)


def check_markers(region: str, markers: list[Marker]) -> list[Claim]:
    """The convention's two failure modes — rule 7.

    **A marker naming a check nobody implements** is a typo, a rename, or
    a check deleted out from under the sentence that relies on it.  Each
    of the three ends the same way: the sentence looks verified and is
    not, which is worse than prose, because prose does not claim to have
    been checked.

    **A figure this module can test that no marker claims** is the
    convention's whole point — ``SNAG-ESTATE-008`` asked for *"every ops
    action names the check that closes it"*, and this is the only place
    that can be enforced.  Note the asymmetry with the checks themselves:
    every pattern-bearing claim still runs whether or not a marker names
    it, so the marker can never make a check quieter.  It exists to make
    an *unmarked* claim loud, never to gate a marked one — a convention
    that could switch a check off would be a way to retire one by
    editing a document, which is precisely what rule 2 refuses.
    """
    named = {marker.key for marker in markers}
    findings = [
        _convention(
            f"marker:{key}",
            f"Block names check '{key}'",
            f"nothing implements '{key}' — the sentence relying on it is unchecked "
            f"(known: {', '.join(sorted(CHECK_KEYS))})",
        )
        for key in sorted(named - CHECK_KEYS)
    ]
    if not region:
        return findings
    findings.extend(
        _convention(
            f"unclaimed:{key}",
            f"Unclaimed figure '{key}'",
            "the block states a figure this check can test and no line names it — "
            f"add <!--check:{key}--> beside the sentence",
        )
        for key in sorted(CLAIM_PATTERNS)
        if key not in named and read_claim(region, key)[0] is not None
    )
    return findings


def check_expiry(marker: Marker, region: str, now: datetime) -> Claim:
    """One prediction, against the clock — rules 8 and 9.

    ``SNAG-ESTATE-011`` was opened by a block asserting a retention
    boundary **three hours before it happened**: "the row clears at 03:32
    with nothing done", written at 00:30.  Nothing about that sentence was
    wrong, and nothing about it could be measured either — which is why it
    is a different class from every other claim here and needs a different
    mechanism.  A prediction is not checked, it is *timed*: before its
    moment it stands, and after its moment it is ``unknown`` until a human
    has looked, because "the prediction came true" and "nobody went back"
    are the two readings and only one of them is health.

    ``unknown`` rather than ``mismatch`` deliberately.  A passed boundary
    does not make the sentence false — rule 2's whole point is that a
    claim nobody managed to test is its own verdict.
    """
    parts = marker.argument.split(None, 1)
    label = parts[1] if len(parts) > 1 else "prediction"
    subject = f"Block predicts: {label}"
    if not parts:
        return _convention(
            "expires:?", subject, "the marker carries no instant — expected "
            f"<!--check:expires {now.strftime(EXPIRY_FORMAT)} what it is about-->",
        )
    try:
        moment = datetime.strptime(parts[0], EXPIRY_FORMAT)
    except ValueError:
        return _convention(
            f"expires:{parts[0]}", subject,
            f"'{parts[0]}' is not an instant of the form {EXPIRY_FORMAT}",
        )

    key = f"expires:{parts[0]}"
    clock = moment.strftime(EXPIRY_CLOCK_FORMAT)
    if region and clock not in prose_without_markers(region):
        return Claim(
            key, subject, "claim", parts[0], _local(moment.timestamp()), "unknown",
            f"the marker names {clock} and the block's prose does not — pinned rather "
            "than trusted, because the instant is the one fact stated twice here",
        )

    hours = (moment - now).total_seconds() / 3600
    if hours > 0:
        return Claim(
            key, subject, "claim", parts[0], f"{humanise_hours(hours)} to run", "match"
        )
    return Claim(
        key, subject, "claim", parts[0], f"passed {humanise_hours(-hours)} ago", "unknown",
        "the block predicts a moment that has passed and nobody re-measured it — "
        "measure it or reword the sentence",
    )


def check_all(path: Path | None = None, now: datetime | None = None) -> list[Claim]:
    """Every check, measured once each, state checks first.

    The state checks run even when STATUS.md cannot be read at all: a
    missing document is a reason to know less about the document, never a
    reason to stop asking whether the box is behind its checkout.
    """
    region, region_problem = load_region(path)
    facts = measure_database()
    unit = measure_unit()
    status = schema_status()
    region_text = region or ""
    markers = read_markers(region_text)
    moment = now or datetime.now()

    return [
        check_schema(status.verdict, status.current, status.problem),
        check_deploy(unit),
        check_routes(region_text, region_problem),
        check_tables(region_text, region_problem, facts),
        check_migration_head(region_text, region_problem, status.head),
        check_alerts(region_text, region_problem, facts),
        check_daemon_start(region_text, region_problem, unit),
        check_health(region_text, region_problem),
        check_open_titles(region_text, region_problem, facts),
        *(
            check_expiry(marker, region_text, moment)
            for marker in markers
            if marker.key == "expires"
        ),
        *check_markers(region_text, markers),
    ]


def overall(claims: list[Claim]) -> Verdict:
    """``mismatch`` outranks ``unknown``, which outranks ``match``.

    Not ``max()`` over :data:`EXIT_STATUS`, which would put ``unknown``
    (2) above ``mismatch`` (1) and report a check that failed to run as
    more urgent than a claim measured false.
    """
    verdicts = {claim.verdict for claim in claims}
    if "mismatch" in verdicts:
        return "mismatch"
    if "unknown" in verdicts:
        return "unknown"
    return "match"


MARKERS: dict[str, str] = {"match": "ok", "mismatch": "no", "unknown": "??"}


def render(claims: list[Claim]) -> list[str]:
    """The report as lines, marker first so a shell caller can colour it."""
    lines = []
    for claim in claims:
        sides = []
        if claim.kind == "claim":
            sides.append(f"block says {claim.documented or '—'}")
        if claim.kind != "convention":
            sides.append(f"measured {claim.measured or '—'}")
        line = f"{MARKERS[claim.verdict]} {claim.subject}"
        if sides:
            line += f": {', '.join(sides)}"
        if claim.note:
            line += f" — {claim.note}"
        lines.append(line)
        lines.extend(f"   {item}" for item in claim.detail)
    return lines


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-check-claims`` — does the block that opens a sitting hold?

    Exit status is :data:`sysadmin.core.schema_guard.EXIT_STATUS`:
    ``0`` every claim holds, ``1`` at least one is false, ``2`` at least
    one could not be tested and none is false.
    """
    parser = argparse.ArgumentParser(
        description="Re-measure the ops claims docs/roadmap/STATUS.md opens with."
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=None,
        help=f"the document to read claims from (default {STATUS_PATH})",
    )
    args = parser.parse_args(argv)

    claims = check_all(args.status_file)
    for line in render(claims):
        print(line)
    return EXIT_STATUS[overall(claims)]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
