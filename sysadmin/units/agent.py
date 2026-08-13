"""Service Discovery Agent — find systemd units nothing is monitoring.

Tier 1 of Session 26.  Hand-registering every new project's units in
projects.yaml or config.yaml is tedious and rots silently: a unit that
was never wired looks exactly like one that is working, and a retired
project leaves units behind that fail on every start with nobody
watching.  This agent is the mechanical backstop for the contract in
``docs/guides/monitorable-project.md``.

The detection itself lives in :mod:`sysadmin.units.scan`, which is
pure.  This module is the thin part: read the config, run the sweep,
store the row, decide whether to alert.

**It never edits projects.yaml or config.yaml.**  Both are hand-curated
and their comments carry reasoning that a rewriter would destroy.  The
advice (:mod:`sysadmin.units.recommendations`) hands the user a
snippet to paste.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from sqlalchemy import select

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.services import get_services
from estate.registry import load_registry
from sysadmin.units.models import UnitAudit
from sysadmin.units.scan import (
    HOST,
    ORPHANED,
    UNMONITORED,
    ProjectRef,
    scan_units,
    wired_units,
)

logger = logging.getLogger(__name__)

#: Substring used to find this agent's own rolled-up alert again.
ALERT_TITLE = "Unmonitored systemd units"


class ServiceDiscoveryAgent(BaseAgent):
    """Cross-references installed systemd units against projects and config."""

    name = "service_discovery"

    async def _execute(self, session) -> AgentResult:
        config = get_config()
        agent_config = config.agents.service_discovery

        projects = await asyncio.to_thread(self._project_refs, config)
        wired = wired_units(get_services().services)

        user_dir = Path(agent_config.user_unit_dir).expanduser()
        system_dir = Path(agent_config.system_unit_dir)

        scan = await asyncio.to_thread(
            scan_units,
            user_dir,
            system_dir,
            str(Path.home()),
            projects,
            wired,
        )

        audit = UnitAudit(
            user_unit_dir=str(user_dir),
            system_unit_dir=str(system_dir),
            units_scanned=scan.units_scanned,
            units_excluded=scan.units_excluded,
            monitored_count=scan.monitored_count,
            timers_folded=scan.timers_folded,
            orphaned_count=scan.count(ORPHANED),
            unmonitored_count=scan.count(UNMONITORED),
            host_count=scan.count(HOST),
            findings=scan.as_findings_blob(),
        )
        session.add(audit)

        alerts_raised = await self._maintain_alert(
            session, scan.actionable, agent_config.alert_threshold, scan
        )

        logger.info(
            "unit_sweep_complete",
            extra={
                "scanned": scan.units_scanned,
                "monitored": scan.monitored_count,
                "orphaned": scan.count(ORPHANED),
                "unmonitored": scan.count(UNMONITORED),
                "host": scan.count(HOST),
            },
        )

        return AgentResult(
            findings_count=scan.actionable,
            alerts_raised=alerts_raised,
            details={
                "units_scanned": scan.units_scanned,
                "units_excluded": scan.units_excluded,
                "monitored": scan.monitored_count,
                "timers_folded": scan.timers_folded,
                "orphaned": scan.count(ORPHANED),
                "unmonitored": scan.count(UNMONITORED),
                "host": scan.count(HOST),
            },
        )

    @staticmethod
    def _project_refs(config) -> list[ProjectRef]:
        """The projects to match units against, from the registry.

        Read from disk rather than from ``project_snapshots``. Reading the
        table would make this agent silently useless until the organiser
        had run once — and worse than useless, because with no projects to
        match, *every* unit classifies as an orphan or a host unit.

        Both agents now go through :func:`estate.registry.load_registry`,
        so there is one definition of "a project" rather than two that can
        drift. The symptom of drift here would be units reported as
        orphans because this sweep could not see the project they belong
        to.
        """
        organiser_config = config.agents.project_organiser
        root = Path(organiser_config.projects_root)
        if not root.exists():
            return []

        registry = load_registry(root, organiser_config.discovery_depth)
        return [
            ProjectRef(name=entry.path.name, path=str(entry.path), status=entry.status)
            for entry in registry.entries
        ]

    async def _maintain_alert(
        self, session, actionable: int, threshold: int, scan
    ) -> int:
        """One rolled-up alert, re-raised only when the count changes.

        ``raise_alert`` inserts unconditionally, so a naive "over
        threshold → alert" would add a row on every sweep — four a day at
        the default interval, forever.  That is SNAG-AGENT-002 (the log
        aggregator raising one alert per error line) in a new costume.

        So: below the threshold, resolve anything outstanding.  Above it,
        raise only if there is no live alert or the count has moved —
        going from 18 findings to 19 is news, seeing the same 18 again is
        not.
        """
        if threshold <= 0 or actionable < threshold:
            await self.resolve_alerts(session, ALERT_TITLE)
            return 0

        existing = (
            await session.execute(
                select(Alert).where(
                    Alert.agent == self.name,
                    Alert.title.ilike(f"%{ALERT_TITLE}%"),
                    Alert.resolved.is_(False),
                )
            )
        ).scalars().first()

        if existing is not None:
            previous = (existing.details or {}).get("actionable")
            if previous == actionable:
                return 0
            await self.resolve_alerts(session, ALERT_TITLE)

        await self.raise_alert(
            session,
            severity="warning",
            title=f"{ALERT_TITLE}: {actionable} findings",
            message=self._alert_message(scan),
            details=self._alert_details(scan, actionable),
        )
        return 1

    @staticmethod
    def _alert_message(scan) -> str:
        parts = []
        if scan.count(ORPHANED):
            parts.append(
                f"{scan.count(ORPHANED)} orphaned (project gone — these fail on start)"
            )
        if scan.count(UNMONITORED):
            parts.append(f"{scan.count(UNMONITORED)} unmonitored project units")
        if scan.count(HOST):
            parts.append(f"{scan.count(HOST)} host units with no project")
        return (
            ", ".join(parts)
            + f". {scan.monitored_count} of {scan.units_scanned} units are wired. "
            "See GET /api/units/actions for snippets."
        )

    @staticmethod
    def _alert_details(scan, actionable: int) -> dict[str, Any]:
        """Alert payload.

        ``actionable`` is stored so the next sweep can tell "the same
        problem" from "a new one" without re-deriving it from the
        findings blob, which is truncated.
        """
        return {
            "actionable": actionable,
            "orphaned": scan.count(ORPHANED),
            "unmonitored": scan.count(UNMONITORED),
            "host": scan.count(HOST),
            "units_scanned": scan.units_scanned,
            "monitored": scan.monitored_count,
            # Worst first, and capped — an alert body is read in a toast.
            "examples": [f.unit for f in scan.findings[:5]],
        }
