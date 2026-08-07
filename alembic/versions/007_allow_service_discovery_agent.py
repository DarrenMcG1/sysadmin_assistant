"""Allow ``service_discovery`` in the alerts agent CHECK constraint.

``sysadmin.alerts`` enumerates the agents allowed to raise an alert.  The
constraint has listed four since 001, so the Session 26 agent's first
live run was rejected by the database with a ``CheckViolationError`` —
after the scan had already succeeded.

Kept as a whitelist rather than dropped.  It is doing real work: an agent
name typo would otherwise create alerts nobody ever queries, and this
failed loudly at the first attempt, which is the behaviour we want.  The
cost is that adding an agent is a two-part change — Python wiring *and*
a migration — which nothing in the codebase said out loud until now.

Revision ID: 007
Revises: 006
Create Date: 2026-08-07
"""
from collections.abc import Sequence

from alembic import op

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
CONSTRAINT = "chk_alert_agent"

AGENTS = (
    "sysadmin",
    "project_organiser",
    "file_organiser",
    "log_aggregator",
    "service_discovery",
)
PREVIOUS_AGENTS = AGENTS[:-1]


def _condition(agents: Sequence[str]) -> str:
    listed = ", ".join(f"'{agent}'" for agent in agents)
    return f"agent IN ({listed})"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, "alerts", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT, "alerts", _condition(AGENTS), schema=SCHEMA
    )


def downgrade() -> None:
    # Any service_discovery alerts must go first or the narrower
    # constraint cannot be validated against the existing rows.
    op.execute(
        f"DELETE FROM {SCHEMA}.alerts WHERE agent = 'service_discovery'"
    )
    op.drop_constraint(CONSTRAINT, "alerts", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT, "alerts", _condition(PREVIOUS_AGENTS), schema=SCHEMA
    )
