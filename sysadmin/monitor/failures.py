"""Agents whose runs keep failing — the third way monitoring goes quiet.

``SNAG-DB-001``: for roughly 18 hours of uptime the daemon logged
``agent_run_failed`` every five minutes — 29 times on the last day alone
— and **nothing read it**.  The alerting path was the thing that had
broken, so it could not report its own failure, and ``service_health``
took no rows for 39 hours while the tray went on rendering the last
values it had.

This module is that missing reader.  It is a **sibling of**
:mod:`sysadmin.monitor.stalls`, not an extension of it, and the two
share :mod:`sysadmin.core.escalation`'s ladder rather than a title.

**Why a separate family.**  "Has not run" and "ran and failed" are
different states with different remedies — a stall points at the
scheduler or the process, a failure points at the code or the data —
and they are *mutually exclusive by construction*: a failing agent is
recording runs, so its ``last_run_at`` is fresh and
:func:`~sysadmin.monitor.self_monitor.summarise_agent` never marks it
stalled.  Folding them into one title would put two faults behind one
line in the tray, which is the mistake ``SNAG-AGENT-005`` had already
recorded on the log side: four open rows all reading ``Log error:
kernel`` are indistinguishable to whoever is looking at them.

The suffix is ``agent failing``, and that is load-bearing.
``SysAdminAgent._resolve_recovered`` sweeps open rows whose titles match
``RESOLVABLE_TITLE_PATTERNS`` — ``% degraded``, ``% warning``, ``%
critical``, ``% unreachable``, ``% auto-restarted`` and the resource
thresholds — and closes any this run did not raise.  A family named with
one of those five words as its last word would have its rows closed by
the sysadmin agent **while they were still true**, which is why
``stalls`` is absent from that tuple and why a test pins this title
against it.  The lifecycle owner of a laddered fault must be the module
that owns the ladder.

**This check could not have been written before Session 41.**
``_record_outcome`` used to write ``status='failed'`` into the very
transaction the failure had already destroyed, so the record of the
failure died with the run it recorded and ``agent_runs`` held no
``failed`` rows at all — 39,762 runs, zero failures, which read as
perfect health off a table that could not express the opposite.  Three
transactions fixed that; this reads what they now write.

Four rules, two of them the opposite of the obvious implementation:

1. **The threshold is a count of runs, never a duration** — and that is
   deliberately the opposite unit from ``escalate_after_hours`` in the
   same config section.  ``agent_runs`` records a *run*, not a schedule,
   so "failing for three hours" cannot distinguish an agent that is
   failing from an agent that is not running — and "not running" is
   exactly the question :mod:`~sysadmin.monitor.stalls` owns.  A
   time-based threshold silently re-merges the two families this design
   exists to separate.  The cost is that a count is fast for a
   60-second agent (two minutes) and slow for a daily one (two days);
   that asymmetry is real and is stated here rather than hidden.
2. **Two failures, not one, because the news is "reproducible" and not
   "happened".**  One failure resolves itself on the next run — for
   ``log_aggregator`` that is a warning toast with a 60-second life,
   which is noise.  Two consecutive means the fault survived a retry.
3. **A stalled agent is never also reported as failing.**  An agent that
   failed and then stopped being scheduled satisfies both tests, and
   raising both would put two ``critical`` rows on screen for one dead
   agent.  The stall supersedes: it is the more recent and more complete
   statement, since an agent that is not running is not failing *now*.
4. **The escalation clock runs from when the alarm rang**, exactly as
   for stalls, and for the same reason recorded there — it is the
   telling that failed, so the telling is what the clock measures.

Recovery is a successful run, and it resolves the row outright rather
than walking back down the rungs: an agent that ran clean is not a
quieter fault, it is not a fault.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from estate.text import truncate_at_word

from sysadmin.core.escalation import (
    Ladder,
    Step,
    hours_since,
    humanise_hours,
    step_for,
)

#: Title suffix for consecutive-failure alerts.  The one place it is
#: written — raise, escalate and resolve all derive from
#: :func:`failure_title`, the rule ``_alert_title`` and
#: ``SERVICE_ALERT_KINDS`` already encode: a hand-written resolve pattern
#: that matches nothing fails silently while the table grows.
#:
#: ``failing`` is not one of the five words in
#: ``SERVICE_ALERT_KINDS``, which is what keeps these rows out of
#: ``_resolve_recovered``'s reach.  Renaming this to end in
#: ``degraded``/``warning``/``critical``/``unreachable``/``auto-restarted``
#: would hand the lifecycle to a second owner — see the module docstring.
FAILURE_TITLE_SUFFIX = "agent failing"

#: Quiet at the threshold, loud once the warning has stood unseen.  The
#: same rungs as a stall and for the same reason: ``critical`` is the
#: only severity ``sysadmin_tray/notifications.py`` renders
#: non-transient, and a monitor that has stopped monitoring is worth a
#: notification that is still on screen when the owner comes back.
FAILURE_LADDER = Ladder(quiet="warning", loud="critical")

#: An open row whose ``details`` carry this key belongs to this family.
#: Keyed from ``details`` rather than by parsing the title back apart,
#: matching how :mod:`sysadmin.monitor.stalls` finds its own rows.
FAILURE_DETAIL_KEY = "failing_agent"

#: Ceiling on the exception text carried into the alert message.  An
#: ``str(e)`` can be a whole SQLAlchemy statement plus parameters — the
#: ``CheckViolationError`` behind SNAG-DB-001 runs to several hundred
#: characters — and the tray renders the message on one line.  The full
#: text stays in ``agent_runs.details['error']``, which is where someone
#: diagnosing it will look anyway.
ERROR_CHARS = 160


def failure_title(agent_name: str) -> str:
    """The alert title for ``agent_name``'s run failures."""
    return f"{agent_name} {FAILURE_TITLE_SUFFIX}"


def is_failing(entry: dict[str, Any], failure_threshold: int) -> bool:
    """Whether this self-report entry counts as a failing agent.

    Exposed so the caller's *resolve* set is built from the same
    predicate that decides the raise, rather than re-deriving it.  Two
    copies of an eligibility rule drift in the direction nobody notices
    — the argument ``sysadmin/projects/nudges.py`` records for borrowing
    ``next_action.eligible_candidates`` instead of restating it.

    ``stalled`` wins outright: see rule 3 in the module docstring.
    """
    if not entry.get("enabled"):
        return False
    if entry.get("stalled"):
        return False
    return int(entry.get("consecutive_failures") or 0) >= failure_threshold


@dataclass(frozen=True)
class OpenFailure:
    """The unresolved failure row for one agent, as this module needs it."""

    alert_id: Any
    severity: str
    created_at: datetime


@dataclass(frozen=True)
class FailureAlert:
    """One failing agent, and the rung its alert should be sitting on."""

    agent_name: str
    severity: str
    step: Step
    consecutive_failures: int
    last_error: str | None
    last_run_at: str | None
    #: The configured count, echoed so the message can name its own rule.
    failure_threshold: int
    #: When the *first* alert for this run of failures was raised.
    #: ``None`` on first detection — nothing has been said yet.
    first_alerted_at: datetime | None
    hours_since_first_alert: float | None
    escalate_after_hours: float

    @property
    def title(self) -> str:
        return failure_title(self.agent_name)

    @property
    def message(self) -> str:
        """One line for the tray.

        The escalated form leads with the elapsed time rather than the
        agent name, matching :class:`~sysadmin.monitor.stalls.StallAlert`
        — the reader has already been told what is broken, and the new
        information is that it has stayed broken.
        """
        runs = _plural(self.consecutive_failures, "run")
        if self.step is Step.ESCALATE and self.hours_since_first_alert is not None:
            hours = humanise_hours(self.hours_since_first_alert)
            base = (
                f"Still failing {hours} after the first warning — "
                f"{self.agent_name} has now failed {runs} in a row"
            )
        else:
            base = f"The {self.agent_name} agent has failed {runs} in a row"
        if self.last_error:
            return f"{base}: {self.last_error}"
        return base

    @property
    def details(self) -> dict[str, Any]:
        """Everything the message compressed, for the alerts API.

        ``failing_agent`` is load-bearing rather than decorative — the
        next run finds this agent's open row by testing for that key, so
        an escalated row that omitted it would be invisible and the
        fault would be re-raised from the quiet rung for ever.  The same
        trap :class:`~sysadmin.monitor.stalls.StallAlert` documents.

        ``first_alerted_at`` survives the escalation deliberately: the
        quiet row is resolved when the loud one is raised, so without it
        the critical row could not say when the alarm first rang.
        """
        return {
            FAILURE_DETAIL_KEY: self.agent_name,
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "last_error": self.last_error,
            "last_run_at": self.last_run_at,
            "kind": "agent_failure",
            "rung": self.severity,
            "escalated": self.step is Step.ESCALATE,
            "first_alerted_at": (
                self.first_alerted_at.isoformat() if self.first_alerted_at else None
            ),
            "hours_since_first_alert": (
                round(self.hours_since_first_alert, 2)
                if self.hours_since_first_alert is not None
                else None
            ),
            "escalate_after_hours": self.escalate_after_hours,
        }


def evaluate(
    agent_entries: list[dict[str, Any]],
    open_failures: dict[str, OpenFailure],
    *,
    failure_threshold: int,
    escalate_after_hours: float,
    now: datetime | None = None,
) -> list[FailureAlert]:
    """The failure alerts this run should write, loudest first.

    Args:
        agent_entries: **Every** ``agents`` entry from
            :func:`~sysadmin.monitor.self_monitor.build_self_report`, not
            a pre-filtered subset — the eligibility rules (enabled, not
            stalled, at threshold) live in :func:`is_failing` so that the
            raise and the caller's resolve cannot disagree about which
            agents are in the family.
        open_failures: This agent's unresolved failure rows, keyed by the
            *failing agent's* name.
        failure_threshold: Consecutive failed runs before the family
            speaks.  A count, never a duration — see the module
            docstring.
        escalate_after_hours: Hours a quiet row may stand before the
            fault is restated at :attr:`FAILURE_LADDER.loud`.
        now: Injected for tests; defaults to the current UTC time.

    :attr:`Step.HOLD` entries are **omitted** rather than returned with a
    flag, so a caller cannot forget to check — the same shape
    :func:`sysadmin.monitor.stalls.evaluate` uses.
    """
    at = now or datetime.now(UTC)
    alerts: list[FailureAlert] = []

    for entry in agent_entries:
        name = entry.get("name")
        if not name or not is_failing(entry, failure_threshold):
            continue

        existing = open_failures.get(name)
        elapsed_hours = hours_since(existing.created_at, at) if existing else 0.0

        # Threshold 0: the fault is on the ladder the moment it qualifies.
        # The waiting has already happened — it took `failure_threshold`
        # consecutive failures to get here — and a second delay before
        # saying anything would push back the *quiet* rung, which is not
        # what the escalation gap is for.
        severity = FAILURE_LADDER.severity_for(elapsed_hours, 0.0, escalate_after_hours)
        if severity is None:  # pragma: no cover — unreachable at threshold 0
            continue

        step = step_for(severity, existing.severity if existing else None)
        if step is Step.HOLD:
            continue

        alerts.append(FailureAlert(
            agent_name=name,
            severity=severity,
            step=step,
            consecutive_failures=int(entry.get("consecutive_failures") or 0),
            last_error=_short_error(entry.get("last_error")),
            last_run_at=entry.get("last_run_at"),
            failure_threshold=failure_threshold,
            first_alerted_at=existing.created_at if existing else None,
            hours_since_first_alert=elapsed_hours if existing else None,
            escalate_after_hours=escalate_after_hours,
        ))

    alerts.sort(key=lambda a: (a.severity != "critical", a.agent_name))
    return alerts


def _short_error(error: Any) -> str | None:
    """The recorded exception text, flattened and capped for one line.

    Newlines are collapsed before truncation rather than after: a
    multi-line ``str(e)`` would otherwise spend its whole budget on the
    first line and truncate to something that reads like a complete
    message while omitting the part naming the fault.
    """
    if not error:
        return None
    flattened = " ".join(str(error).split())
    return truncate_at_word(flattened, ERROR_CHARS) if flattened else None


def _plural(count: int, noun: str) -> str:
    """``3, "run"`` → ``"3 runs"``."""
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

