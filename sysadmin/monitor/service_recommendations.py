"""Turn reliability scores into ranked, executable service advice.

Session 25, Tier 2 — the fourth advice endpoint, beside
``sysadmin.files.recommendations`` (reclaimable megabytes),
``sysadmin.units.recommendations`` (no currency at all) and
``sysadmin.monitor.log_actions`` (occurrences).  Services were the one
scorer with no advice half, though :mod:`sysadmin.monitor.reliability`
has computed the episodes this module ranks since Session 25 Tier 1.

**Named ``service_recommendations`` and not ``service_actions``, and the
collision was real rather than hypothetical.**  ``log_actions`` is named
for its route, so ``service_actions`` was the first choice — but "service
action" already means something else here: ``POST
/api/sysadmin/services/{name}/{action}`` starts, stops and restarts a
unit, and ``tests/test_service_actions.py`` has covered *that* since the
tray's Phase 3.  Two of the three siblings are named
``recommendations`` anyway (``files/``, ``units/``), so the name that
avoids the collision is also the more common one.  The route keeps
``/actions`` for consistency with its three siblings; only the module
does not.

**Nothing here executes anything**, and a test asserts the endpoint is
GET-only for ``units/router.py``'s reason — the remedy for an unreliable
service is a fix in the service or an edit to a hand-curated file,
neither of which a scheduled agent should do on its own.

Pure module: no DB access, no FastAPI.  Give it scored services and
timer observations, get a ranked list back.

The currency: recoverable points
--------------------------------

``recoverable_points`` is the sum of the deductions this row accounts
for — directly measurable off :class:`~sysadmin.monitor.reliability.
Deduction`, which is why this endpoint has a real currency where
``UnitRecommendationInfo`` deliberately has none.

It is **forecast-framed and says so in every ``detail``**, because the
arithmetic differs from its siblings in a way that would otherwise
mislead.  Deleting a duplicate frees megabytes *now*; fixing a service
recovers nothing today.  The points are charged for failures already
inside the window, and they lapse only as those failures age out of it —
so ``recoverable_points`` means "what stops being deducted once the fix
holds for ``window_days``", not "what you get back by acting".  Naming
it ``points`` alone, or letting a reader assume the files module's
immediacy, is the ``FileRecommendationInfo`` argument arriving one
endpoint later: one field whose unit is decided by the producer is
unreadable at the call site, and so is one whose *tense* is.

Rows that map to no deduction carry ``0`` and rank beneath anything with
real points behind them, exactly as tidiness items rank beneath
reclaimable megabytes in the files module.  No number is invented to
make them comparable.

The confidence gate is asymmetric, and that is the whole design
--------------------------------------------------------------

Every one of this box's 30 services was ``confidence: low`` on the day
this was written — the box was powered off 2026-08-18 → 08-22 and
``SNAG-DB-005`` kept the daemon dead for a further 22 hours on 08-23, so
a 7-day window held ``observed_days: 1.07`` at ``coverage_percent:
15.13``.  A gate on ``confidence == "high"`` would therefore have
shipped a **measured-empty population**, which is ``SNAG-LOG-002``'s
shape for the third time in this repository.

The way out is the one Session 63 found for log trends: ask what each
row *argues from*, because a gap in ``service_health`` is
one-directional.  The monitor being down can **hide** an outage; it can
never **invent** one.

``EVENT_ARGUED``
    ``outage``, ``flapping``, ``timer_failed``.  These argue from
    observed failures — 305 recorded failing checks are 305 real failing
    checks whatever the coverage, and the true figure can only be worse.
    A low-confidence window is a floor under them, so they survive it.
    This is :mod:`sysadmin.monitor.log_trends` rule 4's ``NEW``
    asymmetry, one domain over.

``RATE_ARGUED``
    ``check_interval``, ``timer_stale``.  These argue from a *rate* or
    from an *absence* — "it blipped N times per day", "it has not fired
    since".  A gappy window makes the first meaningless and makes the
    second indistinguishable from "nobody was looking".  They require
    ``confidence: high`` and are silently absent otherwise, with
    ``suppressed_by_confidence`` counting them so "nothing to do" can be
    told apart from "we could not tell" — ``ports_checked``'s rule.

A muted service produces no rows at all.  Its deductions are computed
and waived by the scorer, so ``recoverable_points`` would be zero and
the advice would read as "fix the thing you declared expected-down".
``muted_skipped`` reports the count for the same reason
``LogActionsResponse.declared_noise`` does.

Timer staleness is measured by string inequality, never by parsing a
clock
------------------------------------------------------------------

A ``kind: timer`` check stores systemd's ``LastTriggerUSec`` in
``service_health.details['last_run']``, and ``systemctl show`` renders it
as a **local wall clock with a zone abbreviation** — ``"Tue 2026-08-25
08:00:00 BST"``.  Parsing that back is ``SNAG-LOG-009``'s defect wearing
a different hat: an abbreviation is ambiguous between zones and an
autumn fold names two instants.

Nothing here parses it.  ``last_run`` is treated as an **opaque token**
whose only meaningful operation is inequality, and the clock is
``service_health.checked_at`` — a real ``timestamp with time zone`` this
application wrote itself.  A change in the token between two consecutive
observations means the timer fired in between; the token's *content* is
never read.  So the module needs no timezone database, no format
assumption, and survives systemd rendering the property differently.

Two consequences worth stating rather than leaving to be discovered:

1. **A fire is dated to the observation that noticed it**, not to the
   instant it happened, so every cadence sample carries up to one poll
   interval of error.  On a daily timer polled every 300 s that is 0.35 %
   and is ignored; the docstring says so rather than the code pretending
   to a precision it has not got.
2. **A hole in the series under-reports staleness, never over-reports
   it.**  A timer that last fired before a gap has its change observed
   at the first check *after* the gap, so "time since last fire" comes
   out shorter than the truth.  The failure direction is silence, which
   is the safe one — and it is the same one-directional argument
   ``TRUNCATION_LOW_FRACTION`` rests on.

The cadence has its own lookback, and a 7-day window cannot hold one
----------------------------------------------------------------------

``timer_lookback_days`` is deliberately **not**
``reliability.window_days``.  A cadence is a property of the schedule
rather than of the scoring window, and the two genuinely disagree here:
``estate-manager-review-timer`` is weekly, so a 7-day window observes
**one** fire and therefore **zero** gaps — no cadence at all, and a
staleness rule built on the scoring window would be structurally blind
to every weekly timer on the box.  Measured over 30 days it shows 2
fires and is derivable.

A gap-spanning interval is never a cadence sample.  If the series has a
hole inside a fire-to-fire interval, that interval measures the outage
rather than the schedule, so it is dropped — ``reliability.py``'s rule 4
("a gap never becomes a trend") applied to the numerator instead of the
score.  With fewer than :data:`MIN_CADENCE_SAMPLES` clean samples there
is no cadence and no ``timer_stale`` row is produced, whatever the
elapsed time.

One fault occupies one row, and the fold names what it swallows
---------------------------------------------------------------

``SNAG-SYSD-006``.  ``recommend`` runs :func:`_service_rows` over every
scored service and :func:`_timer_rows` over the subset that are timers,
so a ``kind: timer`` service is in **both** loops.  Before
``SNAG-SYSD-005`` that could not collide — a failed job never reached
``service_health.status``, so ``timer_failed`` had a structurally empty
population — and the moment it could, ``GET /api/services/actions``
served ``alfred-career-mail-timer`` twice: ``outage`` at 6 recoverable
points beside ``timer_failed`` at 0, one fault named twice.

:func:`group_faults` is ``log_actions.group_incidents``' treatment, and
that module is **applied and never imported**.  The two rules have
nothing in common mechanically — there is no time window here and no
systemd graph — and an import would trip a live control belonging to a
different entry: ``snag_claims.check_check_interval_looks_away`` uses
this module's import set as its instrument for "the advice has the
service's own log data now", so importing ``log_actions`` for
convenience would report ``SNAG-SVC-001`` refuted by a change that has
nothing to say about it.

Seven rules, four of them the opposite of the obvious implementation:

1. **The grouping key is the service, and the relation is
   :data:`EVENT_ARGUED`.**  Grouping every row of a service is the
   obvious version and is wrong in a way only the controls could say:
   ``check_interval`` and ``timer_stale`` argue about *how the service
   is watched* rather than about the fault — :data:`KIND_ORDER`'s own
   docstring already draws that line — and fixing the service lapses
   neither.  Measured rather than reasoned: ``SNAG-SVC-001``'s check
   finds its row with ``next(r for r in recommendations if r.kind ==
   "check_interval")``, a **top-level** scan, and its synthetic subject
   produces exactly ``flapping`` + ``check_interval``.  Swallowing that
   row makes a still-live entry read as refuted, which is a landed fix
   for one entry deleting another's instrument.

2. **The fold runs after the confidence gate and before the sort, and
   only the second half of that is observable.**  Sorting after is
   load-bearing: the ranking must see the folded points rather than
   rank rows that are about to merge.  Gating first is defensive and
   currently **cannot be told from gating second** — driven both ways
   on a low-confidence service carrying all three shapes, the output
   is identical, because rule 1 makes the suppressible set
   (``RATE_ARGUED``) and the foldable set (``EVENT_ARGUED``) disjoint.
   It is written this way anyway, since the day rule 1 widens is the
   day a withheld row could reach a reader as somebody else's member
   while ``suppressed_by_confidence`` went on reporting it withheld —
   the count and the payload disagreeing about one row.  What the test
   pins is therefore the **disjointness**, which is the fact that
   makes the ordering vacuous, rather than an ordering no observation
   can distinguish: a constant observation is not evidence unless
   something in the population would have forced a different one.

3. **Points are summed; everything else is the anchor's.**  Summing is
   honest here in the way ``_incident_recommendation`` says it would
   *not* be across kinds, and for that rule's reason read from the other
   end: every member shares one currency and one subject, so the sum is
   this service's applied deductions — exactly ``100 - score`` — and
   fixing the service lapses all of them.  It is also what keeps
   :func:`total_recoverable_points` **invariant** under the fold; a
   figure that fell when two rows became one would report the same box
   as cheaper to fix on the day it got tidier to read.

4. **The anchor is :data:`KIND_ORDER`'s first surviving kind, and that
   constant is doing one job rather than two.**  It already answers
   "which claim is more urgent to read" for rows that tie on points;
   which claim leads a folded row is the same question, so stating it
   twice is what would be the second job.  The cause-first alternative
   was considered and refused: ``timer_failed`` genuinely *causes* the
   critical checks the ``outage`` row is computed from, which is
   ``group_incidents``' anchor rule read literally, but it would need a
   declared cause-to-consequence pairing this module has not got and
   would put the summed points on the row whose own evidence did not
   compute them.  That refusal stands and rule 7 does not reverse it:
   what moves there is the ``action``, and nothing else.

5. **The title stays the anchor's, where an incident row's does not.**
   ``_incident_recommendation`` rewrites its title because its members
   are *other units* and the anchor's title would understate the scope.
   Every member here is about the **same service**, so the subject of
   the anchor's sentence is already right and appending a count to it
   would be the count-that-names-nothing this repository spent
   ``SNAG-ESTATE-001`` removing.  What is named is named properly: each
   member's kind, title, detail, action and points, in
   :class:`~sysadmin.core.contracts.ServiceRecommendationMemberInfo` and
   in the folded ``detail``.

6. **Nothing is capped, and it cannot need to be.**  A service has at
   most three ``EVENT_ARGUED`` rows, so a fold names at most two
   members and the roll-up that cannot name what it swallowed is
   unreachable by construction rather than by a threshold — which is
   worth stating, because every other roll-up in this repository needed
   one.

7. **The step can be superseded where the claim cannot**
   (``SNAG-SVC-003``).  Rule 4 settles the anchor and says nothing
   about the ``action``, and the live specimen showed the anchor's
   naming a remedy that *cannot work*: restarting
   ``alfred-career-mail-timer`` re-arms a schedule that was never the
   problem, which the swallowed ``timer_failed`` row's own detail says
   in as many words — one row contradicting the row above it inside a
   fold built to make them one fault.  :data:`STEP_SUPERSEDES` is the
   narrow answer.

   **The discriminator is the member, not the subject, and that is
   measured rather than reasoned.**  On 2026-09-02 two timers carried
   an ``outage`` row: ``alfred-career-mail-timer``, folded, and
   ``pgbackrest-backup-timer``, whose last run had started succeeding
   the day before and which therefore produced no ``timer_failed`` row
   at all.  Both were handed the identical restart step and only the
   folded one's was wrong — for an armed timer whose *unit* went
   inactive the restart is the right step.  So the condition under
   which the anchor's step is refuted is exactly the condition under
   which the fold happens, which is what makes this rule local to
   :func:`_folded_row` rather than a repair to ``_outage_row``.

   Two consequences worth stating.  The set is a **statable property
   of a kind** rather than a causal claim: ``timer_failed``'s step
   operates on the triggered unit, one unit deeper than the row's own
   subject, and no service-level step can reach it.  And the anchor's
   superseded step is named in the ``detail``
   (:func:`_folded_row` rule 5), because the fold would otherwise drop
   a remedy in the one direction rule 4 does not look.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import TYPE_CHECKING

from sysadmin.core.contracts import (
    ServiceRecommendationInfo,
    ServiceRecommendationMemberInfo,
)
from sysadmin.monitor.reliability import ReliabilityScore

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sysadmin.core.config import ServiceActionsConfig

__all__ = [
    "ADVICE_SEVERITIES",
    "EVENT_ARGUED",
    "KIND_ORDER",
    "MIN_CADENCE_SAMPLES",
    "RATE_ARGUED",
    "SERIES_HOLE_FACTOR",
    "STEP_SUPERSEDES",
    "AdviceReport",
    "TimerPoint",
    "TimerSeries",
    "group_faults",
    "recommend",
]

#: Kinds whose evidence is an observed failure.  A gappy window can only
#: have hidden more of them, so it is a floor rather than a doubt and
#: these are produced at any confidence.  See the module docstring.
EVENT_ARGUED = ("outage", "flapping", "timer_failed")

#: Kinds whose evidence is a rate or an absence.  A gappy window makes
#: both unreadable, so these require ``confidence: high``.
RATE_ARGUED = ("check_interval", "timer_stale")

#: Ranking order within an equal ``recoverable_points``.  Faults the box
#: is suffering now come before advice about how it is watched.
KIND_ORDER = ("outage", "flapping", "timer_failed", "timer_stale", "check_interval")

#: Kinds whose **step** supersedes the anchor's inside a fold
#: (``SNAG-SVC-003``).  A kind belongs here when its step reaches a unit
#: the anchor's step cannot: ``timer_failed``'s names the *triggered*
#: service, which is a different unit from the one every other row in
#: this module is about, so a step operating on the service can never
#: reach it.
#:
#: Deliberately **not** :data:`KIND_ORDER` with one element moved.  That
#: constant answers which *claim* leads; this one answers which *step*
#: does, and the two have different answers only because a fold can
#: carry a finding whose subject is one unit deeper than the row's.
#: Anchoring itself was put to the owner on 2026-09-02 and stays with
#: ``KIND_ORDER`` — the title, the points, the rung, the grade and the
#: evidence are all still the anchor's.  See module docstring rule 7.
STEP_SUPERSEDES = ("timer_failed",)

#: Clean fire-to-fire intervals needed before a cadence is claimed.  Two,
#: because one interval is a coincidence and cannot be a median — the
#: same reason ``ReliabilityScore.mean_hours_between_incidents`` is
#: ``None`` below two episodes rather than being invented from the
#: window length.
MIN_CADENCE_SAMPLES = 2

#: A pair of consecutive observations further apart than this many check
#: intervals is a hole in the series rather than a poll.  2.5 admits one
#: missed poll and a little jitter, and refuses two.
SERIES_HOLE_FACTOR = 2.5

#: This family's severity vocabulary, quietest first.  Two values, and
#: it is stated once because two things read it: the list ordering below
#: and :func:`_loudest`, which decides a folded row's rung.  Written out
#: as ``r.severity != "risk"`` in both places it would be one fact with
#: two statements free to disagree — ``max_priority_for`` against
#: ``PRIORITY_MAP``, at the size of a two-element tuple.
ADVICE_SEVERITIES = ("advice", "risk")


@dataclass(frozen=True)
class TimerPoint:
    """One recorded check of a ``kind: timer`` service.

    ``last_run`` is systemd's ``LastTriggerUSec`` **verbatim** and is an
    opaque token here — see the module docstring.  ``None`` means the
    timer has never fired, which ``_timer_facts`` reports by omitting the
    key rather than by writing a sentinel.

    ``last_run`` is the **timer's** and ``last_result`` the **triggered
    unit's**, which is not a mixture but the whole point: the schedule and
    the job are two things, and reading both from the timer is what
    SNAG-SYSD-005 was.  ``triggered_unit`` names whose result it is, and
    is ``None`` on any observation stored before that fix.
    """

    checked_at: datetime
    last_run: str | None = None
    last_result: str | None = None
    triggered_unit: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class TimerSeries:
    """One timer service's observations, oldest first."""

    service: str
    unit: str
    points: list[TimerPoint]


@dataclass(frozen=True)
class AdviceReport:
    """What :func:`recommend` produced, and what it declined to.

    The three counts exist so a short list can be read correctly.  An
    empty ``recommendations`` means something different in each case —
    nothing is wrong, everything is muted, or the window is too gappy to
    tell — and a consumer that cannot distinguish them will read the
    third as the first.
    """

    recommendations: list[ServiceRecommendationInfo]
    muted_skipped: int = 0
    suppressed_by_confidence: int = 0
    services_considered: int = 0


def recommend(
    scores: list[ReliabilityScore],
    settings: ServiceActionsConfig,
    *,
    timers: list[TimerSeries] | None = None,
    check_interval_seconds: int = 300,
    now: datetime,
) -> AdviceReport:
    """Ranked service advice from already-scored services.

    ``scores`` is what :func:`sysadmin.monitor.reliability.score_services`
    returned; nothing is recomputed here, so the endpoint and the advice
    cannot disagree about how a score was arrived at.

    Ordering: ``risk`` first, then recoverable points descending, then
    :data:`KIND_ORDER`, then service name for stability — the files
    module's ordering with its own currency substituted.
    """
    timers = timers or []
    by_service = {t.service: t for t in timers}

    recs: list[ServiceRecommendationInfo] = []
    muted_skipped = 0
    suppressed = 0

    for score in scores:
        if score.muted:
            muted_skipped += 1
            continue

        confident = score.confidence == "high"

        for rec in _service_rows(score, settings, check_interval_seconds):
            if rec.kind in RATE_ARGUED and not confident:
                suppressed += 1
                continue
            recs.append(rec)

        series = by_service.get(score.service)
        if series is not None:
            for rec in _timer_rows(series, settings, check_interval_seconds, now):
                if rec.kind in RATE_ARGUED and not confident:
                    suppressed += 1
                    continue
                recs.append(rec)

    # Rule 2: after the gate, before the sort.
    folded = [
        group[0] if len(group) == 1 else _folded_row(group)
        for group in group_faults(recs)
    ]

    folded.sort(
        key=lambda r: (
            -_severity_rank(r.severity),
            -r.recoverable_points,
            _kind_rank(r.kind),
            r.service,
        )
    )
    return AdviceReport(
        recommendations=folded,
        muted_skipped=muted_skipped,
        suppressed_by_confidence=suppressed,
        services_considered=len(scores) - muted_skipped,
    )


def group_faults(
    rows: Sequence[ServiceRecommendationInfo],
) -> list[list[ServiceRecommendationInfo]]:
    """Collapse the rows that are one fault into one group.

    ``log_actions.group_incidents``' treatment, applied rather than
    imported — see the module docstring for why the import is refused.
    Every group is returned, including groups of one, so a caller can see
    that a row was considered and left alone; that module's shape, and
    for its reason.

    The relation is **the subject plus :data:`EVENT_ARGUED`**: two rows
    are one fault when they name the same service *and* both argue from
    that service's observed failures.  A ``RATE_ARGUED`` row is about how
    the service is watched, or about something not happening, so it is
    returned alone whatever else the service produced — rule 1, which is
    the rule the controls decided rather than taste.

    Within a group the anchor sorts first by :func:`_kind_rank`, ties
    broken on the title so a fold's leading claim cannot depend on dict
    ordering upstream — ``group_incidents`` rule 5, which exists for the
    same reason here even though the tie is currently unreachable (no
    service can produce two rows of one kind).

    Fails **open** in the one direction it can: an unrecognised kind is
    in neither tuple, so it is left alone rather than folded on a guess.
    ``collation.py``'s posture — not knowing means not collapsing, so the
    failure mode is the status quo rather than a false merge.
    """
    groups: list[list[ServiceRecommendationInfo]] = []
    faults: dict[str, list[ServiceRecommendationInfo]] = {}

    for row in rows:
        if row.kind not in EVENT_ARGUED:
            groups.append([row])
            continue
        faults.setdefault(row.service, []).append(row)

    for members in faults.values():
        groups.append(
            sorted(members, key=lambda r: (_kind_rank(r.kind), r.title))
        )

    return groups


def total_recoverable_points(recs: list[ServiceRecommendationInfo]) -> int:
    """Points that lapse if every recommendation holds for a full window.

    Summed across services, so it is an estate figure rather than a
    score: two services each recovering 30 points do not make one
    service's 60.
    """
    return sum(r.recoverable_points for r in recs)


def _folded_row(
    group: Sequence[ServiceRecommendationInfo],
) -> ServiceRecommendationInfo:
    """One row for the findings that are one fault (``SNAG-SYSD-006``).

    ``group`` arrives ordered by :func:`_kind_rank`, so ``group[0]`` is
    the anchor — the strongest claim, which for the founding specimen is
    ``alfred-career-mail-timer``'s ``outage`` row rather than the
    ``timer_failed`` row beside it.

    Five rules, four of them stated in the module docstring and one
    only reachable here:

    1. **Points are summed and everything else is the anchor's, with
       ``action`` the one exception** — docstring rules 3 and 7.  The
       per-service fields (``service``, ``grade``, ``confidence``,
       ``outage_episodes``) are identical across the group by
       construction, so taking the anchor's is a choice with no
       alternative rather than a preference.  ``title``, ``severity``,
       ``kind`` and ``evidence`` are the anchor's by decision.  Only the
       step can be superseded, and only by a member whose kind is in
       :data:`STEP_SUPERSEDES`.

    2. **``members`` carries the anchor too**, which is
       ``LogRecommendation.members``' shape and is what makes the summed
       figure decomposable: ``recoverable_points`` is exactly the sum of
       the members' shares, and a consumer wanting to know what the
       leading claim contributed can read it off the list.  Listing only
       the swallowed rows would leave the anchor's share the one number
       nothing states.

    3. **The rung is the loudest swallowed** — ``judge_attention``'s
       rule, the roll-up rule this repository has written down at four
       scales.  It is **vacuous today and implemented anyway**: the only
       ``risk``-capable kind is ``outage`` (severity follows the
       scorer's ``failing`` grade) and ``outage`` is :data:`KIND_ORDER`'s
       first, so the anchor is already at least as loud as anything it
       swallows.  That is a proof rather than an accident, and it is the
       kind of proof a future kind invalidates silently — so the rule is
       written, and a test pins the coincidence rather than the code
       relying on it.

    4. **The swallowed rows are named in the ``detail`` as well as in
       ``members``.**  A consumer rendering one field must not lose a
       finding: the tray and ``health_review`` read ``title``,
       ``detail`` and ``action``, none of which is ``members``.  Each
       swallowed row contributes its kind, its title, its own detail and
       its own step, because those steps are different in kind and
       cannot be merged the way an incident row merges six
       ``journalctl`` invocations into one.

    5. **A superseded anchor step is named in the ``detail`` too**, and
       for rule 4's reason read the other way round (``SNAG-SVC-003``).
       The moment the anchor's step stops leading it is a finding's
       remedy that no rendered field carries — ``members`` is not one of
       the three — so the fold would drop it exactly as it would have
       dropped a swallowed one.  The line also says *which* finding the
       leading step belongs to, because a step under another finding's
       title is otherwise a sentence about a subject the reader was not
       told had changed.
    """
    anchor = group[0]
    others = list(group[1:])
    points = sum(row.recoverable_points for row in group)

    # Rule 5.  ``others`` is already ordered by ``_kind_rank``, so this
    # takes the ``KIND_ORDER``-first superseding member and invents no
    # second ordering.  Scanning ``others`` rather than ``group`` is
    # what makes an anchor that is itself a superseding kind a no-op:
    # its step already leads.
    leader = next((row for row in others if row.kind in STEP_SUPERSEDES), None)

    lines = [
        anchor.detail,
        f"Also stands for {len(others)} other finding"
        f"{'s' if len(others) != 1 else ''} about {anchor.service}, named "
        f"below with its own step. The {points} recoverable points are the "
        f"sum across all {len(group)}; one fix lapses them together.",
    ]
    if leader is not None:
        lines.append(
            f"The step above is the {leader.kind} finding's, because it "
            f"reaches a unit the {anchor.kind} step cannot. The "
            f"{anchor.kind} finding's own step was: {anchor.action}"
        )
    for row in others:
        lines.append(f"  - {row.kind}: {row.title}")
        lines.append(f"    {row.detail}")
        lines.append(f"    Step: {row.action}")

    return ServiceRecommendationInfo(
        kind=anchor.kind,
        severity=_loudest(group),
        service=anchor.service,
        title=anchor.title,
        detail="\n".join(lines),
        action=anchor.action if leader is None else leader.action,
        recoverable_points=points,
        grade=anchor.grade,
        confidence=anchor.confidence,
        outage_episodes=anchor.outage_episodes,
        evidence=anchor.evidence,
        members=[
            ServiceRecommendationMemberInfo(
                kind=row.kind,
                severity=row.severity,
                title=row.title,
                detail=row.detail,
                action=row.action,
                recoverable_points=row.recoverable_points,
            )
            for row in group
        ],
    )


# --- service rows ---


def _service_rows(
    score: ReliabilityScore,
    settings: ServiceActionsConfig,
    check_interval_seconds: int,
) -> list[ServiceRecommendationInfo]:
    """The rows a single reliability score justifies."""
    out: list[ServiceRecommendationInfo] = []
    applied = {d.kind: d for d in score.deductions if not d.waived}

    downtime = applied.get("downtime")
    if downtime is not None:
        out.append(_outage_row(score, downtime.points))

    instability = applied.get("instability")
    if instability is not None and score.outage_episodes >= settings.flap_min_episodes:
        out.append(_flapping_row(score, instability.points))

    interval = _check_interval_row(score, settings, check_interval_seconds)
    if interval is not None:
        out.append(interval)

    return out


def _outage_row(score: ReliabilityScore, points: int) -> ServiceRecommendationInfo:
    """"It was not there when something asked for it."

    Severity is ``risk`` at the ``failing`` grade and ``advice``
    otherwise.  The grade is the scorer's own band rather than a second
    threshold invented here — a service can be judged unreliable in one
    place only.
    """
    return ServiceRecommendationInfo(
        kind="outage",
        severity="risk" if score.grade == "failing" else "advice",
        service=score.service,
        title=f"{score.service}: {score.uptime_percent:g}% uptime this window",
        detail=(
            f"{score.failed_checks} of {score.checks_measured} measured checks "
            f"failed across {score.outage_episodes} outage"
            f"{'s' if score.outage_episodes != 1 else ''}"
            f"{_longest(score)}. Grade {score.grade}, score {score.score}. "
            f"{_forecast(points, score.window_days)}"
        ),
        action=(
            f"Find out why {score.service} is unavailable — check its unit "
            f"and its own logs. Nothing here restarts it: "
            f"POST /api/sysadmin/services/{score.service}/restart is the "
            "deliberate manual step."
        ),
        recoverable_points=points,
        grade=score.grade,
        confidence=score.confidence,
        outage_episodes=score.outage_episodes,
        evidence="event",
    )


def _flapping_row(score: ReliabilityScore, points: int) -> ServiceRecommendationInfo:
    """"It keeps bouncing" — the separate failure instability measures."""
    mean = score.mean_hours_between_incidents
    cadence = (
        f" about every {mean:g} h" if mean is not None else ""
    )
    return ServiceRecommendationInfo(
        kind="flapping",
        severity="advice",
        service=score.service,
        title=(
            f"{score.service}: {score.outage_episodes} separate outages "
            "this window"
        ),
        detail=(
            f"Dropped out {score.outage_episodes} times{cadence}"
            f"{_longest(score)}. Retry logic survives one long outage and "
            "dies on several short ones, which is why this is charged "
            f"separately from downtime. {_forecast(points, score.window_days)}"
        ),
        action=(
            f"Look for a shared dependency behind the repeats — {score.service} "
            "returning at intervals usually means something it needs is "
            "cycling, not that it is failing on its own."
        ),
        recoverable_points=points,
        grade=score.grade,
        confidence=score.confidence,
        outage_episodes=score.outage_episodes,
        evidence="event",
    )


def _check_interval_row(
    score: ReliabilityScore,
    settings: ServiceActionsConfig,
    check_interval_seconds: int,
) -> ServiceRecommendationInfo | None:
    """The one row that suspects the *check* rather than the service.

    ``tasks.md`` scoped this as "llama-server flapped 6x this week —
    likely GPU contention, consider raising its check interval", and it
    is built as specified.  The narrowing is what makes it defensible:
    it fires only when **every** episode was a single failed check, which
    is what ``longest_outage_minutes == 0`` means (``_outage_episodes``
    dates an episode's end to its last *failing* check, so one sample has
    zero duration).  Many episodes that each lasted one poll is the
    shape a too-sensitive check makes; an episode spanning two polls is
    an outage and this stays quiet about it.

    It is ``RATE_ARGUED``: "N blips per window" is a rate, and a window
    at 15 % coverage cannot support one.

    **Filed as ``SNAG-SVC-001`` rather than resolved here.**  Advising a
    longer interval is advising that a fault be seen less often, which is
    the opposite of ``known_noise`` rule 3 — volume is what makes a fault
    worth looking at, not evidence it is harmless.  The wording therefore
    puts the sensitivity question first and never tells the reader to
    raise the interval outright, but the tension is real and belongs on
    the snag list, not inside a docstring that argues it away.
    """
    if score.outage_episodes < settings.flap_min_episodes:
        return None
    if score.longest_outage_minutes > 0:
        return None

    return ServiceRecommendationInfo(
        kind="check_interval",
        severity="advice",
        service=score.service,
        title=(
            f"{score.service}: {score.outage_episodes} one-check blips — "
            "check sensitivity or a real flap?"
        ),
        detail=(
            f"Every one of {score.service}'s {score.outage_episodes} outages "
            f"this window lasted a single check, so none was observed for "
            f"longer than the {check_interval_seconds}s poll. That is either "
            "a service genuinely returning within one interval or a check "
            "too tight for it — a timeout, or a health path that is slow "
            "while the service is fine. Confirm which before changing "
            "anything: a longer interval hides a real fault just as well as "
            "it hides a false one."
        ),
        action=(
            f"Read {score.service}'s own logs at the blip times. If the "
            "service was up throughout, the check is what needs widening "
            "in services.yaml; if it was not, leave the check alone."
        ),
        recoverable_points=0,
        grade=score.grade,
        confidence=score.confidence,
        outage_episodes=score.outage_episodes,
        evidence="rate",
    )


# --- timer rows ---


def _timer_rows(
    series: TimerSeries,
    settings: ServiceActionsConfig,
    check_interval_seconds: int,
    now: datetime,
) -> list[ServiceRecommendationInfo]:
    """The rows one timer's observations justify."""
    out: list[ServiceRecommendationInfo] = []
    points = sorted(series.points, key=lambda p: p.checked_at)
    if not points:
        return out

    latest = points[-1]

    if latest.last_result not in (None, "", "success"):
        out.append(_timer_failed_row(series, latest))

    stale = _timer_stale_row(series, points, settings, check_interval_seconds, now)
    if stale is not None:
        out.append(stale)

    return out


def _timer_failed_row(
    series: TimerSeries, latest: TimerPoint
) -> ServiceRecommendationInfo:
    """systemd says the last run of the timer's service did not succeed.

    ``EVENT_ARGUED``: ``Result`` is a recorded outcome, not a rate.  A
    gappy window cannot manufacture a failed result, and the property is
    read from the *latest* observation, so it describes now.

    **This row had a structurally empty population until SNAG-SYSD-005.**
    Its own ``detail`` states the mechanism exactly and the field it gated
    on could not express it: ``last_result`` was the **timer's**
    ``Result``, which reports whether the timer unit started.  The
    docstring was right, the wiring was not, and the drive exercising this
    row built a synthetic subject — which is why the emptiness went eight
    weeks unnoticed while a real one failed every morning.
    """
    # The fallback is unreachable by construction and kept because a row
    # that cannot name its unit is a row no execution sitting can close.
    # A stored observation predating SNAG-SYSD-005 carries the *timer's*
    # `Result`, which is `success` on every timer this box has ever had,
    # so it cannot reach this branch; one written since carries
    # `triggered_unit` alongside the `last_result` that admits it.
    triggered = latest.triggered_unit or series.unit.removesuffix(".timer") + ".service"
    return ServiceRecommendationInfo(
        kind="timer_failed",
        severity="advice",
        service=series.service,
        title=f"{series.service}: last scheduled run reported '{latest.last_result}'",
        detail=(
            f"systemd records Result={latest.last_result} for {triggered}, "
            f"started by {series.unit}. "
            "The schedule is firing; what it starts is not succeeding, which "
            "an active-state check cannot see — an armed timer is 'active "
            "(waiting)' whether or not its last run worked."
        ),
        action=(
            f"journalctl --user -u {triggered} "
            "-n 100 — the failure is in the service the timer starts, not in "
            "the timer."
        ),
        recoverable_points=0,
        grade="reliable",
        confidence="high",
        evidence="event",
    )


def _timer_stale_row(
    series: TimerSeries,
    points: list[TimerPoint],
    settings: ServiceActionsConfig,
    check_interval_seconds: int,
    now: datetime,
) -> ServiceRecommendationInfo | None:
    """A timer that is armed and has stopped firing.

    ``tasks.md``'s second scoped example ("alfred-evaluate.timer inactive
    3 days — the schedule has stopped"), built as specified.  Note what
    it is *not*: a timer whose unit has gone inactive is already a failing
    check, so it is counted, scored and covered by ``outage`` above.  The
    case with no owner is the one this row is for — ``active (waiting)``,
    armed, and silently not firing.

    **Filed as ``SNAG-SVC-002``.**  ``self_monitor``/``stalls.py`` owns
    "has not run" for *agents* and escalates it on a ladder; this row
    asks the same question about a *timer* and owns no ladder, so the two
    families answer one question in two voices for different subjects.
    They do not overlap today — no agent is a timer here — but "different
    subjects" is a property of this box rather than of the design, and a
    second owner of one lifecycle is a shape this repository has found at
    six scales.
    """
    if not any(p.is_active for p in points[-1:]):
        return None  # inactive: the outage family already has it

    fires = _observed_fires(points)
    cadence = _observed_cadence(fires, points, check_interval_seconds)
    if cadence is None:
        return None

    last_fire = fires[-1] if fires else None
    if last_fire is None:
        return None

    elapsed = (now - last_fire).total_seconds()
    if elapsed <= cadence * settings.timer_stale_multiplier:
        return None

    missed = int(elapsed // cadence)
    return ServiceRecommendationInfo(
        kind="timer_stale",
        severity="advice",
        service=series.service,
        title=(
            f"{series.service}: armed but has not fired for "
            f"{_hours(elapsed)}"
        ),
        detail=(
            f"{series.unit} is active (waiting), so every check passes, but "
            f"its last observed run was {_hours(elapsed)} ago against an "
            f"observed cadence of {_hours(cadence)} — about {missed} firings "
            "missed. Measured by watching LastTriggerUSec change between "
            "checks, so the figure is dated to the check that noticed and a "
            "gap in the series makes it read short rather than long."
        ),
        action=(
            f"systemctl --user list-timers {series.unit} and check "
            f"OnCalendar= against the wall clock — a timer whose next "
            "elapse has passed without firing usually has a calendar "
            "expression that no longer matches."
        ),
        recoverable_points=0,
        grade="reliable",
        confidence="high",
        evidence="absence",
    )


# --- internals ---


def _observed_fires(points: list[TimerPoint]) -> list[datetime]:
    """The ``checked_at`` of every observation whose token had moved.

    The first point cannot be a fire: there is no earlier observation to
    differ from, and treating it as one would date every timer's last run
    to the start of the lookback.  A token going from ``None`` to a value
    *is* a fire — that is a timer running for the first time.
    """
    fires: list[datetime] = []
    previous = points[0].last_run
    for point in points[1:]:
        if point.last_run != previous:
            fires.append(point.checked_at)
            previous = point.last_run
    return fires


def _observed_cadence(
    fires: list[datetime],
    points: list[TimerPoint],
    check_interval_seconds: int,
) -> float | None:
    """Median seconds between fires, over intervals with no hole in them.

    ``None`` when fewer than :data:`MIN_CADENCE_SAMPLES` clean intervals
    survive — no cadence is claimed from one sample, and none is invented
    from the lookback length.
    """
    if len(fires) < MIN_CADENCE_SAMPLES + 1:
        return None

    holes = _series_holes(points, check_interval_seconds)
    samples = [
        (later - earlier).total_seconds()
        for earlier, later in zip(fires[:-1], fires[1:], strict=True)
        if not any(earlier < hole_end and hole_start < later
                   for hole_start, hole_end in holes)
    ]
    if len(samples) < MIN_CADENCE_SAMPLES:
        return None
    return median(samples)


def _series_holes(
    points: list[TimerPoint], check_interval_seconds: int
) -> list[tuple[datetime, datetime]]:
    """Spans where the monitor stopped observing.

    A hole is a pair of consecutive checks further apart than
    :data:`SERIES_HOLE_FACTOR` intervals.  It is the *monitor's* gap, and
    an interval containing one measures that gap rather than the
    schedule.
    """
    threshold = timedelta(seconds=check_interval_seconds * SERIES_HOLE_FACTOR)
    return [
        (earlier.checked_at, later.checked_at)
        for earlier, later in zip(points[:-1], points[1:], strict=True)
        if later.checked_at - earlier.checked_at > threshold
    ]


def _longest(score: ReliabilityScore) -> str:
    """", longest N min" — omitted when every episode was one check."""
    if not score.longest_outage_minutes:
        return ""
    return f", longest {score.longest_outage_minutes:g} min"


def _forecast(points: int, window_days: int) -> str:
    """The tense marker every points-bearing row carries.

    Stated on the row rather than in this module's docstring alone,
    because ``detail`` is what reaches a reader and the arithmetic is
    genuinely counter-intuitive: nothing is recovered by acting today.
    """
    return (
        f"Worth {points} point{'' if points == 1 else 's'}, recovered once "
        f"the fix has held for the full {window_days}-day window — the "
        "deduction is charged for failures already recorded and lapses as "
        "they age out."
    )


def _hours(seconds: float) -> str:
    """Human duration in the largest unit that keeps it readable."""
    hours = seconds / 3600
    if hours < 1:
        return f"{seconds / 60:.0f} min"
    if hours < 48:
        return f"{hours:.1f} h"
    return f"{hours / 24:.1f} days"


def _kind_rank(kind: str) -> int:
    """Position in :data:`KIND_ORDER`; unknown kinds sort last."""
    return KIND_ORDER.index(kind) if kind in KIND_ORDER else len(KIND_ORDER)


def _severity_rank(severity: str) -> int:
    """Position in :data:`ADVICE_SEVERITIES`; an unknown rung is quietest.

    Reading an unrecognised severity as the **quietest** keeps the list
    ordering it replaced exactly: ``r.severity != "risk"`` sorted
    ``advice`` and any unknown value together, behind ``risk``.  It is
    also the direction that cannot lie in the fold — an unknown rung
    cannot promote a row it was swallowed into.
    """
    return ADVICE_SEVERITIES.index(severity) if severity in ADVICE_SEVERITIES else 0


def _loudest(rows: Sequence[ServiceRecommendationInfo]) -> str:
    """The loudest rung in a fold — :func:`_folded_row` rule 3."""
    return max((row.severity for row in rows), key=_severity_rank)
