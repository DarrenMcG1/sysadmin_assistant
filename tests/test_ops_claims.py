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

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.routing import APIRoute

from sysadmin.core.config import REPO_ROOT
from sysadmin.core.schema_guard import EXIT_STATUS
from sysadmin.ops_claims import (
    CLAIM_PATTERNS,
    MAX_NAMED_ALERTS,
    STATUS_PATH,
    Claim,
    DatabaseFacts,
    UnitState,
    check_alerts,
    check_all,
    check_deploy,
    compare_claim,
    load_region,
    main,
    measure_routes,
    measure_unit,
    overall,
    printed_region,
    read_claim,
)

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

    def test_every_pattern_finds_its_claim_in_the_real_status_file(self):
        """A check whose subject silently disappears is no check at all.

        This is the one assertion that cannot be satisfied by editing this
        file: it reads ``docs/roadmap/STATUS.md`` as it stands.  If it
        fails, either the block moved or a sentence was rewritten, and the
        answer is to re-anchor the pattern — not to delete the claim.
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
