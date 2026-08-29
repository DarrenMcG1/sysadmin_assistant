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

from sysadmin.core.models.alert import Alert
from sysadmin.units import ports as P  # noqa: N812
from sysadmin.units.agent import (
    PORT_ALERT_SEVERITY,
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


def _runtime(user=(), system=(), problems=()):
    """Stand in for the two ``systemd/transient`` directories.

    Injected by ``_observe`` **by default**, so no test in this file
    reads the box it happens to run on.  Without that, a developer who
    had ``systemd-run`` a unit sharing a fixture's name would see a
    different answer from CI for a reason nothing in the test names.
    """
    names = {P.SCOPE_USER: frozenset(user), P.SCOPE_SYSTEM: frozenset(system)}
    return lambda: (names, tuple(problems))


def _observe(stdout=LIVE_SS, cgroups=None, runtime=None, **kwargs):
    table = LIVE_CGROUPS if cgroups is None else cgroups
    return P.observe_listeners(
        runner=_runner(stdout=stdout, **kwargs),
        cgroup_reader=lambda pid: table.get(pid),
        runtime_reader=_runtime() if runtime is None else runtime,
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


#: The live cgroup of ``kdeconnectd`` (pid 12483) on 2026-08-27, copied
#: verbatim from ``/proc``.  Two colons sit *inside* the path, which is
#: the shape ``_unit_from_cgroup`` used to read from the wrong end.
DBUS_ACTIVATED_CGROUP = (
    "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
    "app-dbus\\x2d:1.2\\x2dorg.kde.kdeconnect.slice/"
    "dbus-:1.2-org.kde.kdeconnect@0.service"
)


def test_the_cgroup_path_is_taken_from_the_first_two_colons_not_the_last():
    """``cgroup(5)`` is ``hierarchy:controllers:path`` and only the path may hold a colon.

    A D-Bus activated unit has one, and ``rpartition(":")`` returns the
    tail of the *unit name* rather than the path — dropping the ``dbus-``
    prefix and, with it, the ``/user@1000.service/`` that decides the
    scope.  Both halves are asserted because the second is the
    load-bearing one: scope is part of a unit's identity here
    (``f"{scope}:{unit}"``), so a user unit read as ``system`` is a
    different unit as far as ``wrong_unit`` is concerned.

    Falsified by restoring ``line.rpartition(":")[2]``, which gives
    ``("1.2-org.kde.kdeconnect@0.service", "system")``.
    """
    unit, scope = P._unit_from_cgroup(DBUS_ACTIVATED_CGROUP)
    assert unit == "dbus-:1.2-org.kde.kdeconnect@0.service"
    assert scope == "user"


def test_the_scope_half_is_witnessed_where_the_unit_name_survives():
    """A colon in the *slice* and none in the leaf isolates the scope.

    The specimen above breaks the unit name and the scope together, so
    it cannot say which half a candidate fix repaired.  Here
    ``rpartition`` returns ``…kde.kdeconnect.slice/kdeconnectd.service``
    — whose last segment is already the right unit — and loses only the
    ``/user@1000.service/`` the scope test reads.  A fix that stripped a
    ``dbus-`` prefix, or matched the unit with a regex, would pass the
    specimen above and fail here.

    Falsified by ``line.rpartition(":")[2]``, which gives
    ``("kdeconnectd.service", "system")``.
    """
    unit, scope = P._unit_from_cgroup(
        "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
        "app-dbus\\x2d:1.2\\x2dorg.kde.kdeconnect.slice/kdeconnectd.service"
    )
    assert unit == "kdeconnectd.service"
    assert scope == "user"


def test_a_colon_free_path_is_unmoved_by_the_split():
    """The two shapes that have always worked must keep working.

    The fix changes which field is taken, not what is done with it, so
    the control is the pair the module was written against — a system
    unit and a user one, neither carrying a colon in its path.
    """
    assert P._unit_from_cgroup("0::/system.slice/sysadmin.service") == (
        "sysadmin.service",
        "system",
    )
    assert P._unit_from_cgroup(
        "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
        "alfred-backend.service"
    ) == ("alfred-backend.service", "user")


def test_a_cgroup_v1_line_with_no_path_field_is_still_read():
    """A line with fewer than two colons is not split at all.

    cgroup v1 hierarchies print ``N:controller:/path`` and v2 prints
    ``0::/path``, so two colons is the normal case; the guard exists so
    a malformed or truncated line degrades to "no attribution" rather
    than raising ``IndexError`` inside the sweep.
    """
    assert P._unit_from_cgroup("/system.slice/sysadmin.service") == (
        "sysadmin.service",
        "system",
    )
    assert P._unit_from_cgroup("0::/user.slice/user-1000.slice/session-3") == (
        None,
        None,
    )


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


def _session(open_titles=(), swept=0, message="x", details=None):
    """The two statements ``_maintain_port_alerts`` issues, in order.

    The SELECT hands back **rows**, not titles.  It handed back titles
    until 2026-08-28: ``SNAG-AGENT-009`` made the family refresh a held
    row's ``message`` and ``details``, which it cannot do without the row
    — so a fake still answering with strings would model a database this
    code no longer talks to, and the dedup would look broken because the
    stand-in was.  ``tests/test_alert_dedup.py`` documents the same trap
    from the other side, where a fake that could not tell a projection
    from a row read made ``SNAG-AGENT-007``'s fix read as a regression.

    The rows are kept on the session as ``open_rows`` so a test can ask
    what the refresh did to them.
    """
    rows = [
        Alert(
            agent="service_discovery",
            severity=PORT_ALERT_SEVERITY,
            title=title,
            message=message,
            details=dict(details or {}),
        )
        for title in open_titles
    ]
    select_result = MagicMock()
    select_result.scalars.return_value = rows
    update_result = MagicMock()
    update_result.rowcount = swept

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=[select_result, update_result])
    session.open_rows = rows
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


async def test_a_held_row_whose_holder_moved_is_rewritten(agent):
    """SNAG-AGENT-009 — the title is the port, so the sentence must move.

    ``Port collision on 8100`` is keyed on the port and nothing else
    (Session 26c rule 4), which is what makes the row survive a change of
    holder — and what made it survive with a message naming a unit that
    let the port go hours earlier.  The drive that demonstrated the
    mechanism used this family exactly: raise naming ``alpha``, judge
    again with ``beta``, and both ``message`` and the ``findings`` blob
    still said ``alpha``.
    """
    session = _session(
        open_titles=[port_alert_title(8100)],
        message="8100 is held by user:alpha.service",
        details={"port": 8100, "findings": [{"holder": "user:alpha.service"}]},
    )
    result = await agent._maintain_port_alerts(
        session,
        _report(
            P.PortFinding(
                port=8100,
                kind=P.WRONG_UNIT,
                summary="8100 is held by user:beta.service",
            )
        ),
    )

    agent.raise_alert.assert_not_awaited()
    assert result["held"] == 1 and result["raised"] == 0 and result["refreshed"] == 1
    row = session.open_rows[0]
    assert row.message == "8100 is held by user:beta.service"
    # Both halves, or half the row is still lying — the blob is what the
    # drive found still naming alpha, so it is asserted as well as the
    # sentence.
    assert [f["summary"] for f in row.details["findings"]] == [
        "8100 is held by user:beta.service"
    ]
    assert row.details["source"] == "port_check"


async def test_a_held_row_that_still_says_the_same_thing_is_not_rewritten(agent):
    """The gate.  A standing collision nobody has touched is not news twice."""
    finding = _collision(8100)
    session = _session(
        open_titles=[port_alert_title(8100)],
        message=finding.summary,
        details={
            "port": 8100,
            "kinds": [finding.kind],
            "findings": [finding.as_dict()],
            "source": "port_check",
        },
    )
    result = await agent._maintain_port_alerts(session, _report(finding))
    assert result["held"] == 1 and result["refreshed"] == 0


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


# ── What the sweep knew, beside who it named (SNAG-ESTATE-009) ───────


def _seen_blob(**over):
    """A successful sweep: one unit, one dev server, two it could not name."""
    return {
        "ok": True,
        "unit_ports": {"user:alfred-backend.service": [8100]},
        "transient_ports": {"user:app-code-oss-26348.scope": [3110]},
        "unattributed_ports": [5432, 8601],
        **over,
    }


def test_the_four_reasons_holder_is_none_are_four_readings():
    """``of()`` collapses four states; :meth:`reading` separates them.

    The founding measurement, and it is the sibling of the collapse
    Session 57 fixed one field over: ``of(5432)`` and ``of(8110)`` are
    both ``None`` on the live sweep, and one of them means *the sweep
    looked straight at this port* while the other means *the sweep ran
    before this listener started*.  That second one is what
    ``SNAG-ESTATE-009`` is about.
    """
    a = P.attribution_from_blob(_seen_blob(), "2026-08-29T20:34:14+00:00")
    assert a.reading(8100)["reading"] == "held"
    assert a.reading(3110)["reading"] == "transient"
    assert a.reading(5432)["reading"] == "unattributed"
    assert a.reading(8110)["reading"] == "unswept"
    # The two the fix separates are still one answer to `of`, which asks
    # a different question and is right to.
    assert a.of(5432) is None and a.of(8110) is None


def test_every_reading_carries_the_evidences_age():
    """A reading with no date is a claim with no evidence behind it.

    ``details['holder']['observed_at']`` is the age the entry's "Why P3"
    bullet says already ships — and it is unreachable for exactly the
    rows that need it, because ``holder`` is ``None`` there.
    """
    a = P.attribution_from_blob(_seen_blob(), "2026-08-29T20:34:14+00:00")
    for port in (8100, 3110, 5432, 8110):
        assert a.reading(port)["observed_at"] == "2026-08-29T20:34:14+00:00"


def test_a_failed_observation_is_unknown_and_never_unswept():
    """The ``ok`` gate, and it is the half that is easy to miss.

    ``observe_listeners`` failing returns the error and **no** listeners,
    so ``unattributed_ports`` serialises as ``[]``.  Read as evidence
    that would make every breached port ``unswept`` — a confident
    statement about a sweep that never looked, which is
    ``ports_checked``'s rule rebuilt inside the fix for
    ``ports_checked``'s rule.
    """
    a = P.attribution_from_blob(
        {"ok": False, "error": "ss: command not found", "unattributed_ports": []}
    )
    assert a.unattributed is None
    assert a.reading(5432)["reading"] == "unknown"
    assert a.reading(8110)["reading"] == "unknown"


def test_a_sweep_predating_the_key_cannot_answer():
    """51 stored sweeps have no ``ports`` block and 0 have a partial one.

    The partial case is unreachable on this box today and handled
    anyway: absent evidence is ``unknown``, never a confident
    ``unswept``.

    **The first version of this test passed against the mutation it
    exists to catch.**  It drove ``{"unit_ports": …}`` — a blob with no
    ``ok`` either — so the ``ok`` gate returned before the missing-key
    branch was ever reached, and making that branch answer
    ``frozenset()`` left the test green.  It asserted the right value
    for the wrong reason, which is what the mutation drive is for.  The
    successful-sweep-with-no-key case is what isolates it.
    """
    # A sweep that ran fine and predates the key: the observation is
    # sound and the question is still unanswerable.
    partial = P.attribution_from_blob({"ok": True, "unit_ports": {"u": [8100]}})
    assert partial.unattributed is None
    assert partial.reading(8110)["reading"] == "unknown"
    assert partial.reading(8100)["reading"] == "held"
    # And the no-`ok` case, which is a different gate.
    assert P.attribution_from_blob({"unit_ports": {"u": [8100]}}).unattributed is None
    assert P.attribution_from_blob(None).reading(8110)["reading"] == "unknown"
    assert P.PortAttribution().reading(8110) == {"reading": "unknown", "observed_at": None}


def test_a_bool_in_the_list_is_not_port_one():
    """``isinstance(True, int)`` is ``True``.

    A bool would land as port 1 and read a live listener as
    unattributable — ``judge_audit_findings`` rule 3's trap, one blob
    over.
    """
    a = P.attribution_from_blob(_seen_blob(unattributed_ports=[True, 5432, "x", None]))
    assert a.unattributed == frozenset({5432})
    assert a.reading(1)["reading"] == "unswept"


# ── Conformance with the producer this check reads ───────────────────


ESTATE_PORTS_CHECK = (
    "/home/gaddi/projects/estate-manager/service/estate_service/audit/checks/ports.py"
)
ESTATE_AUDIT_CONFIG = (
    "/home/gaddi/projects/estate-manager/service/estate_service/audit/config.py"
)
#: The block their **live** audit reads.  Their code default and this
#: file are two statements of one fact, pinned on their side by
#: ``test_the_shipped_ranges_and_the_code_default_agree`` — which is
#: exactly the kind of guarantee this module may not lean on, so both
#: are read here.
ESTATE_AUDIT_YAML = "/home/gaddi/projects/estate-manager/service/audit.yaml"

#: What both repositories govern, as of estate-manager's ``e5c639c``
#: (2026-08-27, their ADR-0056).  Stated once here and compared against
#: three places: our config, their yaml, and their code default.
AUDITED_RANGES = [(1000, 1999), (3000, 3999), (8000, 8999)]


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

    **This is the test that fired**, on a clean tree, the day they
    widened the band (``SNAG-PORT-001``).  It is the whole justification
    for the copy, so it is worth stating what it caught and what it did
    not: it caught the *drift*, and it said nothing about what widening
    would change here, which had to be driven live.

    **Both of their statements are read.** Their ``audit.yaml`` is what
    the running audit parses; their ``config.py`` default is what a bare
    ``PortRegistryConfig()`` gives, and their own test pins the two
    together.  Leaning on that test is the cross-repository lookup this
    copy exists to avoid — one repository's guard is not this
    repository's evidence — so a divergence between their own two halves
    is a failure here too, and the message says which half moved.

    Read textually and skipped when the files are absent, because CI has
    no estate checkout.  A brittle test that fails loudly on a real
    divergence beats no test at all; the assertion message says which.
    """
    from pathlib import Path

    import yaml

    from sysadmin.core.config import get_config

    source = Path(ESTATE_AUDIT_CONFIG)
    shipped = Path(ESTATE_AUDIT_YAML)
    if not source.exists() or not shipped.exists():
        pytest.skip("no estate-manager checkout on this host")

    ours = [tuple(r) for r in get_config().agents.service_discovery.ports.audited_ranges]
    assert ours == AUDITED_RANGES

    literal = "[" + ", ".join(f"({lo}, {hi})" for lo, hi in AUDITED_RANGES) + "]"
    assert literal in source.read_text(encoding="utf-8"), (
        f"estate-manager's PortRegistryConfig default is no longer {literal}. "
        "Update PortCheckConfig.audited_ranges to match, or this check stops "
        "judging ports the estate still governs."
    )

    theirs = yaml.safe_load(shipped.read_text(encoding="utf-8"))
    running = [tuple(r) for r in theirs["port_registry"]["audited_ranges"]]
    assert running == AUDITED_RANGES, (
        f"estate-manager's shipped audit.yaml governs {running}, not "
        f"{AUDITED_RANGES}. That is the band their audit actually runs on, "
        "so it is the one this check must match."
    )


def test_the_pure_default_matches_the_config_default():
    """``judge_ports``' fallback is a second statement of the same jurisdiction.

    :mod:`sysadmin.units.ports` is pure below ``observe_listeners`` and
    may not read ``config.yaml``, so it cannot derive what it governs —
    and every production caller passes the config value anyway, which is
    what makes the fallback invisible until it is wrong.  Pinned rather
    than trusted, ``syslog_priority`` against ``journal.PRIORITY_MAP``'s
    treatment: import where you can, pin where you cannot.

    Not the same assertion as the one above.  That one pins this
    repository against **estate-manager**; this one pins this repository
    against **itself**, and a widening applied to ``config.py`` alone
    would leave every test that builds a bare ``judge_ports`` call
    judging the old band while production judged the new one — green in
    both places and wrong in one.
    """
    from sysadmin.core.config import PortCheckConfig

    assert list(P.DEFAULT_AUDITED_RANGES) == [
        tuple(r) for r in PortCheckConfig().audited_ranges
    ]


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
    # judge, or explicitly outside it.  **One row is**, and it is a
    # third-party daemon the estate hosts rather than a service either
    # repository wrote: 22000, the syncthing sync port, recorded under
    # the sidecar rule.  A row inside a range nobody audits is judged by
    # nobody, which is what this assertion exists to catch, and this one
    # is *known* to be — recorded in the row's own text and as their
    # SNAG-ESTATE-070 — so moving it is their decision to ask for and
    # not ours to take.
    #
    # It read ``[1883, 22000]`` until 2026-08-27, when estate-manager
    # widened their band to cover 1000–1999 and this repository followed
    # (SNAG-PORT-001).  1716 joined the table the same day and is inside
    # the new band, so it never appeared here.
    #
    # The band is read from config rather than restated: a literal here
    # would let this test and ``PortCheckConfig`` drift apart, which is
    # the same defect one repository smaller.
    audited = [tuple(r) for r in get_config().agents.service_discovery.ports.audited_ranges]
    unaudited = sorted(p for p in ours if not P.in_range(p, audited))
    assert unaudited == [22000], (
        f"registry rows outside the audited ranges {audited}: {unaudited}. "
        "Either the ranges need widening or the row belongs elsewhere."
    )


# ── SNAG-PORT-003: transience is observed, never read off the name ────


#: Real names from this box on 2026-08-28.  ``app-steam`` and the
#: appimagekit one were *holding ports* while the entry said the
#: population was one, and neither carries a colon — so both fixes
#: ``SNAG-PORT-003`` proposed (a ``dbus-`` prefix, a ``:N.N`` pattern)
#: leave them reading as stable identities.
RUNTIME_SERVICE = "app-steam@455b2e51e70244d98b817b19364641d8.service"
RUNTIME_DBUS = "dbus-:1.2-org.kde.kdeconnect@0.service"
RUNTIME_ESCAPED = "app-code\\x2doss@3ec0681d85b34536883ab69ca8b5671a.service"

_STEAM_SS = 'LISTEN 0 4096 0.0.0.0:27036 0.0.0.0:* users:(("steam",pid=9001,fd=3))\n'


def _held_by(unit, scope="user", pid=9001):
    prefix = (
        "0::/user.slice/user-1000.slice/user@1000.service/app.slice/"
        if scope == "user"
        else "0::/system.slice/"
    )
    return {pid: prefix + unit + "\n"}


def test_a_runtime_created_service_is_transient_though_its_name_says_nothing():
    """The family ``SNAG-PORT-003`` was closed on, and the shape it missed.

    ``app-steam@455b2e51….service`` is a ``.service`` with no colon, so
    the suffix rule and both name-based fixes the entry proposed leave it
    alone.  It held four ports on the day the entry claimed a population
    of one.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_SERVICE),
        runtime=_runtime(user=[RUNTIME_SERVICE]),
    )
    listener = report.listeners[0]
    assert listener.unit == RUNTIME_SERVICE
    assert listener.runtime_created is True
    assert listener.transient is True


def test_the_same_name_is_not_transient_when_no_manager_created_it():
    """The discriminating half: the name alone decides nothing.

    Without this the test above passes for a rule that simply widened to
    ``return True``, which is the gutting ``SNAG-PORT-003``'s own controls
    were written to refuse.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_SERVICE),
        runtime=_runtime(user=[]),
    )
    assert report.listeners[0].runtime_created is False
    assert report.listeners[0].transient is False


def test_a_hand_written_service_is_left_alone_though_a_stale_sibling_is_listed():
    """The negative control, with the directory non-empty so it can fail."""
    report = _observe(runtime=_runtime(user=[RUNTIME_SERVICE, RUNTIME_DBUS]))
    units = {x.unit: x for x in report.listeners if x.unit}
    assert units["alfred-backend.service"].transient is False
    assert units["sysadmin.service"].transient is False


def test_the_escaped_name_matches_the_filename_without_unescaping():
    """systemd writes one escaped name into both places, measured.

    The obvious worry is that the cgroup path and the transient filename
    escape differently, which would make every ``app-*`` unit a miss.  On
    this box they are byte-identical — ``\\x2d`` and all — so the
    comparison is a plain string test and this pins that it stays one.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_ESCAPED),
        runtime=_runtime(user=[RUNTIME_ESCAPED]),
    )
    assert "\\x2d" in (report.listeners[0].unit or "")
    assert report.listeners[0].transient is True


def test_the_scope_suffix_still_decides_when_the_directory_does_not_name_it():
    """``init.scope`` is the witness that this had to be additive.

    Measured 2026-08-28: ``init.scope`` reports ``Transient=yes`` from
    both managers and appears in **neither** transient directory.  A fix
    that replaced the suffix test with the listing — the obvious reading
    of "ask systemd instead of guessing" — would stop recognising it, so
    the listing is added and never substituted.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by("init.scope"),
        runtime=_runtime(user=[]),
    )
    assert report.listeners[0].runtime_created is False
    assert report.listeners[0].transient is True


def test_the_directory_is_chosen_by_the_listener_scope():
    """A user unit named only in the system directory is not stamped.

    Both directories are populated here — ``/run/systemd/transient`` held
    ``dbus-:1.2-org.kde.kameleon.qmk.helper@0.service`` on 2026-08-28 — so
    a reader that merged them would call a user unit transient on a
    system manager's say-so.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_SERVICE, scope="user"),
        runtime=_runtime(system=[RUNTIME_SERVICE]),
    )
    assert report.listeners[0].scope == P.SCOPE_USER
    assert report.listeners[0].transient is False


def test_a_system_scope_listener_is_stamped_from_the_system_directory():
    """The other half of the routing, or the test above passes for a reader
    that never stamps a system unit at all."""
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_SERVICE, scope="system"),
        runtime=_runtime(system=[RUNTIME_SERVICE]),
    )
    assert report.listeners[0].scope == P.SCOPE_SYSTEM
    assert report.listeners[0].transient is True


def test_an_unreadable_directory_degrades_to_the_suffix_rule():
    """Fails toward noise, deliberately.

    Claiming transience on a failed read would suppress a genuine
    collision on the strength of not having looked — the estate judge's
    rule 2.  So the observation is simply absent and the sweep behaves as
    it did before Session 108.
    """
    report = _observe(
        stdout=_STEAM_SS,
        cgroups=_held_by(RUNTIME_SERVICE),
        runtime=_runtime(problems=["/run/user/1000/systemd/transient would not list"]),
    )
    assert report.ok
    assert report.listeners[0].runtime_created is False
    assert report.listeners[0].transient is False


def test_the_directories_are_listed_once_per_sweep_not_once_per_listener():
    """Two listeners in one report must not disagree about the same box."""
    calls = []

    def counting():
        calls.append(1)
        return {P.SCOPE_USER: frozenset(), P.SCOPE_SYSTEM: frozenset()}, ()

    report = _observe(runtime=counting)
    assert len(report.listeners) > 1
    assert len(calls) == 1


def test_transient_reads_no_filesystem_so_a_stored_observation_keeps_its_answer():
    """The property stays pure, which is what the stamp buys.

    ``judge_ports`` is pure below :func:`observe_listeners` and this module
    says so at the top.  Deriving transience in the property would put an
    impure read underneath that line and let the same listener answer two
    ways at two moments.
    """
    listener = P.Listener(port=1, unit=RUNTIME_SERVICE, scope="user")
    assert listener.transient is False
    assert P.Listener(port=1, unit=RUNTIME_SERVICE, runtime_created=True).transient


def test_runtime_unit_names_reports_the_directory_it_could_not_list():
    """A problem is returned, never swallowed — ``ports_checked``'s rule."""

    def explode(_directory):
        raise PermissionError("nope")

    names, problems = P.runtime_unit_names(lister=explode)
    assert names[P.SCOPE_USER] == frozenset()
    assert names[P.SCOPE_SYSTEM] == frozenset()
    assert len(problems) == 2
    assert all("PermissionError" in x for x in problems)


def test_runtime_unit_names_reads_the_system_directory_by_its_constant():
    from pathlib import Path

    seen = []

    def lister(directory):
        seen.append(directory)
        return []

    P.runtime_unit_names(lister=lister)
    assert P.SYSTEM_TRANSIENT_DIR in seen
    assert P.SYSTEM_TRANSIENT_DIR == Path("/run/systemd/transient")


def test_a_transient_holder_stays_out_of_unit_ports_and_lands_in_the_other_map():
    """The consequence the fix exists for, at the map the consumers read.

    Live on 2026-08-28 this moved ``user:dbus-:1.2-org.kde.kdeconnect@0.service``
    out of ``unit_ports`` — where the estate judge would have read it as a
    stable holder and judged a breach at ``warning`` rather than at
    ``TRANSIENT_HOLDER_SEVERITY``.
    """
    report = _observe(
        stdout='LISTEN 0 4096 0.0.0.0:1716 0.0.0.0:* users:(("kdeconnectd",pid=9001,fd=3))\n',
        cgroups=_held_by(RUNTIME_DBUS),
        runtime=_runtime(user=[RUNTIME_DBUS]),
    )
    blob = P.PortReport(listeners=report.listeners, audited_ranges=((1000, 1999),))
    assert blob.unit_ports(audited_only=True) == {}
    assert blob.transient_ports() == {f"user:{RUNTIME_DBUS}": [1716]}


def test_the_port_family_states_its_rung_once():
    """``SNAG-ESTATE-010``, at the family whose population is empty.

    One rung means :func:`may_quieten_in_place` can only ever answer
    ``False`` here, so nothing observable changes — which is exactly why
    the wiring is worth pinning rather than trusting. What must hold is
    that the raise and the held branch name **the same** rung: the whole
    entry is a family gaining a quieter rung while its held branch went
    on knowing nothing about severity, and two literals free to disagree
    is how that happens again.
    """
    from pathlib import Path

    source = Path("sysadmin/units/agent.py").read_text()
    body = source.split("async def _maintain_port_alerts", 1)[1]
    body = body.split("\n    async def ", 1)[0]
    assert body.count("PORT_ALERT_SEVERITY") == 2
    assert 'severity="warning"' not in body


def test_a_held_port_row_is_offered_the_rung_the_family_judged():
    """The refresh is handed a rung at all — the wiring, not its effect.

    Asserted at the call rather than at the row, because the effect is
    nil by construction: ``warning`` is not the floor, so the predicate
    refuses it and the column is untouched. A test asserting the column
    would pass identically against a caller that passed nothing, which
    is the behaviour being fixed.
    """
    import inspect

    from sysadmin.units.agent import ServiceDiscoveryAgent

    source = inspect.getsource(ServiceDiscoveryAgent._maintain_port_alerts)
    refresh = source.split("self.refresh_alert(", 1)[1].split(")", 1)[0]
    assert "severity=PORT_ALERT_SEVERITY" in refresh
