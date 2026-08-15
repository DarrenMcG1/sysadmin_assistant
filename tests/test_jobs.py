"""The schedule as a plan, and applying it — SNAG-RELOAD-001.

The defect this closes is not that a job had the wrong trigger. It is that
two things said what the schedule was: the ``AppConfig`` a reload had just
installed, and the triggers ``main.py``'s lifespan built once at startup.
Measured live on 2026-08-15 — the config object read 999 and the job went
on firing every 300 s, with ``requires_restart`` naming it once.

So the tests that earn their place here are the ones about *convergence*:
that applying the same plan twice touches nothing (because re-timing
restarts the clock), that a plan can remove as well as add, and that a job
the host refuses is named rather than swallowed.
"""

from datetime import datetime, timedelta

import pytest

from sysadmin.core.config import AppConfig
from sysadmin.core.jobs import (
    JOB_CONFIG_PATHS,
    JobSpec,
    apply_jobs,
    plan_jobs,
)
from sysadmin.core.scheduler import Scheduler


async def _noop() -> None:
    return None


def _targets() -> dict:
    return {spec.job_id: _noop for spec in plan_jobs(AppConfig())}


class FakeHost:
    """The :class:`sysadmin.core.jobs.JobHost` contract, in a dict.

    Mirrors the real wrapper's *semantics*, not its implementation: an
    identical trigger is ``unchanged`` and is not written. ``writes``
    records everything that actually touched the schedule, so a test can
    assert an idempotent apply did nothing rather than merely reporting
    nothing.
    """

    def __init__(self, refuse: set[str] | None = None) -> None:
        self.jobs: dict[str, tuple] = {}
        self.writes: list[str] = []
        self.delays: dict[str, int | None] = {}
        self.refuse = refuse or set()

    def _sync(self, job_id, trigger, delay=None):
        if job_id in self.refuse:
            raise RuntimeError("host refused")
        if self.jobs.get(job_id) == trigger:
            return "unchanged"
        outcome = "retimed" if job_id in self.jobs else "added"
        self.jobs[job_id] = trigger
        if outcome == "added":
            self.delays[job_id] = delay
        self.writes.append(job_id)
        return outcome

    def sync_interval(self, job_id, func, *, seconds=None, minutes=None,
                      hours=None, first_run_delay_seconds=None):
        return self._sync(job_id, ("interval", seconds, minutes, hours),
                          first_run_delay_seconds)

    def sync_cron(self, job_id, func, *, hour=0, minute=0, day_of_week="*"):
        return self._sync(job_id, ("cron", hour, minute, day_of_week))

    def remove_job(self, job_id):
        if job_id in self.refuse:
            raise RuntimeError("host refused")
        if job_id not in self.jobs:
            return False
        del self.jobs[job_id]
        self.writes.append(job_id)
        return True


# ── the plan ─────────────────────────────────────────────────────────


class TestThePlan:
    def test_every_planned_job_is_wired_in_main(self):
        """The two halves of a scheduled job live in different files.

        ``core/jobs.py`` says when it runs and ``main.py`` says what runs.
        A job planned and unwired is a ``KeyError`` at startup; a job wired
        and unplanned never runs at all and looks exactly like one that
        does.
        """
        from sysadmin.main import JOB_TARGETS

        assert {spec.job_id for spec in plan_jobs(AppConfig())} == set(JOB_TARGETS)

    def test_the_plan_is_total_regardless_of_what_is_enabled(self):
        """Rule 3: a disabled job is emitted disabled, never omitted.

        Only a plan that still names it can *remove* it — otherwise
        ``enabled: false`` is a restart-only field wearing a live one's
        name, since a reload would simply not mention the job again.
        """
        config = AppConfig()
        config.agents.file_organiser.enabled = False
        config.agents.estate_judge.enabled = False
        config.agents.sysadmin.reliability.enabled = False

        ids = [spec.job_id for spec in plan_jobs(config)]
        assert ids == [spec.job_id for spec in plan_jobs(AppConfig())]
        by_id = {spec.job_id: spec for spec in plan_jobs(config)}
        assert by_id["file_organiser_scan"].enabled is False
        assert by_id["log_aggregator_poll"].enabled is True

    def test_ids_are_unique(self):
        ids = [spec.job_id for spec in plan_jobs(AppConfig())]
        assert len(ids) == len(set(ids))

    def test_the_trigger_follows_the_config(self):
        config = AppConfig()
        config.agents.sysadmin.health_check_interval_seconds = 999
        config.schedules.briefing_hour = 9
        by_id = {spec.job_id: spec for spec in plan_jobs(config)}
        assert by_id["sysadmin_health_check"].trigger_kwargs == {"seconds": 999}
        assert by_id["morning_briefing"].trigger_kwargs["hour"] == 9

    def test_job_config_paths_is_derived_not_restated(self):
        """It is the reload's third classification — it must cover the plan."""
        declared = {p for spec in plan_jobs(AppConfig()) for p in spec.config_paths}
        assert JOB_CONFIG_PATHS == declared


# ── applying it ──────────────────────────────────────────────────────


class TestApplyJobs:
    def test_a_fresh_host_gets_every_enabled_job(self):
        host = FakeHost()
        report = apply_jobs(host, AppConfig(), _targets())
        assert set(report.added) == set(host.jobs)
        assert not report.retimed and not report.removed and not report.failed

    def test_applying_the_same_config_twice_touches_nothing(self):
        """The rule the whole module turns on.

        ``reschedule_job`` recomputes the next fire from *now*, so a reload
        that re-applied identical triggers would postpone every job by a
        full interval — and a box reloaded more often than its slowest
        interval would never run its slowest agent. That is
        ``agent_first_run_delay_seconds``'s failure with a reload standing
        in for a restart.
        """
        host = FakeHost()
        apply_jobs(host, AppConfig(), _targets())
        host.writes.clear()

        report = apply_jobs(host, AppConfig(), _targets())

        assert host.writes == []
        assert not report.added and not report.retimed and not report.removed
        assert set(report.unchanged) == set(host.jobs)

    def test_a_changed_interval_is_retimed_and_only_that_job(self):
        host = FakeHost()
        apply_jobs(host, AppConfig(), _targets())

        config = AppConfig()
        config.agents.sysadmin.health_check_interval_seconds = 999
        report = apply_jobs(host, config, _targets())

        assert report.retimed == ["sysadmin_health_check"]
        assert host.writes[-1:] == ["sysadmin_health_check"]

    def test_a_changed_cron_is_retimed(self):
        host = FakeHost()
        apply_jobs(host, AppConfig(), _targets())
        config = AppConfig()
        config.schedules.retention_hour = 4
        assert apply_jobs(host, config, _targets()).retimed == ["retention_purge"]

    def test_disabling_an_agent_removes_its_job(self):
        host = FakeHost()
        apply_jobs(host, AppConfig(), _targets())
        config = AppConfig()
        config.agents.file_organiser.enabled = False

        report = apply_jobs(host, config, _targets())

        assert report.removed == ["file_organiser_scan"]
        assert "file_organiser_scan" not in host.jobs

    def test_removing_a_job_that_was_never_scheduled_is_not_reported(self):
        """``removed`` means something was taken away, not that a flag is off."""
        config = AppConfig()
        config.agents.file_organiser.enabled = False
        report = apply_jobs(FakeHost(), config, _targets())
        assert report.removed == []

    def test_re_enabling_adds_it_back_with_the_first_run_delay(self):
        """A newly added hours-scale job must not wait a whole interval.

        Re-enabling is the same situation as a cold start for that job: it
        has no next fire, and ``IntervalTrigger`` alone would put the first
        one 24 hours out — SNAG-AGENT-003's shape.
        """
        host = FakeHost()
        off = AppConfig()
        off.agents.file_organiser.enabled = False
        apply_jobs(host, off, _targets())

        report = apply_jobs(host, AppConfig(), _targets())

        assert report.added == ["file_organiser_scan"]
        assert host.delays["file_organiser_scan"] == (
            AppConfig().schedules.agent_first_run_delay_seconds
        )

    def test_only_planned_ids_are_removed(self):
        """Rule 5: a job this module did not plan belongs to somebody else."""
        host = FakeHost()
        host.jobs["someone_elses_job"] = ("interval", 1, None, None)
        config = AppConfig()
        config.agents.file_organiser.enabled = False

        apply_jobs(host, config, _targets())

        assert "someone_elses_job" in host.jobs

    def test_a_refused_job_is_named_with_its_config_paths(self):
        """The configuration is already installed by the time this runs.

        Failing the reload is not available, so the honest outcome is to
        name what did not take effect — which is what ``requires_restart``
        is for, and after this change is nearly all it is left for.
        """
        host = FakeHost(refuse={"log_aggregator_poll"})
        report = apply_jobs(host, AppConfig(), _targets())

        assert set(report.failed) == {"log_aggregator_poll"}
        assert report.failed_config_paths == [
            "agents.log_aggregator.enabled",
            "agents.log_aggregator.poll_interval_seconds",
        ]

    def test_one_refused_job_does_not_cost_the_others(self):
        host = FakeHost(refuse={"log_aggregator_poll"})
        report = apply_jobs(host, AppConfig(), _targets())
        assert "sysadmin_health_check" in report.added
        assert "reliability_snapshot" in report.added

    def test_specs_can_be_supplied_directly(self):
        """The seam the reload tests use — no AppConfig round trip needed."""
        host = FakeHost()
        spec = JobSpec(
            job_id="one_off",
            enabled=True,
            trigger="interval",
            trigger_kwargs={"seconds": 5},
            config_paths=("service.port",),
        )
        report = apply_jobs(host, AppConfig(), {"one_off": _noop}, specs=[spec])
        assert report.added == ["one_off"]


# ── the real wrapper ─────────────────────────────────────────────────


@pytest.fixture
def scheduler():
    instance = Scheduler()
    instance.start()
    yield instance
    instance.shutdown(wait=False)


def _next_run(scheduler: Scheduler, job_id: str) -> datetime:
    job = next(j for j in scheduler.get_jobs() if j["id"] == job_id)
    return datetime.fromisoformat(job["next_run"])


class TestSchedulerConvergence:
    """APScheduler's half, against the real BackgroundScheduler.

    The fake above encodes what this class proves — worth doing both,
    because the semantics being relied on (``reschedule_job`` recomputes
    the next fire from now; ``str(trigger)`` compares equal for equal
    schedules) are APScheduler's, not ours.
    """

    def test_an_identical_trigger_is_unchanged(self, scheduler):
        assert scheduler.sync_interval("j", _noop, seconds=60) == "added"
        assert scheduler.sync_interval("j", _noop, seconds=60) == "unchanged"

    def test_an_unchanged_job_keeps_its_next_run(self, scheduler):
        """Not cosmetic: this is what stops a reload postponing a job.

        A 24-hour job re-applied on every reload would sit permanently 24
        hours from the most recent reload — which on a box being poked at
        is never.
        """
        scheduler.sync_interval("j", _noop, hours=24, first_run_delay_seconds=60)
        before = _next_run(scheduler, "j")
        scheduler.sync_interval("j", _noop, hours=24, first_run_delay_seconds=60)
        assert _next_run(scheduler, "j") == before

    def test_a_changed_trigger_is_retimed(self, scheduler):
        scheduler.sync_interval("j", _noop, hours=24)
        assert scheduler.sync_interval("j", _noop, hours=6) == "retimed"
        assert "6:00:00" in next(
            j for j in scheduler.get_jobs() if j["id"] == "j"
        )["trigger"]

    def test_retiming_does_not_apply_the_first_run_delay(self, scheduler):
        """Rule 2, measured.

        The job already has a next fire; pulling it forward would turn an
        unrelated threshold edit into a 118-second filesystem scan nobody
        asked for — repeatedly, on a box being reloaded.
        """
        scheduler.sync_interval("j", _noop, hours=24, first_run_delay_seconds=60)
        scheduler.sync_interval("j", _noop, hours=6, first_run_delay_seconds=60)
        delta = _next_run(scheduler, "j") - datetime.now(
            _next_run(scheduler, "j").tzinfo
        )
        assert delta > timedelta(hours=5)

    def test_cron_triggers_compare_equal(self, scheduler):
        assert scheduler.sync_cron("c", _noop, hour=3, minute=0) == "added"
        assert scheduler.sync_cron("c", _noop, hour=3, minute=0) == "unchanged"
        assert scheduler.sync_cron("c", _noop, hour=4, minute=0) == "retimed"

    def test_day_of_week_is_part_of_the_comparison(self, scheduler):
        """The weekly review's only weekly field — missing it would make a
        review moved from Monday to Sunday silently stay on Monday."""
        scheduler.sync_cron("c", _noop, hour=5, minute=30, day_of_week="mon")
        assert scheduler.sync_cron(
            "c", _noop, hour=5, minute=30, day_of_week="sun"
        ) == "retimed"

    def test_removing_an_absent_job_reports_false(self, scheduler):
        assert scheduler.remove_job("nope") is False

    def test_removing_a_present_job_reports_true(self, scheduler):
        scheduler.sync_interval("j", _noop, seconds=60)
        assert scheduler.remove_job("j") is True
        assert scheduler.get_jobs() == []

    def test_the_plan_applies_to_the_real_scheduler(self, scheduler):
        """End to end, with nothing faked: plan -> apply -> apply again."""
        first = apply_jobs(scheduler, AppConfig(), _targets())
        second = apply_jobs(scheduler, AppConfig(), _targets())
        assert len(first.added) == len(scheduler.get_jobs())
        assert not second.added and not second.retimed
        assert len(second.unchanged) == len(scheduler.get_jobs())
