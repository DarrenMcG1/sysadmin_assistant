"""Add unit_audits — systemd unit sweeps from the Service Discovery agent.

Session 26: cross-reference the installed units against the projects on
disk and the units already wired into projects.yaml / config.yaml, both
directions.  A unit that maps to a live project but nothing monitors is
a gap; a unit whose project is gone is already broken.

Its own table rather than a column on ``project_snapshots`` because the
findings are estate-level, not per-project: an orphaned unit belongs to
no live project by definition, and there is no snapshot row to hang it
on.

Every count is a column.  Session 24 established why: ``findings`` is
truncated before storage, so a count summed from it is a lower bound
that reads like a total.

Revision ID: 006
Revises: 005
Create Date: 2026-08-07
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"


def upgrade() -> None:
    op.create_table(
        "unit_audits",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_unit_dir", sa.Text(), nullable=True),
        sa.Column("system_unit_dir", sa.Text(), nullable=True),
        sa.Column(
            "units_scanned", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "units_excluded", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "monitored_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "timers_folded", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "orphaned_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "unmonitored_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "host_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "findings",
            JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        schema=SCHEMA,
    )
    # Every read is "the latest sweep" — the endpoints, the recommendation
    # builder and the retention purge all order by this and take one row.
    op.create_index(
        "idx_unit_audits_scanned",
        "unit_audits",
        [sa.text("scanned_at DESC")],
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_index("idx_unit_audits_scanned", table_name="unit_audits", schema=SCHEMA)
    op.drop_table("unit_audits", schema=SCHEMA)
