"""Align DB nullability and idx_alerts_active with the models.

Migration 001 was hand-written and created several defaulted columns as
nullable, while the models (non-Optional ``Mapped[...]``) declare them
NOT NULL. It also created ``idx_alerts_active`` on ``created_at DESC``
where the model declares ascending order. Surfaced by the Session 13
schema drift guard (tests/test_schema_drift.py).

Revision ID: 002
Revises: 001
Create Date: 2026-07-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

# (table, column, backfill value for any existing NULLs)
NOT_NULL_COLUMNS: list[tuple[str, str, str]] = [
    ("service_health", "details", "'{}'::jsonb"),
    ("resource_snapshots", "disk_usage", "'{}'::jsonb"),
    ("resource_snapshots", "gpu_usage", "'{}'::jsonb"),
    ("alerts", "details", "'{}'::jsonb"),
    ("alerts", "acknowledged", "FALSE"),
    ("alerts", "resolved", "FALSE"),
    ("project_snapshots", "findings", "'{}'::jsonb"),
    ("filesystem_audits", "similar_folders_count", "0"),
    ("filesystem_audits", "misplaced_files_count", "0"),
    ("filesystem_audits", "old_downloads_count", "0"),
    ("filesystem_audits", "large_files_count", "0"),
    ("filesystem_audits", "duplicate_groups_count", "0"),
    ("filesystem_audits", "empty_dirs_count", "0"),
    ("filesystem_audits", "stale_project_dirs_count", "0"),
    ("filesystem_audits", "stale_files_count", "0"),
    ("filesystem_audits", "total_reclaimable_mb", "0"),
    ("filesystem_audits", "findings", "'{}'::jsonb"),
    ("log_entries", "metadata", "'{}'::jsonb"),
    ("log_summaries", "sources", "'{}'::jsonb"),
    ("agent_runs", "findings_count", "0"),
    ("agent_runs", "alerts_raised", "0"),
    ("agent_runs", "details", "'{}'::jsonb"),
]


def upgrade() -> None:
    for table, column, backfill in NOT_NULL_COLUMNS:
        op.execute(
            f'UPDATE {SCHEMA}.{table} SET "{column}" = {backfill} '
            f'WHERE "{column}" IS NULL'
        )
        op.execute(
            f'ALTER TABLE {SCHEMA}.{table} ALTER COLUMN "{column}" SET NOT NULL'
        )

    # idx_alerts_active: 001 created it DESC; the model declares ascending
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.idx_alerts_active")
    op.execute(
        f"CREATE INDEX idx_alerts_active ON {SCHEMA}.alerts (created_at) "
        f"WHERE resolved = FALSE"
    )


def downgrade() -> None:
    for table, column, _ in NOT_NULL_COLUMNS:
        op.execute(
            f'ALTER TABLE {SCHEMA}.{table} ALTER COLUMN "{column}" DROP NOT NULL'
        )

    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.idx_alerts_active")
    op.execute(
        f"CREATE INDEX idx_alerts_active ON {SCHEMA}.alerts (created_at DESC) "
        f"WHERE resolved = FALSE"
    )
