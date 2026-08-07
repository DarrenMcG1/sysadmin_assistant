"""Tests for service-discovery advice (Session 26 Tier 2).

The snippets are the part that has to be right: they are pasted into
hand-curated YAML by a human who will assume they work.  A snippet that
looks plausible and silently monitors nothing is worse than no snippet,
so several tests below assert on what is *absent* — an uncommented
``url``, a projects.yaml entry for a timer — rather than on what is there.
"""

import pytest
import yaml

from sysadmin.services.unit_recommendations import (
    KIND_ORDER,
    duplicate_units,
    recommendations_for_scan,
)
from sysadmin.services.units import HOST, ORPHANED, UNMONITORED, UnitFinding


def _finding(unit, category=HOST, **kw) -> UnitFinding:
    kw.setdefault("scope", "user")
    kw.setdefault("path", f"/home/gaddi/.config/systemd/user/{unit}")
    kw.setdefault("monitor_unit", unit)
    kw.setdefault("reason", "reason text")
    return UnitFinding(unit=unit, category=category, **kw)


class _Project:
    def __init__(self, name, path=None):
        self.name = name
        self.path = path


class _ProjectsConfig:
    def __init__(self, projects):
        self.projects = projects


ALFRED = _ProjectsConfig([_Project("Alfred", "/home/gaddi/projects/Alfred")])


# ── Ranking ──────────────────────────────────────────────────────────


def test_orphans_rank_above_gaps_which_rank_above_host_units():
    findings = [
        _finding("h.service", HOST),
        _finding("g.service", UNMONITORED, project="Alfred"),
        _finding("o.service", ORPHANED, dead_path="/gone"),
    ]
    recs = recommendations_for_scan(findings, ALFRED)
    assert [r.kind for r in recs] == list(KIND_ORDER)


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


def test_timer_snippet_goes_to_config_yaml_not_projects_yaml():
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
    assert rec.snippet_target == "config.yaml"
    assert "alfred-job.timer" in rec.snippet


def test_long_running_unit_of_a_known_project_targets_projects_yaml():
    (rec,) = recommendations_for_scan(
        [_finding("alfred-worker.service", UNMONITORED, project="Alfred")], ALFRED
    )
    assert rec.snippet_target == "projects.yaml"


def test_unit_of_a_project_not_in_projects_yaml_targets_config_yaml():
    (rec,) = recommendations_for_scan(
        [_finding("imbabots-bot.service", UNMONITORED, project="ImbaBots")], ALFRED
    )
    assert rec.snippet_target == "config.yaml"


def test_host_unit_always_targets_config_yaml():
    (rec,) = recommendations_for_scan([_finding("pgbackrest-backup.service")], ALFRED)
    assert rec.snippet_target == "config.yaml"
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


def test_config_yaml_snippet_is_valid_yaml_of_the_expected_shape():
    (rec,) = recommendations_for_scan(
        [_finding("deadlock-api-ingest.service", description="Ingest")], ALFRED
    )
    (entry,) = _parse(rec.snippet)
    assert entry == {
        "name": "deadlock-api-ingest",
        "type": "systemd",
        "systemd_unit": "deadlock-api-ingest.service",
        "user": True,
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


def test_projects_yaml_snippet_leaves_url_commented_out():
    """to_monitored_services skips an endpoint with no url, so an entry
    with systemd_unit and no url looks wired and checks nothing.  The
    scan does not know the port yet — that is Session 26b."""
    (rec,) = recommendations_for_scan(
        [_finding("alfred-worker.service", UNMONITORED, project="Alfred")], ALFRED
    )
    parsed = _parse(rec.snippet)
    assert "url" not in parsed["backend"]
    assert "# url:" in rec.snippet
    assert parsed["backend"]["systemd_unit"] == "alfred-worker.service"
    assert parsed["backend"]["user"] is True
    assert parsed["backend"]["log"]["unit"] == "alfred-worker.service"


def test_projects_yaml_snippet_uses_the_frontend_role_when_named_so():
    (rec,) = recommendations_for_scan(
        [_finding("alfred-frontend.service", UNMONITORED, project="Alfred")], ALFRED
    )
    assert "frontend" in _parse(rec.snippet)


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


def test_missing_projects_config_is_tolerated():
    recs = recommendations_for_scan([_finding("x.service", UNMONITORED, project="P")], None)
    assert recs[0].snippet_target == "config.yaml"


@pytest.mark.parametrize("category", [ORPHANED, UNMONITORED, HOST])
def test_every_category_produces_a_titled_actionable_recommendation(category):
    (rec,) = recommendations_for_scan(
        [_finding("x.service", category, project="Alfred", dead_path="/gone")], ALFRED
    )
    assert rec.title and rec.detail and rec.action
    assert rec.unit == "x.service"
