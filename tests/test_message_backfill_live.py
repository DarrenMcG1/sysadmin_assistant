"""The backfill driven against real rows in a rolled-back transaction.

``SNAG-LOG-008``'s check retires with the entry — every member of
``snag_claims.CHECKS`` names an *open* one — and **the detector does
not**.  Its half 1 is here, re-homed: ``FROZEN_TABLES``' rule, and the
precedent Sessions 112 and 115 both set.  Deleting a guard along with its
last finding takes the guard against the defect coming back, at the
moment nothing else is exercising it.

Two things are driven, and they are the two halves of the entry's
mechanism:

1. **The shape is decided at read time.**  This daemon's own journal is
   read twice in one process, minutes apart, at the two declarations
   that bracket the Session 64 deploy.  The same records come back
   shaped differently, which is why a stored row's ``message`` was
   settled by what ``services.yaml`` said when it was ingested and no
   later read revisits it.
2. **Something re-derives a stored row's message now**, which is the
   half the entry said nothing could.  Five probe rows cover every
   branch the repair can take, against the real ``log_entries`` table.

The rows are real and the transaction is rolled back.  ``plan_backfill``
scans the whole declared source, so every assertion here is a **delta**
against a baseline measured in the same transaction — an absolute count
would pass or fail on whether the live population had been repaired yet,
which is a fact about the box and not about the code.

The one branch with no production population is ``unrecoverable``: it
needs a ``message`` cut at its stored cap beside a ``raw_line`` that
still parses, and ``raw_line``'s cap is 2000 against the message's 5000,
so the record is lost first.  It is driven synthetically and said to be
synthetic rather than left unexercised, because it decides an exit
status.
"""

import asyncio
import json

import pytest

from sysadmin.core.config import get_config
from sysadmin.monitor import message_backfill
from sysadmin.monitor.journal import read_journal
from sysadmin.monitor.message_backfill import (
    apply_backfill,
    json_declared_sources,
    plan_backfill,
)
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import load_services_singleton

#: The unit whose journal half 1 reads.  This daemon's own, because it is
#: the only source on this box that declares a format at all — the fact
#: ``unwrap_json_message``'s rule 1 rests on.
PROBE_UNIT = "sysadmin.service"

INNER = "alert_raised"
ENVELOPE = json.dumps({
    "timestamp": "2026-08-17 14:12:04,508",
    "level": "WARNING",
    "logger": "sysadmin.core.agent",
    "message": INNER,
})
#: A message that is *itself* a JSON document with a ``message`` key —
#: the row rule 2's witness exists for.  Unwrapping it a second time
#: would silently destroy a correctly-stored record.
NESTED = json.dumps({"message": "a document this application really logged"})

READER_METADATA = {"pid": "999999", "hostname": "dbelter",
                   "syslog_identifier": "sysadmin-service"}


def _db_available() -> bool:
    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            "postgresql+psycopg2://gaddi@localhost:5432/projects",
            connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


def _record(message: str, **extra: str) -> str:
    """A journalctl ``-o json`` record, as ``raw_line`` stores one."""
    return json.dumps({
        "__CURSOR": "s=probe;i=1",
        "__REALTIME_TIMESTAMP": "1787418616000000",
        "PRIORITY": "4",
        "_PID": "999999",
        "_HOSTNAME": "dbelter",
        "SYSLOG_IDENTIFIER": "sysadmin-service",
        "MESSAGE": message,
        **extra,
    })


async def _rolled_back():
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import NullPool

    config = get_config()
    engine = create_async_engine(
        config.database.url,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"search_path": f"{config.database.schema_},public"}
        },
    )
    try:
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
                    yield session
                finally:
                    await session.rollback()
                    await outer.rollback()
    finally:
        await engine.dispose()


def _probe_rows() -> dict[str, LogEntry]:
    """One row per branch the repair can take.

    Keyed by what each is *for*, so a failure names the rule it broke
    rather than an index.
    """
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    common = {"source": PROBE_UNIT, "severity": "warning", "logged_at": now}
    return {
        # Read under `text` before the declaration: the whole envelope is
        # in `message`, and the record's MESSAGE is byte-identical.
        "frozen": LogEntry(
            **common, message=ENVELOPE, raw_line=_record(ENVELOPE),
            metadata_=dict(READER_METADATA),
        ),
        # The same row with a `raw_line` nothing can parse — refused.
        "unwitnessed": LogEntry(
            **common, message=ENVELOPE, raw_line=_record(ENVELOPE)[:120],
            metadata_=dict(READER_METADATA),
        ),
        # Read under `json` and correct: `message` is the fragment, and
        # the fragment happens to be a document.  Unwrapping again loses
        # a real record.
        "already_unwrapped": LogEntry(
            **common, message=NESTED,
            raw_line=_record(json.dumps({"logger": "app", "message": NESTED})),
            metadata_={**READER_METADATA, "logger": "app"},
        ),
        # An ordinary line, which the declaration correctly left alone.
        "plain": LogEntry(
            **common, message="Started SysAdmin Assistant.",
            raw_line=_record("Started SysAdmin Assistant."),
            metadata_=dict(READER_METADATA),
        ),
        # Planned, then changed underneath the plan before the write.
        "moved": LogEntry(
            **common, message=ENVELOPE, raw_line=_record(ENVELOPE),
            metadata_=dict(READER_METADATA),
        ),
        # Witnessed as never unwrapped, but the envelope will not parse.
        # Synthetic: raw_line's cap is lower than the message's, so a
        # real record is lost from raw_line first.
        "unrecoverable": LogEntry(
            **common, message='{"timestamp": "2026-08-17", "message": "cut here',
            raw_line=_record('{"timestamp": "2026-08-17", "message": "cut here'),
            metadata_=dict(READER_METADATA),
        ),
    }


async def _drive() -> dict:
    load_services_singleton()
    declared = json_declared_sources(get_config().agents.log_aggregator)

    async for session in _rolled_back():
        baseline = await plan_backfill(session)

        rows = _probe_rows()
        for row in rows.values():
            session.add(row)
        await session.flush()
        ids = {name: row.id for name, row in rows.items()}

        plan = await plan_backfill(session)

        # The plan named this row; something else rewrites it before the
        # write lands.  `apply_backfill` must not put a stale `before`'s
        # derivation on top of it.
        rows["moved"].message = "rewritten by somebody else"
        await session.flush()

        applied = await apply_backfill(session, plan)
        await session.flush()

        # Re-read through the database rather than off the ORM objects in
        # hand: an in-place mutation of a JSONB column looks correct in
        # the identity map and writes nothing, which is the whole of
        # SNAG-AGENT-005's rule 3.
        session.expire_all()
        after = {
            name: await session.get(LogEntry, row_id) for name, row_id in ids.items()
        }
        second = await plan_backfill(session)

        return {
            "declared": declared,
            # may-not-turn: the baseline is read before the probe rows are added, so nothing is
            # frozen yet — planned_frozen below is the non-empty end of the same pair
            "baseline_frozen": {row.entry_id for row in baseline.frozen},
            "planned_frozen": {row.entry_id for row in plan.frozen},
            "planned_unwitnessed": set(plan.unwitnessed),
            "planned_unrecoverable": set(plan.unrecoverable),
            "applied": applied.applied,
            "ids": ids,
            "message": {name: row.message for name, row in after.items()},
            "metadata": {name: dict(row.metadata_) for name, row in after.items()},
            "raw_line": {name: row.raw_line for name, row in after.items()},
            # may-not-turn: the repair is idempotent, so nothing is frozen once it has run — an
            # empty second plan is the assertion, and planned_frozen above is the non-empty end of
            # the same pair
            "second_frozen": {row.entry_id for row in second.frozen},
            "second_blind": second.blind,
        }
    raise AssertionError("the rolled-back session never yielded")


async def _read_at_both_declarations() -> tuple[int, int, int]:
    """Half 1 — the same records, read twice, shaped by the declaration.

    Returns ``(shared, enveloped, divergent)``.  The reads are seconds
    apart in the same process and against the same journal, so the only
    thing that differs between them is what the caller declared.

    **Paired on the record's own timestamp, never on ``raw_line``.**  The
    entry records that ``journalctl -o json`` emits a record's fields in
    no fixed order, so the same record read twice yields two
    byte-different lines that parse to the identical dict — measured
    there at 0 of 50 paired, and it broke the retired check's first
    draft and this file's.  ``__REALTIME_TIMESTAMP`` is journald's, is
    already resolved into ``logged_at``, and is stable across reads.
    """
    reads = {}
    for declaration in ("text", "json"):
        read = await read_journal(
            unit=PROBE_UNIT,
            since="1 day ago",
            severity_filter="info",
            user=False,
            limit=50,
            log_format=declaration,
        )
        reads[declaration] = {
            entry["logged_at"]: entry["message"] for entry in read.entries
        }

    shared = set(reads["text"]) & set(reads["json"])
    enveloped = [at for at in shared if reads["text"][at].startswith("{")]
    divergent = [at for at in enveloped if reads["text"][at] != reads["json"][at]]
    return len(shared), len(enveloped), len(divergent)


@pytest.fixture(scope="module")
def reading():
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    return asyncio.run(_drive())


@pytest.fixture(scope="module")
def journal_reading():
    return asyncio.run(_read_at_both_declarations())


class TestTheShapeIsDecidedAtReadTime:
    """Half 1 of the mechanism — the entry's cause, reproduced."""

    def test_the_two_reads_saw_the_same_records(self, journal_reading):
        """The witness.  Without a shared population the assertion below
        is true of the empty set and says nothing about the reader."""
        shared, enveloped, _ = journal_reading
        assert shared > 0, "the two reads share no record — nothing was compared"
        assert enveloped > 0, (
            "this daemon wrote no JSON-enveloped record in the last day, so the "
            "declaration had nothing to shape"
        )

    def test_the_declaration_alone_shapes_a_record(self, journal_reading):
        _, enveloped, divergent = journal_reading
        assert divergent == enveloped, (
            "every enveloped record must be shaped differently under the two "
            "declarations — a reader that no longer honours the declaration "
            "means a stored row's message was not settled by what services.yaml "
            "said when it was ingested, and this entry's cause is gone"
        )


@pytest.mark.premise
class TestThePremises:
    """A constant observation is not evidence unless something could move it."""

    def test_this_box_declares_the_format_for_the_probe_unit(self, reading):
        """The premise is membership, and it used to be stated as equality.

        Until 2026-08-31 this read ``== (PROBE_UNIT,)``, which asserted
        the anti-vacuity premise *and*, incidentally, that this daemon is
        the only source on this box declaring a format.  The estate's
        entry points began emitting JSON that day (message ``76e0438b``)
        and ``services.yaml`` gained a second declaration, so the second
        half died and took a premise with it that never depended on it.

        Membership is the whole premise: the probe rows are stamped with
        this unit, so if *this* unit is undeclared the scan cannot see
        them and every assertion below passes vacuously.  What the rest
        of the estate declares is not this file's business — and is
        pinned where it belongs, by
        ``test_only_measured_sources_declare_a_format``.

        The widened population was driven before this was relaxed rather
        than argued about: ``plan_backfill`` goes from 256 rows scanned
        to 284, and the 28 added rows are systemd's own plain-text lines
        in the estate's journal, which ``unwrap_json_message`` fails open
        on, so they produce no frozen row, no unwitnessed row and no
        unrecoverable one.
        """
        assert PROBE_UNIT in reading["declared"], (
            "the probe rows are stamped with this unit; if nothing declares it "
            "the scan is empty and every assertion below passes vacuously"
        )

    def test_the_probe_rows_are_not_the_live_population(self, reading):
        assert not (set(reading["ids"].values()) & reading["baseline_frozen"])


class TestTheRepairAgainstRealRows:
    def test_the_frozen_row_is_rewritten_to_what_the_reader_would_have_stored(
        self, reading
    ):
        assert reading["ids"]["frozen"] in reading["planned_frozen"]
        assert reading["message"]["frozen"] == INNER
        assert reading["applied"] is True

    def test_the_envelope_reaches_metadata_and_the_reader_s_fields_survive(
        self, reading
    ):
        """Merged and reassigned.

        Re-read from the database, so an in-place mutation that SQLAlchemy
        never flushed fails here — the failure a fake cannot produce.
        """
        after = reading["metadata"]["frozen"]
        assert after["logger"] == "sysadmin.core.agent"
        assert after["pid"] == "999999"
        assert after["hostname"] == "dbelter"
        assert after["syslog_identifier"] == "sysadmin-service"

    def test_raw_line_is_left_exactly_as_the_journal_wrote_it(self, reading):
        assert reading["raw_line"]["frozen"] == _record(ENVELOPE)

    def test_a_correctly_unwrapped_document_is_not_unwrapped_again(self, reading):
        """The witness earning its place.

        Without it this row's message becomes ``"a document this
        application really logged"`` and the record it was is gone —
        a repair that corrupts what it was not asked to touch.
        """
        assert reading["ids"]["already_unwrapped"] not in reading["planned_frozen"]
        assert reading["message"]["already_unwrapped"] == NESTED
        assert reading["ids"]["already_unwrapped"] not in reading[
            "planned_unwitnessed"
        ]

    def test_a_row_nothing_can_witness_is_refused_and_reported(self, reading):
        assert reading["ids"]["unwitnessed"] in reading["planned_unwitnessed"]
        assert reading["ids"]["unwitnessed"] not in reading["planned_frozen"]
        assert reading["message"]["unwitnessed"] == ENVELOPE

    def test_a_row_whose_envelope_will_not_parse_is_reported_as_unrecoverable(
        self, reading
    ):
        assert reading["ids"]["unrecoverable"] in reading["planned_unrecoverable"]
        assert reading["ids"]["unrecoverable"] not in reading["planned_frozen"]

    def test_an_ordinary_line_is_untouched_and_uncounted(self, reading):
        assert reading["message"]["plain"] == "Started SysAdmin Assistant."
        assert reading["ids"]["plain"] not in reading["planned_frozen"]
        assert reading["ids"]["plain"] not in reading["planned_unwitnessed"]
        assert reading["ids"]["plain"] not in reading["planned_unrecoverable"]

    def test_a_row_that_moved_under_the_plan_is_left_alone(self, reading):
        """The plan is a snapshot, and a write from a snapshot has to
        re-check.  Rewriting from a stale ``before`` would silently undo
        whatever changed the row in between."""
        assert reading["ids"]["moved"] in reading["planned_frozen"]
        assert reading["message"]["moved"] == "rewritten by somebody else"

    def test_a_second_pass_finds_nothing_it_repaired(self, reading):
        """Idempotence is a property of the witness, not a flag.

        A repaired row's ``message`` no longer equals the record's
        ``MESSAGE``, so the witness answers ``False`` and rule 2 leaves
        it alone — with nothing recording that it was ever repaired.
        """
        repaired = {name: rid for name, rid in reading["ids"].items()
                    if name != "moved"}
        assert not (set(repaired.values()) & reading["second_frozen"])

    def test_the_two_refusals_survive_a_second_pass(self, reading):
        """They are not repaired by being seen twice, so they stay
        reported — a run that hid them the second time would let a
        caller read a blind scan as a clean one."""
        assert reading["second_blind"] is True


class TestTheDryRunReallyWritesNothing:
    """The worst failure this tool can have, driven rather than inferred.

    ``tests/test_message_backfill.py`` pins where the gate is and that
    ``main`` passes the flag through; neither exercises :func:`run`
    itself, which is the function that owns the session and the commit.
    So the factory is supplied — the one leaf — and everything above it
    is the module's own.  The session joins the outer transaction by
    savepoint, so the commit :func:`run` would issue releases a savepoint
    and the rollback still owns the drive: a write really would land in
    the table if the gate were gone.
    """

    def test_run_without_confirm_leaves_a_frozen_row_frozen(self, monkeypatch):
        if not _db_available():
            pytest.skip("local postgres (projects DB) not reachable")

        async def drive() -> tuple[int, str]:
            from contextlib import asynccontextmanager

            async for session in _rolled_back():
                row = _probe_rows()["frozen"]
                session.add(row)
                await session.flush()
                # Captured before the expire below: an expired attribute
                # is reloaded lazily, which is an IO the greenlet the
                # assertion runs in cannot perform.
                row_id = row.id

                @asynccontextmanager
                async def supplied():
                    yield session

                monkeypatch.setattr(
                    message_backfill, "get_scheduler_session", supplied
                )
                report = await message_backfill.run(confirm=False)
                session.expire_all()
                stored = await session.get(LogEntry, row_id)
                return len(report.frozen), stored.message
            raise AssertionError("unreachable")

        found, stored = asyncio.run(drive())
        assert found >= 1, "the probe row was not even planned"
        assert stored == ENVELOPE, "a dry run wrote to the table"


class TestNothingSurvivesTheRollback:
    def test_no_probe_row_reached_the_table(self, reading):
        async def check() -> int:
            from sqlalchemy import func, select

            async for session in _rolled_back():
                return (
                    await session.execute(
                        select(func.count())
                        .select_from(LogEntry)
                        .where(LogEntry.id.in_(list(reading["ids"].values())))
                    )
                ).scalar_one()
            raise AssertionError("unreachable")

        assert asyncio.run(check()) == 0
