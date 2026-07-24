# Project Status Dashboard

**Last Updated**: 2026-07-24
**Current Phase:** Feature-complete — maintenance & future features

> **Next up**: Full backlog is Sessions 11–20 in [tasks.md](tasks.md) (ideas inbox emptied 2026-07-24 — everything promoted; Session 10 complete). 4 open SNAGs in [snag_list.md](snag_list.md), fixed by Session 11. Order: 11 (bugs) → 15 (llama.cpp migration; LLM summaries currently silently disabled) → 16 (notification calm) → rest as desired.

---

## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 4 agents + scheduler + DB |
| API | 🟢 Complete | 25+ endpoints across 5 routers |
| Database | 🟢 Complete | 9 tables in sysadmin schema, Alembic migrations |
| Agents | 🟢 Complete | SysAdmin, Project Organiser, File Organiser, Log Aggregator |
| GPU Monitoring | 🟢 Complete | AMD via rocm-smi + sysfs fallback, temp/VRAM alerts |
| Observability | 🟢 Complete | Structured JSON logging + request access logs |
| KDE Tray App | 🟢 Phase 3 Complete | Tray icon + service grid + D-Bus notifications + native dashboard + DND mode + service actions (popup retired 2026-07-24) |
| PA Integration | 🟢 Complete | Summary digest endpoint + v2 notification targeting |
| Testing | 🟢 Complete | 154 backend + 124 tray = 278 total |
| Frontend | 🟢 Complete | Built in PA using sysadmin API endpoints |

---

## Recently Completed

- **2026-07-24 — Session 10: Resolved uncommitted loose ends.** Removed unreachable StatsPopup (dashboard won; SNAG-TRAY-004), `get_last_commit_date` now checks all branches (SNAG-AGENT-001), removed dead `count_stale_branches` and unused `orphan_detection` flag, narrowed `get_repo` exception handling with logging. Promoted codebase-review backlog to Sessions 10-20 in tasks.md.

_See [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for full history._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
