"""A weekly review announces itself through the briefing, never an alert row.

``SNAG-AGENT-010``.  Three modules wrote an identical ``info`` alert row
saying a review was ready — :mod:`sysadmin.files.review`,
:mod:`sysadmin.monitor.log_review` and
:mod:`sysadmin.monitor.health_review`.  The entry named one of them,
because the symptom on the box was one row: only the disk review's
scheduler path had ever fired.

Nothing could close such a row.  It has no dedup branch, its title
matches no :data:`~sysadmin.monitor.agent.RESOLVABLE_TITLE_PATTERNS`
entry, and :func:`~sysadmin.core.retention.purge_statement` deletes an
``alerts`` row only ``WHERE resolved = TRUE`` — so "immortal" was
literal.  One stood open 271 hours saying the disk crossed 90 % on a
date that had passed with the disk at 80 %.

The guards here pin the ruling from both sides:

* **behaviour** — the scheduler path adds nothing to the session, and
* **provenance** — no ``Alert(...)`` is constructed in any of the three
  ``run_weekly_review`` functions.

Both are needed and neither substitutes for the other.  A behavioural
test alone passes against a module that builds the row and forgets to
add it; a source test alone passes against one that adds a row built
somewhere else.  The provenance half is an AST walk rather than a
``grep``, because :mod:`sysadmin.monitor.health_review` legitimately
imports ``Alert`` for the queries behind its alert-delta figure — a
name in an import list is not a caller, which is the distinction
``tests/test_autogenerate_config.py`` had to draw for the same reason.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

#: The three weekly reviews, by the module path their scheduler entry
#: point lives in.  Adding a fourth review adds a line here; a review
#: absent from this tuple is a review nothing checks.
REVIEW_MODULES = (
    "sysadmin.files.review",
    "sysadmin.monitor.log_review",
    "sysadmin.monitor.health_review",
)

ENTRY_POINT = "run_weekly_review"


def _entry_point_ast(module_path: str) -> ast.AsyncFunctionDef:
    """The parsed :data:`ENTRY_POINT` of one review module."""
    module = __import__(module_path, fromlist=["_"])
    tree = ast.parse(Path(inspect.getfile(module)).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == ENTRY_POINT:
            return node
    raise AssertionError(f"{module_path} has no async {ENTRY_POINT}")


class TestNoReviewAnnouncesItselfWithAnAlert:
    @pytest.mark.parametrize("module_path", REVIEW_MODULES)
    def test_the_entry_point_constructs_no_alert(self, module_path: str):
        """Provenance, not value: an ``Alert(...)`` call in the function.

        ``health_review`` imports ``Alert`` and must go on importing it —
        its alert-delta figure is four queries over that table — so the
        thing being refused is the *construction*, which only the source
        can answer.
        """
        node = _entry_point_ast(module_path)
        built = [
            call
            for call in ast.walk(node)
            if isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "Alert"
        ]
        assert not built, f"{module_path}.{ENTRY_POINT} builds an Alert"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("module_path", REVIEW_MODULES)
    async def test_the_scheduler_path_writes_nothing(self, module_path: str):
        """Behaviour: a successful generation adds no row to the session.

        ``generate_review`` is patched out, so the only ``session.add``
        this can observe is the announcement — the review's own row is
        added inside the function being stubbed.
        """
        module = __import__(module_path, fromlist=["_"])
        session = MagicMock()
        session.add = MagicMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def fake_scheduler_session():
            yield session

        review = MagicMock()
        review.narrative = "First line.\nSecond."

        with (
            patch.object(module, "get_scheduler_session", fake_scheduler_session),
            patch.object(
                module, "generate_review", new=AsyncMock(return_value=review)
            ),
        ):
            await module.run_weekly_review()

        session.add.assert_not_called()


class TestWhyItIsADeletionAndNotALifecycle:
    def test_an_unresolved_alert_row_is_unreachable_by_retention(self):
        """The half of the entry that makes "immortal" literal.

        A lifecycle would have had to *resolve* the previous notice to
        make it purgeable.  That fix would not have closed the observed
        row: it was written 2026-08-17 05:45 and the next generation was
        due 08-24 05:45, when the daemon was down — so a lifecycle
        anchored to the next run is bounded by the thing that already
        failed.
        """
        from sysadmin.core.retention import purge_statement

        statement = purge_statement("alerts", "created_at")
        assert "resolved = TRUE" in statement

    def test_the_notice_severity_is_below_every_speaker_on_this_box(self):
        """It could not have been heard, which is why nothing is lost.

        Both speakers gate at ``warning`` here — the tray owns the policy
        and ``monitor/desktop.py`` is its understudy — and the row was
        ``info``.  Read from the shipped ``config.yaml`` rather than
        retyped, because the claim is about this box.
        """
        import yaml

        from sysadmin.core.escalation import SEVERITY_ORDER

        live = yaml.safe_load(Path("config.yaml").read_text())
        # `tray.notify_min_severity` is the *top-level* tray block — the
        # tray application's own config — while `notifications.tray`
        # holds the policy knobs (dedup, cooldown, reminders).  Two
        # blocks called "tray" is a trap worth naming where it is read.
        tray = live["tray"]["notify_min_severity"]
        desktop = live["notifications"]["desktop"]["min_severity"]

        assert SEVERITY_ORDER["info"] < SEVERITY_ORDER[tray]
        assert SEVERITY_ORDER["info"] < SEVERITY_ORDER[desktop]

    def test_the_briefing_reads_every_review_table_directly(self):
        """What still announces a review, and the reason no tray work was
        needed — the entry proposed "let the tray read
        ``/api/files/review``" and the consumer that mattered was the
        briefing, which had been reading all three all along."""
        source = Path("sysadmin/briefing/data.py").read_text()
        for model in ("DiskReview", "LogReview", "HealthReview"):
            assert f"_gather_review(session, now, {model})" in source, model
