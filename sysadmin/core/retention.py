"""Data retention service — purges old rows per table configuration.

Runs as a daily cron job (03:00). Reads retention_config table to
determine how long to keep data in each table.
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update
from sqlalchemy.exc import SQLAlchemyError

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
    "log_reviews": "generated_at",
    "alerts": "created_at",
    "project_snapshots": "scanned_at",
    "filesystem_audits": "scanned_at",
    "unit_audits": "scanned_at",
    "reliability_scores": "computed_at",
    "agent_runs": "started_at",
    "project_reviews": "generated_at",
    "disk_reviews": "generated_at",
}

#: The entity for a table with no per-entity dimension: the whole table
#: is one entity, so exactly one row survives.
#:
#: It is a **sentinel taking its own branch**, not a SQL expression, and
#: that is the whole point.  It used to be the literal string ``"true"``,
#: spliced into ``SELECT DISTINCT ON (true) … ORDER BY true`` — which
#: PostgreSQL rejects, because a bare constant in ``ORDER BY`` is read as
#: an ordinal position and ``true`` is not an integer.  Parenthesising
#: does not help; the parser strips it.  See :func:`purge_statement`.
WHOLE_TABLE = None

# Tables whose newest row per entity survives the purge regardless of age.
# The value is the SQL expression identifying the entity, or
# :data:`WHOLE_TABLE`.
#
# The review tables hold an estate-wide narrative with no per-entity
# dimension, so :data:`WHOLE_TABLE` keeps exactly the latest one. Without
# it a portfolio left unreviewed for longer than its window would purge
# its last review and make ``GET /api/files/review`` start 404ing, which
# reads to a consumer as "no review has ever been generated" rather than
# "none lately".
KEEP_LATEST_PER: dict[str, str | None] = {
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
    "project_reviews": WHOLE_TABLE,
    "disk_reviews": WHOLE_TABLE,
    "log_reviews": WHOLE_TABLE,
}


def purge_statement(table_name: str, ts_col: str) -> str:
    """Build the DELETE for one table.  Pure, so it can be parsed in a test.

    Extracted from :func:`run_retention` for one reason: the statement it
    used to build for a :data:`WHOLE_TABLE` entity was **invalid SQL**,
    and the suite could not see it.  ``tests/test_retention.py`` mocked
    the session, so every statement was asserted as a *string* and none
    was ever handed to a parser — 1,866 green tests beside a nightly job
    that raised ``non-integer constant in ORDER BY`` every night from
    2026-08-08, aborting the whole transaction and silently rolling back
    six successful purges it had already logged.

    So the guard that matters is not a stricter assertion about this
    text; it is PostgreSQL reading it (``test_purge_statements_parse``).
    Building the string here is what lets that test exist without a
    scheduler, a clock or a row.

    Three shapes:

    ``alerts``
        Resolved rows only.  An open alert is a live fault whatever its
        age, and purging one loses the incident rather than the history.

    A :data:`KEEP_LATEST_PER` table
        The newest row per entity survives regardless of age.  With
        :data:`WHOLE_TABLE` there is no entity to distinguish, so this
        takes the ``ORDER BY … LIMIT 1`` branch rather than a
        ``DISTINCT ON`` over a constant — the construct that broke.
        ``NOT IN`` over an empty subquery is ``TRUE``, so a table with no
        rows at all needs no special case.

    Anything else
        Straight age cutoff.
    """
    if table_name == "alerts":
        return (
            f"DELETE FROM sysadmin.{table_name} "
            f"WHERE {ts_col} < :cutoff AND resolved = TRUE"
        )

    if table_name in KEEP_LATEST_PER:
        entity = KEEP_LATEST_PER[table_name]
        if entity is WHOLE_TABLE:
            keep = (
                f"SELECT id FROM sysadmin.{table_name} "
                f"ORDER BY {ts_col} DESC LIMIT 1"
            )
        else:
            keep = (
                f"SELECT DISTINCT ON ({entity}) id "
                f"FROM sysadmin.{table_name} "
                f"ORDER BY {entity}, {ts_col} DESC"
            )
        return (
            f"DELETE FROM sysadmin.{table_name} "
            f"WHERE {ts_col} < :cutoff AND id NOT IN ({keep})"
        )

    return f"DELETE FROM sysadmin.{table_name} WHERE {ts_col} < :cutoff"


async def run_retention() -> None:
    """Purge old data according to retention_config. Called by scheduler.

    **One savepoint per table, for the reason ``SysAdminAgent._execute``
    has one per service.**  This ran as a single transaction over twelve
    tables, so one rejected statement took the other eleven with it — and
    it did, nightly, from 2026-08-08: ``project_reviews`` raised
    ``non-integer constant in ORDER BY`` (see :func:`purge_statement`),
    the transaction aborted, and every DELETE *and* every
    ``last_purged_at`` update rolled back with it.

    What made it survive nine days is that the failure was **quieter than
    success**.  Each table logs ``retention_purged`` with a rowcount
    before the commit, so the journal carried six lines a night reporting
    175,018 rows deleted from ``log_entries`` — none of which happened.
    The one honest signal was ``last_purged_at`` frozen at 2026-08-08,
    which is a column nobody reads, and the ``scheduler_job_error`` line
    that nothing alerts on (``SNAG-RETENTION-002``).

    So two things change together, and either alone is insufficient: the
    savepoint means a bad table costs only itself, and a table that fails
    keeps its **old** ``last_purged_at`` rather than being stamped as
    done.  That column now means what its name says — the last time this
    table was actually purged — and a stale one is the fault showing.
    ``details``-style naming applies to the summary too: failures are
    **named**, never counted, because which table is stuck decides
    whether it matters.
    """
    async with get_scheduler_session() as session:
        # Read retention config
        result = await session.execute(select(RetentionConfig))
        configs = result.scalars().all()

        total_deleted = 0
        failed: list[str] = []

        for config in configs:
            table_name = config.table_name
            ts_col = TABLE_TIMESTAMP_MAP.get(table_name)
            if not ts_col:
                continue

            cutoff = datetime.now(UTC) - timedelta(days=config.retention_days)
            stmt = text(purge_statement(table_name, ts_col))

            try:
                # Leaving the block flushes, so a rejection surfaces while
                # this table's savepoint is still the innermost one.
                async with session.begin_nested():
                    result = await session.execute(stmt, {"cutoff": cutoff})
                    # DML executes return a CursorResult at runtime, which
                    # has rowcount
                    deleted = result.rowcount  # type: ignore[attr-defined]

                    # Stamped inside the savepoint, so it rolls back with
                    # the delete it records rather than outliving it.
                    await session.execute(
                        update(RetentionConfig)
                        .where(RetentionConfig.table_name == table_name)
                        .values(last_purged_at=datetime.now(UTC))
                    )
            except SQLAlchemyError as exc:
                failed.append(table_name)
                logger.error(
                    "retention_purge_failed",
                    extra={"table": table_name, "error": str(exc)},
                )
                continue

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

        # Downsample resource_snapshots (hourly after 7 days).  Isolated
        # for the same reason: it is the one step with no config row, so a
        # failure here used to discard every purge above it.
        try:
            async with session.begin_nested():
                await _downsample_resources(session)
        except SQLAlchemyError as exc:
            failed.append("resource_snapshots:downsample")
            logger.error(
                "retention_downsample_failed",
                extra={"error": str(exc)},
            )

        logger.info(
            "retention_run_complete",
            extra={"total_deleted": total_deleted, "failed_tables": failed},
        )


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
