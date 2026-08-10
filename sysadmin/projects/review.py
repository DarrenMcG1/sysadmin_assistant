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

from sysadmin.core.config import get_config
from sysadmin.core.database import get_scheduler_session
from sysadmin.core.models.alert import Alert
from sysadmin.core.text import strip_markdown
from sysadmin.projects.models.project_review import ProjectReview
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.recommendations import recommendations_for
from sysadmin.projects.snapshots import latest_snapshot_query

logger = logging.getLogger(__name__)

REVIEW_SYSTEM_PROMPT = (
    "You are a pragmatic engineering project manager reviewing a personal "
    "software portfolio. Write in UK English. Be concrete and reference "
    "projects by name. Do not invent facts not present in the data."
)

# The numeric sections are deliberately NOT the model's job, and the
# enforcement is structural rather than instructional.
#
# The older of the two reviews, and the one that taught the lesson: asked
# for score changes on 2026-08-04, dria-agent-a-3b enumerated every
# unchanged project as "increased from 95 to 95", and a stricter prompt
# had it presenting recommendation points as movement. The disk review
# was rebuilt figure-free by construction on 2026-08-06 after the same
# model, given "25.0 GB across 50 directories" and an explicit "do not
# restate figures", restated them *and* published the quotient as "each
# consuming 5GB". This prompt was left behind until SNAG-PROJ-005.
#
# So the prompt below contains no figures at all: scores become bands,
# deltas become directions, and recommendation titles — which carry
# counts like "Burn down 40 code markers" — become number-free phrases.
# A model with no numbers in its context cannot restate or derive one.
# Every real figure lives in build_facts_section, prepended
# deterministically.
REVIEW_INSTRUCTIONS = (
    "Write three brief plain-text sections: 1) Decaying: which active "
    "projects most need attention and why, judging from their listed "
    "actions; 2) Archive candidates: projects that look abandoned, if "
    "any; 3) Focus for next week: at most three concrete actions, named "
    "from the listed actions. Figures are reported separately, so do "
    "not state any number, score, count, percentage or date — describe "
    "magnitude in words. Hard limit 150 words. Plain prose only: no "
    "markdown, no headings, no numbered or bulleted lists, no listing "
    "of every project."
)

# Number-free names for each recommendation kind. Several Tier 2 titles
# carry counts ("Prune 7 stale branches", "3 open snags") and so cannot
# go in the prompt; these say the same thing without a figure to
# regurgitate.
KIND_PHRASES = {
    "risk": "a risk item",
    "docs": "missing documentation (README or CLAUDE.md)",
    "config": "no .env beside the committed .env.example",
    "hygiene": "housekeeping left undone (a stale git lock or node_modules)",
    "git": "stale branches to prune",
    "activity": "no recent commits",
    "todos": "code markers left in the source (TODO, FIXME and similar)",
    "roadmap": "roadmap documents out of date (handoff, tasks or snags)",
}

# Score bands, in descending order. The prompt sees the label; the score
# itself only ever reaches build_facts_section.
SCORE_BANDS = (
    (90, "in good shape"),
    (75, "healthy"),
    (50, "needing attention"),
    (25, "neglected"),
    (0, "effectively abandoned"),
)


def score_band(score: int) -> str:
    """Qualitative health — the only score the prompt is allowed to see."""
    for threshold, label in SCORE_BANDS:
        if score >= threshold:
            return label
    return "effectively abandoned"


def delta_phrase(delta: int | None) -> str:
    """Describe the week's movement without stating it.

    ``None`` is "no earlier snapshot", which is a different statement
    from "unchanged" and must not collapse into it — a project scanned
    for the first time this week has not held steady, it has no history.
    """
    if delta is None:
        return "no earlier reading"
    if delta >= 10:
        return "improved markedly"
    if delta > 0:
        return "improved"
    if delta <= -10:
        return "slipped sharply"
    if delta < 0:
        return "slipped"
    return "held steady"


def _kind_phrase(kind: str) -> str:
    return KIND_PHRASES.get(kind, kind.replace("_", " "))


async def gather_review_data(
    session: AsyncSession, period_days: int = 7
) -> dict[str, Any]:
    """Structured facts for the review: current state plus deltas.

    The week-on-week delta compares each project's latest snapshot with
    its *oldest snapshot inside the window* — the closest thing to "where
    it stood a week ago" without assuming any particular scan cadence.
    Projects with a single snapshot get ``delta: None``.

    The current-state side is freshness-filtered, so a project deleted
    from disk stops contributing to ``average_active_score``.  The
    baseline side deliberately is not: it asks where a *surviving*
    project stood a week ago, and rows for the deleted ones are dropped
    anyway when the two sides are joined by name below.
    """
    result = await session.execute(latest_snapshot_query())
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
            # ``kind`` is what the prompt sees — the titles carry counts
            # ("Prune 7 stale branches") and must not reach the model.
            # Both are kept: the titles are what ``stats`` is audited
            # against and what the fallback narrative quotes.
            "top_recommendations": [
                {
                    "kind": r.kind,
                    "title": r.title,
                    "points": r.points,
                    "severity": r.severity,
                }
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
    """Deterministic, figure-free prompt from the gathered facts.

    Contains no numbers by construction — see the note above
    :data:`REVIEW_INSTRUCTIONS` for the two live failures that motivated
    it. Project names pass through unaltered: a name is an identifier the
    model must be able to quote, not a quantity it can restate as a
    finding.
    """
    lines = [
        "Weekly review of a personal software portfolio.",
        "",
        "Projects, with health and how they moved over the period:",
    ]
    for p in data["projects"]:
        line = (
            f"- {p['name']} [{p['status']}] — {score_band(p['score'])}, "
            f"{delta_phrase(p['delta'])}"
        )
        if p["top_recommendations"]:
            recs = "; ".join(
                _kind_phrase(r["kind"])
                + (" [RISK]" if r["severity"] == "risk" else "")
                for r in p["top_recommendations"]
            )
            line += f" — outstanding: {recs}"
        lines.append(line)
    lines += ["", REVIEW_INSTRUCTIONS]
    return "\n".join(lines)


def build_facts_section(data: dict[str, Any]) -> str:
    """Deterministic figures block — numbers never come from the LLM.

    Prepended to the model's prose so every real figure in the stored
    narrative is one this function computed. Was ``build_movers_section``
    and reported only the deltas; the totals joined it when the prompt
    stopped carrying them, or the review would have lost them entirely.
    """
    totals = data["totals"]
    average = totals["average_active_score"]
    lines = [
        f"{totals['project_count']} projects tracked, "
        f"{totals['active_count']} active"
        + (
            f"; average active score {average}."
            if average is not None
            else "; no active projects to average."
        ),
        f"{totals['recoverable_points']} points recoverable across the "
        f"portfolio; {totals['risk_count']} risk item(s).",
    ]

    movers = [p for p in data["projects"] if p["delta"]]
    if not movers:
        lines.append("What moved: no score changes this period.")
    else:
        moved = ", ".join(
            f"{p['name']} {p['delta']:+d}"
            for p in sorted(movers, key=lambda p: p["delta"], reverse=True)
        )
        lines.append(f"What moved: {moved}.")
    return "\n".join(lines)


def build_fallback_narrative(data: dict[str, Any]) -> str:
    """Deterministic digest used when llama-server is unavailable."""
    lines = [
        f"Weekly project review ({data['period_days']} days) — "
        "generated without LLM narration.",
        build_facts_section(data),
    ]
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
    from sysadmin.core.llm_client import LLMClient

    data = await gather_review_data(session, period_days)
    if not data["projects"]:
        logger.info("project_review_skipped_no_data")
        return None

    # Inference can take minutes and Postgres may enforce
    # idle_in_transaction_session_timeout (1min on this host, which
    # killed the connection mid-generation when found live) — end the
    # read transaction now; the INSERT below begins a fresh one.
    await session.commit()

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
    if narrative is not None:
        # Numbers first, deterministically; the model's prose follows,
        # with the markdown it was told not to emit stripped off.
        narrative = f"{build_facts_section(data)}\n\n{strip_markdown(narrative)}"
    else:
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
