#!/usr/bin/env python3
"""Who keeps the dGPU awake overnight?  A one-night witness.

Session 324 measured that the RX 7900 XTX runtime-suspended on exactly one
night since 2026-09-10: 27→28 September, 283 times, under 6.18 LTS.  It
did not suspend on the 13 nights of boot −3 (also 6.18 LTS) or on any
night since the kernel 7.2.7 boot, so the kernel is not what separates
the nights.  The monitors disconnect every night, so they are not either.
The LLM load on 27 September 02:00–05:00 (63 chat and 43 embedding
requests) matched the night after (72 and 60), which did suspend.  What
changed between them was the desktop: Chromium, the project-manager
Electron app, Kate and Konsole all closed between 22:48 and 23:03, and the
first suspend came at 23:14:35.

Read live with the monitors on, five desktop clients submit work to the
dGPU in every second: spotify, steamwebhelper, Xwayland, plasmashell and
an Electron app.  Whether they keep doing it with no outputs is what this
records.  Any client that submits at least once every
``autosuspend_delay_ms`` (5000 here) holds the card awake.

Every second it reads ``power/runtime_status``.  While the card is awake
it also reads each client's ``drm-engine-*`` nanoseconds from
``/proc/<pid>/fdinfo``, for every file descriptor open on one of the
dGPU's DRM nodes.  That is the kernel's per-client accounting, read
without root.  While the card reads ``suspended`` it reads nothing else:
no client can be submitting then, and so the witness cannot be what wakes
it.  Once a minute it writes one JSON line:

* ``status``: seconds sampled ``active`` and ``suspended``;
* ``suspended_ms``: growth of ``power/runtime_suspended_time``;
* ``connectors``: each dGPU connector's ``status`` and ``dpms``;
* ``clients``: per ``comm``, the seconds it submitted work and the
  engine milliseconds it used;
* ``longest_quiet_s``: the longest run of awake seconds in which no
  readable client submitted anything.  A run of 5 or more with no
  suspend means something this cannot see held the card (kwin, which is
  not dumpable; a root process; or the driver itself);
* ``unreadable``: processes whose ``fd`` directory could not be listed.

Standard library only: it runs under ``/usr/bin/python3`` with nothing
of this repository's on the path.
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DGPU = "0000:03:00.0"
PCI = Path("/sys/bus/pci/devices")


def dgpu_nodes(slot: str) -> set[str]:
    """The ``/dev/dri`` names that belong to the card, resolved by PCI slot."""
    drm = PCI / slot / "drm"
    return {f"/dev/dri/{p.name}" for p in drm.iterdir() if p.name.startswith(("card", "renderD"))
            and "-" not in p.name}


def connectors(slot: str) -> dict[str, str]:
    out = {}
    for card in (PCI / slot / "drm").glob("card[0-9]*"):
        for c in card.glob(f"{card.name}-*"):
            if "Writeback" in c.name:
                continue
            status = (c / "status").read_text().strip()
            if status == "connected":
                out[c.name.split("-", 1)[1]] = (c / "dpms").read_text().strip()
            else:
                out[c.name.split("-", 1)[1]] = status
    return out


def read_power(slot: str, name: str) -> str:
    return (PCI / slot / "power" / name).read_text().strip()


def sample_clients(nodes: set[str]) -> tuple[dict[tuple[int, str], tuple[str, int]], int]:
    """``{(pid, client_id): (comm, engine_ns)}`` and the unreadable-process count."""
    clients: dict[tuple[int, str], tuple[str, int]] = {}
    unreadable = 0
    for entry in os.scandir("/proc"):
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            unreadable += 1
            continue
        for fd in fds:
            try:
                if os.readlink(f"/proc/{pid}/fd/{fd}") not in nodes:
                    continue
                info = Path(f"/proc/{pid}/fdinfo/{fd}").read_text()
                comm = Path(f"/proc/{pid}/comm").read_text().strip()
            except OSError:
                continue
            client_id = None
            engine_ns = 0
            for line in info.splitlines():
                key, _, value = line.partition(":")
                if key == "drm-client-id":
                    client_id = value.strip()
                elif key.startswith("drm-engine-"):
                    engine_ns += int(value.split()[0])
            if client_id is not None:
                clients[(pid, client_id)] = (comm, engine_ns)
    return clients, unreadable


def run(slot: str, log: Path, duration: float, period: int) -> None:
    nodes = dgpu_nodes(slot)
    deadline = time.monotonic() + duration
    prev: dict[tuple[int, str], tuple[str, int]] | None = None
    while time.monotonic() < deadline:
        status = defaultdict(int)
        seconds = defaultdict(int)
        engine_ms = defaultdict(float)
        quiet = longest_quiet = 0
        unreadable = 0
        suspended_before = int(read_power(slot, "runtime_suspended_time"))
        for _ in range(period):
            tick = time.monotonic()
            state = read_power(slot, "runtime_status")
            status[state] += 1
            if state == "suspended":
                prev = None
                quiet = 0
            else:
                cur, unreadable = sample_clients(nodes)
                busy = set()
                if prev is not None:
                    for key, (comm, ns) in cur.items():
                        old = prev.get(key)
                        if old is not None and ns > old[1]:
                            busy.add(comm)
                            engine_ms[comm] += (ns - old[1]) / 1e6
                for comm in busy:
                    seconds[comm] += 1
                if prev is not None:  # the first awake second has nothing to diff
                    quiet = 0 if busy else quiet + 1
                    longest_quiet = max(longest_quiet, quiet)
                prev = cur
            time.sleep(max(0.0, 1.0 - (time.monotonic() - tick)))
        line = {
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "monotonic": round(time.monotonic(), 3),
            "status": dict(status),
            "suspended_ms": int(read_power(slot, "runtime_suspended_time")) - suspended_before,
            "connectors": connectors(slot),
            "clients": {c: {"s": seconds[c], "ms": round(engine_ms[c], 1)}
                        for c in sorted(seconds, key=lambda c: -engine_ms[c])},
            "longest_quiet_s": longest_quiet,
            "unreadable": unreadable,
        }
        text = json.dumps(line)
        with log.open("a") as f:
            f.write(text + "\n")
        print(text, flush=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--log", type=Path, required=True)
    ap.add_argument("--duration", type=float, default=10 * 3600, help="seconds")
    ap.add_argument("--period", type=int, default=60, help="seconds per line")
    ap.add_argument("--slot", default=DGPU)
    args = ap.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    run(args.slot, args.log, args.duration, args.period)
    return 0


if __name__ == "__main__":
    sys.exit(main())
