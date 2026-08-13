"""Allow ``estate_judge`` in the alerts agent CHECK constraint.

The judging session (this repository's ADR-0005, estate-manager
ADR-0004 §6): the estate publishes its scan's invariants, the audit's
invariants, the queue's invariants and its computed attention list, and
never acts on any of them.  ``EstateJudgeAgent`` reads all four and
raises the alerts.

The constraint is a whitelist and stays one, for the reason migration
007 records: an agent-name typo would otherwise create rows nobody
queries, and this fails loudly on the first attempt instead.  Migration
007's own docstring is where the four-part cost of adding an agent was
first written down — Python wiring, a config class, this constraint, and
``self_monitor.AGENT_NAMES``.

Note ``project_organiser`` stays listed although the agent left this
repository on 2026-08-13.  The constraint is **add-only**: historical
rows carry retired agent names, and narrowing it would orphan them.

Revision ID: 012
Revises: 011
Create Date: 2026-08-13
"""
from collections.abc import Sequence

from alembic import op

revision: str = "012"
down_revision: str | None = "011"
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
    "estate_judge",
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
    # Any estate_judge alerts must go first or the narrower constraint
    # cannot be validated against the existing rows.
    op.execute(f"DELETE FROM {SCHEMA}.alerts WHERE agent = 'estate_judge'")
    op.drop_constraint(CONSTRAINT, "alerts", schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT, "alerts", _condition(PREVIOUS_AGENTS), schema=SCHEMA
    )
