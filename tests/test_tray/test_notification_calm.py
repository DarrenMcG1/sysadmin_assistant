"""Session 16 — notification calm.

Covers the ``NotificationPolicy`` state machine (flap cooldown, coalescing,
progressive escalation, snooze/mute, warning digest, DND interaction) and
the ``DbusNotifier`` transport behaviour that needs asserting on the CALLS:
``replaces_id`` reuse, urgency levels, the ``transient`` hint and the
action buttons.

Nothing here touches a live session bus: ``DbusNotifier._send`` is the seam
between the pure payload construction and the Qt marshalling, so tests
patch it and inspect the ``NotifyPayload`` objects.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from sysadmin_tray.models import AlertInfo, AlertsResponse
from sysadmin_tray.notifications import (
    FP_COALESCED,
    FP_DIGEST,
    DbusNotifier,
    NotificationPolicy,
    NotificationSettings,
)
from sysadmin_tray.tray_icon import TrayIcon


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class FakeClock:
    """Monotonic-style clock the tests can wind forward."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now += minutes * 60


def _alert(
    severity: str = "critical",
    title: str = "Disk full",
    *,
    aid: str = "a1",
    service: str | None = None,
    message: str | None = None,
) -> AlertInfo:
    details = {"service_name": service} if service else None
    return AlertInfo(
        id=aid, severity=severity, title=title,
        message=message, details=details,
    )


def _alerts(*items: AlertInfo) -> AlertsResponse:
    return AlertsResponse(alerts=list(items), count=len(items))


def _policy(clock: FakeClock, **settings) -> NotificationPolicy:
    """Policy with a warning threshold (so most fixtures are audible)."""
    settings.setdefault("min_severity", "warning")
    return NotificationPolicy(NotificationSettings(**settings), clock=clock)


def _make_notifier(fallback=None, snooze_minutes: int = 60):
    """A DbusNotifier that believes D-Bus is available, with _send patched.

    Returns ``(notifier, iface_mock, sent_payloads)``.  Notification ids
    start at 101 and increment, so tests can assert on replaces_id reuse.
    """
    with patch("sysadmin_tray.notifications.QDBusConnection") as conn_cls, patch(
        "sysadmin_tray.notifications.QDBusInterface"
    ) as iface_cls:
        bus = MagicMock()
        bus.isConnected.return_value = True
        conn_cls.sessionBus.return_value = bus

        iface = MagicMock()
        iface.isValid.return_value = True
        iface_cls.return_value = iface

        notifier = DbusNotifier(
            fallback_tray=fallback, snooze_minutes=snooze_minutes,
        )

    payloads: list = []
    ids = iter(range(101, 400))

    def fake_send(payload):
        payloads.append(payload)
        return next(ids)

    notifier._send = fake_send  # type: ignore[method-assign]
    return notifier, iface, payloads


# ── 1. Update-in-place (replaces_id) ─────────────────────────────────


class TestUpdateInPlace:
    """The D-Bus id per fingerprint is reused as replaces_id."""

    def test_first_notification_replaces_nothing(self, qapp):
        notifier, _iface, payloads = _make_notifier()
        notifier.notify("CRITICAL: sysadmin", "Disk full", "critical",
                        fingerprint="critical:Disk full")
        assert payloads[0].replaces_id == 0

    def test_same_fingerprint_replaces_previous_popup(self, qapp):
        notifier, _iface, payloads = _make_notifier()
        notifier.notify("A", "b", "critical", fingerprint="critical:Disk full")
        notifier.notify("A", "worse", "critical", fingerprint="critical:Disk full")

        assert payloads[0].replaces_id == 0
        assert payloads[1].replaces_id == 101  # the id returned for the first

    def test_different_fingerprints_do_not_share_ids(self, qapp):
        notifier, _iface, payloads = _make_notifier()
        notifier.notify("A", "b", "warning", fingerprint="warning:RAM high")
        notifier.notify("B", "b", "warning", fingerprint="warning:CPU high")
        notifier.notify("A", "b", "warning", fingerprint="warning:RAM high")

        assert [p.replaces_id for p in payloads] == [0, 0, 101]

    def test_no_fingerprint_never_replaces(self, qapp):
        notifier, _iface, payloads = _make_notifier()
        notifier.notify("A", "b", "info")
        notifier.notify("A", "b", "info")
        assert [p.replaces_id for p in payloads] == [0, 0]

    def test_dismissed_notification_keeps_stale_id(self, qapp):
        """A dismissed popup leaves the mapping — a stale id is harmless."""
        notifier, _iface, payloads = _make_notifier()
        notifier.notify("A", "b", "critical", fingerprint="fp")
        notifier._on_notification_closed(101, 2)  # user dismissed
        notifier.notify("A", "b", "critical", fingerprint="fp")
        assert payloads[1].replaces_id == 101

    def test_fallback_path_records_no_id(self, qapp):
        """When D-Bus is unavailable nothing is tracked for replacement."""
        fallback = MagicMock(spec=QSystemTrayIcon)
        with patch("sysadmin_tray.notifications.QDBusConnection") as conn_cls:
            bus = MagicMock()
            bus.isConnected.return_value = False
            conn_cls.sessionBus.return_value = bus
            notifier = DbusNotifier(fallback_tray=fallback)

        assert notifier.notify("A", "b", "critical", fingerprint="fp") is False
        assert notifier._fp_ids == {}

    def test_cleanup_clears_fingerprint_ids(self, qapp):
        notifier, _iface, _payloads = _make_notifier()
        notifier.notify("A", "b", "critical", fingerprint="fp")
        assert notifier._fp_ids
        notifier.cleanup()
        assert notifier._fp_ids == {}


# ── Payload shape: urgency, transient, action buttons ────────────────


class TestPayloadHints:
    """Urgency levels, the transient hint and timeouts."""

    @pytest.mark.parametrize(
        ("severity", "urgency"), [("info", 0), ("warning", 1), ("critical", 2)],
    )
    def test_urgency_map(self, qapp, severity, urgency):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload("s", "b", severity)
        assert payload.hints["urgency"] == urgency

    def test_transient_hint_present_when_requested(self, qapp):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload("s", "b", "info", transient=True)
        assert payload.hints["transient"] is True

    def test_transient_hint_absent_by_default(self, qapp):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload("s", "b", "critical")
        assert "transient" not in payload.hints

    def test_critical_is_persistent(self, qapp):
        notifier, _iface, _p = _make_notifier()
        assert notifier.build_payload("s", "b", "critical").timeout == 0

    def test_service_action_toast_is_transient(self, qapp):
        """on_service_action_complete marks its feedback toast transient."""
        tray = TrayIcon()
        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        tray.on_service_action_complete("redis", "restart", True, "ok")

        assert notifier.notify.call_args.kwargs["transient"] is True

    def test_quiet_first_critical_is_transient(self, qapp):
        """The opening (quiet) critical skips history; the escalation doesn't."""
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=2)
        alerts = _alerts(_alert("critical", "Disk full"))

        first = policy.evaluate(alerts)[0]
        assert first.severity == "info"
        assert first.transient is True

        second = policy.evaluate(alerts)[0]
        assert second.severity == "critical"
        assert second.transient is False


class TestActionButtons:
    """Restart / Snooze buttons and the signals they raise."""

    def test_restart_button_only(self, qapp):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload("s", "b", "critical", service_name="redis")
        assert payload.actions == ("restart", "Restart")

    def test_snooze_button_added(self, qapp):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload(
            "s", "b", "critical", service_name="redis", snooze_key="service:redis",
        )
        assert payload.actions == ("restart", "Restart", "snooze", "Snooze 1h")

    def test_snooze_button_without_service(self, qapp):
        notifier, _iface, _p = _make_notifier()
        payload = notifier.build_payload(
            "s", "b", "warning", snooze_key="fp:warning:RAM high",
        )
        assert payload.actions == ("snooze", "Snooze 1h")

    def test_snooze_label_follows_config(self, qapp):
        notifier, _iface, _p = _make_notifier(snooze_minutes=90)
        assert notifier.snooze_label() == "Snooze 90m"
        notifier.snooze_minutes = 120
        assert notifier.snooze_label() == "Snooze 2h"

    def test_snooze_action_emits_signal(self, qapp):
        notifier, _iface, _p = _make_notifier()
        handler = MagicMock()
        notifier.snooze_requested.connect(handler)

        notifier.notify(
            "s", "b", "critical",
            service_name="redis", snooze_key="service:redis",
        )
        notifier._on_action_invoked(101, "snooze")

        handler.assert_called_once_with("service:redis")

    def test_restart_action_still_emits_restart(self, qapp):
        notifier, _iface, _p = _make_notifier()
        restart, snooze = MagicMock(), MagicMock()
        notifier.restart_requested.connect(restart)
        notifier.snooze_requested.connect(snooze)

        notifier.notify(
            "s", "b", "critical",
            service_name="redis", snooze_key="service:redis",
        )
        notifier._on_action_invoked(101, "restart")

        restart.assert_called_once_with("redis")
        snooze.assert_not_called()

    def test_notification_closed_clears_snooze_action(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier.notify("s", "b", "warning", snooze_key="fp:x")
        notifier._on_notification_closed(101, 2)
        assert notifier._pending_snoozes == {}


# ── 2. Flap cooldown ─────────────────────────────────────────────────


class TestFlapCooldown:
    """A fingerprint that re-fires inside the window doesn't interrupt."""

    def test_recurrence_within_cooldown_is_silent(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=30)
        alerts = _alerts(_alert("warning", "RAM high"))

        assert len(policy.evaluate(alerts)) == 1
        policy.evaluate(_alerts())          # resolved
        clock.advance(5)
        assert policy.evaluate(alerts) == []  # flapped back

    def test_repeats_roll_into_one_summary_after_cooldown(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=30)
        alerts = _alerts(_alert("warning", "RAM high"))

        policy.evaluate(alerts)
        for _ in range(3):                  # three suppressed flaps
            policy.evaluate(_alerts())
            clock.advance(5)
            assert policy.evaluate(alerts) == []

        policy.evaluate(_alerts())
        clock.advance(20)                   # cooldown now expired
        requests = policy.evaluate(alerts)

        assert len(requests) == 1
        assert "flapped 4×" in requests[0].body
        assert "in the last" in requests[0].body

    def test_flap_counter_resets_after_summary(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=10)
        alerts = _alerts(_alert("warning", "RAM high"))

        policy.evaluate(alerts)
        policy.evaluate(_alerts())
        clock.advance(2)
        policy.evaluate(alerts)             # suppressed
        policy.evaluate(_alerts())
        clock.advance(15)
        assert "flapped 2×" in policy.evaluate(alerts)[0].body

        policy.evaluate(_alerts())
        clock.advance(15)
        assert "flapped" not in policy.evaluate(alerts)[0].body

    def test_cooldown_is_per_fingerprint(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=30)

        policy.evaluate(_alerts(_alert("warning", "RAM high")))
        requests = policy.evaluate(
            _alerts(_alert("warning", "RAM high"), _alert("warning", "CPU high"))
        )
        assert len(requests) == 1
        assert "CPU high" in requests[0].body

    def test_zero_cooldown_restores_immediate_renotify(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=0)
        alerts = _alerts(_alert("warning", "RAM high"))

        policy.evaluate(alerts)
        policy.evaluate(_alerts())
        assert len(policy.evaluate(alerts)) == 1

    def test_ongoing_alert_never_repeats(self):
        """A continuously active alert only speaks once per episode."""
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=0)
        alerts = _alerts(_alert("warning", "RAM high"))

        assert len(policy.evaluate(alerts)) == 1
        for _ in range(5):
            clock.advance(10)
            assert policy.evaluate(alerts) == []

    def test_suppressed_episode_speaks_once_cooldown_expires(self):
        """An alert that stays up through the cooldown isn't muted forever."""
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=30)
        alerts = _alerts(_alert("warning", "RAM high"))

        policy.evaluate(alerts)
        policy.evaluate(_alerts())
        clock.advance(1)
        assert policy.evaluate(alerts) == []   # suppressed, stays active
        clock.advance(35)
        assert len(policy.evaluate(alerts)) == 1


# ── 3. Coalescing ────────────────────────────────────────────────────


class TestCoalescing:
    """Several new alerts in one poll become one summary."""

    def test_multiple_new_alerts_produce_one_summary(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(_alerts(
            _alert("critical", "Disk full", aid="a1"),
            _alert("warning", "RAM high", aid="a2"),
            _alert("warning", "CPU high", aid="a3"),
        ))

        assert len(requests) == 1
        request = requests[0]
        assert request.summary == "3 new alerts"
        assert request.body.splitlines()[0] == "1 critical, 2 warning"
        assert request.fingerprint == FP_COALESCED
        for title in ("Disk full", "RAM high", "CPU high"):
            assert title in request.body

    def test_single_new_alert_keeps_detail(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(
            _alerts(_alert("warning", "RAM high", message="Usage at 92%"))
        )
        assert len(requests) == 1
        assert requests[0].summary == "WARNING: sysadmin"
        assert "Usage at 92%" in requests[0].body

    def test_threshold_configurable(self):
        policy = _policy(FakeClock(), coalesce_threshold=3)
        requests = policy.evaluate(_alerts(
            _alert("warning", "RAM high", aid="a1"),
            _alert("warning", "CPU high", aid="a2"),
        ))
        assert len(requests) == 2

    def test_only_new_alerts_are_coalesced(self):
        """An alert already announced doesn't drag the next one into a summary."""
        policy = _policy(FakeClock())
        policy.evaluate(_alerts(_alert("warning", "RAM high", aid="a1")))
        requests = policy.evaluate(_alerts(
            _alert("warning", "RAM high", aid="a1"),
            _alert("warning", "CPU high", aid="a2"),
        ))
        assert len(requests) == 1
        assert requests[0].summary == "WARNING: sysadmin"
        assert "CPU high" in requests[0].body

    def test_long_batches_are_truncated(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(_alerts(*[
            _alert("warning", f"Problem {i}", aid=f"a{i}") for i in range(8)
        ]))
        assert requests[0].summary == "8 new alerts"
        assert "…and 3 more" in requests[0].body

    def test_escalations_are_not_coalesced(self):
        """Two criticals escalating on the same poll stay separate popups."""
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=2, coalesce_threshold=2)
        alerts = _alerts(
            _alert("critical", "Disk full", aid="a1"),
            _alert("critical", "Postgres down", aid="a2"),
        )
        policy.evaluate(alerts)                 # one quiet summary
        requests = policy.evaluate(alerts)      # both escalate

        assert len(requests) == 2
        assert all(r.escalation for r in requests)
        assert {r.fingerprint for r in requests} == {
            "critical:Disk full", "critical:Postgres down",
        }


# ── 4. Snooze / mute ─────────────────────────────────────────────────


class TestSnooze:
    """The "Snooze 1h" button silences a fingerprint or service."""

    def test_snooze_key_is_service_scoped_when_available(self):
        policy = _policy(FakeClock())
        request = policy.evaluate(
            _alerts(_alert("warning", "redis degraded", service="redis"))
        )[0]
        assert request.snooze_key == "service:redis"

    def test_snooze_key_falls_back_to_fingerprint(self):
        policy = _policy(FakeClock())
        request = policy.evaluate(_alerts(_alert("warning", "RAM high")))[0]
        assert request.snooze_key == "fp:warning:RAM high"

    def test_snoozed_service_stays_silent(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=0, snooze_minutes=60)
        alerts = _alerts(_alert("critical", "redis unreachable", service="redis"))

        policy.evaluate(alerts)
        policy.snooze("service:redis")
        policy.evaluate(_alerts())
        clock.advance(30)
        assert policy.evaluate(alerts) == []

    def test_snooze_expires(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=0, snooze_minutes=60)
        alerts = _alerts(_alert("critical", "redis unreachable", service="redis"))

        policy.snooze("service:redis")
        assert policy.evaluate(alerts) == []
        policy.evaluate(_alerts())
        clock.advance(61)
        assert len(policy.evaluate(alerts)) == 1

    def test_snooze_by_fingerprint(self):
        clock = FakeClock()
        policy = _policy(clock, flap_cooldown_minutes=0)
        alerts = _alerts(_alert("warning", "RAM high"))

        policy.snooze("fp:warning:RAM high")
        assert policy.evaluate(alerts) == []

    def test_snooze_only_affects_its_target(self):
        clock = FakeClock()
        policy = _policy(clock)
        policy.snooze("service:redis")
        requests = policy.evaluate(_alerts(
            _alert("warning", "redis degraded", aid="a1", service="redis"),
            _alert("warning", "RAM high", aid="a2"),
        ))
        assert len(requests) == 1
        assert "RAM high" in requests[0].body

    def test_snooze_window_configurable(self):
        clock = FakeClock()
        policy = _policy(clock, snooze_minutes=15)
        policy.snooze("fp:x")
        clock.advance(14)
        assert policy.is_snoozed("fp:x")
        clock.advance(2)
        assert not policy.is_snoozed("fp:x")

    def test_tray_snooze_signal_reaches_policy(self, qapp):
        """DbusNotifier.snooze_requested → TrayIcon → policy."""
        tray = TrayIcon()
        notifier, _iface, _p = _make_notifier()
        tray.set_notifier(notifier)

        notifier.snooze_requested.emit("service:redis")

        assert tray.notification_policy.is_snoozed("service:redis")


class TestMute:
    """Expected-down services never produce a desktop notification."""

    def test_muted_service_is_silent(self):
        policy = _policy(FakeClock(), muted_services=("redis",))
        alerts = _alerts(
            _alert("critical", "redis unreachable", service="redis")
        )
        assert policy.evaluate(alerts) == []

    def test_mute_is_case_insensitive(self):
        policy = _policy(FakeClock(), muted_services=("Redis",))
        alerts = _alerts(_alert("critical", "down", service="redis"))
        assert policy.evaluate(alerts) == []

    def test_mute_matches_title_when_no_service_name(self):
        policy = _policy(
            FakeClock(), muted_services=("personal-assistant",),
        )
        alerts = _alerts(_alert("critical", "personal-assistant unreachable"))
        assert policy.evaluate(alerts) == []

    def test_unmuted_service_still_notifies(self):
        policy = _policy(FakeClock(), muted_services=("redis",))
        alerts = _alerts(_alert("critical", "postgres down", service="postgres"))
        assert len(policy.evaluate(alerts)) == 1

    def test_muted_alerts_do_not_join_the_summary(self):
        policy = _policy(FakeClock(), muted_services=("redis",))
        requests = policy.evaluate(_alerts(
            _alert("critical", "redis unreachable", aid="a1", service="redis"),
            _alert("warning", "RAM high", aid="a2"),
        ))
        assert len(requests) == 1
        assert requests[0].summary == "WARNING: sysadmin"


# ── 5. Progressive escalation ────────────────────────────────────────


class TestEscalation:
    """First failure is quiet; persistence earns a persistent popup."""

    def test_first_poll_is_quiet(self):
        policy = _policy(FakeClock(), escalation_polls=3)
        request = policy.evaluate(_alerts(_alert("critical", "Disk full")))[0]

        assert request.summary == "CRITICAL: sysadmin"   # label is honest
        assert request.severity == "info"                # urgency is not
        assert request.alert_severity == "critical"
        assert request.escalation is False

    def test_escalates_after_configured_polls(self):
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=3)
        alerts = _alerts(_alert("critical", "Disk full"))

        assert len(policy.evaluate(alerts)) == 1   # poll 1 — quiet
        assert policy.evaluate(alerts) == []       # poll 2 — nothing
        requests = policy.evaluate(alerts)         # poll 3 — escalate
        assert len(requests) == 1
        assert requests[0].severity == "critical"
        assert requests[0].escalation is True
        assert "Still failing after 3 checks" in requests[0].body

    def test_escalates_only_once(self):
        policy = _policy(FakeClock(), escalation_polls=2)
        alerts = _alerts(_alert("critical", "Disk full"))
        policy.evaluate(alerts)
        policy.evaluate(alerts)
        assert policy.evaluate(alerts) == []
        assert policy.evaluate(alerts) == []

    def test_escalation_reuses_the_fingerprint_for_replacement(self):
        policy = _policy(FakeClock(), escalation_polls=2)
        alerts = _alerts(_alert("critical", "Disk full"))
        first = policy.evaluate(alerts)[0]
        second = policy.evaluate(alerts)[0]
        assert first.fingerprint == second.fingerprint == "critical:Disk full"

    def test_escalation_disabled_notifies_loudly_at_once(self):
        policy = _policy(FakeClock(), escalation_polls=1)
        request = policy.evaluate(_alerts(_alert("critical", "Disk full")))[0]
        assert request.severity == "critical"
        assert request.transient is False

    def test_warnings_never_escalate(self):
        policy = _policy(FakeClock(), escalation_polls=2)
        alerts = _alerts(_alert("warning", "RAM high"))
        assert policy.evaluate(alerts)[0].severity == "warning"
        assert policy.evaluate(alerts) == []
        assert policy.evaluate(alerts) == []

    def test_resolved_then_recurring_starts_quiet_again(self):
        clock = FakeClock()
        policy = _policy(clock, escalation_polls=2, flap_cooldown_minutes=0)
        alerts = _alerts(_alert("critical", "Disk full"))

        policy.evaluate(alerts)
        policy.evaluate(alerts)              # escalated
        policy.evaluate(_alerts())           # resolved
        assert policy.evaluate(alerts)[0].severity == "info"


# ── 7. Desktop DND vs the app's own DND ──────────────────────────────


class TestDndInteraction:
    """The more restrictive of the two DNDs wins."""

    def test_desktop_inhibition_suppresses_warnings(self):
        policy = _policy(FakeClock())
        assert policy.evaluate(
            _alerts(_alert("warning", "RAM high")), desktop_inhibited=True,
        ) == []

    def test_desktop_inhibition_lets_criticals_through(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(
            _alerts(_alert("critical", "Disk full")), desktop_inhibited=True,
        )
        assert len(requests) == 1

    def test_desktop_inhibition_can_be_ignored(self):
        policy = _policy(FakeClock(), respect_desktop_dnd=False)
        requests = policy.evaluate(
            _alerts(_alert("warning", "RAM high")), desktop_inhibited=True,
        )
        assert len(requests) == 1

    def test_app_dnd_allows_criticals_when_configured(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(
            _alerts(
                _alert("critical", "Disk full", aid="a1"),
                _alert("warning", "RAM high", aid="a2"),
            ),
            dnd_active=True,
            dnd_allow_critical=True,
        )
        assert len(requests) == 1
        assert "Disk full" in requests[0].body

    def test_app_dnd_wins_for_criticals(self):
        """App DND without allow_critical silences everything."""
        policy = _policy(FakeClock())
        assert policy.evaluate(
            _alerts(_alert("critical", "Disk full")),
            dnd_active=True,
            dnd_allow_critical=False,
            desktop_inhibited=False,
        ) == []

    def test_both_dnds_active(self):
        policy = _policy(FakeClock())
        requests = policy.evaluate(
            _alerts(
                _alert("critical", "Disk full", aid="a1"),
                _alert("warning", "RAM high", aid="a2"),
            ),
            dnd_active=True,
            dnd_allow_critical=True,
            desktop_inhibited=True,
        )
        assert len(requests) == 1
        assert "Disk full" in requests[0].body


class TestInhibitedQuery:
    """Reading the org.freedesktop.Notifications Inhibited property.

    The property read itself (Properties.Get marshalling) is exercised
    against the live session bus; these tests cover the caching and
    degradation logic around it.
    """

    def test_true_property_is_reported(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=True)
        assert notifier.desktop_inhibited() is True

    def test_false_property_is_reported(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=False)
        assert notifier.desktop_inhibited() is False

    def test_result_is_cached_between_calls(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=True)
        notifier.desktop_inhibited()
        notifier.desktop_inhibited()
        assert notifier._read_inhibited.call_count == 1

    def test_cache_expires(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=True)
        notifier.desktop_inhibited()
        notifier._inhibit_checked_at -= 60  # pretend the cache went stale
        notifier.desktop_inhibited()
        assert notifier._read_inhibited.call_count == 2

    def test_unsupported_property_degrades_gracefully(self, qapp):
        """A daemon without the property is never queried twice."""
        notifier, _iface, _p = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=None)
        assert notifier.desktop_inhibited() is False
        assert notifier.desktop_inhibited() is False
        assert notifier._read_inhibited.call_count == 1

    def test_invalid_reply_reads_as_unsupported(self, qapp):
        """An error reply from Properties.Get yields None, not a crash."""
        notifier, _iface, _p = _make_notifier()
        props = MagicMock()
        reply = MagicMock()
        reply.isValid.return_value = False
        notifier._props = props
        with patch("sysadmin_tray.notifications.QDBusReply", return_value=reply):
            assert notifier._read_inhibited() is None

    def test_non_bool_value_reads_as_unsupported(self, qapp):
        notifier, _iface, _p = _make_notifier()
        reply = MagicMock()
        reply.isValid.return_value = True
        reply.value.return_value = "yes"
        notifier._props = MagicMock()
        with patch("sysadmin_tray.notifications.QDBusReply", return_value=reply):
            assert notifier._read_inhibited() is None

    def test_bool_value_is_returned(self, qapp):
        notifier, _iface, _p = _make_notifier()
        reply = MagicMock()
        reply.isValid.return_value = True
        reply.value.return_value = True
        notifier._props = MagicMock()
        with patch("sysadmin_tray.notifications.QDBusReply", return_value=reply):
            assert notifier._read_inhibited() is True

    def test_no_properties_proxy_reads_as_unsupported(self, qapp):
        notifier, _iface, _p = _make_notifier()
        notifier._props = None
        assert notifier._read_inhibited() is None

    def test_unavailable_dbus_is_never_inhibited(self, qapp):
        with patch("sysadmin_tray.notifications.QDBusConnection") as conn_cls:
            bus = MagicMock()
            bus.isConnected.return_value = False
            conn_cls.sessionBus.return_value = bus
            notifier = DbusNotifier()
        assert notifier.desktop_inhibited() is False

    def test_tray_treats_non_bool_as_not_inhibited(self, qapp):
        """A mock (or anything but True) must not silence the tray."""
        tray = TrayIcon()
        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)
        assert tray._desktop_inhibited() is False

    def test_tray_without_notifier_is_not_inhibited(self, qapp):
        assert TrayIcon()._desktop_inhibited() is False


# ── 8. Warning digest mode ───────────────────────────────────────────


class TestDigestMode:
    """Opt-in: warnings badge the icon and arrive as a periodic digest."""

    def test_warnings_do_not_interrupt(self):
        policy = _policy(FakeClock(), digest_mode=True)
        assert policy.evaluate(_alerts(_alert("warning", "RAM high"))) == []
        assert policy.pending_digest_count == 1

    def test_criticals_still_interrupt(self):
        policy = _policy(FakeClock(), digest_mode=True)
        requests = policy.evaluate(_alerts(
            _alert("critical", "Disk full", aid="a1"),
            _alert("warning", "RAM high", aid="a2"),
        ))
        assert len(requests) == 1
        assert "Disk full" in requests[0].body
        assert policy.pending_digest_count == 1

    def test_digest_delivered_after_the_interval(self):
        clock = FakeClock()
        policy = _policy(clock, digest_mode=True, digest_interval_minutes=60)
        policy.evaluate(_alerts(_alert("warning", "RAM high", aid="a1")))
        clock.advance(20)
        policy.evaluate(_alerts(_alert("warning", "CPU high", aid="a2")))
        clock.advance(20)
        assert policy.evaluate(_alerts()) == []      # not yet an hour

        clock.advance(25)
        requests = policy.evaluate(_alerts())
        assert len(requests) == 1
        digest = requests[0]
        assert digest.fingerprint == FP_DIGEST
        assert digest.severity == "info"
        assert "2 alerts in the last hour" in digest.summary
        assert "2 warning" in digest.body
        assert "RAM high" in digest.body and "CPU high" in digest.body
        assert policy.pending_digest_count == 0

    def test_repeated_polls_of_one_warning_queue_once(self):
        clock = FakeClock()
        policy = _policy(clock, digest_mode=True)
        alerts = _alerts(_alert("warning", "RAM high"))
        for _ in range(4):
            policy.evaluate(alerts)
            clock.advance(1)
        assert policy.pending_digest_count == 1

    def test_manual_flush_returns_none_when_empty(self):
        policy = _policy(FakeClock(), digest_mode=True)
        assert policy.flush_digest() is None

    def test_digest_off_by_default(self):
        policy = _policy(FakeClock())
        assert len(policy.evaluate(_alerts(_alert("warning", "RAM high")))) == 1
        assert policy.pending_digest_count == 0


# ── Tray wiring ──────────────────────────────────────────────────────


class TestTrayWiring:
    """TrayIcon passes the policy's verdict straight to the notifier."""

    def test_dispatch_forwards_calm_kwargs(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")
        notifier = MagicMock(spec=DbusNotifier)
        notifier.desktop_inhibited.return_value = False
        tray.set_notifier(notifier)

        tray.update_from_alerts(
            _alerts(_alert("warning", "redis degraded", service="redis"))
        )

        kwargs = notifier.notify.call_args.kwargs
        assert kwargs["fingerprint"] == "warning:redis degraded"
        assert kwargs["service_name"] == "redis"
        assert kwargs["snooze_key"] == "service:redis"
        assert kwargs["transient"] is False

    def test_config_flows_into_policy_settings(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True,
            min_severity="warning",
            flap_cooldown_minutes=5,
            escalation_polls=7,
            coalesce_threshold=4,
            snooze_minutes=15,
            digest_mode=True,
            digest_interval_minutes=120,
            respect_desktop_dnd=False,
            muted_services=["redis", "personal-assistant"],
        )

        settings = tray.notification_policy.settings
        assert settings.enabled is True
        assert settings.min_severity == "warning"
        assert settings.flap_cooldown_minutes == 5
        assert settings.escalation_polls == 7
        assert settings.coalesce_threshold == 4
        assert settings.snooze_minutes == 15
        assert settings.digest_mode is True
        assert settings.digest_interval_minutes == 120
        assert settings.respect_desktop_dnd is False
        assert settings.muted_services == ("redis", "personal-assistant")

    def test_omitted_tunables_keep_current_values(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True, min_severity="warning", flap_cooldown_minutes=5,
        )
        tray.set_notification_config(enabled=True, min_severity="critical")
        assert tray.notification_policy.settings.flap_cooldown_minutes == 5

    def test_apply_settings_wholesale(self, qapp):
        tray = TrayIcon()
        settings = NotificationSettings(min_severity="info", digest_mode=True)
        tray.apply_notification_settings(settings)
        assert tray.notification_policy.settings is settings

    def test_muted_service_produces_no_toast(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True, min_severity="warning", muted_services=["redis"],
        )
        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(
                _alerts(_alert("critical", "redis unreachable", service="redis"))
            )
            mock_show.assert_not_called()

    def test_end_to_end_escalation_replaces_in_place(self, qapp):
        """Tray → notifier → payload: the escalation replaces the quiet popup."""
        tray = TrayIcon()
        tray.set_notification_config(
            enabled=True, min_severity="warning", escalation_polls=2,
        )
        notifier, _iface, payloads = _make_notifier()
        notifier._read_inhibited = MagicMock(return_value=False)
        tray.set_notifier(notifier)

        alerts = _alerts(_alert("critical", "Disk full", service="postgres"))
        tray.update_from_alerts(alerts)
        tray.update_from_alerts(alerts)

        assert len(payloads) == 2
        assert payloads[0].replaces_id == 0
        assert payloads[0].hints["urgency"] == 0          # quiet opener
        assert payloads[0].hints["transient"] is True
        assert payloads[1].replaces_id == 101             # replaces the opener
        assert payloads[1].hints["urgency"] == 2          # now critical
        assert "transient" not in payloads[1].hints
