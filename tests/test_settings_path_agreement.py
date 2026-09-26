"""``SNAG-CFG-007`` — the two wiring readers compared on *which* file.

Since ADR-0008 this repository reads ``~/.claude/settings.json`` from a
constant and estate-manager's check 11 reads a *configured* path.  If
those ever differ, both report cleanly about their own file and neither
says which it used.  The estate began publishing its answer on its audit
summary (their message ``999f4432``), and
:func:`sysadmin.estate.hook_wiring.compare_settings_paths` compares it
with this side's read.

Three halves:

* **The comparison** — a derived surface, read only when both halves
  were and the estate actually published a path.  An absent path is
  *unread*, never agreement (rule 2), and every step that can be absent
  is named.
* **The judge** — one fixed-title ``warning`` row on a disagreement, and
  nothing on anything else.
* **The live half** — the estate still publishes the field, and today
  both readers name one file.  A graceful degradation with no separate
  alarm degrades unnoticed, so the one place the field's *absence* can be
  loud is here.
"""

from __future__ import annotations

import httpx
import pytest

from sysadmin.estate import hook_wiring
from sysadmin.estate.client import SurfaceResult
from sysadmin.estate.judgements import (
    DEFAULT_SEVERITY,
    SETTINGS_PATH_TITLE,
    SURFACE_TITLE_PATTERNS,
    judge_settings_path,
)

ESTATE_URL = "http://localhost:8400"

LINK = "/home/u/.claude/settings.json"
TARGET = "/home/u/projects/dotfiles/claude/settings.json"


def _audit(settings_file, *, finished_at="2026-09-26T05:03:01+00:00"):
    """An ``audit_invariants`` result whose wiring summary carries ``inputs``."""
    return SurfaceResult(
        surface="audit_invariants",
        payload={
            "audits_total": 1,
            "last_audit": {
                "finished_at": finished_at,
                "checks": {
                    "wiring": {
                        "status": "ok",
                        "error": None,
                        "findings": 0,
                        "inputs": {"settings_file": settings_file},
                    }
                },
            },
        },
    )


def _local(**where):
    """A ``hook_wiring`` result for a file that parsed."""
    return SurfaceResult(
        surface=hook_wiring.SURFACE,
        payload={**where, "kind": None, "fault": None},
    )


# ---------------------------------------------------------------------------
# The comparison
# ---------------------------------------------------------------------------


class TestTheComparison:
    def test_one_symlink_read_by_both_is_one_file(self):
        result = hook_wiring.compare_settings_paths(
            _audit({"path": LINK, "resolves_to": TARGET}),
            _local(path=LINK, resolves_to=TARGET),
        )

        assert result.read
        assert result.surface == hook_wiring.AGREEMENT_SURFACE
        assert result.payload["same_file"] is True

    def test_a_path_configured_at_the_target_is_still_one_file(self):
        """The estate may be configured with the symlink's *target*, in
        which case it publishes no ``resolves_to`` — the pair's rule says
        ``path`` then **is** the file. Comparing declared paths would
        report two files here; comparing targets reports one."""
        result = hook_wiring.compare_settings_paths(
            _audit({"path": TARGET}),
            _local(path=LINK, resolves_to=TARGET),
        )

        assert result.payload["same_file"] is True

    def test_two_files_are_two_files(self):
        result = hook_wiring.compare_settings_paths(
            _audit({"path": "/elsewhere/settings.json"}),
            _local(path=LINK, resolves_to=TARGET),
        )

        assert result.payload["same_file"] is False
        assert result.payload["ours_target"] == TARGET
        assert result.payload["theirs_target"] == "/elsewhere/settings.json"

    def test_the_payload_carries_the_where_pairs_and_the_audits_moment(self):
        """Only ``path``/``resolves_to`` from each side — the local
        read's ``kind``/``fault`` are another family's facts — and when
        the estate read its file, since its answer is as old as its
        last audit."""
        result = hook_wiring.compare_settings_paths(
            _audit({"path": LINK, "resolves_to": TARGET}),
            _local(path=LINK, resolves_to=TARGET),
        )

        assert result.payload["ours"] == {"path": LINK, "resolves_to": TARGET}
        assert result.payload["theirs"] == {"path": LINK, "resolves_to": TARGET}
        assert result.payload["audit_finished_at"] == "2026-09-26T05:03:01+00:00"


class TestNotComparedIsNotAgreement:
    """Rule 2. Every way of not being able to compare is *unread*, so the
    agent neither raises nor sweeps — and the error names which half."""

    def test_an_unread_audit(self):
        result = hook_wiring.compare_settings_paths(
            SurfaceResult(surface="audit_invariants", error="ConnectError: refused"),
            _local(path=LINK),
        )

        assert not result.read
        assert "audit_invariants" in result.error

    def test_a_missing_audit(self):
        result = hook_wiring.compare_settings_paths(None, _local(path=LINK))

        assert not result.read

    def test_an_unread_local_file(self):
        result = hook_wiring.compare_settings_paths(
            _audit({"path": LINK}),
            SurfaceResult(surface=hook_wiring.SURFACE, error="PermissionError: denied"),
        )

        assert not result.read
        assert hook_wiring.SURFACE in result.error

    @pytest.mark.parametrize(
        ("payload", "named"),
        [
            ({"audits_total": 0, "last_audit": None}, "last_audit"),
            ({"last_audit": {"checks": None}}, "last_audit.checks"),
            ({"last_audit": {"checks": {}}}, "checks.wiring"),
            ({"last_audit": {"checks": {"wiring": {"status": "ok"}}}}, "wiring.inputs"),
            ({"last_audit": {"checks": {"wiring": {"inputs": {}}}}}, "inputs.settings_file"),
            (
                {"last_audit": {"checks": {"wiring": {"inputs": {"settings_file": {}}}}}},
                "inputs.settings_file.path",
            ),
            (
                {"last_audit": {"checks": {"wiring": {"inputs": {
                    "settings_file": {"path": "", "resolves_to": None}
                }}}}},
                "inputs.settings_file.path",
            ),
        ],
    )
    def test_an_absent_path_is_unread_and_names_the_step(self, payload, named):
        """The rollback case: a producer that stops publishing the field
        must not read as "same file" and close a standing row."""
        result = hook_wiring.compare_settings_paths(
            SurfaceResult(surface="audit_invariants", payload=payload),
            _local(path=LINK),
        )

        assert not result.read
        assert result.error.endswith(f"publishes no {named}")


# ---------------------------------------------------------------------------
# The judge
# ---------------------------------------------------------------------------


class TestTheJudge:
    def test_a_disagreement_is_one_warning_row(self):
        payload = {
            "ours_target": TARGET,
            "theirs_target": "/elsewhere/settings.json",
            "same_file": False,
        }

        (row,) = judge_settings_path(payload)

        assert row.surface == hook_wiring.AGREEMENT_SURFACE
        assert row.title == SETTINGS_PATH_TITLE
        assert row.severity == DEFAULT_SEVERITY
        assert TARGET in row.message
        assert "/elsewhere/settings.json" in row.message
        assert row.details == payload

    def test_agreement_is_nothing(self):
        assert judge_settings_path({"same_file": True}) == []

    @pytest.mark.parametrize("value", [None, 0, "false", [], {}])
    def test_a_payload_it_cannot_read_is_nothing(self, value):
        """Rule 3: fails open — ``same_file`` must be exactly ``False``."""
        assert judge_settings_path({"same_file": value}) == []
        assert judge_settings_path({}) == []

    def test_the_title_is_the_derived_surfaces_alone(self):
        from tests.test_estate_judgements import _like

        for surface, patterns in SURFACE_TITLE_PATTERNS.items():
            matched = any(_like(p, SETTINGS_PATH_TITLE) for p in patterns)
            assert matched is (surface == hook_wiring.AGREEMENT_SURFACE), surface


# ---------------------------------------------------------------------------
# The live half
# ---------------------------------------------------------------------------


def _estate_available() -> bool:
    try:
        return httpx.get(f"{ESTATE_URL}/api/health", timeout=2.0).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _estate_available(), reason=f"estate-manager ({ESTATE_URL}) unreachable")
class TestLive:
    @pytest.mark.premise
    def test_the_estate_still_publishes_which_file_it_read(self):
        """The premise the second test rests on, and the alarm for the
        rollback case.

        The skip gate only asks whether ``/api/health`` answered, so an
        estate with no audit yet passes it. This separates *the estate
        answered* from *it said which file its wiring check read*. If it
        goes red, the comparison has gone dark — unread, named in
        ``unread_surfaces`` every hour, and otherwise silent."""
        payload = httpx.get(f"{ESTATE_URL}/api/audit/invariants", timeout=5.0).json()
        result = hook_wiring.compare_settings_paths(
            SurfaceResult(surface="audit_invariants", payload=payload),
            _local(path=LINK),
        )

        assert result.read, result.error

    def test_both_readers_name_one_file_today(self):
        local = hook_wiring.read_settings()
        if not local.read:
            pytest.skip(f"this box's settings file is unread: {local.error}")
        payload = httpx.get(f"{ESTATE_URL}/api/audit/invariants", timeout=5.0).json()

        result = hook_wiring.compare_settings_paths(
            SurfaceResult(surface="audit_invariants", payload=payload), local
        )

        assert result.read, result.error
        assert result.payload["same_file"] is True, result.payload
