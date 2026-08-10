"""One project, one action, and the sentence that defends the choice.

``GET /api/projects/board`` re-projects the estate and lets the caller
pick an order.  This module makes the choice *for* the caller, which is a
different obligation: alfred-glance shows one thing on a phone, so the
ranking is no longer inspectable and has to explain itself in prose.
That is why ``reason`` is a required field rather than a courtesy.

**The ranking is stuckness, decided 2026-08-10.** The candidates
considered were longest-idle (rejected — it ranks by guilt, and the
stated goal is momentum), nearest-to-finishing (rejected — it reads
``done_tasks``/``open_tasks``, which are ``None`` for three of the five
active projects on this estate, so it would be blind to most of the
population while looking authoritative) and smallest-next-step (rejected
as unmeasurable: nothing records the size of a step, and every proxy for
it — string length, task count — is invented rather than observed).

**Stuckness is measured in days, not in scans.** The scan series is
irregular by construction: 6-hourly until Session 35, daily from the
04:32 timer since, plus every manual ``POST /api/projects/scan`` — the
live table holds two scans 17 minutes apart on 2026-08-08 and two more
on 2026-08-10.  A run length in scans would therefore reward whichever
project happened to be scanned most often, which measures the scanner's
cadence and calls it the owner's behaviour.  Run length in *observations*
is still reported, as evidence for the number rather than as the ranking.

Elapsed days come from the snapshot series, not from the handoff's own
``handoff_age_days``.  The document's self-reported date says what it
claims about itself; the series says what was observed, and it is the
observation that is being asserted.  ``handoff_age_days`` keeps its
existing job of deciding ``stalled``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

# A next action is only work if a human queued it.  ``git`` means neither
# a handoff nor a task list existed and the last commit subject is
# standing in — a record of the past, correct on the board where the
# source is rendered beside it, and not an instruction to act on here.
ELIGIBLE_SOURCES = ("handoff", "tasks")


@dataclass(frozen=True)
class Candidate:
    """An active project with a human-stated next action."""

    name: str
    path: str
    next_action: str
    next_action_source: str
    health_score: int
    days_since_commit: int | None
    open_tasks: int | None
    open_snags: int
    scanned_at: datetime | None


@dataclass(frozen=True)
class Streak:
    """How long one next action has stood, and how well that is known."""

    days: int
    since: datetime | None
    scans: int
    #: The run reaches the oldest scan held, so the true age is a lower
    #: bound.  Retention purges at 90 days and a project may simply be
    #: newer than its first scan suggests; either way ``days`` is "at
    #: least", and a consumer that renders it as exact is overstating.
    at_window_edge: bool


def streak_days(points: Sequence[tuple[datetime, str | None]]) -> Streak:
    """Measure the current next action's run.  ``points`` is newest-first.

    A run, not a total: an action that appears, is replaced and returns
    (A → B → A) counts only its current spell.  The alternative — total
    occurrences — would report an action resumed after a month as though
    it had never moved, which is the opposite of what the number is for.
    """
    if not points:
        return Streak(days=0, since=None, scans=0, at_window_edge=True)

    newest_at, current = points[0]
    last = 0
    while last + 1 < len(points) and points[last + 1][1] == current:
        last += 1

    since = points[last][0]
    return Streak(
        days=max(0, (newest_at - since).days),
        since=since,
        scans=last + 1,
        at_window_edge=last == len(points) - 1,
    )


def _sort_key(item: tuple[Candidate, Streak]) -> tuple[int, int, str]:
    candidate, streak = item
    # A project with no commit at all sorts last on the tie-break rather
    # than first: "never committed" is not "committed a long time ago",
    # and the warm-context tie-break has nothing to say about it.
    days_idle = candidate.days_since_commit
    return (-streak.days, days_idle if days_idle is not None else 10**6, candidate.name)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def build_reason(
    winner: tuple[Candidate, Streak],
    ranked: Sequence[tuple[Candidate, Streak]],
) -> str:
    """One sentence saying why this project and not one of the others.

    Written from the ranking that actually ran, so it cannot drift from
    it: the tie-break is only mentioned when a tie was really broken, and
    the "at least" hedge only when the run reaches the window edge.
    """
    candidate, streak = winner
    tied = sum(1 for _, s in ranked if s.days == streak.days)

    if len(ranked) == 1:
        if streak.days > 0:
            return (
                f"It is the only active project with a stated next action, "
                f"and that action has stood for {_plural(streak.days, 'day')}."
            )
        return "It is the only active project with a stated next action."

    if streak.days == 0:
        return (
            "Every active project's next action moved on at the last scan, "
            "so this is the one you committed to most recently."
        )

    at_least = "at least " if streak.at_window_edge else ""
    if tied > 1:
        return (
            f"Its next action has stood for {at_least}"
            f"{_plural(streak.days, 'day')}, level with "
            f"{_plural(tied - 1, 'other project')}, and of those it is the one "
            f"you committed to most recently."
        )
    return (
        f"Its next action has stood unchanged for {at_least}"
        f"{_plural(streak.days, 'day')} — longer than any other active project."
    )


def build_empty_reason(skipped: dict[str, int]) -> str:
    """Why there is no project to return, in the caller's terms.

    ``project: null`` with a bare "nothing found" is the empty-versus-down
    confusion this repo keeps finding: a consumer cannot tell an estate
    that is up to date from one that has never been scanned, and renders
    both as silence.
    """
    if not skipped:
        return "No project scan has been recorded yet."

    says_none = skipped.get("says_no_action", 0)
    missing = skipped.get("no_action", 0) + skipped.get("source_git", 0)
    excluded = skipped.get("excluded", 0)

    parts = []
    if says_none:
        parts.append(f"{says_none} record that there is nothing queued")
    if missing:
        parts.append(f"{missing} have no stated next action")
    if excluded:
        parts.append(f"{excluded} were excluded by the request")

    if not parts:
        return "No active project was found in the most recent scan."
    return "Nothing to pick up: " + ", ".join(parts) + "."


def choose(
    candidates: Sequence[Candidate],
    streaks: dict[str, Streak],
    skipped: dict[str, int],
) -> tuple[Candidate | None, Streak | None, str]:
    """Rank the candidates and explain the winner.

    Returns ``(None, None, reason)`` rather than raising or 404-ing when
    nothing qualifies — see :func:`build_empty_reason`.
    """
    if not candidates:
        return None, None, build_empty_reason(skipped)

    ranked = sorted(
        ((c, streaks.get(c.name, Streak(0, None, 0, True))) for c in candidates),
        key=_sort_key,
    )
    winner = ranked[0]
    return winner[0], winner[1], build_reason(winner, ranked)
