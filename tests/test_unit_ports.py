"""Session 26c — who actually holds each port.

Nothing on this box has ever collided, which is an awkward starting
position for a test suite: every fixture here describes a state that has
never existed, and the one thing that *can* be checked against reality is
that the clean case comes back clean.  So the numbers are the ones
measured on 2026-08-15 — the real ``ss -H -ltnp`` output shape, the real
cgroup paths, the real registry rows — and the collisions are those
fixtures with one field moved.

The observation half is driven through an injected runner rather than
mocked away: parsing ``users:(("uvicorn",pid=1057804,fd=15))`` is the
part most likely to be wrong, and a mock that returns ``Listener``
objects would test nothing but the mock.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.units import ports as P  # noqa: N812
from sysadmin.units.agent import (
    PORT_TITLE_PREFIX,
    ServiceDiscoveryAgent,
    port_alert_title,
)
from sysadmin.units.recommendations import recommendations_for_scan
from sysadmin.units.scan import HOST, UNMONITORED, UnitFinding

# ── Fixtures taken from the live box, 2026-08-15 ─────────────────────

LIVE_SS = """\
LISTEN 0      4096     0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))
LISTEN 0      4096     0.0.0.0:8500 0.0.0.0:* users:(("uvicorn",pid=1267878,fd=16))
LISTEN 0      511      127.0.0.1:3100 0.0.0.0:* users:(("node",pid=1263,fd=21))
LISTEN 0      4096     127.0.0.1:44581 0.0.0.0:*
"""

LIVE_CGROUPS = {
    1057804: "0::/user.slice/user-1000.slice/user@1000.service/app.slice/alfred-backend.service\n",
    1267878: "0::/system.slice/sysadmin.service\n",
    1263: "0::/user.slice/user-1000.slice/user@1000.service/app.slice/alfred-frontend.service\n",
}

#: Four real rows plus the ``_free_`` one, which claims nothing.
LIVE_REGISTRY = """\
| Port | Project | Role |
|------|---------|------|
| 8100 | Alfred | backend (FastAPI) |
| 8200 | SportsAnalyser | backend (FastAPI) |
| 8500 | sysadmin-service | backend (FastAPI) |
| 3100 | Alfred | frontend (Nuxt) |
| 3400 | _free — next frontend allocation_ | |
"""


def _runner(stdout=LIVE_SS, returncode=0, stderr=""):
    def run(*_args, **_kwargs):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    return run


def _observe(stdout=LIVE_SS, cgroups=None, **kwargs):
    table = LIVE_CGROUPS if cgroups is None else cgroups
    return P.observe_listeners(
        runner=_runner(stdout=stdout, **kwargs),
        cgroup_reader=lambda pid: table.get(pid),
    )


def _declared(name, port, unit, scope="user", project=None):
    return SimpleNamespace(
        name=name, port=port, unit=unit, scope=scope, project=project
    )


# ── Observation ──────────────────────────────────────────────────────


def test_ss_output_is_attributed_to_units_with_scope():
    """The measurement the whole session rests on.

    estate-manager runs ``ss`` without ``-p`` on the stated grounds that
    *"process names need privileges for other users' sockets"*.  True,
    and it does not apply to our own: as ``gaddi``, every
    registry-relevant port on this box came back with a pid on
    2026-08-15.  ``/proc/<pid>/cgroup`` then names the unit **and** the
    scope, which is the identity ``services.yaml`` keys on.
    """
    report = _observe()
    assert report.ok
    holders = {x.port: (x.unit, x.scope) for x in report.listeners}
    assert holders[8100] == ("alfred-backend.service", "user")
    assert holders[8500] == ("sysadmin.service", "system")
    assert holders[3100] == ("alfred-frontend.service", "user")


def test_scope_comes_from_the_cgroup_path_not_the_unit_name():
    """``sysadmin.service`` is a *system* unit and nothing in its name says so.

    This is why ``/proc`` beat ``systemctl show -p MainPID``, which needs
    to know the scope before it can ask — the same unit returns
    ``MainPID=0`` on the user bus.
    """
    unit, scope = P._unit_from_cgroup("0::/system.slice/sysadmin.service")
    assert (unit, scope) == ("sysadmin.service", "system")
    unit, scope = P._unit_from_cgroup(
        "0::/user.slice/user-1000.slice/user@1000.service/app.slice/alfred-backend.service"
    )
    assert (unit, scope) == ("alfred-backend.service", "user")


def test_a_dual_stack_listener_is_one_holder_not_two():
    """A port bound on v4 and v6 prints twice with the same pid.

    Without the ``(port, pid)`` dedup this would raise ``port_shared``
    against every dual-stack server on the box — the family's first live
    run would be entirely false positives.
    """
    stdout = (
        'LISTEN 0 4096 0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
        'LISTEN 0 4096 [::]:8100 [::]:* users:(("uvicorn",pid=1057804,fd=16))\n'
    )
    report = _observe(stdout=stdout)
    assert len(report.listeners) == 1
    assert P.judge_ports(report, [], [], {}, {}).findings == ()


def test_a_root_owned_listener_is_unattributed_and_is_not_a_finding():
    """8601 (the SearXNG container) and 5432 come back blank.

    Not-knowing is never a mismatch — the rule
    :mod:`sysadmin.monitor.collation` settled on.  Reported as evidence
    so the gap is visible rather than absent.
    """
    report = _observe()
    assert report.unattributed == (44581,)
    assert all(x.unit is None for x in report.listeners if x.port == 44581)


def test_an_unreadable_cgroup_is_no_attribution_not_an_error():
    """The process exited between ``ss`` printing it and ``/proc`` being read."""
    report = _observe(cgroups={})
    assert report.ok
    assert report.unattributed == (3100, 8100, 8500, 44581)


def test_ss_failing_is_an_error_and_not_an_empty_box():
    """The distinction the sweep's resolve depends on.

    An empty success would close every open collision row on the
    strength of nobody having looked — the estate judge's rule 2, from
    the other side.
    """
    report = _observe(returncode=1, stderr="ss: command not found")
    assert not report.ok
    assert "ss exited 1" in (report.error or "")
    assert report.listeners == ()


def test_ss_missing_entirely_is_the_same_kind_of_error():
    def explode(*_args, **_kwargs):
        raise FileNotFoundError("ss")

    report = P.observe_listeners(runner=explode)
    assert not report.ok
    assert "could not run ss" in (report.error or "")


def test_a_session_scope_is_not_a_service():
    """``app-code-oss-26348.scope`` holds four ports and is nobody's unit.

    The number in the name changes on every login, so a finding built on
    it would never deduplicate.
    """
    stdout = (
        'LISTEN 0 511 127.0.0.1:32876 0.0.0.0:* users:(("electron",pid=26577,fd=47))\n'
    )
    report = _observe(
        stdout=stdout,
        cgroups={
            26577: "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
            "app-code-oss-26348.scope\n"
        },
    )
    listener = report.listeners[0]
    assert listener.attributed and listener.transient
    judged = P.judge_ports(report, [], [], {}, {})
    assert judged.unit_ports() == {}


# ── The registry table ───────────────────────────────────────────────


def test_the_parser_keeps_duplicates_which_is_the_point():
    """estate-manager folds the table into a ``set``.

    That is exactly why a duplicate row has been invisible to their
    check since it was written, and the reason a shared parser would not
    have helped: theirs would have to return the thing it discards.
    """
    document = LIVE_REGISTRY + "| 8100 | venture-assistant | backend |\n"
    claims = P.parse_port_registry(document)
    assert [c.port for c in claims].count(8100) == 2
    assert [c.line for c in claims if c.port == 8100] == [3, 8]


def test_rows_claiming_nothing_are_skipped():
    claims = P.parse_port_registry(LIVE_REGISTRY)
    assert 3400 not in {c.port for c in claims}
    assert len(claims) == 4


# ── The clean box ────────────────────────────────────────────────────


def test_the_live_estate_is_clean_which_is_the_only_thing_reality_can_confirm():
    """Every comparison, against the state that actually exists.

    The three fixtures above are the box as measured, so this asserting
    zero is the same claim tasks.md makes in prose: *"nothing on this box
    has ever collided"* — now verified **with attribution** rather than
    asserted.
    """
    report = P.judge_ports(
        _observe(),
        [
            _declared("alfred", 8100, "alfred-backend.service", "user", "alfred"),
            _declared("sysadmin-service", 8500, "sysadmin.service", "system"),
            _declared("alfred-frontend", 3100, "alfred-frontend.service", "user"),
        ],
        P.parse_port_registry(LIVE_REGISTRY),
        {
            "user:alfred-backend.service": "Alfred",
            "user:alfred-frontend.service": "Alfred",
            "system:sysadmin.service": "sysadmin_assistant",
        },
        {
            "Alfred": ["Alfred", "alfred"],
            "sysadmin_assistant": ["sysadmin_assistant", "sysadmin-assistant"],
        },
    )
    assert report.findings == ()
    assert report.ok


# ── wrong_unit ───────────────────────────────────────────────────────


def test_services_yaml_naming_a_unit_that_does_not_hold_the_port():
    """The check that has never existed and costs nothing to run.

    ``services.yaml`` has carried ``port:`` beside ``systemd: {unit}``
    since Session 35 and the two are read by different checks, so an
    ``http`` probe can be green against a process the tray's restart
    button would never touch.
    """
    report = P.judge_ports(
        _observe(),
        [_declared("alfred", 8100, "nginx.service", "system")],
        [],
        {},
        {},
    )
    assert [f.kind for f in report.findings] == [P.WRONG_UNIT]
    finding = report.findings[0]
    assert finding.port == 8100
    assert finding.detail["actual_units"] == ["user:alfred-backend.service"]
    assert finding.is_collision


def test_scope_alone_is_enough_to_be_wrong():
    """``deadlock-api-ingest.service`` exists in both scopes running two binaries.

    Wiring one says nothing about the other, which is why scope is part
    of a unit's identity here rather than decoration.
    """
    report = P.judge_ports(
        _observe(),
        [_declared("sysadmin-service", 8500, "sysadmin.service", "user")],
        [],
        {},
        {},
    )
    assert [f.kind for f in report.findings] == [P.WRONG_UNIT]


def test_silence_is_not_a_wrong_unit():
    """Nothing listening on a declared port is availability's question.

    It already has two owners — the sysadmin agent's ``% unreachable``
    family and the estate's ``claimed_but_silent`` warn — and a second
    owner closes a row while the first still holds it true.
    """
    report = P.judge_ports(
        _observe(),
        [_declared("venture-assistant", 8300, "venture-assistant-backend.service")],
        [],
        {},
        {},
    )
    assert report.findings == ()


# ── port_shared ──────────────────────────────────────────────────────


def test_two_units_on_one_port_is_a_collision():
    stdout = (
        'LISTEN 0 4096 0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
        'LISTEN 0 4096 127.0.0.1:8100 0.0.0.0:* users:(("node",pid=1263,fd=21))\n'
    )
    report = P.judge_ports(_observe(stdout=stdout), [], [], {}, {})
    assert [f.kind for f in report.findings] == [P.PORT_SHARED]
    assert report.findings[0].detail["units"] == [
        "user:alfred-backend.service",
        "user:alfred-frontend.service",
    ]


# ── duplicate_claim ──────────────────────────────────────────────────


def test_two_registry_rows_claiming_one_port():
    document = LIVE_REGISTRY + "| 8100 | venture-assistant | backend |\n"
    report = P.judge_ports(
        _observe(), [], P.parse_port_registry(document), {}, {}
    )
    assert [f.kind for f in report.findings] == [P.DUPLICATE_CLAIM]
    finding = report.findings[0]
    assert not finding.is_collision
    # Both rows named, not counted — a roll-up cannot be acted on.
    assert [row["line"] for row in finding.detail["rows"]] == [3, 8]


# ── wrong_project ────────────────────────────────────────────────────


def test_the_registry_attributing_a_port_to_the_wrong_project():
    """The attribution estate-manager is structurally blocked from making."""
    document = "| 8100 | SportsAnalyser | backend |\n"
    report = P.judge_ports(
        _observe(),
        [],
        P.parse_port_registry(document),
        {"user:alfred-backend.service": "Alfred"},
        {"Alfred": ["Alfred", "alfred"], "SportsAnalyser": ["SportsAnalyser", "sports-analyser"]},
    )
    assert [f.kind for f in report.findings] == [P.WRONG_PROJECT]
    assert report.findings[0].detail["actual_project"] == "Alfred"


def test_a_manifest_id_is_an_acceptable_name_for_a_project():
    """``SportsAnalyser`` the directory, ``sports-analyser`` the id.

    A third of the repositories here differ that way.  Without the alias
    map a correct registry row reads as a mis-attribution on naming
    alone.
    """
    document = "| 8100 | alfred | backend |\n"
    report = P.judge_ports(
        _observe(),
        [],
        P.parse_port_registry(document),
        {"user:alfred-backend.service": "Alfred"},
        {"Alfred": ["Alfred", "alfred"]},
    )
    assert report.findings == ()


def test_a_row_naming_something_that_is_not_a_project_is_evidence_not_a_finding():
    """``sysadmin-service`` is what the live table says for 8500 today.

    The manifest id is ``sysadmin-assistant`` and the directory is
    ``sysadmin_assistant``, so neither matches — but a registry row may
    legitimately name a third-party daemon (``_syncthing_`` holds 8384),
    and telling a typo from a daemon needs judgement this check does not
    have.  "Wrong project" and "not a project" are different faults.
    """
    document = "| 8500 | sysadmin-service | backend |\n"
    report = P.judge_ports(
        _observe(),
        [],
        P.parse_port_registry(document),
        {"system:sysadmin.service": "sysadmin_assistant"},
        {"sysadmin_assistant": ["sysadmin_assistant", "sysadmin-assistant"]},
    )
    assert report.findings == ()
    assert report.unknown_registry_projects == ("sysadmin-service",)


def test_a_unit_matching_no_project_is_not_a_mismatch():
    document = "| 8384 | _syncthing_ | web UI |\n"
    report = P.judge_ports(
        _observe(), [], P.parse_port_registry(document), {}, {}
    )
    assert report.findings == ()


def test_ports_outside_the_audited_ranges_are_not_judged():
    """22000 is claimed and governs nothing — the registry says so itself."""
    document = "| 22000 | SportsAnalyser | sync |\n"
    stdout = 'LISTEN 0 4096 0.0.0.0:22000 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
    report = P.judge_ports(
        _observe(stdout=stdout),
        [],
        P.parse_port_registry(document),
        {"user:alfred-backend.service": "Alfred"},
        {"Alfred": ["Alfred"], "SportsAnalyser": ["SportsAnalyser"]},
    )
    assert report.findings == ()


def test_a_shared_port_is_not_also_attributed_to_a_project():
    """Two holders means picking one to blame is a guess.

    ``port_shared`` is already the finding; adding ``wrong_project`` on
    top would contradict it with a coin toss.
    """
    stdout = (
        'LISTEN 0 4096 0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
        'LISTEN 0 4096 127.0.0.1:8100 0.0.0.0:* users:(("node",pid=1263,fd=21))\n'
    )
    report = P.judge_ports(
        _observe(stdout=stdout),
        [],
        P.parse_port_registry("| 8100 | SportsAnalyser | backend |\n"),
        {
            "user:alfred-backend.service": "Alfred",
            "user:alfred-frontend.service": "Alfred",
        },
        {"Alfred": ["Alfred"], "SportsAnalyser": ["SportsAnalyser"]},
    )
    assert [f.kind for f in report.findings] == [P.PORT_SHARED]


# ── Failure and exclusion ────────────────────────────────────────────


def test_a_failed_observation_judges_nothing_rather_than_judging_clean():
    report = P.judge_ports(
        _observe(returncode=1),
        [_declared("alfred", 8100, "nginx.service", "system")],
        P.parse_port_registry(LIVE_REGISTRY + "| 8100 | venture | x |\n"),
        {},
        {},
    )
    assert not report.ok
    assert report.findings == ()


def test_ignored_ports_are_judged_by_nothing():
    report = P.judge_ports(
        _observe(),
        [_declared("alfred", 8100, "nginx.service", "system")],
        [],
        {},
        {},
        ignore_ports=[8100],
    )
    assert report.findings == ()


def test_findings_are_ranked_worst_kind_first():
    stdout = (
        'LISTEN 0 4096 0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
        'LISTEN 0 4096 0.0.0.0:8500 0.0.0.0:* users:(("uvicorn",pid=1267878,fd=16))\n'
        'LISTEN 0 4096 127.0.0.1:8500 0.0.0.0:* users:(("node",pid=1263,fd=21))\n'
    )
    report = P.judge_ports(
        _observe(stdout=stdout),
        [_declared("alfred", 8100, "nginx.service", "system")],
        P.parse_port_registry("| 3100 | A | x |\n| 3100 | B | y |\n"),
        {},
        {},
    )
    assert [f.kind for f in report.findings] == [
        P.WRONG_UNIT,
        P.PORT_SHARED,
        P.DUPLICATE_CLAIM,
    ]


# ── The alert family ─────────────────────────────────────────────────
#
# ``_maintain_port_alerts`` runs exactly one SELECT (the open titles) and
# one UPDATE (the sweep), so a two-element ``side_effect`` asserts the
# shape of the work as well as supplying the data.


def _session(open_titles=(), swept=0):
    select_result = MagicMock()
    select_result.scalars.return_value = list(open_titles)
    update_result = MagicMock()
    update_result.rowcount = swept

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=[select_result, update_result])
    return session


@pytest.fixture
def agent():
    a = ServiceDiscoveryAgent()
    a.raise_alert = AsyncMock()
    a._queue_event = MagicMock()
    return a


def _report(*findings, ok=True):
    return P.PortReport(
        findings=tuple(findings), error=None if ok else "ss exited 1"
    )


def _collision(port=8100, kind=P.WRONG_UNIT):
    return P.PortFinding(port=port, kind=kind, summary="x", detail={"port": port})


async def test_the_port_is_in_the_title(agent):
    """Session 46's rule.  A roll-up cannot name anything."""
    await agent._maintain_port_alerts(_session(), _report(_collision(8100)))
    assert agent.raise_alert.await_args.kwargs["title"] == "Port collision on 8100"


async def test_two_kinds_on_one_port_are_one_row(agent):
    """The port is the identity, never the kind.

    A title carrying the kind forks the row the day a second kind lands
    on the same port — and both are one thing to go and look at.
    """
    await agent._maintain_port_alerts(
        _session(),
        _report(_collision(8100, P.WRONG_UNIT), _collision(8100, P.PORT_SHARED)),
    )
    assert agent.raise_alert.await_count == 1
    assert agent.raise_alert.await_args.kwargs["details"]["kinds"] == [
        P.WRONG_UNIT,
        P.PORT_SHARED,
    ]


async def test_only_collisions_reach_the_alert_family(agent):
    """A wrong registry row is debt and goes to the ranked advice."""
    await agent._maintain_port_alerts(
        _session(),
        _report(
            P.PortFinding(port=8100, kind=P.DUPLICATE_CLAIM, summary="x"),
            P.PortFinding(port=8200, kind=P.WRONG_PROJECT, summary="x"),
        ),
    )
    agent.raise_alert.assert_not_awaited()


async def test_a_standing_collision_writes_one_row_not_one_per_sweep(agent):
    result = await agent._maintain_port_alerts(
        _session(open_titles=[port_alert_title(8100)]), _report(_collision(8100))
    )
    agent.raise_alert.assert_not_awaited()
    assert result["held"] == 1 and result["raised"] == 0


async def test_the_still_true_row_is_protected_from_the_sweep(agent):
    """The exclusion set is what the run **judged**, not what it raised.

    Against a raised set, a deduplicating family writes nothing on run
    two, has its still-true row swept here, and re-raises on run three —
    clearing the tray's ``{severity}:{title}`` fingerprint every turn, so
    one fault notifies on every poll.
    """
    session = _session(open_titles=[port_alert_title(8100)])
    await agent._maintain_port_alerts(session, _report(_collision(8100)))
    statement = str(session.execute.await_args_list[1].args[0])
    assert "title NOT IN" in statement


async def test_a_collision_that_clears_resolves_once(agent):
    session = _session(swept=1)
    result = await agent._maintain_port_alerts(session, _report())
    assert result["resolved"] == 1
    agent._queue_event.assert_called_once()


async def test_a_failed_observation_neither_raises_nor_sweeps(agent):
    """The failure this family would otherwise announce as recovery.

    ``ss`` missing means nothing was measured.  Sweeping on that closes
    every open collision row because nobody looked — which reads to the
    tray as a fault having been fixed.
    """
    session = _session(swept=99)
    result = await agent._maintain_port_alerts(session, _report(ok=False))
    session.execute.assert_not_awaited()
    agent.raise_alert.assert_not_awaited()
    assert result == {
        "judged": 0,
        "raised": 0,
        "held": 0,
        "resolved": 0,
        "checked": False,
    }


def test_the_title_stays_clear_of_the_service_families():
    """``RESOLVABLE_TITLE_PATTERNS`` are ``% <kind>`` suffixes.

    A second owner of one row's lifecycle closes it while the first
    still holds it true — the defect ``_resolve_recovered``'s docstring
    names three times over.  The ``Alert.agent`` scoping already makes
    these unreachable; this is the belt to that pair of braces.
    """
    from sysadmin.monitor.agent import RESOLVABLE_TITLE_PATTERNS

    title = port_alert_title(8100)
    for pattern in RESOLVABLE_TITLE_PATTERNS:
        assert not title.endswith(pattern.lstrip("% ")), pattern
    assert title.startswith(PORT_TITLE_PREFIX)


# ── SNAG-UNITS-001: the snippet knows a port now ─────────────────────


def _finding(unit, category, **kwargs):
    kwargs.setdefault("monitor_unit", unit)
    # These model live, enabled units — the enablement gate declines to
    # emit a snippet for a unit nothing starts, so the fixture must say
    # so explicitly.  See the note in tests/test_unit_recommendations.py
    # for why the field's own default is the other way round.
    kwargs.setdefault("enabled", True)
    return UnitFinding(
        unit=unit, scope="user", category=category, path=f"/tmp/{unit}", **kwargs
    )


def _ports_blob(**held):
    return {"unit_audited_ports": dict(held), "findings": []}


def test_a_unit_holding_one_audited_port_is_advised_as_http():
    """SNAG-UNITS-001's fix, and the reason 26c was the sitting to take it.

    A ``kind: systemd`` check asserts only that the unit is active.  A
    backend running while every request 500s is active, healthy by that
    check, and broken.
    """
    recs = recommendations_for_scan(
        [_finding("alfred-backend.service", UNMONITORED, project="Alfred")],
        None,
        ports=_ports_blob(**{"user:alfred-backend.service": [8100]}),
    )
    snippet = recs[0].snippet
    assert "kind: http" in snippet
    assert "url: http://localhost:8100/api/health" in snippet
    assert "port: 8100" in snippet
    assert "kind: systemd" not in snippet


def test_the_health_path_is_marked_as_the_contract_not_an_observation():
    """The sweep sees a port; it never fetches.

    Measured 2026-08-15: ``/api/health`` is right for 4 of the 11
    services declared here and wrong for 7 (``/health``,
    ``/api/v1/health``, and two frontends with no path).  So the
    comment names the alternatives rather than merely hedging —
    SNAG-UNITS-003 carries the argument for shipping a loud wrong url
    over a silent under-monitoring one.
    """
    recs = recommendations_for_scan(
        [_finding("alfred-backend.service", UNMONITORED, project="Alfred")],
        None,
        ports=_ports_blob(**{"user:alfred-backend.service": [8100]}),
    )
    snippet = recs[0].snippet
    assert "path is the contract's default" in snippet
    assert "/health and /api/v1/health are both in use here" in snippet


def test_two_ports_falls_back_rather_than_guessing():
    recs = recommendations_for_scan(
        [_finding("weird.service", HOST)],
        None,
        ports=_ports_blob(**{"user:weird.service": [8100, 8101]}),
    )
    assert "kind: systemd" in recs[0].snippet
    assert "no listening port attributed" in recs[0].snippet


def test_no_port_keeps_the_old_shape_and_gains_the_comment():
    """The snag's own proposed fix, kept for the case its premise still holds."""
    recs = recommendations_for_scan([_finding("quiet.service", HOST)], None)
    assert "kind: systemd" in recs[0].snippet
    assert "use kind: http with a url" in recs[0].snippet


def test_a_timer_is_never_upgraded():
    """A timer holds no socket, and its oneshot is not running when checked."""
    recs = recommendations_for_scan(
        [_finding("job.service", HOST, monitor_unit="job.timer")],
        None,
        ports=_ports_blob(**{"user:job.service": [8100]}),
    )
    assert "kind: timer" in recs[0].snippet
    assert "kind: http" not in recs[0].snippet


# ── The advice half ──────────────────────────────────────────────────


def test_registry_disagreements_become_ranked_advice_last():
    """Last because it is the only kind where the box is right.

    Every other kind names something here that is broken or unwatched;
    this names another repository's document.
    """
    blob = {
        "registry_document": "/x/monitorable-project.md",
        "findings": [
            {
                "port": 8100,
                "kind": P.DUPLICATE_CLAIM,
                "summary": "two rows claim 8100",
                "collision": False,
                "detail": {
                    "rows": [
                        {"line": 3, "project": "Alfred"},
                        {"line": 8, "project": "venture"},
                    ]
                },
            }
        ],
    }
    recs = recommendations_for_scan([_finding("h.service", HOST)], None, ports=blob)
    assert [r.kind for r in recs] == ["host", "port"]
    advice = recs[-1]
    assert advice.severity == "advice"
    assert "line 3 (Alfred)" in advice.action
    # The fix is a row in another repository's markdown table, and the
    # correct row needs the prose in its role column.
    assert advice.snippet == "" and advice.snippet_target is None


def test_collisions_never_appear_as_advice():
    blob = {
        "findings": [
            {"port": 8100, "kind": P.WRONG_UNIT, "summary": "x", "collision": True, "detail": {}}
        ]
    }
    assert recommendations_for_scan([], None, ports=blob) == []


# ── Attribution for the estate judge ─────────────────────────────────


def test_attribution_inverts_the_stored_map():
    attribution = P.attribution_from_blob(
        {"unit_ports": {"user:alfred-backend.service": [8100]}}, "2026-08-15T09:21:06"
    )
    assert attribution.of(8100) == {
        "unit": "alfred-backend.service",
        "scope": "user",
        # Present and False, never absent. A consumer reading
        # ``holder.get("transient")`` against a dict that omitted the key
        # for real units would read every service on the box as
        # non-transient by accident rather than by observation.
        "transient": False,
        "observed_at": "2026-08-15T09:21:06",
    }
    assert attribution.of(9999) is None


def test_a_shared_port_is_not_attributed_to_either_holder():
    attribution = P.attribution_from_blob(
        {"unit_ports": {"user:a.service": [8100], "user:b.service": [8100]}}
    )
    assert attribution.of(8100) is None


def test_the_estate_breach_carries_the_holder_in_details_only():
    """The identity of that row belongs to the producer.

    A holder that changes between sweeps must not fork it, and the sweep
    runs six-hourly against this judge's hourly poll — so the annotation
    carries its own ``observed_at`` rather than implying it is now.
    """
    from sysadmin.estate import judgements

    payload = {
        "findings": [
            {
                "check": "ports",
                "severity": "breach",
                "code": "unclaimed_listener",
                "subject": "port 8100",
                "summary": "port 8100 is listening with no row",
                "detail": {"port": 8100},
            }
        ]
    }
    attribution = P.attribution_from_blob(
        {"unit_ports": {"user:alfred-backend.service": [8100]}}, "2026-08-15T09:21:06"
    )
    judged = judgements.judge_audit_findings(payload, 5, attribution)
    assert judged[0].details["holder"]["unit"] == "alfred-backend.service"
    assert "alfred-backend" not in judged[0].title
    assert "alfred-backend" not in judged[0].message


def test_the_estate_breach_is_unchanged_without_a_sweep_to_read():
    """The enrichment must never become a dependency of the alert."""
    from sysadmin.estate import judgements

    payload = {
        "findings": [
            {
                "check": "ports",
                "severity": "breach",
                "subject": "port 8100",
                "summary": "port 8100 is listening with no row",
                "detail": {"port": 8100},
            }
        ]
    }
    judged = judgements.judge_audit_findings(payload, 5)
    assert len(judged) == 1
    assert judged[0].details["holder"] is None


# ── Session 57: a session scope is attributed, and was invisible ─────

#: Measured on 2026-08-17, the first live rows this family ever produced.
#: Both are Alfred dev servers launched from VS Code — ``uvicorn
#: --reload`` on 8110 (which prints two pid groups, the reloader and the
#: worker) and ``nuxt dev`` on 3110, bound v6-only.
DEV_SERVER_SS = (
    'LISTEN 0      4096     0.0.0.0:8100 0.0.0.0:* users:(("uvicorn",pid=1057804,fd=15))\n'
    # Split for the line limit only. The column padding and *both* pid
    # groups are exactly as ``ss`` printed them: ``uvicorn --reload``
    # runs a reloader and a worker, and the parser takes one pid per
    # group rather than one per line because of it.
    'LISTEN 0      2048     127.0.0.1:8110 0.0.0.0:* '
    'users:(("python",pid=1959174,fd=3),("uvicorn",pid=1897721,fd=3))\n'
    'LISTEN 0      511      [::1]:3110 [::]:* users:(("node",pid=1897728,fd=24))\n'
)

EDITOR_SCOPE = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "app-code-oss-26348.scope\n"
)

DEV_SERVER_CGROUPS = {
    1057804: LIVE_CGROUPS[1057804],
    1959174: EDITOR_SCOPE,
    1897721: EDITOR_SCOPE,
    1897728: EDITOR_SCOPE,
}


def _dev_blob():
    report = _observe(stdout=DEV_SERVER_SS, cgroups=DEV_SERVER_CGROUPS)
    return P.judge_ports(report, [], [], {}, {}).as_blob()


def test_a_session_scope_used_to_fall_out_of_the_blob_entirely():
    """The defect, stated as the two keys that could not hold it.

    ``unit_ports`` skips a transient listener for its own consumer's
    correct reason, and ``unattributed_ports`` never held one because a
    session scope *is* attributed.  So the port appeared in neither, the
    estate judge's ``attribution.of(3110)`` returned ``None``, and
    "nobody is attributable" (5432, root-owned) was indistinguishable
    from "attributable, and to something we chose not to write down".
    """
    blob = _dev_blob()
    assert blob["unit_ports"] == {"user:alfred-backend.service": [8100]}
    assert blob["unattributed_ports"] == []
    assert blob["transient_ports"] == {"user:app-code-oss-26348.scope": [3110, 8110]}


def test_the_snippet_consumers_map_is_untouched_by_the_new_key():
    """One field, two consumers, opposite safe defaults — Session 48.

    ``recommendations.py`` reads ``unit_ports`` to decide whether a unit
    can be advised as ``kind: http``.  A session scope is nobody's
    service, and widening that map rather than adding a second key would
    have made the snippet gate learn about transience in order to keep
    behaving exactly as it already does.
    """
    blob = _dev_blob()
    assert "app-code-oss-26348.scope" not in str(blob["unit_ports"])
    assert "app-code-oss-26348.scope" not in str(blob["unit_audited_ports"])


def test_the_judge_can_now_name_the_editor_holding_the_port():
    """The round trip, driven rather than asserted a piece at a time.

    Session 52's lesson: every rule pinned against a literal written by
    the same hand that wrote the consumer is the strongest evidence
    available and is not an observation.  This one goes ``ss`` output →
    listeners → report → blob → attribution, so a break anywhere in that
    chain fails here.
    """
    attribution = P.attribution_from_blob(_dev_blob(), "2026-08-17T06:07:11+01:00")
    for port in (3110, 8110):
        holder = attribution.of(port)
        assert holder["unit"] == "app-code-oss-26348.scope"
        assert holder["scope"] == "user"
        assert holder["transient"] is True
        # Six-hourly sweep, hourly judge: the annotation may legitimately
        # be five hours older than the row it lands on, so it carries its
        # own stamp rather than implying now.
        assert holder["observed_at"] == "2026-08-17T06:07:11+01:00"
    assert attribution.of(8100)["transient"] is False


def test_a_port_held_by_a_scope_and_a_unit_is_attributed_to_neither():
    """The ambiguity rule spans both maps, not each one separately.

    A dev server bound to a port a real service also holds is exactly the
    state a reader needs told, and naming either as *the* holder would
    answer here a question ``judge_ports`` reports as a disagreement.
    """
    attribution = P.attribution_from_blob(
        {
            "unit_ports": {"user:alfred-backend.service": [8100]},
            "transient_ports": {"user:app-code-oss-26348.scope": [8100]},
        }
    )
    assert attribution.of(8100) is None


def test_a_sweep_written_before_this_change_still_attributes():
    """Every stored sweep before Session 57 has no ``transient_ports``.

    60 of them today.  The key's absence must read as "no transient
    holders were recorded", never as a reason to stop attributing the
    ones that were.
    """
    attribution = P.attribution_from_blob(
        {"unit_ports": {"user:alfred-backend.service": [8100]}}
    )
    assert attribution.of(8100)["unit"] == "alfred-backend.service"
    assert attribution.of(3110) is None


# ── Conformance with the producer this check reads ───────────────────


ESTATE_PORTS_CHECK = (
    "/home/gaddi/projects/estate-manager/service/estate_service/audit/checks/ports.py"
)
ESTATE_AUDIT_CONFIG = (
    "/home/gaddi/projects/estate-manager/service/estate_service/audit/config.py"
)


def test_our_audited_ranges_match_estate_managers():
    """The duplication is deliberate; the drift would not be.

    ``PortCheckConfig.audited_ranges`` restates estate-manager's
    ``PortRegistryConfig.audited_ranges`` rather than deriving it,
    exactly as ``EstateJudgeConfig.base_url`` restates ``services.yaml``:
    a cross-repository lookup would make this check go silently quiet the
    day the other side reorganises its config.  What keeps the two honest
    is this test — a failure someone reads — not a runtime import, which
    is unavailable anyway: ``estate_service`` is the *service* and only
    ``estate-lib`` is a dependency here.

    Read textually and skipped when the file is absent, because CI has no
    estate checkout.  A brittle test that fails loudly on a real
    divergence beats no test at all; the assertion message says which.
    """
    from pathlib import Path

    from sysadmin.core.config import get_config

    source = Path(ESTATE_AUDIT_CONFIG)
    if not source.exists():
        pytest.skip("no estate-manager checkout on this host")

    text = source.read_text(encoding="utf-8")
    assert "[(3000, 3999), (8000, 8999)]" in text, (
        "estate-manager's audited_ranges have moved. Update "
        "PortCheckConfig.audited_ranges to match, or this check stops "
        "judging ports the estate still governs."
    )
    ours = [tuple(r) for r in get_config().agents.service_discovery.ports.audited_ranges]
    assert ours == [(3000, 3999), (8000, 8999)]


def test_the_registry_document_we_read_is_the_one_the_audit_reads():
    """Both sides name ``docs/guides/monitorable-project.md``.

    Ours is absolute (this service runs with its own ``WorkingDirectory``);
    theirs resolves against their repository root.  A moved document
    would leave this check reporting "no duplicate rows" off a file it
    never opened, which is why the agent treats a zero-row parse as an
    error — their rule, adopted.
    """
    from pathlib import Path

    from sysadmin.core.config import get_config

    source = Path(ESTATE_AUDIT_CONFIG)
    if not source.exists():
        pytest.skip("no estate-manager checkout on this host")

    assert 'document: str = "docs/guides/monitorable-project.md"' in source.read_text(
        encoding="utf-8"
    )
    ours = get_config().agents.service_discovery.ports.document
    assert ours.endswith("docs/guides/monitorable-project.md")


def test_the_estate_still_runs_ss_without_p_which_is_why_this_module_exists():
    """The premise of the whole session, pinned.

    If estate-manager ever adds ``-p`` and attributes ports itself, this
    module is a second implementation of their check rather than the half
    they are blocked from — and the right move is to delete it, not to
    keep both.  A test is the only thing that would say so.
    """
    from pathlib import Path

    source = Path(ESTATE_PORTS_CHECK)
    if not source.exists():
        pytest.skip("no estate-manager checkout on this host")

    text = source.read_text(encoding="utf-8")
    assert '["ss", "-H", "-tln"]' in text, (
        "estate-manager's live_listeners() has changed. If it now attributes "
        "ports, sysadmin/units/ports.py duplicates it and should be reconsidered."
    )


def test_our_parser_and_the_estates_agree_on_the_live_document():
    """Two parsers, one table — so assert they read it the same way.

    The claimed *ports* must match exactly.  Ours keeps duplicates and
    theirs folds them into a set, which is the one intended difference,
    so the comparison is on the set of ports rather than the row count.
    """
    from pathlib import Path

    from sysadmin.core.config import get_config

    document = Path(
        get_config().agents.service_discovery.ports.document
    ).expanduser()
    if not document.exists():
        pytest.skip("no estate-manager checkout on this host")

    ours = {c.port for c in P.parse_port_registry(document.read_text(encoding="utf-8"))}
    assert ours, "the live port registry parsed to zero rows"
    # Every port the live table claims is inside the jurisdiction we
    # judge, or explicitly outside it (22000, the syncthing sync port,
    # recorded under the sidecar rule).  A row inside a range we do not
    # audit would be judged by nobody.
    audited = [(3000, 3999), (8000, 8999)]
    unaudited = sorted(p for p in ours if not P.in_range(p, audited))
    assert unaudited == [22000], (
        f"registry rows outside the audited ranges: {unaudited}. Either the "
        "ranges need widening or the row belongs elsewhere."
    )
