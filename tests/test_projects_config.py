"""Tests for projects.yaml config models, merge logic, and backward compatibility."""

import textwrap
from pathlib import Path

from sysadmin.config import (
    AppConfig,
    ManagedProject,
    MonitoredService,
    ProjectEndpoint,
    ProjectEndpointLog,
    ProjectsConfig,
    _merge_projects_config,
    load_config,
)

# ── Model construction ───────────────────────────────────────────


class TestProjectEndpointLog:
    def test_defaults(self):
        log = ProjectEndpointLog()
        assert log.type == "journalctl"
        assert log.unit is None
        assert log.path is None
        assert log.severity_filter == "warning"

    def test_file_type(self):
        log = ProjectEndpointLog(type="file", path="/var/log/app.log", severity_filter="error")
        assert log.type == "file"
        assert log.path == "/var/log/app.log"


class TestProjectEndpoint:
    def test_minimal(self):
        ep = ProjectEndpoint(url="http://localhost:8000/health")
        assert ep.url == "http://localhost:8000/health"
        assert ep.port is None
        assert ep.systemd_unit is None
        assert ep.log is None

    def test_full(self):
        ep = ProjectEndpoint(
            url="http://localhost:8000/health",
            port=8000,
            systemd_unit="app.service",
            log=ProjectEndpointLog(unit="app.service"),
        )
        assert ep.port == 8000
        assert ep.log.unit == "app.service"


class TestManagedProject:
    def test_minimal(self):
        proj = ManagedProject(name="my-app")
        assert proj.name == "my-app"
        assert proj.path is None
        assert proj.backend is None
        assert proj.frontend is None

    def test_to_monitored_services_backend_only(self):
        proj = ManagedProject(
            name="my-app",
            backend=ProjectEndpoint(
                url="http://localhost:8000/health",
                systemd_unit="my-app.service",
            ),
        )
        services = proj.to_monitored_services()
        assert len(services) == 1
        assert services[0].name == "my-app"
        assert services[0].type == "http"
        assert services[0].url == "http://localhost:8000/health"
        assert services[0].systemd_unit == "my-app.service"

    def test_to_monitored_services_backend_and_frontend(self):
        proj = ManagedProject(
            name="my-app",
            backend=ProjectEndpoint(url="http://localhost:8000/health"),
            frontend=ProjectEndpoint(url="http://localhost:3000"),
        )
        services = proj.to_monitored_services()
        assert len(services) == 2
        assert services[0].name == "my-app"
        assert services[1].name == "my-app-frontend"

    def test_to_monitored_services_no_url(self):
        """Endpoints without a URL should not generate a service."""
        proj = ManagedProject(
            name="my-app",
            backend=ProjectEndpoint(systemd_unit="my-app.service"),
        )
        assert proj.to_monitored_services() == []

    def test_to_log_sources_backend(self):
        proj = ManagedProject(
            name="my-app",
            backend=ProjectEndpoint(
                log=ProjectEndpointLog(unit="my-app.service", severity_filter="error"),
            ),
        )
        sources = proj.to_log_sources()
        assert len(sources) == 1
        assert sources[0].name == "my-app"
        assert sources[0].unit == "my-app.service"
        assert sources[0].severity_filter == "error"

    def test_to_log_sources_frontend_naming(self):
        """Frontend log sources should include '-frontend' suffix."""
        proj = ManagedProject(
            name="my-app",
            frontend=ProjectEndpoint(
                log=ProjectEndpointLog(type="file", path="/var/log/nuxt.log"),
            ),
        )
        sources = proj.to_log_sources()
        assert len(sources) == 1
        assert sources[0].name == "my-app-frontend"
        assert sources[0].type == "file"
        assert sources[0].path == "/var/log/nuxt.log"

    def test_to_log_sources_no_log(self):
        """Endpoints without a log block should not generate sources."""
        proj = ManagedProject(
            name="my-app",
            backend=ProjectEndpoint(url="http://localhost:8000/health"),
        )
        assert proj.to_log_sources() == []


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


class TestMergeProjectsConfig:
    def test_missing_file_is_noop(self, tmp_path):
        """No projects.yaml → config unchanged (backward compat)."""
        config = AppConfig()
        _merge_projects_config(config, tmp_path / "projects.yaml")
        assert config.projects.projects == []
        assert config.agents.sysadmin.services == []

    def test_merges_services_and_sources(self, tmp_path):
        projects_file = tmp_path / "projects.yaml"
        _write_yaml(projects_file, """\
            projects:
              - name: foo
                backend:
                  url: http://localhost:9000/health
                  systemd_unit: foo.service
                  log:
                    unit: foo.service
                    severity_filter: error
        """)
        config = AppConfig()
        _merge_projects_config(config, projects_file)

        assert len(config.agents.sysadmin.services) == 1
        assert config.agents.sysadmin.services[0].name == "foo"

        assert len(config.agents.log_aggregator.sources) == 1
        assert config.agents.log_aggregator.sources[0].name == "foo"
        assert config.agents.log_aggregator.sources[0].severity_filter == "error"

    def test_deduplication_prefers_existing(self, tmp_path):
        """If config.yaml already has a service named 'foo', projects.yaml doesn't overwrite."""
        projects_file = tmp_path / "projects.yaml"
        _write_yaml(projects_file, """\
            projects:
              - name: foo
                backend:
                  url: http://localhost:9999/health
        """)
        config = AppConfig()
        existing = MonitoredService(name="foo", type="tcp", host="localhost", port=1234)
        config.agents.sysadmin.services.append(existing)

        _merge_projects_config(config, projects_file)

        # Still only the original entry
        assert len(config.agents.sysadmin.services) == 1
        assert config.agents.sysadmin.services[0].type == "tcp"

    def test_malformed_yaml_logs_warning(self, tmp_path, caplog):
        """Malformed projects.yaml should warn but not crash."""
        projects_file = tmp_path / "projects.yaml"
        projects_file.write_text("projects:\n  - name: 123\n    backend: [invalid")

        config = AppConfig()
        _merge_projects_config(config, projects_file)

        assert config.projects.projects == []
        assert "failed to load" in caplog.text

    def test_multiple_projects(self, tmp_path):
        projects_file = tmp_path / "projects.yaml"
        _write_yaml(projects_file, """\
            projects:
              - name: app-a
                backend:
                  url: http://localhost:8001/health
                frontend:
                  url: http://localhost:3001
              - name: app-b
                backend:
                  url: http://localhost:8002/health
                  log:
                    unit: app-b.service
        """)
        config = AppConfig()
        _merge_projects_config(config, projects_file)

        svc_names = {s.name for s in config.agents.sysadmin.services}
        assert svc_names == {"app-a", "app-a-frontend", "app-b"}

        src_names = {s.name for s in config.agents.log_aggregator.sources}
        assert src_names == {"app-b"}


# ── Full load_config integration ─────────────────────────────────


class TestLoadConfigIntegration:
    def test_load_with_projects_yaml(self, tmp_path):
        """load_config() merges a sibling projects.yaml."""
        config_file = tmp_path / "config.yaml"
        _write_yaml(config_file, """\
            service:
              port: 8500
            agents:
              sysadmin:
                services:
                  - name: postgresql
                    type: systemd
                    systemd_unit: postgresql.service
        """)
        projects_file = tmp_path / "projects.yaml"
        _write_yaml(projects_file, """\
            projects:
              - name: my-app
                backend:
                  url: http://localhost:8000/health
        """)

        # Reset singleton
        import sysadmin.config as cfg
        cfg._config = None

        config = load_config(config_file)
        svc_names = [s.name for s in config.agents.sysadmin.services]
        assert "postgresql" in svc_names
        assert "my-app" in svc_names
        assert len(config.projects.projects) == 1

        # Clean up singleton
        cfg._config = None

    def test_load_without_projects_yaml(self, tmp_path):
        """load_config() works when projects.yaml doesn't exist."""
        config_file = tmp_path / "config.yaml"
        _write_yaml(config_file, """\
            service:
              port: 8500
        """)

        import sysadmin.config as cfg
        cfg._config = None

        config = load_config(config_file)
        assert config.projects.projects == []
        assert config.agents.sysadmin.services == []

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
