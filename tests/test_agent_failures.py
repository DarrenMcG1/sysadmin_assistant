"""The consecutive-agent-failure alert family (SNAG-DB-001, gap 3).

The gap this closes: for ~18 hours of uptime the daemon logged
``agent_run_failed`` every five minutes and nothing read it, because the
alerting path was the thing that had broken.

Two properties get most of the attention here, because both are the
opposite of the obvious implementation:

- the family's title must **not** be reachable by
  ``SysAdminAgent._resolve_recovered``, or the sysadmin agent closes its
  rows while they are still true;
- a stalled agent must **not** also be reported as failing, or one dead
  agent produces two criticals.
"""

import re
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.escalation import Step
from sysadmin.monitor import failures
from sysadmin.monitor.agent import RESOLVABLE_TITLE_PATTERNS
from sysadmin.monitor.failures import (
    FAILURE_DETAIL_KEY,
    FailureAlert,
    OpenFailure,
    evaluate,
    failure_title,
    is_failing,
)

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)


def _entry(
    name: str = "log_aggregator",
    *,
    failures_count: int = 2,
    stalled: bool = False,
    enabled: bool = True,
    last_error: str | None = "CheckViolationError: chk_health_status",
) -> dict:
    """One ``build_self_report`` agents entry."""
    return {
        "name": name,
        "enabled": enabled,
        "stalled": stalled,
        "consecutive_failures": failures_count,
        "last_error": last_error,
        "last_run_at": "2026-08-13T11:55:00+00:00",
    }


def _open(agent_name: str, severity: str = "warning", age_hours: float = 0.0):
    return OpenFailure(
        alert_id=f"fail-{agent_name}",
        severity=severity,
        created_at=NOW - timedelta(hours=age_hours),
    )


# ── The title must stay out of _resolve_recovered's reach ────────────


def _like_to_regex(pattern: str) -> re.Pattern:
    """SQL ``LIKE`` as a regex — ``%`` is any run, ``_`` any one char."""
    out = []
    for ch in pattern:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    return re.compile("".join(out), re.DOTALL)


class TestTitleIsNotSweptByTheServiceResolve:
    """The reason the suffix is ``failing`` and not a severity word.

    ``_resolve_recovered`` closes every open row matching
    ``RESOLVABLE_TITLE_PATTERNS`` that the run did not re-raise. A
    failure row is raised by a *ladder* that depends on the quiet row
    staying open, so a second owner closing it destroys the escalation —
    the same reason ``% agent stalled`` is absent from that tuple.
    """

    @pytest.mark.parametrize(
        "agent_name",
        ["sysadmin", "project_organiser", "file_organiser",
         "log_aggregator", "service_discovery"],
    )
    def test_no_resolvable_pattern_matches_a_failure_title(self, agent_name):
        title = failure_title(agent_name)
        matched = [
            p for p in RESOLVABLE_TITLE_PATTERNS
            if _like_to_regex(p).fullmatch(title)
        ]
        assert matched == [], (
            f"{title!r} is reachable by {matched} — the sysadmin agent "
            "would resolve this family's rows while the fault is live"
        )

    def test_the_suffix_is_not_a_service_alert_kind(self):
        """Guards the rename that would reintroduce the collision."""
        from sysadmin.monitor.agent import SERVICE_ALERT_KINDS

        last_word = failures.FAILURE_TITLE_SUFFIX.split()[-1]
        assert last_word not in SERVICE_ALERT_KINDS

    def test_it_is_also_distinct_from_the_stall_family(self):
        from sysadmin.monitor.stalls import stall_title

        assert failure_title("sysadmin") != stall_title("sysadmin")
        assert failures.FAILURE_DETAIL_KEY != "stalled_agent"


# ── is_failing: the one definition of eligibility ────────────────────


class TestIsFailing:
    def test_at_the_threshold_it_is_failing(self):
        assert is_failing(_entry(failures_count=2), 2) is True

    def test_below_the_threshold_it_is_not(self):
        assert is_failing(_entry(failures_count=1), 2) is False

    def test_above_the_threshold_it_still_is(self):
        assert is_failing(_entry(failures_count=9), 2) is True

    def test_a_disabled_agent_is_never_failing(self):
        """It is not scheduled, so its last failure is history."""
        assert is_failing(_entry(failures_count=9, enabled=False), 2) is False

    def test_a_stalled_agent_is_never_also_failing(self):
        """The stall supersedes — one dead agent, one open row.

        An agent that failed repeatedly and then stopped being scheduled
        satisfies both tests. Raising both would put two criticals on
        screen for one fault.
        """
        assert is_failing(_entry(failures_count=9, stalled=True), 2) is False

    def test_a_missing_count_reads_as_zero(self):
        """Snapshots predating the field must not alert."""
        assert is_failing({"name": "x", "enabled": True}, 2) is False


# ── evaluate: the ladder ─────────────────────────────────────────────


class TestEvaluate:
    def test_first_detection_opens_quiet(self):
        due = evaluate(
            [_entry()], {}, failure_threshold=2,
            escalate_after_hours=24.0, now=NOW,
        )
        assert len(due) == 1
        assert due[0].severity == "warning"
        assert due[0].step is Step.RAISE
        assert due[0].first_alerted_at is None

    def test_an_open_warning_younger_than_the_gap_holds(self):
        due = evaluate(
            [_entry()], {"log_aggregator": _open("log_aggregator", age_hours=3)},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert due == []

    def test_a_warning_past_the_gap_escalates_to_critical(self):
        due = evaluate(
            [_entry()], {"log_aggregator": _open("log_aggregator", age_hours=25)},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert len(due) == 1
        assert due[0].severity == "critical"
        assert due[0].step is Step.ESCALATE
        assert due[0].hours_since_first_alert == pytest.approx(25.0)

    def test_an_open_critical_holds_rather_than_de_escalating(self):
        due = evaluate(
            [_entry()],
            {"log_aggregator": _open("log_aggregator", "critical", age_hours=1)},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert due == []

    def test_healthy_and_stalled_agents_are_omitted(self):
        due = evaluate(
            [
                _entry("sysadmin", failures_count=0),
                _entry("file_organiser", failures_count=5, stalled=True),
                _entry("log_aggregator", failures_count=2),
            ],
            {}, failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert [a.agent_name for a in due] == ["log_aggregator"]

    def test_criticals_sort_first(self):
        due = evaluate(
            [_entry("aaa_agent"), _entry("zzz_agent")],
            {"zzz_agent": _open("zzz_agent", age_hours=48)},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert [a.severity for a in due] == ["critical", "warning"]

    def test_an_entry_without_a_name_is_skipped(self):
        assert evaluate([{"enabled": True, "consecutive_failures": 9}], {},
                        failure_threshold=2, escalate_after_hours=24.0,
                        now=NOW) == []


# ── message and details ──────────────────────────────────────────────


class TestAlertShape:
    def _alert(self, **kw) -> FailureAlert:
        base = dict(
            agent_name="log_aggregator", severity="warning", step=Step.RAISE,
            consecutive_failures=3, last_error="boom", last_run_at="t",
            failure_threshold=2, first_alerted_at=None,
            hours_since_first_alert=None, escalate_after_hours=24.0,
        )
        base.update(kw)
        return FailureAlert(**base)  # type: ignore[arg-type]

    def test_title_is_derived_not_written(self):
        assert self._alert().title == failure_title("log_aggregator")

    def test_message_names_the_count_and_the_error(self):
        msg = self._alert().message
        assert "3 runs in a row" in msg
        assert "boom" in msg

    def test_one_failure_is_singular(self):
        assert "1 run in a row" in self._alert(consecutive_failures=1).message

    def test_escalated_message_leads_with_the_elapsed_time(self):
        msg = self._alert(
            step=Step.ESCALATE, severity="critical",
            first_alerted_at=NOW - timedelta(hours=26),
            hours_since_first_alert=26.0,
        ).message
        assert msg.startswith("Still failing 26 hours after the first warning")

    def test_details_carry_the_lookup_key(self):
        """Without it the next run cannot find this row and re-raises quiet."""
        assert self._alert().details[FAILURE_DETAIL_KEY] == "log_aggregator"

    def test_details_survive_the_escalation(self):
        d = self._alert(
            step=Step.ESCALATE, severity="critical",
            first_alerted_at=NOW, hours_since_first_alert=26.0,
        ).details
        assert d["escalated"] is True
        assert d["first_alerted_at"] == NOW.isoformat()
        assert d[FAILURE_DETAIL_KEY] == "log_aggregator"

    def test_a_missing_error_leaves_the_message_intact(self):
        assert self._alert(last_error=None).message.endswith("3 runs in a row")


class TestErrorText:
    def test_newlines_are_flattened_before_truncation(self):
        due = evaluate(
            [_entry(last_error="line one\n  line two\n\tline three")], {},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert due[0].last_error == "line one line two line three"

    def test_a_long_error_is_capped(self):
        due = evaluate(
            [_entry(last_error="x " * 400)], {},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert len(due[0].last_error) < 400

    def test_an_empty_error_becomes_none(self):
        due = evaluate(
            [_entry(last_error="")], {},
            failure_threshold=2, escalate_after_hours=24.0, now=NOW,
        )
        assert due[0].last_error is None


# ── wiring into SysAdminAgent ────────────────────────────────────────


@pytest.fixture
def sysadmin_agent():
    from sysadmin.monitor.agent import SysAdminAgent

    return SysAdminAgent()


def _report(*entries: dict) -> dict:
    return {"agents": list(entries), "count": len(entries)}


def _patch_report(report: dict):
    return patch(
        "sysadmin.monitor.agent.build_self_report",
        new_callable=AsyncMock, return_value=report,
    )


def _open_row(agent_name: str, severity: str = "warning", age_hours: float = 0.0):
    alert = MagicMock()
    alert.id = f"fail-{agent_name}"
    alert.title = failure_title(agent_name)
    alert.severity = severity
    alert.created_at = datetime.now(UTC) - timedelta(hours=age_hours)
    alert.details = {FAILURE_DETAIL_KEY: agent_name}
    return alert


class TestFailureAlerting:
    @pytest.mark.asyncio
    async def test_raises_for_a_failing_agent(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report(_entry())),
            patch.object(sysadmin_agent, "_active_alerts",
                         new_callable=AsyncMock, return_value=[]),
            patch.object(sysadmin_agent, "raise_alert",
                         new_callable=AsyncMock) as ra,
        ):
            n = await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert n == 1
        kwargs = ra.call_args.kwargs
        assert kwargs["title"] == "log_aggregator agent failing"
        assert kwargs["severity"] == "warning"
        assert kwargs["details"][FAILURE_DETAIL_KEY] == "log_aggregator"

    @pytest.mark.asyncio
    async def test_an_open_row_is_not_duplicated(
        self, sysadmin_agent, mock_session, mock_config
    ):
        """The branch that stops a row-per-run pile-up."""
        with (
            _patch_report(_report(_entry())),
            patch.object(sysadmin_agent, "_active_alerts", new_callable=AsyncMock,
                         return_value=[_open_row("log_aggregator")]),
            patch.object(sysadmin_agent, "raise_alert",
                         new_callable=AsyncMock) as ra,
        ):
            n = await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert n == 0
        ra.assert_not_called()

    @pytest.mark.asyncio
    async def test_recovery_resolves_the_row(
        self, sysadmin_agent, mock_session, mock_config
    ):
        with (
            _patch_report(_report(_entry(failures_count=0))),
            patch.object(sysadmin_agent, "_active_alerts", new_callable=AsyncMock,
                         return_value=[_open_row("log_aggregator")]),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock),
            patch.object(sysadmin_agent, "_resolve_alert_ids",
                         new_callable=AsyncMock) as resolve,
        ):
            await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert resolve.await_args_list[-1].args[1] == ["fail-log_aggregator"]

    @pytest.mark.asyncio
    async def test_becoming_stalled_hands_over_to_the_stall_family(
        self, sysadmin_agent, mock_session, mock_config
    ):
        """One open row that changes its mind, not two criticals.

        The agent was failing; now it is not running at all. The failure
        row is resolved and the stall family opens its own.
        """
        entry = _entry(failures_count=5, stalled=True)
        entry["stall_reason"] = "no run for 9000s"
        entry["seconds_since_last_run"] = 9000.0
        entry["interval_seconds"] = 300

        with (
            _patch_report(_report(entry)),
            patch.object(sysadmin_agent, "_active_alerts", new_callable=AsyncMock,
                         return_value=[_open_row("log_aggregator")]),
            patch.object(sysadmin_agent, "raise_alert",
                         new_callable=AsyncMock) as ra,
            patch.object(sysadmin_agent, "_resolve_alert_ids",
                         new_callable=AsyncMock) as resolve,
        ):
            await sysadmin_agent._check_agent_health(mock_session, mock_config)

        titles = [c.kwargs["title"] for c in ra.call_args_list]
        assert titles == ["log_aggregator agent stalled"]
        assert ["fail-log_aggregator"] in [
            call.args[1] for call in resolve.await_args_list
        ]

    @pytest.mark.asyncio
    async def test_escalation_resolves_the_quiet_row_rather_than_editing_it(
        self, sysadmin_agent, mock_session, mock_config
    ):
        """In-place severity keeps a fingerprint the tray has suppressed."""
        quiet = _open_row("log_aggregator", age_hours=30)
        with (
            _patch_report(_report(_entry())),
            patch.object(sysadmin_agent, "_active_alerts", new_callable=AsyncMock,
                         return_value=[quiet]),
            patch.object(sysadmin_agent, "raise_alert",
                         new_callable=AsyncMock) as ra,
        ):
            await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert quiet.resolved is True
        assert quiet.severity == "warning", "severity must not be edited in place"
        assert ra.call_args.kwargs["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_counts_are_reported_separately_from_stalls(
        self, sysadmin_agent, mock_session, mock_config
    ):
        """Two families, two counts — never summed into one number."""
        with (
            _patch_report(_report(_entry())),
            patch.object(sysadmin_agent, "_active_alerts",
                         new_callable=AsyncMock, return_value=[]),
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock),
        ):
            await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert sysadmin_agent._agent_failure_counts == {
            "failing": 1, "raised": 1, "escalated": 0,
        }
        assert sysadmin_agent._stall_counts["raised"] == 0

    @pytest.mark.asyncio
    async def test_disabled_self_monitoring_reports_zeroes_not_stale_counts(
        self, sysadmin_agent, mock_session, mock_config
    ):
        sysadmin_agent._agent_failure_counts = {
            "failing": 4, "raised": 4, "escalated": 1,
        }
        mock_config.self_monitor.enabled = False
        with patch("sysadmin.monitor.agent.build_self_report",
                   new_callable=AsyncMock) as report:
            n = await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert n == 0
        report.assert_not_called()
        assert sysadmin_agent._agent_failure_counts == {
            "failing": 0, "raised": 0, "escalated": 0,
        }

    @pytest.mark.asyncio
    async def test_both_families_read_one_snapshot(
        self, sysadmin_agent, mock_session, mock_config
    ):
        """Two fetches could disagree about the same agent."""
        with (
            _patch_report(_report(_entry())) as report,
            patch.object(sysadmin_agent, "_active_alerts", new_callable=AsyncMock,
                         return_value=[]) as active,
            patch.object(sysadmin_agent, "raise_alert", new_callable=AsyncMock),
        ):
            await sysadmin_agent._check_agent_health(mock_session, mock_config)

        assert report.await_count == 1
        assert active.await_count == 1
