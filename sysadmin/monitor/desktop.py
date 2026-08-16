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

**A fault that stands has to keep speaking, and gate 2 is what stops
it** (``SNAG-TRAY-007``).  "Speak once per incident" is right for the
186 rows of one outage and wrong for the outage itself: the daemon said
it once, at the quietest severity that passed gate 3, and was then
silent for as long as the fault lasted.  That is Session 39's sentence —
a warning that fires once is indistinguishable from one that got fixed —
and Session 53 fixed it for the tray in ``sysadmin_tray/notifications``
:meth:`NotificationPolicy._reminder`, where notification policy lives.
None of that reaches here: this module is subscribed to ``alert.raised``
and has no clock, so there is no moment at which it could notice that a
fault it announced six hours ago is still open.

:meth:`DesktopNotifier.sweep_reminders` is that moment.  It is a
scheduled job (``sysadmin/core/jobs.py``) rather than a call bolted to
the end of an agent run, because an agent that reminded on this module's
behalf would be a **second owner** of a lifecycle this module owns —
the defect this repository has now found at four scales, and the reason
the snag asked for a decision rather than a patch.

Four rules, three of them the opposite of the obvious implementation:

1. **The population is what *this process* announced, never the open
   rows.**  A sweep over ``resolved IS false`` would adopt every fault
   the tray was speaking for while it was up, and announce the lot on
   the first sweep after the tray dies — an unbounded ``SELECT`` over
   the table whose unboundedness is ``SNAG-AGENT-005``'s bug, wired to a
   notification each.  The spoken set is in memory, so the query is
   ``title IN (:titles_we_said)`` and a sweep that has said nothing
   issues no query at all.  The honest cost is stated rather than
   discovered later: a fault raised while the tray was up is never
   adopted when the tray goes away, and a daemon restart forgets
   everything it had announced.
2. **Tray presence resets the clock, it does not merely skip the
   sweep.**  ``tray_grace_seconds`` already decides precedence for the
   raise path and answers the repeat path the same way — but *skipping*
   would leave ``last_spoken_at`` stale, so the first sweep after a tray
   outage would restate a fault the tray itself restated ten minutes
   earlier.  While something is polling the route, the last thing said
   was said by it.
3. **A roll-up takes the loudest rung it swallows**, and folds at two —
   the tray's ``coalesce_threshold`` and Session 52's rule.  Collapsing
   notifications must not also quieten them: ``notify-send`` has no
   ``replaces_id`` here, so six due reminders would be six toasts.
4. **A reminder that did not land does not move the clock.**
   :meth:`send` returns whether it landed, and a failed send (no session
   bus, no ``notify-send``) leaves the fault due — so the reminder
   arrives on the sweep after the bus comes back rather than a full
   interval later.  The same reason nothing is recorded as spoken until
   the opening notification has actually landed.

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
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from sysadmin.core.config import get_config
from sysadmin.core.escalation import humanise_hours
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

#: Due reminders at or above this count fold into one notification.  Two,
#: matching ``NotificationSettings.coalesce_threshold`` — the tray has
#: ``replaces_id`` and updates a toast in place, and this module has only
#: ``notify-send``, so the case for folding here is strictly stronger.
_ROLLUP_THRESHOLD = 2

#: Titles named inside a roll-up before it starts counting instead.
_MAX_LISTED_TITLES = 5


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


def _loudest(severities: Iterable[str]) -> str:
    """The noisiest of several severities — a roll-up never quietens."""
    return max(severities, key=lambda s: SEVERITY_LEVELS.get(s, 0), default="info")


@dataclass
class _SpokenFault:
    """One fault this process announced and may have to restate.

    Keyed by title, because the title is the identity of a fault
    everywhere else in this repository — the tray fingerprints on
    ``{severity}:{title}``, every dedup and every resolve keys on it, and
    four separate rules forbid forking it.  Severity is carried rather
    than keyed on so that an escalation (the quiet row resolved, a loud
    one raised under the same title) simply replaces the entry: it
    arrives as its own ``alert.raised`` event, is a new incident by
    gate 2, and restarts the clock as news should.
    """

    title: str
    severity: str
    #: When the opening notification landed.  Kept apart from
    #: :attr:`last_spoken_at`, which every reminder moves — the sentence
    #: a reminder says measures the whole episode, and one field cannot
    #: be both.  ``sysadmin_tray``'s ``_FingerprintState`` splits the
    #: same pair for the same reason.
    first_spoken_at: float
    last_spoken_at: float
    #: Reminders sent for this fault (evidence in the log, never ranked on).
    reminders_sent: int = 0

    def mark_spoken(self, now: float) -> None:
        self.last_spoken_at = now
        self.reminders_sent += 1


class DesktopNotifier:
    """Speaks the daemon's alerts aloud, but only when nobody else will.

    Subscribed to ``alert.raised`` at startup.  That event is published
    *after* the raising agent's transaction commits (``_flush_events``),
    so the "is another alert with this title open?" query below sees a
    consistent view rather than racing the insert it is reacting to.

    :meth:`sweep_reminders` is the other entry point, called on a
    schedule so that a fault announced once and still open is restated —
    see the module docstring for why that could not be a call from an
    agent.
    """

    def __init__(self, session_factory=None, clock: Callable[[], float] | None = None) -> None:
        # Injected in tests; resolved lazily in production so import
        # order does not depend on the engine existing yet.
        self._session_factory = session_factory
        # Monotonic for the reason ``TrayPresence`` is: this answers "how
        # long since", and a wall clock is moved by NTP and by suspend.
        self._clock: Callable[[], float] = clock or time.monotonic
        #: title -> what we said about it.  In memory, so a restart
        #: forgets it (module docstring, rule 1).
        self._spoken: dict[str, _SpokenFault] = {}

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
        if not await self.send(severity, title, body):
            # Nothing was said, so there is nothing to restate.  Recording
            # it anyway would start a reminder clock for a notification
            # that never reached a screen.
            return

        now = self._clock()
        self._spoken[title] = _SpokenFault(
            title=title,
            severity=severity,
            first_spoken_at=now,
            last_spoken_at=now,
        )

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

    # ── the repeat path (SNAG-TRAY-007) ───────────────────────────

    async def sweep_reminders(self) -> int:
        """Restate every fault this process announced that is still open.

        Scheduled as ``desktop_reminder_sweep``; returns how many faults
        were restated, which is what the log line carries.  Never raises,
        for :meth:`on_alert_raised`'s reason one layer over: a scheduled
        job that throws is a job APScheduler stops trusting, and the
        failure it would be reporting is a notification that did not
        happen.
        """
        try:
            return await self._sweep()
        except Exception:  # noqa: BLE001 - reported, never propagated
            logger.exception("desktop_reminder_sweep_failed")
            return 0

    async def _sweep(self) -> int:
        now = self._clock()

        # Cheapest gate first and deliberately so: a daemon that has
        # announced nothing — the steady state on a box where the tray
        # runs — issues no query and reads no config beyond this.
        if not self._spoken:
            return 0

        config = get_config().notifications.desktop
        if not config.enabled:
            return 0

        interval = config.reminder_hours * 3600
        if interval <= 0:
            return 0

        if tray_presence.is_watching(config.tray_grace_seconds):
            # Rule 2: the tray is speaking, so the tray is what last
            # spoke.  Moving the clock rather than returning early is the
            # whole point — a plain `return` leaves these stale and the
            # first sweep after the tray dies restates faults it restated
            # minutes ago.
            for fault in self._spoken.values():
                fault.last_spoken_at = now
            return 0

        still_open = await self._still_open(set(self._spoken))
        if still_open is None:
            return 0  # unreadable database → silence, as gate 2 does

        for title in set(self._spoken) - still_open:
            # The fault cleared.  Dropping it means a recurrence months
            # later is announced as news by gate 2 rather than arriving
            # as a reminder of something already fixed.
            del self._spoken[title]

        threshold = SEVERITY_LEVELS.get(config.min_severity, 1)
        due = [
            fault
            for _, fault in sorted(self._spoken.items())
            if now - fault.last_spoken_at >= interval
            and SEVERITY_LEVELS.get(fault.severity, 0) >= threshold
            # DND is re-checked rather than inherited from the raise: a
            # reminder is an interrupt, and 24 hours later the window has
            # moved.  A suppressed reminder does **not** move the clock,
            # so it goes out when the window lifts rather than a whole
            # interval later.
            and not dnd_manager.should_suppress(fault.severity)
        ]
        if not due:
            return 0

        return await self._restate(due, now)

    async def _still_open(self, titles: set[str]) -> set[str] | None:
        """Which of *titles* still have an unresolved row; None on failure.

        Bounded by the titles handed in — ``SNAG-AGENT-005``'s rule, where
        the same query written as "every unresolved row this agent owns"
        pulled 593,814 ORM objects on its first live run.  Scalars rather
        than ORM objects for the same reason: the answer is a set of
        strings.
        """
        factory = self._session_factory
        if factory is None:
            from sysadmin.core.database import get_session_factory

            factory = get_session_factory()
        if factory is None:
            return None

        try:
            async with factory() as session:
                rows = await session.scalars(
                    select(Alert.title)
                    .where(Alert.title.in_(titles), Alert.resolved.is_(False))
                    .distinct()
                )
                return set(rows)
        except Exception:  # noqa: BLE001 - a blip must not become a storm
            logger.exception("desktop_reminder_open_check_failed")
            return None

    async def _restate(self, due: list[_SpokenFault], now: float) -> int:
        """Send the due reminders — one notification, or one roll-up."""
        if len(due) >= _ROLLUP_THRESHOLD:
            # Rule 3: the loudest rung it swallows.  Folding must not
            # quieten, or the fix for noise becomes the reason the one
            # entry that earned a toast never got one.
            severity = _loudest(fault.severity for fault in due)
            lines = [f"• {fault.title}" for fault in due[:_MAX_LISTED_TITLES]]
            if len(due) > _MAX_LISTED_TITLES:
                lines.append(f"…and {len(due) - _MAX_LISTED_TITLES} more")
            summary = f"{len(due)} faults still open"
            if not await self.send(severity, summary, "\n".join(lines)):
                return 0
            for fault in due:
                fault.mark_spoken(now)
            logger.info("desktop_reminder_sent", extra={"count": len(due)})
            return len(due)

        fault = due[0]
        age = humanise_hours((now - fault.first_spoken_at) / 3600)
        body = f"Still open {age} after the first alert"
        if not await self.send(fault.severity, fault.title, body):
            return 0
        fault.mark_spoken(now)
        logger.info(
            "desktop_reminder_sent",
            extra={"title": fault.title, "reminders_sent": fault.reminders_sent},
        )
        return 1

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
