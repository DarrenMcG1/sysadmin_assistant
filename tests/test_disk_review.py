"""Tests for the weekly disk review (Session 24 Tier 3).

NO live inference: the LLM client is always injected as a mock — a
returned string simulates llama-server answering, ``None`` simulates it
being down (which is :meth:`LLMClient.generate`'s real unavailable
behaviour). The GPU is never touched.

The thing worth guarding hardest is the **numbers boundary**: every
figure must come from ``build_facts_section``, never from the model.
Session 23 proved a 3B model will happily invent movement under two
different prompts, so the prompt is asserted to forbid figures and the
narrative is asserted to carry the deterministic block regardless.
"""

import re
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.config import AgentsConfig, AppConfig, FileOrganiserConfig
from sysadmin.models.alert import Alert
from sysadmin.models.disk_review import DiskReview
from sysadmin.models.filesystem_audit import FilesystemAudit
from sysadmin.services.disk_review import (
    REVIEW_INSTRUCTIONS,
    build_facts_section,
    build_fallback_narrative,
    build_review_prompt,
    gather_review_data,
    generate_review,
    run_weekly_review,
    size_band,
    strip_markdown,
)

MOD = "sysadmin.services.disk_review"
BASE = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)


def _audit(
    scanned_days_ago: float = 0,
    reclaimable_mb: int = 0,
    findings: dict | None = None,
    **counts,
) -> FilesystemAudit:
    row = FilesystemAudit(
        scan_root="/home/gaddi",
        total_reclaimable_mb=reclaimable_mb,
        findings=findings or {},
        duplicate_groups_count=counts.get("duplicates", 0),
        old_downloads_count=counts.get("downloads", 0),
        misplaced_files_count=counts.get("misplaced", 0),
        large_files_count=counts.get("large", 0),
        empty_dirs_count=counts.get("empty", 0),
        similar_folders_count=counts.get("similar", 0),
        stale_project_dirs_count=counts.get("stale_dirs", 0),
    )
    row.id = f"audit-{scanned_days_ago}"
    row.scanned_at = datetime.now(UTC) - timedelta(days=scanned_days_ago)
    return row


def _downloads(count: int, size_mb: float) -> dict:
    return {
        "old_downloads": [
            {"path": f"/d/{i}", "days_old": 90, "size_mb": size_mb}
            for i in range(count)
        ]
    }


def _result_first(row):
    result = MagicMock()
    result.scalars.return_value.first.return_value = row
    return result


def _disk_rows(percents: list[float], mount: str = "/") -> list:
    return [
        MagicMock(
            recorded_at=BASE + timedelta(days=i),
            disk_usage={mount: {"total_gb": 500.0, "percent": pct}},
        )
        for i, pct in enumerate(percents)
    ]


def _gather_session(latest, baseline, disk_rows):
    """Three executes: latest audit, baseline audit, resource snapshots."""
    session = AsyncMock()
    snapshots = MagicMock()
    snapshots.all.return_value = disk_rows
    session.execute = AsyncMock(
        side_effect=[_result_first(latest), _result_first(baseline), snapshots]
    )
    return session


def _config():
    return AppConfig(agents=AgentsConfig(file_organiser=FileOrganiserConfig()))


def _llm(response):
    client = MagicMock()
    client.generate = AsyncMock(return_value=response)
    return client


DATA = {
    "period_days": 7,
    "disk": {
        "mount": "/",
        "current_percent": 78.0,
        "baseline_percent": 74.0,
        "delta_pp": 4.0,
        "samples": 7,
        "projection": {
            "percent": 80.0,
            "state": "projected",
            "days_from_now": 4.0,
            "date": "2026-08-10",
        },
    },
    "audit": {
        "scanned_at": "2026-08-06T09:00:00+00:00",
        "baseline_scanned_at": "2026-07-30T09:00:00+00:00",
        "stale_dirs_mb": 25000,
        "stale_dirs_delta_mb": 1200,
        "counts": {
            "duplicate_groups": {"now": 200, "delta": 12},
            "old_downloads": {"now": 11400, "delta": -340},
            "misplaced_files": {"now": 11877, "delta": 2100},
        },
    },
    "actions": {
        "top": [
            {
                "kind": "rebuildable_dirs",
                "title": "Delete 50 rebuildable dependency directories",
                "severity": "advice",
                "reclaimable_mb": 25000.0,
                "action": "Delete by hand",
            },
            {
                "kind": "downloads",
                "title": "Clear 11400 stale downloads",
                "severity": "advice",
                "reclaimable_mb": 900.0,
                "action": "POST /api/files/clean/downloads",
            },
        ],
        "by_kind": {
            "rebuildable_dirs": {"now_mb": 25000.0, "delta_mb": 1200.0},
            "downloads": {"now_mb": 900.0, "delta_mb": -340.0},
            "empty_dirs": {"now_mb": 0.0, "delta_mb": None},
        },
        "total_reclaimable_mb": 25900.0,
        "risk_count": 0,
        "action_count": 4,
    },
}


class TestGatherReviewData:
    @pytest.mark.asyncio
    async def test_two_tables_feed_one_picture(self):
        """Occupancy comes from resource_snapshots, junk from the audit."""
        session = _gather_session(
            _audit(0, reclaimable_mb=25000, downloads=11400),
            _audit(7, reclaimable_mb=23800, downloads=11740),
            _disk_rows([74.0, 75.0, 76.0, 77.0, 78.0]),
        )
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["disk"]["current_percent"] == 78.0
        assert data["disk"]["baseline_percent"] == 74.0
        assert data["disk"]["delta_pp"] == 4.0
        assert data["audit"]["stale_dirs_delta_mb"] == 1200
        assert data["audit"]["counts"]["old_downloads"]["delta"] == -340

    @pytest.mark.asyncio
    async def test_no_baseline_gives_none_deltas_not_zero(self):
        """"Unchanged" and "unknown" are different answers."""
        session = _gather_session(
            _audit(0, reclaimable_mb=25000, downloads=100), None, _disk_rows([70.0])
        )
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["audit"]["stale_dirs_delta_mb"] is None
        assert data["audit"]["counts"]["old_downloads"]["delta"] is None
        assert data["disk"]["delta_pp"] is None

    @pytest.mark.asyncio
    async def test_a_lone_audit_is_not_its_own_baseline(self):
        """Comparing a row with itself would report a spurious "no change"."""
        only = _audit(0, reclaimable_mb=25000)
        session = _gather_session(only, only, _disk_rows([70.0, 71.0]))
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["audit"]["baseline_scanned_at"] is None
        assert data["audit"]["stale_dirs_delta_mb"] is None

    @pytest.mark.asyncio
    async def test_no_audit_at_all_returns_empty(self):
        session = _gather_session(None, None, [])
        with patch(f"{MOD}.get_config", return_value=_config()):
            assert await gather_review_data(session) == {}

    @pytest.mark.asyncio
    async def test_no_disk_samples_is_not_zero_percent(self):
        session = _gather_session(_audit(0), None, [])
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["disk"]["current_percent"] is None
        assert data["disk"]["projection"] is None

    @pytest.mark.asyncio
    async def test_per_kind_reclaim_is_diffed_against_the_baseline(self):
        session = _gather_session(
            _audit(0, findings=_downloads(10, 100.0), downloads=10),
            _audit(7, findings=_downloads(10, 60.0), downloads=10),
            _disk_rows([70.0, 71.0]),
        )
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        downloads = data["actions"]["by_kind"]["downloads"]
        assert downloads["now_mb"] == pytest.approx(1000.0)
        assert downloads["delta_mb"] == pytest.approx(400.0)

    @pytest.mark.asyncio
    async def test_a_kind_absent_a_week_ago_has_no_delta(self):
        session = _gather_session(
            _audit(0, findings=_downloads(5, 10.0), downloads=5),
            _audit(7, findings={}, downloads=0),
            _disk_rows([70.0, 71.0]),
        )
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["actions"]["by_kind"]["downloads"]["delta_mb"] is None

    @pytest.mark.asyncio
    async def test_imminent_crossing_becomes_a_risk_action(self):
        # 75 % climbing 1 pp/day crosses 80 % inside the risk horizon
        session = _gather_session(
            _audit(0, findings=_downloads(5, 10.0), downloads=5),
            None,
            _disk_rows([70.0, 71.0, 72.0, 73.0, 74.0, 75.0]),
        )
        with patch(f"{MOD}.get_config", return_value=_config()):
            data = await gather_review_data(session)

        assert data["disk"]["projection"]["state"] == "projected"
        assert data["actions"]["risk_count"] == 1


class TestFactsSection:
    """Every number in the narrative is produced here, not by the model."""

    def test_reports_occupancy_delta_and_crossing(self):
        text = build_facts_section(DATA)
        assert "78.0% used" in text
        assert "+4.0 pp" in text
        assert "crosses 80% around 2026-08-10" in text

    def test_reports_movers_largest_absolute_change_first(self):
        text = build_facts_section(DATA)
        moved = next(ln for ln in text.splitlines() if ln.startswith("Moved:"))
        assert moved.index("rebuildable_dirs") < moved.index("downloads")
        assert "+1.2 GB" in moved
        assert "-340 MB" in moved

    def test_kinds_with_no_delta_are_omitted_from_movers(self):
        text = build_facts_section(DATA)
        assert "empty_dirs" not in text

    def test_says_so_when_there_is_no_earlier_scan(self):
        data = {
            **DATA,
            "audit": {
                **DATA["audit"],
                "baseline_scanned_at": None,
                "counts": {"duplicate_groups": {"now": 5, "delta": None}},
            },
        }
        assert "deltas unavailable" in build_facts_section(data)

    def test_no_samples_is_stated_not_silently_zero(self):
        data = {
            **DATA,
            "disk": {**DATA["disk"], "current_percent": None, "delta_pp": None},
        }
        assert "no occupancy samples" in build_facts_section(data)

    def test_not_growing_says_no_threshold_course(self):
        data = {
            **DATA,
            "disk": {
                **DATA["disk"],
                "projection": {"percent": 80.0, "state": "not_growing"},
            },
        }
        assert "not on course to cross a threshold" in build_facts_section(data)


class TestPromptIsFigureFree:
    """The prompt must contain no digits outside API paths.

    Found live 2026-08-06: given a prompt carrying "25.0 GB across 50
    directories" and an instruction not to restate figures,
    dria-agent-a-3b restated them *and* published the quotient as
    "each consuming 5GB". Instructing a model not to use a number it can
    see is a request; not showing it one is a constraint. These tests
    guard the constraint.
    """

    def _data_lines(self, prompt: str) -> list[str]:
        """The facts half of the prompt, with API paths stripped.

        The instructions are excluded: they legitimately carry digits
        ("Hard limit 150 words") and are fixed text, not data. API paths
        are stripped because an executor like ``/api/files/clean`` is
        something the model must be able to quote verbatim.
        """
        facts = prompt.split(REVIEW_INSTRUCTIONS)[0]
        return [re.sub(r"/api/\S+", "", line) for line in facts.splitlines()]

    def test_no_digits_reach_the_model(self):
        for line in self._data_lines(build_review_prompt(DATA)):
            assert not re.search(r"\d", line), f"figure leaked into prompt: {line!r}"

    def test_sizes_become_bands_not_megabytes(self):
        prompt = build_review_prompt(DATA)
        assert "very large" in prompt          # 25 GB of rebuildable dirs
        assert "25.0 GB" not in prompt
        assert "25000" not in prompt

    def test_counts_in_tier_2_titles_never_reach_the_model(self):
        """Titles like "Clear 11400 stale downloads" are the leak path."""
        prompt = build_review_prompt(DATA)
        assert "11400" not in prompt
        assert "stale downloads in ~/Downloads" in prompt

    def test_occupancy_is_a_direction_not_a_percentage(self):
        prompt = build_review_prompt(DATA)
        assert "78" not in prompt
        assert "filling up" in prompt and "rising noticeably" in prompt

    def test_crossing_horizon_is_qualitative(self):
        """A 4-day crossing says "soon"; the date stays in the facts block."""
        assert "expected soon" in build_review_prompt(DATA)
        assert "2026-08-10" not in build_review_prompt(DATA)

    def test_distant_crossing_reads_as_years(self):
        data = {
            **DATA,
            "disk": {
                **DATA["disk"],
                "projection": {
                    "percent": 80.0,
                    "state": "projected",
                    "days_from_now": 925.0,
                    "date": "2029-02-16",
                },
            },
        }
        assert "No threshold crossing is expected for years" in build_review_prompt(
            data
        )

    def test_movement_is_direction_only(self):
        prompt = build_review_prompt(DATA)
        assert "rebuildable dependency directories" in prompt
        assert ": grew" in prompt and ": shrank" in prompt

    def test_executors_still_reach_the_model(self):
        """The model must be able to quote a real action."""
        assert "POST /api/files/clean/downloads" in build_review_prompt(DATA)

    def test_instructions_are_attached(self):
        assert REVIEW_INSTRUCTIONS in build_review_prompt(DATA)

    def test_risk_actions_are_marked(self):
        data = {
            **DATA,
            "actions": {
                **DATA["actions"],
                "top": [
                    {
                        "kind": "risk",
                        "title": "Disk crosses 80% soon",
                        "severity": "risk",
                        "reclaimable_mb": 0.0,
                        "action": "Act on the reclaim items below",
                    }
                ],
            },
        }
        prompt = build_review_prompt(data)
        assert "[RISK]" in prompt
        assert "a projected disk threshold crossing" in prompt


class TestSizeBands:
    @pytest.mark.parametrize(
        ("mb", "expected"),
        [
            (25000.0, "very large"),
            (10240.0, "very large"),
            (5000.0, "large"),
            (1024.0, "large"),
            (500.0, "moderate"),
            (0.0, "frees no space"),
        ],
    )
    def test_band_boundaries(self, mb, expected):
        assert size_band(mb) == expected


class TestStripMarkdown:
    """The model emits headings under an explicit instruction not to."""

    def test_headings_are_unwrapped_not_deleted(self):
        text = "### Where the Mess is Coming From\nDownloads is the culprit."
        assert strip_markdown(text) == (
            "Where the Mess is Coming From\nDownloads is the culprit."
        )

    def test_bullet_markers_are_removed(self):
        assert strip_markdown("- one\n* two\n+ three") == "one\ntwo\nthree"

    def test_ordered_list_markers_are_removed(self):
        """Live 2026-08-06: the model produced "1. **Node_modules...**"."""
        assert strip_markdown("1. Node_modules\n2) Duplicates") == (
            "Node_modules\nDuplicates"
        )

    def test_bold_emphasis_is_removed(self):
        assert strip_markdown("**Node_modules directories**: big") == (
            "Node_modules directories: big"
        )

    def test_plain_prose_is_untouched(self):
        text = "The mess is in Downloads.\nClear it first."
        assert strip_markdown(text) == text

    def test_hyphenated_prose_is_not_treated_as_a_bullet(self):
        assert strip_markdown("well-known issue") == "well-known issue"

    def test_a_sentence_starting_with_a_year_is_not_a_list_item(self):
        """Only "N." / "N)" followed by a space is a marker."""
        assert strip_markdown("2026 was a big year.") == "2026 was a big year."


class TestFallback:
    def test_fallback_is_deterministic_and_carries_the_facts(self):
        text = build_fallback_narrative(DATA)
        assert "without LLM narration" in text
        assert "78.0% used" in text
        assert "Clear first: Delete 50 rebuildable dependency directories" in text
        assert text == build_fallback_narrative(DATA)

class TestGenerateReview:
    def _session(self, data):
        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_llm_narrative_is_prefixed_with_computed_facts(self):
        session = self._session(DATA)
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(session, llm_client=_llm("Mess is in ~/Downloads."))

        assert review.llm_used is True
        assert review.narrative.startswith("Disk /: 78.0% used")
        assert review.narrative.endswith("Mess is in ~/Downloads.")
        assert review.stats == DATA

    @pytest.mark.asyncio
    async def test_read_transaction_is_committed_before_inference(self):
        """Session 23: inference outlives idle_in_transaction_session_timeout."""
        session = self._session(DATA)
        order = []
        session.commit = AsyncMock(side_effect=lambda: order.append("commit"))
        client = MagicMock()

        async def _generate(*a, **k):
            order.append("generate")
            return "prose"

        client.generate = _generate

        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            await generate_review(session, llm_client=client)

        assert order == ["commit", "generate"]

    @pytest.mark.asyncio
    async def test_llm_down_falls_back_to_digest(self):
        session = self._session(DATA)
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(session, llm_client=_llm(None))

        assert review.llm_used is False
        assert review.model_used is None
        assert "without LLM narration" in review.narrative

    @pytest.mark.asyncio
    async def test_no_audits_returns_none_and_stores_nothing(self):
        session = self._session({})
        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value={})),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            review = await generate_review(session, llm_client=_llm("unused"))

        assert review is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_injected_client_lifecycle_untouched(self):
        """A caller-supplied client is not started or shut down here."""
        session = self._session(DATA)
        client = _llm("prose")
        client.startup = AsyncMock()
        client.shutdown = AsyncMock()

        with (
            patch(f"{MOD}.gather_review_data", new=AsyncMock(return_value=DATA)),
            patch(f"{MOD}.get_config", return_value=_config()),
        ):
            await generate_review(session, llm_client=client)

        client.startup.assert_not_awaited()
        client.shutdown.assert_not_awaited()


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
        review = DiskReview(
            period_days=7, narrative="Disk /: 78.0% used.\nMore.", llm_used=True
        )
        review.id = "22222222-2222-2222-2222-222222222222"

        with (
            patch(f"{MOD}.get_scheduler_session", ctx),
            patch(f"{MOD}.generate_review", new=AsyncMock(return_value=review)),
        ):
            await run_weekly_review()

        (alert,) = session.add.call_args[0]
        assert isinstance(alert, Alert)
        assert alert.agent == "file_organiser"
        assert alert.severity == "info"
        assert alert.message == "Disk /: 78.0% used."
        assert alert.details["endpoint"] == "/api/files/review"

    @pytest.mark.asyncio
    async def test_no_review_no_alert(self):
        session, ctx = self._scheduler_session()

        with (
            patch(f"{MOD}.get_scheduler_session", ctx),
            patch(f"{MOD}.generate_review", new=AsyncMock(return_value=None)),
        ):
            await run_weekly_review()

        session.add.assert_not_called()
