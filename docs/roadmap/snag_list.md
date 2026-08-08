# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-08

---

## Open Issues

_Eighteen open snags, plus SNAG-SYSD-002 found and fixed on 2026-08-08. `SNAG-ROADMAP-003` was found on 2026-08-08 while
writing the `.project.yaml` manifests: three handoff conventions exist across
the estate and the scanner reads two of them. Three were found on 2026-08-07 by the consumer — Alfred now
renders `briefing/preview` daily and is building a page on `/api/projects/board`,
so producer-side content defects have a reader for the first time. Twelve more
(`SNAG-PROJ-001`…`012`) came from the project-organiser capability audit of the
same day; none were fixed during the audit, and all are owned by
[Session 34](tasks.md)._

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

- [P3] SNAG-SYSD-002: `kind: timer` recorded nothing, because the properties it reads were never requested (2026-08-08, fixed same day)
  - **Symptom**: Every `kind: timer` check returned `ok` with `last_run_recorded: false` and no `last_run`, `next_run` or `last_result`, for timers that had demonstrably fired — `alfred-evaluate.timer` last triggered 08:00 that morning. The check was not failing; it was recording nothing, and reporting success while doing so
  - **Cause**: [`_timer_facts`](../../sysadmin/monitor/agent.py) reads `LastTriggerUSec`, `NextElapseUSecRealtime` and `Result` out of whatever [`get_unit_status`](../../sysadmin/monitor/systemd.py) returns, and `get_unit_status` asks `systemctl show` for a **fixed property list** that contained none of them. The two modules agreed only by accident and had never agreed at all — the feature shipped inert in Phase 3
  - **Impact**: Narrow in effect, wide in lesson. Six timers were affected and none reported wrongly, they simply reported less than intended, so nothing looked broken. **The failure mode is the point**: a check that records nothing looks identical to a check that records nothing worth mentioning, which is the same shape as the dead `projects.yaml` paths this session exists to eliminate. It survived unit tests because those mock `get_unit_status` and supply the properties the assertions expect — the mock was the specification, and the real function had never been asked
  - **Fix**: Requested the three properties for every unit (systemctl omits inapplicable ones, so it costs nothing and avoids a second subprocess for the estate's six timers; `Result` is meaningful for services too, being how a oneshot reports its last outcome). Added a test asserting every property `_timer_facts` reads appears in `get_unit_status`'s request list — the coupling itself is now checked, rather than only the behaviour on a mock that satisfies it
  - **Found**: while installing `sysadmin-organiser.timer` and verifying it end to end rather than assuming, which is the step [monitorable-project.md](../guides/monitorable-project.md) requires and the only reason this surfaced

- [P2] SNAG-ROADMAP-003: Three handoff conventions exist on this box; the scanner knows two, and prefers the wrong one twice (2026-08-08)
  - **Symptom**: `HANDOFF_PATHS` in [`roadmap.py`](../../sysadmin/projects/roadmap.py) is `("docs/sessions/handoff.md", "docs/roadmap/handoff.md")`. The estate actually uses **four** locations. `venture-assistant` keeps a **6,044-byte `HANDOFF.md` at its root** (2026-08-07) and `ImbaBots` a **141,096-byte `docs/handoff.md`** (2026-08-07); neither path is a candidate, so neither file is ever read. Both repos *also* carry a `docs/sessions/handoff.md` of 851 and 882 bytes — the SessionEnd hook's generated stub — and that is the file the scanner picks up. **The next action for two active projects is derived from an 850-byte stub while a 6 KB and a 141 KB record sit unread beside it**
  - **Cause**: Two separate faults. (1) The candidate tuple is incomplete — `HANDOFF.md` and `docs/handoff.md` are both real shapes in the wild and neither is listed. (2) `_read` returns **the first candidate that reads**, which makes precedence a function of tuple order rather than of which document is current. `Alfred` has both listed candidates: `docs/sessions/handoff.md` (815 B, 2026-08-07) wins over `docs/roadmap/handoff.md` (3,150 B, 2026-07-11). That one happens to be right, by luck of ordering rather than by rule
  - **Impact**: Reaches every consumer of `next_action` — the board, `Pick This Up` in the briefing, `GET /api/projects/actions`, and the planned `GET /api/projects/next`. It compounds `SNAG-ROADMAP-001`: the stub the scanner prefers is exactly the file that carries the unfilled-placeholder line, so the two faults together publish a template's apology while the real handoff is invisible. `ImbaBots`'s 141 KB `docs/handoff.md` is an append-log, which is the shape [Session 32](tasks.md) is blocked on wanting
  - **Fix**: Add `HANDOFF.md` and `docs/handoff.md` to the candidates, then **stop letting tuple order decide**: when more than one candidate exists, pick by modification time and record the also-rans, so a repo with two handoffs is a reportable finding rather than a silent choice. The comment above `HANDOFF_PATHS` claims "Alfred keeps its handoff in `docs/roadmap/`" — Alfred now has both and the scanner reads the other one, so the comment is stale and should go with the fix
  - **Note**: The duplicates are worth resolving on the estate side too, but that is 3 repos' housekeeping and separate from the scanner accepting what is there. Raised by the estate owner on 2026-08-08

- [P2] SNAG-ROADMAP-002: `count_open_snags` miscounts a document that groups or cross-references its snags (2026-08-07)
  - **Symptom**: Two independent miscounts, both found while filing the twelve entries below. (1) A `###` sub-heading *inside* `## Open Issues` hid every snag under it — the count read 4 when 16 were open. (2) Once that was fixed the count read **21 for 16 snags**, because five nested `- **Cause**:` bullets happened to mention another snag's id
  - **Cause**: [`_sections`](../../sysadmin/services/roadmap.py#L79) splits on **any** heading level and returns a flat list, so a `###` under a `##` ends the parent section rather than nesting inside it; and `_SNAG_LINE_RE` is `^\s*[-*]\s+.*\bSNAG-[A-Z]+-\d+`, whose leading `\s*` makes an indented detail bullet indistinguishable from a top-level entry
  - **Impact**: `open_snags` reaches `GET /api/projects/board`, the briefing and `claude-preflight.sh`. Both directions are wrong in the dangerous way — grouping *hides* open bugs, cross-referencing *inflates* them — and neither is visible to the author, who sees a correct-looking document. This file is currently written around the parser rather than the parser matching the format
  - **Fix**: Nest sections by heading depth (a `###` under an "open" `##` inherits it), and require the id on an unindented bullet — or count entries by the `[P0]`/`[P1]`/`[P2]` marker, which only ever appears on a real entry line. Add a fixture covering both shapes: a grouped open section, and an entry whose sub-bullets name other snags
  - **Note**: the same `_sections` flattening governs `next_action_from_handoff` and `first_unchecked_task`, so a handoff using sub-headings under `## Next` is exposed to the first half of this

- [P2] SNAG-AGENT-002: Log aggregator raises one alert per error line (2026-07-24)
  - **Symptom**: A single poll over a noisy unit produces dozens of separate alerts — observed live during Session 17 while streaming `/api/sysadmin/events`, where one log_aggregator run emitted alerts continuously
  - **Cause**: The aggregator raises an alert per matched error line rather than grouping by unit + error signature over the poll window
  - **Impact**: Partly masked downstream — Session 16's `NotificationPolicy` coalesces same-poll alerts into one toast and Session 17's SSE queue is bounded — so the user-visible noise is limited, but the `alerts` table still fills with near-duplicate rows and the alerts API/dashboard list is dominated by them
  - **Fix**: Group by unit + normalised message signature within a poll, raise one alert carrying an occurrence count (mirroring the "X flapped N×" pattern Session 16 used for notifications)
  - **Owned by [Session 27](tasks.md)** (promoted 2026-08-05) — the same signature fingerprinting this fix needs is also Tier 1 of the log-aggregator tiers, so the two are deliberately done together rather than the snag being patched twice

**Project organiser — capability audit, 2026-08-07.** _Twelve defects found in
one pass over the project side and deliberately left unfixed so the audit
stayed an audit. Every one of them corrupts output Alfred already consumes, so
they are ordered before the structural work in [Session 35](tasks.md): building
a briefing envelope on top of wrong data only makes the wrong data better
formatted. Kept under this heading rather than a `###` sub-heading on purpose —
`roadmap._sections` splits on any heading level, so a sub-heading would hide
all twelve from `count_open_snags` and from preflight._

- [P1] SNAG-PROJ-001: the board's freshness filter is applied on one route out of eight (2026-08-07)
  - **Symptom**: A project whose directory has been deleted is still reported by `/overview`, `/stale`, `/report`, `/actions`, `/api/summary`, `_build_project_section` and `_build_next_actions_section`. `GET /api/projects/board` is the only surface that drops it
  - **Cause**: The board filters snapshots older than `newest_scan − 1h` ([`projects.py:400-416`](../../sysadmin/routers/projects.py#L400-L416)) *after* calling `_latest_snapshot_query`. Four of the other seven call sites do not use `_latest_snapshot_query` at all — they open-code the latest-per-name query, so there is no single place the filter could have been inherited from
  - **Impact**: Eight surfaces, at least two answers to "what is on this box". Same class as the `Project Health` defect above — a consumer cannot repair it, because nothing in the rows says the directory is gone
  - **Fix**: Move the cutoff **into the shared query** and route all eight call sites through it. Do not repeat the filter seven times — that is the shape the defect already has

- [P2] SNAG-PROJ-002: a deleted project still contributes to `average_active_score` (2026-08-07)
  - **Symptom**: The weekly project review's headline average includes projects that no longer exist on disk
  - **Cause**: `project_review.gather_review_data` selects the latest snapshot per name with no freshness filter — the previous entry's defect, at a call site outside the router
  - **Fix**: Same shared query. Listed separately because it is a separate call site in a separate module, and fixing the router alone would leave it

- [P1] SNAG-PROJ-003: the project organiser never resolves its own alerts (2026-08-07)
  - **Symptom**: **1,664 unresolved alert rows** live, 326 of them sharing one title. Every six-hourly scan re-raises for every project under threshold
  - **Cause**: `ProjectOrganiserAgent` never calls `BaseAgent.resolve_alerts`, though [`sysadmin_agent.py:268`](../../sysadmin/agents/sysadmin_agent.py#L268) and [`service_discovery.py:175`](../../sysadmin/agents/service_discovery.py#L175) both do
  - **Impact**: Unbounded, not merely noisy — retention purges **resolved** alerts only, so not one of these rows will ever expire. The alerts API and the tray's alert list are dominated by them
  - **Fix**: Call `resolve_alerts` on the recovery path, matching the title pattern the raise uses. The other two agents are the working reference

- [P2] SNAG-PROJ-004: the 1,664 existing rows will not clear themselves once resolution works (2026-08-07)
  - **Symptom**: Fixing the entry above resolves alerts raised *after* the fix. The backlog stays
  - **Cause**: `resolve_alerts` acts on the current scan's recovered projects; a historic row for a project that is currently still under threshold is not a recovery
  - **Fix**: Decide deliberately — a one-off backfill marking pre-fix rows resolved, or a dated migration, or leave them and let the retention purge take them once they are resolvable. **Do not ship the resolution fix without settling this**, or the table's size becomes permanent

- [P1] SNAG-PROJ-005: the project review hands the model its figures and asks it not to use them (2026-08-07)
  - **Symptom**: `build_review_prompt` for the project review passes scores, deltas, totals and recommendation point values into the prompt, relying on `REVIEW_INSTRUCTIONS` to tell the model not to restate them
  - **Cause**: The disk review was rebuilt figure-free by construction on 2026-08-06; the project review, which is the older of the two, was never brought into line
  - **Impact**: This exact approach is **recorded in CLAUDE.md as verified to fail**. Given "25.0 GB across 50 directories" plus an explicit "do not restate figures", dria-agent-a-3b restated them and published the quotient "each consuming 5GB". Instructing a model not to use a number it can see is a request; not showing it one is a constraint
  - **Fix**: Bands, phrases and directions in the prompt; every real figure in `build_facts_section`, prepended deterministically. Port the disk review's guard test — no digit reaches the model outside API paths

- [P2] SNAG-PROJ-006: `GET /api/projects/stale` declares a `days` parameter it never reads (2026-08-07)
  - **Symptom**: [`projects.py:92`](../../sysadmin/routers/projects.py#L92) declares `days: int = Query(default=30, le=365)`; the handler filters on `health_score < grade_bands.needs_attention_min` and never references `days`. The endpoint answers "which projects score badly", whatever the caller asks for
  - **Cause**: The parameter documents an intent the implementation dropped. It has no `response_model`, no contract-registry entry and no known consumer
  - **Fix**: Implement the parameter or delete the endpoint. Deletion is the honest default given no consumer exists — but check Alfred first, since a 404 is worse than a wrong answer

- [P2] SNAG-PROJ-007: `HACK` and `XXX` cost health-score points and appear in no column (2026-08-07)
  - **Symptom**: A project with 40 `HACK` markers is penalised for all 40; `todo_count` and `fixme_count` both read 0, so nothing on any surface explains the deduction
  - **Cause**: [`project_organiser.py:258-259`](../../sysadmin/agents/project_organiser.py#L258-L259) records `todos["TODO"]` and `todos["FIXME"]` only, while the penalty is `sum(todos.values())` over all four configured `todo_patterns`
  - **Fix**: Either store the full mapping (a `todos` JSON column beside the two counts) or penalise only what is recorded. Deductions on this service are attributable by design — an unexplained one breaks the rule the three scorers share

- [P2] SNAG-PROJ-008: the TODO scan counts a project's own roadmap documents (2026-08-07)
  - **Symptom**: `snag_list.md`, `tasks.md` and this very file count towards their own repository's TODO penalty. Writing up a snag lowers the score
  - **Cause**: The scan includes `*.md`, and the patterns carry no word boundary — so `TODOS`, `TODO_LIST` and a prose sentence containing "TODO" all match
  - **Fix**: Exclude `*.md` (or at least `docs/roadmap/`), and anchor the patterns with `\b`. The markers are a *code* signal; counting them in documentation inverts the incentive the score is supposed to create

- [P2] SNAG-PROJ-009: `_count_todos`'s cap is per file, and its docstring says otherwise (2026-08-07)
  - **Symptom**: [`project_organiser.py:354`](../../sysadmin/agents/project_organiser.py#L354) documents "Capped at 1000 matches"; `-m 1000` is grep's **per-file** limit, so a repo with 300 files can return 300,000
  - **Fix**: Fix the cap or the docstring — and prefer fixing the cap, since the number reaching the score is the one that matters. Note the interaction with the entry above: excluding `*.md` lowers the counts that make the cap load-bearing

- [P2] SNAG-PROJ-010: `project_reviews` is never purged (2026-08-07)
  - **Symptom**: Four rows today, growing one per week, forever
  - **Cause**: The table is in neither `retention_config` nor `TABLE_TIMESTAMP_MAP` in [`retention.py`](../../sysadmin/services/retention.py). `disk_reviews` (migration 005) should be checked at the same time — it was added by the same pattern
  - **Fix**: Add both to the map with a retention window chosen for *review* data, not check data. A weekly narrative is worth keeping far longer than 30 days of health checks

- [P2] SNAG-PROJ-011: three places document `archived` as waiving git hygiene generally (2026-08-07)
  - **Symptom**: `_analyse_project`'s docstring, [`projects.yaml:173`](../../projects.yaml#L173) and [`config.py:404`](../../sysadmin/config.py#L404) all describe archived projects as exempt from git hygiene. They are not: `archived` waives the **stale-branch deduction only**, and a `.git/index.lock` still costs an archived project 5 points
  - **Fix**: Correct all three to name the single deduction that is waived. Documentation-only — the behaviour is defensible, the description is not

- [P2] SNAG-PROJ-012: archived alert suppression is absolute but documented as conditional (2026-08-07)
  - **Symptom**: The docs read as though an archived project can still alert at a low enough score. It cannot, under any score
  - **Cause**: `_effective_threshold` returns `0` for archived, and the score is clamped with `max(0, …)`, so the alert condition is `score < 0` — unreachable by construction
  - **Fix**: Document it as absolute. Worth keeping the mechanism as-is: a threshold of 0 is a clearer expression of "never alert" than a special case, provided the guarantee is written down and tested

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
