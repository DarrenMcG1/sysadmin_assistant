"""Refusing to serve against a schema this code was not written for.

``SNAG-DB-001``: on 2026-08-08 migration 009 — which adds ``'skipped'``
to ``chk_health_status`` — was written, committed and never applied.
Two minutes later the daemon restarted, picked up a ``services.yaml``
declaring ``venture-chat-large`` as ``monitor: false``, and wrote the
first ``skipped`` row.  The database rejected it, the rejection aborted
the whole run's transaction, and **zero rows reached ``service_health``
for the next 39 hours**.  The tray, ``/api/sysadmin/status`` and
reliability scoring all went on serving from a table that had stopped
receiving data.

**Nothing applies migrations here** — no script, no ``ExecStartPre``, no
CI step; it is a ``uv run alembic upgrade head`` a human has to remember.
Nothing checked either, and three plausible checks all miss it:

- ``verify_connection`` proves the database *answers*, not that it is
  the schema this code was written for.
- ``tests/test_schema_drift.py`` connects to the live database and would
  not have caught it: it explicitly skips ``alembic_version``, and
  ``compare_metadata`` does not diff CHECK constraints.  Verified
  2026-08-10 by restoring the pre-009 constraint inside a rolled-back
  transaction and getting an **empty diff**, with the model declaring
  ``'skipped'`` and the database rejecting it.
- The daemon logged ``agent_run_failed`` every five minutes for ~18
  hours of uptime.  Nothing reads that, and the thing that broke *was*
  the alerting path, so it could not report its own failure.

So the check is here, at startup, and it **refuses to start**.  That is
not a preference for loudness; it is the only option whose failure mode
is visible.  Coming up degraded and raising a critical instead would
write that alert through the schema which is wrong — a monitor
reporting its own brokenness down the broken path is the loop the snag
already demonstrated.  Refusing puts ``sysadmin.service`` into
``failed``, where ``StartLimitBurst=5`` makes the restart loop terminal
and ``sysadmin-failed.service`` announces it persistently, to journald
first (:mod:`sysadmin.core.unit_failure`).  The Session 39 machinery was
built for exactly this shape of fault and this is its second caller.

Three rules worth keeping:

1. **The head comes from alembic's own :class:`ScriptDirectory`**, never
   from parsing ``alembic/versions/*.py``.  A regex over ``revision``
   and ``down_revision`` is a second implementation of the revision
   graph, and the thing this guard is measuring against is precisely
   what ``alembic upgrade head`` would do.  Two implementations of one
   rule drift in the direction nobody notices — the same argument
   ``SERVICE_ALERT_KINDS`` and ``_alert_title`` already encode for
   raise-versus-resolve.
2. **``alembic_version`` is read schema-qualified, not through
   ``search_path``.**  ``version_table_schema="sysadmin"`` exists
   because the ``projects`` database holds another application's
   ``alembic_version`` in ``public``; a guard that resolved *that* one
   would compare this code against a stranger's revision and pass.
3. **Every way of not-knowing fails closed, with its own message.**  An
   unreadable script directory, a branched history with two heads, and a
   database that has never been migrated are three different faults, and
   an operator woken by this needs to be told which.  Failing open on
   "the guard could not run" rebuilds the silent failure the guard
   exists to remove.
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.database import get_engine

logger = logging.getLogger(__name__)

#: Where the migration scripts live.  Alongside ``config.yaml`` at the
#: repository root rather than inside the package, because that is where
#: ``alembic.ini``'s ``script_location`` points and the unit's
#: ``WorkingDirectory`` is the repository.
ALEMBIC_DIR = REPO_ROOT / "alembic"

#: Alembic's bookkeeping table.  Named here rather than inlined because
#: the drift guard skips it by the same name and the two should be
#: greppable together.
VERSION_TABLE = "alembic_version"

#: What to do about it, appended to every failure message.  The guard is
#: read by whoever is looking at ``systemctl status`` at 3am, and the
#: remedy is one command that nothing in this repository runs for them.
_REMEDY = "run `uv run alembic upgrade head` and start the service again"


class SchemaRevisionError(RuntimeError):
    """The live schema is not the one this code was written for.

    A plain ``RuntimeError`` subclass so an uncaught escape from the
    lifespan still terminates startup; the type exists so tests can
    assert on the fault rather than on the message text.
    """


def packaged_head(script_location: Path | None = None) -> str:
    """The revision this checkout's migrations end at.

    Raises:
        SchemaRevisionError: if the scripts cannot be read, or if the
            history has **branched**.  Two heads is not a lesser problem
            deserving a warning: ``alembic upgrade head`` refuses to run
            against it, so a service that started anyway would be
            permanently unable to migrate and would say nothing.
    """
    location = script_location or ALEMBIC_DIR
    config = AlembicConfig()
    config.set_main_option("script_location", str(location))

    try:
        heads = ScriptDirectory.from_config(config).get_heads()
    except Exception as exc:  # noqa: BLE001 — alembic raises several types
        raise SchemaRevisionError(
            f"cannot read migration scripts at {location}: {exc}. "
            "The service is started from its repository "
            "(WorkingDirectory), so this means the deployment is "
            "incomplete rather than merely unmigrated"
        ) from exc

    if len(heads) != 1:
        raise SchemaRevisionError(
            f"migration history at {location} has {len(heads)} heads "
            f"({', '.join(sorted(heads)) or 'none'}); expected exactly "
            "one. `alembic upgrade head` cannot run against a branched "
            "history, so the schema could never be brought up to date"
        )
    return heads[0]


async def live_revision() -> str | None:
    """The revision stamped on the live database, or ``None``.

    ``None`` means the table is absent or empty — a database that has
    never been migrated, which is distinct from one stamped at the wrong
    revision and gets its own message at the call site.
    """
    schema = get_config().database.schema_
    engine = get_engine()
    async with engine.connect() as conn:
        exists = await conn.execute(
            text("SELECT to_regclass(:qualified)"),
            {"qualified": f"{schema}.{VERSION_TABLE}"},
        )
        if exists.scalar() is None:
            return None
        result = await conn.execute(
            text(f"SELECT version_num FROM {schema}.{VERSION_TABLE}")  # noqa: S608
        )
        rows = [row[0] for row in result.fetchall()]

    if not rows:
        return None
    if len(rows) > 1:
        raise SchemaRevisionError(
            f"{schema}.{VERSION_TABLE} holds {len(rows)} rows "
            f"({', '.join(sorted(rows))}); a stamped database has "
            "exactly one, so this schema was migrated along two branches"
        )
    return rows[0]


async def verify_schema_revision() -> str:
    """Assert the live schema matches this checkout, or refuse to start.

    Returns:
        The revision both sides agree on, for the startup log line —
        which is the only routine evidence that the check ran at all.

    Raises:
        SchemaRevisionError: on any mismatch, and on any inability to
            establish one.
    """
    head = packaged_head()
    current = await live_revision()

    if current is None:
        raise SchemaRevisionError(
            f"the database carries no alembic revision (expected {head}); "
            f"it has never been migrated — {_REMEDY}"
        )

    if current != head:
        raise SchemaRevisionError(
            f"database schema is at revision {current} but this code "
            f"expects {head}. Serving against a schema this code was not "
            "written for is what caused SNAG-DB-001's 39-hour monitoring "
            f"blackout — {_REMEDY}"
        )

    logger.info("schema_revision_verified", extra={"revision": current})
    return current
