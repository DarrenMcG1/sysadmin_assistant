# Handoff — 2026-08-14

## Next action

Wire the pre-staged `searxng` entry in `services.yaml` to `estate-manager-searxng-shim.service` on port 8600 — the shim is active and answering 200 now — then restart `sysadmin.service` to deploy this session's port-findings judging alongside it, and take `SNAG-UNITS-002` as the next roadmap session.

## This session — 26b-A, and most of it was checking whether the plan was still true

Session 26b was asked for. **Three of its four checkboxes had been
overtaken** and the session's real work was establishing that before
writing anything, then building the thing none of the four asked for.

Suite **1626 passed** (+29), 1 skipped, ruff and mypy clean, no
migration. Plus the one deliberately-red SearXNG guard, inherited.

### The plan was four days older than the repository that invalidated it

Session 26b was scoped **2026-08-07**. `estate-manager` was created
**2026-08-11** and built its conformance audit **2026-08-13**.

- **Item 1 inverted rather than aged.** "Move the registry into
  `config.yaml`, render the guide's table from it" — but the guide moved
  to estate-manager on 2026-08-11, and
  `estate_service/audit/checks/ports.py` now parses *that markdown table*
  as its source of truth, with a guard that errors rather than reporting
  zero findings on an empty parse. Mirroring the registry here would
  break their check and have the monitor own a cross-repo convention.
  **Killed, not deferred.**
- **Item 2 was already built** — the `unclaimed_listener` breach — and it
  has earned its keep: it is how syncthing's 8384 got a registry row on
  2026-08-13, which that row says in its own text.
- **Item 3 (contended defaults) was delegated** as `SNAG-ESTATE-004`. It
  is conformance against a rule in *their* guide, needs no privileges,
  and filing a finding is the audit's remit rather than ours.
- **Item 4 is genuinely ours** and became **Session 26c**.

### What shipped instead outranked all four

The estate **files findings and never alerts**, and
`judge_audit_invariants` deliberately judged only whether the audit
*ran*. So a `breach` was detected, correct, machine-readable, served at
`:8400/api/audit/findings` — and never said out loud by anything.

That is Session 46's lesson from **the day before**, one layer up: *the
diagnosis was complete, correct and machine-readable the entire time; a
count is not news.* `judge_audit_findings` now judges the `ports` check
per finding, as a fifth surface.

### Rule 3 is narrowed, not reversed, and the filter is a check name for a measured reason

`judgements.py` rule 3 said the estate's findings are not our alerts, for
two reasons — collation findings are this service's own alerts arriving
through a second producer, and pointers/seams are other repositories'
conformance. **Both still exclude exactly what they excluded.** Neither
reaches a port, because no repository owns one, and since the estate may
not alert the question was never who speaks but whether anyone does.

The filter is `check == "ports"` and **not a severity**, which was
checked rather than assumed: **all four** estate checks emit `breach`, so
a severity-only rule would have re-imported the entire collation family.

### Three decisions that were the opposite of the first draft

- **`warn` is not judged.** `claimed_but_silent` is *availability*, and
  availability has an owner here — `services.yaml` plus the sysadmin
  agent's `% unreachable` family. That today's one live `warn` (port
  3300) does not overlap is **luck, not design**: its registry row reads
  "unit to follow", so the overlap arrives the day that unit ships.
- **Above `port_breach_max_rows` (5) the family collapses to a roll-up**
  — the inverse of Session 46's one-row-per-fault rule, and its
  complement. Six unclaimed listeners at once is a table moved or
  truncated, not six services, and six toasts train the reader to dismiss
  the family (`SNAG-UNITS-002`'s refusal to ship fifteen). The estate
  guards the *empty* parse; a partial one is the gap that leaves.
- **`audit_invariants` and `audit_findings` are two surfaces**, though
  they come from one check run. They are two HTTP calls that fail
  independently and the sweep is scoped per surface — one id would let
  "the audit completed" close port rows raised off a payload nobody
  received.

### Verified against the real detector, because this family ships with zero live rows

That is `SNAG-ESTATE-002`'s exact starting position, so a synthesised
literal was not enough. The estate's own `run_check` was driven
**in-process** against the live registry document with a listener bound
on 8888 — no writes to their database:

```
before   breaches=[]                      judged: []
bind 8888  breaches=[8888] unclaimed_listener
           -> warning | Estate port 8888 registry breach
after    breaches=[]                      judged: []
```

It caught one defect no literal would have: the estate stamps a first
sighting `standing_days: 0.0`, and "Standing 0 days." reads as a rounding
artefact. The clause is now dropped below 0.1 days.

### Session 26c is scoped, and the estate's premise does not hold on this side

Measured, not assumed. **`ss -ltnp` unprivileged as `gaddi` attributes
every registry-relevant port** — 8080, 8300, 8400, 8500, 8600 all return
a pid. The estate's "process names need privileges" is true only for
*other users'* sockets, and almost everything in the registry is our own
process. `/proc/<pid>/cgroup` then names the unit with scope in the path.

Blank for root-owned listeners: 5432, 1883, 631, 139/445, and **8601**
(the SearXNG container, podman). Rejected routes and why are in tasks.md.

**Nothing on this box has ever collided** — every listening port appears
exactly once — which is the honest argument for 26c being its own session
rather than folded in here.

## Corrections to the previous handoff

- **Session 46 is deployed**, contrary to its "Blocked / waiting on:
  Deploy". `sysadmin.service` restarted at **15:03 BST** today, after
  that 13:23 commit, and the family is live: one open row, `Orphaned unit
  still enabled: garmin-sync.service (user)`, created 15:04.
- **The SearXNG shim is running.** It was `inactive (dead)`; it is now
  `active` and `http://127.0.0.1:8600/api/health` returns 200
  `{"status":"healthy"}`. The blocker in that handoff is gone. Note the
  commented block still guesses `unit: searxng.service` — the real unit
  is `estate-manager-searxng-shim.service`.
- **This snag list claimed `count_open_snags` reports 15. It reports 47**,
  measured against `estate_service/projects/roadmap.py` — which is also
  where that function lives now, so the claim had outlived the code it
  named as well as the number.
- **Session 26b's last checkbox named `sysadmin/services/units.py`**,
  gone since Session 35's module split. Same stale-path defect as commit
  `ce71bef`, two days later.

## Blocked / waiting on

- **Deploy of this session's work.** The daemon serves start-time code.
  No migration; `port_breach_max_rows` is new in `config.yaml`.
- **`SNAG-ESTATE-004`** needs an estate-manager session to record it —
  nothing was written into that repository from here, deliberately.
- **`judge_attention` against a populated payload** — unchanged since
  Session 45. Note `judge_audit_findings` deliberately did **not** join
  that queue: it was exercised against the live detector before shipping.
- **The tray toast**, the gap Sessions 43–46 all left.

## Next session — ranked, with the reasoning

**Sub-session actions first, separately** (neither is a session): wire
SearXNG and restart to deploy, ~10 minutes together.

1. **`SNAG-UNITS-002` — 15 of this box's 18 units with a `Restart=`
   policy cannot reach `failed`**, every live service except `sysadmin`,
   `alfred-backend` and `alfred-frontend`. It wins because it is the
   estate-wide form of the fault that **restart-looped 52,178 times and
   stalled the kernel on 2026-08-08**, it is live now, and the previous
   session deferred it on a decision that is the actual blocker: whether
   this repository should advise on units it does not own. That decision
   costs minutes and unblocks the work.
2. **Session 27 — log aggregator tiers.** *Demoted on measurement.* Its
   standing argument was 599,794 open alert rows; the live table now
   holds **2 open rows, 0 from `log_aggregator`, 0 critical**. Session 42
   fixed `SNAG-AGENT-002` and the backlog has drained and been purged.
   What remains is genuine feature work — week-on-week signature trends,
   noise recommendations — with nothing forcing it.
3. **Session 26c — port collision detection.** The route is decided and
   written down, so it is cheap whenever it is wanted, but it detects a
   fault this box has never had. Speculative, and it says so.
4. **Sessions 25b/25c — reliability Tiers 2–3.** Nothing is pushing them
   and Tier 1 is answering.

Named as blocked rather than dropped: `SNAG-ESTATE-001`'s retirement
checklist (a process, and an estate convention if it is anyone's) and
`SNAG-ESTATE-004` (needs the other repository's session).
