"""Direct tests for :mod:`sysadmin.monitor.journal`.

**The first ones it has had.** Every existing test patches ``read_journal``
out (``test_log_alert_dedup.py``) or asserts a *different* journalctl
invocation (``test_log_actions.py``'s ``journal_command``, which builds the
command a recommendation tells a human to run). The command this module
actually executes was unasserted, which is how ``-n 500`` came to bound
raw lines while the severity filter ran in Python over what was left.
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.journal import (
    PRIORITY_MAP,
    SEVERITY_ORDER,
    max_priority_for,
    message_text,
    read_journal,
)


class TestMaxPriorityFor:
    """The ``-p`` ceiling is derived from ``PRIORITY_MAP``, not restated."""

    @pytest.mark.parametrize(
        ("severity_filter", "expected"),
        [
            ("critical", 2),
            ("error", 3),
            ("warning", 4),
            ("info", 6),
            ("debug", 7),
        ],
    )
    def test_ceiling_per_severity(self, severity_filter: str, expected: int) -> None:
        assert max_priority_for(severity_filter) == expected

    def test_agrees_with_priority_map_for_every_code(self) -> None:
        """The round trip, which is the point of deriving it.

        For every severity, the codes journalctl would admit under the
        derived ceiling must be exactly the codes ``PRIORITY_MAP`` maps to
        that severity or louder. Asserting the two sides separately is what
        lets them drift; this asserts they are one fact.
        """
        for severity, floor in SEVERITY_ORDER.items():
            ceiling = max_priority_for(severity)
            admitted = {int(c) for c in PRIORITY_MAP if int(c) <= ceiling}
            expected = {
                int(code)
                for code, name in PRIORITY_MAP.items()
                if SEVERITY_ORDER.get(name, 0) >= floor
            }
            assert admitted == expected, severity

    def test_unknown_filter_admits_everything(self) -> None:
        """Matching the Python filter's own ``.get(..., 0)`` fallback.

        Failing differently on the two sides would mean a typo in
        ``services.yaml`` silently narrows the read while the filter below
        stays wide — a source going quiet for a reason nothing reports.
        """
        assert max_priority_for("nonsense") == max(int(c) for c in PRIORITY_MAP)


def _entry(priority: str, message: str, cursor: str) -> str:
    return json.dumps(
        {
            "PRIORITY": priority,
            "MESSAGE": message,
            "__CURSOR": cursor,
            "__REALTIME_TIMESTAMP": "1755000000000000",
        }
    )


class TestPriorityIsPassedToJournalctl:
    """``-p`` bounds the ceiling; without it 61 % of the budget was waste."""

    @pytest.mark.asyncio
    async def test_kernel_error_filter_passes_p_err(self) -> None:
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error")

        cmd = run.call_args[0][0]
        assert "-p" in cmd
        assert cmd[cmd.index("-p") + 1] == "3"
        assert "-k" in cmd and "-u" not in cmd

    @pytest.mark.asyncio
    async def test_user_unit_warning_filter_passes_p_warning(self) -> None:
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal(
                "alfred-backend.service", severity_filter="warning", user=True
            )

        cmd = run.call_args[0][0]
        assert cmd[cmd.index("-p") + 1] == "4"
        assert "--user" in cmd

    @pytest.mark.asyncio
    async def test_ceiling_and_priority_travel_together(self) -> None:
        """``-n`` and ``-p`` are one mechanism, so both must be present.

        ``-n`` alone is the defect this fixes; ``-p`` alone would read an
        unbounded storm into memory. A command carrying one and not the
        other is worse than the version before either.
        """
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error", limit=250)

        cmd = run.call_args[0][0]
        assert cmd[cmd.index("-n") + 1] == "250"
        assert cmd[cmd.index("-p") + 1] == "3"


class TestPythonFilterRemainsTheAuthority:
    """``-p`` is an optimisation on the ceiling, not the decision."""

    @pytest.mark.asyncio
    async def test_entry_below_the_filter_is_still_dropped(self) -> None:
        """Belt and braces, and deliberately not removed.

        A stub returning what ``-p`` would have excluded stands in for
        journalctl behaving differently from this module's reading of it.
        The entry must not be stored.
        """
        stdout = "\n".join(
            [
                _entry("3", "a real error", "c1"),
                _entry("6", "chatter that -p should have excluded", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error")

        assert [e["message"] for e in read.entries] == ["a real error"]

    @pytest.mark.asyncio
    async def test_cursor_still_advances_over_every_entry_read(self) -> None:
        """The rule survives ``-p``, which is why the comment stayed.

        ``-p`` means the discarded entry is not normally returned at all,
        so the two sets coincide in production. The rule is about what was
        *read*, so it is asserted against a read that contains both.
        """
        stdout = "\n".join(
            [
                _entry("3", "a real error", "c1"),
                _entry("6", "chatter", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error")

        assert read.cursor == "c2"


class TestTruncationNowCountsRelevantEntries:
    @pytest.mark.asyncio
    async def test_truncated_when_the_read_fills_the_limit(self) -> None:
        stdout = "\n".join(_entry("3", f"e{i}", f"c{i}") for i in range(5))
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error", limit=5)

        assert read.truncated is True

    @pytest.mark.asyncio
    async def test_not_truncated_below_the_limit(self) -> None:
        stdout = "\n".join(_entry("3", f"e{i}", f"c{i}") for i in range(4))
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("kernel", severity_filter="error", limit=5)

        assert read.truncated is False


class TestLongFieldsAreReadInFull:
    """``-a``, and why its absence was a crash rather than a lost detail.

    ``journalctl -o json`` substitutes ``null`` for any field over ~4096
    bytes unless ``-a`` is passed.  ``MESSAGE`` therefore arrived as
    ``None`` for every record this daemon writes with a traceback in it,
    and the aggregator's ``entry["message"][:5000]`` raised ``TypeError``
    (``SNAG-LOG-004``).
    """

    @pytest.mark.parametrize(
        ("unit", "user"),
        [("kernel", False), ("sysadmin.service", False), ("alfred.service", True)],
    )
    @pytest.mark.asyncio
    async def test_all_is_passed_for_every_source_shape(
        self, unit: str, user: bool
    ) -> None:
        """Every branch of the command builder, because ``-a`` is inserted
        before the ``-k``/``-u``/``--user`` edits and an index slip would
        drop it from exactly one of them."""
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal(unit, severity_filter="warning", user=user)

        assert "-a" in run.call_args[0][0]

    @pytest.mark.asyncio
    async def test_all_travels_with_the_ceiling_and_the_priority(self) -> None:
        """The three flags are one mechanism and must not drift apart.

        ``-n`` bounds the read, ``-p`` makes the bound count entries that
        matter, and ``-a`` makes the entries themselves readable.  A
        command carrying two of the three has been shipped twice now.
        """
        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value="")
        ) as run:
            await read_journal("kernel", severity_filter="error", limit=250)

        cmd = run.call_args[0][0]
        assert "-a" in cmd
        assert cmd[cmd.index("-n") + 1] == "250"
        assert cmd[cmd.index("-p") + 1] == "3"


class TestMessageText:
    """The guard behind ``-a``, for the shapes journalctl may still return."""

    def test_a_string_is_itself(self) -> None:
        assert message_text("kernel: it broke") == "kernel: it broke"

    def test_a_byte_array_is_decoded(self) -> None:
        """``-a`` renders a non-UTF-8 field as an array of byte values.

        The one new shape ``-a`` introduces — without it the same field is
        ``null``, so this branch could not previously be reached.
        """
        assert message_text([104, 105]) == "hi"

    def test_invalid_utf8_bytes_are_replaced_not_raised(self) -> None:
        assert message_text([0xFF, 105]) == "�i"

    def test_a_nonsense_array_is_empty_rather_than_fatal(self) -> None:
        assert message_text([1, "two", None]) == ""

    @pytest.mark.parametrize("value", [None, 42, {"a": 1}])
    def test_anything_else_is_empty_string(self, value: object) -> None:
        """``""`` and never ``None``: a caller slicing the result is the
        whole defect, so the fallback must be sliceable."""
        assert message_text(value) == ""


class TestATruncatedFieldNoLongerPoisonsTheRun:
    """The end-to-end shape of ``SNAG-LOG-004``, asserted at this module's
    boundary — the aggregator slices what comes out of here."""

    @pytest.mark.asyncio
    async def test_null_message_yields_a_sliceable_entry(self) -> None:
        """Stands in for journalctl truncating despite ``-a``.

        ``-a`` is the fix, and this is the belt to its braces: the
        ``-p``/Python-filter pairing is written the same way and for the
        same reason.  A record journald declines to return in full must
        cost that record's text and nothing else.
        """
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "PRIORITY": "3",
                        "MESSAGE": None,
                        "__CURSOR": "c1",
                        "__REALTIME_TIMESTAMP": "1755000000000000",
                    }
                ),
                _entry("3", "a readable error", "c2"),
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("sysadmin.service", severity_filter="error")

        assert len(read.entries) == 2
        # What the aggregator does next, verbatim — this raised TypeError.
        assert [e["message"][:5000] for e in read.entries] == ["", "a readable error"]
        assert read.cursor == "c2"

    @pytest.mark.asyncio
    async def test_every_entry_carries_a_string_message(self) -> None:
        """The invariant, rather than the instance.

        Whatever shapes journald returns, nothing leaves this module with
        a ``message`` a caller cannot slice.
        """
        stdout = "\n".join(
            [
                json.dumps(
                    {"PRIORITY": "3", "MESSAGE": m, "__CURSOR": f"c{i}",
                     "__REALTIME_TIMESTAMP": "1755000000000000"}
                )
                for i, m in enumerate([None, [104, 105], "plain", 7])
            ]
        )
        with patch("sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)):
            read = await read_journal("sysadmin.service", severity_filter="error")

        assert [type(e["message"]) for e in read.entries] == [str] * 4
