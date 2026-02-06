"""BaseAgent — abstract base class for all scheduled agents.

Provides:
- Template method `run()` that records to `agent_runs`
- `raise_alert()` for writing alerts to the database
- Automatic timing and error handling
"""

import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from sysadmin.database import get_scheduler_session
from sysadmin.models.agent_run import AgentRun
from sysadmin.models.alert import Alert

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

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (matches check constraint values)."""
        ...

    @abstractmethod
    async def _execute(self, session) -> AgentResult:
        """Perform the agent's work. Override in subclasses."""
        ...

    async def run(self, run_type: str = "scheduled") -> None:
        """Template method: record run, execute, handle errors."""
        start = time.monotonic()
        started_at = datetime.now(timezone.utc)

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
            run_id = agent_run.id

            try:
                result = await self._execute(session)
                duration = time.monotonic() - start

                # Update run record with results
                agent_run.status = "completed"
                agent_run.completed_at = datetime.now(timezone.utc)
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
                agent_run.completed_at = datetime.now(timezone.utc)
                agent_run.duration_seconds = round(duration, 2)
                agent_run.details = {"error": str(e)}

                logger.exception(
                    "agent_run_failed",
                    extra={"agent": self.name, "run_type": run_type, "error": str(e)},
                )

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
            .values(resolved=True, resolved_at=datetime.now(timezone.utc))
        )
        return result.rowcount
