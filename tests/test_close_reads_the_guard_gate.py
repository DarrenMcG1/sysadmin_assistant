"""The close tells a red suite apart from a measure that could not run.

The guard that outlives ``SNAG-TEST-012``, closed 2026-09-06.

``scripts/check-vacuous-guards.sh`` returns **2** for four different
things — a red suite, no ``uv``, no console script, and a tree the
coverage report does not describe — and argues in writing that a red
suite is not *its* finding, because reporting it would make that gate
loudest exactly when pytest is already saying something truer.  That
reasoning is sound and is about that script.  What nobody argued for was
``claude-postflight.sh`` discarding the distinction: it rendered all four
as *"The measure did not run"*, raised no ``ISSUES``, and then fell to
step 6, whose ``else`` branch printed ``✓ No uncommitted code changes to
test`` — true about its own subject and false about the reader's
question, which is ``UnitFinding.enabled``'s trap.

**A docs-only sitting is the population and not an edge case.**
``TOTAL_CODE`` counts *code* files, so the sitting that edits only
documents has none — and that is exactly the sitting that breaks a
document guard.

**The blocks are extracted from the shipped script and driven**, never
retyped, which is ``tests/test_close_runs_the_handoff_guard.py``'s idiom
one section over: a copy of a shell block in a test is a second statement
of it, free to agree with the test while disagreeing with the file.  Both
blocks go into one harness because step 6 reads two variables step 3.8
sets, and the defect lived in the *join* — 3.8 knowing something it did
not pass on, and step 6 asserting health it had not seen.

The gate is driven at a **stub** ``check-vacuous-guards.sh``: the real one
runs the whole suite under coverage for ninety seconds, and the readings
that matter are the ones a green box cannot produce.  What is under test
is the branching, not the gate.

**The marker is pinned at both ends** rather than merely used.  A shell
caller cannot import a producer's sentence, so it holds a copy — and a
copy that drifts silently rebuilds the entry.  ``import where you can,
pin where you cannot``: :class:`TestTheMarkerIsTheProducersOwnSentence`
reads both files and asserts the caller's needle is the producer's
red-suite line and **no other road's**.
"""

from __future__ import annotations

import pathlib
import re
import subprocess

REPO = pathlib.Path(__file__).resolve().parent.parent
POSTFLIGHT = REPO / "scripts" / "claude-postflight.sh"
GATE = REPO / "scripts" / "check-vacuous-guards.sh"
JUDGE = REPO / "sysadmin" / "vacuous_guards.py"

#: The two blocks the fix lives in, by their own section markers.
GUARDS_BLOCK = ("# 3.8. Did every assert", "# 3.9. Is the handoff")
TESTS_BLOCK = ("# 6. Run tests if there are code changes", "# 7. Run consistency audits")

#: Fragments of the four readings, short enough not to be a second copy
#: of the sentences and distinctive enough to name one branch each.
SAYS_GREEN = "Suite ran green under the vacuous-guard gate above"
SAYS_VACUOUS = "Fix it, or declare it"
SAYS_RED_AT_38 = "the gate above ran it and stopped there"
SAYS_RED_AT_6 = "The suite is red — the gate above ran it; see 3.8"
SAYS_BLIND = "The measure did not run"
SAYS_RUN_IT_YOURSELF = "could not run the suite — run it yourself"

#: The tick this entry exists to have deleted.
THE_OLD_TICK = "No uncommitted code changes to test"


def _block(opens: str, closes: str) -> str:
    """The shipped bytes between two of the script's own markers."""
    lines = POSTFLIGHT.read_text(encoding="utf-8").splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(opens)]
    ends = [i for i, line in enumerate(lines) if line.startswith(closes)]
    assert len(starts) == 1 and len(ends) == 1, (
        f"the block's markers are not where this test can find them: {starts}, {ends}"
    )
    assert starts[0] < ends[0], f"{opens!r} no longer sits above {closes!r}"
    return "\n".join(lines[starts[0] : ends[0]])


def _runs(line: str, needle: str) -> bool:
    """Does *needle* appear on a line that runs something?

    ``test_close_runs_the_handoff_guard``'s rule, and it has a live
    specimen here: ``check-vacuous-guards.sh`` names both ``coverage
    json`` and ``-m pytest`` in the prose above the code, and the prose
    comes first — so a bare substring search finds the paragraph
    describing the invocation rather than the invocation.
    """
    stripped = line.strip()
    return needle in line and not stripped.startswith("#")


def _marker() -> str:
    """The sentence ``claude-postflight.sh`` keys the red-suite road on.

    Read out of the shipped script rather than typed here, so this file
    cannot pin a value the script has stopped using.
    """
    found = re.findall(
        r'^SUITE_RED_MARKER="([^"]+)"$', POSTFLIGHT.read_text(encoding="utf-8"), re.MULTILINE
    )
    assert len(found) == 1, (
        f"the close no longer names one marker for the red-suite road: {found}"
    )
    return found[0]


def _drive(
    tmp_path: pathlib.Path, *, status: int, output: str, staged_code: int = 0
) -> str:
    """Run both shipped blocks against a stub gate in a throwaway repo.

    *status* and *output* are what the stub ``check-vacuous-guards.sh``
    returns; *staged_code* is how many ``.py`` files step 6 will find, so
    the caller can cross the gate's reading with ``TOTAL_CODE``.
    """
    gate = tmp_path / "scripts" / "check-vacuous-guards.sh"
    gate.parent.mkdir(parents=True)
    gate.write_text(
        "#!/bin/sh\ncat <<'STUB_EOF' >&2\n" + output + f"\nSTUB_EOF\nexit {status}\n",
        encoding="utf-8",
    )
    gate.chmod(0o755)

    subprocess.run(["git", "init", "-q", "."], cwd=tmp_path, check=True, timeout=30)
    for n in range(staged_code):
        (tmp_path / f"changed_{n}.py").write_text("x = 1\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", f"changed_{n}.py"], cwd=tmp_path, check=True, timeout=30
        )

    script = tmp_path / "close.sh"
    script.write_text(
        'RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""; ISSUES=0\n'
        + _block(*GUARDS_BLOCK)
        + "\n"
        + _block(*TESTS_BLOCK)
        + '\necho "ISSUES=$ISSUES"\n',
        encoding="utf-8",
    )
    done = subprocess.run(
        ["bash", str(script)], cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, f"the blocks themselves fell over: {done.stderr}"
    return done.stdout


class TestThePremises:
    """What makes the drives below evidence rather than a green nothing."""

    def test_both_blocks_can_still_be_found(self):
        assert _block(*GUARDS_BLOCK).strip(), "the vacuous-guard block's markers bound nothing"
        assert _block(*TESTS_BLOCK).strip(), "the test-status block's markers bound nothing"

    def test_the_two_blocks_are_joined_by_the_variables_the_defect_lived_in(self):
        """The join is the subject, so a harness that split them would
        drive two blocks that cannot contradict each other."""
        guards, tests = _block(*GUARDS_BLOCK), _block(*TESTS_BLOCK)
        for name in ("GUARDS_STATUS", "SUITE_RED"):
            assert f"{name}=" in guards, f"{name} is no longer set by the gate block"
            assert name in tests, f"step 6 no longer reads {name}, so the join is gone"

    def test_the_stub_is_what_the_block_actually_calls(self, tmp_path):
        """Otherwise every reading below is the block failing to find a
        gate at all, which happens to look like exit 2."""
        out = _drive(tmp_path, status=0, output="ok every assert evaluated")
        assert "every assert evaluated" in out, (
            "the block did not run the stub, so nothing below drives the gate's reading"
        )


class TestTheMarkerIsTheProducersOwnSentence:
    """A copy the producer can move out from under, pinned at both ends.

    The gate's exit status is lossy by that script's own argument, so the
    only discriminator is its prose.  What must hold is not that the
    string exists but that it names **one** road: a needle matching the
    ``no uv`` line as well would report a red suite on a box that has no
    uv, which is the entry's defect with the polarity reversed.
    """

    def test_the_close_names_one_marker(self):
        assert _marker().strip(), "the marker is empty, so the case matches everything"

    def test_the_producer_still_emits_it(self):
        assert _marker() in GATE.read_text(encoding="utf-8"), (
            f"{GATE.name} no longer prints {_marker()!r}, so the close silently stopped "
            "telling a red suite from the three roads that could not measure — "
            "SNAG-TEST-012 returning by a reword"
        )

    def test_the_producer_has_other_roads_to_report(self):
        """The anti-vacuity premise for the rule below.

        Without other ``??`` lines, "exactly one carries it" is satisfied
        by a producer with one message, and the rule asserts nothing.
        """
        reports = [
            line for line in GATE.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith('echo "??')
        ]
        assert len(reports) > 1, (
            f"{GATE.name} reports one way, so the discrimination below is untested"
        )

    def test_no_other_road_carries_it(self):
        reports = [
            line for line in GATE.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith('echo "??') and _marker() in line
        ]
        assert len(reports) == 1, (
            f"{len(reports)} of the gate's reports carry {_marker()!r}; the close would "
            f"read one of the could-not-measure roads as a red suite: {reports}"
        )

    def test_it_sits_on_the_road_after_the_suite_runs(self):
        """Structure, not wording: between the pytest invocation and the
        coverage report, which is the only branch a red suite reaches."""
        lines = GATE.read_text(encoding="utf-8").splitlines()
        runs = next(i for i, line in enumerate(lines) if _runs(line, "-m pytest -q"))
        reports = next(i for i, line in enumerate(lines) if _runs(line, "coverage json"))
        marked = [i for i, line in enumerate(lines) if _marker() in line]
        assert marked == [i for i in marked if runs < i < reports], (
            f"the marker has left the failed-suite branch: {marked} against "
            f"pytest at {runs} and coverage json at {reports}"
        )

    def test_the_judge_does_not_speak_it(self):
        """The fifth road — ``sysadmin-check-guards`` exiting 2 over a
        tree the report does not describe — must not match either."""
        assert _marker() not in JUDGE.read_text(encoding="utf-8"), (
            f"{JUDGE.name} can now print the marker, so a stale coverage report would "
            "be announced as a red suite"
        )


class TestTheReadingsOfTheGateCrossedWithCodeChanges:
    """``GUARDS_STATUS`` against ``TOTAL_CODE``, at the shipped bytes."""

    def test_a_green_suite_is_a_tick(self, tmp_path):
        out = _drive(tmp_path, status=0, output="ok every assert under tests/ evaluated")
        assert "ISSUES=0" in out
        assert SAYS_GREEN in out
        assert SAYS_RED_AT_38 not in out

    def test_a_vacuous_guard_is_a_finding_and_the_suite_was_still_green(self, tmp_path):
        out = _drive(tmp_path, status=1, output="no 1 asserts under tests/ were never evaluated")
        assert "ISSUES=1" in out
        assert SAYS_VACUOUS in out
        assert SAYS_GREEN in out, "exit 1 means the suite ran and passed; step 6 must say so"
        assert SAYS_RED_AT_38 not in out

    def test_a_red_suite_on_a_docs_only_sitting_is_named_and_counted(self, tmp_path):
        """The founding reading: ``GUARDS_STATUS=2, TOTAL_CODE=0``."""
        out = _drive(tmp_path, status=2, output=f"?? {_marker()}, so nothing can be told")
        assert "ISSUES=1" in out, (
            "a red suite is heard by nobody at the close — the state SNAG-TEST-012 was "
            "opened about, with the summary free to print 'all clear' over it"
        )
        assert SAYS_RED_AT_38 in out
        assert SAYS_RED_AT_6 in out, (
            "step 6 is the section a reader comes to for the suite's state and says "
            "nothing about it"
        )
        assert THE_OLD_TICK not in out, "the close still claims health for a run it did not see"
        assert SAYS_BLIND not in out, (
            "a red suite is reported as a measure that did not run, which sends the "
            "reader to re-run the thing that has just told them the answer"
        )

    def test_a_red_suite_with_code_changes_reads_the_same_way(self, tmp_path):
        out = _drive(
            tmp_path, status=2, output=f"?? {_marker()}, so nothing can be told", staged_code=1
        )
        assert "ISSUES=1" in out
        assert SAYS_RED_AT_38 in out
        assert SAYS_RED_AT_6 in out
        assert SAYS_RUN_IT_YOURSELF not in out, (
            "the suite ran and failed; advising the reader to run it is the elif branch "
            "being wrong in the one of its four cases that matters"
        )

    def test_a_measure_that_could_not_run_stays_yellow_and_raises_nothing(self, tmp_path):
        """``ports_checked``'s rule, and the direction the fix must not
        have widened: an absent ``uv`` is an environment fault."""
        out = _drive(tmp_path, status=2, output="?? no uv on PATH; the suite was not run")
        assert "ISSUES=0" in out, "an environment fault became a defect in the sitting's work"
        assert SAYS_BLIND in out
        assert SAYS_RED_AT_38 not in out, "a could-not-measure road is announced as a red suite"
        assert THE_OLD_TICK not in out, (
            "step 6 still ticks a suite nothing ran — the entry's own symptom"
        )

    def test_a_road_that_prints_nothing_is_a_measure_that_did_not_run(self, tmp_path):
        """Why the discriminator is keyed **positively**.

        The script's own docstring enumerates four roads to exit 2;
        measured, there are six ``exit 2`` sites, and one of them —
        ``WORK=$(mktemp -d) || exit 2`` — prints nothing at all.  A
        discriminator spelled as *"not one of the other three sentences"*
        would read that silence as a red suite.  Keyed on the red-suite
        sentence, an empty report falls to could-not-measure by
        construction.
        """
        out = _drive(tmp_path, status=2, output="")
        assert "ISSUES=0" in out
        assert SAYS_BLIND in out
        assert SAYS_RED_AT_38 not in out, "a silent exit-2 road was announced as a red suite"
        assert THE_OLD_TICK not in out

    def test_a_measure_that_could_not_run_with_code_changes_still_advises(self, tmp_path):
        out = _drive(
            tmp_path, status=2, output="?? no uv on PATH; the suite was not run", staged_code=2
        )
        assert "ISSUES=0" in out
        assert SAYS_RUN_IT_YOURSELF in out
        assert "2 code file(s)" in out


class TestTheDiscriminatorIsReadOnlyWhereItMeans:
    """The status gate — and it is **behaviourally redundant today**,
    which is stated rather than discovered.

    ``sysadmin-check-guards`` quotes the **source text** of every assert
    it finds, so an exit-1 report can carry any sentence at all,
    including this one.  Reading the discriminator unconditionally would
    let a vacuous-guard finding be announced as a red suite.

    **Driven, that mutation passes.**  Widening the gate from ``-ge 2``
    to every status changes no output, because ``[ "$GUARDS_STATUS" -eq
    1 ]`` is tested first at 3.8 and ``-le 1`` wins at step 6 — so
    ``SUITE_RED=1`` at exit 1 is unobservable through both blocks.  The
    clause is kept anyway, for ``abandoned_runs``' reason: its
    *visibility* is what stops a later sitting reordering those branches
    and rebuilding the misread, and a clause whose removal is invisible
    in behaviour cannot be reached by a behavioural test.  So the
    behaviour is pinned below **and** the statement is, the second being
    the one the mutation moves.
    """

    def test_a_finding_carries_the_asserts_own_source(self):
        """The premise, and it belongs to the producer rather than here.

        ``render`` interpolates ``guard.source`` — the assert's text,
        verbatim — into an exit-1 report, so the sentence a report can
        carry is not bounded by anything this repository controls.  The
        population of asserts naming the marker is **empty today**,
        measured; what makes the reading below a rule rather than a
        hypothetical is that the channel exists.
        """
        source = JUDGE.read_text(encoding="utf-8")
        assert "guard.source" in source, (
            "the report no longer quotes an assert's own text, so an exit-1 report "
            "cannot carry arbitrary prose and the gate below guards nothing"
        )

    def test_a_finding_quoting_the_marker_is_still_a_finding(self, tmp_path):
        out = _drive(
            tmp_path,
            status=1,
            output=(
                "no 1 asserts under tests/ were never evaluated by a green suite\n"
                f'   test_close_reads_the_guard_gate.py:1  assert "{_marker()}" in gate'
            ),
        )
        assert "ISSUES=1" in out
        assert SAYS_VACUOUS in out
        assert SAYS_RED_AT_38 not in out, (
            "an exit-1 report quoting the marker was read as a red suite, so the close "
            "reports the wrong fault about a guard that named the right one"
        )

    def test_the_discriminator_is_read_only_at_the_status_carrying_four_roads(self):
        """The statement test, because the behaviour above is carried by
        the branch order and would survive this clause's deletion."""
        block = _block(*GUARDS_BLOCK).splitlines()
        reads = [i for i, line in enumerate(block) if line.strip().startswith('case "$GUARDS_OUT"')]
        assert len(reads) == 1, f"the close reads GUARDS_OUT {len(reads)} ways: {reads}"
        above = [
            line.strip()
            for line in block[: reads[0]]
            if (s := line.strip()) and not s.startswith("#")
        ]
        assert above and above[-1].startswith("if ["), (
            f"the discriminator is no longer inside a condition: {above[-1:]!r}"
        )
        assert "GUARDS_STATUS" in above[-1] and "2" in above[-1], (
            "the discriminator is read at a status that does not carry four roads, so an "
            f"exit-1 report quoting the marker can be announced as a red suite: {above[-1]!r}"
        )
