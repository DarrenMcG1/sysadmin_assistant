"""Service Discovery Agent — find systemd units nothing is monitoring.

Tier 1 of Session 26.  Hand-registering every new project's units in
``services.yaml`` is tedious and rots silently: a unit that
was never wired looks exactly like one that is working, and a retired
project leaves units behind that fail on every start with nobody
watching.  This agent is the mechanical backstop for the contract in
``docs/guides/monitorable-project.md``.

The detection itself lives in :mod:`sysadmin.units.scan`, which is
pure.  This module is the thin part: read the config, run the sweep,
store the row, decide whether to alert.

**It never edits services.yaml.**  That file is hand-curated and its
comments carry reasoning that a rewriter would destroy.  The
advice (:mod:`sysadmin.units.recommendations`) hands the user a
snippet to paste.

**Two alert families, and the split is the point** (SNAG-ESTATE-001's
durable half).  ``ALERT_TITLE`` is the rolled-up count of everything
worth doing eventually — debt, re-raised only when the number moves.
``ARMED_TITLE_PREFIX`` is one row per *armed orphan*: a unit whose
project is gone and which systemd will nonetheless start.  They are
separate because the roll-up cannot name anything.  ``Unmonitored
systemd units: 17 findings`` was open, accurate and unread for eight
days while two of those seventeen restart-looped 52,178 times and
stalled the kernel — the detector had the diagnosis in plain English
the whole time, on a surface nobody opens.  ``GET /api/units/*`` stays
GET-only and advice-only; what changed is that the dangerous subset now
speaks without being fetched.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from estate.registry import load_registry
from sqlalchemy import select

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.core.escalation import Step, step_for
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.monitor.services import get_services
from sysadmin.units import ports as port_check
from sysadmin.units.models import UnitAudit
from sysadmin.units.recommendations import removal_command
from sysadmin.units.scan import (
    HOST,
    ORPHANED,
    UNMONITORED,
    ProjectRef,
    UnitFinding,
    scan_units,
    wired_units,
)

logger = logging.getLogger(__name__)

#: Substring used to find this agent's own rolled-up alert again.
ALERT_TITLE = "Unmonitored systemd units"

#: Title prefix for the per-unit armed-orphan family.  Kept clear of
#: ``sysadmin/monitor/agent.py``'s ``RESOLVABLE_TITLE_PATTERNS`` by
#: construction — those are all ``% <kind>`` suffixes (``% unreachable``,
#: ``% degraded``) and this is a prefix — though the scoping on
#: ``Alert.agent`` already makes these rows unreachable from that sweep.
#: Belt and braces, because the cost of being wrong is a row closed by a
#: second owner while it is still true.
ARMED_TITLE_PREFIX = "Orphaned unit still enabled"

#: Title prefix for the per-port collision family (Session 26c).  The
#: **port** is the identity, never the kind: two kinds landing on one
#: port are one thing to go and look at, and a title carrying the kind
#: would fork the row the day a second kind arrives for the same port.
#: Kept clear of ``sysadmin/monitor/agent.py``'s
#: ``RESOLVABLE_TITLE_PATTERNS`` by construction — those are ``% <kind>``
#: suffixes and this is a prefix ending in a number — on top of the
#: ``Alert.agent`` scoping that already makes these rows unreachable
#: from that sweep.
PORT_TITLE_PREFIX = "Port collision on"


def port_alert_title(port: int) -> str:
    """The stable identity of one contested port."""
    return f"{PORT_TITLE_PREFIX} {port}"


def armed_alert_title(finding: UnitFinding) -> str:
    """The stable identity of one armed orphan.

    **The unit name is in the title, and that is the whole change.**  The
    roll-up alert was open and correct for eight days
    (SNAG-ESTATE-001): ``Unmonitored systemd units: 17 findings`` said
    the estate had debt, while two of those seventeen were restart-looping
    at 1.3/min and had stalled the kernel.  A count cannot name the thing
    that is on fire.  The tray fingerprints on ``{severity}:{title}``, so
    a title carrying the unit is also what lets two armed orphans
    notify separately instead of one masking the other.

    Scope is part of the identity, never decoration:
    ``deadlock-api-ingest.service`` is installed in both scopes on this
    box running two different binaries, and a scope-blind title would
    let one unit's row answer for the other's fault.

    Raise, escalate and resolve all derive the title from here.  A
    hand-written resolve pattern that matches nothing is invisible — the
    rule ``ProjectOrganiserAgent._alert_title`` already encodes.
    """
    return f"{ARMED_TITLE_PREFIX}: {finding.unit} ({finding.scope})"


def armed_alert_severity(finding: UnitFinding) -> str:
    """How loud one armed orphan should be.

    ``critical`` is reserved for a fault that will not stop on its own.
    An armed orphan whose restart loop can never reach ``failed``
    (:func:`sysadmin.units.scan.restart_is_bounded`) is exactly that: it
    fails, restarts, fails, for ever, and because it never enters
    ``failed`` no ``OnFailure=`` can fire and ``systemctl is-failed``
    reports nothing wrong.  That is the invisible state Session 39 fixed
    on ``sysadmin.service`` and nowhere else.

    It is also the only severity ``sysadmin_tray/notifications.py``
    leaves on screen (``transient=False``).  The owner's reported failure
    in SNAG-ESTATE-001 was not being at the machine, and a transient
    toast in an empty room is the miss whatever its severity.

    An armed orphan that does *not* loop still fails on every trigger,
    which is news but not an emergency: ``warning``.
    """
    return "critical" if not finding.restart_bounded else "warning"


def armed_alert_message(finding: UnitFinding) -> str:
    """What the toast says, ending in the command that fixes it.

    The remedy comes from :func:`~sysadmin.units.recommendations.removal_command`
    rather than being written again here.  Two spellings of one fix drift,
    and this one has a trap worth not re-deriving: ``disable`` before
    ``rm``, because deleting the unit file first strands the enablement
    symlink and systemd warns about a dangling link on every
    ``daemon-reload`` afterwards.
    """
    return f"{finding.reason}. Fix: {removal_command(finding)}"


def armed_alert_details(finding: UnitFinding) -> dict[str, Any]:
    """Evidence for one armed orphan.

    ``restart_bounded`` is carried even though it is implicit in the
    severity: severity says how loud, this says *why*, and the reader
    of a resolved row six weeks later has only this.
    """
    return {
        "source": "unit_sweep",
        "unit": finding.unit,
        "scope": finding.scope,
        "path": finding.path,
        "category": finding.category,
        "enabled": finding.enabled,
        "restart": finding.restart,
        "restart_bounded": finding.restart_bounded,
        "dead_path": finding.dead_path,
        "project": finding.project,
        "project_path": finding.project_path,
        "remedy": removal_command(finding),
    }


class ServiceDiscoveryAgent(BaseAgent):
    """Cross-references installed systemd units against projects and config."""

    name = "service_discovery"

    async def _execute(self, session) -> AgentResult:
        config = get_config()
        agent_config = config.agents.service_discovery

        projects, aliases = await asyncio.to_thread(self._project_inputs, config)
        services = get_services().services
        wired = wired_units(services)

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

        # After the sweep: the port check consumes ``scan.unit_projects``,
        # which is the sweep's own answer to "who owns this unit".  A
        # second matcher here would drift in the direction where a port
        # is attributed to the wrong repository and nothing reports it.
        report = await asyncio.to_thread(
            self._check_ports, agent_config.ports, services, scan, aliases
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
            findings={**scan.as_findings_blob(), "ports": report.as_blob()},
        )
        session.add(audit)

        # Armed orphans first: the roll-up's message reports how many
        # of its findings are already speaking for themselves, and a
        # reader who sees only one of the two alerts should be able to
        # tell that the other exists.
        armed = await self._maintain_armed_alerts(session, scan)
        collisions = await self._maintain_port_alerts(session, report)
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
                "armed": armed["armed"],
                "restart_unbounded": len(scan.restart_findings),
                "port_findings": len(report.findings),
                "port_collisions": len(report.collisions),
                "ports_checked": report.ok,
            },
        )

        return AgentResult(
            findings_count=scan.actionable,
            alerts_raised=(
                alerts_raised
                + armed["raised"]
                + armed["escalated"]
                + collisions["raised"]
            ),
            details={
                "units_scanned": scan.units_scanned,
                "units_excluded": scan.units_excluded,
                "monitored": scan.monitored_count,
                "timers_folded": scan.timers_folded,
                "orphaned": scan.count(ORPHANED),
                "unmonitored": scan.count(UNMONITORED),
                "host": scan.count(HOST),
                # Not summed into ``findings_count`` above, which is
                # ``scan.actionable``: this family is latent risk in
                # units mostly already wired, and the roll-up alert's
                # threshold reads that number.  See ``_alert_details``.
                "restart_unbounded": len(scan.restart_findings),
                # Named ``standing`` for the reason SNAG-AGENT-006 gave
                # it that name on the sysadmin agent: with dedup in
                # place, ``alerts_raised`` reads 0 while a fault is still
                # true, so anything trending it needs the judged count
                # beside it to tell silence from suppression.
                "armed_standing": armed,
                # Same reason ``armed_standing`` carries the judged count
                # beside the raised one: with dedup in place a standing
                # collision reports ``raised: 0``, and silence has to be
                # tellable from suppression.
                "port_standing": collisions,
            },
        )

    async def _maintain_armed_alerts(self, session, scan) -> dict[str, int]:
        """One row per orphan systemd will actually start.

        **This family exists because the roll-up cannot name anything.**
        SNAG-ESTATE-001 is the whole argument: ``Unmonitored systemd
        units: 17 findings`` was open, accurate and unread for eight
        days while two of those findings restart-looped 52,178 times and
        stalled the kernel.  The diagnosis was complete and
        machine-readable; what no surface said was *which two of the
        seventeen were live*.  A count is not news.

        Deliberately **not** governed by ``alert_threshold``.  That knob
        is a patience setting for accumulated debt — twenty findings on a
        detector's first run should not shout — and an armed orphan is
        not debt, it is a unit failing on every trigger right now.  One
        of them is worth saying.

        Three rules, and the middle one is the opposite of the obvious
        implementation:

        1. **Deduplicated on the title, so a standing fault writes one
           row.** The sweep runs four times a day; the roll-up's own
           docstring records what happens without this.
        2. **The sweep's exclusion set is what this run *judged*, not
           what it *raised*** (SNAG-AGENT-006). Against a raised set, a
           deduplicating family writes nothing on run two, has its
           still-true row swept here, re-raises on run three — a
           flip-flop that clears the tray's ``{severity}:{title}``
           fingerprint every turn, so one fault notifies on every poll.
           Dedup suppresses the raise, never the judgement.
        3. **Escalation resolves the quiet row and raises a louder one**,
           never updates severity in place: the tray has already
           suppressed the fingerprint an in-place change would keep. It
           fires when a ``warning`` orphan gains an unbounded
           ``Restart=``. :func:`~sysadmin.core.escalation.step_for`
           refuses the reverse — a ``critical`` row is never quietly
           downgraded — so an orphan whose restart policy is *softened*
           stays loud until it is actually removed, which is the right
           way round for a unit that is still broken.

        Returns the standing counts for ``agent_runs.details``:
        ``alerts_raised`` reads 0 on a run where a known fault is still
        true, and that is its intended meaning rather than silence.
        """
        armed = scan.armed
        # Every armed orphan is judged, whether or not it is raised.
        judged = {armed_alert_title(f) for f in armed}

        open_rows = {
            row.title: row
            for row in (
                await session.execute(
                    select(Alert).where(
                        Alert.agent == self.name,
                        unresolved(),
                        Alert.title.like(f"{ARMED_TITLE_PREFIX}%"),
                    )
                )
            ).scalars()
        }

        raised = escalated = held = 0
        for finding in armed:
            title = armed_alert_title(finding)
            wanted = armed_alert_severity(finding)
            existing = open_rows.get(title)
            step = step_for(wanted, existing.severity if existing else None)

            if step is Step.HOLD:
                held += 1
                continue
            if step is Step.ESCALATE:
                await self.resolve_alerts(session, title)
                escalated += 1
            else:
                raised += 1

            await self.raise_alert(
                session,
                severity=wanted,
                title=title,
                message=armed_alert_message(finding),
                details=armed_alert_details(finding),
            )

        resolved = await self._resolve_disarmed(session, judged)
        return {
            "armed": len(armed),
            "raised": raised,
            "escalated": escalated,
            "held": held,
            "resolved": resolved,
        }

    async def _resolve_disarmed(self, session, judged: set[str]) -> int:
        """Close rows for orphans this sweep did not judge armed.

        Recovery here is any of four things and the statement does not
        care which: the unit was disabled, the unit was deleted, the
        project came back, or the sweep stopped classifying it as an
        orphan.  That is the ``_resolve_recovered`` argument the project
        and service sides both arrived at — a per-item loop can only
        observe recovery for items it still sees, and a deleted one is
        never seen again, which is how 1,664 and then 51,924 rows
        accumulated.

        Scoped to this agent's own rows and to this family's prefix, so
        the roll-up alert beside it is out of reach.  **One owner per
        lifecycle** is the rule those pile-ups keep restating.
        """
        from datetime import UTC, datetime

        from sqlalchemy import update

        conditions = [
            Alert.agent == self.name,
            unresolved(),
            Alert.title.like(f"{ARMED_TITLE_PREFIX}%"),
        ]
        if judged:
            conditions.append(Alert.title.notin_(sorted(judged)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        count: int = result.rowcount or 0
        if count:
            self._queue_event(
                "alert.resolved",
                {
                    "agent": self.name,
                    "match": f"{ARMED_TITLE_PREFIX} %",
                    "count": count,
                },
            )
            logger.info(
                "armed_orphan_alerts_resolved",
                extra={"agent": self.name, "count": count},
            )
        return count

    @staticmethod
    def _check_ports(
        ports_config, services, scan, aliases: dict[str, list[str]]
    ) -> "port_check.PortReport":
        """Observe the box's listeners and judge them against both registries.

        Runs in a worker thread: it shells out to ``ss`` and reads a
        markdown document from another repository, and this agent's
        event loop should not wait on either.

        **Every way of not-knowing produces a report carrying its
        reason and no findings**, never a clean sweep.  That matters
        more here than the usual because
        :meth:`_maintain_port_alerts` resolves on what this run judged:
        an empty success would close every open collision row on the
        strength of a document nobody managed to read.  The estate
        judge's rule 2, arriving from the other side.

        The registry half degrades on its own — an unreadable document
        costs the two document comparisons and leaves the two live ones
        working, because ``ss`` answered.  A missing document is not a
        missing box.
        """
        if not ports_config.enabled:
            return port_check.PortReport(error="port check disabled in config")

        document = Path(ports_config.document).expanduser()
        claims: list[port_check.PortClaim] = []
        registry_error: str | None = None
        try:
            claims = port_check.parse_port_registry(
                document.read_text(encoding="utf-8")
            )
        except OSError as exc:
            registry_error = f"could not read the port registry: {exc}"
        else:
            if not claims:
                # estate-manager's own rule: an empty parse is never a
                # conformant registry, it is a moved document or a
                # broken parser, and reporting "no duplicate rows" off
                # one would be the check quietly switching itself off.
                registry_error = (
                    f"port registry at {document} parsed to zero claimed rows"
                )
        if registry_error:
            logger.warning("port_registry_unreadable", extra={"error": registry_error})

        observed = port_check.observe_listeners()
        return port_check.judge_ports(
            observed,
            port_check.declared_ports(services),
            claims,
            scan.unit_projects,
            aliases,
            audited_ranges=[tuple(r) for r in ports_config.audited_ranges],
            ignore_ports=ports_config.ignore_ports,
            registry_document=str(document),
            registry_error=registry_error,
        )

    async def _maintain_port_alerts(self, session, report) -> dict[str, int]:
        """One row per contested port — the live half of Session 26c.

        Only :data:`~sysadmin.units.ports.COLLISION_KINDS` reach here.
        A duplicate registry row and a mis-attributed one are documents
        being wrong, which is debt and belongs in the ranked advice
        beside the orphan and restart tiers; ``wrong_unit`` and
        ``port_shared`` are the box disagreeing with itself *now* — a
        health check green against a process the tray's restart button
        would never touch.  That is the armed-orphan split applied a
        third time, and it is why ``COLLISION_KINDS`` lives in
        :mod:`sysadmin.units.ports` rather than here: the alert family
        and the advice family must not come to disagree about which
        findings are faults.

        **A run that could not observe judges nothing and sweeps
        nothing.**  ``report.ok`` is false when ``ss`` failed, and the
        resolve below is scoped to what this run judged — so treating a
        failed observation as an empty one would close every open row
        because nobody looked.

        Deduplicated on the title and swept on the **judged** set, not
        the raised one (SNAG-AGENT-006): against a raised set a
        deduplicating family writes nothing on run two, has its
        still-true row closed here, and re-raises on run three, clearing
        the tray's ``{severity}:{title}`` fingerprint on every turn.

        No escalation ladder, deliberately.  ``critical`` is what the
        tray leaves on screen and is reserved for a fault that is
        actively costing something; a port collision is loud enough at
        ``warning`` because it names a port and a unit, and this family
        has never had a member on this box — a ladder tuned against zero
        observations is a guess with a number on it.
        """
        if not report.ok:
            logger.warning("port_check_unavailable", extra={"error": report.error})
            return {"judged": 0, "raised": 0, "held": 0, "resolved": 0, "checked": False}

        by_port: dict[int, list[Any]] = {}
        for finding in report.collisions:
            by_port.setdefault(finding.port, []).append(finding)

        judged = {port_alert_title(port) for port in by_port}
        # ``select(Alert.title)`` yields the titles themselves, not rows.
        # Written as ``row.title`` first, which on a ``str`` silently
        # returns the bound ``str.title`` method rather than raising — so
        # every membership test failed and the family raised a duplicate
        # row on every sweep.  Caught by the dedup test, not by mypy.
        open_titles = set(
            (
                await session.execute(
                    select(Alert.title).where(
                        Alert.agent == self.name,
                        unresolved(),
                        Alert.title.like(f"{PORT_TITLE_PREFIX}%"),
                    )
                )
            ).scalars()
        )

        raised = held = 0
        for port in sorted(by_port):
            title = port_alert_title(port)
            if title in open_titles:
                held += 1
                continue
            # Worst kind first (``KIND_ORDER``), so the message describes
            # the more serious of two findings and ``kinds`` names both.
            findings = sorted(
                by_port[port], key=lambda f: port_check.KIND_ORDER.index(f.kind)
            )
            worst = findings[0]
            await self.raise_alert(
                session,
                severity="warning",
                title=title,
                message=worst.summary,
                details={
                    "port": port,
                    "kinds": [f.kind for f in findings],
                    "findings": [f.as_dict() for f in findings],
                    "source": "port_check",
                },
            )
            raised += 1

        resolved = await self._resolve_uncontested(session, judged)
        return {
            "judged": len(judged),
            "raised": raised,
            "held": held,
            "resolved": resolved,
            "checked": True,
        }

    async def _resolve_uncontested(self, session, judged: set[str]) -> int:
        """Close rows for ports this run did not judge contested.

        Recovery here is any of four things and the statement does not
        care which: the second listener stopped, ``services.yaml`` was
        corrected, the unit was renamed, or the port left the config
        entirely.  A per-port loop can only observe recovery for ports
        it still sees a finding for — and a port that stopped colliding
        produces no finding at all, which is exactly how the 1,664 and
        then 51,924 orphaned rows accumulated.
        """
        from datetime import UTC, datetime

        from sqlalchemy import update

        conditions = [
            Alert.agent == self.name,
            unresolved(),
            Alert.title.like(f"{PORT_TITLE_PREFIX}%"),
        ]
        if judged:
            conditions.append(Alert.title.notin_(sorted(judged)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        count: int = result.rowcount or 0
        if count:
            self._queue_event(
                "alert.resolved",
                {
                    "agent": self.name,
                    "match": f"{PORT_TITLE_PREFIX} %",
                    "count": count,
                },
            )
            logger.info(
                "port_collision_alerts_resolved",
                extra={"agent": self.name, "count": count},
            )
        return count

    @staticmethod
    def _project_inputs(config) -> tuple[list[ProjectRef], dict[str, list[str]]]:
        """Match targets and the names the estate might call each one by.

        One registry load for both.  ``aliases`` maps a project's
        directory name — the key ``scan_units`` reports in
        ``unit_projects`` — to every string that legitimately identifies
        it: the directory and the manifest id, which differ for a third
        of the repositories here (``SportsAnalyser`` /
        ``sports-analyser``).  Without it the port check would read a
        correct registry row as a mis-attribution on naming alone.
        """
        registry = ServiceDiscoveryAgent._registry(config)
        if registry is None:
            return [], {}
        refs = [
            ProjectRef(name=entry.path.name, path=str(entry.path), status=entry.status)
            for entry in registry.entries
        ]
        aliases = {
            entry.path.name: [entry.path.name]
            + ([entry.manifest.id] if entry.manifest else [])
            for entry in registry.entries
        }
        return refs, aliases

    @staticmethod
    def _registry(config):
        """The estate registry, or ``None`` when the projects root is gone."""
        organiser_config = config.agents.project_organiser
        root = Path(organiser_config.projects_root)
        if not root.exists():
            return None
        return load_registry(root, organiser_config.discovery_depth)

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
                    unresolved(),
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
            armed = len(scan.armed)
            # The count of armed orphans is repeated here on purpose.
            # They each have their own alert, and a reader looking at
            # this one needs to know the louder rows exist — otherwise
            # the roll-up reads as the complete picture, which is
            # exactly how SNAG-ESTATE-001 ran for eight days.
            live = f", {armed} of them enabled and failing now" if armed else ""
            parts.append(
                f"{scan.count(ORPHANED)} orphaned (project gone — these fail "
                f"on start{live})"
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

        ``restart_unbounded`` rides here as **evidence and nothing
        else** (SNAG-UNITS-002).  It is deliberately absent from
        ``actionable``, which is the number in this alert's title and the
        number ``alert_threshold`` is compared against: 13 latent risks
        added there would read as 13 new units to wire up and would trip
        the threshold on their own, turning a count of gaps into a count
        of two unrelated things.  It gets no family of its own for the
        reason the armed split was worth making — one row per unit is
        right for a fault in progress and wrong for a latent one, and 13
        rows on the first run is the pile-up shape wearing a new hat.
        The units are named by ``GET /api/units/actions``, which is where
        the fix lives.
        """
        return {
            "actionable": actionable,
            "orphaned": scan.count(ORPHANED),
            "armed": len(scan.armed),
            "unmonitored": scan.count(UNMONITORED),
            "host": scan.count(HOST),
            "units_scanned": scan.units_scanned,
            "monitored": scan.monitored_count,
            "restart_unbounded": len(scan.restart_findings),
            # Worst first, and capped — an alert body is read in a toast.
            "examples": [f.unit for f in scan.findings[:5]],
        }
