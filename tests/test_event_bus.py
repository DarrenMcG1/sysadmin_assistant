"""Tests for the in-process async event bus."""

import asyncio
import threading
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest

from sysadmin.core.event_bus import EventBus, event_bus


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


class TestThreadsafePublish:
    """Agents publish from scheduler threads with their own event loops."""

    @pytest.mark.asyncio
    async def test_publishes_on_the_running_loop(self):
        bus = EventBus()
        received: list[dict] = []

        async def on_event(data: dict) -> None:
            received.append(data)

        bus.subscribe("agent.run", on_event)
        bus.publish_threadsafe("agent.run", {"agent": "sysadmin"})

        await asyncio.sleep(0)
        assert received == [{"agent": "sysadmin"}]

    @pytest.mark.asyncio
    async def test_delivers_to_the_bound_loop_from_another_thread(self):
        """A scheduler thread's asyncio.run() must not deliver on its own loop."""
        bus = EventBus()
        received: list[dict] = []
        delivered = asyncio.Event()

        async def on_event(data: dict) -> None:
            received.append(data)
            delivered.set()

        bus.subscribe("alert.raised", on_event)
        bus.bind_loop()  # the "API" loop — the one running this test

        def scheduler_thread() -> None:
            # Mirrors Scheduler._run_async: a fresh loop in a worker thread
            async def job() -> None:
                bus.publish_threadsafe("alert.raised", {"title": "Disk full"})

            asyncio.run(job())

        thread = threading.Thread(target=scheduler_thread)
        thread.start()
        thread.join()

        await asyncio.wait_for(delivered.wait(), timeout=2)
        assert received == [{"title": "Disk full"}]

    def test_dropped_when_no_loop_is_available(self):
        """Publishing with no loop anywhere must not raise."""
        bus = EventBus()
        bus.subscribe("agent.run", lambda data: None)  # type: ignore[arg-type]
        bus.publish_threadsafe("agent.run", {"agent": "sysadmin"})

    @pytest.mark.asyncio
    async def test_bind_loop_defaults_to_the_running_loop(self):
        bus = EventBus()
        bus.bind_loop()
        assert bus._loop is asyncio.get_running_loop()


class TestSharedBusSingleton:
    def test_module_singleton_is_shared(self):
        from sysadmin.core.agent import event_bus as agent_bus
        from sysadmin.main import event_bus as main_bus

        assert agent_bus is event_bus
        assert main_bus is event_bus

    def test_sse_broadcaster_listens_to_the_singleton(self):
        from sysadmin.monitor.sse import STREAMED_EVENTS

        for event_type in STREAMED_EVENTS:
            assert event_bus._subscribers[event_type], f"{event_type} has no subscriber"


class TestAgentEventPublishing:
    """BaseAgent buffers events until its transaction has committed."""

    @pytest.fixture
    def recording_bus(self):
        bus = EventBus()
        events: list[tuple[str, dict]] = []

        async def record(event_type: str, data: dict) -> None:
            events.append((event_type, data))

        for event_type in ("alert.raised", "alert.resolved", "agent.run"):
            bus.subscribe(
                event_type,
                lambda data, t=event_type: record(t, data),  # type: ignore[misc]
            )
        return bus, events

    @pytest.mark.asyncio
    async def test_alert_event_is_published_after_the_commit(
        self, recording_bus, mock_session
    ):
        from sysadmin.core.agent import AgentResult, BaseAgent

        bus, events = recording_bus
        timeline: list[str] = []

        class _Agent(BaseAgent):
            name = "sysadmin"

            async def _execute(self, session):
                await self.raise_alert(session, severity="warning", title="Disk full")
                timeline.append("executed")
                return AgentResult(alerts_raised=1)

        @asynccontextmanager
        async def fake_session():
            yield mock_session
            timeline.append("committed")

        with (
            patch("sysadmin.core.agent.event_bus", bus),
            patch("sysadmin.core.agent.get_scheduler_session", fake_session),
        ):
            await _Agent().run()
            await asyncio.sleep(0)

        assert timeline == ["executed", "committed"]
        assert [e[0] for e in events] == ["alert.raised", "agent.run"]
        assert events[0][1]["title"] == "Disk full"

    @pytest.mark.asyncio
    async def test_run_event_reports_the_outcome(self, recording_bus, mock_session):
        from sysadmin.core.agent import BaseAgent

        bus, events = recording_bus

        class _BrokenAgent(BaseAgent):
            name = "log_aggregator"

            async def _execute(self, session):
                raise RuntimeError("boom")

        @asynccontextmanager
        async def fake_session():
            yield mock_session

        with (
            patch("sysadmin.core.agent.event_bus", bus),
            patch("sysadmin.core.agent.get_scheduler_session", fake_session),
        ):
            await _BrokenAgent().run(run_type="manual")
            await asyncio.sleep(0)

        assert len(events) == 1
        event_type, data = events[0]
        assert event_type == "agent.run"
        assert data["status"] == "failed"
        assert data["agent"] == "log_aggregator"
        assert data["run_type"] == "manual"
