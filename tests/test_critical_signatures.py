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
from sysadmin.monitor.journal import (
    JournalRead,
    admits,
    max_priority_for,
    read_ceiling,
)
from sysadmin.monitor.log_aggregator import (
    CRITICAL_SIGNATURES,
    DECLARED_FLOOR_SEVERITY,
    NOISE_SEVERITY,
    CriticalSignature,
    LogAggregatorAgent,
    declared_rungs_for,
)
from sysadmin.monitor.log_signature import signature
from sysadmin.monitor.services import stored_source_name

#: The live lines, verbatim from ``journalctl -k -b`` on 2026-09-03.
#: Typed from the journal rather than from documentation, because what a
#: declaration keys on is what the producer actually emits.
#:
#: **That journal was ``6.18.48-1-lts``, and the box reboots between
#: branches.**  Mainline dropped the redundant second ``amdgpu:`` by
#: ``7.2.2``, so this constant is one of *two* real spellings and pinning
#: the declaration against it alone is what let 2026-09-04's reset match
#: nothing.  Both are kept: both kernels are installed, and neither is
#: legacy.
VRAM_LOST = "amdgpu 0000:03:00.0: amdgpu: VRAM is lost due to GPU reset!"
VRAM_LOST_MAINLINE = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"
RESET_BEGIN = "amdgpu 0000:03:00.0: amdgpu: GPU reset begin!. Source:  1"
ILLEGAL_OPCODE = (
    "[drm:gfx_v11_0_bad_op_irq [amdgpu]] *ERROR* Illegal opcode in command stream "
)
RING_USES_VM = "amdgpu 0000:03:00.0: amdgpu: ring gfx_0.0.0 uses VM inv eng 0 on hub 0"

DECLARED_KEY = ("kernel", signature(VRAM_LOST))
SOURCE = LogSource(name="kernel", type="journalctl", unit="kernel",
                   severity_filter="info")

#: A declaration whose *content* is irrelevant: the key tests below are
#: about which string a signature is filed under, not about what it says.
_GPU_RESET_STANDIN = CriticalSignature(
    title="a declared fault", reason="a stand-in", arrives_at="info"
)


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


def _shipped_sources() -> dict[str, LogSource]:
    """The shipped log sources, keyed the way ``log_entries.source`` is.

    **Not by ``source.name``**, which is what this file asserted until
    ``SNAG-CFG-006`` was closed.  ``CRITICAL_SIGNATURES`` is matched in
    ``_execute`` against ``entry["source"]`` — the **unit** for a journal
    source, the **name** for a file one — so a name-keyed lookup agrees
    with the runtime only while the two strings coincide.  They do for
    ``kernel``, the only declared source today, which is exactly why the
    wrong key was green.
    """
    from pathlib import Path

    shipped = parse_config(Path("config.yaml")).agents.log_aggregator
    keyed = {}
    for source in shipped.sources:
        key = stored_source_name(source)
        if key is not None:
            keyed[key] = source
    return keyed


def test_every_declaration_names_a_source_that_is_actually_read():
    """The half of the old pairing test that is not now vacuous.

    A declaration for a source nobody reads produces nothing whatever
    the rungs say, and no derivation can fix that — the source has to
    exist.  What *is* vacuous now is the rung comparison this used to
    make: the reader derives its ceiling from the declaration, so the
    two cannot disagree and asserting that they agree would answer the
    same way either side of the fix — ``check_review_schedule_unread``'s
    defect.
    """
    keyed = _shipped_sources()

    for (source_key, sig), _declared in CRITICAL_SIGNATURES.items():
        assert source_key in keyed, (
            f"{source_key!r} declares {sig!r} and is not a source this "
            f"agent reads — configured sources store as {sorted(keyed)}"
        )


def test_a_narrowed_source_still_reads_its_declaration():
    """The fix, modelled at the edit that used to disarm it.

    ``sysadmin/reload.py`` re-reads ``config.yaml`` on ``SIGHUP``, and
    ``severity_filter`` is not ``RESTART_ONLY`` — it is re-read per run.
    So this drives the shipped source *narrowed to the value the
    declaration was written to survive* and asserts both gates still
    admit it.  Driven at a stand-in modelling the **fix**, not the
    defect: against the shipped ``info`` every assertion here passes for
    free.

    Live, either side of the change: at ``error`` the old reader stored
    32 kernel lines and **0** ``VRAM is lost due to GPU reset!``; the new
    one stores 35 and all **3**, with 1,788 undeclared info lines still
    dropped.
    """
    keyed = _shipped_sources()

    for (source_key, sig), declaration in CRITICAL_SIGNATURES.items():
        narrowed = keyed[source_key].model_copy(update={"severity_filter": "error"})
        rungs = declared_rungs_for(narrowed)

        assert sig in rungs, (
            f"{sig!r} is declared for {source_key!r} and "
            f"declared_rungs_for did not hand it to the reader"
        )
        # Half one: journalctl is asked for the line at all.
        assert read_ceiling(narrowed.severity_filter, rungs) >= max_priority_for(
            declaration.arrives_at
        )
        # Half two, which is the one the entry's own remedy omitted: the
        # Python gate stores it.  A line for which only the ceiling moved
        # is read and then discarded, measurably.
        assert admits(declaration.arrives_at, narrowed.severity_filter, sig, rungs)
        assert not admits(
            declaration.arrives_at, narrowed.severity_filter, sig, None
        ), "widening the ceiling alone stores nothing new"


def test_declared_rungs_are_keyed_the_way_the_runtime_keys_them():
    """A file source stores under its *name* and a journal source under
    its *unit*, and a declaration must reach both.

    Empty population — every declared source on this box is
    ``type: journalctl`` with ``name == unit`` — so this is driven at
    sources whose two identities differ, which is the only shape that can
    tell the right key from the wrong one.
    """
    journal = LogSource(name="gpu-watch", type="journalctl", unit="amdgpu.service")
    logfile = LogSource(name="legacy-app", type="file", path="/var/log/legacy.log")
    never_read = LogSource(name="half-declared", type="journalctl")

    declared = {
        ("amdgpu.service", "a unit-keyed signature"): _GPU_RESET_STANDIN,
        ("gpu-watch", "a name-keyed signature"): _GPU_RESET_STANDIN,
        ("legacy-app", "a file signature"): _GPU_RESET_STANDIN,
    }
    with patch(
        "sysadmin.monitor.log_aggregator.CRITICAL_SIGNATURES", declared
    ):
        assert declared_rungs_for(journal) == {"a unit-keyed signature": "info"}
        assert declared_rungs_for(logfile) == {"a file signature": "info"}
        # A source declaring neither a unit nor a path is never read, so
        # it can produce no rows — ``stored_source_name``'s ``None``, not
        # silently unioned into the map.
        assert declared_rungs_for(never_read) == {}


def test_signature_still_normalises_the_line_the_way_the_key_is_written():
    """``signature``'s treatment of the line, pinned as a value.

    This is the *narrow* half and it is worth naming what it cannot do.
    It pins :func:`signature` — digit runs to ``N``, the rest verbatim —
    so a change to the normaliser turns it red.  It says nothing about
    whether the **producer** still emits either of these lines, because
    both sides are constants typed on one day from one kernel.

    The version this replaced asserted ``DECLARED_KEY in
    CRITICAL_SIGNATURES`` with ``DECLARED_KEY`` derived from the same
    constant, which is a value compared against itself: green on every
    kernel, including the one that had already reworded the line.
    ``tests/test_critical_signature_live.py`` is the discriminating
    half — it reads what this box actually stored.
    """
    assert signature(VRAM_LOST) == "amdgpu N:N:N.N: amdgpu: VRAM is lost due to GPU reset!"
    assert signature(VRAM_LOST_MAINLINE) == "amdgpu N:N:N.N: VRAM is lost due to GPU reset!"


def test_both_kernel_spellings_are_declared():
    """Neither branch is legacy, so dropping either is a regression.

    ``linux`` and ``linux-lts`` are both installed and a ``linux``
    upgrade invalidates ``LoaderEntryDefault``, so the box can boot
    either without anybody choosing — the mechanism that put it on LTS
    on 2026-09-03.  A declaration covering one spelling is silent on
    roughly half of this box's boots.
    """
    for line in (VRAM_LOST, VRAM_LOST_MAINLINE):
        assert ("kernel", signature(line)) in CRITICAL_SIGNATURES, (
            f"{line!r} is emitted by an installed kernel and matches no "
            "declaration — the 2026-09-04 defect, in the other direction"
        )


def test_the_two_spellings_name_one_fault():
    """One reset must not explain itself two ways.

    Two equal literals are two statements of one fact and are free to
    drift — ``SNAG-DB-003``'s shape.  The keys share a value object, so
    a reworded ``reason`` cannot reach one kernel and miss the other.
    """
    declared = [CRITICAL_SIGNATURES[("kernel", signature(line))]
                for line in (VRAM_LOST, VRAM_LOST_MAINLINE)]
    assert declared[0] is declared[1]


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


class TestTheFileReaderSharesTheSameGate:
    """A declaration must not work for one source type and not the other.

    Empty population — every declared source on this box is
    ``type: journalctl`` — and written from the *producer* for
    ``stored_source_name``'s stated reason: a rule derived from the live
    table would omit this half and be green in every test until the
    first file source was declared.  A declaration that silently does
    nothing for a file source is ``SNAG-CFG-006`` wearing a second hat.
    """

    LINE = "some quiet line a declaration speaks for"

    def _read(self, tmp_path, declared):
        log = tmp_path / "legacy.log"
        log.write_text(f"{self.LINE}\nERROR something loud\nundeclared chatter\n")
        agent = LogAggregatorAgent()
        return agent._read_log_file("legacy-app", str(log), "error", 500, declared)

    def test_a_declared_line_below_the_floor_is_read(self, tmp_path) -> None:
        read = self._read(tmp_path, {signature(self.LINE): "info"})
        assert [e["message"] for e in read.entries] == [
            self.LINE,
            "ERROR something loud",
        ]

    def test_an_undeclared_line_below_the_floor_is_still_dropped(self, tmp_path) -> None:
        read = self._read(tmp_path, {signature(self.LINE): "info"})
        assert "undeclared chatter" not in [e["message"] for e in read.entries]

    def test_nothing_declared_reads_exactly_as_before(self, tmp_path) -> None:
        read = self._read(tmp_path, None)
        assert [e["message"] for e in read.entries] == ["ERROR something loud"]


class TestTheDerivedMappingActuallyReachesBothReaders:
    """The wiring, which nothing was driving.

    Every other test here hands ``declared`` to a reader itself, so
    ``declared=None`` at either call site passed the lot — the shape this
    repository keeps finding (*"nothing drove ``_record_start``, so
    deleting the stamp passed all twenty tests"*).  Both of these are
    behavioural rather than argument assertions: they go through the real
    ``read_journal`` and the real ``_read_log_file`` with a source
    narrowed to ``error``, and ask whether the declared line survived.
    """

    DECLARED = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"

    @staticmethod
    def _record(priority: str, message: str, cursor: str) -> str:
        import json

        return json.dumps(
            {
                "__CURSOR": cursor,
                "__REALTIME_TIMESTAMP": "1788514537787407",
                "PRIORITY": priority,
                "MESSAGE": message,
            }
        )

    @pytest.mark.asyncio
    async def test_the_journal_reader_is_handed_the_declaration(self) -> None:
        narrowed = SOURCE.model_copy(update={"severity_filter": "error"})
        agent = LogAggregatorAgent()
        # A cursor, so ``_resume_floor`` is never asked and no session is
        # needed — the resume path is a different rule and is tested with
        # its own file.
        agent._cursors[narrowed.name] = "c0"
        stdout = "\n".join(
            [
                self._record("3", "ring gfx_0.0.0 timeout", "c1"),
                self._record("6", self.DECLARED, "c2"),
                self._record("6", "undeclared kernel chatter", "c3"),
            ]
        )

        with patch(
            "sysadmin.monitor.journal._run", new=AsyncMock(return_value=stdout)
        ) as run:
            read = await agent._read_journal_source(None, narrowed, 500)

        assert run.call_args[0][0][run.call_args[0][0].index("-p") + 1] == "6"
        assert [e["message"] for e in read.entries] == [
            "ring gfx_0.0.0 timeout",
            self.DECLARED,
        ]

    @pytest.mark.asyncio
    async def test_the_file_reader_is_handed_the_declaration(self, tmp_path) -> None:
        line = "a quiet line a declaration speaks for"
        log = tmp_path / "legacy.log"
        log.write_text(f"{line}\nundeclared chatter\n")
        source = LogSource(
            name="legacy-app", type="file", path=str(log), severity_filter="error"
        )
        agent = LogAggregatorAgent()
        session = _CountingSession()

        declared = {("legacy-app", signature(line)): _GPU_RESET_STANDIN}
        with (
            patch(
                "sysadmin.monitor.log_aggregator.get_config", return_value=_config()
            ),
            patch.object(
                LogAggregatorAgent, "_sources", staticmethod(lambda _c: [source])
            ),
            patch("sysadmin.monitor.log_aggregator.CRITICAL_SIGNATURES", declared),
        ):
            await agent._execute(session)

        ingested = [e.message for e in session.added if hasattr(e, "raw_line")]
        assert line in ingested
        assert "undeclared chatter" not in ingested
