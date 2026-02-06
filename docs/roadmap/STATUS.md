# Project Status Dashboard

**Last Updated**: 2026-02-06
**Current Phase:** Core service fully implemented — all 4 agents, API, scheduler, DB

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
| Testing | 🟡 Planned | Test suite needed |
| Frontend | ⬜ Not Started | Nuxt pages in PA (future) |

---

## Recently Completed

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
