# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-08-06

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### ✅ Promoted 2026-08-05 — the project-manager tier pattern in other domains

Sessions 21–23's three-tier ladder (measure → advice as data → periodic LLM
narrative) generalises, and all four candidates captured here are now
**Sessions 24–27 in [tasks.md](tasks.md)**, where the full detail lives:

| Session | Domain | Note |
|---|---|---|
| 24 | File organiser tiers | Currency is reclaimable bytes; also promotes the forecast maths out of the tray |
| 25 | Service reliability scoring | Scores services from `health_checks`/`alerts` history, which nothing reads today |
| 26 | Service discovery — unmonitored-unit detector | Directly requested; the mechanical backstop for [guides/monitorable-project.md](../guides/monitorable-project.md) |
| 27 | Log aggregator tiers | Coupled to SNAG-AGENT-002 — signature fingerprinting fixes both |

The detector ideas parked below feed **Session 24** as new Tier 1 findings:
once a finding exists, the advice for it follows automatically, which is the
payoff of the advice-mirrors-findings design.

### Silent-degradation detection — a service that is up but not doing its job

Captured 2026-08-06, from a real case: `alfred-inference`, `venture-chat`
and `venture-embed` had every model loaded into system RAM instead of VRAM
since installation. Every signal this repo collects said healthy — the unit
was `active (running)`, `/health` returned 200, the GPU sat idle so both
apps' busy-% guards were satisfied. The fault is now fixed at source
(`~/.local/bin/wait-for-dgpu`), but **nothing here would have caught it**,
and it will not be the last of its kind.

The general shape: a service can be *up*, *responsive* and *wrong*. Health
checks answer "is it listening"; they never answer "is it doing what it was
configured to do". Candidate detectors, cheapest first:

- **GPU residency assertion** — cross-reference `rocm-smi` VRAM occupancy
  against the inference services that are supposed to be resident. Three
  llama-servers up and ~3 GB of VRAM in use is arithmetically impossible;
  that is a finding with no per-app cooperation needed. Complements the
  existing `gpu_vram_warning_percent` threshold, which only fires when VRAM
  is *too full* — the opposite failure
- **Startup-log assertions** — a per-service optional `expect_log:` /
  `forbid_log:` pattern checked once after start. `CPU_Mapped model buffer
  size` in a unit meant to be GPU-resident is a one-line rule. The log
  aggregator already reads these journals for errors; this reads them for
  *absence of an expected line*, which no current agent does
- **VRAM budget vs declared residency** — sum what the units claim they
  hold against card capacity and warn when a scheduled job cannot fit. The
  02:00 collision found on 2026-08-06 (24B needing ~14.8 GB against ~12.4 GB
  free with granite resident) was arithmetic anyone could have done, and
  nobody did, because no one place knew all three numbers

Overlaps Session 25 (service reliability scoring) — reliability history and
"up but wrong" are the same question asked over different windows — and
wants the same unit-parsing sweep as Session 26, so it is probably cheapest
taken alongside one of them rather than as its own session.

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
- **Database occupancy is invisible to the file organiser** (found
  2026-08-06). The `projects` database is 16 GB, of which the **retired**
  `personal_assistant` schema is 15 GB across 821 tables — PA was retired
  2026-07-24. That is larger than the entire filesystem reclaim estimate,
  and the file organiser cannot see it: from the filesystem it is opaque
  bytes inside PostgreSQL's data directory, attributable to no project.
  A `pg_namespace`/`pg_database` size query joined to the archived-project
  list would surface it as a `reclaimable` finding in the Session 24
  currency. Dropping the schema itself stays a manual, confirmed action —
  irreversible, and the repos are archived on purpose.

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

_Promoted 2026-08-05:_

- Tier pattern in other domains (file organiser, service reliability,
  service discovery, log aggregator) → **Sessions 24–27**

_Promoted 2026-07-24:_

- File organisation & cleanup → **Session 18**
- Dashboard enhancements → **Session 19**
- Project management (branch cleanup, per-project thresholds, TODO cap) → **Session 20**
- Developer experience (shared models, drift guard, smoke test) → folded into **Sessions 13–14**
- Self-monitoring (self endpoint, SSE, anomaly detection) → **Session 17**
- Notifications — less obtrusive → **Session 16**

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
