"""Tests for the standalone organiser entry point.

The point of the entry point is that the scan does not need the
monitoring daemon, so these check the two things that would quietly
break that: an exit code that reflects the run, and a database engine
disposed whatever happens.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.core.agent import AgentResult
from sysadmin.projects import cli

MOD = "sysadmin.projects.cli"


@pytest.fixture
def wiring():
    """Patch everything outside the entry point's own logic."""
    with (
        patch(f"{MOD}.create_engine_and_session", new_callable=AsyncMock),
        patch(f"{MOD}.dispose_engine", new_callable=AsyncMock) as dispose,
        patch(f"{MOD}.configure_logging"),
        patch(f"{MOD}.get_config"),
    ):
        yield dispose


@pytest.mark.asyncio
async def test_a_successful_scan_exits_zero(wiring):
    with (
        patch(f"{MOD}.verify_connection", new_callable=AsyncMock, return_value=True),
        patch.object(
            cli.ProjectOrganiserAgent, "run", new_callable=AsyncMock,
            return_value=AgentResult(findings_count=25, details={"undeclared": 9}),
        ),
    ):
        assert await cli.run_scan() == 0


@pytest.mark.asyncio
async def test_a_failed_scan_exits_nonzero(wiring):
    """A timer whose unit always exits 0 tells systemctl status nothing."""
    with (
        patch(f"{MOD}.verify_connection", new_callable=AsyncMock, return_value=True),
        patch.object(
            cli.ProjectOrganiserAgent, "run", new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        assert await cli.run_scan() == 1


@pytest.mark.asyncio
async def test_no_database_aborts_rather_than_scanning(wiring):
    with (
        patch(f"{MOD}.verify_connection", new_callable=AsyncMock, return_value=False),
        patch.object(cli.ProjectOrganiserAgent, "run", new_callable=AsyncMock) as run,
    ):
        assert await cli.run_scan() == 1
    run.assert_not_called()


@pytest.mark.asyncio
async def test_the_engine_is_disposed_even_when_the_scan_raises(wiring):
    """A oneshot that leaks a connection pool leaks one per day."""
    with (
        patch(f"{MOD}.verify_connection", new_callable=AsyncMock, return_value=True),
        patch.object(
            cli.ProjectOrganiserAgent, "run", new_callable=AsyncMock,
            side_effect=RuntimeError("git exploded"),
        ),
        pytest.raises(RuntimeError),
    ):
        await cli.run_scan()
    wiring.assert_awaited_once()


@pytest.mark.asyncio
async def test_the_engine_is_disposed_when_the_database_is_absent(wiring):
    with patch(f"{MOD}.verify_connection", new_callable=AsyncMock, return_value=False):
        await cli.run_scan()
    wiring.assert_awaited_once()


def test_the_agent_result_reaches_the_caller():
    """BaseAgent.run returns its result so a one-shot invocation has
    something to turn into an exit code, rather than re-reading the row
    it just wrote."""
    import inspect

    from sysadmin.core.agent import BaseAgent

    assert "AgentResult" in str(inspect.signature(BaseAgent.run).return_annotation)
