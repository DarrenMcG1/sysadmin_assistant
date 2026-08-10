"""Turn a project snapshot into ranked, actionable housekeeping advice.

Each recommendation mirrors one deduction in
``ProjectOrganiserAgent._analyse_project``, so ``points`` is a truthful
"fix this and the health score recovers exactly this much".  The rules
must stay in lock-step with the analyser: when a deduction changes there,
its recommendation changes here (test_recommendations.py cross-checks the
arithmetic).

Status-awareness matches the scorer too — a deduction the project's
status waives produces no recommendation, because there are no points
behind it.  The one deliberate exception is ``no_remote``: it never costs
points (the scorer only records it) but surfaces as a ``risk``
recommendation ranked above everything, because "sole copy of this repo
is on this disk" matters more than any score arithmetic.

Pure module: no DB access, no FastAPI — give it a snapshot, get a list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sysadmin.core.contracts import RecommendationInfo

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sysadmin.core.config import ProjectOrganiserConfig
    from sysadmin.projects.models.project_snapshot import ProjectSnapshot

# Mirrors ProjectOrganiserAgent — 5 points per 10 markers
TODO_PENALTY_PER_BLOCK = 5
TODO_BLOCK_SIZE = 10
STALE_BRANCH_POINTS = 5
STALE_BRANCH_CAP = 5


def recommendations_for(
    snapshot: ProjectSnapshot,
    agent_config: ProjectOrganiserConfig,
) -> list[RecommendationInfo]:
    """Ranked advice for one project's latest snapshot.

    Ordering: ``risk`` severity first, then by recoverable points
    (descending), then title for stability.
    """
    findings = snapshot.findings or {}
    status = findings.get("status", "active")
    recs: list[RecommendationInfo] = []

    if findings.get("no_remote"):
        recs.append(RecommendationInfo(
            kind="risk",
            severity="risk",
            title="Add a git remote",
            detail=(
                "No remote configured — the only copy of this repository "
                "is on this disk."
            ),
            points=0,
            action="git remote add origin <url> && git push -u origin HEAD",
        ))

    if findings.get("missing_readme"):
        recs.append(RecommendationInfo(
            kind="docs",
            title="Write a README.md",
            detail="No README.md at the project root.",
            points=10,
            action="Create README.md",
        ))

    if findings.get("missing_claude_md"):
        recs.append(RecommendationInfo(
            kind="docs",
            title="Write a CLAUDE.md",
            detail="No CLAUDE.md — agent sessions start without project context.",
            points=10,
            action="Create CLAUDE.md",
        ))

    if findings.get("missing_env"):
        recs.append(RecommendationInfo(
            kind="config",
            title="Create .env from .env.example",
            detail=".env.example exists but .env does not.",
            points=10,
            action="Copy .env.example to .env and fill in values",
        ))

    if findings.get("stale_git_lock"):
        recs.append(RecommendationInfo(
            kind="hygiene",
            title="Remove stale .git/index.lock",
            detail="A leftover lock file is blocking git operations.",
            points=5,
            action="Delete .git/index.lock (after checking no git process runs)",
        ))

    if "stale_node_modules" in findings:
        recs.append(RecommendationInfo(
            kind="hygiene",
            title="Refresh or delete node_modules",
            detail=f"node_modules is {findings['stale_node_modules']}.",
            points=5,
            action="Delete node_modules (reinstall on next build)",
        ))

    # Stale branches only — the one git deduction ``archived`` waives,
    # exactly like the scorer.  The stale-lock and missing-remote items
    # above deliberately still apply to an archived project.
    stale_branches = findings.get("stale_branches") or []
    if stale_branches and status != "archived":
        count = len(stale_branches)
        # get_stale_branches records dicts ({name, last_commit, days_stale});
        # tolerate plain strings so hand-written findings still render
        names = [
            b["name"] if isinstance(b, dict) else str(b)
            for b in stale_branches[:5]
        ]
        recs.append(RecommendationInfo(
            kind="git",
            title=f"Prune {count} stale branch{'es' if count != 1 else ''}",
            detail=(
                "Stale: " + ", ".join(names)
                + ("…" if count > 5 else "")
            ),
            points=STALE_BRANCH_POINTS * min(count, STALE_BRANCH_CAP),
            action=(
                f"POST /api/projects/{snapshot.project_name}/branches/prune "
                "(dry run; add confirm: true to execute)"
            ),
        ))

    # Staleness — only an active project is penalised, so only an active
    # one has points to recover.  Both remedies are legitimate: commit,
    # or tell the truth in projects.yaml.
    if status == "active":
        if "stale" in findings:
            recs.append(RecommendationInfo(
                kind="activity",
                title="Commit recent work — or declare the project dormant",
                detail=str(findings["stale"]),
                points=15,
                action=(
                    "Commit, or set status: dormant (resting) / archived "
                    "(retired) in projects.yaml"
                ),
            ))
        elif "aging" in findings:
            recs.append(RecommendationInfo(
                kind="activity",
                title="Commit recent work",
                detail=str(findings["aging"]),
                points=10,
                action="Commit, or set status: dormant in projects.yaml",
            ))

    todo_points = _todo_points(findings, agent_config)
    if todo_points > 0:
        marker_counts = findings.get("todos") or {}
        total = sum(marker_counts.values())
        # Name the markers that were actually charged for.  The title
        # said "TODO/FIXME markers" whatever the mix, so a project
        # penalised for 40 HACK markers reported 0 TODOs and 0 FIXMEs
        # beside a deduction nothing on the page explained.
        breakdown = ", ".join(
            f"{name} {count}"
            for name, count in sorted(marker_counts.items())
            if count
        )
        detail = f"Every {TODO_BLOCK_SIZE} markers cost {TODO_PENALTY_PER_BLOCK} points (capped)."
        if breakdown:
            detail = f"{breakdown}. {detail}"
        if findings.get("todo_scan_truncated"):
            detail += " Count is a lower bound — the scan hit its per-pattern cap."
        recs.append(RecommendationInfo(
            kind="todos",
            title=f"Burn down {total} code markers",
            detail=detail,
            points=todo_points,
            action=f"GET /api/projects/{snapshot.project_name}/todos for the list",
        ))

    recs.extend(_roadmap_recommendations(findings, status))

    recs.sort(key=lambda r: (r.severity != "risk", -r.points, r.title))
    return recs


# A handoff older than this stops being "the next action" and becomes
# evidence the project stalled — a resume-or-park decision, not a task.
STALLED_HANDOFF_DAYS = 30


def _roadmap_recommendations(
    findings: dict, status: str
) -> list[RecommendationInfo]:
    """Advice from the roadmap documents — all worth 0 points.

    Nothing here costs health-score points (the scanner records roadmap
    state without deducting for it), so these follow the ``no_remote``
    precedent: real advice, priced honestly at zero, ranked by ordinary
    severity rather than by arithmetic it does not have.

    Everything is waived for non-active projects.  Nagging a deliberately
    dormant repo to write a session handoff is busywork dressed as
    progress, and generating it for fourteen parked scratch projects is
    how a useful signal becomes noise.
    """
    roadmap = findings.get("roadmap")
    if not isinstance(roadmap, dict) or status != "active":
        return []

    out: list[RecommendationInfo] = []
    age = roadmap.get("handoff_age_days")

    if isinstance(age, int) and age > STALLED_HANDOFF_DAYS:
        out.append(RecommendationInfo(
            kind="roadmap",
            severity="risk",
            title=f"Stalled {age} days — resume or park it",
            detail=(
                f"The handoff is {age} days old. Its next action is a record "
                "of where work stopped, not today's task."
            ),
            points=0,
            action="Pick the work back up, or set status: dormant in projects.yaml",
        ))

    missing = roadmap.get("missing_docs") or []
    if "handoff" in missing:
        out.append(RecommendationInfo(
            kind="roadmap",
            title="No session handoff",
            detail=(
                "docs/sessions/handoff.md is absent, so there is no record of "
                "where work stopped. The SessionEnd hook writes one after any "
                "session that changes something."
            ),
            points=0,
            action="Finish a session in this repo — the hook creates the file",
        ))

    open_snags = roadmap.get("open_snags") or 0
    if open_snags:
        out.append(RecommendationInfo(
            kind="roadmap",
            title=f"{open_snags} open snag{'s' if open_snags != 1 else ''}",
            detail="Recorded in the project's snag list and still open.",
            points=0,
            action="See docs/roadmap/snag_list.md",
        ))

    return out


def potential_score(snapshot: ProjectSnapshot, recs: list[RecommendationInfo]) -> int:
    """The score if every recommendation were acted on.

    Clamped to 100; when the raw score bottomed out at 0 the sum of
    per-item points can exceed the visible deficit, but "everything
    fixed" is 100 regardless.
    """
    return min(100, snapshot.health_score + sum(r.points for r in recs))


def _todo_points(findings: dict, agent_config: ProjectOrganiserConfig) -> int:
    """Recoverable points from the TODO deduction, mirroring the scorer.

    Prefer the recorded ``applied_penalty`` (the cap has already been
    worked out); otherwise recompute from the marker counts.
    """
    capped = findings.get("todo_penalty_capped")
    if capped:
        return int(capped.get("applied_penalty", 0))
    total = sum((findings.get("todos") or {}).values())
    raw = TODO_PENALTY_PER_BLOCK * (total // TODO_BLOCK_SIZE)
    cap = agent_config.max_todo_penalty
    if cap is None:
        return raw
    return min(raw, max(cap, 0))
