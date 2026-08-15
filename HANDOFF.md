# Handoff — 2026-08-15

## Next action

Add `reschedule_job` to `sysadmin/core/scheduler.py` and call it from the reload path, which shrinks `RESTART_ONLY` from fifteen entries to three and closes `SNAG-RELOAD-001` by removing the divergence rather than reporting it better.

## This session — Session 49, the reload path

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

### Open follow-up

`SNAG-RELOAD-001` (P3) — after a reload the config object can hold a
scheduler setting the running scheduler does not obey, and
`requires_restart` says so **once**. It is the only defect on the list that
exists *because* of today's work, which is why it heads the ranking.
