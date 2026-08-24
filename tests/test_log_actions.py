"""Tests for log recommendations (Session 27, Tier 2).

The live 2026-08-17 population throughout, because three of the rules
below were written against fixtures, shipped, and corrected within
minutes by the first run against real data — the commands in
``journal_command``'s docstring.
"""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from sysadmin.monitor.log_actions import (
    INCIDENT_WINDOW_SECONDS,
    NOISE_MIN_OCCURRENCES,
    RecommendationKind,
    group_incidents,
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

#: The two moments the ``journal_command`` tests read, with the epoch
#: journalctl resolves them to written out rather than computed.
#:
#: Computing ``int(dt.timestamp())`` in the assertion would be a second
#: implementation of the thing under test, and it would agree with a
#: broken one — ``max_priority_for``'s rule.  These literals were checked
#: against ``date -d @<n> -u`` on 2026-08-24.
KERNEL_WINDOW = datetime(2026, 8, 12, 18, 11, tzinfo=UTC)
KERNEL_WINDOW_EPOCH = "@1786558260"
CRASH_WINDOW = datetime(2026, 8, 12, 11, 32, tzinfo=UTC)
CRASH_WINDOW_EPOCH = "@1786534320"


def _group(message, *, source="kernel", severity="error", current=0, previous=0,
           total=None, first_seen=None, last_seen=None):
    return MessageGroup(
        source=source, severity=severity, message=message,
        current=current, previous=previous,
        total=total if total is not None else current + previous,
        first_seen=first_seen or (WINDOW_START + timedelta(hours=1)),
        last_seen=last_seen or NOW,
    )


def _recommend(groups, *, coverage=CLEAN, declared=None, scopes=None,
               related=None):
    report = build_report(
        groups, window_days=7, window_start=WINDOW_START,
        previous_start=PREVIOUS_START, generated_at=NOW, coverage=coverage,
    )
    return recommend(report, declared, scopes, related)


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
        assert journal_command("kernel", KERNEL_WINDOW) == (
            f"journalctl -k --since '{KERNEL_WINDOW_EPOCH}'"
        )

    def test_a_user_unit_gets_dash_dash_user(self):
        """Seven of the fourteen declared log sources are user units.

        Measured by running both forms: ``journalctl --user -u
        alfred-backend.service`` returns 2,170 lines over the window and
        the same command without ``--user`` returns one — "No entries".
        """
        cmd = journal_command(
            "alfred-backend.service", datetime(2026, 8, 3, 10, 34, tzinfo=UTC),
            {"alfred-backend.service": True},
        )
        assert cmd == (
            "journalctl --user -u alfred-backend.service "
            "--since '@1785753240'"
        )

    def test_a_system_unit_gets_no_scope_flag(self):
        cmd = journal_command(
            "mosquitto.service", CRASH_WINDOW,
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
        moment = datetime(2026, 8, 1, tzinfo=UTC)
        assert "--user" not in journal_command("who.service", moment, {})
        assert "--user" not in journal_command("who.service", moment, None)

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
# SNAG-LOG-009 — the window journalctl actually opens
# ---------------------------------------------------------------------------


def _journalctl_reads(stamp: str, zone: ZoneInfo) -> datetime:
    """Resolve a ``--since`` argument the way journalctl resolves it.

    Two readings, and the whole defect is which one applies.  ``@<n>`` is
    an instant and carries no zone; anything else is a wall clock read in
    the **reader's local** time.  Modelling the consumer is what makes
    these tests able to fail — asserting the string alone pins today's
    rendering rather than what it means, which is exactly how the old
    form survived three sittings of green tests.
    """
    if stamp.startswith("@"):
        return datetime.fromtimestamp(int(stamp[1:]), tz=UTC)
    return (
        datetime.strptime(stamp, "%Y-%m-%d %H:%M")
        .replace(tzinfo=zone)
        .astimezone(UTC)
    )


def _since_argument(command: str) -> str:
    _, _, tail = command.partition("--since '")
    return tail.rstrip("'")


class TestTheWindowJournalctlOpens:
    """``SNAG-LOG-009``: all nine live rows pointed at the wrong hour.

    Measured on this box on 2026-08-24 before the fix: the mosquitto
    entry is stored ``2026-08-22 18:10:16.115268+01`` and the emitted
    command read ``--since '2026-08-22 17:10'``, which journalctl takes
    as *local* — an hour early here, and five hours **late** at UTC−5,
    where the window opens after the incident and returns nothing.
    """

    def test_the_window_opens_at_the_event_in_every_timezone(self):
        """The property the string assertions above cannot state.

        Falsified against the old rendering: substituting
        ``f"{moment:%Y-%m-%d %H:%M}"`` gives 17:11 UTC in London (an hour
        early) and 22:11 UTC in New York (five hours late, past the
        event) — the two failures the entry was filed for, in one test.
        """
        stamp = _since_argument(journal_command("kernel", KERNEL_WINDOW))
        for zone in ("Europe/London", "America/New_York", "UTC"):
            assert _journalctl_reads(stamp, ZoneInfo(zone)) == KERNEL_WINDOW

    def test_no_row_the_endpoint_serves_carries_a_wall_clock_since(self):
        """The population, not one call.

        Three builders format the same field, so a fix applied to one is
        the shape this repository keeps finding.  Driven through
        ``recommend`` over the specimen groups rather than through
        ``journal_command``, because that is what the route serves.
        """
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        commands = [r.action for r in rows if "--since" in r.action]
        assert commands
        assert all(
            _since_argument(command).startswith("@") for command in commands
        )

    def test_the_epoch_never_opens_after_the_event(self):
        """``int()`` truncates, so the window can only widen.

        Sub-second precision is dropped — ``SNAG-LOG-007``'s observation
        about the same renderer, read from the other side: there it made
        a resume floor re-admit its own boundary, here it is the safe
        direction, because a read that starts a fraction early still
        contains the line and one that starts late does not.
        """
        moment = CRASH.replace(microsecond=999_999)
        stamp = _since_argument(journal_command("mosquitto.service", moment))
        assert _journalctl_reads(stamp, ZoneInfo("UTC")) <= moment

    def test_a_naive_moment_is_refused_rather_than_read_as_local(self):
        """The defect cannot come back in through the fix.

        ``datetime.timestamp()`` reads a naive value as local time, which
        is the reading being removed — so accepting one would rebuild
        ``SNAG-LOG-009`` inside its own fix with the right-looking type.
        Empty population by construction: ``logged_at`` is
        ``timestamp with time zone``.
        """
        with pytest.raises(ValueError, match="aware datetime"):
            journal_command("kernel", KERNEL_WINDOW.replace(tzinfo=None))


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


# ──────────────────────────────────────────────────────────────────────
# SNAG-LOG-001 — one incident, one recommendation
# ──────────────────────────────────────────────────────────────────────

#: The live 2026-08-12 specimen, to the microsecond, from
#: ``sysadmin.log_entries`` on the purged table.  The whole family exists
#: because of these six rows, so they are the fixture rather than
#: something shaped like them.
CRASH = datetime(2026, 8, 12, 11, 32, 51, 283926, tzinfo=UTC)

MOSQ = "mosquitto.service"
PROV = "estate-broker-provision.service"

SPECIMEN = [
    (MOSQ, "Process 1705 (mosquitto) of user 950 dumped core.", 0.000000),
    (MOSQ, f"{MOSQ}: Main process exited, code=dumped, status=11/SEGV", 0.000748),
    (MOSQ, f"{MOSQ}: Failed with result 'core-dump'.", 0.032978),
    (MOSQ, "Failed to start Mosquitto MQTT Broker daemon.", 0.033180),
    (PROV, f"{PROV}: Failed with result 'exit-code'.", 0.348495),
    (PROV, "Failed to start Assert the estate MQTT dynsec schema "
           "(roles, ACLs, static clients).", 0.348682),
]

#: What ``declared_relations`` returns for these two units off the real
#: ``/etc/systemd/system`` — ``estate-broker-provision.service`` carries
#: ``After=mosquitto.service`` and ``Wants=mosquitto.service``, and the
#: map is symmetric because only that side declares anything.
BROKER_GRAPH = {
    "mosquitto.service": frozenset({"estate-broker-provision.service"}),
    "estate-broker-provision.service": frozenset({"mosquitto.service"}),
}


def _trends(groups):
    """The ``SignatureTrend`` rows ``build_report`` makes of ``groups``."""
    return build_report(
        groups, window_days=7, window_start=WINDOW_START,
        previous_start=PREVIOUS_START, generated_at=NOW, coverage=CLEAN,
    ).signatures


def _incident_at(groups, when):
    """The group anchored at ``when``, for asserting membership."""
    return next(g for g in groups if g[0].first_seen == when)


def _specimen_groups(extra=()):
    """The six live rows as first sightings, plus anything given."""
    groups = [
        _group(message, source=source, current=1, previous=0, total=1,
               first_seen=CRASH + timedelta(seconds=offset),
               last_seen=CRASH + timedelta(seconds=offset))
        for source, message, offset in SPECIMEN
    ]
    groups.extend(extra)
    return groups


class TestIncidentGrouping:
    """The correlation rule, against the specimen that motivated it."""

    def test_the_six_live_rows_become_one_recommendation(self):
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        assert len(rows) == 1
        assert len(rows[0].members) == 6
        assert rows[0].kind is RecommendationKind.NEW

    def test_the_entrys_own_proposal_leaves_a_phantom_second_fault(self):
        """``SNAG-LOG-001`` proposed "same unit, same window".

        Passing no graph *is* that rule, and it is why this session
        did not implement what the entry asked for: mosquitto's four
        collapse and the provisioner's two stand alone, so the reader is
        told a dependency failed **and separately** that a broker
        crashed.  Two rows is worse than six, not better.
        """
        rows = _recommend(_specimen_groups(), related=None)
        assert len(rows) == 2
        assert {r.source for r in rows} == {
            "mosquitto.service", "estate-broker-provision.service"
        }

    def test_the_anchor_is_the_unit_that_failed_first(self):
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        assert rows[0].source == "mosquitto.service"
        assert rows[0].units == (
            "mosquitto.service", "estate-broker-provision.service"
        )
        assert "mosquitto.service failed first" in rows[0].detail

    def test_the_rollup_names_every_signature_it_swallows(self):
        """``SNAG-ESTATE-001``'s rule: a count cannot name anything."""
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        for _, message, _ in SPECIMEN:
            # Signatures are normalised, so match on a stable prefix
            # rather than the raw line.
            assert message.split(" ")[0][:12] in rows[0].detail

    def test_one_command_reads_every_unit_in_the_incident(self):
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        assert "-u mosquitto.service" in rows[0].action
        assert "-u estate-broker-provision.service" in rows[0].action

    def test_occurrences_are_summed_across_the_incident(self):
        rows = _recommend(_specimen_groups(), related=BROKER_GRAPH)
        assert rows[0].occurrences == 6

    def test_a_lone_signature_is_unchanged_and_carries_no_members(self):
        """The overwhelming majority of rows must not move."""
        rows = _recommend(
            [_group("something new happened", current=1, previous=0, total=1,
                    first_seen=NOW - timedelta(hours=1))],
            related=BROKER_GRAPH,
        )
        assert len(rows) == 1
        assert rows[0].members == ()
        assert rows[0].title.startswith("New fault from")


class TestIncidentRules:
    """One test per rule in :func:`group_incidents`, each falsifiable."""

    def test_rule_1_the_graph_excludes_what_the_window_admits(self):
        """The live false positive, to the millisecond.

        ``alfred-backend.service`` failed **1.2036 s** after the
        mosquitto crash — comfortably inside the window — because
        PostgreSQL was still starting up.  Nothing declares a relation
        between them, and nothing could: alfred-backend is a *user* unit
        and mosquitto a *system* one, so systemd would ignore the
        declaration anyway.
        """
        intruder = _group(
            "alfred-backend.service: Failed with result 'exit-code'.",
            source="alfred-backend.service", current=1, previous=0, total=1,
            first_seen=CRASH + timedelta(seconds=1.2036),
            last_seen=CRASH + timedelta(seconds=1.2036),
        )
        groups = group_incidents(
            _trends(_specimen_groups([intruder])), BROKER_GRAPH
        )
        incident = _incident_at(groups, CRASH)
        assert len(incident) == 6
        assert "alfred-backend.service" not in {t.source for t in incident}

    def test_rule_1_forging_the_edge_admits_it(self):
        """Proves the exclusion above is the graph, not the clock."""
        intruder = _group(
            "alfred-backend.service: Failed with result 'exit-code'.",
            source="alfred-backend.service", current=1, previous=0, total=1,
            first_seen=CRASH + timedelta(seconds=1.2036),
            last_seen=CRASH + timedelta(seconds=1.2036),
        )
        forged = dict(BROKER_GRAPH)
        forged["mosquitto.service"] = frozenset(
            {"estate-broker-provision.service", "alfred-backend.service"}
        )
        groups = group_incidents(
            _trends(_specimen_groups([intruder])), forged
        )
        assert len(_incident_at(groups, CRASH)) == 7

    def test_rule_2_a_relation_must_be_direct_not_transitive(self):
        """``.target`` units are hubs; two hops relates everything.

        Six user units on this box declare
        ``After=network-online.target``.  If a shared neighbour counted,
        every network-using service on the estate would be one incident.
        """
        graph = {
            "a.service": frozenset({"hub.target"}),
            "b.service": frozenset({"hub.target"}),
            "hub.target": frozenset({"a.service", "b.service"}),
        }
        groups = group_incidents(_trends([
            _group("a failed", source="a.service", current=1, total=1,
                   first_seen=CRASH, last_seen=CRASH),
            _group("b failed", source="b.service", current=1, total=1,
                   first_seen=CRASH + timedelta(seconds=0.1),
                   last_seen=CRASH + timedelta(seconds=0.1)),
        ]), graph)
        assert [len(g) for g in groups] == [1, 1]

    def test_rule_3_the_window_is_measured_from_the_anchor(self):
        """Not single-linkage: a chain must not walk away from its start.

        Three signatures 4 s apart are each within the 5 s window of
        their predecessor, and the third is 8 s from the first.  It must
        not join.
        """
        step = INCIDENT_WINDOW_SECONDS - 1
        # Distinct *and* non-numeric: ``signature()`` maps digit runs to
        # ``N``, so "line 0/1/2" would be one signature and this test
        # would pass for the wrong reason.  It did, on the first run.
        groups = group_incidents(_trends([
            _group(word, source="one.service", current=1, total=1,
                   first_seen=CRASH + timedelta(seconds=step * n),
                   last_seen=CRASH + timedelta(seconds=step * n))
            for n, word in enumerate(("alpha broke", "beta broke", "gamma broke"))
        ]))
        assert [len(g) for g in groups] == [2, 1]

    def test_rule_4_only_first_sightings_are_grouped(self):
        """``first_seen`` is an incident moment only for a first sighting.

        The case is reachable only at the window's edge, and that is
        where it is tested.  A signature first seen just *before*
        ``window_start`` is established — ``STEADY`` here — so its
        ``first_seen`` is the day it was born rather than the moment
        anything happened; a first sighting 2.5 s later is inside the
        5 s window and would be swallowed by it.  Dropping the
        first-sighting filter makes the established row the anchor and
        this assertion fail, which is the only way to observe the rule:
        anywhere else in the window, being established already implies
        being too old to reach.
        """
        established = _group(
            "postgres restarting", source="one.service",
            current=5, previous=5, total=10,
            first_seen=WINDOW_START - timedelta(seconds=2),
            last_seen=NOW,
        )
        sighting = _group(
            "brand new fault", source="one.service",
            current=1, previous=0, total=1,
            first_seen=WINDOW_START + timedelta(seconds=0.5),
            last_seen=WINDOW_START + timedelta(seconds=0.5),
        )
        groups = group_incidents(_trends([established, sighting]))
        assert [len(g) for g in groups] == [1]
        assert groups[0][0].signature == "brand new fault"

    def test_rule_5_a_tie_on_first_seen_still_has_one_anchor(self):
        """Seven live ``sysadmin.service`` rows share a millisecond."""
        tied = _trends([
            _group(f"zzz {n}" if n else "aaa first", source="one.service",
                   current=1, total=1, first_seen=CRASH, last_seen=CRASH)
            for n in range(5)
        ])
        first = group_incidents(tied)[0][0].signature
        assert group_incidents(list(reversed(tied)))[0][0].signature == first

    def test_it_fails_open_with_no_graph_at_all(self):
        """Not knowing means not collapsing — never a false merge."""
        groups = group_incidents(_trends(_specimen_groups()), None)
        assert [len(g) for g in groups] == [4, 2]

    def test_a_declared_noise_signature_never_joins_an_incident(self):
        """Already judged is not work, and not somebody else's member."""
        declared = {("mosquitto.service",
                     "Failed to start Mosquitto MQTT Broker daemon.")}
        rows = _recommend(_specimen_groups(), declared=declared,
                          related=BROKER_GRAPH)
        assert len(rows) == 1
        assert len(rows[0].members) == 5
        assert all("Failed to start Mosquitto" not in m.signature
                   for m in rows[0].members)


class TestIncidentJournalCommand:
    def test_others_are_folded_into_one_invocation(self):
        assert journal_command(
            "mosquitto.service", CRASH_WINDOW, {},
            ("estate-broker-provision.service",),
        ) == (
            "journalctl -u mosquitto.service "
            f"-u estate-broker-provision.service --since '{CRASH_WINDOW_EPOCH}'"
        )

    def test_the_scope_flag_is_emitted_once_for_the_whole_group(self):
        command = journal_command(
            "alfred-backend.service", CRASH_WINDOW,
            {"alfred-backend.service": True, "alfred-frontend.service": True},
            ("alfred-frontend.service",),
        )
        assert command.count("--user") == 1
        assert command.startswith("journalctl --user -u alfred-backend.service")

    def test_kernel_never_gains_company(self):
        """It has no unit file, so it declares no relation."""
        assert journal_command("kernel", CRASH_WINDOW, {},
                               ("mosquitto.service",)) == (
            f"journalctl -k --since '{CRASH_WINDOW_EPOCH}'"
        )
