"""The restart-limit family — SNAG-UNITS-002.

17 of the 20 hand-written units on this box that declare ``Restart=``
have a start limit their own restart cadence can never reach, so a crash
loop never enters ``failed``, no ``OnFailure=`` hook can fire, and
``systemctl is-failed`` reports nothing wrong.  That is the estate-wide
form of SNAG-ESTATE-001, whose two PersonalAssistant units restart-looped
52,178 times in exactly this state.

The detection already existed: :func:`restart_is_bounded` was written for
the armed-orphan family in Session 46 and every finding has carried
``restart_bounded`` since.  What did not exist was a surface naming the
units, because **11 of the 13 are ``monitored``** and
:func:`classify_units` drops monitored units before they become findings.
The question was answerable for six units on the box and invisible for
every live service on it.

Two things these tests hold that nothing else can:

* the **advice actually fixes the unit** — every suggested window is fed
  back through :func:`restart_is_bounded` and must come out bounded.  A
  remedy that clears a symptom without fixing the fault is the trap
  ``ALTER DATABASE … REFRESH COLLATION VERSION`` set for the collation
  family, and it is cheap to build here by accident;
* the family stays **outside** ``actionable`` and outside the bucket sum,
  which is what stops 13 latent risks reading as 13 new gaps to wire up
  and tripping the roll-up alert's threshold on their own.

Fixtures use the shapes measured on this box on 2026-08-15, not tidy
invented ones.
"""

from pathlib import Path

import pytest

from sysadmin.core.contracts import UnitScanSummary
from sysadmin.units.recommendations import (
    KIND_ORDER,
    recommendations_for_scan,
    suggested_start_limit_interval,
)
from sysadmin.units.scan import (
    DEFAULT_START_LIMIT_BURST,
    ORPHANED,
    RESTART_UNBOUNDED,
    ProjectRef,
    restart_is_bounded,
    scan_units,
)

# The live population, 2026-08-15: (RestartSec, what declares it)
LIVE_SHAPES = [
    (5.0, "alfred-inference, estate-manager-api, venture-chat*"),
    (10.0, "venture-assistant-backend, sportsanalyser-*, sysadmin-tray"),
    (60.0, "ticktick-sync-db"),
]


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _unit(
    tmp_path: Path,
    name: str,
    *,
    working_dir: str,
    restart: str = "Restart=always",
    restart_sec: str = "RestartSec=10",
    start_limit: str = "",
) -> Path:
    user = tmp_path / "user"
    _write(
        user / name,
        f"[Unit]\nDescription={name}\n{start_limit}\n\n"
        f"[Service]\nType=simple\nWorkingDirectory={working_dir}\n"
        f"ExecStart={working_dir}/run.sh\n{restart}\n{restart_sec}\n\n"
        "[Install]\nWantedBy=default.target\n",
    )
    return user


# ── The suggestion has to work ───────────────────────────────────────


@pytest.mark.parametrize("restart_sec,who", LIVE_SHAPES)
def test_the_suggested_window_actually_bounds_the_unit(restart_sec, who):
    """The round trip, and the only test that proves the advice is advice.

    Detection and remedy are separate pieces of arithmetic and nothing
    else makes them agree.  A suggestion that merely looked plausible
    would be pasted, watched to fail, and would cost the family its
    reader.
    """
    burst = DEFAULT_START_LIMIT_BURST
    interval = suggested_start_limit_interval(restart_sec, burst)
    assert interval is not None, who
    assert restart_is_bounded("always", restart_sec, interval, burst) is True, who


def test_the_unit_was_unbounded_before_the_suggestion():
    """Guards the round trip above from passing vacuously."""
    assert restart_is_bounded("always", 10.0, None, None) is False


def test_a_bigger_window_is_a_stricter_limiter():
    """The direction is counter-intuitive and the wording depends on it.

    Widening ``StartLimitIntervalSec`` lets *more* starts fall inside it,
    so raising it is the fix.  Anyone "tightening" the window would make
    the loop more immortal, not less.
    """
    assert restart_is_bounded("always", 10.0, 20.0, 5) is False
    assert restart_is_bounded("always", 10.0, 600.0, 5) is True


def test_no_window_is_suggested_when_none_would_help():
    """``RestartSec`` wider than the ladder, and ``infinity``.

    Silence beats a number that does not fix it: the reader pastes it,
    the loop continues, and the family loses its credibility.  The
    recommendation says to lower ``RestartSec`` instead.
    """
    assert suggested_start_limit_interval(3600.0, 5) is None
    assert suggested_start_limit_interval(float("inf"), 5) is None


def test_a_burst_of_one_has_no_window_to_suggest():
    """The second start trips it whenever it happens, so the window is
    irrelevant — and ``restart_is_bounded`` already says so."""
    assert suggested_start_limit_interval(10.0, 1) is None
    assert restart_is_bounded("always", 10.0, None, 1) is True


# ── Who is in the family ─────────────────────────────────────────────


def test_a_monitored_unit_is_in_the_family(tmp_path):
    """The whole of the snag.  11 of the 13 live members are monitored,
    and ``classify_units`` drops monitored units before they become
    findings — so this population was invisible on every surface."""
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(tmp_path, "live.service", working_dir=str(project))

    scan = scan_units(
        user,
        None,
        str(tmp_path),
        [ProjectRef(name="live", path=str(project))],
        {"user:live.service"},
    )

    assert scan.monitored_count == 1
    assert scan.findings == []
    assert [f.unit for f in scan.restart_findings] == ["live.service"]
    assert scan.restart_findings[0].category == RESTART_UNBOUNDED


def test_an_orphan_is_excluded_even_though_it_loops(tmp_path):
    """Deliberately the opposite of the obvious rule.

    A broken unit that also loops reads like the worst case and belongs
    here twice over.  It cannot: the orphan recommendation is *remove
    it*, and a start limit on a file you should delete is two
    contradictory instructions.  The fact is not lost — an armed orphan
    that loops is what ``armed_alert_severity`` promotes to ``critical``.
    """
    user = _unit(tmp_path, "dead.service", working_dir="/gone")

    scan = scan_units(user, None, str(tmp_path), [], set())

    assert [f.category for f in scan.findings] == [ORPHANED]
    assert scan.findings[0].restart_bounded is False
    assert scan.restart_findings == []


def test_a_bounded_unit_is_not_in_the_family(tmp_path):
    """The Session 39 shape on ``sysadmin.service``, which passes."""
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(
        tmp_path,
        "good.service",
        working_dir=str(project),
        start_limit="StartLimitIntervalSec=600\nStartLimitBurst=5",
    )

    scan = scan_units(
        user, None, str(tmp_path), [ProjectRef(name="live", path=str(project))], set()
    )

    assert scan.restart_findings == []


def test_a_unit_that_does_not_restart_is_not_in_the_family(tmp_path):
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(
        tmp_path,
        "quiet.service",
        working_dir=str(project),
        restart="",
        restart_sec="",
    )

    scan = scan_units(
        user, None, str(tmp_path), [ProjectRef(name="live", path=str(project))], set()
    )

    assert scan.restart_findings == []


# ── It must not inflate the sweep's own numbers ──────────────────────


def test_the_family_is_outside_actionable_and_outside_the_sum(tmp_path):
    """``actionable`` is the roll-up alert's title *and* the number
    ``alert_threshold`` is compared against.  13 latent risks added there
    would trip it on their own and would read as 13 units to wire up."""
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(tmp_path, "live.service", working_dir=str(project))
    _unit(tmp_path, "dead.service", working_dir="/gone")

    scan = scan_units(
        user,
        None,
        str(tmp_path),
        [ProjectRef(name="live", path=str(project))],
        {"user:live.service"},
    )

    assert scan.restart_findings, "fixture must produce a restart finding"
    assert scan.actionable == len(scan.findings)
    assert all(f.category != RESTART_UNBOUNDED for f in scan.findings)
    assert (
        scan.monitored_count + scan.timers_folded + len(scan.findings)
        == scan.units_scanned
    )


def test_the_summary_keeps_its_arithmetic_with_the_new_field():
    """``restart_unbounded`` cuts across the buckets like ``armed``, so it
    is reported beside the sum and never inside it."""
    summary = UnitScanSummary(
        units_scanned=46,
        monitored=23,
        timers_folded=11,
        orphaned=6,
        unmonitored=1,
        host=5,
        armed=1,
        restart_unbounded=13,
    )
    assert (
        summary.monitored
        + summary.timers_folded
        + summary.orphaned
        + summary.unmonitored
        + summary.host
        == summary.units_scanned
    )


def test_the_blob_carries_a_scalar_count_beside_the_capped_list(tmp_path):
    """Session 24's rule: a truncated list never sources a count."""
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(tmp_path, "live.service", working_dir=str(project))

    scan = scan_units(
        user,
        None,
        str(tmp_path),
        [ProjectRef(name="live", path=str(project))],
        {"user:live.service"},
    )
    blob = scan.as_findings_blob(limit=0)

    assert blob["restart_unbounded_count"] == 1
    assert blob[RESTART_UNBOUNDED] == []


# ── Advice ───────────────────────────────────────────────────────────


def test_restart_ranks_after_orphan_and_before_unmonitored():
    assert KIND_ORDER.index("orphan") < KIND_ORDER.index("restart")
    assert KIND_ORDER.index("restart") < KIND_ORDER.index("unmonitored")


def _restart_recs(tmp_path, **kwargs):
    project = tmp_path / "live"
    project.mkdir(exist_ok=True)
    user = _unit(tmp_path, "live.service", working_dir=str(project), **kwargs)
    scan = scan_units(
        user,
        None,
        str(tmp_path),
        [ProjectRef(name="live", path=str(project))],
        {"user:live.service"},
    )
    return recommendations_for_scan(scan.findings + scan.restart_findings)


def test_the_snippet_is_the_unit_file_not_services_yaml(tmp_path):
    """The first time this module emits text for a file another
    repository owns — so the target is the absolute unit path, and the
    advice stops at text."""
    rec = _restart_recs(tmp_path)[0]

    assert rec.kind == "restart"
    assert rec.severity == "advice"
    assert rec.snippet_target is not None
    assert rec.snippet_target.endswith("live.service")
    assert "[Unit]" in rec.snippet
    assert "StartLimitIntervalSec=" in rec.snippet
    assert "StartLimitBurst=" in rec.snippet


def test_the_snippet_pastes_into_the_file_it_names(tmp_path):
    """End to end: append the snippet to the real unit, re-scan, and the
    unit must leave the family.  Nothing else proves the two lines are in
    a section systemd reads them from."""
    project = tmp_path / "live"
    project.mkdir()
    user = _unit(tmp_path, "live.service", working_dir=str(project))
    projects = [ProjectRef(name="live", path=str(project))]
    wired = {"user:live.service"}

    scan = scan_units(user, None, str(tmp_path), projects, wired)
    rec = recommendations_for_scan(scan.restart_findings)[0]

    unit_file = Path(rec.snippet_target)
    unit_file.write_text(unit_file.read_text() + "\n" + rec.snippet + "\n")

    rescanned = scan_units(user, None, str(tmp_path), projects, wired)
    assert rescanned.restart_findings == []


def test_a_unit_in_both_scopes_gets_distinguishable_titles(tmp_path):
    """``deadlock-api-ingest.service`` is installed in both scopes running
    two different binaries, and both are unbounded today.  Two identical
    titles read as one item listed twice."""
    project = tmp_path / "live"
    project.mkdir()
    for scope in ("user", "system"):
        _write(
            tmp_path / scope / "twin.service",
            f"[Unit]\nDescription=Twin ({scope})\n\n"
            f"[Service]\nType=simple\nWorkingDirectory={project}\n"
            f"ExecStart={project}/run.sh\nRestart=always\nRestartSec=10\n",
        )

    scan = scan_units(
        tmp_path / "user",
        tmp_path / "system",
        str(tmp_path),
        [ProjectRef(name="live", path=str(project))],
        {"user:twin.service", "system:twin.service"},
    )
    recs = recommendations_for_scan(scan.restart_findings)

    assert len(recs) == 2
    assert len({r.title for r in recs}) == 2


def test_no_suggestion_means_no_snippet_and_a_different_action(tmp_path):
    """A ``RestartSec`` no window helps must not get a paste-ready line
    that does nothing."""
    rec = _restart_recs(tmp_path, restart_sec="RestartSec=1h")[0]

    assert rec.kind == "restart"
    assert rec.snippet == ""
    assert rec.snippet_target is None
    assert "Lower RestartSec" in rec.action


def test_the_detail_names_the_owning_project(tmp_path):
    """The edit belongs to whoever owns the unit — 11 of the 13 live
    members belong to four other repositories."""
    rec = _restart_recs(tmp_path)[0]

    assert "live" in rec.detail
    assert "repository's to make" in rec.detail
