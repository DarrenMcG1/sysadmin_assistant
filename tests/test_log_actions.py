"""Tests for log recommendations (Session 27, Tier 2).

The live 2026-08-17 population throughout, because three of the rules
below were written against fixtures, shipped, and corrected within
minutes by the first run against real data — the commands in
``journal_command``'s docstring.
"""

from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.monitor.log_actions import (
    NOISE_MIN_OCCURRENCES,
    RecommendationKind,
    journal_command,
    recommend,
)
from sysadmin.monitor.log_trends import (
    Confidence,
    MessageGroup,
    WindowCoverage,
    build_report,
)

NOW = datetime(2026, 8, 17, 11, 0, tzinfo=UTC)
WINDOW_START = NOW - timedelta(days=7)
PREVIOUS_START = NOW - timedelta(days=14)

#: A coverage that yields ``HIGH``, so a test about ranking is not
#: silently testing rule 4 instead.
CLEAN = WindowCoverage(runs_observed=20_160, runs_expected=20_160, runs_truncated=0)


def _group(message, *, source="kernel", severity="error", current=0, previous=0,
           total=None, first_seen=None, last_seen=None):
    return MessageGroup(
        source=source, severity=severity, message=message,
        current=current, previous=previous,
        total=total if total is not None else current + previous,
        first_seen=first_seen or (WINDOW_START + timedelta(hours=1)),
        last_seen=last_seen or NOW,
    )


def _recommend(groups, *, coverage=CLEAN, declared=None, scopes=None):
    report = build_report(
        groups, window_days=7, window_start=WINDOW_START,
        previous_start=PREVIOUS_START, generated_at=NOW, coverage=coverage,
    )
    return recommend(report, declared, scopes)


BLUETOOTH = _group(
    "Bluetooth: hci0: Failed to set up firmware (-2)",
    current=39_919, previous=0, total=313_209,
    first_seen=datetime(2026, 7, 15, 4, 0, tzinfo=UTC),
)


# ---------------------------------------------------------------------------
# journal_command — the three commands the first live run got wrong
# ---------------------------------------------------------------------------


class TestJournalCommand:
    def test_kernel_uses_dash_k_not_dash_u(self):
        """``kernel`` is not a unit.

        ``read_journal`` has always known this; the first draft of this
        module did not, so the same fact was stated twice and one of them
        was wrong. Verified by running it: ``journalctl -k`` over the
        window returns 31,151 lines.
        """
        assert journal_command("kernel", "2026-08-12 18:11") == (
            "journalctl -k --since '2026-08-12 18:11'"
        )

    def test_a_user_unit_gets_dash_dash_user(self):
        """Seven of the fourteen declared log sources are user units.

        Measured by running both forms: ``journalctl --user -u
        alfred-backend.service`` returns 2,170 lines over the window and
        the same command without ``--user`` returns one — "No entries".
        """
        cmd = journal_command(
            "alfred-backend.service", "2026-08-03 10:34",
            {"alfred-backend.service": True},
        )
        assert cmd == (
            "journalctl --user -u alfred-backend.service "
            "--since '2026-08-03 10:34'"
        )

    def test_a_system_unit_gets_no_scope_flag(self):
        cmd = journal_command(
            "mosquitto.service", "2026-08-12 11:32",
            {"mosquitto.service": False},
        )
        assert "--user" not in cmd
        assert "-u mosquitto.service" in cmd

    def test_an_unknown_source_is_treated_as_a_system_unit(self):
        """Journalctl's own default, and it fails loudly.

        A wrong ``-u`` returns "No entries" immediately; the reverse
        would quietly read a different journal. ``SNAG-UNITS-003``'s
        trade — loud beats misleading.
        """
        assert "--user" not in journal_command("who.service", "2026-08-01", {})
        assert "--user" not in journal_command("who.service", "2026-08-01", None)

    def test_the_emitted_command_never_greps_the_signature(self):
        """The normalised signature matches no real line.

        Its ``N`` placeholders are not in the journal, and its first
        token is usually the unit's own name — which matches every line
        in that unit's journal. Both make the flag worse than useless.
        """
        recs = _recommend([
            _group("alfred-backend.service: Failed with result 'exit-code'.",
                   source="alfred-backend.service",
                   current=18, previous=5, first_seen=PREVIOUS_START)
        ])
        assert recs[0].kind is RecommendationKind.SURGE
        assert "--grep" not in recs[0].action


# ---------------------------------------------------------------------------
# Rule 1 — kind before volume, no invented number merging them
# ---------------------------------------------------------------------------


class TestRanking:
    def test_a_new_fault_outranks_a_39919_occurrence_regular(self):
        """The live pair, as they actually rank.

        ``mosquitto`` dumped core once; the Bluetooth loop fired 39,919
        times. Novelty is the thing a reader cannot get from today's
        alerts, so it goes first — ``FileRecommendationInfo``'s ordering,
        where a projected threshold crossing outranks every byte total.
        """
        recs = _recommend([
            BLUETOOTH,
            _group("mosquitto.service: Failed with result 'core-dump'.",
                   source="mosquitto.service", severity="critical",
                   current=1, first_seen=NOW - timedelta(days=1)),
        ])
        assert recs[0].kind is RecommendationKind.NEW
        assert recs[0].occurrences == 1
        assert recs[-1].kind is RecommendationKind.NOISE

    def test_surge_ranks_between_new_and_noise(self):
        recs = _recommend([
            BLUETOOTH,
            _group("fresh", source="a.service", current=1,
                   first_seen=NOW - timedelta(hours=2)),
            _group("worse", source="b.service", current=52, previous=8,
                   first_seen=PREVIOUS_START),
        ])
        assert [r.kind for r in recs] == [
            RecommendationKind.NEW,
            RecommendationKind.SURGE,
            RecommendationKind.NOISE,
        ]

    def test_volume_orders_within_a_kind(self):
        recs = _recommend([
            _group("quiet", source="a.service", current=2,
                   first_seen=NOW - timedelta(hours=1)),
            _group("loud", source="b.service", current=40,
                   first_seen=NOW - timedelta(hours=1)),
        ])
        assert [r.occurrences for r in recs] == [40, 2]


# ---------------------------------------------------------------------------
# Rule 2 — a declared signature is not work
# ---------------------------------------------------------------------------


class TestDeclaredNoise:
    def test_a_declared_signature_earns_no_recommendation(self):
        declared = {("kernel", "Bluetooth: hciN: Failed to set up firmware (-N)")}
        assert _recommend([BLUETOOTH], declared=declared) == []

    def test_the_key_is_source_and_signature_together(self):
        """``Failed with result 'exit-code'.`` is logged by six services here.

        Declaring it noise on the strength of one would silence a genuine
        failure in the other five, which is why the pair is the key.
        """
        message = "Failed with result 'exit-code'."
        declared = {("a.service", message)}
        recs = _recommend(
            [
                _group(message, source="a.service", current=200,
                       previous=200, first_seen=PREVIOUS_START),
                _group(message, source="b.service", current=200,
                       previous=200, first_seen=PREVIOUS_START),
            ],
            declared=declared,
        )
        assert [r.source for r in recs] == ["b.service"]

    def test_declaring_a_signature_does_not_hide_it_from_the_trend(self):
        """Quietened, never suppressed — it is still counted."""
        report = build_report(
            [BLUETOOTH], window_days=7, window_start=WINDOW_START,
            previous_start=PREVIOUS_START, generated_at=NOW, coverage=CLEAN,
        )
        assert report.signatures[0].current == 39_919
        assert recommend(
            report,
            {("kernel", "Bluetooth: hciN: Failed to set up firmware (-N)")},
        ) == []


# ---------------------------------------------------------------------------
# Rule 3 — loud is not the same as harmless
# ---------------------------------------------------------------------------


class TestNoiseCandidacy:
    def test_volume_alone_is_not_enough(self):
        """A fault first seen this window is NEW however loud it is.

        Recommending that an outage on its second day be silenced is the
        failure this rule exists to prevent.
        """
        recs = _recommend([
            _group("catastrophe", source="a.service", current=50_000,
                   first_seen=NOW - timedelta(days=1))
        ])
        assert recs[0].kind is RecommendationKind.NEW

    def test_a_surging_signature_is_not_offered_as_noise(self):
        recs = _recommend([
            _group("worse and worse", source="a.service",
                   current=40_000, previous=100, first_seen=PREVIOUS_START)
        ])
        assert recs[0].kind is RecommendationKind.SURGE

    def test_below_the_floor_earns_nothing(self):
        recs = _recommend([
            _group("grumble", source="a.service",
                   current=NOISE_MIN_OCCURRENCES - 1,
                   previous=NOISE_MIN_OCCURRENCES - 1,
                   first_seen=PREVIOUS_START)
        ])
        assert recs == []

    @pytest.mark.parametrize("current,previous", [
        (200, 200),   # steady
        (250, 200),   # rising, below the surge ratio
        (150, 400),   # falling — on its way out is worth silencing
        (200, 0),     # returned — standing fault seen through a gap
    ])
    def test_old_and_flat_qualifies_in_all_its_forms(self, current, previous):
        recs = _recommend([
            _group("steady drone", source="a.service", current=current,
                   previous=previous, first_seen=PREVIOUS_START)
        ])
        assert recs[0].kind is RecommendationKind.NOISE


# ---------------------------------------------------------------------------
# Rule 4 — low confidence suppresses arguments from a count, only
# ---------------------------------------------------------------------------


class TestConfidenceGate:
    def test_low_confidence_suppresses_noise(self):
        """A window that is mostly storm still refuses to argue.

        The 2026-08-12 kernel storm on its own day: 104 truncated reads
        of 1,434 instrumented, 7.3 %, above
        :data:`~sysadmin.monitor.log_trends.TRUNCATION_LOW_FRACTION`.
        Every noise row is an argument from a count, and here the count
        is missing an unbounded amount of data.
        """
        gappy = WindowCoverage(runs_observed=1_434, runs_expected=1_440,
                               runs_truncated=104, runs_instrumented=1_434)
        report = build_report(
            [BLUETOOTH], window_days=7, window_start=WINDOW_START,
            previous_start=PREVIOUS_START, generated_at=NOW, coverage=gappy,
        )
        assert report.confidence is Confidence.LOW
        assert recommend(report) == []

    def test_low_confidence_does_not_suppress_a_new_fault(self):
        """The asymmetry that makes confidence worth carrying separately.

        A gap can hide a fault; it cannot invent one. So a first sighting
        survives a gappy series where a volume argument does not.
        """
        gappy = WindowCoverage(runs_observed=1, runs_expected=20_160,
                               runs_truncated=118)
        report = build_report(
            [_group("mosquitto.service: Failed with result 'core-dump'.",
                    source="mosquitto.service", current=1,
                    first_seen=NOW - timedelta(days=1))],
            window_days=7, window_start=WINDOW_START,
            previous_start=PREVIOUS_START, generated_at=NOW, coverage=gappy,
        )
        assert report.confidence is Confidence.LOW
        assert recommend(report)[0].kind is RecommendationKind.NEW

    def test_bounded_truncation_lets_a_noise_row_through(self):
        """The 2026-08-17 reading, and the falsification for that sitting.

        120 truncated reads of 7,000 instrumented is 1.7 %, and under the
        binary flag it suppressed this row for fourteen days.  Driven
        against the live database the same day, the real report produced
        exactly this: two ``noise`` rows, both Bluetooth firmware
        signatures at 39,921 occurrences.

        Safe because truncation is one-directional — it drops entries, so
        the true count is *higher* than 39,919 and "this is loud" is a
        floor the missing data cannot undercut.
        """
        bounded = WindowCoverage(runs_observed=17_730, runs_expected=20_160,
                                 runs_truncated=120, runs_instrumented=7_000)
        report = build_report(
            [BLUETOOTH], window_days=7, window_start=WINDOW_START,
            previous_start=PREVIOUS_START, generated_at=NOW, coverage=bounded,
        )
        assert report.confidence is Confidence.MEDIUM
        rows = recommend(report)
        assert [r.kind for r in rows] == [RecommendationKind.NOISE]
        assert rows[0].occurrences == 39_919

    def test_low_confidence_does_not_suppress_a_surge(self):
        gappy = WindowCoverage(runs_observed=1, runs_expected=20_160,
                               runs_truncated=118)
        report = build_report(
            [_group("worse", source="a.service", current=52, previous=8,
                    first_seen=PREVIOUS_START)],
            window_days=7, window_start=WINDOW_START,
            previous_start=PREVIOUS_START, generated_at=NOW, coverage=gappy,
        )
        assert recommend(report)[0].kind is RecommendationKind.SURGE


# ---------------------------------------------------------------------------
# The snippet has to be usable, or it is Session 48's defect again
# ---------------------------------------------------------------------------


class TestSnippet:
    def test_only_the_noise_kind_carries_a_snippet(self):
        """A row with no snippet must never tell the reader to paste one.

        ``sysadmin-failed.service`` shipped exactly that and became an
        item no execution sitting could close.
        """
        recs = _recommend([
            BLUETOOTH,
            _group("fresh", source="a.service", current=1,
                   first_seen=NOW - timedelta(hours=1)),
            _group("worse", source="b.service", current=52, previous=8,
                   first_seen=PREVIOUS_START),
        ])
        for rec in recs:
            has_snippet = rec.snippet is not None
            assert has_snippet == (rec.kind is RecommendationKind.NOISE)
            if not has_snippet:
                assert "below" not in rec.action
                assert "snippet" not in rec.action.lower()

    def test_the_snippet_parses_and_quietens_the_signature_it_names(self):
        """The loop closes: emit YAML, parse it with the real model, match.

        This is the whole of Tier 2's claim to be executable. Session 48's
        rule is that advice must name a step that can be taken; the step
        here is "paste this", so the paste has to work.
        """
        import yaml

        from sysadmin.core.config import LogNoiseEntry

        rec = _recommend([BLUETOOTH])[0]
        assert rec.kind is RecommendationKind.NOISE

        parsed = yaml.safe_load(rec.snippet)
        raw = parsed["agents"]["log_aggregator"]["known_noise"][0]
        entry = LogNoiseEntry(**raw)

        assert entry.source == "kernel"
        assert entry.signature == "Bluetooth: hciN: Failed to set up firmware (-N)"
        # The pair the agent keys on, and the pair rule 2 keys on.
        assert (entry.source, entry.signature) == (rec.source, rec.signature)
        assert _recommend([BLUETOOTH], declared={(entry.source, entry.signature)}) == []

    def test_the_reason_is_a_placeholder_not_a_generated_sentence(self):
        """The field records the *operator's* judgement.

        A sentence this module wrote would read back as though someone
        had made a decision nobody made.
        """
        rec = _recommend([BLUETOOTH])[0]
        assert "<why this is safe to quieten>" in rec.snippet


class TestEmptyPopulation:
    def test_a_clean_report_recommends_nothing(self):
        assert _recommend([]) == []
