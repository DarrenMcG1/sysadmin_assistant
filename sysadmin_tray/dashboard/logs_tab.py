"""Logs tab — real-time log viewer with source/severity/hours filtering.

Auto-refreshes every 5 seconds when visible, with colour-coded severity
rows and auto-scroll to bottom.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import LogsResponse, LogStatsResponse
from sysadmin_tray.styles import (
    AMBER,
    COMBOBOX_STYLE,
    RED,
    TABLE_STYLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)

_SEVERITY_ROW_COLOURS: dict[str, str] = {
    "critical": RED,
    "error": RED,
    "warning": AMBER,
    "info": TEXT_PRIMARY,
    "debug": TEXT_MUTED,
}


class LogsTab(QWidget):
    """Dashboard tab for viewing and filtering log entries."""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._known_sources: list[str] = []
        self._auto_scroll = True
        self._build_ui()
        self._connect_signals()

        # Auto-refresh timer (5 seconds), only active when tab is visible
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(5000)
        self._refresh_timer.timeout.connect(self._fetch_logs)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Filter row ───────────────────────────────────────
        filter_row = QHBoxLayout()

        filter_row.addWidget(QLabel("Source:"))
        self._source_combo = QComboBox()
        self._source_combo.setStyleSheet(COMBOBOX_STYLE)
        self._source_combo.addItem("All", "")
        self._source_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._source_combo)

        filter_row.addWidget(QLabel("Severity:"))
        self._severity_combo = QComboBox()
        self._severity_combo.setStyleSheet(COMBOBOX_STYLE)
        self._severity_combo.addItem("All", "")
        for sev in ("critical", "error", "warning", "info"):
            self._severity_combo.addItem(sev, sev)
        self._severity_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._severity_combo)

        filter_row.addWidget(QLabel("Hours:"))
        self._hours_combo = QComboBox()
        self._hours_combo.setStyleSheet(COMBOBOX_STYLE)
        for h in (1, 4, 12, 24, 48):
            self._hours_combo.addItem(str(h), h)
        self._hours_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_row.addWidget(self._hours_combo)

        filter_row.addStretch()

        self._auto_refresh_cb = QCheckBox("Auto-refresh")
        self._auto_refresh_cb.setChecked(True)
        self._auto_refresh_cb.setStyleSheet(f"color: {TEXT_PRIMARY};")
        self._auto_refresh_cb.toggled.connect(self._on_auto_refresh_toggled)
        filter_row.addWidget(self._auto_refresh_cb)

        layout.addLayout(filter_row)

        # ── Log table ────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Time", "Source", "Severity", "Message"])
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 120)
        self._table.setColumnWidth(2, 80)

        layout.addWidget(self._table)

        # ── Status bar ───────────────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        self._client.logs_updated.connect(self._on_logs)
        self._client.log_stats_updated.connect(self._on_stats)

    def _on_logs(self, logs: LogsResponse) -> None:
        """Populate the table with log entries."""
        scrollbar = self._table.verticalScrollBar()
        was_at_bottom = (
            scrollbar.value() >= scrollbar.maximum() - 2
            if scrollbar.maximum() > 0
            else True
        )

        self._table.setRowCount(logs.count)
        for i, entry in enumerate(logs.entries):
            colour = QColor(_SEVERITY_ROW_COLOURS.get(entry.severity, TEXT_PRIMARY))

            # Time column — extract HH:MM:SS
            time_str = ""
            if entry.logged_at:
                try:
                    ts = datetime.fromisoformat(entry.logged_at)
                    time_str = ts.strftime("%H:%M:%S")
                except ValueError:
                    time_str = entry.logged_at[:8]

            for col, text in enumerate([time_str, entry.source, entry.severity, entry.message]):
                item = QTableWidgetItem(text)
                item.setForeground(colour)
                self._table.setItem(i, col, item)

        self._status_label.setText(f"{logs.count} entries")

        # Auto-scroll to bottom if user was already there
        if was_at_bottom and self._auto_scroll:
            self._table.scrollToBottom()

    def _on_stats(self, stats: LogStatsResponse) -> None:
        """Update source dropdown from log stats."""
        new_sources = sorted(stats.sources.keys())
        if new_sources != self._known_sources:
            self._known_sources = new_sources
            current = self._source_combo.currentData()
            self._source_combo.blockSignals(True)
            self._source_combo.clear()
            self._source_combo.addItem("All", "")
            for source in new_sources:
                self._source_combo.addItem(source, source)
            # Restore selection
            idx = self._source_combo.findData(current)
            if idx >= 0:
                self._source_combo.setCurrentIndex(idx)
            self._source_combo.blockSignals(False)

    def _on_filter_changed(self) -> None:
        """Re-fetch logs when any filter changes."""
        self._fetch_logs()

    def _on_auto_refresh_toggled(self, checked: bool) -> None:
        if checked and self.isVisible():
            self._refresh_timer.start()
        else:
            self._refresh_timer.stop()

    def _fetch_logs(self) -> None:
        """Request logs with current filter settings."""
        source = self._source_combo.currentData() or ""
        severity = self._severity_combo.currentData() or ""
        hours = self._hours_combo.currentData() or 1
        self._client.request_logs(hours, source, severity)

    def refresh(self) -> None:
        """Called when tab becomes visible — start timer and fetch data."""
        self._client.request_log_stats()
        self._fetch_logs()
        if self._auto_refresh_cb.isChecked():
            self._refresh_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        """Stop auto-refresh when tab is no longer visible."""
        self._refresh_timer.stop()
        super().hideEvent(event)
