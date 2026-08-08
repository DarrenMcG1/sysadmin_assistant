"""Tests for POST /api/sysadmin/services/{name}/{action} endpoint.

Covers: 404 unknown service, 403 non-controllable, 400 no systemd_unit,
200 happy path for restart/start/stop, failure response, invalid action.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.systemd import UserBusUnavailableError

# Patch target: the shared helper all actions delegate to
_CONTROL = "sysadmin.monitor.systemd._control_unit"


class TestServiceAction:
    @pytest.mark.asyncio
    async def test_unknown_service_returns_404(self, test_client):
        resp = await test_client.post("/api/sysadmin/services/nonexistent/restart")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_non_controllable_returns_403(self, test_client):
        resp = await test_client.post("/api/sysadmin/services/test-infra/restart")
        assert resp.status_code == 403
        assert "not controllable" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_no_systemd_unit_returns_400(self, test_client):
        """test-api is HTTP-only with no systemd_unit."""
        resp = await test_client.post("/api/sysadmin/services/test-api/restart")
        assert resp.status_code == 400
        assert "no systemd_unit" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_restart_success(self, test_client):
        with patch(_CONTROL, new_callable=AsyncMock, return_value=(True, "ok")):
            resp = await test_client.post("/api/sysadmin/services/test-systemd/restart")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_start_success(self, test_client):
        with patch(_CONTROL, new_callable=AsyncMock, return_value=(True, "ok")):
            resp = await test_client.post("/api/sysadmin/services/test-systemd/start")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_stop_success(self, test_client):
        with patch(_CONTROL, new_callable=AsyncMock, return_value=(True, "ok")):
            resp = await test_client.post("/api/sysadmin/services/test-systemd/stop")

        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_restart_failure_returns_success_false(self, test_client):
        with patch(
            _CONTROL,
            new_callable=AsyncMock,
            return_value=(False, "Unit not found"),
        ):
            resp = await test_client.post("/api/sysadmin/services/test-systemd/restart")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_action_returns_422(self, test_client):
        resp = await test_client.post("/api/sysadmin/services/test-systemd/destroy")
        assert resp.status_code == 422


class TestServiceDetails:
    """GET /api/sysadmin/services/{name}/details."""

    _STATUS = "sysadmin.monitor.routers.sysadmin.get_unit_status"

    @pytest.mark.asyncio
    async def test_details_returns_unit_properties(self, test_client):
        with patch(
            self._STATUS,
            new_callable=AsyncMock,
            return_value={"unit": "test.service", "ActiveState": "active", "is_active": True},
        ):
            resp = await test_client.get("/api/sysadmin/services/test-systemd/details")

        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_unqueryable_unit_returns_503_not_500(self, test_client):
        """SNAG-SYSD-001: an unreachable user bus is "ask again later",
        not "this server is broken"."""
        with patch(
            self._STATUS,
            new_callable=AsyncMock,
            side_effect=UserBusUnavailableError("systemd user bus unreachable"),
        ):
            resp = await test_client.get("/api/sysadmin/services/test-systemd/details")

        assert resp.status_code == 503
        assert "user bus unreachable" in resp.json()["detail"]
