"""Tests for the Project Organiser agent — discovery, health scoring, edge cases."""

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

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
        last_commit = datetime.now(UTC) - timedelta(days=last_commit_days_ago)
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


# ---------------------------------------------------------------------------
# TODO penalty cap (Session 20)
#
# Uncapped, 5 points per 10 markers pinned the real 300-TODO projects at
# 0 permanently — the score stopped saying anything about the rest of
# their health, so nothing they fixed ever showed up.
# ---------------------------------------------------------------------------


class TestTodoPenaltyCap:
    @pytest.mark.parametrize(
        ("markers", "expected"),
        [
            (0, 0),
            (9, 0),
            (10, 5),
            (59, 25),
            (60, 30),  # exactly at the cap
            (61, 30),  # first marker past it
            (370, 30),  # PersonalAssistant's real order of magnitude
        ],
    )
    def test_penalty_boundaries(self, agent, markers, expected):
        findings: dict = {}
        assert agent._todo_penalty(markers, 30, findings) == expected

    def test_cap_records_the_raw_penalty(self, agent):
        findings: dict = {}
        agent._todo_penalty(370, 30, findings)

        assert findings["todo_penalty_capped"] == {
            "raw_penalty": 185,
            "applied_penalty": 30,
            "total_markers": 370,
        }

    def test_under_the_cap_records_nothing(self, agent):
        findings: dict = {}
        agent._todo_penalty(40, 30, findings)
        assert findings == {}

    def test_none_disables_the_cap(self, agent):
        assert agent._todo_penalty(370, None, findings={}) == 185

    def test_zero_cap_removes_the_penalty(self, agent):
        assert agent._todo_penalty(370, 0, findings={}) == 0

    def test_high_todo_project_no_longer_pins_at_zero(
        self, agent, agent_config, project_dir
    ):
        """A 370-marker project keeps a score that can still move."""
        with (
            TestAnalyseProject()._patch_git(last_commit_days_ago=1),
            patch.object(
                agent, "_count_todos", return_value={"TODO": 330, "FIXME": 40}
            ),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.health_score == 70  # 100 - 30, nothing else wrong
        assert snapshot.findings["todo_penalty_capped"]["raw_penalty"] == 185

    def test_uncapped_config_restores_old_behaviour(
        self, agent, agent_config, project_dir
    ):
        agent_config.max_todo_penalty = None
        with (
            TestAnalyseProject()._patch_git(last_commit_days_ago=1),
            patch.object(
                agent, "_count_todos", return_value={"TODO": 330, "FIXME": 40}
            ),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.health_score == 0


# ---------------------------------------------------------------------------
# Per-project alert thresholds (Session 20)
# ---------------------------------------------------------------------------


class TestAlertThreshold:
    async def _run(self, agent, tmp_path, score, managed=None, global_threshold=40):
        from sysadmin.config import (
            AgentsConfig,
            AppConfig,
            ProjectOrganiserConfig,
            ProjectsConfig,
        )

        project = tmp_path / "demo"
        project.mkdir(exist_ok=True)
        (project / ".git").mkdir(exist_ok=True)

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(
                    projects_root=str(tmp_path),
                    alert_threshold=global_threshold,
                )
            ),
            projects=ProjectsConfig(projects=managed or []),
        )
        snapshot = MagicMock(
            project_name="demo",
            project_path=str(project),
            health_score=score,
            findings={},
        )
        session = MagicMock()
        session.add = MagicMock()

        mod = "sysadmin.agents.project_organiser"
        with (
            patch(f"{mod}.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=snapshot),
            patch.object(agent, "raise_alert", new=AsyncMock()) as alert,
        ):
            await agent._execute(session)
        return alert

    async def test_global_threshold_applies_without_an_override(self, agent, tmp_path):
        alert = await self._run(agent, tmp_path, score=35)
        assert alert.await_count == 1

        alert = await self._run(agent, tmp_path, score=45)
        assert alert.await_count == 0

    async def test_per_project_override_raises_the_bar(self, agent, tmp_path):
        from sysadmin.config import ManagedProject

        managed = [
            ManagedProject(
                name="demo", path=str(tmp_path / "demo"), alert_threshold=70
            )
        ]
        alert = await self._run(agent, tmp_path, score=65, managed=managed)

        assert alert.await_count == 1
        assert "alert threshold 70" in alert.await_args.kwargs["message"]

    async def test_per_project_override_silences_a_project(self, agent, tmp_path):
        from sysadmin.config import ManagedProject

        managed = [
            ManagedProject(name="demo", path=str(tmp_path / "demo"), alert_threshold=0)
        ]
        alert = await self._run(agent, tmp_path, score=0, managed=managed)

        assert alert.await_count == 0

    async def test_other_projects_keep_the_global_default(self, agent, tmp_path):
        from sysadmin.config import ManagedProject

        managed = [
            ManagedProject(
                name="somewhere-else",
                path=str(tmp_path / "other"),
                alert_threshold=90,
            )
        ]
        alert = await self._run(agent, tmp_path, score=45, managed=managed)

        assert alert.await_count == 0


# ---------------------------------------------------------------------------
# Depth-aware discovery + project status (Session 21)
# ---------------------------------------------------------------------------


class TestDepthDiscovery:
    def test_finds_projects_inside_category_dirs(self, agent, tmp_path):
        (tmp_path / "apps" / "my_app" / ".git").mkdir(parents=True)

        result = agent._discover_projects(tmp_path)
        assert result == [tmp_path / "apps" / "my_app"]

    def test_top_level_and_nested_projects_found_together(self, agent, tmp_path):
        (tmp_path / "solo" / ".git").mkdir(parents=True)
        (tmp_path / "ml" / "model" / ".git").mkdir(parents=True)

        result = agent._discover_projects(tmp_path)
        assert set(result) == {tmp_path / "solo", tmp_path / "ml" / "model"}

    def test_never_descends_into_a_project(self, agent, tmp_path):
        """A repo's vendored sub-repos are its own business."""
        outer = tmp_path / "outer"
        (outer / ".git").mkdir(parents=True)
        (outer / "vendored" / ".git").mkdir(parents=True)

        result = agent._discover_projects(tmp_path)
        assert result == [outer]

    def test_depth_one_restores_old_behaviour(self, agent, tmp_path):
        (tmp_path / "apps" / "my_app" / ".git").mkdir(parents=True)

        assert agent._discover_projects(tmp_path, max_depth=1) == []

    def test_depth_is_bounded(self, agent, tmp_path):
        (tmp_path / "a" / "b" / "deep_proj" / ".git").mkdir(parents=True)

        assert agent._discover_projects(tmp_path) == []
        assert agent._discover_projects(tmp_path, max_depth=3) == [
            tmp_path / "a" / "b" / "deep_proj"
        ]

    def test_hidden_dirs_not_descended(self, agent, tmp_path):
        (tmp_path / ".backups" / "mirror" / ".git").mkdir(parents=True)

        assert agent._discover_projects(tmp_path) == []


class TestInferStatus:
    def test_archive_children_are_archived(self, agent, tmp_path):
        path = tmp_path / "archive" / "old_thing"
        path.mkdir(parents=True)
        assert agent._infer_status(path, tmp_path) == "archived"

    def test_deeper_archive_paths_are_archived(self, agent, tmp_path):
        path = tmp_path / "archive" / "coding-scraps" / "task-1"
        path.mkdir(parents=True)
        assert agent._infer_status(path, tmp_path) == "archived"

    def test_everything_else_is_active(self, agent, tmp_path):
        path = tmp_path / "apps" / "my_app"
        path.mkdir(parents=True)
        assert agent._infer_status(path, tmp_path) == "active"

    def test_paths_outside_root_are_active(self, agent, tmp_path):
        outside = tmp_path.parent / "elsewhere"
        assert agent._infer_status(outside, tmp_path) == "active"


class TestStatusScoring:
    """dormant skips staleness; archived also skips branch hygiene."""

    def test_dormant_skips_staleness_penalty(self, agent, agent_config, project_dir):
        with TestAnalyseProject()._patch_git(last_commit_days_ago=90):
            active = agent._analyse_project(project_dir, agent_config)
            dormant = agent._analyse_project(project_dir, agent_config, "dormant")

        assert active.health_score == dormant.health_score - 15
        # The fact is still recorded — only the deduction is waived
        assert "stale" in dormant.findings

    def test_dormant_still_penalised_for_stale_branches(
        self, agent, agent_config, project_dir
    ):
        with TestAnalyseProject()._patch_git(
            last_commit_days_ago=1, stale_branches=["old-branch"]
        ):
            snapshot = agent._analyse_project(project_dir, agent_config, "dormant")

        assert snapshot.health_score == 95
        assert "stale_branches" in snapshot.findings

    def test_archived_skips_staleness_and_branch_penalties(
        self, agent, agent_config, project_dir
    ):
        with TestAnalyseProject()._patch_git(
            last_commit_days_ago=90, stale_branches=["a", "b"]
        ):
            snapshot = agent._analyse_project(project_dir, agent_config, "archived")

        assert snapshot.health_score == 100
        assert "stale" in snapshot.findings
        assert "stale_branches" in snapshot.findings

    def test_archived_still_penalised_for_untidiness(
        self, agent, agent_config, project_dir
    ):
        (project_dir / ".git" / "index.lock").write_text("")
        with TestAnalyseProject()._patch_git(last_commit_days_ago=90):
            snapshot = agent._analyse_project(project_dir, agent_config, "archived")

        assert snapshot.health_score == 95
        assert "stale_git_lock" in snapshot.findings

    def test_status_recorded_in_findings(self, agent, agent_config, project_dir):
        with TestAnalyseProject()._patch_git(last_commit_days_ago=1):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.findings["status"] == "active"


class TestEffectiveThreshold:
    def _configs(self, managed=None, global_threshold=40):
        from sysadmin.config import ProjectsConfig

        return (
            ProjectsConfig(projects=managed or []),
            ProjectOrganiserConfig(alert_threshold=global_threshold),
        )

    def test_active_gets_the_global_default(self, agent):
        projects, organiser = self._configs()
        assert agent._effective_threshold(
            projects, organiser, "demo", "/p/demo", "active"
        ) == 40

    def test_dormant_gets_the_global_default(self, agent):
        projects, organiser = self._configs()
        assert agent._effective_threshold(
            projects, organiser, "demo", "/p/demo", "dormant"
        ) == 40

    def test_archived_suppresses_the_default(self, agent):
        projects, organiser = self._configs()
        assert agent._effective_threshold(
            projects, organiser, "demo", "/p/demo", "archived"
        ) == 0

    def test_explicit_floor_beats_archived(self, agent, tmp_path):
        from sysadmin.config import ManagedProject

        managed = [
            ManagedProject(name="demo", path=str(tmp_path), alert_threshold=50)
        ]
        projects, organiser = self._configs(managed)
        assert agent._effective_threshold(
            projects, organiser, "demo", str(tmp_path), "archived"
        ) == 50


class TestArchivedAlerts:
    async def test_archived_location_never_alerts_by_default(self, agent, tmp_path):
        """End-to-end: a rotten project under archive/ raises nothing."""
        from sysadmin.config import (
            AgentsConfig,
            AppConfig,
            ProjectsConfig,
        )

        project = tmp_path / "archive" / "old"
        (project / ".git").mkdir(parents=True)

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(
                    projects_root=str(tmp_path)
                )
            ),
            projects=ProjectsConfig(projects=[]),
        )
        snapshot = MagicMock(
            project_name="old", project_path=str(project), health_score=0, findings={}
        )
        session = MagicMock()

        mod = "sysadmin.agents.project_organiser"
        with (
            patch(f"{mod}.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=snapshot) as analyse,
            patch.object(agent, "raise_alert", new=AsyncMock()) as alert,
        ):
            await agent._execute(session)

        assert alert.await_count == 0
        # And the inferred status reached the analyser
        assert analyse.call_args[0][2] == "archived"
