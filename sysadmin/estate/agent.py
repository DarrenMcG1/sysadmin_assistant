"""The estate judge — reads the estate's published surfaces, decides.

The estate manager publishes and never acts (its ADR-0003, ADR-0004 §6):
it files audit findings rather than raising alerts, and it never grades
its own scan.  This agent is the other half of that arrangement and the
piece the Session 4 cutover deliberately left behind — until it ran, the
estate computed idle nudges every night into a surface nothing read, and
the tray showed nothing.

**Dedup and a set-based resolve, together, and that pairing is the whole
design.**  :mod:`sysadmin.monitor.collation` records that the two are
mutually exclusive, and they are — *there*.  That sweep excludes the
titles the run **raised**, so a deduplicating family (which raises
nothing on the second run) has its still-true row resolved, then
re-raised, then resolved: a flip-flop that clears the tray's
``{severity}:{title}`` fingerprint on every turn and notifies again.

The exclusion set here is the titles the run **judged**, which is not
the same set: dedup suppresses the raise, never the judgement.  A fault
that persists is in ``current`` on every run, so it is never swept, and
a fault that clears leaves ``current`` exactly once and is resolved
exactly once.  That is only available to an agent that owns every row it
sweeps — ``_resolve_recovered`` scopes on ``Alert.agent == self.name``,
so ``agent='estate_judge'`` rows are unreachable from the sysadmin
agent's sweep by construction, and this one reaches nothing else.

**The sweep is scoped to the surfaces this run actually read**, which is
the rule that stops a partial pull announcing false recoveries.  Five
independent surfaces are served by one process, so a 500 from
``/api/projects/attention`` while the other three answer is a real
state; sweeping globally would then resolve every open health breach and
idle nudge on the strength of a payload nobody received.  That is
``_resolve_recovered``'s ``error``-is-not-``skipped`` rule — "the state
is unknown and resolving on unknown announces a recovery nobody
observed" — applied per surface instead of per service.

**Unreachability is not this agent's alert.**  ``estate-manager-api`` is
an ``http`` entry in ``services.yaml``, polled every 300 s, and both
estate timers sit beside it as ``kind: timer``.  A second owner of that
lifecycle closes a row while the first still holds it true, which is the
defect this repository has now found at three different scales.  So 8400
being down costs a log line and ``details['unread_surfaces']``, and
nothing else.

**What this agent does not do is escalate, and Session 53 settled why
rather than leaving it deliberate-but-unexamined** (SNAG-ESTATE-003).
Session 39's argument — a warning that fires once is indistinguishable
from one that got fixed — does apply to these families, and
:mod:`sysadmin.core.escalation` is sitting in ``core`` ready to be
reused.  Two reasons stood against wiring it: the loud rung is
``critical``, which breaks DND by configuration and is reserved for
faults on this box rather than for the estate being a day behind on a
scan; and the family most in need of escalation already arrives
pre-escalated from the producer — an idle nudge carries the estate's own
rung (``info`` at 7 days, ``warning`` at 14), which this agent takes
verbatim.

Both still hold, and the snag's proposed alternative — *a third,
repeat-without-*``critical`` *rung here in* ``core`` — was **measured and
refuted**.  The tray fingerprints on ``"{severity}:{title}"`` and only
closes an episode when that pair is absent from a poll, which a
resolve-and-re-raise inside one agent run never produces: a repeat that
keeps both constant is silent whatever this agent writes.  So there is
nothing for a third rung to be *heard* by, and restating a standing
fault is a notification decision rather than a lifecycle one.  It lives
in ``sysadmin_tray/notifications.py`` as ``reminder_hours``, which
covers every deduplicating family at once instead of this one.  **Do not
re-derive the rung** — the ladder here stays two-runged on purpose.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select, update

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.async_http import LoopBoundClient
from sysadmin.core.config import EstateJudgeConfig, get_config
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.estate import client, judgements
from sysadmin.units.models import UnitAudit
from sysadmin.units.ports import PortAttribution, attribution_from_blob

logger = logging.getLogger(__name__)

#: ``details`` key naming the surface an alert came from.
#:
#: The sweep finds a row's surface here rather than by matching its title
#: against :data:`~sysadmin.estate.judgements.SURFACE_TITLE_PATTERNS`,
#: for the reason :mod:`sysadmin.monitor.collation` gives about
#: ``COLLATION_DETAIL_KEY``: a title is a sentence for a human, and
#: splitting one to recover a value is a parser nobody remembers writing.
#: The patterns survive as the documented partition and as what the test
#: asserts, not as runtime machinery.
SURFACE_DETAIL_KEY = "estate_surface"


class EstateJudgeAgent(BaseAgent):
    """Judges the estate's five published surfaces on an hourly poll."""

    def __init__(self) -> None:
        self._http = LoopBoundClient(lambda: httpx.AsyncClient(timeout=10.0))

    @property
    def name(self) -> str:
        return "estate_judge"

    async def _execute(self, session) -> AgentResult:
        """Pull, judge, raise what is new, resolve what has gone.

        **The pull happens before the session is touched**, and the
        ordering is load-bearing rather than tidy.  Session 41 changed
        ``BaseAgent.run`` so ``_execute`` receives a session that has
        never been flushed: its transaction opens at the first statement,
        not before.  Four HTTP round trips against a hung 8400 would
        otherwise sit inside an open transaction on a host that sets
        ``idle_in_transaction_session_timeout=1min`` — the rule
        ``files/review.py`` learned for inference calls (SNAG-AGENT-003),
        which is the same rule and a different remote.
        """
        config = get_config().agents.estate_judge

        # --- 1. Pull, outside any transaction ---------------------------
        async with self._http.scoped():
            async with self._http.borrow() as http:
                results = await client.pull_all(http, config.base_url)

        read = {name for name, r in results.items() if r.read}
        unread = {name: r.error for name, r in results.items() if not r.read}
        if unread:
            logger.warning(
                "estate_surfaces_unread",
                extra={"agent": self.name, "surfaces": sorted(unread)},
            )

        # --- 2. Judge, purely -------------------------------------------
        judged = self._judge(results, config, await self._attribution(session))
        current = {j.title for j in judged}

        # --- 3. Raise and resolve, in one transaction -------------------
        open_alerts = await self._open_alerts(session)
        open_titles = {a.title for a in open_alerts}

        raised = 0
        for judgement in judged:
            if judgement.title in open_titles:
                continue
            await self.raise_alert(
                session,
                severity=judgement.severity,
                title=judgement.title,
                message=judgement.message,
                details={
                    **judgement.details,
                    SURFACE_DETAIL_KEY: judgement.surface,
                },
            )
            # A title is taken the moment it is raised, not on the next
            # run. `judged` may legitimately hold two entries with one
            # title — two `ports` breach codes for one port would be two
            # findings and, by `judge_audit_findings` rule 4, one row —
            # and without this the run inserts both, then deduplicates
            # from the second run onwards. Bounded rather than a
            # pile-up, and still two unresolved rows for one fault: the
            # legibility half of SNAG-AGENT-006, arriving here through a
            # set that was read once and never updated.
            open_titles.add(judgement.title)
            raised += 1

        resolved = await self._resolve_gone(session, open_alerts, current, read)

        per_surface = {
            surface: sum(1 for j in judged if j.surface == surface) for surface in read
        }
        return AgentResult(
            findings_count=len(judged),
            alerts_raised=raised,
            details={
                # `standing` is the number that matters on every run after
                # the first, exactly as `mismatched` is for the collation
                # family: `raised` goes to 0 while the fault persists, and
                # a run reporting only `raised` reads as a clean estate.
                "standing": len(judged),
                "raised": raised,
                "resolved": resolved,
                "by_surface": per_surface,
                "surfaces_read": sorted(read),
                # Named, not counted — which surface is dark decides
                # whether it matters, the rule `truncated_sources` records.
                "unread_surfaces": unread,
            },
        )

    def _judge(
        self,
        results: dict[str, client.SurfaceResult],
        config: EstateJudgeConfig,
        attribution: Any = None,
    ) -> list[judgements.Judgement]:
        """Every surface that answered, through its own rules.

        A surface that was not read contributes nothing — not an empty
        list of judgements, which would be indistinguishable from "read
        and nothing wrong" once the two are concatenated.  The difference
        is preserved by ``read``, which the resolve consults and this
        does not.
        """
        out: list[judgements.Judgement] = []
        payloads = {
            name: result.payload
            for name, result in results.items()
            if result.read and result.payload is not None
        }

        if (payload := payloads.get("projects_invariants")) is not None:
            out += judgements.judge_projects_invariants(
                payload, config.scan_max_age_hours
            )
        if (payload := payloads.get("projects_attention")) is not None:
            out += judgements.judge_attention(payload, config.attention_max_rows)
        if (payload := payloads.get("audit_invariants")) is not None:
            out += judgements.judge_audit_invariants(
                payload, config.audit_max_age_hours
            )
        if (payload := payloads.get("audit_findings")) is not None:
            out += judgements.judge_audit_findings(
                payload, config.port_breach_max_rows, attribution
            )
        if (payload := payloads.get("queue_invariants")) is not None:
            out += judgements.judge_queue_invariants(
                payload, config.queue_max_depth, config.queue_max_wait_seconds
            )
        return out

    async def _attribution(self, session) -> PortAttribution:
        """Who held each port, from the newest stored unit sweep.

        **A read across a domain boundary, and it is deliberate.**  The
        alternative is running ``ss`` here, which would give two answers
        to one question at two different moments — this agent polls
        hourly and the sweep runs every six hours — with neither surface
        saying which one it used.  So the sweep owns the observation and
        this reads it, carrying ``observed_at`` so the age is visible
        rather than assumed.

        Failure is silent by design: an unreadable or absent sweep costs
        the ``details['holder']`` annotation and nothing else.  This
        family judged ports before Session 26c and must keep judging
        them if the sweep has never run — the enrichment is not allowed
        to become a dependency of the alert.
        """
        audit = (
            await session.execute(
                select(UnitAudit).order_by(UnitAudit.scanned_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if audit is None:
            return PortAttribution()
        block = (audit.findings or {}).get("ports")
        return attribution_from_blob(
            block if isinstance(block, dict) else None,
            audit.scanned_at.isoformat() if audit.scanned_at else None,
        )

    async def _open_alerts(self, session) -> list[Alert]:
        """This agent's unresolved rows.

        Bounded by construction, which is the property SNAG-AGENT-005
        found missing the hard way: the log aggregator's equivalent
        loaded 593,814 ORM objects on its first live run, the fix falling
        over on the backlog it existed to end.  This family deduplicates
        from its first run, so the row count is the number of distinct
        faults — a handful for the fixed-title families, one per breached
        or idle project for ``attention``, and never one per poll.
        """
        result = await session.execute(
            select(Alert).where(
                Alert.agent == self.name,
                unresolved(),
            )
        )
        return list(result.scalars().all())

    async def _resolve_gone(
        self,
        session,
        open_alerts: list[Alert],
        current: set[str],
        read: set[str],
    ) -> int:
        """Close every open row whose fault this run did not find.

        Covers recovery, a project deleted from the estate, a threshold
        raised in a ``.project.yaml`` and a source coming back, in one
        statement — the ``_resolve_recovered`` argument, which exists
        because a per-item loop over *current* faults can only ever
        observe the first: the other three never appear in a payload
        again, so their rows would stay open for ever.

        Two exclusions, and neither is optional:

        - a row whose surface was **not read** this run, because its
          state is unknown and resolving on unknown announces a recovery
          nobody observed;
        - a row with no :data:`SURFACE_DETAIL_KEY`, which cannot be
          attributed to a surface at all.  It is left open rather than
          swept: a stale row is a visible fault, a false recovery is an
          invisible one, and this agent's rows all carry the key from its
          first run so the branch is a guard against a future edit rather
          than a live case.
        """
        stale_ids = [
            alert.id
            for alert in open_alerts
            if alert.title not in current
            and (alert.details or {}).get(SURFACE_DETAIL_KEY) in read
        ]
        if not stale_ids:
            return 0

        await session.execute(
            update(Alert)
            .where(Alert.id.in_(stale_ids))
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        # One event for the batch, carrying a match rather than a subject
        # — the shape `BaseAgent.resolve_alerts` and the log aggregator
        # both emit. Recovery is deliberately not announceable from it:
        # `sysadmin/monitor/desktop.py` speaks `alert.raised` only, and a
        # resolved event naming its subject is what would let it start.
        self._queue_event(
            "alert.resolved",
            {
                "agent": self.name,
                "match": "no longer judged",
                "count": len(stale_ids),
            },
        )
        return len(stale_ids)
