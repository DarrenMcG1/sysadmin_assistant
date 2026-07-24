"""Files tab — filesystem audit findings from the file organiser agent.

Read-only by design for this session: the tab surfaces what the existing
``GET /api/files/*`` endpoints already return (audit summary, quick
wins, duplicates, misplaced files, large files, growth forecast) and
offers exactly two actions, neither of which touches user data
destructively beyond an explicit confirmation:

* **Rescan** — ``POST /api/files/scan``, a read-only re-audit.
* **Clean stale caches** — ``POST /api/files/clean/stale-caches``, which
  predates this session, is gated behind a confirmation dialog spelling
  out precisely what will be deleted.

Duplicate/misplaced/old-download *cleanup* is deliberately absent: those
endpoints are being written separately and are not merged yet.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.forecast import format_mb
from sysadmin_tray.models import (
    DuplicatesResponse,
    FileStatusResponse,
    FileTrendsResponse,
    LargeFilesResponse,
    MisplacedFilesResponse,
    ResourceHistoryResponse,
)
from sysadmin_tray.styles import (
    BORDER,
    BUTTON_STYLE,
    COMBOBOX_STYLE,
    TABLE_STYLE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from sysadmin_tray.widgets.disk_forecast import DiskForecastWidget
from sysadmin_tray.widgets.quick_wins import QuickWinsWidget, clean_confirmation_text

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)

# Days of resource history to fit the disk projection over.
FORECAST_HISTORY_DAYS = 30
FORECAST_HISTORY_HOURS = FORECAST_HISTORY_DAYS * 24

VIEW_DUPLICATES = "duplicates"
VIEW_MISPLACED = "misplaced"
VIEW_LARGE = "large"

_VIEW_COLUMNS: dict[str, list[str]] = {
    VIEW_DUPLICATES: ["Copies", "Size group", "Paths"],
    VIEW_MISPLACED: ["Category", "File"],
    VIEW_LARGE: ["Size", "Path"],
}


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet(f"color: {BORDER};")
    return line


class FilesTab(QWidget):
    """Dashboard tab for filesystem audit findings."""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._duplicates: DuplicatesResponse | None = None
        self._misplaced: MisplacedFilesResponse | None = None
        self._large: LargeFilesResponse | None = None
        self._build_ui()
        self._connect_signals()

    # ── UI ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Header ───────────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Files")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        header.addWidget(title)
        header.addStretch()

        self._scan_btn = QPushButton("Rescan")
        self._scan_btn.setStyleSheet(BUTTON_STYLE)
        self._scan_btn.clicked.connect(self._on_scan)
        header.addWidget(self._scan_btn)
        layout.addLayout(header)

        # ── Summary line ─────────────────────────────────────
        self._summary_label = QLabel("Loading…")
        self._summary_label.setWordWrap(True)
        self._summary_label.setStyleSheet(
            f"font-size: 11px; color: {TEXT_SECONDARY};"
        )
        layout.addWidget(self._summary_label)

        self._reclaimable_label = QLabel("")
        self._reclaimable_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        layout.addWidget(self._reclaimable_label)

        # ── Quick wins + forecast side by side ───────────────
        cards = QHBoxLayout()
        cards.setSpacing(8)
        self._quick_wins = QuickWinsWidget()
        cards.addWidget(self._quick_wins, stretch=1)
        self._forecast = DiskForecastWidget()
        cards.addWidget(self._forecast, stretch=1)
        layout.addLayout(cards)

        layout.addWidget(_separator())

        # ── Findings table ───────────────────────────────────
        table_header = QHBoxLayout()
        findings_label = QLabel("Findings")
        findings_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        table_header.addWidget(findings_label)
        table_header.addStretch()

        self._view_combo = QComboBox()
        self._view_combo.setStyleSheet(COMBOBOX_STYLE)
        self._view_combo.addItem("Duplicates", VIEW_DUPLICATES)
        self._view_combo.addItem("Misplaced", VIEW_MISPLACED)
        self._view_combo.addItem("Large files", VIEW_LARGE)
        self._view_combo.currentIndexChanged.connect(self._render_table)
        table_header.addWidget(self._view_combo)
        layout.addLayout(table_header)

        self._table = QTableWidget()
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, stretch=1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        self._client.file_status_updated.connect(self._on_status)
        self._client.file_duplicates_updated.connect(self._on_duplicates)
        self._client.file_misplaced_updated.connect(self._on_misplaced)
        self._client.file_large_updated.connect(self._on_large)
        self._client.file_trends_updated.connect(self._on_trends)
        self._client.resource_history_updated.connect(self._on_history)
        self._client.file_fetch_failed.connect(self._on_fetch_failed)
        self._client.file_scan_triggered.connect(self._on_scan_triggered)
        self._client.stale_caches_cleaned.connect(self._on_cleaned)
        self._client.connection_lost.connect(self._on_connection_lost)
        self._client.connection_restored.connect(self._on_connection_restored)

        self._quick_wins.clean_requested.connect(self._on_clean_requested)

    # ── Data handlers ────────────────────────────────────────────────

    def _on_status(self, status: FileStatusResponse) -> None:
        self._quick_wins.update_from_status(status)

        if not status.has_data:
            self._summary_label.setText(
                status.message
                or "No filesystem audit yet — press Rescan to run one."
            )
            self._reclaimable_label.setText("")
            return

        summary = status.summary
        parts = [
            f"Duplicates: {summary.duplicate_groups}",
            f"Misplaced: {summary.misplaced_files}",
            f"Large files: {summary.large_files}",
            f"Old downloads: {summary.old_downloads}",
            f"Empty dirs: {summary.empty_dirs}",
            f"Stale caches: {summary.stale_project_dirs}",
        ]
        scanned = (status.scanned_at or "").split("T")[0]
        root = status.scan_root or "—"
        self._summary_label.setText(
            f"{root}  ·  scanned {scanned or 'unknown'}\n" + "  ·  ".join(parts)
        )
        self._reclaimable_label.setText(
            f"Reclaimable: {format_mb(status.reclaimable_mb)}"
        )

    def _on_duplicates(self, data: DuplicatesResponse) -> None:
        self._duplicates = data
        if self._current_view() == VIEW_DUPLICATES:
            self._render_table()

    def _on_misplaced(self, data: MisplacedFilesResponse) -> None:
        self._misplaced = data
        if self._current_view() == VIEW_MISPLACED:
            self._render_table()

    def _on_large(self, data: LargeFilesResponse) -> None:
        self._large = data
        if self._current_view() == VIEW_LARGE:
            self._render_table()

    def _on_trends(self, trends: FileTrendsResponse) -> None:
        self._forecast.update_from_trends(trends)

    def _on_history(self, history: ResourceHistoryResponse) -> None:
        self._forecast.update_from_history(history)

    def _on_fetch_failed(self, what: str, message: str) -> None:
        logger.debug("files tab: %s unavailable (%s)", what, message)
        self._status_label.setText(f"Could not load {what}: {message}")

    # ── Table rendering ──────────────────────────────────────────────

    def _current_view(self) -> str:
        return self._view_combo.currentData() or VIEW_DUPLICATES

    def _render_table(self) -> None:
        view = self._current_view()
        columns = _VIEW_COLUMNS[view]
        self._table.clear()
        self._table.setColumnCount(len(columns))
        self._table.setHorizontalHeaderLabels(columns)

        rows = self._rows_for(view)
        self._table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, text in enumerate(row):
                self._table.setItem(r, c, QTableWidgetItem(text))

        header = self._table.horizontalHeader()
        for c in range(len(columns) - 1):
            header.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(
            len(columns) - 1, QHeaderView.ResizeMode.Stretch
        )

        self._status_label.setText(self._status_for(view, len(rows)))

    def _rows_for(self, view: str) -> list[list[str]]:
        """Flatten the loaded response for the selected view."""
        if view == VIEW_DUPLICATES:
            if self._duplicates is None:
                return []
            return [
                [
                    str(group.count),
                    (group.hash or "")[:12],
                    "  |  ".join(group.files),
                ]
                for group in self._duplicates.duplicate_groups
            ]

        if view == VIEW_MISPLACED:
            if self._misplaced is None:
                return []
            return [
                [category, path]
                for category in sorted(self._misplaced.misplaced_files)
                for path in self._misplaced.misplaced_files[category]
            ]

        if self._large is None:
            return []
        return [
            [format_mb(entry.size_mb), entry.path]
            for entry in self._large.large_files
        ]

    def _status_for(self, view: str, shown: int) -> str:
        loaded = {
            VIEW_DUPLICATES: self._duplicates,
            VIEW_MISPLACED: self._misplaced,
            VIEW_LARGE: self._large,
        }[view]
        if loaded is None:
            return "Loading…"
        if shown == 0:
            return "Nothing found — run a scan if this looks wrong."
        noun = {
            VIEW_DUPLICATES: "duplicate groups",
            VIEW_MISPLACED: "misplaced files",
            VIEW_LARGE: "large files",
        }[view]
        return f"{shown} {noun}"

    # ── Actions ──────────────────────────────────────────────────────

    def _on_scan(self) -> None:
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning…")
        self._client.trigger_file_scan()

    def _on_scan_triggered(self, success: bool, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Rescan")
        self._status_label.setText(message)

    def _on_clean_requested(self) -> None:
        """Confirm, in full, before deleting anything."""
        confirmed = self._confirm_clean(
            clean_confirmation_text(self._quick_wins.quick_wins)
        )
        if not confirmed:
            return
        self._quick_wins.set_cleaning(True)
        self._client.clean_stale_caches()

    def _confirm_clean(self, detail: str) -> bool:
        """Show the confirmation dialog — split out so tests can stub it."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Clean stale caches")
        box.setText("Delete stale caches and empty directories?")
        box.setInformativeText(detail)
        box.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes
        )
        box.setDefaultButton(QMessageBox.StandardButton.Cancel)
        return box.exec() == QMessageBox.StandardButton.Yes

    def _on_cleaned(self, success: bool, message: str) -> None:
        self._quick_wins.set_cleaning(False)
        self._quick_wins.show_result(success, message)
        if success:
            self.refresh()

    # ── Connection state ─────────────────────────────────────────────

    def _on_connection_lost(self) -> None:
        self._status_label.setText("Backend unreachable — showing last known data")
        self._scan_btn.setEnabled(False)
        self._quick_wins.set_available(False)
        self._forecast.show_unavailable()

    def _on_connection_restored(self) -> None:
        self._status_label.setText("")
        self._scan_btn.setEnabled(True)
        self._quick_wins.set_available(True)
        self.refresh()

    # ── Refresh ──────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Request every read endpoint this tab renders."""
        self._client.request_file_status()
        self._client.request_file_trends()
        self._client.request_file_duplicates()
        self._client.request_file_misplaced()
        self._client.request_file_large()
        self._client.request_resource_history(FORECAST_HISTORY_HOURS)
