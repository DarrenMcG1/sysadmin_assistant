# Project Status Dashboard

**Last Updated**: 2026-03-23
**Current Phase:** Core service + KDE tray app Phase 2 + DND mode + observability polish

---

## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 4 agents + scheduler + DB |
| API | 🟢 Complete | 25+ endpoints across 5 routers |
| Database | 🟢 Complete | 9 tables in sysadmin schema, Alembic migrations |
| Agents | 🟢 Complete | SysAdmin, Project Organiser, File Organiser, Log Aggregator |
| Scheduler | 🟢 Complete | APScheduler with interval + cron jobs |
| systemd | 🟢 Complete | Unit file + install scripts |
| KDE Tray App | 🟢 Phase 2 Complete | Tray icon + popup + service grid + D-Bus notifications + native dashboard + DND mode, 104 tests |
| DND Mode | 🟢 Complete | Schedule-based + manual toggle, critical breakthrough, backend + tray gating |
| Testing | 🟢 Complete | 104 backend tests + 124 tray tests = 228 total |
| Observability | 🟢 Complete | Structured JSON logging + request access logs |
| Frontend | ⬜ Not Started | Nuxt pages in PA (future) |

---

## Recently Completed

- **2026-03-23**: Structured JSON logging & request middleware
  - `sysadmin/logging_setup.py` — JSON (production/systemd) and text (dev) formatters
  - `sysadmin/middleware.py` — access log: method, path, status, duration_ms (excludes /api/health)
  - `config.yaml` — `log_format: json | text` option in service section
  - `tests/test_logging.py` — 10 tests covering formatter output, extra fields, middleware behaviour

- **2026-03-23**: Service controllable flag & auto-restart
  - `controllable` field on MonitoredService, 403 gating on service actions
  - Auto-restart after N consecutive failures for controllable systemd services
  - Tray UI hides action buttons for non-controllable services

- **2026-03-06**: Backend test suite (94 tests)
  - `tests/conftest.py` — mock config, mock async session, FastAPI test client fixtures
  - `tests/test_health.py` — health endpoint shape and status (3 tests)
  - `tests/test_sysadmin_agent.py` — HTTP/TCP/systemd checks, alerting logic, thresholds, auto-restart (28 tests)
  - `tests/test_project_organiser.py` — discovery, health scoring, edge cases, TODO counting (22 tests)
  - `tests/test_file_organiser.py` — all 8 finding types with tmpdir fixtures (20 tests)
  - `tests/test_retention.py` — purge logic, downsampling, table map completeness (9 tests)
  - `tests/test_routers.py` — status, resources, alerts, DND, ports endpoints (12 tests)

- **2026-03-06**: DND mode & notification control
  - Added `notifications` config section (desktop/PA severity thresholds, DND schedule)
  - DndManager service: schedule evaluation, manual override (tri-state), critical breakthrough
  - GET/POST `/api/sysadmin/dnd` endpoints for status and toggle
  - Notifier gated on DND + PA severity threshold
  - Tray: checkable DND menu item, DND in tooltip, desktop notifications suppressed during DND
  - Polls DND status alongside alerts, syncs menu checkbox from backend

- **2026-02-13**: D-Bus notifications + native dashboard + bug fixes
  - Fixed tray startup crash (missing @pyqtSlot decorators for D-Bus handlers)
  - Fixed D-Bus Notify signature mismatch (UINT32 + array-of-string marshalling)
  - Fixed notification spam (fingerprint-based dedup instead of DB row ID)
  - Removed CriticalAlertDialog in favour of native D-Bus notifications
  - Added native dashboard window (Overview, Services, Logs, Projects tabs)
  - Extended API client/models for dashboard endpoints

- **Session 1**: Project skeleton & bootable service
  - pyproject.toml, config.yaml, Pydantic config validation
  - Async SQLAlchemy engine with search_path for sysadmin schema
  - 9 SQLAlchemy models + Alembic migration
  - FastAPI app with lifespan + /health endpoint
  - systemd unit + install scripts

- **Session 2**: BaseAgent, Scheduler, Event Bus & SysAdmin Agent
  - APScheduler wrapper with async bridge
  - Event bus (pub/sub)
  - BaseAgent ABC with run tracking + alert system
  - SysAdmin agent (HTTP/TCP/systemd checks, psutil resources)
  - SysAdmin router (status, resources, alerts, ports)

- **Session 3**: Alerting, Notifier & PA Integration
  - Notifier service (POST to PA with retries)
  - Briefing service (collects from all agents)
  - Briefing preview endpoint

- **Session 4**: Project Organiser Agent
  - Git utility helpers (branches, staleness, remotes)
  - Project discovery + health scoring
  - Projects router (overview, detail, TODOs, branches, stale, report)

- **Session 5**: File Organiser Agent
  - Ported home_audit.py into agent framework
  - 8 filesystem checks with DB storage
  - Files router (status, report, delta, duplicates, large, misplaced, trends, clean)

- **Session 6**: Log Aggregator & LLM Summarisation
  - journalctl reader with severity mapping
  - Ollama client for LLM summarisation
  - Log aggregator agent (poll + summarise)
  - Logs router (recent, errors, summary, history, stats, by-source)

- **Session 7**: Retention, Integration & Polish
  - Retention service (daily purge at 03:00)
  - Full integration of all agents into main.py
  - scan-all trigger endpoint
  - CORS + error handling middleware

- **Session 8**: KDE System Tray App — Phase 1
  - `sysadmin_tray/` sub-package (11 source files)
  - Tray icon with green/amber/red/grey state (programmatic QPainter)
  - Threaded API client (QThread + httpx, no async)
  - Frameless popup: CPU/RAM/disk gauges, alert badges, action bar
  - Config layering: reads shared config.yaml + CLI overrides
  - 39 unit tests (config, models, client mocking, icon state)
  - `pip install -e ".[tray]"` + `python -m sysadmin_tray` entry point

- **Session 9**: KDE System Tray App — Phase 2
  - Service status grid in popup (coloured dots, name, status, response time)
  - Dynamic row add/remove as services appear/disappear
  - KDE desktop notifications via `QSystemTrayIcon.showMessage()`
  - Dedup by alert ID, severity threshold filtering, configurable via `notify_min_severity`
  - 31 new tests (13 grid + 16 notifications + 2 config) → 70 total tray tests

---

## Up Next

1. Test suite (conftest, health, agent mocks, retention)
2. Structured JSON logging for journal
3. Request logging middleware
4. Night Worker integration endpoints

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
- Disk at 89% triggered warning alert (threshold 80%)
- PA and Redis services detected as unreachable (expected — not running)
