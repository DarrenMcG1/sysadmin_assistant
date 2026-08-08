"""Allow 'skipped' as a service_health status.

services.yaml can declare a service that is deliberately not checked:
``kind: static`` and ``kind: oneshot`` are inactive between invocations by
design, and ``monitor: false`` says so outright. None of the existing
statuses fits. 'critical' and 'unreachable' are claims about the service,
'error' means the check itself failed (migration 003), and 'ok' would be a
lie about a service nobody looked at.

Recording nothing was the alternative and is worse: the service would
vanish from ``/api/sysadmin/status`` and the tray grid that renders it,
and from reliability scoring — where "configured but never checked" is
deliberately scored at low confidence rather than omitted, because an
absence reads as forgotten rather than as decided.

Widening the constraint is additive and cannot invalidate existing rows.

Revision ID: 009
Revises: 008
Create Date: 2026-08-08
"""
from collections.abc import Sequence

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "sysadmin"
TABLE = "service_health"
CONSTRAINT = "chk_health_status"

OLD_STATUSES = "'ok', 'degraded', 'warning', 'critical', 'unreachable', 'error'"
NEW_STATUSES = f"{OLD_STATUSES}, 'skipped'"


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
    op.execute(
        f"DELETE FROM {SCHEMA}.{TABLE} WHERE status = 'skipped'"  # noqa: S608
    )
    _replace_constraint(OLD_STATUSES)
