# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-07

---

## Open Issues

_Four open snags. Three were found on 2026-08-07 by the consumer — Alfred now
renders `briefing/preview` daily and is building a page on `/api/projects/board`,
so producer-side content defects have a reader for the first time._

- [P1] SNAG-BRIEF-001: `Project Health` publishes every project ever scanned, including retired ones (2026-08-07)
  - **Symptom**: The section carries **26 rows**, among them `PersonalAssistant`, `PersonalAssistant-auto` and `PA-worktrees` — a project retired 2026-07-24 whose repos are deliberately archived — plus four near-duplicate casings of the same work (`Portfolio` / `portfolio` / `portfolionew`, `BSL-Translator` / `bsl-translator` / `bsl-translation-app`). The same briefing's `Pick This Up` section lists 5 projects and `GET /api/projects/board` returns 6. One payload, three different answers to "what is on this box"
  - **Cause**: [`briefing._build_project_health_section`](../../sysadmin/services/briefing.py) selects the latest snapshot per project with **no status filter and no cap** — it never reads `findings["status"]`. `_build_next_actions_section`, 40 lines below it in the same file, does exactly that filter (`if findings.get("status", "active") != "active": continue`), and so does the board router. The health section predates the `status` declarations added to `projects.yaml` and was never brought forward
  - **Impact**: Directly undoes the highest-leverage line in [monitorable-project.md](../guides/monitorable-project.md) — declaring `status: dormant` is supposed to suppress board rows and staleness nagging at once, and it does everywhere *except* the one section a human actually reads each morning. A consumer cannot repair this: nothing in the section's rows carries status, so Alfred can only render 26 rows or filter by a hardcoded name list
  - **Fix**: Apply the same `status == "active"` filter, and cap the table the way `Pick This Up` is capped. Sorting by score already puts the 100s (all uninformative) first, so a cap without a re-sort would show the least useful rows — worth ranking by score *ascending* or by score-drop-since-last-scan while the filter is in
  - **Note**: 26 → 6 is a large enough drop that the section may stop justifying a table; the honest replacement is probably "3 below threshold" plus the offenders

- [P1] SNAG-BRIEF-002: `Pick This Up` truncates a next action mid-word with no marker (2026-08-07)
  - **Symptom**: venture-assistant's row reads `"Next up → Review the first scoring sample from the 2026-08-06 nightly run: check \`SELECT lens, count(*), … FROM idea_score GROUP BY 1\` for"` — it stops mid-sentence and nothing says so. The board serves the same field at its full 293 characters, so **the same `next_action` has two lengths on two endpoints and the shorter one looks complete**
  - **Cause**: [`briefing._build_next_actions_section`](../../sysadmin/services/briefing.py) does `"next": action[:180]` — a bare slice, no ellipsis, no marker, no word boundary. The board applies no cap at all
  - **Impact**: A truncated action reads as a finished instruction, which is worse than a long one. Alfred's own contract (ADR-0063 §2) requires a visible `… (truncated)` marker and its `sanitise_text` adds one — but only to `text` sections; `table` cells pass through per-key untouched, so this producer-side cut is what reaches the page. A consumer cannot detect it: 180 characters of prose is indistinguishable from prose that happened to be 180 characters
  - **Fix**: Truncate at a word boundary and append a marker, or (better) don't truncate here — cap once at the source in [`roadmap.next_action_from_handoff`](../../sysadmin/services/roadmap.py) so board and briefing agree. The 180 that stays should be a *documented* cap, since [alfred-briefing-integration.md](../guides/alfred-briefing-integration.md) currently promises "one action per project" without saying how long one is

- [P2] SNAG-ROADMAP-001: An unfilled handoff placeholder is published as a real next action (2026-08-07)
  - **Symptom**: Alfred's `Pick This Up` row reads `"No unchecked task found — set one before the next session."` with `source: handoff` — i.e. a template's apology for having no next action is rendered as the next action, at the highest confidence level the honesty field has
  - **Cause**: Two compounding faults in [`roadmap.py`](../../sysadmin/services/roadmap.py). (1) `next_action_from_handoff`'s **first branch — the "next" heading path — never calls `is_placeholder` at all**; the detector is only wired into `first_unchecked_task` (lines 162, 166), which is the *fallback*. The deliberately-signalled path is the unguarded one. (2) Even adding the call there would not catch this line, because `_first_meaningful` strips leading/trailing underscores (`re.sub(r"^_+|_+$", "", line)`) **before** returning, and `_PLACEHOLDER_RES[0]` is `^_.*_$` — the strip removes precisely the marks the rule matches on. Verified: `is_placeholder("_No unchecked task found…_")` → `True`; `is_placeholder(_first_meaningful([same]))` → `False`
  - **Impact**: Narrower than it looks — `~/.claude/hooks/generate-handoff.sh` emits this italic line, so it will recur on every repo whose session ended without an unchecked task, and always with `source: handoff`. That is the value the guide tells consumers to "show plainly — this is the real thing", which is exactly backwards here. The right outcome is the row being **omitted**, which the builder already does for projects with no action
  - **Fix**: Run `is_placeholder` on the raw line before `_first_meaningful` normalises it (or have `_first_meaningful` return both raw and cleaned), and call it on the "next" heading path. Worth adding the generated line's own wording to `_PLACEHOLDER_RES` as a belt-and-braces rule, since it is emitted by a hook this box controls

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
