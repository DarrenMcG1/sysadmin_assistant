"""Game spans written to a database built to head by the migration chain.

The pure tests in ``test_games.py`` cannot see what PostgreSQL decides:
a focus row inserted with its span in one flush needs the span written
first (there is no ORM relationship to order them, only the foreign
key), the identity CHECK must admit both kinds of span, and a restart's
close must reach both tables.  Built from empty by
``test_schema_build``'s fixture, so it skips where that does.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from sysadmin.core.contracts import GameSpansResponse
from sysadmin.core.retention import purge_statement
from sysadmin.games.agent import FOCUSED, apply_poll, close_open_spans
from sysadmin.games.detect import MATCHED_BY_EXECUTABLE, MATCHED_BY_STEAM, Sighting
from sysadmin.games.models import GameFocus, GameSpan
from sysadmin.games.router import get_game_spans
from tests.test_schema_build import build, pytestmark  # noqa: F401

# ``build`` is the scratch database and ``pytestmark`` its skip.  Ruff
# reads a test requesting ``build`` as a redefinition (F811); it is the
# fixture, by design.

T0 = datetime(2026, 10, 15, 20, 0, tzinfo=UTC)
STEAM_GAME = Sighting("Deadlock", MATCHED_BY_STEAM, 1422450, None, 200, frozenset({200, 204}))
LISTED_GAME = Sighting("Factorio", MATCHED_BY_EXECUTABLE, None, "factorio", 10, frozenset({10}))


@pytest.fixture
def engine(build):  # noqa: F811
    engine = create_engine(build.url)
    yield engine
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM sysadmin.game_spans"))
        conn.execute(text("DELETE FROM sysadmin.agent_runs WHERE agent = 'game_detector'"))
    engine.dispose()


def _open(engine):
    with Session(engine) as session:
        spans = list(session.scalars(select(GameSpan).where(GameSpan.ended_at.is_(None))))
        focus = list(session.scalars(select(GameFocus).where(GameFocus.ended_at.is_(None))))
        return spans, focus


def _poll(engine, sightings, now, window_pid):
    with Session(engine) as session, session.begin():
        spans = list(session.scalars(select(GameSpan).where(GameSpan.ended_at.is_(None))))
        focus = list(session.scalars(select(GameFocus).where(GameFocus.ended_at.is_(None))))
        gap = timedelta(seconds=180)
        session.add_all(
            apply_poll(spans, focus, sightings, now, window_pid=window_pid, max_gap=gap)
        )


def test_a_span_and_its_focus_insert_in_one_flush(engine):
    _poll(engine, [STEAM_GAME, LISTED_GAME], T0, window_pid=204)
    spans, focus = _open(engine)
    assert {s.game for s in spans} == {"Deadlock", "Factorio"}
    [stretch] = [f for f in focus if f.state == FOCUSED]
    assert stretch.span_id == next(s.id for s in spans if s.game == "Deadlock")


def test_polls_extend_then_close_at_the_last_sighting(engine):
    _poll(engine, [STEAM_GAME], T0, window_pid=204)
    _poll(engine, [STEAM_GAME], T0 + timedelta(seconds=60), window_pid=204)
    _poll(engine, [], T0 + timedelta(seconds=120), window_pid=None)
    with Session(engine) as session:
        [span] = session.scalars(select(GameSpan))
        [stretch] = session.scalars(select(GameFocus))
    assert (span.started_at, span.ended_at) == (T0, T0 + timedelta(seconds=60))
    assert stretch.ended_at == T0 + timedelta(seconds=60)


@pytest.mark.asyncio
async def test_a_restart_closes_both_tables(build, engine):  # noqa: F811
    _poll(engine, [STEAM_GAME], T0, window_pid=None)
    async_engine = create_async_engine(build.url.replace("+psycopg2", "+asyncpg"))
    try:
        async with AsyncSession(async_engine) as session, session.begin():
            assert await close_open_spans(session) == 1
    finally:
        await async_engine.dispose()
    assert _open(engine) == ([], [])


def test_the_purge_takes_the_focus_rows_with_their_span(engine):
    _poll(engine, [STEAM_GAME], T0, window_pid=204)
    with engine.begin() as conn:
        conn.execute(
            text(purge_statement("game_spans", "last_seen_at")),
            {"cutoff": T0 + timedelta(days=1)},
        )
        assert conn.execute(text("SELECT count(*) FROM sysadmin.game_focus")).scalar() == 0


def _closed_span(game, started, ended):
    return GameSpan(
        game=game,
        matched_by=MATCHED_BY_EXECUTABLE,
        executable=game.lower(),
        pid=10,
        started_at=started,
        last_seen_at=ended,
        ended_at=ended,
    )


@pytest.mark.asyncio
async def test_the_route_serves_every_span_overlapping_the_range(
    build, engine, patched_config  # noqa: F811
):
    """ADR-0016 §5 rule 1: overlap, not start-inside, over ``[start, end)``.

    A session crossing the range's start, one still open, and one inside
    are served; one that ended before the range and one starting exactly
    at its end are not.
    """
    start, end = T0, T0 + timedelta(hours=4)
    with Session(engine) as session, session.begin():
        session.add_all(
            [
                _closed_span("Before", start - timedelta(hours=2), start - timedelta(minutes=1)),
                _closed_span("Crossing", start - timedelta(hours=1), start + timedelta(minutes=5)),
                _closed_span("Inside", start + timedelta(hours=1), start + timedelta(hours=2)),
                _closed_span("AtEnd", end, end + timedelta(minutes=30)),
            ]
        )
        session.execute(
            text(
                "INSERT INTO sysadmin.agent_runs (agent, run_type, status, started_at)"
                " VALUES ('game_detector', 'scheduled', 'completed', :at)"
            ),
            {"at": start - timedelta(days=1)},
        )
    _poll(engine, [STEAM_GAME], start + timedelta(hours=3), window_pid=204)

    async_engine = create_async_engine(build.url.replace("+psycopg2", "+asyncpg"))
    try:
        async with AsyncSession(async_engine) as session:
            payload = await get_game_spans(start=start, end=end, session=session)
    finally:
        await async_engine.dispose()

    assert [s["game"] for s in payload["spans"]] == ["Crossing", "Inside", "Deadlock"]
    deadlock = payload["spans"][-1]
    assert deadlock["ended_at"] is None
    assert [f["state"] for f in deadlock["focus"]] == [FOCUSED]
    assert payload["retained_from"] == (start - timedelta(days=1)).isoformat()
    assert GameSpansResponse.from_dict(payload).spans[0].game == "Crossing"
