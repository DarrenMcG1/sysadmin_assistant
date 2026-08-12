"""SNAG-AGENT-003 — the run record must outlive the run it records.

``BaseAgent.run`` used to open one session, insert the ``running`` row,
flush it (which *starts* a transaction) and then hand that same session
to ``_execute``.  This host sets ``idle_in_transaction_session_timeout``
to one minute, so any agent whose work ran longer had its backend
terminated by PostgreSQL, and every write of that run was lost —
including the row that would have said so.

Measured on 2026-08-11: the file organiser scanned for 117.71 s, found
25,317 issues, logged ``agent_run_completed``, and then died on
``UPDATE sysadmin.agent_runs SET status='completed'`` with ``connection
is closed``.  ``agent_runs`` held one ``file_organiser`` row afterwards,
dated 2026-08-06 — the one run in the agent's life that finished inside
the timeout, at 29.63 s.  Five days of silent failure was indistinguishable
from an agent that had never been scheduled.

**What these tests can and cannot show.** There is no live database
here, so the timeout itself cannot be reproduced.  What is asserted is
the structural property that makes it survivable: the bookkeeping runs
in transactions of its own, so no amount of time spent inside
``_execute`` can be spent holding one open.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.core.agent import AgentResult, BaseAgent


class _Recorder:
    """A session factory handing out a fresh mock per ``async with``."""

    def __init__(self) -> None:
        self.sessions: list[MagicMock] = []
        self.timeline: list[str] = []

    @asynccontextmanager
    async def factory(self):
        session = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        self.sessions.append(session)
        self.timeline.append(f"open:{len(self.sessions)}")
        yield session
        self.timeline.append(f"commit:{len(self.sessions)}")

    @property
    def statements(self) -> list[str]:
        """Every statement passed to ``session.execute``, compiled."""
        out = []
        for session in self.sessions:
            for call in session.execute.await_args_list:
                out.append(
                    str(call.args[0].compile(dialect=postgresql.dialect()))
                )
        return out


class _Agent(BaseAgent):
    name = "file_organiser"

    def __init__(self, boom: Exception | None = None) -> None:
        self.boom = boom
        self.session_seen: MagicMock | None = None

    async def _execute(self, session):
        self.session_seen = session
        if self.boom:
            raise self.boom
        return AgentResult(findings_count=25317, details={"reclaimable_mb": 34844})


@pytest.fixture
def recorder():
    return _Recorder()


async def _run(agent: _Agent, recorder: _Recorder):
    with patch("sysadmin.core.agent.get_scheduler_session", recorder.factory):
        return await agent.run()


@pytest.mark.asyncio
class TestThreeTransactions:
    async def test_the_running_row_commits_before_execute_is_called(self, recorder):
        agent = _Agent()

        await _run(agent, recorder)

        # open/commit of the run record, *then* the work's session.
        assert recorder.timeline[:3] == ["open:1", "commit:1", "open:2"]

    async def test_execute_gets_a_session_of_its_own(self, recorder):
        """The whole fix: no transaction is open when _execute starts work."""
        agent = _Agent()

        await _run(agent, recorder)

        assert len(recorder.sessions) == 3
        assert agent.session_seen is recorder.sessions[1]
        assert agent.session_seen is not recorder.sessions[0]
        assert agent.session_seen is not recorder.sessions[2]

    async def test_nothing_is_flushed_into_the_work_session_first(self, recorder):
        """A flush before handing over is what opened the transaction."""
        agent = _Agent()

        await _run(agent, recorder)

        recorder.sessions[1].flush.assert_not_awaited()


@pytest.mark.asyncio
class TestAFailedRunIsStillRecorded:
    """The half that made five days of failure look like five days of nothing."""

    async def test_the_outcome_is_written_from_a_different_session(self, recorder):
        agent = _Agent(boom=RuntimeError("connection is closed"))

        await _run(agent, recorder)

        # The session that died is sessions[1]; the failure is recorded
        # through sessions[2], which is the only reason it can be recorded.
        assert len(recorder.sessions) == 3
        recorder.sessions[2].execute.assert_awaited_once()

    async def test_the_row_is_updated_to_failed(self, recorder):
        agent = _Agent(boom=RuntimeError("connection is closed"))

        await _run(agent, recorder)

        sql = recorder.statements[-1]
        assert "UPDATE sysadmin.agent_runs" in sql
        assert "WHERE sysadmin.agent_runs.id" in sql

    async def test_run_returns_none_on_failure(self, recorder):
        assert await _run(_Agent(boom=RuntimeError("boom")), recorder) is None

    async def test_run_returns_the_result_on_success(self, recorder):
        result = await _run(_Agent(), recorder)

        assert result is not None
        assert result.findings_count == 25317


@pytest.mark.asyncio
class TestTheIdSurvivesTheGap:
    async def test_the_update_targets_the_row_the_first_session_inserted(
        self, recorder
    ):
        """Client-side ``default=uuid.uuid4`` is what makes three
        transactions free: the id exists before the INSERT is sent, so
        the outcome can be written without reading the row back."""
        agent = _Agent()

        await _run(agent, recorder)

        inserted = recorder.sessions[0].add.call_args.args[0]
        bound = recorder.sessions[2].execute.await_args.args[0].compile(
            dialect=postgresql.dialect()
        ).params

        assert inserted.id is not None
        assert inserted.id in bound.values()
