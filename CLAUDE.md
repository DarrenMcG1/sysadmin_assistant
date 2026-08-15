# Claude Code Configuration - Sysadmin Assistant

## Quick Context

Infrastructure monitoring and housekeeping service with systemd integration. FastAPI + PostgreSQL + llama.cpp.
UK English throughout (colour, analyse, initialise).

**Current Phase:** _Update this as your project evolves_

---

## Before ANY Task

```bash
./scripts/claude-preflight.sh
```

This checks branches, worktrees, conflicts, and prints current priorities.

---

## Clarify Before Coding

When the user requests development work, **ask clarifying questions BEFORE writing any code** if the request is vague. Use these prompts:

**For vague requests** (e.g., "help me with X", "fix the Y page"):
> Before I start, let me clarify a few things:
> 1. **What specifically** do you want to achieve? (the outcome)
> 2. **Which files** do you expect this to touch?
> 3. **Is this a** quick fix (<5 files), new feature, or refactor?
> 4. Should I **check existing patterns** first?

**For refactor requests** (pattern changes, migrations):
> This sounds like a refactor. Before starting, I should:
> 1. Identify ALL affected files
> 2. Create a tracking document so nothing gets missed
> Want me to do that first?

**Skip questions when:**
- The user already provided specific files and outcomes
- It's clearly a quick fix with obvious scope
- The user says "just do it" or similar

---

## Critical Rules (MUST Follow)

1. **Run preflight before starting** - No exceptions
2. **Declare scope** - State which files you'll modify before touching them
3. **4+ hour tasks need worktrees** - Ask user before creating
4. **Update docs after completing work** - STATUS.md, tasks.md, snag_list.md, ideas.md
5. **Preserve insights before session ends** - Run `./scripts/claude-postflight.sh`
6. **Add tests with new features** - Never defer testing
7. **Archive completed work** - Move finished sessions/SNAGs to archive sections

> **⚠️ DOCUMENTATION IS MANDATORY**: The postflight script will block commits if docs aren't updated. If you complete work, you MUST update the relevant tracking docs before the session ends.

---

## Never Load Into Context

These directories waste tokens - never read or search them:
- `node_modules/`, `__pycache__/`, `.git/`
- `data/`, `logs/`, `dist/`, `build/`, `coverage/`
- `*.sqlite`, `*.log`, `*.pyc`

---

## Documentation Map (Read On Demand)

| When You Need | Read This File | When |
|---------------|----------------|------|
| Current priorities | `docs/roadmap/STATUS.md` (first 50 lines) | Session start |
| Open work sessions | `docs/roadmap/tasks.md` | Before starting work |
| Bugs to fix | `docs/roadmap/snag_list.md` | Before starting work |
| Feature ideas | `docs/roadmap/ideas.md` | When planning new features |
| Architecture decisions | `docs/ARCHITECTURE.md` | Only for structural changes |
| Previous session context | `HANDOFF.md` (root) | Session start (auto-read by preflight) |
| Active refactors | `docs/refactors/` | When doing large migrations |

**Do NOT embed these files** - just read the specific sections you need.

---

## Development Workflow (5 Steps)

### Step 1: Plan
1. Run `./scripts/claude-preflight.sh`
2. Check STATUS.md → tasks.md → snag_list.md (in that order)
3. Declare scope: "I'll be modifying X, Y, Z files"

### Step 2: Develop
- Write code with tests alongside - never defer testing
- Keep changes focused on declared scope

### Step 3: Audit (5+ file changes)
```bash
./scripts/lint_check.sh
```

### Step 4: Test
```bash
uv run pytest             # Full suite (backend + tray, ~360 tests) — must stay green
uv run ruff check .       # Lint — CI runs this, must stay clean
uv run mypy sysadmin      # Type check (backend only) — CI expects clean
```

### Step 5: Commit & Document
Before committing, update ALL relevant docs:
- [ ] **STATUS.md** - Add to "Recently Completed" if feature done
- [ ] **tasks.md** - Mark session/tasks complete
- [ ] **snag_list.md** - Mark bugs fixed with date
- [ ] **ideas.md** - Note if ideas were implemented

**Auto-generated files (auto-staged by pre-commit hook):**
- **docs/roadmap/auto_snag_list.md** - Auto-captured errors
- **audit-report.md** - Automated audit output

Run `./scripts/claude-postflight.sh` to verify docs are updated.

---

## Essential Commands

```bash
# Development
./scripts/run-dev.sh              # Start development servers
./scripts/lint_check.sh           # Validate before commit

# Session Management
./scripts/claude-preflight.sh     # Start session (reads handoff if exists)
./scripts/claude-postflight.sh    # End session (checks docs, generates handoff)

# Parallel Sessions
./scripts/claude-worktrees.sh setup 3    # Create worktrees
./scripts/claude-worktrees.sh teardown   # Merge and clean up
```

---

## Code Style

- **Python:** 4 spaces, snake_case, type hints required
- **Language:** UK English (colour, analyse, initialise)
- **Exceptions:** CSS framework classes, external APIs keep US spelling

---

## Database Configuration

**PostgreSQL is the default database**

| Setting | Value |
|---------|-------|
| Host | `localhost` |
| Port | `5432` |
| Database | `projects` |
| User | `gaddi` |
| Schema | `sysadmin` |
| Connection | `postgresql://gaddi@localhost:5432/projects` |

**Backend Port:** `8500`

**Configuration source:** settings live in `config.yaml` (validated by Pydantic models in `sysadmin/core/config.py`); per-service topology lives in `services.yaml`, keyed by project id and resolved through the `.project.yaml` manifests via `sysadmin/registry/`. `projects.yaml` is retired — project state lives in each repository's `.project.yaml`, and the old file is kept as `docs/projects-registry-legacy.yaml` until its comments have all moved into `decisions:` blocks. **No environment variables are read** — there is no `.env` file. Database URLs are set under the `database:` section of `config.yaml`.

---

## Contract Registry

Backend↔tray response shapes live in **`sysadmin/core/contracts.py`** — pydantic-only
(no FastAPI/SQLAlchemy), imported by both the backend (as `response_model=`)
and the tray (`sysadmin_tray/models.py` re-exports them). Parsing is defensive:
unknown fields ignored, missing fields defaulted, failures raise
`ValidationError` (a `ValueError`) → tray treats as connection lost.
Round-trip guarded by `tests/test_contracts.py`.

| Endpoint | Contract model | Enforcement |
|----------|----------------|-------------|
| `GET /health` | `HealthResponse` | response_model |
| `GET /api/sysadmin/status` | `StatusResponse` / `ServiceStatus` | response_model |
| `GET /api/sysadmin/resources` | `ResourceResponse` (+`RamInfo`, `DiskInfo`) | parse-side only (union "no data yet" shape; disk dict→sorted list) |
| `GET /api/sysadmin/resources/history` | `ResourceHistoryResponse` | response_model |
| `GET /api/sysadmin/alerts` | `AlertsResponse` / `AlertInfo` | response_model |
| `POST /api/sysadmin/alerts/{id}/ack` | `AlertAckResponse` | response_model |
| `POST /api/sysadmin/services/{name}/{action}` | `ServiceActionResponse` | response_model |
| `GET /api/sysadmin/services/{name}/details` | `ServiceDetailInfo` | parse-side only (raw `systemctl show` props, `[not set]` coercion) |
| `GET`/`POST /api/sysadmin/dnd` | `DndStatusResponse` | response_model |
| `POST /api/sysadmin/scan-all` | `ScanAllResponse` | response_model |
| `GET /api/sysadmin/self` | `SelfMonitorResponse` / `AgentSelfHealth` | response_model |
| `GET /api/sysadmin/events` | `EventMessage` | serialise-side only (SSE stream — each `data:` line, not a JSON body) |
| `GET /api/logs/recent` | `LogsResponse` / `LogEntryInfo` | response_model |
| `GET /api/logs/stats` | `LogStatsResponse` | response_model |
| `GET /api/projects/overview` | `ProjectOverviewResponse` | response_model |
| `GET /api/projects/stale` | `StaleProjectsResponse` (+`StaleProjectEntry`) | response_model |
| `GET /api/projects/managed` | `ManagedProjectsResponse` | response_model |
| `GET /api/projects/{name}` | `ProjectDetailResponse` (+`ProjectHistoryPoint`) | parse-side only (history newest-first; tray reverses for plotting; carries `next_action` per point — see below) |
| `GET /api/files/status` | `FileStatusResponse` (+`FileAuditSummary`, `FileQuickWins`) | parse-side only (404 = "no scan yet" → empty state) |
| `GET /api/files/duplicates` | `DuplicatesResponse` | parse-side only (404 = "no scan yet") |
| `GET /api/files/misplaced` | `MisplacedFilesResponse` | parse-side only (404 = "no scan yet") |
| `GET /api/files/large` | `LargeFilesResponse` | parse-side only (404 = "no scan yet") |
| `GET /api/files/trends` | `FileTrendsResponse` (+`FileTrendScan`, `FileTrendForecast`) | parse-side only |
| `GET /api/files/actions` | `FileActionsResponse` (+`FileRecommendationInfo`, `DiskThresholdInfo`) | response_model (404 = "no scan yet") |
| `GET /api/files/review` | `DiskReviewResponse` | response_model (404 = "no review yet") |
| `POST /api/files/review/generate` | `DiskReviewResponse` | response_model (auth; LLM optional — digest fallback) |
| `POST /api/files/clean/stale-caches` | `CleanResultResponse` | parse-side only |
| `POST /api/files/organise` | `FileActionResponse` (+`FileOperation`, `FileFlag`) | response_model |
| `POST /api/files/clean/duplicates` | `FileActionResponse` (+`FileOperation`) | response_model |
| `POST /api/files/clean/downloads` | `FileActionResponse` (+`FileOperation`) | response_model |
| `POST /api/projects/{name}/branches/prune` | `BranchCleanupResponse` (+`BranchInfo`) | response_model |
| `GET /api/projects/{name}/recommendations` | `ProjectRecommendationsResponse` (+`RecommendationInfo`) | response_model |
| `GET /api/projects/actions` | `PortfolioActionsResponse` (+`PortfolioAction`) | response_model |
| `GET /api/projects/board` | `ProjectBoardResponse` (+`ProjectBoardEntry`) | response_model |
| `GET /api/projects/next` | `NextProjectResponse` (+`NextProjectInfo`) | response_model (200 with `project: null` when nothing qualifies — never 404s) |
| `GET /api/projects/momentum` | `ProjectMomentumResponse` (+`ProjectMomentumEntry`) | response_model (200 with `worst: null` when nothing is measurable — never 404s) |
| `GET /api/projects/review` | `ProjectReviewResponse` | response_model |
| `POST /api/projects/review/generate` | `ProjectReviewResponse` | response_model (auth; LLM optional — digest fallback) |
| `GET /api/units/status` | `UnitScanResponse` (+`UnitScanSummary`, `UnitFindingInfo`) | response_model (404 = "no sweep yet") |
| `GET /api/units/actions` | `UnitActionsResponse` (+`UnitRecommendationInfo`) | response_model (404 = "no sweep yet") |
| `GET /api/services/reliability` | `ReliabilityResponse` (+`ReliabilitySummary`, `ServiceReliabilityInfo`, `ReliabilityDeduction`) | response_model (computed live — never 404s) |

Every surface that reports on projects goes through
**`sysadmin/projects/snapshots.py`**, which owns the latest-snapshot-per-name
join *and* the `newest_scan − 1h` freshness cutoff. Before Session 34 the
cutoff existed on `GET /api/projects/board` and nowhere else, so a project
deleted from disk was dropped from the board and reported as live by the other
eight surfaces — `PA-worktrees` held a row for two days after deletion, with a
health score and a next action. The audit counted eight call sites and there
were **nine**, which is the argument for a shared query rather than a repeated
filter: a copy-pasted pattern cannot be counted reliably.

Two rules the module encodes:

1. **Freshness is anchored to the newest scan, never to `now()`.** Anchoring
   to wall-clock would empty every project surface the moment the organiser's
   timer stopped — a monitoring failure reported as an estate with no projects
   in it.
2. **`fresh=False` exists for questions about history**, such as a review's
   week-ago baseline, where excluding projects that have since disappeared
   would hide the change being measured. Every *reporting* caller uses the
   default.

`tests/test_project_snapshots_query.py` fails if any module outside
`snapshots.py` builds `func.max(ProjectSnapshot.scanned_at)` for itself. Note
what it cannot show: the suite mocks every session, so a `WHERE` clause is
invisible to it and the filter's effect is asserted on compiled SQL, not a
round trip.

**`ProjectHistoryPoint` carries the narrative, not just the score.** The
organiser has written the whole roadmap findings block into
`project_snapshots` since Session 28, and until Session 37 the history list
exposed `health_score` and `scanned_at` only — ninety days of next actions
sat in JSONB with no endpoint over them, which is why Session 32's
start-versus-finish accounting was filed as blocked on a *document format*
when the data already existed. `build_narrative_history` adds
`next_action`, `next_action_source` and `next_action_changed`.

Two rules it encodes. **The comparison runs against the older neighbour**
(rows are newest-first, so index `i + 1`): `True` marks the scan where work
moved on, and a run of `False` measures how long one action stayed open —
ImbaBots' `M5-T05` shows 10 consecutive scans across 3 days. **The oldest
point is `None`, never `False`**, because there is nothing older in the
window to compare against; rendering that as "unchanged" invents a streak
whose length moves with `limit` while the data does not. Snapshots from
before 2026-08-06 carry `{}` and yield `None` — every `findings` access is
defensive, since this runs over whatever 90 days of retention holds.

**`GET /api/projects/next` ranks by stuckness, and the unit is days.**
The board describes projects and lets the caller order them; `/next`
chooses *for* the caller — alfred-glance shows one item, so the ranking is
invisible and `reason` is the only place the choice is accountable. The
rule, decided 2026-08-10, is **how long the stated next action has stood
unchanged**, tie-broken by the most recent commit. Rejected: longest-idle
(ranks by guilt, against the stated goal of momentum), nearest-to-finishing
(`done_tasks`/`open_tasks` are `None` for three of five active projects, so
it would be blind to most of the population while looking authoritative)
and smallest-next-step (unmeasurable — nothing records the size of a step).

**Days, not scans, because the cadence is irregular by construction**:
6-hourly until Session 35, daily from the organiser's timer since, plus
every manual `POST /api/projects/scan` — the live table holds two scans 17
minutes apart on 2026-08-08. A run length in scans ranks by how often the
organiser happened to run and calls it the owner's behaviour.
`unchanged_scans` is reported as evidence for the number, never ranked on,
and `at_window_edge` marks a run that reaches the oldest scan held, so
`days_unchanged` is a lower bound.

Three further rules. **Elapsed days come from the snapshot series, not
`handoff_age_days`** — the document's self-reported date says what it
claims about itself, the series says what was observed, and
`handoff_age_days` already decides `stalled`. **A `git`-sourced action is
not a candidate**: a commit subject is a record of the past, honest on the
board where the source is rendered beside it, and not an instruction.
**Nothing to do returns 200 with `project: null`**, never 404, which would
collapse "every project is up to date" into "no scan has ever run";
`skipped` breaks the ruled-out population down by reason, which is what
made it legible that the eligible set is 2 of 23.

**`GET /api/projects/momentum` counts events, not state.** The board and
`/next` read the newest snapshot and the idle nudges read how long one
action has stood — all three describe how things are *now*. This reads the
series and asks how often a session starts here and nothing ships.

The session record is a **side effect of a Stop hook**, not a log.
`~/.claude/hooks/require-handoff.sh` blocks a session that changed code
until `HANDOFF.md` carries today's date, and the organiser has stored that
document's age on every scan since 2026-08-06 — so
`scanned_at − handoff_age_days` reconstructs the date it was written, and a
change in that value between two scans is an observed session. Session 32
was filed as blocked on writing `docs/sessions/log.jsonl`; the log already
existed, sideways, in JSONB.

Three rules `sysadmin/projects/momentum.py` encodes, the first of which was
written the obvious way and refuted by the live series the same hour:

1. **A landing is matched by date window, never at the transition scan.**
   Asking "had a commit been made by the time the scanner saw the new
   handoff?" reads as common sense and is wrong, because the handoff is
   written *before* the work is committed. The scan at `2026-08-10 09:06`
   saw this repository's new handoff while `last_commit_at` still read
   2026-08-08; the day's six commits arrived afterwards and a productive
   day was reported as dropped. Scan timing was deciding the answer. A
   commit dated in `[session_date, next_session_date)` is that session's
   output.
2. **"Landed nothing" and "landed no code" are separate counts.**
   `dropped_code` versus `dropped`, with `docs_only` as the gap — a
   session that wrote up what it decided is a better outcome than silence
   and must not be summed with it. The any-commit date needs no scanner
   change: `findings['git']` is written only when a housekeeping commit
   was skipped (77 rows of 3,635), so its absence means the newest commit
   *is* the newest code commit and the fallback to `last_commit_at` is
   exact rather than approximate.
3. **Every count is a lower bound and the fields say so.** A session that
   changed no code never wrote a handoff; two sessions on one date
   collapse into one; the oldest observation is a state rather than a
   transition, so the session behind it is uncounted (the same rule
   `build_narrative_history` applies to `next_action_changed`); and
   `unverified` marks sessions dated by file mtime, which a clone or
   checkout rewrites. `observed_from` reports the first **dated** scan,
   not the first scan — this estate holds 198 snapshots of
   `sysadmin_assistant` and 22 of them can carry a session.

Its population is `ACTIVELY_SCORED` (`active` + `undeclared`), borrowed
from the agent rather than restated, and deliberately **wider** than
`/api/projects/next`: a commitment needs someone to have written one down,
whereas a session that shipped nothing is a fact about a repository
whether or not it has a plan.

**Two things speak on this box, and only one of them at a time.** The tray
polls `GET /api/sysadmin/alerts` and owns the notification policy (dedup,
flap cooldown, coalescing, digest — `sysadmin_tray/notifications.py`).
`sysadmin/monitor/desktop.py` is its **understudy**: subscribed to
`alert.raised`, it stays silent whenever that route has been polled within
`notifications.desktop.tray_grace_seconds`, and speaks when the tray is not
running — which was silent altogether until 2026-08-11 (SNAG-CFG-001:
`notifications.desktop` was parsed by pydantic and read by nothing, and
`Notifier.send_notification` had no production caller at all).

Three rules it encodes, each measured rather than assumed:

1. **One notification per incident, not per alert row.** The monitor
   writes one row *per failed check* — 186 for one `venture-assistant`
   outage, 88 criticals a day, 547,814 unresolved `Log error: kernel`
   rows in the table. The daemon speaks only when no other alert with
   that title is open.
2. **Both gates fail closed.** An unreachable database returns "not a new
   incident", because the alternative turns a blip into a storm.
3. **Subscribed, never called from `raise_alert`.** `core` must not import
   a domain, and `_queue_event` buffers until the run's transaction
   commits — so the notifier's query cannot race the insert it reacts to.

Recovery is deliberately **not** announced: `alert.resolved` carries a
match pattern (`"Project % health critical"`), not a subject.

**A detected fault has to keep speaking, and the ladder that makes it do
so lives in `core`** (Session 39). `sysadmin/core/escalation.py` owns
`SEVERITY_ORDER`, `Ladder` and `step_for`; `sysadmin/projects/nudges.py`
and `sysadmin/monitor/stalls.py` both climb it. It is in `core` for the
reason `strip_markdown` is — `monitor` may not import `projects`
(`tests/test_import_boundary.py`) — so "reuse rather than copy" required
the move first.

The failure it fixes is **not** a detection failure.
`self_monitor.build_self_report` caught SNAG-AGENT-003 correctly and
`_check_agent_liveness` raised one row; the raise is then deduplicated
while that row is open (correct — it is what stopped the 1,664-row
pile-up) and the tray fingerprints on `{severity}:{title}`. Net effect:
**the alarm rings once, at the quietest severity, and is silent while the
fault persists.** A warning that fires once is indistinguishable from one
that got fixed.

Four rules, three of them the opposite of the obvious implementation:

1. **Escalation resolves the quiet row and raises a louder one**, never
   updates severity in place — an in-place change keeps the fingerprint
   the tray has already suppressed, so the escalation is recorded and
   never spoken.
2. **The loud rung for a stall is `critical`, and that is about
   persistence, not volume.** `sysadmin_tray/notifications.py` sets
   `transient=False` for `critical` alone, making it the only severity
   the tray leaves on screen. The owner's reported failure was "I never
   saw the toast" — away from the machine — and a transient toast in an
   empty room is the miss, whatever its severity. A nudge, by contrast,
   never reaches `critical`; the two modules' docstrings cite each other
   so the difference reads as deliberate.
3. **The escalation clock starts when the alarm rang, not when the stall
   began.** Anchoring to the stall's own age makes a daemon outage
   produce a wall of criticals on restart — nothing runs while the
   service is down, so every agent is stalled — which charges the estate
   for this application's downtime, the rule
   `GET /api/services/reliability` already encodes as "a gap in the
   series never costs points".
4. **`escalate_after_hours: 24` is measured against the slowest agent.**
   `file_organiser` and `service_discovery` run daily, so a stall that is
   merely late clears within one interval; a shorter gap escalates faults
   about to fix themselves. It cannot make detection faster — that is
   `stall_grace_multiplier`, which is the wrong knob someone will reach
   for, so the config docstring says so.

`Restart=always` made the **crash** case silent the same way:
`sysadmin.service` never entered `failed`, so an `OnFailure=` hook could
not fire. `StartLimitBurst=5` / `StartLimitIntervalSec=600` makes a loop
terminal and `sysadmin-failed.service` announces it, persistently
(`--expire-time=0`) and to journald first — the one destination that does
not need anyone logged in. `tests/test_systemd_units.py` pins the two
halves together, because either alone accomplishes nothing.

**Serving against a schema this code was not written for is worse than
not starting** (Session 43, SNAG-DB-001). `sysadmin/core/schema_guard.py`
compares `alembic_version` against the packaged head in the lifespan and
raises — deliberately **not** inside a `try`, unlike the unit-failure
resolve three lines below it, because a stale alert row is worth less
than a boot and a schema mismatch is the exact opposite trade. Migration
009 was written, committed and never applied; two minutes later the
daemon began writing a status the database rejected, and
`service_health` took **no rows for 39 hours** while the tray went on
rendering the last values it had. Nothing applies migrations here — no
script, no `ExecStartPre`, no CI step.

Refusing is the only option whose failure mode is visible: the unit
enters `failed`, `StartLimitBurst=5` makes the loop terminal, and
`sysadmin-failed.service` announces it — the Session 39 machinery's
second caller. Coming up degraded and raising a critical instead would
write that alert *through the schema that is wrong*.

Three rules. **The head comes from alembic's own `ScriptDirectory`**,
never a regex over `alembic/versions/*.py` — a second implementation of
the revision graph drifts from the command it exists to measure against.
**`alembic_version` is read schema-qualified**: `version_table_schema`
exists because the `projects` database holds another application's copy
in `public`, and resolving through `search_path` would compare this code
against a stranger's revision and pass. **Every way of not-knowing fails
closed with its own message** — unreadable scripts, a branched history
(two heads, which `alembic upgrade head` itself refuses), and a database
never migrated are three different faults and the operator needs to be
told which. Note what could *not* have caught this: `verify_connection`
proves the database answers, and the drift guard skips `alembic_version`
and does not diff CHECK constraints.

**One savepoint per service, and it works because leaving the block
flushes.** `SysAdminAgent._execute` used to add all nineteen services'
rows to one session and commit once, so one `CheckViolationError` aborted
the lot. `session.add` never talks to the database — the rejection
surfaced at that single commit, by which point the bad row was
indistinguishable from the eighteen good ones. `session.begin_nested()`
forces it to surface while that service's own savepoint is innermost.

Three consequences. A rejected service is written as `status="error"`
with `details['source'] = 'write_isolation'`, because **absence of a row
is what made the hole invisible** — the same rule `_record_outcome`
learned in Session 41. It is added to `unhealthy`, so `_resolve_recovered`
cannot announce a recovery nobody observed. And `details['write_failures']`
**names** the services rather than counting them. The honest limit: a
savepoint rolls back SQL and nothing else — an auto-restart already
issued stands, and the in-memory streak counters stay bumped.

**"Has not run" and "ran and failed" are two alert families, not one
title with two messages** (Session 43). `sysadmin/monitor/failures.py` is
a **sibling** of `stalls.py` sharing `core/escalation.py`'s ladder, and
the two are mutually exclusive by construction: a failing agent is
recording runs, so its `last_run_at` is fresh and `summarise_agent` never
marks it stalled. `_check_agent_health` reads **one** snapshot of
`agent_runs` and `alerts` and hands it to both — two fetches could
disagree about the same agent, and that mutual exclusion is only sound if
they are looking at the same data.

Four rules. **The suffix `agent failing` is load-bearing**: `failing` is
not one of `SERVICE_ALERT_KINDS`, which is the only thing keeping these
rows out of `_resolve_recovered`'s reach — a family ending in
`degraded`/`warning`/`critical`/`unreachable`/`auto-restarted` would have
its rows closed by the sysadmin agent while they were still true, and a
test pins it. **The threshold is a count of runs, never a duration** —
deliberately the opposite unit from `escalate_after_hours` in the same
config section, because `agent_runs` records a *run* rather than a
schedule, so "failing for three hours" cannot tell a failing agent from
one that is not running, which is the stall family's question. The cost
is stated rather than hidden: a count is fast for a 60-second agent and
slow for a daily one. **Two failures, not one**, because the news is
"reproducible" rather than "happened". **The handover is automatic** — an
agent that fails and then stops being scheduled has its failure row
resolved as the stall row opens, so one fault shows one alert.

This family **could not have been written before Session 41**:
`_record_outcome` wrote `status='failed'` into the transaction the failure
had already destroyed, so `agent_runs` held no failure rows at all — 39,762
runs and zero failures, which reads as perfect health off a table that
could not express the opposite.

**A unit failure also leaves an alert row, and the write is only half of
it.** `sysadmin/core/unit_failure.py` runs *while the application is
dead* — so no async engine, no `BaseAgent.raise_alert`, no event bus; it
uses the **sync** engine that exists for Alembic. `agent` is `'sysadmin'`
because `chk_alert_agent` admits only the five agent names, and
`details['source'] = 'systemd_onfailure'` carries the provenance `agent`
cannot: the sysadmin agent did not raise this, it was dead, which is the
news. A sixth constraint value was rejected — it would name a script
rather than an agent and make `self_monitor.AGENT_NAMES` wrong, and those
two are pinned together by `tests/test_units_api.py`.

**The lifespan resolves it, and that pairing is what makes the row
legitimate.** The service starting *is* the recovery, and it is the only
moment that fact exists — nothing observed the failure from inside. Without
the resolve this is an alert type that can only accumulate, which is how
1,664 orphaned rows happened; dedup on an open row is safe *only* because
of it. `OWN_UNIT` is named in three files (the constant, the unit's
`ExecStart=`, the script's default) and a mismatch does not error — one
side writes `sysadmin.service failed` and the other resolves
`sysadmin failed`, so the row is simply never closed.

**`BaseAgent.run` runs in three transactions, and the count is the
invariant** (Session 39's snag, fixed Session 41). It used to open one
session, insert the `running` row, **flush** it — which starts a
transaction — and hand that same session to `_execute`. This host sets
`idle_in_transaction_session_timeout=1min`, so any agent whose work
outlasts a minute has its backend terminated and loses every write of the
run. The file organiser scanned for 117.71 s on 2026-08-11, found 25,317
issues, logged `agent_run_completed`, and wrote **nothing**: no audit, no
`completed` row, and no `failed` row either.

That last one is the half worth remembering. The `except` branch sets
`status='failed'` on a row living in the transaction the failure
destroyed, so **the failure record dies with the run it records** — an
agent failing this way is indistinguishable from one that was never
scheduled, which is what `GET /api/sysadmin/self` reported for five days,
correctly, off a table that was being emptied. The one surviving run is
the proof rather than the exception: 2026-08-06 took **29.63 s**, the only
run in the agent's life to finish inside the timeout.

Now `_record_start` commits alone, `_execute` gets a session that has
**never been flushed** — so its transaction opens at its first statement
rather than two minutes earlier — and `_record_outcome` is an `UPDATE` by
id from a third. It costs nothing because `UUIDPrimaryKeyMixin` sets
`default=uuid.uuid4` client-side: the id exists before the INSERT is sent.
`tests/test_agent_run_recording.py` asserts the transaction count, because
collapsing them back is the defect.

Two changes of meaning, both deliberate. `_execute`'s writes are no longer
atomic with the run record — still atomic with each other — and a process
killed mid-run leaves a permanent `running` row where it used to leave no
row at all. The second is an improvement for the same reason as the first:
absence of a row is the thing that cannot be told apart from absence of a
run. Note the rule already existed one layer up, in `files/review.py`
("commit the read transaction before calling the LLM") — learned for
inference and never generalised to the framework beneath it.

**Idle nudges have no endpoint, and that is the design** (Session 31). A
nudge is an `alerts` row raised by the organiser — `Project <name> next
action idle` — so it reaches the tray, the DND windows and
`GET /api/sysadmin/alerts` through plumbing that already exists. What it
asks is deliberately *not* the health score: an `active` project whose
human-written next action has not changed for **7 days** (`info`), then
**14** (`warning`), overridable per project as `idle_nudge_days` in
`.project.yaml`. `venture-assistant` scores 100 and could still be sat on
the same action for a fortnight, which is why the score is never
consulted.

Eligibility is **borrowed from `GET /api/projects/next`**, not restated:
`next_action.eligible_candidates` is the one definition of a commitment
(active, `handoff`/`tasks` source, not a "nothing queued" sentence) and
both call it. Two copies drift in the direction nobody notices — the
endpoint stops offering a project while the nudge goes on reminding you
about it, and nothing reports the disagreement.

Three rules `sysadmin/projects/nudges.py` and `_nudge_idle_projects`
encode, each the opposite of the obvious implementation:

1. **Raised once per open nudge, not once per scan.** `raise_alert`
   inserts unconditionally and the organiser runs daily, so the
   health-alert pattern writes one row per day per stuck project — the
   1,664-row pile-up expressed as a feature.
2. **Escalation resolves the quiet row and raises a loud one**, never
   updates severity in place: the tray fingerprints on
   `"{severity}:{title}"`, so an in-place change keeps a fingerprint it
   has already suppressed and the escalation is recorded but never spoken.
3. **The escalation is a gap, not a multiplier.** A project relaxing its
   own threshold to 21 days escalates at 28, not 42 — the per-project
   knob moves when the clock starts, not how patient the escalation is.

A nudge is never `critical`: criticals break through DND by configuration.
Whether the `info` rung is audible at all is decided by
**`tray.notify_min_severity`** — *not* `notifications.desktop.min_severity`,
which is parsed and read by nothing (SNAG-CFG-001).

`GET /api/projects/stale` answers **idleness, not ill health** — commits older
than `days`, defaulting to 30. It spent its first life declaring `days` and
filtering on `health_score < needs_attention_min` instead, which made it a
duplicate of `/overview`: a well-kept repository untouched for a year scored 90
and never appeared. `days_idle` is `None` for a project with no commit at all,
which is distinct from `0` (committed today) and is deliberately *included*
rather than dropped — "never" is the strongest form of the question being
asked. The window is echoed back in the body so a cached response stays
interpretable.

**Both scoring agents resolve alerts set-based**, and the second one arrived
by the first one's argument being reused rather than rediscovered.
`ProjectOrganiserAgent._resolve_recovered` came first: a project deleted from
disk never appears in a scan, so it can never be observed *recovering*, a
per-project loop leaves its alert unresolved forever, and retention purges
resolved rows only. That is how 1,664 rows accumulated by 2026-08-07, 326
sharing one title. `_resolve_recovered` asks the inverse question — which open
health alerts would this scan *not* raise — closing recovery, deletion, rename
and re-declaration as `archived` in one statement. Raise and resolve both
derive their title from `_alert_title`, because a hand-written resolve pattern
that matches nothing is invisible.

`SysAdminAgent._resolve_recovered` is the same statement on the service side
(Session 41, SNAG-AGENT-004), where the same defect had reached **51,924
rows** — twenty times the scale, and in two families rather than one:

- **27,827 for five services that no longer exist** in either config file.
  Recovery was observed inside the loop over the *configured* services, so a
  deconfigured service was never checked, never seen to recover, and never
  resolvable. `redis unreachable` held 6,283 rows last raised 2026-03-07.
- **24,097 for resource thresholds**, which had **no resolve path at any
  point in this application's life**. `Critical disk usage on /` alone is
  13,971 open rows last raised 2026-07-26, against a disk that has been at
  68 % since. A condition that recovered and could not be observed
  recovering is the same defect as a service that was retired, so one
  statement closes both.

Four rules it encodes, two of which are the opposite of the obvious version:

1. **The population is `RESOLVABLE_TITLE_PATTERNS`, not the configured
   service list.** A set built from configuration cannot contain a
   deconfigured service, which is the entire defect. Patterns are the only
   shape that can reach a row whose subject is gone.
2. **Services and resource thresholds take different exclusions.** A mount
   either breached this run or did not, so "titles this run raised" decides
   it exactly. A service's alert is governed by a *streak* — three
   consecutive degraded checks — held in `_degraded_counts`, which is in
   memory and **resets on daemon restart**. The same test would therefore
   close a genuinely-degraded service's alert on the first run after every
   restart and re-raise it two checks later: a recovery announced to the
   tray for a fault that never went away. Services are resolved only when
   this run measured them *healthy*.
3. **Three families are excluded because each has a lifecycle owner
   already**, and a second owner closes a row while it is still true:
   `% agent stalled` (`stalls.py` escalates *off* the quiet row staying
   open), `% failed` (`unit_failure.py` writes it dead and the lifespan
   resolves it alive), `Unusual % usage` (`_check_anomalies` resolves by id).
4. **`skipped` counts as healthy; `error` does not.** Both mean nothing was
   measured, and the difference is who decided. `error` is the check
   failing — the state is unknown and resolving on unknown announces a
   recovery nobody observed. `skipped` is `services.yaml` declaring
   `monitor: false`, and an open critical nothing will ever look at again is
   the pile-up wearing a declaration as an excuse.

The per-service `resolve_alerts(session, service_name)` it replaced was also
a substring `ilike`, so `venture-chat` recovering closed
`venture-chat-large`'s alerts — a second bug nobody had filed, removed by
having one owner of the lifecycle instead of one per item.

What it does **not** cover is `log_aggregator`'s rows (SNAG-AGENT-005, fixed
Session 41's successor). Those are **events, not states** — a log line that
was written cannot un-write itself — so there is no run at which "this would
not be raised" becomes true, and the fix was a *raise* rule.

**A log is not an incident, and the alert's identity is the fault, not the
source** (Session 42, SNAG-AGENT-005). `LogAggregatorAgent` raised one alert
row per matching log line: **598,091 unresolved rows**, 91 % of every
unresolved alert in the table, of which 99.8 % were two Bluetooth firmware
messages emitted by a kernel retry loop at ~8.5 lines a second. This
application had already recorded the mistake once — *"that table records one
row per failed check — 123 rows for one internet outage"*, in
`GET /api/services/reliability`'s docstring — and not generalised it.

`sysadmin/monitor/log_signature.py` owns the identity: the message with its
variable parts removed (digit runs → `N`, hex → `0xN`, whitespace collapsed).
Four rules, the first of which was the obvious implementation and was refuted
by the live table before it was written:

1. **The key is the signature, not the source.** `Log error: kernel` is
   shared by every kernel error whatever it says, so deduplicating on the
   existing title would have let the Bluetooth storm hold the single open row
   while an RCU stall and a USB enumeration failure — **both in the same live
   30-day window** — went unannounced. Half a million rows traded for a mask
   over every other kernel fault is not a fix. Normalisation does lose
   `error -110` versus `error -71`; nothing is actually lost, because
   `message` carries the last verbatim line and `details['occurrences']`
   carries the count that used to be expressed as row volume.
2. **The signature lives in the title**, not in `details`. Dedup, the resolve
   and the tray's `{severity}:{title}` fingerprint all key on title already,
   so no new machinery is needed and none of them can disagree about
   identity — and four open rows all reading `Log error: kernel` are
   indistinguishable to whoever is looking at the tray.
3. **Silence is the only recovery signal an event has.** `_resolve_quiet`
   closes a row unobserved for `alert_quiet_minutes` (15, i.e. 15 polls),
   excluded by exact title as well as by age because an exclusion set cannot
   race the clock that stamped the row. `COALESCE(details->>'last_seen_at',
   created_at)` is what made the pre-existing backlog reachable at all.
   `details` is *reassigned*, never mutated in place: SQLAlchemy does not
   track mutation inside a plain JSONB dict, so an in-place bump looks like
   it worked, writes nothing, and freezes `last_seen_at` while the fault
   fires.
4. **`_open_alerts` is bounded by the titles the run raised.** Written first
   as "every unresolved row this agent owns" — 593,814 ORM objects on the
   first live run, the fix falling over on the backlog it exists to end. An
   unbounded `SELECT` over the table whose unboundedness is the bug is easy
   to write and nasty to ship.

**Dedup and the set-based resolve are mutually exclusive, and the
collation family is where that got written down** (Session 44,
SNAG-DB-002). A glibc upgrade moved this box from locale data 2.43 to
2.44; PostgreSQL records the version each database was created with so
it can say it no longer matches, and had been printing that on every
`psql` connection, read by nobody. Any B-tree index on text was built
against the old ordering, so a lookup can miss a row that is present —
which here would present as an alert that never deduplicates or never
resolves. `sysadmin/monitor/collation.py` reads `pg_database` once per
sysadmin run; the catalog is **cluster-wide**, so the existing
connection to `projects` sees all eleven databases without a second
engine. Eight are stale. The snag said three, because three is how many
someone had opened a shell against.

Four rules, three of them the opposite of the obvious implementation:

1. **Not-knowing is not a mismatch, and this fails _open_** —
   deliberately the reverse of `core/schema_guard.py`, which refuses to
   boot on every way of not-knowing. `template0` records no version and
   a `C`-locale database has no actual version to compare against, so
   both sides are required non-NULL **in SQL**; `IS DISTINCT FROM` is
   rejected for reporting `2.43` against `NULL` as a difference. The
   guard fails closed because serving against the wrong schema is worse
   than not serving; here a false positive is an operator reindexing a
   16 GB database that is fine.
2. **Raised once per open row, never once per run.** The agent polls
   every 300 s and a stale collation persists until someone reindexes,
   so the `_check_thresholds` pattern would write 2,304 rows a day for
   one fault.
3. **Therefore the family stays out of `RESOLVABLE_TITLE_PATTERNS` and
   owns its own lifecycle.** That sweep closes every owned row the run
   did not raise, which is sound *only* for a family that re-raises
   every run — which is why `_check_thresholds` can be in the tuple and
   this cannot. Dedup plus sweep makes a row flip-flop, resolved on the
   run that holds and re-raised on the next, and each flip clears the
   tray's `{severity}:{title}` fingerprint so it notifies again. A
   pile-up is loud; that is loud *and* reads as recovery. The database
   name sits last in the title, keeping it clear of the five
   `% <kind>` patterns by construction.
4. **The remedy's trap is carried in the alert.** `ALTER DATABASE …
   REFRESH COLLATION VERSION` alone clears the warning by asserting the
   versions now match without rebuilding anything — a loud known risk
   turned into a silent one — so the message names `REINDEX` first and
   `details['remedy']` is an ordered two-element list.

The gap this leaves is `SNAG-AGENT-006`: the *service* and *threshold*
families still raise unconditionally, so a sustained fault writes one
row per run — 60 for one dead timer in five hours. Bounded rather than
immortal since Session 41's resolve, and not fixed here because both
halves must move together.

**The estate publishes and never acts; this repository judges — and the
judge owns every row it sweeps, which is what lets it do both** (Session
45). `sysadmin/estate/` is a package rather than a module in `monitor/`
because it is a domain: a client that pulls, a **pure** `judgements`
module holding every threshold, and an agent holding only the lifecycle.
It reads four surfaces on 8400 — the scan's invariants, `attention`, the
audit's invariants and the queue's — hourly, because the producers change
twice a day and `/api/projects/attention` re-walks ~26 `.project.yaml`
manifests from disk on every request.

`monitor/collation.py` records that dedup and a set-based resolve are
mutually exclusive. They are — *there*. That sweep's exclusion set is the
titles the run **raised**, so a deduplicating family (which raises
nothing on run two) has its still-true row resolved, re-raised, resolved,
and each flip clears the tray's `{severity}:{title}` fingerprint. This
agent's exclusion set is the titles the run **judged**, which is a
different set: dedup suppresses the raise, never the judgement. A fault
that persists is in `current` every run and is never swept; a fault that
clears leaves `current` once and resolves once. That is available only to
an agent that owns every row it sweeps — `_resolve_recovered` scopes on
`Alert.agent == self.name`, so `estate_judge` rows are unreachable from
the sysadmin agent by construction.

Five rules, three of them the opposite of the obvious implementation:

1. **A cumulative total is not a rate.** The queue publishes
   `dropped_total`, `expired_total` and `grants_total` as `count(*)` over
   the whole `gpu_leases` table. `dropped_total` is 1 today, so a `> 0`
   rule raises a row no future state can clear — `redis unreachable`'s
   6,283 and `Critical disk usage on /`'s 13,971 arriving by a fourth
   route. Only `depth` and `oldest_waiting_seconds` are gauges; the
   totals are carried in `details` as evidence.
2. **The sweep is scoped to the surfaces the run read.** Four independent
   surfaces come from one process, so three answering while one 500s is a
   real state; sweeping globally would close every health breach and idle
   nudge on the strength of a payload nobody received. Rows carry
   `details['estate_surface']` rather than being matched back by title —
   `COLLATION_DETAIL_KEY`'s rule.
3. **Unreachability is not judged at all.** `estate-manager-api` is an
   `http` entry in `services.yaml` polled every 300 s, with both estate
   timers beside it as `kind: timer`. A second owner of one lifecycle
   closes a row while the first still holds it true. 8400 being down
   costs a log line and `details['unread_surfaces']`, which **names** the
   surfaces.
4. **Nudge severity is the producer's; health severity is ours.** The
   estate computes a nudge's rung on the ladder that moved with the
   domain, so taking it verbatim keeps one implementation. `health`
   carries no severity — that machinery was deleted rather than ported —
   so a breach is `warning`, one rung, never `critical`. The audit's
   `findings_total` is never judged: 8 of today's 10 are the collation
   family this service already raises, and the rest are other
   repositories' conformance, which the estate rules send to their own
   ADR processes. What is judged is whether the audit **ran**.
5. **Variable text never enters a title.** `sources_unreachable` is free
   text ending in an exception class name, so a per-source title opens a
   second row the day the same dead seam fails with `ConnectError`
   instead of `HTTPStatusError`. One row; `details['sources']` names
   them. The title is also kept clear of `RESOLVABLE_TITLE_PATTERNS` by
   construction — `Estate scan could not reach sources`, not `… sources
   unreachable`, which `% unreachable` would match.

`scan_max_age_hours`/`audit_max_age_hours` are **derived** (both timers
are daily, plus the briefing's existing two-hour `stale_sources` margin);
`queue_max_depth`/`queue_max_wait_seconds` are **invented** and say so in
config, because until estate-manager's Session 3 there was no queue to
measure. `base_url` duplicates `services.yaml` deliberately — deriving it
would stop the judging silently when a service is renamed — and a test
asserts the two agree.

**Rule 3 has one named exception, and `ports` is it** (Session 26b-A).
The estate's audit files findings and **never alerts**; this repository
is the only party on the box permitted to speak. Until now nothing
judged `/api/audit/findings`, so a `breach` was detected, correct,
machine-readable and never said out loud — the shape Session 46 spent
itself removing for units, reproduced one layer up. `judge_audit_findings`
judges it per finding.

The narrowing is exact, and both of rule 3's original reasons still
exclude what they excluded. **Scoped to `check == "ports"`, never to a
severity**: all four estate checks emit `breach`, so a severity-only
filter would re-import the collation family `monitor/collation.py`
already raises here (this service's own alerts arriving through a second
producer) and pull in `pointers`/`seams`, which are other repositories'
conformance. Neither reason reaches a port, because **no repository owns
one**.

Five rules, three of them the opposite of the first draft:

1. **Only `breach`, taking the producer's severity as the filter** — the
   deference `judge_attention` already gives a nudge's rung. `warn` is
   `claimed_but_silent`, which is *availability*, and availability has an
   owner here: `services.yaml` plus the sysadmin agent's `% unreachable`
   family. That today's one live `warn` (port 3300) happens not to
   overlap is luck — its registry row reads "unit to follow".
2. **One row per port, port in the title.** Session 46's rule; a roll-up
   cannot name anything.
3. **Until the count says the fault is the registry itself.** Above
   `port_breach_max_rows` (5) it collapses to one row naming the ports in
   `details` — six simultaneous unclaimed listeners is a table moved or
   truncated, not six services, and six toasts train the reader to
   dismiss the family (`SNAG-UNITS-002`'s refusal to ship fifteen). The
   estate errors on an **empty** parse; a partial one is the gap that
   leaves.
4. **The port comes from `detail['port']`, never from `subject`.**
   `subject` is producer prose; a finding whose port will not parse is
   skipped rather than titled from the sentence, because that fallback is
   the forkable title rule 2 forbids. `isinstance(True, int)` is `True`,
   so bools are refused explicitly.
5. **The title carries no `code`.** `unclaimed_listener` is the only
   ports breach today, and a code in the title forks the row when a
   second one lands for the same port. The producer's `summary` is the
   message, so its wording can change without moving the identity.

`audit_invariants` and `audit_findings` are **two surfaces, not one**,
though they come from a single check run: they are two HTTP calls that
fail independently, and the sweep is scoped per surface — sharing an id
would let a successful read of "did the audit complete" close every port
row raised off a findings payload nobody received.

Verified live rather than only against literals, because this family
ships with **zero rows today** and that is exactly `SNAG-ESTATE-002`'s
starting position: the estate's own `run_check` was driven in-process
against the real registry document with a listener bound on 8888, giving
clean → `breach` → clean, with no write to the estate's database. It
caught one defect no literal would have — the estate stamps a first
sighting `standing_days: 0.0`, and "Standing 0 days" reads as a rounding
artefact.

Two gaps are filed rather than assumed settled: `SNAG-ESTATE-002` (the
producer's `Nudge.title`/`.message` are `@property` and `asdict` drops
them, so this repository builds a format the estate believes it owns —
and `judge_attention` has therefore never been exercised against a
populated payload, because both lists have been empty every time anyone
has looked) and `SNAG-ESTATE-003` (no escalation; the loud rung would be
`critical`, which is reserved for faults on this box, and the family most
in need already arrives pre-escalated from the producer).

**Journal reads resume from a cursor, and it must advance over what the
filter discards.** `read_journal` was called with `since="2m ago"` on a
60-second poll, so every unit-journal event was stored **exactly twice**.
`__CURSOR` rather than a narrower window, because narrowing trades the
duplicate for a *gap* whenever a run runs long — the worse failure for a
monitor. The cursor is taken **before** the severity filter: advancing only
past kept entries leaves the resume point behind a run of info-level noise
and rebuilds the defect one layer down. It is in memory, so a restart falls
back to the newest `logged_at` already stored for that source, passed as
`--since @<epoch>` because journalctl reads a bare datetime as **local**
time. The `-n 500` ceiling stays — 8.5 messages a second makes one
unavoidable — but hitting it is now `details['truncated_sources']`, which
**names** the sources rather than counting them, because which one is at its
ceiling decides whether it matters. It was invisible before: `findings_count`
sat at exactly 200 on every run.

**`status: archived` waives exactly two deductions** — commit staleness and
stale branches — and nothing else. It is *not* a general git-hygiene exemption:
a leftover `.git/index.lock` still costs an archived project 5 points and a
missing remote is still reported. Its **alert suppression, by contrast, is
absolute**: `_effective_threshold` returns 0 and the score is clamped with
`max(0, …)`, so the condition is `score < 0` — unreachable at any score, for
any repository, unless a manifest sets an explicit `alert_threshold`.

**The marker scan reads code, not documentation.** `*.md` is excluded because a
repository's own `snag_list.md` counted towards its own penalty — writing up a
defect lowered the score of the project writing it up. Patterns match whole
words (`grep -w`), so `TODO_STATES` and `TodoList` are identifiers rather than
markers, and the cap is a **project total** that records its own truncation in
`findings['todo_scan_truncated']`; `-m` is grep's per-file limit and was
documented as a global one. All configured patterns are penalised, so
`findings['todos']` carries the full per-pattern mapping and the
recommendation names the markers it charged for — a project penalised for 40
`HACK` markers used to read "0 TODOs, 0 FIXMEs" beside an unexplained
deduction.

Both weekly reviews are **figure-free by construction**, not by instruction,
and share `strip_markdown` from `sysadmin/core/text.py` — it lives in `core`
because neither domain may import the other.

`GET /api/files/actions` is the file-organiser mirror of
`GET /api/projects/actions`, with one deliberate difference: its currency is
**reclaimable megabytes**, not health-score points, so it uses its own
`FileRecommendationInfo` rather than reusing `RecommendationInfo` — one
`points` field meaning two units decided by the producer would be unreadable
at the call site. Only duplicates, old downloads, stale caches and rebuildable
dependency directories price above 0.0 MB; tidiness items (misplaced files,
empty dirs, similar folders) rank by `item_count` beneath them. It is the only
`/api/files/*` route that reads `resource_snapshots`: disk **occupancy** is
what answers "when does the disk fill up", and a projected 80 %/90 % crossing
inside 30 days outranks every byte total. Counts come from the audit row's
columns, never from `findings` — the findings lists are truncated to 50–100
entries before storage, so sizes summed from them are a lower bound and say so.

`GET /api/files/review` is the disk equivalent of `GET /api/projects/review`,
stored in its own `disk_reviews` table. Two rules govern any LLM-narrated
review here, both learned from live runs:

1. **Commit the read transaction before calling the LLM.** This host sets
   `idle_in_transaction_session_timeout=1min` and inference takes longer.
2. **Give the model no numbers — do not merely instruct it not to use them.**
   Verified 2026-08-06: handed "25.0 GB across 50 directories" plus an
   explicit "do not restate figures", dria-agent-a-3b restated them *and*
   published the quotient as "each consuming 5GB". `build_review_prompt` is
   now figure-free by construction (sizes → bands, categories → phrases,
   occupancy → a direction), guarded by a test asserting no digit reaches
   the model. Every real figure lives in `build_facts_section`, which is
   prepended to the narrative deterministically. `strip_markdown` removes
   the headings and lists the model emits despite being told not to.

The three `/api/files/*` action endpoints share one manifest shape and are
**dry runs unless the request body sets `confirm: true`** — see
`sysadmin/files/actions.py` for the safety rules (root confinement,
no symlink following, no overwriting, trash instead of delete).

`POST /api/projects/{name}/branches/prune` follows the same contract for git
branches — see `sysadmin/projects/branch_actions.py`. Dry run by default;
only branches **merged into the detected default branch** are eligible, and
deleting an unmerged one needs `include_unmerged: true` on the request **and**
`agents.project_organiser.branch_actions.allow_unmerged_delete` in config. The
default/protected/checked-out/worktree branches and anything ahead of its
upstream are never deleted, whatever the flags say.

`GET /api/units/*` is the service-discovery pair (Session 26): the sweep as
measured, and the sweep as ranked advice. Both are **GET-only and always
will be** — the fix for an unmonitored unit is an edit to a hand-curated
YAML file whose comments carry the reasoning, and the fix for an orphan is
`systemctl disable && rm`, neither of which a scheduled agent should do on
its own. A test asserts no non-GET route exists under `/api/units`.

**The sweep has two alert families, and the split is SNAG-ESTATE-001's
durable half** (Session 46). `ALERT_TITLE` is the rolled-up count of
everything worth doing eventually; `ARMED_TITLE_PREFIX` is one row per
**armed orphan** — a unit whose project is gone and which systemd will
nonetheless start. The roll-up cannot name anything, and that is the
whole defect: `Unmonitored systemd units: 17 findings` was open,
accurate and unread for eight days while two of those seventeen
restart-looped 52,178 times and stalled the kernel. The diagnosis was
complete, correct and machine-readable the entire time. A count is not
news.

**The "will it loop" test is arithmetic, not the presence of a
setting**, and the obvious rule is wrong in *both* directions.
`personalassistant-backend.service` declares no `StartLimitBurst=`, so
systemd's defaults apply (`DefaultStartLimitIntervalSec=10s`,
`DefaultStartLimitBurst=5`) — a limit **does** exist. It also sets
`RestartSec=10`, putting starts ten seconds apart, so five can never fit
inside a ten-second window: the limiter is unreachable and the unit
restarted 34,517 times without once entering `failed`. In the other
direction a bare `Restart=always` restarts every 100ms, five starts fit
easily, and the loop *is* terminal — so "no `StartLimitBurst=`" would
have opened a critical on most of this box's healthy services on its
first run. `restart_is_bounded` asks whether `RestartSec × (burst − 1) <
interval`, which is the sum Session 39 did by hand for `sysadmin.service`
(600s against 40s) and which `alfred-backend.service` also passes on a
hand-written `StartLimitIntervalSec=60`.

Both signals are **pure**, so `scan.py` keeps its no-subprocess promise:
`enabled` is an enablement symlink under a `*.wants/`/`*.requires/`
directory the sweep already walks (matched on link *name*, so a dangling
link left by an `rm` without a `disable` still counts), and the restart
keys are text it already parses. Agreed with `systemctl is-enabled` on
every unit on this box. What purity costs is `NRestarts` and `activating
(auto-restart)` — this says "armed to loop", never "has looped 34,517
times".

Five rules, three of them the opposite of the obvious implementation:

1. **Arming is orphan-only.** Every healthy service here is enabled and
   most restart unboundedly; an `armed` that meant "enabled" would alert
   on all of them. A *disabled* orphan is debt and stays in the roll-up
   — four of this box's six carry the PersonalAssistant shape exactly
   and are harmless only because someone disabled them.
2. **The sweep's exclusion set is what the run judged, not what it
   raised** — `sysadmin/estate/agent.py`'s rule, for its reason. Against
   a raised set a deduplicating family writes nothing on run two, has
   its still-true row swept, re-raises on run three, and each flip clears
   the tray's `{severity}:{title}` fingerprint.
3. **Escalation resolves the quiet row and raises a louder one**, and
   `step_for` refuses the reverse — an orphan whose `Restart=` is
   *softened* stays `critical` until it is actually removed, because a
   softer restart policy does not fix a start job that cannot succeed.
4. **`alert_threshold` does not govern this family.** That knob is
   patience for accumulated debt; an armed orphan is a unit failing on
   every trigger, and one of them is worth saying.
5. **A folded oneshot is armed by its *timer*.** Reading only the
   service's own enablement reports a live schedule as dormant.

`armed` is a **subset of `orphaned`** on `UnitScanSummary`, deliberately
outside the sum the model exists to make auditable, and its count is a
scalar in the `findings` blob rather than `len()` over the stored list —
that list is truncated at 200.

What this deliberately does **not** do is the general case:
`SNAG-UNITS-002` records that 15 of the 18 units on this box with a
`Restart=` policy cannot reach `failed`, including every live service
except `sysadmin`, `alfred-backend` and `alfred-frontend`. Fifteen rows
on the first run is the pile-up shape wearing a new hat.

**Three registries claim a port and only one of them cannot lie**
(Session 26c). `sysadmin/units/ports.py` is a sibling of `scan.py`, not
part of it — that module's no-subprocess promise is load-bearing and was
re-verified in Session 46. The three are the estate's markdown table in
`monitorable-project.md` (18 rows, project granularity, no units), this
repository's `services.yaml` (11 entries carrying **both** `port:` and
`systemd: {unit, scope}`, a hand-declared pair nothing had ever checked),
and the kernel via `ss -H -ltnp` → `/proc/<pid>/cgroup`.

estate-manager compares the first against the third and is
**structurally blocked from the interesting half**: its `live_listeners()`
runs `ss` deliberately without `-p`, on the stated grounds that *"process
names need privileges for other users' sockets"* — true, and true only of
*other users'*. Measured as `gaddi` on 2026-08-15: every
registry-relevant port on the box came back with a pid, and the cgroup
path names the unit **with scope in it** (`…/user@1000.service/app.slice/`
against `/system.slice/`) — the scope-aware identity `services.yaml`
already keys on, for free. Blank only for root-owned and containerised
sockets: 5432, 1883, 631, 139/445 and 8601. A test pins their `ss`
invocation, because if the estate ever adds `-p` this module is a second
implementation of their check rather than the half they cannot do, and
the right move then is to delete it.

**Four comparisons in two families, and the split decides the surface.**
`wrong_unit` (services.yaml says port P is unit U; the cgroup says V) and
`port_shared` (two units, one port) are the box disagreeing with itself
now — one alert row each, port in the title. `duplicate_claim` (two
registry rows, one port — invisible to the estate because `claimed_ports`
is a `set`) and `wrong_project` (the table's project against the one the
sweep matched the holding unit to) are a document being wrong while the
box is right — ranked advice, last in `KIND_ORDER`. That is the
armed-orphan split applied a third time, and `COLLISION_KINDS` lives in
`ports.py` rather than in the agent so the alert family and the advice
list cannot come to disagree about which findings are faults.

Six rules, four of them the opposite of the obvious implementation:

1. **Not-knowing is never a finding, and this fails _open_** — the
   `collation.py` posture, not `schema_guard`'s. An unattributed listener
   is compared against nothing; 8601 alone would otherwise produce a
   false positive on every sweep. A registry row naming something that is
   no project here (`_syncthing_`, and today `sysadmin-service` for 8500)
   lands in `unknown_registry_projects` as evidence: "wrong project" and
   "not a project" are different faults and only the first is ours.
   Filed as `SNAG-ESTATE-005` for the owner, never fixed here.
2. **A failed observation is not an empty one.** `ss` missing yields a
   report carrying the error and no findings, and `_maintain_port_alerts`
   then neither raises nor sweeps — the estate judge's rule 2, because a
   sweep scoped to a payload nobody received closes every row on the
   strength of not having looked. The registry half degrades separately:
   an unreadable document costs the two document comparisons and leaves
   the two live ones working, carried as `registry_error` beside `error`.
3. **A dual-stack listener is one holder.** A port bound on v4 and v6
   prints twice with the same pid, so `(port, pid)` is deduplicated —
   without it `port_shared` fires on every dual-stack server on the box
   and the family's first live run is entirely false positives.
4. **The port is the identity, never the kind.** Two kinds on one port
   are one thing to go and look at; a title carrying the kind forks the
   row the day a second kind arrives. Session 46's rule and
   `judgements.py` rule 5 meeting from opposite directions.
5. **The sweep's exclusion set is what the run judged**, not what it
   raised — the third time this repository has written that down.
6. **No escalation ladder, deliberately.** `critical` is what the tray
   leaves on screen and is reserved for a fault costing something now;
   this family has never had a member on this box, and a ladder tuned
   against zero observations is a guess with a number on it.

Verified live rather than only against fixtures, because the family
ships with **zero rows** — the same starting position as the estate
judge's. The whole agent path was driven against the real database in a
rolled-back transaction: the sweep stored `ports` with 31 listeners, 24
attributed and 12 units holding an audited port; a synthetic `wrong_unit`
then gave raise → hold → resolve across three runs, with **0 rows of
residue** after rollback.

`GET /api/units/status` gains `port_findings`, `port_collisions` and
**`ports_checked`**. The last one is the point: a sweep whose `ss` call
failed reports zero findings, and zero-because-clean must not be served
as the same answer as zero-because-blind. Every sweep stored before
Session 26c reports `false`, correctly.

The estate judge reads the sweep's attribution rather than running `ss`
itself, and that is a deliberate cross-domain read: two calls at two
moments (hourly judge, six-hourly sweep) would give two answers to one
question with neither surface saying which it used. The holder goes in
`details` and **never** in the title or message — the row's identity
belongs to the producer — and carries `observed_at`, so a five-hour-old
attribution says so. Absent attribution changes nothing; the enrichment
must never become a dependency of the alert.

`UnitRecommendationInfo` carries **no score or size field**, unlike its two
siblings. `RecommendationInfo` ranks by health-score points and
`FileRecommendationInfo` by reclaimable megabytes — both directly
measurable. Nothing makes two host units meaningfully "twice" one orphan,
so ranking is by `kind` (`orphan` → `unmonitored` → `host`) and no number
is invented to sort on. The one sub-ordering, added in Session 46, is
`armed` orphans ahead of dormant ones — a measured fact about whether
systemd starts the unit, not a score, and it does not make the tiers
comparable to each other.

**The snippet knows a port now** (SNAG-UNITS-001, fixed in Session 26c).
A `kind: systemd` check asserts only that the unit is *active*, so a
backend running while every request 500s is active, healthy, and broken.
The snag reasoned that a comment was the only honest fix *because* "this
scan does not know the unit's port" — true of the sweep, and no longer
true of its siblings. The entry now emits `kind: http` with `url:` and
`port:` whenever the unit holds **exactly one** port in the audited
range, and keeps `kind: systemd` plus the comment otherwise: zero ports,
two ports (picking one is a guess), or a timer, which holds no socket.

Two honest limits, both measured rather than assumed. Its **population
is empty today** — all 12 units holding an audited port are `monitored`,
which `classify_units` drops before they become findings, the same
two-thirds-invisible shape SNAG-UNITS-002 hit; driven as a
counterfactual it reproduces the hand-written `alfred-backend` entry
exactly. And the **health path is a guess**: `/api/health` is the
contract's, right for 4 of the 11 declared entries here and wrong for 7.
Kept anyway (`SNAG-UNITS-003`) because a wrong url fails loudly within
one poll while `kind: systemd` under-monitors silently for ever — the
trade `schema_guard` makes by refusing to boot.

Three rules the detector encodes, each learned from the live estate:

1. **Distro units are filtered by `is_symlink()`, not a package query.**
   `systemctl enable` installs a symlink into `/usr/lib/systemd/system`, so
   every packaged unit under `/etc` is a link and every hand-written one is
   a real file. No subprocess, and it works off Arch.
2. **A `Type=oneshot` service is reported under its timer.** A oneshot is
   `inactive (dead)` between runs by design, so monitoring the service
   alerts continuously — the rule config.yaml already records by hand for
   `alfred-evaluate`. The finding is keyed on the *service* (which holds
   `WorkingDirectory` and `ExecStart`) with `monitor_unit` naming the
   timer, and the timer suppressed, so one schedule yields one finding.
3. **Scope is part of a unit's identity.** `deadlock-api-ingest.service` is
   installed as both a user unit and a system unit here, running two
   different binaries; wiring one says nothing about the other, and the
   generated config.yaml `name:` gains a `-user`/`-system` suffix so two
   tray tiles cannot share one label.

`GET /api/services/reliability` (Session 25, Tier 1) scores the *services*
— the third scorer, after the project organiser's repositories and the
file organiser's disk. Score is `100 − downtime − instability`, both
individually attributable:

- **downtime** = `round(100 − uptime_percent)`, capped at 60
- **instability** = 5 per outage *episode* from the first, capped at 25

They are separate terms because they are separate failures. Live proof
on this estate: `internet` lost only 7.5 % of its checks but across three
incidents (−15 instability, −8 downtime), while `venture-assistant` lost
27 % in one sustained outage (−27, −5). Retry logic survives one long
outage and dies on three short ones, so a repeated failure must not
outrank a longer single one merely because it was up more of the time.

Four things this endpoint does differently from its siblings, each
learned from the live data rather than assumed:

1. **Computed live, never read back.** `/api/units/status` serves the
   latest stored sweep; this recomputes on every request (~28 ms for the
   whole estate). A stored score would be up to 24 h stale and would 404
   before the first nightly job. The `reliability_scores` table is
   history for trending, written by the 02:00 cron —
   deliberately an hour *ahead* of the 03:00 retention purge so the day's
   score is written before the checks behind it can be deleted.
2. **Incidents come from `service_health` transitions, not `alerts`.**
   The session plan named `alerts`; that table records one row *per
   failed check* — 123 rows for one internet outage, 81 for one
   `venture-assistant` outage — so mean time between alerts would measure
   `health_check_interval_seconds`. Consecutive non-ok checks collapse
   into one episode by construction, and it avoids a join on the
   unindexed `details->>'service_name'`, the only link `alerts` has to a
   service.
3. **Restart frequency is absent, though the plan named it.** Nothing
   records restarts: `systemctl show -p NRestarts` is a live cumulative
   counter never sampled into the DB, and `agent_runs` records agent
   executions. Three measured metrics beat four where one is invented.
4. **A gap in the series never costs points.** It means the *monitor* was
   down — deducting would charge the service for this application's
   downtime — so it lowers `confidence` instead. `confidence: low` means
   under 2 days of history or under 50 % of expected checks; anything
   recommending action off this endpoint must read it. Ordering ignores
   it on purpose: a thinly-observed failing service is still the most
   interesting row on the page.

The population is **the configured services**, not the distinct names in
`service_health`. Both differences matter: retired services (`ollama`,
`personal-assistant`) keep rows for 30 days and must not be scored, and a
service just added to config.yaml has no rows at all — which is a
finding, not an absence, so it is scored 100 at low confidence rather
than omitted. An expected-down service (`mute: true`, **or** listed in
`notifications.tray.mute_services` — the only way to mark one contributed
by projects.yaml, since those entries have no `mute` field) has its
deductions computed and reported with `waived: true` but not applied.

Retention needs **both halves**: a row in the `retention_config` table and
an entry in `TABLE_TIMESTAMP_MAP`. `run_retention` iterates config rows and
looks each up in the map, so a table with one half is silently never purged
— `project_reviews` and `disk_reviews` had neither, `unit_audits` had only
the map. Review tables get **365 days**, not the 30 that check data gets: a
weekly narrative kept for 30 days is four rows, too few to see a trend.
`KEEP_LATEST_PER` protects the newest row per entity (`"true"` means "the
whole table is one entity"), because a purge that emptied `project_reviews`
would make `GET /api/projects/review` 404 — which reads as "never generated"
rather than "none lately".

**The briefing envelope is additive, and `sections` is the part Alfred
owns.** `GET /api/sysadmin/briefing/preview` carries `schema`, `period`,
`summary`, `alerts[]` and `facts{}` *alongside* `sections` and
`generated_at` — never replacing them, because Alfred's `adapt_sysadmin`
reads both and returns one red error section if `sections` is missing.
Alfred owns the section contract by its ADR-0063 and normalises every
producer into it; this service owns the envelope round it. There is no
`generated` key beside `generated_at`: two stamps holding one value is a
fork waiting to happen.

Four rules `sysadmin/briefing/data.py` encodes:

1. **`generated_at` cannot express staleness on a pulled endpoint.**
   Alfred's check is real (`_producer_timestamp` → `produced_at`, flagged
   at a 12-hour gap) and cannot fire, because the payload is stamped when
   the request is answered — an organiser dead three days still yields a
   payload one second old. Every `facts` block carries `measured_at`,
   `facts.stale_sources` names anything over 26 hours, and `summary` says
   it in words. It caught `filesystem` at five days on its first live run.
2. **`period` is anchored to `schedules.briefing_hour`, not to the last
   pull.** Two consumers polling would each shorten the other's window,
   and storing a row per pull makes this route a pull log. `anchor` is in
   the payload because the wrong reading is the one a consumer assumes.
3. **`facts` is a projection, not a copy** — counts and identifiers,
   never the rows the sections render. A facts block containing the whole
   payload cannot be diffed, which is the only reason it exists. A test
   asserts every list in it holds scalars.
4. **`summary` is deterministic.** The two weekly reviews are LLM-narrated
   and pay for it with a figure-free prompt and a markdown stripper; a
   summary made only of numbers gains nothing from that and would take the
   06:00 path down with llama-server.

Both project sections read **one** snapshot query and one
`status == "active"` filter (SNAG-BRIEF-001: they used to disagree inside
one payload — 26 rows against 5). Health rows sort **ascending**, because
descending plus a cap shows only the projects sitting on 100. `next` is
capped at `NEXT_ACTION_CHARS` through `truncate_at_word`, which always
marks the cut (SNAG-BRIEF-002); `GET /api/projects/board` deliberately
serves the same field uncapped.

Adding a **new agent** touches four places, not one: the Python wiring in
`main.py`, a config class in `config.py`, the `chk_alert_agent` CHECK
constraint on `sysadmin.alerts` (a migration — the database rejects an
unknown agent name), and `self_monitor.AGENT_NAMES` (without which the
agent runs unwatched). `tests/test_units_api.py` pins the last two together.


Tray-only presentation (IconState, ICON_COLOURS, compute_icon_state) stays in
`sysadmin_tray/models.py`.

---

## Detailed Documentation

**Decision records** live in `docs/adr/`:

- **0002-estate-manager.md** — **moved 2026-08-11** to
  [estate-manager ADR-0001](../estate-manager/docs/adr/0001-estate-manager.md)
  (renumbered; a pointer stands at [docs/adr/0002-estate-manager.md](docs/adr/0002-estate-manager.md)).
  Why shared infrastructure gets an owner that is not an application, why
  the estate owns the broker's *schema* while each app still ensures its
  own identity, why provisioning is a boot oneshot and never a daemon,
  and why `LoadCredential=` rather than `config.yaml` or an
  `EnvironmentFile`. Read it before publishing to MQTT from here or
  before putting a secret anywhere near this repository. Cross-repo
  documents no longer live in this repository's `docs/guides/` — add
  them to estate-manager.
- **[0001-project-registry.md](docs/adr/0001-project-registry.md)** — why
  project identity moved into the repositories as `.project.yaml`, why
  `services.yaml` holds no paths, why persistence was deliberately
  deferred, and the still-open question of who owns project state. Read it
  before adding a table for project data or changing how projects are
  identified.

Guides: only **api_auth.md** (bearer-token auth setup) still lives in
this repository's `docs/guides/`. The four cross-repo guides —
`estate-map.md`, `monitorable-project.md` (which holds the port
registry), `alfred-briefing-integration.md`, `alfred-projects-page.md` —
**moved to `~/projects/estate-manager/docs/guides/` on 2026-08-11**;
pointers stand at the old paths. `monitorable-project.md` is still
enforced mechanically by this repository's Session 26 service-discovery
agent (`GET /api/units/actions`) — the document moved, the enforcement
did not.
