# Agent runs — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**One savepoint per service, and it works because leaving the block
flushes.** `SysAdminAgent._execute` used to add all nineteen services'
rows to one session and commit once, so one `CheckViolationError` aborted
the lot. `session.add` never talks to the database — the rejection
surfaced at that single commit, by which point the bad row was
indistinguishable from the eighteen good ones. `session.begin_nested()`
forces it to surface while that service's own savepoint is innermost.

Three consequences. A rejected service is written as `status="error"`
with `details['source'] = 'write_isolation'`, because **absence of a row
is what made the hole invisible** — the same rule `_record_outcome`
learned in Session 41. It is added to `unhealthy`, so `_resolve_recovered`
cannot announce a recovery nobody observed. And `details['write_failures']`
**names** the services rather than counting them. The honest limit: a
savepoint rolls back SQL and nothing else — an auto-restart already
issued stands, and the in-memory streak counters stay bumped.

**"Has not run" and "ran and failed" are two alert families, not one
title with two messages** (Session 43). `sysadmin/monitor/failures.py` is
a **sibling** of `stalls.py` sharing `core/escalation.py`'s ladder, and
the two are mutually exclusive by construction: a failing agent is
recording runs, so its `last_run_at` is fresh and `summarise_agent` never
marks it stalled. `_check_agent_health` reads **one** snapshot of
`agent_runs` and `alerts` and hands it to both — two fetches could
disagree about the same agent, and that mutual exclusion is only sound if
they are looking at the same data.

Four rules. **The suffix `agent failing` is load-bearing**: `failing` is
not one of `SERVICE_ALERT_KINDS`, which is the only thing keeping these
rows out of `_resolve_recovered`'s reach — a family ending in
`degraded`/`warning`/`critical`/`unreachable`/`auto-restarted` would have
its rows closed by the sysadmin agent while they were still true, and a
test pins it. **The threshold is a count of runs, never a duration** —
deliberately the opposite unit from `escalate_after_hours` in the same
config section, because `agent_runs` records a *run* rather than a
schedule, so "failing for three hours" cannot tell a failing agent from
one that is not running, which is the stall family's question. The cost
is stated rather than hidden: a count is fast for a 60-second agent and
slow for a daily one. **Two failures, not one**, because the news is
"reproducible" rather than "happened". **The handover is automatic** — an
agent that fails and then stops being scheduled has its failure row
resolved as the stall row opens, so one fault shows one alert.

This family **could not have been written before Session 41**:
`_record_outcome` wrote `status='failed'` into the transaction the failure
had already destroyed, so `agent_runs` held no failure rows at all — 39,762
runs and zero failures, which reads as perfect health off a table that
could not express the opposite.

**A unit failure also leaves an alert row, and the write is only half of
it.** `sysadmin/core/unit_failure.py` runs *while the application is
dead* — so no async engine, no `BaseAgent.raise_alert`, no event bus; it
uses the **sync** engine that exists for Alembic. `agent` is `'sysadmin'`
because `chk_alert_agent` admits only the five agent names, and
`details['source'] = 'systemd_onfailure'` carries the provenance `agent`
cannot: the sysadmin agent did not raise this, it was dead, which is the
news. A sixth constraint value was rejected — it would name a script
rather than an agent and make `self_monitor.AGENT_NAMES` wrong, and those
two are pinned together by `tests/test_units_api.py`.

**The lifespan resolves it, and that pairing is what makes the row
legitimate.** The service starting *is* the recovery, and it is the only
moment that fact exists — nothing observed the failure from inside. Without
the resolve this is an alert type that can only accumulate, which is how
1,664 orphaned rows happened; dedup on an open row is safe *only* because
of it. `OWN_UNIT` is named in three files (the constant, the unit's
`ExecStart=`, the script's default) and a mismatch does not error — one
side writes `sysadmin.service failed` and the other resolves
`sysadmin failed`, so the row is simply never closed.

**`BaseAgent.run` runs in three transactions, and the count is the
invariant** (Session 39's snag, fixed Session 41). It used to open one
session, insert the `running` row, **flush** it — which starts a
transaction — and hand that same session to `_execute`. This host sets
`idle_in_transaction_session_timeout=1min`, so any agent whose work
outlasts a minute has its backend terminated and loses every write of the
run. The file organiser scanned for 117.71 s on 2026-08-11, found 25,317
issues, logged `agent_run_completed`, and wrote **nothing**: no audit, no
`completed` row, and no `failed` row either.

That last one is the half worth remembering. The `except` branch sets
`status='failed'` on a row living in the transaction the failure
destroyed, so **the failure record dies with the run it records** — an
agent failing this way is indistinguishable from one that was never
scheduled, which is what `GET /api/sysadmin/self` reported for five days,
correctly, off a table that was being emptied. The one surviving run is
the proof rather than the exception: 2026-08-06 took **29.63 s**, the only
run in the agent's life to finish inside the timeout.

Now `_record_start` commits alone, `_execute` gets a session that has
**never been flushed** — so its transaction opens at its first statement
rather than two minutes earlier — and `_record_outcome` is an `UPDATE` by
id from a third. It costs nothing because `UUIDPrimaryKeyMixin` sets
`default=uuid.uuid4` client-side: the id exists before the INSERT is sent.
`tests/test_agent_run_recording.py` asserts the transaction count, because
collapsing them back is the defect.

Two changes of meaning, both deliberate. `_execute`'s writes are no longer
atomic with the run record — still atomic with each other — and a process
killed mid-run leaves a permanent `running` row where it used to leave no
row at all. The second is an improvement for the same reason as the first:
absence of a row is the thing that cannot be told apart from absence of a
run. Note the rule already existed one layer up, in `files/review.py`
("commit the read transaction before calling the LLM") — learned for
inference and never generalised to the framework beneath it.

**That permanent `running` row is closed now, and the value for it had
been sitting in the constraint since migration 001** (Session 159b,
`SNAG-DB-006`). `chk_run_status` admitted `cancelled` and nothing wrote
one; the entry named two *opposite* fixes — drop the value or fill it —
and nothing recorded which was intended. The seven live rows decide it:
each is followed by a **clean** daemon death within **0.032–61.2 s** and
for each the next `agent_run_completed` for that agent comes from a
**different PID**. Against a base rate of **0.401 %** (162 of 40,383
`completed` runs) the separation is total, and `file_organiser` — the
widest exposure at ~108 s a scan — is **0 of 112** completed against
**3 of 3** stuck. So the value has a referent, at **4.9 %** of daemon
deaths. `sysadmin/core/abandoned_runs.py` is the sweep.

Six rules, four of them the opposite of the obvious implementation:

1. **It runs at *startup*, which is a third shape the entry does not
   name, and the discriminator is a race rather than coverage.** A
   shutdown-path write is what anyone reaches for and
   `scheduler.shutdown(wait=False)` returns while the worker thread is
   still inside `_execute` — three of the seven had 30–60 s of scan left
   — so it can land *after* a `completed` that thread commits. A startup
   sweep cannot race a process that is gone, and it is
   `core/unit_failure.py`'s argument one table over: the service
   starting is the only moment at which "that run will never finish"
   exists. Its reach into SIGKILL and power-off is **theoretical and
   says so** — all ten crash deaths in the journal died 2.1–4.8 s in
   (`SNAG-DB-005`'s schema-guard refusals), before the scheduler could
   fire anything, so on the live population both shapes reach 7 of 7.
2. **The instance id is minted in-process, never read from the
   environment.** systemd stamps `INVOCATION_ID` into this unit and it
   would do the job; this service reads no environment variables, and a
   lone exception is a convention that has stopped being one. A
   per-process UUID is also more general — an agent driven by hand from
   a session gets an identity, where an environment read gives every
   such drive the same absent value.
3. **A row with no stamp is refused, not swept**, which is what makes
   the fix forward-only *by construction* rather than by a constant. The
   seven predate the stamp, so the sweep cannot attribute them;
   `refused` **counts** them, because zero-because-blind must not read as
   zero-because-clean (`ports_checked`'s rule). The obvious alternative
   — an age cutoff — is an invented constant expressing a fact the row
   already carries.
4. **Nothing is capped and it cannot need to be.** The sweep runs on
   every start, so what it finds is one instance's in-flight runs, which
   `max_instances: 1` bounds; what is *logged* is the agent names, held
   at five by `AGENT_NAMES` whatever the volume, with `count` carrying
   it. `details['truncated_sources']`' rule.
5. **The status is a literal pinned to the constraint, not derived.**
   The constraint lists four values and says nothing about which means
   "abandoned", so `STATUS_READINGS`' treatment does not transfer; a test
   asserts `chk_run_status` still admits it, so a migration dropping the
   value — the entry's *other* fix landing by accident — is a red test
   rather than an `IntegrityError` on the next restart.
6. **It reports and never refuses.** Caught in the lifespan for
   `resolve_unit_failures`' reason and the exact opposite of
   `schema_guard`'s: a stale `running` row is worth less than a boot.

Verified live because the path had never run here: restart 1 gave
`abandoned_runs_unattributable count=7` and no closures, then a
`POST /api/files/scan` killed 2 s in gave restart 2
`abandoned_runs_closed count=1 agents=['file_organiser']` — the first
`cancelled` row in this database's life, carrying the dead instance's id
beside `cancelled_by: startup_sweep`.

**Three of thirteen falsifications passed against deliberately broken
code, and the first is the one worth carrying.** Deleting the
`IS NOT NULL` conjunct changed **nothing**: `NULL <> 'x'` is `NULL`, so
rule 3's refusal was being carried by SQL's three-valued logic rather
than by the clause written for it. The clause stays — its visibility is
what stops a reader "fixing" the NULL case with a `COALESCE` and
sweeping the seven silently — and it is pinned by **compiling the
statement**, because a clause whose removal is invisible in behaviour
cannot be reached by a behavioural test. The other two are the shapes
this repository keeps finding: `status == CANCELLED_STATUS` compared the
module's constant to itself, and **nothing drove `_record_start`**, so
deleting the stamp passed all twenty tests while the sweep went on being
proved correct about rows nothing in production would produce.
