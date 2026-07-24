"""Tests for the outbound PersonalAssistant notifier.

PA was retired on 2026-07-24 and ``personal_assistant.enabled`` is now
false in config.yaml, so the important guarantee here is *negative*: a
disabled integration must make no HTTP call at all, and must not turn a
deliberate steady state into a per-attempt warning or an alert.  The
enabled paths are kept too — this is a dormant flag, not a deletion, and
the transport must still work if it is ever repointed.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from sysadmin.config import (
    AppConfig,
    NotificationsConfig,
    PaNotificationsConfig,
    PersonalAssistantConfig,
)
from sysadmin.services import notifier as notifier_module
from sysadmin.services.notifier import Notifier


def _config(enabled: bool) -> AppConfig:
    """An AppConfig whose only interesting axis is the PA integration."""
    return AppConfig(
        personal_assistant=PersonalAssistantConfig(
            enabled=enabled,
            url="http://localhost:8000",
            notify_endpoint="/api/v2/notifications/send",
            briefing_endpoint="/api/v2/intelligence/briefing/data",
        ),
        notifications=NotificationsConfig(
            pa_notify=PaNotificationsConfig(enabled=True, min_severity="info"),
        ),
    )


@pytest.fixture
def notifier_with_client():
    """A Notifier wired to a mock httpx client, with the once-only log reset."""
    notifier_module._disabled_notice_logged = False
    notifier = Notifier()
    client = MagicMock(spec=httpx.AsyncClient)
    client.post = AsyncMock(return_value=MagicMock(status_code=200))
    notifier._http.attach(client)
    return notifier, client


# ── Disabled: nothing may leave the process ──────────────────────


class TestIntegrationDisabled:
    @pytest.mark.asyncio
    async def test_notification_makes_no_http_call(self, notifier_with_client):
        notifier, client = notifier_with_client

        with patch("sysadmin.services.notifier.get_config", return_value=_config(False)):
            result = await notifier.send_notification("critical", "Disk full", "90%")

        assert result is False
        client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_briefing_makes_no_http_call(self, notifier_with_client):
        notifier, client = notifier_with_client

        with patch("sysadmin.services.notifier.get_config", return_value=_config(False)):
            result = await notifier.send_briefing_data([{"title": "Infra"}])

        assert result is False
        client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_notice_is_logged_once_not_per_attempt(self, notifier_with_client, caplog):
        """Ten suppressed sends must not produce ten log records."""
        notifier, _client = notifier_with_client

        with patch("sysadmin.services.notifier.get_config", return_value=_config(False)):
            with caplog.at_level("INFO", logger="sysadmin.services.notifier"):
                for _ in range(10):
                    await notifier.send_notification("critical", "Disk full", "90%")

        notices = [r for r in caplog.records if r.message == "pa_integration_disabled"]
        assert len(notices) == 1

    @pytest.mark.asyncio
    async def test_suppression_never_warns(self, notifier_with_client, caplog):
        """A retired integration is expected, so nothing above INFO is emitted."""
        notifier, _client = notifier_with_client

        with patch("sysadmin.services.notifier.get_config", return_value=_config(False)):
            with caplog.at_level("DEBUG", logger="sysadmin.services.notifier"):
                await notifier.send_notification("critical", "Disk full", "90%")
                await notifier.send_briefing_data([{"title": "Infra"}])

        assert [r for r in caplog.records if r.levelname in ("WARNING", "ERROR")] == []


# ── Enabled: unchanged behaviour ─────────────────────────────────


class TestIntegrationEnabled:
    @pytest.mark.asyncio
    async def test_notification_posts_as_before(self, notifier_with_client):
        notifier, client = notifier_with_client

        with patch("sysadmin.services.notifier.get_config", return_value=_config(True)):
            result = await notifier.send_notification("critical", "Disk full", "90%")

        assert result is True
        client.post.assert_awaited_once()
        url = client.post.await_args.args[0]
        payload = client.post.await_args.kwargs["json"]
        assert url == "http://localhost:8000/api/v2/notifications/send"
        assert payload["title"] == "Disk full"
        assert payload["priority"] == "critical"

    @pytest.mark.asyncio
    async def test_briefing_posts_as_before(self, notifier_with_client):
        notifier, client = notifier_with_client
        sections = [{"title": "Infrastructure Status"}]

        with patch("sysadmin.services.notifier.get_config", return_value=_config(True)):
            result = await notifier.send_briefing_data(sections)

        assert result is True
        client.post.assert_awaited_once()
        url = client.post.await_args.args[0]
        payload = client.post.await_args.kwargs["json"]
        assert url == "http://localhost:8000/api/v2/intelligence/briefing/data"
        assert payload["sections"] == sections
