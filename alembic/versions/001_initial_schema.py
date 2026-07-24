"""Initial schema — all 9 tables + retention config seed data.

Revision ID: 001
Revises: None
Create Date: 2026-02-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # --- service_health ---
    op.create_table(
        "service_health",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("service_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("response_time_ms", sa.Integer, nullable=True),
        sa.Column("details", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("checked_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "status IN ('ok', 'degraded', 'warning', 'critical', 'unreachable')",
            name="chk_health_status",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_service_health_name_time",
        "service_health",
        ["service_name", sa.text("checked_at DESC")],
        schema=SCHEMA,
    )

    # --- resource_snapshots ---
    op.create_table(
        "resource_snapshots",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("cpu_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("ram_used_mb", sa.Integer, nullable=True),
        sa.Column("ram_total_mb", sa.Integer, nullable=True),
        sa.Column("ram_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("swap_used_mb", sa.Integer, nullable=True),
        sa.Column("swap_total_mb", sa.Integer, nullable=True),
        sa.Column("disk_usage", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("gpu_usage", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("load_avg_1m", sa.Numeric(5, 2), nullable=True),
        sa.Column("load_avg_5m", sa.Numeric(5, 2), nullable=True),
        sa.Column("load_avg_15m", sa.Numeric(5, 2), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_resource_snapshots_time",
        "resource_snapshots",
        [sa.text("recorded_at DESC")],
        schema=SCHEMA,
    )

    # --- alerts ---
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("details", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("acknowledged", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved", sa.Boolean, server_default=sa.text("FALSE")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="chk_alert_severity",
        ),
        sa.CheckConstraint(
            "agent IN ('sysadmin', 'project_organiser', 'file_organiser', 'log_aggregator')",
            name="chk_alert_agent",
        ),
        schema=SCHEMA,
    )
    op.execute(
        f"CREATE INDEX idx_alerts_active ON {SCHEMA}.alerts (created_at DESC) "
        f"WHERE resolved = FALSE"
    )

    # --- project_snapshots ---
    op.create_table(
        "project_snapshots",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("project_path", sa.Text, nullable=False),
        sa.Column("health_score", sa.Integer, nullable=False),
        sa.Column("last_commit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("branch_count", sa.Integer, nullable=True),
        sa.Column("stale_branch_count", sa.Integer, nullable=True),
        sa.Column("todo_count", sa.Integer, nullable=True),
        sa.Column("fixme_count", sa.Integer, nullable=True),
        sa.Column("has_readme", sa.Boolean, nullable=True),
        sa.Column("has_claude_md", sa.Boolean, nullable=True),
        sa.Column("total_size_mb", sa.Integer, nullable=True),
        sa.Column("findings", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_project_snapshots_name_time",
        "project_snapshots",
        ["project_name", sa.text("scanned_at DESC")],
        schema=SCHEMA,
    )

    # --- filesystem_audits ---
    op.create_table(
        "filesystem_audits",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("scan_root", sa.Text, nullable=False),
        sa.Column("similar_folders_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("misplaced_files_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("old_downloads_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("large_files_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("duplicate_groups_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("empty_dirs_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("stale_project_dirs_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("stale_files_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("total_reclaimable_mb", sa.Integer, server_default=sa.text("0")),
        sa.Column("findings", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("report_path", sa.Text, nullable=True),
        sa.Column("scanned_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema=SCHEMA,
    )

    # --- log_entries ---
    op.create_table(
        "log_entries",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("raw_line", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.CheckConstraint(
            "severity IN ('debug', 'info', 'warning', 'error', 'critical')",
            name="chk_log_severity",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_log_entries_source_time",
        "log_entries",
        ["source", sa.text("logged_at DESC")],
        schema=SCHEMA,
    )
    op.execute(
        f"CREATE INDEX idx_log_entries_severity ON {SCHEMA}.log_entries "
        f"(severity, logged_at DESC) WHERE severity IN ('warning', 'error', 'critical')"
    )

    # --- log_summaries ---
    op.create_table(
        "log_summaries",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("entry_count", sa.Integer, nullable=True),
        sa.Column("error_count", sa.Integer, nullable=True),
        sa.Column("sources", JSONB, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        schema=SCHEMA,
    )

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("agent", sa.String(50), nullable=False),
        sa.Column("run_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("duration_seconds", sa.Numeric(10, 2), nullable=True),
        sa.Column("findings_count", sa.Integer, server_default=sa.text("0")),
        sa.Column("alerts_raised", sa.Integer, server_default=sa.text("0")),
        sa.Column("details", JSONB, server_default=sa.text("'{}'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed', 'cancelled')",
            name="chk_run_status",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_agent_runs_agent_time",
        "agent_runs",
        ["agent", sa.text("started_at DESC")],
        schema=SCHEMA,
    )

    # --- retention_config ---
    op.create_table(
        "retention_config",
        sa.Column("table_name", sa.String(100), primary_key=True),
        sa.Column("retention_days", sa.Integer, nullable=False),
        sa.Column("downsample_after_days", sa.Integer, nullable=True),
        sa.Column("downsample_interval", sa.String(20), nullable=True),
        sa.Column("last_purged_at", sa.DateTime(timezone=True), nullable=True),
        schema=SCHEMA,
    )

    # --- Seed retention_config ---
    op.execute(
        f"""
        INSERT INTO {SCHEMA}.retention_config
            (table_name, retention_days, downsample_after_days, downsample_interval)
        VALUES
            ('service_health', 7, NULL, NULL),
            ('resource_snapshots', 30, 7, 'hourly'),
            ('log_entries', 30, NULL, NULL),
            ('log_summaries', 90, NULL, NULL),
            ('alerts', 90, NULL, NULL),
            ('project_snapshots', 90, NULL, NULL),
            ('filesystem_audits', 90, NULL, NULL),
            ('agent_runs', 30, NULL, NULL)
        """
    )


def downgrade() -> None:
    tables = [
        "retention_config", "agent_runs", "log_summaries", "log_entries",
        "filesystem_audits", "project_snapshots", "alerts",
        "resource_snapshots", "service_health",
    ]
    for table in tables:
        op.drop_table(table, schema=SCHEMA)

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
