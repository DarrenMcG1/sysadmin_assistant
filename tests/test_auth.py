"""Tests for bearer-token authentication on state-changing endpoints.

Covers:
- 401 (with WWW-Authenticate: Bearer) on missing/wrong/malformed tokens
- Correct token passes
- Auth disabled (no token configured) leaves endpoints open
- Read-only GET endpoints stay open even with auth enabled
"""

import pytest

AUTH_TOKEN = "test-token-abc123"

# Every mutating route in the test app (scan-all lives on the main app
# and shares the same dependency; see test_scan_all_route_has_auth).
PROTECTED_ROUTES = [
    "/api/sysadmin/services/test-api/restart",
    "/api/sysadmin/alerts/some-id/ack",
    "/api/sysadmin/dnd",
    "/api/projects/scan",
    "/api/files/scan",
    "/api/files/clean/stale-caches",
]


@pytest.fixture
async def auth_client(mock_config, test_client):
    """test_client with api.auth_token set on the patched config."""
    mock_config.api.auth_token = AUTH_TOKEN
    yield test_client
    mock_config.api.auth_token = None


class TestAuthEnabled:
    """With api.auth_token configured, mutating endpoints require it."""

    @pytest.mark.parametrize("path", PROTECTED_ROUTES)
    async def test_missing_token_rejected(self, auth_client, path):
        resp = await auth_client.post(path, json={})
        assert resp.status_code == 401
        assert resp.headers.get("WWW-Authenticate") == "Bearer"

    @pytest.mark.parametrize("path", PROTECTED_ROUTES)
    async def test_wrong_token_rejected(self, auth_client, path):
        resp = await auth_client.post(
            path, json={}, headers={"Authorization": "Bearer wrong-token"}
        )
        assert resp.status_code == 401
        assert resp.headers.get("WWW-Authenticate") == "Bearer"

    async def test_wrong_scheme_rejected(self, auth_client):
        resp = await auth_client.post(
            "/api/sysadmin/dnd",
            json={"enabled": None},
            headers={"Authorization": f"Basic {AUTH_TOKEN}"},
        )
        assert resp.status_code == 401

    async def test_correct_token_passes(self, auth_client):
        resp = await auth_client.post(
            "/api/sysadmin/dnd",
            json={"enabled": None},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        assert resp.status_code == 200

    async def test_get_endpoints_stay_open(self, auth_client):
        """Read-only GETs must not require a token (dashboards rely on this)."""
        resp = await auth_client.get("/api/sysadmin/dnd")
        assert resp.status_code == 200


class TestAuthDisabled:
    """Without api.auth_token, mutating endpoints remain open."""

    async def test_no_token_configured_is_open(self, test_client, mock_config):
        assert mock_config.api.auth_token is None
        resp = await test_client.post(
            "/api/sysadmin/dnd", json={"enabled": None}
        )
        assert resp.status_code == 200

    async def test_empty_token_is_open(self, test_client, mock_config):
        """Empty string (the committed config.yaml placeholder) disables auth."""
        mock_config.api.auth_token = ""
        try:
            resp = await test_client.post(
                "/api/sysadmin/dnd", json={"enabled": None}
            )
            assert resp.status_code == 200
        finally:
            mock_config.api.auth_token = None


class TestScanAllRoute:
    """The scan-all route on the main app carries the auth dependency."""

    def test_scan_all_route_has_auth(self):
        from sysadmin.auth import require_auth
        from sysadmin.main import app

        route = next(
            r for r in app.routes
            if getattr(r, "path", None) == "/api/sysadmin/scan-all"
        )
        dep_calls = [d.call for d in route.dependant.dependencies]
        assert require_auth in dep_calls
