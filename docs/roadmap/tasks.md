# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-04

---

## Active Sessions

### Session 23: Project-manager Tier 3 — weekly LLM portfolio review — ✅ Complete 2026-08-04

- [x] `ProjectReview` model + migration 004 (`project_reviews` table;
      drift guard caught and fixed a nullability/index mismatch)
- [x] `sysadmin/services/project_review.py` — gather (scores, week deltas,
      top recommendations) → bounded prompt → llama-server narrative →
      stored row + `info` alert. **Deterministic digest fallback when the
      LLM is unavailable** (`llm_used: false`) — GPU-busy is a normal
      state, not an error; `stats` JSONB keeps the inputs auditable
- [x] `GET /api/projects/review` + `POST /api/projects/review/generate`
      (auth), both before `/{name}`; contract + tray re-export
- [x] Weekly cron (`schedules.review_*`, default Mon 05:30 before the
      briefing) gated by `agents.project_organiser.weekly_review`
- [x] Briefing gains a "Weekly Project Review" section while < 8 days old
- [x] 21 new tests, **all inference mocked — GPU never touched** (user
      request: GPU busy); live fallback-path run against the real DB
      stored review #1. Real data exposed a `stale_branches` dict-shape
      bug in Session 22's recommendations detail — fixed + regression test
- [x] **Live inference test — done 2026-08-04 once the GPU freed up.**
      Found and fixed two real issues the mocks could not see:
      (1) the DB connection died mid-generation — this host sets
      `idle_in_transaction_session_timeout=1min` and inference takes
      longer, so `generate_review` now commits the read transaction
      before calling the LLM; (2) the 3B model fabricated the numeric
      "what moved" section two prompts running (unchanged scores narrated
      as increases; recommendation points presented as movement), so the
      narrative is now **hybrid**: `build_movers_section` computes the
      numbers deterministically and the model only writes the qualitative
      sections (decay / archive candidates / focus), where its output
      verified accurate against the input data. Residual quirks are
      cosmetic (markdown despite "plain text", ~250 words vs 150 asked)

### Session 22: Project-manager Tier 2 — recommendations engine — ✅ Complete 2026-08-04

Advice as data, execution left to the existing dry-run endpoints:

- [x] `sysadmin/services/recommendations.py` — pure findings → ranked
      advice; every item mirrors one scorer deduction so `points` is the
      exact score recovered; status-aware (waived deductions produce no
      advice); `no_remote` surfaces as a 0-point `risk` ranked first
- [x] `GET /api/projects/{name}/recommendations` — latest snapshot →
      advice + `potential_score` (declared before `/{name}` capture-all)
- [x] `GET /api/projects/actions` — portfolio-wide top wins, risk-first
      then points, `limit` with `total_available` honesty
- [x] Contracts `RecommendationInfo` / `ProjectRecommendationsResponse` /
      `PortfolioAction(s)`, response_model-enforced, tray re-exports added
- [x] 25 new tests incl. round-trips and the /actions-not-shadowed
      regression — suite 1051 → 1076
- [x] ideas.md housekeeping section migrated: missing-remote follow-up now
      served natively by /actions; remaining items reframed as detector ideas

### Session 21: Project-manager Tier 1 — deep discovery + project status — ✅ Complete 2026-08-04

Follows the 2026-08-04 ~/projects reorganisation (category folders:
`apps/`, `web/`, `ml/`, `games/`, `learning/`, `archive/`). The organiser's
top-level-only discovery saw 3 projects where 24 exist, so:

- [x] Depth-aware discovery: descend into category dirs (no project markers)
      up to `discovery_depth` (default 2); never descend into a project
- [x] `status: active | dormant | archived` on projects.yaml entries, with
      `ProjectsConfig.status_for()` (same 3-key matching as alert_threshold)
- [x] Infer `archived` for anything under `archive/`; explicit yaml wins
- [x] Status-aware scoring: dormant/archived skip staleness penalties;
      archived also skips branch penalties and never alerts unless an
      explicit `alert_threshold` is set
- [x] Record status in snapshot `findings` (DB column deferred — no migration)
- [x] Tests alongside (28 new — suite 1023 → 1051); verified live: 24
      projects discovered, all 8 archive/ residents inferred archived

**Later tiers** (promote from ideas.md when ready): Tier 2 recommendations
engine (per-project action list ranked by score recovery — should absorb
the manual housekeeping follow-ups now parked in ideas.md), Tier 3 LLM
weekly narrative review via the briefing service.

---

## Backlog

_Empty — Sessions 10–20 below are all complete as of 2026-07-24. New work should
be added as Session 21+, or captured in [ideas.md](ideas.md) first._

**Carried-forward follow-ups** (small, noted by the sessions that deferred them):
- Wire Session 18's file-action endpoints (`/api/files/organise`, `clean/duplicates`,
  `clean/downloads`) into Session 19's Files tab — the tab is deliberately read-only
  because the endpoints landed in a parallel session
- Tray consumes Session 17's SSE stream (`GET /api/sysadmin/events`) instead of
  polling `/health` every few seconds
- `response_model=` on the `/api/files/*` GET routes (contracts exist and are
  parse-side enforced; the routes aren't annotated yet)
- Set a real `api.auth_token` in the local config.yaml — auth ships disabled
  because config.yaml is committed (the PA-side wiring this once referred to
  is moot; PA was retired 2026-07-24)
- Visual sanity-check of the new Files tab and trend charts on a real Plasma
  session (built and screenshotted headless only)

---

## Maintenance

_Not numbered sessions — config/upkeep work that doesn't warrant one._

### Daemon runtime-environment fixes (SNAG-SYSD-001, SNAG-AGENT-003) — ✅ Complete 2026-07-24
Two bugs the live `sysadmin.service` exposed once it picked up the Alfred config
above. Both had been verified interactively, where neither failure condition exists.
- ✅ **SNAG-SYSD-001** — `systemctl --user` needs `XDG_RUNTIME_DIR`; a system unit's
  environment has only `PATH`, so every `user: true` check failed and a live
  `alfred-evaluate.timer` was reported `critical`. `sysadmin/utils/systemd.py` now
  builds the subprocess env centrally and injects it (default `/run/user/<uid>`),
  fixing the status check, the details endpoint and start/stop/restart at once
- ✅ `DBUS_SESSION_BUS_ADDRESS` deliberately **not** derived — proved against the live
  bus that `XDG_RUNTIME_DIR` alone suffices; systemctl composes `$XDG_RUNTIME_DIR/bus`
- ✅ A failed *query* is no longer a verdict about the *unit*: `SystemdQueryError` /
  `UserBusUnavailableError` → status `"error"` (no alert, streak counters untouched),
  while a genuinely inactive unit is still `critical`. Details endpoint → 503, not 500
- ✅ Migration 003 widens `chk_health_status` to allow `'error'` — `_check_service`
  could always return it, but the DB constraint would have rejected the row
- ✅ **SNAG-AGENT-003** — one `httpx.AsyncClient` built on the API loop, then used from
  APScheduler threads under `asyncio.run()` (fresh loop per run, closed afterwards):
  pooled connections outlived their loop, so `llama-server` read `unreachable` with
  `"Event loop is closed"` while curl answered in 1 ms
- ✅ New `sysadmin/utils/async_http.py` (`LoopBoundClient`) — lends a long-lived client
  out only on the loop that built it, hands anywhere else a short-lived one closed on
  exit. `SysAdminAgent` opens a run-scoped pool in `_execute` and has no startup hook
- ✅ Audited the codebase for the same pattern: `LLMClient` (identical live exposure via
  the log aggregator) and `Notifier` (latent — `briefing.py` builds its own per call)
  both converted; `journalctl --user` confirmed unaffected (reads journal files, no bus)
- ✅ Regression test drives a **real** loopback server across two successive
  `asyncio.run()` calls (a mock transport holds no sockets and cannot reproduce this),
  plus a guard test asserting a naively shared client still raises
- ✅ Verified live with the daemon's environment simulated; 33 new tests — suite 990 → 1023
- ⚠️ The running `sysadmin.service` still serves the old code — it is a **system** unit,
  so a `sudo systemctl restart sysadmin.service` is needed to see the fix live

### PersonalAssistant → Alfred migration — ✅ Complete 2026-07-24
PA was retired and replaced by Alfred; the service's config still pointed at PA
everywhere. Config migration plus one dormant feature flag.
- ✅ projects.yaml: `personal-assistant` → `alfred` (backend `/api/health` on :8100,
  frontend :3100, both `user: true` systemd user units, journals via `journalctl --user`).
  The old entry's `path` (`/home/gaddi/projects/personal-assistant`) had never existed —
  the real directory is `PersonalAssistant` — so its health check was long since broken
- ✅ **Plumbed `user:` through the projects.yaml path** — Session 15 added the flag to
  `MonitoredService`/`LogSource` but `ProjectEndpoint`/`ProjectEndpointLog` never carried
  it, so `to_monitored_services()`/`to_log_sources()` silently dropped it. Log blocks
  inherit their endpoint's scope unless they set `user:` themselves. Proved live:
  `read_journal("alfred-backend.service", user=True)` → 500 entries, `user=False` → 0
- ✅ `alfred-evaluate` monitored via **`alfred-evaluate.timer`**, not the service — the
  service is `Type=oneshot` (inactive by design between daily 08:00 runs) while the timer
  stays `active`/`waiting` while armed, so the existing systemd check handles it as-is
- ✅ `alfred-glance` added scan-only (Android/Gradle, no service or port), like `daiy`
- ✅ Dead PA repos retired-but-retained with `alert_threshold: 0` — `PersonalAssistant`,
  `PersonalAssistant-auto`, `PA-worktrees`. Still dashboard-visible and branch-pruning
  targets; scores clamp at 0 and the test is `score < threshold`, so 0 never alerts
  (they score 15/10/80 against the global floor of 40)
- ✅ PA integration disabled: new `personal_assistant.enabled` (model default `True`,
  config.yaml `false`). Both `Notifier` send paths short-circuit before any HTTP call,
  logging once per process at INFO; the briefing's daily delivery-failed warning drops
  to DEBUG when off. Code and tests kept — dormant flag, not a deletion
- ✅ Docs: STATUS.md Frontend row → 🔴 Retired, PA Integration row → ⚪ Dormant;
  ideas.md gained a web-UI-in-Alfred item; CORS and `mute_services` comments re-examined
- ✅ 12 new tests (`tests/test_notifier.py`, `TestUserScopePropagation`) — suite 978 → 990

**Follow-up:** the running `sysadmin.service` loads config at startup, so it needs a
restart to pick any of this up (it was still reporting `ollama` and the PA services when
this landed — i.e. it predates even Session 15's config).

---

## Completed Sessions (2026-07-24)

_From codebase review 2026-07-24 — see snag_list.md for the individual bugs._

### Session 10: Resolve uncommitted loose ends — ✅ Complete 2026-07-24
Pre-commit cleanup of the working-tree changes previously in flight.
- ✅ Popup vs dashboard decided: dashboard won — removed `StatsPopup`/popup.py and the popup-only ActionBar widget entirely; left click opens dashboard — SNAG-TRAY-004
- ✅ `get_last_commit_date` now checks all branches via `max()`, with HEAD fallback for detached/branchless repos — SNAG-AGENT-001 (tests in tests/test_git_utils.py)
- ✅ Removed dead `count_stale_branches` import and the unused function itself (no other callers)
- ✅ Removed the unused `orphan_detection` config flag from config.py and config.yaml
- ✅ Narrowed `get_repo` to catch `InvalidGitRepositoryError`/`NoSuchPathError` silently; unexpected errors now logged via `logger.warning`

### Session 11: Verified bug fixes — ✅ Complete 2026-07-24
Small mechanical fixes — SNAG-API-001/002/003, SNAG-TRAY-005.
- ✅ Alert ack now raises `HTTPException(404)` instead of the Flask-style tuple return (sysadmin/routers/sysadmin.py); codebase grep found no other `return {...}, <status>` patterns; missing-alert 404 test added — SNAG-API-001
- ✅ Middleware exclusion fixed `/api/health` → `/health` (health router mounts at `/health` in main.py); test_logging.py now mounts the REAL health router and asserts it answers 200 — SNAG-API-002
- ✅ Blocking psutil calls wrapped in `asyncio.to_thread`: `/api/sysadmin/ports` handler, and `_take_resource_snapshot` split so blocking collection runs in `_collect_resource_metrics` via `to_thread` (safe on both scheduler-thread and manual scan-all paths); off-loop tests added — SNAG-API-003
- ✅ Tray: fetch paths catch `ValueError`/`TypeError` (non-JSON body, payload shape drift) and mark connection lost; all `**kwargs` `from_dict`s in models.py converted to defensive `.get()` style; malformed-JSON and extra/missing-field tests added — SNAG-TRAY-005 (Session 13 replaces these dataclasses with shared contracts)

### Session 12: API authentication — ✅ Complete 2026-07-24
Shared bearer token on state-changing endpoints; rationale: localhost binding doesn't stop CSRF-style POSTs from browser pages or other local processes.
- ✅ `api.auth_token` in config.yaml (new `ApiConfig` in sysadmin/config.py) checked by `require_auth` dependency (sysadmin/auth.py, `secrets.compare_digest`, 401 + `WWW-Authenticate: Bearer`) on all seven mutating POSTs: service actions, alert ack, DND, scan-all, project scan, file scan, stale-cache clean; read-only GETs deliberately open
- ✅ Unset/empty token → auth disabled (backwards compatible) with a startup warning; config.yaml is committed to git so the committed value is an empty placeholder — set a real token locally (`secrets.token_hex(32)`), documented in docs/guides/api_auth.md
- ✅ Tray client sends `Authorization: Bearer` on every request — TrayConfig reads `api.auth_token` from the shared config.yaml, ApiWorker sets the header on its httpx.Client
- ✅ PA integration: PA's dashboard views use GETs only so nothing breaks; PA-side header wiring for any mutating calls documented in docs/guides/api_auth.md as a follow-up in the PA repo (out of scope here)
- ✅ Tests: 18 backend (tests/test_auth.py — 401 missing/wrong/malformed token across all routes, correct token passes, disabled/empty-token open, GETs open, scan-all carries the dependency) + 6 tray (header wiring, config loading) — suite 290 → 314

### Session 13: Test hardening + CI — ✅ Complete 2026-07-24
- ✅ Real-app test fixture: main.py refactored to a `create_app(lifespan_ctx=...)` factory (module-level `app = create_app()` unchanged for uvicorn); conftest's `test_client` now builds the REAL app — production routers, CORS + RequestLoggingMiddleware, JSON-500 exception handler, auth dependencies — with only the lifespan stubbed and `app.state` agents mocked. `scan-all` moved from module-global agents to `request.app.state` (matching the other trigger endpoints) so it's finally testable end-to-end. All 208 existing backend tests passed unchanged on the real app; tests/test_app_factory.py adds coverage the synthetic app could never have: scan-all triggers all four agents, project-scan uses app.state, JSON 500 handler, CORS preflight, JSON 404, response_model field-dropping
- ✅ Service tests: tests/test_briefing.py (9 — all four section builders incl. empty-DB/psutil-failure paths, send_morning_briefing delivery + shutdown-on-failure) and tests/test_event_bus.py (7 — pub/sub, isolation of failing callbacks, fire-and-forget); llm_client's 13 Session-15 tests reviewed, no gaps worth extending
- ✅ Shared contracts: new `sysadmin/contracts.py` — pydantic-only (no FastAPI/SQLAlchemy imports, so the tray stays light) wire models for every tray-consumed endpoint, set as `response_model=` on 13 routes (health, status, alerts, ack, resources/history, service action, dnd GET/POST, scan-all, logs/recent, logs/stats, projects/overview, projects/managed); `/resources` and `/services/{name}/details` are parse-side contracts only (union "no data yet" shape / raw systemctl props). sysadmin_tray/models.py now imports the contracts (hand-copied dataclasses deleted) and keeps only IconState/colours/compute_icon_state. Defensive behaviour preserved: `extra="ignore"`, defaulted fields, ValidationError-is-a-ValueError so the client's connection-lost path still catches parse failures — all 119 tray tests passed unchanged. Contract Registry in CLAUDE.md filled in; tests/test_contracts.py (5) round-trips real endpoint responses through the tray-side models
- ✅ Schema drift guard: tests/test_schema_drift.py runs alembic `compare_metadata` against the live postgres (skipif when DB unreachable, so CI without postgres passes). It immediately caught REAL drift: (a) alembic/env.py double-reflected tables (search_path=sysadmin + include_schemas=True vs metadata's explicit `schema="sysadmin"`) — fixed with `include_name` schema filter + search_path=public; (b) migration 001 (hand-written) created 22 defaulted columns nullable where the models say NOT NULL, and idx_alerts_active as `created_at DESC` where the model says ascending — fixed by new migration 002 (backfill + SET NOT NULL + index recreate), applied to the live DB; `uv run alembic check` now reports no operations
- ✅ scripts/smoke_test.sh (executable): health / status / summary / deliberate-404-expects-JSON against http://127.0.0.1:8500 (base URL overridable), coloured pass/fail per check, exit 0/1, fails fast with start-the-service hint when unreachable — both paths verified live
- ✅ .github/workflows/ci.yml: astral-sh/setup-uv (cached) → apt PyQt6 libs (libegl1/libgl1/libxkbcommon0/libdbus-1-3/libfontconfig1/libglib2.0-0) → `uv sync --extra dev --extra tray` → `ruff check .` → `uv run pytest` with QT_QPA_PLATFORM=offscreen (tray tests already create QApplication themselves); no postgres service — drift guard self-skips. Repo-wide ruff was failing (191 issues: datetime.UTC modernisation, unused imports, import order, 37 long lines, 2 dead variables…) — all fixed; per-file E501 ignore only for the historical 001 migration and legacy home_audit.py
- ✅ mypy: adopted (count was modest). `uv run mypy sysadmin` found 8 real errors (None-unsafe `svc.url`/`svc.systemd_unit` in health checks, untyped dicts, Sequence/list mismatch, JsonFormatter assignment, Result.rowcount) — all fixed; mypy added to dev deps with a lenient `[tool.mypy]` baseline (ignore_missing_imports, check_untyped_defs; alembic/tests/tray excluded), now clean over 45 files
- Suite: 327 → 355 (236 backend + 119 tray); ruff, mypy, lint_check.sh all clean

### Session 14: Config consolidation + docs — ✅ Complete 2026-07-24
- ✅ Host/port defaults deduplicated into new `sysadmin/defaults.py` (stdlib-only, like contracts.py): `DEFAULT_API_HOST`/`DEFAULT_API_PORT`/`default_api_url()` — imported by backend `ServiceConfig` and tray `TrayConfig` (both the field default and the config-missing fallback)
- ✅ Magic numbers → config (defaults preserved, all in config.yaml): health-grade bands → `agents.project_organiser.grade_bands` (`healthy_min: 80` / `needs_attention_min: 60` / `neglected_min: 40`, used by /overview `_grade`, /stale threshold, /report emoji); reclaimable milestones → `agents.file_organiser.reclaimable_milestones_mb: [1024, 5120, 10240]` (labels derived, e.g. "1gb"); briefing/retention cron → new root `schedules:` section (`briefing_hour: 6`, `retention_hour: 3` + minutes); CORS origins → `service.cors_origins` (create_app reads via get_config)
- ✅ docs/ARCHITECTURE.md rewritten from the real code: app factory, 6 routers, BaseAgent template method + APScheduler asyncio.run() bridge, services, sysadmin schema + Alembic, shared contracts/defaults modules, tray structure, PA integration, auth, JSON logging, ASCII component diagram
- ✅ Deps: pydantic-settings dropped from pyproject (no imports anywhere; python-dotenv was never a direct dep and left with it via `uv sync`); grep confirmed NO env vars read anywhere (`os.environ`/`getenv`/dotenv) → CLAUDE.md's `.env.example` reference replaced with a "config.yaml only, no env vars" note instead of adding the file
- ✅ CLAUDE.md Step 4 filled in: `uv run pytest` + `uv run ruff check .` + `uv run mypy sysadmin` (all CI-enforced)
- ✅ claude-preflight.sh: snag section now parses only the "Open Issues" section (awk slice + `- [Pn]` grep — the old grep counted Fixed Issues too) and prints count + full titles, or "None — all clear" when empty; both states verified
- ✅ 9 new tests (tests/test_config_defaults.py) pin the shared defaults + lifted values — suite 355 → 364

### Session 15: Migrate LLM client from Ollama to llama.cpp — ✅ Complete 2026-07-24
Runtime has switched to llama.cpp (llama-server); code still spoke the Ollama API, so LLM features silently degraded to None and the monitored "ollama" service alerted as down.
- ✅ services/ollama_client.py → services/llm_client.py (`OllamaClient` → `LLMClient`): `POST /v1/chat/completions` with system prompt as a `{"role": "system"}` message, response parsed from `choices[0].message.content`; availability via `GET /health` (200 ready, 503 loading); same graceful-None interface (`generate`/`is_available`/`startup`/`shutdown`) so the only caller (log_aggregator.py) needed just the rename; optional `transport` constructor param for test injection
- ✅ Config: `ollama:` → `llm:` block (`OllamaConfig` → `LLMConfig`) — url http://localhost:8081 (real llama-server port, confirmed via `ss`/unit file), model dria-agent-a-3b.Q4_K_M.gguf (informational — llama-server serves one loaded model, no switching logic), `timeout_seconds` now configurable; unused `night_model` dropped. Monitored service renamed ollama → llama-server (health url `:8081/health`, unit `alfred-inference.service`); log source renamed likewise
- ✅ llama-server runs as a systemd *user* unit, which the existing system-scope `systemctl`/`journalctl` helpers couldn't see — added `user: true` flag on MonitoredService/LogSource, threaded through utils/systemd.py, utils/journal.py, sysadmin_agent, and the service details/action endpoints (`systemctl --user`, `journalctl --user`)
- ✅ Verified live end-to-end against the running server: `/health` ok, real completion, `summarise_with_llm` produced and stored a genuine summary via the real DB, and the briefing's Overnight Log Summary section carried it; user-scope unit status + journal reads confirmed working
- ✅ tests/test_llm_client.py — 13 tests via httpx.MockTransport: health up/down/503-loading, completion + system-prompt placement, model override, HTTP error/connect error/timeout/malformed/non-JSON → None, lifecycle + lazy client (suite 314 → 327)

### Session 16: Notification calm — ✅ Complete 2026-07-24
Made notifications less obtrusive. New `NotificationPolicy` in sysadmin_tray/notifications.py owns all the shared per-fingerprint state (`_FingerprintState`: episode open/poll count, last-notified timestamp, suppressed-flap count, escalation flag) and returns `NotificationRequest`s; `TrayIcon._check_new_alerts` now just feeds it the poll and dispatches the verdict — the old `_seen_fps` set is gone. Fingerprints stay `"{severity}:{title}"`, and are now the key for replacement as well as dedup. The policy is Qt-free with an injectable clock, so the whole state machine is testable without sleeping or a session bus.
- ✅ Update-in-place: `DbusNotifier` keeps `fingerprint → notification_id` and passes it as `replaces_id` (was hardcoded 0), so a state change *replaces* its popup; a stale id after the user dismisses is deliberately kept (the daemon treats unknown ids as new). Verified live against the running Plasma daemon — the second Notify returned the same id
- ✅ Flap cooldown: `flap_cooldown_minutes` (default 30) per fingerprint. Recurrences inside the window are counted, not shown; the first notification after the window carries "X flapped N× in the last hour". An alert that stays up through the window still gets its one delayed notification (never silenced forever)
- ✅ Coalescing: ≥`coalesce_threshold` (default 2) *new* alerts in one poll become a single "3 new alerts" summary whose first body line is "1 critical, 2 warning" (counts use true severities, urgency follows the effective ones); a lone new alert keeps its detail, and escalations are never folded in since they target a specific popup
- ✅ Snooze/mute: "Snooze 1h" action button alongside "Restart" (`snooze_requested` signal → `TrayIcon` → `policy.snooze()`), scoped to the service when the alert has one, else to the fingerprint; `snooze_minutes` sets both the window and the button label. `mute: true` on a monitored service (new field on `MonitoredService`) plus `notifications.tray.mute_services` permanently silence expected-down services — muted alerts still colour the icon and reach the dashboard. projects.yaml-derived services (personal-assistant, …) have no flag of their own, so they are muted by name in `mute_services`
- ✅ Progressive escalation: a brand-new critical opens at low urgency + `transient` (honest "CRITICAL: sysadmin" label, quiet delivery); only after `escalation_polls` (default 3) consecutive failing polls does it re-fire at critical urgency, persistent, replacing the quiet popup in place with "Still failing after N checks". Warnings never escalate; `escalation_polls: 1` restores the old immediate-loud behaviour
- ✅ `transient: true` hint on quiet/info notifications and on service-action feedback toasts, so KDE's history keeps only what matters; warnings, escalated criticals and the digest stay non-transient
- ✅ Desktop DND: `Inhibited` read via `org.freedesktop.DBus.Properties.Get` (PyQt6's `QDBusInterface.property()` returns None for it even where the daemon exposes it — confirmed by introspection), cached 5s, and disabled permanently after one unreadable answer. **App DND vs desktop DND**: the more restrictive wins — the app's own `/api/sysadmin/dnd` is authoritative for criticals (`allow_critical` decides whether they break through), while desktop inhibition suppresses everything *except* criticals. `respect_desktop_dnd: false` opts out
- ✅ Warning digest mode (`digest_mode`, default off): warnings only badge the tray icon (existing `compute_icon_state` behaviour) and are queued, then delivered as one low-urgency "SysAdmin digest — N alerts in the last hour" every `digest_interval_minutes`; criticals still interrupt immediately. Flush rides the existing alert poll — no extra timer
- ✅ Config: new `notifications.tray:` block (flap_cooldown_minutes 30, escalation_polls 3, coalesce_threshold 2, snooze_minutes 60, digest_mode false, digest_interval_minutes 60, respect_desktop_dnd true, mute_services []) loaded by `TrayConfig`/`load_tray_config` and pushed into the policy by `TrayApp`
- ✅ Tests: 93 new (tests/test_tray/test_notification_calm.py 81 + config 10 + backend mute-flag 2) with the D-Bus transport mocked at the `_send`/`_read_inhibited` seams so the CALLS are asserted — replaces_id reuse, urgency, transient hint, action buttons, coalesced copy, cooldown/flap counting, mute, snooze expiry, escalation sequence, digest batching, both DNDs. Two existing tests changed on purpose (a mixed-severity poll now coalesces; recurrence now respects the cooldown). Suite 364 → 459

### Session 17: Self-monitoring — ✅ Complete 2026-07-24
The service could not answer "are my own agents still running?" — nothing read `agent_runs` back, and a silently-dead agent looked identical to a healthy one.
- ✅ `GET /api/sysadmin/self` (`sysadmin/services/self_monitor.py`, contract `SelfMonitorResponse`/`AgentSelfHealth`): per-agent last run + status, `recent_durations` with mean and a rising/falling/steady trend (newer half vs older half of the last N runs), consecutive-failure streak (in-flight "running" records skipped, not counted as failures), `expected_next_run_at`, and `stalled`. One window-function query (`row_number()` partitioned by agent) fetches the newest N runs per agent, so a long-dead agent still yields its last run instead of being crowded out by a chatty one
- ✅ "Stalled" is derived from config, never hardcoded: `agent_schedules()` mirrors main.py's four `schedule_interval` registrations (sysadmin `health_check_interval_seconds`, project/file organiser `scan_interval_hours × 3600`, log aggregator `poll_interval_seconds`); stall window = `interval × self_monitor.stall_grace_multiplier` floored at `min_stall_grace_seconds` (3.0 / 300s) so a restart cannot flag the 60s log aggregator. An agent with *no* recorded runs reports `last_status: "never"` and is deliberately **not** stalled — a fresh install is indistinguishable from a stopped daily agent. A stuck `running` record older than the window does count as stalled
- ✅ Stall alerting wired into the existing mechanism: the SysAdmin agent calls the same `build_self_report()` the endpoint serves (so alert and endpoint can never disagree) and raises `"<agent> agent stalled"` via `BaseAgent.raise_alert`, deduplicated against unresolved alerts carrying `details.stalled_agent` and auto-resolved once the agent runs again
- ✅ SSE endpoint `GET /api/sysadmin/events` (`sysadmin/services/sse.py`, `StreamingResponse` — no new dependency): reuses the previously-unused `event_bus.py` as the event source rather than adding a parallel mechanism. Agents now publish `alert.raised` / `alert.resolved` / `agent.run` / `service.status`; `EventBroadcaster` is the bus's only subscriber and fans events into one bounded queue per client (oldest dropped on overflow — a slow client never blocks an agent). Heartbeat comment every `events.heartbeat_seconds` (20s) keeps idle streams alive through proxies; disconnects need no polling — Starlette closes the generator, the `subscribe()` context manager unregisters the queue, nothing leaks. Path added to the access-log exclusion list next to `/health` so long-lived streams add no log noise (SNAG-API-002's source now removable entirely). `BaseAgent` buffers events until its transaction commits, so a client that refetches on an event actually sees the change
- ✅ Cross-loop safety: agents run on APScheduler threads via `asyncio.run()`, so publishing directly would touch API-loop queues from the wrong loop — `EventBus.bind_loop()` (called in the lifespan) + `publish_threadsafe()` hand delivery to the API loop via `run_coroutine_threadsafe`; `EventBus` is now a module singleton shared by main.py, the agents, and the broadcaster
- ✅ Resource anomaly detection (`sysadmin/services/anomaly.py`, pure/side-effect-free): rolling mean + sample stdev over `anomaly.window_days` (7) of `resource_snapshots`, flags |z| ≥ `z_threshold` (3.0) for cpu / ram / each disk mount. Cold-start guard (`min_samples` 30 → nothing flagged), flat-series guard (`min_stdev` 1.0 → no infinite z-scores from a constant series), `z_score()` returns `None` rather than inf/nan. History is read *before* the new snapshot joins the session so the current reading is not part of its own baseline
- ✅ Anomaly alert suppression: threshold alerts now tag `details.resource` + `details.threshold`, so an anomaly for a resource that already fired a fixed-threshold alert (this run, or still unresolved from an earlier one) is skipped; an open anomaly alert is not re-raised every 5 minutes, and anomaly alerts self-resolve once the resource is back in range
- ✅ Config: new `self_monitor:` and `events:` sections plus `agents.sysadmin.anomaly:` in config.yaml + config.py (all defaults unchanged behaviourally). No schema changes → no migration; `tests/test_schema_drift.py` still clean
- ✅ Verified live against the real service + DB: `/api/sysadmin/self` returned real run history (and surfaced a genuine finding — file_organiser has never run), and a live `curl -N` SSE stream received heartbeats plus real `agent.run` events
- ✅ 117 new tests — z-score maths (known series → known z, cold start, zero variance), self-monitor logic + endpoint against the real-app fixture, SSE broadcaster/wire-format/heartbeat and a connect→receive→disconnect round trip through the real ASGI app (httpx's ASGITransport buffers whole bodies, so the stream is driven at the ASGI layer), agent wiring for anomaly suppression and stall alerting. Suite 364 → 481

**Follow-up (small):** point the tray at the SSE stream — replace `sysadmin_tray/client.py`'s `/health` poll loop with an `EventSource`-style consumer of `GET /api/sysadmin/events` (parse each `data:` line as `contracts.EventMessage`, refetch status/alerts on `alert.*` / `service.status`, fall back to polling if the stream drops). Backend side is done and the tray was owned by Session 16 in parallel, so it was left untouched. Note from the live run: the log aggregator raises one alert **per** error log line, so a single poll can emit dozens of `alert.raised` events — the consumer should coalesce (Session 16's coalescing covers this) and the per-client queue is bounded at 100 for exactly this reason.

### Session 18: File organisation & cleanup actions — ✅ Complete 2026-07-24
The file organiser could only ever *report*; acting on its findings meant doing it by hand. These are the first endpoints that move and delete the user's real files, so the safety model came first and the features were fitted around it. All the dangerous work lives in one dependency-light module (`sysadmin/services/file_actions.py` — no FastAPI, no DB), which is why every rule below is unit-testable against a fabricated tree.
- ✅ **Safety model** (applies to all three endpoints): **dry run by default** — the body must carry `confirm: true` to touch anything, and the response is the same manifest either way (`dry_run` says whether it ran, each operation's `status` says what happened to it). POST-only behind `require_auth`. Both source *and* destination are `Path.resolve()`-d before the root check, so `..` and symlinks cannot step outside `scan_root`. Symlinks are never followed (`os.walk(followlinks=False)`, symlinked files skipped, `os.rename` moves the link not its target). `.git`/`node_modules`/`__pycache__`/`.venv`/every dot-directory/`projects_root` are never entered. An existing destination is skipped with a reason, never overwritten — and the move reserves its destination with `O_CREAT|O_EXCL` so the check-then-rename race cannot clobber a file either. Plans are computed from the **live filesystem**, not the stored audit, since acting on a stale scan could move a file that has since changed
- ✅ **Delete means trash.** Minimal freedesktop trash implementation (`~/.local/share/Trash` + `.trashinfo` record written *before* the rename) rather than a `send2trash` dependency — the spec's home-trash case is ~30 lines, and doing it inline let us handle the cross-filesystem case honestly: the home trash only accepts same-device files, so anything else is **skipped**, not silently copy+deleted. Overriding needs `force_delete: true` in the request **and** `actions.allow_permanent_delete: true` in config; each flag alone is refused (tested both ways)
- ✅ `POST /api/files/organise` — relocates misplaced files into their category folders, returning per-file source → destination with byte counts. `FILE_CATEGORIES` extended with **books** (.epub/.mobi/.azw/.azw3/.cbz/.cbr/.fb2 → `Books/`; `.epub` moved out of documents) and **archives** (.zip/.7z/.rar/.tar/.gz/.tgz/.bz2/.xz/.zst → `Archives/` — matched on final suffix, so `.tar.gz` works). Files already under the destination *or* under a category's traditional folder name (an existing `photos/` tree) are left alone. **Loose code files in the scan root are flagged only, never moved** — a `.py` in `~/` usually means work in progress; code in subdirectories isn't flagged at all
- ✅ **PDF routing heuristic** (`classify_pdf`, first match wins): paperwork marker in the filename (invoice/receipt/payslip/statement/…) → `Documents/`; book marker (ISBN-13, "chapter", "vol. 2", "edition", a publisher, Z-Library/libgen) → `Books/`; a cheaply-read page count ≥ `pdf_book_min_pages` (50) → `Books/`; otherwise `Documents/`. The page count reads ≤1MB from each end of the file looking for `/Count n` inside a `/Type /Pages` dictionary (an `/Outlines` `/Count` must not inflate it — tested) and returns `None` when undetermined; **unknown never routes to Books**. Size alone is not evidence either — one scanned page can be tens of MB. Verified against the real `~/Downloads`: a 9MB 829-page PRINCE2 book → Books, a 1.2MB 1-page newspaper PDF and two interview-prep PDFs → Documents
- ✅ `POST /api/files/clean/duplicates` — reuses the agent's fingerprint (promoted `_get_file_hash` to a module-level `file_hash()`, so the action and `/api/files/duplicates` can never group differently) rather than re-implementing detection. `strategy: newest|largest` picks the survivor, ties broken by shortest-then-lexicographic path so plans are deterministic. **Exactly one copy per group always survives**: asserted when planning, and re-asserted in `execute_plan` against the live manifest (a hand-built manifest that would remove a retained copy raises rather than running)
- ✅ `POST /api/files/clean/downloads` — `mode: archive` moves files older than `older_than_days` (default `downloads_stale_days`, 30) into the configured archive folder preserving their path relative to `Downloads/`; `mode: trash` sends them to the XDG trash. `archive_dir` is rejected if it resolves outside the root or *inside* `Downloads/` (it would re-archive its own output)
- ✅ **Config-driven category mapping** (Session 14 style): new `agents.file_organiser.actions:` block — `category_folders` (category → folder, relative to `scan_root` or absolute; a folder resolving outside the root is skipped with a reason, not obeyed), `downloads_dir`, `archive_dir`, `duplicate_strategy`, `pdf_book_min_pages`/`pdf_book_min_mb`, `max_operations` (200, caps each manifest), `allow_permanent_delete` (false), `trash_dir`, `code_extensions`, and `enabled` as a master kill switch (→ 409). Retargeting a category is now a config edit
- ✅ Contracts: `FileOperation` / `FileFlag` / `FileActionResponse` appended to `sysadmin/contracts.py` and set as `response_model=` on all three routes; Contract Registry rows added to CLAUDE.md. One shared manifest shape across the three endpoints
- ✅ **Root cause of Session 17's finding — file_organiser had never run (0 rows in `agent_runs`) — was a genuine bug, now fixed.** Not the agent: APScheduler's `IntervalTrigger` schedules the *first* fire at `now + interval`, so a 24h job only ever runs if the service stays up a full 24h. Confirmed from the live DB — the service started 11:24, and project_organiser (6h) fired at exactly 17:24 with a history showing one restart most days, so the 24h job never reached its first execution. `schedule_interval` gained `first_run_delay_seconds`, applied to both hours-scale agents from `schedules.agent_first_run_delay_seconds` (60s). Also hardened `get_jobs()` against pending jobs (`next_run_time` is absent until the scheduler starts)
- ✅ 118 new tests (`tests/test_file_actions.py` 99, `tests/test_scheduler.py` 5, config defaults 5, plus the 3 new routes added to `test_auth.py`'s protected list) — all against `tmp_path` trees, **never the real home directory**. Cover: dry run leaves the tree byte-identical (full snapshot compare), confirm performs exactly the previewed operations, `..`/sibling/prefix-lookalike/symlink path escapes rejected, symlinked files and directories not followed, collisions skipped without overwriting, the retain-one duplicate invariant (including a manifest that violates it), both permanent-delete flags required, age-threshold boundaries (31 goes / 29 stays), and 401 without a token. Suite 576 → 694

**Not automated on purpose:** empty-directory and similar-folder cleanup (the audit reports both, but merging similarly-named folders needs human judgement); permanent deletion is available only behind two independent flags; and nothing acts on the stored audit — every action re-walks the filesystem first.

### Session 19: Dashboard enhancements — ✅ Complete 2026-07-24
The `/api/files/*` audit had no UI at all — the file organiser's findings only existed as JSON — and the stored project score history was never plotted. Everything here is tray-side (`sysadmin_tray/`) plus an appended block in `sysadmin/contracts.py`; no backend routes were added, since Session 18 owns those files in parallel.
- ✅ **Files tab** (`sysadmin_tray/dashboard/files_tab.py`, 5th dashboard tab): audit summary line (scan root + per-category counts) and a bold reclaimable-space figure from `GET /api/files/status`, a Quick Wins card and a Disk Growth Forecast card side by side, then a findings table with a Duplicates / Misplaced / Large-files selector (same `QComboBox` + `QTableWidget` pattern as the Logs and Projects tabs). Each view keeps its own parsed response and only re-renders when selected, so switching is instant and a slow endpoint never blanks another view. **Read-only**: the only buttons are Rescan (`POST /api/files/scan` — a re-audit, non-destructive) and the confirmed stale-cache clean
- ✅ **Charting: custom `QPainter` widget, no new dependency** — `sysadmin_tray/widgets/trend_chart.py` generalises the approach already used by `dashboard/overview_tab.py`'s `ResourceHistoryChart` (PyQt6-Charts is not a dependency and pyqtgraph/matplotlib would be a heavy addition for two line charts). `TrendChart` takes N named series, fixed or auto y-range, optional ISO x-labels, and degrades to a placeholder with no data / a single marker with one point; every shape is covered by a headless render test
- ✅ **Project health trend chart** on the Projects tab: cards are now clickable (blue border marks the selection, which survives a re-render) and load `GET /api/projects/{name}?limit=30`, whose `history` block was already being served and already stored — no new endpoint needed. The response arrives newest-first, so the tab reverses it before plotting; a reply for a project other than the current selection is ignored, so a slow fetch cannot overwrite a newer one
- ✅ **Disk growth forecast widget** (`sysadmin_tray/widgets/disk_forecast.py`) with the maths in a Qt-free `sysadmin_tray/forecast.py`. Two columns because the two questions have different sources: **reclaimable space** formats the regression `GET /api/files/trends` already computes (growth MB/day + projected milestone dates), while **disk usage** is a tray-side least-squares fit over the disk percentage in `GET /api/sysadmin/resources/history?hours=720`, projecting the dates the 80 %/90 % thresholds are crossed — `/api/files/trends` tracks *junk accumulation*, not disk occupancy, so it cannot answer "when does the disk fill up" on its own. States are explicit rather than blank (`projected` / `already exceeded` / `not on current trend` / `not enough samples`), and crossings are coloured by horizon (≤30 days red, ≤90 amber)
- ✅ **Quick-wins widget** (`sysadmin_tray/widgets/quick_wins.py`): empty-dir and stale-cache counts plus cache size from the audit's `quick_wins` block. The one wired action is the pre-existing `POST /api/files/clean/stale-caches?confirm=true`, gated behind a confirmation dialog that names `__pycache__`/`.pytest_cache`, states the megabytes, and caps the promised empty-dir count at the 50 the endpoint actually removes; the copy is built by a pure function so the exact wording is asserted in tests. The button is disabled with no scan data, nothing to clean, or an unreachable backend
- ✅ Client + contracts: `ApiClient`/`ApiWorker` gained read fetches for `/api/files/status|duplicates|misplaced|large|trends`, `/api/projects/{name}`, plus `POST /api/files/scan` and the confirmed clean. A 404 from the files endpoints means "no audit has run" — a legitimate empty state — so it emits a default-constructed model instead of an error; everything else reports through a new `file_fetch_failed(what, message)` signal, and the tab also listens to `connection_lost`/`connection_restored` (last known findings stay on screen, actions disable, forecast blanks). Contracts appended to `sysadmin/contracts.py` in one clearly-marked Session 19 block: `FileStatusResponse` (+`FileAuditSummary`, `FileQuickWins`), `DuplicatesResponse`, `LargeFilesResponse`, `MisplacedFilesResponse`, `FileTrendsResponse` (+`FileTrendScan`, `FileTrendForecast`), `CleanResultResponse`, `ProjectDetailResponse` (+`ProjectHistoryPoint`) — parse-side only, since the routers were contended this session
- ✅ 177 new tests (suite 576 → 753) across `tests/test_tray/`: forecast maths against known series (perfect-fit recovery, degenerate/flat/shrinking inputs, mount gaps skipped rather than read as 0 %, threshold dates to the day), contract parsing of both populated and "no data yet" payloads, worker fetches with mocked httpx (404-as-empty, 500, transport error, malformed JSON), tab construction and population, empty-state copy, the confirmation gate in both directions, and headless renders of every chart/card state. New `tests/test_tray/conftest.py` forces `QT_QPA_PLATFORM=offscreen` (matching CI) and provides a shared `FakeClient` so tabs are driven end-to-end with no worker thread or socket

**Follow-ups (deferred actions — backend not merged this session):**
- Wire the destructive file actions once Session 18 lands: auto-organise misplaced files (with its dry-run preview), duplicate cleanup, and old-downloads archive/delete. The Files tab is structured for it — each view already holds its parsed rows, so the work is per-row/selection buttons plus a confirmation dialog reusing `quick_wins.clean_confirmation_text`'s pattern (name the paths, state the count, say it cannot be undone). A "display-only until the file-action endpoints land" note is shown on the Quick Wins card and should be removed at the same time
- Register the `/api/files/*` + `/api/projects/{name}` shapes in CLAUDE.md's Contract Registry table — deliberately left untouched to avoid a merge conflict with Session 18's rows
- Consider `response_model=` on the `/api/files/*` GETs so the new contracts are enforced server-side too (they are currently parse-side only); needs `sysadmin/routers/files.py`, contended this session
- The Files tab fetches on show/tab-switch only. Once the tray consumes the SSE stream (Session 17's follow-up), a `agent.run` event for the file organiser should refresh it instead of the user pressing Rescan

### Session 20: Project scoring & branch hygiene — ✅ Complete 2026-07-24
The project organiser could *see* branch rot and TODO debt but do nothing about either: it reported PA-auto's branches and then scored the two big projects at a permanent 0, where nothing they fixed could ever show. This session adds the one destructive project action (branch pruning) and makes the score informative again.
- ✅ **Branch pruning** (`sysadmin/services/branch_actions.py` + `POST /api/projects/{name}/branches/prune`) built on Session 18's model: `require_auth`, **dry run unless the body sets `confirm: true`**, and the same manifest shape either way — one row per *local* branch with its name, last commit date and sha, merge state, upstream/ahead counts, and the reason it is (in)eligible. Eligibility is "merged into the default branch **and** untouched for `stale_days`+ days", where merged-ness comes from git itself (`repo.is_ancestor` → `merge-base --is-ancestor`), never inferred from dates. Execution uses `git branch -d` (safe delete), so git independently re-checks merged-ness; `-D` is reached only by the opted-in unmerged path. The manifest records `last_commit_sha` so a deletion is recoverable with `git branch <name> <sha>`
- ✅ **Two-flag pattern for the dangerous case**, mirroring `force_delete` + `allow_permanent_delete`: an unmerged branch needs `include_unmerged: true` on the request **and** `branch_actions.allow_unmerged_delete` in config (default false). Either flag alone reports and does nothing — and the config flag is re-read at execution time, so a plan built while it was on will not run once it is off. **Never deleted whatever the flags say**: the default branch, `protected_branches` globs (default `main`, `master`, `develop`, `release/*`), the checked-out branch, any branch checked out in a worktree, and any branch holding commits its upstream lacks. The default branch is **detected** — remote `HEAD` → `init.defaultBranch` → conventional names → sole local branch — and when it cannot be determined *nothing* is planned, since "merged" is meaningless without it. Ambiguity (unreadable upstream, unreadable commit date) is reported, never acted on. Paths are confined to `projects_root` (a managed project whose `path` points elsewhere is refused), `max_deletions` caps a call at 20 and a request may only lower it, and `min_stale_days: 7` floors the staleness window so `stale_days: 0` cannot sweep up today's work. Against the real PA-auto (224 local branches, all merged, 223 stale) a dry run plans 20 and reports the other 203 as capped
- ✅ **Per-project alert thresholds** — `agents.project_organiser.alert_threshold` (default 40) replaces the hardcoded `< 40`, and any projects.yaml entry may override it with `alert_threshold:`. `ProjectsConfig.alert_threshold_for()` matches the scanned project by resolved path, then managed name, then the basename of `path`, because the scanner names projects after their *directory* while projects.yaml names them however the user likes (`personal-assistant` → `PersonalAssistant`). Entries without the key are ignored entirely, so an existing projects.yaml behaves exactly as before; `alert_threshold: 0` is honoured as "never alert", not read as absent. The alert message now states the threshold it tripped
- ✅ **TODO penalty capped** at `max_todo_penalty: 30` (`null` restores the old unbounded rule). The 5-points-per-10-markers deduction is unchanged below the cap; above it the raw figure is recorded in `findings.todo_penalty_capped` so the score stays explainable. Real counts after Session 10's exclude-dirs: PersonalAssistant 327 TODO + 38 FIXME and PA-auto 290 + 18 were scoring −185/−154 and pinning both at 0; they now sit ~30 points down with room to move, while sysadmin_assistant (35 + 18) is unaffected at −25
- ✅ Contracts `BranchCleanupResponse` + `BranchInfo` appended to `sysadmin/contracts.py` in a marked Session 20 block, enforced with `response_model=` on the route and registered in CLAUDE.md
- ✅ 107 new tests (suite 871 → 978). `tests/test_branch_actions.py` builds **throwaway repos in `tmp_path`** with `git init` and fabricated commits — no real repository is ever opened: default-branch detection (main/master/remote HEAD/`init.defaultBranch`/single-branch/ambiguous/empty), each eligibility rule, the staleness boundary at 29/30/31 days, upstream-ahead and unreadable-upstream, worktree checkout, the cap (from config, lowered by request, not raisable, keeps the stalest, zero, negative), dry run leaving the branch set byte-identical, confirm deleting exactly the previewed set, all four two-flag combinations, and the re-validation paths (branch moved, checked out, or deleted since the preview). Plus threshold-lookup tests in `tests/test_projects_config.py` and cap-boundary/alerting tests in `tests/test_project_organiser.py`

**Follow-ups:**
- Tray/dashboard wiring: the Projects tab could show the dry-run manifest and a confirmation dialog, reusing `quick_wins.clean_confirmation_text`'s pattern (name the branches, state the count, say what is recoverable). The contract is already shared, so this is presentation only
- Remote-tracking refs are read but never deleted — `git remote prune origin` for gone-upstream branches is a separate, safer action worth adding
- A repo-wide "branch report" GET (no auth, no mutation) would let the score explain *which* branches cost it points, rather than only the count already in `findings.stale_branches`
- PA-auto's 224 branches will take 12 confirmed calls at the current cap; raising `max_deletions` for a one-off sweep is a config change, deliberately not a request parameter

---

## Archive

All completed sessions and features archived in [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md).
