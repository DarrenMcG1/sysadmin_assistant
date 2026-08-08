"""Tests for self-monitoring — agent run health and the /api/sysadmin/self endpoint.

The summary logic is a pure function, so stall/trend/failure rules are
pinned directly against hand-built ``AgentRun`` rows; the endpoint is
exercised against the real app fixture with a mocked DB session.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import AppConfig, SelfMonitorConfig
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.monitor.self_monitor import (
    AGENT_NAMES,
    AgentSchedule,
    agent_schedules,
    build_self_report,
    stall_window_seconds,
    summarise_agent,
)

NOW = datetime(2026, 7, 24, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(
    agent: str = "sysadmin",
    status: str = "completed",
    minutes_ago: float = 1.0,
    duration: float | None = 2.0,
    run_type: str = "scheduled",
) -> AgentRun:
    row = AgentRun(
        agent=agent,
        run_type=run_type,
        status=status,
        duration_seconds=duration,
        started_at=NOW - timedelta(minutes=minutes_ago),
    )
    row.id = uuid.uuid4()
    return row


def _live_run(agent: str, seconds_ago: float = 5.0, **overrides) -> AgentRun:
    """A run relative to the real clock — for endpoint tests, which use now()."""
    run = _run(agent=agent, **overrides)
    run.started_at = datetime.now(UTC) - timedelta(seconds=seconds_ago)
    return run


def _schedule(
    name: str = "sysadmin", interval: int = 300, enabled: bool = True
) -> AgentSchedule:
    return AgentSchedule(
        name=name, enabled=enabled, interval_seconds=interval, job_id=f"{name}_job"
    )


def _self_config(**overrides) -> SelfMonitorConfig:
    defaults = dict(
        enabled=True,
        stall_grace_multiplier=3.0,
        min_stall_grace_seconds=300,
        recent_runs=10,
    )
    defaults.update(overrides)
    return SelfMonitorConfig(**defaults)


def _mock_scalars_all(mock_session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# Schedules read from config
# ---------------------------------------------------------------------------


class TestAgentSchedules:
    def test_covers_every_agent(self):
        schedules = agent_schedules(AppConfig())
        assert set(schedules) == set(AGENT_NAMES)

    def test_intervals_come_from_config_not_hardcoded(self, mock_config):
        mock_config.agents.sysadmin.health_check_interval_seconds = 45
        mock_config.agents.project_organiser.scan_interval_hours = 2
        mock_config.agents.file_organiser.scan_interval_hours = 12
        mock_config.agents.log_aggregator.poll_interval_seconds = 90

        schedules = agent_schedules(mock_config)

        assert schedules["sysadmin"].interval_seconds == 45
        assert schedules["project_organiser"].interval_seconds == 2 * 3600
        assert schedules["file_organiser"].interval_seconds == 12 * 3600
        assert schedules["log_aggregator"].interval_seconds == 90

    def test_job_ids_match_the_scheduler_registration(self):
        """The ids here must match main.py's scheduler.schedule_interval calls."""
        import inspect

        from sysadmin import main

        source = inspect.getsource(main.lifespan)
        for schedule in agent_schedules(AppConfig()).values():
            assert f'job_id="{schedule.job_id}"' in source

    def test_disabled_agent_is_reported_as_disabled(self, mock_config):
        mock_config.agents.file_organiser.enabled = False
        assert agent_schedules(mock_config)["file_organiser"].enabled is False


class TestStallWindow:
    def test_multiplies_the_interval(self):
        window = stall_window_seconds(_schedule(interval=600), _self_config())
        assert window == 1800

    def test_floored_at_the_minimum_grace(self):
        """A 60s agent must not be flagged 180s after a restart."""
        window = stall_window_seconds(
            _schedule(interval=60), _self_config(min_stall_grace_seconds=300)
        )
        assert window == 300


# ---------------------------------------------------------------------------
# summarise_agent — the pure logic
# ---------------------------------------------------------------------------


class TestSummariseAgent:
    def test_recent_run_is_not_stalled(self):
        entry = summarise_agent(
            _schedule(), [_run(minutes_ago=1)], _self_config(), NOW
        )
        assert entry["stalled"] is False
        assert entry["stall_reason"] is None
        assert entry["last_status"] == "completed"
        assert entry["seconds_since_last_run"] == 60.0

    def test_silent_agent_is_stalled(self):
        entry = summarise_agent(
            _schedule(interval=300), [_run(minutes_ago=60)], _self_config(), NOW
        )
        assert entry["stalled"] is True
        assert "no run for 3600s" in entry["stall_reason"]

    def test_just_inside_the_window_is_not_stalled(self):
        # 300s interval × 3 = 900s window; 14 minutes ago = 840s
        entry = summarise_agent(
            _schedule(interval=300), [_run(minutes_ago=14)], _self_config(), NOW
        )
        assert entry["stalled"] is False

    def test_just_outside_the_window_is_stalled(self):
        entry = summarise_agent(
            _schedule(interval=300), [_run(minutes_ago=16)], _self_config(), NOW
        )
        assert entry["stalled"] is True

    def test_disabled_agent_is_never_stalled(self):
        entry = summarise_agent(
            _schedule(enabled=False), [_run(minutes_ago=6000)], _self_config(), NOW
        )
        assert entry["stalled"] is False

    def test_agent_with_no_runs_is_never_status_not_stalled(self):
        """A fresh install looks identical to a stopped agent — do not alert."""
        entry = summarise_agent(_schedule(), [], _self_config(), NOW)

        assert entry["last_status"] == "never"
        assert entry["last_run_at"] is None
        assert entry["stalled"] is False
        assert entry["expected_next_run_at"] is None
        assert entry["runs_considered"] == 0

    def test_stuck_running_record_counts_as_stalled(self):
        """A run that started long ago and never finished is a stall too."""
        entry = summarise_agent(
            _schedule(interval=300),
            [_run(status="running", minutes_ago=120, duration=None)],
            _self_config(),
            NOW,
        )
        assert entry["stalled"] is True

    def test_expected_next_run_derives_from_the_interval(self):
        entry = summarise_agent(
            _schedule(interval=300), [_run(minutes_ago=1)], _self_config(), NOW
        )
        expected = (NOW - timedelta(minutes=1) + timedelta(seconds=300)).isoformat()
        assert entry["expected_next_run_at"] == expected

    def test_naive_timestamps_are_treated_as_utc(self):
        run = _run(minutes_ago=1)
        run.started_at = run.started_at.replace(tzinfo=None)

        entry = summarise_agent(_schedule(), [run], _self_config(), NOW)
        assert entry["seconds_since_last_run"] == 60.0


class TestConsecutiveFailures:
    def test_counts_the_leading_failure_streak(self):
        runs = [
            _run(status="failed", minutes_ago=1),
            _run(status="failed", minutes_ago=2),
            _run(status="completed", minutes_ago=3),
            _run(status="failed", minutes_ago=4),
        ]
        entry = summarise_agent(_schedule(), runs, _self_config(), NOW)
        assert entry["consecutive_failures"] == 2

    def test_zero_when_the_latest_run_succeeded(self):
        runs = [_run(status="completed"), _run(status="failed", minutes_ago=2)]
        assert summarise_agent(_schedule(), runs, _self_config(), NOW)[
            "consecutive_failures"
        ] == 0

    def test_in_flight_run_does_not_break_the_streak(self):
        runs = [
            _run(status="running", minutes_ago=0.1, duration=None),
            _run(status="failed", minutes_ago=2),
            _run(status="failed", minutes_ago=3),
        ]
        assert summarise_agent(_schedule(), runs, _self_config(), NOW)[
            "consecutive_failures"
        ] == 2


class TestDurationTrend:
    def _trend(self, durations: list[float]) -> str:
        runs = [
            _run(minutes_ago=i + 1, duration=d) for i, d in enumerate(durations)
        ]
        return summarise_agent(_schedule(), runs, _self_config(), NOW)["duration_trend"]

    def test_too_few_samples_is_unknown(self):
        assert self._trend([1.0, 1.0, 1.0]) == "unknown"

    def test_stable_durations_are_steady(self):
        assert self._trend([2.0, 2.1, 1.9, 2.0, 2.05, 2.0]) == "steady"

    def test_recent_runs_much_slower_is_rising(self):
        # newest-first: recent half ~10s, older half ~2s
        assert self._trend([10.0, 11.0, 9.0, 2.0, 2.1, 1.9]) == "rising"

    def test_recent_runs_much_faster_is_falling(self):
        assert self._trend([2.0, 2.1, 1.9, 10.0, 11.0, 9.0]) == "falling"

    def test_mean_duration_is_reported(self):
        runs = [_run(duration=1.0), _run(minutes_ago=2, duration=3.0)]
        entry = summarise_agent(_schedule(), runs, _self_config(), NOW)
        assert entry["mean_duration_seconds"] == 2.0
        assert entry["recent_durations"] == [1.0, 3.0]

    def test_runs_without_a_duration_are_excluded(self):
        runs = [_run(status="running", duration=None), _run(minutes_ago=2, duration=4.0)]
        entry = summarise_agent(_schedule(), runs, _self_config(), NOW)
        assert entry["recent_durations"] == [4.0]
        assert entry["mean_duration_seconds"] == 4.0


# ---------------------------------------------------------------------------
# build_self_report
# ---------------------------------------------------------------------------


class TestBuildSelfReport:
    @pytest.mark.asyncio
    async def test_reports_every_configured_agent(self, mock_session, mock_config):
        _mock_scalars_all(mock_session, [_run(agent="sysadmin", minutes_ago=1)])

        report = await build_self_report(mock_session, mock_config, NOW)

        assert report["count"] == len(AGENT_NAMES)
        assert {a["name"] for a in report["agents"]} == set(AGENT_NAMES)

    @pytest.mark.asyncio
    async def test_healthy_when_everything_ran_recently(self, mock_session, mock_config):
        rows = [_run(agent=name, minutes_ago=0.5) for name in AGENT_NAMES]
        _mock_scalars_all(mock_session, rows)

        report = await build_self_report(mock_session, mock_config, NOW)

        assert report["healthy"] is True
        assert report["stalled_count"] == 0
        assert report["failing_count"] == 0

    @pytest.mark.asyncio
    async def test_stalled_agent_makes_the_report_unhealthy(
        self, mock_session, mock_config
    ):
        rows = [
            _run(agent=name, minutes_ago=0.5)
            for name in AGENT_NAMES
            if name != "log_aggregator"
        ]
        rows.append(_run(agent="log_aggregator", minutes_ago=600))
        _mock_scalars_all(mock_session, rows)

        report = await build_self_report(mock_session, mock_config, NOW)

        assert report["stalled_count"] == 1
        assert report["healthy"] is False
        stalled = next(a for a in report["agents"] if a["stalled"])
        assert stalled["name"] == "log_aggregator"

    @pytest.mark.asyncio
    async def test_failing_agent_makes_the_report_unhealthy(
        self, mock_session, mock_config
    ):
        rows = [_run(agent=name, minutes_ago=0.5) for name in AGENT_NAMES if name != "sysadmin"]
        rows.append(_run(agent="sysadmin", status="failed", minutes_ago=0.5))
        _mock_scalars_all(mock_session, rows)

        report = await build_self_report(mock_session, mock_config, NOW)

        assert report["failing_count"] == 1
        assert report["healthy"] is False

    @pytest.mark.asyncio
    async def test_runs_are_sorted_newest_first(self, mock_session, mock_config):
        rows = [
            _run(agent="sysadmin", minutes_ago=5, duration=5.0),
            _run(agent="sysadmin", minutes_ago=1, duration=1.0),
        ]
        _mock_scalars_all(mock_session, rows)

        report = await build_self_report(mock_session, mock_config, NOW)
        entry = next(a for a in report["agents"] if a["name"] == "sysadmin")

        assert entry["recent_durations"] == [1.0, 5.0]
        assert entry["seconds_since_last_run"] == 60.0


# ---------------------------------------------------------------------------
# GET /api/sysadmin/self
# ---------------------------------------------------------------------------


class TestSelfEndpoint:
    @pytest.mark.asyncio
    async def test_returns_the_contract_shape(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [_live_run(name) for name in AGENT_NAMES])

        resp = await test_client.get("/api/sysadmin/self")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == len(AGENT_NAMES)
        assert data["healthy"] is True
        assert data["generated_at"]

        entry = data["agents"][0]
        for key in (
            "name",
            "enabled",
            "interval_seconds",
            "last_run_at",
            "last_status",
            "consecutive_failures",
            "recent_durations",
            "mean_duration_seconds",
            "duration_trend",
            "stalled",
            "expected_next_run_at",
        ):
            assert key in entry

    @pytest.mark.asyncio
    async def test_reports_a_stalled_agent(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [_run(agent="sysadmin", minutes_ago=1000)])

        resp = await test_client.get("/api/sysadmin/self")
        data = resp.json()

        assert resp.status_code == 200
        assert data["stalled_count"] >= 1
        assert data["healthy"] is False
        entry = next(a for a in data["agents"] if a["name"] == "sysadmin")
        assert entry["stalled"] is True
        assert "no run for" in entry["stall_reason"]

    @pytest.mark.asyncio
    async def test_empty_agent_runs_table(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])

        resp = await test_client.get("/api/sysadmin/self")
        data = resp.json()

        assert resp.status_code == 200
        assert data["stalled_count"] == 0
        assert all(a["last_status"] == "never" for a in data["agents"])

    @pytest.mark.asyncio
    async def test_parses_as_the_shared_contract(self, test_client, mock_session):
        from sysadmin.core.contracts import SelfMonitorResponse

        _mock_scalars_all(mock_session, [_live_run("sysadmin")])
        resp = await test_client.get("/api/sysadmin/self")

        parsed = SelfMonitorResponse.from_dict(resp.json())
        assert isinstance(parsed, SelfMonitorResponse)
        assert parsed.count == len(AGENT_NAMES)
        assert {a.name for a in parsed.agents} == set(AGENT_NAMES)


# ---------------------------------------------------------------------------
# Stalled-agent alerting (SysAdmin agent wiring)
# ---------------------------------------------------------------------------


def _report(*stalled: str) -> dict:
    """A self-report where the named agents are stalled."""
    agents = [
        {
            "name": name,
            "stalled": name in stalled,
            "last_run_at": "2026-07-24T09:00:00+00:00",
            "stall_reason": "no run for 9000s" if name in stalled else None,
            "seconds_since_last_run": 9000.0 if name in stalled else 5.0,
            "interval_seconds": 300,
            "consecutive_failures": 0,
        }
        for name in AGENT_NAMES
    ]
    return {"agents": agents, "count": len(agents), "stalled_count": len(stalled)}


def _stall_alert(agent_name: str, alert_id: str = "stall-1"):
    alert = MagicMock()
    alert.id = alert_id
    alert.title = f"{agent_name} agent stalled"
    alert.details = {"stalled_agent": agent_name}
    return alert


@pytest.fixture
def sysadmin_agent():
    from sysadmin.monitor.agent import SysAdminAgent

    return SysAdminAgent()


def _patch_report(report: dict):
    return patch(
        "sysadmin.monitor.agent.build_self_report",
        new_callable=AsyncMock,
        return_value=report,
    )


class TestStalledAgentAlerting:
    @pytest.mark.asyncio
    async def test_alerts_when_an_agent_stops_running(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report("log_aggregator")),
            patch.object(
                sysadmin_agent, "_active_alerts", new_callable=AsyncMock, return_value=[]
            ),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock) as ra,
        ):
            raised = await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        assert raised == 1
        kwargs = ra.call_args.kwargs
        assert kwargs["title"] == "log_aggregator agent stalled"
        assert kwargs["severity"] == "warning"
        assert kwargs["details"]["stalled_agent"] == "log_aggregator"
        assert kwargs["details"]["seconds_since_last_run"] == 9000.0

    @pytest.mark.asyncio
    async def test_no_alert_when_every_agent_is_running(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report()),
            patch.object(
                sysadmin_agent, "_active_alerts", new_callable=AsyncMock, return_value=[]
            ),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock) as ra,
        ):
            raised = await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_existing_stall_alert_is_not_duplicated(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report("log_aggregator")),
            patch.object(
                sysadmin_agent,
                "_active_alerts",
                new_callable=AsyncMock,
                return_value=[_stall_alert("log_aggregator")],
            ),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock) as ra,
        ):
            raised = await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_stall_alert_resolved_when_the_agent_returns(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report()),
            patch.object(
                sysadmin_agent,
                "_active_alerts",
                new_callable=AsyncMock,
                return_value=[_stall_alert("log_aggregator", alert_id="stall-7")],
            ),
            patch.object(
                sysadmin_agent, "_resolve_alert_ids", new_callable=AsyncMock
            ) as resolve,
        ):
            await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        resolve.assert_awaited_once()
        assert resolve.call_args.args[1] == ["stall-7"]

    @pytest.mark.asyncio
    async def test_two_stalled_agents_raise_two_alerts(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report("file_organiser", "project_organiser")),
            patch.object(
                sysadmin_agent, "_active_alerts", new_callable=AsyncMock, return_value=[]
            ),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock) as ra,
        ):
            raised = await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        assert raised == 2
        titles = {call.kwargs["title"] for call in ra.call_args_list}
        assert titles == {
            "file_organiser agent stalled",
            "project_organiser agent stalled",
        }

    @pytest.mark.asyncio
    async def test_disabled_self_monitoring_does_nothing(
        self, sysadmin_agent, mock_session, mock_config
    ):
        mock_config.self_monitor.enabled = False
        with patch(
            "sysadmin.monitor.agent.build_self_report", new_callable=AsyncMock
        ) as report:
            raised = await sysadmin_agent._check_agent_liveness(mock_session, mock_config)

        assert raised == 0
        report.assert_not_called()
