"""Resource snapshots — CPU, RAM, disk, GPU."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class ResourceSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "resource_snapshots"

    cpu_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    ram_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    swap_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    swap_total_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_usage: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    gpu_usage: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    load_avg_1m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    load_avg_5m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    load_avg_15m: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        Index("idx_resource_snapshots_time", recorded_at.desc()),
    )
