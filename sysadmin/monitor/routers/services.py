"""Service reliability API — how dependable each monitored service is.

Session 25, Tier 1.  ``GET /api/services/reliability`` is the sysadmin
equivalent of ``GET /api/projects/overview``: one score per service,
worst first, with every deduction attributable.

**Computed live, not read back.**  Unlike ``/api/units/status``, which
serves the latest stored sweep, this recomputes from ``service_health``
on every request.  Three reasons: the query is one indexed range scan
over at most a week of rows (~20 ms for the whole estate here); a stored
answer would be up to 24 hours stale, which is useless for a page whose
job is "is anything broken now"; and reading a table would mean a 404
until the first nightly job had run.  The ``reliability_scores`` table
exists so the score is *trendable* — it is history, not the serving
path, and ``reliability_history.record_reliability_snapshot`` writes it.

Read-only, and the score is not a control surface: the remedy for an
unreliable service is a config change or a fix in the service itself,
neither of which belongs behind a POST here.  Restarting one already has
an endpoint (``POST /api/sysadmin/services/{name}/{action}``).
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    ReliabilityDeduction,
    ReliabilityResponse,
    ReliabilitySummary,
    ServiceActionsResponse,
    ServiceReliabilityInfo,
)
from sysadmin.core.database import get_db_session
from sysadmin.monitor.reliability import ReliabilityScore
from sysadmin.monitor.reliability_history import (
    compute_reliability,
    fetch_timer_series,
)
from sysadmin.monitor.service_recommendations import recommend, total_recoverable_points
from sysadmin.monitor.services import get_services, services_by_project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["services"])


@router.get("/by-project")
async def by_project() -> dict:
    """Project id → the names of its services — sysadmin's contribution.

    Added in estate-manager Session 4 (its ADR-0008, sysadmin ADR-0005):
    the project scanner moved to the estate, but which services a project
    owns is declared in this repository's ``services.yaml`` and stays
    machine-flavoured. The estate pulls this once per scan to publish
    ``services[]`` in estate.json. Names only, deliberately — embedding
    urls and units would make estate.json a second place to edit when a
    port moves.
    """
    return {"by_project": services_by_project(get_services())}

GRADES = ("reliable", "degraded", "unreliable", "failing")
CONFIDENCE_LEVELS = ("high", "low")


def summarise(scores: list[ReliabilityScore]) -> ReliabilitySummary:
    """Estate-level totals over an already-scored list."""
    counts = dict.fromkeys(GRADES, 0)
    for score in scores:
        counts[score.grade] = counts.get(score.grade, 0) + 1

    mean = round(sum(s.score for s in scores) / len(scores), 1) if scores else 100.0
    return ReliabilitySummary(
        services_scored=len(scores),
        reliable=counts["reliable"],
        degraded=counts["degraded"],
        unreliable=counts["unreliable"],
        failing=counts["failing"],
        low_confidence=sum(1 for s in scores if s.confidence == "low"),
        mean_score=mean,
    )


def to_contract(score: ReliabilityScore) -> ServiceReliabilityInfo:
    """Dataclass → wire model, timestamps already ISO-formatted."""
    payload = score.as_dict()
    payload["deductions"] = [
        ReliabilityDeduction(**d) for d in payload.get("deductions", [])
    ]
    return ServiceReliabilityInfo(**payload)


@router.get("/reliability", response_model=ReliabilityResponse)
async def get_reliability(
    grade: str | None = Query(
        None, description="reliable | degraded | unreliable | failing"
    ),
    confidence: str | None = Query(None, description="high | low"),
    session: AsyncSession = Depends(get_db_session),
) -> ReliabilityResponse:
    """Reliability for every configured service, worst first.

    ``summary`` is always computed over **all** services, never over the
    filtered subset — a filtered page whose totals moved with the filter
    would make "3 unreliable" mean something different on every request.
    """
    if grade is not None and grade not in GRADES:
        raise HTTPException(
            status_code=400, detail=f"grade must be one of {', '.join(GRADES)}"
        )
    if confidence is not None and confidence not in CONFIDENCE_LEVELS:
        raise HTTPException(
            status_code=400,
            detail=f"confidence must be one of {', '.join(CONFIDENCE_LEVELS)}",
        )

    config = get_config()
    now = datetime.now(UTC)
    scores = await compute_reliability(session, config, now=now)
    summary = summarise(scores)

    shown = scores
    if grade is not None:
        shown = [s for s in shown if s.grade == grade]
    if confidence is not None:
        shown = [s for s in shown if s.confidence == confidence]

    return ReliabilityResponse(
        computed_at=now.isoformat(),
        window_days=config.agents.sysadmin.reliability.window_days,
        summary=summary,
        services=[to_contract(s) for s in shown],
        count=len(shown),
    )


@router.get("/actions", response_model=ServiceActionsResponse)
async def get_service_actions(
    limit: int | None = Query(
        None, ge=1, le=200, description="Rows to return; config default otherwise"
    ),
    session: AsyncSession = Depends(get_db_session),
) -> ServiceActionsResponse:
    """Ranked service advice — Session 25, Tier 2.

    The fourth advice endpoint, beside ``/api/files/actions``,
    ``/api/logs/actions`` and ``/api/units/actions``.  **GET-only and
    always will be**, for ``/api/units/*``'s reason: the remedy for an
    unreliable service is a fix in the service or an edit to a
    hand-curated file, and restarting one already has its own endpoint.
    A test asserts no non-GET route exists here.

    Computed off the same live ``compute_reliability`` call that
    ``/reliability`` serves rather than off ``reliability_scores``, so
    the advice and the score cannot disagree about the window they
    describe — and so this route never 404s before the first nightly
    job, which is the trade Tier 1 already made and argued for.

    ``limit`` cuts the list; ``total_available`` reports what existed
    before the cut, because a saturated list that cannot say so reads as
    "that is all there is" — the failure ``/api/projects/actions`` hit
    in Session 28 and ``UnitActionsResponse.dropped_by_kind`` was added
    for.
    """
    config = get_config()
    settings = config.agents.sysadmin.service_actions
    now = datetime.now(UTC)

    scores = await compute_reliability(session, config, now=now)
    timers = await fetch_timer_series(session, config, now=now)

    report = recommend(
        scores,
        settings,
        timers=timers,
        check_interval_seconds=config.agents.sysadmin.health_check_interval_seconds,
        now=now,
    )

    cut = limit if limit is not None else settings.limit
    shown = report.recommendations[:cut]

    return ServiceActionsResponse(
        computed_at=now.isoformat(),
        window_days=config.agents.sysadmin.reliability.window_days,
        recommendations=shown,
        count=len(shown),
        total_available=len(report.recommendations),
        # Summed over everything the run produced, never over the page.
        # A total that moved with ``limit`` would make "42 points
        # available" mean something different on every request —
        # ``summarise``'s rule three routes up in this same file.
        total_recoverable_points=total_recoverable_points(report.recommendations),
        muted_skipped=report.muted_skipped,
        suppressed_by_confidence=report.suppressed_by_confidence,
        services_considered=report.services_considered,
    )
