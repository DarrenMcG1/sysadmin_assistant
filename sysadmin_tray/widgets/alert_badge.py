"""Severity-coloured alert count badges."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

_SEVERITY_COLOURS = {
    "critical": "#e74c3c",
    "warning": "#f39c12",
    "info": "#3498db",
}

_SEVERITY_SYMBOLS = {
    "critical": "\u2b24",   # ⬤ large circle
    "warning": "\u2b24",
    "info": "\u2139",       # ℹ
}


class AlertBadge(QWidget):
    """A single severity count: ``● 3 critical``."""

    def __init__(self, severity: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._severity = severity

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        colour = _SEVERITY_COLOURS.get(severity, "#888")
        symbol = _SEVERITY_SYMBOLS.get(severity, "\u2022")

        self._dot = QLabel(symbol)
        self._dot.setStyleSheet(f"color: {colour}; font-size: 10px;")
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._dot)

        self._count_label = QLabel("0")
        self._count_label.setStyleSheet(f"color: {colour}; font-weight: bold;")
        layout.addWidget(self._count_label)

        self._text_label = QLabel(severity)
        self._text_label.setStyleSheet("color: #ccc;")
        layout.addWidget(self._text_label)

    def set_count(self, count: int) -> None:
        """Update the displayed count."""
        self._count_label.setText(str(count))


class AlertBadgeRow(QWidget):
    """Row of critical / warning / info badges."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)

        self._critical = AlertBadge("critical")
        self._warning = AlertBadge("warning")
        self._info = AlertBadge("info")

        layout.addWidget(self._critical)
        layout.addWidget(self._warning)
        layout.addWidget(self._info)
        layout.addStretch()

    def update_counts(
        self, critical: int = 0, warning: int = 0, info: int = 0
    ) -> None:
        """Set all three counts at once."""
        self._critical.set_count(critical)
        self._warning.set_count(warning)
        self._info.set_count(info)
