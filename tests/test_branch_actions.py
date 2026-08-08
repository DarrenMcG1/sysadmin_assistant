"""Tests for stale-branch pruning — the destructive project action.

These delete real git branches, so the safety rules get far more
attention than the happy path:

- dry run is the default and leaves the branch set identical
- confirm deletes exactly the previewed set, nothing more
- an unmerged branch is never deleted without *both* opt-in flags
- the default, protected, checked-out and worktree branches survive
  every configuration
- a branch holding commits its upstream lacks is refused
- the repo path is confined to the configured projects root
- ``max_deletions`` caps a single call

**Every test builds a throwaway repository under ``tmp_path``** with
``git init`` and fabricated commits. Nothing here ever opens, reads or
writes a real repository of the user's.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from git import Repo

from sysadmin.core.config import BranchActionsConfig
from sysadmin.core.contracts import BranchCleanupResponse, BranchInfo
from sysadmin.projects import branch_actions
from sysadmin.projects.branch_actions import (
    BranchActionError,
    execute_branch_cleanup,
    plan_branch_cleanup,
    resolve_project_repo,
)
from sysadmin.projects.git import detect_default_branch, upstream_state, worktree_branches

# ---------------------------------------------------------------------------
# Throwaway repository helpers
# ---------------------------------------------------------------------------


def days_ago(days: int) -> str:
    """A git-friendly timestamp N days in the past."""
    stamp = datetime.now(UTC) - timedelta(days=days)
    return stamp.strftime("%Y-%m-%d %H:%M:%S +0000")


def init_repo(path: Path, initial_branch: str = "main") -> Repo:
    """A fresh repo with a test identity and one commit on the default branch."""
    path.mkdir(parents=True, exist_ok=True)
    repo = Repo.init(path, initial_branch=initial_branch)
    with repo.config_writer() as cw:
        cw.set_value("user", "name", "Test User")
        cw.set_value("user", "email", "test@example.com")
    commit(repo, "README.md", days_ago(400))
    return repo


def commit(repo: Repo, filename: str, when: str, content: str = "content\n"):
    """Add a file and commit it at a fixed date."""
    file_path = Path(repo.working_dir) / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    repo.index.add([filename])
    return repo.index.commit(f"add {filename}", commit_date=when, author_date=when)


def make_merged_branch(repo: Repo, name: str, when: str):
    """A branch whose tip is an ancestor of the default branch.

    Created by pointing the branch at the current tip, then moving the
    default branch on — so ``is_ancestor`` is genuinely true rather than
    inferred from anything.
    """
    default = repo.active_branch.name
    tip = commit(repo, f"{name}.txt", when)
    repo.create_head(name, tip)
    commit(repo, f"after-{name}.txt", days_ago(1))
    repo.heads[default].checkout()
    return repo.heads[name]


def make_unmerged_branch(repo: Repo, name: str, when: str):
    """A branch with a commit that never reaches the default branch."""
    default = repo.active_branch.name
    repo.create_head(name, repo.head.commit).checkout()
    commit(repo, f"{name}-only.txt", when)
    repo.heads[default].checkout()
    return repo.heads[name]


def set_upstream(repo: Repo, branch: str, remote_sha: str | None) -> None:
    """Point ``branch`` at ``origin/<branch>``.

    ``remote_sha`` creates the remote-tracking ref at that commit; None
    leaves the config claiming an upstream that does not exist, which is
    the "state cannot be read" case.
    """
    if remote_sha is not None:
        repo.git.update_ref(f"refs/remotes/origin/{branch}", remote_sha)
    with repo.config_writer() as cw:
        cw.set_value(f'branch "{branch}"', "remote", "origin")
        cw.set_value(f'branch "{branch}"', "merge", f"refs/heads/{branch}")


def branch_shas(repo_path: Path) -> dict[str, str]:
    """Name → tip sha for every local branch — the before/after snapshot."""
    repo = Repo(repo_path)
    return {b.name: b.commit.hexsha for b in repo.branches}


def by_name(response: BranchCleanupResponse) -> dict[str, BranchInfo]:
    return {info.name: info for info in response.branches}


def planned(response: BranchCleanupResponse) -> set[str]:
    return {b.name for b in response.branches if b.status == "planned"}


def deleted(response: BranchCleanupResponse) -> set[str]:
    return {b.name for b in response.branches if b.status == "deleted"}


@pytest.fixture
def settings():
    """Config with both dangerous doors shut — the shipped defaults."""
    return BranchActionsConfig(
        protected_branches=["main", "master", "develop", "release/*"],
        allow_unmerged_delete=False,
        max_deletions=20,
        min_stale_days=7,
    )


@pytest.fixture
def repo_path(tmp_path):
    """A repo with one merged-stale, one unmerged-stale, one fresh branch."""
    path = tmp_path / "projects" / "demo"
    repo = init_repo(path)
    make_merged_branch(repo, "merged-old", days_ago(200))
    make_unmerged_branch(repo, "unmerged-old", days_ago(200))
    make_merged_branch(repo, "merged-fresh", days_ago(2))
    return path


# ---------------------------------------------------------------------------
# Default branch detection — everything downstream depends on it
# ---------------------------------------------------------------------------


class TestDefaultBranchDetection:
    def test_main(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        assert detect_default_branch(repo) == "main"

    def test_master_not_assumed_to_be_main(self, tmp_path):
        repo = init_repo(tmp_path / "r", "master")
        make_unmerged_branch(repo, "feature", days_ago(200))
        assert detect_default_branch(repo) == "master"

    def test_remote_head_wins_over_convention(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        repo.create_head("master", repo.head.commit)
        repo.create_remote("origin", "file:///dev/null")
        repo.git.symbolic_ref("refs/remotes/origin/HEAD", "refs/remotes/origin/master")

        assert detect_default_branch(repo) == "master"

    def test_init_default_branch_config(self, tmp_path):
        repo = init_repo(tmp_path / "r", "trunk-ish")
        repo.create_head("other", repo.head.commit)
        with repo.config_writer() as cw:
            cw.set_value("init", "defaultBranch", "trunk-ish")

        assert detect_default_branch(repo) == "trunk-ish"

    def test_single_branch_is_the_default(self, tmp_path):
        repo = init_repo(tmp_path / "r", "wip")
        assert detect_default_branch(repo) == "wip"

    def test_ambiguous_returns_none(self, tmp_path):
        repo = init_repo(tmp_path / "r", "feature-a")
        repo.create_head("feature-b", repo.head.commit)

        assert detect_default_branch(repo) is None

    def test_empty_repo_returns_none(self, tmp_path):
        path = tmp_path / "empty"
        path.mkdir()
        assert detect_default_branch(Repo.init(path)) is None


class TestWorktreeBranches:
    def test_main_worktree_branch_listed(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        assert worktree_branches(repo) == {"main"}

    def test_linked_worktree_branch_listed(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        make_unmerged_branch(repo, "wt-branch", days_ago(200))
        repo.git.worktree("add", str(tmp_path / "wt"), "wt-branch")

        assert worktree_branches(repo) == {"main", "wt-branch"}


class TestUpstreamState:
    def test_no_upstream(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        assert upstream_state(repo, repo.heads["main"]) == (None, 0)

    def test_in_sync(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        branch = make_unmerged_branch(repo, "feature", days_ago(200))
        set_upstream(repo, "feature", branch.commit.hexsha)

        name, ahead = upstream_state(repo, repo.heads["feature"])
        assert name == "origin/feature"
        assert ahead == 0

    def test_unreadable_upstream_is_none(self, tmp_path):
        repo = init_repo(tmp_path / "r", "main")
        make_unmerged_branch(repo, "feature", days_ago(200))
        set_upstream(repo, "feature", None)

        assert upstream_state(repo, repo.heads["feature"])[1] is None


# ---------------------------------------------------------------------------
# Planning — who is eligible, and why
# ---------------------------------------------------------------------------


class TestEligibility:
    def test_merged_stale_branch_is_planned(self, repo_path, settings):
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)

        assert planned(response) == {"merged-old"}
        assert response.default_branch == "main"
        assert response.dry_run is True

    def test_unmerged_refused_without_opt_in(self, repo_path, settings):
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)

        info = by_name(response)["unmerged-old"]
        assert info.status == "skipped"
        assert info.merged is False
        assert "not merged into main" in info.reason
        assert "allow_unmerged_delete" in info.reason

    def test_unmerged_refused_with_request_flag_only(self, repo_path, settings):
        response = plan_branch_cleanup(
            repo_path, settings, stale_days=30, include_unmerged=True
        )

        assert "unmerged-old" not in planned(response)
        assert response.include_unmerged is False
        assert "allow_unmerged_delete" in response.message

    def test_unmerged_refused_with_config_flag_only(self, repo_path, settings):
        settings.allow_unmerged_delete = True
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)

        assert "unmerged-old" not in planned(response)

    def test_unmerged_planned_with_both_flags(self, repo_path, settings):
        settings.allow_unmerged_delete = True
        response = plan_branch_cleanup(
            repo_path, settings, stale_days=30, include_unmerged=True
        )

        assert planned(response) == {"merged-old", "unmerged-old"}
        assert "NOT merged" in by_name(response)["unmerged-old"].reason

    def test_default_branch_never_planned(self, repo_path, settings):
        settings.protected_branches = []
        settings.allow_unmerged_delete = True
        response = plan_branch_cleanup(
            repo_path, settings, stale_days=7, include_unmerged=True
        )

        assert by_name(response)["main"].reason == "the default branch"
        assert "main" not in planned(response)

    def test_protected_pattern_never_planned(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path)
        make_merged_branch(repo, "release/1.0", days_ago(300))
        make_merged_branch(repo, "develop", days_ago(300))

        response = plan_branch_cleanup(path, settings, stale_days=30)

        assert planned(response) == set()
        assert "release/*" in by_name(response)["release/1.0"].reason
        assert "develop" in by_name(response)["develop"].reason

    def test_current_branch_never_planned(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path)
        make_merged_branch(repo, "checked-out", days_ago(300))
        repo.heads["checked-out"].checkout()

        response = plan_branch_cleanup(path, settings, stale_days=30)

        assert planned(response) == set()
        assert by_name(response)["checked-out"].reason == "currently checked out"

    def test_worktree_branch_never_planned(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path)
        make_merged_branch(repo, "in-worktree", days_ago(300))
        repo.git.worktree("add", str(tmp_path / "wt"), "in-worktree")

        response = plan_branch_cleanup(path, settings, stale_days=30)

        assert planned(response) == set()
        assert by_name(response)["in-worktree"].reason == "checked out in a worktree"

    def test_branch_ahead_of_upstream_never_planned(self, tmp_path, settings):
        """Merged and stale, but holding a commit the remote has not seen."""
        path = tmp_path / "projects" / "p"
        repo = init_repo(path)
        branch = make_merged_branch(repo, "pushed-partly", days_ago(300))
        parent = branch.commit.parents[0]
        set_upstream(repo, "pushed-partly", parent.hexsha)

        response = plan_branch_cleanup(path, settings, stale_days=30)
        info = by_name(response)["pushed-partly"]

        assert info.merged is True
        assert info.ahead == 1
        assert info.status == "skipped"
        assert "not present on upstream origin/pushed-partly" in info.reason

    def test_unreadable_upstream_is_reported_not_deleted(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path)
        make_merged_branch(repo, "ghost-upstream", days_ago(300))
        set_upstream(repo, "ghost-upstream", None)

        response = plan_branch_cleanup(path, settings, stale_days=30)
        info = by_name(response)["ghost-upstream"]

        assert info.status == "skipped"
        assert info.ahead is None
        assert "could not be read" in info.reason

    def test_no_default_branch_plans_nothing(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path, "feature-a")
        repo.create_head("feature-b", repo.head.commit)

        response = plan_branch_cleanup(path, settings, stale_days=30)

        assert planned(response) == set()
        assert response.default_branch == ""
        assert "default branch could not be determined" in response.message

    def test_not_a_repo_is_refused(self, tmp_path, settings):
        (tmp_path / "plain").mkdir()
        with pytest.raises(BranchActionError) as exc:
            plan_branch_cleanup(tmp_path / "plain", settings, stale_days=30)
        assert exc.value.status_code == 400

    def test_every_branch_appears_in_the_manifest(self, repo_path, settings):
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)

        assert response.total_branches == 4
        assert set(by_name(response)) == {
            "main", "merged-old", "unmerged-old", "merged-fresh",
        }
        assert all(info.reason for info in response.branches)
        assert all(info.last_commit_sha for info in response.branches)
        assert all(info.last_commit_at for info in response.branches)


class TestStalenessBoundary:
    @pytest.mark.parametrize(
        ("age", "threshold", "eligible"),
        [(30, 30, True), (31, 30, True), (29, 30, False), (10, 30, False)],
    )
    def test_threshold_boundary(self, tmp_path, settings, age, threshold, eligible):
        path = tmp_path / "projects" / f"p{age}"
        repo = init_repo(path)
        make_merged_branch(repo, "candidate", days_ago(age))

        response = plan_branch_cleanup(path, settings, stale_days=threshold)

        assert ("candidate" in planned(response)) is eligible

    def test_stale_days_below_config_floor_refused(self, repo_path, settings):
        with pytest.raises(BranchActionError) as exc:
            plan_branch_cleanup(repo_path, settings, stale_days=1)

        assert exc.value.status_code == 400
        assert "min_stale_days" in str(exc.value)

    def test_config_floor_boundary_accepted(self, repo_path, settings):
        assert plan_branch_cleanup(repo_path, settings, stale_days=7) is not None


class TestMaxDeletionsCap:
    @pytest.fixture
    def many(self, tmp_path):
        path = tmp_path / "projects" / "many"
        repo = init_repo(path)
        for index in range(5):
            make_merged_branch(repo, f"old-{index}", days_ago(300 - index))
        return path

    def test_cap_from_config(self, many, settings):
        settings.max_deletions = 2
        response = plan_branch_cleanup(many, settings, stale_days=30)

        assert len(planned(response)) == 2
        assert response.truncated is True
        assert response.max_deletions == 2
        capped = [b for b in response.branches if "max_deletions cap" in b.reason]
        assert len(capped) == 3

    def test_request_may_lower_the_cap(self, many, settings):
        response = plan_branch_cleanup(many, settings, stale_days=30, max_deletions=1)

        assert len(planned(response)) == 1
        assert response.max_deletions == 1

    def test_request_may_not_raise_the_cap(self, many, settings):
        settings.max_deletions = 2
        response = plan_branch_cleanup(many, settings, stale_days=30, max_deletions=99)

        assert len(planned(response)) == 2
        assert response.max_deletions == 2

    def test_cap_keeps_the_stalest_branches(self, many, settings):
        settings.max_deletions = 2
        response = plan_branch_cleanup(many, settings, stale_days=30)

        # old-0 is the oldest tip, old-4 the youngest.
        assert planned(response) == {"old-0", "old-1"}

    def test_zero_cap_plans_nothing(self, many, settings):
        response = plan_branch_cleanup(many, settings, stale_days=30, max_deletions=0)

        assert planned(response) == set()
        assert response.truncated is True

    def test_negative_cap_refused(self, many, settings):
        with pytest.raises(BranchActionError):
            plan_branch_cleanup(many, settings, stale_days=30, max_deletions=-1)

    def test_no_truncation_when_under_cap(self, repo_path, settings):
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)
        assert response.truncated is False


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


class TestExecution:
    def test_planning_alone_deletes_nothing(self, repo_path, settings):
        before = branch_shas(repo_path)

        plan_branch_cleanup(repo_path, settings, stale_days=30)

        assert branch_shas(repo_path) == before

    def test_confirm_deletes_exactly_the_previewed_set(self, repo_path, settings):
        before = branch_shas(repo_path)
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)
        preview = planned(plan)

        result = execute_branch_cleanup(plan, repo_path, settings)

        assert deleted(result) == preview == {"merged-old"}
        assert result.dry_run is False
        assert result.deleted_count == 1
        assert set(branch_shas(repo_path)) == set(before) - preview

    def test_deleted_row_records_the_recovery_sha(self, repo_path, settings):
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)
        sha = by_name(plan)["merged-old"].last_commit_sha

        result = execute_branch_cleanup(plan, repo_path, settings)

        assert by_name(result)["merged-old"].last_commit_sha == sha
        assert "branch <name> <last_commit_sha>" in result.message
        # The commit itself is still reachable, so the branch can come back.
        Repo(repo_path).create_head("merged-old", sha)

    def test_unmerged_survives_a_confirmed_run(self, repo_path, settings):
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)

        execute_branch_cleanup(plan, repo_path, settings)

        assert "unmerged-old" in branch_shas(repo_path)

    def test_unmerged_deleted_only_with_both_flags(self, repo_path, settings):
        settings.allow_unmerged_delete = True
        plan = plan_branch_cleanup(
            repo_path, settings, stale_days=30, include_unmerged=True
        )

        result = execute_branch_cleanup(
            plan, repo_path, settings, include_unmerged=True
        )

        assert deleted(result) == {"merged-old", "unmerged-old"}
        assert "unmerged-old" not in branch_shas(repo_path)

    def test_execution_re_checks_the_config_flag(self, repo_path, settings):
        """A plan built with the flag on must not run once config says no."""
        settings.allow_unmerged_delete = True
        plan = plan_branch_cleanup(
            repo_path, settings, stale_days=30, include_unmerged=True
        )
        settings.allow_unmerged_delete = False

        result = execute_branch_cleanup(
            plan, repo_path, settings, include_unmerged=True
        )

        assert deleted(result) == {"merged-old"}
        assert "unmerged-old" in branch_shas(repo_path)
        assert "no longer eligible" in by_name(result)["unmerged-old"].reason

    def test_branch_that_moved_since_the_preview_is_skipped(self, repo_path, settings):
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)
        repo = Repo(repo_path)
        repo.heads["merged-old"].checkout()
        commit(repo, "surprise.txt", days_ago(300))
        repo.heads["main"].checkout()

        result = execute_branch_cleanup(plan, repo_path, settings)

        assert deleted(result) == set()
        assert "merged-old" in branch_shas(repo_path)

    def test_branch_checked_out_since_the_preview_is_skipped(self, repo_path, settings):
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)
        Repo(repo_path).heads["merged-old"].checkout()

        result = execute_branch_cleanup(plan, repo_path, settings)

        assert deleted(result) == set()
        assert "currently checked out" in by_name(result)["merged-old"].reason

    def test_branch_deleted_elsewhere_is_skipped(self, repo_path, settings):
        plan = plan_branch_cleanup(repo_path, settings, stale_days=30)
        Repo(repo_path).delete_head("merged-old", force=True)

        result = execute_branch_cleanup(plan, repo_path, settings)

        assert result.deleted_count == 0
        assert by_name(result)["merged-old"].reason == "branch no longer exists"

    def test_capped_rows_are_not_deleted(self, tmp_path, settings):
        path = tmp_path / "projects" / "many"
        repo = init_repo(path)
        for index in range(4):
            make_merged_branch(repo, f"old-{index}", days_ago(300 - index))
        settings.max_deletions = 2

        plan = plan_branch_cleanup(path, settings, stale_days=30)
        result = execute_branch_cleanup(plan, path, settings)

        assert len(deleted(result)) == 2
        assert {"old-2", "old-3"} <= set(branch_shas(path))

    def test_execution_refuses_without_a_default_branch(self, tmp_path, settings):
        path = tmp_path / "projects" / "p"
        repo = init_repo(path, "feature-a")
        repo.create_head("feature-b", repo.head.commit)
        plan = plan_branch_cleanup(path, settings, stale_days=30)
        # Force a row through as if a plan had been fabricated by a caller.
        plan.branches[0].status = "planned"

        result = execute_branch_cleanup(plan, path, settings)

        assert result.deleted_count == 0
        assert len(branch_shas(path)) == 2


# ---------------------------------------------------------------------------
# Path confinement
# ---------------------------------------------------------------------------


class TestPathConfinement:
    def test_directory_under_root_resolves(self, tmp_path):
        root = tmp_path / "projects"
        (root / "demo").mkdir(parents=True)

        assert resolve_project_repo("demo", root) == (root / "demo").resolve()

    @pytest.mark.parametrize("name", ["..", ".", "../etc", "/etc", "a/b", "", "a\\b"])
    def test_traversal_names_refused(self, tmp_path, name):
        root = tmp_path / "projects"
        root.mkdir()

        with pytest.raises(BranchActionError) as exc:
            resolve_project_repo(name, root)
        assert exc.value.status_code in (400, 404)

    def test_managed_path_outside_root_refused(self, tmp_path):
        root = tmp_path / "projects"
        root.mkdir()
        outside = tmp_path / "elsewhere" / "secret"
        outside.mkdir(parents=True)

        with pytest.raises(BranchActionError) as exc:
            resolve_project_repo("secret", root, {"secret": str(outside)})

        assert exc.value.status_code == 400
        assert "outside" in str(exc.value)

    def test_symlink_escaping_root_refused(self, tmp_path):
        root = tmp_path / "projects"
        root.mkdir()
        outside = tmp_path / "elsewhere"
        outside.mkdir()
        (root / "link").symlink_to(outside)

        with pytest.raises(BranchActionError) as exc:
            resolve_project_repo("link", root)
        assert exc.value.status_code == 400

    def test_managed_name_maps_to_its_path(self, tmp_path):
        root = tmp_path / "projects"
        (root / "RealDir").mkdir(parents=True)

        resolved = resolve_project_repo(
            "friendly-name", root, {"friendly-name": str(root / "RealDir")}
        )

        assert resolved == (root / "RealDir").resolve()

    def test_missing_project_is_404(self, tmp_path):
        root = tmp_path / "projects"
        root.mkdir()

        with pytest.raises(BranchActionError) as exc:
            resolve_project_repo("nope", root)
        assert exc.value.status_code == 404

    def test_root_itself_refused(self, tmp_path):
        root = tmp_path / "projects"
        root.mkdir()

        with pytest.raises(BranchActionError):
            resolve_project_repo("x", root, {"x": str(root)})


# ---------------------------------------------------------------------------
# Contract round-trip
# ---------------------------------------------------------------------------


class TestManifestContract:
    def test_response_round_trips(self, repo_path, settings):
        response = plan_branch_cleanup(repo_path, settings, stale_days=30)

        assert BranchCleanupResponse.from_dict(response.model_dump()) == response

    def test_missing_fields_default(self):
        parsed = BranchCleanupResponse.from_dict({})
        assert parsed.dry_run is True
        assert parsed.branches == []

    def test_branch_info_tolerates_unknown_fields(self):
        parsed = BranchInfo.from_dict({"name": "x", "surprise": 1})
        assert parsed.name == "x"
        assert parsed.status == "skipped"


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

PRUNE = "/api/projects/demo/branches/prune"


@pytest.fixture
def prune_client(mock_config, test_client, tmp_path):
    """The real app with the projects root pointed at a temp tree."""
    root = tmp_path / "projects"
    root.mkdir(parents=True, exist_ok=True)
    mock_config.agents.project_organiser.projects_root = str(root)
    mock_config.agents.project_organiser.stale_branch_days = 30
    return test_client


@pytest.fixture
def api_repo(prune_client, tmp_path):
    path = tmp_path / "projects" / "demo"
    repo = init_repo(path)
    make_merged_branch(repo, "merged-old", days_ago(200))
    make_unmerged_branch(repo, "unmerged-old", days_ago(200))
    return path


class TestPruneApi:
    async def test_requires_auth(self, mock_config, prune_client, api_repo):
        mock_config.api.auth_token = "secret-token"
        try:
            response = await prune_client.post(PRUNE, json={"confirm": True})
            assert response.status_code == 401
            assert response.headers.get("WWW-Authenticate") == "Bearer"
        finally:
            mock_config.api.auth_token = None
        assert "merged-old" in branch_shas(api_repo)

    async def test_get_not_allowed(self, prune_client, api_repo):
        assert (await prune_client.get(PRUNE)).status_code == 405

    async def test_defaults_to_dry_run(self, prune_client, api_repo):
        before = branch_shas(api_repo)

        payload = (await prune_client.post(PRUNE, json={})).json()

        assert payload["dry_run"] is True
        assert "dry run" in payload["message"]
        assert payload["planned_count"] == 1
        assert branch_shas(api_repo) == before

    async def test_empty_body_allowed(self, prune_client, api_repo):
        assert (await prune_client.post(PRUNE)).status_code == 200

    async def test_manifest_shape(self, prune_client, api_repo):
        payload = (await prune_client.post(PRUNE, json={})).json()

        assert payload["project"] == "demo"
        assert payload["repo_path"] == str(api_repo)
        assert payload["default_branch"] == "main"
        assert payload["stale_days"] == 30
        assert payload["total_branches"] == 3
        row = next(b for b in payload["branches"] if b["name"] == "merged-old")
        assert row["status"] == "planned"
        assert row["merged"] is True
        assert row["days_stale"] >= 200
        assert len(row["last_commit_sha"]) == 40
        assert row["last_commit_at"]

    async def test_confirm_deletes(self, prune_client, api_repo):
        payload = (await prune_client.post(PRUNE, json={"confirm": True})).json()

        assert payload["dry_run"] is False
        assert payload["deleted_count"] == 1
        assert "merged-old" not in branch_shas(api_repo)
        assert "unmerged-old" in branch_shas(api_repo)

    async def test_unmerged_needs_config_too(self, prune_client, api_repo):
        payload = (
            await prune_client.post(
                PRUNE, json={"confirm": True, "include_unmerged": True}
            )
        ).json()

        assert payload["deleted_count"] == 1
        assert "unmerged-old" in branch_shas(api_repo)

    async def test_unmerged_with_both_flags(self, mock_config, prune_client, api_repo):
        mock_config.agents.project_organiser.branch_actions.allow_unmerged_delete = True
        try:
            payload = (
                await prune_client.post(
                    PRUNE, json={"confirm": True, "include_unmerged": True}
                )
            ).json()
        finally:
            settings = mock_config.agents.project_organiser.branch_actions
            settings.allow_unmerged_delete = False

        assert payload["deleted_count"] == 2
        assert "unmerged-old" not in branch_shas(api_repo)

    async def test_kill_switch_is_409(self, mock_config, prune_client, api_repo):
        mock_config.agents.project_organiser.branch_actions.enabled = False
        try:
            response = await prune_client.post(PRUNE, json={"confirm": True})
        finally:
            mock_config.agents.project_organiser.branch_actions.enabled = True

        assert response.status_code == 409
        assert "merged-old" in branch_shas(api_repo)

    async def test_unknown_project_is_404(self, prune_client, api_repo):
        response = await prune_client.post(
            "/api/projects/does-not-exist/branches/prune", json={}
        )
        assert response.status_code == 404

    async def test_stale_days_below_floor_is_400(self, prune_client, api_repo):
        response = await prune_client.post(PRUNE, json={"stale_days": 1})

        assert response.status_code == 400
        assert "min_stale_days" in response.json()["detail"]
        assert "merged-old" in branch_shas(api_repo)

    async def test_request_cap_is_honoured(self, prune_client, api_repo):
        payload = (
            await prune_client.post(PRUNE, json={"max_deletions": 0, "confirm": True})
        ).json()

        assert payload["deleted_count"] == 0
        assert "merged-old" in branch_shas(api_repo)

    async def test_non_repo_directory_is_400(self, prune_client, tmp_path):
        (tmp_path / "projects" / "plain").mkdir(parents=True)

        response = await prune_client.post(
            "/api/projects/plain/branches/prune", json={}
        )
        assert response.status_code == 400

    async def test_managed_project_name_resolves(
        self, mock_config, prune_client, tmp_path
    ):
        from sysadmin.core.config import ManagedProject

        path = tmp_path / "projects" / "RealDir"
        repo = init_repo(path)
        make_merged_branch(repo, "merged-old", days_ago(200))
        mock_config.projects.projects = [
            ManagedProject(name="friendly", path=str(path))
        ]
        try:
            payload = (
                await prune_client.post(
                    "/api/projects/friendly/branches/prune", json={}
                )
            ).json()
        finally:
            mock_config.projects.projects = []

        assert payload["repo_path"] == str(path)
        assert payload["planned_count"] == 1


def test_module_never_touches_the_real_projects_root():
    """Sanity guard: nothing in this module hard-codes a real repo path."""
    source = Path(branch_actions.__file__).read_text()
    assert "/home/gaddi" not in source
