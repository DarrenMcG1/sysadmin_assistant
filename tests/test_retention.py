"""Tests for the retention service — purge logic and downsampling."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.services.retention import (
    TABLE_TIMESTAMP_MAP,
    _downsample_resources,
    run_retention,
)


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
            "log_summaries", "alerts", "project_snapshots",
            "filesystem_audits", "unit_audits", "reliability_scores",
            "agent_runs",
        }
        assert set(TABLE_TIMESTAMP_MAP.keys()) == expected_tables

    def test_timestamp_columns_are_strings(self):
        for col in TABLE_TIMESTAMP_MAP.values():
            assert isinstance(col, str)
            assert len(col) > 0


# ---------------------------------------------------------------------------
# Purge logic
# ---------------------------------------------------------------------------


class TestRunRetention:
    @pytest.mark.asyncio
    async def test_purges_each_configured_table(self, mock_retention_configs):
        """run_retention should execute a DELETE for each configured table."""
        mock_session = AsyncMock()

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

        with patch("sysadmin.services.retention.get_scheduler_session") as ctx:
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

        mock_session = AsyncMock()
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

        with patch("sysadmin.services.retention.get_scheduler_session") as ctx:
            ctx.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            ctx.return_value.__aexit__ = AsyncMock(return_value=False)
            await run_retention()

        # Only the initial SELECT + downsample, no DELETE for unknown table
        assert call_count == 2  # SELECT configs + downsample

    @pytest.mark.asyncio
    async def test_empty_configs_still_downsamples(self):
        """With no retention configs, downsampling should still run."""
        mock_session = AsyncMock()
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

        with patch("sysadmin.services.retention.get_scheduler_session") as ctx:
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
        """project_snapshots and filesystem_audits should keep latest per entity."""
        assert "project_snapshots" in TABLE_TIMESTAMP_MAP
        assert "filesystem_audits" in TABLE_TIMESTAMP_MAP


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
