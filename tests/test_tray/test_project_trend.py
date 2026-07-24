"""Tests for the per-project health trend chart on the Projects tab."""

from __future__ import annotations

import pytest

from sysadmin_tray.dashboard.projects_tab import ProjectsTab
from sysadmin_tray.models import (
    ManagedProjectsResponse,
    ProjectDetailResponse,
    ProjectOverviewResponse,
)

from .conftest import render_offscreen

OVERVIEW_PAYLOAD = {
    "projects": [
        {
            "name": "sysadmin_assistant",
            "health_score": 88,
            "grade": "healthy",
            "branch_count": 3,
            "stale_branch_count": 0,
            "todo_count": 12,
        },
        {
            "name": "PA-auto",
            "health_score": 34,
            "grade": "neglected",
            "branch_count": 186,
            "stale_branch_count": 170,
            "todo_count": 400,
        },
    ],
    "count": 2,
}

MANAGED_PAYLOAD = {
    "projects": [
        {
            "name": "personal-assistant",
            "path": "/home/gaddi/projects/PersonalAssistant",
            "project_health": {"health_score": 72},
            "services": [],
        }
    ],
    "count": 1,
}

DETAIL_PAYLOAD = {
    "name": "sysadmin_assistant",
    "current": {"health_score": 88},
    "history": [
        {"health_score": 88, "scanned_at": "2026-07-24T02:00:00+00:00"},
        {"health_score": 84, "scanned_at": "2026-07-23T02:00:00+00:00"},
        {"health_score": 79, "scanned_at": "2026-07-22T02:00:00+00:00"},
    ],
}


@pytest.fixture
def tab(fake_client):
    return ProjectsTab(fake_client)


def _cards(tab, fake_client, payload=OVERVIEW_PAYLOAD):
    tab._view_combo.setCurrentIndex(1)  # "All Projects"
    fake_client.project_overview_updated.emit(
        ProjectOverviewResponse.from_dict(payload)
    )
    return tab._cards


class TestTrendChartPresence:
    def test_chart_starts_empty_with_a_prompt(self, tab):
        assert tab._trend_chart.has_data is False
        assert tab._trend_title.text() == "Health Trend"

    def test_renders_headless_before_selection(self, tab):
        assert not render_offscreen(tab, width=900, height=700).isNull()


class TestProjectSelection:
    def test_cards_carry_their_project_name(self, tab, fake_client):
        cards = _cards(tab, fake_client)
        assert [c.project_name for c in cards] == ["sysadmin_assistant", "PA-auto"]

    def test_managed_cards_carry_their_project_name(self, tab, fake_client):
        fake_client.managed_projects_updated.emit(
            ManagedProjectsResponse.from_dict(MANAGED_PAYLOAD)
        )
        assert tab._cards[0].project_name == "personal-assistant"

    def test_clicking_a_card_requests_its_history(self, tab, fake_client):
        cards = _cards(tab, fake_client)
        cards[0].clicked.emit(cards[0].project_name)

        call = next(c for c in fake_client.calls if c[0] == "request_project_detail")
        assert call[1] == "sysadmin_assistant"
        assert tab._trend_title.text() == "Health Trend — sysadmin_assistant"

    def test_selection_is_highlighted(self, tab, fake_client):
        cards = _cards(tab, fake_client)
        cards[1].clicked.emit(cards[1].project_name)
        assert "#3498db" in cards[1].styleSheet()
        assert "#3498db" not in cards[0].styleSheet()

    def test_selection_survives_a_re_render(self, tab, fake_client):
        cards = _cards(tab, fake_client)
        cards[0].clicked.emit(cards[0].project_name)
        # A fresh overview rebuilds every card
        fake_client.project_overview_updated.emit(
            ProjectOverviewResponse.from_dict(OVERVIEW_PAYLOAD)
        )
        assert "#3498db" in tab._cards[0].styleSheet()

    def test_refresh_re_requests_the_selected_project(self, tab, fake_client):
        cards = _cards(tab, fake_client)
        cards[0].clicked.emit(cards[0].project_name)
        before = fake_client.called("request_project_detail")
        tab.refresh()
        assert fake_client.called("request_project_detail") == before + 1

    def test_refresh_without_a_selection_asks_for_no_detail(self, tab, fake_client):
        tab.refresh()
        assert fake_client.called("request_project_detail") == 0


class TestTrendPlotting:
    def _select(self, tab, fake_client, name="sysadmin_assistant"):
        cards = _cards(tab, fake_client)
        card = next(c for c in cards if c.project_name == name)
        card.clicked.emit(name)

    def test_history_is_plotted_oldest_first(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant", ProjectDetailResponse.from_dict(DETAIL_PAYLOAD)
        )
        assert tab._trend_chart.has_data is True
        # The endpoint returns newest-first; the chart must reverse it.
        assert tab._trend_chart._series[0].values == [79.0, 84.0, 88.0]
        assert "latest 88/100" in tab._status_label.text()

    def test_a_single_snapshot_still_plots(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant",
            ProjectDetailResponse.from_dict(
                {
                    "name": "sysadmin_assistant",
                    "history": [
                        {"health_score": 88, "scanned_at": "2026-07-24T02:00:00+00:00"}
                    ],
                }
            ),
        )
        assert tab._trend_chart.has_data is True
        assert not render_offscreen(tab._trend_chart).isNull()

    def test_empty_history_shows_a_message(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant",
            ProjectDetailResponse.from_dict({"name": "sysadmin_assistant", "history": []}),
        )
        assert tab._trend_chart.has_data is False
        assert "No snapshots recorded" in tab._trend_chart._placeholder

    def test_points_without_timestamps_are_dropped(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant",
            ProjectDetailResponse.from_dict(
                {
                    "history": [
                        {"health_score": 88, "scanned_at": "2026-07-24T02:00:00+00:00"},
                        {"health_score": 0, "scanned_at": None},
                    ]
                }
            ),
        )
        assert tab._trend_chart._series[0].values == [88.0]

    def test_unavailable_history_shows_a_message(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit("sysadmin_assistant", None)
        assert tab._trend_chart.has_data is False
        assert "History unavailable" in tab._trend_chart._placeholder

    def test_late_reply_for_a_different_project_is_ignored(self, tab, fake_client):
        self._select(tab, fake_client, "PA-auto")
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant", ProjectDetailResponse.from_dict(DETAIL_PAYLOAD)
        )
        assert tab._trend_chart.has_data is False

    def test_switching_projects_replaces_the_series(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant", ProjectDetailResponse.from_dict(DETAIL_PAYLOAD)
        )
        tab._cards[1].clicked.emit("PA-auto")
        assert tab._trend_chart.has_data is False

        fake_client.project_detail_updated.emit(
            "PA-auto",
            ProjectDetailResponse.from_dict(
                {
                    "history": [
                        {"health_score": 34, "scanned_at": "2026-07-24T02:00:00+00:00"},
                        {"health_score": 40, "scanned_at": "2026-07-23T02:00:00+00:00"},
                    ]
                }
            ),
        )
        assert tab._trend_chart._series[0].values == [40.0, 34.0]

    def test_renders_headless_with_a_plotted_trend(self, tab, fake_client):
        self._select(tab, fake_client)
        fake_client.project_detail_updated.emit(
            "sysadmin_assistant", ProjectDetailResponse.from_dict(DETAIL_PAYLOAD)
        )
        assert not render_offscreen(tab, width=900, height=700).isNull()
