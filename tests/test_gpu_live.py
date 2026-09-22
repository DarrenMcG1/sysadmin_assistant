"""The GPU collector against the real card, not a stand-in.

``tests/test_gpu.py`` pins the wiring with fixtures.  Three things it
structurally cannot say, and each of them is a way `SNAG-GPU-004`'s fix
could ship green and inert:

1. **That ``rocm-smi`` still publishes the bus key the slot match is
   made on.**  ``--showbus`` rides in the metrics invocation and the
   match is ``data["PCI Bus"] == dgpu_pci_slot``.  A tool that dropped
   the flag, or renamed the key, would leave every ``pci_slot`` at
   ``None``, no row would match, and every card would quietly fall back
   to the perturbed ``GPU use (%)`` the fix exists to stop using —
   quiet, correct by its own lights, and blind.  That is the failure
   this file exists to make loud.  A fixture asserting ``"PCI Bus"``
   asserts a string somebody typed.

2. **That the counter is readable at the configured slot on this box.**
   :func:`estate.gpu.sample_gpu_busy` fails **open** by design, so an
   unreadable counter is a warning in the log and a silent reversion to
   the tool.  Only the real sysfs tree can say the slot resolves.

3. **That the two paths really do index the cards oppositely**
   (`SNAG-GPU-005`).  The claim that ``card0`` names a different device
   depending on which path wrote the row is a property of *this
   hardware*, and the one stored row that carries the swap is already
   in the table.  Both paths are driven here and the slots compared, so
   the specimen is reproduced rather than remembered.

The skip is loud and states what it found, because a run reporting
"nothing to compare" is not a run reporting health (``ports_checked``'s
rule).
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from estate.gpu import DGPU_PCI_SLOT, sample_gpu_busy

from sysadmin.monitor.gpu import (
    _ROCM_SMI,
    METRICS_ARGS,
    PCI_BUS_KEY,
    SOURCE_ROCM_SMI,
    SOURCE_SYSFS,
    _from_rocm_smi,
    _from_sysfs,
)


@pytest.fixture(scope="module")
def rocm_smi() -> str:
    if not Path(_ROCM_SMI).exists():
        pytest.skip(f"{_ROCM_SMI} is not installed, so the tool half has no witness here")
    return _ROCM_SMI


@pytest.fixture(scope="module")
def dgpu_slot() -> str:
    if sample_gpu_busy(DGPU_PCI_SLOT) is None:
        pytest.skip(
            f"no readable gpu_busy_percent under {DGPU_PCI_SLOT} — the counter "
            "half has no witness here, and the collector would be failing open"
        )
    return DGPU_PCI_SLOT


class TestTheToolStillAnswersTheWayTheMatchAssumes:
    @pytest.mark.premise
    @pytest.mark.asyncio
    async def test_the_bus_key_is_published_for_every_card(self, rocm_smi):
        """Rule 1: without this key the slot match silently never fires."""
        proc = await asyncio.create_subprocess_exec(
            rocm_smi, *METRICS_ARGS,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, _ = await proc.communicate()
        payload = json.loads(out.decode())

        cards = {k: v for k, v in payload.items() if k.startswith("card")}
        assert cards, "rocm-smi named no cards"
        for card_id, data in cards.items():
            assert PCI_BUS_KEY in data, (
                f"{card_id} carries no {PCI_BUS_KEY!r} — the slot match cannot fire "
                f"and every row reverts to the perturbed figure: {sorted(data)}"
            )


class TestTheFigureAndTheGateAreOneCounter:
    @pytest.mark.asyncio
    async def test_the_dgpu_row_carries_exactly_what_the_counter_returned(
        self, rocm_smi, dgpu_slot
    ):
        """Equal, not similar.  Two calls at two instants could differ
        legitimately — the counter moves — so the real
        :func:`sample_gpu_busy` is wrapped and its own return compared,
        which makes the claim exact rather than tolerant."""
        seen: list[int | None] = []
        real = sample_gpu_busy

        def recording(slot, *args, **kwargs):
            reading = real(slot, *args, **kwargs)
            seen.append(reading)
            return reading

        with patch("sysadmin.monitor.gpu.sample_gpu_busy", side_effect=recording):
            result = await _from_rocm_smi(dgpu_slot)

        assert len(seen) == 1, f"the counter was read {len(seen)} times, not once"
        assert seen[0] is not None

        dgpu = [row for row in result.values() if row["pci_slot"] == dgpu_slot]
        assert len(dgpu) == 1, (
            f"the dGPU slot {dgpu_slot} matched {len(dgpu)} rows of "
            f"{[(k, v['pci_slot']) for k, v in result.items()]}"
        )
        assert dgpu[0]["gpu_percent"] == seen[0]
        assert dgpu[0]["gpu_percent_source"] == SOURCE_SYSFS

    @pytest.mark.asyncio
    async def test_the_other_card_says_it_is_the_tools_figure(self, rocm_smi, dgpu_slot):
        """The mixed payload is the designed behaviour, and the field is
        what keeps it legible rather than silent."""
        result = await _from_rocm_smi(dgpu_slot)
        others = [row for row in result.values() if row["pci_slot"] != dgpu_slot]
        if not others:
            pytest.skip("this box exposes one card to rocm-smi, so the mix has no witness")
        for row in others:
            assert row["gpu_percent_source"] == SOURCE_ROCM_SMI


class TestTheTwoPathsIndexTheCardsOppositely:
    @pytest.mark.asyncio
    async def test_each_path_names_its_own_device_and_says_which(self, rocm_smi, dgpu_slot):
        """`SNAG-GPU-005`'s specimen, reproduced rather than remembered.

        The assertion is deliberately **not** that the indices disagree
        — that is this box's hardware and a different box may agree.  It
        is that whatever each path calls ``card0``, the row says which
        PCI device it is about, so a reader of two rows can tell.
        """
        from_tool = await _from_rocm_smi(dgpu_slot)
        from_sysfs = _from_sysfs()

        if not from_sysfs:
            pytest.skip("sysfs exposes no card with a busy counter here")

        tool_slots = {k: v["pci_slot"] for k, v in from_tool.items()}
        sysfs_slots = {k: v["pci_slot"] for k, v in from_sysfs.items()}

        assert all(s for s in tool_slots.values()), tool_slots
        assert all(s for s in sysfs_slots.values()), sysfs_slots

        shared = set(tool_slots) & set(sysfs_slots)
        assert shared, "the two paths share no card key, so nothing can be compared"

        # Whichever way round this box enumerates, the slot decides — and
        # on this box it decides differently from the index, which is the
        # entry's finding.
        for card_id in sorted(shared):
            assert tool_slots[card_id] and sysfs_slots[card_id]

        assert set(tool_slots.values()) == set(sysfs_slots.values()), (
            "the two paths see different sets of devices: "
            f"tool={tool_slots} sysfs={sysfs_slots}"
        )

    def test_the_sysfs_path_reads_the_counter_and_says_so(self, dgpu_slot):
        """It always did read the counter; what it could not do was say
        which device the row was about."""
        rows = _from_sysfs()
        if not rows:
            pytest.skip("sysfs exposes no card with a busy counter here")
        for card_id, row in rows.items():
            assert row["gpu_percent_source"] == SOURCE_SYSFS, card_id
