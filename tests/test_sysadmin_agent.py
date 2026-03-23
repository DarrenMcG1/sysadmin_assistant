"""Tests for the SysAdmin agent — HTTP/TCP/systemd checks, alerting, thresholds."""

from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sysadmin.agents.sysadmin_agent import SysAdminAgent
from sysadmin.config import MonitoredService, Thresholds
from sysadmin.models.resource_snapshot import ResourceSnapshot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    a = SysAdminAgent()
    a._http_client = AsyncMock(spec=httpx.AsyncClient)
    return a


@pytest.fixture
def http_service():
    return MonitoredService(
        name="web-api", type="http", url="http://localhost:8000/health"
    )


@pytest.fixture
def tcp_service():
    return MonitoredService(
        name="postgres", type="tcp", host="localhost", port=5432
    )


@pytest.fixture
def systemd_service():
    return MonitoredService(
        name="redis", type="systemd", systemd_unit="redis.service"
    )


# ---------------------------------------------------------------------------
# HTTP checks
# ---------------------------------------------------------------------------


class TestCheckHttp:
    @pytest.mark.asyncio
    async def test_http_ok(self, agent, http_service):
        resp = MagicMock(status_code=200)
        agent._http_client.get = AsyncMock(return_value=resp)

        status, ms, details = await agent._check_http(http_service)
        assert status == "ok"
        assert isinstance(ms, int)
        assert details == {}

    @pytest.mark.asyncio
    async def test_http_4xx_is_degraded(self, agent, http_service):
        resp = MagicMock(status_code=404)
        agent._http_client.get = AsyncMock(return_value=resp)

        status, _, details = await agent._check_http(http_service)
        assert status == "degraded"
        assert details["status_code"] == 404

    @pytest.mark.asyncio
    async def test_http_5xx_is_critical(self, agent, http_service):
        resp = MagicMock(status_code=500)
        agent._http_client.get = AsyncMock(return_value=resp)

        status, _, details = await agent._check_http(http_service)
        assert status == "critical"
        assert details["status_code"] == 500

    @pytest.mark.asyncio
    async def test_http_timeout_is_unreachable(self, agent, http_service):
        agent._http_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        status, _, details = await agent._check_http(http_service)
        assert status == "unreachable"
        assert "timeout" in details["error"]

    @pytest.mark.asyncio
    async def test_http_connect_error_is_unreachable(self, agent, http_service):
        agent._http_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        status, ms, details = await agent._check_http(http_service)
        assert status == "unreachable"
        assert ms is None
        assert "connection refused" in details["error"]


# ---------------------------------------------------------------------------
# TCP checks
# ---------------------------------------------------------------------------


class TestCheckTcp:
    @pytest.mark.asyncio
    async def test_tcp_ok(self, agent, tcp_service):
        mock_writer = AsyncMock()
        mock_writer.close = MagicMock()
        mock_writer.wait_closed = AsyncMock()

        with patch("asyncio.wait_for", new_callable=AsyncMock) as wait_for:
            wait_for.return_value = (AsyncMock(), mock_writer)
            status, ms, details = await agent._check_tcp(tcp_service)

        assert status == "ok"
        assert isinstance(ms, int)

    @pytest.mark.asyncio
    async def test_tcp_timeout(self, agent, tcp_service):
        import asyncio

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            status, _, details = await agent._check_tcp(tcp_service)

        assert status == "unreachable"
        assert "timeout" in details["error"]

    @pytest.mark.asyncio
    async def test_tcp_refused(self, agent, tcp_service):
        with patch("asyncio.wait_for", side_effect=ConnectionRefusedError("refused")):
            status, ms, details = await agent._check_tcp(tcp_service)

        assert status == "unreachable"
        assert ms is None


# ---------------------------------------------------------------------------
# Systemd checks
# ---------------------------------------------------------------------------


class TestCheckSystemd:
    @pytest.mark.asyncio
    async def test_systemd_active(self, agent, systemd_service):
        with patch(
            "sysadmin.agents.sysadmin_agent.get_unit_status",
            new_callable=AsyncMock,
            return_value={"is_active": True, "ActiveState": "active"},
        ):
            status, ms, details = await agent._check_systemd(systemd_service)

        assert status == "ok"
        assert details["is_active"] is True

    @pytest.mark.asyncio
    async def test_systemd_activating(self, agent, systemd_service):
        with patch(
            "sysadmin.agents.sysadmin_agent.get_unit_status",
            new_callable=AsyncMock,
            return_value={"is_active": False, "ActiveState": "activating"},
        ):
            status, _, _ = await agent._check_systemd(systemd_service)

        assert status == "degraded"

    @pytest.mark.asyncio
    async def test_systemd_inactive_is_critical(self, agent, systemd_service):
        with patch(
            "sysadmin.agents.sysadmin_agent.get_unit_status",
            new_callable=AsyncMock,
            return_value={"is_active": False, "ActiveState": "inactive"},
        ):
            status, _, _ = await agent._check_systemd(systemd_service)

        assert status == "critical"

    @pytest.mark.asyncio
    async def test_systemd_error_is_unreachable(self, agent, systemd_service):
        with patch(
            "sysadmin.agents.sysadmin_agent.get_unit_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("dbus failed"),
        ):
            status, ms, details = await agent._check_systemd(systemd_service)

        assert status == "unreachable"
        assert ms is None


# ---------------------------------------------------------------------------
# Unknown check type
# ---------------------------------------------------------------------------


class TestCheckServiceDispatch:
    @pytest.mark.asyncio
    async def test_unknown_type(self, agent):
        svc = MonitoredService(name="mystery", type="grpc")
        status, ms, details = await agent._check_service(svc)
        assert status == "unreachable"
        assert "Unknown check type" in details["error"]


# ---------------------------------------------------------------------------
# Alerting logic (_handle_status)
# ---------------------------------------------------------------------------


class TestHandleStatus:
    @pytest.fixture
    def svc(self):
        return MonitoredService(name="svc", type="http", url="http://localhost/health")

    @pytest.fixture
    def auto_restart_svc(self):
        return MonitoredService(
            name="svc", type="systemd", systemd_unit="svc.service",
            auto_restart=True, auto_restart_after_checks=3,
        )

    @pytest.mark.asyncio
    async def test_ok_resets_degraded_count(self, agent, mock_session, svc):
        agent._degraded_counts["svc"] = 2
        alerts = await agent._handle_status(mock_session, svc, "ok", {})
        assert alerts == 0
        assert agent._degraded_counts["svc"] == 0

    @pytest.mark.asyncio
    async def test_degraded_increments(self, agent, mock_session, svc):
        agent._degraded_counts["svc"] = 0
        alerts = await agent._handle_status(mock_session, svc, "degraded", {})
        assert alerts == 0
        assert agent._degraded_counts["svc"] == 1

    @pytest.mark.asyncio
    async def test_three_degraded_escalates_to_warning(self, agent, mock_session, svc):
        agent._degraded_counts["svc"] = 2
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            alerts = await agent._handle_status(mock_session, svc, "degraded", {})
        assert alerts == 1
        ra.assert_called_once()
        assert ra.call_args.kwargs["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_critical_raises_alert(self, agent, mock_session, svc):
        with patch.object(agent, "raise_alert", new_callable=AsyncMock):
            alerts = await agent._handle_status(mock_session, svc, "critical", {})
        assert alerts == 1

    @pytest.mark.asyncio
    async def test_unreachable_raises_alert(self, agent, mock_session, svc):
        with patch.object(agent, "raise_alert", new_callable=AsyncMock):
            alerts = await agent._handle_status(mock_session, svc, "unreachable", {})
        assert alerts == 1

    @pytest.mark.asyncio
    async def test_warning_raises_alert(self, agent, mock_session, svc):
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            alerts = await agent._handle_status(mock_session, svc, "warning", {})
        assert alerts == 1
        ra.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_restart_after_threshold(self, agent, mock_session, auto_restart_svc):
        """Auto-restart triggers after N consecutive critical/unreachable checks."""
        agent._failure_counts["svc"] = 2  # Already 2 failures
        with (
            patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra,
            patch(
                "sysadmin.agents.sysadmin_agent.restart_unit",
                new_callable=AsyncMock,
                return_value=(True, "restarted"),
            ) as restart_mock,
        ):
            alerts = await agent._handle_status(
                mock_session, auto_restart_svc, "critical", {}
            )
        assert alerts == 1
        restart_mock.assert_called_once_with("svc.service")
        assert agent._failure_counts["svc"] == 0  # Reset after restart
        assert "auto-restarted" in ra.call_args.kwargs["title"]

    @pytest.mark.asyncio
    async def test_auto_restart_not_triggered_below_threshold(
        self, agent, mock_session, auto_restart_svc
    ):
        """Auto-restart should not trigger until threshold is met."""
        agent._failure_counts["svc"] = 0  # First failure
        with (
            patch.object(agent, "raise_alert", new_callable=AsyncMock),
            patch(
                "sysadmin.agents.sysadmin_agent.restart_unit",
                new_callable=AsyncMock,
            ) as restart_mock,
        ):
            await agent._handle_status(mock_session, auto_restart_svc, "critical", {})
        restart_mock.assert_not_called()
        assert agent._failure_counts["svc"] == 1

    @pytest.mark.asyncio
    async def test_non_controllable_skips_auto_restart(self, agent, mock_session):
        """Non-controllable services should not auto-restart even with auto_restart=True."""
        svc = MonitoredService(
            name="pg", type="systemd", systemd_unit="postgresql.service",
            controllable=False, auto_restart=True, auto_restart_after_checks=1,
        )
        agent._failure_counts["pg"] = 0
        with (
            patch.object(agent, "raise_alert", new_callable=AsyncMock),
            patch(
                "sysadmin.agents.sysadmin_agent.restart_unit",
                new_callable=AsyncMock,
            ) as restart_mock,
        ):
            await agent._handle_status(mock_session, svc, "critical", {})
        restart_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Resource snapshot
# ---------------------------------------------------------------------------


VMemory = namedtuple("VMemory", ["used", "total", "percent"])
SwapInfo = namedtuple("SwapInfo", ["used", "total", "percent"])
DiskUsage = namedtuple("DiskUsage", ["total", "used", "free", "percent"])
Partition = namedtuple("Partition", ["device", "mountpoint", "fstype", "opts"])


class TestResourceSnapshot:
    @pytest.mark.asyncio
    async def test_snapshot_fields(self, agent, mock_config):
        with (
            patch("sysadmin.agents.sysadmin_agent.psutil") as mock_psutil,
            patch("sysadmin.agents.sysadmin_agent.get_gpu_usage", new_callable=AsyncMock) as mock_gpu,
        ):
            mock_psutil.cpu_percent.return_value = 42.5
            mock_psutil.virtual_memory.return_value = VMemory(
                used=8 * 1024**3, total=16 * 1024**3, percent=50.0
            )
            mock_psutil.swap_memory.return_value = SwapInfo(
                used=1024**3, total=4 * 1024**3, percent=25.0
            )
            mock_psutil.getloadavg.return_value = (1.5, 2.0, 1.8)
            mock_psutil.disk_partitions.return_value = [
                Partition("/dev/sda1", "/", "ext4", "rw"),
            ]
            mock_psutil.disk_usage.return_value = DiskUsage(
                total=500 * 1024**3,
                used=400 * 1024**3,
                free=100 * 1024**3,
                percent=80.0,
            )
            mock_gpu.return_value = {
                "card0": {
                    "name": "Test GPU",
                    "gpu_percent": 30,
                    "temp_c": 65.0,
                    "vram_used_mb": 3000,
                    "vram_total_mb": 24000,
                    "vram_percent": 12.5,
                    "power_w": 80.0,
                }
            }

            snapshot = await agent._take_resource_snapshot(mock_config)

        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.cpu_percent == 42.5
        assert snapshot.ram_percent == 50.0
        assert snapshot.load_avg_1m == 1.5
        assert "/" in snapshot.disk_usage
        assert "card0" in snapshot.gpu_usage
        assert snapshot.gpu_usage["card0"]["gpu_percent"] == 30


# ---------------------------------------------------------------------------
# Threshold alerting
# ---------------------------------------------------------------------------


class TestCheckThresholds:
    @pytest.mark.asyncio
    async def test_high_ram_alerts(self, agent, mock_session):
        thresholds = Thresholds(ram_warning_percent=85)
        snapshot = ResourceSnapshot(
            cpu_percent=10, ram_percent=90, ram_used_mb=14000, ram_total_mb=16000,
            disk_usage={}, gpu_usage={},
        )
        with patch.object(agent, "raise_alert", new_callable=AsyncMock):
            alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1

    @pytest.mark.asyncio
    async def test_normal_ram_no_alert(self, agent, mock_session):
        thresholds = Thresholds(ram_warning_percent=85)
        snapshot = ResourceSnapshot(
            cpu_percent=10, ram_percent=50, ram_used_mb=8000, ram_total_mb=16000,
            disk_usage={}, gpu_usage={},
        )
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0

    @pytest.mark.asyncio
    async def test_disk_critical_alerts(self, agent, mock_session):
        thresholds = Thresholds(disk_warning_percent=80, disk_critical_percent=90)
        snapshot = ResourceSnapshot(
            cpu_percent=10, ram_percent=50, ram_used_mb=8000, ram_total_mb=16000,
            disk_usage={"/": {"percent": 95}}, gpu_usage={},
        )
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1
        # Should be critical, not just warning
        ra.assert_called_once()
        assert ra.call_args.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_disk_warning_alerts(self, agent, mock_session):
        thresholds = Thresholds(disk_warning_percent=80, disk_critical_percent=90)
        snapshot = ResourceSnapshot(
            cpu_percent=10, ram_percent=50, ram_used_mb=8000, ram_total_mb=16000,
            disk_usage={"/": {"percent": 85}}, gpu_usage={},
        )
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1
        ra.assert_called_once()
        assert ra.call_args.kwargs["severity"] == "warning"
