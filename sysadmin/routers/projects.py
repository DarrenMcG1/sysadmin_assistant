"""Project Organiser API endpoints."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.auth import require_auth
from sysadmin.config import get_config
from sysadmin.contracts import (
    BranchCleanupResponse,
    ManagedProjectsResponse,
    ProjectOverviewResponse,
)
from sysadmin.database import get_db_session
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.models.service_health import ServiceHealth
from sysadmin.services import branch_actions

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/overview", response_model=ProjectOverviewResponse)
async def get_projects_overview(session: AsyncSession = Depends(get_db_session)):
    """Get all projects with their latest health scores."""
    # Latest snapshot per project
    latest_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )

    query = (
        select(ProjectSnapshot)
        .join(
            latest_subq,
            (ProjectSnapshot.project_name == latest_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == latest_subq.c.max_scanned),
        )
        .order_by(desc(ProjectSnapshot.health_score))
    )

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


@router.get("/stale")
async def get_stale_projects(
    days: int = Query(default=30, le=365),
    session: AsyncSession = Depends(get_db_session),
):
    """Get projects with no activity in N days."""
    bands = get_config().agents.project_organiser.grade_bands
    # Latest snapshot per project
    latest_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )

    query = (
        select(ProjectSnapshot)
        .join(
            latest_subq,
            (ProjectSnapshot.project_name == latest_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == latest_subq.c.max_scanned),
        )
        .where(ProjectSnapshot.health_score < bands.needs_attention_min)
        .order_by(ProjectSnapshot.health_score)
    )

    result = await session.execute(query)
    rows = result.scalars().all()

    return {
        "stale_projects": [
            {
                "name": r.project_name,
                "health_score": r.health_score,
                "last_commit_at": r.last_commit_at.isoformat() if r.last_commit_at else None,
                "findings": r.findings,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/report")
async def get_projects_report(session: AsyncSession = Depends(get_db_session)):
    """Get a full markdown report of all projects."""
    # Latest snapshot per project
    latest_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )

    query = (
        select(ProjectSnapshot)
        .join(
            latest_subq,
            (ProjectSnapshot.project_name == latest_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == latest_subq.c.max_scanned),
        )
        .order_by(desc(ProjectSnapshot.health_score))
    )

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
    managed = config.projects.projects

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
    latest_snap_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )
    snap_query = (
        select(ProjectSnapshot)
        .join(
            latest_snap_subq,
            (ProjectSnapshot.project_name == latest_snap_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == latest_snap_subq.c.max_scanned),
        )
    )
    snap_result = await session.execute(snap_query)
    snap_map = {r.project_name: r for r in snap_result.scalars().all()}

    projects_out = []
    for mp in managed:
        svc_entries = mp.to_monitored_services()
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
            "path": mp.path,
            "services": services,
            "project_health": project_health,
            "all_services_healthy": all_healthy if services else None,
        })

    return {"projects": projects_out, "count": len(projects_out)}


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
        "history": [
            {
                "health_score": r.health_score,
                "scanned_at": r.scanned_at.isoformat() if r.scanned_at else None,
            }
            for r in rows
        ],
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
# The rules themselves live in ``sysadmin.services.branch_actions``.
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
    managed_paths = {
        project.name: project.path
        for project in config.projects.projects
        if project.path
    }

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
