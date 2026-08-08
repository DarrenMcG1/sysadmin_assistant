"""Log entries collected by the Log Aggregator agent."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class LogEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "log_entries"

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_line: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default=text("'{}'::jsonb")
    )
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "severity IN ('debug', 'info', 'warning', 'error', 'critical')",
            name="chk_log_severity",
        ),
        Index("idx_log_entries_source_time", "source", logged_at.desc()),
        Index(
            "idx_log_entries_severity",
            "severity",
            logged_at.desc(),
            postgresql_where=text("severity IN ('warning', 'error', 'critical')"),
        ),
    )
