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

from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
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
}


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


def check_all(path: Path | None = None) -> list[Claim]:
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

    return [
        check_schema(status.verdict, status.current, status.problem),
        check_deploy(unit),
        check_routes(region_text, region_problem),
        check_tables(region_text, region_problem, facts),
        check_migration_head(region_text, region_problem, status.head),
        check_alerts(region_text, region_problem, facts),
        check_daemon_start(region_text, region_problem, unit),
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
        sides.append(f"measured {claim.measured or '—'}")
        line = f"{MARKERS[claim.verdict]} {claim.subject}: {', '.join(sides)}"
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
