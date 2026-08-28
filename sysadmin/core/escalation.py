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

**Two rungs, and a third was measured and refused** (Session 53,
``SNAG-ESTATE-003``).  The families that deduplicate but own no ladder —
the estate judge, :mod:`sysadmin.monitor.collation`, the unit sweep's
roll-up — have the same defect this module exists to fix, and the
obvious next move is a rung that repeats without reaching ``critical``,
which is reserved for a fault on this box.  It cannot work.  The tray
fingerprints on ``"{severity}:{title}"`` and holds an episode open for
as long as that pair keeps appearing in a poll, so a rung changing
neither is **inaudible whatever the database records**: measured, a
resolved row replaced by a fresh one carrying a new message produced no
notification at all.  The two audible repeats are a severity change and
a forked title — and a forked title is forbidden, the title being the
identity key for dedup, for the resolve and for the tray alike.

So a repeat at an unchanged severity is a *notification* decision, and
it is implemented where notification policy already lives, as
``reminder_hours`` in ``sysadmin_tray/notifications.py``.  Escalation
stays what it is here: a small number of rungs, each a **louder**
statement.  Anyone reaching for a third rung should read
``NotificationPolicy._reminder`` first.
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


#: The quietest rung there is.
#:
#: Derived from :data:`SEVERITY_ORDER` rather than written as ``"info"``
#: — ``max_priority_for`` against ``PRIORITY_MAP``'s rule.  The two would
#: be a second statement of one fact, and the direction they drift in is
#: the one nobody notices: a fourth rung added below ``info`` would leave
#: this constant naming a rung that is no longer the floor, and
#: :func:`may_quieten_in_place` would then permit an audible write while
#: still reading as though it did not.
QUIETEST_SEVERITY: str = min(SEVERITY_ORDER, key=lambda rung: SEVERITY_ORDER[rung])


def may_quieten_in_place(wanted: str, open_severity: str) -> bool:
    """May a held row be rewritten from ``open_severity`` to ``wanted``?

    ``SNAG-ESTATE-010``'s surviving half.  Every family that
    deduplicates on an open title skips a judgement whose title is
    already open, so **a change that makes a family quieter is silent on
    every fault standing when it ships** — it applies only to faults
    raised afterwards.  Session 57 shipped
    :data:`~sysadmin.estate.judgements.TRANSIENT_HOLDER_SEVERITY` and the
    two rows it was written for stayed at ``warning`` for the life of a
    VS Code window, restated at that rung by ``reminder_hours``
    throughout.

    **Session 39's ban on in-place severity changes is asymmetric, and
    the reason it exists is what makes the reverse safe.**  It bans an
    in-place *escalation* because an escalation must be **heard**: the
    tray fingerprints on ``{severity}:{title}``
    (``sysadmin_tray/notifications.py``), so bumping the column keeps a
    fingerprint the tray has already suppressed and the escalation is
    recorded in the database and never spoken.  A quietening wants
    exactly that outcome.  The mechanism that makes escalation fail is
    what makes this work, so it is one-directional by construction —
    which is
    :meth:`~sysadmin.monitor.log_aggregator.LogAggregatorAgent._record_recurrence`'s
    argument, generalised here rather than left as a rule one family
    states and four obey by accident.

    Four rules, three of them the opposite of the obvious
    implementation:

    1. **The floor is the only destination, not merely a downward
       step.**  "Going down is safe" is the obvious reading of the
       asymmetry above and it is too broad by one rung: ``critical`` →
       ``warning`` in place hands the tray a fingerprint it *will*
       speak, so the quietening arrives as a fresh, less urgent
       notification about a fault that has not improved — which is the
       refusal :func:`step_for` already states in its own docstring, met
       from the other side.  Only :data:`QUIETEST_SEVERITY` is
       inaudible-or-asked-for: it is below ``tray.notify_min_severity``
       on this box (``warning``), and an operator who lowers that knob to
       the floor has asked to hear reclassifications.
    2. **The tray's threshold is not read, and it could not be.**  The
       obvious gate is "quieter than ``notify_min_severity``", which
       makes the daemon a second reader of a policy the tray owns — and
       the backend cannot see that key in any case: ``AppConfig``
       parses ``notifications.tray:``
       (:class:`~sysadmin.core.config.TrayNotificationsConfig`, "the
       slice the *backend* needs") while ``notify_min_severity`` lives in
       the top-level ``tray:`` section the tray parses for itself.
       Adding it would be a config leaf whose only reader is a rule that
       does not need it.
    3. **It answers about a rung, never about a row.**  Whether the row
       is worth rewriting at all — has the sentence moved, is this
       family even allowed to correct itself — belongs to
       :meth:`~sysadmin.core.agent.BaseAgent.refresh_alert`, which owns
       the comparison and the write for all three deduplicating callers.
       A predicate that also read an :class:`~sysadmin.core.models.alert.Alert`
       would put half of that decision in ``core`` and half in the base
       class.
    4. **An unknown rung is refused rather than defaulted.**
       :data:`SEVERITY_ORDER`'s ``.get(..., 0)`` reads an unrecognised
       string as ``info`` elsewhere, which is right where the question is
       "how loud is this" and wrong here: it would read a typo as the
       floor and permit a write to it.  ``chk_alert_severity`` admits
       three values, so a fourth is a bug and the safe answer to a bug is
       to leave the standing row alone.

    Returns:
        ``True`` when ``wanted`` is the quietest rung and the row is
        currently louder.  ``False`` for an escalation, for an unchanged
        rung, and for any downward step that stops short of the floor.
    """
    if wanted not in SEVERITY_ORDER or open_severity not in SEVERITY_ORDER:
        return False
    if wanted != QUIETEST_SEVERITY:
        return False
    return SEVERITY_ORDER[wanted] < SEVERITY_ORDER[open_severity]


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
