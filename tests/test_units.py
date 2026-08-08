"""Tests for the systemd unit sweep (Session 26 Tier 1).

The module under test is pure, so every test here builds a real unit
directory under ``tmp_path`` and parses real unit-file text.  That is
deliberate: Sessions 23 and 24 both shipped bugs that the mocked tests
could not see because the mocks agreed with the code rather than with
the data.  Nothing in this file is mocked except ``path_exists``, and
only where the point of the test is a path that does not exist.

The fixtures reproduce the shapes actually found on this box on
2026-08-07 — a ``curl``-based oneshot with no project path, a unit using
``%h``, a unit installed in both scopes — rather than tidy invented ones.
"""

from pathlib import Path

import pytest

from sysadmin.units.scan import (
    HOST,
    ORPHANED,
    UNMONITORED,
    ProjectRef,
    UnitFile,
    classify_units,
    discover_units,
    expand_specifiers,
    fold_timers,
    load_unit,
    match_unit,
    normalise,
    parse_unit_text,
    project_refs,
    scan_units,
    wired_units,
)

# ── Parsing ──────────────────────────────────────────────────────────


def test_repeated_keys_are_all_kept():
    """ethernet-optimise.service has two ExecStart lines; both count."""
    parsed = parse_unit_text(
        "[Service]\n"
        "Type=oneshot\n"
        "ExecStart=/usr/sbin/ethtool --set-eee eno1 eee off\n"
        "ExecStart=/usr/sbin/ethtool -K eno1 tso off\n"
    )
    execs = [v for k, v in parsed["Service"] if k == "ExecStart"]
    assert len(execs) == 2


def test_comments_and_blank_lines_ignored():
    parsed = parse_unit_text(
        "# a comment\n"
        "; another\n"
        "\n"
        "[Unit]\n"
        "Description=Real\n"
        "# Description=Fake\n"
    )
    assert parsed["Unit"] == [("Description", "Real")]


def test_line_continuation_is_joined():
    parsed = parse_unit_text(
        "[Service]\nExecStart=/usr/bin/thing \\\n    --flag \\\n    --other\n"
    )
    assert parsed["Service"] == [("ExecStart", "/usr/bin/thing --flag --other")]


def test_keys_before_any_section_are_dropped():
    parsed = parse_unit_text("Stray=value\n[Unit]\nDescription=x\n")
    assert parsed == {"Unit": [("Description", "x")]}


def test_value_containing_equals_is_kept_whole():
    """Environment=DATABASE_URL=postgresql://... must not lose the tail."""
    parsed = parse_unit_text("[Service]\nEnvironment=DB=postgresql://h/db\n")
    assert parsed["Service"] == [("Environment", "DB=postgresql://h/db")]


@pytest.mark.parametrize(
    ("value", "home", "expected"),
    [
        ("%h/projects/Thing", "/home/gaddi", "/home/gaddi/projects/Thing"),
        ("/opt/thing", "/home/gaddi", "/opt/thing"),
        # System scope passes home="" — %h stays unexpanded rather than
        # becoming a plausible-looking wrong path.
        ("%h/projects/Thing", "", "%h/projects/Thing"),
        ("100%%free", "/home/gaddi", "100%free"),
        # Specifiers we do not understand are left alone deliberately.
        ("/srv/%i/data", "/home/gaddi", "/srv/%i/data"),
    ],
)
def test_specifier_expansion(value, home, expected):
    assert expand_specifiers(value, home) == expected


def test_load_unit_reads_paths_from_exec_and_working_directory(tmp_path):
    unit = tmp_path / "ticktick-sync.service"
    unit.write_text(
        "[Unit]\nDescription=TickTick Task Sync\n"
        "[Service]\nType=oneshot\n"
        "WorkingDirectory=/home/gaddi/projects/MCP\n"
        "ExecStart=/home/gaddi/projects/MCP/venv/bin/python3 "
        "/home/gaddi/projects/MCP/sync_ticktick.py\n"
        "User=gaddi\n"
        "[Install]\nWantedBy=multi-user.target\n"
    )
    loaded = load_unit(unit, "system", "")

    assert loaded.description == "TickTick Task Sync"
    assert loaded.is_oneshot
    assert loaded.working_directory == "/home/gaddi/projects/MCP"
    assert "/home/gaddi/projects/MCP/sync_ticktick.py" in loaded.exec_paths
    assert loaded.user == "gaddi"
    assert loaded.static is False  # has [Install]


def test_load_unit_strips_exec_prefix_characters(tmp_path):
    unit = tmp_path / "x.service"
    unit.write_text("[Service]\nExecStart=-/opt/app/run.sh --once\n")
    assert load_unit(unit, "system", "").exec_paths == ("/opt/app/run.sh",)


def test_load_unit_ignores_non_path_arguments(tmp_path):
    """sportsanalyser-pipeline runs curl against a URL — no project path."""
    unit = tmp_path / "sportsanalyser-pipeline.service"
    unit.write_text(
        "[Service]\nType=oneshot\n"
        "ExecStart=/usr/bin/curl -sf -X POST http://localhost:8200/api/v1/jobs/run_all\n"
    )
    loaded = load_unit(unit, "user", "/home/gaddi")
    assert loaded.exec_paths == ("/usr/bin/curl",)
    assert loaded.working_directory is None


def test_load_unit_expands_home_specifier(tmp_path):
    unit = tmp_path / "personal-assistant-worker.service"
    unit.write_text(
        "[Service]\nWorkingDirectory=%h/projects/PersonalAssistant\n"
        "ExecStart=%h/projects/PersonalAssistant/scripts/run-worker.sh\n"
    )
    loaded = load_unit(unit, "user", "/home/gaddi")
    assert loaded.working_directory == "/home/gaddi/projects/PersonalAssistant"
    assert loaded.exec_paths == (
        "/home/gaddi/projects/PersonalAssistant/scripts/run-worker.sh",
    )


def test_unreadable_unit_parses_as_empty(tmp_path):
    """A unit we cannot read must not abort the sweep."""
    loaded = load_unit(tmp_path / "missing.service", "system", "")
    assert loaded.name == "missing.service"
    assert loaded.exec_paths == ()


def test_timer_defaults_to_same_stem_service(tmp_path):
    timer = tmp_path / "paccache.timer"
    timer.write_text("[Timer]\nOnCalendar=weekly\n")
    assert load_unit(timer, "system", "").triggers == "paccache.service"


def test_timer_honours_explicit_unit(tmp_path):
    timer = tmp_path / "cleanup.timer"
    timer.write_text("[Timer]\nOnCalendar=daily\nUnit=other-job.service\n")
    assert load_unit(timer, "system", "").triggers == "other-job.service"


# ── Discovery ────────────────────────────────────────────────────────


def _write(directory: Path, name: str, body: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(body)
    return path


def test_discovery_skips_symlinks_and_templates(tmp_path):
    """The distro filter: enable installs a symlink, humans write files."""
    system = tmp_path / "system"
    packaged = tmp_path / "usr" / "bluetooth.service"
    _write(tmp_path / "usr", "bluetooth.service", "[Service]\nExecStart=/x\n")

    _write(system, "mine.service", "[Service]\nExecStart=/opt/mine\n")
    _write(system, "getty@.service", "[Service]\nExecStart=/sbin/agetty\n")
    (system / "dbus-org.bluez.service").symlink_to(packaged)

    units, excluded = discover_units(None, system, "")

    assert [u.name for u in units] == ["mine.service"]
    assert sorted(excluded) == ["dbus-org.bluez.service", "getty@.service"]


def test_discovery_ignores_non_unit_files(tmp_path):
    system = tmp_path / "system"
    _write(system, "real.service", "[Service]\nExecStart=/x\n")
    _write(system, "notes.txt", "hello")
    (system / "real.service.d").mkdir()

    units, _ = discover_units(None, system, "")
    assert [u.name for u in units] == ["real.service"]


def test_discovery_tolerates_missing_directories(tmp_path):
    units, excluded = discover_units(tmp_path / "nope", tmp_path / "also-nope", "")
    assert units == [] and excluded == []


def test_system_scope_leaves_home_specifier_unexpanded(tmp_path):
    """A system unit's %h is the User='s home, which we will not guess."""
    system = tmp_path / "system"
    _write(system, "s.service", "[Service]\nWorkingDirectory=%h/thing\n")
    units, _ = discover_units(None, system, "/home/gaddi")
    # Not a testable claim, so recorded as no claim at all.
    assert units[0].working_directory is None


# ── Matching ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SportsAnalyser", "sportsanalyser"),
        ("sports_analyser", "sportsanalyser"),
        ("sports-analyser", "sportsanalyser"),
        ("sysadmin_assistant", "sysadminassistant"),
    ],
)
def test_normalise_folds_the_three_naming_styles(raw, expected):
    assert normalise(raw) == expected


def _unit(name, scope="user", **kw) -> UnitFile:
    return UnitFile(name=name, scope=scope, path=f"/units/{name}", **kw)


def test_path_match_beats_name_match():
    """A unit whose path is under a project wins even if the name suggests
    a different one — the naming here is unreliable, the paths are not."""
    projects = [
        ProjectRef("Alfred", "/home/gaddi/projects/Alfred"),
        ProjectRef("alfred-glance", "/home/gaddi/projects/apps/alfred-glance"),
    ]
    unit = _unit(
        "alfred-glance-helper.service",
        working_directory="/home/gaddi/projects/Alfred",
    )
    match = match_unit(unit, projects, path_exists=lambda p: True)
    assert match.matched_by == "path"
    assert match.project.name == "Alfred"


def test_path_match_prefers_the_deepest_project():
    """apps/ is a category directory; a project inside it must win."""
    projects = [
        ProjectRef("apps", "/home/gaddi/projects/apps"),
        ProjectRef("venture-assistant", "/home/gaddi/projects/apps/venture-assistant"),
    ]
    unit = _unit(
        "v.service", working_directory="/home/gaddi/projects/apps/venture-assistant"
    )
    assert match_unit(unit, projects, path_exists=lambda p: True).project.name == (
        "venture-assistant"
    )


def test_name_match_catches_a_unit_with_no_project_path():
    """The real sportsanalyser-pipeline case: ExecStart is /usr/bin/curl."""
    projects = [ProjectRef("SportsAnalyser", "/home/gaddi/projects/apps/SportsAnalyser")]
    unit = _unit("sportsanalyser-pipeline.service", exec_paths=("/usr/bin/curl",))
    match = match_unit(unit, projects, path_exists=lambda p: True)
    assert match.matched_by == "name"
    assert match.project.name == "SportsAnalyser"


def test_name_match_resolves_the_alfred_ambiguity():
    """``alfred-inference`` prefix-matches ``alfred`` but not
    ``alfred-glance`` — the longest-wins rule never has to guess."""
    projects = [
        ProjectRef("Alfred", "/home/gaddi/projects/Alfred"),
        ProjectRef("alfred-glance", "/home/gaddi/projects/apps/alfred-glance"),
    ]
    unit = _unit("alfred-inference.service", exec_paths=("/usr/bin/llama-server",))
    assert match_unit(unit, projects, path_exists=lambda p: True).project.name == "Alfred"


def test_name_match_prefers_the_longer_project_name():
    projects = [
        ProjectRef("venture", "/p/venture"),
        ProjectRef("venture-assistant", "/p/venture-assistant"),
    ]
    unit = _unit("venture-assistant-worker.service")
    match = match_unit(unit, projects, path_exists=lambda p: True)
    assert match.project.name == "venture-assistant"


def test_name_match_requires_a_prefix_not_a_substring():
    """A shared word is not a match; ``deadlock-api-ingest`` has no project."""
    projects = [ProjectRef("ImbaBots", "/p/ImbaBots")]
    unit = _unit("deadlock-api-ingest.service", exec_paths=("/opt/deadlock/bin",))
    assert match_unit(unit, projects, path_exists=lambda p: True).project is None


def test_dead_working_directory_is_recorded():
    unit = _unit(
        "garmin-sync.service",
        working_directory="/home/gaddi/projects/PersonalAssistant",
    )
    match = match_unit(unit, [], path_exists=lambda p: False)
    assert match.dead_paths == ("/home/gaddi/projects/PersonalAssistant",)


def test_missing_exec_binary_is_not_a_dead_path():
    """Only WorkingDirectory is a hard claim — a missing /usr/bin binary
    has a dozen causes that are not 'the project moved'."""
    unit = _unit("x.service", exec_paths=("/usr/bin/gone",))
    assert match_unit(unit, [], path_exists=lambda p: False).dead_paths == ()


# ── Timer folding ────────────────────────────────────────────────────


def test_oneshot_service_folds_its_timer():
    units = [
        _unit("paccache.service", scope="system", service_type="oneshot"),
        _unit("paccache.timer", scope="system", triggers="paccache.service"),
    ]
    folded, timer_for = fold_timers(units)
    assert folded == {"system:paccache.timer"}
    assert timer_for == {"system:paccache.service": "paccache.timer"}


def test_long_running_service_does_not_fold_a_timer():
    """A Type=simple service stays active, so the service is the right
    thing to watch and the timer is a separate concern."""
    units = [
        _unit("app.service", service_type="simple"),
        _unit("app.timer", triggers="app.service"),
    ]
    folded, timer_for = fold_timers(units)
    assert folded == set() and timer_for == {}


def test_folding_does_not_cross_scopes():
    units = [
        _unit("job.service", scope="system", service_type="oneshot"),
        _unit("job.timer", scope="user", triggers="job.service"),
    ]
    folded, _ = fold_timers(units)
    assert folded == set()


# ── Classification ───────────────────────────────────────────────────


LIVE = ProjectRef("Alfred", "/p/Alfred", "active")
ARCHIVED = ProjectRef("PersonalAssistant", "/p/archive/PersonalAssistant", "archived")
DORMANT = ProjectRef("daiy", "/p/daiy", "dormant")


def test_wired_unit_produces_no_finding():
    units = [_unit("alfred-backend.service", working_directory="/p/Alfred")]
    findings = classify_units(
        units, [LIVE], {"user:alfred-backend.service"}, path_exists=lambda p: True
    )
    assert findings == []


def test_wiring_the_timer_covers_the_oneshot_service():
    """config.yaml records alfred-evaluate.timer; the service is covered."""
    units = [
        _unit("alfred-evaluate.service", service_type="oneshot",
              working_directory="/p/Alfred"),
        _unit("alfred-evaluate.timer", triggers="alfred-evaluate.service"),
    ]
    findings = classify_units(
        units, [LIVE], {"user:alfred-evaluate.timer"}, path_exists=lambda p: True
    )
    assert findings == []


def test_unmonitored_project_unit():
    units = [_unit("alfred-worker.service", working_directory="/p/Alfred")]
    (finding,) = classify_units(units, [LIVE], set(), path_exists=lambda p: True)
    assert finding.category == UNMONITORED
    assert finding.project == "Alfred"
    assert finding.monitor_unit == "alfred-worker.service"


def test_unmonitored_oneshot_names_the_timer_and_reports_once():
    units = [
        _unit("alfred-job.service", service_type="oneshot",
              working_directory="/p/Alfred"),
        _unit("alfred-job.timer", triggers="alfred-job.service"),
    ]
    findings = classify_units(units, [LIVE], set(), path_exists=lambda p: True)
    assert len(findings) == 1
    assert findings[0].unit == "alfred-job.service"
    assert findings[0].monitor_unit == "alfred-job.timer"


def test_dead_path_is_an_orphan_even_when_the_name_matches():
    units = [
        _unit(
            "personal-assistant-worker.service",
            working_directory="/p/PersonalAssistant",
        )
    ]
    (finding,) = classify_units(
        units, [ARCHIVED], set(), path_exists=lambda p: False
    )
    assert finding.category == ORPHANED
    assert finding.dead_path == "/p/PersonalAssistant"
    assert "does not exist" in finding.reason


def test_archived_project_unit_is_an_orphan_even_with_a_live_path():
    units = [
        _unit(
            "personalassistant-backend.service",
            scope="system",
            working_directory="/p/archive/PersonalAssistant",
        )
    ]
    (finding,) = classify_units(units, [ARCHIVED], set(), path_exists=lambda p: True)
    assert finding.category == ORPHANED
    assert "archived" in finding.reason


def test_dormant_project_unit_is_unmonitored_not_orphaned():
    """Dormant is resting on purpose and may be woken; archived is not."""
    units = [_unit("daiy-backend.service", working_directory="/p/daiy")]
    (finding,) = classify_units(units, [DORMANT], set(), path_exists=lambda p: True)
    assert finding.category == UNMONITORED


def test_unit_with_no_project_is_a_host_unit():
    units = [
        _unit(
            "pgbackrest-backup.service",
            scope="system",
            service_type="oneshot",
            description="pgBackRest daily backup",
        ),
        _unit("pgbackrest-backup.timer", scope="system",
              triggers="pgbackrest-backup.service"),
    ]
    (finding,) = classify_units(units, [LIVE], set(), path_exists=lambda p: True)
    assert finding.category == HOST
    assert finding.monitor_unit == "pgbackrest-backup.timer"
    assert finding.project is None


def test_hand_started_oneshot_is_flagged_manual():
    """Oneshot, no timer, no [Install] — nothing schedules it, so
    'not monitored' is not a defect."""
    units = [_unit("one-off.service", service_type="oneshot", static=True)]
    (finding,) = classify_units(units, [], set(), path_exists=lambda p: True)
    assert finding.manual is True


def test_same_unit_name_in_both_scopes_is_two_findings():
    """deadlock-api-ingest is installed twice, running two binaries."""
    units = [
        _unit("deadlock-api-ingest.service", scope="user",
              exec_paths=("/home/g/.local/share/deadlock-api-ingest/bin",)),
        _unit("deadlock-api-ingest.service", scope="system",
              exec_paths=("/opt/deadlock-api-ingest/bin",)),
    ]
    findings = classify_units(units, [], set(), path_exists=lambda p: True)
    assert {f.scope for f in findings} == {"user", "system"}


def test_wiring_one_scope_does_not_cover_the_other():
    units = [
        _unit("deadlock-api-ingest.service", scope="user"),
        _unit("deadlock-api-ingest.service", scope="system"),
    ]
    findings = classify_units(
        units, [], {"user:deadlock-api-ingest.service"}, path_exists=lambda p: True
    )
    assert [f.scope for f in findings] == ["system"]


def test_findings_are_ordered_worst_first():
    units = [
        _unit("host.service"),
        _unit("gap.service", working_directory="/p/Alfred"),
        _unit("dead.service", working_directory="/p/gone"),
    ]
    findings = classify_units(
        units, [LIVE], set(), path_exists=lambda p: p == "/p/Alfred"
    )
    assert [f.category for f in findings] == [ORPHANED, UNMONITORED, HOST]


# ── The whole sweep ──────────────────────────────────────────────────


def _estate(tmp_path) -> tuple[Path, Path]:
    """A miniature of the real box, including its awkward cases."""
    user = tmp_path / "user"
    system = tmp_path / "system"
    home = str(tmp_path / "home")

    _write(user, "alfred-backend.service",
           f"[Service]\nWorkingDirectory={tmp_path}/projects/Alfred\n"
           f"ExecStart={tmp_path}/projects/Alfred/run.sh\n")
    _write(user, "alfred-job.service",
           f"[Service]\nType=oneshot\nWorkingDirectory={tmp_path}/projects/Alfred\n"
           f"ExecStart=/usr/bin/uv run job\n")
    _write(user, "alfred-job.timer", "[Timer]\nOnCalendar=daily\n")
    _write(user, "pa-worker.service",
           f"[Service]\nWorkingDirectory={home}/projects/PersonalAssistant\n")
    _write(system, "pgbackrest-backup.service",
           "[Unit]\nDescription=pgBackRest daily backup\n"
           "[Service]\nType=oneshot\nExecStart=/usr/bin/pgbackrest --stanza=x\n")
    _write(system, "pgbackrest-backup.timer", "[Timer]\nOnCalendar=daily\n")

    (tmp_path / "projects" / "Alfred").mkdir(parents=True)
    return user, system


def test_scan_counts_are_exhaustive(tmp_path):
    """scanned == monitored + folded + findings.  A count that sums is a
    count a reader can audit; the first version of this inferred
    'monitored' and reported 20 where the truth was 12."""
    user, system = _estate(tmp_path)
    projects = [ProjectRef("Alfred", str(tmp_path / "projects" / "Alfred"))]

    scan = scan_units(
        user, system, str(tmp_path / "home"), projects,
        {"user:alfred-backend.service"},
    )

    assert scan.units_scanned == 6
    assert scan.monitored_count == 1
    assert scan.timers_folded == 2
    assert len(scan.findings) == 3
    assert (
        scan.monitored_count + scan.timers_folded + len(scan.findings)
        == scan.units_scanned
    )


def test_scan_classifies_the_miniature_estate(tmp_path):
    user, system = _estate(tmp_path)
    projects = [ProjectRef("Alfred", str(tmp_path / "projects" / "Alfred"))]
    scan = scan_units(user, system, str(tmp_path / "home"), projects, set())

    by_unit = {f.unit: f for f in scan.findings}
    assert by_unit["alfred-backend.service"].category == UNMONITORED
    assert by_unit["alfred-job.service"].category == UNMONITORED
    assert by_unit["alfred-job.service"].monitor_unit == "alfred-job.timer"
    assert by_unit["pa-worker.service"].category == ORPHANED
    assert by_unit["pgbackrest-backup.service"].category == HOST
    assert by_unit["pgbackrest-backup.service"].monitor_unit == (
        "pgbackrest-backup.timer"
    )


def test_findings_blob_groups_by_category_and_truncates(tmp_path):
    user, system = _estate(tmp_path)
    projects = [ProjectRef("Alfred", str(tmp_path / "projects" / "Alfred"))]
    scan = scan_units(user, system, str(tmp_path / "home"), projects, set())

    blob = scan.as_findings_blob(limit=1)
    assert set(blob) >= {ORPHANED, UNMONITORED, HOST, "units_scanned"}
    assert len(blob[UNMONITORED]) == 1
    # count() reads the in-memory list, never the truncated blob — the
    # Session 24 lesson.
    assert scan.count(UNMONITORED) == 2


# ── Config plumbing ──────────────────────────────────────────────────


class _Endpoint:
    def __init__(self, unit, user=False):
        self.systemd_unit = unit
        self.user = user


class _Project:
    def __init__(self, backend=None, frontend=None):
        self.backend = backend
        self.frontend = frontend


class _ProjectsConfig:
    def __init__(self, projects):
        self.projects = projects


class _Service:
    def __init__(self, unit, user=False):
        self.systemd_unit = unit
        self.user = user


def test_wired_units_reads_every_declared_service():
    """One source. This used to read projects.yaml as well, and a sweep
    that consulted only one of the two reported the other half of the
    estate as unmonitored."""
    wired = wired_units([
        _Service("alfred-backend.service", user=True),
        _Service("alfred-frontend.service", user=True),
        _Service("postgresql.service"),
        _Service("alfred-evaluate.timer", user=True),
    ])
    assert wired == {
        "user:alfred-backend.service",
        "user:alfred-frontend.service",
        "system:postgresql.service",
        "user:alfred-evaluate.timer",
    }


def test_wired_units_keys_include_scope():
    """Without scope in the key, wiring the user unit would silently
    cover the system unit of the same name."""
    wired = wired_units([_Service("x.service", user=True)])
    assert wired == {"user:x.service"}
    assert "system:x.service" not in wired


def test_project_refs_from_dicts_and_rows():
    class _Row:
        project_name = "Alfred"
        project_path = "/p/Alfred"
        findings = {"status": "dormant"}

    refs = project_refs(
        [{"project_name": "A", "project_path": "/p/A", "findings": {"status": "archived"}}]
    )
    assert refs[0].status == "archived" and refs[0].is_live is False

    refs = project_refs([_Row()])
    assert refs[0].status == "dormant" and refs[0].is_live is True


def test_project_refs_skips_incomplete_entries():
    assert project_refs([{"project_name": "no-path"}, {"project_path": "/p"}]) == []
