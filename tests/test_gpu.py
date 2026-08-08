"""Tests for AMD GPU monitoring utility and threshold alerting."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import Thresholds
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.gpu import (
    _parse_float,
    _parse_int,
    get_gpu_usage,
)
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

# ---------------------------------------------------------------------------
# Sample rocm-smi JSON data
# ---------------------------------------------------------------------------

SAMPLE_METRICS = json.dumps({
    "card0": {
        "Temperature (Sensor edge) (C)": "65.0",
        "Temperature (Sensor junction) (C)": "74.0",
        "Temperature (Sensor memory) (C)": "74.0",
        "Average Graphics Package Power (W)": "87.0",
        "GPU use (%)": "18",
        "VRAM Total Memory (B)": "25753026560",
        "VRAM Total Used Memory (B)": "3478065152",
    },
    "card1": {
        "Temperature (Sensor edge) (C)": "50.0",
        "Current Socket Graphics Package Power (W)": "0.014",
        "GPU use (%)": "0",
        "VRAM Total Memory (B)": "2147483648",
        "VRAM Total Used Memory (B)": "26124288",
    },
})

SAMPLE_NAMES = json.dumps({
    "card0": {"Card Series": "AMD Radeon RX 7900 XTX"},
    "card1": {"Card Series": "AMD Ryzen 9 9950X3D"},
})


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


class TestParseHelpers:
    def test_parse_float_valid(self):
        assert _parse_float("65.0") == 65.0

    def test_parse_float_none(self):
        assert _parse_float(None) is None

    def test_parse_float_invalid(self):
        assert _parse_float("N/A") is None

    def test_parse_int_valid(self):
        assert _parse_int("18") == 18

    def test_parse_int_none(self):
        assert _parse_int(None) is None


# ---------------------------------------------------------------------------
# rocm-smi parsing
# ---------------------------------------------------------------------------


class TestRocmSmiParsing:
    @pytest.mark.asyncio
    async def test_parses_two_cards(self):
        async def mock_communicate():
            return (SAMPLE_METRICS.encode(), b"")

        async def mock_names_communicate():
            return (SAMPLE_NAMES.encode(), b"")

        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("sysadmin.monitor.gpu.asyncio.create_subprocess_exec") as mock_exec:
                metrics_proc = AsyncMock()
                metrics_proc.communicate = mock_communicate
                names_proc = AsyncMock()
                names_proc.communicate = mock_names_communicate
                mock_exec.side_effect = [metrics_proc, names_proc]

                result = await get_gpu_usage()

        assert "card0" in result
        assert "card1" in result

    @pytest.mark.asyncio
    async def test_card0_fields(self):
        async def mock_communicate():
            return (SAMPLE_METRICS.encode(), b"")

        async def mock_names_communicate():
            return (SAMPLE_NAMES.encode(), b"")

        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("sysadmin.monitor.gpu.asyncio.create_subprocess_exec") as mock_exec:
                metrics_proc = AsyncMock()
                metrics_proc.communicate = mock_communicate
                names_proc = AsyncMock()
                names_proc.communicate = mock_names_communicate
                mock_exec.side_effect = [metrics_proc, names_proc]

                result = await get_gpu_usage()

        card0 = result["card0"]
        assert card0["name"] == "AMD Radeon RX 7900 XTX"
        assert card0["gpu_percent"] == 18
        assert card0["temp_c"] == 65.0
        assert card0["power_w"] == 87.0
        assert card0["vram_total_mb"] == round(25753026560 / 1024**2)
        assert card0["vram_used_mb"] == round(3478065152 / 1024**2)
        assert card0["vram_percent"] > 0

    @pytest.mark.asyncio
    async def test_fallback_power_field(self):
        """card1 uses 'Current Socket Graphics Package Power' instead of 'Average'."""
        async def mock_communicate():
            return (SAMPLE_METRICS.encode(), b"")

        async def mock_names_communicate():
            return (SAMPLE_NAMES.encode(), b"")

        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("sysadmin.monitor.gpu.asyncio.create_subprocess_exec") as mock_exec:
                metrics_proc = AsyncMock()
                metrics_proc.communicate = mock_communicate
                names_proc = AsyncMock()
                names_proc.communicate = mock_names_communicate
                mock_exec.side_effect = [metrics_proc, names_proc]

                result = await get_gpu_usage()

        assert result["card1"]["power_w"] == 0.014

    @pytest.mark.asyncio
    async def test_rocm_smi_failure_falls_back_to_sysfs(self):
        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("sysadmin.monitor.gpu._from_rocm_smi", side_effect=Exception("boom")):
                with patch(
                    "sysadmin.monitor.gpu._from_sysfs",
                    return_value={"card0": {"name": "sysfs"}},
                ) as mock_sysfs:
                    result = await get_gpu_usage()

        assert result == {"card0": {"name": "sysfs"}}
        mock_sysfs.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_rocm_smi_uses_sysfs(self):
        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with patch("sysadmin.monitor.gpu._from_sysfs", return_value={}) as mock_sysfs:
                result = await get_gpu_usage()

        assert result == {}
        mock_sysfs.assert_called_once()


# ---------------------------------------------------------------------------
# GPU threshold alerting
# ---------------------------------------------------------------------------


def _make_snapshot_with_gpu(gpu_usage: dict) -> ResourceSnapshot:
    row = ResourceSnapshot(
        cpu_percent=25.0,
        ram_used_mb=8000,
        ram_total_mb=16000,
        ram_percent=50.0,
        swap_used_mb=512,
        swap_total_mb=4096,
        disk_usage={},
        gpu_usage=gpu_usage,
        load_avg_1m=1.0,
        load_avg_5m=1.5,
        load_avg_15m=1.2,
    )
    row.id = uuid.uuid4()
    row.recorded_at = datetime.now(UTC)
    return row


class TestGpuThresholds:
    @pytest.fixture
    def agent(self):
        return SysAdminAgent()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def thresholds(self):
        return Thresholds(gpu_temp_warning_c=90, gpu_vram_warning_percent=90)

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 65.0, "vram_percent": 50.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0

    @pytest.mark.asyncio
    async def test_temp_alert_at_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 92.0, "vram_percent": 50.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1

    @pytest.mark.asyncio
    async def test_vram_alert_at_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 65.0, "vram_percent": 95.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1

    @pytest.mark.asyncio
    async def test_both_alerts(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 95.0, "vram_percent": 95.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 2

    @pytest.mark.asyncio
    async def test_empty_gpu_usage_no_alert(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({})
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0

    @pytest.mark.asyncio
    async def test_null_temp_no_alert(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": None, "vram_percent": None},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0
