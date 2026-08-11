"""Idle nudges — "you said you would, and you haven't" (Session 31).

A different question from the health score, and deliberately not derived
from it.  The score asks *is this repository tidy*: README present, no
stale branches, markers under control.  A nudge asks whether a **stated
commitment** has moved.  The two disagree constantly and both readings
are correct — ``venture-assistant`` scores 100 and could still be sitting
on the same next action for a fortnight, while a repository scoring 55
for missing documentation may be the one being worked on hardest.

**Eligibility is not defined here.**  It lives in
:func:`sysadmin.projects.next_action.eligible_candidates`, which
``GET /api/projects/next`` also uses: active status, a next action a
human wrote (``handoff`` or ``tasks``, never the board's ``git``
fallback), and not one of the honest "nothing queued" sentences.  A
project can therefore never be nudged about work the endpoint would not
have offered — one definition of a commitment, two readers.

**The ladder is quiet, then loud.**  At the threshold the nudge is
``info``; after the escalation gap it is re-raised as ``warning``.  On
this host ``tray.notify_min_severity`` is ``warning``, so the first rung
marks the alerts list and the tray badge without speaking and the second
is the first thing that toasts.  That is a property of config.yaml
rather than of this module, and it is the knob to reach for if nudges
arrive too late — the thresholds here say when a commitment counts as
broken, not how loudly to say so.  (The gate is the ``tray:`` section:
``notifications.desktop.min_severity`` looks like it and is read by
nothing — SNAG-CFG-001.)

**The escalation gap, not a multiplier.**  A project may relax its own
threshold in ``.project.yaml`` (``idle_nudge_days``); the gap between
the two rungs stays as configured globally, so a project that waits 21
days escalates at 28 rather than at 42.  The per-project knob decides
when the clock starts, not how patient the escalation is — a multiplier
would make a relaxed project doubly hard to hear from, which is the
opposite of what relaxing the first threshold asks for.

Raising is **once per open nudge**, not once per scan.  The organiser
runs daily and :meth:`BaseAgent.raise_alert` inserts unconditionally;
re-raising would write one row per scan per stuck project, which is the
1,664-row pile-up this repository has already been through, expressed as
a feature.  See :meth:`ProjectOrganiserAgent._nudge_idle_projects`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sysadmin.projects.next_action import Candidate, Streak

#: The one place a nudge's title is built.  Raise, escalate and resolve
#: all derive from it, for the reason ``_alert_title`` records in
#: :mod:`sysadmin.projects.agent`: a hand-written resolve pattern that
#: matches nothing fails silently and the table only grows.
NUDGE_TITLE_SUFFIX = "next action idle"

#: Severity ordering, matching the tray's ``SEVERITY_LEVELS``.  A nudge
#: never reaches ``critical``: an unattended commitment is not an
#: incident, and criticals break through DND by configuration
#: (``notifications.dnd.allow_critical``) — waking someone at 02:00
#: about a roadmap item is how a monitor gets muted wholesale.
SEVERITY_ORDER: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}


def nudge_title(project_name: str) -> str:
    """The alert title for ``project_name``'s idle-nudge."""
    return f"Project {project_name} {NUDGE_TITLE_SUFFIX}"


#: SQL ``LIKE`` form of the above, for the set-based resolve.
NUDGE_TITLE_LIKE = f"Project % {NUDGE_TITLE_SUFFIX}"


@dataclass(frozen=True)
class Nudge:
    """One project whose stated next action has stood too long."""

    project_name: str
    project_path: str
    next_action: str
    next_action_source: str
    #: Days the action has stood, from the snapshot series.
    days: int
    #: The threshold this project crossed (its own, or the default).
    threshold: int
    severity: str
    since: datetime | None
    scans: int
    #: The run reaches the oldest scan held, so ``days`` is a lower bound.
    at_window_edge: bool

    @property
    def title(self) -> str:
        return nudge_title(self.project_name)

    @property
    def message(self) -> str:
        """One line for the tray, hedged where the evidence is.

        ``at least`` is not decoration: a run reaching the edge of the
        90-day retention window has an unknown true length, and a nudge
        that states an exact figure it cannot support is the sort of
        small dishonesty that gets a whole surface distrusted.
        """
        at_least = "at least " if self.at_window_edge else ""
        days = "1 day" if self.days == 1 else f"{self.days} days"
        return (
            f"Unchanged for {at_least}{days} "
            f"(nudges after {self.threshold}): {_shorten(self.next_action)}"
        )

    @property
    def details(self) -> dict[str, Any]:
        """Everything the message had to compress, for the alerts API."""
        return {
            "project": self.project_name,
            "path": self.project_path,
            "next_action": self.next_action,
            "next_action_source": self.next_action_source,
            "days_unchanged": self.days,
            "unchanged_since": self.since.isoformat() if self.since else None,
            "unchanged_scans": self.scans,
            "at_window_edge": self.at_window_edge,
            "threshold_days": self.threshold,
            "kind": "idle_nudge",
        }


#: How much of a next action reaches a desktop notification.  Handoff
#: sentences on this estate run to 300+ characters with embedded shell
#: and file paths; a toast that long is truncated by the notification
#: daemon at a point nobody chose.
_MESSAGE_ACTION_CHARS = 120


def _shorten(action: str) -> str:
    collapsed = " ".join(action.split())
    if len(collapsed) <= _MESSAGE_ACTION_CHARS:
        return collapsed
    return collapsed[: _MESSAGE_ACTION_CHARS - 1].rstrip() + "…"


def severity_for(days: int, threshold: int, escalation_gap: int) -> str | None:
    """Which rung of the ladder ``days`` reaches, or ``None`` for none.

    ``None`` rather than a "no nudge" severity because the caller's next
    decision is whether to raise at all, and a sentinel string would
    have to be checked for at every use.

    An ``escalation_gap`` of 0 is legitimate — it means "loud from the
    first rung" — and yields ``warning`` at the threshold itself.
    """
    if days < threshold:
        return None
    if days >= threshold + escalation_gap:
        return "warning"
    return "info"


def evaluate(
    candidates: Sequence[Candidate],
    streaks: dict[str, Streak],
    thresholds: dict[str, int],
    *,
    default_days: int,
    escalation_gap: int,
) -> list[Nudge]:
    """The nudges this scan warrants, loudest and longest-standing first.

    A candidate with no entry in ``streaks`` is **skipped, not treated as
    zero**: an absent series means the history query returned nothing for
    it, which happens on a project's very first scan.  Nudging on
    unknown history would fire on the day a repository is created.

    Args:
        candidates: From
            :func:`~sysadmin.projects.next_action.eligible_candidates`.
        streaks: Per project, from
            :func:`~sysadmin.projects.snapshots.load_action_streaks`.
        thresholds: Per-project override, keyed by project name.  Missing
            keys take ``default_days``.
        default_days: The global threshold from config.yaml.
        escalation_gap: Days after a project's own threshold at which the
            nudge is escalated to ``warning``.
    """
    nudges: list[Nudge] = []
    for candidate in candidates:
        streak = streaks.get(candidate.name)
        if streak is None:
            continue

        threshold = thresholds.get(candidate.name, default_days)
        severity = severity_for(streak.days, threshold, escalation_gap)
        if severity is None:
            continue

        nudges.append(Nudge(
            project_name=candidate.name,
            project_path=candidate.path,
            next_action=candidate.next_action,
            next_action_source=candidate.next_action_source,
            days=streak.days,
            threshold=threshold,
            severity=severity,
            since=streak.since,
            scans=streak.scans,
            at_window_edge=streak.at_window_edge,
        ))

    nudges.sort(
        key=lambda n: (-SEVERITY_ORDER.get(n.severity, 0), -n.days, n.project_name)
    )
    return nudges
