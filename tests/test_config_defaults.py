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
