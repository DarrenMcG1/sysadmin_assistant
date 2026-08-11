"""The shared quiet-then-loud ladder (Session 39).

Pure functions, so these are pinned directly rather than through an agent.
Two of them exist because the obvious implementation is wrong in a way
that stays green under a careless test: string comparison of severities,
and de-escalation read as an escalation.
"""

import pytest

from sysadmin.core.escalation import SEVERITY_ORDER, Ladder, Step, step_for

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


class TestNudgesStillUsesTheSharedLadder:
    """The reason this module is in ``core`` at all.

    ``sysadmin.monitor`` may not import ``sysadmin.projects``
    (``tests/test_import_boundary.py``), so the alternative to sharing was
    copying — and a copied rule drifts in the direction nobody notices.
    """

    def test_nudge_severities_come_from_the_shared_ladder(self):
        from sysadmin.projects import nudges

        assert nudges.NUDGE_LADDER.quiet == "info"
        assert nudges.NUDGE_LADDER.loud == "warning"
        assert nudges.SEVERITY_ORDER is SEVERITY_ORDER

    @pytest.mark.parametrize(
        ("days", "expected"),
        [(6, None), (7, "info"), (13, "info"), (14, "warning")],
    )
    def test_nudge_severity_for_is_unchanged_by_the_move(self, days, expected):
        from sysadmin.projects.nudges import severity_for

        assert severity_for(days, 7, 7) == expected
