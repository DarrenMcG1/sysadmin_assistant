"""D-Bus desktop notifications plus the "notification calm" policy engine.

Two co-operating pieces live here:

``DbusNotifier``
    The transport.  Uses ``org.freedesktop.Notifications`` for native KDE
    integration: action buttons ("Restart", "Snooze 1h"), urgency hints,
    the ``transient`` hint (skip the notification history), update-in-place
    via ``replaces_id``, and the desktop-level ``Inhibited`` property
    (KDE Do Not Disturb / screen sharing).  Falls back to
    ``QSystemTrayIcon.showMessage()`` when D-Bus is unavailable.

``NotificationPolicy``
    The state machine that decides *whether* and *how loudly* to speak.
    Pure Python (no Qt, no D-Bus) so it is cheap to test: fed the alert
    payload from each poll, it returns a list of ``NotificationRequest``
    objects for the tray to dispatch.  It owns the shared fingerprint
    state used by dedup, flap cooldown, escalation, snooze, mute,
    coalescing and the warning digest.

Fingerprints are ``"{severity}:{title}"`` — the same content fingerprint
the tray has always used for dedup, now also the key for update-in-place
(``replaces_id``) and every suppression rule.
"""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from PyQt6.QtCore import QMetaType, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt6.QtDBus import (
    QDBusArgument,
    QDBusConnection,
    QDBusInterface,
    QDBusMessage,
    QDBusReply,
)
from PyQt6.QtWidgets import QSystemTrayIcon

from sysadmin.core.escalation import humanise_hours
from sysadmin_tray.models import AlertInfo, AlertsResponse

logger = logging.getLogger(__name__)

_DBUS_SERVICE = "org.freedesktop.Notifications"
_DBUS_PATH = "/org/freedesktop/Notifications"
_DBUS_IFACE = "org.freedesktop.Notifications"

_APP_NAME = "SysAdmin Monitor"
_APP_ICON = "dialog-warning"

# Severity ordering shared by the tray and the policy
SEVERITY_LEVELS: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}

# Map severity → D-Bus urgency hint (0 = low, 1 = normal, 2 = critical)
_URGENCY_MAP: dict[str, int] = {
    "info": 0,
    "warning": 1,
    "critical": 2,
}

# Map severity → notification timeout in ms (0 = persistent)
_TIMEOUT_MAP: dict[str, int] = {
    "info": 5000,
    "warning": 10000,
    "critical": 0,
}

# Fallback QSystemTrayIcon message icons
_FALLBACK_ICONS: dict[str, QSystemTrayIcon.MessageIcon] = {
    "info": QSystemTrayIcon.MessageIcon.Information,
    "warning": QSystemTrayIcon.MessageIcon.Warning,
    "critical": QSystemTrayIcon.MessageIcon.Critical,
}

# How long a cached answer to the desktop "Inhibited" query stays fresh
_INHIBIT_CACHE_SECONDS = 5.0

# Stable fingerprints for the synthetic (non-alert) notifications
FP_COALESCED = "sysadmin:new-alert-summary"
FP_DIGEST = "sysadmin:warning-digest"
FP_REMINDER = "sysadmin:still-open-summary"
FP_BACKEND_UNREACHABLE = "sysadmin:backend-unreachable"

#: What the tray calls a backend it cannot reach.  Deliberately about the
#: *monitoring*, not about the machine: ``health_review.confidence_phrase``
#: had to learn the same distinction after a model published "The machine
#: was down for much of the week" about a box that was merely unwatched.
BACKEND_UNREACHABLE_TITLE = "Monitoring is down"

#: ``critical`` is derived rather than picked.  Session 39 settled that
#: ``critical`` is the only severity the tray leaves on screen
#: (:data:`_TIMEOUT_MAP` gives it ``0`` and the request carries
#: ``transient=False``), and chose it for stalls because the owner's
#: reported failure was "I never saw the toast".  The fault this family
#: exists for ran **17h 09m** with the user at the machine and produced
#: no interruption at all, which is that failure with the room occupied.
BACKEND_UNREACHABLE_SEVERITY = "critical"

_MAX_LISTED_TITLES = 5


# ── Payload / request value objects ──────────────────────────────────


@dataclass(frozen=True)
class NotifyPayload:
    """The exact arguments handed to ``org.freedesktop.Notifications.Notify``.

    Kept as plain Python (no Qt types) so tests can assert on it without a
    live session bus; :meth:`DbusNotifier._send` does the Qt marshalling.
    """

    summary: str
    body: str
    replaces_id: int = 0
    actions: tuple[str, ...] = ()
    hints: dict[str, object] = field(default_factory=dict)
    timeout: int = 5000


@dataclass(frozen=True)
class NotificationRequest:
    """One notification the policy has decided to send."""

    summary: str
    body: str
    #: severity driving urgency / timeout / fallback icon.  A brand-new
    #: critical opens quiet ("info") and escalates later — see
    #: :attr:`alert_severity` for what the alert actually is.
    severity: str = "info"
    #: the alert's true severity, used for labels and summary counts
    alert_severity: str | None = None
    service_name: str | None = None
    fingerprint: str | None = None
    transient: bool = False
    snooze_key: str | None = None
    #: this replaces an existing popup in place — never fold into a summary
    escalation: bool = False
    #: a restatement of a fault that was already announced and is still
    #: open.  Kept apart from :attr:`escalation` because the two are
    #: opposite claims: an escalation says the fault got louder, a
    #: reminder says nothing has changed and that is the news.
    reminder: bool = False


# ── Policy configuration ─────────────────────────────────────────────


@dataclass
class NotificationSettings:
    """Tunables for :class:`NotificationPolicy` (mirrors config.yaml)."""

    enabled: bool = True
    min_severity: str = "critical"
    flap_cooldown_minutes: int = 30
    escalation_polls: int = 3
    coalesce_threshold: int = 2
    snooze_minutes: int = 60
    digest_mode: bool = False
    digest_interval_minutes: int = 60
    respect_desktop_dnd: bool = True
    muted_services: tuple[str, ...] = ()
    #: hours a still-open fingerprint stays quiet before being restated.
    #: 0 disables reminders entirely.  See :meth:`NotificationPolicy._reminder`
    #: for why the default is 24 and why it is derived rather than picked.
    reminder_hours: float = 24.0
    #: seconds an unreachable backend is tolerated before the tray speaks.
    #: 0 disables the family.  See
    #: :meth:`NotificationPolicy.evaluate_backend_unreachable` for the
    #: derivation and the measurement it was checked against.
    backend_unreachable_grace_seconds: float = 300.0

    @property
    def min_severity_level(self) -> int:
        """Numeric threshold; unknown names fall back to ``critical``."""
        return SEVERITY_LEVELS.get(self.min_severity, SEVERITY_LEVELS["critical"])


@dataclass
class _FingerprintState:
    """Per-fingerprint bookkeeping shared by every suppression rule."""

    fingerprint: str
    severity: str
    #: alert is present in the most recent poll and we've started an "episode"
    episode_open: bool = False
    #: consecutive polls the current episode has been active (escalation)
    polls_active: int = 0
    #: we already spoke about the current episode
    notified_this_episode: bool = False
    #: the escalation (loud) notification has been sent for this episode
    escalated: bool = False
    #: monotonic timestamp of the last notification actually sent
    last_notified_at: float | None = None
    #: monotonic timestamp of the episode's *opening* notification.  Kept
    #: separately from :attr:`last_notified_at`, which every reminder
    #: resets: the reminder's cadence runs from the last thing said, and
    #: the sentence it says ("still open N later") measures the whole
    #: episode.  One field cannot be both.
    first_notified_at: float | None = None
    #: reminders sent in the current episode (evidence, never ranked on)
    reminders_sent: int = 0
    #: episodes swallowed by the flap cooldown since the last notification
    suppressed_episodes: int = 0


def _humanise_minutes(minutes: float) -> str:
    """Render a window length for notification copy ("hour", "45 min")."""
    mins = round(minutes)
    if mins >= 60 and mins % 60 == 0:
        hours = mins // 60
        return "hour" if hours == 1 else f"{hours} hours"
    if mins <= 0:
        mins = 1
    return f"{mins} min"


def _count_line(severities: Iterable[str]) -> str:
    """"1 critical, 2 warning" — highest severity first, zeroes omitted."""
    counts = Counter(severities)
    parts = [
        f"{counts[sev]} {sev}"
        for sev in ("critical", "warning", "info")
        if counts.get(sev)
    ]
    return ", ".join(parts)


def _highest(severities: Iterable[str]) -> str:
    """The loudest severity in the batch (defaults to ``info``)."""
    return max(
        severities,
        key=lambda s: SEVERITY_LEVELS.get(s, 0),
        default="info",
    )


class NotificationPolicy:
    """Decides which alerts become desktop notifications, and how loudly.

    The whole point is *calm*: the same underlying problem should produce
    at most one interruption per cooldown window, several new problems in
    one poll produce one summary, and a brand-new critical starts quiet
    and only escalates if it is still failing several polls later.

    ``clock`` is injectable (defaults to :func:`time.monotonic`) purely so
    the cooldown / digest windows are testable without sleeping.
    """

    def __init__(
        self,
        settings: NotificationSettings | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings = settings or NotificationSettings()
        self.clock = clock
        self._states: dict[str, _FingerprintState] = {}
        self._snoozes: dict[str, float] = {}       # key → monotonic expiry
        self._digest: list[tuple[str, str]] = []   # (severity, title)
        self._digest_started_at: float | None = None

    # ── Public API ───────────────────────────────────────────────────

    def evaluate(
        self,
        alerts: AlertsResponse,
        *,
        dnd_active: bool = False,
        dnd_allow_critical: bool = True,
        desktop_inhibited: bool = False,
    ) -> list[NotificationRequest]:
        """Fold one poll's alerts into the notifications that should fire.

        Returns an empty list when everything is suppressed — the caller
        simply dispatches whatever comes back, in order.
        """
        now = self.clock()
        if not self.settings.enabled:
            return []

        requests: list[NotificationRequest] = []
        fresh: list[NotificationRequest] = []
        reminders: list[NotificationRequest] = []
        active: set[str] = set()

        for alert in alerts.alerts:
            if alert.acknowledged:
                continue

            fingerprint = self.fingerprint(alert)
            if fingerprint in active:
                continue  # several DB rows for one logical alert
            active.add(fingerprint)

            state = self._states.get(fingerprint)
            if state is None:
                state = _FingerprintState(
                    fingerprint=fingerprint, severity=alert.severity,
                )
                self._states[fingerprint] = state

            first_poll = not state.episode_open
            state.episode_open = True
            state.polls_active += 1

            request = self._consider(
                alert,
                state,
                now,
                first_poll=first_poll,
                dnd_active=dnd_active,
                dnd_allow_critical=dnd_allow_critical,
                desktop_inhibited=desktop_inhibited,
            )
            if request is None:
                continue
            if request.escalation:
                requests.append(request)
            elif request.reminder:
                reminders.append(request)
            else:
                fresh.append(request)

        requests = (
            self._coalesce(fresh)
            + self._coalesce(
                reminders,
                label="alerts still open",
                fingerprint=FP_REMINDER,
                reminder=True,
            )
            + requests
        )

        digest = self._maybe_flush_digest(now)
        if digest is not None:
            requests.append(digest)

        self._close_inactive(active, now)
        return requests

    def evaluate_backend_unreachable(
        self,
        unreachable_for: float,
        *,
        dnd_active: bool = False,
        dnd_allow_critical: bool = True,
        desktop_inhibited: bool = False,
    ) -> NotificationRequest | None:
        """Decide whether an unreachable backend is worth interrupting for.

        Called on every failed status poll with the episode's age in
        seconds, and it is the only path in this module that is not fed
        by an alert payload — by construction, since the process that
        serves the alerts is the one that has died (`SNAG-TRAY-009`).

        **The grace period is `max(3 × status_poll_seconds, 300 s)` = 300 s,
        and both halves are borrowed rather than invented.**  The
        multiplier is ``self_monitor.stall_grace_multiplier``'s 3.0, whose
        argument — one missed observation is merely late and clears on the
        next tick — transfers unchanged, and which
        ``notifications.desktop.tray_grace_seconds`` already applies to a
        tray poll ("3× the tray's alert_poll_seconds").  The floor is
        ``self_monitor.min_stall_grace_seconds``' 300, whose stated reason
        is literally *"so a restart doesn't flag the 60s log aggregator"* —
        this family's noise population, one domain over.

        Five rules, three of them the opposite of the obvious
        implementation and every one settled against the box rather than
        by argument:

        1. **The floor is what does the work, because the multiple alone
           derives from a leaf with two producers.**
           ``status_poll_seconds`` defaults to ``10`` in
           :class:`sysadmin_tray.config.TrayConfig` and is ``30`` in the
           shipped ``config.yaml``, so "3× the poll interval" is 30 s on a
           default install and 90 s here — a 3× spread in a number whose
           job is to clear a daemon restart that does not move with the
           poll interval at all.  The noise is bounded in **seconds** and
           the observation is counted in **polls**; a pure poll count
           would change meaning silently the day anyone edits the
           interval, which is why the threshold is stored in seconds and
           the polls only wake it.
        2. **The bound it clears is measured, not assumed.**  Across 30
           days the daemon's journal holds **104 deploy restarts of 2, 3,
           12 or 13 seconds — maximum 13 s** — and nothing between that
           and a reboot; the tray's own journal holds **27** windows
           where it polled and got nothing, **every one exactly 60.0 s**,
           which is one missed poll.  Against that, 300 s is 23× the
           restart bound and 5× the widest window the tray has ever
           observed.  The nearest real fault is **18,235 s** (5h 04m),
           so the two populations are three orders of magnitude apart and
           every value between them produces identical output —
           ``INCIDENT_WINDOW_SECONDS``' shape.  300 sits *below* the
           geometric midpoint (487 s) on purpose: the cost curve is
           asymmetric, since firing early costs a toast on each of 104
           deploys a month and firing late costs minutes of an outage
           that ran hours.
        3. **``escalation_polls`` is deliberately not applied.**  A new
           ``critical`` normally opens at ``info`` and escalates once it
           is still failing several polls later
           (:meth:`_first_notification`, :meth:`_maybe_escalate`).
           Waiting out the grace **is** that test, already passed, so
           applying both would speak quietly at 300 s and loudly at
           390 s about one fault.  The opening notification is therefore
           the loud one, and it is the only family here that opens that
           way.
        4. **The episode is closed by the connection, never by an alert
           poll.**  :meth:`_close_inactive` resets any fingerprint absent
           from a poll, and this fingerprint is absent from every poll
           because it is not an alert row — so it is excluded there and
           :meth:`backend_reachable` owns it.  Letting an alerts payload
           close it would make a question about reachability answerable
           by the surface that cannot be read while it is open.
        5. **Recovery is not announced**, matching the daemon's rule for
           ``alert.resolved``.  The icon already goes green within one
           poll, and a second toast per restart is the noise this whole
           derivation exists to avoid.

        The honest cost, filed rather than implied: the state is in
        memory, so a tray restart re-opens the episode and re-speaks
        after a fresh grace — :meth:`_reminder`'s rule 1 for its reason,
        and here it is closer to desirable than not, since a tray
        restarting into a dead daemon should say so.
        """
        settings = self.settings
        grace = settings.backend_unreachable_grace_seconds
        if not settings.enabled or grace <= 0:
            return None
        if unreachable_for < grace:
            return None
        if (
            SEVERITY_LEVELS[BACKEND_UNREACHABLE_SEVERITY]
            < settings.min_severity_level
        ):
            return None

        now = self.clock()
        state = self._states.get(FP_BACKEND_UNREACHABLE)
        if state is None:
            state = _FingerprintState(
                fingerprint=FP_BACKEND_UNREACHABLE,
                severity=BACKEND_UNREACHABLE_SEVERITY,
            )
            self._states[FP_BACKEND_UNREACHABLE] = state
        state.episode_open = True
        state.polls_active += 1

        if self._is_snoozed(FP_BACKEND_UNREACHABLE, None):
            return None
        if self._suppressed_by_dnd(
            BACKEND_UNREACHABLE_SEVERITY,
            dnd_active=dnd_active,
            dnd_allow_critical=dnd_allow_critical,
            desktop_inhibited=desktop_inhibited,
        ):
            return None

        if state.notified_this_episode:
            if not self._reminder_due(state, now):
                return None
            state.last_notified_at = now
            state.reminders_sent += 1
            return self._backend_unreachable_request(
                state, unreachable_for, reminder=True,
            )

        # Flap cooldown, for the same reason every other family gets it:
        # a backend that fails the grace, recovers and fails it again
        # inside the window is one story.  Empty population as measured —
        # a restart loop is terminal at StartLimitBurst=5 within 600 s and
        # each restart is 13 s, so it never reaches the grace at all —
        # kept because its absence would be a special case, not a rule.
        cooldown = settings.flap_cooldown_minutes * 60
        if (
            cooldown > 0
            and state.last_notified_at is not None
            and now - state.last_notified_at < cooldown
        ):
            state.suppressed_episodes += 1
            return None

        state.suppressed_episodes = 0
        state.notified_this_episode = True
        state.last_notified_at = now
        state.first_notified_at = now
        state.reminders_sent = 0
        return self._backend_unreachable_request(state, unreachable_for)

    def backend_reachable(self) -> None:
        """Close the unreachable episode; the backend answered.

        The counterpart to :meth:`evaluate_backend_unreachable`, and the
        only thing that closes that episode (rule 4 there).
        ``last_notified_at`` is deliberately **kept**: it is what the flap
        cooldown measures against, so forgetting it here would let a
        backend that fails the grace twice in five minutes speak twice.
        """
        state = self._states.get(FP_BACKEND_UNREACHABLE)
        if state is None:
            return
        state.episode_open = False
        state.polls_active = 0
        state.notified_this_episode = False
        state.escalated = False
        state.first_notified_at = None
        state.reminders_sent = 0
        if state.last_notified_at is None:
            del self._states[FP_BACKEND_UNREACHABLE]

    def _backend_unreachable_request(
        self, state: _FingerprintState, unreachable_for: float, *,
        reminder: bool = False,
    ) -> NotificationRequest:
        """Build the notification for an unreachable backend."""
        elapsed = humanise_hours(unreachable_for / 3600)
        lines = [
            f"No answer from the monitoring service for {elapsed}.",
            "Alerts, service checks and log capture are all stopped.",
        ]
        # What this cannot say, and why SNAG-SYSD-005's login replay stays
        # load-bearing: with the daemon dead the tray cannot read the
        # alert row, so it cannot name _schema_diagnosis's CAUSE: line or
        # the one command that fixes it.  It can say *that* monitoring is
        # down; only the replay can say *why*.
        lines.append("systemctl status sysadmin — journalctl -u sysadmin -n 50")
        return NotificationRequest(
            summary=f"{BACKEND_UNREACHABLE_SEVERITY.upper()}: sysadmin",
            body=f"{BACKEND_UNREACHABLE_TITLE}\n" + "\n".join(lines),
            severity=BACKEND_UNREACHABLE_SEVERITY,
            alert_severity=BACKEND_UNREACHABLE_SEVERITY,
            fingerprint=state.fingerprint,
            transient=False,
            snooze_key=f"fp:{state.fingerprint}",
            reminder=reminder,
        )

    def snooze(self, key: str, minutes: int | None = None) -> None:
        """Silence a fingerprint or service until the snooze expires.

        ``key`` is one of the keys handed out via
        :attr:`NotificationRequest.snooze_key` — ``"service:redis"`` or
        ``"fp:critical:Disk full"``.
        """
        window = self.settings.snooze_minutes if minutes is None else minutes
        self._snoozes[key] = self.clock() + window * 60
        logger.info("notifications snoozed for %s (%d min)", key, window)

    def is_snoozed(self, key: str) -> bool:
        """Whether *key* is currently snoozed (expired entries are dropped)."""
        expiry = self._snoozes.get(key)
        if expiry is None:
            return False
        if expiry <= self.clock():
            del self._snoozes[key]
            return False
        return True

    def flush_digest(self, now: float | None = None) -> NotificationRequest | None:
        """Emit the accumulated warning digest, if there is anything to say."""
        if not self._digest:
            return None
        now = self.clock() if now is None else now
        started = self._digest_started_at or now
        items = self._digest
        self._digest = []
        self._digest_started_at = None

        # Report the digest window, not the odd extra minutes a poll
        # interval adds on top of it ("in the last hour", not "65 min")
        elapsed = max((now - started) / 60, 1)
        window = _humanise_minutes(
            min(elapsed, self.settings.digest_interval_minutes or elapsed)
        )
        titles = [title for _, title in items]
        lines = [_count_line(sev for sev, _ in items)]
        lines.extend(f"• {t}" for t in titles[:_MAX_LISTED_TITLES])
        if len(titles) > _MAX_LISTED_TITLES:
            lines.append(f"…and {len(titles) - _MAX_LISTED_TITLES} more")

        return NotificationRequest(
            summary=f"SysAdmin digest — {len(items)} alerts in the last {window}",
            body="\n".join(lines),
            severity="info",
            alert_severity=_highest(sev for sev, _ in items),
            fingerprint=FP_DIGEST,
            transient=False,  # a digest is exactly what history is for
        )

    @property
    def pending_digest_count(self) -> int:
        """How many warnings are waiting in the digest buffer."""
        return len(self._digest)

    def reset(self) -> None:
        """Forget all state (used on shutdown / reconfiguration)."""
        self._states.clear()
        self._snoozes.clear()
        self._digest.clear()
        self._digest_started_at = None

    @staticmethod
    def fingerprint(alert: AlertInfo) -> str:
        """Content fingerprint — stable across DB rows for one problem."""
        return f"{alert.severity}:{alert.title}"

    # ── Decision helpers ─────────────────────────────────────────────

    def _consider(
        self,
        alert: AlertInfo,
        state: _FingerprintState,
        now: float,
        *,
        first_poll: bool,
        dnd_active: bool,
        dnd_allow_critical: bool,
        desktop_inhibited: bool,
    ) -> NotificationRequest | None:
        """Decide what (if anything) this alert should produce this poll."""
        settings = self.settings
        severity = alert.severity
        is_critical = severity == "critical"

        if SEVERITY_LEVELS.get(severity, 0) < settings.min_severity_level:
            return None
        if self._is_muted(alert):
            logger.debug("notification muted by config: %s", alert.title)
            return None
        if self._is_snoozed(state.fingerprint, alert.service_name):
            return None
        if self._suppressed_by_dnd(
            severity,
            dnd_active=dnd_active,
            dnd_allow_critical=dnd_allow_critical,
            desktop_inhibited=desktop_inhibited,
        ):
            return None

        # Digest mode: warnings never interrupt, they queue up instead.
        if settings.digest_mode and not is_critical:
            if first_poll:
                self._digest.append((severity, alert.title))
                if self._digest_started_at is None:
                    self._digest_started_at = now
            return None

        if state.notified_this_episode:
            # Escalation first: it is the louder statement, and it resets
            # the reminder clock, so a fault climbing a ladder is never
            # also reminded about in the same poll.
            escalated = self._maybe_escalate(alert, state, now)
            if escalated is not None:
                return escalated
            return self._reminder(alert, state, now)

        # Still waiting out the flap cooldown from the previous episode?
        cooldown = settings.flap_cooldown_minutes * 60
        if (
            cooldown > 0
            and state.last_notified_at is not None
            and now - state.last_notified_at < cooldown
        ):
            if first_poll:
                state.suppressed_episodes += 1
                logger.debug(
                    "flap suppressed (%d× since last alert): %s",
                    state.suppressed_episodes, alert.title,
                )
            return None

        return self._first_notification(alert, state, now)

    def _first_notification(
        self, alert: AlertInfo, state: _FingerprintState, now: float,
    ) -> NotificationRequest:
        """Build the opening notification for an episode."""
        severity = alert.severity
        is_critical = severity == "critical"
        quiet_first = is_critical and self.settings.escalation_polls > 1
        effective = "info" if quiet_first else severity

        lines = [alert.title]
        if state.suppressed_episodes and state.last_notified_at is not None:
            flaps = state.suppressed_episodes + 1
            window = _humanise_minutes((now - state.last_notified_at) / 60)
            lines.append(f"{alert.title} flapped {flaps}× in the last {window}")
        if alert.message:
            lines.append(alert.message)

        state.suppressed_episodes = 0
        state.notified_this_episode = True
        state.escalated = False
        state.last_notified_at = now
        state.first_notified_at = now
        state.reminders_sent = 0

        return NotificationRequest(
            summary=f"{severity.upper()}: sysadmin",
            body="\n".join(lines),
            severity=effective,
            alert_severity=severity,
            service_name=alert.service_name,
            fingerprint=state.fingerprint,
            transient=effective == "info",
            snooze_key=self.snooze_key_for(alert, state.fingerprint),
        )

    def _maybe_escalate(
        self, alert: AlertInfo, state: _FingerprintState, now: float,
    ) -> NotificationRequest | None:
        """Promote a still-failing critical from quiet to persistent."""
        if alert.severity != "critical" or state.escalated:
            return None
        if self.settings.escalation_polls <= 1:
            return None
        if state.polls_active < self.settings.escalation_polls:
            return None

        state.escalated = True
        state.last_notified_at = now

        lines = [
            alert.title,
            f"Still failing after {state.polls_active} checks",
        ]
        if alert.message:
            lines.append(alert.message)

        return NotificationRequest(
            summary="CRITICAL: sysadmin",
            body="\n".join(lines),
            severity="critical",
            alert_severity="critical",
            service_name=alert.service_name,
            fingerprint=state.fingerprint,
            transient=False,
            snooze_key=self.snooze_key_for(alert, state.fingerprint),
            escalation=True,
        )

    def _reminder(
        self, alert: AlertInfo, state: _FingerprintState, now: float,
    ) -> NotificationRequest | None:
        """Restate a fault that was announced once and is still open.

        **Why this lives here and not in the daemon** (SNAG-ESTATE-003).
        Five families deduplicate on an open row by design — the estate
        judge, ``monitor/collation``, the unit sweep's roll-up and the
        two the sysadmin agent's ``_raise_judged`` covers — so each rings
        **once, at the quietest severity, and is then silent while the
        fault persists**.  That is Session 39's sentence, and the snag
        proposed fixing it with a third rung in
        :mod:`sysadmin.core.escalation`.  Measured, that rung cannot be
        heard: :meth:`fingerprint` is ``"{severity}:{title}"`` and
        :attr:`_FingerprintState.notified_this_episode` only clears when
        that pair is **absent from a poll**, which a resolve-and-re-raise
        inside one agent run never produces.  A repeat that keeps both
        constant is silent whatever the daemon writes, so the only two
        audible repeats are a severity change (``critical``, reserved for
        faults on this box) or a forked title (which four separate rules
        in this repository forbid, because the title is the identity
        key).  A repeat that is neither is a *notification* decision, and
        notification policy is this module's by construction.

        Four rules:

        1. **The clock runs from the last thing said, not from the row's
           age.**  ``AlertInfo.created_at`` is available and is the wrong
           anchor for the same reason :mod:`sysadmin.monitor.stalls`
           gives — the thing that failed was the *telling*, so the
           telling is what the clock measures.  It also keeps the single
           injected clock that makes every window here testable without
           sleeping.  The honest cost: this state is in memory, so a tray
           restart re-announces every open fault as new and restarts the
           cadence.
        2. **The interval is derived, not picked.**  A family that owns a
           ladder must reach its loud rung as *news*, never as a repeat
           it has already heard at the quiet severity; the only
           escalation gap configured on this box is
           ``self_monitor.escalate_after_hours: 24``.  At 24 h the
           laddered families escalate to a different fingerprint before
           any reminder is due — a new episode, announced immediately —
           so the reminder is what the families with **no** ladder get,
           which is exactly the population the snag names.
        3. **A reminder is never transient.**  The failure it exists to
           fix is a toast in an empty room, so it must survive one:
           :data:`_TIMEOUT_MAP` still expires it from the screen, and
           ``transient=False`` is what keeps it in the notification
           history — ``flush_digest``'s rule, for its reason.
        4. **The fingerprint is unchanged.**  It is the same problem, so
           it updates in place and shares one snooze key: snoozing a
           fault silences its reminders without a second control.

        Not reached in digest mode for anything below ``critical``, and
        that is deliberate rather than missed: digest mode's contract is
        that warnings never interrupt, and a reminder is an interrupt.
        Making the digest itself periodic is a separate question about a
        mode that is ``false`` on this host and has no live observations
        behind it.
        """
        if not self._reminder_due(state, now):
            return None

        # `is None`, never `or`: a monotonic clock reading exactly 0.0 is
        # falsy, and `or` would fall back to `last_notified_at` — which
        # every reminder resets, so each one would report the interval
        # rather than the age.  Caught by a probe whose clock starts at
        # zero; the test fixtures start at 1000.0 and would not have.
        opened = (
            state.last_notified_at
            if state.first_notified_at is None
            else state.first_notified_at
        )
        state.last_notified_at = now
        state.reminders_sent += 1

        severity = alert.severity
        lines = [
            alert.title,
            f"Still open {humanise_hours((now - opened) / 3600)} "
            "after the first alert",
        ]
        if alert.message:
            lines.append(alert.message)

        return NotificationRequest(
            summary=f"{severity.upper()}: sysadmin",
            body="\n".join(lines),
            severity=severity,
            alert_severity=severity,
            service_name=alert.service_name,
            fingerprint=state.fingerprint,
            transient=False,
            snooze_key=self.snooze_key_for(alert, state.fingerprint),
            reminder=True,
        )

    def _reminder_due(self, state: _FingerprintState, now: float) -> bool:
        """Whether ``reminder_hours`` has elapsed since the last thing said.

        Extracted so the alert family and the unreachable-backend family
        cannot come to disagree about when a restatement is due — two
        statements of one interval is ``SNAG-DB-003``'s shape at the size
        of a comparison.  ``0`` disables reminders for both, which is the
        contract ``reminder_hours`` already publishes.
        """
        interval = self.settings.reminder_hours * 3600
        if interval <= 0 or state.last_notified_at is None:
            return False
        return now - state.last_notified_at >= interval

    def _coalesce(
        self,
        fresh: list[NotificationRequest],
        *,
        label: str = "new alerts",
        fingerprint: str = FP_COALESCED,
        reminder: bool = False,
    ) -> list[NotificationRequest]:
        """Fold several notifications from one poll into a single summary.

        Reminders are folded **separately** from new alerts, on the same
        threshold and into their own fingerprint.  Mixing them would
        report a fault announced yesterday inside a summary headed "N new
        alerts", which is the one thing a reminder is not — and the
        estate judge can put five idle-nudge rows on screen at once
        (``attention_max_rows``), so the volume this exists to fold is
        real rather than hypothetical.
        """
        threshold = max(self.settings.coalesce_threshold, 2)
        if len(fresh) < threshold or len(fresh) < 2:
            return fresh

        # Counts name the *real* severities; urgency follows the effective
        # ones, so a batch of brand-new criticals is still a quiet opener
        # that each alert's own escalation can follow up loudly.
        reported = [r.alert_severity or r.severity for r in fresh]
        urgency = _highest(r.severity for r in fresh)
        lines = [_count_line(reported)]
        lines.extend(f"• {r.body.splitlines()[0]}" for r in fresh[:_MAX_LISTED_TITLES])
        if len(fresh) > _MAX_LISTED_TITLES:
            lines.append(f"…and {len(fresh) - _MAX_LISTED_TITLES} more")

        return [
            NotificationRequest(
                summary=f"{len(fresh)} {label}",
                body="\n".join(lines),
                severity=urgency,
                alert_severity=_highest(reported),
                fingerprint=fingerprint,
                # A roll-up of reminders keeps rule 3: it is the same
                # restatement, so it survives an empty room too.
                transient=False if reminder else urgency != "critical",
                reminder=reminder,
            )
        ]

    def _maybe_flush_digest(self, now: float) -> NotificationRequest | None:
        if not self._digest:
            return None
        started = self._digest_started_at or now
        if now - started < self.settings.digest_interval_minutes * 60:
            return None
        return self.flush_digest(now)

    def _close_inactive(self, active: set[str], now: float) -> None:
        """Reset episodes for resolved alerts, and prune cold state."""
        cooldown = self.settings.flap_cooldown_minutes * 60
        for fingerprint, state in list(self._states.items()):
            if fingerprint in active:
                continue
            if fingerprint == FP_BACKEND_UNREACHABLE:
                # Never in ``active``: it is not an alert row, so "absent
                # from this poll" carries no information about it.
                # :meth:`backend_reachable` owns its lifecycle —
                # ``evaluate_backend_unreachable`` rule 4.
                continue
            state.episode_open = False
            state.polls_active = 0
            state.notified_this_episode = False
            state.escalated = False
            state.first_notified_at = None
            state.reminders_sent = 0

            if state.last_notified_at is None:
                del self._states[fingerprint]
            elif now - state.last_notified_at > cooldown:
                # Cooldown fully expired — nothing left to remember
                del self._states[fingerprint]

    # ── Suppression rules ────────────────────────────────────────────

    def _is_muted(self, alert: AlertInfo) -> bool:
        """Whether the alert belongs to a service muted in config.yaml."""
        muted = {m.lower() for m in self.settings.muted_services if m}
        if not muted:
            return False
        service = (alert.service_name or "").lower()
        if service:
            return service in muted
        # Alerts without an explicit service still name it in the title
        title = alert.title.lower()
        return any(re.search(rf"\b{re.escape(name)}\b", title) for name in muted)

    def _is_snoozed(self, fingerprint: str, service_name: str | None) -> bool:
        if self.is_snoozed(f"fp:{fingerprint}"):
            return True
        return bool(service_name) and self.is_snoozed(
            f"service:{(service_name or '').lower()}"
        )

    def _suppressed_by_dnd(
        self,
        severity: str,
        *,
        dnd_active: bool,
        dnd_allow_critical: bool,
        desktop_inhibited: bool,
    ) -> bool:
        """Combine the app's own DND with the desktop's inhibition state.

        The two are complementary and the *more restrictive* answer wins:

        * The app's DND (``/api/sysadmin/dnd``, scheduled or toggled from
          the tray menu) is authoritative for criticals — with
          ``allow_critical`` set they break through, without it nothing
          gets out.
        * The desktop's inhibition (KDE Do Not Disturb, screen sharing,
          full-screen presentation) suppresses everything *except*
          criticals, which the notification server itself will queue into
          history anyway.
        """
        is_critical = severity == "critical"
        if dnd_active and not (is_critical and dnd_allow_critical):
            return True
        return (
            self.settings.respect_desktop_dnd
            and desktop_inhibited
            and not is_critical
        )

    @staticmethod
    def snooze_key_for(alert: AlertInfo, fingerprint: str) -> str:
        """Snoozing a service silences all of its alerts, not just this one."""
        if alert.service_name:
            return f"service:{alert.service_name.lower()}"
        return f"fp:{fingerprint}"


class DbusNotifier(QObject):
    """D-Bus notification transport with action buttons and replace-in-place.

    Signals:
        ``restart_requested(service_name)`` — the user clicked "Restart".
        ``snooze_requested(snooze_key)`` — the user clicked "Snooze 1h".
    """

    restart_requested = pyqtSignal(str)  # service_name
    snooze_requested = pyqtSignal(str)   # snooze key (service:… / fp:…)

    def __init__(
        self,
        fallback_tray: QSystemTrayIcon | None = None,
        parent: QObject | None = None,
        snooze_minutes: int = 60,
    ) -> None:
        super().__init__(parent)
        self._fallback_tray = fallback_tray
        self._pending_actions: dict[int, str] = {}  # notification_id → service_name
        self._pending_snoozes: dict[int, str] = {}  # notification_id → snooze key
        self._fp_ids: dict[str, int] = {}           # fingerprint → notification_id
        self.snooze_minutes = snooze_minutes
        self._available = False
        self._bus: QDBusConnection | None = None
        self._iface: QDBusInterface | None = None
        self._props: QDBusInterface | None = None
        self._inhibit_supported = True
        self._inhibit_cached = False
        self._inhibit_checked_at: float | None = None

        self._init_dbus()

    def _init_dbus(self) -> None:
        """Connect to the session bus and create the notifications interface."""
        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            logger.warning("D-Bus session bus not connected — using fallback")
            return

        self._bus = bus
        self._iface = QDBusInterface(
            _DBUS_SERVICE, _DBUS_PATH, _DBUS_IFACE, bus,
        )
        if not self._iface.isValid():
            logger.warning(
                "D-Bus notifications interface unavailable — using fallback"
            )
            self._iface = None
            return

        # Separate proxy for the property reads (desktop DND)
        self._props = QDBusInterface(
            _DBUS_SERVICE, _DBUS_PATH, "org.freedesktop.DBus.Properties", bus,
        )

        # Subscribe to ActionInvoked and NotificationClosed signals
        bus.connect(
            _DBUS_SERVICE,
            _DBUS_PATH,
            _DBUS_IFACE,
            "ActionInvoked",
            self._on_action_invoked,
        )
        bus.connect(
            _DBUS_SERVICE,
            _DBUS_PATH,
            _DBUS_IFACE,
            "NotificationClosed",
            self._on_notification_closed,
        )

        self._available = True
        logger.debug("D-Bus notifications initialised")

    @property
    def available(self) -> bool:
        """Whether D-Bus notifications are available."""
        return self._available

    # ── Sending ──────────────────────────────────────────────────────

    def notify(
        self,
        summary: str,
        body: str,
        severity: str = "info",
        service_name: str | None = None,
        *,
        fingerprint: str | None = None,
        transient: bool = False,
        snooze_key: str | None = None,
    ) -> bool:
        """Send a desktop notification.

        Returns True if sent via D-Bus, False if it fell back to
        ``showMessage()``.  When *service_name* is given the notification
        carries a "Restart" button; when *snooze_key* is given it also
        carries "Snooze <n>".  When *fingerprint* matches a notification
        we sent earlier, the popup is *replaced* rather than stacked.
        """
        payload = self.build_payload(
            summary, body, severity,
            service_name=service_name,
            fingerprint=fingerprint,
            transient=transient,
            snooze_key=snooze_key,
        )

        if not self._available or self._iface is None or self._bus is None:
            self._fallback_notify(summary, body, severity)
            return False

        notification_id = self._send(payload)
        if notification_id is None:
            self._fallback_notify(summary, body, severity)
            return False

        logger.debug(
            "D-Bus notification %d (replaces %d): [%s] %s",
            notification_id, payload.replaces_id, severity, summary,
        )

        if notification_id:
            if fingerprint:
                self._fp_ids[fingerprint] = notification_id
            if service_name:
                self._pending_actions[notification_id] = service_name
            if snooze_key:
                self._pending_snoozes[notification_id] = snooze_key
        return True

    def build_payload(
        self,
        summary: str,
        body: str,
        severity: str = "info",
        *,
        service_name: str | None = None,
        fingerprint: str | None = None,
        transient: bool = False,
        snooze_key: str | None = None,
    ) -> NotifyPayload:
        """Assemble the Notify arguments (pure — no D-Bus traffic)."""
        actions: list[str] = []
        if service_name:
            actions += ["restart", "Restart"]
        if snooze_key:
            actions += ["snooze", self.snooze_label()]

        hints: dict[str, object] = {"urgency": _URGENCY_MAP.get(severity, 1)}
        if transient:
            hints["transient"] = True

        return NotifyPayload(
            summary=summary,
            body=body,
            replaces_id=self._fp_ids.get(fingerprint, 0) if fingerprint else 0,
            actions=tuple(actions),
            hints=hints,
            timeout=_TIMEOUT_MAP.get(severity, 5000),
        )

    def snooze_label(self) -> str:
        """Button label for the snooze action ("Snooze 1h" by default)."""
        minutes = self.snooze_minutes
        if minutes >= 60 and minutes % 60 == 0:
            return f"Snooze {minutes // 60}h"
        return f"Snooze {minutes}m"

    def _send(self, payload: NotifyPayload) -> int | None:
        """Marshal *payload* onto the bus; returns the notification id.

        Kept separate from :meth:`notify` so the (untestable without a
        live session bus) Qt marshalling is isolated behind a seam.
        """
        if self._bus is None:
            return None

        # Build a typed D-Bus message matching signature: susssasa{sv}i
        # QDBusInterface.call() infers INT32 from Python int and
        # array-of-variant from Python list — both wrong for Notify.
        msg = QDBusMessage.createMethodCall(
            _DBUS_SERVICE, _DBUS_PATH, _DBUS_IFACE, "Notify",
        )

        # PyQt6 strict enums: .value converts Type enum → int for add()/beginArray()
        uint_type = QMetaType.Type.UInt.value
        qstring_type = QMetaType.Type.QString.value

        # replaces_id must be UINT32 (not INT32)
        replaces_arg = QDBusArgument()
        replaces_arg.add(payload.replaces_id, uint_type)

        # actions must be array-of-string (not array-of-variant)
        actions_arg = QDBusArgument()
        actions_arg.beginArray(qstring_type)
        for action in payload.actions:
            actions_arg.add(action)
        actions_arg.endArray()

        # hints as plain dict — Qt auto-marshals dict[str, QVariant] → a{sv}
        hints: dict[str, QVariant] = {
            key: QVariant(value) for key, value in payload.hints.items()
        }

        msg.setArguments([
            _APP_NAME,                     # app_name:       s
            QVariant(replaces_arg),        # replaces_id:    u
            _APP_ICON,                     # app_icon:       s
            payload.summary,               # summary:        s
            payload.body,                  # body:           s
            QVariant(actions_arg),         # actions:        as
            QVariant(hints),               # hints:          a{sv}
            payload.timeout,               # expire_timeout: i
        ])

        reply = QDBusReply(self._bus.call(msg))
        if not reply.isValid():
            logger.warning(
                "D-Bus Notify call failed: %s — using fallback",
                reply.error().message(),
            )
            return None
        return int(reply.value())

    def _fallback_notify(
        self, summary: str, body: str, severity: str,
    ) -> None:
        """Fall back to QSystemTrayIcon.showMessage()."""
        if self._fallback_tray is None:
            logger.debug("no fallback tray — notification dropped: %s", summary)
            return

        icon = _FALLBACK_ICONS.get(severity, QSystemTrayIcon.MessageIcon.Information)
        timeout = _TIMEOUT_MAP.get(severity, 5000)
        self._fallback_tray.showMessage(summary, body, icon, timeout)

    # ── Desktop-level Do Not Disturb ─────────────────────────────────

    def desktop_inhibited(self) -> bool:
        """Whether the desktop is suppressing notifications right now.

        Reads the ``Inhibited`` property of
        ``org.freedesktop.Notifications`` — true during KDE's Do Not
        Disturb, screen sharing, or a full-screen presentation.  The
        answer is cached briefly so a poll with many alerts makes one
        blocking D-Bus call, not one per alert.

        Degrades gracefully: implementations that do not expose the
        property (older notification daemons, the fallback path) simply
        report False and are never queried again.
        """
        if not self._available or not self._inhibit_supported:
            return False

        now = time.monotonic()
        if (
            self._inhibit_checked_at is not None
            and now - self._inhibit_checked_at < _INHIBIT_CACHE_SECONDS
        ):
            return self._inhibit_cached

        value = self._read_inhibited()
        if value is None:
            self._inhibit_supported = False
            self._inhibit_cached = False
            logger.debug(
                "notification daemon does not expose Inhibited — "
                "desktop DND detection disabled"
            )
            return False

        self._inhibit_cached = value
        self._inhibit_checked_at = now
        return value

    def _read_inhibited(self) -> bool | None:
        """One D-Bus read of the ``Inhibited`` property; None if unreadable.

        Goes through ``org.freedesktop.DBus.Properties.Get`` rather than
        ``QDBusInterface.property()``: PyQt6's property accessor returns
        None for this property even on daemons that plainly expose it
        (verified against Plasma's notification daemon).
        """
        if self._props is None:
            return None
        try:
            reply = QDBusReply(
                self._props.call("Get", _DBUS_IFACE, "Inhibited")
            )
            if not reply.isValid():
                logger.debug(
                    "Inhibited property unavailable: %s", reply.error().message(),
                )
                return None
            value = reply.value()
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug("Inhibited property unreadable: %s", exc)
            return None
        return value if isinstance(value, bool) else None

    # ── Signal handlers ──────────────────────────────────────────────

    @pyqtSlot(int, str)
    def _on_action_invoked(self, notification_id: int, action_key: str) -> None:
        """Handle D-Bus ActionInvoked signal."""
        service_name = self._pending_actions.pop(notification_id, None)
        snooze_key = self._pending_snoozes.pop(notification_id, None)

        if action_key == "restart" and service_name:
            logger.info(
                "restart requested via notification for %s", service_name,
            )
            self.restart_requested.emit(service_name)
        elif action_key == "snooze" and snooze_key:
            logger.info("snooze requested via notification for %s", snooze_key)
            self.snooze_requested.emit(snooze_key)

    @pyqtSlot(int, int)
    def _on_notification_closed(self, notification_id: int, reason: int) -> None:
        """Handle D-Bus NotificationClosed signal — clean up pending actions."""
        self._pending_actions.pop(notification_id, None)
        self._pending_snoozes.pop(notification_id, None)
        # The fingerprint → id mapping deliberately survives: a stale
        # replaces_id is harmless (the daemon treats unknown ids as new),
        # and keeping it means a state change still replaces a popup the
        # user has not dismissed yet.

    def cleanup(self) -> None:
        """Release D-Bus resources."""
        self._pending_actions.clear()
        self._pending_snoozes.clear()
        self._fp_ids.clear()
        self._iface = None
        self._props = None
        self._available = False
