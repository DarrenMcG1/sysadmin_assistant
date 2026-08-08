"""Tests for z-score resource anomaly detection.

The maths is pure, so it is pinned directly: known series → known
z-scores, plus the two guards that stop it misbehaving (cold start and a
zero/near-zero standard deviation).
"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import AnomalyConfig, Thresholds
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.anomaly import (
    Anomaly,
    detect_anomalies,
    mean,
    metric_label,
    stdev,
    z_score,
)
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _config(**overrides) -> AnomalyConfig:
    defaults = dict(
        enabled=True,
        window_days=7,
        z_threshold=3.0,
        min_samples=5,
        min_stdev=0.5,
    )
    defaults.update(overrides)
    return AnomalyConfig(**defaults)


# A series with an exactly known mean (5.0) and sample stdev (√2.5 ≈ 1.5811)
KNOWN_SERIES = [3.0, 4.0, 5.0, 6.0, 7.0]


# ---------------------------------------------------------------------------
# Statistics primitives
# ---------------------------------------------------------------------------


class TestStatistics:
    def test_mean_of_known_series(self):
        assert mean(KNOWN_SERIES) == 5.0

    def test_mean_of_empty_series_is_zero(self):
        assert mean([]) == 0.0

    def test_sample_stdev_of_known_series(self):
        assert stdev(KNOWN_SERIES) == pytest.approx(math.sqrt(2.5))

    def test_stdev_of_single_value_is_zero(self):
        assert stdev([42.0]) == 0.0

    def test_stdev_of_constant_series_is_zero(self):
        assert stdev([7.0] * 10) == 0.0

    def test_z_score_of_known_value(self):
        # 5 + 2σ where σ = √2.5
        value = 5.0 + 2 * math.sqrt(2.5)
        assert z_score(value, 5.0, math.sqrt(2.5)) == pytest.approx(2.0)

    def test_z_score_at_the_mean_is_zero(self):
        assert z_score(5.0, 5.0, 1.5) == 0.0

    def test_z_score_below_the_mean_is_negative(self):
        assert z_score(2.0, 5.0, 1.5) == pytest.approx(-2.0)

    def test_zero_stdev_returns_none_not_infinity(self):
        assert z_score(10.0, 5.0, 0.0) is None

    def test_negative_stdev_returns_none(self):
        assert z_score(10.0, 5.0, -1.0) is None

    def test_non_finite_input_returns_none(self):
        assert z_score(math.inf, 5.0, 1.0) is None
        assert z_score(10.0, 5.0, math.inf) is None


class TestMetricLabels:
    def test_known_labels(self):
        assert metric_label("cpu") == "CPU"
        assert metric_label("ram") == "RAM"

    def test_disk_label_keeps_the_mount_point(self):
        assert metric_label("disk:/home") == "disk /home"

    def test_unknown_key_passes_through(self):
        assert metric_label("swap") == "swap"


# ---------------------------------------------------------------------------
# detect_anomalies
# ---------------------------------------------------------------------------


class TestDetectAnomalies:
    def test_flags_value_beyond_threshold(self):
        # Series: mean 10, σ = 1.0 (sample) for [9, 10, 11] repeated
        history = {"cpu": [9.0, 10.0, 11.0] * 5}
        result = detect_anomalies({"cpu": 20.0}, history, _config(min_samples=5))

        assert len(result) == 1
        anomaly = result[0]
        assert anomaly.key == "cpu"
        assert anomaly.label == "CPU"
        assert anomaly.value == 20.0
        assert anomaly.mean == pytest.approx(10.0)
        assert anomaly.z > 3.0
        assert anomaly.direction == "above"
        assert anomaly.samples == 15

    def test_z_score_matches_hand_computed_value(self):
        history = {"ram": KNOWN_SERIES}
        value = 5.0 + 4 * math.sqrt(2.5)  # exactly 4σ above the mean
        result = detect_anomalies({"ram": value}, history, _config(min_samples=5))

        assert len(result) == 1
        assert result[0].z == pytest.approx(4.0)
        assert result[0].stdev == pytest.approx(math.sqrt(2.5))

    def test_normal_value_is_not_flagged(self):
        history = {"cpu": [9.0, 10.0, 11.0] * 5}
        assert detect_anomalies({"cpu": 10.5}, history, _config(min_samples=5)) == []

    def test_value_just_below_threshold_is_not_flagged(self):
        history = {"ram": KNOWN_SERIES}
        value = 5.0 + 2.9 * math.sqrt(2.5)
        assert detect_anomalies({"ram": value}, history, _config(min_samples=5)) == []

    def test_low_outlier_is_flagged_as_below(self):
        history = {"ram": KNOWN_SERIES}
        value = 5.0 - 4 * math.sqrt(2.5)
        result = detect_anomalies({"ram": value}, history, _config(min_samples=5))

        assert len(result) == 1
        assert result[0].direction == "below"
        assert result[0].z < 0

    def test_cold_start_returns_nothing(self):
        """Too few samples must never flag — a fresh install has no baseline."""
        history = {"cpu": [10.0, 10.5, 90.0]}
        assert detect_anomalies({"cpu": 99.0}, history, _config(min_samples=30)) == []

    def test_metric_with_no_history_is_skipped(self):
        assert detect_anomalies({"cpu": 99.0}, {}, _config(min_samples=5)) == []

    def test_zero_variance_history_does_not_explode(self):
        """A constant series would give an infinite z-score — it is skipped."""
        history = {"disk:/": [50.0] * 100}
        result = detect_anomalies({"disk:/": 51.0}, history, _config(min_stdev=0.5))

        assert result == []

    def test_near_zero_variance_is_skipped(self):
        history = {"disk:/": [50.0, 50.01] * 50}
        result = detect_anomalies({"disk:/": 55.0}, history, _config(min_stdev=1.0))

        assert result == []

    def test_disabled_config_returns_nothing(self):
        history = {"cpu": [9.0, 10.0, 11.0] * 5}
        result = detect_anomalies(
            {"cpu": 99.0}, history, _config(enabled=False, min_samples=5)
        )
        assert result == []

    def test_multiple_metrics_sorted_by_severity(self):
        history = {
            "cpu": KNOWN_SERIES * 2,
            "ram": KNOWN_SERIES * 2,
        }
        sigma = stdev(KNOWN_SERIES * 2)
        current = {"cpu": 5.0 + 3.5 * sigma, "ram": 5.0 + 9 * sigma}

        result = detect_anomalies(current, history, _config(min_samples=5))

        assert [a.key for a in result] == ["ram", "cpu"]
        assert abs(result[0].z) > abs(result[1].z)

    def test_non_finite_current_value_is_ignored(self):
        history = {"cpu": KNOWN_SERIES * 3}
        assert detect_anomalies({"cpu": math.nan}, history, _config(min_samples=5)) == []

    def test_none_values_in_history_are_dropped(self):
        history = {"cpu": [None, *KNOWN_SERIES, None]}  # type: ignore[list-item]
        result = detect_anomalies(
            {"cpu": 5.0 + 5 * math.sqrt(2.5)}, history, _config(min_samples=5)
        )
        assert len(result) == 1
        assert result[0].samples == 5


class TestAnomalyDetails:
    def test_details_carry_the_dedup_key_and_stats(self):
        anomaly = Anomaly(
            key="disk:/home",
            label="disk /home",
            value=91.234,
            mean=50.0,
            stdev=2.0,
            z=20.6,
            samples=200,
        )
        details = anomaly.as_details()

        assert details["anomaly"] is True
        assert details["resource"] == "disk:/home"
        assert details["value"] == 91.23
        assert details["z_score"] == 20.6
        assert details["samples"] == 200
        assert details["direction"] == "above"


# ---------------------------------------------------------------------------
# SysAdmin agent wiring — alerting, suppression, history loading
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return SysAdminAgent()


def _snapshot(cpu=10.0, ram=50.0, disk=None) -> ResourceSnapshot:
    return ResourceSnapshot(
        cpu_percent=cpu,
        ram_percent=ram,
        ram_used_mb=8000,
        ram_total_mb=16000,
        disk_usage=disk if disk is not None else {"/": {"percent": 40}},
        gpu_usage={},
    )


def _rows(mock_session, rows):
    """Make session.execute() return ``rows`` via scalars().all()."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _fake_alert(details: dict, alert_id: str = "a1", title: str = "x"):
    alert = MagicMock()
    alert.id = alert_id
    alert.title = title
    alert.details = details
    return alert


class TestSnapshotMetrics:
    def test_keys_cover_cpu_ram_and_every_mount(self):
        metrics = SysAdminAgent._snapshot_metrics(
            _snapshot(disk={"/": {"percent": 40}, "/home": {"percent": 91}})
        )
        assert metrics == {"cpu": 10.0, "ram": 50.0, "disk:/": 40.0, "disk:/home": 91.0}

    def test_missing_values_are_skipped(self):
        snapshot = ResourceSnapshot(
            cpu_percent=None, ram_percent=None, disk_usage={"/": {}}, gpu_usage={}
        )
        assert SysAdminAgent._snapshot_metrics(snapshot) == {}


class TestThresholdKeys:
    @pytest.mark.asyncio
    async def test_threshold_alerts_record_their_resource_key(self, agent, mock_session):
        thresholds = Thresholds(ram_warning_percent=85, disk_warning_percent=80)
        snapshot = _snapshot(ram=90.0, disk={"/home": {"percent": 85}})

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._check_thresholds(mock_session, snapshot, thresholds)

        assert agent._threshold_keys == {"ram", "disk:/home"}
        details = [call.kwargs["details"] for call in ra.call_args_list]
        assert all(d["threshold"] is True for d in details)
        assert {d["resource"] for d in details} == {"ram", "disk:/home"}

    @pytest.mark.asyncio
    async def test_keys_reset_between_runs(self, agent, mock_session):
        thresholds = Thresholds(ram_warning_percent=85)
        with patch.object(agent, "raise_alert", new_callable=AsyncMock):
            await agent._check_thresholds(mock_session, _snapshot(ram=90.0), thresholds)
            assert agent._threshold_keys == {"ram"}
            await agent._check_thresholds(mock_session, _snapshot(ram=50.0), thresholds)

        assert agent._threshold_keys == set()


class TestAgentAnomalyChecks:
    @pytest.fixture
    def anomaly_config(self):
        return AnomalyConfig(min_samples=5, z_threshold=3.0, min_stdev=0.5)

    @pytest.mark.asyncio
    async def test_raises_alert_for_an_outlier(self, agent, mock_session, anomaly_config):
        _rows(mock_session, [])

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session, _snapshot(cpu=80.0), {"cpu": [9.0, 10.0, 11.0] * 5},
                anomaly_config,
            )

        assert raised == 1
        kwargs = ra.call_args.kwargs
        assert kwargs["title"] == "Unusual CPU usage"
        assert kwargs["details"]["anomaly"] is True
        assert kwargs["details"]["resource"] == "cpu"
        assert "above" in kwargs["message"]

    @pytest.mark.asyncio
    async def test_no_alert_when_nothing_is_unusual(
        self, agent, mock_session, anomaly_config
    ):
        _rows(mock_session, [])

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session, _snapshot(cpu=10.0), {"cpu": [9.0, 10.0, 11.0] * 5},
                anomaly_config,
            )

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_suppressed_by_threshold_alert_in_the_same_run(
        self, agent, mock_session, anomaly_config
    ):
        """A resource that just tripped a fixed threshold must not alert twice."""
        _rows(mock_session, [])
        agent._threshold_keys = {"disk:/"}

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session,
                _snapshot(disk={"/": {"percent": 95}}),
                {"disk:/": [40.0, 41.0, 42.0] * 5},
                anomaly_config,
            )

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_suppressed_by_an_unresolved_threshold_alert(
        self, agent, mock_session, anomaly_config
    ):
        _rows(
            mock_session,
            [_fake_alert({"resource": "ram", "threshold": True}, title="High RAM usage")],
        )

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session, _snapshot(ram=95.0), {"ram": [50.0, 51.0, 52.0] * 5},
                anomaly_config,
            )

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_open_anomaly_alert_is_not_repeated(
        self, agent, mock_session, anomaly_config
    ):
        _rows(
            mock_session,
            [_fake_alert({"resource": "cpu", "anomaly": True}, title="Unusual CPU usage")],
        )

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session, _snapshot(cpu=80.0), {"cpu": [9.0, 10.0, 11.0] * 5},
                anomaly_config,
            )

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_anomaly_alert_resolved_once_back_to_normal(
        self, agent, mock_session, anomaly_config
    ):
        _rows(
            mock_session,
            [_fake_alert({"resource": "cpu", "anomaly": True}, alert_id="gone")],
        )

        with patch.object(agent, "_resolve_alert_ids", new_callable=AsyncMock) as resolve:
            await agent._check_anomalies(
                mock_session, _snapshot(cpu=10.0), {"cpu": [9.0, 10.0, 11.0] * 5},
                anomaly_config,
            )

        resolve.assert_awaited_once()
        assert resolve.call_args.args[1] == ["gone"]

    @pytest.mark.asyncio
    async def test_disabled_does_nothing(self, agent, mock_session):
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session,
                _snapshot(cpu=99.0),
                {"cpu": [9.0, 10.0, 11.0] * 5},
                AnomalyConfig(enabled=False),
            )

        assert raised == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_cold_start_raises_nothing(self, agent, mock_session):
        _rows(mock_session, [])

        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            raised = await agent._check_anomalies(
                mock_session,
                _snapshot(cpu=99.0),
                {"cpu": [9.0, 10.0, 11.0]},
                AnomalyConfig(min_samples=30),
            )

        assert raised == 0
        ra.assert_not_called()


class TestLoadMetricHistory:
    @pytest.mark.asyncio
    async def test_builds_a_series_per_metric(self, agent, mock_session):
        _rows(
            mock_session,
            [
                _snapshot(cpu=10.0, ram=50.0, disk={"/": {"percent": 40}}),
                _snapshot(cpu=20.0, ram=60.0, disk={"/": {"percent": 41}}),
            ],
        )

        history = await agent._load_metric_history(mock_session, AnomalyConfig())

        assert history["cpu"] == [10.0, 20.0]
        assert history["ram"] == [50.0, 60.0]
        assert history["disk:/"] == [40.0, 41.0]

    @pytest.mark.asyncio
    async def test_disabled_skips_the_query(self, agent, mock_session):
        mock_session.execute = AsyncMock()

        history = await agent._load_metric_history(
            mock_session, AnomalyConfig(enabled=False)
        )

        assert history == {}
        mock_session.execute.assert_not_called()
