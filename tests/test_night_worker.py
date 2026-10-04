"""Tests for Night Worker integration endpoint enhancements.

Covers the enhanced /api/logs/recent, /api/sysadmin/resources/history,
and /api/files/trends endpoints.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.files.models.filesystem_audit import FilesystemAudit
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

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
    row.logged_at = datetime.now(UTC) - timedelta(hours=hours_ago)
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
    row.recorded_at = datetime.now(UTC) - timedelta(hours=hours_ago)
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
    row.scanned_at = datetime.now(UTC) - timedelta(days=days_ago)
    return row


def _mock_scalars_all(mock_session, rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_session.execute = AsyncMock(return_value=result)


def _mock_trends(mock_session, scans, window=None):
    """Answer ``/api/files/trends``' two queries: the newest scans, then the
    forecast window's (scanned_at, reclaimable_mb) rows.  ``window``
    defaults to the same audits, which is the case where every scan is
    inside the span of days."""
    scans_result = MagicMock()
    scans_result.scalars.return_value.all.return_value = scans
    window_result = MagicMock()
    window_result.__iter__.return_value = iter(
        [
            MagicMock(scanned_at=a.scanned_at, total_reclaimable_mb=a.total_reclaimable_mb)
            for a in (scans if window is None else window)
        ]
    )
    mock_session.execute = AsyncMock(side_effect=[scans_result, window_result])


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
        _mock_trends(mock_session, audits)

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
        _mock_trends(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        assert data["forecast"]["insufficient_data"] is True

    @pytest.mark.asyncio
    async def test_forecast_no_growth(self, test_client, mock_session):
        audits = [
            _make_audit(days_ago=7, reclaimable_mb=500),
            _make_audit(days_ago=0, reclaimable_mb=500),
        ]
        _mock_trends(mock_session, audits)

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
        _mock_trends(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        forecast = data["forecast"]
        # 1gb milestone already passed, should not appear
        assert "1gb" not in forecast.get("projected_milestones", {})

    @pytest.mark.asyncio
    async def test_fitted_line_past_milestone_is_due_now(
        self, test_client, mock_session
    ):
        # Fit: slope 100 MB/day, intercept ~333, so the line stands at
        # ~1,333 MB at the latest scan while the scan itself reads 1,000.
        # 1 GB is due now, dated at the latest scan, not dropped.
        audits = [
            _make_audit(days_ago=10, reclaimable_mb=0),
            _make_audit(days_ago=5, reclaimable_mb=1500),
            _make_audit(days_ago=0, reclaimable_mb=1000),
        ]
        _mock_trends(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        milestones = resp.json()["forecast"]["projected_milestones"]
        assert milestones["1gb"] == audits[-1].scanned_at.strftime("%Y-%m-%d")
        # The milestone still ahead of the line is projected as before.
        assert milestones["5gb"] > milestones["1gb"]

    @pytest.mark.asyncio
    async def test_a_total_past_the_old_rungs_still_shows_milestones(
        self, test_client, mock_session
    ):
        # This box's shape: ~40 GB reclaimable and growing.  Under the old
        # 1/5/10 GB rungs no milestone could show; the ladder shows the
        # rungs above the total and none at or below it (Session 342).
        audits = [
            _make_audit(days_ago=14, reclaimable_mb=39_000),
            _make_audit(days_ago=7, reclaimable_mb=39_900),
            _make_audit(days_ago=0, reclaimable_mb=40_762),
        ]
        _mock_trends(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        milestones = resp.json()["forecast"]["projected_milestones"]
        assert set(milestones) == {"50gb", "100gb"}
        assert milestones["50gb"] < milestones["100gb"]

    @pytest.mark.asyncio
    async def test_the_fit_reads_the_window_not_the_newest_scans(
        self, test_client, mock_session
    ):
        # SNAG-FILES-002's shape: ten scans inside the last day, all on one
        # flat stretch, while the month holds two steps.  The ten newest
        # read no growth; the span of days reads the step rate.
        now = datetime.now(UTC)
        flat = []
        for i in range(10):
            audit = _make_audit(reclaimable_mb=40_762)
            audit.scanned_at = now - timedelta(hours=2 * i)
            flat.append(audit)
        window = [
            _make_audit(days_ago=29, reclaimable_mb=37_000),
            _make_audit(days_ago=20, reclaimable_mb=37_000),
            _make_audit(days_ago=19, reclaimable_mb=38_500),
            _make_audit(days_ago=10, reclaimable_mb=38_500),
            _make_audit(days_ago=9, reclaimable_mb=40_762),
            *reversed(flat),
        ]
        _mock_trends(mock_session, flat, window)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        # ``limit`` still governs the scans list, and only that.
        assert data["count"] == 10
        forecast = data["forecast"]
        assert forecast["growth_rate_mb_per_day"] > 100
        assert forecast["data_points"] == len(window)
        assert set(forecast["projected_milestones"]) == {"50gb", "100gb"}

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query, days", [("", 30), ("?history_days=7", 7)])
    async def test_the_window_is_a_span_of_days(
        self, test_client, mock_session, query, days
    ):
        _mock_trends(mock_session, [])

        before = datetime.now(UTC)
        await test_client.get(f"/api/files/trends{query}")
        after = datetime.now(UTC)

        statement = mock_session.execute.await_args_list[1].args[0]
        assert statement._limit_clause is None
        (cutoff,) = statement.compile().params.values()
        assert (
            before - timedelta(days=days) <= cutoff <= after - timedelta(days=days)
        )

    @pytest.mark.asyncio
    async def test_scans_still_returned(self, test_client, mock_session):
        audits = [_make_audit(days_ago=1), _make_audit(days_ago=0)]
        _mock_trends(mock_session, audits)

        resp = await test_client.get("/api/files/trends")
        data = resp.json()
        assert data["count"] == 2
        assert len(data["scans"]) == 2
