"""The agent-to-timer handover, asserted rather than remembered.

``SNAG-SVC-002`` filed two families asking one question of two subjects:
:mod:`sysadmin.monitor.stalls` asks *has this agent run?* and
:func:`sysadmin.monitor.service_recommendations._timer_stale_row` asks
*has this timer fired?*, with no cross-reference.  The entry's second
bullet says they do not overlap here and calls that "a property of this
box rather than of the design".

**Measured 2026-09-03, that reason is wrong and the box says so.**  Ten
services are declared ``kind: timer``; none intersects ``AGENT_NAMES``
or :func:`~sysadmin.monitor.self_monitor.agent_schedules` by name, by
unit stem, or by what its ``ExecStart`` actually runs, and live the two
families name **zero** common subjects.  But the scenario the entry
treats as hypothetical has already happened.  On 2026-08-08 commit
``5cc04cc`` installed ``sysadmin-organiser.timer``, declared it in
services.yaml as ``kind: timer``, and set
``agents.project_organiser.enabled: false`` — for the *same subject* the
daemon was scheduling as an agent.  Its message states the rule this
module now enforces:

    Monitoring the timer **replaces** the self-monitor's stall watch
    over that agent.  A disabled agent is correctly not flagged as
    stalled, so something else had to be able to tell whether the scan
    ran.

So the disjointness is a **handover**, performed deliberately, once, on
the one subject that could have been both — and then made moot by
ADR-0005 when the agent left for the estate's 8400 service.  What
carried it was a config flag, which is why it is fragile, and
:func:`~sysadmin.monitor.self_monitor.agent_schedules`' own docstring
already says so in as many words: *"it made a config line load-bearing
for a structural fact"*.

Six rules, four of them the opposite of the obvious implementation:

1. **The link is declared on the timer, never on the agent.**  A
   ``services.yaml`` timer entry is what an author *adds* when moving a
   job out of process; the agent side is what they delete.  Declaring it
   where the typing already happens is the only placement that gets
   written down, and it is the side that carries ``extra="forbid"`` — so
   ``agentt:`` fails at load rather than being dropped, which is the
   half ``SNAG-CFG-004`` does not have on the config.yaml side.

2. **Two rungs, and the quiet one is the precedent rather than the
   hypothetical.**  ``breached`` is a declared link naming an agent this
   daemon schedules *and* has enabled: the box runs the job twice and
   both families speak about it.  ``flag_carried`` is a link naming an
   agent still in ``agent_schedules`` but disabled — silent today,
   because :func:`summarise_agent` gates on ``schedule.enabled``, and one
   edit from a breach.  Collapsing them would report the historic state
   as a fault (it was not; it was the handover working) or the double-run
   as tidy (it is not).

3. **Both sets are read, because they answer different questions.**
   ``AGENT_NAMES`` is what the ``chk_alert_agent`` constraint admits
   *ever* and carries retired names; ``agent_schedules`` is what this
   daemon schedules *today*.  A link naming a retired agent —
   ``project_organiser`` on ``estate-manager-scan-timer`` — is the
   **completed** handover and is silent, which is the whole point of the
   key.  A link naming neither is a typo, reported as ``unknown_agents``
   rather than skipped: a handover asserted about an agent that does not
   exist is not a handover.

4. **It reports and never refuses** — :mod:`sysadmin.core.config_keys`
   rule 1, and settled by the shape of the mechanism rather than by a
   flag someone could flip: a walker returns a list.  ``schema_guard``'s
   posture does not transfer, and the cost side is why.  That guard
   refuses because serving against the wrong schema is worse than not
   serving; the state this one detects costs a job run twice and one
   extra alert row, and a boot refused over it is ``SNAG-DB-005``'s
   twenty-three hours bought for a tidiness finding.

5. **``walked`` is the difference between clean and blind.**  A report
   that could not read either half returns no findings and must not be
   read as agreement — ``ports_checked``'s rule, one file over.

6. **Its reach is exactly what was declared, and that is the filed
   cost.**  An author who moves an agent to a timer and writes no
   ``agent:`` key is invisible here.  Deriving the link instead — reading
   ``ExecStart`` and recognising this repository's own console scripts —
   needs a subprocess in a module whose no-subprocess promise is
   load-bearing next door, and recognises an application where this
   honours a statement.  ``SNAG-SVC-005`` carries it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sysadmin.core.config import AppConfig
from sysadmin.monitor.self_monitor import AGENT_NAMES, agent_schedules
from sysadmin.monitor.services import ServicesFile

#: The one ``kind`` an ``agent:`` link may be declared on.  A oneshot is
#: never checked and a ``systemd`` entry asserts a running process, so
#: neither can stand in for a schedule — and services.yaml's own comment
#: already says a oneshot is watched *through its timer*.
LINKABLE_KIND = "timer"


@dataclass(frozen=True)
class HandoverReport:
    """What the agent-to-timer handover looks like in the files on disk.

    ``walked`` is first because every other field is meaningless without
    it: an empty ``breached`` beside ``walked=False`` says the check
    could not look, which is not the same answer as "nothing is wrong".
    """

    walked: bool = False
    #: ``"<service> -> <agent>"`` for a link whose agent is scheduled and
    #: enabled.  The box runs the job twice; both families speak.
    breached: list[str] = field(default_factory=list)
    #: ``"<service> -> <agent>"`` for a link whose agent is still in
    #: ``agent_schedules`` but disabled — the handover held by a config
    #: line rather than by structure.
    flag_carried: list[str] = field(default_factory=list)
    #: ``"<service> -> <agent>"`` for a link naming no known agent.
    unknown_agents: list[str] = field(default_factory=list)
    #: Links declared at all, so zero findings can be told apart from
    #: zero declarations.
    declared: int = 0

    @property
    def clean(self) -> bool:
        """Whether the walk ran and found nothing to say."""
        return self.walked and not (
            self.breached or self.flag_carried or self.unknown_agents
        )


def handover_report(services: ServicesFile, config: AppConfig) -> HandoverReport:
    """Judge every declared agent-to-timer handover in the two files.

    Pure: no I/O, no database, no subprocess. The caller supplies both
    halves already parsed, which is what lets the lifespan and the reload
    ask the same question of the configuration each is about to install
    rather than of the one currently being served.
    """
    schedules = agent_schedules(config)
    known = set(AGENT_NAMES)

    breached: list[str] = []
    flag_carried: list[str] = []
    unknown: list[str] = []
    declared = 0

    for entry in services.services:
        agent = entry.agent
        if agent is None:
            continue
        declared += 1
        pair = f"{entry.name} -> {agent}"
        schedule = schedules.get(agent)
        if schedule is not None:
            # Rule 2. The rung is the flag, and the flag is the fragility.
            (breached if schedule.enabled else flag_carried).append(pair)
        elif agent not in known:
            # Rule 3. Not in either set: nothing was handed over.
            unknown.append(pair)
        # Otherwise: a retired agent this daemon no longer schedules —
        # the completed handover, and the reason the key exists.

    return HandoverReport(
        walked=True,
        breached=breached,
        flag_carried=flag_carried,
        unknown_agents=unknown,
        declared=declared,
    )
