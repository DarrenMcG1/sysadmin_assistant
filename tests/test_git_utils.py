"""Tests for git repository inspection helpers (sysadmin.utils.git).

Uses real throwaway repos created with GitPython — no mocking of git
itself, so branch iteration behaviour is exercised for real.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
from git import Repo

from sysadmin.utils.git import get_last_commit_date, get_repo

OLD_DATE = "2026-01-01 12:00:00 +0000"
NEW_DATE = "2026-06-15 09:30:00 +0000"


def _init_repo(path: Path) -> Repo:
    """Initialise a repo with a test identity configured."""
    repo = Repo.init(path)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test User")
        cw.set_value("user", "email", "test@example.com")
    return repo


def _commit(repo: Repo, filename: str, date: str):
    """Add a file and commit it with a fixed date."""
    file_path = Path(repo.working_dir) / filename
    file_path.write_text("content\n")
    repo.index.add([filename])
    return repo.index.commit(
        f"add {filename}", commit_date=date, author_date=date
    )


class TestGetLastCommitDate:
    """get_last_commit_date should consider all local branches."""

    def test_single_branch(self, tmp_path):
        repo = _init_repo(tmp_path)
        commit = _commit(repo, "a.txt", OLD_DATE)

        assert get_last_commit_date(repo) == commit.committed_datetime

    def test_newest_commit_on_non_head_branch(self, tmp_path):
        """Regression for SNAG-AGENT-001: HEAD-only walk missed newer
        commits sitting on other branches."""
        repo = _init_repo(tmp_path)
        _commit(repo, "a.txt", OLD_DATE)
        default_branch = repo.active_branch

        feature = repo.create_head("feature")
        feature.checkout()
        newer = _commit(repo, "b.txt", NEW_DATE)

        # Return to the default branch so HEAD points at the old commit
        default_branch.checkout()

        result = get_last_commit_date(repo)
        assert result == newer.committed_datetime

    def test_detached_head_no_branches_falls_back_to_head(self, tmp_path):
        repo = _init_repo(tmp_path)
        commit = _commit(repo, "a.txt", OLD_DATE)

        # Detach HEAD, then delete the branch so repo.branches is empty
        branch_name = repo.active_branch.name
        repo.git.checkout(commit.hexsha)
        repo.delete_head(branch_name, force=True)

        assert list(repo.branches) == []
        assert get_last_commit_date(repo) == commit.committed_datetime

    def test_empty_repo_returns_none(self, tmp_path):
        repo = _init_repo(tmp_path)

        assert get_last_commit_date(repo) is None


class TestGetRepo:
    """get_repo should be silent for expected cases, loud for surprises."""

    def test_valid_repo(self, tmp_path):
        _init_repo(tmp_path)

        repo = get_repo(tmp_path)
        assert repo is not None
        assert Path(repo.working_dir) == tmp_path

    def test_non_repo_directory_returns_none(self, tmp_path):
        assert get_repo(tmp_path) is None

    def test_missing_path_returns_none(self, tmp_path):
        assert get_repo(tmp_path / "does-not-exist") is None

    def test_unexpected_error_logged_and_returns_none(self, tmp_path, caplog):
        with (
            patch("sysadmin.utils.git.Repo", side_effect=RuntimeError("boom")),
            caplog.at_level(logging.WARNING, logger="sysadmin.utils.git"),
        ):
            assert get_repo(tmp_path) is None

        assert any(
            "unexpected error opening repo" in record.message
            for record in caplog.records
        )
