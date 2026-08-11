# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-10

---

## Active Sessions

_Sessions 24–27 promoted from [ideas.md](ideas.md) on 2026-08-05. They are
**independent of each other** — take them in any order. 24 and 26 are done,
and 25's Tier 1 landed 2026-08-07; **25b/25c (reliability Tiers 2–3) and
27 (log aggregator tiers) remain**, plus 26b (port-registry
reconciliation), split out of 26 on 2026-08-07._

All four repeat the **tier pattern** proven by Sessions 21–23:

- **Tier 1 — measure**: structured findings; a score whose deductions are
  individually attributable.
- **Tier 2 — advice as data**: a *pure* module (no DB, no FastAPI) mapping
  each finding to ranked advice with an exact payoff, pointing at existing
  safe dry-run executors where one exists, naming the config change where
  one doesn't.
- **Tier 3 — periodic LLM narrative**: facts and deltas computed
  deterministically in code, bounded prompt, model writes only the
  qualitative sections, digest fallback when inference is unavailable,
  persisted with its inputs in `stats` for auditability, surfaced via
  endpoint + cron + briefing section.

**Two hard-won rules any Tier 3 must follow** (both cost a live debugging
session in Session 23): commit the read transaction *before* calling the
LLM — this host sets `idle_in_transaction_session_timeout=1min` and
inference takes longer — and never let the 3B model produce numbers; it
fabricated the numeric section under two different prompts.

### Session 24: File organiser tiers — disk instead of portfolio

**Complete 2026-08-06 (all three tiers).** Tier 1 already existed, so
this was Tiers 2 and 3 plus the module move. The currency is **reclaimable
megabytes** — MB, not bytes, because every source field is `size_mb` and
bytes would be fake precision on a value rounded to 1 dp at scan time.

- [x] **Promote the forecast maths out of the tray** →
      `sysadmin/services/forecast.py`. Not a pure move: `disk_series()`
      took a `ResourceHistoryResponse`, which the backend never has, so
      the primitive is now `disk_series_from(entries, mount)` over
      `(timestamp, disk_usage)` pairs — an ORM row and a parsed contract
      both produce that shape — with the contract version a one-line
      adapter. Tray imports it the way `models.py` already imports
      `contracts`; verified no FastAPI/SQLAlchemy leaks in. Added
      `most_urgent_projection()` (imminent crossing beats an exceeded
      lower threshold; exceeded beats a distant crossing) and deduped
      `_compute_reclaimable_forecast`'s hand-rolled least-squares against
      `linear_fit`
- [x] **Tier 2** — pure `sysadmin/services/file_recommendations.py`.
      **The currency only applies to three finding types.** Duplicates,
      old downloads and stale caches free space; misplaced files, empty
      dirs and similar folders free *nothing* — they price at 0.0 MB and
      rank by `item_count` beneath anything with real megabytes. Large
      files are a fourth case: measurable but not reclaimable, since only
      the user knows which are junk. Split stale project dirs into
      caches (executor exists) and rebuildable dirs (`node_modules`,
      `.venv` — 25 GB here, no executor, advice names the manual step)
- [x] `GET /api/files/actions`, risk-first. The risk needs a **second
      table**: `filesystem_audits` tracks junk accumulation, only
      `resource_snapshots` knows disk occupancy, and occupancy is what
      answers "when does the disk fill up"
- [x] Separate `FileRecommendationInfo`, **not** a reuse of
      `RecommendationInfo` — one `points` field meaning "score recovered"
      or "megabytes" depending on the producer would be unreadable at the
      call site
- [x] Contracts + tray re-exports; 48 new tests (1099 → 1147)

**Two Tier 2 bugs only the live run caught** — both invisible to the mocked
tests, which is the Session 23 lesson repeating:

1. **`findings` is truncated before storage** (50–100 entries per
   category). The real audit row lists 200 misplaced files against an
   actual **11,877**, and 100 downloads against **11,400** — up to 60×
   understated. Fixed by passing the audit row's own count columns as
   `true_counts`; sizes summed from a truncated list are now labelled a
   lower bound ("at least 25 GB"), and the note says "largest N" only for
   the lists the agent actually sorts by size before truncating.
2. **Duplicates and old downloads recorded no sizes at all**, so the
   currency was uncomputable. `FileOrganiserAgent._scan` now stores
   `size_mb` per download and `size_mb`/`reclaimable_mb` per duplicate
   group (priced at "delete all but one copy"), and sorts both lists
   before truncating so the cap keeps the biggest wins. Reading is
   tolerant: pre-existing rows say "sizes were not recorded — rescan to
   price it" rather than claiming 0 MB.

- [x] **Tier 3 complete 2026-08-06** — `sysadmin/services/disk_review.py`
      plus a `disk_reviews` table (migration 005, kept separate from
      `project_reviews` so neither migration can disturb the other's
      rows). Facts come from **two tables**: occupancy delta from
      `resource_snapshots`, junk deltas and per-kind reclaim from
      `filesystem_audits` via Tier 2. Four surfaces, mirroring the
      project review: `GET /api/files/review`,
      `POST /api/files/review/generate`, a Monday 05:45 cron (staggered
      after the 05:30 portfolio review so only one generation is in
      flight) and a "Weekly Disk Review" briefing section —
      `_build_review_section` is now parameterised by model, so the
      8-day freshness rule exists once. 55 new tests (1147 → 1202)
- [x] **Rescan happened 2026-08-06 12:05** as a side effect of live
      testing (the test server's file_organiser first-run fired). The
      new audit records sizes, so reclaim now prices at 43.6 GB instead
      of "unrecorded"

**The Session 23 numbers rule needed strengthening, not just obeying.**
First live generation reproduced the failure in a worse form: given a
prompt listing "25.0 GB across 50 directories" *and* an explicit "do not
restate any figure", dria-agent-a-3b restated them and then invented
**"each consuming 5GB"** — a quotient it derived from data the prompt had
supplied. Instructing a model not to use a number it can see is a
request; not showing it one is a constraint. `build_review_prompt` is now
figure-free by construction — sizes become bands ("very large"),
categories become named phrases (`KIND_PHRASES`, because Tier 2 titles
like "Clear 11400 stale downloads" carry counts), occupancy becomes a
direction and a horizon — guarded by a test asserting no digit reaches
the model outside API paths. Re-verified live: zero figures in the
model's prose. It also ignored "no markdown, no headings, no lists" on
both attempts, so `strip_markdown` removes those deterministically.

Still open:

- [ ] The model ignores the 150-word limit (final live narrative ran
      ~350 words). Harmless — it is honest prose with no invented
      figures — but the briefing section is longer than intended.
      Truncating mid-sentence would be worse; a summarise-again pass or
      a smaller `n_predict` would be the fix
- [ ] A single large cleanup flattens the 30-day disk fit for a month
      (usage fell 92.8 % → 67.3 % in late July, so every threshold reads
      `not_growing` and no risk can fire). Inherent to a least-squares
      fit over a fixed window; a shorter secondary window, or fitting
      only since the last sharp drop, would catch a resumption sooner

### Session 25: Service reliability scoring

Nothing scores *services*, yet the history is already in the DB:
`health_checks` streaks, `alerts`, `resource_snapshots`, `agent_runs`.

**Tier 1 complete 2026-08-07.** Tiers 2 and 3 remain — take them as
Sessions 25b and 25c.

- [x] **Tier 1** — `sysadmin/services/reliability.py` (pure, scores a list
      of `HealthPoint`) + `reliability_history.py` (the DB adapter) +
      `GET /api/services/reliability` + `reliability_scores` table
      (migration 008) + a 02:00 daily snapshot cron. 82 new tests
      (1359 → 1441). Live: `venture-assistant` 68, `internet` 77,
      `alfred-frontend` 95, 14 others 100
- [x] Score is `100 − downtime − instability`, both attributable:
      downtime = `round(100 − uptime%)` capped 60, instability = 5 per
      outage **episode** from the first, capped 25. Separate terms
      because they are separate failures — `internet` lost 7.5 % of its
      checks across *three* incidents (−15 instability, −8 downtime)
      while `venture-assistant` lost 27 % in *one* (−27, −5), and retry
      logic survives the second shape but not the first
- [x] The mute waiver landed as specified: `mute: true` **or** a name in
      `notifications.tray.mute_services` (the only way to mark a
      projects.yaml service, which has no `mute` field) → deductions
      computed and reported with `waived: true`, not applied. Required
      modelling `notifications.tray` backend-side for the first time;
      the tray still parses it independently

**Three departures from the plan, each forced by the live data:**

1. **"Mean time between alerts" was uncomputable as specified.** The
   `alerts` table records one row *per failed check*, not per incident:
   one internet outage wrote **123 rows in 7 days**, one
   `venture-assistant` outage wrote **81**. The mean of those measures
   `health_check_interval_seconds`. Incidents now come from consecutive
   non-ok runs in `service_health`, which collapse into episodes by
   construction — and it avoids a join on `details->>'service_name'`,
   the only (unindexed) link `alerts` has to a service.
2. **Restart frequency was dropped.** Nothing on this host records
   restarts: `NRestarts` is a live cumulative counter never sampled into
   the DB, and `agent_runs` records agent executions. Three measured
   metrics beat four where one is invented. Sampling `NRestarts` into
   the systemd check's `details` would make it computable in ~30 days if
   it is ever wanted.
3. **Coverage became a confidence flag, not a deduction.** The estate
   records ~81 % of expected checks (the monitor's own downtime), and
   services added on 2026-08-06 have 1 day of history against a 7-day
   window. Deducting for a gap would charge the service for *this
   application's* downtime, so it lowers `confidence` instead — and
   ordering deliberately ignores confidence, because a thinly-observed
   failing service is still the most interesting row on the page.

**One design call worth re-reading before Tier 3:** the endpoint
recomputes live (~28 ms) rather than serving the stored row, unlike
`/api/units/status`. The table exists for trending only, written at
02:00 — an hour *ahead* of the 03:00 retention purge, so the day's score
is written before the checks behind it can be deleted.

Also surfaced: `venture-chat` and `pgbackrest-backup-timer` are in
config.yaml with **zero health checks ever** (both added 2026-08-07,
backend not yet restarted). They score 100 at low confidence rather than
vanishing — "configured but never checked" is a finding, not an absence.

- [ ] **Tier 2** — recommendations tied to alert-history facts
      ("llama-server flapped 6× this week — likely GPU contention,
      consider raising its check interval"; "alfred-evaluate.timer
      inactive 3 days — the schedule has stopped"). Few safe executors
      exist beyond service restart, so most items name a config change —
      Session 22's established fallback convention
- [ ] **Tier 3** — weekly system health review: flappiest services, alert
      volume delta, anomaly summary, resource trend direction. Sits beside
      the project review in Monday's briefing and reuses the
      `project_reviews` table design (facts in `stats`, hybrid narrative)

### ✅ Session 26: Service discovery — the unmonitored-unit detector (done 2026-08-07)

**Directly requested 2026-08-05**: hand-registering each new project's
systemd units is tedious and rots silently. The contract this enforces is
written up in [guides/monitorable-project.md](../guides/monitorable-project.md);
this session is its mechanical backstop. Delivered Tiers 1 and 2; there is
deliberately **no Tier 3** (see below).

- [x] `sysadmin/services/units.py` — pure sweep of
      `~/.config/systemd/user/*.{service,timer}` and
      `/etc/systemd/system/*.{service,timer}`, findings **both ways**
- [x] **Unmonitored unit**: maps to a live project, nothing wires it.
      Path first (`WorkingDirectory`/`ExecStart` under the project dir),
      then normalised name-prefix, longest project wins
- [x] **Orphaned unit**: dead `WorkingDirectory`, or a project declared
      `archived`. Ranked `risk`, above everything else — this is not an
      unwatched unit, it is a broken one
- [x] **Host unit** — a *third* category the original plan did not have.
      `pgbackrest-backup` (the estate's only DB backup) and
      `ethernet-optimise` are hand-written, real, unmonitored, and map to
      no project, so the path-match filter would have dropped them
      alongside genuine distro units. They get a **config.yaml
      `services:` snippet**, not a projects.yaml one, because
      projects.yaml models only backend/frontend
- [x] Tier 2 `sysadmin/services/unit_recommendations.py` with
      ready-to-paste snippets, `user: true` for user units, oneshot→timer
      applied
- [x] **Advice-only.** No executor, and both endpoints are GET-only —
      asserted by a test
- [x] `sysadmin/agents/service_discovery.py`, `unit_audits` (migration
      006), `GET /api/units/status` + `GET /api/units/actions`
- [x] 109 new tests — suite 1276 → 1385

**Four things the plan got wrong, all found by running it:**

1. **The `pacman -Qo` ownership query is unnecessary.** Every distro unit
   in `/etc/systemd/system` is a *symlink* into `/usr/lib/systemd/system`
   (that is what `systemctl enable` installs) and every hand-written one
   is a real file. `is_symlink()` is the same test with no subprocess,
   and it works off Arch.
2. **Three of the four named validation targets are orphans, not
   uncovered units.** `~/projects/MCP` and
   `~/Documents/Programming/MCP` no longer exist, so `ticktick-sync`,
   `ticktick-sync-db` and `offline-agents-dashboard` point at dead
   directories — as does `garmin-sync` (`projects/PersonalAssistant`
   moved to `archive/`). They have been failing every start, silently,
   for as long as nothing watched them.
3. **`sportsanalyser-pipeline` was already wired** — in config.yaml, not
   projects.yaml. SportsAnalyser comes back completely clean, which was
   the predicted negative test.
4. **Adding an agent touches four places, not one.** `sysadmin.alerts`
   has a `chk_alert_agent` CHECK constraint enumerating the four known
   agents, so the first live run was rejected by the database *after* the
   scan succeeded (migration 007 widens it, and a test now pins the
   constraint list to `self_monitor.AGENT_NAMES`). The self-monitor's
   own hardcoded `AGENT_NAMES` is the fourth — without it the new agent
   would run entirely unwatched.

**Live result on this box (2026-08-07)**: 44 units seen, 6 distro/template
excluded, 38 scanned → **12 monitored, 8 timers folded into their oneshot
service, 11 orphaned, 0 unmonitored, 7 host**. The counts are exhaustive
by construction (`scanned = monitored + folded + findings`) after the
first draft inferred "monitored" and reported 20 where the truth was 12.

**Zero `unmonitored` findings is the real headline**: every live project's
units are already wired. The estate's actual debt is 11 dead units and 7
unwatched host services — including `pgbackrest-backup`, which nothing
would have noticed going quiet.

**No Tier 3.** Sessions 22 and 24 rank by health-score points and
reclaimable megabytes — both directly measurable. There is no equivalent
currency here, nothing makes two host units meaningfully "twice" one
orphan, and a weekly LLM narrative over 18 findings that change maybe
monthly would be prose about nothing. `UnitRecommendationInfo` carries no
score field at all.

**Pending ops action** (advice, not automation — decide before acting):
11 orphaned units are removable with the exact commands in
`GET /api/units/actions?kind=orphan`, and the 7 host units have
ready-to-paste config.yaml snippets.

### Session 26b: Port-registry reconciliation

**Split out 2026-08-07.** Was folded into Session 26 on 2026-08-06 on the
grounds that "the unit sweep already parses every `ExecStart`, so the
ports are free to extract". Half true: the sweep does parse ExecStart, but
`ss -ltnp` joining, collision detection and the registry migration are a
sitting of their own.

**Decided 2026-08-07 — option (b).** The port allocation moves into
`config.yaml` as structured data, with the table in
[guides/monitorable-project.md](../guides/monitorable-project.md) rendered
from it. (c) was cheaper but misses sidecars — the three llama-servers,
`venture-embed` — which is exactly the gap the reconciliation exists to
close. (a) would have left a markdown table as a load-bearing parser.

- [ ] Move the registry into `config.yaml`; render the guide's table from it
- [ ] **Unregistered listener** — a port held by a project's process with
      no registry row. Source of truth is `ss -ltnp` joined to the unit by
      PID/cgroup, not `ExecStart` alone: a port can come from a config
      file, an `Environment=` line, or a default the flag never mentions
- [ ] **Contended default** — a project on a well-known default (8080,
      3000, 5000, 8888, 9000). Advisory: it has not collided *yet*.
      venture-assistant on 8080 is the live example
- [ ] **Collision / near-miss** — two registry rows claiming one port, or
      a configured port already held by a different cgroup. The only one
      worth a warning alert; the failure is asymmetric (the loser fails,
      the winner looks fine)
- [ ] Reuse `sysadmin/services/units.py` — the parsed `exec_start` lines
      and the scope-aware unit identity are already there

### ✅ Session 28: Roadmap findings + the estate board (done 2026-08-06)

Directly requested: surface "what needs doing / where is this project at"
in Alfred, without Alfred ever reading a directory. Delivered:

- [x] Global **SessionEnd hook** (`~/.claude/hooks/generate-handoff.sh`,
      wired in `~/.claude/settings.json`) writes `docs/sessions/handoff.md`
      in whatever repo the session ran in. Replaces the instruction in
      CLAUDE.md that postflight "generates handoff" — it never did, which
      is why `docs/sessions/` sat empty for months.
      **Superseded 2026-08-10 by Session 37**: right that an instruction is
      a request and a hook is executed, wrong about what follows. SessionEnd
      cannot block, so the file it guaranteed contained only what `git`
      already knew — and by always existing, it removed the signal that a
      real handoff was missing
- [x] `sysadmin/services/roadmap.py` — pure parser for handoff / tasks /
      snag documents, resolving a **next action** (handoff → tasks → git)
- [x] `findings["roadmap"]` recorded by the organiser; **no score
      deduction** — that would move every active project at once and could
      trip alert thresholds as a side effect
- [x] `kind: "roadmap"` recommendations at 0 points (the `no_remote`
      precedent), waived for dormant/archived
- [x] `GET /api/projects/board` + `"Pick This Up"` briefing section
- [x] [guides/alfred-projects-page.md](../guides/alfred-projects-page.md)
      specs the consumer side

48 new tests (1202 → 1250). Two live-only findings, both fixed: Alfred
keeps its handoff at `docs/roadmap/handoff.md` not `docs/sessions/`, and
its tasks file uses a status **table** rather than checkboxes — so
`open_tasks` now reports `None` ("not measurable") rather than `0` for
the busiest project on the box.

**Same-day follow-up (2026-08-06), from the first real use.** The user
looked for ImbaBots — an ongoing project — and concluded it had not been
flagged. It had: `top_action: "Write a README.md"` plus a roadmap item.
Two presentation faults hid it, both fixed:

- [x] **The board defaulted to neglect order**, so an actively-developed
      project sat at row 12 of 18 while abandoned ones led. `?sort=` now
      takes `activity` (default — the working view, recently touched
      first) or `neglect` (the weekly triage view). ImbaBots is now row 2
- [x] **`/api/projects/actions` is saturated**: 11 projects share one
      `no_remote` risk, risk sorts first, and roadmap advice is worth 0
      points, so the default limit of 10 showed nothing but "Add a git
      remote" — 68 available, 10 returned, no indication of *what kind*
      was hidden. Response now carries `dropped_by_kind`
- [x] Roadmap + hygiene written into Contract 1 of
      [guides/monitorable-project.md](../guides/monitorable-project.md),
      waived for dormant/archived

**Open decision — should missing roadmap docs cost health-score points?**
Currently no (findings recorded, advice at 0 points). Deducting would
move every active project's score at once and could fire alerts as a side
effect. Worth taking deliberately once the status triage below has run.

**Estate triage, ranked (not started).** 26 repos, 4 genuinely active;
the dozen showing `days=1` are the `~/projects` reorganisation commit,
not work. In order of value: (1) declare `status:` for ~16 repos in
projects.yaml — one file, ~20 min, and the board drops from 18 rows to 4;
(2) the **11 repos with no git remote**, `sysadmin_assistant` among them;
(3) give this repo a README and a remote — the monitor is currently the
worst-scoring live project it monitors; (4) roadmap docs for whatever
survives (1) as active. An agent fan-out was considered and rejected:
after triage there are ~4 repos left, and the work that remains is
judgement, not volume.

**Follow-up worth taking:** the git fallback is weak where the
`~/projects` reorganisation touched every repo — a dozen projects report
`days_since_commit=1` and a next action of "WIP snapshot before
~/projects reorganisation", which is bulk housekeeping, not work. Either
ignore known bulk-commit subjects, or weight staleness by commits that
touched source rather than by the last commit date.

### Session 27: Log aggregator tiers — take with SNAG-AGENT-002

Thinnest of the four, and deliberately coupled to the open snag: error
**signature fingerprinting** is the fix for both.

- [ ] Fix [SNAG-AGENT-002](snag_list.md) — group by unit + normalised
      message signature within a poll, raise one alert carrying an
      occurrence count (mirroring Session 16's "X flapped N×")
- [ ] **Tier 1** — per-source error-rate trends week-on-week; "new error
      signatures this week vs last" (falls out of the fingerprinting)
- [ ] **Tier 2** — recommendations like "this warning appeared 400× — add
      to known-noise or fix it"
- [ ] **Tier 3** is half-built: the overnight LLM log summary already runs
      in the briefing. Extend rather than duplicate

---

## Momentum sessions (29–32) — moving projects along, not monitoring them

Requested 2026-08-06. Sessions 24–27 make the service a more complete
*monitor*; these four are the other axis — changing what happens on a given
morning. Everything built so far reports; nothing acts.

**The design constraint they share:** each one must make the output
*shorter*. The obvious way to add features here is more surfaces and longer
lists, and that is the failure mode — 400 TODOs and 51 routes have not moved
a project yet. Success is measured in what stops being shown.

Take 29 first: 30 consumes its ranking, and 31/32 are more useful once one
project at a time is the unit.

### Session 29: The one-thing endpoint — done 2026-08-10

- [x] `GET /api/projects/next` — **one** project, one action, one sentence
      of why it is that one. Not a filtered board: a different object, with
      a `reason` field the consumer must render. `NextProjectInfo` carries
      four fields the board has no use for (`days_unchanged`,
      `unchanged_since`, `unchanged_scans`, `at_window_edge`), which is what
      stops it reading as `/board?limit=1`
- [x] **The open design question, and it is the whole feature: what decides
      when two projects both have a live next action?** Decided 2026-08-10:
      **stuckness** — how long the stated next action has stood unchanged —
      with the most recently committed project breaking a tie. Rejected:
      longest-idle (ranks by guilt), nearest-to-finishing (reads
      `done_tasks`/`open_tasks`, which are `None` for three of five active
      projects, so it would be blind to most of the population while looking
      authoritative), smallest-next-step (unmeasurable — nothing records the
      size of a step and every proxy is invented)
- [x] **The unit is elapsed days, not scans.** The cadence is irregular by
      construction (6-hourly until Session 35, daily from the timer since,
      plus manual scans — two live scans 17 minutes apart on 2026-08-08), so
      a run length in scans ranks by how often the organiser happened to
      run. Run length in observations is reported as evidence, not ranked on
- [x] Honour `?exclude=` so a deferred suggestion can be skipped without
      re-rolling the same answer. Repeatable; exclusions are counted in
      `skipped` and echoed in `excluded`, so a caller that excluded its way
      to an empty answer can tell that from an estate with no work in it
- [x] Contract-pinned; feeds alfred-glance, whose whole premise is glance
      then act
- [x] Eligibility: active, `next_action_source` in (`handoff`, `tasks`), and
      not a handoff stating there is nothing queued. `roadmap.looks_like_no_action`
      catches the two live cases ("No unchecked task found — set one before
      the next session"); conservative like `is_placeholder`, since a false
      positive hides real work
- [x] Empty is `200` with `project: null` and a reason, never `404` — a 404
      would collapse "every project is up to date" into "no scan has run"
- [x] Deliberately **not** in scope: a resume/deep-link command. Considered
      and dropped 2026-08-06

**Left for a later session** (found while building, deliberately not fixed):

- [ ] The eligible population is **2 of 23** fresh projects — 20 inactive,
      1 with no stated action, 2 stating there is nothing queued. The
      endpoint is correct and the estate is the constraint; whether
      `says_no_action` should itself become a nudge ("write a next action")
      belongs with Session 31, not here

### Session 30: Next action → an Alfred work item — declined by the consumer 2026-08-11

**Not blocked, not deferred: refused, by the repo that would build it.**
Alfred accepted [ADR-0064][adr64] on 2026-08-07 — three days *before*
Session 29 shipped — declining the whole projects-page arc for v1 and
putting it behind two named triggers. This row said "nothing here blocks
it beyond Session 29" and was wrong when it was written; the block was
never on this side.

The decline is not a rejection of the endpoints. ADR-0064 §1 finds the
estate's momentum data **already ships**, as the daily digest's
`Pick This Up` section, rendered with this guide's own honesty treatment.
A second surface over the same data is the failure mode ADR-0063 was
written to avoid — the ADR names it "a surface that exists because its
data exists".

**The triggers, and where they stood when this was checked (2026-08-11):**

| Trigger | Fires at | Live |
|---|---|---|
| (a) Stall returns | `stalled_count ≥ 2` on `?sort=neglect`, sustained across two consecutive weekly reads | **0** |
| (b) Estate outgrows the five-row cap | `count ≥ 12` active | **5** |

Neither is close, and (b) moved the wrong way: 6 active when the ADR was
written, 5 now. The board carries 3 stalled projects among the 20
inactive ones, which the trigger deliberately does not count — declaring
a project dormant *was* the decision, so it cannot also be a stall.

- [ ] **Do not build this here or in Alfred until a trigger fires.** Both
      are one `curl` against an endpoint that already ships, which is the
      point of writing them as numbers:
      `curl -s 'localhost:8500/api/projects/board?sort=neglect' | jq '{count, stalled_count}'`
- [ ] When one does fire, ADR-0064 §2 says the build instruction is
      [guides/alfred-projects-page.md](../guides/alfred-projects-page.md)
      as written — "good and should be followed rather than redesigned".
      The `sysadmin_name` column on `trackables.Project` belongs to *that*
      triggered ADR, not to this row and not to ADR-0064
- [ ] The boundary survives either way and is now recorded on both sides:
      sysadmin stays read-only, the write happens in Alfred pulling, and
      the board is never written into `trackables.projects` — a curated
      list of life projects against every directory on disk carrying a
      marker (§3 here, ADR-0064 §3 there)

**One premise of the decline has since expired, and it fires nothing.**
ADR-0064 §3 declines to design against `GET /api/projects/next` because
"it returns 404 today" and its ranking policy is "undecided by its own
author". Session 29 shipped it on 2026-08-10: it returns 200, and the
ranking (stuckness in days, tie-broken by the most recent commit) is
decided, documented and argued. That removes a *stated reason* without
touching either *trigger*, and the distinction is the whole discipline —
a deferral with countable triggers is re-opened by the count, not by an
argument. Recorded here so the next reader of ADR-0064 does not have to
re-derive that the endpoint now exists.

[adr64]: file:///home/gaddi/projects/Alfred/docs/adr/0064-estate-board-consumption.md

### Session 31: Idle nudges — a commitment, not hygiene ✅ 2026-08-11

- [x] Distinct from the staleness score, which asks "is this repo tidy".
      This asks "**you have a stated next action and have not touched it in
      N days**" — a broken commitment, not a dirty directory. The score is
      never consulted: `venture-assistant` scores 100 and can still be sat
      on the same action for a fortnight
- [x] Rides plumbing that already exists: severity thresholds, DND windows,
      desktop notifications, the tray. No new delivery path — and **no new
      endpoint**, so the daemon needs no restart; the organiser is a oneshot
      timer that picks this up on its next run
- [x] Only for `active` projects with a non-null `next_action`. Eligibility
      was **not re-implemented** — it was extracted out of
      `GET /api/projects/next` into `next_action.eligible_candidates`, which
      both now call. Two copies of "what counts as a commitment" drift in
      the direction nobody notices: the endpoint stops offering a project
      while the nudge goes on reminding you about it
- [x] Threshold per project (`idle_nudge_days` in `.project.yaml`, beside
      `alert_threshold`), defaulting globally to **7 days**

**Decisions taken, with what was rejected:**

- **7 days, quiet; 14 days, loud.** The live estate turns its next actions
  over in 1–4 days, so 7 fires on nothing today and that is the intended
  shape — the threshold is "long enough that standing still is a fact".
  5 was rejected as within normal turnover; 14-as-first-rung was rejected
  because a feature that can never be observed firing cannot be trusted
- **The `info` rung is silent on this host and that is deliberate**, but
  not for the reason first written down: the gate is
  `tray.notify_min_severity`, **not** `notifications.desktop.min_severity`,
  which is parsed by `DesktopNotificationsConfig` and read by nothing.
  Filed as `SNAG-CFG-001`; three comments named the wrong knob before the
  grep was run
- **Never `critical`.** Criticals break through DND by configuration
  (`notifications.dnd.allow_critical: true`), and waking someone at 02:00
  about a roadmap item is how a monitor gets muted wholesale
- **Escalation is a gap, not a multiplier.** A project that relaxes its own
  threshold to 21 days escalates at 28, not 42. The per-project knob moves
  when the clock starts, not how patient the escalation is
- **Raised once per open nudge, not once per scan.** `BaseAgent.raise_alert`
  inserts unconditionally — this is the mechanism behind the 1,664-row
  pile-up of `SNAG-PROJ-004` — and the organiser runs daily, so re-raising
  would write one row per day per stuck project. Escalation **resolves the
  quiet row and raises a loud one** rather than updating severity in place:
  the tray fingerprints on `"{severity}:{title}"`, so an in-place change
  keeps a fingerprint it has already suppressed and the escalation is never
  spoken
- **Resolution is set-based**, the inverse question `_resolve_recovered`
  already asks: the action moved, the project went dormant, the handoff was
  cleared, the repository was deleted — only the first is observable as an
  event, and a per-project loop leaves the rest open forever

**Verified 2026-08-11**, not assumed: a live organiser run over 25
repositories reported `nudges: {raised: 0, escalated: 0, resolved: 0}` —
correct, since all three eligible projects changed their next action that
morning. Because a clean run proves only that nothing crashed, the ladder
was then run over the **real** historical series for `sysadmin_assistant`
(the "Session 24: File organiser tiers" action, 9 scans across 2 days):
`streak_days` folded it to one run of 2 days, and the ladder produced
`info` / `warning` / no-nudge at the thresholds it should. The 9-scans-to-
2-days ratio is the argument for days over scans, live.

### Session 32: Start-versus-finish accounting ✅ (2026-08-11)

`GET /api/projects/momentum` ships. The reasoning lives in
[momentum.py](../../sysadmin/projects/momentum.py); what follows is what
was decided rather than what was built.

- [x] **The blocker named the wrong evidence and was already gone.** The
      recorded fix was "an append-only `docs/sessions/log.jsonl` written
      by the hook, **or** sysadmin recording handoff-date transitions per
      scan" — and the second had been true since 2026-08-06. Session 28
      writes `handoff_age_days` on every scan, so
      `scanned_at − handoff_age_days` reconstructs the date a handoff was
      written and a *change* in it between two scans is an observed
      session. The log existed sideways, in JSONB, and no new hook,
      writer or migration was needed
- [x] **A landing is matched by date window, not at the transition
      scan.** The obvious rule — "had a commit been made by the time the
      scanner saw the new handoff?" — was written first and refuted by
      the live series within the hour: the scan at `2026-08-10 09:06` saw
      this repository's new handoff while `last_commit_at` still read
      2026-08-08, because the handoff is written *before* the work is
      committed. That day's six commits arrived afterwards and a
      productive day was reported as dropped. Scan timing was deciding
      the answer, and no fixture with a tidy cadence would have shown it.
      A commit dated in `[session_date, next_session_date)` is now that
      session's output. Pinned by
      `test_a_commit_after_the_scan_still_counts_as_landed`
- [x] **Both landings are reported**, because they are different
      failures. `dropped_code` is a session that shipped no code;
      `dropped` is one that shipped *nothing at all*; `docs_only` is the
      gap. A session that wrote up what it decided is a materially better
      outcome than silence and must not be summed with it. No scanner
      change was needed for the second count: `findings['git']` is
      written only when a housekeeping commit was skipped (77 rows of
      3,635), and its absence means the newest commit *is* the newest
      code commit — so the fallback to `last_commit_at` is exact
- [x] **The observed period is the dated scans, not every scan.** Caught
      on the live run: this repo holds 198 snapshots back to 2026-05-13,
      of which 22 carry a roadmap block. Reporting the series as three
      months long invited dividing five sessions by ninety days
- [x] `handoff_date_source` is now recorded for the *chosen* handoff, not
      only the also-rans. An undated handoff falls back to mtime and a
      clone or checkout rewrites mtime, which would present a
      `git checkout` as a morning's work. Prospective only — every
      session observed before today reads `unverified`, and the count is
      hedged in the `reason` sentence rather than quietly asserted
- [x] The population is `ACTIVELY_SCORED` (`active` + `undeclared`),
      **borrowed** from the agent rather than restated — deliberately
      wider than `/api/projects/next`, which additionally requires a
      stated next action. A commitment needs someone to have written one
      down; a session that shipped nothing is a fact about a repository
      whether or not it has a plan
- [x] Couples to Session 31 as predicted — both answer "you said you
      would and didn't", from elapsed time and from attempts made

**Verified against the live estate, and it disagrees with the health
scores.** `alfred-glance` opened 2 sessions and landed nothing (last code
commit 2026-08-03); `venture-assistant` 3 sessions, 1 landed; this repo
5 sessions, 4 landed — the single drop is 2026-08-09, and `git log`
confirms zero commits that day. `Alfred` is 4 of 4. Suite 1776 → 1824.

### Follow-ups this session opened

- [ ] [SNAG-PROJ-013](snag_list.md) — ImbaBots' `HANDOFF.md` heading
      carries no ISO date, so the Stop hook will block its next
      code-changing session. **Deliberately left for that session to
      fix**: the hook demands *today's* date, so dating it on a day
      nobody worked there writes a handoff for a session that did not
      happen — a phantom transition, and therefore a phantom session in
      `/api/projects/momentum`. Close this when a dated ImbaBots handoff
      appears. **The snag was also filed with the wrong diagnosis
      first** ("commits without moving its handoff date") and corrected
      the same day by opening the repository: ImbaBots' last session
      updated its handoff in the same commit as the code, and its 0 is
      the baseline rule working, not a failure
- [ ] Re-read `/api/projects/momentum` after the next organiser run, when
      `handoff_date_source` starts arriving. Every session is currently
      `unverified` by absence of the field, which is honest but makes the
      hedge unconditional and therefore unreadable
- [ ] No consumer renders this yet. It is a `GET` with a `reason`
      sentence built for a one-line surface; alfred-glance is the
      obvious reader, and Session 30's fate says to ask before assuming

### Session 33: Seam drift detection

Requested 2026-08-06. Found by checking rather than assuming: Alfred's
consumer fixture was **two sections behind** the same day it was captured,
with its contract test green the whole time.

- [ ] **Producer publishes the sample.** A test here regenerates
      `docs/contracts/briefing_preview.sample.json` from
      `generate_briefing_data` and fails when it differs from the committed
      copy — so the sample cannot silently go stale, the same trick the
      schema-drift guard already uses for migrations
- [ ] **Detect a stale consumer.** sysadmin can read Alfred's fixture
      (`backend/tests/fixtures/briefing_producers/sysadmin_preview.json` —
      same disk) and raise a finding when its section set is a subset of
      what this service now serves. This catches drift *without waiting for
      anyone to commit*, which is the case that actually bites
- [ ] Consumer registry in config: which repo, which fixture path, which
      producer endpoint. Two entries today; the point is that adding a
      third consumer is a config line, not code
- [ ] **Do not** build a shared contract package or a monorepo. Three repos
      in three languages, two seams — a shared library would couple three
      release cycles to solve what two files and a test already cover.
      Considered and rejected 2026-08-06
- [ ] Write the additive-only rule into
      [guides/monitorable-project.md](../guides/monitorable-project.md):
      sections and fields are added, never renumbered or removed; consumers
      render what arrives and ignore what they do not recognise. That
      tolerance is why the briefing went 5 → 7 sections with no breakage,
      and it does more work than any schema tooling

---

## Project-side consolidation (34–36) — from the 2026-08-07 capability audit

Consolidated from one pass over the project side and the design decisions taken
alongside it. **The ordering was not negotiable**: every defect in Session 34
corrupts output Alfred already consumes, and building the briefing envelope
(36) on top of wrong data just makes the wrong data better formatted. 35 is the
structural work 36 needs; 34 blocked both.

**34 and 35 are both done** (35 on 2026-08-08, 34 on 2026-08-10 — taken out of
order because 35 was already in flight). **36 is now unblocked**, and is the
only remaining member of this group.

### Session 34: Defect clearance — the project side ✅ (2026-08-10)

All twelve defects fixed, tested and verified against the live estate.
Write-ups archived under "Fixed Issues" in [snag_list.md](snag_list.md).

- [x] [SNAG-PROJ-001](snag_list.md) + [SNAG-PROJ-002](snag_list.md) — the
      cutoff moved into a new `sysadmin/projects/snapshots.py`. The audit said
      eight surfaces; grep found **nine** open-coded copies of the join across
      three packages, which is the tell that counting them by hand was never
      going to be reliable. `tests/test_project_snapshots_query.py` now fails
      if any module re-implements it
- [x] [SNAG-PROJ-003](snag_list.md) + [SNAG-PROJ-004](snag_list.md) —
      `_resolve_recovered` closes every health alert a scan did not re-raise,
      and migration 010 resolved the backlog. **1,664 rows resolved live**,
      matching the audit's count exactly
- [x] [SNAG-PROJ-005](snag_list.md) — the project review's prompt is
      figure-free by construction: scores → bands, deltas → directions,
      recommendation titles → `kind` phrases. Guard test ported from the disk
      review
- [x] [SNAG-PROJ-007](snag_list.md), [008](snag_list.md), [009](snag_list.md) —
      `*.md` dropped from the scan, `grep -w` for word boundaries, a real
      project-total cap that records its own truncation, and the
      recommendation names the markers it charged for
- [x] [SNAG-PROJ-006](snag_list.md), [010](snag_list.md), [011](snag_list.md),
      [012](snag_list.md) — `/stale` implements `days` against last-commit age
      with a `StaleProjectsResponse` contract; `project_reviews`,
      `disk_reviews` **and `unit_audits`** added to retention (migration 011);
      the `archived` description corrected in three places and its absolute
      alert suppression pinned by a test

**Follow-up this session revealed** — not part of the twelve:

**[SNAG-DB-001](snag_list.md) — the un-applied migration that blacked out
monitoring for 39 hours.** Fixed by applying it; the three detection gaps that
let it run that long are not, and are the real work. In order of value:

- [ ] **Fail startup on a schema-revision mismatch.** Nothing applies
      migrations here — no script, no `ExecStartPre`, no CI step — and nothing
      checks. `verify_connection` proves the database answers, not that it is
      the schema this code was written for. Compare `alembic_version` against
      the packaged head and refuse to start: serving against a schema the code
      does not match is worse than not starting, and this incident is the proof
- [ ] **Isolate the per-service health write.** `SysAdminAgent._execute` adds
      all nineteen services to one session and commits once, so a single
      rejected row aborted the whole transaction — one deliberately-unmonitored
      service cost the other eighteen their check for 39 hours. A savepoint per
      service, or a failed row recorded as `error` rather than aborting, would
      have turned a total blackout into one missing tile
- [ ] **Alert on consecutive agent-run failures.** The daemon logged
      `agent_run_failed` every five minutes for ~18 hours of uptime and nothing
      read it. `agent_runs` already records every failure with its status;
      nothing watches the column. Note the shape of the problem: the agent that
      raises alerts is the one that was failing, so this cannot live inside it
- [ ] **A live-database test path for the shared snapshot query.** The suite
      mocks every session, so the freshness filter's *effect* is unobservable
      — `tests/test_project_snapshots_query.py` asserts the predicate compiles
      into the statement, which is not the same as Postgres evaluating it.
      Worth one integration test against a real database

### Session 35: The inspection library and the `.project.yaml` manifest

**Groundwork landed unwired 2026-08-07** — `sysadmin/registry/` (discovery, id
derivation, manifest reader + validator, and the duplicate/unknown-id errors
that make an unrecognised id a load-time failure). 68 tests, ruff and mypy
clean, suite 1441 → 1509. **Nothing imports it yet**, so every checkbox below
stays open: the package is only worth its weight once `discover_projects` and
the three readers of `projects_root` are pointed at it, and until then it is a
second implementation of the thing it exists to deduplicate.

**Phase 6 complete 2026-08-08 — Session 35 is done.** The organiser has its
own oneshot unit and daily timer, ADR-0001 records the reasoning, and the spec
is marked superseded-in-part rather than rewritten. Two things deliberately
left for the operator: installing the timer (`systemctl --user enable --now
sysadmin-organiser.timer`), and the follow-on edit that stops the daemon
scanning as well — add the timer to services.yaml as `kind: timer` and set
`agents.project_organiser.enabled: false`. Neither is done here, because
declaring a unit in services.yaml before it is installed would have the monitor
correctly report it down.

**Phase 5 complete 2026-08-08.** `estate.json` is emitted on every organiser
run, versioned and written atomically, with `last_code_commit` separated from
`last_commit` and every downstream staleness figure derived from the former.
The ignore rule needed **two** patterns, not one — the roadmap-document fan-out
of 2026-08-06 is newer than the reorganisation snapshot and shadowed it.
Remaining for Phase 6: the organiser's own user timer, and the ADR.

**Phase 4 complete 2026-08-08.** projects.yaml is retired to
`docs/projects-registry-legacy.yaml` and nothing reads it. The registry removed
the last `units -> projects` import. Remaining: **delete the legacy file** once
its comments are all accounted for — the PA-worktrees note has no manifest to
move into, since the project was deleted, and that is the one piece of reasoning
the transfer cannot rehome.

**Phase 3 complete 2026-08-08.** services.yaml is wired: config.yaml holds no
per-service topology, startup validates project ids against the registry, and
`kind` decides every check. Behaviour deltas are recorded in STATUS.md. Still
open for Phase 4: `projects.yaml` becomes `docs/projects-registry-legacy.yaml`
and its comments move into `decisions:` blocks by hand, one project at a time.

**Phase 3, first half, landed 2026-08-08** — 16 `.project.yaml` manifests
(written by `scripts/migrate_registry.py`, pulled forward from Phase 4 because
Phase 3 cannot validate ids that do not exist yet), `services.yaml` with no
paths, `sysadmin/monitor/services.py`, and migration 009 adding `'skipped'`.
**Nothing reads services.yaml yet** — the wiring is the second half and it
changes monitoring behaviour: 8 http checks gain a unit assertion, 5 systemd
checks become `kind: timer`, `venture-chat-large` appears as a new declared-
but-skipped service, and the duplicate ingestion of `sysadmin.service` under
two log-source names has to be resolved one way or the other.

**Phase 2 landed 2026-08-08** — the module boundary. 62 modules moved into
`core/`, `monitor/`, `projects/`, `files/`, `units/` and `briefing/`, with
`tests/test_import_boundary.py` enforcing that monitor never imports projects.
Routes unchanged (55 → 55), suite 1509 → 1512. The registry is still unwired:
`units/agent.py` continues to import `discover_projects` from
`projects/agent.py`, which is one of the two edges Phase 1 exists to remove.

> **On the 2026-08-06 rejection**: the module split was refused that day on the
> grounds that it would duplicate `discover_projects`. It was re-briefed and
> landed as Phase 2, where the objection did not hold — `units/` imports the
> function from `projects/` rather than copying it. STATUS.md now records this
> as reversed rather than rejected; the remaining work is to remove that import
> in favour of the registry, which is Phase 3.

- [ ] **Extract the pure inspection layer** into a top-level package in this
      repository, installed as a path dependency: `utils/git.py`,
      `discover_projects`, `services/roadmap.py`, and the manifest reader
      below. No database, no config, no FastAPI, no scoring. Dependency is
      `gitpython` plus the grep binary
- [ ] Replace `from sysadmin.agents.project_organiser import discover_projects`
      in `agents/service_discovery.py` with the library import — resolving the
      drift the existing comment warns about, rather than relying on convention
- [ ] Promote `agents.project_organiser.projects_root` to a **top-level config
      key**. Three consumers read it (`service_discovery`, `routers/files` as a
      safety confinement rule, `branch_actions`) and only one is the organiser
- [ ] Define and implement the `.project.yaml` manifest — `schema`, `id`,
      `name`, `category`, `status`, `summary`, `supersedes`, `alert_threshold`,
      `decisions[]`. Reader **and** validator live in the library
- [ ] **Normalise project ids first**, or the current inconsistency is baked
      into twenty files: `sysadmin-service` points at `sysadmin_assistant`,
      `sports_analyser` at `SportsAnalyser`, `terrible` at what the docs call
      `TERRRIBLE`
- [ ] Write the migration generating `.project.yaml` from `projects.yaml` and
      emitting `services.yaml`. **Dry run by default**, and it must report both
      registry entries whose path does not exist and repos under the root the
      registry has never known about
- [ ] Transfer `projects.yaml`'s comments into `decisions:` blocks **by hand,
      one project at a time**. Do not automate it and do not delete the file —
      move it to `docs/projects-registry-legacy.yaml`
- [ ] Replace the runtime half of `projects.yaml` with `services.yaml`, keyed
      by project id and containing no paths: N services per project rather than
      one backend and one frontend, `kind` (`http`/`timer`/`oneshot`/`static`),
      and `monitor: false` with a **required reason**. Fold in the units
      currently exiled to `agents.sysadmin.services` in config.yaml
- [ ] Once ids are the join key, replace `ProjectsConfig._setting_for`'s
      three-way name matching with an id lookup, and make an unknown id a
      **load-time error**
- [ ] Add a CLI. There is no way to run a project scan without starting the web
      service, and the only console script is `sysadmin-tray`. With the library
      separated, `estate scan`, `estate check <path>` and `estate brief` are
      thin wrappers

**Two things considered and rejected 2026-08-07**, both worth re-reading before
anyone re-proposes them:

1. **Extracting the project side into its own repository or service.** Only one
   project endpoint needs anything from monitoring (`/managed`, joining
   `service_health`), while monitoring depends on the project side in three
   places — including a file-action safety rule. Migration 001 creates both
   sides' tables in one function, so this is a data migration wearing a
   directory move's clothes.
2. **The module split as originally briefed**, which asserted that monitoring
   must not import the project side. Backwards: the dependency runs that way
   deliberately, and enforcing the rule would mean duplicating
   `discover_projects` — the exact drift the existing comment warns against.
   The library replaces the rule.

Also rejected: **pre-commit hooks for document standards**. Most of the estate
is dormant, so blocking commits in repos nobody is working is pure friction,
and installing hooks across forty repos is its own maintenance problem.

### Session 36: The briefing publisher ✅ (2026-08-11)

Less work than expected, twice over. Half of it had already landed as Session
35 Phase 5 on 2026-08-08, and the two remaining builds were smaller than the
snag fixes they sat on top of.

- [x] Emit `estate.json` from the library's survey. This is the survey function
      serialised, not a separate feature — **done 2026-08-08 (Session 35 Phase
      5)**, `sysadmin/projects/estate.py`, `SCHEMA_VERSION = 1`
- [x] **Separate `last_commit` from `last_code_commit`**, with a configurable
      ignore rule (SHA list or commit-message pattern) seeded with the
      2026-08-04/05 "WIP snapshot before ~/projects reorganisation" commits.
      Every staleness figure downstream computes from `last_code_commit`.
      Supersedes the Session 28 follow-up describing the same weakness —
      **done 2026-08-08**; it needed **two** patterns, not one, because the
      roadmap-document fan-out of 2026-08-06 is newer than the reorganisation
      snapshot and shadowed it
- [x] Adopt the briefing envelope — `schema`, `source`, `generated`, `period`,
      `summary`, `alerts[]`, `facts{}`. Prose is what Alfred surfaces; `facts`
      is the deterministic input the prose was written from, **so briefings can
      be diffed and a drifting summary is detectable**
- [x] Generate the prose from the `facts` block rather than from raw code output
- [x] Write `estate.json` and any briefing artefact **atomically** — temporary
      path, then rename — **done 2026-08-08**, `tempfile` + `os.replace`
- [x] Confirm Alfred enforces staleness on `generated`. A publisher that has
      not run in three days still reads as current, which is worse than no
      briefing at all — **it does, and the check cannot fire.** See below

**The envelope is additive, and that was the whole delivery decision.**
Alfred's `adapt_sysadmin` reads `payload["sections"]` and returns one red
error section if it is absent, and reads `generated_at` into `produced_at`.
The spec named `generated` and no `sections`, so shipping it literally would
have turned Alfred's Infrastructure group red every morning. Additive is not
a compromise: the spec's own sentence — "prose is what Alfred surfaces,
`facts` is the deterministic input the prose was written from" — resolves it,
because **`sections` are the prose**. Alfred owns the section contract by its
ADR-0063; this service owns the envelope round it. Rejected: an
envelope-native second endpoint (two payloads where one gets updated is the
drift this repository keeps filing snags about) and a coordinated breaking
change (two repos in one sitting, digest red in between). No `generated` key
was added beside `generated_at` — two stamps holding one value is a fork
waiting to happen.

**Checkbox 6's answer is worse than the checkbox feared, and it is what
`facts` is for.** Alfred *does* enforce staleness: `_producer_timestamp`
carries `generated_at` into `produced_at` and `DigestSection.vue` flags a
12-hour gap. It is correctly implemented and **structurally incapable of
firing**, because this is a *pull* endpoint — `generated_at` is stamped when
the request is answered. It says when the phone was picked up, not how old
the data recited into it is. A service whose organiser died three days ago
serves a payload one second old. So every `facts` block carries its own
`measured_at`, `facts.stale_sources` names anything over 26 hours, and
`summary` says it in words. **First live run caught one**: `filesystem` last
measured 2026-08-06, corroborated by an open `file_organiser agent stalled`
alert in the same payload — two independent routes to the same fact, which
is the argument for the field.

**`period` is anchored to the schedule, not the last pull.** "Since the
previous briefing" has no anchor on a pulled endpoint: two consumers polling
would each shorten the other's window, and storing a row per pull turns the
route into a pull log and needs a migration. `schedules.briefing_hour`
already declares the cadence, so the window is the most recent 06:00
boundary — one meaning for every caller, no storage. `anchor: "schedule"` is
in the payload because the other reading is the one a consumer would
otherwise assume.

**`summary` is deterministic, and `facts` is a projection rather than a
copy.** No LLM in the 06:00 path: the two weekly reviews are narrated and
pay for it with a figure-free prompt, a deterministic facts prepend and a
markdown stripper, all of which a summary made only of numbers has nothing
to gain from — while a down llama-server would take the briefing with it.
`facts` carries counts and identifiers and never the rows the sections
render, because a facts block containing the whole payload cannot be diffed,
which is the only reason it exists. A test asserts every list in it holds
scalars.

Two defects fixed underneath, both in the functions the envelope wraps —
`SNAG-BRIEF-001` (26 project rows → 5, one query and one filter for both
sections) and `SNAG-BRIEF-002` (a bare `[:180]` slice → word boundary plus
`… (truncated)`, matching Alfred's own marker). The snag list's own note
made the ordering non-negotiable: *"building a briefing envelope on top of
wrong data only makes the wrong data better formatted."*

Also removed: the project snapshots were being **fetched twice** per
briefing, once per project section, differing only by an `ORDER BY` Python
does for free. Two reads of one table in one payload is two chances to
disagree.

### Deferred (34–36)

Not scheduled; recorded so they are not rediscovered as new.

- The **compliance checker** for required documents (CLAUDE.md, handoff, tasks,
  snags) and the relational checks carrying the real signal: handoff date
  against last code commit, unchecked task count against commit activity, snags
  opened versus closed. Held until the write discipline has produced data worth
  checking. Whatever ships must generalise `roadmap.is_placeholder` so an empty
  template counts as missing, tie requirements to declared `status`, and report
  as a **separate compliance result** rather than as score inputs
- `estate init`, scaffolding the template set into a repo without overwriting

### Open decisions (34–36)

- **Where project state ultimately lives** — an Alfred domain, or a standalone
  service Alfred reads from. The forcing function is the first requirement for
  *history* rather than a snapshot, since that needs a database. Until then the
  organiser stays stateless and file-based, and no project tables go into
  alembic
- **Whether the health score earns its place.** Roadmap state is the richest
  thing the scanner reads and is deliberately worth zero points, so the score is
  a directory-tidiness metric. Nothing has breached a threshold since
  2026-07-24, while the roadmap and next-action layer is what Alfred actually
  consumes. Worth settling before building anything further on top of the score
  — and it subsumes the Session 28 open decision on whether missing roadmap docs
  should cost points

---

## Session 37: The handoff pipeline — writer and reader ✅ (2026-08-10)

Raised by the estate owner: "the handoff hook isn't doing much in
venture-assistant." It was doing worse than nothing, on both ends.

**What was measured first** (15 repos, before any change): 5 carried
`docs/sessions/handoff.md` and **every one was hook output**. Exactly two
repos had ever held a handoff someone wrote — `venture-assistant`
(root `HANDOFF.md`, 8 of its 9 commits) and `SportsAnalyser` (abandoned
2026-03-07). Root `HANDOFF.md` existed in **1 of 15**, not "most".

- [x] **The writer.** `SessionEnd` **cannot block** — it is an
      observability event — so `generate-handoff.sh` could only emit what
      `git` already recorded. Retired (left on disk, unwired, with the
      reasoning). Replaced by `~/.claude/hooks/require-handoff.sh`, a
      **Stop** hook that blocks a session which changed code until
      `HANDOFF.md` carries today's date. Three independent loop guards
      (`stop_hook_active`, a per-session+repo marker file, exit 0 on every
      failure path); ten payload cases verified before wiring
- [x] **The reader.** `SNAG-ROADMAP-003` closed — four candidate paths,
      selection by `handoff_date` rather than tuple order, also-rans
      reported as `handoff_duplicates`. Live proof: `venture-assistant`
      now reads its 6 KB root handoff, `ImbaBots` its 141 KB
      `docs/handoff.md`; both had been serving the board an 850-byte stub
- [x] Stale references corrected in `recommendations.py` (its "No session
      handoff" advice described a hook that guaranteed the check could
      never fire), both `CLAUDE.md` files, `monitorable-project.md` (which
      said "don't hand-write handoffs" — now inverted), and
      `claude-preflight.sh`, whose extract was anchored on
      `## ⚠️ READ THIS FIRST` and `## In-Progress Tasks`: headings no
      handoff on this box has ever used, so it announced a handoff and
      then printed nothing

**The design lesson, worth keeping**: a file guaranteed to exist cannot
also be the file whose absence means something. The hook filled the slot
in every repo, so nothing ever signalled a real handoff was missing —
`venture-assistant` kept the habit only because its handoff lived at a
path the hook never touched.

### Follow-ups this session opened

- [x] Estate migration **done** (commit `0d56081`, 2026-08-10). Seven
      repos hold a handoff and every one holds exactly one: root
      `HANDOFF.md` in `Alfred`, `ImbaBots`, this repo,
      `apps/venture-assistant` and `apps/SportsAnalyser`, plus
      `docs/sessions/handoff.md` in the two archived `PersonalAssistant`
      repos. Re-checked at the top of Session 38 before building the
      reporter, which is what turned that work from a report on a live
      mess into a regression detector.
      **The first re-check was wrong** — it globbed `~/projects/*/`, which
      is 11 directories, while `discovery_depth: 2` makes the scanned
      population 25 across `~/projects/`, `apps/` and `archive/`. It
      reported `venture-assistant` and `SportsAnalyser` as having no
      handoff when both have a root one, contradicting a Session 37
      finding without that contradiction being spotted. Enumerate the
      estate the way the scanner does, or read `estate-map.md`; a
      top-level glob is not the estate
- [x] **The narrative history is now readable** (done 2026-08-10).
      `ProjectHistoryPoint` gained `next_action`, `next_action_source` and
      `next_action_changed`; `build_narrative_history` in
      [router.py](../../sysadmin/projects/router.py) builds them. The data
      was already being collected — Session 28 wrote the whole roadmap
      findings block into `project_snapshots` and the history list exposed
      the score only. **This unblocks Session 32**, whose recorded blocker
      was the SessionEnd hook overwriting its handoff instead of appending
      a log: the log exists, in JSONB, 90 days deep. Live proof — ImbaBots'
      `M5-T05` unchanged across 10 scans and 3 days
- [x] `handoff_duplicates` now has a reader (Session 38, 2026-08-10) — a
      zero-point `kind: "roadmap"` recommendation, so it reaches
      `/api/projects/{name}/recommendations`, `/api/projects/actions` and
      the weekly review without a new route. The field was widened from
      bare paths to `{path, date, date_source, days_older}` first: paths
      alone cannot separate migration debris (delete it) from a document
      that lost on tuple order (do not), and advice that conflated them
      would recreate SNAG-ROADMAP-003 from the deletion side. Nothing on
      the estate holds two handoffs any more, so it was verified against
      a constructed repository rather than live data
- [ ] `SNAG-ROADMAP-002` remains open and this session added evidence:
      `count_open_snags` reports 7 for 5 open snags in this very file

---

## Session 38: The unread handoff gets a reader ✅ (2026-08-10)

Session 37's `handoff_duplicates` reached a surface. Added to
`_roadmap_recommendations`, so it lands on
`/api/projects/{name}/recommendations`, `/api/projects/actions` and the
weekly review at once — no route, no contract change, no migration.

**The estate was re-measured before anything was built, and it changed
what was built.** Zero repos hold two handoffs; the migration cleared
them. This is therefore a regression detector, and it was verified against
a constructed two-handoff repository. The mtime branch is what fired — a
generated stub headed `# Session Handoff` carries no ISO date, so the
realistic case is the one where the age comes from the weaker clock.

### Follow-ups this session opened

- [ ] `handoff_path` is still read only inside the duplicate
      recommendation's detail line, so in a repo with one handoff — every
      repo on the estate today — it remains consumed by nothing. Putting
      it on `ProjectBoardEntry` would let any consumer rendering a
      handoff-sourced next action name the document it came from, which
      is the provenance argument Session 37 made. Deliberately deferred:
      it touches `contracts.py`, the board builder,
      `alfred-projects-page.md` and Alfred's expectations, and that is a
      sitting of its own rather than a rider on this one
- [ ] The recommendation is waived for non-active projects, inheriting
      `_roadmap_recommendations`' blanket rule. Defensible — nobody is
      misled by an unread handoff in a repo nobody opens — but it is an
      inherited default here rather than a decision taken for this item,
      and a dormant repo mid-migration is exactly where a stray handoff
      survives longest. Revisit if a dormant project is ever found
      holding two
- [ ] Nothing asserts the widened `handoff_duplicates` shape at the
      storage boundary. The recommendation tolerates both shapes and the
      scanner emits the new one, so a third shape would degrade quietly
      rather than fail — acceptable for advisory JSONB, worth a schema
      guard if a second consumer appears

---

## Session 39: Who watches the watchers

Raised by the estate owner on 2026-08-11, straight after `SNAG-AGENT-003`.
The framing question was "can we have someone who watches the watchers", and
the first thing worth recording is that **the watcher already existed and
worked**:

| Step | Component | Result |
|---|---|---|
| Detect | `self_monitor.build_self_report` | `stalled: true`, correct, at interval × 3 |
| Alert | `SysAdminAgent._check_agent_stalls` | **one** row, 2026-08-10 09:07 |
| Speak | tray, fingerprint `{severity}:{title}` | **one** toast |
| Escalate | — | nothing exists |

Detection is not the gap. `agent.py` skips raising when an unresolved alert
with that title is open — the same rule that stopped the 1,664-row pile-up,
and correct — but combined with the tray's fingerprint it means **the alarm
rings once, at the quietest severity, and is then silent while the fault
persists**. A warning that fires once and goes quiet is indistinguishable
from one that got fixed. Same shape as `SNAG-DB-001` and as the
`generated_at` hole Session 36 found: *absence of signal read as absence of
problem*.

**The owner's diagnosis, asked and answered rather than assumed: "I never
saw the toast."** Not ignored — away from the machine. That rules out
severity tuning and ranking, and it means escalating louder into D-Bus
repeats the miss on a longer timescale. Targets chosen: **an agent silently
stopping**, and **the daemon dying or wedging**. Explicitly not chosen: box
death (needs an off-box dead man's switch, which this estate has none of).

### What the box actually has — inventory, 2026-08-11

- **`notify-send` / D-Bus** — the tray plus `monitor/desktop.py`. The
  channel that was missed.
- **`zenity`** — installed, unused. Modal; blocks rather than notifies.
- **`claude-preflight.sh`, the briefing, journald** — passive surfaces the
  owner opens deliberately.
- **alfred-glance already renders pushed alerts** — `MqttEventReceiver.kt`
  subscribes to mosquitto (active) and `Notifier.kt` carries a dedicated
  `ALERTS_CHANNEL_ID` for "server-pushed alerts", separate from the daily
  nudge. **A working phone path that exists today.**
- **Off-box: nothing.** postfix/exim/opensmtpd/dma all inactive, no
  `.msmtprc`; `/usr/bin/mail` is s-nail with no MTA behind it. No ntfy, no
  healthchecks.io.
- **No `OnFailure=` anywhere** — user or system. Layer 2 is unbuilt, not
  partly built.

### Decisions taken 2026-08-11, before any code

1. **MQTT is promoted from Alfred's private bus to an estate bus.**
   [estate-map.md](../guides/estate-map.md) reserved this decision in
   writing — *"if a second consumer ever appears, decide then whether it is
   promoted"* — and a second **producer** has now appeared. The guide must
   be amended to record the promotion **and its terms** (who may publish,
   topic naming, LAN-only), not merely to delete the old sentence.
2. **`systemd WatchdogSec` for the wedge case**, over a polling timer. A
   true dead man's switch, native, no new unit — and the heartbeat proves
   the **event loop** is alive rather than merely the process.

### The two constraints found while checking the premises

Both were verified rather than assumed, and both change the shape of the
work:

- **alfred-glance's topic registry is closed by construction.**
  `RENDERERS` in `BusEvents.kt` is "the single source of truth" and
  `SUBSCRIBED_TOPICS` derives from `RENDERERS.keys`, so an unregistered
  topic cannot be subscribed to by design. Publishing therefore needs a
  **second repository, a Kotlin change and an Android release** — not a
  `mosquitto_pub` one-liner. Every existing topic is `alfred/events/<domain>/
  <event>`, so the namespace itself encodes the private-bus assumption:
  promotion has to decide between `alfred/events/sysadmin/…` (cheap,
  keeps a misleading prefix) and a neutral root (honest, touches seven
  existing constants and both ends).
- **`Restart=always` means the crash case is *already* invisible.**
  `sysadmin.service` is `Type=simple` with `Restart=always`, so the unit
  rarely enters `failed` and an `OnFailure=` hook would seldom fire. It
  needs `StartLimitBurst`/`StartLimitIntervalSec` to make a restart *loop*
  reach the failed state. This is the same silence-reads-as-health shape
  the session exists to fix, sitting in the unit file.

### The work

- [x] **Escalation ladder for stalled agents**, reusing
      `sysadmin/projects/nudges.py` rather than copying it — including the
      rule it already encodes: **resolve the quiet row and raise a louder
      one**, never update severity in place, because the tray fingerprints
      on `{severity}:{title}` and an in-place change stays suppressed —
      done 2026-08-11; the shared half had to move to `core` first, see
      below
- [ ] **Publish alerts to MQTT** at or above a configured severity. Decide
      the topic namespace first (above); amend estate-map.md with the terms
      of the promotion in the same change
- [ ] **Register the topic in alfred-glance** — `BusEvents.kt` renderer,
      `BusPayloads.kt` shape. Separate repo, separate session if it needs
      an Android release
- [ ] **`Type=notify` + `WatchdogSec=` on `sysadmin.service`**, with the
      ping issued from the async loop. **Risk to rehearse before enabling**:
      if `READY=1` is never sent, systemd treats startup as failed and kills
      the service — so the rollback must be written down before the unit is
      edited
- [x] **`StartLimitBurst` / `StartLimitIntervalSec`** so a restart loop
      reaches `failed`, then an `OnFailure=` unit that says so — done
      2026-08-11, `StartLimitBurst=5` / `StartLimitIntervalSec=600` plus
      `sysadmin-failed.service` → `scripts/notify-unit-failed.sh`.
      **Installed and verified on the live box the same day**, and the
      ladder proved itself in production on the stall that motivated it:
      the 2026-08-10 09:07 `warning` was resolved and a `critical` raised
      at 17:13 with `hours_since_first_alert: 32.1`
- [x] **A failure leaves state, not just a toast** — added the same day
      after the owner chose `agent='sysadmin'` over a sixth
      `chk_alert_agent` value. `sysadmin/core/unit_failure.py` writes a
      critical row through the **sync** engine (no event loop, no
      scheduler session, nothing subscribed — the application is dead by
      definition), with `details.source = systemd_onfailure` carrying the
      provenance `agent` cannot. **Paired with a resolve in the lifespan**,
      because the service starting *is* the recovery and nothing else can
      ever observe it; without that half it is an alert type that can only
      accumulate. Verified end to end against the live database
- [x] **Do not** build a second detector. Detection works; every item above
      is about a signal persisting until it is seen — held to; not one line
      of `self_monitor.py` changed

### Done 2026-08-11 (part 1 of the session)

**The ladder, and where it had to live.** `sysadmin/monitor` may not import
`sysadmin.projects` (`tests/test_import_boundary.py`), so "reuse nudges.py
rather than copy it" was not possible as stated. The shared half moved to
**`sysadmin/core/escalation.py`** — `SEVERITY_ORDER`, `Ladder`, `step_for`
— the same move `strip_markdown` made into `core/text.py` and for the same
reason. `nudges.py` now delegates to it; `severity_for` survives as a thin
wrapper because the *unit* (days) is what a reader of that module needs.

**The loud rung is `critical`, and the reason is not volume.**
`sysadmin_tray/notifications.py` sets `transient=effective == "info"` on a
first notification and `transient=False` only in `_maybe_escalate`, which
fires for `critical` alone. **`critical` is the only severity the tray
leaves on screen.** A `warning` toast expires whether or not anyone was in
the room — which is exactly the owner's reported failure, so the second
rung is about *persistence*, not loudness. This is the opposite of the rule
`nudges.py` encodes (a nudge never reaches `critical`) and the two
docstrings now point at each other so the difference reads as deliberate.

**The escalation clock runs from when the alarm rang, not from when the
stall began.** Both are computable; the alert row's `created_at` is right
for two reasons. It is the honest claim — "you were told yesterday and it
is still true", and the thing that failed was the telling. And anchoring to
the stall's own age would make **a daemon outage produce a wall of
criticals on restart**: while the service is down no agent runs, so the
first check back would escalate all five at once, charging the estate for
this application's downtime. `GET /api/services/reliability` already
encodes that rule as "a gap in the series never costs points".

**`escalate_after_hours: 24`, measured against the slowest agent, not the
fastest.** `file_organiser` and `service_discovery` run daily, so a stall of
theirs that is merely late recovers within one interval; a shorter gap
escalates faults that were about to clear themselves, and an alarm that
cries wolf stops being read. The knob cannot make *detection* faster —
that is `stall_grace_multiplier`, and the config docstring says so, because
that is the wrong knob someone will reach for.

**`StartLimit` risk, sized rather than assumed.** `Restart=always` with no
limit rides out a slow dependency, and this app does exit rather than
degrade when the database is absent (`verify_connection` raises inside the
lifespan). Measured before making the change: **`NRestarts=0` and zero
"Scheduled restart job" entries in 30 days of journal** — the retry has
never once fired on this box, so the resilience being traded away is
theoretical while the silence it causes is not. The window is 600s rather
than 300s to leave the headroom anyway, and the rollback (including the
`systemctl reset-failed` that is easy to forget) is written into the unit
file rather than into a session note.

`tests/test_systemd_units.py` pins the pair together: `Restart=always`
**with** a burst limit, a window that outlasts `burst × RestartSec`, an
`OnFailure=` naming a unit that exists, a handler with no `OnFailure=` of
its own, and `--expire-time=0` in the script. Installing either half alone
accomplishes nothing, which is the shape of half-change this repository has
shipped before (a retention row with no `TABLE_TIMESTAMP_MAP` entry).

### Still open, and what the two constraints did to the plan

- [ ] **MQTT publishing is blocked on an Alfred-side change, not on a
      topic name.** The premise checked in the scoping session was
      alfred-glance's closed renderer registry. That is real but secondary:
      mosquitto here is `allow_anonymous false` with the **dynamic-security
      plugin**, whose schema Alfred owns
      (`Alfred/backend/alfred/events/dynsec.py`), and
      **`dynsec.reconcile()` deletes every client that is not Alfred's
      admin, not Alfred's publisher, and not a live device token**. A
      `sysadmin-publisher` added by hand with `mosquitto_ctrl` therefore
      works until Alfred next restarts and is then deleted — best-effort,
      logged at `info`, no alert. For an alerting path that is the worst
      available failure mode, and it is this session's own bug reinstalled
      in the fix. Decided 2026-08-11: **Alfred provisions a protected
      non-device publisher for sysadmin**, in its code.
- [ ] **The neutral root costs a dynsec change too.** Both roles are
      scoped to `_TOPIC_FILTER = alfred/events/#`, so `estate/…` is
      **denied by the broker** until Alfred's roles gain a widened or
      second filter. The namespace decision (neutral root, taken
      2026-08-11) is therefore not "seven constants and both ends" as
      scoped — it is that plus the broker's access control. Terms recorded
      in [estate-map.md](../guides/estate-map.md).
- [ ] **Persist an `OnFailure=` firing where the tray can see it.** The
      handler notifies and writes to journald; neither survives as an
      *alert row*, so a failure that happened while nobody was logged in is
      invisible to `GET /api/sysadmin/alerts` afterwards. Blocked on a
      decision rather than on work: `alerts.agent` has a `chk_alert_agent`
      CHECK constraint, so an external writer either lies about provenance
      (`agent='sysadmin'`, when the whole point is that the sysadmin
      service was dead) or needs a migration adding a value for it.
- [ ] **Off-box remains the known gap.** Listeners are `127.0.0.1` and
      `192.168.1.2` only, so nothing built this session survives the box
      being off. Recorded, not closed.

### Rejected, and why

- **A watchdog agent inside the daemon.** A watcher that shares fate with
  what it watches is not a watcher — and the failing component here was
  never the detector.
- **Escalating louder into D-Bus alone.** The owner was away from the
  machine; a louder alarm in an empty room is the same miss with more
  volume.
- **Email.** No MTA is configured and installing one to carry alerts is a
  new service to monitor, which is the problem recursing.
- **Off-box (ntfy / healthchecks.io)** — the only thing that survives the
  box being off, and deliberately deferred: it was not among the failures
  the owner chose, and it adds an external dependency and an account.
  Record it as the known gap rather than pretending the ladder closes it.

---

## Session 40: MOVED to ~/projects/estate-manager

The estate manager repository was created on 2026-08-11 and this session
became **its Session 1**. The work list, the two follow-on sessions and the
measurements behind them now live in
`~/projects/estate-manager/docs/roadmap/tasks.md`.

**A pointer, not a copy** — the rule that session's own scope insists on,
applied to itself. Two roadmaps describing one piece of work would disagree
inside a week, and this repository has filed three snags about exactly that.

What stays here, because it is about *this* service rather than about the
estate:

- **[ADR-0002](../adr/0002-estate-manager.md)** still lives here and is
  still the founding record. Moving it is a task in the new repository's
  Session 1, together with deciding what cross-repo ADR numbering looks
  like — it currently sits in this repository's sequence.
- **sysadmin does not move.** It stays the monitor, keeps its own broker
  credential and publishes alerts directly, and will watch the estate
  manager's units like any other. The monitor must not own the things it
  monitors, and an alerting path with a live dependency on another service
  is not an alerting path.
- **Port 8400 is claimed** for estate-manager in
  [monitorable-project.md](../guides/monitorable-project.md), which is
  still the registry until Session 1 moves it.
- **The four cross-repo guides are still here** and
  `~/.claude/CLAUDE.md` still points at two of them. Deliberate: a global
  pointer at a repository that has not been filled yet would silently stop
  the monitorable-project contract being read by every new-project session.

---

## Backlog

**Carried-forward follow-ups** — small items noted by the sessions that
deferred them. Hoisted here 2026-08-05 when Sessions 10–23 were archived,
so nothing was buried with them.

Notifications (from SNAG-CFG-001, 2026-08-11):
- [ ] **The daemon announces an outage's start and never its end.**
      `sysadmin/monitor/desktop.py` notifies on `alert.raised` only,
      because `alert.resolved` carries a *match pattern* rather than a
      subject — `BaseAgent.resolve_alerts` publishes
      `{"agent", "match", "count"}`, and the project organiser's `match`
      is `"Project % health critical"`. A recovery toast needs the
      resolve events to name what recovered, which means changing the
      three resolve paths, not the notifier
- [ ] **The presence signal cannot tell the tray from any other client.**
      Any GET of `/api/sysadmin/alerts` counts as "somebody is watching",
      including a `curl`. It errs towards silence, which is the safe
      direction and the pre-existing behaviour, but a tray that
      identified itself (a header set in `sysadmin_tray/client.py`) would
      be exact. Deferred because an older tray build would then go
      unrecognised and both would toast — the duplicate this design
      exists to prevent
- [ ] **The tray re-announces the open alert set on every start**, because
      `NotificationPolicy`'s fingerprint state is in-memory. Now that
      `sysadmin-tray.service` starts at login this happens every login.
      Measured 2026-08-11 against the live set — six distinct
      fingerprints fold into **one** coalesced summary and the next poll
      is silent, so it is currently a feature ("here is what is
      outstanding") rather than noise. It stops being one if the distinct
      count ever drops below `coalesce_threshold` while the volume stays
      high. No action while the numbers hold; recorded so the next
      "why did it just announce everything?" is a lookup, not an
      investigation
- [ ] **Page-1 churn can re-notify a standing alert.** The tray fetches
      the newest 50 unresolved alerts; with 547,814 of them, a burst of
      new rows pushes an older title off the page, `_close_inactive`
      closes its episode, and the title notifies again as a *new* episode
      when it reappears. Harmless at the current rate (one alert in 90
      minutes) and unbounded when the log aggregator is noisy — which
      makes it a second consequence of SNAG-AGENT-002 rather than a tray
      defect. A fix belongs on the volume, not on `limit=50`
- [ ] **547,814 unresolved `Log error: kernel` rows** were found in the
      table while measuring notification volume. That is SNAG-AGENT-002's
      damage rather than a new defect, and the notifier's incident gate
      makes it harmless to *notifications*, but nothing has ever purged
      or resolved them — retention purges resolved rows only

Tray / UI:
- Wire Session 18's file-action endpoints (`/api/files/organise`,
  `clean/duplicates`, `clean/downloads`) into Session 19's Files tab — the
  tab is deliberately read-only because the endpoints landed in a parallel
  session. Each view already holds its parsed rows, so the work is
  per-row/selection buttons plus a confirmation dialog reusing
  `quick_wins.clean_confirmation_text`'s pattern. Remove the
  "display-only until the file-action endpoints land" note at the same time
- Tray consumes Session 17's SSE stream (`GET /api/sysadmin/events`)
  instead of polling `/health`. Note from the live run: the log aggregator
  currently raises one alert *per* error line (SNAG-AGENT-002, fixed by
  Session 27), so a poll can emit dozens of `alert.raised` events — the
  consumer must coalesce. Once this lands, a file-organiser `agent.run`
  event should refresh the Files tab instead of the user pressing Rescan
- Projects tab could show the branch-prune dry-run manifest behind a
  confirmation dialog (name the branches, state the count, say what is
  recoverable via `git branch <name> <sha>`). Contract is already shared,
  so this is presentation only
- Visual sanity-check of the Files tab and trend charts on a real Plasma
  session — built and screenshotted headless only

Backend:
- `response_model=` on the `/api/files/*` GET routes (contracts exist and
  are parse-side enforced; the routes aren't annotated yet)
- `git remote prune origin` for gone-upstream remote-tracking refs — read
  but never deleted by Session 20; a separate, safer action
- A repo-wide "branch report" GET (no auth, no mutation) so the score can
  explain *which* branches cost it points, not just the count already in
  `findings.stale_branches`
- Config loader could warn when a managed project's `path` doesn't exist —
  would have caught SNAG-CONF-001 immediately (also in ideas.md and
  snag_list.md)

Config / ops:
- Set a real `api.auth_token` in the local config.yaml — auth ships
  disabled because config.yaml is committed
- PA-auto's 224 branches will take 12 confirmed calls at the current
  `max_deletions: 20`; raising it for a one-off sweep is a config change,
  deliberately not a request parameter

---

## Maintenance

_Not numbered sessions — config/upkeep work that doesn't warrant one.
Completed maintenance is in the archive._

### ⚠️ Pending: restart the live daemon

`sysadmin.service` reads config at startup and is a **system** unit, so:

```bash
sudo systemctl restart sysadmin.service
```

Owed since the 2026-07-24 daemon fixes and the Alfred config migration, and
again since 2026-08-05's SportsAnalyser wiring — the running process
predates all of it.

**Measured cost, 2026-08-10 (Session 38):** the newest stored snapshot
(09:06 today) carries neither `handoff_path` nor `handoff_duplicates`, so
the whole Session 37 reader is absent from the database and every surface
built on it reads `None`. This debt is no longer only theoretical — two
sessions of project-side work are invisible until the restart happens.

### ⚠️ Pending: enable the SportsAnalyser backend unit

`sportsanalyser-backend.service` is `disabled` and only runs because the
frontend `Requires=` it — that survives exactly until the frontend is
stopped or its unit changes:

```bash
systemctl --user enable sportsanalyser-backend.service
```

---

## Archive

- Sessions 10–23, 2026-07-24 maintenance, and SNAGs fixed in that period →
  [archive/completed_2026-08-05.md](archive/completed_2026-08-05.md)
- Sessions 1–9 (full service + tray app) →
  [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md)
