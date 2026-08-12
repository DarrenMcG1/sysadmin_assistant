"""Shared LLM HTTP client for llama.cpp's llama-server.

The wire mechanics (payload construction, POST, content extraction, the
health probe) live in ``estate.llama`` since 2026-08-12 (estate-manager
ADR-0006; this repository's ADR-0004). What stays here is this service's
convention: **failures degrade to ``None`` with a warning, never an
exception** — callers treat "no narrative" as a first-class outcome — and
the event-loop-safe client lifecycle below.

Note: llama-server serves a single loaded model, so the ``model`` field in
requests is largely informational — it is recorded but does not switch models.
"""

import logging

import httpx
from estate.gpu import GpuBusy, ensure_gpu_idle
from estate.llama import (
    LlamaConnectError,
    LlamaInvalidResponse,
    LlamaStatusError,
    LlamaTimeout,
    chat_payload,
    extract_content,
    post_chat,
    probe_health,
)

from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import get_config

logger = logging.getLogger(__name__)


class LLMClient:
    """HTTP client for llama-server's OpenAI-compatible API.

    The underlying ``httpx.AsyncClient`` is held by a
    :class:`~sysadmin.core.async_http.LoopBoundClient`: the log
    aggregator calls this from APScheduler threads, each with its own
    short-lived event loop, and a client shared across loops raises
    "Event loop is closed" (SNAG-AGENT-003). This is why the estate
    library takes the client as an argument rather than owning one.
    """

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialise the client.

        Args:
            transport: optional httpx transport override (used by tests to
                inject a MockTransport).
        """
        self._transport = transport
        self._http = LoopBoundClient(self._build_client)

    async def startup(self) -> None:
        await self._http.open()

    async def shutdown(self) -> None:
        await self._http.close()

    def _build_client(self) -> httpx.AsyncClient:
        timeout = get_config().llm.timeout_seconds
        return httpx.AsyncClient(timeout=timeout, transport=self._transport)

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
    ) -> str | None:
        """Generate a chat completion from llama-server.

        Returns the response text, or None if the server is unavailable
        — or if the dGPU is busy with foreground work (ADR-0004 as
        amended 2026-08-12): this service's inference is deferrable
        housekeeping, and it shares Alfred's server on a GPU someone may
        be gaming on. A busy GPU degrades to "no narrative this run",
        the same first-class outcome callers already handle.
        Free-text path: ``temperature=None`` keeps the server's own
        sampling defaults — this call generates prose, not structured
        extraction, so the estate's structured-path temperature pin does
        not apply (estate ADR-0006 decision 3).
        """
        config = get_config()
        model = model or config.llm.model

        try:
            ensure_gpu_idle(config.llm.gpu_pci_slot, config.llm.gpu_busy_threshold)
        except GpuBusy as e:
            logger.warning(
                "llm_gpu_busy",
                extra={
                    "busy_percent": e.busy_percent,
                    "threshold": e.threshold,
                    "model": model,
                },
            )
            return None

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = chat_payload(model, messages, temperature=None, stream=False)

        try:
            async with self._http.borrow() as client:
                response = await post_chat(client, config.llm.url, payload)
            return extract_content(response)
        except (LlamaTimeout, LlamaConnectError) as e:
            logger.warning(
                "llm_unavailable",
                extra={"error": str(e), "model": model},
            )
            return None
        except LlamaStatusError as e:
            logger.warning(
                "llm_error",
                extra={"status": e.status, "model": model},
            )
            return None
        except LlamaInvalidResponse:
            logger.warning(
                "llm_malformed_response",
                extra={"model": model},
            )
            return None
        except Exception as e:
            logger.error(
                "llm_unexpected_error",
                extra={"error": str(e), "model": model},
            )
            return None

    async def is_available(self) -> bool:
        """Check if llama-server is up with its model loaded.

        llama-server returns 200 ``{"status":"ok"}`` when ready, and 503
        while the model is still loading.
        """
        config = get_config()
        try:
            async with self._http.borrow() as client:
                return await probe_health(client, config.llm.url)
        except Exception:
            return False
