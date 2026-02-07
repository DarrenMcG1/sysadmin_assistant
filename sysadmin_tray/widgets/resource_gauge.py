"""Labelled progress bar with colour thresholds for resource monitoring."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class ResourceGauge(QWidget):
    """A labelled QProgressBar that changes colour at warning/critical thresholds.

    Layout: ``Label  [████████░░░░]  72%  detail``
    """

    def __init__(
        self,
        label: str,
        warn_threshold: int = 70,
        critical_threshold: int = 85,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._warn = warn_threshold
        self._critical = critical_threshold

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self._label = QLabel(label)
        self._label.setFixedWidth(40)
        self._label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._label)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(16)
        layout.addWidget(self._bar, stretch=1)

        self._pct_label = QLabel("—")
        self._pct_label.setFixedWidth(38)
        self._pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._pct_label)

        self._detail_label = QLabel("")
        self._detail_label.setFixedWidth(110)
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._detail_label)

        self._apply_style(0)

    def set_value(self, percent: float, detail: str = "") -> None:
        """Update the gauge value and optional detail text."""
        pct = max(0, min(100, int(percent)))
        self._bar.setValue(pct)
        self._pct_label.setText(f"{pct}%")
        self._detail_label.setText(detail)
        self._apply_style(pct)

    def _apply_style(self, pct: int) -> None:
        """Set the progress bar colour based on thresholds."""
        if pct >= self._critical:
            colour = "#e74c3c"  # red
        elif pct >= self._warn:
            colour = "#f39c12"  # amber
        else:
            colour = "#27ae60"  # green

        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2d2d2d;
                border: 1px solid #444;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {colour};
                border-radius: 2px;
            }}
        """)
