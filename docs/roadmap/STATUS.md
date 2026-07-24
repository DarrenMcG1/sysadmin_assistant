# Project Status Dashboard

**Last Updated**: 2026-07-24
**Current Phase:** Feature-complete — maintenance & future features

> **Next up**: Session 12 (API authentication) in [tasks.md](tasks.md) — Sessions 10–11 complete, 0 open SNAGs in [snag_list.md](snag_list.md). Order: 12 → 15 (llama.cpp migration; LLM summaries currently silently disabled) → 16 (notification calm) → rest as desired.

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
| Testing | 🟢 Complete | 177 backend + 113 tray = 290 total |
| Frontend | 🟢 Complete | Built in PA using sysadmin API endpoints |

---

## Recently Completed

- **2026-07-24 — Session 11: Verified bug fixes.** Alert ack returns a real 404 (SNAG-API-001), access-log exclusion fixed to the real `/health` path with the real router under test (SNAG-API-002), blocking psutil calls moved off the event loop via `asyncio.to_thread` in `/ports` and `_take_resource_snapshot` (SNAG-API-003), tray marks connection lost on malformed/skewed API responses and `from_dict` parsing is defensive (SNAG-TRAY-005). 12 new tests — suite now 290.
- **2026-07-24 — Session 10: Resolved uncommitted loose ends.** Removed unreachable StatsPopup (dashboard won; SNAG-TRAY-004), `get_last_commit_date` now checks all branches (SNAG-AGENT-001), removed dead `count_stale_branches` and unused `orphan_detection` flag, narrowed `get_repo` exception handling with logging. Promoted codebase-review backlog to Sessions 10-20 in tasks.md.

_See [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for full history._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
