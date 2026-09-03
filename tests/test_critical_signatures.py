"""A declared signature speaks above its journal rung, on the second incident.

The gap these cover, measured on this box on 2026-09-03 rather than
reasoned about.  The dGPU took three full amdgpu MODE1 resets in 8.2
hours — ``ring gfx_0.0.0 timeout`` → the per-queue reset failing (``MES
failed to respond to msg=RESET``, ``The CPFW hasn't support pipe reset
yet.``) → ``MODE1 reset`` → ``VRAM is lost due to GPU reset!``, which
destroys every GPU client's memory on a 24 GB card shared by four
services.  The monitor said nothing louder than a log line, for **two
independent reasons that had to be fixed together**:

1. The kernel stamps the diagnosis at ``err`` and the *event* at
   ``info``, and the kernel source read ``journalctl -p 3``.  Counted in
   ``log_entries``: 0 rows for ``VRAM is lost``, ``GPU reset begin``,
   ``MODE1 reset`` and ``device wedged``; 4 apiece for ``Illegal
   opcode`` and ``ring gfx_0.0.0 timeout``.
2. ``critical`` was unreachable regardless — ``chk_alert_severity``
   admits three rungs, journal ``error`` maps to alert ``warning``, and
   amdgpu never uses PRIORITY 0–2.  All **44** amdgpu alert rows on this
   box are ``warning``.

``SNAG-AGENT-008``'s multiplicative shape: a fix for either half alone
is not half the benefit, it is none.  Widening the filter without the
declaration adds 1,804 lines a day and still raises nothing above
``warning``; declaring without widening declares a signature the reader
cannot see.

**What these tests can and cannot show.**  The session is a stand-in, so
a ``WHERE`` clause has no effect and the escalation count is whatever
the stand-in is told to answer — these pin the *rule*, and
:class:`_CountingSession` models the database rather than the one call
site, because a fake that ignores the predicate cannot distinguish
"counts resolved rows" from "counts open rows", which is the rule the
escalation depends on.  The predicate itself is asserted on compiled
SQL.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.core.config import LogSource, parse_config
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.journal import JournalRead, max_priority_for
from sysadmin.monitor.log_aggregator import (
    CRITICAL_SIGNATURES,
    DECLARED_FLOOR_SEVERITY,
    NOISE_SEVERITY,
    LogAggregatorAgent,
)
from sysadmin.monitor.log_signature import signature

#: The live lines, verbatim from ``journalctl -k -b`` on 2026-09-03.
#: Typed from the journal rather than from documentation, because what a
#: declaration keys on is what the producer actually emits.
VRAM_LOST = "amdgpu 0000:03:00.0: amdgpu: VRAM is lost due to GPU reset!"
RESET_BEGIN = "amdgpu 0000:03:00.0: amdgpu: GPU reset begin!. Source:  1"
ILLEGAL_OPCODE = (
    "[drm:gfx_v11_0_bad_op_irq [amdgpu]] *ERROR* Illegal opcode in command stream "
)
RING_USES_VM = "amdgpu 0000:03:00.0: amdgpu: ring gfx_0.0.0 uses VM inv eng 0 on hub 0"

DECLARED_KEY = ("kernel", signature(VRAM_LOST))
SOURCE = LogSource(name="kernel", type="journalctl", unit="kernel",
                   severity_filter="info")


def _entry(message: str, severity: str = "info", source: str = "kernel"):
    return {
        "source": source,
        "severity": severity,
        "message": message,
        "logged_at": datetime.now(UTC),
        "raw_line": message,
        "metadata": {},
    }


def _config(*, known_noise=None, repeat_hours: float = 24.0):
    return SimpleNamespace(
        agents=SimpleNamespace(
            log_aggregator=SimpleNamespace(
                sources=[],
                alert_quiet_minutes=15,
                max_entries_per_read=500,
                critical_repeat_hours=repeat_hours,
                known_noise=known_noise or [],
            )
        )
    )


class _CountingSession:
    """Stand-in that answers the incident count, and records the query.

    It discriminates on ``count(`` rather than on call order: the
    ordering of the reads inside ``_execute`` is not a fact this module
    owns, and a stand-in keyed on it reports a refactor as a failure.
    """

    def __init__(self, prior: int = 0, open_alerts: list[Alert] | None = None):
        self.added: list[object] = []
        self.statements: list[object] = []
        self.count_statements: list[object] = []
        self._prior = prior
        self._open = open_alerts or []
        self.flush = AsyncMock()

    def add(self, obj):
        self.added.append(obj)

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        text = str(statement)
        result = MagicMock()
        if text.startswith("UPDATE"):
            result.rowcount = 0
            return result
        if "count(" in text:
            self.count_statements.append(statement)
            result.scalar_one.return_value = self._prior
            return result
        if "max(" in text:
            result.scalar_one_or_none.return_value = None
            return result
        result.scalars.return_value.all.return_value = self._open
        return result

    @property
    def alerts(self) -> list[Alert]:
        return [a for a in self.added if isinstance(a, Alert)]


async def _run(agent, session, entries, *, known_noise=None, repeat_hours=24.0):
    read = JournalRead(entries=entries, cursor="c1", truncated=False)
    with (
        patch(
            "sysadmin.monitor.log_aggregator.get_config",
            return_value=_config(known_noise=known_noise, repeat_hours=repeat_hours),
        ),
        patch.object(LogAggregatorAgent, "_sources", staticmethod(lambda _c: [SOURCE])),
        patch(
            "sysadmin.monitor.log_aggregator.read_journal",
            AsyncMock(return_value=read),
        ),
    ):
        return await agent._execute(session)


# --- The declaration reaches the reader --------------------------------


def test_every_declaration_is_visible_to_its_source():
    """A signature the configured filter cannot see does nothing.

    This is the entry's own defect rebuilt inside its own fix: the whole
    reason the reset was unsayable is that the line naming it sat below
    ``severity_filter``.  ``arrives_at`` is declared so the pairing can
    be checked against the *shipped* config rather than against a
    fixture — ``max_priority_for`` admits ``0..N``, so a source is
    wide enough when its ceiling is at least the declaration's.
    """
    from pathlib import Path

    shipped = parse_config(Path("config.yaml")).agents.log_aggregator
    by_name = {s.name: s for s in shipped.sources}

    for (source_name, sig), declared in CRITICAL_SIGNATURES.items():
        assert source_name in by_name, (
            f"{source_name!r} declares {sig!r} and is not a configured source"
        )
        ceiling = max_priority_for(by_name[source_name].severity_filter)
        needed = max_priority_for(declared.arrives_at)
        assert ceiling >= needed, (
            f"{source_name} reads -p {ceiling}; {sig!r} arrives at "
            f"{declared.arrives_at} (-p {needed}) and would never be read"
        )


def test_the_producer_still_emits_what_the_key_matches():
    """A kernel reword fails silently, so the mapping is pinned.

    ``signature`` maps digit runs to ``N``, and the key is stored
    normalised — so this asserts the real line still lands on it.  The
    failure mode being silence is why this is a test and not a comment.
    """
    assert DECLARED_KEY in CRITICAL_SIGNATURES
    assert signature(VRAM_LOST) == "amdgpu N:N:N.N: amdgpu: VRAM is lost due to GPU reset!"


def test_the_declared_title_carries_no_rung():
    """The title must survive the ladder, so it cannot name a severity.

    ``alert_title`` builds ``"Log {severity}: {source} — "``, which would
    put ``Log info:`` on a ``critical`` toast and, worse, fork the dedup
    key at the moment the ladder climbs it.
    """
    for declared in CRITICAL_SIGNATURES.values():
        assert not declared.title.startswith("Log ")
        for rung in ("info", "warning", "critical", "error"):
            assert f"Log {rung}" not in declared.title


# --- The rung ----------------------------------------------------------


@pytest.mark.asyncio
async def test_an_info_line_raises_only_when_declared():
    """The gate widened for the declaration and for nothing else."""
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=0)
    result = await _run(agent, session, [_entry(VRAM_LOST), _entry(RING_USES_VM)])

    # Both lines are stored; only the declared one becomes a row.
    assert result.findings_count == 2
    assert [a.title for a in session.alerts] == [
        CRITICAL_SIGNATURES[DECLARED_KEY].title
    ]


@pytest.mark.asyncio
async def test_the_first_incident_is_the_floor():
    """One reset is survivable — the card came back."""
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=0)
    await _run(agent, session, [_entry(VRAM_LOST)])

    row = session.alerts[0]
    assert row.severity == DECLARED_FLOOR_SEVERITY
    assert row.details["prior_incidents"] == 0


@pytest.mark.asyncio
async def test_the_second_incident_is_critical():
    """Three in eight hours is a different claim from one in ten days."""
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=1)
    await _run(agent, session, [_entry(VRAM_LOST)])

    row = session.alerts[0]
    assert row.severity == "critical"
    assert row.details["prior_incidents"] == 1
    assert row.details["escalated_reason"]


@pytest.mark.asyncio
async def test_the_provenance_is_on_the_quiet_row_too():
    """Uniform on every declared row, so absence never carries the news.

    ``ports_checked``'s rule at the size of a dict key: a field present
    only on the escalated row makes its *absence* the signal, and a
    consumer cannot tell that from a producer that stopped publishing it.
    """
    agent = LogAggregatorAgent()
    quiet = _CountingSession(prior=0)
    loud = _CountingSession(prior=2)
    await _run(agent, quiet, [_entry(VRAM_LOST)])
    await _run(agent, loud, [_entry(VRAM_LOST)])

    for session in (quiet, loud):
        details = session.alerts[0].details
        assert "prior_incidents" in details
        assert "escalated_reason" in details


# --- Precedence --------------------------------------------------------


@pytest.mark.asyncio
async def test_known_noise_beats_the_declaration():
    """An operator's judgement outranks this module's own.

    The declaration is this family deciding how loud to be about itself;
    ``known_noise`` is somebody saying the fault is harmless.  A module
    that overrode that would make the config leaf unreadable, which is
    ``SNAG-CFG-001``'s shape arriving through the fix for a different
    silence.
    """
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=5)
    noise = [
        SimpleNamespace(
            source="kernel", signature=DECLARED_KEY[1], reason="bench rig, expected"
        )
    ]
    await _run(agent, session, [_entry(VRAM_LOST)], known_noise=noise)

    row = session.alerts[0]
    assert row.severity == NOISE_SEVERITY
    assert row.details["noise_reason"] == "bench rig, expected"
    # Quietened, never escalated — and never asked, so no count was run.
    assert session.count_statements == []


# --- The count ---------------------------------------------------------


@pytest.mark.asyncio
async def test_the_count_does_not_exclude_resolved_rows():
    """The previous incident's row is closed, by definition.

    ``_recent_incidents`` is only reached when ``_open_alerts`` found
    nothing under this title — that is what makes it a new incident
    rather than a recurrence.  Filtering on
    :func:`~sysadmin.core.models.alert.unresolved` would count exactly
    the rows that cannot be there and return ``0`` for ever, giving an
    escalation that can never fire.
    """
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=1)
    await _run(agent, session, [_entry(VRAM_LOST)])

    assert len(session.count_statements) == 1
    sql = str(
        session.count_statements[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "resolved" not in sql
    assert "alerts.title" in sql
    assert "alerts.agent" in sql
    assert "alerts.created_at" in sql


@pytest.mark.asyncio
async def test_the_window_is_the_configured_one():
    """The cutoff comes from ``critical_repeat_hours``, not a literal."""
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=0)
    before = datetime.now(UTC)
    await _run(agent, session, [_entry(VRAM_LOST)], repeat_hours=3.0)

    sql = str(
        session.count_statements[0].compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    # A three-hour window puts the cutoff three hours back, not 24.
    expected = (before - timedelta(hours=3)).strftime("%Y-%m-%dT%H")
    assert expected in sql.replace(" ", "T")


@pytest.mark.asyncio
async def test_one_incident_of_many_lines_asks_once():
    """Eleven signatures in one second must not be eleven counts.

    Only the declared line reaches the count, and a repeat of it folds
    into the same fault — so a reset's whole burst costs one query.
    """
    agent = LogAggregatorAgent()
    session = _CountingSession(prior=0)
    await _run(
        agent,
        session,
        [_entry(VRAM_LOST), _entry(VRAM_LOST), _entry(RESET_BEGIN),
         _entry(ILLEGAL_OPCODE, severity="error")],
    )

    assert len(session.count_statements) == 1
    declared_row = next(
        a for a in session.alerts if a.title == CRITICAL_SIGNATURES[DECLARED_KEY].title
    )
    assert declared_row.details["occurrences"] == 2
