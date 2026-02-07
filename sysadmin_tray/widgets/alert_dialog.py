"""Persistent dialog listing unacknowledged critical alerts.

Replaces repeated ``showMessage()`` toasts for critical alerts with a
single window that stays visible until all criticals are acknowledged
or the user dismisses it.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import AlertInfo

_DIALOG_STYLE = """
    QDialog {
        background-color: #1e1e1e;
    }
    QLabel {
        color: #ddd;
        font-size: 12px;
    }
    QLabel#alert_title {
        font-weight: bold;
        font-size: 13px;
        color: #e74c3c;
    }
    QLabel#alert_message {
        color: #bbb;
        font-size: 11px;
    }
    QLabel#alert_time {
        color: #888;
        font-size: 11px;
    }
    QPushButton {
        background-color: #3d3d3d;
        color: #ddd;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 4px 12px;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: #4d4d4d;
    }
    QPushButton:pressed {
        background-color: #2d2d2d;
    }
    QPushButton#dismiss_btn {
        background-color: #2b2b2b;
    }
"""


class _AlertCard(QWidget):
    """A single alert entry inside the dialog."""

    ack_clicked = pyqtSignal(str)  # alert_id

    def __init__(self, alert: AlertInfo, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._alert_id = alert.id

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # Title row
        title = QLabel(f"\u26a0 {alert.title}")
        title.setObjectName("alert_title")
        layout.addWidget(title)

        # Message
        if alert.message:
            msg = QLabel(alert.message)
            msg.setObjectName("alert_message")
            msg.setWordWrap(True)
            layout.addWidget(msg)

        # Bottom row: timestamp + ack button
        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 2, 0, 0)

        time_str = ""
        if alert.created_at:
            # Show just HH:MM:SS from ISO timestamp
            try:
                time_str = alert.created_at.split("T")[1][:8]
            except (IndexError, AttributeError):
                time_str = str(alert.created_at)
        time_label = QLabel(time_str)
        time_label.setObjectName("alert_time")
        bottom.addWidget(time_label)

        bottom.addStretch()

        ack_btn = QPushButton("Acknowledge")
        ack_btn.clicked.connect(lambda: self.ack_clicked.emit(self._alert_id))
        bottom.addWidget(ack_btn)

        layout.addLayout(bottom)

        # Separator line
        self.setStyleSheet(
            "border-bottom: 1px solid #444; margin-bottom: 2px;"
        )

    @property
    def alert_id(self) -> str:
        return self._alert_id


class CriticalAlertDialog(QDialog):
    """Persistent dialog showing all active unacknowledged critical alerts."""

    alert_ack_requested = pyqtSignal(str)  # alert_id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Critical Alerts")
        self.setStyleSheet(_DIALOG_STYLE)
        self.setMinimumWidth(400)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self._cards: dict[str, _AlertCard] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Scrollable area for alert cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setStyleSheet("background: transparent;")

        self._card_container = QWidget()
        self._card_layout = QVBoxLayout(self._card_container)
        self._card_layout.setContentsMargins(0, 0, 0, 0)
        self._card_layout.setSpacing(2)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._card_container)
        layout.addWidget(self._scroll, stretch=1)

        # Bottom bar
        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        dismiss_btn = QPushButton("Dismiss All")
        dismiss_btn.setObjectName("dismiss_btn")
        dismiss_btn.clicked.connect(self.hide)
        bottom_bar.addWidget(dismiss_btn)
        layout.addLayout(bottom_bar)

    def update_alerts(self, alerts: list[AlertInfo]) -> None:
        """Sync displayed cards with the given list of critical alerts.

        Adds cards for new alerts, removes cards for resolved/acked ones.
        """
        incoming_ids = {a.id for a in alerts}
        current_ids = set(self._cards.keys())

        # Remove cards no longer in the list
        for aid in current_ids - incoming_ids:
            self._remove_card(aid)

        # Add new cards
        for alert in alerts:
            if alert.id not in self._cards:
                self._add_card(alert)

        # Auto-hide if nothing left
        if not self._cards and self.isVisible():
            self.hide()

    def on_alert_acknowledged(self, alert_id: str, success: bool, message: str) -> None:
        """Remove a card after successful acknowledgement."""
        if success and alert_id in self._cards:
            self._remove_card(alert_id)

        # Auto-hide if empty
        if not self._cards and self.isVisible():
            self.hide()

    def _add_card(self, alert: AlertInfo) -> None:
        """Create and insert a card for an alert."""
        card = _AlertCard(alert)
        card.ack_clicked.connect(self.alert_ack_requested)
        self._cards[alert.id] = card
        # Insert before the stretch
        count = self._card_layout.count()
        self._card_layout.insertWidget(count - 1, card)

    def _remove_card(self, alert_id: str) -> None:
        """Remove and destroy a card by alert ID."""
        card = self._cards.pop(alert_id, None)
        if card:
            self._card_layout.removeWidget(card)
            card.deleteLater()

    @property
    def card_count(self) -> int:
        """Number of currently displayed alert cards."""
        return len(self._cards)
