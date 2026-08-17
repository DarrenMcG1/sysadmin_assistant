"""Tests for structured logging and request logging middleware."""

import json
import logging
from io import StringIO
from logging.config import dictConfig
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from uvicorn.config import LOGGING_CONFIG

from sysadmin.core.config import ServiceConfig
from sysadmin.core.logging_setup import configure_logging, syslog_priority
from sysadmin.monitor.journal import PRIORITY_MAP


def parse_journal_line(output: str) -> dict:
    """Parse one JSON log line, minus the journald level prefix.

    The ``<N>`` prefix is ``SNAG-AGENT-008``'s priority half and journald
    strips it before anything downstream sees it — so the tests below,
    which read the formatter's output directly rather than through the
    journal, are the only place it is visible. Strict rather than
    tolerant: a helper that shrugged at a missing prefix would let the
    fix be reverted with the suite still green.
    """
    assert output.startswith("<"), f"no level prefix on {output[:40]!r}"
    _, _, body = output.partition(">")
    return json.loads(body)


# --- JSON formatter tests ---


class TestConfigureLogging:
    """Test configure_logging with JSON and text formats."""

    def _capture_log(self, service_config: ServiceConfig, message: str) -> str:
        """Configure logging, emit a message, return the captured output."""
        configure_logging(service_config)
        root = logging.getLogger()
        # Replace handler stream with a StringIO to capture output
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("test.json").info(message)
        return buf.getvalue()

    def test_json_format_produces_valid_json(self):
        config = ServiceConfig(log_format="json")
        output = self._capture_log(config, "hello world")
        parsed = parse_journal_line(output)
        assert parsed["message"] == "hello world"

    def test_json_format_has_required_fields(self):
        config = ServiceConfig(log_format="json")
        output = self._capture_log(config, "check fields")
        parsed = parse_journal_line(output)
        assert "timestamp" in parsed
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.json"
        assert parsed["service"] == "sysadmin-service"

    def test_json_format_includes_extra_fields(self):
        config = ServiceConfig(log_format="json")
        configure_logging(config)
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("test.extra").info(
            "with extras", extra={"request_id": "abc123"}
        )
        parsed = parse_journal_line(buf.getvalue())
        assert parsed["request_id"] == "abc123"

    def test_text_format_produces_readable_output(self):
        config = ServiceConfig(log_format="text")
        output = self._capture_log(config, "human readable")
        assert "human readable" in output
        assert "INFO" in output
        # Text mode should NOT be valid JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)

    def test_log_level_respected(self):
        config = ServiceConfig(log_level="warning", log_format="json")
        configure_logging(config)
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("test.level").info("should be suppressed")
        assert buf.getvalue() == ""

    def test_clears_existing_handlers(self):
        root = logging.getLogger()
        root.addHandler(logging.StreamHandler())
        root.addHandler(logging.StreamHandler())
        assert len(root.handlers) >= 2
        configure_logging(ServiceConfig(log_format="text"))
        assert len(root.handlers) == 1


# --- Request logging middleware tests ---


class TestRequestLoggingMiddleware:
    """Test the access log middleware via the FastAPI test app."""

    @pytest.fixture
    async def app_with_middleware(self):
        """Minimal FastAPI app with the request logging middleware.

        Mounts the REAL health router so the excluded path in the
        middleware is tested against the actual mount point (SNAG-API-002).
        """
        from contextlib import asynccontextmanager

        from fastapi import FastAPI

        from sysadmin.core.health import router as health_router
        from sysadmin.core.middleware import RequestLoggingMiddleware

        @asynccontextmanager
        async def noop_lifespan(app):
            yield

        app = FastAPI(lifespan=noop_lifespan)
        app.add_middleware(RequestLoggingMiddleware)
        app.include_router(health_router)

        @app.get("/api/sysadmin/status")
        async def status():
            return {"services": []}

        @app.post("/api/sysadmin/scan-all")
        async def scan():
            return {"status": "triggered"}

        return app

    @pytest.fixture
    async def client(self, app_with_middleware):
        transport = ASGITransport(app=app_with_middleware)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c

    async def test_logs_request_with_correct_fields(self, client):
        with patch("sysadmin.core.middleware.logger") as mock_logger:
            await client.get("/api/sysadmin/status")
            mock_logger.info.assert_called_once()
            _, kwargs = mock_logger.info.call_args
            extra = kwargs["extra"]
            assert extra["method"] == "GET"
            assert extra["path"] == "/api/sysadmin/status"
            assert extra["status"] == 200
            assert "duration_ms" in extra

    async def test_excludes_health_endpoint(self, client):
        with patch("sysadmin.core.middleware.logger") as mock_logger:
            resp = await client.get("/health")
            # The real router must answer here — a 404 would mean we are
            # testing an exclusion for a path that doesn't exist
            assert resp.status_code == 200
            mock_logger.info.assert_not_called()

    async def test_logs_post_requests(self, client):
        with patch("sysadmin.core.middleware.logger") as mock_logger:
            await client.post("/api/sysadmin/scan-all")
            _, kwargs = mock_logger.info.call_args
            assert kwargs["extra"]["method"] == "POST"
            assert kwargs["extra"]["status"] == 200

    async def test_logs_404_status(self, client):
        with patch("sysadmin.core.middleware.logger") as mock_logger:
            await client.get("/nonexistent")
            _, kwargs = mock_logger.info.call_args
            assert kwargs["extra"]["status"] == 404


# --- uvicorn's own access logger (SNAG-AGENT-008, volume half) ---


class TestUvicornAccessLogIsSilenced:
    """``configure_logging`` must reach uvicorn's access logger too.

    Every request was written to the journal twice: once as plain text by
    ``uvicorn.access`` and once as JSON by
    :mod:`sysadmin.core.middleware`. Clearing the *root* handlers does not
    reach it, because uvicorn's default dictConfig attaches a handler to
    that logger directly and sets ``propagate = False``.

    Note what could **not** have caught this.
    ``TestRequestLoggingMiddleware.test_excludes_health_endpoint`` above
    asserts ``/health`` is not logged — by patching the *middleware's*
    logger, which is the one that was already excluding it. The path went
    on being logged 22 times per ten minutes by the emitter that test does
    not look at. So the fixture asserted the decision and the box kept
    disagreeing with it, which is why the test below reconstructs
    uvicorn's logger rather than trusting ours.
    """

    @pytest.fixture
    def uvicorn_access(self):
        """``uvicorn.access`` configured the way uvicorn configures it.

        Own handler, ``propagate = False``, level INFO — rebuilt here
        rather than imported so the test states the shape it defends
        against, and restored afterwards because this is a global logger
        and the suite shares it.
        """
        logger = logging.getLogger("uvicorn.access")
        saved = (logger.handlers[:], logger.propagate, logger.level, logger.disabled)

        buf = StringIO()
        handler = logging.StreamHandler(buf)
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.disabled = False

        yield logger, buf

        logger.handlers, logger.propagate, logger.level, logger.disabled = saved

    def test_access_line_is_not_emitted(self, uvicorn_access):
        """The guard — fails against the pre-fix ``configure_logging``."""
        logger, buf = uvicorn_access
        configure_logging(ServiceConfig(log_format="json"))
        logger.info('%s - "%s %s" %d', "127.0.0.1:53994", "GET", "/health", 200)
        assert buf.getvalue() == ""

    def test_the_record_is_not_rerouted_to_root_instead(self, uvicorn_access):
        """Silenced, not redirected.

        Removing the handler and letting the record propagate would keep
        the duplicate and merely re-dress it as JSON — the same line count
        in the journal, which is the number this change exists to move.
        """
        logger, _ = uvicorn_access
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        root_buf = StringIO()
        root.handlers[0].stream = root_buf
        logger.info("GET /api/sysadmin/status 200")
        assert root_buf.getvalue() == ""

    def test_only_the_access_logger_is_silenced(self, uvicorn_access):
        """``uvicorn.error`` carries startup failures and must survive.

        **This passed for the wrong reason until Session 61.** The fixture
        rebuilds ``uvicorn.access`` and not its parent, so ``uvicorn`` was
        left with no handler and ``propagate = True`` and the record fell
        through to root — while on the box it went to uvicorn's own
        plain-text handler and root stayed empty. The assertion was true
        here and false in production, which is exactly
        ``test_excludes_health_endpoint``'s defect one logger over, in the
        class written to fix it.

        It is kept as a cheap guard that ``disabled`` is not set on the
        wrong logger. :class:`TestUvicornErrorIsRerouted` is what actually
        holds the claim, under uvicorn's real ``LOGGING_CONFIG``.
        """
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("uvicorn.error").warning("address already in use")
        assert "address already in use" in buf.getvalue()

    def test_the_middleware_logger_is_untouched(self, uvicorn_access):
        """The copy that is kept is the one with the structured fields."""
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("sysadmin.access").info(
            "GET /api/sysadmin/status 200 4.1ms",
            extra={"path": "/api/sysadmin/status", "status": 200},
        )
        parsed = parse_journal_line(buf.getvalue())
        assert parsed["path"] == "/api/sysadmin/status"
        assert parsed["status"] == 200


# --- journald level prefix (SNAG-AGENT-008, priority half) ---


class TestJournalLevelPrefix:
    """Every JSON line must tell journald its own level.

    systemd stamps captured stdout/stderr ``PRIORITY=6`` whatever the
    payload says, so ``read_journal``'s ``severity_filter: warning``
    discarded every line this daemon has ever written and
    ``log_entries`` held 0 rows for ``sysadmin.service`` — across nine
    nights on which ``run_retention`` raised a traceback at ``ERROR``.
    """

    def _emit(self, config: ServiceConfig, level: int, message: str) -> str:
        configure_logging(config)
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        logging.getLogger("test.prefix").log(level, message)
        return buf.getvalue()

    @pytest.mark.parametrize(
        ("level", "expected"),
        [
            (logging.DEBUG, "<7>"),
            (logging.INFO, "<6>"),
            (logging.WARNING, "<4>"),
            (logging.ERROR, "<3>"),
            (logging.CRITICAL, "<2>"),
        ],
    )
    def test_each_level_carries_its_syslog_prefix(self, level, expected):
        """The guard — every line is ``<6>`` against the pre-fix formatter."""
        config = ServiceConfig(log_level="debug", log_format="json")
        assert self._emit(config, level, "levelled").startswith(expected)

    @pytest.mark.parametrize(
        ("level", "severity"),
        [
            (logging.DEBUG, "debug"),
            (logging.INFO, "info"),
            (logging.WARNING, "warning"),
            (logging.ERROR, "error"),
            (logging.CRITICAL, "critical"),
        ],
    )
    def test_the_prefix_round_trips_through_the_readers_priority_map(
        self, level, severity
    ):
        """The producer and the consumer are pinned to each other.

        ``syslog_priority`` here and ``PRIORITY_MAP`` in
        :mod:`sysadmin.monitor.journal` are two statements of one fact, and
        two statements that can disagree is this repository's recurring
        defect — ``SNAG-DB-003``'s hand-copied exclusion list, and
        ``chk_alert_agent`` against ``self_monitor.AGENT_NAMES``. Asserting
        each side alone would let them drift in step with nothing failing.
        """
        assert PRIORITY_MAP[str(syslog_priority(level))] == severity

    def test_the_payload_after_the_prefix_is_still_valid_json(self):
        """journald strips the prefix, so nothing downstream may see it.

        Verified on the box against a transient unit as well as here:
        ``<4>{…}`` arrives with ``PRIORITY=4`` and a ``MESSAGE`` identical
        to the unprefixed line. ``log_signature``, ``alert_title`` and the
        stored ``raw_line`` therefore need no change.
        """
        config = ServiceConfig(log_format="json")
        output = self._emit(config, logging.WARNING, "still parseable")
        assert output.startswith("<4>")
        parsed = json.loads(output[3:])
        assert parsed["message"] == "still parseable"
        assert parsed["level"] == "WARNING"

    def test_a_traceback_stays_on_one_line(self):
        """The precondition the JSON gate rests on.

        A level prefix marks **one** line. The JSON formatter escapes
        newlines, so an exception's whole traceback travels on the line
        whose level describes it. Under the text formatter it would not,
        which is why the prefix is bound to the format rather than to the
        destination.
        """
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf
        try:
            raise ZeroDivisionError("division by zero")
        except ZeroDivisionError:
            logging.getLogger("test.trace").exception("purge_traceback")

        output = buf.getvalue()
        assert output.count("\n") == 1
        parsed = json.loads(output[3:])
        assert output.startswith("<3>")
        assert "ZeroDivisionError" in parsed["exc_info"]

    def test_text_format_is_not_prefixed(self):
        """Text mode is a terminal, and its tracebacks span many lines.

        Prefixing there would stamp the first line ``ERROR`` and leave the
        body at ``info`` — one fault split across two priorities, which is
        worse than the uniform ``6`` it replaced because it looks fixed.
        """
        config = ServiceConfig(log_format="text")
        output = self._emit(config, logging.ERROR, "human readable")
        assert not output.startswith("<")
        assert "human readable" in output

    def test_a_level_between_two_rungs_degrades_to_the_quieter_one(self):
        """A custom level must never invent an alarm nobody chose."""
        assert syslog_priority(25) == 6           # between INFO and WARNING
        assert syslog_priority(logging.NOTSET) == 7
        assert syslog_priority(logging.CRITICAL + 10) == 2


# --- uvicorn's own error logger (SNAG-AGENT-008, priority half) ---


class TestUvicornErrorIsRerouted:
    """uvicorn's own records must reach this module's formatter.

    ``uvicorn.error`` has no handler and propagates — but only as far as
    ``uvicorn``, which keeps a plain-text stderr handler with
    ``propagate = False``, exactly the shape ``uvicorn.access`` had. So
    ``Exception in ASGI application`` and the traceback of every unhandled
    500 went out as plain text at ``PRIORITY=6``, and no prefix put on
    *this application's* logger could have reached them.

    **The fixture drives uvicorn's real ``LOGGING_CONFIG``**, and that is
    the whole lesson of this class.
    ``TestUvicornAccessLogIsSilenced.test_only_the_access_logger_is_silenced``
    asserts ``uvicorn.error`` reaches the root handler and passes —
    because its fixture rebuilds ``uvicorn.access`` and not ``uvicorn``,
    leaving the parent with no handler and ``propagate = True``. Measured
    against the real config on 2026-08-17, the record went to uvicorn's
    own handler as ``ERROR:    address already in use`` and root stayed
    empty. A reconstruction that omits the thing under test is
    ``test_excludes_health_endpoint``'s defect, one logger over.
    """

    @pytest.fixture
    def uvicorn_real(self):
        """uvicorn's loggers as ``Config.load()`` leaves them."""
        names = ("uvicorn", "uvicorn.error", "uvicorn.access")
        saved = {
            n: (
                logging.getLogger(n).handlers[:],
                logging.getLogger(n).propagate,
                logging.getLogger(n).level,
                logging.getLogger(n).disabled,
            )
            for n in names
        }

        dictConfig(LOGGING_CONFIG)
        own = StringIO()
        logging.getLogger("uvicorn").handlers[0].stream = own

        yield own

        for n in names:
            lg = logging.getLogger(n)
            lg.handlers, lg.propagate, lg.level, lg.disabled = saved[n]

    def test_uvicorn_error_reaches_the_root_handler_as_prefixed_json(
        self, uvicorn_real
    ):
        """The guard — root stays empty against the pre-fix code."""
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf

        logging.getLogger("uvicorn.error").error("Exception in ASGI application")

        output = buf.getvalue()
        assert output.startswith("<3>")
        assert json.loads(output[3:])["message"] == "Exception in ASGI application"

    def test_uvicorns_own_handler_no_longer_writes(self, uvicorn_real):
        """Rerouted, not duplicated.

        Flipping ``propagate`` without clearing the handler would keep the
        plain line and add a JSON one — the duplicate Session 60 removed,
        arriving through the fix for its sibling.
        """
        configure_logging(ServiceConfig(log_format="json"))
        logging.getLogger("uvicorn.error").error("address already in use")
        assert uvicorn_real.getvalue() == ""

    def test_the_access_logger_is_still_silent(self, uvicorn_real):
        """Session 60's guard, re-asserted under the real wiring.

        ``disabled = True`` is checked in ``isEnabledFor``, so no record is
        created and re-enabling the parent's propagation cannot revive it.
        """
        configure_logging(ServiceConfig(log_format="json"))
        root = logging.getLogger()
        buf = StringIO()
        root.handlers[0].stream = buf

        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s" %d', "127.0.0.1:53994", "GET", "/health", 200
        )

        assert buf.getvalue() == ""
        assert uvicorn_real.getvalue() == ""
