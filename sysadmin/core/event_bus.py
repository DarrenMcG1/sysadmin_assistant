"""Lightweight async event bus for internal pub/sub.

Agents publish events (e.g. "alert.raised", "agent.run") and other
components subscribe to react. Simple callback list — no persistence, no
ordering guarantees.

Cross-thread publishing
-----------------------
Agents run on the APScheduler thread pool, each job bridged into its own
event loop by ``asyncio.run()`` — a *different* loop from the one serving
HTTP requests. Subscribers that own loop-bound state (the SSE broadcaster's
per-client queues) must therefore be woken on the API loop, not the
scheduler's. :meth:`EventBus.bind_loop` records that loop at startup and
:meth:`EventBus.publish_threadsafe` hands the coroutine over to it via
``run_coroutine_threadsafe``.
"""

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """In-process async event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventCallback]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._tasks: set[asyncio.Task] = set()

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for an event type."""
        self._subscribers[event_type].append(callback)
        logger.debug("event_bus_subscribe", extra={"event_type": event_type})

    def bind_loop(self, loop: asyncio.AbstractEventLoop | None = None) -> None:
        """Record the loop that subscriber callbacks must run on.

        Called from the API event loop during startup. Defaults to the
        currently running loop.
        """
        if loop is None:
            loop = asyncio.get_running_loop()
        self._loop = loop
        logger.debug("event_bus_loop_bound")

    async def publish(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Publish an event to all subscribers. Errors in callbacks are logged, not raised."""
        data = data or {}
        callbacks = self._subscribers.get(event_type, [])
        for callback in callbacks:
            try:
                await callback(data)
            except Exception:
                logger.exception(
                    "event_bus_callback_error",
                    extra={"event_type": event_type, "callback": callback.__name__},
                )

    async def publish_fire_and_forget(
        self, event_type: str, data: dict[str, Any] | None = None
    ) -> None:
        """Publish without waiting for callbacks to complete."""
        self._spawn(asyncio.get_running_loop(), event_type, data)

    def publish_threadsafe(
        self, event_type: str, data: dict[str, Any] | None = None
    ) -> None:
        """Publish from any thread or event loop, without waiting.

        Delivery happens on the bound loop when there is one (so callbacks
        touching API-loop state are safe to call from a scheduler thread).
        With no bound loop the running loop is used; with neither, the
        event is dropped — publishing is best-effort by design.
        """
        try:
            running: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        target = self._loop or running
        if target is None or target.is_closed():
            logger.debug("event_bus_no_loop", extra={"event_type": event_type})
            return

        self._spawn(target, event_type, data)

    def _spawn(
        self,
        loop: asyncio.AbstractEventLoop,
        event_type: str,
        data: dict[str, Any] | None,
    ) -> None:
        """Schedule ``publish`` on ``loop`` without awaiting the result."""
        try:
            running: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            running = None

        coro = self.publish(event_type, data)
        if running is loop:
            # Keep a strong reference — a bare create_task may be GC'd.
            task = loop.create_task(coro)
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            return

        try:
            asyncio.run_coroutine_threadsafe(coro, loop)
        except RuntimeError:
            coro.close()
            logger.debug("event_bus_publish_dropped", extra={"event_type": event_type})


#: Process-wide bus. Agents publish to it, the SSE broadcaster listens.
event_bus = EventBus()
