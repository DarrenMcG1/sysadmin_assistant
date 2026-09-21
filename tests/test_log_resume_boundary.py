"""SNAG-LOG-007 — the resume floor re-read its own boundary on every restart.

``self._cursors`` is exact and covers the poll-to-poll case.  It lives in
memory, so a restart falls back to :meth:`_resume_floor`, and that fallback
had an off-by-one nobody had asserted:

* ``journalctl --since`` is **inclusive**, so a window opened at the newest
  stored entry re-admits that entry; and
* :func:`~sysadmin.monitor.journal.since_timestamp` renders ``@<int>``, which
  truncates sub-second precision — so it re-admits every entry sharing that
  entry's whole second too.

Measured on the live table on 2026-08-17, before the fix: **339 duplicate
groups covering 497 surplus rows**, the worst a single journal entry stored
**19 times**.  Every duplicated entry was the newest stored one for its
source — ``sportsanalyser-frontend`` 12:34:26, ``estate-broker-provision``
12:32:51, ``alfred-backend`` 12:33:08, ``kernel`` 19:11:24 — which is the
boundary the off-by-one predicts and not a pattern any other cause explains.

**The row count was never the cost.**  ``_resolve_quiet`` closes a row that
has been unobserved for ``alert_quiet_minutes``, so by the next restart the
previous copy is resolved and the re-read entry raises a *fresh* alert.  A
mosquitto coredump from 2026-08-12 12:32:51 was raised three separate times
— 12:34:15, 14:12:00 and 19:50:20 — each at ``critical``, which is the one
severity ``sysadmin_tray/notifications.py`` leaves on screen.  Every restart
of this daemon announced a five-day-old fault that had already been fixed.

**Why the window is still opened wide.**  The obvious fix — open at
``floor + 1s`` — trades a duplicate for a **gap**, and this module chose the
cursor over a narrower window precisely because a gap is the worse failure
for a monitor.  So the read stays inclusive and the boundary is settled
against the stored rows instead, which is exact in both directions.

**Why the message is compared and not only the timestamp.**  Two entries can
share a microsecond; the Bluetooth pair on this box sits 29 µs apart, which
is close enough to make the assumption unsafe rather than merely untidy.
Comparing the message keeps a genuine second entry at the same instant.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.config import LogSource
from sysadmin.monitor.journal import JournalRead
from sysadmin.monitor.log_aggregator import (
    STORED_MESSAGE_CHARS,
    LogAggregatorAgent,
)

FLOOR = datetime(2026, 8, 12, 12, 32, 51, 283926, tzinfo=UTC)


def _entry(logged_at: datetime, message: str) -> dict:
    return {
        "source": "mosquitto.service",
        "severity": "critical",
        "message": message,
        "raw_line": message,
        "metadata": {},
        "logged_at": logged_at,
    }


class TestIsUnstored:
    """The boundary decision itself, which is pure."""

    def test_strictly_newer_is_kept(self):
        entry = _entry(FLOOR + timedelta(microseconds=1), "anything")
        assert LogAggregatorAgent._is_unstored(entry, FLOOR, {"anything"}) is True

    def test_entry_at_the_floor_already_stored_is_dropped(self):
        """The defect itself: this is the row that came back 19 times."""
        entry = _entry(FLOOR, "Process 1705 (mosquitto) dumped core.")
        stored = {"Process 1705 (mosquitto) dumped core."}
        assert LogAggregatorAgent._is_unstored(entry, FLOOR, stored) is False

    def test_second_entry_at_the_same_instant_is_kept(self):
        """No gap: sharing a microsecond is not being the same entry."""
        entry = _entry(FLOOR, "a different line at the same instant")
        stored = {"Process 1705 (mosquitto) dumped core."}
        assert LogAggregatorAgent._is_unstored(entry, FLOOR, stored) is True

    def test_older_than_the_floor_is_dropped(self):
        entry = _entry(FLOOR - timedelta(seconds=1), "older than the floor")
        assert LogAggregatorAgent._is_unstored(entry, FLOOR, set()) is False

    def test_long_message_compares_on_the_stored_form(self):
        """The trap :data:`STORED_MESSAGE_CHARS` exists to close.

        The row holds a truncated message.  Comparing the untruncated line
        against it would make every long message unequal to itself and
        re-ingest on every restart — this defect wearing a longer name.
        """
        long_message = "x" * (STORED_MESSAGE_CHARS + 500)
        entry = _entry(FLOOR, long_message)
        stored = {long_message[:STORED_MESSAGE_CHARS]}
        assert LogAggregatorAgent._is_unstored(entry, FLOOR, stored) is False


class TestReadJournalSource:
    """The boundary applied to a real read, with the read's own facts kept."""

    @staticmethod
    def _source() -> LogSource:
        # The real model, never a SimpleNamespace: a stand-in silently
        # grows whatever attribute the code asks for, which is how twelve
        # tests missed ``source.format`` in Session 64.
        return LogSource(
            name="mosquitto",
            type="journalctl",
            unit="mosquitto.service",
            severity_filter="warning",
        )

    @pytest.mark.asyncio
    async def test_boundary_entry_is_filtered_and_read_facts_survive(
        self, monkeypatch
    ):
        boundary = _entry(FLOOR, "already stored")
        fresh = _entry(FLOOR + timedelta(seconds=2), "new line")

        agent = LogAggregatorAgent()

        async def fake_floor(session, unit):
            return FLOOR, {"already stored"}

        async def fake_read(**kwargs):
            return JournalRead(
                entries=[boundary, fresh], cursor="s=abc", truncated=True
            )

        monkeypatch.setattr(agent, "_resume_floor", fake_floor)
        monkeypatch.setattr(
            "sysadmin.monitor.log_aggregator.read_journal", fake_read
        )

        read = await agent._read_journal_source(None, self._source(), 500)

        assert [e["message"] for e in read.entries] == ["new line"]
        # cursor and truncated describe the *read*, not what was kept —
        # the same rule that takes the cursor before the severity filter.
        assert read.cursor == "s=abc"
        assert read.truncated is True
        assert agent._cursors["mosquitto"] == "s=abc"

    @pytest.mark.asyncio
    async def test_first_ever_read_filters_nothing(self, monkeypatch):
        """No floor means no stored rows, so there is no boundary to close."""
        entries = [_entry(FLOOR, "a"), _entry(FLOOR, "b")]
        agent = LogAggregatorAgent()

        async def fake_floor(session, unit):
            return None, set()

        async def fake_read(**kwargs):
            return JournalRead(entries=entries, cursor="s=1")

        monkeypatch.setattr(agent, "_resume_floor", fake_floor)
        monkeypatch.setattr(
            "sysadmin.monitor.log_aggregator.read_journal", fake_read
        )

        read = await agent._read_journal_source(None, self._source(), 500)
        assert len(read.entries) == 2

    @pytest.mark.asyncio
    async def test_cursor_path_never_consults_the_floor(self, monkeypatch):
        """Poll-to-poll is the cursor's, and it is exact already.

        Filtering there would spend a query per source per poll to answer a
        question ``--after-cursor`` has already answered.
        """
        agent = LogAggregatorAgent()
        agent._cursors["mosquitto"] = "s=previous"
        called = False

        async def fake_floor(session, unit):
            nonlocal called
            called = True
            return FLOOR, set()

        async def fake_read(**kwargs):
            return JournalRead(entries=[_entry(FLOOR, "x")], cursor="s=2")

        monkeypatch.setattr(agent, "_resume_floor", fake_floor)
        monkeypatch.setattr(
            "sysadmin.monitor.log_aggregator.read_journal", fake_read
        )

        read = await agent._read_journal_source(None, self._source(), 500)
        assert called is False
        assert len(read.entries) == 1


# ── SNAG-LOG-014's detector, re-homed ─────────────────────────────────
#
# ``check_duplicate_ingest_residue`` retired with the entry on 2026-09-21
# — every member of ``snag_claims.CHECKS`` names an *open* one — and
# **the detector did not**.  ``FROZEN_TABLES``' rule: deleting a guard
# along with its last finding takes the guard against the defect coming
# back, at the moment nothing else is exercising it.  It belongs in this
# file rather than in one of its own, because the residue it counted was
# this file's own mechanism: two records at 14:21:03 on 2026-08-17 were
# re-admitted by a ``_resume_floor`` whose close landed nineteen minutes
# after the restart that needed it.
#
# **The key changed on the way across, and it is not either of the two
# the entry argued between.**  That entry weighed
# ``(source, logged_at, message)`` against ``(source, logged_at)`` and
# took the narrow one, on the ground that a wide key admits two genuinely
# distinct records landing in one microsecond.  Both are wrong for a
# *guard*:
#
# * the **narrow** key is blind to the only form of this defect anyone
#   has recorded.  Before ``SNAG-LOG-008``'s backfill the two copies held
#   different ``message`` values — one envelope, one fragment — because
#   the second arrived under a declaration the first predated, and they
#   hid each other for eleven days.  A recurrence needs a restart, and a
#   restart is when a declaration changes, so that is the likely form.
# * the **wide** key has a live false positive.  The entry's supporting
#   figure — *zero groups share a* ``(source, logged_at)`` *while
#   disagreeing about* ``message`` — was true when taken on 2026-09-04
#   and was refuted three days later: ``sysadmin.service`` wrote
#   ``llm_unavailable`` and ``health_review_llm_unavailable_used_fallback``
#   at ``__REALTIME_TIMESTAMP`` **1788753610332654**, the same
#   microsecond, during the 2026-09-07 health review.  Two records, one
#   instant, a gap of **0 µs**.
#
# ``raw_line`` settles it exactly, and it is ``SNAG-LOG-008``'s own rule
# applied one entry over: that backfill chose byte equality against the
# record's ``MESSAGE`` as its witness precisely because "does this look
# like JSON" cannot separate a frozen envelope from a correct unwrap.
# The same column separates a record stored twice from two records at one
# instant — same raw line means one journal record, different raw lines
# mean two — and it is the column no repair here rewrites.
#
# Three measurements behind the choice, taken 2026-09-21 over 771,192
# retained rows and 11 sources:
#
# * the key's margin is **3 µs**, at ``kernel`` — the tightest gap
#   between two *identical* stored lines from one source, and the figure
#   the entry quoted while describing the wide key's margin, which is 0.
#   A kernel storm emitting one line twice inside a microsecond is what
#   turns this red for a non-defect, and that is the right response,
#   since nothing downstream could tell it from a duplicate ingest.
# * ``raw_line`` is **nullable and never null** here — 0 of 771,192 — and
#   ``GROUP BY`` folds nulls together, so the failure direction of that
#   hole is a red rather than a silence.
# * **30** rows carry a ``raw_line`` cut at its 2000-character cap, so
#   two distinct records over 2000 bytes sharing their first 2000 *and* a
#   microsecond would read as one stored twice.  Same direction again.


DUPLICATE_RECORDS_SQL = """
    SELECT source, logged_at, count(*)
    FROM sysadmin.log_entries
    GROUP BY source, logged_at, raw_line
    HAVING count(*) > 1
"""

#: The entry's wide key.  It reaches no assertion of its own — it is the
#: population the discrimination above is *about*, and it empties by
#: retention like any other, so a test requiring a member would go red on
#: a quiet box for no defect.
COINCIDENT_INSTANTS_SQL = """
    SELECT source, logged_at, count(*) AS rows,
           count(DISTINCT raw_line) AS raw_lines
    FROM sysadmin.log_entries
    GROUP BY source, logged_at
    HAVING count(*) > 1
"""

#: Never vacuous, and that is why it is read.  A run that found no
#: duplicate over an empty table is not a run that found health —
#: ``ports_checked``'s rule — so the row count is the witness and a
#: table with nothing in it skips loudly rather than passing.
RETAINED_ROWS_SQL = "SELECT count(*) FROM sysadmin.log_entries"


def one_record_stored_twice(groups: list[tuple]) -> list[tuple]:
    """Which shared instants are one record twice rather than two records.

    A group is ``(source, logged_at, rows, raw_lines)``.  One distinct
    raw line under two rows is the same journal record stored twice; two
    distinct raw lines are two records journald stamped at one
    microsecond, which this box has done — see the note above.

    Named rather than inlined so it can be driven at the answer the live
    table cannot supply.
    """
    return [group for group in groups if group[3] == 1]


def _live_rows(statement: str) -> list[tuple]:
    from sqlalchemy import create_engine, text

    engine = create_engine(
        "postgresql+psycopg2://gaddi@localhost:5432/projects",
        connect_args={"connect_timeout": 2},
    )
    try:
        with engine.connect() as conn:
            return [tuple(row) for row in conn.execute(text(statement)).all()]
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def retained() -> int:
    try:
        rows = _live_rows(RETAINED_ROWS_SQL)
    except Exception as exc:  # noqa: BLE001 — an unreachable database is a skip
        pytest.skip(f"log_entries is unreadable ({exc.__class__.__name__})")
    count = int(rows[0][0])
    if not count:
        pytest.skip("log_entries is empty — nothing to be duplicated")
    return count


class TestNoJournalRecordIsStoredTwice:
    """The end-to-end half of :class:`TestIsUnstored`, against real rows.

    Everything above this line is pure: the boundary decision driven at
    hand-written entries, and the read driven at a stubbed
    ``read_journal``.  Neither could notice that the whole ingestion path
    had begun storing a record twice, which is what happened for the
    nineteen minutes between the 2026-08-17 restart and the commit that
    closed this boundary, and which nothing observed for eleven days.
    """

    @pytest.mark.premise
    def test_the_table_the_guard_reads_is_the_live_one(self, retained: int):
        """``SNAG-TEST-007``'s convention, and why it binds a file off the glob.

        This file is not named ``*_live.py`` — it is ``SNAG-LOG-007``'s,
        and the live drive arrived when ``SNAG-LOG-014``'s detector was
        re-homed into it.  That is exactly the shape rule 2 exists for: a
        drive against the real database sitting in a file that looks like
        every unit test beside it, owing nothing by filename.

        Every assertion below is satisfied by an unreadable or empty
        table, and the fixture skips in both cases.  This states what it
        found, so a reader of a green run can see the drive had rows to
        be wrong about.
        """
        assert retained > 0, "fixture should have skipped"

    def test_no_record_appears_twice(self, retained: int):
        duplicates = _live_rows(DUPLICATE_RECORDS_SQL)
        assert not duplicates, (
            f"{len(duplicates)} journal record(s) stored more than once "
            f"across {retained} retained rows: {duplicates[:5]}"
        )

    def test_a_shared_instant_is_two_records_and_not_one_stored_twice(
        self, retained: int
    ):
        """The discrimination, asserted where it can actually be wrong.

        A group here shares a source and a journal instant.  It is a
        *coincidence* — two records journald stamped at one microsecond —
        exactly when its rows disagree about ``raw_line``, and a duplicate
        ingest when they agree.  The test above catches the second; this
        one states that the two are told apart by the raw line rather than
        by the message, which is the half the retired check got wrong: it
        announced every such group as "this entry's own pre-backfill
        shape", and on the live specimen that sentence is false.

        Empty on a quiet box, and it says so rather than passing silently.
        """
        shared = _live_rows(COINCIDENT_INSTANTS_SQL)
        if not shared:
            pytest.skip(
                f"no instant is shared by two records across {retained} rows — "
                "the discrimination has no live specimen today"
            )
        assert not one_record_stored_twice(shared), (
            "rows sharing an instant also share their raw line, which is one "
            f"record stored twice rather than two records: {shared}"
        )

    def test_the_discrimination_is_driven_at_both_answers(self):
        """The live half above can only ever witness one of the two.

        Its population is every group whose rows *agree* about
        ``raw_line``, and that population is empty on a healthy box — so
        inverting the comparison inside it leaves the suite green, which
        is a falsification passing against deliberately broken code.
        Measured rather than assumed: it did, on the first drive of this
        file.  The predicate is therefore named and driven at a
        fabricated agreeing group as well, which is the only input that
        can distinguish the rule from a comprehension that never runs
        (``SNAG-TEST-010``'s shape).

        The specimen is the entry's own: two rows at one instant from
        ``sysadmin.service``, agreeing about the journal record and
        disagreeing about the message, which is what a copy ingested
        under a later declaration looks like.
        """
        duplicate = ("sysadmin.service", "2026-08-17 14:21:03+01", 2, 1)
        coincidence = ("sysadmin.service", "2026-09-07 05:00:10.332654+01", 2, 2)
        assert one_record_stored_twice([duplicate]) == [duplicate]
        assert one_record_stored_twice([coincidence]) == []
        assert one_record_stored_twice([coincidence, duplicate]) == [duplicate]

    def test_an_empty_table_skips_rather_than_passing(self, monkeypatch):
        """The witness branch, which no live run can reach.

        ``log_entries`` is never empty on this box, so removing the skip
        above changes nothing today — measured, by removing it: the file
        stays green.  A run that found no duplicate over no rows is not a
        run that found health (``ports_checked``'s rule), and the branch
        that says so is driven here rather than left as a sentence.
        """
        monkeypatch.setattr(
            "tests.test_log_resume_boundary._live_rows", lambda statement: [(0,)]
        )
        with pytest.raises(BaseException) as raised:
            retained.__wrapped__()
        assert "empty" in str(raised.value)

    def test_the_key_is_the_raw_line_and_not_the_message(self):
        """Asserted at the statement, because today the pair agrees.

        ``message`` is mutable — ``SNAG-LOG-008``'s backfill rewrote it,
        and the two rows this entry was about were invisible for eleven
        days precisely because it had not yet.  ``raw_line`` holds the
        journalctl record verbatim and no repair here touches it.
        """
        assert "GROUP BY source, logged_at, raw_line" in DUPLICATE_RECORDS_SQL
        assert "message" not in DUPLICATE_RECORDS_SQL
