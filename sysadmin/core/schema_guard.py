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

``SNAG-DB-005``: the guard worked and the outage happened anyway.  On
2026-08-23 migration 013 was written, committed and never applied; the
daemon was restarted to serve a new route, this guard refused,
``StartLimitBurst=5`` made it terminal and ``sysadmin.service`` stayed
dead for **23 hours**.  That is ``SNAG-DB-001``'s cause with the guard
standing in the way — a loud outage instead of a silent blackout, which
is the better half of the trade and is still an outage.

Two things were missing and both are here now.

**The check is available before the restart.**  :func:`schema_status`
and :func:`main` expose the same comparison as a console script,
``sysadmin-check-schema``, called by ``scripts/claude-precommit.sh``
(blocking) and ``scripts/claude-postflight.sh`` (advisory).  The commit
is the last scripted moment before ``kill -TERM``; there is no deploy
script between them.

**The failure names its own remedy.**  ``sysadmin-failed.service`` fired
correctly and its toast said only ``result=exit-code, restarts=5``.
``_REMEDY`` — the one command that fixes it — existed here the whole
time and reached only the journal.  :mod:`sysadmin.core.unit_failure`
now calls :func:`schema_status` and puts the verdict in the alert row,
and ``scripts/notify-unit-failed.sh`` puts it in the notification.  That
is :mod:`sysadmin.monitor.collation`'s rule 4 — the remedy's trap is
carried in the alert — applied to the fault that needed it most.

Three further rules the second caller adds:

4. **The rules are shared; only the connection is copied.**  Both new
   callers run *outside* a running application — a git hook and a
   handler that fires when the daemon is dead — so neither can use
   :func:`get_engine`, and a sync reader is unavoidable.  What is *not*
   duplicated is the identity of the table, the none/one/many
   interpretation of its rows, and the wording of a mismatch: those live
   in :func:`_interpret_version_rows` and :func:`describe_mismatch`, and
   a test drives both readers against the live database and asserts they
   agree.  Two implementations of one rule drift in the direction nobody
   notices, which is rule 1 one layer down.
5. **Three outcomes, never two.**  ``match``, ``mismatch`` and
   ``unknown`` are distinct in the return type and in the exit status
   (0/1/2), because a check whose database was unreachable must not
   report what a check that looked and found nothing wrong reports —
   ``ports_checked``'s rule promoted into a signature.
6. **The sync path fails _soft_, deliberately the opposite of the
   lifespan's.**  :func:`verify_schema_revision` raises on every way of
   not-knowing because serving against the wrong schema is worse than
   not serving.  :func:`schema_status` returns ``unknown`` instead,
   because its callers are a commit hook and a failure handler: a commit
   blocked by an unrelated PostgreSQL outage trains the operator to
   ``--no-verify``, which disarms the check for the case it exists for,
   and a failure handler that raised would stop itself telling a human
   anything at all.
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from sysadmin.core.config import REPO_ROOT, get_config
from sysadmin.core.database import _configure_search_path, get_engine

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

#: What a comparison concluded.  Three values rather than a boolean, so a
#: caller cannot read "the database was unreachable" as "nothing is wrong"
#: — ``ports_checked``'s rule (``sysadmin/units/ports.py``) expressed in a
#: type instead of a companion flag.
SchemaVerdict = Literal["match", "mismatch", "unknown"]


@dataclass(frozen=True)
class SchemaStatus:
    """The comparison as data, for callers that must not raise.

    Attributes:
        verdict: see :data:`SchemaVerdict`.
        head: the revision this checkout's migrations end at, or ``None``
            when the scripts could not be read.
        current: the revision stamped on the live database, ``None`` when
            it has never been migrated *or* could not be reached — the
            two are told apart by ``verdict``, never by this field.
        problem: one sentence naming the fault and its remedy, ``None``
            only when ``verdict`` is ``"match"``.  Built by
            :func:`describe_mismatch` so this and the lifespan's
            exception cannot come to word the same fault differently.
    """

    verdict: SchemaVerdict
    head: str | None
    current: str | None
    problem: str | None

    @property
    def ok(self) -> bool:
        """True only for ``match``.  ``unknown`` is not ok, it is unknown."""
        return self.verdict == "match"


def _qualified(schema: str) -> str:
    """``schema.alembic_version``, built in one place.

    Rule 2 of the module docstring depends on this string never being
    resolved through ``search_path``: the ``projects`` database holds
    another application's ``alembic_version`` in ``public``, and a guard
    that reached *that* one would compare this code against a stranger's
    revision and pass.  Both readers call this rather than formatting it.
    """
    return f"{schema}.{VERSION_TABLE}"


def _interpret_version_rows(rows: list[str], schema: str) -> str | None:
    """Turn ``alembic_version``'s contents into a revision, or ``None``.

    The none/one/many rules, stated once.  ``None`` means the table is
    absent or empty — a database that has never been migrated, which is
    distinct from one stamped at the wrong revision and gets its own
    message at the call site.

    Raises:
        SchemaRevisionError: on more than one row.  Alembic stamps
            exactly one; two means the schema was migrated along two
            branches, which no upgrade can reconcile.
    """
    if not rows:
        return None
    if len(rows) > 1:
        raise SchemaRevisionError(
            f"{_qualified(schema)} holds {len(rows)} rows "
            f"({', '.join(sorted(rows))}); a stamped database has "
            "exactly one, so this schema was migrated along two branches"
        )
    return rows[0]


def describe_mismatch(head: str, current: str | None) -> str | None:
    """One sentence naming the fault, or ``None`` when the two agree.

    The single statement of what a mismatch *is* and what to say about
    it.  :func:`verify_schema_revision` raises this text and
    :func:`schema_status` returns it, so the operator reading a startup
    failure and the operator reading a blocked commit are told the same
    thing in the same words — the ``max_priority_for``/``PRIORITY_MAP``
    rule, one module over.
    """
    if current is None:
        return (
            f"the database carries no alembic revision (expected {head}); "
            f"it has never been migrated — {_REMEDY}"
        )
    if current != head:
        return (
            f"database schema is at revision {current} but this code "
            f"expects {head}. Serving against a schema this code was not "
            "written for is what caused SNAG-DB-001's 39-hour monitoring "
            f"blackout — {_REMEDY}"
        )
    return None



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

    Used by the lifespan, on the application's own engine — which is the
    correct connection to validate, since it is the one that will do the
    serving.  :func:`live_revision_sync` is the same read for callers
    that have no running application; the two share every rule and
    differ only in how they open a connection.
    """
    schema = get_config().database.schema_
    engine = get_engine()
    async with engine.connect() as conn:
        exists = await conn.execute(
            text("SELECT to_regclass(:qualified)"),
            {"qualified": _qualified(schema)},
        )
        if exists.scalar() is None:
            return None
        result = await conn.execute(
            text(f"SELECT version_num FROM {_qualified(schema)}")  # noqa: S608
        )
        rows = [row[0] for row in result.fetchall()]

    return _interpret_version_rows(rows, schema)


def live_revision_sync() -> str | None:
    """:func:`live_revision` for a process with no event loop.

    The sync engine that exists for Alembic, opened for one statement and
    closed — :mod:`sysadmin.core.unit_failure`'s pattern and for its
    reason.  Both of this function's callers run outside a running
    application (a git hook; a handler that fires when the daemon is
    dead), so :func:`get_engine` would raise before any query ran.

    ``pool_pre_ping`` is deliberately **not** set: the caller wants a
    failure to surface as a failure rather than be retried, and
    :func:`schema_status` is what turns it into ``unknown``.
    """
    config = get_config()
    schema = config.database.schema_
    engine = create_engine(config.database.sync_url)
    _configure_search_path(engine, schema)
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT to_regclass(:qualified)"),
                {"qualified": _qualified(schema)},
            )
            if exists.scalar() is None:
                return None
            result = conn.execute(
                text(f"SELECT version_num FROM {_qualified(schema)}")  # noqa: S608
            )
            rows = [row[0] for row in result.fetchall()]
    finally:
        engine.dispose()

    return _interpret_version_rows(rows, schema)


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

    problem = describe_mismatch(head, current)
    if problem is not None:
        raise SchemaRevisionError(problem)

    logger.info("schema_revision_verified", extra={"revision": current})
    assert current is not None  # describe_mismatch returns a problem for None
    return current


def schema_status() -> SchemaStatus:
    """The same comparison as :func:`verify_schema_revision`, but as data.

    For the two callers that must not raise: ``sysadmin-check-schema``
    (see :func:`main`) and :mod:`sysadmin.core.unit_failure`, which is a
    failure handler whose remaining job is to tell a human something.

    **This fails soft where the lifespan fails hard, and the asymmetry is
    the point.**  Refusing to boot on every way of not-knowing is right
    when the alternative is serving against the wrong schema.  It is
    wrong here: a commit blocked because PostgreSQL happens to be down
    teaches the operator to reach for ``--no-verify``, which disarms the
    check for the mismatch it exists to catch.  So an unreachable
    database, unreadable scripts and a branched history all come back as
    ``unknown`` with the reason in ``problem``, and the callers decide
    what an unknown is worth.
    """
    try:
        head = packaged_head()
    except SchemaRevisionError as exc:
        return SchemaStatus("unknown", None, None, str(exc))

    try:
        current = live_revision_sync()
    except SchemaRevisionError as exc:
        return SchemaStatus("unknown", head, None, str(exc))
    except Exception as exc:  # noqa: BLE001 — driver errors are not ours to enumerate
        return SchemaStatus(
            "unknown",
            head,
            None,
            f"could not read the live revision (expected {head}): {exc}",
        )

    problem = describe_mismatch(head, current)
    if problem is None:
        return SchemaStatus("match", head, current, None)
    return SchemaStatus("mismatch", head, current, problem)


#: Exit statuses for :func:`main`, one per verdict.  ``2`` is separate
#: from ``1`` so a caller can treat "I could not look" differently from
#: "I looked and it is wrong" — ``scripts/claude-precommit.sh`` blocks on
#: the second and warns on the first.
EXIT_STATUS: dict[str, int] = {"match": 0, "mismatch": 1, "unknown": 2}


def main(argv: list[str] | None = None) -> int:
    """``sysadmin-check-schema`` — is the live database at this checkout's head?

    Written for shell callers, so the output is two lines of plain text
    and the verdict is in the exit status:

    ==========  ======  =====================================================
    exit        verdict meaning
    ==========  ======  =====================================================
    ``0``       match   the database is at the packaged head
    ``1``       mismatch a migration is unapplied (or the database is ahead)
    ``2``       unknown  the comparison could not be made
    ==========  ======  =====================================================

    ``--quiet`` suppresses the ``match`` line only.  A fault always
    prints, because a check whose failure is silent is the shape this
    whole family exists to remove.
    """
    parser = argparse.ArgumentParser(
        description="Compare the live schema revision to this checkout's head."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="print nothing when the database is already at head",
    )
    args = parser.parse_args(argv)

    status = schema_status()

    if status.verdict == "match":
        if not args.quiet:
            print(f"schema at {status.current} (head)")
    else:
        print(f"{status.verdict}: {status.problem}", file=sys.stderr)

    return EXIT_STATUS[status.verdict]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
