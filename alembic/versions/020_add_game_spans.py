"""Add game_spans and game_focus, and admit the ``game_detector`` agent.

ADR-0016, first half (Session 370).  Alfred asked for the spans in which
a game was running (estate message ``4dc2b8bc``) and nothing on the box
recorded processes.  :class:`~sysadmin.games.agent.GameDetectorAgent`
polls every 60 s and writes here.

**One row per unbroken run of polls**, never merged: Alfred's merge is
Alfred's reading of *Downtime* (ADR-0016 §5).  ``ended_at`` is copied
from ``last_seen_at`` when a poll stops seeing the game, never stamped
with the poll that noticed, so a span is never over-counted by up to a
poll interval.

**``game_focus.state`` is a column ADR-0016 §4 does not list, and §3
needs it.**  §3 says a stretch where the focus probe failed carries
``focus_known: false`` and is never read as unfocused, and §4's three
columns have nowhere to record that.  So a focus row is either
``focused`` or ``unknown``; an unfocused stretch has no row.  The
alternative, a boolean ``known``, makes ``TRUE`` mean "focused" by
convention only.

**No index on the span timestamps.**  The population is gaming
sessions — a handful a day, about 30 days kept — so the route's overlap
query and the nightly purge scan a few hundred rows.  ``span_id`` is
indexed because every focus read joins on it.

Retention lands here with its table, migration 011's rule: both halves
or it is never purged.  Only ``game_spans`` gets a row; ``game_focus``
goes with its span by ``ON DELETE CASCADE``, so a focus stretch can
never outlive the span it describes.

The agent whitelist widens add-only, as in migrations 007 and 012.

Revision ID: 020
Revises: 019
Create Date: 2026-10-15
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "020"
down_revision: str | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
SPANS = "game_spans"
FOCUS = "game_focus"
CONSTRAINT = "chk_alert_agent"

#: Interpolated, never bound — migration 013's fix for offline mode,
#: where a bindparam renders as NULL and NULL reads as "never purge".
RETENTION_DAYS = 30

AGENTS = (
    "sysadmin",
    "project_organiser",
    "file_organiser",
    "log_aggregator",
    "service_discovery",
    "estate_judge",
    "game_detector",
)
PREVIOUS_AGENTS = AGENTS[:-1]


def _condition(agents: Sequence[str]) -> str:
    listed = ", ".join(f"'{agent}'" for agent in agents)
    return f"agent IN ({listed})"


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def upgrade() -> None:
    op.create_table(
        SPANS,
        _uuid_pk(),
        sa.Column("game", sa.String(length=255), nullable=False),
        sa.Column("matched_by", sa.String(length=20), nullable=False),
        sa.Column("appid", sa.Integer(), nullable=True),
        sa.Column("executable", sa.String(length=255), nullable=True),
        sa.Column("pid", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(matched_by = 'steam_appid' AND appid IS NOT NULL)"
            " OR (matched_by = 'executable' AND executable IS NOT NULL)",
            name="chk_game_span_identity",
        ),
        schema=SCHEMA,
    )
    op.create_table(
        FOCUS,
        _uuid_pk(),
        sa.Column(
            "span_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(f"{SCHEMA}.{SPANS}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=10), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('focused', 'unknown')", name="chk_game_focus_state"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_game_focus_span", FOCUS, ["span_id"], schema=SCHEMA)

    op.get_bind().execute(
        sa.text(
            f"""
            INSERT INTO {SCHEMA}.retention_config (table_name, retention_days)
            VALUES ('{SPANS}', {int(RETENTION_DAYS)})
            ON CONFLICT (table_name) DO NOTHING
            """
        )
    )

    op.drop_constraint(CONSTRAINT, "alerts", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT, "alerts", _condition(AGENTS), schema=SCHEMA
    )


def downgrade() -> None:
    op.execute(f"DELETE FROM {SCHEMA}.alerts WHERE agent = 'game_detector'")
    op.drop_constraint(CONSTRAINT, "alerts", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT, "alerts", _condition(PREVIOUS_AGENTS), schema=SCHEMA
    )
    op.get_bind().execute(
        sa.text(
            f"DELETE FROM {SCHEMA}.retention_config WHERE table_name = '{SPANS}'"
        )
    )
    op.drop_index("idx_game_focus_span", table_name=FOCUS, schema=SCHEMA)
    op.drop_table(FOCUS, schema=SCHEMA)
    op.drop_table(SPANS, schema=SCHEMA)
