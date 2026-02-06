"""File Organiser API endpoints — filesystem audit, cleanup, trends."""

import asyncio
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.database import get_db_session
from sysadmin.models.filesystem_audit import FilesystemAudit

router = APIRouter(prefix="/api/files", tags=["files"])


@router.get("/status")
async def get_file_status(session: AsyncSession = Depends(get_db_session)):
    """Get summary of the latest filesystem audit."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        return {"message": "No audit data yet. Trigger a scan with POST /api/files/scan"}

    return {
        "scan_root": audit.scan_root,
        "scanned_at": audit.scanned_at.isoformat() if audit.scanned_at else None,
        "summary": {
            "similar_folders": audit.similar_folders_count,
            "misplaced_files": audit.misplaced_files_count,
            "old_downloads": audit.old_downloads_count,
            "large_files": audit.large_files_count,
            "duplicate_groups": audit.duplicate_groups_count,
            "empty_dirs": audit.empty_dirs_count,
            "stale_project_dirs": audit.stale_project_dirs_count,
            "stale_files": audit.stale_files_count,
        },
        "reclaimable_mb": audit.total_reclaimable_mb,
        "quick_wins": audit.findings.get("quick_wins", {}),
    }


@router.get("/report")
async def get_file_report(session: AsyncSession = Depends(get_db_session)):
    """Get the full latest audit report findings."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="No audit data yet")

    return {
        "scanned_at": audit.scanned_at.isoformat() if audit.scanned_at else None,
        "findings": audit.findings,
        "reclaimable_mb": audit.total_reclaimable_mb,
    }


@router.get("/report/delta")
async def get_delta_report(session: AsyncSession = Depends(get_db_session)):
    """Get changes between the two most recent scans."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(2)
    )
    result = await session.execute(query)
    audits = result.scalars().all()

    if len(audits) < 2:
        return {"message": "Need at least 2 scans for a delta report"}

    current, previous = audits[0], audits[1]

    return {
        "current_scan": current.scanned_at.isoformat() if current.scanned_at else None,
        "previous_scan": previous.scanned_at.isoformat() if previous.scanned_at else None,
        "delta": {
            "similar_folders": current.similar_folders_count - previous.similar_folders_count,
            "misplaced_files": current.misplaced_files_count - previous.misplaced_files_count,
            "old_downloads": current.old_downloads_count - previous.old_downloads_count,
            "large_files": current.large_files_count - previous.large_files_count,
            "duplicate_groups": current.duplicate_groups_count - previous.duplicate_groups_count,
            "empty_dirs": current.empty_dirs_count - previous.empty_dirs_count,
            "stale_project_dirs": current.stale_project_dirs_count - previous.stale_project_dirs_count,
            "stale_files": current.stale_files_count - previous.stale_files_count,
            "reclaimable_mb": current.total_reclaimable_mb - previous.total_reclaimable_mb,
        },
    }


@router.get("/duplicates")
async def get_duplicates(session: AsyncSession = Depends(get_db_session)):
    """Get duplicate file groups from the latest scan."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="No audit data yet")

    return {
        "duplicate_groups": audit.findings.get("duplicates", []),
        "count": audit.duplicate_groups_count,
    }


@router.get("/large")
async def get_large_files(session: AsyncSession = Depends(get_db_session)):
    """Get large files from the latest scan."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="No audit data yet")

    return {
        "large_files": audit.findings.get("large_files", []),
        "count": audit.large_files_count,
    }


@router.get("/misplaced")
async def get_misplaced_files(session: AsyncSession = Depends(get_db_session)):
    """Get misplaced files by category from the latest scan."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="No audit data yet")

    return {
        "misplaced_files": audit.findings.get("misplaced_files", {}),
        "count": audit.misplaced_files_count,
    }


@router.get("/trends")
async def get_trends(
    limit: int = Query(default=10, le=50),
    session: AsyncSession = Depends(get_db_session),
):
    """Get historical finding counts for trend analysis."""
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(limit)
    )
    result = await session.execute(query)
    audits = result.scalars().all()

    return {
        "scans": [
            {
                "scanned_at": a.scanned_at.isoformat() if a.scanned_at else None,
                "similar_folders": a.similar_folders_count,
                "misplaced_files": a.misplaced_files_count,
                "old_downloads": a.old_downloads_count,
                "large_files": a.large_files_count,
                "duplicate_groups": a.duplicate_groups_count,
                "empty_dirs": a.empty_dirs_count,
                "stale_project_dirs": a.stale_project_dirs_count,
                "reclaimable_mb": a.total_reclaimable_mb,
            }
            for a in audits
        ],
        "count": len(audits),
    }


@router.post("/scan")
async def trigger_scan(request: Request):
    """Trigger an immediate filesystem scan."""
    agent = request.app.state.file_organiser_agent
    if agent is None:
        raise HTTPException(status_code=503, detail="File organiser agent not available")

    asyncio.create_task(agent.run(run_type="manual"))
    return {"status": "scan_triggered"}


@router.post("/clean/stale-caches")
async def clean_stale_caches(
    confirm: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
):
    """Auto-remove __pycache__, .pytest_cache, empty dirs. Requires confirm=true."""
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": "Set confirm=true to proceed. This will remove __pycache__, .pytest_cache, and empty directories.",
        }

    # Get latest audit for targets
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    result = await session.execute(query)
    audit = result.scalar_one_or_none()

    if not audit:
        raise HTTPException(status_code=404, detail="No audit data. Run a scan first.")

    removed = {"caches": [], "empty_dirs": []}

    # Remove stale caches
    for d in audit.findings.get("stale_project_dirs", []):
        if d.get("type") in ("__pycache__", ".pytest_cache"):
            path = Path(d["path"])
            if path.exists():
                try:
                    await asyncio.to_thread(shutil.rmtree, path)
                    removed["caches"].append(str(path))
                except (PermissionError, OSError) as e:
                    logger.warning("clean_failed", extra={"path": str(path), "error": str(e)})

    # Remove empty dirs
    for d_str in audit.findings.get("empty_dirs", [])[:50]:
        path = Path(d_str)
        if path.exists():
            try:
                path.rmdir()
                removed["empty_dirs"].append(str(path))
            except (PermissionError, OSError):
                pass

    return {
        "status": "cleaned",
        "removed_caches": len(removed["caches"]),
        "removed_empty_dirs": len(removed["empty_dirs"]),
        "details": removed,
    }


# Needed for the clean endpoint logging
import logging
logger = logging.getLogger(__name__)
