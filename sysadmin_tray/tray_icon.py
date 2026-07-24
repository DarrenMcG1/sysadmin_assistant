"""System tray icon with programmatic colour rendering and context menu."""

from __future__ import annotations

import logging

from PyQt6.QtCore import QSize, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon, QWidget

from sysadmin_tray.models import (
    ICON_COLOURS,
    AlertsResponse,
    IconState,
    StatusResponse,
    compute_icon_state,
)
from sysadmin_tray.notifications import (
    SEVERITY_LEVELS,
    NotificationPolicy,
    NotificationRequest,
    NotificationSettings,
)

logger = logging.getLogger(__name__)

_ICON_SIZE = QSize(22, 22)

_SEVERITY_LEVELS: dict[str, int] = SEVERITY_LEVELS

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
        ``popup_requested``: emitted when the user left-clicks the tray
            icon (the app opens the dashboard in response).
        ``quit_requested``: emitted when the user selects Quit from the menu.
        ``dashboard_requested``: emitted when Dashboard is chosen from menu.
    """

    popup_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    dashboard_requested = pyqtSignal()
    dnd_toggled = pyqtSignal(object)  # bool | None — emitted when user toggles DND from menu

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._current_state = IconState.DISCONNECTED
        self._last_status: StatusResponse | None = None
        self._last_alerts: AlertsResponse | None = None
        self._backend_reachable = False

        # Notification state — the policy owns the shared per-fingerprint
        # bookkeeping (dedup, flap cooldown, escalation, snooze, digest)
        self._policy = NotificationPolicy()
        self._notifier = None  # Optional DbusNotifier, set via set_notifier()

        # DND state (synced from backend)
        self._dnd_active = False
        self._dnd_allow_critical = True

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

        self._dnd_action = QAction("Do Not Disturb", self._menu)
        self._dnd_action.setCheckable(True)
        self._dnd_action.setChecked(False)
        self._dnd_action.triggered.connect(self._on_dnd_toggled)
        self._menu.addAction(self._dnd_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)

        # Left click → open dashboard
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

    def update_dnd_status(self, dnd_status: dict) -> None:
        """Called when DND status data arrives from the backend."""
        self._dnd_active = dnd_status.get("active", False)
        self._dnd_allow_critical = dnd_status.get("allow_critical", True)
        self._dnd_action.setChecked(self._dnd_active)
        # Update tooltip suffix
        self._recompute_state()

    def _on_dnd_toggled(self, checked: bool) -> None:
        """User toggled DND from context menu."""
        # Emit True to enable, None to revert to schedule
        self.dnd_toggled.emit(True if checked else None)

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
        if self._dnd_active:
            tooltip_parts.append("DND active")
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

    @property
    def notification_policy(self) -> NotificationPolicy:
        """The shared notification state machine (see notifications.py)."""
        return self._policy

    def set_notification_config(
        self,
        *,
        enabled: bool = True,
        min_severity: str = "critical",
        flap_cooldown_minutes: int | None = None,
        escalation_polls: int | None = None,
        coalesce_threshold: int | None = None,
        snooze_minutes: int | None = None,
        digest_mode: bool | None = None,
        digest_interval_minutes: int | None = None,
        respect_desktop_dnd: bool | None = None,
        muted_services: list[str] | None = None,
    ) -> None:
        """Configure desktop notification behaviour.

        ``enabled`` / ``min_severity`` keep their original meaning; the
        remaining keyword arguments are the Session 16 "calm" tunables and
        leave the current value alone when omitted.
        """
        settings = self._policy.settings
        settings.enabled = enabled
        settings.min_severity = min_severity

        overrides: dict[str, object | None] = {
            "flap_cooldown_minutes": flap_cooldown_minutes,
            "escalation_polls": escalation_polls,
            "coalesce_threshold": coalesce_threshold,
            "snooze_minutes": snooze_minutes,
            "digest_mode": digest_mode,
            "digest_interval_minutes": digest_interval_minutes,
            "respect_desktop_dnd": respect_desktop_dnd,
        }
        for name, value in overrides.items():
            if value is not None:
                setattr(settings, name, value)
        if muted_services is not None:
            settings.muted_services = tuple(muted_services)

    def apply_notification_settings(self, settings: NotificationSettings) -> None:
        """Replace the policy settings wholesale (used by the app wiring)."""
        self._policy.settings = settings

    def set_notifier(self, notifier) -> None:
        """Inject a DbusNotifier for rich desktop notifications."""
        self._notifier = notifier

        snooze_signal = getattr(notifier, "snooze_requested", None)
        if snooze_signal is not None and hasattr(snooze_signal, "connect"):
            snooze_signal.connect(self._on_snooze_requested)

    def _on_snooze_requested(self, snooze_key: str) -> None:
        """User clicked "Snooze" on a notification."""
        self._policy.snooze(snooze_key)

    def _check_new_alerts(self, alerts: AlertsResponse) -> None:
        """Hand the poll to the notification policy and dispatch its verdict.

        Every suppression rule (fingerprint dedup, flap cooldown, snooze,
        mute, DND, digest mode) lives in :class:`NotificationPolicy`; the
        tray only supplies the current DND context and sends whatever the
        policy hands back.
        """
        for request in self._policy.evaluate(
            alerts,
            dnd_active=self._dnd_active,
            dnd_allow_critical=self._dnd_allow_critical,
            desktop_inhibited=self._desktop_inhibited(),
        ):
            self._dispatch(request)

    def _desktop_inhibited(self) -> bool:
        """Ask the notification daemon whether the desktop is in DND.

        Complementary to the app's own DND: this is KDE's Do Not Disturb
        (or an active screen share).  Anything other than a literal
        ``True`` — no notifier, no D-Bus, property unsupported — counts as
        "not inhibited" so notifications keep working.
        """
        if self._notifier is None:
            return False
        query = getattr(self._notifier, "desktop_inhibited", None)
        if query is None:
            return False
        return query() is True

    def _dispatch(self, request: NotificationRequest) -> None:
        """Send one notification, preferring D-Bus when available."""
        if self._notifier is not None:
            self._notifier.notify(
                request.summary, request.body, request.severity,
                service_name=request.service_name,
                fingerprint=request.fingerprint,
                transient=request.transient,
                snooze_key=request.snooze_key,
            )
        else:
            icon = _SEVERITY_ICONS.get(
                request.severity, QSystemTrayIcon.MessageIcon.Information
            )
            timeout = _SEVERITY_TIMEOUT_MS.get(request.severity, 5000)
            self.showMessage(request.summary, request.body, icon, timeout)

        logger.debug("notification: [%s] %s", request.severity, request.summary)

    def on_service_action_complete(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Show a toast notification for a completed service action.

        These are pure feedback — marked ``transient`` so they never land
        in KDE's notification history.
        """
        if success:
            title = "Service Action"
            body = f"{service_name} {action}ed successfully"
            severity = "info"
        else:
            title = "Service Action Failed"
            body = f"{service_name} {action} failed: {message}"
            severity = "warning"

        if self._notifier is not None:
            self._notifier.notify(
                title, body, severity,
                fingerprint=f"service-action:{service_name}",
                transient=True,
            )
        else:
            icon = _SEVERITY_ICONS.get(
                severity, QSystemTrayIcon.MessageIcon.Information
            )
            timeout = _SEVERITY_TIMEOUT_MS.get(severity, 5000)
            self.showMessage(title, body, icon, timeout)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon clicks."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.popup_requested.emit()
