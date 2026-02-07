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
    ResourceResponse,
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

    # Trigger signals (main→worker, queued connection)
    _request_status = pyqtSignal()
    _request_resources = pyqtSignal()
    _request_alerts = pyqtSignal()
    _request_scan = pyqtSignal()
    _request_service_action = pyqtSignal(str, str)
    _request_alert_ack = pyqtSignal(str)

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

        # Forward worker results → our public signals
        self._worker.status_ready.connect(self.status_updated)
        self._worker.resources_ready.connect(self.resources_updated)
        self._worker.alerts_ready.connect(self.alerts_updated)
        self._worker.connection_lost.connect(self.connection_lost)
        self._worker.connection_restored.connect(self.connection_restored)
        self._worker.scan_complete.connect(self.scan_complete)
        self._worker.service_action_complete.connect(self.service_action_complete)
        self._worker.alert_acknowledged.connect(self.alert_acknowledged)

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

    def shutdown(self) -> None:
        """Stop the worker thread cleanly."""
        self._worker.cleanup()
        self._thread.quit()
        self._thread.wait(3000)
