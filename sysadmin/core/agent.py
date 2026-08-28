"""BaseAgent — abstract base class for all scheduled agents.

Provides:
- Template method `run()` that records to `agent_runs`
- `raise_alert()` for writing alerts to the database
- `refresh_alert()` for keeping a deduplicated row's text true
- Automatic timing and error handling
- Change events published to the event bus (fed to SSE clients)
"""

import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sysadmin.core.database import get_scheduler_session
from sysadmin.core.event_bus import event_bus
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.alert import Alert, unresolved

logger = logging.getLogger(__name__)

#: The log event :meth:`BaseAgent.run` writes when ``_execute`` raises.
#:
#: A constant rather than a literal because it is read **twice** and the
#: two readers must not be able to disagree: this module emits it, and
#: :data:`sysadmin.monitor.log_aggregator.COVERED_SIGNATURES` keys on it
#: to stop the journal family raising a second alert for a fault
#: :mod:`sysadmin.monitor.failures` already owns (``SNAG-LOG-005``).
#: ``max_priority_for`` against ``PRIORITY_MAP`` and ``chk_alert_agent``
#: against ``AGENT_NAMES`` are the same rule: derive, never write beside.
#:
#: It is also the *signature* of that fault, not merely its text —
#: :func:`~sysadmin.monitor.log_signature.signature` is the identity the
#: journal family deduplicates on, and it maps digit runs to ``N``.  This
#: string contains no digits, so the two coincide; a test pins that,
#: because renaming this event to something with a number in it would
#: silently unkey the exclusion rather than break it.
AGENT_RUN_FAILED_EVENT = "agent_run_failed"


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
                AGENT_RUN_FAILED_EVENT,
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

    @staticmethod
    def refresh_alert(
        alert: Alert,
        *,
        message: str | None,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Bring a held row's text up to date, and only if it has moved.

        ``SNAG-AGENT-009``.  Every family that deduplicates on an open
        title takes a ``held`` branch and moves on, so ``alert.message``
        stays whatever the **first** run wrote.  :attr:`Alert.title` is
        the identity and must not move — that is settled, and Session 42
        settled it — but the message is the sentence a reader acts on and
        nothing was keeping it true.  Measured across the 23 post-dedup
        ``High VRAM usage`` rows on this box: **42 of 42** polls that fell
        inside a hold carried a figure different from the frozen one, mean
        absolute drift 8.15 pp, and **19 of the 42 read below the very
        threshold the message was asserting**.

        Five rules, three of them the opposite of the obvious
        implementation:

        1. **``message`` and ``details`` move together, always.**  The
           entry was filed against the message alone; driving it showed
           ``details`` is frozen by the identical ``continue``, so a fix
           that moved only the sentence would leave half the row lying —
           the ports drive kept a ``findings`` blob naming a unit that had
           not held the port for hours.  One write, not a cheaper one.
        2. **The gate is "the text differs", and it is a floor rather
           than a promise of quiet.**  For a family whose ``details`` is a
           live measurement (the service family carries the check's own
           response time) every held poll differs and every held poll
           writes.  That is bounded anyway: holds run at **1,360 across
           ~5,200 runs ≈ 0.26 per run**, and this is an ``UPDATE`` to a
           row that already exists.  ``SNAG-AGENT-006``'s objection was
           about ``INSERT`` statements accumulating — 60 rows for one dead timer
           in five hours — and does not transfer to a statement that
           accumulates nothing.
        3. **``details`` is compared through a JSON round trip, never as
           the dict handed in.**  What comes back from ``JSONB`` has been
           through ``json.dumps``: a tuple written today is a list
           tomorrow, so a plain ``!=`` would report a difference that can
           never be resolved and the gate would pass on every poll for
           ever.  Normalising the *computed* side is what makes the two
           comparable, and it raises on exactly the inputs the write
           itself would raise on, so it adds no new failure.
        4. **What is stored is the caller's dict, not the normalised
           copy.**  A raise and a refresh handed the same input must put
           the same bytes in the row, or its content would depend on
           which path happened to write it — and the normalisation exists
           to answer a question, not to launder a value.
        5. **Reassigned, never mutated in place** —
           :meth:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent._record_recurrence`'s
           rule, and it is the one this family already had to learn:
           SQLAlchemy does not track mutation inside a plain ``JSONB``
           dict, so an in-place update looks like it worked and writes
           nothing.

        **Nothing is announced, and that is not an oversight.**  Session
        39 forbids an in-place *severity* change because the tray
        fingerprints on ``{severity}:{title}`` and would keep a
        fingerprint it has already suppressed.  A message change is
        invisible to that fingerprint, so it is safe in the direction
        that ban is about — and, for the same reason, silent.  No
        ``alert.refreshed`` event is queued: the SSE stream has no
        consumer for one, and an event nobody reads is the
        ``SNAG-CFG-001`` shape.  The corrected sentence reaches the tray
        on its next poll of ``GET /api/sysadmin/alerts``, and reaches a
        reader out loud only when
        :mod:`sysadmin_tray.notifications`' ``reminder_hours`` re-speaks
        the row — which is the surface this fix exists for.

        Finding the row is deliberately **not** done here.  The three
        callers reach it three different ways for reasons of their own —
        the estate judge already holds the ORM rows, the port family
        bounds its read by a title prefix, and
        :meth:`~sysadmin.monitor.agent.SysAdminAgent._raise_judged` keeps
        the title-only snapshot ``SNAG-AGENT-007`` gave it — so a base
        class that took a *title* would own a predicate its subclasses
        state three ways.  It owns the comparison and the write, which is
        the part that must not be written three times.

        Returns:
            ``True`` if the row was changed, ``False`` if it already said
            this.  Never a row count: no row is written, so a refresh must
            not reach ``alerts_raised``.
        """
        wanted = details or {}
        # See rule 3. `json.dumps` without `default=`, deliberately: the
        # write goes through the same serialiser, so anything this
        # rejects is something the row could not have held anyway.
        comparable = json.loads(json.dumps(wanted))
        if alert.message == message and (alert.details or {}) == comparable:
            return False
        alert.message = message
        alert.details = wanted
        logger.debug(
            "alert_refreshed",
            extra={"agent": alert.agent, "title": alert.title},
        )
        return True

    async def resolve_alerts(self, session, title_pattern: str) -> int:
        """Resolve all active alerts matching the given title pattern."""
        from sqlalchemy import update

        result = await session.execute(
            update(Alert)
            .where(
                Alert.agent == self.name,
                Alert.title.ilike(f"%{title_pattern}%"),
                unresolved(),
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
