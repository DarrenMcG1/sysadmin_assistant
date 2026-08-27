"""Index this agent's open alerts, so one family's pile-up is not paid by all.

Session 105, ``SNAG-AGENT-007``.  Every agent asks the same question on
every run — *which of my alerts are still open?* — and ``alerts`` carried
only ``idx_alerts_active`` (``created_at`` where not resolved), which
bounds that read by the **whole** open set rather than by the asking
agent's share of it.

**The half this migration is not.**  The same sitting found that no
reader could reach either index at all: ``Alert.resolved.is_(False)``
compiles to ``resolved IS false`` while both partial predicates say
``resolved = FALSE``, and PostgreSQL matches a partial index
structurally.  Driven against the live table with 100,000 open
``log_aggregator`` rows inserted in a rolled-back transaction, this index
present and the old spelling unchanged, ``SysAdminAgent._active_alerts``
still took a parallel sequential scan: **41,644 buffers, 31.4 ms**.  So
the code change in :func:`sysadmin.core.models.alert.unresolved` is the
load-bearing half and this index alone would have been a no-op — worth
recording, because the obvious reading of a performance snag is that the
database is missing something.

**What it buys once the spelling is fixed**, measured on the same storm:
a bitmap scan over 100,001 index entries returning zero rows (1,935
buffers, 6.7 ms) becomes an index scan of **2 buffers, 0.02 ms**.  The
storm is not hypothetical — ``SNAG-AGENT-005`` reached 598,091
unresolved rows in one family, and this table still holds 667k rows.

**``agent`` alone, not ``(agent, created_at)``.**  No caller of the open
set orders it; the one caller that orders by ``created_at`` wants every
agent's rows and is already served by the index beside this one.

**Partial, so it costs almost nothing.**  It indexes open rows only —
one row on this box at the time of writing — and every insert into
``alerts`` is an open row, which is the write path already paying for
``idx_alerts_active``.

``IF NOT EXISTS`` is deliberately absent: a name collision here means
something outside Alembic created it, which the operator needs to be
told rather than have silently adopted.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "alerts"
INDEX = "idx_alerts_open_by_agent"


def upgrade() -> None:
    op.create_index(
        INDEX,
        TABLE,
        ["agent"],
        unique=False,
        schema=SCHEMA,
        postgresql_where=sa.text("resolved = FALSE"),
    )


def downgrade() -> None:
    op.drop_index(INDEX, table_name=TABLE, schema=SCHEMA)
