"""The reload path — SNAG-UNITS-005's durable half, and SNAG-RELOAD-001's.

The test that earns its place is :func:`test_every_lifespan_config_read_is_classified`.
:data:`sysadmin.reload.RESTART_ONLY` is a hand-written list, and a
hand-written classification that nothing checks is the SNAG-CFG-001 shape:
parsed, plausible, and quietly wrong. This one decides what an operator is
*told* about their own edit, so it rots in the direction nobody notices —
a new scheduled job reading a new config field would silently be reported
as live when it is not.

Session 50 moved the schedule out of ``main.py``'s lifespan and into
``sysadmin/core/jobs.py``, which would have hollowed that guard out
completely: fifteen of the reads it was watching left the function it
walks. So it walks both, and gains a second half —
:func:`test_job_specs_declare_exactly_what_the_planner_reads`, which pins
each ``JobSpec``'s declared ``config_paths`` to the paths ``plan_jobs``
actually reads. The declaration is what the reload reports from; a
declaration that has drifted from its own source is the same failure one
level down.
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
    LIVE_VIA_JOB_SYNC,
    RESTART_ONLY,
    ReloadReport,
    changed_job_paths,
    changed_restart_only,
    diff_services,
    reload_configuration,
)

MAIN_PY = Path(__file__).resolve().parents[1] / "sysadmin" / "main.py"
JOBS_PY = Path(__file__).resolve().parents[1] / "sysadmin" / "core" / "jobs.py"


# ── the classification guard ─────────────────────────────────────────


def _function_node(path: Path, name: str) -> ast.AST:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{path.name} has no `{name}` — adjust this test")


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


def config_paths_read(node: ast.AST) -> set[str]:
    """Dotted config paths a function reads, from its source.

    Only *maximal* chains count: ``config.agents`` on the right of
    ``agents_config = config.agents`` is an alias, not a read, and
    reporting it would demand that the whole ``agents`` subtree be
    classified — the opposite of the point, since the thresholds under it
    are re-read every run.

    **An assignment is an alias only if the name is later used as an
    attribute base.** ``delay = schedules.agent_first_run_delay_seconds``
    looks identical to an alias and is a genuine read of a leaf; treating
    it as an alias drops that leaf from the set silently, which is this
    guard failing in exactly the direction it exists to catch.
    """
    assigns: list[tuple[str, list[str], ast.AST]] = []
    for stmt in ast.walk(node):
        if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
            continue
        target = stmt.targets[0]
        chain = _chain(stmt.value)
        if isinstance(target, ast.Name) and chain is not None:
            assigns.append((target.id, chain, stmt.value))

    # Names used as the base of an attribute access — the only ones that
    # can be aliases, since nothing else resolves *through* them.
    bases = {
        chain[0]
        for sub in ast.walk(node)
        if isinstance(sub, ast.Attribute)
        and (chain := _chain(sub)) is not None
        and len(chain) > 1
    }

    aliases = {"config": ""}
    changed = True
    while changed:  # `agents = config.agents` may precede or follow its own use
        changed = False
        for name, chain, _ in assigns:
            if name in aliases or name not in bases or chain[0] not in aliases:
                continue
            prefix = aliases[chain[0]]
            rest = ".".join(chain[1:])
            aliases[name] = f"{prefix}.{rest}" if prefix else rest
            changed = True
    alias_rhs = {id(value) for name, _, value in assigns if name in aliases}

    # Attribute nodes that are somebody else's `.value` are not maximal.
    inner = {id(sub.value) for sub in ast.walk(node) if isinstance(sub, ast.Attribute)}

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


def lifespan_config_paths() -> set[str]:
    """What the lifespan reads directly, plus what the plan reads for it.

    ``apply_jobs(scheduler, config, JOB_TARGETS)`` is a read of everything
    ``plan_jobs`` touches; counting only the lifespan's own attribute
    chains would let fifteen classified fields quietly leave the guard.
    """
    return config_paths_read(_function_node(MAIN_PY, "lifespan")) | config_paths_read(
        _function_node(JOBS_PY, "plan_jobs")
    )


def test_lifespan_reads_are_actually_found():
    """Guard the guard: a parser that finds nothing passes vacuously."""
    paths = lifespan_config_paths()
    assert "schedules.briefing_hour" in paths
    assert "agents.log_aggregator.poll_interval_seconds" in paths
    assert len(paths) >= 15, sorted(paths)


def test_every_lifespan_config_read_is_classified():
    """Nothing read once at startup may go unclassified.

    A field the lifespan reads is either restart-only, explicitly recorded
    as read again later, or delivered by the job sync. None of the three
    is allowed to simply omit it — an omission means ``requires_restart``
    stays silent about a field the running process is not obeying, which
    is the exact failure the report exists to prevent.
    """
    restart_prefixes = tuple(path for path, _ in RESTART_ONLY)
    live = {path for path, _ in LIVE_AT_STARTUP} | set(LIVE_VIA_JOB_SYNC)
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


def _resolves(path: str) -> bool:
    node: object = AppConfig().model_dump(mode="json")
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def test_classified_paths_exist_on_the_model():
    """A renamed field must break this list rather than drop out of it."""
    for path, reason in RESTART_ONLY + LIVE_AT_STARTUP:
        assert _resolves(path), f"{path} does not resolve against AppConfig"
        assert reason, f"{path} carries no reason"


def test_job_declared_paths_exist_on_the_model():
    """The derived classification gets the same treatment as the two lists.

    It is derived from the plan, so it cannot fall *behind* the jobs — but
    a ``JobSpec`` can still name a leaf that does not exist, and a path
    that resolves against nothing silently matches nothing in the diff.
    """
    for path in sorted(LIVE_VIA_JOB_SYNC):
        assert _resolves(path), f"{path} does not resolve against AppConfig"


def test_job_specs_declare_exactly_what_the_planner_reads():
    """The declaration and its own source, pinned together.

    ``JobSpec.config_paths`` is what ``sysadmin/reload.py`` classifies and
    reports from. Nothing else connects it to the code that produced it,
    so a job re-timed off a field its spec does not name would be applied
    live and reported as needing a restart — or, worse, the reverse.
    """
    from sysadmin.core.jobs import plan_jobs

    declared = {path for spec in plan_jobs(AppConfig()) for path in spec.config_paths}
    read = config_paths_read(_function_node(JOBS_PY, "plan_jobs"))
    assert declared == read, (
        "declared but not read: " + str(sorted(declared - read))
        + "; read but not declared: " + str(sorted(read - declared))
    )


def test_no_path_is_classified_both_ways():
    restart = {path for path, _ in RESTART_ONLY}
    live = {path for path, _ in LIVE_AT_STARTUP}
    assert not restart & live
    assert not restart & LIVE_VIA_JOB_SYNC
    assert not live & LIVE_VIA_JOB_SYNC


def test_a_leaf_read_into_a_local_is_not_mistaken_for_an_alias():
    """Guard the guard, second edition.

    ``delay = schedules.agent_first_run_delay_seconds`` is syntactically
    identical to ``agents = config.agents`` and semantically the opposite.
    The first draft of this helper dropped it, which would have let a real
    read go unclassified while every test still passed.
    """
    module = ast.parse(
        "def f(config):\n"
        "    schedules = config.schedules\n"
        "    delay = schedules.agent_first_run_delay_seconds\n"
        "    return delay\n"
    )
    paths = config_paths_read(module.body[0])
    assert paths == {"schedules.agent_first_run_delay_seconds"}


# ── the diff ─────────────────────────────────────────────────────────


def test_restart_only_diff_names_leaves_not_prefixes():
    """`service` changed is not an answer — an operator still has to grep."""
    old = AppConfig()
    new = AppConfig()
    new.service.port = 8501
    assert changed_restart_only(old, new) == ["service.port"]


def test_the_scheduler_fields_left_restart_only():
    """SNAG-RELOAD-001's shape, as a diff.

    Every one of these was in ``RESTART_ONLY`` when Session 49 shipped,
    and each is now delivered by the job sync. If one comes back to this
    list, a reload has quietly stopped re-timing something.
    """
    old = AppConfig()
    new = AppConfig()
    new.schedules.briefing_hour = 7
    new.agents.sysadmin.health_check_interval_seconds = 999
    new.agents.file_organiser.enabled = False
    assert changed_restart_only(old, new) == []
    assert changed_job_paths(old, new) == [
        "agents.file_organiser.enabled",
        "agents.sysadmin.health_check_interval_seconds",
        "schedules.briefing_hour",
    ]


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


# ── the job sync ─────────────────────────────────────────────────────
#
# SNAG-RELOAD-001. Session 49 installed the whole `AppConfig` and left the
# running scheduler on triggers built at startup, so the config object read
# 999 while the job kept firing every 300 s — named once, in
# `requires_restart`, which is the warning-fires-once shape Session 39
# spent itself removing. These pin the removal rather than the report.


class _FakeSyncer:
    """Stands in for ``main._sync_jobs``, recording what it was given."""

    def __init__(self, report=None, raises=False):
        from sysadmin.core.jobs import JobSyncReport

        self.report = report if report is not None else JobSyncReport()
        self.raises = raises
        self.configs = []
        self.services_at_call = []

    def __call__(self, config):
        self.configs.append(config)
        self.services_at_call.append([s.name for s in get_services().services])
        if self.raises:
            raise RuntimeError("scheduler is gone")
        return self.report


def _bumped(files, **_):
    """Install the baseline, then edit a live job field. The diff is against
    what is *running*, not against pydantic's defaults."""
    config, services = files
    assert _reload((config, services)).ok
    raw = yaml.safe_load(config.read_text())
    raw["agents"]["sysadmin"] = {"health_check_interval_seconds": 999}
    config.write_text(yaml.safe_dump(raw))


def test_a_changed_interval_is_delivered_rather_than_reported(
    files, restore_singletons
):
    """The snag, as a test.

    Before Session 50 this same edit produced
    ``requires_restart == ["agents.sysadmin.health_check_interval_seconds"]``
    and a scheduler still on 300 s.
    """
    from sysadmin.core.jobs import JobSyncReport

    config, services = files
    _bumped(files)
    syncer = _FakeSyncer(JobSyncReport(retimed=["sysadmin_health_check"]))

    report = reload_configuration(
        config_path=config, services_path=services, sync_jobs=syncer
    )

    assert report.ok
    assert report.requires_restart == []
    assert report.jobs_synced is True
    assert report.jobs_retimed == ["sysadmin_health_check"]


def test_without_a_syncer_every_job_leaf_that_moved_is_owed_a_restart(
    files, restore_singletons
):
    """The honest fallback, and why ``jobs_synced`` exists.

    An empty ``jobs_retimed`` means "nothing needed re-timing" in the test
    above and "the scheduler was never looked at" here. Without the flag
    the two are the same response — ``ports_checked``'s rule, one domain
    over.
    """
    config, services = files
    _bumped(files)

    report = reload_configuration(config_path=config, services_path=services)

    assert report.ok
    assert report.jobs_synced is False
    assert report.requires_restart == [
        "agents.sysadmin.health_check_interval_seconds"
    ]


def test_a_syncer_that_blows_up_falls_back_to_reporting(files, restore_singletons):
    """``apply_jobs`` catches per job, so this only fires if the host is
    broken — in which case nothing was re-timed and the no-syncer answer is
    the correct one, not a silent success."""
    config, services = files
    _bumped(files)
    syncer = _FakeSyncer(raises=True)

    report = reload_configuration(
        config_path=config, services_path=services, sync_jobs=syncer
    )

    assert report.ok
    assert report.jobs_synced is False
    assert "agents.sysadmin.health_check_interval_seconds" in report.requires_restart


def test_a_refused_job_is_reported_as_restart_only(files, restore_singletons):
    """One job the host would not take, named per config leaf.

    ``jobs_synced`` stays true: the scheduler *was* reconciled, and eight
    of the nine jobs took. Reporting it as unsynced would owe a restart for
    the whole schedule on one bad job.
    """
    from sysadmin.core.jobs import JobSyncReport

    config, services = files
    _bumped(files)
    syncer = _FakeSyncer(
        JobSyncReport(
            failed={"sysadmin_health_check": "RuntimeError: no"},
            failed_config_paths=["agents.sysadmin.health_check_interval_seconds"],
        )
    )

    report = reload_configuration(
        config_path=config, services_path=services, sync_jobs=syncer
    )

    assert report.jobs_synced is True
    assert report.requires_restart == [
        "agents.sysadmin.health_check_interval_seconds"
    ]


def test_the_syncer_runs_after_the_swap(files, restore_singletons):
    """It must re-time against the configuration that was installed.

    Handing it ``new_config`` while the singletons still held the old pair
    would work by luck — the argument is right and the agents the jobs run
    would read the old services. Both are installed first, inside the same
    lock.
    """
    config, services = files
    syncer = _FakeSyncer()

    reload_configuration(
        config_path=config, services_path=services, sync_jobs=syncer
    )

    assert syncer.configs == [get_config()]
    assert syncer.services_at_call == [["alpha"]]


def test_the_syncer_does_not_run_when_the_reload_is_refused(
    tmp_path, files, restore_singletons
):
    """Nothing was installed, so there is nothing to re-time — and
    re-timing against a config that was rejected is the half-success rule 1
    exists to prevent, reaching the scheduler instead of the singletons."""
    _, services = files
    syncer = _FakeSyncer()

    report = reload_configuration(
        config_path=tmp_path / "gone.yaml",
        services_path=services,
        sync_jobs=syncer,
    )

    assert not report.ok
    assert syncer.configs == []
    assert report.jobs_synced is False


def test_the_payload_carries_the_job_fields(files, restore_singletons):
    from sysadmin.core.jobs import JobSyncReport

    config, services = files
    syncer = _FakeSyncer(
        JobSyncReport(added=["a"], removed=["b"], retimed=["c"], unchanged=["d"])
    )
    payload = reload_configuration(
        config_path=config, services_path=services, sync_jobs=syncer
    ).to_payload()

    assert payload["jobs_synced"] is True
    assert payload["jobs_added"] == ["a"]
    assert payload["jobs_removed"] == ["b"]
    assert payload["jobs_retimed"] == ["c"]
    # `unchanged` is deliberately not on the wire: it is nine ids on every
    # reload, and `jobs_synced` already answers the question it would.
    assert "jobs_unchanged" not in payload
    assert ReloadResponse.model_validate(payload).jobs_retimed == ["c"]


def test_main_hands_the_reload_a_real_syncer():
    """The seam is only worth having if production actually uses it.

    A default of ``None`` means a reload with no syncer is a valid call —
    so nothing but this test stops the daemon from quietly making one and
    reporting a restart it did not need.
    """
    import inspect

    from sysadmin import main

    assert "sync_jobs=_sync_jobs" in inspect.getsource(main._reload_configuration)
    assert main._sync_jobs(get_config()) is not None
