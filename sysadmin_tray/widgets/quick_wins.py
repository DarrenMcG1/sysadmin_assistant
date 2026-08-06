"""Quick-wins card — one-click-fixable filesystem findings.

Surfaces the ``quick_wins`` block the file organiser stores with every
audit (empty directories, stale ``__pycache__``/``.pytest_cache``
folders).  Only the stale-cache clean is wired to an action; everything
else is display-only until the corresponding backend endpoints land.

The confirmation *copy* is built by a pure function so the exact wording
shown before anything is deleted can be asserted in tests without a
modal dialog.
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from sysadmin.services.forecast import format_mb
from sysadmin_tray.models import FileQuickWins, FileStatusResponse
from sysadmin_tray.styles import (
    BG_CARD,
    BORDER,
    BUTTON_STYLE,
    GREEN,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

# The backend deletes at most this many empty directories per call
# (``sysadmin/routers/files.py`` slices ``empty_dirs`` at 50) — the
# confirmation must not promise more than that.
EMPTY_DIR_CLEAN_LIMIT = 50


def clean_confirmation_text(quick_wins: FileQuickWins) -> str:
    """Exact description of what the stale-cache clean will remove.

    Shown verbatim in the confirmation dialog — no euphemisms, and the
    empty-directory cap is stated because the endpoint enforces it.
    """
    empty_dirs = min(quick_wins.empty_dirs, EMPTY_DIR_CLEAN_LIMIT)
    lines = [
        "This will permanently delete:",
        "",
        f"  • {quick_wins.stale_caches} cache directories "
        f"(__pycache__, .pytest_cache) — {quick_wins.stale_cache_mb:.0f} MB",
        f"  • {empty_dirs} empty directories",
    ]
    if quick_wins.empty_dirs > EMPTY_DIR_CLEAN_LIMIT:
        lines.append(
            f"    ({quick_wins.empty_dirs} were found; the backend removes at "
            f"most {EMPTY_DIR_CLEAN_LIMIT} per run)"
        )
    lines += [
        "",
        "Targets come from the most recent scan, so anything created "
        "since then is untouched. This cannot be undone.",
    ]
    return "\n".join(lines)


class QuickWinsWidget(QFrame):
    """Card listing quick wins, with a clean button for stale caches."""

    clean_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._quick_wins = FileQuickWins()
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background-color: {BG_CARD};
                border: 1px solid {BORDER};
                border-radius: 6px;
            }}
        """)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel("Quick Wins")
        title.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(3)

        self._value_labels: dict[str, QLabel] = {}
        for row, (key, caption) in enumerate(
            [
                ("empty_dirs", "Empty directories"),
                ("stale_caches", "Stale caches"),
                ("stale_cache_mb", "Cache size"),
            ]
        ):
            caption_label = QLabel(caption)
            caption_label.setStyleSheet(
                f"font-size: 11px; color: {TEXT_SECONDARY};"
            )
            value_label = QLabel("—")
            value_label.setStyleSheet(
                f"font-size: 11px; font-weight: bold; color: {TEXT_PRIMARY};"
            )
            grid.addWidget(caption_label, row, 0)
            grid.addWidget(value_label, row, 1)
            self._value_labels[key] = value_label
        grid.setColumnStretch(2, 1)
        layout.addLayout(grid)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 4, 0, 0)
        self._clean_btn = QPushButton("Clean stale caches…")
        self._clean_btn.setStyleSheet(BUTTON_STYLE)
        self._clean_btn.setEnabled(False)
        self._clean_btn.clicked.connect(self.clean_requested)
        button_row.addWidget(self._clean_btn)
        button_row.addStretch()

        self._result_label = QLabel("")
        self._result_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        button_row.addWidget(self._result_label)
        layout.addLayout(button_row)

        note = QLabel(
            "Duplicate, misplaced and old-download cleanup are display-only "
            "until the file-action endpoints land."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED};")
        layout.addWidget(note)

    # ── Data ─────────────────────────────────────────────────────────

    @property
    def quick_wins(self) -> FileQuickWins:
        return self._quick_wins

    def update_from_status(self, status: FileStatusResponse) -> None:
        """Populate from ``GET /api/files/status``."""
        self._quick_wins = status.quick_wins
        qw = self._quick_wins
        self._value_labels["empty_dirs"].setText(str(qw.empty_dirs))
        self._value_labels["stale_caches"].setText(str(qw.stale_caches))
        self._value_labels["stale_cache_mb"].setText(format_mb(qw.stale_cache_mb))
        self._clean_btn.setEnabled(status.has_data and qw.total > 0)
        if not status.has_data:
            self._result_label.setText("No scan data yet")

    def set_cleaning(self, busy: bool) -> None:
        """Disable the button and show progress while a clean runs."""
        self._clean_btn.setEnabled(not busy and self._quick_wins.total > 0)
        self._clean_btn.setText(
            "Cleaning…" if busy else "Clean stale caches…"
        )

    def show_result(self, success: bool, message: str) -> None:
        """Report the outcome of a clean next to the button."""
        colour = GREEN if success else TEXT_MUTED
        self._result_label.setStyleSheet(f"font-size: 11px; color: {colour};")
        self._result_label.setText(message)

    def set_available(self, available: bool) -> None:
        """Disable the action when the backend is unreachable."""
        if not available:
            self._clean_btn.setEnabled(False)
        else:
            self._clean_btn.setEnabled(self._quick_wins.total > 0)
