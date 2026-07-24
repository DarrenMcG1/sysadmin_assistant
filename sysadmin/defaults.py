"""Canonical network defaults shared by the backend and the tray app.

Single source of truth for where the API listens (Session 14 — the
backend's ``ServiceConfig`` and the tray's ``TrayConfig`` each hard-coded
these and could drift).

IMPORTANT — keep this module dependency-light: stdlib ONLY.  Like
:mod:`sysadmin.contracts`, the tray imports it at runtime and must not
pull in FastAPI, SQLAlchemy, or any other heavy backend dependency.
"""

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8500


def default_api_url(host: str = DEFAULT_API_HOST, port: int = DEFAULT_API_PORT) -> str:
    """Build the base URL clients use to reach the API."""
    return f"http://{host}:{port}"
