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
        assert set(lease) == set(ACTIVE_LEASE_COLUMNS)
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
