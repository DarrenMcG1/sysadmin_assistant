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
   once is small and enumerable (:data:`RESTART_ONLY`). Refusing the whole
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

**The scheduler is re-timed too, and that is what closes SNAG-RELOAD-001**
(Session 50). Session 49 shipped this module without it, so a reload
installed an interval the running scheduler did not obey and named it —
once — in ``requires_restart``. A warning that fires once is
indistinguishable from one that got fixed, which is the shape Session 39
spent itself removing; and the divergence was a cost this module
*introduced*, since before it existed the config object and the scheduler
were built from one read and could never disagree.

``sync_jobs`` is injected rather than imported: the scheduler lives in
``main.py``, which imports this module, so reaching for it would be a
cycle — and the seam is what lets the whole path be tested against a fake
host. Two rules come with it:

* **The sync runs after the swap and inside the lock**, so it re-times
  against the configuration that was actually installed, and two reloads
  cannot interleave a swap with someone else's sync.
* **Without a syncer, every job leaf that moved is reported as
  restart-only.** :data:`~sysadmin.core.jobs.JOB_CONFIG_PATHS` is derived
  from the plan rather than restated, so that fallback cannot fall behind
  the jobs it describes. ``jobs_synced`` says which of the two happened —
  "re-timed nothing" and "never looked at the scheduler" are the same
  empty list otherwise, which is ``ports_checked``'s rule again.

:data:`RESTART_ONLY` is now **two** prefixes covering three genuinely
immutable things: the socket, the logging setup and the engine.
"""

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from estate.registry import load_registry

from sysadmin.core.config import (
    AppConfig,
    get_config,
    parse_config,
    set_config,
    unknown_config_keys,
)
from sysadmin.core.config_keys import KeyReport
from sysadmin.core.jobs import JOB_CONFIG_PATHS, JobSyncReport
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

#: The third classification, and the only one that is **derived**.
#:
#: Every leaf deciding a job's existence or its timing is delivered by
#: ``sync_jobs`` — fifteen of them, which is what used to make up the bulk
#: of :data:`RESTART_ONLY`. Listing them here by hand would be a fourth
#: copy of the schedule; ``sysadmin.core.jobs`` computes the set from the
#: plan itself, and ``tests/test_reload.py`` requires the plan's
#: declaration to match the config paths ``plan_jobs`` actually reads.
LIVE_VIA_JOB_SYNC: frozenset[str] = JOB_CONFIG_PATHS


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
    #: Whether the running scheduler was reconciled against the new config.
    #: ``False`` means no syncer was supplied, not that nothing changed —
    #: the same distinction ``ports_checked`` draws for a sweep whose ``ss``
    #: call failed. With it false, every job leaf that moved is in
    #: ``requires_restart`` instead.
    jobs_synced: bool = False
    #: Jobs newly scheduled — an agent enabled since the last read.
    jobs_added: list[str] = field(default_factory=list)
    #: Jobs unscheduled — an agent disabled since the last read.
    jobs_removed: list[str] = field(default_factory=list)
    #: Jobs whose trigger moved. Unchanged jobs are deliberately absent
    #: **and** untouched: ``reschedule_job`` recomputes the next fire from
    #: now, so re-applying an identical trigger would postpone the job.
    jobs_retimed: list[str] = field(default_factory=list)
    #: Keys config.yaml sets that no model declares (``SNAG-CFG-004``).
    #: The dual of ``requires_restart``: that list is what the operator
    #: asked for and did not get *yet*, this is what they asked for and
    #: will never get, because nothing reads the key they spelled. Both
    #: are answered with ``ok: true`` — the file is valid, and refusing a
    #: reload over an ignored key would install nothing while the daemon
    #: went on serving the same ignored key, which reports the problem by
    #: withholding the fix for everything else in the file.
    unknown_keys: list[str] = field(default_factory=list)
    #: Sections the key walk could not read. Empty is only good news when
    #: it sits beside an ``unknown_keys`` that was actually computed —
    #: ``ports_checked``'s rule.
    unwalkable_sections: list[str] = field(default_factory=list)

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
            "jobs_synced": self.jobs_synced,
            "jobs_added": list(self.jobs_added),
            "jobs_removed": list(self.jobs_removed),
            "jobs_retimed": list(self.jobs_retimed),
            "unknown_keys": list(self.unknown_keys),
            "unwalkable_sections": list(self.unwalkable_sections),
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


def changed_under(
    old: AppConfig, new: AppConfig, prefixes: Sequence[str]
) -> list[str]:
    """Leaves under ``prefixes`` whose value differs between two configs.

    Reported per **leaf** rather than per prefix — an operator told
    ``schedules`` changed still has to diff the file to find out what, and
    the whole point of the report is that they should not have to.
    """
    old_leaves = _flatten(old.model_dump(mode="json"))
    new_leaves = _flatten(new.model_dump(mode="json"))
    changed = []
    for path in sorted(set(old_leaves) | set(new_leaves)):
        if not any(path == p or path.startswith(f"{p}.") for p in prefixes):
            continue
        if old_leaves.get(path) != new_leaves.get(path):
            changed.append(path)
    return changed


def changed_restart_only(old: AppConfig, new: AppConfig) -> list[str]:
    """Leaves that moved and are read once, at startup."""
    return changed_under(old, new, [path for path, _ in RESTART_ONLY])


def changed_job_paths(old: AppConfig, new: AppConfig) -> list[str]:
    """Leaves that moved and decide a scheduled job's existence or timing.

    Only reported when no syncer was supplied — with one, these are exactly
    the fields the reload *does* deliver. Derived from the plan rather than
    restated, so a job added to ``sysadmin.core.jobs`` cannot quietly stop
    being reported here.
    """
    return changed_under(old, new, sorted(LIVE_VIA_JOB_SYNC))


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


#: Reconciles the running scheduler with a new config. Injected, never
#: imported — see the module docstring.
SyncJobs = Callable[[AppConfig], JobSyncReport]


def reload_configuration(
    *,
    config_path: Path | None = None,
    services_path: Path | None = None,
    prunable: Sequence[Prunable] = (),
    sync_jobs: SyncJobs | None = None,
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

        # The file is valid; now say which of its keys nothing reads
        # (``SNAG-CFG-004``). Deliberately after the parse and never
        # instead of it: this is the report an operator who has just
        # edited the file is looking at, and the surface they are holding
        # is the response to their own POST. Wrapped because a report must
        # never be able to break what it reports on — the rule
        # ``unit_failure._schema_diagnosis`` states for an alert
        # annotation, at the size of a reload.
        try:
            keys = unknown_config_keys(config_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning("config_key_check_failed", extra={"error": str(exc)})
            keys = KeyReport(walked=False)

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

        # Also after the swap, and still inside the lock: the scheduler is
        # re-timed against the configuration that was actually installed,
        # and two reloads cannot interleave one's swap with the other's
        # sync. `apply_jobs` catches per job, so this only fires if the
        # host itself is broken — in which case nothing was re-timed and
        # every job leaf that moved is owed a restart, which is precisely
        # the no-syncer answer below.
        jobs = JobSyncReport()
        jobs_synced = sync_jobs is not None
        if sync_jobs is not None:
            try:
                jobs = sync_jobs(new_config)
            except Exception as exc:  # noqa: BLE001
                logger.exception("job_sync_unavailable", extra={"error": str(exc)})
                jobs_synced = False

    if jobs_synced:
        # Only the jobs the host refused. In the ordinary case this is
        # empty, which is the whole point of the change: the divergence is
        # removed rather than described.
        requires_restart = sorted(
            set(requires_restart) | set(jobs.failed_config_paths)
        )
    else:
        requires_restart = sorted(
            set(requires_restart) | set(changed_job_paths(old_config, new_config))
        )

    report = ReloadReport(
        ok=True,
        reloaded_at=now,
        requires_restart=requires_restart,
        services_added=added,
        services_removed=removed,
        services_changed=changed,
        pruned={name: names for name, names in pruned.items() if names},
        services_total=len(new_services.services),
        jobs_synced=jobs_synced,
        jobs_added=jobs.added,
        jobs_removed=jobs.removed,
        jobs_retimed=jobs.retimed,
        unknown_keys=keys.unknown,
        unwalkable_sections=keys.unwalkable,
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
            "jobs_synced": jobs_synced,
            "jobs_added": jobs.added,
            "jobs_removed": jobs.removed,
            "jobs_retimed": jobs.retimed,
            "jobs_failed": jobs.failed,
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
