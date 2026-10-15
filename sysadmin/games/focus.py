"""The KWin focus probe — which window is active, asked once (ADR-0016 §3).

KWin 6.7.5 has no D-Bus call that returns the active window, so the
probe hands KWin a two-line script that prints ``workspace.activeWindow``'s
PID, runs it, unloads it, and reads the line back from the user journal
by a token unique to the call.  It leaves KWin as it found it.

Four rules, the first two the opposite of what ADR-0016 §3 assumed:

1. **The daemon is a system unit, so the bus address is built here.**
   ``sysadmin.service`` runs in the system slice as ``User=gaddi`` and its
   environment carries neither ``DBUS_SESSION_BUS_ADDRESS`` nor
   ``XDG_RUNTIME_DIR``; ``gdbus`` with that environment fails with
   "Cannot autolaunch D-Bus without X11 $DISPLAY".  Given
   ``XDG_RUNTIME_DIR`` alone, ``gdbus`` finds ``$XDG_RUNTIME_DIR/bus`` and
   ``journalctl --user`` reads the line (driven 2026-10-15) — the same
   repair :func:`sysadmin.monitor.systemd.build_env` makes for
   ``systemctl --user``, so it is reused rather than restated.
2. **The script file lives in the runtime directory, not ``/tmp``.**
   KWin opens the path itself, so it has to be one KWin can see; the
   runtime directory is the user's own and is where the bus already is.
3. **A leftover load is cleared, not worked around.**  ``loadScript``
   answers ``-1`` when the plugin name is already loaded — a probe killed
   between load and unload leaves exactly that — so the probe unloads the
   name and loads once more.  A fresh name per call would never collide
   and would leak one script into KWin per crash instead.
4. **No active window is an answer.**  KWin prints ``pid=0`` when nothing
   holds focus, and the probe returns :data:`NO_WINDOW` rather than
   ``None``: the game is known to be unfocused.  ``None`` is reserved for
   *nobody could tell*, which ADR-0016 §3 forbids reading as unfocused.

Any failure — ``gdbus`` missing, KWin not running, no session at all, a
timeout, the line not in the journal — returns ``None``.  The reason is
logged at debug, and the poll records ``focus: unknown`` in its run
details, which is where a probe that has stopped working shows.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import re
import tempfile
import time
import uuid

from sysadmin.monitor.systemd import SystemdQueryError, build_env

logger = logging.getLogger(__name__)

PLUGIN_NAME = "sysadmin-focus-probe"
MARKER = "sysadmin-focus-probe"

#: What :func:`kwin_focus_probe` returns when KWin reports no active
#: window.  PID 0 is in no game's process tree, so the poll records the
#: minute as unfocused (rule 4).
NO_WINDOW = 0

#: Seconds one ``gdbus`` or ``journalctl`` call may take.
CALL_TIMEOUT = 5.0
#: How long the journal is given to show the line after ``run()``.
#: Measured 2026-10-15: present on the first read every time.
JOURNAL_ATTEMPTS = 5
JOURNAL_RETRY_SECONDS = 0.2

_SCRIPT = (
    "var w = workspace.activeWindow;\n"
    'print("{marker} token={token} pid=" + (w ? w.pid : 0));\n'
)


def script_text(token: str) -> str:
    """The KWin script for one call."""
    return _SCRIPT.format(marker=MARKER, token=token)


def parse_line(output: str, token: str) -> int | None:
    """The PID from this call's journal line, or ``None`` if it is absent."""
    match = re.search(rf"{MARKER} token={re.escape(token)} pid=(-?\d+)", output)
    if match is None:
        return None
    pid = int(match.group(1))
    return pid if pid > 0 else NO_WINDOW


def parse_load_id(output: str) -> int | None:
    """``loadScript``'s id from ``gdbus``'s ``(0,)``; ``None`` if unreadable."""
    match = re.fullmatch(r"\((-?\d+),\)", output.strip())
    return int(match.group(1)) if match else None


class ProbeFailedError(RuntimeError):
    """The probe could not tell which window is active."""


async def _run(args: list[str], env: dict[str, str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), CALL_TIMEOUT)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise ProbeFailedError(f"{args[0]} timed out after {CALL_TIMEOUT} s") from None
    if proc.returncode:
        raise ProbeFailedError(f"{args[0]} exited {proc.returncode}: {stderr.decode().strip()}")
    return stdout.decode()


def _gdbus(path: str, method: str, *args: str) -> list[str]:
    return [
        "gdbus", "call", "--session",
        "--dest", "org.kde.KWin",
        "--object-path", path,
        "--method", method,
        *args,
    ]


async def _load(script_path: str, env: dict[str, str]) -> int:
    load = _gdbus("/Scripting", "org.kde.kwin.Scripting.loadScript", script_path, PLUGIN_NAME)
    script_id = parse_load_id(await _run(load, env))
    if script_id == -1:
        # Rule 3: a previous probe died between load and unload.
        await _run(_gdbus("/Scripting", "org.kde.kwin.Scripting.unloadScript", PLUGIN_NAME), env)
        script_id = parse_load_id(await _run(load, env))
    if script_id is None or script_id < 0:
        raise ProbeFailedError(f"loadScript answered {script_id}")
    return script_id


async def _read_journal(token: str, since: float, env: dict[str, str]) -> int | None:
    # ``--since`` is second-granular, so it starts a second early; the
    # token, not the window, is what picks this call's line.
    args = [
        "journalctl", "--user", "-t", "kwin_wayland",
        "--since", f"@{int(since) - 1}",
        "-o", "cat", "--no-pager",
    ]
    for attempt in range(JOURNAL_ATTEMPTS):
        pid = parse_line(await _run(args, env), token)
        if pid is not None:
            return pid
        if attempt + 1 < JOURNAL_ATTEMPTS:
            await asyncio.sleep(JOURNAL_RETRY_SECONDS)
    return None


async def kwin_focus_probe() -> int | None:
    """The active window's PID, :data:`NO_WINDOW`, or ``None`` if unknown."""
    try:
        env = build_env(user=True)
    except SystemdQueryError as exc:
        logger.debug("focus probe: %s", exc)
        return None
    assert env is not None  # user scope always builds one
    token = uuid.uuid4().hex
    fd, script_path = tempfile.mkstemp(
        prefix=f"{PLUGIN_NAME}-", suffix=".js", dir=env["XDG_RUNTIME_DIR"]
    )
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(script_text(token))
        since = time.time()
        loaded = False
        try:
            script_id = await _load(script_path, env)
            loaded = True
            await _run(_gdbus(f"/Scripting/Script{script_id}", "org.kde.kwin.Script.run"), env)
        finally:
            if loaded:
                with contextlib.suppress(ProbeFailedError, OSError):
                    await _run(
                        _gdbus("/Scripting", "org.kde.kwin.Scripting.unloadScript", PLUGIN_NAME),
                        env,
                    )
        pid = await _read_journal(token, since, env)
        if pid is None:
            logger.debug("focus probe: no journal line for token %s", token)
        return pid
    except (ProbeFailedError, OSError) as exc:
        logger.debug("focus probe: %s", exc)
        return None
    finally:
        with contextlib.suppress(OSError):
            os.unlink(script_path)
