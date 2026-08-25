"""Tests for service recommendations (Session 25, Tier 2).

Built against the live 2026-08-25 population, which is why the confidence
gate is shaped the way it is: **all 30 configured services were
``confidence: low``** that morning.  The box was powered off 08-18 →
08-22 and ``SNAG-DB-005`` kept the daemon dead a further 22 hours on
08-23, so a 7-day window held ``observed_days: 1.07`` at
``coverage_percent: 15.13``.  A gate on ``confidence == "high"`` would
have shipped an empty endpoint, and the tests below pin the asymmetry
that avoided it rather than the threshold that would have caused it.

The cadence figures are the real ones.  Five daily timers on this box
derive **24.0 h** from ``LastTriggerUSec`` string transitions, and both
weekly timers derive ``None`` — two fires is not a cadence.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.config import ServiceActionsConfig
from sysadmin.core.contracts import (
    ServiceActionsResponse,
    ServiceRecommendationInfo,
)
from sysadmin.monitor.reliability import Deduction, ReliabilityScore
from sysadmin.monitor.service_recommendations import (
    EVENT_ARGUED,
    KIND_ORDER,
    MIN_CADENCE_SAMPLES,
    RATE_ARGUED,
    SERIES_HOLE_FACTOR,
    TimerPoint,
    TimerSeries,
    _observed_cadence,
    _observed_fires,
    _series_holes,
    recommend,
    total_recoverable_points,
)

NOW = datetime(2026, 8, 25, 9, 0, tzinfo=UTC)
CHECK_INTERVAL = 300


def settings(**overrides) -> ServiceActionsConfig:
    return ServiceActionsConfig(**overrides)


def score(
    service: str = "svc",
    *,
    grade: str = "unreliable",
    confidence: str = "high",
    episodes: int = 0,
    longest: float = 0.0,
    uptime: float = 100.0,
    muted: bool = False,
    downtime: int | None = None,
    instability: int | None = None,
    waived: bool = False,
) -> ReliabilityScore:
    """A scored service, with only the fields the advice module reads."""
    deductions = []
    if downtime is not None:
        deductions.append(
            Deduction(kind="downtime", points=downtime, detail="", waived=waived)
        )
    if instability is not None:
        deductions.append(
            Deduction(kind="instability", points=instability, detail="", waived=waived)
        )
    return ReliabilityScore(
        service=service,
        score=100 - sum(d.points for d in deductions if not d.waived),
        grade=grade,
        uptime_percent=uptime,
        checks_measured=307,
        failed_checks=52,
        outage_episodes=episodes,
        longest_outage_minutes=longest,
        confidence=confidence,
        muted=muted,
        deductions=deductions,
    )


def run(scores, *, timers=None, cfg=None):
    return recommend(
        scores,
        cfg or settings(),
        timers=timers,
        check_interval_seconds=CHECK_INTERVAL,
        now=NOW,
    )


def series(
    *offsets_and_tokens,
    service: str = "tmr",
    unit: str = "tmr.timer",
    result: str = "success",
    active: bool = True,
    base: datetime | None = None,
) -> TimerSeries:
    """A timer series from ``(minutes_before_now, token)`` pairs."""
    base = base or NOW
    return TimerSeries(
        service=service,
        unit=unit,
        points=[
            TimerPoint(
                checked_at=base - timedelta(minutes=mins),
                last_run=token,
                last_result=result,
                is_active=active,
            )
            for mins, token in offsets_and_tokens
        ],
    )


def daily_series(fires: int, *, since_last_fire_h: float, **kwargs) -> TimerSeries:
    """A timer polled every 5 minutes whose firings are placed explicitly.

    ``fires`` firings 24 h apart, the last of them ``since_last_fire_h``
    before ``NOW``, with polling starting an hour before the earliest so
    the first firing is observable at all — ``_observed_fires`` cannot
    count ``points[0]``.

    The first version of this helper derived the token from elapsed time
    instead, which made the token keep changing right up to ``NOW`` and
    pinned every "last fire" to 24 h ago whatever the caller asked for.
    Three tests failed against correct code because of it, so the firings
    are now stated rather than computed.
    """
    fire_times = sorted(
        NOW - timedelta(hours=since_last_fire_h + 24 * k) for k in range(fires)
    )
    start = fire_times[0] - timedelta(hours=1)
    points: list[TimerPoint] = []
    at = start
    while at <= NOW:
        fired = sum(1 for f in fire_times if f <= at)
        points.append(
            TimerPoint(
                checked_at=at,
                last_run=f"fire-{fired}" if fired else None,
                last_result=kwargs.get("result", "success"),
                is_active=kwargs.get("active", True),
            )
        )
        at += timedelta(minutes=5)
    return TimerSeries(
        service=kwargs.get("service", "tmr"),
        unit=kwargs.get("unit", "tmr.timer"),
        points=points,
    )


class TestCurrency:
    """``recoverable_points`` comes from the scorer, never from here."""

    def test_outage_row_carries_the_downtime_deduction(self):
        rows = run([score(downtime=17)]).recommendations
        outage = [r for r in rows if r.kind == "outage"]
        assert len(outage) == 1
        assert outage[0].recoverable_points == 17

    def test_flapping_row_carries_the_instability_deduction(self):
        rows = run(
            [score(episodes=3, longest=205.0, downtime=17, instability=15)]
        ).recommendations
        flap = [r for r in rows if r.kind == "flapping"]
        assert len(flap) == 1
        assert flap[0].recoverable_points == 15

    def test_a_waived_deduction_is_never_charged(self):
        """The ``waived`` filter, exercised without the muted skip in front.

        The first version of this test set ``muted=True`` as well, so the
        muted skip returned before the filter was reached and it passed
        against a module that charged waived points — the right outcome
        for the wrong reason.  ``muted=False, waived=True`` is
        unreachable from the scorer today (see the invariant test below)
        and is constructed here precisely so the filter has something to
        do.
        """
        rows = run(
            [score(downtime=60, waived=True, muted=False)]
        ).recommendations
        assert rows == []

    def test_the_scorer_only_ever_waives_on_a_muted_service(self):
        """The invariant the filter above leans on, pinned at its owner.

        ``reliability._deductions`` sets ``waived=muted``, so this
        module's muted skip is *sufficient* today and its ``waived``
        filter is belt-and-braces.  That is a fact about another module,
        and a fact stated in two places that can disagree is
        ``SNAG-DB-003``'s shape — so it is asserted against the real
        scorer rather than assumed here.  If waiving is ever decoupled
        from muting, this fails and the filter starts earning its keep.
        """
        from sysadmin.monitor.reliability import HealthPoint, score_service

        points = [
            HealthPoint(checked_at=NOW - timedelta(minutes=5 * i), status="critical")
            for i in range(20)
        ]
        for muted in (True, False):
            result = score_service(
                "s", points, now=NOW, muted=muted, check_interval_seconds=300
            )
            assert result.deductions
            assert all(d.waived is muted for d in result.deductions)

    def test_rows_with_no_deduction_carry_zero_and_invent_nothing(self):
        rows = run(
            [score(episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        interval = [r for r in rows if r.kind == "check_interval"]
        assert len(interval) == 1
        assert interval[0].recoverable_points == 0

    def test_the_forecast_tense_is_stated_on_every_points_bearing_row(self):
        """The counter-intuitive half, so it is said rather than implied.

        Fixing a service recovers nothing today; the points lapse as the
        recorded failures age out of the window.  A reader who assumes
        ``FileRecommendationInfo``'s immediacy is wrong, so the words are
        in ``detail`` and not only in a docstring.
        """
        rows = run([score(downtime=17)]).recommendations
        assert "recovered once the fix has held" in rows[0].detail
        assert "lapses as they age out" in rows[0].detail

    def test_one_point_is_singular(self):
        """Live at 2026-08-25 ``searxng`` was worth exactly 1 point."""
        rows = run([score(uptime=99.35, downtime=1)]).recommendations
        assert "Worth 1 point," in rows[0].detail

    def test_the_estate_total_sums_across_services(self):
        rows = run(
            [score("a", downtime=60), score("b", downtime=17)]
        ).recommendations
        assert total_recoverable_points(rows) == 77


class TestConfidenceGate:
    """The asymmetry, which is the whole design.

    Driven live on 2026-08-25: at ``confidence: low`` the real population
    produced 7 rows with 1 suppressed, and the same scores with
    confidence forced high produced 8 with 0.
    """

    def test_event_argued_rows_survive_a_low_confidence_window(self):
        """A gap can hide an outage; it can never invent one.

        305 recorded failures are 305 real failures whatever the
        coverage, so a thin window is a floor under the claim rather
        than a doubt about it.
        """
        report = run([score(confidence="low", downtime=60, grade="failing")])
        assert [r.kind for r in report.recommendations] == ["outage"]
        assert report.suppressed_by_confidence == 0

    def test_rate_argued_rows_are_withheld_at_low_confidence(self):
        report = run(
            [score(confidence="low", episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        )
        assert "check_interval" not in [r.kind for r in report.recommendations]
        assert report.suppressed_by_confidence == 1

    def test_the_same_scores_at_high_confidence_produce_the_rate_row(self):
        """The counterfactual, so the gate is seen to do something."""
        report = run(
            [score(confidence="high", episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        )
        assert "check_interval" in [r.kind for r in report.recommendations]
        assert report.suppressed_by_confidence == 0

    def test_every_kind_is_classified_exactly_once(self):
        """A kind in neither tuple would silently bypass the gate.

        The failure mode of forgetting one is not an error — it is a
        rate-argued row served off a 15 %-covered window, which is the
        thing this module exists to refuse.
        """
        assert set(EVENT_ARGUED) | set(RATE_ARGUED) == set(KIND_ORDER)
        assert not set(EVENT_ARGUED) & set(RATE_ARGUED)

    def test_a_suppressed_row_is_counted_rather_than_vanishing(self):
        """"Nothing to do" and "we could not tell" are different answers."""
        report = run(
            [score(confidence="low", episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        )
        assert report.recommendations
        assert report.suppressed_by_confidence == 1

    def test_timer_rows_obey_their_owning_services_confidence(self):
        """A timer's staleness is absence-argued, so it takes the gate.

        The confidence belongs to the service's *health* series and the
        staleness to its *timer* series, which is a wider lookback — but
        both are the same monitor being up or down, so one flag governs.
        """
        stale = daily_series(fires=5, since_last_fire_h=96.0, service="tmr")
        report = run(
            [score("tmr", confidence="low", grade="reliable")],
            timers=[stale],
        )
        assert "timer_stale" not in [r.kind for r in report.recommendations]
        assert report.suppressed_by_confidence == 1


class TestMuting:
    def test_a_muted_service_produces_no_rows_and_is_counted(self):
        report = run([score(muted=True, downtime=60, waived=True)])
        assert report.recommendations == []
        assert report.muted_skipped == 1
        assert report.services_considered == 0

    def test_muted_services_are_excluded_from_services_considered(self):
        report = run(
            [score("a", muted=True, waived=True, downtime=60), score("b", downtime=1)]
        )
        assert report.muted_skipped == 1
        assert report.services_considered == 1


class TestRanking:
    def test_risk_outranks_every_point_total(self):
        rows = run(
            [
                score("healthy-ish", grade="degraded", downtime=1),
                score("dead", grade="failing", downtime=60),
            ]
        ).recommendations
        assert rows[0].service == "dead"
        assert rows[0].severity == "risk"

    def test_points_descend_within_a_severity(self):
        rows = run(
            [
                score("small", grade="degraded", downtime=1),
                score("big", grade="degraded", downtime=17),
            ]
        ).recommendations
        assert [r.service for r in rows] == ["big", "small"]

    def test_kind_order_breaks_a_points_tie(self):
        """``outage`` before ``flapping`` at equal points.

        Both are real failures; the one saying "it was not there" is the
        one to read first.
        """
        rows = run(
            [score("s", grade="degraded", episodes=3, longest=9.0,
                   downtime=15, instability=15)]
        ).recommendations
        assert [r.kind for r in rows] == ["outage", "flapping"]

    def test_ordering_is_stable_on_the_service_name(self):
        rows = run(
            [score("b", grade="degraded", downtime=5),
             score("a", grade="degraded", downtime=5)]
        ).recommendations
        assert [r.service for r in rows] == ["a", "b"]

    def test_severity_is_the_scorers_grade_not_a_second_threshold(self):
        """``failing`` is risk; nothing here re-derives the band."""
        assert run([score(grade="failing", downtime=60)]).recommendations[0].severity == "risk"
        assert run([score(grade="unreliable", downtime=40)]).recommendations[0].severity == "advice"


class TestFlapThreshold:
    def test_below_the_threshold_no_flapping_row(self):
        rows = run(
            [score(episodes=2, longest=9.0, downtime=1, instability=10)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        assert "flapping" not in [r.kind for r in rows]

    def test_at_the_threshold_it_fires(self):
        rows = run(
            [score(episodes=3, longest=9.0, downtime=1, instability=15)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        assert "flapping" in [r.kind for r in rows]

    def test_flapping_needs_an_instability_deduction_not_only_a_count(self):
        """Episodes with no instability points cannot happen and are refused.

        The scorer charges from the first episode, so ``episodes >= 3``
        with no deduction means the two disagree — and inventing a row
        off the count alone would make this module a second opinion on
        an arithmetic the scorer owns.
        """
        rows = run(
            [score(episodes=3, longest=9.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        assert "flapping" not in [r.kind for r in rows]


class TestCheckIntervalRow:
    """``tasks.md``'s first scoped example, built as specified.

    The tension it carries is ``SNAG-SVC-001``, filed rather than argued
    away: advising a longer interval is advising that a fault be seen
    less often, which is ``known_noise`` rule 3's opposite.
    """

    def test_it_fires_only_when_every_episode_was_a_single_check(self):
        """``longest_outage_minutes == 0`` is exact, not a threshold.

        ``_outage_episodes`` dates an episode's end to its last *failing*
        check, so one sample has zero duration by construction.
        """
        rows = run(
            [score(episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        assert "check_interval" in [r.kind for r in rows]

    def test_an_episode_spanning_two_polls_is_an_outage_and_stays_quiet(self):
        rows = run(
            [score(episodes=3, longest=5.0, downtime=1, instability=15)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        assert "check_interval" not in [r.kind for r in rows]

    def test_it_never_tells_the_reader_to_raise_the_interval_outright(self):
        """The narrowing that keeps it honest.

        Volume is what makes a fault worth looking at, not evidence it is
        harmless, so the row asks which of two things is true before
        anything is changed.
        """
        rows = run(
            [score(episodes=3, longest=0.0, downtime=1)],
            cfg=settings(flap_min_episodes=3),
        ).recommendations
        row = next(r for r in rows if r.kind == "check_interval")
        assert "Confirm which before changing anything" in row.detail
        assert "hides a real fault just as well" in row.detail


class TestObservedFires:
    """Identity by inequality — the token is never parsed."""

    def test_a_changed_token_is_a_fire(self):
        s = series((20, "a"), (15, "a"), (10, "b"), (5, "b"))
        fires = _observed_fires(sorted(s.points, key=lambda p: p.checked_at))
        assert len(fires) == 1

    def test_the_first_observation_is_never_a_fire(self):
        """Otherwise every timer's last run dates to the lookback start.

        With no earlier observation to differ from there is nothing to
        compare, and counting it would make every timer look freshly
        fired and this whole family silent.
        """
        s = series((10, "a"), (5, "a"))
        assert _observed_fires(sorted(s.points, key=lambda p: p.checked_at)) == []

    def test_none_to_a_value_is_a_fire(self):
        """A timer running for the first time.

        ``_timer_facts`` omits ``last_run`` rather than writing a
        sentinel, so ``None`` is what "never fired" looks like.
        """
        s = series((10, None), (5, "a"))
        assert len(_observed_fires(sorted(s.points, key=lambda p: p.checked_at))) == 1

    def test_the_token_is_opaque_and_its_content_is_never_read(self):
        """systemd renders ``LastTriggerUSec`` as a local wall clock.

        ``"Tue 2026-08-25 08:00:00 BST"`` carries an ambiguous zone
        abbreviation and, at an autumn fold, names two instants —
        ``SNAG-LOG-009``'s defect.  Nothing here parses it, so a token
        that is not a timestamp at all still works.
        """
        s = series((20, "!!not a date!!"), (10, "@1787641200"), (5, "@1787641200"))
        fires = _observed_fires(sorted(s.points, key=lambda p: p.checked_at))
        assert len(fires) == 1


class TestObservedCadence:
    def test_a_daily_timer_derives_twenty_four_hours(self):
        """The live figure: five daily timers on this box derive 24.0 h."""
        s = daily_series(fires=5, since_last_fire_h=2.0)
        pts = sorted(s.points, key=lambda p: p.checked_at)
        cadence = _observed_cadence(_observed_fires(pts), pts, CHECK_INTERVAL)
        assert cadence == pytest.approx(24 * 3600, rel=0.01)

    def test_two_fires_is_not_a_cadence(self):
        """Both weekly timers on this box derive ``None`` off exactly this.

        ``estate-manager-review-timer`` and ``paccache-timer`` each show
        **2** observed firings, which is one interval — a coincidence,
        not a median.  The same reason
        ``mean_hours_between_incidents`` is ``None`` below two episodes
        rather than invented from the window length.

        The first version of this test passed ``fires=1``, which
        exercises "one firing" and leaves the two-firing case — the one
        that actually occurs on this box — unasserted.
        """
        s = daily_series(fires=2, since_last_fire_h=2.0)
        pts = sorted(s.points, key=lambda p: p.checked_at)
        assert len(_observed_fires(pts)) == 2
        assert _observed_cadence(_observed_fires(pts), pts, CHECK_INTERVAL) is None

    def test_one_fire_is_not_a_cadence_either(self):
        s = daily_series(fires=1, since_last_fire_h=2.0)
        pts = sorted(s.points, key=lambda p: p.checked_at)
        assert _observed_cadence(_observed_fires(pts), pts, CHECK_INTERVAL) is None

    def test_three_fires_is_the_smallest_derivable_cadence(self):
        """Two clean intervals, which is :data:`MIN_CADENCE_SAMPLES`.

        Asserted at the boundary because the guard is stated twice — an
        early return on the fire count and a check on the surviving
        sample count — and two redundant guards mean breaking either one
        alone changes nothing.  The boundary is where both have to be
        right.
        """
        s = daily_series(fires=3, since_last_fire_h=2.0)
        pts = sorted(s.points, key=lambda p: p.checked_at)
        cadence = _observed_cadence(_observed_fires(pts), pts, CHECK_INTERVAL)
        assert cadence == pytest.approx(24 * 3600, rel=0.01)

    def test_a_gap_spanning_interval_is_not_a_cadence_sample(self):
        """It measures the outage, not the schedule.

        ``reliability.py``'s rule 4 ("a gap never becomes a trend")
        applied to the numerator instead of to the score.
        """
        base = NOW
        points = []
        # Three clean daily fires, then a six-day hole, then one more.
        for day, token in ((10, "a"), (9, "b"), (8, "c")):
            for step in range(3):
                points.append(TimerPoint(
                    checked_at=base - timedelta(days=day, minutes=-5 * step),
                    last_run=token,
                ))
        points.append(TimerPoint(checked_at=base - timedelta(hours=1), last_run="d"))
        s = TimerSeries(service="t", unit="t.timer", points=points)
        pts = sorted(s.points, key=lambda p: p.checked_at)
        holes = _series_holes(pts, CHECK_INTERVAL)
        assert holes, "the six-day gap must register as a hole"
        cadence = _observed_cadence(_observed_fires(pts), pts, CHECK_INTERVAL)
        # The hole-spanning interval is dropped, leaving fewer than
        # MIN_CADENCE_SAMPLES clean ones.
        assert cadence is None

    def test_min_cadence_samples_is_two(self):
        assert MIN_CADENCE_SAMPLES == 2


class TestSeriesHoles:
    def test_a_normal_poll_is_not_a_hole(self):
        s = series((15, "a"), (10, "a"), (5, "a"))
        assert _series_holes(sorted(s.points, key=lambda p: p.checked_at), CHECK_INTERVAL) == []

    def test_a_gap_beyond_the_factor_is_a_hole(self):
        s = series((600, "a"), (5, "a"))
        holes = _series_holes(sorted(s.points, key=lambda p: p.checked_at), CHECK_INTERVAL)
        assert len(holes) == 1

    def test_one_missed_poll_is_tolerated(self):
        """2.5 admits a missed poll and jitter, and refuses two."""
        s = series((20, "a"), (10, "a"))  # 10 minutes = 2 intervals
        assert _series_holes(sorted(s.points, key=lambda p: p.checked_at), CHECK_INTERVAL) == []
        assert SERIES_HOLE_FACTOR == 2.5


class TestTimerStale:
    def test_an_armed_timer_past_the_multiplier_is_reported(self):
        s = daily_series(fires=5, since_last_fire_h=96.0)
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_stale" in [r.kind for r in rows]

    def test_inside_the_multiplier_it_stays_quiet(self):
        """A schedule that has missed one firing is merely late.

        ``stall_grace_multiplier``'s argument: it clears itself on the
        next tick, and flagging at 2x charges faults that were about to
        fix themselves.
        """
        s = daily_series(fires=5, since_last_fire_h=48.0)
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_stale" not in [r.kind for r in rows]

    def test_no_cadence_means_no_row_however_long_it_has_been(self):
        """The weekly-timer case, live on this box today.

        Without a derived cadence there is no number to be late against,
        and inventing one from the lookback length is what
        ``_observed_cadence`` refuses.
        """
        s = daily_series(fires=1, since_last_fire_h=500.0)
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_stale" not in [r.kind for r in rows]

    def test_an_inactive_timer_is_left_to_the_outage_family(self):
        """A timer whose unit went inactive is already a failing check.

        Reporting it here as well would give one fault two speakers, the
        second-owner defect this repository has found at six scales.
        """
        s = daily_series(fires=5, since_last_fire_h=96.0, active=False)
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_stale" not in [r.kind for r in rows]

    def test_the_row_says_a_gap_makes_the_figure_read_short(self):
        """The failure direction, stated on the row.

        A fire before a hole is observed at the first check after it, so
        time-since-fire comes out shorter than the truth.  Silence is the
        safe direction and the reader is told which way it errs.
        """
        s = daily_series(fires=5, since_last_fire_h=96.0)
        row = next(
            r for r in run([score("tmr", grade="reliable")], timers=[s]).recommendations
            if r.kind == "timer_stale"
        )
        assert "read short rather than long" in row.detail


class TestTimerFailed:
    def test_a_non_success_result_is_reported(self):
        s = daily_series(fires=5, since_last_fire_h=2.0, result="exit-code")
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_failed" in [r.kind for r in rows]

    def test_success_is_silent(self):
        s = daily_series(fires=5, since_last_fire_h=2.0, result="success")
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_failed" not in [r.kind for r in rows]

    def test_an_absent_result_is_not_a_failure(self):
        """Fails open, ``collation.py``'s posture.

        A check that could not read ``Result`` has not observed a
        failure, and reporting one would raise a row about a unit nobody
        looked at.
        """
        s = daily_series(fires=5, since_last_fire_h=2.0, result=None)
        rows = run([score("tmr", grade="reliable")], timers=[s]).recommendations
        assert "timer_failed" not in [r.kind for r in rows]

    def test_it_survives_low_confidence(self):
        """``Result`` is a recorded outcome, not a rate."""
        s = daily_series(fires=5, since_last_fire_h=2.0, result="exit-code")
        report = run([score("tmr", confidence="low", grade="reliable")], timers=[s])
        assert "timer_failed" in [r.kind for r in report.recommendations]

    def test_the_action_points_at_the_service_not_the_timer(self):
        """The failure is in what the timer starts.

        An armed timer is 'active (waiting)' whether or not its last run
        worked, which is exactly why an active-state check cannot see
        this.
        """
        s = daily_series(fires=5, since_last_fire_h=2.0, result="exit-code",
                         unit="alfred-evaluate.timer")
        row = next(
            r for r in run([score("tmr", grade="reliable")], timers=[s]).recommendations
            if r.kind == "timer_failed"
        )
        assert "alfred-evaluate.service" in row.action


class TestContracts:
    def test_the_row_round_trips(self):
        row = ServiceRecommendationInfo(
            kind="outage", severity="risk", service="s", recoverable_points=60,
        )
        assert ServiceRecommendationInfo(**row.model_dump()) == row

    def test_count_defaults_from_the_list(self):
        payload = ServiceActionsResponse(
            recommendations=[ServiceRecommendationInfo(kind="outage")]
        )
        assert payload.count == 1

    def test_none_numbers_are_coerced_rather_than_raising(self):
        row = ServiceRecommendationInfo(recoverable_points=None, outage_episodes=None)
        assert row.recoverable_points == 0
        assert row.outage_episodes == 0

    def test_an_unknown_field_is_ignored(self):
        row = ServiceRecommendationInfo(kind="outage", future_field="x")
        assert row.kind == "outage"


class TestRouteIsReadOnly:
    """The promise the router docstring makes, asserted.

    ``/api/units/*``'s rule for its reason: the remedy for an unreliable
    service is a fix in the service or an edit to a hand-curated file,
    and restarting one already has its own endpoint at
    ``POST /api/sysadmin/services/{name}/{action}``.  A scheduled agent
    acting on this advice by itself is the thing being refused.
    """

    def test_no_non_get_route_exists_under_api_services(self):
        from sysadmin.main import create_app

        app = create_app()
        routes = {
            r.path: getattr(r, "methods", set())
            for r in app.routes
            if r.path.startswith("/api/services")
        }
        assert routes, "the services router must be mounted"
        assert "/api/services/actions" in routes
        assert all(m <= {"GET", "HEAD"} for m in routes.values())
