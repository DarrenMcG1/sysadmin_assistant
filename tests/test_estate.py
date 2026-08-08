"""Tests for estate.json — the ignore rule, the atomic write, the shape."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from git import Actor, Repo

from sysadmin.core.config import CodeCommitIgnoreConfig
from sysadmin.projects.estate import (
    SCHEMA_VERSION,
    build_estate,
    estate_path,
    git_facts,
    health_from,
    write_atomic,
)
from sysadmin.projects.git import get_last_code_commit_date
from sysadmin.registry import load_registry

ACTOR = Actor("Test", "test@example.com")


def commit(repo: Repo, message: str, when: str) -> None:
    """One commit with a fixed date, so ordering is deterministic."""
    path = Path(repo.working_tree_dir) / "file.txt"
    path.write_text(message, encoding="utf-8")
    repo.index.add(["file.txt"])
    repo.index.commit(
        message, author=ACTOR, committer=ACTOR,
        author_date=when, commit_date=when,
    )


@pytest.fixture
def repo_with_history(tmp_path):
    """A repo whose newest two commits are estate-wide sweeps."""
    path = tmp_path / "demo"
    path.mkdir()
    repo = Repo.init(path)
    commit(repo, "feat: the actual work", "2026-02-06T12:00:00+0000")
    commit(repo, "WIP snapshot before ~/projects reorganisation (2026-08-04)",
           "2026-08-04T12:00:00+0000")
    commit(repo, "Add roadmap document set", "2026-08-06T12:00:00+0000")
    (path / ".project.yaml").write_text(
        yaml.safe_dump({"schema": 1, "id": "demo", "name": "demo",
                        "status": "dormant"}),
        encoding="utf-8",
    )
    return path, repo


# ── the ignore rule ──────────────────────────────────────────────


class TestCodeCommitIgnore:
    def test_the_newest_real_commit_wins_over_two_sweeps(self, repo_with_history):
        _, repo = repo_with_history
        cfg = CodeCommitIgnoreConfig()
        stamp, skipped = get_last_code_commit_date(
            repo, cfg.message_patterns, cfg.shas, cfg.max_walk
        )
        assert stamp.date().isoformat() == "2026-02-06"
        assert skipped == 2

    def test_one_pattern_is_not_enough(self, repo_with_history):
        """The reorganisation snapshot alone leaves the doc sweep in front.

        With only that pattern the walk stops at the newest commit having
        skipped nothing, and the figure reads four days old for a project
        last worked on in February.
        """
        _, repo = repo_with_history
        stamp, skipped = get_last_code_commit_date(
            repo, [r"WIP snapshot before ~/projects reorganisation"]
        )
        assert stamp.date().isoformat() == "2026-08-06"
        assert skipped == 0

    def test_no_patterns_reports_the_true_newest_commit(self, repo_with_history):
        _, repo = repo_with_history
        stamp, skipped = get_last_code_commit_date(repo, [])
        assert stamp.date().isoformat() == "2026-08-06"
        assert skipped == 0

    def test_a_sha_excludes_one_commit(self, repo_with_history):
        _, repo = repo_with_history
        newest = repo.head.commit.hexsha
        stamp, skipped = get_last_code_commit_date(repo, [], shas=[newest])
        assert stamp.date().isoformat() == "2026-08-04"
        assert skipped == 1

    def test_an_abbreviated_sha_also_excludes(self, repo_with_history):
        _, repo = repo_with_history
        stamp, _ = get_last_code_commit_date(
            repo, [], shas=[repo.head.commit.hexsha[:12]]
        )
        assert stamp.date().isoformat() == "2026-08-04"

    def test_a_repo_that_is_all_sweeps_reports_no_code_commit(self, tmp_path):
        """Real case: two repositories whose entire history is sweeps."""
        path = tmp_path / "shell"
        path.mkdir()
        repo = Repo.init(path)
        commit(repo, "WIP snapshot before ~/projects reorganisation (2026-08-04)",
               "2026-08-04T12:00:00+0000")
        commit(repo, "Add roadmap document set", "2026-08-06T12:00:00+0000")

        cfg = CodeCommitIgnoreConfig()
        stamp, skipped = get_last_code_commit_date(
            repo, cfg.message_patterns, cfg.shas, cfg.max_walk
        )
        assert stamp is None
        assert skipped == 2

    def test_only_the_subject_is_matched(self, tmp_path):
        """A body quoting the sweep's subject must not exclude real work."""
        path = tmp_path / "body"
        path.mkdir()
        repo = Repo.init(path)
        commit(repo, "feat: real work\n\nReverts WIP snapshot before "
                     "~/projects reorganisation", "2026-05-01T12:00:00+0000")
        cfg = CodeCommitIgnoreConfig()
        stamp, skipped = get_last_code_commit_date(repo, cfg.message_patterns)
        assert stamp.date().isoformat() == "2026-05-01"
        assert skipped == 0

    def test_matching_is_case_insensitive(self, tmp_path):
        path = tmp_path / "case"
        path.mkdir()
        repo = Repo.init(path)
        commit(repo, "feat: work", "2026-01-01T12:00:00+0000")
        commit(repo, "ADD ROADMAP DOCUMENT SET", "2026-08-06T12:00:00+0000")
        stamp, skipped = get_last_code_commit_date(
            repo, [r"^Add roadmap document set$"]
        )
        assert stamp.date().isoformat() == "2026-01-01"
        assert skipped == 1

    def test_an_empty_repository_reports_nothing(self, tmp_path):
        path = tmp_path / "empty"
        path.mkdir()
        repo = Repo.init(path)
        assert get_last_code_commit_date(repo, []) == (None, 0)

    def test_the_walk_is_bounded(self, repo_with_history):
        _, repo = repo_with_history
        stamp, skipped = get_last_code_commit_date(
            repo, CodeCommitIgnoreConfig().message_patterns, max_walk=1
        )
        assert stamp is None
        assert skipped == 1


class TestGitFacts:
    def test_both_dates_are_published(self, repo_with_history):
        path, _ = repo_with_history
        facts = git_facts(path, CodeCommitIgnoreConfig())
        assert facts["last_commit"] == "2026-08-06"
        assert facts["last_code_commit"] == "2026-02-06"
        assert facts["ignored_commits"] == 2

    def test_a_directory_that_is_not_a_repo_is_tolerated(self, tmp_path):
        facts = git_facts(tmp_path, CodeCommitIgnoreConfig())
        assert facts["last_commit"] is None
        assert facts["commits"] == 0


# ── the atomic write ─────────────────────────────────────────────


class TestAtomicWrite:
    def test_it_writes_valid_json(self, tmp_path):
        target = tmp_path / "estate.json"
        write_atomic(target, {"schema": 1, "projects": []})
        assert json.loads(target.read_text())["schema"] == 1

    def test_it_leaves_no_temporary_file_behind(self, tmp_path):
        target = tmp_path / "estate.json"
        write_atomic(target, {"schema": 1})
        assert [p.name for p in tmp_path.iterdir()] == ["estate.json"]

    def test_a_failed_write_leaves_the_previous_file_intact(self, tmp_path):
        """The reason for the rename: a consumer polling this file must
        never see a half-written one, and must never lose the last good
        one to a failure partway through."""
        target = tmp_path / "estate.json"
        write_atomic(target, {"schema": 1, "generation": "first"})

        with patch("json.dump", side_effect=OSError("disk full")):
            with pytest.raises(OSError):
                write_atomic(target, {"schema": 1, "generation": "second"})

        assert json.loads(target.read_text())["generation"] == "first"
        assert [p.name for p in tmp_path.iterdir()] == ["estate.json"]

    def test_the_temporary_file_shares_the_destination_filesystem(self, tmp_path):
        """os.replace is only atomic within one filesystem, so the
        temporary file cannot live in /tmp."""
        seen = {}
        real = os.replace

        def spy(src, dst):
            seen["src_parent"] = Path(src).parent
            return real(src, dst)

        target = tmp_path / "nested" / "estate.json"
        with patch("sysadmin.projects.estate.os.replace", side_effect=spy):
            write_atomic(target, {"schema": 1})
        assert seen["src_parent"] == target.parent

    def test_it_creates_the_parent_directory(self, tmp_path):
        target = tmp_path / "a" / "b" / "estate.json"
        write_atomic(target, {"schema": 1})
        assert target.is_file()

    def test_it_overwrites_rather_than_appending(self, tmp_path):
        target = tmp_path / "estate.json"
        write_atomic(target, {"schema": 1, "projects": [1, 2, 3]})
        write_atomic(target, {"schema": 1, "projects": []})
        assert json.loads(target.read_text())["projects"] == []


class TestEstatePath:
    def test_a_relative_path_resolves_against_the_root(self):
        assert estate_path("estate.json", "/srv/projects") == Path(
            "/srv/projects/estate.json"
        )

    def test_an_absolute_path_is_used_as_given(self):
        assert estate_path("/var/lib/estate.json", "/srv/projects") == Path(
            "/var/lib/estate.json"
        )


# ── the payload ──────────────────────────────────────────────────


class TestBuildEstate:
    @pytest.fixture
    def registry(self, repo_with_history, tmp_path):
        (tmp_path / "mystery" / ".git").mkdir(parents=True)
        return load_registry(tmp_path)

    def test_the_envelope_is_versioned(self, registry):
        payload = build_estate(registry, {}, CodeCommitIgnoreConfig())
        assert payload["schema"] == SCHEMA_VERSION
        assert payload["root"] == str(registry.root)
        assert payload["generated"].endswith("+00:00")

    def test_undeclared_repositories_appear(self, registry):
        payload = build_estate(registry, {}, CodeCommitIgnoreConfig())
        by_id = {p["id"]: p for p in payload["projects"]}
        assert by_id["mystery"]["status"] == "undeclared"
        assert by_id["mystery"]["declared"] is False

    def test_services_are_names_not_topology(self, registry):
        payload = build_estate(
            registry, {"demo": ["demo-backend", "demo-timer"]},
            CodeCommitIgnoreConfig(),
        )
        demo = next(p for p in payload["projects"] if p["id"] == "demo")
        assert demo["services"] == ["demo-backend", "demo-timer"]

    def test_an_undeclared_project_is_given_no_services(self, registry):
        """It has no id to key on, so any match would be a guess."""
        payload = build_estate(
            registry, {"mystery": ["something"]}, CodeCommitIgnoreConfig()
        )
        mystery = next(p for p in payload["projects"] if p["id"] == "mystery")
        assert mystery["services"] == []

    def test_health_is_absent_rather_than_invented_without_a_scan(self, registry):
        payload = build_estate(registry, {}, CodeCommitIgnoreConfig())
        assert all(p["health"]["score"] is None for p in payload["projects"])

    def test_health_comes_from_the_run_that_scored_it(self, registry):
        demo_path = str(registry.root / "demo")
        payload = build_estate(
            registry, {}, CodeCommitIgnoreConfig(),
            snapshots={demo_path: ({"no_remote": True, "missing_readme": True}, 72)},
        )
        demo = next(p for p in payload["projects"] if p["id"] == "demo")
        assert demo["health"]["score"] == 72
        assert "no-remote" in demo["health"]["flags"]
        assert "no-readme" in demo["health"]["flags"]

    def test_decisions_travel_with_the_project(self, tmp_path, repo_with_history):
        path, _ = repo_with_history
        (path / ".project.yaml").write_text(
            yaml.safe_dump({
                "schema": 1, "id": "demo", "name": "demo", "status": "dormant",
                "decisions": [{"date": "2026-08-06", "change": "active -> dormant",
                               "reason": "last code change was February"}],
            }),
            encoding="utf-8",
        )
        payload = build_estate(load_registry(tmp_path), {}, CodeCommitIgnoreConfig())
        demo = next(p for p in payload["projects"] if p["id"] == "demo")
        assert demo["decisions"][0]["change"] == "active -> dormant"
        assert "note" not in demo["decisions"][0]

    def test_projects_are_ordered_by_id(self, registry):
        payload = build_estate(registry, {}, CodeCommitIgnoreConfig())
        ids = [p["id"] for p in payload["projects"]]
        assert ids == sorted(ids)

    def test_generated_is_stamped_by_the_caller(self, registry):
        when = datetime(2026, 8, 8, 17, 13, tzinfo=UTC)
        payload = build_estate(registry, {}, CodeCommitIgnoreConfig(), generated=when)
        assert payload["generated"] == "2026-08-08T17:13:00+00:00"


class TestHealthFlags:
    def test_no_findings_means_no_flags(self):
        assert health_from({}, 100)["flags"] == ["no-next-action"]

    def test_only_truthy_findings_become_flags(self):
        flags = health_from({"no_remote": True, "missing_readme": False}, 90)["flags"]
        assert "no-remote" in flags
        assert "no-readme" not in flags

    def test_a_score_of_zero_is_reported_not_dropped(self):
        assert health_from({}, 0)["score"] == 0
