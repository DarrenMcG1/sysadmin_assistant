"""The quiet-then-loud alert ladder, shared by the domains that climb it.

Session 31 built this for idle nudges and Session 39 needed the same
thing for stalled agents.  It lives in ``core`` for the reason
:func:`sysadmin.core.text.strip_markdown` does: ``sysadmin.monitor`` must
not import ``sysadmin.projects`` (``tests/test_import_boundary.py``), so
a rule both domains obey has nowhere else to go.  Copying it was the
alternative, and a copied rule drifts in the direction nobody notices —
the escalation stops escalating on one side and nothing reports the
disagreement.

**Why a ladder at all.**  :meth:`BaseAgent.raise_alert` inserts
unconditionally, so re-raising every run writes one row per run per open
fault: the 1,664-row pile-up this repository has already been through.
Suppressing the re-raise while a row is open fixes that and creates the
opposite failure, which is what Session 39 was called to fix — the alarm
rings **once, at the quietest severity, and is then silent while the
fault persists**, and a warning that fires once is indistinguishable
from one that got fixed.  A ladder is the resolution: not repeats, but a
small number of rungs, each of which is a fresh, louder statement that
the fault is still there.

Two rules, both learned the hard way and both encoded here rather than
described in a comment at each call site:

1. **Escalation resolves the quiet row and raises a loud one** — never
   updates severity in place.  The tray fingerprints notifications as
   ``"{severity}:{title}"`` (``sysadmin_tray/notifications.py``), so an
   in-place change keeps the fingerprint it has already suppressed: the
   escalation is recorded in the database and never spoken, which is the
   one thing an escalation is for.  Two rows also leave the history
   readable — when it went quiet, and when it got loud.
2. **The second rung is a gap, not a multiplier.**  Where the first
   threshold is per-entity (a project's ``idle_nudge_days``, an agent's
   own scan interval), the wait *after* it stays as configured globally.
   A project relaxing its threshold to 21 days escalates at 28, not 42:
   the per-entity knob moves when the clock starts, not how patient the
   escalation is.  A multiplier makes a relaxed entity doubly hard to
   hear from, which is the opposite of what relaxing it asks for.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

#: Severity ordering, matching the tray's ``SEVERITY_LEVELS``.  The only
#: place loudness is compared — ``>`` on the strings themselves would
#: silently order them alphabetically, which puts ``critical`` first and
#: makes every escalation look like a de-escalation.
SEVERITY_ORDER: dict[str, int] = {"info": 0, "warning": 1, "critical": 2}


class Step(StrEnum):
    """What this run should do about one laddered fault.

    A :class:`~enum.StrEnum` rather than a plain ``Enum`` so it can go
    straight into ``agent_runs.details`` and a log line: ``str(Step)``
    yields ``"escalate"``, where ``(str, Enum)`` would render
    ``"Step.ESCALATE"`` into an f-string and put that in the database.
    """

    #: Nothing is open — insert the first row at the wanted severity.
    RAISE = "raise"
    #: A quieter row is open — resolve it and insert a louder one.
    ESCALATE = "escalate"
    #: A row at this severity or louder is already open.  Say nothing.
    HOLD = "hold"


def step_for(wanted: str, open_severity: str | None) -> Step:
    """Which :class:`Step` a fault at ``wanted`` warrants.

    ``open_severity`` is the severity of the unresolved row for this
    fault, or ``None`` when there is none.

    An open row *louder* than ``wanted`` yields :attr:`Step.HOLD` rather
    than a de-escalation.  It happens when a threshold is lowered in
    config with a critical already open, and quietly restating a live
    fault at a lower severity would fire a new, less urgent notification
    about something that has not improved.  De-escalation belongs to
    recovery, which resolves the row outright.
    """
    if open_severity is None:
        return Step.RAISE
    if SEVERITY_ORDER.get(wanted, 0) > SEVERITY_ORDER.get(open_severity, 0):
        return Step.ESCALATE
    return Step.HOLD


@dataclass(frozen=True)
class Ladder:
    """A two-rung severity ladder, quiet then loud.

    The severities are a parameter because the two users start at
    different volumes and that difference is deliberate.  An idle nudge
    opens at ``info`` — an unattended roadmap item is not an incident,
    and a nudge never reaches ``critical`` because criticals break
    through DND by configuration, which is how a monitor gets muted
    wholesale.  A stalled agent opens at ``warning`` and *does* reach
    ``critical``, because ``critical`` is the only severity the tray
    renders non-transient: see :mod:`sysadmin.monitor.stalls`.
    """

    quiet: str
    loud: str

    def severity_for(
        self, elapsed: float, threshold: float, escalation_gap: float
    ) -> str | None:
        """Which rung ``elapsed`` reaches, or ``None`` for neither.

        ``None`` rather than a "no alert" severity because the caller's
        next decision is whether to speak at all, and a sentinel string
        would have to be checked for at every use.

        An ``escalation_gap`` of 0 is legitimate — it means "loud from
        the first rung" — and yields :attr:`loud` at the threshold
        itself.  ``elapsed``, ``threshold`` and the gap must share a
        unit; which unit is the caller's business (days for nudges,
        hours for stalls).
        """
        if elapsed < threshold:
            return None
        if elapsed >= threshold + escalation_gap:
            return self.loud
        return self.quiet


def hours_since(then: datetime, now: datetime) -> float:
    """Hours between ``then`` and ``now``, tolerating a naive ``then``.

    The ladder's clock, and it lives beside the ladder for the reason
    the ladder itself moved here: both families that climb it — stalled
    agents and failing agents — measure the same elapsed time from the
    same column, ``alerts.created_at``, and a third copy is how the two
    stop agreeing.

    That column is ``DateTime(timezone=True)``, so a row read back
    through asyncpg is aware and needs no coercion.  The guard is for
    the values that do **not** come from a round trip: an ``Alert``
    built in a test, and a default applied in Python rather than by the
    database.  Mixing an aware and a naive datetime raises
    ``TypeError`` rather than returning something merely wrong, so an
    unguarded subtraction here would take the whole health check down
    instead of misreporting one row.  UTC is assumed because that is
    what :meth:`BaseAgent.raise_alert` writes.

    Clamped at zero: a row stamped a few milliseconds in the future by
    clock skew is not a negative-age fault, and a negative ``elapsed``
    would read as below every threshold and silently suppress the rung.
    """
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    return max(0.0, (now - then).total_seconds() / 3600.0)


def humanise_hours(hours: float) -> str:
    """``hours`` as a phrase a notification can end a clause with.

    Shared for consistency rather than for economy: "still stalled 2
    days after the first warning" and "still failing 2 days after the
    first warning" are the same sentence about different faults, and an
    owner comparing two toasts should not have to work out whether
    "2 days" and "48 hours" mean the same thing.
    """
    if hours < 1:
        minutes = max(1, int(round(hours * 60)))
        return f"{minutes} minute" if minutes == 1 else f"{minutes} minutes"
    if hours < 48:
        whole = int(round(hours))
        return f"{whole} hour" if whole == 1 else f"{whole} hours"
    days = int(hours // 24)
    return f"{days} day" if days == 1 else f"{days} days"
