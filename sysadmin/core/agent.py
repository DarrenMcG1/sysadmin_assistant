"""BaseAgent — abstract base class for all scheduled agents.

Provides:
- Template method `run()` that records to `agent_runs`
- `raise_alert()` for writing alerts to the database
- Automatic timing and error handling
- Change events published to the event bus (fed to SSE clients)
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sysadmin.core.database import get_scheduler_session
from sysadmin.core.event_bus import event_bus
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.alert import Alert

logger = logging.getLogger(__name__)


class AgentResult:
    """Result from an agent execution."""

    def __init__(
        self,
        findings_count: int = 0,
        alerts_raised: int = 0,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.findings_count = findings_count
        self.alerts_raised = alerts_raised
        self.details = details or {}


class BaseAgent(ABC):
    """Abstract base class for all agents.

    Subclasses must implement:
    - `_execute(session)` — the actual work
    - `name` property — agent identifier
    """

    #: Events buffered during a run, published once the transaction commits.
    #: ``None`` means "not inside run()" — events then publish immediately.
    _pending_events: list[tuple[str, dict[str, Any]]] | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (matches check constraint values)."""
        ...

    @abstractmethod
    async def _execute(self, session) -> AgentResult:
        """Perform the agent's work. Override in subclasses."""
        ...

    def _queue_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Buffer a change event, or publish it now if no run is in progress.

        Events raised during a run are held until the run's transaction has
        committed — a client told "an alert was raised" must be able to see
        that alert when it refetches.
        """
        if self._pending_events is None:
            event_bus.publish_threadsafe(event_type, data)
        else:
            self._pending_events.append((event_type, data))

    def _flush_events(self) -> None:
        """Publish everything buffered during the run, then stop buffering."""
        pending, self._pending_events = self._pending_events or [], None
        for event_type, data in pending:
            event_bus.publish_threadsafe(event_type, data)

    async def run(self, run_type: str = "scheduled") -> None:
        """Template method: record run, execute, handle errors."""
        start = time.monotonic()
        started_at = datetime.now(UTC)
        self._pending_events = []

        async with get_scheduler_session() as session:
            # Record the run as started
            agent_run = AgentRun(
                agent=self.name,
                run_type=run_type,
                status="running",
                started_at=started_at,
            )
            session.add(agent_run)
            await session.flush()

            outcome = "failed"
            duration = 0.0

            try:
                result = await self._execute(session)
                duration = time.monotonic() - start
                outcome = "completed"

                # Update run record with results
                agent_run.status = "completed"
                agent_run.completed_at = datetime.now(UTC)
                agent_run.duration_seconds = round(duration, 2)
                agent_run.findings_count = result.findings_count
                agent_run.alerts_raised = result.alerts_raised
                agent_run.details = result.details

                logger.info(
                    "agent_run_completed",
                    extra={
                        "agent": self.name,
                        "run_type": run_type,
                        "duration_s": round(duration, 2),
                        "findings": result.findings_count,
                        "alerts": result.alerts_raised,
                    },
                )

            except Exception as e:
                duration = time.monotonic() - start
                agent_run.status = "failed"
                agent_run.completed_at = datetime.now(UTC)
                agent_run.duration_seconds = round(duration, 2)
                agent_run.details = {"error": str(e)}

                logger.exception(
                    "agent_run_failed",
                    extra={"agent": self.name, "run_type": run_type, "error": str(e)},
                )

        # Transaction has committed — safe to tell clients what changed.
        self._queue_event(
            "agent.run",
            {
                "agent": self.name,
                "run_type": run_type,
                "status": outcome,
                "duration_seconds": round(duration, 2),
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )
        self._flush_events()

    async def raise_alert(
        self,
        session,
        severity: str,
        title: str,
        message: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> Alert:
        """Write an alert to the database.

        For critical alerts, the notifier service should be called separately
        to POST to PersonalAssistant.
        """
        alert = Alert(
            agent=self.name,
            severity=severity,
            title=title,
            message=message,
            details=details or {},
        )
        session.add(alert)
        await session.flush()

        logger.warning(
            "alert_raised",
            extra={
                "agent": self.name,
                "severity": severity,
                "title": title,
            },
        )
        self._queue_event(
            "alert.raised",
            {
                "id": str(alert.id),
                "agent": self.name,
                "severity": severity,
                "title": title,
            },
        )
        return alert

    async def resolve_alerts(self, session, title_pattern: str) -> int:
        """Resolve all active alerts matching the given title pattern."""
        from sqlalchemy import update

        result = await session.execute(
            update(Alert)
            .where(
                Alert.agent == self.name,
                Alert.title.ilike(f"%{title_pattern}%"),
                Alert.resolved.is_(False),
            )
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        resolved: int = result.rowcount
        if resolved:
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": title_pattern, "count": resolved},
            )
        return resolved
