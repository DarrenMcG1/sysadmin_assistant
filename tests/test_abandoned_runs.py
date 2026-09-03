"""SNAG-DB-006 — ``cancelled`` gets the path the measurement found for it.

``chk_run_status`` has admitted ``cancelled`` since migration 001 and
nothing had ever written one.  The entry named two *opposite* fixes —
drop the value, or find the path that fills it — and left the choice
open because nothing recorded which was intended.

The seven live ``running`` rows decided it.  Every one is followed by a
**clean** daemon death within 0.032–61.2 s, and for every one the next
``agent_run_completed`` for that agent comes from a different PID.
Against a base rate of **0.401 %** (162 of 40,383 ``completed`` runs
start that close to a death) the separation is total, and
``file_organiser`` — the widest exposure of any agent at ~108 s a scan —
is **0 of 112** completed against **3 of 3** stuck.  So the value has a
referent and the fix is to fill it.

**The shape is a third one the entry does not name**: a sweep at
*startup*, not a write at shutdown.  See
:mod:`sysadmin.core.abandoned_runs` rule 1 for why — briefly, a shutdown
write races the worker thread it describes, and a startup sweep cannot
race a process that is already gone.

**These run against the live database inside a rolled-back
transaction**, and that is not decoration.  Three of the properties
under test are ones a fake agrees with by construction: ``chk_run_status``
really rejects a fifth status, ``details`` really round-trips through
``JSONB`` (which is what the ``->>`` filter is written against), and
``jsonb_build_object`` concatenation really preserves the keys already
there.  A ``MagicMock`` session would answer correctly to all three
whatever the module did.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from sysadmin.core import abandoned_runs as module
from sysadmin.core.abandoned_runs import (
    CANCELLED_BY,
    CANCELLED_STATUS,
    INSTANCE_DETAIL_KEY,
    INSTANCE_ID,
    RUNNING_STATUS,
    close_abandoned_runs,
)
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.snag_claims import rolled_back_drive

#: The agent every fabricated row claims.
#:
#: A real member of ``chk_alert_agent``'s sibling vocabulary rather than a
#: made-up name: ``agent`` is ``String(50)`` with no constraint of its
#: own, so an invented value would pass and the rows would stop being
#: specimens of the shape the sweep meets.  ``project_organiser`` is the
#: retired one — its last real run was 2026-08-13 — so a stray row cannot
#: be mistaken for a live agent's while the drive is open.
PROBE_AGENT = "project_organiser"

#: A stand-in for the process that died.  Minted per call, never a
#: literal: a witness spelled as a constant is found by whatever asserts
#: it, and two tests sharing one would stop being independent.
def _dead_instance() -> str:
    return str(uuid.uuid4())


def _row(instance: str | None, *, status: str = RUNNING_STATUS) -> AgentRun:
    """One ``agent_runs`` row in the state the sweep meets it in.

    ``details`` is ``{}`` rather than ``None`` for an unstamped row,
    because that is what every release before this one wrote and what the
    seven live rows carry — the column is ``NOT NULL``.
    """
    return AgentRun(
        id=uuid.uuid4(),
        agent=PROBE_AGENT,
        run_type="scheduled",
        status=status,
        started_at=datetime.now(UTC),
        details={INSTANCE_DETAIL_KEY: instance} if instance else {},
    )


async def _reread(session, row: AgentRun):
    """Read the row's columns back, deliberately *not* as an ORM object.

    The assertion is then about what is **in the table** rather than
    about what this session believes, which is the stronger of the two
    claims and the reason these tests use the live database at all.

    Written first as ``expire_all()`` followed by
    ``session.scalar(select(AgentRun)...)``, which raised
    ``MissingGreenlet`` in six of these tests: expiring the just-added
    instance leaves the next statement's autoflush needing to load it,
    and that load is synchronous IO outside the greenlet.  Selecting
    columns needs neither the expire nor the identity map.
    """
    return (
        await session.execute(
            select(
                AgentRun.status, AgentRun.completed_at, AgentRun.details
            ).where(AgentRun.id == row.id)
        )
    ).one()


class TestTheSweepClosesWhatADeadProcessLeft:
    """The founding case: a ``running`` row stamped by somebody else."""

    def test_a_previous_instances_row_is_cancelled(self):
        async def work(session):
            row = _row(_dead_instance())
            session.add(row)
            await session.flush()
            result = await close_abandoned_runs(session, instance_id=INSTANCE_ID)
            after = await _reread(session, row)
            return result, after.status, after.completed_at, after.details

        (out, status, completed_at, details), problem = rolled_back_drive(work)
        assert not problem, problem
        # The **literal**, deliberately a second statement of the value.
        # ``status == CANCELLED_STATUS`` compares the module's constant to
        # itself and is true whatever that constant says: a mutation
        # setting it to ``"failed"`` passed every test in this file,
        # including the constraint pin, since ``failed`` is admitted too.
        assert status == "cancelled"
        assert status == CANCELLED_STATUS
        assert completed_at is not None
        assert out.closed >= 1
        assert PROBE_AGENT in out.agents
        # The provenance, not merely the status: `unit_failure`'s
        # `details['source']` rule — a row this sweep closed and one some
        # future on-request cancellation writes are different events.
        assert details["cancelled_by"] == CANCELLED_BY

    def test_the_dead_instances_own_stamp_survives_the_close(self):
        """Concatenation, not replacement.

        The row still says *which* process abandoned it, which is the
        only thing distinguishing one dead instance's residue from
        another's.  A ``.values(details={...})`` would have read the same
        in every other assertion here.
        """
        dead = _dead_instance()

        async def work(session):
            row = _row(dead)
            session.add(row)
            await session.flush()
            await close_abandoned_runs(session, instance_id=INSTANCE_ID)
            return (await _reread(session, row)).details

        details, problem = rolled_back_drive(work)
        assert not problem, problem
        assert details[INSTANCE_DETAIL_KEY] == dead

    def test_a_completed_row_is_never_touched(self):
        """The status filter, which the instance filter does not imply.

        A finished run's ``details`` is replaced whole by
        ``_record_outcome``, so it carries no stamp — but a run that
        failed *before* that replacement can, and closing it would
        overwrite a real outcome with a guess.
        """
        async def work(session):
            row = _row(_dead_instance(), status="completed")
            session.add(row)
            await session.flush()
            await close_abandoned_runs(session, instance_id=INSTANCE_ID)
            return (await _reread(session, row)).status

        status, problem = rolled_back_drive(work)
        assert not problem, problem
        assert status == "completed"


class TestTheSweepCannotReachThisProcess:
    """Rule 1's guarantee, asserted rather than relied on by placement."""

    def test_our_own_running_row_is_left_alone(self):
        async def work(session):
            row = _row(INSTANCE_ID)
            session.add(row)
            await session.flush()
            result = await close_abandoned_runs(session, instance_id=INSTANCE_ID)
            return result, (await _reread(session, row)).status

        (out, status), problem = rolled_back_drive(work)
        assert not problem, problem
        assert status == RUNNING_STATUS
        assert PROBE_AGENT not in out.agents


class TestAnUnstampedRowIsRefusedAndCounted:
    """Rule 3 — forward-only by construction, and observable.

    The seven live rows predate the stamp, so the sweep cannot tell a
    dead process's row from a live one's.  Refusing them is
    ``ports_checked``'s rule; **counting** them is what stops the
    refusal being indistinguishable from having found nothing.
    """

    def test_it_is_not_cancelled(self):
        async def work(session):
            row = _row(None)
            session.add(row)
            await session.flush()
            await close_abandoned_runs(session, instance_id=INSTANCE_ID)
            return (await _reread(session, row)).status

        status, problem = rolled_back_drive(work)
        assert not problem, problem
        assert status == RUNNING_STATUS

    def test_it_is_counted_apart_from_what_was_closed(self):
        async def work(session):
            session.add(_row(None))
            session.add(_row(_dead_instance()))
            await session.flush()
            return await close_abandoned_runs(session, instance_id=INSTANCE_ID)

        out, problem = rolled_back_drive(work)
        assert not problem, problem
        assert out.refused >= 1
        assert out.closed >= 1
        assert not out.found_nothing

    def test_refusing_something_is_not_finding_nothing(self):
        """``found_nothing`` is a third state, not ``closed == 0``.

        A boot after a clean shutdown and a boot that could not attribute
        anything are different facts, and the lifespan logs only the
        first.

        **The witness is minted, not borrowed.**  Written first as an
        assertion over whatever the live table happened to hold — which
        works today only because the seven unstamped rows are still
        there, and would go vacuous when they age out of the 30-day
        retention window on 2026-09-27.  A test whose discriminator
        expires is one that reports success for the wrong reason.
        """
        async def work(session):
            session.add(_row(None))
            await session.flush()
            return await close_abandoned_runs(session, instance_id=INSTANCE_ID)

        out, problem = rolled_back_drive(work)
        assert not problem, problem
        assert out.closed == 0
        assert out.refused >= 1
        assert not out.found_nothing


class TestTheRefusalIsWrittenDownRatherThanInherited:
    """The conjunct no behavioural test can see go.

    ``NULL <> 'x'`` is ``NULL`` in SQL, so ``abandoned_by``'s inequality
    already excludes an unstamped row and the ``IS NOT NULL`` beside it
    changes no result.  Measured: a mutation deleting that line passed
    **all sixteen** tests in this file, including the three that exist to
    assert rule 3.

    That is not a reason to delete it.  The clause is what a reader sees
    when they wonder about the NULL case, and the edit it prevents —
    ``COALESCE(details->>'instance', '')`` — would sweep the seven live
    rows this fix is deliberately forward-only about, silently.  A clause
    that earns its place by being *read* can only be pinned by reading
    the statement, so this compiles it.
    """

    def _sql(self, criteria) -> str:
        from sqlalchemy import select as _select
        from sqlalchemy.dialects import postgresql

        return str(
            _select(AgentRun.id)
            .where(*criteria)
            .compile(dialect=postgresql.dialect())
        )

    def test_the_sweep_states_the_not_null_case(self):
        assert "IS NOT NULL" in self._sql(module.abandoned_by("some-instance"))

    def test_the_refusal_count_states_the_null_case(self):
        assert "IS NULL" in self._sql(module.unattributable())

    def test_neither_coalesces_the_missing_stamp(self):
        """The dangerous edit, refused by name.

        A ``COALESCE`` here reads as defensive and is the one change that
        turns rule 3 off without failing anything else.
        """
        for criteria in (module.abandoned_by("x"), module.unattributable()):
            assert "coalesce" not in self._sql(criteria).lower()

    def test_both_are_scoped_to_running_rows(self):
        for criteria in (module.abandoned_by("x"), module.unattributable()):
            assert "status" in self._sql(criteria)


class TestTheStatusIsPinnedToTheConstraint:
    """Rule 5 — written once, pinned, never derived.

    Which of the four values ``chk_run_status`` admits means "abandoned"
    is not a fact the constraint carries; it lists the vocabulary and
    says nothing about meaning.  So the literal stands and this asserts
    the vocabulary still contains it.  The failure mode of a migration
    dropping the value becomes a red test rather than an
    ``IntegrityError`` on the next restart — which is the *other* of the
    entry's two fixes landing by accident.
    """

    def _sqltext(self) -> str:
        for constraint in AgentRun.__table__.constraints:
            if getattr(constraint, "name", None) == "chk_run_status":
                return str(constraint.sqltext)
        pytest.fail("chk_run_status is not on the model")

    def test_the_constraint_admits_it(self):
        assert CANCELLED_STATUS in self._sqltext()

    def test_the_constraint_admits_the_status_it_moves_from(self):
        assert RUNNING_STATUS in self._sqltext()

    def test_the_database_really_rejects_a_fifth_status(self):
        """The premise the pin rests on.

        Without this the pin asserts a string is present in a string,
        which is true of a constraint the database does not enforce.
        """
        from sqlalchemy.exc import IntegrityError

        async def work(session):
            session.add(_row(_dead_instance(), status="abandoned"))
            try:
                await session.flush()
            except IntegrityError:
                return "rejected"
            return "accepted"

        verdict, problem = rolled_back_drive(work)
        assert not problem, problem
        assert verdict == "rejected"


class TestTheStampAndTheSweepCannotDisagree:
    """One key, one owner — ``max_priority_for`` against ``PRIORITY_MAP``.

    ``_record_start`` writes the stamp and this module reads it.  A
    second spelling of the key would fail **silently**: the sweep would
    attribute nothing, ``refused`` would rise, and every abandoned row
    would stay ``running`` exactly as before the fix.
    """

    def test_the_agent_module_imports_the_key_rather_than_restating_it(self):
        """Provenance, not value.

        ``assert agent.INSTANCE_DETAIL_KEY == module.INSTANCE_DETAIL_KEY``
        is true whether the name is imported or retyped — CPython
        interns short strings — so it asserts a value where it means an
        owner.  Only the source can answer that.
        """
        import ast
        from pathlib import Path

        source = Path("sysadmin/core/agent.py").read_text()
        imported: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.ImportFrom) and node.module == (
                "sysadmin.core.abandoned_runs"
            ):
                imported |= {alias.name for alias in node.names}
        assert {"INSTANCE_DETAIL_KEY", "INSTANCE_ID"} <= imported

    def test_the_agent_module_defines_neither_of_them(self):
        """The other half — an import beside a redefinition is a shadow."""
        import ast
        from pathlib import Path

        source = Path("sysadmin/core/agent.py").read_text()
        assigned: set[str] = set()
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Assign):
                assigned |= {
                    t.id for t in node.targets if isinstance(t, ast.Name)
                }
            elif isinstance(node, ast.AnnAssign) and isinstance(
                node.target, ast.Name
            ):
                assigned.add(node.target.id)
        assert not ({"INSTANCE_DETAIL_KEY", "INSTANCE_ID"} & assigned)

    def test_a_row_record_start_would_write_is_swept_by_a_later_process(self):
        """The round trip, driven through the writer's own shape.

        Not ``_record_start`` itself: that opens a
        ``get_scheduler_session``, which commits on its own engine and
        would put a row outside this transaction and into the live table.
        What is reproduced is the value it constructs — and the AST tests
        above are what tie that reproduction to the real one.
        """
        async def work(session):
            row = AgentRun(
                id=uuid.uuid4(),
                agent=PROBE_AGENT,
                run_type="scheduled",
                status=RUNNING_STATUS,
                started_at=datetime.now(UTC),
                details={INSTANCE_DETAIL_KEY: INSTANCE_ID},
            )
            session.add(row)
            await session.flush()
            # A *later* process, which is the only caller that exists.
            await close_abandoned_runs(session, instance_id=_dead_instance())
            return (await _reread(session, row)).status

        status, problem = rolled_back_drive(work)
        assert not problem, problem
        assert status == CANCELLED_STATUS


class TestRecordStartWritesTheStamp:
    """The writer, driven — not a reconstruction of what it writes.

    Every other test here builds the row itself, so a mutation deleting
    ``details={INSTANCE_DETAIL_KEY: INSTANCE_ID}`` from
    ``_record_start`` passed all twenty: the sweep was proved correct
    about rows nothing in production would ever produce.  This drives the
    real method with its session factory replaced, which is
    ``tests/test_agent_run_recording.py``'s idiom and the only way to
    keep the row out of the live table — ``get_scheduler_session``
    commits on an engine of its own and no outer transaction can hold it.
    """

    def _added_row(self) -> AgentRun:
        import asyncio
        from contextlib import asynccontextmanager
        from unittest.mock import MagicMock, patch

        from sysadmin.core.agent import AgentResult, BaseAgent

        added: list[AgentRun] = []

        @asynccontextmanager
        async def factory():
            session = MagicMock()
            session.add = added.append
            yield session

        class _Agent(BaseAgent):
            name = "project_organiser"

            async def _execute(self, session):  # pragma: no cover - unused
                return AgentResult()

        with patch("sysadmin.core.agent.get_scheduler_session", factory):
            asyncio.run(
                _Agent()._record_start("scheduled", datetime.now(UTC))
            )
        assert len(added) == 1
        return added[0]

    def test_the_row_carries_this_process_s_instance(self):
        assert self._added_row().details == {INSTANCE_DETAIL_KEY: INSTANCE_ID}

    def test_the_row_is_written_running(self):
        """The premise the sweep's status filter rests on."""
        assert self._added_row().status == RUNNING_STATUS


class TestTheInstanceIdIsThisProcesss:
    """Rule 2 — minted, not read from the environment."""

    def test_it_is_a_uuid(self):
        uuid.UUID(INSTANCE_ID)

    def test_it_is_not_systemd_s_invocation_id(self):
        """The convention this repository states: no environment reads.

        Under the daemon ``INVOCATION_ID`` is set and equal to
        ``systemctl show -p InvocationID``; a module that read it would
        pass every other test in this file.
        """
        import os

        invocation = os.environ.get("INVOCATION_ID")
        if invocation is None:
            pytest.skip("not running under systemd — no INVOCATION_ID to differ from")
        assert INSTANCE_ID != invocation

    def test_it_is_stable_within_the_process(self):
        assert module.INSTANCE_ID is INSTANCE_ID
