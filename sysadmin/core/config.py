"""Configuration loader — YAML file validated through Pydantic models."""

import logging
from pathlib import Path

import yaml
from estate.gpu import DEFAULT_BUSY_THRESHOLD, DGPU_PCI_SLOT
from pydantic import BaseModel, Field, model_validator

from sysadmin.core.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT

logger = logging.getLogger(__name__)


# --- Nested config sections ---


class ApiConfig(BaseModel):
    """API authentication settings.

    ``auth_token`` unset/empty → auth disabled (backwards compatible);
    a warning is logged at startup.  When set, state-changing endpoints
    require ``Authorization: Bearer <token>``.
    """

    auth_token: str | None = None


class ServiceConfig(BaseModel):
    name: str = "sysadmin-service"
    port: int = DEFAULT_API_PORT
    host: str = DEFAULT_API_HOST
    log_level: str = "info"
    log_format: str = "json"  # json | text
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )


class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://gaddi@localhost:5432/projects"
    sync_url: str = "postgresql+psycopg2://gaddi@localhost:5432/projects"
    schema_: str = Field(default="sysadmin", alias="schema")

    model_config = {"populate_by_name": True}


class PersonalAssistantConfig(BaseModel):
    """Outbound integration with the PersonalAssistant app (retired 2026-07-24).

    PA is gone and Alfred, its replacement, exposes no inbox — no
    notification, briefing or digest endpoint.  Setting ``enabled: false``
    (as config.yaml now does) makes :class:`~sysadmin.monitor.notifier.Notifier`
    skip both the morning-briefing POST and the v2 notification sends
    without emitting a warning or an alert per attempt.

    The default stays ``True`` so a config predating this flag behaves
    exactly as before.  The code and its tests are kept deliberately: this
    is a dormant feature flag, not a deletion, so it can be repointed at
    Alfred if Alfred ever grows an inbox.
    """

    enabled: bool = True
    url: str = "http://localhost:8000"
    api_prefix: str = "/api"
    notify_endpoint: str = "/api/v2/notifications/send"
    briefing_endpoint: str = "/api/v2/intelligence/briefing/data"


class LLMConfig(BaseModel):
    """llama.cpp (llama-server) settings — OpenAI-compatible API.

    llama-server serves a single loaded model, so ``model`` is largely
    informational (recorded with summaries, passed through in requests).
    """

    url: str = "http://localhost:8081"
    model: str = "dria-agent-a-3b.Q4_K_M.gguf"
    timeout_seconds: float = 120.0
    # The GPU idle-gate (ADR-0004 as amended 2026-08-12): defaults come from
    # the estate so a third transcription of slot/threshold never happens.
    # An empty slot disables the gate; an unreadable counter fails open.
    gpu_pci_slot: str = DGPU_PCI_SLOT
    gpu_busy_threshold: int = DEFAULT_BUSY_THRESHOLD


# --- Agent sub-configs ---


class Thresholds(BaseModel):
    disk_warning_percent: int = 80
    disk_critical_percent: int = 90
    ram_warning_percent: int = 85
    cpu_sustained_percent: int = 90
    cpu_sustained_minutes: int = 10
    gpu_temp_warning_c: int = 90
    gpu_vram_warning_percent: int = 90


class AnomalyConfig(BaseModel):
    """Z-score anomaly detection over ``resource_snapshots`` history.

    Complements the fixed :class:`Thresholds` — flags values that are
    unusual *for this machine* even when they sit below a hard limit.

    - ``window_days``   — how much history the rolling mean/stdev uses
    - ``min_samples``   — cold-start guard; fewer snapshots → no flagging
    - ``min_stdev``     — near-constant series would produce huge/infinite
      z-scores, so a series flatter than this is skipped entirely
    """

    enabled: bool = True
    window_days: int = 7
    z_threshold: float = 3.0
    min_samples: int = 30
    min_stdev: float = 1.0
    severity: str = "warning"


class ReliabilityGradeBands(BaseModel):
    """Score thresholds mapping a reliability score (0-100) to a grade.

    Set higher than :class:`HealthGradeBands` on purpose.  A repository
    scoring 80 is tidy enough; a service that was unavailable for a fifth
    of the week is not "healthy" by any reading, so the reliable band
    starts at 95 — roughly "no more than one bad check-run this week".
    """

    reliable_min: int = 95
    degraded_min: int = 85
    unreliable_min: int = 60


class ReliabilityConfig(BaseModel):
    """Per-service reliability scoring (Session 25, Tier 1).

    ``window_days`` is capped in practice by ``service_health``'s
    retention (30 days by default): a longer window silently narrows to
    however much history survives the nightly purge, so widening this
    means widening retention too.
    """

    enabled: bool = True
    window_days: int = 7
    grade_bands: ReliabilityGradeBands = Field(default_factory=ReliabilityGradeBands)


class SysAdminAgentConfig(BaseModel):
    """Monitoring agent settings.

    The service list is deliberately absent. Per-service topology lives in
    services.yaml, keyed by project id — see
    :mod:`sysadmin.monitor.services`. It was in two places before this
    (here and projects.yaml), which is how seven project units ended up
    filed under "sysadmin" with comments explaining why.
    """

    enabled: bool = True
    health_check_interval_seconds: int = 300
    thresholds: Thresholds = Field(default_factory=Thresholds)
    anomaly: AnomalyConfig = Field(default_factory=AnomalyConfig)
    reliability: ReliabilityConfig = Field(default_factory=ReliabilityConfig)


class HealthGradeBands(BaseModel):
    """Score thresholds mapping ``health_score`` (0-100) to a grade.

    score >= healthy_min          → "healthy"
    score >= needs_attention_min  → "needs_attention"
    score >= neglected_min        → "neglected"
    otherwise                     → "abandoned"
    """

    healthy_min: int = 80
    needs_attention_min: int = 60
    neglected_min: int = 40


class BranchActionsConfig(BaseModel):
    """Stale-branch pruning (``POST /api/projects/{name}/branches/prune``).

    Deleting a branch can destroy unmerged work, so this mirrors the file
    actions' safety model: dry run unless the request says ``confirm``,
    and the genuinely dangerous case needs *two* flags.

    - ``enabled`` — master kill switch; false → the endpoint 409s
    - ``protected_branches`` — glob patterns never deleted, whatever their
      age or merge state (the detected default branch is protected too,
      even when it is not listed here)
    - ``allow_unmerged_delete`` — defence in depth.  A branch that is not
      an ancestor of the default branch is *reported only* unless the
      request sets ``include_unmerged: true`` **and** this flag is true
    - ``max_deletions`` — hard cap per call.  A request may ask for fewer,
      never for more
    - ``min_stale_days`` — floor on the staleness window a request may
      ask for, so ``stale_days: 0`` cannot sweep up today's work
    """

    enabled: bool = True
    protected_branches: list[str] = Field(
        default_factory=lambda: ["main", "master", "develop", "release/*"]
    )
    allow_unmerged_delete: bool = False
    max_deletions: int = 20
    min_stale_days: int = 7


class CodeCommitIgnoreConfig(BaseModel):
    """Commits that touched a repository without being work in it.

    A single ``git commit -am`` across forty repositories leaves every one
    of them looking active on the same day.  This estate has two such
    commits, from the 2026-08-04/05 ``~/projects`` reorganisation, and
    before they were excluded every dormant project read as touched four
    days ago — which is the opposite of what a staleness figure is for.

    ``message_patterns`` are matched against the commit subject
    (case-insensitive, unanchored) and any one matching excludes the
    commit.  ``shas`` pins specific commits when a pattern would be too
    broad.

    A *list* rather than the single regex first sketched, because this
    estate has two such sweeps and neither is a variation of the other:
    the reorganisation snapshot, and the fan-out that wrote a roadmap
    document set into eleven repositories.  With only the first, the
    second still shadows it — the newest commit in eleven projects would
    be a document set, and the walk would stop there having skipped
    nothing.

    Only the *date* is affected. Nothing is rewritten and no commit is
    hidden — ``last_commit`` still reports the true newest commit beside
    ``last_code_commit``, so the difference between them is visible rather
    than silently applied.
    """

    message_patterns: list[str] = Field(
        default_factory=lambda: [
            r"WIP snapshot before ~/projects reorganisation",
            r"^Add roadmap document set$",
        ]
    )
    shas: list[str] = Field(default_factory=list)
    #: How far back to walk before giving up and reporting no code commit.
    #: A repository whose entire history is ignored commits is a real case
    #: (the empty shells), and an unbounded walk on a 400-commit repo for
    #: every scan is not worth the certainty.
    max_walk: int = 200


class EstateConfig(BaseModel):
    """``estate.json`` — the scanner's output contract.

    Versioned and written atomically because it is read by things this
    repository does not own.  ``health`` inside it is derived on every run
    and never persisted, so the scoring rules can change without a
    migration and without a stale score outliving them.
    """

    enabled: bool = True
    #: Written beside the projects it describes.  Relative paths resolve
    #: against ``projects_root``.
    path: str = "estate.json"
    code_commit_ignore: CodeCommitIgnoreConfig = Field(
        default_factory=CodeCommitIgnoreConfig
    )


class IdleNudgeConfig(BaseModel):
    """Idle-nudge thresholds (Session 31).

    A nudge is a *broken commitment*, not a dirty directory: the project
    is active, a human wrote down a next action, and that action has not
    changed for ``days``.  The health score answers a different question
    and is deliberately not consulted — a repository can be tidy, score
    100 and still have stood still for a fortnight.

    **The ladder is quiet-then-loud, and the quiet half is quiet because
    of config.yaml, not because of this code.**  ``tray.notify_min_
    severity`` is ``warning`` on this host, so the ``info`` nudge at
    ``days`` reaches the alerts list and the tray badge and never speaks;
    the escalation at ``escalate_days`` is the first thing that toasts.
    Lowering that to ``info`` moves the first toast forward by a week,
    which is the knob to reach for if the nudge is arriving too late —
    not this threshold.  Note it is the ``tray:`` section, **not**
    ``notifications.desktop.min_severity``: the latter is parsed by
    :class:`DesktopNotificationsConfig` and read by nothing (SNAG-CFG-001).

    ``escalate_days`` must be at least ``days``: a ladder whose second
    rung is below its first would raise the warning on the same scan as
    the info, so the escalation could never be observed as an escalation.
    """

    enabled: bool = True
    #: Days a stated next action may stand before an ``info`` nudge.
    days: int = 7
    #: Days at which the open nudge is escalated to ``warning``.
    escalate_days: int = 14

    @model_validator(mode="after")
    def _ladder_ascends(self) -> "IdleNudgeConfig":
        if self.escalate_days < self.days:
            raise ValueError(
                f"idle_nudges.escalate_days ({self.escalate_days}) must be >= "
                f"days ({self.days}); a ladder that descends never escalates"
            )
        return self


class ProjectOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 6
    projects_root: str = "/home/gaddi/projects"
    # How deep discovery may look for project markers. 1 = the old
    # behaviour (immediate children of projects_root only); 2 lets a
    # *category* directory (one with no markers of its own, e.g. apps/)
    # hold projects.  Directories that ARE projects are never descended
    # into, whatever the depth — a repo's vendored sub-repos are its own
    # business.
    discovery_depth: int = 2
    stale_branch_days: int = 30
    track_todos: bool = True
    todo_patterns: list[str] = Field(
        default_factory=lambda: ["TODO", "FIXME", "HACK", "XXX"]
    )
    grade_bands: HealthGradeBands = Field(default_factory=HealthGradeBands)
    # Global health-score floor below which a project raises an alert.
    # A project may override this in projects.yaml (``alert_threshold``).
    alert_threshold: int = 40
    # Weekly LLM-narrated portfolio review (Session 23).  Generation
    # falls back to a deterministic digest when llama-server is down, so
    # disabling this stops the *schedule*, not just the inference.
    weekly_review: bool = True
    # Ceiling on the TODO/FIXME deduction (5 points per 10 markers).
    # Uncapped, a 300-TODO project pins at 0 forever and the score stops
    # reporting anything about the rest of its health.  ``None`` = no cap.
    max_todo_penalty: int | None = 30
    branch_actions: BranchActionsConfig = Field(default_factory=BranchActionsConfig)
    estate: EstateConfig = Field(default_factory=EstateConfig)
    # Idle nudges (Session 31). A project may override the threshold with
    # ``idle_nudge_days`` in its own ``.project.yaml``.
    idle_nudges: IdleNudgeConfig = Field(default_factory=IdleNudgeConfig)


class FileActionsConfig(BaseModel):
    """Mutating filesystem actions (``POST /api/files/organise``, ``/clean/*``).

    Every action defaults to a dry run; the caller must send ``confirm: true``
    to touch the filesystem.  These settings bound *what* an action may do:

    - ``enabled`` — master kill switch; false → every action endpoint 409s
    - ``category_folders`` — category → destination folder, relative to the
      agent's ``scan_root`` (absolute paths are also accepted).  Retarget a
      category here rather than in code.
    - ``allow_permanent_delete`` — defence in depth.  Deletion normally means
      "move to the XDG trash".  When the trash is unusable (e.g. the file is
      on another filesystem) the operation is *skipped* unless the request
      sets ``force_delete: true`` **and** this flag is true.
    - ``max_operations`` — hard cap on the size of a single action's manifest.
    """

    enabled: bool = True
    category_folders: dict[str, str] = Field(
        default_factory=lambda: {
            "images": "Pictures",
            "videos": "Videos",
            "documents": "Documents",
            "audio": "Music",
            "books": "Books",
            "archives": "Archives",
        }
    )
    downloads_dir: str = "Downloads"
    archive_dir: str = "Archives/Downloads"
    duplicate_strategy: str = "newest"  # newest | largest
    # PDF routing heuristic — see sysadmin/services/file_actions.py
    pdf_book_min_pages: int = 50
    pdf_book_min_mb: float = 5.0
    max_operations: int = 200
    allow_permanent_delete: bool = False
    # Freedesktop trash location. Empty → <scan_root>/.local/share/Trash,
    # the spec default for $XDG_DATA_HOME/Trash (no env vars are read).
    trash_dir: str | None = None
    # Code files sitting loose in the scan root are *flagged only*, never moved
    code_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".c", ".cpp",
            ".h", ".hpp", ".java", ".rb", ".sh", ".php", ".lua", ".sql",
        ]
    )


class FileOrganiserConfig(BaseModel):
    enabled: bool = True
    scan_interval_hours: int = 24
    scan_root: str = "/home/gaddi"
    output_dir: str = "/home/gaddi/Documents/DMDocs/Self/Briefings/Audits"
    stale_days: int = 180
    downloads_stale_days: int = 30
    large_file_mb: int = 100
    similarity_threshold: float = 0.75
    # Weekly LLM-narrated disk review (Session 24 Tier 3).  Generation
    # falls back to a deterministic digest when llama-server is down, so
    # disabling this stops the *schedule*, not just the inference.
    weekly_review: bool = True
    # Reclaimable-space milestones (MB) for the /api/files/trends forecast —
    # the endpoint projects the date each one will be reached
    reclaimable_milestones_mb: list[int] = Field(
        default_factory=lambda: [1024, 5120, 10240]
    )
    skip_dirs: list[str] = Field(
        default_factory=lambda: [
            ".git", ".cache", ".local", ".config", ".var",
            ".mozilla", ".steam", "node_modules", "__pycache__", ".venv",
        ]
    )
    actions: FileActionsConfig = Field(default_factory=FileActionsConfig)


class ServiceDiscoveryConfig(BaseModel):
    """Session 26 — cross-reference installed units against the estate.

    ``alert_threshold`` is a count of *actionable* findings (orphaned +
    unmonitored + host), and the alert it governs is a single rolled-up
    one, re-raised only when the count changes.  Per-unit alerts would
    repeat SNAG-AGENT-002.  Set to 0 to record findings and never alert
    — the Session 28 posture for a new detector whose first run lands
    twenty findings at once.
    """

    enabled: bool = True
    scan_interval_hours: int = 6
    user_unit_dir: str = "~/.config/systemd/user"
    # /etc/systemd/system only.  /usr/lib/systemd/system is the package
    # manager's territory and nothing there is ours to wire up; the
    # sweep additionally skips symlinks, which is how an *enabled* distro
    # unit appears in /etc.
    system_unit_dir: str = "/etc/systemd/system"
    alert_threshold: int = 5


class LogSource(BaseModel):
    name: str
    type: str  # journalctl | file
    unit: str | None = None
    user: bool = False  # journal of a *user* unit (journalctl --user)
    path: str | None = None
    severity_filter: str = "warning"


class LogAggregatorConfig(BaseModel):
    enabled: bool = True
    poll_interval_seconds: int = 60
    sources: list[LogSource] = Field(default_factory=list)
    retention_days: int = 30
    summarise_with_llm: bool = True

    #: How long a fault must go unobserved before its open alert is
    #: resolved.  This is the knob that makes a log alert a *state*: one
    #: row is raised per distinct fault signature and stays open while the
    #: fault keeps being logged, so the only honest recovery signal is
    #: silence.  Measured against the poll, not the fault — 15 minutes is
    #: 15 polls at the default ``poll_interval_seconds``, wide enough that
    #: an intermittent error is one incident rather than a flapping pair.
    #: Too short and a recurring fault is announced as recovered between
    #: occurrences, which is the flap the tray's cooldown exists to damp.
    alert_quiet_minutes: int = 15

    #: Maximum entries taken from one read of one source.  A ceiling is
    #: unavoidable (this box has sustained 8.5 kernel messages a second
    #: for days); what was missing is that hitting it is now reported as
    #: ``details['truncated_sources']`` rather than showing up as a
    #: findings count that never moves (``SNAG-AGENT-005``).
    max_entries_per_read: int = 500


# projects.yaml was retired in Session 35 Phase 4.  Project identity,
# declared status and per-project alert thresholds now live in a
# ``.project.yaml`` manifest inside each repository, read through
# :mod:`estate.registry`; services live in services.yaml.  The file
# itself is kept as docs/projects-registry-legacy.yaml, because its
# comments were the only record of several decisions and those move into
# ``decisions:`` blocks by hand, one project at a time.


class DndScheduleWindow(BaseModel):
    """A time window during which DND is automatically active."""

    start: str = "23:00"  # HH:MM (24h)
    end: str = "07:00"


class DndConfig(BaseModel):
    """Do Not Disturb configuration."""

    enabled: bool = False  # manual toggle default (runtime-overridable)
    schedule: list[DndScheduleWindow] = Field(default_factory=list)
    allow_critical: bool = True  # critical alerts break through DND


class DesktopNotificationsConfig(BaseModel):
    """The daemon's own desktop notifications (``sysadmin/monitor/desktop.py``).

    Read by nothing between Phase 3 and 2026-08-11 (SNAG-CFG-001): the
    tray took over speaking, brought its own ``tray.notify_min_severity``
    key, and this section stayed in config.yaml looking like the knob
    that decided whether an alert was heard.  It now drives a real
    notifier — one that deliberately stays quiet whenever the tray is
    doing the job, so the two never both toast the same alert.

    ``min_severity`` therefore governs *the tray's understudy*, not the
    tray.  Raising it here silences the daemon and leaves the tray as
    loud as it was.
    """

    enabled: bool = True
    min_severity: str = "warning"  # info | warning | critical
    #: How recently the alerts route must have been polled for the daemon
    #: to consider the tray present and stay silent.  Three times the
    #: tray's 60-second ``alert_poll_seconds``, so one dropped poll (or a
    #: laptop resuming) does not produce a burst of daemon notifications
    #: for alerts the tray is about to show anyway.
    tray_grace_seconds: int = 180


class PaNotificationsConfig(BaseModel):
    enabled: bool = True
    min_severity: str = "critical"


class TrayNotificationsConfig(BaseModel):
    """The slice of ``notifications.tray:`` the *backend* needs.

    The tray owns this section and parses config.yaml itself
    (``sysadmin_tray/config.py``); its calm tunables — flap cooldown,
    escalation polls, digest mode — are presentation and never reach the
    backend, so they are deliberately absent here and ignored on load.

    ``mute_services`` is the exception.  It is not merely a toast
    suppressor: it is the only place a service contributed by
    projects.yaml can be declared *expected down*, because those entries
    are generated by ``ManagedProject.to_monitored_services`` and have no
    ``mute`` flag of their own.  Reliability scoring waives deductions
    for an expected-down service, so it has to read this list or half the
    estate could never be waived.
    """

    mute_services: list[str] = Field(default_factory=list)


class NotificationsConfig(BaseModel):
    desktop: DesktopNotificationsConfig = Field(
        default_factory=DesktopNotificationsConfig
    )
    tray: TrayNotificationsConfig = Field(default_factory=TrayNotificationsConfig)
    pa_notify: PaNotificationsConfig = Field(
        default_factory=PaNotificationsConfig
    )
    dnd: DndConfig = Field(default_factory=DndConfig)


class SchedulesConfig(BaseModel):
    """Local times (server timezone) for the daily cron jobs in main.py."""

    briefing_hour: int = 6
    briefing_minute: int = 0
    retention_hour: int = 3
    retention_minute: int = 0
    # Weekly project review — before the Monday briefing so the briefing
    # can carry the fresh narrative.
    review_day_of_week: str = "mon"
    review_hour: int = 5
    review_minute: int = 30
    # Weekly disk review — after the project review rather than beside
    # it, so the 3B model does one generation at a time; still ahead of
    # the 06:00 briefing, which carries both narratives.
    disk_review_hour: int = 5
    disk_review_minute: int = 45
    # Daily reliability snapshot — 02:00, an hour ahead of the 03:00
    # retention purge so the day's score is written before anything is
    # deleted from under it. Nothing reads these rows to serve a request
    # (GET /api/services/reliability recomputes live); they exist so the
    # score becomes trendable.
    reliability_hour: int = 2
    reliability_minute: int = 0
    # APScheduler's IntervalTrigger puts the *first* fire at now + interval,
    # so an agent whose interval exceeds the service's uptime between
    # restarts never runs at all (this is why file_organiser, at 24h, had
    # zero recorded runs). Hours-scale agents therefore get an explicit
    # first run shortly after startup.
    agent_first_run_delay_seconds: int = 60


class SelfMonitorConfig(BaseModel):
    """Self-monitoring of the agents themselves (``/api/sysadmin/self``).

    An agent is considered *stalled* when the time since its last recorded
    run exceeds ``interval × stall_grace_multiplier`` (floored at
    ``min_stall_grace_seconds`` so short-interval agents are not flagged
    by a single restart). The interval comes from each agent's own config
    section — the same values ``main.py`` registers with the scheduler.

    **``escalate_after_hours`` is the Session 39 knob, and it does not
    change detection at all.** A stall is alerted at ``warning`` the
    moment it is detected, exactly as before; this decides how long that
    warning may stand *unresolved* before the fault is restated at
    ``critical`` — the only severity the tray renders as a notification
    that persists on screen rather than expiring unseen. Lowering it
    makes the persistent alarm arrive sooner; it cannot make detection
    faster, which is ``stall_grace_multiplier``'s job. See
    :mod:`sysadmin.monitor.stalls`.

    24 hours is chosen against the *slowest* agent rather than the
    fastest. ``file_organiser`` and ``service_discovery`` run on 24-hour
    intervals, so a stall of theirs that is merely late — a restart, a
    missed tick — recovers within one interval. A gap shorter than that
    escalates faults that were about to clear themselves, and an alarm
    that cries wolf is how the persistent rung stops being read.
    """

    enabled: bool = True
    stall_grace_multiplier: float = 3.0
    min_stall_grace_seconds: int = 300
    recent_runs: int = 10
    #: Hours a ``warning`` stall may stand open before it is re-raised as
    #: ``critical``. 0 means "critical from the first detection".
    escalate_after_hours: float = 24.0
    #: Consecutive failed runs before :mod:`sysadmin.monitor.failures`
    #: speaks. **A count of runs, deliberately not a duration** — the
    #: opposite unit from ``escalate_after_hours`` two lines up, because
    #: ``agent_runs`` records a run rather than a schedule and "failing
    #: for three hours" cannot tell an agent that is failing apart from
    #: one that is not running. The latter is the stall family's
    #: question, and a time-based threshold here would silently merge
    #: the two.
    #:
    #: 2 rather than 1 because the news is "reproducible", not
    #: "happened": a single failure clears on the next run, which for
    #: ``log_aggregator`` is 60 seconds later. The trade is that a count
    #: is fast for a frequent agent (2 minutes) and slow for a daily one
    #: (2 days); raising it slows the daily agents further.
    failure_alert_threshold: int = 2

    @model_validator(mode="after")
    def _escalation_gap_is_not_negative(self) -> "SelfMonitorConfig":
        if self.escalate_after_hours < 0:
            raise ValueError(
                f"self_monitor.escalate_after_hours ({self.escalate_after_hours}) "
                "must be >= 0; a negative gap would escalate before it warned"
            )
        return self

    @model_validator(mode="after")
    def _failure_threshold_is_at_least_one(self) -> "SelfMonitorConfig":
        """0 would alert on every *successful* run.

        ``_consecutive_failures`` returns 0 for a healthy agent, and the
        family's test is ``>= threshold`` — so a threshold of 0 makes
        every agent permanently "failing", which is five criticals and a
        muted monitor rather than an obviously-wrong config.
        """
        if self.failure_alert_threshold < 1:
            raise ValueError(
                "self_monitor.failure_alert_threshold "
                f"({self.failure_alert_threshold}) must be >= 1; 0 would "
                "match every agent, including the ones that are fine"
            )
        return self


class EventsConfig(BaseModel):
    """Server-Sent Events stream (``GET /api/sysadmin/events``).

    ``heartbeat_seconds`` sets how often an SSE comment is written to an
    idle stream so proxies and clients do not drop it. ``max_queued_events``
    bounds each connected client's buffer — a client that cannot keep up
    loses its oldest events rather than stalling the publisher.
    """

    heartbeat_seconds: float = 20.0
    max_queued_events: int = 100
    retry_ms: int = 5000


class AgentsConfig(BaseModel):
    sysadmin: SysAdminAgentConfig = Field(default_factory=SysAdminAgentConfig)
    project_organiser: ProjectOrganiserConfig = Field(default_factory=ProjectOrganiserConfig)
    file_organiser: FileOrganiserConfig = Field(default_factory=FileOrganiserConfig)
    log_aggregator: LogAggregatorConfig = Field(default_factory=LogAggregatorConfig)
    service_discovery: ServiceDiscoveryConfig = Field(
        default_factory=ServiceDiscoveryConfig
    )


# --- Root config ---


class AppConfig(BaseModel):
    service: ServiceConfig = Field(default_factory=ServiceConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    personal_assistant: PersonalAssistantConfig = Field(default_factory=PersonalAssistantConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    schedules: SchedulesConfig = Field(default_factory=SchedulesConfig)
    self_monitor: SelfMonitorConfig = Field(default_factory=SelfMonitorConfig)
    events: EventsConfig = Field(default_factory=EventsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)


# --- Singleton loader ---

_config: AppConfig | None = None


#: Repository root — this module sits at ``<root>/sysadmin/core/config.py``,
#: so config.yaml and projects.yaml are two levels up.  Kept as a named
#: constant because the depth changed when core/ was introduced and a bare
#: chain of ``.parent`` gives no clue what it is counting.
REPO_ROOT = Path(__file__).resolve().parents[2]


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load and validate config from YAML file."""
    global _config

    if config_path is None:
        config_path = REPO_ROOT / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    _config = AppConfig.model_validate(raw or {})

    return _config


def get_config() -> AppConfig:
    """Get the loaded config, loading from default path if needed."""
    global _config
    if _config is None:
        return load_config()
    return _config
