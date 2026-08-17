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
