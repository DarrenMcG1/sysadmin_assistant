"""Systemd unit sweep results from the Service Discovery agent."""

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.models.base import Base, UUIDPrimaryKeyMixin


class UnitAudit(UUIDPrimaryKeyMixin, Base):
    """One sweep of the installed systemd units.

    Every count lives in its own column rather than being derived from
    ``findings`` at read time.  That is Session 24's hard lesson repeating
    itself: the findings lists are truncated before storage, so a count
    summed from them is a lower bound that reads like a total.  The
    columns are written from the untruncated in-memory scan.

    The five bucket columns are exhaustive — ``units_scanned`` equals
    ``monitored_count + timers_folded + orphaned_count +
    unmonitored_count + host_count`` — so a reader can audit the sweep
    without trusting it.
    """

    __tablename__ = "unit_audits"

    #: Where the sweep looked.  Recorded because a row written when the
    #: system directory was unreadable is not comparable with one written
    #: when it was, and nothing else in the row would show the difference.
    user_unit_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_unit_dir: Mapped[str | None] = mapped_column(Text, nullable=True)

    units_scanned: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    #: Distro-owned (symlinked into /usr/lib) and template units, filtered
    #: out before classification.
    units_excluded: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    monitored_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    #: Timers reported under the Type=oneshot service they trigger.
    timers_folded: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    orphaned_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    unmonitored_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    host_count: Mapped[int] = mapped_column(Integer, server_default=text("0"))

    findings: Mapped[dict] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    scanned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("NOW()"), nullable=False
    )

    __table_args__ = (
        # Every read is "the latest sweep" — both endpoints, the
        # recommendation builder and the retention purge order by this
        # and take one row.
        Index("idx_unit_audits_scanned", scanned_at.desc()),
        {"schema": "sysadmin"},
    )
