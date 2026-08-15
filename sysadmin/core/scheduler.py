"""APScheduler wrapper for scheduling agent jobs.

Uses BackgroundScheduler (thread pool) with asyncio.run() bridge
for executing async agent code from scheduler threads.

The two ``sync_*`` methods are **converging**, not additive: they take the
schedule a job should be on and do whatever is needed to get it there —
add it, re-time it, or nothing. There is deliberately no separate "add"
entry point. A caller with both would have to decide which to use, and
that decision is exactly what :mod:`sysadmin.core.jobs` exists to take
away from the two composition roots that schedule anything.

Whether a trigger has changed is decided by comparing it to the **live**
job's trigger, and ``str(trigger)`` is what does the comparing:
APScheduler's own ``__str__`` is derived from the trigger's fields
(``interval[0:05:00]``, ``cron[hour='6', minute='0']``), so equal
schedules compare equal without this module reimplementing trigger
equality. Reading the live job rather than remembering what was last
installed is the point — a remembered plan is a second statement about
what the scheduler is doing, and ``SNAG-RELOAD-001`` is what two such
statements cost.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import datetime, timedelta
from typing import Any, Literal

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, EVENT_JOB_MISSED
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

#: What one ``sync_*`` call did. Reported per job by
#: :func:`sysadmin.core.jobs.apply_jobs`.
Outcome = Literal["added", "retimed", "unchanged"]


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

    def sync_interval(
        self,
        job_id: str,
        func: Callable[..., Coroutine],
        *,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        first_run_delay_seconds: int | None = None,
        **kwargs: Any,
    ) -> Outcome:
        """Put ``job_id`` on a fixed interval, adding or re-timing as needed.

        ``first_run_delay_seconds`` brings the *first* execution forward to
        ``now + delay``.  Without it APScheduler schedules the first fire at
        ``now + interval``, so a job whose interval is longer than the
        service's uptime between restarts never runs — pass it for any
        hours-scale job.

        It applies **only when the job is added**. Re-timing an existing job
        already leaves it with a next fire; pulling that forward would mean
        an unrelated config edit triggers a 118-second filesystem scan
        nobody asked for, and a reload loop would do so repeatedly.
        """
        trigger_kwargs: dict[str, Any] = {}
        if seconds is not None:
            trigger_kwargs["seconds"] = seconds
        if minutes is not None:
            trigger_kwargs["minutes"] = minutes
        if hours is not None:
            trigger_kwargs["hours"] = hours

        return self._sync(
            job_id,
            func,
            IntervalTrigger(**trigger_kwargs),
            first_run_delay_seconds=first_run_delay_seconds,
            **kwargs,
        )

    def sync_cron(
        self,
        job_id: str,
        func: Callable[..., Coroutine],
        *,
        hour: int | str = 0,
        minute: int | str = 0,
        day_of_week: str = "*",
        **kwargs: Any,
    ) -> Outcome:
        """Put ``job_id`` on a cron schedule, adding or re-timing as needed."""
        return self._sync(
            job_id,
            func,
            CronTrigger(hour=hour, minute=minute, day_of_week=day_of_week),
            **kwargs,
        )

    def _sync(
        self,
        job_id: str,
        func: Callable[..., Coroutine],
        trigger: Any,
        *,
        first_run_delay_seconds: int | None = None,
        **kwargs: Any,
    ) -> Outcome:
        """Add, re-time, or leave alone. The one place that decides which.

        Re-timing is ``reschedule_job``, which recomputes the next fire from
        *now* — so leaving an unchanged trigger alone is not an
        optimisation, it is what stops a reload from postponing every job by
        a full interval.
        """
        existing = self._scheduler.get_job(job_id)
        if existing is not None:
            if str(existing.trigger) == str(trigger):
                return "unchanged"
            self._scheduler.reschedule_job(job_id, trigger=trigger)
            logger.info(
                "rescheduled_job",
                extra={
                    "job_id": job_id,
                    "was": str(existing.trigger),
                    "now": str(trigger),
                },
            )
            return "retimed"

        if first_run_delay_seconds is not None:
            kwargs["next_run_time"] = datetime.now() + timedelta(
                seconds=first_run_delay_seconds
            )
        self._scheduler.add_job(
            _run_async,
            trigger=trigger,
            id=job_id,
            args=[func],
            replace_existing=True,
            **kwargs,
        )
        logger.info(
            "scheduled_job", extra={"job_id": job_id, "trigger": str(trigger)}
        )
        return "added"

    def remove_job(self, job_id: str) -> bool:
        """Drop a job. ``False`` if it was not scheduled in the first place.

        The return value is what lets a reload report ``removed`` honestly:
        an agent disabled in a config that already had it disabled did not
        have a job taken away from it.
        """
        try:
            self._scheduler.remove_job(job_id)
        except JobLookupError:
            return False
        logger.info("removed_job", extra={"job_id": job_id})
        return True

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
        """Return info about all scheduled jobs.

        ``next_run_time`` is absent on jobs added before the scheduler
        starts (APScheduler leaves them pending), hence the ``getattr``.
        """
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = getattr(job, "next_run_time", None)
            jobs.append({
                "id": job.id,
                "next_run": str(next_run) if next_run else None,
                "trigger": str(job.trigger),
            })
        return jobs

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
