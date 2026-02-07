"""Tests for the compute_icon_state() pure function."""


from sysadmin_tray.models import (
    AlertInfo,
    AlertsResponse,
    IconState,
    ServiceStatus,
    StatusResponse,
    compute_icon_state,
)


def _status(*statuses: tuple[str, str]) -> StatusResponse:
    """Build a StatusResponse from (name, status) tuples."""
    services = [ServiceStatus(name=n, status=s) for n, s in statuses]
    all_ok = all(s.status == "ok" for s in services)
    return StatusResponse(services=services, all_healthy=all_ok)


def _alerts(*severities: str, acknowledged: bool = False) -> AlertsResponse:
    """Build an AlertsResponse from severity strings."""
    alerts = [
        AlertInfo(id=str(i), severity=s, acknowledged=acknowledged)
        for i, s in enumerate(severities)
    ]
    return AlertsResponse(alerts=alerts, count=len(alerts))


class TestComputeIconState:
    """Pure-function icon state computation."""

    # ── Disconnected ─────────────────────────────────────────────────

    def test_disconnected_when_backend_unreachable(self):
        assert compute_icon_state(None, None, False) == IconState.DISCONNECTED

    def test_disconnected_overrides_healthy_data(self):
        status = _status(("pg", "ok"), ("ollama", "ok"))
        assert compute_icon_state(status, None, False) == IconState.DISCONNECTED

    # ── Healthy ──────────────────────────────────────────────────────

    def test_healthy_all_ok_no_alerts(self):
        status = _status(("pg", "ok"), ("ollama", "ok"))
        assert compute_icon_state(status, None, True) == IconState.HEALTHY

    def test_healthy_with_acknowledged_alerts(self):
        status = _status(("pg", "ok"))
        alerts = _alerts("critical", "warning", acknowledged=True)
        assert compute_icon_state(status, alerts, True) == IconState.HEALTHY

    def test_healthy_no_data_but_reachable(self):
        assert compute_icon_state(None, None, True) == IconState.HEALTHY

    # ── Warning ──────────────────────────────────────────────────────

    def test_warning_from_degraded_service(self):
        status = _status(("pg", "ok"), ("ollama", "degraded"))
        assert compute_icon_state(status, None, True) == IconState.WARNING

    def test_warning_from_unacked_warning_alert(self):
        status = _status(("pg", "ok"))
        alerts = _alerts("warning")
        assert compute_icon_state(status, alerts, True) == IconState.WARNING

    # ── Critical ─────────────────────────────────────────────────────

    def test_critical_from_unreachable_service(self):
        status = _status(("pg", "ok"), ("pa", "unreachable"))
        assert compute_icon_state(status, None, True) == IconState.CRITICAL

    def test_critical_from_error_service(self):
        status = _status(("pg", "error"))
        assert compute_icon_state(status, None, True) == IconState.CRITICAL

    def test_critical_from_unacked_critical_alert(self):
        status = _status(("pg", "ok"))
        alerts = _alerts("critical")
        assert compute_icon_state(status, alerts, True) == IconState.CRITICAL

    # ── Priority ─────────────────────────────────────────────────────

    def test_service_critical_overrides_alert_warning(self):
        status = _status(("pg", "unreachable"))
        alerts = _alerts("warning")
        assert compute_icon_state(status, alerts, True) == IconState.CRITICAL

    def test_alert_critical_with_healthy_services(self):
        status = _status(("pg", "ok"), ("ollama", "ok"))
        alerts = _alerts("critical")
        assert compute_icon_state(status, alerts, True) == IconState.CRITICAL
