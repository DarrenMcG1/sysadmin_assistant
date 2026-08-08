"""Integration tests for key API endpoints via the FastAPI test client.

Tests use mocked DB sessions — no real database needed.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.models.alert import Alert
from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service_health(
    name: str, status: str = "ok", response_time_ms: int = 50
) -> ServiceHealth:
    row = ServiceHealth(
        service_name=name,
        status=status,
        response_time_ms=response_time_ms,
        details={},
    )
    row.id = uuid.uuid4()
    row.checked_at = datetime.now(UTC)
    return row


def _make_resource_snapshot(**overrides) -> ResourceSnapshot:
    defaults = dict(
        cpu_percent=25.0,
        ram_used_mb=8000,
        ram_total_mb=16000,
        ram_percent=50.0,
        swap_used_mb=512,
        swap_total_mb=4096,
        disk_usage={"/": {"total_gb": 500, "used_gb": 200, "free_gb": 300, "percent": 40}},
        gpu_usage={},
        load_avg_1m=1.0,
        load_avg_5m=1.5,
        load_avg_15m=1.2,
    )
    defaults.update(overrides)
    row = ResourceSnapshot(**defaults)
    row.id = uuid.uuid4()
    row.recorded_at = datetime.now(UTC)
    return row


def _make_alert(
    title: str = "Test alert",
    severity: str = "warning",
    resolved: bool = False,
) -> Alert:
    row = Alert(
        agent="sysadmin",
        severity=severity,
        title=title,
        message="Test message",
        details={},
    )
    row.id = uuid.uuid4()
    row.acknowledged = False
    row.resolved = resolved
    row.created_at = datetime.now(UTC)
    return row


def _mock_scalars_all(mock_session, rows):
    """Configure mock_session.execute to return rows via scalars().all()."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _mock_scalar_one_or_none(mock_session, row):
    """Configure mock_session.execute to return a single row or None."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    mock_session.execute = AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# /api/sysadmin/status
# ---------------------------------------------------------------------------


class TestStatusEndpoint:
    @pytest.mark.asyncio
    async def test_get_all_statuses(self, test_client, mock_session):
        rows = [
            _make_service_health("test-api", "ok", 42),
            _make_service_health("test-tcp", "ok", 10),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status")
        assert resp.status_code == 200
        data = resp.json()

        assert "services" in data
        assert "all_healthy" in data
        assert data["all_healthy"] is True
        assert len(data["services"]) == 2

    @pytest.mark.asyncio
    async def test_unhealthy_service_sets_all_healthy_false(self, test_client, mock_session):
        rows = [
            _make_service_health("test-api", "ok"),
            _make_service_health("test-tcp", "critical"),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status")
        data = resp.json()
        assert data["all_healthy"] is False


class TestServiceStatusHistory:
    @pytest.mark.asyncio
    async def test_get_service_history(self, test_client, mock_session):
        rows = [_make_service_health("test-api", "ok", 42)]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/status/test-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "test-api"
        assert len(data["checks"]) == 1

    @pytest.mark.asyncio
    async def test_empty_history(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/sysadmin/status/nonexistent")
        data = resp.json()
        assert data["checks"] == []


# ---------------------------------------------------------------------------
# /api/sysadmin/resources
# ---------------------------------------------------------------------------


class TestResourcesEndpoint:
    @pytest.mark.asyncio
    async def test_get_resources(self, test_client, mock_session):
        snapshot = _make_resource_snapshot()
        _mock_scalar_one_or_none(mock_session, snapshot)

        resp = await test_client.get("/api/sysadmin/resources")
        assert resp.status_code == 200
        data = resp.json()

        assert "cpu_percent" in data
        assert "ram" in data
        assert data["ram"]["used_mb"] == 8000
        assert "disk" in data
        assert "load_avg" in data

    @pytest.mark.asyncio
    async def test_no_resources_yet(self, test_client, mock_session):
        _mock_scalar_one_or_none(mock_session, None)

        resp = await test_client.get("/api/sysadmin/resources")
        data = resp.json()
        assert "message" in data


class TestResourceHistory:
    @pytest.mark.asyncio
    async def test_get_resource_history(self, test_client, mock_session):
        rows = [_make_resource_snapshot()]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/resources/history?hours=24")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_hours"] == 24
        assert len(data["snapshots"]) == 1


# ---------------------------------------------------------------------------
# /api/sysadmin/alerts
# ---------------------------------------------------------------------------


class TestAlertsEndpoint:
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, test_client, mock_session):
        rows = [_make_alert("High RAM", "warning")]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["alerts"][0]["title"] == "High RAM"

    @pytest.mark.asyncio
    async def test_get_all_alerts(self, test_client, mock_session):
        rows = [
            _make_alert("Active", resolved=False),
            _make_alert("Resolved", resolved=True),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/alerts?active_only=false")
        data = resp.json()
        assert data["count"] == 2


class TestAlertAcknowledge:
    @pytest.mark.asyncio
    async def test_ack_alert(self, test_client, mock_session):
        alert = _make_alert("Test")
        _mock_scalar_one_or_none(mock_session, alert)

        resp = await test_client.post(f"/api/sysadmin/alerts/{alert.id}/ack")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "acknowledged"

    @pytest.mark.asyncio
    async def test_ack_missing_alert_returns_404(self, test_client, mock_session):
        """Acking a nonexistent alert must be a real 404, not a 200 tuple (SNAG-API-001)."""
        _mock_scalar_one_or_none(mock_session, None)

        resp = await test_client.post(f"/api/sysadmin/alerts/{uuid.uuid4()}/ack")
        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"] == "Alert not found"


# ---------------------------------------------------------------------------
# /api/sysadmin/dnd
# ---------------------------------------------------------------------------


class TestDndEndpoints:
    @pytest.mark.asyncio
    async def test_get_dnd_status(self, test_client):
        with patch("sysadmin.monitor.routers.sysadmin.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {
                "active": False,
                "manual_override": None,
                "schedule_active": False,
            }
            resp = await test_client.get("/api/sysadmin/dnd")

        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data

    @pytest.mark.asyncio
    async def test_toggle_dnd_on(self, test_client):
        with patch("sysadmin.monitor.routers.sysadmin.dnd_manager") as mock_dnd:
            mock_dnd.get_status.return_value = {"active": True, "manual_override": True}
            resp = await test_client.post(
                "/api/sysadmin/dnd", json={"enabled": True}
            )

        assert resp.status_code == 200
        mock_dnd.set_manual_override.assert_called_once_with(True)


# ---------------------------------------------------------------------------
# /api/sysadmin/ports
# ---------------------------------------------------------------------------


class TestPortsEndpoint:
    @pytest.mark.asyncio
    async def test_get_ports(self, test_client):
        with patch(
            "sysadmin.monitor.routers.sysadmin.SysAdminAgent.get_port_usage",
            return_value=[
                {"port": 5432, "address": "127.0.0.1", "pid": 1234, "process": "postgres"},
            ],
        ):
            resp = await test_client.get("/api/sysadmin/ports")

        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["ports"][0]["port"] == 5432

    @pytest.mark.asyncio
    async def test_get_ports_runs_off_event_loop(self, test_client):
        """The blocking psutil scan must not run on the event loop (SNAG-API-003)."""
        import asyncio

        def _assert_no_loop():
            # asyncio.to_thread runs this in a worker thread, where there
            # is no running event loop; on the loop this would succeed.
            with pytest.raises(RuntimeError):
                asyncio.get_running_loop()
            return []

        with patch(
            "sysadmin.monitor.routers.sysadmin.SysAdminAgent.get_port_usage",
            side_effect=_assert_no_loop,
        ):
            resp = await test_client.get("/api/sysadmin/ports")

        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ---------------------------------------------------------------------------
# /api/projects recommendations (Session 22)
# ---------------------------------------------------------------------------


def _make_project_snapshot(name, score, findings):
    from sysadmin.projects.models.project_snapshot import ProjectSnapshot

    row = ProjectSnapshot(
        project_name=name,
        project_path=f"/projects/{name}",
        health_score=score,
        findings=findings,
    )
    row.id = uuid.uuid4()
    row.scanned_at = datetime.now(UTC)
    return row


def _mock_scalars_first(mock_session, row):
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    mock_session.execute = AsyncMock(return_value=result)


class TestProjectRecommendations:
    @pytest.mark.asyncio
    async def test_recommendations_for_a_project(self, test_client, mock_session):
        row = _make_project_snapshot(
            "demo", 75, {"missing_readme": True, "stale": "No commits in 90 days"}
        )
        _mock_scalars_first(mock_session, row)

        resp = await test_client.get("/api/projects/demo/recommendations")
        assert resp.status_code == 200
        data = resp.json()

        assert data["project"] == "demo"
        assert data["health_score"] == 75
        assert data["potential_score"] == 100
        assert data["count"] == 2
        assert data["recommendations"][0]["points"] == 15

    @pytest.mark.asyncio
    async def test_unknown_project_404s(self, test_client, mock_session):
        _mock_scalars_first(mock_session, None)

        resp = await test_client.get("/api/projects/nope/recommendations")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_status_echoed_from_findings(self, test_client, mock_session):
        row = _make_project_snapshot("old", 100, {"status": "archived"})
        _mock_scalars_first(mock_session, row)

        resp = await test_client.get("/api/projects/old/recommendations")
        assert resp.json()["status"] == "archived"


class TestPortfolioActions:
    @pytest.mark.asyncio
    async def test_ranked_across_projects(self, test_client, mock_session):
        rows = [
            _make_project_snapshot("tidy", 100, {}),
            _make_project_snapshot("risky", 100, {"no_remote": True}),
            _make_project_snapshot(
                "messy", 70, {"missing_readme": True, "stale": "No commits in 90 days"}
            ),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/projects/actions")
        assert resp.status_code == 200
        data = resp.json()

        # Risk first, then points descending; tidy contributes nothing
        assert data["actions"][0]["project"] == "risky"
        assert data["actions"][0]["severity"] == "risk"
        assert data["actions"][1]["points"] == 15
        assert data["projects_with_actions"] == 2
        assert data["count"] == data["total_available"] == 3

    @pytest.mark.asyncio
    async def test_limit_truncates_but_reports_total(self, test_client, mock_session):
        rows = [
            _make_project_snapshot(
                "messy", 60,
                {"missing_readme": True, "missing_claude_md": True,
                 "stale_git_lock": True},
            ),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/projects/actions?limit=2")
        data = resp.json()

        assert data["count"] == 2
        assert data["total_available"] == 3
        assert len(data["actions"]) == 2

    @pytest.mark.asyncio
    async def test_actions_route_not_shadowed_by_name_route(
        self, test_client, mock_session
    ):
        """Regression: /actions must not be captured as project 'actions'."""
        _mock_scalars_all(mock_session, [])

        resp = await test_client.get("/api/projects/actions")
        assert resp.status_code == 200
        assert resp.json()["actions"] == []


# ---------------------------------------------------------------------------
# /api/projects/review (Session 23)
# ---------------------------------------------------------------------------


def _make_review(narrative="Fine week.", llm_used=True):
    from sysadmin.projects.models.project_review import ProjectReview

    row = ProjectReview(period_days=7, narrative=narrative, llm_used=llm_used)
    row.id = uuid.uuid4()
    row.generated_at = datetime.now(UTC)
    row.stats = {"totals": {"project_count": 1}}
    return row


class TestProjectReviewEndpoints:
    @pytest.mark.asyncio
    async def test_latest_review_returned(self, test_client, mock_session):
        _mock_scalars_first(mock_session, _make_review("Steady progress."))

        resp = await test_client.get("/api/projects/review")
        assert resp.status_code == 200
        data = resp.json()

        assert data["narrative"] == "Steady progress."
        assert data["llm_used"] is True
        assert data["stats"]["totals"]["project_count"] == 1

    @pytest.mark.asyncio
    async def test_404_before_first_review(self, test_client, mock_session):
        _mock_scalars_first(mock_session, None)

        resp = await test_client.get("/api/projects/review")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_on_demand(self, test_client, mock_session):
        review = _make_review("Fresh review.", llm_used=False)

        with patch(
            "sysadmin.projects.router.project_review.generate_review",
            new=AsyncMock(return_value=review),
        ):
            resp = await test_client.post("/api/projects/review/generate")

        assert resp.status_code == 200
        data = resp.json()
        assert data["narrative"] == "Fresh review."
        assert data["llm_used"] is False

    @pytest.mark.asyncio
    async def test_generate_409_without_snapshots(self, test_client, mock_session):
        with patch(
            "sysadmin.projects.router.project_review.generate_review",
            new=AsyncMock(return_value=None),
        ):
            resp = await test_client.post("/api/projects/review/generate")

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_review_route_not_shadowed_by_name_route(
        self, test_client, mock_session
    ):
        """Regression: /review must not be captured as project 'review'."""
        _mock_scalars_first(mock_session, None)

        resp = await test_client.get("/api/projects/review")
        # 404 from "no review yet", NOT from "project not found"
        assert resp.json()["detail"] == "No review generated yet"


# ---------------------------------------------------------------------------
# /api/files/actions  (Session 24 Tier 2)
# ---------------------------------------------------------------------------


def _make_filesystem_audit(findings: dict) -> FilesystemAudit:
    audit = FilesystemAudit(scan_root="/home/gaddi", findings=findings)
    audit.id = uuid.uuid4()
    audit.scanned_at = datetime.now(UTC)
    return audit


def _mock_actions_session(mock_session, audit, disk_rows):
    """Two executes: the latest audit, then the disk-usage series.

    ``/api/files/actions`` is the only files route that reads a second
    table — ``resource_snapshots`` is what knows disk *occupancy*, which
    is what the risk ranking is built on.
    """
    audit_result = MagicMock()
    audit_result.scalar_one_or_none.return_value = audit

    snapshot_result = MagicMock()
    snapshot_result.__iter__ = lambda self: iter(disk_rows)

    mock_session.execute = AsyncMock(side_effect=[audit_result, snapshot_result])


def _climbing_disk(start: float, per_day: float, days: int) -> list:
    """``(recorded_at, disk_usage)`` rows climbing at a fixed rate."""
    base = datetime.now(UTC) - timedelta(days=days)
    return [
        MagicMock(
            recorded_at=base + timedelta(days=i),
            disk_usage={"/": {"total_gb": 500.0, "percent": start + per_day * i}},
        )
        for i in range(days)
    ]


class TestFileActions:
    @pytest.mark.asyncio
    async def test_ranked_by_reclaimable_megabytes(self, test_client, mock_session):
        findings = {
            "duplicates": [
                {"hash": "h", "files": ["/a", "/b"], "count": 2,
                 "size_mb": 100.0, "reclaimable_mb": 100.0},
            ],
            "old_downloads": [
                {"path": "/d/big.iso", "days_old": 90, "size_mb": 900.0},
            ],
            "empty_dirs": ["/home/gaddi/x"],
        }
        _mock_actions_session(mock_session, _make_filesystem_audit(findings), [])

        resp = await test_client.get("/api/files/actions")
        assert resp.status_code == 200
        data = resp.json()

        assert [a["kind"] for a in data["actions"]] == [
            "downloads", "duplicates", "empty_dirs"
        ]
        assert data["total_reclaimable_mb"] == pytest.approx(1000.0)
        assert data["count"] == data["total_available"] == 3
        assert data["disk_forecast"] is None  # no resource history supplied

    @pytest.mark.asyncio
    async def test_imminent_disk_crossing_ranks_first(self, test_client, mock_session):
        findings = {
            "old_downloads": [
                {"path": "/d/big.iso", "days_old": 90, "size_mb": 5000.0},
            ],
        }
        # 75 % climbing 1 pp/day → crosses 80 % in about 5 days
        _mock_actions_session(
            mock_session,
            _make_filesystem_audit(findings),
            _climbing_disk(70.0, 1.0, 6),
        )

        resp = await test_client.get("/api/files/actions")
        data = resp.json()

        assert data["actions"][0]["kind"] == "risk"
        assert data["actions"][0]["severity"] == "risk"
        assert data["actions"][1]["kind"] == "downloads"  # 5 GB ranks second
        assert data["disk_forecast"]["percent"] == 80.0
        assert data["disk_forecast"]["state"] == "projected"

    @pytest.mark.asyncio
    async def test_flat_disk_raises_no_risk(self, test_client, mock_session):
        findings = {"empty_dirs": ["/home/gaddi/x"]}
        _mock_actions_session(
            mock_session,
            _make_filesystem_audit(findings),
            _climbing_disk(50.0, 0.0, 6),
        )

        resp = await test_client.get("/api/files/actions")
        data = resp.json()

        assert all(a["severity"] != "risk" for a in data["actions"])
        assert data["disk_forecast"] is None

    @pytest.mark.asyncio
    async def test_limit_truncates_but_totals_stay_whole(
        self, test_client, mock_session
    ):
        """The headline reclaim must not shrink because limit did."""
        findings = {
            "duplicates": [
                {"hash": "h", "files": ["/a", "/b"], "count": 2,
                 "size_mb": 100.0, "reclaimable_mb": 100.0},
            ],
            "old_downloads": [{"path": "/d/a", "days_old": 90, "size_mb": 900.0}],
            "empty_dirs": ["/home/gaddi/x"],
        }
        _mock_actions_session(mock_session, _make_filesystem_audit(findings), [])

        resp = await test_client.get("/api/files/actions?limit=1")
        data = resp.json()

        assert len(data["actions"]) == 1
        assert data["count"] == 1
        assert data["total_available"] == 3
        assert data["total_reclaimable_mb"] == pytest.approx(1000.0)

    @pytest.mark.asyncio
    async def test_404_before_the_first_scan(self, test_client, mock_session):
        _mock_actions_session(mock_session, None, [])

        resp = await test_client.get("/api/files/actions")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No audit data yet"

    @pytest.mark.asyncio
    async def test_clean_audit_returns_an_empty_ranking(
        self, test_client, mock_session
    ):
        _mock_actions_session(mock_session, _make_filesystem_audit({}), [])

        resp = await test_client.get("/api/files/actions")
        data = resp.json()

        assert data["actions"] == []
        assert data["total_available"] == 0
        assert data["total_reclaimable_mb"] == 0.0
        assert data["scanned_at"] is not None


# ---------------------------------------------------------------------------
# /api/files/review  (Session 24 Tier 3)
# ---------------------------------------------------------------------------


class TestDiskReviewEndpoints:
    def _review(self, narrative="Disk /: 67.4% used.", llm_used=True):
        from sysadmin.files.models.disk_review import DiskReview

        review = DiskReview(
            period_days=7,
            narrative=narrative,
            llm_used=llm_used,
            model_used="dria-agent-a-3b" if llm_used else None,
            stats={"disk": {"current_percent": 67.4}},
        )
        review.id = uuid.uuid4()
        review.generated_at = datetime.now(UTC)
        return review

    @pytest.mark.asyncio
    async def test_get_latest_review(self, test_client, mock_session):
        _mock_scalars_first(mock_session, self._review())

        resp = await test_client.get("/api/files/review")
        assert resp.status_code == 200
        data = resp.json()

        assert data["narrative"] == "Disk /: 67.4% used."
        assert data["llm_used"] is True
        assert data["stats"]["disk"]["current_percent"] == 67.4

    @pytest.mark.asyncio
    async def test_404_before_any_review(self, test_client, mock_session):
        _mock_scalars_first(mock_session, None)

        resp = await test_client.get("/api/files/review")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "No review generated yet"

    @pytest.mark.asyncio
    async def test_generate_returns_the_new_review(self, test_client, mock_session):
        review = self._review("Fresh disk review.", llm_used=False)

        with patch(
            "sysadmin.files.router.disk_review.generate_review",
            new=AsyncMock(return_value=review),
        ):
            resp = await test_client.post("/api/files/review/generate")

        assert resp.status_code == 200
        data = resp.json()
        assert data["narrative"] == "Fresh disk review."
        assert data["llm_used"] is False
        assert data["model_used"] is None

    @pytest.mark.asyncio
    async def test_generate_409_without_audits(self, test_client, mock_session):
        with patch(
            "sysadmin.files.router.disk_review.generate_review",
            new=AsyncMock(return_value=None),
        ):
            resp = await test_client.post("/api/files/review/generate")

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_review_route_not_shadowed_by_actions(
        self, test_client, mock_session
    ):
        """Regression guard: /review and /actions are sibling literals."""
        _mock_scalars_first(mock_session, None)

        resp = await test_client.get("/api/files/review")
        assert resp.json()["detail"] == "No review generated yet"
