"""Quick-action button row for the stats popup."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QWidget

_BUTTON_STYLE = """
    QPushButton {
        background-color: #3a3a3a;
        color: #ddd;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 6px 14px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #4a4a4a;
        border-color: #777;
    }
    QPushButton:pressed {
        background-color: #2a2a2a;
    }
    QPushButton:disabled {
        background-color: #2d2d2d;
        color: #666;
        border-color: #444;
    }
"""


class ActionBar(QWidget):
    """Row of quick-action buttons: Scan All, Open Dashboard.

    Signals:
        ``scan_requested``: emitted when the Scan All button is clicked.
        ``dashboard_requested``: emitted when the Dashboard button is clicked.
    """

    scan_requested = pyqtSignal()
    dashboard_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        self._scan_btn = QPushButton("Scan All")
        self._scan_btn.setStyleSheet(_BUTTON_STYLE)
        self._scan_btn.clicked.connect(self._on_scan_clicked)
        layout.addWidget(self._scan_btn)

        self._dashboard_btn = QPushButton("Dashboard")
        self._dashboard_btn.setStyleSheet(_BUTTON_STYLE)
        self._dashboard_btn.clicked.connect(self.dashboard_requested.emit)
        layout.addWidget(self._dashboard_btn)

    def _on_scan_clicked(self) -> None:
        """Disable button briefly to prevent double-clicks, then emit."""
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning…")
        self.scan_requested.emit()

    def on_scan_complete(self, success: bool, message: str) -> None:
        """Re-enable the scan button after the API responds."""
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan All")
