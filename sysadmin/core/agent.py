"""BaseAgent — abstract base class for all scheduled agents.

Provides:
- Template method `run()` that records to `agent_runs`
- `raise_alert()` for writing alerts to the database
- `refresh_alert()` for keeping a deduplicated row's text true
- Automatic timing and error handling
- Change events published to the event bus (fed to SSE clients)
"""

import asyncio
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from sysadmin.core.abandoned_runs import INSTANCE_DETAIL_KEY, INSTANCE_ID
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.escalation import may_quieten_in_place
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

#: The log event :meth:`BaseAgent.raise_alert` writes for every row it
#: inserts, at ``warning``.
#:
#: Lifted to a constant for a reader rather than for this emitter:
#: :func:`sysadmin.snag_claims.check_rung_left_stale` uses its presence in
#: ``log_entries`` as the **witness** that a bare event name written at
#: ``warning`` by this daemon reaches that table at all.  Without it a
#: zero count of :data:`~sysadmin.monitor.agent.RUNG_LEFT_STALE_EVENT` is
#: zero-because-quiet and zero-because-blind at once, which is
#: ``ports_checked``'s rule at the size of a note clause.
#:
#: This event and that one are emitted from different loggers and share
#: the handler chain, the ``<N>`` level prefix and the ``format: json``
#: declaration ``services.yaml`` makes for this unit — so the witness is
#: about the path, not about the module.
ALERT_RAISED_EVENT = "alert_raised"

#: The log event :func:`spawn_manual_run`'s supervisor writes when
#: :meth:`BaseAgent.run` *itself* raises — the bookkeeping around the
#: work, never the work.
#:
#: ``SNAG-LOG-006``.  It sits beside :data:`AGENT_RUN_FAILED_EVENT`
#: because the two must be read together: that constant is the one
#: :data:`sysadmin.monitor.log_aggregator.COVERED_SIGNATURES` **quietens**
#: on the grounds that :mod:`sysadmin.monitor.failures` will speak
#: instead, and this one is the case where that reasoning does not reach.
#: A sitting adding a third entry to that map needs the exception in
#: view, not one module away.
#:
#: Disjoint from it **by construction rather than by convention**.
#: :meth:`BaseAgent.run` swallows ``_execute``'s exception, so the only
#: exceptions that escape it come from ``_record_start``,
#: ``_record_outcome`` and ``_flush_events``.  A supervisor therefore
#: cannot double-report an ordinary agent failure, because an ordinary
#: agent failure *returns normally* — the mutual exclusion
#: :mod:`sysadmin.monitor.failures` and :mod:`sysadmin.monitor.stalls`
#: rely on, one layer down.
#:
#: **No digit, and that is arithmetic rather than taste.**
#: :func:`~sysadmin.monitor.log_signature.signature` maps digit runs to
#: ``N``, so a name carrying a number would make the stored signature
#: differ from this literal — and the failure mode of that is silence,
#: not an error.  ``AGENT_RUN_FAILED_EVENT`` states this for a constant
#: that is *looked up*; these two are looked up by a human reading an
#: alert title, and the same arithmetic decides whether the title they
#: read is the string written here.
MANUAL_RUN_FAILED_EVENT = "manual_run_failed"

#: The log event the same supervisor writes when a manual run is
#: **cancelled** — recorded, deliberately not announced.
#:
#: A task cancelled at interpreter shutdown is not a fault, and
#: :meth:`asyncio.Task.exception` *raises* on a cancelled task, so it has
#: to be tested first whatever is done with it.  Dropping it silently was
#: refused for ``known_noise``'s rule 2: a cancellation leaves exactly
#: the residue a failure leaves — an ``agent_runs`` row stuck at
#: ``running`` that nothing will ever close — so the fact that it
#: happened is worth keeping even though nobody needs waking for it.
#:
#: The rung is the entire mechanism and no flag is kept beside it.
#: :meth:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent._execute`
#: raises a fault only for ``error`` and ``critical``, so a ``warning``
#: line from this source is stored in ``log_entries``, counted, and
#: carried into ``GET /api/logs/trends`` while raising no alert and
#: reaching no tray.  A second suppression list would be a second
#: statement of what the severity already says.
MANUAL_RUN_CANCELLED_EVENT = "manual_run_cancelled"

#: Tasks :func:`spawn_manual_run` is holding.
#:
#: Module level rather than per agent: the five triggers spawn from two
#: composition roots into one process, and a set per agent would make
#: what is retained depend on which agent was asked — a distinction with
#: no reader.  The idiom (a set, plus a callback that discards) is
#: :meth:`sysadmin.core.event_bus.EventBus._spawn`'s, two lines under a
#: comment explaining why the result of ``create_task`` is assigned.
_manual_runs: set[asyncio.Task[Any]] = set()


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

        **The row records which process wrote it** (``SNAG-DB-006``).
        Session 41 stated the cost of the three-transaction split in
        writing — *"a process killed mid-run leaves a permanent
        ``running`` row"* — and this stamp is what lets the next process
        close it as ``cancelled`` instead.  It is written **here** rather
        than by the sweep because the only moment at which "this row
        belongs to this process" is knowable is the moment the row is
        inserted; a sweep inferring it from a clock would need an
        invented constant to express a fact the row can simply carry.
        See :mod:`sysadmin.core.abandoned_runs`.

        ``details`` is otherwise untouched here and is *replaced* whole
        by :meth:`_record_outcome`, so the stamp lives exactly as long as
        the row is a candidate for the sweep and no longer.  That is not
        a leak: a finished run's details belong to the run.
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
                    details={INSTANCE_DETAIL_KEY: INSTANCE_ID},
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
            ALERT_RAISED_EVENT,
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
        severity: str | None = None,
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

        Six rules, four of them the opposite of the obvious
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
        5. **The rung moves in one direction only, and only to the
           floor** (``SNAG-ESTATE-010``, 2026-08-28).  ``severity`` is
           optional and a caller that omits it gets the text-only
           behaviour this method shipped with.  A caller that passes one
           is asking a question, not issuing an instruction:
           :func:`~sysadmin.core.escalation.may_quieten_in_place` decides
           it, and permits exactly a move to
           :data:`~sysadmin.core.escalation.QUIETEST_SEVERITY` from
           something louder.  An escalation is refused here and belongs
           to :func:`~sysadmin.core.escalation.step_for`'s
           resolve-and-re-raise; a downward step that stops short of the
           floor is refused too, because it would be *heard* — see that
           predicate's rule 1.
        6. **Reassigned, never mutated in place** —
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
        that ban is about — and, for the same reason, silent.  A
        **quietening** is visible to it and is silent for the opposite
        reason: the old pair leaves the poll, the new one is dropped
        below ``notify_min_severity`` before ``_consider`` can act on it,
        and the row goes on being served by
        ``GET /api/sysadmin/alerts`` throughout.  Neither write earns an
        event, so neither gets one.  No
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
        # Asked before the text comparison, not after it: a
        # reclassification whose sentence happens to be word-for-word
        # what the row already says is exactly the case the founding
        # entry was filed from — the estate republishes the same breach
        # every hour and only the *rung* moved.  Gating the rung behind
        # "has the text changed" would have shipped green and inert.
        # The rung to write, or `None` for "leave it alone" — carried as
        # the value rather than as a bool so the branch below needs no
        # second test to know it has one.
        quieten_to = (
            severity
            if severity is not None and may_quieten_in_place(severity, alert.severity)
            else None
        )
        if (
            quieten_to is None
            and alert.message == message
            and (alert.details or {}) == comparable
        ):
            return False
        alert.message = message
        alert.details = wanted
        if quieten_to is not None:
            # `info` rather than `debug`, alone among the three writes
            # this method makes. A corrected sentence is bookkeeping; a
            # reclassification is the daemon deciding a standing fault is
            # no longer worth interrupting anyone about, and the journal
            # is the only place that decision is recorded — the row
            # itself keeps no history of the rung it was raised at.
            # Below `severity_filter` for this unit, so it is readable
            # and raises nothing (SNAG-LOG-005's rule, from the other
            # end).
            logger.info(
                "alert_quietened",
                extra={
                    "agent": alert.agent,
                    "title": alert.title,
                    "was": alert.severity,
                    "now": quieten_to,
                },
            )
            alert.severity = quieten_to
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


def spawn_manual_run(agent: BaseAgent) -> asyncio.Task[Any]:
    """Start a manual run and keep watching it, which nothing did before.

    ``SNAG-LOG-006``.  ``POST /api/sysadmin/scan-all`` and
    ``POST /api/files/scan`` started agents with a bare
    ``asyncio.create_task(agent.run(run_type="manual"))`` and kept no
    reference, so there was no scheduler listener behind them and nothing
    awaited the coroutine.  A scheduled run's escape reaches
    ``Scheduler._on_job_error`` and comes out as ``scheduler_job_error``;
    a manual run's reached nobody, which is the one path
    ``COVERED_SIGNATURES``' rule 5 does not cover.

    *The entry names ``POST /api/files/organise`` as the second trigger
    and that is wrong.*  ``/api/files/organise`` is a synchronous action
    route returning ``FileActionResponse``; the discarded task was in
    ``POST /api/files/scan``.  The structural check that watched this
    counted five discards across two files and never named a route, so it
    stayed green either side of the misdescription.

    Six rules, four of them the opposite of the obvious implementation
    and every one settled against the running loop rather than by
    argument:

    1. **The reference is held here, and the residual signal it replaces
       was measured rather than assumed.**  The entry filed the asyncio
       fallback as real but unmeasured — *"what is not established is
       when"* — because no such line exists in this journal.  Driven
       in-process it is **prompt, not deferred**: the loop drops its
       reference when the task completes, CPython collects it on the next
       turn, and ``Task.__del__`` calls the exception handler
       synchronously.  No ``gc.collect()`` is needed and none helps.
       *When* was never the problem.  **What** is: the emitted record
       unwraps to a **252-character signature** and a **220-character
       title** reading ``Task exception was never retrieved future: <Task
       finished name='Task-N' coro=<BaseAgent.run() done, defined at
       …/sysadmin/core/agent.py:N> …`` — ``SNAG-LOG-003``'s shape
       arriving by the one route :func:`~sysadmin.monitor.journal.unwrap_json_message`
       cannot help, since the *unwrapped* message is itself the repr.
       Three costs, each visible in that string: it names ``BaseAgent.run``,
       so all five triggers share one signature and the row cannot say
       which agent died; it carries this module's path, so moving
       ``run()`` forks the row on a commit that changed nothing; and the
       exception's own text sits inside the repr, so on a checkout path
       shorter than this one it falls within the cap and forks a row per
       distinct failure — ``SNAG-AGENT-005``'s pile-up rebuilt inside the
       family built to end it.
    2. **It reports through the journal and never through the database.**
       The exceptions that reach here come from ``_record_start`` and
       ``_record_outcome``, which are database writes — so a report that
       needed a session would need the thing that has just failed.
       :mod:`sysadmin.core.unit_failure` makes this argument one layer
       out, running while the application is dead; this is the same
       argument one layer in.  The journal costs nothing and is already
       wired: since the level prefix (Session 61) and the ``format: json``
       declaration (Session 64) an ``error`` line from this daemon is
       ingested by :class:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent`
       and raises through the family that already owns this source.  No
       new alert family, no new table, no session.
    3. **It cannot double-report an ordinary failure, and that is what
       makes rule 2 safe.**  ``run()`` swallows ``_execute``'s exception,
       so a normal agent failure returns normally and this callback sees
       no exception at all.  Driven across all four shapes ``run()`` can
       escape by: ``_execute`` **and** ``_record_outcome`` raising (the
       journal holds ``agent_run_failed``), ``_record_outcome`` alone
       (``agent_run_completed``), ``_record_start`` (**nothing at all**),
       and ``_flush_events`` (``agent_run_completed``).  All four escape;
       none of the last three writes a ``failed`` row for
       :mod:`sysadmin.monitor.failures` to find.
    4. **That measurement is also what refuted the cheaper fix.**  The
       entry's second candidate — narrow ``COVERED_SIGNATURES`` to
       ``run_type == "scheduled"`` — can only speak where an
       ``agent_run_failed`` line **exists**, which is shape 1 and nothing
       else: **one of the four**.  Shapes 2 and 4 write
       ``agent_run_completed`` and shape 3 writes no line at all, so
       there is nothing there for a narrowed cover to un-quieten.  It is
       also the more expensive of the two, not the cheaper: it needs
       ``unwrap_json_message`` to promote ``run_type`` out of the
       envelope — which that function's own docstring refuses, because
       choosing which further envelope fields join the identity is
       recognising this application again — and it gives
       ``COVERED_SIGNATURES`` a third key component ``known_noise`` does
       not share, when ``NOISE_SEVERITY``'s comment turns on the two
       answering one question.  Costed both ways it buys a quarter of the
       fault for more work.
    5. **Cancellation is tested first and recorded, never announced.**
       :meth:`asyncio.Task.exception` *raises* on a cancelled task, so
       the order is forced; what is not forced is what to do with it.  A
       cancellation at shutdown is not a fault, but it leaves precisely
       the residue a failure leaves — an ``agent_runs`` row stuck at
       ``running`` — so it is written rather than dropped, and written at
       ``warning``, which the log aggregator stores and counts without
       raising.  See :data:`MANUAL_RUN_CANCELLED_EVENT`.
    6. **There is no ``run_type`` parameter, and its absence is the
       rule.**  All five triggers are manual; a scheduled run must not
       arrive here, because APScheduler's listener is what makes
       ``scheduler_job_error`` loud for those and a second supervisor
       would give one fault two speakers — the second-owner defect this
       repository keeps finding, arriving inside the fix for a case of
       it.  Hard-coding ``"manual"`` is what makes that impossible rather
       than merely discouraged, which is
       :func:`~sysadmin.monitor.journal.since_timestamp`'s argument for
       taking a ``datetime``.

    The task is returned for the benefit of a caller that wants it; the
    reference this function keeps does not depend on what the caller does
    with the return, which is the entire point.
    """
    task = asyncio.create_task(agent.run(run_type="manual"))
    _manual_runs.add(task)
    task.add_done_callback(lambda finished: _report_manual_run(agent.name, finished))
    return task


def _report_manual_run(agent_name: str, task: asyncio.Task[Any]) -> None:
    """Say what became of a manual run, then let go of it.

    The discard is in a ``finally`` because a done-callback that raises is
    swallowed by the loop's exception handler — so a logging failure would
    otherwise leak the reference this module exists to hold, and leak it
    silently.

    ``exc_info`` is attached and deliberately not folded into the message.
    Measured through the real :class:`~sysadmin.core.logging_setup.JournalLevelPrefixFormatter`:
    the traceback lands under its own ``exc_info`` envelope key (485
    characters for a short stack) while ``message`` stays the event name,
    so the signature is ``manual_run_failed`` — 17 characters, a
    46-character title — and the evidence is one query away in
    ``raw_line``.  That is ``unwrap_json_message``'s rule 3 holding: the
    unwrap moves what identity is built from, never what is retained.
    """
    try:
        if task.cancelled():
            logger.warning(
                MANUAL_RUN_CANCELLED_EVENT,
                extra={"agent": agent_name, "run_type": "manual"},
            )
            return
        error = task.exception()
        if error is None:
            return
        logger.error(
            MANUAL_RUN_FAILED_EVENT,
            extra={"agent": agent_name, "run_type": "manual", "error": str(error)},
            exc_info=error,
        )
    finally:
        _manual_runs.discard(task)
