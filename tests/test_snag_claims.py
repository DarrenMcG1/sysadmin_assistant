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
import dataclasses
import inspect
import itertools
import re
import socket
import tempfile
import textwrap
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import blake2s
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest

import sysadmin.ops_claims as ops_claims
import sysadmin.snag_claims as snag_claims
from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.core.text import strip_markdown as real_strip_markdown
from sysadmin.snag_claims import (
    CHECKS,
    DEPRECATED_MODULE,
    MAX_NAMED_ENTRIES,
    REVIEW_SCHEDULE_LEAVES,
    SNAG_PATH,
    STRIP_SPECIMEN,
    STRIPPER_FORMS,
    STRIPPER_NAME,
    STRIPPER_PROBE,
    Check,
    Measurement,
    call_sites,
    check_all,
    check_capped_signature_collides,
    check_code_spans_survive,
    check_convention,
    check_deprecated_contracts,
    check_dropin_blind_spot,
    check_estate_port_8500,
    check_health_path_guess,
    check_run_status_cancelled,
    check_sysd_ollama_ordering,
    check_tray_report_unheard,
    check_unmarked_sentence_invisible,
    check_unswept_port_is_loud,
    closure_declared,
    load_entries,
    main,
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
# The unchecked line in every state — SNAG-DOCS-006
# ---------------------------------------------------------------------------

#: Every open entry carries a check.  The state that produced no line at
#: all until 2026-08-28, and the state this box entered the moment
#: ``SNAG-DOCS-006`` closed.
ALL_CHECKED = """# Snag List

## Open Issues

- [P3] SNAG-DONE-001: **a checked thing** (2026-08-01)
  - **Check**: <!--check:fake_one--> `sysadmin-check-snags` — refuted when mended
"""

#: Entries the parser reads, none of them open.  ``load_entries`` finds no
#: problem to report, so nothing upstream catches it, and the unchecked
#: count is nought because there was nothing to count.
NONE_OPEN = """# Snag List

## Open Issues

- [P3] SNAG-GONE-001: **a thing** (2026-08-01, **fixed 2026-08-02**)
  - **Check**: <!--check:fake_one--> `sysadmin-check-snags` — refuted when mended
"""


class TestTheUncheckedLineIsPublishedInEveryState:
    """``SNAG-DOCS-006``: ``ports_checked``'s rule at the claims register.

    The line was appended inside ``if unchecked:``, so *every open entry
    is checked* and *the finding was deleted, renamed or is failing to
    run* rendered identically — as nothing.  Each test here is falsified
    by putting that ``if`` back: the first three then raise ``IndexError``
    on an empty list, and the fourth reads exit ``0`` for a report that
    looked at nothing.
    """

    @staticmethod
    def _line(document: str, checks: dict) -> object:
        with patch.dict(CHECKS, checks, clear=True):
            findings = check_convention(read_entries(document), "")
        return [f for f in findings if f.key == "convention:unchecked"][0]

    def test_a_register_with_every_entry_checked_says_nought(self):
        """The founding case: a line, a count, and ``match``."""
        line = self._line(ALL_CHECKED, {"fake_one": _check(snag="SNAG-DONE-001")})
        assert line.verdict == "match"
        assert "0 of 1 open entries" in line.note
        assert line.detail == ()

    def test_a_register_with_no_open_entry_is_unknown_and_not_clean(self):
        """The witness rule.  Nothing in this population could have differed.

        ``load_entries`` reports a problem only when it reads *no* entries
        at all, so a document whose entries are all closed parses cleanly
        and reaches here with ``open_total == 0``.  Serving that as
        ``match`` would be zero-because-blind dressed as
        zero-because-clean — the defect being fixed, one level in.
        """
        line = self._line(NONE_OPEN, {"fake_one": _check(snag="SNAG-GONE-001")})
        assert line.verdict == "unknown"
        assert "no open entry" in line.note

    def test_an_unchecked_entry_is_still_unknown(self):
        """A regression pin, and it passes against the old code by design.

        The fix must not have widened what an *unchecked* entry reports:
        a claim nobody has tested is rule 5's ``unknown`` whatever else
        moved around it.
        """
        line = self._line(DOCUMENT, {"fake_one": _check()})
        assert line.verdict == "unknown"
        assert line.detail == ("SNAG-FAKE-003",)

    def test_the_key_is_the_same_line_in_all_three_states(self):
        """What makes it publication rather than three findings.

        ``ports_checked`` is one field answered in both states, not a
        field that appears in one of them.  A reader — or a grep — finds
        ``convention:unchecked`` whatever the register holds, and reads
        the verdict to learn which state it is in.
        """
        verdicts = {
            self._line(document, {"fake_one": _check(snag=snag)}).verdict
            for document, snag in (
                (ALL_CHECKED, "SNAG-DONE-001"),
                (NONE_OPEN, "SNAG-GONE-001"),
                (DOCUMENT, "SNAG-FAKE-001"),
            )
        }
        assert verdicts == {"match", "unknown"}

    def test_the_exit_status_contract_survives_the_zero(self):
        """Why this was filed rather than fixed where it was found.

        ``_convention`` returned ``unknown`` unconditionally, so
        publishing the line in the empty state would have pinned
        ``sysadmin-check-snags`` at exit ``2`` for ever — a change to what
        ``claude-precommit.sh`` and ``claude-postflight.sh`` read.  A
        report whose only convention line is the nought exits ``0``; the
        vacuous register still exits ``2``.

        **The presence assertion comes first and is what makes this
        discriminate.**  Written as the two status assertions alone it
        passed against the stripped code, because ``overall`` of *no*
        findings is also ``match`` and also exits ``0`` — a status test
        agreeing with silence, which is the very thing the entry is
        about.  The vacuous half passed for a worse reason still: the
        first draft's document carried no marker, so ``pin:fake_one``
        fired and supplied the ``2`` the branch under test was supposed
        to.
        """
        with patch.dict(CHECKS, {"fake_one": _check(snag="SNAG-DONE-001")}, clear=True):
            clean = check_convention(read_entries(ALL_CHECKED), "")
        with patch.dict(CHECKS, {"fake_one": _check(snag="SNAG-GONE-001")}, clear=True):
            vacuous = check_convention(read_entries(NONE_OPEN), "")
        assert [f.key for f in clean] == ["convention:unchecked"]
        assert EXIT_STATUS[overall(clean)] == 0
        assert [f.key for f in vacuous] == ["convention:unchecked"]
        assert EXIT_STATUS[overall(vacuous)] == 2


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
        read — so a substring instrument reported ``SNAG-CFG-002`` refuted
        on its first run.  Pointing the AST walk at one of those leaves
        finds those readers; pointing it at that entry's own leaves finds
        none.  Same instrument, two questions, and only the exact one is
        right.

        **The demonstration outlived the entry**, which is why this test
        did not retire with the check on 2026-08-30.  It turns on
        ``review_hour`` being a *substring* of ``log_review_hour`` and
        not its ``ast.Attribute.attr``, and neither fact needs the
        deleted leaves to exist.  What it can no longer witness is the
        deletion itself — an empty result now means "absent" as readily
        as "unread", the blind spot that let the retired check report
        ``match`` over its own closure — so the discriminating assertion
        lives beside the model it is about, in
        :class:`tests.test_config_defaults.TestTheVacatedReviewLeavesStayGone`.
        """
        assert snag_claims.attribute_reads(
            frozenset({"log_review_hour"}), (REPO_ROOT / "sysadmin",)
        )
        assert not snag_claims.attribute_reads(REVIEW_SCHEDULE_LEAVES, (REPO_ROOT / "sysadmin",))

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


class TestTheTrayReportUnheardCheck:
    """``SNAG-TRAY-011``'s check — the tray's warning reaches no reader.

    Two independent channels, so the check is driven at **both** fix
    directions and at the reader failing.  A check that could only see
    one would report ``match`` over a half-landed fix, which is the
    ``a-control-a-fix-breaks-is-not-a-control`` shape.
    """

    @pytest.fixture
    def real_services(self):
        """The committed ``services.yaml``, not conftest's four stand-ins.

        The autouse ``services`` fixture installs a synthetic list with
        no tray unit and no ``log:`` block, so every question this check
        asks would be answered by a file the operator never wrote.  It is
        also what makes the witness guard visible: under the stand-ins
        the check correctly returns ``unknown`` rather than reading their
        silence as evidence.
        """
        from sysadmin.monitor import services as services_module
        from sysadmin.monitor.services import default_services_path, load_services

        previous = services_module._services
        services_module._services = load_services(default_services_path())
        yield
        services_module._services = previous

    def test_it_holds_against_the_shipped_files(self, real_services):
        assert check_tray_report_unheard().verdict == "match"

    def test_the_conftest_stand_ins_are_unknown_not_match(self):
        """The witness guard, seen from the fixture that would have hidden it."""
        assert check_tray_report_unheard().verdict == "unknown"

    def test_ingesting_the_trays_journal_refutes_it(self, monkeypatch, real_services):
        """Channel one: a ``log:`` block on ``sysadmin-tray``."""
        from sysadmin.monitor.services import composed_log_sources as real

        def with_tray(agent_config):
            sources = list(real(agent_config))
            forged = sources[0].model_copy(
                update={"name": "sysadmin-tray", "unit": "sysadmin-tray.service"}
            )
            return [*sources, forged]

        monkeypatch.setattr(
            "sysadmin.monitor.services.composed_log_sources", with_tray
        )
        measurement = check_tray_report_unheard()
        assert measurement.verdict == "mismatch"
        assert "declared log source" in measurement.note

    def test_a_second_caller_refutes_it_too(self, monkeypatch, real_services):
        """Channel two: a reload path would make the report non-startup-only."""
        from sysadmin import snag_claims

        monkeypatch.setattr(snag_claims, "_load_tray_config_call_sites", lambda: 2)
        measurement = check_tray_report_unheard()
        assert measurement.verdict == "mismatch"
        assert "call sites" in measurement.note

    def test_both_channels_moving_says_so(self, monkeypatch, real_services):
        from sysadmin import snag_claims
        from sysadmin.monitor.services import composed_log_sources as real

        def with_tray(agent_config):
            sources = list(real(agent_config))
            return [*sources, sources[0].model_copy(update={"unit": "sysadmin-tray.service"})]

        monkeypatch.setattr("sysadmin.monitor.services.composed_log_sources", with_tray)
        monkeypatch.setattr(snag_claims, "_load_tray_config_call_sites", lambda: 3)
        assert "both" in check_tray_report_unheard().note

    def test_a_reader_that_lost_our_own_unit_is_unknown_not_match(
        self, monkeypatch, real_services
    ):
        """The discriminating witness.

        An empty source list would otherwise report the tray's absence
        from it as evidence, when it is only the reader failing —
        ``a-check-needs-a-discriminating-witness``.

        ``real_services`` is not decoration: without it the stand-in is
        aimed *past* the decision, the check returns on the earlier "no
        tray unit" gate, and the assertion passes having never reached
        the guard it names.
        """
        monkeypatch.setattr(
            "sysadmin.monitor.services.composed_log_sources", lambda _cfg: []
        )
        measurement = check_tray_report_unheard()
        assert measurement.verdict == "unknown"
        assert "reader failing" in measurement.note

    def test_an_unreadable_services_yaml_is_unknown(self, monkeypatch):
        """Patched at ``get_services``, which is what the check now calls.

        Its first draft patched ``load_services`` and passed anyway — the
        singleton was already installed, so nothing raised and the
        verdict was ``unknown`` for the unrelated "no tray unit" reason.
        A green test that never ran the branch it names.
        """
        from sysadmin.monitor import services as services_module

        def boom():
            raise OSError("gone")

        monkeypatch.setattr(services_module, "get_services", boom)
        measurement = check_tray_report_unheard()
        assert measurement.verdict == "unknown"
        assert "would not load" in measurement.note

    def test_a_checkout_that_will_not_parse_cannot_read_as_one_caller(
        self, monkeypatch, real_services
    ):
        """``-1`` rather than a count, so a broken tree is never ``match``."""
        from sysadmin import snag_claims

        monkeypatch.setattr(snag_claims, "_parse", lambda _path: None)
        assert snag_claims._load_tray_config_call_sites() == -1
        assert check_tray_report_unheard().verdict == "mismatch"


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


class TestTheDuplicateIngestCheck:
    """``SNAG-LOG-014`` — and the reason it cannot read an empty table.

    This entry's population empties by *retention* on 2026-09-16 with
    nothing done, so "no duplicates" and "the entry is dead" are only the
    same statement while the source still has rows.  The witness is those
    rows, and it is what keeps the check from reporting a refutation the
    calendar wrote — ``SNAG-LOG-013``'s reading, refused a fourth time.
    """

    def test_it_holds_against_the_live_table(self):
        assert snag_claims.check_duplicate_ingest_residue().verdict == "match"

    def test_a_removed_pair_refutes_the_entry_while_the_source_has_rows(self):
        with patch.object(
            snag_claims, "query_one", side_effect=[(0, ""), (199, ""), (0, ""), (0, "")]
        ):
            measurement = snag_claims.check_duplicate_ingest_residue()
        assert measurement.verdict == "mismatch"
        assert "has been removed or has aged out" in measurement.note

    def test_an_emptied_source_is_unknown_and_never_a_refutation(self):
        """The whole reason the row count is read at all.

        Without it a table retention had emptied answers ``mismatch``,
        which is the calendar closing an entry nobody judged.
        """
        with patch.object(
            snag_claims, "query_one", side_effect=[(0, ""), (0, ""), (0, ""), (0, "")]
        ):
            measurement = snag_claims.check_duplicate_ingest_residue()
        assert measurement.verdict == "unknown"
        assert "retention has emptied" in measurement.note

    def test_a_pair_elsewhere_is_reported_rather_than_folded_in(self):
        """The entry's strongest claim is that these are the *only* ones.

        Scoping the count to the source it names would make that claim
        unmeasurable by the check written to measure it, and would hide
        a second occurrence of the mechanism.

        It also carries the **equal-count** case, which is the live one:
        both keys agreeing means nothing diverged, so the divergence
        clause must be absent rather than reading "0 of them".  A count
        of nought announced as a finding is the sentence
        ``SNAG-DOCS-006`` closed one register over.
        """
        with patch.object(
            snag_claims, "query_one", side_effect=[(3, ""), (199, ""), (3, ""), (1, "")]
        ):
            measurement = snag_claims.check_duplicate_ingest_residue()
        assert measurement.verdict == "match"
        note = " ".join(measurement.detail)
        assert "1 of them outside" in note
        assert "agree on the record and not on the message" not in note

    def test_it_counts_groups_and_not_rows(self):
        """One record ingested three times is one fault, not two.

        Asserted at the statement, because the difference is invisible
        in the two-row population this box actually has.
        """
        assert "HAVING count(*) > 1" in snag_claims.DUPLICATE_GROUPS_SQL
        assert "GROUP BY source, logged_at, message" in snag_claims.DUPLICATE_GROUPS_SQL

    def test_the_verdict_is_the_entrys_narrow_key_and_not_the_wide_one(self):
        """A coincidence must not hold a dead entry open.

        Two genuinely distinct records landing in one microsecond share
        the record identity and disagree about the message.  If that
        drove the verdict, ``match`` would survive the day the real pair
        aged out — the calendar keeping an entry alive, which is the
        mirror of the reading this check exists to refuse.

        Measured margin rather than assumed: the tightest gap between
        two distinct records from one source on this box is 3 µs.
        """
        with patch.object(
            snag_claims, "query_one", side_effect=[(0, ""), (199, ""), (4, ""), (4, "")]
        ):
            measurement = snag_claims.check_duplicate_ingest_residue()
        assert measurement.verdict == "mismatch"

    def test_a_divergently_parsed_duplicate_is_named_rather_than_silent(self):
        """The wide count above the narrow one is this entry's own shape.

        Before ``SNAG-LOG-008``'s backfill the two copies carried
        different ``message`` values — one envelope, one fragment — so a
        ``message``-keyed group could not see them, and did not, for
        eleven days.  A second occurrence elsewhere would most likely
        take that form too, the mechanism needing a restart and a restart
        being when a declaration changes.
        """
        with patch.object(
            snag_claims, "query_one", side_effect=[(2, ""), (199, ""), (5, ""), (3, "")]
        ):
            measurement = snag_claims.check_duplicate_ingest_residue()
        note = " ".join(measurement.detail)
        assert "3 of them agree on the record and not on the message" in note

    def test_the_record_identity_omits_the_column_the_backfill_rewrote(self):
        """Asserted at the statement, because today the two keys agree.

        Across 235,230 retained rows and 9 sources, zero groups share a
        ``(source, logged_at)`` while disagreeing about ``message`` — so
        no live population can witness this, and only the source can.
        ``message`` is mutable (``SNAG-LOG-008`` rewrote it);
        ``logged_at`` is the journal's own ``__REALTIME_TIMESTAMP``.
        """
        for statement in (
            snag_claims.DUPLICATE_RECORDS_SQL,
            snag_claims.DUPLICATE_GROUPS_ELSEWHERE_SQL,
        ):
            assert "GROUP BY source, logged_at HAVING" in statement
            assert "message" not in statement

    def test_a_silent_database_is_unknown(self):
        silent = (None, "the database did not answer")
        with patch.object(snag_claims, "query_one", return_value=silent):
            assert snag_claims.check_duplicate_ingest_residue().verdict == "unknown"


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
        emitted = {entry.port: snag_claims.generated_health_url(entry.port) for entry in population}
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
                if by_name[e.name].guess_wrong and not by_name[e.name].declared_path.strip("/")
            ],
        }
        return cls._MEASURED

    @staticmethod
    @contextlib.contextmanager
    def _population(entries):
        with patch.object(snag_claims, "health_path_population", return_value=(list(entries), "")):
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
        """ "Declaring a port and a unit", read off the file.

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
class TestTheUnsweptPortCheck:
    """``SNAG-ESTATE-009``'s check — the sweep's age, driven rather than counted.

    The entry is about a dev server started *between* sweeps, so its
    population is which side of a six-hour boundary somebody opened an
    editor on.  Nothing below counts a row.  What is driven is the one
    fact that makes the window exist: ``_attribution`` reads a single
    stored ``unit_audits`` row, so a sweep naming one of two ports **is**
    a sweep taken before the second listener started.

    Every falsification is a stand-in **modelling a landed fix** — the
    sweep learning to see the port, the judge quietening it unattributed,
    and the row gaining an annotation with the rung untouched — plus the
    two ways the instrument itself can stop discriminating.
    """

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _payload():
        return {
            "findings": [snag_claims.quieten_finding(port) for port in snag_claims.UNSWEPT_PORTS]
        }

    @classmethod
    def _titles(cls) -> dict[int, str]:
        """The two titles, off the producer — never a format string here."""
        from sysadmin.core.config import get_config
        from sysadmin.estate.judgements import judge_audit_findings
        from sysadmin.units.ports import attribution_from_blob

        judged = judge_audit_findings(
            cls._payload(),
            get_config().agents.estate_judge.port_breach_max_rows,
            attribution_from_blob(
                {"transient_ports": {snag_claims.UNSWEPT_HOLDER: [snag_claims.SWEPT_PORT]}},
                datetime.now(UTC).isoformat(),
            ),
        )
        return {judgement.details["port"]: judgement.title for judgement in judged}

    @classmethod
    def _surviving_rows(cls) -> int:
        """Rows on the live box this probe could have left.

        By **title**, for the reason its sibling's guard had to be
        corrected to: this probe opens no row by hand at all, so every
        row it can leak is one it *raised*, wearing the estate's own
        ``summary`` rather than :data:`PROBE_MESSAGE`.  A guard keyed on
        the probe's own message would here be blind to the whole
        population.
        """
        titles = ", ".join(f"'{title}'" for title in cls._titles().values())
        count, problem = snag_claims.query_one(
            f"SELECT count(*) FROM sysadmin.alerts WHERE title IN ({titles})"
        )
        assert not problem, problem
        return int(count or 0)

    @staticmethod
    def _surviving_sweeps() -> int:
        count, problem = snag_claims.query_one(
            "SELECT count(*) FROM sysadmin.unit_audits "
            f"WHERE findings::text LIKE '%{snag_claims.UNSWEPT_HOLDER}%'"
        )
        assert not problem, problem
        return int(count or 0)

    @staticmethod
    @contextlib.contextmanager
    def _fix(mutate):
        """Run the real ``_execute``, then apply ``mutate`` — a landed fix.

        After the production loop rather than instead of it, so the run
        under test is the real one and the only difference is what a fix
        would have done to its output.  A stand-in replacing ``_execute``
        outright would prove the check notices an edit to itself.
        """
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._execute

        async def patched(self, session):
            result = await real(self, session)
            await mutate(session)
            return result

        with patch.object(EstateJudgeAgent, "_execute", patched):
            yield

    @classmethod
    async def _row(cls, session, port: int):
        from sqlalchemy import select

        from sysadmin.core.models.alert import Alert, unresolved

        return (
            (
                await session.execute(
                    select(Alert).where(
                        Alert.title == cls._titles()[port],
                        unresolved(),
                    )
                )
            )
            .scalars()
            .first()
        )

    # -- the instruments -------------------------------------------------

    def test_the_probe_writes_nothing_that_survives(self):
        """What makes writing to the live database allowable, asserted twice.

        Before as well as after, because a probe that had been leaking
        rows for a week would satisfy an "after" assertion on its own.
        """
        assert self._surviving_rows() == 0
        assert self._surviving_sweeps() == 0
        reading, problem = snag_claims.unswept_judgement_reading()
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
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "unknown"
        assert "would not run against the live database" in measurement.note
        assert self._surviving_rows() == 0
        assert self._surviving_sweeps() == 0

    def test_the_probes_own_strings_cannot_become_an_injection(self):
        assert "'" not in snag_claims.UNSWEPT_HOLDER
        assert "\\" not in snag_claims.UNSWEPT_HOLDER

    def test_it_shares_no_port_and_no_holder_with_the_other_drive(self):
        """Rule 4, and a leak has to name which drive left it.

        The two write to the same two tables against the same database.
        Sharing a port would let one deduplicate against the other's
        row; sharing the holder string would make a surviving sweep
        ambiguous about which drive failed to roll back.

        The counterpart was ``SNAG-ESTATE-010``'s probe in this module
        until 2026-08-28 and is ``tests/test_quietened_judgement_live.py``
        now.  It moved and the collision did not, so the assertion
        follows it across the boundary rather than retiring with the
        check — the two are still one script's worth of rows in one
        table.
        """
        from tests import test_quietened_judgement_live as quietened

        assert not set(snag_claims.UNSWEPT_PORTS) & set(quietened.PORTS)
        assert snag_claims.UNSWEPT_HOLDER != quietened.HOLDER

    def test_the_probe_ports_hold_no_live_row(self):
        """The titles it raises must be nobody else's fault."""
        assert self._surviving_rows() == 0

    def test_the_instrument_is_the_agents_own_execute(self):
        """Driven, not reimplemented — one call, one session."""
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._execute
        sessions = []

        async def counting(self, session):
            sessions.append(session)
            return await real(self, session)

        with patch.object(EstateJudgeAgent, "_execute", counting):
            reading, problem = snag_claims.unswept_judgement_reading()
        assert not problem, problem
        assert reading is not None and len(sessions) == 1

    def test_the_attribution_is_read_through_the_agent_twice(self):
        """The production reader is *called*, not stood in for.

        Written after a stand-in swapped the reading's call for a local
        ``attribution_from_blob(blob, observed_at)`` and every assertion
        still passed — the blob is what the row holds, so the two agree
        on every value and only the call itself separates them.  Twice:
        once inside ``_execute`` for the judgement, once after it for the
        report.  They cannot disagree — both read the newest
        ``unit_audits`` row and the transaction writes no second one —
        which is exactly why the count is the thing worth asserting.
        """
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._attribution
        calls = []

        async def counting(self, session):
            out = await real(self, session)
            calls.append(out)
            return out

        with patch.object(EstateJudgeAgent, "_attribution", counting):
            reading, problem = snag_claims.unswept_judgement_reading()
        assert not problem, problem
        assert reading is not None and len(calls) == 2
        assert calls[0].observed_at == calls[1].observed_at

    def test_the_probes_sweep_is_the_newest_on_the_box(self):
        """Or it is not holding the variable at all.

        ``_attribution`` reads **one** row — the newest — so a probe
        whose row is not newest measures the estate's real sweep instead.
        Driven when the row was backdated by one ``scan_interval_hours``
        to model the entry's timing: the box's own sweep, 1.21 h old, won,
        the swept port came back unattributed and the witness refused.
        The age is reported for that reason and asserted here, because
        the failure it guards against is a real sweep landing mid-drive.
        """
        reading, problem = snag_claims.unswept_judgement_reading()
        assert not problem, problem
        assert reading is not None
        assert reading.attribution_age_hours is not None
        assert reading.attribution_age_hours < 0.01

    def test_the_stored_sweep_names_exactly_one_of_the_two_ports(self):
        """The precondition, read at ``_attribution`` rather than at the blob.

        The blob is this module's; what the claim is about is what the
        production reader makes of it, and those are two facts until
        something drives the second.
        """
        reading, problem = snag_claims.unswept_judgement_reading()
        assert not problem, problem
        assert reading is not None
        assert isinstance(reading.attributed_swept, dict)
        assert reading.attributed_swept["transient"] is True
        assert reading.attributed_unswept is None

    def test_only_the_findings_surface_is_read(self):
        """The four declined surfaces, asserted at the sweep that consumes them."""
        from sysadmin.estate.agent import EstateJudgeAgent

        real = EstateJudgeAgent._resolve_gone
        seen = []

        async def recording(self, session, open_alerts, current, read):
            seen.append(set(read))
            return await real(self, session, open_alerts, current, read)

        with patch.object(EstateJudgeAgent, "_resolve_gone", recording):
            reading, problem = snag_claims.unswept_judgement_reading()
        assert not problem, problem
        assert seen == [{"audit_findings"}]

    def test_the_quiet_rung_is_not_read_off_the_run(self):
        """Rule 3, driven at the state that would hide a broken witness.

        If ``quiet`` were taken from the swept row the run produced, the
        witness could never fail — the expectation would follow the
        measurement wherever it went.  So the swept row is moved to a
        rung nothing computes, and the check has to notice.
        """

        async def mangle(session):
            row = await self._row(session, snag_claims.SWEPT_PORT)
            assert row is not None
            row.severity = "critical"
            await session.flush()

        with self._fix(mangle):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "unknown"
        assert "did not raise port" in measurement.note

    # -- the verdicts ----------------------------------------------------

    def test_the_check_holds_on_this_box(self):
        measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "match"
        assert any(
            f"port {snag_claims.UNSWEPT_PORT} is not named by it" in line
            for line in measurement.detail
        )
        assert any(
            f"port {snag_claims.SWEPT_PORT} is named by the stored sweep" in line
            for line in measurement.detail
        )

    # -- the widening the fix forced ------------------------------------

    def test_a_port_only_difference_is_not_an_annotation(self):
        """No false positive: the pair is *allowed* to differ in the port.

        The two rows legitimately carry different ``port``,
        ``fingerprint`` and ``audit_summary`` — three spellings of one
        number.  Exempting them by name would be the second statement of
        a producer's fact this comparison exists to avoid, so each row is
        rendered with its **own** port made opaque instead.
        """
        shape = snag_claims._detail_shape
        swept = {"port": 65008, "fingerprint": "ports:port 65008:x", "summary": "port 65008 up"}
        unswept = {"port": 65009, "fingerprint": "ports:port 65009:x", "summary": "port 65009 up"}
        assert shape(swept, 65008) == shape(unswept, 65009)

    def test_a_value_only_annotation_is_seen(self):
        """The widening, falsified against the comparison it replaced.

        ``annotated`` compared detail **key sets** until 2026-08-29 and
        was blind to the better half of its own limb: an annotation
        added to *every* row with a value that varies leaves the key
        sets identical.  That is the shape the fix took — a key present
        only sometimes is ``ports_checked``'s collapse one level down —
        so the check would have reported ``match`` over a landed fix,
        which is worse than flipping.
        """
        shape = snag_claims._detail_shape
        swept = {"port": 65008, "attribution": {"reading": "transient"}}
        unswept = {"port": 65009, "attribution": {"reading": "unswept"}}
        assert {k for k, _ in shape(swept, 65008)} == {k for k, _ in shape(unswept, 65009)}
        assert shape(swept, 65008) != shape(unswept, 65009)

    def test_the_holder_is_exempt_because_it_owns_a_limb(self):
        """Counting it here would make the note state one fact twice."""
        shape = snag_claims._detail_shape
        swept = {"port": 65008, "holder": {"unit": "x.scope", "transient": True}}
        unswept = {"port": 65009, "holder": None}
        assert shape(swept, 65008) == shape(unswept, 65009)

    def test_the_pair_differs_only_in_the_blob(self):
        """Both ports judged alike once both are attributed, pinned purely."""
        from sysadmin.core.config import get_config
        from sysadmin.estate.judgements import judge_audit_findings
        from sysadmin.units.ports import attribution_from_blob

        judged = judge_audit_findings(
            self._payload(),
            get_config().agents.estate_judge.port_breach_max_rows,
            attribution_from_blob(
                {"transient_ports": {snag_claims.UNSWEPT_HOLDER: list(snag_claims.UNSWEPT_PORTS)}},
                datetime.now(UTC).isoformat(),
            ),
        )
        assert {j.details["port"] for j in judged} == set(snag_claims.UNSWEPT_PORTS)
        assert len({j.severity for j in judged}) == 1
        for judgement in judged:
            assert judgement.details["holder"]["transient"] is True

    def test_a_judge_that_runs_ss_itself_is_a_mismatch(self):
        """The entry's first rejected fix, driven whole.

        Closing the window exactly — by any route that gets the judge a
        live look — arrives here as an attribution naming the port the
        stored sweep did not.  This one **composes** limbs rather than
        isolating one: a dev server found live attributes as transient,
        so the rung and the holder move together, and no single-limb
        falsification can break it.  Each limb has its own scenario
        below and beside it; this asserts that the fix the entry
        actually considered is reported, and reported as both.
        """
        from sysadmin.estate.agent import EstateJudgeAgent
        from sysadmin.units.ports import attribution_from_blob

        async def sees_everything(self, session):
            return attribution_from_blob(
                {"transient_ports": {snag_claims.UNSWEPT_HOLDER: list(snag_claims.UNSWEPT_PORTS)}},
                datetime.now(UTC).isoformat(),
            )

        with patch.object(EstateJudgeAgent, "_attribution", sees_everything):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "mismatch"
        assert "_attribution named it" in measurement.note
        assert "it is judged" in measurement.note

    def test_an_acquired_holder_alone_is_a_mismatch(self):
        """The holder limb, isolated — and the state that isolates it is real.

        A live look does not have to find a dev server.  A port held by
        an ordinary unit comes back **non-transient**, so
        ``_breach_severity`` leaves the rung exactly where it was and
        only ``details['holder']`` moves — and the row has stopped being
        indistinguishable from an ordinary unclaimed listener, which is
        what the entry claims the window prevents.  The swept port keeps
        its transient holder, or there would be no witness to judge
        either verdict against.
        """
        from sysadmin.estate.agent import EstateJudgeAgent
        from sysadmin.units.ports import attribution_from_blob

        async def one_real_unit(self, session):
            return attribution_from_blob(
                {
                    "unit_ports": {"system:probe-stand-in.service": [snag_claims.UNSWEPT_PORT]},
                    "transient_ports": {snag_claims.UNSWEPT_HOLDER: [snag_claims.SWEPT_PORT]},
                },
                datetime.now(UTC).isoformat(),
            )

        with patch.object(EstateJudgeAgent, "_attribution", one_real_unit):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "mismatch"
        assert "details['holder'] is" in measurement.note
        assert "it is judged" not in measurement.note
        assert "its details differ" not in measurement.note

    def test_quietening_an_unattributed_breach_is_a_mismatch(self):
        """The second, and it leaves ``_attribution`` exactly where it was.

        A judge that decided an unclaimed listener inside a fresh-sweep
        window is worth the quiet rung would land here — the holder stays
        ``None`` and only the rung moves.
        """
        from sysadmin.estate import judgements

        quiet = judgements.TRANSIENT_HOLDER_SEVERITY
        with patch.object(judgements, "_breach_severity", lambda holder: quiet):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "mismatch"
        assert f"it is judged {quiet} rather than" in measurement.note
        assert "_attribution now holds" not in measurement.note

    def test_an_annotation_alone_no_longer_moves_the_verdict(self):
        """The third limb, **inverted on 2026-08-29 rather than deleted**.

        It asserted that a row gaining something about the evidence's
        window is a fix, and it was right when written: the entry's
        claim is indistinguishability, and ``holder['observed_at']`` —
        the age the "Why P3" bullet says already ships — is vacuous for
        an unattributed port, since ``holder`` is ``None``.

        That annotation has landed.  ``details['attribution']`` says
        what the sweep knew about every breached port, so this limb is
        true from here on and can never again say anything about the
        window it was pointed at.  It is out of :attr:`UnsweptReading.
        reached` and out of the note, and the check now measures the
        rung and the holder — the entry's live mechanism, which the
        annotation deliberately did not move.

        Kept and inverted because deleting it would take the record of
        what the limb was for along with it, which is the trap Session
        115 named when a test asserting a defect as correct behaviour
        had to be turned round rather than removed.
        """

        async def annotate(session):
            row = await self._row(session, snag_claims.UNSWEPT_PORT)
            assert row is not None
            row.details = {
                **(row.details or {}),
                "attribution_observed_at": datetime.now(UTC).isoformat(),
            }
            await session.flush()

        with self._fix(annotate):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "match"
        assert "its details differ" not in (measurement.note or "")
        # Out of the verdict and still reported: the extra key reaches
        # the detail, which is where a standing observation belongs.
        assert any("attribution_observed_at" in line for line in measurement.detail)

    def test_without_the_witness_the_verdict_is_unknown(self):
        """The control, driven at the state that would otherwise read ``match``.

        A judge whose attribution never arrives raises **both** ports
        loudly and unattributed, so every assertion the ``match`` branch
        makes about the unswept port is still true — and the reason has
        nothing to do with the sweep's age.  Only the witness separates
        them.
        """
        from sysadmin.estate.agent import EstateJudgeAgent
        from sysadmin.units.ports import PortAttribution

        async def blind(self, session):
            return PortAttribution()

        with patch.object(EstateJudgeAgent, "_attribution", blind):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "unknown"
        assert "rather than evidence about the sweep's age" in measurement.note
        assert any(
            f"port {snag_claims.UNSWEPT_PORT} is not named by it: _attribution holds None" in line
            for line in measurement.detail
        )

    def test_a_family_with_no_quieter_rung_is_unknown(self):
        """Session 57 reverted: this entry is a limit on a fix that is gone.

        Reached before anything is written, so it also pins that the
        probe declines the database when it already knows it would
        measure nothing.
        """
        from sysadmin.estate import judgements

        with patch.object(judgements, "DEFAULT_SEVERITY", judgements.TRANSIENT_HOLDER_SEVERITY):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "unknown"
        assert "no quieter rung" in measurement.note
        assert self._surviving_rows() == 0

    def test_a_rolled_up_payload_is_unknown(self):
        """One row for two ports is not the pair this probe holds constant."""
        from sysadmin.core.config import get_config

        with patch.object(get_config().agents.estate_judge, "port_breach_max_rows", 1):
            measurement = check_unswept_port_is_loud()
        assert measurement.verdict == "unknown"
        assert "rather than one row per port at one rung" in measurement.note

    def test_the_check_names_the_entry_and_the_entry_names_the_check(self):
        check = CHECKS["unswept_port_is_loud"]
        assert check.snag == "SNAG-ESTATE-009"
        entries, problem = snag_claims.load_entries()
        assert not problem, problem
        entry = next(e for e in entries if e.snag_id == check.snag)
        assert "unswept_port_is_loud" in entry.markers


class TestTheUnmarkedSentenceCheck:
    """``SNAG-ESTATE-012``'s check — the twentieth, and the one that measures a silence.

    Every other check here looks for something and reports whether it is
    there.  This one reports that a sentence reaches **nothing**, which is
    a claim about an absence — and an absence is what a broken probe
    produces for free.  So almost all of these tests are about the
    instruments rather than about the entry: the witness that separates
    "the reader read the region and found no claim" from "the reader read
    nothing", and the two independent ways a landed fix could show up.

    Each candidate fix is driven as a **real stand-in** wrapping the real
    :func:`sysadmin.ops_claims.check_all`, never as a literal saying the
    fix landed, because the interesting verdicts are the ones that tell
    four differently-shaped fixes apart.
    """

    # -- the specimen ----------------------------------------------------

    def test_the_sentences_are_the_entrys_own(self):
        """The specimens are quoted from the entry, not invented for the check.

        The defect is a human writing an English claim into the block, so
        a sentence this repository made up for the occasion would be
        measuring a hypothetical one.  ``TestTheExpiryCheck``'s producer
        stamp rule, one entry over.
        """
        body = SNAG_PATH.read_text(encoding="utf-8")
        for sentence in snag_claims.INVISIBLE_SENTENCES:
            assert sentence in body, sentence

    def test_no_specimen_sentence_matches_a_claim_pattern(self):
        """A specimen a pattern reaches is not a specimen of this entry.

        Driven at the real :data:`~sysadmin.ops_claims.CLAIM_PATTERNS`
        rather than asserted from the text, so a pattern added later that
        happens to reach one of the three fails *here* — where it reads
        as "the specimen went stale" — rather than in the check, where it
        would read as a landed fix.
        """
        for sentence in snag_claims.INVISIBLE_SENTENCES:
            for key, pattern in ops_claims.CLAIM_PATTERNS.items():
                assert not re.search(pattern, ops_claims.flatten(sentence)), (key, sentence)

    def test_the_marked_half_is_read_and_its_marker_with_it(self):
        """The witness itself, driven at the real reader.

        Both halves: the figure comes back out of the prose, and no
        ``unclaimed:`` finding stands beside it — which is
        ``read_markers`` having reached the marker.  A probe whose
        witness was broken would report every entry in this family as
        holding, so the witness is tested before anything that leans on
        it.
        """
        claims, problem = snag_claims.ops_report(snag_claims.invisible_document())
        assert not problem, problem
        assert snag_claims.witness_problem(claims) == ""

    def test_the_specimen_region_ends_at_the_quick_status_table(self):
        """The document is cut by the module under test, not by this check.

        :func:`~sysadmin.ops_claims.printed_region` returning ``None``
        would make every claim unreadable for a reason that has nothing
        to do with the entry, so the specimen's shape is driven rather
        than assumed.
        """
        region = ops_claims.printed_region(snag_claims.invisible_document())
        assert region is not None
        assert "Quick Status" in region

    def test_every_specimen_has_a_word_the_baseline_lacks(self):
        """The quotation instrument must have something to look for.

        **This is the test that moved a constant.**  At five characters
        the middle specimen yielded nothing — ``8400`` is four, and
        ``answers`` is already the subject of the ``/health`` claim — so
        one of the three was covered by the projection alone and nothing
        said so.  An instrument with an empty population that reports
        silence is this entry's own symptom arriving inside its own
        check.
        """
        base = snag_claims.invisible_document()
        claims, problem = snag_claims.ops_report(base)
        assert not problem, problem
        seen = frozenset(snag_claims.INVISIBLE_WORD_RE.findall(base)) | frozenset(
            word
            for claim in claims
            for word in snag_claims.INVISIBLE_WORD_RE.findall(snag_claims.claim_text(claim))
        )
        for sentence in snag_claims.INVISIBLE_SENTENCES:
            distinctive = frozenset(snag_claims.INVISIBLE_WORD_RE.findall(sentence)) - seen
            assert distinctive, sentence

    # -- the box ---------------------------------------------------------

    def test_it_holds_against_the_live_reader(self):
        """The entry as it stands: nothing reaches an unmarked sentence."""
        measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "match"
        assert all("absent from every family" in line for line in measurement.detail[1:])

    def test_the_witness_is_reported_as_evidence(self):
        """The silence is only ever served beside the thing that discriminates it."""
        measurement = check_unmarked_sentence_invisible()
        assert measurement.detail[0].startswith("witness:")
        assert f"routes={snag_claims.INVISIBLE_ROUTES}" in measurement.detail[0]

    # -- the witness, falsified ------------------------------------------

    def test_a_reader_that_parsed_nothing_is_unknown_not_a_match(self):
        """The founding reason this check has a witness at all.

        A reader that stopped cutting the region reports the unmarked
        sentence **exactly** as a working reader does, so a probe
        asserting silence alone would report this entry holding hardest
        on the morning ``printed_region`` broke.
        """
        with patch.object(ops_claims, "printed_region", lambda document: None):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "unknown"
        assert "says nothing" in measurement.note

    def test_a_broken_marker_reader_is_unknown_too(self):
        """The second half of the witness, which fails apart from the first.

        ``read_claim`` reaching the prose and ``read_markers`` reaching
        the marker beside it are two facts.  The marker half is the one
        both refused remedies would have had to extend, so a probe blind
        to it would keep reporting ``match`` through the fix it exists to
        notice.
        """
        with patch.object(ops_claims, "read_markers", lambda region: []):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "unknown"
        assert "unclaimed" in measurement.note

    def test_a_reader_that_raises_is_unknown(self):
        """A reader that did not run is not a reader that found nothing."""

        def raises(path=None, now=None):
            raise RuntimeError("the region moved")

        with patch.object(ops_claims, "check_all", raises):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "unknown"
        assert "RuntimeError" in measurement.note

    # -- the fixes, each driven ------------------------------------------

    @staticmethod
    def _unmarked_paragraphs(path):
        """The specimen's blockquote lines that carry no marker."""
        region, _ = ops_claims.load_region(path)
        return [
            line[2:]
            for line in (region or "").splitlines()
            if line.startswith("> ") and "<!--" not in line
        ]

    def test_the_first_refused_remedy_is_a_mismatch(self):
        """Remedy 1: every blockquote paragraph must carry a marker.

        The entry refuses it because it turns the ranked recommendation
        and the blocked list into claims they are not — but if it landed,
        this check must say so.  Note that the finding **never quotes the
        sentence**, so the word search cannot see it and only the
        projection can: this is the falsification that justifies having
        two instruments.
        """
        real = ops_claims.check_all

        def remedy(path=None, now=None):
            claims = list(real(path, now))
            claims.extend(
                ops_claims.Claim(
                    f"unmarked:{index}",
                    f"Unmarked paragraph {index}",
                    "convention",
                    None,
                    None,
                    "unknown",
                    "carries no marker",
                )
                for index, _ in enumerate(self._unmarked_paragraphs(path))
            )
            return claims

        with patch.object(ops_claims, "check_all", remedy):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "mismatch"
        # ``unmarked:0`` is the specimen's own opening line, which carries
        # no marker in *either* drive and is therefore in the baseline — so
        # the key the sentence adds is the second one.  The projection
        # compares key sets rather than counting them for exactly this
        # reason: a probe asserting "the fix produced a finding" would pass
        # on a finding the sentence had nothing to do with.
        assert "the report gained unmarked:1" in measurement.note

    def test_a_fix_that_only_quotes_the_sentence_is_a_mismatch(self):
        """Remedy 2's shape: folded into an existing claim, adding no key.

        The mirror of the test above, and the reason the projection
        alone is not enough — the key set is unmoved and every
        ``documented`` is unchanged, so the only thing that has happened
        is that a note now carries words it could only have got from the
        sentence.
        """
        real = ops_claims.check_all

        def remedy(path=None, now=None):
            extra = self._unmarked_paragraphs(path)
            return [
                ops_claims.Claim(
                    claim.key,
                    claim.subject,
                    claim.kind,
                    claim.documented,
                    claim.measured,
                    claim.verdict,
                    f"{claim.note} unchecked beside it: {'; '.join(extra)}",
                    claim.detail,
                )
                if claim.key == "routes" and extra
                else claim
                for claim in real(path, now)
            ]

        with patch.object(ops_claims, "check_all", remedy):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "mismatch"
        assert "quotes the sentence" in measurement.note

    def test_a_pattern_family_that_grows_to_reach_it_is_a_mismatch(self):
        """The third shape, and the only one needing no wrapper at all.

        A ``CLAIM_PATTERNS`` entry that reaches a specimen makes
        ``check_markers`` report it as an unclaimed figure, which is the
        convention doing exactly what it was built to do — and it means
        the sentence has stopped being one nothing can reach.
        """
        grown = {**ops_claims.CLAIM_PATTERNS, "port": r"(\d{4}) answers"}
        with patch.object(ops_claims, "CLAIM_PATTERNS", grown):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "mismatch"
        assert "unclaimed:port" in measurement.note

    def test_a_sentence_that_collides_with_the_marked_figure_is_a_mismatch(self):
        """The fourth shape, and the one that corrected the check's own ordering.

        ``read_claim`` refuses two distinct matches rather than resolving
        them, so a sentence restating the block's figure differently
        makes an existing claim stop reading the block.  The first draft
        re-witnessed every drive and reported this as *"the probe could
        not be driven"* — ``unknown`` for a sentence that had visibly
        been read, which is the wrong verdict in the dangerous
        direction.
        """
        with patch.object(
            snag_claims,
            "INVISIBLE_SENTENCES",
            ("the table above should read **9 routes**",),
        ):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "mismatch"
        assert "stopped reading the block" in measurement.note

    # -- the box moving underneath the probe -----------------------------

    def test_a_figure_that_merely_moves_is_unknown_not_a_mismatch(self):
        """``open_titles`` counts live rows, so two drives can honestly disagree.

        Reporting that as a landed fix would be reporting this
        repository's own alert traffic.  The direction rule is what makes
        the split safe: a sentence can add readability or remove it, and
        it cannot restate a figure the block already carries as a
        different one.
        """
        real = ops_claims.check_all
        drives = itertools.count()

        def noisy(path=None, now=None):
            index = next(drives)
            return [
                ops_claims.Claim(
                    claim.key,
                    claim.subject,
                    claim.kind,
                    f"{index} named",
                    claim.measured,
                    claim.verdict,
                    claim.note,
                    claim.detail,
                )
                if claim.key == "open_titles"
                else claim
                for claim in real(path, now)
            ]

        with patch.object(ops_claims, "check_all", noisy):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "unknown"
        assert "open_titles" in measurement.note
        assert "cannot isolate the sentence" in measurement.note

    def test_a_dead_quotation_instrument_is_declared(self):
        """Half the reach gone is reported, never served as silence.

        Driven at a specimen made entirely of words the baseline report
        already uses, so nothing survives the subtraction.  The
        projection still covers it — which is why the whole check falls
        to ``unknown`` only when *no* specimen is quotable.
        """
        with patch.object(snag_claims, "INVISIBLE_SENTENCES", ("the block claim state",)):
            measurement = check_unmarked_sentence_invisible()
        assert measurement.verdict == "unknown"
        assert "quotation instrument cannot look" in measurement.note


class TestTheTimerAgentCheck:
    """``SNAG-SVC-002``'s check — the twenty-first, and the third on a synthetic subject.

    The entry has been runner-up three times and rule 1 is why.  The
    obvious check measures the disjointness its second bullet reports —
    no agent on this box is a systemd timer, so nothing reaches both
    families — and that is a property of *this box*: one scheduled job
    moved to a ``oneshot`` + ``.timer``, which ``monitorable-project.md``
    requires of every new one, and the check flips to "refuted" with
    nobody having touched either module.

    So the mechanism is reproduced.  Most of these tests are about the
    instruments rather than about the entry, and every candidate fix is
    driven as a **real stand-in** wrapping the real producers rather than
    as a literal saying a fix landed — because the verdicts worth having
    are the ones that tell three differently-shaped fixes apart, and one
    of those fixes is the one the entry **forbids**.
    """

    # -- the population the naive check would have measured --------------

    def test_no_scheduled_agent_on_this_box_is_a_systemd_timer(self):
        """Rule 1's founding condition for this entry, measured rather than quoted.

        If this ever fails, the entry's population has stopped being
        empty and a *population* check would become possible — but it
        would also start reporting the entry refuted the day somebody
        renamed a unit, which is why the check does not use one.  It
        fails here, where it reads as "the box moved", rather than in the
        check, where it would read as a landed fix.
        """
        from sysadmin.monitor.self_monitor import agent_schedules
        from sysadmin.monitor.services import load_services

        # The file, not the singleton: the suite does not prime it, and a
        # singleton that answers "no services" would pass this test by
        # having measured nothing.
        services = load_services(REPO_ROOT / "services.yaml")
        timers = {entry.name for entry in services.services if entry.kind == "timer"}
        agents = set(agent_schedules(get_config()))
        assert timers, "no timers are declared at all — the probe's subject has no analogue"
        assert not (timers & agents)

    # -- the instruments -------------------------------------------------

    def test_the_two_thresholds_are_the_same_number_today(self):
        """The entry's stated mitigation, pinned at the live config.

        ``timer_stale_multiplier`` *is* ``stall_grace_multiplier``, which
        is what makes one elapsed value cross both thresholds — so the
        two families do not merely both *have* an opinion, they form it
        at the same moment.  A divergence does not break the probe (it
        takes the later of the two) and it does weaken the entry's own
        mitigation, so it is reported here rather than silently absorbed.
        """
        config = get_config()
        assert (
            config.agents.sysadmin.service_actions.timer_stale_multiplier
            == config.self_monitor.stall_grace_multiplier
        )

    def test_the_fresh_fault_clears_both_thresholds_and_the_aged_one_clears_a_rung(self):
        """The arithmetic the whole check rests on, and the constant a falsification moved.

        Three conditions, and the middle one is the defect that shipped
        in the first draft:

        1. the fresh fault is past **both** thresholds, or only one
           family speaks and half 1 is vacuous;
        2. it is *inside* ``escalate_after_hours``, or a rung clocked off
           the fault's own age — the only clock a stateless family has —
           is already loud at the fresh drive and the two drives read
           alike;
        3. the aged fault is past that gap, so such a rung has fired.
        """
        config = get_config()
        gap = config.self_monitor.escalate_after_hours * 3600
        interval = config.agents.sysadmin.health_check_interval_seconds
        overshoot = interval * snag_claims.PROBE_FRESH_OVERSHOOT_INTERVALS

        assert overshoot > 0
        assert overshoot < gap
        assert gap * snag_claims.PROBE_LADDER_MULTIPLE > gap

    def test_the_import_walk_sees_an_import_and_never_a_mention(self):
        """Rule 7's instrument, driven at two files that differ only in that.

        The distinction is not hypothetical here — see the next test.
        """
        with tempfile.TemporaryDirectory() as tmp:
            joins = Path(tmp) / "joins.py"
            joins.write_text(
                "from sysadmin.monitor import stalls\n"
                "from sysadmin.monitor.service_recommendations import TimerSeries\n",
                encoding="utf-8",
            )
            mentions = Path(tmp) / "mentions.py"
            mentions.write_text(
                '"""Prose about sysadmin.monitor.stalls and about\n'
                'sysadmin.monitor.service_recommendations, naming neither as an import."""\n',
                encoding="utf-8",
            )
            for module in (snag_claims.STALL_MODULE, snag_claims.TIMER_ADVICE_MODULE):
                assert snag_claims.importers_of(module, [joins]) == [joins]
                assert snag_claims.importers_of(module, [mentions]) == []

    def test_the_advice_module_already_names_stalls_in_prose(self):
        """The reason a grep is the wrong instrument, measured at the real file.

        ``_timer_stale_row``'s own docstring says *"``self_monitor``/
        ``stalls.py`` owns 'has not run' for agents"* — the entry's
        sentence, written into the module the entry is about.  A text
        search reports the cross-reference as already existing and would
        refute this entry on the day it was filed; an ``ast`` walk over
        imports never sees a docstring.  Rule 7's founding argument
        arriving for the fourth time in this registry.
        """
        advice = REPO_ROOT / "sysadmin" / "monitor" / "service_recommendations.py"
        assert "stalls" in advice.read_text(encoding="utf-8")
        assert snag_claims.importers_of(snag_claims.STALL_MODULE, [advice]) == []

    def test_a_series_sampled_more_coarsely_than_the_box_yields_no_cadence(self):
        """Why the probe samples at the live check interval and not at the cadence.

        ``_series_holes`` calls any gap wider than ``SERIES_HOLE_FACTOR``
        intervals a hole in the *monitor's* series and discards every
        cadence sample spanning it.  A probe sampled at its own
        convenience would therefore observe no cadence, produce no
        ``timer_stale`` row, and report a silence it had manufactured —
        which is indistinguishable from the fix.
        """
        from sysadmin.monitor.service_recommendations import (
            _observed_cadence,
            _observed_fires,
        )

        config = get_config()
        interval = config.agents.sysadmin.health_check_interval_seconds
        cadence = float(config.agents.file_organiser.scan_interval_hours * 3600)
        now = datetime.now(UTC)
        from sysadmin.monitor.service_recommendations import MIN_CADENCE_SAMPLES

        fires = MIN_CADENCE_SAMPLES + 1 + snag_claims.PROBE_FIRE_SPARE

        fine = snag_claims.timer_agent_series(cadence, fires, 0.0, interval, "success", now)
        assert _observed_cadence(_observed_fires(fine.points), fine.points, interval) is not None

        coarse = snag_claims.timer_agent_series(
            cadence, fires, 0.0, int(interval * 4), "success", now
        )
        assert _observed_cadence(_observed_fires(coarse.points), coarse.points, interval) is None

    # -- the witnesses ---------------------------------------------------

    def test_a_schedule_that_ran_one_cadence_ago_is_not_stalled(self):
        """W1, alive.  The stall side reads the subject rather than defaulting."""
        reading, problem = snag_claims.timer_agent_reading()
        assert not problem, problem
        assert reading is not None
        assert reading.stall_title  # the *aged* subject is stalled

    def test_a_still_firing_timer_whose_run_failed_yields_a_row(self):
        """W2, alive, through the same call and the same confidence gate.

        Driven at a series that is *not* stale, so the witness cannot be
        satisfied by the row this check is looking for.
        """
        config = get_config()
        interval = config.agents.sysadmin.health_check_interval_seconds
        cadence = float(config.agents.file_organiser.scan_interval_hours * 3600)
        now = datetime.now(UTC)
        from sysadmin.monitor.service_recommendations import MIN_CADENCE_SAMPLES

        rows = snag_claims.timer_agent_rows(
            snag_claims.timer_agent_series(
                cadence,
                MIN_CADENCE_SAMPLES + 1 + snag_claims.PROBE_FIRE_SPARE,
                0.0,
                interval,
                "exit-code",
                now,
            ),
            interval,
            now,
        )
        kinds = {row.kind for row in rows}
        assert "timer_failed" in kinds
        assert "timer_stale" not in kinds

    def test_a_stall_side_that_cannot_tell_the_two_apart_is_unknown(self):
        """W1 broken: everything reads stalled, so the family's speech means nothing."""
        from sysadmin.monitor import self_monitor

        real = self_monitor.summarise_agent

        def always_stalled(*args, **kwargs):
            entry = dict(real(*args, **kwargs))
            entry["stalled"] = True
            return entry

        with patch.object(self_monitor, "summarise_agent", always_stalled):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "unknown"
        assert "cannot tell a working schedule from a stopped one" in result.note

    def test_an_unreachable_advice_family_is_unknown_and_names_both_readings(self):
        """W2 broken, and the note refuses to choose between two honest readings.

        A timer half that has been *removed* is the entry's own fix, and a
        probe whose series no longer satisfies the module is the probe's
        fault.  From here they are the same observation, so rule 5 applies
        — but the note names the first, because a reader who does not go
        and look would otherwise never learn that the fix may have landed.
        """
        from sysadmin.monitor import service_recommendations as advice

        with patch.object(advice, "_timer_rows", lambda *a, **k: []):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "unknown"
        assert "its timer half may have been removed" in result.note

    # -- the entry -------------------------------------------------------

    def test_one_schedule_reaches_both_families_today(self):
        """The mechanism, and the evidence is the two rows side by side."""
        result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "match", result.note
        evidence = "\n".join(result.detail)
        assert "agent stalled [warning -> critical]" in evidence
        assert "armed but has not fired" in evidence
        assert snag_claims.TIMER_AGENT_NAME in evidence

    def test_the_advice_family_ceding_is_the_fix_the_entry_names(self):
        """One family going quiet about the subject — ``stalls.py`` keeps the question."""
        from sysadmin.monitor import service_recommendations as advice

        with patch.object(advice, "_timer_stale_row", lambda *a, **k: None):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "mismatch"
        assert "the advice family no longer speaks" in result.note

    def test_the_stall_family_ceding_is_reported_as_the_wrong_direction(self):
        """The same fix taken the way the entry argues against.

        The ladder is the expensive half and it already exists in
        ``stalls.py``, so a fix that silenced *that* side would have
        moved the question away from the machinery it needs.
        """
        from sysadmin.monitor import self_monitor

        real = self_monitor.summarise_agent

        def never_stalled(*args, **kwargs):
            entry = dict(real(*args, **kwargs))
            entry["stalled"] = False
            entry["stall_reason"] = None
            return entry

        with patch.object(self_monitor, "summarise_agent", never_stalled):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "mismatch"
        assert "the stall family no longer speaks" in result.note

    def test_both_families_ceding_is_not_reported_as_this_entry_fixed(self):
        """Two owners becoming none is a different fault, and the note says so.

        The obvious implementation reports any silence as progress.  A
        question nobody owns is not this entry closed; it is the fault
        underneath both families arriving instead.
        """
        from sysadmin.monitor import self_monitor
        from sysadmin.monitor import service_recommendations as advice

        real = self_monitor.summarise_agent

        def never_stalled(*args, **kwargs):
            entry = dict(real(*args, **kwargs))
            entry["stalled"] = False
            return entry

        with (
            patch.object(self_monitor, "summarise_agent", never_stalled),
            patch.object(advice, "_timer_stale_row", lambda *a, **k: None),
        ):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "mismatch"
        assert "neither family speaks" in result.note
        assert "a different fault rather than this one fixed" in result.note

    def test_a_rung_on_the_timer_family_is_the_fix_the_entry_forbids(self):
        """The half that cannot be inferred from the first — both families still speak.

        The stand-in clocks its rung off the fault's own age at the box's
        one escalation gap, because that is the only shape available to a
        family that is recomputed per request and holds no "when the
        alarm rang".
        """
        laddered = self._laddered_reading()
        with patch.object(snag_claims, "timer_agent_reading", lambda: (laddered, "")):
            result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "mismatch"
        assert "this family has a rung now" in result.note
        assert "forbids by name" in result.note

    def test_the_old_constant_was_blind_to_any_rung_shorter_than_a_cadence(self):
        """The falsification that moved :data:`PROBE_FRESH_OVERSHOOT_INTERVALS`.

        The first draft put the fresh fault one *cadence* past the
        threshold, and the arithmetic is exact: the two drives straddle
        only a rung whose gap falls in ``[overshoot, overshoot + 2 x
        escalate_after_hours)``.  At one cadence that window is **24h to
        72h** — so every rung shorter than a day read loud at both drives,
        the check saw no movement, and it passed against code deliberately
        given a ladder.  At one check interval the window is **5 minutes
        to 48 hours**, and a rung below the monitor's own resolution is
        one it could not observe in any case.

        Driven at the real producers with a rung at *half* the escalation
        gap — the shape a stateless family would most plausibly reach for,
        since it holds no "when the alarm rang" and must clock off the
        fault's own age.  Both verdicts are asserted, because a test that
        only pinned the catch would pass with the old constant restored.
        """
        from sysadmin.monitor import service_recommendations as advice

        config = get_config()
        interval = config.agents.sysadmin.health_check_interval_seconds
        cadence = config.agents.file_organiser.scan_interval_hours * 3600
        rung_gap = config.self_monitor.escalate_after_hours * 3600 / 2
        real = advice._timer_stale_row

        def laddered(series, points, settings, check_interval, now):
            row = real(series, points, settings, check_interval, now)
            if row is None:
                return None
            fires = advice._observed_fires(points)
            observed = advice._observed_cadence(fires, points, check_interval) or 1.0
            elapsed = (now - fires[-1]).total_seconds()
            if elapsed > observed * settings.timer_stale_multiplier + rung_gap:
                return row.model_copy(update={"severity": "risk"})
            return row

        with patch.object(advice, "_timer_stale_row", laddered):
            caught = snag_claims.check_timer_agent_two_owners()
            with patch.object(snag_claims, "PROBE_FRESH_OVERSHOOT_INTERVALS", cadence // interval):
                missed = snag_claims.check_timer_agent_two_owners()

        assert caught.verdict == "mismatch", caught.note
        assert "has a rung now" in caught.note
        assert missed.verdict == "match", (
            "the old constant no longer hides a sub-cadence rung — the constant this "
            "test exists to justify may have been changed without it"
        )

    def test_a_module_importing_both_families_is_a_mismatch(self):
        """Half 3, driven at a real file rather than at a patched instrument.

        This is the shape the entry's *recommended* fix has to take
        whichever file it lands in — a caller feeding ``_observed_fires``
        into the stall family need not edit either module, and a pairwise
        file-to-file check would never see it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            joins = Path(tmp) / "composes_the_two.py"
            joins.write_text(
                "from sysadmin.monitor.stalls import evaluate\n"
                "from sysadmin.monitor.service_recommendations import _observed_fires\n",
                encoding="utf-8",
            )
            with patch.object(snag_claims, "_python_files", lambda roots: [joins]):
                result = snag_claims.check_timer_agent_two_owners()
        assert result.verdict == "mismatch"
        assert "imports both families" in result.note
        assert "composes_the_two.py" in result.note

    def test_this_module_is_excluded_from_its_own_population(self):
        """The only thing here that knows both families exist is the check saying nothing does.

        Not bookkeeping: driving both families means importing both, so
        without the exclusion the check refutes its own entry on every
        run.  The exclusion is shown to be doing work by asking the
        instrument directly.
        """
        self_path = REPO_ROOT / "sysadmin" / "snag_claims.py"
        for module in (snag_claims.STALL_MODULE, snag_claims.TIMER_ADVICE_MODULE):
            assert snag_claims.importers_of(module, [self_path]) == [self_path]

        with patch.object(snag_claims, "_python_files", lambda roots: [self_path]):
            reading, problem = snag_claims.timer_agent_reading()
        assert not problem, problem
        assert reading is not None
        assert reading.joint_importers == ()

    # -- helpers ---------------------------------------------------------

    def _laddered_reading(self):
        """A reading identical to today's but for a rung on the advice family."""
        reading, problem = snag_claims.timer_agent_reading()
        assert not problem, problem
        assert reading is not None
        return dataclasses.replace(reading, aged_timer_severity="risk")


def _answering(payload: dict) -> Callable[..., object]:
    """An ``httpx.get`` stand-in whose response can be raised for status.

    A bare :class:`httpx.Response` refuses ``raise_for_status`` because no
    request is attached, and the refusal is a ``RuntimeError`` the reader
    catches — so a stub without one tests the *error* path while claiming
    to test the answer.  Found by writing it the short way first.
    """
    import httpx

    def answer(url: str, *args: object, **kwargs: object) -> httpx.Response:
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    return answer


class TestTheQueueTimezoneCheck:
    """``SNAG-ESTATE-007``'s check — the twenty-third, and the fifth across a boundary.

    The second whose subject is what another repository *publishes*
    rather than what its code computes, and the first where the fix could
    land in three places: the pool's kwargs (which the entry's cause
    bullet names), ``invariants()``, or the route's serialiser.  All
    three are driven here as real stand-ins, and only the first would be
    visible to an ``ast`` walk for the ``connect_args`` entry.

    Two things this class exists to pin that no other check has needed.
    **The instrument is a *pair* of instants**, because a single one
    agrees with itself only in summer — ``Europe/London`` renders
    ``+00:00`` from late October to late March, so a one-instant check
    reports the entry refuted every winter with nothing having changed.
    And **the reading that discriminates their fix from a box whose
    default moved is the same one that validates the stand-in database**:
    ``pg_settings.source`` is ``client`` when the connection asked and
    ``configuration file`` when it inherited the cluster's, and
    ``database`` when the setting is per-database — at which point this
    repository's database cannot stand in for the estate's and the check
    must say so rather than answer.

    The producer is stubbed rather than mocked out, for
    :class:`TestTheDefaultPortCheck`'s reason: a stub package on disk
    driven by *this* interpreter exercises :func:`estate_probe`'s
    subprocess, its JSON contract and the verdict logic together, and it
    runs where estate-manager is not installed, which is CI.  The stub
    honours the probe's own seeded instants rather than holding a copy of
    them — the fake connection records what the ``INSERT`` was given and
    the fake arbiter renders *that*, so a probe that stopped seeding two
    instants could not be answered by a fixture pretending it had.
    """

    DB = """\
QUEUE_TZ = {queue_tz!r}
QUEUE_SOURCE = {queue_source!r}
QUEUE_SETTING = {setting_override!r} or QUEUE_TZ


class Cursor:
    def __init__(self, row):
        self._row = row

    async def fetchone(self):
        return self._row


class Connection:
    def __init__(self, pool):
        self._pool = pool

    async def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        if "pg_settings" in sql:
            return Cursor({{"setting": QUEUE_SETTING, "source": QUEUE_SOURCE}})
        if sql.upper().startswith("INSERT"):
            self._pool.seeded = list(params or [])
        return Cursor(None)


class Held:
    def __init__(self, pool):
        self._pool = pool

    async def __aenter__(self):
        self._pool.acquired += 1
        return Connection(self._pool)

    async def __aexit__(self, *exc):
        return False


class StubPool:
    def __init__(self, dsn):
        self.dsn = dsn
        self.seeded = []
        self.acquired = 0
        self.closed = False

    async def open(self, wait=True, timeout=10):
        self.opened = True

    async def close(self):
        self.closed = True

    def connection(self):
        return Held(self)


def create_pool(dsn):
    return StubPool(dsn)
"""

    ARBITER = """\
from datetime import datetime
from zoneinfo import ZoneInfo

from .db import QUEUE_TZ

LEASE = {lease!r}
ZONELESS = {zoneless!r}
DROPPED = {dropped!r}
ARBITER_ZONE = {arbiter_zone!r}
STAMPS = ("granted_at", "hold_deadline")


class Arbiter:
    def __init__(self, pool, profiles, systemd, *, gpu_pci_slot, gpu_busy_threshold,
                 sampler=None):
        self.pool = pool
        self.systemd = systemd
        self.sampler = sampler

    async def invariants(self):
        if not LEASE:
            return {{"depth": 0, "active_lease": None}}
        zone = ZoneInfo(ARBITER_ZONE or QUEUE_TZ)
        row = {{"id": 1, "profile": "snagcheck", "requester": "snagcheck"}}
        for name, raw in zip(STAMPS, self.pool.seeded[1:3]):
            if name == DROPPED:
                continue
            moment = datetime.fromisoformat(raw).astimezone(zone)
            row[name] = moment.replace(tzinfo=None) if ZONELESS else moment
        return {{"depth": 0, "active_lease": row}}
"""

    API = """\
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI

ROUTE = {route!r}
NORMALISE = {normalise!r}
RELOCALISE = {relocalise!r}


def _public(row):
    if row is None:
        return None
    out = {{}}
    for key, value in row.items():
        if isinstance(value, datetime):
            if NORMALISE and value.tzinfo is not None:
                value = value.astimezone(UTC)
            elif RELOCALISE and value.tzinfo is not None:
                value = value.astimezone(ZoneInfo(RELOCALISE))
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def create_app(settings=None, *, arbiter=None):
    app = FastAPI()

    @app.get(ROUTE)
    async def invariants():
        stats = await arbiter.invariants()
        stats["active_lease"] = _public(stats["active_lease"])
        return stats

    return app
"""

    CONFIG = """\
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace


@dataclass
class Settings:
    db_dsn: str = "postgresql:///stub"
    profiles_path: Path = field(default_factory=lambda: Path("/dev/null"))
    gpu_pci_slot: str = "0000:00:00.0"
    gpu_busy_threshold: int = 50
    tick_seconds: float = 1.0
    cors_origins: tuple = ()


def load_settings(path=None):
    return Settings()
"""

    SYSTEMD = """\
class UserSystemd:
    def __init__(self, runner=None):
        self.runner = runner
"""

    PROJECTS_DB = """\
from datetime import datetime
from zoneinfo import ZoneInfo

SIBLING_TZ = {sibling_tz!r}
SIBLING_SOURCE = {sibling_source!r}


class Result:
    def __init__(self, row):
        self._row = row

    def mappings(self):
        return self

    def one(self):
        return self._row


class Connection:
    async def execute(self, statement, params=None):
        sql = " ".join(str(statement).split())
        if "pg_settings" in sql:
            return Result({{"setting": SIBLING_TZ, "source": SIBLING_SOURCE}})
        zone = ZoneInfo(SIBLING_TZ)
        return Result({{
            "granted_at": datetime.fromisoformat(params["winter"]).astimezone(zone),
            "hold_deadline": datetime.fromisoformat(params["summer"]).astimezone(zone),
        }})

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class Engine:
    def connect(self):
        return Connection()

    async def dispose(self):
        self.disposed = True


def sqlalchemy_dsn(dsn):
    return dsn


def create_engine_and_session(dsn):
    return Engine(), None
"""

    def _stub(
        self,
        tmp_path: Path,
        *,
        queue_tz: str = "Europe/London",
        queue_source: str = "configuration file",
        setting_override: str = "",
        sibling_tz: str = "UTC",
        sibling_source: str = "client",
        route: str | None = None,
        normalise: bool = False,
        relocalise: str = "",
        lease: bool = True,
        zoneless: bool = False,
        dropped: str = "",
        arbiter_zone: str = "",
    ) -> Path:
        """An ``estate_service`` holding just the six modules the probe imports."""
        service = tmp_path / "service"
        projects = service / "estate_service" / "projects"
        projects.mkdir(parents=True)
        for package in (service / "estate_service", projects):
            (package / "__init__.py").write_text("", encoding="utf-8")
        modules = {
            "db.py": self.DB.format(
                queue_tz=queue_tz, queue_source=queue_source, setting_override=setting_override
            ),
            "arbiter.py": self.ARBITER.format(
                lease=lease, zoneless=zoneless, dropped=dropped, arbiter_zone=arbiter_zone
            ),
            "api.py": self.API.format(
                route=route if route is not None else snag_claims.queue_route(),
                normalise=normalise,
                relocalise=relocalise,
            ),
            "config.py": self.CONFIG,
            "systemd.py": self.SYSTEMD,
        }
        for name, body in modules.items():
            (service / "estate_service" / name).write_text(body, encoding="utf-8")
        (projects / "db.py").write_text(
            self.PROJECTS_DB.format(sibling_tz=sibling_tz, sibling_source=sibling_source),
            encoding="utf-8",
        )
        return service

    LIVE = "live population: active_lease is null, as the entry says"

    def _drive(self, tmp_path, monkeypatch, *, live: str | None = None, **kwargs):
        import sys as _sys

        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", self._stub(tmp_path, **kwargs))
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", Path(_sys.executable))
        monkeypatch.setattr(
            snag_claims, "live_queue_lease", lambda: self.LIVE if live is None else live
        )
        return snag_claims.check_queue_stamps_local()

    # -- the claim holding -----------------------------------------------

    def test_a_local_rendering_beside_a_utc_one_is_the_claim(self, tmp_path, monkeypatch):
        """What the live estate does, and what the entry says."""
        found = self._drive(tmp_path, monkeypatch)
        assert found.verdict == "match"
        assert "+01:00" in found.detail[0]
        assert "+01:00" not in found.detail[2]
        assert "Europe/London (source: configuration file)" in found.detail[3]
        assert "local at both layers" in found.detail[4]

    def test_the_verdict_carries_which_tree_it_was_taken_at(self, tmp_path, monkeypatch):
        """Session 87's rule: a verdict about somebody else's tree needs its state."""
        found = self._drive(tmp_path, monkeypatch)
        assert any("estate-manager's" in line for line in found.detail)

    # -- the three places a fix can land ----------------------------------

    def test_the_pool_asking_for_utc_refutes_it_in_the_place_the_entry_names(
        self, tmp_path, monkeypatch
    ):
        """One ``kwargs`` entry, which is the fix the entry proposes."""
        found = self._drive(tmp_path, monkeypatch, queue_tz="UTC", queue_source="client")
        assert found.verdict == "mismatch"
        assert "asks for its own timezone" in found.note
        assert "in the place it names" in found.note

    def test_a_route_that_normalises_refutes_it_where_the_cause_bullet_does_not_look(
        self, tmp_path, monkeypatch
    ):
        """The fix an ``ast`` walk over their pool would call *still holds*.

        The connection is untouched — still ``Europe/London``, still
        sourced from the configuration file — and the surface publishes
        UTC anyway, because the serialiser converts.  A check reading
        ``invariants()`` alone, or the pool's kwargs, reports the entry
        intact.
        """
        found = self._drive(tmp_path, monkeypatch, normalise=True)
        assert found.verdict == "mismatch"
        assert "normalised in the route" in found.note
        assert "invariants() handed up" in found.detail[1]
        assert "+01:00" in found.detail[1]
        assert "in the route's serialisation" in found.detail[4]

    def test_invariants_normalising_is_seen_through_the_route(self, tmp_path, monkeypatch):
        """The middle layer, which is neither the pool nor the serialiser."""
        found = self._drive(tmp_path, monkeypatch, arbiter_zone="UTC")
        assert found.verdict == "mismatch"
        assert "above a connection that is still local" in found.note
        assert "at or below invariants()" in found.detail[4]

    # -- the instrument ---------------------------------------------------

    def test_one_instant_would_agree_with_itself_only_in_summer(self, tmp_path, monkeypatch):
        """The reason there are two, and it is not redundancy.

        The winter instant renders ``+00:00`` through a ``Europe/London``
        connection — identical, character for character, to what the
        sibling engine publishes.  A check reading ``granted_at`` alone
        would report this entry refuted from late October to late March
        and true again every spring, having measured nothing but the
        calendar.
        """
        found = self._drive(tmp_path, monkeypatch)
        assert found.verdict == "match"
        winter, summer = found.detail[0].split(", hold_deadline")
        assert winter.endswith("+00:00")
        assert summer.endswith("+01:00")
        # And the sibling's winter rendering is the same string, so the
        # two surfaces are indistinguishable on that instant alone.
        assert winter.split()[-1] in found.detail[2]

    def test_stamps_utc_refuses_a_reading_that_holds_one_instant(self):
        """Driven at the property, because the check gates before it gets there.

        This test exists because a falsification **passed**: removing the
        completeness half of :attr:`StampReading.stamps_utc` broke
        nothing, since the verdict body refuses an incomplete reading one
        gate earlier.  The two are not two statements of one fact —
        ``complete`` is defined once and consulted twice — so the
        redundancy is real and harmless *inside the check*, and the
        property is public and would otherwise answer *yes, UTC* about a
        surface that was only ever asked about January.  The gate stays
        and the observation moves to where it is reachable.
        """
        winter_only = snag_claims.StampReading(
            {"granted_at": "2026-01-15T09:31:01+00:00"}, {"granted_at": 0}, ()
        )
        assert not winter_only.complete
        assert not winter_only.stamps_utc

    def test_a_fixed_offset_zone_is_still_not_utc(self, tmp_path, monkeypatch):
        """Both instants equal and non-zero is a local clock without a summer.

        ``stamps_utc`` is *every offset is zero*, not *the offsets
        agree* — a zone with no daylight saving renders both alike and is
        still not what the sibling promises.
        """
        found = self._drive(tmp_path, monkeypatch, queue_tz="Etc/GMT-1")
        assert found.verdict == "match"
        assert found.detail[0].count("+01:00") == 2

    # -- the readings that are not answers --------------------------------

    def test_the_boxs_default_moving_to_utc_is_unknown_and_never_a_closure(
        self, tmp_path, monkeypatch
    ):
        """Rule 1: the mechanism is intact and the symptom is unobservable.

        The surface renders exactly what a fixed one would.  What says it
        is not fixed is ``source``: the connection still *inherits*, so
        the rendering goes local again the day the box does, and
        ``match`` would assert a local rendering this check did not see.
        """
        found = self._drive(
            tmp_path, monkeypatch, queue_tz="UTC", queue_source="configuration file"
        )
        assert found.verdict == "unknown"
        assert "the box's default has moved rather than the pool" in found.note

    def test_a_utc_zone_spelt_another_way_is_still_utc(self, tmp_path, monkeypatch):
        """The witness that the zone name is *resolved* rather than compared.

        PostgreSQL will answer ``UTC``, ``Etc/UTC`` or ``utc`` for one
        setting, and a check comparing the string reads the second as a
        local zone — which turns the box's default moving into a
        *mismatch* naming a fix that never landed.  Nothing else in this
        class would notice, because every other zone here is spelt the
        obvious way.
        """
        found = self._drive(
            tmp_path, monkeypatch, queue_tz="Etc/UTC", queue_source="configuration file"
        )
        assert found.verdict == "unknown"
        assert "the box's default has moved rather than the pool" in found.note

    def test_a_zone_that_will_not_resolve_is_unknown(self, tmp_path, monkeypatch):
        """A name neither PostgreSQL nor :mod:`zoneinfo` can place is not a default."""
        found = self._drive(
            tmp_path,
            monkeypatch,
            queue_tz="UTC",
            queue_source="configuration file",
            setting_override="Mars/Olympus",
        )
        assert found.verdict == "unknown"
        assert "does not resolve to a zone" in found.note

    def test_a_per_database_timezone_makes_the_stand_in_unsound(self, tmp_path, monkeypatch):
        """The one gate that is about this check's own legitimacy.

        The probe points *their* pool at *this* repository's database,
        which the estate rules permit only because the timezone is a
        cluster-wide setting.  ``source: database`` says it is not, and
        the reading that would otherwise be the answer becomes the reason
        there is not one.
        """
        found = self._drive(tmp_path, monkeypatch, queue_source="database")
        assert found.verdict == "unknown"
        assert "per-database" in found.note

    def test_a_zoneless_instant_is_neither_of_the_two_renderings(self, tmp_path, monkeypatch):
        """An offset removed altogether is a third answer, not a UTC one."""
        found = self._drive(tmp_path, monkeypatch, zoneless=True)
        assert found.verdict == "unknown"
        assert "no offset at all" in found.note

    def test_a_field_that_stopped_being_published_is_unknown(self, tmp_path, monkeypatch):
        """One instant is not the pair, so the comparison was not made.

        This is the seasonal defect arriving by a *field* rather than by
        the calendar, and it is why ``stamps_utc`` requires the pair
        rather than merely *every offset is zero*: with only
        ``granted_at`` published, a ``Europe/London`` connection renders
        ``+00:00`` and the draft read it as UTC — refuting the entry off
        the one instant on which the two surfaces have always agreed.
        Found by driving the stand-in, not by reasoning about it.
        """
        found = self._drive(tmp_path, monkeypatch, dropped="hold_deadline")
        assert found.verdict == "unknown"
        assert "compared on one season" in found.note

    def test_a_lease_the_surface_cannot_see_is_unknown(self, tmp_path, monkeypatch):
        """The probe's own witness that its fixture reaches their query."""
        found = self._drive(tmp_path, monkeypatch, lease=False)
        assert found.verdict == "unknown"
        assert "no active lease" in found.note

    def test_a_moved_route_is_a_different_claim(self, tmp_path, monkeypatch):
        """The surface is the subject, so a surface that moved is not it."""
        found = self._drive(tmp_path, monkeypatch, route="/api/gpu/invariants")
        assert found.verdict == "unknown"
        assert snag_claims.queue_route() in found.note

    def test_the_two_layers_disagreeing_is_a_different_fault(self, tmp_path, monkeypatch):
        """UTC below and local above is neither layer doing what it says.

        ``arbiter_zone`` alone is the *middle-layer fix* and is tested
        above; putting the localisation back in the serialiser is what
        produces a surface disagreeing with the function beneath it, and
        that is a fault this entry does not describe.
        """
        found = self._drive(tmp_path, monkeypatch, arbiter_zone="UTC", relocalise="Europe/London")
        assert found.verdict == "unknown"
        assert "disagree about one fact" in found.note

    # -- the premise ------------------------------------------------------

    def test_the_sibling_losing_utc_is_the_premise_going_not_the_complaint(
        self, tmp_path, monkeypatch
    ):
        """Both surfaces agreeing at the wrong end is a closure to judge.

        :func:`check_sysd_ollama_ordering`'s rule, which
        ``SNAG-ESTATE-004``'s check carried until it left the registry
        with its entry on 2026-08-27: a single boolean over the two
        halves would file a *deleted* guarantee as a job well done.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            sibling_tz="Europe/London",
            sibling_source="configuration file",
        )
        assert found.verdict == "mismatch"
        assert "premise has gone rather than its complaint" in found.note

    def test_the_pool_declaring_a_local_zone_kills_the_cause_not_the_symptom(
        self, tmp_path, monkeypatch
    ):
        """A declared zone that is not UTC refutes the entry's cause bullet."""
        found = self._drive(tmp_path, monkeypatch, queue_source="client")
        assert found.verdict == "mismatch"
        assert "cause has gone while its symptom stands" in found.note

    # -- the live population, which is evidence ---------------------------

    def test_the_live_population_is_evidence_and_never_the_verdict(self, tmp_path, monkeypatch):
        """Rule 1, and this entry's population is empty by construction.

        A lease being granted this afternoon is a fact about who is
        holding the GPU.  The verdict must not move with it, in either
        direction.
        """
        absent = self._drive(tmp_path, monkeypatch)
        granted = self._drive(
            tmp_path / "granted",
            monkeypatch,
            live="live population: a lease is granted, and the wire carries granted_at X",
        )
        assert absent.verdict == granted.verdict == "match"
        assert "a lease is granted" in granted.detail[5]

    def test_the_live_reader_says_null_the_way_the_entry_does(self, monkeypatch):
        """The sentence the entry's own observation bullet is checked against."""
        import httpx

        monkeypatch.setattr(httpx, "get", _answering({"active_lease": None}))
        assert "active_lease is null" in snag_claims.live_queue_lease()

    def test_the_live_reader_reports_a_granted_lease_verbatim(self, monkeypatch):
        """The day the population arrives, the wire string is quoted."""
        import httpx

        payload = {
            "active_lease": {
                "granted_at": "2026-08-16T09:31:01+01:00",
                "hold_deadline": "2026-08-16T10:31:01+01:00",
            }
        }
        monkeypatch.setattr(httpx, "get", _answering(payload))
        assert "2026-08-16T09:31:01+01:00" in snag_claims.live_queue_lease()

    def test_an_unreachable_8400_is_a_sentence_and_never_a_gate(self, monkeypatch):
        """:mod:`sysadmin.estate.client` refuses to judge 8400's availability."""
        import httpx

        def refuse(*args, **kwargs):
            raise httpx.ConnectError("nope")

        monkeypatch.setattr(httpx, "get", refuse)
        assert "evidence only" in snag_claims.live_queue_lease()

    # -- what the probe may and may not do --------------------------------

    def test_the_probe_names_no_private_symbol_of_theirs(self):
        """Session 87's rule: a private helper's name is what their fix renames.

        ``_public`` renders the wire string and is deliberately reached by
        *calling the route mounted at the published path* instead.
        """
        tree = ast.parse(
            snag_claims.QUEUE_TIMEZONE_PROBE.format(
                service="/stub",
                dsn="postgresql:///stub",
                winter=snag_claims.QUEUE_WINTER_INSTANT,
                summer=snag_claims.QUEUE_SUMMER_INSTANT,
                route=snag_claims.queue_route(),
                stamps=snag_claims.QUEUE_LEASE_STAMPS,
            )
        )
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
            if (node.module or "").startswith("estate_service")
        }
        assert imported
        assert not [name for name in imported if name.startswith("_")]

    def test_the_probe_is_pointed_at_this_repositorys_own_database(self):
        """Estate rule 1: no application reads another application's database.

        ``create_pool`` is a factory taking a DSN, so the check hands it
        this repository's.  A check running at both ends of every sitting
        would otherwise be the most regular breach of that rule on the
        box.
        """
        dsn = snag_claims.libpq_dsn(get_config().database.sync_url)
        assert dsn.startswith("postgresql://")
        assert "+psycopg2" not in dsn
        assert "estate" not in dsn.rsplit("/", 1)[-1]

    def test_the_probe_cannot_drive_systemd(self):
        """The runner it hands ``UserSystemd`` raises rather than running."""
        assert "runner=refuse" in snag_claims.QUEUE_TIMEZONE_PROBE
        assert "raise RuntimeError" in snag_claims.QUEUE_TIMEZONE_PROBE

    def test_the_lease_lives_in_a_temporary_table(self):
        """No rollback anybody could forget, and no residue to clean up."""
        assert "CREATE TEMPORARY TABLE" in snag_claims.QUEUE_TIMEZONE_PROBE

    def test_the_route_is_read_from_this_repositorys_own_record(self):
        """Two statements of one path can disagree; there is one.

        The estate judge already pulls this surface hourly, so the path
        it uses is the path this check drives — and a rename moves both
        at once or neither.
        """
        from sysadmin.estate.client import SURFACE_PATHS

        path = SURFACE_PATHS["queue_invariants"]
        assert snag_claims.queue_route() == path
        tree = ast.parse(Path(snag_claims.__file__).read_text(encoding="utf-8"))
        literals = [
            node for node in ast.walk(tree) if isinstance(node, ast.Constant) and node.value == path
        ]
        assert not literals, f"{path} is written out at line(s) " + ", ".join(
            str(node.lineno) for node in literals
        )

    def test_the_two_instants_bracket_a_daylight_saving_boundary(self):
        """Otherwise the pair is two readings of one season.

        Driven rather than asserted about the calendar: the check's own
        zone renders them differently and a UTC zone does not.
        """
        from zoneinfo import ZoneInfo

        winter = datetime.fromisoformat(snag_claims.QUEUE_WINTER_INSTANT)
        summer = datetime.fromisoformat(snag_claims.QUEUE_SUMMER_INSTANT)
        london = ZoneInfo("Europe/London")
        assert winter.astimezone(london).utcoffset() != summer.astimezone(london).utcoffset()
        assert winter.astimezone(UTC).utcoffset() == summer.astimezone(UTC).utcoffset()


class TestTheQueueCheckAgainstTheRealProducer:
    """The live half, which is the only thing that can catch the producer.

    :class:`TestTheQueueTimezoneCheck` drives a stub, so it can only
    catch this repository's half of the seam.  These run against
    estate-manager's own interpreter where it is present, and skip where
    it is not — which is CI.
    """

    def test_the_real_queue_surface_yields_one_of_the_three_verdicts(self):
        if not snag_claims.ESTATE_PYTHON.exists():
            pytest.skip("estate-manager's venv is not on this box")
        found = snag_claims.check_queue_stamps_local()
        assert found.verdict in set(EXIT_STATUS)
        assert any("estate-manager's" in line for line in found.detail)

    def test_the_two_engines_are_built_differently_over_there(self):
        """The entry's cause, read where a failure says "they converged".

        In the check this reads as a refutation; here it reads as what it
        is — the one ``kwargs`` entry the entry says is missing, and the
        comment beside its sibling that promises UTC on the wire.
        """
        pool = snag_claims.ESTATE_SERVICE / "estate_service" / "db.py"
        engine = snag_claims.ESTATE_SERVICE / "estate_service" / "projects" / "db.py"
        if not pool.exists() or not engine.exists():
            pytest.skip("estate-manager is not beside this checkout")
        assert "timezone=utc" in engine.read_text(encoding="utf-8")
        assert "timezone=utc" not in pool.read_text(encoding="utf-8")


class TestTheCheckIntervalCheck:
    """``SNAG-SVC-001``'s check — the twenty-fourth, and the fourth on a synthetic subject.

    The entry's population is empty and its own body says so, so the
    contention is **built**: a service whose every outage lasted one poll,
    which is the shape this box has not produced.  What is unusual about
    it is that the claim is a *conflict between two rules*, so the check
    drives both sides — the advice row that answers volume by observing
    less, and ``known_noise`` rule 3, which refuses exactly that move one
    domain over.

    Most of these tests are about the instruments, and one of them
    records a falsification that **passed against deliberately broken
    code** — the fourth in this registry to do so, and the first whose
    cause was a rule stated twice in the module being driven.
    """

    # -- rule 1: the subject is built, not found -------------------------

    def test_the_probe_service_is_declared_nowhere(self):
        """The subject is synthetic, so no rename on this box can move the verdict.

        The entry's population is zero and stays zero until a real
        service starts blipping; a check that read the live scores would
        report the entry refuted on every day the box behaved and live
        the first afternoon a health path went slow, which is a
        measurement of the weather.
        """
        for path in (REPO_ROOT / "services.yaml", REPO_ROOT / "config.yaml"):
            assert snag_claims.BLIP_SERVICE not in path.read_text(encoding="utf-8")

    def test_the_witness_episode_is_the_smallest_that_is_not_one(self):
        """The arithmetic the whole narrowing rests on, driven at the real scorer.

        ``_outage_episodes`` dates an episode to its last *failing*
        check, so one sample spans zero seconds and the row fires; two
        span one interval and it does not.  Both halves are asserted,
        because a witness that measured zero duration too would be the
        subject over again.
        """
        from sysadmin.monitor.reliability import score_service

        now = datetime.now(UTC)
        config = get_config()
        interval = config.agents.sysadmin.health_check_interval_seconds
        window = config.agents.sysadmin.reliability.window_days
        episodes = config.agents.sysadmin.service_actions.flap_min_episodes

        def longest(checks: int) -> float:
            return score_service(
                snag_claims.BLIP_SERVICE,
                snag_claims.blip_health_points(episodes, checks, window, interval, now),
                window_days=window,
                check_interval_seconds=interval,
                now=now,
            ).longest_outage_minutes

        assert snag_claims.BLIP_WITNESS_EPISODE_CHECKS == 2
        assert longest(1) == 0.0
        assert longest(snag_claims.BLIP_WITNESS_EPISODE_CHECKS) > 0.0

    def test_the_episodes_are_spread_so_none_of_them_merge(self):
        """``_outage_episodes`` collapses *consecutive* failing checks.

        Two probe episodes placed one check apart are one episode of
        three — the witness, arriving where the subject was meant to be —
        so the builder spreads them and the scorer is asked to confirm
        the count rather than trusted to.
        """
        from sysadmin.monitor.reliability import score_service

        now = datetime.now(UTC)
        config = get_config()
        interval = config.agents.sysadmin.health_check_interval_seconds
        window = config.agents.sysadmin.reliability.window_days

        for episodes in (2, 3, 5):
            score = score_service(
                snag_claims.BLIP_SERVICE,
                snag_claims.blip_health_points(episodes, 1, window, interval, now),
                window_days=window,
                check_interval_seconds=interval,
                now=now,
            )
            assert score.outage_episodes == episodes

    # -- the instruments -------------------------------------------------

    def test_the_import_walk_sees_an_import_and_never_a_mention(self):
        """Rule 7's instrument, driven at two files that differ only in that."""
        with tempfile.TemporaryDirectory() as tmp:
            joins = Path(tmp) / "joins.py"
            joins.write_text(
                "from sysadmin.monitor.log_actions import group_incidents\n"
                "from sysadmin.monitor import log_trends\n",
                encoding="utf-8",
            )
            mentions = Path(tmp) / "mentions.py"
            mentions.write_text(
                '"""Prose about sysadmin.monitor.log_actions and about\n'
                'sysadmin.monitor.log_trends, naming neither as an import."""\n',
                encoding="utf-8",
            )
            for module in snag_claims.BLIP_LOG_MODULES:
                assert snag_claims.importers_of(module, [joins]) == [joins]
                assert snag_claims.importers_of(module, [mentions]) == []

    def test_the_advice_module_already_names_both_log_families_in_prose(self):
        """Rule 7's fifth instance, and the sharpest of them.

        ``service_recommendations.py`` names ``log_actions`` twice in its
        module docstring, ``log_trends`` in ``_flapping_row``'s, and
        ``known_noise`` in the very docstring that files this snag.  A
        text search therefore reports every one of them as already wired
        and would refute this entry on the day it was filed; an ``ast``
        walk over imports sees none, because a docstring is an
        ``ast.Constant``.
        """
        source = snag_claims.BLIP_ADVICE_PATH.read_text(encoding="utf-8")
        assert "known_noise" in source
        for module in snag_claims.BLIP_LOG_MODULES:
            assert module.rsplit(".", 1)[-1] in source
            assert snag_claims.importers_of(module, [snag_claims.BLIP_ADVICE_PATH]) == []

    def test_the_noise_floor_is_read_from_the_family_that_owns_it(self):
        """``NOISE_MIN_OCCURRENCES`` is invented and says so, so it is never copied.

        A probe carrying its own floor goes on describing a threshold
        nobody uses the day that one moves, and its "loud" drive stops
        being loud without saying so.
        """
        from sysadmin.monitor import log_actions

        reading, problem = snag_claims.blip_contention_reading()
        assert reading is not None, problem
        assert reading.noise_floor == log_actions.NOISE_MIN_OCCURRENCES
        assert reading.occurrences == (
            log_actions.NOISE_MIN_OCCURRENCES * snag_claims.BLIP_NOISE_MULTIPLE
        )

    # -- the witnesses ---------------------------------------------------

    def test_a_series_coarser_than_the_box_is_suppressed_before_the_row_is_built(self):
        """W1: the row is ``RATE_ARGUED``, so the gate runs before the producer.

        A probe sampled at its own convenience scores ``low`` confidence,
        every rate-argued row is dropped, and the check would report a
        silence it manufactured — :func:`timer_agent_series`' trap
        arriving through a different gate.
        """
        real = snag_claims.blip_health_points

        def coarse(episodes, checks, window_days, interval, now):
            return real(episodes, checks, window_days, interval * 10, now)

        with patch.object(snag_claims, "blip_health_points", coarse):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "unknown"
        assert "low confidence" in result.note
        assert "unreachable through this probe" in result.note

    def test_an_unreachable_noise_family_is_unknown_and_says_why(self):
        """W2: a rule that was removed and a family the probe cannot reach agree.

        Without the old-and-flat drive, the silence about the loud *new*
        signature would be the probe's and would read as the rule's.
        """
        from sysadmin.monitor import log_actions

        with patch.object(log_actions, "_is_noise_candidate", lambda *a, **k: False):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "unknown"
        assert "not reachable through this probe" in result.note

    def test_a_family_with_no_volume_floor_is_neither_verdict(self):
        """W3: the conflict is about volume, so a rule that ignores it has moved.

        If a signature below the floor is recommended as noise, the loud
        *new* drive is silent because of its change kind and never
        because of its volume — so "rule 3 still refuses volume alone"
        would be true of a rule that no longer looks at volume at all.
        """
        from sysadmin.monitor import log_actions
        from sysadmin.monitor.log_trends import ChangeKind

        real = log_actions._is_noise_candidate

        def floorless(trend, confidence):
            if trend.change in (ChangeKind.STEADY, ChangeKind.FALLING, ChangeKind.RETURNED):
                return True
            return real(trend, confidence)

        with patch.object(log_actions, "_is_noise_candidate", floorless):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "unknown"
        assert "volume no longer gates the rule at all" in result.note

    def test_the_narrowing_going_is_unknown_rather_than_either_verdict(self):
        """The entry's headline gets *more* true while its third bullet goes false.

        "Still live" understates it and "refuted" is plainly wrong, so
        the check declines to grade an entry that has moved underneath
        it.  This is the one drive whose stand-in makes the defect
        **worse**, and it is the reason the witness is not simply folded
        into the mismatch branch.
        """
        from sysadmin.monitor import service_recommendations as advice

        real = advice._check_interval_row

        def widened(score, settings, interval):
            return real(dataclasses.replace(score, longest_outage_minutes=0.0), settings, interval)

        with patch.object(advice, "_check_interval_row", widened):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "unknown"
        assert "the narrowing the entry's third bullet describes is gone" in result.note
        assert "an entry to rewrite rather than a verdict to grade" in result.note

    # -- the entry -------------------------------------------------------

    def test_the_conflict_is_live_today(self):
        """The mechanism, and the evidence is the two rules side by side."""
        result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "match", result.note
        evidence = "\n".join(result.detail)
        assert "one-check blips" in evidence
        assert "evidence rate, 0 points recoverable" in evidence
        assert "old and flat -> noise" in evidence
        assert "new -> new_signature" in evidence
        assert "surged -> surge" in evidence
        assert "advice module importing a log family: none" in evidence

    def test_deleting_the_kind_is_the_first_resolution_taken(self):
        """One of the two edits the entry leaves to the owner, driven as a stand-in."""
        from sysadmin.monitor import service_recommendations as advice

        with patch.object(advice, "_check_interval_row", lambda *a, **k: None):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "mismatch"
        assert "the kind no longer fires for the shape it was narrowed to" in result.note

    def test_a_row_declaring_other_evidence_is_the_second_resolution(self):
        """The producer's own statement that it argues from more than a rate."""
        from sysadmin.monitor import service_recommendations as advice

        real = advice._check_interval_row

        def evidenced(*args, **kwargs):
            # ``ServiceRecommendationInfo`` is a pydantic contract, not a
            # dataclass — the score one call up is the dataclass, and the
            # two are edited with different verbs.
            row = real(*args, **kwargs)
            return None if row is None else row.model_copy(update={"evidence": "correlation"})

        with patch.object(advice, "_check_interval_row", evidenced):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "mismatch"
        assert "arguing from something other than the blip count" in result.note

    def test_the_advice_module_reaching_a_log_family_is_the_same_resolution(self):
        """The structural half, which a fix has to move whichever file it lands in.

        A correlation between the blips and the service's own logs cannot
        be computed by a module that has not got the data, so the import
        set is the instrument rather than the row's own field — and it
        catches a fix that arrived without relabelling ``evidence``.
        """
        source = snag_claims.BLIP_ADVICE_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            stand_in = Path(tmp) / snag_claims.BLIP_ADVICE_PATH.name
            stand_in.write_text(
                "from sysadmin.monitor.log_actions import group_incidents\n" + source,
                encoding="utf-8",
            )
            with patch.object(snag_claims, "BLIP_ADVICE_PATH", stand_in):
                result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "mismatch"
        assert "the evidence the entry says it has not got" in result.note

    @pytest.mark.parametrize("kind_name", ["NEW", "SURGED"])
    def test_the_other_party_relaxing_dissolves_the_conflict(self, kind_name):
        """The third way this entry stops being true, which it does not anticipate.

        ``known_noise`` rule 3 is the *other* side of the conflict.  Its
        relaxing refutes the entry with nobody having touched the row the
        entry is about, so the note says which side moved — a fix and a
        dissolution must not read alike.

        The stand-in models the loop, **not** the predicate: see
        :meth:`test_relaxing_the_predicate_alone_changes_nothing`.
        """
        from sysadmin.monitor import log_actions
        from sysadmin.monitor.log_trends import ChangeKind

        kind = getattr(ChangeKind, kind_name)
        real = log_actions.recommend

        def relaxed(report, *args, **kwargs):
            rows = list(real(report, *args, **kwargs))
            rows.extend(
                log_actions._noise_recommendation(trend)
                for trend in report.signatures
                if trend.change is kind and trend.current >= log_actions.NOISE_MIN_OCCURRENCES
            )
            return rows

        with patch.object(log_actions, "recommend", relaxed):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "mismatch"
        assert "no longer refuses volume alone" in result.note
        assert "nobody has touched the row this entry is about" in result.note

    def test_relaxing_the_predicate_alone_changes_nothing(self):
        """**The falsification that passed against deliberately broken code.**

        ``_is_noise_candidate`` is the function whose docstring carries
        rules 3 and 4, so it is the obvious place to model "rule 3
        relaxed" — and a stand-in aimed there leaves the verdict at
        ``match``.  ``recommend``'s loop does ``if trend.change is
        ChangeKind.NEW: continue`` **before** the predicate is ever
        called, and takes ``SURGED`` in the branch above it, so neither
        kind can reach the noise branch whatever the predicate says.

        The cause is a rule stated **twice** — once by the loop, once by
        the predicate's admitted tuple — which is ``SNAG-DB-003``'s shape
        inside a module nobody had driven from the outside.  The check
        was right; only the falsification was aimed at the wrong
        function.  Pinned here so the next author of a stand-in is told
        where the decision is actually taken.
        """
        from sysadmin.monitor import log_actions
        from sysadmin.monitor.log_trends import ChangeKind

        real = log_actions._is_noise_candidate

        def admits_everything_loud(trend, confidence):
            if trend.change in (ChangeKind.NEW, ChangeKind.SURGED):
                return True
            return real(trend, confidence)

        with patch.object(log_actions, "_is_noise_candidate", admits_everything_loud):
            result = snag_claims.check_check_interval_looks_away()
        assert result.verdict == "match"

    def test_the_check_reports_liveness_and_never_a_resolution(self):
        """The entry reserves the decision, so the check states no preference.

        Both resolutions are opposite edits to one row and nothing
        measurable here prefers either.  Every note this check can emit
        is therefore a report of what moved — no imperative, and no
        second-person instruction.
        """
        notes = [snag_claims.check_check_interval_looks_away().note]
        from sysadmin.monitor import log_actions
        from sysadmin.monitor import service_recommendations as advice

        with patch.object(advice, "_check_interval_row", lambda *a, **k: None):
            notes.append(snag_claims.check_check_interval_looks_away().note)
        with patch.object(log_actions, "_is_noise_candidate", lambda *a, **k: False):
            notes.append(snag_claims.check_check_interval_looks_away().note)

        directives = (" should ", " must ", "consider raising", "recommend deleting")
        for note in notes:
            for word in directives:
                assert word not in note.lower(), note


class TestTheAuditCodeCheck:
    """``SNAG-ESTATE-006``'s check — the twenty-fifth, and the sixth cross-repo.

    The producer is **stubbed rather than mocked out**, which is
    :class:`TestTheNudgeWordingCheck`'s rule and its reason: a stub
    package on disk driven by this interpreter exercises
    :func:`~sysadmin.snag_claims.estate_probe`'s subprocess, its JSON
    contract, the stand-in session's dispatch and the verdict logic
    together — and it runs where estate-manager is not installed, which
    is CI.

    The stub is a **real SQLAlchemy declarative model and a real FastAPI
    ``Depends``**, not a hand-rolled shape.  Both are load-bearing: the
    probe dispatches on ``statement.column_descriptions``, which only a
    real ``select()`` has, and the poison it installs is only meaningful
    against a route whose session argument is a real dependency default.
    A stub built out of plain functions would let a probe that had lost
    both go on passing.
    """

    #: Every stub's ``findings()`` asks for these four selects, in the
    #: order the real route asks for them.  Held as source rather than
    #: built, because what is being exercised is the stand-in's dispatch
    #: over statements the producer wrote.
    ROUTE = """\
from typing import Any

from fastapi import Depends
from sqlalchemy import desc, select

from estate_service.audit.models import AuditFinding, AuditRun
from estate_service.projects.db import get_db_session


async def findings(session: Any = Depends(get_db_session)) -> dict[str, Any]:
    run = (
        await session.execute(select(AuditRun).order_by(desc(AuditRun.started_at)).limit(1))
    ).scalars().first()
    if run is None:
        return {"run": None, "findings": []}
    rows = (
        await session.execute(select(AuditFinding).where(AuditFinding.run_id == run.id))
    ).scalars().all()
    await session.execute(select(AuditRun.id, AuditRun.started_at))
    await session.execute(select(AuditFinding.fingerprint, AuditFinding.run_id))
    return {"run": {"run_id": str(run.id)}, "findings": [PAYLOAD(row) for row in rows]}
"""

    def _stub(
        self,
        tmp_path: Path,
        *,
        code_column: bool = False,
        payload_code: str | None = None,
        detail_keys: str = "{}",
        finding_fields: tuple[str, ...] = (
            "check: str",
            "severity: str",
            "subject: str",
            "summary: str",
            "code: str",
        ),
        serves: bool = True,
    ) -> Path:
        """A minimal ``estate_service`` holding the audit's three modules."""
        root = tmp_path / "estate_service"
        (root / "audit").mkdir(parents=True)
        (root / "projects").mkdir(parents=True)
        (root / "__init__.py").write_text("", encoding="utf-8")
        (root / "audit" / "__init__.py").write_text("", encoding="utf-8")
        (root / "projects" / "__init__.py").write_text("", encoding="utf-8")
        (root / "projects" / "db.py").write_text(
            "async def get_db_session():\n"
            '    raise RuntimeError("the stub opens no session either")\n'
            "    yield None\n",
            encoding="utf-8",
        )

        fields = "".join(f"    {line}\n" for line in finding_fields)
        (root / "audit" / "finding.py").write_text(
            "from dataclasses import dataclass, field\n"
            "from typing import Any\n\n\n"
            "@dataclass(frozen=True)\n"
            "class Finding:\n"
            f"{fields}"
            "    detail: dict[str, Any] = field(default_factory=dict)\n\n"
            "    @property\n"
            "    def fingerprint(self):\n"
            '        return ":".join(str(getattr(self, n, "")) for n in '
            f"{tuple(line.split(':')[0] for line in finding_fields)!r})\n\n"
            "    def as_payload(self):\n"
            "        out = {n: getattr(self, n) for n in "
            f"{tuple(line.split(':')[0] for line in finding_fields)!r}}}\n"
            '        out["fingerprint"] = self.fingerprint\n'
            '        out["detail"] = self.detail\n'
            "        return out\n",
            encoding="utf-8",
        )

        extra = (
            "    code: Mapped[str] = mapped_column(String(40), nullable=True)\n"
            if code_column
            else ""
        )
        (root / "audit" / "models.py").write_text(
            "import uuid\n"
            "from datetime import datetime\n\n"
            "from sqlalchemy import ForeignKey, String, Text\n"
            "from sqlalchemy.dialects.postgresql import JSONB, UUID\n"
            "from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column\n"
            "from sqlalchemy.types import DateTime\n\n\n"
            "class Base(DeclarativeBase):\n"
            "    pass\n\n\n"
            "class AuditRun(Base):\n"
            '    __tablename__ = "audit_runs"\n'
            "    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)\n"
            "    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))\n\n\n"
            "class AuditFinding(Base):\n"
            '    __tablename__ = "audit_findings"\n'
            "    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)\n"
            "    run_id: Mapped[uuid.UUID] = mapped_column(\n"
            '        UUID(as_uuid=True), ForeignKey("audit_runs.id")\n'
            "    )\n"
            "    check_name: Mapped[str] = mapped_column(String(40))\n"
            "    severity: Mapped[str] = mapped_column(String(10))\n"
            "    subject: Mapped[str] = mapped_column(String(200))\n"
            "    summary: Mapped[str] = mapped_column(Text)\n"
            "    fingerprint: Mapped[str] = mapped_column(String(200))\n"
            "    detail: Mapped[dict] = mapped_column(JSONB)\n"
            "    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))\n"
            f"{extra}",
            encoding="utf-8",
        )

        keys = [
            '"check": row.check_name',
            '"severity": row.severity',
            '"subject": row.subject',
            '"summary": row.summary',
            '"fingerprint": row.fingerprint',
            f'"detail": {detail_keys}',
            '"observed_at": row.observed_at.isoformat()',
        ]
        if payload_code is not None:
            keys.append(f'"code": {payload_code}')
        body = "{" + ", ".join(keys) + "}"
        route = self.ROUTE.replace("PAYLOAD(row)", body)
        if not serves:
            route = route.replace("for row in rows]", "for row in rows[:0]]")
        (root / "audit" / "router.py").write_text(route, encoding="utf-8")
        return tmp_path

    def _drive(self, tmp_path, monkeypatch, *, wire=None, **kwargs):
        """The real check, against a stub producer and a chosen wire."""
        import sys as _sys

        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", self._stub(tmp_path, **kwargs))
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", Path(_sys.executable))
        monkeypatch.setattr(snag_claims, "audit_wire_client", self._client(wire))
        return snag_claims.check_audit_code_unpublished()

    @staticmethod
    def _client(payload):
        """A client factory answering ``audit_findings`` with ``payload``.

        ``None`` means the surface declines, which is what an 8400 that is
        down looks like from here.  Substituted at the factory so the
        production ``pull_all`` runs the whole way down —
        ``mounted_judge``'s rule.
        """
        import httpx

        handler = snag_claims.findings_transport(payload if payload is not None else {})

        def unreachable(request):
            raise httpx.ConnectError("nothing is listening in this test")

        chosen = handler if payload is not None else unreachable
        return lambda: httpx.AsyncClient(transport=httpx.MockTransport(chosen), timeout=5.0)

    @staticmethod
    def _served(**over):
        """One finding on the wire, in the shape the live route serves."""
        finding = {
            "check": "ports",
            "severity": "breach",
            "subject": "port 3300",
            "summary": "claimed and silent",
            "fingerprint": "ports:port 3300:claimed_but_silent",
            "detail": {"port": 3300},
            "observed_at": "2026-08-27T15:07:47+00:00",
            "first_seen_at": "2026-08-27T15:07:47+00:00",
            "standing_days": 0.0,
            "runs_observed": 1,
            "age_truncated": False,
        }
        finding.update(over)
        return {"run": {"run_id": "r"}, "findings": [finding]}

    # ── the claim holding ────────────────────────────────────────────

    def test_computed_and_unpublished_is_the_claim_holding(self, tmp_path, monkeypatch):
        """What the live producer does, and what Session 54 measured."""
        found = self._drive(tmp_path, monkeypatch, wire=self._served())
        assert found.verdict == "match"
        assert found.note == ""
        assert "Finding computes check, code" in found.detail[0]
        assert "the findings route publishes" in found.detail[3]
        assert "code" not in found.detail[3].split("publishes ")[1].split(", ")

    def test_the_bus_payload_carries_the_code_the_route_drops(self, tmp_path, monkeypatch):
        """The evidence line that sharpens the entry rather than the verdict.

        ``as_payload`` publishes ``code`` and the HTTP route does not, so
        "publishes a finding's ``code`` nowhere" is true of the surface
        this repository reads and false of the bus.  Carried in the
        evidence, deliberately: the claim that matters is about the
        surface ``judge_audit_findings`` pulls, and folding the bus into
        the verdict would refute the entry on a fact that changes nothing
        for the consumer.
        """
        found = self._drive(tmp_path, monkeypatch, wire=self._served())
        assert found.verdict == "match"
        assert "code" in found.detail[1].split("publishes ")[1].split(", ")

    # ── the four remedies, each a different note ─────────────────────

    def test_a_published_code_key_refutes_the_entry(self, tmp_path, monkeypatch):
        """The fix the entry waits for: nothing changes here when it lands."""
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=self._served(),
            code_column=True,
            payload_code="row.code",
        )
        assert found.verdict == "mismatch"
        assert "now publishes 'code'" in found.note
        assert "no change here" in found.note

    def test_a_code_key_without_a_column_also_refutes(self, tmp_path, monkeypatch):
        """A fix on the producer's side that stores nothing new.

        The entry's cause names the missing column, so a check keyed on
        the column would report *still holds* for a producer that derived
        the code and published it — which is exactly the sentence
        ``SNAG-ESTATE-004``'s check settled: an ``ast`` walk for the name
        the entry proposes reports still holds for a fix that lands
        somewhere else.  The reading is the published key.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=self._served(),
            payload_code='"derived"',
        )
        assert found.verdict == "mismatch"
        assert "now publishes 'code'" in found.note

    def test_a_code_inside_detail_is_refuted_with_a_line_owed_here(self, tmp_path, monkeypatch):
        """The one refutation that owes *this* repository an edit.

        ``judge_audit_findings`` reads ``finding.get("code")`` at the top
        level, so a producer publishing it inside ``detail`` has ended
        the entry's claim and left the consumer reading ``None``.  A
        check reporting that as a clean closure would hide the line owed
        — ``check_nudge_wording_unpublished``'s partial-fix rule, one
        surface over.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=self._served(),
            detail_keys='{"code": "claimed_but_silent"}',
        )
        assert found.verdict == "mismatch"
        assert "inside the finding's detail blob" in found.note
        assert "one line is owed here" in found.note

    def test_a_producer_that_stops_computing_a_code_refutes_it_differently(
        self, tmp_path, monkeypatch
    ):
        """The delete remedy: the two-owners problem ends, not the publishing one."""
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=self._served(),
            finding_fields=("check: str", "severity: str", "subject: str", "summary: str"),
        )
        assert found.verdict == "mismatch"
        assert "no longer computes a 'code'" in found.note

    def test_the_column_landing_alone_is_match_with_the_residue_named(self, tmp_path, monkeypatch):
        """A fix in flight must not read as silence.

        The claim is about the wire, so a column with no key leaves it
        standing — but a sitting reading ``still holds`` with no note
        cannot tell a producer that has started from one that has not.
        """
        found = self._drive(tmp_path, monkeypatch, wire=self._served(), code_column=True)
        assert found.verdict == "match"
        assert "now carries a 'code' column" in found.note
        assert "the claim is unmoved" in found.note

    # ── the wire ─────────────────────────────────────────────────────

    def test_the_wire_refutes_over_a_probe_that_disagrees(self, tmp_path, monkeypatch):
        """A ``code`` key on a served finding kills the claim outright.

        The deployed process and the checkout can disagree in either
        direction, and only one of them is the surface
        ``judge_audit_findings`` reads.  So the wire is allowed to refute
        against a probe reporting the unfixed shape, and the note says
        it is the deployed surface that moved.
        """
        found = self._drive(tmp_path, monkeypatch, wire=self._served(code="x"))
        assert found.verdict == "mismatch"
        assert "deployed findings surface publishes" in found.note

    def test_the_wire_cannot_confirm_the_claim_on_its_own(self, tmp_path, monkeypatch):
        """Its absence is one deploy behind, so the specimen decides.

        Driven at a producer whose route *does* publish the key while the
        wire does not — the shape a committed-but-undeployed fix makes.
        A check that took the wire's silence as agreement would report
        ``still holds`` for a fix that had already landed.
        """
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=self._served(),
            code_column=True,
            payload_code="row.code",
        )
        assert found.verdict == "mismatch"

    def test_a_detail_key_merely_containing_code_is_not_a_code_key(self, tmp_path, monkeypatch):
        """Exact keys, never a substring.

        The live ``docs`` finding carries ``last_code_commit`` in its
        detail blob, so a substring test would report the entry refuted
        off a key that has nothing to do with it — and would have done so
        on the day the check was written.
        """
        wire = self._served(detail={"last_code_commit": "abc", "encoded": 1})
        found = self._drive(
            tmp_path,
            monkeypatch,
            wire=wire,
            detail_keys='{"last_code_commit": "abc", "encoded": 1}',
        )
        assert found.verdict == "match", found.note

    def test_the_wire_refutes_through_a_detail_blob_with_the_line_owed(self, tmp_path, monkeypatch):
        """The deployed surface can refute either way it publishes the code.

        Read as well as collected: a ``detail_keys`` gathered from the
        wire and consulted by nothing would be ``SNAG-CFG-001``'s shape
        inside the check, and it was exactly that until a falsification
        aimed at the substring rule passed against broken code and found
        the dead field instead of the mis-aimed test.
        """
        wire = self._served(detail={"port": 3300, "code": "claimed_but_silent"})
        found = self._drive(tmp_path, monkeypatch, wire=wire)
        assert found.verdict == "mismatch"
        assert "inside a finding's detail blob" in found.note
        assert "one line is owed here" in found.note

    def test_an_unreadable_wire_leaves_the_specimen_answering(self, tmp_path, monkeypatch):
        """8400 being down is not this entry's business.

        ``sysadmin.estate.client``'s own docstring refuses to judge the
        estate's availability, so an unread surface is a sentence in the
        evidence and the verdict comes from the producer's code.
        """
        found = self._drive(tmp_path, monkeypatch, wire=None)
        assert found.verdict == "match"
        assert "live population:" in found.detail[5]
        assert "was not read" in found.detail[5]

    def test_a_clean_audit_is_answered_rather_than_unknown(self, tmp_path, monkeypatch):
        """The end state the second instrument exists for.

        An audit that finds nothing publishes ``"findings": []``, which
        says nothing about the route's key set.  That is the estate's
        goal rather than a remote possibility, so a wire-only check would
        go blind on precisely the morning it succeeded.
        """
        found = self._drive(tmp_path, monkeypatch, wire={"run": {"run_id": "r"}, "findings": []})
        assert found.verdict == "match"
        assert "served 0 findings" in found.detail[5]

    # ── the ways it declines to answer ───────────────────────────────

    def test_a_route_serving_no_finding_is_unknown(self, tmp_path, monkeypatch):
        """The probe has stopped isolating the question — rule 5.

        A route that hands back no finding for a specimen row publishes
        an empty key set, which reads identically to *no code key* and is
        not the same claim.
        """
        found = self._drive(tmp_path, monkeypatch, wire=self._served(), serves=False)
        assert found.verdict == "unknown"
        assert "stopped isolating the question" in found.note

    def test_a_query_the_stand_in_has_not_met_is_unknown(self, tmp_path, monkeypatch):
        """Dispatch is on the statement, so a new select raises rather than lies.

        Order-based dispatch would answer a reordered route wrongly and
        silently, which is the failure this registry cares most about
        when the thing being driven belongs to somebody else.
        """
        stub = self._stub(tmp_path)
        router = stub / "estate_service" / "audit" / "router.py"
        router.write_text(
            router.read_text(encoding="utf-8").replace(
                "await session.execute(select(AuditRun.id, AuditRun.started_at))",
                "await session.execute(select(AuditFinding.subject))",
            ),
            encoding="utf-8",
        )
        import sys as _sys

        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", stub)
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", Path(_sys.executable))
        monkeypatch.setattr(snag_claims, "audit_wire_client", self._client(self._served()))
        found = snag_claims.check_audit_code_unpublished()
        assert found.verdict == "unknown"
        assert "the audit route asked for" in found.note

    def test_no_interpreter_is_unknown_and_never_a_skip(self, tmp_path, monkeypatch):
        """Which is what CI is, and what a moved checkout is."""
        monkeypatch.setattr(snag_claims, "ESTATE_SERVICE", self._stub(tmp_path))
        monkeypatch.setattr(snag_claims, "ESTATE_PYTHON", tmp_path / "nothing")
        monkeypatch.setattr(snag_claims, "audit_wire_client", self._client(self._served()))
        found = snag_claims.check_audit_code_unpublished()
        assert found.verdict == "unknown"
        assert "interpreter is not at" in found.note

    # ── the constraint the entry imposes on the instrument ───────────

    def test_nothing_here_splits_a_fingerprint(self):
        """The entry's *not worked around here* bullet, as a guard.

        The only workaround it forbids is splitting ``fingerprint`` on
        its last colon, which is this repository parsing an identity
        format the estate owns.  The cheapest way for a later sitting to
        make this check "better" is exactly that, so the module's own
        source is walked for it — including inside
        :data:`~sysadmin.snag_claims.AUDIT_CODE_PROBE`, which is a string
        this module ships and another interpreter runs.
        """
        module = Path(snag_claims.__file__).read_text(encoding="utf-8")
        probe = snag_claims.AUDIT_CODE_PROBE.format(
            service="/probe", code=snag_claims.AUDIT_FINDING_CODE
        )
        for label, body in (("the module", module), ("the probe", probe)):
            splits = self._fingerprint_splits(body)
            assert not splits, f"{label} splits a fingerprint at {splits} — the entry forbids it"

    @staticmethod
    def _fingerprint_splits(source: str) -> list[int]:
        """Every line at which a fingerprint is taken apart.

        Structural rather than textual, and the difference is the whole
        of it: the probe *reads* ``finding.fingerprint`` to answer the
        producer's own join, which a substring test reports as a
        violation and which is the ``value``-where-``provenance``-was-meant
        shape this suite has now caught six times.  What is forbidden is
        splitting it, so what is walked for is a split.

        The **receiver's whole subtree** is searched, for names and for
        string constants alike, and two falsifications bought each half.
        A first draft read only the immediate ``Name`` or ``Attribute``,
        so ``str(f.fingerprint).rsplit(":", 1)`` walked past it — the
        receiver is a ``Call`` and both names come back ``None``.  A
        second read names anywhere in the subtree and still walked past
        ``payload.get("fingerprint").rsplit(":", 1)``, where the field is
        reached through a **dict key** and is an ``ast.Constant``.

        Neither is a contrivance, and the second is the likelier of the
        two: this module reads the probe's JSON and the wire's JSON, so
        a sitting minded to take the code out of the identity would reach
        it by key rather than by attribute.  The detector was tuned to
        the shape the *producer* uses and not to the shape *this module*
        would use, which is the same mis-aiming that made the wire's
        detail blob dead for an afternoon.
        """
        cuts = {"split", "rsplit", "partition", "rpartition"}
        found = []
        for node in ast.walk(ast.parse(source)):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in cuts:
                continue
            reached = []
            for inner in ast.walk(node.func.value):
                reached.append(getattr(inner, "id", None) or getattr(inner, "attr", None))
                if isinstance(inner, ast.Constant) and isinstance(inner.value, str):
                    reached.append(inner.value)
            if any(name and "fingerprint" in name for name in reached):
                found.append(node.lineno)
        return found

    def test_the_probe_poisons_their_session_before_importing_the_router(self):
        """No database is opened in either repository, and it cannot be.

        ``QUEUE_TIMEZONE_PROBE`` keeps ``systemctl`` out of reach with a
        runner that raises; this keeps their database out of reach the
        same way.  The **order** is the whole of it: the router does
        ``from ... import get_db_session`` at import time, so a poison
        installed afterwards would be shadowed by the name the decorator
        already captured.
        """
        probe = snag_claims.AUDIT_CODE_PROBE
        poison = probe.index("projects_db.get_db_session = refuse")
        router = probe.index("from estate_service.audit import router")
        assert poison < router, (
            "the poison is installed after the router captured the dependency, so it guards nothing"
        )

    def test_the_surface_and_the_field_are_not_typed_as_a_path(self):
        """``ports_checked``'s rule at the level of a constant.

        The path comes from this repository's own record of what it pulls
        hourly, so a renamed route reports a read failure rather than a
        refutation.
        """
        from sysadmin.estate.client import SURFACE_PATHS

        assert snag_claims.AUDIT_SURFACE in SURFACE_PATHS
        assert "/" not in snag_claims.AUDIT_SURFACE

    def test_the_check_is_pinned_to_its_entry(self):
        """Rule 4's pin, for the entry this sitting added."""
        check = snag_claims.CHECKS["audit_code_unpublished"]
        assert check.snag == "SNAG-ESTATE-006"
        entry = next(e for e in snag_claims.load_entries()[0] if e.snag_id == "SNAG-ESTATE-006")
        assert "audit_code_unpublished" in entry.markers


class TestTheNightlyHoldCheck:
    """``SNAG-AGENT-011``'s check — a conjunction whose halves refute at different moments.

    Limb 2 is a source walk and flips the instant the fix is *written*;
    limb 1 reads the population and flips the first night after it is
    *deployed*.  Neither is redundant, and the tests below are grouped by
    which half they falsify because the two fail in opposite directions:
    a source walk alone reports the entry dead over a fix nobody
    restarted into, and a population read alone goes on reporting *still
    holds* over a fix landing where this repository cannot see it —
    ``notifications.tray.mute_services``, or the estate retiring the swap.

    The order below is load-bearing for the same reason
    :class:`TestEveryCheckCanSayItDoesNotKnow`'s is: the live drive comes
    first, because every stand-in beneath it is a claim about what the
    check does to a reading, and none of them means anything if the
    reading it substitutes for is not the one the box produces.
    """

    # -- the live box -----------------------------------------------------

    def test_it_holds_against_the_live_box(self):
        assert snag_claims.check_nightly_hold_is_loud().verdict == "match"

    def test_the_check_is_pinned_to_its_entry(self):
        """Rule 4's pin, for the entry this sitting checked."""
        check = snag_claims.CHECKS["nightly_hold_is_loud"]
        assert check.snag == "SNAG-AGENT-011"
        entry = next(e for e in snag_claims.load_entries()[0] if e.snag_id == "SNAG-AGENT-011")
        assert "nightly_hold_is_loud" in entry.markers

    # -- limb 2: the mechanism --------------------------------------------

    def test_both_spellings_of_the_fix_refute_the_entry(self):
        """The fix has two plausible shapes and a walk blind to either is blind.

        A raw payload read is an ``ast.Constant``; a contract model gives
        an ``ast.Attribute``.  Driven at a stand-in *modelling the fix*
        rather than at one modelling the defect —
        ``a-control-a-fix-breaks-is-not-a-control`` — and asserted per
        line, so a walk that found one shape and stopped is red rather
        than merely under-counting.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw.py").write_text(
                'def held(lease):\n    return lease.get("stopped_units", [])\n',
                encoding="utf-8",
            )
            (root / "typed.py").write_text(
                "def held(lease):\n    return lease.stopped_units\n", encoding="utf-8"
            )
            found = snag_claims.lease_discriminator_readers([root])
        assert [hit.rsplit("/", 1)[-1] for hit in found] == ["raw.py:2", "typed.py:2"]

    def test_prose_naming_the_discriminator_does_not_refute(self):
        """``SNAG-SCHED-002``'s lesson, and what actually pays for it here.

        That check's first draft was a *substring* search, so
        ``estate_queue`` matched ``estate_queue_invariants.json`` named in
        a docstring and a sentence about a fix retired the entry the
        sentence described.  What keeps prose out of *this* walk is the
        exactness — ``node.value == LEASE_DISCRIMINATOR`` — so the test
        has to be **discriminating** rather than merely green: the
        specimen is asserted to be exactly what a grep would have found,
        and then asserted absent.  Without the first half this passes
        against a file that mentions nothing.

        **The third mention is outside a docstring and is the one that
        matters**, found by driving the exactness away: softening the
        comparison to ``LEASE_DISCRIMINATOR in node.value`` passed
        against a two-docstring specimen, because the docstring exclusion
        caught what the softening had let through.  Two guards that mask
        each other is one guard nothing witnesses, so the log line is
        here to make the exactness the only thing keeping this file out.
        """
        prose = (
            '"""A module about stopped_units that binds nothing."""\n\n'
            "def held(lease):\n"
            '    """Reads stopped_units one day, not today."""\n'
            '    logger.info("no stopped_units on this lease")\n'
            "    return []\n"
        )
        assert prose.count(snag_claims.LEASE_DISCRIMINATOR) == 3, (
            "the specimen no longer names the discriminator, so its absence "
            "from the report witnesses nothing"
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "prose.py").write_text(prose, encoding="utf-8")
            assert snag_claims.lease_discriminator_readers([root]) == []

    def test_the_docstring_exclusion_has_a_witness_of_its_own(self):
        """The half a mutation found, and reading did not.

        Removing ``id(node) not in docstrings`` was driven against the
        test above and **passed**: a docstring *mentioning* the name is
        not equal to it, so the exclusion never fired.  A guard nothing
        can witness is ``ports_checked``'s rule at the size of a
        conjunct, so the pathological case is built — a docstring that
        **is** the name — and it is the only shape the exclusion can act
        on.  Contrived on purpose: it is the exclusion's whole
        population, and the exclusion is kept because a later reader
        reaching for ``in`` would reintroduce ``SNAG-SCHED-002``'s defect
        with nothing left standing against it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pathological.py").write_text(
                f'"""{snag_claims.LEASE_DISCRIMINATOR}"""\n', encoding="utf-8"
            )
            assert snag_claims.lease_discriminator_readers([root]) == []
            # ...and the same constant outside a docstring is found, or
            # the test above passes because nothing matches at all.
            (root / "pathological.py").write_text(
                f'x = "{snag_claims.LEASE_DISCRIMINATOR}"\n', encoding="utf-8"
            )
            found = snag_claims.lease_discriminator_readers([root])
        assert [hit.rsplit("/", 1)[-1] for hit in found] == ["pathological.py:1"]

    def test_the_exclusion_is_exactly_this_module_and_not_a_shape(self):
        """The self-exclusion, and the reason it has to be narrow.

        Limb 2 is a claim about a *name*, so the check has to spell the
        name to look for it, and a walk including its own definition
        reports the fix landed on the commit adding the check.  The
        exclusion is one file; a wider one — anything assigning the
        name, say — would hide the fix landing in a neighbour.

        Both halves are asserted, because either alone passes over a
        broken exclusion: that the owner really does contain the literal
        (or the exclusion is excluding nothing), and that no site in it
        reaches the report.
        """
        owner = Path(snag_claims.__file__)
        assert snag_claims.LEASE_DISCRIMINATOR in owner.read_text(encoding="utf-8")
        assert not [
            hit for hit in snag_claims.lease_discriminator_readers() if hit.endswith(owner.name)
        ]
        # ...and a file that merely *assigns* the name elsewhere is not
        # excluded by the same rule, which is what makes it narrow.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "elsewhere.py").write_text(
                'DISCRIMINATOR = "stopped_units"\n', encoding="utf-8"
            )
            elsewhere = snag_claims.lease_discriminator_readers([root])
        assert [hit.rsplit("/", 1)[-1] for hit in elsewhere] == ["elsewhere.py:1"]

    def test_a_reader_refutes_while_the_nightly_row_is_still_loud(self):
        """The conjunction's ordering, and why limb 2 is asked first.

        The fix lands as a commit and reaches the box at a restart, so
        for at least one night both halves are true at once: the code
        reads the discriminator and last night's row is still
        ``critical``.  A check taking the population's answer as final
        would report *still holds* over a landed fix — the shape
        ``check_review_schedule_unread`` was, and one this repository has
        already paid for.
        """
        loud = snag_claims.NightlyHoldReading(
            fires_at=datetime(2026, 9, 1, tzinfo=UTC),
            grace_seconds=300,
            rows=(
                ("venture-chat unreachable", "critical", datetime(2026, 8, 31, tzinfo=UTC), None),
            ),
            latest_observed_night=datetime(2026, 8, 31, tzinfo=UTC).date(),
            observed_nights=6,
        )
        with (
            patch.object(snag_claims, "nightly_hold_reading", return_value=(loud, "")),
            patch.object(snag_claims, "lease_discriminator_readers", return_value=["a.py:1"]),
        ):
            measurement = snag_claims.check_nightly_hold_is_loud()
        assert measurement.verdict == "mismatch"
        assert "whatever last night's rung was" in measurement.note

    # -- limb 1: the population -------------------------------------------

    def _reading(self, **over):
        night = datetime(2026, 8, 31, tzinfo=UTC)
        fields = {
            "fires_at": datetime(2026, 9, 1, tzinfo=UTC),
            "grace_seconds": 300,
            "rows": (("venture-chat unreachable", "critical", night, None),),
            "latest_observed_night": night.date(),
            "observed_nights": 6,
        }
        return snag_claims.NightlyHoldReading(**(fields | over))

    def _drive(self, reading):
        with (
            patch.object(snag_claims, "nightly_hold_reading", return_value=(reading, "")),
            patch.object(snag_claims, "lease_discriminator_readers", return_value=[]),
        ):
            return snag_claims.check_nightly_hold_is_loud()

    def test_a_quietened_nightly_row_refutes_the_entry(self):
        """The fix the entry actually asks for, and the row surviving it.

        ``known_noise`` rule 2 and ``TRANSIENT_HOLDER_SEVERITY``'s
        reason: a quietening, never a suppression, so the row still
        exists and still reaches ``GET /api/services/reliability``.  A
        check keyed on the row's *absence* would therefore never see this
        fix at all.
        """
        night = datetime(2026, 8, 31, tzinfo=UTC)
        measurement = self._drive(
            self._reading(rows=(("venture-chat unreachable", "info", night, None),))
        )
        assert measurement.verdict == "mismatch"
        assert "no longer critical" in measurement.note

    def test_a_vanished_population_refutes_and_names_both_readings(self):
        """Rule 2 — a refuted claim is a candidate for closure, never a closure.

        Three things empty the population without a line of this
        repository's code moving: ``mute_services`` gaining the service,
        the estate retiring the swap, or the profile losing its
        ``stopped_units``.  This module cannot separate them, so the note
        names the judgement rather than making it.
        """
        measurement = self._drive(self._reading(rows=()))
        assert measurement.verdict == "mismatch"
        assert "judge whether the estate stopped swapping" in measurement.note

    def test_an_unwatched_window_is_unknown_and_never_a_refutation(self):
        """The coverage half, and the asymmetry it rests on.

        The monitor being down can hide a row and can never invent one —
        ``reliability.py``'s "a gap in the series never costs points" and
        ``health_review``'s refusal of a fall the coverage cannot
        support.  Without this a daemon outage closes the entry, which is
        the calendar's verdict wearing the check's clothes.
        """
        measurement = self._drive(
            self._reading(rows=(), latest_observed_night=None, observed_nights=0)
        )
        assert measurement.verdict == "unknown"
        assert "this daemon having been down" in measurement.note

    def test_a_row_on_a_night_nothing_watched_does_not_hold_the_entry_open(self):
        """The falsification of the test above, from the other side.

        A nightly row exists, and it is not on the latest observed night
        — so the last time anything looked, nothing was announced.  A
        check keyed on "are there any nightly rows" would answer ``match``
        off a row a week old and go on doing so for the length of the
        lookback.
        """
        stale = datetime(2026, 8, 20, tzinfo=UTC)
        measurement = self._drive(
            self._reading(rows=(("venture-chat unreachable", "critical", stale, None),))
        )
        assert measurement.verdict == "mismatch"
        assert "no service was announced unreachable in it" in measurement.note

    # -- the derivations ---------------------------------------------------

    def test_the_window_is_read_as_an_epoch_and_never_as_a_wall_clock(self):
        """``--timestamp=unix``, and why the default rendering is refused.

        ``NextElapseUSecRealtime`` normally prints ``Tue 2026-09-01
        00:00:00 BST`` — a local wall clock with a zone abbreviation,
        which names two instants at an autumn fold and a different one in
        every zone.  That is the token
        ``service_recommendations._timer_stale_row`` refuses to parse for
        ``SNAG-LOG-009``'s reason, and the flag is what keeps this check
        from rebuilding it.  Asserted at the invocation, because on this
        box the two readings agree and only the argument can say which
        was asked for.
        """
        recorded = []

        def _run(argv, **kwargs):
            recorded.append(argv)
            return SimpleNamespace(stdout="NextElapseUSecRealtime=@1788217200\n")

        with patch.object(snag_claims.subprocess, "run", _run):
            fires_at, problem = snag_claims.timer_fires_at("anything.timer")
        assert problem == ""
        assert "--timestamp=unix" in recorded[0]
        assert fires_at == datetime.fromtimestamp(1788217200, UTC).astimezone()

    def test_the_calendar_spec_is_not_parsed(self):
        """A reader of ``OnCalendar`` is a second implementation of a grammar.

        ``schema_guard``'s refusal to regex ``alembic/versions/*.py`` at
        the size of a timer: systemd has already resolved the spec, so
        this asks it for the answer rather than for the question.
        """
        source = inspect.getsource(snag_claims.timer_fires_at)
        body = source.split('"""', 2)[-1]
        assert "TimersCalendar" not in body
        assert "OnCalendar" not in body

    def test_the_loud_rung_is_derived_from_the_ladder(self):
        """``max_priority_for`` against ``PRIORITY_MAP``'s rule.

        Asserted by **provenance** rather than by value: a literal
        ``"critical"`` and this derivation both read ``critical``, and
        only the source separates them — the shape recorded after Session
        59's guards, where two of six passed against broken code for
        exactly this reason.
        """
        assert snag_claims.LOUDEST_SEVERITY == "critical"
        assignment = next(
            node
            for node in ast.walk(ast.parse(Path(snag_claims.__file__).read_text(encoding="utf-8")))
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "LOUDEST_SEVERITY" for t in node.targets
            )
        )
        assert not isinstance(assignment.value, ast.Constant), (
            "LOUDEST_SEVERITY is written down rather than derived from SEVERITY_ORDER"
        )
        assert "SEVERITY_ORDER" in ast.unparse(assignment.value)

    def test_the_windowing_is_pythons_and_not_the_sessions_timezone(self):
        """``created_at::time`` resolves through an inherited ``TimeZone``.

        ``an-observation-can-be-seasonal``'s warning at the size of a
        cast: the same statement answers differently on a connection
        nobody configured, and neither reading announces itself.  Both
        instants come back aware and the comparison is made in Python
        against one zone, the process's — so the SQL must carry no cast
        at all.
        """
        for statement in (snag_claims.UNREACHABLE_ROWS_SQL, snag_claims.SYSADMIN_RUN_STARTS_SQL):
            assert "::time" not in statement
            assert "TimeZone" not in statement
            assert "AT TIME ZONE" not in statement

    def test_the_population_is_every_unreachable_title_and_not_one_service(self):
        """Rule 1 — the mechanism, never the population it happens to have.

        20 of the family's 23 rows are one service today, and scoping the
        read to it would make the check blind to the estate swapping a
        different unit tomorrow.  The unit the lease names is carried as
        evidence and reaches no query.
        """
        assert "% unreachable" in snag_claims.UNREACHABLE_ROWS_SQL
        assert snag_claims.NIGHTLY_STOPPED_UNIT not in snag_claims.UNREACHABLE_ROWS_SQL

    # -- every way of not-knowing -----------------------------------------

    def test_a_timer_that_is_not_armed_is_unknown(self):
        """The premise is another repository's schedule.

        ``SNAG-SCHED-001``'s check rule, inherited with its holder: a
        claim whose premise has died is not a claim that still holds, so
        an unarmed timer is ``unknown`` and never ``match``.
        """
        with patch.object(
            snag_claims.subprocess,
            "run",
            return_value=SimpleNamespace(stdout="NextElapseUSecRealtime=n/a\n"),
        ):
            measurement = snag_claims.check_nightly_hold_is_loud()
        assert measurement.verdict == "unknown"
        assert "the timer is not armed" in measurement.note

    def test_a_timer_systemd_does_not_know_is_unknown(self):
        with patch.object(
            snag_claims.subprocess, "run", return_value=SimpleNamespace(stdout="")
        ):
            measurement = snag_claims.check_nightly_hold_is_loud()
        assert measurement.verdict == "unknown"
        assert "is not a timer systemd knows" in measurement.note

    def test_a_silent_database_is_unknown(self):
        silent = ([], "the database did not answer (OperationalError)")
        with patch.object(snag_claims, "query_rows", return_value=silent):
            assert snag_claims.check_nightly_hold_is_loud().verdict == "unknown"


# ---------------------------------------------------------------------------
# Movement — the header paragraph's figure, derived
# ---------------------------------------------------------------------------


class _Parser:
    """A ``read_snags`` stand-in keyed on the text it is handed.

    Keyed on the *text* rather than counting calls, because the two reads
    :func:`measure_movement` makes — the worktree and the anchor — differ
    only in what they are given, and a call-order stand-in would pass
    against an implementation that read the same document twice.
    """

    def __init__(self, answers: dict[str, tuple[int, int]], default=None, raises=False):
        self.answers = answers
        self.default = default
        #: Whether an unanswerable text arrives as a raise rather than as
        #: an empty read.  Both shapes are real and neither is a version
        #: this repository chooses: ``read_snags`` returned
        #: ``([], "unrecognised")`` until estate-manager's message
        #: ``99679328`` (2026-08-29) closed our ``5a8bbc97`` by raising
        #: ``UnreadableSnagText`` instead, and ``estate-lib`` is an
        #: editable install, so the parser is whichever revision of their
        #: working tree is checked out.
        self.raises = raises
        self.seen: list[str] = []

    def __call__(self, text: str):
        self.seen.append(text)
        answer = self.answers.get(text, self.default)
        if answer is None:
            if self.raises:
                raise ValueError(
                    "read_snags takes a document's text, and this looks like a path"
                )
            return [], "unrecognised"
        total, open_count = answer
        rows = [SimpleNamespace(is_open=index < open_count) for index in range(total)]
        return rows, "bullet"


class TestTheMovementIsDerived:
    """The header paragraph's figure, measured rather than read (Session 120).

    ``docs/roadmap/snag_list.md`` opens with a paragraph recording what
    moved this sitting, and nothing read it: measured 2026-08-28 it was
    **six sittings stale**, last written for Session 111 at 99 entries /
    22 open against a live 100 / 17.  The owner's ruling of 2026-08-29 was
    to derive the figure rather than check the prose, so these tests are
    written against the ways a derivation goes quietly wrong — an empty
    read served as a count, a failed anchor served as "unmoved", and two
    parsers agreeing by not being compared.
    """

    @staticmethod
    def _finding(
        tmp_path,
        *,
        current: tuple[int, int] | None,
        anchor: tuple[int, int] | None | str = None,
        entries=(),
        parser_problem: str = "",
        parser_raises: bool = False,
    ):
        """Drive :func:`check_movement` against a stand-in parser.

        ``anchor`` is the anchor revision's counts, or the string
        ``"unreadable"`` for a ``git show`` that did not answer.
        """
        document = tmp_path / "snag_list.md"
        document.write_text("worktree", encoding="utf-8")
        answers = {"worktree": current} if current else {}
        if isinstance(anchor, tuple):
            answers["anchor"] = anchor
        parser = _Parser(answers, raises=parser_raises)
        read = None if parser_problem else parser
        with (
            patch.object(snag_claims, "owning_parser", lambda: (read, parser_problem)),
            patch.object(
                snag_claims,
                "document_at",
                lambda _rev, _path: (None, "no history") if anchor is None else ("anchor", ""),
            ),
            patch.object(snag_claims, "anchor_commit", lambda _rev: ("abc1234", "a subject")),
            patch.object(snag_claims, "instrument_state", lambda _p: "read with a stand-in"),
        ):
            return snag_claims.check_movement(list(entries), document)

    def test_an_empty_read_is_unknown_and_never_a_count(self, tmp_path):
        """Session 119's published wrong answer, refused.

        ``read_snags`` takes the document's *text*; handed a path it
        returns zero rows and a dialect of ``unrecognised``, and the
        figure published off that read ``100 → 0 entries, 17 → 0 open`` —
        every entry closed, stated confidently.  Falsified by deleting
        ``parser_counts``' ``if not rows`` gate, which makes this finding
        read ``0 entries, 0 open`` at ``match``.
        """
        finding = self._finding(tmp_path, current=None)
        assert finding.verdict == "unknown"
        assert "read no entry" in finding.note
        assert "0 entries" not in finding.note

    def test_a_read_that_raises_is_unknown_for_the_same_reason(self, tmp_path):
        """The same not-knowing, in the shape the owner moved it to.

        Our message ``5a8bbc97`` said an empty read with a dialect of
        ``unrecognised`` reads as an emptied register rather than as a
        type error; estate-manager closed it on 2026-08-29 (message
        ``99679328``) by raising ``UnreadableSnagText``, a ``ValueError``,
        instead.  Both shapes must land on ``unknown``, and both are
        reachable — ``estate-lib`` is an editable install, so the parser
        is whichever revision of their tree is checked out, and a
        genuinely entry-free document is an empty read under any version.
        Falsified by narrowing :func:`parser_counts`' ``except`` to
        ``TypeError``, which turns this into an error rather than a
        verdict.
        """
        finding = self._finding(tmp_path, current=None, parser_raises=True)
        assert finding.verdict == "unknown"
        assert "read no entry" in finding.note
        assert "0 entries" not in finding.note

    def test_a_parser_that_will_not_import_is_unknown_and_says_so(self, tmp_path):
        """Rule 5.  The instrument is another repository's, so it can go.

        ``estate-lib`` is an editable install pointing into their working
        tree; a move, a rename or a syntax error over there is a reason to
        know less and never a reason to report no movement.
        """
        finding = self._finding(
            tmp_path, current=(101, 18), parser_problem="estate.snags could not be imported (X)"
        )
        assert finding.verdict == "unknown"
        assert "could not be imported" in finding.note

    def test_an_unreadable_anchor_is_unknown_and_not_unmoved(self, tmp_path):
        """The failure this derivation could most easily have hidden.

        A ``git show`` that does not answer leaves no previous counts, and
        the tempting default is to compare the document against itself —
        which reports ``unmoved`` for a sitting that moved everything.
        Falsified by defaulting ``was_entries``/``was_open`` to the
        current figures, which turns this green at ``match``.
        """
        finding = self._finding(tmp_path, current=(101, 18), anchor=None)
        assert finding.verdict == "unknown"
        assert "was not measured" in finding.note
        assert "unmoved" not in finding.note
        assert "could not be parsed" in " ".join(finding.detail)

    def test_no_movement_is_said_out_loud(self, tmp_path):
        """A blank is what a broken reader produces for free.

        Falsified by returning ``""`` from :attr:`Movement.movement` when
        nothing moved, which renders ``101 entries, 18 open — `` and is
        indistinguishable from a delta the reader failed to compute.
        """
        finding = self._finding(tmp_path, current=(101, 18), anchor=(101, 18), entries=[])
        assert finding.verdict == "match"
        assert finding.note == "101 entries, 18 open — unmoved since abc1234"

    @pytest.mark.parametrize(
        ("anchor", "expected"),
        [
            ((100, 17), "+1 entry and +1 open since abc1234"),
            ((100, 18), "+1 entry since abc1234"),
            ((102, 19), "-1 entry and -1 open since abc1234"),
            ((99, 18), "+2 entries since abc1234"),
        ],
    )
    def test_the_delta_is_named_in_both_directions(self, tmp_path, anchor, expected):
        """Named rather than counted, and pluralised where it matters.

        The one-opened case is the founding measurement: parsing
        ``git show HEAD~1:docs/roadmap/snag_list.md`` gave 100 / 17
        against HEAD's 101 / 18, precisely what Session 119 wrote by hand.
        """
        finding = self._finding(tmp_path, current=(101, 18), anchor=anchor)
        assert finding.verdict == "match"
        assert finding.note.endswith(expected)

    def test_the_two_parsers_disagreeing_about_open_is_red(self, tmp_path):
        """The finding's discriminating witness, and its only red state.

        ``read_entries`` sweeps this register; ``read_snags`` is what the
        estate board publishes about this repository.  A divergence means
        those two figures have come apart — an entry filed under ``Fixed
        Issues`` that never declared closure is the reachable case — and
        ``TestAgainstTheOwningParser`` pins the same pair only when the
        suite runs.  This asks it at the start of every sitting.
        """
        finding = self._finding(
            tmp_path, current=(101, 18), anchor=(101, 18), entries=read_entries(DOCUMENT)
        )
        assert finding.verdict == "mismatch"
        assert "18" in finding.note and "2" in finding.note
        assert "have come apart" in finding.note

    def test_the_totals_are_deliberately_not_compared(self, tmp_path):
        """The two readers measure different populations by design.

        ``read_snags`` reads the whole file — 101 rows here, 76 of them
        under the open headings — so a total-versus-total comparison would
        report a mismatch on every run.  Falsified by comparing
        ``entries`` against ``len(entries)``, which turns this red.
        """
        entries = read_entries(DOCUMENT)
        finding = self._finding(
            tmp_path,
            current=(101, sum(entry.is_open for entry in entries)),
            anchor=(101, 2),
            entries=entries,
        )
        assert finding.verdict == "match"
        assert "101 entries" in finding.note

    def test_one_reader_alone_is_unknown_rather_than_agreement(self, tmp_path):
        """``ports_checked``'s rule at the size of a comparison.

        An empty entry list is this module's reader having read nothing,
        which is not the two parsers agreeing.
        """
        movement = snag_claims.Movement(
            entries=101,
            open_entries=18,
            was_entries=101,
            was_open=18,
            anchor="abc1234",
            anchor_subject="a subject",
            dialect="bullet",
            local_open=None,
            instrument="",
        )
        assert movement.readers_agree is None

    def test_a_document_outside_the_checkout_has_no_history(self, tmp_path):
        """``document_at`` refuses a path it cannot name a revision for.

        Driven at the real function rather than a stand-in, because the
        ``relative_to`` guard is the whole of it.
        """
        text, problem = snag_claims.document_at("HEAD", tmp_path / "elsewhere.md")
        assert text is None
        assert "outside" in problem


class TestTheMovementAgainstTheRealDocument:
    """The live half.  Nothing here is a stand-in.

    Its counterpart above proves the branches; this proves the wiring —
    that the owning parser imports, that ``git show`` answers in this
    checkout, and that the figure the report prints is the one the
    document holds.
    """

    def test_the_real_document_is_measured_and_the_readers_agree(self):
        finding = snag_claims.check_movement(read_entries(SNAG_PATH.read_text(encoding="utf-8")))
        assert finding.key == "convention:movement"
        assert finding.verdict == "match", finding.note
        assert "entries" in finding.note

    def test_the_instrument_is_named_with_its_checkout_state(self):
        """A cross-repo instrument records whose tree produced the figure.

        The path is resolved from the *imported object*, never
        constructed: ``ESTATE_SERVICE`` names their ``service/``
        directory and this parser lives in ``lib/``, so a built path would
        report the checkout state of a file nothing read.
        """
        read_snags, problem = snag_claims.owning_parser()
        assert read_snags is not None, problem
        state = snag_claims.instrument_state(read_snags)
        assert "estate" in state
        assert "committed" in state or "uncommitted" in state

    def test_the_report_carries_the_line(self):
        """It is published in every state, ``SNAG-DOCS-006``'s rule."""
        keys = [finding.key for finding in check_all()]
        assert keys.count("convention:movement") == 1
        assert keys[-1] == "convention:movement"


class TestTheBannerReaderIsClosureAware:
    """``list_open`` — the count the session banner prints.

    ``claude-preflight.sh`` counted ``^- \\[P[0-9]\\]`` under
    ``## Open Issues`` until 2026-08-29, which is every bullet in the
    section whatever its title says: the banner printed **76 open** eight
    lines below this script's **18 open entries**, and the first ten rows
    of its list were titled **FIXED**.
    """

    def test_a_closed_entry_under_an_open_heading_is_not_listed(self, tmp_path, capsys):
        """The founding defect, at the size of the fixture.

        ``SNAG-FAKE-002``'s title declares closure and it sits under
        ``## Open Issues``; the old grep listed it.  Falsified by dropping
        the ``entry.is_open`` filter, which prints three lines.
        """
        document = tmp_path / "snag_list.md"
        document.write_text(DOCUMENT, encoding="utf-8")
        assert snag_claims.list_open(document) == 0
        listed = capsys.readouterr().out.splitlines()
        assert len(listed) == 2
        assert not any("SNAG-FAKE-002" in line for line in listed)
        assert all(not line.startswith("- ") for line in listed)

    def test_an_unreadable_document_exits_two_and_prints_nothing(self, tmp_path, capsys):
        """``ports_checked`` at the size of a console script.

        The caller renders empty stdout as "none open", so a document that
        could not be read must not produce it silently.  Falsified by
        returning ``EXIT_STATUS["match"]``, which makes the banner print
        "None — all clear" for a missing file.
        """
        assert snag_claims.list_open(tmp_path / "absent.md") == 2
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "could not be read" in captured.err

    def test_the_flag_runs_no_check(self, tmp_path, capsys):
        """It is a document reader, not a claims report.

        Driven through ``main`` because the flag is the contract: a
        listing that also ran the register would take a minute and could
        exit ``1``, which the banner reads as "could not be counted".
        """
        document = tmp_path / "snag_list.md"
        document.write_text(DOCUMENT, encoding="utf-8")
        status = main(["--snag-file", str(document), "--list-open"])
        assert status == 0
        assert capsys.readouterr().out.count("\n") == 2

    def test_the_reader_is_the_one_the_register_counts_with(self):
        """The whole point: one implementation of ``open``.

        A shell approximation of :func:`closure_declared` would be a
        second statement of it, free to drift from the figure printed
        eight lines above it in the same banner — which is the defect,
        not a cheaper way to have it.
        """
        entries, problem = load_entries()
        assert not problem
        listed = sum(1 for entry in entries if entry.is_open)
        movement = snag_claims.check_movement(entries)
        assert f"{listed} open" in movement.note


class TestTheReloadCoherenceCheck:
    """``SNAG-CFG-003`` — and the pair that makes an absence measurable.

    The claim is that nothing on the reload path judges a configuration
    coherent, which is a *negative* about behaviour: one drive can only
    observe that the reload said nothing in particular, and it says
    nothing in particular about every configuration.  Two specimens that
    differ in coherence and are identical in delivery are what turn that
    into a difference somebody has to explain.

    Each fix the entry's last bullet leaves open is driven here as a
    stand-in, because a check that cannot see the fix is coupled to the
    unfixed behaviour and reads a landed fix as a broken probe.
    """

    #: The order ``reload_coherence_reading`` drives its specimens in:
    #: coherent, the same coherent one again (which is what measures
    #: volatility), then the violating one.
    COHERENT, REPEAT, VIOLATING = 0, 1, 2

    @staticmethod
    def _payloads():
        """A real reading from the live drive, to build stand-ins from."""
        reading, problem = snag_claims.reload_coherence_reading()
        assert reading is not None, problem
        return reading

    @classmethod
    def _through(cls, violating=None, loud=(), every=None):
        """The real drive, with the violating one's report decorated.

        **A stand-in that reports a verdict without installing the
        configuration models no fix at all.**  Fix shapes two and three
        install exactly as today's reload does and additionally say
        something, so the drive has to happen; a stand-in that skipped it
        is refused by the installed-witness, which is what four of these
        tests did until they called through.  Only shape one — a refusal
        — legitimately installs nothing, and it is driven without this.

        ``every`` decorates all three drives, which is how a key that
        moves between two identical runs is modelled.
        """
        real = snag_claims._reload_drive
        counter = itertools.count()

        def drive(config_path, services_path, sync):
            payload, seen = real(config_path, services_path, sync)
            nth = next(counter)
            if every is not None:
                payload = dict(payload, **every(nth))
            if nth == cls.VIOLATING:
                payload = dict(payload, **(violating or {}))
                seen = tuple(seen) + tuple(loud)
            return payload, seen

        return drive

    def test_it_holds_on_this_box(self):
        assert snag_claims.check_reload_unjudged_config().verdict == "match"

    def test_the_shipped_configuration_is_put_back(self):
        """Rule 5, and the reason it is asserted rather than trusted.

        ``check_all`` runs sixteen further checks behind this one, and
        every one of them reads ``get_config()``.
        """
        before = get_config()
        snag_claims.check_reload_unjudged_config()
        assert get_config() is before

    def test_the_violating_specimen_really_is_installed(self):
        """The witness: the drive must be able to say the reload took it."""
        reading = self._payloads()
        assert reading.installed
        assert reading.ceiling_installed == reading.ceiling_violating
        assert reading.ceiling_violating >= reading.reminder
        assert reading.ceiling_coherent < reading.reminder

    def test_a_refusing_reload_is_the_fix_and_not_an_unmeasurable_drive(self):
        """Fix shape one, and the ordering it caught.

        A reload that refuses installs nothing, so the installed-witness
        answers "the drive did not take" about the strongest fix there
        is.  Driven at exactly that, the verdict must be ``mismatch``.
        """
        live = self._payloads()
        base = live.payload_coherent
        drives = [(dict(base, reloaded_at=f"t{n}"), ()) for n in (0, 1)]
        drives.append((dict(base, ok=False, error="incoherent", reloaded_at="t2"), ()))
        with patch.object(snag_claims, "_reload_drive", side_effect=drives):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "mismatch"
        assert "refused" in measurement.note

    def test_a_reload_that_claims_success_and_installs_nothing_is_unknown(self):
        """Why the witness reads the singleton and not the specimen back.

        The two are the same number whenever the reload installs, so a
        mutation swapping them passed against every other test here and
        named this one as the gap.  ``ok=True`` with nothing installed is
        a drive that did not take, and reporting it as ``match`` would
        credit the entry to a reload that never happened — the shape
        ``ports_checked`` refuses, one composition root over.
        """
        live = self._payloads()
        base = live.payload_coherent
        drives = [(dict(base, reloaded_at=f"t{n}"), ()) for n in (0, 1, 2)]
        with patch.object(snag_claims, "_reload_drive", side_effect=drives):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "unknown"
        assert "did not take" in measurement.note

    def test_a_verdict_added_to_the_report_is_seen(self):
        """Fix shape two: the entry's own words, a key beside the report."""
        drive = self._through(violating={"incoherent": ["reminder_ceiling"]})
        with patch.object(snag_claims, "_reload_drive", side_effect=drive):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "mismatch"
        assert "semantic verdict" in measurement.note

    def test_a_warning_logged_only_for_the_violating_config_is_seen(self):
        """Fix shape three: install it and say so, payload untouched.

        The shape a comparison over the report alone would miss, which is
        why the drive captures the root logger as well.
        """
        drive = self._through(loud=("sysadmin.reload:config_incoherent",))
        with patch.object(snag_claims, "_reload_drive", side_effect=drive):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "mismatch"

    def test_a_warning_both_drives_emit_is_not_a_verdict(self):
        """The other half of that: a noisy box is not a fix.

        An unrelated warning appears on both sides and must cancel, or
        the check reports the entry refuted by whatever else logged.
        """
        real = snag_claims._reload_drive

        def drive(config_path, services_path, sync):
            payload, seen = real(config_path, services_path, sync)
            return payload, (*seen, "py.warnings:deprecated")

        with patch.object(snag_claims, "_reload_drive", side_effect=drive):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "match"

    def test_a_key_that_moves_between_identical_drives_is_discounted(self):
        """Why the exclusion is measured and not written down.

        The first run of this check reported ``mismatch`` — the fix
        landed — because ``reloaded_at`` is a wall clock stamped per
        call.  A second key behaving the same way must be discounted for
        the same reason and without an edit here.
        """
        drive = self._through(every=lambda nth: {"served_by": f"pid-{nth}"})
        with patch.object(snag_claims, "_reload_drive", side_effect=drive):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "match"
        assert any("served_by" in line for line in measurement.detail)

    def test_reloaded_at_is_what_it_discounts_here(self):
        """Measured on this box rather than assumed of it."""
        assert self._payloads().volatile == ("reloaded_at",)

    def test_reminders_switched_off_reach_no_verdict(self, tmp_path):
        """The guard skips there, and a check that cannot look says so.

        With no repeat due there is no ceiling to breach, so a drive
        would measure the reload's indifference to a configuration that
        violates nothing — ``match`` off a vacuous specimen.
        """
        # The import is function-local, so the name resolves from the
        # owning module at call time and that is where the stand-in goes.
        import sysadmin_tray.config as tray_config

        with patch.object(
            tray_config,
            "load_tray_config",
            return_value=SimpleNamespace(reminder_hours=0),
        ):
            measurement = snag_claims.check_reload_unjudged_config()
        assert measurement.verdict == "unknown"
        assert "reminders are off" in measurement.note

    def test_the_note_says_which_installer_it_measured(self):
        """Rule 3: the reload is not the only one, and silence would read
        as the whole claim."""
        detail = snag_claims.check_reload_unjudged_config().detail
        assert any("a restart installs the same file" in line for line in detail)

    def test_the_check_is_registered_against_its_entry(self):
        check = snag_claims.CHECKS["reload_unjudged_config"]
        assert check.snag == "SNAG-CFG-003"
        assert check.run is snag_claims.check_reload_unjudged_config


# ---------------------------------------------------------------------------
# SNAG-TEST-002 — the fourth sweep over CHECKS
# ---------------------------------------------------------------------------
#
# The three sweeps in :class:`TestTheRealDocument` ask whether the register
# and the registry agree about *which* entries are measured.  None of them
# asks whether a check can say it does not know, which is the property the
# whole file leans on: every live read here reaches the database through
# ``snag_claims.query_one``, whose every way of not-knowing returns
# ``unknown`` rather than ``match``, and each drive asserts that branch by
# name.  Eighteen checks, eighteen classes doing it — by habit.
#
# ``tests/test_live_drive_premises.py`` exempts this file from rule 2 on
# exactly that habit (:data:`~tests.test_live_drive_premises.PRE_CONVENTION`),
# so the exemption rested on something nothing enforced.  It is enforced
# here now.  The check that measured the gap retired with the entry on
# 2026-08-30; its walk did not, and this is where it lives.

#: This file: the drive the sweep reads, and the file whose habit it holds.
OWNER = Path(__file__).resolve()

#: The verdict a check returns when it cannot answer.
#:
#: One spelling, because :func:`_unknown_branch_coverage` searches for this
#: exact constant and a second copy could drift from the one the checks
#: really return — ``max_priority_for`` against ``PRIORITY_MAP``.
NOT_KNOWING = "unknown"

#: Registered checks that cannot be driven to :data:`NOT_KNOWING`, each
#: mapped to the reason it cannot.
#:
#: The claim the sweep makes is about the **test**, never about the
#: producer.  A check whose every input is local — a file this repository
#: owns, an AST walk over it — may have no way of not-knowing to reach,
#: and demanding a drive for one would be demanding a branch that does not
#: exist.  So such a check discharges the rule by a *declaration* somebody
#: wrote down, the way ``PRE_CONVENTION`` discharges rule 2 one file over:
#: a name here is a decision, never a way to be green, and
#: :meth:`TestEveryCheckCanSayItDoesNotKnow.test_no_exemption_is_stale`
#: refuses one that has since been driven after all.
#:
#: **Empty, and measured rather than assumed** — all eighteen registered
#: checks read something they can fail to read, and all eighteen are
#: driven to the branch that says so.
UNKNOWABLE: dict[str, str] = {}


def _unwritable_sentinel() -> str:
    """A verdict spelling no source file can contain, minted per call.

    The witness below asks what the walk reports for a verdict nothing
    asserts, so the answer must be zero *by construction* rather than by
    nobody having typed it.  A literal is not that: the first drive of
    this walk wrote its own sentinel into this file and the walk duly
    found it, reporting coverage for a verdict that does not exist — the
    witness refuted by the act of testing it, which is
    ``a-control-a-fix-breaks-is-not-a-control`` at the size of a string.
    """
    return f"no verdict is spelled this {uuid.uuid4().hex}"


def _unknown_branch_coverage(
    tree: ast.Module, keys: set[str], sentinel: str = NOT_KNOWING
) -> set[str]:
    """Check keys reached by a class asserting a *sentinel* verdict.

    Keyed on the enclosing class rather than on the test, because the
    drives here put the check under test in the class name and its
    stand-ins in the methods — so a method-level walk would report the
    file's naming habits rather than its coverage.

    **The looseness is deliberate and is stated rather than tightened.** A
    class that names a key only in passing while asserting ``unknown``
    about a different one counts as coverage: ``TestTheQueueTimezoneCheck``
    names ``sysd_ollama_ordering`` that way today.  So this is a floor on
    the habit and not a proof of it — every key it reports is also
    reported by the class that owns it, measured, and a sweep that
    demanded sole ownership would be a different claim from the one
    ``SNAG-TEST-002`` recorded.

    *sentinel* is a parameter for one reason: passing a spelling no test
    contains must empty the result.  That is the witness the sweep drives,
    and without it a walker that had stopped seeing anything reports full
    coverage exactly as a healthy one does.
    """
    covered: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        named = {key for key in keys if key in ast.unparse(node)}
        if not named:
            continue
        asserts_sentinel = any(
            isinstance(inner, ast.Constant) and inner.value == sentinel
            for inner in ast.walk(node)
        )
        if asserts_sentinel:
            covered |= named
    return covered


def _unknown_drive_gaps(
    tree: ast.Module, keys: set[str], exempt: dict[str, str] | None = None
) -> list[str]:
    """Registered checks that no class drives to :data:`NOT_KNOWING`.

    The sweep's body, lifted out so it can be driven at a stand-in — a
    sweep that reads only the real file can report what happens to be in
    it and nothing else, which is a detector nobody has watched fail.
    ``test_live_drive_premises._dodges_the_rule`` is composed out for the
    same reason.
    """
    exempt = UNKNOWABLE if exempt is None else exempt
    return sorted(keys - _unknown_branch_coverage(tree, keys) - set(exempt))



class TestEveryCheckCanSayItDoesNotKnow:
    """The fourth sweep over ``CHECKS`` (``SNAG-TEST-002``, closed 2026-08-30).

    Every check in the registry must be driven to a ``unknown`` verdict by
    a test in the class that names it, or be declared unable to reach one
    in :data:`UNKNOWABLE`.  The habit held eighteen of eighteen times
    before this existed; what it did not have was anything making it hold
    for a nineteenth.

    The order below is load-bearing.  The witness comes first, because
    full coverage is the observation the whole sweep rests on and a walk
    that had stopped reading assertions reports it exactly as a healthy
    one does — so the sweep is vacuous until the witness has fired.
    """

    def _tree(self) -> ast.Module:
        return ast.parse(OWNER.read_text(encoding="utf-8"))

    def _own_class(self) -> ast.ClassDef:
        """This class's own source, found by the name it already has.

        ``type(self).__name__`` rather than a constant beside the class:
        a written-out name is a second statement of a fact the class
        already carries, and the two can disagree.  Driven — with the
        name restated as a constant, pointing it at a *different* clean
        class left every test here green, so the pin below was pinned to
        whatever the constant said rather than to the sweep.
        """
        name = type(self).__name__
        found = [
            node
            for node in ast.walk(self._tree())
            if isinstance(node, ast.ClassDef) and node.name == name
        ]
        assert len(found) == 1, f"{name} is not a class in this file exactly once"
        return found[0]

    # -- the witness, first ----------------------------------------------

    def test_a_verdict_no_test_contains_reaches_nothing(self):
        """Nothing below this means anything until it has passed.

        A walk that matched a class by *name* rather than by its
        assertions would report every check covered whatever the drives
        assert, and the coverage figure would be full for a reader that
        had stopped reading.  Driven at the real file with a spelling
        minted per call, which must reach zero.
        """
        blind = _unknown_branch_coverage(
            self._tree(), set(CHECKS), sentinel=_unwritable_sentinel()
        )
        assert blind == set(), (
            "the walk reports coverage for a verdict no test contains, so it "
            f"is not reading assertions: {sorted(blind)}"
        )

    def test_the_sentinel_cannot_be_written_into_the_file_it_reads(self):
        """Why the sentinel is minted rather than named — found by this drive.

        The first version was a literal, and writing it into a test here
        made the walk find it: two checks reported covered by a verdict
        nothing returns, so the witness passed while measuring its own
        source.  Two mints must differ, or the next literal is one
        copy-paste away.
        """
        assert _unwritable_sentinel() != _unwritable_sentinel()
        assert NOT_KNOWING not in _unwritable_sentinel()

    def test_the_registry_is_not_empty(self):
        """``ports_checked``'s rule: zero-because-blind is never clean.

        With no keys the coverage set is empty, the gap list is empty, and
        the sweep passes over nothing at all — which reads exactly like a
        habit holding.
        """
        assert CHECKS, "no checks are registered, so there is no habit to enforce"

    # -- the sweep --------------------------------------------------------

    def test_every_registered_check_is_driven_to_unknown(self):
        """The habit, promoted from a measurement into a guard.

        A check that ships asserting ``match`` with no drive to its
        not-knowing branch would report an entry holding hardest on the
        morning its own reader broke — the unmarked-sentence check's
        founding argument, turned on the family that made it.

        (Written without spelling that check's key, which
        :meth:`test_the_sweeps_own_class_names_no_registered_check`
        refuses and caught on this docstring's first draft.)
        """
        gaps = _unknown_drive_gaps(self._tree(), set(CHECKS))
        assert gaps == [], (
            "these checks are driven to no "
            f"{NOT_KNOWING!r} verdict by the class that names them, so nothing "
            "here asserts they can say they did not measure: "
            f"{gaps}. Add a drive, or declare the check in UNKNOWABLE with "
            "the reason it cannot reach that branch."
        )

    # -- its falsification ------------------------------------------------

    def test_a_check_no_class_drives_is_reported(self):
        """The sweep's own witness — without it, full coverage proves nothing.

        A registered key nothing in this file mentions must come back as a
        gap.  Spelled through :func:`_unknown_drive_gaps` rather than the
        walk beneath it, so what is falsified is the sweep and not one of
        its parts.
        """
        absent = f"a_check_no_drive_names_{uuid.uuid4().hex}"
        gaps = _unknown_drive_gaps(self._tree(), set(CHECKS) | {absent})
        assert gaps == [absent]

    def test_a_check_named_without_the_verdict_is_reported(self):
        """The nearer miss: named by a class, and by one that never says it.

        A walk keyed on the class *name* alone would report this covered,
        which is the shape :meth:`test_a_verdict_no_test_contains_reaches_nothing`
        refuses from the other end.
        """
        tree = ast.parse(
            "class TestAlpha:\n"
            "    def test_it_holds(self):\n"
            '        assert check_alpha().verdict == "match"\n'
        )
        assert _unknown_drive_gaps(tree, {"alpha"}) == ["alpha"]

    def test_a_check_named_with_the_verdict_is_not(self):
        """The same stand-in, one assertion later — or the test above is
        reporting the specimen rather than the rule."""
        tree = ast.parse(
            "class TestAlpha:\n"
            "    def test_it_holds(self):\n"
            '        assert check_alpha().verdict == "match"\n'
            "    def test_a_blind_reader_is_unknown(self):\n"
            '        assert check_alpha().verdict == "unknown"\n'
        )
        assert _unknown_drive_gaps(tree, {"alpha"}) == []

    def test_coverage_is_keyed_on_the_class_and_not_the_method(self):
        """The drives name the check in the class and its stand-ins in methods.

        A method-level walk would ask whether the one test asserting
        ``unknown`` also happens to spell the check's key, which most do
        not.
        """
        tree = ast.parse(
            "class TestAlpha:\n"
            "    def test_it_holds(self):\n"
            '        assert check_alpha().verdict == "match"\n'
            "    def test_a_blind_reader_is_unknown(self):\n"
            '        assert something().verdict == "unknown"\n'
        )
        assert _unknown_branch_coverage(tree, {"alpha"}) == {"alpha"}

    # -- the declaration --------------------------------------------------

    def test_an_exemption_discharges_the_sweep(self):
        """What :data:`UNKNOWABLE` buys, driven while it is empty.

        The escape hatch is what keeps the sweep from demanding a branch
        that cannot exist, and an empty dict is a mechanism nobody has
        watched work — ``SNAG-UNITS-006``'s standing, one file over.
        """
        tree = ast.parse("class TestAlpha:\n    pass\n")
        assert _unknown_drive_gaps(tree, {"alpha"}) == ["alpha"]
        assert _unknown_drive_gaps(tree, {"alpha"}, exempt={"alpha": "why"}) == []

    def test_no_exemption_is_stale(self):
        """A declared exemption that has since been driven is doing nothing.

        The next reader cannot tell an entry carrying the file from one
        that has been overtaken, which is how a hand-written set rots into
        a classification nothing checks — ``FROZEN_TABLES``' rule, and
        ``test_no_exempted_file_has_since_marked_a_premise``'s.
        """
        covered = _unknown_branch_coverage(self._tree(), set(CHECKS))
        overtaken = sorted(set(UNKNOWABLE) & covered)
        assert overtaken == [], (
            f"these are driven to {NOT_KNOWING!r} after all, so the exemption "
            f"is no longer load-bearing — drop them from UNKNOWABLE: {overtaken}"
        )

    def test_no_exemption_names_a_check_nobody_registers(self):
        """The other way it outlives its reason: the check itself has gone."""
        orphans = sorted(set(UNKNOWABLE) - set(CHECKS))
        assert orphans == [], f"UNKNOWABLE names unregistered checks: {orphans}"

    def test_every_exemption_carries_a_reason(self):
        """A name with no reason is a way to be green.

        The dict is a mapping rather than a set for this alone: the value
        is what a later sitting reads to decide whether the exemption is
        still true.
        """
        blank = sorted(key for key, why in UNKNOWABLE.items() if not why.strip())
        assert blank == [], f"UNKNOWABLE entries with no stated reason: {blank}"

    # -- the sweep's own class --------------------------------------------

    def test_the_sweeps_own_class_names_no_registered_check(self):
        """The walk keys on the class, and this class is one of them.

        A class naming a key and asserting the not-knowing verdict counts
        as coverage, so a docstring here spelling a check's key would make
        the sweep vouch for it — itself.  The durable half is the naming:
        a test *about* the ``unknown`` verdict will grow assertions of it,
        while nothing here needs a key.  Pinned rather than skipped,
        because a skip is a second rule to remember and this is the same
        fact as a red test.

        It fired on its own first two drafts, which is the cheapest
        evidence that it discriminates — first on the sweep's docstring
        above, which cited the unmarked-sentence check by key, and then on
        *this* docstring, for naming the key while explaining that naming
        it is what is forbidden.  ``test_live_drive_premises.py`` exempts
        its owner for the same reason; there is no exemption here, so the
        prose is written around the key instead.
        """
        named = sorted(
            key for key in CHECKS if key in ast.unparse(self._own_class())
        )
        assert named == [], (
            "the sweep's own class names registered checks, so it reports "
            f"them covered the moment it asserts {NOT_KNOWING!r}: {named}"
        )

    def test_the_walk_would_see_this_class_if_it_did(self):
        """…and the pin above is only worth having if that is reachable.

        Driven at this class's **real** source with both halves appended
        to it — a key it names, and one assertion of the verdict — which
        must come back covered.
        Without it the pin is green because the walk is blind here, and
        blind is indistinguishable from clean.
        """
        key = f"a_key_spliced_in_{uuid.uuid4().hex}"
        spliced = (
            f"{ast.unparse(self._own_class())}\n\n"
            f"    def test_spliced(self):\n"
            f'        """{key}"""\n'
            f"        assert verdict == {NOT_KNOWING!r}\n"
        )
        assert _unknown_branch_coverage(ast.parse(spliced), {key}) == {key}

