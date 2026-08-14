# Handoff — 2026-08-14

## Next action

Run `sudo systemctl restart sysadmin.service` to deploy the wired SearXNG entry, which is inert until then because the daemon holds `services.yaml` in a process-wide singleton, and then take `SNAG-UNITS-002` as the next roadmap session.

## This session — SearXNG wired, the day its guard went red

The deploy-triggered guard did its job. `tests/test_searxng_wiring.py`
went red when estate-manager deployed SearXNG earlier on 2026-08-14, and
the gap was closed the same day — which is the entire argument for
pre-staging a test rather than a note.

Suite **1631 passed, nothing skipped, nothing red** (from 1627 passed,
1 failed on purpose, 1 skipped). Ruff and mypy clean. No migration.

### Every handed-over value was verified, and one was wrong in the direction that mattered

estate-manager wrote the port, unit name, health path and status ladder
into `tasks.md` for us. All four were checked against the live box
rather than copied, and the check found a trap the *pre-staged block*
had walked into — not the handover.

**The pre-staged block named `/healthz`.** The shim proxies unknown
paths upstream, so `http://localhost:8600/healthz` reaches SearXNG's own
liveness ping and returns **200 whenever the container is running,
including when every search fails** — the one case `kind: http` was
chosen to catch. It answers 200 right now, so that wiring would have
looked correct on the day it landed and been blind on the day it
mattered. `/api/health` is the only path that knows whether searching
works: it records the outcome of every real search proxied through, with
a background probe filling the silence.

### The 424/503 ladder was driven against real sockets, not read

Both repositories describe the mapping in prose. `_check_http` was run
against a socket returning each code: **200 → `ok`**, **424 →
`degraded`** (SearXNG up, searching broken), **503 → `critical`**
(container dead). The distinction is deliberate on their side — a
captcha'd engine is a fault off this box, a dead container is not.

`_handle_status` already requires **three consecutive** degraded checks
before raising, so the estate's request that a 424 be "worth an alert
only if it stands" needed no work here: 15 minutes of persistence at the
300-second interval. `auto_restart` defaults to false, so this service
will never restart estate-manager's container out from under it.

Live check against the running shim: `ok` in **23 ms**, body
`status: healthy`, probe 153 s old, 20 results, no unresponsive engines.

### A second entry the plan did not ask for

`searxng-upstream` declares the 8601 container `monitor: false` with a
reason. It is deliberately not checked — a dead container already
surfaces as the shim's 503, and two entries give one fault two alert
rows. But **omitting it from the file entirely put it in the unit
sweep's `host` findings permanently**, where it could never be actioned
and where "watched through the shim on purpose" is indistinguishable
from "nobody wired it up". That is the shape `venture-chat-large`
already carries for the same reason. Measured: host findings 9 → 8, and
no searx unit is left unaccounted for.

### Item 3's rationale was narrowed rather than inherited

`tasks.md` said no `project:` because SearXNG is "third-party software
with no repository". **That premise no longer describes what we
monitor**: the URL is served by estate-manager's own module and *that*
repository has a `.project.yaml`, so the field would now resolve and the
loader would not object.

Put to the owner, who kept the omission on narrower ground: what this
entry judges is whether **searching works**, and a 424 means upstream
engines are failing off this box — not the estate-manager repository's
fault to carry. The shim is the plumbing that makes SearXNG monitorable,
not the thing being monitored. The guard's docstring records the
narrowing so nobody re-derives it.

### The guard changed shape rather than retiring

Three things, and the third is the one worth keeping:

- **Its gate now separates environments, not dates.** CI has no searxng
  unit, so the three assertions skip there and run here against the live
  box. Before the deploy they skipped *everywhere*, which the file's own
  comment calls worse than no test at all.
- **`test_the_pre_staged_block_is_still_commented_out` was deleted**,
  per its own failure message. It was gated the opposite way round and
  would have gone red in CI the moment the block was activated — proved
  by running the suite under an empty `HOME` rather than reasoned about.
- **The `kind: http` assertion is stronger, not merely narrowed.** The
  obvious fix — skip `monitor: false` entries — would let someone
  silence the family by muting the *shim* and still pass. It now asserts
  **exactly one** searx entry is checked before asserting that one is
  HTTP.

Both real unit names are pinned into the gate's parametrised cases.
**Neither is any of the three spellings it guessed** — the deploy shipped
`estate-manager-searxng-shim.service` and `estate-manager-searxng.service`
— so the substring match is the only reason the gate fired at all, and it
must not be "tidied" into an exact one.

## Corrections to the previous handoff and STATUS.md

- STATUS.md's testing row said **1626** tests; the measured baseline was
  **1627** passed. Corrected to the new 1631.
- `SNAG-UNITS-002` was filed as **15 of 18** units unable to reach
  `failed`. Re-measured live: **17 of 20**, and the two additions are the
  SearXNG units wired this session. The defect is what a correctly
  written unit gets *by default* on this box, so the population grows
  with every service the estate adds — filing it as a fixed list of 15
  understates it as a standing rule. Snag updated.

## Blocked / waiting on

- **The restart could not be run.** `sudo systemctl restart
  sysadmin.service` needs a password and this session was
  non-interactive. The daemon is untouched and still `active`; the
  schema was checked at head **012** beforehand, so the restart is safe
  when someone runs it. Until then the entry is inert — `services.yaml`
  is loaded once into a process-wide singleton at lifespan start.
- **Session 26c** (port-collision detection via `ss -ltnp` →
  `/proc/<pid>/cgroup`) is unblocked but unstarted.
- Two open alerts on the live box, both from Session 46 and both real:
  `Orphaned unit still enabled: garmin-sync.service (user)` and
  `Unmonitored systemd units: 14 findings`.

## Next session — ranked, with the reasoning

**Sub-session actions first, because neither is a session:** the restart
above, and `systemctl --user disable garmin-sync.service && rm` for the
armed orphan that has been holding an alert row open since 15:04 today.

1. **`SNAG-UNITS-002` — the 17 units that cannot reach `failed`.** It
   wins because it *moved today*, and moved because of ordinary work:
   wiring one service added two units to the population. Every other
   candidate is static. It is also the only open item where this
   repository's own dependency is affected — the shim now monitored can
   restart-loop for ever without an `OnFailure=` ever firing, and the
   `kind: http` check written today is the only thing that would notice.
   Session 46 already built `restart_is_bounded`, so the detection
   exists; what is missing is the decision about *saying* it, which
   `SNAG-UNITS-002` itself records as the hard part — 17 criticals on
   the first run is the pile-up shape wearing a new hat.
2. **Session 27 — the log-aggregator tiers, with `SNAG-AGENT-002`.**
   Loses because its evidence evaporated. Its case was 598,091 unresolved
   rows; Session 42 fixed the raise rule and the live table now holds
   **2**. The tiering is still worth building, but it is now a feature
   rather than a fire, and it competes on merit against work that is
   still bleeding.
3. **Sessions 25b/25c — reliability Tiers 2–3.** Loses on the same
   ground and one more: it is the third scorer on a box whose scoring is
   already the best-served part of the system, and nothing on the estate
   is currently asking for it.

**Named as blocked rather than dropped:** `SNAG-ESTATE-002` (the
producer's `Nudge.title`/`.message` are `@property` and `asdict` drops
them, so `judge_attention` has still never run against a populated
payload) needs an estate-manager change first and cannot be started
here.
