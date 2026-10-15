"""Drop ``idx_alerts_open_by_agent``, which migration 019 made redundant.

Migration 017 added it so that an agent's read of its own open alerts is
bounded by its own rows rather than by the whole open set.  Migration 019
then added ``uq_alerts_open_agent_title`` on ``(agent, title)`` under the
same ``resolved = FALSE`` predicate.  A B-tree serves a lookup on its
leading column, so the newer index answers "this agent's open rows" as
well, and the older one was a second copy paid for on every insert.

**Measured before writing this**, on the live table on 2026-10-15
(650,663 rows, 3 open), in one transaction that was rolled back: 100,000
open ``log_aggregator`` rows inserted, ``SNAG-AGENT-007``'s storm, then
``idx_alerts_open_by_agent`` dropped.  ``sysadmin``'s open-row read, both
as ``id, title`` and as whole rows, took an index scan on
``uq_alerts_open_agent_title``: **4 buffers, 0.013 ms**.  Nothing fell
back to ``idx_alerts_active`` or to a sequential scan.

**The pointer is migration 017's docstring.**  The estate's rule that a
dropped database object leaves a pointer covers a schema or a table that
holds data, and asks for a filing at estate-manager naming where the
content lands.  An index holds no content, so nothing was filed; a
search of this repository for the name finds 017, which says where it
went.

``downgrade`` recreates it exactly as 017 did.

Revision ID: 021
Revises: 020
Create Date: 2026-10-15
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "alerts"
INDEX = "idx_alerts_open_by_agent"


def upgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE, schema=SCHEMA)


def downgrade() -> None:
    op.create_index(
        INDEX,
        TABLE,
        ["agent"],
        unique=False,
        schema=SCHEMA,
        postgresql_where=sa.text("resolved = FALSE"),
    )
