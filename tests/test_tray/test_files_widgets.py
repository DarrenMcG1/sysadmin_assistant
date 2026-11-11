"""Tests for the Quick Wins and Disk Forecast cards."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sysadmin.files.forecast import ThresholdProjection
from sysadmin_tray.models import (
    FileStatusResponse,
    FileTrendsResponse,
    ResourceHistoryResponse,
)
from sysadmin_tray.styles import AMBER, GREEN, RED, TEXT_MUTED
from sysadmin_tray.widgets.disk_forecast import (
    DiskForecastWidget,
    projection_colour,
    projection_text,
)
from sysadmin_tray.widgets.quick_wins import QuickWinsWidget

from .conftest import render_offscreen

BASE = datetime(2026, 7, 1, 12, 0, 0)


def _history(percents: list[float], mount: str = "/") -> ResourceHistoryResponse:
    return ResourceHistoryResponse.from_dict(
        {
            "count": len(percents),
            "snapshots": [
                {
                    "disk_usage": {mount: {"percent": pct}},
                    "recorded_at": (BASE + timedelta(days=i)).isoformat(),
                }
                for i, pct in enumerate(percents)
            ],
        }
    )


def _grid_rows(grid) -> list[tuple[str, str]]:
    """Read a two-column QGridLayout back as (caption, value) pairs."""
    rows = []
    for row in range(grid.rowCount()):
        caption = grid.itemAtPosition(row, 0)
        value = grid.itemAtPosition(row, 1)
        if caption is not None and value is not None:
            rows.append((caption.widget().text(), value.widget().text()))
    return rows


# ── Quick wins widget ────────────────────────────────────────────────


class TestQuickWinsWidget:
    @pytest.fixture
    def widget(self, qapp):
        return QuickWinsWidget()

    def test_the_card_offers_no_action(self, widget):
        """Finding H1: the clean button deleted off the stored audit."""
        from PyQt6.QtWidgets import QPushButton

        assert widget.findChildren(QPushButton) == []

    def test_populates_counts(self, widget):
        widget.update_from_status(
            FileStatusResponse.from_dict(
                {
                    "scan_root": "/home/gaddi",
                    "scanned_at": "2026-07-24T02:00:00+00:00",
                    "quick_wins": {
                        "empty_dirs": 21,
                        "stale_caches": 18,
                        "stale_cache_mb": 812.4,
                    },
                }
            )
        )
        assert widget._value_labels["empty_dirs"].text() == "21"
        assert widget._value_labels["stale_caches"].text() == "18"
        assert widget._value_labels["stale_cache_mb"].text() == "812 MB"

    def test_large_cache_size_is_shown_in_gigabytes(self, widget):
        widget.update_from_status(
            FileStatusResponse.from_dict(
                {
                    "scan_root": "/home/gaddi",
                    "scanned_at": "2026-07-24T02:00:00+00:00",
                    "quick_wins": {"stale_caches": 388, "stale_cache_mb": 2914.6},
                }
            )
        )
        assert widget._value_labels["stale_cache_mb"].text() == "2.8 GB"

    def test_no_scan_data_says_so(self, widget):
        widget.update_from_status(
            FileStatusResponse.from_dict({"message": "No audit data yet"})
        )
        assert "No scan data" in widget._result_label.text()

    def test_renders_headless(self, widget):
        assert not render_offscreen(widget).isNull()


# ── Disk forecast widget ─────────────────────────────────────────────


class TestProjectionFormatting:
    def test_projected_shows_date_and_horizon(self):
        caption, value = projection_text(
            ThresholdProjection(80.0, "projected", 12.0, "2026-08-05")
        )
        assert caption == "Reaches 80%"
        assert "2026-08-05" in value
        assert "12 days" in value

    def test_a_date_from_the_short_fit_names_its_window(self):
        # The Growth row is the whole-series rate; without this the two
        # rows can read "shrinking" beside a date a week away.
        _, whole = projection_text(
            ThresholdProjection(80.0, "projected", 12.0, "2026-08-05")
        )
        _, short = projection_text(
            ThresholdProjection(80.0, "projected", 12.0, "2026-08-05", 7.0)
        )
        assert "last" not in whole
        assert short.endswith("· last 7 days")

    def test_exceeded_is_explicit(self):
        _, value = projection_text(ThresholdProjection(80.0, "exceeded"))
        assert value == "already exceeded"

    def test_not_growing_is_explicit(self):
        _, value = projection_text(ThresholdProjection(90.0, "not_growing"))
        assert value == "not on current trend"

    @pytest.mark.parametrize(
        ("projection", "colour"),
        [
            (ThresholdProjection(80.0, "exceeded"), RED),
            (ThresholdProjection(80.0, "projected", 10.0, "2026-08-01"), RED),
            (ThresholdProjection(80.0, "projected", 60.0, "2026-09-01"), AMBER),
            (ThresholdProjection(80.0, "projected", 400.0, "2027-08-01"), GREEN),
            (ThresholdProjection(90.0, "not_growing"), TEXT_MUTED),
        ],
    )
    def test_colour_by_urgency(self, projection, colour):
        assert projection_colour(projection) == colour


class TestDiskForecastWidget:
    @pytest.fixture
    def widget(self, qapp):
        return DiskForecastWidget()

    def test_shows_loading_before_any_data(self, widget):
        assert _grid_rows(widget._disk_grid) == [("Disk history", "Loading…")]

    def test_populates_from_history(self, widget):
        widget.update_from_history(_history([67.0, 68.0, 69.0, 70.0]))
        rows = dict(_grid_rows(widget._disk_grid))
        assert rows["Current"] == "70.0%"
        assert "+1.00 pp/day" in rows["Growth"]
        assert "4 samples" in rows["Growth"]
        assert "2026-07-14" in rows["Reaches 80%"]
        assert "2026-07-24" in rows["Reaches 90%"]

    def test_single_sample_reports_insufficient_history(self, widget):
        widget.update_from_history(_history([70.0]))
        assert _grid_rows(widget._disk_grid) == [
            ("Disk history", "Not enough samples yet")
        ]

    def test_empty_history_reports_insufficient(self, widget):
        widget.update_from_history(
            ResourceHistoryResponse.from_dict({"snapshots": [], "count": 0})
        )
        assert _grid_rows(widget._disk_grid)[0][1] == "Not enough samples yet"

    def test_shrinking_disk_is_labelled(self, widget):
        widget.update_from_history(_history([70.0, 69.0, 68.0]))
        rows = dict(_grid_rows(widget._disk_grid))
        assert "shrinking" in rows["Growth"]
        assert rows["Reaches 80%"] == "not on current trend"

    def test_populates_from_trends(self, widget):
        widget.update_from_trends(
            FileTrendsResponse.from_dict(
                {
                    "scans": [],
                    "forecast": {
                        "growth_rate_mb_per_day": 20.0,
                        "current_reclaimable_mb": 1024.0,
                        "data_points": 5,
                        "projected_milestones": {"5gb": "2026-09-01"},
                    },
                }
            )
        )
        rows = dict(_grid_rows(widget._trend_grid))
        assert rows["Reclaimable now"] == "1.0 GB"
        assert rows["Reaches 5GB"] == "2026-09-01"

    def test_insufficient_trend_data_is_stated(self, widget):
        widget.update_from_trends(
            FileTrendsResponse.from_dict({"forecast": {"insufficient_data": True}})
        )
        assert _grid_rows(widget._trend_grid) == [
            ("Reclaimable trend", "Not enough scans yet")
        ]

    def test_unavailable_blanks_both_columns(self, widget):
        widget.update_from_history(_history([67.0, 68.0, 69.0]))
        widget.show_unavailable()
        assert _grid_rows(widget._disk_grid)[0][1] == "Backend unreachable"
        assert _grid_rows(widget._trend_grid)[0][1] == "Backend unreachable"

    def test_updates_replace_rather_than_append(self, widget):
        widget.update_from_history(_history([67.0, 68.0, 69.0]))
        first = len(_grid_rows(widget._disk_grid))
        widget.update_from_history(_history([67.0, 68.0, 69.0]))
        assert len(_grid_rows(widget._disk_grid)) == first

    def test_renders_headless(self, widget):
        widget.update_from_history(_history([67.0, 68.0, 69.0, 70.0]))
        assert not render_offscreen(widget).isNull()
