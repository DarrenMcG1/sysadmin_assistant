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

Six rules, four of them the opposite of the obvious implementation:

1. **The population is what has been *said*, and what was said is now
   written down.**  It was what *this process* announced, in memory, and
   the two costs that narrowing carried were filed as ``SNAG-TRAY-008``
   and closed by rules 5 and 6 below.  What has not moved is the reason
   for the narrowing: a sweep straight over ``resolved IS false`` is an
   unbounded ``SELECT`` over the table whose unboundedness is
   ``SNAG-AGENT-005``'s bug, wired to a notification each.  The reminder
   query is still ``title IN (:titles_we_said)``, and the one read that
   is not — the adoption scan — is bounded in SQL, capped across sweeps
   and gated on the tray being away.
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
5. **The spoken set survives a restart, because otherwise the interval
   cannot be reached.**  ``desktop_notifications`` holds one row per
   fault this daemon is speaking for.  The number that settles it:
   ``sysadmin.service`` started **111 times in 28.26 days**, median
   uptime **1.77 h**, and **5 of 110** lives reached the 24 hours
   ``reminder_hours`` asks for — so an in-memory set made the reminder
   structurally unavailable on 95 % of this daemon's lives.  That is not
   a slow reminder, it is silence with a number beside it.  Three
   consequences, each the opposite of the obvious version.  The clock
   became a **wall** clock, since no monotonic value survives a process
   and ``CLOCK_MONOTONIC`` does not survive a suspend either, which a
   24-hour interval about elapsed human time should count;
   :class:`TrayPresence` keeps monotonic for its own 180-second
   question.  The store records what was **said** and never what the
   tray's presence implied, so the stamp-forward of rule 2 is not
   written — which bounds writes at one per notification and is safe
   because that same gate corrects a stale restored stamp on the first
   sweep after a restart, inside one grace window.  And the load happens
   **once per process, before the tray gate**, which is where the old
   "a sweep that has said nothing issues no query at all" went: not
   knowing what the last process said is indistinguishable from it
   having said nothing, which is the entry.
6. **A standing fault nobody announced is adopted, and the entry's own
   gate had to become an anchor to be reachable.**  A fault raised while
   the tray was watching is correctly not announced here, so when the
   tray dies nothing on this box speaks for it — the entry's first face,
   and a scoping question rather than a persistence one.  The entry asks
   for adoption *"only when the tray has been absent for a full
   ``reminder_hours``"*; a monotonic in-memory ``TrayPresence`` can only
   observe that in a process that has lived 24 hours, which rule 5's
   measurement says is one life in twenty-two.  So the absence sets the
   adopted fault's clock **back** instead of gating the adoption, capped
   at one interval: quiet by construction when the tray has only just
   left, immediate when nothing has watched for a day.  See
   :meth:`DesktopNotifier._adopt` for the bound, the ordering and why
   the two faces turn out to be multiplicative rather than independent.

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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from sysadmin.core.config import get_config
from sysadmin.core.escalation import humanise_hours
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.monitor.dnd import dnd_manager
from sysadmin.monitor.models.desktop_notification import DesktopNotification

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

#: The most standing faults the sweep will **adopt** — carry without
#: having announced them (rule 6).  Derived by reuse rather than
#: picked: a roll-up names :data:`_MAX_LISTED_TITLES` and then counts
#: the rest, so adopting more than it can name is adopting a fault
#: nobody will ever hear named, which is Session 46's rule — a count
#: is not news.  An announced fault was named once at its raise and is
#: not bounded by this.
MAX_ADOPTED_TITLES = _MAX_LISTED_TITLES


class TrayPresence:
    """Whether something is already reading the alerts route.

    Deliberately in-memory and monotonic-clocked.  Persisting it would
    make a daemon restart inherit a stale belief that the tray is up, and
    a wall-clock reading would be moved by NTP or a suspend/resume — this
    answers "how long since", which is the only question asked of it.

    Never having seen a poll is distinct from having seen one long ago:
    the first is a daemon that has just started (and may simply have
    started before the tray), the second is a tray that has gone away.
    Both allow the daemon to speak, and :meth:`absent_for` is the future
    grace period that distinction was kept for.
    """

    def __init__(self) -> None:
        self._last_seen: float | None = None
        #: Process start, so "never saw a tray" has a floor rather than
        #: an infinity.  See :meth:`absent_for`.
        self._started_at: float = time.monotonic()

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

    def absent_for(self) -> float:
        """How long nothing has watched — **a floor, never an estimate.**

        A daemon that has never seen a poll answers with its own uptime.
        That is deliberately an under-count: the tray may have been away
        for a week before this process started, and the process cannot
        know.  Under-counting delays an adoption's first reminder and can
        never hasten one, which is the direction every gate in this
        module errs in — and the case it under-counts is exactly the case
        :meth:`DesktopNotifier._load_spoken` covers, because a fault the
        previous instance had already adopted arrives with its clock
        intact and is not re-adopted.

        Built on :meth:`seconds_since_seen` rather than on ``_last_seen``
        so that one overridden leaf still reaches both readings.
        """
        elapsed = self.seconds_since_seen()
        if elapsed is not None:
            return elapsed
        return time.monotonic() - self._started_at


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
    #: When the episode began.  Kept apart from :attr:`last_spoken_at`,
    #: which every reminder moves — the sentence a reminder says measures
    #: the whole episode, and one field cannot be both.
    #: ``sysadmin_tray``'s ``_FingerprintState`` splits the same pair for
    #: the same reason.
    #:
    #: It was ``first_spoken_at`` until rule 6 arrived: an **adopted**
    #: fault has no first-spoken moment, and the honest reading for one
    #: is its alert row's own ``created_at`` — which is better evidence
    #: than the announced path has, since the reminder body says "after
    #: the first *alert*" and means it.
    episode_started_at: float
    last_spoken_at: float
    #: Reminders sent for this fault (evidence in the log, never ranked on).
    reminders_sent: int = 0
    #: True when this fault was adopted rather than announced — open, at
    #: or above the threshold, and never spoken for by this daemon.  Read
    #: rather than decorative: it is what bounds the adopted population
    #: against :data:`MAX_ADOPTED_TITLES`.
    adopted: bool = False

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
        # **Wall clock, and ``TrayPresence`` beside it stays monotonic.**
        # The two answer different questions and the difference is now
        # deliberate.  That class asks "how long since the tray polled"
        # over 180 seconds, where an NTP step is the larger error and
        # where a suspended box correctly counts nothing — neither
        # process was running.  A 24-hour reminder asks about elapsed
        # *human* time, and ``CLOCK_MONOTONIC`` stops during suspend, so
        # a workstation asleep overnight would pay nothing towards a
        # reminder that is precisely about the night.  It is also the
        # only reading a column can hold: no monotonic value survives a
        # process, which is what ``SNAG-TRAY-008``'s second face is.
        self._clock: Callable[[], float] = clock or time.time
        #: title -> what we said about it.  Backed by
        #: ``desktop_notifications`` since rule 5, so a restart inherits
        #: it rather than starting silent.
        self._spoken: dict[str, _SpokenFault] = {}
        #: Whether the store has been read in this process.  A failed
        #: read is retried on the next sweep and, until it succeeds,
        #: suppresses adoption — rule 6 must not run against a spoken set
        #: it knows to be incomplete.
        self._loaded = False

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
        fault = _SpokenFault(
            title=title,
            severity=severity,
            episode_started_at=now,
            last_spoken_at=now,
        )
        self._spoken[title] = fault
        await self._remember([fault])

    def _factory(self):
        """The session factory, resolved lazily so import order is free.

        **``get_scheduler_session``, never ``get_session_factory``**, and
        that is a fix rather than a preference.  Every database call this
        module makes happens on a loop that is not the application's:
        the sweep is an APScheduler job and ``scheduler._run_async``
        wraps each firing in its own ``asyncio.run``, while
        ``on_alert_raised`` is published from inside an agent's run,
        which is another one.  The app engine is pooled and its
        connections belong to the loop that opened them, so a checkout
        from a second loop raises ``RuntimeError: got Future … attached
        to a different loop`` and asyncpg then logs
        ``InternalClientError: got result for unknown protocol state``.
        ``get_scheduler_session`` uses ``NullPool`` and builds an engine
        per call, which is what every agent on this box already does.

        **It was already wrong, and nothing could reach it.**
        ``_still_open`` has resolved the pooled factory since Session 55
        and has never once succeeded on this box, because the sweep's old
        first gate — *"a daemon that has announced nothing issues no
        query"* — returned before it. Rule 5's load is the first call to
        get past that gate, so the reminder path had a **second**
        independent reason to be inert, found by deploying rather than by
        reading. Three `Log error: sysadmin.service` rows in the live
        table are what said so.

        One statement of it, because four callers read the database here
        — the two gates, the store and the adoption scan — and four
        copies of a lazy import is four places to get this wrong again.
        """
        if self._session_factory is not None:
            return self._session_factory
        from sysadmin.core.database import get_scheduler_session

        return get_scheduler_session

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
        factory = self._factory()
        if factory is None:
            return False

        try:
            async with factory() as session:
                open_count = await session.scalar(
                    select(func.count())
                    .select_from(Alert)
                    .where(Alert.title == title, unresolved())
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

        config = get_config().notifications.desktop
        if not config.enabled:
            return 0

        interval = config.reminder_hours * 3600
        if interval <= 0:
            return 0

        # Rule 5, and it has to come **before** the tray gate.  A
        # restored fault whose clock was last moved by a previous
        # instance is stale by exactly the age of this process, and the
        # gate below is what corrects it — a load placed after the gate
        # would leave the first sweep of a tray outage restating a fault
        # the tray restated ten minutes earlier, which is rule 2's own
        # defect arriving through the fix for a different one.
        #
        # This is also where the old "issue no query at all" gate went.
        # It cannot survive a durable spoken set: not knowing what the
        # last process said is indistinguishable from it having said
        # nothing, which is the entry.  What it becomes is **one query
        # per process** — after the first call this returns on a bool,
        # and on a box where the tray runs the gate below returns before
        # anything else is read.
        loaded = await self._load_spoken()

        if tray_presence.is_watching(config.tray_grace_seconds):
            # Rule 2: the tray is speaking, so the tray is what last
            # spoke.  Moving the clock rather than returning early is the
            # whole point — a plain `return` leaves these stale and the
            # first sweep after the tray dies restates faults it restated
            # minutes ago.
            #
            # Moved in memory and **not written down** (rule 5): the
            # store records what was *said*, and a watching tray is a
            # belief about another process rather than an utterance of
            # this one.  A restart therefore reloads a stale stamp — and
            # cannot act on it, because a reminder needs the tray absent
            # and this same gate corrects the stamp on the first sweep
            # after the restart, inside one grace window.
            for fault in self._spoken.values():
                fault.last_spoken_at = now
            return 0

        if self._spoken:
            still_open = await self._still_open(set(self._spoken))
            if still_open is None:
                return 0  # unreadable database → silence, as gate 2 does

            cleared = set(self._spoken) - still_open
            for title in cleared:
                # The fault cleared.  Dropping it means a recurrence
                # months later is announced as news by gate 2 rather than
                # arriving as a reminder of something already fixed.
                del self._spoken[title]
            await self._forget(cleared)

        threshold = SEVERITY_LEVELS.get(config.min_severity, 1)

        # Rule 6.  Only once the store has answered: adopting against a
        # spoken set known to be incomplete would re-announce a fault
        # this daemon is already carrying.
        if loaded:
            await self._adopt(now, threshold, interval)
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
        factory = self._factory()
        if factory is None:
            return None

        try:
            async with factory() as session:
                rows = await session.scalars(
                    select(Alert.title)
                    .where(Alert.title.in_(titles), unresolved())
                    .distinct()
                )
                return set(rows)
        except Exception:  # noqa: BLE001 - a blip must not become a storm
            logger.exception("desktop_reminder_open_check_failed")
            return None

    # ── the store (SNAG-TRAY-008, face 2) ─────────────────────────

    async def _load_spoken(self) -> bool:
        """Restore what a previous instance said.  True when the store answered.

        Read **once per process** and never again — the in-memory dict is
        authoritative from then on, because this process is the only
        writer of its own rows and a second read would let a stale row
        overwrite a fresher utterance.

        A title this instance has already spoken about **wins over the
        stored row**.  The order is not arbitrary: ``on_alert_raised`` can
        fire before the first sweep, and what it recorded is newer than
        anything a dead process wrote.

        Failure is soft and retried: ``_loaded`` is set only on success,
        so an unreachable database costs one sweep rather than the
        feature.  While it is unset, rule 6 does not run — see
        :meth:`_adopt`.
        """
        if self._loaded:
            return True
        factory = self._factory()
        if factory is None:
            return False

        restored = 0
        try:
            async with factory() as session:
                stored = list(await session.scalars(select(DesktopNotification)))
            # Mapped **inside** the guard, not after it.  A row this code
            # cannot read is the same event as a database it cannot
            # reach: one sweep lost, retried next time.  Outside, the
            # first surprising row takes down the whole sweep — including
            # the reminders it was about to send for faults it had read
            # perfectly well.
            for row in stored:
                if row.title in self._spoken:
                    continue
                self._spoken[row.title] = _SpokenFault(
                    title=row.title,
                    severity=row.severity,
                    episode_started_at=row.episode_started_at.timestamp(),
                    last_spoken_at=row.last_spoken_at.timestamp(),
                    reminders_sent=row.reminders_sent,
                    adopted=row.adopted,
                )
                restored += 1
        except Exception:  # noqa: BLE001 - a blip must not become a storm
            logger.exception("desktop_spoken_load_failed")
            return False

        self._loaded = True
        if restored:
            logger.info("desktop_spoken_restored", extra={"count": restored})
        return True

    async def _remember(self, faults: Iterable[_SpokenFault]) -> None:
        """Write down what was said.  Never raises, never blocks a toast.

        An upsert on ``title`` rather than a read-then-branch, because
        the title is the fault's identity and two rows for one fault must
        be unrepresentable rather than merely avoided — the unique
        constraint is the statement and this is the write that honours
        it.

        **The commit belongs to ``get_scheduler_session``**, which
        commits on a clean exit and rolls back on an exception — one
        owner, and a second ``commit()`` here would be a statement of
        somebody else's fact.

        A failed write costs a reminder after the next restart and
        nothing sooner, so it is logged and swallowed: the notification
        this is recording has already landed, and a store error must not
        turn into the sweep raising.
        """
        rows = [
            {
                "title": fault.title,
                "severity": fault.severity,
                "episode_started_at": datetime.fromtimestamp(
                    fault.episode_started_at, UTC
                ),
                "last_spoken_at": datetime.fromtimestamp(fault.last_spoken_at, UTC),
                "reminders_sent": fault.reminders_sent,
                "adopted": fault.adopted,
            }
            for fault in faults
        ]
        if not rows:
            return
        factory = self._factory()
        if factory is None:
            return

        try:
            async with factory() as session:
                stmt = pg_insert(DesktopNotification).values(rows)
                await session.execute(
                    stmt.on_conflict_do_update(
                        index_elements=[DesktopNotification.title],
                        set_={
                            "severity": stmt.excluded.severity,
                            "episode_started_at": stmt.excluded.episode_started_at,
                            "last_spoken_at": stmt.excluded.last_spoken_at,
                            "reminders_sent": stmt.excluded.reminders_sent,
                            "adopted": stmt.excluded.adopted,
                        },
                    )
                )
        except Exception:  # noqa: BLE001 - reported, never propagated
            logger.exception("desktop_spoken_write_failed")

    async def _forget(self, titles: Iterable[str]) -> None:
        """Drop the stored rows for faults that have cleared.

        Deleting rather than marking resolved: this table is not a
        history of notifications, it is the live spoken set, and a
        recurrence months later must arrive as news through gate 2 —
        which is the same reason the in-memory entry is deleted.
        """
        gone = list(titles)
        if not gone:
            return
        factory = self._factory()
        if factory is None:
            return

        try:
            async with factory() as session:
                await session.execute(
                    delete(DesktopNotification).where(
                        DesktopNotification.title.in_(gone)
                    )
                )
        except Exception:  # noqa: BLE001 - reported, never propagated
            logger.exception("desktop_spoken_delete_failed")

    # ── adoption (SNAG-TRAY-008, face 1) ──────────────────────────

    async def _adopt(self, now: float, threshold: int, interval: float) -> int:
        """Carry standing faults this daemon never announced.

        The entry's first face: a fault raised while the tray was
        watching is correctly *not* announced here, so it never entered
        the spoken set — and when the tray then dies, nothing on this box
        is speaking for it and nothing ever will.

        Four rules, three of them the opposite of the obvious
        implementation:

        1. **The entry's gate is an anchor here, not a refusal**, and the
           measurement is why.  It asks for adoption *"only when the tray
           has been absent for a full ``reminder_hours``"*.
           :class:`TrayPresence` is in-memory and monotonic on purpose,
           so a process can only observe 24 h of absence if it has lived
           24 h — and ``sysadmin.service`` started **111 times in 28.26
           days**, median uptime **1.77 h**, with **5 of 110** lives
           reaching 24 h.  Written as a refusal the fix would be
           unreachable on 95 % of this daemon's lives.  Written as an
           anchor it is the same rule with the same quiet: the adopted
           fault's ``last_spoken_at`` is set back by however long nothing
           has watched, capped at one interval, so a fault adopted the
           moment the tray leaves waits a full interval before it speaks
           and one adopted after a long silence speaks at once.
        2. **Which makes the two faces multiplicative rather than
           independent.**  Adoption alone re-adopts on every restart, so
           on a 1.77-hour daemon it would re-arm its own anchor for ever
           and never speak; the store is what carries the clock across.
           The store alone leaves this face exactly as the entry
           describes it.  Neither half is worth shipping without the
           other, which is the entry's *"the two faces have one root"*
           arriving as a mechanism rather than as a description.
        3. **Bounded in SQL and by the cap, not by the result being
           small.**  ``SNAG-AGENT-005``'s rule: the unbounded read is
           easy to write and nasty to ship.  ``GROUP BY title`` collapses
           a family writing one row per failed check to one candidate,
           ``LIMIT`` bounds what is materialised, and
           :data:`MAX_ADOPTED_TITLES` bounds the population across
           sweeps — without that last one the cap would be per-sweep and
           a 180-second cadence would adopt the whole open set five
           titles at a time.
        4. **Oldest standing first.**  A reminder is about a fault that
           has been unattended longest, and ``MIN(created_at)`` is the
           only ordering that survives the volume: a family re-raising
           every poll has a fresh newest row and a deduplicating one — the
           families ``SNAG-ESTATE-003`` is about — has a single old row,
           so newest-first would rank exactly backwards.

        **The cost is measured rather than argued.**  Live against
        665,942 rows with 3 open it is **0.086 ms and 8 buffers**, an
        index scan on ``idx_alerts_active`` — the partial index that
        already exists for the open set.  Driven at a synthetic **100,000
        open rows** in a rolled-back transaction it is **185 ms**, with
        the sort spilling to 1,102 temp pages.  That is the storm
        ``SNAG-AGENT-005`` produced, at a 180-second cadence, only while
        the tray is absent: a 0.1 % duty cycle in the degraded state this
        module exists for.
        """
        adopted_already = sum(1 for fault in self._spoken.values() if fault.adopted)
        room = MAX_ADOPTED_TITLES - adopted_already
        if room <= 0:
            return 0

        admitted = [
            rung for rung, level in SEVERITY_LEVELS.items() if level >= threshold
        ]
        if not admitted:
            return 0
        factory = self._factory()
        if factory is None:
            return 0

        opened = func.min(Alert.created_at)
        criteria = [unresolved(), Alert.severity.in_(admitted)]
        if self._spoken:
            criteria.append(Alert.title.notin_(list(self._spoken)))
        stmt = (
            select(
                Alert.title,
                opened.label("opened"),
                func.array_agg(Alert.severity.distinct()).label("rungs"),
            )
            .where(*criteria)
            .group_by(Alert.title)
            .order_by(opened)
            .limit(room)
        )

        try:
            async with factory() as session:
                candidates = (await session.execute(stmt)).all()
        except Exception:  # noqa: BLE001 - a blip must not become a storm
            logger.exception("desktop_adopt_failed")
            return 0

        if not candidates:
            return 0

        # Rule 1's anchor.  Capped at one interval so an adopted fault is
        # at worst immediately due, never overdue by days — a fault open
        # since March must not arrive as a backlog of missed reminders.
        silence = min(tray_presence.absent_for(), interval)
        fresh: list[_SpokenFault] = []
        for title, opened_at, rungs in candidates:
            fault = _SpokenFault(
                title=title,
                severity=_loudest(rungs or ()),
                episode_started_at=opened_at.timestamp(),
                last_spoken_at=now - silence,
                adopted=True,
            )
            self._spoken[title] = fault
            fresh.append(fault)

        await self._remember(fresh)
        logger.info(
            "desktop_faults_adopted",
            extra={
                "count": len(fresh),
                "titles": [fault.title for fault in fresh],
                "silence_s": round(silence, 1),
            },
        )
        return len(fresh)

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
            await self._remember(due)
            logger.info("desktop_reminder_sent", extra={"count": len(due)})
            return len(due)

        fault = due[0]
        # Clamped, because the two ends can disagree: an adopted fault's
        # episode starts at its alert row's ``created_at`` and a clock
        # step between the two readings would otherwise render a negative
        # age into a notification body.
        age = humanise_hours(max(0.0, now - fault.episode_started_at) / 3600)
        body = f"Still open {age} after the first alert"
        if not await self.send(fault.severity, fault.title, body):
            return 0
        fault.mark_spoken(now)
        await self._remember([fault])
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
