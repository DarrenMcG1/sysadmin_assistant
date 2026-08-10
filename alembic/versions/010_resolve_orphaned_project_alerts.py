"""Resolve the project-organiser alert backlog left by the missing resolve path.

``ProjectOrganiserAgent`` raised a health alert on every six-hourly scan
and never resolved one, because it never called anything that could.  By
2026-08-07 the audit counted **1,664 unresolved rows**, 326 of them
sharing a single title.  None of them would ever have expired: retention
purges resolved alerts only, so the table's floor was permanent and
rising.

The code fix (``_resolve_recovered``) closes alerts a scan does not
re-raise.  It cannot touch rows that were already there — a project still
under threshold today has its historic duplicates re-raised, not
recovered — so without this migration the fix would leave the 1,664 as a
permanent floor and merely stop it growing.  SNAG-PROJ-004 exists
precisely to stop that being shipped by accident.

**Resolved, not deleted.** The rows are real history: they record that
the organiser judged those projects unhealthy at those times, and the
retention policy is the thing that owns removal.  Marking them resolved
hands them to the existing 30-day purge instead of routing around it, and
keeps ``resolved_at`` honest about when the judgement stopped applying.

``resolved_at`` is set to *now* rather than to ``created_at``.  The
alerts were open until this migration ran; backdating would invent a
resolution that never happened and would make the whole backlog
instantly purgeable, destroying the history this migration chose not to
delete.

Only ``agent = 'project_organiser'`` rows matching the health-alert
title are touched.  The log aggregator's 547,882 unresolved rows are a
different defect (SNAG-AGENT-002) with a different cause, and sweeping
them up here would hide it.

Irreversible by intent: see ``downgrade``.

Revision ID: 010
Revises: 009
Create Date: 2026-08-10
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

# Matches sysadmin.projects.agent._ALERT_TITLE_LIKE.  Duplicated rather
# than imported: a migration must keep meaning what it meant on the day
# it ran, and importing application code would let a later rename
# silently change what this already-applied migration claims to have done.
TITLE_LIKE = "Project % health critical"


def upgrade() -> None:
    result = op.get_bind().execute(
        sa.text(
            f"""
            UPDATE {SCHEMA}.alerts
               SET resolved = true,
                   resolved_at = now()
             WHERE agent = 'project_organiser'
               AND resolved = false
               AND title LIKE :title_like
            """
        ),
        {"title_like": TITLE_LIKE},
    )
    print(f"  resolved {result.rowcount} orphaned project_organiser alerts")


def downgrade() -> None:
    """Deliberately a no-op.

    Reopening the rows is possible only by guessing which of them this
    migration closed — ``resolved_at`` cannot distinguish them from
    alerts the agent resolved legitimately in the same window once the
    fix is live.  A downgrade that reopened *all* project-organiser
    alerts would be a worse lie than doing nothing, so this states its
    inaction rather than pretending to be reversible.
    """
