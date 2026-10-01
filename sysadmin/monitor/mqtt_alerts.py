"""Raised alerts, published to the estate's MQTT broker.

Session 39's open task ("who watches the watchers"), built 2026-10-01.
Every other speaker on this box — the tray, and ``desktop.py`` as its
understudy — reaches a screen on this machine, so an alert raised while
nobody is at the desk waits for someone to sit down. This puts the alert
on ``estate/…``, the broker's cross-app root, where a reader off the
desk can take it.

**Publishing is not delivery, and the difference decides four rules.**
The estate's bus already carries the audit's findings and the register's
messages to a room with no renderer in it (estate ADR-0180), and what
reaches a phone is decided by alfred-glance's ``RENDERERS`` map, in the
repository that owns the phone. So:

1. **One topic, the severity in the payload.** ``estate/alerts/raised``
   and not ``…/{severity}``: glance keys ``RENDERERS`` by literal topic,
   and ADR-0180 §6 records the audit's per-check segmentation as the
   thing that made its audience cost thirteen entries.
2. **No DND, no incident gate, no reminders.** Those decide what
   *interrupts* a reader, and that is the renderer's call. The gate that
   stays is ``min_severity``, which decides what is *published* and is
   sized against measured volume (see the config model).
3. **One attempt, never retained.** An alert is an event; a retained
   topic holds the last message for ever, which for an alert is a lie by
   the next morning. A failed publish is logged and dropped — a retry
   loop is a delivery path with a queue in it, the estate register's
   refusal in ``register/publisher.py`` and the same reason.
4. **Raises nothing.** A callback that raises takes down the event bus's
   task for every other subscriber.

**The row is read back before it is announced.** Until 2026-10-01
``BaseAgent.run`` flushed buffered events whatever the run's outcome, so
a run that raised an alert and then failed announced a row its rollback
removed. ``run()`` now discards a failed run's events, and every
``raise_alert`` caller is inside a run, so on today's code the read-back
refuses nothing. It stays because a phantom on the bus is an alert
nobody can find, and the guard costs one indexed read per published
alert, at well under one a day.

**What a zero exit proves.** ``mosquitto_pub`` exits 0 for an
unauthorised publish — the broker drops it silently (``estate.bus``'s
docstring, measured 2026-09-04). So ``mqtt_alert_published`` means the
broker accepted this identity, and the ACL is established by
``estate-manager/mqtt/dynsec.yaml`` granting ``estate-publisher`` on
``estate/#``. Only a subscriber can witness more.
"""

import asyncio
import logging
import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from estate.bus import BrokerIdentity, PublishError, publish
from sqlalchemy import func, select

from sysadmin.core.config import MqttNotificationsConfig, get_config
from sysadmin.core.escalation import SEVERITY_ORDER
from sysadmin.core.models.alert import Alert

logger = logging.getLogger(__name__)

#: The registry spelling, which is hyphenated (``sysadmin-assistant``) —
#: the name every estate surface resolves, not this checkout's directory.
SOURCE = "sysadmin-assistant"

#: The variable systemd sets for ``LoadCredential=``. Not a setting: the
#: no-environment-variables rule is about where settings live (ADR-0003).
CREDENTIALS_ENV = "CREDENTIALS_DIRECTORY"

Publisher = Callable[..., None]


def credential_path(config: MqttNotificationsConfig) -> Path | None:
    """``$CREDENTIALS_DIRECTORY/<credential>``, or ``None`` outside the unit."""
    directory = os.environ.get(CREDENTIALS_ENV)
    if not directory:
        return None
    return Path(directory) / config.credential


def build_payload(event: dict[str, Any], now: datetime) -> dict[str, Any]:
    """The wire shape. Flat, every value a string or null.

    ``source`` names the producer because a renderer showing two roots
    side by side must be able to say a failing disk is not a chore
    (alfred-glance's ideas.md, risk 3).
    """
    message = event.get("message")
    return {
        "source": SOURCE,
        "id": str(event.get("id", "")),
        "agent": str(event.get("agent", "")),
        "severity": str(event.get("severity", "")),
        "title": str(event.get("title", "")),
        "message": None if message is None else str(message),
        "published_at": now.isoformat(),
    }


class MqttAlertPublisher:
    """Subscribes to ``alert.raised``; publishes what clears the gate."""

    def __init__(
        self,
        *,
        session_factory=None,
        publisher: Publisher = publish,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session_factory = session_factory
        self._publish = publisher
        self._clock = clock

    async def on_alert_raised(self, event: dict[str, Any]) -> None:
        """Handle one ``alert.raised`` event. Never raises (rule 4)."""
        try:
            await self._handle(event)
        except Exception:  # noqa: BLE001 - reported, never propagated
            logger.exception("mqtt_alert_publish_error", extra={"event": event})

    async def _handle(self, event: dict[str, Any]) -> None:
        config = get_config().notifications.mqtt
        if not config.enabled:
            return

        severity = str(event.get("severity", "info"))
        floor = SEVERITY_ORDER.get(config.min_severity, SEVERITY_ORDER["critical"])
        if SEVERITY_ORDER.get(severity, 0) < floor:
            return

        if not await self._committed(event.get("id")):
            logger.info(
                "mqtt_alert_skipped_uncommitted",
                extra={"alert_id": event.get("id"), "title": event.get("title")},
            )
            return

        path = credential_path(config)
        if path is None:
            logger.warning(
                "mqtt_alert_no_credential",
                extra={
                    "detail": f"${CREDENTIALS_ENV} is unset — not started by "
                    "sysadmin.service, whose LoadCredential= supplies it",
                },
            )
            return

        topic = config.topic
        payload = build_payload(event, self._clock())
        try:
            identity = BrokerIdentity.from_credential_file(
                config.username, path, host=config.host, port=config.port
            )
            # Blocking subprocess; kept off the loop that serves :8500.
            await asyncio.to_thread(
                self._publish,
                identity,
                topic,
                payload,
                retain=False,
                timeout_s=config.timeout_seconds,
            )
        except PublishError as exc:
            logger.warning(
                "mqtt_alert_publish_failed",
                extra={
                    "topic": topic,
                    "title": payload["title"],
                    "returncode": exc.returncode,
                    "error": str(exc),
                },
            )
            return

        logger.info(
            "mqtt_alert_published",
            extra={"topic": topic, "severity": severity, "title": payload["title"]},
        )

    async def _committed(self, alert_id: Any) -> bool:
        """Whether the announced row exists. An unparseable id is not one."""
        try:
            key = uuid.UUID(str(alert_id))
        except ValueError:
            return False
        factory = self._session_factory
        if factory is None:
            # NullPool, an engine per call — the reason is desktop.py's
            # ``_factory`` docstring: this runs on a loop that is not the
            # one the pooled engine's connections belong to.
            from sysadmin.core.database import get_scheduler_session

            factory = get_scheduler_session
        async with factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(Alert).where(Alert.id == key)
            )
        return bool(count)


mqtt_alert_publisher = MqttAlertPublisher()
