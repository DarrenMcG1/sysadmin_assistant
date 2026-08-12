"""Tests for the llama.cpp (llama-server) LLM client.

Mocks httpx at the transport layer via httpx.MockTransport — no real
network calls. Covers: health check up/down/loading, completion parsing,
system-prompt placement, and graceful None degradation on errors.
"""

import json
from unittest.mock import patch

import httpx
import pytest

from sysadmin.core.config import AppConfig, LLMConfig
from sysadmin.core.llm_client import LLMClient


@pytest.fixture
def llm_config():
    """AppConfig with a deterministic llm block.

    ``gpu_pci_slot=""`` disables the GPU gate so these tests never read
    the real sysfs counter (a run during live inference would defer and
    fail); the gate has its own tests below with a patched sampler.
    """
    return AppConfig(
        llm=LLMConfig(
            url="http://testserver:8081",
            model="test-model.gguf",
            timeout_seconds=5.0,
            gpu_pci_slot="",
        )
    )


def _make_client(handler, llm_config) -> LLMClient:
    """Build an LLMClient wired to a MockTransport handler."""
    return LLMClient(transport=httpx.MockTransport(handler))


def _chat_response(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "model": "test-model.gguf",
            "object": "chat.completion",
        },
    )


def _patch_config(config):
    return patch(
        "sysadmin.core.llm_client.get_config", return_value=config
    )


class TestIsAvailable:
    @pytest.mark.asyncio
    async def test_available_when_health_ok(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/health"
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.is_available() is True
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_unavailable_while_model_loading_503(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                503, json={"error": {"message": "Loading model"}}
            )

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.is_available() is False
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_unavailable_when_connection_refused(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.is_available() is False
        await client.shutdown()


class TestGenerate:
    @pytest.mark.asyncio
    async def test_successful_completion_parsing(self, llm_config):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["path"] = request.url.path
            captured["payload"] = json.loads(request.content)
            return _chat_response("The logs look healthy.")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            result = await client.generate(prompt="Summarise these logs")
        await client.shutdown()

        assert result == "The logs look healthy."
        assert captured["path"] == "/v1/chat/completions"
        payload = captured["payload"]
        assert payload["model"] == "test-model.gguf"
        assert payload["stream"] is False
        assert payload["messages"] == [
            {"role": "user", "content": "Summarise these logs"}
        ]

    @pytest.mark.asyncio
    async def test_system_prompt_becomes_system_role_message(self, llm_config):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return _chat_response("ok")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            result = await client.generate(
                prompt="user text", system="You are a sysadmin."
            )
        await client.shutdown()

        assert result == "ok"
        messages = captured["payload"]["messages"]
        assert messages[0] == {"role": "system", "content": "You are a sysadmin."}
        assert messages[1] == {"role": "user", "content": "user text"}

    @pytest.mark.asyncio
    async def test_explicit_model_overrides_config(self, llm_config):
        captured: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["payload"] = json.loads(request.content)
            return _chat_response("ok")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            await client.generate(prompt="hi", model="other-model")
        await client.shutdown()

        assert captured["payload"]["model"] == "other-model"

    @pytest.mark.asyncio
    async def test_http_error_returns_none(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "boom"})

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_connect_error_returns_none(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_malformed_response_returns_none(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []})

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_non_json_response_returns_none(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="not json")

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()


class TestGpuGate:
    """ADR-0004 as amended: a busy dGPU degrades to None, fail-open stands."""

    @pytest.fixture
    def gated_config(self):
        # Estate-default slot and threshold — the gate is live here.
        return AppConfig(
            llm=LLMConfig(
                url="http://testserver:8081",
                model="test-model.gguf",
                timeout_seconds=5.0,
            )
        )

    @pytest.mark.asyncio
    async def test_busy_gpu_returns_none_without_dispatching(
        self, gated_config, monkeypatch
    ):
        monkeypatch.setattr("estate.gpu.sample_gpu_busy", lambda *a, **k: 90)

        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("no dispatch while the GPU is busy")

        client = LLMClient(transport=httpx.MockTransport(handler))
        with _patch_config(gated_config):
            assert await client.generate(prompt="hi") is None
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_unreadable_counter_fails_open_and_dispatches(
        self, gated_config, monkeypatch
    ):
        monkeypatch.setattr("estate.gpu.sample_gpu_busy", lambda *a, **k: None)

        client = LLMClient(
            transport=httpx.MockTransport(lambda request: _chat_response("still fine"))
        )
        with _patch_config(gated_config):
            assert await client.generate(prompt="hi") == "still fine"
        await client.shutdown()

    @pytest.mark.asyncio
    async def test_probe_is_not_gated(self, gated_config, monkeypatch):
        # is_available answers "is the server up", not "may I dispatch" —
        # a busy GPU must not make the server look down.
        monkeypatch.setattr("estate.gpu.sample_gpu_busy", lambda *a, **k: 90)

        client = LLMClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"status": "ok"})
            )
        )
        with _patch_config(gated_config):
            assert await client.is_available() is True
        await client.shutdown()


class TestLifecycle:
    @pytest.mark.asyncio
    async def test_startup_and_shutdown(self, llm_config):
        client = LLMClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"status": "ok"})
        ))
        with _patch_config(llm_config):
            await client.startup()
            assert client._http.client is not None
            await client.shutdown()
            assert client._http.client is None

    @pytest.mark.asyncio
    async def test_lazy_client_creation_without_startup(self, llm_config):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "ok"})

        client = _make_client(handler, llm_config)
        with _patch_config(llm_config):
            # No startup() call — client is created lazily
            assert await client.is_available() is True
        await client.shutdown()
