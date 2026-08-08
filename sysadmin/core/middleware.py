"""Request logging middleware for FastAPI.

Logs method, path, status code, and duration for every request.
The health endpoint (high-frequency polling) and the SSE stream
(long-lived connections) are excluded to avoid noise.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("sysadmin.access")

# Paths excluded from access logging:
#   /health               — high-frequency polling (SNAG-API-002)
#   /api/sysadmin/events  — long-lived SSE streams; logging them at open
#                           time is noise, and the whole point of the
#                           stream is to remove polling log spam
_EXCLUDED_PATHS = frozenset({"/health", "/api/sysadmin/events"})


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        logger.info(
            "%s %s %d %.1fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 1),
            },
        )
        return response
