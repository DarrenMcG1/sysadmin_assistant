"""Alerts raised by agents."""

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    agent: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    acknowledged: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="chk_alert_severity",
        ),
        # Kept in step with the migrations by hand, and it had drifted:
        # `service_discovery` was added to the database by migration 007
        # in Session 26 and never here, because alembic's autogenerate
        # does not diff CHECK constraints (the blind spot
        # `core/schema_guard.py` records for its own reasons). Nothing
        # broke, since no code path builds this table from metadata —
        # which is also why nothing caught it. `estate_judge` arrives
        # with migration 012.
        CheckConstraint(
            "agent IN ('sysadmin', 'project_organiser', 'file_organiser',"
            " 'log_aggregator', 'service_discovery', 'estate_judge')",
            name="chk_alert_agent",
        ),
        Index("idx_alerts_active", "created_at", postgresql_where=text("resolved = FALSE")),
    )
