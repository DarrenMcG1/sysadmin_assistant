"""Tests for Night Worker integration endpoint enhancements.

Covers the enhanced /api/logs/recent, /api/sysadmin/resources/history,
and /api/files/trends endpoints.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.models.filesystem_audit import FilesystemAudit
from sysadmin.models.log_entry import LogEntry
from sysadmin.models.resource_snapshot import ResourceSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_log_entry(
    source: str = "test-service",
    severity: str = "warning",
    message: str = "something happened",
    hours_ago: float = 0,
) -> LogEntry:
    row = LogEntry(source=source, severity=severity, message=message)
    row.id = uuid.uuid4()
    row.logged_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return row


def _make_resource_snapshot(hours_ago: float = 0, **overrides) -> ResourceSnapshot:
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
    row.recorded_at = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    return row


def _make_audit(
    days_ago: int = 0,
    reclaimable_mb: int = 500,
) -> FilesystemAudit:
    row = FilesystemAudit(
        scan_root="/home/test",
        total_reclaimable_mb=reclaimable_mb,
    )
    row.id = uuid.uuid4()
    row.similar_folders_count = 2
    row.misplaced_files_count = 5
    row.old_downloads_count = 3
    row.large_files_count = 1
    row.duplicate_groups_count = 4
    row.empty_dirs_count = 6
    row.stale_project_dirs_count = 2
    row.stale_files_count = 0
    row.findings = {}
    row.scanned_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return row


def _mock_scalars_all(mock_session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


# ---------------------------------------------------------------------------
# /api/logs/recent — Night Worker enhancements
# ---------------------------------------------------------------------------


class TestLogsRecentEnhanced:
    @pytest.mark.asyncio
    async def test_severity_all_returns_all_entries(self, test_client, mock_session):
        rows = [
            _make_log_entry(severity="info"),
            _make_log_entry(severity="warning"),
            _make_log_entry(severity="error"),
        ]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/logs/recent?hours=24&severity=all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3

    @pytest.mark.asyncio
    async def test_high_limit_accepted(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/logs/recent?limit=2000")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_limit_over_max_rejected(self, test_client, mock_session):
        resp = await test_client.get("/api/logs/recent?limit=2001")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_hours_up_to_168_accepted(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/logs/recent?hours=168")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_offset_param(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/logs/recent?offset=50&limit=50")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/sysadmin/resources/history — days param
# ---------------------------------------------------------------------------


class TestResourceHistoryEnhanced:
    @pytest.mark.asyncio
    async def test_days_param(self, test_client, mock_session):
        rows = [_make_resource_snapshot()]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/resources/history?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period_hours"] == 168  # 7 * 24

    @pytest.mark.asyncio
    async def test_days_overrides_hours(self, test_client, mock_session):
        rows = [_make_resource_snapshot()]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/resources/history?days=3&hours=1")
        data = resp.json()
        assert data["period_hours"] == 72  # days takes precedence

    @pytest.mark.asyncio
    async def test_includes_disk_usage(self, test_client, mock_session):
        rows = [_make_resource_snapshot()]
        _mock_scalars_all(mock_session, rows)

        resp = await test_client.get("/api/sysadmin/resources/history?hours=24")
        data = resp.json()
        snapshot = data["snapshots"][0]
        assert "disk_usage" in snapshot
        assert "/" in snapshot["disk_usage"]

    @pytest.mark.asyncio
    async def test_default_24_hours(self, test_client, mock_session):
        _mock_scalars_all(mock_session, [])
        resp = await test_client.get("/api/sysadmin/resources/history")
        data = resp.json()
        assert data["period_hours"] == 24


# ---------------------------------------------------------------------------
# /api/files/trends — forecast
# ---------------------------------------------------------------------------


class TestFilesTrendsForecast:
    @pytest.mark.asyncio
    async def test_forecast_with_growth(self, test_client, mock_session):
        audits = [
            _make_audit(days_ago=7, reclaimable_mb=200),
            _make_audit(days_ago=3, reclaimable_mb=400),
            _make_audit(days_ago=0, reclaimable_mb=600),
        ]
        _mock_scalars_all(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        assert resp.status_code == 200
        data = resp.json()

        assert "forecast" in data
        forecast = data["forecast"]
        assert forecast["growth_rate_mb_per_day"] > 0
        assert forecast["current_reclaimable_mb"] == 600
        assert "projected_milestones" in forecast
        assert "1gb" in forecast["projected_milestones"]

    @pytest.mark.asyncio
    async def test_forecast_insufficient_data(self, test_client, mock_session):
        audits = [_make_audit(days_ago=0, reclaimable_mb=100)]
        _mock_scalars_all(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        assert data["forecast"]["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_forecast_no_growth(self, test_client, mock_session):
        audits = [
            _make_audit(days_ago=7, reclaimable_mb=500),
            _make_audit(days_ago=0, reclaimable_mb=500),
        ]
        _mock_scalars_all(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        forecast = data["forecast"]
        assert forecast["growth_rate_mb_per_day"] == 0.0
        assert "projected_milestones" not in forecast

    @pytest.mark.asyncio
    async def test_forecast_already_past_milestone(self, test_client, mock_session):
        audits = [
            _make_audit(days_ago=7, reclaimable_mb=2000),
            _make_audit(days_ago=0, reclaimable_mb=3000),
        ]
        _mock_scalars_all(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        forecast = data["forecast"]
        # 1gb milestone already passed, should not appear
        assert "1gb" not in forecast.get("projected_milestones", {})

    @pytest.mark.asyncio
    async def test_scans_still_returned(self, test_client, mock_session):
        audits = [_make_audit(days_ago=1), _make_audit(days_ago=0)]
        _mock_scalars_all(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        assert data["count"] == 2
        assert len(data["scans"]) == 2
