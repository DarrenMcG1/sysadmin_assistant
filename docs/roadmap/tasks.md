# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-07-24

---

## Active Sessions

_No active sessions._

---

## Backlog

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

### Session 16: Notification calm
Make notifications less obtrusive — all changes in sysadmin_tray/tray_icon.py + notifications.py, sharing the fingerprint-tracking state.
- Update-in-place: track D-Bus notification ID per fingerprint/service and use `replaces_id` (notifications.py:159 currently hardcodes 0) so state changes replace the popup instead of stacking
- Flap cooldown: per-fingerprint cooldown (~30 min) — `_seen_fps &= active_fps` (tray_icon.py:248) currently re-notifies on every flap; roll repeats into one "X flapped N× in the last hour"
- Coalesce same-poll alerts into one summary notification when >1 arrives in a cycle ("3 new alerts: 1 critical, 2 warning")
- Snooze/mute: "Snooze 1h" action button (reuse DbusNotifier's existing action-button mechanism) + per-service `mute: true` in config.yaml — kills expected-down noise from PA/Redis
- Progressive escalation: quiet low-urgency notify on first failed poll; persistent-critical only if still failing after N polls
- `transient: true` D-Bus hint on info/recovery/service-action toasts so they skip KDE's notification history
- Honour desktop DND: query org.freedesktop.Notifications `Inhibited` property to auto-suppress during KDE DND/screen-share
- Optional warning digest mode: warnings badge the tray icon only, delivered as hourly/daily digest or folded into morning briefing; only critical interrupts live

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

### Session 18: File organisation & cleanup actions
- Auto-organise misplaced files via API endpoint with dry-run preview; extend `FILE_CATEGORIES`: books (.epub/.mobi/.azw3/.cbz/.cbr → Books/), PDFs routed Books/ vs Documents/ by heuristics, archives (.zip/.tar.gz/.7z/.rar → Archives/), loose code files in ~/ flagged for review
- Configurable category→folder mapping in config.yaml
- Duplicate file cleanup endpoint: preview + remove (keep newest or largest, dry-run)
- Old downloads cleanup: archive or delete >30 days with preview

### Session 19: Dashboard enhancements
- Files tab: quick-wins, duplicates, misplaced, reclaimable space, large files (API exists under /api/files/*, needs PyQt6 UI)
- Project health trend chart per project (historical data already stored)
- Disk growth forecast widget from /api/files/trends regression data with projected threshold dates
- Quick-wins widget: one-click fixes for empty dirs / stale caches

### Session 20: Project scoring & branch hygiene
- Branch cleanup actions: prune stale branches with confirmation + dry-run (PA-auto has 186)
- Per-project alert thresholds in projects.yaml instead of global <40
- Cap TODO scoring penalty (e.g. max 30 points) so high-TODO projects aren't permanently at 0

---

## Archive

All completed sessions and features archived in [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md).
