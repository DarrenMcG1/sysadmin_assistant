"""Application orchestrator — wires QTimers, ApiClient, TrayIcon, and Popup.

This is the entry point: ``sysadmin-tray`` console script calls ``main()``.
"""

from __future__ import annotations

import argparse
import logging
import sys
import webbrowser
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from sysadmin_tray.client import ApiClient
from sysadmin_tray.config import TrayConfig, load_tray_config
from sysadmin_tray.models import (
    AlertInfo,
    AlertsResponse,
    StatusResponse,
    compute_icon_state,
)
from sysadmin_tray.popup import StatsPopup
from sysadmin_tray.tray_icon import TrayIcon
from sysadmin_tray.widgets.alert_dialog import CriticalAlertDialog

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SysAdmin system tray monitor")
    parser.add_argument(
        "--api-url",
        help="Override the backend API URL (e.g. http://192.168.1.10:8500)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config.yaml (default: auto-detect)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


class TrayApp:
    """Orchestrates the tray icon, popup, API client, and timers."""

    def __init__(self, config: TrayConfig) -> None:
        self._config = config

        # API client (owns the worker thread)
        self._client = ApiClient(config.api_url)

        # UI components
        self._tray = TrayIcon()
        self._popup = StatsPopup()
        self._alert_dialog = CriticalAlertDialog()

        # Track current state for popup status dot
        self._last_status: StatusResponse | None = None
        self._last_alerts: AlertsResponse | None = None
        self._previous_critical_ids: set[str] = set()
        self._backend_reachable = False

        self._wire_signals()
        self._setup_timers()

        # Configure desktop notifications from config
        self._tray.set_notification_config(
            enabled=config.show_notifications,
            min_severity=config.notify_min_severity,
        )

    def _wire_signals(self) -> None:
        """Connect all signals between components."""
        client = self._client
        tray = self._tray
        popup = self._popup

        # ApiClient → TrayIcon
        client.status_updated.connect(tray.update_from_status)
        client.alerts_updated.connect(tray.update_from_alerts)
        client.connection_lost.connect(tray.on_connection_lost)
        client.connection_restored.connect(tray.on_connection_restored)

        # ApiClient → Popup
        client.status_updated.connect(popup.update_services)
        client.resources_updated.connect(popup.update_resources)
        client.alerts_updated.connect(popup.update_alerts)

        # ApiClient → self (track state for popup dot)
        client.status_updated.connect(self._on_status_updated)
        client.alerts_updated.connect(self._on_alerts_updated)
        client.connection_lost.connect(self._on_connection_lost)
        client.connection_restored.connect(self._on_connection_restored)

        # ApiClient → ActionBar (scan feedback)
        client.scan_complete.connect(popup.action_bar.on_scan_complete)

        # TrayIcon → Popup toggle
        tray.popup_requested.connect(self._toggle_popup)

        # TrayIcon → Quit
        tray.quit_requested.connect(self._quit)

        # TrayIcon / Popup → Dashboard
        tray.dashboard_requested.connect(self._open_dashboard)
        popup.action_bar.dashboard_requested.connect(self._open_dashboard)

        # ActionBar → ApiClient (scan trigger)
        popup.action_bar.scan_requested.connect(client.trigger_scan)

        # Service management: grid → client → grid + tray
        popup.service_grid.service_action_requested.connect(
            client.trigger_service_action
        )
        client.service_action_complete.connect(
            popup.service_grid.on_action_complete
        )
        client.service_action_complete.connect(
            tray.on_service_action_complete
        )

        # Critical alert dialog
        alert_dialog = self._alert_dialog
        tray.critical_alerts_changed.connect(self._on_critical_alerts_changed)
        alert_dialog.alert_ack_requested.connect(client.acknowledge_alert)
        client.alert_acknowledged.connect(alert_dialog.on_alert_acknowledged)

    def _setup_timers(self) -> None:
        """Create polling timers with configured intervals."""
        cfg = self._config

        self._status_timer = QTimer()
        self._status_timer.setInterval(cfg.status_poll_seconds * 1000)
        self._status_timer.timeout.connect(self._client.request_status)

        self._resource_timer = QTimer()
        self._resource_timer.setInterval(cfg.resource_poll_seconds * 1000)
        self._resource_timer.timeout.connect(self._client.request_resources)

        self._alert_timer = QTimer()
        self._alert_timer.setInterval(cfg.alert_poll_seconds * 1000)
        self._alert_timer.timeout.connect(self._client.request_alerts)

    def start(self) -> None:
        """Show the tray icon and start polling."""
        self._tray.show()

        # Fire immediate polls then start timers
        self._client.request_status()
        self._client.request_resources()
        self._client.request_alerts()

        self._status_timer.start()
        self._resource_timer.start()
        self._alert_timer.start()

        logger.info(
            "tray started — polling %s (status=%ds, resources=%ds, alerts=%ds)",
            self._config.api_url,
            self._config.status_poll_seconds,
            self._config.resource_poll_seconds,
            self._config.alert_poll_seconds,
        )

    def stop(self) -> None:
        """Clean up timers and threads."""
        self._status_timer.stop()
        self._resource_timer.stop()
        self._alert_timer.stop()
        self._client.shutdown()

    # ── State tracking for popup status dot ──────────────────────────

    def _on_status_updated(self, status: StatusResponse) -> None:
        self._last_status = status
        self._backend_reachable = True
        self._update_popup_dot()

    def _on_alerts_updated(self, alerts: AlertsResponse) -> None:
        self._last_alerts = alerts
        self._update_popup_dot()

    def _on_connection_lost(self) -> None:
        self._backend_reachable = False
        self._update_popup_dot()

    def _on_connection_restored(self) -> None:
        self._backend_reachable = True
        self._update_popup_dot()

    def _update_popup_dot(self) -> None:
        state = compute_icon_state(
            self._last_status, self._last_alerts, self._backend_reachable
        )
        self._popup.update_status_dot(state)

    # ── Critical alert dialog ────────────────────────────────────────

    def _on_critical_alerts_changed(self, alerts: list[AlertInfo]) -> None:
        """Update the persistent critical alert dialog."""
        self._alert_dialog.update_alerts(alerts)

        # Show the dialog if new criticals appeared
        current_ids = {a.id for a in alerts}
        new_ids = current_ids - self._previous_critical_ids
        self._previous_critical_ids = current_ids

        if new_ids and alerts:
            self._alert_dialog.show()
            self._alert_dialog.raise_()

    # ── Actions ──────────────────────────────────────────────────────

    def _toggle_popup(self) -> None:
        """Position the popup near the tray icon and toggle visibility."""
        geo = self._tray.geometry()
        if geo.isValid():
            anchor = geo.center()
        else:
            # Fallback: bottom-right of primary screen
            screen = QApplication.primaryScreen()
            if screen:
                sg = screen.availableGeometry()
                anchor = sg.bottomRight()
            else:
                anchor = None

        self._popup.toggle_visibility(anchor)

    def _open_dashboard(self) -> None:
        """Open the dashboard URL in the default browser."""
        url = self._config.dashboard_url
        if url:
            webbrowser.open(url)
        else:
            # Default to the API docs
            webbrowser.open(f"{self._config.api_url}/docs")

    def _quit(self) -> None:
        """Clean shutdown."""
        self.stop()
        QApplication.instance().quit()


def main() -> None:
    """Entry point for the ``sysadmin-tray`` console script."""
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )

    config = load_tray_config(
        config_path=args.config,
        api_url_override=args.api_url,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("SysAdmin Tray")
    app.setQuitOnLastWindowClosed(False)

    tray_app = TrayApp(config)
    tray_app.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
