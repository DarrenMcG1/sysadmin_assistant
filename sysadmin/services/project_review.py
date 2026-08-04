"""Weekly LLM-narrated portfolio review (project-manager Tier 3).

Pipeline: gather structured facts (scores, week-on-week deltas, top
recommendations) → build a bounded prompt → ask llama-server for a short
narrative → store a :class:`ProjectReview` row and raise an ``info``
alert so the tray notices.

The LLM is optional at every step: when llama-server is unavailable the
review is still generated from :func:`build_fallback_narrative` — a
deterministic digest of the same facts — with ``llm_used=False``.  The
structured inputs are stored alongside the narrative (``stats``) so the
prose stays auditable against the data it was written from.

llama-server calls go through :class:`LLMClient`, which is constructed
per run (never shared across scheduler event loops — SNAG-AGENT-003).
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from sysadmin.config import get_config
from sysadmin.database import get_scheduler_session
from sysadmin.models.alert import Alert
from sysadmin.models.project_review import ProjectReview
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.services.recommendations import recommendations_for

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = (
    "You are a pragmatic engineering project manager reviewing a personal "
    "software portfolio. Write in UK English. Be concrete and reference "
    "projects by name. Do not invent facts not present in the data."
)

# Keep the narrative request bounded — a 3B model rambles if unconstrained
REVIEW_INSTRUCTIONS = (
    "Write a short weekly review of this project portfolio in four brief "
    "sections: 1) What moved this week (score changes); 2) What is "
    "decaying and why; 3) Archive candidates, if any; 4) Suggested focus "
    "for next week — at most three concrete actions, taken from the "
    "recommendations listed. Keep it under 250 words. Plain text only."
)


async def gather_review_data(
    session: AsyncSession, period_days: int = 7
) -> dict[str, Any]:
    """Structured facts for the review: current state plus deltas.

    The week-on-week delta compares each project's latest snapshot with
    its *oldest snapshot inside the window* — the closest thing to "where
    it stood a week ago" without assuming any particular scan cadence.
    Projects with a single snapshot get ``delta: None``.
    """
    latest_subq = (
        select(
            ProjectSnapshot.project_name,
            func.max(ProjectSnapshot.scanned_at).label("max_scanned"),
        )
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )
    result = await session.execute(
        select(ProjectSnapshot).join(
            latest_subq,
            (ProjectSnapshot.project_name == latest_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == latest_subq.c.max_scanned),
        )
    )
    latest_rows = {r.project_name: r for r in result.scalars().all()}

    cutoff = datetime.now(UTC) - timedelta(days=period_days)
    baseline_subq = (
        select(
            ProjectSnapshot.project_name,
            func.min(ProjectSnapshot.scanned_at).label("min_scanned"),
        )
        .where(ProjectSnapshot.scanned_at >= cutoff)
        .group_by(ProjectSnapshot.project_name)
        .subquery()
    )
    result = await session.execute(
        select(ProjectSnapshot).join(
            baseline_subq,
            (ProjectSnapshot.project_name == baseline_subq.c.project_name)
            & (ProjectSnapshot.scanned_at == baseline_subq.c.min_scanned),
        )
    )
    baseline_rows = {r.project_name: r for r in result.scalars().all()}

    agent_config = get_config().agents.project_organiser
    projects = []
    risk_count = 0
    recoverable_total = 0
    for name, row in sorted(latest_rows.items()):
        findings = row.findings or {}
        recs = recommendations_for(row, agent_config)
        risk_count += sum(1 for r in recs if r.severity == "risk")
        recoverable_total += sum(r.points for r in recs)

        baseline = baseline_rows.get(name)
        delta = None
        if baseline is not None and baseline.scanned_at != row.scanned_at:
            delta = row.health_score - baseline.health_score

        projects.append({
            "name": name,
            "status": findings.get("status", "active"),
            "score": row.health_score,
            "delta": delta,
            "top_recommendations": [
                {"title": r.title, "points": r.points, "severity": r.severity}
                for r in recs[:3]
            ],
        })

    active = [p for p in projects if p["status"] == "active"]
    return {
        "period_days": period_days,
        "projects": projects,
        "totals": {
            "project_count": len(projects),
            "active_count": len(active),
            "average_active_score": (
                round(sum(p["score"] for p in active) / len(active), 1)
                if active
                else None
            ),
            "risk_count": risk_count,
            "recoverable_points": recoverable_total,
        },
    }


def build_review_prompt(data: dict[str, Any]) -> str:
    """Deterministic prompt from the gathered facts."""
    lines = [
        f"Portfolio data for the last {data['period_days']} days.",
        f"Totals: {data['totals']}",
        "",
        "Projects (score is 0-100 health; delta is change over the period):",
    ]
    for p in data["projects"]:
        delta = "n/a" if p["delta"] is None else f"{p['delta']:+d}"
        line = f"- {p['name']} [{p['status']}] score {p['score']} (delta {delta})"
        if p["top_recommendations"]:
            recs = "; ".join(
                f"{r['title']} (+{r['points']})"
                if r["severity"] != "risk"
                else f"{r['title']} (RISK)"
                for r in p["top_recommendations"]
            )
            line += f" — actions: {recs}"
        lines.append(line)
    lines += ["", REVIEW_INSTRUCTIONS]
    return "\n".join(lines)


def build_fallback_narrative(data: dict[str, Any]) -> str:
    """Deterministic digest used when llama-server is unavailable."""
    totals = data["totals"]
    lines = [
        f"Weekly project review ({data['period_days']} days) — "
        "generated without LLM narration.",
        f"{totals['project_count']} projects tracked, "
        f"{totals['active_count']} active; average active score "
        f"{totals['average_active_score']}. "
        f"{totals['recoverable_points']} points recoverable across the "
        f"portfolio; {totals['risk_count']} risk item(s).",
    ]
    movers = [p for p in data["projects"] if p["delta"]]
    if movers:
        moved = ", ".join(
            f"{p['name']} {p['delta']:+d}"
            for p in sorted(movers, key=lambda p: p["delta"], reverse=True)
        )
        lines.append(f"Moved this week: {moved}.")
    worst = [
        p for p in data["projects"]
        if p["status"] == "active" and p["top_recommendations"]
    ]
    worst.sort(key=lambda p: p["score"])
    for p in worst[:3]:
        top = p["top_recommendations"][0]
        lines.append(
            f"Focus: {p['name']} (score {p['score']}) — {top['title']}."
        )
    return "\n".join(lines)


async def generate_review(
    session: AsyncSession,
    llm_client=None,
    period_days: int = 7,
) -> ProjectReview | None:
    """Generate, store and return a review; None when there is no data.

    ``llm_client`` is injectable for tests; by default a fresh
    :class:`LLMClient` is built for this run and shut down afterwards.
    """
    from sysadmin.services.llm_client import LLMClient

    data = await gather_review_data(session, period_days)
    if not data["projects"]:
        logger.info("project_review_skipped_no_data")
        return None

    config = get_config()
    narrative: str | None = None

    owns_client = llm_client is None
    client = llm_client or LLMClient()
    if owns_client:
        await client.startup()
    try:
        narrative = await client.generate(
            build_review_prompt(data), system=REVIEW_SYSTEM_PROMPT
        )
    finally:
        if owns_client:
            await client.shutdown()

    llm_used = narrative is not None
    if not llm_used:
        narrative = build_fallback_narrative(data)
        logger.warning("project_review_llm_unavailable_used_fallback")

    review = ProjectReview(
        period_days=period_days,
        narrative=narrative,
        llm_used=llm_used,
        model_used=config.llm.model if llm_used else None,
        stats=data,
    )
    session.add(review)
    await session.flush()
    return review


async def run_weekly_review() -> None:
    """Scheduler entry point — generate, store, and notify via an alert."""
    async with get_scheduler_session() as session:
        review = await generate_review(session)
        if review is None:
            return

        first_line = review.narrative.splitlines()[0] if review.narrative else ""
        session.add(Alert(
            agent="project_organiser",
            severity="info",
            title="Weekly project review ready",
            message=first_line[:255],
            details={
                "review_id": str(review.id),
                "llm_used": review.llm_used,
                "endpoint": "/api/projects/review",
            },
        ))
    logger.info("weekly_project_review_generated")
