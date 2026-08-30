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

3. **The estate's findings are mostly not this repository's alerts —
   with two named exceptions.**  The audit publishes ``findings_total``,
   and alerting on that *number* would double-count: the collation
   findings are the family :mod:`sysadmin.monitor.collation` already
   raises here, arriving a second time through a different producer, and
   ``pointers``/``seams`` are conformance breaches inside *other*
   repositories, which the estate rules direct to those repositories'
   own ADR processes.  So the total is never judged; what is judged of
   ``/api/audit/invariants`` is whether the audit **ran and completed**
   — ``checks_errored``, ``publish_error``, ``error``, age.  A check that
   errored produced no finding at all, which is the difference between
   "nothing is wrong" and "nothing looked".

   The exceptions are ``ports`` (:func:`judge_audit_findings`) and, since
   2026-08-30, ``wiring`` (:func:`judge_audit_wiring`).  Each is a
   **narrowing of this rule rather than a reversal**: neither reason above
   reaches either subject.  A port is not any repository's conformance —
   no repository owns one — and ``~/.claude/settings.json`` is in no
   repository *at all*; this service raises nothing about either itself,
   so there is nothing to double-count.  What decided both is that the
   estate *may not alert*: it files findings and never acts, this box's
   monitor is the only party permitted to speak, and the alternative to
   judging them here is a finding that is detected, correct,
   machine-readable and never said out loud.  That is the shape Session 46
   removed for units, one layer up.

   **The test is ownership, and it is applied per check rather than per
   severity** — see :data:`JUDGED_AUDIT_CHECKS`, which had to become a
   mapping for the second exception to be expressible at all.  Ten of the
   audit's twelve checks are still excluded, and the two that are not were
   each admitted by an ADR: ``docs/adr/0006-wiring-joins-ports.md`` holds
   the second and the reasoning behind the first.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from sysadmin.core.escalation import SEVERITY_ORDER
from sysadmin.core.text import truncate_at_word

#: How much of a project's stated next action reaches a nudge's message.
#:
#: The message is a desktop notification body by the time anyone reads
#: it (``sysadmin_tray.notifications`` appends ``alert.message``
#: verbatim), and the live actions on this estate run to 469 characters
#: — measured, not guessed, by driving this module against a populated
#: payload for the first time.  A notification daemon truncates a body
#: that long at a point nobody chose, which is ``SNAG-BRIEF-002``'s
#: defect: *a cut that nothing marks is indistinguishable from a
#: sentence that happened to end there*.  So the cut is
#: :func:`~estate.text.truncate_at_word`'s, which always marks it, and
#: the full text stays in ``details['next_action']`` — the place the
#: producer's own ``Nudge.details`` docstring reserves for "everything
#: the message had to compress".
#:
#: 120 is the producer's number for the same destination
#: (``nudges._MESSAGE_ACTION_CHARS``), and reaching the same figure
#: independently is not a copy to be deduplicated: it is unreachable
#: from here (a private constant behind a property ``asdict`` drops —
#: ``SNAG-ESTATE-002``), and this repository's prefix spends ~60
#: characters the producer's does not, so the totals differ even where
#: the budget for the action agrees.
NEXT_ACTION_CHARS = 120

#: Severity for every judgement this module makes, with one exception.
#:
#: ``warning`` and not ``critical``: ``critical`` breaks through the DND
#: windows by configuration and is the only severity
#: ``sysadmin_tray.notifications`` renders non-transient, which
#: :mod:`sysadmin.monitor.stalls` reserves for a fault that has already
#: been announced once and persisted.  Nothing on these five surfaces is
#: an outage of this box — the estate being wrong about a scan costs the
#: morning's project sections, never an alert path (estate ADR-0008 §6).
#: Not ``info`` either: ``info`` is below ``tray.notify_min_severity``
#: here, so it would be raised into the silence this session exists to
#: end.  The exception is an idle nudge, whose severity the producer
#: computes and this repository takes verbatim — see :func:`judge_attention`.
DEFAULT_SEVERITY = "warning"

#: The two roll-up titles :func:`judge_attention` falls back to above
#: ``attention_max_rows``.  Fixed strings rather than f-strings, which is
#: rule 2 read the other way round: a roll-up exists *because* the
#: individual subjects stopped being the identity, so there is nothing
#: variable left to keep out of the title.  They are patterns in
#: :data:`SURFACE_TITLE_PATTERNS` as they stand, with no ``%``.
HEALTH_ROLLUP_TITLE = "Estate project health breaches"
NUDGE_ROLLUP_TITLE = "Estate project next actions idle"

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
    "projects_attention": (
        "Project % health breach",
        "Project % next action idle",
        HEALTH_ROLLUP_TITLE,
        NUDGE_ROLLUP_TITLE,
    ),
    "audit_invariants": ("Estate audit %",),
    # Two families, one surface — they arrive in one payload from one
    # HTTP call, so they are read and swept together and no third
    # pattern set is wanted. ``Estate hook %`` covers both wiring
    # titles; it cannot reach ``Estate port %`` or ``Estate audit %``,
    # which is what the partition test asserts rather than this comment.
    "audit_findings": ("Estate port %", "Estate hook %"),
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


def judge_projects_invariants(payload: dict[str, Any], max_age_hours: float) -> list[Judgement]:
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

    **``estate_written`` is judged only on a scan that did not error**,
    and that guard was put there by running this function over a payload
    the producer built rather than by reading the rule (Session 54).
    ``ScanOutcome.estate_written`` starts ``False`` and is set when
    ``estate.json`` is rewritten, near the end of a scan — so *every*
    failing scan carries ``error`` and ``estate_written: False``
    together, and this used to raise two rows for one fault.  The second
    is worse than redundant: its message says the scan "completed
    without rewriting estate.json", which is false of a scan that did
    not complete.  With ``reminder_hours`` live (Session 53) a wrong row
    is no longer one toast — it restates itself every 24 hours until
    somebody closes it.  The two families are now mutually exclusive by
    construction, the shape :mod:`sysadmin.monitor.failures` and
    :mod:`sysadmin.monitor.stalls` already hold between them: report the
    cause, never the cause and each of its consequences.

    **``finished_at is None`` cannot happen against today's producer**,
    and the branch is kept anyway.  ``ProjectOrganiser.run`` writes its
    ``ScanRun`` **once, after the scan**, with ``finished_at`` a literal
    ``datetime.now(UTC)`` — there is no insert-at-start/update-at-end
    split, so a scan killed mid-flight writes no row at all and surfaces
    through the *stale* rule instead.  Live: 0 of 7 rows unfinished.
    Kept because the column is nullable and the producer may yet split
    the write; recorded here so the next reader does not mistake a rule
    that has never fired for one that is watching something.
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
                    f"{len(sources)} data source{'' if len(sources) == 1 else 's'} "
                    f"{'was' if len(sources) == 1 else 'were'} unreachable during "
                    "the last scan, so it ran on degraded input. See "
                    "details.sources."
                ),
                details={"sources": list(sources), "count": len(sources)},
            )
        )

    if last.get("estate_written") is False and not last.get("error"):
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


def judge_attention(payload: dict[str, Any], max_rows: int) -> list[Judgement]:
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

    **Session 52 ran this against a populated payload for the first
    time**, which is the rest of that snag: ``/api/projects/attention``
    has answered ``{"health": [], "nudges": []}`` on every one of the
    four occasions anyone has looked, so every rule below had been
    exercised only against literals written by the same hand that wrote
    the consumer.  Two defects a literal cannot express came out of it,
    and both are rules this repository had already written down
    elsewhere and never applied here:

    1. **The row count is capped, and the cap is a shape guard rather
       than a tolerance** — :func:`judge_audit_findings` rule 2, one
       surface over.  The forced-population drive produced **26 health
       breaches and 5 nudges in a single run**: 31 rows, 31 tray
       fingerprints, one poll.  Every breach is still worth a row while
       there are few of them, because a roll-up cannot name anything
       (Session 46); above ``max_rows`` the count *is* the news, since
       twenty-six repositories do not go bad between two hourly polls —
       a threshold moved in the estate's ``config.yaml``, or
       ``effective_threshold`` misreading a manifest, does exactly that
       to all of them at once.  The two families collapse
       **independently**: they have separate producers inside the
       estate (a score against a threshold; a streak against a
       schedule), they fail separately, and collapsing one because the
       other is broken would hide the half that still works.

    2. **A roll-up takes the loudest rung it swallows.**  Collapsing
       rows must not also quieten them: an escalated ``warning`` nudge
       folded into a row raised at ``info`` would be **below**
       ``tray.notify_min_severity`` on this box, so the fix for noise
       would have silenced the one entry that had earned a toast.  The
       health roll-up has nothing to take and stays at
       :data:`DEFAULT_SEVERITY`, like the rows it replaces.

    3. **The message is cut at a word boundary and the cut is marked.**
       See :data:`NEXT_ACTION_CHARS`.

    ``max_rows`` is passed rather than read here because this module
    holds no configuration and no clock — the property that lets every
    rule be tested against a dict literal, which is the only way these
    rules could be tested at all before the drive.
    """
    out: list[Judgement] = []

    health = [
        entry
        for entry in payload.get("health") or []
        if isinstance(entry, dict) and entry.get("project")
    ]
    nudges = [
        entry
        for entry in payload.get("nudges") or []
        if isinstance(entry, dict) and entry.get("project_name")
    ]

    if len(health) > max_rows:
        out.append(_health_rollup(health, max_rows))
    else:
        out += [_health_row(entry) for entry in health]

    if len(nudges) > max_rows:
        out.append(_nudge_rollup(nudges, max_rows))
    else:
        out += [_nudge_row(entry) for entry in nudges]

    return out


def _health_row(entry: dict[str, Any]) -> Judgement:
    name = entry["project"]
    score, threshold = entry.get("score"), entry.get("threshold")
    return Judgement(
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


def _health_rollup(health: list[dict[str, Any]], max_rows: int) -> Judgement:
    """One row for all of them, naming the projects in ``details``."""
    projects = sorted(str(entry["project"]) for entry in health)
    return Judgement(
        surface="projects_attention",
        title=HEALTH_ROLLUP_TITLE,
        message=(
            f"{len(health)} projects score below their attention threshold. "
            "That many at once is the estate's scoring or its thresholds "
            "rather than that many repositories — check :8400"
            "/api/projects/attention against alert_threshold in the "
            ".project.yaml manifests. See details.projects."
        ),
        details={
            "projects": projects,
            "breach_count": len(health),
            "max_rows": max_rows,
            # Scalars per project, so the block stays diffable between
            # runs — `briefing/data.py` rule 3, and the reason the rows
            # this replaces are not simply nested here.
            "scores": {str(e["project"]): e.get("score") for e in health},
        },
    )


def _nudge_row(nudge: dict[str, Any]) -> Judgement:
    name = nudge["project_name"]
    days, threshold = nudge.get("days"), nudge.get("threshold")
    # `at_least` is the producer's hedge and is kept: a streak
    # reaching the edge of the retention window has an unknown true
    # length, and restating it as exact is the small dishonesty the
    # estate's own Nudge.message docstring refuses to commit.
    at_least = "at least " if nudge.get("at_window_edge") else ""
    plural = "day" if days == 1 else "days"
    action = truncate_at_word(str(nudge.get("next_action") or ""), NEXT_ACTION_CHARS)
    return Judgement(
        surface="projects_attention",
        title=f"Project {name} next action idle",
        message=(
            f"{name}'s next action has stood unchanged for "
            f"{at_least}{days} {plural} (nudges after "
            f"{threshold}): {action}"
        ),
        severity=_nudge_severity(nudge),
        details={
            "project": name,
            "days_unchanged": days,
            "threshold_days": threshold,
            # The full text, uncut: the message is what had to compress.
            "next_action": nudge.get("next_action"),
            "next_action_source": nudge.get("next_action_source"),
            "since": nudge.get("since"),
            "unchanged_scans": nudge.get("scans"),
            "at_window_edge": nudge.get("at_window_edge"),
            "severity_source": "estate",
        },
    )


def _nudge_rollup(nudges: list[dict[str, Any]], max_rows: int) -> Judgement:
    """One row for all of them, at the loudest rung it swallows."""
    projects = sorted(str(nudge["project_name"]) for nudge in nudges)
    severity = max(
        (_nudge_severity(nudge) for nudge in nudges),
        key=lambda level: SEVERITY_ORDER.get(level, 0),
        default=DEFAULT_SEVERITY,
    )
    return Judgement(
        surface="projects_attention",
        title=NUDGE_ROLLUP_TITLE,
        message=(
            f"{len(nudges)} projects have a stated next action that has stood "
            "past its nudge threshold. That many at once is the estate's "
            "streak query or its idle_nudges settings rather than that many "
            "abandoned commitments. See details.projects."
        ),
        severity=severity,
        details={
            "projects": projects,
            "nudge_count": len(nudges),
            "max_rows": max_rows,
            "days_unchanged": {
                str(n["project_name"]): n.get("days") for n in nudges
            },
            "severity_source": "estate",
        },
    )


def _nudge_severity(nudge: dict[str, Any]) -> str:
    """The producer's rung, or the default if it is not one of the three.

    ``alerts`` has a CHECK constraint on severity, so a producer typo
    reaching the insert is a ``CheckViolationError`` that takes the whole
    run's transaction with it — the failure ``BaseAgent._execute``'s
    per-service savepoints exist to contain, arriving here as data.
    """
    severity = nudge.get("severity")
    return severity if severity in SEVERITY_ORDER else DEFAULT_SEVERITY



# --- the audit -----------------------------------------------------------


def judge_audit_invariants(payload: dict[str, Any], max_age_hours: float) -> list[Judgement]:
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

    **``error`` is unreachable against today's producer**, unlike the
    scan's, and the asymmetry is worth stating because the two surfaces
    otherwise read as the same shape.  ``audit_runs.error`` is a column
    ``_record`` never populates: it builds ``AuditRun`` with no
    ``error=``, and the one path that sets ``AuditOutcome.error`` is
    ``_record`` itself raising, which writes no row at all.  Live: 0 of
    22.  So an audit that cannot record is invisible on this surface and
    arrives as staleness instead — kept for the same reason as the
    scan's unfinished branch, and named so a reader does not read its
    silence as health.
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
            name for name, check in checks.items() if isinstance(check, dict) and check.get("error")
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


#: The estate's port registry, judged by :func:`judge_audit_findings`.
PORTS_CHECK = "ports"

#: The estate's hook wiring, judged by :func:`judge_audit_wiring`.
#:
#: Admitted 2026-08-30 by :doc:`ADR-0006 </adr/0006-wiring-joins-ports>`,
#: answering estate-manager's message ``8462bcc5`` and their ADR-0068 §4.
WIRING_CHECK = "wiring"

#: The audit checks whose findings this repository speaks for, each
#: mapped to **the producer's own severity that it speaks for**.
#:
#: Checks are named explicitly rather than filtered on severity, and the
#: difference is not cosmetic: the estate's ``collation`` findings are
#: the family :mod:`sysadmin.monitor.collation` already raises here — the
#: exact double-count rule 3 forbids — and ``pointers``/``seams`` are
#: conformance breaches inside *other* repositories, which belong to
#: their own ADR processes.
#:
#: **This was two scalars until 2026-08-30 and the pair had gone wrong in
#: two directions at once.**  It was written against a four-check audit
#: in which *every* check emitted ``breach``, so a single
#: ``JUDGED_AUDIT_SEVERITY`` was unambiguously a deference to the
#: producer's rung.  The audit runs **twelve** checks now, at three rungs,
#: and that constant had quietly acquired a second job nobody argued for:
#: it was also a check filter.  So admitting a second check by name alone
#: would have shipped green and inert — ``wiring`` emits no ``breach`` at
#: any code (their ADR-0067 §4 refuses one, because a breach floors the
#: board's grade through an instrument built for a different rule) — and
#: widening the severity globally would have re-imported ``ports``'
#: ``claimed_but_silent``, which is availability and already has an owner
#: on this box.  A mapping is the only shape in which both stay true, and
#: it is why the answer to *"does ``wiring`` join ``ports``?"* could not
#: be a one-word yes.
#:
#: **What admits a check is not severity but ownership**, and the test is
#: the one this constant has always applied: the subject belongs to no
#: repository, it is estate-wide by construction, the estate may not
#: alert (it files findings and never acts), this service is the only
#: party on this box permitted to speak, and this service raises nothing
#: about the subject itself — so the alternative to judging it here is
#: that nobody says it at all.  A port satisfies every clause.  So does
#: ``~/.claude/settings.json``, which is in no repository *at all*
#: rather than merely unowned within one, and which the estate can own
#: the hook script for and cannot wire (their ADR-0024).
JUDGED_AUDIT_CHECKS: dict[str, str] = {PORTS_CHECK: "breach", WIRING_CHECK: "warn"}

#: The producer's own severity for the ``ports`` check, used as its filter.
#:
#: The same deference :func:`judge_attention` gives a nudge's rung: the
#: estate computed it against the contract it owns, and a second opinion
#: here would be two implementations of one policy.
#:
#: **Their ``ports`` check emits four codes across three rungs, and this
#: comment said two of them until 2026-08-27.**  Re-read off their
#: ``checks/ports.py`` rather than remembered: ``breach`` for
#: ``unclaimed_listener``, a *live listener with no registry row* — "the
#: registry being wrong, and it is how two projects end up guessing the
#: same number"; ``warn`` for ``claimed_but_silent``; and ``info`` for
#: both ``dormant_but_listening`` and ``claimed_tool_default``.  The
#: omission was not today's branch going stale — ``dormant_but_listening``
#: has been theirs since 2026-08-13, so the enumeration was incomplete the
#: day it was written, which is why it is now dated and sourced.
#:
#: Only ``breach`` is judged, and each exclusion has its own reason.
#: ``claimed_but_silent`` is **availability**, and availability on this
#: box already has an owner: ``services.yaml`` plus the sysadmin agent's
#: ``% unreachable`` family.  Judging it would make this agent a second
#: owner of that lifecycle, the defect this package's docstrings name
#: three times over.  That the one live ``warn`` today (port 3300,
#: venture-assistant's frontend) happens *not* to overlap is luck rather
#: than design — its registry row reads "unit to follow", so the overlap
#: arrives on the day that unit ships.
#:
#: The two ``info`` codes are **advisory by request, and the request was
#: this repository's**.  ``claimed_tool_default`` exists because
#: ``SNAG-ESTATE-004`` was delegated to them on 2026-08-14 asking for
#: exactly ``SEVERITY_INFO`` — "advisory, not ``warn``, because it has not
#: collided and the remedy is a port move, which is work rather than a
#: correction" — and they built it that way (their ADR-0055, commit
#: ``8f8821d``).  Raising an alert here for a rung this repository asked
#: for would be a second opinion on a policy it wrote itself, and ``info``
#: is below ``tray.notify_min_severity`` on this box in any case, so a
#: judged row would be a silent one.  Written down rather than left as a
#: silence: a consumer that declines to judge a published finding with
#: nothing recording the decision is ``SNAG-CFG-001``'s shape, which is
#: the reason this paragraph exists at all.
#:
#: **Derived from the mapping, never written beside it** — the rule
#: ``journal.max_priority_for`` applies to ``PRIORITY_MAP``.  The name
#: survives because this paragraph is the argument for *why* ``ports`` is
#: filtered at ``breach``, and an argument is worth reading at the point
#: of use; the value is stated once, in :data:`JUDGED_AUDIT_CHECKS`.
JUDGED_AUDIT_SEVERITY = JUDGED_AUDIT_CHECKS[PORTS_CHECK]

#: The rung a breach gets when the sweep attributes its port to a
#: transient session scope — an editor's dev server rather than a
#: service.
#:
#: **Derived, not picked.**  ``info`` is the only rung below
#: ``tray.notify_min_severity`` on this box, which is the whole
#: requirement: the row must stay in ``GET /api/sysadmin/alerts`` and
#: leave the notification path.  It is the same lever
#: :mod:`sysadmin.projects.nudges` documents for its 7-day rung and for
#: the same reason — audibility is the tray's decision and this module
#: only chooses which side of it to sit on.  A second knob here would be
#: a threshold nothing else on the box obeys.
TRANSIENT_HOLDER_SEVERITY = "info"


def judge_audit_findings(
    payload: dict[str, Any],
    max_rows: int,
    attribution: Any = None,
) -> list[Judgement]:
    """The audit's port findings — the one family this repository speaks for.

    Rule 3 said the estate's findings are not this repository's alerts,
    and it is **narrowed rather than reversed** here.  Its two reasons
    both still hold and both still exclude what they excluded: the
    collation findings are this service's own alerts arriving by a second
    producer, and ``pointers``/``seams`` are other repositories'
    conformance.  Neither reason reaches ``ports``, which is nobody's
    repository — and the estate may not alert about it, so the choice was
    never "who speaks" but "does anyone".

    It did not, and the cost is already measured on the other side of the
    same seam.  ``GET /api/units/status`` classified both PersonalAssistant
    units ``orphaned``, correctly and in plain English, eight days before
    anyone looked while they restart-looped 52,178 times.  A finding that
    is complete, correct, machine-readable and unread is the shape Session
    46 spent itself removing, and an audit that files into a surface
    nothing judges reproduces it one layer up.

    Five rules, three of them the opposite of the first draft.  The
    fifth sits after the ``attribution`` paragraph rather than before
    it, because it is the first rule in this module that *reads* the
    attribution instead of merely carrying it:

    1. **One row per port, with the port in the title.**  Session 46's
       rule: ``Unmonitored systemd units: 17 findings`` was open, accurate
       and unread for eight days because a roll-up cannot name anything,
       and a shared title means one fault masks the next behind the tray's
       ``{severity}:{title}`` fingerprint.

    2. **Until the count says the fault is the registry itself.**  Above
       ``max_rows`` this emits one roll-up naming the ports in
       ``details``, which looks like the mistake rule 1 just forbade and
       is its complement: six simultaneous unclaimed listeners is not six
       faults, it is the table having been moved, truncated or
       re-formatted, and six toasts would train the reader to dismiss the
       family before it had said anything true (``SNAG-UNITS-002``'s
       argument for not shipping fifteen rows).  The estate guards the
       *empty* parse on its side and errors rather than reporting zero
       findings; a partial parse is the gap that leaves.

    3. **The port comes from ``detail['port']``, never from ``subject``.**
       ``subject`` is producer-written prose (``"port 3300"`` today) and
       rule 2 keeps variable text out of titles.  A port number is not
       the free text that rule is about — two unclaimed ports are two
       faults and deserve two rows, unlike one dead seam spelled with two
       exception classes — but the *integer* is stable where the sentence
       around it is not.  A finding whose port will not parse is skipped
       rather than titled from the sentence, because the fallback is
       precisely the forkable title.

    4. **The title carries no ``code``.**  ``unclaimed_listener`` is the
       only ``breach`` the ports check emits today, and a title built from
       the code would fork the row the day a second one is added for the
       same port.  The producer's own ``summary`` is the message, so its
       wording can change without moving the identity.

       ``details['code']`` is read for that day and is **``None`` on
       every payload the estate can serve today** — measured, not
       assumed (Session 54).  ``Finding.code`` is a real field on the
       producer's dataclass, folded into ``fingerprint`` as its last
       ``:``-separated segment, and then dropped: ``AuditFinding`` has no
       ``code`` column and the findings route publishes none.  It is
       ``SNAG-ESTATE-002``'s shape one surface over — a value the
       producer computes and the wire discards — and it is filed as
       ``SNAG-ESTATE-006`` rather than worked around here, because the
       only workaround available is splitting ``fingerprint``, which is
       this repository parsing a format the estate owns.  Meanwhile
       ``details['fingerprint']`` carries it where a human can read it.
       ``tests/test_estate_surface_payloads.py`` asserts the absence, so
       the day the estate publishes ``code`` the suite says so and this
       line stops being true by itself.

       The two rules together also make a same-title collision possible
       in principle: two ``breach`` codes for one port are two findings
       and one title.  That is the *agent's* problem rather than this
       module's — a judgement list is allowed to hold two rows the
       lifecycle must merge — and ``EstateJudgeAgent._execute`` now
       counts a title as taken the moment it raises it.

    **``attribution`` is Session 26c's half, and it is the answer to
    the question this family could not previously ask.**  The estate's
    check runs ``ss`` deliberately without ``-p``, so a breach says
    *"port 3300 is listening and no row claims it"* and stops there —
    which is the sentence a reader has to go and resolve by hand
    before they can do anything.  The unit sweep already reads
    ``/proc/<pid>/cgroup`` for every listener, so the holder is a
    lookup rather than a second subprocess.  Two rules: it is added to
    ``details`` and **never to the title or the message**, because the
    identity of this row belongs to the producer and a holder that
    changes between sweeps must not fork it; and it carries
    ``observed_at``, since the sweep runs six-hourly and the judge
    hourly, so the attribution can legitimately be five hours older
    than the breach it annotates.  Absent attribution changes nothing —
    the family behaves exactly as it did before, at ``warning``.

    5. **A transient holder is quietened, never suppressed.**  The only
       two rows this family has ever produced are Alfred dev servers
       launched from an editor — ``uvicorn --reload`` on 8110 and
       ``nuxt dev`` on 3110, both in ``app-code-oss-26348.scope``,
       standing since 2026-08-16.  The estate's finding is *literally
       correct*: no registry row claims either port.  The remedy is the
       half that does not apply, because an editor's dev server is not
       a service the next project could collide with and it leaves when
       the window closes.

       So such a breach is raised at :data:`TRANSIENT_HOLDER_SEVERITY`
       rather than dropped.  **Dropping it was the obvious
       implementation and is wrong for this family's founding reason**:
       Session 26b-A exists because a ports breach was detected,
       correct, machine-readable and never said out loud, and a
       consumer that silently declines to judge a published finding
       rebuilds precisely that — with the extra property that nothing
       records the decision, which is ``SNAG-CFG-001``'s shape.
       Quietening keeps the row in ``GET /api/sysadmin/alerts`` and
       takes it out of the notification path; the roll-up takes the
       loudest rung it swallows (Session 52's rule), so one real breach
       among six dev servers still speaks.

       What this removes is a *recurrence*, not a single toast.  The
       tray clears ``notified_this_episode`` only when a
       ``{severity}:{title}`` pair is absent from a poll, so closing the
       editor resolved both rows and re-opening it raised two fresh
       ``warning`` rows with fresh fingerprints — two toasts per
       development session, indefinitely, and one restatement per row
       per day in between since ``reminder_hours`` landed in Session 53.

       **The quietening is only as good as the attribution's age, and it
       says so.**  The sweep runs six-hourly and this agent hourly, so a
       dev server started inside a sweep window is unattributed, reads
       as an ordinary breach and is raised at ``warning``.  Accepted
       rather than fixed: the alternative is running ``ss`` here, which
       ``EstateJudgeAgent._attribution`` refuses for the reason it
       states — two answers to one question at two moments, with neither
       surface saying which it used.  Filed as ``SNAG-ESTATE-009``.

       Note the shape of the defect this fixed, which was **not** that
       the signal was missing.  :attr:`Listener.transient` has named
       these listeners since Session 26c; ``PortReport.unit_ports``
       dropped them for its own consumer's correct reason and
       ``unattributed_ports`` never held them (a session scope *is*
       attributed), so the port fell out of the stored blob entirely and
       ``holder`` came back ``None`` — indistinguishable here from
       5432's genuine unattributability.  That is ``ports_checked``'s
       rule one layer down: zero-because-clean must not be served as
       zero-because-blind.

    ``standing_days`` and ``runs_observed`` are carried through because
    the estate computes them and this module owns no clock — the same
    reason every age here arrives in the payload.  ``age_truncated``
    marks a first-seen at the retention edge, so ``standing_days`` is a
    lower bound, the rule ``at_window_edge`` already applies on
    ``/api/projects/next``.
    """
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return []

    breaches: list[tuple[int, dict[str, Any]]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get("check") != PORTS_CHECK:
            continue
        if finding.get("severity") != JUDGED_AUDIT_SEVERITY:
            continue
        port = _port_of(finding)
        if port is None:
            continue
        breaches.append((port, finding))

    if not breaches:
        return []

    breaches.sort(key=lambda pair: pair[0])
    ports = [port for port, _ in breaches]
    # Looked up once and shared by both branches: the roll-up needs the
    # same holders the per-port rows would have carried, and computing
    # them twice is two statements about one observation.
    holders = {
        port: (attribution.of(port) if attribution is not None else None)
        for port in ports
    }
    # What the sweep *knew*, beside who it named. Read off the same
    # object in the same call as `holders`, so the two cannot disagree
    # about one observation — the reason `holders` is looked up once and
    # shared by both branches, applied to the second question.
    readings = {port: _reading_of(attribution, port) for port in ports}

    if len(breaches) > max_rows:
        return [
            Judgement(
                surface="audit_findings",
                title="Estate port registry breach",
                severity=_rollup_severity(holders.values()),
                message=(
                    f"{len(breaches)} ports are listening with no row in the "
                    "estate's port registry. That many at once is the registry "
                    "itself being wrong — moved, truncated or re-formatted — "
                    "rather than that many services. Check "
                    "estate-manager/docs/guides/monitorable-project.md against "
                    "the audit at :8400/api/audit/findings."
                ),
                details={
                    "ports": ports,
                    "breach_count": len(breaches),
                    "max_rows": max_rows,
                    # Keyed by the port *as a string*. JSONB keys are
                    # strings, so an int-keyed dict comes back from the
                    # database with string keys and a consumer comparing
                    # against ``details['ports']`` would silently miss
                    # every one. Written that way here rather than
                    # discovered on a read.
                    "holders": {
                        str(port): holder
                        for port, holder in holders.items()
                        if holder is not None
                    },
                    # Every port, unlike `holders` — a reading is never
                    # absent, so filtering it would be the collapse it
                    # exists to remove, one branch over.
                    "attribution": {str(port): r for port, r in readings.items()},
                },
            )
        ]

    return [
        Judgement(
            surface="audit_findings",
            title=f"Estate port {port} registry breach",
            message=_breach_message(port, finding),
            details={
                "port": port,
                "code": finding.get("code"),
                "fingerprint": finding.get("fingerprint"),
                "standing_days": finding.get("standing_days"),
                "runs_observed": finding.get("runs_observed"),
                "age_truncated": finding.get("age_truncated"),
                "first_seen_at": finding.get("first_seen_at"),
                "audit_summary": finding.get("summary"),
                "holder": holders[port],
                "attribution": readings[port],
            },
            severity=_breach_severity(holders[port]),
        )
        for port, finding in breaches
    ]


def _reading_of(attribution: Any, port: int) -> dict[str, Any]:
    """What the stored sweep knew about this port — always a record.

    **The sixth rule, and it moves no rung.**  ``holder`` is ``None``
    for four different reasons and this says which: the sweep held a
    unit, held a session scope, *saw the port and could not name it*, or
    never saw it at all.  Until 2026-08-29 the last two were one answer,
    so a breach raised on a sweep that predates its listener read
    exactly like one the sweep had looked straight at — which is
    ``SNAG-ESTATE-009``'s claim of indistinguishability, and the honest
    annotation the entry has said it ships since Session 57 without
    having it.  ``details['holder']['observed_at']`` cannot carry the
    evidence's age when ``holder`` is ``None``, which is precisely the
    case that needed it.

    **It is an annotation and deliberately not a rung.**  Quietening an
    unattributed breach because the sweep predates it was considered and
    refused on correctness rather than cost, which is what separates it
    from the entry's two standing refusals.
    :meth:`~sysadmin.estate.agent.EstateJudgeAgent._attribution` fails
    **open** in writing — "the enrichment is not allowed to become a
    dependency of the alert" — and making absence of evidence quieten
    inverts that: ``observe_listeners`` failing returns no listeners at
    all, so *every* port would read unswept and the whole family would
    drop below ``tray.notify_min_severity``.  A ports breach detected,
    correct, machine-readable and never said out loud is this family's
    founding defect (Session 26b-A), and that would rebuild it at full
    scale as the fix for a seven-hour window.  It would also be a guess
    :func:`~sysadmin.units.ports.attribution_from_blob` already refuses
    in a milder form, where a port held by two units is *dropped* rather
    than attributed to whichever sorted first.

    Duck-typed for the reason :func:`_breach_severity` is: this module
    holds no clock and no configuration, and an attribution is whatever
    the agent read.  An absent one is answered by an **empty**
    :class:`~sysadmin.units.ports.PortAttribution` rather than by a
    string written here, because "nobody supplied evidence" and "the
    stored sweep cannot answer" are the same fact and a second spelling
    of ``unknown`` in this module is ``SNAG-DB-003``'s shape — two
    statements of one vocabulary, free to drift in the direction nobody
    notices.  The import is function-local so this module's dependencies
    at import time are unchanged; the path is unreachable in production
    in any case, since ``_attribution`` returns an empty attribution
    rather than ``None`` when there is no stored sweep.
    """
    reader = getattr(attribution, "reading", None)
    if callable(reader):
        return reader(port)

    from sysadmin.units.ports import PortAttribution

    return PortAttribution().reading(port)


def _breach_severity(holder: Any) -> str:
    """``info`` for a breach held by a session scope, else ``warning``.

    Reads the holder dict rather than re-deriving transience from the
    unit name here.  A second ``endswith(".scope")`` test in this module
    would be a second definition of what "transient" means, and the two
    would drift in the direction nobody notices — the argument
    ``COLLISION_KINDS`` makes for living in :mod:`sysadmin.units.ports`
    rather than in its agent.
    """
    if isinstance(holder, dict) and holder.get("transient"):
        return TRANSIENT_HOLDER_SEVERITY
    return DEFAULT_SEVERITY


def _rollup_severity(holders: Iterable[Any]) -> str:
    """The loudest rung the roll-up swallows — Session 52's rule.

    Collapsing rows must not also quieten them: six dev servers and one
    genuine unclaimed listener is one row that still has to be heard,
    and taking the quietest (or the first) would make the fix for noise
    the reason the one entry that earned a toast never got one.
    """
    return max(
        (_breach_severity(holder) for holder in holders),
        key=lambda level: SEVERITY_ORDER.get(level, 0),
        default=DEFAULT_SEVERITY,
    )


def _port_of(finding: dict[str, Any]) -> int | None:
    """The port a finding is about, or ``None`` if it cannot be trusted.

    Accepts the int the estate's ``ports`` check writes and the digit
    string a JSON round trip through a looser producer could yield;
    refuses everything else, including a port recoverable only by
    splitting ``subject``.  See rule 3.
    """
    detail = finding.get("detail")
    if not isinstance(detail, dict):
        return None
    port = detail.get("port")
    if isinstance(port, bool):
        return None
    if isinstance(port, int):
        return port
    if isinstance(port, str) and port.isdigit():
        return int(port)
    return None


def _breach_message(port: int, finding: dict[str, Any]) -> str:
    """The producer's sentence, with how long it has stood appended.

    The summary is taken verbatim rather than rewritten: the estate owns
    the ``ports`` contract and its wording explains the fault better than
    a paraphrase that has to be kept in step with it.
    """
    return _with_standing(
        str(finding.get("summary") or f"port {port} is listening unclaimed"), finding
    )


def _with_standing(summary: str, finding: dict[str, Any]) -> str:
    """``summary``, plus how long the producer says it has stood.

    Shared by both audit families rather than copied into the second
    one.  The rule it encodes is not about ports: a first sighting is
    stamped ``standing_days: 0.0`` by the estate, and *"Standing 0
    days"* is true, reads as a rounding artefact, and says nothing the
    row's own ``created_at`` does not.  That was found by driving the
    real producer (Session 45) and applies to every finding it ages.
    """
    standing = finding.get("standing_days")
    if not isinstance(standing, (int, float)) or isinstance(standing, bool):
        return summary
    days = f"{standing:.1f}".rstrip("0").rstrip(".")
    if days in ("0", ""):
        return summary
    edge = " at least" if finding.get("age_truncated") else ""
    return f"{summary}. Standing{edge} {days} days."


# --- the audit's hook wiring ---------------------------------------------


#: Title for a finding about ``settings.json`` as a whole rather than
#: about one hook.
#:
#: A fixed string, which is rule 2 read the way :data:`ATTENTION_ROLLUP_TITLES`
#: reads it: the producer's ``subject`` here is a *configured path*
#: (``~/.claude/settings.json``), so putting it in the title would fork
#: the row on the day the estate re-spells its own config — a fault
#: about one file, wearing two identities.  The path is in ``details``,
#: where ``sources_unreachable`` puts the same kind of fact.
WIRING_FILE_TITLE = "Estate hook wiring unreadable"


def judge_audit_wiring(payload: dict[str, Any]) -> list[Judgement]:
    """The audit's hook-wiring findings — the second family, and the last.

    **Admitted 2026-08-30, and the admission is narrow**: see
    ``docs/adr/0006-wiring-joins-ports.md``, which answers
    estate-manager's message ``8462bcc5`` and their ADR-0068 §4.  Their
    argument is that every clause of :data:`JUDGED_AUDIT_CHECKS`' test
    transfers from a port to ``~/.claude/settings.json``, and it does —
    the file is in no repository at all, it carries the hook entries
    binding all thirteen, the estate may not alert, only the owner can
    repair it (their ADR-0024), and they measured on 2026-08-29 that
    **nobody says it at all**: no code in any repository under
    ``~/projects`` reads ``estate/audit/findings/{check}``, and the one
    consumer of ``GET /api/audit/findings`` was this module, scoped out
    by a single string.

    So this is Session 26b-A's founding defect, one check over: a
    finding that is detected, correct, machine-readable and never said
    out loud.  The estate's own hooks cannot report it — all four fail
    open by design, so a dead hook and a silent one are the same
    observation from inside a session — and on 2026-08-25 a paste took
    every hook on this box down, the blocking ``Stop`` one included,
    with nothing able to say so.

    Five rules, three of them the opposite of the obvious
    implementation:

    1. **The identity is ``subject`` plus ``detail['event']``, which is
       the reverse of the ports family's rule 3.**  There, ``subject``
       is producer prose (``"port 3300"``) and the machine-stable half
       lives in ``detail``.  Here ``subject`` **is** the machine-stable
       half — the estate's :class:`DeclaredHook` documents it as the
       filename precisely because it is "stable across moves of the
       repository in a way an absolute path is not" — and ``detail``
       carries the qualifier.  Rule 2 is satisfied either way; what
       changes is which field to trust, and it is read off the producer
       rather than assumed to match the sibling family.

    2. **The kind is discriminated by the shape of ``detail``, never by
       ``code``.**  ``code`` is computed by the producer, folded into
       ``fingerprint``, and then dropped — ``AuditFinding`` has no column
       for it (``SNAG-ESTATE-006``), verified again against the live
       payload on 2026-08-30.  A ``warn`` finding carrying
       ``detail['event']`` is about one hook; one without is about the
       file.  That is a fact this module can read, where ``code`` is a
       field it would have to invent a source for.

    3. **Only ``warn`` is judged, and the excluded rung is excluded for
       the producer's own stated reason.**  ``wiring`` emits exactly one
       ``info`` code, ``hook_wired_undeclared``, and the estate's check
       says in writing that *"an extra event is the owner's prerogative
       over their own config, and the estate records it rather than
       judging it"*.  A consumer that judged it would be a second
       opinion on a policy the producer already declined to hold — and
       ``info`` is below ``tray.notify_min_severity`` here, so the row
       would be silent in any case.  ``claimed_tool_default``'s
       treatment one check over.

    4. **There is no roll-up, and that is a measured difference rather
       than an omission.**  ``judge_audit_findings`` rule 2 collapses
       above ``max_rows`` because the port population is unbounded — any
       listener on the box — so many at once means the registry itself
       is wrong.  This population is bounded by the estate's own
       ``hooks/`` directory: **four scripts, each declaring exactly one
       event on 2026-08-30**, so the ceiling is four rows and each names
       a hook a human can act on.  The collapse case is also already the
       producer's: an unparseable ``settings.json`` short-circuits its
       check to a *single* finding rather than one per hook.  What is
       left uncollapsed is the 2026-08-25 shape — a well-formed block
       pasted at the top level, which parses and wires nothing, so every
       declared hook files — and four rows naming four hooks is not the
       fifteen ``SNAG-UNITS-002`` refused to ship.  A threshold here
       would be invented against a population that has never exceeded
       it.

    5. **``critical`` was considered and refused.**  An unparseable
       ``settings.json`` does take the blocking ``Stop`` hook down,
       which is the one fault on these surfaces that is genuinely about
       *this* box rather than about the estate being a day behind — so
       :data:`DEFAULT_SEVERITY`'s "nothing here is an outage of this
       box" is narrower than it reads, and this is the exception.  It
       still gets ``warning``: ``critical`` breaks the DND windows by
       configuration and is what the tray leaves on screen, reserved for
       a fault costing something *now*, and a dead hook costs the *next*
       session rather than the running one.  The estate refused ``breach``
       for this check on exactly that shape of argument — not borrowing
       an instrument built for a different rule — and taking ``critical``
       here would be that borrowing performed in this repository.

    **The stated limit, measured and not fixed here.**  The producer's
    ``fingerprint`` is ``<check>:<subject>:<code>`` and carries no event,
    so two events declared by one hook would share one fingerprint and
    therefore one ``standing_days``.  Empty population on 2026-08-30 —
    all four hooks declare exactly one event — and it is the estate's
    identity to change, not this module's to parse around
    (``SNAG-ESTATE-002``'s rule).  ``standing_days`` is carried as
    evidence, never as identity, so the row is correct either way.
    """
    findings = payload.get("findings")
    if not isinstance(findings, list):
        return []

    judged: list[Judgement] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if finding.get("check") != WIRING_CHECK:
            continue
        if finding.get("severity") != JUDGED_AUDIT_CHECKS[WIRING_CHECK]:
            continue

        subject = finding.get("subject")
        if not isinstance(subject, str) or not subject.strip():
            # Rule 1 makes ``subject`` half the identity, so a finding
            # without a usable one is skipped rather than titled from
            # the summary — ``_port_of``'s refusal, applied to the field
            # this family trusts instead.
            continue
        subject = subject.strip()

        event = _wiring_event(finding)
        if event is None:
            judged.append(
                Judgement(
                    surface="audit_findings",
                    title=WIRING_FILE_TITLE,
                    message=_with_standing(
                        str(
                            finding.get("summary")
                            or f"{subject} does not declare the estate's hooks"
                        ),
                        finding,
                    ),
                    details=_wiring_details(finding, subject, event=None),
                )
            )
            continue

        judged.append(
            Judgement(
                surface="audit_findings",
                title=f"Estate hook {subject} not wired for {event}",
                message=_with_standing(
                    str(
                        finding.get("summary")
                        or f"{subject} declares it belongs behind {event} and "
                        "nothing in ~/.claude/settings.json resolves to it"
                    ),
                    finding,
                ),
                details=_wiring_details(finding, subject, event=event),
            )
        )

    return judged


def _wiring_event(finding: dict[str, Any]) -> str | None:
    """The event a wiring finding is about, or ``None`` for a file-level one.

    Rule 2's discriminator.  A non-empty string is required rather than
    truthiness alone, because ``detail`` reaches here through JSONB and
    an ``event`` that arrived as a number or a list would otherwise be
    formatted into a title — the forkable-title fallback rule 1 of
    :func:`judge_audit_findings` refuses one field over.
    """
    detail = finding.get("detail")
    if not isinstance(detail, dict):
        return None
    event = detail.get("event")
    if not isinstance(event, str) or not event.strip():
        return None
    return event.strip()


def _wiring_details(
    finding: dict[str, Any], subject: str, event: str | None
) -> dict[str, Any]:
    """Everything the row carries as evidence rather than as identity.

    ``event`` is present on **every** row, ``None`` on a file-level one,
    rather than being omitted there.  A key that appears only sometimes
    makes "the estate did not say" and "this row is not about one hook"
    the same observation for a consumer — ``ports_checked``'s rule, at
    the size of a dict key, and the collapse ``_reading_of`` exists to
    remove one family over.

    **The key is ``subject`` and not ``hook``, which the live drive
    corrected.**  It was written as ``hook`` and reads correctly on
    three of the four specimens; on the fourth — an unparseable
    ``settings.json`` — the producer's subject is the *config file's
    path*, so the key would have promised a hook name and delivered a
    file.  One field meaning two things by row shape is
    ``UnitFinding.enabled``'s trap, and naming the producer's own field
    is what makes it impossible rather than merely unlikely.
    """
    return {
        "subject": subject,
        "event": event,
        "code": finding.get("code"),
        "fingerprint": finding.get("fingerprint"),
        "standing_days": finding.get("standing_days"),
        "runs_observed": finding.get("runs_observed"),
        "age_truncated": finding.get("age_truncated"),
        "first_seen_at": finding.get("first_seen_at"),
        "audit_summary": finding.get("summary"),
        "audit_detail": finding.get("detail"),
    }


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
