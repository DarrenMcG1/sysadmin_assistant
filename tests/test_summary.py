"""Tests for GET /api/summary digest endpoint.

The projects section left with the scanner in the Session 4 cutover
(ADR-0005): this digest is machine-flavoured now — services, alerts,
resources, DND. Project state is served by the estate on 8400.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.models.alert import Alert
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth


def _make_health(name: str, status: str = "ok") -> ServiceHealth:
    row = ServiceHealth(service_name=name, status=status, response_time_ms=42, details={})
    row.id = uuid.uuid4()
    row.checked_at = datetime.now(UTC)
    return row


def _make_alert(title: str, severity: str = "warning") -> Alert:
    row = Alert(agent="sysadmin", severity=severity, title=title, message="msg", details={})
    row.id = uuid.uuid4()
    row.acknowledged = False
    row.resolved = False
    row.created_at = datetime.now(UTC)
    return row


def _make_snapshot() -> ResourceSnapshot:
    row = ResourceSnapshot(
        cpu_percent=30.0, ram_used_mb=8000, ram_total_mb=16000, ram_percent=50.0,
        swap_used_mb=512, swap_total_mb=4096,
        disk_usage={"/": {"total_gb": 500, "used_gb": 200, "free_gb": 300, "percent": 40}},
        gpu_usage={"card0": {"name": "RX 7900", "gpu_percent": 20, "temp_c": 60.0}},
        load_avg_1m=1.0, load_avg_5m=1.5, load_avg_15m=1.2,
    )
    row.id = uuid.uuid4()
    row.recorded_at = datetime.now(UTC)
    return row


def _mock_multi_queries(mock_session, results_sequence):
    """Mock session.execute to return different results for sequential queries."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        idx = min(call_count, len(results_sequence) - 1)
        call_count += 1
        result = MagicMock()
        data = results_sequence[idx]
        if isinstance(data, list):
            result.scalars.return_value.all.return_value = data
        else:
            result.scalar_one_or_none.return_value = data
        return result

    mock_session.execute = AsyncMock(side_effect=side_effect)


class TestSummaryEndpoint:
    @pytest.mark.asyncio
    async def test_returns_all_sections(self, test_client, mock_session):
        _mock_multi_queries(mock_session, [
            [_make_health("api", "ok")],      # services
            [_make_alert("High RAM")],          # alerts
            _make_snapshot(),                    # resources
        ])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        assert resp.status_code == 200
        data = resp.json()
        assert "generated_at" in data
        assert "services" in data
        assert "alerts" in data
        assert "resources" in data
        assert "dnd" in data
        # Project state moved to the estate's 8400 service (ADR-0005);
        # asserted absent so a reintroduction is a failing test, not a
        # second producer nobody noticed.
        assert "projects" not in data

    @pytest.mark.asyncio
    async def test_services_section(self, test_client, mock_session):
        _mock_multi_queries(mock_session, [
            [_make_health("api", "ok"), _make_health("db", "critical")],
            [],
            None,
        ])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        data = resp.json()
        assert data["services"]["all_healthy"] is False
        assert len(data["services"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_declared_unmonitored_service_is_not_unhealthy(
        self, test_client, mock_session
    ):
        """``SNAG-API-004``, the sibling nobody had counted.

        This flag carried the identical ``!= "ok"`` defect as
        ``GET /api/sysadmin/status``.  The snag named one route; the
        population was three, and this was found by auditing rather than
        by anything failing.
        """
        _mock_multi_queries(mock_session, [
            [_make_health("api", "ok"), _make_health("tray", "skipped")],
            [],
            None,
        ])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        data = resp.json()
        assert data["services"]["all_healthy"] is True
        assert len(data["services"]["items"]) == 2

    @pytest.mark.asyncio
    async def test_a_real_fault_still_speaks_beside_a_skipped_row(
        self, test_client, mock_session
    ):
        _mock_multi_queries(mock_session, [
            [_make_health("tray", "skipped"), _make_health("api", "unreachable")],
            [],
            None,
        ])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        assert resp.json()["services"]["all_healthy"] is False

    @pytest.mark.asyncio
    async def test_empty_state(self, test_client, mock_session):
        _mock_multi_queries(mock_session, [[], [], None])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        data = resp.json()
        assert data["services"]["all_healthy"] is True
        assert data["alerts"]["count"] == 0
        assert data["resources"] is None

    @pytest.mark.asyncio
    async def test_gpu_included_in_resources(self, test_client, mock_session):
        _mock_multi_queries(mock_session, [
            [],
            [],
            _make_snapshot(),
        ])

        with patch("sysadmin.briefing.router.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": False}
            resp = await test_client.get("/api/summary")

        resources = resp.json()["resources"]
        assert "gpu" in resources
        assert "card0" in resources["gpu"]
