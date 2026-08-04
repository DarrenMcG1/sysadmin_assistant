# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-04

---

## Open Issues

_From codebase review 2026-07-24. Session 10 and Session 11 items resolved 2026-07-24._

- [P2] SNAG-AGENT-002: Log aggregator raises one alert per error line (2026-07-24)
  - **Symptom**: A single poll over a noisy unit produces dozens of separate alerts — observed live during Session 17 while streaming `/api/sysadmin/events`, where one log_aggregator run emitted alerts continuously
  - **Cause**: The aggregator raises an alert per matched error line rather than grouping by unit + error signature over the poll window
  - **Impact**: Partly masked downstream — Session 16's `NotificationPolicy` coalesces same-poll alerts into one toast and Session 17's SSE queue is bounded — so the user-visible noise is limited, but the `alerts` table still fills with near-duplicate rows and the alerts API/dashboard list is dominated by them
  - **Fix**: Group by unit + normalised message signature within a poll, raise one alert carrying an occurrence count (mirroring the "X flapped N×" pattern Session 16 used for notifications)

---

## Fixed Issues

- [P2] SNAG-CONF-001: `sports_analyser` projects.yaml entry silently dead — **Fixed 2026-08-04**
  - **Symptom**: The managed entry never matched a scanned project, so its health endpoint and per-project settings were never applied — with no error anywhere
  - **Cause**: `path` said `~/projects/sports_analyser` but the directory on disk is `SportsAnalyser`; on a case-sensitive filesystem the path matched nothing, and a managed entry whose path doesn't exist fails silently (same failure shape as the old PA `user:` scope bug)
  - **Fix**: Corrected the path during the 2026-08-04 ~/projects reorganisation (Phase 2). Also removed the orphaned `PA-worktrees` entry (its empty directory was deleted). Follow-up idea: the config loader could warn when a managed project's `path` doesn't exist — that would have surfaced this immediately

- [P1] SNAG-SYSD-001: `systemctl --user` checks always fail from the daemon — **Fixed 2026-07-24**
  - **Symptom**: `/api/sysadmin/status` reported `alfred-evaluate-timer` as **critical** with `details: {'unit': 'alfred-evaluate.timer', 'is_active': False}` while the timer was genuinely `active`/`waiting`. Every `user: true` systemd check was affected, so the Alfred backend/frontend units were equally suspect
  - **Cause**: `systemctl --user` finds the session bus via `XDG_RUNTIME_DIR` (it composes `$XDG_RUNTIME_DIR/bus` itself). `sysadmin.service` is a **system** unit running as `User=gaddi`, and its environment is only `PATH` (`systemctl show sysadmin.service -p Environment`), so every user-scope call died with "Failed to connect to user scope bus via local transport". The old `get_unit_status` ignored the exit code and the stderr, parsed the empty stdout into a dict with no `ActiveState`, and defaulted `is_active` to `False` — a failed *query* was indistinguishable from a dead *unit*. Session 15 added `user: true` and the Alfred migration plumbed it through projects.yaml; both verified in an interactive shell, which always has `XDG_RUNTIME_DIR` set, so neither could see it
  - **Fix**: `sysadmin/utils/systemd.py` builds the subprocess environment centrally (`build_env`), injecting `XDG_RUNTIME_DIR` (defaulting to `/run/user/<os.getuid()>`) for every user-scope call — so the status check, the details endpoint and start/stop/restart are all fixed at once. `DBUS_SESSION_BUS_ADDRESS` is deliberately **not** derived: verified against the live bus that `XDG_RUNTIME_DIR` alone is sufficient. A failed query now raises `SystemdQueryError`/`UserBusUnavailableError` (bus unreachable, non-zero exit, or output with no `ActiveState`) instead of returning a verdict, `_check_systemd` maps that to status `"error"` — which raises no alert and leaves streak counters untouched, unlike `critical`/`unreachable` — and `/services/{name}/details` answers 503 rather than 500. Migration 003 widens `chk_health_status` to permit `'error'`, which `_check_service` could always return but the DB had never allowed. 26 new tests — 21 in a new `tests/test_systemd.py` (which mocks `create_subprocess_exec` and asserts on the environment handed to systemctl, so they hold with no session bus in CI), plus agent-level "unqueryable is `error`, genuinely inactive is still `critical`" cases and the 503 details case. Verified live with both variables unset: `alfred-evaluate.timer` reads `active`

- [P1] SNAG-AGENT-003: Shared `httpx.AsyncClient` reused across event loops — **Fixed 2026-07-24**
  - **Symptom**: `/api/sysadmin/status` reported `llama-server` as **unreachable** with `details: {'error': 'Event loop is closed'}` while `curl http://localhost:8081/health` answered 200 in under a millisecond. `alfred`, `alfred-frontend`, `internet` and `sports_analyser` reported `ok`, so it looked intermittent and host-specific
  - **Cause**: `SysAdminAgent.startup()` created one `AsyncClient` during the FastAPI lifespan, binding it to the API's event loop, but `_execute()` runs on APScheduler threads under `asyncio.run()` — a fresh loop per run, **closed** afterwards. Pooled keep-alive connections therefore referenced a dead loop, and reusing one raised `RuntimeError: Event loop is closed`. Hosts whose pooled connection had already been dropped got a fresh one and looked healthy, hence the per-host presentation. The lazy re-create (`if not self._http_client`) could never help: the client was not `None`, just loop-poisoned
  - **Fix**: New `sysadmin/utils/async_http.py` — `LoopBoundClient` records the loop a long-lived client was built on and lends it out only while that loop is running; anywhere else it yields a short-lived client closed on exit, so nothing crosses a loop and nothing leaks. `SysAdminAgent` now opens one run-scoped pool inside `_execute` (`scoped()`) and its `startup`/`shutdown` are gone. The same audit found two more instances of the pattern: `LLMClient` (opened at lifespan by the log aggregator, then driven from scheduler threads — same latent failure) and `Notifier` (currently reachable only via `briefing.py`, which builds its own per-call instance, so latent only); both now hold a `LoopBoundClient`, and `LogAggregatorAgent` no longer opens an LLM client on the API loop. 7 new tests (`tests/test_async_http.py`) drive a real loopback HTTP server across two successive `asyncio.run()` calls — `httpx.MockTransport` holds no sockets and cannot reproduce this — including a guard test asserting that a naively shared client *does* still raise "Event loop is closed", so the harness is known to be capable of catching a regression

- [P1] SNAG-API-001: Alert ack returns HTTP 200 with malformed body for missing alerts — **Fixed 2026-07-24**
  - **Symptom**: `POST /api/sysadmin/alerts/{id}/ack` on a nonexistent alert returned 200 with body `[{"error": "Alert not found"}, 404]`; callers checking for 404 never saw it
  - **Cause**: Flask-style tuple return in sysadmin/routers/sysadmin.py — FastAPI serialises the tuple as JSON
  - **Fix**: `raise HTTPException(status_code=404, detail="Alert not found")`; grep found no other tuple-return patterns; missing-alert 404 test added in tests/test_routers.py (Session 11)

- [P1] SNAG-API-002: Access-log middleware never excludes the real health endpoint — **Fixed 2026-07-24**
  - **Symptom**: Every tray `/health` poll (every few seconds) logged at INFO — the exact noise the exclusion was built to prevent
  - **Cause**: `_EXCLUDED_PATHS` had `/api/health` (middleware.py) but health router mounts at `/health`; test_logging.py used a throwaway route so the mismatch was invisible
  - **Fix**: Exclusion changed to `/health`; test_logging.py now mounts the real health router and asserts a 200 from it (Session 11)

- [P1] SNAG-API-003: Two endpoints block the event loop with sync psutil calls — **Fixed 2026-07-24**
  - **Symptom**: All concurrent requests stalled — ≥1s freeze on `POST /api/sysadmin/scan-all` (`cpu_percent(interval=1)` via `asyncio.create_task` on the main loop), variable stall on `GET /api/sysadmin/ports`
  - **Cause**: Missing `asyncio.to_thread` — exceptions to the convention followed elsewhere
  - **Fix**: `/ports` handler wraps `get_port_usage()` in `asyncio.to_thread`; `_take_resource_snapshot` moves blocking collection into `_collect_resource_metrics` run via `to_thread` (correct on both scheduler and manual scan-all paths); off-loop assertion tests added (Session 11)

- [P1] SNAG-TRAY-005: Malformed API responses silently freeze tray on stale data — **Fixed 2026-07-24**
  - **Symptom**: Non-JSON body (proxy error page, truncated response) or payload shape change → tray showed stale data indefinitely with no disconnected indication
  - **Cause**: client.py caught only `httpx.HTTPError`/`TimeoutException`/`OSError`; `resp.json()` raises `JSONDecodeError` and `**kwargs` dataclass construction in models.py raises `TypeError`, both uncaught
  - **Fix**: Fetch paths also catch `ValueError`/`TypeError` and mark connection lost; all `**kwargs` `from_dict`s converted to defensive `.get()` style with defaults; malformed-JSON and field-skew tests added (Session 11 — shared Pydantic contracts follow in Session 13)

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
