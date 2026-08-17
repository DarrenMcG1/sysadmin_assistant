# Project Status Dashboard

**Last Updated**: 2026-08-17
**Current Phase:** Feature-complete — maintenance & future features

> **A restart is owed again, and a reload will not do it.** `sysadmin`
> started **14:10:58** and Session 63's commit landed at **14:29:17**, so
> the process is now **four commits behind** — Sessions 63, 64 and 65
> have never run. Measured rather than reasoned: the *running* daemon's `LogRef` forbids extra fields and has
> no `format`, and driving it against the new `services.yaml` rejects
> the file — `services.13.log.format | Extra inputs are not permitted`.
> Session 49's rule 1 means a SIGHUP installs neither file, so the
> reload fails safely and delivers nothing. `sudo systemctl restart
> sysadmin`.
>
> **It is also what disarms `SNAG-LOG-004`.** The running process still
> crashes its whole `log_aggregator` run on the first `ERROR` line this
> daemon writes, self-sustainingly. It has not fired — **0 error lines
> and 146 clean runs** since 14:10:58 — so the box is one traceback away
> from a silent, permanent log blackout.
>
> **What is still outstanding, unchanged and still two minutes.** Resolve
> the two `Estate port … registry breach` rows so the judge re-raises
> them under Session 57's code (both still open, checked at 14:20):
>
> ```sql
> UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
>  WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
> ```
>
> `SNAG-ESTATE-010`. Session 27 has since solved the *general* version
> of this for the log family (an in-place quietening, legitimate because
> Session 39's ban is asymmetric), so the entry is worth re-reading
> before anyone fixes the estate judge the obvious way.
>
> **The 03:00 purge has still not deleted anything.** `SNAG-DB-004`'s fix
> went live with the 14:10:58 restart, so **tonight's 03:00 is the first
> run that will act**, and it happens by itself.
>
> **Next up**: **Observe three unobserved sittings against live data.**
> *Recommended at the close of Session 65.*
>
> **1. The verification sitting — restart, then measure what Sessions 63,
> 64 and 65 claim.** Session 62's ceiling fix (14:09:16) is the last one
> the running process contains; everything since has shipped green and
> unrun. Four claims are outstanding and every one is measurable within
> an hour of a restart: `-p` takes read efficiency 40 % → 100 % and so
> should drop `truncated_fraction` below `TRUNCATION_LOW_FRACTION`; a
> `medium` report should make the two 39,921-occurrence signatures appear
> as `noise` rows in `GET /api/logs/actions`, a family with an **empty
> population on this box** for its whole life; `-a` plus `format: json`
> should give `log_entries` readable messages for `sysadmin.service`
> where it currently holds 10 rows of raw JSON; and `covered_by` should
> appear the first time an agent fails. It wins because three consecutive
> sittings have now built on foundations nobody has seen run, which is
> precisely what `SNAG-ESTATE-002` was — and because it is the cheapest
> thing on the list, the restart being owed anyway.
>
> **2. Session 27 Tier 3 — the log aggregator's LLM narrative.** The last
> unbuilt tier in the area, and the family is in better shape than it has
> ever been: signature dedup, trends, actions, correct priorities,
> correct ceiling, proportional confidence, readable titles, no crash, one
> owner per fault. It loses for the same reason it lost last sitting and
> by a wider margin — it would add a fifth layer to a stack whose bottom
> three have not run. It wins outright the moment (1) lands.
>
> **3. `SNAG-LOG-001` — one mosquitto crash, four recommendations.** Real,
> and the honest fix is a correlation rule nobody has measured. It loses
> on evidence rather than merit: it needs a live multi-line crash and the
> last one was days ago. Third for the third sitting running, which is
> itself the argument for leaving it there rather than forcing it.
>
> **Blocked or waiting on another repository.** `SNAG-ESTATE-002` and
> `SNAG-ESTATE-004` remain estate-manager's; `SNAG-ESTATE-006` and
> `SNAG-ESTATE-007` are delegated and unchanged. `SNAG-ESTATE-001`'s
> remaining half is a **retirement checklist** — a process, and the entry
> says in writing it is not this repository's to enforce, so it is named
> rather than ranked. `SNAG-LOG-006`, opened today, has a **population of
> zero**: a manual run must fail before it can be observed at all.


---

## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 5 agents + scheduler + DB |
| API | 🟢 Complete | **46 routes** across 8 routers plus 2 defined in `create_app` (`scan-all` and `reload`, which need `app.state`); bearer-token auth on mutating endpoints (GETs open). *Counted live 2026-08-17 off `create_app()`; 44 before Session 27 added `GET /api/logs/trends` and `GET /api/logs/actions`* |
| Database | 🟢 Complete | 13 tables in sysadmin schema, Alembic migrations (head **012**, applied 2026-08-13) |
| Agents | 🟢 Complete | SysAdmin, File Organiser, Log Aggregator, Service Discovery, **Estate Judge** (2026-08-13). Project Organiser left for the estate's 8400 service on 2026-08-13 and stays in `AGENT_NAMES` only because the constraint is add-only |
| GPU Monitoring | 🟢 Complete | AMD via rocm-smi + sysfs fallback, temp/VRAM alerts |
| Observability | 🟢 Complete | Structured JSON logging + request access logs. *`SNAG-LOG-004` found and fixed 2026-08-17: `read_journal` passed no `-a`, so every record over ~4096 bytes returned `MESSAGE: null` and the aggregator crashed on it — armed by the priority fix below, 0 errors and 146 clean runs away from a permanent blackout. `SNAG-LOG-003` closed the same sitting: `services.yaml` now carries a per-source `format: json` declaration and titles read `Log error: sysadmin-service — scheduler_job_error` rather than 252 characters of JSON.* *`SNAG-AGENT-008` closed 2026-08-17: uvicorn's duplicate access logger silenced (volume half), and every JSON line now carries a `<N>` syslog level prefix with `uvicorn.error` rerouted through the same formatter (priority half). **Live since the 14:10:58 restart** — verified, `log_entries` holds 10 `warning` rows for `sysadmin.service` where it held 0 across nine nights* *`SNAG-LOG-005` fixed 2026-08-17: making the daemon visible to itself gave one fault two speakers, so `COVERED_SIGNATURES` quietens `(sysadmin.service, agent_run_failed)` to `info` with `details['covered_by']` naming `failures.py`, which owns agent-run health and waits for two consecutive failures. Keyed on the producers' own constants; measured at 249 error incidents, of which 34 have no owning family and stay loud.* |
| KDE Tray App | 🟢 Phase 3 Complete | Tray icon + service grid + D-Bus notifications + native dashboard + DND mode + service actions (popup retired 2026-07-24) |
| PA Integration | ⚪ Dormant | Code + tests intact, `personal_assistant.enabled: false` — PA retired 2026-07-24, Alfred has no inbox to POST to |
| Testing | 🟢 Complete | **2031 backend + tray, all green** (the deliberately-red `test_searxng_wiring.py` was wired and went green 2026-08-14; nothing skipped on this box, 4 skip in CI where no searxng unit exists); real-app fixture, schema drift guard, import-boundary guard, shared-query guard, unit-file pairing guard, deploy-triggered wiring guard, **job-plan/target pairing guard**, **autogenerate single-copy guard**, **derived-not-picked guards on the two reminder intervals**, **producer-built estate payloads (4 fixtures, recorded + live halves)**, **journal resume-boundary guard (8 tests, each falsified against the old behaviour and against both wrong fixes)**, smoke script |
| CI | 🟢 Complete | GitHub Actions: ruff + mypy-clean codebase + full pytest (headless Qt) |
| LLM | 🟢 Complete | llama.cpp (llama-server :8081, OpenAI-compatible API) — migrated from Ollama 2026-07-24 |
| Frontend | 🔴 Retired | Web UI died with PA (2026-07-24). The PyQt6 tray dashboard is now the only UI — see ideas.md for rebuilding it in Alfred's Nuxt frontend |

---

## Recently Completed

### The 497 surplus log rows purged, and the cost was understated (2026-08-17)

**Session 66's fix stopped new duplicates and deleted none of the old
ones.** This sitting deleted them — reversibly, backed up, with the restore
path verified rather than claimed — and measured both endpoints either side.

**The identity was proved before anything was deleted, and the obvious
evidence pointed the wrong way.** `raw_line` differs in **all 339**
duplicate groups, which reads as proof they are distinct journal entries; it
is journalctl's JSON key ordering varying between reads. Settled against
journald's own identity instead: **338 of 339 groups carry exactly one
distinct `__CURSOR`, and none carries more than one.** The 339th is the
mosquitto coredump, whose `raw_line` is truncated at 2000 characters so the
cursor fell off the end — its three `ingested_at` stamps are the three
restarts, the same evidence by another route.

Two rules the purge itself needed, neither of them in the filed plan:

1. **The purge key must be the fix's key.** `(source, logged_at, message)`
   is what `_is_unstored()` uses to decide an entry is already stored, so
   the surviving table holds no shape the running code refuses to
   re-create. The plan's tie-break was wrong, though: it said "keep the
   earliest `id`", and `UUIDPrimaryKeyMixin` is `uuid.uuid4`, so ordering
   by `id` is arbitrary. The earliest `ingested_at` is kept instead —
   keeping a random copy falsifies when the service first observed the
   entry while leaving `logged_at` correct.
2. **A purge can re-open the defect it cleans up after.** `_resume_floor()`
   reads `max(logged_at)` per source and the message set at it; deleting
   the last surviving row there moves the floor backwards and the next
   poll re-reads the window. Asserted 0 inside the transaction, and both
   guards falsified deliberately — each aborts, and the `DELETE` never
   executes in either falsified run.

**497 rows deleted**, 626,976 → 626,479, duplicate groups 339 → **0**.
`GET /api/logs/actions` went **28 → 24** recommendations at unchanged
`confidence: medium` with **no new rows**; `GET /api/logs/trends` holds 47
signatures, `truncated: false`.

**The entry understated its own cost, which is the part worth carrying.**
It said counts were overstated by up to 19×; four recommendations were
**fabricated rather than inflated**. Both `alfred-backend` surges read 21
vs 5 (ratio 4.2) against a genuine **4 vs 5**, and both
`sportsanalyser-frontend` surges read 19 vs 6 (ratio 3.17) against a
genuine **1 vs 3** — a **decline that was being reported as a surge**.
Duplication inverted the direction, which a claim about magnitude does not
predict. Worst surviving inflation: `estate-broker-provision` **18 → 1**,
`kernel` "failed to reset" **17 → 1**, `estate-manager-api` **23 → 11**,
`venture-assistant-backend` surge **48 → 27**. The two `noise` rows moved
39,922 → **39,885** — so the family this month's work unblocked was the
least distorted of them.

`SNAG-LOG-008` opened: ten `sysadmin.service` rows are frozen as raw JSON
because `unwrap_json_message` applies at read time and cannot reach rows
stored before the Session 64 declaration. Historic and measured — all ten
ingested 14:12–14:22, the readable ones begin at the 19:50:19 restart.

### Four shipped-unrun claims verified, and SNAG-LOG-007 found underneath them (2026-08-17)

**Sessions 63, 64 and 65 shipped green and unrun; this sitting restarted
the daemon and measured what they claimed.** All four hold:

1. **`-p`'s read efficiency.** Reproduced against the real journal on the
   2026-08-12 storm window: **122,531 raw kernel lines carrying 49,012
   storable ones — 40.0 %**, so a 500-entry budget was carrying ~200
   usable entries and now carries 500. The first catch-up read after each
   of three restarts truncated **nothing**.
2. **`SNAG-LOG-002`'s gate.** `GET /api/logs/actions` returns
   `confidence: medium` and **2 `noise` rows** — the two Bluetooth
   signatures at **39,921** apiece — where it had served zero for the
   family's entire life. 25 recommendations total (18 `new_signature`,
   5 `surge`, 2 `noise`).
3. **`SNAG-LOG-003`'s declaration.** A new `log_entries` row reads as
   prose against the 10 raw-JSON rows beside it, and the alert title from
   a **700-character** JSON journal line is **46 characters**:
   `Log error: sysadmin.service — agent_run_failed`.
4. **`SNAG-LOG-005`'s `covered_by`.** Not observable from history — the
   215 historic `agent_run_failed` lines are all `PRIORITY=6`, so the
   reader's `-p 4` excludes them, and `agent_runs` held **0 failed rows
   across 48,452 runs**. Driven by inducing a controlled
   `service_discovery` failure: the row came back `severity: info` with
   `details['covered_by']` naming `failures.py`, `noise_reason` correctly
   `NULL`, and — the point of the fix — it fired on the **first** failure
   and was quietened rather than announced.

**`SNAG-LOG-007` was found by the verification rather than in it.** One
mosquitto coredump from 2026-08-12 had been raised as a fresh `critical`
three times, once per restart, and nothing in the four claims predicted
that. `_resume_floor()` opens the catch-up window at the newest stored
entry; `journalctl --since` is inclusive and `since_timestamp` truncates
to whole seconds, so the boundary entry came back every restart —
**339 duplicate groups, 497 surplus rows, worst case 19 copies of one
entry**. Fixed by closing the boundary against the stored rows rather
than by narrowing the window, because narrowing it trades a duplicate for
a gap. Before/after on the same box: the 19:49 restart re-ingested 26
entries reaching back five days; the 20:03 restart re-ingested **0**.

### SNAG-LOG-005 fixed — one owner for agent-run health (2026-08-17)

**The fix that made the monitor able to see its own errors gave one fault
two speakers.** `BaseAgent.run` states one fact twice, three lines apart:
`logger.exception("agent_run_failed")` to the journal, then a `failed`
row to `agent_runs`. Session 61's level prefix and Session 64's
`format: json` are what let the first copy reach the log aggregator, so
an agent failure raised a row here **and** a row from `failures.py` — two
tray fingerprints. Sharper than duplication: `failures.py` requires
**two** consecutive failures and argues the rule out in writing, while
the journal path raises on the **first** line.

`COVERED_SIGNATURES` maps `(source, signature)` to the family that owns
the fault, quietening to `info` with `details['covered_by']` **naming**
it. Both halves of the one entry are the producers' own constants —
`OWN_UNIT`, and the new `AGENT_RUN_FAILED_EVENT` that replaces the string
literal `BaseAgent.run` used to pass to `logger.exception`.

**Three things the measurement settled that the entry had not.** The
collision was **four** rows historically, not two — 215 of 215 incidents
fired `agent_run_failed`, `scheduler_job_error` and apscheduler's own
`Job "…" raised an exception` in the same second. The obvious wider fix
(exclude this daemon's unit from the alert half) is refuted: **34 of 249
error incidents carry no `agent_run_failed` at all**, and
`retention_purge` is not an agent, so nothing else covers it. And
quietening is safe because `_record_outcome` is awaited *outside*
`run()`'s `try` — the case where `failures.py` is blind is the case where
`scheduler_job_error` is still loud, which is why `agent_runs` holds
**zero** `failed` rows across 7,816 sysadmin runs.

Ships untriggered: all 215 lines fall in the 2026-08-08 → 08-10
`SNAG-DB-001` window. Driven live instead — real journal lines through
the real `unwrap_json_message` and `_execute` against the live database
in a rolled-back transaction, **0 rows of residue**. Six tests, each
falsified deliberately. `SNAG-LOG-006` filed for the one path the safety
argument does not reach: a manual run started with `asyncio.create_task`
has no scheduler listener behind it.

### SNAG-LOG-004 found and fixed, SNAG-LOG-003 closed — the line too long to read at all (2026-08-17)

**Two halves, and the one that was not on the plan is the P0.** Session 64
set out to give this daemon's journal source a `format: json` declaration
and could not test it, because `read_journal` never received the lines it
was meant to unwrap.

`journalctl -o json` substitutes `null` for any field over ~4096 bytes
unless `-a` is passed. `MESSAGE` therefore returned `None`,
`entry["message"][:5000]` in `LogAggregatorAgent._execute` raised
`TypeError`, and the whole run died — every source in it, not just the
one that produced the line. **Self-sustaining**: the failure is logged by
`logger.exception`, itself a >4096-byte line at `ERROR`, so the next poll
reads *that* and crashes again. All **215 historic `agent_run_failed`
lines are 12,837–12,845 bytes** and every one exceeds the cap.

Armed by the previous fix and not yet sprung: those lines were
`PRIORITY=6` until the 14:10:58 restart, so `-p 4` excluded them and
**40,228 `log_aggregator` runs have never failed**. Measured at the moment
of the fix: **0 error lines and 146 clean runs since the restart**.

Then the declaration itself. `LogFormat = Literal["text", "json"]` on
`LogSource` and `LogRef`; `read_journal` takes `log_format` and unwraps
only where declared. Over the **723 real `ERROR` lines** this daemon has
written, the title goes from **6 distinct values of 242–253 characters of
JSON to 5 of 46–151 readable characters**; `logger` goes to metadata
rather than into the title, because putting it back would restore the one
fork the old key produced by accident (`sysadmin.core.scheduler` and
`sysadmin.services.scheduler`, one fault under a renamed module).

It **fails open at every step**, and the reason is measured rather than
habitual: systemd writes its own plain-text error lines into a unit's
journal — `Failed to start SportsAnalyser - Frontend (Next.js).` appears
**668 times** live — so a declaration that discarded non-JSON would
silence exactly the line saying the service died.

**2017 tests** (was 1984), ruff and mypy clean. Both halves' guards
falsified independently.

### SNAG-LOG-002 closed — the gate was binary, and one read pinned a fortnight (2026-08-17)

`log_trends._confidence` returned `LOW` on `runs_truncated > 0`, so a
single catch-up read suppressed every volume argument for fourteen days
and `GET /api/logs/actions` served **zero** `noise` rows against two
signatures at 39,921 occurrences apiece. It now gates on
`truncated_fraction > TRUNCATION_LOW_FRACTION` (0.05) over the
**instrumented** reads. Live after the change: confidence `medium`, **25
recommendations including the 2 `noise` rows**.

Three things the measurement settled that the plan had wrong.
**`_resume_floor()` does not size the catch-up read by daemon downtime** —
it returns the newest stored `logged_at` for that unit, so a source
logging one warning a week is read a week back on every restart, which is
why the 16 non-storm truncations each name four or five sources at once.
**Session 62's `-p` therefore does reach them**, against the expectation
that no ceiling could: the 13:17:05 restart's poll truncated 4 sources,
the 14:10:58 restart's poll truncated nothing. And **the denominator was
wrong** — 120 of 7,006 instrumented runs (1.71 %), not 120 of 17,730
(0.68 %), a 2.5x artefact that would have self-corrected and so would
never have been re-checked.

The threshold is legitimate because **truncation is one-directional**: it
drops entries, so it can only make a count too low, and "this is loud" is
a floor missing data cannot undercut — rule 4's `NEW` asymmetry one step
further. What it bounds is a depressed *current* window moving a
`SURGED` signature into the noise-eligible `STEADY` band. `HIGH` is
untouched; only the floor beneath it moved. Falsified before being
trusted: `TRUNCATION_LOW_FRACTION = 0.0` restores the binary rule exactly
and breaks precisely the four new tests.

### SNAG-LOG-002, the ceiling half — the budget was 40 % useful (2026-08-17)

`read_journal` bounded the read with `-n 500` and then applied
`severity_filter` in **Python, over lines the ceiling had already
counted**. Across the 2026-08-12 kernel storm that is **203,042 raw
lines carrying 81,216 storable ones — 40 %**, a median of **510 raw a
minute against a ceiling of 500**, and **208 of 210 storm minutes
truncated**. The 100 instrumented storm minutes produced **103 truncated
reads: one per poll.**

Passing `-p` to journalctl, derived from `PRIORITY_MAP` rather than
written down beside it, makes the same 500 carry 500 storable entries.
Verified against the real journal: the stored multiset is **identical**,
budget efficiency **40 % → 100 %**, steady kernel polling **510 → 204**
lines a minute. `max_entries_per_read` is unchanged — raising it would
have bought the same headroom at 2.5× the memory and left the waste.

`read_journal` gained its **first direct tests** (`tests/test_journal.py`,
14): every existing test patches it out, which is how the ceiling came to
bound raw lines unasserted.

**It does not close `SNAG-LOG-002`.** Catch-up reads still truncate —
`_resume_floor()` sets the window to how long the daemon was down — and
`_confidence` is binary, so one such read pins the report `LOW` for
fourteen days. The **per-source** confidence fix the handoff named was
measured and **refuted**: it produces zero noise rows, because kernel
holds the only noise-eligible signatures and 103 of the 120 truncations.

### SNAG-AGENT-008, priority half — the daemon can see its own errors (2026-08-17)

Every line this service writes went to stdout, and systemd stamps
captured stdout `PRIORITY=6` whatever the `"level"` inside the JSON says
— so `read_journal`'s `severity_filter: warning` discarded the lot and
`log_entries` held **0 rows** for `sysadmin.service` across nine nights
of `ERROR` from the broken retention purge.

**The entry's own statement of the trade-off was wrong, and one
`systemctl show` settled it.** It said the two unit-file remedies both
need `sudo`. `SyslogLevelPrefix=` **defaults to true** in systemd and
already read `yes` on this unit — so the prefix remedy needs no unit
edit and no `sudo`, putting it on exactly the footing the entry credited
only to the reader-side hack while fixing the artefact rather than one
consumer's view of it. `journalctl -u sysadmin -p err` will work; so
will any `OnFailure=` hook.

`JournalLevelPrefixFormatter` prefixes each JSON line with `<N>`, gated
on `log_format == "json"` as a **precondition** rather than a proxy:
only JSON guarantees one line per record, so a traceback travels on the
line whose level describes it. `uvicorn.error` — which carries
`Exception in ASGI application` and every unhandled 500 — was
**rerouted, not silenced**, the opposite verb from its sibling three
lines up in the same function.

Verified live without the `sudo` the deploy needs: a transient user unit
running the real `configure_logging`, read back by the real
`read_journal` — **3 entries where it has always returned 0**. Filed on
the way: `SNAG-LOG-003`, and a correction to `SNAG-LOG-002`'s
composition (9 sources, not 2).

### SNAG-AGENT-008, volume half — the line that was written twice (2026-08-17)

`sysadmin.service` wrote **673 journal lines per 5 minutes**, and the two
causes were both invisible to the tests that existed. Every request was
logged **twice** — `configure_logging` clears the *root* handlers, which
never reaches `uvicorn.access`, because uvicorn attaches a handler to it
directly with `propagate = False`. 662 plain lines against 640 JSON in
ten minutes, and the difference is exactly the 22 `/health` polls the
middleware excludes: **`SNAG-API-002`'s exclusion has never worked**, and
its test patches the middleware's own logger. Separately, `ServicesTab`
fanned out one `/details` request per service on every status poll
whether or not the dashboard had ever been opened — **86 % of all
lines**, against its own window's promise of *"no background polling
when hidden"*.

Both fixed and both guards falsified against the pre-fix code; the
logging half additionally driven against uvicorn's real `LOGGING_CONFIG`.
The tray is deployed and measured at **`/details` = 0**; the backend
restart needs `sudo` and is owed.

**The justification for doing it was refuted in the same sitting.** The
118 truncated runs blocking `GET /api/logs/actions` are **kernel 103,
sysadmin-service 14** out of 10,064 — 1.2 %, with 104 on a single day —
and `_confidence` is binary, so `SNAG-LOG-002` did not close with this
and its cause has been corrected in place.

### Session 27 — the log-aggregator tiers (2026-08-17)

Tiers 1 and 2 built; Tier 3 deferred and is now all that remains.
`GET /api/logs/trends` (88 ms, live) and `GET /api/logs/actions` (13
recommendations on real data), off two pure modules. **626,906 rows
collapse to 44 distinct messages in 91 ms**, which is what lets the
signature be applied in Python rather than re-implemented in SQL.

Three things the live data settled that fixtures could not: "new" is a
first sighting and not `previous == 0` (the Bluetooth signature reads
`39,919 / 0` and is a month old); truncation rather than poll count is
the confidence signal, because the journal cursor catches a gap up; and
three of the emitted `journalctl` commands did not work until they were
actually run — the kernel is not a unit, and 7 of 14 sources are user
units. `known_noise` was **built rather than named**, quietening rather
than suppressing, and it reaches already-open rows because Session 39's
ban on in-place severity changes is asymmetric. 71 new tests.

### SNAG-DB-004 — the purge that logged success and rolled back (2026-08-17)

The nightly retention job had deleted **nothing since 2026-08-08** while
logging six successful purges a night: `ORDER BY true` is a syntax error
to PostgreSQL, and one transaction over twelve tables meant the twelfth
discarded the eleven before it. 1,866 green tests missed it because the
session was mocked and one test pinned the broken literal exactly. Fixed
with a sentinel taking its own branch, a pure `purge_statement()` that
PostgreSQL parses in a test, and one savepoint per table. 207,566 rows
due at the next 03:00.

### The document catches up with the box — SNAG-DOCS-001 (2026-08-17)

**The recommendation, taken on the fourth attempt, and wrong on both of
its numbers in a way worth keeping.** `CLAUDE.md` is loaded at the start
of every session here, and since 2026-08-13 it had described the project
domain — gone to estate-manager that day — in the present tense. The
entry said fifteen endpoints and five narratives. Measured: **twelve**
table rows and **nine** narrative blocks, plus six loose sentences that
each read correctly alone and wrongly together.

**The population splits three ways, not two, and that is what a literal
reading of the entry would have got wrong.** `GET /api/projects/managed`
is still **served here** — live `service_health` joined to registry
identity, relocated within this repository by ADR-0005 and keeping its
path. `/overview` and `/{name}` are **consumed** from 8400, parsed with
this repository's own tolerant models under
`tests/test_estate_project_contracts.py`. Only the remaining **nine** are
neither. "Move them all behind pointers" would have deleted a live
route's contract and relabelled a live seam as absent.

**Two blocks were rewritten rather than pointed away**, because the
argument is still ours: `SysAdminAgent._resolve_recovered` (the project
organiser made the case; we still run the statement), and
`core/escalation.py`'s placement — whose stated reason, *`monitor` may
not import `projects`*, **expired with the domain** and has been replaced
by the four climbers it actually has. Leaving a correct conclusion
resting on a dead premise is the trap `SNAG-AGENT-006` records; this is
that trap in a document.

**ADR-0005 was not linked from `CLAUDE.md` at all** — the pointer target
of the whole fix, missing from the index the fix points through. Nor were
0003 and 0004. All three are listed now, and ADR-0001's open question
("who owns project state") is marked answered against this repository.
1,774 lines → 1,684. Suite **1866** green.

**Three things came out of measuring the box rather than the tree.**
`SNAG-AGENT-002` was **fixed on 2026-08-12** and closed on paper here —
its stated remedy is `log_signature.py` verbatim, and the live table
holds 8 unresolved rows against 547,814 for one title six days ago, so
**Session 27 is now only the tiers**. `SNAG-ESTATE-010`: Session 57's
quietening is live and cannot reach the two rows it was written for,
because the family dedups on an open title and only *escalation* has a
resolve-and-re-raise path. `SNAG-DOCS-002`: eight project contract models
with zero readers, four re-exported to the tray. Closed two, opened two;
the snag parser reported 36 → 38, which is `SNAG-ROADMAP-002`
demonstrating itself on the sitting that fixed a documentation snag.

### The holder decides how loud — the ports family's first live rows (2026-08-17)

**The third detector in a row to be corrected by its own first data**,
after `judge_attention` (Session 52) and the other three estate surfaces
(Session 54). `Estate port 3110` and `Estate port 8110` had stood at
`warning` since 2026-08-16 12:07 — one minute after the daemon last
entered active, which is this family's first run ever to raise anything.
`CLAUDE.md` still described it as shipping with zero rows.

Both listeners are Alfred dev servers launched from VS Code —
`nuxt dev` and `uvicorn --reload`, all three pids in
`app-code-oss-26348.scope`. **The estate's finding is literally
correct** (no registry row claims either port) and its remedy is the
half that does not apply: an editor's dev server is not a service the
next project could collide with.

**The defect was not a missing signal.** `Listener.transient` has named
these listeners since Session 26c. `PortReport.unit_ports` skips
`attributed and transient` for `recommendations.py`'s correct reason — a
session scope is nobody's service and a `kind: http` snippet for one
would invent a service — and `unattributed_ports` never held them,
because a session scope *is* attributed. So the port fell out of the
stored blob entirely and `details['holder']` came back `None`,
indistinguishable from 5432's genuine unattributability. That is
`ports_checked`'s rule one layer down: zero-because-clean served as
zero-because-blind.

`transient_ports` is a **separate blob key**, not a flag inside
`unit_ports` — one field whose two consumers want opposite safe defaults
is Session 48's `UnitFinding.enabled` trap, caught this time before it
shipped rather than after.

**Quietened, never suppressed.** `TRANSIENT_HOLDER_SEVERITY = "info"`,
which is the only rung below `tray.notify_min_severity` here, so the row
stays in `GET /api/sysadmin/alerts` and leaves the notification path.
Dropping it was the obvious implementation and rebuilds this family's
founding defect — Session 26b-A exists because a ports breach was
detected, correct, machine-readable and never said out loud. The roll-up
takes the loudest rung it swallows, so six dev servers plus one genuine
unclaimed listener still speaks.

What it removes is a *recurrence*: the tray clears
`notified_this_episode` only on a `{severity}:{title}` pair being absent
from a poll, so closing the editor resolved both rows and re-opening it
raised two fresh `warning` rows with fresh fingerprints — two toasts per
dev session indefinitely, plus one restatement per row per day since
Session 53's `reminder_hours`.

Verified live in-process against the real `ss` (37 listeners) and the
real `:8400/api/audit/findings` (2 breaches, plus the standing 3300
`warn` that is still correctly not judged): the same two rows come out
`info` with `holder=app-code-oss-26348.scope` where they came out
`warning` with `holder=None`. 12 new tests, 1866 green.

`SNAG-ESTATE-009` filed for what it cannot reach — the sweep is
six-hourly and the judge hourly, so a dev server started inside a sweep
window is unattributed and speaks at `warning`. Fixing that means either
a second `ss` caller (which `_attribution` refuses in writing) or six
times the sweep cost for one annotation.

### The snag that was already fixed — SNAG-DB-002 (2026-08-17)

**Closed without a line of code, by measuring the box before reading the
entry.** `SNAG-DB-002`'s remedy half was carried out by **estate-manager**
on 2026-08-13 (`eb51ff6` 18:03, `52b312c` 20:29) using their
`scripts/refresh-collations.sh`, which encodes this entry's own trap:
never `REFRESH` unless that database's `REINDEX` has just succeeded.

**The verification, not the closure, is the content.** Index file mtimes
show the two bursts and prove nothing about an actively-written index,
whose file carries a recent mtime whether or not its contents were
rebuilt. The exact test is `pg_class.relfilenode` against
`pg_class.oid` — a rebuild draws a fresh relfilenode from the
cluster-wide counter, so an index never rewritten retains
`relfilenode = oid`. **0 of 125** collation-sensitive user indexes across
the eight databases retains its original; `projects`' 58 sit in one band,
3,882,764–3,886,294, against creation OIDs from 46,010. "Collation
sensitive" is `indcollation NOT IN (0, 950, 951)`, and it is the filter
the entry lacked — `950`/`951` are `C`/`POSIX`, byte-order, immune to a
glibc change.

**Four of the entry's numbers corrected, three of which were true when
written**: 16 GB (real, largely index bloat the reindex reclaimed, before
the estate dropped `personal_assistant` on 2026-08-14 taking the database
to 1,094 MB — so today's 1098 MB is a deletion, not a mistake); eight
databases (the estate audits eleven); 25 indexes "several on text" (58 in
`projects`, 125 cluster-wide, **0** in `pg_catalog`, whose text columns
are `name`); and a quiet window of hours that was **30 seconds**, because
`REINDEX` rebuilds indexes and 3,123 MB of them was the governing figure,
never the 16 GB.

**Filed on the way: `SNAG-ESTATE-008`** — four documents here restated a
finished ops action for three days and five sittings while this
application's own alert table had resolved all eight rows at 18:01:48 on
2026-08-13. An unread fault is a missed alarm; an unread **recovery** is
an instruction to redo finished work. The cause is structural rather than
careless: `EstateJudgeAgent` is narrowed to `check == "ports"` for two
sound reasons, and shared infrastructure remedied by the estate is the
case neither anticipated. Also corrected: `snag_list.md`'s header claimed
`count_open_snags` reports 47 (measured 2026-08-14); driven against the
current parser it reports **35**, the function having been rewritten
around `read_snags` since — the same defect, one document over.

### The understudy gets a clock — SNAG-TRAY-007 (2026-08-16)

**Session 54's recommendation, taken as written**, closing the last hole
in the arc Sessions 39, 53 and 54 built. `monitor/desktop.py` exists for
the case where the tray is not running, and in exactly that case a
standing fault was announced once and then never again.
`DesktopNotifier.sweep_reminders` gives it the clock it never had,
scheduled as `desktop_reminder_sweep`. Suite **1854** (from 1834), ruff
and mypy clean, no migration, no route.

**The deliverable was the decision the snag asked for, and it came in
two halves.** *Precedence*: `tray_grace_seconds` is the same window on
both paths and the action differs — the raise path skips, the repeat
path **stamps the clock forward**, because a skip leaves
`last_spoken_at` at the opening notification and the first sweep after a
tray outage would restate a fault the tray itself restated ten minutes
earlier. The difference is observable only in the middle window; the
first draft of that test had the arithmetic wrong and passed for the
wrong reason. *Ownership*: a `JobSpec`, not a call bolted to
`SysAdminAgent._execute`, because an agent reminding on the notifier's
behalf is the second-owner defect at a fifth scale.

**Neither number is invented.** `reminder_hours` is the tray's 24 for
the tray's reason, and because two speakers with different cadences make
the interval depend on which was running. The sweep's cadence has no
config leaf at all — `max(60, tray_grace_seconds)`.

**The narrowing is filed, not implied**: `SNAG-TRAY-008`. The population
is what this process announced, so a fault raised while the tray was up
is never adopted and a restart forgets everything — the alternative
being `SNAG-AGENT-005`'s unbounded `SELECT` wired to a notification each.

**Verified live**, because the unit tests mock every session and the
`title IN (…)` clause had never reached PostgreSQL. Against the real
table: the query selected the live title and refused one never raised;
the sweep restated once then held; a synthetic row was restated inside a
roll-up of 2, resolved, and dropped — residue **0** after rollback.
Against a real `BackgroundScheduler`: added at `interval[0:03:00]`,
re-apply retimed nothing, grace 600 retimed it to ten minutes,
`enabled: false` removed it.

**Found sideways**: `SNAG-DOCS-001`, while reading the live route table
for the next-session ranking rather than trusting the documents.

### The other three estate surfaces, against data (2026-08-16)

**Session 53's recommendation, taken as written, and it found what its
framing predicted.** `judge_projects_invariants`, `judge_audit_*` and
`judge_queue_invariants` had never been run against anything but
hand-written dicts. Payloads were built by the producer's own code —
estate-manager's route functions, ORM models, `_streak_starts` age walk,
`CheckResult.as_summary`, `Arbiter.invariants` and `api._public` — driven
in its venv against the live `estate` database inside transactions that
were rolled back (verified after at 7 `scan_runs` / 22 `audit_runs` / 92
`audit_findings`, unchanged). The `ports` breaches are real: listeners
bound on 3900–3905 inside the registry's own audited range, through
`ports.run_check` against the real `monitorable-project.md`.

**The defect a literal is structurally unable to show.** Each rule was
pinned one condition at a time, because that is what a keyword override
produces. The producer cannot separate them: `ScanOutcome.estate_written`
starts `False` and is set near the end of a run, so **every** failing
scan carries `error` *and* `estate_written: False`, and the judge raised
two rows for one fault — the second reading *"The last project scan
completed without rewriting estate.json"* of a scan that did not
complete. Under Session 53's `reminder_hours` that is a false sentence
restated every 24 hours, which is what turned a redundancy into a fix.
The rule is now narrowed to a scan that did not error, making the two
families mutually exclusive by construction.

**A second, latent defect, fixed because it is invisible either way**:
`EstateJudgeAgent._execute` read `open_titles` once, so two judgements
sharing a title in one run inserted two rows and deduplicated only from
the second run. Reachable through `judge_audit_findings` rule 4, which
keeps the `code` out of the title on purpose.

**Two producer-side gaps delegated rather than worked around** —
`SNAG-ESTATE-006` (`AuditFinding` has no `code` column, so
`details['code']` is `None` on every payload the estate can serve, and
the docstring said otherwise) and `SNAG-ESTATE-007` (the arbiter's pool
omits the `-c timezone=utc` its sibling engine sets and documents). Both
carry pre-staged tests or a stated cost rather than a parked task.

**Two rules measured and recorded as unreachable rather than deleted**:
the scan's `finished_at is None` and the audit's `error`, both of which
the producer cannot currently write. Kept, and named in the docstrings so
their silence is not read as health.

Suite **1834** (from 1802), ruff and mypy clean, no migration and no
route. Verified live on the real database in a rolled-back transaction:
raise 7 → hold (0 raised, 0 resolved) → resolve 7, **0 rows of residue**.

### A fault that stands keeps speaking — SNAG-ESTATE-003 (2026-08-16)

**The snag asked for a third rung; the session's first deliverable is
the measurement that a third rung cannot be heard.** Five families
deduplicate on an open row and own no ladder, so each rings once at the
quiet severity and is silent while the fault stands. STATUS.md
recommended *a third rung in `sysadmin/core/escalation.py` with three
callers*. Driven against the real `NotificationPolicy`: the tray
fingerprints on `{severity}:{title}` and clears an episode only when
that pair is **absent from a poll**, which a resolve-and-re-raise inside
one agent run never produces — a resolved row replaced by a fresh one
carrying a new message produced **no notification at all**, where the
same fault escalated to `critical` spoke and a forked title spoke. Two
audible repeats; the second is forbidden, the title being the identity
key for dedup, for the resolve and for the tray.

So a repeat at an unchanged severity is a **notification** decision and
went where notification policy already lives: `reminder_hours` in
`sysadmin_tray/notifications.py`, which covers every deduplicating
family rather than the estate's five surfaces alone. That breadth is the
point — `estate_judge` has produced **two rows in its life**, both
resolved, while the live instance on the day was `service_discovery`'s
`Unmonitored systemd units: 8 findings`, the **only** unresolved row on
the box, open 24 hours and spoken once.

**24 h is derived, not picked**: it matches
`self_monitor.escalate_after_hours`, so a family that owns a ladder
escalates to a different fingerprint — a new episode, spoken at once —
before any reminder of its quiet rung is due. The clock runs from **when
the tray last spoke**, not `alert.created_at` (`stalls.py`'s rule, and
it keeps the one injected clock). A reminder is never transient, shares
the fault's fingerprint and snooze key, and folds apart from new alerts
into `FP_REMINDER`.

**A defect the fixtures were structurally unable to catch**, found by a
probe: `state.first_notified_at or state.last_notified_at` reads a
monotonic `0.0` as absent and falls back to the field every reminder
resets, so each reminder reported the interval ("24 hours") rather than
the age of a fault that had stood three days. `FakeClock` starts at
`1000.0`; the new test starts at zero on purpose.

Both docstrings that had said the omission was deliberate — `estate/agent.py`
and `core/escalation.py` — now say why the alternative was **refused**, so
nobody re-derives the rung. Suite **1802** (from 1792), ruff and mypy clean,
no migration, no route, no backend behaviour change. Follow-up opened:
`SNAG-TRAY-007`.

### judge_attention, against data — SNAG-ESTATE-002's half (2026-08-16)

**An alert family that could not be shown to work.**
`GET :8400/api/projects/attention` has answered `{"health": [],
"nudges": []}` on all four occasions anyone has looked, so every rule in
`judge_attention` was pinned against dict literals written by the same
hand that wrote the consumer. A literal cannot express volume or length,
and both turned out to be wrong.

A populated payload was made from the producer's own code — driven
read-only in its own venv against the live estate database, with
`effective_threshold` forced to 101 and `default_days` to 0 so live rows
qualify, and `dataclasses.asdict` over the producer's own `Nudge`.
Committed as a fixture with its provenance, the two forced numbers
visible in the data.

**Two defects, both rules already written down elsewhere here.** The
family raised **31 rows from one poll** (26 health breaches + 5 nudges),
where the ports family has had `port_breach_max_rows` since Session
26b-A — now `attention_max_rows` (5), per family, since the two fail
independently. And the message ran to **469 characters** into a
notification body that a daemon cuts wherever it likes — now
`truncate_at_word` at 120, marked, with the full text kept in `details`.

`tests/test_estate_project_contracts.py` gains the route as its third,
with the per-entry assertions **pre-staged** to start running the first
day the estate publishes anything, and an assertion that fires when
estate-manager closes its side. Verified live and rolled back: raise →
hold → resolve across three runs, 0 rows of residue.

### One copy of the autogenerate rules — SNAG-DB-003 (2026-08-16)

**The only open item in this repository whose failure mode was data
loss, and it failed green.** `include_object()` in `alembic/env.py` and
`_include_object()` in `tests/test_schema_drift.py` were hand-copies of
each other. The two fail in opposite directions: an exclusion present
only in `env.py` makes the drift guard fail loudly, while one present
only in the *test* is silent — the guard stays green while the next
`alembic revision --autogenerate` writes `op.drop_table` into a
migration whose author was doing something else. Fired in a scratch
script before the fix: with the exclusion removed, autogenerate proposes
`remove_index`/`remove_table` for both frozen tables, against **3,739**
and **4** live rows.

**Session 43 filed it with the design question open, and it answers
itself once ownership is stated the right way round.** `env.py` cannot
import from `tests/`; a shared constant in `sysadmin/` looked like
pushing a testing concern into the shipped package. It is not —
`include_object` is what `alembic revision --autogenerate` uses whether
or not a test suite exists, so this is **production configuration the
drift guard borrows**, and the guard is the second caller.

**It went beside `Base` in `sysadmin/metadata.py`**, not into a new
module, because that file's docstring already argues this exact case for
the *model set*: "a table missing from one copy and not the other is
exactly the silent drift the drift test exists to catch". Which of the
live schema's tables the metadata is authoritative for is the same
question one step further. `COMPARISON_OPTS` travels as one dict, splat
by `env.py` into `context.configure` and by the guard into
`MigrationContext.configure(opts=…)`.

**Widened from the exclusion list to the whole comparison.** The flags
were hand-copied too, and they fail the same silent way: `compare_type`
set in `env.py` and absent from the guard leaves the guard green *while
blind to exactly the drift it certifies*. Six option names now have one
statement between them.

**Not moved, deliberately**: the `SET search_path TO public` both
callers issue. It belongs to the connection rather than to the
comparison — `env.py` pairs it with `CREATE SCHEMA IF NOT EXISTS`, DDL
the guard must never run — and its drift fails in the **loud**
direction, double reflection producing phantom diffs rather than a pass.

**`tests/test_autogenerate_config.py` (5 tests) stops the copy coming
back**, which is a live risk rather than a hypothetical one: the natural
way to add a table to the exclusion list is to edit whichever file you
are looking at. It is an AST sweep over every module — no second
`include_object`/`include_name`, no second `FROZEN_TABLES`, none of the
six option names passed by hand as a keyword or an `opts` key. Textual
because `env.py` **cannot be imported**; it runs the migrations at
module scope. This is the opposite of the assertion Session 43
considered and rejected — not "the two bodies are identical" (which pins
the copy) but "there is no second body".

**Two of the five tests exist so the detector can be seen to fail**, the
vacuity lesson `SNAG-TRAY-006` paid for: one runs the walker at the
owner, which must trip every rule, so a green sweep cannot quietly mean
the path was wrong; one feeds it the code this session deleted. A third
asserts both callers still *import* `COMPARISON_OPTS`, because a file
that configured nothing at all would pass an absence check while taking
alembic's defaults in silence.

**Verified live rather than only against literals.** `uv run alembic
check` reports "No new upgrade operations detected" — which exercises
`env.py` itself, the file no test can import — `alembic upgrade head
--sql` still renders offline mode, and re-adding a test-only exclusion
to the drift guard makes the new sweep fail naming file and line. Suite
**1776 passed** (from 1771), ruff and mypy clean, **no migration**, **no
new route**.

**Found while measuring, and it blocks the frozen-table drop**: the
estate's copy of `project_snapshots` holds **3,713** rows in the window
this repository's table covers, against **3,739** here. The 26 missing
are dated **2026-08-13** — one per project from the final organiser run
at 07:35, after the copy was taken. Recorded on the tasks.md drop entry,
whose own warning ("a copy verified once is not a copy verified twice")
is precisely what this measurement was.


### The reload re-times the scheduler — SNAG-RELOAD-001 (2026-08-15)

**Session 50**, Session 49's own follow-up, closed by **removing** the
divergence rather than reporting it better. The entry offered two
mitigations — store the last `ReloadReport` and serve it, or raise it as
an alert row — and named a third option in its last line. The third
shipped: the first is a field nobody polls (`SNAG-CFG-001`'s shape) and
the second needs a settled dedup and resolve lifecycle before it is
written, while still only *describing* something this repository can
simply not have.

`sysadmin/core/jobs.py` holds the plan — `plan_jobs(config)` maps an
`AppConfig` to the nine jobs it asks for, `apply_jobs` reconciles a
scheduler with it — and `Scheduler` gained `sync_interval`, `sync_cron`
and `remove_job`. The lifespan and the reload now call the **same**
function, so the schedule at startup and the schedule after a reload
cannot be produced differently. `RESTART_ONLY` went from **fifteen leaves
to two prefixes**: `service` and `database`, covering the socket, the
logging setup and the engine.

**The obvious implementation is a line shorter and breaks the schedule.**
`reschedule_job` recomputes the next fire from *now*, so re-applying every
job on every reload leaves a 24-hour job permanently 24 hours from the
most recent reload — which on a box being poked at is never. That is
`agent_first_run_delay_seconds`'s failure with a reload standing in for a
restart. An unchanged trigger is therefore left untouched, decided against
the **live** job rather than a remembered plan: a remembered plan is a
second statement of what the scheduler is doing, which is what the snag
was.

**The guard test was rescued rather than lost**, and rescuing it found a
defect in the guard itself. `tests/test_reload.py` walks the lifespan and
requires every config path it reads to be classified; moving fifteen of
those reads into `core/jobs.py` would have hollowed it out silently. It
now walks both and gained a second half — each `JobSpec`'s declared
`config_paths` must equal what `plan_jobs` actually reads. Writing that
showed the walker treats `delay = schedules.agent_first_run_delay_seconds`
as an alias assignment, which is syntactically identical to one and
semantically the opposite: it dropped a real leaf, silently, which is the
guard failing in exactly the direction it exists to catch.

**1771 tests pass** (from 1733), ruff and mypy clean, no migration.
**Verified live** against the real `config.yaml` and a real
`BackgroundScheduler`, in-process and touching neither the daemon nor the
file: 999 s became `interval[0:16:39]`, `retention_purge` moved 03:00 →
04:00, a disabled `estate_judge` had its job removed and re-enabling added
it back with the first-run delay, and `requires_restart` came back `[]`
where Session 49 reported three leaves.

### The reload path — removing the class, not the instance (2026-08-15)

**Session 49**, `SNAG-UNITS-005`'s durable half. Three sittings running had
handed a restart forward because the daemon reads `services.yaml` once, in
the lifespan. `sysadmin/reload.py` re-reads both configuration files on
`SIGHUP` or `POST /api/sysadmin/reload`.

**The design question was real and its premise was false**, which is the
sitting's finding. It was filed as *"config.yaml, which holds thresholds
the running agents have already read"*. They have not: every agent calls
`get_config()` inside `_execute`, because `SNAG-AGENT-003` forbade agents a
startup hook — a constraint written for event-loop safety that bought
per-run configuration for free. Only **fifteen** leaves are genuinely read
once, and they are enumerable.

**The blocker was privilege, not design.** `sysadmin.service` is a system
unit running `User=gaddi`, so the owner may signal it without `sudo` —
probed with `kill -0`, which tests permission without delivering.
`systemctl reload` would need an `ExecReload=` line and *that* edit does
need `sudo`; the raw signal does not.

**Three decisions taken.** Reload both files and **name what was ignored**
rather than refusing the config half — refusing blocks a threshold fix on
an unrelated edit and the operator restarts anyway. **Both triggers, one
function** — the signal needs no `sudo`, the endpoint is the only one that
can return the report. **Prune per-service state, never reset it** —
resetting re-arms the three-poll degraded streak at the moment an operator
is most likely to be reloading *because* something is failing.

**Verified live on the instance that motivated it**: with Session 48's
three entries removed to stand in for the running daemon, a reload of the
real file reports them `added`, installs all three, and reports
`requires_restart: []`. A broken `services.yaml` beside a valid
`config.yaml` installs **neither**.

**1733 tests pass** (from 1708), ruff and mypy clean, no migration. One
follow-up filed (`SNAG-RELOAD-001`) and one rule finally enforced: nothing
below a composition root may import one, which `metadata.py` had asserted
in prose since Phase 2.

### The execution sitting — the advice, carried out (2026-08-15)

**Session 48.** Three sittings (46, 47, 26c) went into making the
diagnosis speak. This one carried out what it says, and **two defects
surfaced inside an hour** — neither visible by reading the code, both the
same root cause: `recommendations.py` under-reading a `UnitFinding` the
sweep had already filled in.

**The advice never asked whether the unit is meant to be running.** Two
of five `host` snippets named units that are disabled and inactive.
Pasting them declares `kind: systemd`/`kind: timer` checks — which assert
*active* and *armed* — returning `critical` **every 300 s for ever**,
verified against the live box. The pile-up Sessions 41–45 spent
themselves deleting, arriving through this module's own remediation text.
The signal to prevent it was already measured, already stored, and
already trusted by the orphan family for `armed`.

**And `removal_command` left a folded oneshot's timer installed** —
`ticktick-sync.timer`, whose `Requires=` would have pointed at nothing,
and which is the half holding the enablement symlink the command's own
docstring exists to avoid orphaning.

Executed: `garmin-sync.service` removed (the armed orphan, enabled since
February — the emitted command ran **verbatim**), `sysadmin-tray.service`
start limit bounded (systemd's own reading matches the advice's
arithmetic exactly, and `restart_bounded` flips `False → True`), and
three host units wired into `services.yaml`, all checking **`ok`**.

Suite **1708 passed** (from 1701), ruff and mypy clean, no migration.
Blocked and named: five system-scope orphans and the deploy restart need
`sudo` (`SNAG-UNITS-005`); eleven restart-unbounded units belong to other
repositories and stay as advice.

**The collation half was already closed** — all 12 databases read
`datcollversion = 2.44` against a live 2.44, all 8 alert rows `resolved`,
one row each. "8 stale collations" was a stale reading.

### Port collision detection — the half the estate cannot do (2026-08-15)

**Session 26c.** `sysadmin/units/ports.py` reads `ss -H -ltnp` and
`/proc/<pid>/cgroup` and answers the question estate-manager's audit is
*structurally* unable to ask. Their `live_listeners()` runs `ss` without
`-p`, on the stated grounds that *"process names need privileges for
other users' sockets"* — true, and true only of *other users'*. Measured
as `gaddi`: **31 listeners, 24 attributed**, every registry-relevant port
on the box named with its unit **and its scope**, blank only for the
root-owned and containerised ones (5432, 1883, 631, 139/445, 8601).

Suite **1701 passed** (from 1653), ruff and mypy clean, **no migration**
— the block rides in `unit_audits.findings['ports']`.

**There are three port registries here and only one cannot lie.** The
estate's markdown table (18 rows, projects, no units); this repository's
`services.yaml` (11 entries carrying `port:` *and* `systemd: {unit,
scope}` — a hand-declared pair that has existed since Session 35 and had
**never been checked**); and the kernel. This is the only party on the
box holding all three, which is the whole argument for the session.

**Four comparisons in two families, and the split decides the surface.**
`wrong_unit` and `port_shared` are the box disagreeing with itself now —
one alert row per port, port in the title. `duplicate_claim` (invisible
to the estate because `claimed_ports` is a `set`) and `wrong_project` are
a document being wrong while the box is right — ranked advice, last in
`KIND_ORDER`. The armed-orphan split, applied a third time.

**Everything came back clean, which is the expected result and the
honest one.** All 11 declared port↔unit pairs agree with the live cgroup
map; no port has two holders; no registry row is duplicated. *"Nothing on
this box has ever collided"* is now **verified with attribution** rather
than asserted. The one thing the check did find is a registry row: 8500
is given to `sysadmin-service`, which is neither the manifest id
(`sysadmin-assistant`) nor the directory (`sysadmin_assistant`) —
recorded as evidence rather than a finding, because a row may
legitimately name a third-party daemon (`_syncthing_` holds 8384), and
filed as `SNAG-ESTATE-005` for its owner.

**Verified live rather than only against fixtures**, since the family
ships with zero rows — the estate judge's starting position. The whole
agent path ran against the real database in a rolled-back transaction:
the sweep stored the block, and a synthetic `wrong_unit` gave raise →
hold → resolve across three runs with **0 rows of residue**.

**One bug the tests caught that mypy could not.** `select(Alert.title)`
yields the titles themselves, and the dedup read them as `row.title` —
which on a `str` silently returns the bound `str.title` **method** rather
than raising. Every membership test failed, so the family would have
raised a duplicate row on every sweep. Found by the "a standing
collision writes one row" test on its first run.

**`SNAG-UNITS-001` folded in and fixed**, and its own premise is what
changed: it argued a comment was the only honest fix *because* "this scan
does not know the unit's port". True of the sweep; no longer true of its
siblings. The snippet now emits `kind: http` with a real url and port
when the unit holds exactly one audited port. Two limits, both measured:
its population is **empty today** (all 12 port-holding units are
`monitored`, which `classify_units` drops — SNAG-UNITS-002's shape
again), and `/api/health` is right for **4 of 11** declared entries and
wrong for 7. Kept anyway, as `SNAG-UNITS-003`, because a wrong url fails
loudly within one poll where `kind: systemd` under-monitors silently for
ever.

### The restart-limit family — 13 units advised on, none of them alerted (2026-08-15)

`SNAG-UNITS-002`. 17 of the 20 hand-written units on this box that
declare `Restart=` have a start limit their own restart cadence can never
reach, so a crash loop never enters `failed`, no `OnFailure=` hook can
fire, and `systemctl is-failed` reports nothing wrong. That is the
estate-wide form of `SNAG-ESTATE-001`, whose two PersonalAssistant units
restart-looped 52,178 times in exactly this state. Suite **1653 passed**
(from 1631), ruff and mypy clean, no migration — the family lives in the
audit's JSONB blob.

**The detection already existed and had done since Session 46.**
`restart_is_bounded` was written for the armed-orphan family and every
finding has carried `restart_bounded` since. What did not exist was any
surface naming the units, and the reason is the measurement nobody had
taken: **11 of the 13 are `monitored`**, and `classify_units` drops
monitored units before they become findings. The question "which units
here can loop for ever" was answerable for the six the sweep already
described and invisible for every live service on the box — the snag's
own entry costed the fix as "one line per unit" without noticing that
two thirds of the population had nothing to hang a line on.

**Measured live rather than inherited**, and the entry's figures moved
again: 17 of 20 unbounded, of which 11 `monitored` (`venture-*` ×4,
`sportsanalyser-*` ×2, `alfred-inference`, `estate-manager-api`,
`estate-manager-searxng{,-shim}`, `sysadmin-tray`), 4 `orphaned`, 2
`host`. The family ships with **13**, not 17.

**Orphans are excluded, which is the opposite of the obvious rule.** A
broken unit that also loops reads like the worst case and belongs here
twice over. It cannot: the orphan recommendation is *remove it*, and a
start limit on a file you should delete is two contradictory
instructions for one unit. Nothing is lost — an armed orphan that loops
is exactly what `armed_alert_severity` already promotes to `critical`.

**Advice-only, and the count rides in the roll-up's `details` as
evidence.** Deliberately *not* added to `scan.actionable`, which is the
roll-up alert's title and the number `alert_threshold` is compared
against: 13 latent risks there would trip the threshold on their own and
would read as 13 new units to wire up. No alert family of its own, for
the reason the armed split was worth making — one row per unit is right
for a fault in progress and wrong for a latent one.

**Ranked second, above `unmonitored`**, because the two are competing
safety nets and this is the stronger one: a wedged unit is seen as
`unreachable` only if something polls it, whereas a reachable start limit
makes systemd itself say so, to a hook, whether or not this service is
running.

**The suggested window is checked against the arithmetic that produced
the finding.** `suggested_start_limit_interval` picks the smallest round
value clearing `RestartSec x (burst - 1)` by 1.5x, and a test feeds every
live shape back through `restart_is_bounded` and requires `True` — a
remedy that clears a symptom without fixing the fault is the trap
`REFRESH COLLATION VERSION` set for the collation family. A second test
appends the emitted snippet to a real unit file and re-scans, which is
the only thing proving the two lines land in a section systemd reads
them from. Where no window would help (`RestartSec` beyond an hour,
`infinity`) it emits **no snippet at all** and says to lower `RestartSec`
instead.

**The first snippets this repository has emitted for a file another
repository owns.** `snippet_target` is the absolute unit path rather than
a filename so the two destinations cannot be confused, and the `detail`
names the owning project — 11 of the 13 belong to four other
repositories. It stops at text served over a GET, which is a pointer.

**`UnitFinding` now carries the three numbers the verdict was computed
from** (`restart_sec`, `start_limit_interval`, `start_limit_burst`).
Without them the boolean asks a reader to trust arithmetic they cannot
see, and the naive version of that arithmetic is wrong in both
directions.

**Verified live, end to end**: the real sweep written to `unit_audits`
and read back through the router's rehydration in a rolled-back
transaction — blob carries `restart_unbounded_count: 13`, the arithmetic
inputs survive JSONB, and `/actions` builds 25 recommendations (6 orphan,
13 restart, 1 unmonitored, 5 host). Residue 0.

**What is deliberately not done**: nothing here edits a unit file, and
the two `deadlock-api-ingest` twins get scope-suffixed titles because
they are two different binaries under one name — the `host` tier still
prints that pair with identical titles, which is pre-existing and
untouched.

### SearXNG wired — the deploy-triggered guard closed the same day it fired (2026-08-14)

`test_searxng_wiring.py` went red on 2026-08-14 when estate-manager
deployed SearXNG, which is precisely what it was built to do, and the
gap was closed the same day. `services.yaml` now carries the entry.
Suite **1631 passed, nothing skipped, nothing red** (was 1627 passed,
1 failed on purpose, 1 skipped); ruff and mypy clean; no migration.

**Every handed-over value was verified rather than copied**, and one of
them was wrong in the direction that would have mattered. The pre-staged
block named `/healthz`; the shim proxies unknown paths upstream, so
`http://localhost:8600/healthz` reaches SearXNG's own liveness ping and
returns **200 whenever the container is running — including when every
search fails**, which is the one case `kind: http` was chosen to catch.
It answers 200 today, so that wiring would have looked right on the day
and been blind on the day it mattered. The live entry polls
`/api/health`, the only path that knows whether searching works.

**The status ladder was driven, not read.** `_check_http` was run
against a real socket returning each code: 200 → `ok`, **424 →
`degraded`** (SearXNG up, searching broken — a fault off this box),
**503 → `critical`** (container dead). `_handle_status` already requires
three consecutive degraded checks before raising, so the estate's "worth
an alert only if it stands" needed no work: a captcha'd engine is silent
for 15 minutes, a standing outage is not. Live check against the running
shim: `ok` in **23 ms**, `status: healthy`, probe 153 s old, 20 results,
no unresponsive engines.

**A second entry the plan did not ask for.** `searxng-upstream` declares
the 8601 container `monitor: false` with a reason. Its health is already
covered by the shim's 503 and a second check would give one fault two
alert rows — but omitting it from the file put it in the unit sweep's
`host` findings *permanently*, unactionable, with "watched through the
shim on purpose" indistinguishable from "nobody wired it up".
`venture-chat-large` carries the same shape. Host findings 9 → 8.

**Item 3's rationale was narrowed, not inherited.** The no-`project:`
rule was written on "third-party software with no repository"; the shim
that actually serves the URL is estate-manager's code and *does* have a
manifest, so the field would now resolve. The omission stands on
narrower ground, decided by the owner: this entry judges whether
**searching** works, and a 424 is upstream engines failing off this box
— not the estate-manager repository's fault to carry.

**The guard changed shape rather than retiring.** Its gate now separates
environments rather than dates: CI has no searxng unit, so the three
assertions skip there and run here against the live box, where before
they skipped everywhere and the file was unfalsifiable. The `kind: http`
assertion is **stronger** — it asserts *exactly one* searx entry is
checked before asserting that one is HTTP, because merely skipping
unmonitored entries would let someone silence the family by muting the
shim and still pass. Both real unit names are pinned into the gate's
cases: **neither is any of the three spellings it guessed**, so the
substring match is the only reason it fired.

**Not deployed.** `sudo systemctl restart sysadmin.service` needs a
password this session could not supply; the daemon holds `services.yaml`
in a process-wide singleton, so the entry is inert until that runs.

### Session 26b-A: the estate's port findings get a voice (2026-08-14)

The estate has reconciled its port registry against the box's live
listeners since 2026-08-13, correctly, and **nothing on this box ever
said so**. `judge_audit_findings` now judges the audit's `ports` check
per finding. Suite **1626 passed, 1 skipped** (+29), ruff and mypy clean.
No migration.

**Most of the session was checking whether the plan was still true, and
it was not.** Session 26b was scoped on 2026-08-07; `estate-manager` was
created on 2026-08-11 and built its conformance audit on 2026-08-13.
Three of its four checkboxes had been overtaken:

- **Item 1 inverted.** "Move the registry into `config.yaml`, render the
  guide's table from it" — but the guide moved to estate-manager, and
  its audit now *parses that markdown table as its source of truth*, with
  a guard that errors rather than reporting zero findings on an empty
  parse. Mirroring the registry here would break their check and have the
  monitor own a cross-repo convention. **Killed, not deferred.**
- **Item 2 was already built** and has earned its keep — the
  `unclaimed_listener` breach is how syncthing's 8384 got a registry row
  on 2026-08-13.
- **Item 3 was delegated** to estate-manager as `SNAG-ESTATE-004`.
- **Item 4 is genuinely ours** and became Session 26c.

**What replaced them outranked all four.** The estate files findings and
never alerts; `judge_audit_invariants` deliberately judged only whether
the audit *ran*. So a `breach` was detected, correct, machine-readable,
served at `:8400/api/audit/findings` — and unread. That is precisely the
shape Session 46 spent itself removing for units one day earlier
(*"the diagnosis was complete, correct and machine-readable the entire
time; a count is not news"*), reproduced one layer up.

**The narrowing of rule 3 is exact, not a reversal.** Both of its
original reasons still exclude what they excluded, and the filter is
`check == "ports"` rather than a severity because **all four** estate
checks emit `breach`: a severity-only rule would re-import the collation
family this service already raises (its own alerts through a second
producer) and pull in `pointers`/`seams`, which are other repositories'
conformance. Ports are the exception because **no repository owns a
port** — and since the estate may not alert, the choice was never who
speaks but whether anyone does.

**Three rules that were the opposite of the first draft.** `warn` is not
judged — `claimed_but_silent` is availability, which `services.yaml` plus
the `% unreachable` family already owns, and that today's one live `warn`
(port 3300) does not overlap is luck, its registry row reading "unit to
follow". Above `port_breach_max_rows` the family **collapses to a
roll-up**, the inverse of Session 46's rule and its complement: six
unclaimed listeners at once is a table moved or truncated, not six
services. And `audit_invariants`/`audit_findings` are **two surfaces**
though they come from one check run — two HTTP calls that fail
independently, and the sweep is scoped per surface, so sharing an id
would let "the audit completed" close port rows raised off a payload
nobody received.

**Verified against the real detector, not only literals**, because this
family ships with **zero live rows** and that is `SNAG-ESTATE-002`'s
starting position. The estate's own `run_check` was driven in-process
against the live registry document with a listener bound on 8888:
clean → `breach` → clean, no write to the estate's database. It caught
one defect no literal would have — the estate stamps a first sighting
`standing_days: 0.0`, and "Standing 0 days" reads as a rounding artefact.

**Two corrections made in passing.** Session 26b's last checkbox named
`sysadmin/services/units.py`, gone since Session 35's module split (the
same stale-path defect as commit `ce71bef`); and this snag list's header
claimed `count_open_snags` reports 15 — it reports **47**, measured
against the estate's parser, which is also no longer in this repository.

### The unit sweep learns to speak — SNAG-ESTATE-001's durable half (2026-08-14)

An orphan finding no longer waits to be fetched. The sweep now measures
whether an orphan is **armed** — systemd will start it — and each armed
one gets its own alert row naming the unit and scope, beside the roll-up
rather than instead of it. Suite **1597 passed, 3 skipped**, ruff and
mypy clean. No migration.

**The failure was never detection.** Both PersonalAssistant units were
classified `orphaned` with the dead path and the cause in plain English
eight days before anyone looked, and `Unmonitored systemd units: 17
findings` was open the whole time. A count cannot name the thing that is
on fire.

**The obvious rule for "will it loop" was wrong in both directions**, and
the live units refuted it before it was written.
`personalassistant-backend.service` declares no start limit, so systemd's
defaults apply — one *does* exist. It also sets `RestartSec=10`, so five
starts can never fit inside the ten-second window: the limiter is
unreachable and it restarted 34,517 times without once entering `failed`.
Meanwhile a bare `Restart=always` restarts every 100ms, five starts fit
easily, and the loop terminates. The real test is arithmetic —
`RestartSec × (StartLimitBurst − 1) < StartLimitIntervalSec` — the same
sum Session 39 did by hand for `sysadmin.service`.

**Both signals are pure**, so `scan.py` keeps its no-subprocess promise:
an enablement symlink under a `*.wants/` directory it already walks, and
four keys of unit text it already parses. Agreed with `systemctl
is-enabled` on every unit on this box.

**Live: 1 armed orphan of 6** — `garmin-sync.service`, one `warning` row.
The four `Restart=always` orphans are harmless only because someone
disabled them, so they stay in the roll-up as debt. Verified in a
rolled-back transaction against the live database: five runs of one fault
wrote 2 rows (raise, dedup, escalate, hold, resolve), roll-up untouched,
residue 0.

**Filed, not fixed: `SNAG-UNITS-002`** — *fixed 2026-08-15, see the top
of this section.* 15 of the 18 units on this box with a `Restart=` policy
cannot reach `failed`, including every live service except `sysadmin`,
`alfred-backend` and `alfred-frontend`. Not alerted on — 15 rows on the
first run is the pile-up shape wearing a new hat. (Both figures moved
before the fix landed: 17 of 20 by the next morning, because the defect
is what a correctly-written unit gets by default here.)

### SearXNG pre-staged — a delegated requirement made mechanical (2026-08-14)

The estate's SearXNG task **stays unchecked**: the trigger is
estate-manager deploying it and claiming a port, and it has not fired —
no unit on either bus, nothing listening, no registry row. So the
`services.yaml` entry cannot be written, because `url` and `port` are
the deploy's to decide. Pre-staged at the owner's request. Suite **1546
passed, 3 skipped**, ruff and mypy clean.

**The commented block is the smaller half.** It sits in `services.yaml`
beside `mosquitto` with every decided field and `<PORT>` where the two
unknowns go. But the failure this item exists to prevent is *a unit
ships and nobody notices*, and a comment does not prevent it —
`tests/test_searxng_wiring.py` does. It skips while no searxng unit
exists and fails from the moment one does, gated on the **unit file**
rather than a port probe (a probe flips off exactly when the service is
down) and matching the substring `searx` rather than one spelling (a
container deploy names its unit `podman-searxng.service`). Nine ungated
tests drive the gate against a fake estate under `tmp_path`: a gate that
has never fired and a gate that cannot fire look identical from outside.

**One part of the task was already enforced; another was at risk from
the thing enforcing it.** The Session 26 unit sweep catches a
hand-written searxng unit unaided, files it `host`, and omits `project:`
— so that decision needs nobody to remember it. Its snippet says
`kind: systemd` though, because the scan cannot know a port, and a unit
check passes a SearXNG that is up while every search errors. Following
the sweep would have *appeared* to close the item. Filed as
`SNAG-UNITS-001`. Fixed in passing: an `unmonitored` finding's `reason`
named `projects.yaml` and `config.yaml`, two files that no longer exist,
in a string the operator reads.

### Session 46 — three snags, and one of them had bad advice in it (2026-08-14)

`SNAG-AGENT-006` fixed, `SNAG-TRAY-006` fixed, `SNAG-ESTATE-002` handed to
the repository that owns it. Suite **1537 passed**, ruff and mypy clean.

**The snag entry's own remedy was wrong, and following it would have
undone SNAG-AGENT-004.** It said dedup and `RESOLVABLE_TITLE_PATTERNS`
are mutually exclusive, so the service and threshold families had to
leave the tuple — which would have stranded every deconfigured service's
rows again, since a set built from configuration cannot contain a service
that has left it. That mutual exclusion held only of an exclusion set
made of the titles a run **raised**. `sysadmin/estate/agent.py` had
already shown the third option and Session 45's handoff named it: exclude
what the run **judged**. Dedup suppresses the raise, never the judgement.
The patterns stayed; `_raise_judged` is the whole fix.

Two corrections fell out of it. `% auto-restarted` is exempt via an
explicit `dedup=False` — `_failure_counts` resets the moment
`restart_unit` returns, so it fires once per restart *cycle* and a second
restart hours later is news that dedup would swallow. And the recorded
reason `collation` stays out of the sweep was itself wrong: the real
reason is that it resolves its own rows by id, not mutual exclusion — a
correct conclusion drawn from a premise that has since moved, which is
the kind that gets a guard removed later for the wrong reason.

**Verified against the live database, rolled back**, because the suite
stands in for PostgreSQL's `LIKE` with a Python matcher and cannot prove
the patterns select the right rows in real SQL: ten sustained runs of one
threshold fault left **1** row where the old code wrote 10; three
auto-restarts left 3; residue 0.

`SNAG-TRAY-006` got a consumer-driven contract test — a recorded 8400
payload plus a reachability-gated live pair sharing one set of
assertions. `estate-lib` was rejected: the two shapes are a *tolerant
consumer parse* and a *producer guarantee*, different jobs, and one class
would make the tray's defensiveness the producer's problem. The design
work was the vacuity — `from_dict({})` **succeeds**, so "does it parse"
would go green against a producer serving nothing.

`SNAG-ESTATE-002` was recorded in estate-manager (as its
**`SNAG-ESTATE-010`** — the IDs are per-repository and that repo already
has a different `002`) and fixed nowhere, per its ADR-0002. Reading the
producer turned up three things the entry did not have: the drift has
**already happened** (`Nudge.message` shortens the action to 120 chars,
this side interpolates it whole), `nudge_title` has **no production
caller** in that repository at all, and its justifying comment cites a
symbol that no longer exists there.

Also closed: Session 45's two time-boxed checks. Both estate timers fired
overnight, so `estate_judge` correctly stayed silent and **has still
never raised a row in production**; `/api/projects/attention` is still
empty even after a scheduled scan, so `judge_attention` remains
unexercised against real data. Filed on the way: `SNAG-AGENT-007`.

### Session 45 — the judging session (2026-08-13)

`estate_judge`, a fifth agent, closes the half of the Session 4 cutover
that was deliberately left behind: the estate manager publishes and never
acts, and until this ran it computed idle nudges every night into a
surface nothing read. **Four surfaces, not the two the task named** —
the scan's invariants and `attention` as planned, plus the audit's
invariants (estate ADR-0009 requires sysadmin to judge them: "the estate
never grades its own audit") and the queue's (ADR-0007; `services.yaml`'s
own comment already called that ours to judge). Hourly.

**The lifecycle is the interesting part.** `collation.py` records that
dedup and a set-based resolve are mutually exclusive, and they are —
*there*, because that sweep excludes the titles the run **raised**, so a
deduplicating family has its still-true row resolved and re-raised on
alternate runs, clearing the tray fingerprint each time. This agent
excludes the titles the run **judged**, which is a different set, and it
can do that only because it owns every row it sweeps.

**Three rules taken against the obvious implementation**: a cumulative
total is never judged (`dropped_total` is already 1, so a `> 0` rule
raises an immortal row — `redis unreachable`'s 6,283 by a fourth route);
the sweep is scoped to the surfaces the run actually read, so a partial
pull cannot announce a recovery from a payload nobody received; and
unreachability is not judged at all, because `estate-manager-api` is
already an `http` entry in `services.yaml` and a second owner of one
lifecycle closes a row while the first still holds it true.

**Verified live** in a rolled-back transaction against real 8400
payloads: run 1 raised 3, run 2 raised 0 and resolved 0 with all 3 still
open (the flip-flop that had to be avoided), restoring thresholds
resolved exactly 3, and a dark surface resolved nothing. Residue after
rollback: 0 rows.

Found on the way and fixed: `Alert.__table__`'s `chk_alert_agent` had
never gained `service_discovery` from migration 007 — alembic does not
diff CHECK constraints — and `test_units_api.py` pinned `AGENT_NAMES` to
migration **007** by set equality, so every new agent broke an unrelated
session's test. Split into a fact about 007 and a self-locating invariant
against the newest widening migration.

Filed rather than fixed: `SNAG-ESTATE-002` (the producer's `Nudge.title`
and `.message` are `@property`, so `asdict` drops them and this
repository builds a format the estate believes it owns) and
`SNAG-ESTATE-003` (no escalation for these families).


- **2026-08-13 — Session 44: the collation check (`SNAG-DB-002`).** A
  glibc upgrade moved this box from locale data 2.43 to 2.44; PostgreSQL
  has been printing a mismatch warning on every `psql` connection since,
  read by nobody, while any B-tree index on text sits built against the
  old ordering — a lookup can miss a row that is present.
  `sysadmin/monitor/collation.py` reads `pg_database` once per sysadmin
  run and raises `Stale collation version on <db>` at `warning`. The
  snag said three databases; the catalog says **eight of eleven**, because
  the original number came from the databases someone had opened a shell
  against. Four rules, three of them the opposite of the obvious
  implementation: it fails **open** on NULL (deliberately the reverse of
  `schema_guard` — `template0` records no version, and inventing an alert
  whose remedy does not exist is the worse error here); it raises **once
  per open row**, because 300-second polling against a fault that
  persists for weeks would write 2,304 rows a day; and it therefore stays
  **out of `RESOLVABLE_TITLE_PATTERNS`** — dedup and that sweep are
  mutually exclusive, and combining them makes a row flip-flop, clearing
  the tray fingerprint on every flip. The `REINDEX` remedy is
  deliberately not automated and the alert names it **before** `REFRESH`,
  which alone would silence the warning without rebuilding anything —
  *and estate-manager automated exactly that ordering in
  `scripts/refresh-collations.sh` and ran it the same evening, which is
  where the remedy half of `SNAG-DB-002` actually closed.*
  Verified live in rolled-back transactions, both raise and resolve,
  residue 0. Filed on the way: `SNAG-AGENT-006`, the raise-side twin of
  `SNAG-AGENT-004` — 60 rows for one dead timer in five hours.

- **2026-08-13 — Session 43: `SNAG-DB-001`'s detection gap, all three parts.**
  The un-applied migration that blacked out monitoring for 39 hours was
  fixed on 2026-08-10 by applying it; the reason nobody noticed was the
  real defect, and it is now closed. **(1)** `sysadmin/core/schema_guard.py`
  compares `alembic_version` against the packaged head at startup and
  **refuses to boot** on a mismatch — not wrapped in a `try`, so the unit
  enters `failed` and `sysadmin-failed.service` announces it, making this
  the Session 39 machinery's second caller. The head comes from alembic's
  own `ScriptDirectory` rather than a regex over the version files, and
  `alembic_version` is read schema-qualified because the `projects`
  database holds another application's copy in `public`. Verified live:
  passes at 011/011, refuses a forced mismatch naming both revisions and
  the remedy. **(2)** One `session.begin_nested()` per service in
  `SysAdminAgent._execute` — load-bearing *because leaving the block
  flushes*, since `session.add` never talks to the database and the
  rejection previously surfaced at the single commit ending the run. A
  rejected service is recorded as `status="error"` rather than costing
  the other eighteen their check. **(3)** `sysadmin/monitor/failures.py`,
  a **sibling** of `stalls.py` on the shared ladder, not an extension of
  it: "has not run" and "ran and failed" are different states with
  different remedies, and the suffix `agent failing` is chosen so
  `_resolve_recovered` cannot reach it. **The threshold is a count of
  runs, never a duration** — the opposite unit from `escalate_after_hours`
  in the same config section, because `agent_runs` records a run rather
  than a schedule. Part (3) **was not implementable when the snag was
  filed**: before Session 41 a failed run left no row, so there was
  nothing to read. 61 new tests. One new snag filed at the estate-manager
  session's request — `SNAG-DB-003`, the autogenerate exclusion list
  hand-copied across `alembic/env.py` and `tests/test_schema_drift.py`,
  where the dangerous direction is silent: an exclusion present only in
  the test leaves `--autogenerate` willing to write `op.drop_table` for
  frozen data.

  _Ran alongside estate-manager's project-state cutover, which was
  editing this repository concurrently under the founding-extraction
  exception. `docs/adr/0005-project-state-leaves.md` arrived from that
  session, not this one._

- **2026-08-12 — Session 42: the log storm, fixed as a raise rule.**
  `SNAG-AGENT-005` — **598,091 unresolved alert rows**, 91 % of every
  unresolved alert in the table, 99.8 % of them two Bluetooth firmware
  messages from a kernel retry loop running at ~8.5 lines a second. The
  agent raised one alert row per matching log line, which is the mistake
  this application had already written down once, in
  `GET /api/services/reliability`'s docstring: a log is not an incident.
  The `SNAG-AGENT-004` inversion does not apply — a log line that was
  written cannot un-write itself, so "which open alerts would this run not
  raise?" answers "all of them, one run later". **Alerts are now keyed on
  a normalised fault signature**, one open row per fault, repeats bumping
  `details['occurrences']`, resolved when the fault goes quiet for 15
  minutes. Plain dedup on the existing title was refuted by the live table
  before it was written: `Log error: kernel` is shared by every kernel
  error, so the storm would have masked the RCU stall and the USB
  enumeration failure sitting in the same 30-day window. Verified live:
  **2,000 kernel error lines in ten minutes → 2 alert rows**, and the
  titles finally name the fault. The 598,091 existing rows were resolved
  as `superseded`; table-wide unresolved alerts went to **2**. Two smaller
  defects went with it — journal reads now resume from `__CURSOR` rather
  than re-reading a 2-minute window on a 60-second poll (**96 entries then
  0** on back-to-back runs, where every entry used to be stored twice), and
  the silent `-n 500` cap is reported as `details['truncated_sources']`.
  **`sysadmin.service` still needs restarting to pick this up** — it is a
  system unit serving start-time code.

- **2026-08-12 — Session 41: the two P1 agent defects, both with the filed
  cause corrected.** `SNAG-AGENT-003` — the file organiser having run once
  in its life — was neither of the two candidates the entry named. The
  scheduler fires and the agent *succeeds*: `BaseAgent.run` opened a
  transaction (insert + flush of the `running` row) before handing the same
  session to `_execute`, and this host sets
  `idle_in_transaction_session_timeout=1min`, so a 117.71-second scan had
  its backend terminated at t+60s and lost every write **including its own
  failure record**. The one surviving run, 2026-08-06, took 29.63 s — the
  only one ever to finish inside the timeout. `run()` is now three
  transactions and a failed run records that it failed.
  `SNAG-AGENT-004` was diagnosed correctly and **understated by about twenty
  times**: 27,827 rows for five retired services (not four — `nuxt-frontend`
  was missed) *plus* 24,097 resource-threshold rows that had no resolve path
  at any point in this application's life, `Critical disk usage on /` alone
  holding 13,971 open rows against a disk at 68 % since July.
  `SysAdminAgent._resolve_recovered` closes both families set-based;
  **51,924 rows in the population**, verified against the live table, with
  the only `agent='sysadmin'` row left open being the file organiser's
  stall. **Both were deployed and proven the same day**: the file organiser
  recorded 3 completed runs against **one in its entire life** before today,
  `filesystem_audits` went 1 row → 4, and **51,976 alerts resolved**, taking
  `agent='sysadmin'` unresolved from 51,925 to **43**. 1,939 tests green (+35).

- **2026-08-11 — Session 39's MQTT half unblocked, from the other side.**
  estate-manager's Session 2 (its founding MQTT extraction, executed
  under estate ADR-0002's bounded exception) removed both walls recorded
  below: Alfred's `reconcile()` now deletes only subscriber-role clients
  with no live token (Alfred ADR-0068), and the neutral root is live —
  `sysadmin-publisher` exists with role `estate-publisher` (write
  `estate/#`), provisioned from `estate-manager/mqtt/dynsec.yaml`, and a
  publish on `estate/alerts/test` reached a subscriber-role client with
  the identity surviving an alfred-backend restart. This repository's
  side: `sysadmin.service` gained
  `LoadCredential=mqtt:/etc/credstore/sysadmin-mqtt`
  ([ADR-0003](../adr/0003-mqtt-credential-by-loadcredential.md) — why
  not `config.yaml`, not an `EnvironmentFile`), pinned by a new
  `test_systemd_units.py` invariant; `services.yaml` gained
  `estate-broker-provision` (the estate's boot oneshot, `scope: system`)
  and — found while wiring it — **`mosquitto.service` itself, which was
  unmonitored**: a dead broker means alerts publish nowhere while every
  consumer reconnect-loops silently. The publisher code stays this
  repository's own open task; the credential file and unit install land
  with estate-manager's `scripts/install-broker-system-units.sh` (one
  sudo run, which also covers the Session 39 unit install below).

- **2026-08-11 — Session 39 (part 1): the alarm now keeps ringing, and the crash case can reach `failed`.** Two of the six scoped items shipped; MQTT publishing is blocked on an Alfred-side change and is written up below. **Detection was not touched, deliberately** — not one line of `self_monitor.py` changed, because it was never broken.

  **The escalation ladder.** A stalled agent is raised at `warning` exactly as before, and re-raised as `critical` once that warning has stood unresolved for `self_monitor.escalate_after_hours` (24). The shared half — `SEVERITY_ORDER`, `Ladder`, `step_for` — went into **`sysadmin/core/escalation.py`**, because the scoped instruction "reuse `nudges.py` rather than copying it" was not possible as written: `sysadmin/monitor` may not import `sysadmin.projects` (`tests/test_import_boundary.py`). Same move `strip_markdown` made into `core/text.py`, same reason.

  **Why `critical` specifically, and it is not about volume.** `sysadmin_tray/notifications.py` sets `transient=effective == "info"` on a first notification and `transient=False` only inside `_maybe_escalate`, which fires for `critical` alone — so **`critical` is the only severity the tray leaves on screen**. The owner's diagnosis was "I never saw the toast", away from the machine; a `warning` toast expires whether or not anyone was in the room. The second rung buys *persistence*, which is exactly the failure described. This is the opposite of the rule `nudges.py` encodes (a nudge never reaches `critical`, because criticals pierce DND and waking someone about a roadmap item is how a monitor gets muted wholesale), and the two docstrings now cite each other so the difference cannot read as an oversight.

  **The clock starts when the alarm rang, not when the stall began** — the open row's `created_at`. Both were computable and the obvious one is wrong twice over: it is the *telling* that failed, so the telling is what should be measured; and anchoring to the stall's own age would make a daemon outage produce **a wall of criticals on restart**, since nothing runs while the service is down and the first check back would escalate all five agents at once. That charges the estate for this application's downtime — the rule `GET /api/services/reliability` already encodes as "a gap in the series never costs points". **24 hours is measured against the slowest agent, not the fastest**: `file_organiser` and `service_discovery` run daily, so a stall that is merely late clears within one interval and a shorter gap escalates faults about to fix themselves.

  **The crash case, and the number that de-risked it.** `sysadmin.service` was `Restart=always` with no limit, so a crash-loop sits in `activating (auto-restart)` for ever and **never enters `failed`** — the state every failure hook watches. `StartLimitBurst=5` / `StartLimitIntervalSec=600` makes a loop terminal; `sysadmin-failed.service` announces it via `scripts/notify-unit-failed.sh`, persistently (`--expire-time=0`, `--urgency=critical`) and **to journald first**, that being the one destination which does not need anyone logged in. The trade — infinite retry rides out a slow dependency, and this app does exit rather than degrade when the database is absent (`verify_connection` raises in the lifespan) — was **measured before the edit, not assumed: `NRestarts=0` and zero "Scheduled restart job" entries in 30 days of journal.** The retry has never once fired here. The rollback, including the `systemctl reset-failed` that is easy to forget, is written into the unit file rather than a session note, and the handler was rehearsed rather than trusted. `tests/test_systemd_units.py` pins the halves together — either alone accomplishes nothing, which is the shape of half-change this repo has shipped before.

  **MQTT is blocked on Alfred, and on something the scoping session did not find.** The premise checked then was alfred-glance's closed renderer registry — real, but secondary. Mosquitto here is `allow_anonymous false` running the **dynamic-security plugin**, whose schema Alfred owns, and **`dynsec.reconcile()` deletes every client that is not Alfred's admin, not Alfred's publisher, and not a live device token.** A `sysadmin-publisher` created by hand survives until Alfred next restarts and is then deleted — best-effort, logged at `info`, no alert. For an *alerting* path that is this session's own bug reinstalled inside the fix. Decided: **Alfred provisions a protected non-device publisher, in its code.** And the namespace decision costs more than scoped — both dynsec roles are scoped to `alfred/events/#`, so the chosen neutral root (`estate/…`) is **denied by the broker** until those roles gain a filter. Terms of the promotion are now in [estate-map.md](../guides/estate-map.md), which had reserved this decision in writing.

  **Verified in production the same day.** The units were installed at 17:08 and the ladder fired on the very stall that motivated it: the `warning` raised 2026-08-10 09:07 is now resolved, replaced by a `critical` at 17:13:12 carrying `escalated: true` and `hours_since_first_alert: 32.1` — which the tray renders as a notification that stays on screen instead of the toast that was missed. A **unit failure now also leaves state**: `sysadmin/core/unit_failure.py` writes a critical row through the sync engine (the application is dead by definition — no event loop, no scheduler session, nothing subscribed), filed under `agent='sysadmin'` with `details.source = systemd_onfailure` carrying the provenance the constraint's five allowed names cannot express. **Paired with a resolve in the lifespan**, because the service starting *is* the recovery and nothing inside ever observed the failure; without that half it is an alert type that can only accumulate. Both directions verified against the live database.

  Two snags found sideways and recorded rather than fixed: **`SNAG-DB-002`** (every database on this box has a stale collation version — glibc 2.44 against `datcollversion` 2.43, 25 indexes in the `sysadmin` schema, and the `REFRESH` that clears the warning without rebuilding is the trap) and **`SNAG-SYSD-003`** (`After=ollama.service` on a runtime retired 2026-07-24, left in so the unit change kept one rollback path). `SNAG-AGENT-003`'s **second half is addressed** — the alert would have gone persistent on 2026-08-11 09:07 instead of staying a single toast — while its first half, the file organiser that has run once in its life, is untouched and still has two unseparated candidate causes.

- **2026-08-11 — Session 36: the briefing envelope, and the staleness check that can never fire.** `GET /api/sysadmin/briefing/preview` now carries `schema`, `period`, `summary`, `alerts[]` and `facts{}` **alongside** the `sections` and `generated_at` it always had. Additive was the delivery decision and it was not a compromise: Alfred's `adapt_sysadmin` reads `payload["sections"]` and returns one red error section if it is missing, and the spec's literal shape had neither `sections` nor `generated_at`. The spec's own sentence resolves it — "prose is what Alfred surfaces, `facts` is the deterministic input the prose was written from" — because **`sections` are the prose**. Alfred owns the section contract by its ADR-0063; this service owns the envelope round it. Rejected: an envelope-native second endpoint (two payloads where one gets updated is the drift this repo keeps filing snags about) and a coordinated breaking change across two repos. No `generated` key was added beside `generated_at`; two stamps holding one value is a fork waiting to happen.

  **The measurement the session was asked to make turned out to be the feature.** Checkbox 6 asked whether Alfred enforces staleness on the generation stamp. It does — `_producer_timestamp` carries `generated_at` into `produced_at` and `DigestSection.vue` flags a 12-hour gap — and the check is **structurally incapable of firing here**, because this is a *pull* endpoint: the payload is stamped at the moment the request is answered. `generated_at` says when the phone was picked up, not how old the data recited into it is; a service whose organiser died three days ago serves a payload one second old. So every block in `facts` carries its own `measured_at`, `facts.stale_sources` names anything measured over 26 hours ago, and `summary` states it in words. **The first live run caught one**: `filesystem` last measured 2026-08-06, five days stale — independently corroborated by an open `file_organiser agent stalled` alert in the same payload, which is two routes to one fact and the argument for the field.

  **`period` is anchored to the schedule rather than the last pull**, because "since the previous briefing" has no anchor on a pulled route: two consumers polling would each shorten the other's window, and storing a row per pull turns the endpoint into a pull log and needs a migration. `schedules.briefing_hour` already declares the cadence, so the window runs from the most recent 06:00 boundary — one meaning for every caller, no storage. `anchor: "schedule"` is in the payload because the other reading is the one a consumer would otherwise assume. **`summary` is deterministic** — no LLM in the 06:00 path, since a summary made only of numbers gains nothing from narration and would take the briefing down with llama-server — and **`facts` is a projection, not a copy**: counts and identifiers, never the rows the sections render, because a facts block containing the whole payload cannot be diffed, which is the only reason it exists. A test asserts every list in it holds scalars.

  **Two P1 snags fixed underneath, and the ordering was forced by the snag list's own note**: *"building a briefing envelope on top of wrong data only makes the wrong data better formatted."* `SNAG-BRIEF-001` — Project Health published every project ever scanned, 26 rows including work retired in July, while "Pick This Up" in the same payload listed 5 and the board returned 6. Both project sections now render from **one** query and one `status == "active"` filter, ordered worst-first (descending plus a cap shows exactly the rows carrying no information) and capped at 5; live result **26 → 5**, and the two sections agree by construction. `SNAG-BRIEF-002` — a bare `[:180]` slice became `truncate_at_word` in `sysadmin/core/text.py`: word boundary, always the marker `… (truncated)`, matching what Alfred's own `sanitise_text` appends. The 180 is now documented rather than anonymous, and the board deliberately still serves the field uncapped. Also removed: the project snapshots were being fetched **twice** per briefing, differing only by an `ORDER BY` Python does for free. Suite 1824 → 1852, ruff and mypy clean. **Handed to the consumer the same day**: the envelope and the staleness limit are written into Alfred's own `docs/external/briefing_producers.md` — its stated re-open trigger covers a payload gaining fields — and re-opened as live **row 130c** rather than reverting the archived, shipped row 130 to `Planned`. Alfred needs no adapter change; what it must *decide* is whether to read `facts.stale_sources`, since `produced_at` will read green forever. The note also flags that the limit is not sysadmin-specific: **SportsAnalyser's stamp has never been checked**. Three stale claims in that file were corrected in passing, including a sections table missing two sections that had been rendering in Alfred for days — the additive contract that makes this boundary safe is the same property that lets its documentation drift with no symptom.

- **2026-08-11 — Session 32: start-versus-finish accounting, and the blocker that named the wrong evidence.** `GET /api/projects/momentum` counts how often a session starts in a repository and nothing ships. The recorded blocker was "the SessionEnd hook overwrites `docs/sessions/handoff.md`, so session history does not survive", with two proposed fixes — an append-only `log.jsonl`, **or** sysadmin recording handoff-date transitions per scan. The second had been true since 2026-08-06: `handoff_age_days` is written on every scan, so `scanned_at − handoff_age_days` reconstructs the date a handoff was written and a change in it between two scans *is* an observed session. No hook, no writer, no migration. The session record is a side effect of a Stop hook that blocks a code-changing session until `HANDOFF.md` carries today's date, which is why it exists at all.

  **The measurement rule was wrong first, and only the live series showed it.** The obvious formulation — did a commit exist by the time the scanner saw the new handoff? — reads as common sense and let scan timing decide the answer, because the handoff is written *before* the work is committed. The scan at `2026-08-10 09:06` saw this repository's new handoff while `last_commit_at` still read 2026-08-08; that day's six commits arrived afterwards and a productive day was scored as dropped. Landings are now matched by **date window** — a commit dated in `[session_date, next_session_date)` is that session's output — which no fixture with an even cadence would have forced. A second correction came from the same run: `observed_from` reported the first scan rather than the first *dated* scan, so this repo's series read as three months when only 22 of its 198 snapshots can carry a session, inviting a reader to divide five sessions by ninety days.

  **Two landings are reported, not one**, because they are different failures: `dropped_code` shipped no code, `dropped` shipped nothing at all, and `docs_only` is the gap — a session that wrote up what it decided is a better outcome than silence and must not be summed with it. That needed no scanner change: `findings['git']` is written only when a housekeeping commit was skipped (77 rows of 3,635), so its absence means the newest commit *is* the newest code commit and the fallback is exact. The one scanner change was recording `handoff_date_source` for the *chosen* handoff rather than only the also-rans — an undated handoff falls back to mtime and a checkout rewrites mtime, which would present a `git checkout` as a morning's work. It is prospective, so every session observed so far is `unverified` and the `reason` sentence hedges rather than quietly asserting.

  **Live, it disagrees with the health scores**: `alfred-glance` has opened 2 sessions and landed nothing since 2026-08-03; `venture-assistant` 3 sessions, 1 landed; this repo 5 sessions, 4 landed, and `git log` confirms the single drop (2026-08-09) had zero commits; `Alfred` is 4 of 4. `ImbaBots` measures **0 sessions**, which is correct and was checked rather than assumed: its last session (`edbd8c2`, 2026-08-07 12:03) changed 22 files *and* its handoff in one commit, and it lands on ImbaBots' baseline scan, so there is nothing older to compare it to. The residual finding is elsewhere and is now `SNAG-PROJ-013` — its heading carries no ISO date, so the Stop hook will block the next code session there. 48 new tests, suite 1776 → 1824, ruff and mypy clean. **No consumer renders it yet** — it is a GET built for a one-line surface, and Session 30's fate says to ask before assuming alfred-glance wants it.

- **2026-08-11 — the tray was not broken, it was never started.** Reported as "no longer working" and diagnosed before anything was built: there is no `~/.config/autostart` entry and there was no unit, so the tray had **only ever been launched by hand** — the box booted 2026-08-10 06:37 and took the last manual instance with it. The code was fine, proven by running `.venv/bin/sysadmin-tray` directly and watching it poll the API. **The estate's only notification surface had been dead for a day and nothing reported it**, which is the same shape as SNAG-DB-001: the thing that would have told you was the thing that was down. Now `~/.config/systemd/user/sysadmin-tray.service`, enabled and running. **It is the first GUI unit here and the contract's skeleton is wrong for one**: lingering is on for `gaddi`, so a `WantedBy=default.target` unit starts at boot with no compositor and restart-loops. It binds to `graphical-session.target` instead (start at login, stop cleanly at logout), which works because KDE imports `DISPLAY`/`WAYLAND_DISPLAY` into the systemd user manager — checked, not assumed. `Restart=on-failure` rather than `always`, because the tray has its own Quit action and `always` would make that menu item a no-op. [monitorable-project.md](../guides/monitorable-project.md) §2.3 gained both rules. Wired into services.yaml the same day as the contract requires, with `monitor: false` and a reason: "inactive" is its *correct* state whenever nobody is logged in, so a check would alert every night and teach the reader to ignore the one surface that shows them alerts. That is a hole only because a dead tray used to mean silence — which the desktop notifier below fixed hours earlier, so a tray dying mid-session is now covered rather than merely unmonitored.

- **2026-08-11 — the daemon can speak for itself (SNAG-CFG-001).** Chased from a stale config key and found to be a whole dead limb: `Notifier.send_notification` was fully implemented, DND-aware, retry-capable — and **called by nothing outside its own tests**. `Notifier` is built in `main.py`, started in the lifespan and hung on `app.state`; `raise_alert`'s docstring says "the notifier service should be called separately" and `monitor/agent.py` says criticals are "to be picked up by notifier". Neither ever happened. Every alerting path in the daemon ended at a database row and waited for the tray to come and read it, so `notifications.desktop` was not a stale key but the visible end of a notification path that had never been connected. **Now wired**: `sysadmin/monitor/desktop.py` subscribes to `alert.raised` on the existing event bus and sends through `notify-send`. Subscribed rather than called from `raise_alert` for two reasons — `core` must not import a domain, and `_queue_event` buffers events until the run's transaction commits, so the notifier's own database query cannot race the insert it is reacting to.

  **It is the tray's understudy, not its rival.** The daemon stays silent whenever `/api/sysadmin/alerts` has been polled within `tray_grace_seconds` (180s, three times the tray's poll), so the two can never both toast one alert; what it covers is the case that was previously silent, **the tray not running** — which was true on this box while the fix was being written, verified by `ps` and `ss`. **The gate that makes it survivable is one-notification-per-incident**, the same "raise once while open" rule the idle nudges use. The measurements are why: the monitor writes one alert row *per failed check* — 186 rows for one `venture-assistant` outage, 123 for one `internet` outage, 88 criticals a day at steady state, and **547,814 unresolved `Log error: kernel` rows** in the table right now. A notifier that spoke per row would be a denial of service against its own reader. Verified against exactly those live rows: `Log error: kernel` → silent, an unseen title → speaks, and both silent while the tray polls. Both gates **fail closed** — an unreachable database returns "not new", because the alternative turns a connection blip into a storm.

  **The transport is `notify-send`, and the daemon had no way to reach a desktop.** `sysadmin.service` is a *system* unit with a minimal `Environment=PATH` and no session-bus address, so a bare `notify-send` fails with "Cannot autolaunch D-Bus without X11 $DISPLAY" — confirmed by running it under `env -i`. The address is supplied in code from the well-known `/run/user/<uid>/bus` socket, only when that socket exists, which keeps the fix out of a root-owned unit file nobody would remember to copy. **Left open deliberately**: recovery is not announced, because `alert.resolved` carries a match pattern (`"Project % health critical"`) rather than a subject — filed in the Backlog rather than papered over. 32 new tests, suite 1744 → 1776. **Needs `sudo systemctl restart sysadmin.service`** to take effect: unlike the organiser, this is daemon code.

- **2026-08-11 — Session 31: idle nudges, a broken commitment rather than a dirty directory.** An `active` project whose human-written next action has not changed for 7 days raises an `info` alert; at 14 it is escalated to `warning`. No new endpoint, no new delivery path and no migration — it rides the alerts table, the tray poll and the DND windows that already exist, and because the organiser is a oneshot timer rather than the daemon, it goes live on the next timer run without a restart. Threshold overridable per project as `idle_nudge_days` in `.project.yaml`, beside `alert_threshold` and deliberately separate from it: a long-cycle repository should be able to relax the commitment clock without also going unwatched for a missing README. **Eligibility was extracted, not re-implemented** — `GET /api/projects/next`'s rules moved into `next_action.eligible_candidates` and both callers now share them, so the endpoint cannot stop offering a project while the nudge goes on reminding you about it. Same reasoning for `load_action_streaks`, which folds the history query the two of them read.

  **Three decisions where the obvious implementation was the wrong one.** (1) **Raise once per open nudge, not once per scan**: `BaseAgent.raise_alert` inserts unconditionally — the mechanism behind SNAG-PROJ-004's 1,664 rows — and the organiser runs daily, so the health-alert pattern would write one row per day per stuck project and turn a nudge into a nag inside the database. (2) **Escalation resolves the quiet row and raises a loud one** rather than updating severity in place, because the tray fingerprints notifications as `"{severity}:{title}"` and an in-place change keeps a fingerprint it has already suppressed — the escalation would be recorded and never spoken. (3) **The escalation is a gap, not a multiplier**: a project that relaxes its own threshold to 21 days escalates at 28, not 42, so the per-project knob moves when the clock starts and not how patient the escalation is. Never `critical` at any age — criticals break through DND by configuration, and waking someone at 02:00 about a roadmap item is how a monitor gets muted wholesale.

  **The feature ships firing nothing, and that is the intended shape.** All three eligible projects turn their next actions over in 1–4 days, so at 7 days the live estate produces zero nudges — a live organiser run over 25 repositories confirmed `{raised: 0, escalated: 0, resolved: 0}`. Since a clean run proves only that nothing crashed, the ladder was then exercised over the **real** historical series for this repo (the "Session 24: File organiser tiers" action, **9 scans across 2 days**): `streak_days` folded it to a single 2-day run and the ladder produced `info`, `warning` and no-nudge at the thresholds it should. That 9-to-2 ratio is Session 29's days-not-scans argument holding on live data. **A wrong claim was caught by checking it**: the design was written three times around `notifications.desktop.min_severity` as the knob deciding whether a nudge is audible, and nothing in `sysadmin/` reads `config.notifications.desktop` at all — the live gate is `tray.notify_min_severity` in a different section. Filed as `SNAG-CFG-001`, not fixed here, since it sits on the tray's configuration boundary and this session changed no notification code. 43 new tests, suite 1701 → 1744, ruff and mypy clean.

- **2026-08-11 — Session 30 closed unbuilt: the consumer had already declined it.** The session opened to build it and checked the consumer first, which ended it. Alfred accepted **ADR-0064** on 2026-08-07 — three days *before* Session 29 shipped — declining the whole projects-page arc for v1 behind two named, countable triggers. This repo's tasks.md said "nothing here blocks it beyond Session 29"; the block was never on this side, and the row had been wrong since the day it was written. **Neither trigger fires and one moved the wrong way**: `stalled_count ≥ 2` sustained over two weekly reads stands at **0**, and `count ≥ 12` active stands at **5**, down from the 6 the ADR was written against. The board does carry 3 stalled projects, all among the 20 inactive ones the trigger deliberately excludes — declaring a project dormant *was* the decision, so it cannot also be a stall. The decline is not a rejection of the endpoints: ADR-0064 §1 finds the momentum data already reaches the owner as the daily digest's `Pick This Up` section, built to this guide's own honesty treatment, and §2 makes `alfred-projects-page.md` the build instruction the moment a trigger fires — "good and should be followed rather than redesigned". **What was actually wrong was that the decision lived in one repo and the work in another.** A declined-by-the-consumer state had no representation on the producer's side, so this roadmap kept advertising the work as unblocked while Alfred had refused it in writing. Recorded now in both places it is read from: the tasks.md row carries the trigger table and the `curl` that re-checks it, and the guide gains a §0 status block ahead of §1 so nobody builds from the spec without meeting the decline first. **One premise of the ADR has expired and fires nothing** — §3 declines to design against `GET /api/projects/next` because it 404s with an undecided ranking, and Session 29 shipped it the next day with a decided, documented one. That retires a stated *reason* without moving either *trigger*, which is the distinction a counted deferral exists to hold: it is re-opened by the count, not by an argument. Alfred's own ADR does not record this yet.

- **2026-08-11 — a test that failed on a date, not on a change.** `test_endpoint_filters_by_confidence` went red in a session that had not touched the reliability scorer, and it was pre-existing — confirmed by stashing the uncommitted work and watching it fail anyway. The file held **two clocks**: every direct-scorer call pinned `now=NOW` (2026-08-07 12:00) with the fixture rows anchored there, while the nine endpoint calls went through the route, which reads `datetime.now(UTC)` because this endpoint is computed live by design. As real time drew away from `NOW` the seven-day window slid off the fixture data. The confidence test went first, at the 3.5-day mark on 2026-08-11, where a seven-day run of checks stops covering half the window and `_confidence` correctly downgrades the service to `low` — the scorer was right and the test was wrong. **The other eight had until 2026-08-14**, when the run would have left the window outright and all nine would have failed together. An autouse fixture pins the route's clock to the same `NOW`; `datetime` is used exactly once in that route module, so the patch is narrow and the route can no longer observe wall-clock time. Suite back to 1701, ruff and mypy clean.

- **2026-08-10 — Session 38: the unread handoff gets a reader.** `handoff_duplicates` had been recorded by `scan_roadmap` since Session 37 and consumed by nothing; it is now a zero-point `kind: "roadmap"` recommendation, which reaches `/api/projects/{name}/recommendations`, `/api/projects/actions` and the weekly review at once because all three call `recommendations_for`. **The estate was checked first and the finding changed the job.** Commit `0d56081` consolidated the migration: **seven repos hold a handoff and every one holds exactly one**, so this ships as a **regression detector**, not a report on a current mess — it fires the day someone re-creates a second handoff. Five carry a root `HANDOFF.md` (`Alfred`, `ImbaBots`, this repo, `apps/venture-assistant`, `apps/SportsAnalyser`) and the two archived `PersonalAssistant` repos still carry `docs/sessions/handoff.md`, which the non-active waiver excludes anyway. **The first survey was wrong and the estate map is why**: globbing `~/projects/*/` sees 11 directories, while `discovery_depth: 2` means the scanned population is 25 across `~/projects/`, `apps/` and `archive/` — the run reported `venture-assistant` and `SportsAnalyser` as holding no handoff when both hold a root one, contradicting a fact Session 37 had already established without that contradiction being noticed. The live table could not have shown it either way: the newest stored snapshot (09:06 today) predates Session 37's code and carries neither `handoff_path` nor `handoff_duplicates`, so 90 days of JSONB read `None` for both. Verified end-to-end against a constructed two-handoff repository instead, and the mtime branch is the one that fired — a generated stub headed `# Session Handoff` carries no ISO date, which is the realistic case. **The field was widened from a list of paths to `{path, date, date_source, days_older}`**, because the two cases a reader must separate are indistinguishable as paths: a loser nine days behind the winner is migration debris and can be deleted, while one *sharing* the winner's date lost on tuple order alone and deleting it unread is how SNAG-ROADMAP-003 would recur from the other side. The advice branches on exactly that — `days_older` of `0` or `None` takes the "confirm which is current" wording, never "delete". `date_source` records which clock produced the gap, since `handoff_date` falls back to mtime and a clone rewrites every mtime on disk; the recommendation marks those "by file date" and says why they are weaker rather than asserting a number it cannot stand behind. Selection still applies the fallback uniformly — this constrains the *advice*, not the choice. The bare-string shape is still accepted for the same reason `stale_branches` accepts strings: retention outlives a shape change. `handoff_path` is consumed in the detail line only, deliberately, so it remains unread in a repo with one handoff — filed as a follow-up rather than expanded into `ProjectBoardEntry` in the same sitting. 11 new tests, suite 1690 → 1701, ruff and mypy clean, no new routes and no migration.

- **2026-08-10 — Session 29: the one-thing endpoint.** `GET /api/projects/next` returns one project, one action and one sentence saying why it is that one. The session's own task list said the ranking policy was the whole feature and needed a decision before code, so the decision was taken first and against measured data rather than defaulted. **The ranking is stuckness** — how long the stated next action has stood unchanged — tie-broken by the most recently committed project. **Nearest-to-finishing was rejected on evidence**: it reads `done_tasks`/`open_tasks`, which are `None` for three of the five active projects on this estate, so it would have been blind to most of the population while looking authoritative. **Smallest-next-step was rejected as unmeasurable** — nothing records the size of a step, and every proxy for it (string length, task count) is invented rather than observed. **Longest-idle was rejected as the guilt metric** the roadmap already doubted.

  **The unit is elapsed days, not scans, and that is the finding worth keeping.** The obvious implementation counts consecutive snapshots carrying the same action — Session 37's `next_action_changed` makes it a one-line query. It would have passed every fixture written with an even cadence and been wrong on live data: the scan series is 6-hourly until Session 35, daily from the organiser's timer since, plus every manual `POST /api/projects/scan`, and the live table holds two scans 17 minutes apart on 2026-08-08 and two more on 2026-08-10. Ranking on scan count measures how often the organiser happened to run and reports it as the owner's behaviour. `unchanged_scans` is still returned as the evidence behind the number; `at_window_edge` marks a run reaching the oldest scan held, so `days_unchanged` is honestly a lower bound. Elapsed days come from the snapshot series rather than `handoff_age_days`, which says what the document claims about itself and already has the job of deciding `stalled`.

  **Eligibility is narrower than the board's, deliberately.** Active projects whose `next_action_source` is `handoff` or `tasks` — the board's `git` fallback is a commit subject, honest there because the source is rendered beside it, and not an instruction to act on. Nor is a handoff that states there is nothing queued: two live estate handoffs read "No unchecked task found — set one before the next session", which is a *correct* handoff and still not something to hand a consumer whose premise is glance-then-act. `roadmap.looks_like_no_action` is conservative in the same direction as `is_placeholder` — bare forms must be the whole line, so "None of the migrations are applied" survives as real work.

  **Empty is 200 with `project: null`**, never 404, because 404 would collapse "every project is up to date" into "no scan has ever run" and a consumer cannot tell those apart from a status code. `skipped` breaks the ruled-out population down by reason, which is what made the live shape legible: **2 candidates out of 23 fresh projects** — 20 inactive, 1 with no stated action, 2 stating there is nothing queued. Verified against the live database before the tests were written: both candidates sat at 2 days unchanged and the tie broke on last commit (1 day vs 3), with the reason sentence naming the tie-break it actually used. The winning action turned out to be stale output from the SessionEnd hook Session 37 retired — the endpoint doing its job on the first run. `action_history_query` extracts one JSONB field in the database rather than loading `ProjectSnapshot` entities, since the alternative drags kilobytes of `findings` per scan across the window to compute a run length. 45 new tests — suite 1645 → 1690, ruff and mypy clean, 55 → 56 routes.

- **2026-08-10 — Session 37: the handoff pipeline, both ends.** Raised as "the handoff hook isn't doing much in venture-assistant". Measuring first changed the diagnosis: across 15 repos, 5 carried a `docs/sessions/handoff.md` and **every one was hook output**, while exactly two repos had ever held a handoff someone wrote — and both lived at paths the scanner could not read. Root `HANDOFF.md` existed in **1 of 15**, not "most", which is why the location question was checked before it was acted on. **The writer**: `SessionEnd` cannot block — it is an observability event — so `generate-handoff.sh` could only ever emit what `git` already recorded (branch, porcelain, today's log). Retired, unwired, left on disk with its reasoning. `~/.claude/hooks/require-handoff.sh` is a **Stop** hook, which can block, and does: a session that changed code cannot finish until `HANDOFF.md` carries today's date, so the file is written by whoever knows what the session did. Three independent loop guards, because a blocking Stop hook that misfires hangs every session — `stop_hook_active`, a per-session+repo marker file (load-bearing: the field is no longer in the documented schema), and exit 0 on every failure path. Ten payload cases verified before wiring, including that `touch HANDOFF.md` does **not** satisfy it. **The reader**: `SNAG-ROADMAP-003` closed — four candidate paths, selection by the document's own heading date rather than tuple order, also-rans reported as `handoff_duplicates`. **The first fix was wrong and only the live estate showed it**: ranking every undated candidate below every dated one re-created the bug from the other side, because ImbaBots' 141 KB handoff heads itself "Handoff — M5 (Tier 2)" with no ISO date and lost to an 882-byte stub written an hour earlier. The mtime fallback has to apply uniformly, which is what `scan_roadmap` already did downstream — the module had been holding two contradictory rules at once. **The design lesson**: a file guaranteed to exist cannot also be the file whose absence means something; the hook filled the slot everywhere, so nothing ever signalled a real handoff was missing. **Session 32 is unblocked, and its premise was wrong twice.** Its recorded blocker was "the SessionEnd hook overwriting its handoff instead of appending a log" — but the hook no longer writes, *and the log already existed*. Session 28 has written the whole roadmap findings block into `project_snapshots` since 2026-08-06; the history list exposed `health_score` and `scanned_at` only, so ninety days of next actions sat in JSONB with no endpoint over them. `ProjectHistoryPoint` now carries `next_action`, `next_action_source` and `next_action_changed`, built by `build_narrative_history`. The change flag compares against the **older** neighbour, and the oldest point in the window is `None` rather than `False` — there is nothing older to compare it to, and calling that "unchanged" invents a streak whose length moves with `limit` while the data does not. Live proof: ImbaBots' `M5-T05` unchanged across 10 scans and 3 days, venture-assistant's next action unchanged since 2026-08-07 while the task it names is ticked `[x]` — a stuck run beside a completed task is the stale-handoff signal, and it is now visible without a hand-written SQL query. Suite 1629 → 1645, ruff and mypy clean.

- **2026-08-10 — Session 34: the twelve project-side defects, cleared.** Every one of them corrupted output Alfred already consumes, which is why they were ordered ahead of the briefing envelope. Two required a decision before any code was written, and both were taken deliberately rather than defaulted. **The 1,664 orphaned alert rows were resolved, not deleted** (migration 010): they are real history — the organiser did judge those projects unhealthy at those times — and marking them resolved hands them to the existing 180-day retention purge instead of routing around the mechanism that is supposed to own removal. `resolved_at` is *now*, not backdated, because the alerts really were open until the migration ran and backdating would have made the whole backlog instantly purgeable, destroying the history the migration chose not to delete. **`GET /api/projects/stale` got its `days` parameter implemented rather than deleted**: no consumer exists anywhere under `~/projects` — only this repo's own docs mention it — so this was a free choice, and the endpoint filtering on `health_score < needs_attention_min` had made it a duplicate of `/overview` wearing a name that promised idleness. A well-kept repository untouched for a year scored 90 and never appeared. It now filters on last-commit age, reports `days_idle` (null for never-committed, which is the strongest form of the question, not the weakest) and has a `StaleProjectsResponse` contract.

  **The audit said eight surfaces; there were nine.** That undercount is the argument for the fix's shape: a pattern copy-pasted across three packages cannot be counted reliably, including by the person auditing it. `sysadmin/projects/snapshots.py` now owns the latest-per-project join *and* the `newest_scan − 1h` cutoff, and `tests/test_project_snapshots_query.py` fails if any module builds its own — an AST walk for `func.max(ProjectSnapshot.scanned_at)` outside the owning module. The helper could not live in `projects/router.py`, since `briefing/data.py` would then import one router from another. **Freshness is anchored to the newest scan, never to `now()`**: anchoring to wall-clock would empty every project surface the moment the organiser's timer stopped, reporting a monitoring failure as an estate with no projects in it. **This carries a real cost, stated rather than glossed**: the suite mocks every session, so a `WHERE` clause is invisible to it and the two board tests that proved a deleted project was dropped can no longer prove it. What replaced them is stronger in coverage (all nine call sites, not the one that happened to have the filter written by hand) and weaker in kind (compiled SQL, not a round trip). A live-database test is filed as a follow-up rather than pretended.

  **Alert resolution is set-based, deliberately unlike the two reference agents.** `sysadmin/monitor/agent.py` and `sysadmin/units/agent.py` loop and call `BaseAgent.resolve_alerts` per recovered item; their populations are fixed by configuration. A project's is not — **a project deleted from disk never appears in a scan, so it can never be observed recovering**, so a per-project loop would have left its alert unresolved forever and the backlog would have regrown on the next deletion. Asking the inverse question ("which of my open alerts would this scan not raise?") closes recovery, deletion, rename and re-declaration as `archived` in one statement, and cannot drift from the raise path because both titles come from `_alert_title`. The rows raised moments earlier in the same transaction are excluded by title, not by timestamp — a title comparison is exact, where "created before now" races the clock the inserts were stamped with.

  **The marker scan's three defects were one job, and the measured effect is large.** `*.md` is no longer scanned (a repository's own `snag_list.md` counted towards its own penalty, so writing up a defect lowered the score of the project writing it up), patterns match whole words via `grep -w` (`TODO_STATES` and `TodoList` were both scored as markers), and the cap is a project total that records its own truncation rather than grep's per-file `-m 1000` behind a docstring claiming a global limit. Live: **PersonalAssistant 327 → 174 markers, sysadmin_assistant 87 → 56, PersonalAssistant-auto 290 → 150**; five projects dropped to zero because their only markers were in documentation. Most scores did not move because those projects sit at the 30-point cap, but **Alfred went 75 → 95 and `terrible` 95 → 100**. `HACK` and `XXX` still cost points — they are real code smells — but the recommendation now names them (`HACK 40. Every 10 markers cost 5 points`) instead of reporting "0 TODOs, 0 FIXMEs" beside an unexplained deduction.

  **The project review is figure-free by construction**, four days after the disk review was rebuilt the same way and a year after the same model taught the lesson on scores. Scores become bands, deltas become directions, and recommendation titles — which carry counts like "Prune 7 stale branches" — become `kind` phrases; every real figure lives in `build_facts_section`, prepended deterministically. `strip_markdown` moved to `sysadmin/core/text.py` so both reviews share it without either domain importing the other. A guard test asserts no digit reaches the model, with project names stripped first: a name is an identifier the model must quote back, not a quantity.

  **Retention gained three tables, not two.** `project_reviews` and `disk_reviews` were in neither `retention_config` nor `TABLE_TIMESTAMP_MAP`; **`unit_audits` was in the map with no config row**, so the code that would have purged it was never reached — found while adding the other two. Reviews get 365 days rather than the 30 that check data gets: they are weekly narratives, and 30 days keeps four of them, which is too few to see a trend. All three are in a new `KEEP_LATEST_PER` map so the newest row survives its window — a purge that emptied `project_reviews` would make `GET /api/projects/review` 404, which the tray renders as "no review has ever been generated" rather than "none lately".

  **And the session found a P0 that was not on the list — a live monitoring blackout, 39 hours old and still running.** While tracing why the schema drift guard had stayed green, `alembic current` turned out to report **008** against a repository head of 009. Migration 009 adds `'skipped'` to `chk_health_status`; it was written on 2026-08-08 in Session 35 Phase 3 and never applied, because **nothing applies migrations here** — no script, no `ExecStartPre`, no CI step, just a manual command a human has to remember. `sysadmin.service` restarted at 17:36 on 2026-08-08, two minutes after the last successful health check, and picked up the new `services.yaml`, in which `venture-chat-large` is `kind: static` with `monitor: false` and therefore records `skipped` — the exact value the un-applied migration was meant to permit. **Zero rows were written to `service_health` from 2026-08-08 17:34:54 until 2026-08-10 09:07:25**, when applying the migration resumed them.

  **One rejected row cost all nineteen services their check.** `SysAdminAgent._execute` adds every service's result to one session and `BaseAgent.run` commits once, so the `CheckViolationError` on a single deliberately-unmonitored service aborted the whole transaction — the failure mode was total, not partial, which is also why it left no partial data to notice. **Nothing noticed for a different reason each time it could have**: the daemon logged `agent_run_failed` every five minutes (29 times this morning alone) and nothing reads that; `verify_connection` proves the database answers, not that it is the schema this code was written for; and the drift guard — the one test that connects to the live database — explicitly skips `alembic_version` *and* runs `compare_metadata`, which does not diff CHECK constraints. That last point was verified rather than assumed: restoring the pre-009 constraint inside a rolled-back transaction produces an **empty diff**, with the model declaring `'skipped'` and the database rejecting it. The alerting path was itself the thing that broke, so it could not report its own failure. ~18 of the 39 hours were with the daemon up and failing; the box was asleep for the rest. Filed as **SNAG-DB-001 (P0)** — fixed, with all three detection gaps left open and specified in tasks.md, because applying the migration fixes this instance and none of the reasons it ran for 39 hours. 64 new tests — suite 1565 → 1629, ruff and mypy clean, 55 routes before and after.

- **2026-08-08 — Session 35 operational: the organiser timer is installed, and verifying it found a bug.** `sysadmin-organiser.timer` is installed into `~/.config/systemd/user`, enabled, and armed for 04:32 daily; a manual run under systemd exits 0 in 1.45 s at 88.5 MB peak against a 512 MB cap. The same-day wiring the contract requires is done: the timer is declared in services.yaml as `kind: timer`, and `agents.project_organiser.enabled` is now **false** — that flag gates the schedule *inside the daemon* and nothing else, so leaving it true would scan the estate twice, once every 6 h in-process and once daily from the timer. Endpoints, the manual `POST /api/projects/scan` and the weekly review are unaffected. Monitoring the timer is what **replaces** the self-monitor's stall watch over that agent: a disabled agent is correctly not flagged as stalled, so something else had to be able to tell whether the scan ran, and now the timer's own last-run is that signal. **Verifying rather than assuming immediately paid: `kind: timer` had been recording nothing since Phase 3** — see SNAG-SYSD-002. `_timer_facts` reads three `systemctl show` properties that `get_unit_status` never requested, so every timer check returned `ok` with an empty last-run and nothing said so. It passed its unit tests because those mock `get_unit_status` and supply the properties the assertions expect; the mock was the specification and the real function had never been asked. Fixed, with a test that asserts the *coupling* — every property `_timer_facts` reads must appear in `get_unit_status`'s request list — rather than only the behaviour on a cooperative mock. Live timers now report real data: `alfred-evaluate` last triggered 08:00:01, `pgbackrest-backup` 00:00:42. 3 new tests — suite 1562 → 1565. **Pending ops action**: `sudo systemctl restart sysadmin.service` — the daemon has been up since 2026-08-07 and still holds the old config, so it is both scanning on the retired 6-hourly schedule and unaware of the new timer.

- **2026-08-08 — Session 35 Phase 6: the organiser gets its own timer, and ADR-0001.** `sysadmin-organiser` is a console script and a `Type=oneshot` unit driven by a daily timer, so the scan and the monitor no longer share a fate: stop the timer and health checks carry on, stop the daemon and the scan still writes its snapshots and rewrites estate.json. Verified standalone — 25 projects in 1.46 s with no daemon running. The unit is **deliberately not `After=sysadmin.service`**: ordering them would make a stopped monitor delay a scan that does not need it. `Persistent=true` because a box asleep at 04:30 must still get its scan, which is the whole point of moving it out of an always-on process. `BaseAgent.run` now returns its `AgentResult` so a one-shot invocation has something to turn into an exit code rather than re-reading the row it just wrote; the scheduler ignores it. **[ADR-0001](../adr/0001-project-registry.md)** records the four things the brief asked for — identity in the repositories, no paths in services.yaml, persistence deferred because it is the decision that locks in ownership, and who owns project state left explicitly open — plus the one thing that is *not* staged for extraction: migration 001 creates both sides' tables in one revision, so moving the project side to its own service still means a data migration. `SYSADMIN-SERVICE-SPEC.md` is marked superseded-in-part with a difference table rather than rewritten; it is the February design record and rewriting it would lose that, the same reasoning that left the archived roadmap entries alone in Phase 2. **One trap worth recording**: `uv sync` without `--all-extras` removes the dev extras, after which `uv run pytest` silently falls back to `/usr/bin/pytest` and the suite runs against system Python with none of the project's dependencies — it presents as `ModuleNotFoundError: pythonjsonlogger`, which looks like a broken dependency rather than a broken environment. 6 new tests — suite 1556 → 1562, ruff and mypy clean. **Pending ops action**: install the timer with `systemctl --user enable --now sysadmin-organiser.timer`, then add it to services.yaml as `kind: timer` and set `agents.project_organiser.enabled: false` so the scan is not run twice.

- **2026-08-08 — Session 35 Phase 5: estate.json.** The organiser writes a versioned `estate.json` on every run, **atomically** — temp file in the destination directory, then `os.replace`, because a consumer polling it must never catch it half-written and `/tmp` is frequently a different filesystem. `health` is derived from the snapshot computed in the same run rather than being a second scorer: two numbers called "health" that disagreed would be a bug nobody could adjudicate. `services` is a list of **names** resolved from services.yaml by project id, not embedded topology, so a port move does not have two places to edit. Undeclared repositories appear with `"status": "undeclared"` and whatever can be derived, because omitting them would make the file agree with itself and disagree with the disk. **The brief's seed for the commit-ignore rule was incomplete, and the feature would not have worked with it.** It named the 2026-08-04/05 reorganisation snapshot; this estate has *two* sweeps, and the second — the fan-out that wrote a roadmap document set into eleven repositories on 2026-08-06 — is **newer**. With only the first pattern the walk stops at the newest commit having skipped nothing, so eleven projects would still have read as touched last week. The rule is therefore a **list** of patterns rather than the single regex sketched, and a test pins the failure mode. Correctness is checkable rather than asserted: the automated rule reproduces every hand-recorded "last code" date in the legacy registry file exactly — daiy 2026-02-06, terrible 2026-03-25, BudgetApp 2025-05-14, SportsAnalyser 2026-03-23, portfolionew never. **Staleness now comes from `last_code_commit` everywhere**, achieved without a migration by putting the code date in `ProjectSnapshot.last_commit_at` (so every downstream reading is derived from it) and recording both raw dates in `findings["git"]` when they differ. **Measured impact: 12 projects' staleness figures change, and zero health scores do** — the corrected projects are all dormant or archived, whose staleness is not penalised, so the numbers get fixed without moving a score or tripping an alert. The largest correction is 1 day → 472 days. 32 new tests — suite 1524 → 1556, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 4: projects.yaml retired.** The file is now `docs/projects-registry-legacy.yaml` and **nothing reads it**. `ManagedProject`, `ProjectEndpoint`, `ProjectsConfig` and `_merge_projects_config` are gone from `core/config.py`; `AppConfig` has no `projects` section. Project state — declared status and per-project alert floors — is read from the `.project.yaml` manifests through the registry, and services from services.yaml. **The registry dissolved the last cross-domain import**: `units → projects` was two imports (`discover_projects`, `_infer_status`) and is now zero, because both agents call `load_registry` instead of one importing the other's discovery. That was the exact drift the registry was built to remove, and its symptom would have been units reported as orphans because one sweep could not see a project the other could. `GET /api/units/actions` now emits **services.yaml** snippets rather than the old config.yaml/projects.yaml pair, and a bug found while converting it is worth recording: the sweep matches units against the *directory* name while services.yaml keys on the *manifest id*, so the first version emitted `project: Alfred` where `alfred` was needed — a snippet that would have failed to load, which is worse than no snippet. A test now parses each generated snippet as a real `ServiceEntry`. `_effective_threshold` reads the manifest instead of doing a three-key lookup by path, name and basename; **`undeclared` is scored exactly like `active`** rather than falling through the `status == "active"` guards by accident, because an absent decision is not a decision to waive anything. The migration script gained the services emission the brief specified, used as a **completeness check** rather than a generator: it reports anything projects.yaml declared that services.yaml does not carry, and flagged the one deliberate difference (the `sysadmin-assistant` id) rather than letting it pass silently. **The reasoning transfer was done by hand, one project at a time** — 20 decisions across 15 manifests, with a test asserting no manifest silently loses its block, since the legacy file is the only other copy. Estate now reads 5 active, 7 dormant, 12 archived, 1 undeclared. 55 routes before and after. Suite 1521 → 1524, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 3 (second half): services.yaml wired in.** `config.yaml` now holds **no per-service topology at all** — `agents.sysadmin.services` is gone, and `agents.log_aggregator.sources` is down to `kernel`, the one source with no service to hang off. `MonitoredService` and `ManagedProject.to_monitored_services`/`to_log_sources` were deleted outright: projects.yaml contributes nothing to monitoring any more. **Startup validates every `project:` reference against the registry**, so an id naming no manifest stops the service with every bad reference listed at once; a path naming nothing failed silently and did, twice. **Four measured behaviour changes**, all flagged before the wiring landed. (1) `kind: http` now asserts the unit is active as well as polling the url — a 200 says *something* answered, not that the unit this estate believes serves it is what answered. It **fails open** on a systemd query error, which is SNAG-SYSD-001's rule: without it one user-bus hiccup would turn every http service on the box degraded at once. (2) Five systemd checks became `kind: timer` and now record `last_run`/`next_run`/`last_result`, because an armed timer is `active (waiting)` and the active test alone cannot tell a schedule about to fire from one whose last run failed. (3) `venture-chat-large` is declared for the first time, as `kind: static` with `monitor: false` and a required `reason`, recorded as `skipped` — previously it was absent from every config file, which made "deliberately not watched" indistinguishable from "nobody wired it up". (4) **A duplicate log ingestion was removed**: `sysadmin.service` was read twice, as `sysadmin` from config.yaml and `sysadmin-service` from projects.yaml, and neither file said so — the merge now drops a config source that duplicates a service by name *or* by unit, and logs which it kept. Service count is unchanged at 17 checked; log sources went 10 → 9. `GET /api/projects/managed` resolves services by id instead of generating them, so it can finally report all four of Alfred's rather than the two projects.yaml could model. The tray reads `mute:` from services.yaml, and a missing file costs it a mute list rather than a launch. 55 routes before and after, every path identical. 12 new wiring tests plus the test-suite migration off `MonitoredService` — suite 1560 → 1553 net (the projects.yaml endpoint tests went with the feature), ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 3 (first half): the manifests and services.yaml.** Phase 3 could not start as briefed: it keys services on project id and demands that an unknown id fail at load, but **zero manifests existed** — writing them is Phase 4. So Phase 4's writer came first. `scripts/migrate_registry.py` (dry run by default, never overwrites without `--force`, never reads projects.yaml's comments) wrote **16 `.project.yaml` manifests** into the project directories themselves, where identity travels with the directory and a rename cannot orphan it. Registry now loads 16 declared ids, 9 undeclared. **Two collisions the derived-id design predicted, both resolved by declaring**: `apps/BSL-Translator` and `archive/bsl-translator` both derive `bsl-translator`, and only the first is declared, so the second stays a provisional id that resolves to nothing; `archive/Portfolio` and `archive/portfolio` — two directories differing only in case — remain a reported finding, which is correct, since nobody has decided anything about either. `services.yaml` folds both sources into one file with **no paths at all**: the six projects.yaml endpoints plus the eleven units exiled to `agents.sysadmin.services`, seven of which were only there because projects.yaml modelled exactly one backend and one frontend and could not express a third unit. `kind` now decides the check, so the rule that `alfred-evaluate` is a oneshot to be watched through its timer — previously a config.yaml comment, correct and hand-maintained and invisible to the code — is a field. **Service names were deliberately kept, against the brief's example**: `service_name` keys `service_health`, reliability scores and the tray's mute list, so renaming `alfred` to `alfred-backend` would orphan a month of history; `role:` carries the tidier label instead. Migration 009 adds `'skipped'` to `chk_health_status` — `kind: static`, `kind: oneshot` and `monitor: false` all mean "deliberately not checked", which no existing status expresses: `error` means the check failed, `critical` is a claim about the service, and recording nothing would make a declared service vanish from `/api/sysadmin/status` and the tray grid, reading as forgotten rather than as decided. Two naming faults fixed before anything consumed the ids: the project id derived from projects.yaml's `name` came out as `sysadmin-service`, identical to a service name in the same file, so it is `sysadmin-assistant`; and the five projects projects.yaml left blank — `alfred`, `alfred-glance`, `sysadmin-assistant`, `athenaeum`, `venture-assistant` — were declared `active` rather than inheriting the new `undeclared` default, since blank previously *meant* active. **Nothing reads services.yaml yet**: the wiring changes monitoring behaviour and is the second half. 48 new tests — suite 1512 → 1560, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 2: the module boundary.** 62 modules relocated with `git mv` into seven packages — `core/` (config, database, contracts, `BaseAgent`, scheduler, retention, LLM client, `/health`), `registry/` (Phase 1, unchanged), and one package each for `monitor/`, `projects/`, `files/`, `units/` and `briefing/`. Imports rewritten in 98 files; **55 routes before, 55 after, every path identical**. `tests/test_import_boundary.py` asserts `sysadmin/monitor` never imports `sysadmin.projects`, and it passes without a detour: monitor imports **only** `core` (31 edges) and nothing else. **The brief named four packages and the estate has six concerns** — file organising (3,296 lines) and service discovery (1,633) fit neither `monitor` nor `projects`, and putting them in `core` would have made the shared layer larger than the domains it serves, so each got its own package. A seventh, `briefing/`, holds the two endpoints that join three domains each: they cannot live in `monitor` without breaking the boundary, cannot live in `projects` without lying, and cannot live in `core`, which must not depend on a domain. **`GET /api/sysadmin/briefing/preview` moved package but kept its path**, because monitor importing `briefing.data` would have reached `projects` transitively — a violation the textual test cannot see. Four cross-domain imports survive and are deliberate: `projects → monitor` for `ServiceHealth` on `/api/projects/managed`, `files → monitor` (×2) for `ResourceSnapshot` disk occupancy, and `units → projects` (×2) for `discover_projects`, which Phase 1's registry is built to absorb. **Three couplings route through `core.config` and so stay invisible to the boundary test** — `self_monitor` reading `agents.project_organiser.{enabled,scan_interval_hours}`, the file actions reading `projects_root` for the `~/projects` safety fence, and the unit sweep reading both sides; a second test now forbids `core/` and `registry/` from importing any domain, without which core becomes the smuggling route and every boundary above it is fiction. `sysadmin/metadata.py` replaces the old `models/__init__.py` aggregator, so Alembic and the schema-drift test share one list instead of two that can diverge. The only real breakage was `load_config`'s `Path(__file__).parent.parent`, which gained a directory level and resolved to `sysadmin/config.yaml` — 198 test errors from one expression, now a named `REPO_ROOT`. 3 new tests — suite 1509 → 1512, ruff and mypy clean.

- **2026-08-07 — Session 25 Tier 1: per-service reliability scoring.** The third scorer, after the project organiser's repositories and the file organiser's disk — the services this application exists to watch had no number attached to them. `GET /api/services/reliability`, a pure `sysadmin/services/reliability.py` (scores a list of `HealthPoint`, no DB or FastAPI) plus a `reliability_history.py` adapter, a `reliability_scores` table (migration 008) and an 02:00 daily snapshot cron. Score is `100 − downtime − instability`, both individually attributable so Tier 2 can price them separately: downtime is `round(100 − uptime%)` capped at 60, instability is 5 per outage **episode** from the first, capped at 25. **They are separate terms because they are separate failures**, and the live data proves it: `internet` lost only 7.5 % of its checks but across *three* incidents (−15 instability, −8 downtime) while `venture-assistant` lost 27 % in *one* sustained outage (−27, −5) — retry logic survives the second shape and dies on the first, so a repeatedly-dropping service must not outrank a longer single outage merely because it was up more of the time. **Three of the plan's four metrics survived contact with the data; the fourth had no data at all.** (1) "Mean time between alerts" was uncomputable as specified: the `alerts` table records one row *per failed check*, so a single internet outage wrote **123 rows in 7 days** and one `venture-assistant` outage wrote **81** — the mean of those measures `health_check_interval_seconds` and nothing else. Incidents now come from consecutive non-ok runs in `service_health`, which collapse into episodes by construction, carry the same information, and avoid a join on `details->>'service_name'` — the only, unindexed, link `alerts` has to a service. (2) **Restart frequency was dropped**: nothing on this host records restarts (`NRestarts` is a live cumulative counter never sampled into the DB; `agent_runs` records *agent* executions), and three measured metrics beat four where one is invented. (3) Coverage became a **confidence flag, not a deduction** — the estate records ~81 % of expected checks and services added on 2026-08-06 have ~1 day of history against a 7-day window, but a gap means the *monitor* was down, so deducting would charge the service for this application's downtime. Ordering deliberately ignores confidence: a thinly-observed failing service is still the most interesting row on the page. **Computed live, never read back** — unlike `/api/units/status`, which serves the latest stored sweep, this recomputes on every request (~28 ms for the whole estate), because a stored score would be up to 24 h stale and would 404 before the first nightly job ran; the table is history for trending, written at 02:00 an hour *ahead* of the 03:00 retention purge so the day's score lands before the checks behind it can be deleted. The population is **the configured services**, not the distinct names in `service_health`, and both differences matter: retired services (`ollama`, `personal-assistant`) keep rows for 30 days and must not be scored, while `venture-chat` and `pgbackrest-backup-timer` are in config.yaml with **zero checks ever** — scored 100 at low confidence rather than omitted, because "configured but never checked" is a finding, not an absence. The mute waiver landed as specified and required modelling `notifications.tray` backend-side for the first time: a projects.yaml-contributed service has no `mute` field, so that list is the only way to declare one expected-down. **Live result: 17 services scored, mean 96.5 — `venture-assistant` 68, `internet` 77, `alfred-frontend` 95, 14 others 100, 8 low-confidence.** 82 new tests — suite 1359 → 1441.

- **2026-08-07 — Session 26: the unmonitored-unit detector.** The mechanical backstop for [guides/monitorable-project.md](../guides/monitorable-project.md): sweep every installed systemd unit, cross-reference it against the projects on disk and the units already wired into projects.yaml/config.yaml, and report the gaps both ways. Tiers 1 and 2 only — and the **absence of a Tier 3 is a decision, not an omission**. Sessions 22 and 24 rank by health-score points and reclaimable megabytes, both directly measurable; nothing here makes two host units meaningfully "twice" one orphan, so `UnitRecommendationInfo` carries **no score field at all** rather than inventing a currency the reader cannot check, and a weekly LLM narrative over findings that change monthly would be prose about nothing. Matching is **path first, name second**, and both earn their place on real data: `alfred-inference` prefix-matches `alfred` but not `alfred-glance` (so longest-wins never has to guess), while `sportsanalyser-pipeline.service` runs `/usr/bin/curl` against an HTTP endpoint and has *no* project path, so only the name fallback catches it. A **third category the plan did not have** proved necessary: `pgbackrest-backup` (the estate's only database backup) and `ethernet-optimise` are hand-written, real, unmonitored, and map to no project — the spec's path-match filter would have dropped them alongside genuine distro units. They get a config.yaml `services:` snippet, not a projects.yaml one, because a projects.yaml endpoint **without a `url` is inert**: `to_monitored_services` skips it, so the entry would look wired and check nothing. **Four things only the live run found.** (1) The planned `pacman -Qo` ownership query is unnecessary — every distro unit in `/etc/systemd/system` is a symlink into `/usr/lib` (that is what `systemctl enable` installs) and every hand-written one is a real file, so `is_symlink()` is the same test with no subprocess and works off Arch. (2) **Three of the four named validation targets are orphans, not uncovered units**: `~/projects/MCP` and `~/Documents/Programming/MCP` no longer exist, so `ticktick-sync`, `ticktick-sync-db` and `offline-agents-dashboard` have dead `WorkingDirectory` paths, as does `garmin-sync` — all failing every start, silently, for as long as nothing watched them. (3) `sportsanalyser-pipeline` was **already wired**, in config.yaml rather than projects.yaml, so SportsAnalyser comes back clean exactly as predicted. (4) **Adding an agent touches four places**: `sysadmin.alerts` has a `chk_alert_agent` CHECK constraint enumerating the four known agents, so the first live run was rejected by the database *after* the scan succeeded (migration 007 widens it; a test now pins the constraint list to `self_monitor.AGENT_NAMES`), and the self-monitor's own hardcoded registry is the fourth — without it the new agent would run entirely unwatched by the service whose job is watching agents. The alert is **one rolled-up warning re-raised only when the count changes**, because `raise_alert` inserts unconditionally and a 6-hourly sweep would otherwise add four rows a day forever — SNAG-AGENT-002 in a new costume. Counts are exhaustive by construction (`scanned = monitored + folded + findings`) after the first draft *inferred* "monitored" and reported 20 where the truth was 12. **Live result: 44 units seen, 6 excluded, 38 scanned → 12 monitored, 8 timers folded into their oneshot service, 11 orphaned, 0 unmonitored, 7 host.** Zero unmonitored findings is the headline: every live project's units are already wired, and the estate's real debt is 11 dead units plus 7 unwatched host services. 109 new tests — suite 1276 → 1385.

- **2026-08-06 — Estate triage: the board is now 6 rows instead of 18.** The status declarations that make the roadmap machinery worth having. `PupilProgressTracker` and `customer-churn-model` **moved to `~/projects/archive/`, not deleted** — the estate's existing convention, reversible, and anything under `archive/` is inferred archived without a projects.yaml edit. The distinction mattered: PupilProgressTracker is fully pushed to GitHub (0 unpushed) so deleting it would have been safe, but **customer-churn-model has no remote and its single commit is unpushed** — `rm -rf` would have destroyed 7 files that exist nowhere else, which is exactly the risk `no_remote` is ranked above everything to prevent. Seven projects declared `dormant` (staleness unpenalised, roadmap advice waived, still scored on everything else): `sports_analyser`, `daiy`, `BSL-Translator`, `BudgetApp`, `InvestingAssistant`, `terrible`, `portfolionew` — each annotated with the last commit that changed **code**, ignoring the bulk `~/projects` reorganisation commit that touched every repo. Declaring SportsAnalyser dormant *is* the resume-or-park decision its 152-day stalled flag was asking for; its endpoints stay monitored because the services are still running. `Athenaeum` is deliberately left **active** despite being idle: marking it dormant would waive the advice while 2.9 MB of real source still has zero commits and no remote. Board: 18 rows → **6** (Alfred, ImbaBots, sysadmin-service, venture-assistant, alfred-glance, Athenaeum), 0 stalled; 25 with `include_inactive=true`.

- **2026-08-06 — Estate init: 14 repos given the standard document set by a 14-agent fan-out, and the run found two more bugs in the scanner.** One agent per repo, each followed by an independent verifier — 28 agents, 0 errors, ~4 minutes, ~1M subagent tokens. Guardrails: create-only (never overwrite), never write `handoff.md` (the hook owns it), never touch git state, nothing invented. Independently confirmed afterwards by `git status --porcelain` across all 14: **no pre-existing file was modified anywhere** — the ` M` entries in ImbaBots (`.gd` source) and venture-assistant (reddit/producthunt fetchers) are the owner's in-progress work, which the verifiers correctly attributed by mtime rather than blaming the agents. 3 repos correctly received nothing (Alfred, alfred-glance, SportsAnalyser already conform); 11 gained 1–5 documents. **Two real bugs surfaced, both fixed.** (1) `first_unchecked_task` accepted unedited template scaffolds, so InvestingAssistant's board entry read `_Task 1_` — a syntactically perfect, semantically empty task list. `is_placeholder` now skips `_Task 1_`/`_Description_`/`TODO:`-style items and falls through to git, deliberately conservative because a false positive silently hides real work. (2) `_latest_snapshot_query` has no freshness test, so **a project deleted from disk keeps its final snapshot forever**: `PA-worktrees` was removed during the reorganisation and still held a board row two days later with a health score and a next action. The board now drops rows more than an hour behind the newest scan stamp. Board went 18 rows → 15, all with real next actions. Also archived three empty shells (`DotaImprover`, `TeacherPlanner` — a `.git` and nothing else) and removed a `projects.yaml` entry pointing at a path that does not exist, which was SNAG-CONF-001 being reintroduced by hand. **Not fixed, flagged only** (the no-overwrite rule held): Alfred's README still says "Ollama (local)" and "no application code yet" — both false since ADR-0052 and seven shipped domains — and alfred-glance's says "Pre-skeleton. No Android code yet." 26 new tests — suite 1250 → 1276. Nothing is committed anywhere; every agent-written file is untracked and reviewable.

- **2026-08-06 — Session 28 follow-up: the board's first real use found two presentation faults.** Asked why ImbaBots (ongoing) "didn't get flagged", when it had been — `top_action: "Write a README.md"`, plus a roadmap item, plus a genuinely useful git-derived next action (`M5-T04: tier-matched garage sparring dummies`). It was invisible for two separate reasons, both now fixed. **The board defaulted to neglect order**, putting an actively-developed project at row 12 of 18 while abandoned ones led — correct for "what have I let slide", exactly backwards for a page opened to see current work. `?sort=` now takes `activity` (default) or `neglect`; ImbaBots is row 2. **`GET /api/projects/actions` is saturated by a single systemic finding**: 11 projects share one `no_remote` risk, risk sorts before everything, and roadmap advice is worth 0 points by design — so the default limit of 10 returned nothing but "Add a git remote", and `total_available: 68` did not say *what kind* of advice had been cut. The response now carries `dropped_by_kind`, because a list that silently drops a whole category reads as "there is nothing else". Roadmap docs and basic hygiene were also written into Contract 1 of [guides/monitorable-project.md](../guides/monitorable-project.md) as the estate standard — waived for dormant/archived, with the note that **declaring `status:` is the higher-leverage move than writing any document**: an undeclared project defaults to active, which is the whole reason the board showed 18 for a four-project estate. 5 new tests — suite 1250 → 1255. **Open decision**: whether missing roadmap docs should cost health-score points (currently not — it would move every active project at once and could fire alerts as a side effect).

- **2026-08-06 — Session 28: Roadmap findings + the estate board.** The scanner has always answered "how tidy is this directory" and never "what was I doing and what comes next"; the only document it read was `README.md`, and only to check the file existed. Four pieces, built so Alfred can show the estate **without ever reading a directory** — sysadmin does the filesystem work and hands over JSON. (1) A global **SessionEnd hook** writes `docs/sessions/handoff.md` in whatever repo the session ran in. This replaces an instruction that was never true: `CLAUDE.md` has said "postflight generates handoff" for months, `claude-preflight.sh:20` dutifully looked for the file, and `claude-postflight.sh` contains no handoff code at all — hence an empty `docs/sessions/` after four months of sessions. The hook refuses to write when a session changed nothing, so asking one read-only question can't overwrite a real handoff with "no changes". (2) `sysadmin/services/roadmap.py`, a pure parser resolving a **next action** in preference order handoff → tasks → git: the plan says what was intended, the handoff says where work actually stopped, and when they disagree the record wins. (3) `findings["roadmap"]` recorded by the organiser with **no score deduction** — deducting would move every active project's score at once and could trip alert thresholds as a side effect of adding a feature, so roadmap advice ships at 0 points using the `no_remote` precedent, waived entirely for dormant/archived projects (nagging a deliberately parked repo to write a session handoff is busywork dressed as progress). (4) `GET /api/projects/board` — one call, contract-pinned, pre-sorted stalled-first then longest-idle, plus a capped `"Pick This Up"` briefing section. **Age qualifies content**: a next action from a handoff older than 30 days is not today's task but a resume-or-park decision, and `next_action_source` (`handoff`/`tasks`/`git`) tells the consumer how much is actually known — a git commit subject standing in for a next action must not render like a handoff-authored step. **Two faults only the live run caught**, both invisible to the fixtures: Alfred keeps its handoff at `docs/roadmap/handoff.md`, not `docs/sessions/`, so the estate's busiest project returned nothing; and its tasks file tracks sessions in a status **table** rather than checkboxes, so a box count returned `0` open tasks for it — `open_tasks` is now `None` ("not measurable") versus `0` ("measured, empty"), the same unchanged-vs-unknown distinction the disk review already draws. Verified against the live DB: 18 active projects, SportsAnalyser correctly flagged stalled at 136 days. Consumer side specced in [guides/alfred-projects-page.md](../guides/alfred-projects-page.md). 48 new tests — suite 1202 → 1250.

- **2026-08-06 — Maintenance: venture-assistant wired into monitoring; three llama-servers found running on CPU.** Config-only in this repo, but the wiring exposed a live estate fault. venture-assistant had four unmonitored user units and no projects.yaml entry: `venture-chat.service` (granite-3.1-8b, :8080) is now its `backend` — llama.cpp's own `/health`, not an app API, because the project has no backend yet (8300 stays reserved for one) — with `venture-embed` (:8082) and `venture-enrich-nightly.timer` in config.yaml's service list per the one-backend-per-project limit and the oneshot→timer rule. `venture-chat-large.service` is deliberately unmonitored: it is `static`, up only during the 02:00 drain, and would alert 23 hours a day. **The fault**: `alfred-inference`, `venture-chat` and `venture-embed` had all been loading their models into system RAM since installation — `-ngl 99` is a request, not a constraint, and at boot they start before amdgpu is ready, so llama.cpp logs `no devices with dedicated memory found` and falls back to CPU while the unit stays `active (running)` and `/health` returns 200. Granite was doing CPU inference at 14.8 GB RSS. Nothing in the estate could see it: the health check curls a port, and both Alfred's and venture's pre-dispatch GPU guards sample busy-% — which reads *idle* precisely because nothing is on the card. **`After=dev-dri-renderD128.device` does not fix this** and was tried first: udev does not TAG the DRM render node with `systemd`, so that device unit is permanently `inactive (dead)` and ordering against it is a no-op (`systemctl --user show dev-dri-renderD128.device -p ActiveState`). The working gate is `~/.local/bin/wait-for-dgpu`, a 45 ms `ExecStartPre` that polls `llama-server --list-devices` for the adapter *by name* — not by `Vulkan0`, since the index is positional and the iGPU can be the only device enumerated early in boot — and exits non-zero on timeout so `Restart=on-failure` self-heals rather than serving silently from RAM. A second fault surfaced from the VRAM arithmetic: the 02:00 drain (first ever run scheduled tonight) needs ~14.8 GB while granite holds ~6.1 GB of the ~18.5 GB free, so `venture-chat-large` now `Conflicts=`/`After=` `venture-chat` to evict it, and `venture-enrich-nightly` gained a second `ExecStopPost` to start granite again — `Conflicts=` does not put it back, and without that line the daytime trickle would have stopped after the first night. `venture-embed` gained `-ngl 0` to make its documented CPU-only intent enforced rather than accidental. Verified live end to end: all three now show `Vulkan0 model buffer size`, the eviction cycle was replayed by hand (11.9 → 20.4 → 11.9 GiB, all endpoints 200), and Alfred's in-repo unit template was updated to match so the installer does not undo it. Session 26 gained **port-registry reconciliation** (unregistered listeners, contended defaults like the 8080 venture holds, and real collisions), and the port registry in the monitorable-project guide gained the three llama-server rows plus a "never take a tool's default port" rule. 123 config tests green. **Needs `sudo systemctl restart sysadmin.service` to take effect.**

- **2026-08-06 — Session 24 Tier 3: weekly LLM-narrated disk review.** `sysadmin/services/disk_review.py` plus a `disk_reviews` table (migration 005 — a separate table from `project_reviews` rather than a shared one with a discriminator, so neither migration can disturb the other's rows). Its facts come from **two tables on purpose**: occupancy delta from `resource_snapshots`, junk deltas and per-kind reclaim from `filesystem_audits` via Tier 2. A week where reclaimable junk grew 3 GB while occupancy fell is a different story from one where both rose, and a review built on either table alone cannot tell them apart. Baselines are the oldest row inside the window, and a lone audit is explicitly *not* its own baseline — deltas come back `None` rather than 0, because "unchanged" and "unknown" are different answers. Four surfaces mirroring the portfolio review: `GET /api/files/review`, `POST /api/files/review/generate`, a Monday 05:45 cron (staggered after the 05:30 project review so only one llama-server generation is in flight) and a "Weekly Disk Review" briefing section — `_build_review_section` is now parameterised by model, so the 8-day freshness rule exists once instead of per review kind. **The Session 23 numbers rule turned out to need strengthening, not just obeying.** The first live generation reproduced the failure in a worse form: handed a prompt listing "25.0 GB across 50 directories" *and* an explicit "do not restate any figure", dria-agent-a-3b restated them and then invented **"each consuming 5GB"** — a quotient derived from data the prompt itself had supplied. Instructing a model not to use a number it can see is a request; not showing it one is a constraint. `build_review_prompt` is now figure-free by construction — sizes become bands ("very large"), categories become named phrases (`KIND_PHRASES`, because Tier 2 titles like "Clear 11400 stale downloads" carry counts in the title itself), occupancy becomes a direction plus a horizon — and a test asserts no digit reaches the model outside API paths. Re-verified live against llama-server: zero figures in the model's prose. It also ignored "no markdown, no headings, no lists" on both attempts, so `strip_markdown` removes headings, bullets, ordered-list markers and bold emphasis deterministically. Read transaction is committed before inference (the other Session 23 rule — this host's `idle_in_transaction_session_timeout` is 1 min), asserted by an ordering test. 55 new tests — suite 1147 → 1202.

- **2026-08-06 — Session 24 (Tiers 1–2): File organiser recommendations + forecast promotion.** The file organiser's mirror of Sessions 21–23, with a different currency: **reclaimable megabytes**, not health-score points. That difference drove the design. The new pure `sysadmin/services/file_recommendations.py` gets its own `FileRecommendationInfo` contract rather than reusing `RecommendationInfo` — one `points` field meaning "score recovered" or "megabytes" depending on which producer filled it would be unreadable at the call site. And the currency turns out to apply to only three of the finding types: duplicates, old downloads and stale caches free space, while misplaced files, empty dirs and similar folders free **nothing** (moving a file reclaims no bytes), so those price at 0.0 MB and rank by `item_count` beneath anything with real megabytes rather than being given an invented currency to compete on. Large files are a fourth case — measurable but not reclaimable, since only the user knows which are junk. Stale project dirs split in two: caches (the existing endpoint removes them) and **rebuildable** dirs (`node_modules`, `.venv` — 25 GB on this box, no executor, so the advice names the manual step, Session 22's convention). New `GET /api/files/actions` mirrors `GET /api/projects/actions` and is the only `/api/files/*` route that reads a second table: `filesystem_audits` tracks junk *accumulation*, only `resource_snapshots` knows disk *occupancy*, and occupancy is what answers "when does the disk fill up" — so a projected 80 %/90 % crossing inside 30 days outranks every byte total, the way `no_remote` outranks score arithmetic. The forecast maths moved out of the tray to `sysadmin/services/forecast.py`; not a pure move, because `disk_series()` took a `ResourceHistoryResponse` the backend never has — the primitive is now `disk_series_from(entries, mount)` over `(timestamp, disk_usage)` pairs, which an ORM row and a parsed contract both produce, with the contract version a one-line adapter. `_compute_reclaimable_forecast`'s hand-rolled least-squares was deduped against the promoted `linear_fit`. **Two bugs only the live run caught**, both invisible to the mocked tests (the Session 23 lesson repeating): the `findings` blob is truncated to 50–100 entries per category before storage, so the endpoint reported 200 misplaced files against an actual **11,877** and 100 downloads against **11,400** — now fixed by passing the audit row's own count columns, with sizes summed from a truncated list labelled a lower bound ("at least 25 GB") and the note saying "largest N" only for the lists the agent really sorts by size; and duplicates/old downloads recorded no sizes **at all**, making the currency uncomputable, so `FileOrganiserAgent._scan` now stores `size_mb` per download and `size_mb`/`reclaimable_mb` per duplicate group (priced at "delete all but one copy") and sorts both before truncating so the cap keeps the biggest wins — pre-existing rows read tolerantly and say "sizes were not recorded — rescan to price it" instead of claiming 0 MB. Verified against the live DB. **Tier 3 (the weekly disk review) is deferred to a second sitting.** 48 new tests — suite 1099 → 1147.

- **2026-08-05 — Maintenance: SportsAnalyser fully wired into monitoring + tier-pattern ideas captured.** Config-only session. The `sports_analyser` projects.yaml entry had URL-only health checks while three live *user* units sat unmonitored: backend and frontend now carry `systemd_unit` + `user: true` + journal log sources (warning filter), and a new `frontend` block covers Next.js on :3200. The daily pipeline is `Type=oneshot`, so per the alfred-evaluate rule its **timer** (`sportsanalyser-pipeline.timer`) is monitored via config.yaml's service list instead — projects.yaml can only model backend/frontend. Verified: config parses, merge produces the three services + two log sources, all units live and endpoints healthy, 118 config tests green. **Needs `sudo systemctl restart sysadmin.service` to take effect** (running since before the edit). Noted in passing: `sportsanalyser-backend.service` is `disabled`, alive only via the frontend's `Requires=` — worth enabling. ideas.md also gained a "repeat the project-manager tier pattern" section with four candidates (file organiser tiers, service reliability scoring, **unmonitored-unit detector** — which would have caught today's gap automatically, plus `garmin-sync`/`deadlock-api-ingest`/`ticktick-sync`/`offline-agents-dashboard` still uncovered and eight orphaned PA units — and log aggregator tiers folded into SNAG-AGENT-002). Follow-up the same day: **`docs/guides/monitorable-project.md`** writes the shape down as a contract — scanner rubric (automatic) vs service integration (manual: port registry with 8300/3300 reserved next, canonical `GET /api/health` for new projects, `<project>-<role>.service` user units, oneshot→timer, same-day projects.yaml wiring with `user: true`, verify via `/api/sysadmin/status`) — and `~/.claude/CLAUDE.md` now points every future new-project Claude session at it, so conformance is enforced at creation time rather than remembered. Roadmap housekeeping closed the day: Sessions 10–23, the 2026-07-24 maintenance work and nine fixed SNAGs moved verbatim to `archive/completed_2026-08-05.md` (snag_list.md keeps a one-line index per fix), the live follow-ups those sessions had buried were hoisted into the tasks.md Backlog before archiving, and the four tier-pattern ideas became **Sessions 24–27**.

- **2026-08-04 — Session 23: Project-manager Tier 3 — weekly LLM portfolio review.** The last tier: llama-server narrates the portfolio weekly. `sysadmin/services/project_review.py` gathers structured facts — latest score per project, week-on-week delta (latest vs the *oldest snapshot inside the window*, so no scan cadence is assumed), and each project's top three recommendations — builds a bounded prompt (250-word limit; a 3B model rambles unconstrained), and asks `LLMClient` for a four-section narrative (what moved / what's decaying / archive candidates / next week's focus). **The LLM is optional at every step**: unavailable inference falls back to a deterministic digest of the same facts with `llm_used: false` — built this way because the GPU was busy during development, which forced the right design: GPU-busy is a normal state, not an error. Reviews persist in the new `project_reviews` table (migration 004 — whose first draft the schema-drift guard rejected for a nullability/index mismatch between model and migration, exactly its job) with the structured inputs stored in `stats` so the prose stays auditable against its data. Surfaced three ways: `GET /api/projects/review` (latest) and `POST /api/projects/review/generate` (on demand, auth), a Monday-05:30 cron (`schedules.review_*`, before the briefing, gated by `agents.project_organiser.weekly_review`), an `info` alert on generation, and a "Weekly Project Review" briefing section while under 8 days old. All 20 new tests mock inference — the GPU was never touched — but a live fallback-path run against the real DB stored review #1 and caught a real bug the mocks missed: Session 22's recommendations read `stale_branches` findings as strings when the scanner stores dicts; fixed with the real shape pinned in tests. The deferred live-inference check ran the same day once the GPU freed and caught two mock-invisible issues, both fixed: the review held a DB transaction across minutes of inference and this host's `idle_in_transaction_session_timeout=1min` killed the connection (now commits the read transaction before calling the LLM); and the 3B model fabricated the numeric "what moved" section under two different prompts, so the narrative is now **hybrid** — `build_movers_section` computes movement deterministically and the model writes only the qualitative sections, which it grounds accurately. Suite 1076 → 1099.

- **2026-08-04 — Session 22: Project-manager Tier 2 — recommendations engine.** The organiser stops at "this project scores 45"; the new engine answers "and here is how to get the points back". `sysadmin/services/recommendations.py` is a pure module (no DB, no FastAPI) that maps a snapshot's findings to ranked advice where **every item mirrors exactly one scorer deduction** — `points` is the score recovered by acting on it, cross-checked by tests against the analyser's arithmetic — and status-awareness matches the scorer too: a waived deduction (dormant staleness, archived branch rot) produces no advice, because there are no points behind it. The deliberate exception is `no_remote`: it never cost points (the scorer only records it) but surfaces as a 0-point `risk` item ranked above everything, because "the only copy of this repo is on this disk" outranks score arithmetic. Where a safe executor already exists the `action` field points at it (branch prune's dry-run endpoint, the todos listing); otherwise it names the config change or command. Two endpoints, both `response_model`-enforced with tray re-exports: `GET /api/projects/{name}/recommendations` (advice + `potential_score`, clamped to 100) and `GET /api/projects/actions` (portfolio-wide top wins, risk-first then points-desc, `limit` honest via `total_available`) — the latter declared **before** `/{name}` so it isn't captured as a project named "actions", with a regression test pinning that. The ideas.md housekeeping section from the reorganisation migrated as promised: the missing-remote follow-up is now served natively by `/actions` after every scan; the un-detectable items were reframed as detector ideas. 25 new tests — suite 1051 → 1076.

- **2026-08-04 — Session 21: Project-manager Tier 1 — deep discovery + project status.** Prompted by the same-day reorganisation of `~/projects` into category folders (`apps/`, `web/`, `ml/`, `games/`, `learning/`, `archive/` — see `docs/roadmap/ideas.md` for the follow-ups it parked), which the organiser's top-level-only discovery couldn't see into: it found 3 projects where 24 exist. Discovery is now depth-aware (`agents.project_organiser.discovery_depth`, default 2): a directory with a project marker IS a project and is never descended into (vendored sub-repos stay invisible, e.g. habitTracker's inner repos), while a marker-less directory is a *category* searched one level further. Projects also carry a **status** — `active | dormant | archived` — declared per entry in projects.yaml (`status:`, matched by the same path → name → basename lookup as `alert_threshold`, now shared as `ProjectsConfig._setting_for`) or inferred from location: anything under `<projects_root>/archive/` is archived, all else active. Status shapes the rubric rather than gating the scan: dormant waives the staleness deduction (resting on purpose is not a defect), archived also waives branch hygiene, and both still score docs/TODOs/locks so the number keeps meaning "how tidy is this directory"; the waived facts are still *recorded* in findings, which also gain the status itself (JSONB — deliberately no DB migration or contract change). Alerting: archived projects suppress the default floor via `_effective_threshold` (extracted from `_execute` precisely so it could be tested pure) but an explicit `alert_threshold:` still wins — the PA entries switched from `alert_threshold: 0` to `status: archived` as the worked example. Verified against the real tree: 24 projects discovered, all 8 archive/ residents inferred archived. 28 new tests — suite 1023 → 1051.

- **2026-07-24 — Maintenance: two runtime-environment bugs found by running for real.** Both surfaced the moment the live `sysadmin.service` picked up the Alfred config, and both had passed verification because verification happened in an interactive shell on the API's event loop — neither condition holds inside the daemon. **SNAG-SYSD-001**: `systemctl --user` locates the session bus through `XDG_RUNTIME_DIR`, and a system unit's environment holds only `PATH`, so *every* `user: true` systemd check failed — and because the old helper ignored the exit code and read the empty output as "no ActiveState → not active", a live `alfred-evaluate.timer` was reported `critical`. `sysadmin/utils/systemd.py` now builds the subprocess environment in one place and injects `XDG_RUNTIME_DIR` (default `/run/user/<uid>`) for user-scope calls, fixing the status check, the details endpoint and start/stop/restart together; `DBUS_SESSION_BUS_ADDRESS` is deliberately not derived, having been proven unnecessary against the live bus. Crucially a failed *query* is no longer a verdict about the *unit*: it raises `SystemdQueryError`/`UserBusUnavailableError` → status `"error"`, which raises no alert and touches no streak counter, while a genuinely inactive unit stays `critical`. Migration 003 widens `chk_health_status` to permit `'error'`, a value `_check_service` could always return but the DB had never allowed. **SNAG-AGENT-003**: `SysAdminAgent.startup()` built one `httpx.AsyncClient` on the API loop, but agent runs happen on APScheduler threads under `asyncio.run()`, which closes its loop afterwards — so pooled keep-alive connections outlived their loop and `llama-server` reported `unreachable / "Event loop is closed"` while curl answered in a millisecond, intermittently and per-host depending on which pooled connections had already been dropped. New `sysadmin/utils/async_http.py` (`LoopBoundClient`) lends a long-lived client out only on the loop that built it and hands anywhere else a short-lived one closed on exit; the agent now opens a run-scoped pool inside `_execute` and has no startup hook at all. The audit for the same pattern found `LLMClient` (identical live exposure via the log aggregator) and `Notifier` (latent), both converted. The regression test drives a real loopback server across two successive `asyncio.run()` calls — a mock transport holds no sockets and cannot reproduce this — and includes a guard asserting a naively shared client still fails, so the harness is known to be able to catch it. Both fixes verified against the live system with the daemon's environment simulated. 33 new tests — suite 990 → 1023. **The running `sysadmin.service` needs a restart (system unit, requires sudo) to pick this up.**
- **2026-07-24 — Maintenance: PersonalAssistant → Alfred migration.** PA is dead and Alfred replaced it, so everything the service pointed at PA was repointed or retired. **projects.yaml**: the `personal-assistant` entry (whose `path` — `/home/gaddi/projects/personal-assistant` — had *never existed*, the real directory being `PersonalAssistant`, so its health check had been silently broken) is replaced by `alfred` → `/api/health` on :8100 and :3100 for the Nuxt frontend, both `alfred-backend.service`/`alfred-frontend.service` **user** units; `alfred-glance` added scan-only (Android/Gradle, no service, no port) alongside `daiy`. This exposed a real gap: Session 15 added `user: true` to `MonitoredService`/`LogSource` but **never plumbed it through the projects.yaml path** — `ProjectEndpoint`/`ProjectEndpointLog` had no such field and `to_monitored_services()`/`to_log_sources()` dropped it. Now added (log blocks inherit their endpoint's scope unless they override it), because the failure mode is silent and permanent: proved live that `read_journal("alfred-backend.service", user=True)` returns 500 entries where `user=False` returns 0, which is exactly how the old PA entries rotted unnoticed. **alfred-evaluate** is monitored via `alfred-evaluate.timer`, not its service — the service is `Type=oneshot` and therefore inactive-by-design between its daily 08:00 runs, whereas a timer holds `ActiveState=active` (`SubState=waiting`) while armed, so the ordinary systemd check reads it correctly and an inactive timer genuinely means the schedule has stopped; no special-casing needed. The dead PA repos (`PersonalAssistant`, `PersonalAssistant-auto`, `PA-worktrees`) are **retired but retained** with `alert_threshold: 0` — they stay visible in the dashboard and remain branch-pruning targets, and since scores are clamped at 0 and the test is `score < threshold`, 0 is mathematically never-alert (they score 15/10/80 against the global floor of 40, so they *would* otherwise alert on every scan). **PA integration disabled** via a new `personal_assistant.enabled` flag (model default `True`, so configs predating it are unchanged): `Notifier.send_notification` and `send_briefing_data` now short-circuit before any HTTP call, logging once per process at INFO rather than warning per attempt, and the briefing's daily "delivery failed" warning drops to DEBUG when the integration is off. Kept deliberately as a dormant feature flag, not deleted, so it can be repointed if Alfred grows an inbox — Alfred's full 67-path OpenAPI schema has no notification/briefing/digest route today. Also: Alfred's :3100 origin added to `service.cors_origins` and the `mute_services` comment re-exampled off PA. All nine monitored services verified `ok` against the live config. 12 new tests — suite 978 → 990.
- **2026-07-24 — Session 20: Project scoring & branch hygiene.** The project organiser can now act on the branch rot it reports: `POST /api/projects/{name}/branches/prune` (`sysadmin/services/branch_actions.py`) follows Session 18's safety model — POST behind `require_auth`, **dry run unless the body sets `confirm: true`**, and the same manifest either way, one row per local branch with its last commit date + sha, merge state, upstream/ahead counts and the reason it is (in)eligible. Eligibility is "merged into the default branch **and** stale for `stale_days`+ days", with merged-ness taken from git (`repo.is_ancestor`), never inferred from dates; deletion uses `git branch -d` so git re-checks it independently. The dangerous case needs **two flags** (`include_unmerged` on the request *and* `branch_actions.allow_unmerged_delete` in config, both default off, re-checked at execution), and the default branch, `protected_branches` globs, the checked-out branch, worktree branches and anything ahead of its upstream are never deleted regardless. The default branch is **detected** (remote HEAD → `init.defaultBranch` → conventional names → sole branch) and when it can't be, nothing is planned. Paths confined to `projects_root`, `max_deletions` capped at 20 per call (a request may only lower it), `min_stale_days: 7` floors the window. On the real PA-auto (224 branches, all merged) a dry run plans 20 and reports the rest as capped. Scoring also got two fixes: the hardcoded `< 40` health alert became `agents.project_organiser.alert_threshold` with a **per-project override in projects.yaml** (`alert_threshold:`, matched by path → managed name → path basename, absent = global, so existing files behave identically), and the TODO deduction is **capped at 30 points** (`max_todo_penalty`, `null` = uncapped) with the raw figure kept in `findings.todo_penalty_capped` — PersonalAssistant (327 TODO + 38 FIXME) and PA-auto (290 + 18) were being docked 185/154 and pinned at 0, so nothing they improved could show. New contracts `BranchCleanupResponse`/`BranchInfo` with `response_model=`. 107 new tests, all against throwaway `git init` repos under `tmp_path` — suite 871 → 978.
- **2026-07-24 — Session 18: File organisation & cleanup actions.** First endpoints that move and delete real files, so the safety model led the design and lives in one dependency-light module (`sysadmin/services/file_actions.py`): **dry run by default** (body must carry `confirm: true`), POST-only behind `require_auth`, source *and* destination resolved before the root check so `..`/symlinks cannot escape `scan_root`, symlinks never followed, `.git`/`node_modules`/dot-dirs/`projects_root` never entered, existing destinations skipped rather than overwritten (with an `O_CREAT|O_EXCL` reservation closing the rename race), and **delete means the XDG trash** — a minimal freedesktop implementation instead of a new dependency, which refuses (rather than silently copy+deletes) when the file is on another filesystem; overriding needs `force_delete` *and* `actions.allow_permanent_delete`. Three endpoints, one shared manifest contract: `POST /api/files/organise` (new **books** and **archives** categories, loose code in `~/` flagged never moved, PDFs routed Books/ vs Documents/ by filename markers then a bounded `/Type /Pages` page-count probe — unknown always means Documents), `POST /api/files/clean/duplicates` (reuses the agent's fingerprint via a promoted `file_hash()`, keeps newest or largest, retain-one-per-group asserted in code and re-checked before execution), and `POST /api/files/clean/downloads` (archive or trash past a configurable age). Category → folder mapping is now config-driven in the new `agents.file_organiser.actions:` block. Also fixed Session 17's finding that **file_organiser had never run**: APScheduler's `IntervalTrigger` puts the first fire at `now + interval`, so a 24h job never fires on a box that restarts daily — hours-scale agents now get an explicit first run 60s after startup. 118 new tests, all on `tmp_path` trees — suite 576 → 694.
- **2026-07-24 — Session 19: Dashboard enhancements.** The file organiser's audit finally has a UI: a new **Files tab** (`sysadmin_tray/dashboard/files_tab.py`) shows the `GET /api/files/status` summary and reclaimable total, a **Quick Wins** card (empty dirs, stale caches, cache size) and a **Disk Growth Forecast** card, plus a findings table switchable between duplicates, misplaced files and large files. Charting stayed dependency-free — `sysadmin_tray/widgets/trend_chart.py` generalises the `QPainter` approach already used by the Overview tab's resource chart, and drives both the new **per-project health trend** (Projects tab cards are now clickable; `GET /api/projects/{name}` already served the stored score history, which arrives newest-first and is reversed for plotting) and the forecast card. Forecast maths lives Qt-free in `sysadmin_tray/forecast.py`: `/api/files/trends`'s regression is formatted as-is for reclaimable growth, while disk-threshold crossing dates (80 %/90 %) come from a tray-side least-squares fit over 30 days of `resources/history` — junk accumulation and disk occupancy are different series. **Read-only by design**, since the file-action endpoints were being written in parallel; the one wired action is the pre-existing stale-cache clean, behind a confirmation dialog that names `__pycache__`/`.pytest_cache`, states the megabytes, and caps the promised empty-dir count at the 50 the endpoint really removes. `/api/files/*` and project-detail shapes appended to `sysadmin/contracts.py` (parse-side only); a 404 there means "no scan yet" and renders as an empty state, not an error. 177 new tests — suite 576 → 753.
- **2026-07-24 — Session 16: Notification calm.** New `NotificationPolicy` (sysadmin_tray/notifications.py) owns the shared per-fingerprint state and decides what the tray says: D-Bus `replaces_id` reuse so a state change replaces its popup instead of stacking (verified live), a 30-minute flap cooldown that rolls repeats into "X flapped N×", one "3 new alerts" summary when several arrive in a poll, "Snooze 1h" action button plus per-service `mute: true` for expected-down services, progressive escalation (quiet opener → persistent critical after 3 failing polls), `transient` hints so feedback toasts skip KDE's history, desktop DND via the `Inhibited` property (more restrictive of app-DND/desktop-DND wins; app DND still decides criticals), and an opt-in hourly warning digest. All tunables live in the new `notifications.tray:` config block. 93 new tests — suite 364 → 459.
- **2026-07-24 — Session 17: Self-monitoring.** New `GET /api/sysadmin/self` (`sysadmin/services/self_monitor.py`) reads `agent_runs` back for the first time: per-agent last run/status, duration trend, consecutive failures, and a *stalled* flag whose window is derived from each agent's configured interval (`interval × self_monitor.stall_grace_multiplier`, floored at `min_stall_grace_seconds`) rather than hardcoded — never-run agents are deliberately not flagged. The SysAdmin agent raises/auto-resolves `"<agent> agent stalled"` alerts from the same report. New SSE endpoint `GET /api/sysadmin/events` (`sysadmin/services/sse.py`, `StreamingResponse`, no new dep) turns the dormant `event_bus.py` into the push path — agents publish `alert.raised`/`alert.resolved`/`agent.run`/`service.status` (buffered until their transaction commits, handed to the API loop via `EventBus.publish_threadsafe` since agents run on scheduler threads), heartbeat comments keep idle streams alive, disconnects unwind cleanly, and the path is access-log-excluded like `/health`. Resource anomaly detection (`sysadmin/services/anomaly.py`) adds z-scores over 7 days of `resource_snapshots` for CPU/RAM/each mount with cold-start and flat-series guards, suppressed when a fixed-threshold alert already covers the resource. New `self_monitor:`/`events:`/`anomaly:` config sections; no schema change. Verified live against the real service and DB. 117 new tests — suite 364 → 481.
- **2026-07-24 — Session 14: Config consolidation + docs.** New `sysadmin/defaults.py` (stdlib-only) is the single source of the API host/port — backend `ServiceConfig` and tray `TrayConfig` both import it. Magic numbers lifted to config.yaml with unchanged defaults: project grade bands (`agents.project_organiser.grade_bands` 80/60/40), reclaimable-space milestones (`agents.file_organiser.reclaimable_milestones_mb` 1/5/10 GB), briefing/retention cron times (new `schedules:` section, 06:00/03:00), CORS origins (`service.cors_origins`). docs/ARCHITECTURE.md rewritten from the real code (was an untouched template) with component diagram. pydantic-settings dropped (unused); confirmed zero env-var reads so CLAUDE.md now says "config.yaml only" instead of referencing a nonexistent .env.example; CLAUDE.md Step 4 test commands filled in. claude-preflight.sh now lists open SNAG count + titles from the Open Issues section only (Fixed Issues no longer inflate counts). 9 new tests — suite 355 → 364.
- **2026-07-24 — Session 13: Test hardening + CI.** Tests now run against the REAL app: `sysadmin/main.py` exposes `create_app()` and conftest builds it with only the lifespan stubbed (routers, middleware, exception handlers, auth deps all production). New shared contracts module `sysadmin/contracts.py` (pydantic-only) is the single source of truth for tray-consumed response shapes — set as `response_model=` on 13 backend routes and imported by `sysadmin_tray/models.py` (hand-copied dataclasses deleted; root cause of SNAG-TRAY-005 gone); Contract Registry in CLAUDE.md filled in. Schema drift guard (`tests/test_schema_drift.py`) found real drift: fixed alembic/env.py double-reflection and added migration 002 (NOT NULL alignment on 22 columns + idx_alerts_active direction) — `alembic check` now clean. New tests for briefing, event bus, app factory, contract round-trips. `scripts/smoke_test.sh` curls the live service (4 checks, fail-fast). GitHub Actions CI (ruff + pytest, headless PyQt6). mypy adopted (8 errors found and fixed, now clean); repo-wide ruff cleanup (191 issues). Suite 327 → 355.
- **2026-07-24 — Session 15: LLM migrated Ollama → llama.cpp.** New `sysadmin/services/llm_client.py` (`LLMClient`) speaks llama-server's OpenAI-compatible API (`POST /v1/chat/completions`, health via `GET /health`); config `ollama:` → `llm:` (url `http://localhost:8081`, model informational — single loaded model). Monitored service + log source renamed to llama-server / `alfred-inference.service`, with new `user: true` support so systemd/journalctl helpers can address *user* units (`systemctl --user`, `journalctl --user`). Verified live end-to-end: real completion, `summarise_with_llm` stored a genuine summary, briefing Overnight Log Summary section populated. 13 new transport-mocked tests — suite now 327.
- **2026-07-24 — Session 12: API authentication.** Shared bearer token (`api.auth_token` in config.yaml) enforced via a FastAPI dependency (`sysadmin/auth.py`, `secrets.compare_digest`) on all seven mutating POST endpoints — service actions, alert ack, DND, scan-all, project/file scans, stale-cache clean. Read-only GETs stay open so tray + PA dashboards keep working. Tray client sends the token automatically (same config.yaml). Unset/empty token → auth disabled with a startup warning (config.yaml is committed, so the committed value is a placeholder — see [guides/api_auth.md](../guides/api_auth.md)). PA-side token wiring is a follow-up in the PA repo. 24 new tests — suite now 314.
- **2026-07-24 — Session 11: Verified bug fixes.** Alert ack returns a real 404 (SNAG-API-001), access-log exclusion fixed to the real `/health` path with the real router under test (SNAG-API-002), blocking psutil calls moved off the event loop via `asyncio.to_thread` in `/ports` and `_take_resource_snapshot` (SNAG-API-003), tray marks connection lost on malformed/skewed API responses and `from_dict` parsing is defensive (SNAG-TRAY-005). 12 new tests — suite now 290.
- **2026-07-24 — Session 10: Resolved uncommitted loose ends.** Removed unreachable StatsPopup (dashboard won; SNAG-TRAY-004), `get_last_commit_date` now checks all branches (SNAG-AGENT-001), removed dead `count_stale_branches` and unused `orphan_detection` flag, narrowed `get_repo` exception handling with logging. Promoted codebase-review backlog to Sessions 10-20 in tasks.md.

_See [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for full history._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
