"""Tests for /api/units/* and the Service Discovery agent (Session 26)."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.units.agent import ALERT_TITLE, ServiceDiscoveryAgent
from sysadmin.units.models import UnitAudit
from sysadmin.units.scan import HOST, ORPHANED, UNMONITORED

SCANNED_AT = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)


def _audit(**overrides) -> UnitAudit:
    findings = {
        "units_scanned": 24,
        "units_excluded": 6,
        "monitored_count": 12,
        "timers_folded": 8,
        "excluded_units": ["autovt@.service"],
        ORPHANED: [
            {
                "unit": "garmin-sync.service",
                "scope": "user",
                "category": ORPHANED,
                "path": "/home/gaddi/.config/systemd/user/garmin-sync.service",
                "description": "Garmin Watch Health Data Sync",
                "dead_path": "/home/gaddi/projects/PersonalAssistant",
                "monitor_unit": "garmin-sync.service",
                "reason": "WorkingDirectory does not exist",
            }
        ],
        UNMONITORED: [
            {
                "unit": "alfred-worker.service",
                "scope": "user",
                "category": UNMONITORED,
                "path": "/home/gaddi/.config/systemd/user/alfred-worker.service",
                "project": "Alfred",
                "project_path": "/home/gaddi/projects/Alfred",
                "matched_by": "path",
                "monitor_unit": "alfred-worker.service",
                "reason": "nothing monitors it",
            }
        ],
        HOST: [
            {
                "unit": "deadlock-api-ingest.service",
                "scope": scope,
                "category": HOST,
                "path": f"/{scope}/deadlock-api-ingest.service",
                "monitor_unit": "deadlock-api-ingest.service",
                "reason": "maps to no project",
            }
            for scope in ("user", "system")
        ],
    }
    audit = UnitAudit(
        user_unit_dir="/home/gaddi/.config/systemd/user",
        system_unit_dir="/etc/systemd/system",
        units_scanned=24,
        units_excluded=6,
        monitored_count=12,
        timers_folded=8,
        orphaned_count=1,
        unmonitored_count=1,
        host_count=2,
        findings=findings,
    )
    audit.scanned_at = SCANNED_AT
    for key, value in overrides.items():
        setattr(audit, key, value)
    return audit


def _return_audit(mock_session, audit):
    result = MagicMock()
    result.scalar_one_or_none.return_value = audit
    mock_session.execute = AsyncMock(return_value=result)


# ── GET /api/units/status ────────────────────────────────────────────


async def test_status_404s_before_the_first_sweep(test_client, mock_session):
    """404, not an empty 200: 'no data yet' and 'nothing to report' are
    different answers and a consumer must tell them apart."""
    _return_audit(mock_session, None)
    response = await test_client.get("/api/units/status")
    assert response.status_code == 404
    assert "has not run" in response.json()["detail"]


async def test_status_returns_summary_and_findings(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/status")).json()

    assert body["summary"] == {
        "units_scanned": 24,
        "units_excluded": 6,
        "monitored": 12,
        "timers_folded": 8,
        "orphaned": 1,
        "unmonitored": 1,
        "host": 2,
    }
    assert body["count"] == 4
    assert body["scanned_at"].startswith("2026-08-07T09:00")


async def test_status_summary_arithmetic_sums(test_client, mock_session):
    _return_audit(mock_session, _audit())
    s = (await test_client.get("/api/units/status")).json()["summary"]
    assert (
        s["monitored"] + s["timers_folded"] + s["orphaned"]
        + s["unmonitored"] + s["host"] == s["units_scanned"]
    )


async def test_status_orders_orphans_first(test_client, mock_session):
    _return_audit(mock_session, _audit())
    findings = (await test_client.get("/api/units/status")).json()["findings"]
    assert findings[0]["category"] == ORPHANED


async def test_status_filters_by_category(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/status?category=host")).json()
    assert body["count"] == 2
    assert {f["category"] for f in body["findings"]} == {HOST}


async def test_status_rejects_an_unknown_category(test_client, mock_session):
    _return_audit(mock_session, _audit())
    assert (await test_client.get("/api/units/status?category=nope")).status_code == 400


async def test_status_names_units_installed_in_both_scopes(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/status")).json()
    assert body["duplicate_units"] == ["deadlock-api-ingest.service"]


async def test_duplicate_units_survive_a_category_filter(test_client, mock_session):
    """The pair is a property of the sweep, not of the filtered view."""
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/status?category=orphaned")).json()
    assert body["duplicate_units"] == ["deadlock-api-ingest.service"]


async def test_status_tolerates_a_malformed_findings_blob(test_client, mock_session):
    _return_audit(mock_session, _audit(findings={ORPHANED: ["not-a-dict", None]}))
    body = (await test_client.get("/api/units/status")).json()
    assert body["count"] == 0


# ── GET /api/units/actions ───────────────────────────────────────────


async def test_actions_404s_before_the_first_sweep(test_client, mock_session):
    _return_audit(mock_session, None)
    assert (await test_client.get("/api/units/actions")).status_code == 404


async def test_actions_rank_orphans_first(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions")).json()
    assert body["recommendations"][0]["kind"] == "orphan"
    assert body["recommendations"][0]["severity"] == "risk"
    assert body["total_available"] == 4


async def test_actions_report_what_the_limit_hid(test_client, mock_session):
    """Without dropped_by_kind a saturated list reads as 'that is all
    there is' — the /api/projects/actions failure from Session 28."""
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions?limit=1")).json()
    assert body["count"] == 1
    assert body["total_available"] == 4
    assert body["dropped_by_kind"] == {"unmonitored": 1, "host": 2}


async def test_actions_report_nothing_dropped_when_all_fit(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions?limit=50")).json()
    assert body["dropped_by_kind"] == {}


async def test_actions_filter_by_kind(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions?kind=host")).json()
    assert body["total_available"] == 2
    assert {r["kind"] for r in body["recommendations"]} == {"host"}


async def test_actions_reject_an_unknown_kind(test_client, mock_session):
    _return_audit(mock_session, _audit())
    assert (await test_client.get("/api/units/actions?kind=nope")).status_code == 400


async def test_actions_carry_a_pasteable_snippet(test_client, mock_session):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions?kind=host")).json()
    rec = body["recommendations"][0]
    assert rec["snippet_target"] == "config.yaml"
    assert "systemd_unit: deadlock-api-ingest.service" in rec["snippet"]


async def test_orphan_action_carries_a_removal_command_not_a_snippet(
    test_client, mock_session
):
    _return_audit(mock_session, _audit())
    body = (await test_client.get("/api/units/actions?kind=orphan")).json()
    rec = body["recommendations"][0]
    assert rec["snippet"] == "" and rec["snippet_target"] is None
    assert "systemctl --user disable --now garmin-sync.service" in rec["action"]


async def test_actions_are_read_only(test_app):
    """No executor here and there will not be one — the fix is an edit to
    a hand-curated file, or a systemctl removal."""
    paths = {r.path: getattr(r, "methods", set()) for r in test_app.routes}
    unit_routes = {p: m for p, m in paths.items() if p.startswith("/api/units")}
    assert unit_routes
    assert all(m <= {"GET", "HEAD"} for m in unit_routes.values())


# ── The agent ────────────────────────────────────────────────────────


def _scan(orphaned=0, unmonitored=0, host=0, monitored=12, scanned=38):
    counts = {ORPHANED: orphaned, UNMONITORED: unmonitored, HOST: host}
    findings = [
        SimpleNamespace(unit=f"{category}-{i}.service", category=category)
        for category, n in counts.items()
        for i in range(n)
    ]
    return SimpleNamespace(
        findings=findings,
        count=counts.get,
        actionable=len(findings),
        monitored_count=monitored,
        units_scanned=scanned,
    )


def _no_existing_alert(session):
    result = MagicMock()
    result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result)


def _existing_alert(session, actionable):
    alert = SimpleNamespace(details={"actionable": actionable})
    result = MagicMock()
    result.scalars.return_value.first.return_value = alert
    session.execute = AsyncMock(return_value=result)


@pytest.fixture
def agent():
    a = ServiceDiscoveryAgent()
    a.raise_alert = AsyncMock()
    a.resolve_alerts = AsyncMock(return_value=0)
    return a


async def test_below_threshold_resolves_and_does_not_alert(agent, mock_session):
    raised = await agent._maintain_alert(mock_session, 3, 5, _scan(orphaned=3))
    assert raised == 0
    agent.raise_alert.assert_not_awaited()
    agent.resolve_alerts.assert_awaited_once_with(mock_session, ALERT_TITLE)


async def test_threshold_of_zero_disables_alerting(agent, mock_session):
    """The Session 28 posture: record findings, never alert."""
    assert await agent._maintain_alert(mock_session, 99, 0, _scan(orphaned=99)) == 0
    agent.raise_alert.assert_not_awaited()


async def test_first_time_over_threshold_raises_one_rolled_up_alert(
    agent, mock_session
):
    _no_existing_alert(mock_session)
    raised = await agent._maintain_alert(
        mock_session, 18, 5, _scan(orphaned=11, host=7)
    )
    assert raised == 1
    agent.raise_alert.assert_awaited_once()
    kwargs = agent.raise_alert.await_args.kwargs
    assert kwargs["severity"] == "warning"
    assert "18 findings" in kwargs["title"]
    assert kwargs["details"]["actionable"] == 18


async def test_unchanged_count_does_not_re_raise(agent, mock_session):
    """raise_alert inserts unconditionally, so re-raising every sweep
    would add four rows a day — SNAG-AGENT-002 in a new costume."""
    _existing_alert(mock_session, 18)
    raised = await agent._maintain_alert(
        mock_session, 18, 5, _scan(orphaned=11, host=7)
    )
    assert raised == 0
    agent.raise_alert.assert_not_awaited()


async def test_a_changed_count_replaces_the_alert(agent, mock_session):
    _existing_alert(mock_session, 18)
    raised = await agent._maintain_alert(
        mock_session, 19, 5, _scan(orphaned=12, host=7)
    )
    assert raised == 1
    agent.resolve_alerts.assert_awaited_once_with(mock_session, ALERT_TITLE)
    agent.raise_alert.assert_awaited_once()


async def test_alert_message_names_each_category_and_the_endpoint(agent):
    message = agent._alert_message(_scan(orphaned=11, unmonitored=2, host=7))
    assert "11 orphaned" in message
    assert "2 unmonitored" in message
    assert "7 host units" in message
    assert "12 of 38" in message
    assert "/api/units/actions" in message


async def test_alert_details_cap_the_examples(agent):
    details = agent._alert_details(_scan(orphaned=20), 20)
    assert len(details["examples"]) == 5


# ── Project references ───────────────────────────────────────────────


def test_project_refs_include_managed_projects_outside_the_scan_root(mock_config):
    """A projects.yaml entry pointing outside projects_root still owns
    units; without it those units would be misreported as orphans."""
    from sysadmin.core.config import ManagedProject, ProjectsConfig

    mock_config.projects = ProjectsConfig(
        projects=[ManagedProject(name="elsewhere", path="/opt/elsewhere")]
    )
    mock_config.agents.project_organiser.projects_root = "/definitely/not/here"

    with patch("pathlib.Path.exists", return_value=True), patch(
        "sysadmin.units.agent.discover_projects", return_value=[]
    ):
        refs = ServiceDiscoveryAgent._project_refs(mock_config)

    assert [(r.name, r.path) for r in refs] == [("elsewhere", "/opt/elsewhere")]


def test_project_refs_are_empty_when_the_root_is_missing(mock_config):
    mock_config.agents.project_organiser.projects_root = "/definitely/not/here"
    assert ServiceDiscoveryAgent._project_refs(mock_config) == []


# ── Self-monitoring ──────────────────────────────────────────────────


def test_the_agent_is_self_monitored():
    """A new agent that is not in AGENT_NAMES runs completely unwatched —
    the monitoring service failing to monitor its own newest agent.  The
    job_id must match main.py or the stall window is computed against a
    schedule that does not exist."""
    from sysadmin.core.config import AppConfig
    from sysadmin.monitor.self_monitor import AGENT_NAMES, agent_schedules

    assert "service_discovery" in AGENT_NAMES
    schedule = agent_schedules(AppConfig())["service_discovery"]
    assert schedule.job_id == "service_discovery_scan"
    assert schedule.interval_seconds == 6 * 3600


def test_the_agent_name_is_accepted_by_the_alerts_constraint():
    """sysadmin.alerts has a CHECK constraint enumerating agents; the
    first live run was rejected by it after the scan had succeeded.
    Migration 007 widened it, and AGENT_NAMES mirrors it."""
    import importlib.util
    from pathlib import Path

    from sysadmin.monitor.self_monitor import AGENT_NAMES

    # alembic/versions is not a package — load the revision by path.
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "007_allow_service_discovery_agent.py"
    )
    spec = importlib.util.spec_from_file_location("rev_007", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert set(module.AGENTS) == set(AGENT_NAMES)
