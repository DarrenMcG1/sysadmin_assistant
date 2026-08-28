"""What the understudy has said out loud, kept across a restart.

``SNAG-TRAY-008``.  :class:`~sysadmin.monitor.desktop.DesktopNotifier`
restates a fault it announced that is still open, and its population was
exactly the keys of an in-memory dict — so the reminder interval was
reachable only by a process that lived a full ``reminder_hours``.
Measured over 28.26 days, ``sysadmin.service`` started **111 times** at a
median uptime of **1.77 h** and only **5 of 110** lives reached the 24 h
the interval asks for.  A reminder that requires a 24-hour process on a
box whose daemon lives 1.77 hours is not a slow reminder; it is silence
with a number beside it.

**One row per fault, keyed on the title**, because the title is the
identity of a fault everywhere else in this repository — the tray
fingerprints on ``{severity}:{title}``, every dedup and every resolve
keys on it, and four separate rules forbid forking it.  The unique
constraint is what makes the write an upsert rather than a read followed
by a branch.

**Wall clock, not monotonic, and the store is why but not the only
reason.**  :class:`~sysadmin.monitor.desktop.TrayPresence` argues for
``time.monotonic`` and keeps it: it answers *how long since the tray
polled* over a 180-second window, where an NTP step would be the larger
error and where a suspended box correctly counts nothing, since neither
process was running.  A **24-hour** interval reads the other way round —
``CLOCK_MONOTONIC`` stops during suspend, so a workstation asleep
overnight charges nothing against a reminder that is precisely about
elapsed human time.  The clocks now differ on purpose, and only one of
them is a timestamp a column can hold.

**No timestamp index.**  The table is bounded by the number of distinct
open faults this daemon has spoken for — single digits on this box, and
capped for the adopted half by
:data:`~sysadmin.monitor.desktop.MAX_ADOPTED_TITLES` — so the nightly
retention scan reads a handful of rows.  An index would be a write cost
paid on every notification to speed up a sequential scan of five rows.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from sysadmin.core.models.base import Base, UUIDPrimaryKeyMixin


class DesktopNotification(UUIDPrimaryKeyMixin, Base):
    """One fault the daemon is speaking for, and when it last did."""

    __tablename__ = "desktop_notifications"

    title: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    #: When the *episode* began — the opening notification for a fault
    #: this process announced, and the alert row's own ``created_at`` for
    #: one it adopted.  Deliberately not called ``first_spoken_at`` any
    #: more: nothing was spoken at that moment for an adopted fault, and
    #: the reminder body it feeds says "after the first **alert**", which
    #: is true of both.
    episode_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    #: When anything last said this out loud.  Moved only by an utterance
    #: — never by the tray's presence stamping the in-memory clock
    #: forward, which is a belief about another process rather than
    #: something this one said.
    last_spoken_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    reminders_sent: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    #: True when the fault was **adopted** — open, at or above the
    #: threshold, and never announced by this daemon.  Read rather than
    #: decorative: it is what bounds the adopted population against
    #: :data:`~sysadmin.monitor.desktop.MAX_ADOPTED_TITLES` across a
    #: restart, and a cap that reset on every restart would let a
    #: 1.77-hour daemon adopt the whole open set five titles at a time.
    adopted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("FALSE")
    )
