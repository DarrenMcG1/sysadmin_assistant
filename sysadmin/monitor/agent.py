"""SysAdmin Agent — infrastructure health monitoring and resource tracking.

Checks:
- Service health via HTTP, TCP, or systemd
- CPU, RAM, disk, swap, load averages via psutil
- AMD GPU utilisation, temperature, VRAM via rocm-smi / sysfs
- Port conflict detection

- Resource anomalies (z-score against recent history, not just thresholds)
- Agent liveness — alerts when another agent silently stops running

Alerting:
- OK → update DB, no notification
- DEGRADED → 3 consecutive = escalate to WARNING
- WARNING → log to alerts table
- CRITICAL → immediate alert (to be picked up by notifier)
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import psutil
from sqlalchemy import select, update

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import AnomalyConfig, AppConfig, get_config
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.anomaly import DISK_KEY_PREFIX, Anomaly, detect_anomalies
from sysadmin.monitor.gpu import get_gpu_usage
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.monitor.self_monitor import build_self_report
from sysadmin.monitor.services import SKIPPED, ServiceEntry, check_plan, get_services
from sysadmin.monitor.systemd import SystemdQueryError, get_unit_status, restart_unit

logger = logging.getLogger(__name__)

#: Title prefix for stalled-agent alerts — also used to resolve them.
STALL_TITLE_SUFFIX = "agent stalled"

#: Timeout for HTTP health probes.
HTTP_CHECK_TIMEOUT_S = 10.0


def _stall_title(agent_name: str) -> str:
    return f"{agent_name} {STALL_TITLE_SUFFIX}"


#: Timer properties worth recording, under readable names.  ``systemctl
#: show`` returns microseconds-since-epoch as strings and "0" for "never",
#: neither of which is worth carrying into the details blob raw.
_TIMER_PROPS = {
    "LastTriggerUSec": "last_run",
    "NextElapseUSecRealtime": "next_run",
    "Result": "last_result",
}


def _timer_facts(props: dict) -> dict:
    """The last-run picture for a timer, from ``systemctl show`` output."""
    facts: dict = {}
    for prop, label in _TIMER_PROPS.items():
        raw = props.get(prop)
        if raw in (None, "", "0", "[not set]", "n/a"):
            continue
        facts[label] = raw
    facts["last_run_recorded"] = "last_run" in facts
    return facts


class SysAdminAgent(BaseAgent):
    """Infrastructure health monitoring agent."""

    name = "sysadmin"

    def __init__(self) -> None:
        self._degraded_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}
        # The HTTP client is owned by each run, never by the application —
        # runs happen on APScheduler threads under asyncio.run(), so a
        # client created once at startup would outlive its loop.
        self._http = LoopBoundClient(
            lambda: httpx.AsyncClient(timeout=HTTP_CHECK_TIMEOUT_S)
        )
        # Resource keys that fired a fixed-threshold alert this run — an
        # anomaly for the same resource would just be a duplicate.
        self._threshold_keys: set[str] = set()
        # Last known status per service, for service.status change events.
        self._last_status: dict[str, str] = {}

    async def _execute(self, session) -> AgentResult:
        """Run all health checks and record resource snapshot."""
        config = get_config()
        agent_config = config.agents.sysadmin
        services = get_services().services
        alerts_raised = 0

        # --- Service health checks ---
        # One connection pool per run, bound to this run's event loop and
        # closed when the block exits (SNAG-AGENT-003).
        async with self._http.scoped():
            for svc in services:
                status, response_time_ms, details = await self._check_service(svc)

                # Record to DB
                health = ServiceHealth(
                    service_name=svc.name,
                    status=status,
                    response_time_ms=response_time_ms,
                    details=details,
                )
                session.add(health)

                # Push a change event when a service flips state
                if self._last_status.get(svc.name) != status:
                    self._last_status[svc.name] = status
                    self._queue_event(
                        "service.status",
                        {"service": svc.name, "status": status},
                    )

                # Alerting logic (+ auto-restart)
                alerts_raised += await self._handle_status(
                    session, svc, status, details
                )

        # --- Resource snapshot ---
        snapshot = await self._take_resource_snapshot(config)

        # History is read BEFORE the new snapshot joins the session, so the
        # current reading is not part of its own baseline.
        history = await self._load_metric_history(session, agent_config.anomaly)

        session.add(snapshot)

        # Check resource thresholds
        alerts_raised += await self._check_thresholds(
            session, snapshot, agent_config.thresholds
        )

        # Statistical anomalies (skips resources that already alerted above)
        alerts_raised += await self._check_anomalies(
            session, snapshot, history, agent_config.anomaly
        )

        # Self-monitoring — has another agent silently stopped running?
        alerts_raised += await self._check_agent_liveness(session, config)

        checked = sum(1 for svc in services if not check_plan(svc).checks_nothing)
        return AgentResult(
            findings_count=len(services),
            alerts_raised=alerts_raised,
            details={"services_checked": checked, "services_declared": len(services)},
        )

    # --- Service checks ---

    async def _check_service(
        self, svc: ServiceEntry
    ) -> tuple[str, int | None, dict]:
        """Check one service, as its ``kind`` in services.yaml calls for.

        The plan comes from :func:`~sysadmin.monitor.services.check_plan`
        rather than from a chain of conditionals here, so "a oneshot is
        watched through its timer" is a property of the declaration and
        not of this function.
        """
        plan = check_plan(svc)
        if plan.checks_nothing:
            return SKIPPED, None, self._skip_details(svc)

        try:
            if plan.connect:
                return await self._check_tcp(svc)
            if plan.poll_url:
                return await self._check_http_and_unit(svc, plan)
            return await self._check_systemd(svc, inspect_timer=plan.inspect_timer)
        except Exception as e:
            logger.error(
                "service_check_error",
                extra={"service": svc.name, "error": str(e)},
            )
            return "unreachable", None, {"error": str(e)}

    @staticmethod
    def _skip_details(svc: ServiceEntry) -> dict:
        """Why a service was not checked, recorded with the skip.

        A ``skipped`` row with no explanation is only marginally better
        than no row, which is the option this replaced.
        """
        details: dict = {"kind": svc.kind, "monitored": svc.monitor}
        details["reason"] = svc.reason or (
            f"kind {svc.kind}: not expected to be running between invocations"
        )
        if svc.unit:
            details["unit"] = svc.unit
        return details

    async def _check_http_and_unit(
        self, svc: ServiceEntry, plan
    ) -> tuple[str, int | None, dict]:
        """Poll the URL, and assert the unit is active when one is named.

        A 200 from a URL says something answered, not that the unit this
        estate believes serves it is the thing that answered. Where a unit
        is declared, both must hold.

        The unit check **fails open**: a systemd query that cannot run
        yields the URL's own verdict rather than a failure. Treating an
        unreadable bus as a down service is precisely SNAG-SYSD-001, which
        flagged a live user timer as down for a week.
        """
        status, elapsed_ms, details = await self._check_http(svc)
        unit = svc.unit
        if not plan.assert_active or unit is None or status != "ok":
            return status, elapsed_ms, details

        try:
            unit_info = await get_unit_status(unit, user=svc.user)
        except SystemdQueryError as e:
            logger.warning(
                "unit_assertion_unavailable",
                extra={"service": svc.name, "unit": unit, "error": str(e)},
            )
            return status, elapsed_ms, {**details, "unit_check": "unavailable"}

        if unit_info.get("is_active"):
            return status, elapsed_ms, details
        if unit_info.get("ActiveState") == "activating":
            return "degraded", elapsed_ms, {
                **details, "reason": "url ok, unit still activating", **unit_info
            }
        return "degraded", elapsed_ms, {
            **details,
            "reason": f"url ok but {unit} is not active",
            **unit_info,
        }

    async def _check_http(
        self, svc: ServiceEntry
    ) -> tuple[str, int | None, dict]:
        """HTTP health check."""
        if not svc.url:
            return "error", None, {"error": "no url configured for http check"}

        start = time.monotonic()
        try:
            async with self._http.borrow() as client:
                resp = await client.get(svc.url)
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
        self, svc: ServiceEntry
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
        except TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "unreachable", elapsed_ms, {"error": "timeout"}
        except (ConnectionRefusedError, OSError) as e:
            return "unreachable", None, {"error": str(e)}

    async def _check_systemd(
        self, svc: ServiceEntry, inspect_timer: bool = False
    ) -> tuple[str, int | None, dict]:
        """Systemd unit status check.

        ``inspect_timer`` adds the timer's schedule to the recorded
        details. An armed timer is ``active (waiting)``, so the active
        test alone cannot tell a schedule that is about to fire from one
        whose last run failed — the properties say which.
        """
        if not svc.systemd_unit:
            return "error", None, {"error": "no systemd_unit configured for systemd check"}

        start = time.monotonic()
        try:
            status_info = await get_unit_status(svc.systemd_unit, user=svc.user)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if inspect_timer:
                status_info = {**status_info, **_timer_facts(status_info)}

            if status_info.get("is_active"):
                return "ok", elapsed_ms, status_info
            elif status_info.get("ActiveState") == "activating":
                return "degraded", elapsed_ms, status_info
            else:
                return "critical", elapsed_ms, status_info
        except SystemdQueryError as e:
            # systemctl could not be queried, so the unit's state is
            # *unknown* — reporting "critical" here is how a live user
            # timer got flagged as down (SNAG-SYSD-001). "error" says the
            # check failed and, unlike critical/unreachable, raises no
            # alert against the service itself.
            logger.warning(
                "systemd_check_unavailable",
                extra={
                    "service": svc.name,
                    "unit": svc.systemd_unit,
                    "error": str(e),
                },
            )
            return "error", None, {
                "unit": svc.systemd_unit,
                "error": str(e),
                "query_failed": True,
            }
        except Exception as e:
            return "unreachable", None, {"error": str(e)}

    # --- Alerting logic ---

    async def _handle_status(
        self, session, svc: ServiceEntry, status: str, details: dict
    ) -> int:
        """Handle status transitions, alerting, and auto-restart.

        Returns count of alerts raised.
        """
        service_name = svc.name

        if status == SKIPPED:
            # services.yaml says not to check this one.  Nothing was
            # measured, so there is nothing to alert on and nothing to
            # count — the same reasoning as "error" below, arrived at by
            # decision rather than by failure.
            return 0

        if status == "error":
            # The *check* failed (misconfigured, or systemctl could not be
            # queried), so nothing is known about the service.  Raise no
            # alert against it and leave the streak counters untouched —
            # an unmeasurable check is neither a success nor a failure.
            return 0

        if status == "ok":
            self._degraded_counts[service_name] = 0
            self._failure_counts[service_name] = 0
            # Resolve any existing alerts for this service
            await self.resolve_alerts(session, service_name)
            return 0

        if status == "degraded":
            self._failure_counts[service_name] = 0
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
            self._failure_counts[service_name] = 0
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

            # Track consecutive failures for auto-restart
            self._failure_counts[service_name] = (
                self._failure_counts.get(service_name, 0) + 1
            )

            # Auto-restart if enabled and threshold met
            if (
                svc.auto_restart
                and svc.controllable
                and svc.systemd_unit
                and self._failure_counts[service_name] >= svc.auto_restart_after_checks
            ):
                logger.info(
                    "auto_restart triggered for %s after %d consecutive failures",
                    service_name,
                    self._failure_counts[service_name],
                )
                success, msg = await restart_unit(svc.systemd_unit, user=svc.user)
                # Reset counter to avoid restart loop
                self._failure_counts[service_name] = 0

                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"{service_name} auto-restarted",
                    message=(
                        f"{service_name} was automatically restarted after "
                        f"{svc.auto_restart_after_checks} consecutive failures"
                        f" — {'succeeded' if success else f'failed: {msg}'}"
                    ),
                    details={**details, "service_name": service_name, "auto_restart": True},
                )
                return 1

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

    @staticmethod
    def _collect_resource_metrics() -> tuple[float, Any, Any, tuple, dict]:
        """Blocking psutil metric collection — run via asyncio.to_thread.

        ``cpu_percent(interval=1)`` sleeps for a full second, so this must
        never run directly on an event loop (SNAG-API-003).
        """
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

        return cpu, mem, swap, load, disk_usage

    async def _take_resource_snapshot(self, config: AppConfig) -> ResourceSnapshot:
        """Collect current system resource metrics including GPU."""
        cpu, mem, swap, load, disk_usage = await asyncio.to_thread(
            self._collect_resource_metrics
        )

        # GPU usage (AMD via rocm-smi / sysfs)
        try:
            gpu_usage = await get_gpu_usage()
        except Exception:
            logger.debug("gpu monitoring failed", exc_info=True)
            gpu_usage = {}

        return ResourceSnapshot(
            cpu_percent=cpu,
            ram_used_mb=int(mem.used / (1024**2)),
            ram_total_mb=int(mem.total / (1024**2)),
            ram_percent=mem.percent,
            swap_used_mb=int(swap.used / (1024**2)),
            swap_total_mb=int(swap.total / (1024**2)),
            disk_usage=disk_usage,
            gpu_usage=gpu_usage,
            load_avg_1m=load[0],
            load_avg_5m=load[1],
            load_avg_15m=load[2],
        )

    async def _check_thresholds(
        self, session, snapshot: ResourceSnapshot, thresholds
    ) -> int:
        """Check resource thresholds and raise alerts. Returns alert count.

        Also records the resource keys that alerted in ``_threshold_keys``
        so :meth:`_check_anomalies` can suppress duplicates.
        """
        alerts = 0
        self._threshold_keys = set()

        # RAM check
        if snapshot.ram_percent and float(snapshot.ram_percent) >= thresholds.ram_warning_percent:
            await self.raise_alert(
                session,
                severity="warning",
                title="High RAM usage",
                message=(
                    f"RAM at {snapshot.ram_percent}% "
                    f"(threshold: {thresholds.ram_warning_percent}%)"
                ),
                details={
                    "ram_percent": float(snapshot.ram_percent),
                    "resource": "ram",
                    "threshold": True,
                },
            )
            self._threshold_keys.add("ram")
            alerts += 1

        # GPU checks
        for card_id, gpu in (snapshot.gpu_usage or {}).items():
            gpu_name = gpu.get("name", card_id)
            temp = gpu.get("temp_c")
            if temp is not None and temp >= thresholds.gpu_temp_warning_c:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"High GPU temperature on {gpu_name}",
                    message=f"GPU temp at {temp}°C (threshold: {thresholds.gpu_temp_warning_c}°C)",
                    details={"card": card_id, "temp_c": temp},
                )
                alerts += 1

            vram_pct = gpu.get("vram_percent")
            if vram_pct is not None and vram_pct >= thresholds.gpu_vram_warning_percent:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"High VRAM usage on {gpu_name}",
                    message=(
                        f"VRAM at {vram_pct}% "
                        f"(threshold: {thresholds.gpu_vram_warning_percent}%)"
                    ),
                    details={"card": card_id, "vram_percent": vram_pct},
                )
                alerts += 1

        # Disk check
        for mount, usage in (snapshot.disk_usage or {}).items():
            pct = usage.get("percent", 0)
            disk_key = f"{DISK_KEY_PREFIX}{mount}"
            if pct >= thresholds.disk_critical_percent:
                await self.raise_alert(
                    session,
                    severity="critical",
                    title=f"Critical disk usage on {mount}",
                    message=(
                        f"Disk at {pct}% on {mount} "
                        f"(threshold: {thresholds.disk_critical_percent}%)"
                    ),
                    details={
                        "mount": mount,
                        "percent": pct,
                        "resource": disk_key,
                        "threshold": True,
                    },
                )
                self._threshold_keys.add(disk_key)
                alerts += 1
            elif pct >= thresholds.disk_warning_percent:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"High disk usage on {mount}",
                    message=(
                        f"Disk at {pct}% on {mount} "
                        f"(threshold: {thresholds.disk_warning_percent}%)"
                    ),
                    details={
                        "mount": mount,
                        "percent": pct,
                        "resource": disk_key,
                        "threshold": True,
                    },
                )
                self._threshold_keys.add(disk_key)
                alerts += 1

        return alerts

    # --- Anomaly detection ---

    @staticmethod
    def _snapshot_metrics(snapshot: ResourceSnapshot) -> dict[str, float]:
        """Current values keyed the same way as the history series."""
        metrics: dict[str, float] = {}
        if snapshot.cpu_percent is not None:
            metrics["cpu"] = float(snapshot.cpu_percent)
        if snapshot.ram_percent is not None:
            metrics["ram"] = float(snapshot.ram_percent)
        for mount, usage in (snapshot.disk_usage or {}).items():
            percent = usage.get("percent")
            if percent is not None:
                metrics[f"{DISK_KEY_PREFIX}{mount}"] = float(percent)
        return metrics

    async def _load_metric_history(
        self, session, config: AnomalyConfig
    ) -> dict[str, list[float]]:
        """Read the recent snapshot window as per-metric series."""
        if not config.enabled:
            return {}

        since = datetime.now(UTC) - timedelta(days=config.window_days)
        result = await session.execute(
            select(ResourceSnapshot).where(ResourceSnapshot.recorded_at >= since)
        )

        history: dict[str, list[float]] = {}
        for row in result.scalars().all():
            for key, value in self._snapshot_metrics(row).items():
                history.setdefault(key, []).append(value)
        return history

    async def _active_alerts(self, session) -> list[Alert]:
        """This agent's unresolved alerts (used for dedup/suppression)."""
        result = await session.execute(
            select(Alert).where(
                Alert.agent == self.name,
                Alert.resolved.is_(False),
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def _resolve_alert_ids(session, alert_ids: list[Any]) -> None:
        """Mark specific alerts resolved (used when a condition clears)."""
        if not alert_ids:
            return
        await session.execute(
            update(Alert)
            .where(Alert.id.in_(alert_ids))
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )

    async def _check_anomalies(
        self,
        session,
        snapshot: ResourceSnapshot,
        history: dict[str, list[float]],
        config: AnomalyConfig,
    ) -> int:
        """Raise alerts for statistically unusual resource readings.

        Suppression rules:
        - a resource that already fired a fixed-threshold alert (this run
          or still unresolved from an earlier one) is skipped — the
          threshold alert says the same thing more plainly
        - an unresolved anomaly alert for the same resource is not repeated
        - anomaly alerts are resolved once the resource is normal again
        """
        if not config.enabled:
            return 0

        anomalies = detect_anomalies(
            self._snapshot_metrics(snapshot), history, config
        )
        active = await self._active_alerts(session)

        threshold_keys = set(self._threshold_keys)
        anomaly_alerts: dict[str, Any] = {}
        for alert in active:
            details = alert.details or {}
            resource = details.get("resource")
            if not resource:
                continue
            if details.get("threshold"):
                threshold_keys.add(resource)
            elif details.get("anomaly"):
                anomaly_alerts[resource] = alert.id

        raised = 0
        flagged: set[str] = set()
        for anomaly in anomalies:
            flagged.add(anomaly.key)
            if anomaly.key in threshold_keys:
                logger.debug(
                    "anomaly_suppressed_by_threshold_alert",
                    extra={"resource": anomaly.key},
                )
                continue
            if anomaly.key in anomaly_alerts:
                continue  # already open — do not re-raise every run
            await self.raise_alert(
                session,
                severity=config.severity,
                title=self._anomaly_title(anomaly),
                message=(
                    f"{anomaly.label} at {anomaly.value:.1f}% is "
                    f"{abs(anomaly.z):.1f}σ {anomaly.direction} the "
                    f"{config.window_days}-day mean of {anomaly.mean:.1f}% "
                    f"(σ={anomaly.stdev:.1f}, n={anomaly.samples})"
                ),
                details=anomaly.as_details(),
            )
            raised += 1

        # Resolve anomaly alerts whose resource is back within normal range
        await self._resolve_alert_ids(
            session,
            [alert_id for key, alert_id in anomaly_alerts.items() if key not in flagged],
        )

        return raised

    @staticmethod
    def _anomaly_title(anomaly: Anomaly) -> str:
        return f"Unusual {anomaly.label} usage"

    # --- Self-monitoring ---

    async def _check_agent_liveness(self, session, config: AppConfig) -> int:
        """Alert when an agent has silently stopped running.

        Reuses the same report the ``/api/sysadmin/self`` endpoint serves,
        so the alert and the endpoint can never disagree. Alerts are
        deduplicated by title and resolved automatically once the agent
        runs again.
        """
        if not config.self_monitor.enabled:
            return 0

        report = await build_self_report(session, config)
        stalled = {a["name"]: a for a in report["agents"] if a["stalled"]}

        active = await self._active_alerts(session)
        open_stall_alerts = {
            alert.title: alert.id
            for alert in active
            if (alert.details or {}).get("stalled_agent")
        }

        raised = 0
        for name, entry in stalled.items():
            title = _stall_title(name)
            if title in open_stall_alerts:
                continue
            await self.raise_alert(
                session,
                severity="warning",
                title=title,
                message=(
                    f"The {name} agent has not run since "
                    f"{entry['last_run_at']} — {entry['stall_reason']}"
                ),
                details={
                    "stalled_agent": name,
                    "last_run_at": entry["last_run_at"],
                    "seconds_since_last_run": entry["seconds_since_last_run"],
                    "interval_seconds": entry["interval_seconds"],
                },
            )
            raised += 1

        # Agent came back — clear its stall alert
        await self._resolve_alert_ids(
            session,
            [
                alert_id
                for title, alert_id in open_stall_alerts.items()
                if title not in {_stall_title(name) for name in stalled}
            ],
        )

        return raised

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
