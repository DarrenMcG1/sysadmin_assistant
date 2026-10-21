"""The advice routes compute off the API's event loop (Session 333).

``GET /api/services/actions`` held the loop for up to 4.2 s per call
under the unit's ``CPUQuota=``, measured as the wait of a concurrent
``async def`` route, and the watchdog's ping runs on that same loop.
Three things keep it off: :func:`run_off_loop` moves the work to a
thread with its own loop, both routes go through it rather than the
request session, and ``fetch_timer_series`` has Postgres extract the
four keys it reads instead of decoding ~86,000 JSONB blobs here.

A fourth keeps the worker from holding the GIL for a whole result set:
both reads stream a partition at a time (SNAG-SVC-008).
"""

import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.core.database import get_db_session, run_off_loop
from sysadmin.main import create_app
from sysadmin.monitor.reliability_history import (
    ROWS_PER_PARTITION,
    compute_reliability,
    fetch_timer_series,
)
from tests.conftest import set_services, stream_rows

NOW = datetime(2026, 10, 2, 12, 0, tzinfo=UTC)


def _patched_worker_session(session):
    @asynccontextmanager
    async def worker_session():
        yield session

    return patch("sysadmin.core.database.get_scheduler_session", worker_session)


# ── run_off_loop ─────────────────────────────────────────────────────


async def test_the_work_runs_on_another_thread_and_another_loop():
    seen = {}
    session = object()

    async def work(s):
        seen["thread"] = threading.get_ident()
        seen["loop"] = asyncio.get_running_loop()
        seen["session"] = s
        return 42

    with _patched_worker_session(session):
        assert await run_off_loop(work) == 42

    assert seen["thread"] != threading.get_ident()
    assert seen["loop"] is not asyncio.get_running_loop()
    assert seen["session"] is session


async def test_the_api_loop_keeps_turning_while_the_work_burns_cpu():
    """A blocking stand-in for the decode: the caller's loop must not wait it out."""
    ticks = 0

    async def work(_session):
        deadline = threading.Event()
        threading.Timer(0.3, deadline.set).start()
        while not deadline.is_set():
            pass  # pure CPU, no await, as asyncpg's row loop is
        return "done"

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    task = asyncio.create_task(ticker())
    with _patched_worker_session(None):
        assert await run_off_loop(work) == "done"
    task.cancel()

    # 0.3 s at 10 ms would be 30 ticks; on the loop it would be 0.
    assert ticks >= 5


async def test_an_exception_in_the_work_reaches_the_caller():
    async def work(_session):
        raise RuntimeError("the database went away")

    with _patched_worker_session(None), pytest.raises(RuntimeError, match="went away"):
        await run_off_loop(work)


# ── the routes use it ────────────────────────────────────────────────


def _dependency_calls(path):
    route = next(r for r in create_app().routes if getattr(r, "path", None) == path)
    return {d.call for d in route.dependant.dependencies}


@pytest.mark.parametrize("path", ["/api/services/actions", "/api/services/reliability"])
def test_the_route_takes_no_request_session(path):
    """The request session is the loop's: a route depending on it reads there."""
    assert get_db_session not in _dependency_calls(path)


def test_the_reader_finds_the_session_on_a_route_that_takes_it():
    """Both routes above declare no dependencies at all, so their set is empty.

    Without this the assert above could not fail: it would hold over an
    empty set whatever the reader looked at (SNAG-TEST-016).
    """
    assert get_db_session in _dependency_calls("/api/units/status")


# ── fetch_timer_series reads four keys, not the blob ─────────────────


@pytest.fixture
def timer_service():
    set_services(
        {
            "name": "nightly-timer",
            "kind": "timer",
            "systemd": {"unit": "nightly.timer", "scope": "user"},
        }
    )


def _rows(session, rows):
    stream_rows(session, rows)


async def test_the_query_extracts_keys_rather_than_selecting_details(
    timer_service, mock_config, mock_session
):
    _rows(mock_session, [])
    await fetch_timer_series(mock_session, mock_config, now=NOW)

    statement = mock_session.connection.return_value.stream.call_args.args[0]
    sql = str(
        statement.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    for key in ("last_run", "last_result", "triggered_unit", "is_active"):
        assert f"service_health.details ->> '{key}'" in sql
    # The whole column, selected bare, is what put the decode in this process.
    assert "service_health.details," not in sql
    assert not sql.split("FROM")[0].rstrip().endswith("service_health.details")


async def test_extracted_values_become_timer_points(timer_service, mock_config, mock_session):
    t0 = NOW - timedelta(hours=2)
    t1 = NOW - timedelta(hours=1)
    _rows(
        mock_session,
        [
            ("nightly-timer", t0, "Thu 2026-10-01 03:00 BST", "success", "nightly.service", "true"),
            ("nightly-timer", t1, None, None, None, None),
            ("retired-timer", t1, "x", "success", "x.service", "true"),
        ],
    )
    [series] = await fetch_timer_series(mock_session, mock_config, now=NOW)

    assert series.service == "nightly-timer"
    assert series.unit == "nightly.timer"
    first, second = series.points
    assert first.last_run == "Thu 2026-10-01 03:00 BST"
    assert first.last_result == "success"
    assert first.triggered_unit == "nightly.service"
    assert first.is_active is True
    # Absent keys come back NULL: no run recorded, and armed by default.
    assert (second.last_run, second.last_result, second.triggered_unit) == (None, None, None)
    assert second.is_active is True


async def test_only_a_json_false_reads_inactive(timer_service, mock_config, mock_session):
    _rows(mock_session, [("nightly-timer", NOW, None, None, None, "false")])
    [series] = await fetch_timer_series(mock_session, mock_config, now=NOW)
    assert series.points[0].is_active is False


# ── both reads stream in partitions (SNAG-SVC-008) ───────────────────


@pytest.mark.parametrize("read", [compute_reliability, fetch_timer_series])
async def test_the_read_streams_a_partition_at_a_time(
    read, timer_service, mock_config, mock_session
):
    """Read whole, the row loops held the GIL for the whole result set.

    ``execute`` buffers every row before it returns; the streamed cursor
    makes each partition a round trip, and the worker gives the GIL up
    while it waits for one.
    """
    _rows(mock_session, [])
    await read(mock_session, mock_config, now=NOW)

    mock_session.execute.assert_not_called()
    statement = mock_session.connection.return_value.stream.call_args.args[0]
    assert statement.get_execution_options()["yield_per"] == ROWS_PER_PARTITION


async def test_every_partition_is_read(timer_service, mock_config, mock_session):
    rows = [
        ("nightly-timer", NOW - timedelta(minutes=i), None, None, None, "true")
        for i in range(5, 0, -1)
    ]
    _rows(mock_session, rows)
    with patch("sysadmin.monitor.reliability_history.ROWS_PER_PARTITION", 2):
        [series] = await fetch_timer_series(mock_session, mock_config, now=NOW)

    # Three partitions of 2, 2 and 1.
    assert [p.checked_at for p in series.points] == [r[1] for r in rows]
