"""Add disk_reviews — weekly LLM-narrated disk reviews.

Session 24 (file-organiser Tier 3): a weekly job narrates the disk (what
grew, what shrank, where the mess is coming from) via llama-server,
falling back to a deterministic digest when inference is unavailable.
Same shape as ``project_reviews`` but a separate table — the two reviews
answer different questions from different sources, so neither migration
should be able to disturb the other's rows.

Revision ID: 005
Revises: 004
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"


def upgrade() -> None:
    op.create_table(
        "disk_reviews",
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
        "idx_disk_reviews_generated",
        "disk_reviews",
        [sa.text("generated_at DESC")],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_disk_reviews_generated", "disk_reviews", schema=SCHEMA)
    op.drop_table("disk_reviews", schema=SCHEMA)
