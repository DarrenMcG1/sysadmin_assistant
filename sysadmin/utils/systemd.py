"""Systemd unit status helpers via subprocess."""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def is_active(unit: str) -> bool:
    """Check if a systemd unit is active."""
    proc = await asyncio.create_subprocess_exec(
        "systemctl", "is-active", unit,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return stdout.decode().strip() == "active"


async def get_unit_status(unit: str) -> dict:
    """Get detailed status of a systemd unit."""
    props = [
        "ActiveState", "SubState", "MainPID",
        "MemoryCurrent", "CPUUsageNSec", "LoadState",
    ]
    prop_args = ",".join(props)

    proc = await asyncio.create_subprocess_exec(
        "systemctl", "show", unit, f"--property={prop_args}",
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
