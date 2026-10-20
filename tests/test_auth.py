"""Tests for the guard on state-changing endpoints (``require_auth``).

Covers:
- 401 (with WWW-Authenticate: Bearer) on missing/wrong/malformed tokens
- Correct token passes
- Auth disabled (no token configured) leaves endpoints open
- Read-only GET endpoints stay open even with auth enabled
- 403 on a mutating request from a foreign ``Origin``, per route, with
  or without a token (``SNAG-API-005``)
"""

import pytest
from fastapi.routing import APIRoute

from sysadmin.core.api_token import (
    CREDENTIAL_ID,
    CREDENTIALS_ENV,
    daemon_token,
    read_token,
)
from sysadmin.core.auth import origin_allowed, require_auth

AUTH_TOKEN = "test-token-abc123"

# Every mutating route, as a URL a client would build. Held equal to the
# routes carrying require_auth on create_app() by
# test_the_list_is_every_guarded_route, so a new route cannot miss a test.
PROTECTED_ROUTES = [
    "/api/sysadmin/services/test-api/restart",
    "/api/sysadmin/alerts/some-id/ack",
    "/api/sysadmin/dnd",
    "/api/sysadmin/review/generate",
    "/api/sysadmin/scan-all",
    "/api/sysadmin/reload",
    "/api/files/scan",
    "/api/files/clean/stale-caches",
    "/api/files/organise",
    "/api/files/clean/duplicates",
    "/api/files/clean/downloads",
    "/api/files/review/generate",
    "/api/logs/review/generate",
]

ALLOWED_ORIGIN = "http://localhost:3100"
FOREIGN_ORIGIN = "https://evil.example"
REFUSED = "Cross-site request refused"


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
        from sysadmin.core.auth import require_auth
        from sysadmin.main import app

        route = next(
            r for r in app.routes
            if getattr(r, "path", None) == "/api/sysadmin/scan-all"
        )
        dep_calls = [d.call for d in route.dependant.dependencies]
        assert require_auth in dep_calls


def _template(url: str, route_path: str) -> bool:
    """Whether ``url`` is an instance of ``route_path``'s template."""
    want, got = route_path.strip("/").split("/"), url.strip("/").split("/")
    return len(want) == len(got) and all(
        w.startswith("{") or w == g for w, g in zip(want, got, strict=True)
    )


class TestRouteCensus:
    """The population the origin check covers is computed, not listed."""

    def test_every_mutating_route_carries_require_auth(self, test_app):
        mutating = [
            r for r in test_app.routes
            if isinstance(r, APIRoute) and r.methods - {"GET", "HEAD", "OPTIONS"}
        ]
        assert mutating, "no mutating route found: the census measured nothing"
        unguarded = [
            r.path for r in mutating
            if require_auth not in [d.call for d in r.dependant.dependencies]
        ]
        assert unguarded == []

    def test_the_list_is_every_guarded_route(self, test_app):
        guarded = [
            r.path for r in test_app.routes
            if isinstance(r, APIRoute)
            and require_auth in [d.call for d in r.dependant.dependencies]
        ]
        unlisted = [p for p in guarded if not any(_template(u, p) for u in PROTECTED_ROUTES)]
        stale = [u for u in PROTECTED_ROUTES if not any(_template(u, p) for p in guarded)]
        assert (unlisted, stale) == ([], [])
        assert len(guarded) == len(PROTECTED_ROUTES)

    def test_the_check_reads_the_list_cors_middleware_holds(self, test_app):
        """One list for both readers; ``service`` is restart-only."""
        from starlette.middleware.cors import CORSMiddleware

        cors = next(m for m in test_app.user_middleware if m.cls is CORSMiddleware)
        assert cors.kwargs["allow_origins"] is test_app.state.cors_origins


@pytest.fixture
def origin_client(test_app, test_client):
    """test_client with a known allowed-origin list on the app."""
    test_app.state.cors_origins = [ALLOWED_ORIGIN]
    return test_client


class TestCrossSiteRefused:
    """A foreign ``Origin`` is refused before any handler runs."""

    @pytest.mark.parametrize("path", PROTECTED_ROUTES)
    async def test_foreign_origin_refused(self, origin_client, path):
        # No body and no custom header: the simple request a page can send.
        resp = await origin_client.post(path, headers={"Origin": FOREIGN_ORIGIN})
        assert resp.status_code == 403
        assert resp.json() == {"detail": REFUSED}

    async def test_null_origin_refused(self, origin_client):
        resp = await origin_client.post(
            "/api/sysadmin/scan-all", headers={"Origin": "null"}
        )
        assert resp.status_code == 403

    async def test_foreign_origin_does_not_reach_the_handler(
        self, origin_client, test_app
    ):
        await origin_client.post(
            "/api/sysadmin/scan-all", headers={"Origin": FOREIGN_ORIGIN}
        )
        test_app.state.sysadmin_agent.run.assert_not_called()

    async def test_refused_even_with_the_right_token(self, origin_client, mock_config):
        mock_config.api.auth_token = AUTH_TOKEN
        try:
            resp = await origin_client.post(
                "/api/sysadmin/dnd",
                json={"enabled": None},
                headers={
                    "Origin": FOREIGN_ORIGIN,
                    "Authorization": f"Bearer {AUTH_TOKEN}",
                },
            )
            assert resp.status_code == 403
        finally:
            mock_config.api.auth_token = None

    async def test_allowed_origin_passes(self, origin_client):
        resp = await origin_client.post(
            "/api/sysadmin/dnd",
            json={"enabled": None},
            headers={"Origin": ALLOWED_ORIGIN},
        )
        assert resp.status_code == 200

    async def test_absent_origin_passes(self, origin_client):
        """The tray and server-side callers send no Origin."""
        resp = await origin_client.post("/api/sysadmin/dnd", json={"enabled": None})
        assert resp.status_code == 200

    async def test_get_stays_open_cross_site(self, origin_client):
        resp = await origin_client.get(
            "/api/sysadmin/dnd", headers={"Origin": FOREIGN_ORIGIN}
        )
        assert resp.status_code == 200


class TestOriginAllowed:
    def test_exact_match_only(self):
        assert origin_allowed("http://localhost:3100", ["http://localhost:3100"])
        assert not origin_allowed("http://localhost:3101", ["http://localhost:3100"])
        assert not origin_allowed("http://localhost:3100/", ["http://localhost:3100"])

    def test_wildcard_allows_anything(self):
        assert origin_allowed("null", ["*"])


@pytest.fixture
def credential_client(test_app, test_client):
    """test_client whose app was handed a delivered credential at build time."""
    test_app.state.api_token = CREDENTIAL_TOKEN
    yield test_client
    test_app.state.api_token = None


CREDENTIAL_TOKEN = "delivered-token-xyz789"


class TestTheCredentialIsTheToken:
    """SNAG-API-005's token half: the ``api-token`` systemd credential."""

    @pytest.mark.parametrize("path", PROTECTED_ROUTES)
    async def test_missing_token_rejected(self, credential_client, path):
        resp = await credential_client.post(path, json={})
        assert resp.status_code == 401

    async def test_the_credential_passes(self, credential_client):
        resp = await credential_client.post(
            "/api/sysadmin/dnd",
            json={"enabled": None},
            headers={"Authorization": f"Bearer {CREDENTIAL_TOKEN}"},
        )
        assert resp.status_code == 200

    async def test_the_credential_wins_over_the_config_token(
        self, credential_client, mock_config
    ):
        mock_config.api.auth_token = AUTH_TOKEN
        try:
            resp = await credential_client.post(
                "/api/sysadmin/dnd",
                json={"enabled": None},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            assert resp.status_code == 401
        finally:
            mock_config.api.auth_token = None

    def test_create_app_reads_the_credentials_directory(
        self, tmp_path, monkeypatch, mock_config
    ):
        from sysadmin.main import create_app

        (tmp_path / CREDENTIAL_ID).write_text(f"{CREDENTIAL_TOKEN}\n", encoding="utf-8")
        monkeypatch.setenv(CREDENTIALS_ENV, str(tmp_path))
        assert create_app().state.api_token == CREDENTIAL_TOKEN


class TestTokenReaders:
    def test_outside_the_unit_there_is_no_credential(self, monkeypatch):
        monkeypatch.delenv(CREDENTIALS_ENV, raising=False)
        assert daemon_token() is None

    def test_the_trailing_newline_is_not_part_of_the_token(self, tmp_path):
        path = tmp_path / "t"
        path.write_text("abc\n", encoding="utf-8")
        assert read_token(path) == "abc"

    def test_a_blank_file_is_no_token(self, tmp_path):
        """Blank must read as absent, or a bearer of nothing would pass."""
        path = tmp_path / "t"
        path.write_text("\n", encoding="utf-8")
        assert read_token(path) is None

    def test_an_absent_file_is_no_token(self, tmp_path):
        assert read_token(tmp_path / "missing") is None

    def test_the_tray_reads_the_delivered_copy(self, tmp_path, monkeypatch):
        import sysadmin.core.api_token as api_token

        (tmp_path / CREDENTIAL_ID).write_text("delivered", encoding="utf-8")
        monkeypatch.setattr(api_token, "DELIVERED_DIRECTORY", tmp_path)
        assert api_token.tray_token() == "delivered"
