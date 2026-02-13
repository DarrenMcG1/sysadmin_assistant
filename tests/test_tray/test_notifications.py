"""Tests for desktop notification logic in TrayIcon and DbusNotifier.

All alert severities above threshold are sent via ``DbusNotifier`` when
available, falling back to ``showMessage()`` toasts.  Deduplication is
by content fingerprint (severity:title) so repeated backend rows for the
same logical alert only fire one notification.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from sysadmin_tray.models import AlertInfo, AlertsResponse
from sysadmin_tray.notifications import DbusNotifier
from sysadmin_tray.tray_icon import TrayIcon


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def _make_alerts(*items: tuple[str, str, str]) -> AlertsResponse:
    """Build AlertsResponse from (id, severity, title) tuples."""
    alerts = [
        AlertInfo(id=aid, severity=sev, title=title)
        for aid, sev, title in items
    ]
    return AlertsResponse(alerts=alerts, count=len(alerts))


def _make_service_alert(
    aid: str, severity: str, title: str, service_name: str,
) -> AlertInfo:
    """Build an AlertInfo with service_name in details."""
    return AlertInfo(
        id=aid, severity=severity, title=title,
        details={"service_name": service_name},
    )


# ── Critical alerts → D-Bus notification ─────────────────────────


class TestCriticalAlertNotification:
    """Critical alerts fire D-Bus / showMessage notifications."""

    def test_critical_alert_fires_notification(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "critical", "Disk full"))
            tray.update_from_alerts(alerts)
            mock_show.assert_called_once()
            assert "CRITICAL" in mock_show.call_args[0][0]

    def test_critical_with_service_name_passes_to_notifier(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        alert = _make_service_alert("a1", "critical", "redis unreachable", "redis")
        alerts = AlertsResponse(alerts=[alert], count=1)
        tray.update_from_alerts(alerts)

        notifier.notify.assert_called_once()
        assert notifier.notify.call_args.kwargs["service_name"] == "redis"

    def test_critical_without_service_name_still_notifies(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        alerts = _make_alerts(("a1", "critical", "High RAM usage"))
        tray.update_from_alerts(alerts)

        notifier.notify.assert_called_once()


# ── Warning / info alerts → showMessage fallback (no notifier) ───


class TestNonCriticalToasts:
    """Warning and info alerts still fire showMessage() toasts when no notifier set."""

    def test_warning_below_critical_threshold_does_not_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()

    def test_warning_at_warning_threshold_does_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts)
            mock_show.assert_called_once()
            assert "WARNING" in mock_show.call_args[0][0]

    def test_info_at_info_threshold_does_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="info")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "info", "Scan complete"))
            tray.update_from_alerts(alerts)
            mock_show.assert_called_once()
            assert "INFO" in mock_show.call_args[0][0]


class TestNotificationDedup:
    """Same alert fingerprint should not trigger duplicate notifications."""

    def test_same_alert_not_notified_twice(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alerts = _make_alerts(("a1", "warning", "RAM high"))

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            tray.update_from_alerts(alerts)
            assert mock_show.call_count == 1

    def test_different_db_ids_same_content_deduped(self, qapp):
        """Multiple DB rows for the same logical alert fire only once."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(
                ("a1", "warning", "RAM high"),
                ("a2", "warning", "RAM high"),  # different ID, same content
            )
            tray.update_from_alerts(alerts)
            assert mock_show.call_count == 1

    def test_different_alerts_both_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        with patch.object(tray, "showMessage") as mock_show:
            alerts1 = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts1)

            alerts2 = _make_alerts(
                ("a1", "warning", "RAM high"),
                ("a2", "warning", "CPU high"),
            )
            tray.update_from_alerts(alerts2)
            assert mock_show.call_count == 2

    def test_resolved_alert_re_notifies_on_recurrence(self, qapp):
        """When an alert resolves then comes back, it fires again."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        with patch.object(tray, "showMessage") as mock_show:
            # Alert appears
            tray.update_from_alerts(_make_alerts(("a1", "warning", "RAM high")))
            assert mock_show.call_count == 1

            # Alert resolves (empty list clears fingerprints)
            tray.update_from_alerts(AlertsResponse(alerts=[], count=0))

            # Alert recurs
            tray.update_from_alerts(_make_alerts(("a3", "warning", "RAM high")))
            assert mock_show.call_count == 2


class TestNotificationDisabled:
    """Notifications can be disabled entirely."""

    def test_disabled_notifications_do_not_fire(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=False, min_severity="info")

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "critical", "Disk full"))
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()


class TestAcknowledgedAlerts:
    """Acknowledged alerts should not trigger notifications."""

    def test_acknowledged_alert_does_not_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        alert = AlertInfo(
            id="a1", severity="critical", title="Disk full", acknowledged=True
        )
        alerts = AlertsResponse(alerts=[alert], count=1)

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()


class TestNotificationMessageFormat:
    """Notification messages include title and optional body (warning/info only)."""

    def test_warning_title_and_message(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alert = AlertInfo(
            id="a1", severity="warning", title="RAM high",
            message="Usage at 92%",
        )
        alerts = AlertsResponse(alerts=[alert], count=1)

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)

            title, body = mock_show.call_args[0][0], mock_show.call_args[0][1]
            assert title == "WARNING: sysadmin"
            assert "RAM high" in body
            assert "Usage at 92%" in body

    def test_warning_uses_10s_timeout(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alerts = _make_alerts(("a1", "warning", "RAM high"))

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            timeout_arg = mock_show.call_args[0][3]
            assert timeout_arg == 10000

    def test_warning_uses_warning_icon(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alerts = _make_alerts(("a1", "warning", "RAM high"))

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            icon_arg = mock_show.call_args[0][2]
            assert icon_arg == QSystemTrayIcon.MessageIcon.Warning


class TestSeverityThresholdConfig:
    """set_notification_config correctly configures the threshold."""

    def test_default_is_critical(self, qapp):
        tray = TrayIcon()
        # Default — only critical should produce notification
        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()

    def test_unknown_severity_falls_back_to_critical(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="banana")
        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()

    def test_mixed_severity_warning_threshold(self, qapp):
        """With warning threshold: all severities >= warning get notified."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alerts = AlertsResponse(
            alerts=[
                AlertInfo(id="a1", severity="info", title="Scan done"),
                AlertInfo(id="a2", severity="warning", title="RAM high"),
                AlertInfo(id="a3", severity="critical", title="Disk full"),
            ],
            count=3,
        )

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            # warning + critical notified, info below threshold
            assert mock_show.call_count == 2


class TestServiceActionToasts:
    """on_service_action_complete shows toast notifications."""

    def test_success_toast(self, qapp):
        tray = TrayIcon()
        with patch.object(tray, "showMessage") as mock_show:
            tray.on_service_action_complete("redis", "restart", True, "ok")
            mock_show.assert_called_once()
            title, body = mock_show.call_args[0][0], mock_show.call_args[0][1]
            assert title == "Service Action"
            assert "redis" in body
            assert "restart" in body

    def test_failure_toast(self, qapp):
        tray = TrayIcon()
        with patch.object(tray, "showMessage") as mock_show:
            tray.on_service_action_complete("redis", "start", False, "access denied")
            mock_show.assert_called_once()
            title, body = mock_show.call_args[0][0], mock_show.call_args[0][1]
            assert "Failed" in title
            assert "access denied" in body


# ── DbusNotifier delegation tests ─────────────────────────────────


class TestNotifierDelegation:
    """When a DbusNotifier is set, TrayIcon delegates notifications to it."""

    def test_warning_delegates_to_notifier(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        alerts = _make_alerts(("a1", "warning", "RAM high"))
        tray.update_from_alerts(alerts)

        notifier.notify.assert_called_once()
        args = notifier.notify.call_args
        assert "WARNING" in args[0][0]
        assert args.kwargs.get("service_name") is None

    def test_notifier_receives_service_name(self, qapp):
        """Warning alert with service_name passes it to notifier."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        alert = _make_service_alert("a1", "warning", "redis degraded", "redis")
        alerts = AlertsResponse(alerts=[alert], count=1)
        tray.update_from_alerts(alerts)

        notifier.notify.assert_called_once()
        assert notifier.notify.call_args.kwargs["service_name"] == "redis"

    def test_service_action_delegates_to_notifier(self, qapp):
        """on_service_action_complete delegates to notifier when set."""
        tray = TrayIcon()
        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        tray.on_service_action_complete("redis", "restart", True, "ok")

        notifier.notify.assert_called_once()
        title_arg = notifier.notify.call_args[0][0]
        assert title_arg == "Service Action"

    def test_service_action_failure_severity(self, qapp):
        """Failed service action uses warning severity via notifier."""
        tray = TrayIcon()
        notifier = MagicMock(spec=DbusNotifier)
        tray.set_notifier(notifier)

        tray.on_service_action_complete("redis", "start", False, "access denied")

        notifier.notify.assert_called_once()
        severity_arg = notifier.notify.call_args[0][2]
        assert severity_arg == "warning"

    def test_no_notifier_falls_back_to_show_message(self, qapp):
        """Without notifier, showMessage is used directly."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")
        # No set_notifier() call

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "warning", "RAM high"))
            tray.update_from_alerts(alerts)
            mock_show.assert_called_once()


# ── DbusNotifier unit tests ──────────────────────────────────────


class TestDbusNotifier:
    """Unit tests for DbusNotifier with mocked D-Bus."""

    def test_fallback_when_dbus_unavailable(self, qapp):
        """When D-Bus init fails, notify() falls back to showMessage()."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=fallback)

        assert not notifier.available

        result = notifier.notify("Test", "body", "warning")
        assert result is False
        fallback.showMessage.assert_called_once()

    def test_fallback_when_interface_invalid(self, qapp):
        """When D-Bus interface is invalid, falls back to showMessage()."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls, patch(
            "sysadmin_tray.notifications.QDBusInterface"
        ) as mock_iface_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = True
            mock_conn_cls.sessionBus.return_value = mock_bus

            mock_iface = MagicMock()
            mock_iface.isValid.return_value = False
            mock_iface_cls.return_value = mock_iface

            notifier = DbusNotifier(fallback_tray=fallback)

        assert not notifier.available

        result = notifier.notify("Test", "body", "info")
        assert result is False
        fallback.showMessage.assert_called_once()

    def test_action_invoked_emits_restart(self, qapp):
        """ActionInvoked with matching notification_id emits restart_requested."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=fallback)

        handler = MagicMock()
        notifier.restart_requested.connect(handler)

        # Simulate pending action
        notifier._pending_actions[42] = "redis"
        notifier._on_action_invoked(42, "restart")

        handler.assert_called_once_with("redis")
        assert 42 not in notifier._pending_actions

    def test_action_invoked_wrong_key_ignored(self, qapp):
        """ActionInvoked with non-restart action key is ignored."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=fallback)

        handler = MagicMock()
        notifier.restart_requested.connect(handler)

        notifier._pending_actions[42] = "redis"
        notifier._on_action_invoked(42, "dismiss")

        handler.assert_not_called()

    def test_notification_closed_cleans_up(self, qapp):
        """NotificationClosed removes from pending_actions."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=fallback)

        notifier._pending_actions[42] = "redis"
        notifier._on_notification_closed(42, 2)  # reason 2 = dismissed

        assert 42 not in notifier._pending_actions

    def test_cleanup_resets_state(self, qapp):
        """cleanup() clears pending actions and marks unavailable."""
        fallback = MagicMock(spec=QSystemTrayIcon)

        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=fallback)

        notifier._pending_actions[42] = "redis"
        notifier.cleanup()

        assert len(notifier._pending_actions) == 0
        assert not notifier.available

    def test_no_fallback_tray_drops_notification(self, qapp):
        """When no fallback_tray and D-Bus unavailable, notification is dropped."""
        with patch(
            "sysadmin_tray.notifications.QDBusConnection"
        ) as mock_conn_cls:
            mock_bus = MagicMock()
            mock_bus.isConnected.return_value = False
            mock_conn_cls.sessionBus.return_value = mock_bus

            notifier = DbusNotifier(fallback_tray=None)

        # Should not raise
        result = notifier.notify("Test", "body", "info")
        assert result is False


# ── AlertInfo.service_name property ───────────────────────────────


class TestAlertInfoServiceName:
    """AlertInfo.service_name property extracts from details dict."""

    def test_service_name_from_details(self):
        alert = AlertInfo(
            id="a1", severity="critical", title="redis down",
            details={"service_name": "redis"},
        )
        assert alert.service_name == "redis"

    def test_service_name_none_when_missing(self):
        alert = AlertInfo(id="a1", severity="warning", title="RAM high")
        assert alert.service_name is None

    def test_service_name_none_when_empty_details(self):
        alert = AlertInfo(
            id="a1", severity="warning", title="RAM high", details={},
        )
        assert alert.service_name is None
