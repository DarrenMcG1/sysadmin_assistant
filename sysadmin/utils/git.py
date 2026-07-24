"""Git repository inspection helpers using GitPython."""

import logging
import os
from datetime import datetime, timedelta, timezone
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
    cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
    stale = []

    for branch in repo.branches:
        try:
            if repo.head.is_detached or branch != repo.active_branch:
                last_commit = branch.commit.committed_datetime
                if last_commit.tzinfo is None:
                    last_commit = last_commit.replace(tzinfo=timezone.utc)
                if last_commit < cutoff:
                    days_stale = (datetime.now(timezone.utc) - last_commit).days
                    stale.append({
                        "name": branch.name,
                        "last_commit": last_commit.isoformat(),
                        "days_stale": days_stale,
                    })
        except Exception:
            continue

    return stale


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
