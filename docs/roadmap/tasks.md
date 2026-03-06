# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-03-06

---

## Active Sessions

_No active sessions._

---

## Completed Sessions

### Session 8: KDE System Tray App — Phase 1

**Status**: 🟢 Complete
**Branch**: `main`

- [x] pyproject.toml: `[tray]` optional extra, console script, packages list
- [x] `sysadmin_tray/__init__.py`, `__main__.py` — package skeleton
- [x] `sysadmin_tray/config.py` — TrayConfig (Pydantic), YAML + CLI layering
- [x] `sysadmin_tray/models.py` — Dataclasses for API responses + `compute_icon_state()`
- [x] `sysadmin_tray/client.py` — ApiClient + ApiWorker (QThread + httpx polling)
- [x] `sysadmin_tray/tray_icon.py` — QSystemTrayIcon, programmatic icons, context menu
- [x] `sysadmin_tray/widgets/` — ResourceGauge, AlertBadge, ActionBar
- [x] `sysadmin_tray/popup.py` — Frameless stats popup with click-outside dismissal
- [x] `sysadmin_tray/app.py` — Orchestrator (timers, signal wiring, entry point)
- [x] `tests/test_tray/` — 39 unit tests (config, models, client, icon state)
- [x] `config.yaml` — Added `tray:` section with poll intervals

### Session 1-7: Full Service Implementation

**Status**: 🟢 Complete
**Branch**: `main`

- [x] Project skeleton (pyproject.toml, config, package structure)
- [x] Database layer (async SQLAlchemy, search_path, session management)
- [x] All 9 SQLAlchemy models
- [x] Alembic migration (schema creation + seed data)
- [x] FastAPI app with lifespan management
- [x] Health endpoint
- [x] APScheduler wrapper
- [x] Event bus
- [x] BaseAgent ABC with run tracking
- [x] SysAdmin agent (health checks + resources)
- [x] SysAdmin router
- [x] Notifier service
- [x] Briefing service
- [x] Git utility helpers
- [x] Project Organiser agent
- [x] Projects router
- [x] File Organiser agent (ported from home_audit.py)
- [x] Files router
- [x] journalctl reader
- [x] Ollama client
- [x] Log Aggregator agent
- [x] Logs router
- [x] Retention service
- [x] Full integration (all agents, routers, scheduler jobs)
- [x] systemd unit + install/setup scripts
- [x] run-dev.sh updated

---

## Backlog

### DND Mode & Notification Control
- [x] Add `notifications` section to config.yaml with desktop/PA severity thresholds and DND schedule
- [x] Add `notifications` Pydantic models to `config.py` (DndConfig, NotificationsConfig)
- [x] Add `POST /api/sysadmin/dnd` endpoint to toggle DND at runtime (in-memory state, config as default)
- [x] Add DND schedule enforcement — auto-enable/disable based on `dnd.schedule` time windows
- [x] Gate notification dispatch in Notifier + tray on DND state (allow critical to break through when `allow_critical: true`)
- [x] Add DND toggle to tray context menu

### Service Controllable Flag
- [ ] Add `controllable: bool = True` field to `MonitoredService` in config.py
- [ ] Gate `POST /services/{name}/{action}` endpoint — return 403 if `controllable` is false
- [ ] Mark postgresql and any infrastructure services as `controllable: false` in config.yaml
- [ ] Add `auto_restart` + `auto_restart_after_checks` fields to MonitoredService
- [ ] Implement auto-restart logic in SysAdminAgent._handle_status() after N consecutive failures
- [ ] Wire controllable flag into tray popup ActionBar (disable buttons for non-controllable services)

### Testing (Priority)
- [ ] `tests/conftest.py` — Fixtures: test DB (transactional rollback), mock config, FastAPI test client
- [ ] `tests/test_health.py` — Health endpoint returns 200 with correct shape
- [ ] `tests/test_sysadmin_agent.py` — Mock HTTP/TCP checks, verify status determination and threshold alerting
- [ ] `tests/test_project_organiser.py` — Mock git repo, verify health score calculation and edge cases
- [ ] `tests/test_file_organiser.py` — Mock filesystem (tmpdir), verify all 8 finding types detected
- [ ] `tests/test_retention.py` — Verify purge logic respects retention days, keeps latest per entity
- [ ] `tests/test_routers.py` — Integration tests for key endpoints (status, resources, projects/overview)

### KDE System Tray App — Phase 2+ (Feature)
- [x] Desktop tray icon for KDE Plasma — persistent indicator showing service health at a glance
- [x] Popup stats window — CPU/RAM/disk gauges, active alerts count, scan trigger
- [x] Service status grid in popup (Phase 2)
- [x] KDE desktop notifications on critical alerts (Phase 2)
- [ ] Dev instance manager — start/stop/restart monitored services from tray popup (Phase 3)

### Polish
- [ ] Structured JSON logging (for systemd journal)
- [ ] Request logging middleware (method, path, status, duration)
- [ ] Night Worker integration endpoints
- [ ] GPU monitoring (nvidia-smi parsing)
- [ ] SSL cert expiry checks
