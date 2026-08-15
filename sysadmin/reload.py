"""Re-read config.yaml and services.yaml without restarting the daemon.

Three sittings in a row handed a restart forward (`SNAG-UNITS-005`): the
daemon reads its service registry once, in the lifespan, so an edit to
``services.yaml`` is inert until ``sudo systemctl restart``, which no agent
session can supply. The instance was worked around each time. This removes
the class.

**This module sits beside main.py on purpose**, for the reason
:mod:`sysadmin.metadata` states: both are composition roots, allowed to
import every domain, imported by no domain. A ``core/reload.py`` would
have to import ``monitor.services`` and break the rule that makes every
other boundary real (``tests/test_import_boundary.py``); a
``monitor/reload.py`` would file config.yaml's lifecycle inside one domain.

Four rules, three of them the opposite of the obvious implementation:

1. **Both files are validated before either is installed.** A reload that
   half-succeeds *across files* leaves the process running a combination
   nobody wrote, which is strictly worse than the restart it replaces —
   the operator's mental model is "the files on disk are what is running",
   and a partial install silently breaks it. :func:`parse_config` and
   :func:`load_services` were split out of their loaders for this: both
   return rather than assign, so the failure lands before the swap and the
   previously-served configuration stands untouched.

2. **Fields a reload cannot deliver are applied-and-named, not refused.**
   Nearly everything an agent reads is already re-read per run — every
   ``_execute`` calls ``get_config()`` at its top, a consequence of
   SNAG-AGENT-003 forbidding agents a startup hook. What is genuinely read
   once is small and enumerable (:data:`RESTART_ONLY`): the scheduler's
   triggers, the engine, the socket, the logging setup. Refusing the whole
   reload when one of those changes would block a threshold fix on an
   unrelated edit in the same file — and the operator would then restart,
   so the refusal delivers nothing the restart did not. Half-success is
   only dangerous when it is *silent*; this names the fields, in the
   response body and in the log, the same rule ``ports_checked``,
   ``truncated_sources`` and ``unread_surfaces`` already encode.

3. **The registry is rebuilt from the *new* config's ``projects_root``.**
   Validating the new ``services.yaml`` against the old root would check
   project ids against a directory the file being installed no longer
   names — a check that passes for the wrong reason, which is the failure
   mode keying services on ids exists to remove.

4. **Per-service in-memory state is pruned, never reset.** See
   :meth:`SysAdminAgent.forget_unknown`. Resetting would re-arm the
   three-poll degraded streak at the moment an operator is most likely to
   be poking at a failing service.

What this deliberately does **not** do is reschedule jobs. APScheduler can
``reschedule_job``, and doing so would shrink :data:`RESTART_ONLY` to the
socket, the engine and the logging setup — but ``Scheduler`` exposes no
such method today, and a reload that silently re-times the estate's cron
jobs is a larger change than the one this session was scoped for. It is
filed rather than assumed settled.
"""

import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from estate.registry import load_registry

from sysadmin.core.config import AppConfig, get_config, parse_config, set_config
from sysadmin.monitor.services import (
    ServicesFile,
    default_services_path,
    get_services,
    load_services,
    set_services,
)

logger = logging.getLogger(__name__)


#: Dotted config paths that are read **once**, at startup, with the reason.
#:
#: Each entry is a prefix: naming ``schedules`` covers every leaf under it.
#: The reason is not decoration — it is what a future reader needs to decide
#: whether a field belongs here, and ``tests/test_reload.py`` walks
#: ``main.py``'s lifespan to assert nothing read there is missing from this
#: list or from :data:`LIVE_AT_STARTUP`. A hand-maintained classification
#: that nothing checks is the ``SNAG-CFG-001`` shape — parsed by pydantic,
#: read by nobody — and this one decides what an operator is told.
RESTART_ONLY: tuple[tuple[str, str], ...] = (
    (
        "service",
        "uvicorn binds host/port once; configure_logging runs in the "
        "lifespan; CORSMiddleware is built in create_app",
    ),
    ("database", "the async engine is created once, in the lifespan"),
    ("schedules", "the daily cron jobs are registered once, at startup"),
    # One entry per scheduled job. Not the whole `agents` subtree: the
    # thresholds beside these fields ARE re-read every run, and sweeping
    # them in here would tell an operator that a threshold change needs a
    # restart when it does not — advice that is wrong in the direction
    # nobody checks.
    ("agents.sysadmin.enabled", "decides whether the health-check job exists"),
    ("agents.sysadmin.health_check_interval_seconds", "the job's IntervalTrigger"),
    ("agents.sysadmin.reliability.enabled", "decides whether the 02:00 cron job exists"),
    ("agents.file_organiser.enabled", "decides whether the scan job exists"),
    ("agents.file_organiser.scan_interval_hours", "the job's IntervalTrigger"),
    ("agents.file_organiser.weekly_review", "decides whether the weekly cron job exists"),
    ("agents.service_discovery.enabled", "decides whether the sweep job exists"),
    ("agents.service_discovery.scan_interval_hours", "the job's IntervalTrigger"),
    ("agents.estate_judge.enabled", "decides whether the poll job exists"),
    ("agents.estate_judge.poll_interval_hours", "the job's IntervalTrigger"),
    ("agents.log_aggregator.enabled", "decides whether the poll job exists"),
    ("agents.log_aggregator.poll_interval_seconds", "the job's IntervalTrigger"),
)

#: Paths the lifespan reads that a reload nonetheless **does** deliver.
#:
#: Both are read at startup and read again later, so listing them under
#: :data:`RESTART_ONLY` would be a false warning. They exist so the guard
#: test can distinguish "classified as live" from "forgotten".
LIVE_AT_STARTUP: tuple[tuple[str, str], ...] = (
    ("api.auth_token", "require_auth reads it on every request"),
    (
        "agents.project_organiser.projects_root",
        "this module rebuilds the registry from it on every reload",
    ),
)


class Prunable(Protocol):
    """An agent holding in-memory state keyed by a configured name."""

    name: str

    def forget_unknown(self) -> list[str]:
        """Drop state for names no longer declared; return what was dropped."""
        ...


@dataclass(frozen=True)
class ReloadReport:
    """What a reload did, and what it could not do.

    ``ok=False`` means **nothing** was installed — see rule 1. It is not a
    partial outcome, and the previously-served configuration is intact.
    """

    ok: bool
    reloaded_at: datetime
    error: str | None = None
    #: Fields that changed and cannot take effect until a restart.
    requires_restart: list[str] = field(default_factory=list)
    services_added: list[str] = field(default_factory=list)
    services_removed: list[str] = field(default_factory=list)
    services_changed: list[str] = field(default_factory=list)
    #: Agent name -> the names whose in-memory state was dropped.
    pruned: dict[str, list[str]] = field(default_factory=dict)
    services_total: int = 0

    @property
    def config_unchanged(self) -> bool:
        """No restart-only field moved — the reload delivered everything."""
        return not self.requires_restart

    def to_payload(self) -> dict[str, Any]:
        """The wire shape, as ``ReloadResponse`` declares it.

        Built here rather than in the endpoint so the mapping is testable
        without FastAPI, and so the SIGHUP path and the HTTP path cannot
        come to describe the same reload differently.
        """
        return {
            "ok": self.ok,
            "reloaded_at": self.reloaded_at.isoformat(),
            "error": self.error,
            "requires_restart": list(self.requires_restart),
            "services_total": self.services_total,
            "services_added": list(self.services_added),
            "services_removed": list(self.services_removed),
            "services_changed": list(self.services_changed),
            "pruned": {k: list(v) for k, v in self.pruned.items()},
        }


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """Every leaf of a dumped model, as ``a.b.c`` -> value.

    Lists are leaves rather than being indexed: ``cors_origins`` reordered
    is a change to ``cors_origins``, and naming ``cors_origins.2`` would
    report a position rather than a setting.
    """
    if not isinstance(value, dict):
        return {prefix: value}
    leaves: dict[str, Any] = {}
    for key, sub in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        leaves.update(_flatten(sub, path))
    return leaves


def changed_restart_only(old: AppConfig, new: AppConfig) -> list[str]:
    """Restart-only leaves whose value differs between two configs.

    Reported per **leaf** rather than per prefix — an operator told
    ``schedules`` changed still has to diff the file to find out what, and
    the whole point of the report is that they should not have to.
    """
    old_leaves = _flatten(old.model_dump(mode="json"))
    new_leaves = _flatten(new.model_dump(mode="json"))
    prefixes = tuple(path for path, _ in RESTART_ONLY)
    changed = []
    for path in sorted(set(old_leaves) | set(new_leaves)):
        if not any(path == p or path.startswith(f"{p}.") for p in prefixes):
            continue
        if old_leaves.get(path) != new_leaves.get(path):
            changed.append(path)
    return changed


def diff_services(
    old: ServicesFile, new: ServicesFile
) -> tuple[list[str], list[str], list[str]]:
    """Added, removed and altered service names between two files."""
    old_by_name = {s.name: s.model_dump(mode="json") for s in old.services}
    new_by_name = {s.name: s.model_dump(mode="json") for s in new.services}
    added = sorted(set(new_by_name) - set(old_by_name))
    removed = sorted(set(old_by_name) - set(new_by_name))
    changed = sorted(
        name
        for name in set(old_by_name) & set(new_by_name)
        if old_by_name[name] != new_by_name[name]
    )
    return added, removed, changed


#: Serialises reloads. Both triggers reach the same function — SIGHUP on the
#: API loop and an authenticated POST on a worker thread — and two swaps
#: interleaving would install one file from each parse.
_lock = threading.Lock()


def reload_configuration(
    *,
    config_path: Path | None = None,
    services_path: Path | None = None,
    prunable: Sequence[Prunable] = (),
) -> ReloadReport:
    """Re-read both configuration files and install them, or neither.

    Returns a :class:`ReloadReport` rather than raising: an invalid file is
    an expected outcome of an operator editing one, not a fault in this
    service, and the report is the product either way.

    The one window this does not close: an agent run that has already
    called ``get_config()`` and has yet to call ``get_services()`` sees one
    file from each generation. Both calls sit at the top of ``_execute``, so
    the window is microseconds wide and costs at most one run of a
    mismatched view — against a restart, which costs the run outright.
    """
    now = datetime.now(UTC)
    with _lock:
        old_config = get_config()
        old_services = get_services()

        try:
            new_config = parse_config(config_path)
        except Exception as exc:  # noqa: BLE001 — the message is the product
            return _refused(now, f"config.yaml: {exc}")

        try:
            registry = load_registry(
                new_config.agents.project_organiser.projects_root
            )
            new_services = load_services(
                services_path or default_services_path(), registry
            )
        except Exception as exc:  # noqa: BLE001
            return _refused(now, f"services.yaml: {exc}")

        requires_restart = changed_restart_only(old_config, new_config)
        added, removed, changed = diff_services(old_services, new_services)

        set_config(new_config)
        set_services(new_services)

        # Only after the swap: each agent computes its own known set from
        # the installed files, because only the agent knows which of them
        # its keys come from — the log aggregator's sources are the union
        # of both, and pruning it against services.yaml alone would throw
        # away cursors config.yaml still declares.
        pruned = {agent.name: agent.forget_unknown() for agent in prunable}

    report = ReloadReport(
        ok=True,
        reloaded_at=now,
        requires_restart=requires_restart,
        services_added=added,
        services_removed=removed,
        services_changed=changed,
        pruned={name: names for name, names in pruned.items() if names},
        services_total=len(new_services.services),
    )
    logger.info(
        "configuration_reloaded",
        extra={
            "services": report.services_total,
            "added": added,
            "removed": removed,
            "changed": changed,
            "requires_restart": requires_restart,
            "pruned": report.pruned,
        },
    )
    if requires_restart:
        # WARNING rather than INFO: this is the half the reload could not
        # do, and it is the only line that says so on the SIGHUP path,
        # where there is no response body to carry the report.
        logger.warning(
            "reload_requires_restart",
            extra={"fields": requires_restart, "count": len(requires_restart)},
        )
    return report


def _refused(now: datetime, error: str) -> ReloadReport:
    """Nothing installed. The running configuration is untouched."""
    logger.error("configuration_reload_refused", extra={"error": error})
    return ReloadReport(ok=False, reloaded_at=now, error=error)
