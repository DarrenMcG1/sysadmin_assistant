"""``raw_line`` keeps a long traceback's exception line — ``SNAG-LOG-019``.

``unwrap_json_message``'s rule 3 says a ``format: json`` record's envelope
"stays one query away" in ``raw_line``.  Under a 2000-character cap it did
not for a traceback: ``MESSAGE`` starts after systemd's own fields, the
envelope is escaped twice inside it, and the cause is the **last** line.
Estate-manager's ADR-0211 sends every unhandled 500 on :8400 in exactly
this shape, and this daemon's own 2026-09-24 ASGI tracebacks lost theirs.

The record below is built the way the box writes one: a block of systemd
fields ahead of ``MESSAGE`` (about 1,000 characters, the high end of the
260–1,024 measured), and a traceback of about 5,600 characters, the size
of the 2026-09-24 manifest outage's.  Recovery is asserted by parsing,
never by substring — the envelope is nested JSON-escaped, so an ``in``
test would pass on the escaped text for the wrong reason.

Three stores, three tests, because the cap was applied three times:
``read_journal`` composes the entry, the aggregator cuts it again when it
builds the row, and ``_parse_log_line`` cuts a file source's line.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor.journal import STORED_RAW_LINE_CHARS, read_journal
from sysadmin.monitor.log_aggregator import LogAggregatorAgent
from sysadmin.monitor.models.log_entry import LogEntry
from tests.test_log_alert_dedup import _entry, _run, _Session

CAUSE = "RuntimeError: manifest unreadable: /home/gaddi/projects/estate-manager"

#: One uvicorn frame, repeated until the traceback is the outage's size.
FRAME = (
    '  File "/home/gaddi/projects/estate-manager/.venv/lib/python3.13/'
    'site-packages/uvicorn/protocols/http/httptools_impl.py", line 409, '
    "in run_asgi\n    result = await app(  # type: ignore[func-returns-value]\n"
)

EXC_INFO = (
    "Traceback (most recent call last):\n"
    + FRAME * (5600 // len(FRAME))
    + CAUSE
)

ENVELOPE = json.dumps(
    {
        "timestamp": "2026-09-24 10:15:46,112",
        "level": "ERROR",
        "logger": "uvicorn.error",
        "message": "Exception in ASGI application",
        "exc_info": EXC_INFO,
    }
)


def _record(message: str) -> str:
    """A journalctl ``-o json`` line, systemd's fields first as on the box."""
    return json.dumps(
        {
            "__CURSOR": "s=" + "a" * 120,
            "__REALTIME_TIMESTAMP": "1758708946112000",
            "_SYSTEMD_CGROUP": "/user.slice/user-1000.slice/user@1000.service/"
            "app.slice/estate-manager-api.service",
            "_CMDLINE": "/home/gaddi/projects/estate-manager/.venv/bin/python "
            "-m uvicorn estate_service.main:app --host 127.0.0.1 --port 8400 "
            + "--log-config x " * 20,
            "_SYSTEMD_INVOCATION_ID": "f" * 32,
            "_BOOT_ID": "b" * 32,
            "_MACHINE_ID": "m" * 32,
            "_EXE": "/usr/bin/python3.13",
            "SYSLOG_IDENTIFIER": "python",
            "PRIORITY": "3",
            "MESSAGE": message,
        }
    )


def _cause_of(raw_line: str) -> str:
    """The exception line recovered from a stored ``raw_line``."""
    envelope = json.loads(json.loads(raw_line)["MESSAGE"])
    return envelope["exc_info"].splitlines()[-1]


def test_the_fixture_is_the_case_the_old_cap_lost():
    """The fixture must be one that 2000 characters could not hold, or the
    tests below would pass under the defect they guard against."""
    record = _record(ENVELOPE)
    assert record.index('"MESSAGE"') > 900
    assert len(record) > 5600
    with pytest.raises(json.JSONDecodeError):
        _cause_of(record[:2000])


@pytest.mark.asyncio
async def test_read_journal_keeps_the_exception_line():
    with patch(
        "sysadmin.monitor.journal._run",
        new=AsyncMock(return_value=_record(ENVELOPE)),
    ):
        read = await read_journal(
            "estate-manager-api.service",
            severity_filter="error",
            log_format="json",
        )

    entry = read.entries[0]
    assert entry["message"] == "Exception in ASGI application"
    assert _cause_of(entry["raw_line"]) == CAUSE


@pytest.mark.asyncio
async def test_the_aggregator_stores_it_uncut():
    """The second cut, at the row, is the one that reaches the table."""
    record = _record(ENVELOPE)
    session = _Session()
    await _run(LogAggregatorAgent(), session, [{**_entry("x"), "raw_line": record}])

    rows = [o for o in session.added if isinstance(o, LogEntry)]
    assert _cause_of(rows[0].raw_line) == CAUSE


@pytest.mark.asyncio
async def test_the_aggregator_still_bounds_a_coredump_sized_record():
    """The cap is raised, not removed: ``systemd-coredump`` writes records
    of up to 357,717 characters, and those are still cut."""
    session = _Session()
    huge = "x" * (STORED_RAW_LINE_CHARS * 2)
    await _run(LogAggregatorAgent(), session, [{**_entry("x"), "raw_line": huge}])

    rows = [o for o in session.added if isinstance(o, LogEntry)]
    assert len(rows[0].raw_line) == STORED_RAW_LINE_CHARS


def test_a_file_source_line_keeps_its_tail():
    """A file source's ``raw_line`` is the line itself.  It must be at
    least as long as the stored ``message`` (5000), or the evidence copy
    would be shorter than the copy it is evidence for."""
    line = "ERROR " + "y" * 6000 + " the end"
    parsed = LogAggregatorAgent()._parse_log_line("app.log", line)

    assert parsed is not None
    assert parsed["raw_line"] == line
