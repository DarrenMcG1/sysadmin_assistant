"""Tests for tray configuration loading."""

from pathlib import Path
from textwrap import dedent

import pytest

from sysadmin_tray.config import TrayConfig, load_tray_config


@pytest.fixture
def tmp_config(tmp_path: Path) -> Path:
    """Write a minimal config.yaml and return its path."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(dedent("""\
        service:
          host: 127.0.0.1
          port: 8500

        tray:
          status_poll_seconds: 5
          resource_poll_seconds: 20
          alert_poll_seconds: 10
          dashboard_url: http://localhost:3000
    """))
    return cfg


class TestTrayConfig:
    """TrayConfig Pydantic model."""

    def test_defaults(self):
        cfg = TrayConfig()
        assert cfg.api_url == "http://127.0.0.1:8500"
        assert cfg.status_poll_seconds == 10
        assert cfg.resource_poll_seconds == 30
        assert cfg.alert_poll_seconds == 15
        assert cfg.show_notifications is True
        assert cfg.notify_min_severity == "critical"
        assert cfg.dashboard_url is None

    def test_notification_calm_defaults(self):
        cfg = TrayConfig()
        assert cfg.flap_cooldown_minutes == 30
        assert cfg.escalation_polls == 3
        assert cfg.coalesce_threshold == 2
        assert cfg.snooze_minutes == 60
        assert cfg.digest_mode is False
        assert cfg.digest_interval_minutes == 60
        assert cfg.respect_desktop_dnd is True
        assert cfg.muted_services == []

    def test_custom_values(self):
        cfg = TrayConfig(
            api_url="http://10.0.0.5:9000",
            status_poll_seconds=5,
        )
        assert cfg.api_url == "http://10.0.0.5:9000"
        assert cfg.status_poll_seconds == 5


class TestLoadTrayConfig:
    """load_tray_config() YAML + override resolution."""

    def test_loads_from_yaml(self, tmp_config: Path):
        cfg = load_tray_config(config_path=tmp_config)
        assert cfg.api_url == "http://127.0.0.1:8500"
        assert cfg.status_poll_seconds == 5
        assert cfg.resource_poll_seconds == 20
        assert cfg.alert_poll_seconds == 10
        assert cfg.dashboard_url == "http://localhost:3000"

    def test_derives_url_from_service_section(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            service:
              host: 192.168.1.50
              port: 9999
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.api_url == "http://192.168.1.50:9999"

    def test_cli_override_wins(self, tmp_config: Path):
        cfg = load_tray_config(
            config_path=tmp_config,
            api_url_override="http://remote:7777",
        )
        assert cfg.api_url == "http://remote:7777"
        # Other settings still come from YAML
        assert cfg.status_poll_seconds == 5

    def test_missing_file_uses_defaults(self, tmp_path: Path):
        missing = tmp_path / "nonexistent.yaml"
        cfg = load_tray_config(config_path=missing)
        assert cfg.api_url == "http://127.0.0.1:8500"
        assert cfg.status_poll_seconds == 10

    def test_notify_min_severity_from_yaml(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            tray:
              notify_min_severity: warning
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.notify_min_severity == "warning"

    def test_notify_min_severity_default(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            tray:
              status_poll_seconds: 5
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.notify_min_severity == "critical"

    def test_auth_token_from_api_section(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            api:
              auth_token: abc123def456
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.auth_token == "abc123def456"

    def test_auth_token_defaults_to_none(self, tmp_config: Path):
        cfg = load_tray_config(config_path=tmp_config)
        assert cfg.auth_token is None

    def test_empty_auth_token_stays_none(self, tmp_path: Path):
        """The committed placeholder (empty string) means auth disabled."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            api:
              auth_token: ""
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.auth_token is None

    def test_empty_yaml(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("")
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.api_url == "http://127.0.0.1:8500"


class TestNotificationCalmConfig:
    """The ``notifications.tray:`` section and per-service muting."""

    def test_tunables_loaded(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            notifications:
              tray:
                flap_cooldown_minutes: 45
                escalation_polls: 5
                coalesce_threshold: 3
                snooze_minutes: 15
                digest_mode: true
                digest_interval_minutes: 120
                respect_desktop_dnd: false
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.flap_cooldown_minutes == 45
        assert cfg.escalation_polls == 5
        assert cfg.coalesce_threshold == 3
        assert cfg.snooze_minutes == 15
        assert cfg.digest_mode is True
        assert cfg.digest_interval_minutes == 120
        assert cfg.respect_desktop_dnd is False

    def test_partial_section_keeps_defaults(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            notifications:
              tray:
                digest_mode: true
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.digest_mode is True
        assert cfg.flap_cooldown_minutes == 30
        assert cfg.escalation_polls == 3

    def test_explicit_mute_services(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            notifications:
              tray:
                mute_services:
                  - redis
                  - personal-assistant
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.muted_services == ["redis", "personal-assistant"]

    def test_monitored_service_mute_flag(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            agents:
              sysadmin:
                services:
                  - name: postgresql
                    type: systemd
                  - name: redis
                    type: tcp
                    mute: true
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.muted_services == ["redis"]

    def test_mute_sources_are_unioned_without_duplicates(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            notifications:
              tray:
                mute_services:
                  - redis
            agents:
              sysadmin:
                services:
                  - name: redis
                    type: tcp
                    mute: true
                  - name: personal-assistant
                    type: http
                    mute: true
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.muted_services == ["redis", "personal-assistant"]

    def test_no_mutes_by_default(self, tmp_config: Path):
        assert load_tray_config(config_path=tmp_config).muted_services == []

    def test_real_config_yaml_parses(self):
        """The committed config.yaml must load through the tray model."""
        repo_root = Path(__file__).resolve().parents[2]
        cfg = load_tray_config(config_path=repo_root / "config.yaml")
        assert cfg.flap_cooldown_minutes == 30
        assert cfg.digest_mode is False
        assert cfg.muted_services == []
