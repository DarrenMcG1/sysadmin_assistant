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

### Session 11: Verified bug fixes
Small mechanical fixes — SNAG-API-001/002/003, SNAG-TRAY-005.
- Replace Flask-style tuple return with `HTTPException(404)` in alert ack (sysadmin/routers/sysadmin.py:294); grep for other `return {...}, <status>` patterns
- Fix middleware health-check exclusion path `/api/health` → `/health` (sysadmin/middleware.py:17); make test_logging.py mount the real health router
- Wrap blocking psutil calls in `asyncio.to_thread`: `/api/sysadmin/ports` handler and `_take_resource_snapshot`'s `cpu_percent(interval=1)` on the manual scan-all path
- Tray: catch `ValueError`/`TypeError` around `resp.json()` + dataclass construction in client.py; convert fragile `**kwargs` `from_dict`s in models.py to defensive `.get()` style

### Session 12: API authentication
- Shared bearer token in config.yaml, checked via FastAPI dependency on state-changing endpoints (service actions, stale-cache clean, scans, dnd, alert ack)
- Tray client + PA integration send the token
- Rationale: localhost binding doesn't stop CSRF-style POSTs from browser pages or other local processes

### Session 13: Test hardening + CI
- Build test app from real routers/middleware instead of synthetic stand-ins (tests/conftest.py noop lifespan let SNAG-API-001/002 slip through)
- Add tests for the three untested services: briefing.py, llm client, event_bus.py (mock httpx at transport layer)
- Shared response models between backend and tray — tray imports backend Pydantic models (or small shared contracts module) instead of hand-copied dataclasses in sysadmin_tray/models.py (root cause of SNAG-TRAY-005); fills the empty Contract Registry in CLAUDE.md
- Schema drift guard — test that `alembic autogenerate` against the models produces an empty diff
- Live smoke-test script `scripts/smoke_test.sh` — curl the real running service (health, status, summary, one deliberate 404)
- Minimal GitHub Actions workflow: ruff check + pytest
- Consider adding mypy (type hints are already required by convention)

### Session 14: Config consolidation + docs
- Deduplicate API host/port defaults (backend config.py:18, tray config.py:16 + fallback at 69-70)
- Move magic numbers to config: health-grade bands 80/60/40 (routers/projects.py ×3), reclaimable-space milestones (routers/files.py:257), briefing/retention cron hours + CORS origins (main.py)
- Rewrite docs/ARCHITECTURE.md (currently an untouched template describing nonexistent backend/frontend dirs)
- Drop unused deps: python-dotenv, pydantic-settings; add .env.example or remove the CLAUDE.md reference to it
- Fill in CLAUDE.md Step 4 test command (`uv run pytest`)
- claude-preflight.sh: print open SNAG count/titles from snag_list.md alongside STATUS.md priorities

### Session 15: Migrate LLM client from Ollama to llama.cpp
Runtime has switched to llama.cpp (llama-server); code still speaks the Ollama API, so LLM features silently degrade to None and the monitored "ollama" service alerts as down.
- Rewrite services/ollama_client.py for the OpenAI-compatible API (`POST /v1/chat/completions`; system prompt becomes a `system` role message; availability check via `GET /health` instead of `/api/tags`) — rename to llm_client.py
- Update config: `ollama:` block → `llm:` (url/port for llama-server, model names), monitored service entry (config.yaml:47-50: url + systemd_unit), log aggregator source unit (config.yaml:109-111)
- Verify `summarise_with_llm` path end-to-end and briefing LLM sections actually produce text again
- Add tests (folds into Session 13's untested-services work — ollama_client.py had zero coverage anyway)

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

### Session 17: Self-monitoring
- `/api/sysadmin/self` endpoint from the existing `agent_runs` table: per-agent last-run status, duration trend, consecutive-failure count; alert when an agent silently stops running
- Server-Sent Events endpoint so the tray gets pushed updates and stops polling `/health` every few seconds (also removes SNAG-API-002's log-noise source entirely)
- Resource anomaly detection: z-score against `resource_snapshots` history to alert on unusual CPU/RAM/disk patterns, not just fixed thresholds

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
