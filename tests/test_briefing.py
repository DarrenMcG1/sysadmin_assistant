"""Tests for the morning briefing data generator.

DB access is mocked at the session level (same pattern as
tests/test_routers.py); psutil and the notifier are patched.
The section builders run in a fixed order — infrastructure, logs,
filesystem, projects — so ``session.execute`` uses ``side_effect``
to feed each query its result.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.briefing.data import generate_briefing_data, send_morning_briefing
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


def _session_returning(
    infra,
    log,
    filesystem,
    projects,
    review=None,
    disk_review=None,
    next_actions=None,
):
    """Mock session whose execute() feeds each section builder in order.

    Order matters and is positional: adding a section to
    ``generate_briefing_data`` without adding a result here exhausts the
    iterator and every test in this file fails at once.  (It did, when
    "Pick This Up" was added — the docstring was right.)

    ``next_actions`` is last in the signature but **fifth** in the list,
    because it feeds the section that runs between project health and the
    weekly reviews.  Keyword position and execution order are not the
    same thing here; the list below is the one that matters.  It defaults
    to the ``projects`` rows, since both builders read the same latest-
    snapshot-per-project query and a test that sets up project health
    almost always means the same fixtures for both.
    """
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result_all(infra),
            _result_one(log),
            _result_one(filesystem),
            _result_all(projects),
            _result_all(projects if next_actions is None else next_actions),
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
            projects=[],
            next_actions=[_project_with_roadmap("alfred")],
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
            projects=[],
            next_actions=[
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
            projects=[],
            next_actions=[
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
            projects=[],
            next_actions=[
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
            projects=[],
            next_actions=[_project_with_roadmap("parked", status="dormant")],
        )
        data = await generate_briefing_data(session)
        assert not any(s["title"] == "Pick This Up" for s in data["sections"])

    @pytest.mark.asyncio
    async def test_section_omitted_entirely_when_nothing_to_show(self):
        """Sections are omitted, not empty — the consumer contract."""
        session = _session_returning(
            infra=[], log=None, filesystem=None, projects=[], next_actions=[]
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
