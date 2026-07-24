"""Tests for the ApiWorker with mocked httpx responses."""

from unittest.mock import MagicMock, patch

import pytest

from sysadmin_tray.client import ApiWorker
from sysadmin_tray.models import AlertsResponse, ResourceResponse, StatusResponse

# ── Fixtures ─────────────────────────────────────────────────────────

MOCK_HEALTH = {"status": "healthy", "service": "sysadmin-service", "version": "0.1.0"}

MOCK_STATUS = {
    "services": [
        {"name": "postgresql", "status": "ok", "response_time_ms": 10.0,
         "details": None, "checked_at": "2026-02-07T10:00:00+00:00"},
    ],
    "all_healthy": True,
}

MOCK_RESOURCES = {
    "cpu_percent": 55.0,
    "ram": {"used_mb": 8000, "total_mb": 16384, "percent": 48.8},
    "swap": {"used_mb": 0, "total_mb": 8192},
    "disk": {"/": {"total_gb": 475.0, "used_gb": 350.0, "free_gb": 125.0, "percent": 73.7}},
    "gpu": {},
    "load_avg": {"1m": 1.0, "5m": 0.8, "15m": 0.7},
    "recorded_at": "2026-02-07T10:00:00+00:00",
}

MOCK_ALERTS = {
    "alerts": [
        {"id": "a1", "agent": "sysadmin", "severity": "warning", "title": "Test",
         "message": "", "details": {}, "acknowledged": False, "resolved": False,
         "created_at": "2026-02-07T10:00:00+00:00"},
    ],
    "count": 1,
}


def _mock_response(json_data, status_code=200):
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


class TestApiWorkerAuth:
    """Bearer token wiring on the underlying httpx client."""

    def test_auth_token_sets_authorization_header(self):
        worker = ApiWorker("http://test:8500", auth_token="secret-token")
        assert worker._client.headers["Authorization"] == "Bearer secret-token"
        worker.cleanup()

    def test_no_token_sends_no_authorization_header(self):
        worker = ApiWorker("http://test:8500")
        assert "Authorization" not in worker._client.headers
        worker.cleanup()

    def test_empty_token_sends_no_authorization_header(self):
        worker = ApiWorker("http://test:8500", auth_token="")
        assert "Authorization" not in worker._client.headers
        worker.cleanup()


class TestApiWorkerFetchStatus:
    """ApiWorker.fetch_status() with mocked HTTP."""

    def test_emits_status_on_success(self):
        worker = ApiWorker("http://test:8500")
        worker.status_ready = MagicMock()
        worker.connection_restored = MagicMock()

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.side_effect = [
                _mock_response(MOCK_HEALTH),   # /health
                _mock_response(MOCK_STATUS),   # /api/sysadmin/status
            ]
            worker.fetch_status()

        worker.status_ready.emit.assert_called_once()
        emitted = worker.status_ready.emit.call_args[0][0]
        assert isinstance(emitted, StatusResponse)
        assert len(emitted.services) == 1

    def test_emits_connection_lost_on_error(self):
        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()

        import httpx
        with patch.object(worker, "_client") as mock_client:
            mock_client.get.side_effect = httpx.ConnectError("refused")
            worker.fetch_status()

        worker.connection_lost.emit.assert_called_once()


class TestApiWorkerFetchResources:
    def test_emits_resources_on_success(self):
        worker = ApiWorker("http://test:8500")
        worker.resources_ready = MagicMock()
        worker.connection_restored = MagicMock()

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = _mock_response(MOCK_RESOURCES)
            worker.fetch_resources()

        worker.resources_ready.emit.assert_called_once()
        emitted = worker.resources_ready.emit.call_args[0][0]
        assert isinstance(emitted, ResourceResponse)
        assert emitted.cpu_percent == pytest.approx(55.0)


class TestApiWorkerFetchAlerts:
    def test_emits_alerts_on_success(self):
        worker = ApiWorker("http://test:8500")
        worker.alerts_ready = MagicMock()
        worker.connection_restored = MagicMock()

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = _mock_response(MOCK_ALERTS)
            worker.fetch_alerts()

        worker.alerts_ready.emit.assert_called_once()
        emitted = worker.alerts_ready.emit.call_args[0][0]
        assert isinstance(emitted, AlertsResponse)
        assert emitted.count == 1


class TestApiWorkerTriggerScan:
    def test_emits_scan_complete_on_success(self):
        worker = ApiWorker("http://test:8500")
        worker.scan_complete = MagicMock()

        with patch.object(worker, "_client") as mock_client:
            mock_client.post.return_value = _mock_response(
                {"status": "all_scans_triggered"}
            )
            worker.trigger_scan()

        worker.scan_complete.emit.assert_called_once_with(True, "All scans triggered")

    def test_emits_scan_complete_on_failure(self):
        worker = ApiWorker("http://test:8500")
        worker.scan_complete = MagicMock()

        import httpx
        with patch.object(worker, "_client") as mock_client:
            mock_client.post.side_effect = httpx.ConnectError("refused")
            worker.trigger_scan()

        worker.scan_complete.emit.assert_called_once()
        args = worker.scan_complete.emit.call_args[0]
        assert args[0] is False


class TestMalformedResponses:
    """Malformed API responses must mark the connection lost (SNAG-TRAY-005)."""

    def test_non_json_body_emits_connection_lost(self):
        """A proxy error page / truncated body raises JSONDecodeError."""
        import json

        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()
        worker.status_ready = MagicMock()

        bad_resp = _mock_response(None)
        bad_resp.json.side_effect = json.JSONDecodeError(
            "Expecting value", "<html>502 Bad Gateway</html>", 0
        )

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = bad_resp
            worker.fetch_status()

        worker.connection_lost.emit.assert_called_once()
        worker.status_ready.emit.assert_not_called()

    def test_payload_shape_change_emits_connection_lost(self):
        """A TypeError from parsing an unexpected payload shape is caught."""
        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()
        worker.status_ready = MagicMock()

        # "services" as a scalar → iterating raises TypeError
        with patch.object(worker, "_client") as mock_client:
            mock_client.get.side_effect = [
                _mock_response(MOCK_HEALTH),                # /health
                _mock_response({"services": 123}),          # bad shape
            ]
            worker.fetch_status()

        worker.connection_lost.emit.assert_called_once()
        worker.status_ready.emit.assert_not_called()

    def test_non_numeric_value_emits_connection_lost(self):
        """A ValueError from a payload value of the wrong type is caught."""
        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()
        worker.resources_ready = MagicMock()

        # cpu_percent as a non-numeric string → float() raises ValueError
        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = _mock_response(
                {"cpu_percent": "not-a-number", "ram": {}, "disk": {}}
            )
            worker.fetch_resources()

        worker.connection_lost.emit.assert_called_once()
        worker.resources_ready.emit.assert_not_called()

    def test_non_json_alerts_body_emits_connection_lost(self):
        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()
        worker.alerts_ready = MagicMock()

        bad_resp = _mock_response(None)
        bad_resp.json.side_effect = ValueError("invalid json")

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = bad_resp
            worker.fetch_alerts()

        worker.connection_lost.emit.assert_called_once()
        worker.alerts_ready.emit.assert_not_called()


class TestConnectionStateTracking:
    """Verify connection_lost/restored only fire on transitions."""

    def test_only_emits_restored_on_first_success(self):
        worker = ApiWorker("http://test:8500")
        worker.connection_restored = MagicMock()
        worker.resources_ready = MagicMock()

        with patch.object(worker, "_client") as mock_client:
            mock_client.get.return_value = _mock_response(MOCK_RESOURCES)

            # First success → should emit restored
            worker.fetch_resources()
            assert worker.connection_restored.emit.call_count == 1

            # Second success → should NOT emit restored again
            worker.fetch_resources()
            assert worker.connection_restored.emit.call_count == 1

    def test_only_emits_lost_once(self):
        worker = ApiWorker("http://test:8500")
        worker._was_connected = True
        worker.connection_lost = MagicMock()

        import httpx
        with patch.object(worker, "_client") as mock_client:
            mock_client.get.side_effect = httpx.ConnectError("refused")

            worker.fetch_resources()
            assert worker.connection_lost.emit.call_count == 1

            worker.fetch_resources()
            assert worker.connection_lost.emit.call_count == 1
