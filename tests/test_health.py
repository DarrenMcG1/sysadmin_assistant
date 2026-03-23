"""Tests for the /health endpoint."""

import pytest

from sysadmin import __version__


@pytest.mark.asyncio
async def test_health_returns_200(test_client):
    resp = await test_client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(test_client):
    resp = await test_client.get("/health")
    data = resp.json()

    assert data["status"] == "healthy"
    assert data["service"] == "sysadmin-service"
    assert data["version"] == __version__


@pytest.mark.asyncio
async def test_health_version_is_string(test_client):
    data = (await test_client.get("/health")).json()
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
