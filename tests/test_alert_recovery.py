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

**The exclusion set changed in SNAG-AGENT-006 and this file is where
that is pinned.** It used to be ``_raised_titles``, filled by a
``raise_alert`` override; the service and threshold families raised
unconditionally, so "raised" and "still true" were the same set and the
distinction cost nothing. They deduplicate now — one dead timer wrote
**60** rows in five hours — so a family raises nothing on its second
run, and an exclusion set of raised titles would sweep a row that is
still true, re-raise it on the third run and sweep it again on the
fourth. The set is now ``_judged_titles``, filled by ``_raise_judged``
whether or not a row was written. ``tests/test_alert_dedup.py`` drives
the four-run lifecycle; what is asserted here is that the statement
excludes what was **judged**.

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

from sysadmin.core.models.alert import unresolved
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


async def resolve_sql(
    agent, session, unhealthy=frozenset(), judged=frozenset()
) -> str:
    agent._judged_titles |= set(judged)
    count = await agent._resolve_recovered(session, set(unhealthy))
    statement = session.execute.await_args.args[0]
    assert count == 27827
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def _rendered(clause) -> str:
    """One clause as it reaches PostgreSQL."""
    return str(clause.compile(dialect=postgresql.dialect()))


@pytest.mark.asyncio
class TestTheResolveStatement:
    async def test_it_is_scoped_to_this_agents_unresolved_rows(self, agent, session):
        sql = await resolve_sql(agent, session)

        assert "UPDATE sysadmin.alerts SET resolved=true" in sql
        assert "alerts.agent = 'sysadmin'" in sql
        # Composed from the predicate rather than typed out.  This line
        # read ``"alerts.resolved IS false"`` until 2026-08-27 and was
        # green throughout: it pinned the *rendering* that could not
        # reach either partial index, which is how a sequential scan over
        # 667k rows survived here for the life of the module —
        # ``TestJournalCommand``'s defect in a second family.  Written
        # this way it cannot pin a spelling at all; the one statement of
        # the predicate decides what it asserts.
        assert _rendered(unresolved()) in sql

    async def test_every_owned_pattern_is_in_the_population(self, agent, session):
        sql = await resolve_sql(agent, session)

        for pattern in RESOLVABLE_TITLE_PATTERNS:
            # `%` doubles in the compiled string — pyformat paramstyle.
            assert f"LIKE '{pattern.replace('%', '%%')}'" in sql

    async def test_titles_judged_still_true_are_excluded(self, agent, session):
        sql = await resolve_sql(
            agent,
            session,
            judged={"venture-assistant unreachable"},
        )

        assert "NOT IN ('venture-assistant unreachable')" in sql

    async def test_a_judged_fault_is_excluded_even_when_no_row_was_written(
        self, agent, session
    ):
        """The whole of SNAG-AGENT-006, expressed as one clause.

        On the second run of a sustained fault ``_raise_judged`` writes
        nothing, so an exclusion set built from raises would be empty
        here and this statement would close a row that is still true —
        then the third run would raise it again, and each flip clears
        the tray's ``{severity}:{title}`` fingerprint.
        """
        agent._judged_titles = {"Critical disk usage on /"}
        agent._suppressed = 1

        sql = await resolve_sql(agent, session)

        assert "NOT IN ('Critical disk usage on /')" in sql

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
        `unhealthy`, which does not depend on the streak.  Judging does
        not rescue it either: nothing is judged until the third
        consecutive degraded check, which is two runs away."""
        agent._judged_titles = set()

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
class TestJudgementIsCollectedCentrally:
    """One helper judges and then decides, so the two cannot drift.

    There are nine raise sites across ``_handle_status`` and
    ``_check_thresholds``.  An inline ``if title not in open: raise`` at
    each is the shape ``projects/snapshots.py`` argues against — the
    audit that motivated it counted eight call sites where there were
    nine — and here the copy that forgot to record its judgement would
    not fail, it would resolve a live alert.
    """

    async def _session(self):
        s = MagicMock()
        s.flush = AsyncMock()
        return s

    async def test_a_judgement_that_raises_records_the_title(self, agent):
        s = await self._session()

        written = await agent._raise_judged(
            s, severity="critical", title="redis unreachable",
            message="down", details={},
        )

        assert written == 1
        assert agent._judged_titles == {"redis unreachable"}

    async def test_a_judgement_that_is_suppressed_records_it_too(self, agent):
        agent._open_titles = {"redis unreachable"}
        s = await self._session()

        written = await agent._raise_judged(
            s, severity="critical", title="redis unreachable",
            message="down", details={},
        )

        assert written == 0
        assert agent._judged_titles == {"redis unreachable"}
        assert agent._suppressed == 1
        s.add.assert_not_called()

    async def test_the_alert_is_still_written_when_nothing_is_open(self, agent):
        s = await self._session()

        await agent._raise_judged(
            s, severity="warning", title="x warning", message="m", details={},
        )

        s.add.assert_called_once()
        s.flush.assert_awaited_once()

    async def test_the_row_just_written_dedups_the_rest_of_the_run(self, agent):
        """Two identically-named GPUs must not open two rows.

        The snapshot is taken before anything is raised, so within one
        run the helper has to consult what it has itself written.
        """
        s = await self._session()
        for _ in range(2):
            await agent._raise_judged(
                s, severity="warning", title="High VRAM usage on RX 7900",
                message="m", details={},
            )

        assert s.add.call_count == 1
        assert agent._suppressed == 1
