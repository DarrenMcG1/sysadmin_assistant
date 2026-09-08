"""The GPU-context predicate against the real box, not a stand-in.

``tests/test_gpu_context.py`` pins the rules with fixtures.  Four things
it structurally cannot say, and each of them is a way this fix could ship
green and inert:

1. **That systemd still publishes the instant in the form the parse
   expects.**  ``ActiveEnterTimestamp`` under
   ``--timestamp=unix`` is read from ``systemctl``, and a fixture
   asserting ``@1788753615`` asserts a string somebody typed.
   :func:`~sysadmin.monitor.systemd.parse_start_instant` refuses anything
   that is not the ``@<epoch>`` form, so a systemd that stopped honouring
   the flag would make every declared service read *unevaluated* — quiet,
   correct-by-its-own-lights, and blind.  That is the failure this file
   exists to make loud.

2. **That the gate really leaves the ten timers alone.**  The whole
   reason the flag is a parameter rather than unconditional is that
   ``--timestamp=`` is a *command* flag and also re-renders
   ``LastTriggerUSec``, which
   :func:`~sysadmin.monitor.service_recommendations._observed_fires`
   reads as a firing whenever the token changes.  A fixture can assert
   which arguments were composed; only the real binary can say what it
   renders in reply.

3. **That the predicate reaches a verdict against the live table.**  The
   adapter's statement is index-scannable only because of a floor whose
   removal no behavioural test can see.

4. **That the verdict flips when a reset is actually there.**  Both
   declared services read clean today — each restarted after the last
   stored reset — so this **ships untriggered**, which is
   ``SNAG-LOG-005``'s position and the reason a counterfactual is the
   only thing that can prove the wiring.  The synthetic reset is written
   inside :func:`~sysadmin.snag_claims.rolled_back_drive`, so it is a
   real row read by the real statement and no row survives the test.

The skip is loud and states what it found, because a run reporting
"nothing to compare" is not a run reporting health (``ports_checked``'s
rule).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from sysadmin.monitor import gpu_context
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import load_services
from sysadmin.monitor.systemd import (
    START_INSTANT_PROP,
    SystemdQueryError,
    get_unit_status,
    parse_start_instant,
)
from sysadmin.snag_claims import rolled_back_drive

#: A declared spelling, taken from :data:`CRITICAL_SIGNATURES` rather than
#: typed, so a kernel reword cannot leave this file asserting against a
#: line the family no longer recognises.  The synthetic row must sign to a
#: declared key or the drive proves nothing about the predicate.
SYNTHETIC_LINE = "amdgpu 0000:03:00.0: VRAM is lost due to GPU reset!"

REPO_ROOT = Path(__file__).resolve().parents[1]


def _declared():
    return [s for s in load_services(REPO_ROOT / "services.yaml").services if s.holds_vram]


@pytest.fixture(scope="module")
def declared():
    services = _declared()
    if not services:
        pytest.skip(
            "no service in services.yaml declares holds_vram, so this drive "
            "has nothing to evaluate — 'could not tell', not 'no service "
            "holds a GPU context'"
        )
    return services


@pytest.fixture(scope="module")
def timer_unit():
    entries = load_services(REPO_ROOT / "services.yaml").services
    timers = [s for s in entries if s.kind == "timer" and s.user]
    if not timers:
        pytest.skip("no user timer declared, so the regression has no witness here")
    return timers[0]


class TestTheDeclaredSignatureIsStillReachable:
    @pytest.mark.premise
    def test_the_synthetic_line_signs_to_a_declared_key(self):
        """Or every assertion below is about a line nothing recognises.

        The premise, and not optional: a kernel reword moves the
        declaration (it did, on 2026-09-04) and a drive built on a stale
        spelling would go on passing while measuring nothing.
        """
        from sysadmin.monitor.log_signature import signature

        assert ("kernel", signature(SYNTHETIC_LINE)) in gpu_context.declared_reset_keys()


class TestSystemdStillPublishesTheInstant:
    def test_every_declared_unit_answers_with_an_epoch(self, declared):
        """The form, from the binary — not from a string in a fixture."""
        import asyncio

        async def read(svc):
            try:
                return await get_unit_status(
                    svc.unit, user=svc.user, start_instant=True
                )
            except SystemdQueryError as exc:
                pytest.skip(f"systemctl could not answer for {svc.unit}: {exc}")

        seen = 0
        for svc in declared:
            info = asyncio.run(read(svc))
            if not info.get("is_active"):
                continue
            raw = info.get(START_INSTANT_PROP)
            assert raw and raw.startswith("@"), (svc.unit, raw)
            started = parse_start_instant(raw)
            assert started is not None and started.tzinfo is not None
            assert started < datetime.now(UTC)
            seen += 1
        if not seen:
            pytest.skip(
                "no declared service is currently active, so systemd "
                "publishes no start instant to read — this is 'could not "
                "tell', not 'the rendering is current'"
            )

    def test_a_timer_read_without_the_gate_keeps_its_own_rendering(self, timer_unit):
        """The regression the parameter exists to prevent, at the binary.

        ``last_run`` is stored verbatim and compared only for inequality,
        so a rendering change is read as a firing.  If this ever returns
        an ``@epoch``, the flag has escaped its gate and every
        ``kind: timer`` series has a spurious fire in it.
        """
        import asyncio

        try:
            info = asyncio.run(get_unit_status(timer_unit.unit, user=timer_unit.user))
        except SystemdQueryError as exc:
            pytest.skip(f"systemctl could not answer for {timer_unit.unit}: {exc}")
        token = info.get("LastTriggerUSec")
        if not token:
            pytest.skip(f"{timer_unit.unit} has never fired, so it renders no token")
        assert not token.startswith("@"), (
            f"{timer_unit.unit} rendered {token!r} — the timestamp flag has "
            "escaped its gate and every timer series now carries a spurious "
            "firing at this deploy"
        )


class TestThePredicateRunsAgainstTheLiveTable:
    def test_each_declared_service_reaches_a_verdict(self, declared):
        """Not *which* verdict — that is a property of the day.

        What is asserted is that the statement executes against the real
        table and the adapter returns something a caller can record.
        """
        async def work(session):
            out = {}
            for svc in declared:
                started = datetime.now(UTC) - timedelta(days=1)
                out[svc.name] = await gpu_context.reset_since(session, started)
            return out

        verdicts, problem = rolled_back_drive(work)
        assert not problem, problem
        assert set(verdicts) == {svc.name for svc in declared}
        for name, sighting in verdicts.items():
            assert sighting is None or sighting.at.tzinfo is not None, name

    def test_a_reset_the_unit_predates_is_found_and_a_later_start_is_not(self):
        """The counterfactual, because the live population is empty today.

        One synthetic row, three start instants, one rolled-back
        transaction.  The tie is the middle one and is the only place
        rule 2 is observable at all: ``logged_at`` carries microseconds
        live, so an exact tie cannot occur on real data.
        """
        exact = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)

        async def work(session):
            session.add(LogEntry(
                source="kernel",
                severity="info",
                message=SYNTHETIC_LINE,
                raw_line=None,
                logged_at=exact,
            ))
            await session.flush()
            return {
                "before": await gpu_context.reset_since(
                    session, exact - timedelta(seconds=1)
                ),
                "tie": await gpu_context.reset_since(session, exact),
                "after": await gpu_context.reset_since(
                    session, exact + timedelta(seconds=1)
                ),
            }

        seen, problem = rolled_back_drive(work)
        assert not problem, problem
        assert seen["before"] is not None, (
            "a reset newer than the start instant was not found, so the "
            "predicate cannot fire on this box at all"
        )
        assert seen["before"].at == exact
        assert "VRAM is lost due to GPU reset!" in seen["before"].signature
        assert seen["tie"] is None
        assert seen["after"] is None

    def test_an_unanswerable_read_does_not_cost_the_run_its_other_rows(self):
        """The containment, driven at a statement PostgreSQL really rejects.

        `_check_service` runs before the per-service savepoint and the
        run's transaction is already open, so an aborted statement aborts
        the transaction — every later service's write would fail with
        `InFailedSqlTransaction`, `_isolate_write_failure`'s recovery
        savepoint included.  A fixture cannot witness this: only a real
        backend enforces the aborted-transaction rule, and a mocked
        session raising `SQLAlchemyError` leaves nothing poisoned.

        Falsified by removing the `begin_nested()` wrapper, which turns
        the second half of this red with the exact production symptom.
        """
        from sqlalchemy import select, text

        from sysadmin.monitor.models.service_health import ServiceHealth

        async def work(session):
            agent = SysAdminAgent()
            with patch.object(
                gpu_context,
                "candidate_statement",
                lambda started_at: select(text("no_such_column_at_all")),
            ):
                status, _, details = await agent._gpu_context_reading(
                    _declared()[0],
                    "probe.service",
                    {START_INSTANT_PROP: "@1788723780"},
                    "ok",
                    5,
                    {},
                    session,
                )
            # The session must still be usable afterwards, which is the
            # whole claim — asserted with a real query rather than by
            # inspecting a flag.
            survived = (
                await session.execute(select(ServiceHealth.id).limit(1))
            ).first()
            return status, details, survived is not None or survived is None

        out, problem = rolled_back_drive(work)
        # `problem` first, and unpacked only after: without the savepoint
        # the whole drive aborts and `out` is None, so unpacking first
        # reports a TypeError instead of naming the poisoned transaction.
        assert not problem, (
            "the failed read took the drive's transaction with it, which is "
            f"the containment this asserts: {problem}"
        )
        status, details, usable = out
        assert status == "ok"
        assert details[gpu_context.DETAIL_KEY]["evaluated"] is False
        assert usable, "the run's transaction did not survive the failed read"

    def test_the_drive_left_no_row_behind(self):
        """The harness's own claim, asserted rather than trusted.

        A live drive that leaks is a control the next fix breaks — this
        repository has produced that once, when ``rolled_back_drive``
        committed three rows into ``alerts``.
        """
        exact = datetime(2026, 9, 8, 12, 0, 0, tzinfo=UTC)

        async def check(session):
            return await gpu_context.reset_since(
                session, exact - timedelta(seconds=1)
            )

        after, problem = rolled_back_drive(check)
        assert not problem, problem
        assert after is None or after.at != exact, (
            "the synthetic reset from the previous test survived its rollback"
        )
