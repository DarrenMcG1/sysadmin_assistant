"""Stalled-agent escalation — making a detected fault stay audible.

Session 39, raised by the estate owner as "can we have someone who
watches the watchers".  The first thing worth recording is that **the
watcher already existed and worked**.  On 2026-08-10 ``file_organiser``
had run once in its life (``SNAG-AGENT-003``);
:func:`~sysadmin.monitor.self_monitor.build_self_report` detected it
correctly at interval × 3, ``_check_agent_liveness`` raised one alert at
09:07, the tray spoke once, and then nothing — for a fault that was
still true a day later.

Detection was never the gap.  ``_check_agent_liveness`` skips raising
while an unresolved row with that title is open, which is correct and is
what stopped the 1,664-row pile-up; combined with the tray's
``{severity}:{title}`` fingerprint it means the alarm **rings once, at
the quietest severity, and is then silent while the fault persists**.
Same shape as ``SNAG-DB-001`` and as the ``generated_at`` hole Session 36
found: absence of signal read as absence of problem.

**The owner's diagnosis, asked rather than assumed: "I never saw the
toast."**  Not ignored — away from the machine.  That rules out severity
tuning as the fix and is why the loud rung here is ``critical``
specifically:

- ``critical`` is **the only severity the tray renders non-transient**.
  ``sysadmin_tray/notifications.py`` sets ``transient=effective ==
  "info"`` on a first notification and ``transient=False`` in
  ``_maybe_escalate``, which fires for ``critical`` alone.  A ``warning``
  toast expires whether or not anyone was in the room; a ``critical``
  becomes a notification that is **still on screen when you come back**.
  The rung is not about volume, it is about persistence — which is
  exactly the failure the owner described.
- This is the opposite of the rule :mod:`sysadmin.projects.nudges`
  encodes, and deliberately.  A nudge never reaches ``critical`` because
  criticals break through DND and waking someone at 02:00 about a
  roadmap item is how a monitor gets muted wholesale.  A blind monitor
  is an incident, and ``notifications.dnd.enabled`` is ``false`` on this
  host in any case.

**The escalation clock runs from when the alarm rang, not from when the
stall began.**  Both are computable — the stall started at
``last_run_at + stall_window`` — and the alert row's ``created_at`` is
the right one for two reasons:

1. It is the honest statement of the fault.  "You were told this
   yesterday and it is still true" is what the second rung says; the
   thing that failed was the *telling*, so the telling is what the clock
   should measure.  A fault detected for the first time has had no
   chance to be seen, whatever its age, so it opens quiet.
2. Anchoring to the stall's own age would make a **daemon outage produce
   a wall of criticals on restart**.  While the service is down no agent
   runs, so every agent is stalled by hours; the first check after a
   restart would escalate all five at once.  That charges the estate for
   this application's downtime — the rule
   ``GET /api/services/reliability`` already encodes as "a gap in the
   series never costs points".

The clock does keep running while the daemon is down, which is correct:
a warning row two days old has genuinely stood unseen for two days, and
the first check after a restart escalates it once.

Recovery is unchanged and still resolves the row outright — see
``_check_agent_liveness``.  A recovered agent is not de-escalated
through the rungs; it is no longer a fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sysadmin.core.escalation import Ladder, Step, step_for

#: Title suffix for stalled-agent alerts.  The one place it is written —
#: raise, escalate and resolve all derive their title from
#: :func:`stall_title`, because a hand-written resolve pattern that
#: matches nothing fails silently and the table only grows.
STALL_TITLE_SUFFIX = "agent stalled"

#: Quiet at detection, loud once the warning has stood unseen.  See the
#: module docstring for why the loud rung is ``critical`` here and never
#: is for an idle nudge.
STALL_LADDER = Ladder(quiet="warning", loud="critical")


def stall_title(agent_name: str) -> str:
    """The alert title for ``agent_name``'s stall."""
    return f"{agent_name} {STALL_TITLE_SUFFIX}"


@dataclass(frozen=True)
class StallAlert:
    """One stalled agent, and the rung its alert should be sitting on."""

    agent_name: str
    severity: str
    step: Step
    #: The self-report entry this was built from, for the message.
    last_run_at: str | None
    stall_reason: str | None
    seconds_since_last_run: float | None
    interval_seconds: int | None
    #: When the *first* alert for this stall was raised, and how long ago.
    #: ``None`` on the first detection — nothing has been said yet.
    first_alerted_at: datetime | None
    hours_since_first_alert: float | None
    #: The configured gap, echoed so the message can name its own rule.
    escalate_after_hours: float

    @property
    def title(self) -> str:
        return stall_title(self.agent_name)

    @property
    def message(self) -> str:
        """One line for the tray.

        The escalated form leads with the elapsed time rather than the
        agent name: the reader has already been told *what* is broken and
        the new information is that it has been broken since then.
        """
        base = f"The {self.agent_name} agent has not run since {self.last_run_at}"
        if self.step is Step.ESCALATE and self.hours_since_first_alert is not None:
            hours = _humanise_hours(self.hours_since_first_alert)
            return (
                f"Still stalled {hours} after the first warning — "
                f"{self.agent_name} has not run since {self.last_run_at}"
            )
        if self.stall_reason:
            return f"{base} — {self.stall_reason}"
        return base

    @property
    def details(self) -> dict[str, Any]:
        """Everything the message compressed, for the alerts API.

        ``stalled_agent`` is load-bearing rather than decorative:
        ``_check_agent_liveness`` finds this agent's open stall rows by
        testing for that key, so an escalated row that omitted it would
        be invisible to the next run and the fault would be re-raised
        from the quiet rung for ever.

        ``first_alerted_at`` survives the escalation deliberately.  The
        quiet row is resolved when the loud one is raised, so without it
        the critical row could not say when the alarm first rang — and
        that is the only figure in the message that makes the escalation
        mean anything.
        """
        return {
            "stalled_agent": self.agent_name,
            "last_run_at": self.last_run_at,
            "seconds_since_last_run": self.seconds_since_last_run,
            "interval_seconds": self.interval_seconds,
            "kind": "agent_stall",
            "rung": self.severity,
            "escalated": self.step is Step.ESCALATE,
            "first_alerted_at": (
                self.first_alerted_at.isoformat() if self.first_alerted_at else None
            ),
            "hours_since_first_alert": (
                round(self.hours_since_first_alert, 2)
                if self.hours_since_first_alert is not None
                else None
            ),
            "escalate_after_hours": self.escalate_after_hours,
        }


def _humanise_hours(hours: float) -> str:
    """``hours`` as a phrase a notification can end a clause with."""
    if hours < 1:
        minutes = max(1, int(round(hours * 60)))
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    if hours < 48:
        whole = int(round(hours))
        return f"{whole} hour" if whole == 1 else f"{whole} hours"
    days = int(hours // 24)
    return f"{days} day" if days == 1 else f"{days} days"


#: An open row whose ``details`` carry this key belongs to a stall.
#: Matches the shape ``_check_agent_liveness`` has written since the
#: check was added, so rows raised before Session 39 are still found.
STALL_DETAIL_KEY = "stalled_agent"


@dataclass(frozen=True)
class OpenStall:
    """The unresolved stall row for one agent, as this module needs it."""

    alert_id: Any
    severity: str
    created_at: datetime


def evaluate(
    stalled_entries: list[dict[str, Any]],
    open_stalls: dict[str, OpenStall],
    *,
    escalate_after_hours: float,
    now: datetime | None = None,
) -> list[StallAlert]:
    """The stall alerts this run should write, loudest first.

    Args:
        stalled_entries: The ``agents`` entries from
            :func:`~sysadmin.monitor.self_monitor.build_self_report`
            whose ``stalled`` flag is set.
        open_stalls: This agent's unresolved stall rows, keyed by the
            *stalled agent's* name — not by title, because the title is
            derived and a caller that keys on it has to rebuild it.
        escalate_after_hours: Hours a quiet row may stand before the
            fault is restated at :attr:`STALL_LADDER.loud`.  The gap
            after the first rung, not a multiple of the agent's own
            interval: see :mod:`sysadmin.core.escalation`.
        now: Injected for tests; defaults to the current UTC time.

    :attr:`Step.HOLD` entries are **omitted from the result** rather than
    returned with a flag.  Every remaining item is something to write,
    so the caller cannot forget to check — the bug the original
    ``continue``-based loop was one edit away from.
    """
    at = now or datetime.now(UTC)
    alerts: list[StallAlert] = []

    for entry in stalled_entries:
        name = entry.get("name")
        if not name:
            continue

        existing = open_stalls.get(name)
        elapsed_hours = _hours_since(existing.created_at, at) if existing else 0.0

        # Threshold 0: the fault is on the ladder the moment it is seen.
        # Detection has already applied the agent's own grace window, so
        # a second waiting period before saying anything at all would
        # delay the *quiet* rung, which is not what the gap is for.
        severity = STALL_LADDER.severity_for(
            elapsed_hours, 0.0, escalate_after_hours
        )
        if severity is None:  # pragma: no cover — unreachable at threshold 0
            continue

        step = step_for(severity, existing.severity if existing else None)
        if step is Step.HOLD:
            continue

        alerts.append(StallAlert(
            agent_name=name,
            severity=severity,
            step=step,
            last_run_at=entry.get("last_run_at"),
            stall_reason=entry.get("stall_reason"),
            seconds_since_last_run=entry.get("seconds_since_last_run"),
            interval_seconds=entry.get("interval_seconds"),
            first_alerted_at=existing.created_at if existing else None,
            hours_since_first_alert=elapsed_hours if existing else None,
            escalate_after_hours=escalate_after_hours,
        ))

    alerts.sort(key=lambda a: (a.severity != "critical", a.agent_name))
    return alerts


def _hours_since(then: datetime, now: datetime) -> float:
    """Hours between ``then`` and ``now``, tolerating a naive ``then``.

    ``alerts.created_at`` is ``DateTime(timezone=True)``, so a row read
    back through asyncpg is aware and needs no coercion.  The guard is
    for the values that do **not** come from a round trip: an ``Alert``
    built in a test, and a default applied in Python rather than by the
    database.  ``self_monitor`` already carries the same two lines for
    ``agent_runs.started_at``, which is declared the same way — mixing an
    aware and a naive datetime raises ``TypeError`` rather than returning
    something merely wrong, so the whole health check would fail instead
    of escalating.  UTC is assumed because that is what
    :meth:`BaseAgent.raise_alert` writes.
    """
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return max(0.0, (now - then).total_seconds() / 3600.0)
