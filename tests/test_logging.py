"""Tests for structured logging and request logging middleware."""

import json
import logging
from io import StringIO
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from sysadmin.core.config import ServiceConfig
from sysadmin.core.logging_setup import configure_logging

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
        parsed = json.loads(output)
        assert parsed["message"] == "hello world"

    def test_json_format_has_required_fields(self):
        config = ServiceConfig(log_format="json")
        output = self._capture_log(config, "check fields")
        parsed = json.loads(output)
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
        parsed = json.loads(buf.getvalue())
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
