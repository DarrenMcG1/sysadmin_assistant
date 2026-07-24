"""Disk growth forecast card.

Two independent projections sit side by side because they answer
different questions and come from different endpoints:

* **Disk usage** — least-squares fit over the disk percentage in
  ``GET /api/sysadmin/resources/history``, projecting the date the 80 %
  warning and 90 % critical thresholds are crossed.
* **Reclaimable space** — the regression the backend already computes in
  ``GET /api/files/trends``; how fast junk accumulates and when it
  passes the configured milestones.

All maths lives in :mod:`sysadmin_tray.forecast` so it is testable
without Qt; this widget only formats and colours the results.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.forecast import (
    ThresholdProjection,
    describe_reclaimable_forecast,
    disk_series,
    format_days,
    growth_rate_per_day,
    project_disk_thresholds,
)
from sysadmin_tray.models import FileTrendsResponse, ResourceHistoryResponse
from sysadmin_tray.styles import (
    AMBER,
    BG_CARD,
    BORDER,
    GREEN,
    RED,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# Horizons that decide the colour of a projected crossing date.
URGENT_DAYS = 30
SOON_DAYS = 90


def projection_text(projection: ThresholdProjection) -> tuple[str, str]:
    """Render one threshold projection as ``(caption, value)``."""
    caption = f"Reaches {projection.percent:.0f}%"
    if projection.state == "exceeded":
        return caption, "already exceeded"
    if projection.state == "not_growing" or projection.days_from_now is None:
        return caption, "not on current trend"
    return caption, f"{projection.date}  ({format_days(projection.days_from_now)})"


def projection_colour(projection: ThresholdProjection) -> str:
    """Colour a projection by urgency."""
    if projection.state == "exceeded":
        return RED
    if projection.state != "projected" or projection.days_from_now is None:
        return TEXT_MUTED
    if projection.days_from_now <= URGENT_DAYS:
        return RED
    if projection.days_from_now <= SOON_DAYS:
        return AMBER
    return GREEN


class DiskForecastWidget(QFrame):
    """Card showing projected disk-threshold crossings and junk growth."""

    def __init__(self, mount: str = "/", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._mount = mount
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("Disk Growth Forecast")
        title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        layout.addWidget(title)

        columns = QHBoxLayout()
        columns.setSpacing(24)

        self._disk_grid = QGridLayout()
        self._disk_grid.setHorizontalSpacing(12)
        self._disk_grid.setVerticalSpacing(3)
        disk_column = QVBoxLayout()
        disk_column.addWidget(self._column_heading(f"Disk usage ({self._mount})"))
        disk_column.addLayout(self._disk_grid)
        disk_column.addStretch()
        columns.addLayout(disk_column, stretch=1)

        self._trend_grid = QGridLayout()
        self._trend_grid.setHorizontalSpacing(12)
        self._trend_grid.setVerticalSpacing(3)
        trend_column = QVBoxLayout()
        trend_column.addWidget(self._column_heading("Reclaimable space"))
        trend_column.addLayout(self._trend_grid)
        trend_column.addStretch()
        columns.addLayout(trend_column, stretch=1)

        layout.addLayout(columns)

        self._set_rows(self._disk_grid, [("Disk history", "Loading…", TEXT_MUTED)])
        self._set_rows(self._trend_grid, [("Scan history", "Loading…", TEXT_MUTED)])

    @staticmethod
    def _column_heading(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        return label

    @staticmethod
    def _set_rows(grid: QGridLayout, rows: list[tuple[str, str, str]]) -> None:
        """Replace a grid's contents with ``(caption, value, colour)`` rows."""
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for row, (caption, value, colour) in enumerate(rows):
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
            value_label = QLabel(value)
            value_label.setStyleSheet(
                f"font-size: 11px; font-weight: bold; color: {colour};"
            )
            grid.addWidget(caption_label, row, 0)
            grid.addWidget(value_label, row, 1)
        grid.setColumnStretch(2, 1)

    # ── Data ─────────────────────────────────────────────────────────

    def update_from_history(self, history: ResourceHistoryResponse) -> None:
        """Recompute the disk-threshold projections from resource history."""
        series = disk_series(history, self._mount)
        if len(series) < 2:
            self._set_rows(
                self._disk_grid,
                [("Disk history", "Not enough samples yet", TEXT_MUTED)],
            )
            return

        rows: list[tuple[str, str, str]] = [
            ("Current", f"{series[-1][1]:.1f}%", TEXT_PRIMARY),
        ]

        rate = growth_rate_per_day(series)
        if rate is None:
            rate_text = "unknown"
        elif rate > 0:
            rate_text = f"+{rate:.2f} pp/day"
        elif rate < 0:
            rate_text = f"{rate:.2f} pp/day (shrinking)"
        else:
            rate_text = "steady"
        rows.append(("Growth", f"{rate_text}  ({len(series)} samples)", TEXT_PRIMARY))

        for projection in project_disk_thresholds(series):
            caption, value = projection_text(projection)
            rows.append((caption, value, projection_colour(projection)))

        self._set_rows(self._disk_grid, rows)

    def update_from_trends(self, trends: FileTrendsResponse) -> None:
        """Show the backend's reclaimable-space regression."""
        rows = [
            (caption, value, TEXT_PRIMARY)
            for caption, value in describe_reclaimable_forecast(trends.forecast)
        ]
        self._set_rows(self._trend_grid, rows)

    def show_unavailable(self, message: str = "Backend unreachable") -> None:
        """Blank both columns when data cannot be fetched."""
        self._set_rows(self._disk_grid, [("Disk usage", message, TEXT_MUTED)])
        self._set_rows(self._trend_grid, [("Reclaimable", message, TEXT_MUTED)])
