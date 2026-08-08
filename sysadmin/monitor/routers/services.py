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
    ServiceReliabilityInfo,
)
from sysadmin.core.database import get_db_session
from sysadmin.monitor.reliability import ReliabilityScore
from sysadmin.monitor.reliability_history import compute_reliability

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/services", tags=["services"])

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
