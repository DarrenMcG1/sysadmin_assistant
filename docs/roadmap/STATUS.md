# Project Status Dashboard

**Last Updated**: 2026-07-24
**Current Phase:** Feature-complete — maintenance & future features

> **Next up**: Sessions 16 + 17 in [tasks.md](tasks.md) — can run in parallel: 16 (notification calm, tray-only) and 17 (self-monitoring, backend-only). Sessions 10–15 complete, 0 open SNAGs in [snag_list.md](snag_list.md).

---

## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 4 agents + scheduler + DB |
| API | 🟢 Complete | 25+ endpoints across 5 routers; bearer-token auth on mutating endpoints (GETs open) |
| Database | 🟢 Complete | 9 tables in sysadmin schema, Alembic migrations |
| Agents | 🟢 Complete | SysAdmin, Project Organiser, File Organiser, Log Aggregator |
| GPU Monitoring | 🟢 Complete | AMD via rocm-smi + sysfs fallback, temp/VRAM alerts |
| Observability | 🟢 Complete | Structured JSON logging + request access logs |
| KDE Tray App | 🟢 Phase 3 Complete | Tray icon + service grid + D-Bus notifications + native dashboard + DND mode + service actions (popup retired 2026-07-24) |
| PA Integration | 🟢 Complete | Summary digest endpoint + v2 notification targeting |
| Testing | 🟢 Complete | 245 backend + 119 tray = 364 total; real-app fixture, schema drift guard, smoke script |
| CI | 🟢 Complete | GitHub Actions: ruff + mypy-clean codebase + full pytest (headless Qt) |
| LLM | 🟢 Complete | llama.cpp (llama-server :8081, OpenAI-compatible API) — migrated from Ollama 2026-07-24 |
| Frontend | 🟢 Complete | Built in PA using sysadmin API endpoints |

---

## Recently Completed

- **2026-07-24 — Session 17: Self-monitoring.** New `GET /api/sysadmin/self` (`sysadmin/services/self_monitor.py`) reads `agent_runs` back for the first time: per-agent last run/status, duration trend, consecutive failures, and a *stalled* flag whose window is derived from each agent's configured interval (`interval × self_monitor.stall_grace_multiplier`, floored at `min_stall_grace_seconds`) rather than hardcoded — never-run agents are deliberately not flagged. The SysAdmin agent raises/auto-resolves `"<agent> agent stalled"` alerts from the same report. New SSE endpoint `GET /api/sysadmin/events` (`sysadmin/services/sse.py`, `StreamingResponse`, no new dep) turns the dormant `event_bus.py` into the push path — agents publish `alert.raised`/`alert.resolved`/`agent.run`/`service.status` (buffered until their transaction commits, handed to the API loop via `EventBus.publish_threadsafe` since agents run on scheduler threads), heartbeat comments keep idle streams alive, disconnects unwind cleanly, and the path is access-log-excluded like `/health`. Resource anomaly detection (`sysadmin/services/anomaly.py`) adds z-scores over 7 days of `resource_snapshots` for CPU/RAM/each mount with cold-start and flat-series guards, suppressed when a fixed-threshold alert already covers the resource. New `self_monitor:`/`events:`/`anomaly:` config sections; no schema change. Verified live against the real service and DB. 117 new tests — suite 364 → 481.
- **2026-07-24 — Session 14: Config consolidation + docs.** New `sysadmin/defaults.py` (stdlib-only) is the single source of the API host/port — backend `ServiceConfig` and tray `TrayConfig` both import it. Magic numbers lifted to config.yaml with unchanged defaults: project grade bands (`agents.project_organiser.grade_bands` 80/60/40), reclaimable-space milestones (`agents.file_organiser.reclaimable_milestones_mb` 1/5/10 GB), briefing/retention cron times (new `schedules:` section, 06:00/03:00), CORS origins (`service.cors_origins`). docs/ARCHITECTURE.md rewritten from the real code (was an untouched template) with component diagram. pydantic-settings dropped (unused); confirmed zero env-var reads so CLAUDE.md now says "config.yaml only" instead of referencing a nonexistent .env.example; CLAUDE.md Step 4 test commands filled in. claude-preflight.sh now lists open SNAG count + titles from the Open Issues section only (Fixed Issues no longer inflate counts). 9 new tests — suite 355 → 364.
- **2026-07-24 — Session 13: Test hardening + CI.** Tests now run against the REAL app: `sysadmin/main.py` exposes `create_app()` and conftest builds it with only the lifespan stubbed (routers, middleware, exception handlers, auth deps all production). New shared contracts module `sysadmin/contracts.py` (pydantic-only) is the single source of truth for tray-consumed response shapes — set as `response_model=` on 13 backend routes and imported by `sysadmin_tray/models.py` (hand-copied dataclasses deleted; root cause of SNAG-TRAY-005 gone); Contract Registry in CLAUDE.md filled in. Schema drift guard (`tests/test_schema_drift.py`) found real drift: fixed alembic/env.py double-reflection and added migration 002 (NOT NULL alignment on 22 columns + idx_alerts_active direction) — `alembic check` now clean. New tests for briefing, event bus, app factory, contract round-trips. `scripts/smoke_test.sh` curls the live service (4 checks, fail-fast). GitHub Actions CI (ruff + pytest, headless PyQt6). mypy adopted (8 errors found and fixed, now clean); repo-wide ruff cleanup (191 issues). Suite 327 → 355.
- **2026-07-24 — Session 15: LLM migrated Ollama → llama.cpp.** New `sysadmin/services/llm_client.py` (`LLMClient`) speaks llama-server's OpenAI-compatible API (`POST /v1/chat/completions`, health via `GET /health`); config `ollama:` → `llm:` (url `http://localhost:8081`, model informational — single loaded model). Monitored service + log source renamed to llama-server / `alfred-inference.service`, with new `user: true` support so systemd/journalctl helpers can address *user* units (`systemctl --user`, `journalctl --user`). Verified live end-to-end: real completion, `summarise_with_llm` stored a genuine summary, briefing Overnight Log Summary section populated. 13 new transport-mocked tests — suite now 327.
- **2026-07-24 — Session 12: API authentication.** Shared bearer token (`api.auth_token` in config.yaml) enforced via a FastAPI dependency (`sysadmin/auth.py`, `secrets.compare_digest`) on all seven mutating POST endpoints — service actions, alert ack, DND, scan-all, project/file scans, stale-cache clean. Read-only GETs stay open so tray + PA dashboards keep working. Tray client sends the token automatically (same config.yaml). Unset/empty token → auth disabled with a startup warning (config.yaml is committed, so the committed value is a placeholder — see [guides/api_auth.md](../guides/api_auth.md)). PA-side token wiring is a follow-up in the PA repo. 24 new tests — suite now 314.
- **2026-07-24 — Session 11: Verified bug fixes.** Alert ack returns a real 404 (SNAG-API-001), access-log exclusion fixed to the real `/health` path with the real router under test (SNAG-API-002), blocking psutil calls moved off the event loop via `asyncio.to_thread` in `/ports` and `_take_resource_snapshot` (SNAG-API-003), tray marks connection lost on malformed/skewed API responses and `from_dict` parsing is defensive (SNAG-TRAY-005). 12 new tests — suite now 290.
- **2026-07-24 — Session 10: Resolved uncommitted loose ends.** Removed unreachable StatsPopup (dashboard won; SNAG-TRAY-004), `get_last_commit_date` now checks all branches (SNAG-AGENT-001), removed dead `count_stale_branches` and unused `orphan_detection` flag, narrowed `get_repo` exception handling with logging. Promoted codebase-review backlog to Sessions 10-20 in tasks.md.

_See [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for full history._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
