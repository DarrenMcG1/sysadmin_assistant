"""SysAdmin Agent — infrastructure health monitoring and resource tracking.

Checks:
- Service health via HTTP, TCP, or systemd
- CPU, RAM, disk, swap, load averages via psutil
- AMD GPU utilisation, temperature, VRAM via rocm-smi / sysfs
- Port conflict detection

- Resource anomalies (z-score against recent history, not just thresholds)
- Agent liveness — alerts when another agent silently stops running

Alerting:
- OK → update DB, no notification
- DEGRADED → 3 consecutive = escalate to WARNING
- WARNING → log to alerts table
- CRITICAL → immediate alert (to be picked up by notifier)
- A fault that is still true writes no second row.  The service and
  threshold families deduplicate against their own open rows, and the
  sweep that closes them keys on what the run **judged** rather than on
  what it raised — see :meth:`SysAdminAgent._raise_judged`
  (SNAG-AGENT-006) and :mod:`sysadmin.estate.agent`, which is where the
  pairing was first shown to work.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import psutil
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import AnomalyConfig, AppConfig, get_config
from sysadmin.core.escalation import QUIETEST_SEVERITY, may_quieten_in_place
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.core.text import TRUNCATION_MARKER
from sysadmin.estate import client as estate_client
from sysadmin.monitor import collation, failures, stalls
from sysadmin.monitor.anomaly import DISK_KEY_PREFIX, Anomaly, detect_anomalies
from sysadmin.monitor.gpu import get_gpu_usage
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot
from sysadmin.monitor.models.service_health import ServiceHealth
from sysadmin.monitor.self_monitor import build_self_report
from sysadmin.monitor.services import SKIPPED, ServiceEntry, check_plan, get_services
from sysadmin.monitor.systemd import SystemdQueryError, get_unit_status, restart_unit

logger = logging.getLogger(__name__)

#: The log event :meth:`SysAdminAgent._refresh_open` writes when a
#: standing row is judged **louder** than the rung it is open at.
#:
#: A constant rather than a literal because it is read twice and the two
#: readers must not be able to disagree: this module emits it, and
#: :func:`sysadmin.snag_claims.check_rung_left_stale` counts it in
#: ``log_entries`` to answer the one question ``SNAG-AGENT-012`` names as
#: its trigger — *"the first ``alert_rung_left_stale`` line that is not a
#: test's"*.  :data:`~sysadmin.core.agent.AGENT_RUN_FAILED_EVENT`'s rule
#: for its reason, and the failure mode of a rename is the one that
#: matters here: a check spelling the old name reports the trigger as
#: never having fired, for ever, and nothing says otherwise.
#:
#: It is also the **signature** the journal family deduplicates on.
#: :func:`~sysadmin.monitor.log_signature.signature` maps digit runs to
#: ``N``, so a name carrying no digits survives normalisation unchanged
#: and the stored ``message`` is this string exactly — which is what lets
#: the count above be an equality rather than a pattern.
RUNG_LEFT_STALE_EVENT = "alert_rung_left_stale"

#: Ceiling on the DBAPI error text carried into a ``service_health``
#: row.  A SQLAlchemy exception embeds the failing statement and its
#: bound parameters, which for a rejected health row is several hundred
#: characters of noise around one useful clause; the full text goes to
#: the log, which is where anyone diagnosing it will be looking.
WRITE_ERROR_CHARS = 400


def _truncate_error(exc: Exception) -> str:
    """The exception as one capped line, class name first.

    The class name leads because it is the part that survives
    truncation and the part that classifies the fault —
    ``IntegrityError`` versus ``OperationalError`` is the difference
    between a bad row and a lost connection, and only the first is this
    service's own doing.
    """
    text = " ".join(f"{exc.__class__.__name__}: {exc}".split())
    if len(text) <= WRITE_ERROR_CHARS:
        return text
    return text[:WRITE_ERROR_CHARS] + TRUNCATION_MARKER

#: Title suffix for stalled-agent alerts. Re-exported from
#: :mod:`sysadmin.monitor.stalls`, which owns it along with the escalation
#: ladder — one definition, since raise, escalate and resolve all derive
#: their title from it and a resolve pattern that matches nothing fails
#: silently while the table grows.
STALL_TITLE_SUFFIX = stalls.STALL_TITLE_SUFFIX

#: Timeout for HTTP health probes.
HTTP_CHECK_TIMEOUT_S = 10.0

#: Every way :meth:`SysAdminAgent._handle_status` can name a service in an
#: alert title.  One tuple because raise and resolve both derive from it —
#: the rule :func:`sysadmin.projects.agent._alert_title` records, for the
#: reason a hand-written resolve pattern that matches nothing fails
#: silently while the table grows.
SERVICE_ALERT_KINDS = (
    "degraded",
    "warning",
    "critical",
    "unreachable",
    "auto-restarted",
)


#: The rung an outage gets when the estate's arbiter stopped the unit.
#:
#: ``SNAG-AGENT-011``.  ``venture-chat.service`` is stopped and restarted
#: by estate-manager's arbiter whenever a lease names it in
#: ``stopped_units``, so this box put a **persistent** critical toast on
#: screen for most of every night — measured over the current regime, 6
#: nightly rows at a mean of 346 minutes open — about a service that is
#: down on purpose.  ``critical`` is the one severity
#: ``sysadmin_tray/notifications.py`` leaves on screen, and it is
#: reserved for a fault costing something now.
#:
#: **A quietening, never a suppression** — ``known_noise`` rule 2's rule
#: and ``TRANSIENT_HOLDER_SEVERITY``'s reason, which is the same
#: situation one domain over: the finding is *literally correct* and its
#: remedy does not apply.  The row still exists, still counts, still
#: reaches ``GET /api/sysadmin/alerts`` and ``GET
#: /api/services/reliability``, and still resolves on the first healthy
#: poll.  What it stops doing is interrupting.
#:
#: **Derived, and deliberately not imported from the judge.**  It is the
#: same rung as
#: :data:`~sysadmin.estate.judgements.TRANSIENT_HOLDER_SEVERITY` and it
#: is *not* that constant: importing the estate judge's vocabulary to
#: decide a service's rung is the thing ``judgements.py`` rule 3 read in
#: reverse forbids — this family consults a fact the estate publishes,
#: and the estate acquires no say in what that fact is worth.  So it
#: comes from :data:`~sysadmin.core.escalation.QUIETEST_SEVERITY`, which
#: both domains may import and which is genuinely derived from
#: ``SEVERITY_ORDER`` rather than written as ``"info"``.  A test pins the
#: two together, because two families that quieten to different floors
#: would be a fact stated twice.
ARBITRATED_STOP_SEVERITY = QUIETEST_SEVERITY

#: The reading a run starts with, before anything asks the estate.
#:
#: ``unread`` rather than ``idle``, and the difference is the whole of
#: ``ports_checked``'s rule at the size of a default: "nobody asked" and
#: "the estate holds nothing" are both empty, and only the first must
#: never be spent as good news.  It fails open either way —
#: :meth:`~sysadmin.estate.client.ArbitratedStops.stopped` answers
#: ``False`` for both — so what this decides is not the rung but what the
#: row *says it knew*.
_NO_ARBITRATION = estate_client.ArbitratedStops(
    reading=estate_client.ARBITRATION_UNREAD
)


def service_alert_title(service_name: str, kind: str) -> str:
    """The alert title for ``service_name`` being in state ``kind``."""
    return f"{service_name} {kind}"


def disk_alert_title(mount: str, critical: bool) -> str:
    """The alert title for disk occupancy on ``mount``."""
    return f"{'Critical' if critical else 'High'} disk usage on {mount}"


#: Alert families whose *recovery* this agent is responsible for observing.
#:
#: Written as ``LIKE`` patterns rather than derived from the configured
#: services, and that is the whole point of SNAG-AGENT-004: a set built
#: from configuration cannot contain a **deconfigured** service, so
#: ``redis unreachable`` — 6,283 rows, newest 2026-03-07 — could never be
#: matched by anything.  ``retention.run_retention`` purges resolved rows
#: only, so those rows were immortal.
#:
#: Two families are deliberately **absent**, because something else already
#: owns their lifecycle and a second owner is how a row gets closed while
#: still being true:
#:
#: - ``Unusual % usage`` — :meth:`SysAdminAgent._check_anomalies` resolves
#:   by alert id when the resource returns to range.
#: - ``% agent stalled`` — :mod:`sysadmin.monitor.stalls` owns the quiet →
#:   loud ladder, and its escalation *depends* on the quiet row staying
#:   open for ``escalate_after_hours``.
#: - ``% failed`` — :mod:`sysadmin.core.unit_failure` writes it while this
#:   application is dead and the lifespan resolves it on the next start.
#:   That pairing is what makes the row legitimate; resolving it from here
#:   would close it before anyone saw it.
#: - ``% agent failing`` — :mod:`sysadmin.monitor.failures` owns the same
#:   quiet → loud ladder for agents whose *runs* keep failing, and
#:   resolves off the streak returning to zero.  Its suffix was chosen so
#:   that it cannot match any pattern in this tuple: ``failing`` is not
#:   one of :data:`SERVICE_ALERT_KINDS`, and a family ending in
#:   ``degraded``/``warning``/``critical``/``unreachable``/``auto-restarted``
#:   would have its rows closed from here while they were still true.
#:   ``tests/test_agent_failures.py`` pins that.
#: - ``Stale collation version on %`` — :mod:`sysadmin.monitor.collation`
#:   raises **once per open row** and resolves its own rows by id, so a
#:   sweep from here would be the second owner of one lifecycle.  That is
#:   the reason it stays out, and it is *not* the reason originally
#:   written here.  The original said dedup and this sweep are mutually
#:   exclusive; that was true of an exclusion set holding the titles the
#:   run **raised**, which since SNAG-AGENT-006 it no longer is.  The
#:   service and threshold families deduplicate now too, and survive this
#:   sweep because :attr:`SysAdminAgent._judged_titles` carries every
#:   fault the run measured, written or suppressed.  What has not changed
#:   is that two owners of one row close it while the other still holds
#:   it true — this repository's most repeated defect, found at three
#:   scales.  The database name sits last in the title, which keeps it
#:   clear of the five ``% <kind>`` patterns by construction rather than
#:   by luck.
RESOLVABLE_TITLE_PATTERNS = tuple(
    f"% {kind}" for kind in SERVICE_ALERT_KINDS
) + (
    # _check_thresholds — one per resource, and until now these had no
    # resolve path *at all*.  23,501 rows were open on 2026-08-12, 13,971
    # of them `Critical disk usage on /` last raised 2026-07-26, against a
    # disk that has been at 68 % since.  A condition that recovered and
    # could not be observed recovering is the same defect as a service
    # that was retired, so it is fixed by the same statement.
    "High RAM usage",
    "High GPU temperature on %",
    "High VRAM usage on %",
    "Critical disk usage on %",
    "High disk usage on %",
)

#: The stall-ladder outcome of a run that did nothing about stalls —
#: because ``self_monitor.enabled`` is false, or because no agent is
#: stalled. Zeroes rather than an absent key: ``"stalls": {}`` in
#: ``agent_runs.details`` reads as "the check did not run", which is the
#: exact confusion Session 39 exists to remove.
_NO_STALLS: dict[str, int] = {"stalled": 0, "raised": 0, "escalated": 0}

#: The failure-ladder outcome of a run that did nothing about failing
#: agents. Zeroes rather than an absent key, for the same reason as
#: :data:`_NO_STALLS`.
_NO_AGENT_FAILURES: dict[str, int] = {"failing": 0, "raised": 0, "escalated": 0}

#: The collation outcome of a run that checked nothing — because
#: ``agents.sysadmin.collation.enabled`` is false. Zeroes rather than an
#: absent key, for the same reason as :data:`_NO_STALLS`: ``{}`` in
#: ``agent_runs.details`` reads as "the check did not run", and here that
#: is *exactly* what it means, so the two must not look alike.
_NO_COLLATION: dict[str, int] = {"mismatched": 0, "raised": 0, "resolved": 0}


#: Timer properties worth recording, under readable names.  ``systemctl
#: show`` returns microseconds-since-epoch as strings and "0" for "never",
#: neither of which is worth carrying into the details blob raw.
#:
#: **These are the schedule's own facts and only those.**  ``Unit`` names
#: the unit the timer starts and is read into :data:`_TRIGGERED_PROPS`'
#: subject rather than recorded as a timer fact in its own right.
_TIMER_PROPS = {
    "LastTriggerUSec": "last_run",
    "NextElapseUSecRealtime": "next_run",
}

#: Properties read from the unit the timer *starts*, under readable names.
#:
#: ``SNAG-SYSD-005``.  ``Result`` used to be read from the **timer**, and a
#: timer's ``Result`` reports whether the timer unit itself started — it is
#: ``success`` on all ten declared timers on this box while one of the ten
#: triggered services sits at ``exit-code``.  So the field named
#: ``last_result`` asserted that a run had succeeded on every one of the
#: 3,988 consecutive ``ok`` checks written across the twenty days
#: ``alfred-career-mail.service`` failed every morning.  It is the
#: triggered unit's ``Result`` now, which is the fact the name always
#: claimed.
_TRIGGERED_PROPS = {
    "Result": "last_result",
    "ActiveState": "triggered_active_state",
    "ExecMainStatus": "triggered_exit_status",
}


def _timer_facts(props: dict, triggered: dict | None = None) -> dict:
    """The last-run picture for a timer, from ``systemctl show`` output.

    ``props`` is the timer's own properties; ``triggered`` those of the
    unit it starts, or ``None`` when that unit could not be read.

    **A triggered unit that could not be read omits ``last_result``
    rather than defaulting it.**  ``ports_checked``'s rule: a run whose
    outcome is unknown must not be served as a run that succeeded, which
    is precisely the collapse this function shipped for the life of the
    ``kind: timer`` check.  ``triggered_result_recorded`` carries the
    distinction for a reader of a stored row.
    """
    facts: dict = {}
    for prop, label in _TIMER_PROPS.items():
        raw = props.get(prop)
        if raw in (None, "", "0", "[not set]", "n/a"):
            continue
        facts[label] = raw

    unit = (props.get("Unit") or "").strip()
    if unit:
        facts["triggered_unit"] = unit

    # Note the sentinel set differs from the timer's by one member: "0"
    # is dropped there because it is systemd's "never" for a timestamp,
    # and kept here because it is `ExecMainStatus`' "exited cleanly".
    for prop, label in _TRIGGERED_PROPS.items():
        raw = (triggered or {}).get(prop)
        if raw in (None, "", "[not set]", "n/a"):
            continue
        facts[label] = raw

    facts["last_run_recorded"] = "last_run" in facts
    facts["triggered_result_recorded"] = "last_result" in facts
    return facts


class SysAdminAgent(BaseAgent):
    """Infrastructure health monitoring agent."""

    name = "sysadmin"

    def __init__(self) -> None:
        self._degraded_counts: dict[str, int] = {}
        self._failure_counts: dict[str, int] = {}
        # The estate arbiter's active lease, read at most once per run and
        # only when something is actually down (SNAG-AGENT-011). `None`
        # means "this run has not asked", which is why the reading itself
        # cannot carry that state — see `_NO_ARBITRATION`.
        self._arbitration: estate_client.ArbitratedStops | None = None
        # The HTTP client is owned by each run, never by the application —
        # runs happen on APScheduler threads under asyncio.run(), so a
        # client created once at startup would outlive its loop.
        self._http = LoopBoundClient(
            lambda: httpx.AsyncClient(timeout=HTTP_CHECK_TIMEOUT_S)
        )
        # Resource keys that fired a fixed-threshold alert this run — an
        # anomaly for the same resource would just be a duplicate.
        self._threshold_keys: set[str] = set()
        # Last known status per service, for service.status change events.
        self._last_status: dict[str, str] = {}
        # Stall ladder outcome for the current run. Reset per run rather
        # than accumulated: a stale count reported in agent_runs.details
        # would read as an escalation that this run performed.
        self._stall_counts: dict[str, int] = _NO_STALLS
        # Deliberately NOT named _failure_counts: that one already
        # exists above and counts consecutive *service* check failures
        # for auto-restart. Two meanings behind one name in one class is
        # how a counter gets reset by the wrong branch.
        self._agent_failure_counts: dict[str, int] = _NO_AGENT_FAILURES
        # Collation outcome for the current run. Reset per run for the
        # same reason as _stall_counts: a carried-over count reads as
        # work this run performed.
        self._collation_counts: dict[str, int] = _NO_COLLATION
        # Titles of this agent's unresolved rows, snapshotted once at
        # the top of the run. The dedup reads this; nothing writes an
        # alert without consulting it. There was a `_raised_titles` set
        # here until SNAG-AGENT-006, filled by a `raise_alert` override
        # and read by `_resolve_recovered`; both are gone, because a set
        # nobody reads is the SNAG-CFG-001 shape and the exclusion now
        # comes from `_judged_titles` below.
        self._open_titles: set[str] = set()
        # Titles this run *wrote a row for*, kept apart from the snapshot
        # above rather than folded into it (SNAG-AGENT-009). Both sets
        # suppress a raise, and only the snapshot admits a refresh: a
        # held row that this run inserted seconds ago is one whose
        # message this run already chose, and refreshing it would make
        # the *last* of two same-titled judgements — two identically
        # named GPUs, the case that put the `add` here in the first
        # place — overwrite the first. Which of the two is current is
        # undefined, so the run must not answer it twice.
        self._written_titles: set[str] = set()
        # Titles this run judged **still true**, whether or not a row was
        # written for them — the set `_resolve_recovered` subtracts.
        # Deliberately not "the titles this run raised": see
        # `_raise_judged`, where the difference is the entire fix.
        self._judged_titles: set[str] = set()
        # Judgements that found a row already open. Counted so that a run
        # reporting zero raises can say which zero it means.
        self._suppressed: int = 0
        # Held rows whose text had moved and was rewritten. Counted
        # beside `_suppressed` rather than inside it: a suppressed
        # judgement that changed nothing and one that corrected a
        # standing sentence are different events, and `agent_runs.details`
        # is where the population of both was measured.
        self._refreshed: int = 0

    def forget_unknown(self) -> list[str]:
        """Drop per-service state for services no longer declared.

        Called after a configuration reload (:mod:`sysadmin.reload`), and
        only then — a scheduled run must never prune, because the three
        dicts below are exactly what a run is accumulating.

        **Streaks for services that survive the reload are kept, and that
        is the decision rather than the shortcut.** ``_degraded_counts``
        holds the three-consecutive-failures streak that gates an alert,
        and a reload is operator-initiated: clearing it would re-arm the
        streak at the moment an operator is most likely to be poking at a
        service that is already failing, delaying a genuine alert by up to
        three polls. The daemon restart this reload replaces clears them
        anyway (``_resolve_recovered`` documents that it does), so keeping
        them is a strict improvement rather than a new risk.

        What must go is the other direction: a name that is removed and
        later re-added would otherwise resume a streak measured against a
        different declaration. Returns the names dropped rather than a
        count — which service lost its state is what decides whether it
        matters.
        """
        known = {s.name for s in get_services().services}
        dropped = sorted(
            (set(self._degraded_counts) | set(self._failure_counts)
             | set(self._last_status)) - known
        )
        for name in dropped:
            self._degraded_counts.pop(name, None)
            self._failure_counts.pop(name, None)
            self._last_status.pop(name, None)
        return dropped

    async def _raise_judged(
        self,
        session,
        *,
        severity: str,
        title: str,
        message: str,
        details: dict[str, Any],
        dedup: bool = True,
    ) -> int:
        """Judge a fault still true, and write a row only if none is open.

        ``SNAG-AGENT-006``.  ``sysadmin-organiser-timer critical`` held
        **60** unresolved rows raised between 07:41 and 12:36 on
        2026-08-13 — one every 300 s, which is
        ``health_check_interval_seconds`` — for one dead timer.
        ``venture-chat unreachable`` reached 85 across 36 hours and
        ``redis unreachable`` 6,283 before anything could close it.  The
        tray never noticed, because it fingerprints on
        ``{severity}:{title}`` and sixty rows are one toast; what read
        sixty times high was ``GET /api/sysadmin/alerts`` and every count
        built on ``resolved = false``.

        **Judging and raising are two operations, and pulling them apart
        is the fix.**  Every call records the title in
        :attr:`_judged_titles` — the set :meth:`_resolve_recovered`
        subtracts — and only then asks whether a row is needed.  The snag
        was filed saying dedup and that sweep are mutually exclusive, and
        against the exclusion set as it then stood they were: it held the
        titles the run **raised**, so a family that writes nothing on its
        second run had its still-true row swept, re-raised on the third,
        swept on the fourth, each flip clearing the tray fingerprint and
        notifying again.  :mod:`sysadmin.estate.agent` had already shown
        the third option — an exclusion set of what the run **judged**.
        Dedup suppresses the raise, never the judgement, so a fault that
        persists is in the set on every run and is never swept, and a
        fault that clears leaves it exactly once and is resolved exactly
        once.  It is available here for the same reason it was available
        there: this agent owns every row the sweep can reach.

        ``dedup=False`` is for the one title in these two families that
        is an **event rather than a state** — ``% auto-restarted``.
        ``_failure_counts`` is reset to zero the moment ``restart_unit``
        returns, so that title fires once per restart *cycle*; a second
        restart three hours later is a second piece of news, and
        deduplicating it would suppress the row that carries it.  Same
        distinction :mod:`sysadmin.monitor.log_signature` draws between a
        log line and an incident.  It is still *judged*, so this run's
        sweep leaves it alone; when the service is next measured healthy
        it falls out of both this set and ``unhealthy`` and resolves with
        the rest of its family.

        Suppression is deliberately the **only** thing this does.  It is
        not folded into :meth:`raise_alert`, because five families —
        anomalies, stalls, agent failures, unit failures, collation —
        already own their own lifecycles, and silently changing all of
        them from one override is the "second owner of one lifecycle"
        defect that produced this method in the first place.

        **A suppressed raise is not a suppressed correction**
        (``SNAG-AGENT-009``).  The largest held population on this box is
        this method — **838** suppressed raises across 751 of 2,303 runs,
        against 131 for the estate judge and 0 for the port family — and
        every one of them left ``message`` and ``details`` as the first
        run wrote them.  The threshold family is the worst case by
        construction: ``High VRAM usage on …`` is stable while its whole
        message is the measurement, ``VRAM at 90.1% (threshold: 90%)``,
        so **42 of 42** polls inside a hold carried a different figure and
        19 of them read *below* the threshold the sentence was asserting.
        The row is therefore brought up to date here, by
        :meth:`~sysadmin.core.agent.BaseAgent.refresh_alert`, which owns
        the comparison and the write.

        Only a row that was open **before this run** is refreshed, which
        is why :attr:`_written_titles` exists as a second set rather than
        as more entries in :attr:`_open_titles` — see its comment.

        The row is fetched at the hold rather than carried in the
        snapshot, and that is ``SNAG-AGENT-005``'s rule rather than
        thrift: a snapshot widened to carry ``message`` and ``details``
        is bounded by *the table*, and this agent's own families reached
        51,924 open rows before ``SNAG-AGENT-004``; a read at the hold is
        bounded by *the judgements this run made*, which is at most a
        handful.  It costs one indexed lookup per held-and-checked title:
        measured against the live table at 665,937 rows, **84 buffers and
        0.098 ms**, on ``idx_alerts_active`` rather than
        ``idx_alerts_open_by_agent`` — with one open row on the box
        either partial index is free and the planner takes the older one,
        which is exactly what ``SNAG-AGENT-007`` recorded about its own
        pair.  The agent-scoped one is what bounds this read if the open
        set ever grows again, and it is reached through
        :meth:`_open_alert_criteria` rather than by a hand-written
        predicate, so it can be reached at all.

        The read happens inside the per-service savepoint on that path,
        which changes nothing:
        :meth:`~sysadmin.core.agent.BaseAgent.raise_alert` already
        flushes there, so this adds no earlier flush than the raise it
        replaces — ``SNAG-DB-001``'s one-savepoint-per-service isolation
        is untouched.

        Returns:
            1 if a row was written, 0 if the fault already had one open.
            A refresh returns 0 — it writes no row, and ``alerts_raised``
            counts rows.  ``details["standing"]["refreshed"]`` is where a
            run says it happened.
        """
        self._judged_titles.add(title)
        if dedup and (title in self._open_titles or title in self._written_titles):
            self._suppressed += 1
            logger.debug(
                "alert_suppressed_row_already_open",
                extra={"agent": self.name, "title": title},
            )
            if title in self._open_titles:
                await self._refresh_open(
                    session,
                    title=title,
                    message=message,
                    details=details,
                    severity=severity,
                )
            return 0
        await self.raise_alert(
            session,
            severity=severity,
            title=title,
            message=message,
            details=details,
        )
        # So that a second judgement of the same title inside one run —
        # two identically-named GPUs, say — dedups against the row this
        # call just wrote rather than against a snapshot taken before it.
        self._written_titles.add(title)
        return 1

    async def _refresh_open(
        self,
        session,
        *,
        title: str,
        message: str,
        details: dict[str, Any],
        severity: str | None = None,
    ) -> bool:
        """Rewrite the standing row for ``title`` if its text has moved.

        Scoped through :meth:`_open_alert_criteria`, so "open" is stated
        where the column and the partial indexes are and this method adds
        no second definition of it.

        **A missing row is not an error.**  The snapshot is taken at the
        top of the run and something may have resolved the row since —
        the lifespan closes ``sysadmin.service failed``, an operator may
        acknowledge and resolve one through the API — and a judgement
        that finds nothing to correct has simply nothing to correct.  It
        is still counted as suppressed, because the *raise* was
        suppressed by the snapshot either way; what the run reports is
        how many corrections it made, not how many it attempted.

        **The judged rung is handed on, and the family that made that
        population non-empty arrived on 2026-08-31** (``SNAG-ESTATE-010``,
        then ``SNAG-AGENT-011``).  Until then every family reaching this
        method paired a rung with a *title kind* —
        ``service_alert_title(name, "degraded")`` is ``warning`` and
        ``…(name, status)`` is ``critical``; a disk breach at the critical
        threshold and one at the warning threshold are two titles, not one
        row at two rungs — so a standing row and the judgement holding it
        could not disagree about severity, and
        :func:`~sysadmin.core.escalation.may_quieten_in_place` could only
        ever answer ``False`` from here.  Session 117 wired it regardless,
        on the grounds that the rung was already a parameter and the
        alternative was a caller that quietly stops honouring the base
        class's contract the day a family gains a second rung.

        **That day came, and the wiring is what made the fix a
        two-line change rather than a design.**
        :data:`ARBITRATED_STOP_SEVERITY` gives ``% unreachable`` a second
        rung under **one** title: ``venture-chat unreachable`` is
        ``critical`` on a poll where the estate could not be read and
        :data:`ARBITRATED_STOP_SEVERITY` on the next one, where it could.
        The title deliberately does not fork — it is the identity
        (Session 42), and forking it would take the row out of
        ``% unreachable``'s sweep — so the disagreement lands here, which
        is the one place equipped for it.  A prediction of an empty
        population is worth keeping in the record beside what refuted it:
        the claim was not *wrong when written*, it was one family from
        being wrong, and "empty by construction" is the phrase that made
        it sound otherwise.

        **The direction is one-way and the residue is filed rather than
        hidden.**  A quietening reaches the standing row; the reverse —
        an outage that began under a lease and outlives it, wanting
        ``critical`` on a row open at the floor — is refused by
        :func:`~sysadmin.core.escalation.may_quieten_in_place` and the row
        stays quiet.  That is ``SNAG-AGENT-012``, filed with its
        population measured at **zero** (181 of 181 rows in this family
        have resolved, the nightly ones at the drain's hold to the
        second) and with :func:`~sysadmin.core.escalation.step_for`'s
        resolve-and-re-raise named as its shape if it ever stops being
        zero.  A ladder tuned against zero observations is a guess with a
        number on it — the ports family's rule 6 — so what ships instead
        is a log line at ``warning``, loud enough to be stored, counted
        and carried into ``GET /api/logs/trends``, and quiet enough
        (``FAULT_SEVERITIES`` is ``error`` and ``critical``) to raise
        nothing: ``manual_run_failed``'s cancellation rung, for its
        reason.

        Note what would happen to a family whose rung merely *fell* a
        step: a disk at 91 % dropping to 85 % under one title would be
        refused, and rightly.  It is still breaching, and a fresh
        ``warning`` toast about it is a less urgent notification about a
        fault that has not improved —
        :func:`~sysadmin.core.escalation.step_for`'s own refusal, which
        rule 1 of that predicate keeps intact.  Only the **floor** is
        reachable in place, which is why the fix above quietens to it and
        not to ``warning``.
        """
        alert = (
            await session.execute(
                select(Alert).where(*self._open_alert_criteria(), Alert.title == title)
            )
        ).scalars().first()
        if alert is None:
            return False
        # SNAG-AGENT-012, said out loud rather than left to be inferred.
        # `may_quieten_in_place` refuses an upward move, so a fault that
        # began quiet and has since become genuinely urgent — an outage
        # that started under an estate lease and outlived it — keeps the
        # floor rung and stops interrupting. The row is still there and
        # still true; what is stale is how loudly it says so.
        #
        # `warning` is the rung, and it is chosen rather than defaulted:
        # `FAULT_SEVERITIES` is `error` and `critical`, so this line is
        # stored, counted and carried into `GET /api/logs/trends` while
        # raising no alert of its own. Announcing it as an alert would
        # give one fault two speakers, which is the defect this
        # repository has now found at six scales; saying nothing at all
        # is what made the founding entry invisible for a night at a
        # time.
        if severity is not None and severity != alert.severity:
            if not may_quieten_in_place(severity, alert.severity):
                logger.warning(
                    RUNG_LEFT_STALE_EVENT,
                    extra={
                        "agent": self.name,
                        "title": title,
                        "open_severity": alert.severity,
                        "judged_severity": severity,
                    },
                )
        if not self.refresh_alert(
            alert, message=message, details=details, severity=severity
        ):
            return False
        self._refreshed += 1
        return True

    async def _execute(self, session) -> AgentResult:
        """Run all health checks and record resource snapshot."""
        self._stall_counts = _NO_STALLS
        self._agent_failure_counts = _NO_AGENT_FAILURES
        self._collation_counts = _NO_COLLATION
        self._arbitration = None
        self._judged_titles = set()
        self._written_titles = set()
        self._suppressed = 0
        self._refreshed = 0
        config = get_config()
        agent_config = config.agents.sysadmin
        services = get_services().services
        alerts_raised = 0
        # Configured services this run did not measure as healthy. Their
        # open alerts are protected from the resolve below — see
        # _resolve_recovered.
        unhealthy: set[str] = set()
        # Services whose own savepoint rolled back. Named rather than
        # counted in agent_runs.details: which service could not be
        # written decides whether it matters, the lesson
        # `details['truncated_sources']` records on the log side.
        write_failures: list[str] = []

        # One snapshot of the open titles for the whole run, taken
        # before anything is raised — `_handle_status` and
        # `_check_thresholds` both dedup against it (SNAG-AGENT-006).
        # Read here rather than at the nine call sites for the reason
        # `_check_agent_health` reads its own tables once: separate
        # fetches milliseconds apart can disagree about the same row, and
        # a per-site query would also need a session, which
        # `_handle_status` is legitimately called without on the skipped
        # path.
        #
        # Titles, not rows (SNAG-AGENT-007). The projection differs from
        # the three row-reading callers below; the *predicate* does not —
        # `_open_alert_criteria` states it once and all four build on it.
        #
        # Deliberately *not* shared with `_check_agent_health` or
        # `_check_collation`, which take their own `_active_alerts`
        # snapshots later in the run. Those two run ladders off the Alert
        # rows themselves — id, severity, created_at, details — and must
        # see what this run has already written; titles taken before the
        # service loop are neither.
        self._open_titles = await self._open_alert_titles(session)

        # --- Service health checks ---
        # One connection pool per run, bound to this run's event loop and
        # closed when the block exits (SNAG-AGENT-003).
        async with self._http.scoped():
            for svc in services:
                status, response_time_ms, details = await self._check_service(svc)
                if status not in ("ok", SKIPPED):
                    unhealthy.add(svc.name)

                # SNAG-AGENT-011. Ask the estate whether this outage was
                # its doing — at most once per run, and only once
                # something is down hard enough for the answer to change
                # a rung.
                #
                # **Here rather than in `_handle_status`, and the reason
                # is the savepoint three lines down.** This host sets
                # `idle_in_transaction_session_timeout=1min`; two HTTP
                # hops at `HTTP_CHECK_TIMEOUT_S` each is up to 20 s, and
                # spending it inside `begin_nested()` is SNAG-AGENT-003's
                # defect rebuilt in the fix for something else. The
                # transaction opens after the answer is already in hand.
                #
                # **Not gated on `svc.systemd_unit`**, though only a unit
                # can match. The read is memoised per run, so gating buys
                # nothing the moment any *other* service has one — and it
                # would leave a unitless service's row reading `unread`
                # when the truth is "nobody asked about it", which is the
                # distinction `_NO_ARBITRATION` exists to keep.
                if status in ("critical", "unreachable"):
                    await self._ensure_arbitration()

                # One savepoint per service — SNAG-DB-001's second gap.
                # These writes used to accumulate in the run's single
                # transaction and land in one commit, so the rejected
                # `venture-chat-large` row aborted the whole thing and
                # took the other eighteen services' checks with it. Zero
                # rows reached `service_health` for 39 hours.
                #
                # The savepoint is load-bearing *because leaving the
                # block flushes*. `session.add` never talks to the
                # database, so a CHECK violation surfaces at flush time
                # — which, before this, was the single commit at the end
                # of the run, by which point the offending row could not
                # be told apart from the eighteen good ones.
                try:
                    async with session.begin_nested():
                        session.add(ServiceHealth(
                            service_name=svc.name,
                            status=status,
                            response_time_ms=response_time_ms,
                            details=details,
                        ))
                        # Inside the savepoint deliberately: a service's
                        # health row and the alert raised about it are
                        # one statement about that service, and half of
                        # it committed is worse than neither.
                        svc_alerts = await self._handle_status(
                            session, svc, status, details
                        )
                except SQLAlchemyError as exc:
                    await self._isolate_write_failure(session, svc, status, exc)
                    # Nothing was measured *and recorded*, so this
                    # service's open alerts must survive the run —
                    # `_resolve_recovered` skips whatever is in
                    # `unhealthy`, and resolving on an unknown state
                    # announces a recovery nobody observed.
                    unhealthy.add(svc.name)
                    write_failures.append(svc.name)
                    continue

                alerts_raised += svc_alerts

                # Push a change event when a service flips state. After
                # the savepoint, not before: an event announcing a
                # transition whose row rolled back is a state change the
                # database never saw, and `_last_status` would suppress
                # the real one on the next run.
                if self._last_status.get(svc.name) != status:
                    self._last_status[svc.name] = status
                    self._queue_event(
                        "service.status",
                        {"service": svc.name, "status": status},
                    )

        # --- Resource snapshot ---
        snapshot = await self._take_resource_snapshot(config)

        # History is read BEFORE the new snapshot joins the session, so the
        # current reading is not part of its own baseline.
        history = await self._load_metric_history(session, agent_config.anomaly)

        session.add(snapshot)

        # Check resource thresholds
        alerts_raised += await self._check_thresholds(
            session, snapshot, agent_config.thresholds
        )

        # Statistical anomalies (skips resources that already alerted above)
        alerts_raised += await self._check_anomalies(
            session, snapshot, history, agent_config.anomaly
        )

        # Self-monitoring — has another agent silently stopped running?
        alerts_raised += await self._check_agent_health(session, config)

        # Text ordering the databases were built against, versus the one
        # the OS provides now (SNAG-DB-002).
        alerts_raised += await self._check_collation(session, agent_config)

        # Everything this run measured and did not alert on has recovered.
        alerts_resolved = await self._resolve_recovered(session, unhealthy)

        checked = sum(1 for svc in services if not check_plan(svc).checks_nothing)
        return AgentResult(
            findings_count=len(services),
            alerts_raised=alerts_raised,
            details={
                "services_checked": checked,
                "services_declared": len(services),
                "alerts_resolved": alerts_resolved,
                # Empty list, never an absent key: `{}` in the details
                # blob reads as "the isolation did not run", which is
                # the confusion this whole area exists to remove.
                "write_failures": write_failures,
                # Recorded so a run that escalated an existing stall is
                # distinguishable from one that found a new one — the two
                # sum into `alerts_raised` and mean different things.
                "stalls": self._stall_counts,
                # The failure family's counts, reported beside the stall
                # family's and never summed with them: "has not run" and
                # "ran and failed" are different states, which is the
                # whole reason they are separate alert families.
                "agent_failures": self._agent_failure_counts,
                # Databases whose recorded collation version no longer
                # matches the OS. Reported beside the two ladders and
                # never summed with them: this family raises once per
                # open row, so `raised` is new faults rather than
                # current ones — `mismatched` is the standing count.
                "collation": self._collation_counts,
                # The two deduplicating families' standing picture.
                # `alerts_raised` alone cannot tell "nothing is wrong"
                # from "sixty things are wrong and every one of them is
                # already on the board" — zero is the correct answer to
                # both, and the second is exactly what a broken dedup
                # also produces. `judged` counts the distinct faults this
                # run measured as still true; `suppressed` how many of
                # them already had a row.
                "standing": {
                    "judged": len(self._judged_titles),
                    "suppressed": self._suppressed,
                    # How many of the suppressed judgements found a
                    # standing row whose sentence had gone stale and
                    # rewrote it (SNAG-AGENT-009). Reported beside
                    # `suppressed` and never summed into `alerts_raised`:
                    # no row was written, and a count of rows that
                    # included updates would stop meaning what four other
                    # families read it as.
                    "refreshed": self._refreshed,
                },
            },
        )

    # --- Service checks ---

    async def _isolate_write_failure(
        self, session, svc: ServiceEntry, status: str, exc: Exception
    ) -> None:
        """Turn one service's failed write into one bad tile, not a blackout.

        The savepoint has already rolled back by the time this is
        called, so the session is usable again and a *second* savepoint
        can record that the check happened and could not be stored.
        ``status="error"`` because that is what the column's own
        vocabulary calls "nothing is known about this service", and
        because it is the value most likely to be legal: the failure
        being isolated is, in the case this exists for, a CHECK
        violation on this very column.

        Writing something matters more than it looks.  SNAG-DB-001's
        39-hour hole was invisible precisely because the absence of a
        row is indistinguishable from a service nobody configured — the
        same confusion ``_record_outcome`` was fixed for in Session 41.
        A row saying "error" makes the tray show a broken tile, which is
        a question someone asks.

        **What a savepoint does not undo.**  It rolls back SQL and
        nothing else.  ``_handle_status`` may have restarted a unit
        through ``systemctl`` and will have bumped ``_degraded_counts``
        or ``_failure_counts``, both of which live in memory; those
        stand.  So does the entry ``_raise_judged`` made in
        ``_judged_titles``, which is the harmless direction — it
        protects this service's open rows from the sweep for one more
        run, and ``unhealthy`` protects them anyway.  The streak
        counters being one ahead can fire the next alert one check
        early, which is the mild direction, and the alternative —
        snapshotting them per service — buys accuracy in a path that
        only runs when the database is already rejecting writes.

        Failure to write even this is logged and swallowed: raising here
        would abort the run and reinstate exactly the behaviour being
        removed.
        """
        logger.error(
            "service_write_isolated",
            extra={
                "service": svc.name,
                "attempted_status": status,
                "error": str(exc),
            },
        )
        try:
            async with session.begin_nested():
                session.add(ServiceHealth(
                    service_name=svc.name,
                    status="error",
                    response_time_ms=None,
                    details={
                        "source": "write_isolation",
                        "attempted_status": status,
                        "error": _truncate_error(exc),
                    },
                ))
        except SQLAlchemyError:
            logger.exception(
                "service_write_isolation_failed",
                extra={"service": svc.name},
            )


    async def _check_service(
        self, svc: ServiceEntry
    ) -> tuple[str, int | None, dict]:
        """Check one service, as its ``kind`` in services.yaml calls for.

        The plan comes from :func:`~sysadmin.monitor.services.check_plan`
        rather than from a chain of conditionals here, so "a oneshot is
        watched through its timer" is a property of the declaration and
        not of this function.
        """
        plan = check_plan(svc)
        if plan.checks_nothing:
            return SKIPPED, None, self._skip_details(svc)

        try:
            if plan.connect:
                return await self._check_tcp(svc)
            if plan.poll_url:
                return await self._check_http_and_unit(svc, plan)
            return await self._check_systemd(svc, inspect_timer=plan.inspect_timer)
        except Exception as e:
            logger.error(
                "service_check_error",
                extra={"service": svc.name, "error": str(e)},
            )
            return "unreachable", None, {"error": str(e)}

    @staticmethod
    def _skip_details(svc: ServiceEntry) -> dict:
        """Why a service was not checked, recorded with the skip.

        A ``skipped`` row with no explanation is only marginally better
        than no row, which is the option this replaced.
        """
        details: dict = {"kind": svc.kind, "monitored": svc.monitor}
        details["reason"] = svc.reason or (
            f"kind {svc.kind}: not expected to be running between invocations"
        )
        if svc.unit:
            details["unit"] = svc.unit
        return details

    async def _check_http_and_unit(
        self, svc: ServiceEntry, plan
    ) -> tuple[str, int | None, dict]:
        """Poll the URL, and assert the unit is active when one is named.

        A 200 from a URL says something answered, not that the unit this
        estate believes serves it is the thing that answered. Where a unit
        is declared, both must hold.

        The unit check **fails open**: a systemd query that cannot run
        yields the URL's own verdict rather than a failure. Treating an
        unreadable bus as a down service is precisely SNAG-SYSD-001, which
        flagged a live user timer as down for a week.
        """
        status, elapsed_ms, details = await self._check_http(svc)
        unit = svc.unit
        if not plan.assert_active or unit is None or status != "ok":
            return status, elapsed_ms, details

        try:
            unit_info = await get_unit_status(unit, user=svc.user)
        except SystemdQueryError as e:
            logger.warning(
                "unit_assertion_unavailable",
                extra={"service": svc.name, "unit": unit, "error": str(e)},
            )
            return status, elapsed_ms, {**details, "unit_check": "unavailable"}

        if unit_info.get("is_active"):
            return status, elapsed_ms, details
        if unit_info.get("ActiveState") == "activating":
            return "degraded", elapsed_ms, {
                **details, "reason": "url ok, unit still activating", **unit_info
            }
        return "degraded", elapsed_ms, {
            **details,
            "reason": f"url ok but {unit} is not active",
            **unit_info,
        }

    async def _check_http(
        self, svc: ServiceEntry
    ) -> tuple[str, int | None, dict]:
        """HTTP health check."""
        if not svc.url:
            return "error", None, {"error": "no url configured for http check"}

        start = time.monotonic()
        try:
            async with self._http.borrow() as client:
                resp = await client.get(svc.url)
            elapsed_ms = int((time.monotonic() - start) * 1000)

            if resp.status_code == 200:
                # Slow response = degraded
                if elapsed_ms > 5000:
                    return "degraded", elapsed_ms, {"reason": "slow response"}
                return "ok", elapsed_ms, {}
            elif resp.status_code < 500:
                return "degraded", elapsed_ms, {"status_code": resp.status_code}
            else:
                return "critical", elapsed_ms, {"status_code": resp.status_code}
        except httpx.TimeoutException:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "unreachable", elapsed_ms, {"error": "timeout"}
        except httpx.ConnectError:
            return "unreachable", None, {"error": "connection refused"}

    async def _check_tcp(
        self, svc: ServiceEntry
    ) -> tuple[str, int | None, dict]:
        """TCP connection check."""
        start = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(svc.host, svc.port),
                timeout=5.0,
            )
            elapsed_ms = int((time.monotonic() - start) * 1000)
            writer.close()
            await writer.wait_closed()
            return "ok", elapsed_ms, {}
        except TimeoutError:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return "unreachable", elapsed_ms, {"error": "timeout"}
        except (ConnectionRefusedError, OSError) as e:
            return "unreachable", None, {"error": str(e)}

    async def _triggered_status(
        self, timer_props: dict, user: bool
    ) -> tuple[dict | None, str | None]:
        """The state of the unit a timer starts, or why it is unknown.

        Returns ``(props, None)`` or ``(None, reason)`` — never a partial
        answer, because a caller holding half of one cannot tell it from
        a whole one.  Every way of not-knowing is a distinct ``reason``
        rather than a bare ``None``, since "the timer names no unit" and
        "the unit would not answer" have different remedies.

        The unit comes from the timer's ``Unit=`` property.  Deriving it
        as ``name.removesuffix('.timer') + '.service'`` is a second
        statement of a fact systemd publishes, and systemd does not
        require the two to correspond.
        """
        unit = (timer_props.get("Unit") or "").strip()
        if not unit:
            return None, "the timer published no Unit= property"
        try:
            triggered = await get_unit_status(unit, user=user)
        except SystemdQueryError as e:
            return None, f"could not query {unit}: {e}"
        if not triggered.get("Result"):
            return None, f"{unit} reported no Result"
        return triggered, None

    async def _check_systemd(
        self, svc: ServiceEntry, inspect_timer: bool = False
    ) -> tuple[str, int | None, dict]:
        """Systemd unit status check.

        ``inspect_timer`` reads the unit the timer *starts* as well as the
        timer, and is the whole of what makes a ``kind: timer`` check
        answer the question it is asked.

        **An armed timer is ``active (waiting)`` whether or not its last
        run worked, and the timer's own properties do not say which.**
        That sentence used to end "— the properties say which", which was
        false for the life of the check: ``Result`` on a ``.timer`` reports
        whether the *timer unit* started.  Measured on this box, it is
        ``success`` on ten of ten declared timers while
        ``alfred-career-mail.service`` had failed on twelve consecutive
        mornings, so the check wrote 3,988 unbroken ``ok`` rows across a
        twenty-day outage and raised nothing (``SNAG-SYSD-005``; Alfred's
        SNAG-50 is the fault it could not see).

        The discriminating fact is the triggered unit's ``Result``, and
        ``Unit=`` is asked of systemd rather than derived by rewriting the
        suffix — see :func:`sysadmin.monitor.systemd.get_unit_status`.
        """
        if not svc.systemd_unit:
            return "error", None, {"error": "no systemd_unit configured for systemd check"}

        start = time.monotonic()
        try:
            status_info = await get_unit_status(svc.systemd_unit, user=svc.user)

            triggered_error: str | None = None
            if inspect_timer:
                triggered, triggered_error = await self._triggered_status(
                    status_info, user=svc.user
                )
                status_info = {
                    **status_info,
                    **_timer_facts(status_info, triggered),
                }
                if triggered_error is not None:
                    status_info["triggered_error"] = triggered_error

            elapsed_ms = int((time.monotonic() - start) * 1000)

            if not status_info.get("is_active"):
                if status_info.get("ActiveState") == "activating":
                    return "degraded", elapsed_ms, status_info
                return "critical", elapsed_ms, status_info

            # The timer is armed, which settles the *schedule* and says
            # nothing about the job.  Only a timer reaches the rest of
            # this: `inspect_timer` is set by `check_plan` for `kind:
            # timer` alone.
            if inspect_timer:
                if triggered_error is not None:
                    # The triggered unit's state is *unknown*, which is
                    # neither a success nor a failure — `error` raises no
                    # alert against the service and is excluded from the
                    # reliability rates, exactly as SNAG-SYSD-001's fix
                    # decided for an unqueryable unit.  Reporting `ok`
                    # here would rebuild this check's founding defect one
                    # level down.
                    logger.warning(
                        "timer_triggered_unit_unreadable",
                        extra={
                            "service": svc.name,
                            "timer": svc.systemd_unit,
                            "error": triggered_error,
                        },
                    )
                    return "error", elapsed_ms, status_info
                if status_info.get("last_result") != "success":
                    return "critical", elapsed_ms, status_info

            return "ok", elapsed_ms, status_info
        except SystemdQueryError as e:
            # systemctl could not be queried, so the unit's state is
            # *unknown* — reporting "critical" here is how a live user
            # timer got flagged as down (SNAG-SYSD-001). "error" says the
            # check failed and, unlike critical/unreachable, raises no
            # alert against the service itself.
            logger.warning(
                "systemd_check_unavailable",
                extra={
                    "service": svc.name,
                    "unit": svc.systemd_unit,
                    "error": str(e),
                },
            )
            return "error", None, {
                "unit": svc.systemd_unit,
                "error": str(e),
                "query_failed": True,
            }
        except Exception as e:
            return "unreachable", None, {"error": str(e)}

    # --- Alerting logic ---

    async def _ensure_arbitration(self) -> None:
        """Read the estate's active lease once per run, failing open.

        ``SNAG-AGENT-011``.  The question is *"did somebody stop this on
        purpose"*, and the estate publishes the answer: a granted
        ``gpu_leases`` row carries ``stopped_units``, the arbiter's own
        record of which units it stopped to free the card.

        **Once per run, not once per raise, and the snag's cost figure
        was wrong.**  It priced the second call at *"once per incident,
        not once per poll"* on the strength of the family having raised
        23 rows in 17 days.  Those 23 are rows **after** dedup:
        :meth:`_raise_judged` is entered on every poll for as long as the
        fault stands and suppresses the *row*, so a read wired at the
        raise would fire every 300 s for six hours a night — 72 pairs of
        calls per nightly hold, not one.  Memoising on the run makes it
        two calls per 300 s whatever is down, and the memo is reset in
        :meth:`_execute` rather than being long-lived, because a lease
        that ended between runs must not be believed.

        **Once per poll is nevertheless the right cadence, which is the
        half that is easy to miss.**  A row raised ``critical`` because
        8400 happened to be unreadable on the first poll of an outage
        would otherwise stay ``critical`` all night; consulting on every
        run lets
        :func:`~sysadmin.core.escalation.may_quieten_in_place` correct it
        on the next one.  So the memo bounds the *cost* and must not
        bound the *consultation*.

        Nothing raises out of here and no failure is recorded as an
        alert: an unreadable estate is somebody else's outage, already
        owned by ``estate-manager-api``'s own ``% unreachable`` row, and
        a second owner of that lifecycle is the defect this repository
        has found at six scales.  It costs a reading of
        :data:`~sysadmin.estate.client.ARBITRATION_UNREAD` and the rung
        stays where it was.

        The base URL comes from the estate judge's config leaf, which is
        the one statement of 8400's address in this repository and is
        already pinned against ``services.yaml`` by
        ``tests/test_estate_judge_wiring.py``.  Reading a *leaf* the
        judge also reads is not reading the judge — no import of
        :mod:`sysadmin.estate.judgements` happens here or anywhere in
        this module.
        """
        if self._arbitration is not None:
            return
        base_url = get_config().agents.estate_judge.base_url
        async with self._http.borrow() as http:
            self._arbitration = await estate_client.read_arbitrated_stops(
                http, base_url
            )

    async def _handle_status(
        self, session, svc: ServiceEntry, status: str, details: dict
    ) -> int:
        """Handle status transitions, alerting, and auto-restart.

        **Every side effect here happens whether or not a row is
        written.**  The streak counters move and ``restart_unit`` runs
        before :meth:`_raise_judged` decides whether the fault already
        has an open row, because suppressing the *raise* must never
        suppress the *check*: a service whose alert is already open
        still has to be counted towards its next restart, and a restart
        that did not happen because the alert was old is a service left
        down.

        Returns:
            Rows written — 0 when the fault is real and already on the
            board.  ``details["standing"]`` in the run record reports
            what was judged beside what was raised, so the two zeroes
            are distinguishable.
        """
        service_name = svc.name

        if status == SKIPPED:
            # services.yaml says not to check this one.  Nothing was
            # measured, so there is nothing to alert on and nothing to
            # count — the same reasoning as "error" below, arrived at by
            # decision rather than by failure.
            return 0

        if status == "error":
            # The *check* failed (misconfigured, or systemctl could not be
            # queried), so nothing is known about the service.  Raise no
            # alert against it and leave the streak counters untouched —
            # an unmeasurable check is neither a success nor a failure.
            return 0

        if status == "ok":
            self._degraded_counts[service_name] = 0
            self._failure_counts[service_name] = 0
            # No resolve here. It used to call
            # `resolve_alerts(session, service_name)` — a substring
            # `ilike`, so `venture-chat` recovering also closed
            # `venture-chat-large`'s alerts — and, being inside the loop
            # over *configured* services, it could only ever observe a
            # service that was still being checked. `_resolve_recovered`
            # at the end of the run asks the inverse question instead.
            return 0

        if status == "degraded":
            self._failure_counts[service_name] = 0
            self._degraded_counts[service_name] = (
                self._degraded_counts.get(service_name, 0) + 1
            )
            if self._degraded_counts[service_name] >= 3:
                return await self._raise_judged(
                    session,
                    severity="warning",
                    title=service_alert_title(service_name, "degraded"),
                    message=f"{service_name} has been degraded for 3 consecutive checks",
                    details={**details, "service_name": service_name},
                )
            return 0

        if status == "warning":
            self._degraded_counts[service_name] = 0
            self._failure_counts[service_name] = 0
            return await self._raise_judged(
                session,
                severity="warning",
                title=service_alert_title(service_name, "warning"),
                message=f"{service_name} is in warning state",
                details={**details, "service_name": service_name},
            )

        if status in ("critical", "unreachable"):
            self._degraded_counts[service_name] = 0

            # Track consecutive failures for auto-restart
            self._failure_counts[service_name] = (
                self._failure_counts.get(service_name, 0) + 1
            )

            # Auto-restart if enabled and threshold met
            if (
                svc.auto_restart
                and svc.controllable
                and svc.systemd_unit
                and self._failure_counts[service_name] >= svc.auto_restart_after_checks
            ):
                logger.info(
                    "auto_restart triggered for %s after %d consecutive failures",
                    service_name,
                    self._failure_counts[service_name],
                )
                success, msg = await restart_unit(svc.systemd_unit, user=svc.user)
                # Reset counter to avoid restart loop
                self._failure_counts[service_name] = 0

                return await self._raise_judged(
                    session,
                    severity="warning",
                    title=service_alert_title(service_name, "auto-restarted"),
                    message=(
                        f"{service_name} was automatically restarted after "
                        f"{svc.auto_restart_after_checks} consecutive failures"
                        f" — {'succeeded' if success else f'failed: {msg}'}"
                    ),
                    details={**details, "service_name": service_name, "auto_restart": True},
                    # The one title in this family that is an event
                    # rather than a state. `_failure_counts` was reset
                    # three lines up, so the next row here means a
                    # *second* restart — news, not a repeat — and
                    # deduplicating it would swallow exactly that.
                    dedup=False,
                )

            # SNAG-AGENT-011. The row is correct and the rung is not.
            # `_check_service` measured this service down and it *is*
            # down; what `critical` asserts on top of that is "this is
            # costing something now", which a declared swap with a hold
            # deadline is not.
            #
            # Quietened, never suppressed — `known_noise` rule 2. The row
            # is still written, still deduplicated, still counted, still
            # served by `GET /api/sysadmin/alerts`, and still resolved by
            # `_resolve_recovered` on the first healthy poll; the title
            # does not move, so it stays inside `% unreachable` and no
            # sweep pattern changes. What it stops doing is holding a
            # non-transient toast on screen all night.
            #
            # Muting the service was refused and is the obvious cheap
            # fix: `mute_services` would delete the row for a genuine
            # 14:00 outage as readily as for the arbitrated 00:00 one,
            # which is the pile-up-wearing-a-declaration-as-an-excuse
            # shape `_resolve_recovered` rule 4 already refuses.
            stops = self._arbitration or _NO_ARBITRATION
            arbitrated = stops.stopped(svc.systemd_unit)
            severity = ARBITRATED_STOP_SEVERITY if arbitrated else "critical"
            message = f"{service_name} is {status}"
            if arbitrated:
                message += (
                    " — stopped by the estate's arbiter under lease "
                    f"{stops.lease_id}"
                )
                if stops.profile:
                    message += f" ({stops.profile})"
            return await self._raise_judged(
                session,
                severity=severity,
                title=service_alert_title(service_name, status),
                message=message,
                details={
                    **details,
                    "service_name": service_name,
                    # Recorded on **every** row of this family, not only
                    # the quietened one — Session 128's rule for
                    # `details['attribution']`, and for its reason: a key
                    # present only sometimes collapses "we asked and the
                    # answer was no" into "nobody asked", which is the
                    # distinction this whole block turns on. The *value*
                    # carries the news.
                    "arbitration": {
                        "reading": stops.reading,
                        "unit": svc.systemd_unit,
                        "stopped_by_estate": arbitrated,
                        "lease_id": stops.lease_id,
                        "profile": stops.profile,
                    },
                },
            )

        return 0

    # --- Alert recovery ---

    async def _resolve_recovered(self, session, unhealthy: set[str]) -> int:
        """Resolve every owned alert this run did **not** raise.

        The service-side twin of
        :meth:`sysadmin.projects.agent.ProjectOrganiserAgent._resolve_recovered`,
        and the same defect at sixteen times the scale (SNAG-AGENT-004).
        Recovery used to be observed one service at a time, inside the
        loop over the *configured* services — so a service removed from
        configuration was never checked again, could never be seen to
        recover, and its alerts stayed open for ever.  ``run_retention``
        purges ``resolved = TRUE`` rows only, deliberately, so nothing
        else was ever going to clear them.

        Live on 2026-08-12, before this ran: **27,827** unresolved rows
        for five services that no longer exist in either config file
        (``personal-assistant`` 9,748, ``personal-assistant-frontend``
        9,748, ``redis`` 6,283, ``ollama`` 1,824, ``nuxt-frontend`` 224),
        and **23,501** more for resource thresholds that had no resolve
        path at any point in this application's life.

        Asking the inverse question closes retirement, rename, recovery
        and threshold-cleared in one statement, and cannot drift from the
        raise path: the population comes from
        :data:`RESOLVABLE_TITLE_PATTERNS` and the exclusions from
        :attr:`_judged_titles`, which :meth:`_raise_judged` fills.

        **The exclusion is what the run judged, not what it raised, and
        that is the whole reason these families can deduplicate**
        (SNAG-AGENT-006).  Against a raised set, a family that writes no
        row on its second run has its still-true row swept here,
        re-raised on the third run, swept on the fourth — a flip-flop
        that clears the tray's ``{severity}:{title}`` fingerprint every
        turn, so one fault notifies on every poll.  Against a judged set
        there is nothing to flip: the row is protected for as long as
        the fault is measured, and becomes reachable on the first run it
        is not.  :mod:`sysadmin.estate.agent` is where that pairing was
        first shown to work, and it works here for the same reason —
        every row this statement can reach belongs to this agent.

        **The two halves still take different exclusions, and the
        difference is not cosmetic.** A resource threshold either
        breached this run or did not, so the judged set decides it
        exactly.  A service's alert is governed by a *streak* — three
        consecutive degraded checks — held in memory, and
        ``_degraded_counts`` resets when the daemon restarts.  Judging
        alone would therefore close a genuinely-degraded service's alert
        on the first run after every restart and re-raise it two checks
        later: a spurious recovery, announced to the tray, for a fault
        that never went away.  So a service's titles are resolved only
        when this run measured it **healthy** — ``unhealthy`` carries
        everything else, including ``error``, where the check itself
        failed and the state is genuinely unknown.

        ``skipped`` counts as healthy for this purpose, and deliberately.
        It means ``services.yaml`` declares ``monitor: false``: the estate
        has said it does not want to know, and an open critical that
        nothing will ever look at again is the pile-up wearing a
        declaration as an excuse.

        A **deconfigured** service is in neither set — it is not in the
        loop at all — so its rows fall through to the resolve.  That is
        the fix, and it is why the population must be pattern-based.

        Titles are excluded by exact match, never by "created before
        now": the rows raised moments ago are in this same transaction
        and a timestamp comparison races the clock that stamped them.

        Returns:
            Number of alerts resolved.
        """
        from sqlalchemy import or_

        protected = self._judged_titles | {
            service_alert_title(name, kind)
            for name in unhealthy
            for kind in SERVICE_ALERT_KINDS
        }

        conditions = [
            *self._open_alert_criteria(),
            or_(*[Alert.title.like(p) for p in RESOLVABLE_TITLE_PATTERNS]),
        ]
        if protected:
            conditions.append(Alert.title.notin_(sorted(protected)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "service_alerts_resolved",
                extra={"agent": self.name, "count": resolved},
            )
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": "recovered", "count": resolved},
            )
        return resolved

    # --- Resource monitoring ---

    @staticmethod
    def _collect_resource_metrics() -> tuple[float, Any, Any, tuple, dict]:
        """Blocking psutil metric collection — run via asyncio.to_thread.

        ``cpu_percent(interval=1)`` sleeps for a full second, so this must
        never run directly on an event loop (SNAG-API-003).
        """
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        load = psutil.getloadavg()

        # Disk usage per mount point
        disk_usage = {}
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                disk_usage[part.mountpoint] = {
                    "total_gb": round(usage.total / (1024**3), 1),
                    "used_gb": round(usage.used / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent,
                }
            except (PermissionError, OSError):
                continue

        return cpu, mem, swap, load, disk_usage

    async def _take_resource_snapshot(self, config: AppConfig) -> ResourceSnapshot:
        """Collect current system resource metrics including GPU."""
        cpu, mem, swap, load, disk_usage = await asyncio.to_thread(
            self._collect_resource_metrics
        )

        # GPU usage (AMD via rocm-smi / sysfs)
        try:
            gpu_usage = await get_gpu_usage()
        except Exception:
            logger.debug("gpu monitoring failed", exc_info=True)
            gpu_usage = {}

        return ResourceSnapshot(
            cpu_percent=cpu,
            ram_used_mb=int(mem.used / (1024**2)),
            ram_total_mb=int(mem.total / (1024**2)),
            ram_percent=mem.percent,
            swap_used_mb=int(swap.used / (1024**2)),
            swap_total_mb=int(swap.total / (1024**2)),
            disk_usage=disk_usage,
            gpu_usage=gpu_usage,
            load_avg_1m=load[0],
            load_avg_5m=load[1],
            load_avg_15m=load[2],
        )

    async def _check_thresholds(
        self, session, snapshot: ResourceSnapshot, thresholds
    ) -> int:
        """Check resource thresholds and raise alerts. Returns rows written.

        Also records the resource keys that **breached** in
        ``_threshold_keys`` so :meth:`_check_anomalies` can suppress
        duplicates — breached, not raised, and the distinction became
        load-bearing with SNAG-AGENT-006's dedup.  A disk that has been
        over the critical mark for a week writes no new row, and tying
        the key to the row would then let an anomaly alert fire for
        exactly the resource whose threshold alert is sitting open: one
        family's suppression manufacturing a duplicate in the other.
        Every ``add`` therefore sits *above* its ``_raise_judged`` call,
        where skipping it takes an edit rather than an oversight.
        """
        alerts = 0
        self._threshold_keys = set()

        # RAM check
        if snapshot.ram_percent and float(snapshot.ram_percent) >= thresholds.ram_warning_percent:
            self._threshold_keys.add("ram")
            alerts += await self._raise_judged(
                session,
                severity="warning",
                title="High RAM usage",
                message=(
                    f"RAM at {snapshot.ram_percent}% "
                    f"(threshold: {thresholds.ram_warning_percent}%)"
                ),
                details={
                    "ram_percent": float(snapshot.ram_percent),
                    "resource": "ram",
                    "threshold": True,
                },
            )

        # GPU checks
        for card_id, gpu in (snapshot.gpu_usage or {}).items():
            gpu_name = gpu.get("name", card_id)
            temp = gpu.get("temp_c")
            if temp is not None and temp >= thresholds.gpu_temp_warning_c:
                alerts += await self._raise_judged(
                    session,
                    severity="warning",
                    title=f"High GPU temperature on {gpu_name}",
                    message=f"GPU temp at {temp}°C (threshold: {thresholds.gpu_temp_warning_c}°C)",
                    details={"card": card_id, "temp_c": temp},
                )

            vram_pct = gpu.get("vram_percent")
            if vram_pct is not None and vram_pct >= thresholds.gpu_vram_warning_percent:
                alerts += await self._raise_judged(
                    session,
                    severity="warning",
                    title=f"High VRAM usage on {gpu_name}",
                    message=(
                        f"VRAM at {vram_pct}% "
                        f"(threshold: {thresholds.gpu_vram_warning_percent}%)"
                    ),
                    details={"card": card_id, "vram_percent": vram_pct},
                )

        # Disk check
        for mount, usage in (snapshot.disk_usage or {}).items():
            pct = usage.get("percent", 0)
            disk_key = f"{DISK_KEY_PREFIX}{mount}"
            if pct >= thresholds.disk_critical_percent:
                self._threshold_keys.add(disk_key)
                alerts += await self._raise_judged(
                    session,
                    severity="critical",
                    title=disk_alert_title(mount, critical=True),
                    message=(
                        f"Disk at {pct}% on {mount} "
                        f"(threshold: {thresholds.disk_critical_percent}%)"
                    ),
                    details={
                        "mount": mount,
                        "percent": pct,
                        "resource": disk_key,
                        "threshold": True,
                    },
                )
            elif pct >= thresholds.disk_warning_percent:
                self._threshold_keys.add(disk_key)
                alerts += await self._raise_judged(
                    session,
                    severity="warning",
                    title=disk_alert_title(mount, critical=False),
                    message=(
                        f"Disk at {pct}% on {mount} "
                        f"(threshold: {thresholds.disk_warning_percent}%)"
                    ),
                    details={
                        "mount": mount,
                        "percent": pct,
                        "resource": disk_key,
                        "threshold": True,
                    },
                )

        return alerts

    # --- Anomaly detection ---

    @staticmethod
    def _snapshot_metrics(snapshot: ResourceSnapshot) -> dict[str, float]:
        """Current values keyed the same way as the history series."""
        metrics: dict[str, float] = {}
        if snapshot.cpu_percent is not None:
            metrics["cpu"] = float(snapshot.cpu_percent)
        if snapshot.ram_percent is not None:
            metrics["ram"] = float(snapshot.ram_percent)
        for mount, usage in (snapshot.disk_usage or {}).items():
            percent = usage.get("percent")
            if percent is not None:
                metrics[f"{DISK_KEY_PREFIX}{mount}"] = float(percent)
        return metrics

    async def _load_metric_history(
        self, session, config: AnomalyConfig
    ) -> dict[str, list[float]]:
        """Read the recent snapshot window as per-metric series."""
        if not config.enabled:
            return {}

        since = datetime.now(UTC) - timedelta(days=config.window_days)
        result = await session.execute(
            select(ResourceSnapshot).where(ResourceSnapshot.recorded_at >= since)
        )

        history: dict[str, list[float]] = {}
        for row in result.scalars().all():
            for key, value in self._snapshot_metrics(row).items():
                history.setdefault(key, []).append(value)
        return history

    def _open_alert_criteria(self) -> tuple[Any, ...]:
        """This agent's unresolved rows — **the** statement of that set.

        ``SNAG-AGENT-007`` is filed against the four reads below, and its
        own body names the tension the fix turns on: the dedup caller
        needs titles alone, so a ``select(Alert.title)`` projection would
        stop it materialising whole ORM rows, *at the cost of* a second
        definition of "this agent's open rows" sitting beside
        :meth:`_active_alerts` and free to drift from it.

        The way out is that those are not the same kind of thing.  A
        **projection** is what a caller wants back; a **predicate** is
        which rows it is asking about.  Only the second is a definition,
        so it is stated here once and both readers build on it —
        :meth:`_active_alerts` selecting rows, :meth:`_open_alert_titles`
        selecting one column.  Adding a third projection tomorrow adds no
        third definition.

        Composed from :func:`~sysadmin.core.models.alert.unresolved`
        rather than restating it: "open" is a fact about the table and
        belongs beside the column and the partial indexes that encode it,
        where nineteen hand-written copies of it could not reach the
        index they were eight lines from.  ``Alert.agent == self.name``
        stays here, because a scope one caller applies is not a
        vocabulary anyone can disagree about.
        """
        return (Alert.agent == self.name, unresolved())

    async def _active_alerts(self, session) -> list[Alert]:
        """This agent's unresolved alerts, as rows.

        Three callers need the rows themselves —
        :meth:`_check_anomalies` (id, ``details``),
        :meth:`_check_agent_health` (id, severity, ``created_at``,
        ``details``, to run two ladders off) and
        :meth:`_check_collation` (id, ``details``) — and each must see
        what the run has already written by the time it asks, so none of
        them can share the snapshot ``_execute`` takes before the service
        loop.  Three reads, deliberately, and the entry is right about
        that; what was wrong was the cost it put on them.

        Prefer :meth:`_open_alert_titles` where only titles are wanted.
        """
        result = await session.execute(
            select(Alert).where(*self._open_alert_criteria())
        )
        return list(result.scalars().all())

    async def _open_alert_titles(self, session) -> set[str]:
        """The titles of this agent's unresolved alerts, and nothing else.

        The dedup snapshot ``_execute`` takes before it raises anything.
        It used to build this set by materialising every open row and
        throwing all but one column away, which is affordable exactly
        while the table is small — and ``SNAG-AGENT-005``'s ``_open_alerts``
        was written the same way and pulled **593,814 ORM objects** on its
        first live run, the fix falling over on the backlog it existed to
        end.

        A set rather than a list: the only question asked of it is
        membership, and building the set at the call site let a caller
        hold the rows longer than it needed them.
        """
        result = await session.execute(
            select(Alert.title).where(*self._open_alert_criteria())
        )
        return set(result.scalars().all())

    @staticmethod
    async def _resolve_alert_ids(session, alert_ids: list[Any]) -> None:
        """Mark specific alerts resolved (used when a condition clears)."""
        if not alert_ids:
            return
        await session.execute(
            update(Alert)
            .where(Alert.id.in_(alert_ids))
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )

    async def _check_anomalies(
        self,
        session,
        snapshot: ResourceSnapshot,
        history: dict[str, list[float]],
        config: AnomalyConfig,
    ) -> int:
        """Raise alerts for statistically unusual resource readings.

        Suppression rules:
        - a resource that already fired a fixed-threshold alert (this run
          or still unresolved from an earlier one) is skipped — the
          threshold alert says the same thing more plainly
        - an unresolved anomaly alert for the same resource is not repeated
        - anomaly alerts are resolved once the resource is normal again
        """
        if not config.enabled:
            return 0

        anomalies = detect_anomalies(
            self._snapshot_metrics(snapshot), history, config
        )
        active = await self._active_alerts(session)

        threshold_keys = set(self._threshold_keys)
        anomaly_alerts: dict[str, Any] = {}
        for alert in active:
            details = alert.details or {}
            resource = details.get("resource")
            if not resource:
                continue
            if details.get("threshold"):
                threshold_keys.add(resource)
            elif details.get("anomaly"):
                anomaly_alerts[resource] = alert.id

        raised = 0
        flagged: set[str] = set()
        for anomaly in anomalies:
            flagged.add(anomaly.key)
            if anomaly.key in threshold_keys:
                logger.debug(
                    "anomaly_suppressed_by_threshold_alert",
                    extra={"resource": anomaly.key},
                )
                continue
            if anomaly.key in anomaly_alerts:
                continue  # already open — do not re-raise every run
            await self.raise_alert(
                session,
                severity=config.severity,
                title=self._anomaly_title(anomaly),
                message=(
                    f"{anomaly.label} at {anomaly.value:.1f}% is "
                    f"{abs(anomaly.z):.1f}σ {anomaly.direction} the "
                    f"{config.window_days}-day mean of {anomaly.mean:.1f}% "
                    f"(σ={anomaly.stdev:.1f}, n={anomaly.samples})"
                ),
                details=anomaly.as_details(),
            )
            raised += 1

        # Resolve anomaly alerts whose resource is back within normal range
        await self._resolve_alert_ids(
            session,
            [alert_id for key, alert_id in anomaly_alerts.items() if key not in flagged],
        )

        return raised

    @staticmethod
    def _anomaly_title(anomaly: Anomaly) -> str:
        return f"Unusual {anomaly.label} usage"

    # --- Self-monitoring ---

    async def _check_agent_health(self, session, config: AppConfig) -> int:
        """Both self-monitoring families, off **one** snapshot of the tables.

        ``agent_runs`` and ``alerts`` are read once here and handed to
        both checks.  Fetching separately would let the two disagree
        about the same agent between one query and the next — and their
        mutual exclusion (a stalled agent is never also reported as
        failing) is only sound if they are looking at the same data.

        The two families are deliberately separate — see
        :mod:`sysadmin.monitor.failures` for why "has not run" and "ran
        and failed" are not one alert with two messages — but they are
        one *decision*, made together, which is why there is one caller.

        Counts are reset here rather than in ``_execute`` so that a run
        with ``self_monitor.enabled`` false reports zeroes rather than
        the previous run's numbers.
        """
        self._stall_counts = _NO_STALLS
        self._agent_failure_counts = _NO_AGENT_FAILURES
        if not config.self_monitor.enabled:
            return 0

        report = await build_self_report(session, config)
        active = await self._active_alerts(session)

        written = await self._check_agent_liveness(session, config, report, active)
        written += await self._check_agent_failures(session, config, report, active)
        return written

    async def _check_agent_failures(
        self,
        session,
        config: AppConfig,
        report: dict[str, Any],
        active: list[Alert],
    ) -> int:
        """Alert when an agent's runs keep failing, and keep saying so.

        The reader SNAG-DB-001 was missing: for ~18 hours of uptime the
        daemon logged ``agent_run_failed`` every five minutes and
        nothing read it, because the thing that had broken *was* the
        alerting path.  ``agent_runs`` has recorded those failures since
        Session 41 — before that the ``failed`` row died in the
        transaction the failure destroyed — and this is what reads them.

        Lifecycle is identical to :meth:`_check_agent_liveness`: raise
        quiet, escalate by resolving the quiet row and inserting a loud
        one (never an in-place severity change, which keeps a tray
        fingerprint that has already been suppressed), hold while a row
        that loud is open.

        **The handover between the two families is automatic**, and it
        is the point of routing eligibility through
        :func:`failures.is_failing`.  An agent that fails repeatedly and
        then stops being scheduled ceases to be "failing" and becomes
        "stalled": this run resolves its failure row and
        :meth:`_check_agent_liveness` opens a stall row, so the owner
        sees one open alert that changed its mind rather than two
        criticals about one dead agent.

        Returns:
            Rows written — raises *and* escalations.
            ``details["agent_failures"]`` breaks them down.
        """
        threshold = config.self_monitor.failure_alert_threshold
        entries: list[dict[str, Any]] = report["agents"]

        # The resolve set comes from the same predicate the raise does,
        # rather than a second reading of "failing" — two copies of an
        # eligibility rule drift in the direction nobody notices.
        failing = {a["name"] for a in entries if failures.is_failing(a, threshold)}

        # Keyed from details rather than by parsing the title apart,
        # matching how the stall family finds its own rows.
        open_failures: dict[str, tuple[Any, failures.OpenFailure]] = {}
        for alert in active:
            name = (alert.details or {}).get(failures.FAILURE_DETAIL_KEY)
            if not name:
                continue
            open_failures[name] = (
                alert,
                failures.OpenFailure(
                    alert_id=alert.id,
                    severity=alert.severity,
                    created_at=alert.created_at,
                ),
            )

        due = failures.evaluate(
            entries,
            {name: entry[1] for name, entry in open_failures.items()},
            failure_threshold=threshold,
            escalate_after_hours=config.self_monitor.escalate_after_hours,
        )

        raised = 0
        escalated = 0
        for item in due:
            if item.step is failures.Step.ESCALATE:
                quiet_row = open_failures[item.agent_name][0]
                quiet_row.resolved = True
                quiet_row.resolved_at = datetime.now(UTC)
                escalated += 1
            else:
                raised += 1
            await self.raise_alert(
                session,
                severity=item.severity,
                title=item.title,
                message=item.message,
                details=item.details,
            )

        # Ran clean again, or handed over to the stall family. Read from
        # open_failures rather than recomputing titles, so this cannot
        # drift from the lookup above.
        await self._resolve_alert_ids(
            session,
            [
                entry[1].alert_id
                for name, entry in open_failures.items()
                if name not in failing
            ],
        )

        self._agent_failure_counts = {
            "failing": len(failing),
            "raised": raised,
            "escalated": escalated,
        }
        return raised + escalated

    async def _check_agent_liveness(
        self,
        session,
        config: AppConfig,
        report: dict[str, Any],
        active: list[Alert],
    ) -> int:
        """Alert when an agent has silently stopped running, and keep saying so.

        The report and the open-alert list are passed in by
        :meth:`_check_agent_health` rather than fetched here, so this and
        the failure family read **one** snapshot of ``agent_runs`` and
        one of ``alerts``. Two fetches a few milliseconds apart could
        disagree about whether an agent is stalled or failing, and the
        two families' mutual exclusion is asserted against exactly that.
        It is still the same report ``/api/sysadmin/self`` serves, so the
        alert and the endpoint cannot disagree either. Detection is
        unchanged since it was written and was never the gap — see
        :mod:`sysadmin.monitor.stalls` for the Session 39 evidence that it
        caught ``SNAG-AGENT-003`` correctly and then went quiet.

        What is decided *here* is the alert lifecycle, and it now has three
        outcomes rather than two:

        - **Raise** — first detection, at :attr:`STALL_LADDER.quiet`.
        - **Escalate** — the warning has stood ``escalate_after_hours``
          unresolved. The quiet row is **resolved and a louder one
          inserted**, never updated in place: the tray fingerprints on
          ``"{severity}:{title}"``, so an in-place severity change keeps
          the fingerprint it has already suppressed and the escalation is
          recorded but never spoken.
        - **Hold** — a row at that severity or louder is already open.
          This is the branch that stopped the 1,664-row pile-up and it
          stays exactly as it was.

        Recovery still resolves the row outright, and deliberately does not
        walk back down the rungs: an agent that ran again is not a quieter
        fault, it is not a fault.

        Returns:
            Rows written — raises *and* escalations, since both are an
            alert this run produced. ``details["stalls"]`` breaks them
            down, so a run that only escalated is distinguishable from one
            that found a new stall.
        """
        stalled = {a["name"]: a for a in report["agents"] if a["stalled"]}

        # Keyed by the *stalled agent*, from details rather than by parsing
        # the title back apart. Rows raised before Session 39 carry the
        # same key, so an alert already open when this deployed is found
        # and escalated rather than duplicated.
        open_stalls: dict[str, tuple[Any, stalls.OpenStall]] = {}
        for alert in active:
            name = (alert.details or {}).get(stalls.STALL_DETAIL_KEY)
            if not name:
                continue
            open_stalls[name] = (
                alert,
                stalls.OpenStall(
                    alert_id=alert.id,
                    severity=alert.severity,
                    created_at=alert.created_at,
                ),
            )

        due = stalls.evaluate(
            list(stalled.values()),
            {name: entry[1] for name, entry in open_stalls.items()},
            escalate_after_hours=config.self_monitor.escalate_after_hours,
        )

        raised = 0
        escalated = 0
        for item in due:
            if item.step is stalls.Step.ESCALATE:
                quiet_row = open_stalls[item.agent_name][0]
                quiet_row.resolved = True
                quiet_row.resolved_at = datetime.now(UTC)
                escalated += 1
            else:
                raised += 1
            await self.raise_alert(
                session,
                severity=item.severity,
                title=item.title,
                message=item.message,
                details=item.details,
            )

        # Agent came back — clear its stall alert. Read from open_stalls
        # rather than recomputing titles, so this cannot drift from the
        # lookup above.
        await self._resolve_alert_ids(
            session,
            [
                entry[1].alert_id
                for name, entry in open_stalls.items()
                if name not in stalled
            ],
        )

        self._stall_counts = {
            "stalled": len(stalled),
            "raised": raised,
            "escalated": escalated,
        }
        return raised + escalated

    # --- Database collation ---

    async def _check_collation(self, session, agent_config) -> int:
        """Alert on databases whose text ordering predates the OS's.

        ``SNAG-DB-002``, and the reason it belongs *here* rather than in
        a script: it is measurable in one query, invisible until
        something goes wrong, and was found only because a human happened
        to open ``psql``.  That is the exact class of fault this service
        exists to catch, and nothing on this box was watching for it.

        **This family owns its own lifecycle**, so it resolves its own
        rows two blocks below rather than falling to
        :meth:`_resolve_recovered` — see rule 4 in
        :mod:`sysadmin.monitor.collation` and the note against
        :data:`RESOLVABLE_TITLE_PATTERNS`.  Dedup and that sweep cannot
        both apply to one family.

        The read is deliberately not wrapped in a savepoint.  Unlike a
        service health row it writes nothing of its own before the
        alerts, so there is no partial state to isolate; a catalog read
        that fails means the database is unreachable, which every other
        check in this run has already discovered more loudly.
        ``SQLAlchemyError`` is caught so a cluster that does not offer
        ``pg_database_collation_actual_version`` (it arrived in
        PostgreSQL 15) costs a log line rather than the whole run — the
        savepoint lesson from ``SNAG-DB-001`` applied at the granularity
        that is available here.

        Returns:
            Rows raised.  ``details["collation"]`` also carries the
            standing ``mismatched`` count, which is the number that
            matters: ``raised`` is 0 on every run after the first.
        """
        if not agent_config.collation.enabled:
            self._collation_counts = _NO_COLLATION
            return 0

        try:
            result = await session.execute(collation.MISMATCH_SQL)
            rows = result.mappings().all()
        except SQLAlchemyError as exc:
            logger.warning(
                "collation_check_failed",
                extra={"agent": self.name, "error": _truncate_error(exc)},
            )
            self._collation_counts = _NO_COLLATION
            return 0

        mismatches = [
            collation.Mismatch(
                datname=row["datname"],
                recorded=str(row["recorded"]),
                actual=str(row["actual"]),
            )
            for row in rows
        ]

        # Open rows are keyed from details, not by parsing the title
        # apart — the same lookup the stall and failure families use.
        open_rows: dict[str, Any] = {}
        for alert in await self._active_alerts(session):
            datname = (alert.details or {}).get(collation.COLLATION_DETAIL_KEY)
            if datname:
                open_rows[datname] = alert.id

        raised = 0
        for item in collation.evaluate(mismatches, set(open_rows)):
            await self.raise_alert(
                session,
                severity=collation.COLLATION_SEVERITY,
                title=item.title,
                message=item.message,
                details=item.details,
            )
            raised += 1

        # Reindexed, dropped, or recreated on current locale data — one
        # set difference covers all three, where a loop over the current
        # mismatches could only ever see the first.
        cleared = collation.resolved_databases(
            set(open_rows), {m.datname for m in mismatches}
        )
        await self._resolve_alert_ids(
            session, [open_rows[name] for name in sorted(cleared)]
        )

        self._collation_counts = {
            "mismatched": len(mismatches),
            "raised": raised,
            "resolved": len(cleared),
        }
        return raised

    # --- Port detection ---

    @staticmethod
    def get_port_usage() -> list[dict[str, Any]]:
        """Get current port usage map (listening ports)."""
        ports = []
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr:
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    ports.append({
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                        "process": proc.name() if proc else None,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    ports.append({
                        "port": conn.laddr.port,
                        "address": conn.laddr.ip,
                        "pid": conn.pid,
                        "process": None,
                    })
        return sorted(ports, key=lambda p: p["port"])
