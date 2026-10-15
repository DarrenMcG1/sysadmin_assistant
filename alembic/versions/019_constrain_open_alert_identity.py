"""One open row per alert, and no flag without its timestamp.

``SNAG-DB-007``, the October design review's R35.  Two rules that only
application code kept until now: every family deduplicates before it
raises, and every writer that sets ``resolved`` or ``acknowledged`` sets
its timestamp in the same statement.  Nothing in the schema backed
either, and ``SNAG-AGENT-005`` (598,091 open rows that could never be
resolved) is what this table looks like when the application's rule
fails.

**The identity is ``(agent, title)``, and it was measured, not chosen.**
Every insert site reads its open rows by exactly that pair before it
writes: the families through ``SysAdminAgent._open_alert_criteria`` and
their equivalents, which compose ``Alert.agent == self.name`` on
:func:`~sysadmin.core.models.alert.unresolved`, and
``record_unit_failure`` by ``agent`` and ``title`` directly.  The one
place ``details['source']`` appears, ``resolve_unit_failures``, narrows
the **resolve**, never the raise, so it is not part of the identity: an
index including it would admit a second open row the raise path refuses.
``title`` alone was rejected because two agents may raise the same title
and nothing in the application stops them, so the index would refuse a
write the code considers legal and fail that agent's run.

Measured on the live table on 2026-10-13 (651,027 rows, 3 open): zero
``(agent, title)`` pairs with two open rows, and, replaying every pair's
history by ``created_at``, zero rows created while an earlier row of the
same pair was still open since 2026-08-14 in any agent.  The 649,686
overlaps before then are the pile-ups ``SNAG-AGENT-004`` and
``SNAG-AGENT-005`` closed.

**An escalation still fits under a non-deferrable index.**
``step_for``'s resolve-and-re-raise marks the quiet row resolved and
inserts the loud one in one flush, and SQLAlchemy's ``save_obj`` emits a
mapper's ``UPDATE`` statements before its ``INSERT`` statements, so the
old row has left the index before the new one arrives.
``tests/test_open_alert_constraints_live.py`` drives that order against
the real index rather than relying on this sentence.

**What changes in behaviour**: a manual run (``spawn_manual_run``, from
``POST /api/sysadmin/scan-all``) is not serialised against the
scheduler's run of the same agent, so two runs can both decide to raise
one new fault.  Until now both inserts landed and the second row stayed
open until a sweep closed it.  Now the second insert waits on the first
transaction and is refused, and that run records a failure.

**The CHECKs are ``flag = (timestamp IS NOT NULL)``**, an equivalence
rather than an implication, because neither direction is legal: a flag
without its timestamp is an alert nobody can date, and a timestamp
without its flag is a row ``unresolved()`` still counts as open.  Both
flags are ``NOT NULL``, so the comparison never yields ``NULL`` and the
CHECK cannot pass by default.  Zero rows violate either on the live
table, and every writer under ``sysadmin/`` sets both columns together.

``idx_alerts_open_by_agent`` (migration 017) is now redundant, since this
index leads on ``agent`` under the same predicate.  It was left in place
here and dropped as its own change by migration 021.

Revision ID: 019
Revises: 018
Create Date: 2026-10-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "alerts"
INDEX = "uq_alerts_open_agent_title"
RESOLVED_CHECK = "chk_alert_resolved_stamped"
ACKNOWLEDGED_CHECK = "chk_alert_acknowledged_stamped"


def upgrade() -> None:
    op.create_index(
        INDEX,
        TABLE,
        ["agent", "title"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("resolved = FALSE"),
    )
    op.create_check_constraint(
        RESOLVED_CHECK,
        TABLE,
        "resolved = (resolved_at IS NOT NULL)",
        schema=SCHEMA,
    )
    op.create_check_constraint(
        ACKNOWLEDGED_CHECK,
        TABLE,
        "acknowledged = (acknowledged_at IS NOT NULL)",
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_constraint(ACKNOWLEDGED_CHECK, TABLE, schema=SCHEMA, type_="check")
    op.drop_constraint(RESOLVED_CHECK, TABLE, schema=SCHEMA, type_="check")
    op.drop_index(INDEX, table_name=TABLE, schema=SCHEMA)
