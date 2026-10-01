#!/usr/bin/env python3
"""Which reads leave a runtime-suspended dGPU asleep?  A one-night drive.

Session 313 measured that the collector's ``rocm-smi`` call resumes a
suspended RX 7900 XTX on every poll (tasks.md, Session 313).  Two ways to
stop it are on the table, and both rest on an unmeasured claim:

* ``rocm-smi -d <iGPU>`` alone — but the tool may still open every card
  while it initialises;
* ``_from_sysfs``'s reads of the dGPU — ``hwmon`` ``temp1_input`` and
  ``power1_average``, ``mem_info_vram_used`` and ``mem_info_vram_total``
  — any of which the driver may serve by waking the card.

The card only suspends with the monitors off, so this runs at night as a
transient unit and is read the next morning.  Each trial starts only
when the card has been ``suspended`` for at least a second, makes **one**
read, and records ``power/runtime_status`` and
``power/runtime_active_time`` either side of it.  Both are the PM core's
attributes, never the driver's, so asking them wakes nothing.  A trial
**woke** the card when the active time grew or the status left
``suspended`` within half a second of the read returning.

Two controls are mixed in with the candidates, in random order each round:

* ``idle`` does nothing for 2 s — the rate at which something *else*
  (the daemon's own poll, venture-assistant's 300 s request) wakes the
  card inside a trial window.  A candidate is only as clean as this.
* ``rocm_smi_all`` is today's collector call — the positive control,
  which must read ``woke`` or the instrument cannot see a wake.

Every line carries ``CLOCK_MONOTONIC`` as well as wall time, so the
morning match against ``journalctl -k -o short-monotonic``'s ``PSP is
resuming`` lines needs no clock arithmetic.  Standard library only: it
runs under ``/usr/bin/python3`` with nothing of this repository's on
the path.
"""

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

DGPU = "0000:03:00.0"
PCI = Path("/sys/bus/pci/devices")
KFD_NODES = Path("/sys/class/kfd/kfd/topology/nodes")
ROCM_SMI = "/opt/rocm/bin/rocm-smi"
METRICS_ARGS = (
    "--showuse", "--showtemp", "--showmeminfo", "vram",
    "--showpower", "--showbus", "--json",
)


def status() -> str:
    try:
        return (PCI / DGPU / "power" / "runtime_status").read_text().strip()
    except OSError as exc:
        return f"error:{exc.errno}"


def active_ms() -> int | None:
    try:
        return int((PCI / DGPU / "power" / "runtime_active_time").read_text())
    except (OSError, ValueError):
        return None


def igpu_index() -> int | None:
    """rocm-smi's index for the iGPU, from KFD topology — no spawn.

    rocm-smi numbers the GPU nodes (``simd_count`` > 0) in node order;
    ``location_id`` is the PCI bus/device/function.  Resolving the index
    by asking ``rocm-smi --showbus`` would be the very read under test.
    """
    gpus = []
    for node in sorted(KFD_NODES.iterdir(), key=lambda p: int(p.name)):
        props = dict(
            line.split(None, 1)
            for line in (node / "properties").read_text().splitlines()
            if " " in line
        )
        if int(props.get("simd_count", 0)) > 0:
            gpus.append(int(props["location_id"]))
    dgpu_loc = int(DGPU.split(":")[1], 16) << 8
    others = [i for i, loc in enumerate(gpus) if loc != dgpu_loc]
    return others[0] if len(others) == 1 else None


def read_file(path: Path) -> dict:
    try:
        return {"value": path.read_text().strip()}
    except OSError as exc:
        return {"errno": exc.errno, "error": exc.strerror}


def run_smi(*args: str) -> dict:
    proc = subprocess.run(
        [ROCM_SMI, *args], capture_output=True, text=True, timeout=60,
    )
    out: dict = {"rc": proc.returncode}
    try:
        payload = json.loads(proc.stdout)
        out["cards"] = {k: v.get("PCI Bus") for k, v in payload.items()}
    except (ValueError, AttributeError):
        out["stdout"] = proc.stdout[-300:]
    return out


def hwmon(name: str) -> Path:
    found = sorted((PCI / DGPU / "hwmon").glob(f"hwmon*/{name}"))
    return found[0] if found else PCI / DGPU / "hwmon" / "missing" / name


def kinds(igpu: int) -> dict:
    dev = PCI / DGPU
    return {
        "idle": lambda: time.sleep(2) or {},
        "rocm_smi_all": lambda: run_smi(*METRICS_ARGS),
        "rocm_smi_igpu": lambda: run_smi("-d", str(igpu), *METRICS_ARGS),
        "rocm_smi_igpu_names": lambda: run_smi(
            "-d", str(igpu), "--showproductname", "--json",
        ),
        "hwmon_temp1_input": lambda: read_file(hwmon("temp1_input")),
        "hwmon_power1_average": lambda: read_file(hwmon("power1_average")),
        "mem_info_vram_used": lambda: read_file(dev / "mem_info_vram_used"),
        "mem_info_vram_total": lambda: read_file(dev / "mem_info_vram_total"),
    }


def settled(timeout: float) -> bool:
    """Wait until the card has read ``suspended`` for a full second."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if status() == "suspended":
            time.sleep(1)
            if status() == "suspended":
                return True
        else:
            time.sleep(0.5)
    return False


def trial(kind: str, fn) -> dict:
    s0, a0 = status(), active_ms()
    wall, mono = time.time(), time.monotonic()
    result = fn()
    took = time.monotonic() - mono
    s1, a1 = status(), active_ms()
    seen = [s1]
    for _ in range(10):
        time.sleep(0.05)
        seen.append(status())
    a2 = active_ms()
    grew = None if None in (a0, a2) else a2 - a0
    return {
        "kind": kind,
        "at": datetime.fromtimestamp(wall).isoformat(timespec="milliseconds"),
        "mono": round(mono, 3),
        "took_s": round(took, 3),
        "status_before": s0,
        "status_after": s1,
        "status_seen": sorted(set(seen)),
        "active_ms_after_read": None if None in (a0, a1) else a1 - a0,
        "active_ms_grew": grew,
        "woke": bool(grew) or any(s != "suspended" for s in seen),
        "result": result,
    }


def emit(out, record: dict) -> None:
    line = json.dumps(record)
    print(line, flush=True)
    out.write(line + "\n")
    out.flush()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--until", required=True, help="HH:MM to stop, local time")
    ap.add_argument("--round-s", type=float, default=300)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    hh, mm = map(int, args.until.split(":"))
    stop = datetime.now().replace(hour=hh, minute=mm, second=0, microsecond=0)
    igpu = igpu_index()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("a") as out:
        emit(out, {"start": datetime.now().isoformat(), "until": stop.isoformat(),
                   "dgpu": DGPU, "igpu_index": igpu,
                   "autosuspend_delay_ms": read_file(
                       PCI / DGPU / "power" / "autosuspend_delay_ms")})
        if igpu is None:
            emit(out, {"abort": "iGPU index not resolvable from KFD topology"})
            return 1
        table = kinds(igpu)
        rnd = 0
        while datetime.now() < stop:
            rnd += 1
            began = time.monotonic()
            order = list(table)
            random.shuffle(order)
            for kind in order:
                if datetime.now() >= stop:
                    break
                if not settled(timeout=60):
                    emit(out, {"round": rnd, "kind": kind,
                               "skipped": "not suspended", "status": status()})
                    continue
                emit(out, {"round": rnd, **trial(kind, table[kind])})
            time.sleep(max(0.0, args.round_s - (time.monotonic() - began)))
        emit(out, {"end": datetime.now().isoformat(), "rounds": rnd})
    return 0


if __name__ == "__main__":
    sys.exit(main())
