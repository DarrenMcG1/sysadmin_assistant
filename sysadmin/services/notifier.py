"""Notifier — sends alerts and briefing data to PersonalAssistant via HTTP.

Gracefully handles PA being unreachable (logs warning, does not crash).
Retries with exponential backoff for transient failures.
"""

import logging
from typing import Any

import httpx

from sysadmin.config import get_config
from sysadmin.services.dnd import dnd_manager

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0


class Notifier:
    """HTTP client for communicating with PersonalAssistant."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._client = httpx.AsyncClient(timeout=15.0)

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    async def send_notification(
        self,
        urgency: str,
        title: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """POST a notification to PersonalAssistant.

        Returns True if delivered, False if PA is unreachable or suppressed by DND.
        """
        # Check DND — suppressed notifications are silently dropped
        if dnd_manager.should_suppress(urgency):
            logger.debug("notification suppressed by DND: [%s] %s", urgency, title)
            return False

        config = get_config()

        # Check PA notification severity threshold
        pa_config = config.notifications.pa_notify
        if not pa_config.enabled:
            logger.debug("PA notifications disabled")
            return False

        severity_levels = {"info": 0, "warning": 1, "critical": 2}
        if severity_levels.get(urgency, 0) < severity_levels.get(pa_config.min_severity, 0):
            logger.debug("notification below PA severity threshold: [%s] %s", urgency, title)
            return False

        url = f"{config.personal_assistant.url}{config.personal_assistant.notify_endpoint}"
        payload = {
            "source": "sysadmin",
            "urgency": urgency,
            "title": title,
            "message": message,
            "details": details or {},
        }

        return await self._post_with_retry(url, payload)

    async def send_briefing_data(self, sections: list[dict[str, Any]]) -> bool:
        """POST briefing data to PersonalAssistant.

        Returns True if delivered, False if PA is unreachable.
        """
        config = get_config()
        url = f"{config.personal_assistant.url}{config.personal_assistant.briefing_endpoint}"
        payload = {
            "source": "sysadmin-service",
            "sections": sections,
        }

        return await self._post_with_retry(url, payload)

    async def _post_with_retry(self, url: str, payload: dict) -> bool:
        """POST with exponential backoff retries."""
        import asyncio

        client = await self._get_client()
        backoff = INITIAL_BACKOFF_S

        for attempt in range(MAX_RETRIES):
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code < 400:
                    logger.info("notification_sent", extra={"url": url})
                    return True
                logger.warning(
                    "notification_failed",
                    extra={"url": url, "status": resp.status_code, "attempt": attempt + 1},
                )
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(
                    "notification_unreachable",
                    extra={"url": url, "error": str(e), "attempt": attempt + 1},
                )
            except Exception as e:
                logger.error(
                    "notification_error",
                    extra={"url": url, "error": str(e), "attempt": attempt + 1},
                )
                return False

            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(backoff)
                backoff *= 2

        logger.warning(
            "notification_all_retries_exhausted",
            extra={"url": url, "retries": MAX_RETRIES},
        )
        return False
