"""Overview tab — at-a-glance system state with resource history chart.

Combines the ResourceGauge, ServiceStatusGrid, and AlertBadgeRow
widgets with a QPainter-based mini line chart for CPU/RAM history.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import (
    AlertsResponse,
    ResourceHistoryResponse,
    ResourceResponse,
    StatusResponse,
)
from sysadmin_tray.styles import (
    BLUE,
    BORDER,
    GREEN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from sysadmin_tray.widgets.alert_badge import AlertBadgeRow
from sysadmin_tray.widgets.resource_gauge import ResourceGauge
from sysadmin_tray.widgets.service_grid import ServiceStatusGrid

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)


class ResourceHistoryChart(QWidget):
    """QPainter-based mini line chart showing CPU and RAM over time.

    No external charting library required.  Draws two lines (CPU in blue,
    RAM in green) with a semi-transparent fill beneath each.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cpu_points: list[float] = []
        self._ram_points: list[float] = []
        self._timestamps: list[str] = []
        self.setMinimumHeight(120)
        self.setMaximumHeight(180)

    def update_data(self, history: ResourceHistoryResponse) -> None:
        """Replace chart data from a ResourceHistoryResponse."""
        self._cpu_points = [
            s.cpu_percent or 0.0 for s in history.snapshots
        ]
        self._ram_points = [
            s.ram_percent or 0.0 for s in history.snapshots
        ]
        self._timestamps = [
            s.recorded_at or "" for s in history.snapshots
        ]
        self.update()  # trigger repaint

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._cpu_points:
            painter = QPainter(self)
            painter.setPen(QColor(TEXT_MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No history data")
            painter.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(40, 20, -12, -24)
        n = len(self._cpu_points)

        # Draw background grid
        painter.setPen(QPen(QColor(BORDER), 0.5))
        for pct in (25, 50, 75):
            y = rect.bottom() - (pct / 100.0) * rect.height()
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

        # Y-axis labels
        painter.setPen(QColor(TEXT_MUTED))
        font = painter.font()
        font.setPixelSize(10)
        painter.setFont(font)
        for pct in (0, 25, 50, 75, 100):
            y = rect.bottom() - (pct / 100.0) * rect.height()
            painter.drawText(QRectF(0, y - 6, 36, 12),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{pct}%")

        # Time labels (start and end)
        if self._timestamps:
            start = self._timestamps[0]
            end = self._timestamps[-1]
            for ts_str, x_pos in [(start, rect.left()), (end, rect.right() - 40)]:
                # Extract HH:MM from ISO timestamp
                time_part = ts_str.split("T")[1][:5] if "T" in ts_str else ts_str[:5]
                painter.drawText(QRectF(x_pos, rect.bottom() + 4, 50, 14),
                                 Qt.AlignmentFlag.AlignLeft, time_part)

        def _draw_line(points: list[float], colour: str) -> None:
            if len(points) < 2:
                return
            pen_colour = QColor(colour)
            fill_colour = QColor(colour)
            fill_colour.setAlpha(30)

            # Build the line path
            path = QPainterPath()
            fill_path = QPainterPath()

            dx = rect.width() / max(n - 1, 1)
            first_x = rect.left()
            first_y = rect.bottom() - (points[0] / 100.0) * rect.height()

            path.moveTo(first_x, first_y)
            fill_path.moveTo(first_x, rect.bottom())
            fill_path.lineTo(first_x, first_y)

            for i in range(1, n):
                x = rect.left() + i * dx
                y = rect.bottom() - (points[i] / 100.0) * rect.height()
                path.lineTo(x, y)
                fill_path.lineTo(x, y)

            fill_path.lineTo(rect.left() + (n - 1) * dx, rect.bottom())
            fill_path.closeSubpath()

            painter.fillPath(fill_path, fill_colour)
            painter.setPen(QPen(pen_colour, 1.5))
            painter.drawPath(path)

        _draw_line(self._cpu_points, BLUE)
        _draw_line(self._ram_points, GREEN)

        # Legend — CPU (blue) and RAM (green) side by side
        lx = rect.left()
        for label, colour, offset in [("CPU", BLUE, 0), ("RAM", GREEN, 60)]:
            painter.setPen(QColor(colour))
            painter.setBrush(QColor(colour))
            painter.drawRect(QRectF(lx + offset, 4, 10, 10))
            painter.setPen(QColor(TEXT_SECONDARY))
            painter.drawText(QRectF(lx + offset + 14, 4, 40, 12),
                             Qt.AlignmentFlag.AlignLeft, label)

        painter.end()


def _separator() -> QFrame:
    """Horizontal separator line matching the dark theme."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {BORDER};")
    return line


class OverviewTab(QWidget):
    """Dashboard overview — resource gauges, service grid, alerts, history chart."""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Resource gauges ──────────────────────────────────────
        gauges_label = QLabel("System Resources")
        gauges_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(gauges_label)

        self._cpu_gauge = ResourceGauge("CPU", warn_threshold=70, critical_threshold=90)
        layout.addWidget(self._cpu_gauge)

        self._ram_gauge = ResourceGauge("RAM", warn_threshold=70, critical_threshold=85)
        layout.addWidget(self._ram_gauge)

        self._disk_gauge = ResourceGauge("Disk", warn_threshold=80, critical_threshold=90)
        layout.addWidget(self._disk_gauge)

        layout.addWidget(_separator())

        # ── Middle row: services + alerts side by side ───────────
        mid_row = QHBoxLayout()

        # Services
        svc_container = QVBoxLayout()
        svc_label = QLabel("Services")
        svc_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        svc_container.addWidget(svc_label)
        self._service_grid = ServiceStatusGrid()
        svc_container.addWidget(self._service_grid)
        svc_container.addStretch()
        mid_row.addLayout(svc_container, stretch=2)

        # Alerts
        alert_container = QVBoxLayout()
        alert_label = QLabel("Active Alerts")
        alert_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        alert_container.addWidget(alert_label)
        self._alert_row = AlertBadgeRow()
        alert_container.addWidget(self._alert_row)
        alert_container.addStretch()
        mid_row.addLayout(alert_container, stretch=1)

        layout.addLayout(mid_row)

        layout.addWidget(_separator())

        # ── Resource history chart ───────────────────────────────
        chart_label = QLabel("Resource History (24h)")
        chart_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};")
        layout.addWidget(chart_label)

        self._chart = ResourceHistoryChart()
        layout.addWidget(self._chart)

        layout.addStretch()

    def _connect_signals(self) -> None:
        """Wire ApiClient signals to local update methods."""
        self._client.status_updated.connect(self._on_status)
        self._client.resources_updated.connect(self._on_resources)
        self._client.alerts_updated.connect(self._on_alerts)
        self._client.resource_history_updated.connect(self._on_history)

        # Forward service actions from the grid to the client
        self._service_grid.service_action_requested.connect(
            self._client.trigger_service_action
        )
        self._client.service_action_complete.connect(
            self._service_grid.on_action_complete
        )

    def _on_status(self, status: StatusResponse) -> None:
        self._service_grid.update_services(status.services)

    def _on_resources(self, res: ResourceResponse) -> None:
        self._cpu_gauge.set_value(res.cpu_percent)

        ram_detail = ""
        if res.ram.total_mb > 0:
            used_gb = res.ram.used_mb / 1024
            total_gb = res.ram.total_mb / 1024
            ram_detail = f"{used_gb:.1f}/{total_gb:.0f} GB"
        self._ram_gauge.set_value(res.ram.percent, ram_detail)

        if res.disk:
            d = res.disk[0]
            disk_detail = f"{d.used_gb:.0f}/{d.total_gb:.0f} GB"
            self._disk_gauge.set_value(d.percent, disk_detail)

    def _on_alerts(self, alerts: AlertsResponse) -> None:
        self._alert_row.update_counts(
            critical=alerts.critical_count,
            warning=alerts.warning_count,
            info=alerts.info_count,
        )

    def _on_history(self, history: ResourceHistoryResponse) -> None:
        self._chart.update_data(history)

    def refresh(self) -> None:
        """Request fresh data from the backend."""
        self._client.request_status()
        self._client.request_resources()
        self._client.request_alerts()
        self._client.request_resource_history()
