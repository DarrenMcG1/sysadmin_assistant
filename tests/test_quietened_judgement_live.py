"""A reclassified breach reaching a standing row, against the real database.

``SNAG-ESTATE-010``'s check retired with the entry on 2026-08-28 — every
member of ``snag_claims.CHECKS`` names an *open* one — and **the detector
did not**.  This is that drive re-homed, ``FROZEN_TABLES``' rule and the
precedent Sessions 112, 115 and 116 each set: deleting a guard along with
its last finding takes the guard against the defect coming back, at the
moment nothing else is exercising it.

**It is stronger than the check it replaces, and deliberately so.**  That
check asserted a disjunction — the entry was refuted if *anything* about
the standing row moved, because a fix could legitimately have landed as
an in-place rung, as a resolved row plus a fresh one, or as the
``holder`` blob alone.  Now that the fix has landed, the shape is known
and the disjunction is the wrong assertion: a resolve-and-re-raise would
satisfy it while rebuilding the flip-flop ``monitor/collation.py``
refuses, and a reader of a green suite could not tell the two apart.  So
this asks which shape: **the rung moved in place, one row, still open,
nothing raised and nothing resolved.**

What it adds over ``tests/test_estate_judge_agent.py``, which models the
database with ``FakeAlert`` and a ``MagicMock`` session, is everything a
fake agrees with by construction.  ``chk_alert_severity`` really rejects
a fourth rung here; ``details`` really round-trips through ``JSONB``,
which is what :meth:`BaseAgent.refresh_alert`'s comparison is written
against; and the whole path runs through the real
:func:`sysadmin.estate.client.pull_all` — path dispatch,
``raise_for_status``, the JSON parse and the per-surface ``read`` flag —
rather than a stubbed ``pull_all`` returning a dict.

Three things are supplied and nothing else is touched, all three the
check's own:

- **the estate's answer**, through an ``httpx.MockTransport``, so the
  four surfaces other than ``audit_findings`` answer ``503`` and the
  run's sweep cannot reach a row this test did not open;
- **the sweep's attribution**, as a ``unit_audits`` row inserted inside
  the transaction, so ``_attribution`` reads it the way it reads a real
  sweep — the route Session 57's fix takes;
- **one already-open row**, at the loud rung with ``holder: null``,
  which is the state the entry was filed from.

Both ports are judged by the **same** ``_execute`` call against the same
payload and the same attribution, so the pair differs in exactly one
thing: whether a row was already open under that title.  Two runs would
differ in the clock, in what the sweep said and in what else the estate
was serving.  The rows are real and the transaction is rolled back.
"""

from datetime import UTC, datetime

import pytest

from sysadmin.core.config import get_config
from sysadmin.core.models.alert import Alert
from sysadmin.estate.agent import SURFACE_DETAIL_KEY
from sysadmin.estate.judgements import (
    DEFAULT_SEVERITY,
    TRANSIENT_HOLDER_SEVERITY,
    judge_audit_findings,
)
from sysadmin.snag_claims import (
    findings_transport,
    mounted_judge,
    quieten_finding,
    rolled_back_drive,
)
from sysadmin.units.models import UnitAudit
from sysadmin.units.ports import attribution_from_blob

#: The two ports the estate is made to report as breached.
#:
#: Far above the registry's audited range and adjacent to nothing, so
#: neither title can collide with a live row.  This test *opens* one of
#: them itself, and a collision would have it deduplicate against
#: somebody else's standing fault and read the result as its own.
OPEN_PORT = 65010
FRESH_PORT = 65011
PORTS = (OPEN_PORT, FRESH_PORT)

#: The session scope the synthetic sweep attributes both to.
#:
#: Transience is decided by *which map* a holder sits in —
#: ``transient_ports`` rather than ``unit_ports``,
#: :func:`~sysadmin.units.ports.attribution_from_blob`'s rule — and never
#: by the name, so the ``.scope`` suffix is legibility for a reader and
#: not the signal being tested.
HOLDER = "user:snag-live-probe.scope"

PROBE_MESSAGE = "sysadmin live probe row — never committed"


def _db_available() -> bool:
    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            "postgresql+psycopg2://gaddi@localhost:5432/projects",
            connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


def _drive():
    """One ``_execute`` over two synthetic breaches; everything read back."""
    from sqlalchemy import select

    config = get_config()
    payload = {"findings": [quieten_finding(port) for port in PORTS]}
    blob = {"transient_ports": {HOLDER: list(PORTS)}}
    attribution = attribution_from_blob(blob, datetime.now(UTC).isoformat())

    # What the run *ought* to produce, computed purely and before any row
    # exists. The titles come from here rather than from a format string:
    # a title written down would stop matching the day the producer's
    # wording moves, and this test would then open a row the run never
    # judges and report the fix broken by a rename.
    judged = judge_audit_findings(
        payload, config.agents.estate_judge.port_breach_max_rows, attribution
    )
    by_port = {judgement.details.get("port"): judgement for judgement in judged}
    open_title = by_port[OPEN_PORT].title
    fresh_title = by_port[FRESH_PORT].title

    agent, problem = mounted_judge(findings_transport(payload))
    assert agent is not None, problem

    async def work(session):
        session.add(
            Alert(
                agent=agent.name,
                severity=DEFAULT_SEVERITY,
                title=open_title,
                message=PROBE_MESSAGE,
                details={
                    SURFACE_DETAIL_KEY: by_port[OPEN_PORT].surface,
                    "port": OPEN_PORT,
                    # The rows the entry was filed from carry
                    # `holder: null` — raised before the sweep's
                    # attribution reached this family at all. Modelled
                    # rather than left absent, so "the blob did not
                    # arrive" is a value that did not change and not a
                    # key missing for two possible reasons.
                    "holder": None,
                },
            )
        )
        session.add(UnitAudit(scanned_at=datetime.now(UTC), findings={"ports": blob}))
        await session.flush()

        result = await agent._execute(session)  # noqa: SLF001
        await session.flush()
        session.expire_all()

        rows = list(
            (
                await session.execute(
                    select(Alert).where(
                        Alert.agent == agent.name,
                        Alert.title.in_([open_title, fresh_title]),
                    )
                )
            )
            .scalars()
            .all()
        )
        standing = [row for row in rows if row.title == open_title]
        fresh = [row for row in rows if row.title == fresh_title]
        after = standing[0] if len(standing) == 1 else None
        new_row = fresh[0] if len(fresh) == 1 else None
        return {
            # Read off the judgement rather than written down, so a
            # rung this module asserted against a family that had moved
            # would fail here rather than pass quietly.
            "judged_quiet": {j.severity for j in judged},
            "loud": DEFAULT_SEVERITY,
            "standing_rows": len(standing),
            "standing_severity": after.severity if after is not None else None,
            "standing_resolved": bool(after.resolved) if after is not None else None,
            "standing_message": after.message if after is not None else None,
            "standing_holder": (
                (after.details or {}).get("holder") if after is not None else None
            ),
            "fresh_rows": len(fresh),
            "fresh_severity": new_row.severity if new_row is not None else None,
            "fresh_holder": (
                (new_row.details or {}).get("holder") if new_row is not None else None
            ),
            "raised": result.alerts_raised,
            "resolved": result.details["resolved"],
            "refreshed": result.details["refreshed"],
        }

    reading, problem = rolled_back_drive(work)
    assert reading is not None, problem
    return reading


@pytest.fixture(scope="module")
def reading():
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    return _drive()


class TestTheQuieteningAgainstTheRealDatabase:
    def test_the_premises_hold_or_nothing_below_means_anything(self, reading):
        """The witness, and the reason it is not optional.

        A standing row that did not move is evidence only if the run
        genuinely had something quieter to move it *to*.  A judge that
        had stopped computing the quiet rung, or a sweep whose
        attribution no longer reached this family, would leave the row
        untouched and look identical — so the same ``_execute`` judges a
        second port with nothing open under its title, and that row must
        land at the quiet rung carrying a transient holder before any
        assertion below means anything.
        """
        assert reading["judged_quiet"] == {TRANSIENT_HOLDER_SEVERITY}
        assert TRANSIENT_HOLDER_SEVERITY != reading["loud"], (
            "a transient holder is judged at the same rung as an ordinary "
            "breach — there is no quieter rung to deliver and nothing here "
            "discriminates"
        )
        assert reading["fresh_rows"] == 1
        assert reading["fresh_severity"] == TRANSIENT_HOLDER_SEVERITY
        assert reading["fresh_holder"]["transient"] is True

    def test_the_rung_reached_the_standing_row(self, reading):
        """The entry, refuted.

        It was filed because ``EstateJudgeAgent._execute`` skips a
        judgement whose title is already open before it looks at
        anything else, so Session 57's quieter rung applied only to
        breaches raised *afterwards* — and the two live rows it was
        written for sat at ``warning`` for the life of a VS Code window.
        """
        assert reading["standing_severity"] == TRANSIENT_HOLDER_SEVERITY

    def test_it_arrived_in_place_and_not_by_a_second_row(self, reading):
        """Which shape, not merely that something moved.

        Resolve-and-re-raise on a severity mismatch is the obvious fix
        and rebuilds the flip-flop ``monitor/collation.py`` refuses: the
        judged rung is computed from ``details`` the estate republishes
        every hour, so a producer wobbling between two rungs would clear
        and re-open the row each time, and every flip clears the tray's
        ``{severity}:{title}`` fingerprint and notifies.  The retired
        check could not tell the two apart — it asserted the disjunction
        on purpose, because any of three shapes would have been a fix.
        """
        assert reading["standing_rows"] == 1
        assert reading["standing_resolved"] is False
        assert reading["raised"] == 1, "the fresh port, and only the fresh port"
        assert reading["resolved"] == 0
        assert reading["refreshed"] == 1

    def test_the_blob_arrived_with_it(self, reading):
        """``SNAG-AGENT-009``'s half, which landed first and still holds.

        The two halves are one write — ``message`` and ``details`` move
        together, that method's rule 1 — so a fix that moved the rung
        without them would leave the row's sentence describing a breach
        it no longer claims to be.
        """
        assert reading["standing_holder"]["transient"] is True
        assert reading["standing_message"] != PROBE_MESSAGE
