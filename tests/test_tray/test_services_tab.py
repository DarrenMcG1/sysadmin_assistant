"""Tests for :class:`~sysadmin_tray.dashboard.services_tab.ServicesTab`.

**SNAG-AGENT-008, volume half.** The tab is built eagerly at tray startup
and wired to ``status_updated`` unconditionally, so before this gate it
issued one ``/details`` request per systemd-backed service on every status
poll — whether or not the dashboard had ever been opened.  Measured on the
live box 2026-08-17: 1,160 of the 1,347 journal lines ``sysadmin.service``
wrote in ten minutes were that fan-out answering itself.

The first test is the guard: it fails against the ungated code with the
whole service list, which is what makes the gate falsifiable rather than
merely present.
"""

from __future__ import annotations

import pytest

from sysadmin_tray.dashboard.services_tab import ServicesTab
from sysadmin_tray.models import ServiceStatus, StatusResponse


def _status() -> StatusResponse:
    """Two systemd-backed services and one without a unit."""
    return StatusResponse(
        services=[
            ServiceStatus(name="postgresql", status="ok", systemd_unit="postgresql.service"),
            ServiceStatus(name="mosquitto", status="ok", systemd_unit="mosquitto.service"),
            ServiceStatus(name="internet", status="ok"),
        ]
    )


@pytest.fixture
def tab(fake_client):
    widget = ServicesTab(fake_client)
    yield widget
    widget.deleteLater()


class TestDetailFanOutIsGated:
    def test_hidden_tab_requests_no_details(self, tab, fake_client):
        """The guard. Ungated, this records one call per systemd service."""
        assert not tab.isVisible()
        fake_client.status_updated.emit(_status())
        assert fake_client.called("request_service_details") == 0

    def test_cards_are_still_built_while_hidden(self, tab, fake_client):
        """Only the fan-out is gated — the cards are in memory and cheap.

        The window can be shown at any moment, so a tab that skipped the
        card update entirely would open empty and stay empty until the next
        poll.  Gating the network call and not the widget update is the
        whole distinction the change rests on.
        """
        fake_client.status_updated.emit(_status())
        assert set(tab._cards) == {"postgresql", "mosquitto", "internet"}

    def test_visible_tab_requests_details_for_systemd_services_only(
        self, tab, fake_client
    ):
        tab.show()
        fake_client.status_updated.emit(_status())
        asked = {c[1] for c in fake_client.calls if c[0] == "request_service_details"}
        assert asked == {"postgresql", "mosquitto"}

    def test_hiding_stops_the_fan_out_again(self, tab, fake_client):
        """The gate is read per poll, not latched at construction."""
        tab.show()
        fake_client.status_updated.emit(_status())
        before = fake_client.called("request_service_details")
        assert before == 2
        tab.hide()
        fake_client.status_updated.emit(_status())
        assert fake_client.called("request_service_details") == before


class TestRefreshCoversTheWarmTab:
    def test_refresh_asks_for_details_of_cards_already_held(self, tab, fake_client):
        """A tab shown after polls it ignored must not sit blank.

        Cards built while hidden carry no systemd detail.  ``refresh`` is
        the moment the tab becomes visible, and requesting status alone
        would leave those cards empty for up to ``status_poll_seconds``.
        """
        fake_client.status_updated.emit(_status())  # hidden: cards, no details
        assert fake_client.called("request_service_details") == 0

        tab.show()
        tab.refresh()
        asked = {c[1] for c in fake_client.calls if c[0] == "request_service_details"}
        assert asked == {"postgresql", "mosquitto"}

    def test_refresh_still_requests_status(self, tab, fake_client):
        """The cold-tab half: no cards yet, so only status can help."""
        tab.refresh()
        assert fake_client.called("request_status") == 1
        assert fake_client.called("request_service_details") == 0

    def test_has_systemd_unit_follows_the_latest_status(self, tab, fake_client):
        """A unit declaration removed by a reload stops being fetched."""
        fake_client.status_updated.emit(_status())
        tab._cards["postgresql"].update_status(
            ServiceStatus(name="postgresql", status="ok")
        )
        tab.show()
        tab.refresh()
        asked = {c[1] for c in fake_client.calls if c[0] == "request_service_details"}
        assert asked == {"mosquitto"}
