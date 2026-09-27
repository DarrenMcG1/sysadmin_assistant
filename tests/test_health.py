"""Tests for the health endpoint, served at ``/health`` and ``/api/health``.

``/api/health`` is the monitorable-project contract's path (200, JSON, no
auth) and the one ``services.yaml`` polls for this service; ``/health`` is
the tray's liveness probe. Both are one handler.
"""

from pathlib import Path

import pytest
import yaml

from sysadmin import __version__

PATHS = ("/health", "/api/health")
SERVICES_YAML = Path(__file__).resolve().parent.parent / "services.yaml"


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_health_returns_200(test_client, path):
    resp = await test_client.get(path)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
@pytest.mark.parametrize("path", PATHS)
async def test_health_response_shape(test_client, path):
    resp = await test_client.get(path)
    data = resp.json()

    assert data["status"] == "healthy"
    assert data["service"] == "sysadmin-service"
    assert data["version"] == __version__


@pytest.mark.asyncio
async def test_health_version_is_string(test_client):
    data = (await test_client.get("/health")).json()
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_both_paths_answer_identically(test_client):
    """One handler under two paths — a copied handler could drift."""
    bodies = [(await test_client.get(path)).json() for path in PATHS]
    assert bodies[0] == bodies[1]


def test_our_own_services_row_polls_the_contract_path():
    """The row monitoring this service is the one place the contract's path
    is *used* here; pointing it back at ``/health`` is the drift the
    estate's ``health:legacy`` marking described."""
    entries = yaml.safe_load(SERVICES_YAML.read_text())["services"]
    own = [e for e in entries if e.get("systemd", {}).get("unit") == "sysadmin.service"]
    assert len(own) == 1, "expected exactly one services.yaml row for sysadmin.service"
    assert own[0]["url"] == "http://localhost:8500/api/health"
