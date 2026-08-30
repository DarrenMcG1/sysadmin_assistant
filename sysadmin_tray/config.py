"""Configuration for the tray application.

Reads the shared ``config.yaml`` for service host/port, an optional
``tray:`` section for poll intervals, and the ``notifications.tray:``
section for the notification-calm tunables.  CLI ``--api-url`` overrides
everything.

**This program reports the undeclared keys in its own section**
(``SNAG-CFG-005``).  ``SNAG-CFG-004`` made an unread key visible
everywhere the backend owns, and left the top-level ``tray:`` section as
the residue: :data:`sysadmin.core.config.FOREIGN_KEYS` exempts it whole,
because holding a model of another parser's section there is the
second-owner defect.  So the section had no watcher on either side, and
``tray.status_poll_secondss: 99`` was accepted, dropped, and silent —
measured 2026-08-30, ``status_poll_seconds`` reading its default with
nothing logged.

Four rules, three of them the opposite of the obvious implementation:

1. **The allowlist is the authority, never the model.**  The obvious fix
   is a walk of ``tray:`` against :class:`TrayConfig`, the way
   :mod:`sysadmin.core.config_keys` walks ``config.yaml`` against
   ``AppConfig``.  It is wrong here and would ship green: ``TrayConfig``
   declares **19** fields and this section supplies **7**, the other
   twelve arriving from ``notifications.tray:``, ``api:`` and
   ``services.yaml`` — so a model walk accepts ``tray.reminder_hours: 5``
   as declared, when the value is read from somewhere else and setting it
   here does nothing.  The model over-declares relative to the section;
   :data:`TRAY_SECTION_KEYS` does not, which is what makes the report one
   set difference.
2. **``notifications.tray:`` is deliberately *not* reported here.**  The
   symmetric move is the second-owner defect: that region is exempted by
   **leaf** rather than by subtree, so the backend already names a typo
   in it — measured, ``notifications.tray.digest_modee`` and
   ``mute_servicess`` both come back from ``report_for_file``.  One fact,
   one speaker.  This program speaks only for the section nothing else
   can see.
3. **A shape it cannot read is reported, never skipped** —
   ``config_keys`` rule 3, and here it also closes a crash.  ``tray: 5``
   used to raise ``TypeError: argument of type 'int' is not iterable``
   out of the membership test below, so the one section this module
   hand-parses failed *unhandled* while ``_read_services`` next door
   catches its own errors and costs "a mute list, not a launch".  It is
   now ``unwalkable``: the section went unread, so its zero unknown keys
   are zero-because-blind.
4. **It reports; it cannot refuse** — ``config_keys`` rule 1, for that
   rule's reason.  A tray that will not start over a stale knob is worse
   than a tray with one dead knob.  :func:`tray_section_report` is total
   over every YAML shape (it tests the type, then iterates a mapping), so
   there is no path by which the annotation breaks what it annotates.

**Stated limit, filed rather than absorbed as ``SNAG-TRAY-011``:** the
warning is quieter than the backend's by three channels.
``sysadmin-tray.service`` carries no ``log:`` block in ``services.yaml``
— measured, ``composed_log_sources`` returns 15 sources and it is not one
— so nothing ingests the line, no alert row is raised, and no endpoint
serves it; and :func:`load_tray_config` has exactly one caller, at
startup, where the backend re-reports on every ``POST
/api/sysadmin/reload``.  An operator who edits ``tray:`` and reloads the
daemon hears this on their next tray restart, not on the edit.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# The backend's vocabulary for "what a config walk found", reused rather
# than restated. ``sysadmin.core`` must not import the tray; the reverse
# is allowed and this module already does it for ``defaults``, so the two
# programs describe an unread key with one type instead of two that can
# drift. ``config_keys`` depends on nothing the tray does not already
# have (stdlib, yaml, pydantic).
from sysadmin.core.config_keys import KeyReport

# Canonical host/port defaults shared with the backend's ServiceConfig
# (sysadmin.core.defaults is stdlib-only, like sysadmin.core.contracts — safe to
# import from the tray without pulling in backend dependencies)
from sysadmin.core.defaults import DEFAULT_API_HOST, DEFAULT_API_PORT, default_api_url

logger = logging.getLogger(__name__)


class TrayConfig(BaseModel):
    """Tray-specific configuration with sensible defaults."""

    api_url: str = default_api_url()
    #: The estate's 8400 service — project state lives there since the
    #: Session 4 cutover (ADR-0005). /api/projects/overview and
    #: /api/projects/{name} are fetched from here; /api/projects/managed
    #: stays on api_url (service health is this repository's data).
    estate_api_url: str = "http://127.0.0.1:8400"
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
    #: hours a still-open alert stays quiet before being restated; 0 = off
    reminder_hours: float = 24.0
    #: seconds an unreachable backend is tolerated before the tray speaks;
    #: 0 = off.  ``max(3 × status_poll_seconds, 300)`` — the floor is what
    #: does the work here, because this leaf and ``status_poll_seconds``
    #: disagree between the model and the shipped file.  Derivation and
    #: measurement:
    #: :meth:`sysadmin_tray.notifications.NotificationPolicy.evaluate_backend_unreachable`
    backend_unreachable_grace_seconds: float = 300.0
    #: services whose alerts are permanently silenced (expected-down)
    muted_services: list[str] = Field(default_factory=list)


#: Keys this program reads out of config.yaml's top-level ``tray:``
#: section, and out of ``notifications.tray:``.
#:
#: Lifted out of the loops that consume them so the backend's
#: :data:`sysadmin.core.config.FOREIGN_KEYS` can be *pinned* against them
#: rather than merely agreeing by hand (``SNAG-CFG-004``). The backend
#: cannot import this module — ``sysadmin.core`` must not depend on the
#: tray — so the declaration is duplicated by necessity and the drift is
#: caught by a test instead: import where you can, pin where you cannot.
#:
#: ``mute_services`` is deliberately absent from the second tuple. It is
#: read here *and* by the backend (``TrayNotificationsConfig``), so it is
#: not foreign, and listing it would make the backend exempt the one key
#: under ``notifications.tray:`` it actually depends on.
TRAY_SECTION_KEYS: tuple[str, ...] = (
    "status_poll_seconds",
    "resource_poll_seconds",
    "alert_poll_seconds",
    "show_notifications",
    "notify_min_severity",
    "dashboard_url",
    "estate_api_url",
)

NOTIFICATIONS_TRAY_KEYS: tuple[str, ...] = (
    "flap_cooldown_minutes",
    "escalation_polls",
    "coalesce_threshold",
    "snooze_minutes",
    "digest_mode",
    "digest_interval_minutes",
    "respect_desktop_dnd",
    "reminder_hours",
    "backend_unreachable_grace_seconds",
)


def tray_section_report(tray_section: Any) -> KeyReport:
    """Keys under ``tray:`` that this program does not read.

    One set difference against :data:`TRAY_SECTION_KEYS`, which is the
    allowlist the loop below actually consumes — see rule 1 in the module
    docstring for why the model is not usable as the authority here, and
    rule 2 for why ``notifications.tray:`` is not this function's
    business.

    A non-mapping section (``tray: 5``, ``tray: [a, b]``) is reported as
    ``unwalkable`` rather than skipped or raised: nothing under it was
    read, so its empty ``unknown`` is zero-because-blind.  ``walked``
    stays true — the *file* was read, and the caller has already parsed
    it — so the boolean keeps the meaning ``config_keys`` gives it.

    ``None`` is clean, not unwalkable, and the two are separated here for
    the reason ``_walk_into`` separates them: a file with no ``tray:`` at
    all, and a ``tray:`` with nothing indented under it, both parse to
    ``None`` and carry no key that can be wrong.  Reporting those as
    blind would make the shipped-by-most-operators case a permanent
    warning, which is how a report gets filtered.  Note this is the one
    place the caller must **not** pre-coerce with ``or {}``: ``tray: []``
    and ``tray: 0`` are falsy *and* malformed, so a coercion upstream
    hands this function a clean ``{}`` and the shape goes unreported.

    Total by construction: it tests the type, then iterates a mapping, so
    no YAML shape reaches an operation that can raise.  That is rule 4's
    "it cannot refuse" settled by the shape of the function rather than
    by a caller remembering to wrap it.
    """
    if tray_section is None:
        return KeyReport()
    if not isinstance(tray_section, dict):
        return KeyReport(unwalkable=["tray"])
    # File order, not sorted: the operator is looking at lines.
    unknown = [f"tray.{key}" for key in tray_section if key not in TRAY_SECTION_KEYS]
    return KeyReport(unknown=unknown)


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
        2. ``service.host`` + ``service.port`` from config.yaml
        3. Hardcoded defaults

    ``tray.api_url`` is **not** a step, and the ``2. tray: section`` this
    docstring used to list has never been one — measured 2026-08-30,
    ``tray.api_url: http://bogus:1234`` is dropped and the URL still comes
    from ``service:``.  ``api_url`` has never appeared in
    :data:`TRAY_SECTION_KEYS`, so the ``if "api_url" not in kwargs`` guard
    that stood here was dead from the module's first commit (``81b3bfb``)
    and its comment asserted the behaviour the docstring copied.  It stays
    unread on purpose: ``service.host``/``service.port`` is where the
    backend's address is declared, and a second home for it is two
    statements of one fact.  ``estate_api_url`` *is* read here because
    8400 has no ``service:`` block to be derived from — one statement
    each, in different places, rather than one fact in two.

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
    # Uncoerced on purpose — see tray_section_report's docstring: an
    # ``or {}`` here makes ``tray: []`` indistinguishable from a clean
    # empty section.
    tray_section = raw.get("tray")
    kwargs: dict = {}

    # SNAG-CFG-005: this section is the one region of config.yaml the
    # backend cannot judge, so this is the only thing that can say a key
    # in it went unread. Reported, never refused (rule 4) — a stale knob
    # must not cost a launch.
    # The keys are in the **message**, not in ``extra=``. The backend
    # writes ``logger.warning("config_unknown_keys", extra={"keys": ...})``
    # and that is readable because ``JsonFormatter`` folds ``extra`` into
    # the line; this program's formatter is ``main()``'s
    # ``basicConfig(format="… %(message)s")``, which renders ``extra``
    # nowhere. Driven live rather than reasoned about: the first version
    # of this warning reached the journal as the bare string
    # ``tray_config_unknown_keys``, announcing that a key was dropped and
    # unable to say which — this entry's own defect one level down, and a
    # convention copied without the formatter that makes it work.
    keys = tray_section_report(tray_section)
    if keys.unknown:
        logger.warning(
            "tray_config_unknown_keys: config.yaml sets %s under tray:, which "
            "the tray does not read — ignored. Check the spelling; the setting "
            "is not taking effect.",
            ", ".join(keys.unknown),
        )
    if keys.unwalkable:
        logger.warning(
            "tray_config_unwalked_section: config.yaml's %s: is not a mapping, so "
            "nothing under it was read and every tray setting is at its default.",
            ", ".join(keys.unwalkable),
        )
    if not isinstance(tray_section, dict):
        tray_section = {}

    # Poll intervals (and the estate URL) from tray section
    for key in TRAY_SECTION_KEYS:
        if key in tray_section:
            kwargs[key] = tray_section[key]

    # Notification-calm tunables from notifications.tray:
    notif_section = (raw.get("notifications", {}) or {}).get("tray", {}) or {}
    for key in NOTIFICATIONS_TRAY_KEYS:
        if key in notif_section:
            kwargs[key] = notif_section[key]

    kwargs["muted_services"] = _collect_muted_services(
        notif_section, _read_services(config_path)
    )

    # Shared API auth token from the backend's api: section
    api_section = raw.get("api", {}) or {}
    if api_section.get("auth_token"):
        kwargs["auth_token"] = api_section["auth_token"]

    # Derive api_url from the service: section. Unconditional since
    # 2026-08-30: nothing above can put ``api_url`` in kwargs, so the
    # ``if "api_url" not in kwargs`` that stood here was dead by
    # construction, and its comment ("if not in tray section") is what the
    # loader docstring copied. Removed rather than kept, because a dead
    # branch asserting a behaviour the module does not have is how the
    # wrong resolution order survived the module's whole life.
    svc = raw.get("service", {}) or {}
    host = svc.get("host", DEFAULT_API_HOST)
    port = svc.get("port", DEFAULT_API_PORT)
    kwargs["api_url"] = default_api_url(host, port)

    # CLI override wins
    if api_url_override:
        kwargs["api_url"] = api_url_override

    return TrayConfig(**kwargs)
