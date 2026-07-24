"""Shared LLM HTTP client for llama.cpp's llama-server.

Speaks the OpenAI-compatible API exposed by llama-server
(POST /v1/chat/completions, GET /health). Gracefully handles the server
being unavailable (logs warning, returns None).

Note: llama-server serves a single loaded model, so the ``model`` field in
requests is largely informational — it is recorded but does not switch models.
"""

import logging
from typing import Any

import httpx

from sysadmin.config import get_config

logger = logging.getLogger(__name__)


class LLMClient:
    """HTTP client for llama-server's OpenAI-compatible API."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialise the client.

        Args:
            transport: optional httpx transport override (used by tests to
                inject a MockTransport).
        """
        self._client: httpx.AsyncClient | None = None
        self._transport = transport

    async def startup(self) -> None:
        self._client = self._build_client()

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _build_client(self) -> httpx.AsyncClient:
        timeout = get_config().llm.timeout_seconds
        return httpx.AsyncClient(timeout=timeout, transport=self._transport)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
    ) -> str | None:
        """Generate a chat completion from llama-server.

        Returns the response text, or None if the server is unavailable.
        """
        config = get_config()
        url = f"{config.llm.url}/v1/chat/completions"
        model = model or config.llm.model

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        client = await self._get_client()
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                try:
                    return data["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError):
                    logger.warning(
                        "llm_malformed_response",
                        extra={"model": model},
                    )
                    return None
            else:
                logger.warning(
                    "llm_error",
                    extra={"status": resp.status_code, "model": model},
                )
                return None
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(
                "llm_unavailable",
                extra={"error": str(e), "model": model},
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
        client = await self._get_client()
        try:
            resp = await client.get(f"{config.llm.url}/health")
            return resp.status_code == 200
        except Exception:
            return False
