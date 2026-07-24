"""Tests for the in-process async event bus."""

import asyncio

import pytest

from sysadmin.services.event_bus import EventBus


class TestSubscribePublish:
    @pytest.mark.asyncio
    async def test_subscriber_receives_event_data(self):
        bus = EventBus()
        received: list[dict] = []

        async def on_event(data: dict) -> None:
            received.append(data)

        bus.subscribe("alert.critical", on_event)
        await bus.publish("alert.critical", {"service": "postgres"})

        assert received == [{"service": "postgres"}]

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_called(self):
        bus = EventBus()
        calls: list[str] = []

        async def first(data: dict) -> None:
            calls.append("first")

        async def second(data: dict) -> None:
            calls.append("second")

        bus.subscribe("scan.complete", first)
        bus.subscribe("scan.complete", second)
        await bus.publish("scan.complete")

        assert calls == ["first", "second"]

    @pytest.mark.asyncio
    async def test_publish_without_subscribers_is_noop(self):
        bus = EventBus()
        # Must not raise
        await bus.publish("nobody.listening", {"x": 1})

    @pytest.mark.asyncio
    async def test_data_defaults_to_empty_dict(self):
        bus = EventBus()
        received: list[dict] = []

        async def on_event(data: dict) -> None:
            received.append(data)

        bus.subscribe("tick", on_event)
        await bus.publish("tick")

        assert received == [{}]

    @pytest.mark.asyncio
    async def test_subscriber_only_gets_its_event_type(self):
        bus = EventBus()
        received: list[dict] = []

        async def on_event(data: dict) -> None:
            received.append(data)

        bus.subscribe("alert.critical", on_event)
        await bus.publish("alert.warning", {"service": "redis"})

        assert received == []


class TestErrorIsolation:
    @pytest.mark.asyncio
    async def test_failing_callback_does_not_break_others(self):
        bus = EventBus()
        calls: list[str] = []

        async def broken(data: dict) -> None:
            raise RuntimeError("subscriber blew up")

        async def healthy(data: dict) -> None:
            calls.append("healthy")

        bus.subscribe("event", broken)
        bus.subscribe("event", healthy)

        # Must not raise, and the healthy subscriber still runs
        await bus.publish("event")
        assert calls == ["healthy"]


class TestFireAndForget:
    @pytest.mark.asyncio
    async def test_fire_and_forget_delivers_eventually(self):
        bus = EventBus()
        received: list[dict] = []

        async def on_event(data: dict) -> None:
            received.append(data)

        bus.subscribe("bg", on_event)
        await bus.publish_fire_and_forget("bg", {"n": 1})

        # Returns before delivery — let the scheduled task run
        assert received == []
        await asyncio.sleep(0)
        assert received == [{"n": 1}]
