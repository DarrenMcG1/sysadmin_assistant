# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-05

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

The closest analogue to the project-manager work: Tier 1 already exists, so
this is mostly Tiers 2 and 3. The currency is **reclaimable bytes**, which
is more honest than project points because it is directly measurable.

- [ ] **Tier 2** — new pure `sysadmin/services/file_recommendations.py`:
      audit findings (duplicates, misplaced, large files, stale caches,
      empty dirs) → ranked advice where `points` is bytes reclaimed.
      Each item's `action` points at the existing Session 18 dry-run
      executor: `/api/files/organise`, `/clean/duplicates`,
      `/clean/downloads`, `/clean/stale-caches`
- [ ] `GET /api/files/actions` mirroring `GET /api/projects/actions` —
      portfolio-wide top wins, **risk-first**: a disk-threshold crossing
      inside 30 days outranks raw megabytes, the way `no_remote` outranks
      score arithmetic in Session 22
- [ ] **Promote the forecast maths out of the tray** — the least-squares
      fit currently lives in `sysadmin_tray/forecast.py` (Qt-free already,
      so this is a move plus an import swap). The review, the briefing and
      any future web UI all need it; today only the tray has it
- [ ] **Tier 3** — weekly disk review from `file_trends` week-on-week
      deltas plus the threshold-crossing forecast. Same shape as
      `project_review.py`: deterministic "what grew / what shrank",
      LLM writes only "where the mess is coming from", digest fallback
- [ ] Contracts + tray re-exports; tests alongside (`tmp_path` trees only,
      never the real home directory — the Session 18 rule)

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
