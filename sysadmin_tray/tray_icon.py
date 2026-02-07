"""System tray icon with programmatic colour rendering and context menu."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from sysadmin_tray.models import (
    ICON_COLOURS,
    AlertInfo,
    AlertsResponse,
    IconState,
    StatusResponse,
    compute_icon_state,
)

logger = logging.getLogger(__name__)

_ICON_SIZE = QSize(22, 22)

_SEVERITY_LEVELS: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}

_SEVERITY_ICONS: dict[str, QSystemTrayIcon.MessageIcon] = {
    "info": QSystemTrayIcon.MessageIcon.Information,
    "warning": QSystemTrayIcon.MessageIcon.Warning,
    "critical": QSystemTrayIcon.MessageIcon.Critical,
}

# Notification display duration in ms (0 = sticky / persistent)
_SEVERITY_TIMEOUT_MS: dict[str, int] = {
    "info": 5000,
    "warning": 10000,
    "critical": 0,
}


def render_icon(state: IconState) -> QIcon:
    """Draw a filled circle with the state colour.

    Keeps things simple for Phase 1 — no SVG assets to ship.
    """
    colour = QColor(ICON_COLOURS[state])
    pixmap = QPixmap(_ICON_SIZE)
    pixmap.fill(QColor(0, 0, 0, 0))  # transparent background

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer ring (slightly darker)
    darker = colour.darker(120)
    painter.setPen(QPen(darker, 1.5))
    painter.setBrush(QBrush(colour))

    margin = 2
    painter.drawEllipse(margin, margin,
                        _ICON_SIZE.width() - margin * 2,
                        _ICON_SIZE.height() - margin * 2)
    painter.end()

    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """KDE system tray icon that reflects backend health state.

    Signals:
        ``popup_requested``: emitted when the user clicks the tray icon.
        ``quit_requested``: emitted when the user selects Quit from the menu.
        ``dashboard_requested``: emitted when Dashboard is chosen from menu.
    """

    popup_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    dashboard_requested = pyqtSignal()
    critical_alerts_changed = pyqtSignal(list)  # list[AlertInfo]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._current_state = IconState.DISCONNECTED
        self._last_status: StatusResponse | None = None
        self._last_alerts: AlertsResponse | None = None
        self._backend_reachable = False

        # Notification state
        self._seen_alert_ids: set[str] = set()
        self._show_notifications = True
        self._min_severity_level = _SEVERITY_LEVELS["critical"]

        # Initial icon
        self.setIcon(render_icon(self._current_state))
        self.setToolTip("SysAdmin Monitor — connecting…")

        # Context menu
        self._menu = QMenu()
        self._status_action = QAction("Status: connecting…", self._menu)
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)
        self._menu.addSeparator()

        dashboard_action = QAction("Open Dashboard", self._menu)
        dashboard_action.triggered.connect(self.dashboard_requested.emit)
        self._menu.addAction(dashboard_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)

        # Left click → toggle popup
        self.activated.connect(self._on_activated)

    # ── Slots for ApiClient signals ──────────────────────────────────

    def update_from_status(self, status: StatusResponse) -> None:
        """Called when new service status data arrives."""
        self._last_status = status
        self._backend_reachable = True
        self._recompute_state()

    def update_from_alerts(self, alerts: AlertsResponse) -> None:
        """Called when new alert data arrives."""
        self._last_alerts = alerts
        self._check_new_alerts(alerts)
        self._recompute_state()

    def on_connection_lost(self) -> None:
        """Called when the backend becomes unreachable."""
        self._backend_reachable = False
        self._recompute_state()

    def on_connection_restored(self) -> None:
        """Called when the backend becomes reachable again."""
        self._backend_reachable = True
        self._recompute_state()

    # ── Internal ─────────────────────────────────────────────────────

    def _recompute_state(self) -> None:
        """Recalculate icon colour and tooltip from current data."""
        new_state = compute_icon_state(
            self._last_status,
            self._last_alerts,
            self._backend_reachable,
        )

        if new_state != self._current_state:
            self._current_state = new_state
            self.setIcon(render_icon(new_state))
            logger.debug("icon state → %s", new_state.value)

        # Update tooltip
        tooltip_parts = [f"SysAdmin Monitor — {new_state.value}"]
        if self._last_alerts and self._last_alerts.count > 0:
            tooltip_parts.append(
                f"{self._last_alerts.critical_count} critical, "
                f"{self._last_alerts.warning_count} warning, "
                f"{self._last_alerts.info_count} info"
            )
        self.setToolTip("\n".join(tooltip_parts))

        # Update status line in context menu
        self._status_action.setText(f"Status: {new_state.value}")

    # ── Notification logic ──────────────────────────────────────────

    def set_notification_config(
        self, *, enabled: bool = True, min_severity: str = "critical"
    ) -> None:
        """Configure desktop notification behaviour."""
        self._show_notifications = enabled
        self._min_severity_level = _SEVERITY_LEVELS.get(
            min_severity, _SEVERITY_LEVELS["critical"]
        )

    def _check_new_alerts(self, alerts: AlertsResponse) -> None:
        """Fire desktop notifications for unseen alerts above threshold.

        Critical alerts are routed to the persistent dialog via signal;
        warning/info alerts still use transient ``showMessage()`` toasts.
        """
        if not self._show_notifications:
            return

        # Collect unacked criticals for the dialog
        unacked_criticals = [
            a for a in alerts.alerts
            if a.severity == "critical" and not a.acknowledged
        ]

        has_new_critical = False
        for alert in alerts.alerts:
            if alert.acknowledged:
                continue
            if alert.id in self._seen_alert_ids:
                continue
            alert_level = _SEVERITY_LEVELS.get(alert.severity, 0)
            if alert_level < self._min_severity_level:
                continue

            self._seen_alert_ids.add(alert.id)

            if alert.severity == "critical":
                has_new_critical = True
            else:
                self._show_desktop_notification(alert)

        # Emit the critical alerts signal whenever we have unacked criticals
        # (the dialog will diff and add/remove cards as needed)
        if unacked_criticals or has_new_critical:
            self.critical_alerts_changed.emit(unacked_criticals)

    def _show_desktop_notification(self, alert: AlertInfo) -> None:
        """Show a native desktop notification via QSystemTrayIcon."""
        severity_upper = alert.severity.upper()
        title = f"{severity_upper}: sysadmin"
        body = alert.title
        if alert.message:
            body = f"{alert.title}\n{alert.message}"

        icon = _SEVERITY_ICONS.get(
            alert.severity, QSystemTrayIcon.MessageIcon.Information
        )
        timeout = _SEVERITY_TIMEOUT_MS.get(alert.severity, 5000)

        self.showMessage(title, body, icon, timeout)
        logger.debug("notification: [%s] %s", alert.severity, alert.title)

    def on_service_action_complete(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Show a toast notification for a completed service action."""
        if success:
            title = "Service Action"
            body = f"{service_name} {action}ed successfully"
            icon = QSystemTrayIcon.MessageIcon.Information
            timeout = 5000
        else:
            title = "Service Action Failed"
            body = f"{service_name} {action} failed: {message}"
            icon = QSystemTrayIcon.MessageIcon.Warning
            timeout = 10000
        self.showMessage(title, body, icon, timeout)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.popup_requested.emit()
