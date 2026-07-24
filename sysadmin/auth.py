"""Bearer-token authentication for state-changing API endpoints.

The shared token lives in ``config.yaml`` under ``api.auth_token``.
When unset or empty, authentication is disabled (backwards compatible)
and mutating endpoints are open — ``main.py`` logs a warning at startup
in that case.

Read-only GET endpoints are deliberately left unauthenticated so
dashboards (tray app, PA frontend) keep working without a token.
Callers of mutating endpoints (tray client, PA backend) must send:

    Authorization: Bearer <token>

Rationale: binding to localhost does not stop CSRF-style POSTs from
browser pages or other local processes.
"""

import secrets

from fastapi import HTTPException, Request

from sysadmin.config import get_config


async def require_auth(request: Request) -> None:
    """FastAPI dependency enforcing the shared bearer token.

    No-op when ``api.auth_token`` is unset/empty.  Raises 401 with a
    ``WWW-Authenticate: Bearer`` header on a missing or wrong token.
    """
    token = get_config().api.auth_token
    if not token:
        return  # Auth disabled — backwards compatible

    header = request.headers.get("Authorization", "")
    scheme, _, supplied = header.partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
        supplied.strip().encode("utf-8"), token.encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
