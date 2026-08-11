"""Sessions that started and landed nothing, counted from what was observed.

The one signal no other surface here can produce.  ``/api/projects/next``
says what to pick up, the idle nudges say a commitment has gone quiet;
both read the *current* state.  This reads the series and asks a question
about behaviour: **how often does a session begin and nothing ship?**

**Where a session record comes from.**  Nothing logs sessions.  What
exists is ``~/.claude/hooks/require-handoff.sh``, a Stop hook that blocks
a session which changed code until ``HANDOFF.md`` carries today's date —
so a code-touching session leaves a dated document behind by force.  The
organiser has recorded that document's age on every scan since
2026-08-06, and ``scanned_at - handoff_age_days`` reconstructs the date it
was written.  A *change* in that reconstructed date between two scans is
therefore an observation that a session happened.  Session 32 was filed
as blocked on writing an append-only ``docs/sessions/log.jsonl``; the log
already existed, sideways, in JSONB.

**Four things this cannot see, stated because the number looks more
authoritative than it is.**

1. *Sessions that changed no code.*  The hook only fires on a code
   change, so an hour of reading that ended in nothing was never
   recorded.  This counts sessions that **intended to ship**.
2. *A second session on the same day.*  Two sessions on one date produce
   one handoff date and count once.  The unit is a session-day.
3. *The baseline.*  The oldest observation is a state, not a transition —
   there is nothing older to compare it against, so the session that
   produced it is not counted.  Same rule ``build_narrative_history``
   applies to ``next_action_changed`` and for the same reason: calling
   the first point a change invents an event whose existence depends on
   ``limit``.
4. *Whether the handoff dated itself.*  An undated handoff falls back to
   file mtime, and a clone or checkout rewrites mtime — which would
   present a ``git checkout`` as a morning's work.  Those transitions are
   counted but reported separately as ``unverified``; snapshots written
   before 2026-08-11 carry no ``handoff_date_source`` at all and are
   unverified by absence.

5. *A project whose only session is its baseline.*  ``ImbaBots`` last
   worked on 2026-08-07 and its first scan in the window falls after
   that commit, so it measures zero sessions — not zero dropped
   sessions, zero *evidence*.  Those projects are reported with
   ``sessions: 0`` and ranked last rather than shown as blameless, which
   is why the sort key separates "measured, nothing dropped" from
   "nothing measured".  Reading a 0 as good conduct is the specific
   mistake this design is arranged to prevent, and it was made anyway on
   the day it was built — see ``SNAG-PROJ-013``, filed from this
   endpoint's output rather than from the repository, and wrong.

Every count is therefore a **lower bound**, and the fields are named so a
consumer cannot round it up by accident.

**What "landed" means.**  A session dated ``D`` landed if a commit dated
``D`` or later had been made by the time the scanner saw the new handoff.
Two answers are reported rather than one, because the difference is the
interesting part:

- ``landed_code`` uses ``ProjectSnapshot.last_commit_at``, which carries
  the newest commit that changed real work — estate-housekeeping sweeps
  are excluded by ``code_commit_ignore``.
- ``landed_any`` uses the true newest commit.  It is stored in
  ``findings['git']['last_commit']`` **only when the two differ**, so its
  absence is not a gap: :func:`~sysadmin.projects.git.get_last_code_commit_date`
  returns the newest commit when it skips nothing, and the fallback to
  the column is exact rather than an approximation.

A session that landed a documentation commit and no code is the gap
between the two, and it is a different failure from one that landed
nothing at all — the first wrote up what it decided, the second did not.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

#: How close to the oldest scan the series may start before its counts are
#: flagged as truncated by retention.  One day, because the organiser's
#: timer is daily.
EDGE_SLACK = timedelta(days=1)


@dataclass(frozen=True)
class Observation:
    """One scan, reduced to the four facts the accounting reads."""

    scanned_at: datetime
    #: Reconstructed from ``scanned_at`` and ``handoff_age_days``.  None
    #: when the project has no handoff, or one whose date could not be
    #: resolved at all.
    handoff_date: date | None
    handoff_date_source: str | None      # heading | mtime | None
    code_commit_date: date | None
    any_commit_date: date | None


@dataclass(frozen=True)
class Session:
    """One observed handoff-date transition, and what it shipped."""

    date: date
    observed_at: datetime
    date_source: str | None
    landed_code: bool
    landed_any: bool

    @property
    def verified(self) -> bool:
        """The handoff dated itself, so this is not an mtime artefact."""
        return self.date_source == "heading"


@dataclass(frozen=True)
class Momentum:
    """One project's start-versus-finish record over the observed series."""

    name: str
    sessions: int
    landed_code: int
    landed_any: int
    #: Sessions that landed something, but nothing that changed real work.
    docs_only: int
    #: Sessions after which no commit of any kind had been made.
    dropped: int
    #: Sessions that shipped no *code*, whether or not they shipped docs.
    dropped_code: int
    unverified: int
    #: First and last scan that could contribute a session — one carrying
    #: a resolvable handoff date.  **Not** the first scan of the project.
    #: This estate holds 198 scans of ``sysadmin_assistant`` back to
    #: 2026-05-13, of which the ones before 2026-08-06 predate the roadmap
    #: findings block and carry ``{}``; reporting those as the observed
    #: period invites dividing five sessions by three months.
    observed_from: date | None
    observed_to: date | None
    #: Scans carrying a handoff date, for the same reason.
    scans: int
    at_window_edge: bool
    last_session: date | None
    last_landing: date | None

    @property
    def drop_rate(self) -> float:
        """Fraction of observed sessions that shipped no code, 0.0–1.0."""
        return self.dropped_code / self.sessions if self.sessions else 0.0


def parse_observation(
    scanned_at: datetime,
    last_commit_at: datetime | None,
    handoff_age_days: str | int | None,
    handoff_date_source: str | None,
    any_commit: str | None,
) -> Observation:
    """Build one :class:`Observation` from a raw snapshot row.

    Every field is parsed defensively.  This runs over whatever ninety
    days of retention happens to hold, including snapshots written before
    the roadmap block existed (2026-08-06, ``findings == {}``) and before
    ``handoff_date_source`` was recorded (2026-08-11).
    """
    age: int | None = None
    if handoff_age_days is not None:
        try:
            age = int(handoff_age_days)
        except (TypeError, ValueError):
            age = None

    handoff = None
    if age is not None and age >= 0:
        handoff = scanned_at.date() - timedelta(days=age)

    code = last_commit_at.date() if last_commit_at else None

    # Absent means "the same as the column" — see the module docstring.
    newest = code
    if any_commit:
        try:
            newest = date.fromisoformat(any_commit)
        except ValueError:
            newest = code

    return Observation(
        scanned_at=scanned_at,
        handoff_date=handoff,
        handoff_date_source=handoff_date_source,
        code_commit_date=code,
        any_commit_date=newest,
    )


def find_sessions(points: Sequence[Observation]) -> list[Session]:
    """The handoff-date transitions in one project's series, oldest first.

    ``points`` is newest-first, matching every other query in
    :mod:`sysadmin.projects.snapshots`.

    A transition is counted when the reconstructed handoff date is newer
    than the one seen at the previous scan.  Strictly newer, not merely
    different: a handoff date moving *backwards* is a checkout, a revert
    or a mistyped heading, and counting it as a session would let history
    manufacture work.  The first observation carries no transition.

    **A landing is matched by date window, not at the transition scan.**
    The obvious rule — ask whether a commit had been made by the time the
    scanner saw the new handoff — was written first and is wrong, because
    the handoff is written before the work is committed.  On 2026-08-10 a
    scan ran at 09:06 and saw this repository's new handoff while
    ``last_commit_at`` still read 2026-08-08; the day's six commits
    arrived afterwards, and the rule reported a productive day as
    dropped.  Scan timing was deciding the answer.

    So a commit dated in ``[session_date, next_session_date)`` is that
    session's output, taken from every commit date the series ever
    observed.  The last session's window is open-ended, which means a
    session opened this morning reads as dropped until something lands —
    correct at the time of asking, and it settles itself on the next
    scan.
    """
    ordered: list[tuple[date, Observation]] = [
        (p.handoff_date, p) for p in reversed(points) if p.handoff_date is not None
    ]

    # Every commit date the series saw.  Only the *newest* commit is
    # recorded per scan, so a day whose commits were entirely superseded
    # before the next scan is invisible — one more reason the counts are
    # lower bounds on landing rather than upper bounds on dropping.
    code_dates = {p.code_commit_date for _, p in ordered if p.code_commit_date}
    any_dates = {p.any_commit_date for _, p in ordered if p.any_commit_date}

    transitions: list[tuple[date, Observation]] = []
    previous: date | None = None
    for current, point in ordered:
        if previous is not None and current > previous:
            transitions.append((current, point))
        previous = current

    def landed(dates: set[date], start: date, end: date | None) -> bool:
        return any(d >= start and (end is None or d < end) for d in dates)

    def following(i: int) -> date | None:
        """The next session's date, closing this one's window."""
        return transitions[i + 1][0] if i + 1 < len(transitions) else None

    return [
        Session(
            date=start,
            observed_at=point.scanned_at,
            date_source=point.handoff_date_source,
            landed_code=landed(code_dates, start, following(i)),
            landed_any=landed(any_dates, start, following(i)),
        )
        for i, (start, point) in enumerate(transitions)
    ]


def measure(
    name: str,
    points: Sequence[Observation],
    *,
    window_start: datetime | None = None,
) -> Momentum:
    """Fold one project's series into its start-versus-finish record.

    Args:
        name: Project name, carried through so a ranked list is readable.
        points: The project's observations, newest scan first.
        window_start: Oldest scan the query could have returned.  A series
            beginning there was truncated by retention, which is a
            different reason for a low count than a young project and is
            reported as ``at_window_edge``.
    """
    # Only scans that resolved a handoff date can carry a transition, so
    # those are the series being reported on.  Counting the rest as
    # "observed" would stretch the period a reader divides by.
    dated = [p for p in points if p.handoff_date is not None]

    if not dated:
        return Momentum(
            name=name, sessions=0, landed_code=0, landed_any=0, docs_only=0,
            dropped=0, dropped_code=0, unverified=0, observed_from=None,
            observed_to=None, scans=0, at_window_edge=False,
            last_session=None, last_landing=None,
        )

    sessions = find_sessions(dated)
    landed_code = sum(1 for s in sessions if s.landed_code)
    landed_any = sum(1 for s in sessions if s.landed_any)
    oldest = dated[-1].scanned_at

    landings = [s.date for s in sessions if s.landed_code]

    return Momentum(
        name=name,
        sessions=len(sessions),
        landed_code=landed_code,
        landed_any=landed_any,
        docs_only=landed_any - landed_code,
        dropped=len(sessions) - landed_any,
        dropped_code=len(sessions) - landed_code,
        unverified=sum(1 for s in sessions if not s.verified),
        observed_from=oldest.date(),
        observed_to=dated[0].scanned_at.date(),
        scans=len(dated),
        at_window_edge=(
            window_start is not None and oldest <= window_start + EDGE_SLACK
        ),
        last_session=sessions[-1].date if sessions else None,
        last_landing=max(landings) if landings else None,
    )


def _sort_key(m: Momentum) -> tuple[int, int, float, str]:
    # Projects with no observed session sort last whatever their counts:
    # a 0/0 record is an absence of evidence, and ranking it beside a
    # measured 0/3 would read as "this one is fine".
    return (0 if m.sessions else 1, -m.dropped_code, -m.drop_rate, m.name)


def rank(records: Sequence[Momentum]) -> list[Momentum]:
    """Worst momentum first: most dropped sessions, then the highest rate."""
    return sorted(records, key=_sort_key)


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def build_reason(ranked: Sequence[Momentum]) -> str:
    """One sentence defending the headline, or explaining its absence.

    Written from the ranking that actually ran, so it cannot drift from
    it — the hedges appear only when the thing being hedged is true.  The
    consumer for a headline is a one-line surface where the list is not
    shown, so this sentence is the only place the choice is accountable.
    """
    measured = [m for m in ranked if m.sessions]
    if not measured:
        if not ranked:
            return "No project scan has been recorded yet."
        return (
            "No session has been observed yet: a handoff date has to change "
            "between two scans before a session can be counted."
        )

    worst = measured[0]
    if worst.dropped_code == 0:
        return (
            f"Nothing to flag — every one of the "
            f"{_plural(sum(m.sessions for m in measured), 'observed session')} "
            f"across {_plural(len(measured), 'project')} landed code."
        )

    at_least = "at least " if worst.at_window_edge else ""
    docs = (
        f", {worst.docs_only} of which committed documentation only"
        if worst.docs_only else ""
    )
    hedge = (
        f" ({_plural(worst.unverified, 'session')} dated by file mtime rather "
        f"than by the document, so that count is soft)"
        if worst.unverified else ""
    )
    return (
        f"{worst.name} has opened {at_least}"
        f"{_plural(worst.dropped_code, 'session')} that shipped no code "
        f"out of {worst.sessions} observed{docs}{hedge}."
    )
