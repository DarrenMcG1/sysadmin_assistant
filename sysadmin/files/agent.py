"""File Organiser Agent — evolved version of home_audit.py.

Runs all 8 filesystem checks as a scheduled agent with DB storage,
trending, delta reports, and quick-wins grouping.
"""

import asyncio
import hashlib
import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.files.recommendations import CACHE_DIR_TYPES

logger = logging.getLogger(__name__)

FILE_CATEGORIES = {
    "images": {
        "extensions": {
            ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff",
            ".svg", ".ico", ".heic", ".raw",
        },
        "expected_dirs": {"Pictures", "Images", "photos", "screenshots"},
    },
    "videos": {
        "extensions": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv", ".m4v"},
        "expected_dirs": {"Videos", "Movies"},
    },
    "documents": {
        "extensions": {
            ".pdf", ".docx", ".doc", ".odt", ".xlsx", ".xls", ".pptx",
            ".ppt", ".txt", ".rtf",
        },
        "expected_dirs": {"Documents", "Docs"},
    },
    "audio": {
        "extensions": {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac", ".wma"},
        "expected_dirs": {"Music", "Audio"},
    },
    # ``.pdf`` stays under "documents" for scanning; the organise action
    # re-routes individual PDFs to "books" via a filename/page-count
    # heuristic (see sysadmin/services/file_actions.classify_pdf).
    "books": {
        "extensions": {".epub", ".mobi", ".azw", ".azw3", ".cbz", ".cbr", ".fb2"},
        "expected_dirs": {"Books", "Library", "ebooks", "Calibre Library"},
    },
    "archives": {
        # ``.tar.gz`` and friends match on their final suffix
        "extensions": {
            ".zip", ".7z", ".rar", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".zst",
        },
        "expected_dirs": {"Archives", "Backups"},
    },
}

STALE_PROJECT_DIRS = {
    "node_modules", "__pycache__", ".venv", "venv", "target", "build",
    "dist", ".tox", ".pytest_cache",
}


def file_hash(filepath: Path, size: int) -> str | None:
    """MD5 of the first 1MB plus the file size — fast duplicate fingerprint.

    Shared with the duplicate-cleanup action
    (``sysadmin.files.actions``) so both group files identically.
    """
    try:
        hasher = hashlib.md5()
        hasher.update(str(size).encode())
        with open(filepath, "rb") as f:
            chunk = f.read(1024 * 1024)
            hasher.update(chunk)
        return hasher.hexdigest()
    except (PermissionError, OSError):
        return None


class FileOrganiserAgent(BaseAgent):
    """Filesystem audit agent with trending and DB storage."""

    name = "file_organiser"

    async def _execute(self, session) -> AgentResult:
        config = get_config()
        agent_config = config.agents.file_organiser

        # Run blocking scan in thread pool
        findings = await asyncio.to_thread(
            self._scan, agent_config
        )

        # Calculate totals
        total_reclaimable = findings.get("stale_project_dirs_total_bytes", 0) // (1024 * 1024)

        # Build the audit record
        audit = FilesystemAudit(
            scan_root=agent_config.scan_root,
            similar_folders_count=len(findings.get("similar_folders", [])),
            misplaced_files_count=sum(
                len(v) for v in findings.get("misplaced_files", {}).values()
            ),
            old_downloads_count=len(findings.get("old_downloads", [])),
            large_files_count=len(findings.get("large_files", [])),
            duplicate_groups_count=len(findings.get("duplicates", [])),
            empty_dirs_count=len(findings.get("empty_dirs", [])),
            stale_project_dirs_count=len(findings.get("stale_project_dirs", [])),
            stale_files_count=len(findings.get("stale_files", [])),
            total_reclaimable_mb=total_reclaimable,
            findings=self._serialise_findings(findings),
        )
        session.add(audit)

        alerts_raised = 0
        total_findings = (
            audit.similar_folders_count
            + audit.misplaced_files_count
            + audit.old_downloads_count
            + audit.large_files_count
            + audit.duplicate_groups_count
            + audit.empty_dirs_count
            + audit.stale_project_dirs_count
        )

        return AgentResult(
            findings_count=total_findings,
            alerts_raised=alerts_raised,
            details={
                "reclaimable_mb": total_reclaimable,
                "total_issues": total_findings,
            },
        )

    def _scan(self, agent_config) -> dict[str, Any]:
        """Blocking filesystem scan — runs all 8 checks."""
        scan_root = Path(agent_config.scan_root)
        stale_cutoff = datetime.now() - timedelta(days=agent_config.stale_days)
        downloads_cutoff = datetime.now() - timedelta(days=agent_config.downloads_stale_days)
        large_threshold = agent_config.large_file_mb * 1024 * 1024
        skip_dirs = set(agent_config.skip_dirs)
        similarity_threshold = agent_config.similarity_threshold

        all_dirs: list[Path] = []
        similar_folders: list[list[str]] = []
        misplaced_files: dict[str, list[str]] = defaultdict(list)
        stale_files: list[dict] = []
        old_downloads: list[dict] = []
        large_files: list[dict] = []
        empty_dirs: list[str] = []
        stale_project_dirs: list[dict] = []
        file_hashes: dict[str, list[str]] = defaultdict(list)
        # Every file in a hash group has the same size — the size is part
        # of the fingerprint (see ``file_hash``) — so one entry per group
        # is enough to price the reclaim.
        hash_sizes: dict[str, int] = {}
        stale_total_bytes = 0

        for root, dirs, files in os.walk(scan_root):
            root_path = Path(root)

            # Filter directories
            dirs[:] = [
                d for d in dirs
                if d not in skip_dirs and not d.startswith(".")
            ]

            for d in dirs:
                dirpath = root_path / d
                all_dirs.append(dirpath)

                # Empty dir check
                try:
                    if not any(dirpath.iterdir()):
                        empty_dirs.append(str(dirpath))
                except PermissionError:
                    pass

                # Stale project dir check
                if d in STALE_PROJECT_DIRS:
                    try:
                        size = sum(
                            f.stat().st_size
                            for f in dirpath.rglob("*")
                            if f.is_file()
                        )
                        stale_project_dirs.append({
                            "path": str(dirpath),
                            "size_mb": round(size / (1024 * 1024), 1),
                            "type": d,
                        })
                        stale_total_bytes += size
                    except (PermissionError, OSError):
                        pass

            for f in files:
                if f.startswith("."):
                    continue
                filepath = root_path / f
                if not filepath.is_file():
                    continue

                try:
                    stat = filepath.stat()
                except (PermissionError, OSError):
                    continue

                ext = filepath.suffix.lower()

                # Misplaced file check
                try:
                    rel_parts = filepath.relative_to(scan_root).parts
                    for category, cat_config in FILE_CATEGORIES.items():
                        if ext in cat_config["extensions"]:
                            in_expected = any(
                                part in cat_config["expected_dirs"] for part in rel_parts
                            )
                            if not in_expected:
                                misplaced_files[category].append(str(filepath))
                            break
                except ValueError:
                    pass

                # Stale file check
                mtime = datetime.fromtimestamp(stat.st_mtime)
                if mtime < stale_cutoff:
                    stale_files.append({
                        "path": str(filepath),
                        "days_old": (datetime.now() - mtime).days,
                    })

                # Old downloads check
                try:
                    rel = filepath.relative_to(scan_root)
                    if rel.parts and rel.parts[0].lower() == "downloads":
                        if mtime < downloads_cutoff:
                            old_downloads.append({
                                "path": str(filepath),
                                "days_old": (datetime.now() - mtime).days,
                                "size_mb": round(stat.st_size / (1024 * 1024), 1),
                            })
                except ValueError:
                    pass

                # Large file check
                if stat.st_size >= large_threshold:
                    large_files.append({
                        "path": str(filepath),
                        "size_mb": round(stat.st_size / (1024 * 1024), 1),
                    })

                # Duplicate check (files > 1KB)
                if stat.st_size >= 1024:
                    file_hash = self._get_file_hash(filepath, stat.st_size)
                    if file_hash:
                        file_hashes[file_hash].append(str(filepath))
                        hash_sizes[file_hash] = stat.st_size

        # Similar folders
        similar_folders = self._find_similar_folders(
            all_dirs, scan_root, similarity_threshold
        )

        # Duplicates.  ``reclaimable_mb`` prices the group at "delete all
        # but one copy" — the same rule ``/api/files/clean/duplicates``
        # applies — so the recommendations can rank on real megabytes
        # rather than on a group count.
        duplicates: list[dict[str, Any]] = [
            {
                "hash": h,
                "files": paths,
                "count": len(paths),
                "size_mb": round(hash_sizes.get(h, 0) / (1024 * 1024), 1),
                "reclaimable_mb": round(
                    hash_sizes.get(h, 0) * (len(paths) - 1) / (1024 * 1024), 1
                ),
            }
            for h, paths in file_hashes.items()
            if len(paths) > 1
        ]

        return {
            "similar_folders": similar_folders,
            "misplaced_files": dict(misplaced_files),
            "stale_files": stale_files[:500],
            # Both lists are truncated before storage, so sort by size
            # first: an arbitrary 50 of 400 duplicate groups would hide
            # exactly the ones worth acting on.
            "old_downloads": sorted(old_downloads, key=lambda x: -x["size_mb"]),
            "large_files": sorted(large_files, key=lambda x: -x["size_mb"]),
            "duplicates": sorted(
                duplicates, key=lambda x: -float(x["reclaimable_mb"])
            )[:200],
            "empty_dirs": empty_dirs[:200],
            "stale_project_dirs": sorted(stale_project_dirs, key=lambda x: -x["size_mb"]),
            "stale_project_dirs_total_bytes": stale_total_bytes,
        }

    def _get_file_hash(self, filepath: Path, size: int) -> str | None:
        """MD5 of first 1MB + file size for fast duplicate detection."""
        return file_hash(filepath, size)

    def _find_similar_folders(
        self,
        dirs: list[Path],
        scan_root: Path,
        threshold: float,
    ) -> list[list[str]]:
        """Find folders with similar names using normalisation and fuzzy matching."""
        normalised: dict[str, list[Path]] = defaultdict(list)
        for d in dirs:
            norm = re.sub(r"[\s_-]+", "", d.name.lower())
            normalised[norm].append(d)

        similar = []

        # Exact normalised matches
        for norm, dirs_group in normalised.items():
            if len(dirs_group) > 1:
                similar.append([str(d) for d in dirs_group])

        # Fuzzy matches (only check first 500 dirs to avoid O(n^2) explosion)
        sample = dirs[:500]
        seen_pairs: set[tuple[str, str]] = set()
        for i, dir1 in enumerate(sample):
            for dir2 in sample[i + 1:]:
                if dir1.parent == dir2.parent:
                    continue
                norm1 = re.sub(r"[\s_-]+", "", dir1.name.lower())
                norm2 = re.sub(r"[\s_-]+", "", dir2.name.lower())
                if norm1 == norm2:
                    continue
                ratio = SequenceMatcher(None, norm1, norm2).ratio()
                if ratio >= threshold:
                    first, second = sorted([str(dir1), str(dir2)])
                    pair = (first, second)
                    if pair not in seen_pairs:
                        seen_pairs.add(pair)
                        similar.append([str(dir1), str(dir2)])

        return similar[:100]

    def _serialise_findings(self, findings: dict) -> dict:
        """Prepare findings for JSONB storage — truncate large lists."""
        return {
            "similar_folders": findings.get("similar_folders", [])[:50],
            "misplaced_files": {
                cat: paths[:50] for cat, paths in findings.get("misplaced_files", {}).items()
            },
            "old_downloads": findings.get("old_downloads", [])[:100],
            "large_files": findings.get("large_files", [])[:50],
            "duplicates": findings.get("duplicates", [])[:50],
            "empty_dirs": findings.get("empty_dirs", [])[:100],
            "stale_project_dirs": findings.get("stale_project_dirs", [])[:50],
            "stale_files_count": len(findings.get("stale_files", [])),
            "quick_wins": self._identify_quick_wins(findings),
        }

    def _identify_quick_wins(self, findings: dict) -> dict:
        """Group findings into quick wins vs needs-review categories.

        ``CACHE_DIR_TYPES`` is shared with
        :mod:`sysadmin.files.recommendations` so the quick-wins
        count and the "delete stale caches" advice can never disagree
        about what counts as a cache.
        """
        quick_wins = {
            "empty_dirs": len(findings.get("empty_dirs", [])),
            "stale_caches": sum(
                1 for d in findings.get("stale_project_dirs", [])
                if d.get("type") in CACHE_DIR_TYPES
            ),
            "stale_cache_mb": sum(
                d.get("size_mb", 0) for d in findings.get("stale_project_dirs", [])
                if d.get("type") in CACHE_DIR_TYPES
            ),
        }
        return quick_wins
