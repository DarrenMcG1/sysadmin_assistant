"""The login-time replay: what it says, when it waits, and what it returns.

``SNAG-SYSD-005``, Session 126. The live half — a real ``dbus-daemon``, a
real name appearing mid-wait, a real ``notify-send`` — is
``tests/test_failure_replay_live.py``. This half is about the decisions,
which are mostly orderings and mostly the opposite of the obvious one:

- the database is read **before** the bus is asked, so a clean login pays
  nothing
- every way of not-knowing is "could not ask", never "nobody is there"
- the row's own message is carried, never rebuilt
"""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from sysadmin.core.failure_replay import (
    COULD_NOT_ASK,
    MAX_SPOKEN,
    NOBODY_LISTENING,
    SERVER_PRESENT,
    WAIT_BUDGET_SECONDS,
    ask_notification_server,
    compose,
    compose_rollup,
    replay,
    wait_for_notification_server,
)
from sysadmin.core.unit_failure import PendingFailure

#: notify-send's own measured activation bound on an unserved bus, from
#: ``SNAG-SYSD-004``. The wait budget is derived from it and must not exceed
#: it — see ``TestTheBudgetIsDerivedAndNotChosen``.
NOTIFY_SEND_ACTIVATION_BOUND = 60.08


def _pending(
    unit: str = "sysadmin.service",
    *,
    hours_ago: float = 2.0,
    message: str = "systemd gave up.",
) -> PendingFailure:
    return PendingFailure(
        unit=unit,
        title=f"{unit} failed",
        message=message,
        created_at=datetime.now(UTC) - timedelta(hours=hours_ago),
        details={"unit": unit, "source": "systemd_onfailure"},
    )


def _guard_script(tmp_path: Path, *, exits: list[int], says: str = "said") -> Path:
    """A stand-in guard that returns each status in turn, then repeats the last.

    A file rather than a monkeypatched function, because the thing under
    test is that this module *shells out to the one script that owns the
    question* rather than asking D-Bus itself.
    """
    statuses = " ".join(str(e) for e in exits)
    script = tmp_path / "guard.sh"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f"statuses=({statuses})\n"
        f'counter="{tmp_path}/calls"\n'
        'n=$(cat "$counter" 2>/dev/null || echo 0)\n'
        'echo $((n + 1)) > "$counter"\n'
        'idx=$n\n'
        'if (( idx >= ${#statuses[@]} )); then idx=$(( ${#statuses[@]} - 1 )); fi\n'
        f'echo "{says}"\n'
        "exit ${statuses[$idx]}\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _calls(tmp_path: Path) -> int:
    counter = tmp_path / "calls"
    return int(counter.read_text().strip()) if counter.exists() else 0


class TestTheSentenceCarriesTheRowRatherThanRebuildingIt:
    def test_the_rows_own_message_is_carried_verbatim(self):
        """`_schema_diagnosis`'s CAUSE must survive to the screen.

        ``SNAG-DB-005`` put the remedy in the message. Composing a fresh
        sentence here would be a second author of it, free to fall behind
        the day the guard learns a new cause.
        """
        row = _pending(message="systemd gave up. CAUSE: database is at 017, head is 018")
        _, body = compose(row)
        assert "CAUSE: database is at 017, head is 018" in body

    def test_it_adds_the_age_the_row_has_always_carried(self):
        summary, body = compose(_pending(hours_ago=37.7))
        assert "38 hours ago" in body
        assert "has not come back" in body
        assert summary == "STILL FAILED: sysadmin.service"

    def test_a_naive_timestamp_is_read_as_utc_and_never_as_local(self):
        """``SNAG-LOG-009``'s rule: a naive value is never the reader's clock.

        The column is ``timestamp with time zone`` so this is defensive
        only — but reading one as local is exactly the defect that entry
        removed, and it would be wrong by the offset rather than loudly.
        """
        naive = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=3)
        row = PendingFailure(
            unit="sysadmin.service",
            title="sysadmin.service failed",
            message="m",
            created_at=naive,
            details={},
        )
        _, body = compose(row)
        assert "3 hours ago" in body

    def test_the_next_steps_name_the_unit_that_failed(self):
        _, body = compose(_pending(unit="alfred-backend.service"))
        assert "systemctl status alfred-backend.service" in body
        assert "journalctl -u alfred-backend.service" in body

    def test_a_rollup_names_every_unit_it_swallows(self):
        """``SNAG-ESTATE-001``'s rule — a count cannot name anything."""
        rows = [_pending(unit=f"svc-{n}.service") for n in range(5)]
        summary, body = compose_rollup(rows)
        assert "5 units" in summary
        for row in rows:
            assert row.unit in body


class TestNotKnowingIsNeverANo:
    def test_a_missing_guard_is_could_not_ask(self, tmp_path: Path):
        verdict, said = ask_notification_server(tmp_path / "absent.sh")
        assert verdict == COULD_NOT_ASK
        assert "no notification guard" in said

    def test_an_unrecognised_exit_status_is_could_not_ask(self, tmp_path: Path):
        """A status this does not recognise must not be read as "nobody".

        The guard itself refuses to read an unrecognised ``busctl`` answer
        as a "no"; the wrapper honours the same rule one layer out, or a
        change in the guard's verdicts silences the notification.
        """
        verdict, _ = ask_notification_server(_guard_script(tmp_path, exits=[7]))
        assert verdict == COULD_NOT_ASK

    def test_a_guard_that_cannot_be_executed_is_could_not_ask(self, tmp_path: Path):
        script = _guard_script(tmp_path, exits=[0])
        script.chmod(0o644)
        verdict, said = ask_notification_server(script)
        assert verdict == COULD_NOT_ASK
        assert "could not run" in said

    def test_the_three_verdicts_are_distinct(self):
        assert len({SERVER_PRESENT, NOBODY_LISTENING, COULD_NOT_ASK}) == 3


class TestTheWaitIsBoundedAndAsksBeforeItSleeps:
    def test_a_server_that_is_already_there_costs_no_sleeping(self, tmp_path: Path):
        """The common case is a session that is already up.

        If the wait slept first, every login would pay the poll interval to
        learn something one 3 ms call already knew.
        """
        slept: list[float] = []
        landed, _ = wait_for_notification_server(
            _guard_script(tmp_path, exits=[0]), sleep=slept.append
        )
        assert landed is True
        assert slept == []
        assert _calls(tmp_path) == 1

    def test_it_returns_as_soon_as_the_name_is_claimed(self, tmp_path: Path):
        slept: list[float] = []
        landed, _ = wait_for_notification_server(
            _guard_script(tmp_path, exits=[1, 1, 0]), sleep=slept.append
        )
        assert landed is True
        assert len(slept) == 2
        assert _calls(tmp_path) == 3

    def test_it_gives_up_at_the_budget(self, tmp_path: Path):
        """A guard against hanging that can itself hang is not a guard."""
        clock = iter([0.0, 0.0, 1.0, 2.0, 3.0, 99.0])
        landed, said = wait_for_notification_server(
            _guard_script(tmp_path, exits=[1], says="nothing owning it"),
            budget=5.0,
            sleep=lambda _: None,
            now=lambda: next(clock),
        )
        assert landed is False
        assert "nothing owning it" in said

    def test_it_keeps_waiting_through_could_not_ask(self, tmp_path: Path):
        """A bus that is not up *yet* answers ``2``, and login is when it comes up.

        Giving up on the first ``2`` would fail exactly the boot-shaped
        case this exists for, where the user manager is a moment behind.
        """
        landed, _ = wait_for_notification_server(
            _guard_script(tmp_path, exits=[2, 2, 0]), sleep=lambda _: None
        )
        assert landed is True


class TestTheBudgetIsDerivedAndNotChosen:
    def test_it_never_outlasts_the_call_it_replaces(self):
        """``WAIT_BUDGET_SECONDS`` is notify-send's own measured bound.

        The point is not the number but its provenance: the replay spends
        exactly the patience a single blocked ``notify-send`` would have
        spent anyway, on a mechanism that can be observed. A budget above
        that bound would be waiting *longer* than the thing Session 125
        rejected.
        """
        assert WAIT_BUDGET_SECONDS <= NOTIFY_SEND_ACTIVATION_BOUND

    def test_it_is_long_enough_for_the_measured_login_race(self):
        """plasmashell was still initialising ~3 s after the target.

        Measured at the 2026-08-23 session: service active 14:44:55, target
        reached 14:44:57, still logging startup at 14:44:58.
        """
        assert WAIT_BUDGET_SECONDS >= 10.0


class TestTheDatabaseIsReadBeforeTheBusIsAsked:
    def test_a_clean_login_never_asks_the_guard(self, tmp_path: Path):
        """The healthy case must not pay for the broken one.

        This is the ordering the module exists to get right: waiting 60 s
        at every login to discover there was nothing to say would be a cost
        borne by every login for the benefit of about one a month.
        """
        guard = _guard_script(tmp_path, exits=[1])
        spoken: list[tuple[str, str]] = []
        rc = replay(
            guard=guard,
            read=lambda: [],
            announce=lambda s, b: spoken.append((s, b)) or True,
        )
        assert rc == 0
        assert _calls(tmp_path) == 0
        assert spoken == []

    def test_a_standing_failure_with_nobody_listening_is_exit_one(self, tmp_path: Path):
        """The row is not lost; the interruption is. That is what ``1`` records."""
        rc = replay(
            guard=_guard_script(tmp_path, exits=[1]),
            budget=0.0,
            read=lambda: [_pending()],
            announce=lambda s, b: pytest.fail("must not speak to nobody"),
            sleep=lambda _: None,
        )
        assert rc == 1

    def test_a_standing_failure_that_is_announced_is_exit_zero(self, tmp_path: Path):
        spoken: list[tuple[str, str]] = []
        rc = replay(
            guard=_guard_script(tmp_path, exits=[0]),
            read=lambda: [_pending()],
            announce=lambda s, b: spoken.append((s, b)) or True,
        )
        assert rc == 0
        assert len(spoken) == 1
        assert "sysadmin.service" in spoken[0][0]

    def test_an_announcement_that_did_not_land_is_exit_two(self, tmp_path: Path):
        """``1`` and ``2`` are different faults with different next steps.

        Nobody listening is a session that has not finished starting;
        notify-send failing against a server that exists is something
        broken. ``ports_checked``'s rule at the size of an exit status.
        """
        rc = replay(
            guard=_guard_script(tmp_path, exits=[0]),
            read=lambda: [_pending()],
            announce=lambda s, b: False,
        )
        assert rc == 2

    def test_one_notification_per_row_up_to_the_cap(self, tmp_path: Path):
        spoken: list[tuple[str, str]] = []
        rows = [_pending(unit=f"svc-{n}.service") for n in range(MAX_SPOKEN)]
        rc = replay(
            guard=_guard_script(tmp_path, exits=[0]),
            read=lambda: rows,
            announce=lambda s, b: spoken.append((s, b)) or True,
        )
        assert rc == 0
        assert len(spoken) == MAX_SPOKEN

    def test_above_the_cap_it_collapses_to_one_that_names_them_all(self, tmp_path: Path):
        spoken: list[tuple[str, str]] = []
        rows = [_pending(unit=f"svc-{n}.service") for n in range(MAX_SPOKEN + 1)]
        rc = replay(
            guard=_guard_script(tmp_path, exits=[0]),
            read=lambda: rows,
            announce=lambda s, b: spoken.append((s, b)) or True,
        )
        assert rc == 0
        assert len(spoken) == 1
        for row in rows:
            assert row.unit in spoken[0][1]

    def test_a_database_that_cannot_be_read_is_not_a_failed_unit(self, tmp_path: Path):
        """``pending_unit_failures`` returns ``[]`` rather than raising.

        Pinned here as well as at its owner because the consequence lives
        here: a fresh session must not open with a failed unit of its own
        because PostgreSQL was slow to accept connections.
        """
        rc = replay(guard=_guard_script(tmp_path, exits=[0]), read=lambda: [])
        assert rc == 0


class TestItDefersToTheScriptThatOwnsTheQuestion:
    def test_the_guard_is_the_shipped_one(self):
        """One statement of "can this box speak", not two.

        Re-implementing ``NameHasOwner`` in Python would be a second
        statement of a fact ``notification-server-present.sh`` already
        owns — ``max_priority_for`` against ``PRIORITY_MAP``'s rule — and
        the two would be free to disagree.
        """
        from sysadmin.core.failure_replay import GUARD_SCRIPT

        assert GUARD_SCRIPT.name == "notification-server-present.sh"
        assert GUARD_SCRIPT.is_file()

    def test_this_module_does_not_ask_dbus_itself(self):
        """The detector, not just the current state.

        A future edit that reached for ``busctl`` directly would pass every
        other test in this file and rebuild the duplicate the guard exists
        to prevent.
        """
        source = Path(__file__).resolve().parents[1] / "sysadmin" / "core" / "failure_replay.py"
        code = "\n".join(
            line for line in source.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
        # The docstring names them as prose; the code must not call them.
        assert "busctl" not in code.split('"""')[-1]
        assert "NameHasOwner" not in code.split('"""')[-1]

    def test_the_bus_path_reaches_the_guard(self, tmp_path: Path):
        """A test must be able to point this at a bus it started itself."""
        script = tmp_path / "guard.sh"
        script.write_text('#!/usr/bin/env bash\necho "asked about $1"\nexit 0\n', encoding="utf-8")
        script.chmod(0o755)
        _, said = ask_notification_server(script, bus_path="/tmp/probe/bus")
        assert "asked about /tmp/probe/bus" in said


class TestTheNotificationIsNotTransient:
    def test_it_never_expires_and_is_critical(self, monkeypatch):
        """Session 39's rule, and this module is its second instance.

        The failure the whole family exists to fix was a transient toast
        nobody was in the room to see. An expiring notification about a
        dead monitor is that miss with extra steps.
        """
        from sysadmin.core import failure_replay

        seen: list[list[str]] = []

        def fake_run(argv, **kwargs):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, "", "")

        failure_replay.speak("s", "b", runner=fake_run)
        assert "--expire-time=0" in seen[0]
        assert "--urgency=critical" in seen[0]
        assert "--app-name=sysadmin" in seen[0]
