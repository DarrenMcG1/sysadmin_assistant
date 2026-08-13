# Handoff — 2026-08-13

## Next action

Restart `sysadmin.service` (a **system** unit — `sudo systemctl restart`, not `--user`) to deploy Session 43, confirm the journal carries `schema_revision_verified` at revision 011 rather than a refusal, and then take `SNAG-DB-002`'s collation check as the next piece of work.

## This session

Session 43 closed `SNAG-DB-001`'s detection gap, all three parts,
committed as `8659be8`. The blackout itself was fixed on 2026-08-10 by
applying migration 009; the reason **nobody noticed for 39 hours** was
always the real defect.

### The open question the last handoff asked, and how it was settled

*Is an agent whose runs keep failing a new alert family, or an extension
of `% agent stalled`?* **A new family, sharing the ladder.** The deciding
argument is that the two are mutually exclusive by construction — a
failing agent is recording runs, so its `last_run_at` is fresh and
`summarise_agent` never marks it stalled — and their remedies differ: a
stall points at the scheduler or the process, a failure at the code or
the data. One title with two messages would put two faults behind one
line in the tray, the mistake `SNAG-AGENT-005` already recorded on the
log side.

**The risk the last handoff named turned out to be conditional, and the
condition is a naming one.** `RESOLVABLE_TITLE_PATTERNS` is an
*allowlist*, not a denylist — `% agent stalled` is structurally unmatched
rather than actively excluded. A new family is swept only if its title's
last word is one of the five in `SERVICE_ALERT_KINDS`. So the suffix
`agent failing` is load-bearing, and `tests/test_agent_failures.py` pins
it by emulating SQL `LIKE` against every pattern.

### Decisions taken, with the rejected option and why

- **The failure threshold is a count of runs, never a duration** — the
  opposite unit from `escalate_after_hours` in the same config section. A
  duration was rejected because `agent_runs` records a *run* rather than
  a schedule, so "failing for three hours" cannot tell an agent that is
  failing from one that is not running, and that is precisely the stall
  family's question. A time-based threshold silently re-merges the two
  families the design exists to separate. The cost is stated rather than
  hidden: a count is fast for a 60-second agent and slow for a daily one.
- **Two failures, not one** — the news worth raising is "reproducible",
  not "happened". One failure clears on the next run, which for
  `log_aggregator` is sixty seconds.
- **Refuse to start on a schema mismatch**, rejecting "start degraded and
  raise a critical": that writes the alert *through the schema that is
  wrong*, the loop the snag already demonstrated.
- **The head comes from alembic's own `ScriptDirectory`**, rejecting a
  regex over `alembic/versions/*.py` — a second implementation of the
  revision graph drifts from the very command the guard measures against.

### Three things discovered that the code does not say

1. **`agent_runs` held 0 `failed` rows across 39,762 runs, all-time.**
   Not health — Session 41's defect leaving a fingerprint, since
   `_record_outcome` used to write `status='failed'` into the transaction
   the failure had already destroyed. **Part (3) was therefore not
   implementable when the snag was filed.**

   That left it shipping with no production evidence, and rather than
   wait for a first natural failure — unbounded, since there has never
   been one — **both new mechanisms were exercised against the live
   database inside a transaction that was rolled back**, so nothing
   persisted and no toast reached the owner. Verified end to end:

   - one failure raises nothing (threshold 2); the second raises
     `service_discovery agent failing` at `warning` with the flattened
     error in the message and `failing_agent` / `consecutive_failures` /
     `kind` in details; a repeat run holds without duplicating; aging the
     quiet row past 24 h **resolves it and inserts a `critical`** rather
     than editing severity in place; a clean run resolves both. Residue
     afterwards: 0 alerts, 0 failed runs.
   - the savepoint against real asyncpg: a bad `status` raises
     `IntegrityError` **at savepoint exit rather than at `session.add`**,
     and — the part a mock cannot show — **the outer transaction survives
     it**, so the `error` fallback row writes and a service *after* the
     bad one still gets its row. A plain Postgres transaction would be
     poisoned at that point and every later statement would fail with
     "current transaction is aborted". That is exactly what turns a
     39-hour blackout into one bad tile. Residue: 0 rows.

   **What is still unproven is only the tray toast** — polling
   `/api/sysadmin/alerts` and fingerprinting on `{severity}:{title}`.
   That path is shared with the stall family and unchanged, and forcing
   it would mean committing a synthetic alert row to the live table,
   which is the pollution three previous sessions spent their time
   clearing. Left deliberately.
2. **A savepoint alone would not have caught the original fault.**
   `session.add` never talks to the database, so the
   `CheckViolationError` surfaced at the single commit ending the run.
   `begin_nested()` works only because *leaving the block flushes*.
   Anyone simplifying that loop later needs to know the flush is the
   mechanism, not the savepoint on its own.
3. **A savepoint rolls back SQL and nothing else.** An auto-restart
   already issued by `_handle_status` stands, and the in-memory streak
   counters stay bumped, so a counter can be one ahead and fire the next
   alert one check early. Accepted: the alternative buys accuracy only on
   a path that runs when the database is already rejecting writes.

### Two copies removed rather than a third added

`hours_since` and `humanise_hours` were verbatim duplicates the moment
`failures.py` existed; they moved into `sysadmin/core/escalation.py`
beside the ladder they clock, and a test fails if a private copy
reappears. `_consecutive_failures` became `_failure_streak`, returning
the count *and* the error text from one walk — two walkers would agree
today and diverge the first time someone changes how a `running` row is
treated, surfacing as "failed 3 runs in a row" beside an error from a
different incident.

### This session ran alongside estate-manager Session 4, and that shaped it

That session executed the project-state extraction here under ADR-0002's
founding-extraction exception, landing as `7467d2c` (estate side
`6c59be7` + `26a5685`, Alfred `d062c41`). **That exception is now closed**
— from here, estate sessions write documents and pointers into this
repository only, and anything needing sysadmin code arrives as a
delegated requirement rather than someone else's commit.

Things worth keeping from working concurrently:

- `docs/adr/0005-project-state-leaves.md` **arrived from that session**,
  not this one.
- Preflight reported a clean tree; twenty minutes later the tree was
  non-importable. The two sessions' changes were entangled in `main.py`,
  where splitting by file leaves a broken intermediate **whichever way
  round**. The asymmetry that resolved it: their cutover was
  self-consistent alone, ours was purely additive to their files. So the
  four shared hunks were backed out to JSON, their commit landed green,
  and the hunks were replayed. Two green commits, full attribution, one
  short deliberate broken window. **This is the pattern to reuse.**
- **Four defects were found by reading their work and handed over rather
  than fixed here**: the stale reason on `agents.project_organiser.enabled`;
  the autogenerate trap (an exclusion added only to
  `tests/test_schema_drift.py` leaves `alembic revision --autogenerate`
  willing to emit `op.drop_table` for frozen data — green test, loaded
  gun); the three-way `AGENT_NAMES` pairing break; and `main` left red
  because `uv run pytest` was treated as *the* gate in a repository with
  three. The last is now `SNAG-CI-001`, filed by that session.
- **One report of ours was wrong**: the `sysadmin/registry/` deletions
  were reported as staged and were unstaged. They had already spotted it
  and amended, so `adc8568` no longer exists and became `7467d2c`. Worth
  knowing if an old hash turns up in a note.

### Correction issued, and acted on

Earlier advice — "keep both `AGENT_NAMES` and the `agent_schedules`
entry" — was **incomplete**. A third link exists:
`test_job_ids_match_the_scheduler_registration` asserts every
`agent_schedules` job id appears in the lifespan, and
`project_organiser_scan` had left it. Removing the name from
`AGENT_NAMES` does not fix it and must not be done — `chk_alert_agent` is
add-only and historical rows carry that agent. The resolution was to
break the *identity* in the middle link: `AGENT_NAMES` is "agents the
`alerts` table admits, ever", `agent_schedules` is "agents this daemon
schedules today", and they stopped being the same question at the
cutover. `agent_schedules()` dropped the entry and
`test_covers_every_agent` became containment.

**Removing the entry rather than leaning on `enabled: false` was the
point.** That flag did hold the fault off, since the stall test gates on
`schedule.enabled` — but it made a config line load-bearing for a
structural fact, justified by a reason the cutover retired. A config
value is the wrong place to record "this agent does not exist here".

## Open, in order

1. **`SNAG-DB-002`** — every database on this box has a stale collation
   version, and a text-index lookup can miss a row that is present. Two
   halves: the **check** belongs in the sysadmin agent by the snag's own
   argument and is small; the `REINDEX` is ops work touching two other
   apps' data and wants a quiet window.
2. **`SNAG-ESTATE-001`** — looks already resolved and should be verified
   and closed rather than worked.
3. **`SNAG-TRAY-006`** (new) — nothing tests that the 8400 producer still
   satisfies the tray's parse of the project routes. Filed with its
   diagnosis corrected: the two shapes are **not** duplicates to collapse
   into estate-lib, they are a consumer's tolerant parse versus a
   producer's enforced guarantee, and merging them pushes the tray's
   defensiveness onto the producer. The gap is a consumer-driven contract
   test, which a shared class would hide behind an appearance of safety.
4. **`SNAG-DB-003`** (new) — the autogenerate exclusion hand-copied
   across `alembic/env.py` and `tests/test_schema_drift.py`. Mitigated,
   not fixed: `env.py` cannot import from `tests/`, and the right home
   for a shared constant is a judgement call Session 43 had no mandate to
   take.
5. **`SNAG-SYSD-003`** — `sysadmin.service` still orders itself after
   `ollama.service`, retired three weeks ago. The honest question is
   whether it should order against `alfred-inference.service` at all.
6. **The fourth `SNAG-DB-001` item**, still open: a live-database test
   path for the shared snapshot query. The suite mocks every session, so
   the freshness filter's *effect* is unobservable.

## State at close

Working tree clean at `ce99be1`. All three gates green and checked
directly rather than reported: `uv run pytest` 1422 passed,
`uv run ruff check .` clean, `uv run mypy sysadmin` clean across 75
source files. The schema guard was additionally verified against the live
database — passes at 011/011, and refuses a forced mismatch naming both
revisions and the remedy — and the failure family and the savepoint were
both exercised against the live database in rolled-back transactions (see
above). **Not yet deployed**: the daemon serves start-time code, so none
of this is live until the restart above.
