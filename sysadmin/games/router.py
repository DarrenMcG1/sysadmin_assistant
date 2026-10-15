"""``GET /api/games/spans`` — the games that ran in a range (ADR-0016 §5).

Read-only, and raw: one span per unbroken run of polls, every focus
stretch it has, no merging and no minimum length.  Alfred's thresholds
are Alfred's reading of *Downtime* and are applied there.

Three rules:

1. **A span is returned if it overlaps the range**, not only if it
   starts inside it, so a session crossing midnight appears on both
   days.  The range is half-open, ``[start, end)``, and an open span
   (``ended_at`` null) overlaps every range that ends after it started.
2. **A timestamp without an offset is refused** (422).  The box keeps
   British time and stores UTC; guessing which one a naive value meant
   would move an evening's play by an hour for half the year.  A ``+``
   offset must be sent as ``%2B``, because a query string decodes ``+``
   to a space; ``Z`` needs no encoding, so the refusal suggests it.
3. **``retained_from`` is the later of two floors**: the oldest run of
   the detector this service still holds, and the retention cutoff for
   ``game_spans``.  The first says when anyone started looking; the
   second says what the nightly purge has already taken.  Either alone
   would claim minutes this service cannot vouch for.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.contracts import GameSpansResponse
from sysadmin.core.database import get_db_session
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.core.models.retention_config import RetentionConfig
from sysadmin.games.agent import UNKNOWN
from sysadmin.games.models import GameFocus, GameSpan

router = APIRouter(prefix="/api/games", tags=["games"])


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def retained_from(
    oldest_run: datetime | None, retention_days: int | None, now: datetime
) -> datetime | None:
    """Rule 3: the earliest instant the spans can vouch for, or ``None``."""
    if oldest_run is None:
        return None
    if retention_days is None:
        return oldest_run
    return max(oldest_run, now - timedelta(days=retention_days))


def span_payload(span: GameSpan, stretches: list[GameFocus]) -> dict:
    """One span as served, its stretches oldest first."""
    stretches = sorted(stretches, key=lambda f: f.started_at)
    return {
        "game": span.game,
        "matched_by": span.matched_by,
        "appid": span.appid,
        "executable": span.executable,
        "started_at": _iso(span.started_at),
        "last_seen_at": _iso(span.last_seen_at),
        "ended_at": _iso(span.ended_at),
        "focus": [
            {
                "state": f.state,
                "started_at": _iso(f.started_at),
                "last_seen_at": _iso(f.last_seen_at),
                "ended_at": _iso(f.ended_at),
            }
            for f in stretches
        ],
        "focus_known": all(f.state != UNKNOWN for f in stretches),
    }


def _aware(name: str, value: datetime) -> datetime:
    if value.tzinfo is None:
        raise HTTPException(
            status_code=422,
            detail=f"{name} has no UTC offset; send e.g. 2026-10-15T00:00:00Z",
        )
    return value


@router.get("/spans", response_model=GameSpansResponse)
async def get_game_spans(
    start: datetime = Query(..., description="Range start, inclusive, with an offset"),
    end: datetime = Query(..., description="Range end, exclusive, with an offset"),
    session: AsyncSession = Depends(get_db_session),
):
    """The spans in which a game was running that overlap ``[start, end)``."""
    start, end = _aware("start", start), _aware("end", end)
    if end <= start:
        raise HTTPException(status_code=422, detail="end must be after start")

    spans = list(
        (
            await session.execute(
                select(GameSpan)
                .where(GameSpan.started_at < end)
                .where(or_(GameSpan.ended_at.is_(None), GameSpan.ended_at >= start))
                .order_by(GameSpan.started_at)
            )
        )
        .scalars()
        .all()
    )
    focus: dict = defaultdict(list)
    if spans:
        rows = await session.execute(
            select(GameFocus).where(GameFocus.span_id.in_([s.id for s in spans]))
        )
        for stretch in rows.scalars().all():
            focus[stretch.span_id].append(stretch)

    oldest_run = (
        await session.execute(
            select(func.min(AgentRun.started_at)).where(AgentRun.agent == "game_detector")
        )
    ).scalar_one_or_none()
    retention_days = (
        await session.execute(
            select(RetentionConfig.retention_days).where(
                RetentionConfig.table_name == "game_spans"
            )
        )
    ).scalar_one_or_none()

    return {
        "poll_seconds": get_config().agents.game_detector.poll_interval_seconds,
        "retained_from": _iso(retained_from(oldest_run, retention_days, datetime.now(UTC))),
        "spans": [span_payload(s, focus[s.id]) for s in spans],
    }
