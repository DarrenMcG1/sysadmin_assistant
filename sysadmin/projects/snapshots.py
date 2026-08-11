"""The one query that answers "which projects exist, and how are they?".

Every surface that reports on projects needs the newest snapshot per
project name, and every one of them needs the same freshness test on top
of it.  Before this module there were **nine** open-coded copies of the
join across three packages and one shared helper with the filter applied
by hand at a single call site, so a project deleted from disk kept its
final snapshot forever and went on being reported as live on eight of the
nine.  ``PA-worktrees`` was removed during the ~/projects reorganisation
and still occupied a board row two days later, with a health score and a
next action.

The filter is in the query rather than in the callers on purpose.  A
caller cannot forget a ``WHERE`` clause it does not know exists, and the
defect's shape was *the filter repeated in one place out of nine* — so
repeating it in nine places would have been the same defect with better
odds.

Freshness is expressed relative to the newest scan in the table, not to
wall-clock now.  The organiser scan stamps every project it finds within
the same few seconds, so "materially behind the newest stamp" means "not
found on the last run".  Anchoring to ``now()`` instead would empty every
surface the moment the organiser's timer stopped, which is a monitoring
failure reported as an estate with no projects in it.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Select, desc, func, select

from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.momentum import Observation, parse_observation
from sysadmin.projects.next_action import Streak, streak_days

# Slack against a scan that straddles the boundary.  Far inside the
# 6-hour scan interval, so a project missed by one whole scan still drops.
FRESHNESS_WINDOW = timedelta(hours=1)

# How far back a "how long has this been the next action" question looks.
# Retention keeps ``project_snapshots`` for 90 days, so a longer window
# would silently be truncated by the purge instead of by a stated rule.
ACTION_HISTORY_WINDOW = timedelta(days=90)


def latest_snapshot_query(*, fresh: bool = True) -> Select[tuple[ProjectSnapshot]]:
    """Select the newest snapshot per project.

    Args:
        fresh: Keep only projects the most recent scan saw.  Defaults to
            ``True`` because every reporting surface wants it.  Pass
            ``False`` only to ask a question *about* the history itself
            — a review's week-ago baseline, say — where excluding the
            projects that have since disappeared would hide the change
            being measured.

    Returns:
        A ``Select`` of whole ``ProjectSnapshot`` rows, unordered.
        Callers add their own ``order_by``; there is no natural order
        shared by a board, a report and a briefing table.
    """
    newest_per_project = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )

    query = select(ProjectSnapshot).join(
        newest_per_project,
        (ProjectSnapshot.project_name == newest_per_project.c.project_name)
        & (ProjectSnapshot.scanned_at == newest_per_project.c.max_scanned),
    )

    if not fresh:
        return query

    # Evaluated by the database in the same statement rather than by a
    # second round trip: two queries could straddle a scan writing rows
    # between them and compute the cutoff from a scan the first query
    # never saw.
    newest_scan = select(func.max(ProjectSnapshot.scanned_at)).scalar_subquery()
    return query.where(ProjectSnapshot.scanned_at >= newest_scan - FRESHNESS_WINDOW)


def action_history_query(
    names: Sequence[str],
    *,
    window: timedelta = ACTION_HISTORY_WINDOW,
) -> Select[tuple[str, datetime, str | None]]:
    """The next-action series per project, newest scan first.

    Three columns, not whole rows.  ``findings`` is a JSONB blob of a few
    kilobytes and this reads one string out of it across every scan in the
    window — selecting ``ProjectSnapshot`` entities would drag roughly two
    orders of magnitude more data over the wire to compute a run length.

    The window is measured from the newest scan in the table for the same
    reason the freshness cutoff is: anchoring to ``now()`` would shrink
    the history the moment the organiser's timer stopped, so a stuck
    action would appear to un-stick itself while nothing was being
    scanned at all.

    Args:
        names: Projects to fetch.  Empty returns a query selecting no
            rows rather than every project — the caller has already
            decided which projects are eligible, and "no candidates"
            must not silently mean "the whole estate".
        window: How far back to look.  Defaults to the retention period,
            beyond which there is nothing to find.

    Returns:
        A ``Select`` of ``(project_name, scanned_at, next_action)``
        ordered by project then newest-first, matching the order
        ``build_narrative_history`` and ``streak_days`` both expect.
    """
    # ``.astext`` yields NULL for a missing path, so snapshots predating
    # the roadmap block (2026-08-06) carry ``{}`` and read as "no action"
    # rather than raising — the same defensiveness the history builder
    # applies in Python.
    findings: Any = ProjectSnapshot.findings
    action = findings["roadmap"]["next_action"].astext.label("next_action")

    newest_scan = select(func.max(ProjectSnapshot.scanned_at)).scalar_subquery()

    return (
        select(ProjectSnapshot.project_name, ProjectSnapshot.scanned_at, action)
        .where(ProjectSnapshot.project_name.in_(names))
        .where(ProjectSnapshot.scanned_at >= newest_scan - window)
        .order_by(ProjectSnapshot.project_name, desc(ProjectSnapshot.scanned_at))
    )


def momentum_history_query(
    names: Sequence[str],
    *,
    window: timedelta = ACTION_HISTORY_WINDOW,
) -> Select[tuple[str, datetime, datetime | None, str | None, str | None, str | None]]:
    """The handoff-and-commit series per project, newest scan first.

    Six columns rather than whole rows, for the reason
    :func:`action_history_query` records: ``findings`` is a JSONB blob of
    a few kilobytes and this reads three short strings out of it across
    every scan in the window.

    Two of those strings are read from paths that did not always exist.
    ``handoff_date_source`` has been written since 2026-08-11 and
    ``roadmap`` itself only since 2026-08-06; ``.astext`` yields NULL for
    a missing path rather than raising, and
    :func:`~sysadmin.projects.momentum.parse_observation` treats NULL as
    "not known" rather than as a value.

    ``git → last_commit`` is present **only** on scans where a
    housekeeping commit was skipped — 77 rows of 3,635 on this estate.
    That is not a gap: absence means the newest commit and the newest
    *code* commit are the same, so the parser falls back to
    ``last_commit_at`` and the answer is exact.

    Args:
        names: Projects to fetch.  Empty selects no rows, so "no
            candidates" cannot silently mean "the whole estate".
        window: How far back to look, anchored to the newest scan for the
            same reason the freshness cutoff is.
    """
    findings: Any = ProjectSnapshot.findings
    age = findings["roadmap"]["handoff_age_days"].astext.label("handoff_age_days")
    source = findings["roadmap"]["handoff_date_source"].astext.label("date_source")
    any_commit = findings["git"]["last_commit"].astext.label("any_commit")

    newest_scan = select(func.max(ProjectSnapshot.scanned_at)).scalar_subquery()

    return (
        select(
            ProjectSnapshot.project_name,
            ProjectSnapshot.scanned_at,
            ProjectSnapshot.last_commit_at,
            age,
            source,
            any_commit,
        )
        .where(ProjectSnapshot.project_name.in_(names))
        .where(ProjectSnapshot.scanned_at >= newest_scan - window)
        .order_by(ProjectSnapshot.project_name, desc(ProjectSnapshot.scanned_at))
    )


async def load_momentum_series(
    session: Any,
    names: Sequence[str],
    *,
    window: timedelta = ACTION_HISTORY_WINDOW,
) -> tuple[dict[str, list[Observation]], datetime | None]:
    """Run :func:`momentum_history_query` and parse it into observations.

    Returns ``(series, window_start)``.  ``window_start`` is the oldest
    scan the query could have returned, and is handed to
    :func:`~sysadmin.projects.momentum.measure` so a series that begins
    at the boundary can say its counts were truncated by retention rather
    than by the project being young.  It is computed from the newest scan
    the query actually returned — the same anchor the ``WHERE`` clause
    used, so the two cannot disagree even if a scan lands between them.

    A project absent from the result is absent from the mapping rather
    than defaulted here.  Whether "never scanned" means "no dropped
    sessions" is the caller's decision, and it is not the same answer as
    "measured, and nothing was dropped".
    """
    if not names:
        return {}, None

    result = await session.execute(momentum_history_query(list(names), window=window))
    series: dict[str, list[Observation]] = {}
    newest: datetime | None = None

    for name, scanned_at, last_commit_at, age, source, any_commit in result.all():
        if newest is None or scanned_at > newest:
            newest = scanned_at
        series.setdefault(name, []).append(parse_observation(
            scanned_at=scanned_at,
            last_commit_at=last_commit_at,
            handoff_age_days=age,
            handoff_date_source=source,
            any_commit=any_commit,
        ))

    return series, (newest - window) if newest else None


async def load_action_streaks(session: Any, names: Sequence[str]) -> dict[str, Streak]:
    """Run :func:`action_history_query` and fold it into one streak per name.

    The fold is three lines and was written out twice the day the idle
    nudges arrived — once in the endpoint, once in the agent — which is
    how the row order (newest-first) and the window anchor become
    assumptions two callers hold separately.  Kept here beside the query
    whose output shape it depends on.

    Only the names handed in are read: ranking or nudging a handful of
    projects must not pull ninety days of scans for the thirty-odd
    repositories that were ruled out before this was called.  An empty
    ``names`` short-circuits without a round trip.

    A project absent from the result — no snapshot in the window at all —
    is simply absent from the mapping rather than defaulted to a
    zero-day streak here.  Whether "unknown" means "not stuck" is the
    caller's decision, and the two callers answer differently: the
    endpoint ranks it last, the nudge declines to raise.
    """
    if not names:
        return {}

    result = await session.execute(action_history_query(list(names)))
    series: dict[str, list[tuple[datetime, str | None]]] = {}
    for name, scanned_at, past_action in result.all():
        series.setdefault(name, []).append((scanned_at, past_action))

    return {name: streak_days(points) for name, points in series.items()}
