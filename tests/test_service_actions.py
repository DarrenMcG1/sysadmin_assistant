"""Tests for POST /api/sysadmin/services/{name}/{action} endpoint.

Covers: 404 unknown service, 403 non-controllable, 400 no systemd_unit,
200 happy path for restart/start/stop, failure response, invalid action.
"""

from unittest.mock import AsyncMock, patch

import pytest

# Patch target: the shared helper all actions delegate to
_CONTROL = "sysadmin.utils.systemd._control_unit"


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
