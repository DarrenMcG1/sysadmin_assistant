"""Filesystem audit results from the File Organiser agent."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.models.base import Base, UUIDPrimaryKeyMixin


class FilesystemAudit(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "filesystem_audits"

    scan_root: Mapped[str] = mapped_column(Text, nullable=False)
    similar_folders_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    misplaced_files_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    old_downloads_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    large_files_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    duplicate_groups_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    empty_dirs_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    stale_project_dirs_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    stale_files_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    total_reclaimable_mb: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    findings: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    report_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
