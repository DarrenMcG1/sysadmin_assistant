"""The trend report as the database produces it — the one query behind Tiers 1–3.

:mod:`sysadmin.monitor.log_trends` and :mod:`sysadmin.monitor.log_actions`
are pure by design: no database, no FastAPI, no filesystem.  Something
still has to run the grouped query and read ``services.yaml``, and until
Session 69 that something was ``routers/logs.py`` — correct while the
only two callers were two routes on one router.

The weekly review (:mod:`sysadmin.monitor.log_review`) is the third
caller and it is **not** a route, so leaving the builder on the router
would mean either a scheduled job importing a router or a second
implementation of the same query.  The router's own docstring already
refused the second option for the first two callers:

    Factored out rather than duplicated because the advice must be
    computed off *the same* report the trend serves — two callers
    running two queries a moment apart could rank a signature as new on
    one surface and established on the other.

A narrative that called a signature new while ``/api/logs/actions``
called it established would be that disagreement in prose, which is the
one form of it a reader cannot check.  So the builder moves here and all
three callers import it.

Nothing about the query changed in the move; the names lost their
leading underscore because they are now a module's surface rather than
one file's privates.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.models.agent_run import AgentRun
from sysadmin.monitor.log_trends import (
    LogTrendReport,
    MessageGroup,
    WindowCoverage,
    build_report,
)
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import (
    composed_log_sources,
    get_services,
    log_sources,
    stored_source_name,
)
from sysadmin.units.scan import declared_relations, discover_units

#: The severities the trend covers.  Wider than the alert family's
#: ``error``/``critical``, because Tier 2's question is "this *warning*
#: appeared 400x — noise or fault?", and a severity the trend cannot see
#: is a question it cannot answer.
TREND_SEVERITIES = ("warning", "error", "critical")


async def build_trend_report(
    session: AsyncSession, days: int | None
) -> LogTrendReport:
    """The grouped query and the fold, shared by all three tiers.

    Factored out rather than duplicated because the advice must be
    computed off *the same* report the trend serves — two callers running
    two queries a moment apart could rank a signature as new on one
    surface and established on the other, which is the kind of
    disagreement ``COLLISION_KINDS`` lives in ``ports.py`` to prevent.
    """
    config = get_config().agents.log_aggregator
    window_days = days or config.trend_window_days
    cap = config.trend_max_groups

    now = datetime.now(UTC)
    window_start = now - timedelta(days=window_days)
    previous_start = now - timedelta(days=window_days * 2)

    grouped = await session.execute(
        select(
            LogEntry.source,
            LogEntry.severity,
            LogEntry.message,
            func.count()
            .filter(LogEntry.logged_at >= window_start)
            .label("current"),
            func.count()
            .filter(
                LogEntry.logged_at >= previous_start,
                LogEntry.logged_at < window_start,
            )
            .label("previous"),
            func.count().label("total"),
            func.min(LogEntry.logged_at).label("first_seen"),
            func.max(LogEntry.logged_at).label("last_seen"),
        )
        .where(LogEntry.severity.in_(TREND_SEVERITIES))
        .group_by(LogEntry.source, LogEntry.severity, LogEntry.message)
        .order_by(desc(func.count()))
        # One over the cap, so hitting it is observed rather than assumed
        # from a length that happens to equal the limit.
        .limit(cap + 1)
    )
    rows = grouped.all()
    truncated = len(rows) > cap

    groups = [
        MessageGroup(
            source=r.source,
            severity=r.severity,
            message=r.message,
            current=r.current,
            previous=r.previous,
            total=r.total,
            first_seen=r.first_seen,
            last_seen=r.last_seen,
        )
        for r in rows[:cap]
    ]

    return build_report(
        groups,
        window_days=window_days,
        window_start=window_start,
        previous_start=previous_start,
        generated_at=now,
        coverage=await trend_coverage(session, previous_start, window_days),
        truncated=truncated,
    )


async def trend_coverage(
    session: AsyncSession, since: datetime, window_days: int
) -> WindowCoverage:
    """How thoroughly the agent polled across both windows.

    ``runs_expected`` is derived from the live poll interval rather than
    written down, so changing the interval moves it without anyone having
    to remember — ``JOB_CONFIG_PATHS``'s rule, one domain over.

    A run counts as truncated when it reported any source at its read
    ceiling.  That is the field that decides confidence, because it is
    the only one that means data was actually lost: a merely missed poll
    is caught up by the journal cursor on the next one.

    ``runs_instrumented`` counts the runs that *could* have said so, and
    it is the denominator rather than ``runs_observed``.
    ``details['truncated_sources']`` first appears on the run at
    2026-08-12 17:31; runs before it have no such key, so
    ``details->>'truncated_sources'`` is NULL and ``NULL <> '[]'`` is
    NULL — they are correctly excluded from the numerator and would be
    wrongly included in the denominator.  Measured 2026-08-17 that is
    120 of 7,000 rather than 120 of 17,730, and the two differ by 2.5x.
    ``.has_key`` rather than ``IS NOT NULL`` because a stored JSON
    ``null`` is still a run that reported.
    """
    agent_config = get_config().agents.log_aggregator
    result = await session.execute(
        select(
            func.count().label("runs"),
            func.count()
            .filter(
                AgentRun.details["truncated_sources"].as_string() != "[]",
            )
            .label("truncated"),
            func.count()
            .filter(AgentRun.details.has_key("truncated_sources"))
            .label("instrumented"),
        ).where(
            AgentRun.agent == "log_aggregator",
            AgentRun.started_at >= since,
        )
    )
    row = result.one()
    interval = max(1, agent_config.poll_interval_seconds)
    expected = int(window_days * 2 * 86400 / interval)
    return WindowCoverage(
        runs_observed=row.runs or 0,
        runs_expected=expected,
        runs_truncated=row.truncated or 0,
        runs_instrumented=row.instrumented or 0,
    )


def log_source_scopes() -> dict[str, bool]:
    """Unit name -> is it a user unit, from ``services.yaml``.

    Read here rather than in :mod:`sysadmin.monitor.log_actions` so that
    module stays pure.  Keyed on ``unit`` rather than the source's
    ``name``, because ``log_entries.source`` stores the unit — the two
    differ for most entries (``alfred`` vs ``alfred-backend.service``)
    and keying on the wrong one silently yields an empty map, which reads
    as "every source is a system unit".
    """
    return {
        source.unit: bool(source.user)
        for source in log_sources(get_services())
        if source.unit
    }


def declared_source_names() -> frozenset[str]:
    """Every value that can legitimately appear in ``log_entries.source``.

    Read here for the reason :func:`log_source_scopes` is read here, and
    per request for the reason :func:`unit_relations` is read per
    request — both underlying singletons are refreshed by
    :mod:`sysadmin.reload`, so a source added to either file is admitted
    without a restart.

    Two things it is deliberately **not**:

    1. **Not the source ``name``.**  The column holds a unit for every
       journal source, so a set of names would reject
       ``alfred-backend.service`` — the string that is actually stored —
       and admit ``alfred``, which never is.  The composition is
       :func:`~sysadmin.monitor.services.stored_source_name`'s, which
       mirrors the ingestion loop's own dispatch rather than restating it
       from the live table.
    2. **Not the distinct sources present in the table.**  A widened
       "declared or present" set would keep a retired source readable
       until retention purged it, at the cost of a query per request and
       of a route whose meaning drifts with the data underneath it.  The
       rows do not become unreachable — ``GET /api/logs/recent?source=``
       has no validator and is the surface for reading history — so the
       cost is bounded and stated rather than paid for.

    Both files, never one: ``kernel`` is declared in config.yaml because
    it belongs to no service, and it is 451,319 of the 451,569 rows in
    ``log_entries`` on this box.  A set built from services.yaml alone
    would be green in every fixture and 404 almost the whole table.
    """
    return frozenset(
        name
        for name in (
            stored_source_name(source)
            for source in composed_log_sources(get_config().agents.log_aggregator)
        )
        if name
    )


def unit_relations() -> dict[str, frozenset[str]]:
    """Source unit -> the units systemd declares it is related to.

    The declared dependency graph ``GET /api/logs/actions`` uses to tell
    one incident from two (``SNAG-LOG-001``).  Read here for the reason
    :func:`log_source_scopes` is read here — the pure module must not
    open files — and read **per request** for the reason that function
    already re-reads ``services.yaml`` per request: this endpoint is
    computed live and never served from storage, so its inputs are read
    live too.

    Three rules:

    1. **The scope resolution happens here, because this is where scope
       is known.**  ``log_entries.source`` is a bare unit name with no
       scope in it, and ``deadlock-api-ingest.service`` is installed in
       **both** scopes on this box running two different binaries.
       ``services.yaml`` is the only thing that says which one a log
       source means, so the graph is flattened to plain names *after*
       being filtered to each source's own scope — never before.

    2. **It reads unit files rather than the stored sweep, deliberately
       departing from ``estate/agent.py``'s precedent.**  That module
       reads the sweep's port attribution instead of running ``ss``
       itself, because two ``ss`` calls at two moments give two answers
       about live kernel state with neither surface saying which it
       used.  A unit file is not live state — it is a document that
       changes when someone edits it — so re-reading it is not a second
       observation of a moving target.  Taking the six-hourly sweep's
       copy would instead mean a unit installed this morning does not
       correlate until this evening, and fails *silently* when it
       doesn't.

    3. **Every failure is empty, never partial-and-unreported.**  An
       unreadable directory yields no relations, which costs
       cross-unit grouping and leaves same-unit grouping working —
       today's behaviour, which is the safe direction.
    """
    config = get_config().agents.service_discovery
    units, _ = discover_units(
        config.user_unit_dir, config.system_unit_dir, str(Path.home())
    )
    graph = declared_relations(units)
    scopes = {
        source.unit: ("user" if source.user else "system")
        for source in log_sources(get_services())
        if source.unit
    }
    return {
        unit: graph[(scope, unit)]
        for unit, scope in scopes.items()
        if (scope, unit) in graph
    }
