"""AMD GPU monitoring via rocm-smi with sysfs fallback.

Collects GPU utilisation, temperature, VRAM usage, and power draw.
Designed for AMD GPUs (RDNA/CDNA) — not applicable to NVIDIA hardware.

**The utilisation figure is read from the counter, never from the tool**
(`SNAG-GPU-004`, 2026-09-22).  ``rocm-smi``'s ``GPU use (%)`` is not
wrong in itself — a single ``--showuse`` agrees with sysfs to sampling
noise — but *this module's invocation of it* perturbs the quantity it
measures: the sensor queries are themselves GPU work and they land
inside the window the figure is averaged over.  Measured three ways,
same card, same minute, n=30 each: sysfs ``gpu_busy_percent`` sd **0.7**,
one bare ``rocm-smi --showuse`` sd **0.8**, this collector sd **9.3**,
the last reading exactly 0 twice while the card held 10.5 GB at ~100 W.
So ``gpu_percent`` for the dGPU comes from :func:`estate.gpu.sample_gpu_busy`
— one file open, no subprocess — and ``rocm-smi`` is kept for what it
alone supplies: product name, temperature, VRAM and power.

Five rules, four of them the opposite of the obvious implementation:

1. **The counter is sampled *before* the subprocesses, not after.**  The
   defect is the perturbation rather than the tool, so a sysfs read
   taken after the spawn inherits it: bracketing one ``rocm-smi`` call
   with a read either side gave sd **0.2** before and sd **3.1** ~55 ms
   after, off the same file.  Ordering is the fix; the source is only
   half of it.
2. **The dGPU is resolved by PCI slot, and the slot is asked of the
   payload rather than of an index** (`SNAG-GPU-005`).  ``rocm-smi``
   and DRM enumerate the cards in **opposite** order on this box —
   ``rocm-smi``'s ``card0`` is the RX 7900 XTX at ``0000:03:00.0`` while
   DRM's ``card0`` is the iGPU at ``0000:47:00.0`` — so the key ``card0``
   names a different physical device depending on which path produced
   the row.  ``--showbus`` rides in the existing invocation at no extra
   subprocess and every row carries its ``pci_slot``, on both paths.
   :mod:`estate.gpu`'s opening rule, which that module states and this
   one did not obey.
3. **Every row says where its figure came from.**  ``gpu_percent_source``
   is ``"sysfs"`` or ``"rocm-smi"``, because a perturbed reading and a
   clean one are the same integer in the same field and only the source
   separates them — `SNAG-API-004`'s lesson, and the property whose
   absence let `SNAG-GPU-003` recruit this figure into a cross-repo
   finding against a sampler that was right.  The iGPU keeps
   ``rocm-smi``'s value and says so: :func:`estate.gpu.sample_gpu_busy`
   answers for one slot, and the mixed payload is legible rather than
   silent.
4. **An unresolvable slot falls back to ``rocm-smi``, it does not blank
   the figure.**  Nothing judges ``gpu_percent`` — no threshold reads it
   — so there is no alert to fail open or closed, and a labelled
   imperfect figure is strictly more than none for the human and the
   briefing that do read it.  An empty ``gpu_pci_slot`` disables the
   LLM gate by :mod:`estate.gpu`'s convention; here it means only that
   the dGPU cannot be told from the iGPU.
5. **A runtime-suspended card reads 0, and the row says the power
   manager answered rather than the counter** (estate-manager ADR-0227,
   their message ``81c4070e``, 2026-10-01).  A card in runtime suspend
   has nothing running on it, and its driver refuses the counter rather
   than wake it.  Before that ADR the refusal came back as ``None`` and
   this collector fell back to ``rocm-smi`` — whose own queries woke the
   card it was measuring.  Over the 9.5 h both monitors were off on
   2026-09-27/28 that fallback wrote **92** dGPU rows: 75 read 0 and 17
   read 1–15 % at a mean of 16 W, every one of them the tool reporting a
   card it had just roused.  The 0 is the truer figure, so it is taken —
   but it was not read off ``gpu_busy_percent``, and rule 3 is that the
   row says which instrument answered.  So ``power/runtime_status`` is
   asked **here**, first (reading it never wakes the device, so rule 1's
   ordering holds), and a suspended card is labelled
   ``runtime-pm``.  The library asks the same attribute again after a
   refused read, in case the card suspended in between; a 0 from that
   second check is labelled ``sysfs``.  That residue is a window of one
   file read, and its figure is right either way — only the label errs.
"""

import asyncio
import json
import logging
from pathlib import Path

from estate.gpu import DGPU_PCI_SLOT, runtime_status, sample_gpu_busy

logger = logging.getLogger(__name__)

_ROCM_SMI = "/opt/rocm/bin/rocm-smi"

#: Where a row's ``gpu_percent`` was read.  ``sysfs`` is the counter the
#: estate's GPU gate reads; ``rocm-smi`` is the perturbed reading rule 1
#: exists to avoid, kept only where the slot cannot be resolved.
SOURCE_SYSFS = "sysfs"
SOURCE_ROCM_SMI = "rocm-smi"
#: A runtime-suspended card (rule 5): the figure is 0 because the PM
#: core says nothing is running, not because a counter read 0.
SOURCE_RUNTIME_PM = "runtime-pm"

#: ``power/runtime_status``'s word for a card in runtime suspend.
SUSPENDED = "suspended"

#: The metrics invocation, named so the live premise test can ask the
#: tool what *this* invocation replies with rather than restating the
#: flags beside it — two statements of one argument list can disagree,
#: and the one that would go quiet is the ``--showbus`` the slot match
#: is made on.
METRICS_ARGS = (
    "--showuse", "--showtemp", "--showmeminfo", "vram",
    "--showpower", "--showbus", "--json",
)

#: The bus key ``--showbus`` publishes, and the key rule 2 matches on.
PCI_BUS_KEY = "PCI Bus"


async def get_gpu_usage(dgpu_pci_slot: str = DGPU_PCI_SLOT) -> dict[str, dict]:
    """Return per-GPU metrics dict keyed by card name.

    Tries rocm-smi first for richer data; falls back to sysfs if unavailable.
    Returns empty dict if no AMD GPU is detected.

    ``dgpu_pci_slot`` is the caller's — :class:`SysAdminAgent` passes
    ``config.llm.gpu_pci_slot``, so the collector and the LLM gate read
    **one** counter on **one** device and cannot come to disagree about
    how busy the card is.  The default is the estate's constant rather
    than a literal, so it is the same object the config field defaults
    to and not a second statement of it.

    Example return::

        {
            "card0": {
                "name": "AMD Radeon RX 7900 XTX",
                "pci_slot": "0000:03:00.0",
                "gpu_percent": 13,
                "gpu_percent_source": "sysfs",
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
            return await _from_rocm_smi(dgpu_pci_slot)
        except Exception:
            logger.debug("rocm-smi failed, falling back to sysfs", exc_info=True)

    return _from_sysfs()


async def _from_rocm_smi(dgpu_pci_slot: str = DGPU_PCI_SLOT) -> dict[str, dict]:
    """Parse rocm-smi JSON output for GPU metrics, utilisation from sysfs.

    The counter is read **first**, on this thread: it is one
    ``read_text`` of a sysfs file, so it needs no ``to_thread`` (that
    applies to :func:`estate.gpu.sustained_busy`, which sleeps through a
    2 s window).  Reading it after the spawn would inherit the
    perturbation the module docstring's rule 1 records.
    """
    # Rule 1: before the subprocesses, which are themselves GPU work.
    # Rule 5: the PM core first, because asking it never wakes the card.
    dgpu_busy: int | None = None
    dgpu_source = SOURCE_SYSFS
    if dgpu_pci_slot:
        if runtime_status(dgpu_pci_slot) == SUSPENDED:
            dgpu_busy, dgpu_source = 0, SOURCE_RUNTIME_PM
        else:
            dgpu_busy = sample_gpu_busy(dgpu_pci_slot)

    metrics_proc = await asyncio.create_subprocess_exec(
        _ROCM_SMI, *METRICS_ARGS,
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

        pci_slot = data.get(PCI_BUS_KEY)

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

        # Rules 2-4: the counter for the card it answers for, the tool
        # for the rest, and the row says which it was.
        gpu_percent: int | None
        if dgpu_busy is not None and pci_slot == dgpu_pci_slot:
            gpu_percent = dgpu_busy
            gpu_percent_source = dgpu_source
        else:
            gpu_percent = _parse_int(data.get("GPU use (%)"))
            gpu_percent_source = SOURCE_ROCM_SMI

        result[card_id] = {
            "name": card_name,
            "pci_slot": pci_slot,
            "gpu_percent": gpu_percent,
            "gpu_percent_source": gpu_percent_source,
            "temp_c": temp_c,
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "vram_percent": round(vram_used / vram_total * 100, 1) if vram_total else 0,
            "power_w": power_w,
        }

    return result


def _from_sysfs() -> dict[str, dict]:
    """Read GPU metrics from sysfs (no external tools needed).

    Keyed on the **DRM** index, which is not ``rocm-smi``'s: on this box
    they are the opposite way round (rule 2).  The key is left as it is
    because it is a stored shape with live consumers; what is added is
    ``pci_slot``, so a reader can tell the two vocabularies apart rather
    than having to know which path wrote the row.  Utilisation here was
    always the counter, and now says so — except on a runtime-suspended
    card, which reads 0 and says ``runtime-pm`` (rule 5), where the
    direct read would otherwise be refused and stored as ``None``.
    """
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
        pci_slot = _pci_slot_of(device)

        gpu_percent: int | None
        if pci_slot and runtime_status(pci_slot) == SUSPENDED:
            gpu_percent, gpu_percent_source = 0, SOURCE_RUNTIME_PM
        else:
            gpu_percent, gpu_percent_source = _read_int(gpu_busy), SOURCE_SYSFS
        temp_c = _read_temp(device)
        vram_total = _read_int(device / "mem_info_vram_total") or 0
        vram_used = _read_int(device / "mem_info_vram_used") or 0
        vram_total_mb = round(vram_total / (1024 ** 2)) if vram_total else 0
        vram_used_mb = round(vram_used / (1024 ** 2)) if vram_used else 0
        power_w = _read_power(device)

        result[card_id] = {
            "name": card_id,
            "pci_slot": pci_slot,
            "gpu_percent": gpu_percent,
            "gpu_percent_source": gpu_percent_source,
            "temp_c": temp_c,
            "vram_used_mb": vram_used_mb,
            "vram_total_mb": vram_total_mb,
            "vram_percent": round(vram_used / vram_total * 100, 1) if vram_total else 0,
            "power_w": power_w,
        }

    return result


# --- Parsing helpers ---


def _pci_slot_of(device: Path) -> str | None:
    """The PCI slot behind ``/sys/class/drm/cardN/device``, or None.

    That path is a symlink into ``/sys/devices/…``, whose final
    component is the slot.  ``None`` rather than a guess when it cannot
    be resolved: a row that does not know which device it describes must
    not read like one that does.
    """
    try:
        return device.resolve(strict=True).name
    except OSError:
        return None


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
