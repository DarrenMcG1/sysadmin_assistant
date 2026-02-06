"""Shared Ollama HTTP client for LLM interactions.

Gracefully handles Ollama being unavailable (logs warning, returns None).
"""

import logging
from typing import Any

import httpx

from sysadmin.config import get_config

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for the Ollama API."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._client = httpx.AsyncClient(timeout=120.0)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
    ) -> str | None:
        """Generate a response from Ollama.

        Returns the response text, or None if Ollama is unavailable.
        """
        config = get_config()
        url = f"{config.ollama.url}/api/generate"
        model = model or config.ollama.model

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        client = await self._get_client()
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                logger.warning(
                    "ollama_error",
                    extra={"status": resp.status_code, "model": model},
                )
                return None
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.warning(
                "ollama_unavailable",
                extra={"error": str(e), "model": model},
            )
            return None
        except Exception as e:
            logger.error(
                "ollama_unexpected_error",
                extra={"error": str(e), "model": model},
            )
            return None

    async def is_available(self) -> bool:
        """Check if Ollama is reachable."""
        config = get_config()
        client = await self._get_client()
        try:
            resp = await client.get(f"{config.ollama.url}/api/tags")
            return resp.status_code == 200
        except Exception:
            return False
