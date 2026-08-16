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
   with one named exception.**  The audit publishes ``findings_total``,
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

   The exception is ``ports``, judged per finding by
   :func:`judge_audit_findings`, and it is a **narrowing of this rule
   rather than a reversal**: neither reason above reaches it.  A port is
   not any repository's conformance — no repository owns one — and this
   service raises nothing about ports itself, so there is nothing to
   double-count.  What decided it is that the estate *may not alert*: it
   files findings and never acts, this box's monitor is the only party
   permitted to speak, and the alternative to judging it here is a
   ``breach`` that is detected, correct, machine-readable and never said
   out loud.  That is the shape Session 46 removed for units, one layer
   up.
"""

from __future__ import annotations

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
    "audit_findings": ("Estate port %",),
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


#: The one audit check whose findings this repository speaks for.
#:
#: Named explicitly rather than filtered on severity, and the difference
#: is not cosmetic: **all four** of the estate's checks emit ``breach``,
#: so a severity-only rule would re-import the collation family
#: :mod:`sysadmin.monitor.collation` already raises here — the exact
#: double-count rule 3 forbids — and pull in ``pointers`` and ``seams``,
#: which are conformance breaches inside *other* repositories and belong
#: to their own ADR processes.
#:
#: Ports are the exception because no repository owns a port.  A port is
#: estate-wide by construction, the estate may not alert (it files
#: findings and never acts), and this service is the only party on this
#: box permitted to speak — so the alternative to judging it here is that
#: nobody says it at all.
JUDGED_AUDIT_CHECK = "ports"

#: The producer's own severity, used as the filter.
#:
#: The same deference :func:`judge_attention` gives a nudge's rung: the
#: estate computed it against the contract it owns, and a second opinion
#: here would be two implementations of one policy.  Its ``ports`` check
#: assigns ``breach`` to a *live listener with no registry row* — "the
#: registry being wrong, and it is how two projects end up guessing the
#: same number" — and ``warn`` to a claimed port that is silent.
#:
#: Only the first is judged, because the second is **availability**, and
#: availability on this box already has an owner: ``services.yaml`` plus
#: the sysadmin agent's ``% unreachable`` family.  Judging it would make
#: this agent a second owner of that lifecycle, the defect this package's
#: docstrings name three times over.  That the one live ``warn`` today
#: (port 3300, venture-assistant's frontend) happens *not* to overlap is
#: luck rather than design — its registry row reads "unit to follow", so
#: the overlap arrives on the day that unit ships.
JUDGED_AUDIT_SEVERITY = "breach"


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

    Four rules, three of them the opposite of the first draft:

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
    the family behaves exactly as it did before.

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
        if finding.get("check") != JUDGED_AUDIT_CHECK:
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

    if len(breaches) > max_rows:
        return [
            Judgement(
                surface="audit_findings",
                title="Estate port registry breach",
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
                    "holders": _holders_for(ports, attribution),
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
                "holder": attribution.of(port) if attribution is not None else None,
            },
        )
        for port, finding in breaches
    ]


def _holders_for(ports: list[int], attribution: Any) -> dict[str, Any]:
    """Holders for the roll-up row, keyed by port as a string.

    JSONB keys are strings, so an int-keyed dict comes back from the
    database with string keys and a consumer comparing against
    ``details['ports']`` would silently miss every one.  Written that
    way here rather than discovered on a read.
    """
    if attribution is None:
        return {}
    return {
        str(port): holder
        for port in ports
        if (holder := attribution.of(port)) is not None
    }


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
    summary = str(finding.get("summary") or f"port {port} is listening unclaimed")
    standing = finding.get("standing_days")
    if not isinstance(standing, (int, float)) or isinstance(standing, bool):
        return summary
    days = f"{standing:.1f}".rstrip("0").rstrip(".")
    if days in ("0", ""):
        # A first sighting. "Standing 0 days" is true, reads as a
        # rounding artefact, and adds nothing the row's own
        # ``created_at`` does not already say.
        return summary
    edge = " at least" if finding.get("age_truncated") else ""
    return f"{summary}. Standing{edge} {days} days."


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
