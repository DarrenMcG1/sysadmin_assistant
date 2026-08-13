# Handoff — 2026-08-13

## Next action

Back out Session 43's two `sysadmin/main.py` hunks and two `sysadmin/core/config.py` hunks the moment the estate-manager session says it is ready to commit, so its cutover lands green and self-contained, then re-apply them and commit Session 43's three `SNAG-DB-001` detection fixes.

## This session

Session 43 closed `SNAG-DB-001`'s detection gap, all three parts. The
blackout itself was fixed on 2026-08-10 by applying migration 009; the
reason **nobody noticed for 39 hours** was always the real defect.

### The open question the last handoff asked, and how it was settled

*Is an agent whose runs keep failing a new alert family, or an extension
of `% agent stalled`?* **A new family, sharing the ladder.** The
deciding argument is that the two are mutually exclusive by
construction — a failing agent is recording runs, so its `last_run_at`
is fresh and `summarise_agent` never marks it stalled — and their
remedies differ: a stall points at the scheduler or the process, a
failure at the code or the data. One title with two messages would put
two faults behind one line in the tray, which is the mistake
`SNAG-AGENT-005` had already recorded on the log side.

**The risk the last handoff named turned out to be conditional, and the
condition is a naming one.** `RESOLVABLE_TITLE_PATTERNS` is an
*allowlist*, not a denylist — `% agent stalled` is structurally
unmatched rather than actively excluded. A new family is swept only if
its title's last word is one of the five in `SERVICE_ALERT_KINDS`. So
the suffix `agent failing` is load-bearing, and
`tests/test_agent_failures.py` pins it by emulating SQL `LIKE` against
every pattern.

### Decisions taken, with the rejected option and why

- **The failure threshold is a count of runs, never a duration** — the
  opposite unit from `escalate_after_hours` in the same config section.
  A duration was rejected because `agent_runs` records a *run* rather
  than a schedule, so "failing for three hours" cannot tell an agent
  that is failing from one that is not running, and that is precisely
  the stall family's question. A time-based threshold silently
  re-merges the two families the whole design exists to separate. The
  cost is real and stated rather than hidden: a count is fast for a
  60-second agent (two minutes) and slow for a daily one (two days).
- **Two failures, not one.** One failure clears on the next run — for
  `log_aggregator` that is a warning toast with a 60-second life. The
  news worth raising is "reproducible", not "happened".
- **A stalled agent is never also reported as failing**, and the
  handover is automatic: an agent that fails and then stops being
  scheduled has its failure row resolved in the same run as its stall
  row opens, so one fault shows one alert rather than two criticals.
- **Refuse to start on a schema mismatch**, rejecting "start degraded
  and raise a critical" — that writes the alert *through the schema
  that is wrong*, which is the loop the snag already demonstrated.
  Refusing puts the unit into `failed`, where `StartLimitBurst=5` makes
  it terminal and `sysadmin-failed.service` announces it. This is the
  Session 39 machinery's second caller.
- **The head comes from alembic's own `ScriptDirectory`**, rejecting a
  regex over `alembic/versions/*.py`: a second implementation of the
  revision graph drifts from the very command the guard measures
  against.

### Three things discovered that the code does not say

1. **`agent_runs` held 0 `failed` rows across 39,762 runs, all-time.**
   That is not health, it is Session 41's defect leaving a fingerprint —
   `_record_outcome` used to write `status='failed'` into the
   transaction the failure had already destroyed. **Part (3) of this
   snag was therefore not implementable when the snag was filed**, and
   it is still being deployed against zero live evidence: nothing has
   failed since the fix. Correctness rests on tests, not on production
   confirmation, and the first real failure is worth watching for.
2. **A savepoint alone would not have caught the original fault.**
   `session.add` never talks to the database, so the `CheckViolationError`
   surfaced at the single commit ending the run. `begin_nested()` works
   only because *leaving the block flushes*, forcing each service's
   rejection to surface while its own savepoint is innermost. Anyone
   simplifying that loop later needs to know the flush is the mechanism.
3. **A savepoint rolls back SQL and nothing else.** An auto-restart
   already issued by `_handle_status` stands, and `_degraded_counts` /
   `_failure_counts` stay bumped — so a streak counter can be one ahead
   and fire the next alert one check early. Accepted deliberately: the
   alternative buys accuracy only on a path that runs when the database
   is already rejecting writes.

### Two copies removed rather than a third added

`hours_since` and `humanise_hours` were verbatim duplicates the moment
`failures.py` existed. They moved into `sysadmin/core/escalation.py`
beside the ladder they clock — the module's own founding argument — and
a test fails if a private copy reappears. `_consecutive_failures` became
`_failure_streak`, returning the count *and* the error text from one
walk: two walkers would agree today and diverge the first time someone
changes how a `running` row is treated, surfacing as "failed 3 runs in a
row" beside an error from a different incident.

### This session ran alongside a concurrent one, and that shaped it

`estate-manager` Session 4 was editing this repository throughout,
executing the project-state extraction under the founding-extraction
exception. Consequences worth knowing:

- `docs/adr/0005-project-state-leaves.md` **arrived from that session**,
  not this one.
- Preflight reported a clean tree; twenty minutes later the tree was
  non-importable. Two `main.py` hunks written early were **backed out**
  and re-applied at the end so that session's commit stayed purely its
  own.
- Three defects were found by reading their work and handed over rather
  than fixed here: the stale reason on `agents.project_organiser.enabled`
  (the flag is fine; its comment justifies itself by a fact about to
  become false), the **autogenerate exclusion trap** (an exclusion added
  only to `tests/test_schema_drift.py` leaves `alembic revision
  --autogenerate` willing to emit `op.drop_table` for frozen data —
  green test, loaded gun), and the three-way pairing break below.
- `SNAG-DB-003` was filed here at their request, covering the
  hand-maintained mirror between `alembic/env.py` and
  `tests/test_schema_drift.py`.

### One correction issued to that session, and acted on

Advice given earlier — "keep both `AGENT_NAMES` and the `agent_schedules`
entry" — was **incomplete**, and the missing half surfaced as a failing
test.
There is a third link in the chain: `test_job_ids_match_the_scheduler_registration`
asserts every `agent_schedules` job id appears in the lifespan, and
`project_organiser_scan` has left it. Removing the name from
`AGENT_NAMES` does not fix it and should not be done — `chk_alert_agent`
is add-only and historical rows carry that agent. The resolution is to
break the *identity* in the middle link, because the two sets have
stopped answering the same question: `AGENT_NAMES` is "agents the
`alerts` table admits, ever" and `agent_schedules` is "agents this
daemon schedules today". They were identical until this cutover.

That session agreed, and the change is **made**: `agent_schedules()` no
longer carries `project_organiser`, and `test_covers_every_agent` became
`test_every_scheduled_agent_is_one_the_alerts_table_admits`, asserting
`set(schedules) <= set(AGENT_NAMES)`. The direction still matters and is
still tested — an agent scheduled but *absent* from `AGENT_NAMES` would
raise alerts the database rejects, which is the fault migration 007 was
written for.

**Removing the entry rather than leaning on `enabled: false` was the
point.** That flag did hold the fault off, since the stall test gates on
`schedule.enabled` — but it made a config line load-bearing for a
structural fact, and its own comment justified it by a reason (double
scanning against `sysadmin-organiser.timer`) the cutover retired. A
config value is the wrong place to record "this agent does not exist
here". Anything asserting on the *report* now counts `SCHEDULED_AGENTS`,
because `build_self_report` iterates the schedules.

## Blocked / waiting on

- **The suite is green — `uv run pytest` is 1422 passed** as of the end
  of this session, including Session 43's 72 new tests. That is the
  *combined* tree: the estate-manager cutover landed in the working tree
  while this handoff was being written, so the number reflects both
  sessions and neither is committed yet.
- **`ruff check .` still fails on 5 files, all from the other session** —
  `sysadmin/units/router.py`, `sysadmin/units/agent.py`,
  `sysadmin/monitor/services.py`, `sysadmin/monitor/routers/projects_managed.py`
  and `tests/test_services_registry.py`. CI runs `ruff check .`, so
  nothing should be committed until those clear. Session 43's own files
  are `ruff` and `mypy` clean (75 source files), and the schema guard is
  verified against the live database: passes at 011/011, refuses a forced
  mismatch naming both revisions and the remedy.
- **Step 1 of the handover is DONE and the tree is in the deliberate
  broken window.** Session 43's two `main.py` hunks and two `config.py`
  hunks are backed out, saved verbatim to
  `<scratchpad>/session43-hunks.json`; both files verify as carrying only
  the other session's work (`config.py` one hunk, `main.py` nine, `ruff`
  clean). **`monitor/agent.py` and `monitor/failures.py` currently read
  `config.self_monitor.failure_alert_threshold`, which does not exist —
  so the suite is expected to fail until the hunks go back.** If this
  handoff is being read *before* the re-apply, that is the first thing to
  do: replay the JSON and re-run.
- **The two sessions cannot both commit atomically**, because the
  changes are entangled in `sysadmin/main.py`. Splitting by file leaves a
  broken intermediate whichever way round: the estate-manager session
  taking `main.py` whole gets `await verify_schema_revision()` without
  `schema_guard.py`, and Session 43 taking it whole gets the project
  wiring removed while `sysadmin/projects/` still exists. The asymmetry
  that resolves it is that **the cutover is self-consistent alone,
  whereas Session 43's changes are purely additive to the other
  session's files** — so the agreed sequence is: back out Session 43's
  four hunks in `main.py` and `config.py`, let the cutover commit green,
  then re-apply and commit. The back-out has been rehearsed once already
  this session and the diff is kept in the scratchpad. **Do not run the
  suite between those two steps** — `monitor/agent.py` reads
  `config.self_monitor.failure_alert_threshold`, which will not exist,
  and the failures would be an artefact of the handover rather than of
  either session's work.
- **Not started**: the fourth item on `SNAG-DB-001`'s list, a
  live-database test path for the shared snapshot query. Still open, and
  still worth one integration test.
- **Two snags filed for others to pick up**, both handed over by the
  estate-manager session rather than found here: `SNAG-DB-003` (the
  autogenerate exclusion hand-copied across `alembic/env.py` and
  `tests/test_schema_drift.py`, where the silent direction leaves
  `--autogenerate` willing to emit `op.drop_table` for frozen data) and
  `SNAG-TRAY-006`. The second was filed with its **diagnosis corrected**:
  it was handed over as "one shape defined in two repositories", and the
  two are not duplicates but different jobs — `contracts.py` is a
  consumer's tolerant parse where a `ValidationError` means "connection
  lost", the estate's is a producer's `response_model=` guarantee.
  Merging them makes the tray's defensiveness the producer's problem.
  What is missing is a consumer-driven contract test, which a shared
  class would appear to provide and would not.
