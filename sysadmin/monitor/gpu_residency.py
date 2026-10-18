"""A service whose VRAM has been evicted to GTT, read from DRM fdinfo.

Estate message ``af170afe-54d0-4997-8a10-42267c6a2214`` (2026-10-18).
When another client oversubscribes the card — a game, or a HIP job —
the kernel moves a Vulkan resident's buffers from VRAM to GTT, which is
system memory reached over PCIe.  Nothing errors, the unit stays up and
``/health`` answers 200, and **nothing moves the buffers back**: on
2026-10-18 ``alfred-inference`` held 1.0 GiB of its 2.2 GiB in GTT from
the evening's Deadlock sessions until at least 21:53, hours after the
game ended.  Only a restart of the unit restores it.  The estate decided
(their Session 415, under their ADR-0189 §4) that its queue will not
publish a per-resident split, so the reading is this repository's: the
monitor is the thing that says a service is not doing its job.

This is ADR-0007's shape at a second term, and for the same reason.  "This
service's buffers are not where they were asked to live" is a
**predicate** over a reading the kernel already publishes per process, so
nothing opens it and nothing closes it: the unit's restart empties the
shortfall and the next poll recomputes it.  The owner is the check that
already writes the ``service_health`` row —
:meth:`~sysadmin.monitor.agent.SysAdminAgent._check_http_and_unit` — and
this module answers a question and writes nothing.

Four rules, three of them the opposite of the obvious implementation, each
settled against the live readings of 2026-10-18 21:53 BST:

1. **The shortfall is ``drm-total-vram`` less ``drm-resident-vram``, and
   ``total`` is the right operand here although it is the wrong one for a
   size.**  amdgpu counts ``total`` by the domain a buffer was *asked*
   for and ``resident`` by where it *is*; the estate's §2.5 rule "never
   ``drm-total-*``" is about sizing a resident, where ``total`` hides the
   eviction.  An eviction is precisely the difference between the two, so
   here it is the operand.  ``amd-requested-vram`` carries the same
   figure as ``drm-total-vram`` and is amdgpu's alone; the ``drm-*``
   keys are the DRM core's.  ``amd-evicted-vram`` is **not** the
   figure: it read **0 KiB** beside a 1.0 GiB shortfall, because a
   buffer allowed in VRAM *or* GTT is validated where it landed and is
   on no eviction list.  The live figures: ``alfred-inference`` total
   2,349,364 KiB, resident 1,301,044 KiB, shortfall 1,048,320 KiB;
   ``drm-resident-gtt`` less ``drm-total-gtt`` gives the identical
   1,048,320, which is the eviction seen from the other side.
2. **Resident may exceed total, so the shortfall is clamped at zero.**
   ``venture-chat`` read resident **8,448 KiB above** total at the same
   instant — the size of ``alfred-inference``'s ``drm-purgeable-vram`` —
   so a signed difference would report a negative eviction.
3. **Clients are deduplicated by ``drm-client-id``, and only the dGPU's
   count.**  Several file descriptors can share one client and each
   reports the client's whole figure, so summing every fd double-counts;
   and the iGPU's clients are a different card's memory.  The slot is
   ``llm.gpu_pci_slot``, the one :func:`~sysadmin.monitor.gpu.get_gpu_usage`
   and the LLM gate read.
4. **No client on the card is a reading, not a verdict.**
   ``venture-embed`` declares ``holds_vram`` and had **no** dGPU client
   at 21:53: it runs ``-ngl 0`` and its process is a boot start, which
   ADR-0007 §2.4 records as running CPU-only.  Whether a declared
   resident with nothing on the card is a fault is the 2026-08-06
   CPU-fallback question, which ``wait-for-dgpu`` answers at start-up
   and which this term does not take over: it records ``clients: 0``
   and leaves the status alone.  Every way of not knowing — no main
   PID, an unreadable ``/proc``, no slot configured — is likewise a
   recorded reading that leaves the status alone, ``gpu_context`` rule 5.

The floor is :data:`EVICTION_FLOOR_KIB`.  The live population has one
member either side of it — 0 KiB clamped and 1,048,320 KiB — and none in
between, so the floor is a judgement about what is worth a restart, not a
measured separation.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DETAIL_KEY",
    "EVICTED_STATUS",
    "EVICTION_FLOOR_KIB",
    "Residency",
    "read_residency",
    "reading",
    "unreadable_reading",
]

#: Where the reading lands in ``service_health.details``, one key holding
#: a mapping, as :data:`~sysadmin.monitor.gpu_context.DETAIL_KEY` does.
DETAIL_KEY = "gpu_residency"

#: The reading recorded for a service past :data:`EVICTION_FLOOR_KIB`.
#: ``degraded`` for ``gpu_context``'s reasons: the check looked, the
#: service answers, and it cannot do its job as it should.
EVICTED_STATUS = "degraded"

#: Below this, a shortfall is recorded and the status left alone.
#: 128 MiB is under ``alfred-inference``'s KV buffer (144 MiB), the
#: smallest of the three buffers the estate's §2.5 lists for it.
EVICTION_FLOOR_KIB = 128 * 1024

_PROC = Path("/proc")


@dataclass(frozen=True)
class Residency:
    """A process's memory on one card, summed over its distinct clients."""

    clients: int
    total_vram_kib: int
    resident_vram_kib: int
    total_gtt_kib: int
    resident_gtt_kib: int

    @property
    def evicted_kib(self) -> int:
        """VRAM asked for and not resident there; rule 2's clamp."""
        return max(0, self.total_vram_kib - self.resident_vram_kib)


def _kib(value: str) -> int:
    """``'1301044 KiB'`` → 1301044.  A bare number is bytes, as ``0`` is."""
    number, _, unit = value.strip().partition(" ")
    scale = {"": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3}[unit.strip()]
    return int(number) * scale // 1024


def read_residency(pid: int, pci_slot: str, proc: Path = _PROC) -> Residency:
    """Sum ``pid``'s distinct DRM clients on ``pci_slot``.

    Raises:
        OSError: the process's ``fdinfo`` directory could not be listed —
            it has exited, or is not this uid's.  A single fd vanishing
            mid-read is skipped, since the descriptor table moves.
    """
    clients: dict[str, dict[str, str]] = {}
    fdinfo = proc / str(pid) / "fdinfo"
    for fd in os.listdir(fdinfo):
        try:
            text = (fdinfo / fd).read_text()
        except OSError:
            continue
        fields = {}
        for line in text.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                fields[key.strip()] = value.strip()
        client = fields.get("drm-client-id")
        if client is None or fields.get("drm-pdev") != pci_slot:
            continue
        clients[client] = fields

    def total(key: str) -> int:
        return sum(_kib(f.get(key, "0")) for f in clients.values())

    return Residency(
        clients=len(clients),
        total_vram_kib=total("drm-total-vram"),
        resident_vram_kib=total("drm-resident-vram"),
        total_gtt_kib=total("drm-total-gtt"),
        resident_gtt_kib=total("drm-resident-gtt"),
    )


def unreadable_reading(unit: str, why: str) -> dict:
    """The term did not run; the caller's status stands (rule 4)."""
    return {DETAIL_KEY: {"unit": unit, "evaluated": False, "reason": why}}


def reading(unit: str, pid: int, residency: Residency) -> dict:
    """The whole derivation, so a stored row explains its own verdict."""
    return {
        DETAIL_KEY: {
            "unit": unit,
            "evaluated": True,
            "pid": pid,
            "clients": residency.clients,
            "total_vram_kib": residency.total_vram_kib,
            "resident_vram_kib": residency.resident_vram_kib,
            "total_gtt_kib": residency.total_gtt_kib,
            "resident_gtt_kib": residency.resident_gtt_kib,
            "evicted_kib": residency.evicted_kib,
            "evicted": residency.evicted_kib >= EVICTION_FLOOR_KIB,
        }
    }
