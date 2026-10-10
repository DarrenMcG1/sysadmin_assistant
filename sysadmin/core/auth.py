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

**The origin half needs no secret** (``SNAG-API-005``). A body-less
``POST`` is a CORS *simple request*: the browser sends it without a
preflight, and CORS hides only the response, so the handler has already
acted. A browser stamps ``Origin`` on every cross-site ``POST`` and a
page cannot remove it, while the tray and server-side callers send none.
So a mutating request whose ``Origin`` is present and not in
``service.cors_origins`` is refused with 403 **before** the token is
checked, whether or not a token is set. An absent ``Origin`` passes, which
is why this stops a web page and never another local process: that half
is the token's.

The allowed list is the one ``create_app`` handed ``CORSMiddleware``,
read off ``app.state.cors_origins`` rather than ``get_config()``.
``service`` is restart-only (``reload.RESTART_ONLY``), so a reload that
installed a new list would otherwise leave the middleware and this check
disagreeing about which pages may call the API.
"""

import secrets

from fastapi import HTTPException, Request

from sysadmin.core.config import get_config


async def require_auth(request: Request) -> None:
    """FastAPI dependency guarding every mutating route.

    Raises 403 when ``Origin`` is set and not an allowed origin (see the
    module docstring), then enforces the bearer token: a no-op when
    ``api.auth_token`` is unset/empty, and 401 with a
    ``WWW-Authenticate: Bearer`` header on a missing or wrong token.
    """
    origin = request.headers.get("Origin")
    if origin is not None and not origin_allowed(
        origin, request.app.state.cors_origins
    ):
        raise HTTPException(status_code=403, detail="Cross-site request refused")

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


def origin_allowed(origin: str, allowed: list[str]) -> bool:
    """Whether ``origin`` may call a mutating route.

    Mirrors ``CORSMiddleware``'s own test: an exact string match, or
    ``"*"`` in the list. ``Origin: null`` (a sandboxed frame, a
    ``file://`` page) matches nothing short of ``"*"``.
    """
    return "*" in allowed or origin in allowed
