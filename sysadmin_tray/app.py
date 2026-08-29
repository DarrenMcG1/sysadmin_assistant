"""Application orchestrator — wires QTimers, ApiClient, TrayIcon, and Dashboard.

This is the entry point: ``sysadmin-tray`` console script calls ``main()``.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from sysadmin_tray.client import ApiClient
from sysadmin_tray.config import TrayConfig, load_tray_config
from sysadmin_tray.dashboard.files_tab import FilesTab
from sysadmin_tray.dashboard.logs_tab import LogsTab
from sysadmin_tray.dashboard.overview_tab import OverviewTab
from sysadmin_tray.dashboard.projects_tab import ProjectsTab
from sysadmin_tray.dashboard.services_tab import ServicesTab
from sysadmin_tray.dashboard.window import DashboardWindow
from sysadmin_tray.notifications import DbusNotifier
from sysadmin_tray.tray_icon import TrayIcon

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
    """Orchestrates the tray icon, dashboard, API client, and timers."""

    def __init__(self, config: TrayConfig) -> None:
        self._config = config

        # API client (owns the worker thread)
        self._client = ApiClient(
            config.api_url,
            auth_token=config.auth_token,
            estate_api_url=config.estate_api_url,
        )

        # UI components
        self._tray = TrayIcon()
        self._dashboard = DashboardWindow(self._client)
        self._dashboard.add_tab(OverviewTab(self._client), "Overview")
        self._dashboard.add_tab(ServicesTab(self._client), "Services")
        self._dashboard.add_tab(LogsTab(self._client), "Logs")
        self._dashboard.add_tab(ProjectsTab(self._client), "Projects")
        self._dashboard.add_tab(FilesTab(self._client), "Files")

        # D-Bus notifier with fallback to tray showMessage()
        self._notifier = DbusNotifier(
            fallback_tray=self._tray, snooze_minutes=config.snooze_minutes,
        )
        self._tray.set_notifier(self._notifier)

        self._wire_signals()
        self._setup_timers()

        # Configure desktop notifications from config
        self._tray.set_notification_config(
            enabled=config.show_notifications,
            min_severity=config.notify_min_severity,
            flap_cooldown_minutes=config.flap_cooldown_minutes,
            escalation_polls=config.escalation_polls,
            coalesce_threshold=config.coalesce_threshold,
            snooze_minutes=config.snooze_minutes,
            digest_mode=config.digest_mode,
            digest_interval_minutes=config.digest_interval_minutes,
            respect_desktop_dnd=config.respect_desktop_dnd,
            reminder_hours=config.reminder_hours,
            backend_unreachable_grace_seconds=(
                config.backend_unreachable_grace_seconds
            ),
            muted_services=config.muted_services,
        )

    def _wire_signals(self) -> None:
        """Connect all signals between components."""
        client = self._client
        tray = self._tray

        # ApiClient → TrayIcon
        client.status_updated.connect(tray.update_from_status)
        client.alerts_updated.connect(tray.update_from_alerts)
        client.connection_lost.connect(tray.on_connection_lost)
        client.connection_restored.connect(tray.on_connection_restored)
        client.backend_unreachable.connect(tray.on_backend_unreachable)

        # TrayIcon → Dashboard (left click opens main dashboard)
        tray.popup_requested.connect(self._open_dashboard)

        # TrayIcon → Quit
        tray.quit_requested.connect(self._quit)

        # TrayIcon menu → Dashboard
        tray.dashboard_requested.connect(self._open_dashboard)

        # Service action feedback → tray notification
        client.service_action_complete.connect(
            tray.on_service_action_complete
        )

        # Refresh status after any service action
        client.service_action_complete.connect(self._on_service_action_done)

        # DND: backend → tray, tray → backend
        client.dnd_status_updated.connect(tray.update_dnd_status)
        tray.dnd_toggled.connect(client.toggle_dnd)

        # D-Bus notification restart action → API restart
        self._notifier.restart_requested.connect(self._on_notification_restart)

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
        self._alert_timer.timeout.connect(self._client.request_dnd_status)

    def start(self) -> None:
        """Show the tray icon and start polling."""
        self._tray.show()

        # Fire immediate polls then start timers
        self._client.request_status()
        self._client.request_resources()
        self._client.request_alerts()
        self._client.request_dnd_status()

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
        self._notifier.cleanup()
        self._client.shutdown()

    # ── Service action feedback ───────────────────────────────────

    def _on_service_action_done(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Refresh service status after a service action completes."""
        if success:
            self._client.request_status()

    # ── Notification actions ────────────────────────────────────────

    def _on_notification_restart(self, service_name: str) -> None:
        """Handle restart request from D-Bus notification action button."""
        logger.info("restart via notification: %s", service_name)
        self._client.trigger_service_action(service_name, "restart")

    # ── Actions ──────────────────────────────────────────────────────

    def _open_dashboard(self) -> None:
        """Toggle the native dashboard window."""
        self._dashboard.toggle_visibility()

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
