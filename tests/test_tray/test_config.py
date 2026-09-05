"""Tests for tray configuration loading."""

import logging
import tempfile
from contextlib import contextmanager
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from sysadmin.core.config import FOREIGN_KEYS, AppConfig
from sysadmin.core.config_keys import report_for_file
from sysadmin_tray.config import (
    TRAY_SECTION_KEYS,
    TrayConfig,
    load_tray_config,
    tray_section_report,
)


@contextmanager
def caplog_at_warning():
    """Every ``WARNING`` this module emits, as whole records.

    Read through ``getMessage()`` by the tests below, which models the
    consumer: the tray's formatter is ``main()``'s
    ``basicConfig(format="… %(message)s")``, so a payload passed as
    ``extra=`` — the *backend's* convention, readable only because
    ``JsonFormatter`` folds it in — reaches the journal as a bare event
    name naming no key.  A live drive is what caught that, and asserting
    the rendered message is what keeps it caught.
    """
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    logger = logging.getLogger("sysadmin_tray.config")
    handler = _Capture()
    logger.addHandler(handler)
    previous, logger.level = logger.level, logging.WARNING
    try:
        yield records
    finally:
        logger.removeHandler(handler)
        logger.level = previous


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
        assert cfg.reminder_hours == 24.0
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
                reminder_hours: 6
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.flap_cooldown_minutes == 45
        assert cfg.escalation_polls == 5
        assert cfg.coalesce_threshold == 3
        assert cfg.snooze_minutes == 15
        assert cfg.digest_mode is True
        assert cfg.digest_interval_minutes == 120
        assert cfg.respect_desktop_dnd is False
        assert cfg.reminder_hours == 6

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

    def test_service_mute_flag(self, tmp_path: Path):
        """``mute:`` moved to services.yaml with the rest of the topology."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("service:\n  port: 8500\n")
        (tmp_path / "services.yaml").write_text(dedent("""\
            schema: 1
            services:
              - name: postgresql
                kind: systemd
                systemd: {unit: postgresql.service, scope: system}
              - name: redis
                kind: tcp
                host: localhost
                port: 6379
                mute: true
        """))
        cfg = load_tray_config(config_path=cfg_file)
        assert cfg.muted_services == ["redis"]

    def test_missing_services_yaml_costs_a_mute_list_not_a_launch(
        self, tmp_path: Path
    ):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("service:\n  port: 8500\n")
        assert load_tray_config(config_path=cfg_file).muted_services == []

    def test_mute_sources_are_unioned_without_duplicates(self, tmp_path: Path):
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            notifications:
              tray:
                mute_services:
                  - redis
        """))
        (tmp_path / "services.yaml").write_text(dedent("""\
            schema: 1
            services:
              - name: redis
                kind: tcp
                host: localhost
                port: 6379
                mute: true
              - name: personal-assistant
                kind: http
                url: http://localhost:8000/health
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


class TestUnreadTraySectionKeys:
    """``SNAG-CFG-005`` — the tray reports the keys it does not read.

    The backend exempts ``tray:`` whole (``FOREIGN_KEYS``) because
    holding a model of another parser's section is the second-owner
    defect, so this program is the only one that can say a key under it
    went unread.  Each test below was driven at code that fails it before
    it was written down.
    """

    def test_an_unread_key_is_named(self):
        report = tray_section_report({"status_poll_seconds": 5, "nope": 1})
        assert report.unknown == ["tray.nope"]
        assert report.unwalkable == []

    def test_every_shipped_key_is_read(self):
        """The fix ships untriggered — the committed file has no residue."""
        repo_root = Path(__file__).resolve().parents[2]
        raw = yaml.safe_load((repo_root / "config.yaml").read_text())
        report = tray_section_report(raw.get("tray"))
        assert report.clean, f"config.yaml's tray: has unread keys: {report.unknown}"

    def test_the_allowlist_is_the_authority_not_the_model(self):
        """Rule 1: ``TrayConfig`` over-declares relative to this section.

        ``reminder_hours`` is a real field on the model and is read from
        ``notifications.tray:``.  Setting it under ``tray:`` does
        nothing, so a walk against the model — the obvious fix, and the
        shape :mod:`sysadmin.core.config_keys` uses for ``AppConfig`` —
        would call it declared and ship green.
        """
        assert "reminder_hours" in TrayConfig.model_fields
        assert "reminder_hours" not in TRAY_SECTION_KEYS
        assert tray_section_report({"reminder_hours": 5}).unknown == ["tray.reminder_hours"]

    def test_notifications_tray_is_not_this_functions_business(self):
        """Rule 2: that region is exempted by *leaf*, so the backend names it.

        One fact, one speaker.  Driven at the backend rather than
        asserted, because the claim is about what the other program does.
        """
        repo_root = Path(__file__).resolve().parents[2]
        raw = yaml.safe_load((repo_root / "config.yaml").read_text())
        raw["notifications"]["tray"]["digest_modee"] = True
        path = repo_root / "config.yaml"
        with tempfile.TemporaryDirectory() as tmp:
            specimen = Path(tmp) / "config.yaml"
            specimen.write_text(yaml.safe_dump(raw))
            report = report_for_file(specimen, AppConfig, foreign=FOREIGN_KEYS)
        assert "notifications.tray.digest_modee" in report.unknown
        assert path.exists()

    def test_this_module_never_speaks_outside_its_own_section(self):
        """The negative half of rule 2, which the test above does not carry.

        Driving the backend proves the other speaker *exists*; it does
        not stop this one from becoming a second.  Without this,
        appending a ``notifications.tray.*`` path to the report goes red
        on an unrelated test by accident, which is a rule with no guard.
        """
        report = tray_section_report(
            {"nope": 1, "reminder_hours": 2, "status_poll_seconds": 3}
        )
        assert report.unknown
        assert all(path.startswith("tray.") for path in report.unknown), report.unknown
        # Was `all(path == "tray" for path in report.unwalkable)`, which is
        # True over the empty list this input produces and therefore
        # asserted nothing — `SNAG-TEST-009`'s one live positive finding,
        # and the reason the gate now reads branch arcs.  Stating the
        # emptiness directly is both decidable and stronger: it separates
        # "nothing was unwalkable" from "some things were, and all of them
        # happened to be spelled `tray`".
        assert report.unwalkable == []

    def test_a_non_mapping_section_is_unwalkable_not_clean(self):
        """Rule 3: zero unknown keys because nothing was read."""
        for shape in (5, [], ["a"], "text"):
            report = tray_section_report(shape)
            assert report.unwalkable == ["tray"], shape
            assert report.unknown == []
            assert not report.clean, shape

    def test_an_absent_section_is_clean_not_unwalkable(self):
        """``tray:`` with nothing under it carries no key to be wrong about.

        Separated from the shape above because the remedies differ and
        because reporting it blind would warn on every file that omits
        the section — which is how a report gets filtered.
        """
        assert tray_section_report(None).clean

    def test_the_loader_warns_and_still_loads(self, tmp_path: Path):
        """Rule 4: it reports, it cannot refuse."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            tray:
              status_poll_seconds: 5
              status_poll_secondss: 99
        """))
        with caplog_at_warning() as records:
            cfg = load_tray_config(config_path=cfg_file)
        assert cfg.status_poll_seconds == 5
        assert len(records) == 1
        assert records[0].getMessage().startswith("tray_config_unknown_keys")
        assert "tray.status_poll_secondss" in records[0].getMessage()

    def test_a_malformed_section_no_longer_crashes_the_tray(self, tmp_path: Path):
        """Until 2026-08-30 this raised ``TypeError`` out of ``key in 5``."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("tray: 5\n")
        with caplog_at_warning() as records:
            cfg = load_tray_config(config_path=cfg_file)
        assert cfg.status_poll_seconds == TrayConfig().status_poll_seconds
        assert len(records) == 1
        assert records[0].getMessage().startswith("tray_config_unwalked_section")
        assert "config.yaml's tray: is not a mapping" in records[0].getMessage()

    def test_a_clean_file_says_nothing(self, tmp_config: Path):
        with caplog_at_warning() as records:
            load_tray_config(config_path=tmp_config)
        assert records == []

    def test_a_falsy_malformed_section_survives_the_call_site(self, tmp_path: Path):
        """``tray: []`` is falsy *and* malformed.

        The loader must not pre-coerce with ``or {}``: that hands the
        report a clean ``{}`` and the shape goes unreported.  This is the
        one test that separates the two, and it was red against the first
        draft of the fix.
        """
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("tray: []\n")
        with caplog_at_warning() as records:
            load_tray_config(config_path=cfg_file)
        assert records[0].getMessage().startswith("tray_config_unwalked_section")

    def test_the_url_the_docstring_used_to_promise_is_reported(self, tmp_path: Path):
        """``tray.api_url`` has never been read, since ``81b3bfb``.

        The loader docstring listed the ``tray:`` section as resolution
        priority 2 for ``api_url`` for the module's whole life, and the
        ``if "api_url" not in kwargs`` guard beneath it was dead by
        construction.  A reader who checks the report against the old
        docstring concludes the report is broken, so the two had to move
        together.
        """
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(dedent("""\
            service:
              host: 127.0.0.1
              port: 8500
            tray:
              api_url: http://bogus:1234
        """))
        with caplog_at_warning() as records:
            cfg = load_tray_config(config_path=cfg_file)
        assert cfg.api_url == "http://127.0.0.1:8500"
        assert "tray.api_url" in records[0].getMessage()

    def test_the_estate_url_is_read_from_here_and_stays_silent(self, tmp_path: Path):
        """The asymmetry with ``api_url`` is deliberate: 8400 has no ``service:``."""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("tray:\n  estate_api_url: http://127.0.0.1:8401\n")
        with caplog_at_warning() as records:
            cfg = load_tray_config(config_path=cfg_file)
        assert cfg.estate_api_url == "http://127.0.0.1:8401"
        assert records == []
