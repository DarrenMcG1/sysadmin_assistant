"""AMD GPU monitoring via rocm-smi with sysfs fallback.

Collects GPU utilisation, temperature, VRAM usage, and power draw.
Designed for AMD GPUs (RDNA/CDNA) — not applicable to NVIDIA hardware.
"""

import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_ROCM_SMI = "/opt/rocm/bin/rocm-smi"


async def get_gpu_usage() -> dict[str, dict]:
    """Return per-GPU metrics dict keyed by card name.

    Tries rocm-smi first for richer data; falls back to sysfs if unavailable.
    Returns empty dict if no AMD GPU is detected.

    Example return::

        {
            "card0": {
                "name": "AMD Radeon RX 7900 XTX",
                "gpu_percent": 18,
                "temp_c": 65.0,
                "vram_used_mb": 3317,
                "vram_total_mb": 24556,
                "vram_percent": 13.5,
                "power_w": 87.0,
            }
        }
    """
    if Path(_ROCM_SMI).exists():
        try:
            return await _from_rocm_smi()
        except Exception:
            logger.debug("rocm-smi failed, falling back to sysfs", exc_info=True)

    return _from_sysfs()


async def _from_rocm_smi() -> dict[str, dict]:
    """Parse rocm-smi JSON output for GPU metrics."""
    metrics_proc = await asyncio.create_subprocess_exec(
        _ROCM_SMI, "--showuse", "--showtemp", "--showmeminfo", "vram",
        "--showpower", "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    names_proc = await asyncio.create_subprocess_exec(
        _ROCM_SMI, "--showproductname", "--json",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    metrics_out, _ = await metrics_proc.communicate()
    names_out, _ = await names_proc.communicate()

    metrics = json.loads(metrics_out.decode())
    names = json.loads(names_out.decode())

    result = {}
    for card_id, data in metrics.items():
        if not card_id.startswith("card"):
            continue

        name_info = names.get(card_id, {})
        card_name = name_info.get("Card Series", card_id)

        vram_total = int(data.get("VRAM Total Memory (B)", 0))
        vram_used = int(data.get("VRAM Total Used Memory (B)", 0))
        vram_total_mb = round(vram_total / (1024 ** 2))
        vram_used_mb = round(vram_used / (1024 ** 2))

        # Temperature — prefer edge sensor
        temp_c = _parse_float(
            data.get("Temperature (Sensor edge) (C)")
            or data.get("Temperature (Sensor junction) (C)")
        )

        # Power — field name varies between GPU generations
        power_w = _parse_float(
            data.get("Average Graphics Package Power (W)")
            or data.get("Current Socket Graphics Package Power (W)")
        )

        result[card_id] = {
            "name": card_name,
            "gpu_percent": _parse_int(data.get("GPU use (%)")),
            "temp_c": temp_c,
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "vram_percent": round(vram_used / vram_total * 100, 1) if vram_total else 0,
            "power_w": power_w,
        }

    return result


def _from_sysfs() -> dict[str, dict]:
    """Read GPU metrics from sysfs (no external tools needed)."""
    drm = Path("/sys/class/drm")
    if not drm.exists():
        return {}

    result = {}
    for card_dir in sorted(drm.glob("card[0-9]*")):
        device = card_dir / "device"
        gpu_busy = device / "gpu_busy_percent"
        if not gpu_busy.exists():
            continue

        card_id = card_dir.name

        gpu_percent = _read_int(gpu_busy)
        temp_c = _read_temp(device)
        vram_total = _read_int(device / "mem_info_vram_total") or 0
        vram_used = _read_int(device / "mem_info_vram_used") or 0
        vram_total_mb = round(vram_total / (1024 ** 2)) if vram_total else 0
        vram_used_mb = round(vram_used / (1024 ** 2)) if vram_used else 0
        power_w = _read_power(device)

        result[card_id] = {
            "name": card_id,
            "gpu_percent": gpu_percent,
            "temp_c": temp_c,
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "vram_percent": round(vram_used / vram_total * 100, 1) if vram_total else 0,
            "power_w": power_w,
        }

    return result


# --- Parsing helpers ---


def _parse_float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _parse_int(val: str | None) -> int | None:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _read_int(path: Path) -> int | None:
    try:
        return int(path.read_text().strip())
    except (FileNotFoundError, ValueError, PermissionError):
        return None


def _read_temp(device: Path) -> float | None:
    """Read temperature from hwmon (millidegrees → degrees C)."""
    for hwmon in sorted(device.glob("hwmon/hwmon*")):
        temp_file = hwmon / "temp1_input"
        if temp_file.exists():
            val = _read_int(temp_file)
            if val is not None:
                return round(val / 1000, 1)
    return None


def _read_power(device: Path) -> float | None:
    """Read power from hwmon (microwatts → watts)."""
    for hwmon in sorted(device.glob("hwmon/hwmon*")):
        power_file = hwmon / "power1_average"
        if power_file.exists():
            val = _read_int(power_file)
            if val is not None:
                return round(val / 1_000_000, 1)
    return None
