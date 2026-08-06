"""Weekly LLM-narrated disk reviews."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.models.base import Base, UUIDPrimaryKeyMixin


class DiskReview(UUIDPrimaryKeyMixin, Base):
    """One generated disk review.

    Deliberately a separate table from ``project_reviews`` rather than a
    shared table with a discriminator: the two reviews answer different
    questions from different sources, and keeping them apart means
    neither migration can disturb the other's rows.

    ``llm_used`` is False when llama-server was unavailable and the
    narrative is the deterministic digest instead — the review still
    exists, it just isn't prose.  ``stats`` keeps the structured inputs
    (occupancy delta, audit deltas, per-kind reclaim) so the narrative
    stays auditable against the data it was written from.
    """

    __tablename__ = "disk_reviews"

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("idx_disk_reviews_generated", generated_at.desc()),
    )
