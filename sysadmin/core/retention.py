"""Data retention service — purges old rows per table configuration.

Runs as a daily cron job (03:00). Reads retention_config table to
determine how long to keep data in each table.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update

from sysadmin.core.database import get_scheduler_session
from sysadmin.core.models.retention_config import RetentionConfig

logger = logging.getLogger(__name__)

# Map table names to their timestamp column for retention.
#
# A table absent from here is silently skipped, and a table present here
# but absent from the ``retention_config`` *table* is never visited at
# all — the loop below iterates config rows, not this map. Both halves
# are needed, which is how ``project_reviews`` grew unbounded from
# migration 004 and ``unit_audits`` from 006: each had one half.
TABLE_TIMESTAMP_MAP = {
    "service_health": "checked_at",
    "resource_snapshots": "recorded_at",
    "log_entries": "ingested_at",
    "log_summaries": "created_at",
    "alerts": "created_at",
    "project_snapshots": "scanned_at",
    "filesystem_audits": "scanned_at",
    "unit_audits": "scanned_at",
    "reliability_scores": "computed_at",
    "agent_runs": "started_at",
    "project_reviews": "generated_at",
    "disk_reviews": "generated_at",
}

# Tables whose newest row per entity survives the purge regardless of age.
# The value is the SQL expression identifying the entity.
#
# ``true`` means "the whole table is one entity" — the review tables hold
# an estate-wide narrative with no per-entity dimension, so this keeps
# exactly the latest one. Without it a portfolio left unreviewed for
# longer than its window would purge its last review and make
# ``GET /api/projects/review`` start 404ing, which reads to a consumer as
# "no review has ever been generated" rather than "none lately".
KEEP_LATEST_PER = {
    "project_snapshots": "project_name",
    # Keep the newest score per service, so a service that stopped being
    # checked still shows its last verdict rather than silently vanishing
    # from the history.
    "reliability_scores": "service_name",
    # No per-entity dimension worth keeping history for — a sweep covers
    # the whole estate — so the "entity" is the directory pair, which
    # keeps the latest sweep.
    "unit_audits": "system_unit_dir",
    "filesystem_audits": "scan_root",
    "project_reviews": "true",
    "disk_reviews": "true",
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
            # Keep latest per entity for snapshot and review tables
            elif table_name in KEEP_LATEST_PER:
                entity_col = KEEP_LATEST_PER[table_name]
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
