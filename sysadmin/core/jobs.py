"""The schedule a configuration asks for, and making the scheduler match.

``main.py`` used to register its jobs inline, in the lifespan, from the
config object it had just loaded. That inlining is why ``SNAG-RELOAD-001``
exists: :mod:`sysadmin.reload` installs a new :class:`AppConfig` and the
running scheduler goes on obeying triggers built at startup, so
``get_config().agents.sysadmin.health_check_interval_seconds`` reads 999
while the job keeps firing every 300 s — measured live on 2026-08-15. The
divergence was named **once**, in ``requires_restart``, which is the
warning-fires-once shape Session 39 spent itself removing: an operator who
reloads and walks away has nothing that still says the scheduler is not
obeying config.yaml.

So the fix is a plan both paths share. :func:`plan_jobs` maps an
``AppConfig`` to the jobs it asks for; :func:`apply_jobs` makes a scheduler
match that plan. The lifespan calls it once at startup and the reload calls
it again with the new config, so **the schedule at startup and the schedule
after a reload are produced by the same function** — the rule
``_reload_configuration`` already applies to its two triggers, one layer
down.

This is ``core`` rather than a fourth composition root beside ``main.py``
and ``reload.py`` because it imports no domain and knows no agent: the
callables are handed in as :data:`JobTargets`, keyed by job id. What it
knows is ``AppConfig`` and the shape of a trigger, which is the layer
``core.scheduler`` already occupies beside it.

Five rules, three of them the opposite of the obvious implementation:

1. **A job whose trigger has not changed is not touched.**
   ``reschedule_job`` recomputes the next fire from *now*, so re-applying
   every job on every reload pushes every job out by a full interval — a
   daily file organiser on a box reloaded daily never runs, which is the
   failure ``config.yaml`` already records at ``agent_first_run_delay_seconds``
   with a reload standing in for a restart. The comparison is against the
   **live trigger**, never a remembered plan: a remembered plan is a second
   statement of what the scheduler is doing, and two statements that can
   disagree is the defect this module was written to close.

2. **A job being added gets the first-run delay; a job being re-timed does
   not.** Added means this process has never scheduled it, and
   ``IntervalTrigger`` alone puts the first fire at ``now + interval`` —
   SNAG-AGENT-003's shape, a 24-hour agent on a box that restarts daily.
   Re-timed means it already has a next fire, and bringing that forward
   would turn an operator's threshold edit into a 118-second filesystem
   scan nobody asked for.

3. **The plan is total: a disabled job is emitted disabled, never
   omitted.** Only a plan that still names it can *remove* it, and an
   ``enabled: false`` that merely stops a job being added at startup is a
   restart-only field wearing a live one's name. It also makes
   :data:`JOB_CONFIG_PATHS` computable from a default config, rather than
   from a guess about which branches some other config would have taken.

4. **Every spec names the config leaves that produced it.** That
   declaration is what :mod:`sysadmin.reload` classifies and reports from,
   and ``tests/test_reload.py`` requires it to equal the paths
   :func:`plan_jobs` actually reads. A hand-maintained classification that
   nothing checks is the SNAG-CFG-001 shape, and this one decides what an
   operator is told about their own edit.

5. **Only planned ids are removed.** A job id this module does not plan
   belongs to whoever added it; sweeping the scheduler down to the plan
   would make a reload delete work it knows nothing about. The same
   scoping rule as the estate judge's sweep, which touches only the rows
   its own run judged.
"""

import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

from sysadmin.core.config import AppConfig

logger = logging.getLogger(__name__)

#: An agent entry point. Async, because the scheduler bridges with
#: ``asyncio.run`` on its own thread.
JobFunc = Callable[..., Coroutine[Any, Any, Any]]

#: Job id -> the coroutine function to run. Supplied by ``main.py``, which
#: owns the agent instances; this module owns only when they run.
JobTargets = Mapping[str, JobFunc]

#: What :meth:`JobHost.sync_interval` reports about one job.
Outcome = Literal["added", "retimed", "unchanged"]

#: Floor on the desktop reminder sweep's interval, in seconds. The sweep's
#: cadence is derived from ``notifications.desktop.tray_grace_seconds``
#: rather than configured; this stops a grace window tuned down to a few
#: seconds from turning a derivation into a hot loop.
MIN_REMINDER_SWEEP_SECONDS = 60


@dataclass(frozen=True)
class JobSpec:
    """One scheduled job, as a configuration asks for it.

    ``enabled=False`` is a real member of the plan — see rule 3. It is the
    only way ``apply_jobs`` can tell "the operator turned this off" from
    "some other part of the process added a job".
    """

    job_id: str
    enabled: bool
    trigger: Literal["interval", "cron"]
    #: Passed straight to the host: ``seconds``/``hours`` for an interval,
    #: ``hour``/``minute``/``day_of_week`` for a cron.
    trigger_kwargs: Mapping[str, int | str]
    #: The config leaves that decided this job's existence and its timing.
    #: Reported by the reload when a sync fails; checked against the source
    #: by ``tests/test_reload.py``.
    config_paths: tuple[str, ...]
    #: Only ever applied when the job is *added* — rule 2.
    first_run_delay_seconds: int | None = None


class JobHost(Protocol):
    """The half of :class:`sysadmin.core.scheduler.Scheduler` this needs.

    A Protocol rather than the class itself so the plan can be applied to
    a fake in tests without APScheduler in the way — and so this module
    states what it needs rather than inheriting everything the wrapper
    happens to expose.
    """

    def sync_interval(
        self,
        job_id: str,
        func: JobFunc,
        *,
        seconds: int | None = None,
        minutes: int | None = None,
        hours: int | None = None,
        first_run_delay_seconds: int | None = None,
    ) -> Outcome: ...

    def sync_cron(
        self,
        job_id: str,
        func: JobFunc,
        *,
        hour: int | str = 0,
        minute: int | str = 0,
        day_of_week: str = "*",
    ) -> Outcome: ...

    def remove_job(self, job_id: str) -> bool: ...


def plan_jobs(config: AppConfig) -> tuple[JobSpec, ...]:
    """Every job this service can run, as this configuration asks for it.

    Total by construction (rule 3): the returned ids do not depend on the
    values, only the ``enabled`` flags and the triggers do. ``main.py``'s
    :data:`JOB_TARGETS` is checked against this set, so a job planned here
    and never wired there fails a test rather than silently never running.
    """
    agents = config.agents
    schedules = config.schedules
    desktop = config.notifications.desktop

    # Hours-scale interval jobs also get an explicit first run shortly
    # after startup. IntervalTrigger alone puts the first fire at
    # now + interval, so the 24 h file organiser never ran on a box that
    # restarts daily. Seconds-scale jobs need no such help.
    delay = schedules.agent_first_run_delay_seconds

    return (
        # SysAdmin agent: health checks + resource snapshots.
        JobSpec(
            job_id="sysadmin_health_check",
            enabled=agents.sysadmin.enabled,
            trigger="interval",
            trigger_kwargs={"seconds": agents.sysadmin.health_check_interval_seconds},
            config_paths=(
                "agents.sysadmin.enabled",
                "agents.sysadmin.health_check_interval_seconds",
            ),
        ),
        # File Organiser: filesystem audit.
        JobSpec(
            job_id="file_organiser_scan",
            enabled=agents.file_organiser.enabled,
            trigger="interval",
            trigger_kwargs={"hours": agents.file_organiser.scan_interval_hours},
            config_paths=(
                "agents.file_organiser.enabled",
                "agents.file_organiser.scan_interval_hours",
                "schedules.agent_first_run_delay_seconds",
            ),
            first_run_delay_seconds=delay,
        ),
        # Service Discovery: installed units vs the wired estate (Session
        # 26). Hours-scale like the other sweeps — unit files change when a
        # project is installed or retired, which is a weekly event at most.
        JobSpec(
            job_id="service_discovery_scan",
            enabled=agents.service_discovery.enabled,
            trigger="interval",
            trigger_kwargs={"hours": agents.service_discovery.scan_interval_hours},
            config_paths=(
                "agents.service_discovery.enabled",
                "agents.service_discovery.scan_interval_hours",
                "schedules.agent_first_run_delay_seconds",
            ),
            first_run_delay_seconds=delay,
        ),
        # Estate Judge: the estate publishes, this judges (ADR-0005).
        # Hourly rather than at the sysadmin agent's 300 s, because the
        # producers change twice a day and `attention` re-walks ~26
        # manifests from disk on every request.
        JobSpec(
            job_id="estate_judge_poll",
            enabled=agents.estate_judge.enabled,
            trigger="interval",
            trigger_kwargs={"hours": agents.estate_judge.poll_interval_hours},
            config_paths=(
                "agents.estate_judge.enabled",
                "agents.estate_judge.poll_interval_hours",
                "schedules.agent_first_run_delay_seconds",
            ),
            first_run_delay_seconds=delay,
        ),
        # Log Aggregator: log polling.
        JobSpec(
            job_id="log_aggregator_poll",
            enabled=agents.log_aggregator.enabled,
            trigger="interval",
            trigger_kwargs={"seconds": agents.log_aggregator.poll_interval_seconds},
            config_paths=(
                "agents.log_aggregator.enabled",
                "agents.log_aggregator.poll_interval_seconds",
            ),
        ),
        # The tray's understudy restating a fault it announced that is
        # still open (SNAG-TRAY-007). A job rather than a call at the end
        # of an agent run, because an agent reminding on the notifier's
        # behalf is a second owner of a lifecycle that module owns.
        #
        # The interval is *derived*: the sweep asks "is a reminder due"
        # and "is the tray still absent", and `tray_grace_seconds` is
        # already that section's answer to how long before the daemon
        # decides the tray is not doing this. A second leaf would be a
        # number invented to sit beside one that already means the right
        # thing. Floored so a grace window tuned down to a few seconds
        # cannot make a hot loop of it; a sweep with nothing announced
        # issues no query and reads no further config, so the floor costs
        # a dict lookup.
        JobSpec(
            job_id="desktop_reminder_sweep",
            enabled=desktop.enabled,
            trigger="interval",
            trigger_kwargs={
                "seconds": max(MIN_REMINDER_SWEEP_SECONDS, desktop.tray_grace_seconds)
            },
            config_paths=(
                "notifications.desktop.enabled",
                "notifications.desktop.tray_grace_seconds",
            ),
        ),
        # Daily cron jobs. Unconditional: the briefing and the retention
        # purge have no kill switch, which is deliberate — a service that
        # stops purging quietly grows a 598,091-row alerts table.
        JobSpec(
            job_id="morning_briefing",
            enabled=True,
            trigger="cron",
            trigger_kwargs={
                "hour": schedules.briefing_hour,
                "minute": schedules.briefing_minute,
            },
            config_paths=("schedules.briefing_hour", "schedules.briefing_minute"),
        ),
        JobSpec(
            job_id="retention_purge",
            enabled=True,
            trigger="cron",
            trigger_kwargs={
                "hour": schedules.retention_hour,
                "minute": schedules.retention_minute,
            },
            config_paths=("schedules.retention_hour", "schedules.retention_minute"),
        ),
        # Weekly log review — Session 27, Tier 3. First in the Monday
        # chain rather than last: the briefing at 06:00 is fixed, the
        # estate's portfolio review holds 05:30 and the disk review
        # 05:45, so the free 15-minute slot is the one before them.
        JobSpec(
            job_id="weekly_log_review",
            enabled=agents.log_aggregator.weekly_review,
            trigger="cron",
            trigger_kwargs={
                "hour": schedules.log_review_hour,
                "minute": schedules.log_review_minute,
                "day_of_week": schedules.review_day_of_week,
            },
            config_paths=(
                "agents.log_aggregator.weekly_review",
                "schedules.log_review_hour",
                "schedules.log_review_minute",
                "schedules.review_day_of_week",
            ),
        ),
        # Weekly disk review — the slot after the estate's portfolio review
        # (now on 8400, estate ADR-0008 / our ADR-0005) so only one
        # llama-server generation is in flight at a time.
        JobSpec(
            job_id="weekly_disk_review",
            enabled=agents.file_organiser.weekly_review,
            trigger="cron",
            trigger_kwargs={
                "hour": schedules.disk_review_hour,
                "minute": schedules.disk_review_minute,
                "day_of_week": schedules.review_day_of_week,
            },
            config_paths=(
                "agents.file_organiser.weekly_review",
                "schedules.disk_review_hour",
                "schedules.disk_review_minute",
                "schedules.review_day_of_week",
            ),
        ),
        # Daily reliability snapshot — an hour ahead of the 03:00 retention
        # purge, so the day's score is written before the checks behind it
        # can be deleted. Nothing serves these rows (the endpoint recomputes
        # live); they exist so the score becomes trendable.
        JobSpec(
            job_id="reliability_snapshot",
            enabled=agents.sysadmin.reliability.enabled,
            trigger="cron",
            trigger_kwargs={
                "hour": schedules.reliability_hour,
                "minute": schedules.reliability_minute,
            },
            config_paths=(
                "agents.sysadmin.reliability.enabled",
                "schedules.reliability_hour",
                "schedules.reliability_minute",
            ),
        ),
    )


#: Every config leaf that decides a job's existence or its timing.
#:
#: Derived from the plan rather than restated, so it cannot fall behind it.
#: :mod:`sysadmin.reload` reports these as restart-only **only when no
#: scheduler was handed to it** — with one, they are delivered.
JOB_CONFIG_PATHS: frozenset[str] = frozenset(
    path for spec in plan_jobs(AppConfig()) for path in spec.config_paths
)


@dataclass(frozen=True)
class JobSyncReport:
    """What :func:`apply_jobs` did to the scheduler.

    ``unchanged`` is carried rather than inferred: at startup everything is
    ``added``, and after an ordinary reload everything is ``unchanged`` —
    the difference between "the reload re-timed nothing" and "the reload
    never looked" is the one this module exists to make visible.
    """

    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    retimed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    #: Job id -> the error, for a job the host refused. Rare, and the
    #: reason ``requires_restart`` still exists.
    failed: dict[str, str] = field(default_factory=dict)
    #: The config leaves behind every failed job — what an operator would
    #: have to restart to deliver.
    failed_config_paths: list[str] = field(default_factory=list)


def apply_jobs(
    host: JobHost,
    config: AppConfig,
    targets: JobTargets,
    *,
    specs: Sequence[JobSpec] | None = None,
) -> JobSyncReport:
    """Make ``host`` match the schedule ``config`` asks for.

    Idempotent by rule 1: called twice with the same config, the second
    call reports everything ``unchanged`` and touches nothing. That is not
    a nicety — a reload that re-applied unchanged triggers would restart
    every job's clock, and a box reloaded more often than its slowest
    interval would never run its slowest agent.

    A job the host refuses is caught rather than raised: the configuration
    is already installed by the time this is called, so failing the reload
    is not available, and the honest outcome is to name what did not take
    effect. That is what ``requires_restart`` is for.
    """
    report = JobSyncReport()
    for spec in specs if specs is not None else plan_jobs(config):
        try:
            if not spec.enabled:
                if host.remove_job(spec.job_id):
                    report.removed.append(spec.job_id)
                continue
            func = targets[spec.job_id]
            if spec.trigger == "interval":
                outcome = host.sync_interval(
                    spec.job_id,
                    func,
                    first_run_delay_seconds=spec.first_run_delay_seconds,
                    **spec.trigger_kwargs,  # type: ignore[arg-type]
                )
            else:
                outcome = host.sync_cron(
                    spec.job_id,
                    func,
                    **spec.trigger_kwargs,  # type: ignore[arg-type]
                )
            getattr(report, outcome).append(spec.job_id)
        except Exception as exc:  # noqa: BLE001 — the message is the product
            logger.exception("job_sync_failed", extra={"job_id": spec.job_id})
            report.failed[spec.job_id] = f"{type(exc).__name__}: {exc}"
            report.failed_config_paths.extend(spec.config_paths)
    report.failed_config_paths[:] = sorted(set(report.failed_config_paths))
    return report
