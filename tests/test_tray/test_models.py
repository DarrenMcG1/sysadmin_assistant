"""Tests for API response model parsing."""

import pytest

from sysadmin_tray.models import (
    AlertsResponse,
    ResourceResponse,
    StatusResponse,
)

# ── Sample API responses (matching actual backend shapes) ────────────

SAMPLE_STATUS = {
    "services": [
        {
            "name": "postgresql",
            "status": "ok",
            "response_time_ms": 12.5,
            "details": None,
            "checked_at": "2026-02-07T10:00:00+00:00",
        },
        {
            "name": "ollama",
            "status": "ok",
            "response_time_ms": 45.2,
            "details": None,
            "checked_at": "2026-02-07T10:00:00+00:00",
        },
        {
            "name": "personal-assistant",
            "status": "unreachable",
            "response_time_ms": None,
            "details": "Connection refused",
            "checked_at": "2026-02-07T10:00:00+00:00",
        },
    ],
    "all_healthy": False,
}

SAMPLE_RESOURCES = {
    "cpu_percent": 72.3,
    "ram": {"used_mb": 6656, "total_mb": 16384, "percent": 40.6},
    "swap": {"used_mb": 128, "total_mb": 8192},
    "disk": {
        "/": {"total_gb": 475.0, "used_gb": 412.0, "free_gb": 63.0, "percent": 86.7},
        "/boot": {"total_gb": 0.5, "used_gb": 0.1, "free_gb": 0.4, "percent": 20.0},
    },
    "gpu": {},
    "load_avg": {"1m": 2.1, "5m": 1.8, "15m": 1.5},
    "recorded_at": "2026-02-07T10:00:00+00:00",
}

SAMPLE_ALERTS = {
    "alerts": [
        {
            "id": "abc-123",
            "agent": "sysadmin",
            "severity": "critical",
            "title": "Disk usage critical on /",
            "message": "Disk at 91%",
            "details": {},
            "acknowledged": False,
            "resolved": False,
            "created_at": "2026-02-07T09:55:00+00:00",
        },
        {
            "id": "def-456",
            "agent": "sysadmin",
            "severity": "warning",
            "title": "High RAM usage",
            "message": "RAM at 87%",
            "details": {},
            "acknowledged": True,
            "resolved": False,
            "created_at": "2026-02-07T09:50:00+00:00",
        },
        {
            "id": "ghi-789",
            "agent": "log_aggregator",
            "severity": "info",
            "title": "New log summary available",
            "message": None,
            "details": {},
            "acknowledged": False,
            "resolved": False,
            "created_at": "2026-02-07T09:45:00+00:00",
        },
    ],
    "count": 3,
}


class TestStatusResponse:
    def test_parses_services(self):
        status = StatusResponse.from_dict(SAMPLE_STATUS)
        assert len(status.services) == 3
        assert status.all_healthy is False

    def test_service_fields(self):
        status = StatusResponse.from_dict(SAMPLE_STATUS)
        pg = status.services[0]
        assert pg.name == "postgresql"
        assert pg.status == "ok"
        assert pg.response_time_ms == 12.5

    def test_unreachable_service(self):
        status = StatusResponse.from_dict(SAMPLE_STATUS)
        pa = status.services[2]
        assert pa.status == "unreachable"
        assert pa.details == "Connection refused"

    def test_empty_response(self):
        status = StatusResponse.from_dict({"services": [], "all_healthy": True})
        assert len(status.services) == 0
        assert status.all_healthy is True


class TestResourceResponse:
    def test_parses_cpu_ram(self):
        res = ResourceResponse.from_dict(SAMPLE_RESOURCES)
        assert res.cpu_percent == pytest.approx(72.3)
        assert res.ram.used_mb == 6656
        assert res.ram.total_mb == 16384
        assert res.ram.percent == pytest.approx(40.6)

    def test_parses_disk_partitions(self):
        res = ResourceResponse.from_dict(SAMPLE_RESOURCES)
        assert len(res.disk) == 2
        # Sorted by mount — "/" comes before "/boot"
        assert res.disk[0].mount == "/"
        assert res.disk[0].percent == pytest.approx(86.7)
        assert res.disk[1].mount == "/boot"

    def test_no_data_yet(self):
        res = ResourceResponse.from_dict({"message": "No resource data yet"})
        assert res.cpu_percent == 0.0
        assert res.ram.total_mb == 0
        assert len(res.disk) == 0

    def test_null_cpu(self):
        data = {**SAMPLE_RESOURCES, "cpu_percent": None}
        res = ResourceResponse.from_dict(data)
        assert res.cpu_percent == 0.0


class TestAlertsResponse:
    def test_parses_alerts(self):
        alerts = AlertsResponse.from_dict(SAMPLE_ALERTS)
        assert alerts.count == 3
        assert len(alerts.alerts) == 3

    def test_severity_counts(self):
        alerts = AlertsResponse.from_dict(SAMPLE_ALERTS)
        assert alerts.critical_count == 1
        assert alerts.warning_count == 1
        assert alerts.info_count == 1

    def test_alert_fields(self):
        alerts = AlertsResponse.from_dict(SAMPLE_ALERTS)
        crit = alerts.alerts[0]
        assert crit.severity == "critical"
        assert crit.acknowledged is False
        assert crit.title == "Disk usage critical on /"

    def test_empty_alerts(self):
        alerts = AlertsResponse.from_dict({"alerts": [], "count": 0})
        assert alerts.count == 0
        assert alerts.critical_count == 0
