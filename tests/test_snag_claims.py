"""The open snag entries, measured against the box (SNAG-ESTATE-014).

``docs/roadmap/snag_list.md`` sets the agenda for what gets fixed, and
nothing had ever checked it.  Session 82 measured all thirty open entries
by hand and found **five dead on the box** — three of them ``P1``, three
fixed for between nine and thirteen days — which is ``SNAG-ESTATE-008``
one document over and at five times the size.

These tests pin the four things that make the machinery worth having, and
each is written against a way it could quietly stop working rather than
against a way it could crash:

* that a claim nobody measured is ``unknown`` rather than agreement, and
  that a check which *raises* cannot take the other seven down with it;
* that the marker and the check stay pinned to each other, since a
  copy-pasted body bullet is what comes apart first;
* that the closure rule under-reports rather than invents, because an
  entry wrongly read as closed leaves the sweep silently;
* and that the real document still parses, which is the failure mode of
  the whole convention — a reworded entry would otherwise retire its check
  with nothing said.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import sysadmin.snag_claims as snag_claims
from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.snag_claims import (
    CHECKS,
    DEPRECATED_MODULE,
    EXPECTED_ACTIVE_ALERTS_CALLS,
    EXPECTED_DISCARDED_RUNS,
    MAX_NAMED_ENTRIES,
    REVIEW_SCHEDULE_LEAVES,
    SNAG_PATH,
    Check,
    Measurement,
    check_active_alerts_reads,
    check_all,
    check_capped_signature_collides,
    check_convention,
    check_deprecated_contracts,
    check_dropin_blind_spot,
    check_estate_port_8500,
    check_manual_run_unawaited,
    check_review_schedule_unread,
    check_run_status_cancelled,
    check_sysd_ollama_ordering,
    closure_declared,
    discarded_tasks,
    load_entries,
    main,
    method_calls,
    overall,
    probe_signatures,
    read_entries,
    render,
    run_check,
    strip_code_spans,
    trailing_parenthetical,
)

DOCUMENT = """# Snag List

## Open Issues

- [P1] SNAG-FAKE-001: **something is broken** (2026-08-01)
  - **Symptom**: it is broken
  - **Check**: <!--check:fake_one--> `sysadmin-check-snags` — refuted when mended

- [P2] SNAG-FAKE-002: **something else** (2026-08-02, **fixed 2026-08-03**)
  - **Symptom**: it was broken

- [P3] SNAG-FAKE-003: **a third thing** (2026-08-04)
  - **Symptom**: no check names this one

## Fixed Issues

- [P1] SNAG-FAKE-004: **long gone** (2026-07-01)

## Creating New SNAGs

- [P1] SNAG-WEB-001: Brief description (YYYY-MM-DD)
"""


def _entries():
    return read_entries(DOCUMENT)


def _check(key="fake_one", snag="SNAG-FAKE-001", verdict="match"):
    return Check(key, snag, "a fake claim", lambda: Measurement(verdict))


# ---------------------------------------------------------------------------
# Reading the document
# ---------------------------------------------------------------------------


class TestReadingEntries:
    def test_only_open_sections_are_read(self):
        """``## Fixed Issues`` and the template section are both excluded.

        Two different exclusions and both are live in the real file: a
        closed heading holds 43 of this document's 67 entries, and the
        template section holds a worked example whose id would otherwise
        be swept as a real open entry.
        """
        ids = {entry.snag_id for entry in _entries()}
        assert ids == {"SNAG-FAKE-001", "SNAG-FAKE-002", "SNAG-FAKE-003"}

    def test_a_declared_closure_is_read_from_the_title(self):
        entries = {entry.snag_id: entry for entry in _entries()}
        assert entries["SNAG-FAKE-001"].is_open
        assert not entries["SNAG-FAKE-002"].is_open

    def test_closure_is_read_from_the_trailing_parenthetical_only(self):
        """``SNAG-AGENT-004``'s real title, which a whole-title search closes.

        *"26,270 alert rows … can never be **resolved** or purged"* was an
        open ``P1`` for thirteen days.  This is the falsification of the
        narrowing, driven at the live wording rather than a synthetic one.
        """
        title = (
            "- [P1] SNAG-AGENT-004: **26,270 alert rows for four services that no "
            "longer exist can never be resolved or purged** (2026-08-11)"
        )
        assert not closure_declared(title)

    def test_closure_must_open_a_clause(self):
        """``SNAG-DB-002``'s real title, the other side of the same narrowing.

        ``check half **fixed 2026-08-13**`` names a closure of *half* the
        entry, and the clause opens with "check".  Under-reporting is the
        stated direction: this entry stayed open in the board's reading
        for eleven days and that was documented drift, not a defect.
        """
        open_half = "- [P2] SNAG-DB-002: **stale collations** (2026-08-11, check half **fixed**)"
        closed = "- [P2] SNAG-DB-002: **stale collations** (2026-08-11, **fixed 2026-08-13**)"
        assert not closure_declared(open_half)
        assert closure_declared(closed)

    def test_a_title_with_no_parenthetical_is_open(self):
        assert trailing_parenthetical("- [P1] SNAG-X-1: a thing") is None
        assert not closure_declared("- [P1] SNAG-X-1: a thing")

    def test_nested_brackets_do_not_break_the_scan(self):
        """The real provenance brackets nest — ``(… (SNAG-ESTATE-008's …))``."""
        title = "- [P1] SNAG-X-1: a thing (2026-08-01, **fixed** (by Session 9))"
        assert closure_declared(title)


class TestQuotedMarkers:
    """A quoted marker is a quotation — the one rule only a live run gave.

    The first run of this module reported two checks nobody implements,
    ``helth`` and ``routes``, both *"named by ``SNAG-ESTATE-011``"* — an
    entry that names neither and merely discusses the convention.  This
    document is the one place on the box that writes *about* markers, so a
    marker syntax with no way to be quoted cannot be used in it.
    """

    def test_a_backticked_marker_is_not_a_marker(self):
        body = "  - `<!--check:routes-->` is not that, and `<!--check:helth-->` is a typo"
        entries = read_entries(f"## Open Issues\n\n- [P1] SNAG-X-1: a thing (2026-08-01)\n{body}\n")
        assert entries[0].markers == ()

    def test_the_same_marker_unquoted_is_read(self):
        """The falsification: identical text, backticks removed."""
        body = "  - <!--check:routes--> is a real marker here"
        entries = read_entries(f"## Open Issues\n\n- [P1] SNAG-X-1: a thing (2026-08-01)\n{body}\n")
        assert entries[0].markers == ("routes",)

    def test_strip_leaves_prose_around_the_span(self):
        assert "is not that" in strip_code_spans("`<!--check:routes-->` is not that")

    def test_a_doubled_fence_closes_on_a_run_of_its_own_length(self):
        """Markdown's rule, and the second thing only a live run gave.

        A span quoting a marker that itself contains backticks is written
        with a doubled fence.  A pattern closing on *any* backtick run
        stops at the inner single one and leaves the marker bare — which
        is what ``SNAG-DOCS-005``'s own body did to the check describing
        it, within a minute of being written.
        """
        body = "  - ``the `<!--check:routes-->` marker`` would register as a claim"
        entries = read_entries(f"## Open Issues\n\n- [P1] SNAG-X-1: a thing (2026-08-01)\n{body}\n")
        assert entries[0].markers == ()


# ---------------------------------------------------------------------------
# The convention
# ---------------------------------------------------------------------------


class TestConvention:
    def test_a_marker_naming_no_check_is_reported(self):
        findings = check_convention(_entries(), "")
        keys = {finding.key for finding in findings}
        assert "marker:fake_one" in keys

    def test_the_pin_fires_when_the_marker_sits_on_the_wrong_entry(self):
        """Rule 4.  A copy-pasted body bullet is what produces this."""
        with patch.dict(CHECKS, {"fake_one": _check(snag="SNAG-FAKE-003")}, clear=True):
            findings = check_convention(_entries(), "")
        pins = [f for f in findings if f.key == "pin:fake_one"]
        assert pins and "SNAG-FAKE-001" in pins[0].note

    def test_the_pin_is_silent_when_the_marker_sits_on_its_own_entry(self):
        """The falsification of the test above — same registry, right entry."""
        with patch.dict(CHECKS, {"fake_one": _check()}, clear=True):
            findings = check_convention(_entries(), "")
        assert not [f for f in findings if f.key.startswith("pin:")]

    def test_open_entries_with_no_check_are_counted_and_named(self):
        with patch.dict(CHECKS, {"fake_one": _check()}, clear=True):
            findings = check_convention(_entries(), "")
        unchecked = [f for f in findings if f.key == "convention:unchecked"][0]
        assert "1 of 2 open entries" in unchecked.note
        assert unchecked.detail == ("SNAG-FAKE-003",)

    def test_a_closed_entry_is_not_reported_unchecked(self):
        """``SNAG-FAKE-002`` declares its closure and must leave the population.

        The falsification is the count in the test above: 2 open, not 3.
        """
        with patch.dict(CHECKS, {"fake_one": _check()}, clear=True):
            findings = check_convention(_entries(), "")
        unchecked = [f for f in findings if f.key == "convention:unchecked"][0]
        assert "SNAG-FAKE-002" not in unchecked.detail

    def test_the_overflow_is_stated_rather_than_dropped(self):
        """``SNAG-ESTATE-001``'s rule — a roll-up that names nothing is the defect."""
        many = "## Open Issues\n\n" + "".join(
            f"- [P3] SNAG-MANY-{n:03d}: a thing (2026-08-01)\n  - body\n\n"
            for n in range(MAX_NAMED_ENTRIES + 4)
        )
        with patch.dict(CHECKS, {}, clear=True):
            findings = check_convention(read_entries(many), "")
        unchecked = [f for f in findings if f.key == "convention:unchecked"][0]
        assert len(unchecked.detail) == MAX_NAMED_ENTRIES + 1
        assert unchecked.detail[-1] == "… and 4 more"

    def test_an_unreadable_document_is_one_finding_and_not_silence(self):
        findings = check_convention([], "no such file")
        assert len(findings) == 1
        assert findings[0].verdict == "unknown"


# ---------------------------------------------------------------------------
# Verdicts
# ---------------------------------------------------------------------------


class TestVerdicts:
    def test_a_check_that_raises_is_unknown_and_does_not_stop_the_others(self):
        """Rule 5.  Letting it propagate hands the sitting no answer at all."""

        def boom() -> Measurement:
            raise RuntimeError("nope")

        finding = run_check(Check("boom", "SNAG-X-1", "a thing", boom))
        assert finding.verdict == "unknown"
        assert "RuntimeError" in finding.note

    def test_mismatch_outranks_unknown(self):
        """Not ``max()`` over EXIT_STATUS, which ranks 'never ran' above 'false'."""
        findings = [
            run_check(_check(verdict="unknown")),
            run_check(_check(verdict="mismatch")),
        ]
        assert overall(findings) == "mismatch"
        assert EXIT_STATUS[overall(findings)] == 1

    def test_unknown_outranks_match(self):
        findings = [run_check(_check(verdict="match")), run_check(_check(verdict="unknown"))]
        assert overall(findings) == "unknown"

    def test_a_holding_claim_renders_as_still_holds_not_as_agreement(self):
        """The polarity that inverts between this module and its sibling.

        A ``match`` in ``ops_claims`` is good news; here it means the bug
        is still real.  The word is what a reader sees, so it is pinned.
        """
        line = render([run_check(_check(verdict="match"))])[0]
        assert line.startswith("ok SNAG-FAKE-001")
        assert "still holds" in line

    def test_a_refuted_claim_renders_as_refuted(self):
        line = render([run_check(_check(verdict="mismatch"))])[0]
        assert line.startswith("no ")
        assert "refuted" in line


# ---------------------------------------------------------------------------
# The instruments
# ---------------------------------------------------------------------------


class TestInstruments:
    def test_attribute_reads_are_exact_and_a_substring_search_is_not(self):
        """Rule 7's founding measurement, driven at the real checkout.

        ``grep review_hour`` matches ``log_review_hour``,
        ``disk_review_hour`` and ``health_review_hour``, all of which are
        read — so a substring instrument reports ``SNAG-CFG-002`` refuted
        on its first run.  Pointing the AST walk at one of those leaves
        finds those readers; pointing it at the entry's own leaves finds
        none.  Same instrument, two questions, and only the exact one is
        right.
        """
        assert snag_claims.attribute_reads(
            frozenset({"log_review_hour"}), (REPO_ROOT / "sysadmin",)
        )
        assert not snag_claims.attribute_reads(
            REVIEW_SCHEDULE_LEAVES, (REPO_ROOT / "sysadmin",)
        )

    def test_method_calls_ignore_the_definition_and_the_docstring(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(
                'def _active_alerts(self):\n    """calls self._active_alerts once."""\n'
                "    # self._active_alerts()\n"
                "    return 1\n\n"
                "def caller(self):\n    return self._active_alerts()\n",
                encoding="utf-8",
            )
            assert method_calls(path, "_active_alerts") == [7]

    def test_discarded_tasks_exclude_a_task_whose_reference_is_kept(self):
        """The distinction ``SNAG-LOG-006`` turns on, and it is structural.

        ``sysadmin/core/event_bus.py`` calls ``create_task`` two lines
        under a comment explaining why it assigns the result.  A search
        for the call name cannot tell the two apart; an ``ast.Expr``
        wrapper *is* the discard.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(
                "import asyncio\n"
                "def a():\n    asyncio.create_task(agent.run(run_type='manual'))\n"
                "def b():\n    task = asyncio.create_task(agent.run(run_type='manual'))\n",
                encoding="utf-8",
            )
            assert discarded_tasks(path, "run") == [3]


# ---------------------------------------------------------------------------
# The eight checks, each falsified against the behaviour it detects
# ---------------------------------------------------------------------------


class TestChecksAgainstTheLiveBox:
    """Every check is driven at the real box, then at a box that moved.

    The second half is the point.  A check that only ever reports *match*
    against a claim that happens to hold is indistinguishable from a check
    that reports *match* unconditionally, which is how ``SNAG-DOCS-002``'s
    grep and Session 81's fix-word predictor both passed while measuring
    the wrong thing.
    """

    def test_sysd_ordering_holds_and_is_refuted_by_an_edited_after_line(self):
        assert check_sysd_ollama_ordering().verdict == "match"
        with tempfile.TemporaryDirectory() as tmp:
            unit = Path(tmp) / "sysadmin.service"
            unit.write_text("[Unit]\nAfter=network.target postgresql.service\n", encoding="utf-8")
            with patch.object(snag_claims, "SYSADMIN_UNIT", unit):
                measurement = check_sysd_ollama_ordering()
        assert measurement.verdict == "mismatch"
        assert "no longer names" in measurement.note

    def test_sysd_ordering_is_refuted_the_other_way_when_ollama_returns(self):
        """The two refutations are opposite and must not share a sentence.

        The line losing ``ollama.service`` is the fix; ``ollama.service``
        resolving again is the claim's premise dying while the line
        stands, and reporting a reinstalled Ollama as a job well done is
        the failure a single boolean would produce.
        """
        with patch.object(snag_claims, "unit_load_state", lambda unit: "loaded"):
            measurement = check_sysd_ollama_ordering()
        assert measurement.verdict == "mismatch"
        assert "rather than not-found" in measurement.note

    def test_sysd_ordering_is_unknown_when_systemd_will_not_answer(self):
        with patch.object(snag_claims, "unit_load_state", lambda unit: "unmeasured (OSError)"):
            assert check_sysd_ollama_ordering().verdict == "unknown"

    def test_run_status_holds_and_is_refuted_by_a_written_row(self):
        assert check_run_status_cancelled().verdict == "match"
        with patch.object(
            snag_claims, "query_one", side_effect=[("CHECK (… cancelled …)", ""), (3, "")]
        ):
            measurement = check_run_status_cancelled()
        assert measurement.verdict == "mismatch"
        assert "something writes it now" in measurement.note

    def test_run_status_is_refuted_the_other_way_by_a_dropped_value(self):
        """The entry's two fixes are opposite, so the check names which was taken."""
        with patch.object(
            snag_claims, "query_one", side_effect=[("CHECK (running, completed)", ""), (0, "")]
        ):
            measurement = check_run_status_cancelled()
        assert measurement.verdict == "mismatch"
        assert "no longer admits" in measurement.note

    def test_run_status_is_unknown_when_the_database_will_not_answer(self):
        silent = (None, "the database did not answer")
        with patch.object(snag_claims, "query_one", return_value=silent):
            assert check_run_status_cancelled().verdict == "unknown"

    def test_review_schedule_holds_and_is_refuted_by_a_reader(self):
        assert check_review_schedule_unread().verdict == "match"
        with patch.object(snag_claims, "REVIEW_SCHEDULE_LEAVES", frozenset({"log_review_hour"})):
            measurement = check_review_schedule_unread()
        assert measurement.verdict == "mismatch"
        assert "reader(s)" in measurement.note

    def test_active_alerts_holds_and_is_refuted_in_either_direction(self):
        assert check_active_alerts_reads().verdict == "match"
        for expected, word in ((EXPECTED_ACTIVE_ALERTS_CALLS - 1, "more"),
                               (EXPECTED_ACTIVE_ALERTS_CALLS + 1, "fewer")):
            with patch.object(snag_claims, "EXPECTED_ACTIVE_ALERTS_CALLS", expected):
                measurement = check_active_alerts_reads()
            assert measurement.verdict == "mismatch"
            assert word in measurement.note

    def test_manual_run_holds_and_is_refuted_when_a_task_is_kept(self):
        assert check_manual_run_unawaited().verdict == "match"
        with patch.object(snag_claims, "EXPECTED_DISCARDED_RUNS", EXPECTED_DISCARDED_RUNS - 1):
            assert check_manual_run_unawaited().verdict == "mismatch"

    def test_deprecated_contracts_holds_and_is_refuted_when_the_shim_goes(self):
        assert check_deprecated_contracts().verdict == "match"
        with patch.object(snag_claims, "DEPRECATED_MODULE", Path("/nonexistent/gone.py")):
            measurement = check_deprecated_contracts()
        assert measurement.verdict == "mismatch"
        assert "gone" in measurement.note

    def test_deprecated_contracts_is_refuted_when_a_name_is_trimmed(self):
        with tempfile.TemporaryDirectory() as tmp:
            shim = Path(tmp) / "_deprecated_contracts.py"
            shim.write_text("class RecommendationInfo:\n    pass\n", encoding="utf-8")
            with patch.object(snag_claims, "DEPRECATED_MODULE", shim):
                measurement = check_deprecated_contracts()
        assert measurement.verdict == "mismatch"
        assert "no longer defined" in measurement.note

    def test_estate_port_holds_and_is_refuted_when_the_row_is_edited(self):
        assert check_estate_port_8500().verdict == "match"
        with patch.object(snag_claims, "ESTATE_PORT_CLAIMANT", "sysadmin-assistant"):
            assert check_estate_port_8500().verdict == "mismatch"

    def test_estate_port_is_unknown_when_the_estate_document_is_absent(self):
        """A delegated entry's evidence lives in another repository.

        Unreachable is ``unknown`` and never ``match``: a checkout without
        estate-manager beside it knows less about the row, not that the
        row is fine.
        """
        with patch.object(snag_claims, "ESTATE_REGISTRY", Path("/nonexistent/guide.md")):
            assert check_estate_port_8500().verdict == "unknown"

    def test_dropin_blind_spot_is_reproduced_and_not_counted(self):
        """Rule 1, and the check that would have closed the wrong entry.

        ``SNAG-UNITS-006``'s population is measured **empty** on this box
        — zero of the 38 swept units carries a drop-in — so a check that
        looked for one would report the entry refuted on the day it was
        filed.  That is precisely the reading Session 83 refused for
        ``SNAG-LOG-013``.  What is reproduced instead is the mechanism: a
        synthetic unit whose drop-in overrides ``RestartSec=``, swept, and
        the parsed value compared against what the drop-in says.
        """
        assert check_dropin_blind_spot().verdict == "match"

    def test_dropin_blind_spot_is_refuted_by_a_sweep_that_reads_drop_ins(self):
        import sysadmin.units.scan as scan

        real = scan.discover_units

        def reads_dropins(user_dir, system_dir, home):
            units, excluded = real(user_dir, system_dir, home)
            return [
                type(unit)(**{**unit.__dict__, "restart_sec": 99.0}) for unit in units
            ], excluded

        with patch.object(scan, "discover_units", reads_dropins):
            measurement = check_dropin_blind_spot()
        assert measurement.verdict == "mismatch"
        assert "now reads drop-in directories" in measurement.note

    def test_capped_signature_collides_is_reproduced_and_not_counted(self):
        """Rule 1's second case, and the entry the rule was written for.

        ``SNAG-LOG-013``'s population is empty at the live endpoint — its
        own last bullet says the ten raw-JSON rows leave the seven-day
        window the afternoon it was filed — so a check that asked *does
        any pair collide today* would refute it for exactly the reason
        that mis-ranked its parent ``SNAG-LOG-010``.  What is driven
        instead is the mechanism, through the real ``recommend()``.
        """
        measurement = check_capped_signature_collides()
        assert measurement.verdict == "match"
        assert "roll-up member lines identical: True" in measurement.detail
        assert "separate rows' titles identical: True" in measurement.detail

    def test_raising_the_cap_is_not_read_as_a_fix(self):
        """The probe is derived from the constant, and this is why.

        The entry says in writing that raising the cap is not the fix —
        *any bound is defeated by two records that differ past it, and a
        larger number only moves where*.  A probe with a hard-coded
        prefix reports a fix the day somebody moves the constant, which
        would make this check argue against the entry it measures.
        """
        import sysadmin.monitor.log_actions as log_actions

        with patch.object(log_actions, "SIGNATURE_DETAIL_CHARS", 400):
            measurement = check_capped_signature_collides()
        assert measurement.verdict == "match"
        assert measurement.detail[0].startswith("cap 400;")

    def test_a_divergence_aware_cap_refutes_both_halves(self):
        """The entry's second candidate fix, landed everywhere.

        ``quoted_signature`` delegates to ``capped_signature``, so the two
        halves are **not** independent in this direction: one fix to the
        shared function closes both, and the note says so rather than
        naming a half.
        """
        import sysadmin.monitor.log_actions as log_actions

        real = log_actions.capped_signature
        with patch.object(
            log_actions, "capped_signature", lambda s: f"{real(s)} [{hash(s) % 997}]"
        ):
            measurement = check_capped_signature_collides()
        assert measurement.verdict == "mismatch"
        assert "neither half collides" in measurement.note

    def test_a_disambiguated_title_refutes_the_headline_half_alone(self):
        """A fix in ``quoted_signature`` closes the title clause only.

        The roll-up goes on naming none of its members, so the entry
        wants narrowing rather than closing — which is a judgement, and
        rule 2 is why the check states the direction and stops.
        """
        import sysadmin.monitor.log_actions as log_actions

        real = log_actions.capped_signature
        with patch.object(
            log_actions,
            "quoted_signature",
            lambda s: f' — "{real(s)}" [{hash(s) % 997}]',
        ):
            measurement = check_capped_signature_collides()
        assert measurement.verdict == "mismatch"
        assert "headline half is closed" in measurement.note
        assert "roll-up member lines identical: True" in measurement.detail

    def test_a_sibling_aware_roll_up_refutes_the_detail_half_alone(self):
        """The one shape that separates the halves is the entry's own fix.

        It proposes capping *from the first character at which the
        group's members diverge*, which needs the sibling set and so
        cannot live in the per-row pure function the titles are built
        from.  That is what this patch stands in for, and it is the only
        reason reporting the halves apart is worth the code.
        """
        import sysadmin.monitor.log_actions as log_actions

        real = log_actions.capped_signature
        with (
            patch.object(
                log_actions, "capped_signature", lambda s: f"{real(s)} [{hash(s) % 997}]"
            ),
            patch.object(log_actions, "quoted_signature", lambda s: f' — "{real(s)}"'),
        ):
            measurement = check_capped_signature_collides()
        assert measurement.verdict == "mismatch"
        assert "second candidate fix" in measurement.note
        assert "separate rows' titles identical: True" in measurement.detail

    def test_a_probe_that_is_never_truncated_is_unknown_not_refuted(self):
        """Rule 5, at the one input that would otherwise read as a fix.

        With the cap removed altogether the two signatures render apart —
        and not because anything learned to tell them apart.  The
        mechanism under test is gone, so there is nothing to measure, and
        ``unknown`` is the difference between *we looked* and *we could
        not*.
        """
        import sysadmin.monitor.log_actions as log_actions

        with patch.object(log_actions, "capped_signature", lambda s: s):
            measurement = check_capped_signature_collides()
        assert measurement.verdict == "unknown"
        assert "uncapped" in measurement.note

    def test_the_probe_isolates_the_signature_and_nothing_else(self):
        """The false negative the first draft of this check shipped with.

        Its ``apart`` half used two *different* sources, and the two
        titles came apart — ``_new_recommendation`` opens a title with the
        source name, so the fixture reported the claim refuted for a
        reason with nothing to do with the cap.  Measured here rather
        than asserted: the same pair, capped identically, yields one
        title from one source and two from two.
        """
        from datetime import UTC, datetime, timedelta

        from sysadmin.monitor.log_actions import (
            INCIDENT_WINDOW_SECONDS,
            SIGNATURE_DETAIL_CHARS,
            quoted_signature,
            recommend,
        )
        from sysadmin.monitor.log_trends import (
            ChangeKind,
            Confidence,
            LogTrendReport,
            SignatureTrend,
        )

        first, second = probe_signatures(SIGNATURE_DETAIL_CHARS)
        assert first != second
        assert quoted_signature(first) == quoted_signature(second)

        anchor = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

        def rows(second_source):
            pair = [
                SignatureTrend(
                    signature=signature,
                    alert_title="Log error: probe",
                    source=source,
                    severity="error",
                    sample=signature,
                    current=1,
                    previous=0,
                    total=1,
                    first_seen=anchor + timedelta(seconds=offset),
                    last_seen=anchor + timedelta(seconds=offset),
                    change=ChangeKind.NEW,
                )
                for signature, source, offset in (
                    (first, "one.service", 0.0),
                    (second, second_source, INCIDENT_WINDOW_SECONDS * 2),
                )
            ]
            return recommend(
                LogTrendReport(
                    window_days=7,
                    window_start=anchor - timedelta(days=7),
                    previous_start=anchor - timedelta(days=14),
                    generated_at=anchor,
                    confidence=Confidence.HIGH,
                    signatures=pair,
                )
            )

        same = rows("one.service")
        different = rows("two.service")
        assert same[0].title == same[1].title
        assert different[0].title != different[1].title

    def test_probe_signatures_agree_past_the_cap_at_any_cap(self):
        """The derivation, at three caps rather than at the live one.

        A probe that only agrees past *today's* constant is a hard-coded
        prefix with an extra step, so the property is asserted where it
        would fail if the arithmetic were wrong.
        """
        for cap in (40, 120, 400):
            first, second = probe_signatures(cap)
            assert first[:cap] == second[:cap]
            assert len(first) > cap
            assert first != second


# ---------------------------------------------------------------------------
# The real document
# ---------------------------------------------------------------------------


class TestTheRealDocument:
    """The failure mode of the whole convention lives here.

    A reworded entry, a renamed check or a body bullet lost to an edit all
    end the same way: the entry looks verified and is not.  These run
    against ``docs/roadmap/snag_list.md`` itself so that happens as a red
    test rather than as silence.
    """

    def test_the_real_snag_list_parses(self):
        entries, problem = load_entries()
        assert not problem
        assert entries

    def test_every_registered_check_is_named_by_its_own_entry(self):
        """Rule 4's pin, against the real file.

        Falsified while it was being written: before the eight markers
        were added, this reported all eight checks orphaned.
        """
        entries, _ = load_entries()
        marked = {
            (entry.snag_id, key) for entry in entries for key in entry.markers
        }
        missing = [
            f"{check.snag} does not carry <!--check:{key}-->"
            for key, check in CHECKS.items()
            if (check.snag, key) not in marked
        ]
        assert not missing, "\n".join(missing)

    def test_no_marker_in_the_real_file_names_a_check_nobody_implements(self):
        entries, _ = load_entries()
        named = {key for entry in entries for key in entry.markers}
        assert not named - set(CHECKS)

    def test_no_marker_reaches_an_entry_title(self):
        """Rule 3 — the title is estate-manager's input, not ours.

        ``read_snags`` takes the whole heading text and
        ``_trailing_parenthetical`` requires it to end in ``)`` before it
        will look for a closure clause, so a marker appended to a title
        changes what the board publishes about this repository.  Verified
        live as well: the board reads 67 entries and 24 open either side
        of this sitting's edit.
        """
        entries, _ = load_entries()
        assert not [entry for entry in entries if "<!--check:" in entry.title]

    def test_every_checked_entry_is_open(self):
        """A check outliving its entry is the other half of the pin.

        Closing an entry without removing its check leaves a claim being
        re-measured for ever with nobody reading the answer, which is the
        orphan side of ``SNAG-ESTATE-011``'s convention.
        """
        entries = {entry.snag_id: entry for entry in load_entries()[0]}
        closed = [
            check.snag
            for check in CHECKS.values()
            if check.snag in entries and not entries[check.snag].is_open
        ]
        assert not closed, f"checks name closed entries: {closed}"

    def test_the_deprecated_module_still_holds_the_five_names(self):
        """The one check whose constant is a list rather than a count."""
        assert DEPRECATED_MODULE.exists()

    def test_check_all_reports_every_registered_check(self):
        findings = check_all()
        assert {f.key for f in findings if f.kind == "claim"} == set(CHECKS)

    def test_main_exits_with_the_schema_guards_status_map(self):
        assert main([]) in set(EXIT_STATUS.values())

    def test_a_missing_document_still_runs_the_claims(self):
        """A missing snag list is a reason to know less about the entries.

        It is never a reason to stop measuring the claims — the split
        ``ops_claims.check_all`` makes for its state checks, here for the
        same reason.
        """
        findings = check_all(Path("/nonexistent/snag_list.md"))
        assert {f.key for f in findings if f.kind == "claim"} == set(CHECKS)
        assert any(f.key == "convention:document" for f in findings)


class TestAgainstTheOwningParser:
    """The open set is read here and pinned against estate-manager's.

    Rule 8.  ``read_snags`` lives in ``estate_service`` rather than in
    ``estate-lib``, so it cannot be imported and the closure rule above is
    a second implementation of somebody else's fact — the thing this
    repository refuses everywhere it can.  What is available instead is a
    pin: drive both readers over the real file and require the open sets
    to agree.  Skipped rather than failed when estate-manager is not
    beside this checkout, because that is a property of the box.
    """

    def _read_snags(self):
        service = Path.home() / "projects" / "estate-manager" / "service"
        if not (service / ".venv" / "bin" / "python").exists():
            pytest.skip("estate-manager's venv is not on this box")
        import subprocess

        script = (
            "import json, sys\n"
            f"sys.path.insert(0, {str(service)!r})\n"
            "from estate_service.projects.roadmap import read_snags\n"
            f"rows, fmt = read_snags(open({str(SNAG_PATH)!r}).read())\n"
            "print(json.dumps({'open': sorted(r.snag_id for r in rows if r.is_open),"
            " 'total': len(rows), 'format': fmt}))\n"
        )
        result = subprocess.run(
            [str(service / ".venv" / "bin" / "python"), "-c", script],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            pytest.skip(f"estate-manager's parser would not run: {result.stderr[-200:]}")
        import json

        return json.loads(result.stdout)

    def test_the_two_readers_agree_on_which_entries_are_open(self):
        theirs = self._read_snags()
        mine = sorted(
            entry.snag_id for entry in load_entries()[0] if entry.is_open and entry.snag_id
        )
        assert mine == theirs["open"]

    def test_the_markers_did_not_move_the_board(self):
        """Rule 3, measured rather than argued.

        The board publishes this repository's entries off the same parse.
        A marker in a body must move neither the dialect it detects nor
        the set it calls open, and this is what says so if the convention
        ever migrates into a title.

        Deliberately **not** ``total == 67``.  A count written into a test
        is a claim about a document that goes stale the next time anyone
        files an entry — which this sitting did twice, and which is
        ``SNAG-ESTATE-008``'s shape arriving inside the guard built to
        answer it.  What is pinned is the agreement between two readers,
        which no amount of filing can invalidate.
        """
        theirs = self._read_snags()
        assert theirs["format"] == "bullet"
        assert theirs["open"] == sorted(
            entry.snag_id for entry in load_entries()[0] if entry.is_open and entry.snag_id
        )
