"""Weekly LLM-narrated project portfolio reviews."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.models.base import Base, UUIDPrimaryKeyMixin


class ProjectReview(UUIDPrimaryKeyMixin, Base):
    """One generated portfolio review.

    ``llm_used`` is False when llama-server was unavailable and the
    narrative is the deterministic data digest instead — the review still
    exists, it just isn't prose.  ``stats`` keeps the structured inputs
    (per-project scores, deltas, top actions) so the narrative stays
    auditable against the data it was written from.
    """

    __tablename__ = "project_reviews"

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("idx_project_reviews_generated", generated_at.desc()),
    )
