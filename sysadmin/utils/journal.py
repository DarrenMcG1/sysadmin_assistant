"""Journalctl log reading helpers."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# journalctl priority mapping (RFC 5424)
PRIORITY_MAP = {
    "0": "critical",  # emerg
    "1": "critical",  # alert
    "2": "critical",  # crit
    "3": "error",
    "4": "warning",
    "5": "info",      # notice
    "6": "info",
    "7": "debug",
}

SEVERITY_ORDER = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}


async def read_journal(
    unit: str,
    since: str = "5m ago",
    severity_filter: str = "warning",
) -> list[dict[str, Any]]:
    """Read journal entries for a systemd unit.

    Args:
        unit: systemd unit name (e.g. 'postgresql.service')
        since: time specification for --since (e.g. '5m ago', '1h ago')
        severity_filter: minimum severity to include

    Returns:
        List of parsed log entries.
    """
    cmd = [
        "journalctl",
        "-u", unit,
        "--since", since,
        "-o", "json",
        "--no-pager",
        "-n", "500",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        logger.warning("journalctl_timeout", extra={"unit": unit})
        return []
    except FileNotFoundError:
        logger.warning("journalctl_not_found")
        return []

    if proc.returncode != 0 and proc.returncode != 1:
        # returncode 1 = no entries, which is fine
        logger.warning(
            "journalctl_error",
            extra={"unit": unit, "stderr": stderr.decode()[:200]},
        )
        return []

    entries = []
    min_severity = SEVERITY_ORDER.get(severity_filter, 0)

    for line in stdout.decode().strip().split("\n"):
        if not line:
            continue
        try:
            data = json.loads(line)
            priority = data.get("PRIORITY", "6")
            severity = PRIORITY_MAP.get(str(priority), "info")

            if SEVERITY_ORDER.get(severity, 0) < min_severity:
                continue

            # Parse timestamp
            usec = data.get("__REALTIME_TIMESTAMP")
            if usec:
                ts = datetime.fromtimestamp(int(usec) / 1_000_000, tz=timezone.utc)
            else:
                ts = datetime.now(timezone.utc)

            entries.append({
                "source": unit,
                "severity": severity,
                "message": data.get("MESSAGE", ""),
                "logged_at": ts,
                "raw_line": line[:2000],
                "metadata": {
                    "pid": data.get("_PID"),
                    "hostname": data.get("_HOSTNAME"),
                    "syslog_identifier": data.get("SYSLOG_IDENTIFIER"),
                },
            })
        except (json.JSONDecodeError, ValueError):
            continue

    return entries
