"""The game detector — polls every 60 s and keeps ``game_spans`` (ADR-0016).

A span is one unbroken run of polls that saw one game.  Three rules
decide where a run breaks, and the first is the opposite of the obvious
implementation:

1. **A span ends at its last sighting, not at the poll that noticed.**
   ``ended_at = last_seen_at``, so a span is never over-counted by up to
   a poll interval (ADR-0016 §4).
2. **A gap of more than** :data:`GAP_POLLS` **intervals breaks a run**
   even when the game is still there.  A suspended box resumes with the
   game still open, and extending ``last_seen_at`` across the night
   would report hours of play nobody played.  Three intervals rather than
   one, so one late or failed poll does not split a session.
3. **A restart closes every open span** (:func:`close_open_spans`, from
   the lifespan).  The last sighting is the honest end; a game still
   running opens a new span on the first poll, and Alfred's merge joins
   them.

The agent keeps nothing in memory between polls: the open rows *are* the
state, so a restart or a failed poll loses nothing that the rules above
do not already account for.

**Focus is recorded, and the probe that reads it is not built yet.**
:attr:`GameDetectorAgent.focus_probe` answers with the active window's
PID, or ``None`` when it cannot tell.  Until ADR-0016's second half
wires the KWin probe, it always answers ``None``, so every gaming minute
is recorded as an ``unknown`` focus stretch.  That is the honest record:
nobody was looking, which §3 forbids reading as unfocused.  The probe is
only called on a poll that found a game (§3's journal-volume argument).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, update

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.games.detect import Sighting, scan
from sysadmin.games.models import GameFocus, GameSpan

logger = logging.getLogger(__name__)

#: Polls a run may miss before it breaks — rule 2.
GAP_POLLS = 3

FOCUSED = "focused"
UNKNOWN = "unknown"

#: The active window's PID, or ``None`` when the probe could not tell.
FocusProbe = Callable[[], Awaitable[int | None]]


async def no_focus_probe() -> int | None:
    """Stands in until the KWin probe exists (ADR-0016, second half)."""
    return None


def focus_state(sighting: Sighting, window_pid: int | None) -> str | None:
    """``focused``, ``unknown``, or ``None`` for unfocused (no row)."""
    if window_pid is None:
        return UNKNOWN
    return FOCUSED if window_pid in sighting.pids else None


def apply_poll(
    open_spans: Sequence[GameSpan],
    open_focus: Sequence[GameFocus],
    sightings: Sequence[Sighting],
    now: datetime,
    *,
    window_pid: int | None,
    max_gap: timedelta,
) -> list[GameSpan | GameFocus]:
    """Move the open rows to this poll; return the rows to insert.

    Mutates ``open_spans`` and ``open_focus`` in place — they are the
    session's own objects, so the commit writes them.  Pure otherwise:
    no session, no clock, no ``/proc``.
    """
    new: list[GameSpan | GameFocus] = []
    focus_by_span = {f.span_id: f for f in open_focus}
    by_key = {(s.matched_by, s.appid, s.executable): s for s in open_spans}
    seen = {s.key: s for s in sightings}

    def close(span: GameSpan) -> None:
        span.ended_at = span.last_seen_at
        stretch = focus_by_span.pop(span.id, None)
        if stretch is not None:
            stretch.ended_at = stretch.last_seen_at

    for key, span in by_key.items():
        if key not in seen or now - span.last_seen_at > max_gap:
            close(span)

    for key, sighting in seen.items():
        existing = by_key.get(key)
        if existing is not None and existing.ended_at is None:
            span = existing
            span.last_seen_at = now
        else:
            span = GameSpan(
                id=uuid.uuid4(),
                game=sighting.game,
                matched_by=sighting.matched_by,
                appid=sighting.appid,
                executable=sighting.executable,
                pid=sighting.pid,
                started_at=now,
                last_seen_at=now,
            )
            new.append(span)

        state = focus_state(sighting, window_pid)
        stretch = focus_by_span.get(span.id)
        if stretch is not None and stretch.state == state:
            stretch.last_seen_at = now
            continue
        if stretch is not None:
            stretch.ended_at = stretch.last_seen_at
        if state is not None:
            new.append(
                GameFocus(
                    span_id=span.id,
                    state=state,
                    started_at=now,
                    last_seen_at=now,
                )
            )
    return new


async def close_open_spans(session) -> int:
    """Close every open span and focus stretch at its last sighting — rule 3."""
    await session.execute(
        update(GameFocus)
        .where(GameFocus.ended_at.is_(None))
        .values(ended_at=GameFocus.last_seen_at)
    )
    result = await session.execute(
        update(GameSpan)
        .where(GameSpan.ended_at.is_(None))
        .values(ended_at=GameSpan.last_seen_at)
    )
    return int(result.rowcount)


class GameDetectorAgent(BaseAgent):
    """Records the spans in which a game was running.  Never alerts."""

    def __init__(self, focus_probe: FocusProbe = no_focus_probe) -> None:
        self.focus_probe = focus_probe

    @property
    def name(self) -> str:
        return "game_detector"

    async def _execute(self, session) -> AgentResult:
        config = get_config().agents.game_detector
        sightings = await asyncio.to_thread(
            scan, Path(config.steam_root).expanduser(), config.games
        )
        window_pid = await self.focus_probe() if sightings else None
        now = datetime.now(UTC)

        open_spans = list(
            (await session.execute(select(GameSpan).where(GameSpan.ended_at.is_(None))))
            .scalars()
            .all()
        )
        open_focus = list(
            (await session.execute(select(GameFocus).where(GameFocus.ended_at.is_(None))))
            .scalars()
            .all()
        )
        new = apply_poll(
            open_spans,
            open_focus,
            sightings,
            now,
            window_pid=window_pid,
            max_gap=timedelta(seconds=config.poll_interval_seconds * GAP_POLLS),
        )
        session.add_all(new)
        return AgentResult(
            findings_count=len(sightings),
            details={
                "games": sorted(s.game for s in sightings),
                "spans_opened": sum(isinstance(row, GameSpan) for row in new),
            },
        )
