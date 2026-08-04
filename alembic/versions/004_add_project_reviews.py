"""Add project_reviews — weekly LLM-narrated portfolio reviews.

Session 23 (project-manager Tier 3): a weekly job narrates the portfolio
(what moved, what is decaying, what to archive) via llama-server, falling
back to a deterministic digest when inference is unavailable.  Reviews
are kept so the briefing and the tray can show the latest without
re-running inference.

Revision ID: 004
Revises: 003
Create Date: 2026-08-04
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"


def upgrade() -> None:
    op.create_table(
        "project_reviews",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column(
            "llm_used",
            sa.Boolean(),
            server_default=sa.text("FALSE"),
            nullable=False,
        ),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "stats",
            JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_project_reviews_generated",
        "project_reviews",
        [sa.text("generated_at DESC")],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_project_reviews_generated", "project_reviews", schema=SCHEMA)
    op.drop_table("project_reviews", schema=SCHEMA)
