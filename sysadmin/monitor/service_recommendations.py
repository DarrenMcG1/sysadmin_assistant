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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import TYPE_CHECKING

from sysadmin.core.contracts import ServiceRecommendationInfo
from sysadmin.monitor.reliability import ReliabilityScore

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sysadmin.core.config import ServiceActionsConfig

__all__ = [
    "EVENT_ARGUED",
    "KIND_ORDER",
    "MIN_CADENCE_SAMPLES",
    "RATE_ARGUED",
    "SERIES_HOLE_FACTOR",
    "AdviceReport",
    "TimerPoint",
    "TimerSeries",
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

    recs.sort(
        key=lambda r: (
            r.severity != "risk",
            -r.recoverable_points,
            _kind_rank(r.kind),
            r.service,
        )
    )
    return AdviceReport(
        recommendations=recs,
        muted_skipped=muted_skipped,
        suppressed_by_confidence=suppressed,
        services_considered=len(scores) - muted_skipped,
    )


def total_recoverable_points(recs: list[ServiceRecommendationInfo]) -> int:
    """Points that lapse if every recommendation holds for a full window.

    Summed across services, so it is an estate figure rather than a
    score: two services each recovering 30 points do not make one
    service's 60.
    """
    return sum(r.recoverable_points for r in recs)


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
