"""BaseAgent — abstract base class for all scheduled agents.

Provides:
- Template method `run()` that records to `agent_runs`
- `raise_alert()` for writing alerts to the database
- Automatic timing and error handling
- Change events published to the event bus (fed to SSE clients)
"""

import logging
import time
import uuid
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

    async def _record_start(self, run_type: str, started_at: datetime) -> uuid.UUID:
        """Commit the ``running`` row in a transaction of its own.

        Its own, because the previous arrangement inserted this row and
        then handed the *same* session to :meth:`_execute` — which opens
        a transaction and leaves it idle for as long as the agent's work
        takes.  This host sets ``idle_in_transaction_session_timeout`` to
        one minute (the rule ``files/review.py`` already records for LLM
        calls), so PostgreSQL terminated the backend under any agent
        whose work ran longer than that, and the run's every write —
        *including this row* — went down with it.

        That is SNAG-AGENT-003.  The file organiser scanned for 117.71 s
        on 2026-08-11, found 25,317 issues, and left no trace at all: no
        audit, no ``completed`` row, and no ``failed`` row either, because
        the record of the failure lived in the transaction the failure
        destroyed.  It read as an agent that had never been scheduled.
        The one run it *did* record, on 2026-08-06, took 29.63 s — the
        only one ever to finish inside the timeout.

        The id is generated client-side (``UUIDPrimaryKeyMixin`` sets
        ``default=uuid.uuid4``), so it is known here without a round trip
        and the outcome can be written from a different session later.
        """
        run_id = uuid.uuid4()
        async with get_scheduler_session() as session:
            session.add(
                AgentRun(
                    id=run_id,
                    agent=self.name,
                    run_type=run_type,
                    status="running",
                    started_at=started_at,
                )
            )
        return run_id

    async def _record_outcome(
        self,
        run_id: uuid.UUID,
        status: str,
        duration: float,
        findings_count: int,
        alerts_raised: int,
        details: dict[str, Any],
    ) -> None:
        """Close out the run's row, in a third short transaction.

        Separate from the work's session so that a failure *of* that
        session is still recordable — which is the whole point.  An
        ``UPDATE`` by id rather than a mutated ORM object, because the
        object belongs to a session that has already committed and closed.
        """
        from sqlalchemy import update

        async with get_scheduler_session() as session:
            await session.execute(
                update(AgentRun)
                .where(AgentRun.id == run_id)
                .values(
                    status=status,
                    completed_at=datetime.now(UTC),
                    duration_seconds=round(duration, 2),
                    findings_count=findings_count,
                    alerts_raised=alerts_raised,
                    details=details,
                )
            )

    async def run(self, run_type: str = "scheduled") -> AgentResult | None:
        """Template method: record run, execute, handle errors.

        Returns the result, or ``None`` if the run failed. The scheduler
        ignores it — the ``agent_runs`` row is the durable record — but a
        one-shot invocation needs something to turn into an exit code,
        and re-reading the row it just wrote to find out how it went
        would be a strange way to ask.

        **Three transactions, not one** — see :meth:`_record_start` for
        the fault that bought them.  Two consequences worth stating,
        because both are changes of meaning and not only of plumbing:

        1. ``_execute``'s writes are no longer atomic with the run
           record.  They are still atomic with *each other* — the session
           below rolls back as a unit — but a run that fails now leaves a
           ``failed`` row saying so, where before it left nothing.  The
           bookkeeping surviving the work it books is the improvement.
        2. A process killed mid-run leaves a permanent ``running`` row.
           Before it left no row at all, which is worse: an agent that
           died and an agent that was never scheduled looked identical,
           and that is precisely how this defect stayed invisible for
           five days.  ``GET /api/sysadmin/self`` reports it as the last
           status.

        ``duration`` is now measured after ``_execute``'s transaction
        commits rather than before, so it includes the commit — a slower
        number than the old one, and the honest one.
        """
        start = time.monotonic()
        started_at = datetime.now(UTC)
        self._pending_events = []
        outcome_result: AgentResult | None = None

        run_id = await self._record_start(run_type, started_at)

        outcome = "failed"
        duration = 0.0
        findings_count = 0
        alerts_raised = 0
        details: dict[str, Any] = {}

        try:
            async with get_scheduler_session() as session:
                result = await self._execute(session)

            duration = time.monotonic() - start
            outcome = "completed"
            outcome_result = result
            findings_count = result.findings_count
            alerts_raised = result.alerts_raised
            details = result.details

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
            details = {"error": str(e)}

            logger.exception(
                "agent_run_failed",
                extra={"agent": self.name, "run_type": run_type, "error": str(e)},
            )

        await self._record_outcome(
            run_id, outcome, duration, findings_count, alerts_raised, details
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
        return outcome_result

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
