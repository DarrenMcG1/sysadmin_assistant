"""Weekly LLM-narrated system health reviews (Session 25, Tier 3)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class HealthReview(UUIDPrimaryKeyMixin, Base):
    """One generated system health review.

    The **third** review table, and a separate one for the reason
    Session 24 gave when it declined to share ``project_reviews`` and
    Session 27 gave when it declined to share ``disk_reviews``: the
    reviews answer different questions from different sources, and
    separate tables mean no migration can disturb another's rows.

    It is emphatically **not** a revival of ``project_reviews``.  The
    written design for this tier said it would "reuse the
    ``project_reviews`` table design"; that table left with the projects
    domain on 2026-08-13 (ADR-0005), was frozen, and was dropped by
    migration 014 on 2026-08-24.  What survives of that design is the
    *shape* — deterministic facts in ``stats``, hybrid narrative in
    ``narrative`` — and the two live mirrors of it are ``disk_reviews``
    and ``log_reviews``, which is what this follows.

    ``llm_used`` is False when llama-server was unavailable and the
    narrative is the deterministic digest instead.

    ``confidence`` is a column rather than a key inside ``stats``, the
    call :class:`~sysadmin.monitor.models.log_review.LogReview` made for
    its own reason and this one makes for a sharper one.  Every
    week-on-week figure in this review is a comparison of two windows,
    and on this box those windows have been observed at **16.5 %** and
    **96.8 %** of expected agent runs.  A review written across that
    reads exactly like one written across two complete weeks, so the
    qualifier has to be as reachable as the prose.
    """

    __tablename__ = "health_reviews"

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False, default=7)
    narrative: Mapped[str] = mapped_column(Text, nullable=False)
    llm_used: Mapped[bool] = mapped_column(Boolean, server_default=text("FALSE"))
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    #: ``high``/``low``, derived from this window's agent-run coverage
    #: against :data:`~sysadmin.monitor.reliability.LOW_COVERAGE_FRACTION`
    #: — the scorer's own threshold rather than a second one.
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    stats: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    __table_args__ = (Index("idx_health_reviews_generated", generated_at.desc()),)
