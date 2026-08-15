"""Tests for the APScheduler wrapper — in particular the first-run delay.

Session 18 root cause: ``/api/sysadmin/self`` reported that the
file_organiser agent had never run (zero rows in ``agent_runs``).  The
cause was not the agent but the trigger: APScheduler's ``IntervalTrigger``
schedules the *first* fire at ``now + interval``, so a 24-hour job on a
machine that restarts daily never reaches its first execution.  The fix
is an explicit ``next_run_time`` shortly after startup for hours-scale
jobs, which is what these tests pin.
"""

from datetime import datetime, timedelta

import pytest

from sysadmin.core.scheduler import Scheduler


async def _noop() -> None:
    return None


@pytest.fixture
def scheduler():
    """A started scheduler — APScheduler only computes ``next_run_time``
    once running, and production starts it the same way."""
    instance = Scheduler()
    instance.start()
    yield instance
    instance.shutdown(wait=False)


def _job(scheduler: Scheduler, job_id: str):
    return next(j for j in scheduler.get_jobs() if j["id"] == job_id)


class TestFirstRunDelay:
    def test_long_interval_without_delay_waits_a_whole_interval(self, scheduler):
        """The old behaviour — kept as documentation of the bug."""
        scheduler.sync_interval(job_id="slow", func=_noop, hours=24)
        next_run = datetime.fromisoformat(_job(scheduler, "slow")["next_run"])
        assert next_run - datetime.now(next_run.tzinfo) > timedelta(hours=23)

    def test_first_run_delay_brings_the_first_fire_forward(self, scheduler):
        scheduler.sync_interval(
            job_id="slow", func=_noop, hours=24, first_run_delay_seconds=60
        )
        next_run = datetime.fromisoformat(_job(scheduler, "slow")["next_run"])
        delta = next_run - datetime.now(next_run.tzinfo)
        assert timedelta(seconds=0) < delta <= timedelta(seconds=61)

    def test_interval_is_still_honoured(self, scheduler):
        scheduler.sync_interval(
            job_id="slow", func=_noop, hours=24, first_run_delay_seconds=60
        )
        assert "interval[1 day, 0:00:00]" == _job(scheduler, "slow")["trigger"]

    def test_short_interval_jobs_unaffected(self, scheduler):
        scheduler.sync_interval(job_id="fast", func=_noop, seconds=60)
        next_run = datetime.fromisoformat(_job(scheduler, "fast")["next_run"])
        delta = next_run - datetime.now(next_run.tzinfo)
        assert delta <= timedelta(seconds=61)


class TestPlanRegistration:
    """The hours-scale agents must be planned with the delay.

    This used to read ``main.py``'s lifespan source for the string
    ``first_run_delay_seconds`` near a job id. Session 50 moved the
    registration into ``sysadmin/core/jobs.py``, so it now asks the plan
    itself — which is both a real assertion and a total one: every
    hours-scale interval job is covered, not the one name someone
    remembered to list.
    """

    def test_every_hours_scale_interval_job_gets_a_first_run_delay(self):
        from sysadmin.core.config import AppConfig
        from sysadmin.core.jobs import plan_jobs

        missing = [
            spec.job_id
            for spec in plan_jobs(AppConfig())
            if spec.trigger == "interval"
            and "hours" in spec.trigger_kwargs
            and not spec.first_run_delay_seconds
        ]
        assert not missing, (
            f"{missing} may never run: IntervalTrigger puts the first fire "
            "at now + interval"
        )

    def test_seconds_scale_jobs_do_not_ask_for_one(self):
        """Not decoration: a delay is only applied when a job is *added*,
        and a job that fires every 60 s needs no help reaching its first
        run. Asking for one anyway would be cargo."""
        from sysadmin.core.config import AppConfig
        from sysadmin.core.jobs import plan_jobs

        for spec in plan_jobs(AppConfig()):
            if spec.trigger == "interval" and "seconds" in spec.trigger_kwargs:
                assert spec.first_run_delay_seconds is None
