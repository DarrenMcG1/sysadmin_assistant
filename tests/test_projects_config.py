"""Tests for projects.yaml — what remains of it after the services.yaml move.

The endpoint half of this file (``backend:``/``frontend:`` blocks, and the
``_merge_projects_config`` injection into the monitoring config) was removed
in Session 35 Phase 3: services.yaml owns every service and every journal
source attached to one. What is still read here is project *state* — the
declared ``status`` and the per-project ``alert_threshold`` — until Phase 4
retires the file in favour of the manifests.
"""

import textwrap
from pathlib import Path

from sysadmin.core.config import (
    ManagedProject,
    ProjectsConfig,
    load_config,
)

# ── Model construction ───────────────────────────────────────────






class TestProjectsConfig:
    def test_empty(self):
        pc = ProjectsConfig()
        assert pc.projects == []

    def test_from_dict(self):
        pc = ProjectsConfig.model_validate({
            "projects": [
                {"name": "app-a"},
                {"name": "app-b", "path": "/opt/app-b"},
            ]
        })
        assert len(pc.projects) == 2
        assert pc.projects[1].path == "/opt/app-b"


# ── Merge logic ──────────────────────────────────────────────────


def _write_yaml(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content))



# ── Full load_config integration ─────────────────────────────────


class TestLoadConfigIntegration:
    def test_load_with_projects_yaml(self, tmp_path):
        """load_config() merges a sibling projects.yaml."""
        config_file = tmp_path / "config.yaml"
        _write_yaml(config_file, """\
            service:
              port: 8500
        """)
        projects_file = tmp_path / "projects.yaml"
        _write_yaml(projects_file, """\
            projects:
              - name: my-app
                backend:
                  url: http://localhost:8000/health
        """)

        # Reset singleton
        import sysadmin.core.config as cfg
        cfg._config = None

        config = load_config(config_file)
        assert len(config.projects.projects) == 1
        assert config.projects.projects[0].name == "my-app"

        # Clean up singleton
        cfg._config = None

    def test_load_without_projects_yaml(self, tmp_path):
        """load_config() works when projects.yaml doesn't exist."""
        config_file = tmp_path / "config.yaml"
        _write_yaml(config_file, """\
            service:
              port: 8500
        """)

        import sysadmin.core.config as cfg
        cfg._config = None

        config = load_config(config_file)
        assert config.projects.projects == []

        cfg._config = None


# ── Per-project alert thresholds (Session 20) ────────────────────


class TestAlertThresholdFor:
    def test_no_entries_returns_the_global_default(self):
        config = ProjectsConfig()
        assert config.alert_threshold_for("anything", None, 40) == 40

    def test_entry_without_a_threshold_is_ignored(self):
        """Backwards compatibility: a pre-Session-20 projects.yaml."""
        config = ProjectsConfig(
            projects=[ManagedProject(name="demo", path="/srv/demo")]
        )
        assert config.alert_threshold_for("demo", "/srv/demo", 40) == 40

    def test_match_by_managed_name(self):
        config = ProjectsConfig(
            projects=[ManagedProject(name="demo", alert_threshold=70)]
        )
        assert config.alert_threshold_for("demo", None, 40) == 70

    def test_match_by_path(self, tmp_path):
        project = tmp_path / "SomeProject"
        project.mkdir()
        config = ProjectsConfig(
            projects=[
                ManagedProject(
                    name="friendly-name", path=str(project), alert_threshold=65
                )
            ]
        )
        # The scanner names the project after its directory, not the
        # projects.yaml name — the path still matches.
        assert config.alert_threshold_for("SomeProject", str(project), 40) == 65

    def test_match_by_path_basename(self):
        config = ProjectsConfig(
            projects=[
                ManagedProject(
                    name="personal-assistant",
                    path="/home/someone/projects/PersonalAssistant",
                    alert_threshold=25,
                )
            ]
        )
        assert config.alert_threshold_for("PersonalAssistant", None, 40) == 25

    def test_path_match_beats_name_match(self, tmp_path):
        project = tmp_path / "demo"
        project.mkdir()
        config = ProjectsConfig(
            projects=[
                ManagedProject(name="demo", alert_threshold=10),
                ManagedProject(name="other", path=str(project), alert_threshold=90),
            ]
        )
        assert config.alert_threshold_for("demo", str(project), 40) == 90

    def test_unmatched_project_falls_back(self):
        config = ProjectsConfig(
            projects=[ManagedProject(name="demo", alert_threshold=70)]
        )
        assert config.alert_threshold_for("elsewhere", "/srv/elsewhere", 40) == 40

    def test_zero_threshold_is_honoured_not_treated_as_absent(self):
        config = ProjectsConfig(
            projects=[ManagedProject(name="dormant", alert_threshold=0)]
        )
        assert config.alert_threshold_for("dormant", None, 40) == 0

    def test_loaded_from_yaml(self, tmp_path):
        raw = textwrap.dedent("""\
            projects:
              - name: demo
                path: /srv/demo
                alert_threshold: 55
              - name: legacy
                path: /srv/legacy
        """)
        config = ProjectsConfig.model_validate(_yaml_load(raw))

        assert config.alert_threshold_for("demo", None, 40) == 55
        assert config.alert_threshold_for("legacy", None, 40) == 40


def _yaml_load(raw: str):
    import yaml

    return yaml.safe_load(raw)


# ── status field + status_for (Session 21) ───────────────────────


class TestStatusFor:
    def test_none_when_no_entry_matches(self):
        config = ProjectsConfig(projects=[ManagedProject(name="other")])
        assert config.status_for("demo", "/p/demo") is None

    def test_none_when_entry_has_no_status(self):
        config = ProjectsConfig(projects=[ManagedProject(name="demo")])
        assert config.status_for("demo") is None

    def test_matches_by_name(self):
        config = ProjectsConfig(
            projects=[ManagedProject(name="demo", status="dormant")]
        )
        assert config.status_for("demo") == "dormant"

    def test_matches_by_path(self, tmp_path):
        config = ProjectsConfig(
            projects=[
                ManagedProject(
                    name="pretty-name", path=str(tmp_path), status="archived"
                )
            ]
        )
        assert config.status_for("ugly-dir-name", str(tmp_path)) == "archived"

    def test_matches_by_path_basename(self):
        config = ProjectsConfig(
            projects=[
                ManagedProject(
                    name="pretty-name", path="/p/UglyDirName", status="dormant"
                )
            ]
        )
        assert config.status_for("UglyDirName") == "dormant"

    def test_invalid_status_rejected(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ManagedProject(name="demo", status="retired")

    def test_has_explicit_alert_threshold(self):
        with_floor = ProjectsConfig(
            projects=[ManagedProject(name="demo", alert_threshold=0)]
        )
        without = ProjectsConfig(projects=[ManagedProject(name="demo")])

        assert with_floor.has_explicit_alert_threshold("demo") is True
        assert without.has_explicit_alert_threshold("demo") is False

    def test_alert_threshold_for_default_unchanged(self):
        """Regression: the Session 20 lookup still falls back to default."""
        config = ProjectsConfig(projects=[ManagedProject(name="other")])
        assert config.alert_threshold_for("demo", None, 40) == 40
