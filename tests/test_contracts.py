"""Round-trip tests for the shared contracts (backend → wire → tray).

Real endpoint responses (served by the real app with response_model
enforcement) must parse cleanly through the SAME contract models the
tray uses — the seam where SNAG-TRAY-005 lived.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.contracts import (
    AlertsResponse,
    ResourceHistoryResponse,
    ResourceResponse,
    StatusResponse,
)
from sysadmin.models.alert import Alert
from sysadmin.models.resource_snapshot import ResourceSnapshot
from sysadmin.models.service_health import ServiceHealth


def _mock_scalars_all(mock_session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _mock_scalar_one_or_none(mock_session, row):
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=result)


def _service_health(name: str, status: str = "ok") -> ServiceHealth:
    row = ServiceHealth(
        service_name=name, status=status, response_time_ms=12, details={}
    )
    row.id = uuid.uuid4()
    row.checked_at = datetime.now(UTC)
    return row


class TestStatusRoundTrip:
    @pytest.mark.asyncio
    async def test_status_parses_through_tray_contract(self, test_client, mock_session):
        _mock_scalars_all(
            mock_session,
            [_service_health("test-api"), _service_health("test-tcp", "unreachable")],
        )

        resp = await test_client.get("/api/sysadmin/status")
        parsed = StatusResponse.from_dict(resp.json())

        assert [s.name for s in parsed.services] == ["test-api", "test-tcp"]
        assert parsed.services[1].status == "unreachable"
        assert parsed.all_healthy is False
        # controllable comes from config — test-api is controllable, test-infra not
        assert parsed.services[0].controllable is True


class TestAlertsRoundTrip:
    @pytest.mark.asyncio
    async def test_alerts_parse_through_tray_contract(self, test_client, mock_session):
        alert = Alert(
            agent="sysadmin",
            severity="critical",
            title="Disk critical",
            message="/ at 91%",
            details={"service_name": "disk"},
        )
        alert.id = uuid.uuid4()
        alert.acknowledged = False
        alert.resolved = False
        alert.created_at = datetime.now(UTC)
        _mock_scalars_all(mock_session, [alert])

        resp = await test_client.get("/api/sysadmin/alerts")
        parsed = AlertsResponse.from_dict(resp.json())

        assert parsed.count == 1
        assert parsed.critical_count == 1
        assert parsed.alerts[0].service_name == "disk"


class TestResourcesRoundTrip:
    @pytest.mark.asyncio
    async def test_dict_keyed_disk_becomes_sorted_list(self, test_client, mock_session):
        snapshot = ResourceSnapshot(
            cpu_percent=25.0,
            ram_used_mb=8000,
            ram_total_mb=16000,
            ram_percent=50.0,
            swap_used_mb=0,
            swap_total_mb=0,
            disk_usage={
                "/boot": {"total_gb": 0.5, "used_gb": 0.1, "free_gb": 0.4, "percent": 20.0},
                "/": {"total_gb": 500, "used_gb": 445, "free_gb": 55, "percent": 89.0},
            },
            gpu_usage={},
            load_avg_1m=1.0,
            load_avg_5m=1.0,
            load_avg_15m=1.0,
        )
        snapshot.id = uuid.uuid4()
        snapshot.recorded_at = datetime.now(UTC)
        _mock_scalar_one_or_none(mock_session, snapshot)

        resp = await test_client.get("/api/sysadmin/resources")
        parsed = ResourceResponse.from_dict(resp.json())

        assert parsed.cpu_percent == pytest.approx(25.0)
        assert parsed.ram.percent == pytest.approx(50.0)
        assert [d.mount for d in parsed.disk] == ["/", "/boot"]
        assert parsed.disk[0].percent == pytest.approx(89.0)

    @pytest.mark.asyncio
    async def test_no_data_message_parses_to_defaults(self, test_client, mock_session):
        _mock_scalar_one_or_none(mock_session, None)

        resp = await test_client.get("/api/sysadmin/resources")
        parsed = ResourceResponse.from_dict(resp.json())

        assert parsed.cpu_percent == 0.0
        assert parsed.disk == []


class TestHistoryRoundTrip:
    @pytest.mark.asyncio
    async def test_history_parses_through_tray_contract(self, test_client, mock_session):
        snapshot = ResourceSnapshot(
            cpu_percent=10.0,
            ram_used_mb=1,
            ram_total_mb=2,
            ram_percent=50.0,
            swap_used_mb=0,
            swap_total_mb=0,
            disk_usage={},
            gpu_usage={},
            load_avg_1m=0.5,
            load_avg_5m=0.5,
            load_avg_15m=0.5,
        )
        snapshot.id = uuid.uuid4()
        snapshot.recorded_at = datetime.now(UTC)
        _mock_scalars_all(mock_session, [snapshot])

        resp = await test_client.get("/api/sysadmin/resources/history?hours=6")
        parsed = ResourceHistoryResponse.from_dict(resp.json())

        assert parsed.period_hours == 6
        assert parsed.count == 1
        assert parsed.snapshots[0].cpu_percent == pytest.approx(10.0)


class TestRecommendationsRoundTrip:
    @pytest.mark.asyncio
    async def test_recommendations_parse_through_tray_contract(
        self, test_client, mock_session
    ):
        from sysadmin.contracts import ProjectRecommendationsResponse
        from sysadmin.models.project_snapshot import ProjectSnapshot

        row = ProjectSnapshot(
            project_name="demo",
            project_path="/projects/demo",
            health_score=75,
            findings={"missing_readme": True, "no_remote": True},
        )
        row.id = uuid.uuid4()
        row.scanned_at = datetime.now(UTC)

        result = MagicMock()
        result.scalars.return_value.first.return_value = row
        mock_session.execute = AsyncMock(return_value=result)

        resp = await test_client.get("/api/projects/demo/recommendations")
        assert resp.status_code == 200

        parsed = ProjectRecommendationsResponse.from_dict(resp.json())
        assert parsed.project == "demo"
        assert parsed.count == 2
        assert parsed.recommendations[0].severity == "risk"
        assert parsed.potential_score == 85

    @pytest.mark.asyncio
    async def test_portfolio_actions_parse_through_tray_contract(
        self, test_client, mock_session
    ):
        from sysadmin.contracts import PortfolioActionsResponse
        from sysadmin.models.project_snapshot import ProjectSnapshot

        row = ProjectSnapshot(
            project_name="demo",
            project_path="/projects/demo",
            health_score=90,
            findings={"stale_git_lock": True},
        )
        row.id = uuid.uuid4()
        row.scanned_at = datetime.now(UTC)
        _mock_scalars_all(mock_session, [row])

        resp = await test_client.get("/api/projects/actions")
        assert resp.status_code == 200

        parsed = PortfolioActionsResponse.from_dict(resp.json())
        assert parsed.count == 1
        assert parsed.actions[0].project == "demo"
        assert parsed.actions[0].points == 5

    @pytest.mark.asyncio
    async def test_file_actions_parse_through_tray_contract(
        self, test_client, mock_session
    ):
        """The file currency is megabytes, not points — a separate model."""
        from sysadmin.contracts import FileActionsResponse
        from sysadmin.models.filesystem_audit import FilesystemAudit

        audit = FilesystemAudit(
            scan_root="/home/gaddi",
            findings={
                "old_downloads": [
                    {"path": "/d/big.iso", "days_old": 90, "size_mb": 900.0}
                ]
            },
        )
        audit.id = uuid.uuid4()
        audit.scanned_at = datetime.now(UTC)

        audit_result = MagicMock()
        audit_result.scalar_one_or_none.return_value = audit
        snapshot_result = MagicMock()
        snapshot_result.__iter__ = lambda self: iter([])
        mock_session.execute = AsyncMock(
            side_effect=[audit_result, snapshot_result]
        )

        resp = await test_client.get("/api/files/actions")
        assert resp.status_code == 200

        parsed = FileActionsResponse.from_dict(resp.json())
        assert parsed.count == 1
        assert parsed.actions[0].kind == "downloads"
        assert parsed.actions[0].reclaimable_mb == pytest.approx(900.0)
        assert parsed.total_reclaimable_mb == pytest.approx(900.0)
        assert parsed.disk_forecast is None
        assert not hasattr(parsed.actions[0], "points")

    @pytest.mark.asyncio
    async def test_disk_review_parses_through_tray_contract(
        self, test_client, mock_session
    ):
        from sysadmin.contracts import DiskReviewResponse
        from sysadmin.models.disk_review import DiskReview

        review = DiskReview(
            period_days=7,
            narrative="Disk /: 67.4% used.\n\nMess is in ~/Downloads.",
            llm_used=True,
            model_used="dria-agent-a-3b",
            stats={"disk": {"current_percent": 67.4, "delta_pp": 0.1}},
        )
        review.id = uuid.uuid4()
        review.generated_at = datetime.now(UTC)

        result = MagicMock()
        result.scalars.return_value.first.return_value = review
        mock_session.execute = AsyncMock(return_value=result)

        resp = await test_client.get("/api/files/review")
        assert resp.status_code == 200

        parsed = DiskReviewResponse.from_dict(resp.json())
        assert parsed.llm_used is True
        assert parsed.narrative.startswith("Disk /: 67.4% used.")
        assert parsed.stats["disk"]["delta_pp"] == 0.1


class TestReviewRoundTrip:
    @pytest.mark.asyncio
    async def test_review_parses_through_tray_contract(
        self, test_client, mock_session
    ):
        from sysadmin.contracts import ProjectReviewResponse
        from sysadmin.models.project_review import ProjectReview

        row = ProjectReview(period_days=7, narrative="Weekly text.", llm_used=False)
        row.id = uuid.uuid4()
        row.generated_at = datetime.now(UTC)
        row.stats = {"totals": {"project_count": 2}}

        result = MagicMock()
        result.scalars.return_value.first.return_value = row
        mock_session.execute = AsyncMock(return_value=result)

        resp = await test_client.get("/api/projects/review")
        assert resp.status_code == 200

        parsed = ProjectReviewResponse.from_dict(resp.json())
        assert parsed.narrative == "Weekly text."
        assert parsed.llm_used is False
        assert parsed.model_used is None
        assert parsed.stats["totals"]["project_count"] == 2


class TestReliabilityRoundTrip:
    """GET /api/services/reliability — Session 25.

    Parsed through ``sysadmin_tray.models`` rather than
    ``sysadmin.contracts`` so the tray's re-export is exercised too: a
    contract the tray cannot import is a contract the tray does not have.
    """

    @pytest.mark.asyncio
    async def test_reliability_parses_through_tray_contract(
        self, test_client, mock_session
    ):
        from sysadmin_tray.models import ReliabilityResponse

        now = datetime.now(UTC)
        rows = [
            ("test-api", "ok", now - timedelta(seconds=60 * (100 - i)))
            for i in range(50)
        ] + [
            ("test-api", "critical", now - timedelta(seconds=60 * (50 - i)))
            for i in range(50)
        ]
        result = MagicMock()
        result.all.return_value = rows
        mock_session.execute = AsyncMock(return_value=result)

        resp = await test_client.get("/api/services/reliability")
        assert resp.status_code == 200

        parsed = ReliabilityResponse.from_dict(resp.json())
        worst = parsed.services[0]

        assert worst.service == "test-api"
        # The arithmetic survives the wire: score plus its deductions is 100
        assert worst.score == 100 - sum(d.points for d in worst.deductions)
        assert {d.kind for d in worst.deductions} == {"downtime", "instability"}
        assert parsed.summary.services_scored == len(parsed.services)

    @pytest.mark.asyncio
    async def test_unmeasured_service_parses_to_a_full_score(
        self, test_client, mock_session
    ):
        """A configured service with no checks must not arrive as an
        error or an omission — it is a low-confidence 100."""
        from sysadmin_tray.models import ReliabilityResponse

        result = MagicMock()
        result.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result)

        resp = await test_client.get("/api/services/reliability")
        parsed = ReliabilityResponse.from_dict(resp.json())

        assert parsed.count == len(parsed.services)
        assert all(s.score == 100 for s in parsed.services)
        assert all(s.confidence == "low" for s in parsed.services)
        assert parsed.summary.low_confidence == parsed.summary.services_scored
