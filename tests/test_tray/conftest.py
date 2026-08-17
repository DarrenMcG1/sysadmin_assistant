"""Shared fixtures for the tray widget tests.

Forces the offscreen Qt platform plugin *before* any QApplication is
created (pytest imports conftest first), so widget and paint tests run
identically on a developer's desktop and in CI, which sets the same
variable in the workflow env.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtCore import QObject, pyqtSignal  # noqa: E402
from PyQt6.QtGui import QImage  # noqa: E402
from PyQt6.QtWidgets import QApplication, QWidget  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    """A single QApplication shared by every widget test."""
    app = QApplication.instance() or QApplication([])
    yield app


def render_offscreen(widget: QWidget, width: int = 480, height: int = 200) -> QImage:
    """Force a widget's ``paintEvent`` to run and return the result.

    ``QWidget.render`` paints into an image without ever mapping a
    window, which is what makes the QPainter charts testable headless.
    Any exception raised inside ``paintEvent`` propagates here.
    """
    widget.resize(width, height)
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    image.fill(0)
    widget.render(image)
    return image


class FakeClient(QObject):
    """Stand-in for :class:`sysadmin_tray.client.ApiClient`.

    Exposes the same signals the dashboard tabs connect to and records
    every request the tab makes, so a tab can be driven end-to-end
    without a worker thread, a socket, or a running backend.
    """

    status_updated = pyqtSignal(object)
    resources_updated = pyqtSignal(object)
    alerts_updated = pyqtSignal(object)
    connection_lost = pyqtSignal()
    connection_restored = pyqtSignal()
    scan_complete = pyqtSignal(bool, str)
    service_action_complete = pyqtSignal(str, str, bool, str)
    service_detail_updated = pyqtSignal(str, object)
    resource_history_updated = pyqtSignal(object)
    managed_projects_updated = pyqtSignal(object)
    project_overview_updated = pyqtSignal(object)
    project_detail_updated = pyqtSignal(str, object)
    file_status_updated = pyqtSignal(object)
    file_duplicates_updated = pyqtSignal(object)
    file_large_updated = pyqtSignal(object)
    file_misplaced_updated = pyqtSignal(object)
    file_trends_updated = pyqtSignal(object)
    file_fetch_failed = pyqtSignal(str, str)
    file_scan_triggered = pyqtSignal(bool, str)
    stale_caches_cleaned = pyqtSignal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple] = []

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, *args))

    def called(self, name: str) -> int:
        """How many times a request method was invoked."""
        return sum(1 for call in self.calls if call[0] == name)

    # ── Request methods ──────────────────────────────────────────────

    def request_file_status(self) -> None:
        self._record("request_file_status")

    def request_file_duplicates(self) -> None:
        self._record("request_file_duplicates")

    def request_file_large(self) -> None:
        self._record("request_file_large")

    def request_file_misplaced(self) -> None:
        self._record("request_file_misplaced")

    def request_file_trends(self) -> None:
        self._record("request_file_trends")

    def request_resource_history(self, hours: int = 24) -> None:
        self._record("request_resource_history", hours)

    def trigger_file_scan(self) -> None:
        self._record("trigger_file_scan")

    def clean_stale_caches(self) -> None:
        self._record("clean_stale_caches")

    def request_managed_projects(self) -> None:
        self._record("request_managed_projects")

    def request_project_overview(self) -> None:
        self._record("request_project_overview")

    def request_project_detail(self, name: str, limit: int = 30) -> None:
        self._record("request_project_detail", name, limit)

    def trigger_scan(self) -> None:
        self._record("trigger_scan")

    def request_status(self) -> None:
        self._record("request_status")

    def request_service_details(self, name: str) -> None:
        self._record("request_service_details", name)

    def trigger_service_action(self, name: str, action: str) -> None:
        self._record("trigger_service_action", name, action)


@pytest.fixture
def fake_client(qapp):
    """A fresh :class:`FakeClient` per test."""
    return FakeClient()
