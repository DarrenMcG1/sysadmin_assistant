"""FastAPI application entry point with lifespan management.

Wires together all agents, routers, scheduled jobs, and middleware.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sysadmin import __version__
from sysadmin.auth import require_auth
from sysadmin.config import load_config
from sysadmin.database import create_engine_and_session, dispose_engine, verify_connection
from sysadmin.logging_setup import configure_logging
from sysadmin.middleware import RequestLoggingMiddleware

# Agents
from sysadmin.agents.sysadmin_agent import SysAdminAgent
from sysadmin.agents.project_organiser import ProjectOrganiserAgent
from sysadmin.agents.file_organiser import FileOrganiserAgent
from sysadmin.agents.log_aggregator import LogAggregatorAgent

# Services
from sysadmin.services.scheduler import Scheduler
from sysadmin.services.event_bus import EventBus
from sysadmin.services.notifier import Notifier
from sysadmin.services.briefing import send_morning_briefing
from sysadmin.services.dnd import dnd_manager
from sysadmin.services.retention import run_retention

# Routers
from sysadmin.routers.health import router as health_router
from sysadmin.routers.sysadmin import router as sysadmin_router
from sysadmin.routers.projects import router as projects_router
from sysadmin.routers.files import router as files_router
from sysadmin.routers.logs import router as logs_router
from sysadmin.routers.summary import router as summary_router

logger = logging.getLogger(__name__)

# --- Shared instances ---
scheduler = Scheduler()
event_bus = EventBus()
notifier = Notifier()
sysadmin_agent = SysAdminAgent()
project_organiser_agent = ProjectOrganiserAgent()
file_organiser_agent = FileOrganiserAgent()
log_aggregator_agent = LogAggregatorAgent()


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

    # Initialise database
    await create_engine_and_session()
    await verify_connection()
    logger.info("database connection verified")

    # Start services
    await notifier.startup()
    await sysadmin_agent.startup()
    await log_aggregator_agent.startup()

    # --- Schedule jobs ---
    agents_config = config.agents

    # SysAdmin agent: health checks + resource snapshots
    if agents_config.sysadmin.enabled:
        scheduler.schedule_interval(
            job_id="sysadmin_health_check",
            func=sysadmin_agent.run,
            seconds=agents_config.sysadmin.health_check_interval_seconds,
        )

    # Project Organiser: project scanning
    if agents_config.project_organiser.enabled:
        scheduler.schedule_interval(
            job_id="project_organiser_scan",
            func=project_organiser_agent.run,
            hours=agents_config.project_organiser.scan_interval_hours,
        )

    # File Organiser: filesystem audit
    if agents_config.file_organiser.enabled:
        scheduler.schedule_interval(
            job_id="file_organiser_scan",
            func=file_organiser_agent.run,
            hours=agents_config.file_organiser.scan_interval_hours,
        )

    # Log Aggregator: log polling
    if agents_config.log_aggregator.enabled:
        scheduler.schedule_interval(
            job_id="log_aggregator_poll",
            func=log_aggregator_agent.run,
            seconds=agents_config.log_aggregator.poll_interval_seconds,
        )

    # Morning briefing: daily at 06:00
    scheduler.schedule_cron(
        job_id="morning_briefing",
        func=send_morning_briefing,
        hour=6,
        minute=0,
    )

    # Retention: daily at 03:00
    scheduler.schedule_cron(
        job_id="retention_purge",
        func=run_retention,
        hour=3,
        minute=0,
    )

    scheduler.start()
    logger.info("scheduler started with %d jobs", len(scheduler.get_jobs()))

    # Expose shared services via app.state
    app.state.scheduler = scheduler
    app.state.event_bus = event_bus
    app.state.notifier = notifier
    app.state.dnd_manager = dnd_manager
    app.state.sysadmin_agent = sysadmin_agent
    app.state.project_organiser_agent = project_organiser_agent
    app.state.file_organiser_agent = file_organiser_agent
    app.state.log_aggregator_agent = log_aggregator_agent

    yield

    # --- Shutdown ---
    scheduler.shutdown(wait=False)
    await sysadmin_agent.shutdown()
    await log_aggregator_agent.shutdown()
    await notifier.shutdown()
    await dispose_engine()
    logger.info("sysadmin-service shut down")


app = FastAPI(
    title="SysAdmin Service",
    description="Infrastructure monitoring and housekeeping service",
    version=__version__,
    lifespan=lifespan,
)

# --- Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
app.include_router(projects_router)
app.include_router(files_router)
app.include_router(logs_router)
app.include_router(summary_router)


# --- Trigger-all endpoint ---
@app.post(
    "/api/sysadmin/scan-all",
    tags=["sysadmin"],
    dependencies=[Depends(require_auth)],
)
async def scan_all():
    """Trigger all agents to run immediately."""
    asyncio.create_task(sysadmin_agent.run(run_type="manual"))
    asyncio.create_task(project_organiser_agent.run(run_type="manual"))
    asyncio.create_task(file_organiser_agent.run(run_type="manual"))
    asyncio.create_task(log_aggregator_agent.run(run_type="manual"))
    return {"status": "all_scans_triggered"}
