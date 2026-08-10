"""Tests for the Project Organiser agent — discovery, health scoring, edge cases."""

from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from sysadmin.core.config import ProjectOrganiserConfig
from sysadmin.projects.agent import ProjectOrganiserAgent


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
        mod = "sysadmin.projects.agent"

        stack = ExitStack()
        stack.enter_context(patch(f"{mod}.get_repo", return_value=repo))
        stack.enter_context(patch(f"{mod}.get_last_commit_date", return_value=last_commit))
        # Staleness is measured from the code commit; with nothing
        # ignored the two dates are the same, which is the case every
        # test here is about.
        stack.enter_context(
            patch(f"{mod}.get_last_code_commit_date", return_value=(last_commit, 0))
        )
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
        mod = "sysadmin.projects.agent"
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
    """The floor now comes from the manifest, not from projects.yaml."""

    async def _run(self, agent, tmp_path, score, manifest=None, global_threshold=40):
        from sysadmin.core.config import (
            AgentsConfig,
            AppConfig,
            ProjectOrganiserConfig,
        )

        project = tmp_path / "demo"
        project.mkdir(exist_ok=True)
        (project / ".git").mkdir(exist_ok=True)
        if manifest is not None:
            (project / ".project.yaml").write_text(
                yaml.safe_dump({"schema": 1, "id": "demo", "name": "demo"} | manifest),
                encoding="utf-8",
            )

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(
                    projects_root=str(tmp_path),
                    alert_threshold=global_threshold,
                )
            ),
        )
        snapshot = MagicMock(
            project_name="demo",
            project_path=str(project),
            health_score=score,
            findings={},
        )
        session = MagicMock()
        session.add = MagicMock()
        # The scan now closes alerts it did not re-raise (SNAG-PROJ-003),
        # so execute() must be awaitable even when nothing is resolved.
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        mod = "sysadmin.projects.agent"
        with (
            patch(f"{mod}.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=snapshot),
            patch.object(agent, "raise_alert", new=AsyncMock()) as alert,
        ):
            await agent._execute(session)
        return alert

    async def test_global_threshold_applies_without_an_override(self, agent, tmp_path):
        alert = await self._run(agent, tmp_path, score=30)
        alert.assert_awaited_once()

    async def test_a_healthy_project_raises_nothing(self, agent, tmp_path):
        alert = await self._run(agent, tmp_path, score=90)
        alert.assert_not_awaited()

    async def test_per_project_override_raises_the_bar(self, agent, tmp_path):
        alert = await self._run(
            agent, tmp_path, score=60, manifest={"alert_threshold": 70}
        )
        alert.assert_awaited_once()

    async def test_per_project_override_silences_a_project(self, agent, tmp_path):
        alert = await self._run(
            agent, tmp_path, score=10, manifest={"alert_threshold": 0}
        )
        alert.assert_not_awaited()

    async def test_an_archived_project_never_alerts_by_default(self, agent, tmp_path):
        alert = await self._run(
            agent, tmp_path, score=5, manifest={"status": "archived"}
        )
        alert.assert_not_awaited()

    async def test_an_undeclared_project_still_alerts(self, agent, tmp_path):
        """Undeclared is undecided, not exempt."""
        alert = await self._run(agent, tmp_path, score=10, manifest=None)
        alert.assert_awaited_once()


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
    """The floor is a property of the manifest entry, not of a lookup."""

    def _entry(self, status="active", alert_threshold=None):
        return SimpleNamespace(status=status, alert_threshold=alert_threshold)

    def _organiser(self, global_threshold=40):
        return ProjectOrganiserConfig(alert_threshold=global_threshold)

    @pytest.mark.parametrize("status", ["active", "dormant", "undeclared"])
    def test_scored_statuses_get_the_global_default(self, agent, status):
        assert agent._effective_threshold(
            self._entry(status), self._organiser()
        ) == 40

    def test_archived_suppresses_the_default(self, agent):
        assert agent._effective_threshold(
            self._entry("archived"), self._organiser()
        ) == 0

    def test_explicit_floor_beats_archived(self, agent):
        assert agent._effective_threshold(
            self._entry("archived", alert_threshold=50), self._organiser()
        ) == 50

    def test_explicit_zero_is_honoured_not_treated_as_absent(self, agent):
        assert agent._effective_threshold(
            self._entry("active", alert_threshold=0), self._organiser()
        ) == 0


class TestArchivedAlerts:
    async def test_archived_location_never_alerts_by_default(self, agent, tmp_path):
        """End-to-end: a rotten project under archive/ raises nothing.

        Nothing declares it — the inference that anything under
        ``archive/`` is archived is the registry's, and it survived the
        move off projects.yaml.
        """
        from sysadmin.core.config import (
            AgentsConfig,
            AppConfig,
            ProjectOrganiserConfig,
        )

        project = tmp_path / "archive" / "rotten"
        project.mkdir(parents=True)
        (project / ".git").mkdir()

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(
                    projects_root=str(tmp_path), alert_threshold=40
                )
            ),
        )
        snapshot = MagicMock(
            project_name="rotten",
            project_path=str(project),
            health_score=0,
            findings={},
        )
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        mod = "sysadmin.projects.agent"
        with (
            patch(f"{mod}.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=snapshot),
            patch.object(agent, "raise_alert", new=AsyncMock()) as alert,
        ):
            await agent._execute(session)

        alert.assert_not_awaited()



# ---------------------------------------------------------------------------
# Marker scanning — SNAG-PROJ-007/008/009
#
# All three defects made the score say something the surfaces could not
# explain: HACK and XXX cost points and appeared in no column, a repo's
# own snag list counted towards its own penalty, and the documented cap
# was grep's per-file limit rather than a total.
# ---------------------------------------------------------------------------


class TestMarkerScanExclusions:
    def test_markdown_is_not_scanned(self, agent, tmp_path):
        """Writing up a snag must not lower the score of the repo writing it."""
        proj = tmp_path / "documented"
        proj.mkdir()
        (proj / "snag_list.md").write_text("- TODO: fix the thing\n- TODO: and this")

        assert agent._count_todos(proj, ["TODO"])["TODO"] == 0

    def test_code_is_still_scanned(self, agent, tmp_path):
        """Guard against the test above passing because nothing is scanned."""
        proj = tmp_path / "coded"
        proj.mkdir()
        (proj / "main.py").write_text("# TODO: fix the thing")

        assert agent._count_todos(proj, ["TODO"])["TODO"] == 1

    def test_yaml_is_still_scanned(self, agent, tmp_path):
        proj = tmp_path / "configured"
        proj.mkdir()
        (proj / "config.yaml").write_text("# TODO: raise the timeout")

        assert agent._count_todos(proj, ["TODO"])["TODO"] == 1


class TestMarkerScanWordBoundaries:
    """``TODO`` is a marker; ``TODO_STATES`` is an identifier."""

    @pytest.mark.parametrize(
        ("line", "expected"),
        [
            ("# TODO: implement", 1),
            ("# TODO implement", 1),
            ("x = 1  # TODO", 1),
            ("TODO_STATES = ['a']", 0),
            ("print(TODOS)", 0),
            ("class TodoList: pass", 0),
        ],
    )
    def test_only_whole_words_count(self, agent, tmp_path, line, expected):
        proj = tmp_path / "words"
        proj.mkdir()
        (proj / "main.py").write_text(line)

        assert agent._count_todos(proj, ["TODO"])["TODO"] == expected


class TestMarkerScanCap:
    def test_cap_is_a_project_total_not_a_per_file_limit(self, agent, tmp_path):
        """``-m 1000`` bounded each file; 300 files could return 300,000."""
        proj = tmp_path / "swamped"
        proj.mkdir()
        per_file = agent._MAX_MATCHES_PER_FILE
        files = (agent._MAX_MATCHES_PER_PATTERN // per_file) + 2
        for i in range(files):
            (proj / f"mod{i}.py").write_text("# TODO: x\n" * per_file)

        findings: dict = {}
        counts = agent._count_todos(proj, ["TODO"], findings)

        assert counts["TODO"] == agent._MAX_MATCHES_PER_PATTERN
        assert findings["todo_scan_truncated"] == ["TODO"]

    def test_an_uncapped_scan_records_no_truncation(self, agent, tmp_path):
        proj = tmp_path / "modest"
        proj.mkdir()
        (proj / "main.py").write_text("# TODO: x\n# TODO: y")

        findings: dict = {}
        agent._count_todos(proj, ["TODO"], findings)

        assert "todo_scan_truncated" not in findings


class TestAllMarkersAreRecorded:
    def test_hack_and_xxx_reach_findings(self, agent, agent_config, project_dir):
        """The penalty is levied on all four patterns, so all four are stored."""
        agent_config.todo_patterns = ["TODO", "FIXME", "HACK", "XXX"]
        (project_dir / "nasty.py").write_text("# HACK: temporary\n# XXX: revisit")

        mod = "sysadmin.projects.agent"
        with (
            patch(f"{mod}.get_repo", return_value=None),
            patch(f"{mod}.get_repo_size_mb", return_value=1),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.findings["todos"]["HACK"] == 1
        assert snapshot.findings["todos"]["XXX"] == 1

    def test_named_columns_still_mean_what_they_say(
        self, agent, agent_config, project_dir
    ):
        """``todo_count`` counts TODOs — not "all markers"."""
        agent_config.todo_patterns = ["TODO", "FIXME", "HACK"]
        (project_dir / "nasty.py").write_text("# HACK: one\n# HACK: two")

        mod = "sysadmin.projects.agent"
        with (
            patch(f"{mod}.get_repo", return_value=None),
            patch(f"{mod}.get_repo_size_mb", return_value=1),
        ):
            snapshot = agent._analyse_project(project_dir, agent_config)

        assert snapshot.findings["todos"]["HACK"] == 2
        assert snapshot.todo_count == 1  # the one in main.py
        assert snapshot.fixme_count == 0


# ---------------------------------------------------------------------------
# Alert resolution — SNAG-PROJ-003/004
#
# The organiser raised on every six-hourly scan and never resolved, so
# 1,664 rows were live and unresolvable by 2026-08-07. Retention purges
# resolved alerts only, so none of them would ever have expired.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAlertResolution:
    async def _run(self, agent, tmp_path, *, score, resolved_rows=0):
        from sysadmin.core.config import (
            AgentsConfig,
            AppConfig,
            ProjectOrganiserConfig,
        )

        project = tmp_path / "demo"
        project.mkdir(exist_ok=True)
        (project / ".git").mkdir(exist_ok=True)

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(
                    projects_root=str(tmp_path), alert_threshold=40
                )
            ),
        )
        snapshot = MagicMock(
            project_name="demo",
            project_path=str(project),
            health_score=score,
            findings={},
        )
        session = MagicMock()
        session.execute = AsyncMock(
            return_value=MagicMock(rowcount=resolved_rows)
        )

        mod = "sysadmin.projects.agent"
        with (
            patch(f"{mod}.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=snapshot),
            patch.object(agent, "raise_alert", new=AsyncMock()),
        ):
            result = await agent._execute(session)
        return session, result

    async def test_every_scan_attempts_a_resolve(self, agent, tmp_path):
        """Not only when something recovered — a vanished project never does."""
        session, _ = await self._run(agent, tmp_path, score=90)

        session.execute.assert_awaited_once()

    async def test_resolved_count_is_reported(self, agent, tmp_path):
        _, result = await self._run(agent, tmp_path, score=90, resolved_rows=7)

        assert result.details["alerts_resolved"] == 7

    async def test_a_still_failing_project_is_excluded_from_the_resolve(
        self, agent, tmp_path
    ):
        """Its alert was raised moments ago in this same transaction."""
        session, _ = await self._run(agent, tmp_path, score=10)

        sql = str(session.execute.await_args.args[0])
        assert "title NOT IN" in sql

    async def test_a_clean_scan_resolves_without_an_exclusion(
        self, agent, tmp_path
    ):
        """Nothing failing means every open health alert is stale."""
        session, _ = await self._run(agent, tmp_path, score=90)

        sql = str(session.execute.await_args.args[0])
        assert "title NOT IN" not in sql
        assert "title LIKE" in sql

    async def test_only_this_agents_health_alerts_are_touched(
        self, agent, tmp_path
    ):
        """The log aggregator's 547,882 rows are a different defect."""
        session, _ = await self._run(agent, tmp_path, score=90)

        sql = str(session.execute.await_args.args[0])
        assert "alerts.agent =" in sql
        assert "resolved IS false" in sql


class TestAlertTitleHasOneSource:
    """A hand-written resolve pattern that matches nothing is invisible."""

    def test_raise_and_resolve_derive_from_the_same_function(self):
        from sysadmin.projects.agent import _ALERT_TITLE_LIKE, _alert_title

        title = _alert_title("demo")
        prefix, suffix = _ALERT_TITLE_LIKE.split("%")

        assert title.startswith(prefix) and title.endswith(suffix)


# ---------------------------------------------------------------------------
# What `archived` actually waives — SNAG-PROJ-011/012
#
# Three places described archived projects as exempt from git hygiene
# generally. They are not: `archived` waives the stale-branch deduction
# and the staleness deduction, and nothing else. Alert suppression, by
# contrast, is stronger than the docs implied — absolute, at any score.
# ---------------------------------------------------------------------------


class TestArchivedWaivesExactlyTwoDeductions:
    def _analyse(self, agent, agent_config, project_dir, status, **git):
        mod = "sysadmin.projects.agent"
        repo = MagicMock()
        last_commit = datetime.now(UTC) - timedelta(
            days=git.pop("last_commit_days_ago", 5)
        )
        with (
            patch(f"{mod}.get_repo", return_value=repo),
            patch(f"{mod}.get_last_commit_date", return_value=last_commit),
            patch(
                f"{mod}.get_last_code_commit_date", return_value=(last_commit, 0)
            ),
            patch(f"{mod}.get_branches", return_value=["main"]),
            patch(
                f"{mod}.get_stale_branches",
                return_value=git.pop("stale_branches", []),
            ),
            patch(f"{mod}.has_remote", return_value=git.pop("has_remote", True)),
            patch(f"{mod}.get_repo_size_mb", return_value=1),
        ):
            return agent._analyse_project(project_dir, agent_config, status)

    def test_stale_branches_are_waived(self, agent, agent_config, project_dir):
        branches = [f"b{i}" for i in range(5)]
        active = self._analyse(
            agent, agent_config, project_dir, "active", stale_branches=branches
        )
        archived = self._analyse(
            agent, agent_config, project_dir, "archived", stale_branches=branches
        )

        assert archived.health_score > active.health_score
        # Recorded either way — waived is not the same as unmeasured.
        assert archived.findings["stale_branches"] == branches

    def test_commit_staleness_is_waived(self, agent, agent_config, project_dir):
        active = self._analyse(
            agent, agent_config, project_dir, "active", last_commit_days_ago=400
        )
        archived = self._analyse(
            agent, agent_config, project_dir, "archived", last_commit_days_ago=400
        )

        assert archived.health_score > active.health_score

    def test_a_stale_git_lock_still_costs_an_archived_project(
        self, agent, agent_config, project_dir
    ):
        """The specific claim SNAG-PROJ-011 was filed about."""
        (project_dir / ".git" / "index.lock").write_text("")
        archived = self._analyse(agent, agent_config, project_dir, "archived")

        assert archived.findings["stale_git_lock"] is True
        assert archived.health_score <= 95

    def test_a_missing_remote_is_still_reported_when_archived(
        self, agent, agent_config, project_dir
    ):
        archived = self._analyse(
            agent, agent_config, project_dir, "archived", has_remote=False
        )

        assert archived.findings.get("no_remote") is True

    def test_missing_docs_still_count_when_archived(
        self, agent, agent_config, project_dir
    ):
        (project_dir / "README.md").unlink()
        archived = self._analyse(agent, agent_config, project_dir, "archived")

        assert "missing_readme" in archived.findings


class TestArchivedAlertSuppressionIsAbsolute:
    """`_effective_threshold` returns 0 and the score is clamped at 0.

    So the alert condition is `score < 0` — unreachable at any score,
    for any repository. The docs read as though a low enough score would
    still alert (SNAG-PROJ-012); it cannot, and the guarantee is worth
    a test rather than a sentence.
    """

    def _entry(self, status, alert_threshold=None):
        return SimpleNamespace(
            status=status, alert_threshold=alert_threshold, declared=True
        )

    def test_archived_threshold_is_zero(self, agent, agent_config):
        threshold = agent._effective_threshold(
            self._entry("archived"), agent_config
        )
        assert threshold == 0

    @pytest.mark.parametrize("score", [0, 1, 40, 100])
    def test_no_score_can_reach_the_threshold(self, agent, agent_config, score):
        threshold = agent._effective_threshold(
            self._entry("archived"), agent_config
        )
        assert not score < threshold

    def test_an_explicit_threshold_still_overrides_it(self, agent, agent_config):
        """The escape hatch: a retired repo somebody still wants warned about."""
        threshold = agent._effective_threshold(
            self._entry("archived", alert_threshold=50), agent_config
        )
        assert threshold == 50
        assert 30 < threshold

    def test_dormant_is_not_suppressed(self, agent, agent_config):
        """Only `archived` gets the absolute waiver — resting is not retired."""
        threshold = agent._effective_threshold(
            self._entry("dormant"), agent_config
        )
        assert threshold == agent_config.alert_threshold
