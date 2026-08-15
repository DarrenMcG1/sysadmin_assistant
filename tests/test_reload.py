"""The reload path — SNAG-UNITS-005's durable half.

The test that earns its place is :func:`test_every_lifespan_config_read_is_classified`.
:data:`sysadmin.reload.RESTART_ONLY` is a hand-written list, and a
hand-written classification that nothing checks is the SNAG-CFG-001 shape:
parsed, plausible, and quietly wrong. This one decides what an operator is
*told* about their own edit, so it rots in the direction nobody notices —
a new scheduled job reading a new config field would silently be reported
as live when it is not.
"""

import ast
from pathlib import Path

import pytest
import yaml

from sysadmin.core.config import AppConfig, get_config, set_config
from sysadmin.core.contracts import ReloadResponse
from sysadmin.monitor import services as services_module
from sysadmin.monitor.services import get_services
from sysadmin.reload import (
    LIVE_AT_STARTUP,
    RESTART_ONLY,
    ReloadReport,
    changed_restart_only,
    diff_services,
    reload_configuration,
)

MAIN_PY = Path(__file__).resolve().parents[1] / "sysadmin" / "main.py"


# ── the classification guard ─────────────────────────────────────────


def _lifespan_node() -> ast.AsyncFunctionDef:
    tree = ast.parse(MAIN_PY.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "lifespan":
            return node
    raise AssertionError("main.py has no `lifespan` — adjust this test")


def _chain(node: ast.AST) -> list[str] | None:
    """``a.b.c`` -> ``['a', 'b', 'c']``; None for anything else."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append(node.id)
    return list(reversed(parts))


def lifespan_config_paths() -> set[str]:
    """Dotted config paths the lifespan reads, from its source.

    Only *maximal* chains count: ``config.agents`` appearing as the right
    hand side of ``agents_config = config.agents`` is an alias, not a read,
    and reporting it would demand that the whole ``agents`` subtree be
    classified — which is the opposite of the point, since the thresholds
    under it are re-read every run.
    """
    node = _lifespan_node()

    # name -> dotted prefix. Seeded with the config object itself.
    aliases = {"config": ""}
    alias_rhs: set[int] = set()
    for stmt in ast.walk(node):
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        chain = _chain(stmt.value)
        if not isinstance(target, ast.Name) or chain is None:
            continue
        if chain[0] in aliases:
            prefix = aliases[chain[0]]
            rest = ".".join(chain[1:])
            aliases[target.id] = f"{prefix}.{rest}" if prefix else rest
            alias_rhs.add(id(stmt.value))

    # Attribute nodes that are somebody else's `.value` are not maximal.
    inner = {
        id(sub.value) for sub in ast.walk(node) if isinstance(sub, ast.Attribute)
    }

    paths: set[str] = set()
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Attribute) or id(sub) in inner:
            continue
        if id(sub) in alias_rhs:
            continue
        chain = _chain(sub)
        if chain is None or chain[0] not in aliases:
            continue
        prefix = aliases[chain[0]]
        rest = ".".join(chain[1:])
        paths.add(f"{prefix}.{rest}" if prefix else rest)
    return paths


def test_lifespan_reads_are_actually_found():
    """Guard the guard: a parser that finds nothing passes vacuously."""
    paths = lifespan_config_paths()
    assert "schedules.briefing_hour" in paths
    assert "agents.log_aggregator.poll_interval_seconds" in paths
    assert len(paths) >= 15, sorted(paths)


def test_every_lifespan_config_read_is_classified():
    """Nothing read once at startup may go unclassified.

    A field the lifespan reads is either restart-only or explicitly
    recorded as read again later. Neither list is allowed to simply omit
    it — an omission means ``requires_restart`` stays silent about a field
    the running process is not obeying, which is the exact failure the
    report exists to prevent.
    """
    restart_prefixes = tuple(path for path, _ in RESTART_ONLY)
    live = {path for path, _ in LIVE_AT_STARTUP}
    unclassified = sorted(
        path
        for path in lifespan_config_paths()
        if path not in live
        and not any(path == p or path.startswith(f"{p}.") for p in restart_prefixes)
    )
    assert not unclassified, (
        "main.py's lifespan reads config fields that sysadmin/reload.py "
        "classifies neither way:\n  " + "\n  ".join(unclassified)
    )


def test_classified_paths_exist_on_the_model():
    """A renamed field must break this list rather than drop out of it."""
    dumped = AppConfig().model_dump(mode="json")
    for path, reason in RESTART_ONLY + LIVE_AT_STARTUP:
        node = dumped
        for part in path.split("."):
            assert isinstance(node, dict) and part in node, (
                f"{path} does not resolve against AppConfig"
            )
            node = node[part]
        assert reason, f"{path} carries no reason"


def test_no_path_is_classified_both_ways():
    restart = {path for path, _ in RESTART_ONLY}
    live = {path for path, _ in LIVE_AT_STARTUP}
    assert not restart & live


# ── the diff ─────────────────────────────────────────────────────────


def test_restart_only_diff_names_leaves_not_prefixes():
    """`schedules` changed is not an answer — an operator still has to grep."""
    old = AppConfig()
    new = AppConfig()
    new.schedules.briefing_hour = 7
    assert changed_restart_only(old, new) == ["schedules.briefing_hour"]


def test_threshold_change_needs_no_restart():
    """The half the reload genuinely delivers.

    Every ``_execute`` calls ``get_config()`` at its top, so a threshold is
    live the moment the reload returns. Reporting it as restart-only would
    be wrong in the direction nobody checks — the operator restarts anyway
    and the reload has bought nothing.
    """
    old = AppConfig()
    new = AppConfig()
    new.agents.sysadmin.thresholds.disk_warning_percent = 55
    assert changed_restart_only(old, new) == []


def test_identical_configs_report_nothing():
    assert changed_restart_only(AppConfig(), AppConfig()) == []


def test_service_diff_splits_added_removed_changed():
    from sysadmin.monitor.services import ServiceEntry, ServicesFile

    old = ServicesFile(schema=1, services=[
        ServiceEntry.model_validate({"name": "a", "kind": "http", "url": "http://x/1"}),
        ServiceEntry.model_validate({"name": "b", "kind": "http", "url": "http://x/2"}),
    ])
    new = ServicesFile(schema=1, services=[
        ServiceEntry.model_validate({"name": "a", "kind": "http", "url": "http://x/9"}),
        ServiceEntry.model_validate({"name": "c", "kind": "http", "url": "http://x/3"}),
    ])
    assert diff_services(old, new) == (["c"], ["b"], ["a"])


# ── installing, and refusing to ──────────────────────────────────────


@pytest.fixture
def files(tmp_path):
    """A valid config.yaml + services.yaml pair on disk."""
    projects = tmp_path / "projects"
    projects.mkdir()
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump({
        "service": {"name": "sysadmin-service", "port": 8500},
        "agents": {"project_organiser": {"projects_root": str(projects)}},
    }))
    services = tmp_path / "services.yaml"
    services.write_text(yaml.safe_dump({
        "schema": 1,
        "services": [
            {"name": "alpha", "kind": "http", "url": "http://localhost:1/health"},
        ],
    }))
    return config, services


@pytest.fixture
def restore_singletons():
    """Both singletons are process-wide; put them back afterwards."""
    saved_config = get_config()
    saved_services = services_module._services
    yield
    set_config(saved_config)
    services_module._services = saved_services


def _reload(files, prunable=()):
    config, services = files
    return reload_configuration(
        config_path=config, services_path=services, prunable=prunable
    )


def test_reload_installs_the_new_services(files, restore_singletons):
    report = _reload(files)
    assert report.ok and report.error is None
    assert [s.name for s in get_services().services] == ["alpha"]
    assert report.services_total == 1
    assert "alpha" in report.services_added


def test_invalid_services_installs_nothing(files, restore_singletons):
    config, services = files
    services.write_text("services: [{name: alpha, kind: nonsense}]")
    before_config = get_config()
    before_services = get_services()

    report = reload_configuration(config_path=config, services_path=services)

    assert not report.ok
    assert "services.yaml" in (report.error or "")
    assert get_services() is before_services
    assert get_config() is before_config


def test_invalid_config_installs_nothing_including_valid_services(
    files, restore_singletons
):
    """Rule 1, and the half that is easy to get wrong.

    services.yaml is valid here. Installing it anyway would leave the
    process running one file from disk and one from before the edit — a
    combination nobody wrote, and strictly worse than the restart this
    replaces, because the operator cannot tell by looking.
    """
    config, services = files
    config.write_text("service: {port: 'not-a-port'}")
    before_services = get_services()

    report = reload_configuration(config_path=config, services_path=services)

    assert not report.ok
    assert "config.yaml" in (report.error or "")
    assert get_services() is before_services


def test_missing_config_is_refused_not_raised(tmp_path, files, restore_singletons):
    config, services = files
    report = reload_configuration(
        config_path=tmp_path / "gone.yaml", services_path=services
    )
    assert not report.ok
    assert "config.yaml" in (report.error or "")


def test_requires_restart_is_reported_and_the_reload_still_happens(
    files, restore_singletons
):
    """Applied-and-named, not refused — the decision this session took."""
    config, services = files
    # Install the baseline first: the diff is against what is *running*,
    # not against pydantic's defaults.
    assert _reload((config, services)).ok

    raw = yaml.safe_load(config.read_text())
    raw["schedules"] = {"briefing_hour": 9}
    raw["agents"]["log_aggregator"] = {"poll_interval_seconds": 120}
    config.write_text(yaml.safe_dump(raw))

    report = _reload((config, services))

    assert report.ok
    assert report.requires_restart == [
        "agents.log_aggregator.poll_interval_seconds",
        "schedules.briefing_hour",
    ]
    assert not report.config_unchanged
    # The reload still installed everything it could.
    assert get_config().schedules.briefing_hour == 9
    assert [s.name for s in get_services().services] == ["alpha"]


def test_services_registry_is_checked_against_the_new_projects_root(
    tmp_path, files, restore_singletons
):
    """Rule 3: an id is validated against the root the new file names.

    With one manifest present the registry turns strict, so an unknown
    project id must fail — and it must fail against the root config.yaml
    now declares, not the one it declared before the edit.
    """
    config, services = files
    root = tmp_path / "elsewhere"
    (root / "known").mkdir(parents=True)
    (root / "known" / ".project.yaml").write_text(
        yaml.safe_dump(
            {"schema": 1, "id": "known", "name": "known", "status": "active"}
        )
    )
    raw = yaml.safe_load(config.read_text())
    raw["agents"]["project_organiser"]["projects_root"] = str(root)
    config.write_text(yaml.safe_dump(raw))
    services.write_text(yaml.safe_dump({
        "schema": 1,
        "services": [{"name": "alpha", "kind": "http",
                      "url": "http://localhost:1/health", "project": "ghost"}],
    }))

    report = reload_configuration(config_path=config, services_path=services)

    assert not report.ok
    assert "ghost" in (report.error or "")


# ── pruning ──────────────────────────────────────────────────────────


class _FakeAgent:
    name = "fake"

    def __init__(self, dropped):
        self._dropped = dropped
        self.calls = 0

    def forget_unknown(self):
        self.calls += 1
        return self._dropped


def test_pruners_run_after_the_swap_and_names_are_reported(files, restore_singletons):
    agent = _FakeAgent(["gone"])
    report = _reload(files, prunable=(agent,))
    assert agent.calls == 1
    assert report.pruned == {"fake": ["gone"]}


def test_pruners_that_dropped_nothing_are_omitted(files, restore_singletons):
    report = _reload(files, prunable=(_FakeAgent([]),))
    assert report.pruned == {}


def test_pruners_do_not_run_when_the_reload_is_refused(
    tmp_path, files, restore_singletons
):
    """A refused reload changed nothing, so there is nothing to prune."""
    _, services = files
    agent = _FakeAgent(["gone"])
    reload_configuration(
        config_path=tmp_path / "gone.yaml", services_path=services, prunable=(agent,)
    )
    assert agent.calls == 0


def test_sysadmin_agent_prunes_removed_and_keeps_survivors():
    """The decision: prune the departed, keep the streaks of the living.

    Clearing ``_degraded_counts`` wholesale would re-arm the three-poll
    streak that gates an alert — at the moment an operator is most likely
    to be reloading *because* something is failing.
    """
    from sysadmin.monitor.agent import SysAdminAgent
    from tests.conftest import set_services as install

    agent = SysAdminAgent()
    agent._degraded_counts = {"stays": 2, "goes": 2}
    agent._failure_counts = {"stays": 1, "goes": 1}
    agent._last_status = {"stays": "degraded", "goes": "ok"}

    install({"name": "stays", "kind": "http", "url": "http://localhost:1/health"})
    dropped = agent.forget_unknown()

    assert dropped == ["goes"]
    assert agent._degraded_counts == {"stays": 2}
    assert agent._failure_counts == {"stays": 1}
    assert agent._last_status == {"stays": "degraded"}


def test_log_aggregator_keeps_cursors_for_config_declared_sources(monkeypatch):
    """The known set is both files, not services.yaml alone.

    Dropping a cursor is not a clean slate: the next poll falls back to
    ``_resume_floor()`` and re-reads from the newest stored entry, which is
    the per-restart duplication the cursor exists to remove.
    """
    from sysadmin.core.config import AppConfig, LogSource
    from sysadmin.monitor.log_aggregator import LogAggregatorAgent
    from tests.conftest import set_services as install

    config = AppConfig()
    config.agents.log_aggregator.sources = [
        LogSource(name="from-config", type="journalctl", unit="x.service")
    ]
    monkeypatch.setattr("sysadmin.monitor.log_aggregator.get_config", lambda: config)

    agent = LogAggregatorAgent()
    agent._cursors = {"from-services": "c1", "from-config": "c2", "retired": "c3"}
    agent._file_offsets = {"retired": 10}

    install({"name": "from-services", "kind": "http",
             "url": "http://localhost:1/health",
             "log": {"type": "journalctl", "unit": "y.service"}})

    assert agent.forget_unknown() == ["retired"]
    assert set(agent._cursors) == {"from-services", "from-config"}
    assert agent._file_offsets == {}


# ── the wire shape ───────────────────────────────────────────────────


def test_payload_round_trips_through_the_contract(files, restore_singletons):
    report = _reload(files)
    parsed = ReloadResponse.from_dict(report.to_payload())
    assert parsed.ok is True
    assert parsed.services_total == 1
    assert parsed.reloaded_at


def test_refusal_payload_carries_the_error(tmp_path):
    report = ReloadReport(
        ok=False,
        reloaded_at=__import__("datetime").datetime.now(
            __import__("datetime").UTC
        ),
        error="config.yaml: boom",
    )
    parsed = ReloadResponse.from_dict(report.to_payload())
    assert parsed.ok is False
    assert parsed.error == "config.yaml: boom"
    assert parsed.requires_restart == []


# ── the endpoint and the signal ──────────────────────────────────────


@pytest.mark.anyio
async def test_reload_endpoint_returns_200_with_ok_false_on_a_bad_file(
    test_client, monkeypatch
):
    """200 whatever the outcome — a 4xx would make a client discard the report."""
    import sysadmin.main as main

    async def refuse():
        return ReloadReport(
            ok=False,
            reloaded_at=__import__("datetime").datetime.now(
                __import__("datetime").UTC
            ),
            error="services.yaml: invalid",
        )

    monkeypatch.setattr(main, "_reload_configuration", refuse)
    response = await test_client.post("/api/sysadmin/reload")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error"] == "services.yaml: invalid"


def test_reload_endpoint_requires_auth():
    """The mutating-endpoint rule applies — this one re-reads a file as root's peer."""
    from sysadmin.main import create_app

    app = create_app()
    route = next(
        r for r in app.routes
        if getattr(r, "path", None) == "/api/sysadmin/reload"
    )
    assert route.dependant.dependencies, "reload must carry require_auth"


@pytest.mark.anyio
async def test_sighup_handler_installs_and_removes():
    """The mechanism, not the reload.

    Python's default SIGHUP action *terminates* the process, so this
    handler is the only thing separating ``kill -HUP`` from a restart
    dressed as a reload — which is why it is asserted rather than assumed.
    """
    import asyncio
    import signal

    from sysadmin.main import _install_sighup_handler

    loop = asyncio.get_running_loop()
    assert _install_sighup_handler(loop) is True
    loop.remove_signal_handler(signal.SIGHUP)
