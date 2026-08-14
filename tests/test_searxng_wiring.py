"""The deploy-triggered half of the SearXNG task, made mechanical.

`docs/roadmap/tasks.md` carries a delegated requirement from
estate-manager: **monitor SearXNG when the estate deploys it.** Its
trigger is another repository's action, which is the whole difficulty —
the precedent it was written against (`estate-manager-audit.timer`,
`fa51aac`) shipped a unit that ran unmonitored until this repository's
next session happened to notice. A task list does not fire; a test does.

**Gated, not asserted unconditionally — and the gate fired on
2026-08-14**, the day estate-manager deployed SearXNG. It went red that
morning and was wired the same day, which is the whole design: the red
appears on the day the gap opens, which is the day it is cheap to close.

The gate is still load-bearing rather than spent, because it now
separates two environments rather than two dates. CI has no searxng
unit, so the three assertions below skip there and run here, against the
live box. An ungated version would be red on every CI run in a
repository that has no fault, and would be deleted or marked xfail
within a week. The skip shape is borrowed from `tests/test_schema_drift.py`
rather than a custom marker, so there is one way to say "this needs
something live" here.

**The gate is the unit file, not a listening port.** A port answers only
while the service is up, so a probe would flip the gate off exactly when
SearXNG is down — the state monitoring exists for. A unit file is
installed once and stays. It is matched on the substring `searx` rather
than an exact `searxng.service` because the deploy shape was not decided
when this was written: a container deploy names its unit
`podman-searxng.service` or `container-searxng.service`, and a gate that
only knows one spelling fails open on the other two.

**That fail-open is what made the gate fire.** What estate-manager
actually shipped was two units — `estate-manager-searxng.service` (the
upstream container on loopback :8601) and
`estate-manager-searxng-shim.service` (:8600, the monitored one) — and
**neither name is any of the three spellings guessed above**. An exact
match, or a match on the guessed set, would have stayed silently closed
on the day it was supposed to open, which is the failure mode a gate
has: it looks identical to a gate with nothing to report.

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


def _monitored(entries: list[dict]) -> list[dict]:
    """The entries that are actually checked. `monitor:` defaults to true."""
    return [e for e in entries if e.get("monitor", True)]


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
        "Declare it beside mosquitto as kind: http against the shim's "
        "/api/health on the port estate-manager's registry claims — see "
        "the commentary on the searxng entry in services.yaml for why "
        "each field is the shape it is."
    )


@pytest.mark.skipif(
    not _searx_units(),
    reason="no searxng unit installed — estate-manager has not deployed it yet",
)
def test_searxng_is_polled_over_http_not_merely_active():
    """`kind: systemd` would pass a SearXNG whose every search errors.

    **Scoped to the monitored entries, and counted rather than filtered.**
    The deploy is two units and only one is checked: the shim on 8600
    carries the health endpoint, and SearXNG's own container on 8601 is
    declared `monitor: false` because a container that is down already
    shows up as a 503 from the shim. Asserting `kind: http` over every
    searx-named entry would therefore fail on a correct file.

    But merely skipping unmonitored entries would make this vacuous —
    setting `monitor: false` on the *shim* would silence the whole family
    and still pass. So the count is asserted first: exactly one searx
    entry is checked, and that one is polled over HTTP.
    """
    entries = _searx_entries(_declared_services())
    monitored = _monitored(entries)

    assert len(monitored) == 1, (
        "expected exactly one monitored searxng entry — the shim that "
        f"serves the health endpoint — but {len(monitored)} of "
        f"{len(entries)} are checked: "
        f"{[e.get('name') for e in monitored]}. Two monitored entries give "
        "one fault two alert rows; none means the family has been "
        "silenced with monitor: false rather than fixed."
    )

    entry = monitored[0]
    assert entry.get("kind") == "http", (
        f"{entry.get('name')} is declared as kind={entry.get('kind')!r}. "
        "A unit check reports SearXNG healthy whenever the process is "
        "running, including when it answers every query with an error — "
        "which is the failure worth catching. Use kind: http against "
        "the shim's /api/health — NOT /healthz, which the shim "
        "proxies straight to SearXNG and which answers 200 whenever "
        "the container is running, reintroducing the blindness this "
        "assertion exists to prevent. The unit sweep's generated "
        "snippet says kind: systemd because the scan cannot know a "
        "port; the port is in estate-manager's registry."
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
def test_an_unmonitored_searx_unit_says_why():
    """Declared-and-not-checked must stay distinguishable from forgotten.

    The loader already requires a `reason` beside `monitor: false`. This
    asserts the *intent* rather than the schema: the 8601 container is
    left out of checking because the shim's 503 already covers it, and an
    entry that stopped saying so would read as a unit someone quietly
    muted.
    """
    for entry in _searx_entries(_declared_services()):
        if entry.get("monitor", True):
            continue
        assert entry.get("reason", "").strip(), (
            f"{entry.get('name')} is monitor: false with no reason. An "
            "unchecked service without one is indistinguishable from a "
            "service nobody wired up."
        )


@pytest.mark.skipif(
    not _searx_units(),
    reason="no searxng unit installed — estate-manager has not deployed it yet",
)
def test_searxng_carries_no_project_id():
    """The subject of this check is third-party, so it names no repository.

    Not redundant with the loader, which raises on a `project:` that
    resolves to nothing: the failure this guards is someone *creating* a
    manifest to satisfy the field. `mosquitto` is the precedent —
    estate-owned since that repository's Session 2, and carrying no
    `project:` here the whole time. Project-less is not ownerless.

    **The deploy narrowed why this holds** (2026-08-14). Written on the
    assumption that SearXNG would be deployed bare, it read "third-party
    software with no repository under ~/projects". What shipped puts an
    estate-manager-owned shim in front of it, and that module *does* have
    a manifest — so the field would now resolve and the loader would not
    object. The assertion stands on the narrower ground, decided by the
    owner: what this entry judges is whether **searching works**, and the
    424 rung fires for upstream engines failing off this box. Attributing
    that to the estate-manager repository would charge it for a fault it
    does not own. The shim is the plumbing that makes SearXNG monitorable,
    not the thing being monitored.
    """
    for entry in _searx_entries(_declared_services()):
        assert "project" not in entry, (
            f"{entry.get('name')} declares project={entry['project']!r}. "
            "The subject of this check is SearXNG — third-party software "
            "the estate hosts — even though the URL is served by "
            "estate-manager's shim. A 424 here means upstream search "
            "engines are failing, which is not the estate-manager "
            "repository's fault to carry. Four other host entries omit "
            "the field; mosquitto is estate-owned and omits it too."
        )


# --------------------------------------------------------------------------
# The gate itself
# --------------------------------------------------------------------------
#
# Everything above now runs on this box and skips in CI, where no searxng
# unit is installed. Before the deploy it skipped everywhere, which made
# the whole file unfalsifiable: a gate that never fires and a gate that
# cannot fire are indistinguishable from the outside, and the second one
# is worse than no test at all. These run in both places, drive the same
# helpers against a fake estate under `tmp_path`, and keep the skip
# honest as a state rather than a permanent condition.


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
        # Guessed before the deploy, none of which it used.
        "searxng.service",
        "podman-searxng.service",
        "container-searxng.service",
        "SearXNG.service",
        # What estate-manager actually installed on 2026-08-14. Pinned
        # here so the substring match cannot be "tidied" into an exact or
        # enumerated one without going red: every real name on this box
        # is a prefixed variant that no guess above anticipated.
        "estate-manager-searxng-shim.service",
        "estate-manager-searxng.service",
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

    # Muting the shim must not read as "one monitored entry, all well".
    silenced = [
        {"name": "searxng", "kind": "http", "monitor": False, "reason": "x"},
        {"name": "searxng-upstream", "kind": "systemd", "monitor": False,
         "reason": "y"},
    ]
    assert _monitored(silenced) == []

    # And the real shape: two declared, exactly one checked.
    live = [
        {"name": "searxng", "kind": "http", "url": "http://localhost:8600/"},
        {"name": "searxng-upstream", "kind": "systemd", "monitor": False,
         "reason": "covered by the shim's 503"},
    ]
    assert len(_monitored(live)) == 1

    with_project = [{"name": "searxng", "kind": "http", "project": "searxng"}]
    assert "project" in _searx_entries(with_project)[0]
