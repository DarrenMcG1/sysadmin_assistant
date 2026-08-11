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

**`ProjectOrganiserAgent` resolves alerts set-based**, unlike the two reference
agents which loop and call `BaseAgent.resolve_alerts` per recovered item. Their
populations are fixed by configuration; a project's is not — a project deleted
from disk never appears in a scan, so it can never be observed *recovering*,
and a per-project loop leaves its alert unresolved forever while retention
purges resolved rows only. That is how 1,664 rows accumulated by 2026-08-07,
326 sharing one title. `_resolve_recovered` asks the inverse question — which
open health alerts would this scan *not* raise — closing recovery, deletion,
rename and re-declaration as `archived` in one statement. Raise and resolve
both derive their title from `_alert_title`, because a hand-written resolve
pattern that matches nothing is invisible.

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

`UnitRecommendationInfo` carries **no score or size field**, unlike its two
siblings. `RecommendationInfo` ranks by health-score points and
`FileRecommendationInfo` by reclaimable megabytes — both directly
measurable. Nothing makes two host units meaningfully "twice" one orphan,
so ranking is by `kind` alone (`orphan` → `unmonitored` → `host`) and no
number is invented to sort on.

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

- **[0001-project-registry.md](docs/adr/0001-project-registry.md)** — why
  project identity moved into the repositories as `.project.yaml`, why
  `services.yaml` holds no paths, why persistence was deliberately
  deferred, and the still-open question of who owns project state. Read it
  before adding a table for project data or changing how projects are
  identified.

For comprehensive guides on specific topics, see `docs/guides/`:

- **monitorable-project.md** is enforced mechanically by the Session 26
  service-discovery agent — see `GET /api/units/actions`.
- **alfred-projects-page.md** — the spec for Alfred's projects page:
  `GET /api/projects/board`, what `next_action_source` obliges a consumer
  to render differently, and why the board must not be written into
  Alfred's own `trackables.projects` table.
- **estate-map.md** — what runs on this box and how it connects: the app
  inventory, the one app-to-app data flow (briefing → Alfred → glance),
  shared resources (GPU/VRAM, `~/models/`, PostgreSQL, Alfred's private
  MQTT), and which apps are grandfathered against which convention. Read
  it for anything spanning two projects; also pointed at from
  `~/.claude/CLAUDE.md`.
- **monitorable-project.md** — the contract new `~/projects` services must
  follow (port registry, `/api/health`, unit naming, oneshot→timer,
  projects.yaml wiring). Pointed at from `~/.claude/CLAUDE.md` so every
  new-project session reads it.
- **api_auth.md** — bearer-token auth setup
- **alfred-briefing-integration.md** — consuming the briefing from Alfred
