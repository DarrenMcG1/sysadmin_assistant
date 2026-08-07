"""Finding the repositories on disk.

A directory is a repository if it holds ``.git`` or a ``.project.yaml``.
The manifest counts on its own so a directory can declare itself before
it is a git repository, and so a repository that has been archived
without its history still appears.

A repository is never descended into.  A repo's vendored sub-repos are
its own business, and the alternative is the registry claiming identity
over directories the project owns.
"""

import logging
import re
from pathlib import Path

from sysadmin.registry.manifest import MANIFEST_NAME

logger = logging.getLogger(__name__)

DEFAULT_ROOT = Path("~/projects")

DEFAULT_DEPTH = 2

PRUNE_DIRS: frozenset[str] = frozenset({
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    ".next",
    ".nuxt",
    "target",
    ".godot",
})

BARE_REPO_SUFFIX = ".git"


def should_prune(name: str) -> bool:
    """Whether a directory named ``name`` is skipped outright.

    The ``.git`` suffix test is what keeps a mirror directory out of the
    estate: ``~/projects/.backups`` holds bare clones named
    ``<project>.git``, every one of which satisfies the repository test
    and would otherwise be discovered as a second copy of a real project.
    """
    return name in PRUNE_DIRS or name.endswith(BARE_REPO_SUFFIX)


def is_repository(path: Path) -> bool:
    """Whether ``path`` is a repository in its own right."""
    return (path / ".git").exists() or (path / MANIFEST_NAME).is_file()


def discover_repositories(
    root: Path, depth: int = DEFAULT_DEPTH
) -> list[Path]:
    """Every repository at or under ``root``, to ``depth`` levels below it.

    A directory with no repository markers is treated as a *category*
    (``apps/``, ``ml/``) and searched one level further.  Hidden
    directories are skipped entirely, which is what keeps ``.backups``
    and ``.cache`` out without needing either named in ``PRUNE_DIRS``.
    """
    found: list[Path] = []

    def walk(directory: Path, remaining: int) -> None:
        try:
            entries = sorted(directory.iterdir())
        except OSError as exc:
            logger.warning(
                "registry_scan_unreadable",
                extra={"path": str(directory), "error": str(exc)},
            )
            return

        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.name.startswith(".") or should_prune(entry.name):
                continue
            if is_repository(entry):
                found.append(entry)
            elif remaining > 1:
                walk(entry, remaining - 1)

    walk(root, max(depth, 1))
    return found


def derive_id(name: str) -> str:
    """A provisional id for a repository that has not declared one.

    Only ever used for reporting.  A derived id never enters the id map:
    ``SportsAnalyser`` derives ``sportsanalyser`` while its manifest may
    well declare ``sports-analyser``, so treating the two as the same
    thing would make references resolve to whichever ran first.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    return slug.strip("-") or "unnamed"


def derive_category(path: Path, root: Path) -> str | None:
    """The category directory a repository sits in, or None at the root."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return None
    parts = relative.parts
    return parts[0] if len(parts) > 1 else None


def relative_path(path: Path, root: Path) -> str:
    """``path`` expressed relative to ``root``, falling back to absolute."""
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except (OSError, ValueError):
        return str(path)


def under_archive(path: Path, root: Path) -> bool:
    """Whether ``path`` lives under ``<root>/archive/``."""
    try:
        relative = path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return bool(relative.parts) and relative.parts[0] == "archive"
