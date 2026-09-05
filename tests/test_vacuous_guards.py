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
import sqlite3
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from sysadmin import vacuous_guards
from sysadmin.core import schema_guard
from sysadmin.core.config import REPO_ROOT
from sysadmin.vacuous_guards import (
    DECLARATION,
    LOOP_DECLARATION,
    Sweep,
    _declared_reason,
    _loop_turned,
    main,
    read_arcs,
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
    """The half a line report cannot reach, on every report.

    Still a standing declaration and still on every report — what moved
    with ``SNAG-TEST-009`` is that there are now two spellings of it, and
    which one prints is the whole of what ``--arcs`` buys.
    """

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

        Driven without ``--arcs``, which is the reading this wording
        belongs to: the sites are unjudged, and the report says so
        rather than printing a zero for a question nobody asked.
        """
        root = _tree(tmp_path, {"test_a.py": self.BLIND})
        files = {"test_a.py": executed} if executed else {}
        result = sweep(_report(tmp_path, files), root)

        assert result.verdict == verdict
        assert any("did not judge them" in line for line in render(result))

    @pytest.mark.parametrize(
        ("executed", "verdict"),
        [([1, 2], "mismatch"), ([1], "mismatch"), ([], "unknown")],
        ids=["loop-finding", "assert-finding", "unknown"],
    )
    def test_the_judged_count_replaces_it_whatever_the_verdict(
        self, tmp_path, executed, verdict
    ):
        """The same property for the wider measure, and the pair is what
        keeps the two spellings from both going missing at once.

        The verdicts differ from the drive above because these sites are
        now judged, and the middle one is the reason the ids changed:
        with the assert unevaluated the *loop* half stands down — its
        statement never ran — and what remains is the assert finding, so
        this row is a second mismatch rather than the blind reading its
        old id claimed.
        """
        root = _tree(tmp_path, {"test_a.py": self.BLIND})
        files = {"test_a.py": executed} if executed else {}
        result = sweep(
            _report(tmp_path, files),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): set()}),
        )
        text = "\n".join(render(result))

        assert result.verdict == verdict
        assert "comprehension sites under tests/ turned at least once" in text
        assert "did not judge them" not in text

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


# ---------------------------------------------------------------------------
# SNAG-TEST-009 — the guard that ran over nothing
# ---------------------------------------------------------------------------


def _arcs(tmp_path: Path, arcs: dict[str, set[tuple[int, int]]], *, branch: bool = True) -> Path:
    """A ``coverage run --branch`` data file, in coverage's own schema.

    Hand-built rather than produced, for the module's stated reason —
    coverage is not installed on this box.  What that costs is that these
    drives pin the *rules* and not the model of coverage they rest on,
    which is why :file:`tests/test_vacuous_guards_live.py` exists and
    runs the real tool over the same shapes.
    """
    path = tmp_path / ".coverage"
    with sqlite3.connect(path) as db:
        db.execute("create table coverage_schema (version integer)")
        db.execute("insert into coverage_schema values (7)")
        db.execute("create table meta (key text, value text)")
        db.execute("insert into meta values ('version', '7.16.0')")
        db.execute("insert into meta values ('has_arcs', ?)", ("1" if branch else "0",))
        db.execute("create table file (id integer primary key, path text)")
        db.execute(
            "create table arc "
            "(file_id integer, context_id integer, fromno integer, tono integer)"
        )
        for index, (name, pairs) in enumerate(arcs.items(), start=1):
            db.execute("insert into file values (?, ?)", (index, name))
            for start, end in pairs:
                db.execute("insert into arc values (?, 0, ?, ?)", (index, start, end))
    return path


def _only_comprehension(source: str) -> tuple[ast.expr, list[ast.expr]]:
    """The first comprehension in a snippet, and every comprehension in it."""
    tree = ast.parse(textwrap.dedent(source).lstrip("\n"))
    found = [
        node
        for node in ast.walk(tree)
        if isinstance(node, vacuous_guards._COMPREHENSIONS)
    ]
    return found[0], found


class TestTheBackEdgeRule:
    """Rule 1 — a turn reaches the element line, and only a turn does.

    Every arc set below is the one the real tool emits for that shape,
    transcribed from a live ``coverage run --branch`` over the same
    source.  The pairs are what make each drive a falsification rather
    than a restatement: the *only* difference between the turning and
    empty members of each pair is the arc a turn leaves.
    """

    def test_a_single_line_comprehension_that_turned_leaves_a_self_arc(self):
        node, siblings = _only_comprehension("assert all(x > 0 for x in live)")

        assert _loop_turned(node, {(1, 1)}, siblings) == (True, None)

    def test_the_same_comprehension_over_an_empty_iterable_leaves_none(self):
        node, siblings = _only_comprehension("assert all(x > 0 for x in live)")

        assert _loop_turned(node, set(), siblings) == (False, None)

    def test_a_multi_line_comprehension_turns_on_an_arc_into_its_element(self):
        """The two-line case, and the one the entry's own rule gets wrong.

        ``SNAG-TEST-009`` records rule 1 as *any arc running backwards
        inside the span*.  Both arc sets here satisfy that — ``(3, 1)`` is
        the generator's exhaustion *return*, present whether or not the
        loop ever turned — so the wider rule reports the empty case as
        turned and hides the finding.
        """
        source = """
            assert all(
                x > 0
                for x in live
            )
            """
        node, siblings = _only_comprehension(source)
        empty = {(1, 3), (3, 1)}

        assert _loop_turned(node, empty, siblings) == (False, None)
        assert _loop_turned(node, empty | {(3, 2), (2, 3)}, siblings) == (True, None)

    def test_entering_the_comprehension_is_not_a_turn(self):
        """The one arc excluded, and it exists only where the element
        sits below the first line — which is why the exclusion is
        conditioned on that rather than written unconditionally."""
        source = """
            assert all(
                x > 0 for x in live
            )
            """
        node, siblings = _only_comprehension(source)

        assert _loop_turned(node, {(1, 2), (2, 1)}, siblings) == (False, None)
        assert _loop_turned(node, {(1, 2), (2, 1), (2, 2)}, siblings) == (True, None)

    def test_a_dict_comprehension_is_judged_on_the_earlier_of_key_and_value(self):
        source = """
            assert {
                key:
                value
                for key, value in live
            } == {}
            """
        node, siblings = _only_comprehension(source)

        assert _loop_turned(node, {(1, 4), (4, 1)}, siblings) == (False, None)
        assert _loop_turned(node, {(1, 4), (4, 1), (4, 2)}, siblings) == (True, None)


class TestTheShortCircuitRule:
    """Rule 2 — ``any`` and ``next`` abandon the frame mid-yield.

    Without it every short-circuiting generator in the suite reads as
    empty, because the abandoned frame emits neither the back-edge nor
    the exit arc.  The discriminator is the *exit*: an exhausted
    generator returns, an abandoned one never does.
    """

    def test_a_generator_entered_and_never_returned_yielded_at_least_once(self):
        node, siblings = _only_comprehension("assert any(x > 0 for x in live)")

        assert _loop_turned(node, {(-1, 1)}, siblings) == (True, None)

    def test_a_generator_entered_and_returned_with_no_back_edge_is_empty(self):
        """The pair that makes the rule a rule rather than "no arcs means
        empty": both sets lack the back-edge and only one has the exit."""
        node, siblings = _only_comprehension("assert not any(x > 0 for x in live)")

        assert _loop_turned(node, {(-1, 1), (1, -1)}, siblings) == (False, None)

    def test_a_generator_never_reached_at_all_is_empty(self):
        node, siblings = _only_comprehension("assert any(x > 0 for x in live)")

        assert _loop_turned(node, set(), siblings) == (False, None)


class TestInlinedComprehensionsTakeTheBackEdgeAlone:
    """Rule 3 — PEP 709 leaves list, set and dict comprehensions no frame.

    So rule 2 has nothing to read for them, and the rule is expressed by
    asking rule 2 only of a generator rather than by a second branch.
    The drive is the *counterfactual*: handed a frame-entry arc that a
    list comprehension can never produce, it must still answer from the
    back-edge, or a comprehension that genuinely ran over nothing inside
    an abandoned outer frame would read as having turned.
    """

    def test_a_list_comprehension_is_not_rescued_by_a_frame_entry_arc(self):
        node, siblings = _only_comprehension("assert [x for x in live] == []")

        assert _loop_turned(node, {(-1, 1)}, siblings) == (False, None)

    def test_a_set_comprehension_still_turns_on_its_back_edge(self):
        node, siblings = _only_comprehension("assert {x for x in live} == set()")

        assert _loop_turned(node, {(1, 1)}, siblings) == (True, None)


class TestWhatTheArcsCannotDecide:
    """The two shapes where a turning loop and an empty one are spelled
    identically, and are therefore refused rather than guessed at."""

    def test_an_element_on_the_first_line_of_a_multi_line_comprehension(self):
        """The iteration arc and the return arc are the same pair.

        Measured, not reasoned about: driven at the real tool, zero and
        two iterations of ``all(x > 0\\n for x in live)`` both produce
        exactly ``{(1, 2), (2, 1)}``.
        """
        source = """
            assert all(x > 0
                       for x in live)
            """
        node, siblings = _only_comprehension(source)
        turned, why = _loop_turned(node, {(1, 2), (2, 1)}, siblings)

        assert turned is None
        assert why == "its element sits on the comprehension's own first line"

    def test_the_refusal_is_not_specific_to_generators(self):
        """A list comprehension is inlined and has no return arc of its
        own, and the enclosing multi-line statement supplies the same
        pair anyway — so conditioning the refusal on the node type would
        leave the list case guessing."""
        source = """
            assert [x
                    for x in live] == []
            """
        node, siblings = _only_comprehension(source)

        assert _loop_turned(node, {(1, 2), (2, 1)}, siblings)[0] is None

    def test_two_comprehensions_sharing_an_element_line_decide_neither(self):
        node, siblings = _only_comprehension(
            "assert all(any(d in c for d in denials) for c in clauses)"
        )

        assert len(siblings) == 2
        for comprehension in siblings:
            turned, why = _loop_turned(comprehension, {(1, 1)}, siblings)
            assert turned is None
            assert why == "another comprehension shares its element line"

    def test_adjacent_comprehensions_collide_as_readily_as_nested_ones(self):
        """Not only nesting: two comprehensions written side by side on
        one line share every arc that could decide either."""
        node, siblings = _only_comprehension(
            "assert [a for a in left] == [b for b in right]"
        )

        assert [_loop_turned(c, {(1, 1)}, siblings)[0] for c in siblings] == [None, None]

    def test_a_comprehension_alone_on_its_line_is_still_decided(self):
        """The anti-vacuity half: the sibling rule must not swallow the
        ordinary case, which is what makes the four drives above mean
        something."""
        node, siblings = _only_comprehension("assert all(x > 0 for x in live)")

        assert _loop_turned(node, {(1, 1)}, siblings) == (True, None)


VACUOUS_AND_TURNING = """
def test_over_nothing():
    live = []
    assert all(x > 0 for x in live)

def test_over_something():
    live = [1]
    assert all(x > 0 for x in live)
"""


class TestTheLoopHalfOfTheSweep:
    """The join, end to end: source, a line report, and a branch data file."""

    def _sweep(self, tmp_path, source, *, executed, arcs, branch=True):
        root = _tree(tmp_path, {"test_a.py": source})
        return sweep(
            _report(tmp_path, {"test_a.py": executed}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): arcs}, branch=branch),
        )

    def test_a_comprehension_that_turned_zero_times_is_a_finding(self, tmp_path):
        result = self._sweep(
            tmp_path, VACUOUS_AND_TURNING,
            executed=[1, 2, 3, 5, 6, 7], arcs={(7, 7)},
        )

        assert [loop.line for loop in result.loop_findings] == [3]
        assert result.verdict == "mismatch"
        assert result.loops == 2
        assert result.loops_turned == 1

    def test_the_finding_survives_the_other_halfs_declaration(self, tmp_path):
        """The two markers are not interchangeable, which is the whole
        reason there are two of them.

        A ``may-not-evaluate`` reason on a statement says the *assert*
        need not run.  Read as covering the loop as well, it would
        silence this finding — and because a loop cannot turn without its
        statement running, the reverse reading would report every loop
        declaration as a stale assert declaration on every run.
        """
        source = VACUOUS_AND_TURNING.replace(
            "    assert all(x > 0 for x in live)\n\ndef test_over_something",
            f"    # {DECLARATION} the estate is idle most of the day\n"
            "    assert all(x > 0 for x in live)\n\ndef test_over_something",
            1,
        )
        result = self._sweep(
            tmp_path, source, executed=[1, 2, 4, 6, 7, 8], arcs={(8, 8)}
        )

        assert [loop.line for loop in result.loop_findings] == [4]
        assert result.declared == ()
        assert [guard.line for guard in result.stale] == [4]

    def test_its_own_declaration_quietens_it_and_is_reported(self, tmp_path):
        source = VACUOUS_AND_TURNING.replace(
            "    assert all(x > 0 for x in live)\n\ndef test_over_something",
            f"    # {LOOP_DECLARATION} an empty findings list is the healthy result\n"
            "    assert all(x > 0 for x in live)\n\ndef test_over_something",
            1,
        )
        result = self._sweep(
            tmp_path, source, executed=[1, 2, 4, 6, 7, 8], arcs={(8, 8)}
        )

        assert result.loop_findings == ()
        assert result.verdict == "match"
        assert [loop.reason for loop in result.loop_declared] == [
            "an empty findings list is the healthy result"
        ]

    def test_a_declaration_whose_loop_turned_anyway_is_named_not_swallowed(self, tmp_path):
        """``known_noise``'s rule: a stale exemption stops describing
        anything and starts hiding the next finding."""
        source = f"""
            def test_over_something():
                live = [1]
                # {LOOP_DECLARATION} thought to be empty here
                assert all(x > 0 for x in live)
            """
        result = self._sweep(
            tmp_path, source, executed=[1, 2, 4], arcs={(4, 4)}
        )

        assert result.loop_findings == ()
        assert [loop.reason for loop in result.loop_stale] == ["thought to be empty here"]
        assert result.verdict == "match"

    def test_a_comprehension_in_a_message_is_never_a_finding(self, tmp_path):
        """It is evaluated only once the assert has already failed, so on
        a green run its loop turning zero times is the definition of
        health."""
        source = """
            def test_it():
                live = []
                assert True, f"{[x for x in live]}"
            """
        result = self._sweep(tmp_path, source, executed=[1, 2, 3], arcs=set())

        assert result.loop_findings == ()
        assert result.loops == 0

    def test_a_statement_that_never_ran_is_left_to_the_other_half(self, tmp_path):
        """One fault, one speaker.

        A comprehension in a skipped test turned zero times and says
        nothing whatever about a population.  The assert half already
        owns *this never executed*; reporting it here as well would give
        one fault two speakers, which is the defect this repository has
        now found at seven scales.
        """
        source = """
            def test_it():
                live = []
                assert all(x > 0 for x in live)
            """
        result = self._sweep(tmp_path, source, executed=[1, 2], arcs=set())

        assert result.loop_findings == ()
        assert [guard.line for guard in result.findings] == [3]

    def test_a_comprehension_outside_an_assert_is_still_judged(self, tmp_path):
        """``SNAG-TEST-009`` measured seven live sites that bind the
        comprehension to a local and assert on the *name*, which an
        ``ast.Assert.test``-only walk cannot see and which are guard
        claims all the same."""
        source = """
            def test_it():
                live = []
                names = [row.name for row in live]
                assert not names
            """
        result = self._sweep(tmp_path, source, executed=[1, 2, 3, 4], arcs=set())

        assert [loop.line for loop in result.loop_findings] == [3]

    def test_an_undecidable_site_moves_no_verdict_and_is_named(self, tmp_path):
        source = """
            def test_it():
                live = []
                assert all(x > 0
                           for x in live)
            """
        result = self._sweep(
            tmp_path, source, executed=[1, 2, 3], arcs={(3, 4), (4, 3)}
        )

        assert result.loop_findings == ()
        assert result.verdict == "match"
        assert [loop.line for loop in result.loop_undecidable] == [3]
        assert result.loops_turned == 0
        assert result.loops == 1

    def test_the_undecidable_set_is_named_in_the_report(self, tmp_path):
        source = """
            def test_it():
                live = []
                assert all(x > 0
                           for x in live)
            """
        result = self._sweep(
            tmp_path, source, executed=[1, 2, 3], arcs={(3, 4), (4, 3)}
        )
        text = "\n".join(render(result))

        assert "cannot be decided either way" in text
        assert "test_a.py:3" in text


class TestTheBranchDataFileIsRequiredToJudge:
    """``ports_checked``'s rule, with the fail-closed direction chosen
    because the alternative is a *loud* false positive rather than a
    quiet false negative."""

    def test_a_data_file_written_without_branch_is_refused(self, tmp_path):
        """The failure this gate exists to not have.

        A line-only data file opens cleanly and has an empty ``arc``
        table, so read as evidence it says every comprehension in the
        suite ran over nothing — hundreds of findings out of a missing
        flag.  ``meta.has_arcs`` separates the two, and it is read rather
        than inferred from the row count, which cannot.
        """
        root = _tree(tmp_path, {"test_a.py": VACUOUS_AND_TURNING})
        result = sweep(
            _report(tmp_path, {"test_a.py": [1, 2, 3, 5, 6, 7]}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): set()}, branch=False),
        )

        assert result.verdict == "unknown"
        assert result.problem is not None and "--branch" in result.problem
        assert result.loop_findings == ()

    def test_an_empty_arc_table_from_a_branch_run_is_evidence(self, tmp_path):
        """The other side of the same coin, and what makes the drive
        above a discriminator rather than "no arcs means unknown": the
        identical empty table, declared as a branch run, is read."""
        root = _tree(tmp_path, {"test_a.py": VACUOUS_AND_TURNING})
        result = sweep(
            _report(tmp_path, {"test_a.py": [1, 2, 3, 5, 6, 7]}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): set()}, branch=True),
        )

        assert result.verdict == "mismatch"
        assert [loop.line for loop in result.loop_findings] == [3, 7]

    def test_no_data_file_at_all_leaves_the_half_unjudged_and_says_so(self, tmp_path):
        """Absent is not broken.  ``--report`` alone stays a legitimate
        narrower measure, and the report must not print a zero for a
        question it did not ask."""
        root = _tree(tmp_path, {"test_a.py": VACUOUS_AND_TURNING})
        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 3, 5, 6, 7]}), root)
        text = "\n".join(render(result))

        assert result.verdict == "match"
        assert result.loops_measured is False
        assert "did not judge them" in text
        assert "--arcs" in text

    def test_an_unreadable_data_file_is_unknown_not_a_narrower_measure(self, tmp_path):
        root = _tree(tmp_path, {"test_a.py": VACUOUS_AND_TURNING})
        rubbish = tmp_path / "not-a-database"
        rubbish.write_text("certainly not sqlite")

        result = sweep(_report(tmp_path, {"test_a.py": [1, 2, 3]}), root, rubbish)

        assert result.verdict == "unknown"

    def test_read_arcs_keys_on_the_resolved_path(self, tmp_path):
        arcs = read_arcs(_arcs(tmp_path, {"tests/test_a.py": {(1, 1)}}))

        assert arcs == {(REPO_ROOT / "tests/test_a.py").resolve(): {(1, 1)}}

    def test_read_arcs_refuses_a_missing_file(self, tmp_path):
        assert read_arcs(tmp_path / "nothing-here") is None


class TestTheGateAsksForBranchArcs:
    """The shell half.  The module cannot judge what the run did not
    record, so the flag and the data file are pinned at their one caller
    rather than left to be true by habit."""

    def test_the_suite_is_run_with_branch(self):
        assert "coverage run --branch" in GATE.read_text()

    def test_the_data_file_is_handed_to_the_judge(self):
        body = GATE.read_text()

        assert "--arcs" in body
        assert '--report "$WORK/coverage.json" --arcs "$WORK/.coverage"' in body

    def test_the_refuted_sentence_is_gone_from_both_artefacts(self):
        """``SNAG-TEST-009``'s first clause stood for three sittings:
        *branch coverage cannot either, because the comprehension's own
        iteration is not a branch of the assert statement*.  It is not a
        branch of the assert, and coverage records the back-edge
        regardless — so the claim that no measure can reach these must
        not survive the measure that does.
        """
        for path in (GATE, REPO_ROOT / "sysadmin" / "vacuous_guards.py"):
            body = path.read_text()
            assert "no line-coverage measure can judge" not in body, path
            assert "this measure cannot judge them" not in body, path


class TestADeclarationCoversOneComprehension:
    """One statement can hold several, and one comment must not cover all.

    Found by running the gate rather than by argument, and it shipped
    **green**: a ``return {...}`` in
    ``tests/test_message_backfill_live.py`` holds six comprehensions, a
    statement-anchored read attached one comment to all six, and a stale
    declaration moves no verdict — so only the stale report named it.
    """

    SIX_IN_ONE_STATEMENT = f"""
        def test_it():
            empty = []
            full = [1]
            return {{
                # {LOOP_DECLARATION} this one is empty by design
                "a": {{x for x in empty}},
                "b": {{x for x in full}},
            }}
        """

    def _sweep(self, tmp_path, arcs):
        root = _tree(tmp_path, {"test_a.py": self.SIX_IN_ONE_STATEMENT})
        return sweep(
            _report(tmp_path, {"test_a.py": [1, 2, 3, 4]}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): arcs}),
        )

    def test_only_the_declared_comprehension_is_quietened(self, tmp_path):
        result = self._sweep(tmp_path, set())

        assert [loop.line for loop in result.loop_declared] == [6]
        assert [loop.line for loop in result.loop_findings] == [7]

    def test_its_neighbour_is_not_reported_stale_when_it_turns(self, tmp_path):
        """The shape the live run actually produced: four sites reported
        as *declared and turned anyway* off one comment they had nothing
        to do with."""
        result = self._sweep(tmp_path, {(7, 7)})

        assert result.loop_stale == ()
        assert [loop.line for loop in result.loop_declared] == [6]

    def test_a_marker_inside_a_nested_comprehension_is_not_the_outers(self, tmp_path):
        """``last`` stops at the comprehension's own first line, so the
        inner one's claim cannot be read as the outer's."""
        source = f"""
            def test_it():
                rows = [[1]]
                assert all(
                    all(  # {LOOP_DECLARATION} the inner list is empty here
                        y for y in inner
                    )
                    for inner in rows
                )
            """
        root = _tree(tmp_path, {"test_a.py": source})
        result = sweep(
            _report(tmp_path, {"test_a.py": [1, 2, 3]}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): set()}),
        )
        declared = {loop.line for loop in result.loop_declared}
        findings = {loop.line for loop in result.loop_findings}

        assert declared == {4}
        assert findings == {3}

    def test_a_multi_line_reason_survives_the_new_anchor(self, tmp_path):
        """The same live run truncated every reason to *"so nothing is"*,
        because the statement-line road takes only the marker's own line
        while the comment-block road continues onto the next.  Anchoring
        on the comprehension puts the block directly above it, so the
        reason is read whole."""
        source = f"""
            def test_it():
                empty = []
                return {{
                    # {LOOP_DECLARATION} the baseline is read before the rows
                    # are added, so nothing is frozen yet
                    "a": {{x for x in empty}},
                }}
            """
        root = _tree(tmp_path, {"test_a.py": source})
        result = sweep(
            _report(tmp_path, {"test_a.py": [1, 2, 3]}),
            root,
            _arcs(tmp_path, {str(root / "test_a.py"): set()}),
        )

        assert [loop.reason for loop in result.loop_declared] == [
            "the baseline is read before the rows are added, so nothing is frozen yet"
        ]
