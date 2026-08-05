# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-08-05

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### Repeat the project-manager tier pattern in other domains (2026-08-05)

Sessions 21–23 established a three-tier ladder that generalises: **Tier 1**
measure deeply (structured findings, a score whose deductions are individually
attributable), **Tier 2** advice as data (pure module, each recommendation
mirrors exactly one finding with an exact payoff, points at safe dry-run
executors), **Tier 3** periodic LLM narrative (deterministic facts and deltas
computed in code, bounded prompt, model writes qualitative sections only,
digest fallback when inference is unavailable, persisted with inputs in
`stats`, endpoint + cron + briefing section). Session 23's runtime lessons
carry over: commit the read transaction before calling the LLM, and never let
the 3B model produce numbers.

Four candidates, in rough priority order:

1. **File organiser tiers — disk instead of portfolio.** Strongest analogue;
   most machinery exists. Tier 1 is done (duplicates/misplaced/large/stale
   caches + `file_trends`). Tier 2: a pure `file_recommendations.py` where
   `points` = **reclaimable bytes**, each item pointing at the Session 18
   dry-run executors (`/api/files/organise`, `/clean/duplicates`,
   `/clean/downloads`, `/clean/stale-caches`), plus a portfolio-style
   `GET /api/files/actions` — risk-first (disk-threshold forecast crossing
   outranks raw MB, like `no_remote`). Tier 3: weekly disk review from
   `file_trends` deltas + the threshold-crossing forecast — which means
   promoting the least-squares fit from `sysadmin_tray/forecast.py` into a
   backend service so review, briefing and any web UI share it. The detector
   ideas below (multi-venv clutter, name-similarity duplicates) become new
   Tier 1 findings that automatically surface as recommendations.

2. **Service reliability scoring — the SysAdmin agent's world.** Nothing
   scores *services*, yet the history is in the DB (`health_checks` streaks,
   `alerts`, `resource_snapshots`, `agent_runs`). Tier 1: per-service
   reliability score (uptime %, flap count, MTBA, restart frequency) with the
   status-awareness trick — muted/expected-down services waive deductions
   rather than being excluded. Tier 2: recommendations tied to alert-history
   facts ("llama-server flapped 6× this week", "alfred-evaluate.timer
   inactive 3 days — schedule has stopped"); few safe executors exist beyond
   service restart, so most items name config changes (Session 22's fallback
   convention). Tier 3: weekly system health review — flappiest services,
   alert volume delta, anomaly summary, resource trend direction — beside the
   project review in Monday's briefing, reusing the `project_reviews` design.

3. **Service discovery — unmonitored-unit detector (project manager).**
   Adding each new project's systemd units to projects.yaml by hand is
   tedious and rots silently (the broken-path PA entries proved it). The
   organiser should cross-reference discovered projects against installed
   units — `~/.config/systemd/user/*.{service,timer}` plus
   `/etc/systemd/system/*.service` — and raise findings both ways:

   - **Unmonitored unit**: a unit maps to a live project but projects.yaml
     doesn't wire it. Matching signal in preference order: the unit file's
     `WorkingDirectory`/`ExecStart` path under the project dir (robust),
     then normalised name-prefix match (strip `-_`, case-fold:
     `sportsanalyser-*` → `SportsAnalyser`/`sports_analyser`). Tier 2
     recommendation carries a **ready-to-paste projects.yaml snippet**
     (with `user: true` for user units, and the alfred-evaluate lesson
     baked in: a `Type=oneshot` service means monitor its *timer*).
     Grounded 2026-08-05: `sportsanalyser-{backend,frontend,pipeline}`
     units exist but the yaml entry has URL-only checks — unmonitored
     today; `garmin-sync`, `deadlock-api-ingest`, `ticktick-sync`,
     `offline-agents-dashboard` have no entry at all. Future projects
     (e.g. venture-assistant) get caught automatically on first
     `systemctl enable`.
   - **Orphaned unit**: a unit whose project is archived or gone — six
     dead `personal-assistant-*` user units and two `personalassistant-*`
     system units are still installed now.

   Advice-only, no auto-editing: projects.yaml is hand-curated with
   comments, so the recommendation surfaces the snippet rather than an
   executor writing the file. Distro/template units (`@.service`,
   `dbus-org.*`) filtered by the path-match requirement.

4. **Log aggregator tiers — thinnest, take with SNAG-AGENT-002.** Tier 3 is
   half-done (overnight LLM log summary in the briefing). Missing substance:
   per-source error-rate trends week-on-week, "new error signatures this week
   vs last", recommendations like "this warning appeared 400× — add to
   known-noise or fix". Error-signature fingerprinting is also the fix for
   SNAG-AGENT-002 (one alert per error line), so this is best done as part of
   that snag rather than standalone.

### Housekeeping follow-ups from the 2026-08-04 ~/projects reorganisation

The Tier 2 recommendations engine landed 2026-08-04 (Session 22:
`GET /api/projects/{name}/recommendations` + `GET /api/projects/actions`)
and now surfaces **missing remotes natively** — the six unbacked repos
appear as `risk` items in `/api/projects/actions` after every scan, so
that follow-up no longer needs a doc entry. The rest stay parked because
the scanner has no finding for them yet; each is really a *detector idea*:

- **apps/oanIt vs apps/habitTracker** — habitTracker contains
  `oanIt_Frontend`/`oanIt_backend` dirs; both trees have real content.
  Needs a manual look. (Detector idea: name-similarity duplicate flag.)
- **apps/BudgetApp venv clutter** — carries both `.venv` and `.venv1`
  (~290M, recreatable). (Detector idea: multiple/oversized venvs as a
  `hygiene` finding — the file organiser already hunts stale caches.)
- **Config loader could warn on nonexistent managed paths** — would have
  caught SNAG-CONF-001 immediately (also noted in snag_list.md).

### Rebuild the sysadmin web UI inside Alfred's frontend

The web dashboard was built in PersonalAssistant and died with it (2026-07-24);
the PyQt6 tray is currently the only UI. Alfred — PA's replacement — ships a
**Nuxt frontend on :3100**, which is the obvious host for a rebuild.

Nothing on the backend needs to change to make this possible:

- **The API is unchanged.** The same 25+ endpoints the PA dashboard consumed are
  still served on :8500, and their response shapes are now pinned by
  `sysadmin/contracts.py` (the tray's contracts) rather than hand-copied — so a
  web client and the tray can't drift apart the way they used to.
- **`GET /api/sysadmin/events`** (SSE, Session 17) means a browser client can
  subscribe with `EventSource` instead of polling, which the tray still doesn't
  do — the web UI could be the first real consumer.
- **Mutating routes are bearer-auth protected** (Session 12: service actions,
  alert ack, DND, scans, file/branch actions). A browser UI therefore needs the
  `api.auth_token` — and since it can't hold a shared secret safely, the sane
  shape is for Alfred's *backend* to proxy the mutating calls and hold the token
  server-side, leaving the browser to hit read-only GETs directly. Worth
  deciding before any UI work starts, not after.
- **CORS** already lists `http://localhost:3100` / `http://127.0.0.1:3100` in
  `service.cors_origins`, added during the PA→Alfred migration.

Scope worth having on day one: the Overview/resource charts, the alerts list with
ack, and the Projects tab — the parts that benefit most from a big screen. The
Files tab's action endpoints (Session 18) are the higher-risk surface and should
follow, not lead.

---

_Remaining inbox clear — all other pending ideas promoted to sessions on 2026-07-24:_

- File organisation & cleanup → **Session 18**
- Dashboard enhancements → **Session 19**
- Project management (branch cleanup, per-project thresholds, TODO cap) → **Session 20**
- Developer experience (shared models, drift guard, smoke test) → folded into **Sessions 13–14**
- Self-monitoring (self endpoint, SSE, anomaly detection) → **Session 17**
- Notifications — less obtrusive → **Session 16**

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
