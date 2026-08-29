"""Session 127 — the tray speaks about a backend it cannot reach.

`SNAG-TRAY-009`.  Across the 2026-08-22 outage the tray polled a dead
daemon for **22.2 hours** across two graphical sessions, displayed
``IconState.DISCONNECTED`` and interrupted nobody.  It was silent for two
independent reasons and a fix for one is not half the benefit, it is none:

* **Face 1** — ``ApiWorker._on_disconnected`` emitted ``connection_lost``
  only ``if self._was_connected``, and that flag started ``False``.  A
  tray *arriving* at an already-dead backend has never connected, so it
  never emitted.
* **Face 2** — the handler recoloured an icon.  There was no path from it
  to :mod:`sysadmin_tray.notifications` at all.

The measurement that ranks them is in
:class:`TestTheMeasuredPopulations`: both real outages were arrivals, and
every window Face 1's signal *did* fire on was a 60-second deploy
restart.  The transition signal fired only on noise and never once on a
fault.
"""

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
import yaml

from sysadmin_tray import app as tray_app
from sysadmin_tray.client import ApiWorker
from sysadmin_tray.config import TrayConfig, load_tray_config
from sysadmin_tray.notifications import (
    BACKEND_UNREACHABLE_SEVERITY,
    FP_BACKEND_UNREACHABLE,
    NotificationPolicy,
    NotificationSettings,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── The live measurement this family is calibrated against ───────────
#
# Taken 2026-08-29 from two independent instruments over 30 days.  They
# are constants here rather than prose so a future edit to the grace
# period is compared against the box that motivated it.

#: Longest deploy restart in the daemon's journal.  104 of them, all of
#: 2, 3, 12 or 13 seconds, with nothing between this and a reboot.
MEASURED_DEPLOY_RESTART_SECONDS = 13.0

#: Every one of the 27 unreachable windows the tray's own journal holds:
#: exactly one missed poll at ``status_poll_seconds: 30``.
MEASURED_TRAY_WINDOW_SECONDS = 60.0

#: The shorter of the two real outages (2026-08-22T18:34:46 → 23:38:42).
MEASURED_REAL_OUTAGE_SECONDS = 5 * 3600 + 4 * 60


class FakeClock:
    """Monotonic-style clock the tests can wind forward."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _policy(clock: FakeClock, **settings) -> NotificationPolicy:
    settings.setdefault("min_severity", "warning")
    return NotificationPolicy(NotificationSettings(**settings), clock=clock)


def _dead_worker() -> ApiWorker:
    """A worker whose every request raises, as against a dead daemon."""
    worker = ApiWorker("http://127.0.0.1:8500")
    worker._client = MagicMock()
    worker._client.get.side_effect = httpx.ConnectError("connection refused")
    return worker


# ── Face 1: the arrival ──────────────────────────────────────────────


class TestATrayThatArrivesAtADeadBackendSaysSo:
    """The population is arrivals, and arrivals used to be silent."""

    def test_the_first_failed_poll_emits_connection_lost(self):
        worker = _dead_worker()
        seen = []
        worker.connection_lost.connect(lambda: seen.append(True))

        worker.fetch_status()

        assert seen == [True], (
            "a tray starting against a dead backend has never connected, "
            "and that is the shape both real outages took"
        )

    def test_it_emits_once_per_episode_not_once_per_poll(self):
        worker = _dead_worker()
        seen = []
        worker.connection_lost.connect(lambda: seen.append(True))

        for _ in range(5):
            worker.fetch_status()

        assert seen == [True]

    def test_the_tick_carries_the_episodes_age_and_it_grows(self):
        worker = _dead_worker()
        ages: list[float] = []
        worker.backend_unreachable.connect(ages.append)

        with patch("sysadmin_tray.client.time.monotonic", side_effect=[
            100.0, 100.0,   # episode opens, age read
            130.0,          # second poll
            160.0,          # third poll
        ]):
            worker.fetch_status()
            worker.fetch_status()
            worker.fetch_status()

        assert ages == [0.0, 30.0, 60.0], (
            "the grace period is measured against this, so it has to be "
            "the episode's age and not the poll's"
        )

    def test_reconnecting_closes_the_episode_and_the_clock_restarts(self):
        worker = _dead_worker()
        restored = []
        worker.connection_restored.connect(lambda: restored.append(True))

        worker.fetch_status()
        assert worker._unreachable_since is not None

        worker._client.get.side_effect = None
        worker._client.get.return_value = _ok_status()
        worker.fetch_status()

        assert restored == [True]
        assert worker._unreachable_since is None

        worker._client.get.side_effect = httpx.ConnectError("gone again")
        ages: list[float] = []
        worker.backend_unreachable.connect(ages.append)
        worker.fetch_status()
        assert ages == [pytest.approx(0.0, abs=1.0)], (
            "a second outage is a new episode, not a continuation"
        )

    def test_the_third_state_is_distinguishable_from_a_loss(self):
        """``None`` is not ``False``: the whole of Face 1 is that gap."""
        worker = ApiWorker("http://127.0.0.1:8500")
        assert worker._was_connected is None


def _ok_status():
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"services": [], "all_healthy": True}
    return resp


# ── Face 2: the policy ───────────────────────────────────────────────


class TestTheMeasuredPopulations:
    """Driven at the numbers the box produced, not at round figures."""

    def test_a_deploy_restart_is_silent(self):
        """104 of these a month.  Speaking about them is the failure mode."""
        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(
            MEASURED_DEPLOY_RESTART_SECONDS
        ) is None

    def test_the_widest_window_the_tray_has_ever_seen_is_silent(self):
        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(
            MEASURED_TRAY_WINDOW_SECONDS
        ) is None

    def test_the_real_outage_speaks(self):
        clock = FakeClock()
        policy = _policy(clock)
        request = policy.evaluate_backend_unreachable(
            MEASURED_REAL_OUTAGE_SECONDS
        )
        assert request is not None
        assert request.severity == BACKEND_UNREACHABLE_SEVERITY

    def test_the_grace_sits_between_the_two_populations(self):
        """The void is what makes the number safe to be roughly wrong in."""
        grace = NotificationSettings().backend_unreachable_grace_seconds
        assert MEASURED_TRAY_WINDOW_SECONDS < grace < MEASURED_REAL_OUTAGE_SECONDS
        assert grace >= 5 * MEASURED_TRAY_WINDOW_SECONDS
        assert grace >= 20 * MEASURED_DEPLOY_RESTART_SECONDS


class TestWhatItSaysAndHowLoudly:
    def test_it_opens_loud_because_the_grace_already_did_escalations_job(self):
        """``escalation_polls`` is deliberately not applied here.

        A new ``critical`` normally opens at ``info`` and escalates once
        it is still failing several polls later.  Waiting out 300 s *is*
        that test; applying both would speak quietly at 300 s and loudly
        at 390 s about one fault.
        """
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=3)

        request = policy.evaluate_backend_unreachable(300.0)

        assert request is not None
        assert request.severity == "critical", (
            "not 'info' — the opening notification is the loud one"
        )
        assert request.transient is False, (
            "critical is the only rung the tray leaves on screen, and the "
            "fault this exists for ran 17 hours in an occupied room"
        )

    def test_it_names_the_monitoring_not_the_machine(self):
        clock = FakeClock()
        request = _policy(clock).evaluate_backend_unreachable(300.0)
        assert request is not None
        body = request.body.lower()
        assert "monitoring is down" in body
        assert "machine" not in body, (
            "health_review.confidence_phrase had to learn this after a "
            "model published 'The machine was down' about an unwatched box"
        )

    def test_it_carries_a_next_step_because_it_cannot_carry_the_cause(self):
        clock = FakeClock()
        request = _policy(clock).evaluate_backend_unreachable(300.0)
        assert request is not None
        assert "journalctl -u sysadmin" in request.body

    def test_the_elapsed_time_is_rendered_from_the_episode(self):
        clock = FakeClock()
        request = _policy(clock).evaluate_backend_unreachable(5 * 3600)
        assert request is not None
        assert "5 hours" in request.body


class TestItSpeaksOncePerEpisode:
    def test_a_standing_outage_is_not_restated_every_poll(self):
        clock = FakeClock()
        policy = _policy(clock)

        spoke = []
        for elapsed in (300.0, 330.0, 360.0, 390.0):
            request = policy.evaluate_backend_unreachable(elapsed)
            clock.advance(30)
            if request is not None:
                spoke.append(request)

        assert len(spoke) == 1

    def test_a_reminder_arrives_after_reminder_hours(self):
        clock = FakeClock()
        policy = _policy(clock, reminder_hours=24.0)

        first = policy.evaluate_backend_unreachable(300.0)
        assert first is not None

        clock.advance(23 * 3600)
        assert policy.evaluate_backend_unreachable(23 * 3600 + 300) is None

        clock.advance(2 * 3600)
        later = policy.evaluate_backend_unreachable(25 * 3600 + 300)
        assert later is not None
        assert later.reminder is True
        assert later.transient is False

    def test_reminder_hours_zero_disables_the_restatement(self):
        clock = FakeClock()
        policy = _policy(clock, reminder_hours=0.0)
        assert policy.evaluate_backend_unreachable(300.0) is not None
        clock.advance(100 * 3600)
        assert policy.evaluate_backend_unreachable(400 * 3600) is None


class TestTheEpisodeIsClosedByTheConnection:
    def test_backend_reachable_ends_the_episode(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=0)

        assert policy.evaluate_backend_unreachable(300.0) is not None
        policy.backend_reachable()

        clock.advance(600)
        assert policy.evaluate_backend_unreachable(300.0) is not None, (
            "a second outage after a recovery is a second episode"
        )

    def test_an_alerts_poll_cannot_close_it(self):
        """``_close_inactive`` must not reach this fingerprint.

        It is not an alert row, so "absent from this poll" carries no
        information about it — and while the episode is open the alerts
        route cannot be read at all.
        """
        from sysadmin_tray.models import AlertsResponse

        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(300.0) is not None

        policy.evaluate(AlertsResponse(alerts=[], count=0))

        state = policy._states[FP_BACKEND_UNREACHABLE]
        assert state.notified_this_episode is True, (
            "an alerts payload decided a question about reachability"
        )

    def test_the_flap_cooldown_survives_a_recovery(self):
        """Two failures either side of a recovery are one story."""
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=30)

        assert policy.evaluate_backend_unreachable(300.0) is not None
        policy.backend_reachable()

        clock.advance(5 * 60)
        assert policy.evaluate_backend_unreachable(300.0) is None

        clock.advance(31 * 60)
        assert policy.evaluate_backend_unreachable(300.0) is not None


class TestTheSuppressionRulesReachIt:
    def test_zero_grace_disables_the_family(self):
        clock = FakeClock()
        policy = _policy(clock, backend_unreachable_grace_seconds=0.0)
        assert policy.evaluate_backend_unreachable(10 * 3600) is None

    def test_notifications_disabled_disables_it(self):
        clock = FakeClock()
        policy = _policy(clock, enabled=False)
        assert policy.evaluate_backend_unreachable(10 * 3600) is None

    def test_snoozing_it_silences_it(self):
        clock = FakeClock()
        policy = _policy(clock)
        request = policy.evaluate_backend_unreachable(300.0)
        assert request is not None
        assert request.snooze_key is not None

        policy.backend_reachable()
        policy.snooze(request.snooze_key, minutes=60)
        clock.advance(30 * 60)
        assert policy.evaluate_backend_unreachable(300.0) is None

        clock.advance(31 * 60)  # snooze expired
        assert policy.evaluate_backend_unreachable(300.0) is not None

    def test_dnd_without_allow_critical_silences_it(self):
        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(
            300.0, dnd_active=True, dnd_allow_critical=False,
        ) is None

    def test_dnd_with_allow_critical_lets_it_through(self):
        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(
            300.0, dnd_active=True, dnd_allow_critical=True,
        ) is not None

    def test_a_desktop_inhibit_does_not_silence_a_critical(self):
        clock = FakeClock()
        policy = _policy(clock)
        assert policy.evaluate_backend_unreachable(
            300.0, desktop_inhibited=True,
        ) is not None


# ── The derivation, pinned to its sources ────────────────────────────


class TestTheGraceIsDerivedRatherThanPicked:
    """``max(3 × status_poll_seconds, min_stall_grace_seconds)``.

    Both halves are borrowed, so both are read back out of the shipped
    file rather than restated here — a constant written beside the thing
    it was derived from is free to drift from it, which is what
    ``SNAG-DB-003`` is about.
    """

    @staticmethod
    def _shipped() -> dict:
        return yaml.safe_load((REPO_ROOT / "config.yaml").read_text()) or {}

    def test_the_shipped_value_equals_its_derivation(self):
        raw = self._shipped()
        poll = raw["tray"]["status_poll_seconds"]
        floor = raw["self_monitor"]["min_stall_grace_seconds"]
        multiplier = raw["self_monitor"]["stall_grace_multiplier"]
        shipped = raw["notifications"]["tray"][
            "backend_unreachable_grace_seconds"
        ]

        assert shipped == max(multiplier * poll, floor)

    def test_the_floor_is_what_binds_here(self):
        """Stated as an assertion because it is the reason for the floor.

        ``status_poll_seconds`` has two producers — ``10`` in
        :class:`TrayConfig` and ``30`` in the shipped file — so the
        multiple alone spans 30–90 s while the 13 s restart it must clear
        does not move with the poll interval at all.
        """
        raw = self._shipped()
        multiplier = raw["self_monitor"]["stall_grace_multiplier"]
        floor = raw["self_monitor"]["min_stall_grace_seconds"]

        for poll in (TrayConfig().status_poll_seconds,
                     raw["tray"]["status_poll_seconds"]):
            assert multiplier * poll < floor, (
                "if the multiple ever exceeds the floor, the grace starts "
                "tracking the observer instead of the noise"
            )

    def test_the_two_producers_of_the_poll_interval_really_do_disagree(self):
        """The premise of the test above, asserted rather than assumed."""
        raw = self._shipped()
        assert TrayConfig().status_poll_seconds != raw["tray"][
            "status_poll_seconds"
        ]

    def test_the_leaf_is_read_from_the_file_and_not_merely_defaulted(
        self, tmp_path,
    ):
        """Driven at a *mutated copy*, because the shipped value is the default.

        Asserting ``load_tray_config(config.yaml) == the value in
        config.yaml`` is green whether or not the loader ever looks at
        the file — 300 is also :class:`NotificationSettings`' default, so
        nothing in that population could have forced a different reading.
        A leaf parsed by pydantic and read by nothing is ``SNAG-CFG-001``
        and this is precisely the test that would miss it.  Falsified by
        removing the key from ``config.py``'s parse loop, which the
        equality form survived.
        """
        raw = self._shipped()
        witness = 137.0
        assert witness != TrayConfig().backend_unreachable_grace_seconds
        raw["notifications"]["tray"][
            "backend_unreachable_grace_seconds"
        ] = witness

        copy = tmp_path / "config.yaml"
        copy.write_text(yaml.safe_dump(raw))
        assert load_tray_config(copy).backend_unreachable_grace_seconds == witness

    def test_the_shipped_file_and_the_model_agree_today(self):
        """Separate from the read test on purpose — a different claim.

        The one above proves the *path* exists; this one records that the
        box and the packaged default currently say the same thing, so a
        default install and this host behave alike.  Two tests composing
        rather than one doing both.
        """
        raw = self._shipped()
        assert (
            raw["notifications"]["tray"]["backend_unreachable_grace_seconds"]
            == TrayConfig().backend_unreachable_grace_seconds
            == NotificationSettings().backend_unreachable_grace_seconds
        )


# ── The wiring, which is what Face 2 was missing ─────────────────────


class TestTheHandlerReachesTheNotifier:
    def test_the_tick_is_connected_to_the_tray(self):
        """``app.py`` must join the two halves, or both fixes are inert."""
        source = inspect.getsource(tray_app)
        tree = ast.parse(source)
        connected = {
            f"{ast.unparse(node.func.value)}"
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "connect"
            and isinstance(node.func.value, ast.Attribute)
        }
        assert "client.backend_unreachable" in connected

    def test_the_tray_dispatches_what_the_policy_returns(self, qapp):
        from sysadmin_tray.tray_icon import TrayIcon

        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True, min_severity="warning",
            backend_unreachable_grace_seconds=300.0,
        )
        notifier = MagicMock()
        notifier.desktop_inhibited.return_value = False
        tray.set_notifier(notifier)

        tray.on_backend_unreachable(60.0)
        assert notifier.notify.call_count == 0

        tray.on_backend_unreachable(300.0)
        assert notifier.notify.call_count == 1

    def test_reconnecting_closes_the_policys_episode(self, qapp):
        from sysadmin_tray.tray_icon import TrayIcon

        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True, min_severity="warning",
            flap_cooldown_minutes=0,
            backend_unreachable_grace_seconds=300.0,
        )
        notifier = MagicMock()
        notifier.desktop_inhibited.return_value = False
        tray.set_notifier(notifier)

        tray.on_backend_unreachable(300.0)
        tray.on_connection_restored()
        tray.on_backend_unreachable(300.0)

        assert notifier.notify.call_count == 2, (
            "the recovery must close the episode, or the second outage is "
            "swallowed as a continuation of the first"
        )


class TestTheRetiredChecksDetector:
    """`SNAG-TRAY-009`'s ``sysadmin-check-snags`` detector, re-homed.

    ``FROZEN_TABLES``' rule: the check retires with the entry and the
    detector does not.  What is re-homed is the **corrected** predicate,
    because the retired one answered ``match`` — *"the tray is still
    silent"* — against the fixed code, which is a false negative in the
    one direction that matters.  Measured against both states:

    * Its Face 1 test asked whether the emit sits inside an ``if`` that
      reads ``_was_connected``.  That is ``True`` **before and after**:
      the fix keeps the guard and corrects its polarity, so the defect
      was never the guard's existence, it was the guard's reachability
      from the initial state.
    * Its "initialised ``False``" test walked the whole module for an
      ``Assign`` of ``False`` to that name.  At HEAD it matched **two** —
      line 91, the real initialiser, and line 411, inside
      ``_on_disconnected`` — so it was right for the wrong reason.  After
      the fix the initialiser is an ``AnnAssign`` of ``None``, invisible
      to it, and it went on matching the assignment *inside the method*.
      It never distinguished an initialiser from any assignment anywhere.
    * Its Face 2 test was aimed at ``on_connection_lost`` by name, and
      the speaking legitimately moved to a new method.

    So the useful part is a predicate about the **initialiser**, and the
    rest of this file replaces the shape tests with behaviour.
    """

    def test_the_initialiser_is_not_the_two_valued_flag(self):
        from sysadmin_tray import client as client_module

        tree = ast.parse(Path(client_module.__file__).read_text())
        init = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        assigned = [
            node.value for node in ast.walk(init)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Attribute)
            and target.attr == "_was_connected"
        ]
        assert assigned, "_was_connected is no longer initialised in __init__"
        for value in assigned:
            assert not (
                isinstance(value, ast.Constant) and value.value is False
            ), (
                "initialising to False spells 'never connected' and 'connected "
                "then lost it' the same way, which is the whole of Face 1"
            )


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
