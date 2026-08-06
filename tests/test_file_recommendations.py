"""Tests for the pure file-organiser recommendations (Session 24 Tier 2).

No DB, no FastAPI, no filesystem — every input is a plain findings dict
of the shape ``FilesystemAudit.findings`` stores.  Per the Session 18
rule the real home directory is never touched; nothing here even walks a
``tmp_path``, because the module reads stored findings rather than disk.

The arithmetic that matters is the *currency split*: only duplicates,
old downloads, stale caches and rebuildable dependency directories free
space.  Everything else must price at 0.0 MB, or the endpoint would
promise reclaims that acting on it cannot deliver.
"""

from __future__ import annotations

import pytest

from sysadmin.config import FileOrganiserConfig
from sysadmin.services.file_recommendations import (
    CACHE_DIR_TYPES,
    RISK_HORIZON_DAYS,
    recommendations_for_audit,
    total_reclaimable_mb,
)
from sysadmin.services.forecast import ThresholdProjection


@pytest.fixture
def agent_config() -> FileOrganiserConfig:
    return FileOrganiserConfig()


def _by_kind(recs: list) -> dict:
    return {r.kind: r for r in recs}


def _duplicates(*sizes_and_counts: tuple[float, int]) -> list[dict]:
    """Duplicate groups priced at ``(size_mb, copies)``."""
    return [
        {
            "hash": f"h{i}",
            "files": [f"/home/u/f{i}-{n}" for n in range(count)],
            "count": count,
            "size_mb": size,
            "reclaimable_mb": round(size * (count - 1), 1),
        }
        for i, (size, count) in enumerate(sizes_and_counts)
    ]


class TestSpaceCurrency:
    def test_duplicates_price_at_all_but_one_copy(self, agent_config):
        findings = {"duplicates": _duplicates((100.0, 3), (50.0, 2))}
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["duplicates"]

        # 100 MB × 2 extra copies + 50 MB × 1 extra copy
        assert rec.reclaimable_mb == pytest.approx(250.0)
        # Counted in groups, matching the audit's ``duplicate_groups_count``
        assert rec.item_count == 2
        assert "3 redundant copies" in rec.detail
        assert "clean/duplicates" in rec.action

    def test_old_downloads_sum_their_sizes(self, agent_config):
        findings = {
            "old_downloads": [
                {"path": "/home/u/Downloads/a.iso", "days_old": 90, "size_mb": 700.0},
                {"path": "/home/u/Downloads/b.zip", "days_old": 45, "size_mb": 12.5},
            ]
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["downloads"]

        assert rec.reclaimable_mb == pytest.approx(712.5)
        assert rec.item_count == 2
        assert str(agent_config.downloads_stale_days) in rec.detail

    def test_stale_caches_and_rebuildable_dirs_are_separate_items(self, agent_config):
        """Only caches have an executor; node_modules must not claim one."""
        findings = {
            "stale_project_dirs": [
                {"path": "/p/a/__pycache__", "size_mb": 20.0, "type": "__pycache__"},
                {"path": "/p/b/node_modules", "size_mb": 400.0, "type": "node_modules"},
                {"path": "/p/c/.venv", "size_mb": 300.0, "type": ".venv"},
            ]
        }
        recs = _by_kind(recommendations_for_audit(findings, agent_config))

        assert recs["stale_caches"].reclaimable_mb == pytest.approx(20.0)
        assert recs["stale_caches"].action == "POST /api/files/clean/stale-caches"

        assert recs["rebuildable_dirs"].reclaimable_mb == pytest.approx(700.0)
        assert recs["rebuildable_dirs"].item_count == 2
        assert "/api/files/" not in recs["rebuildable_dirs"].action
        assert "node_modules" in recs["rebuildable_dirs"].detail

    def test_cache_types_are_the_ones_the_agent_counts(self):
        """The shared constant is what stops advice and quick-wins drifting."""
        assert CACHE_DIR_TYPES == ("__pycache__", ".pytest_cache", ".tox")

    def test_total_sums_only_reclaimable_items(self, agent_config):
        findings = {
            "duplicates": _duplicates((100.0, 2)),
            "large_files": [{"path": "/home/u/big.mkv", "size_mb": 4000.0}],
            "misplaced_files": {"images": ["/home/u/a.png"] * 30},
            "empty_dirs": ["/home/u/x", "/home/u/y"],
        }
        recs = recommendations_for_audit(findings, agent_config)

        # 4 GB of large files and 30 misplaced images contribute nothing
        assert total_reclaimable_mb(recs) == pytest.approx(100.0)


class TestTidinessItemsFreeNothing:
    def test_large_files_are_review_only(self, agent_config):
        findings = {
            "large_files": [
                {"path": "/home/u/big.mkv", "size_mb": 4000.0},
                {"path": "/home/u/med.iso", "size_mb": 900.0},
            ]
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["large_files"]

        assert rec.reclaimable_mb == 0.0
        assert rec.item_count == 2
        assert "big.mkv" in rec.detail  # names the largest
        assert "only you know which are junk" in rec.detail

    def test_misplaced_files_break_down_by_category(self, agent_config):
        findings = {
            "misplaced_files": {
                "images": ["/home/u/a.png", "/home/u/b.png"],
                "videos": ["/home/u/c.mp4"],
                "audio": [],
            }
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["misplaced"]

        assert rec.reclaimable_mb == 0.0
        assert rec.item_count == 3
        assert rec.detail.startswith("2 images, 1 videos")  # largest first
        assert "audio" not in rec.detail  # empty categories are dropped
        assert "organise" in rec.action

    def test_empty_dirs_and_similar_folders_are_counted_not_priced(
        self, agent_config
    ):
        findings = {
            "empty_dirs": ["/home/u/x", "/home/u/y", "/home/u/z"],
            "similar_folders": [["/home/u/Docs", "/home/u/docs"]],
        }
        recs = _by_kind(recommendations_for_audit(findings, agent_config))

        assert recs["empty_dirs"].reclaimable_mb == 0.0
        assert recs["empty_dirs"].item_count == 3
        assert recs["similar_folders"].reclaimable_mb == 0.0
        assert recs["similar_folders"].item_count == 1


class TestDiskRiskRanking:
    def _busy_findings(self) -> dict:
        return {"duplicates": _duplicates((5000.0, 2))}  # ~5 GB, the biggest win

    def test_imminent_crossing_outranks_the_biggest_byte_total(self, agent_config):
        projection = ThresholdProjection(
            percent=90.0, state="projected", days_from_now=12.0, date="2026-08-18"
        )
        recs = recommendations_for_audit(
            self._busy_findings(), agent_config, projection
        )

        assert recs[0].kind == "risk"
        assert recs[0].severity == "risk"
        assert recs[0].reclaimable_mb == 0.0
        assert "2026-08-18" in recs[0].detail
        assert recs[1].kind == "duplicates"  # 5 GB still ranks second

    def test_crossing_beyond_the_horizon_is_a_trend_not_a_risk(self, agent_config):
        projection = ThresholdProjection(
            percent=90.0,
            state="projected",
            days_from_now=RISK_HORIZON_DAYS + 1,
            date="2027-01-01",
        )
        recs = recommendations_for_audit(
            self._busy_findings(), agent_config, projection
        )

        assert all(r.severity != "risk" for r in recs)

    def test_already_exceeded_is_always_a_risk(self, agent_config):
        projection = ThresholdProjection(percent=90.0, state="exceeded")
        recs = recommendations_for_audit(
            self._busy_findings(), agent_config, projection
        )

        assert recs[0].severity == "risk"
        assert "no longer optional" in recs[0].detail

    def test_a_disk_that_is_not_filling_raises_nothing(self, agent_config):
        projection = ThresholdProjection(percent=90.0, state="not_growing")
        recs = recommendations_for_audit(
            self._busy_findings(), agent_config, projection
        )

        assert all(r.severity != "risk" for r in recs)

    def test_no_projection_degrades_to_megabytes_descending(self, agent_config):
        findings = {
            "duplicates": _duplicates((100.0, 2)),
            "old_downloads": [{"path": "/d/a", "days_old": 60, "size_mb": 900.0}],
            "empty_dirs": ["/home/u/x"],
        }
        recs = recommendations_for_audit(findings, agent_config, None)

        assert [r.kind for r in recs] == ["downloads", "duplicates", "empty_dirs"]


class TestTruncatedFindings:
    """Findings lists are capped at 50–100 entries before storage.

    Found live 2026-08-06 against the real audit row: the stored
    findings listed 200 misplaced files where the audit's own column
    said 11,877.  Ranking and headline counts must come from the
    columns; sizes summed from the truncated list become a lower bound
    and have to be labelled as one.
    """

    def test_true_counts_override_the_truncated_list(self, agent_config):
        findings = {"misplaced_files": {"images": ["/home/u/a.png"] * 50}}
        rec = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"misplaced_files": 11877}
            )
        )["misplaced"]

        assert rec.item_count == 11877
        assert "11877 misplaced files" in rec.title
        assert "first 50 of 11877 files" in rec.detail

    def test_walk_order_lists_are_not_called_the_largest(self, agent_config):
        """Misplaced files are stored in walk order, not size order."""
        findings = {
            "misplaced_files": {"images": ["/home/u/a.png"] * 50},
            "old_downloads": [
                {"path": f"/d/{i}", "days_old": 60, "size_mb": 10.0}
                for i in range(100)
            ],
        }
        recs = _by_kind(
            recommendations_for_audit(
                findings,
                agent_config,
                None,
                {"misplaced_files": 11877, "old_downloads": 11400},
            )
        )

        assert "first 50" in recs["misplaced"].detail
        assert "largest" not in recs["misplaced"].detail
        # Downloads *are* sorted by size before truncation, so they may
        assert "largest 100" in recs["downloads"].detail

    def test_unrecorded_sizes_are_not_reported_as_zero(self, agent_config):
        """"holding at least 0 MB" reads as "there is nothing here"."""
        findings = {
            "old_downloads": [{"path": f"/d/{i}", "days_old": 60} for i in range(100)]
        }
        rec = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"old_downloads": 11400}
            )
        )["downloads"]

        assert "an unrecorded amount" in rec.detail
        assert "0 MB" not in rec.detail
        assert "Sizes were not recorded" in rec.detail
        # A scan that recorded no sizes cannot have sorted by them
        assert "first 100 of 11400" in rec.detail
        assert "largest" not in rec.detail

    def test_sizes_from_a_truncated_list_are_a_lower_bound(self, agent_config):
        findings = {
            "old_downloads": [
                {"path": f"/d/{i}", "days_old": 60, "size_mb": 10.0}
                for i in range(100)
            ]
        }
        rec = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"old_downloads": 11400}
            )
        )["downloads"]

        assert rec.item_count == 11400
        assert rec.reclaimable_mb == pytest.approx(1000.0)
        assert "at least" in rec.detail

    def test_untruncated_findings_claim_no_lower_bound(self, agent_config):
        findings = {
            "old_downloads": [{"path": "/d/a", "days_old": 60, "size_mb": 10.0}]
        }
        rec = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"old_downloads": 1}
            )
        )["downloads"]

        assert "at least" not in rec.detail
        assert "truncated" not in rec.detail

    def test_a_stored_count_below_the_listed_length_is_ignored(self, agent_config):
        """The list is visible; a smaller column must not shrink it."""
        findings = {"empty_dirs": ["/a", "/b", "/c"]}
        rec = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"empty_dirs": 1}
            )
        )["empty_dirs"]

        assert rec.item_count == 3

    def test_stale_dir_split_shares_one_combined_count(self, agent_config):
        """Caches and rebuildables come from one column, so both note it."""
        findings = {
            "stale_project_dirs": [
                {"path": "/p/a/__pycache__", "size_mb": 20.0, "type": "__pycache__"},
                {"path": "/p/b/node_modules", "size_mb": 400.0, "type": "node_modules"},
            ]
        }
        recs = _by_kind(
            recommendations_for_audit(
                findings, agent_config, None, {"stale_project_dirs": 112}
            )
        )

        assert "largest 2 of 112 stale directories" in recs["stale_caches"].detail
        assert "largest 2 of 112 stale directories" in recs["rebuildable_dirs"].detail
        # Each half still counts only what it can see
        assert recs["stale_caches"].item_count == 1
        assert recs["rebuildable_dirs"].item_count == 1

    def test_ranking_uses_true_counts_within_the_zero_megabyte_tier(
        self, agent_config
    ):
        findings = {
            "empty_dirs": ["/a"] * 100,
            "similar_folders": [["/x", "/y"]] * 50,
        }
        recs = recommendations_for_audit(
            findings,
            agent_config,
            None,
            {"empty_dirs": 200, "similar_folders": 9000},
        )

        # 9000 similar folder groups outranks 200 empty dirs, even
        # though the stored lists say 50 vs 100
        assert [r.kind for r in recs] == ["similar_folders", "empty_dirs"]

    def test_missing_true_counts_fall_back_to_the_list(self, agent_config):
        findings = {"empty_dirs": ["/a", "/b"]}
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["empty_dirs"]

        assert rec.item_count == 2
        assert "truncated" not in rec.detail


class TestTolerantParsing:
    def test_empty_findings_produce_no_advice(self, agent_config):
        assert recommendations_for_audit({}, agent_config) == []

    def test_audits_predating_size_recording_say_so(self, agent_config):
        """Old rows have no ``reclaimable_mb`` — say "rescan", not "0 MB"."""
        findings = {
            "duplicates": [
                {"hash": "h", "files": ["/a", "/b"], "count": 2},
            ]
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["duplicates"]

        assert rec.reclaimable_mb == 0.0
        assert "Sizes were not recorded" in rec.detail

    def test_a_genuine_zero_does_not_claim_missing_sizes(self, agent_config):
        findings = {
            "duplicates": [
                {"hash": "h", "files": ["/a", "/b"], "count": 2, "reclaimable_mb": 0.0},
            ]
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["duplicates"]

        assert "Sizes were not recorded" not in rec.detail

    def test_malformed_findings_degrade_to_no_recommendation(self, agent_config):
        """JSONB is hand-editable; a bad row must not 500 an API request."""
        findings = {
            "duplicates": "not a list",
            "old_downloads": [None, "junk", 42],
            "misplaced_files": ["wrong shape"],
            "stale_project_dirs": {"also": "wrong"},
        }
        assert recommendations_for_audit(findings, agent_config) == []

    def test_non_numeric_sizes_are_treated_as_zero(self, agent_config):
        findings = {
            "old_downloads": [
                {"path": "/d/a", "days_old": 60, "size_mb": "big"},
                {"path": "/d/b", "days_old": 60, "size_mb": 10.0},
            ]
        }
        rec = _by_kind(recommendations_for_audit(findings, agent_config))["downloads"]

        assert rec.reclaimable_mb == pytest.approx(10.0)
        assert rec.item_count == 2
