"""Allow 'error' as a service_health status.

``SysAdminAgent._check_service`` has always been able to return "error"
for a check it could not perform (an http service with no url, a systemd
service with no unit), but ``chk_health_status`` never permitted it — the
value was unreachable in practice, so the mismatch stayed dormant.

SNAG-SYSD-001 makes it load-bearing: a systemd *user* unit whose session
bus cannot be reached is now recorded as "error" rather than a false
"critical", because the check failed rather than the service. Widening
the constraint is additive and cannot invalidate existing rows.

Revision ID: 003
Revises: 002
Create Date: 2026-07-24
"""
from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "service_health"
CONSTRAINT = "chk_health_status"

OLD_STATUSES = "'ok', 'degraded', 'warning', 'critical', 'unreachable'"
NEW_STATUSES = f"{OLD_STATUSES}, 'error'"


def _replace_constraint(statuses: str) -> None:
    op.drop_constraint(CONSTRAINT, TABLE, schema=SCHEMA, type_="check")
    op.create_check_constraint(
        CONSTRAINT,
        TABLE,
        f"status IN ({statuses})",
        schema=SCHEMA,
    )


def upgrade() -> None:
    _replace_constraint(NEW_STATUSES)


def downgrade() -> None:
    # Any rows recorded while 'error' was legal would violate the narrower
    # constraint, so retire them first.
    op.execute(
        f"DELETE FROM {SCHEMA}.{TABLE} WHERE status = 'error'"  # noqa: S608
    )
    _replace_constraint(OLD_STATUSES)
