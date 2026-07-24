"""Tests for the dashboard Files tab.

Driven entirely through the ``FakeClient`` signals from ``conftest.py``
— no worker thread, no sockets, no live backend.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sysadmin_tray.dashboard.files_tab import (
    FORECAST_HISTORY_HOURS,
    VIEW_DUPLICATES,
    VIEW_LARGE,
    VIEW_MISPLACED,
    FilesTab,
)
from sysadmin_tray.models import (
    DuplicatesResponse,
    FileStatusResponse,
    FileTrendsResponse,
    LargeFilesResponse,
    MisplacedFilesResponse,
    ResourceHistoryResponse,
)

from .conftest import render_offscreen

BASE = datetime(2026, 7, 1, 12, 0, 0)

STATUS_PAYLOAD = {
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
    "reclaimable_mb": 2048.0,
    "quick_wins": {"empty_dirs": 21, "stale_caches": 18, "stale_cache_mb": 812.0},
}

DUPLICATES_PAYLOAD = {
    "duplicate_groups": [
        {"hash": "aaaaaaaaaaaabbbb", "files": ["/home/a.jpg", "/home/b.jpg"], "count": 2},
        {"hash": "cccccccccccc", "files": ["/home/c.txt", "/home/d.txt"], "count": 2},
    ],
    "count": 2,
}

MISPLACED_PAYLOAD = {
    "misplaced_files": {
        "images": ["/home/gaddi/a.png", "/home/gaddi/b.png"],
        "documents": ["/home/gaddi/c.pdf"],
    },
    "count": 3,
}

LARGE_PAYLOAD = {
    "large_files": [
        {"path": "/home/gaddi/big.iso", "size_mb": 4300.0},
        {"path": "/home/gaddi/mid.tar", "size_mb": 512.0},
    ],
    "count": 2,
}


@pytest.fixture
def tab(fake_client):
    return FilesTab(fake_client)


def _table_texts(table, column: int) -> list[str]:
    return [
        table.item(row, column).text()
        for row in range(table.rowCount())
        if table.item(row, column) is not None
    ]


class TestConstruction:
    def test_builds_without_data(self, tab):
        assert tab._summary_label.text() == "Loading…"
        assert tab._table.rowCount() == 0

    def test_default_view_is_duplicates(self, tab):
        assert tab._current_view() == VIEW_DUPLICATES

    def test_offers_all_three_views(self, tab):
        views = [
            tab._view_combo.itemData(i) for i in range(tab._view_combo.count())
        ]
        assert views == [VIEW_DUPLICATES, VIEW_MISPLACED, VIEW_LARGE]

    def test_has_no_destructive_buttons_beyond_the_cache_clean(self, tab):
        """Session 19 is read-only apart from the pre-existing clean."""
        from PyQt6.QtWidgets import QPushButton

        labels = {b.text() for b in tab.findChildren(QPushButton)}
        assert labels == {"Rescan", "Clean stale caches…"}

    def test_renders_headless(self, tab):
        assert not render_offscreen(tab, width=900, height=700).isNull()


class TestRefresh:
    def test_requests_every_read_endpoint(self, tab, fake_client):
        tab.refresh()
        for request in (
            "request_file_status",
            "request_file_trends",
            "request_file_duplicates",
            "request_file_misplaced",
            "request_file_large",
        ):
            assert fake_client.called(request) == 1

    def test_requests_a_long_history_window_for_the_forecast(self, tab, fake_client):
        tab.refresh()
        call = next(c for c in fake_client.calls if c[0] == "request_resource_history")
        assert call[1] == FORECAST_HISTORY_HOURS


class TestSummaryPopulation:
    def test_populates_summary_and_reclaimable(self, tab, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(STATUS_PAYLOAD)
        )
        assert "/home/gaddi" in tab._summary_label.text()
        assert "Duplicates: 4" in tab._summary_label.text()
        assert "Large files: 7" in tab._summary_label.text()
        assert tab._reclaimable_label.text() == "Reclaimable: 2.0 GB"

    def test_no_audit_data_shows_the_backend_message(self, tab, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(
                {"message": "No audit data yet. Trigger a scan with POST /api/files/scan"}
            )
        )
        assert "No audit data yet" in tab._summary_label.text()
        assert tab._reclaimable_label.text() == ""

    def test_no_audit_data_falls_back_to_our_own_prompt(self, tab, fake_client):
        fake_client.file_status_updated.emit(FileStatusResponse.from_dict({}))
        assert "press Rescan" in tab._summary_label.text()

    def test_quick_wins_card_is_populated(self, tab, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(STATUS_PAYLOAD)
        )
        assert tab._quick_wins.quick_wins.stale_caches == 18


class TestFindingsTable:
    def test_duplicates_populate_the_table(self, tab, fake_client):
        fake_client.file_duplicates_updated.emit(
            DuplicatesResponse.from_dict(DUPLICATES_PAYLOAD)
        )
        assert tab._table.rowCount() == 2
        assert tab._table.columnCount() == 3
        assert _table_texts(tab._table, 0) == ["2", "2"]
        assert "/home/a.jpg" in tab._table.item(0, 2).text()
        assert "2 duplicate groups" in tab._status_label.text()

    def test_switching_view_renders_misplaced_files(self, tab, fake_client):
        fake_client.file_misplaced_updated.emit(
            MisplacedFilesResponse.from_dict(MISPLACED_PAYLOAD)
        )
        tab._view_combo.setCurrentIndex(1)
        assert tab._current_view() == VIEW_MISPLACED
        # Categories are sorted, so documents comes before images.
        assert _table_texts(tab._table, 0) == ["documents", "images", "images"]
        assert "3 misplaced files" in tab._status_label.text()

    def test_switching_view_renders_large_files(self, tab, fake_client):
        fake_client.file_large_updated.emit(
            LargeFilesResponse.from_dict(LARGE_PAYLOAD)
        )
        tab._view_combo.setCurrentIndex(2)
        assert _table_texts(tab._table, 0) == ["4.2 GB", "512 MB"]
        assert _table_texts(tab._table, 1) == [
            "/home/gaddi/big.iso",
            "/home/gaddi/mid.tar",
        ]

    def test_data_for_an_inactive_view_is_kept_until_selected(self, tab, fake_client):
        fake_client.file_large_updated.emit(
            LargeFilesResponse.from_dict(LARGE_PAYLOAD)
        )
        assert tab._table.rowCount() == 0  # still on Duplicates
        tab._view_combo.setCurrentIndex(2)
        assert tab._table.rowCount() == 2

    def test_empty_findings_are_stated_not_left_blank(self, tab, fake_client):
        fake_client.file_duplicates_updated.emit(
            DuplicatesResponse.from_dict({"duplicate_groups": [], "count": 0})
        )
        assert tab._table.rowCount() == 0
        assert "Nothing found" in tab._status_label.text()

    def test_unloaded_view_says_loading(self, tab):
        tab._view_combo.setCurrentIndex(1)
        assert tab._status_label.text() == "Loading…"


class TestForecastWiring:
    def test_trends_reach_the_forecast_card(self, tab, fake_client):
        fake_client.file_trends_updated.emit(
            FileTrendsResponse.from_dict(
                {
                    "scans": [],
                    "forecast": {
                        "growth_rate_mb_per_day": 10.0,
                        "current_reclaimable_mb": 500.0,
                        "data_points": 3,
                    },
                }
            )
        )
        grid = tab._forecast._trend_grid
        captions = [
            grid.itemAtPosition(r, 0).widget().text()
            for r in range(grid.rowCount())
            if grid.itemAtPosition(r, 0) is not None
        ]
        assert "Reclaimable now" in captions

    def test_resource_history_reaches_the_forecast_card(self, tab, fake_client):
        history = ResourceHistoryResponse.from_dict(
            {
                "count": 3,
                "snapshots": [
                    {
                        "disk_usage": {"/": {"percent": 70.0 + i}},
                        "recorded_at": (BASE + timedelta(days=i)).isoformat(),
                    }
                    for i in range(3)
                ],
            }
        )
        fake_client.resource_history_updated.emit(history)
        grid = tab._forecast._disk_grid
        values = [
            grid.itemAtPosition(r, 1).widget().text()
            for r in range(grid.rowCount())
            if grid.itemAtPosition(r, 1) is not None
        ]
        assert "72.0%" in values


class TestScanAction:
    def test_scan_button_requests_a_rescan(self, tab, fake_client):
        tab._scan_btn.click()
        assert fake_client.called("trigger_file_scan") == 1
        assert tab._scan_btn.isEnabled() is False
        assert tab._scan_btn.text() == "Scanning…"

    def test_scan_result_re_enables_the_button(self, tab, fake_client):
        tab._scan_btn.click()
        fake_client.file_scan_triggered.emit(True, "Filesystem scan triggered")
        assert tab._scan_btn.isEnabled() is True
        assert tab._scan_btn.text() == "Rescan"
        assert "scan triggered" in tab._status_label.text()

    def test_scan_failure_is_surfaced(self, tab, fake_client):
        tab._scan_btn.click()
        fake_client.file_scan_triggered.emit(False, "connection refused")
        assert tab._scan_btn.isEnabled() is True
        assert "refused" in tab._status_label.text()


class TestCleanAction:
    def _load_quick_wins(self, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(STATUS_PAYLOAD)
        )

    def test_confirmation_is_required_before_cleaning(
        self, tab, fake_client, monkeypatch
    ):
        self._load_quick_wins(fake_client)
        monkeypatch.setattr(tab, "_confirm_clean", lambda detail: False)
        tab._quick_wins._clean_btn.click()
        assert fake_client.called("clean_stale_caches") == 0

    def test_confirming_triggers_the_clean(self, tab, fake_client, monkeypatch):
        self._load_quick_wins(fake_client)
        monkeypatch.setattr(tab, "_confirm_clean", lambda detail: True)
        tab._quick_wins._clean_btn.click()
        assert fake_client.called("clean_stale_caches") == 1

    def test_confirmation_spells_out_what_is_deleted(
        self, tab, fake_client, monkeypatch
    ):
        self._load_quick_wins(fake_client)
        shown: list[str] = []

        def _capture(detail: str) -> bool:
            shown.append(detail)
            return False

        monkeypatch.setattr(tab, "_confirm_clean", _capture)
        tab._quick_wins._clean_btn.click()

        assert len(shown) == 1
        assert "18 cache directories" in shown[0]
        assert "21 empty directories" in shown[0]
        assert "812 MB" in shown[0]

    def test_successful_clean_refreshes_and_reports(
        self, tab, fake_client, monkeypatch
    ):
        self._load_quick_wins(fake_client)
        monkeypatch.setattr(tab, "_confirm_clean", lambda detail: True)
        tab._quick_wins._clean_btn.click()

        fake_client.stale_caches_cleaned.emit(True, "Removed 18 caches, 21 empty dirs")
        assert "Removed 18 caches" in tab._quick_wins._result_label.text()
        assert fake_client.called("request_file_status") >= 1

    def test_failed_clean_does_not_refresh(self, tab, fake_client, monkeypatch):
        self._load_quick_wins(fake_client)
        monkeypatch.setattr(tab, "_confirm_clean", lambda detail: True)
        tab._quick_wins._clean_btn.click()
        before = fake_client.called("request_file_status")

        fake_client.stale_caches_cleaned.emit(False, "connection refused")
        assert fake_client.called("request_file_status") == before
        assert "refused" in tab._quick_wins._result_label.text()


class TestErrorHandling:
    def test_fetch_failure_is_reported_in_the_status_bar(self, tab, fake_client):
        fake_client.file_fetch_failed.emit("duplicates", "connection refused")
        assert "Could not load duplicates" in tab._status_label.text()
        assert "refused" in tab._status_label.text()

    def test_connection_lost_disables_actions_and_keeps_data(self, tab, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(STATUS_PAYLOAD)
        )
        fake_client.file_duplicates_updated.emit(
            DuplicatesResponse.from_dict(DUPLICATES_PAYLOAD)
        )

        fake_client.connection_lost.emit()

        assert "unreachable" in tab._status_label.text()
        assert tab._scan_btn.isEnabled() is False
        assert tab._quick_wins._clean_btn.isEnabled() is False
        # Last known findings stay on screen rather than vanishing.
        assert tab._table.rowCount() == 2

    def test_connection_lost_blanks_the_forecast(self, tab, fake_client):
        fake_client.connection_lost.emit()
        grid = tab._forecast._disk_grid
        values = [
            grid.itemAtPosition(r, 1).widget().text()
            for r in range(grid.rowCount())
            if grid.itemAtPosition(r, 1) is not None
        ]
        assert values == ["Backend unreachable"]

    def test_connection_restored_re_enables_and_refetches(self, tab, fake_client):
        fake_client.file_status_updated.emit(
            FileStatusResponse.from_dict(STATUS_PAYLOAD)
        )
        fake_client.connection_lost.emit()
        fake_client.connection_restored.emit()

        assert tab._scan_btn.isEnabled() is True
        assert tab._quick_wins._clean_btn.isEnabled() is True
        assert fake_client.called("request_file_status") >= 1

    def test_renders_headless_after_a_connection_loss(self, tab, fake_client):
        fake_client.connection_lost.emit()
        assert not render_offscreen(tab, width=900, height=700).isNull()
