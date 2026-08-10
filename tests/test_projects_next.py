"""GET /api/projects/next — one project, one action, one reason.

The board can be wrong in a small way and stay useful: a consumer sees
six rows and picks. This endpoint picks *for* the consumer, so the tests
that matter are the ones pinning the choice and the sentence that
defends it — and, above all, the unit the choice is made in.

**Why so much weight on days-not-scans.** The scan series is irregular
by construction (6-hourly until Session 35, daily from the timer since,
plus manual scans — the live table holds two scans 17 minutes apart on
2026-08-08). Ranking on run length in scans would have looked correct in
every fixture written with an even cadence, and on live data would have
ranked by how often the organiser happened to run. That failure mode is
only visible if a test says so out loud, which is what
``test_bunched_scans_do_not_inflate_the_streak`` is for.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.next_action import (
    Candidate,
    Streak,
    build_reason,
    choose,
    streak_days,
)
from sysadmin.projects.roadmap import looks_like_no_action
from sysadmin.projects.snapshots import action_history_query

NOW = datetime.now(UTC)


def ago(days=0, hours=0, minutes=0):
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)


def make_snapshot(
    name="demo",
    score=90,
    status="active",
    next_action="Wire the drain retry path",
    source="handoff",
    last_commit_days=1,
    open_tasks=3,
    open_snags=1,
):
    roadmap = {
        "next_action": next_action,
        "next_action_source": source,
        "open_tasks": open_tasks,
        "open_snags": open_snags,
    }
    return ProjectSnapshot(
        project_name=name,
        project_path=f"/home/gaddi/projects/{name}",
        health_score=score,
        last_commit_at=(
            ago(days=last_commit_days) if last_commit_days is not None else None
        ),
        scanned_at=NOW,
        findings={"status": status, "roadmap": roadmap},
    )


def stub_two_queries(session, snapshots, history):
    """The route executes twice: latest snapshots, then the action series."""
    latest = MagicMock()
    latest.scalars.return_value.all.return_value = snapshots
    series = MagicMock()
    series.all.return_value = history
    session.execute.side_effect = [latest, series]


def candidate(name="demo", days_since_commit=1):
    return Candidate(
        name=name,
        path=f"/home/gaddi/projects/{name}",
        next_action="Wire the drain retry path",
        next_action_source="handoff",
        health_score=90,
        days_since_commit=days_since_commit,
        open_tasks=3,
        open_snags=1,
        scanned_at=NOW,
    )


class TestStreakDays:
    def test_no_history_is_zero_and_unknown(self):
        """Not a measurement of zero: nothing was observed at all."""
        streak = streak_days([])
        assert streak == Streak(days=0, since=None, scans=0, at_window_edge=True)

    def test_one_observation_cannot_prove_a_streak(self):
        streak = streak_days([(NOW, "Ship the parser")])
        assert streak.days == 0
        assert streak.scans == 1
        assert streak.at_window_edge is True

    def test_run_is_measured_in_elapsed_days(self):
        points = [
            (NOW, "Ship the parser"),
            (ago(days=1), "Ship the parser"),
            (ago(days=3), "Ship the parser"),
            (ago(days=4), "Write the parser"),
        ]
        streak = streak_days(points)

        assert streak.days == 3
        assert streak.scans == 3
        assert streak.since == ago(days=3)
        assert streak.at_window_edge is False

    def test_bunched_scans_do_not_inflate_the_streak(self):
        """Four scans in one hour is one day's evidence, not four."""
        points = [
            (NOW, "Ship the parser"),
            (ago(minutes=17), "Ship the parser"),
            (ago(minutes=34), "Ship the parser"),
            (ago(minutes=51), "Ship the parser"),
            (ago(days=2), "Write the parser"),
        ]
        streak = streak_days(points)

        assert streak.days == 0
        assert streak.scans == 4

    def test_only_the_current_spell_counts(self):
        """A → B → A is a resumed action, not one that never moved."""
        points = [
            (NOW, "Ship the parser"),
            (ago(days=1), "Fix the migration"),
            (ago(days=30), "Ship the parser"),
        ]
        streak = streak_days(points)

        assert streak.days == 0
        assert streak.scans == 1
        assert streak.at_window_edge is False

    def test_run_reaching_the_oldest_row_is_flagged(self):
        points = [
            (NOW, "Ship the parser"),
            (ago(days=40), "Ship the parser"),
        ]
        streak = streak_days(points)

        assert streak.days == 40
        assert streak.at_window_edge is True

    def test_missing_action_still_forms_a_run(self):
        """``None`` compares like any other value — no crash, no special case."""
        streak = streak_days([(NOW, None), (ago(days=2), None)])
        assert streak.days == 2


class TestLooksLikeNoAction:
    @pytest.mark.parametrize("text", [
        "No unchecked task found — set one before the next session.",
        "None",
        "none.",
        "N/A",
        "Nothing",
        "—",
        "Nothing left to do",
        "No next actions recorded",
        "_Task 1_",
        "",
        "   ",
        None,
    ])
    def test_recognised_as_no_action(self, text):
        assert looks_like_no_action(text) is True

    @pytest.mark.parametrize("text", [
        "Wire the drain retry path",
        # Starts with a bare-word form and is real work. The whole-line
        # anchor exists for exactly this line.
        "None of the migrations are applied to the live database",
        "Nothing in the parser handles a missing header — add one",
        "There is no task runner configured; pick one",
        "Session 24: File organiser tiers — disk instead of portfolio",
    ])
    def test_real_work_survives(self, text):
        assert looks_like_no_action(text) is False


class TestChooseAndReason:
    def test_longest_stuck_wins(self):
        candidates = [candidate("warm", 0), candidate("stuck", 9)]
        streaks = {
            "warm": Streak(days=1, since=ago(days=1), scans=2, at_window_edge=False),
            "stuck": Streak(days=6, since=ago(days=6), scans=6, at_window_edge=False),
        }
        winner, streak, reason = choose(candidates, streaks, {})

        assert winner is not None and winner.name == "stuck"
        assert streak is not None and streak.days == 6
        assert "longer than any other active project" in reason

    def test_tie_breaks_on_the_most_recent_commit(self):
        candidates = [candidate("cold", 12), candidate("warm", 1)]
        tied = Streak(days=3, since=ago(days=3), scans=3, at_window_edge=False)
        winner, _, reason = choose(candidates, {"cold": tied, "warm": tied}, {})

        assert winner is not None and winner.name == "warm"
        assert "level with 1 other project" in reason
        assert "committed to most recently" in reason

    def test_never_committed_loses_the_tie_break(self):
        """Unknown is not recent — and it is not urgent either."""
        candidates = [candidate("never", None), candidate("warm", 4)]
        tied = Streak(days=3, since=ago(days=3), scans=3, at_window_edge=False)
        winner, _, _ = choose(candidates, {"never": tied, "warm": tied}, {})

        assert winner is not None and winner.name == "warm"

    def test_window_edge_hedges_the_number(self):
        streak = Streak(days=88, since=ago(days=88), scans=40, at_window_edge=True)
        reason = build_reason(
            (candidate("old"), streak),
            [(candidate("old"), streak), (candidate("other", 2), Streak(1, NOW, 2, False))],
        )
        assert "at least 88 days" in reason

    def test_everything_moved_says_so_rather_than_claiming_a_streak(self):
        candidates = [candidate("a", 1), candidate("b", 5)]
        fresh = Streak(days=0, since=NOW, scans=1, at_window_edge=False)
        winner, _, reason = choose(candidates, {"a": fresh, "b": fresh}, {})

        assert winner is not None and winner.name == "a"
        assert "moved on at the last scan" in reason

    def test_single_candidate_does_not_claim_it_beat_anything(self):
        streak = Streak(days=2, since=ago(days=2), scans=3, at_window_edge=False)
        _, _, reason = choose([candidate("only")], {"only": streak}, {})

        assert "only active project with a stated next action" in reason
        assert "longer than any other" not in reason

    def test_missing_streak_is_treated_as_unmeasured(self):
        """A candidate with no history rows must not crash the ranking."""
        winner, streak, _ = choose([candidate("new")], {}, {})

        assert winner is not None and winner.name == "new"
        assert streak is not None and streak.at_window_edge is True

    def test_empty_reasons_distinguish_never_scanned_from_nothing_queued(self):
        _, _, never = choose([], {}, {})
        _, _, quiet = choose([], {}, {"says_no_action": 2, "no_action": 1})

        assert never == "No project scan has been recorded yet."
        assert "2 record that there is nothing queued" in quiet
        assert "1 have no stated next action" in quiet


@pytest.mark.anyio
class TestNextEndpoint:
    async def test_returns_one_project_with_its_reason(
        self, test_client, mock_session
    ):
        stub_two_queries(
            mock_session,
            [make_snapshot(name="venture-assistant")],
            [
                ("venture-assistant", NOW, "Wire the drain retry path"),
                ("venture-assistant", ago(days=2), "Wire the drain retry path"),
                ("venture-assistant", ago(days=3), "Read the scoring sample"),
            ],
        )

        resp = await test_client.get("/api/projects/next")
        assert resp.status_code == 200
        body = resp.json()

        assert body["project"]["name"] == "venture-assistant"
        assert body["project"]["days_unchanged"] == 2
        assert body["project"]["unchanged_scans"] == 2
        assert body["project"]["at_window_edge"] is False
        assert body["reason"]
        assert body["considered"] == 1

    async def test_git_sourced_action_is_not_work(self, test_client, mock_session):
        """A commit subject records the past; it is not an instruction."""
        stub_two_queries(
            mock_session,
            [make_snapshot(name="terrible", source="git")],
            [],
        )

        body = (await test_client.get("/api/projects/next")).json()

        assert body["project"] is None
        assert body["skipped"] == {"source_git": 1}
        assert body["considered"] == 0

    async def test_dormant_projects_are_not_candidates(
        self, test_client, mock_session
    ):
        stub_two_queries(
            mock_session, [make_snapshot(name="daiy", status="dormant")], []
        )
        body = (await test_client.get("/api/projects/next")).json()

        assert body["project"] is None
        assert body["skipped"] == {"inactive": 1}

    async def test_a_handoff_saying_nothing_is_queued_is_counted_apart(
        self, test_client, mock_session
    ):
        """The live case: two estate handoffs say there is no next action."""
        stub_two_queries(
            mock_session,
            [
                make_snapshot(
                    name="Alfred",
                    next_action="No unchecked task found — set one before the "
                                "next session.",
                ),
                make_snapshot(name="Athenaeum", next_action=None, source=None),
            ],
            [],
        )

        body = (await test_client.get("/api/projects/next")).json()

        assert body["project"] is None
        assert body["skipped"] == {"says_no_action": 1, "no_action": 1}
        assert "nothing queued" in body["reason"]
        assert "have no stated next action" in body["reason"]

    async def test_exclude_defers_a_suggestion_without_re_rolling_it(
        self, test_client, mock_session
    ):
        stub_two_queries(
            mock_session,
            [make_snapshot(name="a", last_commit_days=1),
             make_snapshot(name="b", last_commit_days=2)],
            [
                ("b", NOW, "Wire the drain retry path"),
                ("b", ago(days=1), "Wire the drain retry path"),
            ],
        )

        body = (await test_client.get("/api/projects/next?exclude=a")).json()

        assert body["project"]["name"] == "b"
        assert body["excluded"] == ["a"]
        assert body["skipped"]["excluded"] == 1

    async def test_exclude_is_repeatable(self, test_client, mock_session):
        stub_two_queries(
            mock_session,
            [make_snapshot(name="a"), make_snapshot(name="b")],
            [],
        )

        body = (
            await test_client.get("/api/projects/next?exclude=a&exclude=b")
        ).json()

        assert body["project"] is None
        assert body["excluded"] == ["a", "b"]
        assert body["skipped"]["excluded"] == 2

    async def test_empty_estate_is_200_not_404(self, test_client, mock_session):
        """404 would collapse "nothing to do" into "never scanned"."""
        stub_two_queries(mock_session, [], [])

        resp = await test_client.get("/api/projects/next")

        assert resp.status_code == 200
        body = resp.json()
        assert body["project"] is None
        assert body["reason"] == "No project scan has been recorded yet."
        assert body["skipped"] == {}

    async def test_next_is_not_captured_as_a_project_name(
        self, test_client, mock_session
    ):
        """Regression: /next must stay declared before /{name}."""
        stub_two_queries(mock_session, [], [])

        body = (await test_client.get("/api/projects/next")).json()

        assert "reason" in body
        assert "history" not in body

    async def test_history_is_only_fetched_for_candidates(
        self, test_client, mock_session
    ):
        """No second query at all when nothing qualifies."""
        latest = MagicMock()
        latest.scalars.return_value.all.return_value = [
            make_snapshot(name="daiy", status="dormant")
        ]
        mock_session.execute.side_effect = [latest]

        resp = await test_client.get("/api/projects/next")

        assert resp.status_code == 200
        assert mock_session.execute.await_count == 1


class TestActionHistoryQuery:
    """Compiled SQL, for the same reason the freshness guard uses it: the
    suite has no live database, so the shape of the statement is the
    honest thing to assert."""

    def _sql(self, query):
        return str(query.compile(dialect=postgresql.dialect()))

    def test_reads_one_json_field_not_whole_rows(self):
        sql = self._sql(action_history_query(["demo"]))

        # ``findings['roadmap'] ->> 'next_action'`` — extracted by the
        # database, so one string comes back per scan.
        assert "project_snapshots.findings[" in sql
        assert "->>" in sql
        assert "AS next_action" in sql
        # The blob itself must not be selected — it is kilobytes per row
        # across every scan in the window.
        assert "project_snapshots.findings," not in sql

    def test_window_is_anchored_to_the_newest_scan(self):
        """Anchoring to now() would un-stick actions while nothing scanned."""
        sql = self._sql(action_history_query(["demo"]))

        assert "max(sysadmin.project_snapshots.scanned_at)" in sql
        assert "scanned_at >= (SELECT max" in sql

    def test_ordered_newest_first_per_project(self):
        sql = self._sql(action_history_query(["demo"]))

        assert "ORDER BY sysadmin.project_snapshots.project_name, " \
               "sysadmin.project_snapshots.scanned_at DESC" in sql

    def test_no_names_selects_no_rows_rather_than_every_project(self):
        sql = self._sql(action_history_query([]))

        assert "IN (" in sql
