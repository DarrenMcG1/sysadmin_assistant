"""Tests for the ServiceStatusGrid and ServiceStatusRow widgets."""

import pytest
from PyQt6.QtWidgets import QApplication

from sysadmin_tray.models import ServiceStatus
from sysadmin_tray.widgets.service_grid import (
    _STATUS_COLOURS,
    ServiceStatusGrid,
    ServiceStatusRow,
)


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


class TestServiceStatusRow:
    """ServiceStatusRow rendering tests."""

    def test_initial_state(self, qapp):
        row = ServiceStatusRow("postgresql")
        assert row.service_name == "postgresql"
        assert row._name_label.text() == "postgresql"
        assert row._status_label.text() == "—"

    def test_update_ok_status(self, qapp):
        row = ServiceStatusRow("postgresql")
        svc = ServiceStatus(name="postgresql", status="ok", response_time_ms=12.0)
        row.update_status(svc)
        assert row._status_label.text() == "ok"
        assert row._time_label.text() == "12ms"
        assert _STATUS_COLOURS["ok"] in row._dot.styleSheet()

    def test_update_unreachable_status(self, qapp):
        row = ServiceStatusRow("redis")
        svc = ServiceStatus(name="redis", status="unreachable")
        row.update_status(svc)
        assert row._status_label.text() == "unreachable"
        assert row._time_label.text() == "—"
        assert _STATUS_COLOURS["unreachable"] in row._dot.styleSheet()

    def test_update_degraded_status(self, qapp):
        row = ServiceStatusRow("ollama")
        svc = ServiceStatus(name="ollama", status="degraded", response_time_ms=450.0)
        row.update_status(svc)
        assert row._status_label.text() == "degraded"
        assert row._time_label.text() == "450ms"
        assert _STATUS_COLOURS["degraded"] in row._dot.styleSheet()

    def test_update_error_status(self, qapp):
        row = ServiceStatusRow("pg")
        svc = ServiceStatus(name="pg", status="error")
        row.update_status(svc)
        assert row._status_label.text() == "error"
        assert _STATUS_COLOURS["error"] in row._dot.styleSheet()

    def test_unknown_status_uses_default_colour(self, qapp):
        row = ServiceStatusRow("mystery")
        svc = ServiceStatus(name="mystery", status="banana")
        row.update_status(svc)
        assert row._status_label.text() == "banana"
        # Default grey colour
        assert "#95a5a6" in row._dot.styleSheet()


class TestServiceStatusGrid:
    """ServiceStatusGrid dynamic row management tests."""

    def test_initial_empty(self, qapp):
        grid = ServiceStatusGrid()
        assert len(grid._rows) == 0

    def test_adds_rows_on_first_update(self, qapp):
        grid = ServiceStatusGrid()
        services = [
            ServiceStatus(name="postgresql", status="ok", response_time_ms=5.0),
            ServiceStatus(name="redis", status="ok", response_time_ms=2.0),
        ]
        grid.update_services(services)
        assert len(grid._rows) == 2
        assert "postgresql" in grid._rows
        assert "redis" in grid._rows

    def test_reuses_rows_on_subsequent_updates(self, qapp):
        grid = ServiceStatusGrid()
        services = [ServiceStatus(name="pg", status="ok")]
        grid.update_services(services)

        row_ref = grid._rows["pg"]
        # Update again — same row object should be reused
        services = [ServiceStatus(name="pg", status="degraded")]
        grid.update_services(services)
        assert grid._rows["pg"] is row_ref
        assert grid._rows["pg"]._status_label.text() == "degraded"

    def test_removes_disappeared_services(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(name="pg", status="ok"),
            ServiceStatus(name="redis", status="ok"),
        ])
        assert len(grid._rows) == 2

        # Redis disappears
        grid.update_services([
            ServiceStatus(name="pg", status="ok"),
        ])
        assert len(grid._rows) == 1
        assert "pg" in grid._rows
        assert "redis" not in grid._rows

    def test_adds_new_service_on_update(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([ServiceStatus(name="pg", status="ok")])
        assert len(grid._rows) == 1

        # Ollama appears
        grid.update_services([
            ServiceStatus(name="pg", status="ok"),
            ServiceStatus(name="ollama", status="ok"),
        ])
        assert len(grid._rows) == 2
        assert "ollama" in grid._rows

    def test_empty_update_clears_all_rows(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(name="pg", status="ok"),
            ServiceStatus(name="redis", status="ok"),
        ])
        assert len(grid._rows) == 2

        grid.update_services([])
        assert len(grid._rows) == 0

    def test_status_values_propagate_to_rows(self, qapp):
        grid = ServiceStatusGrid()
        grid.update_services([
            ServiceStatus(name="pg", status="ok", response_time_ms=3.0),
            ServiceStatus(name="redis", status="unreachable"),
        ])
        assert grid._rows["pg"]._status_label.text() == "ok"
        assert grid._rows["pg"]._time_label.text() == "3ms"
        assert grid._rows["redis"]._status_label.text() == "unreachable"
        assert grid._rows["redis"]._time_label.text() == "—"
