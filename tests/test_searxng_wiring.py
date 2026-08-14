"""The deploy-triggered half of the SearXNG task, made mechanical.

`docs/roadmap/tasks.md` carries a delegated requirement from
estate-manager: **monitor SearXNG when the estate deploys it.** Its
trigger is another repository's action, which is the whole difficulty —
the precedent it was written against (`estate-manager-audit.timer`,
`fa51aac`) shipped a unit that ran unmonitored until this repository's
next session happened to notice. A task list does not fire; a test does.

**Gated, not asserted unconditionally.** The unit does not exist today,
so an ungated version would be red on every run in a repository that has
no fault, and would be deleted or marked xfail within a week. It skips
until a searxng unit is installed on this box and fails from that moment
until `services.yaml` declares it — so the red appears on the day the
gap opens, which is the day it is cheap to close. The skip shape is
borrowed from `tests/test_schema_drift.py` rather than a custom marker,
so there is one way to say "this needs something live" here.

**The gate is the unit file, not a listening port.** A port answers only
while the service is up, so a probe would flip the gate off exactly when
SearXNG is down — the state monitoring exists for. A unit file is
installed once and stays. It is matched on the substring `searx` rather
than an exact `searxng.service` because the deploy shape is not decided:
a container deploy names its unit `podman-searxng.service` or
`container-searxng.service`, and a gate that only knows one spelling
fails open on the other two.

**What is asserted is `kind: http`, and that is the point of the file.**
The Session 26 unit sweep will already catch this unit unaided and file
it as a `host` finding — hand-written, mapping to no project — with a
`services.yaml` snippet that correctly omits `project:`. But that snippet
says `kind: systemd`, documented in `sysadmin/units/recommendations.py`:
the scan cannot know a port. `kind: systemd` asserts only that the unit
is active, and a SearXNG that is running while every search errors is
both *active* and *useless* — it is the case worth catching, and it is
the one case a unit check cannot see. The port is knowable at deploy
time (estate-manager's registry claims it before anything listens), so
this asserts the shape the scanner structurally cannot derive.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

#: Where hand-written units live in each scope — the same two directories
#: `sysadmin.units.scan.discover_units` reads.
UNIT_DIRS = (
    Path.home() / ".config/systemd/user",
    Path("/etc/systemd/system"),
)

SERVICES_YAML = Path(__file__).resolve().parents[1] / "services.yaml"


def _searx_units() -> list[str]:
    """Installed unit files whose name mentions searx, in either scope."""
    found: list[str] = []
    for directory in UNIT_DIRS:
        try:
            entries = list(directory.iterdir())
        except OSError:
            continue
        found.extend(
            entry.name
            for entry in entries
            if "searx" in entry.name.lower() and entry.suffix == ".service"
        )
    return sorted(found)


def _declared_services() -> list[dict]:
    return yaml.safe_load(SERVICES_YAML.read_text())["services"]


def _searx_entries(services: list[dict]) -> list[dict]:
    return [s for s in services if "searx" in str(s.get("name", "")).lower()]


@pytest.mark.skipif(
    not _searx_units(),
    reason="no searxng unit installed — estate-manager has not deployed it yet",
)
def test_searxng_is_declared_in_services_yaml():
    """A live searxng unit that services.yaml does not know about is the gap."""
    units = _searx_units()
    entries = _searx_entries(_declared_services())

    assert entries, (
        f"searxng is installed on this box ({', '.join(units)}) and "
        "services.yaml declares nothing for it, so nothing is checking it. "
        "The pre-staged block sits commented in services.yaml beside "
        "mosquitto — fill in the port and health path and uncomment it. "
        "See the SearXNG item in docs/roadmap/tasks.md for why each field "
        "is the shape it is."
    )


@pytest.mark.skipif(
    not _searx_units(),
    reason="no searxng unit installed — estate-manager has not deployed it yet",
)
def test_searxng_is_polled_over_http_not_merely_active():
    """`kind: systemd` would pass a SearXNG whose every search errors."""
    for entry in _searx_entries(_declared_services()):
        assert entry.get("kind") == "http", (
            f"{entry.get('name')} is declared as kind={entry.get('kind')!r}. "
            "A unit check reports SearXNG healthy whenever the process is "
            "running, including when it answers every query with an error — "
            "which is the failure worth catching. Use kind: http against "
            "SearXNG's own health path. The unit sweep's generated snippet "
            "says kind: systemd because the scan cannot know a port; the "
            "port is in estate-manager's registry."
        )
        assert entry.get("url"), (
            f"{entry.get('name')} is kind: http with no url, which the "
            "loader rejects — but say so here too, because the url is one "
            "of the two fields the pre-staged block could not supply."
        )


@pytest.mark.skipif(
    not _searx_units(),
    reason="no searxng unit installed — estate-manager has not deployed it yet",
)
def test_searxng_carries_no_project_id():
    """Third-party infrastructure has no repository to reference.

    Not redundant with the loader, which raises on a `project:` that
    resolves to nothing: the failure this guards is someone *creating* a
    manifest to satisfy the field. `mosquitto` is the precedent —
    estate-owned since that repository's Session 2, and carrying no
    `project:` here the whole time. Project-less is not ownerless.
    """
    for entry in _searx_entries(_declared_services()):
        assert "project" not in entry, (
            f"{entry.get('name')} declares project={entry['project']!r}. "
            "SearXNG is third-party software the estate hosts, with no "
            "repository under ~/projects and no .project.yaml. Four other "
            "host entries omit the field; mosquitto is estate-owned and "
            "omits it too."
        )


# --------------------------------------------------------------------------
# The gate itself
# --------------------------------------------------------------------------
#
# Everything above skips on this box and will keep skipping until another
# repository acts, which makes the whole file unfalsifiable: a gate that
# never fires and a gate that cannot fire are indistinguishable from the
# outside, and the second one is worse than no test at all. These run in
# CI, drive the same helpers against a fake estate under `tmp_path`, and
# assert that the skip is a state rather than a permanent condition.


@pytest.fixture
def fake_units(tmp_path, monkeypatch):
    """Point the unit search at a directory the test controls."""
    unit_dir = tmp_path / "user"
    unit_dir.mkdir()
    monkeypatch.setattr("tests.test_searxng_wiring.UNIT_DIRS", (unit_dir,))
    return unit_dir


def test_gate_is_closed_when_no_unit_is_installed(fake_units):
    (fake_units / "alfred-backend.service").write_text("[Service]\n")
    assert _searx_units() == []


@pytest.mark.parametrize(
    "unit_name",
    [
        "searxng.service",
        "podman-searxng.service",
        "container-searxng.service",
        "SearXNG.service",
    ],
)
def test_gate_opens_for_every_plausible_deploy_shape(fake_units, unit_name):
    """A container deploy does not name its unit `searxng.service`."""
    (fake_units / unit_name).write_text("[Service]\n")
    assert _searx_units() == [unit_name]


def test_gate_ignores_the_timer_beside_a_service(fake_units):
    """`.timer`/`.socket` siblings would double-count one deploy."""
    (fake_units / "searxng.service").write_text("[Service]\n")
    (fake_units / "searxng.socket").write_text("[Socket]\n")
    assert _searx_units() == ["searxng.service"]


def test_gate_survives_a_missing_scope_directory(tmp_path, monkeypatch):
    """/etc/systemd/system is unreadable in some CI images."""
    monkeypatch.setattr(
        "tests.test_searxng_wiring.UNIT_DIRS", (tmp_path / "nope",)
    )
    assert _searx_units() == []


def test_assertions_fire_against_an_undeclared_unit():
    """The failure the gated tests exist to produce, produced on demand."""
    assert _searx_entries([{"name": "mosquitto", "kind": "systemd"}]) == []

    systemd_shaped = [{"name": "searxng", "kind": "systemd"}]
    found = _searx_entries(systemd_shaped)
    assert found and found[0]["kind"] != "http"

    with_project = [{"name": "searxng", "kind": "http", "project": "searxng"}]
    assert "project" in _searx_entries(with_project)[0]


@pytest.mark.skipif(
    bool(_searx_units()),
    reason="searxng is deployed — the entry is supposed to be live now",
)
def test_the_pre_staged_block_is_still_commented_out():
    """Uncommenting it before the deploy checks a unit that does not exist.

    The loader has no "declared but absent" state, so a live entry naming
    an uninstalled unit reports down every 300 seconds for as long as the
    deploy takes — the alert-storm shape this repository has paid for
    four times. The block is prose until someone fills in the port.

    Gated the opposite way round from the three above, deliberately: this
    is the only assertion here that stops being true once SearXNG exists,
    so it retires itself at the deploy rather than becoming a test whose
    documented remedy is to delete it.
    """
    text = SERVICES_YAML.read_text()
    assert "# - name: searxng" in text, (
        "the pre-staged SearXNG block has gone from services.yaml — if it "
        "was activated, delete this test with it"
    )
    assert not _searx_entries(_declared_services()), (
        "searxng is a live services.yaml entry while no searxng unit is "
        "installed, so this check runs every 300 seconds against a unit "
        "that does not exist and reports it down each time. Re-comment it "
        "until the deploy lands."
    )
