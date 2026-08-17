"""Tests for week-on-week log trends (Session 27, Tier 1).

Every fixture below is built from the live ``sysadmin.log_entries`` table
as measured on 2026-08-17, because the rules being tested were settled by
that data rather than by reasoning — most of all rule 2, which the
obvious implementation gets wrong and which one live row refutes.
"""

from datetime import UTC, datetime, timedelta

from sysadmin.monitor.log_signature import alert_title
from sysadmin.monitor.log_trends import (
    LOW_COVERAGE_FRACTION,
    RATIO_MIN_COUNT,
    SURGE_RATIO,
    TRUNCATION_LOW_FRACTION,
    ChangeKind,
    Confidence,
    MessageGroup,
    WindowCoverage,
    build_report,
)

NOW = datetime(2026, 8, 17, 11, 0, tzinfo=UTC)
WINDOW_START = NOW - timedelta(days=7)
PREVIOUS_START = NOW - timedelta(days=14)


def _group(message, *, source="kernel", severity="error", current=0, previous=0,
           total=None, first_seen=None, last_seen=None):
    return MessageGroup(
        source=source,
        severity=severity,
        message=message,
        current=current,
        previous=previous,
        total=total if total is not None else current + previous,
        first_seen=first_seen or (WINDOW_START + timedelta(hours=1)),
        last_seen=last_seen or NOW,
    )


def _report(groups, coverage=None, truncated=False):
    return build_report(
        groups,
        window_days=7,
        window_start=WINDOW_START,
        previous_start=PREVIOUS_START,
        generated_at=NOW,
        coverage=coverage,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Rule 2 — "new" is a first sighting, not an empty previous window
# ---------------------------------------------------------------------------


class TestNewIsAFirstSighting:
    def test_the_bluetooth_storm_is_returned_not_new(self):
        """The live row that refutes the obvious implementation.

        ``Bluetooth: hci0: Failed to set up firmware (-2)`` reads
        ``current=39,919, previous=0`` on 2026-08-17 and has been storming
        in bursts since 2026-07-15 — 313,209 occurrences across the
        retained window, on five separate days.  Testing ``previous == 0``
        would have made a month-old kernel retry loop the headline of
        "new errors this week", on its fifth outbreak.
        """
        report = _report([
            _group(
                "Bluetooth: hci0: Failed to set up firmware (-2)",
                current=39_919,
                previous=0,
                total=313_209,
                first_seen=datetime(2026, 7, 15, 4, 0, tzinfo=UTC),
                last_seen=datetime(2026, 8, 12, 20, 0, tzinfo=UTC),
            )
        ])
        trend = report.signatures[0]
        assert trend.change is ChangeKind.RETURNED
        assert trend.is_new is False
        assert report.new_signatures == []

    def test_first_seen_inside_the_window_is_new(self):
        """``mosquitto.service`` dumped core for the first time on 2026-08-16."""
        report = _report([
            _group(
                "Process 1705 (mosquitto) of user 950 dumped core.",
                source="mosquitto.service",
                severity="critical",
                current=1,
                previous=0,
                first_seen=datetime(2026, 8, 16, 9, 0, tzinfo=UTC),
            )
        ])
        assert report.signatures[0].change is ChangeKind.NEW
        assert len(report.new_signatures) == 1

    def test_new_wins_over_returned_when_both_would_match(self):
        """Order of the two tests, not a coincidence.

        A genuinely new fault also satisfies ``previous == 0``.  If
        ``RETURNED`` were tested first, rule 2's whole distinction would
        collapse into "nothing is ever new".
        """
        report = _report([
            _group("brand new fault", current=5, previous=0,
                   first_seen=WINDOW_START + timedelta(minutes=1))
        ])
        assert report.signatures[0].change is ChangeKind.NEW

    def test_a_fault_exactly_at_the_window_edge_is_new(self):
        """The boundary is inclusive, so a fault first seen at the window's
        first instant belongs to the window it opened."""
        report = _report([
            _group("edge fault", current=3, previous=0, first_seen=WINDOW_START)
        ])
        assert report.signatures[0].change is ChangeKind.NEW


# ---------------------------------------------------------------------------
# Rule 1 — one signature implementation, and it re-aggregates
# ---------------------------------------------------------------------------


class TestSignatureAggregation:
    def test_distinct_messages_fold_into_one_signature(self):
        """Eight live messages, one fault.

        ``INFO: task X blocked for more than 122 seconds`` and its 245
        twin are separate rows in ``log_entries`` and the same kernel
        hang.  ``GROUP BY message`` cannot see that; the signature can.
        """
        groups = [
            _group(f"INFO: task kworker/11:1:650089 blocked for more than {secs} seconds.",
                   current=2, previous=1)
            for secs in (122, 245, 368, 491)
        ]
        report = _report(groups)
        assert len(report.signatures) == 1
        trend = report.signatures[0]
        assert trend.current == 8
        assert trend.previous == 4
        assert trend.signature == (
            "INFO: task kworker/N:N:N blocked for more than N seconds."
        )

    def test_four_left_over_process_lines_are_one_signature(self):
        """Live: pids 5849, 2489, 2498, 2638 across two windows."""
        groups = [
            _group(f"sportsanalyser-frontend.service: Found left-over process {pid} "
                   "(node) in control group while starting unit.",
                   source="sportsanalyser-frontend.service",
                   severity="warning", current=1)
            for pid in (5849, 2489, 2498, 2638)
        ]
        assert len(_report(groups).signatures) == 1

    def test_severity_is_part_of_the_key(self):
        """One signature at two severities is two alert rows, so two trends.

        ``alert_title`` embeds the severity, so merging them would produce
        a trend row that matches neither alert.
        """
        report = _report([
            _group("Failed with result 'exit-code'.", severity="error", current=3),
            _group("Failed with result 'exit-code'.", severity="warning", current=3),
        ])
        assert len(report.signatures) == 2

    def test_source_is_part_of_the_key(self):
        report = _report([
            _group("Failed with result 'exit-code'.", source="a.service", current=3),
            _group("Failed with result 'exit-code'.", source="b.service", current=3),
        ])
        assert len(report.signatures) == 2

    def test_alert_title_matches_the_alert_family(self):
        """No second derivation of the identity.

        The title here must be the one ``LogAggregatorAgent`` would raise,
        or a reader cannot match a trend row to an alert row.
        """
        message = "Bluetooth: hci0: Failed to set up firmware (-2)"
        report = _report([_group(message, current=5, previous=5)])
        assert report.signatures[0].alert_title == alert_title(
            "error", "kernel", message
        )

    def test_the_newest_line_is_the_sample(self):
        """Normalisation drops the errno; the sample is where it survives.

        ``_record_recurrence`` applies the same rule to ``alert.message``:
        the verbatim example beside a normalised identity should be the
        most recent occurrence, not whichever the database returned first.
        """
        older = _group("usb 1-11: device not accepting address 9, error -71",
                       current=1, last_seen=NOW - timedelta(days=3))
        newer = _group("usb 1-11: device not accepting address 10, error -110",
                       current=1, last_seen=NOW - timedelta(hours=1))
        report = _report([older, newer])
        assert len(report.signatures) == 1
        assert report.signatures[0].sample.endswith("error -110")

    def test_first_seen_is_the_earliest_across_the_folded_group(self):
        early = datetime(2026, 7, 20, tzinfo=UTC)
        report = _report([
            _group("usb 1-11: device descriptor read/64, error -110",
                   current=1, first_seen=early),
            _group("usb 1-11: device descriptor read/64, error -71",
                   current=1, first_seen=NOW - timedelta(hours=2)),
        ])
        assert report.signatures[0].first_seen == early


# ---------------------------------------------------------------------------
# Change classification and the ratio floor
# ---------------------------------------------------------------------------


class TestClassification:
    def test_doubling_is_a_surge(self):
        report = _report([_group("x", current=100, previous=50,
                                 first_seen=PREVIOUS_START)])
        trend = report.signatures[0]
        assert trend.change is ChangeKind.SURGED
        assert trend.ratio == 2.0
        assert trend.ratio >= SURGE_RATIO

    def test_a_small_rise_is_rising_not_surged(self):
        report = _report([_group("x", current=60, previous=50,
                                 first_seen=PREVIOUS_START)])
        assert report.signatures[0].change is ChangeKind.RISING

    def test_a_fall_is_reported(self):
        report = _report([_group("x", current=20, previous=50,
                                 first_seen=PREVIOUS_START)])
        assert report.signatures[0].change is ChangeKind.FALLING

    def test_silence_this_window_is_gone(self):
        report = _report([_group("x", current=0, previous=50,
                                 first_seen=PREVIOUS_START)])
        assert report.signatures[0].change is ChangeKind.GONE
        assert report.signatures[0].ratio is None

    def test_small_numbers_get_no_ratio(self):
        """One occurrence becoming three is a 3x surge and two events.

        Without the floor the loudest row on the page is the quietest
        thing in the logs.
        """
        report = _report([_group("x", current=3, previous=1,
                                 first_seen=PREVIOUS_START)])
        trend = report.signatures[0]
        assert trend.change is ChangeKind.STEADY
        assert trend.ratio is None
        assert 3 < RATIO_MIN_COUNT

    def test_the_floor_clears_when_either_window_is_loud_enough(self):
        report = _report([_group("x", current=RATIO_MIN_COUNT, previous=2,
                                 first_seen=PREVIOUS_START)])
        assert report.signatures[0].change is ChangeKind.SURGED


# ---------------------------------------------------------------------------
# Rule 3 — truncation is decisive, a thin poll series is only suspicious
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_truncation_without_a_denominator_fails_closed(self):
        """No ``runs_instrumented`` means the caller cannot say, so LOW.

        This is the binary behaviour the proportional gate replaced, kept
        as the not-knowing case rather than deleted: a caller reporting
        truncation with no denominator has not measured completeness, and
        serving a volume argument off that is what rule 4 refuses.
        """
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=17_731, runs_expected=20_160, runs_truncated=118))
        assert report.coverage.truncated_fraction == 1.0
        assert report.confidence is Confidence.LOW

    def test_a_bounded_share_of_truncation_is_medium(self):
        """The live 2026-08-17 reading, and the whole point of the change.

        120 truncated reads of 7,000 instrumented is 1.7 %: 103 of them
        one kernel storm on 08-12, 16 of them the first poll after a
        restart.  Under the binary flag this was LOW for fourteen days
        and suppressed every ``noise`` recommendation on the box.
        """
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=17_730, runs_expected=20_160,
            runs_truncated=120, runs_instrumented=7_000))
        assert report.coverage.truncated_fraction < TRUNCATION_LOW_FRACTION
        assert report.confidence is Confidence.MEDIUM

    def test_a_dominant_share_of_truncation_is_still_low(self):
        """Lowering the gate is not the same as removing it.

        The 2026-08-12 storm on its own day: 104 truncated of 1,434
        instrumented, 7.3 %.  A window that is mostly storm must still
        refuse to argue from a count, or this change is the "unblock the
        demo" fix the snag forbids.
        """
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=1_434, runs_expected=1_440,
            runs_truncated=104, runs_instrumented=1_434))
        assert report.confidence is Confidence.LOW

    def test_the_denominator_is_instrumented_runs_not_observed_ones(self):
        """The same truncation count, two divisors, opposite verdicts.

        ``details['truncated_sources']`` first appears 2026-08-12 17:31,
        so 10,730 of the window's 17,730 runs cannot report truncation.
        Dividing by all of them reads 0.68 % against a true 1.71 % — the
        artefact is 2.5x and it self-corrects as those runs age out,
        which is exactly why it must not be left in.
        """
        honest = WindowCoverage(runs_observed=17_730, runs_expected=20_160,
                                runs_truncated=350, runs_instrumented=7_000)
        flattering = WindowCoverage(runs_observed=17_730, runs_expected=20_160,
                                    runs_truncated=350, runs_instrumented=17_730)
        assert honest.truncated_fraction == 0.05
        assert flattering.truncated_fraction < TRUNCATION_LOW_FRACTION
        assert _report([_group("x", current=5)],
                       coverage=flattering).confidence is Confidence.MEDIUM
        # 0.05 is not *above* 0.05, so this one sits on the boundary and
        # stays MEDIUM; one more truncated read tips it.
        assert _report([_group("x", current=5)],
                       coverage=honest).confidence is Confidence.MEDIUM
        tipped = WindowCoverage(runs_observed=17_730, runs_expected=20_160,
                                runs_truncated=351, runs_instrumented=7_000)
        assert _report([_group("x", current=5)],
                       coverage=tipped).confidence is Confidence.LOW

    def test_any_truncation_at_all_costs_high(self):
        """HIGH has never meant "nearly complete" and does not start now.

        Only the floor beneath it moved.  A fully-polled window with one
        truncated read is MEDIUM, not HIGH.
        """
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=20_160, runs_expected=20_160,
            runs_truncated=1, runs_instrumented=20_160))
        assert report.confidence is Confidence.MEDIUM

    def test_a_gap_without_truncation_is_only_medium(self):
        """A missed poll normally costs nothing — the cursor resumes.

        Counting polls alone would charge a fully-recovered gap as data
        loss, which is why truncation is the signal and this is the proxy.
        """
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=10_000, runs_expected=20_160, runs_truncated=0))
        assert report.coverage.fraction < LOW_COVERAGE_FRACTION
        assert report.confidence is Confidence.MEDIUM

    def test_a_full_clean_series_is_high(self):
        report = _report([_group("x", current=5)], coverage=WindowCoverage(
            runs_observed=20_160, runs_expected=20_160, runs_truncated=0))
        assert report.confidence is Confidence.HIGH

    def test_no_expected_runs_is_low_not_high(self):
        """Nothing observed is not the same as nothing wrong."""
        report = _report([_group("x", current=5)], coverage=WindowCoverage())
        assert report.confidence is Confidence.LOW

    def test_coverage_fraction_never_exceeds_one(self):
        cov = WindowCoverage(runs_observed=30_000, runs_expected=20_160)
        assert cov.fraction == 1.0


# ---------------------------------------------------------------------------
# Rule 4 and presentation
# ---------------------------------------------------------------------------


class TestCountsAndOrdering:
    def test_counts_are_never_scaled_by_coverage(self):
        """The divisor would be wrong in an unknown direction.

        The cursor makes ingestion non-proportional to poll count, so a
        rate computed from observed time looks precise and is not.
        ``reliability.py`` made the same call for the same reason.
        """
        thin = _report([_group("x", current=100, previous=50,
                               first_seen=PREVIOUS_START)],
                       coverage=WindowCoverage(runs_observed=1, runs_expected=20_160))
        full = _report([_group("x", current=100, previous=50,
                               first_seen=PREVIOUS_START)],
                       coverage=WindowCoverage(runs_observed=20_160,
                                               runs_expected=20_160))
        assert thin.signatures[0].current == full.signatures[0].current == 100
        assert thin.signatures[0].ratio == full.signatures[0].ratio

    def test_new_outranks_volume(self):
        """A four-occurrence novelty beats a 39,919-occurrence regular.

        Novelty is the thing a reader cannot get by looking at today's
        alerts, which is why it ranks the way a projected disk-threshold
        crossing outranks every byte total in ``FileRecommendationInfo``.
        """
        report = _report([
            _group("Bluetooth: hci0: Failed to set up firmware (-2)",
                   current=39_919, previous=0, total=313_209,
                   first_seen=datetime(2026, 7, 15, tzinfo=UTC)),
            _group("mosquitto.service: Failed with result 'core-dump'.",
                   source="mosquitto.service", current=4, previous=0,
                   first_seen=NOW - timedelta(days=1)),
        ])
        assert report.signatures[0].change is ChangeKind.NEW
        assert report.signatures[0].current == 4

    def test_truncated_is_carried_not_inferred(self):
        """``ports_checked``'s rule: blind must not read as clean."""
        assert _report([], truncated=True).truncated is True
        assert _report([]).truncated is False

    def test_groups_read_reports_the_input_not_the_output(self):
        """34 signatures from 44 groups on the live table — both are facts."""
        groups = [
            _group(f"INFO: task kworker/11:1:{pid} blocked for more than 122 seconds.",
                   current=1)
            for pid in range(650089, 650095)
        ]
        report = _report(groups)
        assert report.groups_read == 6
        assert len(report.signatures) == 1


class TestSourceTrends:
    def test_errors_and_warnings_stay_separate(self):
        """One number cannot say "warnings doubled, errors vanished"."""
        report = _report([
            _group("boom", source="a.service", severity="error",
                   current=0, previous=10, first_seen=PREVIOUS_START),
            _group("careful", source="a.service", severity="warning",
                   current=20, previous=10, first_seen=PREVIOUS_START),
        ])
        source = report.sources[0]
        assert (source.previous_errors, source.current_errors) == (10, 0)
        assert (source.previous_warnings, source.current_warnings) == (10, 20)
        assert source.error_delta == -10

    def test_volume_is_summed_from_groups_not_signatures(self):
        """A source's error volume is a count of lines.

        Folding into signatures first would make the total depend on how
        well the normaliser happened to work on that source's wording.
        """
        report = _report([
            _group(f"usb 1-11: device not accepting address {n}, error -71",
                   current=5)
            for n in (9, 10, 11)
        ])
        assert len(report.signatures) == 1
        assert report.sources[0].current_errors == 15

    def test_critical_counts_as_an_error(self):
        report = _report([
            _group("dumped core", source="mosquitto.service",
                   severity="critical", current=1)
        ])
        assert report.sources[0].current_errors == 1

    def test_biggest_movement_ranks_first_in_either_direction(self):
        """A source whose errors collapsed is as worth seeing as one that doubled."""
        report = _report([
            _group("a", source="quiet.service", current=1, previous=1,
                   first_seen=PREVIOUS_START),
            _group("b", source="collapsed.service", current=0, previous=500,
                   first_seen=PREVIOUS_START),
        ])
        assert report.sources[0].source == "collapsed.service"

    def test_new_signature_count_is_per_source(self):
        report = _report([
            _group("fresh", source="a.service", current=1,
                   first_seen=NOW - timedelta(hours=1)),
            _group("old", source="b.service", current=1, previous=1,
                   first_seen=PREVIOUS_START),
        ])
        by_name = {s.source: s for s in report.sources}
        assert by_name["a.service"].new_signatures == 1
        assert by_name["b.service"].new_signatures == 0


class TestEmptyPopulation:
    def test_no_groups_is_a_clean_report_not_a_crash(self):
        report = _report([])
        assert report.signatures == []
        assert report.sources == []
        assert report.new_signatures == []
        assert report.groups_read == 0
