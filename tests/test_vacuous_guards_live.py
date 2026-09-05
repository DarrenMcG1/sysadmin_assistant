"""``SNAG-TEST-009`` — the arc rules against the real ``coverage --branch``.

:file:`tests/test_vacuous_guards.py` drives every rule at arc sets typed
out by hand, which pins the *rules* and takes the model of coverage they
rest on entirely on trust.  That is the half this file exists for, and it
is not a formality: the entry that ordered this fix records a detector
that was wrong three times before it was right — **110 → 43 → 26 → 23**
findings — with every wrong version returning a plausible number.  A
count cannot falsify a detector; a fixture whose iteration count is known
can.

So the shapes below are driven at 0, 1 and 2 iterations, at ``any`` and
``next``, and at both the single- and multi-line spellings, under the
real tool.  Two of the expectations here contradict what the entry wrote
down, and only running it could have said so:

* the entry's rule 1 — *some arc runs backwards inside the span* — is
  satisfied by a generator that turned **zero** times, because exhausting
  one emits a return arc from the ``for`` line to the frame's first line;
* two written shapes leave a turning loop and an empty one **byte
  identical**, which the entry does not record at all, and which this
  file asserts as an equality rather than describing.

``coverage`` is not a dependency here (see the module docstring), so it
arrives the way the gate brings it — an ephemeral ``uv run --with``
overlay that leaves ``.venv`` and the lock untouched.  The skip is gated
on ``uv`` being on ``PATH`` rather than on importing anything, because a
gate keyed on an import goes quietly green the day a sync prunes it.
"""

from __future__ import annotations

import ast
import shutil
import subprocess

import pytest

from sysadmin.vacuous_guards import _COMPREHENSIONS, _loop_turned, read_arcs

pytestmark = pytest.mark.skipif(
    shutil.which("uv") is None,
    reason="the branch-coverage drive needs uv to bring coverage in ephemerally",
)

#: One function per shape.  The name is the join — line numbers are read
#: back off the parsed tree rather than counted here, so inserting a case
#: cannot silently re-aim an expectation at its neighbour.
FIXTURE = '''
def single_line_zero():
    live = []
    assert all(x > 0 for x in live)


def single_line_one():
    live = [1]
    assert all(x > 0 for x in live)


def single_line_two():
    live = [1, 2]
    assert all(x > 0 for x in live)


def multi_line_zero():
    live = []
    assert all(
        x > 0
        for x in live
    )


def multi_line_two():
    live = [1, 2]
    assert all(
        x > 0
        for x in live
    )


def any_short_circuits():
    live = [1, 2, 3]
    assert any(x > 0 for x in live)


def any_over_empty():
    live = []
    assert not any(x > 0 for x in live)


def next_short_circuits():
    live = [1, 2, 3]
    assert next(x for x in live if x > 0) == 1


def listcomp_zero():
    live = []
    assert [x for x in live] == []


def listcomp_two():
    live = [1, 2]
    assert [x for x in live] == [1, 2]


def setcomp_zero():
    live = []
    assert {x for x in live} == set()


def dictcomp_two():
    live = [1, 2]
    assert {x: x for x in live} == {1: 1, 2: 2}


def element_on_first_line_zero():
    live = []
    assert all(x > 0
               for x in live)


def element_on_first_line_two():
    live = [1, 2]
    assert all(x > 0
               for x in live)


def never_consumed():
    live = [1, 2]
    generator = (x > 0 for x in live)
    assert generator is not None


for _case in (
    single_line_zero, single_line_one, single_line_two,
    multi_line_zero, multi_line_two,
    any_short_circuits, any_over_empty, next_short_circuits,
    listcomp_zero, listcomp_two, setcomp_zero, dictcomp_two,
    element_on_first_line_zero, element_on_first_line_two,
    never_consumed,
):
    _case()
'''

#: What each shape must come back as.  ``None`` is *refused*, never a
#: guess — see :class:`TestTheRefusalIsForced`, which asserts the arcs
#: really are indistinguishable rather than taking the refusal on faith.
EXPECTED = {
    "single_line_zero": False,
    "single_line_one": True,
    "single_line_two": True,
    "multi_line_zero": False,
    "multi_line_two": True,
    "any_short_circuits": True,
    "any_over_empty": False,
    "next_short_circuits": True,
    "listcomp_zero": False,
    "listcomp_two": True,
    "setcomp_zero": False,
    "dictcomp_two": True,
    "element_on_first_line_zero": None,
    "element_on_first_line_two": None,
    "never_consumed": False,
}


@pytest.fixture(scope="module")
def driven(tmp_path_factory) -> tuple[dict[str, ast.expr], set[tuple[int, int]], list[ast.expr]]:
    """Run the fixture under ``coverage run --branch`` and read its arcs.

    Module-scoped: one overlay resolution and one run for every drive
    below, which is what keeps the real tool affordable in a suite that
    must stay under a minute and a half.
    """
    work = tmp_path_factory.mktemp("branch-arcs")
    source = work / "shapes.py"
    source.write_text(FIXTURE.lstrip("\n"))
    data = work / ".coverage"

    run = subprocess.run(
        [
            "uv", "run", "--with", "coverage[toml]",
            "coverage", "run", "--branch",
            f"--data-file={data}", f"--source={work}",
            str(source),
        ],
        capture_output=True,
        text=True,
        cwd=work,
        timeout=300,
    )
    assert run.returncode == 0, run.stderr or run.stdout

    read = read_arcs(data)
    assert read is not None, "the run declared no branch arcs"
    arcs = read[source.resolve()]
    assert arcs, "the run recorded no arcs for the fixture at all"

    tree = ast.parse(source.read_text())
    siblings = [n for n in ast.walk(tree) if isinstance(n, _COMPREHENSIONS)]
    sites: dict[str, ast.expr] = {}
    for function in (n for n in tree.body if isinstance(n, ast.FunctionDef)):
        within = [
            node
            for node in ast.walk(function)
            if isinstance(node, _COMPREHENSIONS)
        ]
        assert len(within) == 1, f"{function.name} must carry exactly one comprehension"
        sites[function.name] = within[0]
    return sites, arcs, siblings


@pytest.mark.premise
class TestThePremise:
    """Before believing any verdict below, that the drive happened.

    Every verdict in this file is read off one arc set, so a drive that
    silently produced nothing would make every classification below
    ``False`` — *no back-edge* is exactly what an empty arc set says —
    and the file would go green while measuring nothing at all.  The
    module-scoped fixture refuses an empty read; these two ask the
    stronger question, that the run recorded the *shapes* it was given.
    """

    def test_every_declared_shape_is_present_in_the_fixture(self, driven):
        sites, _, _ = driven

        assert set(sites) == set(EXPECTED)

    def test_the_run_recorded_a_frame_for_a_generator_and_none_for_a_listcomp(
        self, driven
    ):
        """PEP 709, asserted rather than assumed — it is rule 3's whole
        premise, and a Python that stopped inlining would make rule 2
        reachable for a comprehension that cannot short-circuit."""
        sites, arcs, _ = driven
        generator = sites["single_line_zero"]
        inlined = sites["listcomp_zero"]

        assert (-generator.lineno, generator.lineno) in arcs
        assert (-inlined.lineno, inlined.lineno) not in arcs


class TestTheRulesAgainstTheRealTool:
    """Each shape, at a known iteration count."""

    @pytest.mark.parametrize("name", sorted(EXPECTED))
    def test_the_shape_is_classified_as_measured(self, name, driven):
        sites, arcs, siblings = driven
        turned, _ = _loop_turned(sites[name], arcs, siblings)

        assert turned is EXPECTED[name]

    def test_one_iteration_is_enough_to_leave_a_back_edge(self, driven):
        """The boundary, stated on its own because it is the one a
        detector keyed on *two* passes through the loop would get wrong
        while looking right on every other row here."""
        sites, arcs, siblings = driven
        one = sites["single_line_one"]

        assert (one.lineno, one.lineno) in arcs
        assert _loop_turned(one, arcs, siblings)[0] is True


class TestTheEntrysOwnRuleIsRefuted:
    """``SNAG-TEST-009`` rule 1 — *some arc runs backwards inside the
    ``lineno..end_lineno`` span* — read literally, and shown wrong."""

    def test_a_generator_that_never_turned_still_arcs_backwards_inside_its_span(
        self, driven
    ):
        sites, arcs, _ = driven
        empty = sites["multi_line_zero"]
        span = range(empty.lineno, (empty.end_lineno or empty.lineno) + 1)
        backwards = {
            (start, end)
            for start, end in arcs
            if start in span and end in span and end <= start
        }

        assert backwards, "the wider rule would have found nothing to be wrong about"
        assert (empty.generators[-1].iter.lineno, empty.lineno) in backwards


class TestTheRefusalIsForced:
    """The two undecidable shapes, asserted as an equality.

    A refusal is only honest if the evidence really is the same on both
    sides.  Asserting that the classification is ``None`` would pass
    against a detector that refuses everything of that shape for no
    reason; asserting that the arc sets are *identical* is the claim.
    """

    def test_the_turning_and_empty_spellings_leave_the_same_arcs(self, driven):
        sites, arcs, _ = driven
        empty = sites["element_on_first_line_zero"]
        turning = sites["element_on_first_line_two"]

        def within(node: ast.expr) -> set[tuple[int, int]]:
            span = range(node.lineno, (node.end_lineno or node.lineno) + 1)
            offset = node.lineno
            return {
                (start - offset, end - offset)
                for start, end in arcs
                if start in span and end in span
            }

        assert within(empty) == within(turning)

    def test_a_decidable_pair_does_not_leave_the_same_arcs(self, driven):
        """The control for the drive above.  Without it, an arc reader
        that returned the empty set for everything would satisfy the
        equality and read as proof of indistinguishability.
        """
        sites, arcs, _ = driven
        empty = sites["multi_line_zero"]
        turning = sites["multi_line_two"]

        def within(node: ast.expr) -> set[tuple[int, int]]:
            span = range(node.lineno, (node.end_lineno or node.lineno) + 1)
            offset = node.lineno
            return {
                (start - offset, end - offset)
                for start, end in arcs
                if start in span and end in span
            }

        assert within(empty) != within(turning)
