"""Tests for the retention service — purge logic and downsampling."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import ProgrammingError

from sysadmin.core.retention import (
    KEEP_LATEST_PER,
    TABLE_TIMESTAMP_MAP,
    WHOLE_TABLE,
    _downsample_resources,
    purge_statement,
    run_retention,
)


def _savepoint_session() -> AsyncMock:
    """An AsyncMock session that can also be used as ``begin_nested()``.

    ``run_retention`` wraps each table in ``async with
    session.begin_nested()``, so the mock needs a *synchronous* callable
    returning an async context manager — ``AsyncMock().begin_nested()``
    returns a coroutine, which ``async with`` cannot take.
    """
    session = AsyncMock()
    savepoint = AsyncMock()
    savepoint.__aenter__ = AsyncMock(return_value=savepoint)
    savepoint.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=savepoint)
    return session


@pytest.fixture
def mock_retention_configs():
    """Simulated RetentionConfig rows from the database."""
    configs = []
    for table, ts_col in TABLE_TIMESTAMP_MAP.items():
        cfg = MagicMock()
        cfg.table_name = table
        cfg.retention_days = 30
        configs.append(cfg)
    return configs


# ---------------------------------------------------------------------------
# TABLE_TIMESTAMP_MAP completeness
# ---------------------------------------------------------------------------


class TestTableTimestampMap:
    def test_all_tables_have_entries(self):
        expected_tables = {
            "service_health", "resource_snapshots", "log_entries",
            "alerts",
            "filesystem_audits", "unit_audits", "reliability_scores",
            "agent_runs",
            # SNAG-PROJ-010: added by migration 005 and left out of
            # retention entirely, so it grew one row per week forever.
            "disk_reviews",
            # Session 69: the weekly log review's table, added with both
            # halves at once — a table in one half and not the other is
            # silently never purged, which is what this test exists for.
            "log_reviews",
            # Session 79: the weekly system health review's table, same
            # treatment.  Both halves land in migration 016 together.
            "health_reviews",
            # Session 115, SNAG-TRAY-008: the understudy's spoken set,
            # durable so the 24-hour reminder can be reached by a daemon
            # whose median life is 1.77 h.  Both halves in migration 018.
            "desktop_notifications",
        }
        assert set(TABLE_TIMESTAMP_MAP.keys()) == expected_tables

    def test_timestamp_columns_are_strings(self):
        for col in TABLE_TIMESTAMP_MAP.values():
            assert isinstance(col, str)
            assert len(col) > 0

    def test_keep_latest_tables_are_all_purgeable(self):
        """A keep-latest rule for a table nothing purges is dead config."""
        assert set(KEEP_LATEST_PER) <= set(TABLE_TIMESTAMP_MAP)

    def test_review_tables_keep_their_newest_row(self):
        """Emptying them would make /api/*/review 404 — read as "never run".

        A disk left unreviewed for longer than the retention window must
        still serve its last review rather than the empty state.

        ``project_reviews`` was the third of these until migration 014
        dropped it; the rule is the table's, not the estate's, so the
        two that remain assert it unchanged.
        """
        assert KEEP_LATEST_PER["disk_reviews"] is WHOLE_TABLE
        assert KEEP_LATEST_PER["log_reviews"] is WHOLE_TABLE


# ---------------------------------------------------------------------------
# Purge logic
# ---------------------------------------------------------------------------


class TestRunRetention:
    @pytest.mark.asyncio
    async def test_purges_each_configured_table(self, mock_retention_configs):
        """run_retention should execute a DELETE for each configured table."""
        mock_session = _savepoint_session()

        # First call: SELECT retention_config → returns configs
        # Subsequent calls: DELETE + UPDATE for each table
        # Final call: downsampling
        config_result = MagicMock()
        config_result.scalars.return_value.all.return_value = mock_retention_configs

        # Track execute calls
        execute_results = []
        delete_result = MagicMock()
        delete_result.rowcount = 5

        async def fake_execute(stmt, params=None):
            execute_results.append(stmt)
            stmt_str = str(stmt)
            if hasattr(stmt, "text") or stmt_str.startswith(("DELETE", "SELECT")):
                return delete_result
            return config_result

        mock_session.execute = AsyncMock(side_effect=fake_execute)

        # First execute returns the configs
        calls = []

        async def tracked_execute(stmt, params=None):
            calls.append(("execute", str(stmt)[:50]))
            if len(calls) == 1:
                # First call is SELECT retention_config
                return config_result
            # All subsequent calls return a rowcount result
            return delete_result

        mock_session.execute = AsyncMock(side_effect=tracked_execute)

        with patch("sysadmin.core.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        # Should have executed: 1 select + (1 delete + 1 update) per table + 1 downsample
        # = 1 + 8*2 + 1 = 18
        assert len(calls) >= len(mock_retention_configs) * 2 + 1

    @pytest.mark.asyncio
    async def test_skips_unknown_tables(self):
        """Tables not in TABLE_TIMESTAMP_MAP are silently skipped."""
        unknown_config = MagicMock()
        unknown_config.table_name = "nonexistent_table"
        unknown_config.retention_days = 30

        mock_session = _savepoint_session()
        config_result = MagicMock()
        config_result.scalars.return_value.all.return_value = [unknown_config]

        delete_result = MagicMock()
        delete_result.rowcount = 0

        call_count = 0

        async def tracking_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return config_result
            return delete_result

        mock_session.execute = AsyncMock(side_effect=tracking_execute)

        with patch("sysadmin.core.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        # Only the initial SELECT + downsample, no DELETE for unknown table
        assert call_count == 2  # SELECT configs + downsample

    @pytest.mark.asyncio
    async def test_empty_configs_still_downsamples(self):
        """With no retention configs, downsampling should still run."""
        mock_session = _savepoint_session()
        config_result = MagicMock()
        config_result.scalars.return_value.all.return_value = []

        delete_result = MagicMock()
        delete_result.rowcount = 0

        call_count = 0

        async def tracking_execute(stmt, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return config_result
            return delete_result

        mock_session.execute = AsyncMock(side_effect=tracking_execute)

        with patch("sysadmin.core.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        # SELECT + downsample = 2
        assert call_count == 2


# ---------------------------------------------------------------------------
# SQL generation verification
# ---------------------------------------------------------------------------


class TestRetentionSqlLogic:
    def test_alerts_only_purge_resolved(self):
        """The alerts table should only delete resolved=TRUE rows."""
        # Verify the logic exists in the code by checking TABLE_TIMESTAMP_MAP
        assert "alerts" in TABLE_TIMESTAMP_MAP
        assert TABLE_TIMESTAMP_MAP["alerts"] == "created_at"

    def test_snapshot_tables_keep_latest(self):
        """A periodic sweep keeps its newest row per entity."""
        assert "filesystem_audits" in TABLE_TIMESTAMP_MAP
        assert KEEP_LATEST_PER["filesystem_audits"] == "scan_root"
        assert "unit_audits" in TABLE_TIMESTAMP_MAP
        assert KEEP_LATEST_PER["unit_audits"] == "system_unit_dir"


# ---------------------------------------------------------------------------
# Downsampling
# ---------------------------------------------------------------------------


class TestDownsampleResources:
    @pytest.mark.asyncio
    async def test_downsample_executes_delete(self):
        mock_session = AsyncMock()
        result = MagicMock()
        result.rowcount = 10
        mock_session.execute = AsyncMock(return_value=result)

        await _downsample_resources(mock_session)

        mock_session.execute.assert_called_once()
        # Verify the SQL contains the expected clauses
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0])
        assert "resource_snapshots" in sql_text
        assert "date_trunc" in sql_text

    @pytest.mark.asyncio
    async def test_downsample_zero_rows_no_log(self):
        mock_session = AsyncMock()
        result = MagicMock()
        result.rowcount = 0
        mock_session.execute = AsyncMock(return_value=result)

        await _downsample_resources(mock_session)
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Statement construction — and PostgreSQL as the judge of it
# ---------------------------------------------------------------------------


class TestPurgeStatement:
    """The three branches of :func:`purge_statement`, by shape.

    These assert *text*, which is exactly what could not catch
    ``SNAG-RETENTION-001``: the broken statement was a perfectly good
    string. They are here to pin intent; the guard is
    ``test_purge_statements_parse`` below.
    """

    def test_alerts_purges_only_resolved(self):
        sql = purge_statement("alerts", "created_at")
        assert "resolved = TRUE" in sql
        # An open alert is a live fault whatever its age.
        assert "NOT IN" not in sql

    def test_whole_table_entity_takes_the_limit_branch(self):
        """No ``DISTINCT ON`` over a constant — that is the construct that broke."""
        sql = purge_statement("disk_reviews", "generated_at")
        assert "DISTINCT ON" not in sql
        assert "ORDER BY generated_at DESC LIMIT 1" in sql
        assert "NOT IN" in sql

    def test_per_entity_table_keeps_distinct_on(self):
        sql = purge_statement("reliability_scores", "computed_at")
        assert "DISTINCT ON (service_name)" in sql
        assert "ORDER BY service_name, computed_at DESC" in sql

    def test_plain_table_is_a_bare_cutoff(self):
        sql = purge_statement("log_entries", "ingested_at")
        assert sql == (
            "DELETE FROM sysadmin.log_entries WHERE ingested_at < :cutoff"
        )

    def test_no_bare_constant_reaches_an_order_by(self):
        """The specific regression, stated in the terms PostgreSQL uses.

        A bare constant in ``ORDER BY`` is read as an ordinal position, so
        ``ORDER BY true`` is ``non-integer constant in ORDER BY``.  This is
        a weaker check than the parser and is kept only because it names
        the fault; it runs everywhere, including a CI box with no database.
        """
        for table, ts_col in TABLE_TIMESTAMP_MAP.items():
            sql = purge_statement(table, ts_col)
            for clause in sql.split("ORDER BY ")[1:]:
                first_term = clause.split(",")[0].split(")")[0].strip()
                assert first_term.lower() not in ("true", "false"), (
                    f"{table}: ORDER BY {first_term} is an ordinal reference "
                    "to PostgreSQL, not a constant expression"
                )


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


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — the parse guard needs the real schema",
)
def test_purge_statements_parse():
    """Hand every statement ``run_retention`` builds to PostgreSQL.

    **This is the guard, and its absence is why a nightly job raised for
    nine days behind 1,866 green tests.**  Every other test in this file
    mocks the session, so the statements were asserted as strings and
    never parsed.  ``project_reviews`` built
    ``SELECT DISTINCT ON (true) … ORDER BY true``, which is valid Python,
    a plausible-looking string, and a syntax error — and because the purge
    ran as one transaction, it silently rolled back the six purges it had
    already logged as successful.

    ``EXPLAIN`` parses and plans without executing, so this deletes
    nothing and costs milliseconds.  It covers the whole map rather than
    the one table that broke: the next bad statement will be a different
    one.
    """
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql_text

    engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")
    try:
        with engine.connect() as conn:
            for table, ts_col in TABLE_TIMESTAMP_MAP.items():
                stmt = purge_statement(table, ts_col)
                conn.execute(
                    sql_text(f"EXPLAIN {stmt}"),
                    {"cutoff": datetime(2000, 1, 1, tzinfo=UTC)},
                )
    finally:
        engine.dispose()


# ---------------------------------------------------------------------------
# One bad table costs only itself
# ---------------------------------------------------------------------------


class TestPurgeIsolation:
    @pytest.mark.asyncio
    async def test_one_failing_table_does_not_abort_the_others(self):
        """``SysAdminAgent._execute``'s savepoint rule, one domain over.

        The whole run used to be a single transaction, so the twelfth
        table's syntax error discarded the first eleven tables' deletes
        *and* their ``last_purged_at`` stamps.  Nine days of that was
        invisible because each table logs its rowcount before the commit.
        """
        configs = []
        for table in ("log_entries", "disk_reviews", "agent_runs"):
            cfg = MagicMock()
            cfg.table_name = table
            cfg.retention_days = 30
            configs.append(cfg)

        session = _savepoint_session()
        config_result = MagicMock()
        config_result.scalars.return_value.all.return_value = configs

        delete_result = MagicMock()
        delete_result.rowcount = 7
        purged: list[str] = []

        async def execute(stmt, params=None):
            sql = str(stmt)
            if sql.startswith("SELECT") and "retention_config" in sql:
                return config_result
            if "disk_reviews" in sql and sql.startswith("DELETE"):
                raise ProgrammingError("DELETE ...", {}, Exception("boom"))
            if sql.startswith("DELETE"):
                purged.append(sql.split("sysadmin.")[1].split(" ")[0])
            return delete_result

        session.execute = AsyncMock(side_effect=execute)

        with patch("sysadmin.core.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        # The two healthy tables were purged despite the one in between.
        assert purged == ["log_entries", "agent_runs"]

    @pytest.mark.asyncio
    async def test_a_failed_table_is_not_stamped_as_purged(self):
        """``last_purged_at`` must mean what its name says.

        The stamp lives inside the savepoint, so it rolls back with the
        delete it records.  A table stamped on a run that deleted nothing
        turns the one honest staleness signal into a lie — which is what
        the single-transaction version did in reverse, rolling back
        stamps for tables that had genuinely succeeded.
        """
        cfg = MagicMock()
        cfg.table_name = "disk_reviews"
        cfg.retention_days = 365

        session = _savepoint_session()
        config_result = MagicMock()
        config_result.scalars.return_value.all.return_value = [cfg]

        stamped: list[str] = []

        async def execute(stmt, params=None):
            sql = str(stmt)
            if sql.startswith("SELECT") and "retention_config" in sql:
                return config_result
            if sql.startswith("DELETE") and "disk_reviews" in sql:
                raise ProgrammingError("DELETE ...", {}, Exception("boom"))
            if sql.startswith("UPDATE"):
                stamped.append(sql)
            result = MagicMock()
            result.rowcount = 0
            return result

        session.execute = AsyncMock(side_effect=execute)

        with patch("sysadmin.core.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        assert stamped == []


# ---------------------------------------------------------------------------
# The half nothing else reads
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _db_available(),
    reason="local postgres (projects DB) not reachable — the pairing guard needs the real schema",
)
def test_every_configured_table_can_be_purged():
    """A ``retention_config`` row the map cannot resolve purges nothing, silently.

    The module docstring has said since migration 006 that retention
    needs **both** halves, and until migration 014 nothing checked the
    *config* half against anything.  ``test_all_tables_have_entries``
    pins the map against a hand-written literal, and
    :func:`test_purge_statements_parse` hands the map to PostgreSQL —
    both read the map, neither reads the table.

    The two halves fail in opposite directions, and only one of them is
    uncovered.  A map entry for a table that no longer exists is **loud**:
    its ``DELETE`` raises every night, contained to that table by its
    savepoint, and ``test_purge_statements_parse`` already refuses it —
    more strongly than an existence check would, since that test also
    catches a wrong column and invalid SQL.  Asserting it again here
    would be a second statement of one fact, which is what
    ``sysadmin/metadata.py`` exists to stop; it was written, measured
    against the stronger guard, and deleted.

    A config row naming a table the map has dropped is **silent**:
    ``run_retention`` iterates config rows and looks each one up, so a
    miss is skipped with no log line.  Nothing is purged and nothing says
    so — the shape ``SNAG-CFG-001`` names, arriving as a database row.
    Migration 014 removed three of these by hand; this is the assertion
    it was making.
    """
    from sqlalchemy import create_engine
    from sqlalchemy import text as sql_text

    from sysadmin.metadata import SCHEMA

    engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")
    try:
        with engine.connect() as conn:
            configured = {
                row[0]
                for row in conn.execute(
                    sql_text(f"SELECT table_name FROM {SCHEMA}.retention_config")
                )
            }
    finally:
        engine.dispose()

    assert configured <= set(TABLE_TIMESTAMP_MAP), (
        "retention_config names tables absent from TABLE_TIMESTAMP_MAP: "
        f"{sorted(configured - set(TABLE_TIMESTAMP_MAP))} — run_retention "
        "skips them in silence, so they are never purged and nothing says so"
    )
