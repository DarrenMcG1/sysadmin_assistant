"""Projects tab — project health cards with managed/all toggle.

Displays project health scores, grades, branch/TODO counts, and metadata
from the project organiser agent scans.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sysadmin_tray.models import (
    ManagedProjectInfo,
    ManagedProjectsResponse,
    ProjectOverviewEntry,
    ProjectOverviewResponse,
)
from sysadmin_tray.styles import (
    AMBER,
    BG_CARD,
    BG_PRIMARY,
    BORDER,
    BUTTON_STYLE,
    COMBOBOX_STYLE,
    GREEN,
    GREY,
    RED,
    STATUS_COLOURS,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)


def _score_colour(score: int) -> str:
    """Return a colour hex based on health score."""
    if score >= 80:
        return GREEN
    if score >= 60:
        return AMBER
    return RED


class ProjectCard(QFrame):
    """A card showing a project's health score, grade, and metadata."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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
        layout.setSpacing(4)

        # ── Top row: name + score ────────────────────────────
        top = QHBoxLayout()
        self._name_label = QLabel()
        self._name_label.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {TEXT_PRIMARY};"
        )
        top.addWidget(self._name_label)
        top.addStretch()
        self._score_label = QLabel()
        self._score_label.setStyleSheet(f"font-size: 13px; font-weight: bold;")
        top.addWidget(self._score_label)
        layout.addLayout(top)

        # ── Health bar ───────────────────────────────────────
        bar_row = QHBoxLayout()
        self._grade_label = QLabel()
        self._grade_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        self._grade_label.setFixedWidth(100)
        bar_row.addWidget(self._grade_label)

        self._health_bar = QProgressBar()
        self._health_bar.setRange(0, 100)
        self._health_bar.setTextVisible(False)
        self._health_bar.setFixedHeight(14)
        bar_row.addWidget(self._health_bar, stretch=1)
        layout.addLayout(bar_row)

        # ── Detail row ───────────────────────────────────────
        self._detail_label = QLabel()
        self._detail_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self._detail_label.setWordWrap(True)
        layout.addWidget(self._detail_label)

        # ── Metadata row ─────────────────────────────────────
        self._meta_label = QLabel()
        self._meta_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._meta_label)

        # ── Services row (managed projects only) ─────────────
        self._services_label = QLabel()
        self._services_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        self._services_label.setVisible(False)
        layout.addWidget(self._services_label)

    def update_from_overview(self, proj: ProjectOverviewEntry) -> None:
        """Populate from a project overview entry (all projects view)."""
        score = proj.health_score
        colour = _score_colour(score)

        self._name_label.setText(proj.name)
        self._score_label.setText(f"Score: {score}/100")
        self._score_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {colour};")

        grade_display = proj.grade.replace("_", " ").title()
        self._grade_label.setText(f"Grade: {grade_display}")

        self._health_bar.setValue(score)
        self._health_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2d2d2d;
                border: 1px solid {BORDER};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {colour};
                border-radius: 2px;
            }}
        """)

        stale = proj.stale_branch_count
        branch_text = f"Branches: {proj.branch_count}"
        if stale > 0:
            branch_text += f" ({stale} stale)"
        detail_parts = [branch_text, f"TODOs: {proj.todo_count}"]
        self._detail_label.setText("  \u00b7  ".join(detail_parts))

        meta_parts = []
        if proj.last_commit_at:
            # Extract date portion
            date = proj.last_commit_at.split("T")[0] if "T" in proj.last_commit_at else proj.last_commit_at
            meta_parts.append(f"Last commit: {date}")
        if proj.total_size_mb:
            meta_parts.append(f"Size: {proj.total_size_mb:.0f} MB")
        readme = "\u2713" if proj.has_readme else "\u2717"
        claude = "\u2713" if proj.has_claude_md else "\u2717"
        meta_parts.append(f"README: {readme}  CLAUDE.md: {claude}")
        self._meta_label.setText("  \u00b7  ".join(meta_parts))

        self._services_label.setVisible(False)

    def update_from_managed(self, proj: ManagedProjectInfo) -> None:
        """Populate from a managed project entry."""
        self._name_label.setText(proj.name)

        # Score from project_health if available
        score = 0
        if proj.project_health:
            score = proj.project_health.health_score
        colour = _score_colour(score)

        if proj.project_health:
            self._score_label.setText(f"Score: {score}/100")
            self._score_label.setStyleSheet(
                f"font-size: 13px; font-weight: bold; color: {colour};"
            )
            self._health_bar.setValue(score)
        else:
            self._score_label.setText("Not scanned")
            self._score_label.setStyleSheet(
                f"font-size: 13px; color: {TEXT_MUTED};"
            )
            self._health_bar.setValue(0)

        self._health_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: #2d2d2d;
                border: 1px solid {BORDER};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {colour};
                border-radius: 2px;
            }}
        """)

        # Grade from score
        if score >= 80:
            grade = "Healthy"
        elif score >= 60:
            grade = "Needs Attention"
        elif score >= 40:
            grade = "Neglected"
        elif score > 0:
            grade = "Abandoned"
        else:
            grade = "\u2014"
        self._grade_label.setText(f"Grade: {grade}")

        self._detail_label.setText(f"Path: {proj.path}")
        self._meta_label.setText("")

        # Services
        if proj.services:
            svc_parts = []
            for svc in proj.services:
                dot_colour = STATUS_COLOURS.get(svc.status, GREY)
                svc_parts.append(
                    f'<span style="color:{dot_colour}">\u2b24</span> {svc.name}: {svc.status}'
                )
            self._services_label.setText("  ".join(svc_parts))
            self._services_label.setTextFormat(Qt.TextFormat.RichText)
            self._services_label.setVisible(True)
        else:
            self._services_label.setVisible(False)


class ProjectsTab(QWidget):
    """Dashboard tab for project health monitoring."""

    def __init__(self, client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._client = client
        self._cards: list[ProjectCard] = []
        self._overview_data: ProjectOverviewResponse | None = None
        self._managed_data: ManagedProjectsResponse | None = None
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # ── Header row ───────────────────────────────────────
        header = QHBoxLayout()
        title = QLabel("Projects")
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {TEXT_PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self._view_combo = QComboBox()
        self._view_combo.setStyleSheet(COMBOBOX_STYLE)
        self._view_combo.addItem("Managed", "managed")
        self._view_combo.addItem("All Projects", "all")
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        header.addWidget(self._view_combo)

        self._scan_btn = QPushButton("Trigger Scan")
        self._scan_btn.setStyleSheet(BUTTON_STYLE)
        self._scan_btn.clicked.connect(self._on_scan)
        header.addWidget(self._scan_btn)

        layout.addLayout(header)

        # ── Scrollable card area ─────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background-color: {BG_PRIMARY};")

        self._cards_container = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setSpacing(8)
        self._cards_layout.addStretch()

        scroll.setWidget(self._cards_container)
        layout.addWidget(scroll)

        # ── Status bar ───────────────────────────────────────
        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        layout.addWidget(self._status_label)

    def _connect_signals(self) -> None:
        self._client.project_overview_updated.connect(self._on_overview)
        self._client.managed_projects_updated.connect(self._on_managed)
        self._client.scan_complete.connect(self._on_scan_complete)

    def _on_overview(self, data: ProjectOverviewResponse) -> None:
        self._overview_data = data
        if self._current_view() == "all":
            self._render_overview()

    def _on_managed(self, data: ManagedProjectsResponse) -> None:
        self._managed_data = data
        if self._current_view() == "managed":
            self._render_managed()

    def _current_view(self) -> str:
        return self._view_combo.currentData() or "managed"

    def _on_view_changed(self) -> None:
        view = self._current_view()
        if view == "managed":
            if self._managed_data:
                self._render_managed()
            self._client.request_managed_projects()
        else:
            if self._overview_data:
                self._render_overview()
            self._client.request_project_overview()

    def _clear_cards(self) -> None:
        """Remove all existing cards."""
        for card in self._cards:
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()

    def _render_overview(self) -> None:
        """Render project cards from overview data."""
        if not self._overview_data:
            return
        self._clear_cards()
        for proj in self._overview_data.projects:
            card = ProjectCard()
            card.update_from_overview(proj)
            self._cards.append(card)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._status_label.setText(f"{self._overview_data.count} projects")

    def _render_managed(self) -> None:
        """Render project cards from managed projects data."""
        if not self._managed_data:
            return
        self._clear_cards()
        for proj in self._managed_data.projects:
            card = ProjectCard()
            card.update_from_managed(proj)
            self._cards.append(card)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._status_label.setText(f"{self._managed_data.count} managed projects")

    def _on_scan(self) -> None:
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning\u2026")
        self._client.trigger_scan()

    def _on_scan_complete(self, success: bool, message: str) -> None:
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Trigger Scan")
        # Refresh data after scan
        if success:
            self.refresh()

    def refresh(self) -> None:
        """Request fresh data based on current view."""
        if self._current_view() == "managed":
            self._client.request_managed_projects()
        else:
            self._client.request_project_overview()
