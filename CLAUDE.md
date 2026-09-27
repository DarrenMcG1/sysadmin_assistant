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
| Why a module is built the way it is | `docs/design/<domain>.md` (listed under Design reasoning below) | Before changing that module |

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

`dev` and `tray` are `[project.optional-dependencies]` here rather than
dependency groups, so **a bare `uv sync` prunes them** — pytest, ruff,
mypy and PyQt6 all go, and `uv run pytest` then falls through to
`/usr/bin/pytest`, which fails on `import estate`. The command is
`uv sync --all-extras`.

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

**Configuration source:** settings live in `config.yaml` (validated by Pydantic models in `sysadmin/core/config.py`); per-service topology lives in `services.yaml`, keyed by project id and resolved through the `.project.yaml` manifests via `estate.registry` (the parse moved to `estate-lib` on 2026-08-13, ADR-0005; `sysadmin/registry/` no longer exists). `projects.yaml` is retired — project state lives in each repository's `.project.yaml`, and the old file is kept as `docs/projects-registry-legacy.yaml` until its comments have all moved into `decisions:` blocks. **No environment variables are read** — there is no `.env` file. Database URLs are set under the `database:` section of `config.yaml`.

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
| `GET /api/health` | `HealthResponse` | response_model (the contract's path, one handler with `/health`; `services.yaml` polls this one, the tray probes the other) |
| `GET /api/sysadmin/status` | `StatusResponse` / `ServiceStatus` | response_model |
| `GET /api/sysadmin/resources` | `ResourceResponse` (+`RamInfo`, `DiskInfo`) | parse-side only (union "no data yet" shape; disk dict→sorted list) |
| `GET /api/sysadmin/resources/history` | `ResourceHistoryResponse` | response_model |
| `GET /api/sysadmin/alerts` | `AlertsResponse` / `AlertInfo` | response_model |
| `POST /api/sysadmin/alerts/{id}/ack` | `AlertAckResponse` | response_model |
| `POST /api/sysadmin/services/{name}/{action}` | `ServiceActionResponse` | response_model |
| `GET /api/sysadmin/services/{name}/details` | `ServiceDetailInfo` | parse-side only (raw `systemctl show` props, `[not set]` coercion) |
| `GET`/`POST /api/sysadmin/dnd` | `DndStatusResponse` | response_model |
| `POST /api/sysadmin/scan-all` | `ScanAllResponse` | response_model |
| `POST /api/sysadmin/reload` | `ReloadResponse` | response_model (auth; 200 whatever the outcome — `ok` carries it) |
| `GET /api/sysadmin/self` | `SelfMonitorResponse` / `AgentSelfHealth` | response_model |
| `GET /api/sysadmin/review` | `HealthReviewResponse` | response_model (404 = "no review yet") |
| `POST /api/sysadmin/review/generate` | `HealthReviewResponse` | response_model (auth; LLM optional — digest fallback) |
| `GET /api/sysadmin/events` | `EventMessage` | serialise-side only (SSE stream — each `data:` line, not a JSON body) |
| `GET /api/logs/recent` | `LogsResponse` / `LogEntryInfo` | response_model |
| `GET /api/logs/stats` | `LogStatsResponse` | response_model |
| `GET /api/logs/trends` | `LogTrendsResponse` (+`LogSignatureTrendInfo`, `LogSourceTrendInfo`, `LogTrendCoverageInfo`) | response_model (computed live — never 404s) |
| `GET /api/logs/actions` | `LogActionsResponse` (+`LogRecommendationInfo`, `LogIncidentMemberInfo`) | response_model (computed live) |
| `GET /api/logs/review` | `LogReviewResponse` | response_model (404 = "no review yet") |
| `POST /api/logs/review/generate` | `LogReviewResponse` | response_model (auth; LLM optional — digest fallback) |
| `GET /api/projects/managed` | `ManagedProjectsResponse` | response_model (the only `/api/projects` route this service serves — see below) |
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
| `GET /api/units/status` | `UnitScanResponse` (+`UnitScanSummary`, `UnitFindingInfo`) | response_model (404 = "no sweep yet") |
| `GET /api/units/actions` | `UnitActionsResponse` (+`UnitRecommendationInfo`) | response_model (404 = "no sweep yet") |
| `GET /api/services/reliability` | `ReliabilityResponse` (+`ReliabilitySummary`, `ServiceReliabilityInfo`, `ReliabilityDeduction`) | response_model (computed live — never 404s) |
| `GET /api/services/actions` | `ServiceActionsResponse` (+`ServiceRecommendationInfo`, `ServiceRecommendationMemberInfo`) | response_model (computed live off the same call `/reliability` serves) |
| `GET /api/services/by-project` | `ServicesByProjectResponse` | response_model (the only row whose consumer is another repository — estate-manager on 8400, not the tray) |

**Consumed from estate-manager on 8400** — parsed here, served there:

| Endpoint | Contract model | Enforcement |
|----------|----------------|-------------|
| `GET :8400/api/projects/overview` | `ProjectOverviewResponse` | parse-side only (tolerant parse; guarded by `tests/test_estate_project_contracts.py`) |
| `GET :8400/api/projects/{name}` | `ProjectDetailResponse` (+`ProjectHistoryPoint`) | parse-side only (history newest-first; tray reverses for plotting) |

**Served with no contract model** — the eleven routes the registry
deliberately does not hold, each with the reason it holds none. **Twelve
until `SNAG-DOCS-018` pinned `GET /api/services/by-project` on
2026-09-10**: it was excused for declaring `response_model=dict`, which
is a reason that describes the code rather than the payload, and a
reason a row can retire by being fixed is the one kind of exemption this
table is not for:

| Endpoint | Returns | Why no contract |
|----------|---------|-----------------|
| `GET /api/summary` | ad-hoc digest dict | single-call digest for the PA, not the tray — no `contracts.py` model binds it at either end |
| `GET /api/sysadmin/briefing/preview` | the briefing envelope | Alfred's `adapt_sysadmin` is the consumer and Alfred owns the section contract (its ADR-0063); the envelope round it is described in prose above |
| `GET /api/sysadmin/ports` | `{"ports": […], "count": n}` | a live `ss` reading with no stored shape; the *sweep*'s port findings are served under `/api/units/status`, which is pinned |
| `GET /api/sysadmin/status/{service}` | health-check history rows | no consumer — the tray reads `/services/{name}/details` instead |
| `GET /api/files/report` | the latest audit's raw findings blob | the findings lists are truncated before storage, so the payload is evidence rather than a shape a consumer parses |
| `GET /api/files/report/delta` | two scans differenced | same blob, twice; no consumer |
| `POST /api/files/scan` | `{"status": "scan_triggered"}` | tray-consumed (`client.py`), but it reads the **status code** and never the body |
| `GET /api/logs/errors` | error/critical rows | superseded in practice by `/api/logs/recent`, which is pinned; no consumer |
| `GET /api/logs/{source}` | rows for one source | the catch-all; the two `410` rows below are declared *above* it in the router, which is the only reason they are reachable at all. No consumer |
| `GET /api/logs/summary` | `410 Gone` | a tombstone (`SNAG-LOG-011`), `include_in_schema=False` — it answers no shape by design |
| `GET /api/logs/summary/history` | `410 Gone` | the same tombstone, second path |

**Membership is a property a test computes for the *routes* now, and until
2026-09-10 the sentence below claiming that was true only of the models**
(`SNAG-DOCS-014`). `tests/test_contract_reachability.py` walks field
annotations and base classes from every root — a property of
`contracts.py`, which says nothing whatever about what is served, so a
route added with no registry row was invisible to the very mechanism this
section named as its guarantee. `tests/test_claude_md_registry.py` sweeps
the routes, and the rule it enforces is mechanical rather than a
judgement:

**A route belongs in the registry iff a `contracts.py` model is bound to
it** — as `response_model=` on the producer side, or as the tray's parse
on the consumer side. **Both halves are computed** since 2026-09-10
(`SNAG-DOCS-017`). Seven rules, five of them the opposite of the obvious
implementation:

1. **The producer half is exact because FastAPI stores it; the consumer
   half had to be walked.** `response_model=` naming a class defined in
   `contracts.py` is readable off `create_app()`, because the binding is
   an attribute on the route object. Nothing holds the other binding: the
   pairing between the URL requested and the class the reply is handed to
   exists only as *adjacency in a function body*, so
   `document_claims.tray_consumption` is an AST walk of `sysadmin_tray/`
   or there is no computation at all. Measured 2026-09-10: **30** of 51
   live (method, path) pairs are pinned by `response_model=` and **28**
   of those had rows — the two that did not were `GET /api/logs/review`
   and `POST /api/logs/review/generate`, added above. **31 later the same
   day**, `SNAG-DOCS-018` having pinned `GET /api/services/by-project`,
   and all 31 carry rows; the route count is unmoved at 51, because that
   sitting added a model and no route. The tray parses
   **16** pairs with a `contracts.py` model, **14** served here and 2 the
   estate's; **6** of the 14 are pinned by `response_model=` as well, so
   **8 routes belong in this table by the consumer half alone** and their
   membership rested entirely on prose until the walk existed.
2. **A name in the tray is not a parse, which is why this was a second
   sitting rather than a wider `grep`.** `sysadmin_tray/models.py`
   re-exports `contracts.py` wholesale, so every model this table names
   is present under `sysadmin_tray/` for reasons unrelated to any route —
   a name-keyed sweep answers *true* for all of them, ships green, and
   measures nothing. The walk keys on the **call**,
   `Model.from_dict(resp.json())`: the verb, never the noun.
3. **The exemption table cannot hide a contract, on either side.** A
   route the producer has pinned is *refused* an entry there, so the list
   can only ever excuse what the code has already left unpinned —
   `check_markers` rule 1's refusal of a marker whose deletion retires a
   check, met from the other side. Deciding a route needs no shape stays
   a judgement; deciding one *has* no shape does not. **The same clause
   is now owed on the consumer side** — a route the tray parses with a
   contract cannot be excused either, which was unreachable before the
   walk and was what this rule was missing rather than a new rule.
4. **The exemption is declared in this document, never in the test.** A
   list living in the guard would protect the guard's knowledge and
   leave the reader exactly as misled — the failure `SNAG-DOCS-001` was,
   where fifteen departed endpoints stayed in this table and a reader
   concluded this service served them. `routes_by_prefix`'s rule: the
   document supplies the partition and the test checks it for totality,
   because zero-unaccounted-for must not read as nobody having looked.
5. **A path parameter's *spelling* is normalised away.** This table
   writes `{id}` and `{name}` where the handlers write `{alert_id}` and
   `{service_name}`, and a naive set comparison reports three phantom
   gaps beside three phantom stale rows. A parameter name appears in no
   URL a client builds, so pinning it would make the guard demand the
   document restate handler-local variable names — `interval_seconds`'
   rule, comparing the quantity rather than the spelling. Normalisation
   is **injective over the live set** (51 of 51 distinct), and a test
   pins that, because a collapsing instrument compares fewer things than
   it believes.
6. **The rows' *content* was measured before the membership sweep was
   written, and it was correct 36 of 36.** Every `response_model` claim
   has one, every `parse-side only` claim has none, and the first model
   named is the live `response_model` in every case — so that half of
   the guard ships with an empty finding population and says so. Only
   membership was incomplete, which is the direction `SNAG-DOCS-001`
   ran in reverse: a route served and unlisted, costing the tray, which
   reads this table to know what shape to parse. The eleven `parse-side`
   and `serialise-side` claims were likewise correct when the consumer
   walk first ran — **10 confirmed and the eleventh honest**, `GET
   /api/sysadmin/events` being a *serialise*-side claim about the way out
   rather than a tray parse. A correct population is the ranking and
   never the reason to leave a class uncomputed, which is the reading
   that mis-ranked `SNAG-LOG-010`'s parent.
7. **Four exemption reasons say *no consumer* and only one limb of that
   is checkable, which the guard's own name states.** Alfred and
   estate-manager are outside this checkout, so a test here can *refute*
   "no consumer" — the tray requesting the route is enough — and can
   never confirm it. `ports_checked`'s rule at the size of a reason cell:
   the narrower finding is reported as the narrower finding.
   `POST /api/files/scan` is the one reason confirmed in **both**
   directions, its claim being that the tray calls it and reads the
   status code rather than the body — requested by the walk, absent from
   its parses.

**Project state left this repository on 2026-08-13, and what remains is a
consumer.** [ADR-0005](docs/adr/0005-project-state-leaves.md) records the
move and estate-manager's ADR-0004 and ADR-0008 hold the other side.
`sysadmin/projects/` and `sysadmin/registry/` are **gone**: the scanner,
the roadmap parse, the board, `/next`, momentum, the nudge arithmetic, the
weekly project review, branch actions and estate.json emission are
`estate_service/projects/` on port 8400, and the `.project.yaml` parse is
`estate.registry` in `estate-lib`. The reasoning behind every rule those
modules encode — the latest-snapshot-per-name join and its
`newest_scan − 1h` cutoff, why `next_action_changed` is `None` and never
`False` at the oldest point, why `/next` ranks in days rather than scans,
why momentum matches a landing by date window rather than at the
transition scan — **moved with them and is worth reading there.** It is
not restated here, because a narrative describing another repository's
code in the present tense is precisely what `SNAG-DOCS-001` was.

Three things stayed, and holding them apart is the point:

1. **`GET /api/projects/managed` is still served here.** Its substance is
   live `service_health` joined to registry identity the library supplies
   — monitor data wearing a project-shaped path
   (`sysadmin/monitor/routers/projects_managed.py`). The tray keeps its
   URL. It is the only route under `/api/projects` this service serves;
   `GET /openapi.json` is the check, and it disagreed with this document
   from 2026-08-13 until this was written on 2026-08-17.
2. **Two routes are *consumed*, not served.** The tray fetches
   `/overview` and `/{name}` from **8400** and parses them with this
   repository's models — two models for one payload deliberately, a
   tolerant parse (`extra="ignore"`, every field defaulted) against a
   producer's guarantee (`response_model=`). Collapsing them would make
   the tray's defensiveness the producer's problem. The seam is guarded
   by `tests/test_estate_project_contracts.py`, whose recorded half
   catches consumer drift in CI and whose live half is the only thing
   that can catch the producer's.
3. **The estate's surfaces are judged here.** `/api/projects/invariants`
   and `/api/projects/attention` on 8400, read by `sysadmin/estate/` —
   the swap ADR-0005 records: the estate publishes and never acts, this
   repository judges and never scans. Neither judges itself.

**The registry describes only what this service serves or parses, and
membership is a property a test computes** (Session 77, `SNAG-DOCS-002`
closed) — of the **models**, which is the half stated here and the half
`SNAG-DOCS-014` found was being read as both; the route half is the rule
above. It carried eight project response models describing routes that
left on 2026-08-13 (ADR-0005) — the `SNAG-CFG-001` shape in the file this
document calls the contract registry. **Fifteen** models went, not eight:
`tests/test_contract_reachability.py` walks field annotations and base
classes from every root, and the eight dragged exactly seven members
reachable from nothing else. 83 classes became 68, 1,846 lines 1,460.

Four rules, three of them corrections to how the entry was measured:

1. **The property is reachability, never reference count, and the entry
   was measured three times by grep and wrong three times.** A member of
   a served payload has **no mention anywhere** and is load-bearing —
   grep reports 32 models with no external reader and **17** of them are
   that. Session 76 put `ProjectHealthInfo` in the dead set on exactly
   that evidence; it is a field of `ManagedProjectInfo`, the
   `response_model` of `/api/projects/managed`. Session 58 counted four
   re-exports and Session 76 three; it is **five**.
2. **A root is a name *used*, never a name *imported*** — the
   distinction Session 58 stated in prose ("a name in an import list and
   not a caller") and then measured with a tool that cannot draw it. So
   the detector is an **AST walk**: `ast.Import`/`ast.ImportFrom` are
   skipped, docstrings are `ast.Constant` and fall out for free (which is
   what made `RecommendationInfo` look alive off one line of prose in
   `units/recommendations.py`), and `response_model=` needs no special
   case because it is already an `ast.Name` in a keyword.
3. **Five names left the registry without leaving the wheel, and left
   the wheel on 2026-09-04** (`SNAG-DOCS-003` closed).
   `RecommendationInfo`, `ProjectRecommendationsResponse`,
   `PortfolioAction`, `PortfolioActionsResponse` and
   `ProjectReviewResponse` spent ten days in
   `sysadmin_tray/_deprecated_contracts.py` behind a PEP 562 module
   `__getattr__` warning on **access** rather than at import, because
   `sysadmin_tray` ships in the wheel and an import list is a published
   surface. **It had never been published**: 0 of 31 `sysadmin_service`
   wheels on this box carry `sysadmin_tray/` code (every one a uv
   *editable* stub), there is no git remote, and an AST sweep of 20,795
   `.py` files outside the checkout finds 0 importers — keyed on the
   **import**, because estate-manager defines all five names itself and
   a name-keyed sweep answers 5/5 and names the wrong party. The module,
   the `__getattr__`, `check_deprecated_contracts` and four of the five
   guard tests are gone; `test_none_of_them_are_defined_in_contracts`
   stays, on the half reachability cannot reach — a name returning
   *with a reader wired to it*.
4. **The guard's own blind spot was measured, and the removal closed
   it.** `tests` is a consumer package on purpose — a model exercised
   only by its round-trip test is consumed — so a name this suite *uses*
   is a root by that use alone. Driven at the **pre-fix** registry while
   the shim existed the walker reported **12** of the 15: three leaked in
   as roots, `PortfolioAction` and `RecommendationInfo` from the shim's
   own annotations and base class and `PortfolioActionsResponse` from
   `models.PortfolioActionsResponse` in the shim tests. Both sources went
   with `SNAG-DOCS-003` on 2026-09-04 and **the same drive at the same
   file now reports 15 of 15** — re-measured either side, not inferred.
   So the stated reason for keeping
   `test_none_of_them_are_defined_in_contracts` — *the only cover for
   three names reachability cannot judge* — **expired on the commit that
   closed the entry**, and the test now stands on a stronger claim:
   reachability asks whether a model is read, and this asks whether it
   belongs here at all, which is the case a name returning **with a
   reader wired to it** would pass and this would fail. The blind spot
   was visible at all only because the falsification was driven at the
   real pre-fix file rather than at a synthetic name, which passes
   cleanly — and a rule 3 base-class illustration went with it: that pair
   was the registry's only one, so the edge now has an **empty
   population** in `contracts.py` and is exercised by the synthetic
   alone, which the docstring states rather than leaving as silence.

Tray-only presentation (IconState, ICON_COLOURS, compute_icon_state) stays in
`sysadmin_tray/models.py`.

---

## Adding an agent

Adding a **new agent** touches four places, not one: the Python wiring in
`main.py`, a config class in `config.py`, the `chk_alert_agent` CHECK
constraint on `sysadmin.alerts` (a migration — the database rejects an
unknown agent name), and `self_monitor.AGENT_NAMES` (without which the
agent runs unwatched). `tests/test_units_api.py` pins the last two
together. If it is **scheduled**, that is two more: a `JobSpec` in
`core/jobs.py` and an entry in `main.py`'s `JOB_TARGETS` — planned and
unwired is a `KeyError` at startup, wired and unplanned never runs and
looks exactly like one that does.

---

## Detailed Documentation

## Design reasoning — moved to `docs/design/`

Until 2026-09-27 about 3,940 lines of per-session design reasoning sat
here, under the Contract Registry heading. It moved to `docs/design/`,
one file per domain, verbatim. **Read the domain's file before changing
a module it names**: each records which rules the module encodes, which
of them are the opposite of the obvious implementation, and what was
measured to settle them.

- `docs/design/notifications.md` — who speaks on this box (the tray, and `monitor/desktop.py` as its understudy), the escalation ladder in `core/escalation.py`, `reminder_hours`, and the understudy's reminder sweep and `desktop_notifications` store.
- `docs/design/logs.md` — the log aggregator: `log_signature.py`'s identity rule, the journal cursor, `log_trends.py`, `log_actions.py` and `known_noise`, incident correlation, `journal_command`, the `-p` and `-a` read fixes, `truncated_fraction`, the uvicorn loggers and `JournalLevelPrefixFormatter`, `format: json` and `message_backfill`, `COVERED_SIGNATURES`, and `spawn_manual_run`.
- `docs/design/alerts.md` — how alert rows open and close: `_resolve_recovered` and `RESOLVABLE_TITLE_PATTERNS`, the collation family (`monitor/collation.py`), `unresolved()` and the partial index, `refresh_alert`, and `may_quieten_in_place`.
- `docs/design/agent-runs.md` — `BaseAgent.run`'s three transactions, one savepoint per service, the `agent failing` family (`monitor/failures.py`), `core/unit_failure.py`, and the startup sweep in `core/abandoned_runs.py`.
- `docs/design/schema-and-storage.md` — `core/schema_guard.py` and `sysadmin-check-schema`, `metadata.py`'s autogenerate options and `FROZEN_TABLES`, and retention's two halves (`retention_config` and `TABLE_TIMESTAMP_MAP`).
- `docs/design/status-claims.md` — `sysadmin/ops_claims.py`: re-measuring `STATUS.md`'s opening block, the `<!--check:…-->` markers, and timed `expires` predictions.
- `docs/design/estate.md` — `sysadmin/estate/`: the estate judge and its surfaces on 8400, the queue's `waiting_reason`, `gpu_floor` and `vram_floor`, `ports` audit findings and transient holders, `judge_attention`, and the idle nudges and repository health score that are now the estate's.
- `docs/design/gpu.md` — `monitor/gpu.py`: the sysfs busy counter in place of `rocm-smi`'s, resolution by PCI slot, and `gpu_percent_source`.
- `docs/design/files.md` — the file organiser: the weekly disk review, `GET /api/files/actions`, the two rules every LLM-narrated review follows, the dry-run action endpoints, and branch pruning (now the estate's).
- `docs/design/units-and-ports.md` — service discovery (`GET /api/units/*`): armed orphans, `restart_is_bounded`, `units/ports.py`'s three port registries, and the generated `services.yaml` snippets.
- `docs/design/services.md` — `GET /api/services/reliability`, `service_recommendations.py` with `group_faults` and `action_from`, and `STATUS_READINGS` on `service_health.status`.
- `docs/design/health-review.md` — `GET /api/sysadmin/review` (`monitor/health_review.py`): alert deltas by distinct title, the coverage asymmetry, and why the route sits under `/api/sysadmin`.
- `docs/design/config.md` — `core/config_keys.py` and the tray's `tray_section_report`, the reload (`reload.py`, `RESTART_ONLY`), and the job plan (`core/jobs.py`).
- `docs/design/briefing.md` — the envelope `briefing/data.py` puts round Alfred's `sections`.

## Cross-repo friction is filed, not absorbed — a pointer

**The rule is estate-manager's and its canonical body is
`~/projects/estate-manager/docs/conventions/session-brief.md`**, section
"Cross-repo friction is filed, not absorbed" (owner's ruling 2026-08-25,
estate ADR-0041 and ADR-0042). The global `~/.claude/CLAUDE.md` now
carries a short section of its own ("File cross-repo friction; do not
absorb it") — this read "deliberately **not** in the global" until
2026-09-23, which was true when written and stopped being true when the
estate wrote the caps there (their ADR-0190). This is a pointer too, and
the headline is all that belongs here.

Headline: when a sitting hits friction crossing a repository boundary —
another repository's state it could not read, a decision it could not
find, a filing that collided, work it duplicated — it files a message
rather than working around it:

    POST http://127.0.0.1:8400/api/estate/messages
    {"sender": "sysadmin_assistant", "receiver": "<owner of the thing>",
     "summary": "one sentence", "detail": "optional"}

**One sentence in `summary`; the body, if there is one, in `detail`** —
capped at **1,000** and **20,000** characters, and an over-long field is
**rejected, never truncated**. The cap is a budget: `summary` is printed
whole into every session of the receiving repository at start-up, and
`detail` is not (estate ADR-0190, message `14692b4c`).

Default the receiver to `estate-manager`. **It is a message, not a
finding**: no severity, no deadline, no ageing, and the receiver is not
non-conformant for having caused it. The receiver closes it; the sender
may withdraw it. `~/.claude/hooks/inbox-notice.sh` is wired to
`SessionStart` and tells a sitting when something is waiting, so an
unread inbox is not a failure mode a session has to remember to check.

**This repository's first use was 2026-08-25**, message `6a330427`,
routing Session 33's blocker. The eight rankings that named that blocker
before then are not a record of neglect — the register did not exist
until that day, and it is worth knowing that the *route* is one day older
than this paragraph.

---

**Decision records** live in `docs/adr/`:

- **0002-estate-manager.md** — **moved 2026-08-11** to estate-manager
  ADR-0001 (renumbered; a pointer stands at [docs/adr/0002-estate-manager.md](docs/adr/0002-estate-manager.md)).
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
  `services.yaml` holds no paths, and why persistence was deliberately
  deferred. Its open question — who owns project state — was **answered
  against this repository** by ADR-0005 below. Read it before adding a
  table for project data or changing how projects are identified.
- **[0003-mqtt-credential-by-loadcredential.md](docs/adr/0003-mqtt-credential-by-loadcredential.md)**
  — why the broker password reaches this process through `LoadCredential=`
  and never through `config.yaml` or an `EnvironmentFile`.
- **[0004-estate-lib-client-core.md](docs/adr/0004-estate-lib-client-core.md)**
  — why `estate-lib` is a shared library rather than a copied client, and
  what this repository is allowed to import from it.
- **[0005-project-state-leaves.md](docs/adr/0005-project-state-leaves.md)**
  — **read this before writing anything about projects here.** The
  scanner, the board, `/next`, momentum, the nudge arithmetic, the weekly
  project review, branch actions and the briefing's project half left for
  estate-manager on 2026-08-13; `sysadmin/registry/` went to `estate-lib`
  as `estate.registry`. It records what stayed, what this repository
  gained (the judging swap), and what was left knowingly untidy —
  including the frozen `project_snapshots` / `project_reviews` tables —
  **dropped by migration 014 on 2026-08-24 together with
  `log_summaries`**, the estate's copy having been verified a superset
  first — and the `agents.project_organiser` config block that stayed
  parsed and mostly unread. **"Mostly" was the operative word and it was
  never measured until 2026-09-14**: Session 236 trimmed the block to the
  two leaves that do have readers — `projects_root` (seven) and
  `discovery_depth` (two, and in no `config.yaml`, so a sweep of the file
  alone reads it as dead) — and deleted the other eleven with the five
  nested models holding them. Estate side: their ADR-0004 (the decision) and ADR-0008
  (the migration's shape).
- **[0006-wiring-joins-ports.md](docs/adr/0006-wiring-joins-ports.md)** —
  **read this before adding a third check to `JUDGED_AUDIT_CHECKS`.**
  The estate's `wiring` check joins `ports` as a second audit check whose
  findings this repository speaks for, answering estate-manager's message
  `8462bcc5` and their ADR-0068 §4. It records what admits a check — an
  **ownership** test, never a severity — and why the constant had to stop
  being two scalars: the filter is a conjunction, `wiring` emits no
  `breach` at any code (their ADR-0067 §4 refuses one), and widening the
  severity globally re-imports `ports`' `claimed_but_silent`, which is
  availability and already owned here by `% unreachable`. Also records
  the four places the wiring family departs from the ports family — the
  identity is `subject` + `detail['event']`, which is the **reverse** of
  the ports rule; the kind is read from `detail`'s shape and never from
  `code`; there is no roll-up, because the population is bounded by the
  estate's own `hooks/` directory; and `critical` was refused.
- **[0007-a-poisoned-gpu-context-is-a-predicate.md](docs/adr/0007-a-poisoned-gpu-context-is-a-predicate.md)**
  — **read this before giving any reset-opened condition an owner.** The
  question *"who owns the state a GPU reset opens, and who closes it"* has
  no answer because there is no state: *"this service holds a GPU context
  created before the last reset"* is a predicate over two instants the box
  already publishes — a unit's `ActiveEnterTimestamp` and the newest
  `log_entries` row keyed by `CRITICAL_SIGNATURES` — so the unit's own
  restart moves the first past the second and the next poll recomputes it.
  The owner is the check that already writes the `service_health` row, so
  the second-owner defect is avoided by construction. Records why the
  reading is `degraded` and not `unwatched` (`skipped` means *nobody looked
  by declaration*, and `UNMEASURED_STATUSES` would excuse the outage as a
  decision — `SNAG-SVC-001` in reverse), why the population is a
  declaration in `services.yaml` rather than `role: inference` (measured:
  `venture-embed` runs `-ngl 0` and served **267 of 823** successful
  embeddings while the predicate was true), and the three measurement traps
  — `journalctl -k` implying `--boot=0`, second-granular `@epoch`
  truncation erring toward over-reporting, and an empty
  `ActiveEnterTimestamp` on an inactive unit.
- **[0008-the-file-half-of-the-wiring-check.md](docs/adr/0008-the-file-half-of-the-wiring-check.md)**
  — **read this before moving a check between repositories, or before
  reading a green `wiring` result as evidence.** The owner recommended
  that estate-manager's whole `wiring` audit check move here, because
  their ADR-0132 lets an estate session write `settings.json`'s `hooks`
  key and the check therefore audits its own writes. Half was taken and
  half declined, and the argument is the transferable part: the check
  compares two **operands** — the hook scripts' `estate-hook-event:`
  declarations and `~/.claude/settings.json` — and ADR-0132 removed the
  independence of the second, so relocating the **comparator** leaves
  both operands the estate's and a green result means exactly what it
  meant before. What decides the split is that the four codes do not
  take the same inputs: `settings_unparseable` and
  `settings_not_an_object` read the file **alone**, need no statement of
  the estate's, and carry the consequence the check exists for, so they
  are `sysadmin/estate/hook_wiring.py` and a **sixth surface** here; the
  two per-hook codes need the estate's declarations and stay theirs.
  Also records that two clauses of ADR-0006's admission test were
  falsified the same morning — the file is a symlink into
  `~/projects/dotfiles`, registry-`active` since 2026-09-08, so *"in no
  repository at all"* is false — while the clause that decides,
  *"nobody says it at all"*, held on re-measurement; why ADR-0006 §7's
  refusal of a sixth surface is superseded by its own stated reason; and
  why the estate's file-level findings stop being judged here rather
  than being judged twice.
- **[0009-the-remote-is-two-questions.md](docs/adr/0009-the-remote-is-two-questions.md)**
  — **read this before publishing anything from this repository, or
  before reading its remote as a backup.** "Where does the remote go" is
  two questions with two deadlines: the second copy had a live cost
  (`services.yaml` is the monitoring configuration for all 32 declared
  services and existed on one disk), and publication has none — so the
  private push landed at once and public is deferred to its own sitting.
  Records the audit measured over all 347 commits (**zero** key-shaped
  strings in any blob; `api.auth_token` has held `""` and nothing else;
  no `.env`/`*.pem`/`*.key` ever existed; the owner's real name in no
  file content — *that last cell is corrected by ADR-0010 §5: the ADR's
  own commit put the address into file content by quoting it, so the
  finding was falsified by being written down*) and, more usefully,
  **why it was boring** — ADR-0003 and
  the empty-token-with-a-warning design had already made a secret
  unable to land here, neither taken with publication in mind. Records
  what publication still owes as **disclosure rather than secrets** (26
  private project names, 38,774 lines of narrative about a private box)
  and three refusals: a history rewrite, because **116** commit SHAs are
  cited across this repository's own documents; a curated public mirror,
  because two repositories holding one history is the second-owner
  defect arriving as a release process; and publishing first, because a
  remote is reversible and indexing is not. §6 keeps the residue
  explicit: this is a copy of the *repository*, not of the `projects`
  database.
- **[0010-publication-was-one-option-wearing-three.md](docs/adr/0010-publication-was-one-option-wearing-three.md)**
  — **read this before reasoning about what is disclosed by writing
  here, and before trusting an option list in a handoff.** This
  repository is **public** as of 2026-09-09, verified unauthenticated.
  ADR-0009 deferred the question and Session 205's handoff stated three
  options — accept the 26 private project names, redact them, or ask
  their owners — of which **two were unavailable and nothing new had to
  be measured to see it**. *Ask their owners* is empty: all 26 resolve
  to the owner's own accounts, so the claim that they name third
  parties was a **scope** claim and false. *Redact* is unreachable by
  ADR-0009's own §2 argument, that publication exposes every commit and
  a blob is served at its SHA for ever — the names entered history on
  2026-08-04, so redaction means the history rewrite §4 refused over
  116 cited commit SHAs; only **2 of 26** were ever reachable by a
  working-tree edit. And the owner's standing ruling to publish the
  roadmap as-is had **already decided most of the open item**, because
  19 of the 26 names are inside that narrative (`Alfred` 144 times,
  `venture-assistant` 51) — the two ADR-0009 list items overlap and
  nobody had measured the overlap. Also records the sweep ADR-0009
  never ran (**third-party personal data**, zero across all 348
  commits, which is what the two school-sounding project names
  demanded), why the audit was re-run at *N+1* commits, and §7's three
  non-consequences — the box is still not backed up, the
  monitorable-project contract is unchanged though its
  `services.yaml` **comments** are now published, and the measured
  audience for the announcement was two repositories, not the estate.

- **[0011-a-cited-register-id-is-a-claim-about-this-repository.md](docs/adr/0011-a-cited-register-id-is-a-claim-about-this-repository.md)**
  — **read this before writing a commit message that cites a cross-repo
  register message id.** The rule: the citing sentence carries one clause
  saying what the message said, and an id for a filing *this* sitting made
  is written **whole** while one for a message this repository *received*
  stays **short**. Records that the owner devolved the question on
  2026-09-10 (each repository decides for itself, the estate publishes the
  method), so the standing refusal in `SNAG-DOCS-016` expired rather than
  being overruled. What decides the two halves is **compulsion, not the
  gloss rate**: the announce-by-filing rule requires the id for the 31
  sites citing our own filing and requires nothing for the 47 citing one we
  received — and the gloss-rate split that would have argued the same case
  is a *reading* two careful readers inverted (estate-manager 17/31 own
  against 22/43 received; this tree's own reading 12/31 against 27/47, with
  aggregate gloss agreeing at 39 either way). Also records why **disclosure
  is not a term** — the register is a live service whose 136 rows no tree
  holds, so resolvability turns on `:8400` and retention rather than on who
  can read the tree — and four structural hypotheses for *why* half the
  corpus is bare, **all four refuted**, which is what leaves the rule
  binding the sitting rather than a template.

Guides: only **api_auth.md** (bearer-token auth setup) still lives in
this repository's `docs/guides/`. The four cross-repo guides —
`estate-map.md`, `monitorable-project.md` (which holds the port
registry), `alfred-briefing-integration.md`, `alfred-projects-page.md` —
**moved to `~/projects/estate-manager/docs/guides/` on 2026-08-11**;
pointers stand at the old paths. `monitorable-project.md` is still
enforced mechanically by this repository's Session 26 service-discovery
agent (`GET /api/units/actions`) — the document moved, the enforcement
did not.
