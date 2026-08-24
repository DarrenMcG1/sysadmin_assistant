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

from sysadmin.core.schema_guard import SchemaStatus
from sysadmin.core.unit_failure import (
    FILED_UNDER,
    OWN_UNIT,
    SOURCE,
    _details,
    _schema_diagnosis,
    record_unit_failure,
    resolve_unit_failures,
    unit_failure_title,
)

REPO = Path(__file__).resolve().parents[1]

#: What `_schema_diagnosis` returns when the schema is fine. Written out
#: rather than defaulted in `_details`, because a default would let a
#: caller that forgot the block produce a row indistinguishable from one
#: whose schema was checked — the `UnitFinding.enabled` trap.
_MATCHED = {"verdict": "match", "head": "013", "current": "013", "problem": None}


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
        details = _details("sysadmin.service", "exit-code", "1", "5", _MATCHED)
        assert details["source"] == SOURCE
        assert details["raised_by"].endswith("notify-unit-failed.sh")
        assert details["kind"] == "unit_failure"

    def test_details_carry_the_systemd_verdict(self):
        """result and restarts are the first two questions asked later."""
        details = _details("sysadmin.service", "oom-kill", "9", "5", _MATCHED)
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


# ── SNAG-DB-005 ─────────────────────────────────────────────────────────
#
# On 2026-08-23 this handler fired correctly and said only
# `result=exit-code, restarts=5`.  The fault was an unapplied migration,
# the remedy was one command, and `sysadmin/core/schema_guard.py` knew
# both and wrote them only to the journal.  The daemon stayed dead 23
# hours.  These pin that the diagnosis reaches the row, that a healthy
# schema is recorded without being narrated, and — the one that matters
# most — that the annotation can never suppress the row it annotates.


def _status(verdict, head="013", current="013", problem=None):
    return SchemaStatus(verdict, head, current, problem)


class TestSchemaDiagnosis:
    def test_a_matching_schema_says_nothing_in_the_message(self):
        """A critical toast is not the place to rule causes out one by one."""
        with patch(
            "sysadmin.core.unit_failure.schema_status", return_value=_status("match")
        ):
            note, block = _schema_diagnosis()
        assert note == ""
        assert block["verdict"] == "match"

    def test_a_matching_schema_is_still_recorded(self):
        """"Checked, and it was not this" is not "never checked".

        `ports_checked`'s rule: the reader of a stale row cannot tell the
        two apart unless the verdict is stored either way.
        """
        with patch(
            "sysadmin.core.unit_failure.schema_status", return_value=_status("match")
        ):
            _, block = _schema_diagnosis()
        assert block == {
            "verdict": "match",
            "head": "013",
            "current": "013",
            "problem": None,
        }

    def test_a_mismatch_names_the_cause_and_the_remedy(self):
        problem = "database schema is at revision 012 — run `uv run alembic upgrade head`"
        with patch(
            "sysadmin.core.unit_failure.schema_status",
            return_value=_status("mismatch", current="012", problem=problem),
        ):
            note, block = _schema_diagnosis()
        assert "CAUSE:" in note
        assert problem in note
        assert block["verdict"] == "mismatch"

    def test_an_unknown_schema_is_named_not_silent(self):
        """The database being unreadable is itself a candidate cause."""
        with patch(
            "sysadmin.core.unit_failure.schema_status",
            return_value=_status("unknown", current=None, problem="connection refused"),
        ):
            note, block = _schema_diagnosis()
        assert note.strip() != ""
        assert block["verdict"] == "unknown"

    def test_it_cannot_raise(self):
        """The rule the whole helper is written around.

        This annotates a row whose purpose is to survive the application
        being dead. An annotation that took the row down with it would be
        strictly worse than no annotation at all.
        """
        with patch(
            "sysadmin.core.unit_failure.schema_status",
            side_effect=RuntimeError("alembic exploded"),
        ):
            note, block = _schema_diagnosis()
        assert note == ""
        assert block["verdict"] == "unknown"
        assert "alembic exploded" in block["problem"]


class TestTheRowCarriesTheDiagnosis:
    def _record(self, status):
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.execute.return_value.first.return_value = None
        with (
            patch("sysadmin.core.unit_failure._sync_session", return_value=session),
            patch("sysadmin.core.unit_failure.schema_status", return_value=status),
        ):
            assert record_unit_failure("sysadmin.service", result="exit-code") is True
        return session.add.call_args[0][0]

    def test_mismatch_reaches_the_alert_message(self):
        """The message is what a notification body renders verbatim."""
        alert = self._record(
            _status("mismatch", current="012", problem="at 012, expects 013")
        )
        assert "CAUSE:" in alert.message
        assert "at 012, expects 013" in alert.message

    def test_mismatch_reaches_the_details_block(self):
        alert = self._record(_status("mismatch", current="012", problem="at 012"))
        assert alert.details["schema"]["verdict"] == "mismatch"
        assert alert.details["schema"]["current"] == "012"
        assert alert.details["schema"]["head"] == "013"

    def test_a_healthy_schema_leaves_the_message_as_it_was(self):
        alert = self._record(_status("match"))
        assert "CAUSE:" not in alert.message
        assert alert.message.endswith("Monitoring is down until it is started.")
        assert alert.details["schema"]["verdict"] == "match"

    def test_the_schema_block_is_always_present(self):
        """Absent means nothing looked, and nothing may say that by accident."""
        for verdict in ("match", "mismatch", "unknown"):
            alert = self._record(_status(verdict, problem=None if verdict == "match" else "x"))
            assert "schema" in alert.details
            assert alert.details["schema"]["verdict"] == verdict

    def test_a_broken_schema_check_still_writes_the_row(self):
        """The regression this fix could most easily have introduced."""
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.execute.return_value.first.return_value = None
        with (
            patch("sysadmin.core.unit_failure._sync_session", return_value=session),
            patch(
                "sysadmin.core.unit_failure.schema_status",
                side_effect=RuntimeError("boom"),
            ),
        ):
            assert record_unit_failure("sysadmin.service") is True
        assert session.add.called
        assert session.commit.called


class TestTheNotifierCarriesItToo:
    """The row is durable; the toast is what a human actually sees.

    Session 69's outage was announced by a persistent critical toast that
    named neither cause nor remedy, so both destinations are pinned.
    """

    SCRIPT = REPO / "scripts" / "notify-unit-failed.sh"

    def test_it_asks_the_schema_check(self):
        assert "check-migrations.sh" in self.SCRIPT.read_text()

    def test_a_mismatch_puts_the_remedy_in_the_body(self):
        text = self.SCRIPT.read_text()
        assert "CAUSE:" in text
        assert "alembic upgrade head" in text

    def test_it_no_longer_tells_the_reader_to_sudo_systemctl_status(self):
        """Verified as gaddi: `systemctl status` and `journalctl -u` exit 0.

        A next step the reader can take more easily than they were told is
        the same defect as the missing remedy, one line up.
        """
        text = self.SCRIPT.read_text()
        assert "sudo systemctl status" not in text

    def test_a_healthy_schema_adds_nothing_to_the_body(self):
        """The `0)` arm of the case must stay empty."""
        text = self.SCRIPT.read_text()
        case_body = text.split("case \"$schema_rc\" in")[1].split("esac")[0]
        zero_arm = case_body.split("0)")[1].split(";;")[0]
        assert zero_arm.strip() == ""
