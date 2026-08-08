"""Run the project organiser once, without the monitoring daemon.

The organiser and the monitor keep different company. The monitor polls
every five minutes and must never stop; the organiser walks forty
repositories once a day and can fail, be interrupted, or be skipped
entirely without anything downstream noticing until tomorrow. Running the
second inside the first means a scan that hangs on a slow git operation
holds a thread in the process that is meant to be watching everything
else.

So: a oneshot unit and a timer. This entry point is what they invoke.

The monitoring service does not depend on this in either direction. Stop
the timer and health checks carry on; stop the daemon and the scan still
runs, writes its snapshots and rewrites estate.json.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sysadmin.core.config import get_config, load_config
from sysadmin.core.database import (
    create_engine_and_session,
    dispose_engine,
    verify_connection,
)
from sysadmin.core.logging_setup import configure_logging
from sysadmin.projects.agent import ProjectOrganiserAgent

logger = logging.getLogger(__name__)


async def run_scan(config_path: Path | None = None) -> int:
    """One organiser run. Returns a process exit code.

    Reports the run's own outcome rather than trusting it: the agent
    records to ``agent_runs`` whatever happens, and a timer whose unit
    always exits 0 tells ``systemctl status`` nothing worth reading.
    """
    config = load_config(config_path) if config_path else get_config()
    configure_logging(config.service)

    await create_engine_and_session()
    try:
        if not await verify_connection():
            logger.error("organiser_scan_aborted", extra={"reason": "no database"})
            return 1

        result = await ProjectOrganiserAgent().run(run_type="scheduled")
    finally:
        await dispose_engine()

    if result is None:
        logger.error("organiser_scan_failed")
        return 1

    logger.info(
        "organiser_scan_complete",
        extra={
            "projects": result.findings_count,
            "alerts": result.alerts_raised,
            **(result.details or {}),
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=None,
        help="config.yaml to use (default: the one beside this repository)",
    )
    args = parser.parse_args(argv)
    return asyncio.run(run_scan(args.config))


if __name__ == "__main__":
    sys.exit(main())
