# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-05

---

## Open Issues

_One open snag. Everything else from the 2026-07-24 codebase review is fixed and archived._

- [P2] SNAG-AGENT-002: Log aggregator raises one alert per error line (2026-07-24)
  - **Symptom**: A single poll over a noisy unit produces dozens of separate alerts — observed live during Session 17 while streaming `/api/sysadmin/events`, where one log_aggregator run emitted alerts continuously
  - **Cause**: The aggregator raises an alert per matched error line rather than grouping by unit + error signature over the poll window
  - **Impact**: Partly masked downstream — Session 16's `NotificationPolicy` coalesces same-poll alerts into one toast and Session 17's SSE queue is bounded — so the user-visible noise is limited, but the `alerts` table still fills with near-duplicate rows and the alerts API/dashboard list is dominated by them
  - **Fix**: Group by unit + normalised message signature within a poll, raise one alert carrying an occurrence count (mirroring the "X flapped N×" pattern Session 16 used for notifications)
  - **Owned by [Session 27](tasks.md)** (promoted 2026-08-05) — the same signature fingerprinting this fix needs is also Tier 1 of the log-aggregator tiers, so the two are deliberately done together rather than the snag being patched twice

---

## Fixed Issues

_All SNAGs fixed to date are archived — nothing outstanding is hidden here._

| SNAG | Title | Fixed |
|---|---|---|
| SNAG-CONF-001 | `sports_analyser` projects.yaml entry silently dead (wrong-case path) | 2026-08-04 |
| SNAG-SYSD-001 | `systemctl --user` checks always fail from the daemon (missing `XDG_RUNTIME_DIR`) | 2026-07-24 |
| SNAG-AGENT-003 | Shared `httpx.AsyncClient` reused across event loops | 2026-07-24 |
| SNAG-API-001 | Alert ack returned 200 with a malformed body for missing alerts | 2026-07-24 |
| SNAG-API-002 | Access-log middleware never excluded the real health endpoint | 2026-07-24 |
| SNAG-API-003 | Two endpoints blocked the event loop with sync psutil calls | 2026-07-24 |
| SNAG-TRAY-005 | Malformed API responses silently froze the tray on stale data | 2026-07-24 |
| SNAG-TRAY-004 | StatsPopup unreachable after dashboard cutover but still live | 2026-07-24 |
| SNAG-AGENT-001 | Project staleness scored from HEAD only, not all branches | 2026-07-24 |

Full symptom/cause/fix write-ups:
[archive/completed_2026-08-05.md](archive/completed_2026-08-05.md) (2026-07-24 → 2026-08-04) ·
[archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) (SNAG-TRAY-001/002/003)


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
