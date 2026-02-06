"""Lightweight async event bus for internal pub/sub.

Agents publish events (e.g. "alert.critical", "scan.complete") and
other components subscribe to react. Simple callback list — no
persistence, no ordering guarantees.
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

    def subscribe(self, event_type: str, callback: EventCallback) -> None:
        """Register a callback for an event type."""
        self._subscribers[event_type].append(callback)
        logger.debug("event_bus_subscribe", extra={"event_type": event_type})

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

    async def publish_fire_and_forget(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """Publish without waiting for callbacks to complete."""
        asyncio.create_task(self.publish(event_type, data))
