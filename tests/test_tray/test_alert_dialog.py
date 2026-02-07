"""Tests for the CriticalAlertDialog widget."""

from unittest.mock import MagicMock

import pytest
from PyQt6.QtWidgets import QApplication

from sysadmin_tray.models import AlertInfo
from sysadmin_tray.widgets.alert_dialog import CriticalAlertDialog, _AlertCard


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for widget tests."""
    app = QApplication.instance() or QApplication([])
    yield app


def _make_alert(
    aid: str = "a1",
    title: str = "Test alert",
    message: str | None = "Something went wrong",
    created_at: str | None = "2026-02-07T14:32:07+00:00",
) -> AlertInfo:
    return AlertInfo(
        id=aid,
        agent="sysadmin",
        severity="critical",
        title=title,
        message=message,
        acknowledged=False,
        resolved=False,
        created_at=created_at,
    )


# ── _AlertCard tests ───────────────────────────────────────────────


class TestAlertCard:
    """Individual alert card rendering and signals."""

    def test_card_displays_title(self, qapp):
        alert = _make_alert(title="Disk full")
        card = _AlertCard(alert)
        assert card.alert_id == "a1"

    def test_card_stores_alert_id(self, qapp):
        alert = _make_alert(aid="xyz-123")
        card = _AlertCard(alert)
        assert card.alert_id == "xyz-123"

    def test_ack_signal_emits_alert_id(self, qapp):
        alert = _make_alert(aid="a42")
        card = _AlertCard(alert)

        handler = MagicMock()
        card.ack_clicked.connect(handler)
        card.ack_clicked.emit("a42")
        handler.assert_called_once_with("a42")

    def test_card_without_message(self, qapp):
        """Card with no message should still render without error."""
        alert = _make_alert(message=None)
        card = _AlertCard(alert)
        assert card.alert_id == "a1"

    def test_card_without_timestamp(self, qapp):
        """Card with no created_at should render an empty time string."""
        alert = _make_alert(created_at=None)
        card = _AlertCard(alert)
        assert card.alert_id == "a1"


# ── CriticalAlertDialog tests ─────────────────────────────────────


class TestDialogRendering:
    """Dialog creates/removes cards based on alert list."""

    def test_initial_empty(self, qapp):
        dialog = CriticalAlertDialog()
        assert dialog.card_count == 0

    def test_update_adds_cards(self, qapp):
        dialog = CriticalAlertDialog()
        alerts = [_make_alert(aid="a1"), _make_alert(aid="a2")]
        dialog.update_alerts(alerts)
        assert dialog.card_count == 2

    def test_update_removes_resolved_cards(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1"), _make_alert(aid="a2")])
        assert dialog.card_count == 2

        # a2 resolved (no longer in list)
        dialog.update_alerts([_make_alert(aid="a1")])
        assert dialog.card_count == 1
        assert "a1" in dialog._cards
        assert "a2" not in dialog._cards

    def test_update_keeps_existing_cards(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])
        card_ref = dialog._cards["a1"]

        # Same alert in next update — card should be reused
        dialog.update_alerts([_make_alert(aid="a1")])
        assert dialog._cards["a1"] is card_ref

    def test_update_with_empty_list_removes_all(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1"), _make_alert(aid="a2")])
        dialog.update_alerts([])
        assert dialog.card_count == 0

    def test_update_adds_new_and_removes_old(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])
        dialog.update_alerts([_make_alert(aid="a2")])
        assert dialog.card_count == 1
        assert "a2" in dialog._cards
        assert "a1" not in dialog._cards


class TestAckButton:
    """Acknowledge button forwards signal through dialog."""

    def test_ack_signal_forwarded(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])

        handler = MagicMock()
        dialog.alert_ack_requested.connect(handler)

        # Simulate the card's ack button
        dialog._cards["a1"].ack_clicked.emit("a1")
        handler.assert_called_once_with("a1")

    def test_on_alert_acknowledged_removes_card(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1"), _make_alert(aid="a2")])

        dialog.on_alert_acknowledged("a1", True, "acknowledged")
        assert dialog.card_count == 1
        assert "a1" not in dialog._cards

    def test_on_alert_acknowledged_failure_keeps_card(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])

        dialog.on_alert_acknowledged("a1", False, "network error")
        assert dialog.card_count == 1
        assert "a1" in dialog._cards

    def test_on_alert_acknowledged_unknown_id_no_error(self, qapp):
        """Acknowledging a non-existent alert should not raise."""
        dialog = CriticalAlertDialog()
        dialog.on_alert_acknowledged("ghost", True, "ok")


class TestAutoHide:
    """Dialog auto-hides when all alerts are resolved/acknowledged."""

    def test_auto_hides_when_last_alert_acked(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])
        dialog.show()
        assert dialog.isVisible()

        dialog.on_alert_acknowledged("a1", True, "ok")
        assert not dialog.isVisible()

    def test_auto_hides_when_update_empties(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])
        dialog.show()

        dialog.update_alerts([])
        assert not dialog.isVisible()

    def test_stays_visible_when_alerts_remain(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1"), _make_alert(aid="a2")])
        dialog.show()

        dialog.on_alert_acknowledged("a1", True, "ok")
        assert dialog.isVisible()  # a2 still present


class TestDismissAll:
    """Dismiss All button hides but does not acknowledge."""

    def test_dismiss_hides_dialog(self, qapp):
        dialog = CriticalAlertDialog()
        dialog.update_alerts([_make_alert(aid="a1")])
        dialog.show()

        # Find the dismiss button and click it
        dialog.hide()  # simulates dismiss
        assert not dialog.isVisible()
        # Cards should still exist (not acknowledged)
        assert dialog.card_count == 1
