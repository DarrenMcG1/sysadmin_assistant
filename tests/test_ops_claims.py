"""The session-opening block, measured against the box (SNAG-ESTATE-008).

``docs/roadmap/STATUS.md`` opens with what a sitting is owed.  Measured on
2026-08-16, all three actions it carried had already been done — two of
them by a party that never touched the document — and it went on asking
for five sittings; on 2026-08-24 the same file asserted a retention
boundary three hours before it happened.  Nothing had ever checked it.

These tests pin the three things that make the check worth having: that a
claim it cannot read is *unknown* rather than agreement, that the two
kinds of failure stay told apart (a stale document and a stale box want
opposite repairs), and that the patterns still find the claims in the real
file — which is the failure mode of the whole mechanism, since a reworded
sentence would otherwise retire the check in silence.
"""

import contextlib
import os
import re
import subprocess
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.routing import APIRoute

from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.ops_claims import (
    CHECK_KEYS,
    CLAIM_PATTERNS,
    CODE_SPAN_RE,
    EXPIRY_FORMAT,
    EXPIRY_NAIVE_FORMAT,
    KEYLESS_CHECKS,
    MARKER_RE,
    MAX_NAMED_ALERTS,
    STATUS_PATH,
    Claim,
    DatabaseFacts,
    Marker,
    UnitState,
    check_alerts,
    check_all,
    check_deploy,
    check_expiry,
    check_markers,
    check_open_titles,
    claim_sentence,
    compare_claim,
    flatten,
    load_region,
    main,
    measure_routes,
    measure_unit,
    overall,
    printed_region,
    read_claim,
    read_markers,
)
from sysadmin.snag_claims import strip_code_spans


@contextlib.contextmanager
def _zone(name: str):
    """Run a block at a nominated timezone, restoring the box's own.

    ``time.tzset`` is what makes ``astimezone()`` move, so the zone cannot
    be injected as an argument: :func:`sysadmin.ops_claims.check_expiry`
    reads the process's idea of local time exactly as the document's own
    author does.  Copied in shape from the ``SNAG-ESTATE-013`` check that
    retired with the entry — the mechanism it drove lives on here.
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


DOCUMENT = """# Project Status Dashboard

> **No deploy is owed.** `sysadmin` was restarted at **2026-08-24 09:58:28**
> and `alerts` holds **2** unresolved rows in total.

## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| API | Complete | **46 routes** across 8 routers; *44 before Session 27* |
| Database | Complete | **14 tables** (15 counting `alembic_version`), head **013** |

---

## Recently Completed

- an older sitting, when there were **99 routes** and head **007**
"""


class TestPrintedRegion:
    def test_it_stops_at_the_heading_after_the_table(self):
        """Rule 1.

        The rest of the file restates old figures on purpose, so a region
        that ran to the end of the document would find two values for
        every claim and report the lot unreadable.  Falsified by widening
        the region: with the whole document passed in, ``routes`` reads
        ``None``.
        """
        region = printed_region(DOCUMENT)
        assert region is not None
        assert "**46 routes**" in region
        assert "**99 routes**" not in region
        assert read_claim(region, "routes") == ("46", "")
        assert read_claim(DOCUMENT, "routes")[0] is None

    def test_it_keeps_the_block_above_the_table(self):
        """The sub-session block is the half the snag was filed about."""
        region = printed_region(DOCUMENT)
        assert region is not None
        assert "restarted at **2026-08-24 09:58:28**" in region

    def test_a_document_with_no_quick_status_is_none_not_empty(self):
        """A guessed region would narrow to nothing and blame the prose.

        ``None`` sends every claim to ``unknown`` naming the *file*, which
        is a different instruction to the reader from "the sentence has
        been reworded".
        """
        assert printed_region("# Something else entirely\n\nno table here\n") is None
        region, problem = load_region(Path("/nonexistent/STATUS.md"))
        assert region is None
        assert "could not be read" in problem


class TestReadClaim:
    def test_a_missing_claim_names_the_pattern_it_looked_for(self):
        value, problem = read_claim("nothing of interest", "routes")
        assert value is None
        assert "routes" in problem

    def test_two_different_figures_are_refused_rather_than_resolved(self):
        """Rule 2.

        Taking the first match would report agreement with whichever half
        happened to be written first, while the document went on
        contradicting itself.  Falsified by ``re.search`` in place of
        ``finditer``: this returns ``"46"`` and passes the wrong way.
        """
        value, problem = read_claim("**46 routes** … later, **47 routes**", "routes")
        assert value is None
        assert "2 different figures" in problem
        assert "46" in problem and "47" in problem

    def test_the_same_figure_twice_is_still_one_claim(self):
        """A block that restates a figure consistently has not drifted."""
        assert read_claim("**46 routes** … still **46 routes**", "routes") == ("46", "")


class TestCompareClaim:
    def test_an_unmeasured_box_is_unknown_and_says_which_side_failed(self):
        """Rule 2 — ``unknown`` is not a flavour of ``mismatch``.

        "The sentence was reworded" and "PostgreSQL is down" call for
        entirely different responses, so the note names the side.
        """
        claim = compare_claim(
            "k", "K", "46", "", None, "the database did not answer (OperationalError)"
        )
        assert claim.verdict == "unknown"
        assert "database did not answer" in claim.note

    def test_an_unreadable_document_is_unknown_not_match(self):
        claim = compare_claim("k", "K", None, "the block states no figure", "46", "")
        assert claim.verdict == "unknown"
        assert "no figure" in claim.note

    def test_agreement_carries_no_note(self):
        claim = compare_claim("k", "K", "46", "", "46", "")
        assert claim.verdict == "match"
        assert claim.note == ""


class TestAlerts:
    def _facts(self, count, titles=()):
        return DatabaseFacts(tables=14, unresolved=count, open_titles=tuple(titles))

    def test_a_rise_says_something_opened_since(self):
        claim = check_alerts("holds **2** unresolved rows", "", self._facts(7))
        assert claim.verdict == "mismatch"
        assert "5 more" in claim.note

    def test_a_fall_says_an_action_may_already_be_done(self):
        """Rule 5, and it is the case the snag was filed for.

        ``SNAG-DB-002``'s eight collation rows resolved themselves when
        estate-manager ran the ``REINDEX``; four documents went on asking
        for it for three days.  A fall is the signal that already existed
        and had no reader.
        """
        claim = check_alerts("holds **8** unresolved rows", "", self._facts(0))
        assert claim.verdict == "mismatch"
        assert "8 fewer" in claim.note
        assert "already be done" in claim.note

    def test_the_open_rows_are_named_and_the_overflow_is_stated(self):
        """A cap that drops rows silently is the roll-up that names nothing."""
        titles = [f"warning: fault {n}" for n in range(MAX_NAMED_ALERTS + 3)]
        claim = check_alerts("holds **8** unresolved rows", "", self._facts(len(titles), titles))
        assert len(claim.detail) == MAX_NAMED_ALERTS + 1
        assert claim.detail[-1] == "… and 3 more"

    def test_no_open_rows_means_no_detail(self):
        claim = check_alerts("holds **0** unresolved rows", "", self._facts(0))
        assert claim.verdict == "match"
        assert claim.detail == ()


class TestDeploy:
    UNIT = UnitState(loaded=True, active_state="active", entered_at=1000.0, main_pid="4242")

    def test_a_source_edit_after_the_start_names_the_file_and_the_remedy(self):
        """Rule 4 — the running process is not serving what is on disk."""
        with patch(
            "sysadmin.ops_claims.newest_source",
            return_value=(REPO_ROOT / "sysadmin" / "main.py", 2000.0),
        ):
            claim = check_deploy(self.UNIT)
        assert claim.verdict == "mismatch"
        assert "kill -TERM 4242" in claim.note
        assert claim.detail and "sysadmin/main.py" in claim.detail[0]

    def test_a_start_after_the_newest_edit_is_a_match(self):
        with patch(
            "sysadmin.ops_claims.newest_source",
            return_value=(REPO_ROOT / "sysadmin" / "main.py", 500.0),
        ):
            claim = check_deploy(self.UNIT)
        assert claim.verdict == "match"

    def test_a_unit_systemd_has_never_heard_of_is_unknown(self):
        """The trap this module exists to remove, in its own measurement.

        ``systemctl show`` answers for a unit that does not exist, exits
        ``0``, and prints ``ActiveState=inactive``.  Read without the
        ``LoadState`` gate that is a timestamp of ``0`` — older than every
        file on disk — so the deploy check would report a restart owed on
        a box where the unit is not installed at all.
        """
        absent = UnitState(loaded=False, active_state="", entered_at=None, problem="not-found")
        claim = check_deploy(absent)
        assert claim.verdict == "unknown"
        assert claim.measured is None


class TestMeasurement:
    def test_systemctl_reports_a_nonexistent_unit_as_not_loaded(self):
        """Driven against the real ``systemctl``, not a stub.

        The whole point of the ``LoadState`` gate is what the binary does
        rather than what a fixture says it does, and a stub written by the
        same hand as the gate would agree with it by construction.
        """
        state = measure_unit("definitely-not-a-unit-8f2a.service")
        assert state.loaded is False
        assert state.entered_at is None
        assert state.problem

    def test_the_route_count_excludes_fastapi_s_own_routes(self):
        """``/openapi.json``, ``/docs``, ``/docs/oauth2-redirect``, ``/redoc``.

        Falsified by ``len(app.routes)``, which is four higher and would
        report the Quick Status table stale on the first sitting anybody
        ran this.
        """
        from sysadmin.main import create_app

        count, problem = measure_routes()
        app = create_app()
        assert problem == ""
        assert count == len([r for r in app.routes if isinstance(r, APIRoute)])
        assert count is not None and count < len(app.routes)


def _verdict(verdict):
    """A Claim carrying nothing but a verdict, for the ranking tests."""
    return Claim("k", "K", "state", None, None, verdict)


class TestOverall:
    def test_a_false_claim_outranks_a_check_that_did_not_run(self):
        """Not ``max()`` over the exit map, which would invert these.

        ``unknown`` is 2 and ``mismatch`` is 1, so the obvious ``max``
        would report a check that failed to run as more urgent than a
        claim measured false.  Falsified by writing it: the second
        assertion returns ``"unknown"``.
        """
        assert overall([_verdict("match"), _verdict("unknown")]) == "unknown"
        assert overall([_verdict("unknown"), _verdict("mismatch")]) == "mismatch"
        assert overall([_verdict("match")]) == "match"

    def test_the_exit_map_is_the_schema_check_s(self):
        """One vocabulary for both checks, imported rather than restated."""
        assert EXIT_STATUS == {"match": 0, "mismatch": 1, "unknown": 2}


class TestAgainstTheRealDocument:
    """The live half.  These are what fire the day the block is reworded."""

    @pytest.mark.premise
    def test_every_pattern_finds_its_claim_in_the_real_status_file(self):
        """A check whose subject silently disappears is no check at all.

        This is the one assertion that cannot be satisfied by editing this
        file: it reads ``docs/roadmap/STATUS.md`` as it stands.  If it
        fails, either the block moved or a sentence was rewritten, and the
        answer is to re-anchor the pattern — not to delete the claim.

        **The premise for this class, and it is about the document rather
        than the box** (`SNAG-TEST-007`, 2026-09-05).  ``assert region is
        not None`` is ordered first so a failure names the missing block;
        everything after it is a dict comprehension over
        :data:`CLAIM_PATTERNS`, which is empty — and therefore green —
        for a region nothing could be read out of.

        The file reaches the box too: :func:`check_all` runs the state
        checks, which dial 8500 and query the live ``alerts`` table, and
        that is the property ``tests/test_live_drive_premises.py`` now
        keys on.  No premise is owed for *that* half and the reason is
        worth stating rather than leaving as silence — nothing here
        believes a negative about the box.  ``test_the_state_checks_run
        _even_with_no_document`` asserts the ``schema`` verdict is one of
        the three the vocabulary admits and that the document-shaped
        claims all read ``unknown``; ``test_main_exits_through_the_shared
        _map`` asserts the exit code is in the map.  Both hold whether or
        not 8500 answered, deliberately, because ``unknown`` is what this
        module returns for every way of not-knowing — the premise is
        enforced in the producer, which is :data:`PRE_CONVENTION`'s
        argument for ``test_snag_claims.py`` arriving one module over.
        """
        region, problem = load_region()
        assert region is not None, problem
        unreadable = {
            key: read_claim(region, key)[1]
            for key in CLAIM_PATTERNS
            if read_claim(region, key)[0] is None
        }
        assert not unreadable, f"STATUS.md no longer states: {unreadable}"

    def test_the_documented_restart_parses_as_a_time(self):
        region, _ = load_region()
        assert region is not None
        stamp, _ = read_claim(region, "daemon_start")
        assert stamp is not None
        datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")

    def test_the_state_checks_run_even_with_no_document(self):
        """A missing document is a reason to know less about the document.

        It is never a reason to stop asking whether the box is behind its
        checkout, which is the half that costs an outage.
        """
        claims = check_all(Path("/nonexistent/STATUS.md"))
        by_key = {claim.key: claim for claim in claims}
        assert by_key["schema"].verdict in {"match", "mismatch", "unknown"}
        assert by_key["schema"].kind == "state"
        assert all(claim.verdict == "unknown" for claim in claims if claim.kind == "claim")

    def test_main_exits_through_the_shared_map(self, capsys):
        code = main(["--status-file", str(STATUS_PATH)])
        printed = capsys.readouterr().out
        assert code in EXIT_STATUS.values()
        assert printed.splitlines()


class TestTheWrapperNeverEdits:
    """Rule 6 — it reports, the sitting edits.

    ``tests/test_schema_guard.py`` asserts the word ``upgrade`` appears in
    no executable line of ``check-migrations.sh``, for the same reason: the
    only place a future edit would put the forbidden behaviour is the
    script, and an assertion about prose would not catch it.
    """

    SCRIPT = REPO_ROOT / "scripts" / "check-ops-claims.sh"

    def test_it_exists_and_is_executable(self):
        import os

        assert self.SCRIPT.is_file()
        assert os.access(self.SCRIPT, os.X_OK)

    def test_no_executable_line_writes_to_a_document(self):
        lines = [
            line
            for line in self.SCRIPT.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        body = "\n".join(lines)
        assert "sed -i" not in body
        assert "STATUS.md" not in body
        assert ">>" not in body

    def test_pyproject_declares_the_console_script(self):
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert 'sysadmin-check-claims = "sysadmin.ops_claims:main"' in pyproject


@pytest.mark.parametrize("key", sorted(CLAIM_PATTERNS))
def test_each_pattern_requires_the_emphasis(key):
    """The bold is load-bearing.

    It is what separates the figure this file has just measured from the
    history the same sentence carries — "**46 routes** … 44 before Session
    27".  A pattern without it reads both.
    """
    assert "\\*\\*" in CLAIM_PATTERNS[key]


class TestProseWraps:
    """A paragraph reflow must not retire a claim.

    Found by using it: the first rewrite of the block under this check put
    ``holds **2**`` and ``unresolved`` on two lines *with a blockquote
    marker between them*, and the claim came back unreadable — correct by
    rule 2 and useless, because ``unknown`` for a reason no reader would
    guess is how a check goes quiet.  Falsified by removing the
    :func:`flatten` call: the first assertion below is the shape that
    actually occurred, and it fails.
    """

    def test_a_claim_split_across_two_lines_is_still_read(self):
        wrapped = "> `alerts` holds **2**\n> unresolved rows in total."
        assert read_claim(wrapped, "alerts") == ("2", "")

    def test_the_same_holds_for_the_other_prose_claims(self):
        assert read_claim("> head\n> **013**", "migration_head") == ("013", "")
        assert read_claim("> restarted\n> at **2026-08-24 21:46:11**", "daemon_start")[0] == (
            "2026-08-24 21:46:11"
        )

    def test_the_captured_timestamp_never_contains_a_newline(self):
        """``\\s+`` inside the value would swallow the wrap into the claim.

        The comparison is against ``ActiveEnterTimestamp`` rendered as a
        wall clock, so a value with a newline in it can only ever
        mismatch — a false ``no`` where the document is fine.
        """
        stamp, _ = read_claim("restarted at **2026-08-24 21:46:11**", "daemon_start")
        assert stamp is not None and "\n" not in stamp


# ---------------------------------------------------------------------------
# SNAG-ESTATE-011 — the convention
# ---------------------------------------------------------------------------


class TestMarkers:
    """A marker names a check and never a value — rule 7.

    That distinction is the whole design.  ``<!-- routes=46 -->`` beside a
    sentence is a second statement of one fact that can agree with the box
    while the prose disagrees, and nothing notices; ``<!--check:routes-->``
    states no fact at all, so there is nothing for it to drift from.
    """

    def test_a_marker_wrapped_onto_its_own_quoted_line_is_still_read(self):
        """Falsified by matching against the region rather than :func:`flatten`.

        The same failure :class:`TestProseWraps` pins one level down: a
        paragraph reflow must not be able to retire a claim, and it would
        be perverse for the mechanism that makes claims explicit to be the
        one thing a reflow can switch off.
        """
        wrapped = "> `alerts` holds **2** unresolved rows\n> <!--check:alerts-->"
        assert [marker.key for marker in read_markers(wrapped)] == ["alerts"]

    def test_the_argument_is_carried_and_is_empty_for_a_plain_marker(self):
        markers = read_markers(
            "<!--check:expires 2026-08-25T03:32 the estate row--> <!--check:alerts-->"
        )
        assert [(m.key, m.argument) for m in markers] == [
            ("expires", "2026-08-25T03:32 the estate row"),
            ("alerts", ""),
        ]

    def test_the_known_names_are_derived_not_written_beside_the_patterns(self):
        """``max_priority_for`` against ``PRIORITY_MAP``'s rule.

        Falsified by hand-writing :data:`CHECK_KEYS`: adding a pattern
        without adding its name would then make the new figure
        unmarkable, and the report would tell a sitting to add a marker
        it goes on to reject.
        """
        assert CHECK_KEYS == frozenset(CLAIM_PATTERNS) | KEYLESS_CHECKS
        assert "routes" in CHECK_KEYS and "expires" in CHECK_KEYS


class TestAQuotedMarkerIsAQuotation:
    """``SNAG-DOCS-005`` — a marker between backticks states nothing.

    The convention's syntax is also something a document has to be able to
    *write about*, and the block that explains it is the block this module
    reads.  Before the fix the two were indistinguishable, and the failure
    was quiet in both directions: a quoted key nothing implements was
    reported as a broken marker, and a quoted key that *is* implemented
    silenced the ``unclaimed`` finding beside a sentence claiming nothing.
    The block paid for it in prose — *"One thing this block deliberately
    does not do: quote a marker"* — so the entry's empty population was an
    avoidance rather than a measurement.

    The founding case is the sibling's, not a hypothesis:
    :mod:`sysadmin.snag_claims` shipped the same shape without the guard
    and its first live run reported two checks nobody implements,
    ``helth`` and ``routes``, both "named by" an entry that only quotes
    them.
    """

    QUOTED = "> The `<!--check:helth-->` marker names a check and states no value."
    DOUBLED = "> Session 76 wrote that ``the `<!--check:helth-->` marker`` names a check."

    def test_a_quoted_marker_is_not_read_as_one(self):
        assert read_markers(self.QUOTED) == []

    def test_the_doubled_fence_is_where_the_naive_pattern_leaks(self):
        """The reason :data:`CODE_SPAN_RE` closes on a run of its own length.

        Markdown writes a span containing a span with a doubled fence, and
        ``snag_list.md`` carries exactly this sentence.  Falsified against
        ``` `[^`]+` ``` — which passes the test above and fails this one,
        closing at the *inner* backtick and leaving the marker bare.  Driven
        the same way one function over, where
        ``sysadmin-check-snags`` reports the naive pattern a narrowing of
        ``SNAG-DOCS-005`` rather than a closure.
        """
        assert read_markers(self.DOUBLED) == []
        naive = re.compile(r"`[^`]+`")
        assert MARKER_RE.search(naive.sub(" ", self.DOUBLED)) is not None

    def test_a_real_marker_beside_a_quoted_one_is_still_read(self):
        """The fix must remove the quotation and nothing else.

        A code span the marker does not sit inside is ordinary prose
        furniture — every claim in the real block wears one — so a pattern
        that ate to the next backtick would retire the live markers while
        closing the entry.
        """
        region = "> `alerts` holds **2** rows <!--check:alerts-->\n> unlike `<!--check:helth-->`"
        assert [marker.key for marker in read_markers(region)] == ["alerts"]

    def test_quoting_an_implemented_key_no_longer_silences_its_finding(self):
        """The second direction, and the control is what makes it evidence.

        A finding's absence says nothing until its presence has been
        observed, so the same region is read twice — once stating the
        figure with nothing quoted, once with the marker quoted beside it.
        """
        stated = "> The application serves **7 routes**."
        control = check_markers(stated, read_markers(stated))
        assert "unclaimed:routes" in {finding.key for finding in control}

        quoted = stated + " The `<!--check:routes-->` marker names a check."
        findings = {finding.key for finding in check_markers(quoted, read_markers(quoted))}
        assert "unclaimed:routes" in findings
        assert "marker:routes" not in findings

    def test_quoting_a_key_nobody_implements_invents_no_finding(self):
        region = "> Session 76's `<!--check:helth-->` fired from both sides."
        assert [finding.key for finding in check_markers(region, read_markers(region))] == []

    def test_the_sibling_s_copy_and_this_one_agree_shape_for_shape(self):
        """Import where you can, pin where you cannot.

        :func:`sysadmin.snag_claims.strip_code_spans` is a copy rather than
        an import — two composition roots must not couple to share a
        regex, and a snag-list parse must not move because the dashboard's
        reader was edited.  What replaces the import is this: the two are
        pinned on *behaviour*, over every shape this box's documents
        actually write, rather than on a pattern string.  It is the pin
        that outlives ``SNAG-DOCS-005``'s check, which was retired with
        the entry the day both sides were fixed.

        Falsified by pointing :data:`CODE_SPAN_RE` at ``` `[^`]+` ```,
        which parts company from the sibling on the doubled fence — the
        divergence that would otherwise let one module close the entry
        while the other still leaks.
        """
        shapes = (
            self.QUOTED,
            self.DOUBLED,
            "``a fence holding a `span` inside it``",
            "a `span`, a `second span` and prose between them",
            "an unpaired ` backtick and a <!--check:alerts--> after it",
            "a span across\na line break: `one\ntwo`",
            "no span at all",
        )
        for shape in shapes:
            assert CODE_SPAN_RE.sub(" ", shape) == strip_code_spans(shape), shape
        assert any(CODE_SPAN_RE.sub(" ", shape) != shape for shape in shapes)


class TestTheConventionsTwoFailures:
    BLOCK = (
        "> `alerts` holds **2** unresolved rows <!--check:alerts-->\n"
        "> and **46 routes** exist.\n"
    )

    def test_a_marker_naming_a_check_nobody_implements_is_reported(self):
        """Falsified by ignoring an unknown name.

        A typo, a rename or a deleted check all end the same way: the
        sentence looks verified and is not, which is worse than prose —
        prose never claimed to have been checked.
        """
        findings = check_markers(self.BLOCK, [Marker("helth", "", "")])
        assert [claim.key for claim in findings][0] == "marker:helth"
        assert findings[0].verdict == "unknown"
        assert "nothing implements 'helth'" in findings[0].note

    def test_a_figure_no_line_claims_is_reported(self):
        """The enforcement point SNAG-ESTATE-008 asked for and could not have."""
        findings = check_markers(self.BLOCK, read_markers(self.BLOCK))
        keys = [claim.key for claim in findings]
        assert "unclaimed:routes" in keys
        assert "unclaimed:alerts" not in keys, "the marker on that line claims it"

    def test_a_figure_the_block_does_not_state_is_not_reported_as_unclaimed(self):
        """Absence of a claim is not an unclaimed claim.

        Falsified by iterating :data:`CLAIM_PATTERNS` without testing the
        prose: every block would then owe a marker for every check,
        including ones about sentences it does not contain.
        """
        findings = check_markers(self.BLOCK, read_markers(self.BLOCK))
        assert "unclaimed:daemon_start" not in [claim.key for claim in findings]

    def test_the_marker_is_additive_and_cannot_switch_a_check_off(self):
        """Rule 7's second half, and the one that keeps rule 2 true.

        ``**46 routes**`` carries no marker in :attr:`BLOCK`, and the
        routes claim is still compared — so deleting a marker can never
        be a way to retire a check, only a way to be told about it.
        """
        claims = {claim.key: claim for claim in check_all(Path("/nonexistent"))}
        assert "routes" in claims
        assert claims["routes"].kind == "claim"

    def test_convention_findings_carry_no_sides_to_compare(self):
        """Rule 3's third kind: the remedy is a marker, not a reword or a restart."""
        finding = check_markers(self.BLOCK, [Marker("nope", "", "")])[0]
        assert finding.kind == "convention"
        assert finding.documented is None and finding.measured is None


class TestExpiry:
    """A prediction is timed, not measured — rules 8 and 9.

    The instance that opened SNAG-ESTATE-011: "the row clears at 03:32
    with nothing done", written at 00:30 and true of nothing yet.  Every
    fixture here carries an offset since SNAG-ESTATE-013: the marker that
    opened *that* entry did not, and named an instant an hour before the
    thing it predicted.
    """

    #: The prose is a local wall clock, so the block and the marker agree
    #: only when the marker's offset is this box's.  ``+01:00`` rather
    #: than a rendered ``datetime.now()``: a fixture whose zone follows
    #: the process cannot demonstrate the disagreement these tests are
    #: about, and a naive fixture is what the module now refuses.
    BLOCK = (
        "> the estate row clears at 03:32 with nothing done "
        "<!--check:expires 2026-08-25T03:32+01:00 estate scan row-->"
    )
    #: Read out of the block rather than hand-built.  Since
    #: ``SNAG-DOCS-008`` a marker carries the sentence it stands in, and
    #: a hand-built marker paired with a separate block is exactly the
    #: region/marker mismatch that field exists to make unrepresentable —
    #: these tests used to do it four times.
    MARKER = read_markers(BLOCK)[0]
    BST = timezone(timedelta(hours=1))

    def _marker(self, argument: str) -> Marker:
        """A marker standing in the block's sentence, carrying ``argument``.

        The convention findings — no instant, unparseable instant — return
        before the pin, so the sentence cannot reach them.  It is the
        block's own anyway, so that a test which later *did* come to
        depend on it would be depending on something real rather than on
        an empty string chosen because nothing read it.
        """
        return Marker("expires", argument, self.MARKER.sentence)

    def _at(self, hour: int, minute: int) -> datetime:
        """A clock in the marker's own zone, so the arithmetic is readable."""
        return datetime(2026, 8, 25, hour, minute, tzinfo=self.BST)

    def test_before_its_moment_the_prediction_stands(self):
        claim = check_expiry(self.MARKER, self._at(0, 30))
        assert claim.verdict == "match"
        assert "to run" in (claim.measured or "")
        assert claim.subject.endswith("estate scan row")

    def test_after_its_moment_it_is_unknown_rather_than_false(self):
        """Falsified by returning ``mismatch``.

        A passed boundary does not make the sentence wrong — the
        prediction may well have come true.  What nobody did is look, and
        rule 2 reserves ``unknown`` for exactly that.
        """
        claim = check_expiry(self.MARKER, self._at(6, 32))
        assert claim.verdict == "unknown"
        assert "nobody re-measured it" in claim.note

    def test_the_instant_is_pinned_to_the_prose_rather_than_trusted(self):
        """Rule 9.  Falsified by skipping the pin.

        The instant is the single fact this document states twice — the
        marker needs a date the prose has no room for — so it is handled
        the way ``syslog_priority`` is handled against ``PRIORITY_MAP``:
        pinned by a check, not asserted on each side.
        """
        drifted = (
            "> the estate row clears at 04:15 with nothing done "
            "<!--check:expires 2026-08-25T03:32+01:00 estate scan row-->"
        )
        claim = check_expiry(read_markers(drifted)[0], self._at(0, 30))
        assert claim.verdict == "unknown"
        assert "03:32" in claim.note and "does not" in claim.note

    def test_the_pin_does_not_read_the_markers_own_copy_of_the_instant(self):
        """Found by running it, not by a fixture — and the fixture was green.

        The first implementation searched the flattened region, which
        contains the marker, so ``03:32`` matched the marker's own text
        and the pin passed whatever the sentence said.  A pin that
        searches text containing the thing it is pinning is the check
        agreeing with itself by construction.  Falsified by dropping the
        ``MARKER_RE.sub`` in :func:`_sentence_at`, which is where that
        stripping moved when the pin narrowed (``SNAG-DOCS-008``); the
        test above shares this fixture now and is falsified by skipping
        the pin instead, so the two remain two mutations rather than one.
        """
        only_in_the_marker = (
            "> the estate row clears at 04:15 with nothing done "
            "<!--check:expires 2026-08-25T03:32+01:00 estate scan row-->"
        )
        claim = check_expiry(read_markers(only_in_the_marker)[0], self._at(0, 30))
        assert claim.verdict == "unknown"
        assert "the sentence it stands in does not" in claim.note

    def test_a_marker_with_no_instant_is_a_convention_finding(self):
        claim = check_expiry(self._marker(""), self._at(0, 30))
        assert claim.kind == "convention"
        assert "carries no instant" in claim.note

    def test_the_example_it_offers_is_one_the_module_would_accept(self):
        """The remedy in a convention finding must not be a third format.

        A message suggesting a shape ``EXPIRY_FORMAT`` rejects is a
        remedy that fails when followed, which is worse than none — the
        author has then written the marker twice and been refused twice.
        Falsified by rendering the example with ``EXPIRY_NAIVE_FORMAT``.
        """
        claim = check_expiry(self._marker(""), self._at(0, 30))
        offered = re.search(r"<!--check:expires (\S+)", claim.note)
        assert offered, claim.note
        assert datetime.strptime(offered.group(1), EXPIRY_FORMAT).tzinfo is not None

    def test_an_unparseable_instant_names_the_form_it_wanted(self):
        claim = check_expiry(self._marker("tomorrow-ish"), self._at(0, 30))
        assert claim.kind == "convention"
        assert "tomorrow-ish" in claim.note

    def test_two_predictions_are_two_claims(self):
        """The family's members are declared by the document, not by this module."""
        block = (
            "> one clears at 03:32 <!--check:expires 2026-08-25T03:32+01:00 estate row-->\n"
            "> another leaves the window at 14:11 "
            "<!--check:expires 2026-08-25T14:11+01:00 log rows-->"
        )
        markers = [m for m in read_markers(block) if m.key == "expires"]
        claims = [check_expiry(m, self._at(0, 30)) for m in markers]
        assert [claim.key for claim in claims] == [
            "expires:2026-08-25T03:32+01:00",
            "expires:2026-08-25T14:11+01:00",
        ]
        assert all(claim.verdict == "match" for claim in claims)


class TestThePinIsNarrowedToOneSentence:
    """SNAG-DOCS-008 — rule 9's pin reads the marker's sentence, not the block.

    Rule 9 always said searching the whole printed region was "the weaker
    half", and rule 10 declined to narrow it on the grounds that the two
    narrowings *"fail in different directions — a pin that cannot find its
    instant is ``unknown`` and loud, where a membership test that finds a
    title anywhere is ``match`` and silent"*.  That is true of one of the
    pin's two directions.  A pin that finds its instant in an **unrelated**
    sentence is ``match`` and silent, which is rule 10's own defect with a
    five-character needle drawn from 1440 values.

    Measured on 2026-09-04 rather than supposed: the printed region states
    **86** distinct wall clocks, **28** of them more than once, and it grew
    from 38.5 kB to 188 kB in the preceding eight days — the same
    append-only curve rule 10 closed on.
    """

    #: The founding SNAG-ESTATE-013 fault: a UTC-stamped instant copied off
    #: an estate surface into a sentence written in BST.  05:45 is the disk
    #: review slot on this box, so ``04:45+00:00`` is exactly what such a
    #: surface publishes for it — which is why the local rendering collides
    #: with eleven unrelated mentions of the schedule.
    COPIED = "2026-09-05T04:45+00:00"

    def _claim(
        self, block: str, now: datetime | None = None, argument: str | None = None
    ) -> Claim:
        """The claim for one prediction, selected by what it is about.

        **Selected rather than taken first, since 2026-09-04.**  This read
        ``next(m for m in read_markers(block) if m.key == "expires")``, and
        "the first prediction in the block" was "the one this test planted"
        only because the real document carried none — the family shipped
        untriggered on 2026-08-24 and gained its first live member the day
        this was repaired.  So the live drive below silently began measuring
        *that* marker instead of its own, which is a guard broken by the
        document doing the thing the guard exists to encourage:
        ``SNAG-LOG-004``'s ordering, a fix that widens what a reader can see
        being a regression surface for whatever reads it.

        The count is asserted rather than the first match taken, because an
        ambiguous selector is the defect being removed and picking one of
        two is how it stayed quiet.
        """
        markers = [m for m in read_markers(block) if m.key == "expires"]
        if argument is not None:
            markers = [m for m in markers if m.argument.endswith(argument)]
        assert len(markers) == 1, (
            f"{len(markers)} expires marker(s) match {argument!r} — the selector "
            "no longer names one prediction"
        )
        return check_expiry(markers[0], now or datetime(2026, 9, 1, tzinfo=UTC))

    def test_a_clock_in_another_sentence_does_not_pin_the_marker(self):
        """Falsified by pinning against the whole region: the claim passes.

        The two sentences are the smallest specimen of the shape rule 9
        admitted and rule 10 left standing — the block states the clock,
        for a different reason, somewhere the marker is not.
        """
        block = (
            "> **The estate row clears at 03:32, which is the boundary.** "
            "Nothing further is owed."
            "<!--check:expires 2026-09-05T03:32+01:00 the estate row-->"
        )
        claim = self._claim(block)
        assert claim.verdict == "unknown"
        assert "the sentence it stands in does not" in claim.note
        assert "SNAG-DOCS-008" in claim.note

    def test_the_same_clock_in_the_markers_own_sentence_still_pins(self):
        """The narrowing must not cost the correct case.

        Falsified by returning ``None`` from :func:`_sentence_at`: this
        goes ``unknown`` and the endpoint reports every prediction unpinned.
        """
        block = (
            "> **The estate row clears at 03:32 with nothing done.**"
            "<!--check:expires 2026-09-05T03:32+01:00 the estate row-->"
        )
        assert self._claim(block).verdict == "match"

    def test_the_live_region_no_longer_swallows_the_zone_fault(self):
        """The drive that settled the entry, against the real document.

        Wide, this returns ``match``: the marker renders 05:45 locally and
        the block says 05:45 eleven times for reasons that have nothing to
        do with the prediction, so ``SNAG-ESTATE-013``'s founding fault is
        reported as a healthy claim.  Narrow, the sentence says 04:45 and
        the check reaches that entry's own diagnostic.

        Falsified by pinning against the whole region.  Driven at the real
        188 kB block rather than a fixture, because the fixture cannot
        *have* the property under test — an unrelated sentence naming the
        clock is what accumulates, and no fixture accumulates.
        """
        region, problem = load_region()
        assert region, problem
        planted = region + (
            "\n> **The disk review row clears at 04:45 with nothing done.**"
            f"<!--check:expires {self.COPIED} the disk review row-->\n"
        )
        assert "05:45" in region, "the collision this test turns on has aged out"
        claim = self._claim(planted, argument="the disk review row")
        assert claim.verdict == "unknown"
        assert "different clocks" in claim.note

    def test_two_predictions_are_each_pinned_to_their_own_sentence(self):
        """The family ``claim_sentence`` cannot serve — the reason for the field.

        ``expires`` is the one check whose members the *document* declares,
        so two predictions are two markers with one key, which is the shape
        :func:`claim_sentence` refuses outright.  Falsified by routing the
        pin through it: both claims become ``unknown`` naming the refusal
        rather than the clock.
        """
        block = (
            "> **One clears at 03:32.**"
            "<!--check:expires 2026-09-05T03:32+01:00 the estate row--> "
            "**Another leaves the window at 14:11.**"
            "<!--check:expires 2026-09-05T14:11+01:00 the log rows-->"
        )
        markers = [m for m in read_markers(block) if m.key == "expires"]
        claims = [check_expiry(m, datetime(2026, 9, 1, tzinfo=UTC)) for m in markers]
        assert [c.verdict for c in claims] == ["match", "match"]
        assert "03:32" in markers[0].sentence and "14:11" not in markers[0].sentence
        assert "14:11" in markers[1].sentence and "03:32" not in markers[1].sentence

    def test_the_key_lookup_still_refuses_a_key_stated_twice(self):
        """The refusal that is *right* for every other check, kept intact.

        Narrowing rule 9 must not reach :func:`claim_sentence` and soften
        it: a membership claim named twice has two candidate sentences and
        taking the first reports agreement with whichever was written
        first.  Falsified by resolving the ambiguity there instead of here.
        """
        block = (
            "> **One clears at 03:32.**"
            "<!--check:expires 2026-09-05T03:32+01:00 a--> "
            "**Another at 14:11.**<!--check:expires 2026-09-05T14:11+01:00 b-->"
        )
        sentence, problem = claim_sentence(block, "expires")
        assert sentence is None
        assert "names the check twice" in problem

    def test_the_two_narrowings_share_one_locator(self):
        """Two implementations of "where does this sentence begin" is drift.

        :func:`claim_sentence` is now a key lookup over :func:`read_markers`,
        so the sentence a membership claim is read from and the sentence a
        prediction is pinned against are the same string by construction.
        Falsified by giving either its own scan.
        """
        region, problem = load_region()
        assert region, problem
        looked_up, why = claim_sentence(region, "open_titles")
        assert looked_up, why
        carried = next(m for m in read_markers(region) if m.key == "open_titles")
        assert carried.sentence == looked_up
        assert len(looked_up) < len(flatten(region)) / 100


    def test_a_marker_written_flush_against_the_full_stop_closes_its_sentence(self):
        """Two silent widenings, found by writing the fixture the note asks for.

        The new note tells an author to move the marker into the sentence
        naming the clock, and the obvious way to do that is to write it
        straight after the full stop.  :data:`SENTENCE_END_RE` wants
        whitespace or the end of the region after a terminator and a
        marker is neither, so the terminator went unseen and the sentence
        ran *backwards* through the preceding paragraph — the pin getting
        wider, arriving through the fix for the pin being too wide.
        :func:`_unmarked` is that half.

        Blanking the marker then moved the anchor past the terminator, so
        the sentence became the **next** one, which here is empty and pins
        nothing.  :func:`_anchor` is that half: a marker belongs to the
        sentence it closes.  Falsified by dropping either.
        """
        block = (
            "> **The row was already gone.** "
            "**The estate row clears at 03:32 with nothing done.**"
            "<!--check:expires 2026-09-05T03:32+01:00 the estate row-->"
        )
        marker = read_markers(block)[0]
        assert marker.sentence.startswith("**The estate row clears")
        assert "already gone" not in marker.sentence
        assert self._claim(block).verdict == "match"

    def test_the_anchor_skips_a_marker_that_precedes_it(self):
        """Whitespace is skipped on the unmarked string, not the prose.

        Two markers closing one sentence is the live document's own shape
        — ``deploy`` and ``daemon_start`` sit side by side — so the second
        must anchor past the first rather than landing inside a blank.
        Falsified by taking the probe on ``prose`` instead of ``unmarked``.
        """
        block = (
            "> **The estate row clears at 03:32 with nothing done.**"
            "<!--check:alerts--> <!--check:expires 2026-09-05T03:32+01:00 row-->"
        )
        assert {m.sentence for m in read_markers(block)} == {
            "**The estate row clears at 03:32 with nothing done.**"
        }
        assert self._claim(block).verdict == "match"


class TestTheLiveBlockCarriesAPrediction:
    """Rules 8 and 9, driven at the marker the document actually carries.

    Every other guarantee in this file is driven at a **planted** marker.
    The family shipped on 2026-08-24 and had no live member until
    2026-09-04, so the whole of it — the pin, the offset refusal, the
    timing — was pinned against blocks these tests wrote themselves,
    which is the strongest evidence available and is not the same as an
    observation.  ``SNAG-ESTATE-002``'s position exactly, one module
    over.

    **The verdict is deliberately not asserted against the wall clock.**
    A test reading ``match`` off ``datetime.now()`` turns red the morning
    the boundary passes, which is a red suite with nothing wrong — the
    calendar writing a verdict, which is the reading this repository has
    refused four times in ``snag_claims``.  So ``now`` is taken from the
    marker's **own** instant and moved a minute either side: what is
    guaranteed is that the shipped marker is well-formed and pins its
    clock in its own sentence, at any date, and the verdict a human reads
    stays the checker's to report at both ends of a sitting.
    """

    MINUTE = timedelta(minutes=1)

    def _markers(self) -> list[Marker]:
        region = printed_region(STATUS_PATH.read_text())
        assert region is not None, "the Quick Status heading moved"
        return [m for m in read_markers(region) if m.key == "expires"]

    def test_the_block_states_at_least_one_prediction(self):
        """The anti-vacuity premise, and it is the whole point of the class.

        Without it every assertion below is satisfied by a document
        carrying no prediction at all, and the class reports health over
        the untriggered family it exists to end.
        """
        assert self._markers(), (
            "docs/roadmap/STATUS.md carries no <!--check:expires ...--> marker — "
            "the family is untriggered again and every guarantee here is vacuous"
        )

    def test_every_prediction_carries_an_offset(self):
        """Falsified by writing the instant naive: the claim is a convention finding.

        ``SNAG-ESTATE-013``'s founding fault is a stamp copied off a
        UTC-publishing surface with the offset dropped on the way in, and
        it is invisible in the verdict — a naive marker is *recognised*,
        so what it produces is a ``convention`` claim rather than a
        parse error.
        """
        for marker in self._markers():
            instant = marker.argument.split(None, 1)[0]
            moment = datetime.strptime(instant, EXPIRY_FORMAT)
            assert moment.tzinfo is not None
            assert check_expiry(marker, moment - self.MINUTE).kind == "claim"

    def test_every_prediction_pins_its_clock_in_its_own_sentence(self):
        """Rule 9 at the real document — falsified by moving the marker.

        Driven a minute *before* each marker's own moment, so a passing
        boundary can never redden it: at that clock a pinned prediction
        is ``match`` and an unpinned one is ``unknown`` carrying the
        remedy.  The two are distinguishable by verdict alone, which is
        why nothing here reads the note.
        """
        for marker in self._markers():
            moment = datetime.strptime(marker.argument.split(None, 1)[0], EXPIRY_FORMAT)
            claim = check_expiry(marker, moment - self.MINUTE)
            assert claim.verdict == "match", claim.note
            assert "to run" in (claim.measured or "")

    def test_each_prediction_goes_unknown_once_its_moment_passes(self):
        """The timing half, at the shipped marker rather than a planted one.

        This is what the block buys: after the boundary the claim stops
        agreeing, so *nobody went back* is loud at the next preflight
        instead of being indistinguishable from a prediction that came
        true.
        """
        for marker in self._markers():
            moment = datetime.strptime(marker.argument.split(None, 1)[0], EXPIRY_FORMAT)
            claim = check_expiry(marker, moment + self.MINUTE)
            assert claim.verdict == "unknown"
            assert "nobody re-measured it" in (claim.note or "")


class TestTheInstantCarriesItsZone:
    """SNAG-ESTATE-013 — a zoneless instant is refused, not read as local.

    The entry's specimen is a *copy*: the estate publishes
    ``started_at: "2026-08-25T03:32:17.538288+00:00"``, a human took the
    wall clock out of it, and the marker then named 03:32 **BST** — an
    hour before the thing it predicted, and four hours *after* it west of
    Greenwich.  The magnitude is the reader's offset and the sign is the
    reader's hemisphere; what neither of them changes is that the marker
    had no zone for the check to disagree with.

    These tests are the durable half of ``check_expiry_naive_instant``,
    which retired with the entry it measured.  The registry rule is that
    a check names an open entry; the *detector* outlives it as a test,
    which is what Session 112 did with ``TestNoTriggerDiscardsItsTask``.
    """

    #: The stamp the entry quotes, verbatim.  Both forms below are
    #: rendered from this one value, so the naive marker and the aware
    #: one cannot come to name two different instants the way two typed
    #: literals would — the retired check's rule, kept.
    PRODUCER = "2026-08-25T03:32:17.538288+00:00"

    def _drive(self, instant: str, now: datetime, clocks=("03:32", "04:32")) -> Claim:
        """The real reader and the real timer, given a marker text.

        ``read_markers`` rather than a hand-built :class:`Marker`: the
        argument is the part of the convention this is about, and
        ``MARKER_RE``'s group stops at ``>``, so that ``+00:00`` survives
        it is a fact about the reader worth driving rather than assuming.

        **The prose names every clock the instant could render as**, so
        rule 9's pin is satisfied in advance and what is measured here is
        the parse.  Otherwise a correctly-parsed instant comes back
        ``unknown`` for the pin's reason and these tests report the wrong
        limb moved — which is what the first draft did at
        ``America/New_York``, where 03:32 UTC is the previous evening.
        """
        stated = ", ".join(clocks)
        region = (
            f"> the estate row clears at {stated} with nothing done "
            f"<!--check:expires {instant} estate scan row-->"
        )
        marker = next(m for m in read_markers(region) if m.key == "expires")
        return check_expiry(marker, now)

    def test_the_producer_stamp_is_the_entrys_own(self):
        """The specimen is quoted, never invented — the defect is a copy."""
        snags = (REPO_ROOT / "docs/roadmap/snag_list.md").read_text(encoding="utf-8")
        assert self.PRODUCER in snags

    def test_a_zoneless_instant_is_refused_and_names_both_readings(self):
        """Falsified by keeping ``EXPIRY_FORMAT`` naive: the drive parses.

        ``convention`` rather than a timed claim is the whole of it —
        ``Claim.measured`` is what separates a mis-timed prediction from
        a rejected marker, because both print ``??``.
        """
        producer = datetime.fromisoformat(self.PRODUCER)
        claim = self._drive(producer.strftime(EXPIRY_NAIVE_FORMAT), producer)
        assert claim.kind == "convention" and claim.measured is None
        assert "carries no offset" in claim.note

    def test_the_producers_own_form_parses(self):
        """The half that makes the refusal usable rather than a wall.

        An author copying the estate's ``started_at`` and cutting it at
        the minute writes exactly this, so a fix that refused the naive
        form and did not accept the offset-bearing one would leave the
        family with no writable shape at all.
        """
        producer = datetime.fromisoformat(self.PRODUCER)
        claim = self._drive(producer.isoformat(timespec="minutes"), producer)
        assert claim.kind == "claim" and claim.measured is not None

    def test_utc_may_be_written_as_z(self):
        """``Z`` is what a JSON surface is as likely to publish as ``+00:00``."""
        claim = self._drive("2026-08-25T03:32Z", datetime.fromisoformat(self.PRODUCER))
        assert claim.kind == "claim" and claim.measured is not None

    def test_an_epoch_is_refused_though_since_timestamp_renders_one(self):
        """The deliberate departure from ``journal.since_timestamp``.

        Both refuse the same ambiguity; only one of them has a human
        reader who must pin the instant against the sentence beside it
        (rule 9).  An epoch is unambiguous and unreadable, so it is
        refused *here* and correct *there* — a difference of reader, not
        of instant.  Falsified by teaching the parse ``@<epoch>``.
        """
        moment = datetime.fromisoformat(self.PRODUCER)
        claim = self._drive(f"@{int(moment.timestamp())}", moment)
        assert claim.kind == "convention" and claim.measured is None

    def test_a_sentence_in_the_markers_zone_rather_than_the_boxs_is_named_as_such(self):
        """Rule 9 doing more than spelling — the entry's own block, exactly.

        "the estate's stored scan of 03:32 today" beside
        ``<!--check:expires 2026-08-25T03:32…-->`` is the copy that opened
        the entry: both halves say 03:32 and both are an hour from the
        moment predicted.  Naive, the two agree and the pin passes.  With
        an offset they visibly disagree, and the note says which of them
        is in which clock rather than reporting a drifted figure.

        Falsified by pinning against ``moment.strftime`` instead of
        ``moment.astimezone().strftime``: the marker's own rendering is
        then what is looked for, it is in the prose, and the pin passes
        exactly as it did before the fix.
        """
        with _zone("Europe/London"):
            producer = datetime.fromisoformat(self.PRODUCER)
            claim = self._drive(
                producer.isoformat(timespec="minutes"), producer, clocks=("03:32",)
            )
        assert claim.verdict == "unknown"
        assert "different clocks" in claim.note
        assert "04:32" in claim.note and "03:32" in claim.note

    @pytest.mark.parametrize(
        ("zone", "displaced"),
        [("Europe/London", True), ("America/New_York", True), ("UTC", False)],
    )
    def test_the_boundary_sits_where_the_producer_stamped_it_in_every_zone(
        self, zone, displaced
    ):
        """The entry's symptom is a displacement whose *sign* the zone picks.

        Written first as "does it expire early", which is the entry's own
        wording and holds only east of Greenwich: at ``America/New_York``
        the same naive marker named an instant four hours **after** its
        subject, so the prediction outlived what it predicted and an
        early-expiry test reported the module correct.  ``SNAG-LOG-009``'s
        *"N hours late at UTC−N"* one document over.

        So what is asserted is that the boundary now sits at the
        producer's instant in **all three** zones, including the one where
        the old reading was accidentally right.  ``displaced`` records
        which zones could have demonstrated the fault at all: at UTC the
        two readings name one moment, so this is a control rather than a
        witness and says so rather than looking like evidence.
        """
        with _zone(zone):
            producer = datetime.fromisoformat(self.PRODUCER)
            naive = producer.astimezone().strftime(EXPIRY_NAIVE_FORMAT)
            offset = producer.astimezone().utcoffset() or timedelta(0)
            assert bool(offset) is displaced, "the zone database moved under this test"

            minute = timedelta(minutes=1)
            aware = producer.isoformat(timespec="minutes")
            local = (producer.astimezone().strftime("%H:%M"),)
            before = self._drive(aware, producer - minute, clocks=local)
            after = self._drive(aware, producer + minute, clocks=local)
            assert before.verdict == "match" and after.verdict == "unknown"
            assert after.measured and "passed" in after.measured

            # And the reading that produced the displacement no longer parses,
            # in the zone where it was wrong and in the zone where it was not.
            assert self._drive(naive, producer, clocks=local).kind == "convention"


class TestTheClockItIsJudgedAgainst:
    """``now`` must be aware — SNAG-ESTATE-013, the guard's other half.

    ``since_timestamp``'s posture, arriving at a function that takes two
    instants rather than one.  The subtraction below would raise on its
    own, which is why this is a *relocation* of a failure rather than a
    new one; what it buys is that the failure lands on the caller that
    passed the naive clock instead of on the day somebody writes the
    first well-formed marker.
    """

    def test_a_naive_clock_is_refused_before_any_marker_is_read(self):
        """Falsified by dropping the guard: the empty marker returns a finding.

        Driven at a marker carrying **no instant at all**, deliberately.
        That path never reaches the subtraction, so it is the one drive
        that would sail past a guard placed at the arithmetic — which is
        the entire argument for putting it at the entry point.
        """
        with pytest.raises(TypeError, match="aware clock"):
            check_expiry(Marker("expires", "", ""), datetime(2026, 8, 25, 0, 30))

    def test_check_all_judges_predictions_against_an_aware_clock(self, tmp_path):
        """The default is aware, so the module's own caller is not the bug.

        Falsified by restoring ``datetime.now()``: every ``expires``
        claim in a real document becomes a ``TypeError``.
        """
        seen: list[datetime] = []

        def _spy(marker, now):
            seen.append(now)
            return Claim("expires:x", "s", "claim", None, None, "match", "")

        document = (
            "# Project Status Dashboard\n\n"
            "> a prediction <!--check:expires 2026-08-25T03:32+01:00 something-->\n\n"
            "## Quick Status\n"
        )
        status = tmp_path / "STATUS.md"
        status.write_text(document, encoding="utf-8")
        with patch("sysadmin.ops_claims.check_expiry", _spy):
            check_all(status)
        assert seen and all(moment.tzinfo is not None for moment in seen)


class TestOpenTitlesAreNamed:
    """The count cannot see a swap; this can.

    One row resolving as another opens holds the total still while the
    block's sentence about *which* rows are open goes silently wrong.

    ``BLOCK`` carries the marker because the real document does, and has
    since ``SNAG-ESTATE-011``.  The fixture went without one for as long
    as the check read the whole region, which is the shape recorded
    against ``UnitFinding.enabled``'s stand-ins: a fixture that omits a
    field the production artefact always carries is not a smaller
    document, it is a different one.
    """

    BLOCK = "> `Estate scan could not reach sources` is expected <!--check:open_titles-->."

    def test_a_row_the_block_never_mentions_is_named(self):
        facts = DatabaseFacts(
            11, 2, ("warning: Estate scan could not reach sources", "critical: Disk full on /")
        )
        claim = check_open_titles(self.BLOCK, "", facts)
        assert claim.verdict == "mismatch"
        assert claim.detail == ("unnamed: critical: Disk full on /",)

    def test_every_row_named_is_a_match(self):
        facts = DatabaseFacts(11, 1, ("warning: Estate scan could not reach sources",))
        assert check_open_titles(self.BLOCK, "", facts).verdict == "match"

    def test_the_severity_prefix_is_dropped_before_the_substring_test(self):
        """Falsified by matching the rendered ``severity: title`` string.

        The block quotes the title alone; requiring the severity beside it
        would make every row unnamed and the check permanently loud, which
        is how a check gets ignored.
        """
        facts = DatabaseFacts(11, 1, ("warning: Estate scan could not reach sources",))
        assert check_open_titles(self.BLOCK, "", facts).verdict == "match"

    def test_an_unreadable_database_is_unknown_not_a_clean_block(self):
        facts = DatabaseFacts(None, None, (), "the database did not answer (OperationalError)")
        claim = check_open_titles(self.BLOCK, "", facts)
        assert claim.verdict == "unknown"


class TestTheHaystackIsOneSentence:
    """``SNAG-ESTATE-016`` — rule 10.

    The substring test was right and the region it ran over is
    append-only, so a title written down once was named for ever.  These
    pin the narrowing itself; :class:`TestTheBlockThatOpenedTheEntry`
    drives it at the real document that produced the finding.
    """

    #: The entry's shape at fixture size: the marked sentence names one
    #: row, and a past sitting's account below it names the other.  Every
    #: test here is falsified by matching against ``flatten(BLOCK)``, which
    #: is what the check did before.
    BLOCK = (
        "> `alerts` holds **2** unresolved rows, `Estate scan could not reach\n"
        "> sources` and `Project Alfred next action idle`, **2** named here\n"
        "> <!--check:open_titles-->.\n"
        "> *(1 until 09:00 — `High VRAM usage on AMD Radeon RX 7900 XTX`\n"
        "> resolved, which is `check_alerts`' fall note doing its job.)*\n"
        "> Previously: the sitting spent itself on\n"
        "> `High VRAM usage on AMD Radeon RX 7900 XTX`, four sittings ago.\n"
    )

    def test_a_title_only_a_past_sitting_wrote_down_does_not_count(self):
        """The founding case, at fixture size.

        Falsified against the pre-fix rule: the title is in the region
        twice, so the whole-region test answers ``match`` and this
        answers ``mismatch``.
        """
        open_now = (
            "warning: Estate scan could not reach sources",
            "warning: Project Alfred next action idle",
            "warning: High VRAM usage on AMD Radeon RX 7900 XTX",
        )
        claim = check_open_titles(self.BLOCK, "", DatabaseFacts(11, 3, open_now))
        assert claim.verdict == "mismatch"
        assert claim.detail == ("unnamed: warning: High VRAM usage on AMD Radeon RX 7900 XTX",)
        assert "past sitting" in claim.note
        # The pre-fix reading, spelled out rather than described.
        assert "High VRAM usage on AMD Radeon RX 7900 XTX" in flatten(self.BLOCK)

    def test_the_rows_the_sentence_names_still_match(self):
        """The narrowing discriminates; it did not merely get stricter.

        Same block, same 178 kB-shaped history, a different population —
        and the verdict moves with the population rather than with the
        change.
        """
        open_now = (
            "warning: Estate scan could not reach sources",
            "warning: Project Alfred next action idle",
        )
        assert check_open_titles(self.BLOCK, "", DatabaseFacts(11, 2, open_now)).verdict == "match"

    def test_a_resolved_title_the_fall_note_names_is_not_an_offence(self):
        """The direction the docstring reserves stays reserved.

        ``check_alerts``' fall note legitimately names a row that has
        since resolved, and the parenthetical carrying it sits outside the
        marked sentence — so it neither satisfies this check nor breaks
        it.  Falsified by asserting on the sentence rather than the
        verdict: a rule that refused an unmatched *name* would fire here.
        """
        open_now = ("warning: Estate scan could not reach sources",
                    "warning: Project Alfred next action idle")
        sentence, _ = claim_sentence(self.BLOCK, "open_titles")
        assert "resolved, which is" not in sentence
        assert check_open_titles(self.BLOCK, "", DatabaseFacts(11, 2, open_now)).verdict == "match"


class TestTheMarkerDecidesWhereNotWhether:
    """Rule 10's half of rule 7 — the marker may never yield ``match``.

    A marker is additive and cannot gate a check.  Here it decides the
    haystack, so its absence is a genuine not-knowing; what rule 2 buys is
    that not-knowing is a third verdict, so ``delete the marker`` cannot
    be used to make a failing check pass.
    """

    UNMARKED = "> `alerts` holds **1** unresolved row, `Disk full on /`, **1** named here."

    def test_no_marker_is_unknown_and_names_the_remedy(self):
        claim = check_open_titles(
            self.UNMARKED, "", DatabaseFacts(11, 1, ("critical: Disk full on /",))
        )
        assert claim.verdict == "unknown"
        assert "<!--check:open_titles-->" in claim.note

    def test_deleting_the_marker_cannot_turn_a_mismatch_into_a_match(self):
        """The property, driven at both spellings of one block.

        Falsified by falling back to the whole region when no marker is
        found — which is the pre-fix behaviour and would answer ``match``
        here, since the row is named further down.
        """
        marked = (
            "> `alerts` holds **1** unresolved row, `Disk full on /`, **1** named\n"
            "> here <!--check:open_titles-->.\n"
            "> Previously: `Estate scan could not reach sources` was open too.\n"
        )
        unmarked = marked.replace(" <!--check:open_titles-->", "")
        facts = DatabaseFacts(
            11, 2,
            ("critical: Disk full on /", "warning: Estate scan could not reach sources"),
        )
        assert check_open_titles(marked, "", facts).verdict == "mismatch"
        assert check_open_titles(unmarked, "", facts).verdict == "unknown"

    def test_two_markers_are_refused_rather_than_resolved(self):
        """``read_claim``'s rule for a span instead of a value.

        The live document carries the shape today — ``migration_head`` is
        marked in two places — so this is not a hypothetical.  Falsified
        by taking the first hit, which answers ``match`` here.
        """
        block = (
            "> `alerts` holds **1** unresolved row, `Disk full on /`, **1** named\n"
            "> here <!--check:open_titles-->.\n"
            "> Later: `Estate scan could not reach sources` <!--check:open_titles-->.\n"
        )
        sentence, problem = claim_sentence(block, "open_titles")
        assert sentence is None
        assert "twice" in problem
        claim = check_open_titles(block, "", DatabaseFacts(11, 1, ("critical: Disk full on /",)))
        assert claim.verdict == "unknown"

    def test_the_real_document_still_carries_exactly_one(self):
        """The live half — this fires the day the block loses its marker.

        Which is the whole point of the verdict being ``unknown``: the
        check goes loud rather than agreeable, and this says so first.
        """
        region, problem = load_region()
        assert region, problem
        sentence, why = claim_sentence(region, "open_titles")
        assert sentence is not None, why
        assert len(sentence) < len(flatten(region)) / 100


class TestTheSentenceBoundary:
    """What may and may not end a sentence — :data:`SENTENCE_END_RE`."""

    def test_a_full_stop_inside_a_quoted_title_does_not_end_it(self):
        """Alert titles carry full stops and this is not hypothetical.

        ``sysadmin.service failed`` and ``Estate hook session-notice.sh not
        wired for Notification`` are both real titles on this box.  **The
        veil is what saves them, not the lookahead** — this test was
        written crediting the lookahead and stayed green when it was
        removed, because a quoted title is blanked before any boundary is
        looked for.  Falsified by veiling with a single space instead.
        The lookahead's own population is
        :meth:`test_a_bolded_lead_in_sentence_is_not_swallowed`.
        """
        block = (
            "> `alerts` holds **2** unresolved rows, `sysadmin.service failed` and\n"
            "> `Estate hook session-notice.sh not wired for Notification`, **2**\n"
            "> named here <!--check:open_titles-->.\n"
        )
        facts = DatabaseFacts(
            11, 2,
            ("critical: sysadmin.service failed",
             "warning: Estate hook session-notice.sh not wired for Notification"),
        )
        assert check_open_titles(block, "", facts).verdict == "match"

    def test_a_full_stop_with_a_space_inside_a_quoted_title_is_veiled(self):
        """The half the lookahead alone cannot reach.

        Falsified by veiling with a single space the way
        :func:`read_markers` does: the offsets stop indexing the original
        and the slice lands in the wrong place.
        """
        block = (
            "> `alerts` holds **1** unresolved row,\n"
            "> `Log error: sysadmin.service — Failed with result. Retrying now`,\n"
            "> **1** named here <!--check:open_titles-->.\n"
        )
        facts = DatabaseFacts(
            11, 1,
            ("warning: Log error: sysadmin.service — Failed with result. Retrying now",),
        )
        assert check_open_titles(block, "", facts).verdict == "match"

    def test_a_bolded_lead_in_sentence_is_not_swallowed(self):
        """:data:`SENTENCE_END_RE`'s trailing class, at its live shape.

        Every paragraph in this block opens with a bolded lead-in, so
        ``.**`` is how a sentence ends here **290 times** in the printed
        region.  A terminator that insists on whitespace immediately after
        the stop refuses all of them, and the marked sentence then runs
        backwards through the lead-in — rule 10's defect at one paragraph.

        Falsified against ``[.!?](?=\\s|$)``, which is what shipped first
        and which swallows the lead-in whole.
        """
        block = (
            "> **The estate wrote nothing overnight and `Disk full on /` cleared.**\n"
            "> `alerts` holds **1** unresolved row, `Project Alfred next action\n"
            "> idle`, **1** named here <!--check:open_titles-->.\n"
        )
        sentence, _ = claim_sentence(block, "open_titles")
        assert "cleared" not in sentence
        facts = DatabaseFacts(
            11, 2,
            ("critical: Disk full on /", "warning: Project Alfred next action idle"),
        )
        claim = check_open_titles(block, "", facts)
        assert claim.verdict == "mismatch"
        assert claim.detail == ("unnamed: critical: Disk full on /",)

    def test_a_decimal_figure_in_prose_does_not_end_the_sentence(self):
        """The lookahead's own population, and it is not the quoted title.

        A figure the block measures is written in **bold**, not in a code
        span — ``median uptime **1.77 h**`` is the shape — so the veil
        does not reach it and only the lookahead does.  Without one the
        sentence is cut at ``1.`` and every title after it reads unnamed,
        which is a false ``mismatch`` a sitting cannot fix by rewording.

        Falsified against ``[.!?]``, which is the pattern with no
        lookahead at all.  **The figure has to sit between the titles and
        the marker**, which the first version of this test got wrong: a
        cut ahead of the list leaves every title inside the sentence and
        the check answers ``match`` either way, so the fixture agreed with
        the mutation it was written to kill.
        """
        block = (
            "> `alerts` holds **1** unresolved row, `Project Alfred next action\n"
            "> idle`, and the daemon's median life is **1.77 h**, **1** named\n"
            "> here <!--check:open_titles-->.\n"
        )
        facts = DatabaseFacts(11, 1, ("warning: Project Alfred next action idle",))
        assert check_open_titles(block, "", facts).verdict == "match"

    def test_a_parenthetical_closes_before_the_marked_sentence(self):
        """``.)*`` is why ``)`` and ``*`` are both in the class.

        The block's fall notes are written ``*(… doing its job.)*``, and a
        note that cannot close is joined to the sentence *after* it — so
        the marked sentence would inherit every title the note names,
        which is the direction that yields ``match``.  The note is placed
        before the marked sentence deliberately: after it, the extraction
        ends at the marker's own full stop and the class decides nothing.
        The first version of this test made that mistake and passed
        against ``[.!?](?=\\s|$)``.

        Falsified against that pattern, which swallows the note.
        """
        block = (
            "> *(2 until 09:00 — `Disk full on /` cleared, the fall note doing\n"
            "> its job.)* `alerts` holds **1** unresolved row, `Project Alfred\n"
            "> next action idle`, **1** named here <!--check:open_titles-->.\n"
        )
        sentence, _ = claim_sentence(block, "open_titles")
        assert "fall note" not in sentence
        facts = DatabaseFacts(
            11, 2,
            ("critical: Disk full on /", "warning: Project Alfred next action idle"),
        )
        claim = check_open_titles(block, "", facts)
        assert claim.verdict == "mismatch"
        assert claim.detail == ("unnamed: critical: Disk full on /",)

    def test_the_previous_sentence_is_not_part_of_the_haystack(self):
        block = (
            "> The estate wrote nothing overnight and `Disk full on /` cleared.\n"
            "> `alerts` holds **1** unresolved row, `Project Alfred next action\n"
            "> idle`, **1** named here <!--check:open_titles-->.\n"
        )
        facts = DatabaseFacts(
            11, 2,
            ("critical: Disk full on /", "warning: Project Alfred next action idle"),
        )
        claim = check_open_titles(block, "", facts)
        assert claim.verdict == "mismatch"
        assert claim.detail == ("unnamed: critical: Disk full on /",)

    def test_a_block_with_no_terminator_at_all_is_the_whole_region(self):
        """The degenerate case fails toward the old behaviour, not a crash.

        A marked sentence with nothing to bound it is the whole block,
        which is exactly what the check did before rule 10 — no worse, and
        reachable only by a document nobody would write.
        """
        block = "> `Disk full on /` is open <!--check:open_titles-->"
        facts = DatabaseFacts(11, 1, ("critical: Disk full on /",))
        assert check_open_titles(block, "", facts).verdict == "match"


class TestTheSentenceIsReadTheWayMarkersAre:
    """The veil is one rule read twice — ``SNAG-DOCS-005`` and rule 10."""

    def test_a_quoted_marker_does_not_anchor_the_check(self):
        """Quoting a marker re-arms nothing, here either.

        ``read_markers`` already refuses a marker inside a code span; a
        second reader that accepted one would put the two at odds about
        which sentences the document marks.
        """
        block = "> The `<!--check:open_titles-->` marker names this check."
        sentence, problem = claim_sentence(block, "open_titles")
        assert sentence is None
        assert "no sentence carries" in problem

    def test_the_two_veilings_would_still_agree_on_the_real_document(self):
        """The fact that licensed collapsing them into one.

        :func:`read_markers` used to blank each code span with a *single*
        space, because it wanted only the set of markers; locating a
        sentence needs offsets that still index the prose, so it reads the
        length-preserving veil now (``SNAG-DOCS-008``).  That swap is
        behaviour-preserving only while the two see the same markers —
        26.5 kB of the live block is code spans — so the discarded veiling
        is driven here rather than deleted along with its call site.
        Falsified by collapsing spans to the empty string, which lets a
        marker straddling one re-form.
        """
        region, problem = load_region()
        assert region, problem
        from sysadmin.ops_claims import _veiled

        prose = flatten(region)
        discarded = CODE_SPAN_RE.sub(" ", prose)
        assert len(discarded) < len(prose), "the block carries no code spans to veil"
        seen = [(m.group(1), m.group(2).strip()) for m in MARKER_RE.finditer(discarded)]
        assert seen == [(m.key, m.argument) for m in read_markers(region)]
        assert len(_veiled(prose)) == len(prose)

    def test_a_marker_in_the_sentence_cannot_satisfy_the_check(self):
        """``prose_without_markers``' reason, one span narrower.

        An ``expires`` argument is free text naming what the prediction is
        about, so a marker sharing the sentence could put a title into it
        and have the check agree with the checker's own words.  Falsified
        by returning the slice unstripped.
        """
        block = (
            "> `alerts` holds **1** unresolved row <!--check:expires\n"
            "> 2026-09-05T03:32+01:00 the Disk full on / row clears-->, **1**\n"
            "> named here <!--check:open_titles-->.\n"
        )
        claim = check_open_titles(block, "", DatabaseFacts(11, 1, ("critical: Disk full on /",)))
        assert claim.verdict == "mismatch"


#: The commit ``SNAG-ESTATE-016`` was found at — the block hand-corrected
#: that afternoon, and the last revision in which the marked sentence named
#: a row that was not open.
SPECIMEN_COMMIT = "9a3fe30"


@pytest.fixture(scope="module")
def region():
    """``docs/roadmap/STATUS.md``'s printed region as it stood at the commit.

    Skipped when the commit does not resolve — a shallow clone or a
    rewritten history — and a **red** for every other way ``git show``
    can fail, since a gate that swallows those goes green on exactly the
    box where the pin matters.
    """
    resolved = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"{SPECIMEN_COMMIT}^{{commit}}"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    if resolved.returncode != 0:
        pytest.skip(f"{SPECIMEN_COMMIT} is not in this checkout — the specimen is unreadable")
    shown = subprocess.run(
        ["git", "show", f"{SPECIMEN_COMMIT}:docs/roadmap/STATUS.md"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    printed = printed_region(shown.stdout)
    assert printed is not None, "the specimen has no '## Quick Status' heading"
    return printed


class TestTheBlockThatOpenedTheEntry:
    """The specimen, driven at the real document rather than at its shape.

    ``SNAG-ESTATE-016`` was found because a hand-corrected block disagreed
    with a green check.  This reads ``docs/roadmap/STATUS.md`` as it stood
    at ``9a3fe30`` — 178,301 characters flattened — and asserts the two
    verdicts the entry reports: the sentence named a row that was not open
    and omitted one that was, and the check said ``match``.

    Skipped, never failed, when the commit is not in this checkout: a
    shallow clone or a rewritten history is a reason to know less about
    the specimen, and :class:`TestTheHaystackIsOneSentence` carries the
    rules regardless.  Gated on the **commit resolving**, never on
    ``git show`` working — a subprocess that fails for any other reason is
    a red, because ``importorskip``-shaped gates go green on the one box
    where the pin matters.
    """

    #: The four rows unresolved at that commit, per the entry.  The fourth
    #: is the discriminator: the sentence names ``GPU was reset — every
    #: client lost its VRAM`` instead, which had already resolved.
    OPEN_THEN = (
        "critical: High disk usage on /",
        "warning: Project ImbaBots next action idle",
        "warning: Estate port 3110 registry breach",
        "warning: High VRAM usage on AMD Radeon RX 7900 XTX",
    )
    MISSING = "High VRAM usage on AMD Radeon RX 7900 XTX"
    NAMED_INSTEAD = "GPU was reset — every client lost its VRAM"

    def test_the_specimen_is_the_one_the_entry_measured(self, region):
        """The premise, asserted before either verdict is believed.

        The entry's number is what makes the mechanism a mechanism, and a
        specimen that had drifted would let both assertions below pass for
        the wrong reason.
        """
        assert len(flatten(region)) == 178301

    def test_the_marked_sentence_named_a_row_that_was_not_open(self, region):
        sentence, problem = claim_sentence(region, "open_titles")
        assert sentence is not None, problem
        assert self.NAMED_INSTEAD in sentence
        assert self.MISSING not in sentence

    def test_the_missing_title_was_in_the_region_once_and_far_below(self, region):
        """Why the pre-fix check said ``match``, measured rather than said.

        One occurrence, in an account of a fault four sittings old — so
        the whole-region test was satisfied by history and the marked
        sentence was never consulted.
        """
        prose = flatten(region)
        assert prose.count(self.MISSING) == 1
        marker = prose.index("<!--check:open_titles-->")
        assert prose.index(self.MISSING) > marker
        # Far enough below that no sentence boundary could reach it.
        assert prose.index(self.MISSING) - marker > 5000

    def test_the_narrowed_check_refutes_the_block_the_old_one_passed(self, region):
        claim = check_open_titles(region, "", DatabaseFacts(14, 4, self.OPEN_THEN))
        assert claim.verdict == "mismatch"
        assert claim.documented == "3 named"
        assert claim.measured == "4 open"
        assert claim.detail == (f"unnamed: warning: {self.MISSING}",)

    def test_the_same_block_still_matches_the_rows_it_claimed(self, region):
        """The narrowing discriminates rather than merely refusing.

        Same 178 kB, same sentence, the population the sentence describes
        — and the verdict moves with the population.  Without this the
        test above is satisfied by any change that makes the check louder.
        """
        claimed = self.OPEN_THEN[:3] + (f"warning: {self.NAMED_INSTEAD}",)
        assert check_open_titles(region, "", DatabaseFacts(14, 4, claimed)).verdict == "match"


class TestTheConventionAgainstTheRealDocument:
    """The live half — these fire the day the block gains an unmarked figure."""

    def test_the_real_block_leaves_no_figure_unclaimed(self):
        region, problem = load_region()
        assert region is not None, problem
        findings = check_markers(region, read_markers(region))
        unclaimed = [claim.key for claim in findings if claim.key.startswith("unclaimed:")]
        assert not unclaimed, f"STATUS.md states these and no line claims them: {unclaimed}"

    def test_every_marker_in_the_real_block_names_a_check_that_exists(self):
        region, problem = load_region()
        assert region is not None, problem
        unknown = sorted({m.key for m in read_markers(region)} - CHECK_KEYS)
        assert not unknown, f"STATUS.md names checks nobody implements: {unknown}"

    def test_every_prediction_in_the_real_block_is_pinned_to_its_sentence(self):
        """Rule 9 against the document rather than a fixture.

        A marker whose wall clock has drifted out of the prose is the one
        way the expiry family can go quiet, so it is asserted here as well
        as in :class:`TestExpiry`.

        **The loop body ran for the first time on 2026-09-04**, the family
        having shipped untriggered on 2026-08-24 — so what this asserted
        for eleven days was that an empty ``for`` completes.  Driving it at
        the first live marker found it **half a guard**: it keyed on two
        note substrings, and every :func:`_convention` refusal writes a
        note carrying neither, so a naive instant (``SNAG-ESTATE-013``'s
        own founding shape), an unparseable one and a marker carrying no
        instant at all *all passed*.  Measured, not reasoned — all three
        driven at the real document.

        ``kind`` is what separates them, and it is deliberately not a
        verdict test: a prediction whose moment has passed earns
        ``unknown`` by rule 8, so asserting the verdict would turn this red
        on the morning a prediction came true — the calendar writing a
        failure, which is the reading this repository has refused four
        times over.  A convention finding is the third *kind* (rule 7), so
        the axis that separates a broken marker from a passed one is the
        one that carries no date in it.
        """
        region, problem = load_region()
        assert region is not None, problem
        for marker in read_markers(region):
            if marker.key != "expires":
                continue
            claim = check_expiry(marker, datetime.now().astimezone())
            assert claim.kind != "convention", f"malformed: {claim.note}"
            assert "does not" not in claim.note, f"unpinned: {marker.argument}"
            assert "different clocks" not in claim.note, f"zone drift: {marker.argument}"
