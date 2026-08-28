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
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import Delete, Insert

from sysadmin.core.config import AppConfig, DesktopNotificationsConfig
from sysadmin.monitor.desktop import (
    MAX_ADOPTED_TITLES,
    DesktopNotifier,
    TrayPresence,
    session_bus_address,
)
from sysadmin.monitor.models.desktop_notification import DesktopNotification

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


def stored_row(
    title: str,
    *,
    severity: str = "critical",
    episode_started_at: float = 0.0,
    last_spoken_at: float = 0.0,
    reminders_sent: int = 0,
    adopted: bool = False,
) -> DesktopNotification:
    """One row as ``desktop_notifications`` would hand it back.

    The real model, not a namespace: twelve tests one module over
    (``test_log_aggregator``) built a ``SimpleNamespace`` stand-in for a
    config model and broke the day the reader read one more field, and
    the fix that made them pass would have swallowed a genuine wiring
    failure. Seconds in, ``datetime`` out — the notifier's clock is a
    wall clock now, so the conversion is the column's and not a delta.
    """
    return DesktopNotification(
        title=title,
        severity=severity,
        episode_started_at=datetime.fromtimestamp(episode_started_at, UTC),
        last_spoken_at=datetime.fromtimestamp(last_spoken_at, UTC),
        reminders_sent=reminders_sent,
        adopted=adopted,
    )


def _inserted_rows(stmt) -> list[dict]:
    """The rows a multi-VALUES insert carries, back out of its parameters.

    SQLAlchemy renders ``values([{...}, {...}])`` as ``title_m0``,
    ``title_m1`` … so the row index is the suffix. Read out rather than
    captured by patching :meth:`DesktopNotifier._remember`, because a
    test that patches the writer cannot witness *what* was written.
    """
    rows: dict[int, dict] = {}
    for key, value in stmt.compile().params.items():
        column, _, index = key.rpartition("_m")
        if not index.isdigit():
            continue
        rows.setdefault(int(index), {})[column] = value
    return [rows[i] for i in sorted(rows)]


class _FakeSession:
    """A session that answers by *statement*, not by call order.

    The stand-in this replaced answered every ``scalars()`` with the open
    titles, which was true while the sweep asked exactly one question.
    Since ``SNAG-TRAY-008`` it asks three — which of my faults are still
    open, what did the last process say, and what is standing that I
    never announced — and a fake that cannot tell them apart reports the
    fix as broken rather than reporting the code. Session 110 paid for
    this exact lesson in four stand-ins at once: model the database, not
    the one call site.
    """

    def __init__(self, still_open, stored, adoptable):
        self.still_open = still_open
        self.stored = stored
        #: ``(title, opened_at_seconds, [severity, ...])`` — what a
        #: ``GROUP BY title`` over the open rows would yield.
        self.adoptable = adoptable
        self.written: list[dict] = []
        self.deleted: list[str] = []
        self.queries: list[str] = []
        #: The table as the upsert leaves it, keyed on title.
        self.rows: dict[str, dict] = {}
        #: The rendered upsert. A fake applies its *own* replace-the-row
        #: semantics, so which columns the real ``ON CONFLICT`` actually
        #: updates is a question only the statement can answer.
        self.insert_sql: list[str] = []

    # the two context-manager halves ``async with factory()`` needs
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def scalar(self, _stmt, *_a, **_k):
        self.queries.append("incident_count")
        return 1

    async def scalars(self, stmt, *_a, **_k):
        if stmt.column_descriptions[0]["entity"] is DesktopNotification:
            self.queries.append("load")
            return list(self.stored)
        self.queries.append("still_open")
        return list(self.still_open)

    async def execute(self, stmt, *_a, **_k):
        if isinstance(stmt, Delete):
            self.queries.append("forget")
            for value in stmt.compile().params.values():
                self.deleted.extend(value if isinstance(value, list) else [value])
            for title in self.deleted:
                self.rows.pop(title, None)
            return MagicMock()
        if isinstance(stmt, Insert):
            self.queries.append("remember")
            self.insert_sql.append(
                str(stmt.compile(dialect=postgresql.dialect()))
            )
            for row in _inserted_rows(stmt):
                self.written.append(row)
                # The real statement is an upsert on ``title``; a fake
                # that appended without replacing would let a test assert
                # a stale row is still there and pass.
                self.rows[row["title"]] = row
            return MagicMock()
        self.queries.append("adopt")
        # The cap and the exclusion are enforced **in SQL**, so a fake
        # that returned everything it was holding would report an
        # uncapped adoption as capped — or, worse here, the reverse. Both
        # are read back off the compiled statement rather than
        # reimplemented from the caller's arguments.
        params = stmt.compile().params
        excluded = set(params.get("title_1") or ())
        admitted = set(params.get("severity_1") or ())
        limit = params.get("param_1")
        offered = [
            (title, datetime.fromtimestamp(opened, UTC), rungs)
            for title, opened, rungs in self.adoptable
            if title not in excluded and (not admitted or set(rungs) & admitted)
        ]
        offered.sort(key=lambda row: row[1])
        result = MagicMock()
        result.all = MagicMock(
            return_value=offered if limit is None else offered[:limit]
        )
        return result

    async def commit(self):
        return None


def sweeper(
    clock: _Clock,
    open_titles: list[str] | None = None,
    *,
    stored: list[DesktopNotification] | None = None,
    adoptable: list[tuple[str, float, list[str]]] | None = None,
):
    """A notifier whose gate-2 query says "new" and whose sweep sees *open_titles*.

    The list is returned so a test can close a fault by emptying it —
    which is the only way ``_spoken`` is ever pruned.

    ``stored`` is what a previous instance left in
    ``desktop_notifications``; ``adoptable`` is what a ``GROUP BY title``
    over the open alerts would offer the adoption scan.
    """
    still_open = ["venture-chat unreachable"] if open_titles is None else open_titles
    session = _FakeSession(still_open, stored or [], adoptable or [])
    desktop = DesktopNotifier(session_factory=lambda: session, clock=clock)
    return desktop, session, still_open


@contextmanager
def wired(
    *,
    config=None,
    watching: bool = False,
    dnd: bool = False,
    absent_hours: float | None = None,
):
    """The module-level collaborators the notifier reaches for.

    ``absent_hours`` supplies :meth:`TrayPresence.seconds_since_seen` —
    one leaf, so ``is_watching`` and ``absent_for`` above it stay the
    module's own and still read the live ``tray_grace_seconds``. A test
    cannot otherwise build a tray that left thirty hours ago without
    sleeping for thirty hours, and a plain never-marked presence reports
    an absence of *this process's uptime*, which is milliseconds.
    """
    settings = MagicMock()
    settings.notifications.desktop = config or DesktopNotificationsConfig()
    presence = TrayPresence()
    if watching:
        presence.mark_seen()
    if absent_hours is not None:
        presence.mark_seen()
        presence.seconds_since_seen = lambda: absent_hours * 3600

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

    async def test_the_steady_state_costs_one_query_per_process(self):
        """What rule 1's "no query at all" became when the set went durable.

        It cannot survive persistence: not knowing what the last process
        said is indistinguishable from it having said nothing, which is
        ``SNAG-TRAY-008``. So the bound moved from *per sweep* to *per
        process* — and on a box where the tray runs, the gate after the
        load returns before anything else is read.
        """
        clock = _Clock()
        desktop, session, _ = sweeper(clock)

        for _ in range(4):
            with wired(watching=True):
                assert await desktop.sweep_reminders() == 0

        assert session.queries == ["load"]

    async def test_a_fault_the_tray_announced_is_adopted_once_nobody_is_watching(self):
        """This assertion used to be its own opposite, and passed for years.

        ``test_a_fault_the_tray_announced_is_never_adopted`` pinned
        ``SNAG-TRAY-008``'s first face as correct behaviour — the
        population is what *this process* said — which is exactly the
        cost that entry was filed to record. Rule 6 moved it, so the test
        is inverted rather than deleted: the fault the tray spoke for is
        now carried when the tray is gone.
        """
        title = "something the tray spoke for"
        clock = _Clock()
        desktop, session, _ = sweeper(
            clock, [title], adoptable=[(title, clock.now - 3600, ["critical"])]
        )

        clock.advance_hours(48)
        with (
            wired(absent_hours=48),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            assert await desktop.sweep_reminders() == 1

        send.assert_awaited_once()
        assert send.await_args.args[1] == title
        assert desktop._spoken[title].adopted is True
        assert session.rows[title]["adopted"] is True

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
        before = len(session.queries)
        config = DesktopNotificationsConfig(reminder_hours=0)
        with wired(config=config), patch.object(desktop, "send", new=AsyncMock()) as send:
            assert await desktop.sweep_reminders() == 0

        send.assert_not_awaited()
        # Not even the load: a disabled interval is answered from config
        # before the store is reached.
        assert session.queries[before:] == []


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


class TestTheSpokenSetSurvivesARestart:
    """``SNAG-TRAY-008``, face 2 — and the number that makes it P1-shaped.

    The reminder interval is 24 hours and the population of the sweep was
    the keys of an in-memory dict, so a reminder needed a process that
    lived a day. Measured over 28.26 days, ``sysadmin.service`` started
    **111 times** at a median uptime of **1.77 h**, and **5 of 110** lives
    reached 24 hours — so ``SNAG-TRAY-007``'s fix was unavailable on 95 %
    of this daemon's lives. Not a slow reminder: silence.
    """

    async def test_an_announcement_is_written_down(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)

        assert session.rows["venture-chat unreachable"]["severity"] == "critical"
        assert session.rows["venture-chat unreachable"]["adopted"] is False

    async def test_a_restart_restores_what_the_previous_instance_said(self):
        """The whole entry's second face, in one assertion.

        The notifier is *new* — nothing announced, nothing in memory —
        and the fault is one only a dead process ever spoke for.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["venture-chat unreachable"],
            stored=[stored_row("venture-chat unreachable", last_spoken_at=clock.now)],
        )

        clock.advance_hours(24)
        with (
            wired(absent_hours=30),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            assert await desktop.sweep_reminders() == 1

        assert send.await_args.args[1] == "venture-chat unreachable"

    async def test_the_restored_clock_is_the_stored_one_not_this_process_start(self):
        """Or a restart would silently grant every fault a fresh interval.

        This is the failure a naive restore has and a green suite would
        not see: the fault *is* restored, it simply never comes due,
        which on a 1.77-hour daemon is the defect unchanged.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["venture-chat unreachable"],
            stored=[
                stored_row("venture-chat unreachable", last_spoken_at=clock.now - 1)
            ],
        )

        clock.advance_hours(0.5)
        with (
            wired(absent_hours=30),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            assert await desktop.sweep_reminders() == 0
        send.assert_not_awaited()

        assert desktop._spoken["venture-chat unreachable"].last_spoken_at == 999.0

    async def test_the_store_is_read_once_per_process(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)

        for _ in range(3):
            with wired(), patch.object(desktop, "send", new=AsyncMock()):
                await desktop.sweep_reminders()

        assert session.queries.count("load") == 1

    async def test_this_instance_beats_the_stored_row_for_the_same_title(self):
        """``on_alert_raised`` can fire before the first sweep.

        What it recorded is newer than anything a dead process wrote, so
        the load fills gaps and never overwrites.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            stored=[
                stored_row(
                    "venture-chat unreachable", severity="info", reminders_sent=9
                )
            ],
        )
        await announce(desktop)

        with wired(watching=True):
            await desktop.sweep_reminders()

        fault = desktop._spoken["venture-chat unreachable"]
        assert fault.severity == "critical"
        assert fault.reminders_sent == 0

    async def test_an_unreadable_store_is_retried_rather_than_given_up_on(self):
        clock = _Clock()
        desktop, session, _ = sweeper(
            clock, stored=[stored_row("a standing fault", last_spoken_at=clock.now)]
        )
        broken = AsyncMock(side_effect=RuntimeError("connection reset"))
        working = session.scalars
        session.scalars = broken

        with wired(), patch.object(desktop, "send", new=AsyncMock()):
            assert await desktop.sweep_reminders() == 0
        assert desktop._spoken == {}

        session.scalars = working
        with wired(watching=True):
            await desktop.sweep_reminders()
        assert "a standing fault" in desktop._spoken

    async def test_a_row_this_code_cannot_read_costs_one_sweep_not_the_sweep(self):
        """The mapping loop is inside the guard, which it was not at first.

        Outside it, the first surprising row takes down the whole sweep —
        including reminders for faults it had read perfectly well.
        """
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)
        session.stored = ["not a row at all"]

        clock.advance_hours(24)
        with (
            wired(),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            assert await desktop.sweep_reminders() == 1
        send.assert_awaited_once()

    async def test_a_watching_tray_moves_the_clock_and_writes_nothing(self):
        """Rule 5: the store records what was *said*.

        A watching tray is a belief about another process, so the
        stamp-forward stays in memory — which bounds writes at one per
        notification. The stale restored stamp it leaves cannot act,
        because this same gate corrects it within one grace window.
        """
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)
        writes = session.queries.count("remember")

        clock.advance_hours(24)
        with wired(watching=True):
            assert await desktop.sweep_reminders() == 0

        assert session.queries.count("remember") == writes
        assert desktop._spoken["venture-chat unreachable"].last_spoken_at == clock.now

    async def test_a_cleared_fault_leaves_the_store(self):
        clock = _Clock()
        desktop, session, still_open = sweeper(clock)
        await announce(desktop)

        still_open.clear()
        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock()):
            await desktop.sweep_reminders()

        assert session.deleted == ["venture-chat unreachable"]
        assert session.rows == {}

    async def test_a_reminder_moves_the_stored_clock(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)):
            assert await desktop.sweep_reminders() == 1

        row = session.rows["venture-chat unreachable"]
        assert row["last_spoken_at"] == datetime.fromtimestamp(clock.now, UTC)
        assert row["reminders_sent"] == 1

    def test_the_clock_is_a_wall_clock_and_the_tray_gate_is_not(self):
        """They differ on purpose, and the difference is the whole of rule 5.

        No monotonic value survives a process — nor a suspend, which a
        24-hour interval about elapsed human time should count. The
        180-second tray question wants the opposite reading and keeps it.
        """
        import time

        assert DesktopNotifier()._clock is time.time
        assert TrayPresence()._started_at <= time.monotonic()


class TestAdoption:
    """``SNAG-TRAY-008``, face 1 — a standing fault nobody announced.

    The entry calls this *"a scoping question rather than a persistence
    one"* and warns that fixing the other half leaves this one looking
    fixed.
    """

    async def test_the_entrys_gate_is_an_anchor_so_a_fresh_absence_is_quiet(self):
        """Quiet by construction when the tray has only just left."""
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now - 7200, ["warning"])],
        )

        with (
            wired(absent_hours=0.2),
            patch.object(desktop, "send", new=AsyncMock()) as send,
        ):
            assert await desktop.sweep_reminders() == 0
        send.assert_not_awaited()
        assert desktop._spoken["a standing fault"].adopted is True

    async def test_a_full_interval_of_silence_speaks_at_once(self):
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now - 7200, ["warning"])],
        )

        with (
            wired(absent_hours=25),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            assert await desktop.sweep_reminders() == 1
        send.assert_awaited_once()

    async def test_a_long_silence_is_capped_at_one_interval(self):
        """A fault open since March must not arrive as a backlog.

        Observable only through the clock it leaves behind: both a
        30-hour and a 300-hour absence speak once, and the difference is
        whether the *next* reminder is due immediately.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now - 7200, ["warning"])],
        )

        with wired(absent_hours=300), patch.object(
            desktop, "send", new=AsyncMock(return_value=True)
        ):
            await desktop.sweep_reminders()

        fault = desktop._spoken["a standing fault"]
        assert fault.last_spoken_at == clock.now

    async def test_nothing_is_adopted_while_the_tray_is_watching(self):
        clock = _Clock()
        desktop, session, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now, ["critical"])],
        )

        with wired(watching=True), patch.object(desktop, "send", new=AsyncMock()):
            assert await desktop.sweep_reminders() == 0

        assert "adopt" not in session.queries
        assert desktop._spoken == {}

    async def test_adoption_waits_for_the_store_to_answer(self):
        """Adopting against a spoken set known to be incomplete would

        re-announce a fault this daemon is already carrying.
        """
        clock = _Clock()
        desktop, session, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now, ["critical"])],
        )
        session.scalars = AsyncMock(side_effect=RuntimeError("connection reset"))

        with wired(absent_hours=30), patch.object(desktop, "send", new=AsyncMock()):
            assert await desktop.sweep_reminders() == 0

        assert "adopt" not in session.queries

    async def test_the_adopted_population_is_capped_across_sweeps(self):
        """Per-sweep would be no cap at all at a 180-second cadence."""
        clock = _Clock()
        offered = [(f"fault {i}", clock.now, ["warning"]) for i in range(12)]
        desktop, _, _ = sweeper(
            clock, [title for title, _, _ in offered], adoptable=offered
        )

        for _ in range(4):
            with wired(absent_hours=0.2), patch.object(
                desktop, "send", new=AsyncMock(return_value=True)
            ):
                await desktop.sweep_reminders()

        adopted = [f for f in desktop._spoken.values() if f.adopted]
        assert len(adopted) == MAX_ADOPTED_TITLES

    async def test_the_cap_survives_a_restart(self):
        """Or a 1.77-hour daemon adopts the whole open set five at a time."""
        clock = _Clock()
        offered = [(f"fault {i}", clock.now, ["warning"]) for i in range(12)]
        desktop, _, _ = sweeper(
            clock,
            [title for title, _, _ in offered],
            stored=[
                stored_row(f"old {i}", adopted=True, last_spoken_at=clock.now)
                for i in range(MAX_ADOPTED_TITLES)
            ],
            adoptable=offered,
        )

        with wired(absent_hours=0.2), patch.object(desktop, "send", new=AsyncMock()):
            await desktop.sweep_reminders()

        assert [f for f in desktop._spoken.values() if not f.adopted] == []
        assert len(desktop._spoken) == MAX_ADOPTED_TITLES

    async def test_an_announced_fault_is_not_bounded_by_the_adoption_cap(self):
        clock = _Clock()
        titles = [f"announced {i}" for i in range(MAX_ADOPTED_TITLES + 3)]
        desktop, _, _ = sweeper(clock, titles)
        for title in titles:
            await announce(desktop, title=title)

        assert len(desktop._spoken) == len(titles)

    async def test_a_fault_this_daemon_announced_is_not_adopted_underneath_it(self):
        """The exclusion is in SQL, and without it the cap is wrong too.

        A re-adopted announcement would have its clock reset to the
        anchor, lose its ``reminders_sent``, and consume one of the five
        adoption slots — so the bound on adoption would be quietly spent
        on faults that were never adopted.
        """
        clock = _Clock()
        title = "venture-chat unreachable"
        desktop, session, _ = sweeper(
            clock, [title], adoptable=[(title, clock.now - 7200, ["critical"])]
        )
        await announce(desktop)

        with wired(absent_hours=25), patch.object(desktop, "send", new=AsyncMock()):
            await desktop.sweep_reminders()

        assert desktop._spoken[title].adopted is False
        assert [f for f in desktop._spoken.values() if f.adopted] == []

    async def test_an_adopted_faults_age_comes_from_the_alert_row(self):
        """It has no first-*spoken* moment, so the row's own opening is used.

        Which is better evidence than the announced path has, and is why
        the field is ``episode_started_at`` rather than
        ``first_spoken_at``.
        """
        clock = _Clock()
        opened = clock.now - 3 * 3600
        desktop, _, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", opened, ["warning"])],
        )

        with (
            wired(absent_hours=25),
            patch.object(desktop, "send", new=AsyncMock(return_value=True)) as send,
        ):
            await desktop.sweep_reminders()

        assert "Still open 3 hours after the first alert" in send.await_args.args[2]

    @pytest.mark.parametrize("rungs", [["warning", "critical"], ["critical", "warning"]])
    async def test_a_title_carrying_two_rungs_is_adopted_at_the_louder(self, rungs):
        """Both orders, because only arrival order can witness this.

        ``array_agg`` gives no ordering guarantee, so taking ``rungs[0]``
        is the plausible wrong implementation and this is what catches
        it. What it cannot catch is honest to state: among the two rungs
        ``min_severity`` admits here, alphabetical order and loudness
        agree, so a sort would pass. :func:`_loudest` is pinned against
        ``SEVERITY_LEVELS`` by its own tests.
        """
        clock = _Clock()
        desktop, _, _ = sweeper(
            clock,
            ["a standing fault"],
            adoptable=[("a standing fault", clock.now, rungs)],
        )

        with wired(absent_hours=25), patch.object(
            desktop, "send", new=AsyncMock(return_value=True)
        ):
            await desktop.sweep_reminders()

        assert desktop._spoken["a standing fault"].severity == "critical"

    async def test_the_cap_is_derived_from_what_a_roll_up_can_name(self):
        """Session 46: a count is not news, so an unnameable adoption is not

        an adoption worth making.
        """
        from sysadmin.monitor import desktop as module

        assert MAX_ADOPTED_TITLES == module._MAX_LISTED_TITLES


class TestTrayAbsence:
    """``absent_for`` is a floor, and the two readings differ on purpose."""

    def test_a_poll_that_happened_is_the_answer(self):
        presence = TrayPresence()
        presence.mark_seen()
        presence.seconds_since_seen = lambda: 4242.0
        assert presence.absent_for() == 4242.0

    def test_never_having_seen_one_falls_back_to_process_uptime(self):
        """An under-count, deliberately: the tray may have been away for a

        week before this process started, and delaying an adoption's
        first reminder is the safe direction.

        The uptime is **forced**, because the honest-looking assertion —
        ``0 <= absent_for() < 60`` on a fresh object — is satisfied by a
        method that returns zero, and a witness a broken implementation
        also produces is not a witness.
        """
        import time

        presence = TrayPresence()
        assert presence.seconds_since_seen() is None
        presence._started_at = time.monotonic() - 5000.0
        assert presence.absent_for() >= 5000.0


class TestTheUpsert:
    """What ``ON CONFLICT`` updates, which a fake cannot witness.

    ``_FakeSession`` replaces the whole row on conflict — that is what a
    correct upsert does, so it agrees with a broken ``set_`` clause that
    keeps the existing value, and every behavioural assertion above is
    blind to it. Two mutations proved it: mapping ``reminders_sent`` and
    ``severity`` to the column instead of ``excluded`` left all 84 tests
    green while a reminder count froze at its first value for ever.
    """

    async def test_every_mutable_column_is_taken_from_the_excluded_row(self):
        clock = _Clock()
        desktop, session, _ = sweeper(clock)
        await announce(desktop)

        sql = session.insert_sql[0].lower()
        assert "on conflict (title) do update" in sql
        for column in (
            "severity",
            "episode_started_at",
            "last_spoken_at",
            "reminders_sent",
            "adopted",
        ):
            assert f"{column} = excluded.{column}" in sql, column
        # The identity is the conflict target and must never be an
        # assignment: a title that "updated" itself would be the one
        # column an upsert has no business touching.
        assert "title = excluded.title" not in sql

    async def test_a_roll_up_writes_every_fault_it_swallowed(self):
        """The fold has its own ``_remember`` call and had no witness.

        Removing it left 84 tests green while every reminder delivered as
        part of a roll-up — which is the common case, since the fold
        threshold is two — failed to move its stored clock.
        """
        clock = _Clock()
        desktop, session, _ = sweeper(clock, ["a warning", "a critical"])
        await announce(desktop, title="a warning", severity="warning")
        await announce(desktop, title="a critical", severity="critical")

        clock.advance_hours(24)
        with wired(), patch.object(desktop, "send", new=AsyncMock(return_value=True)):
            assert await desktop.sweep_reminders() == 2

        for title in ("a warning", "a critical"):
            row = session.rows[title]
            assert row["last_spoken_at"] == datetime.fromtimestamp(clock.now, UTC)
            assert row["reminders_sent"] == 1


class TestTheSessionIsSchedulerSafe:
    """Every read here happens on a loop that is not the application's.

    The sweep is an APScheduler job and ``scheduler._run_async`` gives
    each firing its own ``asyncio.run``; ``on_alert_raised`` is published
    from inside an agent's run, which is another one. A pooled
    connection belongs to the loop that opened it, so the app engine
    raises ``RuntimeError: got Future … attached to a different loop``
    and asyncpg follows with ``InternalClientError``.

    **This was already wrong and nothing could reach it.**
    ``_still_open`` resolved the pooled factory from Session 55 until
    2026-08-28 and never once succeeded on this box, because the sweep's
    old first gate returned before any query. It was found by deploying
    the store — whose load is the first call past that gate — and
    reading three `Log error: sysadmin.service` rows out of the live
    table, not by reading the code.
    """

    def test_the_uninjected_factory_is_the_scheduler_safe_one(self):
        from sysadmin.core.database import get_scheduler_session

        assert DesktopNotifier()._factory() is get_scheduler_session

    def test_no_reader_here_reaches_the_pooled_factory(self):
        """An AST sweep, because the name is what a future edit would use.

        ``get_session_factory`` is correct everywhere a request handler
        runs and wrong everywhere in this module, and the failure mode is
        a caught exception in a log line rather than a red test.
        """
        import ast
        import pathlib

        source = pathlib.Path("sysadmin/monitor/desktop.py").read_text()
        names = {
            node.id
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Name)
        } | {
            alias.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "get_session_factory" not in names
