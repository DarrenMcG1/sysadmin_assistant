"""A unit failure recorded as state, not just as a toast (Session 39).

The handler runs while the application is dead, so these pin the two things
that cannot be checked at runtime by anything else: that the row is filed
in a way the CHECK constraint accepts while still carrying its true
provenance, and that the string naming the unit agrees across the three
files that use it. A mismatch there does not error — the handler writes one
title and startup resolves another, so the row is simply never closed.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.unit_failure import (
    FILED_UNDER,
    OWN_UNIT,
    SOURCE,
    _details,
    record_unit_failure,
    resolve_unit_failures,
    unit_failure_title,
)

REPO = Path(__file__).resolve().parents[1]


class TestFiledUnderAKnownAgent:
    def test_agent_is_one_the_check_constraint_admits(self):
        """`chk_alert_agent` rejects anything else, so this is not cosmetic."""
        from sysadmin.monitor.self_monitor import AGENT_NAMES

        assert FILED_UNDER in AGENT_NAMES

    def test_details_record_the_provenance_that_agent_cannot(self):
        """Why the row says "sysadmin" when the sysadmin agent was dead.

        `agent` is the ownership field the constraint makes it. Without
        these keys the row claims an agent raised it, and nothing anywhere
        says otherwise.
        """
        details = _details("sysadmin.service", "exit-code", "1", "5")
        assert details["source"] == SOURCE
        assert details["raised_by"].endswith("notify-unit-failed.sh")
        assert details["kind"] == "unit_failure"

    def test_details_carry_the_systemd_verdict(self):
        """result and restarts are the first two questions asked later."""
        details = _details("sysadmin.service", "oom-kill", "9", "5")
        assert details["systemd_result"] == "oom-kill"
        assert details["restarts"] == "5"


class TestTheUnitNameAgreesEverywhere:
    def test_constant_matches_what_the_handler_unit_passes(self):
        """Three files name this unit; a mismatch never closes the row."""
        unit = (REPO / "systemd" / "sysadmin-failed.service").read_text(encoding="utf-8")
        exec_lines = [ln for ln in unit.splitlines() if ln.startswith("ExecStart=")]
        assert exec_lines, "no ExecStart= in sysadmin-failed.service"
        assert OWN_UNIT in exec_lines[0], (
            f"unit file does not pass {OWN_UNIT!r}: {exec_lines[0]!r}"
        )

    def test_constant_matches_the_script_default(self):
        script = (REPO / "scripts" / "notify-unit-failed.sh").read_text(encoding="utf-8")
        assert f'unit="${{1:-{OWN_UNIT}}}"' in script

    def test_the_handler_calls_the_recorder(self):
        """Without this the failure leaves a toast and no state."""
        script = (REPO / "scripts" / "notify-unit-failed.sh").read_text(encoding="utf-8")
        assert "sysadmin-record-failure" in script

    def test_the_recorder_call_cannot_fail_the_handler(self):
        """The database may be why the service died.

        The handler's exit status is reserved for whether it could tell a
        human; a failed insert must not become a failed unit needing its
        own explanation.
        """
        script = (REPO / "scripts" / "notify-unit-failed.sh").read_text(encoding="utf-8")
        recorder = script[script.index("sysadmin-record-failure") :]
        assert "|| true" in recorder.split("notify-send")[0]


class TestRecordingNeverRaises:
    def test_a_dead_database_returns_false_rather_than_raising(self):
        """The caller's remaining job is to notify a human."""
        with patch(
            "sysadmin.core.unit_failure._sync_session",
            side_effect=OSError("connection refused"),
        ):
            assert record_unit_failure("sysadmin.service") is False

    def test_an_already_open_row_is_not_duplicated(self):
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.execute.return_value.first.return_value = ("existing-id",)

        with patch("sysadmin.core.unit_failure._sync_session", return_value=session):
            assert record_unit_failure("sysadmin.service") is False
        session.add.assert_not_called()

    def test_a_clear_table_writes_one_critical_row(self):
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.execute.return_value.first.return_value = None

        with patch("sysadmin.core.unit_failure._sync_session", return_value=session):
            assert record_unit_failure("sysadmin.service", result="exit-code") is True

        alert = session.add.call_args.args[0]
        assert alert.severity == "critical"
        assert alert.agent == FILED_UNDER
        assert alert.title == unit_failure_title("sysadmin.service")
        session.commit.assert_called_once()


class TestTheDaemonComingBackClosesIt:
    @pytest.mark.asyncio
    async def test_startup_resolves_the_open_row(self):
        """The pairing is the feature.

        Nothing else can ever observe this recovery — the row was written
        while the application was dead. An alert type that can only
        accumulate is how 1,664 orphaned rows happened.
        """
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=1))

        resolved = await resolve_unit_failures(session, OWN_UNIT)

        assert resolved == 1
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_resolve_is_narrowed_to_this_source(self):
        """A future agent reporting unit failures must not be cleared by us."""
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        await resolve_unit_failures(session, OWN_UNIT)

        compiled = str(session.execute.call_args.args[0])
        assert "details" in compiled
        assert "resolved" in compiled
