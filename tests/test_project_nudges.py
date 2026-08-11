"""Idle nudges — the ladder, the lifecycle, and what must never nudge.

Session 31.  Three things are worth pinning here and they fail in
different places:

1. **The ladder**, in :mod:`sysadmin.projects.nudges` — pure arithmetic
   over days, testable without a database or a clock.
2. **The lifecycle**, in ``ProjectOrganiserAgent`` — raise once, escalate
   by replacement, resolve set-based.  This is where a nudge turns into
   a nag if it is wrong, and the failure is invisible in the code: it
   looks identical to the health-alert path that *is* meant to re-raise.
3. **Eligibility**, which is not implemented here at all.  The tests
   below assert that it is still borrowed from
   ``GET /api/projects/next`` rather than re-stated, because two copies
   of "what counts as a commitment" would drift silently — the endpoint
   would stop offering a project while the nudge went on reminding you
   about it, and nothing would report the disagreement.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import IdleNudgeConfig, ProjectOrganiserConfig
from sysadmin.projects import nudges
from sysadmin.projects.agent import ProjectOrganiserAgent
from sysadmin.projects.next_action import Candidate, Streak, eligible_candidates

NOW = datetime(2026, 8, 11, 9, 0, tzinfo=UTC)


def candidate(name: str = "demo", **kwargs) -> Candidate:
    return Candidate(
        name=name,
        path=f"/home/gaddi/projects/{name}",
        next_action=kwargs.get("next_action", "Finish the thing"),
        next_action_source=kwargs.get("next_action_source", "handoff"),
        health_score=kwargs.get("health_score", 90),
        days_since_commit=kwargs.get("days_since_commit", 3),
        open_tasks=kwargs.get("open_tasks"),
        open_snags=kwargs.get("open_snags", 0),
        scanned_at=NOW,
    )


def streak(days: int, *, scans: int = 5, edge: bool = False) -> Streak:
    return Streak(
        days=days,
        since=NOW - timedelta(days=days),
        scans=scans,
        at_window_edge=edge,
    )


def snapshot(
    name: str = "demo",
    *,
    status: str = "active",
    action: str | None = "Finish the thing",
    source: str | None = "handoff",
    **findings,
) -> SimpleNamespace:
    roadmap = {"next_action": action, "next_action_source": source, **findings}
    return SimpleNamespace(
        project_name=name,
        project_path=f"/home/gaddi/projects/{name}",
        health_score=90,
        last_commit_at=NOW - timedelta(days=2),
        scanned_at=NOW,
        findings={"status": status, "roadmap": roadmap},
    )


class TestTheLadder:
    """Quiet at the threshold, loud after the gap."""

    def test_below_the_threshold_is_not_a_nudge(self):
        assert nudges.severity_for(6, threshold=7, escalation_gap=7) is None

    def test_the_threshold_itself_nudges_quietly(self):
        """A commitment breaks *on* day 7, not the day after."""
        assert nudges.severity_for(7, threshold=7, escalation_gap=7) == "info"

    def test_it_stays_quiet_until_the_gap_has_passed(self):
        assert nudges.severity_for(13, threshold=7, escalation_gap=7) == "info"

    def test_the_gap_escalates_it(self):
        assert nudges.severity_for(14, threshold=7, escalation_gap=7) == "warning"

    def test_a_zero_gap_is_loud_from_the_first_rung(self):
        """A legitimate configuration, not a degenerate one."""
        assert nudges.severity_for(7, threshold=7, escalation_gap=0) == "warning"

    def test_a_nudge_never_reaches_critical(self):
        """Criticals break through DND; a roadmap item must not."""
        severities = {
            nudges.severity_for(days, threshold=7, escalation_gap=7)
            for days in range(0, 400)
        }
        assert severities == {None, "info", "warning"}


class TestPerProjectThreshold:
    """The manifest knob moves when the clock starts, not the gap."""

    def _evaluate(self, days: int, thresholds: dict[str, int]):
        return nudges.evaluate(
            [candidate("slow")],
            {"slow": streak(days)},
            thresholds,
            default_days=7,
            escalation_gap=7,
        )

    def test_an_override_relaxes_the_first_rung(self):
        assert self._evaluate(14, {"slow": 21}) == []

    def test_the_override_still_fires_eventually(self):
        raised = self._evaluate(21, {"slow": 21})

        assert [n.severity for n in raised] == ["info"]
        assert raised[0].threshold == 21

    def test_escalation_is_the_gap_after_the_override_not_a_multiple(self):
        """21-day patience escalates at 28, not at 42.

        A multiplier would make a project that asked for a longer first
        rung doubly hard to hear from, which is the opposite of what
        relaxing the first threshold asks for.
        """
        assert [n.severity for n in self._evaluate(27, {"slow": 21})] == ["info"]
        assert [n.severity for n in self._evaluate(28, {"slow": 21})] == ["warning"]

    def test_projects_without_an_override_take_the_default(self):
        assert [n.severity for n in self._evaluate(7, {})] == ["info"]


class TestWhatIsNeverNudged:
    """Eligibility is borrowed from /api/projects/next, not re-stated."""

    def test_a_dormant_project_is_not_a_broken_commitment(self):
        """Declaring it dormant *was* the decision."""
        found, skipped = eligible_candidates([snapshot(status="dormant")], now=NOW)

        assert found == []
        assert skipped == {"inactive": 1}

    def test_a_commit_subject_is_not_an_instruction(self):
        """The board's git fallback is a record of the past."""
        found, skipped = eligible_candidates(
            [snapshot(source="git")], now=NOW
        )

        assert found == []
        assert skipped == {"source_git": 1}

    def test_nothing_queued_is_an_honest_handoff(self):
        found, skipped = eligible_candidates(
            [snapshot(action="No unchecked task found — set one before the next session.")],
            now=NOW,
        )

        assert found == []
        assert skipped == {"says_no_action": 1}

    def test_an_unknown_streak_never_nudges(self):
        """A project's first scan has no history to be stuck in."""
        assert nudges.evaluate(
            [candidate("brand-new")], {}, {}, default_days=7, escalation_gap=7
        ) == []

    def test_the_nudge_module_does_not_restate_the_source_rule(self):
        """A tripwire, not a proof — see the module docstring.

        If ``handoff``/``tasks`` ever appear here as a literal, two
        modules decide what a commitment is and the endpoint and the
        nudge can disagree without anything noticing.
        """
        from pathlib import Path

        source = Path(nudges.__file__).read_text(encoding="utf-8")
        code = "\n".join(
            line for line in source.splitlines()
            if not line.lstrip().startswith(("#", '"', "*"))
        )
        assert '"handoff"' not in code
        assert '"tasks"' not in code


class TestTheMessage:
    """What reaches a toast, and what it may claim."""

    def test_a_window_edge_run_is_hedged(self):
        nudge = nudges.evaluate(
            [candidate()], {"demo": streak(90, edge=True)}, {},
            default_days=7, escalation_gap=7,
        )[0]

        assert "at least 90 days" in nudge.message

    def test_a_measured_run_is_not_hedged(self):
        nudge = nudges.evaluate(
            [candidate()], {"demo": streak(9)}, {},
            default_days=7, escalation_gap=7,
        )[0]

        assert "Unchanged for 9 days" in nudge.message
        assert "at least" not in nudge.message

    def test_one_day_is_singular(self):
        nudge = nudges.evaluate(
            [candidate()], {"demo": streak(1)}, {},
            default_days=1, escalation_gap=7,
        )[0]

        assert "Unchanged for 1 day " in nudge.message

    def test_a_long_action_is_truncated_and_unwrapped(self):
        action = "Rebuild the\n  ingest pipeline " + "x" * 300
        nudge = nudges.evaluate(
            [candidate(next_action=action)], {"demo": streak(9)}, {},
            default_days=7, escalation_gap=7,
        )[0]

        assert "\n" not in nudge.message
        assert "Rebuild the ingest pipeline" in nudge.message
        assert nudge.message.endswith("…")

    def test_the_untruncated_action_survives_in_details(self):
        """The toast compresses; the alerts API must not."""
        action = "Rebuild the ingest pipeline " + "x" * 300
        nudge = nudges.evaluate(
            [candidate(next_action=action)], {"demo": streak(9)}, {},
            default_days=7, escalation_gap=7,
        )[0]

        assert nudge.details["next_action"] == action
        assert nudge.details["kind"] == "idle_nudge"
        assert nudge.details["threshold_days"] == 7
        assert nudge.details["days_unchanged"] == 9


class TestOrdering:
    def test_loudest_first_then_longest(self):
        found = nudges.evaluate(
            [candidate("a"), candidate("b"), candidate("c")],
            {"a": streak(8), "b": streak(30), "c": streak(9)},
            {},
            default_days=7,
            escalation_gap=7,
        )

        assert [n.project_name for n in found] == ["b", "c", "a"]


class TestTitleHasOneSource:
    """A resolve pattern that matches nothing is invisible."""

    def test_raise_and_resolve_derive_from_the_same_function(self):
        title = nudges.nudge_title("demo")
        prefix, suffix = nudges.NUDGE_TITLE_LIKE.split("%")

        assert title.startswith(prefix) and title.endswith(suffix)

    def test_a_nudge_is_not_mistaken_for_a_health_alert(self):
        """Two families share one agent and one LIKE-driven resolve."""
        from sysadmin.projects.agent import _ALERT_TITLE_LIKE, _alert_title

        assert not nudges.nudge_title("demo").endswith(
            _ALERT_TITLE_LIKE.split("%")[1]
        )
        assert not _alert_title("demo").endswith(
            nudges.NUDGE_TITLE_LIKE.split("%")[1]
        )


# ---------------------------------------------------------------------------
# The lifecycle: raise once, escalate by replacement, resolve set-based.
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return ProjectOrganiserAgent()


@pytest.fixture
def organiser_config():
    return ProjectOrganiserConfig(idle_nudges=IdleNudgeConfig(days=7, escalate_days=14))


def open_alert(name: str, severity: str) -> MagicMock:
    return MagicMock(
        title=nudges.nudge_title(name), severity=severity, resolved=False
    )


class TestLifecycle:
    async def _run(
        self,
        agent,
        config,
        *,
        streaks: dict[str, Streak],
        open_nudges: dict[str, MagicMock],
        rows=None,
    ):
        session = MagicMock()
        session.flush = AsyncMock()
        with (
            patch(
                "sysadmin.projects.agent.load_action_streaks",
                new=AsyncMock(return_value=streaks),
            ),
            patch.object(
                agent, "_open_nudges", new=AsyncMock(return_value=open_nudges)
            ),
            patch.object(agent, "raise_alert", new=AsyncMock()) as raise_alert,
            patch.object(
                agent, "_resolve_moved_on", new=AsyncMock(return_value=0)
            ) as resolve,
        ):
            counts = await agent._nudge_idle_projects(
                session,
                rows if rows is not None else [snapshot()],
                {},
                config,
            )
        return counts, raise_alert, resolve

    async def test_a_stuck_project_raises_once(self, agent, organiser_config):
        counts, raise_alert, _ = await self._run(
            agent, organiser_config, streaks={"demo": streak(8)}, open_nudges={}
        )

        assert counts == {"raised": 1, "escalated": 0, "resolved": 0}
        assert raise_alert.await_args.kwargs["severity"] == "info"

    async def test_an_open_nudge_is_not_re_raised(self, agent, organiser_config):
        """The organiser runs daily; raise_alert inserts unconditionally."""
        counts, raise_alert, _ = await self._run(
            agent,
            organiser_config,
            streaks={"demo": streak(9)},
            open_nudges={nudges.nudge_title("demo"): open_alert("demo", "info")},
        )

        assert counts == {"raised": 0, "escalated": 0, "resolved": 0}
        raise_alert.assert_not_awaited()

    async def test_escalation_replaces_the_quiet_row(self, agent, organiser_config):
        """Updating severity in place keeps a fingerprint already suppressed."""
        existing = open_alert("demo", "info")
        counts, raise_alert, _ = await self._run(
            agent,
            organiser_config,
            streaks={"demo": streak(14)},
            open_nudges={existing.title: existing},
        )

        assert counts == {"raised": 0, "escalated": 1, "resolved": 0}
        assert existing.resolved is True
        assert existing.resolved_at is not None
        assert raise_alert.await_args.kwargs["severity"] == "warning"

    async def test_an_escalated_nudge_does_not_escalate_again(
        self, agent, organiser_config
    ):
        counts, raise_alert, _ = await self._run(
            agent,
            organiser_config,
            streaks={"demo": streak(40)},
            open_nudges={nudges.nudge_title("demo"): open_alert("demo", "warning")},
        )

        assert counts == {"raised": 0, "escalated": 0, "resolved": 0}
        raise_alert.assert_not_awaited()

    async def test_a_moved_action_leaves_nothing_to_re_state(
        self, agent, organiser_config
    ):
        """The resolve runs with an empty exclusion set — everything closes."""
        counts, raise_alert, resolve = await self._run(
            agent, organiser_config, streaks={"demo": streak(0)}, open_nudges={}
        )

        raise_alert.assert_not_awaited()
        assert resolve.await_args.args[1] == set()
        assert counts["raised"] == 0

    async def test_a_still_stuck_project_is_excluded_from_the_resolve(
        self, agent, organiser_config
    ):
        _, _, resolve = await self._run(
            agent, organiser_config, streaks={"demo": streak(8)}, open_nudges={}
        )

        assert resolve.await_args.args[1] == {nudges.nudge_title("demo")}

    async def test_disabling_the_feature_touches_nothing(self, agent):
        config = ProjectOrganiserConfig(idle_nudges=IdleNudgeConfig(enabled=False))
        session = MagicMock()
        session.flush = AsyncMock()

        counts = await agent._nudge_idle_projects(session, [snapshot()], {}, config)

        assert counts == {"raised": 0, "escalated": 0, "resolved": 0}
        session.flush.assert_not_awaited()

    async def test_the_scan_flushes_before_reading_its_own_history(
        self, agent, organiser_config
    ):
        """Without it the newest point in every series is yesterday's scan."""
        session = MagicMock()
        session.flush = AsyncMock()
        with (
            patch(
                "sysadmin.projects.agent.load_action_streaks", new=AsyncMock(return_value={})
            ) as load,
            patch.object(agent, "_resolve_moved_on", new=AsyncMock(return_value=0)),
        ):
            await agent._nudge_idle_projects(
                session, [snapshot()], {}, organiser_config
            )

        session.flush.assert_awaited_once()
        assert session.flush.await_count == 1
        load.assert_awaited_once()


class TestResolveStatement:
    """The SQL shape of the set-based close."""

    @staticmethod
    def _compiled(session):
        return session.execute.await_args.args[0].compile()

    async def test_it_only_touches_this_agents_nudges(self, agent):
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        await agent._resolve_moved_on(session, set())

        compiled = self._compiled(session)
        assert nudges.NUDGE_TITLE_LIKE in compiled.params.values()
        assert "alerts.agent =" in str(compiled)
        assert "resolved IS false" in str(compiled)
        assert "title NOT IN" not in str(compiled)

    async def test_a_still_stuck_project_is_excluded(self, agent):
        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        await agent._resolve_moved_on(session, {nudges.nudge_title("demo")})

        assert "title NOT IN" in str(self._compiled(session))

    async def test_health_alerts_are_a_different_family(self, agent):
        """The two LIKE patterns must not match each other's titles."""
        from sysadmin.projects.agent import _ALERT_TITLE_LIKE

        session = MagicMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        await agent._resolve_moved_on(session, set())

        assert _ALERT_TITLE_LIKE not in self._compiled(session).params.values()


class TestOpenNudges:
    async def test_the_loudest_row_wins_a_duplicate_title(self, agent):
        """Comparing against the quietest would re-escalate every scan."""
        quiet, loud = open_alert("demo", "info"), open_alert("demo", "warning")
        session = MagicMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [quiet, loud]
        session.execute = AsyncMock(return_value=result)

        found = await agent._open_nudges(session)

        assert found[quiet.title] is loud


class TestThresholdKeying:
    """The override must be keyed the way the snapshots are."""

    async def test_a_manifest_name_unlike_its_directory_keeps_its_override(
        self, agent, tmp_path
    ):
        """``project_name`` is the directory; ``manifest.name`` is free text.

        Keying the threshold map on ``entry.name`` would silently drop
        the override for every project whose declared name differs from
        the folder it lives in — and the symptom would be a project
        nudging on the global default while its manifest said 21.
        """
        import yaml

        from sysadmin.core.config import AgentsConfig, AppConfig

        project = tmp_path / "sysadmin_assistant"
        project.mkdir()
        (project / ".git").mkdir()
        (project / ".project.yaml").write_text(
            yaml.safe_dump({
                "schema": 1,
                "id": "sysadmin-assistant",
                "name": "SysAdmin Assistant",
                "status": "active",
                "idle_nudge_days": 21,
            }),
            encoding="utf-8",
        )

        config = AppConfig(
            agents=AgentsConfig(
                project_organiser=ProjectOrganiserConfig(projects_root=str(tmp_path))
            )
        )
        row = snapshot("sysadmin_assistant")
        session = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock(rowcount=0))

        with (
            patch("sysadmin.projects.agent.get_config", return_value=config),
            patch.object(agent, "_analyse_project", return_value=row),
            patch.object(agent, "raise_alert", new=AsyncMock()),
            patch.object(
                agent,
                "_nudge_idle_projects",
                new=AsyncMock(return_value={"raised": 0, "escalated": 0, "resolved": 0}),
            ) as nudge,
        ):
            await agent._execute(session)

        assert nudge.await_args.args[2] == {"sysadmin_assistant": 21}


class TestConfigLadder:
    def test_a_descending_ladder_is_rejected(self):
        """It would raise both rungs on the same scan."""
        with pytest.raises(ValueError, match="escalate_days"):
            IdleNudgeConfig(days=14, escalate_days=7)

    def test_equal_rungs_are_allowed(self):
        assert IdleNudgeConfig(days=7, escalate_days=7).escalate_days == 7

    def test_the_shipped_default_is_a_week_then_a_fortnight(self):
        config = IdleNudgeConfig()

        assert (config.enabled, config.days, config.escalate_days) == (True, 7, 14)
