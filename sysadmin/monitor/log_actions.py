"""Ranked, executable advice off the log trend (Session 27, Tier 2).

Sibling of :mod:`sysadmin.monitor.log_trends` the way
``units/recommendations.py`` is a sibling of ``units/scan.py``: that
module measures, this one says what to do about it, and keeping them
apart is what stops a threshold moving in one place and a
recommendation's wording disagreeing with it in another.

Pure module.  Takes a :class:`~sysadmin.monitor.log_trends.LogTrendReport`
and the declared noise list, returns :class:`LogRecommendation` rows.

**Advice has to be executable, and this session is the first in this
repository to build the mechanism a recommendation names rather than
naming one that exists.**  Session 48 is the precedent and the warning:
it found ``sysadmin-failed.service`` shipping a row that said "paste the
snippet below" with no snippet, an item no execution sitting can close,
so it returns on every sweep for ever.  Tier 2's scoped example —
*"this warning appeared 400x — add to known-noise or fix it"* — named a
known-noise list that did not exist, and there were exactly two honest
ways out: build it, or stop making the recommendation.  It is built
(``agents.log_aggregator.known_noise``, quietening rather than
suppressing per Session 57), so every row below names a step that can
actually be taken today.

Four rules, three of them the opposite of the obvious implementation:

1. **Kind ranks before volume, and no number is invented to merge
   them.**  A signature seen four times for the first time outranks one
   seen 39,919 times for the fifth week — the ordering
   ``FileRecommendationInfo`` uses when a projected disk-threshold
   crossing outranks every byte total, and for the same reason: novelty
   is the only thing here a reader cannot get by looking at today's
   alerts.  Within a kind, ``occurrences`` orders honestly because it is
   measured.  Unlike ``UnitRecommendationInfo``, which has no score
   field at all, this one has a real currency and says what it is.

2. **A signature already declared as noise earns no recommendation.**
   The obvious implementation keeps it and marks it handled, which turns
   a list of things to do into a list of things done.  What it *does*
   get is a row in the trend, at ``info``, carrying the operator's own
   ``reason`` — visible to anyone who looks, absent from the queue of
   work.

3. **Nothing is recommended as noise on volume alone.**  Volume is what
   makes a fault worth looking at; it is not evidence that it is
   harmless.  A ``NOISE`` row additionally requires the signature to be
   **old and flat** — first seen before the current window and neither
   surging nor new — because a fault that has been shouting the same
   thing at the same rate for a fortnight is the shape an operator can
   actually judge.  Get this wrong and the endpoint recommends silencing
   an outage on its second day.

4. **A low-confidence report recommends nothing about volume.**  Every
   ``NOISE`` row is an argument from a count, and
   :class:`~sysadmin.monitor.log_trends.Confidence` ``LOW`` means the
   count is missing an unknown amount of data.  ``NEW`` rows survive,
   because a first sighting is still a first sighting when the series is
   gappy — a gap can hide a fault, never invent one.  That asymmetry is
   the whole reason confidence is carried rather than being folded into
   the numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from sysadmin.monitor.log_trends import (
    ChangeKind,
    Confidence,
    LogTrendReport,
    SignatureTrend,
)

__all__ = [
    "NOISE_MIN_OCCURRENCES",
    "LogRecommendation",
    "journal_command",
    "RecommendationKind",
    "recommend",
]

#: Occurrences in the current window before a flat, long-standing
#: signature is worth offering as noise.
#:
#: **Invented, and it says so** — the terms ``queue_max_depth`` is
#: declared on in config.yaml.  Tier 2's scoped example said "appeared
#: 400x", which is a number in a sentence rather than a measurement; 100
#: is the round number below it that still clears everything on this box
#: that is plainly not noise.  Measured 2026-08-17, the live population
#: either side of it is unambiguous: the two Bluetooth firmware
#: signatures sit at 39,919 apiece and the next loudest thing on the box
#: is 52.
NOISE_MIN_OCCURRENCES = 100


class RecommendationKind(StrEnum):
    """Ranked in declaration order — see rule 1."""

    #: First seen inside the current window.  Go and look.
    NEW = "new_signature"
    #: Established, and at least :data:`~sysadmin.monitor.log_trends.SURGE_RATIO`
    #: times its previous volume.
    SURGE = "surge"
    #: Loud, old and flat.  Fix it or declare it.
    NOISE = "noise"


_ORDER = {kind: index for index, kind in enumerate(RecommendationKind)}


@dataclass(frozen=True)
class LogRecommendation:
    """One thing to do, with the step that does it."""

    kind: RecommendationKind
    severity: str
    title: str
    detail: str
    #: The step, in words the operator can act on without translating.
    action: str
    source: str
    signature: str
    alert_title: str
    occurrences: int
    #: The exact YAML to paste, for the one kind that has a config edit
    #: as its remedy.  ``None`` everywhere else, and rows that have none
    #: never tell the reader to paste anything — Session 48's rule, which
    #: exists because a row promising an absent snippet can never be
    #: closed.
    snippet: str | None = None


def _noise_snippet(trend: SignatureTrend) -> str:
    """The config.yaml block that quietens this signature.

    Emitted with a placeholder ``reason`` rather than a generated one:
    the field exists to record *the operator's* judgement, and a sentence
    this module wrote would read back as though someone had made a
    decision nobody made.
    """
    return (
        "agents:\n"
        "  log_aggregator:\n"
        "    known_noise:\n"
        f"      - source: {trend.source}\n"
        f"        signature: {trend.signature!r}\n"
        "        reason: \"<why this is safe to quieten>\"\n"
    )


def recommend(
    report: LogTrendReport,
    declared_noise: set[tuple[str, str]] | None = None,
    scopes: dict[str, bool] | None = None,
) -> list[LogRecommendation]:
    """Turn a trend report into ranked, executable advice.

    ``declared_noise`` is the set of ``(source, signature)`` pairs already
    in ``agents.log_aggregator.known_noise``, and ``scopes`` maps each
    declared source to whether it is a user unit.  Both are passed in
    rather than read from config here so this module stays pure and the
    caller owns the reads — ``reliability.py``'s division of labour.
    """
    declared = declared_noise or set()
    out: list[LogRecommendation] = []

    for trend in report.signatures:
        key = (trend.source, trend.signature)
        if key in declared:
            # Rule 2: already judged.  It is still in the trend, still
            # counted, and still carries the operator's reason on its
            # alert row; it is simply not work.
            continue

        if trend.change is ChangeKind.NEW:
            out.append(_new_recommendation(trend, scopes))
        elif trend.change is ChangeKind.SURGED:
            out.append(
                _surge_recommendation(trend, report.previous_start, scopes)
            )
        elif _is_noise_candidate(trend, report.confidence):
            out.append(_noise_recommendation(trend))

    out.sort(key=lambda r: (_ORDER[r.kind], -r.occurrences, r.signature))
    return out


def _is_noise_candidate(trend: SignatureTrend, confidence: Confidence) -> bool:
    """Loud, old and flat — rules 3 and 4.

    ``RETURNED`` counts as flat: it was here before the window and is
    here now, which is the same standing fault seen through a gap.
    ``FALLING`` does too — something on its way out is exactly what an
    operator may want to stop hearing about.  ``NEW`` and ``SURGED`` are
    excluded by construction, since they are their own kinds above.
    """
    if confidence is Confidence.LOW:
        return False
    if trend.current < NOISE_MIN_OCCURRENCES:
        return False
    return trend.change in (
        ChangeKind.STEADY,
        ChangeKind.RISING,
        ChangeKind.FALLING,
        ChangeKind.RETURNED,
    )


def journal_command(
    source: str, since: str, scopes: dict[str, bool] | None = None
) -> str:
    """The journalctl invocation that actually reads ``source``.

    **Written after the first live run emitted three commands that do not
    work**, which is the whole reason this repository drives a new
    surface against real data before believing it.  The draft emitted
    ``journalctl -u <source> --since …`` for everything, and:

    * ``kernel`` is not a unit.  It needs ``-k``, which
      :func:`~sysadmin.monitor.journal.read_journal` has always known and
      this module did not — the same fact, stated twice, one of them
      wrong.
    * **Seven of the fourteen declared log sources are user units**
      (``alfred-backend``, ``sportsanalyser-*``, ``venture-assistant``,
      ``estate-manager-api``, …), and ``journalctl -u`` without
      ``--user`` reads the system journal, where they are not.

    ``scopes`` maps unit name to "is a user unit", built by the caller
    from ``services.yaml`` so this module stays pure.  A source missing
    from it is treated as a **system** unit: that is journalctl's own
    default, and being wrong that way returns "no entries" immediately,
    where the reverse would quietly read a different journal.  It is
    ``SNAG-UNITS-003``'s trade — a command that fails loudly beats one
    that misleads silently.
    """
    if source == "kernel":
        return f"journalctl -k --since '{since}'"
    scope = "--user " if (scopes or {}).get(source) else ""
    return f"journalctl {scope}-u {source} --since '{since}'"


def _new_recommendation(
    trend: SignatureTrend, scopes: dict[str, bool] | None = None
) -> LogRecommendation:
    return LogRecommendation(
        kind=RecommendationKind.NEW,
        severity="risk",
        title=f"New fault from {trend.source}",
        detail=(
            f"First seen {trend.first_seen:%Y-%m-%d %H:%M}, "
            f"{trend.current} occurrence(s) since. "
            f"Latest line: {trend.sample[:200]}"
        ),
        action="Read the source: " + journal_command(
            trend.source, f"{trend.first_seen:%Y-%m-%d %H:%M}", scopes
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
    )


def _surge_recommendation(
    trend: SignatureTrend,
    previous_start: datetime,
    scopes: dict[str, bool] | None = None,
) -> LogRecommendation:
    ratio = f"{trend.ratio:.1f}x" if trend.ratio is not None else "sharply"
    return LogRecommendation(
        kind=RecommendationKind.SURGE,
        severity="risk",
        title=f"{trend.source} fault up {ratio}",
        detail=(
            f"{trend.previous} occurrence(s) last window, {trend.current} this one. "
            f"Latest line: {trend.sample[:200]}"
        ),
        # No ``--grep``: the draft grepped on the *normalised* signature,
        # whose ``N`` placeholders match no real line, and its first token
        # is usually the unit's own name — which matches every line in its
        # own journal. The window plus the sample in ``detail`` is what a
        # reader actually needs.
        action="Compare the two windows: " + journal_command(
            trend.source, f"{previous_start:%Y-%m-%d %H:%M}", scopes
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
    )


def _noise_recommendation(trend: SignatureTrend) -> LogRecommendation:
    return LogRecommendation(
        kind=RecommendationKind.NOISE,
        severity="advice",
        title=f"{trend.source}: {trend.current} occurrences, unchanged",
        detail=(
            f"{trend.current} this window against {trend.previous} last, "
            f"{trend.total} in all retained history since "
            f"{trend.first_seen:%Y-%m-%d}. Fix it, or declare it noise and "
            f"it drops to info — it keeps being counted either way."
        ),
        action=(
            "Add the block below to config.yaml, then reload without a "
            "restart: POST /api/sysadmin/reload"
        ),
        source=trend.source,
        signature=trend.signature,
        alert_title=trend.alert_title,
        occurrences=trend.current,
        snippet=_noise_snippet(trend),
    )
