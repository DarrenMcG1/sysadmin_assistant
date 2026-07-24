"""Session 14 — shared defaults and config-lifted magic numbers.

Guards against the backend and tray drifting apart on host/port, and
pins the defaults for values that used to be hard-coded in routers/main.
"""

from sysadmin.config import (
    AppConfig,
    FileOrganiserConfig,
    HealthGradeBands,
    MonitoredService,
    SchedulesConfig,
    ServiceConfig,
)
from sysadmin.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT, default_api_url
from sysadmin_tray.config import TrayConfig, load_tray_config


class TestSharedDefaults:
    def test_backend_service_config_uses_shared_defaults(self):
        svc = ServiceConfig()
        assert svc.host == DEFAULT_API_HOST
        assert svc.port == DEFAULT_API_PORT

    def test_tray_default_api_url_matches_shared_defaults(self):
        assert TrayConfig().api_url == default_api_url()
        assert TrayConfig().api_url == f"http://{DEFAULT_API_HOST}:{DEFAULT_API_PORT}"

    def test_tray_fallback_without_config_file_uses_shared_defaults(self, tmp_path):
        cfg = load_tray_config(config_path=tmp_path / "missing.yaml")
        assert cfg.api_url == default_api_url()

    def test_default_api_url_formats_overrides(self):
        assert default_api_url("192.168.1.10", 9000) == "http://192.168.1.10:9000"


class TestLiftedMagicNumbers:
    def test_grade_bands_defaults(self):
        bands = HealthGradeBands()
        assert (bands.healthy_min, bands.needs_attention_min, bands.neglected_min) == (
            80,
            60,
            40,
        )

    def test_reclaimable_milestones_default(self):
        assert FileOrganiserConfig().reclaimable_milestones_mb == [1024, 5120, 10240]

    def test_schedules_defaults(self):
        s = SchedulesConfig()
        assert (s.briefing_hour, s.briefing_minute) == (6, 0)
        assert (s.retention_hour, s.retention_minute) == (3, 0)

    def test_cors_origins_default(self):
        assert ServiceConfig().cors_origins == [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    def test_app_config_exposes_new_sections(self):
        cfg = AppConfig()
        assert cfg.schedules.briefing_hour == 6
        assert cfg.agents.project_organiser.grade_bands.healthy_min == 80
        assert cfg.agents.file_organiser.reclaimable_milestones_mb[0] == 1024


class TestMonitoredServiceMute:
    """Session 16 — per-service mute flag for expected-down services."""

    def test_mute_defaults_to_false(self):
        svc = MonitoredService(name="redis", type="tcp")
        assert svc.mute is False

    def test_mute_can_be_set(self):
        svc = MonitoredService(name="redis", type="tcp", mute=True)
        assert svc.mute is True


class TestSession17Defaults:
    """Self-monitoring, SSE, and anomaly-detection tunables."""

    def test_self_monitor_defaults(self):
        cfg = AppConfig().self_monitor
        assert cfg.enabled is True
        assert cfg.stall_grace_multiplier == 3.0
        assert cfg.min_stall_grace_seconds == 300
        assert cfg.recent_runs == 10

    def test_events_defaults(self):
        cfg = AppConfig().events
        assert cfg.heartbeat_seconds == 20.0
        assert cfg.max_queued_events == 100
        assert cfg.retry_ms == 5000

    def test_anomaly_defaults(self):
        cfg = AppConfig().agents.sysadmin.anomaly
        assert cfg.enabled is True
        assert cfg.window_days == 7
        assert cfg.z_threshold == 3.0
        assert cfg.min_samples == 30
        assert cfg.min_stdev == 1.0
        assert cfg.severity == "warning"

    def test_repo_config_yaml_declares_the_new_sections(self):
        """The committed config.yaml must still validate with the new blocks."""
        from pathlib import Path

        import yaml

        raw = yaml.safe_load(
            (Path(__file__).parent.parent / "config.yaml").read_text()
        )
        cfg = AppConfig.model_validate(raw)

        assert cfg.self_monitor.stall_grace_multiplier == 3.0
        assert cfg.events.heartbeat_seconds == 20
        assert cfg.agents.sysadmin.anomaly.z_threshold == 3.0


class TestSession18Defaults:
    """File-action settings and the interval-job first-run delay."""

    def test_file_actions_defaults(self):
        cfg = AppConfig().agents.file_organiser.actions
        assert cfg.enabled is True
        assert cfg.downloads_dir == "Downloads"
        assert cfg.archive_dir == "Archives/Downloads"
        assert cfg.duplicate_strategy == "newest"
        assert cfg.pdf_book_min_pages == 50
        assert cfg.max_operations == 200
        # Permanent deletion is opt-in — trashing is the default
        assert cfg.allow_permanent_delete is False
        assert cfg.trash_dir is None

    def test_default_category_folders(self):
        folders = AppConfig().agents.file_organiser.actions.category_folders
        assert folders == {
            "images": "Pictures",
            "videos": "Videos",
            "documents": "Documents",
            "audio": "Music",
            "books": "Books",
            "archives": "Archives",
        }

    def test_category_mapping_is_config_driven(self):
        """Retargeting a category needs no code change."""
        cfg = FileOrganiserConfig.model_validate(
            {"actions": {"category_folders": {"images": "Media/Photos"}}}
        )
        assert cfg.actions.category_folders["images"] == "Media/Photos"

    def test_agent_first_run_delay_default(self):
        assert SchedulesConfig().agent_first_run_delay_seconds == 60

    def test_repo_config_yaml_declares_the_action_settings(self):
        from pathlib import Path

        import yaml

        raw = yaml.safe_load(
            (Path(__file__).parent.parent / "config.yaml").read_text()
        )
        cfg = AppConfig.model_validate(raw)

        actions = cfg.agents.file_organiser.actions
        assert actions.enabled is True
        assert actions.allow_permanent_delete is False
        assert actions.category_folders["books"] == "Books"
        assert actions.category_folders["archives"] == "Archives"
        assert ".py" in actions.code_extensions
        assert cfg.schedules.agent_first_run_delay_seconds == 60
