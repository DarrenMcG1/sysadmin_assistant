"""The GPU-context predicate, its declaration, and its ways of not-knowing.

ADR-0007 and ``SNAG-GPU-001``.  The live half — the real journal, the
real ``systemctl``, the real table — is
``tests/test_gpu_context_live.py``; what is here is the rules, which a
stand-in can hold.

Every test below was falsified against the behaviour it replaces; the
mutations are named in the docstrings where the mutation is not simply
"delete the clause".
"""

import ast
import inspect
import textwrap
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from sysadmin.monitor import gpu_context
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.log_aggregator import CRITICAL_SIGNATURES
from sysadmin.monitor.models.service_health import STATUS_READINGS, is_fault
from sysadmin.monitor.services import ServiceEntry, check_plan
from sysadmin.monitor.systemd import (
    START_INSTANT_PROP,
    START_INSTANT_TIMESTAMP_FLAG,
    SystemdQueryError,
    get_unit_status,
    parse_start_instant,
)

#: A real spelling this box has stored, not a paraphrase.  The other
#: declared spelling is the LTS kernel's, which repeats the device name.
RESET_LINE = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"

RESET_AT = datetime(2026, 9, 6, 19, 43, 1, 696229, tzinfo=UTC)

_UNIT_STATUS = "sysadmin.monitor.agent.get_unit_status"


def declaring(**overrides) -> ServiceEntry:
    """A service that declares ``holds_vram``, shaped like the live two."""
    return ServiceEntry.model_validate({
        "name": "llama-server",
        "kind": "http",
        "url": "http://localhost:8081/health",
        "port": 8081,
        "holds_vram": True,
        "systemd": {"unit": "alfred-inference.service", "scope": "user"},
    } | overrides)


def silent(**overrides) -> ServiceEntry:
    """``venture-embed``: the same role, and no declaration."""
    return ServiceEntry.model_validate({
        "name": "venture-embed",
        "kind": "http",
        "role": "inference",
        "url": "http://localhost:8082/health",
        "port": 8082,
        "systemd": {"unit": "venture-embed.service", "scope": "user"},
    } | overrides)


def active_unit(started: str | None = "@1788723780", **overrides) -> dict:
    """A live unit's properties as ``get_unit_status`` returns them."""
    props = {
        "is_active": True,
        "ActiveState": "active",
        "SubState": "running",
        "Result": "success",
    } | overrides
    if started is not None:
        props[START_INSTANT_PROP] = started
    return props


class _Savepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeSession:
    """A session stand-in that can be *used* the way production uses it.

    ``object()`` was enough until the read moved inside
    ``session.begin_nested()`` — the savepoint that stops a failed read
    aborting the run's whole transaction.  A stand-in that cannot answer
    the call under test does not model the code under test, which is the
    shape this repository keeps finding: four stand-ins in Session 110
    modelled a database the code no longer talked to.
    """

    def __init__(self):
        self.savepoints = 0

    def begin_nested(self):
        self.savepoints += 1
        return _Savepoint()


def rows(*messages: str, at: datetime = RESET_AT, source: str = "kernel"):
    """``(source, message, logged_at)`` triples, as the adapter yields."""
    return [(source, message, at) for message in messages]


class TestThePopulationIsADeclaration:
    """gpu_context rule 1 — and the measurement that refused the role."""

    def test_a_declaring_service_asks_systemd_for_the_instant(self):
        assert declaring().holds_vram is True

    def test_the_role_it_shares_declares_nothing(self):
        """``venture-embed`` is the whole reason the key is not the role.

        It carries ``role: inference`` and served 267 of 823 successful
        embeddings while the predicate was true.  Falsified by keying the
        production check on ``svc.role == "inference"``, which turns this
        red and nothing else.
        """
        assert silent().role == "inference"
        assert silent().holds_vram is False

    @pytest.mark.asyncio
    async def test_an_undeclared_service_is_never_asked_for_an_instant(self):
        svc = silent()
        seen: dict = {}

        async def show(unit, user=False, *, start_instant=False):
            seen["start_instant"] = start_instant
            return active_unit(started=None)

        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, show),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert seen["start_instant"] is False
        assert status == "ok"
        assert gpu_context.DETAIL_KEY not in details

    def test_a_declaration_that_could_never_be_evaluated_is_refused(self):
        """The validator, and both halves of the conjunction.

        A declaration on a kind no check path evaluates parses cleanly
        and is silently never read — ``SNAG-CFG-001``'s shape.  Both
        limbs are driven, because a validator testing one of them admits
        the other.
        """
        with pytest.raises(ValidationError, match="holds_vram requires kind http"):
            declaring(kind="systemd", url=None)
        with pytest.raises(ValidationError, match="holds_vram requires kind http"):
            ServiceEntry.model_validate({
                "name": "probe",
                "kind": "http",
                "url": "http://localhost:9/health",
                "holds_vram": True,
            })

    def test_the_shipped_file_declares_exactly_the_measured_two(self):
        """The declaration is a fact about this box, so it is read here.

        Not a restatement: the point of the entry is *which* services
        hold VRAM, and a test over a fixture could not notice a third
        being added without a measurement behind it.
        """
        from sysadmin.monitor.services import load_services

        entries = load_services(
            Path(__file__).resolve().parents[1] / "services.yaml"
        ).services
        declared = sorted(s.name for s in entries if s.holds_vram)
        inference = sorted(s.name for s in entries if s.role == "inference")
        assert declared == ["llama-server", "venture-chat"]
        assert set(declared) < set(inference), (
            "the role is a strict superset, which is why it is not the key"
        )


class TestTheComparisonIsStrict:
    """gpu_context rule 2."""

    def test_a_reset_after_the_start_is_a_lost_context(self):
        started = RESET_AT - timedelta(seconds=1)
        sighting = gpu_context.newest_declared_reset(rows(RESET_LINE), after=started)
        assert sighting is not None
        assert sighting.at == RESET_AT

    def test_a_reset_before_the_start_is_not(self):
        started = RESET_AT + timedelta(seconds=1)
        assert gpu_context.newest_declared_reset(rows(RESET_LINE), after=started) is None

    def test_an_exact_tie_is_not_flagged(self):
        """Falsified by relaxing ``<=`` to ``<`` in the adapter's filter.

        Its population is empty on real data — ``logged_at`` carries
        microseconds — so this is the only place the rule is observable,
        and the module docstring says so rather than leaving the
        emptiness to be discovered.
        """
        assert gpu_context.newest_declared_reset(
            rows(RESET_LINE, at=RESET_AT), after=RESET_AT
        ) is None

    def test_the_newest_of_several_is_the_one_reported(self):
        older = RESET_AT - timedelta(hours=3)
        candidates = [
            ("kernel", RESET_LINE, older),
            ("kernel", "amdgpu 0000:03:00.0: amdgpu: VRAM is lost due to GPU reset!", RESET_AT),
        ]
        sighting = gpu_context.newest_declared_reset(
            candidates, after=older - timedelta(seconds=1)
        )
        assert sighting is not None and sighting.at == RESET_AT


class TestTheIdentityIsTheDeclaredSignature:
    """gpu_context rule 3 — Python signs, and the keys are derived."""

    def test_the_keys_come_from_the_alert_family(self):
        assert gpu_context.declared_reset_keys() == frozenset(CRITICAL_SIGNATURES)

    def test_the_sources_are_derived_and_stable(self):
        assert gpu_context.declared_reset_sources() == ("kernel",)
        assert gpu_context.declared_reset_sources() == tuple(
            sorted(gpu_context.declared_reset_sources())
        )

    def test_a_line_that_is_not_a_declared_reset_is_ignored(self):
        """A neighbouring kernel fault in the same window says nothing."""
        assert gpu_context.newest_declared_reset(
            rows("amdgpu 0000:03:00.0: ring gfx_0.0.0 timeout"),
            after=RESET_AT - timedelta(days=1),
        ) is None

    def test_the_same_payload_from_another_source_is_ignored(self):
        """The key is ``(source, signature)``, never the signature alone.

        Falsified by matching on the signature only, which this turns
        red and no other test here does.
        """
        assert gpu_context.newest_declared_reset(
            rows(RESET_LINE, source="sysadmin.service"),
            after=RESET_AT - timedelta(days=1),
        ) is None

    def test_the_digits_are_normalised_before_matching(self):
        """A different BDF is the same fault, which is what ``N`` buys."""
        sighting = gpu_context.newest_declared_reset(
            rows("amdgpu 0000:07:00.0: VRAM is lost due to GPU reset!"),
            after=RESET_AT - timedelta(days=1),
        )
        assert sighting is not None
        assert "N:N:N.N" in sighting.signature


class TestTheNarrowingClausesArePinnedByCompiling:
    """Two clauses no behavioural test can reach, and why they are here.

    Both are cost, not meaning: the floor is exact and the grouping is a
    projection, so deleting either leaves every answer identical.  Driven
    as the tenth of ten mutations, dropping the floor left all thirty-one
    tests **green** — a guard that cannot fail is not a guard, so the
    statement is compiled and read.
    """

    def _sql(self) -> str:
        from sqlalchemy.dialects import postgresql

        statement = gpu_context.candidate_statement(RESET_AT)
        return str(statement.compile(dialect=postgresql.dialect()))

    def test_the_floor_is_in_the_statement(self):
        """Without it this is a sequential scan of the whole table.

        Measured 2026-09-08: 69,810 buffers of which 64,007 are reads —
        half a gigabyte — against 6,855 all-hit buffers floored, every
        300 seconds.
        """
        assert "log_entries.logged_at >=" in self._sql()

    def test_the_read_is_grouped(self):
        """Grouping is what bounds the answer, and a count never could.

        49,527 rows sit newer than the newest stored reset; the same span
        holds 173 distinct messages.
        """
        sql = self._sql()
        assert "GROUP BY" in sql
        assert "max(sysadmin.log_entries.logged_at)" in sql

    def test_the_source_is_narrowed_to_the_declared_ones(self):
        assert "log_entries.source IN" in self._sql()

    def test_the_statement_is_what_the_adapter_executes(self):
        """Or the pin is on a statement nothing runs.

        The lift is only honest if `reset_since` has no second copy of
        the query, so this asserts it builds none of its own.
        """
        source = textwrap.dedent(inspect.getsource(gpu_context.reset_since))
        tree = ast.parse(source)
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "candidate_statement" in called
        assert "select" not in called


class TestEveryWayOfNotKnowingIsARecordedReading:
    """gpu_context rule 5 — and none of them is ``False``."""

    def test_an_inactive_unit_publishes_no_instant(self):
        assert parse_start_instant("") is None
        assert parse_start_instant(None) is None

    def test_a_wall_clock_rendering_is_refused(self):
        """The flag did not travel with the property, so nothing is read.

        Accepting it would mean parsing a local wall clock with a zone
        abbreviation — the reading ``SNAG-LOG-009`` removed.
        """
        assert parse_start_instant("Mon 2026-09-07 05:00:15 BST") is None

    def test_an_epoch_is_read_as_utc(self):
        assert parse_start_instant("@1788753615") == datetime(
            2026, 9, 7, 4, 0, 15, tzinfo=UTC
        )

    @pytest.mark.asyncio
    async def test_an_unreadable_instant_leaves_the_status_alone_and_says_so(self):
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(return_value=active_unit(started=""))),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert status == "ok"
        assert details[gpu_context.DETAIL_KEY]["evaluated"] is False
        assert "ActiveEnterTimestamp" in details[gpu_context.DETAIL_KEY]["reason"]

    @pytest.mark.asyncio
    async def test_a_missing_session_is_a_reading_rather_than_a_verdict(self):
        """The polarity trap, named rather than left to be discovered.

        ``_check_service``'s ``session`` defaults to ``None`` so the
        twenty existing call sites are unaffected; a *declaring* service
        reached without one must therefore say it was not evaluated, or
        the default would be a quiet ``False``.
        """
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(return_value=active_unit())),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), None
            )
        assert status == "ok"
        assert details[gpu_context.DETAIL_KEY] == {
            "unit": "alfred-inference.service",
            "evaluated": False,
            "reason": "no database session was supplied to the check",
        }

    @pytest.mark.asyncio
    async def test_a_systemd_failure_keeps_both_readings(self):
        """The unit assertion fails open and the term records its silence.

        Two facts, two keys: ``unit_check`` was already carried and the
        GPU term is a second thing that did not happen.
        """
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(side_effect=SystemdQueryError("no bus"))),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert status == "ok"
        assert details["unit_check"] == "unavailable"
        assert details[gpu_context.DETAIL_KEY]["evaluated"] is False

    def test_the_key_is_present_on_every_reading_and_the_value_carries_the_news(self):
        """Session 128's rule: uniform key, differing value.

        A key present only sometimes makes absent and present the only
        signal, which is the collapse ``ports_checked`` names.
        """
        unreadable = gpu_context.unreadable_reading("u.service", "why")
        clean = gpu_context.verdict_reading("u.service", RESET_AT, None)
        lost = gpu_context.verdict_reading(
            "u.service", RESET_AT, gpu_context.ResetSighting(RESET_AT, "sig")
        )
        for reading in (unreadable, clean, lost):
            assert set(reading) == {gpu_context.DETAIL_KEY}
            assert "evaluated" in reading[gpu_context.DETAIL_KEY]


class TestTheReadingIsAFaultAndItDeducts:
    """ADR-0007 §3 — ``skipped`` was refused and this is why."""

    def test_the_recorded_status_classifies_as_a_fault(self):
        assert is_fault(gpu_context.POISONED_STATUS)
        assert STATUS_READINGS[gpu_context.POISONED_STATUS] == "fault"

    def test_it_is_not_an_unwatched_reading(self):
        """Falsified by setting ``POISONED_STATUS = "skipped"``.

        That value would drop the row from the reliability rates
        entirely, so 79.9 measured hours of a server that could not serve
        would cost it nothing — ``SNAG-SVC-001`` run in reverse.
        """
        from sysadmin.monitor.reliability import UNMEASURED_STATUSES

        assert STATUS_READINGS[gpu_context.POISONED_STATUS] != "unwatched"
        assert gpu_context.POISONED_STATUS not in UNMEASURED_STATUSES

    @pytest.mark.asyncio
    async def test_a_lost_context_is_recorded_with_its_whole_derivation(self):
        svc = declaring()
        agent = SysAdminAgent()
        sighting = gpu_context.ResetSighting(RESET_AT, "amdgpu N:N:N.N: VRAM is lost…")
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(return_value=active_unit())),
            patch.object(
                gpu_context, "reset_since", AsyncMock(return_value=sighting)
            ),
        ):
            session = FakeSession()
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), session
            )
        assert status == gpu_context.POISONED_STATUS
        assert session.savepoints == 1, (
            "the read ran outside a savepoint, so a failed statement would "
            "abort the run's transaction and cost every later service its row"
        )
        blob = details[gpu_context.DETAIL_KEY]
        assert blob["context_lost"] is True
        assert blob["unit_started_at"] == "2026-09-06T19:43:00+00:00"
        assert blob["reset_at"] == RESET_AT.isoformat()
        assert blob["reset_signature"] == sighting.signature
        assert "VRAM" in details["reason"]

    @pytest.mark.asyncio
    async def test_a_clean_context_leaves_ok_and_still_records_the_reading(self):
        """"Checked, and it was not this" is not the same fact as silence."""
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(return_value=active_unit())),
            patch.object(gpu_context, "reset_since", AsyncMock(return_value=None)),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert status == "ok"
        assert details[gpu_context.DETAIL_KEY]["context_lost"] is False
        assert "reason" not in details


class TestTheTermRunsOnlyWhereItCanMeanSomething:
    @pytest.mark.asyncio
    async def test_a_url_that_did_not_answer_is_not_asked_about_its_context(self):
        """The URL's own verdict already names a fault; this adds none."""
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(
                agent, "_check_http", AsyncMock(return_value=("unreachable", None, {"error": "x"}))
            ),
            patch(_UNIT_STATUS, AsyncMock(return_value=active_unit())) as show,
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert status == "unreachable"
        assert gpu_context.DETAIL_KEY not in details
        show.assert_not_called()

    @pytest.mark.asyncio
    async def test_an_inactive_unit_keeps_its_own_fault(self):
        """An inactive unit has no context to have lost.

        Falsified by moving the term above the ``is_active`` branch,
        which makes this row report a GPU verdict about a dead process.
        """
        svc = declaring()
        agent = SysAdminAgent()
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(
                _UNIT_STATUS,
                AsyncMock(return_value={"is_active": False, "ActiveState": "failed"}),
            ),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), FakeSession()
            )
        assert status == "degraded"
        assert "is not active" in details["reason"]
        assert gpu_context.DETAIL_KEY not in details


class TestThePropertyAndTheFlagTravelTogether:
    """systemd.get_unit_status' gate — and the ten timers it protects."""

    @pytest.mark.asyncio
    async def test_asking_for_the_instant_adds_both(self):
        with patch(
            "sysadmin.monitor.systemd._run",
            AsyncMock(return_value=(0, "ActiveState=active\n", "")),
        ) as run:
            await get_unit_status("u.service", user=True, start_instant=True)
        args = run.await_args.args[0]
        assert START_INSTANT_TIMESTAMP_FLAG in args
        assert START_INSTANT_PROP in args[-1]

    @pytest.mark.asyncio
    async def test_not_asking_adds_neither(self):
        """The whole point of the gate.

        ``--timestamp=`` is a command flag, so it also re-renders
        ``LastTriggerUSec`` — which ``_observed_fires`` reads as a firing
        whenever the token changes.  Falsified by making the flag
        unconditional, which turns this red and nothing else in the
        suite, because no other test compares two renderings of a token
        every consumer treats as opaque.
        """
        with patch(
            "sysadmin.monitor.systemd._run",
            AsyncMock(return_value=(0, "ActiveState=active\n", "")),
        ) as run:
            await get_unit_status("u.timer", user=True)
        args = run.await_args.args[0]
        assert START_INSTANT_TIMESTAMP_FLAG not in args
        assert START_INSTANT_PROP not in args[-1]

    @pytest.mark.asyncio
    async def test_the_timer_properties_are_still_requested_either_way(self):
        """The gate widens the property list; it must not replace it."""
        for asked in (False, True):
            with patch(
                "sysadmin.monitor.systemd._run",
                AsyncMock(return_value=(0, "ActiveState=active\n", "")),
            ) as run:
                await get_unit_status("u.timer", start_instant=asked)
            props = run.await_args.args[0][-1]
            for prop in ("LastTriggerUSec", "NextElapseUSecRealtime", "Unit"):
                assert prop in props, (asked, prop)


class TestTheProductionPathSuppliesASession:
    """The guard the optional parameter needs, or the default is a trap."""

    def test_execute_passes_its_own_session_to_the_check(self):
        """An AST walk, because the value is what matters and a drive of
        ``_execute`` would prove only that *something* was passed.

        Falsified by dropping the argument at the call site, which no
        behavioural test here can see: every one of them calls
        ``_check_http_and_unit`` directly.
        """
        source = textwrap.dedent(inspect.getsource(SysAdminAgent._execute))
        tree = ast.parse(source)
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "_check_service"
        ]
        assert len(calls) == 1, "the production call site moved or forked"
        assert [
            arg.id for arg in calls[0].args if isinstance(arg, ast.Name)
        ] == ["svc", "session"]
