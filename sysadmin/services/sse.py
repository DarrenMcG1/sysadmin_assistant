"""Server-Sent Events fan-out — pushes change events to connected clients.

Replaces client polling (the tray hitting ``/health`` every few seconds,
SNAG-API-002's log-noise source) with a single long-lived stream.

Wiring: agents publish to the shared :data:`~sysadmin.services.event_bus`
(``alert.raised``, ``alert.resolved``, ``agent.run``, ``service.status``);
this broadcaster is the bus's only subscriber and copies each event into
one bounded queue per connected client. Nothing else in the request path
knows about SSE.

Back-pressure: a client that cannot keep up loses its **oldest** queued
events rather than blocking the publisher — the stream is a "something
changed, refetch" hint, so the newest events matter most.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from typing import Any

from sysadmin.services.event_bus import EventBus, event_bus

logger = logging.getLogger(__name__)

#: Event types forwarded to SSE clients. Anything else on the bus stays internal.
STREAMED_EVENTS = (
    "alert.raised",
    "alert.resolved",
    "agent.run",
    "service.status",
)

#: SSE comment written to idle streams so proxies/clients keep them open.
HEARTBEAT = ": keepalive\n\n"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class Event:
    """One event delivered to SSE clients."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=_now_iso)

    def payload(self) -> dict[str, Any]:
        """JSON body of the ``data:`` line — see ``contracts.EventMessage``.

        Self-describing (carries the type as well as the ``event:`` line)
        so a client using a plain ``onmessage`` handler still knows what
        it received.
        """
        return {"event": self.type, "data": self.data, "ts": self.ts}


def format_sse(
    event_type: str,
    data: dict[str, Any],
    retry_ms: int | None = None,
) -> str:
    """Serialise one message in the ``text/event-stream`` wire format."""
    lines = []
    if retry_ms is not None:
        lines.append(f"retry: {retry_ms}")
    lines.append(f"event: {event_type}")
    lines.append(f"data: {json.dumps(data, default=str)}")
    return "\n".join(lines) + "\n\n"


class EventBroadcaster:
    """Fans event-bus events out to per-client queues."""

    def __init__(self, max_queue: int = 100) -> None:
        self._queues: set[asyncio.Queue[Event]] = set()
        self._max_queue = max_queue
        self._attached_to: set[int] = set()

    @property
    def subscriber_count(self) -> int:
        """Number of currently connected SSE clients."""
        return len(self._queues)

    def attach(self, bus: EventBus) -> None:
        """Subscribe to the streamed event types on ``bus`` (idempotent)."""
        if id(bus) in self._attached_to:
            return
        self._attached_to.add(id(bus))
        for event_type in STREAMED_EVENTS:
            bus.subscribe(event_type, partial(self._on_event, event_type))

    async def _on_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Bus callback — copy the event into every client queue."""
        self.dispatch(Event(type=event_type, data=data))

    def dispatch(self, event: Event) -> None:
        """Deliver an event to all connected clients, dropping oldest on overflow."""
        for queue in list(self._queues):
            if queue.full():
                try:
                    queue.get_nowait()  # discard the oldest — never block a publisher
                except asyncio.QueueEmpty:  # pragma: no cover — racing consumer
                    pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover — racing consumer
                logger.debug("sse_queue_full", extra={"event_type": event.type})

    @asynccontextmanager
    async def subscribe(
        self, max_queue: int | None = None
    ) -> AsyncIterator[asyncio.Queue[Event]]:
        """Register a client queue for the life of the context.

        The ``finally`` is what guarantees a disconnected client is
        forgotten: when the stream generator is closed or cancelled the
        queue is removed, so no reference (and no task) is leaked.
        """
        queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue or self._max_queue)
        self._queues.add(queue)
        logger.debug("sse_client_connected", extra={"clients": len(self._queues)})
        try:
            yield queue
        finally:
            self._queues.discard(queue)
            logger.debug("sse_client_disconnected", extra={"clients": len(self._queues)})


async def event_stream(
    broadcaster: EventBroadcaster,
    heartbeat_seconds: float,
    retry_ms: int,
    max_queue: int | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames until the client goes away.

    Emits an immediate ``connected`` event (so clients can confirm the
    stream works without waiting for real activity), then one frame per
    event, with a heartbeat comment whenever the stream is idle for
    ``heartbeat_seconds``.

    Disconnects need no polling: Starlette closes/cancels this generator
    when the client vanishes, which unwinds :meth:`EventBroadcaster.subscribe`
    and unregisters the queue.
    """
    async with broadcaster.subscribe(max_queue=max_queue) as queue:
        hello = Event(type="connected")
        yield format_sse(hello.type, hello.payload(), retry_ms=retry_ms)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=heartbeat_seconds)
            except TimeoutError:
                yield HEARTBEAT
                continue
            yield format_sse(event.type, event.payload())


#: Process-wide broadcaster, listening to the shared event bus.
event_broadcaster = EventBroadcaster()
event_broadcaster.attach(event_bus)
