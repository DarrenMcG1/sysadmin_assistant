"""Per-service status rows displayed in the popup.

Each row shows a coloured status dot, service name, status text,
and response time (if available).

Layout per row::

    ⬤ postgresql       ok        12ms
    ⬤ redis            unreachable  —
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenu, QVBoxLayout, QWidget

from sysadmin_tray.models import ServiceStatus

# Status → colour mapping (reuses project palette)
_STATUS_COLOURS: dict[str, str] = {
    "ok": "#27ae60",
    "degraded": "#f39c12",
    "unreachable": "#e74c3c",
    "error": "#e74c3c",
}

_DEFAULT_COLOUR = "#95a5a6"  # grey for unknown statuses


class ServiceStatusRow(QWidget):
    """A single service row: dot + name + status + response time."""

    action_requested = pyqtSignal(str, str)  # service_name, action

    def __init__(self, name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._name = name
        self._systemd_unit: str | None = None
        self._controllable: bool = True
        self._current_status: str = ""
        self._action_in_progress = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 1, 0, 1)
        layout.setSpacing(6)

        self._dot = QLabel("\u2b24")  # ⬤
        self._dot.setFixedWidth(16)
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dot)

        self._name_label = QLabel(name)
        self._name_label.setFixedWidth(120)
        layout.addWidget(self._name_label)

        self._status_label = QLabel("—")
        self._status_label.setFixedWidth(90)
        layout.addWidget(self._status_label)

        self._time_label = QLabel("")
        self._time_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self._time_label, stretch=1)

    @property
    def service_name(self) -> str:
        return self._name

    def update_status(self, svc: ServiceStatus) -> None:
        """Refresh this row from a ServiceStatus object."""
        self._systemd_unit = svc.systemd_unit
        self._controllable = svc.controllable
        self._current_status = svc.status

        colour = _STATUS_COLOURS.get(svc.status, _DEFAULT_COLOUR)
        self._dot.setStyleSheet(f"color: {colour}; font-size: 10px;")
        self._status_label.setText(svc.status)

        if svc.response_time_ms is not None:
            self._time_label.setText(f"{svc.response_time_ms:.0f}ms")
        else:
            self._time_label.setText("—")

    def set_action_in_progress(self, in_progress: bool) -> None:
        """Toggle the disabled appearance and status text during a pending action."""
        self._action_in_progress = in_progress
        self.setEnabled(not in_progress)
        if in_progress:
            self._status_label.setText("working\u2026")
            self._status_label.setStyleSheet("color: #95a5a6; font-style: italic;")
        else:
            self._status_label.setText(self._current_status or "—")
            self._status_label.setStyleSheet("")

    def contextMenuEvent(self, event) -> None:  # noqa: N802 — Qt override
        """Show restart/start/stop context menu for systemd-managed services."""
        if not self._systemd_unit or not self._controllable or self._action_in_progress:
            return

        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: #2b2b2b; color: #ddd; }"
            "QMenu::item:selected { background: #3d3d3d; }"
        )

        restart_action = QAction("Restart", menu)
        restart_action.triggered.connect(lambda: self.action_requested.emit(self._name, "restart"))
        menu.addAction(restart_action)

        if self._current_status != "ok":
            start_action = QAction("Start", menu)
            start_action.triggered.connect(lambda: self.action_requested.emit(self._name, "start"))
            menu.addAction(start_action)

        if self._current_status == "ok":
            stop_action = QAction("Stop", menu)
            stop_action.triggered.connect(lambda: self.action_requested.emit(self._name, "stop"))
            menu.addAction(stop_action)

        menu.exec(event.globalPos())


class ServiceStatusGrid(QWidget):
    """Container that holds a dynamic set of ServiceStatusRow widgets.

    Rows are created on first encounter and reused on subsequent updates.
    Services that disappear from the response have their rows removed.
    """

    service_action_requested = pyqtSignal(str, str)  # service_name, action

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._rows: dict[str, ServiceStatusRow] = {}

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)

    def update_services(self, services: list[ServiceStatus]) -> None:
        """Sync grid rows with the given service list."""
        seen: set[str] = set()

        for svc in services:
            seen.add(svc.name)
            if svc.name not in self._rows:
                row = ServiceStatusRow(svc.name)
                row.action_requested.connect(self._on_row_action)
                self._rows[svc.name] = row
                self._layout.addWidget(row)
            self._rows[svc.name].update_status(svc)

        # Remove rows for services no longer present
        for name in list(self._rows):
            if name not in seen:
                row = self._rows.pop(name)
                self._layout.removeWidget(row)
                row.deleteLater()

    def _on_row_action(self, service_name: str, action: str) -> None:
        """Forward a row's action request, disabling the row meanwhile."""
        if service_name in self._rows:
            self._rows[service_name].set_action_in_progress(True)
        self.service_action_requested.emit(service_name, action)

    def on_action_complete(
        self, service_name: str, action: str, success: bool, message: str
    ) -> None:
        """Re-enable the row after a service action completes."""
        if service_name in self._rows:
            self._rows[service_name].set_action_in_progress(False)
