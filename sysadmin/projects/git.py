"""Git repository inspection helpers using GitPython."""

import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from git import InvalidGitRepositoryError, Repo
from git.exc import NoSuchPathError

logger = logging.getLogger(__name__)


def get_repo(path: Path) -> Repo | None:
    """Open a git repo at the given path, or None if not a git repo."""
    try:
        return Repo(path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        # Expected: path isn't a git repo (or doesn't exist) — stay silent.
        return None
    except Exception:
        logger.warning("unexpected error opening repo at %s", path, exc_info=True)
        return None


def get_last_commit_date(repo: Repo) -> datetime | None:
    """Get the date of the most recent commit across all local branches.

    Falls back to the HEAD commit for detached-HEAD or branchless repos.
    Returns None if the repo has no commits at all.
    """
    dates: list[datetime] = []
    try:
        for branch in repo.branches:
            try:
                dates.append(branch.commit.committed_datetime)
            except Exception:
                continue
        if dates:
            return max(dates)
        # No usable branches — detached HEAD or unborn branch.
        return repo.head.commit.committed_datetime
    except Exception:
        return None


def get_branches(repo: Repo) -> list[dict[str, Any]]:
    """Get all local branches with their last commit date."""
    branches = []
    for branch in repo.branches:
        try:
            last_commit = branch.commit.committed_datetime
            branches.append({
                "name": branch.name,
                "last_commit": last_commit.isoformat(),
                "is_active": branch == repo.active_branch if not repo.head.is_detached else False,
            })
        except Exception:
            branches.append({
                "name": branch.name,
                "last_commit": None,
                "is_active": False,
            })
    return branches


def get_stale_branches(repo: Repo, stale_days: int = 30) -> list[dict[str, Any]]:
    """Get branches with no commits in the last N days."""
    cutoff = datetime.now(UTC) - timedelta(days=stale_days)
    stale = []

    for branch in repo.branches:
        try:
            if repo.head.is_detached or branch != repo.active_branch:
                last_commit = branch.commit.committed_datetime
                if last_commit.tzinfo is None:
                    last_commit = last_commit.replace(tzinfo=UTC)
                if last_commit < cutoff:
                    days_stale = (datetime.now(UTC) - last_commit).days
                    stale.append({
                        "name": branch.name,
                        "last_commit": last_commit.isoformat(),
                        "days_stale": days_stale,
                    })
        except Exception:
            continue

    return stale


# Names conventionally used for a repository's default branch, in the
# order they are tried when the remote does not advertise one.
DEFAULT_BRANCH_CANDIDATES = ("main", "master", "trunk", "default")


def detect_default_branch(repo: Repo) -> str | None:
    """Work out the repo's default branch, or None when it is ambiguous.

    Never assumes "main".  Tried in order:

    1. the remote's advertised HEAD (``refs/remotes/<remote>/HEAD``),
    2. ``init.defaultBranch`` from git config,
    3. the conventional names in :data:`DEFAULT_BRANCH_CANDIDATES`,
    4. the sole local branch, if there is exactly one.

    Returning None is a meaningful answer: callers that delete branches
    must refuse to act rather than guess, since "merged" is defined
    entirely by this branch.
    """
    try:
        local = {branch.name for branch in repo.branches}
    except Exception:
        return None
    if not local:
        return None

    for remote in getattr(repo, "remotes", []):
        prefix = f"refs/remotes/{remote.name}/"
        try:
            ref = repo.git.symbolic_ref(f"{prefix}HEAD").strip()
        except Exception:
            continue
        if ref.startswith(prefix):
            candidate = ref[len(prefix):]
            if candidate in local:
                return candidate

    try:
        configured = repo.git.config("--get", "init.defaultBranch").strip()
    except Exception:
        configured = ""
    if configured in local:
        return configured

    for candidate in DEFAULT_BRANCH_CANDIDATES:
        if candidate in local:
            return candidate

    if len(local) == 1:
        return next(iter(local))
    return None


def worktree_branches(repo: Repo) -> set[str]:
    """Branch names checked out in *any* worktree, main one included.

    ``git worktree list --porcelain`` prints a ``branch refs/heads/x``
    line per worktree with an attached branch.  Deleting one of these is
    refused by git anyway, but they are filtered out up front so the
    manifest never promises a deletion that cannot happen.
    """
    names: set[str] = set()
    try:
        output = repo.git.worktree("list", "--porcelain")
    except Exception:
        return names
    for line in output.splitlines():
        if line.startswith("branch "):
            ref = line[len("branch "):].strip()
            if ref.startswith("refs/heads/"):
                names.add(ref[len("refs/heads/"):])
    return names


def is_merged_into(repo: Repo, branch: Any, target: Any) -> bool:
    """Is every commit on ``branch`` reachable from ``target``?

    Asks git (``merge-base --is-ancestor`` under the hood) rather than
    inferring anything from dates.  Any error answers False — the caller
    treats "unknown" as "not merged", which is the safe direction.
    """
    try:
        return bool(repo.is_ancestor(branch.commit, target.commit))
    except Exception:
        return False


def upstream_state(repo: Repo, branch: Any) -> tuple[str | None, int | None]:
    """Return ``(upstream_ref_name, commits_ahead)`` for a local branch.

    ``(None, 0)`` — the branch tracks nothing.
    ``(name, n)`` — it tracks ``name`` and has ``n`` commits the upstream
    does not.
    ``(name, None)`` — it claims an upstream whose state cannot be read
    (e.g. the remote-tracking ref is gone).  Ambiguous: callers must not
    delete it.
    """
    try:
        tracking = branch.tracking_branch()
    except Exception:
        return None, None
    if tracking is None:
        return None, 0
    name = getattr(tracking, "name", str(tracking))
    try:
        counts = repo.git.rev_list(
            "--left-right", "--count", f"{tracking.path}...{branch.path}"
        )
        _behind, ahead = counts.split()
        return name, int(ahead)
    except Exception:
        return name, None


def has_remote(repo: Repo) -> bool:
    """Check if the repo has at least one remote configured."""
    try:
        return len(repo.remotes) > 0
    except Exception:
        return False


_SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", ".next", ".nuxt", "coverage",
    ".tox", ".mypy_cache", ".pytest_cache", "site-packages",
    ".eggs", "vendor", "bower_components",
}


def get_repo_size_mb(path: Path) -> int:
    """Estimate total size of a project's own source files in MB."""
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
            for name in files:
                try:
                    total += (Path(root) / name).stat().st_size
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total // (1024 * 1024)
