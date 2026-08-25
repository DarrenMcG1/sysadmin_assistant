"""Record skipped checks beside error checks on reliability_scores.

Session 78.  ``ReliabilityScore`` gained ``skipped_checks`` when
``sysadmin/monitor/reliability.py`` stopped scoring a ``skipped`` health
row as an outage, and this column is the persisted half.

**The defect the field exists to make visible.**  ``services.yaml`` can
declare ``monitor: false`` on a service that is inactive by design —
``venture-chat-large`` is pulled up by ``venture-enrich-nightly`` for the
02:00 drain and stopped by its ``ExecStopPost``; ``sysadmin-tray`` and
``searxng-upstream`` are declared the same way.  The agent writes those
checks as ``skipped``.  ``score_service`` excluded only ``error`` from
its rates, so a ``skipped`` row counted as measured-and-not-``ok`` — an
outage — and all three scored **35** and graded ``failing`` off 307
checks nobody had taken.

It went unnoticed from Session 25 (2026-08-07) because a wrong score is a
number on a page.  ``GET /api/services/actions`` turned each into a
``risk`` recommendation worth 60 recoverable points on its first live
run, which is what made it loud enough to find.

**Why a separate column rather than folding into ``error_checks``.**
Both statuses mean nothing was measured and the difference is *who
decided* — the check failed, or nobody looked by choice — and the
remedies are opposites: an all-``error`` service needs its check fixed
and an all-``skipped`` one is behaving exactly as declared.  One field
holding two claims is ``UnitFinding.enabled``'s trap, which this
repository has now paid for once.

**Nullability.**  ``server_default`` of 0 and ``NOT NULL``, matching
``error_checks`` beside it.  Rows written before today genuinely have no
value for this, and 0 is the honest reading of "this snapshot did not
distinguish them" only because the old code folded skipped rows into
``failed_checks`` rather than dropping them — so the historic totals
still add up, they were simply attributed to the wrong bucket.  The
scores in those rows stay as they were recorded; a migration that
recomputed history would be inventing measurements it never took.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "reliability_scores"
COLUMN = "skipped_checks"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            COLUMN,
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN, schema=SCHEMA)
