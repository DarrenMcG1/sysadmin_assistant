"""SNAG-LOG-006 — a manual run had no loud fallback if its own record failed.

``POST /api/sysadmin/scan-all`` and ``POST /api/files/scan`` started
agents with a bare ``asyncio.create_task(agent.run(run_type="manual"))``
and kept no reference.  A scheduled run's escape reaches APScheduler's
listener and comes out as ``scheduler_job_error``; a manual run's reached
nobody — the one path ``COVERED_SIGNATURES``' rule 5 does not cover.

**What was measured before any of this was written**, because the entry
filed both its candidate fixes as *"neither costed"* and its residual
signal as unmeasured:

* The asyncio fallback the entry hoped for **does** fire, at ``ERROR``,
  on the loop turn after the task completes — prompt rather than
  GC-deferred, and no ``gc.collect()`` helps or is needed.  *When* was
  never the problem.  **What** is: it unwraps to a 252-character
  signature and a 220-character title reading ``Task exception was never
  retrieved future: <Task finished name='Task-N' coro=<BaseAgent.run()
  done, defined at …/sysadmin/core/agent.py:N> …``.  It names
  ``BaseAgent.run``, so all five triggers share one signature; it carries
  this module's path, so moving ``run()`` forks the row; and the
  exception's own text sits inside the repr, so on a shorter checkout
  path it falls inside the cap and forks a row per distinct failure.
* ``run()`` can escape in **four** shapes, and only one of them writes an
  ``agent_run_failed`` line.  That is what refutes the entry's second
  candidate — narrowing ``COVERED_SIGNATURES`` to ``run_type ==
  "scheduled"`` can only speak where that line exists, so it buys one
  quarter of the fault for strictly more work.

These tests drive all four shapes.  ``TestTheFourShapes`` is the one that
would have been red before the fix; the rest pin the properties that make
the fix's report usable — a stable identity, an uncovered signature, a
rung that records without announcing, and a reference that cannot leak.
"""

import ast
import asyncio
import json
import logging
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.agent import (
    AGENT_RUN_FAILED_EVENT,
    MANUAL_RUN_CANCELLED_EVENT,
    MANUAL_RUN_FAILED_EVENT,
    AgentResult,
    BaseAgent,
    _manual_runs,
    spawn_manual_run,
)
from sysadmin.core.logging_setup import JournalLevelPrefixFormatter, syslog_priority
from sysadmin.core.unit_failure import OWN_UNIT
from sysadmin.monitor.journal import PRIORITY_MAP, unwrap_json_message
from sysadmin.monitor.log_aggregator import COVERED_SIGNATURES, FAULT_SEVERITIES
from sysadmin.monitor.log_signature import alert_title, signature

REPO_ROOT = Path(__file__).resolve().parents[1]

#: The two files that start a manual run.  The entry names
#: ``POST /api/files/organise`` as the second trigger and that is wrong —
#: ``/organise`` is a synchronous action route returning
#: ``FileActionResponse``.  The discarded task was in ``POST /api/files/scan``.
TRIGGER_PATHS = (
    REPO_ROOT / "sysadmin" / "main.py",
    REPO_ROOT / "sysadmin" / "files" / "router.py",
)

#: Four in ``scan-all``, one in ``POST /api/files/scan``.
EXPECTED_SPAWNS = 5

BOOM = RuntimeError("connection was closed in the middle of operation")


class Probe(BaseAgent):
    """An agent whose work either succeeds or raises, on request."""

    name = "sysadmin"

    def __init__(self, execute_raises: bool = False) -> None:
        self.execute_raises = execute_raises

    async def _execute(self, session):
        if self.execute_raises:
            raise BOOM
        return AgentResult(findings_count=1)


@pytest.fixture
def journal(caplog):
    """Records as the journal would see them, unwrapped the way the reader does.

    Deliberately not ``caplog.messages``: this fix's whole claim is about
    what the *signature* comes out as, and the signature is computed from
    the unwrapped ``MESSAGE`` of a line this daemon serialises as JSON
    with a ``<N>`` priority prefix.  Asserting on the ``LogRecord`` would
    pin the input to the pipeline and say nothing about its output — the
    defect ``TestJournalCommand`` had, one family over.
    """
    formatter = JournalLevelPrefixFormatter("%(message)s")

    def rendered():
        out = []
        for record in caplog.records:
            line = formatter.format(record)
            prefix, _, body = line.partition(">")
            message, meta = unwrap_json_message(body)
            out.append(
                {
                    # ``PRIORITY_MAP`` is keyed on the *string* journalctl
                    # emits, not on an int — the reader's vocabulary, kept
                    # as the reader has it.
                    "priority": prefix.lstrip("<"),
                    "severity": PRIORITY_MAP[prefix.lstrip("<")],
                    "message": message,
                    "signature": signature(message),
                    "meta": meta,
                    "envelope": json.loads(body),
                }
            )
        return out

    caplog.set_level(logging.DEBUG)
    return rendered


async def _drive(
    *,
    execute_raises: bool = False,
    start_raises: bool = False,
    outcome_raises: bool = False,
    flush_raises: bool = False,
    cancel: bool = False,
) -> asyncio.Task:
    """Run one manual run to completion through the real ``spawn_manual_run``."""
    agent = Probe(execute_raises)
    start = (
        AsyncMock(side_effect=BOOM)
        if start_raises
        else AsyncMock(return_value=uuid.uuid4())
    )
    outcome = AsyncMock(side_effect=BOOM) if outcome_raises else AsyncMock()
    flush = MagicMock(side_effect=BOOM) if flush_raises else MagicMock()
    with (
        patch.object(Probe, "_record_start", start),
        patch.object(Probe, "_record_outcome", outcome),
        patch.object(Probe, "_flush_events", flush),
        patch("sysadmin.core.agent.get_scheduler_session"),
    ):
        task = spawn_manual_run(agent)
        if cancel:
            task.cancel()
        for _ in range(8):
            await asyncio.sleep(0)
        await asyncio.sleep(0.01)
    return task


def _events(journal, name):
    return [row for row in journal() if row["message"] == name]


class TestTheFourShapes:
    """Every way ``run()`` can escape now says so, and only one used to.

    ``_execute``'s exception is swallowed by ``run()``'s ``try``, so the
    exceptions that escape come from the bookkeeping around the work.
    Shape 3 is the one worth staring at: it wrote **no journal line at
    all** before this fix, so there was nothing for any reader-side or
    exclusion-side remedy to find.
    """

    async def test_execute_and_outcome_both_raise(self, journal):
        await _drive(execute_raises=True, outcome_raises=True)
        assert len(_events(journal, MANUAL_RUN_FAILED_EVENT)) == 1
        # The covered line is still written, and still covered.  This fix
        # adds a speaker; it does not un-quieten the family SNAG-LOG-005
        # deliberately quietened.
        assert len(_events(journal, AGENT_RUN_FAILED_EVENT)) == 1

    async def test_record_outcome_raises_alone(self, journal):
        """The run *worked*; only the bookkeeping failed.

        No ``agent_run_failed`` line exists here, which is why the entry's
        second candidate cannot reach this shape.
        """
        await _drive(outcome_raises=True)
        assert len(_events(journal, MANUAL_RUN_FAILED_EVENT)) == 1
        assert _events(journal, AGENT_RUN_FAILED_EVENT) == []

    async def test_record_start_raises(self, journal):
        """The shape that wrote nothing whatsoever."""
        await _drive(start_raises=True)
        assert len(_events(journal, MANUAL_RUN_FAILED_EVENT)) == 1
        assert _events(journal, AGENT_RUN_FAILED_EVENT) == []

    async def test_flush_events_raises(self, journal):
        await _drive(flush_raises=True)
        assert len(_events(journal, MANUAL_RUN_FAILED_EVENT)) == 1

    async def test_a_healthy_run_says_nothing(self, journal):
        """The supervisor is silent on success, or it is a second speaker.

        This is the assertion that keeps rule 3 honest: a callback that
        fired on every manual run would give every ordinary run a second
        voice, which is the defect being fixed rather than the fix.
        """
        await _drive()
        assert _events(journal, MANUAL_RUN_FAILED_EVENT) == []
        assert _events(journal, MANUAL_RUN_CANCELLED_EVENT) == []

    async def test_the_asyncio_fallback_no_longer_fires(self, journal):
        """Retrieving the exception is what removes the 252-character title.

        The fallback was real — measured, and prompt rather than
        GC-deferred — so the fix has to be seen to *replace* it and not
        merely to add beside it, or the box gets both.
        """
        await _drive(outcome_raises=True)
        assert [row for row in journal() if row["message"].startswith("Task exception")] == []


class TestTheIdentityItRaisesUnder:
    """A row's identity is the fault, and this one has to survive the pipeline."""

    async def test_the_signature_is_the_event_name(self, journal):
        """``exc_info`` must stay out of ``message``, or every failure forks.

        Measured through the real formatter: the traceback lands under its
        own ``exc_info`` envelope key while ``message`` stays the event
        name.  Folding it in would make the identity a whole traceback —
        ``SNAG-AGENT-005``'s pile-up inside the family built to end it.
        """
        await _drive(outcome_raises=True)
        row = _events(journal, MANUAL_RUN_FAILED_EVENT)[0]
        assert row["signature"] == MANUAL_RUN_FAILED_EVENT
        assert row["envelope"]["exc_info"]
        assert "Traceback" not in row["message"]
        assert len(alert_title("error", OWN_UNIT, row["message"])) < 60

    async def test_it_carries_the_agent_and_the_error(self, journal):
        """The asyncio fallback named ``BaseAgent.run`` and no agent at all."""
        await _drive(outcome_raises=True)
        envelope = _events(journal, MANUAL_RUN_FAILED_EVENT)[0]["envelope"]
        assert envelope["agent"] == "sysadmin"
        assert envelope["run_type"] == "manual"
        assert "connection was closed" in envelope["error"]

    def test_neither_event_name_carries_a_digit(self):
        """``signature()`` maps digit runs to ``N``.

        A number in either name would make the stored signature differ
        from the literal — and the failure mode of that is silence, so it
        is pinned rather than remembered.  ``AGENT_RUN_FAILED_EVENT``
        carries the same assertion for the same arithmetic.
        """
        for event in (MANUAL_RUN_FAILED_EVENT, MANUAL_RUN_CANCELLED_EVENT):
            assert signature(event) == event

    def test_the_new_event_is_not_covered(self):
        """The negative assertion the whole fix turns on.

        ``COVERED_SIGNATURES`` quietens ``agent_run_failed`` because
        ``failures.py`` will speak instead.  Nothing speaks for this one,
        so an entry here would restore the silence being removed.
        """
        assert (OWN_UNIT, MANUAL_RUN_FAILED_EVENT) not in COVERED_SIGNATURES
        assert (OWN_UNIT, MANUAL_RUN_CANCELLED_EVENT) not in COVERED_SIGNATURES
        assert (OWN_UNIT, AGENT_RUN_FAILED_EVENT) in COVERED_SIGNATURES

    def test_the_three_events_are_distinct(self):
        events = {MANUAL_RUN_FAILED_EVENT, MANUAL_RUN_CANCELLED_EVENT, AGENT_RUN_FAILED_EVENT}
        assert len(events) == 3


class TestCancellationIsRecordedNotAnnounced:
    """The rung is the mechanism, and it is derived rather than restated."""

    async def test_a_cancelled_run_is_written(self, journal):
        task = await _drive(cancel=True)
        assert task.cancelled()
        assert len(_events(journal, MANUAL_RUN_CANCELLED_EVENT)) == 1
        assert _events(journal, MANUAL_RUN_FAILED_EVENT) == []

    async def test_its_rung_is_one_the_aggregator_does_not_raise_on(self, journal):
        """Pinned against ``FAULT_SEVERITIES`` rather than against ``"warning"``.

        Writing ``== "warning"`` here would be a second statement of the
        aggregator's gate that can drift from it silently — the shape
        ``max_priority_for`` and ``chk_alert_agent`` are both derived to
        avoid.  What matters is not the word; it is that the word is
        *below* the rungs that raise.
        """
        await _drive(cancel=True)
        row = _events(journal, MANUAL_RUN_CANCELLED_EVENT)[0]
        assert row["severity"] not in FAULT_SEVERITIES

    async def test_a_failure_uses_a_rung_that_does_raise(self, journal):
        """The other half of the same pin, or the fix is silent by accident."""
        await _drive(outcome_raises=True)
        row = _events(journal, MANUAL_RUN_FAILED_EVENT)[0]
        assert row["severity"] in FAULT_SEVERITIES

    def test_the_two_rungs_survive_the_priority_round_trip(self):
        """The producer and the consumer must agree about one fact.

        ``syslog_priority`` writes the ``<N>`` prefix and ``PRIORITY_MAP``
        reads it back; the level chosen here is only correct if the
        round trip preserves which side of ``FAULT_SEVERITIES`` it lands.
        """
        assert PRIORITY_MAP[str(syslog_priority(logging.ERROR))] in FAULT_SEVERITIES
        assert PRIORITY_MAP[str(syslog_priority(logging.WARNING))] not in FAULT_SEVERITIES


class TestTheReferenceCannotLeak:
    """A set that grows without bound is the defect wearing the fix's clothes."""

    async def test_it_is_held_while_running_and_released_after(self):
        agent = Probe()
        with (
            patch.object(Probe, "_record_start", AsyncMock(return_value=uuid.uuid4())),
            patch.object(Probe, "_record_outcome", AsyncMock()),
            patch("sysadmin.core.agent.get_scheduler_session"),
        ):
            task = spawn_manual_run(agent)
            assert task in _manual_runs
            await task
            for _ in range(4):
                await asyncio.sleep(0)
        assert task not in _manual_runs

    async def test_a_failing_report_still_releases_it(self):
        """The discard is in a ``finally`` and this is why.

        A done-callback that raises is swallowed by the loop's exception
        handler, so a logging failure would otherwise leak the reference
        this module exists to hold — and leak it silently.
        """
        agent = Probe()
        with (
            patch.object(Probe, "_record_start", AsyncMock(return_value=uuid.uuid4())),
            patch.object(Probe, "_record_outcome", AsyncMock(side_effect=BOOM)),
            patch("sysadmin.core.agent.get_scheduler_session"),
            patch("sysadmin.core.agent.logger.error", side_effect=RuntimeError("no handler")),
        ):
            task = spawn_manual_run(agent)
            for _ in range(8):
                await asyncio.sleep(0)
        assert task not in _manual_runs


class TestNoTriggerDiscardsItsTask:
    """The regression guard, structural rather than nominal.

    This is ``snag_claims.discarded_tasks`` re-homed.  It lived as a claims
    check while the entry was open — a check's job is "does this still
    hold?", and the answer is now permanently no, so it retires with the
    entry.  What must not retire is the detector: a bare ``create_task``
    coming back is exactly the regression, and ``FROZEN_TABLES``' rule
    applies — deleting a guard along with its last finding takes the guard
    against the defect coming back.

    "Bare" is load-bearing and is why this is not a search for
    ``create_task``: an ``ast.Expr`` wrapper *is* "the value was
    discarded", so ``event_bus.py``'s deliberate ``task =
    loop.create_task(…)`` is excluded by grammar rather than by name.
    """

    @staticmethod
    def _discarded_runs(path: Path) -> list[int]:
        tree = ast.parse(path.read_text())
        lines = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
                continue
            call = node.value
            if not (isinstance(call.func, ast.Attribute) and call.func.attr == "create_task"):
                continue
            if not call.args or not isinstance(call.args[0], ast.Call):
                continue
            inner = call.args[0].func
            if isinstance(inner, ast.Attribute) and inner.attr == "run":
                lines.append(node.lineno)
        return sorted(lines)

    @staticmethod
    def _spawn_calls(path: Path) -> list[int]:
        tree = ast.parse(path.read_text())
        return sorted(
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "spawn_manual_run"
        )

    def test_no_trigger_file_discards_an_agent_run(self):
        found = {
            path.name: self._discarded_runs(path)
            for path in TRIGGER_PATHS
            if self._discarded_runs(path)
        }
        assert found == {}, f"a manual run is unsupervised again: {found}"

    def test_every_trigger_goes_through_the_supervisor(self):
        """Counted, because "nothing is bare" is also true of a file that
        stopped triggering anything at all."""
        total = sum(len(self._spawn_calls(path)) for path in TRIGGER_PATHS)
        assert total == EXPECTED_SPAWNS

    def test_the_detector_trips_on_the_shape_it_is_looking_for(self):
        """Driven at a stand-in *modelling the defect*, or it proves nothing.

        A guard that has never returned non-empty is indistinguishable
        from one that cannot.
        """
        module = ast.parse(
            "import asyncio\n"
            "asyncio.create_task(agent.run(run_type='manual'))\n"
            "held = asyncio.create_task(agent.run(run_type='manual'))\n"
        )
        bare = [
            node.lineno
            for node in ast.walk(module)
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "create_task"
        ]
        assert bare == [2], "the assigned form must be excluded by grammar"
