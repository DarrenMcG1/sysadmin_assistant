# Snag List

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [ideas.md](ideas.md)
>
> **Last Updated**: 2026-08-11

---

## Open Issues

_Six open snags, plus three found and fixed the same day and left in place for
the write-up (`SNAG-SYSD-002` on 2026-08-08, `SNAG-DB-001` on 2026-08-10,
`SNAG-CFG-001` on 2026-08-11) — `count_open_snags` therefore reports 9, which is
the entries listed rather than the entries outstanding, and is itself an
instance of `SNAG-ROADMAP-002`.
`SNAG-PROJ-013` was found by Session 32 on 2026-08-11: the momentum endpoint
cannot see a session in a repository that never dates its handoff.
`SNAG-CFG-001` was found by Session 31, which needed to know which severity is
audible and found that the obvious knob is not the one; the fix turned out to
be a whole dead notification path rather than a stale key. The twelve
`SNAG-PROJ-*` entries from the 2026-08-07 project-organiser capability audit
were **all cleared by [Session 34](tasks.md) on 2026-08-10** and are archived
below with their fix dates. `SNAG-ROADMAP-003` — found 2026-08-08 while writing
the `.project.yaml` manifests — was **fixed on 2026-08-10 (Session 37)** along
with the SessionEnd hook that had been generating the stubs it preferred. The
`BRIEF`/`ROADMAP` entries were
found on 2026-08-07 by the consumer — Alfred now renders `briefing/preview`
daily and is building a page on `/api/projects/board`, so producer-side content
defects have a reader for the first time._

- [P0] SNAG-DB-001: the live database was a migration behind, and it caused a **39-hour monitoring blackout** nobody saw (2026-08-10, fixed same day)
  - **Symptom**: **Zero rows were written to `service_health` between 2026-08-08 17:34:54 and 2026-08-10 09:07:25.** Not degraded — absent. `/api/sysadmin/status`, the tray grid and reliability scoring were all serving from a table that had stopped receiving data a day and a half earlier
  - **Cause, in three parts, each individually survivable**:
    1. `alembic current` reported **008** while the repository head was 009. Migration 009 — which adds `'skipped'` to `chk_health_status` — was written and committed on 2026-08-08 (Session 35 Phase 3) and never applied. **Nothing applies migrations**: no script, no `ExecStartPre`, no CI step. It is a manual `uv run alembic upgrade head` a human has to remember
    2. `sysadmin.service` restarted at 17:36:31 on 2026-08-08, two minutes after the last successful check, and picked up the new `services.yaml`. `venture-chat-large` is declared `kind: static` with `monitor: false`, which records `skipped` — the exact value the un-applied migration was meant to permit
    3. **One rejected row killed all nineteen.** `SysAdminAgent._execute` `session.add`s every service's result into one session and `BaseAgent.run` commits once, so the `CheckViolationError` on `venture-chat-large` aborted the whole transaction. A single deliberately-unmonitored service took the entire health check down with it
  - **Why nothing noticed**: the daemon logged `agent_run_failed` on every run — **29 times today alone**, once every five minutes from 06:37 to 09:02 — and nothing reads those. The alerting path is the thing that broke, so it could not report its own failure. `verify_connection` checks that the database answers, not that it is the schema this code was written for. The schema drift guard connects to the live database and would not have caught it either: it explicitly skips `alembic_version`, and `compare_metadata` does not diff CHECK constraints — verified 2026-08-10 by restoring the pre-009 constraint inside a rolled-back transaction and getting an empty diff, with the model declaring `'skipped'` and the database rejecting it
  - **Impact**: ~39.5 hours wall clock, of which roughly **18 hours the daemon was up and failing every five minutes** (the box was asleep for the rest). No health history, no alerts, no reliability data. `GET /api/services/reliability` computes live from `service_health`, so it scored the estate off a table with a day-and-a-half hole in it
  - **Fixed**: `uv run alembic upgrade head` on 2026-08-10 applied 009, 010 and 011. Checks resumed at 09:07:25, first `skipped` row written successfully. **This was found by accident** — while tracing why the drift guard had stayed green, not by anything designed to catch it
  - **The detection gap is still open**, and is the real defect. Three things are missing, in order of value: (1) a startup check comparing `alembic_version` against the packaged head, failing loudly rather than serving against a schema it does not match; (2) per-service write isolation, or at minimum a savepoint, so one bad row cannot cost the other eighteen their check; (3) an alert when an agent's runs fail consecutively — `agent_runs` records every failure and nothing reads it. See [tasks.md](tasks.md)

- [P2] SNAG-PROJ-013: `ImbaBots` heads its handoff with no ISO date, so the Stop hook will block its next code session (2026-08-11)
  - **Filed first with the wrong diagnosis, corrected the same day.** The original entry read "commits without ever moving its handoff date — either the hook is not firing there or that work is not done through Claude Code sessions", and both alternatives are false. Recorded rather than quietly rewritten, because the mistake was to reason from an endpoint's output instead of opening the repository
  - **What is actually true**: ImbaBots' last session is `edbd8c2` (2026-08-07 12:03), which changed 22 `game/` files **and** `docs/handoff.md` in one commit — the habit was kept. `HANDOFF.md`'s mtime is still that timestamp because nothing has run there since. The only later commit, `7144fc5` on 2026-08-10, is the estate migration promoting `docs/handoff.md` to the root, run from *this* repository. ImbaBots' first scan in the momentum window falls after 12:03 on 2026-08-07, so that date is its **baseline** — a state, not a transition — and `sessions: 0` is the correct reading, not a measurement failure
  - **The residual defect is smaller and elsewhere**: the first heading is `# Handoff — M5 (Tier 2) · ⚠ …` with no `YYYY-MM-DD`. `~/.claude/hooks/require-handoff.sh` greps the first heading for today's date, so **the next code-changing session in ImbaBots will be blocked until someone adds one** — the hook cannot be satisfied by the document as it stands. Secondarily, an undated heading means `handoff_date_source` is permanently `mtime` there, so every session ImbaBots ever contributes reads `unverified`
  - **Fix**: add an ISO date to ImbaBots' `HANDOFF.md` first heading. One line, in another repository, and it resolves both halves. **Not** a change to this codebase: the `commits_without_sessions` field considered in the original entry would have been a contract widened to describe a defect that does not exist

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

- [P2] SNAG-ROADMAP-002: `count_open_snags` miscounts a document that groups or cross-references its snags (2026-08-07)
  - **Symptom**: Two independent miscounts, both found while filing the twelve entries below. (1) A `###` sub-heading *inside* `## Open Issues` hid every snag under it — the count read 4 when 16 were open. (2) Once that was fixed the count read **21 for 16 snags**, because five nested `- **Cause**:` bullets happened to mention another snag's id
  - **Cause**: [`_sections`](../../sysadmin/services/roadmap.py#L79) splits on **any** heading level and returns a flat list, so a `###` under a `##` ends the parent section rather than nesting inside it; and `_SNAG_LINE_RE` is `^\s*[-*]\s+.*\bSNAG-[A-Z]+-\d+`, whose leading `\s*` makes an indented detail bullet indistinguishable from a top-level entry
  - **Impact**: `open_snags` reaches `GET /api/projects/board`, the briefing and `claude-preflight.sh`. Both directions are wrong in the dangerous way — grouping *hides* open bugs, cross-referencing *inflates* them — and neither is visible to the author, who sees a correct-looking document. This file is currently written around the parser rather than the parser matching the format
  - **Fix**: Nest sections by heading depth (a `###` under an "open" `##` inherits it), and require the id on an unindented bullet — or count entries by the `[P0]`/`[P1]`/`[P2]` marker, which only ever appears on a real entry line. Add a fixture covering both shapes: a grouped open section, and an entry whose sub-bullets name other snags
  - **Note**: the same `_sections` flattening governs `next_action_from_handoff` and `first_unchecked_task`, so a handoff using sub-headings under `## Next` is exposed to the first half of this

- [P2] SNAG-CFG-001: `notifications.desktop.min_severity` was read by nothing, and looked exactly like the knob that decides whether an alert speaks (2026-08-11, **fixed same day**)
  - **Symptom**: `config.yaml` carries `notifications.desktop: {enabled: true, min_severity: warning}` and `sysadmin/core/config.py` validates it through `DesktopNotificationsConfig`. **No module reads `config.notifications.desktop`** — verified by grep across `sysadmin/`, which finds the section's siblings (`.dnd` in `monitor/dnd.py`, `.pa_notify` and `.tray.mute_services` in `monitor/notifier.py` and `monitor/reliability_history.py`) and never `.desktop`. The setting that actually gates a desktop toast is **`tray.notify_min_severity`** in the separate top-level `tray:` section, parsed by `sysadmin_tray/config.py`, which the tray reads out of the same file
  - **Cause**: The backend used to own desktop notification and handed the job to the tray in Phase 3 (popup retired 2026-07-24). The producer moved; its configuration did not, and the tray brought its own key rather than adopting the existing one. Both currently read `warning`, so the two have never disagreed and nothing has ever surfaced the redundancy
  - **Impact**: Latent, and of the shape this repository keeps finding — a control that is *requested* but not *enforced*. Lowering `notifications.desktop.min_severity` to `info` changes nothing, and raising it to `critical` silences nothing; a reader tuning notification loudness edits the plausible knob and concludes the setting does not work. Found on 2026-08-11 while writing Session 31's idle nudges, whose whole ladder is designed around *which* severity is audible — three comments were written naming the wrong knob before the grep was run
  - **The defect was larger than the key.** `Notifier.send_notification` — the only method that had ever consulted this section — has **no production caller**: grep finds it in `tests/test_notifier.py` and nowhere else. `Notifier` is instantiated in `main.py`, started in the lifespan and attached to `app.state`, and nothing ever asks it to send an alert. `BaseAgent.raise_alert`'s own docstring says "the notifier service should be called separately" and `monitor/agent.py` says criticals are "to be picked up by notifier"; neither ever happened. The dead key was one symptom of a notification path that had been dead since it was written
  - **Fixed 2026-08-11** by giving the daemon a real notifier rather than deleting the config: `sysadmin/monitor/desktop.py` subscribes to `alert.raised` on the existing event bus and sends via `notify-send`. It is the tray's **understudy** — silent whenever the tray has polled `/api/sysadmin/alerts` within `tray_grace_seconds` — so the two can never both toast one alert, and the case it covers is the one that was previously silent: **the tray not running**, which was true on this box while the fix was being written
  - **The gate that makes it survivable is one-notification-per-incident.** The monitor writes one alert row per failed check, so a notifier that speaks per row is a denial of service against its own reader. Measured while building: 186 rows for one `venture-assistant` outage, 123 for one `internet` outage, 88 criticals/day at steady state, and **547,814 unresolved `Log error: kernel` rows** sitting in the table right now (SNAG-AGENT-002's damage). The daemon speaks only when no other alert with that title is already open, verified against those live rows: `Log error: kernel` → silent, an unseen title → speaks
  - **Subscribed, not called from `raise_alert`**, for two reasons: `core` must not import a domain (`test_import_boundary`), and `_queue_event` buffers until the run's transaction commits, so the "is another one open?" query cannot race the insert it is reacting to
  - **Both gates fail closed.** An unreachable database returns "not new" rather than "new", because the alternative turns a connection blip into a notification storm — which is the failure the module spends most of its code avoiding
  - **Still open, deliberately**: recovery is not announced. `alert.resolved` carries a *match pattern* rather than a subject (`"Project % health critical"`), so two of the three producers would publish something that reads as gibberish on a desktop. Announcing an outage's start and never its end is a real gap, recorded as one rather than papered over — see [tasks.md](tasks.md) Backlog

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

---

## Fixed Issues

_All SNAGs fixed to date are archived — nothing outstanding is hidden here._

| SNAG | Title | Fixed |
|---|---|---|
| SNAG-ROADMAP-003 | Four handoff conventions; scanner knew two and tuple order decided | 2026-08-10 |
| SNAG-PROJ-001 | Board freshness filter applied on one route out of nine | 2026-08-10 |
| SNAG-PROJ-002 | Deleted projects contributed to `average_active_score` | 2026-08-10 |
| SNAG-PROJ-003 | Project organiser never resolved its own alerts | 2026-08-10 |
| SNAG-PROJ-004 | 1,664 existing alert rows would never have cleared | 2026-08-10 |
| SNAG-PROJ-005 | Project review handed the model its figures | 2026-08-10 |
| SNAG-PROJ-006 | `/api/projects/stale` declared a `days` parameter it never read | 2026-08-10 |
| SNAG-PROJ-007 | `HACK`/`XXX` cost points and appeared in no column | 2026-08-10 |
| SNAG-PROJ-008 | TODO scan counted a project's own roadmap documents | 2026-08-10 |
| SNAG-PROJ-009 | `_count_todos`'s cap was per file, docstring said otherwise | 2026-08-10 |
| SNAG-PROJ-010 | `project_reviews` (and `disk_reviews`, `unit_audits`) never purged | 2026-08-10 |
| SNAG-PROJ-011 | Three places described `archived` as waiving git hygiene generally | 2026-08-10 |
| SNAG-PROJ-012 | Archived alert suppression absolute but documented as conditional | 2026-08-10 |
| SNAG-DB-001 | Un-applied migration caused a 39-hour monitoring blackout | 2026-08-10 |
| SNAG-CONF-001 | `sports_analyser` projects.yaml entry silently dead (wrong-case path) | 2026-08-04 |
| SNAG-SYSD-001 | `systemctl --user` checks always fail from the daemon (missing `XDG_RUNTIME_DIR`) | 2026-07-24 |
| SNAG-AGENT-003 | Shared `httpx.AsyncClient` reused across event loops | 2026-07-24 |
| SNAG-API-001 | Alert ack returned 200 with a malformed body for missing alerts | 2026-07-24 |
| SNAG-API-002 | Access-log middleware never excluded the real health endpoint | 2026-07-24 |
| SNAG-API-003 | Two endpoints blocked the event loop with sync psutil calls | 2026-07-24 |
| SNAG-TRAY-005 | Malformed API responses silently froze the tray on stale data | 2026-07-24 |
| SNAG-TRAY-004 | StatsPopup unreachable after dashboard cutover but still live | 2026-07-24 |
| SNAG-AGENT-001 | Project staleness scored from HEAD only, not all branches | 2026-07-24 |


### Session 37 write-up (handoff pipeline, fixed 2026-08-10)

**SNAG-ROADMAP-003 — four handoff conventions; the scanner knew two, and tuple order decided.**

- **Symptom**: `HANDOFF_PATHS` was `("docs/sessions/handoff.md", "docs/roadmap/handoff.md")`. The estate used **four** locations. `venture-assistant` kept a 6,044-byte `HANDOFF.md` at its root and `ImbaBots` a 141,096-byte `docs/handoff.md`; neither path was a candidate, so neither file was ever read. Both repos *also* carried a `docs/sessions/handoff.md` of 851 and 882 bytes — the SessionEnd hook's generated stub — and that was the file the scanner picked up. The next action for two active projects came from an 850-byte stub while a 6 KB and a 141 KB record sat unread beside it
- **Cause**: Two faults. (1) The candidate tuple was incomplete. (2) `_read` returned the first candidate that opened, making precedence a function of tuple order rather than of which document was current. `Alfred` had both listed candidates and happened to get the right one, by luck of ordering rather than by rule
- **Fix**: All four shapes listed, and `_read_handoff` selects by `handoff_date` — the document's own first-heading date, mtime as fallback — with tuple order breaking ties only. Also-rans are returned as `handoff_duplicates` rather than discarded, so a repo mid-migration is a reportable finding instead of a silent choice
- **The first attempt at the fix was wrong, and only the live estate showed it.** Ranking every *undated* candidate below every dated one is intuitive and re-creates the bug from the other side: `ImbaBots`' real handoff heads itself "Handoff — M5 (Tier 2)" with no ISO date, so the 882-byte stub written an hour *earlier the same day* outranked it purely for carrying one. The fallback has to apply uniformly — which is what `scan_roadmap` already did downstream when ageing a handoff, so the module had been holding two contradictory rules at once. The regression test uses real same-day timestamps deliberately: with bare epoch mtimes the stub wins honestly and the test would pass for the wrong reason
- **Root cause was upstream, and is also fixed.** The stubs existed because a SessionEnd hook wrote them. `SessionEnd` cannot block, so it could only emit what `git` already knew. It is retired in favour of a **Stop** hook that blocks until `HANDOFF.md` carries today's date — see [tasks.md](tasks.md) Session 37

### Session 34 write-ups (project-organiser capability audit, fixed 2026-08-10)

_Kept in full rather than summarised: each entry records what was measured
and why the chosen fix was chosen, which is the part that stops the defect
being reintroduced. Line references are to the pre-Session-35 layout
(`routers/projects.py`, `agents/project_organiser.py`); those modules are now
`projects/router.py` and `projects/agent.py`._

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
