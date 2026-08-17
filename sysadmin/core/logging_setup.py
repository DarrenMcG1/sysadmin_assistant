"""Structured logging configuration.

Provides JSON formatting for systemd journal (production) and human-readable
text formatting for development. Called once during app lifespan startup.
"""

import logging
import sys

from pythonjsonlogger.json import JsonFormatter

from sysadmin.core.config import ServiceConfig

#: Python level -> syslog priority: the **producer** half of the pair whose
#: consumer is :data:`sysadmin.monitor.journal.PRIORITY_MAP`.  Descending,
#: and read as "the highest threshold at or below this level", so a custom
#: level between two rungs degrades to the quieter one rather than raising
#: an alarm nobody chose.  ``5`` (notice) is deliberately absent: Python has
#: no rung for it and the reader maps it to ``info`` regardless.
_SYSLOG_PRIORITY: tuple[tuple[int, int], ...] = (
    (logging.CRITICAL, 2),  # crit
    (logging.ERROR, 3),     # err
    (logging.WARNING, 4),   # warning
    (logging.INFO, 6),      # info
    (logging.DEBUG, 7),     # debug
)


def syslog_priority(levelno: int) -> int:
    """Map a Python level number to the syslog priority journald records.

    Kept a module-level function rather than folded into the formatter so
    ``tests/test_logging.py`` can drive it against
    :data:`sysadmin.monitor.journal.PRIORITY_MAP` directly — the two are a
    producer/consumer pair and the only thing worth asserting is that a
    level survives the round trip.  Two maps that can disagree about one
    fact is this repository's recurring defect (``SNAG-DB-003``, and
    ``chk_alert_agent`` against ``self_monitor.AGENT_NAMES``).
    """
    for level, priority in _SYSLOG_PRIORITY:
        if levelno >= level:
            return priority
    return 7


class JournalLevelPrefixFormatter(JsonFormatter):
    """A JSON formatter that prefixes each line with ``<N>`` for journald.

    ``SNAG-AGENT-008``, priority half.  systemd stamps **captured stdout
    and stderr** ``PRIORITY=6`` whatever the payload says, so every line
    this daemon wrote arrived as ``info``: ``read_journal`` filters on
    journald's ``PRIORITY``, ``services.yaml`` declares this source at
    ``severity_filter: warning``, and ``log_entries`` therefore held **0
    rows** for ``sysadmin.service`` across nine consecutive nights on
    which ``run_retention`` raised a traceback at Python ``ERROR``
    (``SNAG-DB-004``).  The monitor was blind to itself in exactly the
    place its own stack traces come out.

    **This needs no unit-file edit and therefore no ``sudo``**, which is
    the opposite of what the snag assumed and is why this remedy was
    chosen over parsing the ``"level"`` key back out in ``read_journal``.
    ``SyslogLevelPrefix=`` **defaults to true** in systemd; measured on
    2026-08-17, ``systemctl show sysadmin.service -p SyslogLevelPrefix``
    already reads ``yes``.  Verified end to end against a transient unit
    rather than read off the documentation: ``<4>{…}`` arrives as
    ``PRIORITY=4`` and journald **strips the prefix**, so ``MESSAGE`` is
    byte-identical to the unprefixed line and nothing downstream —
    ``log_signature``, ``alert_title``, the stored ``raw_line`` — sees it.

    Why the producer and not the reader.  Parsing ``"level"`` inside
    ``read_journal`` would fix this repository's view and leave the
    artefact lying: ``journalctl -u sysadmin -p err`` would still print
    nothing, and so would any ``OnFailure=`` hook or anyone reading the
    journal by hand.  It would also put a special case for **one** source
    into a reader that serves fourteen, keyed on this application's own
    log format — ``sysadmin.service`` is the only JSON-writing journal
    source on this box, measured, so the branch could never pay for
    itself.

    **Why this is bound to the JSON format and not to the destination.**
    The gate is not a proxy for "running under systemd"; it is the
    precondition for the prefix being *sound*.  A level prefix marks one
    line, and only the JSON formatter guarantees one line per record —
    ``json.dumps`` escapes newlines, so a traceback stays on the line its
    level describes.  Under the text formatter a traceback spans many
    lines: the first would be stamped ``ERROR`` and its body left at
    ``info``, splitting one fault across two priorities, which is worse
    than the uniform ``6`` it replaced because it *looks* fixed.
    """

    def format(self, record: logging.LogRecord) -> str:
        return f"<{syslog_priority(record.levelno)}>{super().format(record)}"


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
        formatter = JournalLevelPrefixFormatter(
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

    # SNAG-AGENT-008, priority half. The *sibling* of the line above, and
    # the one that carries the errors. ``uvicorn.error`` has no handler of
    # its own and propagates — but only as far as ``uvicorn``, which
    # keeps a plain-text stderr handler and ``propagate = False``, exactly
    # the shape ``uvicorn.access`` had. So uvicorn's own records —
    # including ``Exception in ASGI application`` with the traceback of
    # any unhandled 500 — never reached this module's formatter, and no
    # prefix put on *our* logger could have reached them.
    #
    # **Rerouted, not silenced**, which is deliberately the opposite verb
    # from the access logger three lines up. That line is a duplicate of a
    # structured line the middleware already writes, so the second copy is
    # waste; uvicorn's error line has no second copy anywhere, so
    # silencing it would delete the only record an ASGI-level crash
    # leaves. Same file, same fault, opposite remedies.
    #
    # The handler is cleared as well as the flag flipped: leaving it would
    # keep the plain line *and* add a JSON one, which is the duplicate
    # Session 60 removed arriving through the fix for its sibling.
    # ``uvicorn.access`` is unaffected — ``disabled = True`` is checked in
    # ``isEnabledFor``, so no record is created to propagate.
    #
    # Note what was asserting the opposite. ``test_only_the_access_logger_
    # _is_silenced`` (Session 60) claims ``uvicorn.error`` reaches the root
    # handler, and it passes — because its fixture rebuilds
    # ``uvicorn.access`` and not ``uvicorn``, leaving the parent with no
    # handler and ``propagate = True``. Driven against uvicorn's real
    # ``LOGGING_CONFIG`` on 2026-08-17 the record went to uvicorn's own
    # stderr handler as ``ERROR:    address already in use`` and the root
    # buffer stayed empty. A green test asserting a decision the box does
    # not implement is the defect Session 60 found, reproduced by the
    # session that found it.
    uvicorn_root = logging.getLogger("uvicorn")
    uvicorn_root.handlers.clear()
    uvicorn_root.propagate = True
