"""Tests for GET /api/projects/board and the roadmap recommendations.

The board is the estate's answer to "what do I pick up", so the rules
worth pinning are the ones about *honesty*: where a next action came
from, when it stops being current, and what happens to a project that
keeps no roadmap documents at all.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from sysadmin.core.config import ProjectOrganiserConfig
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.recommendations import (
    STALLED_HANDOFF_DAYS,
    recommendations_for,
)


def make_snapshot(
    name="demo",
    score=90,
    status="active",
    roadmap=None,
    last_commit_days=1,
    last_commit_subject=None,
    **extra_findings,
):
    findings = {"status": status, **extra_findings}
    if roadmap is not None:
        findings["roadmap"] = roadmap
    if last_commit_subject:
        findings["last_commit_subject"] = last_commit_subject

    return ProjectSnapshot(
        project_name=name,
        project_path=f"/home/gaddi/projects/{name}",
        health_score=score,
        last_commit_at=(
            datetime.now(UTC) - timedelta(days=last_commit_days)
            if last_commit_days is not None
            else None
        ),
        scanned_at=datetime.now(UTC),
        findings=findings,
    )


def roadmap(**overrides):
    base = {
        "has_handoff": True,
        "has_tasks": True,
        "has_status": True,
        "next_action": "Wire the drain retry path",
        "next_action_source": "handoff",
        "handoff_age_days": 2,
        "open_tasks": 3,
        "open_snags": 1,
        "missing_docs": [],
    }
    base.update(overrides)
    return base


def stub_rows(session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute.return_value = result


class TestRoadmapRecommendations:
    def test_stalled_handoff_is_a_risk_not_a_task(self):
        snap = make_snapshot(roadmap=roadmap(handoff_age_days=150))
        recs = recommendations_for(snap, ProjectOrganiserConfig())

        stalled = [r for r in recs if r.kind == "roadmap" and "Stalled" in r.title]
        assert len(stalled) == 1
        assert stalled[0].severity == "risk"
        # Zero points: the scanner records roadmap state without deducting
        assert stalled[0].points == 0

    def test_fresh_handoff_raises_no_stalled_advice(self):
        snap = make_snapshot(roadmap=roadmap(handoff_age_days=3))
        recs = recommendations_for(snap, ProjectOrganiserConfig())
        assert not any("Stalled" in r.title for r in recs)

    def test_boundary_is_exclusive(self):
        exactly = make_snapshot(roadmap=roadmap(handoff_age_days=STALLED_HANDOFF_DAYS))
        one_more = make_snapshot(
            roadmap=roadmap(handoff_age_days=STALLED_HANDOFF_DAYS + 1)
        )
        assert not any(
            "Stalled" in r.title
            for r in recommendations_for(exactly, ProjectOrganiserConfig())
        )
        assert any(
            "Stalled" in r.title
            for r in recommendations_for(one_more, ProjectOrganiserConfig())
        )

    def test_dormant_project_is_never_nagged(self):
        """Declaring a project dormant is the decision — don't ask again."""
        snap = make_snapshot(
            status="dormant",
            roadmap=roadmap(handoff_age_days=400, missing_docs=["handoff", "tasks"]),
        )
        recs = recommendations_for(snap, ProjectOrganiserConfig())
        assert not any(r.kind == "roadmap" for r in recs)

    def test_archived_project_is_never_nagged(self):
        snap = make_snapshot(
            status="archived", roadmap=roadmap(missing_docs=["handoff"])
        )
        assert not any(
            r.kind == "roadmap"
            for r in recommendations_for(snap, ProjectOrganiserConfig())
        )

    def test_missing_handoff_advice(self):
        snap = make_snapshot(roadmap=roadmap(missing_docs=["handoff"]))
        recs = recommendations_for(snap, ProjectOrganiserConfig())
        assert any("No session handoff" in r.title for r in recs)

    def test_snapshot_without_roadmap_key_is_tolerated(self):
        """Snapshots scanned before this feature existed must not crash."""
        snap = make_snapshot(roadmap=None)
        assert recommendations_for(snap, ProjectOrganiserConfig()) == []


def duplicate(path, days_older=7, date_source="heading", date="2026-08-03"):
    return {
        "path": path,
        "date": date,
        "date_source": date_source,
        "days_older": days_older,
    }


class TestDuplicateHandoffAdvice:
    """``handoff_duplicates`` reaching a surface that reports it.

    ``_read_handoff`` has picked a winner and reported the losers since
    Session 37, and until now the losers were reported to nobody — the
    field was recorded and read by nothing.  The harm being surfaced is
    not disk space: it is that somebody is writing session notes into a
    document no consumer reads, and cannot tell.
    """

    def test_two_handoffs_raise_one_zero_point_roadmap_item(self):
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[duplicate("docs/handoff.md")],
            )
        )
        recs = recommendations_for(snap, ProjectOrganiserConfig())

        (rec,) = [r for r in recs if "unread" in r.title]
        assert rec.kind == "roadmap"
        assert rec.severity == "advice"
        assert rec.points == 0
        assert rec.title == "Two handoffs — one is unread"

    def test_detail_names_the_winner_and_the_loser(self):
        """``handoff_path`` is consumed here and nowhere else.

        A recommendation that says "you have two handoffs" without
        saying which one the estate board is actually reading leaves the
        reader to guess which document their next action came from.
        """
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[duplicate("docs/sessions/handoff.md")],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert "Reading HANDOFF.md" in rec.detail
        assert "docs/sessions/handoff.md (7 days older)" in rec.detail

    def test_a_dated_gap_licenses_deletion(self):
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[duplicate("docs/handoff.md", days_older=12)],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert rec.action.startswith("Fold anything still true into HANDOFF.md")
        assert "delete docs/handoff.md" in rec.action

    def test_a_same_day_loser_is_never_told_to_delete(self):
        """Zero days apart means path order decided, not recency.

        The winner is whichever sits earlier in ``HANDOFF_PATHS``, which
        says nothing about which document holds the real record — this
        is precisely the shape SNAG-ROADMAP-003 was.  Advice to delete
        here would destroy the record to tidy up the stub.
        """
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[duplicate("docs/handoff.md", days_older=0)],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert rec.action.startswith("Confirm which is current")
        assert "same date — it lost on path order" in rec.detail

    def test_an_mtime_dated_gap_says_the_claim_is_weaker(self):
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[
                    duplicate("docs/handoff.md", date_source="mtime")
                ],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert "7 days older by file date" in rec.detail
        assert "clone or checkout rewrites those" in rec.detail

    def test_a_bare_path_from_an_older_snapshot_is_tolerated(self):
        """The field held plain strings before it was widened.

        Ninety days of retention outlive a shape change, so an undatable
        entry must still render — and must take the cautious branch,
        because nothing here can say which document is the real one.
        """
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=["docs/handoff.md"],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert "docs/handoff.md" in rec.detail
        assert rec.action.startswith("Confirm which is current")

    def test_three_handoffs_count_the_unread_ones(self):
        snap = make_snapshot(
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[
                    duplicate("docs/handoff.md"),
                    duplicate("docs/sessions/handoff.md", days_older=1),
                ],
            )
        )
        (rec,) = [
            r
            for r in recommendations_for(snap, ProjectOrganiserConfig())
            if "unread" in r.title
        ]
        assert rec.title == "3 handoffs — 2 are unread"
        assert "1 day older" in rec.detail

    def test_one_handoff_raises_nothing(self):
        snap = make_snapshot(
            roadmap=roadmap(handoff_path="HANDOFF.md", handoff_duplicates=[])
        )
        assert not any(
            "unread" in r.title
            for r in recommendations_for(snap, ProjectOrganiserConfig())
        )

    def test_dormant_project_is_not_nagged_about_duplicates(self):
        """Nobody is misled by an unread handoff in a repo nobody opens."""
        snap = make_snapshot(
            status="dormant",
            roadmap=roadmap(
                handoff_path="HANDOFF.md",
                handoff_duplicates=[duplicate("docs/handoff.md")],
            ),
        )
        assert not any(
            r.kind == "roadmap"
            for r in recommendations_for(snap, ProjectOrganiserConfig())
        )


@pytest.mark.anyio
class TestBoardEndpoint:
    async def test_returns_next_action_and_source(self, test_client, mock_session):
        stub_rows(
            mock_session,
            [make_snapshot(name="venture-assistant", roadmap=roadmap())],
        )

        resp = await test_client.get("/api/projects/board")
        assert resp.status_code == 200
        body = resp.json()

        assert body["count"] == 1
        entry = body["projects"][0]
        assert entry["name"] == "venture-assistant"
        assert entry["next_action"] == "Wire the drain retry path"
        assert entry["next_action_source"] == "handoff"
        assert entry["stalled"] is False

    async def test_git_fallback_when_no_roadmap_docs(self, test_client, mock_session):
        """A repo with no roadmap files still gets a row, labelled honestly."""
        stub_rows(mock_session, [
            make_snapshot(
                name="terrible",
                roadmap=roadmap(
                    next_action=None,
                    next_action_source=None,
                    handoff_age_days=None,
                    missing_docs=["handoff", "tasks", "status"],
                ),
                last_commit_subject="Add collision detection",
            )
        ])

        body = (await test_client.get("/api/projects/board")).json()
        entry = body["projects"][0]
        assert entry["next_action"] == "Add collision detection"
        assert entry["next_action_source"] == "git"

    async def test_stalled_flag_and_count(self, test_client, mock_session):
        stub_rows(mock_session, [
            make_snapshot(name="fresh", roadmap=roadmap(handoff_age_days=1)),
            make_snapshot(name="stale", roadmap=roadmap(handoff_age_days=150)),
        ])

        body = (await test_client.get("/api/projects/board")).json()
        assert body["stalled_count"] == 1
        # Ordering is not asserted here: the default view is activity-first,
        # so a stalled project does NOT lead it. That is deliberate — see
        # test_neglect_sort_puts_stalled_above_merely_idle for the view
        # where being stalled is the ranking signal.
        stale = next(p for p in body["projects"] if p["name"] == "stale")
        assert stale["stalled"] is True

    async def test_inactive_excluded_by_default(self, test_client, mock_session):
        stub_rows(mock_session, [
            make_snapshot(name="live"),
            make_snapshot(name="parked", status="dormant"),
            make_snapshot(name="retired", status="archived"),
        ])

        body = (await test_client.get("/api/projects/board")).json()
        assert [p["name"] for p in body["projects"]] == ["live"]

    async def test_include_inactive_opt_in(self, test_client, mock_session):
        stub_rows(mock_session, [
            make_snapshot(name="live"),
            make_snapshot(name="parked", status="dormant"),
        ])

        body = (
            await test_client.get("/api/projects/board?include_inactive=true")
        ).json()
        names = [p["name"] for p in body["projects"]]
        assert names == ["live", "parked"]  # active still sorts first

    async def test_default_sort_is_current_work_first(
        self, test_client, mock_session
    ):
        """An actively-developed project must not be buried.

        Regression for the first draft, which defaulted to neglect order
        and put an ongoing project at row 12 of 18.
        """
        stub_rows(mock_session, [
            make_snapshot(name="recent", last_commit_days=0),
            make_snapshot(name="ancient", last_commit_days=90),
        ])

        body = (await test_client.get("/api/projects/board")).json()
        assert [p["name"] for p in body["projects"]] == ["recent", "ancient"]

    async def test_neglect_sort_inverts_it(self, test_client, mock_session):
        stub_rows(mock_session, [
            make_snapshot(name="recent", last_commit_days=0),
            make_snapshot(name="ancient", last_commit_days=90),
        ])

        body = (
            await test_client.get("/api/projects/board?sort=neglect")
        ).json()
        assert [p["name"] for p in body["projects"]] == ["ancient", "recent"]

    async def test_neglect_sort_puts_stalled_above_merely_idle(
        self, test_client, mock_session
    ):
        stub_rows(mock_session, [
            make_snapshot(name="idle", last_commit_days=200),
            make_snapshot(
                name="stalled", last_commit_days=40, roadmap=roadmap(handoff_age_days=99)
            ),
        ])

        body = (
            await test_client.get("/api/projects/board?sort=neglect")
        ).json()
        assert [p["name"] for p in body["projects"]] == ["stalled", "idle"]

    async def test_unknown_commit_date_sorts_last_in_both_modes(
        self, test_client, mock_session
    ):
        """Never committed is neither recent work nor urgently overdue."""
        rows = [
            make_snapshot(name="never", last_commit_days=None),
            make_snapshot(name="old", last_commit_days=45),
        ]
        for mode in ("activity", "neglect"):
            stub_rows(mock_session, rows)
            body = (
                await test_client.get(f"/api/projects/board?sort={mode}")
            ).json()
            assert [p["name"] for p in body["projects"]] == ["old", "never"], mode

    async def test_bad_sort_value_rejected(self, test_client, mock_session):
        stub_rows(mock_session, [make_snapshot()])
        resp = await test_client.get("/api/projects/board?sort=sideways")
        assert resp.status_code == 422

    async def test_board_is_not_captured_as_a_project_name(
        self, test_client, mock_session
    ):
        """Regression: /board must stay declared before /{name}."""
        stub_rows(mock_session, [make_snapshot()])
        resp = await test_client.get("/api/projects/board")
        assert "projects" in resp.json()

    async def test_empty_estate(self, test_client, mock_session):
        stub_rows(mock_session, [])
        body = (await test_client.get("/api/projects/board")).json()
        assert body == {
            "projects": [],
            "count": 0,
            "stalled_count": 0,
            "generated_at": body["generated_at"],
        }


@pytest.mark.anyio
class TestActionsTruncationIsVisible:
    """A saturated list must say what it stopped showing.

    Eleven projects share one `no_remote` risk. Risk sorts first and
    `roadmap` advice is worth 0 points, so the default limit of 10 was
    filled entirely by "Add a git remote" — every roadmap finding on the
    estate was invisible, and `total_available: 68` did not say which
    kinds went missing.
    """

    async def test_dropped_kinds_reported(self, test_client, mock_session):
        rows = [
            make_snapshot(
                name=f"p{i}",
                no_remote=True,
                missing_readme=True,
                # open_snags=0 so each project yields exactly three items:
                # one risk, one docs, one roadmap. Keeps the arithmetic
                # below about truncation rather than about fixtures.
                roadmap=roadmap(missing_docs=["handoff"], open_snags=0),
            )
            for i in range(6)
        ]
        stub_rows(mock_session, rows)

        body = (await test_client.get("/api/projects/actions?limit=6")).json()
        assert body["count"] == 6
        assert body["total_available"] == 18
        # The 6 risks fill the window; what they hid is named, not merely counted
        assert body["dropped_by_kind"] == {"docs": 6, "roadmap": 6}
        assert all(a["severity"] == "risk" for a in body["actions"])

    async def test_nothing_dropped_reports_empty(self, test_client, mock_session):
        stub_rows(mock_session, [make_snapshot(name="p", missing_readme=True)])
        body = (await test_client.get("/api/projects/actions?limit=10")).json()
        assert body["dropped_by_kind"] == {}


@pytest.mark.anyio
class TestDeletedProjectsLeaveTheBoard:
    """A project removed from disk must stop being reported as live.

    ``PA-worktrees`` was deleted during the ~/projects reorganisation and
    still held a board row two days later, complete with health score and
    next action.

    The board applied the ``newest_scan − 1h`` cutoff in Python and was
    the only surface of nine that did (SNAG-PROJ-001). It now comes from
    ``latest_snapshot_query``, in SQL, so a mocked session cannot
    demonstrate the exclusion — the rows a test stubs are returned
    whatever the ``WHERE`` clause says. The predicate itself is asserted
    in ``tests/test_project_snapshots_query.py``; what stays here is the
    board's own behaviour on rows the query does hand it.
    """

    async def test_board_no_longer_filters_by_hand(self, test_client, mock_session):
        """Rows the query returns are rendered — the cutoff is upstream.

        The inverse of the old test, and deliberately so: a second
        filter here would be the "repeat it at every call site" shape
        that caused the defect.
        """
        fresh = make_snapshot(name="live")
        old = make_snapshot(name="also-live")
        old.scanned_at = datetime.now(UTC) - timedelta(days=2)
        stub_rows(mock_session, [fresh, old])

        body = (await test_client.get("/api/projects/board")).json()
        assert sorted(p["name"] for p in body["projects"]) == ["also-live", "live"]

    async def test_snapshots_without_a_timestamp_do_not_crash_it(
        self, test_client, mock_session
    ):
        """``scanned_at`` is nullable in the model, so the board must cope."""
        row = make_snapshot(name="odd")
        row.scanned_at = None
        stub_rows(mock_session, [row, make_snapshot(name="fine")])

        resp = await test_client.get("/api/projects/board")
        assert resp.status_code == 200
        assert sorted(p["name"] for p in resp.json()["projects"]) == ["fine", "odd"]
