"""APScheduler wrapper for scheduling agent jobs.

Uses BackgroundScheduler (thread pool) with asyncio.run() bridge
for executing async agent code from scheduler threads.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED, EVENT_JOB_EXECUTED
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def _run_async(coro_fn: Callable[..., Coroutine], *args: Any, **kwargs: Any) -> Any:
    """Bridge: run an async function in a new event loop (for scheduler threads)."""
    return asyncio.run(coro_fn(*args, **kwargs))


class Scheduler:
    """Wrapper around APScheduler's BackgroundScheduler."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 300,
            }
        )
        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self._scheduler.add_listener(self._on_job_missed, EVENT_JOB_MISSED)
        self._scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)

    def schedule_interval(
        self,
        job_id: str,
        func: Callable[..., Coroutine],
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Schedule an async function to run at a fixed interval."""
        trigger_kwargs: dict[str, Any] = {}
        if seconds is not None:
            trigger_kwargs["seconds"] = seconds
        if minutes is not None:
            trigger_kwargs["minutes"] = minutes
        if hours is not None:
            trigger_kwargs["hours"] = hours

        self._scheduler.add_job(
            _run_async,
            trigger=IntervalTrigger(**trigger_kwargs),
            id=job_id,
            args=[func],
            replace_existing=True,
            **kwargs,
        )
        logger.info("scheduled_interval_job", extra={"job_id": job_id, "trigger": trigger_kwargs})

    def schedule_cron(
        self,
        job_id: str,
        func: Callable[..., Coroutine],
        hour: int | str = 0,
        minute: int | str = 0,
        day_of_week: str = "*",
        **kwargs: Any,
    ) -> None:
        """Schedule an async function to run on a cron schedule."""
        self._scheduler.add_job(
            _run_async,
            trigger=CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week),
            id=job_id,
            args=[func],
            replace_existing=True,
            **kwargs,
        )
        logger.info(
            "scheduled_cron_job",
            extra={"job_id": job_id, "hour": hour, "minute": minute},
        )

    def start(self) -> None:
        """Start the scheduler."""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("scheduler_started")

    def shutdown(self, wait: bool = True) -> None:
        """Shut down the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("scheduler_shutdown")

    def get_jobs(self) -> list[dict[str, Any]]:
        """Return info about all scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self._scheduler.get_jobs()
        ]

    @staticmethod
    def _on_job_error(event) -> None:
        logger.error(
            "scheduler_job_error",
            extra={
                "job_id": event.job_id,
                "error": str(event.exception),
            },
            exc_info=event.exception,
        )

    @staticmethod
    def _on_job_missed(event) -> None:
        logger.warning(
            "scheduler_job_missed",
            extra={"job_id": event.job_id},
        )

    @staticmethod
    def _on_job_executed(event) -> None:
        logger.debug(
            "scheduler_job_executed",
            extra={"job_id": event.job_id},
        )
