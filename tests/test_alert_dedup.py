"""SNAG-AGENT-006 — one fault, one row, for as long as it lasts.

``sysadmin-organiser-timer critical`` held **60** unresolved rows raised
between 07:41 and 12:36 on 2026-08-13, one every 300 s, for a single
dead timer.  ``venture-chat unreachable`` reached 85 across 36 hours and
``redis unreachable`` 6,283 before Session 41 gave the family a resolve
path at all.  The tray was never the victim — it fingerprints on
``{severity}:{title}``, so sixty rows are one toast — but
``GET /api/sysadmin/alerts`` and every count built on ``resolved =
false`` read sixty times high.

**The lifecycle is what has to be pinned, not the raise.** The snag was
filed saying dedup and ``_resolve_recovered`` are mutually exclusive,
because that sweep's exclusion set held the titles the run *raised*: a
family that writes nothing on its second run has its still-true row
swept, re-raised on the third and swept on the fourth, and every flip
clears the tray fingerprint so one fault notifies on every poll.  So a
test that only checks "run two writes no row" would pass against the
broken version.  Four runs are driven here — fault, fault again, fault
gone, fault back — because runs 2 and 3 are the two the naive
implementation gets wrong in opposite directions.

**What this file can and cannot show.**  ``FakeAlerts`` applies the
resolve by reading the ``NOT IN`` list off the compiled statement and
matching :data:`RESOLVABLE_TITLE_PATTERNS` in Python — the same stand-in
for SQL ``LIKE`` that ``tests/test_alert_recovery.py`` documents, and
the same limit: it proves the statement says what it means to say, not
that PostgreSQL evaluates it that way.  What it does prove end to end is
the *sequence*, which no amount of statement inspection can.
"""

import re
from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import Update
from sqlalchemy.dialects import postgresql

from sysadmin.core.models.alert import Alert
from sysadmin.estate import client as estate_client
from sysadmin.monitor.agent import (
    _NO_ARBITRATION,
    RESOLVABLE_TITLE_PATTERNS,
    SysAdminAgent,
)
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.services import ServiceEntry

TIMER = "sysadmin-organiser-timer"
TIMER_ALERT = f"{TIMER} critical"
DISK_ALERT = "Critical disk usage on /"


def _like(pattern: str, value: str) -> bool:
    """SQL ``LIKE`` for the ``%``-only patterns in the tuple."""
    return re.fullmatch(re.escape(pattern).replace("%", ".*"), value) is not None


def _title_equals(statement) -> str | None:
    """The ``alerts.title = '…'`` this statement asks for, if it asks for one."""
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    match = re.search(r"alerts\.title = '(.*?)'", sql)
    return match.group(1) if match else None


class FakeAlerts:
    """The ``alerts`` rows this agent can see, kept across runs.

    Rows survive between runs deliberately: the defect is a property of
    run *N+1* seeing what run *N* wrote, and a fresh table each time is
    the one shape in which the bug cannot appear.
    """

    def __init__(self) -> None:
        self.rows: list[Alert] = []
        self.resolved: set[int] = set()

    def insert(self, alert: Alert) -> None:
        self.rows.append(alert)

    def open(self) -> list[Alert]:
        return [
            row for i, row in enumerate(self.rows) if i not in self.resolved
        ]

    def open_titles(self) -> list[str]:
        return [row.title for row in self.open()]

    def sweep(self, statement) -> int:
        """Apply ``_resolve_recovered``'s UPDATE as it is written."""
        sql = str(
            statement.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        match = re.search(r"alerts\.title NOT IN \((.*?)\)", sql)
        excluded = (
            {part.strip().strip("'") for part in match.group(1).split(",")}
            if match
            else set()
        )
        hit = 0
        for i, row in enumerate(self.rows):
            if i in self.resolved or row.title in excluded:
                continue
            if any(_like(p, row.title) for p in RESOLVABLE_TITLE_PATTERNS):
                self.resolved.add(i)
                hit += 1
        return hit


class FakeSession:
    """Enough of ``AsyncSession`` to drive ``_execute`` against ``FakeAlerts``."""

    def __init__(self, alerts: FakeAlerts) -> None:
        self.alerts = alerts
        self.other_rows: list = []

    def add(self, obj) -> None:
        if isinstance(obj, Alert):
            self.alerts.insert(obj)
        else:
            self.other_rows.append(obj)

    async def flush(self) -> None:
        return None

    async def execute(self, statement):
        if isinstance(statement, Update):
            return MagicMock(rowcount=self.alerts.sweep(statement))
        answer = self._answer(statement)
        result = MagicMock()
        result.scalars.return_value.all.return_value = answer
        # ``.first()`` as the database means it, not as a MagicMock
        # invents it: ``_refresh_open`` reads one row this way, and a
        # mock answering with a mock would let ``refresh_alert`` compare
        # a string against an attribute that is never equal to anything
        # and rewrite a row on every held poll (SNAG-AGENT-009).
        result.scalars.return_value.first.return_value = answer[0] if answer else None
        return result

    def _answer(self, statement):
        """What the database would hand back for *this* statement.

        The stand-in used to return whole rows for every SELECT, which
        was true of ``_execute`` until ``SNAG-AGENT-007``: the dedup
        snapshot now asks for ``select(Alert.title)`` and a fake that
        cannot tell a projection from a row read answers it with ``Alert``
        objects.  Dedup then compares titles against rows, matches
        nothing, and every fault opens a second row — the exact defect
        these tests exist to catch, reported as a fix breaking them.

        Discriminated on ``selected_columns`` rather than on the caller,
        so the fake models the database instead of the one call site that
        happens to project today.

        **The WHERE clause is honoured too, and it had to start being**
        (SNAG-AGENT-009): ``_refresh_open`` asks for one row by title, and
        a fake that answers every row read with *every* open row hands it
        the wrong alert and reports a refresh that never happened.  Read
        off the compiled statement, the idiom ``FakeAlerts.sweep`` already
        uses for the ``NOT IN`` list, and with the same limit — it proves
        the statement says what it means to say, not that PostgreSQL
        evaluates it that way.
        """
        if [c.name for c in statement.selected_columns] == ["title"]:
            return self.alerts.open_titles()
        rows = self.alerts.open()
        wanted = _title_equals(statement)
        if wanted is not None:
            rows = [row for row in rows if row.title == wanted]
        return rows

    def begin_nested(self):
        return _Savepoint()


def _no_rows_session():
    """A session that answers every read with nothing.

    Enough for the tests that drive ``_handle_status`` alone with
    ``_open_titles`` set by hand: there is no row behind those titles, so
    the refresh ``SNAG-AGENT-009`` added finds nothing and does nothing.
    That is the production path for a row resolved between the snapshot
    and the judgement, exercised here for free — and it is a real
    ``AsyncMock`` rather than a bare ``MagicMock`` because a mock that
    cannot be awaited hides the read behind a ``TypeError`` instead of
    modelling it.
    """
    session = MagicMock()
    session.flush = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    return session


class _Savepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _snapshot(disk_percent: float) -> ResourceSnapshot:
    return ResourceSnapshot(
        cpu_percent=5.0,
        ram_used_mb=1000,
        ram_total_mb=32000,
        ram_percent=10.0,
        swap_used_mb=0,
        swap_total_mb=8000,
        disk_usage={"/": {"percent": disk_percent}},
        gpu_usage={},
        load_avg_1m=0.5,
        load_avg_5m=0.5,
        load_avg_15m=0.5,
    )


async def _run(agent, session, mock_config, *, status: str, disk_percent: float):
    """One whole ``_execute``, with the service loop, the thresholds and
    the resolve left real and everything else stubbed.

    **The estate is asked and answers :data:`_NO_ARBITRATION`, which is
    the reading every assertion below holds under** (``SNAG-TEST-008``).
    ``_execute`` consults the arbiter for any service it measures
    ``critical`` or ``unreachable``, so leaving that read real made seven
    tests in this file dial ``:8400`` through the borrowed client —
    measured at **44 connections across 8 tests**, not the 16 the entry
    reported, which counted distinct addresses per nodeid rather than
    every connect.

    **Stubbed at the transport, never at the method.** Patching
    ``_ensure_arbitration`` out leaves ``_arbitration`` at ``None`` and
    reaches the same reading through the ``or _NO_ARBITRATION`` fallback
    — the right answer spelled as an *absence*, which is
    ``ports_checked``'s rule at the size of a stub: ``None`` and
    ``unread`` are both empty and only one of them says which. Stubbing
    :func:`~sysadmin.estate.client.read_arbitrated_stops` instead leaves
    the memo gate, the ``estate_judge.base_url`` leaf and
    ``self._http.borrow()`` real, so the only forged thing is the hop
    that would have left the box.

    **``unread`` rather than ``idle`` or a lease, and the choice is not
    about strength.** Driven three ways with the producer's own
    ``ArbitratedStops`` — unread, a lease holding nothing, and a lease
    naming every unit spelling in sight, with
    ``ServiceEntry.systemd_unit`` forced non-``None`` so the rung is
    genuinely reached — **19 of 19 pass in all six cells**, and a witness
    over ``_raise_judged`` confirms the granted cell moved **21**
    judgements from ``critical`` to ``info`` carrying
    ``stopped_by_estate: True``. So no reading discriminates, even one
    that changes production behaviour twenty-one times, and the
    "strongest reading" framing has nothing to choose between. What is
    left is which reading is *true of the run being driven*: nothing here
    asks an estate, and :data:`_NO_ARBITRATION`'s own docstring says
    "nobody asked" must never be spent as "the estate holds nothing".

    The constant is imported rather than rebuilt, so this file cannot
    declare a reading production would never start at —
    ``max_priority_for`` against ``PRIORITY_MAP``'s rule.
    """
    registry = MagicMock()
    registry.services = [
        ServiceEntry(name=TIMER, kind="http", url="http://localhost/health")
    ]

    scoped = MagicMock()
    scoped.return_value.__aenter__ = AsyncMock(return_value=None)
    scoped.return_value.__aexit__ = AsyncMock(return_value=False)

    async def check(_svc):
        return status, 12, {}

    with ExitStack() as stack:
        for p in (
            patch("sysadmin.monitor.agent.get_config", return_value=mock_config),
            patch("sysadmin.monitor.agent.get_services", return_value=registry),
            patch.object(agent, "_check_service", side_effect=check),
            patch.object(agent._http, "scoped", scoped),
            patch.object(
                agent, "_take_resource_snapshot", new_callable=AsyncMock,
                return_value=_snapshot(disk_percent),
            ),
            patch.object(
                agent, "_load_metric_history", new_callable=AsyncMock,
                return_value={},
            ),
            patch.object(agent, "_check_anomalies", new_callable=AsyncMock,
                         return_value=0),
            patch.object(agent, "_check_agent_health", new_callable=AsyncMock,
                         return_value=0),
            patch.object(agent, "_check_collation", new_callable=AsyncMock,
                         return_value=0),
            patch.object(
                estate_client, "read_arbitrated_stops",
                new_callable=AsyncMock, return_value=_NO_ARBITRATION,
            ),
        ):
            stack.enter_context(p)
        return await agent._execute(session)


@pytest.fixture
def agent():
    a = SysAdminAgent()
    # `run()` sets this before calling `_execute`; driving `_execute`
    # directly skips it, and `None` means "publish immediately" rather
    # than "no events".
    a._pending_events = []
    return a


@pytest.fixture
def alerts():
    return FakeAlerts()


@pytest.fixture
def session(alerts):
    return FakeSession(alerts)


# ---------------------------------------------------------------------------
# The premise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestTheReadingTheseAssertionsHoldUnder:
    """``SNAG-TEST-008`` — stated as an assertion, not as a comment.

    ``_run``'s docstring says which reading the file is driven at; this
    is what makes the sentence checkable. The witness is **identity**,
    not the reading string: an unstubbed
    :func:`~sysadmin.estate.client.read_arbitrated_stops` builds a fresh
    ``ArbitratedStops`` on every call, so ``is _NO_ARBITRATION`` fails
    whether ``:8400`` is up, down or dropping packets — where
    ``reading == ARBITRATION_UNREAD`` would pass on a box where the
    estate merely refuses the connection, going green while dialling.
    A witness has to be one the code under test cannot produce.
    """

    async def test_a_run_that_asks_gets_the_declared_reading(
        self, agent, session, mock_config
    ):
        await _run(agent, session, mock_config, status="critical", disk_percent=95)

        assert agent._arbitration is _NO_ARBITRATION

    async def test_a_run_with_nothing_down_never_asks_at_all(
        self, agent, session, mock_config
    ):
        """``None`` is not this file's declared reading, it is the state
        before anything has one.

        The consultation is gated on a service measuring ``critical`` or
        ``unreachable``, so a healthy run leaves the memo untouched and
        the rung falls through ``or _NO_ARBITRATION`` at the raise. Both
        roads reach ``unread`` and only one of them asked — the
        distinction the constant exists to keep, and the reason the
        assertion above is worth making at all.
        """
        await _run(agent, session, mock_config, status="ok", disk_percent=10)

        assert agent._arbitration is None


# ---------------------------------------------------------------------------
# The four runs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestOneFaultOneRow:
    async def test_run_one_raises(self, agent, session, alerts, mock_config):
        result = await _run(
            agent, session, mock_config, status="critical", disk_percent=95
        )

        assert sorted(alerts.open_titles()) == sorted([TIMER_ALERT, DISK_ALERT])
        assert result.alerts_raised == 2
        assert result.details["standing"] == {"judged": 2, "suppressed": 0, "refreshed": 0}

    async def test_run_two_raises_nothing_and_resolves_nothing(
        self, agent, session, alerts, mock_config
    ):
        """The one that matters.

        Raising nothing is half the answer; a sweep keyed on raises
        would also close both rows here, and run three would open them
        again.  Sixty rows are a legibility defect — a row that resolves
        and reopens every five minutes is a tray that notifies every
        five minutes, which is worse than the bug being fixed.
        """
        await _run(agent, session, mock_config, status="critical", disk_percent=95)
        result = await _run(
            agent, session, mock_config, status="critical", disk_percent=95
        )

        assert len(alerts.rows) == 2, "a second row was written for one fault"
        assert alerts.resolved == set(), "a still-true row was swept"
        assert result.alerts_raised == 0
        assert result.details["alerts_resolved"] == 0

    async def test_run_two_says_which_zero_it_means(
        self, agent, session, mock_config
    ):
        """Zero raised is the right answer to "nothing is wrong" and to
        "everything is wrong and already on the board"; a broken dedup
        produces the first while the second is true."""
        await _run(agent, session, mock_config, status="critical", disk_percent=95)
        result = await _run(
            agent, session, mock_config, status="critical", disk_percent=95
        )

        assert result.alerts_raised == 0
        # Nothing moved between the two runs — same status, same 95% — so
        # the gate holds and neither standing row is rewritten
        # (SNAG-AGENT-009).
        assert result.details["standing"] == {
            "judged": 2,
            "suppressed": 2,
            "refreshed": 0,
        }

    async def test_a_held_row_whose_figure_moved_is_rewritten(
        self, agent, session, alerts, mock_config
    ):
        """``SNAG-AGENT-009`` — the row stands, the sentence moves.

        This is the family the entry never named and the largest of the
        five: **838** suppressed raises across 751 of 2,303 runs.  The
        threshold half is the worst case by construction, because the
        title is stable while the whole message is the measurement — so
        ``Critical disk usage on /`` raised at 95% went on saying 95% for
        as long as the disk stayed over the line.  Across the live
        ``High VRAM usage`` rows every one of the 42 measurable held
        polls carried a different figure, and 19 read *below* the
        threshold the frozen sentence was asserting.
        """
        await _run(agent, session, mock_config, status="critical", disk_percent=95)
        row = next(r for r in alerts.open() if r.title == DISK_ALERT)
        assert "95" in row.message

        result = await _run(
            agent, session, mock_config, status="critical", disk_percent=99
        )

        assert len(alerts.rows) == 2, "a moved figure must not open a second row"
        assert result.alerts_raised == 0
        assert result.details["standing"]["refreshed"] == 1
        assert "99" in row.message and "95" not in row.message
        # Both halves, or the evidence disagrees with the sentence above
        # it — which is what the drive found on the ports family.
        assert row.details["percent"] == 99

    async def test_a_row_written_by_this_same_run_is_not_rewritten(
        self, agent, session, alerts, mock_config
    ):
        """The reason ``_written_titles`` is a second set.

        A title judged twice inside one run — two identically-named GPUs
        is the case that put the bookkeeping there — dedups against the
        row the first judgement just inserted.  Which of the two is
        *current* is undefined, so the run must not answer it twice: the
        first sentence stands and the second is merely suppressed.
        Driven through the disk loop, where two mounts can be made to
        produce one title.
        """
        agent._open_titles = set()
        agent._written_titles = set()
        agent._judged_titles = set()
        agent._suppressed = agent._refreshed = 0

        for percent in (95, 99):
            await agent._raise_judged(
                session,
                severity="critical",
                title=DISK_ALERT,
                message=f"Disk at {percent}%",
                details={"percent": percent},
            )

        assert len(alerts.rows) == 1
        assert alerts.rows[0].message == "Disk at 95%"
        assert agent._suppressed == 1 and agent._refreshed == 0

    async def test_ten_runs_of_one_fault_are_still_one_row_each(
        self, agent, session, alerts, mock_config
    ):
        """Five minutes apart, ten runs is fifty minutes.  The live table
        held sixty rows for five hours of exactly this."""
        for _ in range(10):
            await _run(
                agent, session, mock_config, status="critical", disk_percent=95
            )

        assert len(alerts.rows) == 2
        assert sorted(alerts.open_titles()) == sorted([TIMER_ALERT, DISK_ALERT])

    async def test_run_three_resolves_when_the_fault_clears(
        self, agent, session, alerts, mock_config
    ):
        await _run(agent, session, mock_config, status="critical", disk_percent=95)
        await _run(agent, session, mock_config, status="critical", disk_percent=95)

        result = await _run(
            agent, session, mock_config, status="ok", disk_percent=10
        )

        assert alerts.open_titles() == []
        assert result.details["alerts_resolved"] == 2
        assert result.details["standing"] == {"judged": 0, "suppressed": 0, "refreshed": 0}

    async def test_run_four_raises_again_when_the_fault_returns(
        self, agent, session, alerts, mock_config
    ):
        """Dedup must not outlive the row it deduplicated against.

        The open-row snapshot is taken per run, so a resolved row stops
        suppressing — otherwise a fault that recurs after a recovery is
        silent for ever, which is the failure mode of every in-memory
        "already told you" cache."""
        await _run(agent, session, mock_config, status="critical", disk_percent=95)
        await _run(agent, session, mock_config, status="ok", disk_percent=10)

        result = await _run(
            agent, session, mock_config, status="critical", disk_percent=95
        )

        assert sorted(alerts.open_titles()) == sorted([TIMER_ALERT, DISK_ALERT])
        assert result.alerts_raised == 2
        assert len(alerts.rows) == 4


# ---------------------------------------------------------------------------
# The carve-out
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAutoRestartIsAnEventNotAState:
    """``% auto-restarted`` is the one title in these families that must
    not deduplicate.

    ``_failure_counts`` is reset to zero the moment ``restart_unit``
    returns, so the title fires once per restart *cycle*.  A second
    restart three hours later is a second piece of news; suppressing it
    because the first row is still open loses the only record that the
    service went down twice.  Same distinction ``log_signature.py``
    draws between a log line and an incident.
    """

    @pytest.fixture
    def svc(self):
        return ServiceEntry(
            name="svc", kind="systemd",
            systemd={"unit": "svc.service", "scope": "system"},
            auto_restart=True, auto_restart_after_checks=1,
        )

    async def test_a_second_restart_writes_a_second_row(self, agent, svc):
        session = _no_rows_session()
        agent._open_titles = {"svc auto-restarted"}

        with patch(
            "sysadmin.monitor.agent.restart_unit",
            new_callable=AsyncMock, return_value=(True, "restarted"),
        ) as restart:
            written = await agent._handle_status(session, svc, "critical", {})

        assert written == 1, "the row saying it was restarted again was suppressed"
        assert agent._suppressed == 0
        restart.assert_awaited_once()

    async def test_the_service_criticals_beside_it_still_deduplicate(
        self, agent
    ):
        """The carve-out is one title, not the family."""
        svc = ServiceEntry(name="svc", kind="http", url="http://localhost/h")
        session = _no_rows_session()
        agent._open_titles = {"svc critical"}

        written = await agent._handle_status(session, svc, "critical", {})

        assert written == 0
        assert agent._suppressed == 1

    async def test_the_restart_still_happens_when_a_raise_is_suppressed(
        self, agent
    ):
        """Suppressing the raise must never suppress the check.

        The streak counter and ``restart_unit`` sit above
        ``_raise_judged`` for this reason: a restart that did not happen
        because the alert was old is a service left down.
        """
        svc = ServiceEntry(
            name="svc", kind="systemd",
            systemd={"unit": "svc.service", "scope": "system"},
            auto_restart=True, auto_restart_after_checks=2,
        )
        session = _no_rows_session()
        agent._open_titles = {"svc critical", "svc auto-restarted"}

        with patch(
            "sysadmin.monitor.agent.restart_unit",
            new_callable=AsyncMock, return_value=(True, "restarted"),
        ) as restart:
            # First check: below the restart threshold, and its critical
            # row is already open — the suppressed case.
            await agent._handle_status(session, svc, "critical", {})
            assert agent._failure_counts["svc"] == 1
            restart.assert_not_awaited()

            await agent._handle_status(session, svc, "critical", {})

        restart.assert_awaited_once_with("svc.service", user=False)
        assert agent._failure_counts["svc"] == 0
