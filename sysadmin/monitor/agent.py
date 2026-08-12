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
from sysadmin.monitor import stalls
from sysadmin.monitor.anomaly import DISK_KEY_PREFIX, Anomaly, detect_anomalies
from sysadmin.monitor.gpu import get_gpu_usage
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.monitor.self_monitor import build_self_report
from sysadmin.monitor.services import SKIPPED, ServiceEntry, check_plan, get_services
from sysadmin.monitor.systemd import SystemdQueryError, get_unit_status, restart_unit

logger = logging.getLogger(__name__)

#: Title suffix for stalled-agent alerts. Re-exported from
#: :mod:`sysadmin.monitor.stalls`, which owns it along with the escalation
#: ladder — one definition, since raise, escalate and resolve all derive
#: their title from it and a resolve pattern that matches nothing fails
#: silently while the table grows.
STALL_TITLE_SUFFIX = stalls.STALL_TITLE_SUFFIX

#: Timeout for HTTP health probes.
HTTP_CHECK_TIMEOUT_S = 10.0

#: Every way :meth:`SysAdminAgent._handle_status` can name a service in an
#: alert title.  One tuple because raise and resolve both derive from it —
#: the rule :func:`sysadmin.projects.agent._alert_title` records, for the
#: reason a hand-written resolve pattern that matches nothing fails
#: silently while the table grows.
SERVICE_ALERT_KINDS = (
    "degraded",
    "warning",
    "critical",
    "unreachable",
    "auto-restarted",
)


def service_alert_title(service_name: str, kind: str) -> str:
    """The alert title for ``service_name`` being in state ``kind``."""
    return f"{service_name} {kind}"


def disk_alert_title(mount: str, critical: bool) -> str:
    """The alert title for disk occupancy on ``mount``."""
    return f"{'Critical' if critical else 'High'} disk usage on {mount}"


#: Alert families whose *recovery* this agent is responsible for observing.
#:
#: Written as ``LIKE`` patterns rather than derived from the configured
#: services, and that is the whole point of SNAG-AGENT-004: a set built
#: from configuration cannot contain a **deconfigured** service, so
#: ``redis unreachable`` — 6,283 rows, newest 2026-03-07 — could never be
#: matched by anything.  ``retention.run_retention`` purges resolved rows
#: only, so those rows were immortal.
#:
#: Two families are deliberately **absent**, because something else already
#: owns their lifecycle and a second owner is how a row gets closed while
#: still being true:
#:
#: - ``Unusual % usage`` — :meth:`SysAdminAgent._check_anomalies` resolves
#:   by alert id when the resource returns to range.
#: - ``% agent stalled`` — :mod:`sysadmin.monitor.stalls` owns the quiet →
#:   loud ladder, and its escalation *depends* on the quiet row staying
#:   open for ``escalate_after_hours``.
#: - ``% failed`` — :mod:`sysadmin.core.unit_failure` writes it while this
#:   application is dead and the lifespan resolves it on the next start.
#:   That pairing is what makes the row legitimate; resolving it from here
#:   would close it before anyone saw it.
RESOLVABLE_TITLE_PATTERNS = tuple(
    f"% {kind}" for kind in SERVICE_ALERT_KINDS
) + (
    # _check_thresholds — one per resource, and until now these had no
    # resolve path *at all*.  23,501 rows were open on 2026-08-12, 13,971
    # of them `Critical disk usage on /` last raised 2026-07-26, against a
    # disk that has been at 68 % since.  A condition that recovered and
    # could not be observed recovering is the same defect as a service
    # that was retired, so it is fixed by the same statement.
    "High RAM usage",
    "High GPU temperature on %",
    "High VRAM usage on %",
    "Critical disk usage on %",
    "High disk usage on %",
)

#: The stall-ladder outcome of a run that did nothing about stalls —
#: because ``self_monitor.enabled`` is false, or because no agent is
#: stalled. Zeroes rather than an absent key: ``"stalls": {}`` in
#: ``agent_runs.details`` reads as "the check did not run", which is the
#: exact confusion Session 39 exists to remove.
_NO_STALLS: dict[str, int] = {"stalled": 0, "raised": 0, "escalated": 0}


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
        # Stall ladder outcome for the current run. Reset per run rather
        # than accumulated: a stale count reported in agent_runs.details
        # would read as an escalation that this run performed.
        self._stall_counts: dict[str, int] = _NO_STALLS
        # Exact alert titles raised by the current run — the "still
        # failing" set _resolve_recovered subtracts. Collected in
        # raise_alert rather than at the ten call sites, so it cannot
        # drift from them.
        self._raised_titles: set[str] = set()

    async def raise_alert(
        self,
        session,
        severity: str,
        title: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> Alert:
        """Raise as normal, and remember the title for :meth:`_resolve_recovered`.

        The inverse question that method asks — "which of my open alerts
        did this run *not* raise?" — needs the run's titles exactly, and
        the one place they all pass through is here.  Titles outside
        :data:`RESOLVABLE_TITLE_PATTERNS` (anomalies, stalls) are
        collected too and are simply never matched, which is cheaper than
        a second rule about which ones to collect.
        """
        self._raised_titles.add(title)
        return await super().raise_alert(session, severity, title, message, details)

    async def _execute(self, session) -> AgentResult:
        """Run all health checks and record resource snapshot."""
        self._stall_counts = _NO_STALLS
        self._raised_titles = set()
        config = get_config()
        agent_config = config.agents.sysadmin
        services = get_services().services
        alerts_raised = 0
        # Configured services this run did not measure as healthy. Their
        # open alerts are protected from the resolve below — see
        # _resolve_recovered.
        unhealthy: set[str] = set()

        # --- Service health checks ---
        # One connection pool per run, bound to this run's event loop and
        # closed when the block exits (SNAG-AGENT-003).
        async with self._http.scoped():
            for svc in services:
                status, response_time_ms, details = await self._check_service(svc)
                if status not in ("ok", SKIPPED):
                    unhealthy.add(svc.name)

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

        # Everything this run measured and did not alert on has recovered.
        alerts_resolved = await self._resolve_recovered(session, unhealthy)

        checked = sum(1 for svc in services if not check_plan(svc).checks_nothing)
        return AgentResult(
            findings_count=len(services),
            alerts_raised=alerts_raised,
            details={
                "services_checked": checked,
                "services_declared": len(services),
                "alerts_resolved": alerts_resolved,
                # Recorded so a run that escalated an existing stall is
                # distinguishable from one that found a new one — the two
                # sum into `alerts_raised` and mean different things.
                "stalls": self._stall_counts,
            },
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
            # No resolve here. It used to call
            # `resolve_alerts(session, service_name)` — a substring
            # `ilike`, so `venture-chat` recovering also closed
            # `venture-chat-large`'s alerts — and, being inside the loop
            # over *configured* services, it could only ever observe a
            # service that was still being checked. `_resolve_recovered`
            # at the end of the run asks the inverse question instead.
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
                    title=service_alert_title(service_name, "degraded"),
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
                title=service_alert_title(service_name, "warning"),
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
                    title=service_alert_title(service_name, "auto-restarted"),
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
                title=service_alert_title(service_name, status),
                message=f"{service_name} is {status}",
                details={**details, "service_name": service_name},
            )
            return 1

        return 0

    # --- Alert recovery ---

    async def _resolve_recovered(self, session, unhealthy: set[str]) -> int:
        """Resolve every owned alert this run did **not** raise.

        The service-side twin of
        :meth:`sysadmin.projects.agent.ProjectOrganiserAgent._resolve_recovered`,
        and the same defect at sixteen times the scale (SNAG-AGENT-004).
        Recovery used to be observed one service at a time, inside the
        loop over the *configured* services — so a service removed from
        configuration was never checked again, could never be seen to
        recover, and its alerts stayed open for ever.  ``run_retention``
        purges ``resolved = TRUE`` rows only, deliberately, so nothing
        else was ever going to clear them.

        Live on 2026-08-12, before this ran: **27,827** unresolved rows
        for five services that no longer exist in either config file
        (``personal-assistant`` 9,748, ``personal-assistant-frontend``
        9,748, ``redis`` 6,283, ``ollama`` 1,824, ``nuxt-frontend`` 224),
        and **23,501** more for resource thresholds that had no resolve
        path at any point in this application's life.

        Asking the inverse question closes retirement, rename, recovery
        and threshold-cleared in one statement, and cannot drift from the
        raise path: the population comes from
        :data:`RESOLVABLE_TITLE_PATTERNS` and the exclusions from
        :attr:`_raised_titles`, which :meth:`raise_alert` fills.

        **The two halves take different exclusions, and the difference is
        not cosmetic.** A resource threshold either breached this run or
        did not, so ``_raised_titles`` decides it exactly.  A service's
        alert is governed by a *streak* — three consecutive degraded
        checks — held in memory, and ``_degraded_counts`` resets when the
        daemon restarts.  Testing "did this run raise it?" would therefore
        close a genuinely-degraded service's alert on the first run after
        every restart and re-raise it two checks later: a spurious
        recovery, announced to the tray, for a fault that never went away.
        So a service's titles are resolved only when this run measured it
        **healthy** — ``unhealthy`` carries everything else, including
        ``error``, where the check itself failed and the state is
        genuinely unknown.

        ``skipped`` counts as healthy for this purpose, and deliberately.
        It means ``services.yaml`` declares ``monitor: false``: the estate
        has said it does not want to know, and an open critical that
        nothing will ever look at again is the pile-up wearing a
        declaration as an excuse.

        A **deconfigured** service is in neither set — it is not in the
        loop at all — so its rows fall through to the resolve.  That is
        the fix, and it is why the population must be pattern-based.

        Titles are excluded by exact match, never by "created before
        now": the rows raised moments ago are in this same transaction
        and a timestamp comparison races the clock that stamped them.

        Returns:
            Number of alerts resolved.
        """
        from sqlalchemy import or_

        protected = self._raised_titles | {
            service_alert_title(name, kind)
            for name in unhealthy
            for kind in SERVICE_ALERT_KINDS
        }

        conditions = [
            Alert.agent == self.name,
            Alert.resolved.is_(False),
            or_(*[Alert.title.like(p) for p in RESOLVABLE_TITLE_PATTERNS]),
        ]
        if protected:
            conditions.append(Alert.title.notin_(sorted(protected)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "service_alerts_resolved",
                extra={"agent": self.name, "count": resolved},
            )
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": "recovered", "count": resolved},
            )
        return resolved

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
                    title=disk_alert_title(mount, critical=True),
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
                    title=disk_alert_title(mount, critical=False),
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
        """Alert when an agent has silently stopped running, and keep saying so.

        Reuses the same report the ``/api/sysadmin/self`` endpoint serves,
        so the alert and the endpoint can never disagree. Detection is
        unchanged since it was written and was never the gap — see
        :mod:`sysadmin.monitor.stalls` for the Session 39 evidence that it
        caught ``SNAG-AGENT-003`` correctly and then went quiet.

        What is decided *here* is the alert lifecycle, and it now has three
        outcomes rather than two:

        - **Raise** — first detection, at :attr:`STALL_LADDER.quiet`.
        - **Escalate** — the warning has stood ``escalate_after_hours``
          unresolved. The quiet row is **resolved and a louder one
          inserted**, never updated in place: the tray fingerprints on
          ``"{severity}:{title}"``, so an in-place severity change keeps
          the fingerprint it has already suppressed and the escalation is
          recorded but never spoken.
        - **Hold** — a row at that severity or louder is already open.
          This is the branch that stopped the 1,664-row pile-up and it
          stays exactly as it was.

        Recovery still resolves the row outright, and deliberately does not
        walk back down the rungs: an agent that ran again is not a quieter
        fault, it is not a fault.

        Returns:
            Rows written — raises *and* escalations, since both are an
            alert this run produced. ``details["stalls"]`` breaks them
            down, so a run that only escalated is distinguishable from one
            that found a new stall.
        """
        if not config.self_monitor.enabled:
            return 0

        report = await build_self_report(session, config)
        stalled = {a["name"]: a for a in report["agents"] if a["stalled"]}

        active = await self._active_alerts(session)
        # Keyed by the *stalled agent*, from details rather than by parsing
        # the title back apart. Rows raised before Session 39 carry the
        # same key, so an alert already open when this deployed is found
        # and escalated rather than duplicated.
        open_stalls: dict[str, tuple[Any, stalls.OpenStall]] = {}
        for alert in active:
            name = (alert.details or {}).get(stalls.STALL_DETAIL_KEY)
            if not name:
                continue
            open_stalls[name] = (
                alert,
                stalls.OpenStall(
                    alert_id=alert.id,
                    severity=alert.severity,
                    created_at=alert.created_at,
                ),
            )

        due = stalls.evaluate(
            list(stalled.values()),
            {name: entry[1] for name, entry in open_stalls.items()},
            escalate_after_hours=config.self_monitor.escalate_after_hours,
        )

        raised = 0
        escalated = 0
        for item in due:
            if item.step is stalls.Step.ESCALATE:
                quiet_row = open_stalls[item.agent_name][0]
                quiet_row.resolved = True
                quiet_row.resolved_at = datetime.now(UTC)
                escalated += 1
            else:
                raised += 1
            await self.raise_alert(
                session,
                severity=item.severity,
                title=item.title,
                message=item.message,
                details=item.details,
            )

        # Agent came back — clear its stall alert. Read from open_stalls
        # rather than recomputing titles, so this cannot drift from the
        # lookup above.
        await self._resolve_alert_ids(
            session,
            [
                entry[1].alert_id
                for name, entry in open_stalls.items()
                if name not in stalled
            ],
        )

        self._stall_counts = {
            "stalled": len(stalled),
            "raised": raised,
            "escalated": escalated,
        }
        return raised + escalated

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
