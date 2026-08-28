"""Shared test fixtures for the sysadmin backend test suite.

Provides:
- Mock AppConfig with sensible test defaults
- Mock async DB session (no real database needed for unit tests)
- The REAL FastAPI app (via ``sysadmin.main.create_app``) with the
  production lifespan stubbed and the DB dependency overridden — same
  routers, middleware stack, and exception handlers as production.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from sysadmin.core.config import (
    AgentsConfig,
    AppConfig,
    DatabaseConfig,
    FileOrganiserConfig,
    ProjectOrganiserConfig,
    ServiceConfig,
    SysAdminAgentConfig,
    Thresholds,
)
from sysadmin.monitor import services as services_module
from sysadmin.monitor.services import ServiceEntry, ServicesFile

#: The services every test sees unless it installs its own. Mirrors the
#: shapes that matter: an http service with no unit, a tcp one, a
#: controllable systemd unit and a non-controllable one.
DEFAULT_TEST_SERVICES = [
    {"name": "test-api", "kind": "http", "url": "http://localhost:9999/health"},
    {"name": "test-tcp", "kind": "tcp", "host": "localhost", "port": 5432},
    {"name": "test-systemd", "kind": "systemd",
     "systemd": {"unit": "test.service", "scope": "system"}},
    {"name": "test-infra", "kind": "systemd", "controllable": False,
     "systemd": {"unit": "infra.service", "scope": "system"}},
]


def set_services(*entries: dict | ServiceEntry) -> ServicesFile:
    """Install a services.yaml for the duration of one test.

    Written into the module singleton rather than patched per import site:
    ``get_services`` is imported by name in half a dozen modules, so
    patching the function would need one target per consumer and would
    silently miss the next one.
    """
    parsed = [
        e if isinstance(e, ServiceEntry) else ServiceEntry.model_validate(e)
        for e in entries
    ]
    services_module._services = ServicesFile(schema=1, services=parsed)
    return services_module._services


@pytest.fixture(autouse=True)
def services():
    """Default service list, reset after every test."""
    installed = set_services(*DEFAULT_TEST_SERVICES)
    yield installed
    services_module._services = None

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

    ``execute`` answers with an **empty result** rather than a bare
    ``AsyncMock``.  A bare one returns a coroutine from ``.scalars()``,
    so a caller writing the ordinary ``.scalars().first()`` gets
    ``AttributeError`` on a coroutine — a stand-in failing in a way no
    database does, and a test that then reads as a bug in the code under
    it.  Any test wanting rows back sets ``return_value`` itself.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.__iter__ = lambda self: iter(())
    session.execute = AsyncMock(return_value=result)
    return session


@pytest.fixture
def patched_config(mock_config):
    """Patch get_config() globally to return the mock config."""
    with patch("sysadmin.core.config.get_config", return_value=mock_config):
        with patch("sysadmin.core.config._config", mock_config):
            yield mock_config


def _stub_app_state(app) -> None:
    """Install the shared-state objects the real lifespan would set.

    The httpx ASGITransport never runs the lifespan, so the agents,
    scheduler, and notifier the routers reach via ``app.state`` are
    stubbed here with mocks (agents get an AsyncMock ``run``).
    """
    app.state.scheduler = MagicMock()
    app.state.event_bus = MagicMock()
    app.state.notifier = MagicMock()
    app.state.dnd_manager = MagicMock()
    for name in (
        "sysadmin_agent",
        "project_organiser_agent",
        "file_organiser_agent",
        "log_aggregator_agent",
        "service_discovery_agent",
    ):
        agent = MagicMock()
        agent.run = AsyncMock(return_value=None)
        setattr(app.state, name, agent)


@pytest.fixture
def test_app(mock_config, mock_session):
    """The REAL application — built by the same factory as production.

    Only the lifespan (DB engine, scheduler, agent startup) is stubbed;
    routers, middleware, exception handlers, and route dependencies are
    exactly what ``sysadmin.main.create_app`` wires in production.
    """
    from contextlib import asynccontextmanager

    from sysadmin.core.database import get_db_session
    from sysadmin.main import create_app

    @asynccontextmanager
    async def stub_lifespan(app):
        yield

    app = create_app(lifespan_ctx=stub_lifespan)
    _stub_app_state(app)

    async def override_get_db_session():
        yield mock_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    return app


@pytest.fixture
async def test_client(test_app, mock_config):
    """Async httpx client against the real app with mocked dependencies."""
    # Patch config for routers that call get_config() directly
    with patch("sysadmin.core.config.get_config", return_value=mock_config):
        with patch("sysadmin.core.config._config", mock_config):
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client
