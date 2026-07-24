"""Project Organiser Agent — scans ~/projects, computes health scores.

Detects:
- Stale projects (no recent commits)
- Stale/merged branches
- TODO/FIXME counts
- Missing documentation (README, CLAUDE.md)
- Project size
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sysadmin.agents.base import AgentResult, BaseAgent
from sysadmin.config import get_config
from sysadmin.models.project_snapshot import ProjectSnapshot
from sysadmin.utils.git import (
    get_branches,
    get_last_commit_date,
    get_repo,
    get_repo_size_mb,
    get_stale_branches,
    has_remote,
)

logger = logging.getLogger(__name__)

PROJECT_MARKERS = {".git", "pyproject.toml", "package.json", "Cargo.toml", "go.mod"}


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

        # Discover projects
        projects = await asyncio.to_thread(self._discover_projects, projects_root)

        # Include explicit project paths from projects.yaml
        if config.projects and config.projects.projects:
            discovered_set = set(projects)
            for mp in config.projects.projects:
                if mp.path:
                    p = Path(mp.path)
                    if p.exists() and p not in discovered_set:
                        projects.append(p)

        alerts_raised = 0

        for project_path in projects:
            snapshot = await asyncio.to_thread(
                self._analyse_project, project_path, agent_config
            )
            session.add(snapshot)

            # Alert on low health scores
            if snapshot.health_score < 40:
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=f"Project {snapshot.project_name} health critical",
                    message=f"Health score: {snapshot.health_score}/100",
                    details=snapshot.findings,
                )
                alerts_raised += 1

        return AgentResult(
            findings_count=len(projects),
            alerts_raised=alerts_raised,
            details={"projects_scanned": len(projects)},
        )

    def _discover_projects(self, root: Path) -> list[Path]:
        """Find directories that look like projects."""
        projects = []
        try:
            for entry in sorted(root.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                # Check for project markers
                if any((entry / marker).exists() for marker in PROJECT_MARKERS):
                    projects.append(entry)
        except PermissionError:
            logger.warning("permission_denied_scanning_projects", extra={"path": str(root)})
        return projects

    def _analyse_project(
        self, project_path: Path, agent_config
    ) -> ProjectSnapshot:
        """Analyse a single project and build a snapshot."""
        name = project_path.name
        findings: dict[str, Any] = {}
        score = 100

        # Git analysis
        repo = get_repo(project_path)
        last_commit_at = None
        branch_count = 0
        stale_branch_count = 0
        has_remote_flag = False

        if repo:
            last_commit_at = get_last_commit_date(repo)
            branches = get_branches(repo)
            branch_count = len(branches)
            stale_branches = get_stale_branches(repo, agent_config.stale_branch_days)
            stale_branch_count = len(stale_branches)
            has_remote_flag = has_remote(repo)

            if stale_branches:
                findings["stale_branches"] = stale_branches
                # Cap deduction at 5 branches
                score -= 5 * min(stale_branch_count, 5)

            # Staleness check
            if last_commit_at:
                if last_commit_at.tzinfo is None:
                    last_commit_at = last_commit_at.replace(tzinfo=timezone.utc)
                days_since = (datetime.now(timezone.utc) - last_commit_at).days
                if days_since > 60:
                    score -= 15
                    findings["stale"] = f"No commits in {days_since} days"
                elif days_since > 30:
                    score -= 10
                    findings["aging"] = f"No commits in {days_since} days"

            if not has_remote_flag:
                findings["no_remote"] = True

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
                score -= 5 * (total_todos // 10)

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
                    node_modules.stat().st_mtime, tz=timezone.utc
                )
                nm_days = (datetime.now(timezone.utc) - nm_mtime).days
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
