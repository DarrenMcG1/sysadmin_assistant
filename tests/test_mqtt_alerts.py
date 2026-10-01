"""Raised alerts on the estate bus, and the gates before them.

What is pinned is the shape of what reaches ``estate.bus.publish`` — its
arguments are the whole contract with the broker — and the four ways an
event is declined before a subprocess is spent: disabled, below the
floor, a row the run's rollback removed, and no credential.
"""

import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from estate.bus import BrokerIdentity, PublishError, publish

from sysadmin.core.config import MqttNotificationsConfig, parse_config
from sysadmin.monitor.mqtt_alerts import (
    CREDENTIALS_ENV,
    SOURCE,
    MqttAlertPublisher,
    build_payload,
)

NOW = datetime(2026, 10, 1, 21, 0, tzinfo=UTC)

RAISED = {
    "id": "1f0e0d3a-0000-4000-8000-000000000000",
    "agent": "sysadmin",
    "severity": "critical",
    "title": "venture-chat unreachable",
    "message": "GET http://127.0.0.1:8301/api/health refused",
}


def publisher(*, rows: int = 1, publish_fn=None) -> tuple[MqttAlertPublisher, MagicMock]:
    """A publisher whose read-back finds ``rows`` rows, and its spy."""
    session = MagicMock()
    session.scalar = AsyncMock(return_value=rows)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    spy = MagicMock(side_effect=publish_fn)
    return (
        MqttAlertPublisher(
            session_factory=lambda: session, publisher=spy, clock=lambda: NOW
        ),
        spy,
    )


@pytest.fixture
def credentials(tmp_path, monkeypatch) -> Path:
    """What ``LoadCredential=mqtt:…`` leaves behind: one line, the password."""
    (tmp_path / "mqtt").write_text("s3cret\n", encoding="utf-8")
    monkeypatch.setenv(CREDENTIALS_ENV, str(tmp_path))
    return tmp_path


async def handle(mqtt: MqttAlertPublisher, event=None, *, config=None) -> None:
    settings = MagicMock()
    settings.notifications.mqtt = config or MqttNotificationsConfig(enabled=True)
    with patch("sysadmin.monitor.mqtt_alerts.get_config", return_value=settings):
        await mqtt.on_alert_raised(dict(event or RAISED))


class TestWhatReachesTheBroker:
    async def test_a_critical_is_published_once(self, credentials):
        mqtt, spy = publisher()
        await handle(mqtt)

        spy.assert_called_once()
        identity, topic, payload = spy.call_args.args
        assert topic == "estate/alerts/raised"
        assert identity == BrokerIdentity(
            username="sysadmin-publisher", password="s3cret"
        )
        assert payload["title"] == "venture-chat unreachable"

    async def test_never_retained(self, credentials):
        """An alert is an event: a retained one is a lie by morning."""
        mqtt, spy = publisher()
        await handle(mqtt)

        assert spy.call_args.kwargs["retain"] is False

    async def test_the_configured_identity_and_bound_are_the_ones_used(
        self, credentials
    ):
        (credentials / "other").write_text("pw2\n", encoding="utf-8")
        config = MqttNotificationsConfig(
            enabled=True,
            host="192.168.1.2",
            port=1884,
            username="someone-else",
            credential="other",
            topic="estate/alerts/elsewhere",
            timeout_seconds=1.5,
        )
        mqtt, spy = publisher()
        await handle(mqtt, config=config)

        identity, topic, _ = spy.call_args.args
        assert identity == BrokerIdentity(
            username="someone-else", password="pw2", host="192.168.1.2", port=1884
        )
        assert topic == "estate/alerts/elsewhere"
        assert spy.call_args.kwargs["timeout_s"] == 1.5

    def test_the_payload_is_flat_and_names_its_source(self):
        payload = build_payload(RAISED, NOW)

        assert payload == {
            "source": SOURCE,
            "id": RAISED["id"],
            "agent": "sysadmin",
            "severity": "critical",
            "title": "venture-chat unreachable",
            "message": RAISED["message"],
            "published_at": "2026-10-01T21:00:00+00:00",
        }
        assert SOURCE == "sysadmin-assistant"

    def test_a_missing_message_is_null_not_the_string_none(self):
        assert build_payload({**RAISED, "message": None}, NOW)["message"] is None

    async def test_the_wire_argv_is_estate_bus_unchanged(self, credentials):
        """Driven through the real ``publish`` with only the runner swapped.

        The publisher passes ``retain`` and ``timeout_s`` by keyword into a
        library it does not own, so a renamed parameter there must fail
        here rather than at 3 a.m.
        """
        runner = MagicMock(
            return_value=subprocess.CompletedProcess([], 0, stdout="", stderr="")
        )

        def real(identity, topic, payload, **kwargs):
            publish(identity, topic, payload, runner=runner, **kwargs)

        mqtt, _ = publisher(publish_fn=real)
        await handle(mqtt)

        argv = runner.call_args.args[0]
        assert argv[0] == "mosquitto_pub"
        assert argv[argv.index("-t") + 1] == "estate/alerts/raised"
        assert argv[argv.index("-u") + 1] == "sysadmin-publisher"
        assert argv[argv.index("-q") + 1] == "1"
        assert "-r" not in argv
        assert '"title": "venture-chat unreachable"' in runner.call_args.kwargs["input"]


class TestTheGates:
    @pytest.mark.parametrize(
        ("floor", "severity", "published"),
        [
            ("critical", "critical", True),
            ("critical", "warning", False),
            ("critical", "info", False),
            ("warning", "warning", True),
            ("warning", "critical", True),
            ("warning", "info", False),
            ("info", "info", True),
        ],
    )
    async def test_the_floor_is_this_rung_and_every_louder_one(
        self, credentials, floor, severity, published
    ):
        mqtt, spy = publisher()
        await handle(
            mqtt,
            {**RAISED, "severity": severity},
            config=MqttNotificationsConfig(enabled=True, min_severity=floor),
        )

        assert spy.called is published

    async def test_an_unknown_floor_fails_closed_to_critical(self, credentials):
        """A typo in config.yaml must not open the floor to every warning."""
        mqtt, spy = publisher()
        await handle(
            mqtt,
            {**RAISED, "severity": "warning"},
            config=MqttNotificationsConfig(enabled=True, min_severity="warnin"),
        )

        spy.assert_not_called()

    async def test_disabled_publishes_nothing(self, credentials):
        mqtt, spy = publisher()
        await handle(mqtt, config=MqttNotificationsConfig(enabled=False))

        spy.assert_not_called()

    def test_the_model_defaults_off_and_the_shipped_file_turns_it_on(self):
        """Off for a process the unit did not start; on for the one it did."""
        assert MqttNotificationsConfig().enabled is False

        shipped = parse_config().notifications.mqtt
        assert shipped.enabled is True
        assert shipped.min_severity == "critical"
        assert shipped.topic.startswith("estate/")

    async def test_a_row_the_rollback_removed_is_not_announced(self, credentials):
        """``BaseAgent.run`` flushes events whatever the run's outcome."""
        mqtt, spy = publisher(rows=0)
        await handle(mqtt)

        spy.assert_not_called()

    async def test_an_unparseable_id_is_not_a_row(self, credentials):
        mqtt, spy = publisher()
        await handle(mqtt, {**RAISED, "id": "not-a-uuid"})

        spy.assert_not_called()

    async def test_no_credentials_directory_is_reported_and_quiet(
        self, monkeypatch, caplog
    ):
        monkeypatch.delenv(CREDENTIALS_ENV, raising=False)
        mqtt, spy = publisher()
        with caplog.at_level(logging.WARNING, logger="sysadmin.monitor.mqtt_alerts"):
            await handle(mqtt)

        spy.assert_not_called()
        assert "mqtt_alert_no_credential" in caplog.messages


class TestFailureIsLoggedNeverRaised:
    async def test_a_broker_refusal_is_a_warning(self, credentials, caplog):
        def refuse(identity, topic, payload, **kwargs):
            raise PublishError("exited 5", topic=topic, returncode=5)

        mqtt, spy = publisher(publish_fn=refuse)
        with caplog.at_level(logging.WARNING, logger="sysadmin.monitor.mqtt_alerts"):
            await handle(mqtt)

        spy.assert_called_once()
        assert "mqtt_alert_publish_failed" in caplog.messages

    async def test_an_empty_credential_file_is_a_warning(self, credentials, caplog):
        (credentials / "mqtt").write_text("", encoding="utf-8")
        mqtt, spy = publisher()
        with caplog.at_level(logging.WARNING, logger="sysadmin.monitor.mqtt_alerts"):
            await handle(mqtt)

        spy.assert_not_called()
        assert "mqtt_alert_publish_failed" in caplog.messages

    async def test_anything_else_is_contained(self, credentials):
        """A raising subscriber takes the bus's task down for the others."""

        def explode(*args, **kwargs):
            raise RuntimeError("boom")

        mqtt, _ = publisher(publish_fn=explode)
        await handle(mqtt)  # must not raise


def test_it_is_subscribed_at_startup():
    """Built and never wired is a feature that reads exactly like a quiet day."""
    source = Path("sysadmin/main.py").read_text(encoding="utf-8")
    assert (
        'event_bus.subscribe("alert.raised", mqtt_alert_publisher.on_alert_raised)'
        in source
    )
