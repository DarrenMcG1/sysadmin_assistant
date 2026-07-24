"""Parsing tests for the Session 19 /api/files/* and project-detail contracts.

The routers are not annotated with ``response_model=``, so these shapes
are enforced only on the parse side — which makes it worth pinning both
the populated payloads and the "no data yet" / 404 shapes the backend
legitimately returns.
"""

from __future__ import annotations

import pytest

from sysadmin_tray.models import (
    DuplicatesResponse,
    FileStatusResponse,
    FileTrendsResponse,
    LargeFilesResponse,
    MisplacedFilesResponse,
    ProjectDetailResponse,
)

FULL_STATUS = {
    "scan_root": "/home/gaddi",
    "scanned_at": "2026-07-24T02:00:00+00:00",
    "summary": {
        "similar_folders": 3,
        "misplaced_files": 12,
        "old_downloads": 5,
        "large_files": 7,
        "duplicate_groups": 4,
        "empty_dirs": 21,
        "stale_project_dirs": 30,
        "stale_files": 900,
    },
    "reclaimable_mb": 4096.5,
    "quick_wins": {"empty_dirs": 21, "stale_caches": 18, "stale_cache_mb": 812.4},
}


class TestFileStatusResponse:
    def test_parses_full_payload(self):
        status = FileStatusResponse.from_dict(FULL_STATUS)
        assert status.has_data
        assert status.scan_root == "/home/gaddi"
        assert status.summary.duplicate_groups == 4
        assert status.reclaimable_mb == pytest.approx(4096.5)
        assert status.quick_wins.stale_caches == 18
        assert status.quick_wins.total == 39

    def test_no_data_message_parses_to_empty_defaults(self):
        status = FileStatusResponse.from_dict(
            {"message": "No audit data yet. Trigger a scan with POST /api/files/scan"}
        )
        assert status.has_data is False
        assert status.reclaimable_mb == 0.0
        assert status.summary.large_files == 0
        assert status.quick_wins.total == 0
        assert "No audit data" in status.message

    def test_empty_payload_parses(self):
        status = FileStatusResponse.from_dict({})
        assert status.has_data is False
        assert status.quick_wins.empty_dirs == 0

    def test_null_quick_wins_becomes_defaults(self):
        status = FileStatusResponse.from_dict(
            {**FULL_STATUS, "quick_wins": None, "reclaimable_mb": None}
        )
        assert status.quick_wins.total == 0
        assert status.reclaimable_mb == 0.0

    def test_unknown_fields_are_ignored(self):
        status = FileStatusResponse.from_dict({**FULL_STATUS, "brand_new": 1})
        assert status.scan_root == "/home/gaddi"


class TestDuplicatesResponse:
    def test_parses_groups_and_count(self):
        data = DuplicatesResponse.from_dict(
            {
                "duplicate_groups": [
                    {"hash": "abc123", "files": ["/a", "/b"], "count": 2},
                    {"hash": "def456", "files": ["/c", "/d", "/e"], "count": 3},
                ],
                "count": 2,
            }
        )
        assert data.count == 2
        assert data.duplicate_groups[1].count == 3
        assert data.duplicate_groups[0].files == ["/a", "/b"]

    def test_missing_group_count_is_derived_from_files(self):
        data = DuplicatesResponse.from_dict(
            {"duplicate_groups": [{"hash": "x", "files": ["/a", "/b", "/c"]}]}
        )
        assert data.count == 1
        assert data.duplicate_groups[0].count == 3

    def test_empty_payload_parses(self):
        data = DuplicatesResponse.from_dict({})
        assert data.duplicate_groups == []
        assert data.count == 0


class TestLargeFilesResponse:
    def test_parses_entries(self):
        data = LargeFilesResponse.from_dict(
            {
                "large_files": [
                    {"path": "/home/gaddi/big.iso", "size_mb": 4300.2},
                    {"path": "/home/gaddi/mid.tar", "size_mb": 512.0},
                ],
                "count": 2,
            }
        )
        assert data.count == 2
        assert data.large_files[0].size_mb == pytest.approx(4300.2)

    def test_null_size_becomes_zero(self):
        data = LargeFilesResponse.from_dict(
            {"large_files": [{"path": "/x", "size_mb": None}]}
        )
        assert data.large_files[0].size_mb == 0.0

    def test_count_defaults_to_length(self):
        data = LargeFilesResponse.from_dict({"large_files": [{"path": "/x"}]})
        assert data.count == 1


class TestMisplacedFilesResponse:
    def test_parses_category_mapping(self):
        data = MisplacedFilesResponse.from_dict(
            {
                "misplaced_files": {
                    "images": ["/home/gaddi/a.png", "/home/gaddi/b.png"],
                    "documents": ["/home/gaddi/c.pdf"],
                },
                "count": 3,
            }
        )
        assert data.count == 3
        assert data.misplaced_files["images"] == [
            "/home/gaddi/a.png",
            "/home/gaddi/b.png",
        ]

    def test_missing_count_sums_all_categories(self):
        data = MisplacedFilesResponse.from_dict(
            {"misplaced_files": {"images": ["/a", "/b"], "docs": ["/c"]}}
        )
        assert data.count == 3

    def test_null_mapping_becomes_empty(self):
        data = MisplacedFilesResponse.from_dict({"misplaced_files": None})
        assert data.misplaced_files == {}
        assert data.count == 0


class TestFileTrendsResponse:
    def test_parses_scans_and_forecast(self):
        data = FileTrendsResponse.from_dict(
            {
                "scans": [
                    {"scanned_at": "2026-07-20T02:00:00+00:00", "reclaimable_mb": 900.0},
                    {"scanned_at": "2026-07-21T02:00:00+00:00", "reclaimable_mb": 950.0},
                ],
                "count": 2,
                "forecast": {
                    "growth_rate_mb_per_day": 50.0,
                    "current_reclaimable_mb": 950.0,
                    "data_points": 2,
                    "projected_milestones": {"1gb": "2026-07-22"},
                },
            }
        )
        assert data.count == 2
        assert data.scans[1].reclaimable_mb == pytest.approx(950.0)
        assert data.forecast.growth_rate_mb_per_day == pytest.approx(50.0)
        assert data.forecast.projected_milestones["1gb"] == "2026-07-22"

    def test_insufficient_data_forecast(self):
        data = FileTrendsResponse.from_dict(
            {"scans": [], "count": 0, "forecast": {"insufficient_data": True}}
        )
        assert data.forecast.insufficient_data is True
        assert data.forecast.projected_milestones == {}

    def test_forecast_without_projections(self):
        data = FileTrendsResponse.from_dict(
            {"scans": [], "forecast": {"growth_rate_mb_per_day": 0.0}}
        )
        assert data.forecast.projected_milestones == {}

    def test_empty_payload_parses(self):
        data = FileTrendsResponse.from_dict({})
        assert data.scans == []
        assert data.forecast.insufficient_data is False


class TestProjectDetailResponse:
    def test_parses_history_newest_first(self):
        detail = ProjectDetailResponse.from_dict(
            {
                "name": "sysadmin_assistant",
                "current": {"health_score": 88},
                "history": [
                    {"health_score": 88, "scanned_at": "2026-07-24T02:00:00+00:00"},
                    {"health_score": 80, "scanned_at": "2026-07-23T02:00:00+00:00"},
                ],
            }
        )
        assert detail.name == "sysadmin_assistant"
        assert [p.health_score for p in detail.history] == [88, 80]
        assert detail.current["health_score"] == 88

    def test_null_scores_become_zero(self):
        detail = ProjectDetailResponse.from_dict(
            {"history": [{"health_score": None, "scanned_at": None}]}
        )
        assert detail.history[0].health_score == 0

    def test_empty_payload_parses(self):
        detail = ProjectDetailResponse.from_dict({})
        assert detail.history == []
        assert detail.current == {}
