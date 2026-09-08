"""A service holding a GPU context created before the last card reset.

`ADR-0007 <../../docs/adr/0007-a-poisoned-gpu-context-is-a-predicate.md>`_,
and the design half of ``SNAG-GPU-001``.

**There is no state here, which is why there is no owner to argue about.**
"This service holds a GPU context created before the last reset" is a
*predicate* over two instants the box already publishes durably and
independently — a unit's ``ActiveEnterTimestamp`` and the newest
``log_entries`` row whose ``(source, signature)`` is a key of
:data:`~sysadmin.monitor.log_aggregator.CRITICAL_SIGNATURES`.  Nothing
opens it, nothing closes it, and every poll recomputes it from scratch.

So the owner is the check that already writes the ``service_health`` row
— :meth:`~sysadmin.monitor.agent.SysAdminAgent._check_http_and_unit` —
and the second-owner defect this repository has found at seven scales is
avoided **by construction rather than by argument**.  Nothing here writes
a row, raises an alert or holds a lifecycle; this module answers a
question and the caller records the answer beside the reading it already
had.

The recorded reading is :data:`POISONED_STATUS` — ``degraded``, a fault,
and it deducts.  ``skipped`` was refused: ``STATUS_READINGS`` classifies
it as ``unwatched`` and its meaning is *somebody decided not to look, and
recorded the decision*, both halves of which are false here — the check
did look and no declaration says not to.  It would also drop the row from
:data:`~sysadmin.monitor.reliability.UNMEASURED_STATUSES`' rates
entirely, so 79.9 measured hours of a server that could not serve would
cost it nothing.  That is ``SNAG-SVC-001``'s defect run in reverse.

Five rules, four of them the opposite of the obvious implementation and
every one settled against 34 days of the live journal rather than by
argument.

1. **The population is a declaration, never a role.**  ``role:
   inference`` names four services in ``services.yaml`` and is the
   cheapest rule available; keyed on it this reading ships **267 false
   alarms**.  ``venture-embed`` runs ``llama-server … -ngl 0`` — no
   offloaded layers, no resident VRAM — and served 267 of its 823
   successful embeddings *while the predicate was true*, across the same
   twelve resets, with zero aborts in the unit's whole retained history.
   On the two units that do hold VRAM the separation is total in both
   directions: 16 of 16 aborts preceded by a true predicate, and not one
   of 11,565 successful requests served while it was true.  So
   ``ServiceEntry.holds_vram`` is honoured as a *statement*, which is
   :func:`~sysadmin.monitor.journal.unwrap_json_message`'s rule met from
   a new direction.  Reading ``-ngl`` out of the unit's ``ExecStart`` is
   the other cheap rule and is refused for the same reason plus a
   stronger one — it makes this repository a parser of a command line
   another repository owns.

2. **The comparison is strict, and strictness buys less than ADR-0007
   claims for it.**  ``--timestamp=unix`` renders whole seconds, and
   truncation moves a unit's start instant **earlier**, which makes the
   predicate *more* likely to be true.  A tie is therefore not flagged —
   ``SNAG-LOG-009`` rule 2's ``int`` → :func:`math.ceil` lesson read the
   other way round.

   That decision is right and its stated reach is not.  The ADR says the
   strictness *"corrects exactly the direction the truncation errs in"*;
   it corrects the **exact** tie, and the truncation's error is up to a
   **full second**.  A unit that really started at ``19:43:01.9`` reads
   ``19:43:01`` and is flagged against a reset at ``19:43:01.696`` that
   it actually survived.  Worse, the exact tie has an **empty population
   by construction**: ``logged_at`` is journald's
   ``__REALTIME_TIMESTAMP`` at microsecond precision, so it equals a
   whole-second instant only when a reset lands on ``.000000``, and every
   one of the eight stored resets carries microseconds.  So the branch
   the strictness protects is unreachable on real data and the residual
   window it does not protect is the one that can fire — which is
   ``SNAG-GPU-002``, filed rather than implied.

   It is kept because the residual is bounded and measured, not because
   it is absent: the shortest observed gap between a reset and the abort
   it explains is **3.4 minutes**, so the error window is 0.5 % of the
   margin.  ``--timestamp=us+utc`` closes it and costs a wall-clock parse;
   it is the recorded alternative if a sub-second case is ever produced.

3. **The database narrows and Python decides, and the floor is exact
   rather than a bound.**  ``signature`` is not a column, so normalising
   in SQL would be a second implementation of the identity the alert
   family is keyed on — :mod:`~sysadmin.monitor.log_trends` rule 1.  What
   makes the honest version affordable is that a reset *older* than the
   unit's start makes the predicate false by definition, so
   ``logged_at >= started_at`` excludes nothing that could change the
   answer.  Measured on the live table 2026-09-08: the unfloored grouped
   read is a parallel sequential scan at **69,810 buffers — 64,007 of
   them reads rather than cache hits, half a gigabyte — and ~35 ms**,
   while the same read floored at ``alfred-inference``'s start instant is
   an index scan on ``idx_log_entries_source_time`` at **6,855 buffers,
   every one a hit, and ~15 ms**.  ``GROUP BY`` rather than ``DISTINCT
   ON``, which reads the identical 6,855 buffers and then sorts them:
   85 ms against 15 ms for the same answer.
   Note the floor is ``>=`` and rule 2's strictness is applied in Python:
   the SQL is a pre-filter that may admit a tie, and the authority
   refuses it — :func:`~sysadmin.monitor.journal.read_journal`'s ``-p``
   rule, where the server-side narrowing exists to bound the read and the
   Python filter is still what decides.

4. **A row-count bound was refuted by the table.**  "Read the newest N
   kernel rows and sign them" is the obvious implementation and would
   have needed N ≈ 50,000: measured 2026-09-08, **49,527** kernel rows
   sit newer than the newest stored reset, which is 1.7 days old.  The
   same span holds **173 distinct messages**, so grouping is what bounds
   the answer and a count never could — the anti-correlation
   :mod:`~sysadmin.monitor.log_trends` rule 1 records, arriving in a
   third family.

5. **Every way of not-knowing is a reading and none of them is
   ``False``.**  ``ActiveEnterTimestamp`` is **empty** for an inactive
   unit — measured against ``venture-chat-large.service``, which is
   ``monitor: false`` and inactive by design — and a ``systemctl`` query
   can fail outright.  A unit whose start instant cannot be read yields
   *no reading*: the term is skipped, the status the check already
   reached stands, and :data:`DETAIL_KEY` says which way it was not
   known.  ``ports_checked``'s rule — zero because nothing was wrong must
   never be served as zero because nobody looked — at the size of one
   term in one check.

**The estate publishes the same instant now, and it is deliberately not
read** (2026-09-08, estate message ``6eba763a`` and their ADR-0133).  A
granted GPU lease carries ``card_reset_at``, and ``estate.queue.Lease``
parses it.  The ruling that came with it is that a lease stays a promise
about *units* — the estate publishes when the card died, this repository
holds when its server started, and the comparison is ours — so that field
is a second witness of one half rather than an answer.  Three reasons not
to take it, in order of weight.  It exists **only at a grant**, and
``active_lease`` is ``null`` on every occasion anyone has looked, so it
cannot answer a 300-second poll.  Reading it would make a health reading
depend on 8400 being up, which :mod:`sysadmin.estate.judgements` rule 3
refuses on the second-owner argument this whole module is built to avoid.
And ``log_entries`` already holds the fact, keyed the way the alert family
is keyed and retained for thirty days.  ADR-0007 §5 anticipated the
opposite ruling and said this reading would be correct under either; it
is, and this records which one arrived.

**No boot id is read, and that was checked rather than assumed.**
``log_entries`` retains a reset row for 30 days, so the newest declared
reset can belong to a previous boot — but every unit start instant is
necessarily after the boot that follows it, so the comparison already
answers ``False``.  Reading a boot id would be a second statement of an
ordering the two instants already carry.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.monitor.log_aggregator import CRITICAL_SIGNATURES
from sysadmin.monitor.log_signature import signature
from sysadmin.monitor.models.log_entry import LogEntry

__all__ = [
    "DETAIL_KEY",
    "POISONED_STATUS",
    "ResetSighting",
    "declared_reset_keys",
    "declared_reset_sources",
    "candidate_statement",
    "newest_declared_reset",
    "reset_since",
    "unreadable_reading",
    "verdict_reading",
]

#: Where the derivation lands in ``service_health.details``.
#:
#: One key holding a small mapping rather than several flat keys, so a
#: reader of a stored row can tell "this term did not run" from "this
#: term ran and found nothing" without comparing key sets — Session 128's
#: rule, where a key present only sometimes is the absent-versus-present
#: collapse one level down.  Every reading this module produces carries
#: it, and the *value* is what differs.
DETAIL_KEY = "gpu_context"

#: The reading recorded for a service whose GPU context predates the last
#: card reset.
#:
#: A literal rather than a derivation, because
#: :data:`~sysadmin.monitor.models.service_health.STATUS_READINGS` says
#: which readings exist and nothing in it says which one means *this*.
#: ``STATUS_READINGS`` classifies it as a fault, which is the half that
#: matters and which a test pins.
POISONED_STATUS = "degraded"


@dataclass(frozen=True)
class ResetSighting:
    """A declared card reset, and the row that declared it."""

    at: datetime
    #: The **normalised** signature, which is the key
    #: :data:`CRITICAL_SIGNATURES` is stated in — not the verbatim line.
    #: A reader wanting the line has ``logged_at`` and the source.
    signature: str


def declared_reset_keys() -> frozenset[tuple[str, str]]:
    """``(source, signature)`` pairs :data:`CRITICAL_SIGNATURES` declares.

    Derived rather than restated.  A second literal here is
    ``SNAG-DB-003``'s shape and would drift on the next kernel reword —
    which has already happened once, on 2026-09-04, when amdgpu dropped
    its redundant device prefix and a declaration written from the LTS
    journal matched nothing.
    """
    return frozenset(CRITICAL_SIGNATURES)


def declared_reset_sources() -> tuple[str, ...]:
    """The ``log_entries.source`` values a declared reset can arrive on.

    Sorted so the emitted SQL is stable across processes — a set's
    iteration order is not, and an unstable ``IN`` list makes two
    identical reads look different in a query log.
    """
    return tuple(sorted({source for source, _ in declared_reset_keys()}))


def newest_declared_reset(
    rows: Iterable[tuple[str, str, datetime]],
    *,
    after: datetime,
) -> ResetSighting | None:
    """The newest declared reset in ``rows`` strictly newer than ``after``.

    ``rows`` are ``(source, message, logged_at)`` — one per distinct
    message, already grouped by the database (rule 3).  The message is
    signed **here**, so this function and the alert family cannot come to
    disagree about what a reset is.

    ``after`` is applied strictly (rule 2): a row stamped at exactly the
    unit's start instant is *not* a reset the unit's context predates,
    and second truncation is why the tie falls that way.
    """
    newest: ResetSighting | None = None
    for source, message, logged_at in rows:
        sig = signature(message)
        if (source, sig) not in declared_reset_keys():
            continue
        if logged_at <= after:
            continue
        if newest is None or logged_at > newest.at:
            newest = ResetSighting(at=logged_at, signature=sig)
    return newest


def candidate_statement(started_at: datetime):
    """The narrowing read, as a statement a test can compile.

    Lifted out of :func:`reset_since` because **its two clauses cannot be
    reached by a behavioural test**.  Both are cost rather than meaning:
    the floor is exact (rule 3) and the grouping is a projection, so
    deleting either leaves every answer identical and every test green —
    driven, not assumed, as the tenth of ten mutations against
    ``tests/test_gpu_context.py``.  ``abandoned_runs``' ``IS NOT NULL``
    conjunct is the same shape and took the same remedy: a clause whose
    removal is invisible in behaviour is pinned by compiling the
    statement.

    Their visibility is the point.  Without the floor this is a parallel
    sequential scan of ``log_entries`` — half a gigabyte read every 300
    seconds — and without the grouping the adapter hands ~50,000 rows to
    a Python loop to answer a question about 173 distinct messages.
    """
    return (
        select(
            LogEntry.source,
            LogEntry.message,
            # The newest sighting of each distinct message. A reset
            # signature recurs, and only its latest sighting can be
            # newer than a start instant that is itself moving forward.
            func.max(LogEntry.logged_at),
        )
        .where(LogEntry.source.in_(declared_reset_sources()))
        .where(LogEntry.logged_at >= started_at)
        .group_by(LogEntry.source, LogEntry.message)
    )


async def reset_since(
    session: AsyncSession, started_at: datetime
) -> ResetSighting | None:
    """The newest declared card reset since ``started_at``, or ``None``.

    The adapter half of this module: the only thing here that touches a
    database.  It returns one row per distinct message rather than one
    per log row, which is what makes signing them in Python affordable —
    49,527 rows against 173 distinct messages, measured 2026-09-08.

    The floor is ``>=`` and :func:`newest_declared_reset` applies the
    strict comparison, so this statement is honestly a pre-filter and the
    tie rule has one owner.
    """
    rows = (await session.execute(candidate_statement(started_at))).all()
    return newest_declared_reset(
        ((source, message, at) for source, message, at in rows),
        after=started_at,
    )


def unreadable_reading(unit: str, why: str) -> dict:
    """The reading for a declared service whose start instant is unknown.

    Rule 5.  The term did not run; the status the caller already reached
    stands, and this says which way it was not known rather than leaving
    the absence to be read as health.
    """
    return {DETAIL_KEY: {"unit": unit, "evaluated": False, "reason": why}}


def verdict_reading(
    unit: str,
    started_at: datetime,
    sighting: ResetSighting | None,
) -> dict:
    """The reading for a declared service whose start instant was read.

    The whole derivation lands in the row — both instants and the
    signature that declared the reset — so a reader can see why the
    verdict is what it is without going back to the journal.
    ``monitor/collation.py`` rule 4's posture: what a reader needs to act
    is carried in the row rather than left to be looked up.
    """
    reading: dict = {
        "unit": unit,
        "evaluated": True,
        "unit_started_at": _iso(started_at),
        "context_lost": sighting is not None,
    }
    if sighting is not None:
        reading["reset_at"] = _iso(sighting.at)
        reading["reset_signature"] = sighting.signature
    return {DETAIL_KEY: reading}


def _iso(moment: datetime) -> str:
    """``moment`` as an ISO-8601 string in UTC.

    UTC rather than the reader's local clock, agreeing with
    ``GET /api/logs/trends`` and with ``journal_command``'s ``@<epoch>``:
    ``SNAG-LOG-009`` rule 4, where the prose beside an instant is
    labelled rather than converted.
    """
    return moment.astimezone(UTC).isoformat()
