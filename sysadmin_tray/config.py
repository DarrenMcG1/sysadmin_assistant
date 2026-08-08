"""Configuration for the tray application.

Reads the shared ``config.yaml`` for service host/port, an optional
``tray:`` section for poll intervals, and the ``notifications.tray:``
section for the notification-calm tunables.  CLI ``--api-url`` overrides
everything.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# Canonical host/port defaults shared with the backend's ServiceConfig
# (sysadmin.core.defaults is stdlib-only, like sysadmin.core.contracts — safe to
# import from the tray without pulling in backend dependencies)
from sysadmin.core.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT, default_api_url


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

    # ── Notification calm (config.yaml ``notifications.tray:``) ──────
    #: minutes a fingerprint stays quiet after firing, so a flapping
    #: alert produces one "flapped N×" summary instead of N interrupts
    flap_cooldown_minutes: int = 30
    #: consecutive failing polls before a critical escalates from the
    #: opening quiet notification to a persistent one
    escalation_polls: int = 3
    #: new alerts in a single poll at/above this count become one summary
    coalesce_threshold: int = 2
    #: how long the "Snooze" notification button silences a service
    snooze_minutes: int = 60
    #: warnings badge the icon only and arrive as a periodic digest
    digest_mode: bool = False
    digest_interval_minutes: int = 60
    #: honour the desktop's own DND (org.freedesktop.Notifications Inhibited)
    respect_desktop_dnd: bool = True
    #: services whose alerts are permanently silenced (expected-down)
    muted_services: list[str] = Field(default_factory=list)


def _default_config_path() -> Path:
    """Walk upward from this file to find config.yaml in the project root."""
    here = Path(__file__).resolve().parent
    for ancestor in [here.parent, here.parent.parent, Path.cwd()]:
        candidate = ancestor / "config.yaml"
        if candidate.exists():
            return candidate
    return here.parent / "config.yaml"


def _read_services(config_path: Path) -> list[dict]:
    """The ``services:`` list from services.yaml beside config.yaml.

    Parsed raw rather than through the backend models on purpose: the tray
    is a separate process that must start whether or not the backend is
    installed or the estate is migrated, and a missing or malformed
    services.yaml costs it a mute list, not a launch.
    """
    path = config_path.parent / "services.yaml"
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    services = raw.get("services") or []
    return [s for s in services if isinstance(s, dict)]


def _collect_muted_services(
    notif_section: dict, services: list[dict]
) -> list[str]:
    """Union of explicitly muted names and ``mute: true`` services.

    Muting is for services that are *expected* to be down (a dev backend
    that only runs on demand) — their alerts never produce a desktop
    notification, though they still colour the tray icon and appear in
    the dashboard.

    ``mute`` is now available on every service, which it was not while
    half of them were generated from projects.yaml with no flag of their
    own. ``notifications.tray.mute_services`` stays as the way to mute
    something without editing its declaration.
    """
    muted: list[str] = []
    for name in notif_section.get("mute_services", []) or []:
        if name and name not in muted:
            muted.append(str(name))

    for service in services:
        name = service.get("name")
        if service.get("mute") and name and name not in muted:
            muted.append(str(name))

    return muted


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

    Notification-calm tunables come from ``notifications.tray:``; the
    muted-service list is the union of ``notifications.tray.mute_services``
    and every monitored service flagged ``mute: true`` under
    ``agents.sysadmin.services``.
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

    # Notification-calm tunables from notifications.tray:
    notif_section = (raw.get("notifications", {}) or {}).get("tray", {}) or {}
    for key in ("flap_cooldown_minutes", "escalation_polls",
                "coalesce_threshold", "snooze_minutes", "digest_mode",
                "digest_interval_minutes", "respect_desktop_dnd"):
        if key in notif_section:
            kwargs[key] = notif_section[key]

    kwargs["muted_services"] = _collect_muted_services(
        notif_section, _read_services(config_path)
    )

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
