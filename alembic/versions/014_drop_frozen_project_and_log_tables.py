"""Drop the three frozen tables — project_snapshots, project_reviews, log_summaries.

ADR-0005 names this as its follow-up and migration 013 states the rule it
turns on: *"a table is destroyed once."*  Three tables have had no writer
for eleven days or longer, and four mechanisms still carry each of them —
a ``retention_config`` row, a ``TABLE_TIMESTAMP_MAP`` entry, an exclusion
in ``sysadmin/metadata.py`` (for two of the three) and, for the third, a
mapped model.  Carrying a table costs a nightly purge, a line in every
count of the schema, and a standing instruction to autogenerate not to
look at it.

**What is actually destroyed, counted before the drop was written.**

===================  ======  ===================================
table                 rows   last written
===================  ======  ===================================
project_snapshots     3,447  2026-08-13 07:35:03  (ADR-0005)
project_reviews           4  2026-08-04 22:14:24  (ADR-0005)
log_summaries             1  2026-07-24 13:47:09  (Session 69)
===================  ======  ===================================

**Only the third row is unique, and it is one row describing 29 seconds.**
The other two were copied to estate-manager when the domain left, and the
copy is a *superset* rather than a mirror.  Compared by hand on
2026-08-24, key ``(project_name, scanned_at)``: the estate holds 4,155
snapshots reaching back to 2026-05-10 against this schema's 3,447 from
2026-05-20, and **3,421 of these 3,447 rows exist there verbatim**.  The
26 that do not are a single farewell sweep — one row per project, all
stamped ``07:35:03.803907+01`` on handover day — and the estate's own
first scan lands at ``07:35:46``, **43 seconds later**.  ``project_reviews``
is the same shape: 6 rows there against 4 here, agreeing to the
microsecond on the oldest.  ``log_summaries`` is superseded rather than
copied — migration 013 records why its shape could not be carried
forward, and ``log_reviews`` has answered the same question since
2026-08-24 07:54.

**That comparison is not repeated at runtime, and must not be.**  Reading
the estate's database from this process is the first estate rule
("no application reads or writes another application's database"); it was
done once, from a shell, by a human deciding whether to destroy data, and
the finding is recorded here instead of being re-derived.

**The drop is unobstructed, also measured.**  The ``sysadmin`` schema
holds no foreign keys at all and no view depends on any of the three, so
these are three independent ``DROP TABLE``s and not the head of a graph.

**``downgrade()`` restores the schema and cannot restore the rows.**  That
asymmetry is the reason a drop migration is written last rather than
first, and it is stated here rather than left for a reader to discover:
downgrading gives back three empty tables and their retention policies,
which is enough for ``alembic upgrade``/``downgrade`` to round-trip and
for the drift guard to pass, and is not a backup.

**The names are interpolated, never bound** — migration 013's rule, for
its reason.  ``alembic upgrade --sql`` does not bind parameters, so a
``WHERE table_name = :name`` renders as ``= NULL`` and deletes nothing,
leaving the file meaning two different things depending on how it is run
with only one of them ever exercised.  Every value below is a literal in
this module, so there is nothing from outside to inject and one rendering
serves both modes.

Revision ID: 014
Revises: 013
Create Date: 2026-08-24
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"

#: The tables, with the retention window each carried, so ``downgrade``
#: restores the policy rows it removed rather than a plausible guess at
#: them.  90 days is the check-data window; 365 is migration 011's rule
#: for a review table, where 30 days is four rows and too few to trend.
DROPPED = (
    ("project_snapshots", 90),
    ("project_reviews", 365),
    ("log_summaries", 90),
)


def upgrade() -> None:
    bind = op.get_bind()

    # The policy row first.  A ``retention_config`` row naming a table
    # that does not exist is *silently* skipped by ``run_retention`` —
    # the loop iterates config rows and looks each up in
    # ``TABLE_TIMESTAMP_MAP`` — so leaving one behind produces no error
    # and no purge, which is the dead-config shape rather than a fault.
    # The map entry is the loud half and goes with this migration, in
    # ``sysadmin/core/retention.py``.
    for table_name, _days in DROPPED:
        bind.execute(
            sa.text(
                f"DELETE FROM {SCHEMA}.retention_config "
                f"WHERE table_name = '{table_name}'"
            )
        )

    # Their indexes go with them; no other object depends on any of the
    # three, verified against ``pg_constraint`` and ``pg_depend`` before
    # this was written.
    for table_name, _days in DROPPED:
        op.drop_table(table_name, schema=SCHEMA)


def downgrade() -> None:
    """Recreate the schema.  The rows are gone; see the module docstring."""
    op.create_table(
        "project_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_name", sa.String(200), nullable=False),
        sa.Column("project_path", sa.Text(), nullable=False),
        sa.Column("health_score", sa.Integer(), nullable=False),
        sa.Column("last_commit_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("branch_count", sa.Integer(), nullable=True),
        sa.Column("stale_branch_count", sa.Integer(), nullable=True),
        sa.Column("todo_count", sa.Integer(), nullable=True),
        sa.Column("fixme_count", sa.Integer(), nullable=True),
        sa.Column("has_readme", sa.Boolean(), nullable=True),
        sa.Column("has_claude_md", sa.Boolean(), nullable=True),
        sa.Column("total_size_mb", sa.Integer(), nullable=True),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "scanned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_project_snapshots_name_time",
        "project_snapshots",
        ["project_name", sa.text("scanned_at DESC")],
        schema=SCHEMA,
    )

    op.create_table(
        "project_reviews",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column(
            "llm_used",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "stats",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_project_reviews_generated",
        "project_reviews",
        [sa.text("generated_at DESC")],
        schema=SCHEMA,
    )

    # No index: it had none live, and migration 001 gave it none.
    op.create_table(
        "log_summaries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("entry_count", sa.Integer(), nullable=True),
        sa.Column("error_count", sa.Integer(), nullable=True),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )

    bind = op.get_bind()
    for table_name, days in DROPPED:
        bind.execute(
            sa.text(
                f"INSERT INTO {SCHEMA}.retention_config (table_name, retention_days) "
                f"VALUES ('{table_name}', {days}) "
                f"ON CONFLICT (table_name) DO NOTHING"
            )
        )
