"""Reusable QPainter line chart for historical series.

Deliberately dependency-free — the dashboard already draws its resource
history with ``QPainter`` (``dashboard/overview_tab.py``), so this widget
generalises that approach rather than pulling in QtCharts, pyqtgraph or
matplotlib for one more chart.

It renders correctly with no data, one point, or many, which matters
because the backend legitimately answers "no scans yet".
"""

from __future__ import annotations

from typing import NamedTuple

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from sysadmin_tray.styles import (
    BLUE,
    BORDER,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


class TrendSeries(NamedTuple):
    """One plotted line: a label, a colour, and its y-values."""

    label: str
    colour: str
    values: list[float]


def _short_date(stamp: str) -> str:
    """Reduce an ISO timestamp to ``MM-DD`` (or ``HH:MM`` within a day)."""
    if not stamp:
        return ""
    date_part, _, time_part = stamp.partition("T")
    bits = date_part.split("-")
    if len(bits) == 3:
        return f"{bits[1]}-{bits[2]}"
    return time_part[:5] if time_part else date_part[:10]


class TrendChart(QWidget):
    """Line chart over an ordered series of points.

    ``y_min``/``y_max`` fix the vertical range (health scores are always
    0–100); pass ``y_max=None`` to scale to the data instead.  X-axis
    labels are optional ISO timestamps — only the first and last are
    drawn, matching the Overview tab's chart.
    """

    def __init__(
        self,
        y_min: float = 0.0,
        y_max: float | None = 100.0,
        y_suffix: str = "%",
        placeholder: str = "No trend data",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._y_min = y_min
        self._y_max = y_max
        self._y_suffix = y_suffix
        self._placeholder = placeholder
        self._series: list[TrendSeries] = []
        self._labels: list[str] = []
        self.setMinimumHeight(120)
        self.setMaximumHeight(200)

    # ── Data ─────────────────────────────────────────────────────────

    def set_series(
        self,
        series: list[TrendSeries],
        labels: list[str] | None = None,
    ) -> None:
        """Replace all plotted series and trigger a repaint."""
        self._series = [s for s in series if s.values]
        self._labels = labels or []
        self.update()

    def set_values(
        self,
        values: list[float],
        labels: list[str] | None = None,
        label: str = "",
        colour: str = BLUE,
    ) -> None:
        """Convenience wrapper for the common single-series case."""
        self.set_series([TrendSeries(label, colour, list(values))], labels)

    def set_placeholder(self, text: str) -> None:
        """Set the message shown when there is nothing to plot."""
        self._placeholder = text
        self.update()

    def clear(self) -> None:
        """Drop all data — the placeholder is shown again."""
        self._series = []
        self._labels = []
        self.update()

    @property
    def has_data(self) -> bool:
        return bool(self._series)

    # ── Painting ─────────────────────────────────────────────────────

    def _value_range(self) -> tuple[float, float]:
        """Resolve the vertical range, padding an auto-scaled one."""
        if self._y_max is not None:
            return self._y_min, self._y_max

        all_values = [v for s in self._series for v in s.values]
        if not all_values:
            return 0.0, 1.0
        low = min(min(all_values), self._y_min)
        high = max(all_values)
        if high <= low:
            high = low + 1.0
        pad = (high - low) * 0.1
        return low, high + pad

    def paintEvent(self, event) -> None:  # noqa: N802 — Qt override
        painter = QPainter(self)
        try:
            if not self._series:
                painter.setPen(QColor(TEXT_MUTED))
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    self._placeholder,
                )
                return

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            rect = QRectF(self.rect()).adjusted(46, 20, -12, -24)
            if rect.width() <= 0 or rect.height() <= 0:
                return

            low, high = self._value_range()
            span = high - low or 1.0

            def y_for(value: float) -> float:
                frac = (value - low) / span
                return rect.bottom() - max(0.0, min(1.0, frac)) * rect.height()

            self._draw_grid(painter, rect, low, high, y_for)
            self._draw_x_labels(painter, rect)

            for series in self._series:
                self._draw_series(painter, rect, series, y_for)

            self._draw_legend(painter, rect)
        finally:
            painter.end()

    def _draw_grid(self, painter, rect, low, high, y_for) -> None:
        """Horizontal gridlines plus right-aligned y-axis labels."""
        painter.setPen(QPen(QColor(BORDER), 0.5))
        steps = [low + (high - low) * f for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
        for value in steps:
            y = y_for(value)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        painter.setPen(QColor(TEXT_MUTED))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        for value in steps:
            y = y_for(value)
            painter.drawText(
                QRectF(0, y - 6, 42, 12),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.0f}{self._y_suffix}",
            )

    def _draw_x_labels(self, painter, rect) -> None:
        """First and last timestamps beneath the plot area."""
        if not self._labels:
            return
        painter.setPen(QColor(TEXT_MUTED))
        pairs = [(self._labels[0], rect.left())]
        if len(self._labels) > 1:
            pairs.append((self._labels[-1], rect.right() - 44))
        for stamp, x_pos in pairs:
            painter.drawText(
                QRectF(x_pos, rect.bottom() + 4, 60, 14),
                Qt.AlignmentFlag.AlignLeft,
                _short_date(stamp),
            )

    def _draw_series(self, painter, rect, series: TrendSeries, y_for) -> None:
        """Line + translucent fill, or a lone marker for a single point."""
        values = series.values
        colour = QColor(series.colour)

        if len(values) == 1:
            painter.setPen(QPen(colour, 1.5))
            painter.setBrush(colour)
            painter.drawEllipse(
                QPointF(rect.center().x(), y_for(values[0])), 3.5, 3.5
            )
            return

        dx = rect.width() / (len(values) - 1)
        path = QPainterPath()
        fill = QPainterPath()

        first_y = y_for(values[0])
        path.moveTo(rect.left(), first_y)
        fill.moveTo(rect.left(), rect.bottom())
        fill.lineTo(rect.left(), first_y)

        for i, value in enumerate(values[1:], start=1):
            x = rect.left() + i * dx
            y = y_for(value)
            path.lineTo(x, y)
            fill.lineTo(x, y)

        fill.lineTo(rect.left() + (len(values) - 1) * dx, rect.bottom())
        fill.closeSubpath()

        fill_colour = QColor(series.colour)
        fill_colour.setAlpha(30)
        painter.fillPath(fill, fill_colour)
        painter.setPen(QPen(colour, 1.5))
        painter.drawPath(path)

        # Emphasise the latest reading
        painter.setBrush(colour)
        painter.drawEllipse(
            QPointF(rect.left() + (len(values) - 1) * dx, y_for(values[-1])),
            3.0,
            3.0,
        )

    def _draw_legend(self, painter, rect) -> None:
        """Swatch + label per named series along the top of the plot."""
        offset = 0.0
        for series in self._series:
            if not series.label:
                continue
            painter.setPen(QColor(series.colour))
            painter.setBrush(QColor(series.colour))
            painter.drawRect(QRectF(rect.left() + offset, 4, 10, 10))
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(
                QRectF(rect.left() + offset + 14, 4, 90, 12),
                Qt.AlignmentFlag.AlignLeft,
                series.label,
            )
            offset += 24 + 7 * len(series.label)
