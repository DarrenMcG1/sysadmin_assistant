"""Git repository inspection helpers using GitPython."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from git import InvalidGitRepositoryError, Repo
from git.exc import GitCommandError

logger = logging.getLogger(__name__)


def get_repo(path: Path) -> Repo | None:
    """Open a git repo at the given path, or None if not a git repo."""
    try:
        return Repo(path)
    except (InvalidGitRepositoryError, Exception):
        return None


def get_last_commit_date(repo: Repo) -> datetime | None:
    """Get the date of the most recent commit on any branch."""
    try:
        if repo.head.is_detached:
            return repo.head.commit.committed_datetime
        commits = list(repo.iter_commits(max_count=1))
        if commits:
            return commits[0].committed_datetime
    except Exception:
        pass
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


def count_stale_branches(repo: Repo, stale_days: int = 30) -> int:
    """Count branches that haven't had commits in N days."""
    return len(get_stale_branches(repo, stale_days))


def get_repo_size_mb(path: Path) -> int:
    """Estimate total size of a project directory in MB (excluding .git)."""
    total = 0
    try:
        for f in path.rglob("*"):
            if ".git" in f.parts:
                continue
            if f.is_file():
                try:
                    total += f.stat().st_size
                except (PermissionError, OSError):
                    continue
    except (PermissionError, OSError):
        pass
    return total // (1024 * 1024)
