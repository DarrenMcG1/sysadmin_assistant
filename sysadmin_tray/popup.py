"""Frameless stats popup shown when the tray icon is clicked.

Layout:
    ┌──────────────────────────────────────┐
    │  SysAdmin Monitor           ● status │
    ├──────────────────────────────────────┤
    │  CPU  [████████░░░]  72%             │
    │  RAM  [██████░░░░░]  41%  6.5/16 GB  │
    │  Disk [█████████░░]  87%  412/475 GB │
    ├──────────────────────────────────────┤
    │  ● 1 critical  ● 2 warning  ℹ 3 info│
    ├──────────────────────────────────────┤
    │  [ Scan All ]      [ Dashboard ]     │
    ├──────────────────────────────────────┤
    │  Last updated: 14:32:07              │
    └──────────────────────────────────────┘
"""

from __future__ import annotations

import time
from datetime import datetime

from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import (
    ICON_COLOURS,
    AlertsResponse,
    IconState,
    ResourceResponse,
    StatusResponse,
)
from sysadmin_tray.widgets.action_bar import ActionBar
from sysadmin_tray.widgets.alert_badge import AlertBadgeRow
from sysadmin_tray.widgets.resource_gauge import ResourceGauge
from sysadmin_tray.widgets.service_grid import ServiceStatusGrid

_POPUP_STYLE = """
    QWidget#StatsPopup {
        background-color: #1e1e1e;
        border: 1px solid #555;
        border-radius: 8px;
    }
    QLabel {
        color: #ddd;
        font-size: 12px;
    }
    QLabel#title {
        font-size: 14px;
        font-weight: bold;
        color: #fff;
    }
    QLabel#subtitle {
        font-size: 11px;
        color: #888;
    }
"""


def _separator() -> QFrame:
    """Create a horizontal line separator."""
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #444;")
    return line


class StatsPopup(QWidget):
    """Frameless popup displaying system resource gauges and alert badges."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatsPopup")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setStyleSheet(_POPUP_STYLE)
        self.setFixedWidth(360)

        self._last_hidden: float = 0.0  # monotonic timestamp

        self._build_ui()

        # Install event filter for click-outside dismissal
        QApplication.instance().installEventFilter(self)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # ── Header ───────────────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("SysAdmin Monitor")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        self._status_dot = QLabel("\u2b24")  # ⬤
        self._status_dot.setStyleSheet(
            f"color: {ICON_COLOURS[IconState.DISCONNECTED]}; font-size: 14px;"
        )
        header.addWidget(self._status_dot)
        layout.addLayout(header)

        layout.addWidget(_separator())

        # ── Resource gauges ──────────────────────────────────────────
        self._cpu_gauge = ResourceGauge("CPU", warn_threshold=70, critical_threshold=90)
        layout.addWidget(self._cpu_gauge)

        self._ram_gauge = ResourceGauge("RAM", warn_threshold=70, critical_threshold=85)
        layout.addWidget(self._ram_gauge)

        self._disk_gauge = ResourceGauge("Disk", warn_threshold=80, critical_threshold=90)
        layout.addWidget(self._disk_gauge)

        layout.addWidget(_separator())

        # ── Service status grid ───────────────────────────────────────
        self._service_grid = ServiceStatusGrid()
        layout.addWidget(self._service_grid)

        layout.addWidget(_separator())

        # ── Alert badges ─────────────────────────────────────────────
        self._alert_row = AlertBadgeRow()
        layout.addWidget(self._alert_row)

        layout.addWidget(_separator())

        # ── Action bar ───────────────────────────────────────────────
        self.action_bar = ActionBar()
        layout.addWidget(self.action_bar)

        layout.addWidget(_separator())

        # ── Footer ───────────────────────────────────────────────────
        self._timestamp = QLabel("Last updated: —")
        self._timestamp.setObjectName("subtitle")
        layout.addWidget(self._timestamp)

    # ── Public accessors for signal wiring ────────────────────────────

    @property
    def service_grid(self) -> ServiceStatusGrid:
        """Expose the service grid for external signal connections."""
        return self._service_grid

    # ── Data update slots ────────────────────────────────────────────

    def update_resources(self, res: ResourceResponse) -> None:
        """Refresh gauges from a ResourceResponse."""
        self._cpu_gauge.set_value(res.cpu_percent)

        ram_detail = ""
        if res.ram.total_mb > 0:
            used_gb = res.ram.used_mb / 1024
            total_gb = res.ram.total_mb / 1024
            ram_detail = f"{used_gb:.1f}/{total_gb:.0f} GB"
        self._ram_gauge.set_value(res.ram.percent, ram_detail)

        # Show root partition (or first available)
        if res.disk:
            d = res.disk[0]
            disk_detail = f"{d.used_gb:.0f}/{d.total_gb:.0f} GB"
            self._disk_gauge.set_value(d.percent, disk_detail)

        if res.recorded_at:
            try:
                ts = datetime.fromisoformat(res.recorded_at)
                self._timestamp.setText(f"Last updated: {ts.strftime('%H:%M:%S')}")
            except ValueError:
                self._timestamp.setText(f"Last updated: {res.recorded_at}")

    def update_services(self, status: StatusResponse) -> None:
        """Refresh the service grid from a StatusResponse."""
        self._service_grid.update_services(status.services)

    def update_alerts(self, alerts: AlertsResponse) -> None:
        """Refresh alert badge counts."""
        self._alert_row.update_counts(
            critical=alerts.critical_count,
            warning=alerts.warning_count,
            info=alerts.info_count,
        )

    def update_status_dot(self, state: IconState) -> None:
        """Update the status dot colour in the header."""
        colour = ICON_COLOURS[state]
        self._status_dot.setStyleSheet(f"color: {colour}; font-size: 14px;")

    # ── Visibility ───────────────────────────────────────────────────

    def toggle_visibility(self, anchor: QPoint | None = None) -> None:
        """Show or hide the popup, positioning relative to an anchor point."""
        if self.isVisible():
            self.hide()
            self._last_hidden = time.monotonic()
            return

        # Debounce: if the event filter *just* hid us (same click that
        # triggered the tray icon activation), don't re-show immediately.
        if time.monotonic() - self._last_hidden < 0.3:
            return

        if anchor:
            self._position_near(anchor)

        self.show()
        self.raise_()
        self.activateWindow()

    def _position_near(self, anchor: QPoint) -> None:
        """Position the popup above or below the anchor (tray icon area)."""
        screen = QApplication.primaryScreen()
        if not screen:
            return

        screen_geo = screen.availableGeometry()
        popup_size = self.sizeHint()

        # Try above the anchor first (typical for bottom panel)
        x = anchor.x() - popup_size.width() // 2
        y = anchor.y() - popup_size.height() - 8

        # If that goes off-screen top, place below
        if y < screen_geo.top():
            y = anchor.y() + 8

        # Clamp horizontal position
        x = max(screen_geo.left() + 4, min(x, screen_geo.right() - popup_size.width() - 4))

        self.move(x, y)

    # ── Window close (KDE title-bar button) ────────────────────────────

    def closeEvent(self, event):  # noqa: N802 — Qt override
        """Intercept the close button — hide instead of destroying."""
        event.ignore()
        self.hide()
        self._last_hidden = time.monotonic()

    # ── Click-outside dismissal ──────────────────────────────────────

    def eventFilter(self, obj, event):  # noqa: N802 — Qt override
        """Hide popup when user clicks outside it."""
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and self.isVisible()
            and not self.geometry().contains(event.globalPosition().toPoint())
        ):
            self.hide()
            self._last_hidden = time.monotonic()
            return True
        return super().eventFilter(obj, event)
