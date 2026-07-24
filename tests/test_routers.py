"""Integration tests for key API endpoints via the FastAPI test client.

Tests use mocked DB sessions — no real database needed.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.models.alert import Alert
from sysadmin.models.resource_snapshot import ResourceSnapshot
from sysadmin.models.service_health import ServiceHealth


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_health(
    name: str, status: str = "ok", response_time_ms: int = 50
) -> ServiceHealth:
    row = ServiceHealth(
        service_name=name,
        status=status,
        response_time_ms=response_time_ms,
        details={},
    )
    row.id = uuid.uuid4()
    row.checked_at = datetime.now(timezone.utc)
    return row


def _make_resource_snapshot(**overrides) -> ResourceSnapshot:
    defaults = dict(
        cpu_percent=25.0,
        ram_used_mb=8000,
        ram_total_mb=16000,
        ram_percent=50.0,
        swap_used_mb=512,
        swap_total_mb=4096,
        disk_usage={"/": {"total_gb": 500, "used_gb": 200, "free_gb": 300, "percent": 40}},
        gpu_usage={},
        load_avg_1m=1.0,
        load_avg_5m=1.5,
        load_avg_15m=1.2,
    )
    defaults.update(overrides)
    row = ResourceSnapshot(**defaults)
    row.id = uuid.uuid4()
    row.recorded_at = datetime.now(timezone.utc)
    return row


def _make_alert(
    title: str = "Test alert",
    severity: str = "warning",
    resolved: bool = False,
) -> Alert:
    row = Alert(
        agent="sysadmin",
        severity=severity,
        title=title,
        message="Test message",
        details={},
    )
    row.id = uuid.uuid4()
    row.acknowledged = False
    row.resolved = resolved
    row.created_at = datetime.now(timezone.utc)
    return row


def _mock_scalars_all(mock_session, rows):
    """Configure mock_session.execute to return rows via scalars().all()."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _mock_scalar_one_or_none(mock_session, row):
    """Configure mock_session.execute to return a single row or None."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# /api/sysadmin/status
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    @pytest.mark.asyncio
    async def test_get_all_statuses(self, test_client, mock_session):
        rows = [
            _make_service_health("test-api", "ok", 42),
            _make_service_health("test-tcp", "ok", 10),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "services" in data
        assert "all_healthy" in data
        assert data["all_healthy"] is True
        assert len(data["services"]) == 2

    @pytest.mark.asyncio
    async def test_unhealthy_service_sets_all_healthy_false(self, test_client, mock_session):
        rows = [
            _make_service_health("test-api", "ok"),
            _make_service_health("test-tcp", "critical"),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status")
        data = resp.json()
        assert data["all_healthy"] is False


class TestServiceStatusHistory:
    @pytest.mark.asyncio
    async def test_get_service_history(self, test_client, mock_session):
        rows = [_make_service_health("test-api", "ok", 42)]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status/test-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "test-api"
        assert len(data["checks"]) == 1

    @pytest.mark.asyncio
    async def test_empty_history(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/sysadmin/status/nonexistent")
        data = resp.json()
        assert data["checks"] == []


# ---------------------------------------------------------------------------
# /api/sysadmin/resources
# ---------------------------------------------------------------------------


class TestResourcesEndpoint:
    @pytest.mark.asyncio
    async def test_get_resources(self, test_client, mock_session):
        snapshot = _make_resource_snapshot()
        _mock_scalar_one_or_none(mock_session, snapshot)

        resp = await test_client.get("/api/sysadmin/resources")
        assert resp.status_code == 200
        data = resp.json()

        assert "cpu_percent" in data
        assert "ram" in data
        assert data["ram"]["used_mb"] == 8000
        assert "disk" in data
        assert "load_avg" in data

    @pytest.mark.asyncio
    async def test_no_resources_yet(self, test_client, mock_session):
        _mock_scalar_one_or_none(mock_session, None)

        resp = await test_client.get("/api/sysadmin/resources")
        data = resp.json()
        assert "message" in data


class TestResourceHistory:
    @pytest.mark.asyncio
    async def test_get_resource_history(self, test_client, mock_session):
        rows = [_make_resource_snapshot()]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/resources/history?hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_hours"] == 24
        assert len(data["snapshots"]) == 1


# ---------------------------------------------------------------------------
# /api/sysadmin/alerts
# ---------------------------------------------------------------------------


class TestAlertsEndpoint:
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, test_client, mock_session):
        rows = [_make_alert("High RAM", "warning")]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["alerts"][0]["title"] == "High RAM"

    @pytest.mark.asyncio
    async def test_get_all_alerts(self, test_client, mock_session):
        rows = [
            _make_alert("Active", resolved=False),
            _make_alert("Resolved", resolved=True),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/alerts?active_only=false")
        data = resp.json()
        assert data["count"] == 2


class TestAlertAcknowledge:
    @pytest.mark.asyncio
    async def test_ack_alert(self, test_client, mock_session):
        alert = _make_alert("Test")
        _mock_scalar_one_or_none(mock_session, alert)

        resp = await test_client.post(f"/api/sysadmin/alerts/{alert.id}/ack")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_ack_missing_alert_returns_404(self, test_client, mock_session):
        """Acking a nonexistent alert must be a real 404, not a 200 tuple (SNAG-API-001)."""
        _mock_scalar_one_or_none(mock_session, None)

        resp = await test_client.post(f"/api/sysadmin/alerts/{uuid.uuid4()}/ack")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"] == "Alert not found"


# ---------------------------------------------------------------------------
# /api/sysadmin/dnd
# ---------------------------------------------------------------------------


class TestDndEndpoints:
    @pytest.mark.asyncio
    async def test_get_dnd_status(self, test_client):
        with patch("sysadmin.routers.sysadmin.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {
                "active": False,
                "manual_override": None,
                "schedule_active": False,
            }
            resp = await test_client.get("/api/sysadmin/dnd")

        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data

    @pytest.mark.asyncio
    async def test_toggle_dnd_on(self, test_client):
        with patch("sysadmin.routers.sysadmin.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": True, "manual_override": True}
            resp = await test_client.post(
                "/api/sysadmin/dnd", json={"enabled": True}
            )

        assert resp.status_code == 200
        mock_dnd.set_manual_override.assert_called_once_with(True)


# ---------------------------------------------------------------------------
# /api/sysadmin/ports
# ---------------------------------------------------------------------------


class TestPortsEndpoint:
    @pytest.mark.asyncio
    async def test_get_ports(self, test_client):
        with patch(
            "sysadmin.routers.sysadmin.SysAdminAgent.get_port_usage",
            return_value=[
                {"port": 5432, "address": "127.0.0.1", "pid": 1234, "process": "postgres"},
            ],
        ):
            resp = await test_client.get("/api/sysadmin/ports")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["ports"][0]["port"] == 5432

    @pytest.mark.asyncio
    async def test_get_ports_runs_off_event_loop(self, test_client):
        """The blocking psutil scan must not run on the event loop (SNAG-API-003)."""
        import asyncio

        def _assert_no_loop():
            # asyncio.to_thread runs this in a worker thread, where there
            # is no running event loop; on the loop this would succeed.
            with pytest.raises(RuntimeError):
                asyncio.get_running_loop()
            return []

        with patch(
            "sysadmin.routers.sysadmin.SysAdminAgent.get_port_usage",
            side_effect=_assert_no_loop,
        ):
            resp = await test_client.get("/api/sysadmin/ports")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0
