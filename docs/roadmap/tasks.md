# Tasks & Sessions

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [snag_list.md](snag_list.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-02-06

---

## Active Sessions

_No active sessions._

---

## Completed Sessions

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

- [ ] Test suite (pytest fixtures, agent mocks, endpoint tests)
- [ ] Structured JSON logging
- [ ] Request logging middleware
- [ ] Night Worker integration endpoints
- [ ] GPU monitoring (nvidia-smi)
- [ ] SSL cert expiry checks
