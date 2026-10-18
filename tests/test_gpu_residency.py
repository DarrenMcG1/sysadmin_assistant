"""A VRAM resident evicted to GTT, read from DRM fdinfo.

``sysadmin/monitor/gpu_residency.py`` and estate message
``af170afe-54d0-4997-8a10-42267c6a2214``.  The fdinfo texts below are
the live ones of 2026-10-18 21:53 BST, trimmed to the keys the reader
uses plus the ``amd-evicted-vram`` that rule 1 refuses.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sysadmin.monitor import gpu_context, gpu_residency
from sysadmin.monitor.agent import SysAdminAgent
from sysadmin.monitor.models.service_health import is_fault
from sysadmin.monitor.services import ServiceEntry, check_plan

DGPU = "0000:03:00.0"
IGPU = "0000:7c:00.0"

#: ``alfred-inference``, MainPID 1316, after the evening's Deadlock spans.
EVICTED = f"""\
pos:\t0
drm-driver:\tamdgpu
drm-client-id:\t28
drm-pdev:\t{DGPU}
drm-total-gtt:\t20836 KiB
drm-resident-gtt:\t1069156 KiB
drm-total-vram:\t2349364 KiB
drm-resident-vram:\t1301044 KiB
amd-evicted-vram:\t0 KiB
"""

#: ``venture-chat``, MainPID 1315, the same minute: resident above total.
ON_THE_CARD = f"""\
drm-driver:\tamdgpu
drm-client-id:\t27
drm-pdev:\t{DGPU}
drm-total-gtt:\t38208 KiB
drm-resident-gtt:\t38208 KiB
drm-total-vram:\t6275144 KiB
drm-resident-vram:\t6283592 KiB
"""

_UNIT_STATUS = "sysadmin.monitor.agent.get_unit_status"


def fake_proc(tmp_path: Path, pid: int, fds: dict[str, str]) -> Path:
    fdinfo = tmp_path / str(pid) / "fdinfo"
    fdinfo.mkdir(parents=True)
    for fd, text in fds.items():
        (fdinfo / fd).write_text(text)
    return tmp_path


def declaring() -> ServiceEntry:
    return ServiceEntry.model_validate({
        "name": "alfred-inference",
        "kind": "http",
        "url": "http://localhost:8081/health",
        "port": 8081,
        "holds_vram": True,
        "systemd": {"unit": "alfred-inference.service", "scope": "user"},
    })


class TestTheShortfallIsTotalLessResident:
    def test_the_live_eviction_reads_one_gib(self, tmp_path):
        """Falsified by reading ``amd-evicted-vram``, which says 0."""
        proc = fake_proc(tmp_path, 1316, {"6": EVICTED})
        residency = gpu_residency.read_residency(1316, DGPU, proc)
        assert residency.evicted_kib == 1_048_320
        assert residency.resident_gtt_kib - residency.total_gtt_kib == 1_048_320

    def test_resident_above_total_is_no_eviction(self, tmp_path):
        """Rule 2: a signed difference would read -8,448 KiB."""
        proc = fake_proc(tmp_path, 1315, {"6": ON_THE_CARD})
        residency = gpu_residency.read_residency(1315, DGPU, proc)
        assert residency.evicted_kib == 0
        assert not gpu_residency.reading("u", 1315, residency)[
            gpu_residency.DETAIL_KEY
        ]["evicted"]

    def test_a_bare_number_is_bytes(self):
        assert gpu_residency._kib("0") == 0
        assert gpu_residency._kib("2048") == 2
        assert gpu_residency._kib("3 MiB") == 3072


class TestClientsAreDeduplicatedAndScopedToTheCard:
    def test_two_fds_on_one_client_count_once(self, tmp_path):
        """Falsified by summing per fd, which doubles every figure."""
        proc = fake_proc(tmp_path, 1316, {"6": EVICTED, "9": EVICTED})
        residency = gpu_residency.read_residency(1316, DGPU, proc)
        assert residency.clients == 1
        assert residency.evicted_kib == 1_048_320

    def test_the_igpu_and_non_drm_fds_are_not_counted(self, tmp_path):
        proc = fake_proc(tmp_path, 1316, {
            "0": "pos:\t0\nflags:\t02\n",
            "7": EVICTED.replace(DGPU, IGPU),
        })
        residency = gpu_residency.read_residency(1316, DGPU, proc)
        assert residency.clients == 0
        assert residency.evicted_kib == 0

    def test_a_vanished_process_raises(self, tmp_path):
        with pytest.raises(OSError):
            gpu_residency.read_residency(4242, DGPU, tmp_path)


def _active(pid: int | None) -> dict:
    props = {"is_active": True, "ActiveState": "active", "SubState": "running"}
    if pid is not None:
        props["MainPID"] = str(pid)
    return props


async def _check(unit_info: dict, residency=None, read_error=None):
    """Drive the production path with the context term held at ``ok``."""
    svc = declaring()
    agent = SysAdminAgent()
    with (
        patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
        patch(_UNIT_STATUS, AsyncMock(return_value=unit_info)),
        patch.object(
            agent,
            "_gpu_context_reading",
            AsyncMock(side_effect=lambda *a: (a[3], a[4], a[5])),
        ),
        patch.object(
            gpu_residency,
            "read_residency",
            side_effect=read_error or (lambda pid, slot: residency),
        ) as reader,
    ):
        status, _, details = await agent._check_http_and_unit(
            svc, check_plan(svc), object()
        )
    return status, details, reader


def _residency(text: str, tmp_path: Path) -> gpu_residency.Residency:
    return gpu_residency.read_residency(1, DGPU, fake_proc(tmp_path, 1, {"6": text}))


class TestTheCheckRecordsTheEviction:
    @pytest.mark.asyncio
    async def test_an_evicted_resident_is_degraded_with_a_reason(self, tmp_path):
        status, details, _ = await _check(_active(1316), _residency(EVICTED, tmp_path))
        assert status == gpu_residency.EVICTED_STATUS
        assert is_fault(status)
        assert "1.0 GiB" in details["reason"]
        assert details[gpu_residency.DETAIL_KEY]["evicted_kib"] == 1_048_320

    @pytest.mark.asyncio
    async def test_a_resident_on_the_card_stays_ok(self, tmp_path):
        status, details, reader = await _check(
            _active(1315), _residency(ON_THE_CARD, tmp_path)
        )
        assert status == "ok"
        assert details[gpu_residency.DETAIL_KEY]["evaluated"] is True
        reader.assert_called_once_with(1315, DGPU)

    @pytest.mark.asyncio
    async def test_no_client_on_the_card_is_recorded_not_judged(self, tmp_path):
        """Rule 4: ``venture-embed``'s boot start, CPU-only by design."""
        empty = gpu_residency.Residency(0, 0, 0, 0, 0)
        status, details, _ = await _check(_active(1046), empty)
        assert status == "ok"
        assert details[gpu_residency.DETAIL_KEY]["clients"] == 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("unit_info", "error", "why"),
        [
            (_active(None), None, "no MainPID"),
            (_active(0), None, "no MainPID"),
            (_active(1316), PermissionError("denied"), "could not be read"),
        ],
    )
    async def test_every_way_of_not_knowing_leaves_the_status(
        self, unit_info, error, why
    ):
        status, details, _ = await _check(unit_info, read_error=error)
        assert status == "ok"
        assert details[gpu_residency.DETAIL_KEY]["evaluated"] is False
        assert why in details[gpu_residency.DETAIL_KEY]["reason"]

    @pytest.mark.asyncio
    async def test_a_lost_context_keeps_its_own_reason(self, tmp_path):
        """The reading rides along; the alert quotes the first fault named."""
        svc = declaring()
        agent = SysAdminAgent()
        lost = ("degraded", 5, {"reason": "context lost", gpu_context.DETAIL_KEY: {}})
        with (
            patch.object(agent, "_check_http", AsyncMock(return_value=("ok", 5, {}))),
            patch(_UNIT_STATUS, AsyncMock(return_value=_active(1316))),
            patch.object(agent, "_gpu_context_reading", AsyncMock(return_value=lost)),
            patch.object(
                gpu_residency, "read_residency",
                return_value=_residency(EVICTED, tmp_path),
            ),
        ):
            status, _, details = await agent._check_http_and_unit(
                svc, check_plan(svc), object()
            )
        assert status == "degraded"
        assert details["reason"] == "context lost"
        assert details[gpu_residency.DETAIL_KEY]["evicted"] is True
