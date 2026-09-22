"""Tests for AMD GPU monitoring utility and threshold alerting.

**The utilisation figure's *source* is what these tests pin, and it is
what no test of this module pinned before** (`SNAG-GPU-004`).  Every
assertion here used to be a *value*, and a value was never wrong: over
the estate's own coverage the collector's mean was 40.6 against their
38–40, so a mean-comparison passes against the defect and did for the
life of the module.  What was wrong was the spread, and its cause was
the invocation — so the stub below deliberately returns a number the
rocm-smi fixture does **not** carry.  A stub returning the fixture's own
``18`` would pass against the unfixed code, which is the trap of pinning
a stub by value rather than by identity.

``tests/test_gpu_live.py`` holds the half a fixture cannot state: that
the collector and the estate's GPU gate come back with one number off
one file, on the real card.
"""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sysadmin.core.config import Thresholds
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.gpu import (
    SOURCE_ROCM_SMI,
    SOURCE_SYSFS,
    _parse_float,
    _parse_int,
    _pci_slot_of,
    get_gpu_usage,
)
from sysadmin.monitor.models.resource_snapshot import ResourceSnapshot

# ---------------------------------------------------------------------------
# Sample rocm-smi JSON data
# ---------------------------------------------------------------------------

#: The slots this box actually carries, and they are the opposite way
#: round from DRM's (`SNAG-GPU-005`): rocm-smi's ``card0`` is the dGPU.
DGPU_SLOT = "0000:03:00.0"
IGPU_SLOT = "0000:47:00.0"

#: Deliberately unequal to either card's ``GPU use (%)`` below, so a row
#: carrying it can only have got it from the counter.
COUNTER_READING = 7

SAMPLE_METRICS = json.dumps({
    "card0": {
        "Temperature (Sensor edge) (C)": "65.0",
        "Temperature (Sensor junction) (C)": "74.0",
        "Temperature (Sensor memory) (C)": "74.0",
        "Average Graphics Package Power (W)": "87.0",
        "GPU use (%)": "18",
        "PCI Bus": DGPU_SLOT,
        "VRAM Total Memory (B)": "25753026560",
        "VRAM Total Used Memory (B)": "3478065152",
    },
    "card1": {
        "Temperature (Sensor edge) (C)": "50.0",
        "Current Socket Graphics Package Power (W)": "0.014",
        "GPU use (%)": "0",
        "PCI Bus": IGPU_SLOT,
        "VRAM Total Memory (B)": "2147483648",
        "VRAM Total Used Memory (B)": "26124288",
    },
})

SAMPLE_NAMES = json.dumps({
    "card0": {"Card Series": "AMD Radeon RX 7900 XTX"},
    "card1": {"Card Series": "AMD Ryzen 9 9950X3D"},
})


async def _drive(
    *,
    counter: int | None = COUNTER_READING,
    slot: str = DGPU_SLOT,
    log: list | None = None,
) -> dict[str, dict]:
    """Run the collector with stubbed subprocesses and a stubbed counter.

    ``log``, when given, records the order of the two kinds of read, so
    a caller can assert the counter was sampled before anything was
    spawned — which is half the fix and is invisible to any assertion
    about the returned value.
    """
    async def mock_communicate():
        return (SAMPLE_METRICS.encode(), b"")

    async def mock_names_communicate():
        return (SAMPLE_NAMES.encode(), b"")

    def fake_sample(pci_slot, *args, **kwargs):
        if log is not None:
            log.append(("sample", pci_slot))
        return counter

    def fake_exec(*args, **kwargs):
        if log is not None:
            log.append(("spawn", args[1] if len(args) > 1 else None))
        return fake_exec.procs.pop(0)

    metrics_proc = AsyncMock()
    metrics_proc.communicate = mock_communicate
    names_proc = AsyncMock()
    names_proc.communicate = mock_names_communicate
    fake_exec.procs = [metrics_proc, names_proc]

    with patch("sysadmin.monitor.gpu.Path") as mock_path:
        mock_path.return_value.exists.return_value = True
        with patch("sysadmin.monitor.gpu.sample_gpu_busy", side_effect=fake_sample):
            with patch(
                "sysadmin.monitor.gpu.asyncio.create_subprocess_exec",
                side_effect=fake_exec,
            ):
                return await get_gpu_usage(slot)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


class TestParseHelpers:
    def test_parse_float_valid(self):
        assert _parse_float("65.0") == 65.0

    def test_parse_float_none(self):
        assert _parse_float(None) is None

    def test_parse_float_invalid(self):
        assert _parse_float("N/A") is None

    def test_parse_int_valid(self):
        assert _parse_int("18") == 18

    def test_parse_int_none(self):
        assert _parse_int(None) is None


# ---------------------------------------------------------------------------
# rocm-smi parsing
# ---------------------------------------------------------------------------


class TestRocmSmiParsing:
    @pytest.mark.asyncio
    async def test_parses_two_cards(self):
        result = await _drive()
        assert "card0" in result
        assert "card1" in result

    @pytest.mark.asyncio
    async def test_card0_fields(self):
        """rocm-smi still supplies everything except the utilisation."""
        card0 = (await _drive())["card0"]
        assert card0["name"] == "AMD Radeon RX 7900 XTX"
        assert card0["temp_c"] == 65.0
        assert card0["power_w"] == 87.0
        assert card0["vram_total_mb"] == round(25753026560 / 1024**2)
        assert card0["vram_used_mb"] == round(3478065152 / 1024**2)
        assert card0["vram_percent"] > 0

    @pytest.mark.asyncio
    async def test_fallback_power_field(self):
        """card1 uses 'Current Socket Graphics Package Power' instead of 'Average'."""
        result = await _drive()
        assert result["card1"]["power_w"] == 0.014

    @pytest.mark.asyncio
    async def test_rocm_smi_failure_falls_back_to_sysfs(self):
        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True

            with patch("sysadmin.monitor.gpu._from_rocm_smi", side_effect=Exception("boom")):
                with patch(
                    "sysadmin.monitor.gpu._from_sysfs",
                    return_value={"card0": {"name": "sysfs"}},
                ) as mock_sysfs:
                    result = await get_gpu_usage()

        assert result == {"card0": {"name": "sysfs"}}
        mock_sysfs.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_rocm_smi_uses_sysfs(self):
        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            with patch("sysadmin.monitor.gpu._from_sysfs", return_value={}) as mock_sysfs:
                result = await get_gpu_usage()

        assert result == {}
        mock_sysfs.assert_called_once()


# ---------------------------------------------------------------------------
# Where the utilisation figure came from (SNAG-GPU-004)
# ---------------------------------------------------------------------------


class TestUtilisationProvenance:
    @pytest.mark.asyncio
    async def test_the_dgpu_figure_is_the_counter_and_not_the_tool(self):
        """The fixture says 18; the counter says 7; the row must say 7.

        This is the assertion the module lacked.  Every other test here
        passes against the perturbed reading, because the perturbed
        reading is still an integer in the right field.
        """
        card0 = (await _drive())["card0"]
        assert card0["gpu_percent"] == COUNTER_READING
        assert card0["gpu_percent_source"] == SOURCE_SYSFS

    @pytest.mark.asyncio
    async def test_the_igpu_keeps_the_tools_figure_and_says_which(self):
        """``sample_gpu_busy`` answers for one slot, so the other card is
        still the tool's — and the mixed payload is legible rather than
        silent, which is the whole point of the source field."""
        card1 = (await _drive())["card1"]
        assert card1["gpu_percent"] == 0
        assert card1["gpu_percent_source"] == SOURCE_ROCM_SMI

    @pytest.mark.asyncio
    async def test_the_counter_is_sampled_before_anything_is_spawned(self):
        """Ordering is half the fix: a read taken after the spawn
        inherits the perturbation it exists to avoid (sd 0.2 before
        against 3.1 after, measured off the same file)."""
        log: list = []
        await _drive(log=log)
        assert log[0][0] == "sample", f"counter was not read first: {log}"
        assert [kind for kind, _ in log].count("spawn") == 2

    @pytest.mark.asyncio
    async def test_the_counter_is_asked_for_the_slot_the_caller_passed(self):
        """The caller's slot, not the module's default — otherwise a
        ``config.yaml`` override reaches the gate and not the collector,
        and the two instruments part company again."""
        log: list = []
        await _drive(slot=IGPU_SLOT, log=log)
        assert ("sample", IGPU_SLOT) in log

    @pytest.mark.asyncio
    async def test_an_unreadable_counter_falls_back_to_the_tool(self):
        """Nothing judges this figure, so there is no alert to fail open
        or closed; a labelled imperfect number beats no number."""
        card0 = (await _drive(counter=None))["card0"]
        assert card0["gpu_percent"] == 18
        assert card0["gpu_percent_source"] == SOURCE_ROCM_SMI

    @pytest.mark.asyncio
    async def test_an_empty_slot_never_touches_the_counter(self):
        """An empty slot disables the estate's gate; here it means only
        that the dGPU cannot be told from the iGPU."""
        log: list = []
        result = await _drive(slot="", log=log)
        assert [kind for kind, _ in log].count("sample") == 0
        assert result["card0"]["gpu_percent_source"] == SOURCE_ROCM_SMI

    @pytest.mark.asyncio
    async def test_every_row_carries_the_slot_it_describes(self):
        """`SNAG-GPU-005`: the ``cardN`` key is a vocabulary, not an
        identity, and the row has to say which device it is about."""
        result = await _drive()
        assert result["card0"]["pci_slot"] == DGPU_SLOT
        assert result["card1"]["pci_slot"] == IGPU_SLOT

    @pytest.mark.asyncio
    async def test_the_slot_is_asked_of_the_payload_not_of_the_index(self):
        """Matching on ``card0`` would work on this box by luck and name
        the iGPU on a box that enumerates the other way."""
        swapped = json.loads(SAMPLE_METRICS)
        swapped["card0"]["PCI Bus"] = IGPU_SLOT
        swapped["card1"]["PCI Bus"] = DGPU_SLOT

        with patch("sysadmin.monitor.gpu.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            with patch(
                "sysadmin.monitor.gpu.sample_gpu_busy", return_value=COUNTER_READING
            ):
                async def metrics_comm():
                    return (json.dumps(swapped).encode(), b"")

                async def names_comm():
                    return (SAMPLE_NAMES.encode(), b"")

                metrics_proc = AsyncMock()
                metrics_proc.communicate = metrics_comm
                names_proc = AsyncMock()
                names_proc.communicate = names_comm
                with patch(
                    "sysadmin.monitor.gpu.asyncio.create_subprocess_exec",
                    side_effect=[metrics_proc, names_proc],
                ):
                    result = await get_gpu_usage(DGPU_SLOT)

        assert result["card1"]["gpu_percent"] == COUNTER_READING
        assert result["card1"]["gpu_percent_source"] == SOURCE_SYSFS
        assert result["card0"]["gpu_percent_source"] == SOURCE_ROCM_SMI


class TestSysfsSlotResolution:
    def test_it_resolves_the_symlink_to_the_slot(self, tmp_path):
        slot_dir = tmp_path / "0000:03:00.0"
        slot_dir.mkdir()
        device = tmp_path / "card1" / "device"
        device.parent.mkdir()
        device.symlink_to(slot_dir)
        assert _pci_slot_of(device) == "0000:03:00.0"

    def test_a_dangling_link_is_none_and_not_a_guess(self, tmp_path):
        """A row that does not know which device it describes must not
        read like one that does (``ports_checked``'s rule)."""
        device = tmp_path / "card1" / "device"
        device.parent.mkdir()
        device.symlink_to(tmp_path / "gone")
        assert _pci_slot_of(device) is None


# ---------------------------------------------------------------------------
# GPU threshold alerting
# ---------------------------------------------------------------------------


def _make_snapshot_with_gpu(gpu_usage: dict) -> ResourceSnapshot:
    row = ResourceSnapshot(
        cpu_percent=25.0,
        ram_used_mb=8000,
        ram_total_mb=16000,
        ram_percent=50.0,
        swap_used_mb=512,
        swap_total_mb=4096,
        disk_usage={},
        gpu_usage=gpu_usage,
        load_avg_1m=1.0,
        load_avg_5m=1.5,
        load_avg_15m=1.2,
    )
    row.id = uuid.uuid4()
    row.recorded_at = datetime.now(UTC)
    return row


class TestGpuThresholds:
    @pytest.fixture
    def agent(self):
        return SysAdminAgent()

    @pytest.fixture
    def mock_session(self):
        session = AsyncMock()
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.execute = AsyncMock()
        return session

    @pytest.fixture
    def thresholds(self):
        return Thresholds(gpu_temp_warning_c=90, gpu_vram_warning_percent=90)

    @pytest.mark.asyncio
    async def test_no_alert_below_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 65.0, "vram_percent": 50.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0

    @pytest.mark.asyncio
    async def test_temp_alert_at_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 92.0, "vram_percent": 50.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1

    @pytest.mark.asyncio
    async def test_vram_alert_at_threshold(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 65.0, "vram_percent": 95.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 1

    @pytest.mark.asyncio
    async def test_both_alerts(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": 95.0, "vram_percent": 95.0},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts >= 2

    @pytest.mark.asyncio
    async def test_empty_gpu_usage_no_alert(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({})
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0

    @pytest.mark.asyncio
    async def test_null_temp_no_alert(self, agent, mock_session, thresholds):
        snapshot = _make_snapshot_with_gpu({
            "card0": {"name": "RX 7900", "temp_c": None, "vram_percent": None},
        })
        alerts = await agent._check_thresholds(mock_session, snapshot, thresholds)
        assert alerts == 0
