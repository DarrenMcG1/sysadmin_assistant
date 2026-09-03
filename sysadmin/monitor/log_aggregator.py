"""Log Aggregator Agent — collects, filters, and summarises logs.

Sources:
- journalctl units (systemd services)
- Log files (tail with byte offset tracking)

Pipeline: parse → filter → store → alert → periodic LLM summarise
"""

import asyncio
import logging
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import DateTime, func, select, update

from sysadmin.core.agent import AGENT_RUN_FAILED_EVENT, AgentResult, BaseAgent
from sysadmin.core.config import get_config

# The alert-rung comparison this module used to do by hand against an
# aliased ``SEVERITY_ORDER``.  The alias existed because ``journal``
# exports a *different* ``SEVERITY_ORDER`` — five log severities, not
# the three ``chk_alert_severity`` admits — and letting the two names
# collide would have compared a log level against an alert level, wrong
# only for ``error``, which has no alert rung at all.  Importing the
# predicate instead of the ordering removes the collision rather than
# renaming around it, and there is now one statement of when a rung may
# move under a standing row.
from sysadmin.core.escalation import may_quieten_in_place
from sysadmin.core.models.alert import Alert, unresolved
from sysadmin.core.unit_failure import OWN_UNIT
from sysadmin.monitor.journal import (
    SEVERITY_ORDER,
    JournalRead,
    read_journal,
    since_timestamp,
)
from sysadmin.monitor.log_signature import alert_title, signature
from sysadmin.monitor.models.log_entry import LogEntry
from sysadmin.monitor.services import composed_log_sources

logger = logging.getLogger(__name__)

#: The loudest rung the tray will not speak.
#:
#: ``info`` because it is the only rung below ``tray.notify_min_severity``
#: on this box — the same derivation, and the same one number, as
#: ``judgements.TRANSIENT_HOLDER_SEVERITY``.  The row still exists, still
#: counts occurrences and still appears in the trend; it simply stops
#: interrupting.
#:
#: **One constant for both quietening paths, deliberately.**  A signature
#: declared in ``agents.log_aggregator.known_noise`` and one listed in
#: :data:`COVERED_SIGNATURES` are quiet for entirely different reasons —
#: an operator's judgement that a fault is harmless, against a structural
#: fact that another family owns the fault — and they are recorded under
#: different ``details`` keys so a reader can tell them apart.  But the
#: *number* answers one question, "what does the tray decline to say", and
#: two constants holding one value is the fork ``SNAG-DB-003`` describes.
NOISE_SEVERITY = "info"

#: How much of a journal message ``log_entries.message`` retains.
#:
#: Named rather than repeated, because :meth:`~LogAggregatorAgent._is_unstored`
#: compares an incoming line against a **stored** one to decide whether a
#: restart has already ingested it.  Truncating at two different lengths
#: would make every message longer than the smaller one compare unequal to
#: itself and re-ingest on every restart — ``SNAG-LOG-007`` rebuilt by the
#: fix for ``SNAG-LOG-007``.  ``raw_line`` keeps its own separate cap: it is
#: retained as evidence and nothing compares against it.
STORED_MESSAGE_CHARS = 5000

#: Fault signatures a **different alert family already owns**, mapped to
#: the family that owns them.  Keyed ``(source, signature)``.
#:
#: ``SNAG-LOG-005``.  ``BaseAgent.run`` states one fact twice, three lines
#: apart: it writes :data:`~sysadmin.core.agent.AGENT_RUN_FAILED_EVENT` to
#: the journal and then a ``failed`` row to ``agent_runs``.  Since the
#: level prefix (Session 61) and the ``format: json`` declaration (Session
#: 64) the journal copy reaches this agent, so one agent failure produced
#: a row here **and** a row from :mod:`sysadmin.monitor.failures` — two
#: tray fingerprints, two toasts.  Worse than duplication: ``failures.py``
#: requires **two** consecutive failures and argues that rule out in
#: writing, and this family raises on the **first** line, so it announced
#: exactly the event a sibling decided was not worth announcing.  A
#: deliberate threshold was not overridden, it was bypassed.
#:
#: Five rules, three of them the opposite of the obvious implementation:
#:
#: 1. **Quietened, never dropped.**  ``known_noise``'s rule 2 for its
#:    reason: a consumer that silently declines to judge is
#:    ``SNAG-CFG-001``'s shape, a decision taken with nothing recording
#:    that it was taken.  The row still carries its occurrence count into
#:    ``GET /api/logs/trends``, and ``details['covered_by']`` names the
#:    family that will speak — so a reader who finds the quiet row is told
#:    where the loud one comes from rather than left to wonder why it is
#:    ``info``.
#: 2. **Both halves of the key are constants the producers already own**,
#:    never strings written here.  ``OWN_UNIT`` is the unit
#:    ``read_journal`` reads and stamps into ``log_entries.source``;
#:    ``AGENT_RUN_FAILED_EVENT`` is the event ``BaseAgent.run`` emits.
#:    Copying either would be a second statement of somebody else's fact —
#:    the rule ``max_priority_for`` and ``chk_alert_agent`` already encode.
#: 3. **The source is half the key, never the signature alone** —
#:    ``known_noise``'s rule 1.  Another service logging the same word
#:    has no ``failures.py`` row behind it, so quietening it on the
#:    strength of this daemon's arrangement would silence a real fault.
#: 4. **Scoped to the one signature, not to this daemon's unit.**  The
#:    wider fix — excluding ``OWN_UNIT`` from the alert half entirely —
#:    was refused on measurement: of 249 error incidents in this journal,
#:    **34 carry no** ``agent_run_failed`` at all (``file_organiser_scan``
#:    ×27, ``retention_purge`` ×7), and ``retention_purge`` is not an
#:    agent, so no family covers it.  Excluding the unit deletes the only
#:    witness those have.
#: 5. **The case where ``failures.py`` is blind is the case where a
#:    different signature is still loud**, which is what makes rule 1's
#:    quietening safe rather than merely tidy.  ``failures.py`` reads
#:    ``agent_runs``, so it cannot see a failure ``_record_outcome``
#:    failed to record — but ``_record_outcome`` is awaited outside
#:    ``run()``'s ``try``, so its failure propagates into APScheduler and
#:    raises ``scheduler_job_error``, which this family still speaks at
#:    ``warning``.  Measured on the live journal: 215 of 215 historic
#:    ``agent_run_failed`` incidents carry ``scheduler_job_error`` in the
#:    same second, and every one of them wrote **no** ``agent_runs`` row.
#:    The net is stated rather than assumed — see ``SNAG-LOG-006`` for the
#:    one path it does not cover.
#:
#: A hand-maintained set of this kind is the ``SNAG-CFG-001`` shape, so it
#: is bounded rather than open: one entry, both halves derived, and a test
#: pins that the emitter still emits what this keys on.
#: The rungs at which an ingested line becomes an alert.  Below these a
#: line is stored, counted, and carried into ``GET /api/logs/trends``
#: while raising nothing and reaching no tray.
#:
#: Named rather than written inline because a *producer* now depends on
#: it: :data:`sysadmin.core.agent.MANUAL_RUN_CANCELLED_EVENT` is emitted
#: at ``warning`` precisely so that it is recorded without being
#: announced, and that choice is only correct while this tuple says so.
#: A test pins the two against each other — ``max_priority_for`` against
#: ``PRIORITY_MAP`` and ``chk_alert_agent`` against ``AGENT_NAMES``, the
#: same rule: derive, never write beside.
FAULT_SEVERITIES = ("error", "critical")

COVERED_SIGNATURES: dict[tuple[str, str], str] = {
    (OWN_UNIT, AGENT_RUN_FAILED_EVENT): "sysadmin/monitor/failures.py — "
    "'<agent> agent failing', at two consecutive failures",
}


@dataclass(frozen=True)
class CriticalSignature:
    """A line this family speaks for, louder than its journal rung.

    The mirror of :data:`COVERED_SIGNATURES` and of
    ``agents.log_aggregator.known_noise``, which both move a rung
    *down*.  Nothing moved one up, and on this box that left a whole
    class of fault unsayable: a full-card amdgpu MODE1 reset kills every
    GPU client on a 24 GB card shared by four services, and
    :data:`FAULT_SEVERITIES` could not reach it from either direction.

    **Two independent reasons, and fixing one alone fixes nothing** —
    ``SNAG-AGENT-008``'s multiplicative shape, met again:

    1. The kernel stamps the *diagnosis* at ``err`` and the **event** at
       ``info``.  Measured across the 2026-09-03 boot: ``GPU reset
       begin!``, ``MODE1 reset``, ``VRAM is lost due to GPU reset!`` and
       ``device wedged, but recovered through reset`` are all
       ``PRIORITY=6``, while ``Illegal opcode in command stream`` and
       ``ring gfx_0.0.0 timeout`` are ``PRIORITY=3``.  With the kernel
       source at ``severity_filter: error`` the reader passed
       ``journalctl -p 3``, so ``log_entries`` held **0** rows for all
       four event lines and **4** apiece for the two symptoms.  The
       monitor stored the wreckage and none of the event.
    2. ``critical`` was unreachable anyway.  ``chk_alert_severity``
       admits three rungs and journal ``error`` maps to alert
       ``warning``, so a log fault reaches ``critical`` only from
       ``PRIORITY`` 0–2, which amdgpu never uses.  All **44** amdgpu
       alert rows on this box are ``warning``.

    So the declaration widens what may raise *and* what rung it may
    reach, and neither half is any use alone.

    Attributes:
        title: What the row is called, at every rung.  Deliberately
            **not** :func:`~sysadmin.monitor.log_signature.alert_title`'s
            ``"Log {severity}: {source} — "``, for two reasons that point
            the same way.  That prefix interpolates the *journal* rung,
            so a line arriving at ``info`` and raised at ``critical``
            would carry ``Log info:`` on the one toast the tray leaves on
            screen — a row contradicting itself, which is the defect
            ``SNAG-LOG-010`` removed from the ``noise`` title.  And the
            rung cannot go in the title instead, because
            :func:`~sysadmin.core.escalation.step_for` escalates by
            resolving the quiet row and raising a louder one **under the
            same title**; a rung-derived title would fork the identity at
            exactly the moment the ladder is climbing it.  A declared
            fault is named after the fault.
        reason: Why this line is worth interrupting for, carried into
            ``details['escalated_reason']`` — ``known_noise``'s rule 2,
            for its reason: a judgement taken by a consumer with nothing
            recording that it was taken is ``SNAG-CFG-001``'s shape.
        arrives_at: The journal rung the producer stamps this line with.
            Declared rather than discovered so the pairing can be
            *checked*: a signature the configured ``severity_filter``
            cannot see is a declaration that silently does nothing, which
            is this entry's own defect rebuilt inside its own fix.
            ``tests/test_critical_signatures.py`` drives it against
            :func:`~sysadmin.monitor.journal.max_priority_for`.
    """

    title: str
    reason: str
    arrives_at: str


#: Signatures this family raises above their journal rung, and the only
#: place an alert rung is chosen by declaration rather than by mapping.
#:
#: Five rules, four of them the opposite of the obvious implementation:
#:
#: 1. **The second sighting is the news, not the first.**  A single MODE1
#:    reset is survivable — the card comes back, ``device wedged, but
#:    recovered through reset`` — and the box has produced one in ten days
#:    without anybody needing to be interrupted.  Three in eight hours is
#:    a different claim.  So a declared signature raises at
#:    :data:`DECLARED_FLOOR_SEVERITY` on its first raise inside
#:    ``critical_repeat_hours`` and escalates on the next, which is
#:    ``failures.py``'s "two consecutive failures" rule — *"the news is
#:    reproducible rather than happened"* — applied to an event family
#:    rather than a run table.
#: 2. **It climbs the existing ladder rather than picking a rung.**
#:    :func:`~sysadmin.core.escalation.step_for` resolves the quiet row
#:    and raises a louder one, because the tray fingerprints on
#:    ``{severity}:{title}`` and an in-place bump keeps a fingerprint it
#:    has already suppressed.  Session 39's rule, and the reason this is
#:    a *count* feeding a ladder and not a second severity map.
#: 3. **The count is of raises, never of lines.**  One reset writes
#:    eleven distinct signatures in the same second and this family opens
#:    one row per signature; counting lines would escalate the first
#:    reset on the strength of its own noise.  Counting rows carrying the
#:    declared title is counting *incidents*, which is what the rule
#:    means.
#: 4. **Bounded to what a producer already writes.**  Every key is a
#:    signature this box has actually emitted, verified against
#:    ``log_entries``/``raw_line`` rather than typed from documentation —
#:    a hand-maintained set is the ``SNAG-CFG-001`` shape, so it is small,
#:    and a test pins that :func:`signature` still maps the real line to
#:    the key (the failure mode of a kernel reword is *silence*, not an
#:    error).
#: 5. **The event, never the symptoms.**  ``Illegal opcode`` and ``ring
#:    gfx_0.0.0 timeout`` are the two symptom signatures already reaching
#:    ``warning``, and they were deliberately left there: they fire for
#:    hangs that recover without a reset, so declaring them would make
#:    this family speak for faults it cannot vouch for.  ``VRAM is lost
#:    due to GPU reset!`` is emitted by ``amdgpu`` only after the reset
#:    has happened, which is the one line that means what the row claims.
CRITICAL_SIGNATURES: dict[tuple[str, str], CriticalSignature] = {
    (
        "kernel",
        "amdgpu N:N:N.N: amdgpu: VRAM is lost due to GPU reset!",
    ): CriticalSignature(
        title="GPU was reset — every client lost its VRAM",
        reason=(
            "a full-card MODE1 reset: the graphics ring wedged, the "
            "per-queue reset failed, and amdgpu reset the device. Every "
            "GPU client's memory was destroyed — the foreground "
            "application and any resident inference server alike."
        ),
        arrives_at="info",
    ),
}

#: The rung a declared signature opens at, before the ladder moves it.
#:
#: ``warning`` rather than ``info`` because the first sighting is still a
#: fault that happened, and ``info`` is below ``tray.notify_min_severity``
#: on this box — an opening rung nobody can hear makes the escalation the
#: *only* audible rung, which is the "warning that fires once" defect
#: read backwards.  It is not derived from :data:`SEVERITY_ORDER`: the
#: floor of that mapping is ``debug``, and what this names is a policy
#: choice about how loud a first sighting is, not the bottom of a scale.
DECLARED_FLOOR_SEVERITY = "warning"


class LogAggregatorAgent(BaseAgent):
    """Collects and summarises logs from configured sources."""

    name = "log_aggregator"

    def __init__(self) -> None:
        self._file_offsets: dict[str, int] = {}
        # Journal resume positions, one per source.  In memory, so a
        # restart falls back to _resume_floor(), which reads the highest
        # entry already stored for that source — the cursor removes the
        # per-poll duplication, the floor the per-restart kind.  The
        # floor did **not** remove it until 2026-08-17 (SNAG-LOG-007):
        # it narrowed the re-read from a 5-minute window to a 1-second
        # one and the boundary entry came back every time.
        self._cursors: dict[str, str] = {}

    def forget_unknown(self) -> list[str]:
        """Drop resume state for sources no longer declared.

        The known set is :meth:`_sources`, not ``services.yaml`` alone —
        this agent reads journal sources from **both** files, and pruning
        on the services half would discard the cursor of every source
        config.yaml contributes. A dropped cursor is not a clean slate: the
        next poll falls back to ``_resume_floor()``, re-reading from the
        newest stored entry, which is the per-restart duplication the
        cursor exists to remove.

        So this prunes only what neither file declares any more, and it is
        called only from a configuration reload (:mod:`sysadmin.reload`).
        Returns the names dropped — ``details['truncated_sources']``'s rule:
        which source is affected decides whether it matters.
        """
        known = {s.name for s in self._sources(get_config().agents.log_aggregator)}
        dropped = sorted((set(self._cursors) | set(self._file_offsets)) - known)
        for name in dropped:
            self._cursors.pop(name, None)
            self._file_offsets.pop(name, None)
        return dropped

    @staticmethod
    def _sources(agent_config) -> list:
        """Journal sources, services.yaml first, config.yaml for the rest.

        The composition itself moved to
        :func:`sysadmin.monitor.services.composed_log_sources` in Session
        75, when ``GET /api/logs/{source}`` gained a validator and became
        its second caller.  This wrapper stays because it is the seam the
        tests patch, and because the ingestion loop below reads it as the
        agent's own answer to "what do I read".
        """
        return composed_log_sources(agent_config)

    async def _execute(self, session) -> AgentResult:
        """Ingest every source, then raise **one alert per distinct fault**.

        The raise used to sit inside the entry loop, unconditional, one row
        per matching log line — 593,814 unresolved rows for a Bluetooth
        firmware retry loop, 91 % of every unresolved alert in the table
        (``SNAG-AGENT-005``).  That is the mistake this application already
        recorded once, in ``GET /api/services/reliability``'s docstring:
        *"that table records one row per failed check — 123 rows for one
        internet outage"*.  A log is not an incident.

        So alerting happens **after** the loop, over
        :func:`~sysadmin.monitor.log_signature.alert_title` keys, and the
        three rules are the interesting part:

        1. **One open row per fault signature**, not per line and not per
           source.  A source-level key would let the Bluetooth storm hold
           the single ``Log error: kernel`` row while an RCU stall went
           unannounced — both are in the live 30-day window, so this is
           measured rather than hypothetical.
        2. **A repeat bumps the open row instead of raising a new one.**
           ``details['occurrences']`` carries the count that used to be
           expressed as row volume, which is the same information at
           1/300,000th of the storage and is legible on one tray line.
        2b. **A fault another family owns is quietened here rather than
           raised** — :data:`COVERED_SIGNATURES`, ``SNAG-LOG-005``.  The
           row is still written, still counted and still resolved on
           silence; it simply stops being the second thing that speaks
           about one fault.
        3. **Silence is the only recovery signal there is**, so the resolve
           is time-based (:meth:`_resolve_quiet`) rather than the
           "which open alerts would this run not raise?" inversion
           :meth:`sysadmin.monitor.agent.SysAdminAgent._resolve_recovered`
           uses.  That question is meaningless for an event: the answer is
           "all of them, one run later", which is expiry wearing
           resolution's clothes.
        """
        config = get_config()
        agent_config = config.agents.log_aggregator
        # Rebuilt every run rather than cached, which is free and is what
        # makes an edit to config.yaml take effect on the next poll — the
        # per-run configuration SNAG-AGENT-003 bought by forbidding agents
        # a startup hook.  ``GET /api/logs/actions`` tells the operator to
        # make that edit, so it had better land without a restart.
        known_noise = {
            (entry.source, entry.signature): entry
            for entry in agent_config.known_noise
        }
        total_ingested = 0
        alerts_raised = 0
        truncated: list[str] = []
        # signature title -> (severity, source, last message, count)
        faults: dict[str, dict[str, Any]] = {}

        # Sources declared beside the service that emits them, plus the
        # ones in config.yaml that belong to no service — the kernel
        # journal has no unit to hang off.  Names collide only if a
        # config.yaml source duplicates a service, which is the fault this
        # merge exists to make visible rather than to tolerate silently.
        for source in self._sources(agent_config):
            if source.type == "journalctl" and source.unit:
                read = await self._read_journal_source(
                    session, source, agent_config.max_entries_per_read
                )
            elif source.type == "file" and source.path:
                read = await asyncio.to_thread(
                    self._read_log_file,
                    source.name,
                    source.path,
                    source.severity_filter,
                    agent_config.max_entries_per_read,
                )
            else:
                continue

            if read.truncated:
                truncated.append(source.name)

            for entry in read.entries:
                log_entry = LogEntry(
                    source=entry["source"],
                    severity=entry["severity"],
                    message=entry["message"][:STORED_MESSAGE_CHARS],
                    raw_line=entry.get("raw_line", "")[:2000],
                    metadata_=entry.get("metadata", {}),
                    logged_at=entry["logged_at"],
                )
                session.add(log_entry)
                total_ingested += 1

                # The signature is computed for every stored line now,
                # where it used to be computed only for a line that had
                # already passed the rung gate.  It has to be: a declared
                # signature is precisely one whose *rung* does not admit
                # it, so the gate cannot be asked before the key exists.
                # The cost is a regex pass per ingested line rather than
                # per new fault — bounded by ``max_entries_per_read``, and
                # `signature` collapses 626,906 rows in 91 ms, so a full
                # 500-entry storm read spends well under a millisecond
                # here.
                sig = signature(entry["message"])
                key = (entry["source"], sig)
                declared = CRITICAL_SIGNATURES.get(key)

                if declared is None and entry["severity"] not in FAULT_SEVERITIES:
                    continue

                title = (
                    declared.title
                    if declared is not None
                    else alert_title(
                        entry["severity"], entry["source"], entry["message"]
                    )
                )
                fault = faults.get(title)
                if fault is None:
                    noise = known_noise.get(key)
                    # Two independent reasons to be quiet, kept apart in
                    # ``details`` because they answer different questions:
                    # an operator said this is harmless, against another
                    # family already owning it.  Either alone is enough to
                    # drop the rung, and a signature carrying both is
                    # over-determined rather than ambiguous.
                    covered_by = COVERED_SIGNATURES.get(key)
                    faults[title] = {
                        # A declared signature opens at the floor and is
                        # moved by the ladder in the raise phase, which is
                        # where the count of previous incidents can be
                        # read.  Deciding it here would need one query per
                        # ingested line.
                        #
                        # **Both quietenings still win, and the ordering is
                        # deliberate.**  ``known_noise`` is an operator
                        # saying this is harmless and
                        # :data:`COVERED_SIGNATURES` is a structural fact
                        # that another family speaks for it; a declaration
                        # here is this family's own judgement, and a
                        # module's judgement about its own rung must not
                        # override an operator's or another owner's.  A
                        # signature carrying both is over-determined rather
                        # than ambiguous — the same reading the two
                        # quietenings already give each other — and
                        # ``details`` records which applied.
                        "severity": (
                            NOISE_SEVERITY
                            if noise is not None or covered_by is not None
                            else DECLARED_FLOOR_SEVERITY
                            if declared is not None
                            else "critical"
                            if entry["severity"] == "critical"
                            else "warning"
                        ),
                        "declared": declared,
                        "source": entry["source"],
                        "message": entry["message"],
                        "count": 1,
                        "signature": sig,
                        "noise_reason": noise.reason if noise else None,
                        "covered_by": covered_by,
                    }
                else:
                    # The newest line wins, so the verbatim example beside
                    # a normalised title is the most recent occurrence
                    # rather than whichever arrived first.
                    fault["message"] = entry["message"]
                    fault["count"] += 1

        open_alerts = await self._open_alerts(session, set(faults))
        now = datetime.now(UTC)
        for title, fault in faults.items():
            existing = open_alerts.get(title)
            if existing is not None:
                self._record_recurrence(existing, fault, now)
                continue

            # The ladder, for a declared signature only, and only from
            # the floor — a row quietened by ``known_noise`` or by
            # :data:`COVERED_SIGNATURES` is left where those put it.
            #
            # This is a *raise*, not an in-place bump: ``existing`` is
            # ``None`` above, so the previous incident's row has already
            # been resolved by ``_resolve_quiet``.  Session 39's ban is
            # about rewriting a standing row's rung and does not reach
            # here; what the ladder contributes is the rule that the
            # louder statement is a fresh row under the same title, which
            # is what a declared title being rung-free makes possible.
            prior_incidents = 0
            if (
                fault["declared"] is not None
                and fault["severity"] == DECLARED_FLOOR_SEVERITY
            ):
                prior_incidents = await self._recent_incidents(
                    session, title, now, agent_config.critical_repeat_hours
                )
                if prior_incidents:
                    fault["severity"] = "critical"

            await self.raise_alert(
                session,
                severity=fault["severity"],
                title=title,
                message=fault["message"][:500],
                details={
                    "source": fault["source"],
                    "signature": fault["signature"],
                    "first_seen_at": now.isoformat(),
                    "last_seen_at": now.isoformat(),
                    "occurrences": fault["count"],
                    # Why this family is speaking above the rung the
                    # producer stamped, carried on the row rather than
                    # left to be inferred from the title — ``known_noise``
                    # rule 2's argument, in the loud direction.
                    #
                    # ``prior_incidents`` is uniform on every declared row
                    # including the first, where it is ``0``: a key
                    # present only on the escalated row would make its
                    # absence carry the news, which is the
                    # absent-vs-present collapse ``ports_checked``'s rule
                    # refuses.  The *value* carries it.
                    **(
                        {
                            "escalated_reason": fault["declared"].reason,
                            "prior_incidents": prior_incidents,
                        }
                        if fault["declared"] is not None
                        else {}
                    ),
                    # Present only when config.yaml says so, so a reader
                    # of the row can see *why* it is quiet without going
                    # to look — the reason SNAG-CFG-001 was a defect
                    # rather than a tidy-up.
                    **(
                        {"noise_reason": fault["noise_reason"]}
                        if fault["noise_reason"]
                        else {}
                    ),
                    # Names the family rather than merely flagging that
                    # one exists: a reader who finds an ``info`` row for
                    # a genuine fault needs to know where the loud row
                    # comes from, and ``details['truncated_sources']``'s
                    # rule is that naming beats counting.
                    **(
                        {"covered_by": fault["covered_by"]}
                        if fault["covered_by"]
                        else {}
                    ),
                },
            )
            alerts_raised += 1

        alerts_resolved = await self._resolve_quiet(
            session, set(faults), agent_config.alert_quiet_minutes, now
        )

        if truncated:
            logger.warning(
                "log_read_truncated",
                extra={"sources": truncated, "limit": agent_config.max_entries_per_read},
            )

        return AgentResult(
            findings_count=total_ingested,
            alerts_raised=alerts_raised,
            details={
                "entries_ingested": total_ingested,
                "distinct_faults": len(faults),
                "alerts_resolved": alerts_resolved,
                # Named, not counted: a source at its ceiling is a source
                # whose entries are being dropped, and which one it is
                # decides whether that matters.
                "truncated_sources": truncated,
            },
        )

    async def _read_journal_source(
        self, session, source, limit: int
    ) -> JournalRead:
        """Read one journal source, resuming where the last read stopped.

        Two resume mechanisms, because they fail in different ways.
        ``self._cursors`` is exact and covers the poll-to-poll case, which
        is where the damage was: ``since="2m ago"`` on a 60-second poll
        ingested every unit-journal event **exactly twice** — two copies of
        all 18 ``venture-assistant-backend`` and all 15
        ``sportsanalyser-frontend`` events, doubling every count anything
        downstream computes from ``log_entries``.

        The cursor lives in memory, so a restart loses it.  The floor
        covers that: the newest ``logged_at`` already stored for this
        source, which is durable because it *is* the stored data.  A window
        is still needed for a genuinely first read, and only then.
        """
        cursor = self._cursors.get(source.name)
        since = "5m ago"
        floor: datetime | None = None
        stored_at_floor: set[str] = set()
        if not cursor:
            floor, stored_at_floor = await self._resume_floor(session, source.unit)
            if floor is not None:
                since = since_timestamp(floor)

        read = await read_journal(
            unit=source.unit,
            since=since,
            severity_filter=source.severity_filter,
            user=source.user,
            after_cursor=cursor,
            limit=limit,
            log_format=source.format,
        )
        if read.cursor:
            self._cursors[source.name] = read.cursor
        if floor is None:
            return read
        # The window deliberately re-admits the boundary (see
        # :meth:`_resume_floor`); this is where it is closed again.
        # ``cursor`` and ``truncated`` are carried through untouched — the
        # cursor is journalctl's answer to "where did this read stop",
        # which is a fact about the read and not about what was kept, the
        # same rule that takes it *before* the severity filter.
        return replace(
            read,
            entries=[
                entry
                for entry in read.entries
                if self._is_unstored(entry, floor, stored_at_floor)
            ],
        )

    @staticmethod
    def _is_unstored(
        entry: dict[str, Any], floor: datetime, stored_at_floor: set[str]
    ) -> bool:
        """Is ``entry`` newer than the resume floor, or new at it?

        Strictly-newer is the common case and needs no message
        comparison.  At the floor's own microsecond the timestamp cannot
        decide, so the message does — truncated to
        :data:`STORED_MESSAGE_CHARS` first, because that is the form the
        row holds and comparing the untruncated line against a truncated
        one would read every long message as new on every restart, which
        is this defect wearing a longer name.
        """
        logged_at = entry["logged_at"]
        if logged_at > floor:
            return True
        if logged_at < floor:
            return False
        return entry["message"][:STORED_MESSAGE_CHARS] not in stored_at_floor

    @staticmethod
    async def _resume_floor(session, unit: str) -> tuple[datetime | None, set[str]]:
        """Newest stored ``logged_at`` for ``unit``, and the messages at it.

        Two values rather than one, because the floor alone cannot say
        whether the entry *at* it has been stored — and it always has.
        ``journalctl --since`` is **inclusive** and
        :func:`~sysadmin.monitor.journal.since_timestamp` truncates to
        whole seconds, so a window opened at the newest stored entry
        re-admits that entry and every other one sharing its second.

        Widening the window is deliberate and must stay: the alternative
        — opening at ``floor + 1s`` — trades the duplicate for a **gap**,
        which is the worse failure for a monitor and the reason
        :meth:`_read_journal_source` uses a cursor at all.  So the read
        stays wide and the boundary is settled here instead, against the
        stored rows themselves.

        The message set is scoped to the floor's exact microsecond, which
        is one row on every source measured on this box.  Comparing on
        the message as well as the timestamp keeps a genuine second entry
        stamped in the same microsecond — the Bluetooth pair sits 29 µs
        apart, so a collision is possible — rather than assuming one
        timestamp means one entry.
        """
        result = await session.execute(
            select(func.max(LogEntry.logged_at)).where(LogEntry.source == unit)
        )
        floor = result.scalar_one_or_none()
        if floor is None:
            return None, set()
        stored = await session.execute(
            select(LogEntry.message).where(
                LogEntry.source == unit, LogEntry.logged_at == floor
            )
        )
        return floor, set(stored.scalars().all())

    async def _recent_incidents(
        self, session, title: str, now: datetime, window_hours: float
    ) -> int:
        """How many rows this family already raised under ``title``.

        The count behind :data:`CRITICAL_SIGNATURES`' rule 1 — a first
        sighting is survivable and a repeat is the news.

        Four things decided its shape:

        1. **Rows, never occurrences.**  ``details['occurrences']``
           counts *lines*, and one MODE1 reset writes eleven signatures
           in the same second; a line count would escalate the first
           reset on the strength of its own noise.  A row exists once
           per incident, because ``alert_quiet_minutes`` folds the lines
           of one incident into it and only silence closes it.
        2. **Resolved rows count.**  The previous incident's row is
           closed by definition — this method is only reached when
           ``_open_alerts`` found nothing, which is what makes this a new
           incident rather than a recurrence.  Reading
           :func:`~sysadmin.core.models.alert.unresolved` here would
           count exactly the rows that cannot be here and return ``0``
           for ever, an escalation that can never fire.
        3. **Scoped to this agent.**  ``Alert.agent`` keeps the count off
           any other family that happens to choose the same title — the
           scoping ``_resolve_recovered`` and the estate judge both apply
           for the same reason.
        4. **The scan is accepted and stated rather than indexed
           around.**  There is no index on ``(title, created_at)``;
           ``idx_alerts_active`` is partial on ``resolved = false``,
           which rule 2 has just excluded, so this is a sequential scan —
           **41,644 buffers, 33.3 ms** at this table's 667k rows, the
           figure ``SNAG-AGENT-007`` measured.  It runs once per declared
           incident, not once per poll: this family raised **4** rows in
           thirty days.  An index for a query that runs four times a
           month is a write cost on every alert insert to save 33 ms a
           week.
        """
        cutoff = now - timedelta(hours=window_hours)
        result = await session.execute(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.agent == self.name,
                Alert.title == title,
                Alert.created_at >= cutoff,
            )
        )
        return int(result.scalar_one())

    async def _open_alerts(self, session, titles: set[str]) -> dict[str, Alert]:
        """Unresolved alerts among ``titles``, keyed by title.

        **Bounded by the titles this run raised, deliberately.** The
        obvious query — every unresolved row this agent owns — would have
        materialised 593,814 ORM objects on the first run against the live
        table, so the fix would have fallen over on the backlog it exists
        to end.  A run only needs the rows it might bump, and that set is
        the number of distinct fault signatures in one poll.

        No title-pattern population here, unlike
        :data:`~sysadmin.monitor.agent.RESOLVABLE_TITLE_PATTERNS`: this
        agent raises exactly one kind of alert, so ``agent = 'log_aggregator'``
        already names every row it owns and a pattern list would only be a
        second thing to keep in step with the raise site.
        """
        if not titles:
            return {}
        result = await session.execute(
            select(Alert).where(
                Alert.agent == self.name,
                unresolved(),
                Alert.title.in_(sorted(titles)),
            )
        )
        return {alert.title: alert for alert in result.scalars().all()}

    @staticmethod
    def _record_recurrence(alert: Alert, fault: dict[str, Any], now: datetime) -> None:
        """Fold a repeat occurrence into the open row.

        ``details`` is reassigned rather than mutated in place: SQLAlchemy
        does not track mutation inside a plain JSONB dict, so an in-place
        update would look like it worked and write nothing — and the whole
        resolve depends on ``last_seen_at`` moving.

        **A newly-declared noise entry quietens the open row in place, and
        that is legitimate precisely because it is going down.**
        ``SNAG-ESTATE-010`` records the general fault: dedup skips a
        judgement whose title is already open, so a change that makes a
        family *quieter* never reaches anything standing when it ships.
        This family is the worst case for it — a signature loud enough to
        be worth marking as noise is by definition one that never goes
        quiet, so its row never resolves and the operator's edit would
        take effect approximately never.

        The rule this family wrote down first now lives at
        :func:`~sysadmin.core.escalation.may_quieten_in_place`, beside
        the ban whose asymmetry it depends on, and is **asked** here
        rather than restated: it was the only statement of it for two
        sittings while four other deduplicating families needed the same
        answer, which is how a copied rule drifts in the direction nobody
        notices — this module's own opening argument for living in
        ``core``.  Its rule 1 narrows what this hand-rolled test
        permitted, from any downward step to a step landing on the floor,
        and that costs this family **nothing measured**: ``alert_title``
        interpolates the entry's own severity, so one title carries one
        rung and the only downward move a fault here can make is to
        :data:`NOISE_SEVERITY`, which *is* the floor.

        :data:`COVERED_SIGNATURES` rides the same path for the same
        reason, and it needs it more rather than less: a ``known_noise``
        entry appears when an operator edits config.yaml, which the next
        poll re-reads, whereas a covered signature appears at a *deploy*
        — so the open row it must reach is one this daemon raised loudly
        under the previous release, which is exactly the row a restart
        does not resolve.

        It is deliberately **one-directional**.  Raising severity in place
        here would be Session 39's defect verbatim, so a fault that has
        stopped matching a noise entry keeps its quiet row until silence
        resolves it and the next occurrence raises a loud one — the
        resolve-and-re-raise the ladder does explicitly, arriving by the
        route this family already has.
        """
        details = dict(alert.details or {})
        details["last_seen_at"] = now.isoformat()
        details["occurrences"] = int(details.get("occurrences") or 0) + fault["count"]
        details.setdefault("first_seen_at", details["last_seen_at"])
        details.setdefault("source", fault["source"])
        details["signature"] = fault["signature"]
        if fault["noise_reason"]:
            details["noise_reason"] = fault["noise_reason"]
        else:
            details.pop("noise_reason", None)
        if fault["covered_by"]:
            details["covered_by"] = fault["covered_by"]
        else:
            details.pop("covered_by", None)
        alert.details = details
        alert.message = fault["message"][:500]

        wanted = fault["severity"]
        if may_quieten_in_place(wanted, alert.severity):
            alert.severity = wanted

    async def _resolve_quiet(
        self, session, seen: set[str], quiet_minutes: int, now: datetime
    ) -> int:
        """Resolve open alerts whose fault has not been logged for a while.

        The resolve is **excluded by exact title** for anything this run
        observed, and only then filtered on age.  Both tests do the same
        job — a title seen this run has just had ``last_seen_at`` set to
        ``now`` — and the exclusion is kept because it cannot race a clock,
        which is the caution
        :meth:`sysadmin.monitor.agent.SysAdminAgent._resolve_recovered`
        records for rows raised inside the same transaction.

        ``created_at`` is the fallback for a row with no ``last_seen_at``,
        which is every row raised before this change.  Without it the whole
        pre-existing backlog would be permanently unresolvable — the defect
        this method exists to end, preserved by the fix for it.
        """
        cutoff = now - timedelta(minutes=quiet_minutes)
        last_seen = func.coalesce(
            Alert.details["last_seen_at"].astext.cast(DateTime(timezone=True)),
            Alert.created_at,
        )
        conditions = [
            Alert.agent == self.name,
            unresolved(),
            last_seen < cutoff,
        ]
        if seen:
            conditions.append(Alert.title.notin_(sorted(seen)))

        result = await session.execute(
            update(Alert).where(*conditions).values(resolved=True, resolved_at=now)
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "log_alerts_resolved",
                extra={"agent": self.name, "count": resolved, "quiet_minutes": quiet_minutes},
            )
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": "went quiet", "count": resolved},
            )
        return resolved

    def _read_log_file(
        self, source_name: str, path: str, severity_filter: str, limit: int
    ) -> JournalRead:
        """Read new lines from a log file, tracking byte offset.

        Returns a :class:`~sysadmin.monitor.journal.JournalRead` so a file
        source and a journal source report truncation the same way.  It
        carries no cursor: a byte offset already resumes exactly, and it is
        durable across a restart only in the sense that the file is — a
        rotation resets it, which the size check below detects.
        """
        filepath = Path(path)
        if not filepath.exists():
            return JournalRead(entries=[])

        entries = []
        min_severity = SEVERITY_ORDER.get(severity_filter, 0)

        try:
            file_size = filepath.stat().st_size
            current_offset = self._file_offsets.get(source_name, 0)

            # Detect rotation (file smaller than offset)
            if file_size < current_offset:
                current_offset = 0

            with open(filepath) as f:
                f.seek(current_offset)
                for line in f:
                    parsed = self._parse_log_line(source_name, line.strip())
                    if parsed and SEVERITY_ORDER.get(parsed["severity"], 0) >= min_severity:
                        entries.append(parsed)

                self._file_offsets[source_name] = f.tell()

        except (PermissionError, OSError) as e:
            logger.warning(
                "log_file_read_error",
                extra={"path": path, "error": str(e)},
            )

        # The cap was ``entries[:500]``, silent — the same defect as
        # journalctl's ``-n 500`` and fixed the same way.  Here the
        # *oldest* entries are kept, because the byte offset has already
        # advanced past the lot: dropping the newest would leave them
        # unread for good, whereas a journal cursor can be re-read.
        return JournalRead(entries=entries[:limit], truncated=len(entries) > limit)

    def _parse_log_line(self, source: str, line: str) -> dict[str, Any] | None:
        """Parse a log line into structured data."""
        if not line:
            return None

        # Attempt to detect severity from common patterns
        severity = "info"
        line_upper = line.upper()
        if "CRITICAL" in line_upper or "FATAL" in line_upper:
            severity = "critical"
        elif "ERROR" in line_upper:
            severity = "error"
        elif "WARNING" in line_upper or "WARN" in line_upper:
            severity = "warning"
        elif "DEBUG" in line_upper:
            severity = "debug"

        return {
            "source": source,
            "severity": severity,
            "message": line[:5000],
            "logged_at": datetime.now(UTC),
            "raw_line": line[:2000],
            "metadata": {},
        }
