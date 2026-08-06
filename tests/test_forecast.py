"""Tests for the pure forecasting maths in ``sysadmin.services.forecast``.

No Qt, no database — every input is a plain contract object or a raw
``(timestamp, disk_usage)`` pair.  Contracts are imported from
:mod:`sysadmin.contracts` rather than the tray's re-export: the maths
lives on the backend now and must not depend on the tray to be tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from sysadmin.contracts import FileTrendForecast, ResourceHistoryResponse
from sysadmin.services.forecast import (
    ThresholdProjection,
    describe_reclaimable_forecast,
    disk_series,
    disk_series_from,
    format_days,
    format_mb,
    growth_rate_per_day,
    linear_fit,
    most_urgent_projection,
    project_disk_thresholds,
)

BASE = datetime(2026, 7, 1, 12, 0, 0)


def _history(percents: list[float], mount: str = "/", step_hours: int = 24) -> dict:
    """Build a resources/history payload with one disk reading per step."""
    return {
        "period_hours": step_hours * len(percents),
        "count": len(percents),
        "snapshots": [
            {
                "cpu_percent": 10.0,
                "ram_percent": 40.0,
                "disk_usage": {
                    mount: {
                        "total_gb": 500.0,
                        "used_gb": 500.0 * pct / 100,
                        "percent": pct,
                    }
                },
                "recorded_at": (BASE + timedelta(hours=step_hours * i)).isoformat(),
            }
            for i, pct in enumerate(percents)
        ],
    }


class TestLinearFit:
    def test_perfect_line_recovers_slope_and_intercept(self):
        fit = linear_fit([(0.0, 10.0), (1.0, 12.0), (2.0, 14.0), (3.0, 16.0)])
        assert fit is not None
        assert fit.slope == pytest.approx(2.0)
        assert fit.intercept == pytest.approx(10.0)
        assert fit.points == 4

    def test_single_point_is_unfittable(self):
        assert linear_fit([(0.0, 10.0)]) is None

    def test_empty_is_unfittable(self):
        assert linear_fit([]) is None

    def test_identical_x_values_do_not_divide_by_zero(self):
        assert linear_fit([(5.0, 1.0), (5.0, 9.0)]) is None

    def test_negative_slope_for_shrinking_series(self):
        fit = linear_fit([(0.0, 90.0), (1.0, 85.0), (2.0, 80.0)])
        assert fit is not None
        assert fit.slope == pytest.approx(-5.0)


class TestDiskSeries:
    def test_extracts_percent_for_requested_mount(self):
        history = ResourceHistoryResponse.from_dict(_history([50.0, 51.0, 52.0]))
        series = disk_series(history, "/")
        assert [pct for _, pct in series] == [50.0, 51.0, 52.0]

    def test_unknown_mount_yields_nothing(self):
        history = ResourceHistoryResponse.from_dict(_history([50.0, 51.0]))
        assert disk_series(history, "/home") == []

    def test_snapshots_without_disk_block_are_skipped_not_zeroed(self):
        payload = _history([50.0, 51.0])
        payload["snapshots"].insert(
            1,
            {
                "cpu_percent": 1.0,
                "disk_usage": None,
                "recorded_at": (BASE + timedelta(hours=6)).isoformat(),
            },
        )
        history = ResourceHistoryResponse.from_dict(payload)
        series = disk_series(history, "/")
        assert [pct for _, pct in series] == [50.0, 51.0]

    def test_unparseable_timestamps_are_skipped(self):
        payload = _history([50.0, 51.0])
        payload["snapshots"][0]["recorded_at"] = "not-a-date"
        history = ResourceHistoryResponse.from_dict(payload)
        assert len(disk_series(history, "/")) == 1

    def test_series_is_sorted_oldest_first(self):
        payload = _history([50.0, 60.0, 70.0])
        payload["snapshots"].reverse()
        history = ResourceHistoryResponse.from_dict(payload)
        assert [pct for _, pct in disk_series(history, "/")] == [50.0, 60.0, 70.0]

    def test_empty_history_yields_empty_series(self):
        history = ResourceHistoryResponse.from_dict({"snapshots": [], "count": 0})
        assert disk_series(history) == []


class TestDiskSeriesFrom:
    """The ORM-shaped entry point the backend uses.

    ``ResourceSnapshot.recorded_at`` is a real ``datetime`` and
    ``disk_usage`` a JSONB dict, so no ISO parsing happens on that path.
    """

    def _rows(self, percents: list[float], mount: str = "/") -> list[tuple]:
        return [
            (
                BASE + timedelta(hours=24 * i),
                {mount: {"total_gb": 500.0, "percent": pct}},
            )
            for i, pct in enumerate(percents)
        ]

    def test_datetime_timestamps_pass_through_unparsed(self):
        series = disk_series_from(self._rows([60.0, 61.0, 62.0]))
        assert [pct for _, pct in series] == [60.0, 61.0, 62.0]
        assert series[0][0] == BASE

    def test_matches_the_contract_adapter_for_equivalent_data(self):
        from_rows = disk_series_from(self._rows([50.0, 51.0, 52.0]))
        from_contract = disk_series(
            ResourceHistoryResponse.from_dict(_history([50.0, 51.0, 52.0])), "/"
        )
        assert from_rows == from_contract

    def test_rows_missing_the_mount_are_skipped(self):
        rows = self._rows([50.0, 51.0]) + [(BASE + timedelta(hours=48), {})]
        assert len(disk_series_from(rows, "/")) == 2

    def test_none_disk_usage_is_skipped_not_zeroed(self):
        rows = self._rows([50.0, 51.0])
        rows.insert(1, (BASE + timedelta(hours=6), None))
        assert [pct for _, pct in disk_series_from(rows, "/")] == [50.0, 51.0]

    def test_boolean_percent_is_rejected(self):
        """``True`` is an ``int`` in Python — 1 % free disk is not a reading."""
        rows = [(BASE, {"/": {"percent": True}}), *self._rows([50.0, 51.0])]
        assert [pct for _, pct in disk_series_from(rows, "/")] == [50.0, 51.0]

    def test_rows_are_sorted_oldest_first(self):
        rows = list(reversed(self._rows([50.0, 60.0, 70.0])))
        assert [pct for _, pct in disk_series_from(rows, "/")] == [50.0, 60.0, 70.0]


class TestGrowthRate:
    def test_one_point_per_day_gives_daily_rate(self):
        history = ResourceHistoryResponse.from_dict(_history([50.0, 51.0, 52.0, 53.0]))
        rate = growth_rate_per_day(disk_series(history, "/"))
        assert rate == pytest.approx(1.0)

    def test_hourly_samples_scale_to_days(self):
        history = ResourceHistoryResponse.from_dict(
            _history([50.0, 50.5, 51.0], step_hours=12)
        )
        rate = growth_rate_per_day(disk_series(history, "/"))
        assert rate == pytest.approx(1.0)

    def test_single_sample_has_no_rate(self):
        history = ResourceHistoryResponse.from_dict(_history([50.0]))
        assert growth_rate_per_day(disk_series(history, "/")) is None


class TestProjectDiskThresholds:
    def test_projects_both_thresholds_from_a_steady_climb(self):
        # 70 % climbing 1 pp/day → 80 % in 10 days, 90 % in 20 days.
        history = ResourceHistoryResponse.from_dict(_history([67.0, 68.0, 69.0, 70.0]))
        projections = project_disk_thresholds(disk_series(history, "/"))

        assert [p.percent for p in projections] == [80.0, 90.0]
        assert all(p.state == "projected" for p in projections)
        assert projections[0].days_from_now == pytest.approx(10.0, abs=0.05)
        assert projections[1].days_from_now == pytest.approx(20.0, abs=0.05)
        assert projections[0].date == "2026-07-14"
        assert projections[1].date == "2026-07-24"

    def test_threshold_already_passed_is_reported_as_exceeded(self):
        history = ResourceHistoryResponse.from_dict(_history([80.0, 82.0, 84.0]))
        projections = project_disk_thresholds(disk_series(history, "/"))
        assert projections[0].state == "exceeded"
        assert projections[0].date is None
        assert projections[1].state == "projected"

    def test_shrinking_disk_never_crosses(self):
        history = ResourceHistoryResponse.from_dict(_history([70.0, 69.0, 68.0]))
        projections = project_disk_thresholds(disk_series(history, "/"))
        assert [p.state for p in projections] == ["not_growing", "not_growing"]
        assert all(p.days_from_now is None for p in projections)

    def test_flat_disk_never_crosses(self):
        history = ResourceHistoryResponse.from_dict(_history([70.0, 70.0, 70.0]))
        projections = project_disk_thresholds(disk_series(history, "/"))
        assert [p.state for p in projections] == ["not_growing", "not_growing"]

    def test_too_little_history_yields_no_projections(self):
        history = ResourceHistoryResponse.from_dict(_history([70.0]))
        assert project_disk_thresholds(disk_series(history, "/")) == []

    def test_custom_thresholds_are_honoured(self):
        history = ResourceHistoryResponse.from_dict(_history([70.0, 71.0, 72.0]))
        projections = project_disk_thresholds(
            disk_series(history, "/"), thresholds=(75,)
        )
        assert len(projections) == 1
        assert projections[0].percent == 75.0

    def test_noisy_series_still_projects_from_the_fitted_trend(self):
        history = ResourceHistoryResponse.from_dict(
            _history([70.0, 72.0, 71.0, 73.0, 72.0, 74.0])
        )
        projections = project_disk_thresholds(disk_series(history, "/"))
        assert projections[0].state == "projected"
        assert projections[0].days_from_now is not None
        assert projections[0].days_from_now > 0


class TestMostUrgentProjection:
    """Which of several crossings is the one worth warning about."""

    def test_imminent_crossing_beats_an_already_exceeded_lower_threshold(self):
        projections = [
            ThresholdProjection(80.0, "exceeded"),
            ThresholdProjection(90.0, "projected", 10.0, "2026-07-11"),
        ]
        chosen = most_urgent_projection(projections, horizon_days=30.0)
        assert chosen is not None
        assert chosen.percent == 90.0

    def test_exceeded_wins_when_the_next_crossing_is_far_out(self):
        """Being past 80 % is worth saying even if 90 % is a year away."""
        projections = [
            ThresholdProjection(80.0, "exceeded"),
            ThresholdProjection(90.0, "projected", 400.0, "2027-08-05"),
        ]
        chosen = most_urgent_projection(projections, horizon_days=30.0)
        assert chosen is not None
        assert chosen.state == "exceeded"
        assert chosen.percent == 80.0

    def test_soonest_wins_among_several_imminent_crossings(self):
        projections = [
            ThresholdProjection(80.0, "projected", 20.0, "2026-07-21"),
            ThresholdProjection(90.0, "projected", 5.0, "2026-07-06"),
        ]
        chosen = most_urgent_projection(projections, horizon_days=30.0)
        assert chosen is not None
        assert chosen.days_from_now == 5.0

    def test_highest_exceeded_is_chosen(self):
        projections = [
            ThresholdProjection(80.0, "exceeded"),
            ThresholdProjection(90.0, "exceeded"),
        ]
        chosen = most_urgent_projection(projections)
        assert chosen is not None
        assert chosen.percent == 90.0

    def test_distant_projection_is_still_returned_for_display(self):
        projections = [ThresholdProjection(80.0, "projected", 400.0, "2027-08-05")]
        chosen = most_urgent_projection(projections, horizon_days=30.0)
        assert chosen is not None
        assert chosen.days_from_now == 400.0

    def test_not_growing_is_never_chosen(self):
        projections = [
            ThresholdProjection(80.0, "not_growing"),
            ThresholdProjection(90.0, "not_growing"),
        ]
        assert most_urgent_projection(projections) is None

    def test_empty_input_yields_none(self):
        assert most_urgent_projection([]) is None

    def test_end_to_end_from_a_real_series(self):
        # 70 % climbing 1 pp/day: 80 % in 10 days, 90 % in 20 days.
        history = ResourceHistoryResponse.from_dict(_history([67.0, 68.0, 69.0, 70.0]))
        chosen = most_urgent_projection(
            project_disk_thresholds(disk_series(history, "/")), horizon_days=30.0
        )
        assert chosen is not None
        assert chosen.percent == 80.0
        assert chosen.days_from_now == pytest.approx(10.0, abs=0.05)


class TestFormatting:
    @pytest.mark.parametrize(
        ("days", "expected"),
        [
            (0.5, "under a day"),
            (12.0, "12 days"),
            (59.0, "59 days"),
            (90.0, "~3 months"),
            (1000.0, "~2.7 years"),
        ],
    )
    def test_format_days(self, days, expected):
        assert format_days(days) == expected

    @pytest.mark.parametrize(
        ("mb", "expected"),
        [(0.0, "0 MB"), (512.0, "512 MB"), (2048.0, "2.0 GB")],
    )
    def test_format_mb(self, mb, expected):
        assert format_mb(mb) == expected


class TestDescribeReclaimableForecast:
    def test_insufficient_data_still_returns_a_row(self):
        forecast = FileTrendForecast.from_dict({"insufficient_data": True})
        rows = describe_reclaimable_forecast(forecast)
        assert rows == [("Reclaimable trend", "Not enough scans yet")]

    def test_single_scan_counts_as_insufficient(self):
        forecast = FileTrendForecast.from_dict(
            {"growth_rate_mb_per_day": 5.0, "data_points": 1}
        )
        assert describe_reclaimable_forecast(forecast)[0][1] == "Not enough scans yet"

    def test_growth_and_milestones_are_formatted(self):
        forecast = FileTrendForecast.from_dict(
            {
                "growth_rate_mb_per_day": 42.5,
                "current_reclaimable_mb": 2048.0,
                "data_points": 6,
                "projected_milestones": {"5gb": "2026-08-01", "10gb": "2026-10-01"},
            }
        )
        rows = dict(describe_reclaimable_forecast(forecast))
        assert rows["Reclaimable now"] == "2.0 GB"
        assert "+42.5 MB/day" in rows["Junk growth"]
        assert "6 scans" in rows["Junk growth"]
        assert rows["Reaches 5GB"] == "2026-08-01"
        assert rows["Reaches 10GB"] == "2026-10-01"

    def test_shrinking_junk_is_labelled(self):
        forecast = FileTrendForecast.from_dict(
            {"growth_rate_mb_per_day": -3.0, "data_points": 4}
        )
        rows = dict(describe_reclaimable_forecast(forecast))
        assert "shrinking" in rows["Junk growth"]

    def test_steady_junk_is_labelled(self):
        forecast = FileTrendForecast.from_dict(
            {"growth_rate_mb_per_day": 0.0, "data_points": 4}
        )
        rows = dict(describe_reclaimable_forecast(forecast))
        assert "steady" in rows["Junk growth"]
