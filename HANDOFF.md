# Handoff — 2026-08-15

## Next action

Take `SNAG-DB-003` — the autogenerate exclusion list is hand-copied between `alembic/env.py` and `tests/test_schema_drift.py`, and an exclusion present only in the test leaves the guard green while the next `alembic revision --autogenerate` writes `op.drop_table('project_snapshots')` into someone else's migration.

## This session — Session 50, the reload re-times the scheduler

`SNAG-RELOAD-001`, which Session 49 filed against itself yesterday and
which is closed here by **removing** the divergence rather than reporting
it better. The entry offered two mitigations and named a third option in
its last line; the third is what shipped.

Suite **1771 passed** (from 1733), ruff and mypy clean, **no migration**,
**no new route**.

### What the entry proposed, and why neither mitigation was built

Storing the last `ReloadReport` and serving it is a field nobody polls —
`SNAG-CFG-001`'s shape exactly. Raising it as an alert row is the right
*shape* but needs a settled dedup and resolve lifecycle before it is
written, which is a session of its own; and both still only **describe** a
divergence this repository can simply not have. Before the reload existed,
startup built the config object and the scheduler from one read and they
could never disagree — so the honest fix restores that property rather
than narrating its absence.

### The obvious implementation is a line shorter and breaks the schedule

`reschedule_job` recomputes the next fire from **now**. Re-applying every
job on every reload therefore leaves a 24-hour job permanently 24 hours
from the most recent reload — which on a box being poked at is never. That
is `agent_first_run_delay_seconds`'s failure (SNAG-AGENT-003) with a reload
standing in for a restart.

So an unchanged trigger is left **untouched**, and "unchanged" is decided
against the **live** job rather than a remembered plan. A remembered plan
is a second statement of what the scheduler is doing, and two statements
that can disagree is precisely what this snag was.

### Three decisions taken, and what each rejected

- **A plan in `core`, not a fourth composition root.**
  `sysadmin/core/jobs.py` imports no domain and knows no agent — the
  callables arrive as `JOB_TARGETS` from `main.py`. So that file owns
  *what* runs and this one owns *when*, and `tests/test_jobs.py` asserts
  the two sets match exactly: planned-and-unwired is a `KeyError` at
  startup, wired-and-unplanned never runs and looks identical to one that
  does. Rejected: a `sysadmin/jobs.py` beside `main.py` and `reload.py`,
  which would have been a third composition root for a module that needs
  none of the licence.
- **Converging `sync_*` methods, with no separate "add" left.** A caller
  holding both has a decision to take, and taking that decision away from
  the two roots that schedule anything is the point. `schedule_interval`
  and `schedule_cron` are gone rather than kept beside them.
- **A job being *added* gets the first-run delay; a job being *re-timed*
  does not.** Added means this process has never scheduled it — a cold
  start or an agent just re-enabled — and `IntervalTrigger` alone puts the
  first fire an interval out. Re-timed already has a next fire, and pulling
  it forward turns an unrelated threshold edit into a 118-second
  filesystem scan nobody asked for.

### The guard test was rescued, and rescuing it found a defect in the guard

`tests/test_reload.py` walks the lifespan by AST and requires every config
path read there to be classified. Moving fifteen of those reads into
`core/jobs.py` would have hollowed it out **silently** — the assertion
would have gone on passing over a shrinking population. It now walks both
functions, and gained a second half: each `JobSpec`'s declared
`config_paths` must equal what `plan_jobs` actually reads.

Writing that showed the walker treats `delay =
schedules.agent_first_run_delay_seconds` as an alias assignment. It is
syntactically identical to `agents = config.agents` and semantically the
opposite, so a real leaf was being dropped without a word — the guard
failing in exactly the direction it exists to catch. An assignment now
counts as an alias only if the name is later used as an attribute base,
and `test_a_leaf_read_into_a_local_is_not_mistaken_for_an_alias` pins it.

Three source-grep tests elsewhere were converted to real assertions
against the plan rather than substring matches on `main.py`:
`test_scheduler`, `test_self_monitor` and `test_estate_judge_wiring`. All
three would have kept passing while meaning nothing.

### `RESTART_ONLY`: fifteen leaves to two prefixes

`service` and `database`, covering the socket, the logging setup and the
engine — genuinely immutable in-process, and the report still names them.
The third classification is **derived**: `JOB_CONFIG_PATHS` comes from the
plan, so the no-syncer fallback cannot fall behind the jobs it describes.
`jobs_synced` carries the distinction `ports_checked` already encodes —
`jobs_retimed: []` is "nothing needed re-timing" when true and "the
scheduler was never looked at" when false.

### Verified live, not only against fixtures

In-process against the real `config.yaml` and a real
`BackgroundScheduler`, touching neither the daemon on 8500 nor the file:

- 999 s → `interval[0:16:39]`; `retention_purge` 03:00 → 04:00; a disabled
  `estate_judge` had its job **removed**, and re-enabling **added it back
  with the first-run delay**.
- `requires_restart` came back `[]` where Session 49 reported three leaves.
- The same reload run twice re-timed nothing — the idempotence the whole
  design turns on.
- With no syncer supplied, Session 49's behaviour exactly: `jobs_synced:
  false` and all three leaves named.

### The daemon is still two sessions behind, and it was measured

`POST /api/sysadmin/reload` **404s** against PID 1410826 (started 14:32
BST), so the running process predates Session 49 as well as this one. One
restart deploys both. Until it is run, **do not send that HUP** — the
running daemon has no handler and Python's default action is to die, with
`Restart=always` making it look like a reload that worked.

---

## Previous session — Session 49, the reload path

`SNAG-UNITS-005`'s durable half. Three sittings running had handed a
restart forward because the daemon reads `services.yaml` once, in the
lifespan. `sysadmin/reload.py` re-reads both configuration files on
`SIGHUP` or `POST /api/sysadmin/reload`.

Suite **1733 passed** (from 1708), ruff and mypy clean, **no migration**.

### The design question was real, and its premise was false

The session was scoped around *"what may safely reload — just
services.yaml, or config.yaml too, which holds thresholds the running
agents have already read"*. **They have not.** Every agent calls
`get_config()` inside `_execute` — `SNAG-AGENT-003` forbade agents a
startup hook because they run on scheduler threads with their own event
loops, and that constraint, written for event-loop safety, bought per-run
configuration for free. Only **fifteen** config leaves are genuinely read
once, and they are enumerable.

So the scope question answered itself and the interesting question moved:
not *whether* config.yaml may reload, but what to do about the fifteen.

### The blocker was privilege, not design

`sysadmin.service` is a **system** unit that runs `User=gaddi`, so the
owner may signal it without `sudo`. Probed with `kill -0`, which tests
permission without delivering — necessary, because Python's default
`SIGHUP` action **terminates**, so a HUP sent to a daemon predating the
handler is a restart wearing a reload's name.

`systemctl reload` would additionally need an `ExecReload=` line in the
unit file and *that* edit does need `sudo`. The raw signal does not, which
is why the signal is the half that removes the blocker.

### Three decisions taken, and what each rejected

- **Both files, naming what was ignored** — rather than refusing the
  config half when a restart-only field moves. Refusing blocks a threshold
  fix on an unrelated edit in the same file, and the operator then restarts
  anyway, so the refusal delivers nothing the restart did not.
  Half-success is dangerous when **silent**; this names the changed
  *leaves* (not the prefixes — `schedules` changed is not an answer) in the
  body and in a `WARNING` log line, which is the only report the SIGHUP
  path has.
- **`SIGHUP` and an authenticated `POST`, one shared function.** The signal
  is the path needing no `sudo`; the endpoint is the only one that can
  *return* the report, and the only straightforwardly testable one. A
  signal handler can log and nothing else.
- **Prune per-service in-memory state, never reset it.** Resetting
  `_degraded_counts` re-arms the three-poll streak that gates an alert, at
  the moment an operator is most likely to be reloading *because*
  something is failing. What must go is a name removed and later re-added,
  which would otherwise resume a streak measured against a different
  declaration.

Rejected outright: **rescheduling jobs in the same sitting.** It is the
right fix and it is filed (see Next action) — but `Scheduler` exposes no
`reschedule_job`, and a reload that silently re-times the estate's cron
jobs is a larger change than this session was scoped for.

### The rule that decided where it lives

`sysadmin/reload.py` composes `core.config` with `monitor.services`, and
`tests/test_import_boundary.py` forbids `core` from importing a domain —
the rule that makes every other boundary real. `metadata.py` had already
settled the placement in prose (*"composition roots… no domain imports
them"*) and **nothing checked it**; a fourth boundary test now does, for
`main`, `metadata` and `reload` alike. That is what forced
`POST /api/sysadmin/reload` into `create_app` rather than the sysadmin
router — the same place `scan-all` already sits.

### The guard that earns its place

`RESTART_ONLY` is a hand-written list of fifteen paths, and a
hand-maintained classification nothing checks is the `SNAG-CFG-001` shape.
`tests/test_reload.py` **walks `main.py`'s lifespan by AST** and requires
every config path read there to be classified either as restart-only or as
`LIVE_AT_STARTUP` with the reason it is read again later. A new scheduled
job reading a new field fails the suite until someone classifies it.

### Verified live, not only against fixtures

- The real `config.yaml` + `services.yaml` reload cleanly and idempotently:
  30 services, empty diff, `requires_restart: []`.
- **The exact blocked instance**: with Session 48's three entries removed
  to stand in for the running daemon, a reload of the real file reports
  them `added`, installs all three, `requires_restart: []`. Had this
  existed yesterday the restart would not have been owed.
- **Cross-file atomicity**: a broken `services.yaml` beside a valid
  `config.yaml` installs **neither** — the threshold stayed at its previous
  value rather than being half-applied.
- **The mixed edit**: one live field and two restart-only ones together →
  the threshold delivered, the other two named. This is what found
  `SNAG-RELOAD-001`.

### Two documents were stale, and the live box said so

Read before starting, per the standing rule, and both were wrong:

- **HANDOFF's `## Next action` said to run `sudo systemctl restart
  sysadmin.service`. It had already been run** — the daemon started 14:32
  BST (after the 13:40 commit) and `/api/sysadmin/status` serves all 30
  services including Session 48's three.
- **It then said to take `SNAG-AGENT-006`. That was fixed on 2026-08-14**,
  the day *before* the sitting that recommended it — the snag header says
  so, `tests/test_alert_dedup.py` exists, and three code sites cite it.

`roadmap.py` publishes that first line verbatim to the estate board, so a
next action that has stopped being true is published estate-wide.
`SNAG-ROADMAP-001` covers *placeholder* text, not text that was true and
went stale. Not filed here as a snag because the roadmap surfaces left for
estate-manager's 8400 service on 2026-08-13 — it is named as a runner-up
in STATUS.md instead, and the fix is likely theirs.

### One number corrected rather than incremented

STATUS.md's API cell claimed **57 routes**. Counted live: **44**
`APIRoute`s (43 before this session). The cell now carries the measured
figure and says what it used to claim.

### Blocked on sudo — unchanged, and no reload can reach it

`SNAG-UNITS-005` conflated a **deploy** blocker with an **ops** blocker.
Only the first is gone. The five system-scope orphan removals are
`systemctl disable` and `rm` under `/etc/systemd/system`:

```
sudo systemctl disable --now offline-agents-dashboard.service \
  && sudo rm /etc/systemd/system/offline-agents-dashboard.service
sudo systemctl disable --now personalassistant-backend.service \
  && sudo rm /etc/systemd/system/personalassistant-backend.service
sudo systemctl disable --now personalassistant-frontend.service \
  && sudo rm /etc/systemd/system/personalassistant-frontend.service
sudo systemctl disable --now ticktick-sync.timer ticktick-sync.service \
  && sudo rm /etc/systemd/system/ticktick-sync.timer \
            /etc/systemd/system/ticktick-sync.service
sudo systemctl disable --now ticktick-sync-db.service \
  && sudo rm /etc/systemd/system/ticktick-sync-db.service
sudo systemctl daemon-reload
```

**One restart is still owed, and it is the last of its kind**:

```
sudo systemctl restart sysadmin.service   # deploys the reload path itself
```

From then on `kill -HUP $(systemctl show sysadmin.service -p MainPID --value)`
reaches it without `sudo`, or `curl -X POST localhost:8500/api/sysadmin/reload`
for the report. Do **not** send that HUP before the restart: the running
daemon has no handler and would take the default action, which is to die.

### Open follow-up — closed by Session 50

`SNAG-RELOAD-001` (P3) was filed here and fixed the next sitting. See the
top of this document.
