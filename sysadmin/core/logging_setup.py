"""Structured logging configuration.

Provides JSON formatting for systemd journal (production) and human-readable
text formatting for development. Called once during app lifespan startup.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from sysadmin.core.config import ServiceConfig


def configure_logging(service_config: ServiceConfig) -> None:
    """Set up root logger with the configured format and level."""
    level = getattr(logging, service_config.log_level.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    # Remove any existing handlers (e.g. from basicConfig or uvicorn)
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    formatter: logging.Formatter
    if service_config.log_format == "json":
        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
            static_fields={"service": service_config.name},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s — %(message)s"
        )

    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quieten noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # SNAG-AGENT-008, volume half. Clearing the *root* handlers above does
    # not reach uvicorn's own access logger: its default dictConfig
    # attaches a handler directly to ``uvicorn.access`` with
    # ``propagate = False``, so that handler survives untouched and every
    # request was written to the journal **twice** — once as plain text
    # here and once as JSON by :mod:`sysadmin.core.middleware`. Measured
    # 2026-08-17 over ten minutes: 662 plain lines against 640 JSON access
    # lines, and 662 - 640 is exactly the 22 ``/health`` polls the
    # middleware excludes and this one did not.
    #
    # That second clause is the part worth keeping in view.
    # ``_EXCLUDED_PATHS`` is SNAG-API-002's fix, and it has never worked:
    # the path it suppresses was being logged anyway by a logger nobody
    # had looked at. An exclusion that a second emitter ignores is not a
    # quieter log, it is a decision with nothing enforcing it.
    #
    # **The middleware is the copy that is kept**, not uvicorn's, because
    # only it carries ``method``/``path``/``status``/``duration_ms`` as
    # structured fields — uvicorn's line is prose that has to be parsed
    # back. Disabling rather than re-levelling: uvicorn logs access at
    # INFO and nothing else, so ``setLevel(WARNING)`` would be silence
    # spelled indirectly, and would quietly start emitting again if
    # uvicorn ever added a warning-level access line.
    #
    # Order is load-bearing and is why this is safe: uvicorn configures
    # its loggers in ``Config.load()``, before the app is imported, and
    # this function runs from the lifespan — so the handler always exists
    # by the time it is switched off. Nothing calls ``dictConfig`` again
    # afterwards, which is what would re-enable it.
    logging.getLogger("uvicorn.access").disabled = True
