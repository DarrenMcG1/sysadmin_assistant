"""Retention policy configuration — controls auto-purge of old data."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base


class RetentionConfig(Base):
    __tablename__ = "retention_config"

    table_name: Mapped[str] = mapped_column(String(100), primary_key=True)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False)
    downsample_after_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    downsample_interval: Mapped[str | None] = mapped_column(String(20), nullable=True)
    last_purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
