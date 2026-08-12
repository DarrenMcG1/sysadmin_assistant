"""Journalctl log reading helpers."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

#: Entries parsed from one read.  A ceiling is unavoidable — the kernel
#: journal on this box has sustained 8.5 messages a second for days — so
#: the question is only whether hitting it is visible.  It was not:
#: ``-n 500`` was passed with no report, and ``findings_count`` sat at
#: exactly 200 on every single run while nobody read it as a symptom
#: (``SNAG-AGENT-005``).
DEFAULT_READ_LIMIT = 500


@dataclass(frozen=True)
class JournalRead:
    """One read of a journal, with the two facts a poller needs back.

    ``read_journal`` used to return a bare list, which could express
    neither "where to resume" nor "there was more than this".
    """

    entries: list[dict[str, Any]]
    #: Opaque journalctl cursor of the newest entry seen, or ``None`` when
    #: the read was empty.  Taken **before** the severity filter — see
    #: :func:`read_journal`.
    cursor: str | None = None
    #: The read hit ``limit``, so older unread entries were skipped.
    truncated: bool = False

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


def since_timestamp(moment: datetime) -> str:
    """Format ``moment`` as a journalctl ``--since`` argument.

    ``@<epoch seconds>`` rather than a formatted datetime, because
    journalctl reads a bare ``YYYY-MM-DD HH:MM:SS`` in **local** time while
    everything stored here is UTC — a one-hour window silently shifted by
    the BST offset is the kind of gap that only shows up in winter.
    """
    return f"@{int(moment.timestamp())}"


async def read_journal(
    unit: str,
    since: str = "5m ago",
    severity_filter: str = "warning",
    user: bool = False,
    after_cursor: str | None = None,
    limit: int = DEFAULT_READ_LIMIT,
) -> JournalRead:
    """Read journal entries for a systemd unit.

    **Resume from ``after_cursor``, not from a time window.** The caller
    used to pass ``since="2m ago"`` on a 60-second poll, so every entry was
    ingested exactly twice — confirmed at two copies for all 18
    ``venture-assistant-backend`` and all 15 ``sportsanalyser-frontend``
    events (``SNAG-AGENT-005``). Narrowing the window instead would trade
    the duplicate for a gap whenever a run ran long, which is the worse
    failure for a monitor: a cursor overlaps safely because journalctl,
    not a clock, decides what has already been read.

    ``since`` is still the **first** read of a source and the fallback when
    a cursor no longer resolves — the journal is vacuumed and rotated, so a
    cursor from before a rotation is simply gone, and treating that as a
    hard failure would stop a source for good.

    Args:
        unit: systemd unit name (e.g. 'postgresql.service'), or 'kernel'.
        since: time specification used only when there is no usable cursor.
        severity_filter: minimum severity to include.
        user: read a *user* unit's journal (journalctl --user).
        after_cursor: resume position from the previous read.
        limit: maximum entries to take from one read.

    Returns:
        A :class:`JournalRead`.
    """
    base = [
        "journalctl",
        "-o", "json",
        "--no-pager",
        "-n", str(limit),
    ]
    # Kernel messages use -k/--dmesg rather than -u
    if unit == "kernel":
        base.insert(1, "-k")
    else:
        base[1:1] = ["-u", unit]
        if user:
            base.insert(1, "--user")

    stdout = None
    if after_cursor:
        stdout = await _run([*base, "--after-cursor", after_cursor], unit)
        if stdout is None:
            # A cursor the journal no longer holds. Start again from the
            # window rather than leaving this source permanently unread.
            logger.warning("journal_cursor_stale", extra={"unit": unit})
    if stdout is None:
        stdout = await _run([*base, "--since", since], unit)
    if stdout is None:
        return JournalRead(entries=[])

    lines = [ln for ln in stdout.strip().split("\n") if ln]
    entries = []
    cursor = None
    min_severity = SEVERITY_ORDER.get(severity_filter, 0)

    for line in lines:
        try:
            data = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue

        # The cursor advances over **every** entry read, not only the ones
        # that survive the severity filter. Advancing only past kept
        # entries would leave the resume point behind a run of info-level
        # noise, and the next read would parse it all again — the
        # duplicate-ingest defect rebuilt one layer down.
        cursor = data.get("__CURSOR") or cursor

        try:
            priority = data.get("PRIORITY", "6")
            severity = PRIORITY_MAP.get(str(priority), "info")

            if SEVERITY_ORDER.get(severity, 0) < min_severity:
                continue

            # Parse timestamp
            usec = data.get("__REALTIME_TIMESTAMP")
            if usec:
                ts = datetime.fromtimestamp(int(usec) / 1_000_000, tz=UTC)
            else:
                ts = datetime.now(UTC)

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

    return JournalRead(
        entries=entries,
        cursor=cursor,
        # ``-n`` returns the *newest* ``limit`` entries, so hitting the cap
        # means older unread ones were skipped and the cursor has jumped
        # past them. Staying current matters more than completeness for a
        # monitor, but the skip must be reported rather than inferred from
        # a findings count that never moves.
        truncated=len(lines) >= limit,
    )


async def _run(cmd: list[str], unit: str) -> str | None:
    """Run a journalctl command, returning stdout or ``None`` on failure.

    Return code 1 means "no entries", which is not a failure.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except TimeoutError:
        logger.warning("journalctl_timeout", extra={"unit": unit})
        return None
    except FileNotFoundError:
        logger.warning("journalctl_not_found")
        return None

    if proc.returncode not in (0, 1):
        logger.warning(
            "journalctl_error",
            extra={"unit": unit, "stderr": stderr.decode()[:200]},
        )
        return None

    return stdout.decode()
