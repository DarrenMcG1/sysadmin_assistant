"""The estate's arbiter, consulted by the service family (SNAG-AGENT-011).

Two halves, deliberately in one file because they are one seam.
:class:`TestReadArbitratedStops` drives the transport in
:mod:`sysadmin.estate.client` against an ``httpx.MockTransport``, and
:class:`TestTheRungIsQuietenedInPlace` drives the verdict in
:mod:`sysadmin.monitor.agent`.

**Every failure path is a test rather than a comment**, because the
whole contract of this feature is what happens when it does not work.
An enrichment that becomes a dependency of the alert would silence every
service outage on this box the day 8400 goes down —
``EstateJudgeAgent._attribution``'s stated rule — and the only thing
standing between that and this code is that ``stopped()`` answers
``False`` for every way of not-knowing.
"""

from __future__ import annotations

import httpx
import pytest

from sysadmin.estate import client as estate_client
from sysadmin.estate.client import (
    ARBITRATION_GRANTED,
    ARBITRATION_IDLE,
    ARBITRATION_UNREAD,
    ArbitratedStops,
    read_arbitrated_stops,
)

BASE = "http://localhost:8400"

#: A granted lease as the live producer serves it on ``/api/queue/invariants``.
#:
#: Five keys and **no** ``stopped_units`` — captured from
#: ``Arbiter.invariants``, which selects an explicit column list and pops
#: ``hold_overdue`` before returning.  Written out rather than trimmed
#: from a lease row, because the whole reason this feature needs two
#: calls is that these two payloads differ, and a fixture derived from
#: one cannot witness that.
ACTIVE_LEASE = {
    "id": 35,
    "profile": "venture-nightly-24b",
    "requester": "venture-drain",
    "granted_at": "2026-08-31T00:00:03.375097+01:00",
    "hold_deadline": "2026-08-31T07:15:03.375097+01:00",
}

#: Lease 30 as ``GET /api/queue/leases/30`` really served it on 2026-08-31.
LEASE_ROW = {
    "id": 35,
    "profile": "venture-nightly-24b",
    "requester": "venture-drain",
    "state": "granted",
    "requested_at": "2026-08-31T00:00:00.663843+01:00",
    "wait_deadline": "2026-08-31T02:00:00.663843+01:00",
    "max_hold_seconds": 26100,
    "granted_at": "2026-08-31T00:00:03.375097+01:00",
    "hold_deadline": "2026-08-31T07:15:03.375097+01:00",
    "finished_at": None,
    "stopped_units": ["venture-chat.service"],
    "started_units": ["venture-chat-large.service"],
    "detail": None,
}


def _client(routes: dict[str, object]) -> httpx.AsyncClient:
    """A client answering by path, 404ing anything the test did not declare.

    404 rather than a default payload: a test that reaches an unexpected
    path should fail on that, not be quietly served something plausible.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        answer = routes.get(request.url.path)
        if answer is None:
            return httpx.Response(404, json={"detail": request.url.path})
        if isinstance(answer, httpx.Response):
            return answer
        return httpx.Response(200, json=answer)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestReadArbitratedStops:
    """The two-call path, and every way it can decline to answer."""

    @pytest.mark.asyncio
    async def test_a_granted_lease_yields_its_stopped_units(self):
        """The happy path, and the only one that can quieten anything."""
        async with _client({
            "/api/queue/invariants": {"depth": 0, "active_lease": ACTIVE_LEASE},
            "/api/queue/leases/35": LEASE_ROW,
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_GRANTED
        assert stops.stopped("venture-chat.service") is True
        assert stops.lease_id == 35
        assert stops.profile == "venture-nightly-24b"
        assert stops.known is True

    @pytest.mark.asyncio
    async def test_a_unit_the_lease_does_not_name_is_not_stopped(self):
        """The discriminator has to discriminate.

        ``venture-embed`` sits beside ``venture-chat`` in
        ``services.yaml``, on the same box, under the same project, and
        the arbiter does **not** touch it.  Without this the feature
        would quieten every outage on the box for as long as any lease
        was held — which is ``mute_services`` with extra steps, the
        remedy the entry explicitly refuses.
        """
        async with _client({
            "/api/queue/invariants": {"active_lease": ACTIVE_LEASE},
            "/api/queue/leases/35": LEASE_ROW,
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.stopped("venture-embed.service") is False
        assert stops.stopped(None) is False

    @pytest.mark.asyncio
    async def test_no_active_lease_is_idle_and_not_unread(self):
        """Every daytime read. A real fact, not a failure.

        ``active_lease: null`` is what ``GET /api/queue/invariants``
        returned on every read taken while building this — the estate
        answered, and it holds nothing.  Collapsing it into ``unread``
        would make a healthy estate indistinguishable from a dead one in
        ``details['arbitration']``.
        """
        async with _client({
            "/api/queue/invariants": {"depth": 0, "active_lease": None},
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_IDLE
        assert stops.known is True
        assert stops.stopped("venture-chat.service") is False

    @pytest.mark.asyncio
    async def test_an_unreachable_estate_is_unread_and_stops_nothing(self):
        """Fail open. The single most important assertion in this file.

        If this inverts, an 8400 outage silences every service outage on
        the box — the enrichment having become a dependency of the alert.
        """
        async def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(refuse)
        ) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_UNREAD
        assert stops.known is False
        assert stops.stopped("venture-chat.service") is False
        assert stops.error is not None and "ConnectError" in stops.error

    @pytest.mark.asyncio
    async def test_the_second_hop_failing_is_unread_and_names_the_lease(self):
        """The first call can succeed and the second still fail.

        Two calls means two independent failures, and the one that is
        easy to get wrong is this one: the id is in hand, so the code has
        every temptation to report something.  It reports ``unread`` and
        carries the id, which is what a human needs to run the call by
        hand.
        """
        async with _client({
            "/api/queue/invariants": {"active_lease": ACTIVE_LEASE},
            # /api/queue/leases/35 deliberately absent -> 404
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_UNREAD
        assert stops.stopped("venture-chat.service") is False
        assert stops.lease_id == 35
        assert stops.profile == "venture-nightly-24b"

    @pytest.mark.asyncio
    async def test_a_lease_that_stops_nothing_is_granted_with_no_units(self):
        """The estate's own ``estate-review`` profile is declared this way.

        Read, and the answer is "none" — which is not the same as
        unread, and must not be, or a no-swap lease would leave the
        reading looking like an outage of 8400.
        """
        async with _client({
            "/api/queue/invariants": {"active_lease": ACTIVE_LEASE},
            "/api/queue/leases/35": {**LEASE_ROW, "stopped_units": None},
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_GRANTED
        assert stops.known is True
        assert stops.stopped("venture-chat.service") is False

    @pytest.mark.asyncio
    async def test_a_malformed_stopped_units_is_unread_not_empty(self):
        """``ports_checked``'s rule: blind is never served as clean.

        A list is the contract.  A string is a contract break this
        repository cannot interpret, and interpreting it as "nothing was
        stopped" is the one reading that is silently wrong.
        """
        async with _client({
            "/api/queue/invariants": {"active_lease": ACTIVE_LEASE},
            "/api/queue/leases/35": {**LEASE_ROW, "stopped_units": "venture-chat"},
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_UNREAD
        assert stops.known is False

    @pytest.mark.asyncio
    async def test_a_boolean_lease_id_is_refused_rather_than_formatted(self):
        """``isinstance(True, int)`` is ``True``.

        ``judge_audit_findings`` rule 4's guard, for its reason.  A bool
        formatted into the path yields ``/api/queue/leases/True``, whose
        422 would read as an unreachable estate — a contract break
        reported as somebody else's outage.
        """
        async with _client({
            "/api/queue/invariants": {"active_lease": {**ACTIVE_LEASE, "id": True}},
        }) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert stops.reading == ARBITRATION_UNREAD
        assert stops.lease_id is None
        assert stops.error is not None and "bool" in stops.error

    @pytest.mark.asyncio
    async def test_it_asks_for_the_lease_the_invariants_named(self):
        """The id is *used*, not merely read.

        Falsifies an implementation that reads ``active_lease`` and then
        fetches a hard-coded or most-recent lease — which would pass
        every assertion above, since the fixture serves one lease.
        """
        asked: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            asked.append(request.url.path)
            if request.url.path == "/api/queue/invariants":
                return httpx.Response(
                    200, json={"active_lease": {**ACTIVE_LEASE, "id": 41}}
                )
            return httpx.Response(200, json={**LEASE_ROW, "id": 41})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http:
            stops = await read_arbitrated_stops(http, BASE)

        assert asked == ["/api/queue/invariants", "/api/queue/leases/41"]
        assert stops.lease_id == 41

    def test_the_lease_path_is_not_a_pull_surface(self):
        """It takes a parameter, so it cannot live in ``SURFACE_PATHS``.

        Stated as a test because the tempting tidy-up is to add it there,
        and every surface-keyed consumer — the judgement functions,
        ``agent_runs.details``, the sweep's title-pattern selection —
        would gain a sixth member it must then learn to skip.
        """
        assert "/api/queue/leases" not in str(estate_client.SURFACE_PATHS)
        assert "{lease_id}" in estate_client.LEASE_PATH
        assert len(estate_client.SURFACES) == len(estate_client.SURFACE_PATHS)


class TestTheReadingIsFailOpenByShape:
    """Failing open is a property of the data, not a branch."""

    @pytest.mark.parametrize("reading", [ARBITRATION_IDLE, ARBITRATION_UNREAD])
    def test_only_a_granted_reading_can_carry_units(self, reading):
        """The constructor is not what enforces this — the fetch is.

        This asserts the *invariant the fetch maintains*: no code path
        outside ``granted`` populates ``units``.  It is written as a
        statement about the class so that a future fourth reading has to
        confront it, rather than as another assertion buried in a fetch
        test.
        """
        stops = ArbitratedStops(reading=reading)
        assert stops.units == frozenset()
        assert stops.stopped("anything.service") is False

    def test_stopped_is_false_for_every_reading_that_is_not_granted(self):
        for reading in (ARBITRATION_IDLE, ARBITRATION_UNREAD):
            assert ArbitratedStops(reading=reading).stopped("x.service") is False


# --- The verdict half ---------------------------------------------------

from unittest.mock import AsyncMock, patch  # noqa: E402

from sysadmin.monitor.agent import (  # noqa: E402
    ARBITRATED_STOP_SEVERITY,
    SysAdminAgent,
)
from sysadmin.monitor.services import ServiceEntry  # noqa: E402


@pytest.fixture
def agent():
    return SysAdminAgent()


@pytest.fixture
def chat():
    """``venture-chat`` as ``services.yaml`` really declares it."""
    return ServiceEntry(
        name="venture-chat",
        kind="http",
        url="http://localhost:8080/health",
        port=8080,
        systemd={"unit": "venture-chat.service", "scope": "user"},
    )


def _granted(units=("venture-chat.service",)) -> ArbitratedStops:
    return ArbitratedStops(
        reading=ARBITRATION_GRANTED,
        units=frozenset(units),
        lease_id=35,
        profile="venture-nightly-24b",
    )


class TestTheRungIsQuietenedInPlace:
    """SNAG-AGENT-011's whole point: the row is right, the rung is not."""

    @pytest.mark.asyncio
    async def test_an_arbitrated_stop_is_quietened(
        self, agent, mock_session, chat
    ):
        agent._arbitration = _granted()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            alerts = await agent._handle_status(
                mock_session, chat, "unreachable", {"error": "connection refused"}
            )

        assert alerts == 1
        assert ra.call_args.kwargs["severity"] == ARBITRATED_STOP_SEVERITY

    @pytest.mark.asyncio
    async def test_the_row_is_still_written_and_keeps_its_title(
        self, agent, mock_session, chat
    ):
        """A quietening, never a suppression — ``known_noise`` rule 2.

        The title is load-bearing twice over: it is the dedup key, and it
        is what keeps the row inside ``% unreachable`` so
        ``_resolve_recovered`` still closes it when the lease releases.
        A fix that forked the title to mark the row would strand it open
        for ever, which is the defect that put 6,283 ``redis
        unreachable`` rows in this table.
        """
        agent._arbitration = _granted()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, chat, "unreachable", {})

        assert ra.call_args.kwargs["title"] == "venture-chat unreachable"

    @pytest.mark.asyncio
    async def test_an_unrelated_service_stays_critical_under_the_same_lease(
        self, agent, mock_session
    ):
        """The lease quietens the unit it names, not the box.

        ``venture-embed`` is the same project on the same host under the
        same lease.  If this goes quiet the fix has become
        ``mute_services`` with extra steps.
        """
        embed = ServiceEntry(
            name="venture-embed", kind="http", url="http://localhost:8082/health",
            systemd={"unit": "venture-embed.service", "scope": "user"},
        )
        agent._arbitration = _granted()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, embed, "unreachable", {})

        assert ra.call_args.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "reading",
        [ARBITRATION_IDLE, ARBITRATION_UNREAD],
    )
    async def test_an_unreadable_or_idle_estate_leaves_the_rung_at_critical(
        self, agent, mock_session, chat, reading
    ):
        """Fail open, at the surface the operator actually feels.

        The transport half asserts ``stopped()`` is ``False``; this
        asserts the *consequence* — that a dead 8400 does not silence a
        real outage.  Two tests because a future implementation could
        keep the reading correct and still special-case the rung.
        """
        agent._arbitration = ArbitratedStops(reading=reading)
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, chat, "unreachable", {})

        assert ra.call_args.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_a_run_that_never_asked_leaves_the_rung_at_critical(
        self, agent, mock_session, chat
    ):
        """``_arbitration`` is ``None`` until something asks.

        The default must fail open too — this is the state every run
        starts in, so an implementation that read ``None`` as "nothing is
        stopped, carry on" would be correct here and an implementation
        that read it as truthy would silence everything.
        """
        assert agent._arbitration is None
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, chat, "unreachable", {})

        assert ra.call_args.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_every_row_records_what_the_run_knew(
        self, agent, mock_session, chat
    ):
        """Uniform on every row of the family, not only the quiet one.

        Session 128's rule for ``details['attribution']``: a key present
        only sometimes collapses "we asked and the answer was no" into
        "nobody asked", which is the distinction the whole block turns
        on.  So the *value* carries the news.
        """
        agent._arbitration = ArbitratedStops(reading=ARBITRATION_IDLE)
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, chat, "unreachable", {})

        arb = ra.call_args.kwargs["details"]["arbitration"]
        assert arb["reading"] == ARBITRATION_IDLE
        assert arb["stopped_by_estate"] is False
        assert arb["unit"] == "venture-chat.service"

    @pytest.mark.asyncio
    async def test_the_quiet_row_names_the_lease_that_caused_it(
        self, agent, mock_session, chat
    ):
        """``alert.message`` reaches a notification body verbatim.

        A row that has been quietened without saying why is a row whose
        reader cannot check the claim — and the lease id is exactly what
        makes ``GET :8400/api/queue/leases/{id}`` runnable by hand.
        """
        agent._arbitration = _granted()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, chat, "unreachable", {})

        message = ra.call_args.kwargs["message"]
        assert "venture-chat is unreachable" in message
        assert "35" in message and "venture-nightly-24b" in message

        details = ra.call_args.kwargs["details"]["arbitration"]
        assert details["lease_id"] == 35
        assert details["stopped_by_estate"] is True

    @pytest.mark.asyncio
    async def test_a_service_with_no_unit_cannot_be_arbitrated(
        self, agent, mock_session
    ):
        """``internet`` has no unit, so nothing can have stopped it.

        The reading is still recorded — the run *did* ask — which is why
        this is not simply the unread case again.
        """
        internet = ServiceEntry(
            name="internet", kind="http", url="https://example.invalid/",
        )
        agent._arbitration = _granted()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, internet, "unreachable", {})

        assert ra.call_args.kwargs["severity"] == "critical"
        arb = ra.call_args.kwargs["details"]["arbitration"]
        assert arb["unit"] is None
        assert arb["reading"] == ARBITRATION_GRANTED


class TestTheEstateIsAskedOncePerRun:
    """The snag's cost figure was wrong, and the memo is why it is now right."""

    @pytest.mark.asyncio
    async def test_the_second_call_is_not_repeated_within_a_run(self, agent):
        """``_raise_judged`` is entered on **every** poll for a standing
        fault — it suppresses the row, not the call — so a read wired at
        the raise would fire every 300 s for six hours a night.  The
        entry priced it at "once per incident" off the 23 post-dedup
        rows, which is the wrong denominator.
        """
        calls = 0

        async def counting(http, base_url):
            nonlocal calls
            calls += 1
            return _granted()

        with patch.object(
            estate_client, "read_arbitrated_stops", side_effect=counting
        ):
            await agent._ensure_arbitration()
            await agent._ensure_arbitration()
            await agent._ensure_arbitration()

        assert calls == 1
        assert agent._arbitration is not None

    @pytest.mark.asyncio
    async def test_a_new_run_asks_again(self, agent):
        """The memo is per run, and a lease that ended must not be believed.

        ``_execute`` resets it; this asserts the reset exists rather than
        that ``_execute`` was called, because a long-lived memo would
        keep a released lease quietening a genuine outage for the life of
        the daemon.
        """
        import ast
        import inspect

        source = inspect.getsource(SysAdminAgent._execute)
        tree = ast.parse(source.lstrip())
        resets = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Attribute) and t.attr == "_arbitration"
                for t in node.targets
            )
            and isinstance(node.value, ast.Constant)
            and node.value.value is None
        ]
        assert resets, "_execute must reset _arbitration to None each run"

    @pytest.mark.asyncio
    async def test_the_estate_is_never_read_inside_a_savepoint(self, agent):
        """Two HTTP hops at 10 s each, inside ``begin_nested()``, on a host
        with ``idle_in_transaction_session_timeout=1min``, is
        SNAG-AGENT-003 rebuilt inside the fix for something else.

        Asserted at the source, because the failure is a *timeout under
        load* that no fixture reproduces: the call must appear before the
        ``async with session.begin_nested()`` block, not within it.
        """
        import ast
        import inspect
        import textwrap

        tree = ast.parse(textwrap.dedent(inspect.getsource(SysAdminAgent._execute)))
        offenders = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncWith):
                continue
            if "begin_nested" not in ast.dump(node.items[0].context_expr):
                continue
            for inner in ast.walk(node):
                if (
                    isinstance(inner, ast.Attribute)
                    and inner.attr == "_ensure_arbitration"
                ):
                    offenders.append(ast.dump(inner))
        assert not offenders, (
            "_ensure_arbitration must not be awaited inside the per-service "
            "savepoint — it holds a transaction open across two HTTP calls"
        )
