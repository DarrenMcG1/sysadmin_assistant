# Handoff — 2026-08-13

## Next action

Run the two time-boxed checks recorded below first (did the estate's timers finally fire, and is `attention` ever populated), then take `SNAG-AGENT-006` — give the service and threshold alert families the dedup that `sysadmin/estate/agent.py` proved can coexist with a set-based sweep, by changing the exclusion set from the titles the run raised to the titles the run judged still true.

## This session

Session 45 built the **judging session** — `estate_judge`, a fifth agent
in a new `sysadmin/estate/` package. It is the half of the estate's
Session 4 cutover that was deliberately left behind: the estate manager
publishes and never acts, so until this runs it computes idle nudges
every night into a surface nothing reads.

**Deployed and verified in production** at 21:30:24, after the
rolled-back verification below. The first run at 21:31:24 read all four
surfaces, judged nothing and wrote nothing:

```
completed | findings=0 | raised=0
surfaces_read: [audit_invariants, projects_attention,
                projects_invariants, queue_invariants]
unread_surfaces: {}
by_surface: all zero
```

Zero is the correct answer at that moment — the scan and the audit had
both run within the hour, the queue was idle and `attention` was empty —
and it is also exactly what a wrong key name would produce, which is why
the narrowed-threshold dry run against the same live payloads was done
first. `GET /api/sysadmin/self` now lists five agents.

### It judges four surfaces, not the two the task named

The task named `/api/projects/invariants` and `/api/projects/attention`.
Two more were already live and already ours by somebody else's ADR:

- **`/api/audit/invariants`** — estate ADR-0009 requires sysadmin to
  judge the audit's own numbers, in the same words the global rules use:
  *the estate never grades its own audit*.
- **`/api/queue/invariants`** — ADR-0007, and `services.yaml`'s own
  comment beside `estate-manager-api` already said "exposed to be judged
  HERE … this repository's own upcoming task".

Hourly, not at the sysadmin agent's 300 s: the producers change twice a
day (scan 04:30, audit 05:03) and `/attention` re-walks ~26
`.project.yaml` manifests from disk on **every** request, so a 5-minute
poll would have the estate reading the filesystem 288 times a day to
serve unchanged data.

### The lifecycle rule that made a new agent worth it

`monitor/collation.py` records that dedup and a set-based resolve are
mutually exclusive. They are — **there**. That sweep's exclusion set is
the titles the run *raised*, so a deduplicating family raises nothing on
run two, has its still-true row resolved, then re-raised — and each flip
clears the tray's `{severity}:{title}` fingerprint and notifies again.

This agent's exclusion set is the titles the run **judged**, which is a
different set: dedup suppresses the raise, never the judgement. A fault
that persists is in `current` on every run and is never swept; a fault
that clears leaves `current` once and resolves once.

That is available **only** to an agent that owns every row it sweeps.
`_resolve_recovered` scopes on `Alert.agent == self.name`, so
`estate_judge` rows are unreachable from the sysadmin agent by
construction. It is the concrete argument for the new-agent choice over
a module inside the sysadmin agent, and it was not obvious before
reading that predicate.

### Decisions taken, with the rejected option and why

- **A cumulative total is never judged.** The queue publishes
  `dropped_total`, `expired_total` and `grants_total` as `count(*)` over
  the whole `gpu_leases` table. `dropped_total` is **already 1**, so the
  obvious `> 0` rule would have raised an immortal row on the first run
  — `redis unreachable`'s 6,283 and `Critical disk usage on /`'s 13,971
  arriving by a fourth route. Only `depth` and `oldest_waiting_seconds`
  are gauges. The totals ride in `details` as evidence.
- **`active_lease.hold_deadline` was considered and rejected**, and it
  was the one threshold that would not have to be invented. The
  arbiter's `tick()` calls `_expire_if_overdue` first, so an overdue
  lease visible to a poller means the tick loop is between ticks or
  dead — which needs a grace period, which is an invented number after
  all. The condition surfaces anyway as waiters piling up behind it.
- **Reachability is not judged.** `estate-manager-api` is an `http`
  entry in `services.yaml` polled every 300 s, with both estate timers
  beside it as `kind: timer`. Rejected: a "cannot judge" alert here — a
  second owner of one lifecycle closes a row while the first still holds
  it true, which is the defect this repository has now found at three
  scales. 8400 being down costs `details['unread_surfaces']`, which
  **names** the surfaces.
- **The sweep is scoped per surface.** Four independent surfaces from
  one process, so three answering while one 500s is a real state.
  Rejected: one global sweep, which would close every health breach and
  idle nudge on the strength of a payload nobody received.
- **Nudge severity verbatim, health severity ours.** The estate computes
  a nudge's rung on the ladder that moved with the domain. Rejected:
  re-deriving it here — two implementations of one ladder in two
  repositories. `health` publishes no severity at all (that machinery
  was deleted rather than ported), so a breach is `warning`, one rung,
  never `critical`.
- **`findings_total` is never judged.** 8 of today's 10 audit findings
  are stale collation versions this service already holds eight open
  rows for; a rule on the total would announce its own alerts through a
  second producer. What is judged is whether the audit **ran** —
  `checks_errored`, `publish_error`, `error`, age.
- **`base_url` duplicates `services.yaml` on purpose.** Rejected:
  deriving it from that entry, which would stop the judging silently
  when a service is renamed or set `monitor: false`. A test asserts the
  two agree instead — the difference between a comment and an
  enforcement.

### Two things found by reading the producer rather than trusting it

- **`asdict` drops properties.** `Nudge.title` and `Nudge.message` are
  `@property`, and `oversight.attention` serialises with
  `dataclasses.asdict`, which emits fields only. So the estate's
  "**the one place a nudge's title is built**" never reaches the wire,
  and this repository builds its own. Filed as `SNAG-ESTATE-002`; the
  fix is the estate's under ADR-0002, not ours.
- **`repos_skipped` is a thrown exception, not a benign skip.** That
  project writes no snapshot and vanishes from every project surface
  without being reported as gone — alertable. `undeclared` (9 of 26) is
  scored exactly like `active` and is a standing description of the
  estate, so a rule on it would open a row that stays open until
  somebody declares nine repositories they have chosen not to declare.
  Not judged.

### Found on the way, fixed in passing

- **`Alert.__table__`'s `chk_alert_agent` had never gained
  `service_discovery`** from migration 007 in Session 26. Harmless —
  nothing builds this table from metadata — which is also why nothing
  caught it: alembic's autogenerate does not diff CHECK constraints, the
  blind spot `core/schema_guard.py` records for its own reasons.
- **`test_units_api.py` pinned `AGENT_NAMES` to migration 007 by set
  equality**, so every new agent broke a test belonging to an unrelated
  session — a pin masquerading as an invariant. Split: 007 now asserts
  its own fact (containment), and
  `test_estate_judge_wiring.py::test_the_newest_constraint_migration_matches_agent_names`
  **finds** the newest widening migration itself and cannot rot.
- **A title collision the new partition test caught on its first run.**
  `Estate scan sources unreachable` matches `% unreachable` in
  `RESOLVABLE_TITLE_PATTERNS`. Not a live bug — that sweep scopes on
  `agent='sysadmin'` — but `collation.py` rule 4 settled that a title
  should be clear of those patterns *by construction rather than by
  luck*. Renamed to `Estate scan could not reach sources`.

### A delegated requirement arrived mid-session and is closed

A concurrent estate-manager session committed `fa51aac` into **this**
repository's `tasks.md` while this work was in progress: *"Watch and
judge the estate's audit agent"*, its ADR-0009 §8. That is ADR-0002's
delegation pattern working — the estate's bounded exception closed on
2026-08-13, so it may no longer edit this repository's runtime-read
config and recorded the requirement instead of making the edit.

Both parts are done:

- **Part 1** was genuinely undone and is now `estate-manager-audit-timer`
  in `services.yaml`.
- **Part 2** names audit age, `checks_errored` and `publish_error` — the
  same three `judge_audit_invariants` had already been built around,
  derived independently from reading the payload. Two parties reaching
  the same three fields is the closest thing to corroboration available
  across a seam.

**The two parts catch different faults and both were needed.** The
`services.yaml` entry catches a timer that stops firing; `estate_judge`
catches an audit that runs and goes wrong. Neither sees the other's, and
only the timer half was overdue.

### What is verified, and what is not

Against the **live** database and the **live** 8400, in transactions
that were rolled back:

```
dry run, real thresholds : 4/4 surfaces read, 0 judgements  (correct — and
                           indistinguishable from a key-name mismatch)
dry run, thresholds tight: 3 judgements off real values — scan age 857 s,
                           audit age 483 s, queue depth 0. This is what
                           proves the key names.
run 1 (faults present)   : raised=3  standing=3  resolved=0   open=3
run 2 (same faults)      : raised=0  standing=3  resolved=0   open=3
run 3 (faults cleared)   : raised=0  standing=0  resolved=3   open=0
run 4 (faults return)    : raised=3                            open=3
run 5 (scan surface dark): raised=0  resolved=0                open=3
residue after rollback   : 0 rows
```

Run 2 is the one that mattered — it is the flip-flop `collation.py` had
to avoid by staying out of the sweep entirely. Run 5 is the fails-closed
rule.

**Migration 012 is applied to the live database** (`alembic_version` =
012, constraint confirmed by `pg_get_constraintdef`). The running daemon
booted at 17:46:44 BST, ~90 seconds before this session began, so it is
serving pre-session code and `estate_judge` is absent from
`GET /api/sysadmin/self`.

**Not verified:**

- **Anything in production.** No restart has happened.
- **`judge_attention` against a populated payload.**
  `/api/projects/attention` has answered `{"health": [], "nudges": []}`
  every time anybody has looked, on both sides of the seam — the
  estate's own test asserts exactly that. Its rules are pinned against
  literals built from the producer's dataclass fields, which is the
  strongest evidence available and is not a capture.
- **`oldest_waiting_seconds`.** The live queue is idle, so that key has
  only ever been `null`. The null path is tested; the populated one is
  not.
- **The tray toast**, the same gap Sessions 43 and 44 both left.

## Two checks for tomorrow morning, both time-boxed to tomorrow

Neither is a task and neither should become one — both are observations
that are only available on 2026-08-14 and cost nothing to make.

**1. Did the estate's timers fire?** Neither has ever run:
`systemctl --user list-timers 'estate*'` showed `LAST PASSED: -` for all
three on 2026-08-13, so `scans_total` was **1** and that one scan was
`run_type: manual`. `estate-manager-scan.timer` is due 04:31 and
`estate-manager-audit.timer` 05:03.

```
systemctl --user list-timers 'estate*' --all
curl -s localhost:8400/api/projects/invariants | python3 -m json.tool
```

If either did not fire, `estate_judge` should have raised
`Estate scan stale` (or `Estate audit stale`) by about **06:35** —
26 hours after the last run on record. **That would be the first real
judgement this agent has ever made**, and it is worth more than the
successful case: it would confirm the whole path end to end — pull,
judge, raise, dedup — on a fault nobody planted. Check with:

```
psql -X -tAc "SELECT severity, title, created_at FROM sysadmin.alerts \
  WHERE agent='estate_judge' AND resolved=false ORDER BY created_at" projects
```

If the timers *did* fire, the agent correctly stays silent and the check
costs one command. Either answer is useful; the second answer is more so.

**2. Is `attention` ever populated?** `GET :8400/api/projects/attention`
has answered `{"health": [], "nudges": []}` every single time anybody has
looked, on **both** sides of the seam — the estate's own suite asserts
exactly that (`test_nudges_are_published_not_stored`). So
`judge_attention` is the one half of this agent that has never seen real
data, and its rules are pinned against literals built from the producer's
dataclass fields rather than from a capture.

```
curl -s localhost:8400/api/projects/attention | python3 -m json.tool
```

A nudge needs an eligible project whose stated next action has stood
**7 days** unchanged, computed on read from the latest snapshots — so a
scan that has actually run overnight is a precondition, which is why this
check follows the first one rather than standing alone. A health entry
needs a project scoring under its manifest threshold.

**If either list is non-empty, capture the payload verbatim** into the
`SNAG-ESTATE-002` entry before doing anything else with it. That is the
evidence neither repository currently has, it is worth more than the
alert it produces, and the shape it proves or disproves is
`asdict`-drops-properties — the finding that entry exists to record.

## Open, in order

1. **Restart and confirm** — the only thing standing between this and
   production. `sudo systemctl restart sysadmin.service`, then check
   `agent_runs.details->'by_surface'` on the first `estate_judge` row 60
   seconds later, and that `GET /api/sysadmin/self` lists five agents.
2. **`SNAG-AGENT-006`** — the raise-side pile-up. Both halves move
   together; `sysadmin/monitor/collation.py` is the worked example and
   `sysadmin/estate/agent.py` is now a second one, with the
   judged-versus-raised exclusion set written out.
3. **`SNAG-ESTATE-002`** (new) — the producer's nudge title never
   reaches the wire. Recorded here, executed in estate-manager.
4. **`SNAG-ESTATE-003`** (new) — no escalation for these families, and
   why inventing a third rung for this one alone is the wrong shape.
5. **`SNAG-ESTATE-001`** — looks already resolved; verify and close
   rather than work.
6. **`SNAG-TRAY-006`**, **`SNAG-DB-003`**, **`SNAG-SYSD-003`** and the
   fourth `SNAG-DB-001` item remain as the previous handoff left them.

## State at close

Committed as **`8220bcc`** (20 files, +2,630/−182) and **`0b8691f`**.
Note the parent is `fa51aac`, **not** the commit the previous handoff
named: a concurrent estate-manager session committed a delegated
requirement into this repository's `tasks.md` mid-session (ADR-0002's
delegation pattern working). Both its parts are done here.

All three gates green and checked directly rather than reported:
`uv run pytest` **1517 passed** (1455 + 62 new), `uv run ruff check .`
clean, `uv run mypy sysadmin` clean across 80 source files.
`./scripts/lint_check.sh` clean, and the pre-commit hook's own lint and
documentation checks both passed.

**Migration 012 applied and the daemon restarted at 21:30:24**, so both
halves are live. Still unverified, and unverifiable today: `judge_attention`
against a populated payload, `oldest_waiting_seconds` against a busy
queue, and the tray toast.
