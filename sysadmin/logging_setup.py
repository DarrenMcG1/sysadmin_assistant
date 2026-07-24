"""Structured logging configuration.

Provides JSON formatting for systemd journal (production) and human-readable
text formatting for development. Called once during app lifespan startup.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from sysadmin.config import ServiceConfig


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
