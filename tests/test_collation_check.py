"""SNAG-DB-002 — the collation check, and the three ways it could go wrong.

A glibc upgrade moved this box from locale data 2.43 to 2.44.  Counted
live on 2026-08-13, ``pg_database``:

===============  ========  ======  =============
database         recorded  actual  state
===============  ========  ======  =============
``alfred``       2.43      2.44    mismatch
``alfred_dev``   2.43      2.44    mismatch
``alfred_e2e``   2.43      2.44    mismatch
``alfred_test``  2.43      2.44    mismatch
``alfred_test_cc``  2.43   2.44    mismatch
``postgres``     2.43      2.44    mismatch
``projects``     2.43      2.44    mismatch
``template1``    2.43      2.44    mismatch
``estate``       2.44      2.44    ok — created after the upgrade
``estate_test``  2.44      2.44    ok
``venture``      2.44      2.44    ok
``template0``    NULL      2.44    **not tracked**
===============  ========  ======  =============

``estate`` and ``venture`` being clean is the evidence that ``CREATE
DATABASE`` stamps the *current* OS version rather than inheriting the
template's — so ``template1`` at 2.43 is not a trap for future
databases, only for its own indexes.

**What these tests can and cannot show.** The NULL rule lives in SQL and
sessions are mocked, so it is asserted on the statement text rather than
by round trip — the same limit ``tests/test_alert_recovery.py`` records.
Everything else is Python and is asserted directly.
"""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from sysadmin.monitor import collation
from sysadmin.monitor.agent import (
    RESOLVABLE_TITLE_PATTERNS,
    SERVICE_ALERT_KINDS,
    SysAdminAgent,
)
from sysadmin.monitor.collation import (
    COLLATION_DETAIL_KEY,
    Mismatch,
    collation_title,
    evaluate,
    resolved_databases,
)

LIVE_MISMATCHED = [
    "alfred", "alfred_dev", "alfred_e2e", "alfred_test",
    "alfred_test_cc", "postgres", "projects", "template1",
]


def _like(pattern: str, value: str) -> bool:
    """SQL ``LIKE`` for the ``%``-only patterns used here."""
    return re.fullmatch(re.escape(pattern).replace("%", ".*"), value) is not None


def _mismatch(datname: str = "projects") -> Mismatch:
    return Mismatch(datname=datname, recorded="2.43", actual="2.44")


# ── Rule 4: this family must stay out of _resolve_recovered's reach ──


class TestTitleIsNotSweptByTheServiceResolve:
    """This family resolves its own rows, so nothing else may.

    The assertion has outlived its original reason and the difference is
    worth stating.  It was written because dedup and the pattern sweep
    were mutually exclusive: that sweep closed every owned row the run
    did not **raise**, so a family raising nothing from its second run
    onward had its own row closed and reopened, each flip clearing the
    tray's ``{severity}:{title}`` fingerprint.  SNAG-AGENT-006 refuted
    the general form — the exclusion set is now what the run **judged**,
    and the service and threshold families deduplicate too.

    What survives is narrower and is why this still has to hold: this
    family resolves its own rows by id, in ``_check_collation``, and
    nothing here feeds the sweep's judged set.  A second owner would
    close a row on the first run and re-raise it on the next, which is
    the same flip-flop arrived at from the other direction.
    """

    @pytest.mark.parametrize("datname", LIVE_MISMATCHED + ["template0", "estate"])
    def test_no_resolvable_pattern_matches_a_collation_title(self, datname):
        title = collation_title(datname)
        matched = [p for p in RESOLVABLE_TITLE_PATTERNS if _like(p, title)]
        assert matched == [], (
            f"{title!r} is reachable by {matched} — the sysadmin agent "
            "would close this row on every run that dedups, and the "
            "next run would raise it again"
        )

    def test_the_database_name_sits_last_in_the_title(self):
        """Why the collision cannot happen, rather than that it does not.

        Every pattern in the tuple matches on a *final* word.  Ending the
        title with a database name keeps it clear of all five by
        construction — the rule a rename would otherwise break silently.
        """
        assert collation_title("projects").endswith("projects")
        assert collation_title("projects").split()[-1] not in SERVICE_ALERT_KINDS

    def test_it_is_distinct_from_the_stall_and_failure_families(self):
        from sysadmin.monitor.failures import FAILURE_DETAIL_KEY

        assert COLLATION_DETAIL_KEY != FAILURE_DETAIL_KEY
        assert COLLATION_DETAIL_KEY != "stalled_agent"


# ── Rule 1: not-knowing is not a mismatch ────────────────────────────


class TestTheNullRuleLivesInSql:
    """``template0`` records no version, and neither does a ``C``-locale DB.

    ``recorded != actual`` in Python reads NULL as a difference and
    invents an alert whose remedy does not exist.  This check fails
    **open** — deliberately the opposite of
    :mod:`sysadmin.core.schema_guard`, because there the cost of
    not-knowing is serving against the wrong schema and here it is an
    operator asked to reindex a database that is fine.
    """

    def test_both_sides_are_guarded_against_null(self):
        sql = " ".join(str(collation.MISMATCH_SQL).split())
        assert "datcollversion IS NOT NULL" in sql
        assert "pg_database_collation_actual_version(oid) IS NOT NULL" in sql

    def test_the_comparison_is_not_is_distinct_from(self):
        """``IS DISTINCT FROM`` would report 2.43 against NULL as a fault."""
        assert "IS DISTINCT FROM" not in str(collation.MISMATCH_SQL)

    def test_the_catalog_is_cluster_wide(self):
        """One connection sees every database — no second engine needed."""
        assert "pg_database" in str(collation.MISMATCH_SQL)


# ── Rule 3: raised once per open row, never once per run ─────────────


class TestEvaluate:
    def test_a_new_mismatch_is_raised(self):
        assert evaluate([_mismatch()], set()) == [_mismatch()]

    def test_a_mismatch_with_an_open_row_is_held(self):
        assert evaluate([_mismatch()], {"projects"}) == []

    def test_each_database_is_judged_alone(self):
        items = [_mismatch(name) for name in ("alfred", "projects")]
        assert evaluate(items, {"alfred"}) == [_mismatch("projects")]

    def test_the_live_population_costs_eight_rows_not_eight_a_run(self):
        items = [_mismatch(n) for n in LIVE_MISMATCHED]
        first = evaluate(items, set())
        assert len(first) == 8
        # Second run, rows now open: nothing further is written. At 300s
        # polling the raise-every-run pattern would cost 2,304 a day.
        assert evaluate(items, {m.datname for m in first}) == []


class TestResolvedDatabases:
    def test_a_reindexed_database_clears(self):
        assert resolved_databases({"projects"}, set()) == {"projects"}

    def test_a_dropped_database_clears_too(self):
        """The reason it is a set difference and not a loop over mismatches.

        A dropped database never appears in a query result again, so a
        per-mismatch loop can only ever observe the *fixed* case — the
        shape of SNAG-AGENT-004, locally.
        """
        assert resolved_databases({"alfred_e2e"}, {"projects"}) == {"alfred_e2e"}

    def test_a_still_stale_database_is_left_open(self):
        assert resolved_databases({"projects"}, {"projects"}) == set()


# ── What the alert says ──────────────────────────────────────────────


class TestTheMessageCarriesTheTrap:
    def test_reindex_is_named_before_refresh(self):
        """``REFRESH`` alone silences the warning without rebuilding.

        Run on its own it converts a loud known risk into a silent one,
        which is strictly worse than the state being reported.
        """
        message = _mismatch().message
        assert message.index("REINDEX") < message.index("REFRESH")

    def test_both_versions_are_stated(self):
        message = _mismatch().message
        assert "2.43" in message and "2.44" in message

    def test_the_remedy_is_a_list_in_order(self):
        remedy = _mismatch().details["remedy"]
        assert remedy == [
            "REINDEX DATABASE projects",
            "ALTER DATABASE projects REFRESH COLLATION VERSION",
        ]

    def test_details_name_the_database_for_the_open_row_lookup(self):
        assert _mismatch().details[COLLATION_DETAIL_KEY] == "projects"

    def test_severity_is_never_critical_and_never_info(self):
        """``critical`` breaks DND; ``info`` is below the tray's floor."""
        assert collation.COLLATION_SEVERITY == "warning"


# ── The agent method ─────────────────────────────────────────────────


def _agent_config(enabled: bool = True):
    cfg = MagicMock()
    cfg.collation.enabled = enabled
    return cfg


def _session(rows):
    session = MagicMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    session.execute = AsyncMock(return_value=result)
    return session


def _row(datname):
    return {"datname": datname, "recorded": "2.43", "actual": "2.44"}


@pytest.mark.asyncio
class TestCheckCollation:
    async def test_a_first_run_raises_one_row_per_database(self):
        agent = SysAdminAgent()
        agent.raise_alert = AsyncMock()
        agent._active_alerts = AsyncMock(return_value=[])
        session = _session([_row("projects"), _row("alfred")])

        raised = await agent._check_collation(session, _agent_config())

        assert raised == 2
        titles = {c.kwargs["title"] for c in agent.raise_alert.await_args_list}
        assert titles == {
            collation_title("projects"),
            collation_title("alfred"),
        }
        assert agent._collation_counts == {
            "mismatched": 2, "raised": 2, "resolved": 0,
        }

    async def test_a_second_run_holds_without_duplicating(self):
        agent = SysAdminAgent()
        agent.raise_alert = AsyncMock()
        open_row = MagicMock()
        open_row.details = {COLLATION_DETAIL_KEY: "projects"}
        open_row.id = "abc"
        agent._active_alerts = AsyncMock(return_value=[open_row])
        session = _session([_row("projects")])

        raised = await agent._check_collation(session, _agent_config())

        assert raised == 0
        agent.raise_alert.assert_not_awaited()
        # Standing count still reported — `raised` is 0 forever after
        # the first run, so it is not the number that matters.
        assert agent._collation_counts["mismatched"] == 1

    async def test_a_cleared_database_has_its_row_resolved(self):
        agent = SysAdminAgent()
        agent.raise_alert = AsyncMock()
        agent._resolve_alert_ids = AsyncMock()
        open_row = MagicMock()
        open_row.details = {COLLATION_DETAIL_KEY: "projects"}
        open_row.id = "abc"
        agent._active_alerts = AsyncMock(return_value=[open_row])
        session = _session([])

        await agent._check_collation(session, _agent_config())

        agent._resolve_alert_ids.assert_awaited_once_with(session, ["abc"])
        assert agent._collation_counts["resolved"] == 1

    async def test_alerts_from_other_families_are_ignored(self):
        """Open rows are keyed on the details key, not on being open."""
        agent = SysAdminAgent()
        agent.raise_alert = AsyncMock()
        agent._resolve_alert_ids = AsyncMock()
        stall_row = MagicMock()
        stall_row.details = {"stalled_agent": "file_organiser"}
        agent._active_alerts = AsyncMock(return_value=[stall_row])
        session = _session([_row("projects")])

        raised = await agent._check_collation(session, _agent_config())

        assert raised == 1
        agent._resolve_alert_ids.assert_awaited_once_with(session, [])

    async def test_disabled_runs_no_query_at_all(self):
        agent = SysAdminAgent()
        session = _session([])

        raised = await agent._check_collation(session, _agent_config(enabled=False))

        assert raised == 0
        session.execute.assert_not_awaited()
        assert agent._collation_counts == {
            "mismatched": 0, "raised": 0, "resolved": 0,
        }

    async def test_a_failing_catalog_read_costs_a_log_line_not_the_run(self):
        """PostgreSQL 14 has no ``pg_database_collation_actual_version``.

        The savepoint lesson from SNAG-DB-001 at the granularity
        available here: one check failing must not take the other
        nineteen with it.
        """
        from sqlalchemy.exc import SQLAlchemyError

        agent = SysAdminAgent()
        session = MagicMock()
        session.execute = AsyncMock(side_effect=SQLAlchemyError("no such function"))

        raised = await agent._check_collation(session, _agent_config())

        assert raised == 0
        assert agent._collation_counts["mismatched"] == 0
