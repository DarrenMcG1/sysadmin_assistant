# Completed Work Archive — up to 2026-03-23

## Sessions 1–9: Full Service + Tray App

All sessions completed on `main` branch.

### Session 1: Project skeleton & bootable service
- pyproject.toml, config.yaml, Pydantic config validation
- Async SQLAlchemy engine with search_path for sysadmin schema
- 9 SQLAlchemy models + Alembic migration
- FastAPI app with lifespan + /health endpoint
- systemd unit + install scripts

### Session 2: BaseAgent, Scheduler, Event Bus & SysAdmin Agent
- APScheduler wrapper with async bridge
- Event bus (pub/sub)
- BaseAgent ABC with run tracking + alert system
- SysAdmin agent (HTTP/TCP/systemd checks, psutil resources)
- SysAdmin router (status, resources, alerts, ports)

### Session 3: Alerting, Notifier & PA Integration
- Notifier service (POST to PA with retries)
- Briefing service (collects from all agents)
- Briefing preview endpoint

### Session 4: Project Organiser Agent
- Git utility helpers (branches, staleness, remotes)
- Project discovery + health scoring
- Projects router (overview, detail, TODOs, branches, stale, report)

### Session 5: File Organiser Agent
- Ported home_audit.py into agent framework
- 8 filesystem checks with DB storage
- Files router (status, report, delta, duplicates, large, misplaced, trends, clean)

### Session 6: Log Aggregator & LLM Summarisation
- journalctl reader with severity mapping
- Ollama client for LLM summarisation
- Log aggregator agent (poll + summarise)
- Logs router (recent, errors, summary, history, stats, by-source)

### Session 7: Retention, Integration & Polish
- Retention service (daily purge at 03:00)
- Full integration of all agents into main.py
- scan-all trigger endpoint, CORS + error handling middleware

### Session 8: KDE System Tray App — Phase 1
- `sysadmin_tray/` sub-package (11 source files)
- Tray icon with green/amber/red/grey state (programmatic QPainter)
- Threaded API client (QThread + httpx, no async)
- Frameless popup: CPU/RAM/disk gauges, alert badges, action bar
- Config layering: reads shared config.yaml + CLI overrides
- 39 unit tests

### Session 9: KDE System Tray App — Phase 2
- Service status grid in popup (coloured dots, name, status, response time)
- D-Bus desktop notifications (with bug fixes: SNAG-TRAY-001/002/003)
- Native dashboard window (Overview, Services, Logs, Projects tabs)

---

## Feature Work (2026-02–03)

### DND Mode & Notification Control (2026-03-06)
- `notifications` config section (desktop/PA severity thresholds, DND schedule)
- DndManager service: schedule evaluation, manual override (tri-state), critical breakthrough
- GET/POST `/api/sysadmin/dnd`, tray menu integration

### Service Controllable Flag & Auto-Restart (2026-03-23)
- `controllable` field on MonitoredService, 403 gating on service actions
- Auto-restart after N consecutive failures for controllable systemd services
- Tray UI hides action buttons for non-controllable services

### Backend Test Suite (2026-03-06 + 2026-03-23)
- 134 backend tests across 9 test files
- 124 tray tests → 258 total

### Structured JSON Logging & Request Middleware (2026-03-23)
- JSON formatter for systemd journal, text fallback for dev
- Request access log: method, path, status, duration_ms

### Night Worker Integration Endpoints (2026-03-23)
- `/api/logs/recent` — raised limits, severity=all, offset pagination
- `/api/sysadmin/resources/history` — days param, disk_usage in response
- `/api/files/trends` — linear growth rate forecast, milestone projections

### AMD GPU Monitoring (2026-03-23)
- `sysadmin/utils/gpu.py` — rocm-smi JSON parsing with sysfs fallback
- Threshold alerts: gpu_temp_warning_c, gpu_vram_warning_percent

---

## Fixed Bugs

| ID | Summary | Fixed |
|----|---------|-------|
| SNAG-TRAY-001 | Tray crash: missing @pyqtSlot decorators for D-Bus handlers | 2026-02-13 |
| SNAG-TRAY-002 | D-Bus Notify signature mismatch (UINT32 + array-of-string) | 2026-02-13 |
| SNAG-TRAY-003 | Notification spam: dedup by content fingerprint | 2026-02-13 |
