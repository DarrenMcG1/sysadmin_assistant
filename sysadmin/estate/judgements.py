"""What the estate's numbers mean — the rules, with no I/O around them.

A payload in, a list of :class:`Judgement` out.  No database, no HTTP,
no ``datetime.now()``: every age this module reasons about is carried in
the payload as ``age_seconds``, computed by the producer against its own
clock, which is also the only clock that can measure it correctly — the
scan's age is the distance from *its* ``started_at``, and re-deriving it
here from an ISO string would put two clocks and a timezone parse
between the fact and the judgement for no gain.

That makes every rule testable against a dict literal, which matters
more here than usual: ``GET /api/projects/attention`` has answered with
two empty lists every time anybody has looked, and the estate's own test
asserts exactly that (``test_nudges_are_published_not_stored``).  The
populated shape is unobserved on **both** sides of the seam, so the
rules that consume it have to be exercised against a literal or not at
all.

Three rules run through everything below.

1. **A cumulative total is not a rate, and alerting on one is
   immortal.**  The queue publishes ``dropped_total``, ``expired_total``
   and ``grants_total`` as ``count(*)`` over the whole ``gpu_leases``
   table.  ``dropped_total`` is 1 today; a ``> 0`` rule raises a row
   that no future state can clear, which is ``redis unreachable``'s
   6,283 rows and ``Critical disk usage on /``'s 13,971 arriving by a
   new route.  Only ``depth`` and ``oldest_waiting_seconds`` are gauges,
   and only gauges are judged.  The totals are reported in ``details``
   and in ``agent_runs``, where a human comparing two runs can see a
   change that this module cannot.

2. **Variable text never enters a title.**  The title is the identity
   key — dedup, the resolve and the tray's ``{severity}:{title}``
   fingerprint all read it — so a title that varies with the fault's
   wording is a title that never deduplicates.  ``sources_unreachable``
   is free text ending in an exception class name (today: ``"services
   endpoint unreachable: HTTPStatusError"``), so the same dead seam
   would open a second row the day it fails with ``ConnectError``.  One
   row names the count; ``details['sources']`` names the sources, the
   rule :mod:`sysadmin.monitor.journal` already applies to
   ``truncated_sources``.

3. **The estate's findings are not this repository's alerts.**  The
   audit publishes ``findings_total`` — 10 today, of which 8 are the
   collation family :mod:`sysadmin.monitor.collation` already raises
   here.  Alerting on that number would double-count this service's own
   alerts through a second producer, and the remaining findings are
   conformance breaches in *other* repositories, which the estate rules
   direct to those repositories' own ADR processes.  What is judged is
   whether the audit **ran and completed** — ``checks_errored``,
   ``publish_error``, ``error``, age.  A check that errored produced no
   finding at all, which is the difference between "nothing is wrong"
   and "nothing looked".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

#: Severity for every judgement this module makes, with one exception.
#:
#: ``warning`` and not ``critical``: ``critical`` breaks through the DND
#: windows by configuration and is the only severity
#: ``sysadmin_tray.notifications`` renders non-transient, which
#: :mod:`sysadmin.monitor.stalls` reserves for a fault that has already
#: been announced once and persisted.  Nothing on these four surfaces is
#: an outage of this box — the estate being wrong about a scan costs the
#: morning's project sections, never an alert path (estate ADR-0008 §6).
#: Not ``info`` either: ``info`` is below ``tray.notify_min_severity``
#: here, so it would be raised into the silence this session exists to
#: end.  The exception is an idle nudge, whose severity the producer
#: computes and this repository takes verbatim — see :func:`judge_attention`.
DEFAULT_SEVERITY = "warning"

#: Title patterns per surface, for the resolve sweep.
#:
#: The sweep is **scoped to the surfaces a run actually read** (see
#: :meth:`sysadmin.estate.agent.EstateJudgeAgent._execute`), so these
#: patterns must partition the agent's rows: a pattern that matched
#: another surface's titles would let a successful pull of one surface
#: close rows belonging to one that failed, announcing a recovery from a
#: payload nobody received.  ``tests/test_estate_judgements.py`` asserts
#: the partition against every title this module can produce.
SURFACE_TITLE_PATTERNS: dict[str, tuple[str, ...]] = {
    "projects_invariants": ("Estate scan %",),
    "projects_attention": ("Project % health breach", "Project % next action idle"),
    "audit_invariants": ("Estate audit %",),
    "queue_invariants": ("Estate queue %",),
}


@dataclass(frozen=True)
class Judgement:
    """One thing worth an alert row, already decided.

    Carries its own ``surface`` because the lifecycle is per-surface:
    the agent may only resolve within surfaces it read, and grouping
    after the fact would need a second mapping from title back to
    surface — the "splitting a title to recover a value" parser
    :mod:`sysadmin.monitor.collation` names and avoids.
    """

    surface: str
    title: str
    message: str
    severity: str = DEFAULT_SEVERITY
    details: dict[str, Any] = field(default_factory=dict)


def _hours(seconds: float | None) -> str:
    """An age in whole hours, for a message a human reads once."""
    if seconds is None:
        return "an unknown time"
    hours = seconds / 3600.0
    if hours < 1:
        return f"{int(seconds // 60)} minutes"
    return f"{hours:.1f} hours"


# --- the scan ------------------------------------------------------------


def judge_projects_invariants(
    payload: dict[str, Any], max_age_hours: float
) -> list[Judgement]:
    """The estate's scan, judged from the record it keeps of itself.

    ``scan_runs`` is written in its own transaction precisely so a failed
    scan's rollback cannot erase the evidence (estate ADR-0008 §3), which
    is what makes ``error`` and ``estate_written`` trustworthy here: a
    row saying the scan failed is stronger evidence than the absence of a
    row, the same argument ``_record_outcome`` learned in Session 41.

    ``undeclared`` is deliberately **not** judged.  It counts
    repositories with no ``.project.yaml`` — 9 of 26 today — which the
    estate scores exactly like ``active`` and reports separately by
    design.  It is a standing description of the estate, not a breach,
    and a rule on it would open a row that stays open until somebody
    declares nine repositories they have chosen not to declare.
    """
    out: list[Judgement] = []
    last = payload.get("last_scan")

    if not last:
        return [
            Judgement(
                surface="projects_invariants",
                title="Estate scan never ran",
                message=(
                    "The estate's project scanner has no run on record. "
                    "Every project surface — the board, /next, the "
                    "briefing's project sections — is served from its "
                    "snapshots. Check estate-manager-scan.timer."
                ),
                details={"scans_total": payload.get("scans_total", 0)},
            )
        ]

    age = last.get("age_seconds")
    if age is not None and age > max_age_hours * 3600:
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan stale",
                message=(
                    f"The last project scan started {_hours(age)} ago "
                    f"(threshold {max_age_hours:g}h, run type "
                    f"{last.get('run_type', 'unknown')}). Every project "
                    "surface is serving snapshots from that scan."
                ),
                details={
                    "age_seconds": age,
                    "max_age_hours": max_age_hours,
                    "run_type": last.get("run_type"),
                    "started_at": last.get("started_at"),
                    "scans_total": payload.get("scans_total"),
                },
            )
        )

    if last.get("error"):
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan failed",
                message=f"The last project scan recorded: {last['error']}",
                details={"error": last["error"], "started_at": last.get("started_at")},
            )
        )

    if last.get("finished_at") is None:
        # A run row with no finish is a scan that died mid-flight, which
        # is the state Session 41's three-transaction split makes
        # legible: the record survives the failure that produced it.
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan did not finish",
                message=(
                    f"The last project scan started {_hours(age)} ago and "
                    "recorded no finish. The process died mid-scan, or is "
                    "still running."
                ),
                details={"started_at": last.get("started_at"), "age_seconds": age},
            )
        )

    parse_failures = last.get("parse_failures") or 0
    if parse_failures:
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan parse failures",
                message=(
                    f"{parse_failures} repositories' roadmap documents did "
                    "not parse in the last scan. Those projects are scored "
                    "and published without the findings the documents carry."
                ),
                details={
                    "parse_failures": parse_failures,
                    "projects_scanned": last.get("projects_scanned"),
                },
            )
        )

    repos_skipped = last.get("repos_skipped") or 0
    if repos_skipped:
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan skipped repositories",
                message=(
                    f"{repos_skipped} repositories threw during analysis and "
                    "were skipped. A skipped repository writes no snapshot, "
                    "so it disappears from every project surface without "
                    "being reported as gone."
                ),
                details={
                    "repos_skipped": repos_skipped,
                    "projects_scanned": last.get("projects_scanned"),
                },
            )
        )

    sources = last.get("sources_unreachable") or []
    if sources:
        out.append(
            Judgement(
                surface="projects_invariants",
                # Not "… sources unreachable": that ends in a word
                # `RESOLVABLE_TITLE_PATTERNS` matches (`% unreachable`,
                # from SERVICE_ALERT_KINDS). Harmless today — that sweep
                # scopes on `Alert.agent == 'sysadmin'` and cannot reach
                # these rows — but `collation.py` rule 4 settled that a
                # title should be clear of those patterns *by
                # construction rather than by luck*, because the next
                # reader of the table, or the next person to move a
                # family under a shared sweep, has no reason to check.
                # `tests/test_estate_judgements.py` pins it.
                title="Estate scan could not reach sources",
                message=(
                    f"{len(sources)} data sources were unreachable during the "
                    "last scan, so it ran on degraded input. See "
                    "details.sources."
                ),
                details={"sources": list(sources), "count": len(sources)},
            )
        )

    if last.get("estate_written") is False:
        out.append(
            Judgement(
                surface="projects_invariants",
                title="Estate scan did not write estate.json",
                message=(
                    "The last project scan completed without rewriting "
                    "estate.json, the scanner's output contract. Anything "
                    "reading that file is on the previous scan's data."
                ),
                details={"started_at": last.get("started_at")},
            )
        )

    return out


# --- attention -----------------------------------------------------------


def judge_attention(payload: dict[str, Any]) -> list[Judgement]:
    """Health breaches and idle nudges, turned into rows.

    This is the half where **this repository is a delivery path and not
    a second opinion**.  The estate computes both, holds no way to
    announce either (its ADR-0001), and publishes them as data; the
    arithmetic behind a nudge — the streak, the per-project threshold,
    the escalation gap — was ported into
    ``estate_service/projects/nudges.py`` when the domain moved and
    stayed there.  Re-deriving severity here would be two
    implementations of one ladder in two repositories, which is the
    copy-drift the estate manager exists to remove.  So ``severity`` is
    taken verbatim, validated only for being one of the three the alerts
    table admits.

    The **health** half has no severity to take.  The estate publishes
    ``{project, score, threshold, status}`` and nothing else: the
    raise/escalate machinery was deleted rather than ported, so severity
    for a breach is genuinely this repository's to decide, and it is one
    rung — ``warning``, never ``critical``.  A repository scoring below
    its threshold is a standing condition that can persist for weeks; the
    severity that stays on screen and breaks DND is reserved for faults
    that have already been announced and ignored.

    Two things the payload does not carry, discovered by reading the
    producer rather than by trusting its dataclass: ``Nudge.title`` and
    ``Nudge.message`` are ``@property``, and ``oversight.attention``
    serialises with ``dataclasses.asdict``, which emits **fields only**.
    So the estate's "one place a nudge's title is built" never reaches
    the wire, and the title below is this repository's own.  That is
    defensible — the title is the identity key in *this* table — but it
    is a duplication to know about rather than to discover later, and it
    is filed as a snag.
    """
    out: list[Judgement] = []

    for entry in payload.get("health") or []:
        name = entry.get("project")
        if not name:
            continue
        score, threshold = entry.get("score"), entry.get("threshold")
        out.append(
            Judgement(
                surface="projects_attention",
                title=f"Project {name} health breach",
                message=(
                    f"{name} scores {score} against a threshold of "
                    f"{threshold} (status {entry.get('status', 'unknown')}). "
                    "See the estate's project detail for the deductions."
                ),
                details={
                    "project": name,
                    "score": score,
                    "threshold": threshold,
                    "status": entry.get("status"),
                },
            )
        )

    for nudge in payload.get("nudges") or []:
        name = nudge.get("project_name")
        if not name:
            continue
        days, threshold = nudge.get("days"), nudge.get("threshold")
        # `at_least` is the producer's hedge and is kept: a streak
        # reaching the edge of the retention window has an unknown true
        # length, and restating it as exact is the small dishonesty the
        # estate's own Nudge.message docstring refuses to commit.
        at_least = "at least " if nudge.get("at_window_edge") else ""
        plural = "day" if days == 1 else "days"
        severity = nudge.get("severity")
        out.append(
            Judgement(
                surface="projects_attention",
                title=f"Project {name} next action idle",
                message=(
                    f"{name}'s next action has stood unchanged for "
                    f"{at_least}{days} {plural} (nudges after "
                    f"{threshold}): {nudge.get('next_action', '')}"
                ),
                severity=(
                    severity
                    if severity in {"info", "warning", "critical"}
                    else DEFAULT_SEVERITY
                ),
                details={
                    "project": name,
                    "days_unchanged": days,
                    "threshold_days": threshold,
                    "next_action": nudge.get("next_action"),
                    "next_action_source": nudge.get("next_action_source"),
                    "since": nudge.get("since"),
                    "unchanged_scans": nudge.get("scans"),
                    "at_window_edge": nudge.get("at_window_edge"),
                    "severity_source": "estate",
                },
            )
        )

    return out


# --- the audit -----------------------------------------------------------


def judge_audit_invariants(
    payload: dict[str, Any], max_age_hours: float
) -> list[Judgement]:
    """The conformance audit's own numbers — never its findings.

    Rule 3 of the module docstring is the whole design of this function.
    ``findings_total`` is 10 today and 8 of them are stale collation
    versions, which :mod:`sysadmin.monitor.collation` already holds eight
    open rows for; a rule on the total would announce this service's own
    alerts a second time through a different producer.  It is reported in
    ``details`` on the age judgement so a reader has the number without
    an alert attached to it.

    ``checks_errored`` is the one that matters and reads as the quiet
    opposite of ``findings_total``: a check that errored produced no
    finding, so the audit's clean-looking result for that dimension means
    nothing looked rather than nothing was wrong — the same distinction
    ``_resolve_recovered`` draws between ``error`` and ``skipped``.
    """
    out: list[Judgement] = []
    last = payload.get("last_audit")

    if not last:
        return [
            Judgement(
                surface="audit_invariants",
                title="Estate audit never ran",
                message=(
                    "The estate's conformance audit has no run on record. "
                    "Check estate-manager-audit.timer."
                ),
                details={"audits_total": payload.get("audits_total", 0)},
            )
        ]

    age = last.get("age_seconds")
    if age is not None and age > max_age_hours * 3600:
        out.append(
            Judgement(
                surface="audit_invariants",
                title="Estate audit stale",
                message=(
                    f"The last conformance audit started {_hours(age)} ago "
                    f"(threshold {max_age_hours:g}h). Port-registry drift, "
                    "closed seams and pointer rot are unobserved until it "
                    "runs."
                ),
                details={
                    "age_seconds": age,
                    "max_age_hours": max_age_hours,
                    "run_type": last.get("run_type"),
                    "verdict": last.get("verdict"),
                    # Reported, never judged — see the module docstring.
                    "findings_total": last.get("findings_total"),
                },
            )
        )

    errored = last.get("checks_errored") or 0
    if errored:
        checks = last.get("checks") or {}
        failed = sorted(
            name
            for name, check in checks.items()
            if isinstance(check, dict) and check.get("error")
        )
        out.append(
            Judgement(
                surface="audit_invariants",
                title="Estate audit checks errored",
                message=(
                    f"{errored} of {last.get('checks_run', '?')} audit checks "
                    f"errored ({', '.join(failed) or 'unnamed'}). Those "
                    "dimensions produced no findings because nothing looked, "
                    "not because nothing is wrong."
                ),
                details={
                    "checks_errored": errored,
                    "checks_run": last.get("checks_run"),
                    "errored_checks": failed,
                },
            )
        )

    if last.get("publish_error"):
        out.append(
            Judgement(
                surface="audit_invariants",
                title="Estate audit publish failed",
                message=(
                    "The audit ran but could not publish its findings to "
                    f"estate/audit/…: {last['publish_error']}. The findings "
                    "are still served at :8400/api/audit/findings."
                ),
                details={"publish_error": last["publish_error"]},
            )
        )

    if last.get("error"):
        out.append(
            Judgement(
                surface="audit_invariants",
                title="Estate audit failed",
                message=f"The last conformance audit recorded: {last['error']}",
                details={"error": last["error"]},
            )
        )

    return out


# --- the queue -----------------------------------------------------------


def judge_queue_invariants(
    payload: dict[str, Any], max_depth: int, max_wait_seconds: float
) -> list[Judgement]:
    """GPU lease arbitration, judged on its two gauges only.

    Rule 1 of the module docstring: ``dropped_total``, ``expired_total``
    and ``grants_total`` are lifetime ``count(*)`` values over
    ``gpu_leases`` and are carried into ``details`` without a rule
    attached.

    ``active_lease.hold_deadline`` was considered and **rejected**, and
    the reason is worth keeping.  A deadline set by the producer is the
    one threshold here that would not have to be invented — but the
    arbiter's own ``tick()`` calls ``_expire_if_overdue`` before doing
    anything else, so an overdue lease visible to a poller means the tick
    loop is between ticks or dead, not that the lease is a problem.
    Judging it would need a grace period long enough to clear the race,
    which is an invented number after all, and the condition it detects
    surfaces anyway: a lease nothing expires blocks the queue, and
    waiters pile up behind it as ``depth`` and ``oldest_waiting_seconds``.
    One symptom with two derived thresholds beats three with an extra.

    Both thresholds **are** judgements rather than measurements, and say
    so in config: nothing on this box records what a normal queue depth
    is, because until Session 3 there was no queue.  They are defaults to
    be moved once the shape of a busy day is known.
    """
    out: list[Judgement] = []
    totals = {
        "dropped_total": payload.get("dropped_total"),
        "expired_total": payload.get("expired_total"),
        "grants_total": payload.get("grants_total"),
    }

    depth = payload.get("depth") or 0
    if depth > max_depth:
        out.append(
            Judgement(
                surface="queue_invariants",
                title="Estate queue backlog",
                message=(
                    f"{depth} requests are waiting for a GPU lease "
                    f"(threshold {max_depth}). The single 24 GB card is "
                    "shared, so a backlog means callers are blocked rather "
                    "than slow."
                ),
                details={"depth": depth, "max_depth": max_depth, **totals},
            )
        )

    waiting = payload.get("oldest_waiting_seconds")
    if waiting is not None and waiting > max_wait_seconds:
        out.append(
            Judgement(
                surface="queue_invariants",
                title="Estate queue starved",
                message=(
                    f"The oldest GPU lease request has waited {_hours(waiting)} "
                    f"(threshold {max_wait_seconds / 60:.0f} minutes). Either a "
                    "holder never released, or the arbiter's tick loop has "
                    "stopped granting."
                ),
                details={
                    "oldest_waiting_seconds": waiting,
                    "max_wait_seconds": max_wait_seconds,
                    "depth": depth,
                    "active_lease": payload.get("active_lease"),
                    **totals,
                },
            )
        )

    return out
