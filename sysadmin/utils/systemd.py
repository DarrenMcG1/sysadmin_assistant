"""Systemd unit status helpers via subprocess.

All helpers accept ``user=True`` to target *user* units
(``systemctl --user ...``) instead of system units.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


def _base_cmd(user: bool) -> list[str]:
    """Build the systemctl command prefix for system or user scope."""
    return ["systemctl", "--user"] if user else ["systemctl"]


async def is_active(unit: str, user: bool = False) -> bool:
    """Check if a systemd unit is active."""
    proc = await asyncio.create_subprocess_exec(
        *_base_cmd(user), "is-active", unit,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "active"


async def get_unit_status(unit: str, user: bool = False) -> dict:
    """Get detailed status of a systemd unit."""
    props = [
        "ActiveState", "SubState", "MainPID",
        "MemoryCurrent", "CPUUsageNSec", "LoadState",
    ]
    prop_args = ",".join(props)

    proc = await asyncio.create_subprocess_exec(
        *_base_cmd(user), "show", unit, f"--property={prop_args}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    result: dict = {"unit": unit}
    for line in stdout.decode().strip().split("\n"):
        if "=" in line:
            key, _, value = line.partition("=")
            result[key] = value

    result["is_active"] = result.get("ActiveState") == "active"
    return result


async def _control_unit(action: str, unit: str, user: bool = False) -> tuple[bool, str]:
    """Run ``systemctl [--user] <action> <unit>`` and return (success, message)."""
    proc = await asyncio.create_subprocess_exec(
        *_base_cmd(user), action, unit,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode == 0:
        return True, "ok"
    msg = stderr.decode().strip() or f"systemctl {action} exited with code {proc.returncode}"
    logger.warning("systemctl %s %s failed: %s", action, unit, msg)
    return False, msg


async def restart_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Restart a systemd unit.  Returns (success, message)."""
    return await _control_unit("restart", unit, user)


async def start_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Start a systemd unit.  Returns (success, message)."""
    return await _control_unit("start", unit, user)


async def stop_unit(unit: str, user: bool = False) -> tuple[bool, str]:
    """Stop a systemd unit.  Returns (success, message)."""
    return await _control_unit("stop", unit, user)
