"""Quick-wins card — the small filesystem findings, display-only.

Surfaces the ``quick_wins`` block the file organiser stores with every
audit (empty directories, stale ``__pycache__``/``.pytest_cache``
folders).  The card has no action.  Its "Clean stale caches" button and
the confirmation text went on 2026-11-11 with
``POST /api/files/clean/stale-caches``, which deleted off the stored
audit with no root confinement (``docs/review/bug-review.md``, finding
H1).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from sysadmin.files.forecast import format_mb
from sysadmin_tray.models import FileQuickWins, FileStatusResponse
from sysadmin_tray.styles import (
    BG_CARD,
    BORDER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class QuickWinsWidget(QFrame):
    """Card listing quick wins.  Display-only: it offers no action."""

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

        self._result_label = QLabel("")
        self._result_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._result_label)

        note = QLabel(
            "Display-only: nothing here deletes. Remove empty directories "
            "and caches by hand."
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
        self._result_label.setText("" if status.has_data else "No scan data yet")
