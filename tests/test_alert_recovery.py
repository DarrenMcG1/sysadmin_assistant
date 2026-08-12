"""SNAG-AGENT-004 — recovery observed set-based, for the service side.

Recovery used to be observed one service at a time, inside the loop over
the *configured* services.  A service removed from configuration is never
checked again, so it can never be seen to recover; ``run_retention``
purges ``resolved = TRUE`` rows only, deliberately, so nothing else was
ever going to clear them.  Resource-threshold alerts had no resolve path
at any point in this application's life.

Counted live on 2026-08-12, unresolved:

===================================  ======  ====================
title                                  rows  newest
===================================  ======  ====================
``Critical disk usage on /``         13,971  2026-07-26
``personal-assistant unreachable``    9,748  2026-07-24
``personal-assistant-frontend …``     9,748  2026-07-24
``High disk usage on /``              9,530  2026-06-28
``redis unreachable``                 6,283  2026-03-07
``ollama unreachable``                1,824  2026-07-24
``nuxt-frontend unreachable``           224  2026-02-08
===================================  ======  ====================

This is the defect ``ProjectOrganiserAgent._resolve_recovered`` already
fixed on the project side, at sixteen times the scale.

**What these tests can and cannot show.** Sessions are mocked, so a
``WHERE`` clause has no effect here and the *population* is asserted on
compiled SQL — it proves the predicate is in the statement, not that
PostgreSQL evaluates it as intended.  The classification half is
asserted in Python against a stand-in for SQL ``LIKE``, so that "does
``file_organiser agent stalled`` fall inside this agent's resolve?" has
an answer that does not depend on a database being up.
"""

import inspect
import re
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from sysadmin.core.unit_failure import unit_failure_title
from sysadmin.monitor.agent import (
    RESOLVABLE_TITLE_PATTERNS,
    SERVICE_ALERT_KINDS,
    SysAdminAgent,
    disk_alert_title,
    service_alert_title,
)
from sysadmin.monitor.stalls import STALL_TITLE_SUFFIX


def _like(pattern: str, value: str) -> bool:
    """SQL ``LIKE`` for the ``%``-only patterns used here."""
    return re.fullmatch(re.escape(pattern).replace("%", ".*"), value) is not None


def owned(title: str) -> bool:
    """Would ``_resolve_recovered``'s population include this title?"""
    return any(_like(p, title) for p in RESOLVABLE_TITLE_PATTERNS)


# ---------------------------------------------------------------------------
# Which alert families this agent owns the recovery of
# ---------------------------------------------------------------------------


class TestThePopulation:
    @pytest.mark.parametrize("kind", SERVICE_ALERT_KINDS)
    def test_every_service_state_is_owned(self, kind):
        assert owned(service_alert_title("redis", kind))

    def test_a_retired_service_is_owned_though_it_is_in_no_config(self):
        """The reason the population is patterns and not the service list."""
        assert owned("personal-assistant-frontend unreachable")
        assert owned("ollama unreachable")

    @pytest.mark.parametrize("mount", ["/", "/run/media/gaddi/PENDRIVE"])
    @pytest.mark.parametrize("critical", [True, False])
    def test_disk_thresholds_are_owned(self, mount, critical):
        assert owned(disk_alert_title(mount, critical=critical))

    def test_the_other_resource_thresholds_are_owned(self):
        assert owned("High RAM usage")
        assert owned("High GPU temperature on AMD Radeon RX 7900 XTX")
        assert owned("High VRAM usage on AMD Radeon RX 7900 XTX")


class TestWhatThisAgentMustNotResolve:
    """Three families with a lifecycle owner already. A second owner
    closes a row while it is still true."""

    def test_a_stalled_agent_is_left_alone(self):
        """stalls.py needs the quiet row open to escalate off it."""
        assert not owned(f"file_organiser {STALL_TITLE_SUFFIX}")

    def test_a_unit_failure_is_left_alone(self):
        """unit_failure.py writes it dead; the lifespan resolves it alive."""
        assert not owned(unit_failure_title("sysadmin.service"))

    def test_an_anomaly_is_left_alone(self):
        """_check_anomalies resolves by id when the resource returns to range."""
        anomaly = MagicMock(label="cpu")

        assert not owned(SysAdminAgent._anomaly_title(anomaly))

    def test_the_log_aggregators_rows_are_a_different_agent(self):
        """547,814 `Log error: kernel` rows are out of scope by `agent`,
        not by title — and they are events, not states, so they need a
        rule of their own rather than this one widened."""
        assert SysAdminAgent.name != "log_aggregator"


# ---------------------------------------------------------------------------
# The statement
# ---------------------------------------------------------------------------


@pytest.fixture
def agent():
    return SysAdminAgent()


@pytest.fixture
def session():
    s = MagicMock()
    s.execute = AsyncMock(return_value=MagicMock(rowcount=27827))
    return s


async def resolve_sql(agent, session, unhealthy=frozenset()) -> str:
    count = await agent._resolve_recovered(session, set(unhealthy))
    statement = session.execute.await_args.args[0]
    assert count == 27827
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


@pytest.mark.asyncio
class TestTheResolveStatement:
    async def test_it_is_scoped_to_this_agents_unresolved_rows(self, agent, session):
        sql = await resolve_sql(agent, session)

        assert "UPDATE sysadmin.alerts SET resolved=true" in sql
        assert "alerts.agent = 'sysadmin'" in sql
        assert "alerts.resolved IS false" in sql

    async def test_every_owned_pattern_is_in_the_population(self, agent, session):
        sql = await resolve_sql(agent, session)

        for pattern in RESOLVABLE_TITLE_PATTERNS:
            # `%` doubles in the compiled string — pyformat paramstyle.
            assert f"LIKE '{pattern.replace('%', '%%')}'" in sql

    async def test_titles_raised_this_run_are_excluded(self, agent, session):
        agent._raised_titles = {"venture-assistant unreachable"}

        sql = await resolve_sql(agent, session)

        assert "NOT IN ('venture-assistant unreachable')" in sql

    async def test_an_unhealthy_services_whole_family_is_excluded(
        self, agent, session
    ):
        """Not only the title raised: a service transitioning
        degraded → critical has two open rows and neither is a recovery."""
        sql = await resolve_sql(agent, session, unhealthy={"venture-chat"})

        for kind in SERVICE_ALERT_KINDS:
            assert f"'{service_alert_title('venture-chat', kind)}'" in sql

    async def test_a_degraded_service_survives_a_daemon_restart(
        self, agent, session
    ):
        """`_degraded_counts` is in memory and resets on restart, so the
        first run afterwards raises nothing for a service that has been
        degraded for hours.  Testing "did this run raise it?" would close
        that alert and re-raise it two checks later — a recovery
        announced to the tray for a fault that never went away.  Hence
        `unhealthy`, which does not depend on the streak."""
        agent._raised_titles = set()

        sql = await resolve_sql(agent, session, unhealthy={"venture-chat"})

        assert f"'{service_alert_title('venture-chat', 'degraded')}'" in sql

    async def test_nothing_open_and_nothing_raised_still_runs(self, agent, session):
        """No exclusions must not become no WHERE clause."""
        sql = await resolve_sql(agent, session)

        assert "NOT IN" not in sql
        assert "alerts.agent = 'sysadmin'" in sql


# ---------------------------------------------------------------------------
# Raise and resolve derive from one place
# ---------------------------------------------------------------------------


class TestNoDrift:
    def test_the_service_patterns_are_built_from_the_kinds(self):
        for kind in SERVICE_ALERT_KINDS:
            assert f"% {kind}" in RESOLVABLE_TITLE_PATTERNS

    def test_handle_status_alerts_only_in_kinds_the_resolve_knows(self):
        """Adding a sixth status without a sixth kind leaves its alerts
        immortal — the failure mode is silence, so it is asserted here.

        Reaches the literal call sites only; the one that passes
        ``status`` through is covered by the test below."""
        source = inspect.getsource(SysAdminAgent._handle_status)
        literals = re.findall(r'service_alert_title\([^,]+, "([^"]+)"\)', source)

        assert literals, "the raise sites stopped going through the constructor"
        for kind in literals:
            assert kind in SERVICE_ALERT_KINDS

    @pytest.mark.parametrize("status", ["critical", "unreachable"])
    def test_the_statuses_passed_through_verbatim_are_kinds(self, status):
        """``_handle_status`` hands ``status`` straight to the
        constructor for these two, so the status vocabulary and the alert
        vocabulary have to agree on them by name."""
        assert status in SERVICE_ALERT_KINDS
        assert owned(service_alert_title("venture-chat", status))


@pytest.mark.asyncio
class TestRaisedTitlesAreCollectedCentrally:
    async def test_raise_alert_records_the_title(self, agent):
        s = MagicMock()
        s.flush = AsyncMock()

        await agent.raise_alert(s, severity="critical", title="redis unreachable")

        assert agent._raised_titles == {"redis unreachable"}

    async def test_the_alert_is_still_written(self, agent):
        s = MagicMock()
        s.flush = AsyncMock()

        alert = await agent.raise_alert(s, severity="warning", title="x warning")

        s.add.assert_called_once_with(alert)
        s.flush.assert_awaited_once()
