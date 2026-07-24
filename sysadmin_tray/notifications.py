"""D-Bus desktop notifications with action button support.

Uses ``org.freedesktop.Notifications`` for native KDE integration:
  - Action buttons (e.g. "Restart" on service-failure alerts)
  - Urgency hints (low / normal / critical)
  - Proper notification history in KDE's notification centre

Falls back to ``QSystemTrayIcon.showMessage()`` when D-Bus is unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QMetaType, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import (
    QDBusArgument,
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
    QDBusReply,
)
from PyQt6.QtWidgets import QSystemTrayIcon

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_DBUS_SERVICE = "org.freedesktop.Notifications"
_DBUS_PATH = "/org/freedesktop/Notifications"
_DBUS_IFACE = "org.freedesktop.Notifications"

# Map severity → D-Bus urgency hint (0 = low, 1 = normal, 2 = critical)
_URGENCY_MAP: dict[str, int] = {
    "info": 0,
    "warning": 1,
    "critical": 2,
}

# Map severity → notification timeout in ms (0 = persistent)
_TIMEOUT_MAP: dict[str, int] = {
    "info": 5000,
    "warning": 10000,
    "critical": 0,
}

# Fallback QSystemTrayIcon message icons
_FALLBACK_ICONS: dict[str, QSystemTrayIcon.MessageIcon] = {
    "info": QSystemTrayIcon.MessageIcon.Information,
    "warning": QSystemTrayIcon.MessageIcon.Warning,
    "critical": QSystemTrayIcon.MessageIcon.Critical,
}


class DbusNotifier(QObject):
    """D-Bus notification helper with action button support.

    Emits ``restart_requested(service_name)`` when the user clicks
    a "Restart" action button on a notification.
    """

    restart_requested = pyqtSignal(str)  # service_name

    def __init__(
        self,
        fallback_tray: QSystemTrayIcon | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._fallback_tray = fallback_tray
        self._pending_actions: dict[int, str] = {}  # notification_id → service_name
        self._available = False
        self._bus: QDBusConnection | None = None
        self._iface: QDBusInterface | None = None

        self._init_dbus()

    def _init_dbus(self) -> None:
        """Connect to the session bus and create the notifications interface."""
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            logger.warning("D-Bus session bus not connected — using fallback")
            return

        self._bus = bus
        self._iface = QDBusInterface(
            _DBUS_SERVICE, _DBUS_PATH, _DBUS_IFACE, bus,
        )
        if not self._iface.isValid():
            logger.warning(
                "D-Bus notifications interface unavailable — using fallback"
            )
            self._iface = None
            return

        # Subscribe to ActionInvoked and NotificationClosed signals
        bus.connect(
            _DBUS_SERVICE,
            _DBUS_PATH,
            _DBUS_IFACE,
            "ActionInvoked",
            self._on_action_invoked,
        )
        bus.connect(
            _DBUS_SERVICE,
            _DBUS_PATH,
            _DBUS_IFACE,
            "NotificationClosed",
            self._on_notification_closed,
        )

        self._available = True
        logger.debug("D-Bus notifications initialised")

    @property
    def available(self) -> bool:
        """Whether D-Bus notifications are available."""
        return self._available

    def notify(
        self,
        summary: str,
        body: str,
        severity: str = "info",
        service_name: str | None = None,
    ) -> bool:
        """Send a desktop notification.

        Returns True if sent via D-Bus, False if fell back to showMessage().
        When *service_name* is provided, adds a "Restart" action button.
        """
        if not self._available or self._iface is None:
            self._fallback_notify(summary, body, severity)
            return False

        # Build actions list: pairs of (action_key, display_label)
        actions: list[str] = []
        if service_name:
            actions = ["restart", "Restart"]

        urgency = _URGENCY_MAP.get(severity, 1)
        timeout = _TIMEOUT_MAP.get(severity, 5000)

        # Build a typed D-Bus message matching signature: susssasa{sv}i
        # QDBusInterface.call() infers INT32 from Python int and
        # array-of-variant from Python list — both wrong for Notify.
        msg = QDBusMessage.createMethodCall(
            _DBUS_SERVICE, _DBUS_PATH, _DBUS_IFACE, "Notify",
        )

        # PyQt6 strict enums: .value converts Type enum → int for add()/beginArray()
        uint_type = QMetaType.Type.UInt.value
        qstring_type = QMetaType.Type.QString.value

        # replaces_id must be UINT32 (not INT32)
        replaces_arg = QDBusArgument()
        replaces_arg.add(0, uint_type)

        # actions must be array-of-string (not array-of-variant)
        actions_arg = QDBusArgument()
        actions_arg.beginArray(qstring_type)
        for action in actions:
            actions_arg.add(action)
        actions_arg.endArray()

        # hints as plain dict — Qt auto-marshals dict[str, QVariant] → a{sv}
        hints: dict[str, QVariant] = {"urgency": QVariant(urgency)}

        msg.setArguments([
            "SysAdmin Monitor",           # app_name:       s
            QVariant(replaces_arg),        # replaces_id:    u
            "dialog-warning",              # app_icon:       s
            summary,                       # summary:        s
            body,                          # body:           s
            QVariant(actions_arg),         # actions:        as
            QVariant(hints),               # hints:          a{sv}
            timeout,                       # expire_timeout: i
        ])

        reply_msg = self._bus.call(msg)

        reply = QDBusReply(reply_msg)
        if not reply.isValid():
            logger.warning(
                "D-Bus Notify call failed: %s — using fallback",
                reply.error().message(),
            )
            self._fallback_notify(summary, body, severity)
            return False

        notification_id = reply.value()
        logger.debug(
            "D-Bus notification %d: [%s] %s", notification_id, severity, summary,
        )

        # Track pending action if we offered a restart button
        if service_name and notification_id:
            self._pending_actions[notification_id] = service_name

        return True

    def _fallback_notify(
        self, summary: str, body: str, severity: str,
    ) -> None:
        """Fall back to QSystemTrayIcon.showMessage()."""
        if self._fallback_tray is None:
            logger.debug("no fallback tray — notification dropped: %s", summary)
            return

        icon = _FALLBACK_ICONS.get(severity, QSystemTrayIcon.MessageIcon.Information)
        timeout = _TIMEOUT_MAP.get(severity, 5000)
        self._fallback_tray.showMessage(summary, body, icon, timeout)

    @pyqtSlot(int, str)
    def _on_action_invoked(self, notification_id: int, action_key: str) -> None:
        """Handle D-Bus ActionInvoked signal."""
        service_name = self._pending_actions.pop(notification_id, None)
        if service_name and action_key == "restart":
            logger.info(
                "restart requested via notification for %s", service_name,
            )
            self.restart_requested.emit(service_name)

    @pyqtSlot(int, int)
    def _on_notification_closed(self, notification_id: int, reason: int) -> None:
        """Handle D-Bus NotificationClosed signal — clean up pending actions."""
        self._pending_actions.pop(notification_id, None)

    def cleanup(self) -> None:
        """Release D-Bus resources."""
        self._pending_actions.clear()
        self._iface = None
        self._available = False
