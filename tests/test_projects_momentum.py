"""GET /api/projects/momentum — sessions that started and landed nothing.

Two of these tests exist because the obvious implementation was written
first and the live data refuted it.

``test_a_commit_after_the_scan_still_counts_as_landed`` is the important
one.  The first rule asked whether a commit had been made *by the time
the scanner saw the new handoff*, which reads as common sense and is
wrong: the handoff is written before the work is committed.  On
2026-08-10 a scan ran at 09:06 and saw this repository's new handoff
while ``last_commit_at`` still read 2026-08-08; the day's six commits
arrived afterwards, and a productive day was reported as dropped.  Scan
timing was deciding the answer, and no fixture with a tidy cadence would
have shown it.

``test_undated_scans_do_not_stretch_the_observed_period`` is the second.
This estate holds 198 scans of ``sysadmin_assistant`` going back to
2026-05-13, but the roadmap findings block only exists from 2026-08-06 —
so reporting the series as three months long invited dividing five
sessions by ninety days.  Only scans that resolved a handoff date can
carry a session, so only those are the observed period.
"""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.momentum import (
    Momentum,
    Observation,
    build_reason,
    find_sessions,
    measure,
    parse_observation,
    rank,
)
from sysadmin.projects.roadmap import scan_roadmap
from sysadmin.projects.snapshots import momentum_history_query


def at(day, hour=6):
    """A scan on 2026-08-<day>."""
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def obs(day, handoff=None, code=None, any_commit=None, source="heading", hour=6):
    """One observation, with dates given as day-of-August integers."""
    return Observation(
        scanned_at=at(day, hour),
        handoff_date=date(2026, 8, handoff) if handoff else None,
        handoff_date_source=source if handoff else None,
        code_commit_date=date(2026, 8, code) if code else None,
        any_commit_date=date(2026, 8, any_commit or code) if (any_commit or code)
        else None,
    )


def series(*points):
    """Newest-first, the order every snapshots.py query returns."""
    return list(reversed(points))


class TestParseObservation:
    def test_handoff_date_is_reconstructed_from_the_scan_and_the_age(self):
        point = parse_observation(
            scanned_at=at(11), last_commit_at=None,
            handoff_age_days="4", handoff_date_source="heading", any_commit=None,
        )
        assert point.handoff_date == date(2026, 8, 7)

    def test_missing_age_is_not_a_date(self):
        """Snapshots before 2026-08-06 carry ``{}`` and must not raise."""
        point = parse_observation(at(11), None, None, None, None)
        assert point.handoff_date is None
        assert point.handoff_date_source is None

    def test_unparseable_age_is_not_a_date(self):
        point = parse_observation(at(11), None, "not-a-number", None, None)
        assert point.handoff_date is None

    def test_absent_any_commit_falls_back_to_the_column_exactly(self):
        """Not an approximation — see the module docstring.

        ``findings['git']`` is written only when a housekeeping commit was
        skipped (77 rows of 3,635 on this estate).  Its absence means the
        newest commit *is* the newest code commit.
        """
        point = parse_observation(
            at(11), datetime(2026, 8, 9, tzinfo=UTC), "0", "heading", None,
        )
        assert point.code_commit_date == date(2026, 8, 9)
        assert point.any_commit_date == date(2026, 8, 9)

    def test_any_commit_is_read_when_the_two_differ(self):
        point = parse_observation(
            at(11), datetime(2026, 8, 4, tzinfo=UTC), "0", "heading", "2026-08-10",
        )
        assert point.code_commit_date == date(2026, 8, 4)
        assert point.any_commit_date == date(2026, 8, 10)

    def test_malformed_any_commit_falls_back_rather_than_raising(self):
        point = parse_observation(
            at(11), datetime(2026, 8, 4, tzinfo=UTC), "0", "heading", "the-fourth",
        )
        assert point.any_commit_date == date(2026, 8, 4)


class TestFindSessions:
    def test_the_baseline_is_a_state_not_a_session(self):
        """One observation cannot show a transition.

        The same rule ``build_narrative_history`` applies to
        ``next_action_changed``: calling the first point a change invents
        an event whose existence depends on ``limit``.
        """
        assert find_sessions(series(obs(9, handoff=8, code=8))) == []

    def test_a_handoff_date_moving_forward_is_one_session(self):
        sessions = find_sessions(series(
            obs(9, handoff=8, code=8),
            obs(10, handoff=10, code=10),
        ))
        assert [s.date for s in sessions] == [date(2026, 8, 10)]

    def test_a_repeated_handoff_date_is_not_a_new_session(self):
        """The organiser scans daily; a quiet day must not count as work."""
        sessions = find_sessions(series(
            obs(8, handoff=7),
            obs(9, handoff=7),
            obs(10, handoff=7),
        ))
        assert sessions == []

    def test_a_handoff_date_moving_backwards_is_not_a_session(self):
        """A checkout or a revert must not manufacture work."""
        sessions = find_sessions(series(
            obs(9, handoff=9),
            obs(10, handoff=5),
        ))
        assert sessions == []

    def test_a_commit_after_the_scan_still_counts_as_landed(self):
        """The regression this module was rewritten for — see the docstring.

        The scan that first sees the new handoff can run *before* the
        day's commits. Attributing by date window rather than by what the
        scanner had seen makes the answer independent of scan timing.
        """
        sessions = find_sessions(series(
            obs(9, handoff=8, code=8),
            obs(10, handoff=10, code=8, hour=9),    # commits not made yet
            obs(11, handoff=10, code=10, hour=4),   # observed next morning
        ))
        assert len(sessions) == 1
        assert sessions[0].landed_code is True

    def test_a_later_sessions_commit_does_not_credit_an_earlier_one(self):
        """The window closes at the next session, not at the end of time."""
        sessions = find_sessions(series(
            obs(8, handoff=7, code=7),
            obs(9, handoff=9, code=7),      # 9th: nothing landed
            obs(10, handoff=10, code=10),   # 10th: landed
        ))
        assert [(s.date.day, s.landed_code) for s in sessions] == [
            (9, False), (10, True),
        ]

    def test_the_last_sessions_window_stays_open(self):
        """A session opened this morning has not dropped yet — but reads
        as dropped until something lands, which is correct at the time of
        asking and settles itself on the next scan."""
        sessions = find_sessions(series(
            obs(9, handoff=8, code=8),
            obs(10, handoff=10, code=8),
        ))
        assert sessions[0].landed_code is False

    def test_docs_only_is_the_gap_between_the_two_answers(self):
        sessions = find_sessions(series(
            obs(9, handoff=8, code=8, any_commit=8),
            obs(10, handoff=10, code=8, any_commit=10),
        ))
        assert sessions[0].landed_code is False
        assert sessions[0].landed_any is True

    def test_an_mtime_dated_session_is_counted_but_not_verified(self):
        sessions = find_sessions(series(
            obs(9, handoff=8),
            obs(10, handoff=10, source="mtime"),
        ))
        assert len(sessions) == 1
        assert sessions[0].verified is False

    def test_a_session_from_a_snapshot_predating_the_field_is_unverified(self):
        """``handoff_date_source`` has only been written since 2026-08-11."""
        sessions = find_sessions(series(
            obs(9, handoff=8, source=None),
            obs(10, handoff=10, source=None),
        ))
        assert sessions[0].date_source is None
        assert sessions[0].verified is False


class TestMeasure:
    def test_nothing_observed_is_not_a_measurement_of_zero(self):
        record = measure("Athenaeum", [])
        assert record.sessions == 0
        assert record.observed_from is None
        assert record.scans == 0

    def test_undated_scans_do_not_stretch_the_observed_period(self):
        """See the module docstring: 198 scans, 22 of them measurable."""
        record = measure("demo", series(
            obs(1), obs(2), obs(3),                   # pre-roadmap: findings {}
            obs(9, handoff=8, code=8),
            obs(10, handoff=10, code=10),
        ))
        assert record.scans == 2
        assert record.observed_from == date(2026, 8, 9)
        assert record.observed_to == date(2026, 8, 10)

    def test_the_two_dropped_counts_are_different_failures(self):
        record = measure("demo", series(
            obs(8, handoff=7, code=7, any_commit=7),
            obs(9, handoff=9, code=7, any_commit=9),    # docs only
            obs(10, handoff=10, code=7, any_commit=7),  # nothing at all
        ))
        assert record.sessions == 2
        assert record.dropped_code == 2      # neither shipped code
        assert record.dropped == 1           # only one shipped nothing
        assert record.docs_only == 1

    def test_drop_rate_is_zero_rather_than_undefined_with_no_sessions(self):
        assert measure("demo", []).drop_rate == 0.0

    def test_a_series_starting_at_the_window_edge_says_so(self):
        record = measure(
            "demo",
            series(obs(9, handoff=8), obs(10, handoff=10)),
            window_start=at(9) - timedelta(hours=12),
        )
        assert record.at_window_edge is True

    def test_a_series_starting_inside_the_window_does_not(self):
        record = measure(
            "demo",
            series(obs(9, handoff=8), obs(10, handoff=10)),
            window_start=at(1),
        )
        assert record.at_window_edge is False

    def test_last_landing_reports_the_newest_session_that_shipped_code(self):
        record = measure("demo", series(
            obs(8, handoff=7, code=7),
            obs(9, handoff=9, code=9),
            obs(11, handoff=11, code=9),
        ))
        assert record.last_session == date(2026, 8, 11)
        assert record.last_landing == date(2026, 8, 9)


def record(name, sessions=3, dropped_code=1):
    return Momentum(
        name=name, sessions=sessions, landed_code=sessions - dropped_code,
        landed_any=sessions - dropped_code, docs_only=0,
        dropped=dropped_code, dropped_code=dropped_code, unverified=0,
        observed_from=date(2026, 8, 6), observed_to=date(2026, 8, 11),
        scans=10, at_window_edge=False, last_session=date(2026, 8, 11),
        last_landing=None,
    )


class TestRank:
    def test_most_dropped_sessions_first(self):
        ordered = rank([record("a", dropped_code=1), record("b", dropped_code=3)])
        assert [m.name for m in ordered] == ["b", "a"]

    def test_the_rate_breaks_a_tie_on_the_count(self):
        ordered = rank([
            record("many", sessions=9, dropped_code=2),
            record("few", sessions=3, dropped_code=2),
        ])
        assert [m.name for m in ordered] == ["few", "many"]

    def test_an_unmeasured_project_ranks_below_a_measured_clean_one(self):
        """0-of-0 is an absence of evidence.

        Ranking it beside a measured 0-of-5 would read as "this one is
        fine", which is the one thing the data cannot say.
        """
        ordered = rank([
            record("unmeasured", sessions=0, dropped_code=0),
            record("clean", sessions=5, dropped_code=0),
        ])
        assert [m.name for m in ordered] == ["clean", "unmeasured"]


class TestBuildReason:
    def test_no_scan_at_all_says_so(self):
        assert "No project scan" in build_reason([])

    def test_scanned_but_nothing_observed_is_a_different_sentence(self):
        text = build_reason([record("demo", sessions=0, dropped_code=0)])
        assert "No session has been observed" in text

    def test_a_clean_estate_is_stated_rather_than_left_empty(self):
        text = build_reason(rank([
            record("a", sessions=3, dropped_code=0),
            record("b", sessions=2, dropped_code=0),
        ]))
        assert "landed code" in text
        assert "5 observed sessions" in text

    def test_the_headline_names_the_project_and_the_counts(self):
        text = build_reason(rank([record("alfred-glance", sessions=2,
                                         dropped_code=2)]))
        assert "alfred-glance" in text
        assert "2 sessions that shipped no code" in text
        assert "out of 2 observed" in text

    def test_an_unverified_count_is_hedged_in_the_sentence(self):
        soft = Momentum(
            name="demo", sessions=2, landed_code=0, landed_any=0, docs_only=0,
            dropped=2, dropped_code=2, unverified=2, observed_from=date(2026, 8, 9),
            observed_to=date(2026, 8, 10), scans=3, at_window_edge=False,
            last_session=date(2026, 8, 10), last_landing=None,
        )
        assert "mtime" in build_reason([soft])

    def test_a_verified_count_is_not_hedged(self):
        assert "mtime" not in build_reason([record("demo", 3, 2)])

    def test_the_window_edge_adds_an_at_least(self):
        edged = Momentum(
            name="demo", sessions=2, landed_code=0, landed_any=0, docs_only=0,
            dropped=2, dropped_code=2, unverified=0, observed_from=date(2026, 8, 9),
            observed_to=date(2026, 8, 10), scans=3, at_window_edge=True,
            last_session=date(2026, 8, 10), last_landing=None,
        )
        assert "at least" in build_reason([edged])


class TestHandoffDateSource:
    """The scanner half — without it every session is unverified."""

    def test_a_dated_heading_is_recorded_as_heading(self, tmp_path):
        (tmp_path / "HANDOFF.md").write_text(
            "# Handoff — 2026-08-11\n\n## Next action\n\nShip the thing.\n"
        )
        info = scan_roadmap(tmp_path, now=datetime(2026, 8, 11, tzinfo=UTC))
        assert info["handoff_date_source"] == "heading"
        assert info["handoff_age_days"] == 0

    def test_an_undated_heading_falls_back_to_mtime_and_says_so(self, tmp_path):
        """ImbaBots heads its 141 KB handoff "Handoff — M5 (Tier 2)"."""
        (tmp_path / "HANDOFF.md").write_text(
            "# Handoff — M5 (Tier 2)\n\n## Next action\n\nShip the thing.\n"
        )
        info = scan_roadmap(tmp_path, now=datetime(2026, 8, 11, tzinfo=UTC))
        assert info["handoff_date_source"] == "mtime"

    def test_a_malformed_date_is_mtime_not_heading(self, tmp_path):
        """2026-13-45 is not a date, and claiming the document dated
        itself would be the overstatement the field exists to prevent."""
        (tmp_path / "HANDOFF.md").write_text("# Handoff — 2026-13-45\n\nBody.\n")
        info = scan_roadmap(tmp_path, now=datetime(2026, 8, 11, tzinfo=UTC))
        assert info["handoff_date_source"] == "mtime"

    def test_no_handoff_leaves_the_field_unset(self, tmp_path):
        info = scan_roadmap(tmp_path, now=datetime(2026, 8, 11, tzinfo=UTC))
        assert info["handoff_date_source"] is None


class TestMomentumHistoryQuery:
    """Compiled SQL: the suite has no live database, so the shape of the
    statement is the honest thing to assert."""

    def _sql(self, query):
        return str(query.compile(dialect=postgresql.dialect()))

    def test_reads_three_json_fields_not_whole_rows(self):
        sql = self._sql(momentum_history_query(["demo"]))
        assert "AS handoff_age_days" in sql
        assert "AS date_source" in sql
        assert "AS any_commit" in sql
        # Kilobytes per row across every scan in the window.
        assert "project_snapshots.findings," not in sql

    def test_the_commit_column_is_selected_not_derived_from_findings(self):
        """``last_commit_at`` carries the code-commit date for every row;
        ``findings['git']`` exists on 2% of them."""
        sql = self._sql(momentum_history_query(["demo"]))
        assert "project_snapshots.last_commit_at" in sql

    def test_window_is_anchored_to_the_newest_scan(self):
        sql = self._sql(momentum_history_query(["demo"]))
        assert "max(sysadmin.project_snapshots.scanned_at)" in sql
        assert "scanned_at >= (SELECT max" in sql

    def test_ordered_newest_first_per_project(self):
        sql = self._sql(momentum_history_query(["demo"]))
        assert "ORDER BY sysadmin.project_snapshots.project_name, " \
               "sysadmin.project_snapshots.scanned_at DESC" in sql

    def test_no_names_selects_no_rows_rather_than_every_project(self):
        assert "IN (" in self._sql(momentum_history_query([]))


def snapshot(name="demo", status="active"):
    return ProjectSnapshot(
        project_name=name,
        project_path=f"/home/gaddi/projects/{name}",
        health_score=90,
        last_commit_at=datetime(2026, 8, 10, tzinfo=UTC),
        scanned_at=at(11),
        findings={"status": status, "roadmap": {}},
    )


def stub_two_queries(session, snapshots, history):
    latest = MagicMock()
    latest.scalars.return_value.all.return_value = snapshots
    rows = MagicMock()
    rows.all.return_value = history
    session.execute.side_effect = [latest, rows]


@pytest.mark.asyncio
class TestMomentumEndpoint:
    async def test_an_empty_estate_is_200_with_a_reason(self, test_client,
                                                        mock_session):
        """A 404 would collapse "everything landed" into "never scanned"."""
        stub_two_queries(mock_session, [], [])

        resp = await test_client.get("/api/projects/momentum")

        assert resp.status_code == 200
        assert resp.json()["worst"] is None
        assert resp.json()["reason"]

    async def test_the_route_is_not_swallowed_by_the_name_parameter(
        self, test_client, mock_session
    ):
        """``/{name}`` is declared after it; a reordering would turn this
        endpoint into a lookup for a project called "momentum"."""
        stub_two_queries(mock_session, [], [])

        body = (await test_client.get("/api/projects/momentum")).json()

        assert "projects" in body
        assert "health_score" not in body

    async def test_dormant_and_archived_projects_are_skipped_and_counted(
        self, test_client, mock_session
    ):
        """Not a finding: that is what declaring a project dormant meant.
        Counted rather than dropped, so the reader can see the estate is
        bigger than the list."""
        stub_two_queries(mock_session, [
            snapshot("live"),
            snapshot("old", status="archived"),
            snapshot("resting", status="dormant"),
        ], [])

        body = (await test_client.get("/api/projects/momentum")).json()

        assert [p["name"] for p in body["projects"]] == ["live"]
        assert body["skipped"] == {"archived": 1, "dormant": 1}

    async def test_undeclared_projects_are_measured(
        self, test_client, mock_session
    ):
        """``ACTIVELY_SCORED`` is borrowed, not restated — an undeclared
        repository is scored as if active everywhere else here."""
        stub_two_queries(mock_session, [snapshot("ImbaBots", "undeclared")], [])

        body = (await test_client.get("/api/projects/momentum")).json()

        assert [p["name"] for p in body["projects"]] == ["ImbaBots"]

    async def test_history_is_not_fetched_when_nothing_qualifies(
        self, test_client, mock_session
    ):
        latest = MagicMock()
        latest.scalars.return_value.all.return_value = [
            snapshot("old", status="archived")
        ]
        mock_session.execute.side_effect = [latest]

        resp = await test_client.get("/api/projects/momentum")

        assert resp.status_code == 200
        assert mock_session.execute.await_count == 1

    async def test_the_headline_and_the_totals_agree_with_the_list(
        self, test_client, mock_session
    ):
        stub_two_queries(mock_session, [snapshot("alfred-glance")], [
            # (name, scanned_at, last_commit_at, age, source, any_commit)
            ("alfred-glance", at(10), datetime(2026, 8, 3, tzinfo=UTC),
             "0", "heading", None),
            ("alfred-glance", at(10, 5), datetime(2026, 8, 3, tzinfo=UTC),
             "1", "heading", None),
            ("alfred-glance", at(9), datetime(2026, 8, 3, tzinfo=UTC),
             "1", "heading", None),
        ])

        body = (await test_client.get("/api/projects/momentum")).json()

        assert body["worst"]["name"] == "alfred-glance"
        assert body["worst"]["sessions"] == 2
        assert body["worst"]["dropped_code"] == 2
        assert body["total_sessions"] == 2
        assert body["total_dropped_code"] == 2
        assert "alfred-glance" in body["reason"]
