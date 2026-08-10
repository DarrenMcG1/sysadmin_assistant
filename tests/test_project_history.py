"""The narrative history behind GET /api/projects/{name}.

The organiser has written the whole roadmap findings block into
``project_snapshots`` since Session 28 (2026-08-06). Until Session 37 the
history list carried only ``health_score`` and ``scanned_at``, so ninety
days of next actions sat in JSONB with no endpoint over them — and Session
32's start-versus-finish accounting was recorded as blocked on a document
format while the data it needed was already being collected.
"""

from datetime import UTC, datetime

from sysadmin.core.contracts import ProjectDetailResponse, ProjectHistoryPoint
from sysadmin.projects.router import build_narrative_history


class Row:
    """A snapshot row, duck-typed — the builder never touches the ORM."""

    def __init__(self, score=100, day=1, action=None, source=None, findings=...):
        self.health_score = score
        self.scanned_at = datetime(2026, 8, day, tzinfo=UTC)
        if findings is not ...:
            self.findings = findings
            return
        roadmap = {}
        if action is not None:
            roadmap["next_action"] = action
        if source is not None:
            roadmap["next_action_source"] = source
        self.findings = {"roadmap": roadmap} if roadmap else {}


class TestBuildNarrativeHistory:
    def test_carries_action_and_source_per_point(self):
        rows = [Row(day=7, action="Ship it", source="handoff")]
        (point,) = build_narrative_history(rows)
        assert point["next_action"] == "Ship it"
        assert point["next_action_source"] == "handoff"
        assert point["health_score"] == 100
        assert point["scanned_at"].startswith("2026-08-07")

    def test_change_is_measured_against_the_older_neighbour(self):
        """Rows are newest-first, so the comparison runs *down* the list."""
        rows = [
            Row(day=8, action="Second thing"),   # newest — changed
            Row(day=7, action="First thing"),    # changed from day 6
            Row(day=6, action="First thing"),    # oldest — unknowable
        ]
        changed = [p["next_action_changed"] for p in build_narrative_history(rows)]
        assert changed == [True, False, None]

    def test_oldest_point_is_none_not_false(self):
        """None means "no older row in this window", not "unchanged".

        Rendering it as unchanged would invent a streak whose length moves
        with ``limit`` — the window slides, the reported run changes, and
        nothing in the data did.
        """
        rows = [Row(day=8, action="Same"), Row(day=7, action="Same")]
        points = build_narrative_history(rows)
        assert points[0]["next_action_changed"] is False
        assert points[1]["next_action_changed"] is None

    def test_a_run_of_false_measures_how_long_an_action_stayed_open(self):
        rows = [Row(day=d, action="Long job") for d in (9, 8, 7, 6)]
        points = build_narrative_history(rows)
        assert [p["next_action_changed"] for p in points] == [False, False, False, None]

    def test_snapshots_predating_the_roadmap_block_yield_none(self):
        """Rows from before 2026-08-06 carry {} and must not raise."""
        rows = [Row(day=7, action="Now known"), Row(day=6, findings={})]
        points = build_narrative_history(rows)
        assert points[0]["next_action"] == "Now known"
        assert points[1]["next_action"] is None
        # Known vs unknown still counts as a change; the alternative is
        # silently reporting continuity across the boundary where the
        # organiser started recording.
        assert points[0]["next_action_changed"] is True

    def test_findings_none_is_survivable(self):
        """A NULL findings column must not take out a portfolio read."""
        rows = [Row(day=7, findings=None)]
        (point,) = build_narrative_history(rows)
        assert point["next_action"] is None
        assert point["next_action_source"] is None

    def test_empty_rows_gives_empty_history(self):
        assert build_narrative_history([]) == []


class TestHistoryContract:
    def test_new_fields_round_trip(self):
        point = ProjectHistoryPoint.model_validate({
            "health_score": 92,
            "scanned_at": "2026-08-10T09:00:00+00:00",
            "next_action": "Surface handoff_duplicates somewhere a human reads",
            "next_action_source": "handoff",
            "next_action_changed": True,
        })
        assert point.next_action_source == "handoff"
        assert point.next_action_changed is True

    def test_old_payload_without_the_fields_still_parses(self):
        """A tray built before Session 37 must not break on new data, and
        this endpoint is parse-side only — nothing validates it server-side."""
        point = ProjectHistoryPoint.model_validate(
            {"health_score": 80, "scanned_at": "2026-05-10T09:00:00+00:00"}
        )
        assert point.next_action is None
        assert point.next_action_changed is None

    def test_detail_response_carries_the_richer_points(self):
        response = ProjectDetailResponse.model_validate({
            "name": "ImbaBots",
            "history": [
                {"health_score": 90, "scanned_at": "2026-08-07T00:00:00+00:00",
                 "next_action": "Play T05 and rule", "next_action_source": "handoff",
                 "next_action_changed": True},
                {"health_score": 90, "scanned_at": "2026-08-06T00:00:00+00:00",
                 "next_action": "Play T05 and rule", "next_action_source": "tasks",
                 "next_action_changed": None},
            ],
        })
        assert [p.next_action_source for p in response.history] == ["handoff", "tasks"]
