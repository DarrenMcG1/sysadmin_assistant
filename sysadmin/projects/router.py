"""Project Organiser API endpoints."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.auth import require_auth
from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    BranchCleanupResponse,
    ManagedProjectsResponse,
    NextProjectResponse,
    PortfolioActionsResponse,
    ProjectBoardResponse,
    ProjectOverviewResponse,
    ProjectRecommendationsResponse,
    ProjectReviewResponse,
    StaleProjectsResponse,
)
from sysadmin.core.database import get_db_session
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.monitor.services import get_services
from sysadmin.projects import branch_actions, next_action, recommendations
from sysadmin.projects import review as project_review
from sysadmin.projects.models.project_review import ProjectReview
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.snapshots import (
    latest_snapshot_query,
    load_action_streaks,
)
from sysadmin.registry import load_registry

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/overview", response_model=ProjectOverviewResponse)
async def get_projects_overview(session: AsyncSession = Depends(get_db_session)):
    """Get all projects with their latest health scores."""
    query = latest_snapshot_query().order_by(desc(ProjectSnapshot.health_score))

    result = await session.execute(query)
    rows = result.scalars().all()

    bands = get_config().agents.project_organiser.grade_bands

    def _grade(score: int) -> str:
        if score >= bands.healthy_min:
            return "healthy"
        if score >= bands.needs_attention_min:
            return "needs_attention"
        if score >= bands.neglected_min:
            return "neglected"
        return "abandoned"

    return {
        "projects": [
            {
                "name": r.project_name,
                "health_score": r.health_score,
                "grade": _grade(r.health_score),
                "last_commit_at": r.last_commit_at.isoformat() if r.last_commit_at else None,
                "branch_count": r.branch_count,
                "stale_branch_count": r.stale_branch_count,
                "todo_count": r.todo_count,
                "has_readme": r.has_readme,
                "has_claude_md": r.has_claude_md,
                "total_size_mb": r.total_size_mb,
                "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/stale", response_model=StaleProjectsResponse)
async def get_stale_projects(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    """Projects with no commit in the last ``days`` days.

    Staleness is **idleness**, not ill health.  This handler used to
    ignore ``days`` entirely and filter on ``health_score <
    needs_attention_min``, which made it a duplicate of ``/overview``
    under a name that promised something else: a well-kept repository
    untouched for a year scored 90 and never appeared, while an actively
    developed one with a dirty tree and no README appeared every day.

    A project with no commits at all — no git history, or a repository
    the scanner could not read — is reported with ``days_idle: null``
    rather than omitted.  "Never committed" is the strongest form of the
    thing being asked about, and dropping it would answer a narrower
    question than the caller asked.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days)
    query = (
        latest_snapshot_query()
        .where(
            (ProjectSnapshot.last_commit_at < cutoff)
            | (ProjectSnapshot.last_commit_at.is_(None))
        )
        # Nulls first: never-committed is more stale than any date.
        .order_by(ProjectSnapshot.last_commit_at.asc().nullsfirst())
    )

    result = await session.execute(query)
    rows = result.scalars().all()

    now = datetime.now(UTC)

    def _days_idle(row: ProjectSnapshot) -> int | None:
        if row.last_commit_at is None:
            return None
        last = row.last_commit_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        return (now - last).days

    return {
        "stale_projects": [
            {
                "name": r.project_name,
                "health_score": r.health_score,
                "last_commit_at": r.last_commit_at.isoformat() if r.last_commit_at else None,
                "days_idle": _days_idle(r),
                "status": (r.findings or {}).get("status", "active"),
                "findings": r.findings,
            }
            for r in rows
        ],
        "count": len(rows),
        "days": days,
    }


@router.get("/report")
async def get_projects_report(session: AsyncSession = Depends(get_db_session)):
    """Get a full markdown report of all projects."""
    query = latest_snapshot_query().order_by(desc(ProjectSnapshot.health_score))

    result = await session.execute(query)
    rows = result.scalars().all()

    bands = get_config().agents.project_organiser.grade_bands
    lines = ["# Project Health Report\n"]
    for r in rows:
        score_emoji = (
            "🟢" if r.health_score >= bands.healthy_min
            else "🟡" if r.health_score >= bands.needs_attention_min
            else "🔴"
        )
        lines.append(f"## {score_emoji} {r.project_name} — {r.health_score}/100\n")
        lines.append(f"- **Path:** `{r.project_path}`")
        if r.last_commit_at:
            lines.append(f"- **Last commit:** {r.last_commit_at.strftime('%Y-%m-%d')}")
        lines.append(f"- **Branches:** {r.branch_count} ({r.stale_branch_count} stale)")
        lines.append(f"- **TODOs:** {r.todo_count or 0}  |  **FIXMEs:** {r.fixme_count or 0}")
        readme_mark = "✓" if r.has_readme else "✗"
        claude_mark = "✓" if r.has_claude_md else "✗"
        lines.append(f"- **README:** {readme_mark}  |  **CLAUDE.md:** {claude_mark}")
        lines.append(f"- **Size:** {r.total_size_mb} MB")
        if r.findings:
            lines.append(f"- **Findings:** {r.findings}")
        lines.append("")

    return {"report": "\n".join(lines)}


@router.get("/managed", response_model=ManagedProjectsResponse)
async def get_managed_projects(session: AsyncSession = Depends(get_db_session)):
    """List projects from projects.yaml with live service health status."""
    config = get_config()
    registry = load_registry(config.agents.project_organiser.projects_root)

    # Fetch latest health check per service
    latest_health_subq = (
        select(
            ServiceHealth.service_name,
            func.max(ServiceHealth.checked_at).label("max_checked"),
        )
        .group_by(ServiceHealth.service_name)
        .subquery()
    )
    health_query = (
        select(ServiceHealth)
        .join(
            latest_health_subq,
            (ServiceHealth.service_name == latest_health_subq.c.service_name)
            & (ServiceHealth.checked_at == latest_health_subq.c.max_checked),
        )
    )
    result = await session.execute(health_query)
    health_map = {r.service_name: r for r in result.scalars().all()}

    # Fetch latest project snapshot per project
    snap_result = await session.execute(latest_snapshot_query())
    snap_map = {r.project_name: r for r in snap_result.scalars().all()}

    # Services come from services.yaml, resolved by project id. projects.yaml
    # used to generate them from its own backend/frontend blocks, which is
    # why it could only ever report two per project — Alfred has four.
    declared = get_services()

    projects_out = []
    for mp in registry.declared:
        svc_entries = declared.for_project(mp.id)
        services = []
        all_healthy = True
        for svc in svc_entries:
            h = health_map.get(svc.name)
            entry: dict = {"name": svc.name, "status": h.status if h else "unknown"}
            if h and h.response_time_ms is not None:
                entry["response_time_ms"] = h.response_time_ms
            services.append(entry)
            if not h or h.status != "ok":
                all_healthy = False

        snap = snap_map.get(mp.name)
        project_health = None
        if snap:
            project_health = {
                "health_score": snap.health_score,
                "scanned_at": snap.scanned_at.isoformat() if snap.scanned_at else None,
            }

        projects_out.append({
            "name": mp.name,
            "path": str(mp.path),
            "services": services,
            "project_health": project_health,
            "all_services_healthy": all_healthy if services else None,
        })

    return {"projects": projects_out, "count": len(projects_out)}


# NOTE: /review and /review/generate must stay declared before ``/{name}``
# or they would be captured as a project called "review".
@router.get("/review", response_model=ProjectReviewResponse)
async def get_project_review(session: AsyncSession = Depends(get_db_session)):
    """The latest stored weekly portfolio review."""
    result = await session.execute(
        select(ProjectReview).order_by(desc(ProjectReview.generated_at)).limit(1)
    )
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="No review generated yet")

    return {
        "generated_at": review.generated_at.isoformat() if review.generated_at else None,
        "period_days": review.period_days,
        "narrative": review.narrative,
        "llm_used": review.llm_used,
        "model_used": review.model_used,
        "stats": review.stats,
    }


@router.post(
    "/review/generate",
    response_model=ProjectReviewResponse,
    dependencies=[Depends(require_auth)],
)
async def generate_project_review(session: AsyncSession = Depends(get_db_session)):
    """Generate a review on demand (falls back to a digest if the LLM is down)."""
    review = await project_review.generate_review(session)
    if review is None:
        raise HTTPException(status_code=409, detail="No project snapshots to review")

    return {
        "generated_at": review.generated_at.isoformat() if review.generated_at else None,
        "period_days": review.period_days,
        "narrative": review.narrative,
        "llm_used": review.llm_used,
        "model_used": review.model_used,
        "stats": review.stats,
    }


# NOTE: must stay declared before ``/{name}`` or it would be captured as
# a project called "actions".
@router.get("/actions", response_model=PortfolioActionsResponse)
async def get_portfolio_actions(
    limit: int = Query(default=10, le=50),
    session: AsyncSession = Depends(get_db_session),
):
    """Top housekeeping wins across every project, ranked by impact."""
    result = await session.execute(latest_snapshot_query())
    rows = result.scalars().all()

    agent_config = get_config().agents.project_organiser
    actions = []
    projects_with_actions = 0
    for row in rows:
        recs = recommendations.recommendations_for(row, agent_config)
        if recs:
            projects_with_actions += 1
        for rec in recs:
            actions.append({
                **rec.model_dump(),
                "project": row.project_name,
                "health_score": row.health_score,
            })

    actions.sort(key=lambda a: (a["severity"] != "risk", -a["points"], a["project"]))

    shown = actions[:limit]
    dropped: dict[str, int] = {}
    for action in actions[limit:]:
        kind = action.get("kind") or "other"
        dropped[kind] = dropped.get(kind, 0) + 1

    return {
        "actions": shown,
        "count": len(shown),
        "total_available": len(actions),
        "projects_with_actions": projects_with_actions,
        "dropped_by_kind": dict(sorted(dropped.items())),
    }


# NOTE: must stay declared before ``/{name}`` — same capture hazard as
# /actions and /review above.
@router.get("/board", response_model=ProjectBoardResponse)
async def get_project_board(
    include_inactive: bool = Query(default=False),
    sort: str = Query(default="activity", pattern="^(activity|neglect)$"),
    session: AsyncSession = Depends(get_db_session),
):
    """The whole estate in one call — health joined to "what do I do next".

    Built for Alfred's projects page, which would otherwise need four
    calls and a client-side join.  Everything here is a re-projection of
    the latest snapshot; nothing is computed that the scanner has not
    already stored.

    Two orderings, because "what am I working on" and "what have I
    abandoned" are different questions and one list cannot lead with both:

    - ``activity`` (default) — most recently touched first.  This is the
      working view.  The first draft defaulted to the other order and
      buried an actively-developed project at row 12 of 18, which is
      exactly backwards for a page you open to see current work.
    - ``neglect`` — stalled first, then longest-idle.  The weekly
      triage view: what needs a resume-or-park decision.

    Dormant and archived projects are excluded by default.  They have no
    next action by definition — that is what declaring them dormant
    *meant* — and listing them turns a short actionable board into an
    inventory.
    """
    result = await session.execute(latest_snapshot_query())
    rows = result.scalars().all()

    # The freshness test that used to live here is now inside
    # ``latest_snapshot_query`` — the board was the only one of nine
    # surfaces applying it, which is why a deleted project was dropped
    # here and reported everywhere else.  See sysadmin/projects/snapshots.py.

    config = get_config()
    bands = config.agents.project_organiser.grade_bands
    agent_config = config.agents.project_organiser
    now = datetime.now(UTC)

    def _grade(score: int) -> str:
        if score >= bands.healthy_min:
            return "healthy"
        if score >= bands.needs_attention_min:
            return "needs_attention"
        if score >= bands.neglected_min:
            return "neglected"
        return "abandoned"

    entries = []
    for row in rows:
        findings = row.findings or {}
        status = findings.get("status", "active")
        if not include_inactive and status != "active":
            continue

        roadmap = findings.get("roadmap") or {}
        next_action = roadmap.get("next_action")
        source = roadmap.get("next_action_source")

        # Last resort: neither a handoff nor a task list exists, so stand
        # the last commit subject in and label it honestly. A project with
        # no roadmap documents at all still deserves a row — it is exactly
        # the one most likely to have been forgotten.
        if not next_action and findings.get("last_commit_subject"):
            next_action = str(findings["last_commit_subject"])
            source = "git"

        days_since = None
        if row.last_commit_at:
            last = row.last_commit_at
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
            days_since = (now - last).days

        age = roadmap.get("handoff_age_days")
        stalled = isinstance(age, int) and age > recommendations.STALLED_HANDOFF_DAYS

        recs = recommendations.recommendations_for(row, agent_config)

        entries.append({
            "name": row.project_name,
            "path": row.project_path,
            "status": status,
            "health_score": row.health_score,
            "grade": _grade(row.health_score),
            "last_commit_at": (
                row.last_commit_at.isoformat() if row.last_commit_at else None
            ),
            "days_since_commit": days_since,
            "next_action": next_action,
            "next_action_source": source,
            "handoff_age_days": age,
            "stalled": stalled,
            "open_tasks": roadmap.get("open_tasks"),
            "open_snags": roadmap.get("open_snags", 0),
            "top_action": recs[0].title if recs else None,
            "scanned_at": row.scanned_at.isoformat() if row.scanned_at else None,
        })

    # A project that has never been committed sorts last in both modes:
    # unknown is not the same as urgent, and it is not recent work either.
    def _days(entry: dict) -> int:
        days = entry["days_since_commit"]
        return days if days is not None else 10**6

    if sort == "neglect":
        entries.sort(
            key=lambda e: (
                e["status"] != "active",
                not e["stalled"],
                -_days(e) if e["days_since_commit"] is not None else 1,
                e["name"],
            )
        )
    else:
        entries.sort(
            key=lambda e: (e["status"] != "active", _days(e), e["name"])
        )

    return {
        "projects": entries,
        "count": len(entries),
        "stalled_count": sum(1 for e in entries if e["stalled"]),
        "generated_at": now.isoformat(),
    }


# NOTE: must stay declared before ``/{name}`` — same capture hazard as
# /actions, /review and /board above.
@router.get("/next", response_model=NextProjectResponse)
async def get_next_project(
    exclude: list[str] = Query(default=[]),
    session: AsyncSession = Depends(get_db_session),
):
    """The one project to pick up next, and why it is that one.

    The board's smaller sibling, and a different object rather than
    ``/board?limit=1``: it ranks by how long a next action has stood
    unchanged, which no board ordering exposes.  Built for
    alfred-glance, whose premise is glance-then-act — a six-row list on
    a phone reintroduces the choosing problem the feature exists to
    remove.

    ``?exclude=`` is repeatable and takes project names, so a suggestion
    can be deferred without re-rolling the same answer.  The exclusions
    are counted in ``skipped`` and echoed in ``excluded``: a caller that
    has excluded its way to an empty response should be able to see that
    is what happened, rather than read it as an estate with no work in
    it.

    The ranking, the reason text and the eligibility rules live in
    :mod:`sysadmin.projects.next_action`, which records why stuckness
    was chosen over idleness and why the unit is days rather than scans.
    """
    result = await session.execute(latest_snapshot_query())
    rows = result.scalars().all()

    now = datetime.now(UTC)
    excluded = sorted({name.strip() for name in exclude if name.strip()})

    # Eligibility lives in next_action so the idle nudges of Session 31
    # cannot drift from it — one definition of "a commitment", read by
    # the endpoint that offers work and by the agent that reminds you of
    # it.
    candidates, skipped = next_action.eligible_candidates(
        rows, now=now, excluded=excluded
    )

    # Only the candidates' history is fetched.  Reading every project's
    # series to rank five of them would pull ninety days of scans for the
    # thirty-odd repositories that were already ruled out.
    streaks = await load_action_streaks(session, [c.name for c in candidates])

    winner, streak, reason = next_action.choose(candidates, streaks, skipped)

    project = None
    if winner is not None and streak is not None:
        project = {
            "name": winner.name,
            "path": winner.path,
            "next_action": winner.next_action,
            "next_action_source": winner.next_action_source,
            "days_unchanged": streak.days,
            "unchanged_since": streak.since.isoformat() if streak.since else None,
            "unchanged_scans": streak.scans,
            "at_window_edge": streak.at_window_edge,
            "days_since_commit": winner.days_since_commit,
            "health_score": winner.health_score,
            "open_tasks": winner.open_tasks,
            "open_snags": winner.open_snags,
            "scanned_at": (
                winner.scanned_at.isoformat() if winner.scanned_at else None
            ),
        }

    return {
        "project": project,
        "reason": reason,
        "considered": len(candidates),
        "skipped": dict(sorted(skipped.items())),
        "excluded": excluded,
        "generated_at": now.isoformat(),
    }


def build_narrative_history(rows: Sequence[Any]) -> list[dict[str, Any]]:
    """Score *and* next action per snapshot, newest-first like ``rows``.

    The organiser has written the whole roadmap findings block into
    ``project_snapshots`` since Session 28 (2026-08-06) and nothing read it
    back — ninety days of next actions in JSONB with no endpoint over them.
    Session 32's start-versus-finish accounting was recorded as blocked on
    a document format while the data it needed was already being collected.

    Each point is compared against its *older* neighbour (index ``i + 1``),
    so ``next_action_changed`` is ``True`` on the scan where the action
    moved on, and a run of ``False`` measures how long one action stayed
    open. The oldest point gets ``None``, not ``False``: there is nothing
    older in the window to compare it to, and calling that "unchanged"
    would invent a streak whose length varies with ``limit``.

    Every ``findings`` access is defensive. Snapshots predate the roadmap
    block, so rows from before 2026-08-06 carry ``{}`` and must yield
    ``None`` rather than raise — this runs over whatever 90 days of
    retention happens to hold.
    """
    def _action(row: Any) -> tuple[str | None, str | None]:
        roadmap = (getattr(row, "findings", None) or {}).get("roadmap") or {}
        return roadmap.get("next_action"), roadmap.get("next_action_source")

    actions = [_action(r) for r in rows]
    out: list[dict[str, Any]] = []
    for i, r in enumerate(rows):
        action, source = actions[i]
        changed: bool | None = None
        if i + 1 < len(actions):
            changed = action != actions[i + 1][0]
        out.append({
            "health_score": r.health_score,
            "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
            "next_action": action,
            "next_action_source": source,
            "next_action_changed": changed,
        })
    return out


@router.get("/{name}")
async def get_project_detail(
    name: str,
    limit: int = Query(default=5, le=50),
    session: AsyncSession = Depends(get_db_session),
):
    """Get detail for a specific project (recent snapshots)."""
    query = (
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_name == name)
        .order_by(desc(ProjectSnapshot.scanned_at))
        .limit(limit)
    )
    result = await session.execute(query)
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    latest = rows[0]
    history = build_narrative_history(rows)
    return {
        "name": name,
        "current": {
            "health_score": latest.health_score,
            "last_commit_at": latest.last_commit_at.isoformat() if latest.last_commit_at else None,
            "branch_count": latest.branch_count,
            "stale_branch_count": latest.stale_branch_count,
            "todo_count": latest.todo_count,
            "fixme_count": latest.fixme_count,
            "has_readme": latest.has_readme,
            "has_claude_md": latest.has_claude_md,
            "total_size_mb": latest.total_size_mb,
            "findings": latest.findings,
            "scanned_at": latest.scanned_at.isoformat() if latest.scanned_at else None,
        },
        "history": history,
    }


@router.get("/{name}/recommendations", response_model=ProjectRecommendationsResponse)
async def get_project_recommendations(
    name: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Ranked housekeeping advice from the project's latest snapshot."""
    query = (
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_name == name)
        .order_by(desc(ProjectSnapshot.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    snapshot = result.scalars().first()

    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    agent_config = get_config().agents.project_organiser
    recs = recommendations.recommendations_for(snapshot, agent_config)
    findings = snapshot.findings or {}
    return {
        "project": name,
        "status": findings.get("status", "active"),
        "health_score": snapshot.health_score,
        "potential_score": recommendations.potential_score(snapshot, recs),
        "recommendations": [r.model_dump() for r in recs],
        "count": len(recs),
        "scanned_at": snapshot.scanned_at.isoformat() if snapshot.scanned_at else None,
    }


@router.get("/{name}/todos")
async def get_project_todos(
    name: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get TODO/FIXME details for a project from the latest scan."""
    query = (
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_name == name)
        .order_by(desc(ProjectSnapshot.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    return {
        "project": name,
        "todo_count": row.todo_count,
        "fixme_count": row.fixme_count,
        "todos": row.findings.get("todos", {}),
    }


@router.get("/{name}/branches")
async def get_project_branches(
    name: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get branch details for a project from the latest scan."""
    query = (
        select(ProjectSnapshot)
        .where(ProjectSnapshot.project_name == name)
        .order_by(desc(ProjectSnapshot.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    row = result.scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail=f"Project '{name}' not found")

    return {
        "project": name,
        "branch_count": row.branch_count,
        "stale_branch_count": row.stale_branch_count,
        "stale_branches": row.findings.get("stale_branches", []),
    }


@router.post("/scan", dependencies=[Depends(require_auth)])
async def trigger_scan(request: Request):
    """Trigger an immediate project scan."""
    agent = request.app.state.project_organiser_agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Project organiser agent not available")

    # Run in background to avoid request timeout
    asyncio.create_task(agent.run(run_type="manual"))
    return {"status": "scan_triggered"}


# ---------------------------------------------------------------------------
# Branch hygiene — the one mutating, destructive project action.
#
# Same contract as Session 18's file actions:
#   * POST only, behind ``require_auth``
#   * **dry run unless the body sets ``confirm: true``** — the default
#     response is a manifest of exactly which branches would go, and the
#     repository is not touched
#   * the same manifest shape comes back either way
#     (``BranchCleanupResponse``), one row per local branch with its last
#     commit, merge state and the reason it is (in)eligible
#   * merged-into-the-default-branch only; unmerged deletion needs
#     ``include_unmerged`` on the request **and**
#     ``branch_actions.allow_unmerged_delete`` in config
# The rules themselves live in ``sysadmin.projects.branch_actions``.
# ---------------------------------------------------------------------------


class BranchPruneRequest(BaseModel):
    """Nothing is deleted without ``confirm``."""

    confirm: bool = Field(
        default=False,
        description="Set true to actually delete. Default is a dry run.",
    )
    stale_days: int | None = Field(
        default=None,
        description=(
            "Only consider branches untouched for this many days. Defaults "
            "to agents.project_organiser.stale_branch_days; may not go below "
            "branch_actions.min_stale_days."
        ),
    )
    include_unmerged: bool = Field(
        default=False,
        description=(
            "Permit deleting branches not merged into the default branch. "
            "Also requires branch_actions.allow_unmerged_delete in config."
        ),
    )
    max_deletions: int | None = Field(
        default=None,
        description=(
            "Lower the per-call deletion cap. Cannot raise it above "
            "branch_actions.max_deletions."
        ),
    )


@router.post(
    "/{name}/branches/prune",
    dependencies=[Depends(require_auth)],
    response_model=BranchCleanupResponse,
)
async def prune_project_branches(
    name: str,
    body: BranchPruneRequest | None = None,
) -> BranchCleanupResponse:
    """Preview (or, with ``confirm``, perform) deletion of stale branches.

    Dry run by default.  Only branches fully merged into the repository's
    *detected* default branch are eligible; the default branch itself,
    protected patterns, the checked-out branch, branches live in a
    worktree, and branches holding unpushed commits are never deleted.
    """
    body = body or BranchPruneRequest()
    config = get_config()
    organiser = config.agents.project_organiser
    settings = organiser.branch_actions
    if not settings.enabled:
        raise HTTPException(
            status_code=409,
            detail=(
                "Branch actions are disabled "
                "(agents.project_organiser.branch_actions.enabled)"
            ),
        )

    stale_days = (
        organiser.stale_branch_days if body.stale_days is None else body.stale_days
    )
    # Both the manifest id and the directory name resolve, because a
    # caller reasonably uses either: the board reports directory names,
    # services.yaml references ids.
    registry = load_registry(organiser.projects_root)
    managed_paths: dict[str, str] = {}
    for entry in registry.declared:
        managed_paths.setdefault(entry.id, str(entry.path))
        managed_paths.setdefault(entry.path.name, str(entry.path))

    try:
        repo_path = await asyncio.to_thread(
            branch_actions.resolve_project_repo,
            name,
            Path(organiser.projects_root),
            managed_paths,
        )
        plan = await asyncio.to_thread(
            branch_actions.plan_branch_cleanup,
            repo_path,
            settings,
            stale_days,
            body.include_unmerged,
            body.max_deletions,
            name,
        )
        if not body.confirm:
            plan.message = (
                f"{plan.message + ' — ' if plan.message else ''}"
                "dry run: nothing was deleted. Send confirm=true to apply."
            ).strip()
            return plan
        return await asyncio.to_thread(
            branch_actions.execute_branch_cleanup,
            plan,
            repo_path,
            settings,
            body.include_unmerged,
        )
    except branch_actions.BranchActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
