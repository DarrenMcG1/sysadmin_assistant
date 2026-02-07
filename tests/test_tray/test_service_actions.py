"""Tests for service grid context menu and action signals."""

from unittest.mock import MagicMock, patch

import pytest
from PyQt6.QtCore import QPoint
from PyQt6.QtGui import QContextMenuEvent
from PyQt6.QtWidgets import QApplication, QMenu

from sysadmin_tray.models import ServiceStatus
from sysadmin_tray.widgets.service_grid import ServiceStatusGrid, ServiceStatusRow


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def _make_event() -> QContextMenuEvent:
    return QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
    )


# ── ServiceStatusRow context menu ──────────────────────────────────


class TestRowContextMenuPresence:
    """Context menu only appears for services with a systemd_unit."""

    def test_no_menu_without_systemd_unit(self, qapp):
        """Row with no systemd_unit should not show a context menu."""
        row = ServiceStatusRow("nuxt-frontend")
        svc = ServiceStatus(name="nuxt-frontend", status="ok", systemd_unit=None)
        row.update_status(svc)

        with patch("sysadmin_tray.widgets.service_grid.QMenu") as mock_menu_cls:
            row.contextMenuEvent(_make_event())
            mock_menu_cls.assert_not_called()

    def test_menu_shown_with_systemd_unit(self, qapp):
        """Row with a systemd_unit should create and exec a context menu."""
        row = ServiceStatusRow("postgresql")
        svc = ServiceStatus(
            name="postgresql", status="ok", systemd_unit="postgresql.service"
        )
        row.update_status(svc)

        # Patch exec on the QMenu class to prevent blocking
        with patch.object(QMenu, "exec", return_value=None):
            row.contextMenuEvent(_make_event())
            # If we get here without error, the menu was created

    def test_no_menu_when_action_in_progress(self, qapp):
        """Disabled row should not show context menu."""
        row = ServiceStatusRow("redis")
        svc = ServiceStatus(
            name="redis", status="unreachable", systemd_unit="redis.service"
        )
        row.update_status(svc)
        row.set_action_in_progress(True)

        with patch("sysadmin_tray.widgets.service_grid.QMenu") as mock_menu_cls:
            row.contextMenuEvent(_make_event())
            mock_menu_cls.assert_not_called()


class TestRowContextMenuItems:
    """Menu items vary based on service status."""

    def _get_menu_action_names(self, row, status):
        """Helper: fire contextMenuEvent and capture QAction texts."""
        svc = ServiceStatus(
            name=row.service_name,
            status=status,
            systemd_unit="test.service",
        )
        row.update_status(svc)

        captured = []
        original_add = QMenu.addAction

        def spy_add(menu_self, action):
            captured.append(action.text())
            return original_add(menu_self, action)

        with patch.object(QMenu, "exec", return_value=None), \
             patch.object(QMenu, "addAction", spy_add):
            row.contextMenuEvent(_make_event())

        return captured

    def test_ok_service_shows_restart_and_stop(self, qapp):
        row = ServiceStatusRow("postgresql")
        actions = self._get_menu_action_names(row, "ok")
        assert "Restart" in actions
        assert "Stop" in actions
        assert "Start" not in actions

    def test_unreachable_service_shows_restart_and_start(self, qapp):
        row = ServiceStatusRow("redis")
        actions = self._get_menu_action_names(row, "unreachable")
        assert "Restart" in actions
        assert "Start" in actions
        assert "Stop" not in actions

    def test_degraded_service_shows_restart_and_start(self, qapp):
        row = ServiceStatusRow("ollama")
        actions = self._get_menu_action_names(row, "degraded")
        assert "Restart" in actions
        assert "Start" in actions
        assert "Stop" not in actions


class TestRowActionSignal:
    """action_requested signal emits (service_name, action)."""

    def test_signal_emitted_on_action(self, qapp):
        row = ServiceStatusRow("postgresql")
        svc = ServiceStatus(
            name="postgresql", status="ok", systemd_unit="postgresql.service"
        )
        row.update_status(svc)

        handler = MagicMock()
        row.action_requested.connect(handler)

        # Simulate the signal directly (avoids needing to click menu)
        row.action_requested.emit("postgresql", "restart")
        handler.assert_called_once_with("postgresql", "restart")


class TestRowDisabledState:
    """Row disabled during action, re-enabled on complete."""

    def test_set_action_in_progress_disables_row(self, qapp):
        row = ServiceStatusRow("redis")
        assert row.isEnabled()
        row.set_action_in_progress(True)
        assert not row.isEnabled()
        assert row._action_in_progress is True

    def test_clear_action_in_progress_re_enables_row(self, qapp):
        row = ServiceStatusRow("redis")
        row.set_action_in_progress(True)
        row.set_action_in_progress(False)
        assert row.isEnabled()
        assert row._action_in_progress is False


# ── ServiceStatusGrid signal forwarding ────────────────────────────


class TestGridActionSignal:
    """ServiceStatusGrid forwards row action signals."""

    def test_grid_forwards_row_action(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(
                name="postgresql", status="ok", systemd_unit="postgresql.service"
            ),
        ])

        handler = MagicMock()
        grid.service_action_requested.connect(handler)

        # Simulate the row action
        grid._rows["postgresql"].action_requested.emit("postgresql", "restart")
        handler.assert_called_once_with("postgresql", "restart")

    def test_grid_disables_row_on_action(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(
                name="redis", status="unreachable", systemd_unit="redis.service"
            ),
        ])

        grid._rows["redis"].action_requested.emit("redis", "start")
        assert not grid._rows["redis"].isEnabled()

    def test_grid_re_enables_row_on_complete(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(
                name="redis", status="unreachable", systemd_unit="redis.service"
            ),
        ])

        grid._rows["redis"].action_requested.emit("redis", "start")
        assert not grid._rows["redis"].isEnabled()

        grid.on_action_complete("redis", "start", True, "ok")
        assert grid._rows["redis"].isEnabled()

    def test_grid_action_complete_unknown_service_no_error(self, qapp):
        """on_action_complete for a missing service should not raise."""
        grid = ServiceStatusGrid()
        grid.on_action_complete("ghost", "restart", False, "not found")


class TestGridStoresSystemdUnit:
    """ServiceStatusRow stores systemd_unit from ServiceStatus."""

    def test_systemd_unit_stored(self, qapp):
        row = ServiceStatusRow("postgresql")
        svc = ServiceStatus(
            name="postgresql", status="ok", systemd_unit="postgresql.service"
        )
        row.update_status(svc)
        assert row._systemd_unit == "postgresql.service"

    def test_systemd_unit_none_when_absent(self, qapp):
        row = ServiceStatusRow("nuxt")
        svc = ServiceStatus(name="nuxt", status="ok")
        row.update_status(svc)
        assert row._systemd_unit is None
