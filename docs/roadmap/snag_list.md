# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-07-24

---

## Open Issues

_From codebase review 2026-07-24. Fix session: 11 (bugs) in tasks.md; Session 10 items resolved 2026-07-24._

- [P1] SNAG-API-001: Alert ack returns HTTP 200 with malformed body for missing alerts (2026-07-24)
  - **Symptom**: `POST /api/sysadmin/alerts/{id}/ack` on a nonexistent alert returns 200 with body `[{"error": "Alert not found"}, 404]`; callers checking for 404 never see it
  - **Cause**: Flask-style tuple return at sysadmin/routers/sysadmin.py:294 — FastAPI serialises the tuple as JSON
  - **Fix**: `raise HTTPException(status_code=404, ...)`; add a missing-alert test case

- [P1] SNAG-API-002: Access-log middleware never excludes the real health endpoint (2026-07-24)
  - **Symptom**: Every tray `/health` poll (every few seconds) logged at INFO — the exact noise the exclusion was built to prevent
  - **Cause**: `_EXCLUDED_PATHS` has `/api/health` (middleware.py:17) but health router mounts at `/health`; test_logging.py uses a throwaway route so the mismatch is invisible
  - **Fix**: Exclude `/health` (or mount health under `/api`); test against the real router

- [P1] SNAG-API-003: Two endpoints block the event loop with sync psutil calls (2026-07-24)
  - **Symptom**: All concurrent requests stall — ≥1s freeze on `POST /api/sysadmin/scan-all` (`cpu_percent(interval=1)` via `asyncio.create_task` on the main loop), variable stall on `GET /api/sysadmin/ports`
  - **Cause**: Missing `asyncio.to_thread` — exceptions to the convention followed elsewhere
  - **Fix**: Wrap `get_port_usage()` and `_take_resource_snapshot` in `asyncio.to_thread`

- [P1] SNAG-TRAY-005: Malformed API responses silently freeze tray on stale data (2026-07-24)
  - **Symptom**: Non-JSON body (proxy error page, truncated response) or payload shape change → tray shows stale data indefinitely with no disconnected indication
  - **Cause**: client.py catches only `httpx.HTTPError`/`TimeoutException`/`OSError`; `resp.json()` raises `JSONDecodeError` and `**kwargs` dataclass construction in models.py raises `TypeError`, both uncaught
  - **Fix**: Catch `ValueError`/`TypeError` (emit `connection_lost`); convert fragile `from_dict`s to defensive `.get()` style

---

## Fixed Issues

- [P1] SNAG-TRAY-004: StatsPopup unreachable after dashboard cutover but still live — **Fixed 2026-07-24**
  - **Symptom**: Tray click opens dashboard; compact popup could never be shown, yet processed every poll update and kept a global Qt event filter installed for the app's lifetime
  - **Cause**: Both `popup_requested` and `dashboard_requested` wired to `_open_dashboard`; `_toggle_popup` connected to nothing — half-finished migration
  - **Fix**: Removed popup.py and the popup-only ActionBar widget entirely; left click opens the dashboard, scan feedback lives in the dashboard tabs (Session 10)

- [P2] SNAG-AGENT-001: Project staleness scored from HEAD only, not all branches — **Fixed 2026-07-24**
  - **Symptom**: Project parked on old `main` with active feature branches flagged stale; could fire a false critical-health alert
  - **Cause**: `get_last_commit_date` walked HEAD despite docstring saying "any branch" (sysadmin/utils/git.py)
  - **Fix**: `max()` of `committed_datetime` across all local branches, HEAD fallback for detached/branchless repos; covered by tests/test_git_utils.py (Session 10)

_Earlier fixes archived — see [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for SNAG-TRAY-001/002/003._

---

## Creating New SNAGs

**Naming**: `SNAG-###` or use domain prefixes like `SNAG-WEB-###`, `SNAG-API-###`, `SNAG-DB-###`

**Priority levels:**
- `[P0]` - Critical: Blocks users or causes data loss
- `[P1]` - High: Important functionality broken
- `[P2]` - Medium: Workaround exists

**Format:**
```markdown
- [P1] SNAG-WEB-001: Brief description (YYYY-MM-DD)
  - **Symptom**: What the user sees
  - **Cause**: Root cause (if known)
  - **Fix**: What was done to fix it (when resolved)
```
