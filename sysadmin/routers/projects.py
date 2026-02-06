"""Project Organiser API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.database import get_db_session
from sysadmin.models.project_snapshot import ProjectSnapshot

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("/overview")
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

    def _grade(score: int) -> str:
        if score >= 80:
            return "healthy"
        if score >= 60:
            return "needs_attention"
        if score >= 40:
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
        .where(ProjectSnapshot.health_score < 60)
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

    lines = ["# Project Health Report\n"]
    for r in rows:
        score_emoji = "🟢" if r.health_score >= 80 else "🟡" if r.health_score >= 60 else "🔴"
        lines.append(f"## {score_emoji} {r.project_name} — {r.health_score}/100\n")
        lines.append(f"- **Path:** `{r.project_path}`")
        if r.last_commit_at:
            lines.append(f"- **Last commit:** {r.last_commit_at.strftime('%Y-%m-%d')}")
        lines.append(f"- **Branches:** {r.branch_count} ({r.stale_branch_count} stale)")
        lines.append(f"- **TODOs:** {r.todo_count or 0}  |  **FIXMEs:** {r.fixme_count or 0}")
        lines.append(f"- **README:** {'✓' if r.has_readme else '✗'}  |  **CLAUDE.md:** {'✓' if r.has_claude_md else '✗'}")
        lines.append(f"- **Size:** {r.total_size_mb} MB")
        if r.findings:
            lines.append(f"- **Findings:** {r.findings}")
        lines.append("")

    return {"report": "\n".join(lines)}


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


@router.post("/scan")
async def trigger_scan(request: Request):
    """Trigger an immediate project scan."""
    agent = request.app.state.project_organiser_agent
    if agent is None:
        raise HTTPException(status_code=503, detail="Project organiser agent not available")

    # Run in background to avoid request timeout
    import asyncio
    asyncio.create_task(agent.run(run_type="manual"))
    return {"status": "scan_triggered"}
