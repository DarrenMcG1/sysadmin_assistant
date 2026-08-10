"""Give project_reviews, disk_reviews and unit_audits a retention policy.

``run_retention`` iterates rows of the ``retention_config`` *table* and
looks each one up in ``TABLE_TIMESTAMP_MAP``. A table needs an entry in
both to be purged, and three tables had at most one:

- ``project_reviews`` (migration 004) — in neither. Four rows today,
  growing one per week, forever.
- ``disk_reviews`` (migration 005) — in neither. Added by the same
  pattern as the above, which is why the audit said to check it.
- ``unit_audits`` (migration 006) — in the map but with no config row,
  so the code that would purge it was never reached. Not in the original
  snag; found while adding the other two.

**Reviews get 365 days, not the 30 that check data gets.** They are
weekly narratives: 30 days keeps four of them, which is too few to see a
trend and makes the table pointless to keep at all. A year is 52 rows of
text — nothing, as storage — and is the shortest window over which
"where was the portfolio last spring" is answerable. Check data is
sampled every few minutes and answers a different question.

``unit_audits`` gets 90 days, matching ``filesystem_audits`` and
``project_snapshots``: it is a periodic sweep of the same kind and there
is no reason for it to be the odd one out.

All three are in ``KEEP_LATEST_PER``, so the newest row survives its
window regardless. A purge that emptied ``project_reviews`` would make
``GET /api/projects/review`` return 404 — which the tray renders as "no
review has ever been generated", not "none recently".

Revision ID: 011
Revises: 010
Create Date: 2026-08-10
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

POLICIES = [
    ("project_reviews", 365),
    ("disk_reviews", 365),
    ("unit_audits", 90),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table_name, days in POLICIES:
        bind.execute(
            sa.text(
                f"""
                INSERT INTO {SCHEMA}.retention_config (table_name, retention_days)
                VALUES (:table_name, :days)
                ON CONFLICT (table_name) DO NOTHING
                """
            ),
            {"table_name": table_name, "days": days},
        )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name, _days in POLICIES:
        bind.execute(
            sa.text(
                f"DELETE FROM {SCHEMA}.retention_config WHERE table_name = :table_name"
            ),
            {"table_name": table_name},
        )
