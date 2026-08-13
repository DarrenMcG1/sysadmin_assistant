"""FastAPI application entry point with lifespan management.

Wires together all agents, routers, scheduled jobs, and middleware.

The app is built by :func:`create_app` so tests can construct the REAL
application (same routers, middleware, and exception handlers) with the
production lifespan swapped for a stub — no synthetic test app that can
drift from reality.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from estate.registry import load_registry
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sysadmin import __version__
from sysadmin.briefing.data import send_morning_briefing
from sysadmin.briefing.router import router as summary_router
from sysadmin.core.auth import require_auth
from sysadmin.core.config import get_config, load_config
from sysadmin.core.contracts import ScanAllResponse
from sysadmin.core.database import (
    create_engine_and_session,
    dispose_engine,
    get_async_session,
    verify_connection,
)
from sysadmin.core.event_bus import event_bus

# Routers
from sysadmin.core.health import router as health_router
from sysadmin.core.logging_setup import configure_logging
from sysadmin.core.middleware import RequestLoggingMiddleware
from sysadmin.core.retention import run_retention

# Services
from sysadmin.core.scheduler import Scheduler
from sysadmin.core.schema_guard import verify_schema_revision
from sysadmin.core.unit_failure import OWN_UNIT, resolve_unit_failures
from sysadmin.files.agent import FileOrganiserAgent
from sysadmin.files.review import run_weekly_review as run_weekly_disk_review
from sysadmin.files.router import router as files_router

# Agents
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.desktop import desktop_notifier
from sysadmin.monitor.dnd import dnd_manager
from sysadmin.monitor.log_aggregator import LogAggregatorAgent
from sysadmin.monitor.notifier import Notifier
from sysadmin.monitor.reliability_history import record_reliability_snapshot
from sysadmin.monitor.routers.logs import router as logs_router
from sysadmin.monitor.routers.projects_managed import router as projects_managed_router
from sysadmin.monitor.routers.services import router as services_router
from sysadmin.monitor.routers.sysadmin import router as sysadmin_router
from sysadmin.monitor.services import check_plan, load_services_singleton
from sysadmin.units.agent import ServiceDiscoveryAgent
from sysadmin.units.router import router as units_router

logger = logging.getLogger(__name__)

# --- Shared instances ---
scheduler = Scheduler()
notifier = Notifier()
sysadmin_agent = SysAdminAgent()
file_organiser_agent = FileOrganiserAgent()
log_aggregator_agent = LogAggregatorAgent()
service_discovery_agent = ServiceDiscoveryAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    # --- Startup ---
    config = load_config()

    configure_logging(config.service)

    logger.info(
        "starting sysadmin-service v%s on %s:%d",
        __version__,
        config.service.host,
        config.service.port,
    )

    # API authentication status
    if config.api.auth_token:
        logger.info("API auth enabled — state-changing endpoints require a bearer token")
    else:
        logger.warning(
            "api.auth_token is not set — state-changing endpoints are UNAUTHENTICATED. "
            "Set api.auth_token in config.yaml to enable bearer-token auth."
        )

    # services.yaml, validated against the registry. An id that names no
    # project fails here, at startup, naming every bad reference at once —
    # which is the whole reason services are keyed on id rather than path.
    # A path that names nothing fails silently and did, twice.
    services = load_services_singleton(registry=load_registry(
        config.agents.project_organiser.projects_root
    ))
    logger.info(
        "services_loaded",
        extra={
            "services": len(services.services),
            "projects": len(services.project_ids),
            "unchecked": sum(
                1 for s in services.services if check_plan(s).checks_nothing
            ),
        },
    )

    # Agents publish change events from scheduler threads (each with its own
    # event loop) — bind the API loop so SSE clients are woken on it.
    event_bus.bind_loop(asyncio.get_running_loop())

    # The daemon's own desktop notifications — the tray's understudy,
    # silent whenever the tray is polling.  Subscribed rather than called
    # from raise_alert so ``core`` keeps its rule of never importing a
    # domain, and so notifications fire only after the raising agent's
    # transaction has committed (events are buffered until then).
    event_bus.subscribe("alert.raised", desktop_notifier.on_alert_raised)

    # Initialise database
    await create_engine_and_session()
    await verify_connection()
    logger.info("database connection verified")

    # ...and that it is the schema this code was written for, which is a
    # different question and the one SNAG-DB-001 turned on. Deliberately
    # NOT wrapped in a try: an un-applied migration must stop startup, so
    # the unit enters `failed` and `sysadmin-failed.service` announces it.
    # Contrast the unit-failure resolve below, which IS caught — a stale
    # alert row is worth less than a boot, and a schema mismatch is the
    # exact opposite trade.
    await verify_schema_revision()

    # This service starting IS the recovery from its own unit failure, and
    # this is the only moment that fact exists. `sysadmin-failed.service`
    # writes a critical alert while the application is dead, so no agent
    # can ever observe the recovery — leaving a row that only accumulates,
    # which is how 1,664 orphaned alerts happened once already. Failure
    # here must not stop startup: an unresolved alert is a stale row, and
    # refusing to boot over one would be a worse outcome than the row.
    try:
        async with get_async_session() as session:
            await resolve_unit_failures(session, OWN_UNIT)
    except Exception as exc:  # noqa: BLE001
        logger.warning("could not resolve unit-failure alerts: %s", exc)

    # Start services.  Agents deliberately have no startup hook: they run
    # on scheduler threads, each with its own event loop, so anything
    # loop-bound must be created per run rather than here (SNAG-AGENT-003).
    await notifier.startup()

    # --- Schedule jobs ---
    agents_config = config.agents

    # SysAdmin agent: health checks + resource snapshots
    if agents_config.sysadmin.enabled:
        scheduler.schedule_interval(
            job_id="sysadmin_health_check",
            func=sysadmin_agent.run,
            seconds=agents_config.sysadmin.health_check_interval_seconds,
        )

    # Hours-scale agents also get an explicit first run shortly after
    # startup. IntervalTrigger alone puts the first fire at now + interval,
    # so the 24h file organiser never ran on a box that restarts daily.
    first_run_delay = config.schedules.agent_first_run_delay_seconds

    # File Organiser: filesystem audit
    if agents_config.file_organiser.enabled:
        scheduler.schedule_interval(
            job_id="file_organiser_scan",
            func=file_organiser_agent.run,
            hours=agents_config.file_organiser.scan_interval_hours,
            first_run_delay_seconds=first_run_delay,
        )

    # Service Discovery: installed units vs the wired estate (Session 26).
    # Hours-scale like the other sweeps — unit files change when a project
    # is installed or retired, which is a weekly event at most.
    if agents_config.service_discovery.enabled:
        scheduler.schedule_interval(
            job_id="service_discovery_scan",
            func=service_discovery_agent.run,
            hours=agents_config.service_discovery.scan_interval_hours,
            first_run_delay_seconds=first_run_delay,
        )

    # Log Aggregator: log polling
    if agents_config.log_aggregator.enabled:
        scheduler.schedule_interval(
            job_id="log_aggregator_poll",
            func=log_aggregator_agent.run,
            seconds=agents_config.log_aggregator.poll_interval_seconds,
        )

    # Daily cron jobs — times from config.schedules (defaults 06:00 / 03:00)
    schedules = config.schedules
    scheduler.schedule_cron(
        job_id="morning_briefing",
        func=send_morning_briefing,
        hour=schedules.briefing_hour,
        minute=schedules.briefing_minute,
    )
    scheduler.schedule_cron(
        job_id="retention_purge",
        func=run_retention,
        hour=schedules.retention_hour,
        minute=schedules.retention_minute,
    )
    # Weekly disk review — the slot after the estate's portfolio review
    # (now on 8400, estate ADR-0008 / our ADR-0005) so only one
    # llama-server generation is in flight at a time
    if agents_config.file_organiser.weekly_review:
        scheduler.schedule_cron(
            job_id="weekly_disk_review",
            func=run_weekly_disk_review,
            hour=schedules.disk_review_hour,
            minute=schedules.disk_review_minute,
            day_of_week=schedules.review_day_of_week,
        )
    # Daily reliability snapshot — an hour ahead of the 03:00 retention
    # purge, so the day's score is written before the checks behind it can
    # be deleted. Nothing serves these rows (the endpoint recomputes
    # live); they exist so the score becomes trendable.
    if agents_config.sysadmin.reliability.enabled:
        scheduler.schedule_cron(
            job_id="reliability_snapshot",
            func=record_reliability_snapshot,
            hour=schedules.reliability_hour,
            minute=schedules.reliability_minute,
        )

    scheduler.start()
    logger.info("scheduler started with %d jobs", len(scheduler.get_jobs()))

    # Expose shared services via app.state
    app.state.scheduler = scheduler
    app.state.event_bus = event_bus
    app.state.notifier = notifier
    app.state.dnd_manager = dnd_manager
    app.state.sysadmin_agent = sysadmin_agent
    app.state.file_organiser_agent = file_organiser_agent
    app.state.log_aggregator_agent = log_aggregator_agent
    app.state.service_discovery_agent = service_discovery_agent

    yield

    # --- Shutdown ---
    scheduler.shutdown(wait=False)
    await notifier.shutdown()
    await dispose_engine()
    logger.info("sysadmin-service shut down")


LifespanFactory = Callable[[FastAPI], AbstractAsyncContextManager[None]]


def create_app(lifespan_ctx: LifespanFactory | None = None) -> FastAPI:
    """Build the FastAPI application — real routers, middleware, and handlers.

    ``lifespan_ctx`` lets tests substitute a stub lifespan (no DB engine,
    scheduler, or agent startup) while keeping everything else identical
    to production.
    """
    app = FastAPI(
        title="SysAdmin Service",
        description="Infrastructure monitoring and housekeeping service",
        version=__version__,
        lifespan=lifespan_ctx if lifespan_ctx is not None else lifespan,
    )

    # --- Middleware ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_config().service.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLoggingMiddleware)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch unhandled exceptions and return a JSON 500 response."""
        logger.exception("unhandled_exception", extra={"path": request.url.path})
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # --- Routers ---
    app.include_router(health_router)
    app.include_router(sysadmin_router)
    app.include_router(projects_managed_router)
    app.include_router(files_router)
    app.include_router(logs_router)
    app.include_router(units_router)
    app.include_router(services_router)
    app.include_router(summary_router)

    # --- Trigger-all endpoint ---
    @app.post(
        "/api/sysadmin/scan-all",
        tags=["sysadmin"],
        dependencies=[Depends(require_auth)],
        response_model=ScanAllResponse,
    )
    async def scan_all(request: Request):
        """Trigger all agents to run immediately."""
        state = request.app.state
        asyncio.create_task(state.sysadmin_agent.run(run_type="manual"))
        asyncio.create_task(state.file_organiser_agent.run(run_type="manual"))
        asyncio.create_task(state.log_aggregator_agent.run(run_type="manual"))
        asyncio.create_task(state.service_discovery_agent.run(run_type="manual"))
        return {"status": "all_scans_triggered"}

    return app


app = create_app()
