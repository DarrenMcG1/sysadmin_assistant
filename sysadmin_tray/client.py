"""Threaded HTTP client for polling the sysadmin-service API.

Architecture:
    - ``ApiWorker`` lives on a ``QThread`` and makes blocking ``httpx`` calls.
    - ``ApiClient`` lives on the main thread, owns the worker, and exposes
      Qt signals that the tray icon and dashboard connect to.
    - ``QTimer`` instances on the main thread trigger polls at configured
      intervals; the actual HTTP work runs off-thread so the UI never blocks.

Error handling:
    Fetch paths catch ``ValueError``/``TypeError`` alongside the transport
    errors so a non-JSON body or an unexpected payload shape marks the
    connection lost instead of silently freezing on stale data
    (SNAG-TRAY-005).
"""

from __future__ import annotations

import logging
import time

import httpx
from PyQt6.QtCore import QMutex, QObject, QThread, pyqtSignal, pyqtSlot

from sysadmin_tray.models import (
    AlertsResponse,
    CleanResultResponse,
    DuplicatesResponse,
    FileStatusResponse,
    FileTrendsResponse,
    LargeFilesResponse,
    LogsResponse,
    LogStatsResponse,
    ManagedProjectsResponse,
    MisplacedFilesResponse,
    ProjectDetailResponse,
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
    #: every failed status poll, carrying the unreachable episode's age in
    #: seconds.  ``connection_lost`` opens the episode and says nothing
    #: about how long it has run; the grace period in
    #: :class:`~sysadmin_tray.notifications.NotificationPolicy` needs a
    #: repeating tick, and while the backend is down the status poll is
    #: the only tick that still fires — every other surface the tray
    #: reads is served by the process that has died.
    backend_unreachable = pyqtSignal(float)  # seconds since the episode opened
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
    project_detail_ready = pyqtSignal(str, object)   # project_name, ProjectDetailResponse
    file_status_ready = pyqtSignal(object)           # FileStatusResponse
    file_duplicates_ready = pyqtSignal(object)       # DuplicatesResponse
    file_large_ready = pyqtSignal(object)            # LargeFilesResponse
    file_misplaced_ready = pyqtSignal(object)        # MisplacedFilesResponse
    file_trends_ready = pyqtSignal(object)           # FileTrendsResponse
    file_fetch_failed = pyqtSignal(str, str)         # what, message
    file_scan_triggered = pyqtSignal(bool, str)      # success, message
    stale_caches_cleaned = pyqtSignal(bool, str)     # success, message

    def __init__(
        self,
        api_url: str,
        auth_token: str | None = None,
        estate_api_url: str = "http://127.0.0.1:8400",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._api_url = api_url.rstrip("/")
        # Project state moved to the estate's 8400 service at the Session 4
        # cutover (ADR-0005): /api/projects/overview and /api/projects/{name}
        # are served there now; /api/projects/managed stays on api_url.
        self._estate_api_url = estate_api_url.rstrip("/")
        # Send the bearer token on every request (only mutating endpoints
        # require it, but sending it everywhere is harmless and simpler).
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self._client = httpx.Client(timeout=10.0, headers=headers)
        # Tri-state, and the third state is the whole of SNAG-TRAY-009's
        # first face.  ``False`` used to be the initial value, so a tray
        # that started against an already-dead backend had "never
        # connected" and "was connected and then lost it" spelled the same
        # way — and :meth:`_on_disconnected` only spoke for the second.
        # That is not an edge case here: ``graphical-session.target`` is
        # reached long after a boot-time failure, so *starting* against a
        # dead daemon is the common shape.  Measured across the
        # 2026-08-22/23 outage, both silent sessions (5h 04m and 17h 09m)
        # were arrivals and every window this signal did fire on was a
        # 60-second deploy restart — the signal fired only on noise and
        # never once on a fault.
        #
        #   None  — nothing observed yet
        #   True  — the last observation reached the backend
        #   False — the last observation did not
        self._was_connected: bool | None = None
        #: monotonic start of the current unreachable episode, or ``None``
        #: when the backend is reachable.  Monotonic rather than wall
        #: clock for ``TrayPresence``'s reason: it does not advance across
        #: a suspend, and a suspended box is one where neither this
        #: process nor the daemon nor the human was running, so it
        #: correctly counts nothing towards the grace period.
        self._unreachable_since: float | None = None
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("status fetch failed: %s", exc)
            # Only the status poll carries the tick.  Every fetch method
            # calls ``_on_disconnected`` so the episode clock starts at
            # whichever request failed first, but the tick is emitted from
            # one of them: the cadence a grace period is measured against
            # must be a single interval the operator can name, and the
            # others (resources, alerts, dashboard tabs) fire on their own
            # timers or on a click.
            self.backend_unreachable.emit(self._on_disconnected())

    @pyqtSlot()
    def fetch_resources(self) -> None:
        """GET /api/sysadmin/resources."""
        try:
            resp = self._client.get(f"{self._api_url}/api/sysadmin/resources")
            resp.raise_for_status()

            resources = ResourceResponse.from_dict(resp.json())
            self._on_connected()
            self.resources_ready.emit(resources)
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("alerts fetch failed: %s", exc)
            self._on_disconnected()

    @pyqtSlot()
    def trigger_scan(self) -> None:
        """POST /api/sysadmin/scan-all."""
        try:
            resp = self._client.post(f"{self._api_url}/api/sysadmin/scan-all")
            resp.raise_for_status()
            self.scan_complete.emit(True, "All scans triggered")
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("logs fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_log_stats(self) -> None:
        """GET /api/logs/stats."""
        try:
            resp = self._client.get(f"{self._api_url}/api/logs/stats")
            resp.raise_for_status()
            stats = LogStatsResponse.from_dict(resp.json())
            self.log_stats_ready.emit(stats)
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("log stats fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_managed_projects(self) -> None:
        """GET /api/projects/managed."""
        try:
            resp = self._client.get(f"{self._api_url}/api/projects/managed")
            resp.raise_for_status()
            projects = ManagedProjectsResponse.from_dict(resp.json())
            self.managed_projects_ready.emit(projects)
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("managed projects fetch failed: %s", exc)

    @pyqtSlot()
    def fetch_project_overview(self) -> None:
        """GET /api/projects/overview — from the estate's 8400 service."""
        try:
            resp = self._client.get(f"{self._estate_api_url}/api/projects/overview")
            resp.raise_for_status()
            overview = ProjectOverviewResponse.from_dict(resp.json())
            self.project_overview_ready.emit(overview)
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("project overview fetch failed: %s", exc)

    @pyqtSlot(str, int)
    def fetch_project_detail(self, project_name: str, limit: int = 30) -> None:
        """GET /api/projects/{name}?limit=N — from the estate's 8400 service."""
        try:
            resp = self._client.get(
                f"{self._estate_api_url}/api/projects/{project_name}",
                params={"limit": limit},
            )
            resp.raise_for_status()
            detail = ProjectDetailResponse.from_dict(resp.json())
            self.project_detail_ready.emit(project_name, detail)
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("project detail fetch failed for %s: %s", project_name, exc)
            self.project_detail_ready.emit(project_name, None)

    # ── File organiser (read-only) ───────────────────────────────────

    def _fetch_file_endpoint(self, what: str, path: str, model, signal) -> None:
        """Shared GET path for the /api/files/* read endpoints.

        A 404 means "no audit data yet" (the scan has never run), which
        is a legitimate empty state rather than a failure — emit a
        default-constructed model so the tab can say so.  Everything
        else is reported through ``file_fetch_failed``.
        """
        try:
            resp = self._client.get(f"{self._api_url}{path}")
            if resp.status_code == 404:
                signal.emit(model.from_dict({}))
                return
            resp.raise_for_status()
            signal.emit(model.from_dict(resp.json()))
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("%s fetch failed: %s", what, exc)
            self.file_fetch_failed.emit(what, str(exc))

    @pyqtSlot()
    def fetch_file_status(self) -> None:
        """GET /api/files/status."""
        self._fetch_file_endpoint(
            "status", "/api/files/status", FileStatusResponse, self.file_status_ready
        )

    @pyqtSlot()
    def fetch_file_duplicates(self) -> None:
        """GET /api/files/duplicates."""
        self._fetch_file_endpoint(
            "duplicates",
            "/api/files/duplicates",
            DuplicatesResponse,
            self.file_duplicates_ready,
        )

    @pyqtSlot()
    def fetch_file_large(self) -> None:
        """GET /api/files/large."""
        self._fetch_file_endpoint(
            "large files", "/api/files/large", LargeFilesResponse, self.file_large_ready
        )

    @pyqtSlot()
    def fetch_file_misplaced(self) -> None:
        """GET /api/files/misplaced."""
        self._fetch_file_endpoint(
            "misplaced files",
            "/api/files/misplaced",
            MisplacedFilesResponse,
            self.file_misplaced_ready,
        )

    @pyqtSlot()
    def fetch_file_trends(self) -> None:
        """GET /api/files/trends."""
        self._fetch_file_endpoint(
            "trends", "/api/files/trends", FileTrendsResponse, self.file_trends_ready
        )

    @pyqtSlot()
    def trigger_file_scan(self) -> None:
        """POST /api/files/scan — non-destructive re-audit of the filesystem."""
        try:
            resp = self._client.post(f"{self._api_url}/api/files/scan")
            resp.raise_for_status()
            self.file_scan_triggered.emit(True, "Filesystem scan triggered")
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            self.file_scan_triggered.emit(False, str(exc))

    @pyqtSlot()
    def clean_stale_caches(self) -> None:
        """POST /api/files/clean/stale-caches?confirm=true.

        Only ever called after the UI has shown the user exactly what
        will be removed and they have confirmed.
        """
        try:
            resp = self._client.post(
                f"{self._api_url}/api/files/clean/stale-caches",
                params={"confirm": "true"},
            )
            resp.raise_for_status()
            result = CleanResultResponse.from_dict(resp.json())
            if result.status == "cleaned":
                self.stale_caches_cleaned.emit(
                    True,
                    f"Removed {result.removed_caches} caches, "
                    f"{result.removed_empty_dirs} empty dirs",
                )
            else:
                self.stale_caches_cleaned.emit(
                    False, result.message or result.status or "Nothing was cleaned"
                )
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            self.stale_caches_cleaned.emit(False, str(exc))

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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("service detail fetch failed for %s: %s", service_name, exc)

    @pyqtSlot()
    def fetch_dnd_status(self) -> None:
        """GET /api/sysadmin/dnd."""
        try:
            resp = self._client.get(f"{self._api_url}/api/sysadmin/dnd")
            resp.raise_for_status()
            self.dnd_status_ready.emit(resp.json())
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
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
        except (httpx.HTTPError, httpx.TimeoutException, OSError, ValueError, TypeError) as exc:
            logger.debug("dnd toggle failed: %s", exc)

    # ── Connection state tracking ────────────────────────────────────

    def _on_connected(self) -> None:
        self._mutex.lock()
        try:
            self._unreachable_since = None
            if self._was_connected is not True:
                self._was_connected = True
                self.connection_restored.emit()
        finally:
            self._mutex.unlock()

    def _on_disconnected(self) -> float:
        """Record a failed reach and return the episode's age in seconds.

        ``is not False`` rather than the old truthiness test: ``None``
        means nothing has been observed yet, and a first observation that
        fails is news exactly as a transition is.  See
        :attr:`_was_connected` for why that is the population that
        matters rather than an edge case.

        The returned age is what :meth:`fetch_status` carries on
        ``backend_unreachable``.  It is computed here so the episode's
        start and its age are read under one lock — two callers asking
        the clock separately could disagree about the same episode.
        """
        self._mutex.lock()
        try:
            if self._unreachable_since is None:
                self._unreachable_since = time.monotonic()
            age = time.monotonic() - self._unreachable_since
            if self._was_connected is not False:
                self._was_connected = False
                self.connection_lost.emit()
            return age
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
        - ``backend_unreachable(float)``
        - ``scan_complete(bool, str)``
    """

    # Re-emitted from worker (already auto-queued across threads)
    status_updated = pyqtSignal(object)
    resources_updated = pyqtSignal(object)
    alerts_updated = pyqtSignal(object)
    connection_lost = pyqtSignal()
    connection_restored = pyqtSignal()
    backend_unreachable = pyqtSignal(float)  # seconds since the episode opened
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
    project_detail_updated = pyqtSignal(str, object)  # project_name, ProjectDetailResponse
    file_status_updated = pyqtSignal(object)          # FileStatusResponse
    file_duplicates_updated = pyqtSignal(object)      # DuplicatesResponse
    file_large_updated = pyqtSignal(object)           # LargeFilesResponse
    file_misplaced_updated = pyqtSignal(object)       # MisplacedFilesResponse
    file_trends_updated = pyqtSignal(object)          # FileTrendsResponse
    file_fetch_failed = pyqtSignal(str, str)          # what, message
    file_scan_triggered = pyqtSignal(bool, str)       # success, message
    stale_caches_cleaned = pyqtSignal(bool, str)      # success, message

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
    _request_project_detail = pyqtSignal(str, int)
    _request_file_status = pyqtSignal()
    _request_file_duplicates = pyqtSignal()
    _request_file_large = pyqtSignal()
    _request_file_misplaced = pyqtSignal()
    _request_file_trends = pyqtSignal()
    _request_file_scan = pyqtSignal()
    _request_stale_cache_clean = pyqtSignal()

    def __init__(
        self,
        api_url: str,
        auth_token: str | None = None,
        estate_api_url: str = "http://127.0.0.1:8400",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._thread = QThread(self)
        self._worker = ApiWorker(
            api_url, auth_token=auth_token, estate_api_url=estate_api_url
        )
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
        self._request_project_detail.connect(self._worker.fetch_project_detail)
        self._request_file_status.connect(self._worker.fetch_file_status)
        self._request_file_duplicates.connect(self._worker.fetch_file_duplicates)
        self._request_file_large.connect(self._worker.fetch_file_large)
        self._request_file_misplaced.connect(self._worker.fetch_file_misplaced)
        self._request_file_trends.connect(self._worker.fetch_file_trends)
        self._request_file_scan.connect(self._worker.trigger_file_scan)
        self._request_stale_cache_clean.connect(self._worker.clean_stale_caches)

        # Forward worker results → our public signals
        self._worker.status_ready.connect(self.status_updated)
        self._worker.resources_ready.connect(self.resources_updated)
        self._worker.alerts_ready.connect(self.alerts_updated)
        self._worker.connection_lost.connect(self.connection_lost)
        self._worker.connection_restored.connect(self.connection_restored)
        self._worker.backend_unreachable.connect(self.backend_unreachable)
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
        self._worker.project_detail_ready.connect(self.project_detail_updated)
        self._worker.file_status_ready.connect(self.file_status_updated)
        self._worker.file_duplicates_ready.connect(self.file_duplicates_updated)
        self._worker.file_large_ready.connect(self.file_large_updated)
        self._worker.file_misplaced_ready.connect(self.file_misplaced_updated)
        self._worker.file_trends_ready.connect(self.file_trends_updated)
        self._worker.file_fetch_failed.connect(self.file_fetch_failed)
        self._worker.file_scan_triggered.connect(self.file_scan_triggered)
        self._worker.stale_caches_cleaned.connect(self.stale_caches_cleaned)

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

    def request_project_detail(self, project_name: str, limit: int = 30) -> None:
        """Ask the worker to fetch one project's snapshot history (non-blocking)."""
        self._request_project_detail.emit(project_name, limit)

    def request_file_status(self) -> None:
        """Ask the worker to fetch the filesystem audit summary (non-blocking)."""
        self._request_file_status.emit()

    def request_file_duplicates(self) -> None:
        """Ask the worker to fetch duplicate file groups (non-blocking)."""
        self._request_file_duplicates.emit()

    def request_file_large(self) -> None:
        """Ask the worker to fetch large files (non-blocking)."""
        self._request_file_large.emit()

    def request_file_misplaced(self) -> None:
        """Ask the worker to fetch misplaced files (non-blocking)."""
        self._request_file_misplaced.emit()

    def request_file_trends(self) -> None:
        """Ask the worker to fetch audit trends + forecast (non-blocking)."""
        self._request_file_trends.emit()

    def trigger_file_scan(self) -> None:
        """Ask the worker to POST a filesystem re-scan (non-blocking)."""
        self._request_file_scan.emit()

    def clean_stale_caches(self) -> None:
        """Ask the worker to POST the stale-cache clean (non-blocking).

        Callers MUST have confirmed with the user first — this deletes
        ``__pycache__``/``.pytest_cache`` directories and empty dirs.
        """
        self._request_stale_cache_clean.emit()

    def shutdown(self) -> None:
        """Stop the worker thread cleanly."""
        self._worker.cleanup()
        self._thread.quit()
        self._thread.wait(3000)
