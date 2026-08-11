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
from sysadmin.core.models.alert import Alert
from sysadmin.monitor.services import get_services, services_by_project
from sysadmin.projects import nudges
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
from sysadmin.projects.next_action import eligible_candidates
from sysadmin.projects.roadmap import scan_roadmap
from sysadmin.projects.snapshots import load_action_streaks
from sysadmin.registry import load_registry

logger = logging.getLogger(__name__)

#: Statuses whose commit staleness is penalised.  ``dormant`` and
#: ``archived`` are declared exemptions; ``undeclared`` is not one —
#: nobody has said the project is resting, so it is scored as though
#: it were active and reported as undeclared separately.
ACTIVELY_SCORED = frozenset({"active", "undeclared"})

#: The one place the health alert's title is built.  Raising and
#: resolving derive from this function, so the two cannot drift — the
#: failure mode of a hand-written title pattern is a resolve that quietly
#: matches nothing and an alerts table that only ever grows.
_ALERT_TITLE_SUFFIX = "health critical"


def _alert_title(project_name: str) -> str:
    return f"Project {project_name} {_ALERT_TITLE_SUFFIX}"


#: SQL ``LIKE`` form of the above, for the set-based resolve.
_ALERT_TITLE_LIKE = f"Project % {_ALERT_TITLE_SUFFIX}"

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
        still_failing: set[str] = set()
        written: list[ProjectSnapshot] = []
        # Keyed by *directory* name, because that is what
        # ``_analyse_project`` writes into ``project_name`` — a manifest's
        # ``name:`` is free text and need not match the directory, so
        # keying on ``entry.name`` would silently drop the override for
        # any project where the two differ.
        nudge_thresholds: dict[str, int] = {}

        for entry in registry.entries:
            if not entry.declared:
                undeclared += 1

            snapshot = await asyncio.to_thread(
                self._analyse_project, entry.path, agent_config, entry.status
            )
            session.add(snapshot)
            written.append(snapshot)
            scored[str(entry.path)] = (snapshot.findings, snapshot.health_score)
            if entry.idle_nudge_days is not None:
                nudge_thresholds[entry.path.name] = entry.idle_nudge_days

            threshold = self._effective_threshold(entry, agent_config)
            if snapshot.health_score < threshold:
                still_failing.add(_alert_title(snapshot.project_name))
                await self.raise_alert(
                    session,
                    severity="warning",
                    title=_alert_title(snapshot.project_name),
                    message=(
                        f"Health score: {snapshot.health_score}/100 "
                        f"(alert threshold {threshold})"
                    ),
                    details=snapshot.findings,
                )
                alerts_raised += 1

        alerts_resolved = await self._resolve_recovered(session, still_failing)

        nudged = await self._nudge_idle_projects(
            session, written, nudge_thresholds, agent_config
        )

        estate_written = await asyncio.to_thread(
            self._emit_estate, registry, agent_config, scored
        )

        return AgentResult(
            findings_count=len(registry.entries),
            alerts_raised=alerts_raised + nudged["raised"] + nudged["escalated"],
            details={
                "projects_scanned": len(registry.entries),
                "undeclared": undeclared,
                "alerts_resolved": alerts_resolved,
                "nudges": nudged,
                "estate": str(estate_written) if estate_written else None,
            },
        )

    async def _nudge_idle_projects(
        self,
        session,
        written: list[ProjectSnapshot],
        thresholds: dict[str, int],
        agent_config,
    ) -> dict[str, int]:
        """Raise, escalate and clear the "you said you would" nudges.

        Session 31.  The policy — eligibility, the day thresholds, the
        quiet-then-loud ladder — lives in
        :mod:`sysadmin.projects.nudges` and
        :mod:`sysadmin.projects.next_action`; what is decided *here* is
        the alert lifecycle, and it differs from the health alerts above
        in one way that matters.

        **A nudge is raised once per open nudge, not once per scan.**
        :meth:`BaseAgent.raise_alert` inserts unconditionally, and the
        organiser runs daily, so the health-alert pattern of re-raising
        every scan writes one row per day per stuck project.  On a
        commitment that is *meant* to stay open for a week or more, that
        is the pile-up this repository has already been through, dressed
        up as a feature — and an unacknowledged count that climbs on its
        own trains the reader to clear the tray without looking.

        **Escalation resolves the quiet row and raises a loud one**
        rather than updating the severity in place.  The tray fingerprints
        notifications as ``"{severity}:{title}"``, so an in-place change
        keeps the ``info`` fingerprint it has already suppressed and the
        escalation is never spoken — the one thing the escalation is for.
        Two rows also leave the history readable: when it went quiet, and
        when it got loud.

        The scan's own snapshots are evaluated (``written``), not a
        re-read of the table, and the flush below is what makes them
        visible to the history query — without it the newest point in
        every series would be yesterday's scan and a streak would be a
        day short.

        Returns:
            ``{"raised", "escalated", "resolved"}`` counts, reported in
            ``agent_runs.details`` so a silent nudge run is
            distinguishable from one that never executed.
        """
        settings = agent_config.idle_nudges
        if not settings.enabled:
            return {"raised": 0, "escalated": 0, "resolved": 0}

        await session.flush()

        candidates, _ = eligible_candidates(written)
        streaks = await load_action_streaks(session, [c.name for c in candidates])
        due = nudges.evaluate(
            candidates,
            streaks,
            thresholds,
            default_days=settings.days,
            # The gap, not a multiplier: a project that relaxes its own
            # threshold moves when the clock starts, not how long the
            # escalation waits afterwards.
            escalation_gap=max(0, settings.escalate_days - settings.days),
        )

        # Read the open nudges only when there is something to compare
        # them against.  Nothing due still has to *resolve* below — a
        # project whose action moved has no candidate to look up — but
        # that is one statement rather than two.
        open_nudges = await self._open_nudges(session) if due else {}
        raised = 0
        escalated = 0
        for nudge in due:
            existing = open_nudges.get(nudge.title)
            if existing is not None:
                loudness = nudges.SEVERITY_ORDER
                if loudness.get(nudge.severity, 0) <= loudness.get(existing.severity, 0):
                    continue
                existing.resolved = True
                existing.resolved_at = datetime.now(UTC)
                escalated += 1
            else:
                raised += 1

            await self.raise_alert(
                session,
                severity=nudge.severity,
                title=nudge.title,
                message=nudge.message,
                details=nudge.details,
            )

        resolved = await self._resolve_moved_on(
            session, {nudge.title for nudge in due}
        )
        return {"raised": raised, "escalated": escalated, "resolved": resolved}

    async def _open_nudges(self, session) -> dict[str, Alert]:
        """Every unresolved idle-nudge, by title, loudest kept on a tie.

        A duplicate title should not exist — this method is why — but if
        one ever does, comparing against the *quietest* row would
        re-escalate on every scan, so the loudest wins and the leftovers
        are cleared by :meth:`_resolve_moved_on` when the action moves.
        """
        from sqlalchemy import select

        result = await session.execute(
            select(Alert).where(
                Alert.agent == self.name,
                Alert.resolved.is_(False),
                Alert.title.like(nudges.NUDGE_TITLE_LIKE),
            )
        )
        open_by_title: dict[str, Alert] = {}
        for alert in result.scalars().all():
            current = open_by_title.get(alert.title)
            if current is None or nudges.SEVERITY_ORDER.get(
                alert.severity, 0
            ) > nudges.SEVERITY_ORDER.get(current.severity, 0):
                open_by_title[alert.title] = alert
        return open_by_title

    async def _resolve_moved_on(self, session, still_nudged: set[str]) -> int:
        """Close every open nudge this scan did not re-state.

        The inverse question, like :meth:`_resolve_recovered` and for the
        same reason: the reasons a nudge stops applying are *the action
        changed*, *the project was declared dormant*, *the handoff was
        cleared*, *the repository was deleted* — and only the first is
        observable as an event.  A per-project loop would leave the rest
        open forever, and retention purges resolved rows only.

        The rows raised moments ago in this same transaction are excluded
        by title rather than by timestamp: an exact comparison cannot
        race the clock those inserts were stamped with.
        """
        from sqlalchemy import update

        conditions = [
            Alert.agent == self.name,
            Alert.resolved.is_(False),
            Alert.title.like(nudges.NUDGE_TITLE_LIKE),
        ]
        if still_nudged:
            conditions.append(Alert.title.notin_(sorted(still_nudged)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "project_nudges_resolved",
                extra={"agent": self.name, "count": resolved},
            )
            self._queue_event(
                "alert.resolved",
                {
                    "agent": self.name,
                    "match": nudges.NUDGE_TITLE_LIKE,
                    "count": resolved,
                },
            )
        return resolved

    async def _resolve_recovered(self, session, still_failing: set[str]) -> int:
        """Resolve every health alert this scan did **not** re-raise.

        Deliberately set-based, where the two reference agents
        (:mod:`sysadmin.monitor.agent`, :mod:`sysadmin.units.agent`) loop
        and call :meth:`BaseAgent.resolve_alerts` once per recovered
        item.  Their populations are fixed by configuration; a project's
        is not.  A project deleted from disk never appears in a scan, so
        it can never be observed *recovering*, so a per-project loop
        would leave its alert unresolved forever — and retention purges
        resolved rows only.  That is exactly how 1,664 rows accumulated
        by 2026-08-07, 326 of them sharing one title.

        Asking the inverse question — "which of my open alerts would
        this scan not raise?" — closes recovery, deletion, rename and
        re-declaration as ``archived`` in one statement, and cannot
        drift from the raise path because both titles come from
        :func:`_alert_title`.

        The rows raised moments ago in this same transaction are excluded
        by ``still_failing``, not by timestamp: a title comparison is
        exact, whereas a "created before now" test races the clock the
        inserts were stamped with.

        Returns:
            Number of alerts resolved.
        """
        from sqlalchemy import update

        conditions = [
            Alert.agent == self.name,
            Alert.resolved.is_(False),
            Alert.title.like(_ALERT_TITLE_LIKE),
        ]
        if still_failing:
            conditions.append(Alert.title.notin_(sorted(still_failing)))

        result = await session.execute(
            update(Alert)
            .where(*conditions)
            .values(resolved=True, resolved_at=datetime.now(UTC))
        )
        resolved: int = result.rowcount or 0
        if resolved:
            logger.info(
                "project_alerts_resolved",
                extra={"agent": self.name, "count": resolved},
            )
            self._queue_event(
                "alert.resolved",
                {"agent": self.name, "match": _ALERT_TITLE_LIKE, "count": resolved},
            )
        return resolved

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

        **An archived project's alert suppression is absolute**, not
        "unless it scores badly enough". The caller's condition is
        ``score < threshold`` and the score is clamped with ``max(0,
        …)``, so a threshold of 0 makes the condition ``score < 0`` —
        unreachable by construction, at any score, for any repository.
        Documented because it did not read that way (SNAG-PROJ-012) and
        pinned by a test; the mechanism is worth keeping as it is, since
        a threshold of 0 expresses "never alert" more clearly than a
        special case in the caller would.

        An explicit ``alert_threshold`` in the manifest overrides this,
        including on an archived project — a deliberate escape hatch for
        a retired repository somebody still wants warned about.
        """
        if entry.alert_threshold is not None:
            return entry.alert_threshold
        return 0 if entry.status == "archived" else agent_config.alert_threshold

    def _analyse_project(
        self, project_path: Path, agent_config, status: str = "active"
    ) -> ProjectSnapshot:
        """Analyse a single project and build a snapshot.

        ``status`` shapes the rubric, and shapes **only two deductions**:

        - ``dormant`` and ``archived`` waive the *commit staleness*
          penalty. The project is resting on purpose, so the date is
          recorded and not charged for.
        - ``archived`` additionally waives the *stale branch* penalty.
          Branches nobody will merge are not a defect in a retired repo.

        That is the whole list. It is emphatically **not** "git hygiene
        stops mattering at retirement", which is what three places used
        to say (SNAG-PROJ-011): a leftover ``.git/index.lock`` still
        costs an archived project 5 points, and a missing git remote is
        still reported as a risk. Everything else — README, CLAUDE.md,
        code markers, ``.env``, node_modules, size — is scored
        identically whatever the status, so the number keeps meaning
        "how tidy is this directory" rather than "how tidy is this
        directory, for a given intent".

        ``undeclared`` is scored exactly like ``active``: an absent
        decision is not a decision to waive anything.
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
            todos = self._count_todos(
                project_path, agent_config.todo_patterns, findings
            )
            # ``todo_count`` and ``fixme_count`` stay exact counts of the
            # markers they are named after.  The penalty is levied on all
            # configured patterns, so the full per-pattern mapping goes
            # into ``findings['todos']`` and the recommendation quotes it
            # by name — a project penalised for 40 HACK markers used to
            # read "0 TODOs, 0 FIXMEs" with an unexplained deduction.
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

    #: File types the marker scan reads.  ``*.md`` was here and is not
    #: any more: a repository's own ``snag_list.md``, ``tasks.md`` and
    #: ``handoff.md`` counted towards its own penalty, so writing up a
    #: defect lowered the score of the project that wrote it up.  The
    #: markers are a *code* signal, and counting them in documentation
    #: inverts the incentive the score exists to create.
    _SCANNED_INCLUDES = (
        "*.py", "*.js", "*.ts", "*.tsx", "*.vue", "*.yaml", "*.yml",
    )

    #: Per-pattern ceiling on matches *for the whole project*.  The old
    #: ``-m 1000`` is grep's **per-file** limit, so a 300-file repository
    #: could return 300,000 while the docstring claimed a cap of 1000.
    #: Enforced here, on the total, which is the number that reaches the
    #: score.
    _MAX_MATCHES_PER_PATTERN = 1000

    #: Per-file limit, kept to bound the work grep does on a generated
    #: file with tens of thousands of markers.  Named for what it is.
    _MAX_MATCHES_PER_FILE = 200

    def _count_todos(
        self,
        project_path: Path,
        patterns: list[str],
        findings: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """Count code-marker occurrences per pattern.

        Matches whole words only (``grep -w``): without it ``TODO``
        matched ``TODOS``, ``TODO_LIST`` and any prose sentence
        containing the word, so a constant named ``TODO_STATES`` cost
        points.

        Each pattern's total is capped at
        :data:`_MAX_MATCHES_PER_PATTERN` across the whole project, and
        a pattern that hits the cap is recorded in
        ``findings['todo_scan_truncated']`` — a capped count is a lower
        bound and any surface quoting it should be able to say so.
        """
        exclude_args = []
        for d in self._EXCLUDE_DIRS:
            exclude_args.extend(["--exclude-dir", d])

        include_args = [f"--include={pat}" for pat in self._SCANNED_INCLUDES]

        counts: dict[str, int] = {}
        truncated: list[str] = []
        for pattern in patterns:
            try:
                result = subprocess.run(
                    [
                        "grep", "-rnw",
                        *include_args,
                        *exclude_args,
                        "-m", str(self._MAX_MATCHES_PER_FILE),
                        "--", pattern,
                        str(project_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                count = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
                if count >= self._MAX_MATCHES_PER_PATTERN:
                    count = self._MAX_MATCHES_PER_PATTERN
                    truncated.append(pattern)
                counts[pattern] = count
            except (subprocess.TimeoutExpired, FileNotFoundError):
                counts[pattern] = 0
        if truncated and findings is not None:
            findings["todo_scan_truncated"] = truncated
        return counts
