"""The daemon's desktop notifications, and the four gates before them.

Wired 2026-08-11 (SNAG-CFG-001). Before it, ``notifications.desktop`` was
parsed by pydantic and read by nothing, and the only method that had ever
consulted it — ``Notifier.send_notification`` — had no production caller:
every alerting path in the daemon ended at a database row and waited for
the tray to come and read it.

What is worth pinning here is not the transport, which is one subprocess
call, but the **gates**. The monitor writes one alert row per failed
check — 186 rows for a single ``venture-assistant`` outage, 123 for one
``internet`` outage, 88 criticals a day at steady state — so a notifier
that speaks per row is not a feature, it is a denial of service against
its own reader. Two of the four gates exist solely because of those
numbers, and both fail *closed*: an unknown answer produces silence,
never a toast.
"""

from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import AppConfig, DesktopNotificationsConfig
from sysadmin.monitor.desktop import (
    DesktopNotifier,
    TrayPresence,
    session_bus_address,
)

RAISED = {
    "id": "1f0e0d3a-0000-4000-8000-000000000000",
    "agent": "sysadmin",
    "severity": "critical",
    "title": "venture-chat unreachable",
}


def notifier(*, open_alerts: int = 1) -> DesktopNotifier:
    """A notifier whose incident query returns ``open_alerts``."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=open_alerts)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    return DesktopNotifier(session_factory=lambda: session)


class TestTrayPresence:
    def test_a_daemon_that_has_seen_nothing_is_not_watched(self):
        assert TrayPresence().is_watching(180) is False
        assert TrayPresence().seconds_since_seen() is None

    def test_a_recent_poll_counts_as_present(self):
        presence = TrayPresence()
        presence.mark_seen()

        assert presence.is_watching(180) is True

    def test_a_stale_poll_does_not(self):
        """A tray that has gone away must not silence the daemon forever."""
        presence = TrayPresence()
        with patch("sysadmin.monitor.desktop.time.monotonic", return_value=1000.0):
            presence.mark_seen()
        with patch("sysadmin.monitor.desktop.time.monotonic", return_value=1181.0):
            assert presence.is_watching(180) is False

    def test_never_seen_is_distinct_from_seen_long_ago(self):
        """Both allow speech; only one of them means "the tray existed"."""
        presence = TrayPresence()
        assert presence.ever_seen is False

        presence.mark_seen()
        assert presence.ever_seen is True


class TestTheGates:
    """Four questions, in cost order, each answered before the next."""

    async def _handle(self, desktop, *, config=None, watching=False, dnd=False):
        settings = MagicMock()
        settings.notifications.desktop = config or DesktopNotificationsConfig()
        presence = TrayPresence()
        if watching:
            presence.mark_seen()

        with (
            patch("sysadmin.monitor.desktop.get_config", return_value=settings),
            patch("sysadmin.monitor.desktop.tray_presence", presence),
            patch(
                "sysadmin.monitor.desktop.dnd_manager.should_suppress",
                return_value=dnd,
            ),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            await desktop.on_alert_raised(dict(RAISED))
        return send

    async def test_a_new_incident_speaks(self):
        send = await self._handle(notifier(open_alerts=1))

        send.assert_awaited_once()
        assert send.await_args.args[0] == "critical"
        assert send.await_args.args[1] == "venture-chat unreachable"

    async def test_the_same_outage_still_failing_does_not(self):
        """186 rows for one outage; the reader wants one notification."""
        send = await self._handle(notifier(open_alerts=2))

        send.assert_not_awaited()

    async def test_a_watching_tray_silences_the_daemon(self):
        """Otherwise every alert arrives twice on the same desktop."""
        send = await self._handle(notifier(), watching=True)

        send.assert_not_awaited()

    async def test_dnd_silences_it(self):
        send = await self._handle(notifier(), dnd=True)

        send.assert_not_awaited()

    async def test_disabled_silences_it(self):
        send = await self._handle(
            notifier(), config=DesktopNotificationsConfig(enabled=False)
        )

        send.assert_not_awaited()

    async def _handle_severity(self, severity: str, min_severity: str):
        desktop = notifier()
        settings = MagicMock()
        settings.notifications.desktop = DesktopNotificationsConfig(
            min_severity=min_severity
        )

        with (
            patch("sysadmin.monitor.desktop.get_config", return_value=settings),
            patch("sysadmin.monitor.desktop.tray_presence", TrayPresence()),
            patch(
                "sysadmin.monitor.desktop.dnd_manager.should_suppress",
                return_value=False,
            ),
            patch.object(desktop, "send", new=AsyncMock()) as send,
        ):
            await desktop.on_alert_raised({**RAISED, "severity": severity})
        return send

    @pytest.mark.parametrize(
        ("severity", "min_severity", "speaks"),
        [
            ("info", "warning", False),       # the default threshold
            ("warning", "warning", True),
            ("critical", "warning", True),
            ("warning", "critical", False),   # raised to criticals only
            ("critical", "critical", True),
            ("info", "info", True),           # lowered to everything
        ],
    )
    async def test_the_severity_threshold_is_obeyed(
        self, severity, min_severity, speaks
    ):
        send = await self._handle_severity(severity, min_severity)

        assert bool(send.await_count) is speaks


class TestFailingClosed:
    """An unknown answer must produce silence, never a storm."""

    async def test_a_database_error_does_not_become_a_notification(self):
        session = MagicMock()
        session.scalar = AsyncMock(side_effect=RuntimeError("connection reset"))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        desktop = DesktopNotifier(session_factory=lambda: session)

        assert await desktop._is_new_incident("anything") is False

    async def test_a_subscriber_never_raises(self):
        """A raising subscriber takes the bus's task down for everyone."""
        desktop = DesktopNotifier(session_factory=lambda: 1 / 0)

        with patch(
            "sysadmin.monitor.desktop.get_config", side_effect=RuntimeError("boom")
        ):
            await desktop.on_alert_raised(dict(RAISED))  # must not raise

    async def test_one_open_alert_is_ours_and_counts_as_new(self):
        assert await notifier(open_alerts=1)._is_new_incident("t") is True

    async def test_zero_open_alerts_still_counts_as_new(self):
        """Resolved between insert and event: speak rather than swallow."""
        assert await notifier(open_alerts=0)._is_new_incident("t") is True


class TestSessionBus:
    def test_an_inherited_address_wins(self):
        with patch.dict("os.environ", {"DBUS_SESSION_BUS_ADDRESS": "unix:path=/x"}):
            assert session_bus_address() == "unix:path=/x"

    def test_it_falls_back_to_the_well_known_socket(self):
        """sysadmin.service is a system unit with no bus in its environment."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("sysadmin.monitor.desktop.os.getuid", return_value=1000),
            patch("sysadmin.monitor.desktop.Path.exists", return_value=True),
        ):
            assert session_bus_address() == "unix:path=/run/user/1000/bus"

    def test_no_socket_means_no_bus_rather_than_a_bad_address(self):
        """Booted before login: report unreachable instead of failing later."""
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("sysadmin.monitor.desktop.Path.exists", return_value=False),
        ):
            assert session_bus_address() is None


class TestTransport:
    def _send(self, desktop, **kwargs):
        return desktop._send_blocking(
            kwargs.pop("severity", "critical"), "Title", "Body"
        )

    def test_a_missing_binary_is_reported_not_raised(self):
        with patch("sysadmin.monitor.desktop.shutil.which", return_value=None):
            assert self._send(DesktopNotifier()) is False

    def test_no_session_bus_means_no_send(self):
        with (
            patch("sysadmin.monitor.desktop.shutil.which", return_value="/n/s"),
            patch("sysadmin.monitor.desktop.session_bus_address", return_value=None),
            patch("sysadmin.monitor.desktop.subprocess.run") as run,
        ):
            assert self._send(DesktopNotifier()) is False
            run.assert_not_called()

    def test_a_successful_send_carries_urgency_and_expiry(self):
        with (
            patch("sysadmin.monitor.desktop.shutil.which", return_value="/n/s"),
            patch(
                "sysadmin.monitor.desktop.session_bus_address",
                return_value="unix:path=/run/user/1000/bus",
            ),
            patch(
                "sysadmin.monitor.desktop.subprocess.run",
                return_value=MagicMock(returncode=0, stderr=""),
            ) as run,
        ):
            assert self._send(DesktopNotifier()) is True

        argv = run.call_args.args[0]
        assert "--urgency" in argv and argv[argv.index("--urgency") + 1] == "critical"
        # 0 ms = persist until dismissed, which is only tolerable at one
        # notification per incident.
        assert argv[argv.index("--expire-time") + 1] == "0"
        # "--" before the text, so a title beginning with a dash is not
        # parsed as a flag.
        assert argv[-3] == "--"
        assert run.call_args.kwargs["env"]["DBUS_SESSION_BUS_ADDRESS"] == (
            "unix:path=/run/user/1000/bus"
        )

    def test_a_rejected_send_reports_false(self):
        """notify-send exits 1 and explains itself; the exit code is real."""
        with (
            patch("sysadmin.monitor.desktop.shutil.which", return_value="/n/s"),
            patch(
                "sysadmin.monitor.desktop.session_bus_address", return_value="unix:x"
            ),
            patch(
                "sysadmin.monitor.desktop.subprocess.run",
                return_value=MagicMock(
                    returncode=1,
                    stderr="Cannot autolaunch D-Bus without X11 $DISPLAY",
                ),
            ),
        ):
            assert self._send(DesktopNotifier()) is False

    def test_a_wedged_notification_daemon_cannot_hang_the_loop(self):
        import subprocess

        with (
            patch("sysadmin.monitor.desktop.shutil.which", return_value="/n/s"),
            patch(
                "sysadmin.monitor.desktop.session_bus_address", return_value="unix:x"
            ),
            patch(
                "sysadmin.monitor.desktop.subprocess.run",
                side_effect=subprocess.TimeoutExpired("notify-send", 5),
            ),
        ):
            assert self._send(DesktopNotifier()) is False


class TestPresenceIsMarkedByTheRoute:
    """The gate is only as good as the signal that feeds it."""

    async def test_polling_the_alerts_route_marks_the_tray_present(
        self, test_client, mock_session
    ):
        from sysadmin.monitor.desktop import tray_presence

        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result)

        with patch.object(tray_presence, "mark_seen") as mark:
            await test_client.get("/api/sysadmin/alerts")

        mark.assert_called_once()

    async def test_another_route_does_not(self, test_client, mock_session):
        """A dashboard reading /status shows nobody an alert."""
        from sysadmin.monitor.desktop import tray_presence

        with patch.object(tray_presence, "mark_seen") as mark:
            await test_client.get("/health")

        mark.assert_not_called()


class TestSubscribedInProduction:
    def test_the_lifespan_subscribes_the_notifier(self):
        """A notifier nobody subscribes is the defect being fixed here.

        `Notifier.send_notification` was fully implemented, DND-aware and
        never called by anything but its own tests; a textual check is
        cheap insurance against this one going the same way.
        """
        from pathlib import Path

        import sysadmin.main as main

        source = Path(main.__file__).read_text(encoding="utf-8")
        assert 'event_bus.subscribe("alert.raised"' in source
        assert "desktop_notifier.on_alert_raised" in source


class TestConfigIsReadAtLast:
    def test_the_section_has_a_consumer(self):
        """SNAG-CFG-001: parsed by pydantic, read by nobody, for months."""
        from pathlib import Path

        source = Path(
            __file__
        ).resolve().parents[1] / "sysadmin" / "monitor" / "desktop.py"
        text = source.read_text(encoding="utf-8")

        assert "notifications.desktop" in text
        assert "config.min_severity" in text or "min_severity" in text

    def test_the_grace_window_is_a_multiple_of_the_tray_poll(self):
        """One dropped poll must not produce a burst of daemon toasts."""
        assert DesktopNotificationsConfig().tray_grace_seconds == 180


class _Clock:
    """An injected monotonic clock, so a 24-hour window costs no sleep."""

    def __init__(self, now: float = 1000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance_hours(self, hours: float) -> None:
        self.now += hours * 3600


def sweeper(clock: _Clock, open_titles: list[str] | None = None):
    """A notifier whose gate-2 query says "new" and whose sweep sees *open_titles*.

    The list is returned so a test can close a fault by emptying it —
    which is the only way ``_spoken`` is ever pruned.
    """
    still_open = ["venture-chat unreachable"] if open_titles is None else open_titles
    session = MagicMock()
    session.scalar = AsyncMock(return_value=1)
    session.scalars = AsyncMock(side_effect=lambda *_a, **_k: list(still_open))
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    desktop = DesktopNotifier(session_factory=lambda: session, clock=clock)
    return desktop, session, still_open


@contextmanager
def wired(*, config=None, watching: bool = False, dnd: bool = False):
    """The module-level collaborators the notifier reaches for."""
    settings = MagicMock()
    settings.notifications.desktop = config or DesktopNotificationsConfig()
    presence = TrayPresence()
    if watching:
        presence.mark_seen()

    with (
        patch("sysadmin.monitor.desktop.get_config", return_value=settings),
        patch("sysadmin.monitor.desktop.tray_presence", presence),
        patch("sysadmin.monitor.desktop.dnd_manager.should_suppress", return_value=dnd),
    ):
        yield


async def announce(desktop, *, title: str = None, severity: str = "critical", **kw):
    """Drive the raise path once, so the sweep has something to restate."""
    event = dict(RAISED, severity=severity)
    if title is not None:
        event["title"] = title
    with wired(**kw), patch.object(desktop, "send", new=AsyncMock(return_value=True)):
        await desktop.on_alert_raised(event)


class TestTheRepeatPath:
    """SNAG-TRAY-007: a fault that stands has to keep speaking.

    Gate 2 turns 186 rows into one notification, and then turns a
    week-long outage into one notification too. The tray grew a reminder
    in Session 53; this module is event-driven and had no moment at which
    it could notice a fault it announced six hours ago was still open.
    """

    async def test_a_fault_still_open_is_restated_after_the_interval(self):
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 1

        send.assert_awaited_once()
        assert send.await_args.args[1] == "venture-chat unreachable"
        assert "Still open 24 hours after the first alert" in send.await_args.args[2]

    async def test_before_the_interval_it_says_nothing(self):
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(23.9)
        with wired(), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()

    async def test_a_fault_that_cleared_is_dropped_and_never_restated(self):
        """The resolve is what stops a reminder, since nothing announces one."""
        clock = _Clock()
        desktop, _, still_open = sweeper(clock)
        await announce(desktop)

        still_open.clear()
        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()
        assert desktop._spoken == {}

    async def test_a_sweep_with_nothing_announced_issues_no_query(self):
        """Rule 1's whole point: the steady state costs one dict lookup."""
        clock = _Clock()
        desktop, session, _ = sweeper(clock)

        with wired():
            assert await desktop.sweep_reminders() == 0

        session.scalars.assert_not_awaited()

    async def test_a_fault_the_tray_announced_is_never_adopted(self):
        """The population is what *this process* said, not what is open."""
        clock = _Clock()
        desktop, _, still_open = sweeper(clock, ["something the tray spoke for"])

        clock.advance_hours(48)
        with wired(), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()

    async def test_a_watching_tray_resets_the_clock_rather_than_skipping(self):
        """Rule 2. A plain skip leaves ``last_spoken_at`` stale, so the

        first sweep after a tray outage restates a fault the tray itself
        restated ten minutes earlier.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(24)
        with wired(watching=True), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0
        send.assert_not_awaited()

        # The tray goes away. The fault is now 36 h old — which a *skip*
        # would have restated at once, having left the clock at the
        # opening notification — but only 12 h have passed since the tray
        # last spoke for it, so nothing is due.
        clock.advance_hours(12)
        with wired(), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0
        send.assert_not_awaited()

        clock.advance_hours(12)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 1
        send.assert_awaited_once()

    async def test_two_due_reminders_fold_into_one_taking_the_loudest(self):
        """Rule 3. ``notify-send`` has no replaces_id: six due = six toasts."""
        clock = _Clock()
        desktop, _, still_open = sweeper(clock, ["a warning", "a critical"])
        await announce(desktop, title="a warning", severity="warning")
        await announce(desktop, title="a critical", severity="critical")

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 2

        send.assert_awaited_once()
        severity, summary, body = send.await_args.args
        assert severity == "critical"
        assert summary == "2 faults still open"
        assert "• a warning" in body and "• a critical" in body

    async def test_a_roll_up_names_five_and_counts_the_rest(self):
        clock = _Clock()
        titles = [f"fault {i}" for i in range(7)]
        desktop, _, _ = sweeper(clock, titles)
        for title in titles:
            await announce(desktop, title=title, severity="warning")

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 7

        body = send.await_args.args[2]
        assert body.count("•") == 5
        assert "…and 2 more" in body

    async def test_a_reminder_that_did_not_land_stays_due(self):
        """Rule 4: the clock moves on what was said, not on what was tried."""
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=False)):
            assert await desktop.sweep_reminders() == 0

        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 1
        send.assert_awaited_once()

    async def test_an_opening_notification_that_did_not_land_is_not_recorded(self):
        """Nothing was said, so there is nothing to restate."""
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=False)):
            await desktop.on_alert_raised(dict(RAISED))

        assert desktop._spoken == {}

    async def test_dnd_holds_a_reminder_without_moving_the_clock(self):
        """A reminder is an interrupt, and 24 h later the window has moved."""
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(24)
        with wired(dnd=True), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0
        send.assert_not_awaited()

        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send:
            assert await desktop.sweep_reminders() == 1
        send.assert_awaited_once()

    async def test_a_raised_threshold_silences_a_reminder(self):
        """min_severity is re-read per sweep, not inherited from the raise."""
        clock = _Clock()
        desktop, _, _ = sweeper(clock, ["a warning"])
        await announce(desktop, title="a warning", severity="warning")

        clock.advance_hours(24)
        config = DesktopNotificationsConfig(min_severity="critical")
        with wired(config=config), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()

    async def test_zero_hours_disables_reminders(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(240)
        config = DesktopNotificationsConfig(reminder_hours=0)
        with wired(config=config), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()
        session.scalars.assert_not_awaited()


class TestTheSweepFailsClosed:
    async def test_an_unreadable_database_is_silence_not_a_storm(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)
        session.scalars = AsyncMock(side_effect=RuntimeError("connection reset"))

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()

    async def test_an_unreadable_database_does_not_drop_the_spoken_set(self):
        """Otherwise a blip is indistinguishable from a resolve."""
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)
        session.scalars = AsyncMock(side_effect=RuntimeError("connection reset"))

        clock.advance_hours(24)
        with wired():
            await desktop.sweep_reminders()

        assert "venture-chat unreachable" in desktop._spoken

    async def test_the_sweep_never_raises(self):
        """A scheduled job that throws is one APScheduler stops trusting."""
        clock = _Clock()
        desktop, _, _ = sweeper(clock)
        await announce(desktop)

        with (
            patch(
                "sysadmin.monitor.desktop.get_config",
                side_effect=RuntimeError("config gone"),
            ),
            patch.object(desktop, "send", new=AsyncMock()),
        ):
            assert await desktop.sweep_reminders() == 0


class TestTheSweepIsScheduled:
    def test_the_job_is_planned_and_wired(self):
        """Planned and unwired is a KeyError; wired and unplanned never runs."""
        from sysadmin.core.jobs import plan_jobs
        from sysadmin.main import JOB_TARGETS

        spec = next(
            s for s in plan_jobs(AppConfig()) if s.job_id == "desktop_reminder_sweep"
        )
        assert spec.trigger == "interval"
        assert JOB_TARGETS["desktop_reminder_sweep"].__name__ == "sweep_reminders"

    def test_the_interval_is_derived_from_the_grace_window(self):
        """Not a leaf of its own: the sweep asks the same question that

        window already answers, and a second number beside it would be
        invented rather than derived.
        """
        from sysadmin.core.jobs import plan_jobs

        config = AppConfig()
        config.notifications.desktop.tray_grace_seconds = 300
        spec = next(
            s for s in plan_jobs(config) if s.job_id == "desktop_reminder_sweep"
        )

        assert spec.trigger_kwargs == {"seconds": 300}

    def test_a_tiny_grace_window_cannot_make_a_hot_loop(self):
        from sysadmin.core.jobs import MIN_REMINDER_SWEEP_SECONDS, plan_jobs

        config = AppConfig()
        config.notifications.desktop.tray_grace_seconds = 5
        spec = next(
            s for s in plan_jobs(config) if s.job_id == "desktop_reminder_sweep"
        )

        assert spec.trigger_kwargs == {"seconds": MIN_REMINDER_SWEEP_SECONDS}

    def test_the_reminder_interval_matches_the_trays(self):
        """Two speakers with different cadences make the interval depend on

        which of them happened to be running — the thing the understudy
        exists to hide.
        """
        from sysadmin_tray.notifications import NotificationSettings

        assert (
            DesktopNotificationsConfig().reminder_hours
            == NotificationSettings().reminder_hours
        )
