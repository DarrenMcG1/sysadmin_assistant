"""``SNAG-TEST-006`` — the gate that refuses an assert nothing evaluated.

Every drive here is against a synthetic tree and a synthetic coverage
report, because the module deliberately never imports ``coverage`` — the
tool is not a dependency and reaches the suite through an ephemeral
``uv run --with`` overlay, so a test that needed it would be a test this
box cannot run.  What that costs is stated rather than hidden: the
*coverage* half of the join — that a report attributes a multi-line
statement to its first line — cannot be asserted here and was measured
live instead, against ``tests/test_arbitrated_stops_live.py``'s four-line
assert, which came back missing as line 147 alone.  The :mod:`ast` half
is pinned below.
"""

from __future__ import annotations

import ast
import json
import re
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sysadmin import vacuous_guards
from sysadmin.core import schema_guard
from sysadmin.core.config import REPO_ROOT
from sysadmin.vacuous_guards import (
    DECLARATION,
    Sweep,
    _declared_reason,
    main,
    render,
    sweep,
)

POSTFLIGHT = REPO_ROOT / "scripts" / "claude-postflight.sh"
GATE = REPO_ROOT / "scripts" / "check-vacuous-guards.sh"


def _tree(tmp_path: Path, files: dict[str, str]) -> Path:
    """A stand-in ``tests/`` tree, written verbatim after a dedent."""
    root = tmp_path / "tests"
    root.mkdir(exist_ok=True)
    for name, body in files.items():
        (root / name).write_text(textwrap.dedent(body).lstrip("\n"))
    return root


def _report(
    tmp_path: Path,
    executed: dict[str, list[int]],
    *,
    root: Path | None = None,
    taken: datetime | None = None,
    stamp: str | None = "",
) -> Path:
    """A ``coverage json`` report over that tree.

    ``taken`` defaults to a minute in the future so the tree is older
    than the report, which is the ordering a real run produces and the
    one the staleness rule is written against.
    """
    base = root if root is not None else tmp_path / "tests"
    when = taken if taken is not None else datetime.now() + timedelta(minutes=1)
    document = {
        "meta": {"timestamp": when.isoformat() if stamp == "" else stamp},
        "files": {
            str(base / name): {"executed_lines": lines, "missing_lines": []}
            for name, lines in executed.items()
        },
    }
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(document))
    return path


ONE_OF_EACH = """
def test_ran():
    assert True

def _never_called():
    assert False
"""


class TestTheJoin:
    """An assert whose line never executed asserted nothing."""

    def test_a_never_evaluated_assert_is_a_finding(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        report = _report(tmp_path, {"test_a.py": [1, 2, 4]})

        result = sweep(report, root)

        assert result.verdict == "mismatch"
        assert [guard.line for guard in result.findings] == [5]

    def test_an_evaluated_assert_is_not_a_finding(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        report = _report(tmp_path, {"test_a.py": [1, 2, 4, 5]})

        result = sweep(report, root)

        assert result.verdict == "match"
        assert result.findings == ()
        assert result.asserts == 2

    def test_a_multi_line_assert_is_anchored_at_its_first_line(self, tmp_path):
        """The premise of the whole join, pinned on the half this box can see.

        Coverage attributes a statement to its first line, so an assert
        spanning four is present or absent as one number.  If
        :attr:`ast.Assert.lineno` ever named a different line the sweep
        would report every long assert as unevaluated, which is a wall
        of false findings rather than a silence — but it would be the
        gate's own credibility, so it is asserted rather than assumed.
        """
        source = 'def test_x():\n    assert (\n        1\n        == 1\n    )\n'
        node = next(n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assert))
        assert (node.lineno, node.end_lineno) == (2, 5)

        root = _tree(tmp_path, {"test_a.py": source})
        # Only the anchor is missing — the shape a real report produces.
        result = sweep(_report(tmp_path, {"test_a.py": [1]}), root)

        assert [guard.line for guard in result.findings] == [2]


class TestTheDeclaration:
    """Quietened, never suppressed — ``known_noise``'s rule 2."""

    DECLARED = f"""
    def _never_called():
        # {DECLARATION} the estate is idle most of the day
        assert False
    """

    def test_a_declared_assert_is_reported_and_not_refused(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": self.DECLARED})
        result = sweep(_report(tmp_path, {"test_a.py": [1]}), root)

        assert result.verdict == "match"
        assert result.findings == ()
        assert [guard.reason for guard in result.declared] == [
            "the estate is idle most of the day"
        ]
        assert any("declared may-not-evaluate" in line for line in render(result))

    @pytest.mark.parametrize(
        "bare",
        [
            f"def _f():\n    # {DECLARATION}\n    assert False\n",
            f"def _f():\n    assert False  # {DECLARATION}\n",
        ],
        ids=["block", "beside"],
    )
    def test_a_declaration_with_no_reason_is_not_a_declaration(self, tmp_path, bare):
        """``known_noise``'s ``reason`` is a required field, here too.

        A bare marker is a way to go quiet with nothing recording why,
        which is the shape the declaration exists to avoid rather than a
        cheaper spelling of it.

        **Both roads**, because the block rule gave the reader a second
        return and a drive at one of them is a drive at half the rule —
        the shape the timestamp's two roads had already cost this file
        once.
        """
        root = _tree(tmp_path, {"test_a.py": bare})

        result = sweep(_report(tmp_path, {"test_a.py": [1]}), root)

        assert result.verdict == "mismatch"
        assert result.declared == ()

    @pytest.mark.parametrize(
        "source",
        [
            f"def _f():\n    # {DECLARATION} above the statement\n    assert False\n",
            f"def _f():\n    assert False  # {DECLARATION} beside the statement\n",
            f"def _f():\n    assert (\n        # {DECLARATION} inside the statement\n"
            "        False\n    )\n",
        ],
        ids=["above", "beside", "inside"],
    )
    def test_all_three_placements_read(self, tmp_path, source):
        """Three spellings, one meaning, so all three are accepted.

        An unread declaration is worse than none, because its author
        believes it landed and the gate goes on refusing an assert they
        have already judged.
        """
        root = _tree(tmp_path, {"test_a.py": source})
        result = sweep(_report(tmp_path, {"test_a.py": [1]}), root)

        assert result.verdict == "match", result.findings

    def test_a_reason_continues_onto_the_blocks_following_lines(self, tmp_path):
        """The defect the first live run found and no fixture could.

        All six of this repository's declarations went in as comment
        blocks — one, two and three lines, the marker at the top of each
        — and a one-line lookback read exactly **one** of them.  Every
        synthetic fixture here used a single-line comment, which is the
        one shape that cannot discriminate the rule.
        """
        source = (
            "def _f():\n"
            f"    # {DECLARATION} only a granted lease has a key set to look in,\n"
            "    # and the queue is idle most of the day.\n"
            "    assert False\n"
        ).format(DECLARATION=DECLARATION)
        root = _tree(tmp_path, {"test_a.py": source})

        result = sweep(_report(tmp_path, {"test_a.py": [1]}), root)

        assert result.verdict == "match", result.findings
        assert result.declared[0].reason == (
            "only a granted lease has a key set to look in, and the queue is idle "
            "most of the day."
        )

    def test_a_comment_block_broken_by_code_does_not_reach(self, tmp_path):
        """The run is contiguous, or the lookback is unbounded.

        A marker further up a file, separated by a statement, is about
        something else — reading it would let one declaration silence
        every assert beneath it.
        """
        source = (
            "def _f():\n"
            f"    # {DECLARATION} about the line below this one\n"
            "    x = 1\n"
            "    assert x == 2\n"
        ).format(DECLARATION=DECLARATION)
        root = _tree(tmp_path, {"test_a.py": source})

        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 3]}), root)

        assert result.verdict == "mismatch"

    def test_every_declaration_in_this_repository_is_read(self):
        """The live half of the block rule, keyed on the reader.

        The count is asserted as well, because a walk that found no
        declarations would pass this by reading none of them.
        """
        read = 0
        for path in sorted((REPO_ROOT / "tests").rglob("*.py")):
            source = path.read_text()
            if DECLARATION not in source:
                continue
            lines = source.splitlines()
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Assert) and _declared_reason(node, lines):
                    read += 1
        written = sum(
            line.count(DECLARATION)
            for path in sorted((REPO_ROOT / "tests").rglob("*.py"))
            for line in path.read_text().splitlines()
        )
        assert written >= 6, "no declarations left — this test is judging nothing"
        assert read == written, (
            f"{written} declarations written, {read} reachable from an assert — "
            "a declaration its own gate cannot see is worse than none"
        )

    def test_a_declaration_whose_assert_evaluated_is_reported_as_stale(self, tmp_path):
        """Reported, and deliberately not a finding.

        Three of this repository's six declarations are branches on live
        state that *will* evaluate the day the estate holds a lease, so
        an evaluated declaration is the ordinary case rather than a
        stale one — but a declaration that has stopped describing
        anything hides the next real finding under it, which is
        ``config_keys`` rule 5's exemption trap, so it is named.
        """
        root = _tree(tmp_path, {"test_a.py": self.DECLARED})
        result = sweep(_report(tmp_path, {"test_a.py": [1, 3]}), root)

        assert result.verdict == "match"
        assert len(result.stale) == 1
        assert any("evaluated anyway" in line for line in render(result))

    def test_every_declaration_in_this_repository_carries_a_reason(self):
        """The live half, and its own anti-vacuity premise.

        A declaration with no reason is silently not a declaration, so
        the gate would refuse an assert whose author believed it
        settled.  The count is asserted as well as the property: a walk
        finding nothing would pass this by having looked at no
        declarations at all.
        """
        found = [
            (path.name, line)
            for path in sorted((REPO_ROOT / "tests").rglob("*.py"))
            for line in path.read_text().splitlines()
            if DECLARATION in line
        ]
        assert len(found) >= 6, "no declarations left — this test is judging nothing"
        empty = [where for where, line in found if not line.split(DECLARATION)[1].strip()]
        assert empty == []


class TestNotKnowing:
    """Zero findings from a report that measured nothing is not zero findings."""

    def test_a_file_absent_from_the_report_is_unknown_not_clean(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        result = sweep(_report(tmp_path, {}), root)

        assert result.verdict == "unknown"
        assert [Path(name).name for name in result.unmeasured] == ["test_a.py"]

    def test_a_file_with_no_asserts_is_not_reported_unmeasured(self, tmp_path):
        """``tests/__init__.py`` is empty and always will be.

        The blindness this rule is about is an assert nobody evaluated,
        so a file holding none cannot be hiding one — reporting it would
        make the gate permanently ``unknown`` on a repository that is
        fine, which is the always-yellow failure the third verdict was
        refused for.
        """
        root = _tree(tmp_path, {"__init__.py": "\n", "test_a.py": ONE_OF_EACH})
        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 4, 5]}), root)

        assert result.verdict == "match"
        assert result.unmeasured == ()

    def test_a_file_edited_after_the_run_is_unknown(self, tmp_path):
        """The join is line numbers against line numbers.

        Adding a comment moves every assert below it without changing a
        single statement, so a digest of the executed set would not
        notice — and it is exactly what this fix did to three test files
        between the coverage run and the sweep.
        """
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        report = _report(
            tmp_path,
            {"test_a.py": [1, 2, 4, 5]},
            taken=datetime.now() - timedelta(minutes=1),
        )

        result = sweep(report, root)

        assert result.verdict == "unknown"
        assert [Path(name).name for name in result.moved] == ["test_a.py"]

    def test_unknown_outranks_mismatch(self, tmp_path):
        """A finding count taken over an unknown fraction of the suite.

        The usual ordering here — ``ops_claims.overall`` — puts
        ``mismatch`` first, because a claim measured false outranks one
        nobody tested.  This is the reverse and the reversal is the
        point: the number is not a lower bound on anything a reader can
        act on until the sweep says what it covered.
        """
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH, "test_b.py": ONE_OF_EACH})
        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 4]}), root)

        assert result.findings, "the mismatch half of the premise is missing"
        assert result.unmeasured, "the unknown half of the premise is missing"
        assert result.verdict == "unknown"

    def test_a_report_that_will_not_read_is_unknown(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        broken = tmp_path / "coverage.json"
        broken.write_text("not json")

        result = sweep(broken, root)

        assert result.verdict == "unknown"
        assert result.problem is not None

    @pytest.mark.parametrize("stamp", [None, "not a date"], ids=["absent", "unparseable"])
    def test_a_report_with_no_usable_timestamp_fails_open(self, tmp_path, stamp):
        """The one place this module fails open, and only this one.

        Every other not-knowing here is about ``tests/``, where a silent
        skip understates the finding count.  This is about the report's
        own metadata: refusing every sweep because a future coverage
        release renamed a key would take the gate off the close path for
        a fact it can live without.

        **Both roads, because there are two and one drive covered
        whichever it happened to take.**  ``str(None)`` is ``"None"`` —
        truthy — so an absent stamp was reaching the parse branch and a
        mutation to the absent branch passed cleanly.
        """
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        report = _report(tmp_path, {"test_a.py": [1, 2, 4, 5]}, stamp=stamp)

        result = sweep(report, root)

        assert result.verdict == "match"
        assert result.moved == ()
        assert result.measured_at in ("", "not a date")


class TestTheStandingDeclaration:
    """The half no line-coverage measure can reach, on every report."""

    BLIND = """
    def test_ran():
        assert all(isinstance(x, str) for x in [])
    """

    @pytest.mark.parametrize(
        ("executed", "verdict"),
        [([1, 2], "match"), ([1], "mismatch"), ([], "unknown")],
        ids=["match", "mismatch", "unknown"],
    )
    def test_the_blind_count_is_printed_whatever_the_verdict(
        self, tmp_path, executed, verdict
    ):
        """``ports_checked`` literally: a field on every payload.

        A status that fired on it would fire for ever — the population
        is a property of the measure, not of the run — and a gate that
        is always yellow is ``SNAG-LOG-002``'s binary ``LOW``.
        """
        root = _tree(tmp_path, {"test_a.py": self.BLIND})
        files = {"test_a.py": executed} if executed else {}
        result = sweep(_report(tmp_path, files), root)

        assert result.verdict == verdict
        assert any("cannot judge them" in line for line in render(result))

    def test_the_blind_count_does_not_shrink_when_the_measure_goes_blind(self, tmp_path):
        """Counted before the three skips, because it describes the tree.

        Counting it after let the standing declaration fall 314 → 312
        the moment three files went ``moved``, which reads as a suite
        with fewer unjudgeable asserts rather than as a sweep that
        stopped looking.
        """
        root = _tree(tmp_path, {"test_a.py": self.BLIND})
        seen = sweep(_report(tmp_path, {"test_a.py": [1, 2]}), root)
        blind = sweep(
            _report(tmp_path, {"test_a.py": [1, 2]}, taken=datetime.now() - timedelta(1)),
            root,
        )

        assert blind.verdict == "unknown"
        assert len(blind.comprehension) == len(seen.comprehension) == 1
        assert blind.asserts == seen.asserts == 1

    def test_a_comprehension_in_the_message_is_not_counted(self, tmp_path):
        """``ast.Assert.test`` only.

        A comprehension in the message cannot decide whether the guard
        held, so counting it would inflate the population this measure
        admits it cannot judge — and that number is the whole of the
        third verdict.
        """
        source = 'def test_x():\n    assert 1 == 1, ", ".join(str(x) for x in [])\n'
        root = _tree(tmp_path, {"test_a.py": source})

        result = sweep(_report(tmp_path, {"test_a.py": [1, 2]}), root)

        assert result.asserts == 1
        assert result.comprehension == ()


class TestTheReport:
    """What a reader is handed."""

    def test_findings_are_ordered_by_path_and_line(self, tmp_path):
        """``ast.walk`` is breadth-first, so its order is not a reader's.

        Measured on the live tree before this was fixed: three findings
        in one file came out 166, 167, 147.
        """
        # The nested assert is written *first* and walked *last*: breadth
        # first visits both top-level asserts before descending.  A
        # specimen nesting downwards comes out 2, 4, 6 already sorted and
        # asserts nothing — which is how this test passed against an
        # unsorted implementation on its first drive.
        source = textwrap.dedent(
            """
            def _outer():
                if False:
                    assert False
                assert False
                assert False
            """
        ).lstrip("\n")
        root = _tree(tmp_path, {"test_b.py": source, "test_a.py": source})

        result = sweep(_report(tmp_path, {"test_a.py": [], "test_b.py": []}), root)

        walked = [
            node.lineno
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Assert)
        ]
        assert walked == [4, 5, 3], "the specimen no longer discriminates the sort"
        assert [(Path(g.path).name, g.line) for g in result.findings] == [
            ("test_a.py", 3),
            ("test_a.py", 4),
            ("test_a.py", 5),
            ("test_b.py", 3),
            ("test_b.py", 4),
            ("test_b.py", 5),
        ]

    def test_a_clean_sweep_says_how_many_it_looked_at(self, tmp_path):
        """"Nothing found" and "nothing looked at" are not one sentence."""
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 4, 5]}), root)

        assert any("2 asserts" in line for line in render(result))


class TestExitStatus:
    """0/1/2, with ``check-migrations.sh``'s meaning."""

    @pytest.mark.parametrize(
        ("executed", "status"),
        [({"test_a.py": [1, 2, 4, 5]}, 0), ({"test_a.py": [1, 2, 4]}, 1), ({}, 2)],
        ids=["clean", "found", "could-not-measure"],
    )
    def test_main_returns_the_shared_map(self, tmp_path, capsys, executed, status):
        root = _tree(tmp_path, {"test_a.py": ONE_OF_EACH})
        report = _report(tmp_path, executed)

        assert main(["--report", str(report), "--tests-root", str(root)]) == status

    def test_the_exit_map_is_imported_and_not_restated(self):
        """Provenance, not value — the shape this repository keeps finding.

        Three console scripts answer a shell caller with these three
        numbers, and a fourth spelling of them is one edit from
        disagreeing.  ``is`` discriminates where ``==`` cannot, a dict
        having no interning to borrow an identity from.
        """
        assert vacuous_guards.EXIT_STATUS is schema_guard.EXIT_STATUS


class TestTheGateIsOnTheClosePath:
    """The retired ``vacuous_guard_ungated`` check's detector, re-homed.

    ``FROZEN_TABLES``' rule: deleting a guard along with its last
    finding takes the guard against the defect coming back.  The check
    read the close path for a coverage invocation and retires refuted;
    what outlives it is the assertion that the wiring is still there,
    because a gate written and unwired is precisely the entry.
    """

    def test_postflight_runs_the_gate(self):
        lines = [
            line
            for line in POSTFLIGHT.read_text().splitlines()
            if GATE.name in line and not line.strip().startswith("#")
        ]
        runs = [line for line in lines if not re.match(r"\s*(echo|printf)\b", line)]
        assert runs, f"claude-postflight.sh names {GATE.name} but never runs it"

    def test_the_gate_runs_the_suite_under_coverage(self):
        body = [
            line
            for line in GATE.read_text().splitlines()
            if not line.strip().startswith("#")
        ]
        assert any("coverage run" in line for line in body)
        assert any("pytest" in line for line in body)

    def test_the_gate_never_exits_1_of_its_own_accord(self):
        """A red suite is 2, and everything this script decides is 2.

        ``1`` means an assert asserted nothing, which only the console
        script is in a position to say — so the shell passing its own
        ``1`` for a missing tool would be the gate reporting a finding
        it never looked for.
        """
        body = [
            line.strip()
            for line in GATE.read_text().splitlines()
            if not line.strip().startswith("#")
        ]
        assert [line for line in body if re.fullmatch(r"exit\s+1", line)] == []
        assert [line for line in body if re.fullmatch(r"exit\s+2", line)]

    def test_the_report_is_temporary(self):
        """A coverage.json left in the tree is what the next run reads.

        The join is line numbers against line numbers, so a stale report
        against an edited tree is confidently wrong rather than absent —
        the module refuses that join, and this keeps the file that would
        provoke it from existing at all.
        """
        body = GATE.read_text()
        assert "mktemp -d" in body
        assert re.search(r"trap\s+'rm -rf", body)


class TestSweepDefaults:
    """The dataclass a caller gets when nothing was read."""

    def test_an_empty_sweep_is_unknown_only_by_its_problem(self):
        """An all-defaults ``Sweep`` is ``match``, and that is correct.

        It models a tree with no test files rather than a failed read,
        so the verdict has to come from a field somebody set — which is
        why ``problem`` exists rather than the emptiness being read as
        blindness.
        """
        assert Sweep().verdict == "match"
        assert Sweep(problem="no report").verdict == "unknown"
