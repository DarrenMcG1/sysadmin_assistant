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

from sysadmin.services.scheduler import Scheduler


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
        scheduler.schedule_interval(job_id="slow", func=_noop, hours=24)
        next_run = datetime.fromisoformat(_job(scheduler, "slow")["next_run"])
        assert next_run - datetime.now(next_run.tzinfo) > timedelta(hours=23)

    def test_first_run_delay_brings_the_first_fire_forward(self, scheduler):
        scheduler.schedule_interval(
            job_id="slow", func=_noop, hours=24, first_run_delay_seconds=60
        )
        next_run = datetime.fromisoformat(_job(scheduler, "slow")["next_run"])
        delta = next_run - datetime.now(next_run.tzinfo)
        assert timedelta(seconds=0) < delta <= timedelta(seconds=61)

    def test_interval_is_still_honoured(self, scheduler):
        scheduler.schedule_interval(
            job_id="slow", func=_noop, hours=24, first_run_delay_seconds=60
        )
        assert "interval[1 day, 0:00:00]" == _job(scheduler, "slow")["trigger"]

    def test_short_interval_jobs_unaffected(self, scheduler):
        scheduler.schedule_interval(job_id="fast", func=_noop, seconds=60)
        next_run = datetime.fromisoformat(_job(scheduler, "fast")["next_run"])
        delta = next_run - datetime.now(next_run.tzinfo)
        assert delta <= timedelta(seconds=61)


class TestLifespanRegistration:
    """The hours-scale agents must be registered with the delay."""

    def test_organiser_agents_get_a_first_run_delay(self, monkeypatch):
        import inspect

        from sysadmin import main

        source = inspect.getsource(main.lifespan)
        for job in ("project_organiser_scan", "file_organiser_scan"):
            block = source.split(job, 1)[1].split(")", 1)[0]
            assert "first_run_delay_seconds" in block, (
                f"{job} must pass first_run_delay_seconds or it may never run"
            )
