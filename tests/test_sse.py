"""Tests for the Server-Sent Events stream (GET /api/sysadmin/events).

Covers the broadcaster fan-out, the wire format, heartbeats, and — against
the REAL app — connect / receive one event / disconnect without leaking a
subscriber.

The route is driven through the ASGI interface directly rather than
``httpx.ASGITransport``: that transport buffers the whole response body
before returning, which never happens for an endless stream.
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from sysadmin.core.contracts import EventMessage
from sysadmin.core.event_bus import EventBus
from sysadmin.monitor.sse import (
    HEARTBEAT,
    STREAMED_EVENTS,
    Event,
    EventBroadcaster,
    event_broadcaster,
    event_stream,
    format_sse,
)

EVENTS_PATH = "/api/sysadmin/events"


# ---------------------------------------------------------------------------
# Raw ASGI client for streaming responses
# ---------------------------------------------------------------------------


class SSEConnection:
    """A live ASGI request whose response body arrives in chunks."""

    def __init__(self, sent: asyncio.Queue, to_app: asyncio.Queue, task: asyncio.Task):
        self._sent = sent
        self._to_app = to_app
        self._task = task
        self.start_message: dict = {}

    @property
    def headers(self) -> dict[str, str]:
        return {
            k.decode().lower(): v.decode()
            for k, v in self.start_message.get("headers", [])
        }

    @property
    def status_code(self) -> int:
        return self.start_message["status"]

    async def next_chunk(self, timeout: float = 2.0) -> str:
        message = await asyncio.wait_for(self._sent.get(), timeout=timeout)
        assert message["type"] == "http.response.body"
        return message["body"].decode()

    async def next_event(self, timeout: float = 2.0) -> dict:
        """Read chunks until a real event frame (not a heartbeat) arrives."""
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            chunk = await self.next_chunk(timeout=max(remaining, 0.01))
            if chunk.startswith(":"):
                continue  # heartbeat comment
            return parse_sse_frame(chunk)

    async def disconnect(self) -> None:
        await self._to_app.put({"type": "http.disconnect"})
        with contextlib.suppress(asyncio.TimeoutError, asyncio.CancelledError):
            await asyncio.wait_for(asyncio.shield(self._task), timeout=2.0)


def parse_sse_frame(chunk: str) -> dict:
    """Parse one ``text/event-stream`` frame into its fields."""
    frame: dict = {"data": None, "event": None, "retry": None}
    for line in chunk.strip().splitlines():
        field, _, value = line.partition(":")
        value = value.strip()
        if field == "data":
            frame["data"] = json.loads(value)
        elif field in ("event", "retry"):
            frame[field] = value
    return frame


@asynccontextmanager
async def sse_request(app, path: str = EVENTS_PATH) -> AsyncIterator[SSEConnection]:
    """Open a streaming request against an ASGI app; always disconnects."""
    to_app: asyncio.Queue = asyncio.Queue()
    sent: asyncio.Queue = asyncio.Queue()
    await to_app.put({"type": "http.request", "body": b"", "more_body": False})

    async def receive() -> dict:
        return await to_app.get()

    async def send(message: dict) -> None:
        await sent.put(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"testserver"), (b"accept", b"text/event-stream")],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }

    task = asyncio.create_task(app(scope, receive, send))
    connection = SSEConnection(sent, to_app, task)

    try:
        start = await asyncio.wait_for(sent.get(), timeout=2.0)
        assert start["type"] == "http.response.start"
        connection.start_message = start
        yield connection
    finally:
        await connection.disconnect()


# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------


class TestFormatSse:
    def test_frame_has_event_and_data_lines(self):
        frame = format_sse("alert.raised", {"id": "abc"})
        assert frame.startswith("event: alert.raised\n")
        assert 'data: {"id": "abc"}' in frame
        assert frame.endswith("\n\n")  # frames must be blank-line terminated

    def test_retry_hint_is_emitted_first(self):
        frame = format_sse("connected", {}, retry_ms=5000)
        assert frame.splitlines()[0] == "retry: 5000"

    def test_data_is_single_line_json(self):
        frame = format_sse("agent.run", {"nested": {"a": 1}, "list": [1, 2]})
        data_lines = [ln for ln in frame.splitlines() if ln.startswith("data:")]
        assert len(data_lines) == 1

    def test_non_serialisable_values_do_not_raise(self):
        from datetime import UTC, datetime

        frame = format_sse("agent.run", {"at": datetime.now(UTC)})
        assert "data:" in frame

    def test_heartbeat_is_a_comment(self):
        assert HEARTBEAT.startswith(":")
        assert HEARTBEAT.endswith("\n\n")


# ---------------------------------------------------------------------------
# Broadcaster
# ---------------------------------------------------------------------------


class TestBroadcaster:
    @pytest.mark.asyncio
    async def test_subscribe_registers_and_unregisters(self):
        broadcaster = EventBroadcaster()
        assert broadcaster.subscriber_count == 0

        async with broadcaster.subscribe():
            assert broadcaster.subscriber_count == 1

        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_unregisters_even_when_the_consumer_raises(self):
        broadcaster = EventBroadcaster()
        with pytest.raises(RuntimeError):
            async with broadcaster.subscribe():
                raise RuntimeError("client vanished")
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_event_reaches_every_subscriber(self):
        broadcaster = EventBroadcaster()
        async with broadcaster.subscribe() as first, broadcaster.subscribe() as second:
            broadcaster.dispatch(Event("alert.raised", {"id": "1"}))

            assert (await first.get()).data == {"id": "1"}
            assert (await second.get()).data == {"id": "1"}

    @pytest.mark.asyncio
    async def test_bus_events_are_forwarded(self):
        bus = EventBus()
        broadcaster = EventBroadcaster()
        broadcaster.attach(bus)

        async with broadcaster.subscribe() as queue:
            await bus.publish("alert.raised", {"title": "High RAM"})

            event = await queue.get()
            assert event.type == "alert.raised"
            assert event.data == {"title": "High RAM"}

    @pytest.mark.asyncio
    async def test_unstreamed_event_types_are_ignored(self):
        bus = EventBus()
        broadcaster = EventBroadcaster()
        broadcaster.attach(bus)

        async with broadcaster.subscribe() as queue:
            await bus.publish("internal.thing", {"x": 1})
            assert queue.empty()

    def test_attach_is_idempotent(self):
        bus = EventBus()
        broadcaster = EventBroadcaster()
        broadcaster.attach(bus)
        broadcaster.attach(bus)

        assert len(bus._subscribers["alert.raised"]) == 1

    def test_all_streamed_types_are_subscribed(self):
        bus = EventBus()
        EventBroadcaster().attach(bus)
        for event_type in STREAMED_EVENTS:
            assert bus._subscribers[event_type]

    @pytest.mark.asyncio
    async def test_slow_client_loses_oldest_events_not_newest(self):
        broadcaster = EventBroadcaster()
        async with broadcaster.subscribe(max_queue=2) as queue:
            broadcaster.dispatch(Event("agent.run", {"n": 1}))
            broadcaster.dispatch(Event("agent.run", {"n": 2}))
            broadcaster.dispatch(Event("agent.run", {"n": 3}))

            assert queue.qsize() == 2
            assert (await queue.get()).data == {"n": 2}
            assert (await queue.get()).data == {"n": 3}

    @pytest.mark.asyncio
    async def test_dispatch_without_subscribers_is_a_noop(self):
        EventBroadcaster().dispatch(Event("agent.run", {}))


# ---------------------------------------------------------------------------
# event_stream generator
# ---------------------------------------------------------------------------


class TestEventStream:
    @pytest.mark.asyncio
    async def test_first_frame_is_the_connected_event(self):
        broadcaster = EventBroadcaster()
        stream = event_stream(broadcaster, heartbeat_seconds=5, retry_ms=1234)

        frame = parse_sse_frame(await anext(stream))
        await stream.aclose()

        assert frame["event"] == "connected"
        assert frame["retry"] == "1234"
        assert frame["data"]["event"] == "connected"

    @pytest.mark.asyncio
    async def test_idle_stream_emits_heartbeats(self):
        broadcaster = EventBroadcaster()
        stream = event_stream(broadcaster, heartbeat_seconds=0.01, retry_ms=1000)

        await anext(stream)  # connected
        assert await anext(stream) == HEARTBEAT
        assert await anext(stream) == HEARTBEAT

        await stream.aclose()

    @pytest.mark.asyncio
    async def test_published_event_is_streamed(self):
        broadcaster = EventBroadcaster()
        stream = event_stream(broadcaster, heartbeat_seconds=5, retry_ms=1000)

        await anext(stream)  # connected
        broadcaster.dispatch(Event("alert.raised", {"title": "Disk full"}))

        frame = parse_sse_frame(await anext(stream))
        await stream.aclose()

        assert frame["event"] == "alert.raised"
        assert frame["data"]["data"] == {"title": "Disk full"}

    @pytest.mark.asyncio
    async def test_closing_the_stream_unsubscribes(self):
        broadcaster = EventBroadcaster()
        stream = event_stream(broadcaster, heartbeat_seconds=5, retry_ms=1000)

        await anext(stream)
        assert broadcaster.subscriber_count == 1

        await stream.aclose()
        assert broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_payload_matches_the_shared_contract(self):
        broadcaster = EventBroadcaster()
        stream = event_stream(broadcaster, heartbeat_seconds=5, retry_ms=1000)

        await anext(stream)
        broadcaster.dispatch(Event("agent.run", {"agent": "sysadmin"}))
        frame = parse_sse_frame(await anext(stream))
        await stream.aclose()

        message = EventMessage.from_dict(frame["data"])
        assert message.event == "agent.run"
        assert message.data == {"agent": "sysadmin"}
        assert message.ts


# ---------------------------------------------------------------------------
# The real endpoint
# ---------------------------------------------------------------------------


class TestEventsEndpoint:
    @pytest.mark.asyncio
    async def test_connect_receive_event_disconnect(self, test_app):
        """Full round trip: stream opens, an event arrives, the client leaves."""
        assert event_broadcaster.subscriber_count == 0

        async with sse_request(test_app) as connection:
            assert connection.status_code == 200
            assert connection.headers["content-type"].startswith("text/event-stream")
            assert connection.headers["cache-control"] == "no-cache"
            assert connection.headers["x-accel-buffering"] == "no"

            hello = parse_sse_frame(await connection.next_chunk())
            assert hello["event"] == "connected"

            # The stream is registered, so a published change reaches it
            await _wait_for_subscriber()
            event_broadcaster.dispatch(
                Event("alert.raised", {"title": "Critical disk usage on /"})
            )

            frame = await connection.next_event()
            assert frame["event"] == "alert.raised"
            assert frame["data"]["data"]["title"] == "Critical disk usage on /"

        # Client gone → no leaked subscriber
        await _wait_for_no_subscribers()
        assert event_broadcaster.subscriber_count == 0

    @pytest.mark.asyncio
    async def test_agent_events_reach_the_endpoint(self, test_app):
        """An agent publishing to the shared bus lands on a connected stream."""
        from sysadmin.core.event_bus import event_bus

        async with sse_request(test_app) as connection:
            await connection.next_chunk()  # connected
            await _wait_for_subscriber()

            event_bus.publish_threadsafe(
                "agent.run", {"agent": "log_aggregator", "status": "completed"}
            )

            frame = await connection.next_event()
            assert frame["event"] == "agent.run"
            assert frame["data"]["data"]["agent"] == "log_aggregator"

        await _wait_for_no_subscribers()

    @pytest.mark.asyncio
    async def test_stream_is_excluded_from_the_access_log(self, test_app):
        """Long-lived streams must not reintroduce SNAG-API-002's log noise."""
        with patch("sysadmin.core.middleware.logger") as mock_logger:
            async with sse_request(test_app) as connection:
                await connection.next_chunk()

            mock_logger.info.assert_not_called()

    def test_events_path_is_in_the_exclusion_list(self):
        from sysadmin.core.middleware import _EXCLUDED_PATHS

        assert EVENTS_PATH in _EXCLUDED_PATHS

    @pytest.mark.asyncio
    async def test_second_client_gets_its_own_stream(self, test_app):
        async with sse_request(test_app) as first, sse_request(test_app) as second:
            await first.next_chunk()
            await second.next_chunk()
            await _wait_for_subscriber(count=2)

            event_broadcaster.dispatch(Event("service.status", {"service": "postgres"}))

            assert (await first.next_event())["event"] == "service.status"
            assert (await second.next_event())["event"] == "service.status"

        await _wait_for_no_subscribers()


async def _wait_for_subscriber(count: int = 1, timeout: float = 2.0) -> None:
    """Give the streaming task time to register its queue."""
    deadline = asyncio.get_running_loop().time() + timeout
    while event_broadcaster.subscriber_count < count:
        # may-not-evaluate: the deadline guard runs only if the wait turns at
        # least once, and a healthy box registers the queue before the first
        # check.  It cannot be restructured into evaluating — an assert that
        # ran when nothing was waited for would be asserting about no wait.
        assert asyncio.get_running_loop().time() < deadline, "stream never subscribed"
        await asyncio.sleep(0.01)


async def _wait_for_no_subscribers(timeout: float = 2.0) -> None:
    """Wait for disconnect cleanup to unwind the subscription."""
    deadline = asyncio.get_running_loop().time() + timeout
    while event_broadcaster.subscriber_count:
        # may-not-evaluate: the same deadline shape as _wait_for_subscriber —
        # cleanup has usually unwound before this loop is entered.
        assert asyncio.get_running_loop().time() < deadline, "subscriber leaked"
        await asyncio.sleep(0.01)
