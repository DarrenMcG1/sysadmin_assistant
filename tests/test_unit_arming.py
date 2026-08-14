"""Armed orphans — SNAG-ESTATE-001's durable half.

The snag is not a detection failure.  ``GET /api/units/status`` had
``personal-assistant-idle-watcher.service`` classified ``orphaned``, with
the dead path and the cause in plain English, eight days before anyone
looked — while it restart-looped 34,517 times and stalled the kernel.
There was even an open alert: ``Unmonitored systemd units: 17 findings``.

What no surface said is *which two of the seventeen were live*.  These
tests cover the two things that changed: the sweep now measures whether
an orphan is armed, and the agent gives each armed one its own alert row.

The scan half builds a real unit directory under ``tmp_path`` and parses
real unit text, following ``test_units.py`` — the arming signals are
filesystem facts, and a mocked filesystem would only agree with the code.
The numbers in the fixtures are the ones measured on this box on
2026-08-14, not tidy invented ones.
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.units.agent import (
    ALERT_TITLE,
    ARMED_TITLE_PREFIX,
    ServiceDiscoveryAgent,
    armed_alert_message,
    armed_alert_severity,
    armed_alert_title,
)
from sysadmin.units.recommendations import recommendations_for_scan
from sysadmin.units.scan import (
    ORPHANED,
    ProjectRef,
    UnitFinding,
    discover_units,
    enablement_links,
    parse_timespan,
    restart_is_bounded,
    scan_units,
)

# ── The arithmetic ───────────────────────────────────────────────────
#
# The rule is not "does the unit declare a start limit".  It is whether
# the limit it has can ever be reached.


def test_the_personalassistant_shape_is_unbounded():
    """The exact unit that restart-looped 34,517 times.

    ``Restart=always``, ``RestartSec=10``, no ``StartLimit*`` of its own,
    so systemd's defaults apply: 5 starts in 10 seconds.  Starts ten
    seconds apart can never put five inside that window, so the limiter
    never fires and the unit never enters ``failed``.
    """
    assert restart_is_bounded("always", 10.0, None, None) is False


def test_ticktick_sync_db_is_worse_and_still_unbounded():
    """RestartSec=60 — one start a minute against a ten-second window."""
    assert restart_is_bounded("always", 60.0, None, None) is False


def test_a_bare_restart_always_is_bounded_which_the_naive_rule_gets_wrong():
    """The false positive that makes "no StartLimitBurst=" the wrong test.

    A unit declaring nothing but ``Restart=always`` restarts every 100ms,
    so five starts fit in the ten-second window easily and the loop
    terminates.  Flagging it would put most of this box's units in a
    critical alert on the first run.
    """
    assert restart_is_bounded("always", None, None, None) is True


def test_the_session_39_fix_passes_its_own_test():
    """``sysadmin.service``: StartLimitIntervalSec=600 against RestartSec=10.

    Five starts span 40 seconds, comfortably inside 600, so the loop is
    terminal — which is the entire reason ``sysadmin-failed.service`` can
    ever fire.  If this test ever fails, that unit has been edited into
    the invisible state it was written to escape.
    """
    assert restart_is_bounded("always", 10.0, 600.0, 5) is True


@pytest.mark.parametrize("interval,burst", [(0.0, 5), (10.0, 0)])
def test_a_disabled_limiter_is_unbounded(interval, burst):
    """systemd documents either value at zero as "rate limiting off"."""
    assert restart_is_bounded("always", 10.0, interval, burst) is False


@pytest.mark.parametrize("restart", [None, "", "no", "No"])
def test_a_unit_that_does_not_restart_is_bounded(restart):
    assert restart_is_bounded(restart, 10.0, None, None) is True


def test_an_unreadable_restart_sec_does_not_accuse():
    """Not knowing is not a finding.

    ``parse_timespan`` returns ``None`` for anything it cannot read, and
    the caller then falls back to systemd's default rather than assuming
    the worst.  A false positive here sends someone to rewrite a unit
    file that is fine — the direction ``monitor/collation.py`` settled on
    for the same class of question.
    """
    assert parse_timespan("every so often") is None
    assert restart_is_bounded("always", parse_timespan("every so often"), None, None)


@pytest.mark.parametrize(
    "text,seconds",
    [
        ("10", 10.0),
        ("100ms", 0.1),
        ("5s", 5.0),
        ("2min", 120.0),
        ("1min 30s", 90.0),
        ("1h", 3600.0),
        ("infinity", float("inf")),
    ],
)
def test_timespans_parse_the_forms_systemd_writes(text, seconds):
    assert parse_timespan(text) == seconds


@pytest.mark.parametrize("text", ["", None, "bogus", "10 bogus", "10s junk"])
def test_unparseable_timespans_return_none_rather_than_a_guess(text):
    assert parse_timespan(text) is None


def test_a_partly_parseable_value_is_refused_whole():
    """Reading the half that parsed would be a number nobody wrote."""
    assert parse_timespan("10s !!") is None


# ── Enablement, read off the filesystem ──────────────────────────────


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


ORPHAN_TEXT = (
    "[Unit]\nDescription=Retired thing\n\n"
    "[Service]\nType=simple\nWorkingDirectory=/gone/project\n"
    "ExecStart=/gone/project/run.sh\nRestart=always\nRestartSec=10\n\n"
    "[Install]\nWantedBy=multi-user.target\n"
)


def test_an_enable_symlink_is_what_makes_a_unit_enabled(tmp_path):
    """``systemctl enable`` writes into ``<target>.wants/`` and nothing else.

    Reading that directory answers "will systemd start this" exactly,
    with no subprocess — the same trade ``discover_units`` already makes
    with ``is_symlink()`` for distro ownership.  Checked against
    ``systemctl is-enabled`` on every unit on this box (2026-08-14): they
    agreed.
    """
    unit = _write(tmp_path / "thing.service", ORPHAN_TEXT)
    assert enablement_links(tmp_path) == set()

    wants = tmp_path / "multi-user.target.wants"
    wants.mkdir()
    (wants / "thing.service").symlink_to(unit)
    assert enablement_links(tmp_path) == {"thing.service"}


def test_requires_directories_count_too(tmp_path):
    unit = _write(tmp_path / "thing.service", ORPHAN_TEXT)
    requires = tmp_path / "multi-user.target.requires"
    requires.mkdir()
    (requires / "thing.service").symlink_to(unit)
    assert enablement_links(tmp_path) == {"thing.service"}


def test_a_dangling_enable_symlink_still_counts(tmp_path):
    """The state ``removal_command``'s docstring warns about.

    Deleting a unit file without disabling it first leaves the link
    behind.  Matching on the link *name* rather than following it to a
    target means the sweep still sees what systemd still sees.
    """
    wants = tmp_path / "multi-user.target.wants"
    wants.mkdir()
    (wants / "ghost.service").symlink_to(tmp_path / "not-here.service")
    assert enablement_links(tmp_path) == {"ghost.service"}


def test_discover_units_marks_the_enabled_one(tmp_path):
    user = tmp_path / "user"
    unit = _write(user / "armed.service", ORPHAN_TEXT)
    _write(user / "dormant.service", ORPHAN_TEXT)
    wants = user / "default.target.wants"
    wants.mkdir()
    (wants / "armed.service").symlink_to(unit)

    units, _ = discover_units(user, None, str(tmp_path))
    by_name = {u.name: u for u in units}
    assert by_name["armed.service"].enabled is True
    assert by_name["dormant.service"].enabled is False


def test_the_restart_keys_are_parsed_off_the_file(tmp_path):
    units, _ = discover_units(
        _write(tmp_path / "u" / "x.service", ORPHAN_TEXT).parent,
        None,
        str(tmp_path),
    )
    unit = units[0]
    assert unit.restart == "always"
    assert unit.restart_sec == 10.0
    assert unit.restart_bounded is False


def test_start_limit_keys_are_read_from_unit_or_service(tmp_path):
    """systemd moved them to ``[Unit]`` in v229 and still accepts ``[Service]``.

    A unit written before that move would otherwise read as declaring no
    limit at all, and be reported as a runaway on the strength of where
    someone put a line.
    """
    body = (
        "[Unit]\nDescription=x\n{unit_keys}\n\n"
        "[Service]\nExecStart=/bin/true\nRestart=always\nRestartSec=10\n"
        "{service_keys}\n"
    )
    modern = _write(
        tmp_path / "a" / "modern.service",
        body.format(
            unit_keys="StartLimitIntervalSec=600\nStartLimitBurst=5", service_keys=""
        ),
    )
    legacy = _write(
        tmp_path / "b" / "legacy.service",
        body.format(
            unit_keys="", service_keys="StartLimitIntervalSec=600\nStartLimitBurst=5"
        ),
    )
    for path in (modern, legacy):
        units, _ = discover_units(path.parent, None, str(tmp_path))
        assert units[0].restart_bounded is True, path.name


# ── Arming is a property of orphans only ─────────────────────────────


def _estate(tmp_path, *, enabled: bool, working_dir: str, restart: str = "") -> Path:
    user = tmp_path / "user"
    unit = _write(
        user / "thing.service",
        "[Unit]\nDescription=Thing\n\n"
        f"[Service]\nType=simple\nWorkingDirectory={working_dir}\n"
        f"ExecStart={working_dir}/run.sh\n{restart}\n\n"
        "[Install]\nWantedBy=default.target\n",
    )
    if enabled:
        wants = user / "default.target.wants"
        wants.mkdir(exist_ok=True)
        (wants / "thing.service").symlink_to(unit)
    return user


def _only_finding(user_dir: Path, tmp_path: Path, projects=()) -> UnitFinding:
    scan = scan_units(user_dir, None, str(tmp_path), list(projects), set())
    assert len(scan.findings) == 1
    return scan.findings[0]


def test_an_enabled_orphan_is_armed(tmp_path):
    finding = _only_finding(
        _estate(tmp_path, enabled=True, working_dir="/gone"), tmp_path
    )
    assert finding.category == ORPHANED
    assert finding.enabled is True
    assert finding.armed is True


def test_a_disabled_orphan_is_debt_not_a_fault(tmp_path):
    """Four of this box's six orphans, and why they get no alert.

    They carry ``Restart=always`` with an unreachable start limit — the
    PersonalAssistant shape exactly — and are harmless only because
    someone disabled them.  Nothing starts them, so the roll-up is the
    right home; the shape is still recorded on the finding.
    """
    finding = _only_finding(
        _estate(
            tmp_path,
            enabled=False,
            working_dir="/gone",
            restart="Restart=always\nRestartSec=10",
        ),
        tmp_path,
    )
    assert finding.category == ORPHANED
    assert finding.armed is False
    assert finding.restart_bounded is False


def test_a_live_projects_enabled_unit_is_not_armed(tmp_path):
    """Arming is orphan-only.  Every healthy service on this box is
    enabled, and most of them restart unboundedly — an ``armed`` that
    meant "enabled" would alert on all of them."""
    project = tmp_path / "live-project"
    project.mkdir()
    finding = _only_finding(
        _estate(tmp_path, enabled=True, working_dir=str(project)),
        tmp_path,
        projects=[ProjectRef(name="live-project", path=str(project))],
    )
    assert finding.category != ORPHANED
    assert finding.enabled is True
    assert finding.armed is False


def test_a_folded_oneshot_is_armed_by_its_timer(tmp_path):
    """The service is disabled and the schedule still runs.

    A ``Type=oneshot`` is started *by* its timer, so reading only the
    service's own enablement would report a live schedule as dormant.
    The finding is keyed on the service — which holds the paths — with
    the timer named in ``monitor_unit``.
    """
    user = tmp_path / "user"
    _write(
        user / "job.service",
        "[Unit]\nDescription=Job\n\n"
        "[Service]\nType=oneshot\nWorkingDirectory=/gone\nExecStart=/gone/job.sh\n",
    )
    timer = _write(
        user / "job.timer",
        "[Unit]\nDescription=Job timer\n\n"
        "[Timer]\nOnCalendar=daily\n\n[Install]\nWantedBy=timers.target\n",
    )
    wants = user / "timers.target.wants"
    wants.mkdir()
    (wants / "job.timer").symlink_to(timer)

    finding = _only_finding(user, tmp_path)
    assert finding.unit == "job.service"
    assert finding.monitor_unit == "job.timer"
    assert finding.armed is True


def test_the_reason_says_whether_anything_starts_it(tmp_path):
    """``reason`` is what the drill-down and the advice both render."""
    armed = _only_finding(
        _estate(tmp_path / "a", enabled=True, working_dir="/gone",
                restart="Restart=always\nRestartSec=10"),
        tmp_path,
    )
    dormant = _only_finding(
        _estate(tmp_path / "b", enabled=False, working_dir="/gone"), tmp_path
    )
    assert "enabled" in armed.reason
    assert "for ever" in armed.reason
    assert "disabled, so nothing starts it" in dormant.reason


def test_the_armed_count_is_a_scalar_in_the_blob(tmp_path):
    """Not ``len()`` over the stored list, which is truncated at 200."""
    scan = scan_units(
        _estate(tmp_path, enabled=True, working_dir="/gone"), None, str(tmp_path), [], set()
    )
    assert scan.as_findings_blob()["armed_count"] == 1
    assert len(scan.armed) == 1


def test_armed_orphans_rank_first_in_the_advice(tmp_path):
    findings = [
        UnitFinding(unit="dormant.service", scope="system", category=ORPHANED,
                    path="/etc/systemd/system/dormant.service"),
        UnitFinding(unit="armed.service", scope="system", category=ORPHANED,
                    path="/etc/systemd/system/armed.service", enabled=True),
    ]
    recs = recommendations_for_scan(findings)
    assert [r.unit for r in recs] == ["armed.service", "dormant.service"]


# ── The alert family ─────────────────────────────────────────────────


def _armed(unit="garmin-sync.service", scope="user", bounded=True, **kw) -> UnitFinding:
    return UnitFinding(
        unit=unit,
        scope=scope,
        category=ORPHANED,
        path=f"/home/gaddi/.config/systemd/{scope}/{unit}",
        dead_path="/home/gaddi/projects/PersonalAssistant",
        reason="WorkingDirectory is gone",
        enabled=True,
        restart=None if bounded else "always",
        restart_bounded=bounded,
        **kw,
    )


def _scan(*findings) -> SimpleNamespace:
    return SimpleNamespace(
        findings=list(findings), armed=[f for f in findings if f.armed]
    )


def _session(open_rows=(), swept=0):
    """A session that answers the family's two statements, in order.

    ``_maintain_armed_alerts`` runs exactly one SELECT (the open rows)
    and one UPDATE (the sweep), so a two-element ``side_effect`` is an
    assertion about the shape of the work as well as a fixture.
    """
    select_result = MagicMock()
    select_result.scalars.return_value = list(open_rows)
    update_result = MagicMock()
    update_result.rowcount = swept

    session = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock(side_effect=[select_result, update_result])
    return session


def _open(title, severity):
    return SimpleNamespace(title=title, severity=severity)


@pytest.fixture
def agent():
    a = ServiceDiscoveryAgent()
    a.raise_alert = AsyncMock()
    a.resolve_alerts = AsyncMock(return_value=1)
    return a


async def test_the_title_names_the_unit_which_is_the_whole_change(agent):
    """``Unmonitored systemd units: 17 findings`` could not.

    It was open, accurate and unread for eight days while two of those
    seventeen restart-looped 52,178 times.  A count cannot name the thing
    that is on fire, and the tray fingerprints on ``{severity}:{title}``
    — so a shared title also means one armed orphan masks the next.
    """
    finding = _armed()
    session = _session()
    await agent._maintain_armed_alerts(session, _scan(finding))

    title = agent.raise_alert.await_args.kwargs["title"]
    assert title == armed_alert_title(finding)
    assert "garmin-sync.service" in title
    assert "(user)" in title


async def test_scope_is_part_of_the_identity(agent):
    """``deadlock-api-ingest.service`` exists in both scopes here, running
    two different binaries.  One row must not answer for the other."""
    user = _armed(unit="deadlock-api-ingest.service", scope="user")
    system = _armed(unit="deadlock-api-ingest.service", scope="system")
    assert armed_alert_title(user) != armed_alert_title(system)

    session = _session()
    counts = await agent._maintain_armed_alerts(session, _scan(user, system))
    assert counts["raised"] == 2


async def test_an_unbounded_restart_loop_is_critical(agent):
    """The only severity the tray leaves on screen (``transient=False``).

    The reported failure in SNAG-ESTATE-001 was not being at the machine.
    A transient toast in an empty room is the miss whatever its severity,
    and this fault does not stop on its own.
    """
    assert armed_alert_severity(_armed(bounded=False)) == "critical"


async def test_an_armed_orphan_that_cannot_loop_is_a_warning(agent):
    """It fails on every trigger, which is news but not an emergency."""
    assert armed_alert_severity(_armed(bounded=True)) == "warning"


async def test_the_message_carries_the_command_that_fixes_it(agent):
    message = armed_alert_message(_armed())
    assert "systemctl --user disable --now garmin-sync.service" in message
    # disable before rm, or the enablement symlink is stranded and
    # systemd warns about a dangling link on every daemon-reload.
    assert message.index("disable") < message.index("rm ")


async def test_a_standing_fault_writes_one_row_not_one_per_sweep(agent):
    """The sweep runs four times a day.  Without dedup that is the
    1,664-row pile-up this repository has already been through."""
    finding = _armed()
    session = _session(open_rows=[_open(armed_alert_title(finding), "warning")])

    counts = await agent._maintain_armed_alerts(session, _scan(finding))
    assert counts == {"armed": 1, "raised": 0, "escalated": 0, "held": 1, "resolved": 0}
    agent.raise_alert.assert_not_awaited()


async def test_the_still_true_row_is_protected_from_the_sweep(agent):
    """The rule SNAG-AGENT-006 turned on: exclude what the run *judged*.

    Against a set of what it *raised*, a deduplicating family writes
    nothing on run two, has its still-true row swept, re-raises on run
    three — a flip-flop that clears the tray's fingerprint every turn, so
    one fault notifies on every poll.  That is louder than the pile-up
    *and* reads as a recovery.
    """
    finding = _armed()
    session = _session(open_rows=[_open(armed_alert_title(finding), "warning")])
    await agent._maintain_armed_alerts(session, _scan(finding))

    sweep = session.execute.await_args_list[-1].args[0]
    compiled = str(sweep.compile(compile_kwargs={"literal_binds": True}))
    assert "NOT IN" in compiled.upper()
    assert armed_alert_title(finding) in compiled


async def test_a_fault_that_clears_resolves_once(agent):
    """Disabled, deleted, or the project came back — the statement does
    not care which, which is the point.  A per-item loop can only observe
    recovery for items it still sees, and a deleted one is never seen."""
    session = _session(swept=1)
    counts = await agent._maintain_armed_alerts(session, _scan())
    assert counts["resolved"] == 1
    agent.raise_alert.assert_not_awaited()


async def test_escalation_resolves_the_quiet_row_and_raises_a_loud_one(agent):
    """Never an in-place severity change.

    The tray has already suppressed ``warning:<title>``; updating the row
    keeps that fingerprint, so the escalation is recorded in the database
    and never spoken — the one thing an escalation is for.
    """
    finding = _armed(bounded=False)
    session = _session(open_rows=[_open(armed_alert_title(finding), "warning")])

    counts = await agent._maintain_armed_alerts(session, _scan(finding))
    assert counts["escalated"] == 1
    agent.resolve_alerts.assert_awaited_once_with(session, armed_alert_title(finding))
    assert agent.raise_alert.await_args.kwargs["severity"] == "critical"


async def test_a_critical_row_is_never_quietly_downgraded(agent):
    """Softening ``Restart=`` does not fix a unit whose start job fails.

    ``step_for`` refuses the de-escalation, so the row stays loud until
    the orphan is actually disabled or removed.
    """
    finding = _armed(bounded=True)
    session = _session(open_rows=[_open(armed_alert_title(finding), "critical")])

    counts = await agent._maintain_armed_alerts(session, _scan(finding))
    assert counts == {"armed": 1, "raised": 0, "escalated": 0, "held": 1, "resolved": 0}


async def test_the_sweep_cannot_reach_the_rolled_up_alert(agent):
    """Two families, one agent.  A second owner of a lifecycle closes a
    row while the first still holds it true."""
    session = _session()
    await agent._maintain_armed_alerts(session, _scan())

    compiled = str(
        session.execute.await_args_list[-1]
        .args[0]
        .compile(compile_kwargs={"literal_binds": True})
    )
    assert ARMED_TITLE_PREFIX in compiled
    assert ALERT_TITLE not in compiled


async def test_the_family_ignores_alert_threshold(agent):
    """``alert_threshold`` is patience for accumulated debt — twenty
    findings on a detector's first run should not shout.  An armed orphan
    is not debt; one of them is worth saying."""
    session = _session()
    counts = await agent._maintain_armed_alerts(session, _scan(_armed()))
    assert counts["raised"] == 1


async def test_the_details_carry_the_evidence_and_the_remedy(agent):
    session = _session()
    await agent._maintain_armed_alerts(session, _scan(_armed(bounded=False)))

    details = agent.raise_alert.await_args.kwargs["details"]
    assert details["source"] == "unit_sweep"
    assert details["enabled"] is True
    assert details["restart_bounded"] is False
    assert "disable --now" in details["remedy"]


async def test_the_rollup_says_how_many_are_speaking_for_themselves(agent):
    """A reader of one alert must be able to tell the other exists."""
    scan = SimpleNamespace(
        findings=[],
        armed=[_armed()],
        count={ORPHANED: 6}.get,
        monitored_count=21,
        units_scanned=44,
    )
    message = agent._alert_message(scan)
    assert "6 orphaned" in message
    assert "1 of them enabled and failing now" in message
