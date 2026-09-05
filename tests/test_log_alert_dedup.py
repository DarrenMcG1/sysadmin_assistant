"""SNAG-AGENT-005 — a log line is an event, and events are not alert rows.

``LogAggregatorAgent`` raised **one alert row per matching log entry**.
Counted live on 2026-08-12, unresolved, ``agent='log_aggregator'``:

===========================================  =======  ====================
title                                           rows  range
===========================================  =======  ====================
``Log error: kernel``                        593,814  2026-03-24 → 08-12
``Log critical: ollama.service``                  29  service retired 07-24
``Log error: alfred-backend.service``             23
===========================================  =======  ====================

That is 91 % of every unresolved alert in the table, and 99.8 % of it is
**two** Bluetooth firmware messages emitted in a kernel retry loop every
~0.58 s.  A missing firmware blob produced half a million alert rows.

**Why the SNAG-AGENT-004 fix does not apply.** That one asks "which of my
open alerts would this run *not* raise?", which only means something for a
*state*.  A log line that was written cannot un-write itself, so the
answer here is "all of them, one run later" — an alert type with a
lifetime of one poll.  The fix is therefore a **raise** rule, and the
resolve that follows it is time-based.

**What these tests can and cannot show.**  Sessions are mocked, so a
``WHERE`` clause has no effect and ``_resolve_quiet``'s predicates are
asserted on compiled SQL — that they are *in* the statement, not that
PostgreSQL evaluates them as intended.  The dedup half needs no database:
it is decided in Python, before any row is built, which is the point of
moving the raise out of the entry loop.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.core.agent import AGENT_RUN_FAILED_EVENT, BaseAgent
from sysadmin.core.config import LogSource
from sysadmin.core.models.alert import Alert
from sysadmin.core.text import TRUNCATION_MARKER
from sysadmin.core.unit_failure import OWN_UNIT
from sysadmin.monitor.journal import JournalRead
from sysadmin.monitor.log_aggregator import (
    COVERED_SIGNATURES,
    NOISE_SEVERITY,
    LogAggregatorAgent,
)
from sysadmin.monitor.log_signature import TITLE_MAX, alert_title, signature

# The live 30-day kernel population, verbatim.  These are the messages the
# normalisation rules were chosen against, so they are the ones that must
# keep working.
BLUETOOTH_A = "Bluetooth: hci0: Failed to set up firmware (-2)"
BLUETOOTH_B = "Bluetooth: hci0: Failed to load firmware file (-2)"
USB_TIMEOUT = "usb 1-11: device descriptor read/64, error -110"
USB_PROTO_9 = "usb 1-11: device not accepting address 9, error -71"
USB_PROTO_10 = "usb 1-11: device not accepting address 10, error -71"
RCU_STALL = (
    "rcu: \tTasks blocked on level-1 rcu_node (CPUs 0-15): P657968/1:b..l"
)
HUNG_TASK = (
    "INFO: task (idle-watcher.):658024 is blocked on a mutex "
    "likely owned by task 657968"
)


# --- The signature ------------------------------------------------------


def test_variable_parts_collapse():
    """Device index, PID and errno stop forking the identity."""
    assert signature(USB_PROTO_9) == signature(USB_PROTO_10)
    assert signature(BLUETOOTH_A) == signature(
        "Bluetooth: hci1: Failed to set up firmware (-2)"
    )


def test_distinct_faults_stay_distinct():
    """The storm must not swallow the faults that matter.

    This is the whole argument for signature-keyed dedup over
    source-keyed dedup: all of these share the title ``Log error: kernel``
    and all of them are in the same live 30-day window, so plain dedup
    would have left the RCU stall unannounced behind 594,779 Bluetooth
    lines.
    """
    sigs = {
        signature(m)
        for m in (BLUETOOTH_A, BLUETOOTH_B, USB_TIMEOUT, USB_PROTO_9, RCU_STALL,
                  HUNG_TASK)
    }
    assert len(sigs) == 6


def test_whitespace_does_not_fork_the_identity():
    """The kernel indents continuation lines; layout is not identity."""
    assert signature(RCU_STALL) == signature(RCU_STALL.replace("\t", "    "))


def test_hex_collapses_whole():
    """0x1f must not become 0xNf — one signature per address defeats the point."""
    assert signature("BUG: unable to handle page fault at 0x1f") == signature(
        "BUG: unable to handle page fault at 0xdeadbeef"
    )


def test_title_fits_the_column():
    """``alerts.title`` is String(255); an over-long title is an insert error.

    The marker is asserted as *present* rather than as the last thing in
    the string, because a cut title now ends with its discriminator —
    see :class:`TestACutTitleStaysAnIdentity`.  This assertion is what
    pinned that defect: it required the cut to be **marked** and never
    that it stayed **distinguishing**, which are different properties and
    only the first was being bought.
    """
    title = alert_title("error", "kernel", "x" * 4000)
    assert len(title) <= TITLE_MAX
    assert TRUNCATION_MARKER in title


class TestACutTitleStaysAnIdentity:
    """``SNAG-LOG-013`` at the surface its own cost bullet excludes.

    That entry prices the defeat of a cap at *"a GET advice surface, no
    toast and no row"*.  :func:`alert_title` is the dedup key, the
    set-based resolve's key and the tray's ``{severity}:{title}``
    fingerprint, so two faults agreeing past the title budget are one
    row, one fingerprint and one toast — which is this file's own
    ``SNAG-AGENT-005`` read backwards: not four faults wearing one
    uninformative title, but sixteen wearing one informative-looking one.

    Measured on the population the entry observed, recovered from
    ``raw_line`` because ``SNAG-LOG-008``'s backfill has since rewritten
    ``message``: **39 distinct signatures collapsed to 21 titles**, four
    of them covering 2, 2, 2 and 16 faults.  After the digest, 39 → 39.
    """

    #: Every traceback this daemon writes opens with the same two frames,
    #: so the first 211 characters — the whole of a ``sysadmin.service``
    #: title's budget — are boilerplate.  Verbatim from the live journal.
    LIFESPAN_FRAME = (
        "Traceback (most recent call last): "
        'File "/home/gaddi/projects/sysadmin_assistant/.venv/lib/python3.12/'
        'site-packages/starlette/routing.py", line 694, in lifespan '
        "async with self.lifespan_context(app) as maybe_state: "
    )

    def test_two_faults_agreeing_past_the_budget_are_two_rows(self):
        """The live near-miss, driven: two lifespan-time failures.

        This is one second startup fault away from being the live
        population — ``schema_guard`` raises exactly here — so it is the
        specimen rather than a construction.
        """
        first = alert_title(
            "error", OWN_UNIT, self.LIFESPAN_FRAME + "ValueError: schema is at 017, code wants 018"
        )
        second = alert_title(
            "error", OWN_UNIT, self.LIFESPAN_FRAME + "RuntimeError: could not reach the broker"
        )
        assert first != second
        assert len(first) <= TITLE_MAX
        assert len(second) <= TITLE_MAX

    def test_the_shared_half_is_still_readable(self):
        """The discriminator is added, never substituted for the text.

        A digest that *replaced* the cut signature would buy identity by
        giving the reader nothing at all, which is the state
        ``SNAG-AGENT-005`` describes and this module's docstring refuses.
        """
        title = alert_title("error", OWN_UNIT, self.LIFESPAN_FRAME + "ValueError: boom")
        assert title.startswith(f"Log error: {OWN_UNIT} — Traceback (most recent call last):")
        assert TRUNCATION_MARKER in title

    def test_an_uncut_title_carries_no_discriminator(self):
        """Only a cut title is stamped, so no open row's fingerprint moves.

        The deploy cost of this change is exactly the set of open rows
        whose title was cut; on this box that was **0** (three such rows
        all-time, all resolved).  Stamping every title would have made it
        every open log row instead.
        """
        assert alert_title("error", "kernel", USB_PROTO_9) == (
            "Log error: kernel — usb N-N: device not accepting address N, error -N"
        )

    def test_one_signature_keeps_one_title(self):
        """The digest is of the *signature*, never of the message.

        Several messages share one signature by design — that is the
        whole of :func:`signature` — so digesting the message would fork
        the identity per errno and rebuild the pile-up this file is
        about.  ``USB_PROTO_9`` and ``USB_PROTO_10`` are the live pair
        that proves it, lengthened past the budget so the cut path runs.
        """
        pad = " padding" * 40
        assert alert_title("error", "kernel", USB_PROTO_9 + pad) == alert_title(
            "error", "kernel", USB_PROTO_10 + pad
        )

    def test_the_discriminator_does_not_depend_on_the_process(self):
        """``hashlib``, not the builtin ``hash``, which ``PYTHONHASHSEED``
        salts per process — the aggregator and
        :mod:`sysadmin.monitor.log_trends` would then disagree about one
        fault's identity across a restart, which is the defect the suffix
        exists to remove arriving through its own fix.
        """
        import subprocess
        import sys

        script = (
            "from sysadmin.monitor.log_signature import alert_title;"
            "print(alert_title('error', 'kernel', 'x' * 4000))"
        )
        runs = {
            subprocess.run(  # noqa: S603 — this interpreter, a fixed script
                [sys.executable, "-c", script],
                capture_output=True,
                text=True,
                check=True,
                env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin"},
            ).stdout
            for seed in ("0", "1", "random")
        }
        assert len(runs) == 1


def test_title_carries_the_signature():
    """``Log error: kernel`` told a reader nothing — four open rows with that
    text are indistinguishable on the tray."""
    title = alert_title("error", "kernel", USB_PROTO_9)
    assert title.startswith("Log error: kernel")
    assert "device not accepting address N" in title


# --- The raise rule -----------------------------------------------------


def _entry(message: str, severity: str = "error", source: str = "kernel"):
    return {
        "source": source,
        "severity": severity,
        "message": message,
        "logged_at": datetime.now(UTC),
        "raw_line": message,
        "metadata": {},
    }


class _Session:
    """Mock session recording adds, and answering the three queries."""

    def __init__(self, open_alerts: list[Alert] | None = None):
        self.added: list[object] = []
        self.statements: list[object] = []
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
        if "max(" in text:
            result.scalar_one_or_none.return_value = None
            return result
        result.scalars.return_value.all.return_value = self._open
        return result

    @property
    def alerts(self) -> list[Alert]:
        return [a for a in self.added if isinstance(a, Alert)]


def _config(quiet_minutes: int = 15, limit: int = 500, known_noise=None):
    return SimpleNamespace(
        agents=SimpleNamespace(
            log_aggregator=SimpleNamespace(
                sources=[],
                alert_quiet_minutes=quiet_minutes,
                max_entries_per_read=limit,
                # Empty by default, and that is the *loud* default —
                # absent evidence must mean "not noise". Session 48's
                # ``UnitFinding.enabled`` trap is one field with two
                # consumers wanting opposite safe defaults; this one has
                # a single safe default and it is this one.
                known_noise=known_noise or [],
            )
        )
    )


#: The real model rather than a ``SimpleNamespace`` stand-in.
#:
#: A hand-built namespace is a second declaration of ``LogSource``'s
#: fields that nothing keeps in step, and it drifted the moment ``format``
#: was added: the agent read ``source.format``, the box was fine and
#: twelve tests raised ``AttributeError``. Constructing the model makes
#: the fixture inherit every future field with its production default —
#: ``UnitFinding.enabled``'s trap answered in the fixture rather than by
#: softening the read, since ``getattr(source, "format", "text")`` would
#: swallow a genuine wiring failure.
SOURCE = LogSource(
    name="kernel", type="journalctl", unit="kernel",
    severity_filter="error", user=False, path=None,
)


async def _run(agent, session, entries, *, truncated=False, cursor="c1",
               known_noise=None):
    read = JournalRead(entries=entries, cursor=cursor, truncated=truncated)
    with (
        patch("sysadmin.monitor.log_aggregator.get_config",
              return_value=_config(known_noise=known_noise)),
        patch.object(LogAggregatorAgent, "_sources", staticmethod(lambda _c: [SOURCE])),
        patch("sysadmin.monitor.log_aggregator.read_journal",
              AsyncMock(return_value=read)) as reader,
    ):
        result = await agent._execute(session)
    return result, reader


@pytest.mark.asyncio
async def test_one_alert_for_a_storm():
    """1,000 copies of one message is one incident, not 1,000 rows."""
    agent = LogAggregatorAgent()
    session = _Session()
    result, _ = await _run(agent, session, [_entry(BLUETOOTH_A) for _ in range(1000)])

    assert len(session.alerts) == 1
    assert result.alerts_raised == 1
    # The count that used to be expressed as row volume.
    assert session.alerts[0].details["occurrences"] == 1000
    # Every line is still stored — the log is the record, the alert is not.
    assert result.findings_count == 1000


@pytest.mark.asyncio
async def test_the_storm_does_not_mask_the_stall():
    """The regression signature-keyed dedup exists to prevent."""
    agent = LogAggregatorAgent()
    session = _Session()
    entries = [_entry(BLUETOOTH_A) for _ in range(500)] + [_entry(RCU_STALL)]
    result, _ = await _run(agent, session, entries)

    assert result.alerts_raised == 2
    assert any("rcu_node" in a.title for a in session.alerts)


@pytest.mark.asyncio
async def test_repeat_bumps_the_open_row():
    """A fault already alerted on must not raise a second row."""
    agent = LogAggregatorAgent()
    open_row = Alert(
        agent="log_aggregator",
        severity="warning",
        title=alert_title("error", "kernel", BLUETOOTH_A),
        message=BLUETOOTH_A,
        details={"source": "kernel", "occurrences": 7},
    )
    session = _Session(open_alerts=[open_row])
    result, _ = await _run(agent, session, [_entry(BLUETOOTH_A) for _ in range(3)])

    assert session.alerts == []
    assert result.alerts_raised == 0
    assert open_row.details["occurrences"] == 10
    assert open_row.details["last_seen_at"]


@pytest.mark.asyncio
async def test_details_are_reassigned_not_mutated():
    """SQLAlchemy does not track mutation inside a plain JSONB dict.

    An in-place update looks like it worked and writes nothing — and
    ``last_seen_at`` never moving means the row is resolved on the next
    quiet sweep while its fault is still firing.
    """
    original = {"source": "kernel", "occurrences": 1}
    open_row = Alert(
        agent="log_aggregator",
        severity="warning",
        title=alert_title("error", "kernel", BLUETOOTH_A),
        details=original,
    )
    session = _Session(open_alerts=[open_row])
    await _run(agent := LogAggregatorAgent(), session, [_entry(BLUETOOTH_A)])
    assert agent is not None
    assert open_row.details is not original
    assert original["occurrences"] == 1


@pytest.mark.asyncio
async def test_open_alert_lookup_is_bounded_by_this_run():
    """The obvious query would have loaded 593,814 ORM objects on run one.

    ``SELECT * FROM alerts WHERE agent = 'log_aggregator' AND NOT resolved``
    is the natural way to write this and would have fallen over on exactly
    the backlog the fix exists to end.  A run only needs the rows it might
    bump.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(agent, session, [_entry(BLUETOOTH_A), _entry(RCU_STALL)])

    selects = [s for s in session.statements if str(s).startswith("SELECT")]
    lookup = next(s for s in selects if "alerts" in str(s))
    sql = _compiled(lookup)
    assert "title IN" in sql
    assert "device" not in sql  # sanity: it is the alert query, not a log one


@pytest.mark.asyncio
async def test_no_lookup_when_nothing_alerted():
    """A quiet poll must not query for an empty title set."""
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(agent, session, [_entry("all is well", severity="info")])
    assert not [
        s
        for s in session.statements
        if "alerts" in str(s) and str(s).startswith("SELECT")
    ]


@pytest.mark.asyncio
async def test_truncation_is_named_not_swallowed():
    """``findings_count`` sat at exactly 200 on every run and nobody read it."""
    agent = LogAggregatorAgent()
    session = _Session()
    result, _ = await _run(agent, session, [_entry(BLUETOOTH_A)], truncated=True)
    assert result.details["truncated_sources"] == ["kernel"]


# --- Resuming -----------------------------------------------------------


@pytest.mark.asyncio
async def test_second_poll_resumes_from_the_cursor():
    """``since='2m ago'`` on a 60s poll ingested every entry exactly twice."""
    agent = LogAggregatorAgent()
    session = _Session()
    _, first = await _run(agent, session, [_entry(BLUETOOTH_A)], cursor="cursor-1")
    assert first.await_args.kwargs["after_cursor"] is None

    _, second = await _run(agent, _Session(), [_entry(BLUETOOTH_A)], cursor="cursor-2")
    assert second.await_args.kwargs["after_cursor"] == "cursor-1"


@pytest.mark.asyncio
async def test_cold_start_floors_on_stored_data():
    """The cursor is in memory; a restart must not re-ingest a window."""
    agent = LogAggregatorAgent()
    floor = datetime(2026, 8, 12, 15, 0, tzinfo=UTC)

    class _Floored(_Session):
        async def execute(self, statement, *args, **kwargs):
            if "max(" in str(statement):
                result = MagicMock()
                result.scalar_one_or_none.return_value = floor
                return result
            return await super().execute(statement, *args, **kwargs)

    _, reader = await _run(agent, _Floored(), [_entry(BLUETOOTH_A)])
    assert reader.await_args.kwargs["since"] == f"@{int(floor.timestamp())}"


# --- The quiet resolve --------------------------------------------------


def _compiled(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


@pytest.mark.asyncio
async def test_quiet_resolve_predicates():
    agent = LogAggregatorAgent()
    session = _Session()
    now = datetime(2026, 8, 12, 16, 0, tzinfo=UTC)
    await agent._resolve_quiet(session, {"Log error: kernel — x"}, 15, now)

    sql = _compiled(session.statements[-1])
    assert "UPDATE sysadmin.alerts" in sql
    # Scoped to this agent's own rows.
    assert "agent = 'log_aggregator'" in sql
    # Age is measured from last_seen_at, falling back to created_at so the
    # pre-existing backlog is reachable at all.
    assert "last_seen_at" in sql
    assert "created_at" in sql
    assert "coalesce" in sql.lower()
    # Anything seen this run is excluded by exact title, which cannot race
    # the clock that stamped it.
    assert "NOT IN" in sql


@pytest.mark.asyncio
async def test_quiet_window_is_the_configured_gap():
    agent = LogAggregatorAgent()
    session = _Session()
    now = datetime(2026, 8, 12, 16, 0, tzinfo=UTC)
    await agent._resolve_quiet(session, set(), 45, now)
    assert str(now - timedelta(minutes=45)) in _compiled(session.statements[-1])


# ---------------------------------------------------------------------------
# known_noise — quietened, never suppressed (Session 27, Tier 2)
# ---------------------------------------------------------------------------


def _noise(source, message, reason="measured harmless"):
    from sysadmin.core.config import LogNoiseEntry

    return LogNoiseEntry(
        source=source, signature=signature(message), reason=reason
    )


@pytest.mark.asyncio
async def test_a_declared_signature_is_quietened_not_dropped():
    """The row still exists, still counts, and stops interrupting.

    Dropping it was the obvious implementation and rebuilds
    ``SNAG-CFG-001``'s shape: a decision taken by a consumer with nothing
    recording that it was taken. Session 57 settled this for the ports
    family; this is the same argument one domain over.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    result, _ = await _run(
        agent, session, [_entry(BLUETOOTH_A) for _ in range(1000)],
        known_noise=[_noise("kernel", BLUETOOTH_A)],
    )

    assert len(session.alerts) == 1
    row = session.alerts[0]
    assert row.severity == NOISE_SEVERITY
    # Still counted, and still stored — quietened is not suppressed.
    assert row.details["occurrences"] == 1000
    assert result.findings_count == 1000
    # The operator's own justification travels with the row.
    assert row.details["noise_reason"] == "measured harmless"


@pytest.mark.asyncio
async def test_the_pair_is_the_key_not_the_signature_alone():
    """A signature declared for one source must not silence another.

    ``Failed with result 'exit-code'.`` is logged by six services on this
    box; keying on the signature alone would silence a genuine failure in
    five of them.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(
        agent, session,
        [_entry(BLUETOOTH_A), _entry(BLUETOOTH_A, source="other")],
        known_noise=[_noise("kernel", BLUETOOTH_A)],
    )

    by_source = {a.details["source"]: a.severity for a in session.alerts}
    assert by_source["kernel"] == NOISE_SEVERITY
    assert by_source["other"] == "warning"


@pytest.mark.asyncio
async def test_an_undeclared_signature_is_untouched():
    """Absent evidence means "not noise", which is the loud default."""
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(agent, session, [_entry(RCU_STALL)],
               known_noise=[_noise("kernel", BLUETOOTH_A)])

    assert session.alerts[0].severity == "warning"
    assert "noise_reason" not in session.alerts[0].details


@pytest.mark.asyncio
async def test_a_new_declaration_quietens_a_row_that_is_already_open():
    """``SNAG-ESTATE-010``, and why this family cannot wait it out.

    Dedup skips a judgement whose title is already open, so a change that
    makes a family quieter normally reaches nothing standing when it
    ships. Here that is fatal rather than untidy: a signature loud enough
    to be worth declaring is by definition one that never goes quiet, so
    its row never resolves and the operator's edit would take effect
    approximately never.
    """
    agent = LogAggregatorAgent()
    open_row = Alert(
        agent="log_aggregator",
        severity="warning",
        title=alert_title("error", "kernel", BLUETOOTH_A),
        message=BLUETOOTH_A,
        details={"source": "kernel", "occurrences": 297_390},
    )
    session = _Session(open_alerts=[open_row])
    result, _ = await _run(agent, session, [_entry(BLUETOOTH_A)],
                           known_noise=[_noise("kernel", BLUETOOTH_A)])

    # No second row: the identity did not move, only the volume did.
    assert result.alerts_raised == 0
    assert open_row.severity == NOISE_SEVERITY
    assert open_row.details["occurrences"] == 297_391
    assert open_row.details["noise_reason"] == "measured harmless"


@pytest.mark.asyncio
async def test_the_in_place_change_is_one_directional():
    """Raising severity in place would be Session 39's defect verbatim.

    The tray fingerprints on ``{severity}:{title}``, so an in-place bump
    keeps a fingerprint it has already suppressed and the escalation is
    recorded but never spoken. Going *down* wants exactly that outcome,
    which is why the asymmetry is the point rather than an oversight: a
    quietening must be silenced, an escalation must be heard.
    """
    agent = LogAggregatorAgent()
    open_row = Alert(
        agent="log_aggregator",
        severity=NOISE_SEVERITY,
        title=alert_title("error", "kernel", BLUETOOTH_A),
        message=BLUETOOTH_A,
        details={"source": "kernel", "occurrences": 5},
    )
    session = _Session(open_alerts=[open_row])
    # No noise declaration now — the fault "wants" to be a warning again.
    await _run(agent, session, [_entry(BLUETOOTH_A)])

    assert open_row.severity == NOISE_SEVERITY
    assert "noise_reason" not in open_row.details


@pytest.mark.asyncio
async def test_the_signature_is_recorded_on_the_row():
    """``details['signature']`` is what ``known_noise`` is keyed on.

    Without it the operator has to re-derive the normalisation by hand to
    write the config entry — which is the second implementation
    ``log_trends`` rule 1 exists to avoid, performed by a human.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(agent, session, [_entry(BLUETOOTH_A)])
    assert session.alerts[0].details["signature"] == signature(BLUETOOTH_A)


# ---------------------------------------------------------------------------
# COVERED_SIGNATURES — a fault another family owns (Session 65, SNAG-LOG-005)
# ---------------------------------------------------------------------------
#
# The collision could not exist before 2026-08-17: ``log_entries`` held no
# rows at all for ``sysadmin.service`` until Session 61 put a level prefix
# on this daemon's JSON, and the message was an unreadable JSON document
# until Session 64 made the source declare its format.  Two fixes that
# widened what the monitor can see are what made a second producer for one
# fault visible — which is the argument for them rather than against.

#: The unwrapped message a failing agent leaves in the journal.  It is the
#: event constant itself, because ``unwrap_json_message`` lifts
#: ``"message"`` out of the envelope and that field carries exactly this.
AGENT_FAILURE_LINE = AGENT_RUN_FAILED_EVENT

#: An error this daemon writes that **no** other family covers, so it must
#: stay loud.  Live counts behind the choice: of 249 error incidents in
#: this journal, 34 carry ``scheduler_job_error`` and no
#: ``agent_run_failed`` at all — ``file_organiser_scan`` ×27 (the run
#: record died with the run) and ``retention_purge`` ×7, which is not an
#: agent and has no owning family anywhere.
UNCOVERED_LINE = "scheduler_job_error"

OWN_SOURCE = LogSource(
    name="sysadmin-service", type="journalctl", unit=OWN_UNIT,
    severity_filter="warning", user=False, path=None, format="json",
)


async def _run_own(agent, session, entries, **kwargs):
    """``_run`` against this daemon's own journal source."""
    with patch.object(
        LogAggregatorAgent, "_sources", staticmethod(lambda _c: [OWN_SOURCE])
    ):
        return await _run(agent, session, entries, **kwargs)


@pytest.mark.asyncio
async def test_a_covered_signature_is_quietened_not_dropped():
    """``failures.py`` speaks; this family records and stays silent.

    Dropping the row was candidate (a) in the snag and rebuilds
    ``SNAG-CFG-001``'s shape — a decision taken by a consumer with nothing
    recording that it was taken.  The row still counts occurrences, still
    reaches ``GET /api/logs/trends``, and names the family that will
    speak.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    result, _ = await _run_own(
        agent, session,
        [_entry(AGENT_FAILURE_LINE, source=OWN_UNIT) for _ in range(4)],
    )

    assert len(session.alerts) == 1
    row = session.alerts[0]
    assert row.severity == NOISE_SEVERITY
    assert row.details["occurrences"] == 4
    assert result.findings_count == 4
    # Named, never merely flagged — details['truncated_sources']'s rule.
    assert "failures.py" in row.details["covered_by"]
    # The two quietening reasons stay apart: this is not an operator's
    # judgement that the fault is harmless.
    assert "noise_reason" not in row.details


@pytest.mark.asyncio
async def test_another_service_logging_the_same_word_is_untouched():
    """Rule 3 — the source is half the key.

    ``agent_run_failed`` from anything but this unit has no
    ``failures.py`` row behind it, so quietening it on the strength of
    this daemon's arrangement silences a fault nothing else reports.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    await _run(agent, session, [_entry(AGENT_FAILURE_LINE, source="kernel")])

    assert session.alerts[0].severity == "warning"
    assert "covered_by" not in session.alerts[0].details


@pytest.mark.asyncio
async def test_this_daemons_uncovered_errors_stay_loud():
    """Rule 4 — scoped to the signature, never to the unit.

    Candidate (b) in the snag was to exclude ``OWN_UNIT`` from the alert
    half entirely.  Refused on measurement: ``retention_purge`` is not an
    agent, so ``scheduler_job_error`` is the only witness its failures
    have, and 7 live incidents are exactly that.
    """
    agent = LogAggregatorAgent()
    session = _Session()
    await _run_own(
        agent, session,
        [_entry(UNCOVERED_LINE, source=OWN_UNIT),
         _entry(AGENT_FAILURE_LINE, source=OWN_UNIT)],
    )

    by_title = {a.title: a for a in session.alerts}
    assert len(by_title) == 2
    loud = by_title[alert_title("error", OWN_UNIT, UNCOVERED_LINE)]
    quiet = by_title[alert_title("error", OWN_UNIT, AGENT_FAILURE_LINE)]
    assert loud.severity == "warning"
    assert "covered_by" not in loud.details
    assert quiet.severity == NOISE_SEVERITY


@pytest.mark.asyncio
async def test_a_deploy_quietens_a_row_that_is_already_open():
    """The in-place quietening reaches the row raised by the old release.

    ``known_noise``'s entry arrives when an operator edits config.yaml,
    which the next poll re-reads.  A covered signature arrives at a
    *deploy*, so the open row it must reach was raised loudly by the
    previous release — and this family's rows do not resolve themselves
    while the fault keeps firing.  Session 39's ban on in-place severity
    changes is asymmetric, and this is the direction it permits.
    """
    agent = LogAggregatorAgent()
    open_row = Alert(
        agent="log_aggregator",
        severity="warning",
        title=alert_title("error", OWN_UNIT, AGENT_FAILURE_LINE),
        message=AGENT_FAILURE_LINE,
        details={"source": OWN_UNIT, "occurrences": 9},
    )
    session = _Session(open_alerts=[open_row])
    await _run_own(agent, session, [_entry(AGENT_FAILURE_LINE, source=OWN_UNIT)])

    assert session.alerts == []
    assert open_row.severity == NOISE_SEVERITY
    assert "failures.py" in open_row.details["covered_by"]
    assert open_row.details["occurrences"] == 10


def test_the_key_survives_the_normalisation_it_is_matched_through():
    """The exclusion is keyed on a *signature*, not on the raw message.

    ``signature()`` maps digit runs to ``N``, so an event name carrying a
    number would be normalised into something
    :data:`COVERED_SIGNATURES` does not hold — and the failure mode is
    silence, not an error: the entry would simply never match and the
    duplicate toast would come back.
    """
    assert signature(AGENT_RUN_FAILED_EVENT) == AGENT_RUN_FAILED_EVENT
    assert (OWN_UNIT, signature(AGENT_RUN_FAILED_EVENT)) in COVERED_SIGNATURES


@pytest.mark.asyncio
async def test_the_emitter_still_emits_what_the_exclusion_keys_on(caplog):
    """The pin, driven through the real ``BaseAgent.run``.

    Both halves of the key are somebody else's fact — ``OWN_UNIT`` is the
    unit's, ``AGENT_RUN_FAILED_EVENT`` is ``BaseAgent``'s — and an
    exclusion keyed on a stale copy fails *silently*, which is the
    ``SNAG-DB-003`` shape.  Asserting the constant against itself proves
    nothing, so this drives a real failing run and keys on what the
    logger actually emitted.
    """
    from contextlib import asynccontextmanager

    class _Boom(BaseAgent):
        name = "log_aggregator"

        async def _execute(self, session):
            raise RuntimeError("check constraint violated")

    @asynccontextmanager
    async def _session():
        session = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        yield session

    with (
        caplog.at_level("ERROR", logger="sysadmin.core.agent"),
        patch("sysadmin.core.agent.get_scheduler_session", _session),
    ):
        await _Boom().run()

    emitted = [r.getMessage() for r in caplog.records if r.name == "sysadmin.core.agent"]
    assert emitted, "the failing run wrote no ERROR line"
    assert any((OWN_UNIT, signature(m)) in COVERED_SIGNATURES for m in emitted), (
        f"nothing BaseAgent.run emitted matches COVERED_SIGNATURES: {emitted}"
    )
