"""SNAG-AGENT-009 — a held row's sentence has to keep being true.

Every family that deduplicates on an open title takes a ``held`` branch
and moves on, so ``alert.message`` stayed whatever the **first** run
wrote.  The title is the identity and must not move — Session 42 settled
that, and the tray's ``{severity}:{title}`` fingerprint depends on it —
but the message is what a reader acts on, and until 2026-08-28 only
:meth:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent._record_recurrence`
kept one current.

Measured before it was built: **1,360 held events all-time** across five
families, 838 of them in ``SysAdminAgent._raise_judged``, and across the
23 post-dedup ``High VRAM usage`` rows **42 of 42** polls inside a hold
carried a figure different from the frozen one — 19 of them *below* the
threshold the frozen sentence was asserting.

This file drives the shared primitive.  The three callers are driven
where their own lifecycles are: ``tests/test_alert_dedup.py`` (the 838),
``tests/test_estate_judge_agent.py`` (the 131) and
``tests/test_unit_ports.py`` (the 0).
"""

from sysadmin.core.agent import BaseAgent
from sysadmin.core.models.alert import Alert


def _row(message="VRAM at 90.1% (threshold: 90%)", details=None):
    return Alert(
        agent="sysadmin",
        severity="warning",
        title="High VRAM usage on Radeon RX 7900 XTX",
        message=message,
        details={"card": "card1", "vram_percent": 90.1} if details is None else details,
    )


class TestTheGate:
    def test_an_unmoved_row_is_left_alone(self):
        """The whole reason this is affordable.

        Holds run at roughly 0.26 per run; a refresh that wrote
        unconditionally would still be bounded by that, but the number a
        run reports would stop meaning "a standing sentence was
        corrected" and start meaning "a judgement was held".
        """
        row = _row()
        assert (
            BaseAgent.refresh_alert(
                row,
                message="VRAM at 90.1% (threshold: 90%)",
                details={"card": "card1", "vram_percent": 90.1},
            )
            is False
        )

    def test_a_moved_message_is_written(self):
        row = _row()
        assert BaseAgent.refresh_alert(
            row,
            message="VRAM at 51.0% (threshold: 90%)",
            details={"card": "card1", "vram_percent": 51.0},
        )
        assert row.message == "VRAM at 51.0% (threshold: 90%)"
        assert row.details["vram_percent"] == 51.0

    def test_a_moved_blob_is_written_even_when_the_sentence_is_identical(self):
        """``details`` is not decoration on the sentence.

        The drive that demonstrated the mechanism found the ports
        family's ``findings`` blob still naming a unit that had let the
        port go — so a fix moving only ``message`` leaves half the row
        lying, and the gate has to read both.
        """
        row = _row(message="8100 is contested", details={"holder": "user:alpha.service"})
        assert BaseAgent.refresh_alert(
            row, message="8100 is contested", details={"holder": "user:beta.service"}
        )
        assert row.details == {"holder": "user:beta.service"}


class TestTheComparisonModelsWhatWasStored:
    def test_a_tuple_that_round_trips_to_a_list_is_not_a_difference(self):
        """The rule that keeps the gate from degenerating into "always".

        ``JSONB`` has no tuple.  A caller that builds ``details`` with one
        gets a *list* back on the next run, so a plain ``!=`` reports a
        difference no write can ever settle and every held poll rewrites
        the row for ever — the gate switched off by a type, with the
        counter reporting corrections that corrected nothing.

        Falsified by comparing ``details or {}`` directly, which returns
        ``True`` here.
        """
        row = _row(details={"kinds": ["wrong_unit"]})
        assert (
            BaseAgent.refresh_alert(row, message=row.message, details={"kinds": ("wrong_unit",)})
            is False
        )

    def test_key_order_is_not_a_difference(self):
        row = _row(details={"a": 1, "b": 2})
        assert BaseAgent.refresh_alert(row, message=row.message, details={"b": 2, "a": 1}) is False

    def test_an_absent_blob_and_an_empty_one_are_the_same_row(self):
        """``details`` is ``NOT NULL`` with a ``'{}'`` default in the table.

        A row read back before its default has been applied carries
        ``None`` in Python, and treating that as different from ``{}``
        would rewrite it once per process for no change at all.
        """
        row = _row(details=None)
        row.details = None
        assert BaseAgent.refresh_alert(row, message=row.message, details={}) is False


class TestWhatIsStored:
    def test_the_callers_dict_is_stored_not_the_normalised_copy(self):
        """A raise and a refresh handed one input must write one row.

        The normalisation exists to answer a question — has this moved —
        and laundering the value through it would make a row's contents
        depend on which path happened to write it.
        """
        details = {"card": "card1", "vram_percent": 51.0}
        row = _row()
        assert BaseAgent.refresh_alert(row, message="moved", details=details)
        assert row.details is details

    def test_the_blob_is_reassigned_rather_than_mutated(self):
        """``_record_recurrence``'s rule, and this family had to learn it too.

        SQLAlchemy does not track mutation inside a plain ``JSONB`` dict,
        so an in-place update looks like it worked and writes nothing.
        """
        original = {"card": "card1", "vram_percent": 90.1}
        row = _row(details=original)
        assert BaseAgent.refresh_alert(row, message="moved", details={"card": "card1"})
        assert original == {"card": "card1", "vram_percent": 90.1}
        assert row.details is not original

    def test_a_caller_that_names_no_rung_touches_neither_severity_nor_title(self):
        """Session 39's ban, which the text-only call does not go near.

        An in-place *severity* change keeps a ``{severity}:{title}``
        fingerprint the tray has already suppressed, so an escalation is
        recorded and never spoken.  A message change is invisible to that
        fingerprint — which is what makes it safe, and equally what makes
        it silent.

        Narrowed on 2026-08-28 rather than deleted: ``SNAG-ESTATE-010``
        gives the method an optional ``severity``, and this test asserted
        the absence of the whole capability.  What survives is the claim
        it was always making — a caller that names no rung moves none —
        and the title stays untouchable either way, because it is the
        identity.
        """
        row = _row()
        before = (row.severity, row.title, row.resolved)
        BaseAgent.refresh_alert(row, message="moved", details={"card": "card2"})
        assert (row.severity, row.title, row.resolved) == before


class TestTheRungMovesOneWay:
    """``SNAG-ESTATE-010``'s surviving half, at the primitive.

    The predicate itself is pinned in ``tests/test_escalation.py``; what
    is asserted here is that this method asks it, obeys it, and — the
    part that would have shipped green and inert — asks it on a call
    whose text has not moved at all.
    """

    def test_a_quietening_is_written(self):
        row = _row()
        assert (
            BaseAgent.refresh_alert(
                row, message="moved", details={"card": "card2"}, severity="info"
            )
            is True
        )
        assert row.severity == "info"

    def test_a_quietening_lands_even_when_the_sentence_has_not_moved(self):
        """The founding case, and the one a naive gate order misses.

        The estate republishes the same breach every hour, so the
        recomputed message and blob are word-for-word what the standing
        row already says and only the rung moved.  A fix that asked
        "has the text changed" first would have returned ``False`` here,
        left the row loud, and passed every other test in this file.
        """
        row = _row()
        assert (
            BaseAgent.refresh_alert(
                row,
                message=row.message,
                details=dict(row.details),
                severity="info",
            )
            is True
        )
        assert row.severity == "info"

    def test_an_escalation_is_refused(self):
        """Session 39's ban, arriving through the new parameter.

        The row is left at ``warning`` and the *text* still moves — the
        two decisions are independent, and refusing the rung must not
        also refuse the correction.
        """
        row = _row()
        assert (
            BaseAgent.refresh_alert(
                row, message="moved", details={"card": "card2"}, severity="critical"
            )
            is True
        )
        assert row.severity == "warning"
        assert row.message == "moved"

    def test_an_escalation_alone_writes_nothing(self):
        row = _row()
        assert (
            BaseAgent.refresh_alert(
                row,
                message=row.message,
                details=dict(row.details),
                severity="critical",
            )
            is False
        )
        assert row.severity == "warning"

    def test_a_fall_that_stops_short_of_the_floor_is_refused(self):
        """A ``critical`` row recomputed ``warning`` stays ``critical``.

        Not an oversight and not the same question as a quietening: the
        fault has not improved, and ``warning:title`` is a fingerprint
        the tray *will* speak, so the write would arrive as a fresh, less
        urgent toast about a live fault — ``step_for``'s own refusal.
        """
        row = _row()
        row.severity = "critical"
        BaseAgent.refresh_alert(
            row, message="moved", details={"card": "card2"}, severity="warning"
        )
        assert row.severity == "critical"

    def test_the_title_is_still_untouchable(self):
        """Whatever the rung does.  It is the identity — Session 42."""
        row = _row()
        before = row.title
        BaseAgent.refresh_alert(
            row, message="moved", details={"card": "card2"}, severity="info"
        )
        assert row.title == before
