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
import contextlib
import inspect
import json
import logging
import os
import re
import shutil
import socket
import tempfile
import textwrap
import time
from datetime import UTC, datetime
from hashlib import blake2s
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest

import sysadmin.ops_claims as ops_claims
import sysadmin.snag_claims as snag_claims
from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.core.text import strip_markdown as real_strip_markdown
from sysadmin.monitor.journal import unwrap_json_message
from sysadmin.ops_claims import check_expiry as real_check_expiry
from sysadmin.snag_claims import (
    CHECKS,
    DEPRECATED_MODULE,
    EXPECTED_ACTIVE_ALERTS_CALLS,
    EXPECTED_DISCARDED_RUNS,
    EXPIRY_PRODUCER_STAMP,
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
    check_expiry_naive_instant,
    check_health_path_guess,
    check_manual_run_unawaited,
    check_quietened_judgement_reach,
    check_review_schedule_unread,
    check_run_status_cancelled,
    check_sysd_ollama_ordering,
    check_unwrap_is_read_time,
    closure_declared,
    discarded_tasks,
    envelope_message,
    expiry_reading,
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

    Rule 8.  The closure rule above is a second implementation of somebody
    else's fact — the thing this repository refuses everywhere it can — so
    what is available instead is a pin: drive both readers over the real
    file and require the open sets to agree.

    **The instrument moved on 2026-08-26 and this pin skipped rather than
    failed**, which Session 93 found while measuring the entry count for a
    different sitting.  ``read_snags`` left ``estate_service`` for
    ``estate.snags`` in ``estate-lib`` (their commit ``a5c1834``), the
    subprocess raised ``ImportError``, and the ``returncode != 0`` branch
    read that as "their parser would not run" — a property of the box.  It
    was not: estate-manager was present, healthy and had simply published
    the function somewhere better.  So the whole class went quiet, the
    suite reported ``2 skipped`` and ``STATUS.md`` went on saying nothing
    skips here.

    Two rules come out of it, and the second is the one worth carrying:

    1. **The library is tried first, because it is now the public
       surface.**  ``estate-lib`` is an editable install, so
       ``estate.snags`` resolves into their working tree with no
       subprocess and no venv — the mechanism ``SNAG-LOG-012``'s check
       already uses for ``strip_markdown``.  Rule 8's *"it cannot be
       imported"* was true when written and is the reason the fallback
       exists rather than a reason to keep preferring it.
    2. **Absence is a skip; a moved symbol is a failure.**  Those are
       different facts with opposite remedies — one is a box without
       estate-manager on it, the other is this pin having quietly stopped
       pinning — and collapsing them is ``ports_checked``'s rule at the
       level of a test.  The skip is now reachable **only** when
       estate-manager is not beside this checkout at all.
    """

    #: Where the reader has lived.  Newest first, so a box carrying both
    #: is measured against the surface the owner publishes today.
    ESTATE_ROOT = Path.home() / "projects" / "estate-manager"

    def _read_snags(self):
        if not self.ESTATE_ROOT.exists():
            pytest.skip("estate-manager is not beside this checkout")

        reasons = []
        try:
            from estate.snags import read_snags
        except ImportError as exc:
            reasons.append(f"estate.snags: {exc}")
        else:
            rows, fmt = read_snags(SNAG_PATH.read_text(encoding="utf-8"))
            return {
                "open": sorted(row.snag_id for row in rows if row.is_open),
                "total": len(rows),
                "format": fmt,
            }

        service = self.ESTATE_ROOT / "service"
        interpreter = service / ".venv" / "bin" / "python"
        if interpreter.exists():
            import json
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
                [str(interpreter), "-c", script],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode == 0:
                return json.loads(result.stdout)
            reasons.append(f"estate_service.projects.roadmap: {result.stderr.strip()[-200:]}")
        else:
            reasons.append(f"{interpreter} does not exist")

        raise AssertionError(
            "estate-manager is on this box and neither place publishes read_snags — the "
            "instrument moved and this pin has stopped pinning, which is a failure and "
            "never a skip:\n  " + "\n  ".join(reasons)
        )

    def test_the_skip_is_only_reachable_when_estate_manager_is_absent(self):
        """The defect that hid the move, pinned from the outside.

        A ``pytest.skip`` on any *other* condition is how this class went
        quiet for a day: a moved symbol and a missing repository are
        different facts, and only one of them is a property of the box.
        The source is what answers this, since a green run cannot witness
        a branch it did not take.
        """
        tree = ast.parse(textwrap.dedent(inspect.getsource(self._read_snags)))
        skips = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "skip"
        ]
        assert len(skips) == 1, (
            "a second pytest.skip has appeared in the reader, so a way of not-running "
            f"other than estate-manager's absence can go quiet again (lines {skips})"
        )

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

class TestTheExpiryCheck:
    """``SNAG-ESTATE-013``'s check — the first aimed at this repository's own claims machinery.

    Every other check here measures the box, another repository's tree or
    a domain module.  This one drives :mod:`sysadmin.ops_claims`, which is
    what ``check-ops-claims.sh`` runs at both ends of a sitting — so the
    subject is imported and driven rather than reimplemented, and these
    tests exist mostly to pin the two things a run refuted about the first
    draft.

    **Both are about the probe rather than the module.**  The single
    straddle it started with holds only east of Greenwich; and the control
    it started with was the unfixed behaviour asserted twice, so a landed
    fix broke it.  Each candidate fix is therefore driven as a **real
    stand-in** — a module that reads the stamp differently — rather than
    as a literal saying "the fix landed", because the interesting verdicts
    are the ones that tell four different fixes apart.
    """

    #: The three zones the check is driven at, and why each is here.  One
    #: east of Greenwich (where the entry was observed), one west (where
    #: the same marker outlives its subject instead), and UTC (where the
    #: two stamps name one instant and the probe must decline).
    #: ``SNAG-LOG-009``'s three-timezone treatment, which is where the
    #: sign asymmetry was first written down in this repository.
    EAST, WEST, ZERO = "Europe/London", "America/New_York", "UTC"

    @staticmethod
    @contextlib.contextmanager
    def _zone(name: str):
        """Run a block at a nominated timezone, restoring the box's own.

        ``time.tzset`` is what makes ``astimezone()`` move, so the zone
        cannot be injected as an argument — the check reads the process's
        idea of local time exactly as :func:`datetime.datetime.now` does
        in the module it is measuring.
        """
        before = os.environ.get("TZ")
        os.environ["TZ"] = name
        time.tzset()
        try:
            yield
        finally:
            if before is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = before
            time.tzset()

    @staticmethod
    def _reslot(marker, region, now, instant):
        """The real ``check_expiry``, given a marker carrying ``instant``.

        Every stand-in below is a *rewriting* of the argument in front of
        the real timer rather than a reimplementation of it, so a
        stand-in cannot pass by accidentally modelling something simpler
        than the module — the Session 92 lesson about a disambiguator
        that measured its own luck.
        """
        parts = marker.argument.split(None, 1)
        rewritten = " ".join([instant.strftime("%Y-%m-%dT%H:%M"), *parts[1:]])
        return real_check_expiry(ops_claims.Marker(marker.key, rewritten), region, now)

    @staticmethod
    @contextlib.contextmanager
    def _accepting(fmt: str):
        """The module's accepted instant format moved, at **both** names.

        ``snag_claims`` does ``from sysadmin.ops_claims import
        EXPIRY_FORMAT``, so the constant lives in two namespaces and a
        landed fix moves both.  Patching only the owner is what let the
        coupling test below pass against the very code it was written to
        break — a guard asserting a *value* where it means *provenance*,
        for the third time in this repository.
        """
        with (
            patch.object(ops_claims, "EXPIRY_FORMAT", fmt),
            patch.object(snag_claims, "EXPIRY_FORMAT", fmt),
        ):
            yield

    def _drive(self, zone: str, **patches):
        with contextlib.ExitStack() as stack:
            stack.enter_context(self._zone(zone))
            for name, value in patches.items():
                stack.enter_context(patch.object(snag_claims, name, value))
            return check_expiry_naive_instant()

    # -- the specimen ----------------------------------------------------

    def test_the_producer_stamp_is_the_entrys_own(self):
        """The probe drives the stamp the entry quotes, not an invented one.

        The defect is a *copy* — a human reads an estate surface and
        writes its wall clock into a marker — so a specimen the entry
        does not name would be measuring a hypothetical copy.
        """
        assert EXPIRY_PRODUCER_STAMP in SNAG_PATH.read_text(encoding="utf-8")

    def test_the_region_names_both_wall_clocks(self):
        """Rule 9's pin must pass whichever clock a fix chooses to render.

        ``ops_claims`` requires the marker's wall clock to appear in the
        prose beside it.  A fix that taught the marker an offset would
        have to render one of two clocks back out — UTC's ``03:32`` or
        this box's ``04:32`` — and a region carrying only one would come
        back as a *pin* failure, so the check would report the wrong limb
        moved.  Driven rather than asserted from the text: both are put
        through the real ``check_expiry`` and neither may complain.
        """
        with self._zone(self.EAST):
            for clock in ("2026-08-25T03:32", "2026-08-25T04:32"):
                reading, problem = expiry_reading("pin", clock, datetime(2026, 8, 25, 3, 0))
                assert not problem, problem
                assert "prose does not" not in reading.note, clock

    # -- the box, in three zones -----------------------------------------

    def test_it_holds_east_of_greenwich(self):
        """The entry's own observation, re-measured: expiry before the subject."""
        measurement = self._drive(self.EAST)
        assert measurement.verdict == "match"
        assert any("expires 1 hour before its subject occurs" in d for d in measurement.detail)

    def test_it_holds_west_of_greenwich_in_the_other_direction(self):
        """The same marker, the other sign — and the defect the first draft missed.

        At ``UTC-4`` the marker names an instant four hours *after* its
        subject, so the prediction outlives what it predicted.  A probe
        asking only "did it expire early" reports the module correct
        here, which is ``SNAG-LOG-009``'s *"N hours late at UTC−N"*
        arriving one document over.
        """
        measurement = self._drive(self.WEST)
        assert measurement.verdict == "match"
        assert any("outlives its subject by 4 hours" in d for d in measurement.detail)

    def test_a_box_at_utc_declines_rather_than_refuting(self):
        """Zero-because-blind is never served as zero-because-clean.

        The magnitude *is* the local offset, so at UTC the two stamps
        name one instant and a zone-blind reading is indistinguishable
        from a correct one.  Reporting ``mismatch`` there would close an
        entry whose mechanism is untouched.
        """
        measurement = self._drive(self.ZERO)
        assert measurement.verdict == "unknown"
        assert "cannot demonstrate it" in measurement.note

    # -- the four fixes, each driven -------------------------------------

    def test_an_offset_bearing_format_refutes_both_halves(self):
        """The natural landing: the accepted form gains ``%z``.

        Patched at ``ops_claims`` rather than at this module, because
        that global is what ``check_expiry`` reads — and the naive stamp
        must keep rendering naively, which is the whole reason
        :data:`EXPIRY_NAIVE_FORMAT` is owned here.
        """
        with self._zone(self.EAST), self._accepting("%Y-%m-%dT%H:%M%z"):
            measurement = check_expiry_naive_instant()
        assert measurement.verdict == "mismatch"
        assert "first half" in measurement.note
        assert "second half" in measurement.note

    def test_the_naive_stamp_is_still_naive_when_the_module_moves(self):
        """The coupling a falsification found, pinned from the outside.

        The first draft rendered the naive stamp with the module's own
        ``EXPIRY_FORMAT``; under the fix above it silently starts
        rendering ``+0000``, the control moves with the thing it controls
        for, and a landed fix comes back looking like no fix at all.
        """
        with self._zone(self.EAST), self._accepting("%Y-%m-%dT%H:%M%z"):
            measurement = check_expiry_naive_instant()
        assert any(
            "expires 2026-08-25T03:32 …" in line for line in measurement.detail
        ), measurement.detail

    def test_the_naive_rendering_never_reaches_for_the_modules_constant(self):
        """The same coupling, banned at the source rather than measured.

        Session 92's rule — *banning the instrument beats measuring the
        property* — and here it is not a preference: the behavioural test
        above passed against the broken code until its patch was widened,
        because ``EXPIRY_FORMAT`` lives in two namespaces and only one of
        them was moved.  A value cannot answer provenance; the source
        can, so this refuses ``EXPIRY_FORMAT`` as an argument to any
        ``strftime`` in the check, which is the one place the coupling
        could come back.
        """
        tree = ast.parse(inspect.getsource(check_expiry_naive_instant))
        offenders = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "strftime"
            and any(
                isinstance(arg, ast.Name) and arg.id == "EXPIRY_FORMAT" for arg in node.args
            )
        ]
        assert not offenders, (
            "the naive stamp is rendered with ops_claims' own accepted format, so the "
            f"probe's control moves with the thing it controls for (line {offenders})"
        )

    def test_a_module_tolerant_of_both_forms_refutes_the_offset_half_alone(self):
        def tolerant(marker, region, now):
            parts = marker.argument.split(None, 1)
            try:
                moment = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M%z")
            except ValueError:
                return real_check_expiry(marker, region, now)
            return self._reslot(marker, region, now, moment.astimezone().replace(tzinfo=None))

        measurement = self._drive(self.EAST, check_expiry=tolerant)
        assert measurement.verdict == "mismatch"
        assert "first half" in measurement.note
        assert "second half" not in measurement.note

    def test_a_parse_that_fails_closed_refutes_the_zoneless_half_alone(self):
        def fail_closed(marker, region, now):
            parts = marker.argument.split(None, 1)
            if parts and len(parts[0]) == len("2026-08-25T03:32"):
                return ops_claims.Claim(
                    "expires:x", "x", "claim", None, None, "unknown", "a naive instant is refused"
                )
            return real_check_expiry(marker, region, now)

        measurement = self._drive(self.EAST, check_expiry=fail_closed)
        assert measurement.verdict == "mismatch"
        assert "second half" in measurement.note
        assert "first half" not in measurement.note

    def test_a_zoneless_instant_read_as_utc_refutes_it_by_neither_half(self):
        """The fix that moves the boundary onto the event, naming no half.

        **This is what refuted the first draft's control.**  It asserted
        the timer flips at the marker's own text — which a zone-aware
        module does not do, because its boundary is the producer's
        instant — so a landed fix came back ``unknown`` where it should
        come back ``mismatch``.  A control a fix breaks is the unfixed
        behaviour asserted twice.
        """

        def zone_aware(marker, region, now):
            parts = marker.argument.split(None, 1)
            try:
                moment = datetime.strptime(parts[0], "%Y-%m-%dT%H:%M").replace(tzinfo=UTC)
            except ValueError:
                return real_check_expiry(marker, region, now)
            return self._reslot(marker, region, now, moment.astimezone().replace(tzinfo=None))

        measurement = self._drive(self.EAST, check_expiry=zone_aware)
        assert measurement.verdict == "mismatch"
        assert "straddles the producer's instant" in measurement.note

    # -- the probe losing its grip ---------------------------------------

    def test_a_reader_that_stops_seeing_the_marker_is_reported(self):
        measurement = self._drive(self.EAST, read_markers=lambda region: [])
        assert measurement.verdict == "mismatch"
        assert "no longer sees the form the block writes" in measurement.note

    @pytest.mark.parametrize(
        ("label", "measured", "verdict"),
        [("passed", "passed 1 hour ago", "unknown"), ("to run", "1 hour to run", "match")],
    )
    def test_a_timer_stuck_on_one_answer_is_unknown(self, label, measured, verdict):
        """A straddle over a timer that cannot flip measures nothing.

        Both directions, because each satisfies one half of a naive
        "before says X, after says Y" test on its own.
        """

        def stuck(marker, region, now):
            claim = real_check_expiry(marker, region, now)
            if claim.measured is None:
                return claim
            return ops_claims.Claim(
                claim.key, claim.subject, claim.kind, claim.documented, measured, verdict, ""
            )

        measurement = self._drive(self.EAST, check_expiry=stuck)
        assert measurement.verdict == "unknown"
        assert "flips at neither straddle" in measurement.note

    # -- the entry's own deeper claim ------------------------------------

    def test_the_verdict_cannot_separate_the_two_readings(self):
        """Why the probe classifies on ``measured`` and never on the verdict.

        ``SNAG-ESTATE-013``'s title says the check "cannot say so", and
        it is truer than the entry states: a mis-timed prediction and a
        marker the module could not parse at all are **both** ``unknown``
        and both print ``??``, so nothing in the rendered report
        distinguishes them.  Only ``Claim.measured`` does.
        """
        with self._zone(self.EAST):
            mistimed, _ = expiry_reading(
                "naive", "2026-08-25T03:32", datetime(2026, 8, 25, 4, 32)
            )
            unparsed, _ = expiry_reading(
                "aware", "2026-08-25T03:32+00:00", datetime(2026, 8, 25, 4, 32)
            )
        assert mistimed.verdict == unparsed.verdict == "unknown"
        assert mistimed.parsed is True
        assert unparsed.parsed is False


class TestTheHealthPathCheck:
    """``SNAG-UNITS-003``'s check — the first here that sends a request.

    The entry is the registry's first whose headline is a **counted
    population**: *"wrong more often than right"*, at 4 right and 7 wrong
    of 11, measured once on 2026-08-15 by an author whose first draft
    said "two of twelve".  So the fixtures below are taken from the box
    on every run rather than written down — a test naming
    ``venture-chat`` as a wrong one would fossilise exactly the way the
    entry did, and would go on passing after the service moved.

    Every falsification is driven at a stand-in **modelling the change**
    rather than at a literal saying it happened: a generator that decides
    the path per port is the entry's own candidate fix, and a box where
    the guess answers everywhere is the premise dying with the generator
    untouched.
    """

    _MEASURED: dict[str, object] = {}

    @classmethod
    def _live(cls) -> dict[str, object]:
        """The box, partitioned once: right, wrong, witnesses, bare.

        Cached across the class because it is 22 loopback requests and
        every verdict test narrows the same partition.  It is also the
        check's own instruments, driven — so a test that narrows the
        population to "the ones the guess answers" is using the same
        measurement the check would.
        """
        if cls._MEASURED:
            return cls._MEASURED
        population, problem = snag_claims.health_path_population()
        assert not problem, problem
        emitted = {
            entry.port: snag_claims.generated_health_url(entry.port) for entry in population
        }
        probes, problem = snag_claims.probe_health_paths(population, emitted)
        assert not problem, problem
        by_name = {probe.name: probe for probe in probes}
        cls._MEASURED = {
            "population": population,
            "probes": by_name,
            "right": [e for e in population if by_name[e.name].guess_right],
            "wrong": [e for e in population if by_name[e.name].guess_wrong],
            "witness": [e for e in population if by_name[e.name].is_witness],
            # Derived from the declared path, never from ``is_witness``:
            # the two tests below break that property deliberately, and a
            # partition computed from it would empty itself and fail on
            # its own precondition instead of on the property.
            "bare": [
                e
                for e in population
                if by_name[e.name].guess_wrong
                and not by_name[e.name].declared_path.strip("/")
            ],
        }
        return cls._MEASURED

    @staticmethod
    @contextlib.contextmanager
    def _population(entries):
        with patch.object(
            snag_claims, "health_path_population", return_value=(list(entries), "")
        ):
            yield

    @staticmethod
    def _closed_port() -> int:
        """A port nothing is listening on, taken and released."""
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    @staticmethod
    def _entry(name: str, port: int, path: str):
        from sysadmin.monitor.services import ServiceEntry, SystemdRef

        return ServiceEntry(
            name=name,
            kind="http",
            url=f"http://localhost:{port}{path}",
            port=port,
            systemd=SystemdRef(unit=f"{name}.service", scope="user"),
        )

    # -- the instruments -------------------------------------------------

    def test_the_population_is_the_entrys_own_filter(self):
        """"Declaring a port and a unit", read off the file.

        The ``internet`` entry is the one this filter has to exclude: it
        is the only off-box url in ``services.yaml``, and it declares
        neither a port nor a unit, which is why the loopback guard is a
        second line of defence rather than the first.
        """
        population, problem = snag_claims.health_path_population()
        assert not problem
        assert population, "no services.yaml entry declares both a port and a unit"
        for entry in population:
            assert entry.port is not None and entry.unit is not None, entry.name
        assert "internet" not in {entry.name for entry in population}

    def test_the_pure_half_makes_no_request(self):
        """The mechanism claim itself, driven at a port nothing answers.

        If the generator probed before emitting, a closed port could not
        produce a url — and this is the assertion a landed fix breaks
        first, which is what makes it the entry's mechanism rather than
        a restatement of its wording.
        """
        url = snag_claims.generated_health_url(self._closed_port())
        assert url is not None
        assert url.endswith("/api/health")

    def test_the_emitted_url_is_the_one_the_snippet_would_have_a_reader_paste(self):
        """Read out of the advice, never rebuilt beside it.

        A check that assembled ``http://localhost:{port}/api/health``
        itself would go on probing that path for ever after the
        generator started emitting another one, and would report the
        entry holding against a fix that had landed.
        """
        from sysadmin.units.recommendations import recommendations_for_scan
        from sysadmin.units.scan import UNMONITORED, UnitFinding

        port = self._closed_port()
        finding = UnitFinding(
            unit=snag_claims.HEALTH_PROBE_UNIT,
            scope=snag_claims.HEALTH_PROBE_SCOPE,
            category=UNMONITORED,
            path=f"/nonexistent/{snag_claims.HEALTH_PROBE_UNIT}",
            monitor_unit=snag_claims.HEALTH_PROBE_UNIT,
            enabled=True,
        )
        blob = {
            "unit_audited_ports": {
                f"{snag_claims.HEALTH_PROBE_SCOPE}:{snag_claims.HEALTH_PROBE_UNIT}": [port]
            }
        }
        snippet = recommendations_for_scan([finding], None, blob)[0].snippet
        assert snag_claims.generated_health_url(port) in snippet

    def test_the_probe_never_leaves_this_machine(self):
        """Every url the check sends a request to, recorded and asserted.

        **Its population is measured empty and the guard it covers is
        one layer down**, which is stated rather than left to be read as
        coverage.  ``services.yaml``'s only off-box url is ``internet``,
        which declares neither a port nor a unit, so removing
        :func:`_loopback` entirely leaves this test green — the
        falsification that fires is
        :meth:`test_an_off_box_declared_url_is_unmeasured_rather_than_probed`,
        which drives a remote entry through the prober directly.  What
        this one pins is the property the sitting actually cares about:
        a check running at both ends of every sitting does not reach off
        the box today.
        """
        from sysadmin.monitor.agent import SysAdminAgent

        seen: list[str] = []
        real = SysAdminAgent._check_http

        async def recording(self, svc):
            seen.append(svc.url)
            return await real(self, svc)

        with patch.object(SysAdminAgent, "_check_http", recording):
            check_health_path_guess()
        assert seen
        for url in seen:
            assert urlsplit(url).hostname in snag_claims.LOOPBACK_HOSTS, url

    def test_an_off_box_declared_url_is_unmeasured_rather_than_probed(self):
        from sysadmin.monitor.services import ServiceEntry, SystemdRef

        remote = ServiceEntry(
            name="elsewhere",
            kind="http",
            url="https://1.1.1.1/cdn-cgi/trace",
            port=443,
            systemd=SystemdRef(unit="elsewhere.service", scope="user"),
        )
        probes, problem = snag_claims.probe_health_paths(
            [remote], {443: "http://localhost:443/api/health"}
        )
        assert not problem
        assert probes[0].measured is False
        assert "no url on this machine" in probes[0].problem

    def test_a_bare_path_service_is_never_a_witness(self):
        """The distinction the witness rule turns on, pinned at the box.

        A frontend declaring ``http://localhost:3100`` counts in the
        population and is a *wrong* guess, but no implementation that
        probed would have emitted a bare url either — so it cannot
        separate a guessing generator from a probing one that fell
        back.
        """
        live = self._live()
        for entry in live["bare"]:
            probe = live["probes"][entry.name]
            assert probe.guess_wrong is True
            assert probe.is_witness is False
            assert probe.declared_path.strip("/") == ""
        for entry in live["witness"]:
            probe = live["probes"][entry.name]
            assert probe.guess_wrong is True
            assert probe.declared_path.strip("/")

    # -- the verdicts ----------------------------------------------------

    def test_the_check_holds_on_this_box(self):
        measurement = check_health_path_guess()
        assert measurement.verdict == "match"
        assert any("witness port(s)" in line for line in measurement.detail)
        assert any("measured services answer it" in line for line in measurement.detail)

    def test_the_recount_follows_the_box_and_is_not_a_constant(self):
        """The entry's 4, 7 and 11 appear nowhere in the module.

        Driven rather than grepped: narrow the population and the
        reported figures move with it.  A check carrying the document's
        own numbers as constants would report the same three whatever
        ``services.yaml`` said, which is the fossil this entry is.
        """
        live = self._live()
        narrowed = live["right"][:1] + live["witness"][:2]
        with self._population(narrowed):
            measurement = check_health_path_guess()
        assert any(f"all {len(narrowed)} ports" in line for line in measurement.detail)
        assert any(f"1 of {len(narrowed)} measured" in line for line in measurement.detail)

    def test_a_generator_that_decides_the_path_per_port_is_a_mismatch(self):
        """The entry's own candidate fix, driven as the behaviour it is.

        *"Probe /api/health, /health and /api/v1/health once when a
        snippet is generated, and emit the one that answers"* — modelled
        by emitting each service's own declared url, which is what such
        a probe would find.
        """
        live = self._live()
        answering = {entry.port: entry.url for entry in live["population"]}
        with patch.object(snag_claims, "generated_health_url", answering.get):
            measurement = check_health_path_guess()
        assert measurement.verdict == "mismatch"
        assert "deciding the path per port" in measurement.note

    def test_an_empty_path_is_named_rather_than_joined_away(self):
        """A note saying four paths must name four.

        Two services here declare a url with no path at all — the entry
        counts them as exactly that — and ``", ".join`` renders an empty
        path as nothing, so the first draft of the per-port note read
        ``(, /api/health, /api/v1/health, /health)`` and left the reader
        to notice a gap where a measurement was.  ``SNAG-BRIEF-002``'s
        rule at the size of a list separator.
        """
        live = self._live()
        answering = {entry.port: entry.url for entry in live["population"]}
        assert any(not urlsplit(url).path for url in answering.values()), (
            "no service declares a bare url any more, so this test no longer "
            "reaches the rendering it pins"
        )
        with patch.object(snag_claims, "generated_health_url", answering.get):
            measurement = check_health_path_guess()
        # Parsed with the closing context, not on the first ``)``: the
        # marker this test is about carries brackets of its own, and a
        # naive split reads ``(no path`` and fails for the wrong reason.
        listed = re.search(r"ports \((.*)\) — it is deciding", measurement.note)
        assert listed, measurement.note
        items = [item.strip() for item in listed.group(1).split(",")]
        assert "(no path)" in items
        assert "" not in items

    def test_a_box_where_the_guess_answers_everywhere_is_a_mismatch(self):
        """The premise dying with the generator untouched.

        Narrowed to the services the guess already answers, which is the
        box this entry would describe if every service adopted the
        contract's path.  The generator is the real one throughout.
        """
        live = self._live()
        with self._population(live["right"]):
            measurement = check_health_path_guess()
        assert measurement.verdict == "mismatch"
        assert "no longer describes this box" in measurement.note

    def test_a_tie_no_longer_reads_as_wrong_more_often_than_right(self):
        """The boundary the title's claim sits on, driven at it.

        ``wrong <= right`` and not ``<``: an even split is not "wrong
        more often than right", and an off-by-one here would keep the
        entry alive through the exact state that retires it.
        """
        live = self._live()
        count = min(len(live["right"]), len(live["witness"]))
        assert count, "the box has no right/wrong pair to balance"
        with self._population(live["right"][:count] + live["witness"][:count]):
            measurement = check_health_path_guess()
        assert measurement.verdict == "mismatch"
        assert "no longer wrong more often than right" in measurement.note

    def test_no_witness_is_unknown_and_never_a_match(self):
        """A constant path with nowhere else to go proves nothing.

        The population is one service the guess answers and every
        bare-path one it does not, so the guess is wrong more often than
        right and *still* cannot be told from an implementation that
        probed, found nothing and fell back.
        """
        live = self._live()
        assert live["bare"], "the box has no bare-path service to build this on"
        with self._population(live["right"][:1] + live["bare"]):
            measurement = check_health_path_guess()
        assert measurement.verdict == "unknown"
        assert "declares a bare path of its own" in measurement.note

    def test_a_box_where_nothing_answers_its_own_url_is_unknown(self):
        """The control, and the reading it refuses.

        Without it a stopped estate reports every path wrong and this
        entry holds hardest on the morning the box came up — the
        strongest confirmation the check could give, from the one state
        that is no evidence at all.
        """
        port = self._closed_port()
        with self._population([self._entry("dead", port, "/health")]):
            measurement = check_health_path_guess()
        assert measurement.verdict == "unknown"
        assert "evidence about the box, not about the path" in measurement.note

    def test_a_generator_emitting_no_url_is_unknown(self):
        with patch.object(snag_claims, "generated_health_url", return_value=None):
            measurement = check_health_path_guess()
        assert measurement.verdict == "unknown"
        assert "the snippet's shape has moved" in measurement.note

    def test_an_unloadable_services_file_is_unknown(self):
        with patch.object(
            snag_claims, "health_path_population", return_value=([], "services.yaml would not load")
        ):
            assert check_health_path_guess().verdict == "unknown"

    def test_an_empty_population_is_unknown_and_never_a_match(self):
        with self._population([]):
            measurement = check_health_path_guess()
        assert measurement.verdict == "unknown"
        assert "the population the entry counted is gone" in measurement.note

    def test_a_probe_that_will_not_run_is_unknown(self):
        """A check that raises is a check that did not run — rule 5.

        Caught inside the prober rather than by :func:`run_check`, so
        the emitted path is still reported: an offline box should say
        what the advice emits even when it cannot say whether it works.
        """
        from sysadmin.monitor.agent import SysAdminAgent

        with patch.object(SysAdminAgent, "_check_http", side_effect=OSError("no network")):
            measurement = check_health_path_guess()
        assert measurement.verdict == "unknown"
        assert "the health probe would not run" in measurement.note
        assert any("the advice emits" in line for line in measurement.detail)

    # -- the reading -----------------------------------------------------

    def test_nothing_here_compares_a_health_status_to_ok_by_hand(self):
        """``SNAG-API-004``'s guard, applied to the module that just gained a reader.

        ``!= "ok"`` was written three times and was wrong three times the
        day migration 009 admitted ``skipped``.  This module now reads a
        status ``_check_http`` produced, so it is the fourth place that
        rule has to hold, and the classification is imported from beside
        the CHECK constraint rather than restated here.
        """
        tree = ast.parse((REPO_ROOT / "sysadmin" / "snag_claims.py").read_text(encoding="utf-8"))
        offenders = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Compare)
            and any(
                isinstance(other, ast.Constant) and other.value == "ok"
                for other in node.comparators
            )
        ]
        assert not offenders, f"a health status compared to 'ok' by hand at {offenders}"


class TestTheQuietenedJudgementCheck:
    """``SNAG-ESTATE-010``'s check — the first here that writes to the database.

    Every check before this one reads: an ``ast`` walk, a driven pure
    function, another repository's interpreter, a journal, an outbound
    request.  This one opens a row, judges over it and rolls back, which
    makes *"nothing survives"* a property with a test of its own rather
    than a promise in a docstring.

    The entry's own population has resolved — its third bullet predicted
    that it would — so nothing below counts the two dev-server rows it
    was filed from.  What is driven is the mechanism, and every
    falsification is a stand-in **modelling a landed fix** rather than a
    literal saying one landed: an in-place rung, a resolve-and-re-raise,
    and the ``holder`` blob arriving alone are the three shapes a fix
    could take, and two of them leave the severity column untouched.
    """

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _judged():
        """The two judgements the probe's payload produces, computed purely."""
        from sysadmin.core.config import get_config
        from sysadmin.estate.judgements import judge_audit_findings
        from sysadmin.units.ports import attribution_from_blob

        payload = {
            "findings": [
                snag_claims.quieten_finding(port) for port in snag_claims.QUIETEN_PORTS
            ]
        }
        attribution = attribution_from_blob(
            {"transient_ports": {snag_claims.QUIETEN_HOLDER: list(snag_claims.QUIETEN_PORTS)}},
            datetime.now(UTC).isoformat(),
        )
        judged = judge_audit_findings(
            payload, get_config().agents.estate_judge.port_breach_max_rows, attribution
        )
        return {judgement.details["port"]: judgement for judgement in judged}

    @classmethod
    def _surviving_rows(cls) -> int:
        """Alert rows on the live box that the probe could have left.

        **Counted by title, and the first draft counted by message.**
        The row the probe *opens* carries :data:`QUIETEN_MESSAGE`; the
        row it raises — the witness, and the more interesting write —
        carries the estate's own ``summary``, because ``raise_alert`` is
        handed the judgement's message.  So a guard keyed on the probe's
        message was blind to exactly the row the check exists to produce,
        and a committing stand-in leaked one past it.  Found by driving
        that stand-in rather than by reading this, which is the fourth
        time in this file a falsification has corrected the guard it was
        aimed at.

        Interpolated rather than bound because :func:`query_one` takes a
        statement; the constants are asserted quote-free one test down,
        so the interpolation cannot become an injection by a later edit.
        """
        judged = cls._judged()
        titles = ", ".join(f"'{judged[port].title}'" for port in snag_claims.QUIETEN_PORTS)
        count, problem = snag_claims.query_one(
            f"SELECT count(*) FROM sysadmin.alerts WHERE title IN ({titles}) "
            f"OR message = '{snag_claims.QUIETEN_MESSAGE}'"
        )
        assert not problem, problem
        return int(count or 0)

    @staticmethod
    def _surviving_sweeps() -> int:
        count, problem = snag_claims.query_one(
            "SELECT count(*) FROM sysadmin.unit_audits "
            f"WHERE findings::text LIKE '%{snag_claims.QUIETEN_HOLDER}%'"
        )
        assert not problem, problem
        return int(count or 0)

    @staticmethod
    @contextlib.contextmanager
    def _fix(mutate):
        """Run the real ``_execute``, then apply ``mutate`` — a landed fix.

        The fix is modelled *after* the production loop rather than
        instead of it, so the run under test is the real one and the only
        difference is that something reclassified a standing row.  A
        stand-in replacing ``_execute`` outright would prove the check
        notices an edit to itself.
        """
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._execute

        async def patched(self, session):
            result = await real(self, session)
            await mutate(session)
            return result

        with patch.object(EstateJudgeAgent, "_execute", patched):
            yield

    @staticmethod
    async def _standing(session):
        from sqlalchemy import select

        from sysadmin.core.models.alert import Alert

        return (
            (
                await session.execute(
                    select(Alert).where(
                        Alert.message == snag_claims.QUIETEN_MESSAGE,
                        Alert.resolved.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )

    # -- the instruments -------------------------------------------------

    def test_the_probe_writes_nothing_that_survives(self):
        """The property that makes writing to the live database allowable.

        Asserted before and after, because a probe that had been leaking
        rows for a week would satisfy an "after" assertion on its own.
        """
        assert self._surviving_rows() == 0
        assert self._surviving_sweeps() == 0
        reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert reading is not None and reading.witnessed
        assert self._surviving_rows() == 0
        assert self._surviving_sweeps() == 0

    def test_nothing_survives_a_run_that_raised(self):
        """The rollback is in a ``finally``, so a failed drive leaks nothing either."""
        from sysadmin.estate.agent import EstateJudgeAgent

        async def boom(self, session):
            raise RuntimeError("the judge fell over mid-run")

        with patch.object(EstateJudgeAgent, "_execute", boom):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "unknown"
        assert "would not run against the live database" in measurement.note
        assert self._surviving_rows() == 0
        assert self._surviving_sweeps() == 0

    def test_the_probes_own_strings_cannot_become_an_injection(self):
        for constant in (snag_claims.QUIETEN_MESSAGE, snag_claims.QUIETEN_HOLDER):
            assert "'" not in constant and "\\" not in constant, constant

    def test_the_probe_ports_hold_no_live_row(self):
        """The titles it opens must be nobody else's fault.

        A probe port that collided with a real breach would deduplicate
        against a standing row somebody else raised and read the result
        as its own — and would leave that row's severity as the thing it
        reported on.
        """
        assert self._surviving_rows() == 0

    def test_the_instrument_is_the_agents_own_execute(self):
        """Driven, not reimplemented.

        The claim is a branch three statements into ``_execute``; a check
        that rebuilt the raise loop beside it would report a fix landing
        in the real one as no change at all.
        """
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._execute
        sessions = []

        async def counting(self, session):
            sessions.append(session)
            return await real(self, session)

        with patch.object(EstateJudgeAgent, "_execute", counting):
            reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert reading is not None and len(sessions) == 1

    def test_the_run_sees_a_standing_row_at_the_loud_rung(self):
        """The precondition, read off what the production loop was handed.

        ``holder: null`` and not an absent key: the rows the entry was
        filed from carry exactly that, and "the blob did not arrive" has
        to be a value that did not change rather than a key missing for
        two possible reasons.
        """
        from sysadmin.estate.agent import EstateJudgeAgent
        from sysadmin.estate.judgements import DEFAULT_SEVERITY

        real = EstateJudgeAgent._open_alerts
        seen = []

        async def recording(self, session):
            rows = await real(self, session)
            seen.extend(
                (row.severity, (row.details or {}).get("holder"), "holder" in (row.details or {}))
                for row in rows
                if row.message == snag_claims.QUIETEN_MESSAGE
            )
            return rows

        with patch.object(EstateJudgeAgent, "_open_alerts", recording):
            reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert seen == [(DEFAULT_SEVERITY, None, True)]

    def test_only_the_findings_surface_is_read(self):
        """The four declined surfaces, asserted at the sweep that consumes them.

        ``503`` rather than an empty payload: the sweep is scoped per
        surface, so a run that read all five would resolve every genuinely
        open estate row inside the transaction.  Rolled back either way,
        and a probe that can decline the blast should not spend the
        rollback instead.
        """
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._resolve_gone
        seen = []

        async def recording(self, session, open_alerts, current, read):
            seen.append(set(read))
            return await real(self, session, open_alerts, current, read)

        with patch.object(EstateJudgeAgent, "_resolve_gone", recording):
            reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert seen == [{"audit_findings"}]

    def test_neither_title_nor_rung_is_written_down_in_the_module(self):
        """Provenance, and asserted at the source rather than at a value.

        ``assert title == judged.title`` passes whether the module
        derived it or retyped it — the shape this repository has now been
        caught by three times — so this walks the tree: no string
        constant outside a docstring may carry the producer's title, and
        ``TRANSIENT_HOLDER_SEVERITY`` may not be imported at all.
        """
        tree = ast.parse(Path(snag_claims.__file__).read_text(encoding="utf-8"))
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(
                node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef
            ):
                first = node.body[0] if node.body else None
                if (
                    isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)
                ):
                    docstrings.add(id(first.value))
        offenders = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
            and "Estate port" in node.value
        ]
        assert not offenders, f"the producer's title is written down here: {offenders}"
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "TRANSIENT_HOLDER_SEVERITY" not in imported

    def test_the_run_says_nothing_a_reader_would_take_for_the_box(self, caplog):
        """``alert_raised`` for a row about to be rolled back, suppressed.

        This script prints its report to a terminal at both ends of every
        sitting, and a log line announcing an alert on two ports nothing
        is listening on is a worse artefact than noise.
        """
        with caplog.at_level(logging.INFO):
            reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert reading is not None and reading.witnessed
        assert not [
            record for record in caplog.records if record.getMessage() == "alert_raised"
        ]

    def test_the_disable_is_restored_and_caplog_cannot_witness_that(self):
        """The other half of the same ``finally``, and it needs its own test.

        Written first as one assertion inside the ``caplog`` block above,
        where it **passed against code whose restore had been deleted**.
        ``caplog.at_level`` is not neutral: pytest's ``catching_logs``
        sets ``logging.disable(NOTSET)`` on entry and puts the previous
        level back on exit, so the global is restored by the fixture
        whatever the module does with it.  A guard that cannot fail is
        the shape this file has now recorded three times — twice for
        asserting a *value* where it meant provenance, and once here for
        asserting a global inside the one context manager that owns it.
        """
        before = logging.root.manager.disable
        reading, problem = snag_claims.quietened_judgement_reading()
        assert not problem, problem
        assert reading is not None
        assert logging.root.manager.disable == before

    # -- the verdicts ----------------------------------------------------

    def test_the_check_holds_on_this_box(self):
        measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "match"
        assert any(
            f"port {snag_claims.QUIETEN_OPEN_PORT} stood open at" in line
            for line in measurement.detail
        )
        assert any(
            f"port {snag_claims.QUIETEN_FRESH_PORT} stood open at nothing" in line
            for line in measurement.detail
        )

    def test_the_two_ports_are_judged_alike_and_differ_only_in_what_stood_open(self):
        """The one variable the pair holds, pinned at the pure judgement."""
        judged = self._judged()
        assert set(judged) == set(snag_claims.QUIETEN_PORTS)
        rungs = {judgement.severity for judgement in judged.values()}
        assert len(rungs) == 1
        for judgement in judged.values():
            assert judgement.details["holder"]["transient"] is True

    def test_an_in_place_severity_change_is_a_mismatch(self):
        """The first of the three shapes a fix could take."""
        from sqlalchemy import update

        from sysadmin.core.models.alert import Alert
        from sysadmin.estate.judgements import TRANSIENT_HOLDER_SEVERITY

        async def in_place(session):
            await session.execute(
                update(Alert)
                .where(
                    Alert.message == snag_claims.QUIETEN_MESSAGE,
                    Alert.resolved.is_(False),
                )
                .values(severity=TRANSIENT_HOLDER_SEVERITY)
            )

        with self._fix(in_place):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "mismatch"
        assert "its severity went warning → info" in measurement.note

    def test_resolve_and_re_raise_is_a_mismatch(self):
        """The second, and the one the entry's fourth bullet names as obvious.

        It leaves the original row's severity exactly where it was, so a
        check reading that column alone would call this no change.
        """
        from sysadmin.core.models.alert import Alert
        from sysadmin.estate.judgements import TRANSIENT_HOLDER_SEVERITY

        async def resolve_and_reraise(session):
            row = await self._standing(session)
            assert row is not None
            row.resolved = True
            row.resolved_at = datetime.now(UTC)
            session.add(
                Alert(
                    agent=row.agent,
                    severity=TRANSIENT_HOLDER_SEVERITY,
                    title=row.title,
                    message=snag_claims.QUIETEN_MESSAGE,
                    details={**(row.details or {}), "holder": {"transient": True}},
                )
            )
            await session.flush()

        with self._fix(resolve_and_reraise):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "mismatch"
        assert "2 rows now carry the standing title" in measurement.note

    def test_the_holder_blob_arriving_alone_is_a_mismatch(self):
        """The third, and the reason the assertion is reach rather than rung.

        Session 26c's annotation reaching a standing row while its
        severity stays put is a real partial fix — the entry names both
        halves — and a check watching only the severity column would
        report it as the entry still holding.
        """

        async def holder_only(session):
            row = await self._standing(session)
            assert row is not None
            row.details = {
                **(row.details or {}),
                "holder": {"unit": "probe.scope", "scope": "user", "transient": True},
            }
            await session.flush()

        with self._fix(holder_only):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "mismatch"
        assert "details['holder'] is now" in measurement.note
        assert "severity went" not in measurement.note

    def test_without_the_witness_the_verdict_is_unknown(self):
        """The control, driven at the state that would otherwise read ``match``.

        A run whose attribution never arrives raises the fresh port at
        the loud rung and leaves the standing row exactly as untouched as
        the dedup does — so the detail still reports an unmoved row, and
        only the witness rule stops that being published as the entry
        holding.
        """
        from sysadmin.estate.agent import EstateJudgeAgent
        from sysadmin.units.ports import PortAttribution

        async def blind(self, session):
            return PortAttribution()

        with patch.object(EstateJudgeAgent, "_attribution", blind):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "unknown"
        assert "evidence about this probe" in measurement.note
        assert any(
            f"port {snag_claims.QUIETEN_OPEN_PORT} stood open at warning; after the run "
            "1 row(s) carry its title, severity warning" in line
            for line in measurement.detail
        )

    def test_a_family_with_no_quieter_rung_is_unknown(self):
        """Session 57's fix reverted: nothing left for a fix to deliver.

        Reached before any row is written, so this also pins that the
        probe declines to touch the database when it already knows it
        would measure nothing.
        """
        from sysadmin.estate import judgements

        with patch.object(
            judgements, "DEFAULT_SEVERITY", judgements.TRANSIENT_HOLDER_SEVERITY
        ):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "unknown"
        assert "no quieter rung" in measurement.note
        assert self._surviving_rows() == 0

    def test_a_rolled_up_payload_is_unknown(self):
        """One row for two ports is not the pair this probe holds constant."""
        from sysadmin.core.config import get_config

        with patch.object(get_config().agents.estate_judge, "port_breach_max_rows", 1):
            measurement = check_quietened_judgement_reach()
        assert measurement.verdict == "unknown"
        assert "rather than one per port" in measurement.note

    def test_the_check_names_the_entry_and_the_entry_names_the_check(self):
        check = CHECKS["quietened_judgement_reach"]
        assert check.snag == "SNAG-ESTATE-010"
        entries, problem = snag_claims.load_entries()
        assert not problem, problem
        entry = next(e for e in entries if e.snag_id == check.snag)
        assert "quietened_judgement_reach" in entry.markers
