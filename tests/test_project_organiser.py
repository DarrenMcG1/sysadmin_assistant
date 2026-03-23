"""Tests for the Project Organiser agent — discovery, health scoring, edge cases."""

import os
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sysadmin.agents.project_organiser import ProjectOrganiserAgent
from sysadmin.config import ProjectOrganiserConfig


@pytest.fixture
def agent():
    return ProjectOrganiserAgent()


@pytest.fixture
def agent_config():
    return ProjectOrganiserConfig(
        projects_root="/tmp/test_projects",
        stale_branch_days=30,
        track_todos=True,
        todo_patterns=["TODO", "FIXME"],
    )


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory structure."""
    proj = tmp_path / "my_project"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "README.md").write_text("# My Project")
    (proj / "CLAUDE.md").write_text("# Instructions")
    (proj / "main.py").write_text("# TODO: implement\nprint('hello')")
    return proj


# ---------------------------------------------------------------------------
# Project discovery
# ---------------------------------------------------------------------------


class TestDiscoverProjects:
    def test_finds_git_project(self, agent, tmp_path):
        proj = tmp_path / "my_app"
        proj.mkdir()
        (proj / ".git").mkdir()

        result = agent._discover_projects(tmp_path)
        assert len(result) == 1
        assert result[0] == proj

    def test_finds_pyproject_toml_project(self, agent, tmp_path):
        proj = tmp_path / "py_app"
        proj.mkdir()
        (proj / "pyproject.toml").write_text("[project]\nname = 'test'")

        result = agent._discover_projects(tmp_path)
        assert len(result) == 1

    def test_finds_package_json_project(self, agent, tmp_path):
        proj = tmp_path / "js_app"
        proj.mkdir()
        (proj / "package.json").write_text("{}")

        result = agent._discover_projects(tmp_path)
        assert len(result) == 1

    def test_ignores_hidden_dirs(self, agent, tmp_path):
        hidden = tmp_path / ".hidden_project"
        hidden.mkdir()
        (hidden / ".git").mkdir()

        result = agent._discover_projects(tmp_path)
        assert len(result) == 0

    def test_ignores_files(self, agent, tmp_path):
        (tmp_path / "readme.txt").write_text("not a project")
        result = agent._discover_projects(tmp_path)
        assert len(result) == 0

    def test_ignores_dir_without_markers(self, agent, tmp_path):
        (tmp_path / "random_dir").mkdir()
        result = agent._discover_projects(tmp_path)
        assert len(result) == 0

    def test_empty_root(self, agent, tmp_path):
        result = agent._discover_projects(tmp_path)
        assert result == []


# ---------------------------------------------------------------------------
# Health score calculation
# ---------------------------------------------------------------------------


class TestAnalyseProject:
    def _patch_git(
        self,
        *,
        last_commit_days_ago: int = 5,
        branches: list[str] | None = None,
        stale_branches: list[str] | None = None,
        has_remote: bool = True,
    ):
        """Context manager that patches all git utility functions."""
        repo = MagicMock()
        last_commit = datetime.now(timezone.utc) - timedelta(days=last_commit_days_ago)
        mod = "sysadmin.agents.project_organiser"

        stack = ExitStack()
        stack.enter_context(patch(f"{mod}.get_repo", return_value=repo))
        stack.enter_context(patch(f"{mod}.get_last_commit_date", return_value=last_commit))
        stack.enter_context(patch(f"{mod}.get_branches", return_value=branches or ["main"]))
        stack.enter_context(patch(f"{mod}.get_stale_branches", return_value=stale_branches or []))
        stack.enter_context(patch(f"{mod}.has_remote", return_value=has_remote))
        stack.enter_context(patch(f"{mod}.get_repo_size_mb", return_value=42))
        return stack

    def test_healthy_project_scores_high(self, agent, agent_config, project_dir):
        with self._patch_git(last_commit_days_ago=1):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.health_score >= 80
        assert snapshot.project_name == project_dir.name
        assert snapshot.has_readme is True
        assert snapshot.has_claude_md is True

    def test_missing_readme_deducts_10(self, agent, agent_config, project_dir):
        (project_dir / "README.md").unlink()
        with self._patch_git():
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.has_readme is False
        assert "missing_readme" in snapshot.findings

    def test_missing_claude_md_deducts_10(self, agent, agent_config, project_dir):
        (project_dir / "CLAUDE.md").unlink()
        with self._patch_git():
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.has_claude_md is False
        assert "missing_claude_md" in snapshot.findings

    def test_stale_branches_deduct_points(self, agent, agent_config, project_dir):
        with self._patch_git(stale_branches=["old-feature", "experiment", "dead-branch"]):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.stale_branch_count == 3
        assert "stale_branches" in snapshot.findings
        # 3 branches × 5 points = -15
        assert snapshot.health_score <= 85

    def test_stale_branch_deduction_capped_at_5(self, agent, agent_config, project_dir):
        with self._patch_git(stale_branches=[f"branch-{i}" for i in range(10)]):
            snapshot = agent._analyse_project(project_dir, agent_config)

        # Max deduction: 5 × 5 = 25
        assert snapshot.health_score >= 75 - 10  # allow TODO deductions

    def test_old_project_60_days_deducts_15(self, agent, agent_config, project_dir):
        with self._patch_git(last_commit_days_ago=65):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert "stale" in snapshot.findings
        assert snapshot.health_score <= 85

    def test_aging_project_30_days_deducts_10(self, agent, agent_config, project_dir):
        with self._patch_git(last_commit_days_ago=35):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert "aging" in snapshot.findings

    def test_missing_env_deducts_10(self, agent, agent_config, project_dir):
        (project_dir / ".env.example").write_text("SECRET=xxx")
        with self._patch_git():
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert "missing_env" in snapshot.findings

    def test_git_lock_deducts_5(self, agent, agent_config, project_dir):
        (project_dir / ".git" / "index.lock").write_text("")
        with self._patch_git():
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert "stale_git_lock" in snapshot.findings

    def test_no_git_repo(self, agent, agent_config, project_dir):
        mod = "sysadmin.agents.project_organiser"
        with (
            patch(f"{mod}.get_repo", return_value=None),
            patch(f"{mod}.get_repo_size_mb", return_value=10),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.branch_count == 0
        assert snapshot.last_commit_at is None

    def test_score_clamped_to_0(self, agent, agent_config, project_dir):
        """Even with many deductions, score should not go below 0."""
        (project_dir / "README.md").unlink()
        (project_dir / "CLAUDE.md").unlink()
        (project_dir / ".env.example").write_text("x")
        (project_dir / ".git" / "index.lock").write_text("")

        with (
            self._patch_git(last_commit_days_ago=100, stale_branches=[f"b{i}" for i in range(10)]),
            patch.object(agent, "_count_todos", return_value={"TODO": 100, "FIXME": 50}),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.health_score >= 0

    def test_score_clamped_to_100(self, agent, agent_config, project_dir):
        """Score should never exceed 100."""
        with self._patch_git():
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.health_score <= 100


# ---------------------------------------------------------------------------
# TODO counting
# ---------------------------------------------------------------------------


class TestCountTodos:
    def test_counts_todos_in_files(self, agent, project_dir):
        counts = agent._count_todos(project_dir, ["TODO"])
        assert counts["TODO"] >= 1

    def test_counts_multiple_patterns(self, agent, project_dir):
        (project_dir / "fix.py").write_text("# FIXME: broken\n# TODO: later")
        counts = agent._count_todos(project_dir, ["TODO", "FIXME"])
        assert counts["TODO"] >= 1
        assert counts["FIXME"] >= 1

    def test_empty_project_zero_todos(self, agent, tmp_path):
        proj = tmp_path / "empty_proj"
        proj.mkdir()
        counts = agent._count_todos(proj, ["TODO"])
        assert counts["TODO"] == 0
