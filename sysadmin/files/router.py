"""File Organiser API endpoints — filesystem audit, cleanup, trends."""

import asyncio
import logging
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.auth import require_auth
from sysadmin.core.config import AppConfig, FileOrganiserConfig, get_config
from sysadmin.core.contracts import (
    DiskReviewResponse,
    FileActionResponse,
    FileActionsResponse,
)
from sysadmin.core.database import get_db_session
from sysadmin.files import actions as file_actions
from sysadmin.files import forecast
from sysadmin.files import recommendations as file_recommendations
from sysadmin.files import review as disk_review
from sysadmin.files.models.disk_review import DiskReview
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

logger = logging.getLogger(__name__)

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
            "duplicate_groups": (
                current.duplicate_groups_count - previous.duplicate_groups_count
            ),
            "empty_dirs": current.empty_dirs_count - previous.empty_dirs_count,
            "stale_project_dirs": (
                current.stale_project_dirs_count - previous.stale_project_dirs_count
            ),
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
    """Get historical finding counts with growth rate and threshold projection.

    Night Worker uses this to predict when disk thresholds will be hit.
    Returns per-scan data plus a ``forecast`` section with linear growth
    rate and projected dates for warning/critical thresholds.
    """
    query = (
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(limit)
    )
    result = await session.execute(query)
    audits = result.scalars().all()

    scans = [
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
    ]

    forecast = _compute_reclaimable_forecast(list(audits))

    return {
        "scans": scans,
        "count": len(audits),
        "forecast": forecast,
    }


def _review_payload(review: DiskReview) -> dict:
    return {
        "generated_at": (
            review.generated_at.isoformat() if review.generated_at else None
        ),
        "period_days": review.period_days,
        "narrative": review.narrative,
        "llm_used": review.llm_used,
        "model_used": review.model_used,
        "stats": review.stats,
    }


@router.get("/review", response_model=DiskReviewResponse)
async def get_disk_review(session: AsyncSession = Depends(get_db_session)):
    """The latest stored weekly disk review."""
    result = await session.execute(
        select(DiskReview).order_by(desc(DiskReview.generated_at)).limit(1)
    )
    review = result.scalars().first()
    if review is None:
        raise HTTPException(status_code=404, detail="No review generated yet")
    return _review_payload(review)


@router.post(
    "/review/generate",
    response_model=DiskReviewResponse,
    dependencies=[Depends(require_auth)],
)
async def generate_disk_review(session: AsyncSession = Depends(get_db_session)):
    """Generate a review on demand (falls back to a digest if the LLM is down)."""
    review = await disk_review.generate_review(session)
    if review is None:
        raise HTTPException(status_code=409, detail="No filesystem audits to review")
    return _review_payload(review)


@router.get("/actions", response_model=FileActionsResponse)
async def get_file_actions(
    limit: int = Query(default=10, le=50),
    history_days: int = Query(default=30, ge=2, le=365),
    mount: str = Query(default="/"),
    session: AsyncSession = Depends(get_db_session),
):
    """Top disk wins from the latest audit, ranked risk-first.

    The mirror of ``GET /api/projects/actions``, with reclaimable
    megabytes in place of health-score points.

    "Risk-first" needs a second table.  ``filesystem_audits`` tracks
    *junk accumulation*; only ``resource_snapshots`` knows disk
    *occupancy*, and it is occupancy that answers "when does this disk
    fill up".  So the projected 80 %/90 % crossing is fitted over the
    last ``history_days`` of resource history and, when it lands inside
    the risk horizon, outranks every byte total below it.  With too
    little history to fit a line the endpoint degrades to a plain
    megabytes-descending ranking rather than failing.
    """
    audit_result = await session.execute(
        select(FilesystemAudit)
        .order_by(desc(FilesystemAudit.scanned_at))
        .limit(1)
    )
    audit = audit_result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="No audit data yet")

    cutoff = datetime.now(UTC) - timedelta(days=history_days)
    snapshot_result = await session.execute(
        select(ResourceSnapshot.recorded_at, ResourceSnapshot.disk_usage)
        .where(ResourceSnapshot.recorded_at >= cutoff)
        .order_by(ResourceSnapshot.recorded_at)
    )
    series = forecast.disk_series_from(
        ((row.recorded_at, row.disk_usage) for row in snapshot_result), mount
    )
    projection = forecast.most_urgent_projection(
        forecast.project_disk_thresholds(series),
        horizon_days=file_recommendations.RISK_HORIZON_DAYS,
    )

    agent_config = get_config().agents.file_organiser
    recs = file_recommendations.recommendations_for_audit(
        audit.findings or {},
        agent_config,
        projection,
        # The findings blob is truncated to 50–100 entries per category
        # before storage; these columns hold the real totals.  Without
        # them a live scan reports "200 misplaced files" against an
        # actual 11,877.
        true_counts={
            "duplicates": audit.duplicate_groups_count,
            "old_downloads": audit.old_downloads_count,
            "misplaced_files": audit.misplaced_files_count,
            "large_files": audit.large_files_count,
            "empty_dirs": audit.empty_dirs_count,
            "similar_folders": audit.similar_folders_count,
            "stale_project_dirs": audit.stale_project_dirs_count,
        },
    )

    return {
        "actions": [r.model_dump() for r in recs[:limit]],
        "count": min(len(recs), limit),
        "total_available": len(recs),
        # Sums every recommendation, not just the returned page — the
        # headline "this much is on the table" must not shrink because
        # the caller asked for a smaller limit.
        "total_reclaimable_mb": file_recommendations.total_reclaimable_mb(recs),
        "scanned_at": audit.scanned_at.isoformat() if audit.scanned_at else None,
        "disk_forecast": projection._asdict() if projection else None,
    }


def _compute_reclaimable_forecast(
    audits: list[FilesystemAudit],
) -> dict:
    """Compute linear growth rate of reclaimable_mb and project threshold dates.

    Uses simple linear regression on (timestamp, reclaimable_mb) pairs.
    Returns growth_rate_mb_per_day and projected dates when reclaimable
    space reaches the milestones configured under
    ``agents.file_organiser.reclaimable_milestones_mb`` (default 1/5/10 GB).
    """
    if len(audits) < 2:
        return {"insufficient_data": True}

    # Build (days_since_first, reclaimable_mb) pairs — oldest first
    ordered = sorted(
        [(a.scanned_at, a.total_reclaimable_mb) for a in audits if a.scanned_at],
        key=lambda x: x[0],
    )
    if len(ordered) < 2:
        return {"insufficient_data": True}

    t0 = ordered[0][0]
    points = [
        ((ts - t0).total_seconds() / 86400, mb) for ts, mb in ordered
    ]

    # One least-squares implementation for the whole codebase — this
    # used to hand-roll the same arithmetic as
    # ``sysadmin.files.forecast.linear_fit``.  A degenerate x-range
    # (every scan at the same instant) returns None there and keeps the
    # "flat growth" answer it has always given here.
    fit = forecast.linear_fit(points)
    if fit is None:
        return {"growth_rate_mb_per_day": 0.0}
    n, slope, intercept = fit.points, fit.slope, fit.intercept

    current_mb = ordered[-1][1]
    latest_ts = ordered[-1][0]

    result: dict = {
        "growth_rate_mb_per_day": round(slope, 2),
        "current_reclaimable_mb": current_mb,
        "data_points": n,
    }

    # Project when milestones will be reached (only if growing)
    if slope > 0:
        milestones_mb = get_config().agents.file_organiser.reclaimable_milestones_mb
        milestones = {f"{mb / 1024:g}gb": mb for mb in milestones_mb}
        projections = {}
        days_since_first = (latest_ts - t0).total_seconds() / 86400

        for label, target_mb in milestones.items():
            if current_mb >= target_mb:
                continue
            days_to_target = (target_mb - intercept) / slope
            days_from_now = days_to_target - days_since_first
            if days_from_now > 0:
                projected_date = latest_ts + timedelta(days=days_from_now)
                projections[label] = projected_date.strftime("%Y-%m-%d")

        if projections:
            result["projected_milestones"] = projections

    return result


@router.post("/scan", dependencies=[Depends(require_auth)])
async def trigger_scan(request: Request):
    """Trigger an immediate filesystem scan."""
    agent = request.app.state.file_organiser_agent
    if agent is None:
        raise HTTPException(status_code=503, detail="File organiser agent not available")

    asyncio.create_task(agent.run(run_type="manual"))
    return {"status": "scan_triggered"}


@router.post("/clean/stale-caches", dependencies=[Depends(require_auth)])
async def clean_stale_caches(
    confirm: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
):
    """Auto-remove __pycache__, .pytest_cache, empty dirs. Requires confirm=true."""
    if not confirm:
        return {
            "status": "confirmation_required",
            "message": (
                "Set confirm=true to proceed. This will remove __pycache__, "
                ".pytest_cache, and empty directories."
            ),
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

    removed: dict[str, list[str]] = {"caches": [], "empty_dirs": []}

    # Remove stale caches
    for d in audit.findings.get("stale_project_dirs", []):
        if d.get("type") in ("__pycache__", ".pytest_cache"):
            path = Path(d["path"])
            if path.exists():
                try:
                    await asyncio.to_thread(shutil.rmtree, path)
                    removed["caches"].append(str(path))
                except (PermissionError, OSError) as e:
                    logger.warning(
                        "clean_failed", extra={"path": str(path), "error": str(e)}
                    )

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


# ---------------------------------------------------------------------------
# Mutating file actions — organise, de-duplicate, clean downloads
#
# All three follow the same contract:
#   * POST only, behind ``require_auth``
#   * **dry run unless the body sets ``confirm: true``** — the default
#     response is a manifest of what *would* happen and nothing is touched
#   * the same manifest shape comes back either way (``FileActionResponse``),
#     with per-operation source → destination, byte counts and a status
#   * every path is confined to the agent's ``scan_root`` and "delete"
#     means "move to the XDG trash"
# The safety rules themselves live in ``sysadmin.files.actions``.
# ---------------------------------------------------------------------------


class ActionRequest(BaseModel):
    """Base body — nothing happens on the filesystem without ``confirm``."""

    confirm: bool = Field(
        default=False,
        description="Set true to actually perform the operation. Default is a dry run.",
    )


class OrganiseRequest(ActionRequest):
    categories: list[str] | None = Field(
        default=None,
        description=(
            "Limit to these categories: images, videos, documents, audio, "
            "books, archives."
        ),
    )


class DuplicateCleanupRequest(ActionRequest):
    strategy: str | None = Field(
        default=None,
        description="Which copy to retain: 'newest' or 'largest'. Defaults to config.",
    )
    force_delete: bool = Field(
        default=False,
        description=(
            "Permit an unrecoverable delete when the trash is unusable. Also "
            "requires actions.allow_permanent_delete in config."
        ),
    )


class DownloadsCleanupRequest(ActionRequest):
    mode: str = Field(
        default="archive", description="'archive' (move) or 'trash' (send to XDG trash)."
    )
    older_than_days: int | None = Field(
        default=None,
        description=(
            "Age threshold in days. Defaults to "
            "agents.file_organiser.downloads_stale_days."
        ),
    )
    force_delete: bool = Field(default=False)


def _action_config() -> tuple[AppConfig, FileOrganiserConfig]:
    """Fetch config, refusing every action when the kill switch is off."""
    config = get_config()
    organiser = config.agents.file_organiser
    if not organiser.actions.enabled:
        raise HTTPException(
            status_code=409,
            detail="File actions are disabled (agents.file_organiser.actions.enabled)",
        )
    return config, organiser


def _excluded_roots(config: AppConfig) -> list[Path]:
    """Trees the actions must never descend into.

    The user's project directories are off limits: files there belong to
    work in progress, not to a tidy-up.
    """
    roots: list[Path] = []
    projects_root = config.agents.project_organiser.projects_root
    if projects_root:
        roots.append(Path(projects_root).expanduser().resolve())
    return roots


async def _run_action(planner, organiser, confirm: bool, force_delete: bool = False):
    """Plan in a worker thread, then execute only when confirmed."""
    try:
        plan = await asyncio.to_thread(planner)
        if not confirm:
            plan.message = (
                f"{plan.message + ' — ' if plan.message else ''}"
                "dry run: nothing was changed. Send confirm=true to apply."
            ).strip()
            return plan
        return await asyncio.to_thread(
            file_actions.execute_plan,
            plan,
            organiser,
            force_delete,
            Path(organiser.scan_root).expanduser(),
        )
    except file_actions.FileActionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/organise",
    dependencies=[Depends(require_auth)],
    response_model=FileActionResponse,
)
async def organise_files(body: OrganiseRequest | None = None) -> FileActionResponse:
    """Relocate misplaced files into their configured category folders.

    Dry run by default. Loose code files in the scan root are reported
    under ``flagged`` and never moved; destination collisions are skipped
    rather than overwritten.
    """
    body = body or OrganiseRequest()
    config, organiser = _action_config()
    excluded = _excluded_roots(config)
    return await _run_action(
        lambda: file_actions.plan_organise(organiser, excluded, body.categories),
        organiser,
        body.confirm,
    )


@router.post(
    "/clean/duplicates",
    dependencies=[Depends(require_auth)],
    response_model=FileActionResponse,
)
async def clean_duplicates(
    body: DuplicateCleanupRequest | None = None,
) -> FileActionResponse:
    """Remove duplicate copies, always retaining exactly one per group.

    Dry run by default. Removals go to the XDG trash so they stay
    recoverable.
    """
    body = body or DuplicateCleanupRequest()
    config, organiser = _action_config()
    excluded = _excluded_roots(config)
    return await _run_action(
        lambda: file_actions.plan_duplicate_cleanup(organiser, excluded, body.strategy),
        organiser,
        body.confirm,
        body.force_delete,
    )


@router.post(
    "/clean/downloads",
    dependencies=[Depends(require_auth)],
    response_model=FileActionResponse,
)
async def clean_downloads(
    body: DownloadsCleanupRequest | None = None,
) -> FileActionResponse:
    """Archive or trash downloads older than a configurable age.

    Dry run by default. ``mode=archive`` moves files into the configured
    archive folder preserving their relative path; ``mode=trash`` sends
    them to the XDG trash.
    """
    body = body or DownloadsCleanupRequest()
    config, organiser = _action_config()
    excluded = _excluded_roots(config)
    return await _run_action(
        lambda: file_actions.plan_downloads_cleanup(
            organiser, excluded, body.mode, body.older_than_days
        ),
        organiser,
        body.confirm,
        body.force_delete,
    )
