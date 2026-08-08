"""Project Organiser Agent — scans ~/projects, computes health scores.

Detects:
- Stale projects (no recent commits)
- Stale/merged branches
- TODO/FIXME counts
- Missing documentation (README, CLAUDE.md)
- Roadmap state (handoff, tasks, snags) — see services/roadmap.py
- Project size
"""

import asyncio
import logging
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sysadmin.core.agent import AgentResult, BaseAgent
from sysadmin.core.config import get_config
from sysadmin.monitor.services import get_services, services_by_project
from sysadmin.projects.estate import build_estate, estate_path, write_atomic
from sysadmin.projects.git import (
    get_branches,
    get_last_code_commit_date,
    get_last_commit_date,
    get_repo,
    get_repo_size_mb,
    get_stale_branches,
    has_remote,
)
from sysadmin.projects.models.project_snapshot import ProjectSnapshot
from sysadmin.projects.roadmap import scan_roadmap
from sysadmin.registry import load_registry

logger = logging.getLogger(__name__)

#: Statuses whose commit staleness is penalised.  ``dormant`` and
#: ``archived`` are declared exemptions; ``undeclared`` is not one —
#: nobody has said the project is resting, so it is scored as though
#: it were active and reported as undeclared separately.
ACTIVELY_SCORED = frozenset({"active", "undeclared"})

# Discovery, identity and declared status all come from
# sysadmin.registry now.  ``discover_projects`` and ``_infer_status`` used
# to live here and were imported by the service-discovery agent, which is
# the drift the registry exists to remove: two agents with two ideas of
# what counts as a project, whose symptom is a unit reported as an orphan
# because one sweep could not see the project the other could.


class ProjectOrganiserAgent(BaseAgent):
    """Scans projects directory and assesses project health."""

    name = "project_organiser"

    async def _execute(self, session) -> AgentResult:
        config = get_config()
        agent_config = config.agents.project_organiser
        projects_root = Path(agent_config.projects_root)

        if not projects_root.exists():
            logger.warning("projects_root_not_found", extra={"path": str(projects_root)})
            return AgentResult()

        registry = await asyncio.to_thread(
            load_registry, projects_root, agent_config.discovery_depth
        )

        alerts_raised = 0
        undeclared = 0
        scored: dict[str, tuple[dict, int]] = {}

        for entry in registry.entries:
            if not entry.declared:
                undeclared += 1

            snapshot = await asyncio.to_thread(
                self._analyse_project, entry.path, agent_config, entry.status
            )
            session.add(snapshot)
            scored[str(entry.path)] = (snapshot.findings, snapshot.health_score)

            threshold = self._effective_threshold(entry, agent_config)
            if snapshot.health_score < threshold:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"Project {snapshot.project_name} health critical",
                    message=(
                        f"Health score: {snapshot.health_score}/100 "
                        f"(alert threshold {threshold})"
                    ),
                    details=snapshot.findings,
                )
                alerts_raised += 1

        estate_written = await asyncio.to_thread(
            self._emit_estate, registry, agent_config, scored
        )

        return AgentResult(
            findings_count=len(registry.entries),
            alerts_raised=alerts_raised,
            details={
                "projects_scanned": len(registry.entries),
                "undeclared": undeclared,
                "estate": str(estate_written) if estate_written else None,
            },
        )

    @staticmethod
    def _emit_estate(registry, agent_config, scored) -> Path | None:
        """Write estate.json for this run.

        Failure here never fails the scan. The snapshots are already in
        the session and are the durable record; estate.json is a
        re-projection of them for consumers outside this repository, and
        losing one run of it is a smaller problem than losing the scan
        that produced it.
        """
        settings = agent_config.estate
        if not settings.enabled:
            return None

        try:
            services = services_by_project(get_services())
            payload = build_estate(
                registry, services, settings.code_commit_ignore, scored
            )
            return write_atomic(
                estate_path(settings.path, agent_config.projects_root), payload
            )
        except Exception:  # noqa: BLE001 - reported, never fatal to the scan
            logger.exception("estate_write_failed")
            return None

    @staticmethod
    def _effective_threshold(entry, agent_config) -> int:
        """The health-score floor below which this project alerts.

        An explicit ``alert_threshold`` in the manifest wins.  Failing
        that, an ``archived`` project gets 0 — retirement is not a defect
        — and everything else the global default.  ``undeclared`` is
        undecided rather than exempt: nobody has said this project is
        resting, so it is still scored and still alerts.
        """
        if entry.alert_threshold is not None:
            return entry.alert_threshold
        return 0 if entry.status == "archived" else agent_config.alert_threshold

    def _analyse_project(
        self, project_path: Path, agent_config, status: str = "active"
    ) -> ProjectSnapshot:
        """Analyse a single project and build a snapshot.

        ``status`` shapes the rubric: a ``dormant`` project is resting on
        purpose, so commit staleness is recorded but not penalised; an
        ``archived`` one additionally keeps its stale branches penalty-free
        — git hygiene stops mattering at retirement.  ``undeclared`` is
        scored exactly like ``active``: an absent decision is not a
        decision to waive anything.  Everything else (docs, TODOs, locks)
        still counts, so the score keeps meaning "how tidy is this
        directory" whatever the intent.
        """
        name = project_path.name
        findings: dict[str, Any] = {"status": status}
        score = 100

        # Git analysis
        repo = get_repo(project_path)
        last_commit_at = None
        newest_commit_at = None
        ignored_commits = 0
        branch_count = 0
        stale_branch_count = 0
        has_remote_flag = False

        if repo:
            # Staleness is measured from the last commit that changed real
            # work.  A single sweep across forty repositories left every
            # one of them looking touched on the same day, which is the
            # opposite of what the figure is for.  ``last_commit_at`` on
            # the snapshot therefore carries the *code* date — every
            # downstream staleness reading is derived from that column —
            # and the true newest commit is recorded beside it in
            # ``findings`` so the difference is visible, not applied
            # behind the reader's back.
            newest_commit_at = get_last_commit_date(repo)
            last_commit_at, ignored_commits = get_last_code_commit_date(
                repo,
                agent_config.estate.code_commit_ignore.message_patterns,
                agent_config.estate.code_commit_ignore.shas,
                agent_config.estate.code_commit_ignore.max_walk,
            )
            if ignored_commits:
                findings["git"] = {
                    "last_commit": (
                        newest_commit_at.date().isoformat()
                        if newest_commit_at else None
                    ),
                    "last_code_commit": (
                        last_commit_at.date().isoformat() if last_commit_at else None
                    ),
                    "ignored_commits": ignored_commits,
                }
            branches = get_branches(repo)
            branch_count = len(branches)
            stale_branches = get_stale_branches(repo, agent_config.stale_branch_days)
            stale_branch_count = len(stale_branches)
            has_remote_flag = has_remote(repo)

            if stale_branches:
                findings["stale_branches"] = stale_branches
                if status != "archived":
                    # Cap deduction at 5 branches
                    score -= 5 * min(stale_branch_count, 5)

            # Staleness check — recorded for every project, but only an
            # *active* one is penalised for it
            if last_commit_at:
                if last_commit_at.tzinfo is None:
                    last_commit_at = last_commit_at.replace(tzinfo=UTC)
                days_since = (datetime.now(UTC) - last_commit_at).days
                if days_since > 60:
                    if status in ACTIVELY_SCORED:
                        score -= 15
                    findings["stale"] = f"No commits in {days_since} days"
                elif days_since > 30:
                    if status in ACTIVELY_SCORED:
                        score -= 10
                    findings["aging"] = f"No commits in {days_since} days"

            if not has_remote_flag:
                findings["no_remote"] = True

            # Subject of the last commit — the estate board's last-resort
            # "next action" when a project keeps no roadmap documents at
            # all.  "Where you actually stopped" is still recoverable from
            # git even when nobody wrote it down.
            try:
                findings["last_commit_subject"] = str(repo.head.commit.summary)[:200]
            except Exception:  # noqa: BLE001 - unborn HEAD, corrupt ref, etc.
                pass

        # Roadmap documents — recorded, never scored.  A deduction here
        # would move every active project's health score at once and could
        # trip alert thresholds as a side effect of adding a feature; that
        # is a decision to take deliberately, not to slip in.  Advice is
        # still produced (see services/recommendations.py) at 0 points, the
        # same shape `no_remote` already uses.
        findings["roadmap"] = scan_roadmap(project_path)

        # Documentation checks
        has_readme = (project_path / "README.md").exists()
        has_claude_md = (project_path / "CLAUDE.md").exists()

        if not has_readme:
            score -= 10
            findings["missing_readme"] = True
        if not has_claude_md:
            score -= 10
            findings["missing_claude_md"] = True

        # TODO/FIXME scanning
        todo_count = 0
        fixme_count = 0
        if agent_config.track_todos:
            todos = self._count_todos(project_path, agent_config.todo_patterns)
            todo_count = todos.get("TODO", 0)
            fixme_count = todos.get("FIXME", 0)
            total_todos = sum(todos.values())
            if total_todos > 0:
                findings["todos"] = todos
                score -= self._todo_penalty(
                    total_todos, agent_config.max_todo_penalty, findings
                )

        # Missing .env check
        env_example = (project_path / ".env.example").exists()
        env_file = (project_path / ".env").exists()
        if env_example and not env_file:
            score -= 10
            findings["missing_env"] = True

        # Stale git lock
        if (project_path / ".git" / "index.lock").exists():
            score -= 5
            findings["stale_git_lock"] = True

        # Stale node_modules
        node_modules = project_path / "node_modules"
        if node_modules.exists():
            try:
                nm_mtime = datetime.fromtimestamp(
                    node_modules.stat().st_mtime, tz=UTC
                )
                nm_days = (datetime.now(UTC) - nm_mtime).days
                if nm_days > 90:
                    score -= 5
                    findings["stale_node_modules"] = f"{nm_days} days old"
            except OSError:
                pass

        # Size
        total_size_mb = get_repo_size_mb(project_path)

        # Clamp score
        score = max(0, min(100, score))

        return ProjectSnapshot(
            project_name=name,
            project_path=str(project_path),
            health_score=score,
            last_commit_at=last_commit_at,
            branch_count=branch_count,
            stale_branch_count=stale_branch_count,
            todo_count=todo_count,
            fixme_count=fixme_count,
            has_readme=has_readme,
            has_claude_md=has_claude_md,
            total_size_mb=total_size_mb,
            findings=findings,
        )

    TODO_PENALTY_PER_BLOCK = 5
    TODO_BLOCK_SIZE = 10

    def _todo_penalty(
        self,
        total_todos: int,
        cap: int | None,
        findings: dict[str, Any],
    ) -> int:
        """Points to deduct for TODO/FIXME markers, bounded by ``cap``.

        Five points per ten markers, as before — but uncapped this pinned
        a 300-marker project at 0 forever, so the score said nothing about
        whether anything else had improved. The cap (default 30) keeps the
        signal alive; when it bites, the raw figure is recorded in
        ``findings`` so the deduction stays explainable. ``cap=None``
        restores the old unbounded behaviour.
        """
        raw = self.TODO_PENALTY_PER_BLOCK * (total_todos // self.TODO_BLOCK_SIZE)
        if cap is None or raw <= cap:
            return raw
        applied = max(cap, 0)
        findings["todo_penalty_capped"] = {
            "raw_penalty": raw,
            "applied_penalty": applied,
            "total_markers": total_todos,
        }
        return applied

    # Directories that contain third-party or generated code
    _EXCLUDE_DIRS = [
        "node_modules", "__pycache__", ".venv", "venv", ".git",
        "dist", "build", ".next", ".nuxt", "coverage",
        ".tox", ".mypy_cache", ".pytest_cache", "site-packages",
        ".eggs", "egg-info", "vendor", "bower_components",
    ]

    def _count_todos(
        self, project_path: Path, patterns: list[str]
    ) -> dict[str, int]:
        """Count TODO/FIXME/etc. occurrences using grep. Capped at 1000 matches."""
        exclude_args = []
        for d in self._EXCLUDE_DIRS:
            exclude_args.extend(["--exclude-dir", d])

        counts: dict[str, int] = {}
        for pattern in patterns:
            try:
                result = subprocess.run(
                    [
                        "grep", "-rn",
                        "--include=*.py", "--include=*.js",
                        "--include=*.ts", "--include=*.tsx", "--include=*.vue",
                        "--include=*.md", "--include=*.yaml", "--include=*.yml",
                        *exclude_args,
                        "-m", "1000",
                        pattern,
                        str(project_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                counts[pattern] = count
            except (subprocess.TimeoutExpired, FileNotFoundError):
                counts[pattern] = 0
        return counts
