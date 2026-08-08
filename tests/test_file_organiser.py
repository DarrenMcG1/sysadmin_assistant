"""Tests for the File Organiser agent — filesystem scanning with tmpdir fixtures.

Verifies all 8 finding types:
1. Similar folders
2. Misplaced files
3. Stale files
4. Old downloads
5. Large files
6. Duplicate files
7. Empty directories
8. Stale project directories
"""

import os
import time
from pathlib import Path

import pytest

from sysadmin.core.config import FileOrganiserConfig
from sysadmin.files.agent import FileOrganiserAgent


@pytest.fixture
def agent():
    return FileOrganiserAgent()


@pytest.fixture
def scan_config(tmp_path):
    return FileOrganiserConfig(
        scan_root=str(tmp_path),
        stale_days=30,
        downloads_stale_days=7,
        large_file_mb=1,  # 1MB threshold for easier testing
        similarity_threshold=0.75,
        skip_dirs=[".git", "node_modules", "__pycache__"],
    )


def _set_mtime_days_ago(path: Path, days: int):
    """Set file/dir modification time to N days ago."""
    old = time.time() - (days * 86400)
    os.utime(path, (old, old))


# ---------------------------------------------------------------------------
# Empty directories
# ---------------------------------------------------------------------------


class TestEmptyDirs:
    def test_detects_empty_dir(self, agent, scan_config, tmp_path):
        (tmp_path / "empty_folder").mkdir()
        findings = agent._scan(scan_config)
        assert len(findings["empty_dirs"]) >= 1
        assert any("empty_folder" in d for d in findings["empty_dirs"])

    def test_non_empty_dir_not_flagged(self, agent, scan_config, tmp_path):
        d = tmp_path / "has_content"
        d.mkdir()
        (d / "file.txt").write_text("content")
        findings = agent._scan(scan_config)
        assert not any("has_content" in d for d in findings["empty_dirs"])


# ---------------------------------------------------------------------------
# Large files
# ---------------------------------------------------------------------------


class TestLargeFiles:
    def test_detects_large_file(self, agent, scan_config, tmp_path):
        big = tmp_path / "huge.bin"
        big.write_bytes(b"\x00" * (2 * 1024 * 1024))  # 2MB > 1MB threshold
        findings = agent._scan(scan_config)
        assert len(findings["large_files"]) >= 1
        assert any("huge.bin" in f["path"] for f in findings["large_files"])

    def test_small_file_not_flagged(self, agent, scan_config, tmp_path):
        small = tmp_path / "tiny.txt"
        small.write_text("hello")
        findings = agent._scan(scan_config)
        assert not any("tiny.txt" in f["path"] for f in findings["large_files"])


# ---------------------------------------------------------------------------
# Stale files
# ---------------------------------------------------------------------------


class TestStaleFiles:
    def test_detects_stale_file(self, agent, scan_config, tmp_path):
        stale = tmp_path / "old_report.txt"
        stale.write_text("ancient")
        _set_mtime_days_ago(stale, 60)  # 60 > 30 day threshold
        findings = agent._scan(scan_config)
        assert len(findings["stale_files"]) >= 1

    def test_recent_file_not_flagged(self, agent, scan_config, tmp_path):
        recent = tmp_path / "fresh.txt"
        recent.write_text("new")
        findings = agent._scan(scan_config)
        stale_paths = [f["path"] for f in findings["stale_files"]]
        assert not any("fresh.txt" in p for p in stale_paths)


# ---------------------------------------------------------------------------
# Old downloads
# ---------------------------------------------------------------------------


class TestOldDownloads:
    def test_detects_old_download(self, agent, scan_config, tmp_path):
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        old_file = downloads / "installer.exe"
        old_file.write_text("data")
        _set_mtime_days_ago(old_file, 14)  # 14 > 7 day threshold

        findings = agent._scan(scan_config)
        assert len(findings["old_downloads"]) >= 1

    def test_recent_download_not_flagged(self, agent, scan_config, tmp_path):
        downloads = tmp_path / "Downloads"
        downloads.mkdir()
        new_file = downloads / "fresh.zip"
        new_file.write_text("data")

        findings = agent._scan(scan_config)
        paths = [f["path"] for f in findings["old_downloads"]]
        assert not any("fresh.zip" in p for p in paths)


# ---------------------------------------------------------------------------
# Misplaced files
# ---------------------------------------------------------------------------


class TestMisplacedFiles:
    def test_image_outside_pictures(self, agent, scan_config, tmp_path):
        # Image in root, not in Pictures/
        img = tmp_path / "photo.jpg"
        img.write_bytes(b"\xff\xd8")  # JPEG magic bytes
        findings = agent._scan(scan_config)
        misplaced_images = findings.get("misplaced_files", {}).get("images", [])
        assert any("photo.jpg" in p for p in misplaced_images)

    def test_image_in_pictures_not_flagged(self, agent, scan_config, tmp_path):
        pics = tmp_path / "Pictures"
        pics.mkdir()
        img = pics / "photo.jpg"
        img.write_bytes(b"\xff\xd8")
        findings = agent._scan(scan_config)
        misplaced_images = findings.get("misplaced_files", {}).get("images", [])
        assert not any("photo.jpg" in p for p in misplaced_images)

    def test_document_outside_documents(self, agent, scan_config, tmp_path):
        doc = tmp_path / "report.pdf"
        doc.write_bytes(b"%PDF")
        findings = agent._scan(scan_config)
        misplaced_docs = findings.get("misplaced_files", {}).get("documents", [])
        assert any("report.pdf" in p for p in misplaced_docs)


# ---------------------------------------------------------------------------
# Duplicate files
# ---------------------------------------------------------------------------


class TestDuplicates:
    def test_detects_duplicates(self, agent, scan_config, tmp_path):
        content = b"x" * 2048  # >1KB to trigger duplicate check
        d1 = tmp_path / "dir1"
        d2 = tmp_path / "dir2"
        d1.mkdir()
        d2.mkdir()
        (d1 / "file.dat").write_bytes(content)
        (d2 / "copy.dat").write_bytes(content)

        findings = agent._scan(scan_config)
        assert len(findings["duplicates"]) >= 1
        dup_group = findings["duplicates"][0]
        assert dup_group["count"] == 2

    def test_different_files_not_duplicates(self, agent, scan_config, tmp_path):
        d1 = tmp_path / "a"
        d2 = tmp_path / "b"
        d1.mkdir()
        d2.mkdir()
        (d1 / "file1.dat").write_bytes(b"x" * 2048)
        (d2 / "file2.dat").write_bytes(b"y" * 2048)

        findings = agent._scan(scan_config)
        assert len(findings["duplicates"]) == 0


# ---------------------------------------------------------------------------
# Stale project directories
# ---------------------------------------------------------------------------


class TestStaleProjectDirs:
    def test_detects_pycache(self, agent, tmp_path):
        # Use config that doesn't skip __pycache__
        config = FileOrganiserConfig(
            scan_root=str(tmp_path),
            stale_days=180,
            downloads_stale_days=30,
            large_file_mb=100,
            similarity_threshold=0.75,
            skip_dirs=[".git"],  # Don't skip __pycache__ so it gets scanned
        )
        cache = tmp_path / "project" / "__pycache__"
        cache.mkdir(parents=True)
        (cache / "module.pyc").write_bytes(b"\x00" * 100)

        findings = agent._scan(config)
        assert len(findings["stale_project_dirs"]) >= 1
        assert any(d["type"] == "__pycache__" for d in findings["stale_project_dirs"])

    def test_detects_venv(self, agent, tmp_path):
        """Detect .venv-style dirs that don't start with '.' (venv)."""
        config = FileOrganiserConfig(
            scan_root=str(tmp_path),
            stale_days=180,
            downloads_stale_days=30,
            large_file_mb=100,
            similarity_threshold=0.75,
            skip_dirs=[".git"],
        )
        venv = tmp_path / "project" / "venv"
        venv.mkdir(parents=True)
        (venv / "pyvenv.cfg").write_text("home = /usr/bin")

        findings = agent._scan(config)
        assert any(d["type"] == "venv" for d in findings["stale_project_dirs"])

    def test_dot_prefixed_stale_dirs_skipped(self, agent, tmp_path):
        """Dirs starting with '.' (e.g. .pytest_cache) are filtered by os.walk."""
        config = FileOrganiserConfig(
            scan_root=str(tmp_path),
            stale_days=180,
            downloads_stale_days=30,
            large_file_mb=100,
            similarity_threshold=0.75,
            skip_dirs=[".git"],
        )
        cache = tmp_path / "project" / ".pytest_cache"
        cache.mkdir(parents=True)
        (cache / "data.json").write_text("{}")

        findings = agent._scan(config)
        # .pytest_cache starts with '.' so it's filtered out by the hidden-dir check
        assert not any(d["type"] == ".pytest_cache" for d in findings["stale_project_dirs"])


# ---------------------------------------------------------------------------
# Similar folders
# ---------------------------------------------------------------------------


class TestSimilarFolders:
    def test_exact_normalised_match(self, agent, tmp_path):
        (tmp_path / "my_project").mkdir()
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "my-project").mkdir()

        dirs = [tmp_path / "my_project", tmp_path / "subdir" / "my-project"]
        result = agent._find_similar_folders(dirs, tmp_path, 0.75)
        assert len(result) >= 1

    def test_no_similarity_for_distinct_names(self, agent, tmp_path):
        dirs = [tmp_path / "alpha", tmp_path / "beta"]
        for d in dirs:
            d.mkdir()
        result = agent._find_similar_folders(dirs, tmp_path, 0.75)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# Serialisation and quick wins
# ---------------------------------------------------------------------------


class TestSerialisation:
    def test_serialise_truncates(self, agent):
        findings = {
            "similar_folders": [["a", "b"]] * 100,
            "misplaced_files": {"images": ["img"] * 100},
            "old_downloads": [{"path": "x"}] * 200,
            "large_files": [{"path": "x", "size_mb": 1}] * 100,
            "duplicates": [{"hash": "x", "files": [], "count": 0}] * 100,
            "empty_dirs": ["dir"] * 300,
            "stale_project_dirs": [{"path": "x", "size_mb": 1, "type": "__pycache__"}] * 100,
            "stale_files": [{"path": "x"}] * 1000,
        }
        serialised = agent._serialise_findings(findings)
        assert len(serialised["similar_folders"]) <= 50
        assert len(serialised["misplaced_files"]["images"]) <= 50
        assert len(serialised["empty_dirs"]) <= 100

    def test_quick_wins_counts_caches(self, agent):
        findings = {
            "empty_dirs": ["a", "b"],
            "stale_project_dirs": [
                {"type": "__pycache__", "size_mb": 5},
                {"type": ".pytest_cache", "size_mb": 2},
                {"type": "node_modules", "size_mb": 500},
            ],
        }
        qw = agent._identify_quick_wins(findings)
        assert qw["empty_dirs"] == 2
        assert qw["stale_caches"] == 2  # __pycache__ + .pytest_cache
        assert qw["stale_cache_mb"] == 7
