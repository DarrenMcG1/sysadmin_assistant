"""The ``sd_notify`` sender: ``READY=1``, ``WATCHDOG=1`` and ``STOPPING=1``.

What ``Type=notify`` + ``WatchdogSec=`` on ``sysadmin.service`` needs from
the process (tasks.md, Session 39 block). Written before the unit edit, so
the sender ships while the unit still reads ``Type=simple`` and does
nothing there. Stdlib only: the protocol is one datagram on a Unix socket,
and neither ``systemd-python`` nor ``sdnotify`` is worth a dependency for it.

Three rules:

1. **No socket is a silent no-op, never an error.** Under ``Type=simple``
   systemd sets no ``NOTIFY_SOCKET``, and the rollback written in
   ``systemd/sysadmin.service`` (Session 327) relies on that: it reverts
   the unit and leaves this code alone. The rehearsal there showed a
   process whose send was a no-op after the rollback running normally.
   The same holds for a test run, a session driving the app by hand, and
   ``uv run uvicorn``.

2. **The environment is read here, and that is a handover, not a setting.**
   ``CLAUDE.md`` says this service reads no environment variables, and
   ``core/abandoned_runs.py`` refused ``INVOCATION_ID`` on that rule
   because it could mint its own id instead. Nothing can be minted here:
   systemd passes the socket's address only as ``NOTIFY_SOCKET`` and the
   watchdog's period only as ``WATCHDOG_USEC``. That is the class
   ``monitor/mqtt_alerts.py`` already reads ``CREDENTIALS_DIRECTORY``
   under: systemd telling the process what it set up, which config.yaml
   cannot hold because the unit decides it. The rule is about where
   settings live (ADR-0003).

3. **The ping interval comes from the unit, never from config.yaml.**
   Half of ``WATCHDOG_USEC``, as ``sd_watchdog_enabled(3)`` advises. A
   configured interval would be a second statement of ``WatchdogSec=``
   that could disagree with it, and a disagreement in one direction is a
   watchdog kill every period. ``WATCHDOG_PID``, when set, must be this
   process, so a child that inherits the environment never pings for us.

The ping runs as a task on the API's event loop, which is the point of it:
if that loop wedges, the pings stop and systemd kills the process. It
does not watch the scheduler's threads. ``self_monitor`` covers those.
"""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from collections.abc import Callable

logger = logging.getLogger(__name__)

#: Set by systemd for ``Type=notify`` (and ``NotifyAccess=``). A path, or
#: an abstract-namespace name written with a leading ``@``.
SOCKET_ENV = "NOTIFY_SOCKET"

#: Set by systemd when ``WatchdogSec=`` is non-zero: the period in µs.
WATCHDOG_USEC_ENV = "WATCHDOG_USEC"

#: Set alongside it: the PID the watchdog expects pings from.
WATCHDOG_PID_ENV = "WATCHDOG_PID"

Sender = Callable[[str], bool]


def _address(raw: str) -> str | bytes | None:
    """The address to send to, or ``None`` for one systemd never hands out.

    ``@name`` is the abstract namespace, which the socket API spells with a
    leading NUL. ``vsock:`` addresses (VMs) are not supported, and refused
    rather than mistaken for a path.
    """
    if raw.startswith("@"):
        return b"\0" + raw[1:].encode()
    if raw.startswith("/"):
        return raw
    return None


def notify(state: str) -> bool:
    """Send one ``sd_notify`` state string. ``False`` if nothing was sent.

    Never raises. A failure to send is logged, because under a watchdog
    the next thing to happen is a kill and this line is its cause.
    """
    raw = os.environ.get(SOCKET_ENV)
    if not raw:
        return False
    address = _address(raw)
    if address is None:
        logger.warning("sd_notify_unsupported_socket", extra={"socket": raw})
        return False
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(address)
            sock.sendall(state.encode())
    except OSError as exc:
        logger.warning(
            "sd_notify_failed", extra={"state": state, "error": str(exc)}
        )
        return False
    return True


def watchdog_interval() -> float | None:
    """Seconds between pings, or ``None`` when no watchdog is armed for us."""
    raw = os.environ.get(WATCHDOG_USEC_ENV)
    if not raw:
        return None
    pid = os.environ.get(WATCHDOG_PID_ENV)
    if pid and pid != str(os.getpid()):
        return None
    try:
        usec = int(raw)
    except ValueError:
        logger.warning("sd_watchdog_unparseable", extra={"value": raw})
        return None
    if usec <= 0:
        return None
    return usec / 2_000_000


async def ping_forever(interval: float, send: Sender = notify) -> None:
    """``WATCHDOG=1`` every ``interval`` seconds until cancelled."""
    while True:
        send("WATCHDOG=1")
        await asyncio.sleep(interval)


def start_watchdog(send: Sender = notify) -> asyncio.Task[None] | None:
    """Start pinging on the running loop, or return ``None`` if unarmed."""
    interval = watchdog_interval()
    if interval is None:
        return None
    logger.info("sd_watchdog_armed", extra={"interval_seconds": interval})
    return asyncio.create_task(ping_forever(interval, send), name="sd-watchdog")
