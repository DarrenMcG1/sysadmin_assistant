"""The open-alert identity and the flag/timestamp CHECKs, against the real database.

``SNAG-DB-007``, migration 019.  The model declares
``uq_alerts_open_agent_title``, ``chk_alert_resolved_stamped`` and
``chk_alert_acknowledged_stamped``, but a model is not the schema:
``tests/test_schema_drift.py`` cannot see a CHECK at all, because
``compare_metadata`` does not diff them.  So each rule is driven at the
live table, inside a transaction that is rolled back.

Two of these are about what the index must **admit**, and they matter as
much as the refusals.  The same title under another agent is legal in
the application, so an index on ``title`` alone would fail that agent's
run.  And ``step_for``'s resolve-and-re-raise, as
``SysAdminAgent`` writes it for the ``agent failing`` and ``agent
stalled`` families, marks the quiet row resolved on the ORM object and
inserts the loud one in the same flush; that works under a
non-deferrable index only because SQLAlchemy emits a mapper's ``UPDATE``
before its ``INSERT``.

Every title carries a fresh UUID, so no drive can collide with a row
that is really open on this box.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.snag_claims import rolled_back_drive

INDEX = "uq_alerts_open_agent_title"
RESOLVED_CHECK = "chk_alert_resolved_stamped"
ACKNOWLEDGED_CHECK = "chk_alert_acknowledged_stamped"

#: Both admitted by ``chk_alert_agent``.
AGENT = "sysadmin"
OTHER_AGENT = "log_aggregator"


def _title() -> str:
    return f"snag-db-007 probe {uuid.uuid4()}"


def _row(title: str, *, agent: str = AGENT, severity: str = "warning", **columns) -> Alert:
    return Alert(agent=agent, severity=severity, title=title, message="probe", **columns)


async def _refusal(session, *rows: Alert) -> str | None:
    """Flush ``rows`` in a savepoint; the error text if refused, else ``None``."""
    try:
        async with session.begin_nested():
            session.add_all(rows)
            await session.flush()
    except IntegrityError as exc:
        return str(exc.orig)
    return None


async def _open_count(session, title: str) -> int:
    return await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.title == title, unresolved())
    )


@pytest.mark.box
class TestOneOpenRowPerAlert:
    @pytest.mark.premise
    def test_a_second_open_row_for_the_pair_is_refused(self):
        """The witness for every admission in this file.

        An admission is a negative, and a table with no index admits
        everything: without this refusal the three tests that expect
        ``None`` would pass against a schema that holds nothing.
        """
        title = _title()

        async def work(session):
            assert await _refusal(session, _row(title)) is None
            return await _refusal(session, _row(title))

        refused, problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is not None
        assert INDEX in refused

    def test_the_same_title_under_another_agent_is_admitted(self):
        title = _title()

        async def work(session):
            return await _refusal(session, _row(title), _row(title, agent=OTHER_AGENT))

        refused, problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is None

    def test_a_resolved_row_does_not_hold_the_identity(self):
        title = _title()
        closed = _row(title, resolved=True, resolved_at=datetime.now(UTC))

        async def work(session):
            return await _refusal(session, closed, _row(title))

        refused, problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is None

    def test_an_escalation_resolves_and_re_raises_in_one_flush(self):
        """The shape at ``monitor/agent.py``'s two ladder families.

        The quiet row is resolved by attribute, not by an ``UPDATE``
        statement, and the loud row is added before anything flushes, so
        the order the two reach the database is the unit of work's.
        """
        title = _title()

        async def work(session):
            quiet = _row(title, severity="warning")
            session.add(quiet)
            await session.flush()

            quiet.resolved = True
            quiet.resolved_at = datetime.now(UTC)
            refused = await _refusal(session, _row(title, severity="critical"))
            open_severities = (
                await session.scalars(
                    select(Alert.severity).where(Alert.title == title, unresolved())
                )
            ).all()
            return refused, open_severities

        (refused, open_severities), problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is None
        assert open_severities == ["critical"]


@pytest.mark.box
class TestAFlagCarriesItsTimestamp:
    @pytest.mark.parametrize(
        ("columns", "constraint"),
        [
            ({"resolved": True}, RESOLVED_CHECK),
            ({"resolved": False, "resolved_at": datetime.now(UTC)}, RESOLVED_CHECK),
            ({"acknowledged": True}, ACKNOWLEDGED_CHECK),
            ({"acknowledged": False, "acknowledged_at": datetime.now(UTC)}, ACKNOWLEDGED_CHECK),
        ],
        ids=[
            "resolved-undated",
            "dated-unresolved",
            "acknowledged-undated",
            "dated-unacknowledged",
        ],
    )
    def test_a_disagreeing_pair_is_refused(self, columns, constraint):
        async def work(session):
            return await _refusal(session, _row(_title(), **columns))

        refused, problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is not None
        assert constraint in refused

    def test_both_pairs_set_together_are_admitted(self):
        now = datetime.now(UTC)
        row = _row(
            _title(), resolved=True, resolved_at=now, acknowledged=True, acknowledged_at=now
        )

        async def work(session):
            return await _refusal(session, row)

        refused, problem = rolled_back_drive(work)
        assert not problem, problem
        assert refused is None


@pytest.mark.box
def test_the_model_and_the_database_name_the_same_constraints():
    """The half ``test_schema_drift.py`` cannot see.

    ``compare_metadata`` diffs indexes and ignores CHECKs, so a CHECK
    renamed or dropped on one side only would pass the drift guard.
    """
    declared = {
        c.name for c in Alert.__table__.constraints if c.name and c.name.startswith("chk_")
    } | {i.name for i in Alert.__table__.indexes}

    async def work(session):
        checks = await session.scalars(
            text(
                "SELECT conname FROM pg_constraint"
                " WHERE conrelid = 'sysadmin.alerts'::regclass AND contype = 'c'"
            )
        )
        indexes = await session.scalars(
            text(
                "SELECT indexname FROM pg_indexes"
                " WHERE schemaname = 'sysadmin' AND tablename = 'alerts'"
            )
        )
        return set(checks.all()) | set(indexes.all())

    live, problem = rolled_back_drive(work)
    assert not problem, problem
    assert {INDEX, RESOLVED_CHECK, ACKNOWLEDGED_CHECK} <= declared
    assert declared <= live
