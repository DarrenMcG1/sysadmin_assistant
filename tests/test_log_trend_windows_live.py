"""Which of the trend report's counts are windowed, against the real query.

``LogSignatureTrendInfo`` says it since Session 295: ``current`` and
``previous`` are counts inside the two windows, and ``total``,
``first_seen`` and ``last_seen`` span all retained history.  The
unwindowed half is deliberate — ``docs/design/logs.md`` rule 2 judges
"new" against everything retained, and ``first_seen`` is how.

Nothing pinned it.  ``tests/test_log_trends.py`` drives
:func:`build_report` with hand-built :class:`MessageGroup` rows whose
fixture defaults ``total`` to ``current + previous`` — the very reading
the contract says is wrong — and the three ``FILTER`` clauses that decide
the question live in :func:`build_trend_report`'s SQL, which no test ran.
A windowed ``total`` would pass every test in that file.

So this drives the query itself, with one signature of three rows: one
in the current window, one in the previous, and one **older than both**.
The last row is the whole test.  It is counted by ``total`` and moves
``first_seen``, and it is counted by neither window.

**The group cap is lifted for this drive, and that is not a judgement
on the cap.**  This box holds more groups than the shipped 2,000 (2,461
on 2026-09-30).  When this was written the query ranked on the
unwindowed ``count()``, so a three-row probe sat below the cut and the
drive would have failed on the cap and not on the windowing.  Since
``SNAG-LOG-020`` the probe is its shape's oldest group and survives any
cap above the shape count, but the lift stays: this file asks about
windows, and ``tests/test_log_trend_cap_live.py`` asks about the cap.

The rows are real and the transaction is rolled back.
:func:`build_trend_report` does not commit, and the session joins the
outer transaction by savepoint anyway, in case it ever does.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest

from sysadmin.core.config import get_config
from sysadmin.monitor.log_query import build_trend_report
from sysadmin.monitor.log_trends import SignatureTrend
from sysadmin.monitor.models.log_entry import LogEntry

PROBE_SOURCE = "sysadmin-live-probe"
#: No digits, so the signature normaliser leaves it whole and one message
#: folds to one signature.
PROBE_MESSAGE = "sysadmin live probe: a trend row that is never committed"
WINDOW_DAYS = 7

#: Well clear of any live group count, so that whether the probe is read
#: is not a question about how noisy the box has been.
UNCAPPED = 1_000_000


def _db_available() -> bool:
    from sqlalchemy import create_engine

    try:
        engine = create_engine(
            "postgresql+psycopg2://gaddi@localhost:5432/projects",
            connect_args={"connect_timeout": 2},
        )
        try:
            with engine.connect():
                return True
        finally:
            engine.dispose()
    except Exception:
        return False


@asynccontextmanager
async def _rolled_back():
    """A session on a connection whose transaction is rolled back."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.pool import NullPool

    config = get_config()
    engine = create_async_engine(
        config.database.url,
        poolclass=NullPool,
        connect_args={
            "server_settings": {"search_path": f"{config.database.schema_},public"}
        },
    )
    try:
        async with engine.connect() as connection:
            outer = await connection.begin()
            factory = async_sessionmaker(
                bind=connection,
                class_=AsyncSession,
                expire_on_commit=False,
                join_transaction_mode="create_savepoint",
            )
            async with factory() as session:
                try:
                    yield session
                finally:
                    await session.rollback()
                    await outer.rollback()
    finally:
        await engine.dispose()


async def _drive() -> dict:
    now = datetime.now(UTC)
    # A day inside each boundary, so the half-open window edges and the
    # few milliseconds between here and the query's own ``now`` decide
    # nothing.
    stamps = {
        "current": now - timedelta(days=1),
        "previous": now - timedelta(days=WINDOW_DAYS + 3),
        "older": now - timedelta(days=WINDOW_DAYS * 2 + 6),
    }
    async with _rolled_back() as session:
        session.add_all(
            LogEntry(
                source=PROBE_SOURCE,
                severity="warning",
                message=PROBE_MESSAGE,
                logged_at=stamp,
            )
            for stamp in stamps.values()
        )
        await session.flush()
        report = await build_trend_report(session, WINDOW_DAYS)

    probes = [t for t in report.signatures if t.source == PROBE_SOURCE]
    return {"stamps": stamps, "report": report, "probes": probes}


@pytest.fixture(scope="module")
def reading() -> dict:
    if not _db_available():
        pytest.skip("local postgres (projects DB) not reachable")
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(get_config().agents.log_aggregator, "trend_max_groups", UNCAPPED)
        return asyncio.run(_drive())


@pytest.fixture(scope="module")
def probe(reading) -> SignatureTrend:
    (only,) = reading["probes"]
    return only


class TestTheCountsSplitAtTheWindow:
    @pytest.mark.premise
    def test_the_probe_was_read_and_nothing_was_cut(self, reading):
        """The premise: the fold saw every group, and the probe as one.

        With the cap in force, a missing probe would read as "the query
        dropped the old row", and it would be a verdict about the cap.
        ``truncated`` is what says the lift reached the query, and
        exactly one probe signature is what says the three rows folded
        together rather than into three signatures.
        """
        assert reading["report"].truncated is False
        assert len(reading["probes"]) == 1
        assert reading["report"].window_days == WINDOW_DAYS

    def test_each_window_counts_only_its_own_row(self, probe):
        assert probe.current == 1
        assert probe.previous == 1

    def test_total_counts_the_row_outside_both_windows(self, probe):
        """The entry.  A windowed ``total`` reads 2 here."""
        assert probe.total == 3
        assert probe.total > probe.current + probe.previous

    def test_first_seen_is_the_row_outside_both_windows(self, probe, reading):
        """``first_seen`` is unwindowed, which is what keeps this from reading as new.

        A signature whose first row in the *windows* is this week and
        whose first row in *retained history* is three weeks ago is not
        new, and ``change`` is how the report says so.
        """
        stamps = reading["stamps"]
        assert probe.first_seen == stamps["older"]
        assert probe.first_seen < reading["report"].previous_start
        assert probe.last_seen == stamps["current"]
        assert probe.is_new is False
