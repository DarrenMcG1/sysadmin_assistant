"""Add reliability_scores — per-service reliability history.

Session 25, Tier 1.  The project organiser scores repositories and the
file organiser scores the disk; the services this application exists to
watch had no number attached to them.

Its own table rather than a column on ``service_health``: a health check
is one observation, a score is a verdict over a window of them, and
writing the verdict onto every observation row would mean recomputing
and rewriting history on each check.

``GET /api/services/reliability`` does not read this table — it
recomputes from ``service_health`` on every request, so the answer is
never stale and there is no cold-start 404.  These rows exist so the
score becomes trendable (and so Tier 3's weekly review has a delta to
report).

Every measured quantity is a column.  Sessions 24 and 26 established
why: a number buried in JSONB cannot be indexed, constrained or trended.
``deductions`` holds only the attribution prose.

Revision ID: 008
Revises: 007
Create Date: 2026-08-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"


def upgrade() -> None:
    op.create_table(
        "reliability_scores",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("service_name", sa.String(length=100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(length=20), nullable=False),
        # --- what was measured ---
        sa.Column("uptime_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "checks_recorded", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "checks_measured", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "failed_checks", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "error_checks", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "outage_episodes", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("longest_outage_minutes", sa.Numeric(10, 1), nullable=True),
        sa.Column("mean_hours_between_incidents", sa.Numeric(10, 1), nullable=True),
        # --- how far to trust it ---
        sa.Column(
            "checks_expected", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "coverage_percent",
            sa.Numeric(6, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "observed_days",
            sa.Numeric(6, 2),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.String(length=10),
            server_default=sa.text("'high'"),
            nullable=False,
        ),
        sa.Column("confidence_reason", sa.Text(), nullable=True),
        # --- provenance ---
        sa.Column(
            "window_days", sa.Integer(), server_default=sa.text("7"), nullable=False
        ),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "muted", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False
        ),
        sa.Column(
            "waived_points", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "deductions",
            JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="chk_reliability_score_range"),
        sa.CheckConstraint(
            "grade IN ('reliable', 'degraded', 'unreliable', 'failing')",
            name="chk_reliability_grade",
        ),
        sa.CheckConstraint(
            "confidence IN ('high', 'low')", name="chk_reliability_confidence"
        ),
        schema=SCHEMA,
    )
    # Every read is "the latest score for this service", or a trend for
    # one service — both are covered by (service_name, computed_at DESC).
    op.create_index(
        "idx_reliability_scores_service_time",
        "reliability_scores",
        ["service_name", sa.text("computed_at DESC")],
        schema=SCHEMA,
    )

    # Wire the new table into the retention purge. 90 days matches the
    # other derived-verdict tables (project_snapshots, filesystem_audits)
    # rather than service_health's 30: a score is a summary, so keeping it
    # longer than the checks it summarises is the point.
    op.execute(
        sa.text(
            "INSERT INTO sysadmin.retention_config "
            "(table_name, retention_days) VALUES ('reliability_scores', 90) "
            "ON CONFLICT (table_name) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM sysadmin.retention_config "
            "WHERE table_name = 'reliability_scores'"
        )
    )
    op.drop_index(
        "idx_reliability_scores_service_time",
        table_name="reliability_scores",
        schema=SCHEMA,
    )
    op.drop_table("reliability_scores", schema=SCHEMA)
