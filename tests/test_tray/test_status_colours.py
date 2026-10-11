"""The tray's one status-colour map, pinned to ``chk_health_status``.

``SNAG-TRAY-012``.  Two maps once coloured the status dots and neither
held ``critical``, ``warning`` or ``skipped``, so a critical service
showed the same grey as one nobody had checked — 311 ``critical`` rows
in the seven days before the fix.  The map's keys are now the
constraint's values exactly, read off its ``sqltext`` rather than
re-typed, and each of the three sites that draws a dot is driven through
every one of them, so a site that stops reading the map fails here too.
"""

from __future__ import annotations

import pytest

from sysadmin_tray.dashboard.projects_tab import ProjectCard
from sysadmin_tray.dashboard.services_tab import ServiceCard
from sysadmin_tray.models import (
    ManagedProjectInfo,
    ManagedServiceInfo,
    ServiceStatus,
)
from sysadmin_tray.styles import GREY, RED, STATUS_COLOURS, status_colour
from sysadmin_tray.widgets.service_grid import ServiceStatusRow
from tests.test_service_health_status import constraint_vocabulary

VOCABULARY = sorted(constraint_vocabulary())


class TestTheMapIsTheConstraint:
    def test_every_admitted_status_has_a_colour(self):
        assert set(VOCABULARY) <= set(STATUS_COLOURS)

    def test_nothing_is_coloured_that_the_database_would_reject(self):
        # The other direction: a key no row can hold is a colour nothing
        # draws, which is how ``active``/``inactive``/``failed`` sat here
        # from February until this fix.
        assert set(STATUS_COLOURS) <= set(VOCABULARY)

    def test_critical_is_red_not_grey(self):
        # The symptom the entry was opened for.
        assert status_colour("critical") == RED

    def test_an_unknown_status_falls_to_grey(self):
        # ``unknown`` is what /api/projects/managed sends for a service
        # with no health row; it is not in the CHECK and should not be.
        assert "unknown" not in STATUS_COLOURS
        assert status_colour("unknown") == GREY


@pytest.mark.parametrize("status", VOCABULARY)
class TestEverySiteReadsTheMap:
    def test_the_overview_row(self, qapp, status):
        row = ServiceStatusRow("svc")
        row.update_status(ServiceStatus(name="svc", status=status))
        assert f"color: {STATUS_COLOURS[status]};" in row._dot.styleSheet()

    def test_the_services_tab_card(self, fake_client, status):
        card = ServiceCard(ServiceStatus(name="svc", status=status), fake_client)
        assert f"color: {STATUS_COLOURS[status]};" in card._dot.styleSheet()

    def test_the_projects_tab_card(self, qapp, status):
        card = ProjectCard()
        card.update_from_managed(
            ManagedProjectInfo(
                name="proj",
                services=[ManagedServiceInfo(name="svc", status=status)],
            )
        )
        assert f'color:{STATUS_COLOURS[status]}"' in card._services_label.text()
