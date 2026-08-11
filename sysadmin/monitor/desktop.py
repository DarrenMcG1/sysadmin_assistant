"""Desktop notifications from the daemon — the tray's understudy.

The tray has spoken for this application since Phase 3: it polls
``GET /api/sysadmin/alerts`` and turns what it finds into D-Bus toasts,
with a policy (dedup, flap cooldown, coalescing, digest) that is the
reason a 186-row outage produces one notification rather than 186.  This
module does **not** compete with that.  It covers the case the tray
cannot: **the tray is not running.**  Until now that case was silent —
every alerting path in the daemon ends at a database row, and
``Notifier.send_notification`` (the only thing that ever consulted
``notifications.desktop``) had no production caller at all.

Three gates decide whether the daemon speaks, and each exists because of
something measured on this estate:

1. **Is anything else already watching?**  The tray marks its presence
   every time it polls the alerts route.  Inside the grace window the
   daemon stays quiet, so the two can never both toast the same alert.
   Any client of that route counts, not only the tray — the route has no
   way to tell them apart, and erring towards silence keeps the
   pre-existing behaviour when the answer is unclear.
2. **Is this a new incident, or the same one still failing?**  The
   monitor writes **one alert row per failed check**: 186 rows for one
   ``venture-assistant`` outage, 123 for one ``internet`` outage, 88
   criticals a day at steady state.  Notifying per row would be 186
   persistent toasts for one event.  The daemon speaks only when no
   other alert with that title is already open — the same
   "raise once while open" rule the idle nudges use — which turns those
   351 rows into roughly four notifications a week.
3. **Do the severity threshold and DND allow it?**  ``notifications
   .desktop.min_severity`` and the existing DND manager, unchanged.

**Recovery is deliberately not announced.**  ``alert.resolved`` carries
a *match pattern* rather than a subject — ``"Project % health critical"``
for the project organiser — so two of the three producers would publish
something that reads as gibberish on a desktop.  Announcing the start of
an outage and never its end is a real gap and is recorded as one rather
than papered over with a pattern string.

**The transport is ``notify-send``, not D-Bus directly.**  The backend
has no Qt and no D-Bus dependency (both live in the ``tray`` extra), and
adding one to the monitoring daemon to send a handful of notifications a
week is the wrong trade.  ``sysadmin.service`` is a *system* unit with a
minimal ``Environment=PATH`` and no session-bus address, so a bare
``notify-send`` fails with "Cannot autolaunch D-Bus without X11
$DISPLAY" — verified 2026-08-11.  The address is supplied here from the
well-known per-user socket path instead, which keeps the fix in code
rather than in a root-owned unit file nobody will remember to copy.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from sysadmin.core.config import get_config
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.dnd import dnd_manager

logger = logging.getLogger(__name__)

SEVERITY_LEVELS: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}

#: severity → freedesktop urgency.  ``critical`` is *not* mapped to the
#: ``critical`` urgency lightly: it makes the toast persist until
#: dismissed, which is right for the one-per-incident volume this module
#: emits and would be intolerable at one per failed check.
_URGENCY: dict[str, str] = {
    "info": "low",
    "warning": "normal",
    "critical": "critical",
}

_APP_NAME = "SysAdmin Monitor"

#: How long a notification stays up, in ms.  0 = until dismissed.
_TIMEOUT_MS: dict[str, int] = {"info": 5000, "warning": 10000, "critical": 0}

#: Bound on the subprocess, so a wedged notification daemon cannot hold
#: an event-loop thread.  Generous: this is a local socket write.
_SEND_TIMEOUT_S = 5.0


class TrayPresence:
    """Whether something is already reading the alerts route.

    Deliberately in-memory and monotonic-clocked.  Persisting it would
    make a daemon restart inherit a stale belief that the tray is up, and
    a wall-clock reading would be moved by NTP or a suspend/resume — this
    answers "how long since", which is the only question asked of it.

    Never having seen a poll is distinct from having seen one long ago:
    the first is a daemon that has just started (and may simply have
    started before the tray), the second is a tray that has gone away.
    Both currently allow the daemon to speak; the distinction is kept
    because it is the sort of thing a future grace period will need.
    """

    def __init__(self) -> None:
        self._last_seen: float | None = None

    def mark_seen(self) -> None:
        self._last_seen = time.monotonic()

    @property
    def ever_seen(self) -> bool:
        return self._last_seen is not None

    def seconds_since_seen(self) -> float | None:
        if self._last_seen is None:
            return None
        return time.monotonic() - self._last_seen

    def is_watching(self, grace_seconds: float) -> bool:
        """True when a poll arrived recently enough to count as present."""
        elapsed = self.seconds_since_seen()
        return elapsed is not None and elapsed <= grace_seconds


#: Process-wide, like ``dnd_manager`` beside it: the alerts route writes
#: to it and the event subscriber reads it, and they are not otherwise
#: connected.
tray_presence = TrayPresence()


def session_bus_address() -> str | None:
    """The session bus this process should talk to, or None if unreachable.

    An inherited ``DBUS_SESSION_BUS_ADDRESS`` always wins — a user who
    has set one means it.  Failing that the well-known socket for this
    uid is used **only if it exists**, so a daemon started at boot before
    anyone logs in reports "no bus" rather than handing ``notify-send``
    an address that will fail.
    """
    inherited = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
    if inherited:
        return inherited

    socket = Path(f"/run/user/{os.getuid()}/bus")
    return f"unix:path={socket}" if socket.exists() else None


class DesktopNotifier:
    """Speaks the daemon's alerts aloud, but only when nobody else will.

    Subscribed to ``alert.raised`` at startup.  That event is published
    *after* the raising agent's transaction commits (``_flush_events``),
    so the "is another alert with this title open?" query below sees a
    consistent view rather than racing the insert it is reacting to.
    """

    def __init__(self, session_factory=None) -> None:
        # Injected in tests; resolved lazily in production so import
        # order does not depend on the engine existing yet.
        self._session_factory = session_factory

    # ── the subscriber ────────────────────────────────────────────

    async def on_alert_raised(self, event: dict[str, Any]) -> None:
        """Handle one ``alert.raised`` event.

        Never raises.  A notification that fails is a notification that
        did not happen; a subscriber that raises takes down the event
        bus's task for every other subscriber too.
        """
        try:
            await self._handle(event)
        except Exception:  # noqa: BLE001 - reported, never propagated
            logger.exception("desktop_notify_failed", extra={"event": event})

    async def _handle(self, event: dict[str, Any]) -> None:
        config = get_config().notifications.desktop
        if not config.enabled:
            return

        severity = str(event.get("severity", "info"))
        if SEVERITY_LEVELS.get(severity, 0) < SEVERITY_LEVELS.get(
            config.min_severity, 1
        ):
            return

        if dnd_manager.should_suppress(severity):
            logger.debug("desktop_notify_suppressed_dnd", extra={"severity": severity})
            return

        if tray_presence.is_watching(config.tray_grace_seconds):
            logger.debug(
                "desktop_notify_skipped_tray_present",
                extra={"since_seen_s": round(tray_presence.seconds_since_seen() or 0, 1)},
            )
            return

        title = str(event.get("title", "")) or "SysAdmin alert"
        if not await self._is_new_incident(title):
            logger.debug("desktop_notify_skipped_ongoing", extra={"title": title})
            return

        body = f"{event.get('agent', 'sysadmin')} · {severity}"
        await self.send(severity, title, body)

    async def _is_new_incident(self, title: str) -> bool:
        """True when this title has exactly one unresolved alert — ours.

        Counting rather than comparing ids: the event carries the id as a
        string and the column is a UUID, and a count answers the question
        being asked ("is this the only one open?") without a cast that
        could quietly fail open and toast on every failed check.

        A database that cannot be reached returns **False** — silence.
        The alternative, treating an unknown as new, turns a database
        blip into a notification storm, which is the failure this module
        spends most of its gates avoiding.
        """
        factory = self._session_factory
        if factory is None:
            from sysadmin.core.database import get_session_factory

            factory = get_session_factory()
        if factory is None:
            return False

        try:
            async with factory() as session:
                open_count = await session.scalar(
                    select(func.count())
                    .select_from(Alert)
                    .where(Alert.title == title, Alert.resolved.is_(False))
                )
        except Exception:  # noqa: BLE001 - a blip must not become a storm
            logger.exception("desktop_notify_incident_check_failed")
            return False

        return (open_count or 0) <= 1

    # ── the transport ─────────────────────────────────────────────

    async def send(self, severity: str, title: str, body: str) -> bool:
        """Fire one desktop notification.  Returns whether it landed."""
        return await asyncio.to_thread(self._send_blocking, severity, title, body)

    def _send_blocking(self, severity: str, title: str, body: str) -> bool:
        binary = shutil.which("notify-send")
        if binary is None:
            logger.warning("desktop_notify_unavailable", extra={"reason": "notify-send"})
            return False

        address = session_bus_address()
        if address is None:
            logger.debug("desktop_notify_no_session_bus")
            return False

        try:
            result = subprocess.run(
                [
                    binary,
                    "--app-name", _APP_NAME,
                    "--urgency", _URGENCY.get(severity, "normal"),
                    "--expire-time", str(_TIMEOUT_MS.get(severity, 5000)),
                    "--", title, body,
                ],
                env={**os.environ, "DBUS_SESSION_BUS_ADDRESS": address},
                capture_output=True,
                text=True,
                timeout=_SEND_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            logger.warning("desktop_notify_send_failed", extra={"error": str(exc)})
            return False

        if result.returncode != 0:
            # notify-send exits 1 and explains itself on stderr; the
            # message ("Cannot autolaunch D-Bus without X11 $DISPLAY") is
            # the whole diagnosis, so it is logged rather than discarded.
            logger.warning(
                "desktop_notify_rejected",
                extra={"code": result.returncode, "stderr": result.stderr.strip()},
            )
            return False

        logger.info(
            "desktop_notify_sent", extra={"severity": severity, "title": title}
        )
        return True


desktop_notifier = DesktopNotifier()
