"""Week-on-week trends over log entries, keyed on fault signature.

Session 27, Tier 1.  The log aggregator could say what is happening *now*
— :mod:`sysadmin.monitor.log_signature` gave it one open alert per
distinct fault and killed a 598,091-row pile-up — but nothing could say
whether a fault is **new**, or whether one that has been there all along
is getting worse.  A monitor that only reports the present tense makes
every recurring fault look like today's news.

Pure module: no DB access, no FastAPI.  It takes
:class:`MessageGroup` rows — one per distinct ``(source, severity,
message)``, which is what the caller's ``GROUP BY`` produces — and
returns a :class:`LogTrendReport`.  ``reliability.py``'s shape, for
``reliability.py``'s reason: an ORM row and a hand-written fixture make
the same input, so every rule below is testable without a database.

Four rules, three of them the opposite of the obvious implementation and
all four settled by measuring the live table rather than by reasoning
about it.

1. **The signature is computed here, in Python, over rows the database
   has already grouped.**  The obvious implementation normalises in SQL
   with ``regexp_replace`` and groups on the result — one pass, no
   Python.  It is a **second implementation of the identity the alert
   family is keyed on**, and it would drift from
   :func:`~sysadmin.monitor.log_signature.signature` exactly as a regex
   over ``alembic/versions/*.py`` drifts from the revision graph
   (``core/schema_guard.py``'s rule).  A trend report naming signatures
   the ``alerts`` table has never heard of is worse than no trend report.

   What makes the honest version affordable is measured, not assumed:
   **626,906 rows collapse to 44 distinct messages, in 91 ms** on the
   live table.  The reduction is a *property of this data*, though, not
   a bound — a service embedding a request id in every line has one
   group per line — so the caller caps the grouped set and says so.
   Note the anti-correlation: the messages that do **not** collapse under
   ``GROUP BY message`` are precisely the ones the signature helps most.

2. **"New" is measured against all retained history, never against the
   previous window.**  The obvious test is ``previous == 0``, and the
   live table refutes it in one row: the Bluetooth firmware signature
   reads ``current=39,919, previous=0`` today and has been storming in
   bursts since at least 2026-07-15 — five separate days of it inside the
   retained window.  It would have headed a "new errors this week" list
   on its fifth outbreak.  A fault is new when it was **first seen**
   inside the current window; ``previous == 0`` says only that it was
   quiet last week, which is a different and much less interesting fact
   (it is :attr:`ChangeKind.RETURNED`).

3. **A gap in the series lowers confidence; it never becomes a trend.**
   ``reliability.py``'s rule 4, reused rather than rediscovered — a
   window in which the monitor was down measures this application's
   uptime and reports it as the estate's error rate.  Measured: the log
   aggregator's poll coverage across the last 14 days ranges from 46 %
   to 99.9 %, with the previous window at ~73 % and the current at ~91 %,
   so a raw count ratio carries a ~1.25× artefact before any fault moves.

   But **poll count is the proxy and truncation is the signal**, and
   that ordering is the opposite of the obvious one.  A missed poll
   normally loses nothing: the journal cursor resumes where it stopped,
   so the next poll catches up.  Data is lost only when a catch-up read
   hits ``max_entries_per_read`` and the cursor jumps past what it did
   not return — which the agent already records as
   ``details['truncated_sources']``.  So truncation is decisive and a
   thin poll series is merely suspicious, and counting polls alone would
   charge a fully-recovered gap as data loss.

   **Decisive in proportion, not as a flag** (2026-08-17).  The first
   version returned ``LOW`` on ``runs_truncated > 0``, which made one
   catch-up read after one restart suppress every volume argument for
   fourteen days — measured, 16 of the 120 truncations in the window are
   exactly that, one per restart, each naming four or five sources at
   once because ``_resume_floor()`` sizes a source's catch-up window by
   *how long since it last stored a row* rather than by how long the
   daemon was down.  A source that logs one warning a week is read a
   week back on every restart.  The gate is now
   :data:`TRUNCATION_LOW_FRACTION` over the **instrumented** reads, and
   it is safe to have one because truncation is one-directional: it
   drops entries, so it can only make a count too low.

4. **Counts are never scaled by coverage.**  Dividing by observed time
   would produce a rate that looks precise and is not: the cursor makes
   ingestion non-proportional to poll count (rule 3), so the divisor is
   wrong in an unknown direction.  ``reliability.py`` made the same
   choice for the same reason — report the deduction, lower the
   confidence, and let the reader see both numbers.

The population is **wider than the alert family's**.  The agent raises
on ``error`` and ``critical`` only; this covers ``warning`` too, because
Tier 2's whole question is "this warning appeared 400× — is it noise or
a fault?", and a severity the trend cannot see is a question it cannot
answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from sysadmin.monitor.log_signature import alert_title, signature

__all__ = [
    "LOW_COVERAGE_FRACTION",
    "RATIO_MIN_COUNT",
    "SURGE_RATIO",
    "TRUNCATION_LOW_FRACTION",
    "ChangeKind",
    "Confidence",
    "LogTrendReport",
    "MessageGroup",
    "SignatureTrend",
    "SourceTrend",
    "WindowCoverage",
    "build_report",
]

#: A signature must reach this many occurrences in a window before a
#: ratio is computed for it.  One occurrence becoming three is a 3×
#: "surge" and two events; the floor is what stops the loudest thing on
#: the page being the quietest thing in the logs.
#:
#: **Invented, not derived**, and it says so here for the reason
#: ``queue_max_depth`` does in config.yaml: nothing on this box has ever
#: measured a log trend, so there is no prior observation to derive it
#: from.  Revisit once the endpoint has a month of real readings.
RATIO_MIN_COUNT = 10

#: Ratio of current to previous at which a signature is ``SURGED`` rather
#: than ``RISING``.  Doubling is a round number chosen for being one, and
#: is invented on the same terms as :data:`RATIO_MIN_COUNT`.
SURGE_RATIO = 2.0

#: Below this fraction of expected polls a window is too gappy to compare
#: — the same number and the same reasoning as
#: ``reliability.LOW_COVERAGE_FRACTION``, kept as a separate constant
#: because it governs a different measurement: there, the fraction of
#: expected *health checks*; here, of expected *journal reads*.  Sharing
#: one constant would make a future change to either silently change the
#: other.
LOW_COVERAGE_FRACTION = 0.5

#: Fraction of *instrumented* reads that may have hit their ceiling before
#: the report stops supporting an argument from a count.  Above this the
#: report is ``LOW``; at or below it truncation costs ``HIGH`` but not
#: ``MEDIUM``.
#:
#: What this bounds is **not** the error in a count.  A truncated read
#: drops entries, so it can only make a count too *low* — and a ``NOISE``
#: row argues that a signature is loud, which a floor already
#: establishes.  What it bounds is the chance that a depressed *current*
#: window moves a signature across a kind boundary: a genuine
#: :attr:`ChangeKind.SURGED` reading as :attr:`ChangeKind.STEADY` is
#: noise-eligible, and that is the failure rule 4 exists to prevent.
#:
#: **Invented, on :data:`RATIO_MIN_COUNT`'s terms**, but with the live
#: numbers to hand.  Measured 2026-08-17: **120 truncated of 7,000
#: instrumented reads across the 14-day window — 1.7 %** — of which 103
#: are one kernel storm on 2026-08-12 and 16 are the first poll after a
#: restart.  The storm's own day is 104 of 1,434, **7.3 %**.  So 5 % puts
#: a fortnight containing one bounded storm at ``MEDIUM`` and a window
#: that is mostly storm at ``LOW``, which is the discrimination the
#: binary flag could not make.  Revisit once a post-``-p`` fortnight has
#: been observed.
TRUNCATION_LOW_FRACTION = 0.05


class Confidence(StrEnum):
    """How much of the window was actually observed.

    ``LOW``
        More than :data:`TRUNCATION_LOW_FRACTION` of the instrumented
        reads dropped data, or nothing was observed at all.  Anything
        acting on this report must read it — ``reliability.py``'s rule,
        and for the same reason.
    ``MEDIUM``
        The poll series has gaps, or a bounded share of reads truncated.
        Either way what is missing is small enough that a count still
        supports an argument — and since truncation only ever *lowers* a
        count, the argument it supports is a floor.
    ``HIGH``
        Both windows fully polled, no truncation at all.  Unchanged by
        the move to a proportional gate: ``HIGH`` has never meant
        "nearly complete" and does not start now.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChangeKind(StrEnum):
    """What happened to a signature between the two windows.

    ``NEW`` is the only one that consults history outside the two
    windows, and that is rule 2: everything else is a comparison, while
    "new" is a claim about a first sighting.
    """

    NEW = "new"
    #: Seen before the current window, absent from the previous one.  Not
    #: ``NEW`` — the distinction rule 2 exists to draw.
    RETURNED = "returned"
    SURGED = "surged"
    RISING = "rising"
    STEADY = "steady"
    FALLING = "falling"
    #: Present in the previous window, silent in this one.
    GONE = "gone"


@dataclass(frozen=True)
class MessageGroup:
    """One ``(source, severity, message)`` group, as the caller's query returns it.

    ``current`` and ``previous`` are conditional aggregates over the
    **same** pass, never two queries.  Two window queries can each be
    capped independently, and a signature ranked first this week and five
    hundredth last week would then read its previous count as zero — a
    truncation artefact wearing rule 2's clothes.
    """

    source: str
    severity: str
    message: str
    current: int
    previous: int
    total: int
    first_seen: datetime
    last_seen: datetime


@dataclass(frozen=True)
class WindowCoverage:
    """How thoroughly the agent observed the period the report covers.

    ``runs_expected`` is derived from the poll interval rather than
    passed in as a judgement, so a config change moves it without anyone
    remembering to.

    ``runs_instrumented`` is the denominator :attr:`truncated_fraction`
    divides by, and it is **not** ``runs_observed``.  A run can only
    report truncation if it recorded ``details['truncated_sources']`` at
    all, and that field first appears on the run at 2026-08-12 17:31 —
    10,730 of the 17,730 runs in today's window predate it.  Dividing by
    every observed run reads **0.68 %** where the truth is **1.71 %**: a
    rate that looks precise with a divisor wrong in a known direction,
    which is rule 4's own objection turned on the confidence calculation
    itself.  The dilution self-corrects as those runs age out of the
    window, and that is exactly why it must not be left — a number that
    is wrong today and right next week is one nobody re-checks.
    """

    runs_observed: int = 0
    runs_expected: int = 0
    runs_truncated: int = 0
    #: Runs that *could* have reported truncation.  Zero means the caller
    #: does not know, which is a different thing from zero truncation —
    #: see :attr:`truncated_fraction`.
    runs_instrumented: int = 0

    @property
    def fraction(self) -> float:
        if self.runs_expected <= 0:
            return 0.0
        return min(1.0, self.runs_observed / self.runs_expected)

    @property
    def truncated_fraction(self) -> float:
        """Share of instrumented reads that hit their ceiling.

        **Fails closed on not-knowing**, ``schema_guard``'s posture
        rather than ``collation.py``'s: a caller that reports truncation
        without a denominator gets ``1.0`` and therefore the binary
        behaviour this property replaced.  Serving a volume argument off
        a report whose completeness is unmeasured is the thing rule 4
        exists to refuse, so the safe answer is the pessimistic one.
        """
        if self.runs_truncated <= 0:
            return 0.0
        if self.runs_instrumented <= 0:
            return 1.0
        return min(1.0, self.runs_truncated / self.runs_instrumented)


@dataclass(frozen=True)
class SignatureTrend:
    """One fault signature, across both windows."""

    signature: str
    #: The identity the *alert* family uses, so a reader can match a row
    #: here against a row in ``alerts`` without re-deriving anything.
    alert_title: str
    source: str
    severity: str
    #: The most recent verbatim line, kept because normalisation drops
    #: the errno the signature deliberately does not distinguish.
    sample: str
    current: int
    previous: int
    total: int
    first_seen: datetime
    last_seen: datetime
    change: ChangeKind
    #: ``current / previous``, or ``None`` when either window is too thin
    #: for the ratio to mean anything (:data:`RATIO_MIN_COUNT`).
    ratio: float | None = None

    @property
    def is_new(self) -> bool:
        return self.change is ChangeKind.NEW


@dataclass(frozen=True)
class SourceTrend:
    """Per-source volume, the axis Tier 1 was scoped around.

    Errors and warnings are carried separately rather than summed: a
    source whose warnings doubled while its errors vanished has not "got
    50 % worse", and one number cannot say so.
    """

    source: str
    current_errors: int = 0
    previous_errors: int = 0
    current_warnings: int = 0
    previous_warnings: int = 0
    signatures: int = 0
    new_signatures: int = 0

    @property
    def error_delta(self) -> int:
        return self.current_errors - self.previous_errors


@dataclass(frozen=True)
class LogTrendReport:
    """The whole comparison."""

    window_days: int
    window_start: datetime
    previous_start: datetime
    generated_at: datetime
    confidence: Confidence
    signatures: list[SignatureTrend] = field(default_factory=list)
    sources: list[SourceTrend] = field(default_factory=list)
    coverage: WindowCoverage = field(default_factory=WindowCoverage)
    #: True when the caller's grouped query hit its cap, so these
    #: rankings are over a subset.  ``ports_checked``'s rule: zero
    #: findings because clean must never be served as the same answer as
    #: zero findings because blind.
    truncated: bool = False
    groups_read: int = 0

    @property
    def new_signatures(self) -> list[SignatureTrend]:
        """Signatures first seen inside the current window."""
        return [s for s in self.signatures if s.is_new]


def _classify(
    current: int, previous: int, first_seen: datetime, window_start: datetime
) -> tuple[ChangeKind, float | None]:
    """Decide what happened to one signature, and whether a ratio is honest.

    Order matters.  ``NEW`` is tested **first and on a different input**
    — a first sighting, not a comparison — because a genuinely new fault
    also satisfies ``previous == 0``, and letting ``RETURNED`` win would
    collapse rule 2's whole distinction.
    """
    if first_seen >= window_start:
        return ChangeKind.NEW, None
    if current == 0:
        return ChangeKind.GONE, None
    if previous == 0:
        return ChangeKind.RETURNED, None

    # Both windows are non-empty, but a ratio over a handful of events is
    # arithmetic rather than evidence.
    if current < RATIO_MIN_COUNT and previous < RATIO_MIN_COUNT:
        return ChangeKind.STEADY, None

    ratio = current / previous
    if ratio >= SURGE_RATIO:
        return ChangeKind.SURGED, ratio
    if ratio > 1.0:
        return ChangeKind.RISING, ratio
    if ratio < 1.0:
        return ChangeKind.FALLING, ratio
    return ChangeKind.STEADY, ratio


def _confidence(coverage: WindowCoverage) -> Confidence:
    """Truncation is decisive in proportion; a thin poll series is only suspicious.

    See rule 3.  A missed poll normally costs nothing because the cursor
    resumes, so poll count alone cannot demote a window past ``MEDIUM``.

    Truncation used to be binary — ``runs_truncated > 0`` returned
    ``LOW``, so **one** catch-up read pinned the whole report for
    fourteen days.  Three things make that the wrong shape, and the
    third is why the constant can exist at all:

    1. It cannot distinguish 1.7 % of reads from 100 % of them, and
       those are not the same evidential state.
    2. The remaining population is bounded and nameable.  After the
       2026-08-17 ceiling fix the only reads that lose data are ones
       where a source produced more than ``max_entries_per_read``
       *storable* entries since it last stored one — which is a
       sustained fault, not a busy journal.
    3. **A truncated read can only depress a count.**  So a volume
       argument survives it, exactly as a first sighting survives a gap
       (rule 4's asymmetry, one step further).  What does *not* survive
       is a ratio, because a depressed current window can move a
       ``SURGED`` signature into the noise-eligible ``STEADY`` band —
       and bounding that is what :data:`TRUNCATION_LOW_FRACTION` is for.

    ``HIGH`` is deliberately untouched: it still means nothing was lost
    and nothing was missed.  All that moved is the floor beneath it, so
    a report that loses a little is ``MEDIUM`` rather than ``LOW`` — and
    ``MEDIUM`` is what :func:`~sysadmin.monitor.log_actions.recommend`
    already treats as good enough for a count.
    """
    if coverage.runs_expected <= 0:
        return Confidence.LOW
    if coverage.truncated_fraction > TRUNCATION_LOW_FRACTION:
        return Confidence.LOW
    if coverage.runs_truncated > 0:
        return Confidence.MEDIUM
    if coverage.fraction < LOW_COVERAGE_FRACTION:
        return Confidence.MEDIUM
    if coverage.fraction < 1.0:
        return Confidence.MEDIUM
    return Confidence.HIGH


def build_report(
    groups: list[MessageGroup],
    *,
    window_days: int,
    window_start: datetime,
    previous_start: datetime,
    generated_at: datetime,
    coverage: WindowCoverage | None = None,
    truncated: bool = False,
) -> LogTrendReport:
    """Fold message groups into signature and source trends.

    The re-aggregation is the whole point of the module: several distinct
    messages share one signature, and the live table is full of them —
    ``INFO: task X blocked for more than 122 seconds`` and its ``245``
    twin are two messages and one fault, as are the four
    ``Found left-over process <pid>`` lines and the two
    ``device not accepting address N, error -71``.
    """
    coverage = coverage or WindowCoverage()

    # signature key -> accumulator.  Severity is part of the key because
    # ``alert_title`` includes it: one signature logged at warning by one
    # service and at error by another is two alert rows, and a trend
    # report that merged them could not be matched against either.
    acc: dict[tuple[str, str, str], dict] = {}
    for group in groups:
        sig = signature(group.message)
        key = (group.source, group.severity, sig)
        entry = acc.get(key)
        if entry is None:
            acc[key] = {
                "current": group.current,
                "previous": group.previous,
                "total": group.total,
                "first_seen": group.first_seen,
                "last_seen": group.last_seen,
                "sample": group.message,
            }
            continue
        entry["current"] += group.current
        entry["previous"] += group.previous
        entry["total"] += group.total
        entry["first_seen"] = min(entry["first_seen"], group.first_seen)
        # The newest line wins, so the verbatim example beside a
        # normalised signature is the most recent occurrence rather than
        # whichever the database happened to return first — the rule
        # ``_record_recurrence`` already applies to ``alert.message``.
        if group.last_seen > entry["last_seen"]:
            entry["last_seen"] = group.last_seen
            entry["sample"] = group.message

    trends: list[SignatureTrend] = []
    for (source, severity, sig), entry in acc.items():
        change, ratio = _classify(
            entry["current"], entry["previous"], entry["first_seen"], window_start
        )
        trends.append(
            SignatureTrend(
                signature=sig,
                alert_title=alert_title(severity, source, entry["sample"]),
                source=source,
                severity=severity,
                sample=entry["sample"],
                current=entry["current"],
                previous=entry["previous"],
                total=entry["total"],
                first_seen=entry["first_seen"],
                last_seen=entry["last_seen"],
                change=change,
                ratio=ratio,
            )
        )

    # New first, then loudest.  A new signature with four occurrences
    # outranks a stable one with forty thousand, for the reason a
    # projected disk-threshold crossing outranks every byte total in
    # ``FileRecommendationInfo``: novelty is the thing a reader cannot
    # get by looking at today's alerts.
    trends.sort(key=lambda t: (not t.is_new, -t.current, -t.total, t.signature))

    sources = _source_trends(groups, trends)

    return LogTrendReport(
        window_days=window_days,
        window_start=window_start,
        previous_start=previous_start,
        generated_at=generated_at,
        confidence=_confidence(coverage),
        signatures=trends,
        sources=sources,
        coverage=coverage,
        truncated=truncated,
        groups_read=len(groups),
    )


def _source_trends(
    groups: list[MessageGroup], trends: list[SignatureTrend]
) -> list[SourceTrend]:
    """Per-source volume, summed from the groups rather than the signatures.

    Deliberately off the **groups**: a source's error volume is a count
    of lines, and folding messages into signatures first would make the
    total depend on how well the normaliser happened to work on that
    source's wording.
    """
    totals: dict[str, dict[str, int]] = {}
    for group in groups:
        bucket = totals.setdefault(
            group.source,
            {"cur_err": 0, "prev_err": 0, "cur_warn": 0, "prev_warn": 0},
        )
        if group.severity in ("error", "critical"):
            bucket["cur_err"] += group.current
            bucket["prev_err"] += group.previous
        elif group.severity == "warning":
            bucket["cur_warn"] += group.current
            bucket["prev_warn"] += group.previous

    per_source_sigs: dict[str, list[SignatureTrend]] = {}
    for trend in trends:
        per_source_sigs.setdefault(trend.source, []).append(trend)

    out = [
        SourceTrend(
            source=source,
            current_errors=bucket["cur_err"],
            previous_errors=bucket["prev_err"],
            current_warnings=bucket["cur_warn"],
            previous_warnings=bucket["prev_warn"],
            signatures=len(per_source_sigs.get(source, [])),
            new_signatures=sum(
                1 for t in per_source_sigs.get(source, []) if t.is_new
            ),
        )
        for source, bucket in totals.items()
    ]
    # Biggest error movement first, in either direction — a source whose
    # errors collapsed is as worth seeing as one whose errors doubled.
    out.sort(key=lambda s: (-abs(s.error_delta), -s.current_errors, s.source))
    return out
