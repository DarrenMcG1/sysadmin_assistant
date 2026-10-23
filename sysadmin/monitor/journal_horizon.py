"""How far back the journal reaches, and the core-dump loops that shorten it.

Session 414 found the gap.  journald runs on its defaults here, so the
system and user files share one 4G cap.  baloo's crash loop wrote about
207k ``systemd-coredump`` records between 2026-10-20 and 2026-10-22,
filled that cap, and the vacuum cut the journal back to three days.
**Nothing in this service noticed**: venture-assistant did, when its
nightly drain found 10-17 to 10-20 gone (estate message ``4a35a2e7``).
estate-manager's ADR-0185 places the box's disk disposition with this
repository, so the watch is here.

Two families, one per cause a reader can act on:

- ``Short journal window`` — the oldest retained record is younger than
  ``min_window_days``.  This is the symptom every journal reader pays
  for, whatever filled the cap.
- ``Core dump loop in <exe>`` — one executable dumped ``loop_count``
  times or more in the last ``loop_window_minutes``.  This is the cause
  seen hours before the window collapses: baloo's loop ran for two and
  a half days before anyone looked.

Four rules.

1. **The window is the shorter of the two scopes.**  The daemon reads
   both: the system journal, and its user's own with ``--user``.
   Measured 2026-10-23 they started five minutes apart (12:16 and
   12:21), because journald vacuums one directory.  The shorter one is
   what a reader of either scope can rely on.
2. **Not knowing is not a fault, and it holds open rows.**  A read that
   fails raises nothing and resolves nothing, so a broken ``journalctl``
   cannot close a row that is still true.  That is
   :mod:`sysadmin.monitor.collation`'s fail-open rule.
3. **Raised once per open row; this family resolves its own rows.**  It
   stays out of :data:`sysadmin.monitor.agent.RESOLVABLE_TITLE_PATTERNS`
   for collation's rule-4 reason: a second owner closes a row while the
   first still holds it true.  Both titles end in a word none of those
   patterns ends in, and a test pins that.
4. **A loop is counted per executable, never in total.**  The remedy is
   per program (disable it, fix it), and a total would sum three
   unrelated browser crashes into one false loop.  Measured over the
   24 hours to 2026-10-23 21:50: three dumps from three executables.
   The flood's worst hour held 11,963 from ``baloo_file_extractor``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sysadmin.monitor.journal import _run, since_timestamp

#: ``details`` key marking the window row.  Its value is always
#: :data:`WINDOW_SUBJECT`, because the box has one journal window.
HORIZON_DETAIL_KEY = "journal_horizon"
WINDOW_SUBJECT = "window"

#: ``details`` key naming the executable a loop row is about.
COREDUMP_DETAIL_KEY = "coredump_exe"

#: Both families are ``warning``, for collation's reason: ``critical``
#: breaks through DND and ``info`` is below the tray's notify floor.
HORIZON_SEVERITY = "warning"

#: ``systemd-coredump``'s catalogue id for "Process … dumped core".
#: Filtering on it keeps the read to dump records alone; the unit's
#: other lines (start, stop, the stack trace) carry other ids or none.
COREDUMP_MESSAGE_ID = "fc2e22bc6ee647b6b90729ab34a250b1"

WINDOW_TITLE = "Short journal window"


def loop_title(exe: str) -> str:
    """The title for a dump loop in ``exe``, its basename last."""
    return f"Core dump loop in {os.path.basename(exe)}"


@dataclass(frozen=True)
class Window:
    """How far back the journal reaches, per scope.

    ``None`` for a scope whose read failed or came back empty.
    """

    system_head: datetime | None
    user_head: datetime | None
    measured_at: datetime

    @property
    def head(self) -> datetime | None:
        """The newer of the two heads — rule 1.  ``None`` if both failed."""
        heads = [h for h in (self.system_head, self.user_head) if h is not None]
        return max(heads) if heads else None

    @property
    def days(self) -> float | None:
        head = self.head
        if head is None:
            return None
        return (self.measured_at - head).total_seconds() / 86_400


@dataclass(frozen=True)
class Loop:
    """One executable that dumped core at least ``loop_count`` times."""

    exe: str
    count: int
    window_minutes: int

    @property
    def title(self) -> str:
        return loop_title(self.exe)

    @property
    def message(self) -> str:
        return (
            f"{self.exe} dumped core {self.count} times in the last "
            f"{self.window_minutes} minutes. Each dump is a journal "
            f"record, and a loop fills the journal's size cap until the "
            f"vacuum cuts its window short. Stop the program or fix the "
            f"crash; coredumpctl info {os.path.basename(self.exe)} shows "
            f"the newest trace."
        )

    @property
    def details(self) -> dict[str, Any]:
        return {
            COREDUMP_DETAIL_KEY: self.exe,
            "dumps": self.count,
            "window_minutes": self.window_minutes,
        }


def window_message(window: Window, min_days: float) -> str:
    """The window row's sentence, stating both instants and the floor."""
    head = window.head
    assert head is not None and window.days is not None
    return (
        f"The journal reaches back {window.days:.1f} days, to "
        f"{head.astimezone():%Y-%m-%d %H:%M}, under the {min_days:g}-day "
        f"floor. Records older than that are gone, so a reader that "
        f"looks further back finds nothing. Usual cause: something "
        f"flooding the journal (see any open core dump loop row); "
        f"journalctl --disk-usage shows the cap."
    )


def window_details(window: Window, min_days: float) -> dict[str, Any]:
    return {
        HORIZON_DETAIL_KEY: WINDOW_SUBJECT,
        "window_days": round(window.days or 0.0, 2),
        "min_window_days": min_days,
        "system_head": window.system_head.isoformat() if window.system_head else None,
        "user_head": window.user_head.isoformat() if window.user_head else None,
    }


def is_short(window: Window, min_days: float) -> bool | None:
    """Whether the window is under the floor; ``None`` when unknown."""
    days = window.days
    if days is None:
        return None
    return days < min_days


def loops_from(
    exe_counts: dict[str, int], loop_count: int, window_minutes: int
) -> list[Loop]:
    """Executables at or over ``loop_count``, most dumps first — rule 4."""
    found = [
        Loop(exe=exe, count=n, window_minutes=window_minutes)
        for exe, n in exe_counts.items()
        if n >= loop_count
    ]
    return sorted(found, key=lambda loop: (-loop.count, loop.exe))


def _epoch_head(stdout: str | None) -> datetime | None:
    """The ``__REALTIME_TIMESTAMP`` of a one-record JSON read, or ``None``."""
    if not stdout:
        return None
    try:
        micros = int(json.loads(stdout.splitlines()[0])["__REALTIME_TIMESTAMP"])
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    return datetime.fromtimestamp(micros / 1_000_000, tz=UTC)


async def read_head(user: bool) -> datetime | None:
    """The oldest retained record's time in one scope.

    ``-n +1`` is the oldest record (systemd 255 and later) and costs
    about 2 ms here, against a journal of 4G.  No ``build_env`` is
    needed for ``--user``: journalctl reads the files, not the bus, and
    it answered under the daemon's stripped environment.
    """
    cmd = ["journalctl", "-n", "+1", "-o", "json",
           "--output-fields=__REALTIME_TIMESTAMP", "--no-pager", "-q"]
    if user:
        cmd.insert(1, "--user")
    return _epoch_head(await _run(cmd, "journal-head"))


async def read_window(now: datetime | None = None) -> Window:
    """Both scopes' heads, measured against ``now``."""
    return Window(
        system_head=await read_head(user=False),
        user_head=await read_head(user=True),
        measured_at=now or datetime.now(UTC),
    )


async def read_dump_counts(
    window_minutes: int, now: datetime | None = None
) -> dict[str, int] | None:
    """Core dumps per executable in the last ``window_minutes``.

    ``None`` when the read failed, which is not the same as no dumps —
    rule 2.  The flood's worst hour was 11,963 records and read in
    0.55 s, inside :func:`sysadmin.monitor.journal._run`'s 30 s timeout.
    """
    since = (now or datetime.now(UTC)) - timedelta(minutes=window_minutes)
    cmd = ["journalctl", f"MESSAGE_ID={COREDUMP_MESSAGE_ID}",
           "--since", since_timestamp(since), "-o", "json",
           "--output-fields=COREDUMP_EXE", "--no-pager", "-q"]
    stdout = await _run(cmd, "systemd-coredump")
    if stdout is None:
        return None
    counts: dict[str, int] = {}
    for line in stdout.splitlines():
        try:
            exe = json.loads(line).get("COREDUMP_EXE")
        except ValueError:
            continue
        if isinstance(exe, str) and exe:
            counts[exe] = counts.get(exe, 0) + 1
    return counts
