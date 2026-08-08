"""Service Discovery API endpoints — installed units vs the wired estate.

Session 26.  ``/status`` is the sweep as measured; ``/actions`` is the
same sweep turned into ranked advice with ready-to-paste YAML.  The split
mirrors ``/api/files/status`` and ``/api/files/actions``.

Read-only by design.  There is no executor here and there will not be
one: the fix for an unmonitored unit is an edit to a hand-curated YAML
file whose comments carry the reasoning, and the fix for an orphan is
``systemctl disable && rm``, which is not something a scheduled agent
should do to a machine on its own.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.core.config import get_config
from sysadmin.core.contracts import (
    UnitActionsResponse,
    UnitFindingInfo,
    UnitRecommendationInfo,
    UnitScanResponse,
    UnitScanSummary,
)
from sysadmin.core.database import get_db_session
from sysadmin.registry import load_registry
from sysadmin.units.models import UnitAudit
from sysadmin.units.recommendations import (
    KIND_ORDER,
    recommendations_for_scan,
)
from sysadmin.units.scan import CATEGORY_ORDER, UnitFinding

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/units", tags=["units"])

NO_SCAN_YET = "No unit sweep yet — the service_discovery agent has not run."


async def _latest_audit(session: AsyncSession) -> UnitAudit:
    audit = (
        await session.execute(
            select(UnitAudit).order_by(desc(UnitAudit.scanned_at)).limit(1)
        )
    ).scalar_one_or_none()
    if audit is None:
        # 404 rather than an empty 200, matching /api/files/*: "no data
        # yet" and "nothing to report" are different answers and a
        # consumer must be able to tell them apart.
        raise HTTPException(status_code=404, detail=NO_SCAN_YET)
    return audit


def _findings_from(audit: UnitAudit, category: str | None = None) -> list[UnitFinding]:
    """Rehydrate stored findings into the dataclass the pure modules use.

    Stored grouped by category, so a category filter is a dict lookup
    rather than a scan-and-filter over a flat list.
    """
    blob = audit.findings or {}
    wanted = (category,) if category else CATEGORY_ORDER

    findings: list[UnitFinding] = []
    for key in wanted:
        for row in blob.get(key) or []:
            if not isinstance(row, dict):
                continue
            findings.append(
                UnitFinding(
                    unit=str(row.get("unit", "")),
                    scope=str(row.get("scope", "system")),
                    category=str(row.get("category", key)),
                    path=str(row.get("path", "")),
                    description=row.get("description"),
                    project=row.get("project"),
                    project_path=row.get("project_path"),
                    matched_by=row.get("matched_by"),
                    monitor_unit=str(row.get("monitor_unit") or row.get("unit", "")),
                    dead_path=row.get("dead_path"),
                    manual=bool(row.get("manual", False)),
                    reason=str(row.get("reason", "")),
                )
            )
    return findings


@router.get("/status", response_model=UnitScanResponse)
async def get_unit_status(
    category: str | None = Query(
        None,
        description="orphaned | unmonitored | host — omit for all three",
    ),
    session: AsyncSession = Depends(get_db_session),
) -> UnitScanResponse:
    """The latest unit sweep: what was scanned and what needs attention.

    Monitored units are counted in ``summary`` but never listed.  A list
    of things that are fine is noise the reader has to filter every time,
    and the count is the part that makes the arithmetic checkable.
    """
    if category is not None and category not in CATEGORY_ORDER:
        raise HTTPException(
            status_code=400,
            detail=f"category must be one of {', '.join(CATEGORY_ORDER)}",
        )

    audit = await _latest_audit(session)
    findings = _findings_from(audit, category)

    scopes: dict[str, set[str]] = {}
    for finding in _findings_from(audit):
        scopes.setdefault(finding.unit, set()).add(finding.scope)

    return UnitScanResponse(
        scanned_at=audit.scanned_at.isoformat() if audit.scanned_at else None,
        summary=UnitScanSummary(
            units_scanned=audit.units_scanned,
            units_excluded=audit.units_excluded,
            monitored=audit.monitored_count,
            timers_folded=audit.timers_folded,
            orphaned=audit.orphaned_count,
            unmonitored=audit.unmonitored_count,
            host=audit.host_count,
        ),
        findings=[UnitFindingInfo(**f.as_dict()) for f in findings],
        count=len(findings),
        duplicate_units=sorted(u for u, s in scopes.items() if len(s) > 1),
    )


@router.get("/actions", response_model=UnitActionsResponse)
async def get_unit_actions(
    limit: int = Query(10, ge=1, le=100),
    kind: str | None = Query(
        None, description="orphan | unmonitored | host — omit for all three"
    ),
    session: AsyncSession = Depends(get_db_session),
) -> UnitActionsResponse:
    """Ranked service-discovery advice, worst first.

    ``dropped_by_kind`` reports what ``limit`` hid, keyed by kind.
    Without it a saturated list reads as "that is all there is" — the
    failure ``/api/projects/actions`` hit in Session 28, where eleven
    identical ``no_remote`` risks filled the default limit and nothing
    said the roadmap advice existed underneath.
    """
    if kind is not None and kind not in KIND_ORDER:
        raise HTTPException(
            status_code=400, detail=f"kind must be one of {', '.join(KIND_ORDER)}"
        )

    audit = await _latest_audit(session)
    config = get_config()

    recs = recommendations_for_scan(
        _findings_from(audit),
        load_registry(config.agents.project_organiser.projects_root),
    )
    if kind is not None:
        recs = [r for r in recs if r.kind == kind]

    returned = recs[:limit]
    dropped: dict[str, int] = {}
    for rec in recs[limit:]:
        dropped[rec.kind] = dropped.get(rec.kind, 0) + 1

    return UnitActionsResponse(
        scanned_at=audit.scanned_at.isoformat() if audit.scanned_at else None,
        recommendations=[UnitRecommendationInfo(**r.model_dump()) for r in returned],
        count=len(returned),
        total_available=len(recs),
        dropped_by_kind=dropped,
    )
