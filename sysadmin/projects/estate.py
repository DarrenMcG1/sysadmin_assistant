"""estate.json — the scanner's output contract.

Written on every organiser run, versioned, and read by things this
repository does not own. That last part is what shapes the rest:

**Atomic.** Written to a temporary file in the same directory and then
renamed. A consumer polling the file must never catch it half-written,
and a rename within one filesystem is the only cheap way to promise that.

**Health is derived, never stored here.** ``health`` comes from the
snapshot computed in the same run, so the scoring rules can change
without a migration and without a stale score outliving the rubric that
produced it. It is deliberately *not* a second scorer: two things called
"health" that disagree would be worse than either alone.

**Services are names, not topology.** They are resolved from services.yaml
by project id. Embedding the urls and units here would make estate.json a
second place to edit when a port moves, which is the failure the whole
registry exists to stop.

**Undeclared repositories appear.** With ``"status": "undeclared"`` and
whatever can be derived. Omitting them would make the file agree with
itself and disagree with the disk.
"""

import json
import logging
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sysadmin.core.config import CodeCommitIgnoreConfig
from sysadmin.projects.git import (
    commit_count,
    current_branch,
    detect_languages,
    detect_signals,
    get_last_code_commit_date,
    get_last_commit_date,
    get_repo,
    is_dirty,
    remote_url,
)
from sysadmin.registry import ProjectEntry, Registry

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

#: ``findings`` key → the flag it becomes.  Flags are the shortest honest
#: label for a deduction, so a consumer can group by them without having
#: to parse a sentence written for a human.
FINDING_FLAGS = {
    "missing_readme": "no-readme",
    "missing_claude_md": "no-claude-md",
    "no_remote": "no-remote",
    "stale": "stale",
    "aging": "aging",
    "missing_env": "no-env",
    "stale_git_lock": "git-lock",
    "stale_node_modules": "stale-node-modules",
    "todo_penalty_capped": "todo-cap-hit",
}


def _iso_date(stamp: datetime | None) -> str | None:
    """A date, not a timestamp.

    Every consumer of these two fields compares them to other dates or
    renders them; a time-of-day would be precision nobody uses and one
    more thing to normalise across timezones.
    """
    if stamp is None:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=UTC)
    return stamp.date().isoformat()


def git_facts(path: Path, ignore: CodeCommitIgnoreConfig) -> dict[str, Any]:
    """The git half of one project's record.

    ``last_commit`` and ``last_code_commit`` are both reported, and they
    differ whenever an estate-wide sweep touched the repository without
    being work in it. Publishing only the second would hide that a sweep
    happened; publishing only the first is what made every dormant
    project read as touched four days ago.
    """
    repo = get_repo(path)
    if repo is None:
        return {
            "last_commit": None,
            "last_code_commit": None,
            "branch": None,
            "commits": 0,
            "dirty": False,
            "remote": None,
            "ignored_commits": 0,
        }

    last_code, skipped = get_last_code_commit_date(
        repo, ignore.message_patterns, ignore.shas, ignore.max_walk
    )
    return {
        "last_commit": _iso_date(get_last_commit_date(repo)),
        "last_code_commit": _iso_date(last_code),
        "branch": current_branch(repo),
        "commits": commit_count(repo),
        "dirty": is_dirty(repo),
        "remote": remote_url(repo),
        "ignored_commits": skipped,
    }


def health_from(findings: dict[str, Any] | None, score: int | None) -> dict[str, Any]:
    """The health block, derived from the run that produced ``findings``.

    Not a second rubric. The organiser has one, it runs anyway, and a
    number here that disagreed with the one on the board would be a bug
    nobody could adjudicate.
    """
    findings = findings or {}
    flags = sorted(
        flag for key, flag in FINDING_FLAGS.items() if findings.get(key)
    )
    if findings.get("roadmap", {}).get("next_action") is None:
        flags.append("no-next-action")
    return {"score": score, "flags": flags}


def project_record(
    entry: ProjectEntry,
    services: list[str],
    ignore: CodeCommitIgnoreConfig,
    findings: dict[str, Any] | None = None,
    score: int | None = None,
) -> dict[str, Any]:
    """One project, as estate.json describes it."""
    manifest = entry.manifest
    return {
        "id": entry.id,
        "name": entry.name,
        "path": entry.relative,
        "category": entry.category,
        "status": entry.status,
        "declared": entry.declared,
        "summary": manifest.summary if manifest else None,
        "tags": list(manifest.tags) if manifest else [],
        "supersedes": list(manifest.supersedes) if manifest else [],
        "languages": detect_languages(entry.path),
        "git": git_facts(entry.path, ignore),
        "signals": detect_signals(entry.path),
        "decisions": [
            {
                "date": decision.date.isoformat(),
                "change": decision.change,
                "reason": decision.reason,
                **({"note": decision.note} if decision.note else {}),
            }
            for decision in (manifest.decisions if manifest else [])
        ],
        "services": services,
        "health": health_from(findings, score),
    }


def build_estate(
    registry: Registry,
    services_by_project: dict[str, list[str]],
    ignore: CodeCommitIgnoreConfig,
    snapshots: dict[str, tuple[dict[str, Any] | None, int | None]] | None = None,
    generated: datetime | None = None,
) -> dict[str, Any]:
    """The whole payload.

    ``snapshots`` maps a project path to ``(findings, score)`` from the
    run in progress. Absent, every ``health`` is reported with a null
    score rather than a guess — a file that says "unknown" is usable and
    a file that says 100 because nothing was measured is not.
    """
    snapshots = snapshots or {}
    stamp = generated or datetime.now(UTC)

    projects = []
    for entry in registry.entries:
        findings, score = snapshots.get(str(entry.path), (None, None))
        projects.append(
            project_record(
                entry,
                services_by_project.get(entry.id, []) if entry.declared else [],
                ignore,
                findings,
                score,
            )
        )

    projects.sort(key=lambda record: record["id"])
    return {
        "schema": SCHEMA_VERSION,
        "generated": stamp.replace(microsecond=0).isoformat(),
        "root": str(registry.root),
        "projects": projects,
    }


def write_atomic(path: Path, payload: dict[str, Any]) -> Path:
    """Write ``payload`` so a reader never sees a partial file.

    The temporary file is created in the destination's own directory
    because ``os.replace`` is only atomic within a filesystem, and
    ``/tmp`` is frequently a different one.
    """
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return path


def estate_path(configured: str, projects_root: str | Path) -> Path:
    """Where estate.json goes — relative paths resolve against the root."""
    path = Path(configured).expanduser()
    return path if path.is_absolute() else Path(projects_root).expanduser() / path
