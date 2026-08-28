"""The shared quiet-then-loud ladder (Session 39).

Pure functions, so these are pinned directly rather than through an agent.
Two of them exist because the obvious implementation is wrong in a way
that stays green under a careless test: string comparison of severities,
and de-escalation read as an escalation.
"""

import pytest

from sysadmin.core.escalation import (
    QUIETEST_SEVERITY,
    SEVERITY_ORDER,
    Ladder,
    Step,
    may_quieten_in_place,
    step_for,
)

NUDGE = Ladder(quiet="info", loud="warning")
STALL = Ladder(quiet="warning", loud="critical")


class TestSeverityOrder:
    def test_loudness_is_not_alphabetical(self):
        """The trap this dict exists to avoid.

        ``"critical" < "warning"`` is True as strings, so comparing the
        severities directly would classify every escalation to critical as
        a de-escalation — and the ladder would hold for ever at warning
        while looking like it was working.
        """
        assert "critical" < "warning"  # the naive comparison...
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["warning"]  # ...and the fix

    def test_covers_every_severity_the_tray_knows(self):
        assert set(SEVERITY_ORDER) == {"info", "warning", "critical"}


class TestLadderRungs:
    def test_below_the_threshold_is_none_not_a_sentinel_string(self):
        assert NUDGE.severity_for(6, 7, 7) is None

    def test_at_the_threshold_is_quiet(self):
        assert NUDGE.severity_for(7, 7, 7) == "info"

    def test_after_the_gap_is_loud(self):
        assert NUDGE.severity_for(14, 7, 7) == "warning"

    def test_a_zero_gap_is_loud_from_the_first_rung(self):
        """Legitimate: it means "never merely quiet about this"."""
        assert NUDGE.severity_for(7, 7, 0) == "warning"

    def test_the_two_users_start_at_different_volumes(self):
        """Not an accident — see the two modules' docstrings.

        A nudge never reaches critical (criticals pierce DND, and waking
        someone about a roadmap item is how a monitor gets muted). A stall
        must, because critical is the only severity the tray leaves on
        screen.
        """
        assert NUDGE.severity_for(99, 7, 7) == "warning"
        assert STALL.severity_for(99, 0, 24) == "critical"

    def test_the_gap_is_measured_from_the_threshold_not_from_zero(self):
        """The "gap, not a multiplier" rule, in arithmetic.

        A project relaxing its own threshold to 21 days escalates at 28 —
        21 + the global 7 — not at 42. The per-entity knob moves when the
        clock starts, not how patient the escalation is.
        """
        assert NUDGE.severity_for(27, 21, 7) == "info"
        assert NUDGE.severity_for(28, 21, 7) == "warning"


class TestStepFor:
    def test_nothing_open_is_a_raise(self):
        assert step_for("warning", None) is Step.RAISE

    def test_a_quieter_open_row_is_an_escalation(self):
        assert step_for("critical", "warning") is Step.ESCALATE

    def test_an_equal_open_row_holds(self):
        """The branch that stopped the 1,664-row pile-up."""
        assert step_for("warning", "warning") is Step.HOLD

    def test_a_louder_open_row_holds_rather_than_de_escalating(self):
        """Happens when a threshold is lowered with a critical already open.

        Restating a live fault at a lower severity fires a new, less
        urgent notification about something that has not improved.
        De-escalation belongs to recovery, which resolves the row outright.
        """
        assert step_for("warning", "critical") is Step.HOLD

    def test_step_is_a_string_so_it_can_be_stored_and_logged(self):
        assert Step.ESCALATE == "escalate"


# TestNudgesStillUsesTheSharedLadder left with the nudges in the Session
# 4 cutover (ADR-0005). It pinned that sysadmin.projects.nudges climbed
# *this* ladder rather than a copy; the estate's port inlined the ladder
# deliberately (estate ADR-0008 §3) because the estate labels its own
# published data and this repo's escalation policy stays this repo's.
# The two are now free to differ, which is the point — but if the
# severities are ever meant to agree again, that is a shared contract and
# belongs in estate-lib, not in two hand-kept copies.


# ── The ladder's clock, shared by both families (Session 43) ──────────


class TestHoursSince:
    """``hours_since`` moved into ``core`` when a second family needed it.

    ``stalls.py`` and ``failures.py`` both measure elapsed time from
    ``alerts.created_at`` to decide the rung. Three copies of that
    (``self_monitor`` carries its own for ``agent_runs.started_at``) is
    how two ladders stop agreeing about when to escalate.
    """

    def test_measures_whole_hours(self):
        from datetime import UTC, datetime, timedelta

        from sysadmin.core.escalation import hours_since

        now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
        assert hours_since(now - timedelta(hours=26), now) == 26.0

    def test_a_naive_datetime_is_read_as_utc(self):
        """Not every value comes from a round trip.

        An ``Alert`` built in a test, or a default applied in Python,
        is naive — and mixing aware and naive raises ``TypeError``, which
        would take the whole health check down rather than misreport one
        row.
        """
        from datetime import UTC, datetime

        from sysadmin.core.escalation import hours_since

        now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
        naive = datetime(2026, 8, 13, 6, 0)
        assert hours_since(naive, now) == 6.0

    def test_a_future_timestamp_clamps_to_zero(self):
        """Clock skew must not read as "below every threshold".

        A negative elapsed would silently suppress the rung rather than
        opening it quiet.
        """
        from datetime import UTC, datetime, timedelta

        from sysadmin.core.escalation import hours_since

        now = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
        assert hours_since(now + timedelta(hours=3), now) == 0.0


class TestHumaniseHours:
    """Shared so two toasts about different faults phrase time the same."""

    @pytest.mark.parametrize(
        "hours,expected",
        [
            (0.01, "1 minute"),
            (0.5, "30 minutes"),
            (1.0, "1 hour"),
            (26.0, "26 hours"),
            (48.0, "2 days"),
            (24.0 * 9, "9 days"),
        ],
    )
    def test_phrasing(self, hours, expected):
        from sysadmin.core.escalation import humanise_hours

        assert humanise_hours(hours) == expected

    def test_both_families_render_the_same_elapsed_time_identically(self):
        """The point of sharing it rather than copying it."""
        from datetime import UTC, datetime, timedelta

        from sysadmin.core.escalation import Step
        from sysadmin.monitor.failures import FailureAlert
        from sysadmin.monitor.stalls import StallAlert

        at = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
        first = at - timedelta(hours=50)

        stall = StallAlert(
            agent_name="a", severity="critical", step=Step.ESCALATE,
            last_run_at="t", stall_reason=None, seconds_since_last_run=1.0,
            interval_seconds=300, first_alerted_at=first,
            hours_since_first_alert=50.0, escalate_after_hours=24.0,
        )
        failure = FailureAlert(
            agent_name="a", severity="critical", step=Step.ESCALATE,
            consecutive_failures=3, last_error=None, last_run_at="t",
            failure_threshold=2, first_alerted_at=first,
            hours_since_first_alert=50.0, escalate_after_hours=24.0,
        )
        assert "2 days" in stall.message
        assert "2 days" in failure.message


class TestNoPrivateCopiesRemain:
    def test_neither_family_carries_its_own_clock(self):
        """Guards the copy coming back.

        Both modules had a verbatim ``_hours_since`` and
        ``_humanise_hours`` before Session 43; reuse required the move
        first, and a reintroduced copy would drift silently.
        """
        from pathlib import Path

        for module in ("sysadmin/monitor/stalls.py", "sysadmin/monitor/failures.py"):
            source = Path(module).read_text()
            assert "def _hours_since" not in source, module
            assert "def _humanise_hours" not in source, module


class TestQuietestSeverity:
    """The floor is derived, never written down."""

    def test_it_is_the_bottom_of_the_ordering(self):
        assert SEVERITY_ORDER[QUIETEST_SEVERITY] == min(SEVERITY_ORDER.values())

    def test_it_is_not_a_literal_beside_the_ordering(self):
        """``max_priority_for`` against ``PRIORITY_MAP``'s rule.

        A constant written as ``"info"`` agrees with the ordering today
        and stops agreeing the day a quieter rung is added — and the
        failure would be silent, because :func:`may_quieten_in_place`
        would go on permitting a write to a rung that is no longer
        inaudible.  Asserting the *value* cannot see that, since a
        literal and a derivation both read ``"info"``; the source is the
        only place provenance exists.
        """
        from pathlib import Path

        source = Path("sysadmin/core/escalation.py").read_text()
        line = next(
            ln for ln in source.splitlines() if ln.startswith("QUIETEST_SEVERITY")
        )
        assert "SEVERITY_ORDER" in line
        assert '"info"' not in line


class TestMayQuietenInPlace:
    """``SNAG-ESTATE-010``'s surviving half, as a rule about two rungs.

    Session 39 bans an in-place *escalation* because an escalation must
    be heard and the tray's ``{severity}:{title}`` fingerprint is already
    suppressed.  A quietening wants that outcome, so the ban is
    asymmetric — but only as far as the floor.
    """

    def test_a_warning_row_may_be_quietened(self):
        assert may_quieten_in_place("info", "warning") is True

    def test_a_critical_row_may_be_quietened_all_the_way(self):
        """Two rungs at once is still one write to an inaudible rung."""
        assert may_quieten_in_place("info", "critical") is True

    def test_a_fall_that_stops_short_of_the_floor_is_refused(self):
        """Rule 1, and the clause a "downward is safe" fix would omit.

        ``warning:title`` is a fingerprint the tray speaks, so this write
        would arrive as a fresh, less urgent notification about a fault
        that has not improved — which is exactly what :func:`step_for`
        refuses in its own docstring.
        """
        assert may_quieten_in_place("warning", "critical") is False

    def test_an_escalation_is_refused(self):
        assert may_quieten_in_place("critical", "info") is False
        assert may_quieten_in_place("warning", "info") is False

    def test_an_unchanged_rung_is_not_a_move(self):
        for rung in SEVERITY_ORDER:
            assert may_quieten_in_place(rung, rung) is False

    def test_an_unrecognised_rung_is_refused_on_either_side(self):
        """Rule 4 — refused, not defaulted.

        ``SEVERITY_ORDER.get(..., 0)`` reads an unknown string as the
        floor, which is right where the question is "how loud is this"
        and wrong here: it would read a typo as the quietest rung and
        permit a write to it.  ``chk_alert_severity`` admits three
        values, so a fourth is a bug and the safe answer to a bug is to
        leave the standing row alone.
        """
        assert may_quieten_in_place("infoo", "warning") is False
        assert may_quieten_in_place("info", "wraning") is False

    def test_it_is_total_over_the_rungs_the_database_admits(self):
        """Every ordered pair answers, and only the ones named do.

        The pair-by-pair truth table, so a rewrite cannot quietly widen
        what is permitted while leaving the four named tests green.
        """
        permitted = {
            (wanted, standing)
            for wanted in SEVERITY_ORDER
            for standing in SEVERITY_ORDER
            if may_quieten_in_place(wanted, standing)
        }
        assert permitted == {
            (QUIETEST_SEVERITY, standing)
            for standing in SEVERITY_ORDER
            if standing != QUIETEST_SEVERITY
        }
