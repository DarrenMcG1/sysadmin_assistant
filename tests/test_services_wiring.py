"""Tests for the behaviour services.yaml changed when it was wired in.

Every case here is a delta flagged before the wiring landed: the unit
assertion added to http checks, the timer inspection, the skipped status,
and the log-source de-duplication.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.agent import SysAdminAgent, _timer_facts
from sysadmin.monitor.services import SKIPPED, ServiceEntry
from sysadmin.monitor.systemd import SystemdQueryError, UserBusUnavailableError

_UNIT_STATUS = "sysadmin.monitor.agent.get_unit_status"


def two_units(timer: dict, triggered: dict | None):
    """A ``get_unit_status`` stand-in that can tell two units apart.

    SNAG-SYSD-005.  A ``kind: timer`` check reads the timer **and** the
    unit it starts, so a stub answering every call with one dict answers
    the second question with the first unit's facts — which is the defect
    itself, wearing a mock's clothes.  Three tests here were green for the
    life of that bug because their stub could not hold two units.

    ``triggered=None`` models a triggered unit systemd will not answer for.
    """
    served = {"Unit": timer.get("Unit", "nightly.service"), **timer}

    async def _dispatch(unit, user=False):
        if unit == served["Unit"]:
            if triggered is None:
                raise SystemdQueryError(f"systemctl show {unit} exited with code 1")
            return triggered
        return served

    return _dispatch


def armed_timer(**overrides) -> dict:
    """An armed timer's own properties: active, waiting, fired this morning."""
    return {
        "is_active": True,
        "ActiveState": "active",
        "SubState": "waiting",
        "Unit": "nightly.service",
        "LastTriggerUSec": "Sat 2026-08-08 08:00:01 BST",
        "NextElapseUSecRealtime": "Sun 2026-08-09 08:00:00 BST",
        # The timer's own Result. `success` on ten of ten timers on this
        # box, including the one whose service had failed twelve mornings
        # running — which is why nothing may read it as a run outcome.
        "Result": "success",
    } | overrides


def triggered_unit(**overrides) -> dict:
    """The started unit's properties: a oneshot that exited cleanly."""
    return {
        "is_active": False,
        "ActiveState": "inactive",
        "SubState": "dead",
        "Result": "success",
        "ExecMainStatus": "0",
    } | overrides


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
        with patch(_UNIT_STATUS, new=two_units(
            armed_timer(LastTriggerUSec="Thu 2026-08-07 02:00:01 BST"),
            triggered_unit(),
        )):
            status, _, details = await agent._check_service(svc)
        assert status == "ok"
        assert details["last_run_recorded"] is True
        assert details["last_result"] == "success"

    def test_a_timer_that_has_never_fired_says_so(self):
        facts = _timer_facts({"LastTriggerUSec": "0"}, triggered_unit())
        assert facts["last_run_recorded"] is False
        assert "last_run" not in facts

    def test_unset_properties_are_dropped(self):
        facts = _timer_facts({"LastTriggerUSec": "[not set]"}, triggered_unit())
        assert facts["last_run_recorded"] is False


class TestTheTimerIsNotTheJob:
    """SNAG-SYSD-005 — the check reads the unit the timer *starts*.

    Alfred's `alfred-career-mail.service` failed on twelve consecutive
    mornings while this check wrote 3,988 unbroken `ok` rows, because it
    read `Result` off the `.timer`.  Measured on this box the day it was
    fixed: `Result=success` on ten of ten declared timers, and one of the
    ten triggered services at `exit-code`.  The field the check read was
    constant across the whole population; the field it did not read
    discriminated exactly the broken one.
    """

    @pytest.mark.asyncio
    async def test_an_armed_timer_whose_job_failed_is_critical(self, agent):
        """The founding case, in the shape the live box had it."""
        svc = ServiceEntry(name="career-mail", kind="timer",
                           systemd={"unit": "career-mail.timer"})
        with patch(_UNIT_STATUS, new=two_units(
            armed_timer(Unit="career-mail.service"),
            triggered_unit(ActiveState="failed", SubState="failed",
                           Result="exit-code", ExecMainStatus="1"),
        )):
            status, _, details = await agent._check_service(svc)

        assert status == "critical"
        # The timer is genuinely fine and the row says so — the news is
        # that being fine is not the question.
        assert details["ActiveState"] == "active"
        assert details["last_result"] == "exit-code"
        assert details["triggered_unit"] == "career-mail.service"
        assert details["triggered_exit_status"] == "1"

    @pytest.mark.asyncio
    async def test_the_timers_own_result_is_never_the_answer(self, agent):
        """The exact live shape: timer `success`, job `exit-code`.

        Falsified against the pre-fix code, where `last_result` came from
        the timer and this returned `ok` with `last_result == "success"`.
        """
        svc = ServiceEntry(name="career-mail", kind="timer",
                           systemd={"unit": "career-mail.timer"})
        with patch(_UNIT_STATUS, new=two_units(
            armed_timer(Unit="career-mail.service", Result="success"),
            triggered_unit(Result="exit-code", ExecMainStatus="1"),
        )):
            status, _, details = await agent._check_service(svc)

        assert status == "critical"
        assert details["last_result"] != "success"

    @pytest.mark.asyncio
    async def test_a_clean_run_leaves_the_timer_ok(self, agent):
        """A oneshot at rest is `inactive (dead)` with `Result=success`.

        The resting state of every healthy timer here, so reading
        `ActiveState` rather than `Result` on the triggered unit would
        report all ten as down.
        """
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new=two_units(armed_timer(), triggered_unit())):
            status, _, details = await agent._check_service(svc)

        assert status == "ok"
        assert details["triggered_active_state"] == "inactive"
        assert details["last_result"] == "success"

    @pytest.mark.asyncio
    async def test_an_unreadable_triggered_unit_is_error_not_ok(self, agent):
        """`ports_checked`'s rule: zero-because-blind is not zero-because-clean.

        `error` raises no alert and is excluded from the reliability
        rates, which is SNAG-SYSD-001's decision for an unqueryable unit.
        Reporting `ok` would rebuild this check's founding defect one
        level down.
        """
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new=two_units(armed_timer(), None)):
            status, _, details = await agent._check_service(svc)

        assert status == "error"
        assert "triggered_error" in details
        assert details["triggered_result_recorded"] is False
        assert "last_result" not in details

    @pytest.mark.asyncio
    async def test_a_timer_naming_no_unit_is_error(self, agent):
        """A timer that publishes no `Unit=` is a way of not-knowing too."""
        timer = armed_timer()
        del timer["Unit"]
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})

        async def _only_the_timer(unit, user=False):
            return timer

        with patch(_UNIT_STATUS, new=_only_the_timer):
            status, _, details = await agent._check_service(svc)

        assert status == "error"
        assert "Unit=" in details["triggered_error"]

    @pytest.mark.asyncio
    async def test_an_inactive_timer_is_still_critical_on_the_timer(self, agent):
        """A disarmed schedule is a fault the timer itself carries.

        It returns before the triggered unit is ever consulted, so a
        stopped timer is not misreported as an unreadable job.
        """
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new=two_units(
            armed_timer(is_active=False, ActiveState="inactive",
                        SubState="dead"),
            triggered_unit(),
        )):
            status, _, details = await agent._check_service(svc)

        assert status == "critical"
        assert "triggered_error" not in details

    @pytest.mark.asyncio
    async def test_a_non_timer_service_reads_only_itself(self, agent):
        """`inspect_timer` is set by `check_plan` for `kind: timer` alone.

        A plain `kind: systemd` service must not gain a second subprocess
        or a `triggered_unit` key it has no business carrying.
        """
        calls: list[str] = []

        async def _record(unit, user=False):
            calls.append(unit)
            return {"is_active": True, "ActiveState": "active",
                    "Unit": "somewhere.service", "Result": "success"}

        svc = ServiceEntry(name="api", kind="systemd",
                           systemd={"unit": "api.service"})
        with patch(_UNIT_STATUS, new=_record):
            status, _, details = await agent._check_service(svc)

        assert status == "ok"
        assert calls == ["api.service"]
        assert "triggered_unit" not in details


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
        """The coupling itself, over **both** units' property sets.

        It covered `_TIMER_PROPS` alone until SNAG-SYSD-005, which is one
        of the two reasons the fix needed a new request: `Unit` resolves
        the triggered unit and `_TRIGGERED_PROPS` describes it, and a
        property this walk cannot see would make `_timer_facts` record
        nothing while reporting success — the original defect exactly.
        """
        import inspect

        from sysadmin.monitor import systemd
        from sysadmin.monitor.agent import _TIMER_PROPS, _TRIGGERED_PROPS

        source = inspect.getsource(systemd.get_unit_status)
        wanted = [*_TIMER_PROPS, *_TRIGGERED_PROPS, "Unit"]
        missing = [prop for prop in wanted if f'"{prop}"' not in source]
        assert not missing, (
            "get_unit_status does not request: " + ", ".join(missing) +
            " — _timer_facts would silently record nothing"
        )

    def test_the_timers_own_result_is_not_read_as_a_run_outcome(self):
        """Provenance, not value — the shape Session 59's guards recorded.

        `_timer_facts({"Result": ...}, triggered)` must take `last_result`
        from the *second* argument.  Asserting the value alone passes
        against the pre-fix code whenever the two agree, which they do on
        nine of this box's ten timers.
        """
        from sysadmin.monitor.agent import _TIMER_PROPS

        facts = _timer_facts(
            armed_timer(Result="success"),
            triggered_unit(Result="exit-code"),
        )
        assert facts["last_result"] == "exit-code"
        assert "Result" not in _TIMER_PROPS, (
            "the timer's own Result is back in the schedule's fact set — "
            "it reports whether the timer unit started, not the job"
        )

    @pytest.mark.asyncio
    async def test_a_timer_that_has_fired_records_its_last_run(self, agent):
        svc = ServiceEntry(name="nightly", kind="timer",
                           systemd={"unit": "nightly.timer"})
        with patch(_UNIT_STATUS, new=two_units(armed_timer(), triggered_unit())):
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
        with patch(_UNIT_STATUS, new=two_units(
            armed_timer(Unit="fresh.service", LastTriggerUSec="",
                        NextElapseUSecRealtime="Sun 2026-08-09 04:33:53 BST"),
            # A unit systemd has loaded but never started: `Result` is
            # `success` from the outset, which is why "has it ever run"
            # is `timer_stale`'s question and not this check's.
            triggered_unit(ExecMainStatus="0"),
        )):
            status, _, details = await agent._check_service(svc)

        assert status == "ok"
        assert details["last_run_recorded"] is False
        assert details["next_run"]
