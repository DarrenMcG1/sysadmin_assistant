"""Weekly LLM-narrated log reviews (Session 27, Tier 3)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class LogReview(UUIDPrimaryKeyMixin, Base):
    """One generated log review.

    A separate table from ``disk_reviews`` and ``project_reviews`` for the
    reason Session 24 gave when it declined to share one: the three
    reviews answer different questions from different sources, and
    keeping them apart means no migration can disturb another's rows.

    It is **not** an extension of ``log_summaries``, which it replaces.
    That table was shaped for a thirty-minute window of raw lines — it
    carries ``entry_count``/``error_count`` and no ``stats``, so the
    inputs a narrative was written from could not be stored beside it.
    Its single row (2026-07-24) summarised **29 seconds** of one storming
    signature and reported ``entry_count = error_count = 100``, both of
    them the query's ``LIMIT`` rather than a measurement.

    ``llm_used`` is False when llama-server was unavailable and the
    narrative is the deterministic digest instead — the review still
    exists, it just is not prose.  ``confidence`` is copied from the
    trend report rather than recomputed: a review generated off a
    truncated window must say so on its own face, because the narrative
    it carries reads exactly the same either way.
    """

    __tablename__ = "log_reviews"

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    #: ``low``/``medium``/``high``, straight from
    #: :class:`~sysadmin.monitor.log_trends.LogTrendReport`.
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    __table_args__ = (Index("idx_log_reviews_generated", generated_at.desc()),)
