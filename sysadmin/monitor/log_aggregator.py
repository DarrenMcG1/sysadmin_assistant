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

from sqlalchemy import select

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.core.llm_client import LLMClient
from sysadmin.monitor.journal import SEVERITY_ORDER, read_journal
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
        config = get_config()
        agent_config = config.agents.log_aggregator
        total_ingested = 0
        alerts_raised = 0

        # Sources declared beside the service that emits them, plus the
        # ones in config.yaml that belong to no service — the kernel
        # journal has no unit to hang off.  Names collide only if a
        # config.yaml source duplicates a service, which is the fault this
        # merge exists to make visible rather than to tolerate silently.
        for source in self._sources(agent_config):
            if source.type == "journalctl" and source.unit:
                entries = await read_journal(
                    unit=source.unit,
                    since="2m ago",
                    severity_filter=source.severity_filter,
                    user=source.user,
                )
            elif source.type == "file" and source.path:
                entries = await asyncio.to_thread(
                    self._read_log_file,
                    source.name,
                    source.path,
                    source.severity_filter,
                )
            else:
                continue

            for entry in entries:
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

                # Alert on error/critical
                if entry["severity"] in ("error", "critical"):
                    await self.raise_alert(
                        session,
                        severity="warning" if entry["severity"] == "error" else "critical",
                        title=f"Log {entry['severity']}: {entry['source']}",
                        message=entry["message"][:500],
                        details={"source": entry["source"]},
                    )
                    alerts_raised += 1

        return AgentResult(
            findings_count=total_ingested,
            alerts_raised=alerts_raised,
            details={"entries_ingested": total_ingested},
        )

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
        self, source_name: str, path: str, severity_filter: str
    ) -> list[dict[str, Any]]:
        """Read new lines from a log file, tracking byte offset."""
        filepath = Path(path)
        if not filepath.exists():
            return []

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

        return entries[:500]

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
