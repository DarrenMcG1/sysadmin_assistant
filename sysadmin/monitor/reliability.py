"""Per-service reliability scoring over recorded health checks.

Session 25, Tier 1.  Nothing scored *services* — the project organiser
scores repositories and the file organiser scores the disk, but the thing
this application exists to watch had no number attached to it.

Pure module: no DB access, no FastAPI.  Give it a list of
:class:`HealthPoint` for one service and get a :class:`ReliabilityScore`
back.  The caller does the query, exactly as ``forecast.py`` takes
``(timestamp, value)`` pairs rather than a session — an ORM row and a
hand-built test fixture both produce the same shape.

Two departures from the original session plan, both deliberate:

**Incidents are counted from the health series, not from ``alerts``.**
The plan named "mean time between alerts".  The ``alerts`` table records
one row *per failed check*, not one per incident: a single seven-hour
internet outage on this host wrote 123 rows over 7 days, and
``venture-assistant`` wrote 81 for one sustained outage.  Mean time
between those measures ``health_check_interval_seconds`` and nothing
else.  Consecutive non-ok checks in ``service_health`` collapse into one
*episode* by construction, carry the same information, and need no join
against ``details->>'service_name'`` — which is the only link ``alerts``
has to a service, and is not indexed.

**Restart frequency is absent.**  The plan named it; nothing on this host
records restarts.  ``systemctl show -p NRestarts`` is a live cumulative
counter that is never sampled into the database, and ``agent_runs``
records agent executions rather than service ones.  Three measured
metrics beat four where one is invented.

Two deductions, each individually attributable so Tier 2 can price them
separately:

``downtime``
    ``round(100 - uptime_percent)``, capped at :data:`DOWNTIME_CAP`.
    "It was not there when something asked for it."

``instability``
    :data:`INSTABILITY_PER_EPISODE` per outage episode, capped at
    :data:`INSTABILITY_CAP`.  "It keeps bouncing."  A separate term
    because it is a separate failure: retry logic survives one long
    outage and dies on three short ones, so a service that dropped out
    three times must not score better than one that dropped out once for
    longer merely because it was up more of the time.

Status handling mirrors the agent that wrote the rows
(``SysAdminAgent._handle_status``).  ``error`` means the *check* failed,
so the service's state is unknown — those rows are counted and reported
but excluded from every rate, because an unmeasurable check is neither a
success nor a failure.  Everything else is binary: ``ok`` is up, anything
else is down.  Weighting ``degraded`` as a fraction of an outage would be
precision this data cannot support.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

__all__ = [
    "DOWNTIME_CAP",
    "INSTABILITY_CAP",
    "INSTABILITY_PER_EPISODE",
    "Deduction",
    "HealthPoint",
    "ReliabilityScore",
    "score_service",
    "score_services",
]

#: Ceiling on the downtime deduction.  A service down most of the week is
#: already the worst thing in the list; letting downtime alone reach 100
#: would leave no room for instability to rank two dead services against
#: each other.
DOWNTIME_CAP = 60

#: Points per outage episode, charged from the first one.  A service that
#: failed a check this week should not read as a perfect 100.
INSTABILITY_PER_EPISODE = 5

#: Ceiling on the instability deduction (five episodes).
INSTABILITY_CAP = 25

#: Statuses that record **no evidence about the service**, so they are
#: excluded from every rate here.  Both mean nothing was measured and the
#: difference is *who decided*, which is why they are counted separately
#: on the result rather than summed into one field.
#:
#: ``error``
#:     The check itself failed — the service's state is unknown.
#: ``skipped``
#:     ``services.yaml`` declares ``monitor: false``.  Nobody looked, by
#:     choice.
#:
#: **``skipped`` was missing until 2026-08-25 and the cost was 60 points
#: a service** (Session 78).  Only ``error`` was excluded, so a
#: ``skipped`` row counted as measured-and-not-``ok`` — i.e. as an
#: outage — and this box's three declared-unmonitored services
#: (``venture-chat-large``, ``sysadmin-tray``, ``searxng-upstream``)
#: each scored **35** and graded ``failing`` off 307 checks nobody had
#: taken.  It sat unnoticed as a number on a page from Session 25 until
#: ``GET /api/services/actions`` turned each one into a ``risk`` row.
#:
#: Note that neither obvious reading is right and the sibling rule does
#: not transfer.  ``SysAdminAgent._resolve_recovered`` treats ``skipped``
#: as *healthy*, correctly — an open critical nobody will look at again
#: is a pile-up wearing a declaration as an excuse — but that is a
#: question about closing an alert, and importing it here would fabricate
#: a **100**.  Scoring it as down fabricates a **35**.  A score with no
#: evidence behind it is ``ports_checked``'s rule: zero-because-blind
#: must never be served as zero-because-clean, so the row is excluded and
#: ``confidence`` carries the truth.
UNMEASURED_STATUSES = ("error", "skipped")

#: Kept for readers that only care about the check-failed case.
UNMEASURED_STATUS = "error"

#: The declared-unmonitored half of :data:`UNMEASURED_STATUSES`.
SKIPPED_STATUS = "skipped"

#: Below this fraction of expected checks, the window is too gappy to
#: trust — the monitor was down, so the sample is not representative.
LOW_COVERAGE_FRACTION = 0.5

#: Below this much observed history, the score is an early reading rather
#: than a week's evidence.
MIN_CONFIDENT_HISTORY_DAYS = 2.0


@dataclass(frozen=True)
class HealthPoint:
    """One recorded health check.

    Deliberately narrower than ``ServiceHealth``: the score needs the
    time and the verdict, and nothing else in the row changes it.
    """

    checked_at: datetime
    status: str


@dataclass(frozen=True)
class Deduction:
    """One attributable subtraction from 100.

    ``waived`` deductions are computed and reported but not applied — see
    :func:`score_service` for why a muted service is scored rather than
    skipped.
    """

    kind: str  # downtime | instability
    points: int
    detail: str
    waived: bool = False


@dataclass
class ReliabilityScore:
    """One service's reliability over the scoring window."""

    service: str
    score: int = 100
    grade: str = "reliable"

    # --- what was measured ---
    uptime_percent: float = 100.0
    checks_recorded: int = 0
    checks_measured: int = 0  # recorded minus unmeasurable ('error') checks
    failed_checks: int = 0
    error_checks: int = 0
    #: Checks ``services.yaml`` declared away with ``monitor: false``.
    #: Separate from ``error_checks`` because "the check failed" and
    #: "nobody looked, by choice" are different claims about the same
    #: absence, and one field holding both is ``UnitFinding.enabled``'s
    #: trap.
    skipped_checks: int = 0
    outage_episodes: int = 0
    longest_outage_minutes: float = 0.0
    #: Mean gap between the *starts* of consecutive outage episodes.
    #: ``None`` with fewer than two episodes — one incident establishes no
    #: interval, and inventing one from the window length would imply a
    #: cadence the data has not shown.
    mean_hours_between_incidents: float | None = None

    # --- how far to trust it ---
    checks_expected: int = 0
    coverage_percent: float = 0.0
    observed_days: float = 0.0
    confidence: str = "high"  # high | low
    confidence_reason: str | None = None

    # --- provenance ---
    window_days: int = 7
    window_start: datetime | None = None
    first_check_at: datetime | None = None
    last_check_at: datetime | None = None
    muted: bool = False
    waived_points: int = 0
    deductions: list[Deduction] = field(default_factory=list)

    def as_dict(self) -> dict:
        """Plain dict, timestamps ISO-formatted — ready for a contract."""
        out = asdict(self)
        for key in ("window_start", "first_check_at", "last_check_at"):
            value = out[key]
            out[key] = value.isoformat() if value else None
        return out


def score_service(
    service: str,
    points: list[HealthPoint],
    *,
    window_days: int = 7,
    check_interval_seconds: int = 300,
    now: datetime,
    muted: bool = False,
    grade_bands: tuple[int, int, int] = (95, 85, 60),
) -> ReliabilityScore:
    """Score one service from its recorded checks.

    ``points`` need not be sorted; anything outside the window is
    ignored, so the caller may pass a wider slice.

    A ``muted`` service — one declared expected-down — has its deductions
    computed and listed with ``waived=True`` but not applied.  Excluding
    it instead would leave a hole in the report where a monitored service
    ought to be, and a reader cannot tell "expected down" from "not
    monitored" once the row is gone.
    """
    window_start = now - timedelta(days=window_days)
    inside = sorted(
        (p for p in points if p.checked_at >= window_start),
        key=lambda p: p.checked_at,
    )

    result = ReliabilityScore(
        service=service,
        window_days=window_days,
        window_start=window_start,
        muted=muted,
        checks_recorded=len(inside),
        checks_expected=max(1, int(window_days * 86400 / max(1, check_interval_seconds))),
    )

    if not inside:
        # No evidence is not a failure.  The score stays 100 and the
        # confidence flag carries the truth, so a consumer that ranks by
        # score does not promote an unmeasured service above a measured
        # one that had a bad week.
        result.confidence = "low"
        result.confidence_reason = "no checks recorded in the window"
        result.grade = _grade(result.score, grade_bands)
        return result

    result.first_check_at = inside[0].checked_at
    result.last_check_at = inside[-1].checked_at
    result.observed_days = round(
        (result.last_check_at - result.first_check_at).total_seconds() / 86400, 2
    )
    result.coverage_percent = round(
        100.0 * result.checks_recorded / result.checks_expected, 2
    )

    measured = [p for p in inside if p.status not in UNMEASURED_STATUSES]
    result.error_checks = sum(1 for p in inside if p.status == UNMEASURED_STATUS)
    result.skipped_checks = sum(1 for p in inside if p.status == SKIPPED_STATUS)
    result.checks_measured = len(measured)

    if not measured:
        result.confidence = "low"
        # The two absences are reported apart, because the remedies are
        # opposite: a service that is all-``error`` needs its check
        # fixed, and one that is all-``skipped`` is behaving exactly as
        # declared and needs nothing at all.
        if result.skipped_checks and not result.error_checks:
            result.confidence_reason = (
                f"not monitored — services.yaml declares monitor: false, so all "
                f"{result.skipped_checks} checks in the window recorded no "
                "evidence either way"
            )
        else:
            result.confidence_reason = "every check in the window was unmeasurable"
        result.grade = _grade(result.score, grade_bands)
        return result

    result.failed_checks = sum(1 for p in measured if p.status != "ok")
    result.uptime_percent = round(
        100.0 * (len(measured) - result.failed_checks) / len(measured), 2
    )

    episodes = _outage_episodes(measured)
    result.outage_episodes = len(episodes)
    if episodes:
        result.longest_outage_minutes = round(
            max((end - start).total_seconds() for start, end in episodes) / 60, 1
        )
    if len(episodes) > 1:
        starts = [start for start, _ in episodes]
        gaps = [
            (later - earlier).total_seconds()
            for earlier, later in zip(starts[:-1], starts[1:], strict=True)
        ]
        result.mean_hours_between_incidents = round(sum(gaps) / len(gaps) / 3600, 1)

    result.confidence, result.confidence_reason = _confidence(result)
    result.deductions = _deductions(result, muted=muted)

    applied = sum(d.points for d in result.deductions if not d.waived)
    result.waived_points = sum(d.points for d in result.deductions if d.waived)
    result.score = max(0, 100 - applied)
    result.grade = _grade(result.score, grade_bands)
    return result


def score_services(
    series: dict[str, list[HealthPoint]],
    *,
    muted: set[str] | None = None,
    window_days: int = 7,
    check_interval_seconds: int = 300,
    now: datetime,
    grade_bands: tuple[int, int, int] = (95, 85, 60),
) -> list[ReliabilityScore]:
    """Score several services, worst first.

    Ordering is score ascending, then service name — so the thing to look
    at is at the top and the order is stable between calls.  Confidence
    deliberately does not affect ordering: a low-confidence bad score is
    still the most interesting row on the page, and burying it under
    fifteen perfect ones would hide the only service that failed.
    """
    muted = muted or set()
    scores = [
        score_service(
            name,
            points,
            window_days=window_days,
            check_interval_seconds=check_interval_seconds,
            now=now,
            muted=name in muted,
            grade_bands=grade_bands,
        )
        for name, points in series.items()
    ]
    scores.sort(key=lambda s: (s.score, s.service))
    return scores


# --- internals ---


def _outage_episodes(
    measured: list[HealthPoint],
) -> list[tuple[datetime, datetime]]:
    """Collapse consecutive non-ok checks into ``(start, end)`` spans.

    ``end`` is the last failing check, not the recovery — the recovery
    check is evidence the service was already back, and dating the outage
    to it would inflate every span by one check interval.  A single
    failing check therefore has zero duration, which is honest: one
    sample cannot show how long something lasted.
    """
    episodes: list[tuple[datetime, datetime]] = []
    start: datetime | None = None
    last_bad: datetime | None = None

    for point in measured:
        if point.status != "ok":
            if start is None:
                start = point.checked_at
            last_bad = point.checked_at
        elif start is not None and last_bad is not None:
            episodes.append((start, last_bad))
            start = last_bad = None

    if start is not None and last_bad is not None:
        episodes.append((start, last_bad))
    return episodes


def _confidence(result: ReliabilityScore) -> tuple[str, str | None]:
    """Whether the window holds enough evidence to act on.

    A gap means the *monitor* was down, not the service, so it never
    costs points — it only lowers confidence.  Deducting for it would
    blame the wrong component, and the component it would blame is this
    application.
    """
    if result.observed_days < MIN_CONFIDENT_HISTORY_DAYS:
        return "low", (
            f"only {result.observed_days:g} days of history — the service was "
            "added recently or checks have only just started"
        )
    if result.coverage_percent < LOW_COVERAGE_FRACTION * 100:
        return "low", (
            f"{result.coverage_percent:g}% of expected checks recorded — the "
            "monitor was down for much of the window"
        )
    return "high", None


def _deductions(result: ReliabilityScore, *, muted: bool) -> list[Deduction]:
    """The subtractions behind the score, largest first."""
    out: list[Deduction] = []

    downtime = min(DOWNTIME_CAP, round(100 - result.uptime_percent))
    if downtime > 0:
        capped = " (capped)" if downtime == DOWNTIME_CAP else ""
        out.append(Deduction(
            kind="downtime",
            points=downtime,
            detail=(
                f"{result.uptime_percent:g}% uptime across "
                f"{result.checks_measured} measured checks — "
                f"{result.failed_checks} failed{capped}."
            ),
            waived=muted,
        ))

    episodes = result.outage_episodes
    if episodes > 0:
        raw = INSTABILITY_PER_EPISODE * episodes
        instability = min(INSTABILITY_CAP, raw)
        plural = "s" if episodes != 1 else ""
        longest = (
            f", longest {result.longest_outage_minutes:g} min"
            if result.longest_outage_minutes
            else ""
        )
        capped = " (capped)" if instability < raw else ""
        out.append(Deduction(
            kind="instability",
            points=instability,
            detail=(
                f"{episodes} separate outage{plural}{longest} — "
                f"{INSTABILITY_PER_EPISODE} points each{capped}."
            ),
            waived=muted,
        ))

    out.sort(key=lambda d: (-d.points, d.kind))
    return out


def _grade(score: int, bands: tuple[int, int, int]) -> str:
    """Map a score to a word, mirroring the project organiser's bands."""
    reliable_min, degraded_min, unreliable_min = bands
    if score >= reliable_min:
        return "reliable"
    if score >= degraded_min:
        return "degraded"
    if score >= unreliable_min:
        return "unreliable"
    return "failing"
