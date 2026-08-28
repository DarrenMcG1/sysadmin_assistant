"""Add desktop_notifications — the understudy's spoken set, made durable.

Session 115, ``SNAG-TRAY-008``.
:class:`~sysadmin.monitor.desktop.DesktopNotifier` restates a fault it
announced that is still open, and the population of that sweep was
exactly the keys of an in-memory dict.  So the reminder was reachable
only by a process that lived a full ``notifications.desktop
.reminder_hours``.  Measured over 28.26 days: ``sysadmin.service``
started **111 times** at a median uptime of **1.77 h**, and **5 of 110**
lives reached 24 h.  The reminder was therefore structurally unavailable
on 95 % of this daemon's lives — not slow, silent.

**Wall clock in both timestamp columns, which is a change of reading and
not merely of storage.**  The notifier's clock was ``time.monotonic``,
inherited from :class:`~sysadmin.monitor.desktop.TrayPresence`, and no
monotonic value survives a process — nor, on Linux, a suspend, where
``CLOCK_MONOTONIC`` stops.  A 24-hour reminder is precisely about
elapsed human time, so a workstation asleep overnight should be charged
those hours.  ``TrayPresence`` keeps monotonic for its own 180-second
question; the two now differ deliberately.

**Unique on ``title``.**  The title is a fault's identity everywhere else
here, so the write is an upsert and two rows for one fault cannot exist.
No index on the timestamps: the table is bounded by the number of
distinct open faults the daemon has spoken for — one on this box at the
time of writing, and the adopted half is capped at five — so the nightly
purge sequentially scans a handful of rows and an index would be a write
cost on every notification to save nothing.

**Thirty days, and the two halves of the fix are what make that cheap.**
The other retention windows range 30–365 and the review tables take 365
because four rows cannot show a trend.  This table holds no history: a
row is either about a fault that is still open, in which case the sweep
maintains it, or about one that resolved while the daemon was down, in
which case it is dead.  Forgetting a live row costs one re-adoption,
which the same session's adoption half makes automatic — so the window
need only comfortably exceed one reminder interval, and 30 days is 30×
it.  ``log_entries``, ``agent_runs`` and ``service_health`` already sit
there.

Both retention halves land here together, migration 011's rule: a config
row the map cannot resolve is skipped in **silence**, and a map entry for
a table that does not exist raises every night.  See
``sysadmin/core/retention.py``.

Revision ID: 018
Revises: 017
Create Date: 2026-08-28
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "desktop_notifications"

#: A module-level ``int`` interpolated into the statement rather than
#: bound — migration 013's fix for migration 011's offline-mode defect.
#: ``alembic upgrade --sql`` does not bind parameters, so a bindparam
#: renders as ``VALUES ('desktop_notifications', NULL)``: a policy row
#: with a NULL window, which ``run_retention`` reads as no purge at all.
RETENTION_DAYS = 30


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column(
            "episode_started_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("last_spoken_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "reminders_sent",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "adopted", sa.Boolean(), server_default=sa.text("FALSE"), nullable=False
        ),
        sa.UniqueConstraint("title", name=f"uq_{TABLE}_title"),
        schema=SCHEMA,
    )

    # Both halves or it is never purged, and the two fail in opposite
    # directions — the silent one is this.
    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.retention_config (table_name, retention_days)
            VALUES ('{TABLE}', {int(RETENTION_DAYS)})
            ON CONFLICT (table_name) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.retention_config WHERE table_name = '{TABLE}'"
        )
    )
    op.drop_table(TABLE, schema=SCHEMA)
