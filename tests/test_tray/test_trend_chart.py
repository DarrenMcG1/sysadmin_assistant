"""Tests for the reusable QPainter TrendChart widget.

The point of these is that ``paintEvent`` must survive every data shape
the dashboard can hand it — including none at all — when rendered
headless (``QT_QPA_PLATFORM=offscreen``, forced in ``conftest.py``).
"""

from __future__ import annotations

import pytest

from sysadmin_tray.styles import BLUE, GREEN
from sysadmin_tray.widgets.trend_chart import TrendChart, TrendSeries, _short_date

from .conftest import render_offscreen


@pytest.fixture
def chart(qapp):
    return TrendChart()


class TestShortDate:
    def test_iso_timestamp_becomes_month_day(self):
        assert _short_date("2026-07-24T02:00:00+00:00") == "07-24"

    def test_plain_date_becomes_month_day(self):
        assert _short_date("2026-07-24") == "07-24"

    def test_empty_string_stays_empty(self):
        assert _short_date("") == ""

    def test_unparseable_value_does_not_raise(self):
        assert isinstance(_short_date("garbage"), str)


class TestTrendChartData:
    def test_starts_empty(self, chart):
        assert chart.has_data is False

    def test_set_values_populates_one_series(self, chart):
        chart.set_values([1.0, 2.0, 3.0], label="Health")
        assert chart.has_data is True

    def test_empty_series_is_discarded(self, chart):
        chart.set_series([TrendSeries("Health", BLUE, [])])
        assert chart.has_data is False

    def test_clear_drops_data(self, chart):
        chart.set_values([1.0, 2.0])
        chart.clear()
        assert chart.has_data is False

    def test_auto_range_pads_above_the_maximum(self, qapp):
        auto = TrendChart(y_max=None)
        auto.set_values([10.0, 20.0])
        low, high = auto._value_range()
        assert low == 0.0
        assert high > 20.0

    def test_auto_range_of_a_flat_series_is_not_degenerate(self, qapp):
        auto = TrendChart(y_max=None)
        auto.set_values([5.0, 5.0, 5.0])
        low, high = auto._value_range()
        assert high > low

    def test_fixed_range_is_respected(self, chart):
        chart.set_values([10.0, 90.0])
        assert chart._value_range() == (0.0, 100.0)


class TestTrendChartRendering:
    """Every one of these fails loudly if paintEvent raises."""

    def test_renders_placeholder_with_no_data(self, chart):
        image = render_offscreen(chart)
        assert not image.isNull()

    def test_renders_a_single_point(self, chart):
        chart.set_values([42.0], labels=["2026-07-24T00:00:00"])
        assert not render_offscreen(chart).isNull()

    def test_renders_many_points(self, chart):
        chart.set_values(
            [float(v) for v in range(0, 100, 3)],
            labels=[f"2026-07-{(d % 28) + 1:02d}T00:00:00" for d in range(34)],
        )
        assert not render_offscreen(chart).isNull()

    def test_renders_two_series(self, chart):
        chart.set_series(
            [
                TrendSeries("CPU", BLUE, [10.0, 20.0, 30.0]),
                TrendSeries("RAM", GREEN, [50.0, 40.0, 60.0]),
            ],
            labels=["2026-07-01T00:00:00", "2026-07-02T00:00:00", "2026-07-03T00:00:00"],
        )
        assert not render_offscreen(chart).isNull()

    def test_renders_without_labels(self, chart):
        chart.set_values([1.0, 2.0, 3.0])
        assert not render_offscreen(chart).isNull()

    def test_renders_flat_series(self, chart):
        chart.set_values([50.0] * 10)
        assert not render_offscreen(chart).isNull()

    def test_renders_values_outside_the_fixed_range(self, chart):
        """Out-of-range values are clamped, not allowed to blow up."""
        chart.set_values([-20.0, 50.0, 180.0])
        assert not render_offscreen(chart).isNull()

    def test_renders_in_a_tiny_viewport(self, chart):
        chart.set_values([10.0, 20.0, 30.0])
        assert not render_offscreen(chart, width=20, height=20).isNull()

    def test_renders_auto_scaled_series(self, qapp):
        auto = TrendChart(y_max=None, y_suffix=" MB")
        auto.set_values([100.0, 250.0, 700.0])
        assert not render_offscreen(auto).isNull()

    def test_renders_unnamed_series_without_legend(self, chart):
        chart.set_series([TrendSeries("", BLUE, [1.0, 2.0, 3.0])])
        assert not render_offscreen(chart).isNull()
