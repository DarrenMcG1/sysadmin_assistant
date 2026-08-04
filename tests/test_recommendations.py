"""Tests for the recommendations engine (Session 22).

The engine mirrors the scorer's deductions, so these tests cross-check
the arithmetic: every ``points`` value here matches the deduction in
``ProjectOrganiserAgent._analyse_project`` for the same finding.
"""

from sysadmin.config import ProjectOrganiserConfig
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.services.recommendations import (
    potential_score,
    recommendations_for,
)


def make_snapshot(score=100, findings=None, name="demo"):
    return ProjectSnapshot(
        project_name=name,
        project_path=f"/projects/{name}",
        health_score=score,
        findings=findings or {},
    )


def agent_config(**overrides):
    return ProjectOrganiserConfig(**overrides)


class TestIndividualRules:
    def test_healthy_project_gets_no_advice(self):
        recs = recommendations_for(make_snapshot(), agent_config())
        assert recs == []

    def test_missing_docs(self):
        snapshot = make_snapshot(
            80, {"missing_readme": True, "missing_claude_md": True}
        )
        recs = recommendations_for(snapshot, agent_config())

        assert len(recs) == 2
        assert all(r.kind == "docs" and r.points == 10 for r in recs)
        assert potential_score(snapshot, recs) == 100

    def test_missing_env(self):
        recs = recommendations_for(
            make_snapshot(90, {"missing_env": True}), agent_config()
        )
        assert recs[0].kind == "config"
        assert recs[0].points == 10

    def test_stale_git_lock(self):
        recs = recommendations_for(
            make_snapshot(95, {"stale_git_lock": True}), agent_config()
        )
        assert recs[0].points == 5

    def test_stale_node_modules_detail_carries_age(self):
        recs = recommendations_for(
            make_snapshot(95, {"stale_node_modules": "120 days old"}),
            agent_config(),
        )
        assert recs[0].points == 5
        assert "120 days old" in recs[0].detail

    def test_stale_branches_points_capped_at_five_branches(self):
        # Real shape: get_stale_branches records dicts, not names
        branches = [
            {"name": f"b{i}", "last_commit": "2026-01-01T00:00:00", "days_stale": 90}
            for i in range(8)
        ]
        recs = recommendations_for(
            make_snapshot(75, {"stale_branches": branches}), agent_config()
        )

        assert recs[0].kind == "git"
        assert recs[0].points == 25  # 5 × min(8, 5)
        assert "prune" in recs[0].action.lower()
        assert "b0" in recs[0].detail
        assert "…" in recs[0].detail  # only 5 names listed

    def test_stale_branches_tolerates_plain_strings(self):
        recs = recommendations_for(
            make_snapshot(95, {"stale_branches": ["old-branch"]}), agent_config()
        )
        assert recs[0].points == 5
        assert "old-branch" in recs[0].detail

    def test_staleness_active_project(self):
        recs = recommendations_for(
            make_snapshot(85, {"stale": "No commits in 90 days"}), agent_config()
        )
        assert recs[0].kind == "activity"
        assert recs[0].points == 15
        assert "dormant" in recs[0].action

    def test_aging_active_project(self):
        recs = recommendations_for(
            make_snapshot(90, {"aging": "No commits in 45 days"}), agent_config()
        )
        assert recs[0].points == 10

    def test_todo_points_from_counts(self):
        snapshot = make_snapshot(90, {"todos": {"TODO": 20, "FIXME": 5}})
        recs = recommendations_for(snapshot, agent_config())

        assert recs[0].kind == "todos"
        assert recs[0].points == 10  # 5 × (25 // 10)
        assert "25" in recs[0].title

    def test_todo_points_prefer_recorded_capped_penalty(self):
        snapshot = make_snapshot(
            70,
            {
                "todos": {"TODO": 330, "FIXME": 40},
                "todo_penalty_capped": {
                    "raw_penalty": 185,
                    "applied_penalty": 30,
                    "total_markers": 370,
                },
            },
        )
        recs = recommendations_for(snapshot, agent_config())
        assert recs[0].points == 30

    def test_no_remote_is_risk_with_zero_points(self):
        recs = recommendations_for(
            make_snapshot(100, {"no_remote": True}), agent_config()
        )
        assert recs[0].severity == "risk"
        assert recs[0].points == 0


class TestStatusAwareness:
    def test_archived_gets_no_branch_or_staleness_advice(self):
        snapshot = make_snapshot(
            100,
            {
                "status": "archived",
                "stale_branches": ["a", "b"],
                "stale": "No commits in 400 days",
            },
        )
        assert recommendations_for(snapshot, agent_config()) == []

    def test_dormant_skips_staleness_but_keeps_branches(self):
        snapshot = make_snapshot(
            95,
            {
                "status": "dormant",
                "stale_branches": ["a"],
                "stale": "No commits in 90 days",
            },
        )
        recs = recommendations_for(snapshot, agent_config())

        assert [r.kind for r in recs] == ["git"]

    def test_archived_still_advised_on_untidiness(self):
        snapshot = make_snapshot(
            90, {"status": "archived", "stale_git_lock": True, "no_remote": True}
        )
        recs = recommendations_for(snapshot, agent_config())

        assert {r.kind for r in recs} == {"risk", "hygiene"}


class TestRanking:
    def test_risk_outranks_bigger_point_items(self):
        snapshot = make_snapshot(
            75, {"no_remote": True, "stale": "No commits in 90 days"}
        )
        recs = recommendations_for(snapshot, agent_config())

        assert recs[0].severity == "risk"
        assert recs[1].points == 15

    def test_advice_sorted_by_points_descending(self):
        snapshot = make_snapshot(
            70,
            {
                "stale_git_lock": True,       # 5
                "stale": "No commits in 90 days",  # 15
                "missing_readme": True,       # 10
            },
        )
        recs = recommendations_for(snapshot, agent_config())
        assert [r.points for r in recs] == [15, 10, 5]

    def test_potential_score_clamped_to_100(self):
        findings = {
            "missing_readme": True,
            "missing_claude_md": True,
            "missing_env": True,
            "stale": "No commits in 200 days",
            "stale_branches": ["a", "b", "c", "d", "e", "f"],
            "todos": {"TODO": 100},
            "stale_git_lock": True,
        }
        snapshot = make_snapshot(0, findings)
        recs = recommendations_for(snapshot, agent_config())

        assert sum(r.points for r in recs) > 100
        assert potential_score(snapshot, recs) == 100
