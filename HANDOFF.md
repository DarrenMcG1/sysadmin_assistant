# Handoff — 2026-08-28

## Next action

Fix `SNAG-DOCS-006` — make `check_convention` emit `convention:unchecked` unconditionally so a register in which every open entry is checked reports nought rather than falling silent, which is `ports_checked`'s rule arriving at this repository's own claims register and is the fifth way the count can move that `SNAG-ESTATE-014` did not catalogue.

## Session 112 is complete — the cheap fix reached one shape of four

`SNAG-LOG-006` is **fixed**, and the costing its entry never did is what
settles which of its two candidates was honest.

**The four shapes.** `BaseAgent.run` swallows `_execute`'s exception, so
the exceptions that escape it come from the bookkeeping around the work.
Driven through the real `run()`: `_execute` *and* `_record_outcome`
raising (journal holds `agent_run_failed`), `_record_outcome` alone
(`agent_run_completed`), `_record_start` (**no line at all**) and
`_flush_events` (`agent_run_completed`).

**The cheap candidate reaches one of them.** Narrowing
`COVERED_SIGNATURES` to `run_type == "scheduled"` can speak only where an
`agent_run_failed` line exists. It is also the *more* expensive of the
two, not the cheaper: `unwrap_json_message` returns `{"logger": …}` and
its own docstring refuses to promote further envelope fields into the
identity, and `COVERED_SIGNATURES` would gain a third key component
`known_noise` does not share while `NOISE_SEVERITY`'s comment turns on
the two answering one question.

**The entry misnames its second trigger.** `POST /api/files/organise` is
a synchronous action route returning `FileActionResponse`; the discarded
task was in `POST /api/files/scan`. `check_manual_run_unawaited` counted
five discards across two *files* and never named a route, so it reported
`match` — the right number about the wrong thing — for eleven days.

**The residual signal is measured, and *when* was never the problem.**
asyncio's fallback fires at `ERROR` on the loop turn after the task
completes; no `gc.collect()` is needed or helps. What it emits is the
defect: a 252-character signature and a 220-character title naming
`BaseAgent.run` and this module's path, so all five triggers share one
row, moving `run()` forks it, and on a shorter checkout path the
exception text falls inside the cap and forks a row per failure.

**What was built.** `spawn_manual_run` holds the reference and
`_report_manual_run` speaks — to the **journal and never the database**,
because the exceptions that reach it *are* database failures
(`unit_failure.py`'s argument, one layer in). `manual_run_failed` is a
17-character signature; `exc_info` was measured landing under its own
envelope key, so the traceback stays out of the identity and one query
away in `raw_line`. Cancellation is recorded at `warning`, which
`FAULT_SEVERITIES` excludes — that tuple extracted from an inline literal
in `LogAggregatorAgent._execute` so the rung is derived rather than
restated.

**Options rejected.** A per-agent reference set (a distinction with no
reader); a `run_type` parameter (a scheduled run must not arrive here —
APScheduler's listener already owns it, and a second supervisor is the
second-owner defect inside the fix for a case of it); dropping the
cancellation line (`known_noise`'s rule 2 — the residue is identical to a
failure's); and a second alert family (it would need a session at the
moment the session is what failed).

**The check retired and the detector did not.** Every member of `CHECKS`
names an *open* entry, so `manual_run_unawaited` and the `discarded_tasks`
helper it was the only caller of are gone; the AST walk lives on as
`TestNoTriggerDiscardsItsTask` in `tests/test_manual_run_supervision.py`,
`FROZEN_TABLES`' rule.

**Suite 2790** (2772 + 20 − 2). Ten mutations driven, each red on the
right test, **two of them wrong on the first attempt**: removing the
`finally` produced a `SyntaxError` rather than a leak and had to be
rewritten as a discard moved inside the guard, and the priority
round-trip test read `PRIORITY_MAP` with an `int` key when the map is
keyed on the string journalctl emits.

**Deployed and verified live.** Restart 2026-08-28 14:13:52 (PID 3716817
→ 3745842), schema checked at head 017 *before* the signal, `/health`
200. The real `POST /api/sysadmin/scan-all` put all four agents through
`spawn_manual_run`: four `agent_run_completed`, **zero**
`manual_run_failed`. It ships untriggered, the position `SNAG-LOG-005`
shipped in.

**Nothing is blocked.**

## Session 111 is complete — the notice had no lifecycle because it should never have been a row

`SNAG-AGENT-010` is **fixed**, by the second of the two candidates it
named and against the framing it gave that candidate. The live parser
reads **99 entries either side, open 23 → 22** at estate-manager's
committed `c545fa8` on a clean tree. Suite **2764 → 2772**, 9 added and
1 retired. All nine ops claims ok. Restart owed and taken at
**13:41:23**; no migration.

### What the sitting settled

- **The entry named one writer and the box had three.**
  `files/review.py:553`, `monitor/log_review.py:575` and
  `monitor/health_review.py:1055` write the identical bare
  `session.add(Alert(...))` at `info`. The symptom was one row because
  only the disk review's scheduler path has ever fired — `disk_reviews`
  holds 4, three of them the manual `POST` route which never announced.
  Grepping from the symptom finds one writer; grepping the *shape*
  finds three.
- **The lifecycle candidate was ruled out by arithmetic, not taste.**
  It anchors to the next run; the row was written 2026-08-17 05:45 and
  the next generation was due 08-24 05:45, when the daemon was down
  (first `agent_runs` row that day is 07:00). Under that fix the row is
  open today at 271 h with the same wrong sentence.
- **The surviving candidate needed nothing built.** Its framing —
  *"let the tray read `/api/files/review`"* — names a tray feature that
  does not exist; `sysadmin_tray/` holds no reference to any review
  endpoint. `briefing/data.py`'s `_gather` reads all three review
  tables directly and always has.
- **The clinching observation is one payload disagreeing with itself.**
  The briefing dropped the Weekly Disk Review as stale at 11 days
  (`_REVIEW_FRESH_DAYS` is 8) and carried `Weekly disk review ready` in
  the same envelope's alert digest. One announcement, two owners, and
  only one of them holding a freshness rule.
- **A notice was being counted as a fault by this repository's own
  review.** `health_review._gather_alerts` takes no severity filter and
  its sentence reads "Distinct faults alerted", so the health review
  would have narrated its own announcement in the next week's
  `new_titles`. The fixture had already normalised it, using
  `"Weekly disk review ready"` as its example of a fault. Filtering the
  query was refused — it leaves three immortal rows standing and
  teaches the count to ignore a severity `known_noise` and
  `COVERED_SIGNATURES` use legitimately.
- **The suite was pinning the immortality as intended behaviour**,
  which is why this was found by counting the table rather than by a
  red test. `test_the_announcement_escapes_the_sysadmin_resolve_sweep`
  treated escaping the resolve sweep as the property to protect; read
  the other way it is the defect, since retention deletes an `alerts`
  row only when it is resolved.
- **The guard is two halves that fail apart, falsified rather than
  asserted.** A stand-in that builds the row and never adds it fires
  only the provenance half, so a behavioural test alone would have
  passed it. The provenance half is an `ast` walk, not a grep, because
  `health_review` legitimately imports `Alert`.

### What was measured and deliberately not acted on

- **The defect class is closed, not just the instance.** Every
  remaining direct `Alert(...)` writer — `stalls.py`, `failures.py`,
  `unit_failure.py` — has a documented, argued lifecycle;
  `snag_claims.py`'s write is `SNAG-ESTATE-010`'s probe inside a
  rolled-back transaction. No other family lacks one.
- **The severity-filter question has an empty population.** Over the
  last 7 days `alerts` holds 13 critical rows / 5 titles, 39 warning /
  13, and **1 info** — the notice just removed. No `covered_by` or
  `noise_reason` rows in the window, so widening
  `health_review._gather_alerts` to exclude quietened rows would be a
  rule tuned against zero observations. Not filed.

### The near-miss worth carrying

The first parser drive returned `unrecognised` / 0 entries and was one
signature-read away from a cross-repo message accusing estate-manager
of breaking the parse. `read_snags` takes the document *text* and reads
a path as a one-line document; it has taken text at every commit that
has ever touched it. **Session 108 hit this same trap earlier today and
recorded it in the snag-list header, and it is also in memory** — so
the note is written and not read. The recovery route was the same both
times: read the signature before concluding anything about their tree.
Nothing was filed, because there was nothing to file.

## Session 110 is complete — the fix landed in the ranked order, and it half-closed a different entry

`SNAG-AGENT-009` is **fixed**, in Session 109's order: `_raise_judged`
(838 held events), `EstateJudgeAgent._execute` (131),
`_maintain_port_alerts` (0 in 65 runs, and its docstring now says so).
The live parser reads **99 entries either side, open 24 → 23** at
estate-manager's committed `047eb8a` on a clean tree. Suite **2750 →
2764**, 14 added and none removed. All nine ops claims ok. Restart owed
and taken at **13:03:15**; no migration.

### What the sitting settled

- **`BaseAgent.refresh_alert` owns the comparison and the write, and
  *finding* the row stays with each caller.** The three reach it three
  ways for reasons of their own — the estate judge already holds the ORM
  rows, the port family bounds its read by a title prefix, and
  `_raise_judged` keeps the title-only snapshot `SNAG-AGENT-007` gave it
  — so a base class taking a *title* would own a predicate its
  subclasses state three ways.
- **The 838's row is read at the hold, not carried in the snapshot.**
  Widening it is bounded by *the table* (51,924 open rows before
  `SNAG-AGENT-004`); a read at the hold is bounded by *the judgements
  the run made*. Measured at 665,937 rows: **84 buffers, 0.098 ms**.
- **`details` is compared through a JSON round trip, or the gate is
  decorative.** `JSONB` has no tuple, so a plain `!=` reports a
  difference no write can settle and every held poll rewrites for ever.
  What is *stored* is the caller's dict, so a raise and a refresh handed
  one input write one row.
- **`_written_titles` splits from `_open_titles`** so a title judged
  twice inside one run — two identically named GPUs — is suppressed
  rather than rewritten by the second judgement. Which of the two is
  current is undefined and the run must not answer it twice.
- **The gate is a floor, not a promise of quiet.** A family whose
  `details` is a live measurement differs on every held poll. Bounded at
  ~0.26 per run, and an `UPDATE` rather than the `INSERT`s
  `SNAG-AGENT-006` objected to.

### What only running it could have said

- **The refresh read lands on `idx_alerts_active`, not
  `idx_alerts_open_by_agent`.** The docstring claimed the agent-scoped
  one; `EXPLAIN` refuted it. One open row makes either partial index
  free and the planner takes the older — exactly what `SNAG-AGENT-007`
  recorded about its own pair. Corrected in place rather than left.
- **`SNAG-ESTATE-010`'s check flipped to `mismatch`.** This fix is the
  third of the three shapes that check enumerates, so `details['holder']`
  now reaches a standing row while the rung does not. The clause came
  **out** of `QuietenReading.reached` rather than the verdict being
  accepted: a `reached` still reading the blob answers `mismatch`
  whatever happens to the rung, which is a control this fix broke. The
  falsification asserting the blob alone was a mismatch is kept and
  **inverted**, and a second test drives its arrival with no stand-in at
  all, so a revert shows up there.
- **That probe found its standing row by `message == PROBE_MESSAGE`** —
  the value this fix rewrites — so it keys on the title now, which is
  the identity the entry it checks turns on.
- **Four stand-ins modelled a database this code no longer talks to**,
  and that was most of the work: `test_unit_ports.py` answered the dedup
  read with *titles*, `test_estate_judge_agent.py`'s `FakeAlert` had no
  `message`, `test_alert_dedup.py`'s fake ignored the WHERE clause and
  could not answer `.first()`, and `conftest.mock_session`'s bare
  `AsyncMock` returns a coroutine from `.scalars()` — a failure no
  database produces, which reads as a bug in the code under it.

### Verified on the box, not only in the tree

- The real `_raise_judged` against the real database in a rolled-back
  transaction: a row raised at `VRAM at 91.5%` judged again at 51.0%
  gives `raised=0`, **one** row, message and `details` both moved,
  `suppressed=1 / refreshed=1`; a second identical judgement
  `refreshed=0`; **0 rows of residue**.
- All three families ship the counter live — the 13:04:17 runs of
  `estate_judge` and `service_discovery` and the 13:08:17 run of
  `sysadmin` each carry `refreshed` in `agent_runs.details`.
- Five falsifications, each firing on the tests that name it: the
  refresh made a no-op (7), the gate removed (7), the JSON round trip
  removed (1), `details` left frozen (7), the two sets merged (1).

### Deliberately not done

- **`SNAG-AGENT-009` gets no check.** A check here would assert that a
  held row *is* refreshed, which is this fix's own tests rather than a
  claim about the box that goes stale between sittings.
  `SNAG-PORT-003`'s retired check is the warning about writing one
  anyway. What does watch the box is `SNAG-ESTATE-010`'s, whose witness
  half now depends on this fix running.
- **`SNAG-AGENT-010` is untouched.** That row was never *held*, so this
  fix cannot reach it, and its lifecycle question stays open — which is
  the next action above.

---

## Previously — Session 109 is complete — the population was in the family the entry never named, and the one stale row was a different bug

`SNAG-AGENT-009` is **measured and decided, not fixed**; `SNAG-AGENT-010`
is opened. The live parser reads **98 → 99 entries, open 23 → 24** at
estate-manager's committed `516116f`. Suite **2750, unmoved** — no guard
was added, because the fix is not built and there is nothing for a check
to hold still against. All nine ops claims ok. No migration, no restart,
no production code.

### What the sitting settled

- **The mechanism is real in both named families, and it was driven
  rather than argued.** Against the live database in a rolled-back
  transaction: `_maintain_port_alerts` raises naming
  `user:alpha.service`, then `user:beta.service` takes the port —
  `held: 1, raised: 0`, message still naming alpha.
  `EstateJudgeAgent._execute` holds two titles through a score moving
  42 → 31 and a streak 8 → 9 days — `raised=0`, both messages unchanged.
- **`details` is frozen too, which the entry does not say.** The ports
  `findings` blob still carried alpha. A fix that moves only `message`
  leaves half the row lying, and `_record_recurrence` — the precedent
  this entry cites — already reassigns both.
- **The live population is 1 open row and 0 of it is this entry.** The
  box holds exactly one unresolved alert; its message *is* stale, and it
  belongs to a family with no dedup branch at all. Filed as
  `SNAG-AGENT-010` rather than counted here, because same symptom and
  opposite mechanism is exactly what a population count must separate.
- **The entry's two halves are not comparable, and one is empty
  all-time.** `_maintain_port_alerts` has taken the held branch **0
  times in 65 runs**; `EstateJudgeAgent._execute` **131 times across 77
  of 240**. Giving them equal billing is `SNAG-PORT-003`'s framing
  defect, one entry later.
- **The largest population is a family the entry never mentions.**
  `SysAdminAgent._raise_judged` has suppressed **838** raises across 751
  of 2,303 runs. Full table: threshold+service 838, collation 386,
  estate judge 131, armed orphans 5, ports 0 — **1,360** all-time.
- **The stale-prone set is decided by a predicate rather than by
  inspection**: a held message goes stale iff it interpolates a quantity
  that moves while the fault stands. The units roll-up and the service
  family put the moving figure in the **title**, so a state change mints
  a new row — twelve roll-up rows on this box, twelve different counts —
  and collation states a condition. Left: the threshold family, the
  estate judge (**18 of 21** templates) and ports.
- **The drift is 100% of every held poll that could be measured.**
  Joining `resource_snapshots` to each held window of the 23 post-dedup
  `High VRAM usage` rows: **42 of 42** polls carried a moved figure,
  mean **8.15 pp**, max **43.8 pp**, and **19 of 42** read below the
  90% threshold the message was asserting.
- **Decision: keep `P3`, re-scope, take candidate 1.** `P3` survives
  because no dedup row has ever been held past `reminder_hours: 24`
  *with a figure-bearing message* — the four that outlived 24 h are
  condition-messages or title-coupled — so the consequence surface
  (`notifications.py:617` re-speaking the frozen message beside a live
  "Still open N hours") has an empty population to date.
- **The other two candidates are refuted by measurement, not
  out-ranked.** Carrying the state in `details` is the *same* write
  landing where nothing reads: **3 of 3** tray render sites read
  `message` and none reads `details`. Documenting that a message is a
  first sighting cannot survive the sentence being republished as
  current every 24 h, and reaches the threshold family not at all,
  whose message has no content but the measurement.
- **Candidate 1's own objection does not transfer, and that is the
  number the entry was missing.** `SNAG-AGENT-006` was about `INSERT`s
  accumulating rows — 60 for one dead timer in five hours. This is an
  `UPDATE` to a row that already exists: it accumulates nothing, ceiling
  **0.26 per run** across ~5,200 runs, lower again once gated on the
  text differing.

### The sitting's own mistake, recorded because it produced a confident number

The first drift query read the VRAM percentage at
`gpu_usage->0->>'vram_percent'` when the blob is keyed `card0`, so every
comparison was `NULL <> x`, which is never true, and it reported **0 of
42 polls moved** — the answer that would have closed the entry as
harmless. Nothing errored. What said so was `min_seen` and `max_seen`
coming back empty beside a non-zero poll count:
`a-check-needs-a-discriminating-witness`, met inside the instrument
rather than in the thing being measured.

### Two corrections to what was written down

- The entry names `log_aggregator._refresh`; **no such symbol exists**.
  It is `LogAggregatorAgent._record_recurrence`
  (`monitor/log_aggregator.py:524`), and reading the real one is what
  showed the precedent reassigns `details` as well as `message`.
- `SNAG-PORT-003`'s closing bullet calls this entry **`SNAG-PORT-004`**;
  the id minted was `SNAG-AGENT-009`. Left as-is in that entry rather
  than rewritten, since it is a closed entry's own record of what it
  believed, and noted here instead.

## Session 108 is complete — the blocker was gone, the family was three times bigger, and the name never carried the fact

`SNAG-PORT-003` is **closed** and `SNAG-AGENT-009` opened; the live
parser reads **97 → 98 entries with open unmoved at 23**. Suite
**2755 → 2750** (2755 − 18 + 13), ruff and mypy clean, all nine ops
claims ok. Daemon restarted **10:37:40**, `/health` 200 — owed this
time, unlike Session 107's. No migration.

### What the sitting settled

- **The entry's own framing was the smaller half of its defect.** It is
  filed as a *D-Bus* fault with a population of one, deferring itself
  for want of *"a second instance to tell a rule from a coincidence"*.
  `$XDG_RUNTIME_DIR/systemd/transient` holds **eight** runtime-created
  services: three bus-named and **five** `app-*@<32-hex>`. The second
  instance was there when the entry was written and was a **different
  shape**, which is precisely what makes a rule tuned to the first the
  coincidence.
- **Both named fixes are refuted by the count, and by which units were
  listening.** A `dbus-` prefix reaches 3 of 8; `:N.N` reaches 2,
  because `dbus-:1.21-org.a11y.atspi.Registry@0.service` sits beside
  `:1.2` and refutes the entry's own spelling of the pattern it
  rejects. Both leave `app-steam@455b2e51….service` (27036, 34223,
  46847, 57343) and `app-appimagekit_…@….service` (36577) — `.service`,
  colon-free, and holding ports on the day the entry recorded a
  population of one.
- **No name rule could have worked, which is the durable half.**
  `app-steam@455b….service` and `syncthing@gaddi.service` are the same
  shape. Separating them means deciding a 32-hex instance is special —
  `systemd-run`'s convention, which is the format-someone-else-owns
  objection the entry raised against `:N.N`, met from the other side.
  The name does not carry the fact, so the fix had to stop reading it.
- **The third fix is systemd's own answer and it is added, never
  substituted.** `runtime_unit_names` lists both managers' transient
  directories — the same class of signal `discover_units` reads for
  enablement, no second subprocess — and `observe_listeners` stamps
  `Listener.runtime_created`. The obvious reading is to *replace* the
  suffix test; `init.scope` refutes it, reporting `Transient=yes` from
  both managers while appearing in **neither** directory. So the listing
  is a proxy that under-reports, and additive cannot subtract.
- **Stamped at observation, not derived in the property**, so
  `judge_ports` stays pure below `observe_listeners` — the promise this
  module makes in its first paragraph. Nothing in production rebuilds a
  `Listener` from storage, so the stamp cannot go stale in a consumer.
- **The handoff's second question answered: no.** The entry predicted a
  new title every login; `port_alert_title` is keyed on the **port**, so
  the row dedups and what churns is the message. That makes the entry
  *less* urgent and the fix **no smaller** — a message-refresh reaches
  one of the eight by accident and none correctly, and Session 57's rule
  for a per-launch holder is to quieten it, not to describe it better.
  Fixing `transient` closes the staleness here outright, because no such
  finding is raised at all.
- **The retired check reported `match` against the fix that closed its
  entry.** `transient_misses_bus_name` asked
  `Listener(port=0, unit=name).transient` — a *synthetic* listener — so
  it assumed transience is a function of the name. It was built to be
  neutral between the two fixes the entry named, and both were
  name-based, so it inherited their shared assumption and the fix
  refuting both is invisible to it; read off the *observed* listener the
  same property returns `True`.
  `a-control-a-fix-breaks-is-not-a-control`, a third time, and the first
  where the coupling came from the entry's framing rather than the
  check's construction. It retired with the entry per the registry's own
  rule, and the reading is recorded in the entry rather than lost.
- **Live either side, through the production path.**
  `unit_ports(audited_only=True)` **13 keys → 12**, findings **0 → 0**,
  and the degraded path driven at `XDG_RUNTIME_DIR=/nonexistent`: one
  warning logged, `ok: True`, and the `.scope` holder still recognised.

### Two mistakes the sitting made, recorded

- **A cross-repo filing was nearly made against our own error.** The
  first drive of `estate.snags.read_snags` returned **0 entries,
  format unrecognised**, at HEAD *and* the working tree — which reads
  exactly like a regression in their parser between `1e7a9a9` and
  `516116f`. It was ours: the function takes the document *text* and was
  handed a *path*. Reading their signature before writing the message is
  what stopped it.
- **A falsification harness that reverts with `git checkout` deletes the
  fix it is testing.** The first pass restored `sysadmin/units/ports.py`
  from HEAD between stand-ins; the fix was uncommitted, so it went too,
  and only the next stand-in's missing anchor showed it. Re-applied, and
  every later revert came from a copy in the scratchpad.

### Left deliberately

- **`SNAG-AGENT-009` is filed, not fixed, and its `P3` is a guess.** The
  population is unmeasured — that is the next action above. Its three
  candidate remedies are not comparable until the number exists, and the
  obvious one (refresh every held row) is `SNAG-AGENT-006`'s per-run
  write arriving by the back door.
- **Two open entries now carry no check** (`SNAG-DOCS-006` and the new
  `SNAG-AGENT-009`), up from one, which is the cost of closing an entry
  whose check retired with it.
- **`app-signal-2308871.scope` and five other runtime units bind no
  port**, so the fix's effect on them is unobservable today and is not
  claimed. What is claimed is the four that do.

## Session 107 is complete — the instrument for an entry that argues for its own postponement

`SNAG-PORT-003` has a check and **stays open at `P3`**; nothing was
fixed, which is what the entry asked for. Open entries carrying no check
go **2 → 1**. Suite **2737 → 2755** (2737 + 18), ruff and mypy clean, all
nine ops claims ok. Daemon restarted **09:30:18** — see below, because it
did not need to be. No migration; no entry opened or closed, so the
parser still reads 97 with open at 23.

### What the sitting settled

- **The handoff's own proposed verdict rule was refuted by the first
  run.** It asked for a check "whose verdict flips on the day a second
  instance appears". The second instance was already here:
  `$XDG_RUNTIME_DIR/systemd/transient` holds **three** D-Bus activated
  units, so a verdict keyed on the population would have printed
  *refuted* against a live, untouched defect on day one — rule 1's
  reading, and the one Session 83 refused for `SNAG-LOG-013`. So
  `mismatch` is reserved for the entry being **dead**, and the blocker's
  disappearance rides in the note, which `render` prints on a `match`
  line too. `SNAG-TRAY-008`'s rule reached from the other side: an entry
  whose fix has become *buildable* must stay open, and one reported
  `mismatch` sits in the bucket with the ones to close.
- **The second instance is discriminating, not merely present.** The
  entry spells the rejected pattern `:N.N`, and
  `dbus-:1.21-org.a11y.atspi.Registry@0.service` sits beside
  `dbus-:1.2-org.kde.kdeconnect@0.service`. That is strictly the evidence
  the entry says is missing — a pair that tells a rule from a
  coincidence — and it is why the candidate pool is the **union** of the
  listener and runtime sets: only `:1.2` binds a TCP port, so a pool
  taken from `ss` alone reports the anchored naive fix complete, which is
  the one verdict this check exists to be able to refuse.
- **Two of the entry's own claims were corrected by the instrument built
  to measure it.** Its *"no consumer reaches it"* names
  `recommendations.py` and the estate judge and **not** `judge_ports`,
  whose `holders` map admits the listener because its guard is the
  property under test — one synthetic `DeclaredPort` produces a
  `wrong_unit` naming the per-session unit verbatim. And its predicted
  *"new title every login"* is not what it would get: `port_alert_title`
  is `Port collision on 1716`, keyed on the port, so the row deduplicates
  and what churns is the message. Both are recorded in the `Check`
  bullet rather than by rewriting the bullets they correct, because a
  check that edits the entry it reads is the second author
  `ops_claims` rule 6 exists to keep out.
- **Two of the eighteen tests passed against deliberately broken code, in
  one shape.** Both decided their `pytest.skip` from a value the break
  itself empties — the partial-rule test read `reading.candidates`, which
  a narrowed pool empties, and the failure-mode test read
  `reading.reach_title`, which removing that instrument nulls. Both
  decide from the box now.
  `a-control-a-fix-breaks-is-not-a-control`, found twice in one class.
- **The restart was not owed and was taken anyway.**
  `sysadmin/snag_claims.py` is reached from the `sysadmin-check-snags`
  console script and from nothing in `create_app()`, so the daemon's
  imported code did not move. The deploy check compares the newest `.py`
  on disk and its docstring already prices this: *"a file the daemon
  never imports reports a restart owed, and that fails in the direction
  that costs a needless `kill -TERM`"*. The alternative was a red claim
  at every preflight until an unrelated sitting restarted.

### Left deliberately

- **`SNAG-PORT-003` is not fixed and its priority is unchanged.** No
  family can raise on it today and its own first escalation trigger — a
  bus-named unit declared in `services.yaml` — has not fired. What
  changed is only that its argument for staying unfixed no longer holds.
- **The registry's second trigger is unmeasured and the check says so.**
  Whether the registry claims a bus-named holder's port *under a project
  name* needs the project join `wrong_project` already owns; 1716 is
  claimed as `_kdeconnectd_`, which folds to a name matching no project
  on disk. Reproducing that join would be a second implementation of an
  existing comparison, so the silence is stated rather than left to be
  read as an oversight.
- **One open entry still carries no check** (`SNAG-DOCS-006`).
- **Both estate messages are closed** (`8c1706d3`, `153c1c96`), and the
  bullet that stood here said the opposite — that they were
  estate-manager's to close. That was Session 106's clause carried
  forward unchecked. The brief says *"the receiver closes it when dealt
  with; the sender may withdraw it"*, and the close endpoint refuses a
  bystander with **409**: we are the receiver on both, so a receiver
  declining to close leaves the row open for nobody. Neither asked
  anything of us — *"Cost to us: none"* and *"Nothing is asked of you"*,
  in their own words.
- **Closing `8c1706d3` caught a live instance of what it warns about.**
  It asks that entry counts be re-derived rather than compared; this
  sitting's first pass carried `97 entries` forward from the previous
  handoff, and only drove `estate.snags.read_snags` when it came to write
  the close note. Re-derived at their committed `1e7a9a9`, clean tree:
  **97 entries, 23 open**. Said in the note rather than quietly fixed.
- **`estate.provenance.checkout()` is filed in `ideas.md`, not adopted
  and not declined.** It reports the commit of the code that *answered*
  where `estate_module_state` infers it from the tree, and they measured
  it would have read `DIRTY` at 14:12 inside a window we were driving
  them. Adopting it changes what four cross-repo checks report and the
  falsifications pinned to that wording, so it is its own sitting.

## Session 106 is complete — the band moved, nothing was raised, and the parse underneath it was wrong

`SNAG-PORT-001` is **closed**, `SNAG-PORT-002` opened and closed in the
same sitting, and `SNAG-PORT-003` **opened**. The live parser reads
**95 → 97 entries with open unmoved at 23**. Suite **2732 → 2737**, all
green — the two red on a clean tree when this sitting opened are the two
that closed. Daemon restarted **22:26:57**, `/health` 200, all ten ops
claims check out — **nine**, not the ten the previous handoff said, which nobody had counted. No migration; the change is one constant, one parse and
their guards.

### What the sitting settled

- **The widening raises nothing, and that had to be driven rather than
  reasoned.** `ServiceDiscoveryAgent._check_ports` was run through its
  own code path against the real `ss`, the real `services.yaml` and the
  real registry document at both bands: **findings 0 → 0, collisions
  0 → 0, advice 0 → 0**. The single observable difference is
  `unit_audited_ports`, 12 units → 13. So the entry's stated reason for
  deferring — *"widening the band changes what an alert family raises"* —
  had an empty population, which is `SNAG-LOG-002`'s shape for the fourth
  time here. The deferral was still correct: the only way to know it is
  zero is to drive it, and driving it is a sitting.
- **The entry's blast radius was wrong and both sides of the copy got it
  wrong the same way.** It names four comparisons; `in_range` has **two**
  production call sites and one of them is not a comparison —
  `judge_ports`' `wrong_project` gate, and
  `PortReport.unit_ports(audited_only=True)`. `port_shared`, `wrong_unit`
  and `duplicate_claim` never consult the band at all. estate-manager had
  already caught and corrected the identical overstatement on their side
  the same day (their ADR-0054 §5 → their `SNAG-ESTATE-070`).
- **1883 could never have contributed.** Root-owned socket, so `ss -p`
  names no holder, so it is `unattributed` and compared against nothing
  by construction. Widening a band over a port nobody can attribute buys
  jurisdiction and no observation — the distinction `ports_checked`
  exists to keep visible. `SNAG-ESTATE-009` is untouched, because the
  estate judge reads the holder out of `unit_ports`, which was never
  gated on the band.
- **`SNAG-PORT-002` is what the drive found underneath.**
  `_unit_from_cgroup` took the path from the *last* colon; `cgroup(5)` is
  `hierarchy:controllers:path` and only the first two fields are
  colon-free. A D-Bus activated unit
  (`dbus-:1.2-org.kde.kdeconnect@0.service`) lost its prefix and, with
  it, the `/user@1000.service/` that decides scope — a **user** unit
  stamped `system` since Session 26c. 1 of 30 attributed listeners, 4 of
  694 processes. No live consequence today; what the fix buys is that the
  next such listener is compared against the right identity.
- **The scope half needed its own witness.** The live specimen breaks the
  unit name and the scope together, so it cannot say which half a
  candidate fix repaired. A second test uses a shape where the colon is
  in the *slice* and not the leaf, where `rpartition` returns the right
  unit and loses only the scope. Three falsifications; a fourth stand-in
  (`split(":", 2)[-1]`) passes, correctly, because behind the
  colon-count guard it is the same code — recorded because an
  unexplained green in a falsification list reads as a gap.
- **The band has three statements and all three are pinned now.**
  `ports.DEFAULT_AUDITED_RANGES` gives `judge_ports`' fallback a name a
  test can address, because the pure module may not read `config.yaml`
  and so cannot derive what it governs. Without it a widening applied to
  `config.py` alone leaves every bare `judge_ports` call in the suite
  judging the old band while production judges the new one — green in
  both places.
- **Both of the producer's statements are read.** The check now parses
  their shipped `audit.yaml` — what the running audit actually reads — as
  well as the `config.py` default it was reading before. Their own test
  pins the two together, and one repository's guard is not this
  repository's evidence. Empty population today; witnessed against
  doctored copies in both directions.

### Not done, and named

- **`SNAG-PORT-003` carries no check**, so open entries without one go
  1 → 2 (`SNAG-DOCS-006` is the other). That is the next action above.
- **The stored sweep still carries the old band.** `service_discovery`
  runs six-hourly and the row in `unit_audits` was written 20:02, before
  the restart; the next run picks the widening up. Normal operation, not
  residue — the same fact `ports_checked` already reports as `false` on
  any pre-26c sweep.
- **Both estate messages stay open.** `8c1706d3` was honoured by
  re-deriving the entry counts rather than comparing them against
  yesterday's, but it is not this repository's to close. `153c1c96` — the
  `SNAG-ESTATE-*` namespace having two minters and no owner — was routed
  around by minting today's ids into `SNAG-PORT-*`, which is not the same
  as answering it; renaming this repository's 14 colliding ids is a
  sitting of its own and the ownership question is estate-manager's.
