"""The arbiter seam against the running estate (SNAG-AGENT-011).

The recorded half in ``tests/test_arbitrated_stops.py`` is a photograph:
it catches consumer drift and is structurally unable to catch the
producer's.  That matters more here than for most seams, because this
entry was **filed against the wrong route** and the error was invisible
from inside this repository.  ``SNAG-AGENT-011`` said
``GET /api/queue/invariants`` publishes ``stopped_units``; it does not.
``Arbiter.invariants`` selects an explicit column list and pops
``hold_overdue`` before returning, so ``active_lease`` reaches the wire
with five keys — a field is a property of a **route**, not of a table,
and only the handler's projection can say which.  A fixture written from
the snag's prose would have been green and wrong.

**The granted path is driven against the live producer without taking a
lease.**  Acquiring one is the obvious way to observe ``active_lease``
populated, and it would stop ``venture-chat.service`` on a live box and
occupy another repository's queue to do it — a real side effect on shared
infrastructure, taken for a test.  Instead the first hop is *projected
from a real lease row through the producer's own column list*, which is
precisely the transformation ``Arbiter.invariants`` performs, and the
**second hop is the real service answering with real data**.  So the half
that carries ``stopped_units`` — the half the snag got wrong — is never
synthetic.

Skipped, never failed, when 8400 is not running: a box without
estate-manager has no fault of ours to report.
"""

from __future__ import annotations

import httpx
import pytest

from sysadmin.estate.client import (
    ARBITRATION_GRANTED,
    ARBITRATION_IDLE,
    ARBITRATION_UNREAD,
    read_arbitrated_stops,
)

ESTATE_URL = "http://127.0.0.1:8400"

#: Columns ``Arbiter.invariants`` selects for ``active_lease``.
#:
#: Read off the producer's SQL on 2026-08-31 rather than off its prose.
#: ``hold_overdue`` is selected and then popped, so it is deliberately
#: absent here: what reaches the wire is these five.
ACTIVE_LEASE_COLUMNS = ("id", "profile", "requester", "granted_at", "hold_deadline")


def _estate_available() -> bool:
    """True when 8400 answers its health route inside 2 s.

    Mirrors ``tests/test_estate_project_contracts.py::_estate_available``
    — one way to say "this needs a live dependency" in this suite.
    """
    try:
        return httpx.get(f"{ESTATE_URL}/api/health", timeout=2.0).status_code == 200
    except Exception:
        return False


def _a_lease_with_stops() -> dict | None:
    """The newest lease whose ``stopped_units`` names anything.

    Walked downwards from a generous ceiling rather than read from a
    listing, because the estate publishes **no** lease index — only
    ``acquire``, ``release``, ``invariants`` and ``leases/{id}``.  A
    missing id is a 404 and simply not a candidate.
    """
    for lease_id in range(60, 0, -1):
        try:
            response = httpx.get(
                f"{ESTATE_URL}/api/queue/leases/{lease_id}", timeout=2.0
            )
        except Exception:
            return None
        if response.status_code != 200:
            continue
        row = response.json()
        if row.get("stopped_units"):
            return row
    return None


class _ProjectedInvariants(httpx.AsyncBaseTransport):
    """The real transport, with ``/api/queue/invariants`` answered locally.

    Only the first hop is stood in for, and its payload is derived from a
    real row.  Everything else — crucially ``/api/queue/leases/{id}`` —
    goes to the running service.
    """

    def __init__(self, active_lease: dict | None) -> None:
        self._real = httpx.AsyncHTTPTransport()
        self._active_lease = active_lease

    async def handle_async_request(self, request):
        if request.url.path == "/api/queue/invariants":
            response = httpx.Response(
                200, json={"depth": 0, "active_lease": self._active_lease}
            )
            response.request = request
            return response
        return await self._real.handle_async_request(request)


@pytest.mark.skipif(
    not _estate_available(), reason=f"estate-manager ({ESTATE_URL}) unreachable"
)
class TestTheArbiterSeamLive:
    """What the producer actually serves, asked of the producer."""

    @pytest.mark.premise
    def test_the_premise_holds_a_lease_that_stopped_something(self):
        """The anti-vacuity pin, and it runs first for a reason.

        Every assertion below is about a lease naming ``stopped_units``.
        If the estate has none — a fresh database, a retention purge, a
        profile change — the granted-path tests would pass by having
        nothing to check, which is the shape a live half is worst at
        reporting.  This one fails instead, naming the missing premise.
        """
        row = _a_lease_with_stops()
        assert row is not None, (
            "no lease on 8400 names any stopped_units — the granted-path "
            "assertions below would be vacuous"
        )
        assert isinstance(row["stopped_units"], list)
        assert all(isinstance(unit, str) for unit in row["stopped_units"])

    def test_invariants_does_not_publish_stopped_units(self):
        """The snag's founding error, pinned so it cannot be re-filed.

        If the estate ever *does* put the field here, this fails and the
        second hop becomes deletable — which is the good outcome and is
        exactly why it is asserted rather than assumed.  It is stated
        about ``active_lease``'s **key set** when one is granted, and
        about the top-level payload otherwise, so it says something on
        every run rather than only at night.
        """
        payload = httpx.get(f"{ESTATE_URL}/api/queue/invariants", timeout=5.0).json()
        assert "stopped_units" not in payload
        lease = payload.get("active_lease")
        if lease is not None:
            # may-not-evaluate: only a granted lease has a key set to look in,
            # and the queue is idle most of the day.  The assert above this
            # branch is what makes the test say something either way.
            assert "stopped_units" not in lease, (
                "the estate now publishes stopped_units on /invariants — "
                "the second hop in read_arbitrated_stops is now redundant"
            )

    def test_the_active_lease_projection_is_still_five_named_columns(self):
        """The first hop must keep carrying ``id``, or the path breaks.

        A granted lease is the only time this is observable, so the
        assertion is written to say something either way: when one is
        held it checks the real key set, and when none is it checks that
        the field is present and null rather than absent — the shape
        :func:`read_arbitrated_stops` reads as ``idle``.
        """
        payload = httpx.get(f"{ESTATE_URL}/api/queue/invariants", timeout=5.0).json()
        assert "active_lease" in payload
        lease = payload["active_lease"]
        if lease is None:
            return
        # may-not-evaluate: reachable only while the queue holds a granted
        # lease; the idle payload returns above.
        assert set(lease) == set(ACTIVE_LEASE_COLUMNS)
        # may-not-evaluate: the same granted-lease branch as the line above.
        assert isinstance(lease["id"], int) and not isinstance(lease["id"], bool)

    def test_a_released_lease_is_readable_by_id(self):
        """The retrospective half the entry twice said was unreachable.

        ``leases/{id}`` is ``_public(SELECT * …)`` and answers for a
        released lease as readily as a granted one, which is what makes
        the two-call path work at all.
        """
        row = _a_lease_with_stops()
        assert row is not None
        assert row["state"] in ("granted", "released", "expired", "dropped")
        assert "stopped_units" in row

    @pytest.mark.asyncio
    async def test_the_live_estate_reads_cleanly_right_now(self):
        """Whatever the box is doing, the reading is one of the three.

        Deliberately not asserting ``idle``: this suite runs at night
        too, and a test that failed during the nightly hold would fail
        exactly when the feature is working.
        """
        async with httpx.AsyncClient(timeout=5.0) as http:
            stops = await read_arbitrated_stops(http, ESTATE_URL)

        assert stops.reading in (
            ARBITRATION_GRANTED, ARBITRATION_IDLE, ARBITRATION_UNREAD
        )
        assert stops.reading != ARBITRATION_UNREAD, (
            f"8400 answered its health route but not its queue: {stops.error}"
        )
        if stops.reading == ARBITRATION_IDLE:
            assert stops.stopped("venture-chat.service") is False

    @pytest.mark.asyncio
    async def test_the_granted_path_end_to_end_against_the_real_producer(self):
        """The whole point: real ``stopped_units``, through the real route.

        The first hop is projected from the real row exactly as
        ``Arbiter.invariants`` projects it; the second is the live
        service.  So this fails if the estate renames the field, changes
        its type, or stops answering ``leases/{id}`` — none of which any
        fixture in this repository could notice.
        """
        row = _a_lease_with_stops()
        assert row is not None
        projected = {column: row[column] for column in ACTIVE_LEASE_COLUMNS}

        async with httpx.AsyncClient(
            transport=_ProjectedInvariants(projected), timeout=5.0
        ) as http:
            stops = await read_arbitrated_stops(http, ESTATE_URL)

        assert stops.reading == ARBITRATION_GRANTED
        assert stops.lease_id == row["id"]
        assert stops.profile == row["profile"]
        assert stops.units == frozenset(row["stopped_units"])
        for unit in row["stopped_units"]:
            assert stops.stopped(unit) is True
        assert stops.stopped("a-unit-no-lease-will-ever-name.service") is False

    @pytest.mark.asyncio
    async def test_an_estate_that_is_not_there_fails_open_against_a_real_socket(self):
        """Fail-open, against a refused connection rather than a raised stub.

        The recorded half raises ``ConnectError`` from a mock transport,
        which is the exception this code expects to see.  This drives a
        port nothing is listening on, so the failure is produced by the
        network stack — the one shape a hand-written stub cannot get
        wrong in the same direction as the code under test.
        """
        async with httpx.AsyncClient(timeout=2.0) as http:
            stops = await read_arbitrated_stops(http, "http://127.0.0.1:8599")

        assert stops.reading == ARBITRATION_UNREAD
        assert stops.known is False
        assert stops.stopped("venture-chat.service") is False


# ---------------------------------------------------------------------------
# The deployed path, read off the live ``alerts`` table
# ---------------------------------------------------------------------------
#
# Re-homed from ``snag_claims.check_nightly_hold_is_loud``'s limb 1 when
# ``SNAG-AGENT-011`` closed on 2026-09-01 — ``FROZEN_TABLES``' rule, which
# this repository has now spent six times: the check retires with its
# entry and the *detector* does not, or the guard against the defect
# coming back leaves with the last finding of it.
#
# **It is stronger than the check it replaces, and in the axis that
# matters.**  Limb 1 reconstructed a nightly window from
# ``venture-enrich-nightly.timer`` and asked whether the latest observed
# night's row was loud.  That keys the guard on *another project's
# schedule*: the drain moved 02:00 → 00:00 on 2026-08-25 and the window
# moved with it, so a guard shaped that way reports on a population that
# empties whenever the estate re-times its own timer.  These read the
# thing the fix actually writes — ``details['arbitration']`` — so they
# hold whatever hour the drain fires at, and they would witness an
# arbitrated stop of a unit nobody has thought of yet.
#
# **Why a live read at all**, when ``tests/test_arbitrated_stops.py``
# already drives every branch deterministically: a recorded test cannot
# tell a fix that works from a fix that has never executed.  This
# repository has shipped that exact shape — ``_still_open`` carried a
# loop-affinity defect from Session 55 to Session 115 and *never once
# ran* on this box, because a cheap gate returned before reaching it, and
# `SNAG-TRAY-007`'s reminder could not have worked here for a fault the
# daemon had announced.  Only the production table can say the path fired.
#
# Anti-vacuity is the whole discipline here.  A sweep that finds no
# arbitrated row and passes is a constant observation over an empty
# population, which is not evidence — ``a-check-needs-a-discriminating-
# witness``.  So the population is asserted *first*, in its own test, and
# the assertions skip rather than pass when it is empty.


ARBITRATION_KEY = "arbitration"

#: How far back the sweep reaches.  Bounded well inside ``alerts``' 180-day
#: retention and deliberately not tied to the drain's cadence: what is
#: being witnessed is that the deployed code writes the blob at all, and a
#: window spanning two schedules would hold nights no shape can describe.
ARBITRATION_LOOKBACK_DAYS = 30

#: Every ``% unreachable`` row in the window that the deployed fix
#: annotated.  ``severity`` and the blob come back together because the
#: property under test is a *relation* between them — a row's rung is
#: judged against its own reading and never against the table's.
ARBITRATED_ROWS_SQL = f"""
    SELECT title,
           severity,
           details -> '{ARBITRATION_KEY}' ->> 'reading'   AS reading,
           details -> '{ARBITRATION_KEY}' ->> 'stopped_by_estate' AS stopped,
           created_at
    FROM sysadmin.alerts
    WHERE title LIKE '%% unreachable'
      AND details ? '{ARBITRATION_KEY}'
      AND created_at > now() - interval '{ARBITRATION_LOOKBACK_DAYS} days'
    ORDER BY created_at DESC
"""


def _db_available() -> bool:
    """True when the live ``projects`` database answers inside 2 s.

    ``tests/test_message_backfill_live.py::_db_available``'s shape — one
    way to say "this needs the real table" in this suite.
    """
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


def _arbitrated_rows() -> list:
    """Annotated ``% unreachable`` rows off the live table, newest first."""
    from sqlalchemy import create_engine, text

    engine = create_engine("postgresql+psycopg2://gaddi@localhost:5432/projects")
    try:
        with engine.connect() as conn:
            return list(conn.execute(text(ARBITRATED_ROWS_SQL)).fetchall())
    finally:
        engine.dispose()


@pytest.mark.skipif(not _db_available(), reason="live projects database unreachable")
class TestTheDeployedQuieteningLive:
    """What the running daemon actually wrote, asked of ``alerts``."""

    def test_the_deployed_path_has_annotated_at_least_one_row(self):
        """The anti-vacuity pin, and it runs first for a reason.

        Every assertion below is satisfied by an empty table.  A green
        class over no rows says only that the daemon has not raised a
        ``% unreachable`` row since the fix deployed — which is a fact
        about the box's health, never evidence about the fix.  This test
        is what separates the two, and it *fails* rather than skips: a
        box that has gone a month without one arbitrated row has either
        stopped swapping the unit or stopped monitoring it, and both are
        worth a red rather than a silent pass.
        """
        rows = _arbitrated_rows()
        assert rows, (
            "no '% unreachable' row in the last "
            f"{ARBITRATION_LOOKBACK_DAYS} days carries details['{ARBITRATION_KEY}'] — "
            "either the daemon predates SNAG-AGENT-011's fix, or nothing has been "
            "unreachable since it deployed; the assertions below are vacuous until "
            "one exists"
        )

    def test_an_arbitrated_stop_is_never_loud(self):
        """The defect, asked of production rather than of a stand-in.

        ``stopped_by_estate`` true is the estate's own record that it
        stopped the unit under a granted lease, which is the one case
        ``critical`` must not describe.  Scoped to that flag rather than
        to a service name for the check's own rule 1: what the entry
        claimed is a *mechanism*, and keying on ``venture-chat`` would go
        blind the day the estate swaps something else.
        """
        arbitrated = [row for row in _arbitrated_rows() if row.stopped == "true"]
        if not arbitrated:
            pytest.skip("no arbitrated stop in the window")
        loud = [
            (row.title, row.severity, row.created_at)
            for row in arbitrated
            if row.severity == "critical"
        ]
        assert not loud, f"arbitrated stops announced at critical: {loud}"

    def test_a_row_the_estate_could_not_explain_is_left_alone(self):
        """Fail-open, witnessed rather than assumed.

        The quietening must never become a suppression: a reading of
        ``unread`` is an unreachable 8400, and ``_attribution``'s rule —
        *the enrichment is not allowed to become a dependency of the
        alert* — says the rung stays where it was.  So this asserts the
        **absence of a quietening**, which is the direction a fix of this
        shape fails in.  Empty population on a healthy box, and that is
        the point of stating it: the day it is not empty, the row must
        still be loud.
        """
        unexplained = [row for row in _arbitrated_rows() if row.stopped != "true"]
        if not unexplained:
            pytest.skip("the estate answered on every raise in the window")
        quietened = [
            (row.title, row.severity, row.reading)
            for row in unexplained
            if row.severity == "info"
        ]
        assert not quietened, (
            f"rows quietened without the estate claiming the stop: {quietened}"
        )

    def test_every_annotated_row_carries_a_reading_this_release_knows(self):
        """The blob is a vocabulary, not free text.

        A reading this checkout cannot name is a producer or a predecessor
        writing a shape nothing here classifies, and ``is_fault``'s rule
        applies at the size of a dict value: a monitor going quiet about a
        state it does not understand is worse than a false alarm.  Pinned
        against ``estate.client``'s own constants rather than string
        literals — ``max_priority_for`` against ``PRIORITY_MAP``.
        """
        known = {ARBITRATION_GRANTED, ARBITRATION_IDLE, ARBITRATION_UNREAD}
        strange = {
            row.reading for row in _arbitrated_rows() if row.reading not in known
        }
        assert not strange, f"readings this release cannot classify: {sorted(strange)}"
