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
