"""Branch hygiene — preview and prune stale local git branches.

This module does the *dangerous* work behind
``POST /api/projects/{name}/branches/prune``.  It is plain GitPython and
pathlib: no FastAPI, no database, no ``app.state`` — so every safety rule
can be unit-tested against throwaway repos built under ``tmp_path``.

Safety model
------------
Deleting a branch can destroy work that exists nowhere else, so this
follows the same shape as ``sysadmin.services.file_actions`` (Session 18)
and then tightens it:

1. **Dry run by default.**  :func:`plan_branch_cleanup` returns a full
   manifest and touches nothing.  The router only calls
   :func:`execute_branch_cleanup` when the body carried ``confirm: true``.
2. **Merged-only by default.**  A branch is eligible only when git itself
   says every one of its commits is reachable from the default branch
   (``repo.is_ancestor`` → ``merge-base --is-ancestor``).  Dates are never
   used to infer merged-ness — an old branch is not a merged branch.
3. **Two flags for unmerged.**  Deleting an unmerged branch needs the
   request to set ``include_unmerged: true`` **and** config to allow
   ``branch_actions.allow_unmerged_delete`` — mirroring Session 18's
   ``force_delete`` + ``allow_permanent_delete`` pattern.  Both default to
   off, so the dangerous case cannot happen by accident or by config
   alone.
4. **Never touched**, whatever the flags say:
   - the detected default branch,
   - any branch matching a ``protected_branches`` glob,
   - the currently checked-out branch,
   - any branch checked out in a linked worktree,
   - any branch with commits its upstream does not have.
5. **The default branch is detected, never assumed** (see
   :func:`sysadmin.utils.git.detect_default_branch`).  When it cannot be
   determined the whole repo is reported and *nothing* is planned:
   without it, "merged" is undefined.
6. **Root confinement.**  The repo path is resolved (symlinks collapsed)
   and must land inside the configured ``projects_root``.
7. **Capped.**  ``max_deletions`` bounds a single call; a request may ask
   for fewer, never more.  Branches beyond the cap are reported, not
   deleted.
8. **Ambiguity is reported, not acted on.**  An unreadable upstream, an
   unreadable commit date, a detached HEAD — all become a ``skipped``
   row with a reason.
9. **Safe delete.**  Execution uses ``git branch -d``, which refuses to
   drop an unmerged branch, so git independently re-checks rule 2.
   ``-D`` is used only for the deliberately opted-in unmerged case.
10. **Plans are re-validated at execution time** against the live repo:
    the branch may have moved, been checked out, or been merged since
    the preview.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from fnmatch import fnmatch
from pathlib import Path

from git import Repo

from sysadmin.config import BranchActionsConfig
from sysadmin.contracts import BranchCleanupResponse, BranchInfo
from sysadmin.utils.git import (
    detect_default_branch,
    get_repo,
    is_merged_into,
    upstream_state,
    worktree_branches,
)

logger = logging.getLogger(__name__)

NO_DEFAULT_BRANCH_MESSAGE = (
    "the default branch could not be determined — refusing to prune, since "
    "'merged' is defined relative to it"
)


class BranchActionError(Exception):
    """A request the branch layer refuses outright — mapped to HTTP 4xx."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


# ── Locating the repository ──────────────────────────────────────────


def resolve_project_repo(
    name: str,
    projects_root: Path,
    managed_paths: dict[str, str] | None = None,
) -> Path:
    """Resolve a project name to a repo path inside ``projects_root``.

    Accepts either a directory name under the projects root or the name
    of a projects.yaml entry (whose ``path`` is then used).  The result
    is fully resolved and must sit inside the root — a name containing
    ``..`` or an absolute-looking segment is refused, and so is a managed
    project whose path points elsewhere on disk.

    Raises:
        BranchActionError: name is unusable (400), the path escapes the
            root (400), or nothing is there (404).
    """
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise BranchActionError(f"invalid project name {name!r}", 400)

    root = Path(projects_root).expanduser().resolve()
    candidates: list[Path] = [root / name]

    managed = managed_paths or {}
    configured = managed.get(name)
    if configured:
        candidates.insert(0, Path(configured).expanduser())

    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved == root or root not in resolved.parents:
            raise BranchActionError(
                f"refusing to operate on {candidate}: resolves outside the "
                f"configured projects root {root}",
                400,
            )
        if resolved.is_dir():
            return resolved

    raise BranchActionError(f"project {name!r} not found under {root}", 404)


# ── Planning ─────────────────────────────────────────────────────────


def _finalise(response: BranchCleanupResponse) -> BranchCleanupResponse:
    """Recompute the summary counters from the manifest."""
    response.total_branches = len(response.branches)
    response.planned_count = sum(1 for b in response.branches if b.status == "planned")
    response.deleted_count = sum(1 for b in response.branches if b.status == "deleted")
    response.skipped_count = sum(1 for b in response.branches if b.status == "skipped")
    response.failed_count = sum(1 for b in response.branches if b.status == "failed")
    return response


def _current_branch(repo: Repo) -> str | None:
    """Name of the checked-out branch, or None for a detached HEAD."""
    try:
        if repo.head.is_detached:
            return None
        return repo.active_branch.name
    except Exception:
        return None


def _protected_by(name: str, patterns: list[str]) -> str | None:
    """The first glob in ``patterns`` that matches ``name``, if any."""
    for pattern in patterns:
        if fnmatch(name, pattern):
            return pattern
    return None


def _commit_age(branch) -> tuple[datetime | None, int]:
    """``(committed_datetime_utc, days_since)`` for a branch tip."""
    try:
        committed = branch.commit.committed_datetime
    except Exception:
        return None, 0
    if committed.tzinfo is None:
        committed = committed.replace(tzinfo=UTC)
    return committed, (datetime.now(UTC) - committed).days


def _describe(repo: Repo, branch, default_ref) -> BranchInfo:
    """Build the descriptive (non-decision) part of a manifest row."""
    committed, days = _commit_age(branch)
    try:
        sha = branch.commit.hexsha
    except Exception:
        sha = ""
    upstream, ahead = upstream_state(repo, branch)
    return BranchInfo(
        name=branch.name,
        last_commit_at=committed.isoformat() if committed else None,
        last_commit_sha=sha,
        days_stale=days,
        merged=is_merged_into(repo, branch, default_ref) if default_ref else False,
        upstream=upstream,
        ahead=ahead,
        status="skipped",
    )


def _classify(
    info: BranchInfo,
    *,
    default_branch: str,
    current: str | None,
    worktrees: set[str],
    protected: list[str],
    stale_days: int,
    unmerged_allowed: bool,
    has_commit_date: bool,
) -> None:
    """Decide a single branch's fate, setting ``status`` and ``reason``.

    Order matters: the identity rules (default / protected / checked out)
    are applied before the age and merge rules so the reason a branch
    survived is always the strongest one.
    """
    name = info.name

    if name == default_branch:
        info.reason = "the default branch"
        return

    pattern = _protected_by(name, protected)
    if pattern is not None:
        info.reason = f"protected by pattern {pattern!r}"
        return

    if name == current:
        info.reason = "currently checked out"
        return

    if name in worktrees:
        info.reason = "checked out in a worktree"
        return

    if not has_commit_date:
        info.reason = "last commit date could not be read — reporting only"
        return

    if info.days_stale < stale_days:
        info.reason = (
            f"last commit {info.days_stale} day(s) ago — newer than the "
            f"{stale_days}-day stale threshold"
        )
        return

    if info.ahead is None:
        info.reason = (
            f"tracks {info.upstream} but its state could not be read — "
            "reporting only"
        )
        return
    if info.ahead > 0:
        info.reason = (
            f"{info.ahead} commit(s) not present on upstream {info.upstream}"
        )
        return

    if not info.merged:
        if not unmerged_allowed:
            info.reason = (
                f"not merged into {default_branch} — needs include_unmerged "
                "on the request and branch_actions.allow_unmerged_delete in "
                "config"
            )
            return
        info.status = "planned"
        info.reason = (
            f"stale {info.days_stale} day(s) and NOT merged into "
            f"{default_branch} — unmerged deletion explicitly enabled"
        )
        return

    info.status = "planned"
    info.reason = (
        f"merged into {default_branch}, last commit {info.days_stale} day(s) ago"
    )


def _apply_cap(response: BranchCleanupResponse, cap: int) -> None:
    """Demote planned rows beyond ``cap`` back to skipped.

    Branches are already ordered oldest-first, so the cap keeps the
    stalest ones — the least likely to be wanted back.
    """
    kept = 0
    for info in response.branches:
        if info.status != "planned":
            continue
        kept += 1
        if kept > cap:
            info.status = "skipped"
            info.reason = f"max_deletions cap of {cap} reached — not deleted"
            response.truncated = True


def plan_branch_cleanup(
    repo_path: Path,
    config: BranchActionsConfig,
    stale_days: int,
    include_unmerged: bool = False,
    max_deletions: int | None = None,
    project: str = "",
) -> BranchCleanupResponse:
    """Build the manifest of branches a prune would delete.

    Touches nothing.  Every local branch appears in the result, planned
    or skipped-with-a-reason, so the caller can see the whole picture
    before confirming.

    Raises:
        BranchActionError: the path is not a git repo, or ``stale_days``
            is below ``config.min_stale_days``.
    """
    if stale_days < config.min_stale_days:
        raise BranchActionError(
            f"stale_days must be at least {config.min_stale_days} "
            f"(branch_actions.min_stale_days)",
            400,
        )
    cap = config.max_deletions
    if max_deletions is not None:
        if max_deletions < 0:
            raise BranchActionError("max_deletions must not be negative", 400)
        cap = min(cap, max_deletions)

    repo = get_repo(repo_path)
    if repo is None:
        raise BranchActionError(f"{repo_path} is not a git repository", 400)

    unmerged_allowed = include_unmerged and config.allow_unmerged_delete

    response = BranchCleanupResponse(
        project=project or repo_path.name,
        repo_path=str(repo_path),
        dry_run=True,
        stale_days=stale_days,
        max_deletions=cap,
        include_unmerged=unmerged_allowed,
    )

    default_branch = detect_default_branch(repo)
    if default_branch is None:
        response.default_branch = ""
        for branch in _ordered_branches(repo):
            info = _describe(repo, branch, None)
            info.reason = NO_DEFAULT_BRANCH_MESSAGE
            response.branches.append(info)
        response.message = NO_DEFAULT_BRANCH_MESSAGE
        return _finalise(response)

    response.default_branch = default_branch
    default_ref = repo.heads[default_branch]
    current = _current_branch(repo)
    worktrees = worktree_branches(repo)

    for branch in _ordered_branches(repo):
        info = _describe(repo, branch, default_ref)
        _classify(
            info,
            default_branch=default_branch,
            current=current,
            worktrees=worktrees,
            protected=list(config.protected_branches),
            stale_days=stale_days,
            unmerged_allowed=unmerged_allowed,
            has_commit_date=info.last_commit_at is not None,
        )
        response.branches.append(info)

    _apply_cap(response, cap)
    response.message = (
        f"{len(response.branches)} local branch(es); eligible = merged into "
        f"{default_branch} and untouched for {stale_days}+ days"
    )
    if include_unmerged and not config.allow_unmerged_delete:
        response.message += (
            " — include_unmerged ignored: branch_actions.allow_unmerged_delete "
            "is false in config"
        )
    return _finalise(response)


def _ordered_branches(repo: Repo) -> list:
    """Local branches, oldest tip first (ties broken by name)."""
    try:
        branches = list(repo.branches)
    except Exception:
        return []

    def sort_key(branch):
        committed, _days = _commit_age(branch)
        stamp = committed.timestamp() if committed else 0.0
        return (stamp, branch.name)

    return sorted(branches, key=sort_key)


# ── Execution ────────────────────────────────────────────────────────


def execute_branch_cleanup(
    response: BranchCleanupResponse,
    repo_path: Path,
    config: BranchActionsConfig,
    include_unmerged: bool = False,
) -> BranchCleanupResponse:
    """Delete the planned branches, re-checking every rule first.

    The plan was built from an earlier read of the repo and the repo may
    have moved on — a branch could now be checked out, or have gained
    commits.  Each row is re-validated against the live repo immediately
    before deletion; one that no longer qualifies becomes ``skipped``
    rather than failing the request.

    Uses ``git branch -d`` (safe delete, which git refuses on an unmerged
    branch) for the normal path; ``-D`` only for the explicitly enabled
    unmerged case.
    """
    repo = get_repo(repo_path)
    if repo is None:
        raise BranchActionError(f"{repo_path} is not a git repository", 400)

    default_branch = detect_default_branch(repo)
    if default_branch is None:
        for info in response.branches:
            if info.status == "planned":
                info.status = "skipped"
                info.reason = NO_DEFAULT_BRANCH_MESSAGE
        response.dry_run = False
        response.message = NO_DEFAULT_BRANCH_MESSAGE
        return _finalise(response)

    default_ref = repo.heads[default_branch]
    current = _current_branch(repo)
    worktrees = worktree_branches(repo)
    unmerged_allowed = include_unmerged and config.allow_unmerged_delete
    live = {branch.name: branch for branch in repo.branches}
    deleted: list[BranchInfo] = []

    for info in response.branches:
        if info.status != "planned":
            continue

        branch = live.get(info.name)
        if branch is None:
            info.status = "skipped"
            info.reason = "branch no longer exists"
            continue

        fresh = _describe(repo, branch, default_ref)
        _classify(
            fresh,
            default_branch=default_branch,
            current=current,
            worktrees=worktrees,
            protected=list(config.protected_branches),
            stale_days=response.stale_days,
            unmerged_allowed=unmerged_allowed,
            has_commit_date=fresh.last_commit_at is not None,
        )
        if fresh.status != "planned":
            info.status = "skipped"
            info.reason = f"no longer eligible: {fresh.reason}"
            continue
        if fresh.last_commit_sha != info.last_commit_sha:
            info.status = "skipped"
            info.reason = "branch moved since the preview — not deleted"
            continue

        flag = "-d" if fresh.merged else "-D"
        try:
            repo.git.branch(flag, info.name)
        except Exception as exc:
            info.status = "failed"
            info.reason = f"{type(exc).__name__}: {exc}"
            logger.warning(
                "branch_delete_failed",
                extra={"repo": str(repo_path), "branch": info.name},
            )
            continue

        info.status = "deleted"
        info.reason = (
            f"deleted with 'git branch {flag}' — {info.reason}"
        )
        deleted.append(info)
        logger.info(
            "branch_deleted",
            extra={
                "repo": str(repo_path),
                "branch": info.name,
                "sha": info.last_commit_sha,
                "merged": fresh.merged,
            },
        )

    response.dry_run = False
    if deleted:
        response.message = (
            f"deleted {len(deleted)} branch(es); restore one with "
            f"'git -C {repo_path} branch <name> <last_commit_sha>' while the "
            "commit is still reachable"
        )
    else:
        response.message = "nothing was deleted"
    return _finalise(response)
