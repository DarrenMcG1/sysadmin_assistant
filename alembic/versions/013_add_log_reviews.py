"""Add log_reviews — the weekly log narrative's own table (Session 27, Tier 3).

A third review table rather than a discriminator column on an existing
one, which is the call Session 24 made when it added ``disk_reviews``
beside ``project_reviews``: the reviews answer different questions from
different sources, and separate tables mean no migration can disturb
another's rows.

**It is not an ALTER of ``log_summaries``.** That table belongs to the
producer this release deletes — ``LogAggregatorAgent.summarise()``, which
had no caller anywhere and left exactly one row, written 2026-07-24 over
a **29-second** window with ``entry_count = error_count = 100``, both of
them the query's own ``LIMIT``. Its columns describe that shape
(``period_start``/``period_end``/``entry_count``/``error_count``) and it
has nowhere to keep the inputs a narrative was written from, which the
tier pattern requires. Reusing it would carry a dead design forward for
the sake of avoiding a ``CREATE TABLE``.

``log_summaries`` is therefore left **frozen**, not dropped — the
treatment ADR-0005 gave ``project_snapshots`` and ``project_reviews``
when their producer left. Nothing writes it, its retention row still
thins it, and dropping it together with its model, its metadata entry
and its retention row is a follow-up with its own migration. A table is
destroyed once.

``confidence`` is a column rather than a key inside ``stats`` because a
consumer decides whether to *show* the review on it. A review generated
across a truncated window reads exactly like one that was not, so the
qualifier has to be as reachable as the prose.

Revision ID: 013
Revises: 012
Create Date: 2026-08-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

#: 365 days, migration 011's rule for a review table: a weekly narrative
#: kept for 30 days is four rows, too few to see a trend.
#:
#: **Interpolated rather than bound**, deliberately departing from
#: migration 011, which passes the same value as a bindparam.  Alembic's
#: offline mode (``alembic upgrade --sql``) does not bind parameters, so
#: 011 renders as ``VALUES ('disk_reviews', NULL)`` — a policy row with a
#: NULL window, which ``run_retention`` reads as no purge at all.  Online
#: it binds and is correct, so the file means two different things
#: depending on how it is run and only one of them is ever exercised.
#: This is a module-level ``int`` in this file, so there is no value from
#: outside to inject and one rendering serves both modes.
RETENTION_DAYS = 365


def upgrade() -> None:
    op.create_table(
        "log_reviews",
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
        "idx_log_reviews_generated",
        "log_reviews",
        [sa.text("generated_at DESC")],
        schema=SCHEMA,
    )

    # Both halves or it is never purged: run_retention iterates this
    # table and looks each row up in TABLE_TIMESTAMP_MAP.
    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.retention_config (table_name, retention_days)
            VALUES ('log_reviews', {int(RETENTION_DAYS)})
            ON CONFLICT (table_name) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(f"DELETE FROM {SCHEMA}.retention_config WHERE table_name = 'log_reviews'")
    )
    op.drop_index("idx_log_reviews_generated", "log_reviews", schema=SCHEMA)
    op.drop_table("log_reviews", schema=SCHEMA)
