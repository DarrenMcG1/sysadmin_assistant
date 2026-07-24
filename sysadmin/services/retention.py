"""Data retention service — purges old rows per table configuration.

Runs as a daily cron job (03:00). Reads retention_config table to
determine how long to keep data in each table.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update

from sysadmin.database import get_scheduler_session
from sysadmin.models.retention_config import RetentionConfig

logger = logging.getLogger(__name__)

# Map table names to their timestamp column for retention
TABLE_TIMESTAMP_MAP = {
    "service_health": "checked_at",
    "resource_snapshots": "recorded_at",
    "log_entries": "ingested_at",
    "log_summaries": "created_at",
    "alerts": "created_at",
    "project_snapshots": "scanned_at",
    "filesystem_audits": "scanned_at",
    "agent_runs": "started_at",
}


async def run_retention() -> None:
    """Purge old data according to retention_config. Called by scheduler."""
    async with get_scheduler_session() as session:
        # Read retention config
        result = await session.execute(select(RetentionConfig))
        configs = result.scalars().all()

        total_deleted = 0

        for config in configs:
            table_name = config.table_name
            ts_col = TABLE_TIMESTAMP_MAP.get(table_name)
            if not ts_col:
                continue

            cutoff = datetime.now(UTC) - timedelta(days=config.retention_days)

            # Special handling for alerts — only purge resolved ones
            if table_name == "alerts":
                stmt = text(
                    f"DELETE FROM sysadmin.{table_name} "
                    f"WHERE {ts_col} < :cutoff AND resolved = TRUE"
                )
            # Keep latest per entity for snapshot tables
            elif table_name in ("project_snapshots", "filesystem_audits"):
                # Delete old rows but keep the most recent per entity
                if table_name == "project_snapshots":
                    entity_col = "project_name"
                else:
                    entity_col = "scan_root"

                stmt = text(
                    f"DELETE FROM sysadmin.{table_name} "
                    f"WHERE {ts_col} < :cutoff "
                    f"AND id NOT IN ("
                    f"  SELECT DISTINCT ON ({entity_col}) id "
                    f"  FROM sysadmin.{table_name} "
                    f"  ORDER BY {entity_col}, {ts_col} DESC"
                    f")"
                )
            else:
                stmt = text(
                    f"DELETE FROM sysadmin.{table_name} "
                    f"WHERE {ts_col} < :cutoff"
                )

            result = await session.execute(stmt, {"cutoff": cutoff})
            # DML executes return a CursorResult at runtime, which has rowcount
            deleted = result.rowcount  # type: ignore[attr-defined]
            total_deleted += deleted

            if deleted > 0:
                logger.info(
                    "retention_purged",
                    extra={
                        "table": table_name,
                        "deleted": deleted,
                        "cutoff": cutoff.isoformat(),
                    },
                )

            # Update last_purged_at
            await session.execute(
                update(RetentionConfig)
                .where(RetentionConfig.table_name == table_name)
                .values(last_purged_at=datetime.now(UTC))
            )

        # Downsample resource_snapshots (hourly after 7 days)
        await _downsample_resources(session)

        logger.info("retention_run_complete", extra={"total_deleted": total_deleted})


async def _downsample_resources(session) -> None:
    """Downsample resource_snapshots older than 7 days to hourly averages.

    Strategy: for each hour block, keep only the row closest to the hour mark,
    delete the rest.
    """
    cutoff = datetime.now(UTC) - timedelta(days=7)
    # This is a simplification — delete duplicates within the same hour
    # keeping the one with the smallest minute value (closest to hour boundary)
    stmt = text("""
        DELETE FROM sysadmin.resource_snapshots
        WHERE recorded_at < :cutoff
        AND id NOT IN (
            SELECT DISTINCT ON (date_trunc('hour', recorded_at)) id
            FROM sysadmin.resource_snapshots
            WHERE recorded_at < :cutoff
            ORDER BY date_trunc('hour', recorded_at), recorded_at
        )
    """)

    result = await session.execute(stmt, {"cutoff": cutoff})
    if result.rowcount > 0:
        logger.info(
            "resource_snapshots_downsampled",
            extra={"deleted": result.rowcount},
        )
