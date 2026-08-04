"""Tests for the weekly portfolio review (Session 23).

NO live inference: the LLM client is always injected as a mock — a
returned string simulates llama-server answering, ``None`` simulates it
being down (which is :meth:`LLMClient.generate`'s real unavailable
behaviour). The GPU is never touched.
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.config import AgentsConfig, AppConfig, ProjectOrganiserConfig
from sysadmin.models.alert import Alert
from sysadmin.models.project_review import ProjectReview
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.services.project_review import (
    REVIEW_INSTRUCTIONS,
    build_fallback_narrative,
    build_movers_section,
    build_review_prompt,
    gather_review_data,
    generate_review,
    run_weekly_review,
)

MOD = "sysadmin.services.project_review"


def _snapshot(name, score, findings=None, scanned_days_ago=0):
    row = ProjectSnapshot(
        project_name=name,
        project_path=f"/projects/{name}",
        health_score=score,
        findings=findings or {},
    )
    row.scanned_at = datetime.now(UTC) - timedelta(days=scanned_days_ago)
    return row


def _result_all(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


def _gather_session(latest, baselines):
    """Session whose two execute() calls feed the latest + baseline queries."""
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[_result_all(latest), _result_all(baselines)]
    )
    return session


def _config():
    return AppConfig(
        agents=AgentsConfig(project_organiser=ProjectOrganiserConfig())
    )


def _llm(response):
    client = MagicMock()
    client.generate = AsyncMock(return_value=response)
    return client


DATA = {
    "period_days": 7,
    "projects": [
        {
            "name": "alpha", "status": "active", "score": 60, "delta": -15,
            "top_recommendations": [
                {"title": "Write a README.md", "points": 10, "severity": "advice"},
            ],
        },
        {
            "name": "beta", "status": "active", "score": 95, "delta": 5,
            "top_recommendations": [
                {"title": "Add a git remote", "points": 0, "severity": "risk"},
            ],
        },
        {
            "name": "old", "status": "archived", "score": 100, "delta": None,
            "top_recommendations": [],
        },
    ],
    "totals": {
        "project_count": 3, "active_count": 2, "average_active_score": 77.5,
        "risk_count": 1, "recoverable_points": 10,
    },
}


class TestGatherReviewData:
    @pytest.mark.asyncio
    async def test_deltas_against_oldest_snapshot_in_window(self):
        latest = [_snapshot("demo", 80)]
        baseline = [_snapshot("demo", 60, scanned_days_ago=6)]
        session = _gather_session(latest, baseline)

        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["projects"][0]["delta"] == 20

    @pytest.mark.asyncio
    async def test_single_snapshot_has_no_delta(self):
        row = _snapshot("demo", 80)
        session = _gather_session([row], [row])  # same row both times

        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["projects"][0]["delta"] is None

    @pytest.mark.asyncio
    async def test_totals_and_recommendations(self):
        latest = [
            _snapshot("risky", 100, {"no_remote": True}),
            _snapshot("messy", 80, {"missing_readme": True, "missing_claude_md": True}),
            _snapshot("old", 100, {"status": "archived"}),
        ]
        session = _gather_session(latest, [])

        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        totals = data["totals"]
        assert totals["project_count"] == 3
        assert totals["active_count"] == 2
        assert totals["risk_count"] == 1
        assert totals["recoverable_points"] == 20
        messy = next(p for p in data["projects"] if p["name"] == "messy")
        assert len(messy["top_recommendations"]) == 2


class TestPromptAndFallback:
    def test_prompt_contains_projects_and_instructions(self):
        prompt = build_review_prompt(DATA)

        assert "alpha [active] score 60 (delta -15)" in prompt
        assert "Write a README.md (+10)" in prompt
        assert "Add a git remote (RISK)" in prompt
        assert "old [archived] score 100 (delta n/a)" in prompt
        assert REVIEW_INSTRUCTIONS in prompt

    def test_movers_section_lists_changed_projects_only(self):
        assert build_movers_section(DATA) == "What moved: beta +5, alpha -15."

    def test_movers_section_when_nothing_moved(self):
        still = {**DATA, "projects": [
            {**p, "delta": None} for p in DATA["projects"]
        ]}
        assert build_movers_section(still) == (
            "What moved: no score changes this week."
        )

    def test_fallback_is_deterministic_and_complete(self):
        narrative = build_fallback_narrative(DATA)

        assert narrative == build_fallback_narrative(DATA)
        assert "without LLM narration" in narrative
        assert "beta +5" in narrative and "alpha -15" in narrative
        assert "Focus: alpha (score 60) — Write a README.md." in narrative


class TestGenerateReview:
    def _store_session(self, latest):
        session = _gather_session(latest, [])
        session.add = MagicMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_llm_narrative_stored(self):
        session = self._store_session([_snapshot("demo", 80)])

        with patch(f"{MOD}.get_config", return_value=_config()):
            review = await generate_review(session, llm_client=_llm("A good week."))

        # Hybrid assembly: deterministic movers line, then the LLM prose
        assert review.narrative.startswith("What moved:")
        assert review.narrative.endswith("A good week.")
        assert review.llm_used is True
        assert review.model_used  # from config.llm.model
        assert review.stats["totals"]["project_count"] == 1
        session.add.assert_called_once_with(review)

    @pytest.mark.asyncio
    async def test_llm_down_falls_back_to_digest(self):
        session = self._store_session([_snapshot("demo", 80)])

        with patch(f"{MOD}.get_config", return_value=_config()):
            review = await generate_review(session, llm_client=_llm(None))

        assert review.llm_used is False
        assert review.model_used is None
        assert "without LLM narration" in review.narrative

    @pytest.mark.asyncio
    async def test_no_snapshots_returns_none_and_stores_nothing(self):
        session = self._store_session([])

        with patch(f"{MOD}.get_config", return_value=_config()):
            review = await generate_review(session, llm_client=_llm("unused"))

        assert review is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_injected_client_lifecycle_untouched(self):
        """The caller's client must not be started or stopped by us."""
        session = self._store_session([_snapshot("demo", 80)])
        client = _llm("text")
        client.startup = AsyncMock()
        client.shutdown = AsyncMock()

        with patch(f"{MOD}.get_config", return_value=_config()):
            await generate_review(session, llm_client=client)

        client.startup.assert_not_called()
        client.shutdown.assert_not_called()


class TestRunWeeklyReview:
    def _scheduler_session(self):
        session = AsyncMock()
        session.add = MagicMock()

        @asynccontextmanager
        async def fake_scheduler_session():
            yield session

        return session, fake_scheduler_session

    @pytest.mark.asyncio
    async def test_generates_and_raises_info_alert(self):
        session, ctx = self._scheduler_session()
        review = ProjectReview(
            period_days=7, narrative="First line.\nSecond.", llm_used=True
        )
        review.id = "11111111-1111-1111-1111-111111111111"

        with (
            patch(f"{MOD}.get_scheduler_session", ctx),
            patch(f"{MOD}.generate_review", new=AsyncMock(return_value=review)),
        ):
            await run_weekly_review()

        (alert,) = session.add.call_args[0]
        assert isinstance(alert, Alert)
        assert alert.agent == "project_organiser"
        assert alert.severity == "info"
        assert alert.message == "First line."
        assert alert.details["endpoint"] == "/api/projects/review"

    @pytest.mark.asyncio
    async def test_no_review_no_alert(self):
        session, ctx = self._scheduler_session()

        with (
            patch(f"{MOD}.get_scheduler_session", ctx),
            patch(f"{MOD}.generate_review", new=AsyncMock(return_value=None)),
        ):
            await run_weekly_review()

        session.add.assert_not_called()
