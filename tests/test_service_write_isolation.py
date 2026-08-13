"""Per-service write isolation (SNAG-DB-001, gap 2).

``SysAdminAgent._execute`` used to ``session.add`` all nineteen
services' health rows into one session and commit once.  On 2026-08-08
``venture-chat-large`` recorded ``skipped`` — a value migration 009 was
meant to permit and had never been applied — and the
``CheckViolationError`` aborted the whole transaction.  **Zero rows
reached ``service_health`` for 39 hours**: one deliberately-unmonitored
service cost the other eighteen their check.

The fake session below models the part that made this hard to see:
``session.add`` never talks to the database, so a rejected row surfaces
at **flush** time.  Leaving a ``begin_nested()`` block flushes, which is
the whole reason a savepoint fixes this — rows added inside one only
reach ``committed_rows`` if that block exits cleanly, and a bad row
raises there rather than at the end of the run.
"""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError

from sysadmin.monitor.services import ServiceEntry


class _Savepoint:
    """``session.begin_nested()`` — rows land only if the block exits clean."""

    def __init__(self, session: "FakeSession") -> None:
        self.session = session
        self.rows: list = []

    async def __aenter__(self) -> "_Savepoint":
        self.session._current = self.rows
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        self.session._current = None
        if exc_type is not None:
            self.session.rolled_back.append(list(self.rows))
            return False
        # Exiting flushes. A row whose service is programmed to fail and
        # whose status is not the known-good fallback is rejected here —
        # modelling chk_health_status refusing an un-migrated value.
        bad = [
            r for r in self.rows
            if getattr(r, "service_name", None) in self.session.fail_services
            and getattr(r, "status", None) != "error"
        ]
        if bad:
            self.session.rolled_back.append(list(self.rows))
            raise IntegrityError(
                "INSERT INTO service_health ...",
                {},
                Exception('violates check constraint "chk_health_status"'),
            )
        self.session.committed_rows.extend(self.rows)
        return False


class FakeSession:
    """Enough of ``AsyncSession`` to exercise the savepoint loop."""

    def __init__(self, fail_services: set[str] | None = None) -> None:
        self.fail_services = set(fail_services or ())
        self.committed_rows: list = []
        self.rolled_back: list[list] = []
        self._current: list | None = None
        self.execute = AsyncMock()
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    def add(self, obj) -> None:
        if self._current is None:
            self.committed_rows.append(obj)
        else:
            self._current.append(obj)

    def begin_nested(self) -> _Savepoint:
        return _Savepoint(self)


def _svc(name: str) -> ServiceEntry:
    return ServiceEntry(name=name, kind="http", url=f"http://localhost/{name}")


def _health_rows(session: FakeSession) -> dict[str, str]:
    """``service_name -> status`` for every row that survived."""
    return {
        r.service_name: r.status
        for r in session.committed_rows
        if hasattr(r, "service_name")
    }


@pytest.fixture
def agent():
    from sysadmin.monitor.agent import SysAdminAgent

    return SysAdminAgent()


def _drive(agent, services, statuses, mock_config):
    """Patch everything ``_execute`` needs that is not the service loop."""
    registry = MagicMock()
    registry.services = services

    async def check(svc):
        return statuses[svc.name], 12, {}

    scoped = MagicMock()
    scoped.return_value.__aenter__ = AsyncMock(return_value=None)
    scoped.return_value.__aexit__ = AsyncMock(return_value=False)

    snapshot = MagicMock(spec=[])  # no service_name — not a health row

    return (
        patch("sysadmin.monitor.agent.get_config", return_value=mock_config),
        patch("sysadmin.monitor.agent.get_services", return_value=registry),
        patch.object(agent, "_check_service", side_effect=check),
        patch.object(agent._http, "scoped", scoped),
        patch.object(agent, "_take_resource_snapshot",
                     new_callable=AsyncMock, return_value=snapshot),
        patch.object(agent, "_load_metric_history",
                     new_callable=AsyncMock, return_value={}),
        patch.object(agent, "_check_thresholds",
                     new_callable=AsyncMock, return_value=0),
        patch.object(agent, "_check_anomalies",
                     new_callable=AsyncMock, return_value=0),
        patch.object(agent, "_check_agent_health",
                     new_callable=AsyncMock, return_value=0),
        patch.object(agent, "_check_collation",
                     new_callable=AsyncMock, return_value=0),
        patch.object(agent, "_resolve_recovered",
                     new_callable=AsyncMock, return_value=0),
        patch.object(agent, "raise_alert", new_callable=AsyncMock),
    )


def _enter(stack: ExitStack, patches: tuple) -> None:
    """Enter every patch in ``patches`` on ``stack``.

    ``_drive`` returns a variable-length tuple of context managers, which
    a plain ``with`` cannot unpack — ExitStack is the shape that takes a
    list.
    """
    for p in patches:
        stack.enter_context(p)


class TestOneBadRowDoesNotCostTheOthers:
    @pytest.mark.asyncio
    async def test_the_other_services_still_get_their_row(self, agent, mock_config):
        """The 39-hour blackout, reduced to one bad tile."""
        services = [_svc("alpha"), _svc("poison"), _svc("omega")]
        statuses = {"alpha": "ok", "poison": "skipped", "omega": "ok"}
        session = FakeSession(fail_services={"poison"})

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, statuses, mock_config))
            result = await agent._execute(session)

        rows = _health_rows(session)
        assert rows["alpha"] == "ok"
        assert rows["omega"] == "ok"
        assert result.findings_count == 3

    @pytest.mark.asyncio
    async def test_the_rejected_service_is_recorded_as_error(
        self, agent, mock_config
    ):
        """Absence of a row is what made this invisible for 39 hours."""
        services = [_svc("alpha"), _svc("poison")]
        statuses = {"alpha": "ok", "poison": "skipped"}
        session = FakeSession(fail_services={"poison"})

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, statuses, mock_config))
            await agent._execute(session)

        rows = _health_rows(session)
        assert rows["poison"] == "error"
        recorded = next(
            r for r in session.committed_rows
            if getattr(r, "service_name", None) == "poison"
        )
        assert recorded.details["source"] == "write_isolation"
        assert recorded.details["attempted_status"] == "skipped"
        assert "chk_health_status" in recorded.details["error"]

    @pytest.mark.asyncio
    async def test_the_failure_is_named_in_the_run_details(
        self, agent, mock_config
    ):
        """Which service could not be written decides whether it matters."""
        services = [_svc("alpha"), _svc("poison")]
        statuses = {"alpha": "ok", "poison": "skipped"}
        session = FakeSession(fail_services={"poison"})

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, statuses, mock_config))
            result = await agent._execute(session)

        assert result.details["write_failures"] == ["poison"]

    @pytest.mark.asyncio
    async def test_a_clean_run_reports_an_empty_list_not_a_missing_key(
        self, agent, mock_config
    ):
        """``{}`` would read as "the isolation did not run"."""
        services = [_svc("alpha")]
        session = FakeSession()

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, {"alpha": "ok"}, mock_config))
            result = await agent._execute(session)

        assert result.details["write_failures"] == []

    @pytest.mark.asyncio
    async def test_the_failed_service_is_protected_from_the_resolve(
        self, agent, mock_config
    ):
        """Nothing was recorded, so its state is unknown.

        ``_resolve_recovered`` closes open alerts for services this run
        did not measure as unhealthy — resolving on an unknown state
        announces a recovery nobody observed, the rule that module
        already encodes for ``error``.
        """
        services = [_svc("alpha"), _svc("poison")]
        statuses = {"alpha": "ok", "poison": "ok"}
        session = FakeSession(fail_services={"poison"})

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, statuses, mock_config))
            await agent._execute(session)
            unhealthy = agent._resolve_recovered.await_args.args[1]

        assert "poison" in unhealthy, (
            "a service whose write failed was measured 'ok' but not "
            "recorded — its open alerts must not be resolved"
        )

    @pytest.mark.asyncio
    async def test_no_status_change_event_for_a_row_that_rolled_back(
        self, agent, mock_config
    ):
        """The event would announce a transition the database never saw."""
        services = [_svc("poison")]
        session = FakeSession(fail_services={"poison"})
        # `run()` initialises this before calling `_execute`; driving
        # `_execute` directly skips that, and `None` is not the absence
        # of events, it is the absence of a buffer.
        agent._pending_events = []

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, {"poison": "critical"}, mock_config))
            await agent._execute(session)

        assert agent._pending_events == []
        assert "poison" not in agent._last_status


class TestSavepointMechanics:
    @pytest.mark.asyncio
    async def test_each_service_gets_its_own_savepoint(self, agent, mock_config):
        """Grouping them would restore the all-or-nothing behaviour."""
        services = [_svc("a"), _svc("b"), _svc("c")]
        statuses = {"a": "ok", "b": "ok", "c": "ok"}
        session = FakeSession()
        session.begin_nested = MagicMock(wraps=session.begin_nested)

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, statuses, mock_config))
            await agent._execute(session)

        assert session.begin_nested.call_count == 3

    @pytest.mark.asyncio
    async def test_a_failure_costs_exactly_two_savepoints(
        self, agent, mock_config
    ):
        """The rolled-back one, then the one recording that it happened."""
        services = [_svc("poison")]
        session = FakeSession(fail_services={"poison"})
        session.begin_nested = MagicMock(wraps=session.begin_nested)

        with ExitStack() as stack:
            _enter(stack, _drive(agent, services, {"poison": "skipped"}, mock_config))
            await agent._execute(session)

        assert session.begin_nested.call_count == 2
        assert len(session.rolled_back) == 1
