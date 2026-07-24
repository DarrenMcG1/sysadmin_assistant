"""Configuration for the tray application.

Reads the shared ``config.yaml`` for service host/port and an optional
``tray:`` section for poll intervals.  CLI ``--api-url`` overrides everything.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel

# Canonical host/port defaults shared with the backend's ServiceConfig
# (sysadmin.defaults is stdlib-only, like sysadmin.contracts — safe to
# import from the tray without pulling in backend dependencies)
from sysadmin.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT, default_api_url


class TrayConfig(BaseModel):
    """Tray-specific configuration with sensible defaults."""

    api_url: str = default_api_url()
    auth_token: str | None = None
    status_poll_seconds: int = 10
    resource_poll_seconds: int = 30
    alert_poll_seconds: int = 15
    show_notifications: bool = True
    notify_min_severity: str = "critical"
    dashboard_url: str | None = None


def _default_config_path() -> Path:
    """Walk upward from this file to find config.yaml in the project root."""
    here = Path(__file__).resolve().parent
    for ancestor in [here.parent, here.parent.parent, Path.cwd()]:
        candidate = ancestor / "config.yaml"
        if candidate.exists():
            return candidate
    return here.parent / "config.yaml"


def load_tray_config(
    config_path: Path | None = None,
    api_url_override: str | None = None,
) -> TrayConfig:
    """Build a TrayConfig from the YAML file and optional overrides.

    Resolution order (highest priority first):
        1. ``api_url_override`` (--api-url CLI flag)
        2. ``tray:`` section in config.yaml
        3. ``service.host`` + ``service.port`` from config.yaml
        4. Hardcoded defaults
    """
    if config_path is None:
        config_path = _default_config_path()

    raw: dict = {}
    if config_path.exists():
        with open(config_path) as f:
            raw = yaml.safe_load(f) or {}

    # Start from tray section defaults
    tray_section = raw.get("tray", {}) or {}
    kwargs: dict = {}

    # Poll intervals from tray section
    for key in ("status_poll_seconds", "resource_poll_seconds",
                "alert_poll_seconds", "show_notifications",
                "notify_min_severity", "dashboard_url"):
        if key in tray_section:
            kwargs[key] = tray_section[key]

    # Shared API auth token from the backend's api: section
    api_section = raw.get("api", {}) or {}
    if api_section.get("auth_token"):
        kwargs["auth_token"] = api_section["auth_token"]

    # Derive api_url from service section if not in tray section
    if "api_url" not in kwargs:
        svc = raw.get("service", {})
        host = svc.get("host", DEFAULT_API_HOST)
        port = svc.get("port", DEFAULT_API_PORT)
        kwargs["api_url"] = default_api_url(host, port)

    # CLI override wins
    if api_url_override:
        kwargs["api_url"] = api_url_override

    return TrayConfig(**kwargs)
