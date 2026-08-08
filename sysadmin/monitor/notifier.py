"""Notifier — sends alerts and briefing data to PersonalAssistant via HTTP.

Gracefully handles PA being unreachable (logs warning, does not crash).
Retries with exponential backoff for transient failures.

PA was retired on 2026-07-24 and ``personal_assistant.enabled`` is now
``false``, so in practice every send short-circuits before any HTTP call.
The transport is kept intact so the integration can be repointed at a
replacement inbox by flipping one flag.
"""

import logging
from typing import Any

import httpx

from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import AppConfig, get_config
from sysadmin.monitor.dnd import dnd_manager

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
INITIAL_BACKOFF_S = 1.0

# The "integration is disabled" notice is worth seeing once per process, not
# once per suppressed send — a retired integration is a steady state, not a
# fault, so it must never produce a warning (or an alert) on every attempt.
_disabled_notice_logged = False


def _integration_disabled(config: AppConfig) -> bool:
    """True when the PersonalAssistant integration is switched off.

    Logs a single INFO line the first time it suppresses something in this
    process, then drops to DEBUG for the rest of the process's life.
    """
    if config.personal_assistant.enabled:
        return False

    global _disabled_notice_logged
    if not _disabled_notice_logged:
        _disabled_notice_logged = True
        logger.info(
            "pa_integration_disabled",
            extra={"detail": "personal_assistant.enabled is false — outbound sends skipped"},
        )
    else:
        logger.debug("PA integration disabled; send skipped")
    return True


class Notifier:
    """HTTP client for communicating with PersonalAssistant.

    The shared instance is opened on the API event loop during the
    lifespan but may be driven from APScheduler threads, so the client is
    held by a :class:`~sysadmin.core.async_http.LoopBoundClient` — one
    reused across event loops raises "Event loop is closed"
    (SNAG-AGENT-003).
    """

    def __init__(self) -> None:
        self._http = LoopBoundClient(lambda: httpx.AsyncClient(timeout=15.0))

    async def startup(self) -> None:
        await self._http.open()

    async def shutdown(self) -> None:
        await self._http.close()

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

        # Integration retired → skip before any HTTP work
        if _integration_disabled(config):
            return False

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
            "category": "system",
            "priority": urgency,
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

        # Integration retired → skip before any HTTP work
        if _integration_disabled(config):
            return False

        url = f"{config.personal_assistant.url}{config.personal_assistant.briefing_endpoint}"
        payload = {
            "source": "sysadmin-service",
            "sections": sections,
        }

        return await self._post_with_retry(url, payload)

    async def _post_with_retry(self, url: str, payload: dict) -> bool:
        """POST with exponential backoff retries."""
        import asyncio

        backoff = INITIAL_BACKOFF_S

        async with self._http.borrow() as client:
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
