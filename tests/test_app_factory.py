"""Tests for behaviours only the REAL app exhibits.

The old synthetic test app (hand-mounted routers, no middleware, no
exception handlers, no scan-all route) let SNAG-API-001/002 slip
through. These tests exercise the parts of ``create_app`` the synthetic
app never had.
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient


class TestScanAll:
    @pytest.mark.asyncio
    async def test_scan_all_triggers_every_agent(self, test_client, test_app):
        resp = await test_client.post("/api/sysadmin/scan-all")
        assert resp.status_code == 200
        assert resp.json() == {"status": "all_scans_triggered"}

        for name in (
            "sysadmin_agent",
            "project_organiser_agent",
            "file_organiser_agent",
            "log_aggregator_agent",
        ):
            agent = getattr(test_app.state, name)
            agent.run.assert_called_once_with(run_type="manual")


class TestProjectScanTrigger:
    @pytest.mark.asyncio
    async def test_project_scan_uses_app_state_agent(self, test_client, test_app):
        resp = await test_client.post("/api/projects/scan")
        assert resp.status_code == 200
        assert resp.json() == {"status": "scan_triggered"}
        test_app.state.project_organiser_agent.run.assert_called_once_with(
            run_type="manual"
        )


class TestExceptionHandler:
    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_json_500(self, test_app, mock_config):
        """The real app converts unhandled exceptions to a JSON 500 body."""

        @test_app.get("/boom")
        async def boom():
            raise RuntimeError("kaboom")

        with patch("sysadmin.config.get_config", return_value=mock_config):
            with patch("sysadmin.config._config", mock_config):
                transport = ASGITransport(app=test_app, raise_app_exceptions=False)
                async with AsyncClient(
                    transport=transport, base_url="http://test"
                ) as client:
                    resp = await client.get("/boom")

        assert resp.status_code == 500
        assert resp.json() == {"detail": "Internal server error"}


class TestMiddlewareStack:
    @pytest.mark.asyncio
    async def test_cors_preflight_allows_frontend_origin(self, test_client):
        resp = await test_client.options(
            "/api/sysadmin/status",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.status_code == 200
        assert (
            resp.headers.get("access-control-allow-origin")
            == "http://localhost:3000"
        )

    @pytest.mark.asyncio
    async def test_unknown_route_is_json_404(self, test_client):
        resp = await test_client.get("/api/does-not-exist")
        assert resp.status_code == 404
        assert resp.json() == {"detail": "Not Found"}


class TestResponseModelEnforcement:
    @pytest.mark.asyncio
    async def test_dnd_response_drops_uncontracted_fields(self, test_client):
        """response_model enforcement: fields outside the contract never leak."""
        with patch("sysadmin.routers.sysadmin.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {
                "active": True,
                "manual_override": None,
                "config_enabled": False,
                "allow_critical": True,
                "schedule": [],
                "internal_debug_field": "should not appear",
            }
            resp = await test_client.get("/api/sysadmin/dnd")

        assert resp.status_code == 200
        data = resp.json()
        assert data["active"] is True
        assert "internal_debug_field" not in data
