"""Something on the close path runs ``tests/test_handoff_shape.py``.

The guard that outlives ``SNAG-TEST-005``, closed 2026-09-06.  That entry
was never about the shape guard, which works — it was red at ``457d011``
and caught the fault the moment anything ran it.  It was about the
*moment*: ``HANDOFF.md`` is written at the end of a sitting, after the
suite has been reported green, and nothing between that edit and the
commit ran the file again.  ``check_handoff_shape_unguarded`` retired with
the entry; this did not, because deleting a detector along with its last
finding takes the guard against the defect coming back — ``FROZEN_TABLES``'
rule, and the shape ``SNAG-LOG-006`` and ``SNAG-TEST-004`` both left
behind.

**It is stronger than the check in two axes, and the first of them is
two rules that are multiplicative rather than independent** —
``SNAG-AGENT-008``'s shape, and the sitting's own prose was wrong about
it until the counterfactual below was driven.  The retired check swept
for *either* name on any line that was not a comment.  Delete the
invocation and leave the two lines of *advice* the fix also added, and:

* as written it answers ``mismatch``, reporting a closed entry over a
  live regression — which is the part that was expected;
* **the mention rule alone does not fix that.**  ``if [ -x
  ".venv/bin/pytest" ]`` is a genuine non-echo line naming ``pytest``, so
  an *either*-rule still answers ``mismatch``;
* **requiring both names alone does not fix it either.**  The advice echo
  carries ``test_handoff_shape``, so a both-rule without the mention rule
  goes green.

Only the pair sees it, which is why neither is observable on its own
against the shipped script and why
:class:`TestNeitherRuleCatchesTheRegressionAlone` drives them at a
stand-in instead.

**The second axis is that running the guard was never the whole claim.**
``check-vacuous-guards.sh`` has run the whole suite at the close since
2026-09-05, and renders a red one as exit 2, *"the measure did not run"*,
with **no** ``ISSUES`` and ``No uncommitted code changes to test`` beneath
it on a docs-only sitting — which is exactly the sitting that breaks this
document.  So what is pinned here is the invocation *and* that its red is
heard.

**The block is extracted from the shipped script and driven**, never
retyped: a copy of a shell block in a test is a second statement of it,
free to agree with the test while disagreeing with the file.  The three
readings are driven at a **stub** ``pytest`` rather than the real one, for
two reasons — a test in ``test_handoff_shape.py`` that ran the close would
recurse into itself, and the red reading is otherwise only reachable by
mutating the live ``HANDOFF.md``, which another session in this tree would
see.  What is under test is the block's branching, not pytest.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent
POSTFLIGHT = REPO / "scripts" / "claude-postflight.sh"

#: The block's own markers, and the section that must follow it.
BLOCK_OPENS = "# 3.9. Is the handoff"
BLOCK_CLOSES = "# 4. DOCUMENTATION ENFORCEMENT"

#: What a line has to name to be running the guard.  ``pytest`` is the
#: command and ``test_handoff_shape`` the file, and the fix names both.
GUARD_INVOCATIONS = ("pytest", "test_handoff_shape")


def _executable_lines(path: pathlib.Path) -> list[str]:
    """The script's lines with comments and blanks dropped.

    ``test_schema_guard``'s idiom, which reads the same directory for the
    opposite claim.  A comment naming the guard is prose about it.
    """
    raw = path.read_text(encoding="utf-8")
    return [line for line in raw.splitlines() if (s := line.strip()) and not s.startswith("#")]


def _invokes(lines: list[str], needle: str) -> bool:
    """Does *needle* appear on a line that **runs** something?

    The comment rule one step further, and it has a live specimen rather
    than a hypothetical one — see
    :meth:`TestAMentionIsNotAnInvocation.test_the_script_really_does_mention_without_running`.

    It is half of a rule and not a rule: on its own it still reads the
    regression as a fix, because the binary is also named by the ``[ -x
    … ]`` test that guards the call.  What it buys is that the *second*
    name has to be invoked too, which the advice line would otherwise
    have supplied.  See the module docstring.
    """
    return any(needle in line and not line.strip().startswith("echo") for line in lines)


def _block() -> str:
    """The shipped bytes of the gate, between its own two markers."""
    lines = POSTFLIGHT.read_text(encoding="utf-8").splitlines()
    opens = [i for i, line in enumerate(lines) if line.startswith(BLOCK_OPENS)]
    closes = [i for i, line in enumerate(lines) if line.startswith(BLOCK_CLOSES)]
    assert len(opens) == 1 and len(closes) == 1, (
        f"the gate's markers are not where this test can find them: {opens}, {closes}"
    )
    assert opens[0] < closes[0], "the gate is no longer above the documentation section"
    return "\n".join(lines[opens[0] : closes[0]])


def _drive(tmp_path: pathlib.Path, pytest_exit: int | None) -> str:
    """Run the shipped block against a stub ``pytest``.

    *pytest_exit* is the status the stub returns, or ``None`` for a tree
    with no ``.venv/bin/pytest`` at all — the reading that must not be
    mistaken for a pass.
    """
    if pytest_exit is not None:
        binary = tmp_path / ".venv" / "bin" / "pytest"
        binary.parent.mkdir(parents=True)
        binary.write_text(
            "#!/bin/sh\n"
            "echo 'FAILED tests/test_handoff_shape.py::a_rule_this_document_breaks'\n"
            f"exit {pytest_exit}\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)

    script = tmp_path / "gate.sh"
    script.write_text(
        'RED=""; GREEN=""; YELLOW=""; BLUE=""; BOLD=""; NC=""; ISSUES=0\n'
        + _block()
        + '\necho "ISSUES=$ISSUES"\n',
        encoding="utf-8",
    )
    done = subprocess.run(
        ["bash", str(script)], cwd=tmp_path, capture_output=True, text=True, timeout=60
    )
    assert done.returncode == 0, f"the block itself fell over: {done.stderr}"
    return done.stdout


class TestThePremises:
    """What makes the sweeps below evidence rather than a green nothing."""

    def test_the_script_is_there_and_is_runnable(self):
        assert POSTFLIGHT.is_file(), f"{POSTFLIGHT} is gone — the close runs nothing"
        assert os.access(POSTFLIGHT, os.X_OK), (
            "a mode is not content, so nothing that reads this file could see it "
            "(commit 30bfbea shipped claude-preflight.sh at 0644)"
        )

    def test_the_sweep_has_something_to_read(self):
        assert _executable_lines(POSTFLIGHT), (
            "no executable lines, so every sweep below would pass over an empty "
            "population — ports_checked's rule"
        )

    def test_the_block_can_still_be_found(self):
        assert _block().strip(), "the gate's markers no longer bound anything"


class TestTheCloseRunsTheGuard:
    def test_it_invokes_the_handoff_shape_file(self):
        """The defect coming back.

        Not "the suite runs at the close" — that has been true since
        2026-09-05 through ``check-vacuous-guards.sh`` and was not
        enough, because a red there is exit 2 and reads as a measure that
        did not run.  What is asserted is that the guard is invoked by
        name, which is what makes its red a finding.
        """
        lines = _executable_lines(POSTFLIGHT)
        missing = [needle for needle in GUARD_INVOCATIONS if not _invokes(lines, needle)]
        assert not missing, (
            "the close no longer runs tests/test_handoff_shape.py, so a HANDOFF.md that "
            "estate-manager's parser would misread reaches the estate board with nobody "
            f"having heard the guard: {missing} named on no line that runs anything"
        )

    def test_it_runs_after_the_document_is_written(self):
        """Placement, and it is not decoration.

        The gate is worth nothing above the point at which a sitting has
        written its handoff.  Nothing in the script states that moment,
        so what is pinned is the weaker fact that can be: it sits with
        the other machine gates and above the documentation section, in
        a script whose whole purpose is the close.
        """
        text = POSTFLIGHT.read_text(encoding="utf-8")
        assert text.index(BLOCK_OPENS) > text.index("# 3.8."), (
            "the handoff gate has moved above the vacuous-guard gate"
        )
        assert text.index(BLOCK_OPENS) < text.index(BLOCK_CLOSES)


class TestAMentionIsNotAnInvocation:
    """The axis the retired check was blind on.

    Its sweep was a substring over executable lines, so the two lines of
    *advice* this fix also added would have satisfied it on their own —
    and a sitting deleting the invocation while leaving the advice would
    have kept it answering ``mismatch``, reporting a closed entry over a
    live regression.
    """

    def test_the_script_really_does_mention_without_running(self):
        """The anti-vacuity premise, and its population is live.

        Without this the rule below is asserted against a file that
        happens to contain no such line, which is a rule nothing could
        have broken.
        """
        mentions = [
            line.strip()
            for line in _executable_lines(POSTFLIGHT)
            if "pytest" in line and line.strip().startswith("echo")
        ]
        assert mentions, (
            "no line advises running pytest without running it, so the rule below is "
            "untested against this script"
        )

    def test_advice_alone_would_not_satisfy_the_sweep(self, tmp_path):
        """Driven at the real advice lines, not at a hand-written one."""
        advice = [
            line
            for line in _executable_lines(POSTFLIGHT)
            if "pytest" in line and line.strip().startswith("echo")
        ]
        assert not any(_invokes(advice, needle) for needle in GUARD_INVOCATIONS), (
            f"these run nothing and would be read as running the guard: {advice}"
        )

    def test_a_comment_would_not_either(self, tmp_path):
        """The rule this detector was born with, driven at the real reader.

        A script documenting the guard is what the entry was about in
        the first place, so a sweep satisfied by prose would have
        reported the fix landed on the paragraph describing it.
        """
        script = tmp_path / "claude-postflight.sh"
        script.write_text(
            "# TODO: .venv/bin/pytest tests/test_handoff_shape.py one day\n"
            "./scripts/check-migrations.sh\n",
            encoding="utf-8",
        )
        lines = _executable_lines(script)
        assert lines, "the reader dropped every line, so the assertion below is vacuous"
        assert not any(_invokes(lines, needle) for needle in GUARD_INVOCATIONS)


class TestNeitherRuleCatchesTheRegressionAlone:
    """A recorded counterfactual, and it says so.

    ``test_it_invokes_the_handoff_shape_file`` catches the regression —
    driven, it turns red when the invocation is deleted and the advice is
    left.  What it cannot show is *why*, because both of its rules fire
    together at the shipped script and no mutation of one alone is
    visible there.  So the two are driven apart at a stand-in carrying
    the regression, which is the only place they are separable.

    This guards no behaviour of its own.  It exists so that a later
    sitting simplifying either rule away sees the cost stated as a red
    test rather than as a paragraph nobody re-derives.
    """

    #: The regression: the call gone, the ``[ -x … ]`` guard and the two
    #: lines of advice left exactly as the fix wrote them.
    REGRESSED = (
        'if [ -x ".venv/bin/pytest" ]; then\n'
        '    HANDOFF_OUT=""\n'
        '    echo -e "  Why: .venv/bin/pytest tests/test_handoff_shape.py"\n'
        "else\n"
        "    echo -e \"  no .venv/bin/pytest - run 'uv sync --all-extras'\"\n"
        "fi\n"
    )

    @staticmethod
    def _lines(text: str) -> list[str]:
        return [line for line in text.splitlines() if (s := line.strip()) and not s.startswith("#")]

    @staticmethod
    def _seen(lines: list[str], needle: str, mention_rule: bool) -> bool:
        return any(
            needle in line and not (mention_rule and line.strip().startswith("echo"))
            for line in lines
        )

    def test_the_stand_in_really_carries_the_regression(self):
        """The premise.  A stand-in that still runs the guard would make
        every reading below agree for the wrong reason."""
        lines = self._lines(self.REGRESSED)
        assert lines
        assert not any(
            "test_handoff_shape" in line and not line.strip().startswith("echo")
            for line in lines
        ), "the stand-in still invokes the guard, so there is no regression to miss"

    def test_the_retired_rule_reads_it_as_a_fix(self):
        """Either-name, no mention rule — ``check_handoff_shape_unguarded``
        as Session 165 wrote it."""
        lines = self._lines(self.REGRESSED)
        assert any(self._seen(lines, n, mention_rule=False) for n in GUARD_INVOCATIONS)

    def test_the_mention_rule_alone_still_reads_it_as_a_fix(self):
        """Because ``[ -x ".venv/bin/pytest" ]`` is not an echo."""
        lines = self._lines(self.REGRESSED)
        assert any(self._seen(lines, n, mention_rule=True) for n in GUARD_INVOCATIONS)

    def test_requiring_both_names_alone_still_reads_it_as_a_fix(self):
        """Because the advice echo carries the second name."""
        lines = self._lines(self.REGRESSED)
        assert all(self._seen(lines, n, mention_rule=False) for n in GUARD_INVOCATIONS)

    def test_only_the_pair_sees_it(self):
        """The rule this file actually ships."""
        lines = self._lines(self.REGRESSED)
        assert not all(self._seen(lines, n, mention_rule=True) for n in GUARD_INVOCATIONS)


class TestTheThreeReadingsOfTheGate:
    """Driven at the shipped block, because the branching is the fix.

    Running the guard and *swallowing* its red is the state the transitive
    suite run was already in, so an invocation on its own is not the
    closure — being heard is.
    """

    def test_a_clean_document_is_quiet(self, tmp_path):
        out = _drive(tmp_path, pytest_exit=0)
        assert "ISSUES=0" in out
        assert "estate-manager parses" in out

    def test_a_broken_document_raises_an_issue_and_names_it(self, tmp_path):
        out = _drive(tmp_path, pytest_exit=1)
        assert "ISSUES=1" in out, (
            "the close ran the guard and said nothing the summary counts — which is "
            "the state check-vacuous-guards.sh was already in"
        )
        assert "wrong line to the estate board" in out
        assert "a_rule_this_document_breaks" in out, (
            "the finding does not name which rule broke, so a reader has to go and "
            "run it themselves to learn anything"
        )

    def test_no_binary_is_not_a_pass(self, tmp_path):
        """``ports_checked``'s rule.

        A bare ``uv sync`` prunes the dev extra, and a gate that went
        green on an absent pytest would report the document clean on
        exactly the box that had stopped checking it.
        """
        out = _drive(tmp_path, pytest_exit=None)
        assert "ISSUES=0" in out, "an environment fault is not a defect in the document"
        assert "not the same as 'the handoff is fine'" in out
        assert "estate-manager parses" not in out


class TestTheCommitPathStaysRefused:
    """The half the entry refused, pinned as a *record* and not as a ban.

    ``claude-precommit.sh`` deliberately does not run the suite: 63 s on
    every commit, against damage that begins at the edit rather than at
    the commit, since the estate reads this file from disk.  A later
    sitting may overturn that on its own measurement — what this refuses
    is overturning it silently, so the assertion names the cost rather
    than forbidding the line.
    """

    def test_the_pre_commit_hook_still_does_not_run_the_suite(self):
        lines = _executable_lines(REPO / "scripts" / "claude-precommit.sh")
        assert lines, "the pre-commit script would not read"
        running = [needle for needle in GUARD_INVOCATIONS if _invokes(lines, needle)]
        if running:
            pytest.fail(
                "the pre-commit hook now runs the suite. That may be right — but "
                "SNAG-TEST-005 refused it twice at 63 s on every commit, so the "
                "measurement that overturned it belongs in the register beside this "
                f"test: {running}"
            )
