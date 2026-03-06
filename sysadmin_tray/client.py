"""Threaded HTTP client for polling the sysadmin-service API.

Architecture:
    - ``ApiWorker`` lives on a ``QThread`` and makes blocking ``httpx`` calls.
    - ``ApiClient`` lives on the main thread, owns the worker, and exposes
      Qt signals that the tray icon and popup connect to.
    - ``QTimer`` instances on the main thread trigger polls at configured
      intervals; the actual HTTP work runs off-thread so the UI never blocks.
"""

from __future__ import annotations

import logging

import httpx
from PyQt6.QtCore import QMutex, QObject, QThread, pyqtSignal, pyqtSlot

from sysadmin_tray.models import (
    AlertsResponse,
    LogStatsResponse,
    LogsResponse,
    ManagedProjectsResponse,
    ProjectOverviewResponse,
    ResourceHistoryResponse,
    ResourceResponse,
    ServiceDetailInfo,
    StatusResponse,
)

logger = logging.getLogger(__name__)


class ApiWorker(QObject):
    """Performs blocking HTTP requests on a background QThread."""

    status_ready = pyqtSignal(object)       # StatusResponse
    resources_ready = pyqtSignal(object)     # ResourceResponse
    alerts_ready = pyqtSignal(object)        # AlertsResponse
    connection_lost = pyqtSignal()
    connection_restored = pyqtSignal()
    scan_complete = pyqtSignal(bool, str)    # success, message
    service_action_complete = pyqtSignal(str, str, bool, str)  # name, action, success, msg
    alert_acknowledged = pyqtSignal(str, bool, str)            # alert_id, success, msg
    resource_history_ready = pyqtSignal(object)   # ResourceHistoryResponse
    logs_ready = pyqtSignal(object)               # LogsResponse
    log_stats_ready = pyqtSignal(object)          # LogStatsResponse
    managed_projects_ready = pyqtSignal(object)   # ManagedProjectsResponse
    project_overview_ready = pyqtSignal(object)   # ProjectOverviewResponse
    service_detail_ready = pyqtSignal(str, object)  # service_name, ServiceDetailInfo
    dnd_status_ready = pyqtSignal(object)            # dict (DND status)

    def __init__(self, api_url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._api_url = api_url.rstrip("/")
        self._client = httpx.Client(timeout=10.0)
        self._was_connected = False
        self._mutex = QMutex()

    # ── Fetch methods (called via signal from main thread) ───────────

    @pyqtSlot()
    def fetch_status(self) -> None:
        """GET /health + /api/sysadmin/status."""
        try:
            # Quick liveness check first
            self._client.get(f"{self._api_url}/health")

            resp = self._client.get(f"{self._api_url}/api/sysadmin/status")
            resp.raise_for_status()

            status = StatusResponse.from_dict(resp.json())
            self._on_connected()
            self.status_ready.emit(status)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("status fetch failed: %s", exc)
            self._on_disconnected()

    @pyqtSlot()
    def fetch_resources(self) -> None:
        """GET /api/sysadmin/resources."""
        try:
            resp = self._client.get(f"{self._api_url}/api/sysadmin/resources")
            resp.raise_for_status()

            resources = ResourceResponse.from_dict(resp.json())
            self._on_connected()
            self.resources_ready.emit(resources)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("resource fetch failed: %s", exc)
            self._on_disconnected()

    @pyqtSlot()
    def fetch_alerts(self) -> None:
        """GET /api/sysadmin/alerts?active_only=true."""
        try:
            resp = self._client.get(
                f"{self._api_url}/api/sysadmin/alerts",
                params={"active_only": "true"},
            )
            resp.raise_for_status()

            alerts = AlertsResponse.from_dict(resp.json())
            self._on_connected()
            self.alerts_ready.emit(alerts)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("alerts fetch failed: %s", exc)
            self._on_disconnected()

    @pyqtSlot()
    def trigger_scan(self) -> None:
        """POST /api/sysadmin/scan-all."""
        try:
            resp = self._client.post(f"{self._api_url}/api/sysadmin/scan-all")
            resp.raise_for_status()
            self.scan_complete.emit(True, "All scans triggered")
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            self.scan_complete.emit(False, str(exc))

    @pyqtSlot(str, str)
    def trigger_service_action(self, service_name: str, action: str) -> None:
        """POST /api/sysadmin/services/{service_name}/{action}."""
        try:
            resp = self._client.post(
                f"{self._api_url}/api/sysadmin/services/{service_name}/{action}"
            )
            resp.raise_for_status()
            data = resp.json()
            self.service_action_complete.emit(
                service_name, action, data.get("success", False), data.get("message", "")
            )
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            self.service_action_complete.emit(service_name, action, False, str(exc))

    @pyqtSlot(str)
    def acknowledge_alert(self, alert_id: str) -> None:
        """POST /api/sysadmin/alerts/{alert_id}/ack."""
        try:
            resp = self._client.post(
                f"{self._api_url}/api/sysadmin/alerts/{alert_id}/ack"
            )
            resp.raise_for_status()
            self.alert_acknowledged.emit(alert_id, True, "acknowledged")
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            self.alert_acknowledged.emit(alert_id, False, str(exc))

    @pyqtSlot(int)
    def fetch_resource_history(self, hours: int = 24) -> None:
        """GET /api/sysadmin/resources/history?hours=N."""
        try:
            resp = self._client.get(
                f"{self._api_url}/api/sysadmin/resources/history",
                params={"hours": hours},
            )
            resp.raise_for_status()
            history = ResourceHistoryResponse.from_dict(resp.json())
            self.resource_history_ready.emit(history)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("resource history fetch failed: %s", exc)

    @pyqtSlot(int, str, str)
    def fetch_logs(self, hours: int = 1, source: str = "", severity: str = "") -> None:
        """GET /api/logs/recent with optional filters."""
        try:
            params: dict = {"hours": hours, "limit": 200}
            if source:
                params["source"] = source
            if severity:
                params["severity"] = severity
            resp = self._client.get(
                f"{self._api_url}/api/logs/recent", params=params,
            )
            resp.raise_for_status()
            logs = LogsResponse.from_dict(resp.json())
            self.logs_ready.emit(logs)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("logs fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_log_stats(self) -> None:
        """GET /api/logs/stats."""
        try:
            resp = self._client.get(f"{self._api_url}/api/logs/stats")
            resp.raise_for_status()
            stats = LogStatsResponse.from_dict(resp.json())
            self.log_stats_ready.emit(stats)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("log stats fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_managed_projects(self) -> None:
        """GET /api/projects/managed."""
        try:
            resp = self._client.get(f"{self._api_url}/api/projects/managed")
            resp.raise_for_status()
            projects = ManagedProjectsResponse.from_dict(resp.json())
            self.managed_projects_ready.emit(projects)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("managed projects fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_project_overview(self) -> None:
        """GET /api/projects/overview."""
        try:
            resp = self._client.get(f"{self._api_url}/api/projects/overview")
            resp.raise_for_status()
            overview = ProjectOverviewResponse.from_dict(resp.json())
            self.project_overview_ready.emit(overview)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("project overview fetch failed: %s", exc)

    @pyqtSlot(str)
    def fetch_service_details(self, service_name: str) -> None:
        """GET /api/sysadmin/services/{service_name}/details."""
        try:
            resp = self._client.get(
                f"{self._api_url}/api/sysadmin/services/{service_name}/details"
            )
            resp.raise_for_status()
            detail = ServiceDetailInfo.from_dict(resp.json())
            self.service_detail_ready.emit(service_name, detail)
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("service detail fetch failed for %s: %s", service_name, exc)

    @pyqtSlot()
    def fetch_dnd_status(self) -> None:
        """GET /api/sysadmin/dnd."""
        try:
            resp = self._client.get(f"{self._api_url}/api/sysadmin/dnd")
            resp.raise_for_status()
            self.dnd_status_ready.emit(resp.json())
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("dnd status fetch failed: %s", exc)

    @pyqtSlot(object)
    def toggle_dnd(self, enabled: object) -> None:
        """POST /api/sysadmin/dnd with {enabled: bool|null}."""
        try:
            resp = self._client.post(
                f"{self._api_url}/api/sysadmin/dnd",
                json={"enabled": enabled},
            )
            resp.raise_for_status()
            self.dnd_status_ready.emit(resp.json())
        except (httpx.HTTPError, httpx.TimeoutException, OSError) as exc:
            logger.debug("dnd toggle failed: %s", exc)

    # ── Connection state tracking ────────────────────────────────────

    def _on_connected(self) -> None:
        self._mutex.lock()
        try:
            if not self._was_connected:
                self._was_connected = True
                self.connection_restored.emit()
        finally:
            self._mutex.unlock()

    def _on_disconnected(self) -> None:
        self._mutex.lock()
        try:
            if self._was_connected:
                self._was_connected = False
                self.connection_lost.emit()
        finally:
            self._mutex.unlock()

    def cleanup(self) -> None:
        """Close the httpx client."""
        self._client.close()


class ApiClient(QObject):
    """Main-thread controller that owns the worker thread.

    Connect to these signals from the UI:
        - ``status_updated(StatusResponse)``
        - ``resources_updated(ResourceResponse)``
        - ``alerts_updated(AlertsResponse)``
        - ``connection_lost()``
        - ``connection_restored()``
        - ``scan_complete(bool, str)``
    """

    # Re-emitted from worker (already auto-queued across threads)
    status_updated = pyqtSignal(object)
    resources_updated = pyqtSignal(object)
    alerts_updated = pyqtSignal(object)
    connection_lost = pyqtSignal()
    connection_restored = pyqtSignal()
    scan_complete = pyqtSignal(bool, str)
    service_action_complete = pyqtSignal(str, str, bool, str)  # name, action, ok, msg
    alert_acknowledged = pyqtSignal(str, bool, str)            # id, ok, msg

    # Dashboard signals (forwarded from worker)
    resource_history_updated = pyqtSignal(object)
    logs_updated = pyqtSignal(object)
    log_stats_updated = pyqtSignal(object)
    managed_projects_updated = pyqtSignal(object)
    project_overview_updated = pyqtSignal(object)
    service_detail_updated = pyqtSignal(str, object)  # service_name, ServiceDetailInfo
    dnd_status_updated = pyqtSignal(object)              # dict

    # Trigger signals (main→worker, queued connection)
    _request_status = pyqtSignal()
    _request_resources = pyqtSignal()
    _request_alerts = pyqtSignal()
    _request_scan = pyqtSignal()
    _request_service_action = pyqtSignal(str, str)
    _request_alert_ack = pyqtSignal(str)
    _request_resource_history = pyqtSignal(int)
    _request_logs = pyqtSignal(int, str, str)
    _request_log_stats = pyqtSignal()
    _request_managed_projects = pyqtSignal()
    _request_project_overview = pyqtSignal()
    _request_service_details = pyqtSignal(str)
    _request_dnd_status = pyqtSignal()
    _request_dnd_toggle = pyqtSignal(object)  # bool | None

    def __init__(self, api_url: str, parent: QObject | None = None) -> None:
        super().__init__(parent)

        self._thread = QThread(self)
        self._worker = ApiWorker(api_url)
        self._worker.moveToThread(self._thread)

        # Wire trigger signals → worker slots
        self._request_status.connect(self._worker.fetch_status)
        self._request_resources.connect(self._worker.fetch_resources)
        self._request_alerts.connect(self._worker.fetch_alerts)
        self._request_scan.connect(self._worker.trigger_scan)
        self._request_service_action.connect(self._worker.trigger_service_action)
        self._request_alert_ack.connect(self._worker.acknowledge_alert)
        self._request_resource_history.connect(self._worker.fetch_resource_history)
        self._request_logs.connect(self._worker.fetch_logs)
        self._request_log_stats.connect(self._worker.fetch_log_stats)
        self._request_managed_projects.connect(self._worker.fetch_managed_projects)
        self._request_project_overview.connect(self._worker.fetch_project_overview)
        self._request_service_details.connect(self._worker.fetch_service_details)
        self._request_dnd_status.connect(self._worker.fetch_dnd_status)
        self._request_dnd_toggle.connect(self._worker.toggle_dnd)

        # Forward worker results → our public signals
        self._worker.status_ready.connect(self.status_updated)
        self._worker.resources_ready.connect(self.resources_updated)
        self._worker.alerts_ready.connect(self.alerts_updated)
        self._worker.connection_lost.connect(self.connection_lost)
        self._worker.connection_restored.connect(self.connection_restored)
        self._worker.scan_complete.connect(self.scan_complete)
        self._worker.service_action_complete.connect(self.service_action_complete)
        self._worker.alert_acknowledged.connect(self.alert_acknowledged)
        self._worker.resource_history_ready.connect(self.resource_history_updated)
        self._worker.logs_ready.connect(self.logs_updated)
        self._worker.log_stats_ready.connect(self.log_stats_updated)
        self._worker.managed_projects_ready.connect(self.managed_projects_updated)
        self._worker.project_overview_ready.connect(self.project_overview_updated)
        self._worker.service_detail_ready.connect(self.service_detail_updated)
        self._worker.dnd_status_ready.connect(self.dnd_status_updated)

        self._thread.start()

    # ── Public API (call from main thread) ───────────────────────────

    def request_status(self) -> None:
        """Ask the worker to fetch status (non-blocking)."""
        self._request_status.emit()

    def request_resources(self) -> None:
        """Ask the worker to fetch resources (non-blocking)."""
        self._request_resources.emit()

    def request_alerts(self) -> None:
        """Ask the worker to fetch alerts (non-blocking)."""
        self._request_alerts.emit()

    def trigger_scan(self) -> None:
        """Ask the worker to POST scan-all (non-blocking)."""
        self._request_scan.emit()

    def trigger_service_action(self, service_name: str, action: str) -> None:
        """Ask the worker to POST a service action (non-blocking)."""
        self._request_service_action.emit(service_name, action)

    def acknowledge_alert(self, alert_id: str) -> None:
        """Ask the worker to POST an alert acknowledgement (non-blocking)."""
        self._request_alert_ack.emit(alert_id)

    def request_resource_history(self, hours: int = 24) -> None:
        """Ask the worker to fetch resource history (non-blocking)."""
        self._request_resource_history.emit(hours)

    def request_logs(self, hours: int = 1, source: str = "", severity: str = "") -> None:
        """Ask the worker to fetch logs with optional filters (non-blocking)."""
        self._request_logs.emit(hours, source, severity)

    def request_log_stats(self) -> None:
        """Ask the worker to fetch log statistics (non-blocking)."""
        self._request_log_stats.emit()

    def request_managed_projects(self) -> None:
        """Ask the worker to fetch managed projects (non-blocking)."""
        self._request_managed_projects.emit()

    def request_project_overview(self) -> None:
        """Ask the worker to fetch project overview (non-blocking)."""
        self._request_project_overview.emit()

    def request_service_details(self, service_name: str) -> None:
        """Ask the worker to fetch details for a specific service (non-blocking)."""
        self._request_service_details.emit(service_name)

    def request_dnd_status(self) -> None:
        """Ask the worker to fetch DND status (non-blocking)."""
        self._request_dnd_status.emit()

    def toggle_dnd(self, enabled: bool | None) -> None:
        """Ask the worker to toggle DND (non-blocking)."""
        self._request_dnd_toggle.emit(enabled)

    def shutdown(self) -> None:
        """Stop the worker thread cleanly."""
        self._worker.cleanup()
        self._thread.quit()
        self._thread.wait(3000)
