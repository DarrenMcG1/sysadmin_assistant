"""Log Aggregator Agent — collects, filters, and summarises logs.

Sources:
- journalctl units (systemd services)
- Log files (tail with byte offset tracking)

Pipeline: parse → filter → store → alert → periodic LLM summarise
"""

import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, func, select, update

from sysadmin.core.agent import AGENT_RUN_FAILED_EVENT, AgentResult, BaseAgent
from sysadmin.core.config import get_config

# Aliased, because this module already imports a *different*
# ``SEVERITY_ORDER`` from ``journal``: that one ranks the five log
# severities a journal entry can carry (debug…critical), this one the
# three an ``alerts`` row may hold (``chk_alert_severity``).  Letting
# the names collide would compare a log level against an alert level
# and be wrong only for ``error``, which has no alert rung at all.
from sysadmin.core.escalation import SEVERITY_ORDER as ALERT_SEVERITY_ORDER
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.core.unit_failure import OWN_UNIT
from sysadmin.monitor.journal import (
    SEVERITY_ORDER,
    JournalRead,
    read_journal,
    since_timestamp,
)
from sysadmin.monitor.log_signature import alert_title, signature
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import composed_log_sources

logger = logging.getLogger(__name__)

#: The loudest rung the tray will not speak.
#:
#: ``info`` because it is the only rung below ``tray.notify_min_severity``
#: on this box — the same derivation, and the same one number, as
#: ``judgements.TRANSIENT_HOLDER_SEVERITY``.  The row still exists, still
#: counts occurrences and still appears in the trend; it simply stops
#: interrupting.
#:
#: **One constant for both quietening paths, deliberately.**  A signature
#: declared in ``agents.log_aggregator.known_noise`` and one listed in
#: :data:`COVERED_SIGNATURES` are quiet for entirely different reasons —
#: an operator's judgement that a fault is harmless, against a structural
#: fact that another family owns the fault — and they are recorded under
#: different ``details`` keys so a reader can tell them apart.  But the
#: *number* answers one question, "what does the tray decline to say", and
#: two constants holding one value is the fork ``SNAG-DB-003`` describes.
NOISE_SEVERITY = "info"

#: How much of a journal message ``log_entries.message`` retains.
#:
#: Named rather than repeated, because :meth:`~LogAggregatorAgent._is_unstored`
#: compares an incoming line against a **stored** one to decide whether a
#: restart has already ingested it.  Truncating at two different lengths
#: would make every message longer than the smaller one compare unequal to
#: itself and re-ingest on every restart — ``SNAG-LOG-007`` rebuilt by the
#: fix for ``SNAG-LOG-007``.  ``raw_line`` keeps its own separate cap: it is
#: retained as evidence and nothing compares against it.
STORED_MESSAGE_CHARS = 5000

#: Fault signatures a **different alert family already owns**, mapped to
#: the family that owns them.  Keyed ``(source, signature)``.
#:
#: ``SNAG-LOG-005``.  ``BaseAgent.run`` states one fact twice, three lines
#: apart: it writes :data:`~sysadmin.core.agent.AGENT_RUN_FAILED_EVENT` to
#: the journal and then a ``failed`` row to ``agent_runs``.  Since the
#: level prefix (Session 61) and the ``format: json`` declaration (Session
#: 64) the journal copy reaches this agent, so one agent failure produced
#: a row here **and** a row from :mod:`sysadmin.monitor.failures` — two
#: tray fingerprints, two toasts.  Worse than duplication: ``failures.py``
#: requires **two** consecutive failures and argues that rule out in
#: writing, and this family raises on the **first** line, so it announced
#: exactly the event a sibling decided was not worth announcing.  A
#: deliberate threshold was not overridden, it was bypassed.
#:
#: Five rules, three of them the opposite of the obvious implementation:
#:
#: 1. **Quietened, never dropped.**  ``known_noise``'s rule 2 for its
#:    reason: a consumer that silently declines to judge is
#:    ``SNAG-CFG-001``'s shape, a decision taken with nothing recording
#:    that it was taken.  The row still carries its occurrence count into
#:    ``GET /api/logs/trends``, and ``details['covered_by']`` names the
#:    family that will speak — so a reader who finds the quiet row is told
#:    where the loud one comes from rather than left to wonder why it is
#:    ``info``.
#: 2. **Both halves of the key are constants the producers already own**,
#:    never strings written here.  ``OWN_UNIT`` is the unit
#:    ``read_journal`` reads and stamps into ``log_entries.source``;
#:    ``AGENT_RUN_FAILED_EVENT`` is the event ``BaseAgent.run`` emits.
#:    Copying either would be a second statement of somebody else's fact —
#:    the rule ``max_priority_for`` and ``chk_alert_agent`` already encode.
#: 3. **The source is half the key, never the signature alone** —
#:    ``known_noise``'s rule 1.  Another service logging the same word
#:    has no ``failures.py`` row behind it, so quietening it on the
#:    strength of this daemon's arrangement would silence a real fault.
#: 4. **Scoped to the one signature, not to this daemon's unit.**  The
#:    wider fix — excluding ``OWN_UNIT`` from the alert half entirely —
#:    was refused on measurement: of 249 error incidents in this journal,
#:    **34 carry no** ``agent_run_failed`` at all (``file_organiser_scan``
#:    ×27, ``retention_purge`` ×7), and ``retention_purge`` is not an
#:    agent, so no family covers it.  Excluding the unit deletes the only
#:    witness those have.
#: 5. **The case where ``failures.py`` is blind is the case where a
#:    different signature is still loud**, which is what makes rule 1's
#:    quietening safe rather than merely tidy.  ``failures.py`` reads
#:    ``agent_runs``, so it cannot see a failure ``_record_outcome``
#:    failed to record — but ``_record_outcome`` is awaited outside
#:    ``run()``'s ``try``, so its failure propagates into APScheduler and
#:    raises ``scheduler_job_error``, which this family still speaks at
#:    ``warning``.  Measured on the live journal: 215 of 215 historic
#:    ``agent_run_failed`` incidents carry ``scheduler_job_error`` in the
#:    same second, and every one of them wrote **no** ``agent_runs`` row.
#:    The net is stated rather than assumed — see ``SNAG-LOG-006`` for the
#:    one path it does not cover.
#:
#: A hand-maintained set of this kind is the ``SNAG-CFG-001`` shape, so it
#: is bounded rather than open: one entry, both halves derived, and a test
#: pins that the emitter still emits what this keys on.
COVERED_SIGNATURES: dict[tuple[str, str], str] = {
    (OWN_UNIT, AGENT_RUN_FAILED_EVENT): "sysadmin/monitor/failures.py — "
    "'<agent> agent failing', at two consecutive failures",
}


class LogAggregatorAgent(BaseAgent):
    """Collects and summarises logs from configured sources."""

    name = "log_aggregator"

    def __init__(self) -> None:
        self._file_offsets: dict[str, int] = {}
        # Journal resume positions, one per source.  In memory, so a
        # restart falls back to _resume_floor(), which reads the highest
        # entry already stored for that source — the cursor removes the
        # per-poll duplication, the floor the per-restart kind.  The
        # floor did **not** remove it until 2026-08-17 (SNAG-LOG-007):
        # it narrowed the re-read from a 5-minute window to a 1-second
        # one and the boundary entry came back every time.
        self._cursors: dict[str, str] = {}

    def forget_unknown(self) -> list[str]:
        """Drop resume state for sources no longer declared.

        The known set is :meth:`_sources`, not ``services.yaml`` alone —
        this agent reads journal sources from **both** files, and pruning
        on the services half would discard the cursor of every source
        config.yaml contributes. A dropped cursor is not a clean slate: the
        next poll falls back to ``_resume_floor()``, re-reading from the
        newest stored entry, which is the per-restart duplication the
        cursor exists to remove.

        So this prunes only what neither file declares any more, and it is
        called only from a configuration reload (:mod:`sysadmin.reload`).
        Returns the names dropped — ``details['truncated_sources']``'s rule:
        which source is affected decides whether it matters.
        """
        known = {s.name for s in self._sources(get_config().agents.log_aggregator)}
        dropped = sorted((set(self._cursors) | set(self._file_offsets)) - known)
        for name in dropped:
            self._cursors.pop(name, None)
            self._file_offsets.pop(name, None)
        return dropped

    @staticmethod
    def _sources(agent_config) -> list:
        """Journal sources, services.yaml first, config.yaml for the rest.

        The composition itself moved to
        :func:`sysadmin.monitor.services.composed_log_sources` in Session
        75, when ``GET /api/logs/{source}`` gained a validator and became
        its second caller.  This wrapper stays because it is the seam the
        tests patch, and because the ingestion loop below reads it as the
        agent's own answer to "what do I read".
        """
        return composed_log_sources(agent_config)

    async def _execute(self, session) -> AgentResult:
        """Ingest every source, then raise **one alert per distinct fault**.

        The raise used to sit inside the entry loop, unconditional, one row
        per matching log line — 593,814 unresolved rows for a Bluetooth
        firmware retry loop, 91 % of every unresolved alert in the table
        (``SNAG-AGENT-005``).  That is the mistake this application already
        recorded once, in ``GET /api/services/reliability``'s docstring:
        *"that table records one row per failed check — 123 rows for one
        internet outage"*.  A log is not an incident.

        So alerting happens **after** the loop, over
        :func:`~sysadmin.monitor.log_signature.alert_title` keys, and the
        three rules are the interesting part:

        1. **One open row per fault signature**, not per line and not per
           source.  A source-level key would let the Bluetooth storm hold
           the single ``Log error: kernel`` row while an RCU stall went
           unannounced — both are in the live 30-day window, so this is
           measured rather than hypothetical.
        2. **A repeat bumps the open row instead of raising a new one.**
           ``details['occurrences']`` carries the count that used to be
           expressed as row volume, which is the same information at
           1/300,000th of the storage and is legible on one tray line.
        2b. **A fault another family owns is quietened here rather than
           raised** — :data:`COVERED_SIGNATURES`, ``SNAG-LOG-005``.  The
           row is still written, still counted and still resolved on
           silence; it simply stops being the second thing that speaks
           about one fault.
        3. **Silence is the only recovery signal there is**, so the resolve
           is time-based (:meth:`_resolve_quiet`) rather than the
           "which open alerts would this run not raise?" inversion
           :meth:`sysadmin.monitor.agent.SysAdminAgent._resolve_recovered`
           uses.  That question is meaningless for an event: the answer is
           "all of them, one run later", which is expiry wearing
           resolution's clothes.
        """
        config = get_config()
        agent_config = config.agents.log_aggregator
        # Rebuilt every run rather than cached, which is free and is what
        # makes an edit to config.yaml take effect on the next poll — the
        # per-run configuration SNAG-AGENT-003 bought by forbidding agents
        # a startup hook.  ``GET /api/logs/actions`` tells the operator to
        # make that edit, so it had better land without a restart.
        known_noise = {
            (entry.source, entry.signature): entry
            for entry in agent_config.known_noise
        }
        total_ingested = 0
        alerts_raised = 0
        truncated: list[str] = []
        # signature title -> (severity, source, last message, count)
        faults: dict[str, dict[str, Any]] = {}

        # Sources declared beside the service that emits them, plus the
        # ones in config.yaml that belong to no service — the kernel
        # journal has no unit to hang off.  Names collide only if a
        # config.yaml source duplicates a service, which is the fault this
        # merge exists to make visible rather than to tolerate silently.
        for source in self._sources(agent_config):
            if source.type == "journalctl" and source.unit:
                read = await self._read_journal_source(
                    session, source, agent_config.max_entries_per_read
                )
            elif source.type == "file" and source.path:
                read = await asyncio.to_thread(
                    self._read_log_file,
                    source.name,
                    source.path,
                    source.severity_filter,
                    agent_config.max_entries_per_read,
                )
            else:
                continue

            if read.truncated:
                truncated.append(source.name)

            for entry in read.entries:
                log_entry = LogEntry(
                    source=entry["source"],
                    severity=entry["severity"],
                    message=entry["message"][:STORED_MESSAGE_CHARS],
                    raw_line=entry.get("raw_line", "")[:2000],
                    metadata_=entry.get("metadata", {}),
                    logged_at=entry["logged_at"],
                )
                session.add(log_entry)
                total_ingested += 1

                if entry["severity"] not in ("error", "critical"):
                    continue

                title = alert_title(
                    entry["severity"], entry["source"], entry["message"]
                )
                fault = faults.get(title)
                if fault is None:
                    sig = signature(entry["message"])
                    key = (entry["source"], sig)
                    noise = known_noise.get(key)
                    # Two independent reasons to be quiet, kept apart in
                    # ``details`` because they answer different questions:
                    # an operator said this is harmless, against another
                    # family already owning it.  Either alone is enough to
                    # drop the rung, and a signature carrying both is
                    # over-determined rather than ambiguous.
                    covered_by = COVERED_SIGNATURES.get(key)
                    faults[title] = {
                        "severity": (
                            NOISE_SEVERITY
                            if noise is not None or covered_by is not None
                            else "critical"
                            if entry["severity"] == "critical"
                            else "warning"
                        ),
                        "source": entry["source"],
                        "message": entry["message"],
                        "count": 1,
                        "signature": sig,
                        "noise_reason": noise.reason if noise else None,
                        "covered_by": covered_by,
                    }
                else:
                    # The newest line wins, so the verbatim example beside
                    # a normalised title is the most recent occurrence
                    # rather than whichever arrived first.
                    fault["message"] = entry["message"]
                    fault["count"] += 1

        open_alerts = await self._open_alerts(session, set(faults))
        now = datetime.now(UTC)
        for title, fault in faults.items():
            existing = open_alerts.get(title)
            if existing is not None:
                self._record_recurrence(existing, fault, now)
                continue
            await self.raise_alert(
                session,
                severity=fault["severity"],
                title=title,
                message=fault["message"][:500],
                details={
                    "source": fault["source"],
                    "signature": fault["signature"],
                    "first_seen_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                    "occurrences": fault["count"],
                    # Present only when config.yaml says so, so a reader
                    # of the row can see *why* it is quiet without going
                    # to look — the reason SNAG-CFG-001 was a defect
                    # rather than a tidy-up.
                    **(
                        {"noise_reason": fault["noise_reason"]}
                        if fault["noise_reason"]
                        else {}
                    ),
                    # Names the family rather than merely flagging that
                    # one exists: a reader who finds an ``info`` row for
                    # a genuine fault needs to know where the loud row
                    # comes from, and ``details['truncated_sources']``'s
                    # rule is that naming beats counting.
                    **(
                        {"covered_by": fault["covered_by"]}
                        if fault["covered_by"]
                        else {}
                    ),
                },
            )
            alerts_raised += 1

        alerts_resolved = await self._resolve_quiet(
            session, set(faults), agent_config.alert_quiet_minutes, now
        )

        if truncated:
            logger.warning(
                "log_read_truncated",
                extra={"sources": truncated, "limit": agent_config.max_entries_per_read},
            )

        return AgentResult(
            findings_count=total_ingested,
            alerts_raised=alerts_raised,
            details={
                "entries_ingested": total_ingested,
                "distinct_faults": len(faults),
                "alerts_resolved": alerts_resolved,
                # Named, not counted: a source at its ceiling is a source
                # whose entries are being dropped, and which one it is
                # decides whether that matters.
                "truncated_sources": truncated,
            },
        )

    async def _read_journal_source(
        self, session, source, limit: int
    ) -> JournalRead:
        """Read one journal source, resuming where the last read stopped.

        Two resume mechanisms, because they fail in different ways.
        ``self._cursors`` is exact and covers the poll-to-poll case, which
        is where the damage was: ``since="2m ago"`` on a 60-second poll
        ingested every unit-journal event **exactly twice** — two copies of
        all 18 ``venture-assistant-backend`` and all 15
        ``sportsanalyser-frontend`` events, doubling every count anything
        downstream computes from ``log_entries``.

        The cursor lives in memory, so a restart loses it.  The floor
        covers that: the newest ``logged_at`` already stored for this
        source, which is durable because it *is* the stored data.  A window
        is still needed for a genuinely first read, and only then.
        """
        cursor = self._cursors.get(source.name)
        since = "5m ago"
        floor: datetime | None = None
        stored_at_floor: set[str] = set()
        if not cursor:
            floor, stored_at_floor = await self._resume_floor(session, source.unit)
            if floor is not None:
                since = since_timestamp(floor)

        read = await read_journal(
            unit=source.unit,
            since=since,
            severity_filter=source.severity_filter,
            user=source.user,
            after_cursor=cursor,
            limit=limit,
            log_format=source.format,
        )
        if read.cursor:
            self._cursors[source.name] = read.cursor
        if floor is None:
            return read
        # The window deliberately re-admits the boundary (see
        # :meth:`_resume_floor`); this is where it is closed again.
        # ``cursor`` and ``truncated`` are carried through untouched — the
        # cursor is journalctl's answer to "where did this read stop",
        # which is a fact about the read and not about what was kept, the
        # same rule that takes it *before* the severity filter.
        return replace(
            read,
            entries=[
                entry
                for entry in read.entries
                if self._is_unstored(entry, floor, stored_at_floor)
            ],
        )

    @staticmethod
    def _is_unstored(
        entry: dict[str, Any], floor: datetime, stored_at_floor: set[str]
    ) -> bool:
        """Is ``entry`` newer than the resume floor, or new at it?

        Strictly-newer is the common case and needs no message
        comparison.  At the floor's own microsecond the timestamp cannot
        decide, so the message does — truncated to
        :data:`STORED_MESSAGE_CHARS` first, because that is the form the
        row holds and comparing the untruncated line against a truncated
        one would read every long message as new on every restart, which
        is this defect wearing a longer name.
        """
        logged_at = entry["logged_at"]
        if logged_at > floor:
            return True
        if logged_at < floor:
            return False
        return entry["message"][:STORED_MESSAGE_CHARS] not in stored_at_floor

    @staticmethod
    async def _resume_floor(session, unit: str) -> tuple[datetime | None, set[str]]:
        """Newest stored ``logged_at`` for ``unit``, and the messages at it.

        Two values rather than one, because the floor alone cannot say
        whether the entry *at* it has been stored — and it always has.
        ``journalctl --since`` is **inclusive** and
        :func:`~sysadmin.monitor.journal.since_timestamp` truncates to
        whole seconds, so a window opened at the newest stored entry
        re-admits that entry and every other one sharing its second.

        Widening the window is deliberate and must stay: the alternative
        — opening at ``floor + 1s`` — trades the duplicate for a **gap**,
        which is the worse failure for a monitor and the reason
        :meth:`_read_journal_source` uses a cursor at all.  So the read
        stays wide and the boundary is settled here instead, against the
        stored rows themselves.

        The message set is scoped to the floor's exact microsecond, which
        is one row on every source measured on this box.  Comparing on
        the message as well as the timestamp keeps a genuine second entry
        stamped in the same microsecond — the Bluetooth pair sits 29 µs
        apart, so a collision is possible — rather than assuming one
        timestamp means one entry.
        """
        result = await session.execute(
            select(func.max(LogEntry.logged_at)).where(LogEntry.source == unit)
        )
        floor = result.scalar_one_or_none()
        if floor is None:
            return None, set()
        stored = await session.execute(
            select(LogEntry.message).where(
                LogEntry.source == unit, LogEntry.logged_at == floor
            )
        )
        return floor, set(stored.scalars().all())

    async def _open_alerts(self, session, titles: set[str]) -> dict[str, Alert]:
        """Unresolved alerts among ``titles``, keyed by title.

        **Bounded by the titles this run raised, deliberately.** The
        obvious query — every unresolved row this agent owns — would have
        materialised 593,814 ORM objects on the first run against the live
        table, so the fix would have fallen over on the backlog it exists
        to end.  A run only needs the rows it might bump, and that set is
        the number of distinct fault signatures in one poll.

        No title-pattern population here, unlike
        :data:`~sysadmin.monitor.agent.RESOLVABLE_TITLE_PATTERNS`: this
        agent raises exactly one kind of alert, so ``agent = 'log_aggregator'``
        already names every row it owns and a pattern list would only be a
        second thing to keep in step with the raise site.
        """
        if not titles:
            return {}
        result = await session.execute(
            select(Alert).where(
                Alert.agent == self.name,
                unresolved(),
                Alert.title.in_(sorted(titles)),
            )
        )
        return {alert.title: alert for alert in result.scalars().all()}

    @staticmethod
    def _record_recurrence(alert: Alert, fault: dict[str, Any], now: datetime) -> None:
        """Fold a repeat occurrence into the open row.

        ``details`` is reassigned rather than mutated in place: SQLAlchemy
        does not track mutation inside a plain JSONB dict, so an in-place
        update would look like it worked and write nothing — and the whole
        resolve depends on ``last_seen_at`` moving.

        **A newly-declared noise entry quietens the open row in place, and
        that is legitimate precisely because it is going down.**
        ``SNAG-ESTATE-010`` records the general fault: dedup skips a
        judgement whose title is already open, so a change that makes a
        family *quieter* never reaches anything standing when it ships.
        This family is the worst case for it — a signature loud enough to
        be worth marking as noise is by definition one that never goes
        quiet, so its row never resolves and the operator's edit would
        take effect approximately never.

        Session 39 forbids in-place severity changes, and the ban is
        **asymmetric**.  Its reason is that an escalation must be *heard*:
        the tray fingerprints on ``{severity}:{title}``, so bumping
        severity in place keeps a fingerprint it has already suppressed
        and the escalation is recorded but never spoken.  A quietening
        wants the opposite outcome.  Writing ``info`` in place hands the
        tray a fingerprint that ``_consider`` drops below
        ``notify_min_severity`` before it can notify — which is the entire
        objective, so the mechanism that makes escalation fail is what
        makes this work.

        :data:`COVERED_SIGNATURES` rides the same path for the same
        reason, and it needs it more rather than less: a ``known_noise``
        entry appears when an operator edits config.yaml, which the next
        poll re-reads, whereas a covered signature appears at a *deploy*
        — so the open row it must reach is one this daemon raised loudly
        under the previous release, which is exactly the row a restart
        does not resolve.

        It is deliberately **one-directional**.  Raising severity in place
        here would be Session 39's defect verbatim, so a fault that has
        stopped matching a noise entry keeps its quiet row until silence
        resolves it and the next occurrence raises a loud one — the
        resolve-and-re-raise the ladder does explicitly, arriving by the
        route this family already has.
        """
        details = dict(alert.details or {})
        details["last_seen_at"] = now.isoformat()
        details["occurrences"] = int(details.get("occurrences") or 0) + fault["count"]
        details.setdefault("first_seen_at", details["last_seen_at"])
        details.setdefault("source", fault["source"])
        details["signature"] = fault["signature"]
        if fault["noise_reason"]:
            details["noise_reason"] = fault["noise_reason"]
        else:
            details.pop("noise_reason", None)
        if fault["covered_by"]:
            details["covered_by"] = fault["covered_by"]
        else:
            details.pop("covered_by", None)
        alert.details = details
        alert.message = fault["message"][:500]

        wanted = fault["severity"]
        if ALERT_SEVERITY_ORDER.get(wanted, 0) < ALERT_SEVERITY_ORDER.get(
            alert.severity, 0
        ):
            alert.severity = wanted

    async def _resolve_quiet(
        self, session, seen: set[str], quiet_minutes: int, now: datetime
    ) -> int:
        """Resolve open alerts whose fault has not been logged for a while.

        The resolve is **excluded by exact title** for anything this run
        observed, and only then filtered on age.  Both tests do the same
        job — a title seen this run has just had ``last_seen_at`` set to
        ``now`` — and the exclusion is kept because it cannot race a clock,
        which is the caution
        :meth:`sysadmin.monitor.agent.SysAdminAgent._resolve_recovered`
        records for rows raised inside the same transaction.

        ``created_at`` is the fallback for a row with no ``last_seen_at``,
        which is every row raised before this change.  Without it the whole
        pre-existing backlog would be permanently unresolvable — the defect
        this method exists to end, preserved by the fix for it.
        """
        cutoff = now - timedelta(minutes=quiet_minutes)
        last_seen = func.coalesce(
            Alert.details["last_seen_at"].astext.cast(DateTime(timezone=True)),
            Alert.created_at,
        )
        conditions = [
            Alert.agent == self.name,
            unresolved(),
            last_seen < cutoff,
        ]
        if seen:
            conditions.append(Alert.title.notin_(sorted(seen)))

        result = await session.execute(
            update(Alert).where(*conditions).values(resolved=True, resolved_at=now)
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "log_alerts_resolved",
                extra={"agent": self.name, "count": resolved, "quiet_minutes": quiet_minutes},
            )
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": "went quiet", "count": resolved},
            )
        return resolved

    def _read_log_file(
        self, source_name: str, path: str, severity_filter: str, limit: int
    ) -> JournalRead:
        """Read new lines from a log file, tracking byte offset.

        Returns a :class:`~sysadmin.monitor.journal.JournalRead` so a file
        source and a journal source report truncation the same way.  It
        carries no cursor: a byte offset already resumes exactly, and it is
        durable across a restart only in the sense that the file is — a
        rotation resets it, which the size check below detects.
        """
        filepath = Path(path)
        if not filepath.exists():
            return JournalRead(entries=[])

        entries = []
        min_severity = SEVERITY_ORDER.get(severity_filter, 0)

        try:
            file_size = filepath.stat().st_size
            current_offset = self._file_offsets.get(source_name, 0)

            # Detect rotation (file smaller than offset)
            if file_size < current_offset:
                current_offset = 0

            with open(filepath) as f:
                f.seek(current_offset)
                for line in f:
                    parsed = self._parse_log_line(source_name, line.strip())
                    if parsed and SEVERITY_ORDER.get(parsed["severity"], 0) >= min_severity:
                        entries.append(parsed)

                self._file_offsets[source_name] = f.tell()

        except (PermissionError, OSError) as e:
            logger.warning(
                "log_file_read_error",
                extra={"path": path, "error": str(e)},
            )

        # The cap was ``entries[:500]``, silent — the same defect as
        # journalctl's ``-n 500`` and fixed the same way.  Here the
        # *oldest* entries are kept, because the byte offset has already
        # advanced past the lot: dropping the newest would leave them
        # unread for good, whereas a journal cursor can be re-read.
        return JournalRead(entries=entries[:limit], truncated=len(entries) > limit)

    def _parse_log_line(self, source: str, line: str) -> dict[str, Any] | None:
        """Parse a log line into structured data."""
        if not line:
            return None

        # Attempt to detect severity from common patterns
        severity = "info"
        line_upper = line.upper()
        if "CRITICAL" in line_upper or "FATAL" in line_upper:
            severity = "critical"
        elif "ERROR" in line_upper:
            severity = "error"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            severity = "warning"
        elif "DEBUG" in line_upper:
            severity = "debug"

        return {
            "source": source,
            "severity": severity,
            "message": line[:5000],
            "logged_at": datetime.now(UTC),
            "raw_line": line[:2000],
            "metadata": {},
        }
