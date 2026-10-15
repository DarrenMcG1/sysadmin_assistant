"""The two game tables, built by migration 020 (ADR-0016 §4)."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class GameSpan(UUIDPrimaryKeyMixin, Base):
    """One unbroken run of polls that saw one game."""

    __tablename__ = "game_spans"

    game: Mapped[str] = mapped_column(String(255), nullable=False)
    #: ``steam_appid`` or ``executable`` — which rule found it.
    matched_by: Mapped[str] = mapped_column(String(20), nullable=False)
    appid: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executable: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: The outermost matching process at the first sighting.  Evidence,
    #: not identity: a span is keyed on the game, see
    #: :mod:`sysadmin.games.detect`.
    pid: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    #: ``None`` while open.  Set to ``last_seen_at``, never to the time of
    #: the poll that noticed the game had gone.
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(matched_by = 'steam_appid' AND appid IS NOT NULL)"
            " OR (matched_by = 'executable' AND executable IS NOT NULL)",
            name="chk_game_span_identity",
        ),
    )


class GameFocus(UUIDPrimaryKeyMixin, Base):
    """A stretch of one span where the game held focus, or nobody could tell.

    An unfocused stretch has no row.  ``unknown`` is a stretch where the
    focus probe gave no answer, which ADR-0016 §3 forbids reading as
    unfocused.
    """

    __tablename__ = "game_focus"

    span_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sysadmin.game_spans.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Never read.  It is what makes the unit of work insert a new span
    #: before a focus row naming it in the same flush: a bare foreign key
    #: orders nothing, and PostgreSQL refused the focus row first
    #: (``tests/test_game_spans_db.py``).
    span: Mapped[GameSpan] = relationship()
    state: Mapped[str] = mapped_column(String(10), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("state IN ('focused', 'unknown')", name="chk_game_focus_state"),
        Index("idx_game_focus_span", "span_id"),
    )
