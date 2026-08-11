"""Recording a systemd unit failure as an alert row, from outside the app.

Session 39. `sysadmin-failed.service` notifies the desktop and writes to
journald, and neither survives as *state*: a failure that happened while
nobody was logged in is invisible to `GET /api/sysadmin/alerts` afterwards.
The toast expired unseen and the journal is not a surface anyone opens
unprompted — which is the same "absence of signal read as absence of
problem" this session exists to remove, one layer out.

**This module runs when the application is dead.** That is not a caveat,
it is the entire operating condition, and it rules out almost everything
the rest of the codebase does:

- no async engine — there is no event loop and no lifespan
- no :meth:`BaseAgent.raise_alert` — that needs a session from a running
  scheduler, and an agent instance that is not running
- no event bus — nothing is subscribed, because nothing is up

What is left is the **sync** engine that already exists for Alembic, and
`_configure_search_path` alongside it. One connection, one insert, no pool.

**`agent` is `'sysadmin'`, and the precise truth lives in `details`.**
The `chk_alert_agent` CHECK constraint admits only the five known agent
names, so an outside writer must either claim one or gain a value by
migration. Claiming `sysadmin` reads oddly — the sysadmin agent did not
raise this; it was dead, which is the news — so `details['source']`
records `systemd_onfailure` and `details['raised_by']` records the handler.
Read that way `agent` is the *ownership* field the constraint makes it
(whose alerts are these, whose resolve pattern matches them) and nothing
is claimed that is not true. A migration adding a sixth name was the
alternative and is recorded in ADR-0002 as deliberately not taken: a value
that names a script rather than an agent would also make
`self_monitor.AGENT_NAMES` wrong, and that list is pinned to the
constraint by `tests/test_units_api.py`.

**The row is resolved by the daemon coming back**, in
:func:`resolve_unit_failures`, called from the lifespan. Without that half
this row is unresolvable by construction — nothing else knows it exists —
and an alert type that can only accumulate is how this repository reached
1,664 orphaned rows. The pairing is the feature: the alerts list then
answers "is it broken *now*", and the resolved row stays as history.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from sysadmin.core.config import get_config
from sysadmin.core.database import _configure_search_path
from sysadmin.core.models.alert import Alert

logger = logging.getLogger(__name__)

#: The agent this row is filed under. See the module docstring: the
#: constraint makes this an ownership field, and `details` carries the
#: provenance that `agent` cannot express.
FILED_UNDER = "sysadmin"

#: Marks a row as written by the failure handler rather than by an agent.
#: Both halves of the lifecycle match on it, so it must not be edited on
#: one side only.
SOURCE = "systemd_onfailure"

#: The unit this application runs as. Named in **three** places — here, the
#: `ExecStart=` in `systemd/sysadmin-failed.service`, and the default in
#: `scripts/notify-unit-failed.sh` — because the title is derived from it
#: and raise and resolve must agree on the string. A mismatch does not
#: error: the handler writes `sysadmin.service failed` and startup resolves
#: `sysadmin failed`, so the row is simply never closed.
#: `tests/test_unit_failure.py` pins it to the unit file.
OWN_UNIT = "sysadmin.service"


def unit_failure_title(unit: str) -> str:
    """The alert title for ``unit`` having failed.

    The one place it is built, for the reason ``_alert_title`` records in
    :mod:`sysadmin.projects.agent`: raise and resolve derive from the same
    function, because a hand-written resolve pattern that matches nothing
    fails silently while the table grows.
    """
    return f"{unit} failed"


def _sync_session() -> Session:
    """A single short-lived sync session, search_path configured.

    ``NullPool`` is not needed and a pool is not wanted: this process
    inserts one row and exits. ``pool_pre_ping`` earns its place because
    the database may itself be the reason the service died.
    """
    config = get_config()
    engine = create_engine(config.database.sync_url, pool_pre_ping=True)
    _configure_search_path(engine, config.database.schema_)
    return Session(engine)


def record_unit_failure(
    unit: str,
    *,
    result: str | None = None,
    exit_status: str | None = None,
    restarts: str | None = None,
) -> bool:
    """Insert a critical alert saying ``unit`` has entered ``failed``.

    Returns ``True`` when a row was written. Returns ``False`` — rather
    than raising — when one is already open for this unit, or when the
    database cannot be reached: the caller is a failure handler whose
    remaining job is to notify a human, and an exception here would stop
    it doing that. The reason is logged either way, and the handler writes
    to journald *before* calling this for exactly that reason.

    Deduplicated on an open row for the same title, matching the rule the
    rest of this codebase uses. Note that dedup is only safe because
    :func:`resolve_unit_failures` closes the row when the daemon returns —
    otherwise the first failure would silence every later one.
    """
    try:
        with _sync_session() as session:
            existing = session.execute(
                select(Alert.id).where(
                    Alert.agent == FILED_UNDER,
                    Alert.title == unit_failure_title(unit),
                    Alert.resolved.is_(False),
                )
            ).first()
            if existing is not None:
                logger.info("unit failure already open for %s — not duplicating", unit)
                return False

            session.add(Alert(
                agent=FILED_UNDER,
                severity="critical",
                title=unit_failure_title(unit),
                message=(
                    f"systemd gave up restarting {unit} "
                    f"(result={result or 'unknown'}, exit={exit_status or '?'}, "
                    f"restarts={restarts or '?'}). Monitoring is down until it "
                    "is started."
                ),
                details=_details(unit, result, exit_status, restarts),
            ))
            session.commit()
    except Exception as exc:  # noqa: BLE001 — a handler must not raise
        logger.error("could not record unit failure for %s: %s", unit, exc)
        return False

    logger.warning("recorded unit failure alert for %s", unit)
    return True


def _details(
    unit: str, result: str | None, exit_status: str | None, restarts: str | None
) -> dict[str, Any]:
    """The provenance `agent` cannot carry, plus the systemd verdict.

    ``result`` distinguishes an exit code from a timeout from an OOM kill,
    and ``restarts`` says whether the unit thrashed or died once — the two
    questions asked first when reading this row later.
    """
    return {
        "kind": "unit_failure",
        "unit": unit,
        # Why `agent` says "sysadmin" when the sysadmin agent was dead.
        "source": SOURCE,
        "raised_by": "scripts/notify-unit-failed.sh",
        "systemd_result": result,
        "exit_status": exit_status,
        "restarts": restarts,
    }


async def resolve_unit_failures(session, unit: str) -> int:
    """Close any open unit-failure alert for ``unit``. Called at startup.

    The other half of :func:`record_unit_failure`, and not optional: the
    handler runs while this application is dead, so no agent will ever
    observe the recovery. The service starting *is* the recovery, and this
    is the only moment that fact is available.

    Deliberately narrowed to ``source == SOURCE`` rather than resolving
    every alert with a matching title. A future agent that legitimately
    reports on unit failures must not have its rows cleared by a restart
    of this one.
    """
    result = await session.execute(
        update(Alert)
        .where(
            Alert.agent == FILED_UNDER,
            Alert.title == unit_failure_title(unit),
            Alert.resolved.is_(False),
            Alert.details["source"].astext == SOURCE,
        )
        .values(resolved=True, resolved_at=datetime.now(UTC))
    )
    resolved: int = result.rowcount
    if resolved:
        logger.info("resolved %d open unit-failure alert(s) for %s", resolved, unit)
    return resolved


def main() -> int:
    """``sysadmin-record-failure`` — entry point for the OnFailure handler.

    Exits 0 even when nothing was written. The handler's exit status is
    reserved for whether it could *tell a human*; a database that is down
    is worth a log line, not a failed unit that then needs its own
    explanation.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("unit", help="the unit that failed, e.g. sysadmin.service")
    parser.add_argument("--result", default=None, help="systemd Result= property")
    parser.add_argument("--exit-status", default=None, help="ExecMainStatus")
    parser.add_argument("--restarts", default=None, help="NRestarts")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    record_unit_failure(
        args.unit,
        result=args.result,
        exit_status=args.exit_status,
        restarts=args.restarts,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
