"""Tests for desktop notification logic in TrayIcon.

Critical alerts are routed to the persistent dialog via
``critical_alerts_changed`` signal — they no longer call ``showMessage()``.
Warning/info alerts still use ``showMessage()`` toasts.
"""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon

from sysadmin_tray.models import AlertInfo, AlertsResponse
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


# ── Critical alerts → signal (not toast) ──────────────────────────


class TestCriticalAlertSignal:
    """Critical alerts emit critical_alerts_changed instead of showMessage."""

    def test_critical_alert_emits_signal_not_toast(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "critical", "Disk full"))
            tray.update_from_alerts(alerts)

            # showMessage NOT called for criticals
            mock_show.assert_not_called()
            # Signal emitted with list of unacked criticals
            handler.assert_called_once()
            emitted = handler.call_args[0][0]
            assert len(emitted) == 1
            assert emitted[0].id == "a1"

    def test_critical_signal_carries_all_unacked_criticals(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        alerts = _make_alerts(
            ("a1", "critical", "Disk full"),
            ("a2", "critical", "CPU spike"),
        )
        tray.update_from_alerts(alerts)

        emitted = handler.call_args[0][0]
        assert len(emitted) == 2

    def test_critical_dedup_still_emits_signal(self, qapp):
        """Same critical seen twice: signal still emitted (dialog needs full list)."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        alerts = _make_alerts(("a1", "critical", "Disk full"))
        tray.update_from_alerts(alerts)
        tray.update_from_alerts(alerts)

        # Signal emitted both times (dialog reconciles internally)
        assert handler.call_count == 2

    def test_acknowledged_critical_not_in_signal(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        alert = AlertInfo(
            id="a1", severity="critical", title="Disk full", acknowledged=True
        )
        alerts = AlertsResponse(alerts=[alert], count=1)
        tray.update_from_alerts(alerts)

        # No unacked criticals → signal not emitted
        handler.assert_not_called()


# ── Warning / info alerts → still use showMessage ────────────────


class TestNonCriticalToasts:
    """Warning and info alerts still fire showMessage() toasts."""

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
    """Same alert ID should not trigger duplicate notifications."""

    def test_same_warning_not_notified_twice(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        alerts = _make_alerts(("a1", "warning", "RAM high"))

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            tray.update_from_alerts(alerts)
            assert mock_show.call_count == 1

    def test_different_warnings_both_notify(self, qapp):
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


class TestNotificationDisabled:
    """Notifications can be disabled entirely."""

    def test_disabled_notifications_do_not_fire(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=False, min_severity="info")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        with patch.object(tray, "showMessage") as mock_show:
            alerts = _make_alerts(("a1", "critical", "Disk full"))
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()
            handler.assert_not_called()


class TestAcknowledgedAlerts:
    """Acknowledged alerts should not trigger notifications."""

    def test_acknowledged_alert_does_not_notify(self, qapp):
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="critical")

        alert = AlertInfo(
            id="a1", severity="critical", title="Disk full", acknowledged=True
        )
        alerts = AlertsResponse(alerts=[alert], count=1)

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

        with patch.object(tray, "showMessage") as mock_show:
            tray.update_from_alerts(alerts)
            mock_show.assert_not_called()
            handler.assert_not_called()


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
        # Default — only critical should produce signal, no showMessage
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
        """With warning threshold: warning → toast, critical → signal, info → skip."""
        tray = TrayIcon()
        tray.set_notification_config(enabled=True, min_severity="warning")

        handler = MagicMock()
        tray.critical_alerts_changed.connect(handler)

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
            # Only warning goes to showMessage (info below threshold, critical to signal)
            assert mock_show.call_count == 1
            assert "WARNING" in mock_show.call_args[0][0]

        # Critical went to signal
        handler.assert_called_once()
        emitted = handler.call_args[0][0]
        assert len(emitted) == 1
        assert emitted[0].severity == "critical"


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
