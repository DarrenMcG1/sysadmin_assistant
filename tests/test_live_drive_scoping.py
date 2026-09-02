"""No live drive selects processes across the whole box.

``SNAG-TEST-004``, closed 2026-09-02.  ``tests/test_notify_guard_live.py``
started its **own** ``dbus-daemon`` per test and then asked two questions
about *the machine*: the teardown ran ``pkill -f plasma_waitforname`` and
:meth:`test_asking_does_not_start_the_waiter_that_calling_starts` counted
with ``pgrep -c -f``.  Both reported a box-wide answer as an answer about
that fixture, and the first was measured to turn a **concurrent session's
run** red — three kills landing inside another run's blocking call make
the bus stop re-activating the waiter, the activation fails, and the
pending ``notify-send`` returns, which is ``assert not returned`` failing.

Both operations are scoped now (``2502dbc``).  This is the guard that
keeps them scoped, and it is deliberately wider than the entry: the
hazard belongs to *starting a private resource and then selecting by a
pattern the box shares*, which every live drive is in a position to do
and two of them start buses today.  ``FROZEN_TABLES``' rule — the
detector outlives the finding.

**The selector is the defect, never the read.**  :func:`_waiters_under`
in the fixed file still lists **every** process on the box
(``ps -eo pid=,ppid=,args=``) and is correct, because it then selects by
ppid chain: the waiter it kills is a descendant of this fixture's own
daemon.  ``kill <pid>`` is likewise a scoped operation whatever the box
is doing.  What cannot be scoped is a *pattern* — ``pkill``, ``pgrep``,
``killall`` and ``pidof`` choose their targets from the whole process
table by name, so a concurrent session's copy of the same program is
indistinguishable from your own.  The detector therefore keys on the
verb and not on the noun.

**Prose is not read, and that is measured rather than tidy.**  A text
sweep for these words is not a weaker version of this walk, it is the
**inverse** of it.  Measured 2026-09-02 against the two real revisions of
``test_notify_guard_live.py``: the module docstring at ``ec54ab8`` — the
file with all three unscoped calls in it — mentions neither ``pkill`` nor
``pgrep``, while the fixed file at ``2502dbc`` mentions **both**, because
the fix explains itself.  So a grep reports the file that is right and
passes the file that is wrong.  Comments never reach the AST at all and
docstrings are :class:`ast.Constant` at statement level, so both fall out
by construction here rather than by an exclusion list somebody maintains.

**What it cannot see, stated rather than implied.**  A selector reached
through a variable holding a string, a name assembled at runtime, or a
shell pipeline built by string formatting all evade this walk.  It is the
shape ``test_schema_guard.py`` uses to keep ``upgrade`` out of
``check-migrations.sh``: satisfiable by a determined author, and that is
not what it is for — the default path, writing a third bus-starting drive
and reaching for ``pkill`` because it is the obvious tool, fails instead
of shipping green and turning a peer red.
"""

from __future__ import annotations

import ast
import os
import pathlib
import subprocess

import pytest

from tests.test_live_drive_premises import LIVE_DRIVES

#: This file, which must hold the spellings it hunts for in order to hunt
#: them — and is duly **reported by its own walk**, which was not the
#: first draft's expectation and is the more interesting result.  The hits
#: are not the stand-in sources: those are strings, and a string is prose.
#: They are the *expected values* — ``== ["pkill"]`` is a list literal
#: whose first element is a selector, which is the shape rule 1 reads as
#: argv, because an expectation and an invocation are written identically.
#: That is the mirror of the prose problem this detector was built around,
#: so it is recorded rather than worked around: the file stays outside
#: :data:`LIVE_DRIVES` by name — the glob is ``test_*_live.py`` — and
#: :meth:`TestTheDetectorCanBeSeenToFail.test_the_detector_sees_its_owner`
#: drives the walk here so the exclusion is proven necessary rather than
#: assumed.  ``test_live_drive_premises.py``'s ``OWNER`` for the same
#: reason, one rule over.
OWNER = pathlib.Path(__file__).resolve()

#: Commands that choose their targets by matching against every process on
#: the box.  ``kill`` is absent on purpose: it takes a pid, so it is scoped
#: by the thing it is given rather than by where it is called from.
SELECTORS = frozenset({"pkill", "pgrep", "killall", "pidof"})

#: Callables whose string argument is a command line rather than prose.
#: The list-literal form needs no such gate — a list whose first element is
#: ``"pkill"`` is argv by shape — but a bare string is only a command when
#: something runs it, and a message that happens to open with the word
#: would otherwise be reported.
_RUNNERS = frozenset(
    {"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}
)


def _head(token: str) -> str:
    """The command word a string begins with, basename-resolved.

    ``/usr/bin/pkill -f x`` and ``pkill -f x`` are one invocation, so the
    path is stripped; a caller reaching for the absolute path is not
    reaching for a different program.
    """
    first = token.strip().split(None, 1)[0] if token.strip() else ""
    return os.path.basename(first)


def _callee(node: ast.Call) -> str:
    """The trailing name of the thing being called, or ``""``."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def box_wide_selectors(source: str) -> list[tuple[int, str]]:
    """Every box-wide process selector *source* invokes, as (line, command).

    Two shapes, because both are how a command gets run in this suite:

    1. A list or tuple literal whose first element is a selector — argv,
       and reported wherever it appears, since assigning it to a variable
       first is a spelling and not a difference.
    2. A string argument to a runner (:data:`_RUNNERS`) whose first word is
       a selector — the ``shell=True`` form.

    Nothing else is read.  A docstring, a comment, a message and a
    variable name may all say ``pkill`` and none of them runs one.
    """
    tree = ast.parse(source)
    found: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            first = node.elts[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                if (name := _head(first.value)) in SELECTORS:
                    found.append((node.lineno, name))
        elif isinstance(node, ast.Call) and _callee(node) in _RUNNERS:
            for arg in [*node.args, *(kw.value for kw in node.keywords)]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if (name := _head(arg.value)) in SELECTORS:
                        found.append((arg.lineno, name))

    return sorted(set(found))


def _selectors_in(path: pathlib.Path) -> list[tuple[int, str]]:
    return box_wide_selectors(path.read_text(encoding="utf-8"))


#: The revision of ``test_notify_guard_live.py`` carrying all three
#: unscoped calls — the real specimen rather than a reconstruction of one,
#: because a synthetic stand-in models the defect somebody remembers and
#: this file models the defect that shipped.
PRE_FIX_COMMIT = "ec54ab8"
PRE_FIX_PATH = "tests/test_notify_guard_live.py"


def _pre_fix_source() -> str | None:
    """The pre-fix file out of git, or ``None`` where history cannot reach it.

    A shallow checkout — which is what CI does by default — has no such
    object, and that is reported as a skip rather than as a pass: a
    detector nobody could drive is not a detector that saw nothing.
    """
    done = subprocess.run(
        ["git", "show", f"{PRE_FIX_COMMIT}:{PRE_FIX_PATH}"],
        capture_output=True,
        text=True,
        cwd=OWNER.parents[1],
        check=False,
    )
    return done.stdout if done.returncode == 0 and done.stdout else None


class TestNoLiveDriveAsksTheBoxAQuestion:
    """The sweep, and the two things that stop it being vacuous."""

    def test_the_population_is_real(self):
        """A glob that matched nothing would pass the sweep in silence."""
        assert len(LIVE_DRIVES) >= 2, LIVE_DRIVES

    def test_no_live_drive_selects_processes_box_wide(self):
        offenders = {
            path.name: hits for path in LIVE_DRIVES if (hits := _selectors_in(path))
        }

        assert not offenders, (
            f"{offenders} — these select processes by a pattern the whole box "
            "shares, so a concurrent session's copy of the same program is "
            "indistinguishable from this test's own. Scope the operation to "
            "the resource this test started (SNAG-TEST-004)"
        )

    def test_the_repaired_file_would_still_trip_a_text_sweep(self):
        """The measurement that decided the detector's shape.

        The fixed file explains itself, so it names both selectors in
        prose; the broken one named neither.  A ``grep`` is therefore not
        a coarser version of this walk but the inverse of it, and this
        pins the fact rather than leaving it in a docstring — if the
        explanation is ever removed, the argument for reading only argv
        loses its evidence and should be re-derived.
        """
        guarded = next(p for p in LIVE_DRIVES if p.name == "test_notify_guard_live.py")
        prose = ast.get_docstring(ast.parse(guarded.read_text(encoding="utf-8"))) or ""

        assert "pkill" in prose and "pgrep" in prose, (
            "the fix no longer explains itself, so the evidence that a text "
            "sweep is inverted rather than merely coarser has gone with it"
        )
        assert not _selectors_in(guarded), (
            "the guarded file invokes a selector again — the sweep above is "
            "the finding; this test only loses its second half"
        )


class TestTheDetectorCanBeSeenToFail:
    """A sweep over a clean tree reports nothing whether or not it works."""

    @staticmethod
    def _found(source: str) -> list[str]:
        return [name for _, name in box_wide_selectors(source)]

    def test_the_real_pre_fix_file_is_reported(self):
        source = _pre_fix_source()
        if source is None:
            pytest.skip(
                f"{PRE_FIX_COMMIT} is unreachable — a shallow checkout cannot "
                "produce the specimen, and a detector nobody drove saw nothing"
            )

        assert box_wide_selectors(source) == [
            (138, "pkill"),
            (372, "pgrep"),
            (383, "pgrep"),
        ], "the specimen no longer carries the three calls the entry measured"

    def test_an_argv_list_is_reported(self):
        assert self._found(
            'subprocess.run(["pkill", "-f", "waiter"], check=False)\n'
        ) == ["pkill"]

    def test_argv_held_in_a_variable_is_still_argv(self):
        """Naming the list first is a spelling, not a difference."""
        assert self._found('cmd = ["pgrep", "-c", "-f", "waiter"]\nrun(cmd)\n') == [
            "pgrep"
        ]

    def test_an_absolute_path_is_the_same_program(self):
        assert self._found('subprocess.run(["/usr/bin/killall", "waiter"])\n') == [
            "killall"
        ]

    def test_a_shell_string_given_to_a_runner_is_reported(self):
        assert self._found(
            'subprocess.run("pkill -f waiter", shell=True)\n'
        ) == ["pkill"]

    def test_a_selector_named_only_in_prose_is_not_reported(self):
        """The exclusion the shipped file depends on."""
        assert not self._found(
            '"""This used to run a global pkill and count with pgrep."""\n'
            "# pkill -f waiter\n"
            'MESSAGE = "pkill was removed in SNAG-TEST-004"\n'
        )

    def test_killing_a_known_pid_is_not_reported(self):
        """``kill`` is scoped by its argument wherever it is called."""
        assert not self._found('subprocess.run(["kill", waiter], check=False)\n')

    def test_reading_the_whole_process_table_is_not_reported(self):
        """The fix's own instrument. The selection is what is judged."""
        assert not self._found(
            'subprocess.run(["ps", "-eo", "pid=,ppid=,args="], check=False)\n'
        )

    def test_the_detector_sees_its_owner(self):
        """The exclusion, proven necessary rather than granted.

        :data:`SELECTORS` is a set of bare constants and costs nothing;
        what this file cannot write without being reported is an
        *assertion* — ``== ["pkill"]`` has the shape of argv, since an
        expectation and an invocation are spelled the same way.  So the
        walk must report its owner, and the owner must stay out of
        :data:`LIVE_DRIVES`.  A silent run here would mean rule 1 had
        stopped reading list literals, which is most of the detector.
        """
        found = _selectors_in(OWNER)

        assert found, (
            "the detector no longer reports its own expectation lists, so "
            "rule 1 has stopped reading list literals"
        )
        assert OWNER not in LIVE_DRIVES
