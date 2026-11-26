"""Raised alerts on the estate bus, and the gates before them.

What is pinned is the shape of what reaches ``estate.bus.publish`` — its
arguments are the whole contract with the broker — and the four ways an
event is declined before a subprocess is spent: disabled, below the
floor, a row the run's rollback removed, and no credential. And the
``kind`` mark, from its ``services.yaml`` declaration to the wire.
"""

import logging
import subprocess
import typing
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from estate.bus import BrokerIdentity, PublishError, publish
from pydantic import ValidationError

from sysadmin.core.config import MqttNotificationsConfig, parse_config
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.mqtt_alerts import (
    ALERT_KIND_DETAIL,
    CREDENTIALS_ENV,
    RESTART_FAILED_KIND,
    SOURCE,
    MqttAlertPublisher,
    build_payload,
)
from sysadmin.monitor.services import OutageKind, ServiceEntry, load_services

NOW = datetime(2026, 10, 1, 21, 0, tzinfo=UTC)

RAISED = {
    "id": "1f0e0d3a-0000-4000-8000-000000000000",
    "agent": "sysadmin",
    "severity": "critical",
    "title": "venture-chat unreachable",
    "message": "GET http://127.0.0.1:8301/api/health refused",
}


def publisher(
    *, rows: int = 1, details: dict | None = None, publish_fn=None
) -> tuple[MqttAlertPublisher, MagicMock]:
    """A publisher whose read-back finds ``rows`` rows with ``details``, and its spy."""
    result = MagicMock()
    result.first.return_value = (details if details is not None else {},) if rows else None
    session = MagicMock()
    session.execute = AsyncMock(return_value=result)
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
            "kind": None,
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


class TestTheKind:
    """alfred-glance's message ``db66a2c0``: mark the owner's phone item 1."""

    async def test_a_marked_row_publishes_its_kind(self, credentials):
        mqtt, spy = publisher(details={ALERT_KIND_DETAIL: "alfred-down"})
        await handle(mqtt, {**RAISED, "title": "alfred unreachable"})

        assert spy.call_args.args[2]["kind"] == "alfred-down"

    async def test_an_unmarked_row_publishes_null_and_keeps_the_key(self, credentials):
        """The backup timer going inactive is the critical glance must not push."""
        mqtt, spy = publisher(details={ALERT_KIND_DETAIL: None})
        await handle(mqtt, {**RAISED, "title": "pgbackrest-backup-timer critical"})

        payload = spy.call_args.args[2]
        assert "kind" in payload and payload["kind"] is None

    async def test_a_row_with_null_details_still_publishes(self, credentials):
        mqtt, spy = publisher(details=None)
        await handle(mqtt)

        assert spy.call_args.args[2]["kind"] is None

    def test_the_shipped_file_marks_alfreds_backend_and_frontend_only(self):
        services = load_services(Path("services.yaml")).services
        marked = {s.name: s.outage_kind for s in services if s.outage_kind}

        assert marked == {"alfred": "alfred-down", "alfred-frontend": "alfred-down"}
        backup = next(s for s in services if s.name == "pgbackrest-backup-timer")
        assert backup.outage_kind is None

    def test_a_misspelt_kind_fails_at_load(self):
        with pytest.raises(ValidationError):
            ServiceEntry(name="x", kind="tcp", host="h", port=1, outage_kind="alfred-dwn")

    def test_build_payload_names_every_value_it_can_carry(self):
        """glance's decoder names ``build_payload`` as its authority."""
        doc = build_payload.__doc__ or ""
        for value in (*typing.get_args(OutageKind), RESTART_FAILED_KIND):
            assert f'"{value}"' in doc

    def test_the_restart_kind_cannot_be_declared(self):
        """Phone item 2 is the monitor's finding, never a services.yaml claim."""
        assert RESTART_FAILED_KIND == "restart-failed"
        assert RESTART_FAILED_KIND not in typing.get_args(OutageKind)
        with pytest.raises(ValidationError):
            ServiceEntry(
                name="x", kind="tcp", host="h", port=1, outage_kind=RESTART_FAILED_KIND
            )

    async def test_a_restart_failed_row_publishes_its_kind(self, credentials):
        mqtt, spy = publisher(details={ALERT_KIND_DETAIL: RESTART_FAILED_KIND})
        await handle(mqtt, {**RAISED, "title": "alfred restart-failed"})

        assert spy.call_args.args[2]["kind"] == "restart-failed"

    @pytest.mark.parametrize(
        ("declared", "status"),
        [("alfred-down", "unreachable"), ("alfred-down", "critical"), (None, "critical")],
    )
    async def test_the_outage_path_writes_the_declared_kind(
        self, mock_session, declared, status
    ):
        svc = ServiceEntry(
            name="alfred",
            kind="http",
            url="http://localhost:8100/api/health",
            port=8100,
            systemd={"unit": "alfred-backend.service", "scope": "user"},
            outage_kind=declared,
        )
        agent = SysAdminAgent()
        with patch.object(agent, "raise_alert", new_callable=AsyncMock) as ra:
            await agent._handle_status(mock_session, svc, status, {})

        assert ra.call_args.kwargs["severity"] == "critical"
        details = ra.call_args.kwargs["details"]
        assert ALERT_KIND_DETAIL in details
        assert details[ALERT_KIND_DETAIL] == declared


def test_it_is_subscribed_at_startup():
    """Built and never wired is a feature that reads exactly like a quiet day."""
    source = Path("sysadmin/main.py").read_text(encoding="utf-8")
    assert (
        'event_bus.subscribe("alert.raised", mqtt_alert_publisher.on_alert_raised)'
        in source
    )
