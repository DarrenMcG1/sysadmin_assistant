"""Tests for the pure reliability scorer (Session 25, Tier 1).

The arithmetic is the contract here.  A score is only useful if a reader
can check it, so every test that asserts a score also asserts the
deductions behind it — the two must not be able to drift apart.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.monitor.reliability import (
    DOWNTIME_CAP,
    INSTABILITY_CAP,
    INSTABILITY_PER_EPISODE,
    MIN_CONFIDENT_HISTORY_DAYS,
    HealthPoint,
    score_service,
    score_services,
)

NOW = datetime(2026, 8, 7, 12, 0, tzinfo=UTC)
INTERVAL = 300  # 5 minutes, matching config.yaml


def series(statuses: list[str], *, interval_s: int = INTERVAL,
           end: datetime = NOW) -> list[HealthPoint]:
    """Build an evenly-spaced check series ending at ``end``.

    Last element of ``statuses`` is the most recent check.
    """
    return [
        HealthPoint(
            checked_at=end - timedelta(seconds=interval_s * (len(statuses) - 1 - i)),
            status=status,
        )
        for i, status in enumerate(statuses)
    ]


def full_week(status: str = "ok") -> list[HealthPoint]:
    """A complete 7-day series at the default interval."""
    return series([status] * (7 * 86400 // INTERVAL))


# --- the happy path ---


def test_perfect_service_scores_100_with_no_deductions():
    result = score_service("alfred", full_week(), now=NOW)

    assert result.score == 100
    assert result.grade == "reliable"
    assert result.uptime_percent == 100.0
    assert result.outage_episodes == 0
    assert result.deductions == []
    assert result.confidence == "high"


# --- the two deductions ---


def test_downtime_deduction_equals_lost_uptime():
    # 90 ok, 10 down at the end — one episode, 90% uptime
    result = score_service("svc", series(["ok"] * 90 + ["critical"] * 10), now=NOW)

    assert result.uptime_percent == 90.0
    downtime = next(d for d in result.deductions if d.kind == "downtime")
    assert downtime.points == 10
    assert result.score == 100 - 10 - INSTABILITY_PER_EPISODE


def test_instability_charges_per_episode_including_the_first():
    """A single failed check costs points — it is not a perfect service."""
    result = score_service("svc", series(["ok"] * 99 + ["critical"]), now=NOW)

    assert result.outage_episodes == 1
    instability = next(d for d in result.deductions if d.kind == "instability")
    assert instability.points == INSTABILITY_PER_EPISODE
    assert result.score < 100


def test_three_short_outages_outrank_one_long_one_on_instability():
    """The reason instability is a separate term from downtime.

    Both services lose the same number of checks; the one that dropped
    out repeatedly must score worse, because retry logic survives one
    long outage and dies on three short ones.
    """
    one_long = score_service("long", series(["ok"] * 90 + ["critical"] * 9), now=NOW)
    three_short = score_service(
        "short",
        series(["ok"] * 30 + ["critical"] * 3 + ["ok"] * 30 + ["critical"] * 3
               + ["ok"] * 30 + ["critical"] * 3),
        now=NOW,
    )

    assert one_long.uptime_percent == pytest.approx(three_short.uptime_percent, abs=0.2)
    assert one_long.outage_episodes == 1
    assert three_short.outage_episodes == 3
    assert three_short.score < one_long.score


def test_deductions_are_capped():
    # Down for the whole window: downtime hits its cap, and 20 separate
    # episodes would be 100 points of instability without its own cap.
    flapping = ["critical", "ok"] * 40
    result = score_service("svc", series(flapping), now=NOW)

    downtime = next(d for d in result.deductions if d.kind == "downtime")
    instability = next(d for d in result.deductions if d.kind == "instability")
    assert instability.points == INSTABILITY_CAP
    assert downtime.points <= DOWNTIME_CAP
    assert result.score == max(0, 100 - downtime.points - instability.points)


def test_score_never_goes_below_zero():
    result = score_service("svc", series(["critical"] * 100), now=NOW)

    assert result.score == 100 - DOWNTIME_CAP - INSTABILITY_PER_EPISODE
    assert result.score >= 0


# --- episodes ---


def test_consecutive_failures_collapse_into_one_episode():
    """The whole reason incidents come from health checks, not alerts.

    The alerts table writes one row per failed check — 123 rows for a
    single internet outage on the live host — so counting alerts would
    measure the check interval instead of reliability.
    """
    result = score_service("svc", series(["ok"] * 10 + ["critical"] * 50), now=NOW)

    assert result.failed_checks == 50
    assert result.outage_episodes == 1


def test_longest_outage_measures_to_the_last_failing_check():
    """Not to the recovery check — that one is evidence it was back."""
    result = score_service(
        "svc", series(["ok"] * 5 + ["critical"] * 4 + ["ok"] * 5), now=NOW
    )

    # 4 failing checks 5 minutes apart spans 3 intervals, not 4
    assert result.longest_outage_minutes == 15.0


def test_single_failing_check_has_zero_duration():
    """One sample cannot show how long something lasted."""
    result = score_service("svc", series(["ok"] * 5 + ["critical"] + ["ok"] * 5),
                           now=NOW)

    assert result.outage_episodes == 1
    assert result.longest_outage_minutes == 0.0


def test_an_ongoing_outage_still_counts_as_an_episode():
    """No recovery check yet — the episode must not be dropped."""
    result = score_service("svc", series(["ok"] * 50 + ["critical"] * 10), now=NOW)

    assert result.outage_episodes == 1


def test_mean_time_between_incidents_needs_two_episodes():
    one = score_service("svc", series(["ok"] * 50 + ["critical"] * 5), now=NOW)
    assert one.mean_hours_between_incidents is None

    two = score_service(
        "svc",
        # episode starts 60 checks (= 5 hours) apart
        series(["critical"] + ["ok"] * 59 + ["critical"] + ["ok"] * 10),
        now=NOW,
    )
    assert two.outage_episodes == 2
    assert two.mean_hours_between_incidents == 5.0


# --- 'error' checks are unmeasurable, not failures ---


def test_error_checks_are_excluded_from_every_rate():
    """Mirrors SysAdminAgent._handle_status: an unmeasurable check is
    neither a success nor a failure (SNAG-SYSD-001)."""
    result = score_service("svc", series(["ok"] * 50 + ["error"] * 50), now=NOW)

    assert result.checks_recorded == 100
    assert result.error_checks == 50
    assert result.checks_measured == 50
    assert result.uptime_percent == 100.0
    assert result.score == 100


def test_error_checks_do_not_split_an_outage_into_two_episodes():
    result = score_service(
        "svc",
        series(["ok"] * 10 + ["critical"] * 5 + ["error"] * 3 + ["critical"] * 5),
        now=NOW,
    )

    assert result.outage_episodes == 1


def test_a_window_of_only_errors_scores_100_at_low_confidence():
    result = score_service("svc", series(["error"] * 100), now=NOW)

    assert result.score == 100
    assert result.confidence == "low"
    assert "unmeasurable" in (result.confidence_reason or "")


# --- confidence ---


def test_no_checks_at_all_is_low_confidence_not_a_failure():
    """A service in config.yaml the monitor has never reached.

    Live example: venture-chat and pgbackrest-backup-timer, both added
    to config.yaml on 2026-08-07 before the backend restarted.
    """
    result = score_service("venture-chat", [], now=NOW)

    assert result.score == 100
    assert result.confidence == "low"
    assert result.confidence_reason == "no checks recorded in the window"
    assert result.checks_recorded == 0


def test_thin_history_lowers_confidence():
    # ~1 day of checks in a 7-day window
    result = score_service("new-svc", series(["ok"] * 288), now=NOW)

    assert result.observed_days < 2
    assert result.confidence == "low"
    assert "history" in (result.confidence_reason or "")


def test_a_gappy_window_lowers_confidence_but_never_the_score():
    """A gap means the MONITOR was down. Deducting would charge the
    service for this application's own downtime."""
    # 7 days of history but only a third of the expected checks
    sparse = series(["ok"] * 672, interval_s=900)  # 15-minute spacing
    result = score_service("svc", sparse, now=NOW)

    assert result.observed_days > MIN_CONFIDENT_HISTORY_DAYS
    assert result.coverage_percent < 50
    assert result.confidence == "low"
    assert result.score == 100
    assert result.deductions == []


def test_coverage_is_measured_against_the_configured_interval():
    result = score_service("svc", full_week(), now=NOW, check_interval_seconds=INTERVAL)

    assert result.checks_expected == 7 * 86400 // INTERVAL
    assert result.coverage_percent == pytest.approx(100.0, abs=0.5)


# --- muting ---


def test_a_muted_service_has_its_deductions_waived_not_hidden():
    """Expected-down services are scored, not skipped: a reader must be
    able to tell 'expected down' from 'not monitored'."""
    points = series(["ok"] * 50 + ["critical"] * 50)
    scored = score_service("dev-backend", points, now=NOW, muted=True)
    unmuted = score_service("dev-backend", points, now=NOW, muted=False)

    assert scored.score == 100
    assert scored.muted is True
    assert scored.waived_points == unmuted.waived_points + (100 - unmuted.score)
    unmuted_kinds = [d.kind for d in unmuted.deductions]
    assert [d.kind for d in scored.deductions] == unmuted_kinds
    assert all(d.waived for d in scored.deductions)


# --- window and grading ---


def test_checks_outside_the_window_are_ignored():
    old = [HealthPoint(checked_at=NOW - timedelta(days=30), status="critical")]
    result = score_service("svc", old + full_week(), now=NOW)

    assert result.score == 100
    assert result.first_check_at is not None
    assert result.first_check_at >= result.window_start


@pytest.mark.parametrize(
    ("statuses", "expected_grade"),
    [
        (["ok"] * 100, "reliable"),
        # 88% uptime, 1 episode → 100 - 12 - 5 = 83 → degraded band (85..94)
        # is missed; use 8% down for 100-8-5 = 87
        (["ok"] * 92 + ["critical"] * 8, "degraded"),
        (["ok"] * 70 + ["critical"] * 30, "unreliable"),
        (["critical"] * 100, "failing"),
    ],
)
def test_grade_bands(statuses, expected_grade):
    result = score_service("svc", series(statuses), now=NOW)
    assert result.grade == expected_grade


def test_custom_grade_bands_are_honoured():
    lenient = score_service(
        "svc", series(["ok"] * 90 + ["critical"] * 10), now=NOW,
        grade_bands=(50, 40, 20),
    )
    assert lenient.grade == "reliable"


# --- score_services ---


def test_score_services_orders_worst_first():
    scores = score_services(
        {
            "healthy": full_week(),
            "broken": series(["critical"] * 100),
            "wobbly": series(["ok"] * 95 + ["critical"] * 5),
        },
        now=NOW,
    )

    assert [s.service for s in scores] == ["broken", "wobbly", "healthy"]


def test_score_services_does_not_bury_low_confidence_bad_scores():
    """A thinly-observed failing service is still the most interesting
    row on the page — confidence must not push it down the list."""
    scores = score_services(
        {"healthy": full_week(), "new-and-broken": series(["critical"] * 100)},
        now=NOW,
    )

    assert scores[0].service == "new-and-broken"
    assert scores[0].confidence == "low"


def test_score_services_applies_the_muted_set():
    scores = score_services(
        {"expected-down": series(["critical"] * 100)},
        muted={"expected-down"},
        now=NOW,
    )

    assert scores[0].score == 100
    assert scores[0].muted is True


def test_as_dict_iso_formats_timestamps():
    payload = score_service("svc", full_week(), now=NOW).as_dict()

    assert isinstance(payload["window_start"], str)
    assert payload["window_start"].startswith("2026-07-31")
    assert isinstance(payload["first_check_at"], str)


def test_as_dict_leaves_absent_timestamps_as_none():
    payload = score_service("svc", [], now=NOW).as_dict()

    assert payload["first_check_at"] is None
    assert payload["last_check_at"] is None


# ── skipped checks (Session 78) ──────────────────────────────────────
#
# ``services.yaml`` can declare ``monitor: false`` on a service that is
# inactive by design, and the agent writes those checks as ``skipped``.
# Until 2026-08-25 only ``error`` was excluded from the rates here, so a
# ``skipped`` row counted as measured-and-not-``ok`` — an outage — and
# this box's three declared-unmonitored services each scored **35** and
# graded ``failing`` off 307 checks nobody had taken.
#
# Every test below fails against the pre-fix scorer.  None existed
# before, which is why a wrong score survived from Session 25: the whole
# suite passed either side of the fix, so nothing pinned the behaviour in
# *either* direction.


def test_skipped_checks_are_excluded_from_every_rate():
    """Nobody looked, so there is no evidence to rate.

    The sibling rule does not transfer.
    ``SysAdminAgent._resolve_recovered`` treats ``skipped`` as *healthy*
    — correctly, since an open critical nobody will look at again is a
    pile-up wearing a declaration as an excuse — but that decides whether
    to close an alert.  Importing it here would fabricate a 100 exactly
    as the old behaviour fabricated a 35.
    """
    result = score_service(
        "declared-unmonitored",
        series(["ok"] * 10 + ["skipped"] * 10),
        now=NOW,
        check_interval_seconds=INTERVAL,
    )
    assert result.skipped_checks == 10
    assert result.checks_measured == 10
    assert result.uptime_percent == 100.0
    assert result.failed_checks == 0
    assert result.score == 100


def test_a_window_of_only_skipped_checks_scores_100_at_low_confidence():
    """The live shape: ``venture-chat-large``, 307 of 307 skipped.

    Before the fix this scored 35 (60 downtime capped + 5 instability)
    and graded ``failing``.
    """
    result = score_service(
        "venture-chat-large",
        full_week("skipped"),
        now=NOW,
        check_interval_seconds=INTERVAL,
    )
    assert result.score == 100
    assert result.grade == "reliable"
    assert result.outage_episodes == 0
    assert result.deductions == []
    assert result.confidence == "low"


def test_the_all_skipped_reason_names_the_declaration_not_a_failure():
    """"Nobody looked, by choice" and "the check broke" need different words.

    The remedies are opposites: an all-``error`` service needs its check
    fixed, and an all-``skipped`` one is behaving exactly as declared and
    needs nothing at all.
    """
    result = score_service(
        "s", full_week("skipped"), now=NOW, check_interval_seconds=INTERVAL
    )
    assert result.confidence_reason is not None
    assert "monitor: false" in result.confidence_reason

    errored = score_service(
        "s", full_week("error"), now=NOW, check_interval_seconds=INTERVAL
    )
    assert errored.confidence_reason == "every check in the window was unmeasurable"


def test_skipped_and_error_are_counted_apart():
    """One field holding two claims is ``UnitFinding.enabled``'s trap.

    Both mean nothing was measured; the difference is who decided, and a
    reader cannot recover it from a sum.
    """
    result = score_service(
        "s",
        series(["ok"] * 5 + ["error"] * 3 + ["skipped"] * 2),
        now=NOW,
        check_interval_seconds=INTERVAL,
    )
    assert result.error_checks == 3
    assert result.skipped_checks == 2
    assert result.checks_measured == 5


def test_skipped_checks_do_not_split_an_outage_into_two_episodes():
    """A declared gap is not a recovery.

    ``error`` already had this rule; ``skipped`` reaches
    ``_outage_episodes`` through the same filter, so the two cannot
    disagree about what interrupts an episode.
    """
    result = score_service(
        "s",
        series(["ok", "critical", "skipped", "critical", "ok"]),
        now=NOW,
        check_interval_seconds=INTERVAL,
    )
    assert result.outage_episodes == 1
    # The episode count alone passes against the pre-fix scorer too, for
    # the wrong reason: a ``skipped`` row counted as *down*, so it joined
    # the outage rather than being dropped from it.  The counts are what
    # tell the two apart — 2 failures out of 4 measured, not 3 out of 5.
    assert result.failed_checks == 2
    assert result.checks_measured == 4
    assert result.skipped_checks == 1


def test_a_skipped_service_produces_no_advice():
    """The end-to-end consequence, asserted where it was actually felt.

    ``GET /api/services/actions`` served three ``risk`` rows worth 60
    recoverable points each — 180 of its 213 total — for services nobody
    was monitoring.  That is what made a wrong number on a page loud
    enough to find.
    """
    from sysadmin.core.config import ServiceActionsConfig
    from sysadmin.monitor.service_recommendations import recommend

    result = score_service(
        "venture-chat-large",
        full_week("skipped"),
        now=NOW,
        check_interval_seconds=INTERVAL,
    )
    report = recommend(
        [result], ServiceActionsConfig(), check_interval_seconds=INTERVAL, now=NOW
    )
    assert report.recommendations == []
