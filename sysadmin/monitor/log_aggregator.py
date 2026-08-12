"""Log Aggregator Agent — collects, filters, and summarises logs.

Sources:
- journalctl units (systemd services)
- Log files (tail with byte offset tracking)

Pipeline: parse → filter → store → alert → periodic LLM summarise
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, func, select, update

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.core.llm_client import LLMClient
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.journal import (
    SEVERITY_ORDER,
    JournalRead,
    read_journal,
    since_timestamp,
)
from sysadmin.monitor.log_signature import alert_title
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.services import get_services, log_sources

logger = logging.getLogger(__name__)

SUMMARISE_PROMPT_SYSTEM = (
    "You are a sysadmin reviewing logs. Summarise the following log entries. "
    "Group by service. Highlight: recurring errors, new errors not seen before, "
    "patterns suggesting degradation, and anything requiring immediate attention. "
    "Be concise and direct."
)


class LogAggregatorAgent(BaseAgent):
    """Collects and summarises logs from configured sources."""

    name = "log_aggregator"

    def __init__(self) -> None:
        self._file_offsets: dict[str, int] = {}
        # Journal resume positions, one per source.  In memory, so a
        # restart falls back to _resume_floor(), which reads the highest
        # entry already stored for that source — the cursor removes the
        # per-poll duplication, the floor removes the per-restart kind.
        self._cursors: dict[str, str] = {}
        # Constructing an LLMClient opens no connections, and it manages
        # its own per-event-loop HTTP client — so there is deliberately no
        # startup()/shutdown() here.  Opening one on the API loop would
        # only hand this agent, which runs on scheduler threads, a client
        # belonging to somebody else's loop (SNAG-AGENT-003).
        self._llm = LLMClient()


    @staticmethod
    def _sources(agent_config) -> list:
        """Journal sources, services.yaml first, config.yaml for the rest.

        A service and its logs used to be described in two files that had
        to agree by hand, and they did not: ``sysadmin.service`` was
        ingested twice, as ``sysadmin`` from config.yaml and as
        ``sysadmin-service`` from projects.yaml. Declaring the source
        beside the service removes the second name; a config.yaml entry
        that still duplicates one is dropped here and logged, because a
        journal read twice costs nothing but shows up as doubled error
        counts in the summaries.
        """
        sources = log_sources(get_services())
        seen = {s.name for s in sources}
        by_unit = {(s.unit, s.user) for s in sources if s.unit}
        for extra in agent_config.sources:
            if extra.name in seen:
                logger.warning(
                    "duplicate_log_source_name",
                    extra={"source": extra.name, "kept": "services.yaml"},
                )
                continue
            if extra.unit and (extra.unit, extra.user) in by_unit:
                logger.warning(
                    "duplicate_log_source_unit",
                    extra={"source": extra.name, "unit": extra.unit,
                           "kept": "services.yaml"},
                )
                continue
            sources.append(extra)
            seen.add(extra.name)
        return sources

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
                    message=entry["message"][:5000],
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
                    faults[title] = {
                        "severity": (
                            "critical" if entry["severity"] == "critical" else "warning"
                        ),
                        "source": entry["source"],
                        "message": entry["message"],
                        "count": 1,
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
                    "first_seen_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                    "occurrences": fault["count"],
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
        if not cursor:
            floor = await self._resume_floor(session, source.unit)
            if floor is not None:
                since = since_timestamp(floor)

        read = await read_journal(
            unit=source.unit,
            since=since,
            severity_filter=source.severity_filter,
            user=source.user,
            after_cursor=cursor,
            limit=limit,
        )
        if read.cursor:
            self._cursors[source.name] = read.cursor
        return read

    @staticmethod
    async def _resume_floor(session, unit: str) -> datetime | None:
        """Newest stored ``logged_at`` for ``unit``, or ``None`` if never read."""
        result = await session.execute(
            select(func.max(LogEntry.logged_at)).where(LogEntry.source == unit)
        )
        return result.scalar_one_or_none()

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
                Alert.resolved.is_(False),
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
        """
        details = dict(alert.details or {})
        details["last_seen_at"] = now.isoformat()
        details["occurrences"] = int(details.get("occurrences") or 0) + fault["count"]
        details.setdefault("first_seen_at", details["last_seen_at"])
        details.setdefault("source", fault["source"])
        alert.details = details
        alert.message = fault["message"][:500]

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
            Alert.resolved.is_(False),
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

    async def summarise(self, session) -> str | None:
        """Generate an LLM summary of recent warnings/errors. Called on a separate schedule."""
        config = get_config()
        agent_config = config.agents.log_aggregator

        if not agent_config.summarise_with_llm:
            return None

        # Get recent warning/error/critical entries
        since = datetime.now(UTC) - timedelta(minutes=30)
        query = (
            select(LogEntry)
            .where(
                LogEntry.ingested_at >= since,
                LogEntry.severity.in_(["warning", "error", "critical"]),
            )
            .order_by(LogEntry.logged_at)
            .limit(100)
        )
        result = await session.execute(query)
        entries = result.scalars().all()

        if len(entries) < 3:
            return None

        # Build prompt
        log_text = "\n".join(
            f"[{e.logged_at.strftime('%H:%M:%S')}] [{e.severity.upper()}] "
            f"[{e.source}] {e.message[:200]}"
            for e in entries
        )
        prompt = f"Here are the recent log entries:\n\n{log_text}\n\nProvide a concise summary."

        summary_text = await self._llm.generate(
            prompt=prompt,
            system=SUMMARISE_PROMPT_SYSTEM,
        )

        if summary_text:
            # Store summary
            sources_list = list({e.source for e in entries})
            error_count = sum(1 for e in entries if e.severity in ("error", "critical"))

            log_summary = LogSummary(
                period_start=entries[0].logged_at,
                period_end=entries[-1].logged_at,
                model_used=config.llm.model,
                summary=summary_text,
                entry_count=len(entries),
                error_count=error_count,
                sources=sources_list,
            )
            session.add(log_summary)

            logger.info(
                "log_summary_generated",
                extra={"entries": len(entries), "model": config.llm.model},
            )

        return summary_text

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
