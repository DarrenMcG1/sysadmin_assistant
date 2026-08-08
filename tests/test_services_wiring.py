"""Tests for the behaviour services.yaml changed when it was wired in.

Every case here is a delta flagged before the wiring landed: the unit
assertion added to http checks, the timer inspection, the skipped status,
and the log-source de-duplication.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.agent import SysAdminAgent, _timer_facts
from sysadmin.monitor.services import SKIPPED, ServiceEntry
from sysadmin.monitor.systemd import UserBusUnavailableError

_UNIT_STATUS = "sysadmin.monitor.agent.get_unit_status"


def http_svc(**overrides) -> ServiceEntry:
    base = {
        "name": "api",
        "kind": "http",
        "url": "http://localhost:9/health",
        "systemd": {"unit": "api.service"},
    }
    return ServiceEntry.model_validate(base | overrides)


@pytest.fixture
def agent():
    return SysAdminAgent()


class TestHttpUnitAssertion:
    """kind: http polls the url AND asserts the unit is active."""

    @pytest.mark.asyncio
    async def test_url_ok_and_unit_active_is_ok(self, agent):
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("ok", 12, {})),
            patch(_UNIT_STATUS, new_callable=AsyncMock,
                  return_value={"is_active": True}),
        ):
            status, ms, _ = await agent._check_service(http_svc())
        assert (status, ms) == ("ok", 12)

    @pytest.mark.asyncio
    async def test_url_ok_but_unit_dead_is_degraded(self, agent):
        """The new failure mode: something answers, but not the unit we believe in."""
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("ok", 12, {})),
            patch(_UNIT_STATUS, new_callable=AsyncMock,
                  return_value={"is_active": False, "ActiveState": "failed"}),
        ):
            status, _, details = await agent._check_service(http_svc())
        assert status == "degraded"
        assert "not active" in details["reason"]

    @pytest.mark.asyncio
    async def test_url_ok_and_unit_activating_is_degraded(self, agent):
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("ok", 12, {})),
            patch(_UNIT_STATUS, new_callable=AsyncMock,
                  return_value={"is_active": False, "ActiveState": "activating"}),
        ):
            status, _, details = await agent._check_service(http_svc())
        assert status == "degraded"
        assert "activating" in details["reason"]

    @pytest.mark.asyncio
    async def test_the_unit_check_fails_open(self, agent):
        """An unreadable bus is not evidence the service is down.

        This is SNAG-SYSD-001's rule. Without it, a user-bus hiccup would
        turn every healthy http service on the box degraded at once.
        """
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("ok", 12, {})),
            patch(_UNIT_STATUS, new_callable=AsyncMock,
                  side_effect=UserBusUnavailableError("no session bus")),
        ):
            status, _, details = await agent._check_service(http_svc())
        assert status == "ok"
        assert details["unit_check"] == "unavailable"

    @pytest.mark.asyncio
    async def test_a_failing_url_is_not_rescued_by_a_live_unit(self, agent):
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("unreachable", None, {"error": "refused"})),
            patch(_UNIT_STATUS, new_callable=AsyncMock,
                  return_value={"is_active": True}) as unit,
        ):
            status, _, _ = await agent._check_service(http_svc())
        assert status == "unreachable"
        unit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_unit_declared_means_no_assertion(self, agent):
        """The internet probe polls a url no unit on this box serves."""
        probe = ServiceEntry(name="internet", kind="http", url="https://1.1.1.1")
        with (
            patch.object(agent, "_check_http", new_callable=AsyncMock,
                         return_value=("ok", 30, {})),
            patch(_UNIT_STATUS, new_callable=AsyncMock) as unit,
        ):
            status, _, _ = await agent._check_service(probe)
        assert status == "ok"
        unit.assert_not_called()


class TestTimerInspection:
    @pytest.mark.asyncio
    async def test_a_timer_records_its_last_run(self, agent):
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new_callable=AsyncMock, return_value={
            "is_active": True,
            "LastTriggerUSec": "Thu 2026-08-07 02:00:01 BST",
            "Result": "success",
        }):
            status, _, details = await agent._check_service(svc)
        assert status == "ok"
        assert details["last_run_recorded"] is True
        assert details["last_result"] == "success"

    def test_a_timer_that_has_never_fired_says_so(self):
        facts = _timer_facts({"LastTriggerUSec": "0", "Result": "success"})
        assert facts["last_run_recorded"] is False
        assert "last_run" not in facts

    def test_unset_properties_are_dropped(self):
        assert _timer_facts({"LastTriggerUSec": "[not set]"})["last_run_recorded"] is False


class TestSkipped:
    @pytest.mark.asyncio
    async def test_skipped_raises_no_alert_and_moves_no_counter(self, agent):
        svc = ServiceEntry(name="drain", kind="static", monitor=False,
                           reason="nightly only",
                           systemd={"unit": "drain.service"})
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as alert:
            raised = await agent._handle_status(None, svc, SKIPPED, {})
        assert raised == 0
        alert.assert_not_called()
        assert "drain" not in agent._failure_counts


class TestLogSourceDeduplication:
    def test_a_config_source_duplicating_a_service_unit_is_dropped(self):
        """sysadmin.service was ingested twice, as two differently-named sources."""
        from sysadmin.core.config import LogAggregatorConfig, LogSource
        from sysadmin.monitor.log_aggregator import LogAggregatorAgent
        from tests.conftest import set_services

        set_services({
            "name": "sysadmin-service", "kind": "http",
            "url": "http://localhost:8500/health",
            "systemd": {"unit": "sysadmin.service", "scope": "system"},
            "log": {"type": "journalctl", "severity_filter": "warning"},
        })
        agent_config = LogAggregatorConfig(sources=[
            LogSource(name="sysadmin", type="journalctl", unit="sysadmin.service"),
            LogSource(name="kernel", type="journalctl", unit="kernel",
                      severity_filter="error"),
        ])

        names = [s.name for s in LogAggregatorAgent._sources(agent_config)]
        assert names == ["sysadmin-service", "kernel"]

    def test_a_source_with_no_service_survives(self):
        from sysadmin.core.config import LogAggregatorConfig, LogSource
        from sysadmin.monitor.log_aggregator import LogAggregatorAgent
        from tests.conftest import set_services

        set_services()
        agent_config = LogAggregatorConfig(sources=[
            LogSource(name="kernel", type="journalctl", unit="kernel"),
        ])
        assert [s.name for s in LogAggregatorAgent._sources(agent_config)] == ["kernel"]


class TestTimerPropertiesAreActuallyFetched:
    """The coupling that made timer inspection inert on the first attempt.

    ``_timer_facts`` reads properties out of whatever ``get_unit_status``
    returns, and ``get_unit_status`` asks systemctl for a fixed list. The
    two agreed only by accident, and when they stopped agreeing the check
    still reported ``ok`` — it simply recorded nothing. Nothing failed, so
    nothing said so.
    """

    def test_every_property_timer_facts_reads_is_requested(self):
        import inspect

        from sysadmin.monitor import systemd
        from sysadmin.monitor.agent import _TIMER_PROPS

        source = inspect.getsource(systemd.get_unit_status)
        missing = [prop for prop in _TIMER_PROPS if f'"{prop}"' not in source]
        assert not missing, (
            "get_unit_status does not request: " + ", ".join(missing) +
            " — _timer_facts would silently record nothing"
        )

    @pytest.mark.asyncio
    async def test_a_timer_that_has_fired_records_its_last_run(self, agent):
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new_callable=AsyncMock, return_value={
            "is_active": True,
            "ActiveState": "active",
            "SubState": "waiting",
            "LastTriggerUSec": "Sat 2026-08-08 08:00:01 BST",
            "NextElapseUSecRealtime": "Sun 2026-08-09 08:00:00 BST",
            "Result": "success",
        }):
            status, _, details = await agent._check_service(svc)

        assert status == "ok"
        assert details["last_run"] == "Sat 2026-08-08 08:00:01 BST"
        assert details["next_run"] == "Sun 2026-08-09 08:00:00 BST"
        assert details["last_result"] == "success"
        assert details["last_run_recorded"] is True

    @pytest.mark.asyncio
    async def test_an_armed_timer_that_has_never_fired_is_still_ok(self, agent):
        """A newly installed timer is active and waiting with no last run.
        That is correct, not a fault."""
        svc = ServiceEntry(name="fresh", kind="timer",
                           systemd={"unit": "fresh.timer"})
        with patch(_UNIT_STATUS, new_callable=AsyncMock, return_value={
            "is_active": True, "SubState": "waiting",
            "LastTriggerUSec": "", "Result": "success",
            "NextElapseUSecRealtime": "Sun 2026-08-09 04:33:53 BST",
        }):
            status, _, details = await agent._check_service(svc)

        assert status == "ok"
        assert details["last_run_recorded"] is False
        assert details["next_run"]
