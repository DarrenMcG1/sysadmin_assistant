# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-07

---

## Active Sessions

_Sessions 24–27 promoted from [ideas.md](ideas.md) on 2026-08-05. They are
**independent of each other** — take them in any order. 24 and 26 are done;
**25 (service reliability scoring) and 27 (log aggregator tiers) remain**,
plus 26b (port-registry reconciliation), split out of 26 on 2026-08-07._

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

- [ ] **Tier 1** — per-service reliability score: uptime %, flap count,
      mean time between alerts, restart frequency. Use the Session 21
      status-awareness trick: a `mute: true` or expected-down service
      **waives** deductions rather than being excluded, so the number
      still means "how reliable is this service"
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
      is why `docs/sessions/` sat empty for months
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

### Session 29: The one-thing endpoint

- [ ] `GET /api/projects/next` — **one** project, one action, one sentence
      of why it is that one. Not a filtered board: a different object, with
      a `reason` field the consumer must render
- [ ] **The open design question, and it is the whole feature: what decides
      when two projects both have a live next action?** Longest-idle is the
      obvious rule and probably the wrong one — it optimises for guilt.
      "Smallest next step" or "nearest to finishing" optimise for momentum,
      which is the stated goal. Needs a decision before code
- [ ] Honour `?exclude=` so a deferred suggestion can be skipped without
      re-rolling the same answer
- [ ] Contract-pinned; feeds alfred-glance, whose whole premise is glance
      then act
- [ ] Deliberately **not** in scope: a resume/deep-link command. Considered
      and dropped 2026-08-06

### Session 30: Next action → an Alfred work item

- [ ] Alfred creates one `work_item` per active project from
      `/api/projects/next` (or the board), refreshed daily, linked by the
      nullable `sysadmin_name` on `trackables.Project`
- [ ] **The write happens in Alfred, pulling** — exactly as it already does
      for `/api/sysadmin/briefing/preview`. sysadmin stays read-only, so the
      "report only" restriction survives intact rather than being revisited
- [ ] Do **not** insert sysadmin's projects into `trackables.projects` —
      that table is curated life projects (warhammer, birdfeeder). See
      [guides/alfred-projects-page.md](../guides/alfred-projects-page.md) §3
- [ ] Work in Alfred's repo; nothing here blocks it beyond Session 29

### Session 31: Idle nudges — a commitment, not hygiene

- [ ] Distinct from the staleness score, which asks "is this repo tidy".
      This asks "**you have a stated next action and have not touched it in
      N days**" — a broken commitment, not a dirty directory
- [ ] Rides plumbing that already exists: severity thresholds, DND windows,
      desktop notifications, the tray. No new delivery path
- [ ] Only for `active` projects with a non-null `next_action`. A dormant
      project has made its decision; a project with no next action has
      nothing to be reminded of
- [ ] Threshold per project, defaulting globally. Getting this wrong makes
      the tray a nag, which trains the user to ignore it — start long

### Session 32: Start-versus-finish accounting

- [ ] The one signal nothing else here can produce: **sessions that start
      and land nothing**. The SessionEnd hook records that a session
      happened; git records whether anything shipped. A project
      accumulating sessions with no commits between them is the
      start-and-drop pattern made measurable
- [ ] **Blocker to solve first:** the hook *overwrites*
      `docs/sessions/handoff.md`, so session history does not survive. Needs
      either an append-only `docs/sessions/log.jsonl` written by the hook,
      or sysadmin recording handoff-date transitions per scan. The former is
      cheaper and keeps the record with the repo
- [ ] Couples to Session 31 — both answer "you said you would and didn't"
      from different evidence (elapsed time vs. attempts made). Worth
      taking together if 31 lands first

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

## Backlog

**Carried-forward follow-ups** — small items noted by the sessions that
deferred them. Hoisted here 2026-08-05 when Sessions 10–23 were archived,
so nothing was buried with them.

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
