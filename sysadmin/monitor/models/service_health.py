"""Service health check results."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class ServiceHealth(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "service_health"

    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        # 'error' means the *check* failed (misconfigured, or systemctl
        # could not be queried) — distinct from 'critical'/'unreachable',
        # which are claims about the service itself. See migration 003.
        CheckConstraint(
            "status IN ('ok', 'degraded', 'warning', 'critical', "
            "'unreachable', 'error')",
            name="chk_health_status",
        ),
        Index("idx_service_health_name_time", "service_name", checked_at.desc()),
    )
