"""Project health snapshots from the Project Organiser agent."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.models.base import Base, UUIDPrimaryKeyMixin


class ProjectSnapshot(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "project_snapshots"

    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    project_path: Mapped[str] = mapped_column(Text, nullable=False)
    health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    last_commit_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    branch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stale_branch_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    todo_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fixme_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_readme: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    has_claude_md: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    total_size_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    findings: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        Index("idx_project_snapshots_name_time", "project_name", scanned_at.desc()),
    )
