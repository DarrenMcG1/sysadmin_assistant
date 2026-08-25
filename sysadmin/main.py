"""FastAPI application entry point with lifespan management.

Wires together all agents, routers, scheduled jobs, and middleware.

The app is built by :func:`create_app` so tests can construct the REAL
application (same routers, middleware, and exception handlers) with the
production lifespan swapped for a stub — no synthetic test app that can
drift from reality.
"""

import asyncio
import logging
import signal
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
from sysadmin.core.contracts import ReloadResponse, ScanAllResponse
from sysadmin.core.database import (
    create_engine_and_session,
    dispose_engine,
    get_async_session,
    verify_connection,
)
from sysadmin.core.event_bus import event_bus

# Routers
from sysadmin.core.health import router as health_router
from sysadmin.core.jobs import JobSyncReport, JobTargets, apply_jobs
from sysadmin.core.logging_setup import configure_logging
from sysadmin.core.middleware import RequestLoggingMiddleware
from sysadmin.core.retention import run_retention

# Services
from sysadmin.core.scheduler import Scheduler
from sysadmin.core.schema_guard import verify_schema_revision
from sysadmin.core.unit_failure import OWN_UNIT, resolve_unit_failures
from sysadmin.estate.agent import EstateJudgeAgent
from sysadmin.files.agent import FileOrganiserAgent
from sysadmin.files.review import run_weekly_review as run_weekly_disk_review
from sysadmin.files.router import router as files_router

# Agents
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.desktop import desktop_notifier
from sysadmin.monitor.dnd import dnd_manager
from sysadmin.monitor.health_review import run_weekly_review as run_weekly_health_review
from sysadmin.monitor.log_aggregator import LogAggregatorAgent
from sysadmin.monitor.log_review import run_weekly_review as run_weekly_log_review
from sysadmin.monitor.notifier import Notifier
from sysadmin.monitor.reliability_history import record_reliability_snapshot
from sysadmin.monitor.routers.logs import router as logs_router
from sysadmin.monitor.routers.projects_managed import router as projects_managed_router
from sysadmin.monitor.routers.services import router as services_router
from sysadmin.monitor.routers.sysadmin import router as sysadmin_router
from sysadmin.monitor.services import check_plan, load_services_singleton
from sysadmin.reload import ReloadReport, reload_configuration
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
estate_judge_agent = EstateJudgeAgent()

#: Agents holding in-memory state keyed by a configured name. Only these
#: two: the file organiser, service discovery and estate judge key nothing
#: on a service name, so handing them a pruner would be a no-op wearing a
#: contract.
PRUNABLE: tuple = (sysadmin_agent, log_aggregator_agent)

#: Job id -> what runs. ``sysadmin/core/jobs.py`` owns *when* each of these
#: runs and knows nothing about agents; this file owns the instances and
#: knows nothing about triggers. ``tests/test_jobs.py`` asserts the two
#: sets match exactly, so a job planned there and unwired here fails a test
#: rather than being planned, enabled, and silently absent.
JOB_TARGETS: JobTargets = {
    "sysadmin_health_check": sysadmin_agent.run,
    "file_organiser_scan": file_organiser_agent.run,
    "service_discovery_scan": service_discovery_agent.run,
    "estate_judge_poll": estate_judge_agent.run,
    "log_aggregator_poll": log_aggregator_agent.run,
    "desktop_reminder_sweep": desktop_notifier.sweep_reminders,
    "morning_briefing": send_morning_briefing,
    "retention_purge": run_retention,
    "weekly_disk_review": run_weekly_disk_review,
    "weekly_log_review": run_weekly_log_review,
    "weekly_health_review": run_weekly_health_review,
    "reliability_snapshot": record_reliability_snapshot,
}


def _sync_jobs(config) -> JobSyncReport:
    """Make the running scheduler match ``config``.

    Handed to the reload rather than reached for by it: ``sysadmin/reload.py``
    is a composition root and cannot import this one (this file imports it),
    and a module-level scheduler is not something a reload should be
    rummaging for anyway. Passing it also means the reload can be tested
    against a fake host with no APScheduler in the way.
    """
    return apply_jobs(scheduler, config, JOB_TARGETS)


async def _reload_configuration() -> ReloadReport:
    """Both triggers land here, so they cannot come to disagree.

    Off the event loop: two YAML reads and a walk of ~26 ``.project.yaml``
    manifests are blocking I/O, and the API loop is the one serving
    ``/api/sysadmin/events`` to the tray.
    """
    return await asyncio.to_thread(
        reload_configuration, prunable=PRUNABLE, sync_jobs=_sync_jobs
    )


def _install_sighup_handler(loop: asyncio.AbstractEventLoop) -> bool:
    """Make ``kill -HUP <MainPID>`` a reload rather than a kill.

    Worth stating plainly, because it decides how this is tested: Python's
    **default** SIGHUP action terminates the process. Before this handler
    exists a HUP kills the daemon, and ``Restart=always`` brings it back —
    a restart wearing a reload's name. So the signal must never be sent to
    a daemon running code that predates this function.

    ``sysadmin.service`` is a system unit running ``User=gaddi``, so the
    owner can signal it without ``sudo`` — which is the whole point, since
    ``SNAG-UNITS-005`` is a privilege blocker rather than a design one.
    ``systemctl reload`` would additionally need an ``ExecReload=`` line in
    the unit file, and that edit does need ``sudo``; the raw signal does
    not, so the class of blocker is removed without one.

    Registered through ``loop.add_signal_handler`` rather than
    ``signal.signal``: the callback then runs as a normal loop callback
    rather than interrupting arbitrary bytecode, which matters because the
    work it schedules takes a lock.
    """
    try:
        loop.add_signal_handler(signal.SIGHUP, _on_sighup)
    except (NotImplementedError, RuntimeError) as exc:
        logger.warning("sighup_handler_unavailable: %s", exc)
        return False
    return True


def _on_sighup() -> None:
    """Schedule a reload. Never does the work on the signal callback."""
    logger.info("sighup_received")
    asyncio.create_task(_reload_configuration())


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
    #
    # One call, and the same one the reload makes. Registering these inline
    # here is what SNAG-RELOAD-001 was: the config object moved and the
    # scheduler did not, because the triggers were built from a read that
    # happened once, in this function. The plan and the reasoning behind
    # each job now live in `sysadmin/core/jobs.py`.
    job_report = apply_jobs(scheduler, config, JOB_TARGETS)
    if job_report.failed:
        logger.error("jobs_not_scheduled", extra={"failed": job_report.failed})

    scheduler.start()
    logger.info(
        "scheduler started with %d jobs",
        len(scheduler.get_jobs()),
        extra={"added": job_report.added, "disabled": job_report.removed},
    )

    # Expose shared services via app.state
    app.state.scheduler = scheduler
    app.state.event_bus = event_bus
    app.state.notifier = notifier
    app.state.dnd_manager = dnd_manager
    app.state.sysadmin_agent = sysadmin_agent
    app.state.file_organiser_agent = file_organiser_agent
    app.state.log_aggregator_agent = log_aggregator_agent
    app.state.service_discovery_agent = service_discovery_agent

    # Registered last, deliberately. A HUP arriving mid-startup would
    # otherwise reload files the rest of the lifespan is still installing;
    # before this line the signal keeps its default action, which is what
    # every earlier release did anyway.
    sighup = _install_sighup_handler(asyncio.get_running_loop())
    logger.info("startup complete", extra={"sighup_reload": sighup})

    yield

    # --- Shutdown ---
    if sighup:
        asyncio.get_running_loop().remove_signal_handler(signal.SIGHUP)
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

    @app.post(
        "/api/sysadmin/reload",
        tags=["sysadmin"],
        dependencies=[Depends(require_auth)],
        response_model=ReloadResponse,
    )
    async def reload_config():
        """Re-read config.yaml and services.yaml. See :mod:`sysadmin.reload`.

        Defined here rather than in the sysadmin router because
        ``sysadmin.reload`` is a composition root and no domain may import
        one — the same rule that puts ``scan-all`` above in this file.

        Always 200: ``ok`` carries the outcome, and ``requires_restart``
        carries the half a reload cannot do. A non-2xx would make a client
        discard the body, which is the entire product.
        """
        report = await _reload_configuration()
        return report.to_payload()

    return app


app = create_app()
