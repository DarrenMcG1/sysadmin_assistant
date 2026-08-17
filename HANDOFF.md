# Handoff — 2026-08-17

## Next action

Restart `sysadmin` and spend the sitting observing what Sessions 63, 64 and 65 claim, because Session 62's ceiling fix at 14:09:16 is the last commit the running process contains and three consecutive sittings have now shipped green and unrun, so `-p`'s 40 % → 100 % efficiency, the `truncated_fraction` gate that should finally produce `noise` rows in `GET /api/logs/actions`, the readable titles from `format: json` and the new `covered_by` are four claims nobody has seen fire.

## Two sub-session items, and the first is the same restart

**`sudo systemctl restart sysadmin` — and a SIGHUP still will not do it.**
The daemon started **14:10:58** and is now **four commits behind**. Its
`LogRef` forbids extra fields and has no `format`, so driving the
*running* parser against the current `services.yaml` rejects it outright
— `services.13.log.format | Extra inputs are not permitted`. Session 49's
rule 1 means neither file would be installed, so the reload fails safely
and delivers nothing.

The restart is also what **disarms `SNAG-LOG-004`**: the running process
still crashes its whole `log_aggregator` run on the first `ERROR` line
this daemon writes, self-sustainingly. Still untriggered — the journal
holds no `ERROR` line since 14:10:58 — so the box remains one traceback
away from a silent, permanent log blackout.

**Still owed from Session 63, still two minutes.** Both rows are still
open, checked this sitting. They need resolving so Session 57's `info`
rung can reach them (`SNAG-ESTATE-010`):

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

## This session — Session 65: one fault had two speakers, and the entry undercounted them

The sitting was `SNAG-LOG-005` as the handoff named it: decide which
single family owns "this daemon's agent failed". The answer is
`sysadmin/monitor/failures.py`, and the log aggregator now defers to it
by name.

**The decision was made from the journal rather than from the entry**,
which turned out to matter. 713 `ERROR`/`CRITICAL` lines from this daemon
resolve to **249 incidents** and 5 signatures, and three facts came out
of counting them:

- **The collision was four rows, not two.** 215 of 215 incidents fired
  `agent_run_failed`, `scheduler_job_error` **and** apscheduler's own
  `Job "…" raised an exception` in the same second. Only two of those can
  recur, because Session 41 made `_record_outcome` survive a failed run —
  so the entry was right by accident.
- **Candidate (b) is refuted.** Excluding this daemon's unit from the
  alert half would delete the only witness **34 of the 249** incidents
  have: `file_organiser_scan` ×27, where the run record died with the
  run, and `retention_purge` ×7, which is not an agent at all and has no
  owning family anywhere.
- **The population is historic.** All 215 fall on 2026-08-08 → 08-10, the
  `SNAG-DB-001` window, and `agent_runs` holds **zero** `failed` rows
  across 7,816 sysadmin runs — which is the same fact stated twice, since
  `run()` raised out and the record died with it.

**What shipped is candidate (c), narrowed to one derived entry.**
`COVERED_SIGNATURES` maps `(source, signature)` to the family that owns
the fault. Both halves of the key are the producers' own constants —
`OWN_UNIT`, and the new `AGENT_RUN_FAILED_EVENT` replacing the literal
`BaseAgent.run` passed to `logger.exception` — so nothing is copied and
nothing can drift.

Options rejected, and why:

- **Dropping the row** rebuilds `SNAG-CFG-001`'s shape: a decision taken
  by a consumer with nothing recording that it was taken. It is quietened
  to `info` instead, still counted, still in the trend, with
  `details['covered_by']` **naming** the family that will speak.
- **A `known_noise` YAML entry** would have cost ten minutes and recorded
  a structural fact as an operator's judgement about harmlessness, in a
  file an operator may edit without knowing the coupling exists.
- **Demoting the log line to `WARNING`** at the producer would have
  removed the duplicate with no reader-side special case, and was refused
  because it puts agent failures back out of reach of
  `journalctl -u sysadmin -p err` and any `OnFailure=` hook — the exact
  artefact Session 61 existed to fix.

**Why quietening is safe, and it is structural rather than careful.**
`failures.py` reads `agent_runs`, so it cannot see a failure
`_record_outcome` failed to record — but `_record_outcome` is awaited
*outside* `run()`'s `try`, so its failure propagates into APScheduler and
raises `scheduler_job_error`, which stays at `warning`. The case where
the owning family is blind is the case where a different signature is
still loud.

**Verified live, because the fix ships untriggered.** Real historic
`agent_run_failed` and `scheduler_job_error` lines were pulled from the
journal, unwrapped by the real `unwrap_json_message`, and driven through
the real `_execute` against the live database in a rolled-back
transaction: `info` + `covered_by` for the first, `warning` for the
second, occurrences counted on both, **0 rows of residue**. Six tests,
2,023 total, all green; each new test falsified deliberately — emptying
`COVERED_SIGNATURES` breaks five, re-keying the lookup on the signature
alone breaks the sixth, which is the one asserting a negative.

**Opened rather than bundled**: `SNAG-LOG-006`, the one path the safety
argument above does not reach. `POST /api/sysadmin/scan-all` starts
agents with `asyncio.create_task` and keeps no reference, so a manual run
whose `_record_outcome` fails has no scheduler listener behind it and
nothing speaks. Population zero on this box, and the residual signal
(asyncio's `Task exception was never retrieved` on GC) is unmeasured,
which is why it is filed rather than assumed away.

## Previous session — Session 64: the snag was cosmetic and the thing under it was not

The sitting was scoped to `SNAG-LOG-003` — a 252-character title made of
JSON — and the first attempt to test it against the real rows the
14:10:58 restart had made available found that `read_journal` never
receives those rows at all.

**`SNAG-LOG-004`, found rather than looked for, and a P0 under a P2.**
`journalctl -o json` substitutes `null` for any field over ~4096 bytes
unless `-a` is passed. `MESSAGE` came back `None`,
`entry["message"][:5000]` raised `TypeError`, and the whole run died —
every source in it. Self-sustaining, because `logger.exception` writes a
>4096-byte line at `ERROR`, so the next poll reads that and crashes
again. All **215 historic `agent_run_failed` lines are 12,837–12,845
bytes**.

Four things the measurement settled:

- **The previous fix armed it.** These lines were `PRIORITY=6` until the
  restart, so `-p 4` excluded them and 40,228 runs had never failed. A fix
  that widens what a monitor sees is a regression surface for whatever
  consumes it.
- **Only a single-line structured source can reach it.** Other services'
  tracebacks arrive as many short entries; `JsonFormatter` folds
  `exc_info` into one `MESSAGE`.
- **It is the JSON serialiser's cap, not journalctl's reading** — the same
  records print in full under the default text output (11,572 and 12,164
  characters), so `journal_command` needed no change and that was checked
  rather than assumed.
- **No fixture could have caught it.** Every existing test patches `_run`
  with a stub returning hand-written JSON, so `MESSAGE` was always a
  string somebody had typed.

**Then `SNAG-LOG-003` itself, by the candidate the entry named.**
`LogFormat = Literal["text", "json"]` on `LogSource` and `LogRef`;
`read_journal` takes `log_format` and unwraps only where declared. Over
the **723 real `ERROR` lines**: 6 distinct titles of 242–253 characters of
JSON become **5 of 46–151 readable characters**.

Decisions taken, and what they cost:

- **`logger` goes to metadata, not into the title.** The old key's sixth
  title was a *fork*: `sysadmin.core.scheduler` and
  `sysadmin.services.scheduler` emit the same `scheduler_job_error` and
  were split only because the module path fell inside the 252 characters
  truncation left. Restoring it would rebuild that by design.
- **It fails open at every step**, decided from the box rather than from
  caution: systemd writes its own plain-text error lines into a unit's
  journal — 668 of them for `sportsanalyser-frontend` — so a declaration
  that discarded non-JSON would silence the line saying the service died.
  Verified by reading that unit with `format: json` forced on.
- **Severity is not read from the envelope**, although `"level": "ERROR"`
  sits beside the message. The level prefix already put it in `PRIORITY`,
  and only the prefix reaches `journalctl -p err` and `OnFailure=`.
- **Rejected: sniffing a leading `{`.** That is the coupling the priority
  half was sent to the producer to avoid — a special case for one source
  in a reader serving fifteen.
- **Rejected: `getattr(source, "format", "text")`** when twelve tests
  broke on `source.format`. It would have made them pass while swallowing
  a genuine wiring failure, so the fixture now builds the real
  `LogSource` instead.

**What is blocked**: nothing. **What is unobserved**: both fixes ship with
an empty live population — there have been no `ERROR` lines since the
restart, so the first real instance is still the first chance to see a
notification body.

2017 tests (was 1984), ruff and mypy clean. All four guards falsified
independently.

## Previous session — Session 63: the change was right and its stated reason was not

The handoff's `## Next action` line named proportional confidence and it
was the right change. **It was wrong about the mechanism**, and measuring
that before writing the gate is what turned a permitted change into a
safe one.

`log_trends._confidence` was `if coverage.runs_truncated > 0: return
LOW` — binary, so one catch-up read pinned the whole report for fourteen
days and `GET /api/logs/actions` served **zero** `noise` rows against two
signatures at 39,921 occurrences apiece. It now gates on
`truncated_fraction > TRUNCATION_LOW_FRACTION` (0.05) over the
**instrumented** reads. Driven against the live database after the
change: confidence **`medium`**, **25 recommendations including the 2
`noise` rows** — the falsification the sitting was set up around.

### Three things the measurement corrected

**`_resume_floor()` does not size the catch-up read by daemon downtime.**
It returns the newest stored `logged_at` **for that unit**, so it sizes
by *how long since that source last stored a row* — days for a quiet
source, against the two seconds a `systemctl restart` takes. That is why
16 of the 120 truncations each name **four or five sources at once**:
every one of them is the first `log_aggregator` poll after a restart,
~62 s after `Started SysAdmin…`. A source logging one warning a week is
read a week back on every restart.

**So Session 62's `-p` does reach the catch-up read**, against that
session's own expectation that no ceiling could. With `-p` the 500-entry
budget is spent on *storable* entries, and a week-long window on a quiet
source holds about one. Proof on the same box within one hour: the
13:17:05 restart's poll truncated 4 sources; the 14:10:58 restart's poll
truncated nothing. The population this gate was written for is therefore
smaller than either the entry or the handoff supposed — what the gate
now does is stop the *history* of it suppressing the family for a
fortnight.

**The denominator was wrong.** `_trend_coverage` counted the numerator
over runs carrying `details['truncated_sources']` and the denominator
over every run in the window. That field first appears 2026-08-12 17:31,
so 10,724 of the window's 17,730 runs could not have reported truncation:
**120 of 7,006 (1.71 %)**, not 120 of 17,730 (0.68 %). The artefact is
2.5x and self-correcting, which is exactly why it had to be fixed rather
than waited out — a number wrong today and right next week is one nobody
re-checks.

### Why a threshold is legitimate here and is not a lowered gate

The entry forbids lowering the gate "to unblock a demo", and that was
right. What makes this different is that **truncation is
one-directional**: a truncated read *drops* entries, so it can only make
a count too **low**, and a `noise` row argues that a signature is loud —
a floor the missing data cannot undercut. That is rule 4's own `NEW`
asymmetry ("a gap can hide a fault, never invent one") one step further.

What the threshold actually bounds is narrower and worth carrying
forward: a depressed *current* window can move a genuine `SURGED`
signature into the noise-eligible `STEADY` band. Both live rows are
`RETURNED` with `previous = 0`, so no ratio is computed for either and
nothing is distorted today — but that is the failure mode the number
exists for, not volume error.

`HIGH` is deliberately **untouched**: it still means nothing was lost and
nothing was missed. Only the floor beneath it moved, and `MEDIUM` was
already good enough for `_is_noise_candidate`, which only ever tested for
`LOW`.

### What made the guards suspect, and what was done about it

`truncated_fraction` **fails closed** — `schema_guard`'s posture rather
than `collation.py`'s — so a caller reporting truncation with no
`runs_instrumented` gets `1.0` and the binary behaviour back. That is
correct, and it meant **all 1,984 tests passed on the first run after the
change**, because every existing fixture sets no denominator. So the four
new tests were falsified deliberately: setting
`TRUNCATION_LOW_FRACTION = 0.0` restores the binary rule **exactly** —
it is the limit case, not a replacement — and breaks precisely those four
and nothing else.

### Files

- `sysadmin/monitor/log_trends.py` — `TRUNCATION_LOW_FRACTION`,
  `WindowCoverage.runs_instrumented` / `.truncated_fraction`, rewritten
  `_confidence`, rule 3 and the `Confidence` docstring
- `sysadmin/monitor/routers/logs.py` — `_trend_coverage` counts
  instrumented runs via `has_key`; both new fields serialised
- `sysadmin/core/contracts.py` — `LogTrendCoverageInfo` gains both,
  additive and defaulted
- `tests/test_log_trends.py` — five confidence tests; the old binary one
  kept as the not-knowing case
- `tests/test_log_actions.py` — the falsification pinned; the LOW gate
  test re-based on the storm day's real 7.3 %

Full suite **1,984 passed**, ruff clean, mypy clean.

## What was deliberately not done

**The apscheduler duplicate is untouched.** `apscheduler.executors.default`
logs `Job "…" raised an exception` with a traceback for every fault
`Scheduler._on_job_error` already records as structured
`scheduler_job_error` — 249 lines, the `uvicorn.access` shape one module
over. Not fixed here because Session 60's own rule cuts against the easy
version: that logger emits at **two** levels (the duplicate at `ERROR`,
the genuine "maximum number of running instances reached" at `WARNING`),
so `setLevel` cannot express it and disabling the logger loses real
signal. It needs a filter or a decision, and it is a different module
from the one this sitting was scoped to.

**`SNAG-LOG-006` is filed rather than fixed**, because its honest remedy
— retaining the task references and attaching a done-callback — touches
two composition roots, and its cheap alternative would need the JSON
unwrap to promote `run_type` into the identity the exclusion keys on,
which is the coupling `SNAG-LOG-003`'s fix was chosen to avoid.

**The name/unit seam is still open.** `details['truncated_sources']` keys
on the `services.yaml` **name** and `log_entries.source` on the **unit**,
and only `kernel` collides. Untouched again this sitting, and worth
noting that `COVERED_SIGNATURES` keys on the **unit** deliberately, which
is the side `log_entries.source` is on.

## Next session — ranked

1. **The verification sitting.** Restart, then measure the four
   outstanding claims from Sessions 63, 64 and 65 against the live table.
   It wins because three consecutive sittings have now built on
   foundations nobody has seen run — `SNAG-ESTATE-002`'s shape at three
   times the depth — and because it is the cheapest item here: the
   restart is owed anyway, and each claim is a query.
2. **Session 27 Tier 3** — the log aggregator's LLM narrative. The last
   unbuilt tier in the area and the family has never been in better
   shape. Loses for the fifth sitting, and by a wider margin than last
   time: it would add a fifth layer to a stack whose bottom three have
   not run. Wins outright the moment (1) lands.
3. **`SNAG-DOCS-002`** — eight project contract models with zero readers,
   four re-exported to the tray. Runner-up for the sixth time, on the
   same grounds: half an hour of deletion plus one decision about the
   tray's public surface.

**Named as blocked rather than dropped**: `SNAG-LOG-001` needs a
correlation rule nobody has measured, and the obvious cap rebuilds
`SNAG-ESTATE-001`'s roll-up defect. `SNAG-LOG-006` has a population of
zero and needs a manual run to fail before it can be observed.
`SNAG-ESTATE-001`'s remaining half is a retirement checklist, which the
entry says in writing is not this repository's to enforce.
`SNAG-ESTATE-002` and `SNAG-ESTATE-006` remain estate-manager's;
`SNAG-ESTATE-009` waits on a second consumer of `PortAttribution`.
