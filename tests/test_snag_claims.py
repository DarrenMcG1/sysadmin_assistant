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

import ast
import json
import re
import shutil
import tempfile
from hashlib import blake2s
from pathlib import Path
from unittest.mock import patch

import pytest

import sysadmin.snag_claims as snag_claims
from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.core.text import strip_markdown as real_strip_markdown
from sysadmin.monitor.journal import unwrap_json_message
from sysadmin.snag_claims import (
    CHECKS,
    DEPRECATED_MODULE,
    EXPECTED_ACTIVE_ALERTS_CALLS,
    EXPECTED_DISCARDED_RUNS,
    MAX_NAMED_ENTRIES,
    REVIEW_SCHEDULE_LEAVES,
    SNAG_PATH,
    STRIP_SPECIMEN,
    STRIPPER_FORMS,
    STRIPPER_NAME,
    STRIPPER_PROBE,
    UNWRAP_READER,
    Check,
    Measurement,
    call_sites,
    check_active_alerts_reads,
    check_all,
    check_capped_signature_collides,
    check_code_spans_survive,
    check_convention,
    check_deprecated_contracts,
    check_dropin_blind_spot,
    check_estate_port_8500,
    check_manual_run_unawaited,
    check_review_schedule_unread,
    check_run_status_cancelled,
    check_sysd_ollama_ordering,
    check_unwrap_is_read_time,
    closure_declared,
    discarded_tasks,
    envelope_message,
    load_entries,
    main,
    method_calls,
    overall,
    probe_signatures,
    read_entries,
    record_identity,
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


def _marker(text: str) -> str:
    """A stand-in disambiguator that is stable across processes.

    ``SNAG-TEST-001``.  The three falsification tests in
    :class:`TestChecksAgainstTheLiveBox` patch in a hypothetical fix whose
    entire job is to render two signatures that agree past the cap
    *apart*, so the stand-in has to separate the probe pair — and it was
    written as ``hash(text) % 997``, which does so only by luck.  CPython
    seeds ``str`` hashing from ``PYTHONHASHSEED``, so the value is stable
    within a process and different between them: the pair collides in
    about **one run in 997**, all three guards fail together having
    measured the stand-in rather than the check, and the next run is green
    with nothing changed.  Measured rather than reasoned about — 19
    collisions over 20,000 seeds, and ``PYTHONHASHSEED=282`` reproduces
    the original ``3 failed, 104 passed`` exactly.

    Note what could not have found it.  The entry excluded both obvious
    causes by reading the path, correctly: the probe is pure and there is
    no randomising plugin.  The secret is read before the interpreter
    imports anything, so it is upstream of the path being read.

    ``blake2s`` is the same short marker with the randomisation removed.
    Whether the pair separates becomes a property of the text alone, which
    is a fact this file asserts in
    :meth:`TestTheStandInDisambiguator.test_it_separates_the_probe_pair`
    rather than a probability it has to live with.
    """
    return blake2s(text.encode(), digest_size=4).hexdigest()


# ---------------------------------------------------------------------------
# Reading the document
# ---------------------------------------------------------------------------


class TestReadingEntries:
    def test_only_open_sections_are_read(self):
        """``## Fixed Issues`` and the template section are both excluded.

        Two different exclusions and both are live in the real file: a
        closed heading holds 45 of this document's 69 entries, and the
        template section holds a worked example whose id would otherwise
        be swept as a real open entry.

        *Re-measured 2026-08-26 by Session 91: 43 of 67 was stale by two,
        and the instrument moved rather than the document — the reader
        became ``estate.snags`` in estate-lib at 17:06:27 that day, after
        the previous sitting's commit, and now reads the two ``### Session
        NN write-up`` headings under ``## Fixed Issues`` as entries.  Both
        come back ``is_open`` ``False``, which is why the open count never
        moved and why this drift stayed invisible: the figure the board
        publishes was right throughout.  Note what cannot be checked — the
        old reader is gone from the box, so what any past sitting actually
        measured is unrecoverable, and driving today's reader over past
        commits answers a question about the instrument instead.*
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
        assert not snag_claims.attribute_reads(REVIEW_SCHEDULE_LEAVES, (REPO_ROOT / "sysadmin",))

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

    def test_call_sites_name_the_enclosing_function_and_take_the_innermost(self):
        """The half a count of call sites cannot supply.

        ``SNAG-LOG-008`` is not about *how many* callers the unwrap has —
        it is about *where* the one caller is.  A backfill that replaced
        the read-time call rather than adding to it leaves the count at
        one and moves the mechanism, so the enclosing name is the field
        the verdict reads.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(
                "unwrap_json_message(boot)\n"
                "def read_journal():\n"
                "    return unwrap_json_message(line)\n"
                "def outer():\n"
                "    def inner():\n"
                "        return unwrap_json_message(line)\n"
                "    return inner\n",
                encoding="utf-8",
            )
            found = call_sites("unwrap_json_message", (path,))
        assert [(where.rsplit("/", 1)[-1], enclosing) for where, enclosing in found] == [
            ("m.py:1", "<module>"),
            ("m.py:3", "read_journal"),
            ("m.py:6", "inner"),
        ]

    def test_call_sites_see_both_import_styles(self):
        """A backfill is not absent because whoever wrote it imported the module.

        ``from … import unwrap_json_message`` and ``journal.unwrap_json_message``
        are one call site under two spellings, and a check that saw only
        the bare name would report the entry unchanged against a fix it
        was looking straight at.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "m.py"
            path.write_text(
                "def backfill():\n"
                "    a = unwrap_json_message(x)\n"
                "    b = journal.unwrap_json_message(x)\n"
                "    return a, b\n",
                encoding="utf-8",
            )
            assert len(call_sites("unwrap_json_message", (path,))) == 2


# ---------------------------------------------------------------------------
# The eight checks, each falsified against the behaviour it detects
# ---------------------------------------------------------------------------


class TestTheStandInDisambiguator:
    """``_marker`` is what the next class's three guards actually rest on.

    ``SNAG-TEST-001``: they rested on ``hash(s) % 997``, whose value is
    seeded per process, so they were red about once in 997 runs and said
    nothing about the check on the other 996.  A guard that is wrong at a
    rate nobody has measured is worth less than its green runs read.
    """

    def test_it_separates_the_probe_pair(self):
        """The property the three falsification guards assume, asserted.

        Each of them patches in a hypothetical fix built from ``_marker``
        and then asserts the check notices.  If the marker does not
        separate the probe pair there is no fix to notice, and all three
        report the entry *unrefuted* — a green check turning red with no
        edit behind it.  So the assumption is measured here once rather
        than gambled on three times.
        """
        from sysadmin.monitor.log_actions import SIGNATURE_DETAIL_CHARS

        first, second = probe_signatures(SIGNATURE_DETAIL_CHARS)
        assert first != second
        assert _marker(first) != _marker(second)

    def test_it_is_a_function_of_the_text_and_nothing_else(self):
        """Stability *within* a run was never the defect, so pin the rest.

        ``hash`` is stable within a process too — that is precisely why
        the loop the entry recommends does not find it, and why fifteen
        green runs proved nothing.  What has to hold is that two
        interpreters agree, which cannot be observed from inside one, so
        it is pinned as purity here and as a known digest below.
        """
        text = "a signature that agrees past the cap"
        assert _marker(text) == _marker(text)
        assert _marker(text) == blake2s(text.encode(), digest_size=4).hexdigest()
        assert _marker(text) != _marker(text + "!")

    def test_no_guard_here_reaches_for_the_randomised_builtin(self):
        """An AST sweep, because the docstrings above are full of the word.

        Scoped to this file rather than to ``tests/`` — a test of some
        type's ``__hash__`` is legitimate and this rule would forbid it —
        and this file is where the convention it protects is written down.
        The repo-wide population was measured before the fix and was
        exactly the three stand-ins replaced here.

        The failure mode being refused is silence: a fourth falsification
        reaching for the obvious short-identity builtin is green on the
        run that adds it and every run for weeks afterwards.
        """
        tree = ast.parse(Path(__file__).read_text())
        offenders = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "hash"
        ]
        assert offenders == [], (
            f"builtin hash() at lines {offenders}: its value is seeded per process "
            "(SNAG-TEST-001), so a stand-in built from it separates two strings only "
            "by luck — use _marker"
        )


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
        for expected, word in (
            (EXPECTED_ACTIVE_ALERTS_CALLS - 1, "more"),
            (EXPECTED_ACTIVE_ALERTS_CALLS + 1, "fewer"),
        ):
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
        with patch.object(log_actions, "capped_signature", lambda s: f"{real(s)} [{_marker(s)}]"):
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
            lambda s: f' — "{real(s)}" [{_marker(s)}]',
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
            patch.object(log_actions, "capped_signature", lambda s: f"{real(s)} [{_marker(s)}]"),
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
        marked = {(entry.snag_id, key) for entry in entries for key in entry.markers}
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
        live as well: the board reads 69 entries and 24 open either side
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


class TestTheNudgeWordingCheck:
    """``SNAG-ESTATE-002``'s check — the second with a cross-repo instrument.

    The registry's first such check closed its own entry one sitting after
    it was written, and it left three things behind that are exercised
    here rather than re-derived: the three verdicts, the coupling that
    would silently disarm a probe, and the fact that *not being able to
    run* is ``unknown`` and never a skip.

    The producer is stubbed rather than mocked out.  A stub package on
    disk driven by this interpreter exercises :func:`estate_probe`'s
    subprocess, its JSON contract and the verdict logic together — and it
    runs where estate-manager is not installed, which is CI.

    Every stub deliberately omits ``from __future__ import annotations``,
    which the real module has.  That makes ``dataclasses.fields(...).type``
    a type *object* here and a *string* over there, so the probe is driven
    against the annotation form it will not meet in production — the
    reverse of the usual fixture risk, and it is why ``filler_for`` reads
    both.
    """

    WORDING = (
        "    @property\n"
        "    def title(self):\n"
        '        return "Project " + str(self.project_name) + " next action idle"\n'
        "\n"
        "    @property\n"
        "    def message(self):\n"
        '        return "Unchanged for " + str(self.days) + " days"\n'
        "\n"
        "    @property\n"
        "    def details(self):\n"
        '        return {"project": self.project_name}\n'
    )

    def _stub(
        self,
        tmp_path: Path,
        *,
        properties: str | None = None,
        extra_fields: tuple[str, ...] = (),
        bare_route: bool = True,
    ) -> Path:
        """A minimal ``estate_service.projects`` holding the two modules."""
        pkg = tmp_path / "estate_service" / "projects"
        pkg.mkdir(parents=True)
        (tmp_path / "estate_service" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "__init__.py").write_text("", encoding="utf-8")

        fields = "".join(f"    {line}\n" for line in extra_fields)
        body = self.WORDING if properties is None else properties
        (pkg / "nudges.py").write_text(
            "from dataclasses import dataclass\n\n\n"
            "@dataclass(frozen=True)\n"
            "class Nudge:\n"
            "    project_name: str\n"
            "    days: int\n"
            "    at_window_edge: bool\n"
            f"{fields}\n"
            f"{body or '    pass\n'}",
            encoding="utf-8",
        )
        element = (
            "asdict(nudge)"
            if bare_route
            else '{**asdict(nudge), "title": nudge.title, "message": nudge.message}'
        )
        (pkg / "oversight.py").write_text(
            "from dataclasses import asdict\n\n\n"
            "def attention(items):\n"
            f"    due = [{element} for nudge in items]\n"
            '    return {"nudges": due}\n',
            encoding="utf-8",
        )
        return tmp_path

    def _drive(self, tmp_path, monkeypatch, **kwargs):
        import sys as _sys

        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", self._stub(tmp_path, **kwargs))
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", Path(_sys.executable))
        return snag_claims.check_nudge_wording_unpublished()

    # ── the claim holding ────────────────────────────────────────────

    def test_wording_computed_and_dropped_is_the_claim_holding(self, tmp_path, monkeypatch):
        """What the live producer does, and what Session 45 measured."""
        found = self._drive(tmp_path, monkeypatch)
        assert found.verdict == "match"
        assert "Nudge offers title, message, details" in found.detail[0]
        assert "'Project probe next action idle'" in found.detail[2], (
            "the specimen came back unfilled, so `filler_for` is reading only one of the "
            "two annotation forms — and the stub deliberately uses the other one"
        )

    # ── the three remedies the entry offers ──────────────────────────

    def test_wording_published_as_fields_is_a_candidate_for_closure(self, tmp_path, monkeypatch):
        """Remedy one: convert the properties.

        Also the test that the specimen adapts to a changed constructor.
        A probe holding its own copy of the field list would raise
        ``TypeError`` here and report ``unknown`` for ever — the removed
        ``SNAG-ROADMAP-001`` check's own defect, which is why the
        arguments come from ``dataclasses.fields``.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            properties="",
            extra_fields=("title: str", "message: str", "details: str"),
        )
        assert found.verdict == "mismatch"
        assert "reaches the wire" in found.note

    def test_a_producer_that_stops_computing_the_wording_is_refuted(self, tmp_path, monkeypatch):
        """Remedy three: delete the properties and the "one place" comment.

        A refutation rather than a failure to measure.  The entry's
        complaint is that both sides think they own the format and
        neither says so; a producer that has stopped claiming it has
        answered that, so ``unknown`` would be the wrong verdict and
        ``match`` a false one.
        """
        found = self._drive(tmp_path, monkeypatch, properties="")
        assert found.verdict == "mismatch"
        assert "no longer computes" in found.note

    def test_a_partial_fix_is_refuted_with_the_residue_named(self, tmp_path, monkeypatch):
        """The entry's own warning, made into a verdict.

        Its body says a fix converting ``title`` and ``message`` and
        stopping there "leaves the same defect one field over".  Reporting
        that as ``match`` hides the fix and reporting it as a clean
        refutation hides the residue, so it is a candidate for closure
        whose note names what is still dropped.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            properties=(
                "    @property\n"
                "    def details(self):\n"
                '        return {"project": self.project_name}\n'
            ),
            extra_fields=("title: str", "message: str"),
        )
        assert found.verdict == "mismatch"
        assert "title, message now reach the wire" in found.note
        assert "details still" in found.note

    def test_a_route_that_augments_the_payload_is_unknown(self, tmp_path, monkeypatch):
        """Remedy two is the one ``asdict`` cannot see, so it is not guessed.

        Augmenting beside the ``asdict`` call leaves the dataclass exactly
        as it is, so every other signal here reads "claim holding" while
        the wire carries the wording.  Answering ``match`` there is the
        trap the removed check spent its docstring on — measuring that a
        remedy is *absent from where you looked* rather than that the
        fault is gone.
        """
        found = self._drive(tmp_path, monkeypatch, bare_route=False)
        assert found.verdict == "unknown"
        assert "bare asdict()" in found.note

    # ── every way of not knowing ─────────────────────────────────────

    def test_an_absent_interpreter_is_unknown_and_never_a_skip(self, tmp_path, monkeypatch):
        """Rule 5, and the question the tenth check's sitting settled.

        A test may ``skip`` when estate-manager is not on the box —
        :class:`TestAgainstTheOwningParser` does, because it asserts two
        readers agree and has nothing to assert with one.  A *check*
        reports on a claim, so not being able to test it is the third
        verdict rather than a fourth thing.
        """
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", tmp_path / "nowhere" / "python")
        found = snag_claims.check_nudge_wording_unpublished()
        assert found.verdict == "unknown"
        assert "interpreter" in found.note

    def test_a_producer_that_will_not_import_is_unknown_naming_why(self, tmp_path, monkeypatch):
        """The state estate-manager's tree was actually in on 2026-08-25.

        A half-applied rename is neither a claim holding nor a claim
        refuted, and the sentence naming the import failure is what a
        sitting needs at that moment.
        """
        import sys as _sys

        pkg = tmp_path / "estate_service" / "projects"
        pkg.mkdir(parents=True)
        (tmp_path / "estate_service" / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "nudges.py").write_text("raise ImportError('half-applied')\n", encoding="utf-8")
        (pkg / "oversight.py").write_text("", encoding="utf-8")
        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", tmp_path)
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", Path(_sys.executable))
        found = snag_claims.check_nudge_wording_unpublished()
        assert found.verdict == "unknown"
        assert "would not import or run" in found.note

    # ── the coupling guard the last cross-repo check paid for ────────

    def test_the_probe_touches_nothing_private(self):
        """**The guard for the defect the tenth check's falsification found.**

        Its first draft called ``roadmap._first_meaningful`` to evidence
        the strip — a private helper whose *name* is what estate-manager's
        fix renamed — so driven at the real fix it reported ``unknown``
        and would have gone on reporting it for ever, structurally unable
        to witness the closure it exists to notice.  A check coupled to
        the implementation it measures is the shape of the bug it
        measures, and nothing else here would catch it coming back: the
        stubs above define only public names, so a probe reaching for a
        private one fails the same way against every fixture and reads as
        an environment problem.

        **Dunders are exempt and single underscores are not**, which is
        the rule stated precisely rather than the tenth check's blanket
        ``startswith("_")``.  That version passed only because its probe
        happened to touch none; this one reads ``exc.__class__.__name__``
        and ``annotation.__name__``, which are language protocol on
        stdlib objects and private to nobody.  What must never appear is
        a single-underscore name — the shape of ``_first_meaningful`` —
        or *any* attribute reached off the producer's own names, which is
        the stronger half and the one a blanket rule could not express.
        """
        import ast

        probe = snag_claims.NUDGE_PROBE.format(service="/x", wording=snag_claims.NUDGE_WORDING)
        tree = ast.parse(probe)
        attributes = [node for node in ast.walk(tree) if isinstance(node, ast.Attribute)]
        private = {
            node.attr
            for node in attributes
            if node.attr.startswith("_") and not node.attr.startswith("__")
        }
        assert private == set(), "the probe reaches for a private symbol"

        producer = {"nudges", "oversight"}
        reached = {
            node.attr
            for node in attributes
            if isinstance(node.value, ast.Name)
            and node.value.id in producer
            and node.attr.startswith("_")
        }
        assert reached == set(), f"the probe reaches into the producer: {sorted(reached)}"

    def test_the_probe_names_no_field_of_its_own(self):
        """The other half of the same lesson, stated positively.

        The specimen's arguments must come from the producer's dataclass.
        A field name written into the probe is a second statement of a
        signature estate-manager owns, and the day they change it this
        check reports ``unknown`` for ever instead of the closure it
        exists to notice.
        """
        probe = snag_claims.NUDGE_PROBE.format(service="/x", wording=snag_claims.NUDGE_WORDING)
        assert "dataclasses.fields" in probe
        for field_name in ("project_name", "next_action", "at_window_edge", "threshold"):
            assert field_name not in probe, f"the probe names {field_name} itself"


class TestTheUnwrapCheck:
    """``SNAG-LOG-008``'s check — the registry's clearest case for rule 1.

    The entry's population is ten stored rows from one ten-minute window
    on 2026-08-17.  They left ``GET /api/logs/trends``' seven-day window
    on 2026-08-24 with nothing fixed and the purge takes the rows at
    thirty days, so a check that counted them would report the entry
    refuted by the calendar.  What is reproduced instead is the
    mechanism, in the two halves a fix could land in — and only the
    second of them can move, which is why the reproduction alone would
    have been a check that can only ever say *match*.
    """

    #: One journald record, spelled two ways.  ``journalctl -o json``
    #: does not emit a record's fields in a stable order, so these are
    #: the same record as two different lines — which is the fact that
    #: broke this check's first draft and is pinned below.
    RECORD = {
        "__REALTIME_TIMESTAMP": "1787846400000000",
        "__CURSOR": "s=abc;i=1",
        "MESSAGE": '{"timestamp": "2026-08-26 14:00:00,000", "level": "ERROR",'
        ' "logger": "sysadmin.core.agent", "message": "alert_raised"}',
        "_PID": "9999",
    }

    def _line(self, order: tuple[str, ...], **overrides: str) -> str:
        record = {**self.RECORD, **overrides}
        return json.dumps({key: record[key] for key in order})

    ORDER_A = ("__REALTIME_TIMESTAMP", "__CURSOR", "MESSAGE", "_PID")
    ORDER_B = ("_PID", "MESSAGE", "__CURSOR", "__REALTIME_TIMESTAMP")

    # -- the identity ----------------------------------------------------

    def test_identity_survives_the_field_order_that_broke_the_first_draft(self):
        """The one thing about this check only a live run could supply.

        The draft paired the two reads on ``raw_line`` and argued for it
        from the code under test: ``unwrap_json_message``'s rule 3
        promises that field is kept *verbatim*, so the guarantee comes
        from the thing being measured.  Driven at the real journal it
        paired **0 of 50** records, because the promise is about the
        record's content and not about its bytes.
        """
        first, second = self._line(self.ORDER_A), self._line(self.ORDER_B)
        assert first != second, "the two spellings must differ, or this pins nothing"
        assert record_identity(first) == record_identity(second)

    def test_identity_separates_records_sharing_a_millisecond(self):
        """A timestamp alone is not a key for this source.

        The eight ``alert_raised`` rows behind ``SNAG-LOG-008`` were
        ingested inside 1.7 ms of one another, so pairing on the instant
        would fold them into each other and the probe would compare a
        record against a different one.
        """
        same_instant = self._line(self.ORDER_A, MESSAGE='{"message": "a second fault"}')
        assert record_identity(self._line(self.ORDER_A)) != record_identity(same_instant)

    @pytest.mark.parametrize(
        "line",
        [
            "not json at all",
            "[1, 2, 3]",
            '{"MESSAGE": "no timestamp"}',
            '{"__REALTIME_TIMESTAMP": "1787846400000000"}',
            '{"__REALTIME_TIMESTAMP": "1", "MESSAGE": [72, 105]}',
        ],
    )
    def test_a_record_it_cannot_key_is_dropped_rather_than_guessed(self, line):
        """A truncated or byte-valued record leaves the population.

        ``raw_line`` is capped at 2000 characters and the field order
        that broke the draft decides what falls outside the cap, so a
        record whose key is not in the stored line is a real shape here.
        Dropping it costs the probe one record; keying it on a guess
        would pair two different records and report on neither.
        """
        assert record_identity(line) is None

    # -- the population --------------------------------------------------

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ('{"message": "alert_raised"}', "alert_raised"),
            ("Failed to start SportsAnalyser - Frontend (Next.js).", None),
            ("{not json", None),
            ('["a", "b"]', None),
            ('{"level": "ERROR"}', None),
            ('{"message": ""}', None),
            ('{"message": 3}', None),
        ],
    )
    def test_envelope_message_reads_only_a_real_envelope(self, raw, expected):
        assert envelope_message(raw) == expected

    def test_the_second_implementation_agrees_with_the_one_under_test(self):
        """``envelope_message`` is a copy, so it is pinned rather than trusted.

        It exists because deciding the population with
        :func:`~sysadmin.monitor.journal.unwrap_json_message` would make
        the probe agree with the code under test by construction — the
        defect :mod:`sysadmin.ops_claims` rule 3 recorded one day before
        this was written, where a pin searched a region containing its
        own marker.  A copy that can never disagree is worth nothing, so
        what is asserted is that the two answer the same question the
        same way today, over the shapes the real journal holds — the
        ``syslog_priority`` against ``PRIORITY_MAP`` treatment.
        """
        shapes = [
            '{"message": "alert_raised", "logger": "sysadmin.core.agent"}',
            "Failed to start SportsAnalyser - Frontend (Next.js).",
            "{not json",
            '["a"]',
            '{"level": "ERROR"}',
            '{"message": ""}',
            '{"message": 3}',
        ]
        for shape in shapes:
            unwrapped, _ = unwrap_json_message(shape)
            mine = envelope_message(shape)
            assert (mine is not None) == (unwrapped != shape), shape
            if mine is not None:
                assert mine == unwrapped, shape

    # -- the verdicts ----------------------------------------------------

    def test_the_check_holds_on_this_box(self):
        """The reproduction, driven at the real journal through the real reader."""
        if shutil.which("journalctl") is None:
            pytest.skip("journalctl is not on this box")
        measurement = check_unwrap_is_read_time()
        if measurement.verdict == "unknown":
            pytest.skip(f"the probe could not measure: {measurement.note}")
        assert measurement.verdict == "match"
        assert any("shaped differently by the declaration" in line for line in measurement.detail)
        assert any(f"in {UNWRAP_READER}()" in line for line in measurement.detail)

    def test_a_reader_that_ignores_the_declaration_is_a_mismatch(self):
        """The half the reproduction can refute: shape stops depending on the read."""
        agreed = [("alert_raised", "{...}", "{...}")]
        with patch.object(snag_claims, "read_at_both_declarations", return_value=(agreed, "")):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "mismatch"
        assert "no longer shapes a record by the source's declaration" in measurement.note

    def test_a_second_call_site_is_a_mismatch_without_reading_the_journal(self):
        """Where a backfill lands, and the order the two halves are settled in.

        The call-site half needs no subprocess, so it is decided first —
        a box where journalctl will not answer still reports a landed
        backfill rather than an ``unknown`` that hides one.  The journal
        read is asserted *not* to have happened, because "it also
        happened to be right" is what a call-count cannot tell from "it
        was decided here".
        """
        sites = [
            ("sysadmin/monitor/journal.py:349", UNWRAP_READER),
            ("alembic/versions/017_backfill_json_messages.py:22", "upgrade"),
        ]
        with (
            patch.object(snag_claims, "call_sites", return_value=sites),
            patch.object(snag_claims, "read_at_both_declarations") as read,
        ):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "mismatch"
        assert "017_backfill_json_messages.py:22 in upgrade()" in measurement.note
        assert not read.called

    def test_the_unwrap_moving_out_of_the_reader_is_a_mismatch(self):
        """A fix that *relocates* the call leaves the count at one.

        This is the reason the instrument reports the enclosing function
        rather than a line: an unwrap that moved to a query path serves
        the ten rows unwrapped without touching them, which answers the
        entry, and a check counting call sites would see no change at all.
        """
        with patch.object(
            snag_claims, "call_sites", return_value=[("sysadmin/monitor/log_query.py:88", "recent")]
        ):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "mismatch"
        assert "recent()" in measurement.note

    def test_a_renamed_unwrap_is_unknown_and_never_a_match(self):
        with patch.object(snag_claims, "call_sites", return_value=[]):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "unknown"
        assert "renamed or inlined" in measurement.note

    def test_a_journal_that_will_not_answer_is_unknown_and_never_a_match(self):
        with patch.object(
            snag_claims,
            "read_at_both_declarations",
            return_value=([], "either journalctl did not answer or the window held nothing"),
        ):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "unknown"
        assert measurement.detail, "the call-site evidence survives an unmeasurable read"

    def test_a_mixture_is_unknown_rather_than_a_partial_match(self):
        """Some records shaped and some not is a probe that stopped isolating.

        The reading it refuses is the tempting one — *most* records
        diverged, so the mechanism holds.  A reader that unwrapped only
        some records under a ``json`` declaration is a different
        mechanism from the one the entry describes, and reporting it as
        the entry's own would leave the residue unexplained.
        """
        mixed = [("a", "{...}", "a"), ("b", "{...}", "{...}")]
        with patch.object(snag_claims, "read_at_both_declarations", return_value=(mixed, "")):
            measurement = check_unwrap_is_read_time()
        assert measurement.verdict == "unknown"
        assert "reading a mixture" in measurement.note


class TestEstateModuleState:
    """Which tree the verdict was measured against — ``ports_checked``'s rule.

    A ``mismatch`` off a committed fix and one off an edit in flight have
    opposite remedies, and the sitting that wrote this needed the
    difference within the hour.
    """

    def test_a_clean_tree_reports_committed_and_says_it_is_not_deployed(self):
        """The distinction that closed ``SNAG-ROADMAP-001``.

        Their fix was committed at 22:42 and the daemon on 8400 had last
        started eleven hours earlier, so "committed" and "running" were
        demonstrably different facts.  The wording carries that rather
        than claiming the stronger one.
        """
        if not snag_claims.ESTATE_SERVICE.exists():
            pytest.skip("estate-manager is not beside this checkout")
        state = snag_claims.estate_module_state(snag_claims.ESTATE_NUDGE_MODULES)
        assert "could not be read" not in state
        if "uncommitted" not in state:
            assert "not the same as deployed" in state

    def test_an_unreadable_checkout_is_a_sentence_and_never_a_raise(self, tmp_path, monkeypatch):
        """Never a reason to fail — the evidence degrades, the check does not."""
        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", tmp_path / "nowhere")
        state = snag_claims.estate_module_state(snag_claims.ESTATE_NUDGE_MODULES)
        assert "could not be read" in state

    def test_naming_no_module_is_reported_rather_than_asked_of_git(self, monkeypatch):
        """An empty tuple would make ``git status`` answer for the whole tree.

        That reads "uncommitted" off any unrelated edit over there, which
        is a confident wrong answer where a sentence is the honest one.
        """
        state = snag_claims.estate_module_state(())
        assert "no estate-manager module was named" in state


class TestTheNudgeCheckAgainstTheRealProducer:
    """The live half, skipped rather than failed when they are not here.

    :class:`TestTheNudgeWordingCheck` drives stubs, which pin the verdict
    logic and can never notice the producer moving.  This one runs the
    real thing — the same split ``TestAgainstTheOwningParser`` makes, and
    the reason the tenth check caught estate-manager mid-edit at all.
    """

    def test_the_real_producer_yields_one_of_the_three_verdicts(self):
        if not snag_claims.ESTATE_PYTHON.exists():
            pytest.skip("estate-manager's venv is not on this box")
        found = snag_claims.check_nudge_wording_unpublished()
        assert found.verdict in set(EXIT_STATUS)
        assert any("estate-manager's" in line for line in found.detail), (
            "the verdict must carry which tree it was measured against"
        )


class TestTheCodeSpanCheck:
    """``SNAG-LOG-012``'s check — the first pre-staged against another repo's fix.

    The tenth and eleventh checks shell into estate-manager's venv to
    drive their code.  This one needs no cross-repo access at all:
    ``estate-lib`` is an *editable* install, so ``strip_markdown``
    resolves into their working tree and the check flips on the next run
    after they commit, with nothing synced and nobody told.

    The two candidate fixes are driven as **real patterns** rather than
    as literals saying "the fix landed", because the interesting verdict
    is the one that tells them apart: the naive ``` `[^`]+` ``` leaks a
    doubled fence and the same-length pattern does not, which is the
    distinction ``SNAG-DOCS-005`` closed on in this very module a day
    before this was written.
    """

    #: Where the library lives on this box.  Held still whenever the
    #: *behaviour* is being moved, so a test says which limb it is
    #: simulating — patching ``strip_markdown`` alone moves the resolved
    #: source file too, and would be simulating a local copy instead.
    LIBRARY = "/home/gaddi/projects/estate-manager/lib/estate/text.py"

    @staticmethod
    def _fixed(pattern: str):
        """``strip_markdown`` as it would read with a code-span pass added.

        The real function is bound at definition rather than looked up
        on the module, because the module's name is the one being
        patched — the first draft recursed until the stack ran out.
        """

        def stripper(text: str) -> str:
            return real_strip_markdown(re.sub(pattern, lambda m: m.group(0).strip("`"), text))

        return stripper

    def _with(self, stripper):
        return (
            patch.object(snag_claims, "strip_markdown", stripper),
            patch.object(snag_claims, "stripper_implementation", return_value=self.LIBRARY),
        )

    # -- the specimen ----------------------------------------------------

    def test_every_form_is_visible_in_its_own_specimen_line(self):
        """A probe whose token is absent from its own line pins nothing.

        Each form claims that a token makes it visible; if the token is
        not in the line to begin with, the form reads as "stripped"
        whatever the stripper does, and the check quietly stops
        measuring it.
        """
        for form in STRIPPER_FORMS:
            assert form.token in form.line, form.label

    def test_the_specimen_is_the_forms_and_not_a_second_copy(self):
        assert STRIP_SPECIMEN.split("\n") == [form.line for form in STRIPPER_FORMS]

    def test_the_entrys_own_driven_literal_still_reads_as_the_entry_records(self):
        """The document's recorded measurement, re-driven.

        ``SNAG-LOG-012``'s symptom bullet quotes a literal and its
        result — bold removed, backticks kept, a mid-line ``#`` kept.
        That is a claim in the document like any other, so it is pinned
        against the box rather than trusted.
        """
        assert (
            snag_claims.strip_markdown("a `code` and **bold** and # head")
            == "a `code` and bold and # head"
        )

    def test_the_controls_are_forms_the_library_really_strips(self):
        """The controls carry the whole weight of the subject's verdict.

        A control that the library never stripped would be a control
        that can only fire the ``unknown`` branch, which would make the
        check unable to reach ``match`` at all.
        """
        left, problem = snag_claims.strip_forms()
        assert not problem
        for form in STRIPPER_FORMS:
            assert (form.token in left[form.label]) is form.survives, form.label

    # -- the verdicts ----------------------------------------------------

    def test_the_check_holds_on_this_box(self):
        measurement = check_code_spans_survive()
        assert measurement.verdict == "match"
        assert any("estate-manager" in line for line in measurement.detail)
        assert any("generate_review()" in line for line in measurement.detail)

    def test_the_same_length_fix_is_a_clean_mismatch(self):
        """The fix the entry recommends, driven as the pattern it would be."""
        stripper, source = self._with(self._fixed(r"(`+)[\s\S]*?\1"))
        with stripper, source:
            measurement = check_code_spans_survive()
        assert measurement.verdict == "mismatch"
        assert "landed the fix this entry recommends" in measurement.note
        assert "doubled code fence" in measurement.note

    def test_the_naive_fix_is_a_mismatch_that_names_the_residue(self):
        """The partial state, and the one this repository already refused.

        Reported as ``mismatch`` and not as ``match``, because backticks
        *do* still reach the briefing — the entry's headline is intact —
        and the note has to say the library took the fix
        ``SNAG-DOCS-005`` rejected rather than leave the judging sitting
        to discover it.
        """
        stripper, source = self._with(self._fixed(r"`[^`]+`"))
        with stripper, source:
            measurement = check_code_spans_survive()
        assert measurement.verdict == "mismatch"
        assert "a partial fix" in measurement.note
        assert "SNAG-DOCS-005" in measurement.note
        assert "doubled code fence" in measurement.note

    def test_a_stripper_that_strips_nothing_is_unknown_and_never_a_match(self):
        """The reading the controls exist to refuse.

        ``"`" in strip_markdown("a `x`")`` is ``True`` for the identity
        function, so the obvious probe reports this entry holding
        against a ``strip_markdown`` that has stopped working entirely —
        a much larger fault served as evidence for a P3.
        """
        stripper, source = self._with(lambda text: text)
        with stripper, source:
            measurement = check_code_spans_survive()
        assert measurement.verdict == "unknown"
        assert "the controls are what make a surviving backtick mean something" in measurement.note

    def test_a_reflowing_stripper_is_unknown(self):
        """The line pairing is the instrument, so losing it is unknown."""
        stripper, source = self._with(lambda text: text.replace("\n", " "))
        with stripper, source:
            measurement = check_code_spans_survive()
        assert measurement.verdict == "unknown"
        assert "no longer maps a line to a line" in measurement.note

    def test_a_copy_landing_here_is_a_mismatch_on_the_delegation_limb(self):
        """The entry's "not ours to fix" moving, and only that.

        ``mismatch`` rather than ``unknown`` because it is a measurement
        and not a failure to measure — but the headline claim is
        untouched, so the note says which limb moved rather than letting
        a judging sitting read it as the behaviour changing.
        """
        local = str(REPO_ROOT / "sysadmin" / "core" / "text.py")
        with patch.object(snag_claims, "stripper_implementation", return_value=local):
            measurement = check_code_spans_survive()
        assert measurement.verdict == "mismatch"
        assert "inside this repository" in measurement.note
        assert "the delegation limb alone" in measurement.note

    def test_an_unresolvable_implementation_is_unknown_and_never_a_match(self):
        with patch.object(snag_claims, "stripper_implementation", return_value=None):
            measurement = check_code_spans_survive()
        assert measurement.verdict == "unknown"
        assert "whose implementation" in measurement.note

    def test_nothing_calling_it_here_is_unknown_and_never_a_match(self):
        with patch.object(snag_claims, "call_sites", return_value=[]):
            measurement = check_code_spans_survive()
        assert measurement.verdict == "unknown"
        assert "no narrative is stripped at all here" in measurement.note

    # -- the probe counting itself ---------------------------------------

    def test_the_probe_is_excluded_from_its_own_consumer_count(self):
        """The defect the first live drive found, pinned from both sides.

        The check calls ``strip_markdown`` itself, so an unfiltered walk
        reported **five** callers where there are three — and made the
        "nothing calls it" limb above unreachable, since the probe
        guaranteed a non-zero count.  Asserting only the filtered side
        would let the exclusion be deleted silently, so the raw walk is
        asserted to still contain what the filter removes.
        """
        raw = call_sites(STRIPPER_NAME, (REPO_ROOT / "sysadmin",))
        assert [site for site, _ in raw if site.startswith(STRIPPER_PROBE)], (
            "the probe no longer calls strip_markdown, so the exclusion below "
            "is no longer doing anything and this test has stopped pinning it"
        )
        measurement = check_code_spans_survive()
        assert not any(STRIPPER_PROBE in line for line in measurement.detail)
        assert any("3 caller(s)" in line for line in measurement.detail)
