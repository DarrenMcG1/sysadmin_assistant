"""Closing the ``agent_runs`` rows a dead process left behind.

Session 41 split :meth:`~sysadmin.core.agent.BaseAgent.run` into three
transactions and stated the cost in writing: *"a process killed mid-run
leaves a permanent ``running`` row where it used to leave no row at
all"*.  ``SNAG-DB-006`` is the other end of that sentence — the
``chk_run_status`` CHECK constraint has admitted ``cancelled`` since
migration 001 and nothing has ever written one, so a reader takes the
value as evidence of a path that does not exist.

**Measured before deciding, because the entry named two opposite fixes
and the measurement picks between them.**  All seven live ``running``
rows (2026-08-14 → 2026-08-28) are one thing: a run interrupted by
``scheduler.shutdown(wait=False)`` in :func:`sysadmin.main.lifespan`.
Each is followed by a **clean** daemon death within 0.032–61.2 s, and for
each the next ``agent_run_completed`` for that agent comes from a
*different* PID — the successor instance.  None of the seven ever logged
an outcome.

The control is what makes that evidence rather than a coincidence: of
40,383 ``completed`` runs, **162 (0.401 %)** started within that window,
and ``file_organiser`` — whose scan takes ~108 s and so has the widest
exposure of any agent — is **0 of 112** against **3 of 3** stuck.  The
separation is total: no run starting more than 61 s from a death has ever
got stuck.  So ``cancelled`` has a real referent, and dropping it from
the constraint would delete the name of a thing that happens roughly
**every twentieth daemon death** (7 of 144 since 2026-08-04).

Six rules, four of them the opposite of the obvious implementation:

1. **The sweep runs at *startup*, not at shutdown — a third shape the
   entry does not name.**  Writing ``cancelled`` from the lifespan's
   shutdown half is what anyone reaches for, and it races the thing it
   describes: ``shutdown(wait=False)`` returns while the worker thread is
   still inside ``_execute``, and three of the seven had 30–60 s of
   ``file_organiser`` scan left at that moment.  A shutdown write can
   therefore land *after* a ``completed`` the thread manages to commit.
   A startup sweep cannot race anything, because the process whose rows
   it closes is gone: ``Deactivated successfully`` precedes ``Started``
   in 144 of the 145 deaths in the journal, and the exception is a
   reboot.  It is also :mod:`sysadmin.core.unit_failure`'s argument
   arriving one table over — *the service starting is the only moment at
   which the fact exists* — and it reaches the shapes a shutdown hook
   cannot: SIGKILL, a hard power-off, and a crash mid-run.

   That last clause is a **theoretical** advantage here and says so.  All
   ten crash deaths in the journal died 2.1–4.8 s into the instance —
   ``SNAG-DB-005``'s schema-guard refusals — before the scheduler could
   fire anything, so they could not have left a stuck row.  On the live
   population both shapes reach 7 of 7.  The race in rule 1 is the
   discriminator that is not hypothetical.

2. **The instance id is minted here, never read from the environment.**
   systemd stamps ``INVOCATION_ID`` into this unit's environment and it
   would do the job, but ``CLAUDE.md`` states that this service reads no
   environment variables at all, and a lone exception is a convention
   that has stopped being one.  A per-process UUID is also strictly more
   general: an agent driven by hand from a session — a real population in
   this repository, and the shape that wrote two of the seven rows — gets
   an identity for free, where an environment read would give every such
   drive the *same* absent value and make them indistinguishable from
   each other.

3. **A row with no stamp is refused, not swept — which is what makes
   this forward-only by construction rather than by a constant.**  The
   seven live rows predate this module, so they carry no
   ``details['instance']`` and the sweep cannot attribute them to a dead
   process rather than to a live one.  Refusing them is ``ports_checked``'s
   rule: zero-because-blind must not be served as zero-because-clean.
   The alternative — bounding the sweep by an age — would need an invented
   constant (``NOISE_MIN_OCCURRENCES``' status) to express a fact the data
   already carries.  They age out of the 30-day retention window by
   2026-09-27 on their own, and ``refused`` **counts them** so the
   forward-only property is observable rather than merely intended.

4. **Nothing is capped, and unlike its siblings it cannot need to be.**
   Every roll-up in this repository bounds what it names.  Here the
   steady state is bounded by construction: the sweep runs on *every*
   start, so what it finds is what one instance had in flight, and
   APScheduler's ``max_instances: 1`` caps that at one run per job.  What
   is logged is the **agent names** — bounded by
   :data:`~sysadmin.monitor.self_monitor.AGENT_NAMES` at five whatever
   the volume — with the count carrying the volume.  That is
   ``details['truncated_sources']``' rule: name the sources, count the
   rest.

5. **The status is a literal here and pinned to the constraint by a
   test.**  ``STATUS_READINGS`` sits beside its CHECK constraint because
   a *classification* of every admitted value belongs there; this is one
   value of four, and which of the four means "abandoned" cannot be
   derived from a constraint that merely lists them.  So it is written
   once and ``tests/test_abandoned_runs.py`` asserts ``chk_run_status``
   still admits it — ``syslog_priority`` against ``PRIORITY_MAP``'s
   treatment.  The failure mode of a migration dropping the value is then
   a red test rather than an ``IntegrityError`` on the next restart.

6. **It reports and never refuses.**  The caller wraps it, for
   ``resolve_unit_failures``' reason three lines above it in the
   lifespan: a stale ``running`` row is worth less than a boot, which is
   the exact opposite of the trade :mod:`sysadmin.core.schema_guard`
   makes.  A sweep that cannot run leaves the rows it would have closed —
   which is the behaviour of every release before this one.

The query is a sequential scan and is left that way deliberately:
measured on the live table at **5.1 ms over 2,612 buffers**, once per
process start, against ``SNAG-AGENT-007``'s 41,644 buffers *four times
per 300-second run* — the case that did warrant an index.
"""

import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.models.agent_run import AgentRun

logger = logging.getLogger(__name__)

#: Identity of *this* process, minted once at import.
#:
#: Rule 2: not systemd's ``INVOCATION_ID``.  A module-level constant
#: rather than a lazily-created one because it must be stable across
#: every scheduler thread in the process, and the threads are created
#: after import in all five triggers.
INSTANCE_ID: str = str(uuid.uuid4())

#: Where :meth:`~sysadmin.core.agent.BaseAgent._record_start` writes it.
#:
#: In ``details`` rather than in a column of its own: a column needs a
#: migration, which moves the packaged head and so owes the box
#: ``alembic upgrade head`` plus a restart or :mod:`schema_guard` refuses
#: to boot — ``SNAG-DB-005``'s twenty-three hours, for a fact that is
#: read by exactly one query and never joined on.
INSTANCE_DETAIL_KEY = "instance"

#: What :func:`close_abandoned_runs` records about why the row moved.
#:
#: ``unit_failure``'s ``details['source'] = 'systemd_onfailure'``: the
#: provenance the ``status`` column cannot carry.  A ``cancelled`` row
#: written by some future path that genuinely cancels a run on request is
#: a different event from one this sweep closed, and a reader of a stale
#: row cannot otherwise tell them apart.
CANCELLED_BY = "startup_sweep"

#: The status an abandoned run is closed with.  Rule 5 — one of the four
#: values ``chk_run_status`` admits, pinned there by a test rather than
#: derived, because the constraint lists the vocabulary and does not say
#: which member means this.
CANCELLED_STATUS = "cancelled"

#: The status a row is in while it is a candidate.
RUNNING_STATUS = "running"


def abandoned_by(instance_id: str):
    """Criteria for a ``running`` row some *other* process is holding.

    Split out of :func:`close_abandoned_runs` so it can be compiled and
    read — ``_open_alert_criteria``'s shape, and for that rule's reason:
    what a caller wants *back* may differ, what it is asking *about* may
    not.  Here there is one caller and the split earns its place a
    different way, which is worth stating because it was measured rather
    than reasoned:

    **The ``IS NOT NULL`` conjunct is redundant and is kept anyway.**
    Under SQL's three-valued logic ``NULL <> 'x'`` is ``NULL``, so an
    unstamped row is already excluded by the inequality alone — a
    mutation deleting the conjunct passes **every** behavioural test in
    ``tests/test_abandoned_runs.py``.  It stays because its visibility is
    what stops the dangerous edit: a reader who notices the NULL case and
    "fixes" it with a ``COALESCE(details->>'instance', '')`` would sweep
    the very rows rule 3 refuses, and would do it silently.  A clause
    whose removal is invisible in behaviour can only be pinned by reading
    the statement, which is what
    ``TestTheRefusalIsWrittenDownRatherThanInherited`` does.
    """
    return (
        AgentRun.status == RUNNING_STATUS,
        AgentRun.details[INSTANCE_DETAIL_KEY].astext.isnot(None),
        AgentRun.details[INSTANCE_DETAIL_KEY].astext != instance_id,
    )


def unattributable():
    """Criteria for a ``running`` row carrying no instance stamp at all.

    The complement of :func:`abandoned_by` over ``running`` rows, and
    stated positively rather than as its negation: rule 3's count is a
    claim about evidence the sweep does not have, not a leftover.
    """
    return (
        AgentRun.status == RUNNING_STATUS,
        AgentRun.details[INSTANCE_DETAIL_KEY].astext.is_(None),
    )


@dataclass(frozen=True)
class SweepResult:
    """What one startup sweep found.

    ``closed`` and ``refused`` are deliberately separate counts and not a
    sum.  A row this sweep could not attribute is not a row it decided to
    leave alone: the first is evidence that a release predating
    :data:`INSTANCE_DETAIL_KEY` wrote it, the second would be a judgement
    nobody took.  Collapsing them retires rule 3 in silence the day the
    last unstamped row ages out.
    """

    closed: int = 0
    refused: int = 0
    agents: tuple[str, ...] = field(default_factory=tuple)

    @property
    def found_nothing(self) -> bool:
        """True when there was nothing to close and nothing to refuse."""
        return self.closed == 0 and self.refused == 0


async def close_abandoned_runs(
    session: AsyncSession, instance_id: str = INSTANCE_ID
) -> SweepResult:
    """Close every ``running`` row a *previous* process left behind.

    Sound because there is exactly one of this daemon at a time — it is a
    systemd service bound to a fixed port — so a ``running`` row carrying
    an instance id that is not ours belongs to a process that is already
    gone.  Rule 1: the ordering that guarantees it is systemd's, and the
    journal shows ``Deactivated successfully`` before ``Started`` on
    every death but one reboot.

    ``instance_id`` is a parameter with a default rather than a read of
    the module constant, so a test can drive two "processes" without
    reaching into module state — and so this function states which
    identity it used rather than which one it happened to import.

    The one hazard worth naming is benign and self-correcting: an agent
    driven by hand from a session, still running when the daemon
    restarts, has its row closed here.  That drive's own
    ``_record_outcome`` then overwrites ``cancelled`` with the real
    outcome, so the final value is correct in both directions — and if
    the drive is itself killed, ``cancelled`` was correct all along.
    """
    refused = await session.scalar(
        select(func.count()).select_from(AgentRun).where(*unattributable())
    )

    rows = (
        await session.execute(
            update(AgentRun)
            .where(*abandoned_by(instance_id))
            .values(
                status=CANCELLED_STATUS,
                completed_at=func.now(),
                details=AgentRun.details.op("||")(
                    func.jsonb_build_object("cancelled_by", CANCELLED_BY)
                ),
            )
            .returning(AgentRun.agent)
        )
    ).scalars().all()

    result = SweepResult(
        closed=len(rows),
        refused=int(refused or 0),
        agents=tuple(sorted(set(rows))),
    )

    if result.closed:
        logger.info(
            "abandoned_runs_closed",
            extra={
                "count": result.closed,
                "agents": list(result.agents),
                "instance": instance_id,
            },
        )
    if result.refused:
        logger.info(
            "abandoned_runs_unattributable",
            extra={
                "count": result.refused,
                "detail": (
                    "running rows with no recorded instance — written "
                    "before this sweep existed, so they cannot be "
                    "attributed to a dead process and are left alone"
                ),
            },
        )
    return result
