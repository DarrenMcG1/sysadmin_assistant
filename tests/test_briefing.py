"""Tests for the morning briefing — envelope, facts, prose and sections.

DB access is mocked at the session level (same pattern as
tests/test_routers.py); psutil and the notifier are patched.  ``_gather``
runs its queries in a fixed order — services, logs, filesystem, projects,
alerts, then the two reviews — so ``session.execute`` uses ``side_effect``
to feed each one its result.

Note what a mocked session cannot show: the project query's freshness
cutoff and the alert query's ``GROUP BY`` are invisible here, because no
``WHERE`` clause is ever executed.  Those belong to
tests/test_project_snapshots_query.py and to reading the SQL.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.briefing.data import (
    NEXT_ACTION_CHARS,
    SCHEMA_VERSION,
    build_facts,
    generate_briefing_data,
    send_morning_briefing,
    summarise,
)
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_summary import LogSummary
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.projects.models.project_snapshot import ProjectSnapshot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _result_all(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def _result_one(row):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    return result


def _service(name: str, status: str = "ok", details: dict | None = None) -> ServiceHealth:
    row = ServiceHealth(service_name=name, status=status, details=details or {})
    row.checked_at = datetime.now(UTC)
    return row


def _log_summary(text: str = "All quiet overnight.") -> LogSummary:
    row = LogSummary(summary=text)
    row.created_at = datetime.now(UTC)
    return row


def _audit() -> FilesystemAudit:
    row = FilesystemAudit()
    row.total_reclaimable_mb = 1234
    row.empty_dirs_count = 5
    row.stale_project_dirs_count = 2
    row.duplicate_groups_count = 3
    row.scanned_at = datetime.now(UTC)
    return row


def _project(
    name: str,
    score: int = 90,
    stale_branches: int = 0,
    todos: int = 0,
) -> ProjectSnapshot:
    row = ProjectSnapshot(project_name=name, health_score=score)
    row.stale_branch_count = stale_branches
    row.todo_count = todos
    row.scanned_at = datetime.now(UTC)
    return row


def _result_first(row):
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    return result


def _review(narrative: str = "A fine week.", days_old: int = 0):
    from sysadmin.projects.models.project_review import ProjectReview

    row = ProjectReview(period_days=7, narrative=narrative, llm_used=True)
    row.generated_at = datetime.now(UTC) - timedelta(days=days_old)
    return row


def _disk_review(narrative: str = "Disk held steady.", days_old: int = 0):
    from sysadmin.files.models.disk_review import DiskReview

    row = DiskReview(period_days=7, narrative=narrative, llm_used=True)
    row.generated_at = datetime.now(UTC) - timedelta(days=days_old)
    return row


def _result_rows(rows):
    """A grouped result — ``.all()`` rather than ``.scalars().all()``.

    The alert query aggregates in SQL (``GROUP BY severity, title``), so
    it yields Rows of labelled columns rather than ORM objects.
    """
    result = MagicMock()
    result.all.return_value = rows
    return result


def _alert_row(title, severity="warning", occurrences=1, latest=None):
    return SimpleNamespace(
        severity=severity,
        title=title,
        occurrences=occurrences,
        latest=latest or datetime.now(UTC),
    )


def _session_returning(
    infra,
    log,
    filesystem,
    projects,
    review=None,
    disk_review=None,
    alerts=None,
):
    """Mock session whose execute() feeds each gather step in order.

    Order matters and is positional: adding a query to ``_gather``
    without adding a result here exhausts the iterator and every test in
    this file fails at once.  (It did, when "Pick This Up" was added, and
    again when the envelope added alerts — the docstring was right twice.)

    ``projects`` feeds **one** query, not two.  "Project Health" and
    "Pick This Up" used to issue the same latest-snapshot query
    separately; they now share a single read, which is why the old
    ``next_actions`` parameter is gone.  A test that wants different rows
    in the two sections was expressing something the database could never
    produce.
    """
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result_all(infra),
            _result_one(log),
            _result_one(filesystem),
            _result_all(projects),
            _result_rows(alerts or []),
            _result_first(review),
            _result_first(disk_review),
        ]
    )
    return session


# ---------------------------------------------------------------------------
# generate_briefing_data
# ---------------------------------------------------------------------------


class TestGenerateBriefingData:
    @pytest.mark.asyncio
    async def test_all_sections_present_when_data_exists(self):
        session = _session_returning(
            infra=[_service("postgres"), _service("redis")],
            log=_log_summary(),
            filesystem=_audit(),
            projects=[_project("pa")],
        )

        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=89.0)
            briefing = await generate_briefing_data(session)

        assert briefing["source"] == "sysadmin-service"
        assert "generated_at" in briefing
        titles = [s["title"] for s in briefing["sections"]]
        assert titles == [
            "Infrastructure Status",
            "Overnight Log Summary",
            "Filesystem",
            "Project Health",
        ]

    @pytest.mark.asyncio
    async def test_empty_database_yields_no_sections(self):
        session = _session_returning(infra=[], log=None, filesystem=None, projects=[])
        briefing = await generate_briefing_data(session)
        assert briefing["sections"] == []

    @pytest.mark.asyncio
    async def test_infrastructure_section_flags_unhealthy(self):
        session = _session_returning(
            infra=[
                _service("postgres", "ok"),
                _service("pa", "unreachable", details={"reason": "Connection refused"}),
            ],
            log=None,
            filesystem=None,
            projects=[],
        )
        briefing = await generate_briefing_data(session)

        (infra,) = briefing["sections"]
        assert infra["type"] == "status_grid"
        assert infra["data"]["all_services_healthy"] is False
        pa = next(s for s in infra["data"]["services"] if s["name"] == "pa")
        assert pa["note"] == "Connection refused"

    @pytest.mark.asyncio
    async def test_log_section_carries_summary_text(self):
        session = _session_returning(
            infra=[], log=_log_summary("Two errors from redis."), filesystem=None, projects=[]
        )
        briefing = await generate_briefing_data(session)

        (log_section,) = briefing["sections"]
        assert log_section["type"] == "text"
        assert log_section["data"] == "Two errors from redis."

    @pytest.mark.asyncio
    async def test_filesystem_section_metrics(self):
        session = _session_returning(infra=[], log=None, filesystem=_audit(), projects=[])

        with patch("sysadmin.briefing.data.psutil.disk_usage") as mock_disk:
            mock_disk.return_value = MagicMock(percent=89.0)
            briefing = await generate_briefing_data(session)

        (fs,) = briefing["sections"]
        assert fs["type"] == "metrics"
        assert fs["data"]["disk_used_percent"] == 89.0
        assert fs["data"]["reclaimable_mb"] == 1234
        assert fs["data"]["empty_dirs"] == 5

    @pytest.mark.asyncio
    async def test_filesystem_section_survives_psutil_failure(self):
        session = _session_returning(infra=[], log=None, filesystem=_audit(), projects=[])

        with patch(
            "sysadmin.briefing.data.psutil.disk_usage", side_effect=OSError("no mount")
        ):
            briefing = await generate_briefing_data(session)

        (fs,) = briefing["sections"]
        assert fs["data"]["disk_used_percent"] is None

    @pytest.mark.asyncio
    async def test_project_section_notes_stale_branches_and_todos(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project("clean", score=95),
                _project("messy", score=40, stale_branches=3, todos=25),
            ],
        )
        briefing = await generate_briefing_data(session)

        (projects,) = briefing["sections"]
        assert projects["type"] == "table"
        clean = next(p for p in projects["data"] if p["project"] == "clean")
        messy = next(p for p in projects["data"] if p["project"] == "messy")
        assert "note" not in clean
        assert messy["note"] == "3 stale branches, 25 TODOs"


# ---------------------------------------------------------------------------
# send_morning_briefing
# ---------------------------------------------------------------------------


def _mock_notifier(send_result: bool = True) -> MagicMock:
    notifier = MagicMock()
    notifier.startup = AsyncMock()
    notifier.shutdown = AsyncMock()
    notifier.send_briefing_data = AsyncMock(return_value=send_result)
    return notifier


def _patch_scheduler_session(session):
    @asynccontextmanager
    async def fake_session():
        yield session

    return patch("sysadmin.briefing.data.get_scheduler_session", fake_session)


def _project_with_roadmap(name, *, status="active", **roadmap_overrides):
    """A snapshot carrying roadmap findings, for the "Pick This Up" section."""
    roadmap = {
        "next_action": f"Do the {name} thing",
        "next_action_source": "handoff",
        "handoff_age_days": 2,
    }
    roadmap.update(roadmap_overrides)
    row = _project(name)
    row.findings = {"status": status, "roadmap": roadmap}
    return row


class TestNextActionsSection:
    """The "Pick This Up" section — one action per project, not a backlog."""

    @pytest.mark.asyncio
    async def test_section_lists_next_actions(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project_with_roadmap("alfred")],
        )
        data = await generate_briefing_data(session)
        section = next(s for s in data["sections"] if s["title"] == "Pick This Up")

        assert section["type"] == "table"
        assert section["data"] == [
            {"project": "alfred", "next": "Do the alfred thing", "source": "handoff"}
        ]

    @pytest.mark.asyncio
    async def test_stalled_projects_are_marked_and_sorted_first(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project_with_roadmap("fresh", handoff_age_days=1),
                _project_with_roadmap("stalled", handoff_age_days=150),
            ],
        )
        data = await generate_briefing_data(session)
        rows = next(
            s for s in data["sections"] if s["title"] == "Pick This Up"
        )["data"]

        assert rows[0]["project"] == "stalled"
        assert "stalled 150 days" in rows[0]["note"]
        assert "note" not in rows[1]

    @pytest.mark.asyncio
    async def test_capped_so_the_briefing_stays_short(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project_with_roadmap(f"p{i}", handoff_age_days=i) for i in range(12)
            ],
        )
        data = await generate_briefing_data(session)
        rows = next(
            s for s in data["sections"] if s["title"] == "Pick This Up"
        )["data"]
        assert len(rows) == 5

    @pytest.mark.asyncio
    async def test_projects_without_an_action_are_omitted_not_blank(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project_with_roadmap("has-one"),
                _project_with_roadmap("has-none", next_action=None),
            ],
        )
        data = await generate_briefing_data(session)
        rows = next(
            s for s in data["sections"] if s["title"] == "Pick This Up"
        )["data"]
        assert [r["project"] for r in rows] == ["has-one"]

    @pytest.mark.asyncio
    async def test_dormant_projects_excluded(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project_with_roadmap("parked", status="dormant")],
        )
        data = await generate_briefing_data(session)
        assert not any(s["title"] == "Pick This Up" for s in data["sections"])

    @pytest.mark.asyncio
    async def test_section_omitted_entirely_when_nothing_to_show(self):
        """Sections are omitted, not empty — the consumer contract."""
        session = _session_returning(
            infra=[], log=None, filesystem=None, projects=[]
        )
        data = await generate_briefing_data(session)
        assert not any(s["title"] == "Pick This Up" for s in data["sections"])


class TestSendMorningBriefing:
    @pytest.mark.asyncio
    async def test_sends_generated_sections(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        notifier = _mock_notifier(send_result=True)

        with _patch_scheduler_session(session):
            with patch("sysadmin.monitor.notifier.Notifier", return_value=notifier):
                await send_morning_briefing()

        notifier.startup.assert_awaited_once()
        notifier.send_briefing_data.assert_awaited_once()
        (sections,) = notifier.send_briefing_data.await_args.args
        assert sections[0]["title"] == "Infrastructure Status"
        notifier.shutdown.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notifier_shutdown_runs_even_on_delivery_failure(self):
        session = _session_returning(infra=[], log=None, filesystem=None, projects=[])
        notifier = _mock_notifier(send_result=False)

        with _patch_scheduler_session(session):
            with patch("sysadmin.monitor.notifier.Notifier", return_value=notifier):
                await send_morning_briefing()

        notifier.shutdown.assert_awaited_once()


# ---------------------------------------------------------------------------
# Weekly review section (Session 23)
# ---------------------------------------------------------------------------


class TestReviewSection:
    @pytest.mark.asyncio
    async def test_fresh_review_included(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            projects=[],
            review=_review("Portfolio held steady this week."),
        )
        briefing = await generate_briefing_data(session)

        titles = [s["title"] for s in briefing["sections"]]
        assert "Weekly Project Review" in titles
        review_section = next(
            s for s in briefing["sections"] if s["title"] == "Weekly Project Review"
        )
        assert review_section["type"] == "text"
        assert review_section["data"] == "Portfolio held steady this week."

    @pytest.mark.asyncio
    async def test_stale_review_excluded(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            projects=[],
            review=_review(days_old=9),
        )
        briefing = await generate_briefing_data(session)

        titles = [s["title"] for s in briefing["sections"]]
        assert "Weekly Project Review" not in titles

    @pytest.mark.asyncio
    async def test_no_review_no_section(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        briefing = await generate_briefing_data(session)

        titles = [s["title"] for s in briefing["sections"]]
        assert "Weekly Project Review" not in titles


# ---------------------------------------------------------------------------
# Weekly disk review section (Session 24 Tier 3)
# ---------------------------------------------------------------------------


class TestDiskReviewSection:
    """The disk review reuses the project review's freshness rule.

    ``_build_review_section`` is parameterised by model, so these tests
    guard that the second caller is wired up — not that the 8-day rule
    works, which TestReviewSection already covers.
    """

    @pytest.mark.asyncio
    async def test_fresh_disk_review_included(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            projects=[],
            disk_review=_disk_review("Junk is coming from Downloads."),
        )
        briefing = await generate_briefing_data(session)

        section = next(
            s for s in briefing["sections"] if s["title"] == "Weekly Disk Review"
        )
        assert section["type"] == "text"
        assert section["data"] == "Junk is coming from Downloads."

    @pytest.mark.asyncio
    async def test_stale_disk_review_excluded(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            projects=[],
            disk_review=_disk_review(days_old=9),
        )
        briefing = await generate_briefing_data(session)

        assert "Weekly Disk Review" not in [
            s["title"] for s in briefing["sections"]
        ]

    @pytest.mark.asyncio
    async def test_both_reviews_appear_project_first(self):
        session = _session_returning(
            infra=[_service("postgres")],
            log=None,
            filesystem=None,
            projects=[],
            review=_review("Portfolio steady."),
            disk_review=_disk_review("Disk steady."),
        )
        briefing = await generate_briefing_data(session)

        titles = [s["title"] for s in briefing["sections"]]
        assert titles.index("Weekly Project Review") < titles.index(
            "Weekly Disk Review"
        )

    @pytest.mark.asyncio
    async def test_no_disk_review_no_section(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        briefing = await generate_briefing_data(session)

        assert "Weekly Disk Review" not in [
            s["title"] for s in briefing["sections"]
        ]


# ---------------------------------------------------------------------------
# The envelope (Session 36)
# ---------------------------------------------------------------------------


class TestEnvelope:
    """`schema`, `period`, `summary`, `alerts`, `facts` — added, never swapped."""

    @pytest.mark.asyncio
    async def test_alfreds_two_keys_survive(self):
        """The regression this whole design is arranged around.

        `adapt_sysadmin` reads `payload["sections"]` and returns a single
        red error section if it is absent or not a list, and reads
        `generated_at` into `produced_at`.  The envelope is additive
        precisely so that neither moves.
        """
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        briefing = await generate_briefing_data(session)

        assert isinstance(briefing["sections"], list)
        assert briefing["generated_at"]
        # No second stamp holding the same value — one name, one meaning.
        assert "generated" not in briefing

    @pytest.mark.asyncio
    async def test_envelope_keys_present(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        briefing = await generate_briefing_data(session)

        assert briefing["schema"] == SCHEMA_VERSION
        assert briefing["source"] == "sysadmin-service"
        assert set(briefing["period"]) == {"from", "to", "anchor"}
        assert isinstance(briefing["summary"], str) and briefing["summary"]
        assert isinstance(briefing["alerts"], list)
        assert isinstance(briefing["facts"], dict)

    @pytest.mark.asyncio
    async def test_period_is_anchored_to_the_schedule(self):
        """Not to the last pull — two consumers polling would each shorten
        the other's window, and the span must mean one thing."""
        session = _session_returning(infra=[], log=None, filesystem=None, projects=[])
        briefing = await generate_briefing_data(session)

        period = briefing["period"]
        assert period["anchor"] == "schedule"
        start = datetime.fromisoformat(period["from"])
        end = datetime.fromisoformat(period["to"])
        assert start < end
        assert end - start <= timedelta(days=1)
        assert start.astimezone().hour == 6

    @pytest.mark.asyncio
    async def test_facts_holds_no_rows(self):
        """A facts block containing the whole payload cannot be diffed.

        Counts and identifiers only: every list in it is a list of
        scalars, never of the rows the sections render.
        """
        session = _session_returning(
            infra=[_service("postgres"), _service("redis", "unreachable")],
            log=None,
            filesystem=None,
            projects=[_project_with_roadmap(f"p{i}") for i in range(9)],
        )
        briefing = await generate_briefing_data(session)

        def scalars_only(value, path="facts"):
            if isinstance(value, dict):
                for key, item in value.items():
                    scalars_only(item, f"{path}.{key}")
            elif isinstance(value, list):
                for item in value:
                    assert not isinstance(item, (dict, list)), f"{path} carries rows"

        scalars_only(briefing["facts"])


# ---------------------------------------------------------------------------
# SNAG-BRIEF-001 — Project Health published everything ever scanned
# ---------------------------------------------------------------------------


class TestProjectHealthFilter:
    @pytest.mark.asyncio
    async def test_only_active_projects_are_published(self):
        """26 rows including a project retired in July was the symptom.

        The same payload's "Pick This Up" listed 5 and the board returned
        6 — one document, three answers to "what is on this box".
        """
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project_with_roadmap("live"),
                _project_with_roadmap("retired", status="archived"),
                _project_with_roadmap("parked", status="dormant"),
            ],
        )
        briefing = await generate_briefing_data(session)

        health = next(s for s in briefing["sections"] if s["title"] == "Project Health")
        assert [row["project"] for row in health["data"]] == ["live"]

    @pytest.mark.asyncio
    async def test_both_project_sections_agree_on_the_population(self):
        """The defect was two sections in one document disagreeing."""
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[
                _project_with_roadmap("live"),
                _project_with_roadmap("retired", status="archived"),
            ],
        )
        briefing = await generate_briefing_data(session)

        by_title = {s["title"]: s["data"] for s in briefing["sections"]}
        assert {r["project"] for r in by_title["Project Health"]} == {
            r["project"] for r in by_title["Pick This Up"]
        }

    @pytest.mark.asyncio
    async def test_worst_scores_come_first(self):
        """Descending order plus a cap would show exactly the rows that
        carry no information — every project sitting on 100."""
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project("good", 95), _project("bad", 30), _project("mid", 70)],
        )
        briefing = await generate_briefing_data(session)

        health = next(s for s in briefing["sections"] if s["title"] == "Project Health")
        assert [row["project"] for row in health["data"]] == ["bad", "mid", "good"]

    @pytest.mark.asyncio
    async def test_capped_and_the_omission_is_counted(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project(f"p{i}", score=i) for i in range(12)],
        )
        briefing = await generate_briefing_data(session)

        health = next(s for s in briefing["sections"] if s["title"] == "Project Health")
        assert len(health["data"]) == 5
        assert briefing["facts"]["projects"]["active"] == 12
        assert briefing["facts"]["projects"]["omitted"] == 7
        assert "showing the 5 lowest" in briefing["summary"]


# ---------------------------------------------------------------------------
# SNAG-BRIEF-002 — a next action cut mid-word with no marker
# ---------------------------------------------------------------------------


class TestNextActionTruncation:
    @pytest.mark.asyncio
    async def test_a_long_action_is_cut_visibly(self):
        long_action = "Review the scoring sample and decide what to do about it " * 6
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project_with_roadmap("va", next_action=long_action)],
        )
        briefing = await generate_briefing_data(session)

        (row,) = next(
            s for s in briefing["sections"] if s["title"] == "Pick This Up"
        )["data"]
        assert row["next"].endswith("… (truncated)")
        assert len(row["next"]) <= NEXT_ACTION_CHARS + len("… (truncated)") + 1

    @pytest.mark.asyncio
    async def test_a_short_action_is_left_alone(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[_project_with_roadmap("va")],
        )
        briefing = await generate_briefing_data(session)

        (row,) = next(
            s for s in briefing["sections"] if s["title"] == "Pick This Up"
        )["data"]
        assert row["next"] == "Do the va thing"


# ---------------------------------------------------------------------------
# Alerts — grouped by incident, counted by row
# ---------------------------------------------------------------------------


class TestAlerts:
    @pytest.mark.asyncio
    async def test_counts_are_exact_while_the_list_is_capped(self):
        """Grouping in SQL and capping in Python, in that order.

        Capping in SQL would quietly make `open` mean "open, of the ten I
        looked at" — and this table holds 547,814 rows for one unresolved
        `Log error: kernel`.
        """
        rows = [
            _alert_row(f"incident {i}", severity="warning", occurrences=100)
            for i in range(15)
        ]
        session = _session_returning(
            infra=[], log=None, filesystem=None, projects=[], alerts=rows
        )
        briefing = await generate_briefing_data(session)

        assert len(briefing["alerts"]) == 10
        assert briefing["facts"]["alerts"]["incidents"] == 15
        assert briefing["facts"]["alerts"]["open"] == 1500
        assert briefing["facts"]["alerts"]["by_severity"]["warning"] == 1500

    @pytest.mark.asyncio
    async def test_summary_counts_incidents_not_rows(self):
        session = _session_returning(
            infra=[],
            log=None,
            filesystem=None,
            projects=[],
            alerts=[_alert_row("kernel noise", "critical", occurrences=547814)],
        )
        briefing = await generate_briefing_data(session)

        assert "1 open alert incident" in briefing["summary"]

    @pytest.mark.asyncio
    async def test_no_alerts_no_clause(self):
        session = _session_returning(infra=[], log=None, filesystem=None, projects=[])
        briefing = await generate_briefing_data(session)

        assert "alert" not in briefing["summary"]


# ---------------------------------------------------------------------------
# The prose — deterministic, and the staleness Alfred cannot see
# ---------------------------------------------------------------------------


class TestSummary:
    @pytest.mark.asyncio
    async def test_summary_reports_what_the_facts_say(self):
        session = _session_returning(
            infra=[_service("postgres"), _service("redis", "unreachable")],
            log=None,
            filesystem=None,
            projects=[],
        )
        briefing = await generate_briefing_data(session)

        assert briefing["summary"].startswith("1 of 2 services healthy; redis down.")

    def test_summary_is_a_pure_function_of_facts(self):
        """No LLM in the 06:00 path.  The two weekly reviews pay for
        narration with a figure-free prompt and a markdown stripper; a
        summary that is only numbers has nothing to gain from that and a
        down llama-server to lose."""
        facts = {
            "services": {"total": 3, "healthy": 3, "failing": [], "measured_at": None},
            "alerts": {
                "open": 0,
                "incidents": 0,
                "shown": 0,
                "by_severity": {"critical": 0, "warning": 0, "info": 0},
            },
        }
        assert summarise(facts) == summarise(facts) == "All 3 services healthy."

    def test_nothing_measured_says_so(self):
        assert "Nothing has been measured yet" in summarise({})

    @pytest.mark.asyncio
    async def test_stale_data_is_named_because_generated_at_cannot_say_it(self):
        """The hole this envelope exists to close.

        Alfred's staleness rule reads `generated_at`, which on a pulled
        payload is seconds old however long ago the agent behind it died.
        """
        old = _project("forgotten", 55)
        old.scanned_at = datetime.now(UTC) - timedelta(days=3)
        session = _session_returning(
            infra=[], log=None, filesystem=None, projects=[old]
        )
        briefing = await generate_briefing_data(session)

        assert briefing["facts"]["stale_sources"] == ["projects"]
        assert "projects is over a day old" in briefing["summary"]

    @pytest.mark.asyncio
    async def test_fresh_data_is_not_flagged(self):
        session = _session_returning(
            infra=[], log=None, filesystem=None, projects=[_project("live", 90)]
        )
        briefing = await generate_briefing_data(session)

        assert briefing["facts"]["stale_sources"] == []
        assert "over a day old" not in briefing["summary"]


class TestBuildFacts:
    def test_facts_are_derived_never_measured_separately(self):
        """A facts block with its own queries would be a second producer
        able to disagree with the first."""
        gathered = {
            "services": {
                "items": [{"name": "a", "status": "ok"}, {"name": "b", "status": "down"}],
                "measured_at": datetime.now(UTC).isoformat(),
            },
            "logs": None,
            "filesystem": None,
            "projects": {"health": [], "actions": [], "scored": 0, "measured_at": None},
            "alerts": {
                "items": [],
                "open": 0,
                "incidents": 0,
                "shown": 0,
                "by_severity": {"critical": 0, "warning": 0, "info": 0},
            },
            "project_review": None,
            "disk_review": None,
        }
        facts = build_facts(gathered, datetime.now(UTC))

        assert facts["services"] == {
            "total": 2,
            "healthy": 1,
            "failing": ["b"],
            "unmonitored": 0,
            "measured_at": gathered["services"]["measured_at"],
        }
        assert "projects" not in facts


class TestSkippedServices:
    """A declared non-check is not a failure.

    `skipped` (migration 009) marks a service the estate has decided not
    to monitor and said why — a GUI unit bound to
    `graphical-session.target`, or `monitor: false` with a reason.
    Counting it as failing reports a *decision* as a fault.
    """

    @pytest.mark.asyncio
    async def test_a_skipped_service_is_not_reported_down(self):
        session = _session_returning(
            infra=[
                _service("postgres", "ok"),
                _service("sysadmin-tray", "skipped"),
                _service("ollama", "unreachable"),
            ],
            log=None,
            filesystem=None,
            projects=[],
        )
        briefing = await generate_briefing_data(session)

        services = briefing["facts"]["services"]
        assert services["failing"] == ["ollama"]
        assert services["total"] == 2
        assert services["unmonitored"] == 1
        assert "sysadmin-tray" not in briefing["summary"]

    @pytest.mark.asyncio
    async def test_skipped_alone_still_reads_healthy(self):
        """Four units on this estate are skipped by design.  Treating them
        as unhealthy pinned Alfred's grid permanently false."""
        session = _session_returning(
            infra=[_service("postgres", "ok"), _service("sysadmin-tray", "skipped")],
            log=None,
            filesystem=None,
            projects=[],
        )
        briefing = await generate_briefing_data(session)

        (infra,) = briefing["sections"]
        assert infra["data"]["all_services_healthy"] is True
        assert briefing["summary"].startswith("All 1 services healthy.")
