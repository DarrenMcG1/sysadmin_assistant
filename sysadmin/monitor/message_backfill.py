"""Re-derive stored messages a later ``format: json`` declaration left frozen.

``SNAG-LOG-008``.  :func:`~sysadmin.monitor.journal.unwrap_json_message` is
applied at **read** time, by :func:`~sysadmin.monitor.journal.read_journal`,
against the declaration in force at that moment.  A source that gains
``format: json`` after it has already been ingested therefore keeps the raw
envelope in ``log_entries.message`` for ever: nothing revisits a stored row,
and ``signature()`` and ``alert_title()`` are both computed from ``message``.
This module is the second caller — the one the entry's *"no read will ever
unwrap them"* names as its own refutation.

**It is a repair, not a migration.**  A data-only Alembic revision would move
the packaged head for no structural reason, and the box would then need
``alembic upgrade head`` plus a restart or ``schema_guard`` refuses to boot —
which is ``SNAG-DB-005``'s twenty-three hours bought for ten rows.  It would
also fix this population once, where the defect is a *class*: it recurs for
every source whose declaration arrives after its rows do.  So it is a console
script in the shape the three checkers already use, run by hand, idempotent,
and a dry run unless the caller says otherwise (``files/actions.py``'s
contract).

Six rules, four of them the opposite of what the entry proposed:

1. **The new message is derived from ``message``, never from ``raw_line``.**
   The entry proposes ``raw_line`` and prices in its 2000-character
   truncation as the reason a backfill "is not free".  Read what
   ``read_journal`` composes: ``message = message_text(MESSAGE)`` first, then
   ``unwrap_json_message`` on **that same string** only where the source
   declares it.  A ``text``-declared row's stored ``message`` is therefore
   exactly the unwrap's input, and applying the unwrap to it reproduces the
   ``json`` read by construction.  Going through ``raw_line`` instead means
   re-implementing ``message_text(json.loads(line)["MESSAGE"])`` — a second
   statement of the reader's parse, free to drift from it.  Measured over the
   live population: the two derivations agree **10 of 10**, so the cheaper
   one is also the exact one.

2. **``raw_line`` is the *witness*, which is the job it can do and the
   derivation is not.**  "Does this message look like JSON" cannot tell a
   frozen envelope from a correctly-unwrapped message that is itself a JSON
   document, and acting on the guess double-unwraps the second.  The exact
   test is byte equality against the record's own ``MESSAGE``: a row nothing
   ever unwrapped still holds it verbatim, and an unwrapped row holds the
   fragment.  So the truncation the entry feared is real and lands on the
   *witness* rather than on the derivation — which is the weaker half, since
   a row that cannot be witnessed is refused rather than corrupted.

3. **The population is the declaration's, never the shape's.**  A candidate
   is a row whose source declares ``format: json`` **today**; a sweep for
   JSON-looking messages across every source would rewrite a plain-text
   service that happened to log a document, which is recognising an
   application rather than honouring a statement —
   :func:`unwrap_json_message`'s own rule, and the reason the declaration
   exists at all.  The set is taken from
   :func:`~sysadmin.monitor.services.composed_log_sources` and resolved
   through :func:`~sysadmin.monitor.services.stored_source_name`, because
   ``log_entries.source`` holds the **unit** while the declaration is keyed
   on the ``name`` — the trap ``log_source_scopes`` records from the other
   side, where keying on ``name`` yields an empty map that reads as success.

4. **Idempotence is a property, not a flag.**  There is no "backfilled"
   column and no marker in ``metadata``: a repaired row fails rule 2's
   witness on the next run, because its ``message`` no longer equals the
   record's ``MESSAGE``.  A flag would be a second statement of a fact the
   data already carries, and one that can disagree with it.

5. **Nothing schedules this.**  ``run_retention`` and the agents mutate rows
   unattended; a repair that rewrites stored history must not, for the reason
   ``check-migrations.sh`` is asserted never to run ``upgrade`` — an
   unattended rewrite reaches production with nobody watching.
   ``tests/test_message_backfill.py`` pins that no job plan or agent reaches
   it.

6. **Every way of not-knowing is reported and none of them is success.**  A
   row that cannot be witnessed and a row whose envelope will not parse are
   distinct from "nothing to do", and both push the exit status to ``2`` —
   ``ports_checked``'s rule, zero-because-clean never served as
   zero-because-blind.

Measured on this box 2026-08-28, which is what decided this was a backfill
and not a closure as moot: the population is **10 rows and intact**.  They
left the trend's current window on 2026-08-24, leave ``GET /api/logs/trends``
altogether on 2026-08-31 and ``log_entries`` at retention on 2026-09-17 — so
the calendar was going to empty it, and had not.  All ten unwrap, all ten are
witnessed, ``logger`` is recovered for all ten, and the ten distinct
signatures they serve today collapse to **two** (``alert_raised`` nine times,
one ``api.auth_token is not set …``).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.monitor.journal import message_text, unwrap_json_message
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import (
    composed_log_sources,
    load_services_singleton,
    stored_source_name,
)

logger = logging.getLogger(__name__)

#: The declaration this repair exists for.  Named rather than written into
#: the comparison so the one string sits beside the rule that reads it;
#: ``LogSource.format`` is the vocabulary's owner.
BACKFILL_FORMAT = "json"

#: Exit statuses, in the shape ``sysadmin-check-schema`` established.
EXIT_CLEAN = 0
EXIT_WORK_PENDING = 1
EXIT_UNKNOWN = 2


@dataclass(frozen=True)
class FrozenRow:
    """One stored row whose message still carries the envelope.

    Attributes:
        entry_id: the ``log_entries`` primary key.
        source: the value in ``log_entries.source`` — the unit.
        before: the message as stored, envelope and all.
        after: what the reader would have stored had the declaration
            been in force.
        envelope: the metadata the unwrap gave up for free, merged into
            ``metadata`` on apply.  Empty is normal, not a failure.
    """

    entry_id: UUID
    source: str
    before: str
    after: str
    envelope: dict[str, str]


@dataclass(frozen=True)
class BackfillReport:
    """What one pass found, and whether it wrote anything.

    ``frozen`` is the work; ``unwitnessed`` and ``unrecoverable`` are the
    two ways of not-knowing rule 6 keeps apart from an empty ``frozen``.

    Attributes:
        sources: the units scanned, resolved from the declaration.
        scanned: rows read for those units.
        frozen: rows that unwrap and are witnessed as never unwrapped.
        unwitnessed: rows that unwrap but whose ``raw_line`` cannot say
            they were never unwrapped — refused, because acting on them
            risks a second unwrap.
        unrecoverable: rows witnessed as never unwrapped whose envelope
            will not parse, so nothing can be re-derived.  A message cut
            at :data:`~sysadmin.monitor.log_aggregator.STORED_MESSAGE_CHARS`
            lands here.
        applied: whether the rewrites were committed.
    """

    sources: tuple[str, ...]
    scanned: int
    frozen: tuple[FrozenRow, ...] = ()
    unwitnessed: tuple[UUID, ...] = ()
    unrecoverable: tuple[UUID, ...] = ()
    applied: bool = False

    @property
    def blind(self) -> bool:
        """Did anything defeat measurement rather than come back clean?"""
        return bool(self.unwitnessed or self.unrecoverable)


def json_declared_sources(agent_config: Any) -> tuple[str, ...]:
    """Units whose rows the declaration says should have been unwrapped.

    Rule 3.  Both halves are borrowed rather than restated:
    :func:`composed_log_sources` is the one statement of which sources this
    daemon ingests (a set built from ``services.yaml`` alone would omit
    ``kernel``), and :func:`stored_source_name` is the one statement of what
    a source's rows carry in ``log_entries.source``.  A source declaring
    neither a unit nor a path yields ``None`` there and is dropped, because
    it can produce no rows to repair.
    """
    return tuple(
        sorted(
            {
                stored
                for source in composed_log_sources(agent_config)
                if source.format == BACKFILL_FORMAT
                and (stored := stored_source_name(source)) is not None
            }
        )
    )


def record_message(raw_line: str | None) -> str | None:
    """The journal record's own ``MESSAGE``, or ``None`` if unreadable.

    ``None`` covers an absent ``raw_line`` and one cut at 2000 characters —
    the truncation the entry names.  It is a *refusal*, never a fallback:
    the caller has no evidence either way, and rule 2's whole point is that
    guessing here double-unwraps a row whose real message is a document.
    """
    if not raw_line:
        return None
    try:
        record = json.loads(raw_line)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    return message_text(record.get("MESSAGE"))


def never_unwrapped(message: str, raw_line: str | None) -> bool | None:
    """Was this row stored without the unwrap ever being applied?

    ``True``/``False``/``None`` rather than a bool, because "no" and "cannot
    tell" have opposite remedies and one of them must not read as the other
    — ``ports_checked``'s rule at the size of a predicate.

    The test is byte equality against the record's ``MESSAGE``.  It is exact
    in both directions: a row read under ``text`` stored ``MESSAGE``
    verbatim, and a row read under ``json`` stored a fragment of it, which
    can equal the whole only for a record the unwrap declined — and such a
    record is not a candidate, since it does not unwrap now either.
    """
    stored = record_message(raw_line)
    if stored is None:
        return None
    return stored == message


async def plan_backfill(session: Any, sources: tuple[str, ...] | None = None) -> BackfillReport:
    """Measure without writing.  The dry run *is* this function.

    Split from :func:`apply_backfill` so the report a caller reads and the
    rewrites it authorises are the same objects — a second scan between
    deciding and writing could act on rows nobody was shown.
    """
    if sources is None:
        load_services_singleton()
        sources = json_declared_sources(get_config().agents.log_aggregator)
    if not sources:
        return BackfillReport(sources=(), scanned=0)

    rows = (
        await session.execute(select(LogEntry).where(LogEntry.source.in_(sources)))
    ).scalars().all()

    frozen: list[FrozenRow] = []
    unwitnessed: list[UUID] = []
    unrecoverable: list[UUID] = []

    for row in rows:
        after, envelope = unwrap_json_message(row.message)
        if after != row.message:
            witness = never_unwrapped(row.message, row.raw_line)
            if witness is None:
                unwitnessed.append(row.id)
            elif witness:
                frozen.append(
                    FrozenRow(
                        entry_id=row.id,
                        source=row.source,
                        before=row.message,
                        after=after,
                        envelope=envelope,
                    )
                )
            # witness False: the row was read under the declaration and its
            # message merely happens to be a document.  Leaving it alone is
            # rule 2 working, so it is neither counted nor reported.
            continue
        # A message that will not unwrap is ordinarily a plain line the
        # declaration correctly left alone.  It is only a *fault* when the
        # witness says nothing ever unwrapped it and it still looks like an
        # envelope — a cut at STORED_MESSAGE_CHARS is the reachable case.
        if row.message.startswith("{") and never_unwrapped(row.message, row.raw_line):
            unrecoverable.append(row.id)

    return BackfillReport(
        sources=tuple(sources),
        scanned=len(rows),
        frozen=tuple(frozen),
        unwitnessed=tuple(unwitnessed),
        unrecoverable=tuple(unrecoverable),
    )


async def apply_backfill(session: Any, report: BackfillReport) -> BackfillReport:
    """Rewrite the rows the report names.  Nothing else is touched.

    ``metadata`` is **merged and reassigned**, never mutated in place: the
    reader's ``pid``/``hostname``/``syslog_identifier`` are facts about the
    record and stay, the envelope adds ``logger``, and SQLAlchemy does not
    track mutation inside a plain JSONB dict — an in-place update looks like
    it worked and writes nothing (``SNAG-AGENT-005``'s rule 3).

    The commit belongs to the caller's context manager.  ``raw_line`` is
    never rewritten: it is the record verbatim and the witness rule 2 needs
    on the next run.
    """
    if not report.frozen:
        return report

    by_id = {row.entry_id: row for row in report.frozen}
    entries = (
        await session.execute(select(LogEntry).where(LogEntry.id.in_(by_id)))
    ).scalars().all()

    for entry in entries:
        planned = by_id[entry.id]
        # Re-checked rather than trusted: the plan was made against a read
        # of this same session, but a row that moved between the two must
        # not be rewritten from a stale `before`.
        if entry.message != planned.before:
            continue
        entry.message = planned.after
        entry.metadata_ = {**(entry.metadata_ or {}), **planned.envelope}

    logger.info(
        "message_backfill_applied",
        extra={"rows": len(entries), "sources": list(report.sources)},
    )
    return BackfillReport(
        sources=report.sources,
        scanned=report.scanned,
        frozen=report.frozen,
        unwitnessed=report.unwitnessed,
        unrecoverable=report.unrecoverable,
        applied=True,
    )


def render(report: BackfillReport, verbose: bool = False) -> str:
    """The report as plain text, for a shell caller."""
    scanned = ", ".join(report.sources) or f"(no source declares {BACKFILL_FORMAT})"
    lines = [f"sources: {scanned} — {report.scanned} rows scanned"]
    verb = "rewritten" if report.applied else "would be rewritten"
    lines.append(f"{len(report.frozen)} frozen {verb}")
    if verbose:
        for row in report.frozen:
            lines.append(f"  {row.entry_id} {row.before[:60]!r} -> {row.after[:60]!r}")
    if report.unwitnessed:
        lines.append(
            f"{len(report.unwitnessed)} refused: raw_line cannot witness that they "
            "were never unwrapped, and rewriting one risks a second unwrap"
        )
    if report.unrecoverable:
        lines.append(
            f"{len(report.unrecoverable)} unrecoverable: witnessed as never unwrapped "
            "but the envelope will not parse (a message cut at its stored cap)"
        )
    return "\n".join(lines)


async def run(confirm: bool) -> BackfillReport:
    """One pass, on its own engine.

    ``get_scheduler_session`` rather than the application's pooled factory:
    this runs as a console script outside the daemon, where ``get_engine()``
    would raise, and a pooled asyncpg connection belongs to the loop that
    opened it (``SNAG-TRAY-008``'s deployment defect, one caller over).
    """
    async with get_scheduler_session() as session:
        report = await plan_backfill(session)
        if confirm and report.frozen:
            report = await apply_backfill(session, report)
            await session.commit()
        return report


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-backfill-messages`` — repair rows a late declaration froze.

    A dry run by default.  Exit status, in the shape the three checkers
    already use:

    ==========  =====================================================
    exit        meaning
    ==========  =====================================================
    ``0``       nothing frozen, or the rewrites were applied cleanly
    ``1``       frozen rows found and nothing was written
    ``2``       something defeated measurement — see rule 6
    ==========  =====================================================
    """
    parser = argparse.ArgumentParser(
        description=(
            "Re-derive log_entries.message for rows ingested before their "
            "source declared format: json. Dry run unless --confirm."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="write the rewrites (without this nothing is changed)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print every row that would be rewritten",
    )
    args = parser.parse_args(argv)

    try:
        report = asyncio.run(run(confirm=args.confirm))
    except Exception as exc:  # noqa: BLE001 — a shell caller needs the reason
        print(f"unknown: {exc}", file=sys.stderr)
        return EXIT_UNKNOWN

    stream = sys.stderr if (report.frozen and not report.applied) or report.blind else sys.stdout
    print(render(report, verbose=args.verbose), file=stream)

    if report.blind:
        return EXIT_UNKNOWN
    if report.frozen and not report.applied:
        return EXIT_WORK_PENDING
    return EXIT_CLEAN


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
