"""SNAG-AGENT-014 — a run of an agent already running is declined.

``spawn_manual_run`` starts a run on the API loop and the scheduler
starts one with ``asyncio.run`` in a worker thread, and its
``max_instances: 1`` caps only its own jobs.  Two overlapping runs of one
agent both read the open alert set, both raised the same new fault, and
since migration 019 ``uq_alerts_open_agent_title`` failed the second.

These tests drive the overlap both ways it arrives, on one loop and
across two threads, and the two ways a run can end abnormally, because a
lock that outlives its run declines every later run for good.
"""

import asyncio
import logging
import threading
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.agent import (
    AGENT_RUN_DECLINED_EVENT,
    AgentResult,
    BaseAgent,
    _run_locks,
)


@asynccontextmanager
async def _session():
    session = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    yield session


class _Agent(BaseAgent):
    """An agent whose ``_execute`` blocks until told to finish."""

    name = "sysadmin"

    def __init__(self, boom: Exception | None = None) -> None:
        self.boom = boom
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.executions = 0

    async def _execute(self, session):
        self.executions += 1
        self.started.set()
        await self.release.wait()
        if self.boom:
            raise self.boom
        return AgentResult()


async def _bounded(run):
    """Await something a regression would leave waiting for ever.

    Without the bound, a regression hangs the suite rather than failing
    it: a run that is not declined waits on ``release``, and a run
    declined by a lock left held never sets ``started``.
    """
    return await asyncio.wait_for(run, timeout=5)


@pytest.fixture(autouse=True)
def _fake_sessions():
    with patch("sysadmin.core.agent.get_scheduler_session", _session):
        yield


@pytest.fixture(autouse=True)
def _no_lock_left_over():
    yield
    # Popped before the assert, so a lock one test leaves held fails that
    # test and does not decline every run in the tests after it.
    lock = _run_locks.pop(_Agent.name, None)
    assert lock is None or not lock.locked()


@pytest.mark.asyncio
class TestAnOverlappingRunIsDeclined:
    async def test_a_second_run_on_the_same_loop_returns_none(self, caplog):
        agent = _Agent()
        first = asyncio.create_task(agent.run("scheduled"))
        await _bounded(agent.started.wait())

        with caplog.at_level(logging.INFO, logger="sysadmin.core.agent"):
            second = await _bounded(agent.run("manual"))

        assert second is None
        assert agent.executions == 1
        declined = [r for r in caplog.records if r.getMessage() == AGENT_RUN_DECLINED_EVENT]
        assert [(r.agent, r.run_type) for r in declined] == [("sysadmin", "manual")]

        agent.release.set()
        assert isinstance(await first, AgentResult)

    async def test_a_declined_run_writes_no_agent_runs_row(self):
        agent = _Agent()
        first = asyncio.create_task(agent.run("scheduled"))
        await _bounded(agent.started.wait())

        with patch.object(agent, "_record_start", AsyncMock()) as record_start:
            await _bounded(agent.run("manual"))

        record_start.assert_not_awaited()
        agent.release.set()
        await first

    async def test_a_run_in_another_thread_is_declined(self):
        """The real overlap: a scheduled run is ``asyncio.run`` in a worker thread."""
        agent = _Agent()
        first = asyncio.create_task(agent.run("manual"))
        await _bounded(agent.started.wait())

        # A fresh agent instance on purpose: the lock is keyed by name,
        # which is the key the unique index refuses on.
        other = _Agent()
        other.release.set()
        result: list[AgentResult | None] = []
        thread = threading.Thread(target=lambda: result.append(asyncio.run(other.run())))
        thread.start()
        await asyncio.to_thread(thread.join, 5)

        assert result == [None]
        assert other.executions == 0
        agent.release.set()
        await first

    async def test_the_next_run_after_one_finishes_runs(self):
        agent = _Agent()
        agent.release.set()

        assert isinstance(await agent.run(), AgentResult)
        assert isinstance(await agent.run(), AgentResult)
        assert agent.executions == 2

    async def test_another_agent_is_not_held_up(self):
        agent = _Agent()
        first = asyncio.create_task(agent.run())
        await _bounded(agent.started.wait())

        other = _Agent()
        other.name = "log_aggregator"
        other.release.set()

        assert isinstance(await other.run(), AgentResult)
        agent.release.set()
        await first


@pytest.mark.asyncio
class TestTheLockIsReleased:
    async def test_after_a_failed_run(self):
        agent = _Agent(boom=RuntimeError("uq_alerts_open_agent_title"))
        agent.release.set()

        assert await agent.run() is None
        assert not _run_locks[agent.name].locked()

    async def test_after_a_cancelled_run(self):
        agent = _Agent()
        task = asyncio.create_task(agent.run("manual"))
        await _bounded(agent.started.wait())

        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert not _run_locks[agent.name].locked()

    async def test_after_the_bookkeeping_raises(self):
        """``_record_start`` failing escapes ``run``; the lock must not go with it."""
        agent = _Agent()
        with (
            patch.object(agent, "_record_start", AsyncMock(side_effect=OSError("db down"))),
            pytest.raises(OSError),
        ):
            await agent.run()

        assert not _run_locks[agent.name].locked()
