"""Dashboard main window — tab container with hide-on-close behaviour.

The window is created once and shown/hidden on demand.  Each tab connects
itself to ApiClient signals in its own ``__init__``, keeping wiring
localised rather than centralised in this file.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QTabWidget

from sysadmin_tray.styles import DASHBOARD_STYLE

if TYPE_CHECKING:
    from sysadmin_tray.client import ApiClient

logger = logging.getLogger(__name__)


class DashboardWindow(QMainWindow):
    """Native dashboard window with tabbed interface.

    Hides on close (rather than destroying) so the tray app stays
    alive.  Tabs call ``refresh()`` when the window is shown or when
    the user switches to them — no background polling when hidden.
    """

    def __init__(self, client: ApiClient, parent=None) -> None:
        super().__init__(parent)
        self._client = client

        self.setWindowTitle("SysAdmin Dashboard")
        self.setMinimumSize(720, 520)
        self.resize(840, 600)
        self.setStyleSheet(DASHBOARD_STYLE)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        # Tabs are added by phases — each phase appends its tab
        self._tab_widgets: list = []

        # Refresh active tab when user switches
        self._tabs.currentChanged.connect(self._on_tab_changed)

    @property
    def client(self) -> ApiClient:
        return self._client

    @property
    def tabs(self) -> QTabWidget:
        return self._tabs

    def add_tab(self, widget, label: str) -> None:
        """Add a tab and track it for refresh dispatching."""
        self._tabs.addTab(widget, label)
        self._tab_widgets.append(widget)

    def _on_tab_changed(self, index: int) -> None:
        """Refresh the newly-selected tab if the window is visible."""
        if self.isVisible() and 0 <= index < len(self._tab_widgets):
            tab = self._tab_widgets[index]
            if hasattr(tab, "refresh"):
                tab.refresh()

    def showEvent(self, event) -> None:  # noqa: N802 — Qt override
        """Refresh the active tab whenever the window becomes visible."""
        super().showEvent(event)
        idx = self._tabs.currentIndex()
        if 0 <= idx < len(self._tab_widgets):
            tab = self._tab_widgets[idx]
            if hasattr(tab, "refresh"):
                tab.refresh()

    def closeEvent(self, event) -> None:  # noqa: N802 — Qt override
        """Hide instead of destroying — the tray app owns our lifecycle."""
        event.ignore()
        self.hide()

    def toggle_visibility(self) -> None:
        """Show or hide the dashboard window."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()
