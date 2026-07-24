"""Tests for the morning briefing data generator.

DB access is mocked at the session level (same pattern as
tests/test_routers.py); psutil and the notifier are patched.
The section builders run in a fixed order — infrastructure, logs,
filesystem, projects — so ``session.execute`` uses ``side_effect``
to feed each query its result.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.models.filesystem_audit import FilesystemAudit
from sysadmin.models.log_summary import LogSummary
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.models.service_health import ServiceHealth
from sysadmin.services.briefing import generate_briefing_data, send_morning_briefing

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


def _session_returning(infra, log, filesystem, projects):
    """Mock session whose execute() feeds each section builder in order."""
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _result_all(infra),
            _result_one(log),
            _result_one(filesystem),
            _result_all(projects),
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

        with patch("sysadmin.services.briefing.psutil.disk_usage") as mock_disk:
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

        with patch("sysadmin.services.briefing.psutil.disk_usage") as mock_disk:
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
            "sysadmin.services.briefing.psutil.disk_usage", side_effect=OSError("no mount")
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

    return patch("sysadmin.services.briefing.get_scheduler_session", fake_session)


class TestSendMorningBriefing:
    @pytest.mark.asyncio
    async def test_sends_generated_sections(self):
        session = _session_returning(
            infra=[_service("postgres")], log=None, filesystem=None, projects=[]
        )
        notifier = _mock_notifier(send_result=True)

        with _patch_scheduler_session(session):
            with patch("sysadmin.services.notifier.Notifier", return_value=notifier):
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
            with patch("sysadmin.services.notifier.Notifier", return_value=notifier):
                await send_morning_briefing()

        notifier.shutdown.assert_awaited_once()
