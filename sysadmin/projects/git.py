"""Git repository inspection helpers using GitPython."""

import logging
import os
import re
from collections.abc import Collection, Sequence
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


#: Extension → language, for the estate's ``languages`` field.  A ranking
#: by file count, not a claim about proportions of anything.
LANGUAGE_BY_SUFFIX = {
    ".py": "python", ".ts": "typescript", ".tsx": "typescript",
    ".js": "javascript", ".jsx": "javascript", ".vue": "vue",
    ".gd": "gdscript", ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".rs": "rust", ".go": "go", ".sql": "sql", ".sh": "shell",
    ".java": "java", ".kt": "kotlin", ".cs": "csharp", ".rb": "ruby",
    ".php": "php", ".swift": "swift", ".dart": "dart", ".lua": "lua",
    ".html": "html", ".css": "css", ".scss": "css",
}

#: Directories never walked when counting languages — generated code and
#: vendored dependencies would otherwise decide the answer.
_LANGUAGE_SKIP = frozenset({
    ".git", "node_modules", "__pycache__", ".venv", "venv", "build",
    "dist", ".next", ".nuxt", "target", ".godot", "vendor", ".mypy_cache",
    ".pytest_cache", "site-packages", ".tox", "coverage",
})

_CI_PATHS = (".github/workflows", ".gitlab-ci.yml", ".circleci", "Jenkinsfile")
_TEST_DIRS = ("tests", "test", "spec", "__tests__")


def is_ignored_commit(
    commit: Any, patterns: Sequence[Any], shas: Collection[str]
) -> bool:
    """Whether a commit is estate housekeeping rather than work.

    Matched on the subject line only.  A body can quote anything,
    including the subject of the commit it is reverting, and a rule that
    reads the body would exclude commits that mention the bulk one.
    """
    if commit.hexsha in shas or commit.hexsha[:12] in shas:
        return True
    if not patterns:
        return False
    lines = str(commit.message).splitlines() if commit.message else []
    subject = lines[0].strip() if lines else ""
    return any(pattern.search(subject) for pattern in patterns)


def get_last_code_commit_date(
    repo: Repo,
    message_patterns: Sequence[str] = (),
    shas: Collection[str] = (),
    max_walk: int = 200,
) -> tuple[datetime | None, int]:
    """``(date, skipped)`` for the newest commit that changed real work.

    Returns the true last commit date when nothing is ignored, so a
    repository the rule does not touch costs one comparison and behaves
    exactly as before.  ``skipped`` is reported rather than swallowed:
    "this project's newest three commits were all estate housekeeping" is
    the kind of thing worth seeing once and never guessing at.
    """
    patterns = [re.compile(p, re.IGNORECASE) for p in message_patterns if p]
    ignored = {s.strip() for s in shas if s.strip()}
    skipped = 0

    try:
        for commit in repo.iter_commits(max_count=max_walk):
            if is_ignored_commit(commit, patterns, ignored):
                skipped += 1
                continue
            stamp = datetime.fromtimestamp(commit.committed_date, tz=UTC)
            return stamp, skipped
    except (ValueError, OSError):
        # Unborn HEAD, or a repository whose objects cannot be read.
        return None, skipped
    except Exception:  # noqa: BLE001 - GitPython raises broadly on bad refs
        return None, skipped

    return None, skipped


def detect_languages(path: Path, limit: int = 4) -> list[str]:
    """The languages present, most files first."""
    counts: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [
            d for d in dirnames if d not in _LANGUAGE_SKIP and not d.startswith(".")
        ]
        for name in filenames:
            language = LANGUAGE_BY_SUFFIX.get(Path(name).suffix.lower())
            if language:
                counts[language] = counts.get(language, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [language for language, _ in ranked[:limit]]


def detect_signals(path: Path) -> dict[str, bool]:
    """Whether each of the estate's documentation and tooling markers exists."""
    return {
        "claude_md": (path / "CLAUDE.md").is_file(),
        "readme": (path / "README.md").is_file(),
        "docs": (path / "docs").is_dir(),
        "tests": any((path / hint).is_dir() for hint in _TEST_DIRS),
        "ci": any((path / candidate).exists() for candidate in _CI_PATHS),
    }


def current_branch(repo: Repo) -> str | None:
    try:
        return repo.active_branch.name
    except (TypeError, ValueError):
        return None
    except Exception:  # noqa: BLE001 - detached HEAD, unborn branch
        return None


def commit_count(repo: Repo) -> int:
    try:
        return sum(1 for _ in repo.iter_commits())
    except Exception:  # noqa: BLE001 - unborn HEAD
        return 0


def is_dirty(repo: Repo) -> bool:
    try:
        return bool(repo.is_dirty(untracked_files=False))
    except Exception:  # noqa: BLE001
        return False


def remote_url(repo: Repo) -> str | None:
    try:
        return repo.remotes.origin.url
    except Exception:  # noqa: BLE001 - no origin
        return None
