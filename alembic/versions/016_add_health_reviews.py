"""Add health_reviews — the weekly system-health narrative's table (Session 25, Tier 3).

A **third** review table rather than a discriminator column on an
existing one, which is the call Session 24 made when it added
``disk_reviews`` and Session 27 repeated when it added ``log_reviews``:
the reviews answer different questions from different sources, and
separate tables mean no migration can disturb another's rows.

**It does not resurrect ``project_reviews``.**  Session 25's written
plan for this tier said it would "reuse the ``project_reviews`` table
design".  That table left with the projects domain on 2026-08-13
(ADR-0005), was frozen, and was dropped by migration 014 on 2026-08-24
after estate-manager's copy was verified a superset.  A table is
destroyed once; this creates a new one rather than reviving a dropped
name, and what is actually reused is the *shape* the two surviving
mirrors carry.

``confidence`` is a column rather than a key inside ``stats`` for
``log_reviews``' reason, sharpened: every figure in this review compares
two windows, and the two windows on this box were observed at 16.5 % and
96.8 % of expected agent runs.  A consumer decides whether to show the
review on that, so it must be as reachable as the prose.

Revision ID: 016
Revises: 015
Create Date: 2026-08-25
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

#: 365 days, migration 011's rule for a review table: a weekly narrative
#: kept for 30 days is four rows, too few to see a trend.
#:
#: A module-level ``int`` interpolated into the statement rather than
#: bound, migration 013's fix for migration 011's offline-mode defect —
#: ``alembic upgrade --sql`` does not bind parameters, so a bindparam
#: renders as ``VALUES ('health_reviews', NULL)``, a policy row with a
#: NULL window that ``run_retention`` reads as no purge at all.
RETENTION_DAYS = 365


def upgrade() -> None:
    op.create_table(
        "health_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
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
            "llm_used", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False
        ),
        sa.Column("model_used", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_health_reviews_generated",
        "health_reviews",
        [sa.text("generated_at DESC")],
        schema=SCHEMA,
    )

    # Both halves or it is never purged, and the two halves fail in
    # opposite directions: a config row the map cannot resolve is
    # *silent*, a map entry for a missing table is loud.  See
    # ``sysadmin/core/retention.py`` for the other half.
    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.retention_config (table_name, retention_days)
            VALUES ('health_reviews', {int(RETENTION_DAYS)})
            ON CONFLICT (table_name) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.retention_config WHERE table_name = 'health_reviews'"
        )
    )
    op.drop_index("idx_health_reviews_generated", "health_reviews", schema=SCHEMA)
    op.drop_table("health_reviews", schema=SCHEMA)
