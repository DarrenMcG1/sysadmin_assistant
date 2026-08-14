# Handoff — 2026-08-14

## Next action

Start `estate-manager-searxng-shim.service` — it is enabled but `inactive (dead)` while SearXNG's container runs behind it on 8601 — then confirm `http://127.0.0.1:8600/api/health` answers in the contract's shape, uncomment the pre-staged `searxng` block in `services.yaml` with port 8600, and restart `sysadmin.service` to deploy that together with this session's armed-orphan alert family.

## This session

One task, taken end to end: `SNAG-ESTATE-001`'s durable half, the "make an
orphan finding **speak**" part of it. The other half — a retirement
checklist that includes `systemctl disable` — is a process rather than
code and is left open.

Suite **1597 passed** (51 new), ruff and mypy clean, no migration. Plus one
genuinely red test that is not this work's, described at the bottom.

### The failure was never detection, and that shaped the whole design

`GET /api/units/status` had both PersonalAssistant units classified
`orphaned`, with the dead path and the cause in plain English, eight days
before anyone looked — while they restart-looped 52,178 times and stalled
the kernel. There was an open alert the entire time: `Unmonitored systemd
units: 17 findings`.

So nothing was added to the *detector*. What was missing is that the
roll-up cannot name anything. A count says the estate has debt; it cannot
say which two of the seventeen are on fire. The fix is a second alert
family beside the roll-up — one row per **armed orphan**, an orphan
systemd will actually start — with the unit and scope in the title,
because the tray fingerprints on `{severity}:{title}` and a shared title
means one armed orphan masks the next.

### The obvious rule for "will it loop" was wrong, and the live units refuted it before it was written

This is the part worth carrying forward. "`Restart=` with no
`StartLimitBurst=`" reads as sound and is wrong in **both** directions:

- `personalassistant-backend.service` declares no start limit, so
  systemd's defaults apply — `DefaultStartLimitIntervalSec=10s`,
  `DefaultStartLimitBurst=5`. A limit **does** exist. It also sets
  `RestartSec=10`, which puts starts ten seconds apart, so five can never
  fit inside a ten-second window: the limiter is unreachable, and that is
  why it restarted 34,517 times without once entering `failed`. The naive
  rule gets the right answer here **for the wrong reason**, and would keep
  getting it until someone added a `StartLimitBurst=` that changed
  nothing.
- A unit declaring only `Restart=always` restarts every 100ms, five starts
  fit easily, and the loop *is* terminal. The naive rule calls that
  dangerous — and would have opened a critical on most of this box's
  healthy services on its first run.

The real test is arithmetic: `RestartSec × (StartLimitBurst − 1) <
StartLimitIntervalSec`. It is the same sum Session 39 did by hand for
`sysadmin.service` (`StartLimitIntervalSec=600` against `RestartSec=10`),
which is why that fix works, and `alfred-backend.service` passes it too on
a hand-written `StartLimitIntervalSec=60` — so the check distinguishes a
real guard from an absent one rather than just counting keys.

**Not knowing fails open**: an unparseable `RestartSec` falls back to the
default rather than assuming the worst. A false positive here sends
someone to rewrite a unit file that is fine, which is the direction
`monitor/collation.py` settled on for the same class of question.

### Both signals stayed pure, and that was checked rather than assumed

`scan.py` promises no subprocesses, and it keeps it. "Enabled" is an
enablement symlink under a `*.wants/`/`*.requires/` directory the sweep
already walks — the same trade `is_symlink()` already makes for distro
ownership. Matched on the link **name**, not its target, so a dangling
link left by an `rm` without a `disable` still counts, which is the state
`removal_command`'s docstring already warned about.

Cross-checked against `systemctl is-enabled` on every unit on this box:
they agreed, both scopes.

What purity costs is stated rather than hidden: this says "armed to loop",
never "has looped 34,517 times". `NRestarts` and `activating
(auto-restart)` need a subprocess and are not read.

### Three design decisions, each the opposite of the first draft

- **Arming is orphan-only.** Every healthy service here is enabled and
  most restart unboundedly, so an `armed` that meant "enabled" would alert
  on all of them. A *disabled* orphan is debt and stays in the roll-up —
  four of this box's six carry the PersonalAssistant shape exactly and are
  harmless only because someone disabled them.
- **The sweep excludes what the run *judged*, not what it raised.**
  `sysadmin/estate/agent.py`'s rule, and `SNAG-AGENT-006`'s. Against a
  raised set, a deduplicating family writes nothing on run two, has its
  still-true row swept, re-raises on run three — a flip-flop clearing the
  tray's fingerprint every turn.
- **`step_for` refuses the de-escalation, and that is deliberate here.**
  An orphan whose `Restart=` is *softened* stays `critical` until it is
  actually removed. A gentler restart policy does not fix a start job that
  cannot succeed.

`alert_threshold` does not govern this family. That knob is patience for
accumulated debt; an armed orphan is a unit failing on every trigger, and
one of them is worth saying.

### Verified against the live database in a rolled-back transaction

Necessary rather than ceremonial: the suite mocks the session, so it
cannot prove the title prefix plus `NOT IN (judged)` selects the right
rows in real PostgreSQL. Five runs of one fault:

```
run 1  raised 1     -> 1 row,  warning
run 2  held         -> 1 row   (dedup; NOT swept — the flip-flop case)
run 3  escalated    -> 1 row,  critical  (loop appears)
run 4  held         -> 1 row,  critical
run 5  resolved 1   -> 0 rows  (unit disabled)

2 rows written for one fault. Roll-up untouched. Residue after rollback: 0.
```

Two mutations were run against the suite before trusting it: swapping the
judged set for a raised set, and removing the `HOLD` branch. Each turned
the intended test red and nothing else.

### Live on this box: 1 armed orphan of 6

`garmin-sync.service` (user, enabled, `WorkingDirectory` under the
archived PersonalAssistant) → one `warning` row. It has no `Restart=`, so
it fails once per trigger rather than looping — the warning tier, not
critical. The four `Restart=always` orphans are all disabled and stay in
the roll-up.

### Filed, not fixed: SNAG-UNITS-002

**15 of the 18 units on this box with a `Restart=` policy cannot reach
`failed`** — every live service except `sysadmin`, `alfred-backend` and
`alfred-frontend`. This is the estate-wide form of the same defect, and
the first time the population has been counted rather than asserted.

Not alerted on: 15 rows on the first run is the pile-up shape wearing a
new hat, and it would train the reader to dismiss the family before it had
said anything true. The entry carries two candidate fixes and names the
decision each needs — the second (advice under `GET /api/units/actions`)
needs a ruling on whether this repository should advise on units it does
not own.

## Blocked / waiting on

- **Deploy.** The daemon serves start-time code, so none of this is live
  until `sysadmin.service` restarts. No migration, no config change.
  `armed_count` is a scalar in the existing `findings` JSONB.
- **The retirement checklist**, `SNAG-ESTATE-001`'s remaining half. A
  process, and an estate convention if it is anyone's — not this
  repository's to enforce.
- **`judge_attention` against a populated payload**, unchanged from
  Sessions 45 and its successor.
- **The tray toast**, the same gap Sessions 43–45 all left.

## SearXNG deployed mid-session, and the guard caught it within hours

`estate-manager` deployed SearXNG at **12:20 today**, while this session
was running. `tests/test_searxng_wiring.py` — pre-staged yesterday and
skipping until a unit existed — **went red on the next run**, naming its
own fix. That is the whole reason it was written instead of a comment.

**It is deliberately left red.** Wiring it is a different task from the
one this session was asked for, and the owner chose to leave the flag
flying rather than have it folded in.

What the deploy decided, so the next session does not have to re-derive
it — both blocked fields are now facts, not guesses:

- **`estate-manager-searxng-shim.service` is the unit to monitor**, on
  **port 8600**, serving `GET /api/health`. Its own unit file says so.
- `estate-manager-searxng.service` is the upstream container on **8601,
  loopback only**, and its comments say it deliberately has no health
  endpoint worth monitoring. Do not point the entry at it.

**The shim is `inactive (dead)` while the container is `active`.** 8601
answers 200; 8600 answers nothing. It is `enabled` and was never started.
That is `SNAG-ESTATE-001`'s own shape reproducing one layer up the same
afternoon — a unit ships, is enabled, nothing starts it, and the only
thing that noticed was a test written to notice.

Two consequences worth knowing before acting:

- **Uncommenting the entry while the shim is dead raises a truthful
  `searxng unreachable` alert immediately.** Start the shim first and
  confirm the health path against the running process rather than against
  the unit file's claim — the shim is estate-manager's code and this side
  has never seen its output.
- **Starting another repository's service is on that repository's side of
  the line.** It was not done here for that reason. If it stays dead, the
  honest report is that the estate deployed a surface that does not serve.

Both new units already appear in the sweep as `unmonitored` with
`restart_bounded=False`, so they join `SNAG-UNITS-002`'s fifteen the
moment the next sweep runs.
