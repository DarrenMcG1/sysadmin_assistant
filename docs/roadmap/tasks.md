# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-06

---

## Active Sessions

_Sessions 24–27 promoted from [ideas.md](ideas.md) on 2026-08-05. They are
**independent of each other** — take them in any order. The order below is
the priority agreed when they were captured, but **Session 26 is the one
directly asked for** (the tedium of hand-registering every new service) and
is the smallest, so it is a reasonable one to pull forward._

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

### Session 26: Service discovery — the unmonitored-unit detector

**Directly requested 2026-08-05**: hand-registering each new project's
systemd units is tedious and rots silently. The contract this enforces is
written up in [guides/monitorable-project.md](../guides/monitorable-project.md);
this session is its mechanical backstop.

- [ ] Cross-reference discovered projects against installed units —
      `~/.config/systemd/user/*.{service,timer}` and
      `/etc/systemd/system/*.service` — and raise findings **both ways**
- [ ] **Unmonitored unit**: a unit maps to a live project but projects.yaml
      doesn't wire it. Match in preference order: the unit's
      `WorkingDirectory`/`ExecStart` path under the project dir (robust),
      then normalised name-prefix (strip `-_`, case-fold, so
      `sportsanalyser-*` → `SportsAnalyser`/`sports_analyser`). Path-first
      matters because the naming is inconsistent in exactly the way that
      breaks heuristics
- [ ] **Orphaned unit**: a unit whose project is archived or gone — eight
      dead `personal-assistant-*` / `personalassistant-*` units are
      installed right now
- [ ] Tier 2 recommendation carries a **ready-to-paste projects.yaml
      snippet**, with `user: true` for user units and the oneshot→timer
      rule applied (a `Type=oneshot` service means monitor its `.timer`,
      and the timer goes in config.yaml since projects.yaml only models
      backend/frontend)
- [ ] **Advice-only — never auto-edit projects.yaml.** It is hand-curated
      with comments that carry the reasoning; an executor rewriting it
      would destroy them
- [ ] Distro/template units (`@.service`, `dbus-org.*`) filtered out by the
      path-match requirement
- [ ] Known targets to validate against on the day: `garmin-sync`,
      `deadlock-api-ingest`, `ticktick-sync`, `offline-agents-dashboard`
      (all uncovered), plus the eight orphaned PA units.
      `sportsanalyser-*` was the motivating case and was wired by hand
      2026-08-05, so it should now come back **clean** — a good negative test

**Port-registry reconciliation** (added 2026-08-06, same session, same
scan): the unit sweep already parses every `ExecStart`, so the ports are
free to extract. Three findings, cheapest first:

- [ ] **Unregistered listener** — a port held by a project's process that
      has no row in the registry table in
      [guides/monitorable-project.md](../guides/monitorable-project.md).
      Source of truth is `ss -ltnp` joined to the unit by PID/cgroup, not
      the `ExecStart` string alone: a port can be set in a config file, an
      `Environment=` line or a default the flag never mentions
- [ ] **Contended default** — a project listening on a well-known default
      (8080, 3000, 5000, 8888, 9000). Advisory, not an error: it did not
      collide *yet*. venture-assistant on 8080 is the live example and the
      thing that prompted this
- [ ] **Collision / near-miss** — two registry rows claiming one port, or
      a unit whose configured port is already held by a different cgroup.
      This is the only one worth a warning alert; the failure is
      asymmetric (the loser fails, the winner looks fine)
- [ ] Parsing the registry table out of a markdown doc is the fragile part.
      Decide on the day whether to (a) parse it, (b) move the allocation
      into `config.yaml` with the doc rendered from it, or (c) infer
      "registered" from projects.yaml `port:` fields and treat the table as
      documentation only. (c) is cheapest and covers backends; it misses
      sidecars like the three llama-servers, which is exactly the gap

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
