"""SysAdmin Agent — infrastructure health monitoring and resource tracking.

Checks:
- Service health via HTTP, TCP, or systemd
- CPU, RAM, disk, swap, load averages via psutil
- Port conflict detection

Alerting:
- OK → update DB, no notification
- DEGRADED → 3 consecutive = escalate to WARNING
- WARNING → log to alerts table
- CRITICAL → immediate alert (to be picked up by notifier)
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import psutil

from sysadmin.agents.base import AgentResult, BaseAgent
from sysadmin.config import AppConfig, MonitoredService, get_config
from sysadmin.models.resource_snapshot import ResourceSnapshot
from sysadmin.models.service_health import ServiceHealth
from sysadmin.utils.systemd import get_unit_status, is_active

logger = logging.getLogger(__name__)


class SysAdminAgent(BaseAgent):
    """Infrastructure health monitoring agent."""

    name = "sysadmin"

    def __init__(self) -> None:
        self._degraded_counts: dict[str, int] = {}
        self._http_client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        """Create shared HTTP client."""
        self._http_client = httpx.AsyncClient(timeout=10.0)

    async def shutdown(self) -> None:
        """Close shared HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def _execute(self, session) -> AgentResult:
        """Run all health checks and record resource snapshot."""
        config = get_config()
        agent_config = config.agents.sysadmin
        alerts_raised = 0

        # --- Service health checks ---
        for svc in agent_config.services:
            status, response_time_ms, details = await self._check_service(svc)

            # Record to DB
            health = ServiceHealth(
                service_name=svc.name,
                status=status,
                response_time_ms=response_time_ms,
                details=details,
            )
            session.add(health)

            # Alerting logic
            alerts_raised += await self._handle_status(
                session, svc.name, status, details
            )

        # --- Resource snapshot ---
        snapshot = self._take_resource_snapshot(config)
        session.add(snapshot)

        # Check resource thresholds
        alerts_raised += await self._check_thresholds(
            session, snapshot, agent_config.thresholds
        )

        return AgentResult(
            findings_count=len(agent_config.services),
            alerts_raised=alerts_raised,
            details={"services_checked": len(agent_config.services)},
        )

    # --- Service checks ---

    async def _check_service(
        self, svc: MonitoredService
    ) -> tuple[str, int | None, dict]:
        """Check a single service. Returns (status, response_time_ms, details)."""
        try:
            if svc.type == "http":
                return await self._check_http(svc)
            elif svc.type == "tcp":
                return await self._check_tcp(svc)
            elif svc.type == "systemd":
                return await self._check_systemd(svc)
            else:
                return "unreachable", None, {"error": f"Unknown check type: {svc.type}"}
        except Exception as e:
            logger.error(
                "service_check_error",
                extra={"service": svc.name, "error": str(e)},
            )
            return "unreachable", None, {"error": str(e)}

    async def _check_http(
        self, svc: MonitoredService
    ) -> tuple[str, int | None, dict]:
        """HTTP health check."""
        if not self._http_client:
            self._http_client = httpx.AsyncClient(timeout=10.0)

        start = time.monotonic()
        try:
            resp = await self._http_client.get(svc.url)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if resp.status_code == 200:
                # Slow response = degraded
                if elapsed_ms > 5000:
                    return "degraded", elapsed_ms, {"reason": "slow response"}
                return "ok", elapsed_ms, {}
            elif resp.status_code < 500:
                return "degraded", elapsed_ms, {"status_code": resp.status_code}
            else:
                return "critical", elapsed_ms, {"status_code": resp.status_code}
        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "unreachable", elapsed_ms, {"error": "timeout"}
        except httpx.ConnectError:
            return "unreachable", None, {"error": "connection refused"}

    async def _check_tcp(
        self, svc: MonitoredService
    ) -> tuple[str, int | None, dict]:
        """TCP connection check."""
        start = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(svc.host, svc.port),
                timeout=5.0,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            writer.close()
            await writer.wait_closed()
            return "ok", elapsed_ms, {}
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "unreachable", elapsed_ms, {"error": "timeout"}
        except (ConnectionRefusedError, OSError) as e:
            return "unreachable", None, {"error": str(e)}

    async def _check_systemd(
        self, svc: MonitoredService
    ) -> tuple[str, int | None, dict]:
        """Systemd unit status check."""
        start = time.monotonic()
        try:
            status_info = await get_unit_status(svc.systemd_unit)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if status_info.get("is_active"):
                return "ok", elapsed_ms, status_info
            elif status_info.get("ActiveState") == "activating":
                return "degraded", elapsed_ms, status_info
            else:
                return "critical", elapsed_ms, status_info
        except Exception as e:
            return "unreachable", None, {"error": str(e)}

    # --- Alerting logic ---

    async def _handle_status(
        self, session, service_name: str, status: str, details: dict
    ) -> int:
        """Handle status transitions and alerting. Returns count of alerts raised."""
        if status == "ok":
            self._degraded_counts[service_name] = 0
            # Resolve any existing alerts for this service
            await self.resolve_alerts(session, service_name)
            return 0

        if status == "degraded":
            self._degraded_counts[service_name] = (
                self._degraded_counts.get(service_name, 0) + 1
            )
            if self._degraded_counts[service_name] >= 3:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"{service_name} degraded",
                    message=f"{service_name} has been degraded for 3 consecutive checks",
                    details={**details, "service_name": service_name},
                )
                return 1
            return 0

        if status == "warning":
            self._degraded_counts[service_name] = 0
            await self.raise_alert(
                session,
                severity="warning",
                title=f"{service_name} warning",
                message=f"{service_name} is in warning state",
                details={**details, "service_name": service_name},
            )
            return 1

        if status in ("critical", "unreachable"):
            self._degraded_counts[service_name] = 0
            await self.raise_alert(
                session,
                severity="critical",
                title=f"{service_name} {'critical' if status == 'critical' else 'unreachable'}",
                message=f"{service_name} is {status}",
                details={**details, "service_name": service_name},
            )
            return 1

        return 0

    # --- Resource monitoring ---

    def _take_resource_snapshot(self, config: AppConfig) -> ResourceSnapshot:
        """Collect current system resource metrics."""
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load = psutil.getloadavg()

        # Disk usage per mount point
        disk_usage = {}
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_usage[part.mountpoint] = {
                    "total_gb": round(usage.total / (1024**3), 1),
                    "used_gb": round(usage.used / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent,
                }
            except (PermissionError, OSError):
                continue

        return ResourceSnapshot(
            cpu_percent=cpu,
            ram_used_mb=int(mem.used / (1024**2)),
            ram_total_mb=int(mem.total / (1024**2)),
            ram_percent=mem.percent,
            swap_used_mb=int(swap.used / (1024**2)),
            swap_total_mb=int(swap.total / (1024**2)),
            disk_usage=disk_usage,
            gpu_usage={},
            load_avg_1m=load[0],
            load_avg_5m=load[1],
            load_avg_15m=load[2],
        )

    async def _check_thresholds(
        self, session, snapshot: ResourceSnapshot, thresholds
    ) -> int:
        """Check resource thresholds and raise alerts. Returns alert count."""
        alerts = 0

        # RAM check
        if snapshot.ram_percent and float(snapshot.ram_percent) >= thresholds.ram_warning_percent:
            await self.raise_alert(
                session,
                severity="warning",
                title="High RAM usage",
                message=f"RAM at {snapshot.ram_percent}% (threshold: {thresholds.ram_warning_percent}%)",
                details={"ram_percent": float(snapshot.ram_percent)},
            )
            alerts += 1

        # Disk check
        for mount, usage in (snapshot.disk_usage or {}).items():
            pct = usage.get("percent", 0)
            if pct >= thresholds.disk_critical_percent:
                await self.raise_alert(
                    session,
                    severity="critical",
                    title=f"Critical disk usage on {mount}",
                    message=f"Disk at {pct}% on {mount} (threshold: {thresholds.disk_critical_percent}%)",
                    details={"mount": mount, "percent": pct},
                )
                alerts += 1
            elif pct >= thresholds.disk_warning_percent:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"High disk usage on {mount}",
                    message=f"Disk at {pct}% on {mount} (threshold: {thresholds.disk_warning_percent}%)",
                    details={"mount": mount, "percent": pct},
                )
                alerts += 1

        return alerts

    # --- Port detection ---

    @staticmethod
    def get_port_usage() -> list[dict[str, Any]]:
        """Get current port usage map (listening ports)."""
        ports = []
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr:
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    ports.append({
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                        "process": proc.name() if proc else None,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    ports.append({
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                        "process": None,
                    })
        return sorted(ports, key=lambda p: p["port"])
