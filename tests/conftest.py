"""Shared test fixtures for the sysadmin backend test suite.

Provides:
- Mock AppConfig with sensible test defaults
- Mock async DB session (no real database needed for unit tests)
- FastAPI test client with dependency overrides
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from sysadmin.config import (
    AgentsConfig,
    AppConfig,
    DatabaseConfig,
    FileOrganiserConfig,
    MonitoredService,
    NotificationsConfig,
    ProjectOrganiserConfig,
    ServiceConfig,
    SysAdminAgentConfig,
    Thresholds,
)


@pytest.fixture
def mock_config():
    """Minimal AppConfig for testing — no real files or services needed."""
    return AppConfig(
        service=ServiceConfig(name="sysadmin-service", port=8500, host="127.0.0.1"),
        database=DatabaseConfig(
            url="postgresql+asyncpg://test@localhost/test",
            sync_url="postgresql+psycopg2://test@localhost/test",
            schema="sysadmin_test",
        ),
        agents=AgentsConfig(
            sysadmin=SysAdminAgentConfig(
                enabled=True,
                health_check_interval_seconds=60,
                services=[
                    MonitoredService(
                        name="test-api",
                        type="http",
                        url="http://localhost:9999/health",
                    ),
                    MonitoredService(
                        name="test-tcp",
                        type="tcp",
                        host="localhost",
                        port=5432,
                    ),
                    MonitoredService(
                        name="test-systemd",
                        type="systemd",
                        systemd_unit="test.service",
                    ),
                ],
                thresholds=Thresholds(
                    disk_warning_percent=80,
                    disk_critical_percent=90,
                    ram_warning_percent=85,
                ),
            ),
            project_organiser=ProjectOrganiserConfig(
                enabled=True,
                projects_root="/tmp/test_projects",
                stale_branch_days=30,
                track_todos=True,
                todo_patterns=["TODO", "FIXME"],
            ),
            file_organiser=FileOrganiserConfig(
                enabled=True,
                scan_root="/tmp/test_scan",
                stale_days=180,
                downloads_stale_days=30,
                large_file_mb=100,
                similarity_threshold=0.75,
                skip_dirs=[".git", "node_modules", "__pycache__"],
            ),
        ),
    )


@pytest.fixture
def mock_session():
    """Mock async SQLAlchemy session for unit tests.

    Provides add(), flush(), execute(), commit(), rollback() as AsyncMocks.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def patched_config(mock_config):
    """Patch get_config() globally to return the mock config."""
    with patch("sysadmin.config.get_config", return_value=mock_config):
        with patch("sysadmin.config._config", mock_config):
            yield mock_config


@pytest.fixture
async def test_client(mock_config, mock_session):
    """Async httpx client against the FastAPI app with mocked dependencies.

    Overrides:
    - get_db_session → yields mock_session
    - lifespan → no-op (no DB, scheduler, or agents started)
    """
    from contextlib import asynccontextmanager

    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from sysadmin import __version__
    from sysadmin.database import get_db_session
    from sysadmin.routers.files import router as files_router
    from sysadmin.routers.health import router as health_router
    from sysadmin.routers.logs import router as logs_router
    from sysadmin.routers.projects import router as projects_router
    from sysadmin.routers.sysadmin import router as sysadmin_router

    @asynccontextmanager
    async def noop_lifespan(app):
        yield

    # Build a test app with noop lifespan
    test_app = FastAPI(
        title="SysAdmin Service (test)",
        version=__version__,
        lifespan=noop_lifespan,
    )
    test_app.include_router(health_router)
    test_app.include_router(sysadmin_router)
    test_app.include_router(projects_router)
    test_app.include_router(files_router)
    test_app.include_router(logs_router)

    # Override DB dependency
    async def override_get_db_session():
        yield mock_session

    test_app.dependency_overrides[get_db_session] = override_get_db_session

    # Patch config for routers that call get_config() directly
    with patch("sysadmin.config.get_config", return_value=mock_config):
        with patch("sysadmin.config._config", mock_config):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
