"""ApiWorker tests for the /api/files/* and project-detail fetches.

Kept in their own module (rather than appended to ``test_client.py``)
because Session 19 and Session 18 touch this area in parallel.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from sysadmin_tray.client import ApiWorker
from sysadmin_tray.models import (
    DuplicatesResponse,
    FileStatusResponse,
    FileTrendsResponse,
    LargeFilesResponse,
    MisplacedFilesResponse,
    ProjectDetailResponse,
)


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.fixture
def worker():
    w = ApiWorker("http://test:8500")
    yield w
    w.cleanup()


class TestFetchFileStatus:
    def test_emits_parsed_status(self, worker):
        worker.file_status_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {
                    "scan_root": "/home/gaddi",
                    "scanned_at": "2026-07-24T02:00:00+00:00",
                    "summary": {"duplicate_groups": 4},
                    "reclaimable_mb": 1024.0,
                    "quick_wins": {"empty_dirs": 3, "stale_caches": 9},
                }
            )
            worker.fetch_file_status()

        emitted = worker.file_status_ready.emit.call_args[0][0]
        assert isinstance(emitted, FileStatusResponse)
        assert emitted.has_data
        assert emitted.quick_wins.stale_caches == 9

    def test_hits_the_expected_url(self, worker):
        worker.file_status_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response({})
            worker.fetch_file_status()
        assert client.get.call_args[0][0] == "http://test:8500/api/files/status"

    def test_no_data_message_is_not_an_error(self, worker):
        worker.file_status_ready = MagicMock()
        worker.file_fetch_failed = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response({"message": "No audit data yet"})
            worker.fetch_file_status()

        worker.file_fetch_failed.emit.assert_not_called()
        assert worker.file_status_ready.emit.call_args[0][0].has_data is False


class TestFetchFileCollections:
    def test_duplicates(self, worker):
        worker.file_duplicates_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {"duplicate_groups": [{"hash": "a", "files": ["/x", "/y"]}], "count": 1}
            )
            worker.fetch_file_duplicates()

        emitted = worker.file_duplicates_ready.emit.call_args[0][0]
        assert isinstance(emitted, DuplicatesResponse)
        assert emitted.count == 1

    def test_large_files(self, worker):
        worker.file_large_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {"large_files": [{"path": "/big", "size_mb": 900.0}], "count": 1}
            )
            worker.fetch_file_large()

        emitted = worker.file_large_ready.emit.call_args[0][0]
        assert isinstance(emitted, LargeFilesResponse)
        assert emitted.large_files[0].path == "/big"

    def test_misplaced_files(self, worker):
        worker.file_misplaced_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {"misplaced_files": {"images": ["/a.png"]}, "count": 1}
            )
            worker.fetch_file_misplaced()

        emitted = worker.file_misplaced_ready.emit.call_args[0][0]
        assert isinstance(emitted, MisplacedFilesResponse)
        assert emitted.misplaced_files["images"] == ["/a.png"]

    def test_trends(self, worker):
        worker.file_trends_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {"scans": [], "count": 0, "forecast": {"insufficient_data": True}}
            )
            worker.fetch_file_trends()

        emitted = worker.file_trends_ready.emit.call_args[0][0]
        assert isinstance(emitted, FileTrendsResponse)
        assert emitted.forecast.insufficient_data is True


class TestFileFetchFailures:
    def test_404_emits_an_empty_model_not_a_failure(self, worker):
        """No audit data yet is an empty state, not an error."""
        worker.file_duplicates_ready = MagicMock()
        worker.file_fetch_failed = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {"detail": "No audit data yet"}, status_code=404
            )
            worker.fetch_file_duplicates()

        worker.file_fetch_failed.emit.assert_not_called()
        emitted = worker.file_duplicates_ready.emit.call_args[0][0]
        assert emitted.duplicate_groups == []

    def test_connection_error_reports_failure(self, worker):
        worker.file_large_ready = MagicMock()
        worker.file_fetch_failed = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.side_effect = httpx.ConnectError("refused")
            worker.fetch_file_large()

        worker.file_large_ready.emit.assert_not_called()
        what, message = worker.file_fetch_failed.emit.call_args[0]
        assert what == "large files"
        assert "refused" in message

    def test_server_error_reports_failure(self, worker):
        worker.file_status_ready = MagicMock()
        worker.file_fetch_failed = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response({}, status_code=500)
            worker.fetch_file_status()

        worker.file_status_ready.emit.assert_not_called()
        worker.file_fetch_failed.emit.assert_called_once()

    def test_malformed_payload_reports_failure(self, worker):
        worker.file_trends_ready = MagicMock()
        worker.file_fetch_failed = MagicMock()
        resp = _mock_response(None)
        resp.json.side_effect = ValueError("not json")
        with patch.object(worker, "_client") as client:
            client.get.return_value = resp
            worker.fetch_file_trends()

        worker.file_trends_ready.emit.assert_not_called()
        worker.file_fetch_failed.emit.assert_called_once()


class TestFileActions:
    def test_scan_posts_and_reports_success(self, worker):
        worker.file_scan_triggered = MagicMock()
        with patch.object(worker, "_client") as client:
            client.post.return_value = _mock_response({"status": "scan_triggered"})
            worker.trigger_file_scan()

        assert client.post.call_args[0][0] == "http://test:8500/api/files/scan"
        success, _ = worker.file_scan_triggered.emit.call_args[0]
        assert success is True

    def test_scan_failure_is_reported(self, worker):
        worker.file_scan_triggered = MagicMock()
        with patch.object(worker, "_client") as client:
            client.post.side_effect = httpx.ConnectError("refused")
            worker.trigger_file_scan()

        success, message = worker.file_scan_triggered.emit.call_args[0]
        assert success is False
        assert "refused" in message

    def test_clean_sends_confirm_true(self, worker):
        worker.stale_caches_cleaned = MagicMock()
        with patch.object(worker, "_client") as client:
            client.post.return_value = _mock_response(
                {
                    "status": "cleaned",
                    "removed_caches": 12,
                    "removed_empty_dirs": 5,
                    "details": {"caches": [], "empty_dirs": []},
                }
            )
            worker.clean_stale_caches()

        url = client.post.call_args[0][0]
        assert url.endswith("/api/files/clean/stale-caches")
        assert client.post.call_args[1]["params"] == {"confirm": "true"}

        success, message = worker.stale_caches_cleaned.emit.call_args[0]
        assert success is True
        assert "12 caches" in message
        assert "5 empty dirs" in message

    def test_clean_without_confirmation_response_is_a_failure(self, worker):
        """A ``confirmation_required`` answer must not read as success."""
        worker.stale_caches_cleaned = MagicMock()
        with patch.object(worker, "_client") as client:
            client.post.return_value = _mock_response(
                {"status": "confirmation_required", "message": "Set confirm=true"}
            )
            worker.clean_stale_caches()

        success, message = worker.stale_caches_cleaned.emit.call_args[0]
        assert success is False
        assert message == "Set confirm=true"

    def test_clean_transport_error_is_reported(self, worker):
        worker.stale_caches_cleaned = MagicMock()
        with patch.object(worker, "_client") as client:
            client.post.side_effect = httpx.ConnectError("refused")
            worker.clean_stale_caches()

        success, message = worker.stale_caches_cleaned.emit.call_args[0]
        assert success is False
        assert "refused" in message


class TestFetchProjectDetail:
    def test_emits_history_with_project_name(self, worker):
        worker.project_detail_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response(
                {
                    "name": "pa",
                    "current": {"health_score": 70},
                    "history": [
                        {"health_score": 70, "scanned_at": "2026-07-24T00:00:00+00:00"},
                        {"health_score": 65, "scanned_at": "2026-07-23T00:00:00+00:00"},
                    ],
                }
            )
            worker.fetch_project_detail("pa", 30)

        assert client.get.call_args[1]["params"] == {"limit": 30}
        name, detail = worker.project_detail_ready.emit.call_args[0]
        assert name == "pa"
        assert isinstance(detail, ProjectDetailResponse)
        assert len(detail.history) == 2

    def test_unknown_project_emits_none(self, worker):
        worker.project_detail_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.return_value = _mock_response({}, status_code=404)
            worker.fetch_project_detail("nope")

        name, detail = worker.project_detail_ready.emit.call_args[0]
        assert name == "nope"
        assert detail is None

    def test_connection_error_emits_none(self, worker):
        worker.project_detail_ready = MagicMock()
        with patch.object(worker, "_client") as client:
            client.get.side_effect = httpx.ConnectError("refused")
            worker.fetch_project_detail("pa")

        assert worker.project_detail_ready.emit.call_args[0][1] is None
