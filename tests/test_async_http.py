"""Cross-event-loop regression tests for shared httpx clients.

SNAG-AGENT-003: agents run on APScheduler threads, each job bridged into
its own event loop by ``asyncio.run()`` — which *closes* that loop when
the job returns.  An ``httpx.AsyncClient`` created once during the FastAPI
lifespan therefore hands out pooled keep-alive connections belonging to a
dead loop, and reusing one raises ``RuntimeError: Event loop is closed``.

These tests deliberately use a real loopback HTTP server rather than
``httpx.MockTransport``: the bug lives in the *socket* the connection pool
keeps, and a mock transport holds no sockets, so it cannot reproduce it.
Every test that matters here drives two successive ``asyncio.run()`` calls,
mirroring two consecutive scheduler runs — a single-loop test passes even
against the broken code.
"""

import asyncio
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import MonitoredService
from sysadmin.monitor.agent import SysAdminAgent


class _KeepAliveHandler(BaseHTTPRequestHandler):
    """HTTP/1.1 so responses are keep-alive and the pool retains the socket."""

    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
        body = b'{"status": "ok"}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args) -> None:
        """Silence the default stderr access log."""


@pytest.fixture(scope="module")
def health_url():
    """A real loopback HTTP server that keeps connections alive."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _KeepAliveHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/health"
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# The bug itself
# ---------------------------------------------------------------------------


class TestCrossLoopReuse:
    def test_naively_shared_client_dies_on_the_second_loop(self, health_url):
        """Guard the guard.

        Proves this harness really does reproduce the original failure —
        otherwise the tests below could pass for the wrong reason.
        """
        client = httpx.AsyncClient(timeout=5.0)

        async def probe() -> int:
            return (await client.get(health_url)).status_code

        assert asyncio.run(probe()) == 200  # loop 1 pools a live connection
        with pytest.raises(RuntimeError, match="Event loop is closed"):
            asyncio.run(probe())  # loop 2 tries to reuse it

    def test_loop_bound_client_survives_successive_loops(self, health_url):
        """The same shape, through LoopBoundClient: every run succeeds."""
        holder = LoopBoundClient(lambda: httpx.AsyncClient(timeout=5.0))

        async def open_and_probe() -> int:
            # Stands in for the FastAPI lifespan opening a shared client.
            await holder.open()
            async with holder.borrow() as client:
                return (await client.get(health_url)).status_code

        async def probe() -> int:
            # Stands in for a later scheduler run on a brand-new loop.
            async with holder.borrow() as client:
                return (await client.get(health_url)).status_code

        assert asyncio.run(open_and_probe()) == 200
        assert asyncio.run(probe()) == 200
        assert asyncio.run(probe()) == 200

    def test_borrow_reuses_the_client_on_its_own_loop(self, health_url):
        """Loop affinity must not cost connection pooling within a run."""

        async def scenario() -> None:
            holder = LoopBoundClient(lambda: httpx.AsyncClient(timeout=5.0))
            opened = await holder.open()
            async with holder.borrow() as first, holder.borrow() as second:
                assert first is opened
                assert second is opened
            await holder.close()

        asyncio.run(scenario())

    def test_scoped_closes_its_client_and_restores_the_previous_one(self):
        async def scenario() -> None:
            holder = LoopBoundClient(lambda: httpx.AsyncClient(timeout=5.0))
            async with holder.scoped() as client:
                assert holder.client is client
                assert not client.is_closed
            assert client.is_closed
            assert holder.client is None

        asyncio.run(scenario())

    def test_close_forgets_a_client_belonging_to_a_dead_loop(self, health_url):
        """Shutting down after the owning loop is gone must not explode."""
        holder = LoopBoundClient(lambda: httpx.AsyncClient(timeout=5.0))

        asyncio.run(holder.open())
        assert holder.client is not None

        asyncio.run(holder.close())
        assert holder.client is None


# ---------------------------------------------------------------------------
# The agent, driven the way APScheduler drives it
# ---------------------------------------------------------------------------


class TestAgentHttpCheckAcrossRuns:
    def test_consecutive_runs_both_report_ok(self, health_url):
        """Two scheduler runs in a row, each with its own closed-after loop.

        Before the fix the second run returned ("unreachable", {"error":
        "Event loop is closed"}) for whichever host still had a pooled
        connection — exactly what /api/sysadmin/status showed for
        llama-server while curl was answering in under a millisecond.
        """
        agent = SysAdminAgent()
        svc = MonitoredService(name="probe", type="http", url=health_url)

        async def one_run() -> tuple[str, int | None, dict]:
            # Mirrors _execute(): a run-scoped client on this run's loop.
            async with agent._http.scoped():
                return await agent._check_http(svc)

        first_status, _, first_details = asyncio.run(one_run())
        second_status, _, second_details = asyncio.run(one_run())

        assert first_status == "ok", first_details
        assert second_status == "ok", second_details

    def test_check_works_with_no_run_scope_at_all(self, health_url):
        """A check outside a run builds and closes its own client."""
        agent = SysAdminAgent()
        svc = MonitoredService(name="probe", type="http", url=health_url)

        assert asyncio.run(agent._check_http(svc))[0] == "ok"
        assert asyncio.run(agent._check_http(svc))[0] == "ok"
        assert agent._http.client is None
