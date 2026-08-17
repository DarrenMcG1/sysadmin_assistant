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
