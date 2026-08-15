"""Tests for service-discovery advice (Session 26 Tier 2).

The snippets are the part that has to be right: they are pasted into
hand-curated YAML by a human who will assume they work.  A snippet that
looks plausible and silently monitors nothing is worse than no snippet,
so several tests below assert on what is *absent* — an uncommented
``url``, a projects.yaml entry for a timer — rather than on what is there.
"""

from pathlib import Path

import pytest
import yaml

from sysadmin.units.recommendations import (
    KIND_ORDER,
    duplicate_units,
    recommendations_for_scan,
)
from sysadmin.units.scan import (
    HOST,
    ORPHANED,
    RESTART_UNBOUNDED,
    UNMONITORED,
    UnitFinding,
)


def _finding(unit, category=HOST, **kw) -> UnitFinding:
    kw.setdefault("scope", "user")
    kw.setdefault("path", f"/home/gaddi/.config/systemd/user/{unit}")
    kw.setdefault("monitor_unit", unit)
    kw.setdefault("reason", "reason text")
    # ``enabled`` is load-bearing for snippet emission since the
    # enablement gate: an advice row for a unit nothing starts declines
    # to offer paste-ready text.  These fixtures model units that *are*
    # enabled, so they must now say so — the field defaults to ``False``
    # for ``armed``'s sake, where absent evidence must read as "not
    # armed", which is the opposite polarity from this one.
    kw.setdefault("enabled", True)
    return UnitFinding(unit=unit, category=category, **kw)


class _Entry:
    """A declared registry entry, as far as these snippets care."""

    def __init__(self, project_id, path):
        self.id = project_id
        self.path = Path(path)


class _Registry:
    def __init__(self, declared):
        self.declared = declared


ALFRED = _Registry([_Entry("alfred", "/home/gaddi/projects/Alfred")])


# ── Ranking ──────────────────────────────────────────────────────────


def test_orphans_rank_above_gaps_which_rank_above_host_units():
    """All four *unit* tiers, deliberately shuffled in the input.

    ``restart`` sits second (SNAG-UNITS-002): above ``unmonitored``
    because the two are competing safety nets and a reachable start limit
    is the stronger one — systemd itself says so, to a hook, whether or
    not this service is polling.

    ``KIND_ORDER``'s fifth entry, ``port``, is not a unit finding at all
    — it comes from the stored port block, not from this list — so the
    assertion names the four rather than the whole tuple.  Session 26c's
    own ordering is covered in ``test_unit_ports.py``.
    """
    findings = [
        _finding("h.service", HOST),
        _finding("g.service", UNMONITORED, project="Alfred"),
        _finding(
            "r.service",
            RESTART_UNBOUNDED,
            restart="always",
            restart_sec=10.0,
            restart_bounded=False,
        ),
        _finding("o.service", ORPHANED, dead_path="/gone"),
    ]
    recs = recommendations_for_scan(findings, ALFRED)
    assert [r.kind for r in recs] == [k for k in KIND_ORDER if k != "port"]


def test_only_orphans_are_risks():
    """An orphan is broken; the other two are merely unwatched."""
    findings = [
        _finding("o.service", ORPHANED, dead_path="/gone"),
        _finding("g.service", UNMONITORED, project="Alfred"),
        _finding("h.service", HOST),
    ]
    recs = recommendations_for_scan(findings, ALFRED)
    assert [r.severity for r in recs] == ["risk", "advice", "advice"]


def test_no_recommendation_carries_a_score():
    """This tier has no currency — inventing one would be a number the
    reader cannot check.  Guard against a points field creeping back in."""
    (rec,) = recommendations_for_scan([_finding("h.service")], ALFRED)
    dumped = rec.model_dump()
    assert not {"points", "reclaimable_mb", "score"} & set(dumped)


# ── Orphan advice ────────────────────────────────────────────────────


def test_orphan_action_is_scope_correct_and_ordered():
    """disable before rm: deleting the file first strands the enablement
    symlink and systemd warns on every daemon-reload."""
    (rec,) = recommendations_for_scan(
        [_finding("garmin-sync.service", ORPHANED, dead_path="/gone")], ALFRED
    )
    assert rec.action.startswith("systemctl --user disable --now garmin-sync.service")
    assert rec.action.index("disable") < rec.action.index("rm ")
    assert "daemon-reload" in rec.action


def test_system_orphan_action_uses_sudo():
    (rec,) = recommendations_for_scan(
        [
            _finding(
                "personalassistant-backend.service",
                ORPHANED,
                scope="system",
                path="/etc/systemd/system/personalassistant-backend.service",
                dead_path="/opt/gone",
            )
        ],
        ALFRED,
    )
    assert rec.action.startswith("sudo systemctl disable --now")
    assert "sudo rm /etc/systemd/system/" in rec.action


def test_orphan_has_no_snippet():
    (rec,) = recommendations_for_scan(
        [_finding("x.service", ORPHANED, dead_path="/gone")], ALFRED
    )
    assert rec.snippet == "" and rec.snippet_target is None


def test_orphan_of_a_named_project_asks_for_confirmation_first():
    (rec,) = recommendations_for_scan(
        [_finding("pa.service", ORPHANED, project="PersonalAssistant")], ALFRED
    )
    assert "genuinely retired" in rec.detail


def test_orphan_detail_says_the_failures_were_silent():
    (rec,) = recommendations_for_scan(
        [_finding("x.service", ORPHANED, dead_path="/gone",
                  reason="WorkingDirectory /gone does not exist")],
        ALFRED,
    )
    assert "silent" in rec.detail


# ── Snippet targeting ────────────────────────────────────────────────


def test_timer_snippet_declares_kind_timer():
    """projects.yaml models only backend/frontend; a timer is neither."""
    (rec,) = recommendations_for_scan(
        [
            _finding(
                "alfred-job.service",
                UNMONITORED,
                project="Alfred",
                monitor_unit="alfred-job.timer",
            )
        ],
        ALFRED,
    )
    assert rec.snippet_target == "services.yaml"
    assert "alfred-job.timer" in rec.snippet


def test_a_declared_project_gets_a_project_reference():
    (rec,) = recommendations_for_scan(
        [_finding("alfred-worker.service", UNMONITORED, project="Alfred")], ALFRED
    )
    assert rec.snippet_target == "services.yaml"


def test_an_undeclared_project_gets_no_project_reference():
    (rec,) = recommendations_for_scan(
        [_finding("imbabots-bot.service", UNMONITORED, project="ImbaBots")], ALFRED
    )
    assert rec.snippet_target == "services.yaml"


def test_host_unit_carries_no_project():
    (rec,) = recommendations_for_scan([_finding("pgbackrest-backup.service")], ALFRED)
    assert rec.snippet_target == "services.yaml"
    assert "projects.yaml" not in rec.action


def test_hand_started_oneshot_gets_no_snippet():
    """Nothing schedules it, so a monitor would report it dead almost
    always — there is nothing honest to wire."""
    (rec,) = recommendations_for_scan([_finding("one-off.service", manual=True)], ALFRED)
    assert rec.snippet == "" and rec.snippet_target is None
    assert "started by hand" in rec.detail or "only runs when invoked" in rec.detail


# ── Snippet content ──────────────────────────────────────────────────


def _parse(snippet: str):
    """Snippets are indented for pasting; de-indent before parsing."""
    lines = snippet.splitlines()
    indent = min(len(ln) - len(ln.lstrip()) for ln in lines if ln.strip())
    return yaml.safe_load("\n".join(ln[indent:] for ln in lines))


def test_snippet_is_valid_yaml_of_the_expected_shape():
    (rec,) = recommendations_for_scan(
        [_finding("deadlock-api-ingest.service", description="Ingest")], ALFRED
    )
    (entry,) = _parse(rec.snippet)
    assert entry == {
        "name": "deadlock-api-ingest",
        "kind": "systemd",
        "systemd": {"unit": "deadlock-api-ingest.service", "scope": "user"},
        "log": {"type": "journalctl", "severity_filter": "warning"},
    }


def test_config_yaml_snippet_omits_user_for_a_system_unit():
    (rec,) = recommendations_for_scan(
        [_finding("pgbackrest.service", scope="system",
                  path="/etc/systemd/system/pgbackrest.service")],
        ALFRED,
    )
    (entry,) = _parse(rec.snippet)
    assert "user" not in entry


def test_timer_entry_is_named_and_marked_uncontrollable():
    """Start/stop on a timer arms or disarms a schedule, which is not
    what the tray button reads as."""
    (rec,) = recommendations_for_scan(
        [_finding("paccache.service", scope="system",
                  path="/etc/systemd/system/paccache.service",
                  monitor_unit="paccache.timer")],
        ALFRED,
    )
    (entry,) = _parse(rec.snippet)
    assert entry["name"] == "paccache-timer"
    assert entry["controllable"] is False


def test_snippet_uses_kind_systemd_since_the_port_is_unknown():
    """kind: http would need a url, and the scan does not know the port.

    kind: systemd checks something real without one, which is what the
    old shape could not do: a projects.yaml endpoint carrying a
    systemd_unit and no url was skipped entirely and looked wired.
    """
    (rec,) = recommendations_for_scan(
        [_finding("alfred-worker.service", UNMONITORED, project="Alfred")], ALFRED
    )
    (entry,) = _parse(rec.snippet)
    assert entry["kind"] == "systemd"
    assert "url" not in entry
    assert entry["systemd"] == {
        "unit": "alfred-worker.service", "scope": "user"
    }


def test_snippet_references_the_manifest_id_not_the_directory_name():
    """The sweep matches on the directory name; services.yaml keys on the
    manifest id. Emitting the wrong one produces a snippet that fails to
    load, which is worse than no snippet."""
    (rec,) = recommendations_for_scan(
        [_finding("alfred-frontend.service", UNMONITORED, project="Alfred")], ALFRED
    )
    (entry,) = _parse(rec.snippet)
    assert entry["project"] == "alfred"


def test_the_snippet_parses_as_a_real_service_entry():
    """The point of a paste-ready snippet is that it pastes."""
    from sysadmin.monitor.services import ServiceEntry

    (rec,) = recommendations_for_scan(
        [_finding("alfred-worker.service", UNMONITORED, project="Alfred")], ALFRED
    )
    (entry,) = _parse(rec.snippet)
    parsed = ServiceEntry.model_validate(entry)
    assert parsed.unit == "alfred-worker.service"
    assert parsed.scope == "user"


def test_description_becomes_a_comment_not_a_field():
    (rec,) = recommendations_for_scan(
        [_finding("x.service", description="Some daemon")], ALFRED
    )
    assert "# Some daemon" in rec.snippet
    (entry,) = _parse(rec.snippet)
    assert "description" not in entry


# ── Two-scope duplicates ─────────────────────────────────────────────


def test_duplicate_units_detects_the_two_scope_case():
    findings = [
        _finding("deadlock-api-ingest.service", scope="user"),
        _finding("deadlock-api-ingest.service", scope="system"),
        _finding("solo.service", scope="user"),
    ]
    assert duplicate_units(findings) == {"deadlock-api-ingest.service"}


def test_duplicate_units_get_distinct_config_names():
    """Two tiles with one label and no way to tell which binary died."""
    findings = [
        _finding("deadlock-api-ingest.service", scope="user"),
        _finding("deadlock-api-ingest.service", scope="system",
                 path="/etc/systemd/system/deadlock-api-ingest.service"),
    ]
    names = [_parse(r.snippet)[0]["name"] for r in recommendations_for_scan(findings, ALFRED)]
    assert sorted(names) == ["deadlock-api-ingest-system", "deadlock-api-ingest-user"]


def test_unique_unit_name_gets_no_scope_suffix():
    (rec,) = recommendations_for_scan([_finding("solo.service")], ALFRED)
    assert _parse(rec.snippet)[0]["name"] == "solo"


# ── Degenerate input ─────────────────────────────────────────────────


def test_no_findings_yields_no_recommendations():
    assert recommendations_for_scan([], ALFRED) == []


def test_missing_registry_is_tolerated():
    recs = recommendations_for_scan([_finding("x.service", UNMONITORED, project="P")], None)
    assert recs[0].snippet_target == "services.yaml"
    assert "no .project.yaml manifest" in recs[0].snippet


@pytest.mark.parametrize("category", [ORPHANED, UNMONITORED, HOST])
def test_every_category_produces_a_titled_actionable_recommendation(category):
    (rec,) = recommendations_for_scan(
        [_finding("x.service", category, project="Alfred", dead_path="/gone")], ALFRED
    )
    assert rec.title and rec.detail and rec.action
    assert rec.unit == "x.service"


# ── Session 48: the advice must be executable ────────────────────────
#
# Both defects below were found by *executing* the advice this endpoint
# emits rather than by reading it, which is the argument for the sitting
# existing at all.  Sessions 46, 47 and 26c made the diagnosis speak; nobody
# had checked that what it says can be carried out.


def test_a_disabled_host_unit_gets_no_snippet():
    """The pile-up, re-created by this module's own remediation advice.

    ``kind: systemd`` asserts the unit is *active*.  A host unit nothing
    enables is not started by anything on the box, so pasting the
    snippet declares a check that fails on every poll for ever — the
    shape Sessions 41-45 spent themselves deleting.

    Live on 2026-08-15: of five ``host`` findings, the two with
    ``enabled=False`` (system ``deadlock-api-ingest.service`` and its
    updater timer) were both ``inactive``; the three with
    ``enabled=True`` were all ``active``.
    """
    (rec,) = recommendations_for_scan(
        [_finding("deadlock-api-ingest.service", HOST, enabled=False)]
    )
    assert rec.snippet == ""
    assert rec.snippet_target is None
    assert "Nothing enables" in rec.detail


def test_an_enabled_host_unit_still_gets_its_snippet():
    """The gate must not swallow the family it exists inside."""
    (rec,) = recommendations_for_scan(
        [_finding("ethernet-optimise.service", HOST, enabled=True)]
    )
    assert rec.snippet
    assert rec.snippet_target == "services.yaml"


def test_a_snippetless_recommendation_never_says_paste_the_snippet_below():
    """An advice row that reads as actionable and is not.

    ``sysadmin-failed.service`` shipped as exactly this: ``snippet: ""``
    under the text *"Paste the snippet below into services.yaml"*.  An
    execution sitting cannot close it, so it returns on every sweep for
    ever — a count that never falls, which is the roll-up defect wearing
    a single unit's name.
    """
    for kw in ({"enabled": False}, {"manual": True, "enabled": False}):
        (rec,) = recommendations_for_scan(
            [_finding("something.service", HOST, **kw)]
        )
        assert rec.snippet == ""
        assert "snippet below" not in rec.action
        # It must still say what to actually do.
        assert rec.action.strip()


def test_a_disabled_unit_is_told_how_to_become_monitorable():
    """The next step is a fork, and naming it is what closes the item."""
    (rec,) = recommendations_for_scan(
        [_finding("deadlock-api-ingest.service", HOST, enabled=False)]
    )
    assert "systemctl --user enable --now deadlock-api-ingest.service" in rec.action
    assert "remove" in rec.action.lower()


def test_the_enable_command_names_the_timer_for_a_folded_oneshot():
    """Enabling a folded oneshot's *service* arms nothing.

    A oneshot with a timer is started by the timer, so the timer is the
    half carrying ``[Install]``.  Same field, same reason, as
    :func:`removal_command`.
    """
    (rec,) = recommendations_for_scan(
        [
            _finding(
                "paccache.service",
                HOST,
                monitor_unit="paccache.timer",
                scope="system",
                enabled=False,
            )
        ]
    )
    assert "sudo systemctl enable --now paccache.timer" in rec.action
    assert "paccache.service" not in rec.action


def test_removing_a_folded_orphan_removes_its_timer_too():
    """Removing only the service leaves a timer pointing at nothing.

    ``ticktick-sync.timer`` declares ``Requires=ticktick-sync.service``
    and was left installed by the command this module emitted — systemd
    warns on every ``daemon-reload``, and the next sweep cannot see it,
    because a timer with no service is not a finding shape this module
    has.  Found on this box 2026-08-15.
    """
    (rec,) = recommendations_for_scan(
        [
            _finding(
                "ticktick-sync.service",
                ORPHANED,
                scope="system",
                path="/etc/systemd/system/ticktick-sync.service",
                monitor_unit="ticktick-sync.timer",
            )
        ]
    )
    assert "ticktick-sync.timer" in rec.action
    assert "/etc/systemd/system/ticktick-sync.timer" in rec.action
    # Timer first: disarm the schedule before its service goes away.
    assert rec.action.index("ticktick-sync.timer") < rec.action.index(
        "ticktick-sync.service"
    )


def test_an_unfolded_orphan_removal_is_unchanged():
    """The timer clause must not fire when there is no timer.

    ``monitor_unit`` equals ``unit`` for every unfolded finding, so a
    naive implementation would emit the unit twice.
    """
    (rec,) = recommendations_for_scan(
        [
            _finding(
                "garmin-sync.service",
                ORPHANED,
                path="/home/gaddi/.config/systemd/user/garmin-sync.service",
            )
        ]
    )
    assert rec.action.count("garmin-sync.service") == 2  # disable, then rm
    assert "timer" not in rec.action
