"""Do Not Disturb manager — runtime state + schedule evaluation.

Consumers call ``dnd_manager.should_suppress(severity)`` to check whether
a notification should be silenced. Critical alerts can optionally break
through DND when ``allow_critical`` is set in config.
"""

import logging
from datetime import datetime, time

from sysadmin.config import DndConfig, get_config

logger = logging.getLogger(__name__)


def _parse_time(hhmm: str) -> time:
    """Parse "HH:MM" string into a ``datetime.time``."""
    parts = hhmm.strip().split(":")
    return time(int(parts[0]), int(parts[1]))


def _in_window(now_time: time, start: time, end: time) -> bool:
    """Check if *now_time* falls within a start→end window.

    Handles overnight windows (e.g. 23:00→07:00) where end < start.
    """
    if start <= end:
        return start <= now_time <= end
    # Overnight: 23:00→07:00 means "23:00–midnight OR midnight–07:00"
    return now_time >= start or now_time <= end


class DndManager:
    """Singleton-style DND state manager.

    The ``manual_override`` flag lets the API or tray toggle DND
    independently of the schedule. When ``None``, the schedule
    decides; when ``True``/``False``, it takes precedence.
    """

    def __init__(self) -> None:
        self._manual_override: bool | None = None

    @property
    def config(self) -> DndConfig:
        return get_config().notifications.dnd

    @property
    def manual_override(self) -> bool | None:
        return self._manual_override

    def set_manual_override(self, enabled: bool | None) -> None:
        """Set or clear the manual DND override.

        ``True``  = force DND on
        ``False`` = force DND off
        ``None``  = revert to schedule-only
        """
        self._manual_override = enabled
        logger.info("dnd manual_override set to %s", enabled)

    def is_active(self, now: datetime | None = None) -> bool:
        """Return whether DND is currently active.

        Priority: manual override > schedule > config default.
        """
        if self._manual_override is not None:
            return self._manual_override

        cfg = self.config

        # Check schedule windows
        now = now or datetime.now()
        now_time = now.time()
        for window in cfg.schedule:
            start = _parse_time(window.start)
            end = _parse_time(window.end)
            if _in_window(now_time, start, end):
                return True

        # Fall back to the config default (usually False)
        return cfg.enabled

    def should_suppress(self, severity: str, now: datetime | None = None) -> bool:
        """Return True if a notification of *severity* should be suppressed.

        Critical alerts break through DND when ``allow_critical`` is set.
        """
        if not self.is_active(now):
            return False

        # DND is active — check if critical should break through
        if severity == "critical" and self.config.allow_critical:
            return False

        return True

    def get_status(self, now: datetime | None = None) -> dict:
        """Return current DND status for the API."""
        return {
            "active": self.is_active(now),
            "manual_override": self._manual_override,
            "config_enabled": self.config.enabled,
            "allow_critical": self.config.allow_critical,
            "schedule": [
                {"start": w.start, "end": w.end}
                for w in self.config.schedule
            ],
        }


# Module-level singleton
dnd_manager = DndManager()
