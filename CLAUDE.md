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

**Consumed from estate-manager on 8400** — parsed here, served there:

| Endpoint | Contract model | Enforcement |
|----------|----------------|-------------|
| `GET :8400/api/projects/overview` | `ProjectOverviewResponse` | parse-side only (tolerant parse; guarded by `tests/test_estate_project_contracts.py`) |
| `GET :8400/api/projects/{name}` | `ProjectDetailResponse` (+`ProjectHistoryPoint`) | parse-side only (history newest-first; tray reverses for plotting) |

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
closed). It carried eight project response models describing routes that
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
3. **Five names left the registry without leaving the wheel.**
   `sysadmin_tray` ships in it, so removing a name from
   `sysadmin_tray/models.py` is a change to a published surface;
   `sysadmin_tray/_deprecated_contracts.py` holds
   `RecommendationInfo`, `ProjectRecommendationsResponse`,
   `PortfolioAction`, `PortfolioActionsResponse` and
   `ProjectReviewResponse`, resolved by a PEP 562 module `__getattr__`
   that warns on **access** rather than at import — warning at import
   fires on every tray start whether or not anything touched a
   deprecated name, which teaches the reader to filter the category.
   The set is closed under its own references, so the move cannot strand
   a served payload. Removal is `SNAG-DOCS-003`.
4. **The guard's own blind spot is measured and stated rather than
   implied.** `tests` is a consumer package on purpose — a model
   exercised only by its round-trip test is consumed — so a name this
   suite mentions is a root by that mention alone. Driven at the
   **pre-fix** registry the walker reports **12** of the 15: three leak
   in from the shim's own annotations and from `models.PortfolioActionsResponse`
   in the new test. `test_none_of_them_are_defined_in_contracts` is what
   covers those three — two tests composing rather than one doing both,
   and visible only because the falsification was driven at the real
   pre-fix file instead of a synthetic name, which passes cleanly.

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

**A monitor that only speaks in the present tense makes every recurring
fault look like today's news** (Session 27, Tier 1). `log_signature.py`
gave the aggregator one open row per distinct fault and ended a
598,091-row pile-up; what it could not say is whether a fault is *new*.
`sysadmin/monitor/log_trends.py` is the pure module that can —
`reliability.py`'s shape, for its reason — and `GET /api/logs/trends`
computes it live in **88 ms**.

Four rules, three of them the opposite of the obvious implementation and
all four settled by the live table rather than by argument:

1. **The signature is applied in Python, over rows the database has
   already grouped.** Normalising in SQL with `regexp_replace` is a
   second implementation of the identity the *alert* family is keyed on,
   and it drifts exactly as a regex over `alembic/versions/*.py` drifts
   from the revision graph. What makes the honest version affordable is
   measured: **626,906 rows collapse to 44 distinct messages in 91 ms**.
   The reduction is a property of this data, not a bound — a service
   embedding a request id in every line has one group per line — so the
   caller caps the set and reports `truncated`. Note the
   anti-correlation: the messages that do *not* collapse under `GROUP BY
   message` are the ones the signature helps most.
2. **"New" is a first sighting, measured against all retained history.**
   `previous == 0` was the obvious test and one live row refutes it: the
   Bluetooth firmware signature reads `current=39,919, previous=0` and
   has been storming since 2026-07-15, so it would have headed "new
   errors this week" on its fifth outbreak. It comes out `returned`. The
   8 genuinely-new signatures include `Bluetooth: hciN: failed to reset
   (-N)` — a *distinct* signature a source-level key would have masked.
3. **A gap lowers confidence and never becomes a trend** —
   `reliability.py`'s rule 4 — but **truncation is the signal and poll
   count only the proxy**, which is the reverse of the obvious ordering.
   A missed poll is caught up by the journal cursor, so data is lost only
   when a catch-up read hits `max_entries_per_read`, which the agent
   already records as `details['truncated_sources']`. Counting polls
   alone charges a fully-recovered gap as data loss. **Decisive in
   proportion, not as a flag** (Session 63): the gate is
   `TRUNCATION_LOW_FRACTION` over the *instrumented* reads, and it can
   exist at all because truncation is **one-directional** — it drops
   entries, so it only ever makes a count too low. `HIGH` is untouched
   and still means nothing was lost; only the floor beneath it moved.
4. **Counts are never scaled by coverage.** The cursor makes ingestion
   non-proportional to poll count, so a rate computed from observed time
   looks precise and has a divisor wrong in an unknown direction.

The population is **wider than the alert family's** — `warning` too,
because Tier 2's whole question is about a warning.

**Advice has to be executable, and this is the first sitting here to
build the mechanism a recommendation names** (Session 27, Tier 2).
`sysadmin/monitor/log_actions.py` ranks `new_signature` → `surge` →
`noise`, kind before volume, with no invented number merging them —
`FileRecommendationInfo`'s ordering, and its currency argument one step
further: `occurrences` is a third unit, so it is a third model rather
than a third meaning for `points`.

Tier 2's scoped example — *"this warning appeared 400× — add to
known-noise or fix it"* — named a list that did not exist, which is
Session 48's defect in advance: a row saying "paste the snippet below"
with no snippet is an item no execution sitting can close.
`agents.log_aggregator.known_noise` is that list. Four rules:

1. **Keyed on `(source, signature)`, never the signature alone.**
   `Failed with result 'exit-code'.` is logged by six services on this
   box; declaring it noise on the strength of one silences a genuine
   failure in five.
2. **Quietened, never suppressed** — `info`, the only rung below
   `tray.notify_min_severity` here, the same derivation as
   `judgements.TRANSIENT_HOLDER_SEVERITY`. The row still exists, still
   counts occurrences, still appears in the trend. Dropping it rebuilds
   `SNAG-CFG-001`'s shape: a decision taken by a consumer with nothing
   recording that it was taken. `reason` is a required *field* rather
   than a YAML comment, because an endpoint serves it back.
3. **Nothing is recommended as noise on volume alone, and a `LOW`
   confidence report recommends none at all.** Volume is what makes a
   fault worth looking at, not evidence it is harmless — so a `noise`
   row also requires the signature to be old and flat, or the endpoint
   recommends silencing an outage on its second day. The confidence gate
   is asymmetric: `new` rows survive a gappy series, because a gap can
   hide a fault and never invent one.
4. **The quietening reaches a row that is already open**, which
   `SNAG-ESTATE-010` said nothing did until this rule was lifted out of
   here into `core/escalation.may_quieten_in_place` on 2026-08-28 — and
   this family cannot wait it
   out, since a signature loud enough to declare is by definition one
   that never goes quiet, so its row never resolves. Session 39's ban on
   in-place severity changes is **asymmetric and that is what rescues
   it**: an escalation must be *heard*, so an in-place bump keeps a
   fingerprint the tray has suppressed; a quietening must be *silenced*,
   and `{severity}:{title}` becoming `info:…` is dropped by `_consider`
   before it can notify. The mechanism that makes escalation fail is what
   makes this work, so it is one-directional by construction.

**Three of the emitted commands did not work, and only a live run said
so.** The draft emitted `journalctl -u kernel` (the kernel is not a
unit — `read_journal` has always known that, so the same fact was stated
twice and one was wrong), omitted `--user` for the **7 of 14** declared
sources that are user units (measured by running both: 2,170 lines with
the flag, 1 without), and grepped on the *normalised* signature, whose
`N` placeholders match no real line and whose first token is usually the
unit's own name. `journal_command` fixes all three and the docstring
carries why, because the fixtures were green throughout.

Two limits were filed rather than implied. `SNAG-LOG-001`: one mosquitto
crash produced four recommendations, because systemd narrates it in four
lines that are four genuine signatures — a cap would hide the fourth
without saying the four were one thing, so the real fix was a correlation
rule nobody had measured. `SNAG-LOG-002`: the `noise` family had an
**empty population on this box**, because 118 truncated runs made
confidence `LOW`.

**The correlation rule exists now, and the relation it keys on is
systemd's, not the clock's** (Session 68, `SNAG-LOG-001` closed).
`log_actions.group_incidents` collapses first sightings that share a unit
**or a declared systemd dependency** inside `INCIDENT_WINDOW_SECONDS`,
and `units/scan.py` supplies the graph: `UnitFile.relations` and
`declared_relations()`, off the same files the sweep already opens. Live,
`GET /api/logs/actions` went **24 → 11** and the specimen's six rows
became one, naming all six signatures and emitting one `journalctl -u … -u …`
that was run and works.

Five rules, four of them the opposite of the obvious implementation and
every one settled against the live box rather than by argument:

1. **The declared graph is enough, and the interesting measurement was
   *which directories*.** `mosquitto.service` is packaged, so
   `discover_units` excludes it as distro-owned and its file sits in
   `/usr/lib/systemd/system`, which the sweep never walks — so the
   obvious move was to widen the walk. **Parsing `/usr/lib` as well reads
   629 further unit files and yields zero further relations** between the
   fourteen declared log sources, because a relation is declared by the
   unit that *depends* and on this estate that unit is always the
   hand-written one. `scan.py`'s no-subprocess promise was never in
   question; the effective graph `systemctl list-dependencies` resolves
   was not needed.
2. **The graph is the filter and the window only bounds it.**
   `alfred-backend.service` failed **1.2036 s** after the crash — inside
   any usable window — because PostgreSQL was still starting up, and
   `sportsanalyser-backend.service` failed **2.9 s before** it. Neither
   is reachable by a clock and both are excluded by the graph. Driven as
   a counterfactual rather than asserted: forging one edge admits
   alfred-backend, and removing the graph reproduces the entry's own
   proposal exactly.
3. **One hop, never transitive closure.** Six user units here declare
   `After=network-online.target`, so a second hop makes every
   network-using service one incident and the rule degenerates into
   "same window", which rule 2 has just refused.
4. **Every member is measured against the anchor, never the group.**
   Single-linkage lets a chain walk arbitrarily far from where it
   started, so a service retrying every 5 s would grow one incident
   across a whole outage. The anchor is the earliest first sighting,
   which is also what an incident *is*.
5. **First sightings only, so the roll-up's rung arithmetic is
   vacuous and says so.** `first_seen` is an incident moment only for a
   first sighting; a `SURGED` signature's is weeks old, and grouping
   surges on `last_seen` instead would put every active surge in one
   "incident". Every member therefore shares one kind, so
   `judge_attention`'s "take the loudest rung you swallow" has nothing to
   decide — absent because vacuous, not because forgotten. The rule is
   observable only at the window's edge, and that is where it is tested.

`INCIDENT_WINDOW_SECONDS = 5.0` is **derived, and what was derived is a
gap rather than a number**. Across the 21 live first sightings the
separations are bimodal with nothing between them: every
genuinely-one-incident pair lands inside **349 ms**, and the nearest
genuinely-two-incidents pair is **64.4 s** apart. Every value between
produces identical output, so the geometric midpoint sits three orders of
magnitude from anything it could get wrong — unlike
`NOISE_MIN_OCCURRENCES`, which is invented and says so.

The roll-up **names every signature it swallows** and truncates each to
`SIGNATURE_DETAIL_CHARS` instead — `SNAG-ESTATE-001`'s rule, since
dropping a member rebuilds the count that cannot name anything, while
shortening one does not. `LogRecommendationInfo.source`/`.signature` stay
the **anchor's** rather than becoming lists, so a consumer ignoring
`members` still gets a correct row about the fault that happened first.

Three things the sitting corrected in what was written down. The entry's
stated **mechanism was backwards**: systemd started the oneshot **2 ms
after** mosquitto had already failed, because the relation is `Wants=`,
which does not propagate failure — the provisioner then failed on its own
connect. The whole window is a **boot** beginning twelve seconds earlier,
which nothing in three sittings had noticed and which is exactly why a
same-window rule is dangerous here. And the rule collapses
`sysadmin.service`'s raw-JSON rows from **10 recommendations to 3**
(`SNAG-LOG-008`), seven of them one agent run's alerts inside 1.7 ms —
a byproduct that does not close that entry, which is about the signatures
being unreadable rather than about how many rows they occupy.

Two costs are filed rather than implied. `SNAG-LOG-009`: `journal_command`
formats a UTC-rendered timestamp into a `--since` journalctl reads as
**local**, so every command is an hour early here and would be five hours
*late* — missing the incident entirely — west of Greenwich; found by
running what the new row emits, Session 27's rule catching a fourth
command. `SNAG-UNITS-006`: `discover_units` skips `*.service.d/`
directories, so a relation added by drop-in would silently fail to
correlate — empty population today, measured, since neither of this box's
two drop-in directories belongs to a unit the sweep sees.

**The first of those is fixed, and the fix was already in the repository
one module over** (Session 71, `SNAG-LOG-009`). `journal_command` now
takes a **`datetime`** rather than a rendered string, and
`journal.since_timestamp` — which has emitted `@<epoch>` and stated this
exact reason since the module was written — owns the rendering. So the
defect was never a missing conversion: three callers each formatted
`f"{first_seen:%Y-%m-%d %H:%M}"`, implementing a fact a fourth function
already owned, which is the `-k` bullet in `journal_command`'s own
docstring met from a third direction. Taking the *type* is what makes a
fourth caller impossible rather than merely unlikely.

Four rules, three of them corrections to what the entry proposed:

1. **`astimezone()` was the weaker fix and would have shipped green.**
   It renders a *local* wall clock — correct on this box, verifiable,
   and still ambiguous: right only while the process writing the command
   and the human running it share a zone, and an autumn-fold local time
   names two instants. `@<epoch>` carries no zone at all, so it is
   unambiguous rather than merely correct here.
2. **The tests were what hid it, so they now model the consumer.**
   `TestJournalCommand` pinned the *rendering*, which is how a wrong
   command stayed green across three sittings; `_journalctl_reads`
   resolves the emitted argument the way journalctl does — `@<n>` as an
   instant, anything else as the reader's local clock — and the same
   assertion runs in London, New York and UTC. All four new tests were
   falsified against the behaviour they replace, the truncation-direction
   one needing its own (`int` → `math.ceil`, which opens the window 1 s
   *after* the event).
3. **`since_timestamp` refuses a naive datetime.** `timestamp()` reads
   one as local, which is precisely the reading being removed, so
   accepting it would rebuild the defect inside its own fix with the
   right-looking type — `schema_guard`'s fail-closed posture, not
   `collation.py`'s. Empty population by construction: every caller
   reads `logged_at`, a `timestamp with time zone`.
4. **The prose is labelled, never converted.** `detail`'s "First seen …"
   and the incident line's "within Ns of …" render the same instant the
   command points at and now say `UTC`, so the fix leaves no row
   disagreeing with itself. Rendering them *local* was refused: the
   command had a timezone taken out of it, and putting one back beside it
   is the opposite direction — and the label agrees with
   `GET /api/logs/trends`, which serialises `first_seen` with a `+00:00`
   offset.

Measured at two timezones rather than reasoned about. The specimen is
stored `2026-08-22 18:10:16.115268+01`; the emitted `--since
'@1787418616'` resolves to exactly that. On this box the old form lost
**one** line, which is the trap stated precisely — BST makes the error
*widen* the read, so the box that would notice is the one that never runs
the command. Re-run under `TZ=America/New_York` the epoch form is unmoved
at **57,695 lines** and the wall-clock form returns **48,946**, opening
`17:10:00 -04:00`, four hours past the incident and without it. The rule
is *N* hours late at UTC−*N*, so the entry's "five hours" is EST and four
is EDT.

**A row's identity is the fault, not the source — and the advice endpoint
was the last surface where it was not** (Session 72, `SNAG-LOG-010`).
`SNAG-AGENT-005` moved the signature *into* `alert_title` because four
open rows reading `Log error: kernel` are indistinguishable to whoever is
looking at them. Every title in `log_actions.py` was still built from
`source` and a number, and sibling rows share both: live, `GET
/api/logs/actions` served two rows reading exactly `kernel: 39885
occurrences, unchanged`. `quoted_signature()` now appends the signature
to all four, bounded by `capped_signature()` at `SIGNATURE_DETAIL_CHARS`
with `truncate_at_word`, and `log_review._quoted_signature` keeps only
its `figure_free` gate and borrows the rest — so a review line and an
advice title cannot write one signature two ways.

Four things settled by driving the producer rather than reading it:

1. **The family the entry named is the smallest of the three affected.**
   It scoped the defect to `noise` and ranked it last on "population is
   currently zero". At the 2026-08-12 anchor **14 of 21 rows collided in
   five groups**; at the live anchor the `noise` population genuinely
   *is* zero and **7 of 9 rows still collided**, all `severity: risk`.
   Reading the code confirms the entry; running `recommend()` against
   the live table refutes it.
2. **The cut is marked now, and it was the module lending the constant
   that was slicing.** `log_review._quoted_signature`'s docstring says
   an unmarked cut is `SNAG-BRIEF-002` and is *worse* on a signature,
   because a reader may try to match it against `GET /api/logs/actions`
   — which is this module, which was cutting **12 member signatures
   per request** mid-word, one ending `"message": "alert_raised",
   "service"`. `SAMPLE_DETAIL_CHARS` names the second bare slice, which
   had been written twice.
3. **The noise title claimed a direction it could not know.**
   `unchanged` was asserted for all four change kinds
   `_is_noise_candidate` admits, and the live pair classifies `FALLING`
   — 39,885 this window against 77,496 last — so the title asserted
   flatness about a signature that had halved while its own `detail`
   printed the contradiction. The count stays, because Tier 2's question
   is about volume; the direction goes, because `detail` states it and
   `change` decides it.
4. **The cost is `SNAG-LOG-008` becoming visible, and it is the trade
   `alert_title` already made.** Four of the nine live titles now open
   with `{"timestamp": "N-N-N …`, and an ugly title a reader can tell
   apart beats a tidy one they cannot — `SNAG-LOG-003` paid this exact
   price for the alert family. What the cap leaves is `SNAG-LOG-013`: 9
   of 55 signatures share their capped prefix and one live incident row
   lists **7 members identical after capping**, which is the roll-up
   naming nothing one level below the titles. Its population empties by
   retention the same afternoon it was filed, and the entry says so —
   because "population is zero" is what mis-ranked its parent.

Note what was pinning the titles: one assertion,
`rows[0].title.startswith("New fault from")`, which the defect passes
intact — `TestJournalCommand` one sitting over. All nine new tests were
falsified against the behaviour they replace, and one had to be
strengthened before it could be: it compared the two modules' quoting on
a *short* signature, where a slice and a marked cut agree, so it passed
against the broken code.

*That entry named the wrong culprit and Session 60 corrected it against
`agent_runs`: the 118 are **kernel 103, sysadmin-service 14** out of
**10,064 runs**, and **104 of them fell on one day**, 2026-08-12. Since
`_confidence` is `runs_truncated > 0` — binary, not proportional — the
family is available only between kernel storms, and the volume fix below
did not close it.*

**The ceiling counted the wrong lines, and the number was never the
problem** (Session 62, `SNAG-LOG-002` ceiling half). `read_journal`
bounded the read with `-n 500` and then applied `severity_filter` in
**Python, over lines the ceiling had already counted**. Across the
2026-08-12 storm: **203,042 raw kernel lines carrying 81,216 storable
ones — 40 %**, a median of **510 raw a minute against a ceiling of
500**, so **208 of 210 storm minutes truncated** and the 100
instrumented storm minutes produced **103 truncated reads, one per
poll**. Passing `-p` to journalctl makes the same 500 carry 500 storable
entries: verified against the real journal, the stored multiset is
**identical** and efficiency goes 40 % → 100 %, so the effective ceiling
rose 2.5× with **no edit to `max_entries_per_read`** — raising it would
have bought the same headroom at 2.5× the memory and left the waste.

Four rules, three of them the opposite of the obvious implementation:

1. **`max_priority_for` is derived from `PRIORITY_MAP`**, never written
   beside it — `syslog_priority`'s rule and `chk_alert_agent` against
   `AGENT_NAMES`. `journalctl -p N` admits `0..N`, which is
   `SEVERITY_ORDER`'s "this rung and every louder one" read the other
   way, so the two compose with no conversion anyone has to remember.
2. **The Python filter stays and is still the authority.** `-p` exists
   to make the *ceiling* count entries that matter; deleting the filter
   would make journalctl's reading of a record the only one, and an
   unknown filter string must narrow both sides identically or a typo in
   `services.yaml` silences a source for a reason nothing reports.
3. **The cursor rule is kept as written although `-p` dissolves it.**
   Advancing over every entry *read* now coincides with advancing over
   every entry kept, because the noise is no longer returned — so
   collapsing them would make dropping `-p` silently rebuild the
   duplicate-ingest defect.
4. **The ceiling was not raised.** The catch-up path is what remains,
   and no ceiling reaches it: `_resume_floor()` sets the window to how
   long the daemon was down, so one restart behind a backlog truncates
   at any limit. `truncated` now means *relevant* data was lost rather
   than "the read was busy", which is the stronger signal it was
   claiming to be.

**This does not close `SNAG-LOG-002`, and the fix that was going to was
refuted by measurement.** Per-source confidence produces **zero** noise
rows — driven through the real `_build_trend_report` → `recommend()`
against the live database — because the entire noise-eligible population
is two kernel signatures at 39,920 apiece and kernel holds **103 of the
120** truncated runs, while the eight sources it liberates have a
loudest signature of **54** against `NOISE_MIN_OCCURRENCES = 100`. It
would also have failed **silently**: `details['truncated_sources']` keys
on the `services.yaml` **name** and `log_entries.source` on the **unit**,
and `kernel` is the only string in both — so the obvious join reads the
eight as untruncated and kernel as truncated, wrong in both directions
and green. `_log_source_scopes` carries that same warning one function
over. What remained was the **binary** flag, not the global one.

**That flag is gone, and the mechanism everyone had written down for it
was wrong** (Session 63, `SNAG-LOG-002` closed). One catch-up read pinned
the report `LOW` for fourteen days, so `GET /api/logs/actions` served
zero `noise` rows against two signatures at 39,921 apiece.
`_confidence` now gates on `truncated_fraction >
TRUNCATION_LOW_FRACTION` (0.05) over the **instrumented** reads; live,
that is 120 of 7,006 — `medium`, and the two rows appear.

Four rules, three of them corrections to what was believed before the
measurement:

1. **`_resume_floor()` sizes a catch-up read by how long since that
   source last *stored* a row, not by daemon downtime.** A source
   logging one warning a week is read a week back on every restart,
   which is why 16 of the 120 truncations each name four or five sources
   at once — every one of them the first poll after a restart, ~62 s
   after `Started SysAdmin…`.
2. **So the ceiling fix does reach them**, against the entry's claim
   that no ceiling could: `-p` spends the 500-entry budget on storable
   entries, and a week-long window on a quiet source holds about one.
   Measured on one box in one hour — the 13:17:05 restart's poll
   truncated 4 sources, the 14:10:58 restart's poll truncated nothing.
3. **The denominator is the instrumented runs, never the observed
   ones.** `details['truncated_sources']` first appears 2026-08-12
   17:31, so 10,724 of the window's 17,730 runs could not have reported
   truncation; dividing by all of them reads 0.68 % against a true
   1.71 %. It self-corrects as those runs age out, which is precisely
   why leaving it was not an option — a number wrong today and right
   next week is one nobody re-checks.
4. **A threshold is legitimate because truncation is
   one-directional.** It drops entries, so a `noise` row's "this is
   loud" is a floor the missing data cannot undercut — rule 4's `NEW`
   asymmetry one step further. What the threshold bounds is not the
   volume error but the chance a depressed *current* window moves a
   `SURGED` signature into the noise-eligible `STEADY` band. Both live
   rows were `RETURNED` with `previous = 0` when this was written, so no
   ratio was computed for either. **That is a property of the window,
   not of the pair, and it has already moved**: at a window covering the
   2026-08-12 storm they are `FALLING`, 39,885 against 77,496 (measured
   2026-08-24). The argument is unaffected — a `FALLING` row is
   noise-eligible too — but a sentence in the present tense about which
   rung two live rows sit on goes stale faster than the rule it
   supports.

`truncated_fraction` **fails closed** — `schema_guard`'s posture, not
`collation.py`'s — so a caller with no denominator gets `1.0` and the
binary behaviour back. That is why all 1,984 tests passed on the first
run after the change, and why the guards were falsified deliberately:
`TRUNCATION_LOW_FRACTION = 0.0` restores the old rule *exactly* (it is
the limit case, not a replacement) and breaks precisely the four new
tests.

`read_journal` also gained its **first direct tests**. Every existing
test patches it out, or asserts `journal_command` — the invocation a
recommendation tells a *human* to run — so the command this module
actually executes was unasserted, which is how the ceiling came to bound
raw lines for the life of the module.

**A logger that is not the one you configured writes the line anyway**
(Session 60, `SNAG-AGENT-008` volume half). `configure_logging` clears
the **root** handlers, which does not reach `uvicorn.access`: uvicorn's
dictConfig attaches a handler to that logger *directly* and sets
`propagate = False`, so it sat outside every switch this module throws
and wrote a plain-text copy of every request beside the middleware's
JSON one. Measured over ten minutes: **662 plain against 640 JSON**, and
662 − 640 is exactly the **22 `/health` polls** `_EXCLUDED_PATHS`
suppresses — so `SNAG-API-002`'s fix had never once worked. Note what
could not have caught it: `test_excludes_health_endpoint` patches
`sysadmin.core.middleware.logger`, the emitter that was already
honouring the exclusion.

Three rules. **The structured copy is the one kept** — only it carries
`method`/`path`/`status`/`duration_ms` as fields rather than prose to be
parsed back. **Disabled, not re-levelled**: uvicorn logs access at INFO
and nothing else, so `setLevel(WARNING)` is silence spelled indirectly
and starts emitting again the day uvicorn adds a warning-level access
line. **Silenced, not redirected** — removing the handler and letting
the record propagate keeps the duplicate and merely re-dresses it as
JSON, which is the same line count in the journal and the line count is
the number being moved. A test drives uvicorn's real `LOGGING_CONFIG`
rather than a reconstruction of it.

**The other half of the same blindness is the level, and the trade-off
this repository had written down was wrong** (Session 61,
`SNAG-AGENT-008` priority half). systemd stamps captured stdout
`PRIORITY=6` whatever the `"level"` inside the JSON says, so
`read_journal`'s `severity_filter: warning` discarded every line this
daemon has ever written and `log_entries` held **0 rows** for
`sysadmin.service` across nine nights of `ERROR`. The snag said the two
unit-file remedies both need `sudo`, leaving a reader-side parse as the
only cheap option. `SyslogLevelPrefix=` **defaults to true** in systemd
and already read `yes` here — so the prefix costs no unit edit and no
`sudo` either. A trade-off written from documentation rather than from
the box had sent the choice toward the weakest of three.

`JournalLevelPrefixFormatter` prefixes each JSON line with `<N>`.
Journald strips it, so `MESSAGE` is byte-identical and `log_signature`,
`alert_title` and `raw_line` need no change — verified against a
transient unit before the code was written.

Four rules, three of them the opposite of the obvious implementation:

1. **The producer, not the reader.** Parsing `"level"` in
   `read_journal` fixes this repository's view and leaves the artefact
   lying: `journalctl -u sysadmin -p err` still prints nothing, and so
   does any `OnFailure=` hook. It also puts a special case for **one**
   source into a reader serving fourteen — and `sysadmin.service` is the
   only JSON-writing journal source on this box, measured, so the branch
   could never pay for itself.
2. **The JSON gate is a precondition, not a proxy for the destination.**
   A level prefix marks one line, and only the JSON formatter guarantees
   one line per record. Under the text formatter a traceback's first
   line would be stamped `ERROR` and its body left at `info` — one fault
   across two priorities, worse than the uniform `6` because it *looks*
   fixed.
3. **`uvicorn.error` is rerouted, not silenced** — deliberately the
   opposite verb from `uvicorn.access` three lines up in the same
   function. It has no handler and propagates only as far as `uvicorn`,
   which keeps a plain-text handler with `propagate = False`: the access
   logger's shape exactly, carrying `Exception in ASGI application` and
   every unhandled 500. The access line duplicates a structured line the
   middleware already writes, so the second copy is waste; uvicorn's
   error line has no second copy anywhere, so silencing it would delete
   the only record an ASGI crash leaves.
4. **`syslog_priority` is pinned to `journal.PRIORITY_MAP` by a
   round-trip test**, not asserted alone on each side — two maps that
   can disagree about one fact is `SNAG-DB-003`'s shape and
   `chk_alert_agent` against `AGENT_NAMES`.

Note what was asserting the opposite and passing.
`test_only_the_access_logger_is_silenced` (Session 60) claims
`uvicorn.error` reaches the root handler; its fixture rebuilds
`uvicorn.access` and **not** its parent, so the record fell through to
root in the test and went to uvicorn's own handler on the box. True in
CI, false in production — `test_excludes_health_endpoint`'s defect one
logger over, shipped by the session that found it.

`SNAG-LOG-003` was the cost, filed rather than bundled: `MESSAGE` for
this source is the whole JSON line, so `alert_title` yielded a
252-character title made of JSON that reaches a notification body
verbatim.

**Trying to test that fix against real rows found a P0 underneath it**
(Session 64, `SNAG-LOG-004`). `journalctl -o json` substitutes `null`
for any field over ~4096 bytes unless **`-a`** is passed, and
`read_journal` never passed it — so `MESSAGE` came back `None`,
`entry["message"][:5000]` raised `TypeError`, and the whole
`log_aggregator` run died, every source in it. **Self-sustaining**: the
failure is written by `logger.exception`, itself a >4096-byte line at
`ERROR`, so the next poll reads *that* and crashes again. All **215
historic `agent_run_failed` lines are 12,837–12,845 bytes**.

Four things worth carrying forward:

1. **The previous fix armed it.** These lines were `PRIORITY=6` until
   the 14:10:58 restart, so `-p 4` excluded them and 40,228 runs had
   never failed. Measured at the moment of the fix: **0 error lines and
   146 clean runs since the restart** — live and untriggered. A fix that
   widens what a monitor can see is a regression surface for whatever
   consumes it.
2. **Reachable only for a source that puts a long record on one line.**
   A Python traceback from any other service arrives as many short
   journal entries; `JsonFormatter` folds `exc_info` into a single
   `MESSAGE`. Same "only JSON-writing journal source on this box" fact
   Session 61 used, read the other way.
3. **It is the JSON serialiser's cap, not journalctl's reading.** The
   same records print in full under the default text output (11,572 and
   12,164 characters), so `journal_command` — the invocation a
   recommendation hands a human — needed no change, and that was checked
   rather than assumed.
4. **No fixture could have caught it.** Every existing test patches
   `_run` with a stub returning hand-written JSON, so `MESSAGE` was
   always a string somebody had typed. `test_excludes_health_endpoint`'s
   defect one module over.

`message_text()` sits behind `-a` for the one shape `-a` introduces — a
non-UTF-8 field, rendered as an array of byte values rather than as
`null`. Empty population here (205,298 kernel records over seven days,
all `str`), kept because the shape is journalctl's to choose.

**Then the declaration, which is the reader honouring a statement rather
than recognising an application.** `LogFormat = Literal["text", "json"]`
sits on `sysadmin/core/config.py`'s `LogSource` — one vocabulary, since
both files funnel into it — and `read_journal` applies
`unwrap_json_message` only where a source declares it. Measured over the
**723 real `ERROR` lines**: 6 distinct titles of 242–253 characters of
JSON become **5 of 46–151 readable characters**.

Four rules, three of them the opposite of the obvious implementation:

1. **It fails open at every step, and the reason is measured rather
   than cautious.** systemd writes its **own** plain-text lines into a
   unit's journal at error level — `Failed to start SportsAnalyser -
   Frontend (Next.js).` appears **668 times** live, nine distinct such
   messages exist — so a declaration that discarded non-JSON would
   silence exactly the line saying the service died. A declaration
   describes what the *application* writes; it can never describe
   everything in the journal it writes to.
2. **Severity is not taken from the envelope.** `"level": "ERROR"` sits
   beside the message and is ignored, because the level prefix already
   put it in `PRIORITY` — two statements of one fact that can disagree,
   `max_priority_for`'s rule — and only the prefix reaches `journalctl
   -p err` and `OnFailure=`.
3. **`logger` goes to metadata, never into the title.** The old key's
   sixth title was a *fork*, not a distinction: `sysadmin.core.scheduler`
   and `sysadmin.services.scheduler` emit the same
   `scheduler_job_error` and were split only because the module path
   fell inside the 252 characters truncation left. Putting `logger` back
   in the title would rebuild that by design.
4. **The two declarations are pinned, not restated.**
   `service.log_format` decides what this process emits and
   `log.format` how the reader parses it; they live in different files,
   so a test asserts they agree — keyed on `OWN_UNIT` rather than the
   historical `name`, and paired with one asserting no other source
   declares a format, which is the measured claim the whole design rests
   on.

`raw_line` still holds the journalctl record verbatim, so the unwrap
moves what identity is built from and never what is retained. The stated
limit: `agent_run_failed` is written by all five agents, so five
failures share one signature — not a regression, since the truncated
JSON title cut at `"servic` and never reached the `agent` field either.

The fixture was the thing that had to change. Twelve tests built a
`SimpleNamespace` stand-in for `LogSource` and broke on `source.format`;
`getattr(source, "format", "text")` would have made them pass while
swallowing a genuine wiring failure, so the fixture constructs the real
model instead — `UnitFinding.enabled`'s trap answered on the correct
side.

**A declaration applied at read time cannot reach a row already stored,
and the repair reads the column the reader read** (Session 116,
`SNAG-LOG-008`). Ten `sysadmin.service` rows kept the raw envelope in
`message` because they were ingested before the declaration existed;
`signature()` and `alert_title()` are both computed from `message`, so
`GET /api/logs/trends` served ten unreadable signatures.
`sysadmin/monitor/message_backfill.py` is the second caller of
`unwrap_json_message` — the one the entry named as its own refutation —
and `sysadmin-backfill-messages` the console script over it.

Six rules, four of them the opposite of what the entry proposed and every
one settled against the live table rather than by argument:

1. **The new message is derived from `message`, never from `raw_line`.**
   The entry asks for the reverse and prices in `raw_line`'s
   2000-character truncation as the reason a backfill "is not free".
   Read what `read_journal` composes: `message = message_text(MESSAGE)`
   **first**, then `unwrap_json_message` on that same string only where
   the source declares it. A `text`-declared row's stored `message` is
   therefore exactly the unwrap's input, so applying the unwrap to it
   reproduces the `json` read by construction, while going through
   `raw_line` re-implements `message_text(json.loads(line)["MESSAGE"])`
   — a second statement of the reader's own parse, free to drift from
   it. The two derivations agree **10 of 10**, so the cheaper route is
   also the exact one.
2. **`raw_line` earns a different job instead: the *witness*.** "Does
   this look like JSON" cannot separate a frozen envelope from a
   correctly-unwrapped message that is itself a JSON document, and
   acting on the guess destroys the second. Byte equality against the
   record's own `MESSAGE` is exact in both directions — a row nothing
   unwrapped holds it verbatim, an unwrapped row holds the fragment. So
   the truncation the entry feared is real and lands on the **witness**,
   which is the weaker half: a row that cannot be cleared is *refused
   and reported* rather than corrupted. Re-measured, Session 90's
   anti-correlation has grown and still holds — **16** rows now carry a
   `raw_line` cut at 2000, intersecting the ten at **zero**.
3. **The population is the declaration's, never the shape's.** A
   candidate is a row whose source declares `format: json` *today*; a
   sweep for JSON-looking messages would rewrite a plain-text service
   that happened to log a document, which is recognising an application
   rather than honouring a statement — `unwrap_json_message`'s own rule.
   The set is `composed_log_sources` resolved through
   `stored_source_name`, because `log_entries.source` holds the **unit**
   while the declaration is keyed on the **name**: `log_source_scopes`
   records that trap from the other side, where the wrong key yields an
   empty map that reads as success.
4. **Idempotence is a property, not a flag.** A repaired row's `message`
   no longer equals the record's `MESSAGE`, so rule 2's witness answers
   `False` on the next run. A `backfilled` column would be a second
   statement of a fact the data already carries.
5. **A console script, not a data migration**, which inverts the obvious
   ranking. An Alembic revision moves the packaged head for no structural
   reason, so the box owes `alembic upgrade head` plus a restart or
   `schema_guard` refuses to boot — `SNAG-DB-005`'s twenty-three hours
   bought for ten rows — and it repairs this population once where the
   defect is a *class*. Dry run unless `--confirm` (`files/actions.py`'s
   contract), and **never scheduled**: `check-migrations.sh`'s rule, with
   a test pinning that no job plan or agent reaches it.
6. **Every way of not-knowing is reported and none is success.** A row
   that cannot be witnessed and a row whose envelope will not parse are
   distinct from "nothing to do" and both push the exit status to `2` —
   `ports_checked`'s rule at the size of a return code.

Measured before deciding, which is what the sitting was for: the
population was **intact and three days from moot**. The ten left the
trend's current window on 2026-08-24 and would have left the endpoint on
2026-08-31; live either side of the write, `GET /api/logs/trends` went
**60 → 50** signatures, `sysadmin.service` **24 → 14** and raw-JSON
**10 → 0**. `GET /api/logs/actions` is **unmoved at 8** — the ten were
`previous`-only and never produced advice — which corrects this
document's own "four of the nine live titles now open with
`{"timestamp"`": that population had already aged out.

**Applying it exposed a duplicate nobody had seen, and dating the commits
is what settled the mechanism.** Two of the ten have a readable twin
ingested at **19:50:19**, the restart that deployed the declaration; the
declaration was committed at **17:53:33** and `SNAG-LOG-007`'s boundary
close (`_is_unstored`, `stored_at_floor`) landed at **20:09:44** —
*nineteen minutes after that restart* — so `_resume_floor` re-admitted
its own inclusive second. Invisible before the backfill, because the
twins were different signatures and hid each other; `SNAG-LOG-004`'s
ordering a fourth time, a fix that widens what a monitor can see being a
regression surface for whatever reads it. Filed as `SNAG-LOG-014`.

The check retired with the entry and **the detector did not** — its
two-declaration drive is `tests/test_message_backfill_live.py`,
`FROZEN_TABLES`' rule. Re-homing it walked into the entry's own warning
a second time: the drive paired the two reads on `raw_line`, whose field
order `journalctl -o json` does not fix, so it compared nothing and
**skipped**. It pairs on `__REALTIME_TIMESTAMP` now, with a premise test
asserting the reads shared a record at all. Two of fourteen mutations
were wrong on the first attempt — removing the declaration filter gave a
*collection error* rather than a red test, and breaking the confirm gate
was caught only by an AST sweep until a live drive through `run()`
itself was added.

**Making the monitor able to see its own errors gave one fault two
speakers, and the second-owner defect existed at a sixth scale by this
repository's own hand** (Session 65, `SNAG-LOG-005`). `BaseAgent.run`
states one fact twice, three lines apart: `logger.exception` writes
`agent_run_failed` to the journal, then `_record_outcome` writes a
`failed` row to `agent_runs`. Session 61's level prefix and Session 64's
`format: json` are what let the first copy reach the log aggregator — so
an agent failure raised a row here **and** a row from `failures.py`, two
tray `{severity}:{title}` fingerprints, two toasts. Sharper than
duplication: `failures.py` requires **two** consecutive failures and
argues the rule out in writing (*"One failure resolves itself on the next
run… which is noise"*), while the journal path raises on the **first**
line. A deliberate threshold was not overridden, it was bypassed.

`COVERED_SIGNATURES` maps `(source, signature)` to the family that owns
the fault. Five rules, three of them the opposite of the obvious
implementation and all five settled by counting the journal rather than
by argument:

1. **Quietened, never dropped** — `known_noise`'s rule 2 for its reason.
   The row still counts occurrences, still reaches `GET /api/logs/trends`
   and still resolves on silence; `details['covered_by']` **names** the
   owning family, `details['truncated_sources']`'s rule. `noise_reason`
   and `covered_by` are separate keys because an operator's judgement
   that a fault is harmless and a structural fact that another family
   owns it are different claims — one field holding both is
   `UnitFinding.enabled`'s trap.
2. **Both halves of the key are constants the producers already own.**
   `OWN_UNIT` is the unit `read_journal` stamps into
   `log_entries.source`; `AGENT_RUN_FAILED_EVENT` replaces the string
   literal `BaseAgent.run` passed to `logger.exception`. Copying either
   would be a second statement of somebody else's fact —
   `max_priority_for` against `PRIORITY_MAP`, `chk_alert_agent` against
   `AGENT_NAMES`. The signature is matched *after* normalisation, and
   `signature()` maps digit runs to `N`, so a test pins that the event
   name still survives it: the failure mode of a rename is silence, not
   an error.
3. **Scoped to the one signature, never to this daemon's unit.** The
   obvious wider fix — excluding `OWN_UNIT` from the alert half — was
   refused on measurement. 713 `ERROR`/`CRITICAL` lines resolve to **249
   incidents**, and **34 carry no `agent_run_failed` at all**
   (`file_organiser_scan` ×27, `retention_purge` ×7). `retention_purge`
   is not an agent, so no family covers it anywhere; excluding the unit
   deletes the only witness those have.
4. **Quietening is safe because the case where `failures.py` is blind is
   the case where a different signature is still loud.** That family
   reads `agent_runs`, so it cannot see a failure `_record_outcome`
   failed to record — but `_record_outcome` is awaited *outside*
   `run()`'s `try`, so its failure propagates into APScheduler and raises
   `scheduler_job_error`, still at `warning`. Measured: 215 of 215
   historic incidents carry both lines in the same second, and
   `agent_runs` holds **zero** `failed` rows across 7,816 sysadmin runs —
   the same fact stated twice. `SNAG-LOG-006` is the one path it misses:
   a manual run is started with `asyncio.create_task` and has no
   scheduler listener behind it.
5. **The quietening reaches a row raised by the previous release.**
   `known_noise` arrives by a config edit the next poll re-reads; a
   covered signature arrives at a **deploy**, so the open row it must
   reach is one this daemon raised loudly under the old code — and this
   family's rows do not resolve while the fault keeps firing. Session
   39's ban on in-place severity changes is asymmetric, and this is the
   direction it permits.

**The entry understated its own symptom, which is the part worth
carrying.** It said one fault produced two rows; the journal says
**four** — 215 of 215 incidents fired `agent_run_failed`,
`scheduler_job_error` and apscheduler's own `Job "…" raised an exception`
in the same second. Only two of those can recur, because Session 41 made
`_record_outcome` survive a failed run, so the entry was right by
accident. It also quoted the title as `Log error: sysadmin-service — …`;
`log_entries.source` is the **unit**, so it is `sysadmin.service`. A snag
filed from reasoning about a mechanism rather than from counting its
output is the failure `verify-ops-claims-live` names, one document over.

The fix ships **untriggered**: all 215 lines fall on 2026-08-08 → 08-10,
the `SNAG-DB-001` window, and there have been none since. So it was
driven live rather than only against fixtures — real historic lines
through the real `unwrap_json_message` and the real `_execute` against
the live database in a rolled-back transaction, giving `info` +
`covered_by` for one signature and `warning` for the other with **0 rows
of residue**. Each of the six tests was falsified deliberately: emptying
`COVERED_SIGNATURES` breaks five, and re-keying the lookup on the
signature alone breaks the sixth — the one asserting a *negative*, which
an empty set can never break.

**Rule 5's one uncovered path is closed, and costing the two candidates
inverted the ranking the entry implied** (Session 112, `SNAG-LOG-006`).
That rule rests on `_record_outcome` being awaited *outside* `run()`'s
`try`, so a failure to record a failure propagates into APScheduler and
raises `scheduler_job_error`. A manual run has no scheduler behind it:
`POST /api/sysadmin/scan-all` and `POST /api/files/scan` started agents
with a bare `asyncio.create_task(agent.run(...))` and kept no reference.
`spawn_manual_run` and `_report_manual_run` in `core/agent.py` are the
supervisor; all five triggers go through them.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the running loop rather than by argument:

1. **`run()` escapes in four shapes and the cheap fix reaches one.**
   `_execute`'s exception is swallowed, so what escapes is the
   bookkeeping around the work. Driven through the real `run()`:
   `_execute` **and** `_record_outcome` raising (journal holds
   `agent_run_failed`), `_record_outcome` alone (`agent_run_completed`),
   `_record_start` (**no line at all**) and `_flush_events`
   (`agent_run_completed`). Narrowing `COVERED_SIGNATURES` to
   `run_type == "scheduled"` can speak only where an `agent_run_failed`
   line **exists** — shape 1, and nothing else. It is also the *more*
   expensive: `unwrap_json_message` returns `{"logger": …}` and its own
   docstring refuses to promote further envelope fields into the
   identity, and the map would gain a third key component `known_noise`
   does not share.
2. **The report goes to the journal and never to the database.** The
   exceptions that reach here come from `_record_start` and
   `_record_outcome`, which are database writes, so a report needing a
   session would need the thing that has just failed —
   `core/unit_failure.py`'s argument (it runs while the application is
   dead) arriving one layer in. The journal is already wired: since the
   level prefix and the `format: json` declaration an `error` line from
   this daemon is ingested and raises through the family that owns this
   source. No new alert family, no new table, no session.
3. **It cannot double-report an ordinary failure, which is what makes
   rule 2 safe.** A normal agent failure *returns normally*, so the
   callback sees no exception at all — `failures.py`/`stalls.py`'s
   mutual-exclusion-by-construction one layer down, and the
   healthy-run-says-nothing test is what keeps it honest.
4. **The residual signal the entry filed as unmeasured is prompt, and
   *when* was never the problem.** asyncio's fallback fires at `ERROR` on
   the loop turn **after** the task completes — the loop drops its
   reference, CPython collects the task, `Task.__del__` calls the handler
   synchronously; no `gc.collect()` is needed or helps. **What** it emits
   is the defect: a **252-character signature** and a **220-character
   title** reading `Task exception was never retrieved future: <Task
   finished name='Task-N' coro=<BaseAgent.run() done, defined at
   …/core/agent.py:N> …` — `SNAG-LOG-003`'s shape by the one route
   `unwrap_json_message` cannot help, since the *unwrapped* message is
   itself the repr. It names `BaseAgent.run`, so all five triggers share
   one signature and the row cannot say which agent died; it carries the
   module path, so moving `run()` forks the row on a commit that changed
   nothing; and the exception's own text sits inside the repr, so on a
   checkout path shorter than this one it falls inside the cap and forks
   a row per distinct failure — `SNAG-AGENT-005`'s pile-up rebuilt inside
   the family built to end it. What ships instead is
   `manual_run_failed`: a **17-character** signature and a
   **46-character** title, with `exc_info` measured landing under its own
   envelope key so the traceback stays out of the identity and one query
   away in `raw_line`.
5. **Cancellation is tested first, recorded, and never announced.**
   `Task.exception()` *raises* on a cancelled task, so the order is
   forced; what is not forced is the response. A cancellation leaves
   precisely the residue a failure leaves — an `agent_runs` row stuck at
   `running` — so it is written rather than dropped (`known_noise`'s rule
   2), and written at `warning`, which `FAULT_SEVERITIES` excludes:
   stored, counted, carried into `GET /api/logs/trends`, raising nothing.
   That tuple was extracted from an inline literal in
   `LogAggregatorAgent._execute` so the rung is derived rather than
   restated — `max_priority_for` against `PRIORITY_MAP`'s rule. The rung
   *is* the mechanism; a second suppression list would restate what the
   severity already says.
6. **There is no `run_type` parameter.** A scheduled run must not arrive
   here, because APScheduler's listener is what makes
   `scheduler_job_error` loud for those and a second supervisor gives one
   fault two speakers — the second-owner defect arriving inside the fix
   for a case of it. Hard-coding `"manual"` makes that impossible rather
   than discouraged, which is `since_timestamp`'s argument for taking a
   `datetime`.

**The entry named the wrong second trigger and its own check could not
have said so.** `POST /api/files/organise` is a *synchronous* action
route returning `FileActionResponse`; the discarded task was in
`POST /api/files/scan`. `check_manual_run_unawaited` counted five
discards across two *files* and never named a route, so it reported
`match` — the right number about the wrong thing. The check retires with
the entry (every member of `CHECKS` names an open one) and the detector
does **not**: the AST walk is re-homed as `TestNoTriggerDiscardsItsTask`,
`FROZEN_TABLES`' rule, since deleting a guard along with its last finding
takes the guard against the defect coming back.

Ten mutations were driven against the twenty new tests and each lands red
on the right one — **two of them wrong on the first attempt, which is the
part worth carrying**: removing the `finally` produced a `SyntaxError`
rather than a leak (a stand-in that cannot compile is silence wearing a
result), and the priority round-trip test read `PRIORITY_MAP` with an
`int` key when the map is keyed on the **string** journalctl emits.
Verified live and untriggered: the real `POST /api/sysadmin/scan-all` on
the restarted daemon produced four `agent_run_completed` lines and zero
`manual_run_failed`.

The other 86 % was the tray. `sysadmin_tray/dashboard/services_tab.py`
is built eagerly at startup and wired to `status_updated`
unconditionally, so it issued one `/details` per systemd-backed service
on **every** status poll, dashboard open or not — **1,160 of 1,347
lines** in ten minutes, against `DashboardWindow`'s own docstring
promising *"no background polling when hidden"*. `LogsTab` stops its
timer in `hideEvent`; this tab had no timer to stop, so the polling was
never scheduled, it was inherited from a signal that fires anyway.
`isVisible()` is false both when the window is hidden and when another
tab is selected — both cases where nobody is looking — so the widget's
own answer is used and no second flag is kept, a flag being free to
disagree with Qt about the same fact. `refresh()` fetches details for
cards already held, because the gate's visible cost is a warm tab
opening blank for a poll interval and it is paid there rather than by
widening the gate. `ServicesTab` was the **only** tab issuing a request
from a client signal handler, so it is fixed in place rather than
abstracted.

**The two halves of `SNAG-AGENT-008` are multiplicative, not
independent**, which is the part worth carrying forward.
`_read_journal_source` falls back to a five-minute window only when
there is no cursor **and** `_resume_floor` is `None`. For
`sysadmin-service` the floor is *always* `None` — the priority half
means no rows are ever stored — so the durable resume mechanism is
permanently disabled, every restart re-reads five minutes, and five
minutes at 673 lines overflows the 500-line ceiling. Fixing **either**
half stops the truncation; only the priority half stops the re-read.

**A detected fault has to keep speaking, and the ladder that makes it do
so lives in `core`** (Session 39). `sysadmin/core/escalation.py` owns
`SEVERITY_ORDER`, `Ladder` and `step_for`. It was put there for the reason
`strip_markdown` was — the two climbers sat on opposite sides of the rule
that `monitor` may not import `projects`
(`tests/test_import_boundary.py`), so "reuse rather than copy" required
the move first. **That reason has since expired and the placement gained
better ones**: the projects domain left on 2026-08-13 and four domains
climb the ladder now — `monitor/stalls.py`, `monitor/failures.py`,
`units/agent.py` and `estate/judgements.py`, with `monitor/desktop.py`
taking `humanise_hours`. The boundary test still names a package that
cannot exist, which makes it a guard against bringing it back rather than
a live constraint.

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

**The ladder has two rungs and a third was measured and refused**
(Session 53, `SNAG-ESTATE-003`). Five families deduplicate on an open
row and own no ladder — the estate judge, `monitor/collation.py`, the
unit sweep's roll-up and the two `_raise_judged` covers — so each rings
once at the quiet severity and is silent while the fault stands, which
is Session 39's defect one layer over. The obvious next move is a rung
that repeats without reaching `critical`. **It cannot be heard.** The
tray fingerprints on `{severity}:{title}` and clears
`notified_this_episode` only when that pair is **absent from a poll**,
which a resolve-and-re-raise inside one agent run never produces:
measured against the real policy, a resolved row replaced by a fresh one
carrying a new message produced **no notification at all**, where the
same fault escalated to `critical` spoke and a forked title spoke. The
title is the identity key, so the second is forbidden — leaving nothing
for a third rung to be heard by.

A repeat at an unchanged severity is therefore a **notification**
decision, and it lives where notification policy already does:
`reminder_hours` in `sysadmin_tray/notifications.py`. Four rules.
**The clock runs from when the tray last spoke**, not from
`alert.created_at` — `stalls.py`'s rule, the thing that failed being the
*telling*, and it keeps the one injected clock that makes every window
in that module testable without sleeping. **24 hours is derived, not
picked**: it matches `self_monitor.escalate_after_hours`, the only
escalation gap on this box, so a family that owns a ladder escalates to
a different fingerprint — a new episode, spoken at once — before any
reminder of its quiet rung is due; shorten it and the loud rung becomes
the second thing you hear rather than news. **A reminder is never
transient**, because the failure it fixes is a toast in an empty room
and `transient=False` is what keeps it in the notification history
(`flush_digest`'s rule). **Reminders fold apart from new alerts**, into
`FP_REMINDER` with their own wording: a fault announced yesterday inside
a summary headed "N new alerts" is the one thing a reminder is not.

Two limits, both stated in the code. `digest_mode` never reminds below
`critical` — that mode's contract is that warnings do not interrupt, and
making the digest itself periodic is a separate question about a mode
that is off here. And the policy state is in memory, so a tray restart
re-announces every open fault as new. The third is `SNAG-TRAY-007`:
`monitor/desktop.py` is event-driven off `alert.raised` and shares none
of this, so while the tray is down — the only case the understudy exists
for — a standing fault is still announced once.

**The understudy has a clock now, and the precedence answer is the same
window used the other way round** (Session 55, `SNAG-TRAY-007`).
`monitor/desktop.py` speaks once per incident and is subscribed to
`alert.raised`, so it had no moment at which it could notice that a
fault it announced six hours ago was still open — Session 39's defect
surviving in the one component that exists for the case where the tray
is *down*, which is precisely where Session 53's `reminder_hours` cannot
reach. `DesktopNotifier.sweep_reminders` is that moment, scheduled as
`desktop_reminder_sweep` in `core/jobs.py`.

It is a **job**, not a call at the end of `SysAdminAgent._execute`: an
agent reminding on the notifier's behalf owns a lifecycle
`monitor/desktop.py` holds, which is the second-owner defect this
repository has now found at five scales.

Four rules, three of them the opposite of the obvious implementation:

1. **A watching tray stamps the clock forward; it does not skip the
   sweep.** `tray_grace_seconds` decides precedence on both paths and
   the *action* differs. Skipping leaves `last_spoken_at` at the opening
   notification, so the first sweep after a tray outage restates a fault
   the tray itself restated ten minutes earlier. While something polls
   the route, the last thing said was said by it — and the difference is
   observable **only** in the middle window, which is what the test pins
   and where the first draft of that test had the arithmetic wrong.
2. **The population is what this process announced, never the open
   rows.** A sweep over `resolved IS false` adopts every fault the tray
   was speaking for and announces the lot the moment the tray dies —
   `SNAG-AGENT-005`'s unbounded `SELECT` wired to a notification each.
   The spoken set is in memory, so the query is `title IN (:titles)` and
   a sweep that has said nothing issues no query at all. The cost is
   `SNAG-TRAY-008`, filed rather than implied: a fault raised while the
   tray was up is never adopted, and a restart forgets everything.
3. **Neither number is invented.** `reminder_hours` is the tray's 24 for
   the tray's reason, and because two speakers with different cadences
   make the interval depend on which happened to be running — the thing
   the understudy exists to hide. The sweep's own cadence has **no leaf
   at all**: `max(60, tray_grace_seconds)`, since the sweep asks the two
   questions that window already answers.
4. **A reminder that did not land does not move the clock**, and nothing
   is recorded as spoken until the opening notification has actually
   landed. `send` returns whether it reached a screen, so a missing
   session bus delays a reminder by one sweep rather than by a full
   interval.

A roll-up folds at two and takes the **loudest** rung it swallows
(Session 52's rule): `notify-send` has no `replaces_id`, so six due
reminders would otherwise be six toasts.

**The understudy remembers now, and the reminder it could not reach was
a restart-cadence problem nobody had measured** (Session 115,
`SNAG-TRAY-008`). `DesktopNotifier._spoken` was in memory and the sweep's
population was exactly its keys, so the entry's two costs stood: a fault
raised while the tray was watching was never adopted when the tray died,
and a restart forgot everything. `desktop_notifications` (migration 018)
is the store and `DesktopNotifier._adopt` the scope.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the box rather than by argument:

1. **The number reranks the entry, and the entry could not see it
   because it filed its population as zero.** `sysadmin.service` started
   **111 times in 28.26 days** — median uptime **1.77 h**, mean 6.17 h,
   **5 of 110** lives reaching the 24 h `reminder_hours` asks for. So
   `SNAG-TRAY-007`'s reminder was structurally unavailable on **95 %**
   of this daemon's lives: not a slow reminder, silence with a number
   beside it.
2. **The entry's own shape-of-fix is unreachable as written, and the
   same measurement is why.** It asks for adoption *"only when the tray
   has been absent for a full `reminder_hours`"*; `TrayPresence` is
   monotonic and in-memory by deliberate design, so a process observes
   24 h of absence only by living 24 h. Shipped as a **refusal** the fix
   would have been correct, green and inert. It ships as an **anchor** —
   `absent_for()` sets the adopted fault's `last_spoken_at` back, capped
   at one interval — which keeps the quiet-by-construction property the
   entry wanted and is reachable here. `absent_for()` falls back to
   process uptime, an under-count that delays an adoption and can never
   hasten one.
3. **The two faces are multiplicative, not independent** —
   `SNAG-AGENT-008`'s shape, and the mechanism the entry describes
   without naming. Adoption alone re-adopts on every restart and re-arms
   its own anchor, so on a 1.77-hour daemon it never speaks; the store
   alone leaves face 1 exactly as filed. A fix for one half is not half
   the benefit, it is none.
4. **The clock became a wall clock, which is a change of *reading***.
   No monotonic value survives a process — and on Linux
   `CLOCK_MONOTONIC` does not survive a **suspend** either, so a
   workstation asleep overnight paid nothing towards an interval that is
   precisely about elapsed human time. `TrayPresence` keeps monotonic
   for its own 180-second question, where a suspended box correctly
   counts nothing because neither process was running.
5. **The store records what was *said*, never what the tray's presence
   implied.** Rule 2's stamp-forward stays in memory, which bounds writes
   at one per notification and is safe because a restored stale stamp
   cannot act — a reminder needs the tray absent, and that same gate
   corrects it on the first sweep after a restart, inside one grace
   window. The stated cost is one early toast if the daemon restarts
   while the tray is up and the tray dies inside that window.
6. **The old cheapest gate could not survive persistence and was
   replaced rather than kept.** *"A sweep that has said nothing issues
   no query at all"* **is** the entry — not knowing what the last
   process said is indistinguishable from it having said nothing. The
   bound moved from per sweep to **one query per process**, and where
   the tray runs the tray gate returns before anything else is read.
   Adoption is bounded in SQL (`GROUP BY title`, `LIMIT`) and across
   sweeps by `MAX_ADOPTED_TITLES`, which is `_MAX_LISTED_TITLES` reused:
   adopting more than a roll-up can name is adopting a fault nobody will
   hear named, Session 46's rule. It orders by `MIN(created_at)`,
   because a family re-raising every poll has a fresh newest row and a
   deduplicating one — the families `SNAG-ESTATE-003` is about — has a
   single old row, so newest-first ranks exactly backwards.

Three things only running it could have said. **A test asserted the
defect as correct behaviour** — `test_a_fault_the_tray_announced_is_never_adopted`,
green since Session 55 — and had to be inverted rather than deleted.
**Six of twenty-eight falsifications passed against deliberately broken
code**, four of them upsert columns no fake can witness, because a fake
replaces the whole row on conflict and therefore agrees with an `ON
CONFLICT` that keeps the old value; the guard is a statement test
asserting every mutable column is set from `excluded`. And
**`rolled_back_drive` leaked** before it was hardened: `_remember`
commits, that harness rolled back a plain session, and this session's own
suite run committed three rows into `alerts` and three into
`desktop_notifications`. It now joins the connection's transaction by
savepoint — a harness that cannot survive the code it drives is a control
the next fix breaks.

**Deploying it found a second, independent reason the reminder path was
inert.** `DesktopNotifier` resolved `get_session_factory()` — the
*application's* pooled engine — while every call it makes runs on a loop
that is not the application's: the sweep is an APScheduler job and
`scheduler._run_async` wraps each firing in its own `asyncio.run`, and
`on_alert_raised` is published from inside an agent's run, which is
another. A pooled asyncpg connection belongs to the loop that opened it,
so the first query out of a restarted daemon raised `RuntimeError: got
Future … attached to a different loop` and asyncpg followed with
`InternalClientError: got result for unknown protocol state 3`.

**`_still_open` has carried that defect since Session 55 and never once
executed on this box**, because the sweep's old first gate returned
before reaching it — so `SNAG-TRAY-007`'s reminder could not have worked
here even for a fault the daemon *had* announced, and this entry's own
symptom was what hid it. `_factory()` returns `get_scheduler_session`
now (`NullPool`, an engine per call, what every agent already does) and
the commit belongs to that context manager rather than being restated
beside it. Found by restarting and reading three `Log error:
sysadmin.service` rows out of the live table, which is
`verify-ops-claims-live` for a claim about a code path nothing had ever
run.

The check retired with the entry and the drive is re-homed as
`tests/test_desktop_store_live.py` (`FROZEN_TABLES`' rule), where it is
**stronger than the check**: once adoption landed, "the restarted
instance restated its predecessor's fault" was producible by adoption
alone, so the live test asks *how* it was inherited — a restored episode
carries a reminder already sent and is not marked adopted. Live
population here is zero by design: the tray runs, so the tray gate
returns before adoption ever queries.

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

**The guard worked and the outage happened anyway, and the snag's own
ranking of the fix was wrong in two places** (Session 70,
`SNAG-DB-005`). Migration 013 was written, committed and never applied;
the daemon was restarted to serve a new route, this guard refused, and
`sysadmin.service` stayed dead **23 hours** — `SNAG-DB-001`'s cause with
the guard in the way, which is the better half of the trade and is still
an outage. `sysadmin-check-schema` is the same comparison as a console
script, wrapped by `scripts/check-migrations.sh`, **blocking** in
`claude-precommit.sh` and advisory in `claude-postflight.sh`.

Six rules, four of them the opposite of what the entry proposed:

1. **`ExecStartPre=` buys nothing, and cost was the wrong axis to rank
   on.** The entry put it first as the cheapest option that works. A
   check there fails *identically* to the lifespan guard — same refusal,
   same `failed`, same 23 hours, one process earlier. It is not a weaker
   version of the fix, it is the fix already in place, relocated. The
   entry's second candidate has the mirror defect: postflight would not
   have caught **this** outage, because the restart that triggered it
   happened *mid-sitting*, and a session-end check runs after the box is
   already down.
2. **The commit is the last scripted moment before the restart.** There
   is no deploy script on this box; the restart is a hand-typed `kill
   -TERM`. So the check lands at the commit, and it blocks **whatever is
   staged, not only a migration file** — the question is the state of
   the box rather than the content of the commit, and a database behind
   the checkout means the daemon is already dead or dies at its next
   restart.
3. **Three verdicts and three exit statuses, because `unknown` is not a
   flavour of failure.** `match`/`mismatch`/`unknown` → 0/1/2 —
   `ports_checked`'s rule promoted into a return type. Exit 2 **warns
   and never blocks**, which is the one place this family fails *open*:
   a commit refused because PostgreSQL happens to be down teaches the
   operator to reach for `--no-verify`, which disarms the check for the
   case it exists for, and a commit is not what breaks the box — the
   restart is. `schema_guard` still fails closed at boot, where the
   alternative is serving against the wrong schema.
4. **Only the connection is duplicated; never the rule.** Both new
   callers run *outside* a running application — a git hook, and a
   handler that fires when the daemon is dead — so `get_engine()` would
   raise and `live_revision_sync` is unavoidable. The schema-qualified
   table name, the none/one/many interpretation and the wording of a
   mismatch live in `_qualified`, `_interpret_version_rows` and
   `describe_mismatch`, and a test drives **both** readers against the
   live `alembic_version` and asserts they agree. Falsified by pointing
   the sync one at `public.alembic_version` — the other application's
   copy that rule 2 exists to keep out — and it fires.
5. **Nothing applies a migration, and a test enforces that.** Applying
   unattended at boot is how a bad migration reaches production with
   nobody watching, so `tests/test_schema_guard.py` asserts the word
   `upgrade` appears nowhere in `check-migrations.sh`'s executable
   lines — the only place a future edit would put it.

6. **The entry named only prevention, and prevention owns almost none of
   the 23 hours.** `sysadmin-failed.service` fired *correctly*, with a
   persistent critical toast, and said `result=exit-code, exit=1,
   restarts=5` — pointing at `systemctl status` and `journalctl`. The
   cause was one revision number and the remedy one command, and
   `_REMEDY` had held both all along and written them **only to the
   journal**, the surface nobody opens unprompted. `unit_failure.`
   `_schema_diagnosis()` puts the verdict in `details['schema']` and in
   the alert message, and `notify-unit-failed.sh` puts it in the toast:
   `monitor/collation.py`'s rule 4 — the remedy's trap is carried in the
   alert — applied to the fault that needed it most.

A healthy schema **adds nothing to the message and is still recorded**,
because "checked, and it was not this" is a different fact from "never
checked" and a reader of a stale row cannot tell them apart otherwise.
And the annotation **can never suppress the row it annotates** — the
regression this fix could most easily have introduced — so
`_schema_diagnosis` catches everything and a test drives `schema_status`
raising while asserting the row is still written.

Two things the sitting corrected on the box rather than on paper. The
toast said `sudo systemctl status`; measured as `gaddi` (wheel), both it
and `journalctl -u sysadmin` exit 0, so a reader was told a next step was
harder than it is — the missing remedy's defect one line up, and the
second `sudo` claim in two sittings to be wrong when checked. And the
counterfactual was driven by adding a temporary **migration file**, which
raises the packaged head and leaves `alembic_version` untouched: stamping
the database down would have put the box into the state the snag
describes for the duration of the test.


**A document that states what is owed has to be re-measured, and the
place to do it is the script that already prints it** (Session 73,
`SNAG-ESTATE-008`). `docs/roadmap/STATUS.md` opens with the block a
sitting reads before deciding anything. Measured 2026-08-16, **all three
ops actions it carried had already been done**, two of them by a party
that never touched the document, and it went on asking for five sittings.
`sysadmin/ops_claims.py` is the reader; `sysadmin-check-claims` and
`scripts/check-ops-claims.sh` are how `claude-preflight.sh` (start of a
sitting) and `claude-postflight.sh` (the close, where the numbers are
*written*) run it. It sits beside `main.py` for `reload.py`'s reason —
the route count comes from `create_app()`, so it imports every domain.

Six rules, three of them the opposite of the obvious implementation:

1. **The parsed region is exactly the region preflight prints**, and the
   parse runs over `flatten()`ed prose rather than markdown. Not the
   whole file, which restates old figures on purpose (*"44 before Session
   27"*), and not a machine-readable marker beside the sentence, which is
   a second statement of one fact that can disagree with the first —
   `SNAG-DB-003`'s shape arriving in a document.
2. **Every way of not-knowing is `unknown`, never `match`** —
   `ports_checked`'s rule, and the verdicts and exit statuses are
   `schema_guard`'s three, imported rather than restated. Four
   distinguishable faults: a pattern that finds nothing, a block stating
   one figure two ways (drift with both halves inside one file), a
   database that will not answer, and a unit systemd has never heard of.
3. **Two kinds of check, because the remedies are opposites.** A `claim`
   compares the document against the box, so a mismatch means the
   *document* is stale; a `state` check compares the box against this
   checkout, so a mismatch means the *box* is, and no wording would fix
   it. The state checks run even when STATUS.md cannot be read at all.
4. **The deploy check compares file mtimes, never commit times**, and the
   obvious version was wrong on the day it was written: the daemon
   entered active at 09:58:28 and the newest commit touching `sysadmin/`
   landed at 10:05:22 with identical content, because this repository
   restarts to verify and commits afterwards. The newest `.py` on disk —
   09:57:46, 42 s *before* the start — answers the question actually
   being asked. The cost is stated: a rebase, or a file the daemon never
   imports, reports a restart owed, and that fails in the direction that
   costs a needless `kill -TERM`.
5. **A *fall* in the unresolved-alert count is the founding case.**
   Equality, or a rise, is the rule anyone would write. This snag exists
   because `SNAG-DB-002`'s eight collation rows resolved themselves at
   18:01:48 when estate-manager ran the `REINDEX` and four documents went
   on asking for it — so a fall is the signal that already existed and
   had no reader. Open titles are named, never counted.
6. **Nothing here writes to a document**, and there is no `--quiet`: a
   check that corrects the file it reads becomes a second author of the
   claim, and a flag nothing passes is `SNAG-CFG-001` at the size of a
   flag.

Three things only running it could have said. `systemctl show` **answers
for a unit that does not exist** — exit `0`, `ActiveState=inactive` —
which is this snag's own shape inside its own fix, so `LoadState` is the
gate and its test drives the real binary. `len(app.routes)` is **50**
against the documented **46**, because FastAPI adds `/openapi.json`,
`/docs`, `/docs/oauth2-redirect` and `/redoc` itself. And the check
**refuted its author within a minute**: the first rewrite of the block
wrapped `holds **2**` and `unresolved` across two lines with a `>`
between them and the claim came back `unknown`, which is why the region
is flattened before matching. `SNAG-ESTATE-011` is what remains — the
block's other claims are prose no pattern can reach.

**The other claims name the check that closes them, and the marker that
works is the one that states no fact** (Session 76, `SNAG-ESTATE-011`).
Five figures were machine-checkable and the rest of the block was prose;
the entry proposed `<!-- check: … -->` and refused a marker in the next
clause, which is `ops_claims.py` rule 1 — `<!-- routes=46 -->` beside a
sentence can agree with the box while the prose disagrees, and nothing
notices. **`<!--check:routes-->` is not that.** It names a *check*, never
a value, so the figure in the prose stays the only statement of itself
and the two cannot disagree about a fact, because one of them states
none. Live, the first run against the real block reported **five
unclaimed figures** — every one a sentence checked for a sitting and
never claimed.

Four rules, three of them the opposite of the obvious implementation:

1. **The marker is additive and cannot subtract.** Every pattern-bearing
   claim runs whether or not a line names it, so deleting a marker is a
   way to be *told*, never a way to retire a check. A marker that gated
   one would make "edit the document" a switch, which is rule 2's silent
   retirement arriving inside the fix for it. What the marker buys is
   `check_markers`: a figure this module can test that no line claims,
   and a marker naming a check nobody implements. A typo fires from
   **both** sides — `<!--check:helth-->` produced the unknown name *and*
   the now-unclaimed `health` beside it, which was not designed.
2. **A prediction is timed, not measured.** The entry was opened by *"the
   row clears at 03:32 with nothing done"*, written at 00:30 — not wrong
   when written and not measurable when written, so no pattern reaches
   it. `expires` is the one family whose **members the document
   declares**. After its moment the claim is `unknown`, never `mismatch`:
   the prediction may well have come true, and "nobody went back" is what
   rule 2 reserves `unknown` for.
3. **The instant is the one fact stated twice, so it is pinned rather
   than trusted.** The marker must carry a date the prose has no room for
   — "at 03:32" names a wall clock and no day — so the wall clock it
   renders must appear in the block or the claim is `unknown` naming both
   moments. `syslog_priority` against `PRIORITY_MAP`'s treatment. **The
   pin was broken and only a live run said so**: it searched the
   flattened region, *which contains the marker*, so it matched the
   marker's own copy and passed whatever the sentence said — a check
   agreeing with itself by construction. Three fixture tests of that pin
   were green either side of the fix, because their fixtures happen not
   to carry a marker.
4. **`check_open_titles` is the finer half of the alert count**, which
   holds still through a **swap** — one row resolving as another opens —
   while the sentence about *which* rows are open goes wrong. One
   direction only: a row the block names that has resolved is already
   `check_alerts`'s *fall* note, and what that note cannot say is that a
   row nobody wrote about is open.

`/health` is checked and **8400 deliberately is not**, though the block
asserts both. The first is a different fact from the deploy check's —
`systemctl` reporting `active` says the process is up, `/health` says the
application is serving, and `SNAG-DB-005` is the 23 hours where those
parted company. The second is estate-manager's availability, which
`estate/judgements.py` rule 3 declines to judge here; a claims-checker
that alerted on it would re-import the second owner that rule exists to
prevent. The block says so in its own prose rather than leaving the
silence to be read as an oversight — which is the cheapest form of the
convention for a claim no pattern reaches, and is `SNAG-ESTATE-012`: a
sentence with **no pattern and no marker** is still invisible, because
deciding that an English sentence is a claim is a human's job.

The cost is stated rather than implied: the markers are HTML comments and
do not render, but `claude-preflight.sh` prints the block as raw text, so
the session-opening banner is slightly noisier and every figure in it now
carries the name of the thing that would refute it.

`dev` and `tray` are `[project.optional-dependencies]` here rather than
dependency groups, so **a bare `uv sync` prunes them** — pytest, ruff,
mypy and PyQt6 all go, and `uv run pytest` then falls through to
`/usr/bin/pytest`, which fails on `import estate`. The command is
`uv sync --all-extras`.

**What autogenerate compares has one statement, and it is production
configuration the test borrows** (`SNAG-DB-003`). `sysadmin/metadata.py`
owns `FROZEN_TABLES`, `include_object`, `include_name` and the
`COMPARISON_OPTS` dict; `alembic/env.py` splats it into
`context.configure` and `tests/test_schema_drift.py` into
`MigrationContext.configure(opts=…)`. It sits beside `Base` because that
module already makes the same argument for the *model set*, and which of
the live schema's tables the metadata is authoritative for is that
question one step further.

The two copies it replaced failed in **opposite directions**: an
exclusion present only in `env.py` makes the drift guard fail loudly,
while one present only in the guard is silent — green test, and the next
`alembic revision --autogenerate` writes `op.drop_table` into an
unrelated migration. Measured with the exclusion removed: `remove_table`
for both frozen tables, against 3,739 and 4 live rows.

**`FROZEN_TABLES` is empty since migration 014 and is deliberately
kept.** An entry there is a *blindfold* over the drift guard, which
compares whatever `include_object` admits — so dropping the three tables
needed the set emptied rather than a new test to prove them gone, and
every live table is mapped again. Deleting the constant with its last
member would take this guard against the copy coming back with it, at
the moment nothing is exercising it. A domain leaving and stranding its
tables is a shape this estate has produced once; an entry added here must
be paired with a *drop* entry on the roadmap, because frozen is a stage
and not a destination.

Three rules. **The flags travel with the exclusions**, because
`compare_type` set in `env.py` and absent from the guard leaves the
guard green while blind to the drift it certifies. **The search_path
does not travel**: it belongs to the connection (`env.py` pairs it with
`CREATE SCHEMA`, DDL the guard must never run) and its drift fails
loudly as double reflection. **`tests/test_autogenerate_config.py` is an
AST sweep, not an import** — `env.py` runs the migrations at module
scope and cannot be imported — asserting there is no *second* body
rather than that two bodies match, which would pin the copy instead of
removing it. Two of its five tests exist so the detector can be seen to
fail: one runs the walker at the owner, which must trip every rule.

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

**That permanent `running` row is closed now, and the value for it had
been sitting in the constraint since migration 001** (Session 159b,
`SNAG-DB-006`). `chk_run_status` admitted `cancelled` and nothing wrote
one; the entry named two *opposite* fixes — drop the value or fill it —
and nothing recorded which was intended. The seven live rows decide it:
each is followed by a **clean** daemon death within **0.032–61.2 s** and
for each the next `agent_run_completed` for that agent comes from a
**different PID**. Against a base rate of **0.401 %** (162 of 40,383
`completed` runs) the separation is total, and `file_organiser` — the
widest exposure at ~108 s a scan — is **0 of 112** completed against
**3 of 3** stuck. So the value has a referent, at **4.9 %** of daemon
deaths. `sysadmin/core/abandoned_runs.py` is the sweep.

Six rules, four of them the opposite of the obvious implementation:

1. **It runs at *startup*, which is a third shape the entry does not
   name, and the discriminator is a race rather than coverage.** A
   shutdown-path write is what anyone reaches for and
   `scheduler.shutdown(wait=False)` returns while the worker thread is
   still inside `_execute` — three of the seven had 30–60 s of scan left
   — so it can land *after* a `completed` that thread commits. A startup
   sweep cannot race a process that is gone, and it is
   `core/unit_failure.py`'s argument one table over: the service
   starting is the only moment at which "that run will never finish"
   exists. Its reach into SIGKILL and power-off is **theoretical and
   says so** — all ten crash deaths in the journal died 2.1–4.8 s in
   (`SNAG-DB-005`'s schema-guard refusals), before the scheduler could
   fire anything, so on the live population both shapes reach 7 of 7.
2. **The instance id is minted in-process, never read from the
   environment.** systemd stamps `INVOCATION_ID` into this unit and it
   would do the job; this service reads no environment variables, and a
   lone exception is a convention that has stopped being one. A
   per-process UUID is also more general — an agent driven by hand from
   a session gets an identity, where an environment read gives every
   such drive the same absent value.
3. **A row with no stamp is refused, not swept**, which is what makes
   the fix forward-only *by construction* rather than by a constant. The
   seven predate the stamp, so the sweep cannot attribute them;
   `refused` **counts** them, because zero-because-blind must not read as
   zero-because-clean (`ports_checked`'s rule). The obvious alternative
   — an age cutoff — is an invented constant expressing a fact the row
   already carries.
4. **Nothing is capped and it cannot need to be.** The sweep runs on
   every start, so what it finds is one instance's in-flight runs, which
   `max_instances: 1` bounds; what is *logged* is the agent names, held
   at five by `AGENT_NAMES` whatever the volume, with `count` carrying
   it. `details['truncated_sources']`' rule.
5. **The status is a literal pinned to the constraint, not derived.**
   The constraint lists four values and says nothing about which means
   "abandoned", so `STATUS_READINGS`' treatment does not transfer; a test
   asserts `chk_run_status` still admits it, so a migration dropping the
   value — the entry's *other* fix landing by accident — is a red test
   rather than an `IntegrityError` on the next restart.
6. **It reports and never refuses.** Caught in the lifespan for
   `resolve_unit_failures`' reason and the exact opposite of
   `schema_guard`'s: a stale `running` row is worth less than a boot.

Verified live because the path had never run here: restart 1 gave
`abandoned_runs_unattributable count=7` and no closures, then a
`POST /api/files/scan` killed 2 s in gave restart 2
`abandoned_runs_closed count=1 agents=['file_organiser']` — the first
`cancelled` row in this database's life, carrying the dead instance's id
beside `cancelled_by: startup_sweep`.

**Three of thirteen falsifications passed against deliberately broken
code, and the first is the one worth carrying.** Deleting the
`IS NOT NULL` conjunct changed **nothing**: `NULL <> 'x'` is `NULL`, so
rule 3's refusal was being carried by SQL's three-valued logic rather
than by the clause written for it. The clause stays — its visibility is
what stops a reader "fixing" the NULL case with a `COALESCE` and
sweeping the seven silently — and it is pinned by **compiling the
statement**, because a clause whose removal is invisible in behaviour
cannot be reached by a behavioural test. The other two are the shapes
this repository keeps finding: `status == CANCELLED_STATUS` compared the
module's constant to itself, and **nothing drove `_record_start`**, so
deleting the stamp passed all twenty tests while the sweep went on being
proved correct about rows nothing in production would produce.

**Idle nudges are raised by the estate now, and judged here.** The nudge
— an `active` project whose human-written next action has not changed for
N days — was this repository's from Session 31 until the domain left on
2026-08-13 (ADR-0005). Its arithmetic, its per-project `idle_nudge_days`
override and the rule that eligibility is *borrowed* from the
next-project endpoint rather than restated are estate-manager's, and are
worth reading there.

What remains here is the consuming half, and it is the interesting half:
the estate publishes nudges on `GET :8400/api/projects/attention` and
**may not act on them**, so `judge_attention` turns them into alert rows
— taking the producer's severity verbatim rather than recomputing a rung,
because the ladder moved with the domain. Whether the quiet rung is
audible at all is still decided by **`tray.notify_min_severity`** — *not*
`notifications.desktop.min_severity`, which is parsed and read by nothing
(SNAG-CFG-001).

**`SysAdminAgent._resolve_recovered` resolves alerts set-based**, and it
arrived by an argument being reused rather than rediscovered. The project
organiser made it first: a project deleted from disk never appears in a
scan, so it can never be observed *recovering*, a per-project loop leaves
its alert unresolved for ever, and retention purges resolved rows only —
which is how 1,664 rows accumulated by 2026-08-07, 326 of them sharing one
title. The fix was to ask the inverse question: which open alerts would
this run *not* raise. That agent left with the projects domain on
2026-08-13 (ADR-0005) and its own account of the rule is estate-manager's;
the statement it argued for is still here, on the service side (Session
41, SNAG-AGENT-004), where the same defect had reached **51,924 rows** —
twenty times the scale, and in two families rather than one:

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
   route. Only `depth` and the oldest-wait gauge are judged; the
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
measure.

**The busy day arrived, and the gauge moved rather than the threshold**
(2026-08-30, Session 139, estate message `d1939cf7` / their ADR-0076 and
ADR-0077, filed *before* the commit that carried it — their rule 3).
estate-manager's weekly review now **takes** a GPU lease instead of
sampling a counter, so it queues behind `venture-enrich-nightly` every
Monday 05:30 and waits **915–1038 s** across the five nights they
measured — over this repository's 900 s threshold every time, for a
third cause the "Estate queue starved" message does not name and cannot:
*the queue working exactly as designed*. Their surface gained
`waiting_reason` (`null`/`behind_holder`/`holder_overdue`/
`nothing_granted`) and `oldest_unexplained_wait_seconds`, which is
`oldest_waiting_seconds` with `behind_holder` masked to `null`.
`judge_queue_invariants` reads the masked field now.

Four rules, three of them the opposite of the obvious implementation and
every one settled against the producer's own code rather than its prose:

1. **The threshold did not move, and raising it was the wrong half.**
   900 → 1200 is what anyone reaches for and it buys nothing: at a
   bigger number the gauge still cannot separate a normal Monday from a
   stuck queue, it only says so later — and the Monday wait is bounded
   by *another repository's* timer, so any number clearing it is one
   schedule change from being wrong again. `config.yaml` now carries
   that refusal beside the leaf, because the leaf is where a future
   Monday false alarm sends someone.
2. **The mask is read, never recomputed.** `waiting_reason ==
   "behind_holder"` plus the raw gauge reconstructs the masked number,
   and reconstructing it makes this a second implementation of the
   producer's derivation — `SNAG-DB-003`'s shape, `max_priority_for`
   against `PRIORITY_MAP`. A test drives an *inconsistent* payload
   (`behind_holder` beside an unexplained wait) and asserts the row is
   still raised: the estate owns that derivation and disagreeing with it
   silently is how two statements of one fact drift.
3. **Absent is not masked, which is `ports_checked`'s rule at the size
   of a dict key.** `payload.get(...)` answers `None` both for a
   producer that looked and explained the wait and for one that does not
   publish the field at all. Collapsing them retires this family in
   silence the day the estate rolls back, so a payload with no such key
   falls back to `oldest_waiting_seconds` and labels the row
   `details['wait_gauge'] = "total"` — deliberately the **pre-fix**
   behaviour rather than a refusal, because over-reporting on a Monday
   is the failure this module survives and going quiet is not. The
   fixture's 2026-08-16 `backlog` scenario is a *real* specimen of that
   shape and is kept unmodified rather than re-captured; hand-editing it
   into the new shape breaks a test.
4. **The reason is named, because the producer names it.** The old
   message posed a disjunction and `waiting_reason` answers it — leaving
   it unread is `SNAG-UNITS-004`'s defect, under-reading a field the
   producer had already filled in. The two values that can still reach a
   row are exactly the disjunction's two limbs, which is why the
   sentence stays true. A value this repository has not been told about
   falls back to the disjunction rather than being rendered:
   `_port_of`'s refusal to title a finding from `subject`.

The trade the fallback makes is that the new field's **absence** is
survivable and therefore silent everywhere — so the only place it can be
loud is the live half, where
`test_the_wait_discriminator_is_still_published` fails if 8400 stops
publishing it. A graceful degradation with no separate alarm degrades
unnoticed. The three states are pinned against payloads built by running
`Arbiter.submit` → `tick` → `invariants` in estate-manager's own venv
against a scratch database — never the live `estate` one, which estate
rule 1 forbids writing and which two connections could not have been
rolled back across anyway.

`active_lease.hold_deadline` was rejected here as a threshold in Session
45 and the estate has since made that same deadline its `holder_overdue`
discriminator — asked of the database against the clock that set it, and
published as a *classification* rather than as a column for a consumer
to threshold. The rejection stands and the condition is named anyway. `base_url` duplicates `services.yaml` deliberately — deriving it
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

Six rules, four of them the opposite of the first draft:

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

6. **A transient holder is quietened, never suppressed** (Session 57).
The family's first two live rows are Alfred dev servers launched from an
editor — `nuxt dev` on 3110, `uvicorn --reload` on 8110, all three pids
in `app-code-oss-26348.scope`. The estate's finding is *literally
correct* and its remedy does not apply, so the row is raised at
`TRANSIENT_HOLDER_SEVERITY` (`info`, the only rung below
`tray.notify_min_severity` here) rather than dropped. **Dropping was the
obvious implementation and rebuilds this family's founding defect** —
Session 26b-A exists because a ports breach was detected, correct,
machine-readable and never said out loud, and a consumer that silently
declines to judge a published finding is that shape with nothing
recording the decision, which is `SNAG-CFG-001`'s. The roll-up takes the
loudest rung it swallows, so one genuine breach among six dev servers
still speaks.

The defect was **not a missing signal**. `Listener.transient` has named
these listeners since Session 26c; `PortReport.unit_ports` drops them for
`recommendations.py`'s correct reason and `unattributed_ports` never held
them, because a session scope *is* attributed — so the port fell out of
the stored blob entirely and `holder` came back `None`,
indistinguishable from 5432's genuine unattributability. That is
`ports_checked`'s rule one layer down. `transient_ports` is a **separate
blob key**, not a flag inside `unit_ports`: one field whose two consumers
want opposite safe defaults is Session 48's `UnitFinding.enabled` trap,
caught before shipping this time. `PortAttribution.of()` returns
`transient` as a bool that is always present, so
`holder.get("transient")` cannot read every service on the box as
non-transient by accident, and the ambiguity rule spans both maps — a
port held by a dev server *and* a real service is attributed to neither.

`SNAG-ESTATE-009` is the gap: the sweep is six-hourly and the judge
hourly, so a dev server started inside a sweep window is unattributed and
speaks at `warning`. Both closures were refused — a second `ss` caller
(which `_attribution` forbids in writing) and an hourly sweep (six times
the cost, for one annotation).

7. **The row says what the sweep *knew*, beside who it named — and that
is an annotation, not a rung** (Session 128). `PortAttribution.of()`
answers *who held this port* and returns `None` for **four** different
reasons; `reading()` answers *what the evidence says* and never returns
nothing: `held`, `transient`, `unattributed` (the sweep looked straight
at the port and could not name a holder — 5432, 8601), `unswept` (the
sweep ran before this listener started, which is `SNAG-ESTATE-009`), and
`unknown` (no stored row, a failed observation, or a blob predating the
key). `details['attribution']` carries it on every breach row and in the
roll-up.

Four rules, three of them the opposite of the obvious implementation and
every one settled against the live sweep rather than by argument:

1. **The discriminator was already stored and no consumer read it.**
   `as_blob` has emitted `unattributed_ports` since Session 26c;
   `attribution_from_blob` was written later for a different consumer
   and ignored it. So this is not new evidence, it is the **sibling** of
   the collapse rule 6 fixed one field over in the same function —
   `ports_checked`'s rule, which that rule's own closing paragraph cites
   while leaving this half standing.
2. **It moves no rung, and the refusal is on correctness where the
   entry's two are on cost.** Quietening an unattributed breach because
   the sweep predates it inverts `_attribution`'s stated posture — *"the
   enrichment is not allowed to become a dependency of the alert"* — and
   a failed `observe_listeners` returns **no** listeners, so every port
   would read unswept and the whole family would fall below
   `tray.notify_min_severity`. Session 26b-A's founding defect at full
   scale, as the fix for a seven-hour window. Gating on `ok` removes
   that failure and not the objection: the default for an unknown port
   would still be *"probably a dev server"*, a guess
   `attribution_from_blob` already refuses where a port held by two
   units is **dropped** rather than attributed to whichever sorted first.
3. **`ok` gates the evidence, which is the half that is easy to miss.**
   A failed observation serialises `unattributed_ports` as `[]`, and an
   empty list read as evidence is a confident statement about a sweep
   that never looked — `ports_checked`'s rule rebuilt inside the fix for
   `ports_checked`'s rule. `unattributed` is therefore `None` rather
   than empty whenever the sweep cannot answer.
4. **Uniform on every row, never only the odd one.** A key present only
   sometimes is the absent-vs-present collapse one level down, so the
   *value* carries the news and the roll-up keeps a reading for every
   port even though `holders` is filtered to the ones it named.

**The entry stays open and its own check said so.** The annotation
removes the indistinguishability the check is keyed on and moves nothing
about the mechanism. Two of the entry's measurements were also refuted
by the box: its four historic `warning` rows **predate `transient_ports`
in the blob by a day**, so this entry has never observed its own class;
and *"the window is six hours wide"* is the **p90** — 83 inter-sweep gaps
give a median of **1.30 h**, because `agent_first_run_delay_seconds: 60`
re-runs every added job on each daemon start and this daemon's median
life is 1.77 h. Both errors have one root: the mechanism was costed from
`config.yaml` and the code path rather than from `unit_audits`.

The check needed **widening before its third limb could be removed
honestly**, and the baseline is what caught it: `annotated` compared
detail *key sets*, so it saw a key added to one row and was blind to the
same key added to every row with a varying value — which is the shape
rule 4 requires. Measured before a line of the fix existed, so the check
would have reported `match` over a landed fix, which is worse than
flipping. `_detail_shape` compares values with each row's **own** port
rendered opaque rather than by naming `port`/`fingerprint`/
`audit_summary`, the three spellings of one number.

Verified live rather than only against literals. This family **shipped
with zero rows until 2026-08-16**, which was exactly `SNAG-ESTATE-002`'s
starting position: the estate's own `run_check` was driven in-process
against the real registry document with a listener bound on 8888, giving
clean → `breach` → clean, with no write to the estate's database. It
caught one defect no literal would have — the estate stamps a first
sighting `standing_days: 0.0`, and "Standing 0 days" reads as a rounding
artefact. Session 57 then re-drove the whole path against the real `ss`
and the real findings payload, which is what caught rule 6.

Two gaps are filed rather than assumed settled: `SNAG-ESTATE-002` (the
producer's `Nudge.title`/`.message` are `@property` and `asdict` drops
them, so this repository builds a format the estate believes it owns) and
`SNAG-ESTATE-003` (no escalation; the loud rung would be `critical`,
which is reserved for faults on this box, and the family most in need
already arrives pre-escalated from the producer).

**`judge_attention` was written against literals and refuted by data the
first hour it saw any** (Session 52). `GET :8400/api/projects/attention`
has answered `{"health": [], "nudges": []}` on all four occasions anyone
has looked, so every rule in that function was pinned against dict
literals **written by the same hand that wrote the consumer** — which is
the strongest evidence available and is not the same as an observation.
A populated payload was made from the producer's own code, driven
read-only in its own venv against the live estate database with
`effective_threshold` forced to 101 and `nudges.evaluate(default_days=0)`
so live rows qualify; everything else is the estate's, including
`dataclasses.asdict` over the real `Nudge`, which is the point — the
field names are what an unforced payload would carry.

Two defects came out of it, and **neither is a rule this repository had
to invent**; both were already written down for other families and never
applied here.

1. **The row count is capped, per family.** The run produced **31 rows
   and 31 tray fingerprints from one hourly poll** — 26 health breaches
   and 5 nudges. Every breach is worth its own row while there are few
   of them, because a roll-up cannot name anything (Session 46); above
   `attention_max_rows` the count *is* the news, since twenty-six
   repositories do not go bad between two polls but a threshold moved in
   the estate's `config.yaml` does exactly that to all of them at once.
   The two families collapse **independently** — separate producers
   inside the estate (a score against a threshold; a streak against a
   schedule) that fail separately, and collapsing the working half
   because the other broke hides the half still naming its projects. The
   recording lands on both sides of the cap without being made to: 26
   collapses, 5 (the whole eligible nudge population) does not.
2. **A roll-up takes the loudest rung it swallows.** Collapsing rows
   must not also quieten them: `info` is below `tray.notify_min_severity`
   here, so an escalated `warning` nudge folded into an `info` row makes
   the fix for noise the reason the one entry that earned a toast never
   got one. Volume is not severity in the other direction either — a
   roll-up of six `info` nudges stays `info`.

The message is also cut with `truncate_at_word` at `NEXT_ACTION_CHARS`
and the full action kept in `details['next_action']`. The live actions on
this estate reach **469 characters** and `alert.message` reaches a
notification body verbatim, so the daemon was cutting them at a point
nobody chose — `SNAG-BRIEF-002` exactly, one domain over. That the
producer independently reached 120 for the same destination is not a copy
to deduplicate: its constant is private, behind a property `asdict` drops.

The seam itself is guarded where the other two 8400 routes already were,
in `tests/test_estate_project_contracts.py` rather than a new file. Its
live half can only assert the envelope, so the per-entry assertions are
**pre-staged** — they begin running by themselves the first day the
estate publishes a breach or a nudge, which is also the first day they
could catch anything. One of them asserts `title`/`message`/`details` are
*absent* from a nudge, so the day estate-manager closes its side the
suite says so and names the next move.

**The other three surfaces went the same way, and the defect is the one
a literal cannot hold** (Session 54). Every rule in
`judge_projects_invariants`, `judge_audit_*` and `judge_queue_invariants`
was pinned one condition at a time, because a keyword override to a test
helper produces one condition. **The producer cannot separate them.**
`ScanOutcome.estate_written` starts `False` and is set near the end of a
run, so *every* failing scan carries `error` and `estate_written: False`
together — two rows for one fault, the second reading "the last project
scan **completed** without rewriting estate.json" of a scan that did not
complete. The rule is now narrowed to a scan that did not error, which is
`failures.py`/`stalls.py`'s mutual-exclusion-by-construction one domain
over. What made a redundancy worth fixing is Session 53: a wrong row is
no longer one toast, it is a daily restatement.

The payloads are the producer's route functions, ORM models,
`_streak_starts` and `CheckResult.as_summary`, driven in estate-manager's
venv against the live `estate` database inside rolled-back transactions —
**one notch weaker than Session 52's** and it says so in the fixtures: the
unhappy *rows* are synthetic, because 0 of 7 `scan_runs` and 0 of 22
`audit_runs` have ever carried an error. The `ports` breaches are not:
real listeners on 3900–3905 through `ports.run_check` against the real
registry document.

Three further things it settled. **`EstateJudgeAgent._execute` claims a
title as it raises it** — `open_titles` was read once, so two judgements
sharing a title in one run inserted two rows, which
`judge_audit_findings` rule 4 makes reachable by keeping the finding's
`code` out of the title on purpose. **`details['code']` is `None` on
every payload the estate can serve** (`SNAG-ESTATE-006`): `AuditFinding`
has no `code` column, the value survives only inside `fingerprint`, and
splitting that is this repository parsing a format the estate owns — so
the field is still read, the absence is asserted, and the fix lands on
the producer's side with no change here. **Two rules are unreachable
against today's producer and are kept anyway** — the scan's
`finished_at is None` (the row is written once, after the scan) and the
audit's `error` (`_record` builds `AuditRun` without one) — named in the
docstrings so their silence is not read as health.

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

**The repository health score is the estate's.** `status: archived`'s two
waived deductions, the marker scan that excludes `*.md` so a repository's
own `snag_list.md` stops lowering its score, the whole-word `grep -w` and
the per-project truncation cap — every rule that turns a repository into a
number moved with `sysadmin/projects/` on 2026-08-13 (ADR-0005) and is
argued for there. What this repository does with the result is judge it
from outside: `judge_attention` reads the breaches the estate publishes
and never recomputes a score.

The weekly disk review is **figure-free by construction**, not by
instruction, and uses `strip_markdown` from `sysadmin/core/text.py` —
which now re-exports `estate.text`, the mechanism having gone to the
library when the project review that shared it left. It lived in `core`
because neither domain could import the other; it stays there because the
signature stayed and every importer here is unchanged.

`GET /api/files/actions` was built as the file-organiser mirror of
`/api/projects/actions` — estate-manager's route since 2026-08-13 — with
one deliberate difference: its currency is
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

`GET /api/files/review` is the weekly disk review, stored in its own
`disk_reviews` table. It was built as the mirror of the project review
that has since moved to 8400, and is now the only LLM-narrated review this
service produces. Two rules govern any LLM-narrated
review here, both learned from live runs:

1. **Commit the read transaction before calling the LLM.** This host sets
   `idle_in_transaction_session_timeout=1min` and inference takes longer.
2. **Give the model no numbers — do not merely instruct it not to use them.**
   Verified 2026-08-06: handed "25.0 GB across 50 directories" plus an
   explicit "do not restate figures", dria-agent-a-3b restated them *and*
   published the quotient as "each consuming 5GB". `build_review_prompt` is
   now figure-free by construction (sizes → bands, categories → phrases,
   occupancy → a direction), guarded by a test asserting no digit reaches
   the model **from the data** — the narrow form, because every
   `REVIEW_INSTRUCTIONS` block numbers its sections and caps the model at
   150 words, and those digits are instructions to the model rather than
   measurements about the box. Two of the three Tier 3 docstrings claimed
   the wider "contains no digit by construction" until 2026-08-25
   (`SNAG-DOCS-004`); the rule is stated once now, in
   `tests/review_prompts.py`, and each of the three modules drives its own
   prompt against it. Every real figure lives in `build_facts_section`,
   which is prepended to the narrative deterministically. `strip_markdown` removes
   the headings and lists the model emits despite being told not to.

The three `/api/files/*` action endpoints share one manifest shape and are
**dry runs unless the request body sets `confirm: true`** — see
`sysadmin/files/actions.py` for the safety rules (root confinement,
no symlink following, no overwriting, trash instead of delete).

`POST /api/projects/{name}/branches/prune` applied the same contract to
git branches and **moved with the domain** (ADR-0005). Its safety rules —
merged-into-the-default-branch eligibility, `include_unmerged` gated on
both the request and config, and the default/protected/checked-out/worktree
branches that are never deleted whatever the flags say — are
estate-manager's now. The `agents.project_organiser.branch_actions` block
in `config.yaml` is still parsed here and read by nothing, recorded as
knowingly untidy in ADR-0005 rather than trimmed in the same sitting:
config classes fan out into defaults tests.

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

**Advice has to be executable, and Session 48 was the first sitting to
carry it out.** Sessions 46, 47 and 26c made the diagnosis speak; nobody
had run what it says. Two defects surfaced inside an hour, both the same
root cause — `recommendations.py` under-reading a `UnitFinding` the sweep
had already filled in (`SNAG-UNITS-004`).

**A snippet is offered only for a unit something starts.** `kind:
systemd` asserts the unit is *active* and `kind: timer` that the schedule
is armed, so wiring up a disabled unit declares a check that fails on
every poll for ever — measured: the two suppressed snippets would each
have written a `critical` **every 300 s**, the pile-up Sessions 41–45
spent themselves deleting, arriving through this module's own remediation
text. The gate is **"nothing enables it", not "it is not running"**:
`enabled` is an enablement symlink `scan.py` already walks and
`classify_units` folds a oneshot's timer enablement into it, so the
no-subprocess promise survives where an `ActiveState` test would have
cost it. `manual` is a subset — no `[Install]` means it cannot be
enabled — so it is tested first and keeps its wording.

**A folded oneshot's timer is removed with its service.** `monitor_unit`
names the timer, and the timer is the half carrying `[Install]`, so it
holds the enablement symlink `removal_command`'s docstring exists to
avoid orphaning. Removing only the service leaves a `Requires=` pointing
at nothing, which the next sweep cannot see — a timer with no service is
not a finding shape this module has.

Both imply the rule that closes the family: **a row offering no snippet
must never say "paste the snippet below"**. `sysadmin-failed.service`
shipped exactly that, which is an item an execution sitting *cannot
close*, so it returns on every sweep for ever — `SNAG-ESTATE-001`'s
roll-up defect wearing a single unit's name. Every no-snippet row now
names its real next step, and for a disabled unit that step is a fork.

Note the polarity trap the fix exposed: `UnitFinding.enabled` defaults to
`False`, which is right for `armed` (absent evidence reads as "not
armed", quiet) and the **opposite** of what this gate wants (absent
evidence suppresses advice, loud). One field, two consumers, opposite
safe defaults — fixed in the fixtures, because flipping the default would
quietly arm every orphan.

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
— the third scorer, after the repository scoring that moved to the estate
on 2026-08-13 (ADR-0005) and the
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

**The services scorer had an advice half at last, and building it found
the score itself wrong by 60 points a service** (Session 78, Tier 2).
`GET /api/services/actions` is the fourth sibling of `/api/files/actions`,
`/api/logs/actions` and `/api/units/actions`, and
`sysadmin/monitor/service_recommendations.py` is its pure module. The
currency is **recoverable points**, straight off `Deduction.points` —
which is why this endpoint has a real one where `UnitRecommendationInfo`
deliberately has none.

**`skipped` was being scored as an outage, and only the advice endpoint
made it loud.** `services.yaml` declares `monitor: false` on three
services that are inactive by design; the agent writes those checks as
`skipped`; `score_service` excluded only `error` from its rates, so a
`skipped` row counted as measured-and-not-`ok`. All three scored **35**
and graded `failing` off 307 checks nobody had taken, from Session 25
(2026-08-07) until 2026-08-25. Live either side of the fix: **6 rows and
213 points → 3 and 33**, `failing` 3 → 0, mean 92.1 → 98.6, with 180 of
those points and every one of the endpoint's `risk` rows fabricated.

Five rules, four of them the opposite of the obvious implementation:

1. **Neither obvious reading of `skipped` is right, and the sibling rule
   does not transfer.** `SysAdminAgent._resolve_recovered` treats it as
   *healthy* — correctly, because an open critical nobody will look at
   again is a pile-up wearing a declaration as an excuse — but that
   decides whether to close an alert. Importing it here fabricates a
   **100** exactly as scoring it down fabricated a **35**. It joins
   `error` in `UNMEASURED_STATUSES` and `confidence` carries the truth:
   `ports_checked`'s rule, zero-because-blind never served as
   zero-because-clean. `skipped_checks` is counted apart from
   `error_checks` (migration 015) because "the check failed" and "nobody
   looked, by choice" are different claims with opposite remedies —
   `UnitFinding.enabled`'s trap, already paid for once.
2. **The confidence gate is asymmetric, or the endpoint ships empty.**
   All 30 services read `confidence: low` on the build day: the box was
   off 2026-08-18 → 08-22 and `SNAG-DB-005` killed the daemon a further
   22 h on 08-23, leaving `observed_days: 1.07` at `coverage_percent:
   15.13`. A `confidence == "high"` gate is the obvious implementation
   and is `SNAG-LOG-002`'s measured-empty population for the **third**
   time. The way out is what each row *argues from*, because a gap is
   one-directional — it can hide an outage and never invent one. So
   `outage`/`flapping`/`timer_failed` are floors under their own claims
   and survive a thin window; `check_interval`/`timer_stale` argue from
   a rate or an absence and require `high`. `log_trends.py` rule 4's
   `NEW` asymmetry, one domain over. `suppressed_by_confidence` counts
   what was withheld, so "nothing to do" and "we could not tell" stay
   distinguishable.
3. **The currency differs from its siblings in *tense*, and that is said
   on every row.** Reclaimable megabytes are freed when the duplicate is
   deleted; reliability points are charged for failures already inside
   the window and lapse only as those age out. So `recoverable_points`
   is a forecast — "what stops being deducted once the fix has held for
   `window_days`" — and each points-bearing `detail` says so in words.
   `FileRecommendationInfo`'s argument extended: a field whose *unit* is
   decided by the producer is unreadable at the call site, and so is one
   whose tense is.
4. **Timer staleness parses no clock**, because the obvious approach
   rebuilds `SNAG-LOG-009`. `service_health.details['last_run']` is
   systemd's `LastTriggerUSec` rendered as a **local wall clock with a
   zone abbreviation** — ambiguous between zones, two instants at an
   autumn fold. The token is treated as **opaque** and compared only for
   inequality; the clock is `checked_at`, a `timestamp with time zone`
   this application wrote itself. Live, that derives **24.0 h** for all
   five daily timers, `alfred-evaluate-timer` included despite 15 holes
   in its series. A hole under-reports staleness rather than
   over-reporting it — a fire before a gap is observed at the first check
   after it — so the failure direction is silence.
5. **The cadence has its own lookback and a 7-day window cannot hold
   one.** `timer_lookback_days` is 30 and deliberately not
   `reliability.window_days`: `estate-manager-review-timer` is weekly, so
   the scoring window observes **one** firing and therefore zero
   intervals, and a staleness rule built on it would be structurally
   blind to every weekly timer here. A gap-spanning interval is never a
   cadence sample — it measures the outage, not the schedule.

`timer_stale_multiplier` is **derived by reuse**: it is
`self_monitor.stall_grace_multiplier`'s 3.0, for that field's own
argument — a schedule that has missed one firing is merely late and
clears on the next tick. `flap_min_episodes` is **invented and says so**,
`NOISE_MIN_OCCURRENCES`'s status stated the same way.

The module is named `service_recommendations` rather than
`service_actions` because **the collision was real**: "service action"
already means start/stop/restart here, and `tests/test_service_actions.py`
has covered `POST /api/sysadmin/services/{name}/{action}` since the
tray's Phase 3. Two of the three siblings use `recommendations` anyway.
The route keeps `/actions`; only the module moved. GET-only and always
will be, asserted by a test, for `units/router.py`'s reason.

Two costs filed rather than implied, both at the owner's explicit
direction to build `tasks.md`'s scoped examples as written and record the
conflict rather than decide it. `SNAG-SVC-001`: advising a longer check
interval is advising that a fault be *seen* less often, which is
`known_noise` rule 3's opposite — narrowed so it can only fire when every
episode lasted a single check, and worded to refuse a remedy, which is a
narrowing and not a fix. `SNAG-SVC-002`: `timer_stale` asks `stalls.py`'s
"has it run?" about a timer rather than an agent, with no ladder and no
cross-reference — disjoint populations today only because no agent on
this box is a systemd timer, which is a property of the box and not of
the design.

**What the tests were doing is the part worth carrying.** The whole suite
passed either side of the `skipped` fix, so a wrong score was not merely
undetected but untestable-by-omission. And **two of eight falsifications
passed against deliberately broken code**: the `waived` test set
`muted=True`, so the muted skip returned before the filter it named was
ever reached, and the cadence test passed one firing where it claimed to
test two. A third — the episode-count assertion — passes against the
broken scorer for the wrong reason, since a `skipped` row also failed to
split an episode by counting as *down*. All three repaired, plus an
invariant test pinning `reliability._deductions`' `waived=muted` at its
owner, since this module leans on a fact another module holds.

**One fault occupies one row, and the entry asking for it had measured
half of its own population** (Session 149, `SNAG-SYSD-006`).
`recommend` runs `_service_rows` over every scored service and
`_timer_rows` over the subset that are timers, so a `kind: timer`
service is in **both** loops; once `SNAG-SYSD-005` let a failed job
reach `service_health.status`, `GET /api/services/actions` served
`alfred-career-mail-timer` twice — `outage` at 6 recoverable points
beside `timer_failed` at 0, one fault named twice. `group_faults` and
`_folded_row` are `log_actions.group_incidents`' treatment applied to a
relation with no clock and no systemd graph in it. Live either side:
**8 rows → 6**.

Six rules, four of them the opposite of the obvious implementation and
two of them settled by controls belonging to a different entry:

1. **The key is the service plus `EVENT_ARGUED`, and the entry's own
   scope was the smaller half.** It describes a timer collision;
   `venture-chat` had been serving `outage` 26 beside `flapping` 25
   since the endpoint shipped on 2026-08-25 — **eight days**, one
   service named twice, no timer in it. Reading the entry finds one
   instance, running the endpoint finds two. `RATE_ARGUED` rows never
   join: `check_interval` and `timer_stale` argue about how a service is
   *watched*, which `KIND_ORDER`'s docstring already separates, and
   fixing the service lapses neither.

2. **That narrowing was decided by a live control, not by taste.**
   `snag_claims.check_check_interval_looks_away` finds its row with
   `next(r for r in recommendations if r.kind == "check_interval")` — a
   **top-level** scan — and its synthetic subject produces exactly
   `flapping` + `check_interval`. The obvious "one row per service"
   makes that `None` and reports `SNAG-SVC-001` **refuted** by a change
   with nothing to say about it: a landed fix for one entry deleting
   another entry's instrument. Its third limb reads this module's
   **import set** as the instrument for *"the advice has the service's
   own log data now"*, so reaching for `group_incidents` by *importing*
   it refutes the same entry from the other side. The treatment is
   therefore applied and the module is not imported, pinned by an `ast`
   walk — a docstring mention is an `ast.Constant`, and this module
   names `log_actions` in prose four times. Driven by stash before and
   after: all 18 checks report `still holds`, unmoved.

3. **Points are summed, and the invariant is what decided it.** Every
   member shares one currency and one subject, so the sum is the
   service's applied deductions — exactly `100 - score` — and one fix
   lapses them together, which is the honesty
   `_incident_recommendation` says summing would *not* have across
   kinds. It is also what keeps `total_recoverable_points` **invariant**:
   78 before and 78 after, where an anchor keeping its own share alone
   would have reported the same box at 53 on the day the list got easier
   to read. `members` carries the anchor too, so the figure decomposes.

4. **The anchor is `KIND_ORDER`'s first surviving kind, doing one job
   rather than two.** That constant already answers "which claim is more
   urgent to read" for rows tying on points; which claim leads a fold is
   the same question. Cause-first anchoring was put to the owner and
   refused — `timer_failed` genuinely causes the checks the `outage` row
   is computed from, which is `group_incidents`' anchor rule read
   literally, but it needs a declared cause-to-consequence pairing this
   module has not got and would put the summed points on the row whose
   evidence did not compute them. `SNAG-SVC-003` is the cost, filed
   rather than implied: for a timer fault the anchor's step names a
   *restart* the swallowed row's own detail explains cannot help.

5. **The title stays the anchor's, where an incident row's does not.**
   `_incident_recommendation` rewrites its title because its members are
   *other units*; every member here is about the **same service**, so
   the anchor's sentence already has the right subject and appending a
   count to it is the count-that-names-nothing `SNAG-ESTATE-001`
   removed. What is named is named whole: each swallowed finding's kind,
   title, detail, action and points, in `members` **and** in the folded
   `detail`, because the steps differ in kind and cannot be merged the
   way six `journalctl` invocations can.

6. **Nothing is capped and it cannot need to be.** A service has at most
   three `EVENT_ARGUED` rows, so a fold names at most two members — the
   roll-up that cannot name what it swallowed is unreachable by
   construction rather than by a threshold, which every other roll-up
   here needed.

**Two of the six are vacuous, in opposite directions, and both say so.**
*Loudest-rung-wins* is implemented and cannot currently lose: `outage`
is the only `risk`-capable kind and is `KIND_ORDER`'s first, so the
anchor is always at least as loud as what it swallows — a proof about
today's five kinds that a sixth invalidates in silence, so the rule is
written and a test pins the coincidence. *Gate-before-fold* is
**unobservable**: driven both ways on one low-confidence subject the
output is identical, because rule 1 makes the suppressible set and the
foldable set disjoint — so the test pins the **disjointness that makes
it vacuous** rather than an ordering nothing could distinguish.

**The fix had to land twice, because a consumer flattened it back.**
`health_review._service_facts` projects `title` and `action` — both the
**anchor's** — into the weekly review's `top`, so the first version
named one finding and never told the reader the other existed: the
roll-up that cannot name anything, rebuilt one consumer downstream of
the fold that promised not to. `stands_for` carries the swallowed titles
through, keyed on the **kind** rather than on position, so it is not a
second statement of how `group_faults` sorts.

**Two of eleven falsifications passed against deliberately broken code.**
Anchoring by points instead of `KIND_ORDER` broke nothing, because the
live specimen cannot discriminate the rule — `outage` leads
`KIND_ORDER` *and* carries all 6 of career-mail's points — so a subject
with 1 point of downtime against 25 of instability had to be added
before the anchor rule was tested at all. And emptying the review
projection's `stands_for` passed cleanly, because the digest test
injected the field into a fixture and therefore pinned the renderer
while saying nothing about the projection that fills it; it drives the
real `recommend` at the folding shape now.

**That consumer had a second fact to flatten, and the question was
whether to read it or work it out again** (Session 155,
`SNAG-SVC-004`). `SNAG-SVC-003` let a `timer_failed` member's step
supersede the anchor's, and `_folded_row` rule 5 wrote *whose* step is
leading into the folded `detail` — which this projection does not carry,
so the review printed one finding's remedy under another finding's title
and nothing said the subject had changed.
`ServiceRecommendationInfo.action_from` is that fact as its own field:
the promoted member's `kind`, empty when the step is the anchor's own.

Four rules, three of them the opposite of the obvious implementation:

1. **`stands_for`'s treatment is a *derivation*, and copying it
   literally would have been the defect.** That field is
   `m.title for m in members if m.kind != r.kind` — a restatement of
   what *swallowed* means, which is structural and cannot disagree with
   the producer. The same shape here is
   `next(m.kind for m in members if m.kind in STEP_SUPERSEDES)`, which
   restates which member **won**: a judgement `_folded_row` already
   took, free to drift the day that tuple widens. `SNAG-DB-003`'s
   shape, and `judge_queue_invariants`' *"the mask is read, never
   recomputed"*. So the producer publishes it (`_folded_row` rule 6) and
   every consumer reads it. One mutation is exactly the recomputing
   projection and exactly one test is red on it.
2. **Empty is deliberately *not* `ports_checked`'s not-knowing.** The
   field reads `""` both for a row whose step is its own and for a
   producer that does not publish it at all. Every other absent-vs-present
   collapse in this repository hides a *blind* reading; this one cannot,
   because both spellings mean "render nothing extra" and no consumer
   can act on the difference. So the renderer gates on truthiness alone
   rather than on `action_from != kind`, which would restate the
   producer's rule and print `The step is the  finding's` for an
   unfolded row.
3. **Spelling it as the row's own `kind` was refused**, which is where
   Session 128's *"uniform on every row"* does not transfer: that rule
   is about a `details` **key** whose presence is the only signal, and a
   pydantic field is always present. The uniform-scalar version fires
   the renderer's clause on every folded row and makes every consumer
   compare two fields to learn nothing — `stands_for`'s empty list is
   the right analogue, not a value.
4. **The refused fix is pinned rather than merely avoided.** Projecting
   `detail` carries the provenance *and* every swallowed row's own
   detail and step into the blob the review is built from, so a test
   asserts `detail` is absent from the projection.

**Both fold shapes were live at the moment of the fix**, which is the
discrimination a specimen of one could not have supplied:
`alfred-career-mail-timer` (`outage` + `timer_failed`) reads
`action_from: "timer_failed"` and `venture-chat` (`outage` + `flapping`)
reads `""`, because `flapping` promotes nothing. The entry had described
the live line as *reading correctly by luck of one string* —
`_timer_failed_row`'s step happens to explain its own subject — and it
now says so in its own words instead.

**The guard is a test rather than a twenty-first snag check, and the
entry's own last bullet is why.** What one would drive asserts the
**fix**, and `check-snag-claims.sh`'s `ok` means *the bug is still
real*, so such a check can only report a landed fix for ever —
`check_review_schedule_unread`'s defect. `FROZEN_TABLES`' rule met from
the other end: `TestTheStepsProvenanceIsProjected` outlives the finding.

**The week the box had is narrated now, and the number it nearly
reported was off by three orders of magnitude** (Session 79, Tier 3).
`GET /api/sysadmin/review` is the **fourth** Tier 3 here, after the
project review that left with its domain, the disk review and the log
review. `sysadmin/monitor/health_review.py` is the module and
`health_reviews` (migration 016) its own table — a third review table
beside `disk_reviews` and `log_reviews` for Session 24's reason: the
reviews answer different questions and no migration should be able to
disturb another's rows. It does **not** reuse `project_reviews`, which
its own roadmap entry named and migration 014 dropped on 2026-08-24.

The two rules every Tier 3 follows apply (commit the read transaction
before inference; give the model no numbers rather than instructing it
not to use them). Three more, each settled against the live tables:

1. **The alert delta counts distinct titles, never rows.** This
   repository has written down four times that `alerts` holds one row
   *per failed check* — `reliability.py`'s "123 rows for one internet
   outage", `SNAG-AGENT-002`, `SNAG-AGENT-005`'s 598,091 rows,
   `judgements.py` rule 1 — and had never applied it to a *count of
   alerts*, because nothing counted them. Measured across the two live
   comparison windows: **24 rows against 59,650**, a 2,485x fall, of
   which **59,200 share one title** and fell on a single day. The same
   windows hold **17 distinct titles against 39**, a 2.3x fall, which is
   the shape a reader recognises. Rows stay in `stats` as evidence —
   dropping them would make a week with many faults indistinguishable
   from a week with one loud one — and no sentence is written from them.
2. **A fall is refused when the monitor's own coverage fell**, which is
   `log_review.direction_phrase`'s asymmetry against a different
   mechanism. There the one-directional thing is read truncation; here
   it is agent-run coverage, and the logic is identical because a period
   the monitor did not watch can hide alerts it never recorded and can
   never invent one. So a **rise** is trustworthy at any coverage and a
   **fall** is not. Load-bearing rather than theoretical: the two live
   windows were observed at **17.01 %** and **96.33 %** of expected runs.
   **Both** windows are measured, because checking only the current one
   reports poor coverage on this box and still lets every delta through
   unqualified — the previous window is the complete one here.
   `coverage_confidence` imports `reliability.LOW_COVERAGE_FRACTION`
   rather than restating 0.5, so a review cannot call a window
   trustworthy while every score inside it says the opposite.
3. **Disk occupancy is deferred to the disk review by name.**
   `GET /api/files/review` already narrates occupancy, its direction and
   its projected threshold crossings into the **same** 06:00 briefing, so
   a second narrative is the second-owner defect this repository has
   found at six scales. `NARRATED_METRICS` is CPU, RAM, swap and load —
   which nothing else on this box narrates at all — and the disk figures
   stay under `stats['resources']['disk_evidence']` so the review remains
   auditable against the snapshots the disk review read. The fallback
   digest **names** the review that does cover it, because an omission a
   reader has to infer is one they will not infer.

**The route is under `/api/sysadmin`, not `/api/services`**, which is the
one place this tier departs from its three siblings' naming and the
departure is what keeps a guard honest. `/api/services` carries a test
asserting that no non-GET route exists anywhere beneath it — the promise
that the reliability score is not a control surface — so a
`POST .../review/generate` there could only ship by narrowing that test
to admit the route being added. The content agrees: three of the four
inputs are alert volume, resource anomalies and resource trend, all
already served from `/api/sysadmin`, and only the fourth is service
reliability.

**Three defects the live run found and no fixture would have**, which is
the fourth Tier 3 and the fourth time this has been the headline:

- **The model inverted the one sentence that must not invert.** Handed
  "The monitor was down for much of this period", dria-agent-a-3b
  published **"The machine was down for much of the week"** — an outage
  report about a box that was merely unwatched, in a review whose other
  sections describe genuine service outages. `confidence_phrase` now
  names the *monitoring service* and denies the inference in the next
  clause ("That says nothing about how the machine behaved"), and the
  re-run produced neither the inversion nor anything like it.
- **A conversational preamble reached the narrative verbatim.**
  `strip_markdown` removes formatting, not prose, so "I'll help you
  analyze the Linux workstation's health report. Let me break it down:"
  would have gone into the briefing. One clause in `REVIEW_INSTRUCTIONS`
  fixed it; a stripper was refused as a fifth heuristic to maintain.
- **The prompt dropped two faults the instant a third appeared.** Its
  first draft named only `unreliable`/`failing` services and fell back to
  the whole list when there were none, so `searxng` and `alfred-frontend`
  — both degraded, both with real outages — vanished at the exact moment
  `venture-chat` went unreliable. Every service that dropped out is named
  now and the **grade** does the ranking, which is what the model reads
  anyway and what the instruction block's cap already bounds.

`STEADY_FRACTION` is **invented and says so** (`NOISE_MIN_OCCURRENCES`'
and `flap_min_episodes`' status), and it is cheap to be wrong about
because it decides a *word* in a figure-free prompt while every figure it
describes is in `stats` and in the facts section regardless. The Monday
slot is **derived**: 06:00 is the briefing, 05:45 the disk review, 05:15
the log review, and 05:30 is `estate-manager-review.timer` — another
repository's generation on the same 24 GB card, verified with
`systemctl --user cat` rather than taken from the comment that asserted
it. So the chain grows at the front, to 05:00, keeping the 15-minute
spacing the existing three already assume is enough for one generation.

Two limits filed rather than implied. `SNAG-DOCS-004`: `log_review` and
`files.review` both document their prompt as "contains no digit by
construction" and both contain `1`, `2`, `3` and `150` from their own
instruction block — the claim was always about the *data* half, which
`tests/test_health_review.py::TestPromptIsFigureFree` now asserts for all
three by partitioning each prompt at its own `REVIEW_INSTRUCTIONS`.
`SNAG-CFG-002`: `schedules.review_hour`/`review_minute` had driven
nothing since the projects domain left, and the reload's classification
test could not see them, because a path nothing reads is not a path it
classifies. **Both leaves are gone (2026-08-30, Session 135)** —
`review_day_of_week` stays, read by all three weekly reviews, and its
name is generic because that is now accurate rather than vague.

**A check that answers the same way either side of its fix is not a
check**, which is what that closure is worth carrying for.
`check_review_schedule_unread` returned `match` whenever it found no
reader, and a deleted field has no reader — so it would have gone on
reporting *still holds* over a landed closure, indefinitely. The
regression guard is keyed on the **absence** of the fields instead, and
carries a second assertion that the three surviving `*_review_*` pairs
are present, because an empty intersection is satisfied by a model with
no fields at all. The rule generalises past this entry: a control must
be driven at a stand-in modelling the *fix*, not only at one modelling
the defect.

What the deletion did **not** reach was `SNAG-CFG-004`, and the entry's
own headline fix was refuted by the file it was about (Session 136).
`config.yaml`'s models inherit `extra="ignore"` (**0 of 37**) while
`services.yaml`'s all set `extra="forbid"` (**4 of 4**), so
`briefing_hourr: 9` parses cleanly and the briefing stays at 6. **The
counts have not moved and must not**: walking the shipped `config.yaml`
against `AppConfig`'s field tree finds **ten keys the backend does not
declare** — the top-level `tray:` section and nine leaves under
`notifications.tray:`, every one read by `sysadmin_tray/config.py`,
which parses the same file for itself. `extra="forbid"` across the 37 is
therefore not a trade-off to weigh against `SNAG-DB-005`; it is a daemon
that does not start on this box.

**The asymmetry is structural rather than an inconsistency.**
`services.yaml` can forbid because every key in it belongs to the
process holding the models; `config.yaml` cannot, because it carries a
region this process does not own. One file, two parsers, neither a
superset — and `schema_guard`'s posture runs the *other* way here for a
reason that is about the cost side rather than the shape: that guard
refuses because serving against the wrong schema is worse than not
serving, and serving with an ignored config key is demonstrably not,
having been this daemon's behaviour for its whole life at a cost of one
briefing at the wrong hour.

`sysadmin/core/config_keys.py` is what shipped, and it **reports**.
Five rules, three of them the opposite of the obvious implementation:

1. **It cannot refuse**, and that is settled by the shape of the
   mechanism rather than by a flag someone could flip — a walker returns
   a list. The lifespan warns and `ReloadReport.unknown_keys` carries it
   to `POST /api/sysadmin/reload`, which is the surface an operator who
   has just edited the file is actually holding.
2. **It derives from `model_fields`** rather than restating the schema.
   A second hand-written list of valid keys is `SNAG-DB-003`'s shape,
   and the entry is about a key nobody declared.
3. **A shape it cannot classify is reported, never skipped.**
   `unwalkable` names a subtree that went unread, so its zero unknown
   keys are zero-because-blind — `ports_checked`'s rule, and a silent
   skip is this module's own defect one level down.
4. **Foreign keys are exempted by leaf, with `tray:` the one deliberate
   subtree.** `notifications.tray.mute_services` is read *here*, so a
   subtree exemption would silence `mute_servicess` on the one key under
   that section the backend depends on — the defect rebuilt inside its
   own fix. The dividend is unasked-for and real: because the correct
   spelling is exempt and a typo is not, a misspelt *tray-owned* leaf is
   reported too. `tray:` is exempt whole because holding a model of
   another parser's section is the second-owner defect.
5. **The boundary is pinned, not asserted.** `sysadmin.core` may not
   import the tray, so `TRAY_SECTION_KEYS` and `NOTIFICATIONS_TRAY_KEYS`
   were lifted out of the loops consuming them and a test asserts they
   agree with `FOREIGN_KEYS` — import where you can, pin where you
   cannot. A second test refuses an exemption naming a key `AppConfig`
   declares, because a stale exemption stops describing a foreign key
   and starts hiding one of ours.

**The drop is unchanged and only the silence is gone**, which is the
pair a later reader needs both halves of: no model gained
`extra="forbid"`, so the typo is still accepted and still dropped, and
`tests/test_config_defaults.py` keeps the parse half while
`tests/test_config_keys.py` holds the report half, each naming the
other.

**The residue had its own owner, and the fix belongs on the other side
of the seam** (`SNAG-CFG-005`, closed 2026-08-30).
`sysadmin_tray/config.py`'s `tray_section_report` names the keys under
`tray:` this program does not read — a `WARNING`, never a refusal, for
`config_keys` rule 1's reason. Four rules, three of them the opposite of
the obvious implementation:

1. **The allowlist is the authority, never the model.** A walk of
   `tray:` against `TrayConfig` is the shape `config_keys` uses for
   `AppConfig`, is legal here (`sysadmin.core` must not import the tray;
   the reverse is fine and this module already does it for `defaults`)
   and **would have shipped green**. `TrayConfig` declares **19** fields
   and the section supplies **7** — the other twelve arrive from
   `notifications.tray:`, `api:` and `services.yaml` — so a model walk
   calls `tray.reminder_hours: 5` declared when setting it there does
   nothing. The model over-declares relative to the section;
   `TRAY_SECTION_KEYS` does not, which is what Session 136 lifting it
   out of the consuming loop made available.
2. **`notifications.tray:` is not reported here**, because that region
   is exempt by *leaf* and the backend already names a typo in it —
   driven, not assumed: `digest_modee` and `mute_servicess` both come
   back from `report_for_file`. One fact, one speaker. The test that
   named this rule drove the **backend**, which proves the other speaker
   exists and does nothing to stop this one becoming a second, so a
   mutation appending a `notifications.tray.*` path went red on an
   unrelated test by accident. The negative half is a separate test and
   exists because the mutation exposed its absence.
3. **A shape it cannot read is reported, and that closed a crash.**
   `tray: 5` raised `TypeError: argument of type 'int' is not iterable`
   out of `key in tray_section` — the one section this module
   hand-parses failing unhandled, while `_read_services` next door costs
   "a mute list, not a launch". `None` is clean and a non-mapping is
   `unwalkable`, and the split is only reachable because the caller
   stopped coercing: `raw.get("tray", {}) or {}` hands the report a
   clean `{}` for `tray: []`, which is falsy *and* malformed.
4. **The payload is in the message, not in `extra=`, and only a live
   drive said so.** The backend's idiom is readable because
   `JsonFormatter` folds `extra` into the line; the tray's formatter is
   `main()`'s `basicConfig(format="… %(message)s")`, so the first
   version reached the journal as the bare event name
   `tray_config_unknown_keys` — announcing a dropped key and unable to
   say which, this entry's own defect one level down. The retired check
   had recorded the *opposite* lesson (its first draft read
   `getMessage()` and missed the backend's `extra=`), so the wrong half
   of a two-sided lesson was copied. The convention is "use `extra=`
   where a formatter renders it", never "always".

Two things the sitting corrected in the module rather than around it.
**`tray.api_url` has never been read** and the loader docstring listed
the `tray:` section as its resolution priority 2 since `81b3bfb`, the
module's first commit; the `if "api_url" not in kwargs` guard beneath
was dead by construction and its comment is what the docstring copied.
Both went — a reader checking the new report against the old docstring
concludes the *report* is broken — and the key stays unread on purpose,
because `service.host`/`port` is the one home for the backend's address
while `estate_api_url` is read from `tray:` only because 8400 has no
`service:` block. `SNAG-TRAY-011` is the residue in turn: the warning
reaches `journalctl --user -u sysadmin-tray` and nothing else
(`composed_log_sources` returns 15 units and `sysadmin-tray.service` is
not among them) and fires once, at startup, where the backend
re-reports on every `POST /api/sysadmin/reload`.

The entry's check retired with it and **its meaning inverted**. It
counted `extra="forbid"` on both sides; this fix moves neither count, so
it would have gone on reporting *still holds* over a landed closure —
`check_review_schedule_unread`'s defect one entry earlier, and not a
flaw in how it was written, since the entry closed by a route the check
did not anticipate. `TestTheAsymmetryIsDeliberateAndStays` is the same
walk guarding the opposite claim.

A **service name** is deliberately not filtered through the digit gate
`log_review` applies to a signature: a name is not a measurement, and a
service called `postgres15` would be deleted from the review entirely by
a gate that cannot tell the two apart. Empty population — 0 of 30
configured names carry a digit — so the rule is stated as policy rather
than dressed up as a measurement.

**A column read four ways has one classification, and it lives beside the
CHECK constraint** (Session 80, `SNAG-API-004`). `status != "ok"` was
written in four readers of `service_health.status` and was wrong in three
of them from the day migration 009 added `skipped` — a *declaration* not
to check, which every "not ok" reader silently reclassified as a fault on
the same day. `STATUS_READINGS` on `monitor/models/service_health.py`
classifies all seven admitted values as `well`/`fault`/`unwatched`, and
`is_fault()` / `is_unwatched()` are the readers.

Five rules, three of them the opposite of the obvious implementation and
all five settled against the live box:

1. **The population was three, and the entry named one.** `GET
   /api/sysadmin/status` is the route the snag names; `GET /api/summary`
   carries the identical phrasing and was never named by anyone; `GET
   /api/projects/managed` carries it too and is **the only one that was
   not masked** — measured 2026-08-25 it reported `venture-assistant` and
   `sysadmin_assistant` unhealthy with every real service `ok`, each
   having one `monitor: false` service beside its live ones. Reading the
   code finds the phrasing; only running the three routes ranks them.
2. **The classification sits beside the constraint, not beside a
   reader** — `max_priority_for` against `PRIORITY_MAP`. A test asserts
   it is **exactly total** over the constraint's own `sqltext`, parsed
   out rather than re-typed, so a status added by a migration fails the
   suite instead of falling silently to one side.
3. **`is_fault` fails closed and the totality guard is what makes that
   branch unreachable.** An unrecognised value reads as a fault, because
   a monitor going quiet about a state it does not understand is worse
   than a false alarm — `schema_guard`'s posture, not `collation.py`'s.
   The two guards are kept apart deliberately: one decides the direction,
   the other removes the case.
4. **`reliability.py` is pinned, never imported.** Its docstring promises
   purity ("no DB access, no FastAPI") and the vocabulary's owner is an
   ORM model, so its two status strings stay typed and a test drives both
   sides against the constraint — `syslog_priority` against
   `journal.PRIORITY_MAP`. Import where you can, pin where you cannot;
   the failure mode of neither is drift. It also stopped negating `ok`:
   `DOWN_STATUSES` names the four measured faults positively, which
   changes **no number today** — both readers run over `measured`, which
   has already dropped the unmeasurable rows — and changes the failure
   mode, since a newly-admitted status would otherwise be charged as an
   outage exactly as `skipped` was for eighteen days.
5. **A missing row is deliberately not a declaration.** On
   `/api/projects/managed` a service with no health row still reads
   unhealthy: a `skipped` row is a recorded *decision* not to look, and
   an absent row is nobody having decided anything, so there is no
   evidence to claim health from. Empty population today, pinned by a
   test so the fix is not generalised one step too far.

**The suite was green either side of all three defects**, which is the
part worth carrying: the tests covered a healthy box and an unhealthy one
and never a healthy box with a declaration on it, and
`/api/projects/managed` had **no test at all**, which is why its version
was the visible one. `TestNoReaderNegatesOkByHand` is an AST sweep over
every module that reads `ServiceHealth`, refusing a hand-written
comparison of a health status to `"ok"` — what made this the *third*
instance rather than the first is that the two earlier fixes each stopped
where somebody had noticed.

One falsification **passed against deliberately broken code**: `assert
SERVICES_SKIPPED is SKIPPED` is True whether `services.py` re-exports the
literal or retypes it, because CPython interns short strings. It asserts
a *value* where it means *provenance*, which is the shape recorded after
Session 59's guards, and only the source can answer provenance — it is an
AST check now.

**An index a reader cannot reach is not an index, and the two were eight
lines apart** (Session 105, `SNAG-AGENT-007`). `alerts` has carried
`idx_alerts_active … WHERE resolved = FALSE` since it was created.
Nineteen readers asked for their open rows as
`Alert.resolved.is_(False)`, which renders `resolved IS false`;
PostgreSQL matches a partial index **structurally**, and a `BooleanTest`
is not an `OpExpr`. Every one of them fell to a sequential scan.
`unresolved()` on `sysadmin/core/models/alert.py` is the one statement of
*open*, and it renders the index's own predicate literally.

Five rules, four of them the opposite of what the entry proposed:

1. **The entry costed the read by its result and the cost is its scan.**
   It ranked itself P3 on "the table is small"; the table is **666,936
   rows** and what is small is the answer — **zero** open `sysadmin`
   rows. Live: **41,644 buffers and 33.3 ms** against **13 buffers and
   0.03 ms**, four times per 300-second run. Reading the code confirms
   the entry's count; running `EXPLAIN` refutes its ranking, which is
   `verify-ops-claims-live` for a claim about performance.
2. **A projection is not a definition, which is what dissolves the
   tension the entry filed itself around.** It refused
   `select(Alert.title)` for the dedup caller as *"a second definition of
   this agent's open rows"*. What a caller wants **back** may differ per
   caller; which rows it is **asking about** may not. So the predicate is
   stated once and `SysAdminAgent._open_alert_criteria` composes the
   agent scope on top — a third projection tomorrow adds no third
   definition. `Alert.agent == self.name` deliberately stays at the
   agent: a scope one caller applies is not a vocabulary anyone can
   disagree about.
3. **Migration 017 alone would have been a no-op**, which is worth
   knowing because the obvious reading of a performance snag is that the
   database is missing something. `idx_alerts_open_by_agent` bounds an
   agent's read by *its own* open rows rather than by the whole open set
   — `SNAG-AGENT-005` reached 598,091 in one family — and driven at
   100,000 synthetic open rows in a rolled-back transaction the old
   spelling **with the new index present** still seq-scanned at 41,644
   buffers. Only the pair gives 2 buffers. Today the planner still
   prefers the older index, one open row making either free, so the new
   one is insurance that engages when the entry's worry materialises —
   stated rather than implied, since an index nothing chooses looks
   exactly like an index that does not work.
4. **The substitution is provable, not merely safe-looking.** `IS false`
   and `= false` differ on exactly one input and `resolved` is `NOT
   NULL`, which is why the definition lives beside the column: the column
   is the proof. A test asserts the nullability rather than remembering
   it, because nineteen call sites were rewritten on that one fact.
5. **The sweep is driven at its own owner.** `unresolved()` *is* the
   hand-written form — that is what makes it the one definition — so the
   AST guard exempts the model and then runs at it, which must trip every
   rule. `test_autogenerate_config.py`'s idiom, reused.

Note what was pinning the defect: `test_it_is_scoped_to_this_agents_unresolved_rows`
asserted the string `alerts.resolved IS false` and was green for the life
of the module — `TestJournalCommand` in a second family. It composes from
`unresolved()` now, so it pins **provenance** (the resolve uses the
shared predicate) while `tests/test_open_alert_predicate.py` pins the
**value** (that predicate renders the index's string). And
`test_alert_dedup.py`'s stand-in could not tell a projection from a row
read, so the fix arrived as four red dedup tests — the defect they exist
to catch, wearing the fix's clothes; it discriminates on
`selected_columns` now, modelling the database rather than the one call
site that happens to project.

**A row is deduplicated on its title, and until 2026-08-28 that froze
its sentence with it** (Session 110, `SNAG-AGENT-009`). Every family
that dedups takes a `held` branch and `continue`s, so `alert.message`
stayed whatever the *first* run wrote — and `details` with it, which the
entry did not say. `Alert.title` is the identity and must not move
(Session 42), but the message is what a reader acts on.
`BaseAgent.refresh_alert` rewrites both, and only when the recomputed
text differs. Measured before it was built: **1,360 held events
all-time** — threshold+service **838**, collation 386, estate judge
**131**, armed orphans 5, ports **0** — and across the 23 post-dedup
`High VRAM usage` rows **42 of 42** polls inside a hold carried a
different figure, 19 of them *below* the threshold the frozen sentence
was asserting.

Six rules, four of them the opposite of the obvious implementation:

1. **The base class owns the comparison and the write; finding the row
   stays with each caller.** The three reach it three ways for reasons of
   their own — the estate judge already holds the ORM rows,
   `_maintain_port_alerts` bounds its read by a title prefix, and
   `_raise_judged` keeps the title-only snapshot `SNAG-AGENT-007` gave
   it — so a base class taking a *title* would own a predicate its
   subclasses state three ways. `_open_alert_criteria`'s split of
   projection from predicate, read from the other end.
2. **The 838's row is read at the hold, never carried in the
   snapshot.** A snapshot widened to hold `message` and `details` is
   bounded by *the table*, and this agent's families reached 51,924 open
   rows before `SNAG-AGENT-004`; a read at the hold is bounded by *the
   judgements the run made*. Live at 665,937 rows it is **84 buffers,
   0.098 ms** — and lands on `idx_alerts_active`, **not** the
   agent-scoped index the first docstring claimed: one open row makes
   either partial index free and the planner takes the older one, which
   is exactly `SNAG-AGENT-007`'s own reading. `EXPLAIN` corrected the
   prose; reading the code would have shipped it.
3. **`details` is compared through a JSON round trip, or the gate
   degenerates into "always".** `JSONB` has no tuple, so a caller
   building `details` with one gets a list back next run and a plain
   `!=` reports a difference no write can settle — the gate switched off
   by a type, with the counter reporting corrections that corrected
   nothing. What is *stored* is the caller's dict, because a raise and a
   refresh handed one input must write one row.
4. **Only a row open before this run is refreshed**, which is why
   `_written_titles` is a second set rather than more entries in
   `_open_titles`. A title judged twice inside one run — two identically
   named GPUs, the case that put the `add` there — would otherwise have
   the *last* judgement overwrite the first, and which of the two is
   current is undefined. The run must not answer that twice.
5. **The gate is a floor, not a promise of quiet.** For a family whose
   `details` is a live measurement — the service family carries the
   check's own response time — every held poll differs and every held
   poll writes. Bounded anyway at ~**0.26 per run**, and it is an
   `UPDATE` to a row that already exists: `SNAG-AGENT-006`'s objection
   was about `INSERT`s accumulating and does not transfer.
6. **Nothing is announced, and that is not an oversight.** Session 39
   bans an in-place *severity* change because the tray fingerprints on
   `{severity}:{title}` and would keep a fingerprint it has already
   suppressed. A message change is invisible to that fingerprint, so it
   is safe in the direction that ban is about and, for the same reason,
   silent — no `alert.refreshed` event is queued, because an event
   nobody reads is `SNAG-CFG-001`'s shape. The corrected sentence reaches
   the tray on its next poll, and reaches a reader out loud only when
   `reminder_hours` re-speaks the row, which is the surface this exists
   for.

**It half-closes `SNAG-ESTATE-010`, and that entry's own check is what
said so.** That check enumerates three shapes a fix could take and
refuses to watch the severity column alone; the third — *the `holder`
blob arriving with the severity unmoved* — is this fix, so the blob now
reaches a standing row on every run. The clause came **out** of
`QuietenReading.reached` rather than the verdict being accepted: a
`reached` still reading the blob answers `mismatch` whatever happens to
the rung, which is a control this fix broke. The rung half stood at the
time, by Session 39's design, and **closed the same day** — see the
`may_quieten_in_place` section below, where that design turns out to
permit exactly this direction. The blob is still carried in the
*detail*, because "the correction reached the row and the rung stayed
put" was a stronger statement of the then-surviving claim than "nothing
happened".

**Four stand-ins modelled a database this code no longer talks to**, and
that was most of the work. `tests/test_unit_ports.py` answered the dedup
read with *titles*; `test_estate_judge_agent.py`'s `FakeAlert` had no
`message`; `test_alert_dedup.py`'s fake ignored the WHERE clause and
could not answer `.first()`; and `conftest.mock_session`'s bare
`AsyncMock` returns a coroutine from `.scalars()`, which fails in a way
no database produces and reads as a bug in the code under it.
`SNAG-ESTATE-010`'s probe located its standing row by
`message == PROBE_MESSAGE` — the value this fix rewrites — and keys on
the title now, which is the identity the entry it checks turns on.

**The rung moves too now, in one direction and only to the floor**
(Session 117, `SNAG-ESTATE-010`). The half `SNAG-AGENT-009` left is a
judgement that gets *quieter*: every dedup skips a title that is already
open before it looks at severity, so Session 57's
`TRANSIENT_HOLDER_SEVERITY` applied only to breaches raised afterwards
and the two rows it was written for sat at `warning` for the life of a
VS Code window. `core/escalation.may_quieten_in_place` is the rule and
`BaseAgent.refresh_alert`'s optional `severity=` asks it.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the running code rather than by argument:

1. **The rule was already here, stated once and obeyed by one family.**
   `log_aggregator._record_recurrence` has quietened a held row in place
   since Session 66, because **Session 39's ban is asymmetric and the
   reason it exists is what makes the reverse safe**: the ban is about an
   escalation needing to be *heard*, and the tray's suppressed
   `{severity}:{title}` fingerprint is exactly what a quietening wants.
   Four other deduplicating families needed the same answer and had no
   way to ask for it, which is how a copied rule drifts — `escalation`'s
   own opening argument for living in `core`.
2. **"Downward is safe" is too broad by one rung, and that is the whole
   narrowing.** `critical` → `warning` in place hands the tray a
   fingerprint it *will* speak, so the write arrives as a fresh, less
   urgent notification about a fault that has not improved — which is
   `step_for`'s refusal met from the other side. Only `QUIETEST_SEVERITY`
   is inaudible-or-asked-for, and it is **derived** from `SEVERITY_ORDER`
   rather than written as `"info"`: `max_priority_for` against
   `PRIORITY_MAP`'s rule, pinned by reading the source, because a literal
   and a derivation both *read* `info` and only provenance separates
   them.
3. **The tray's threshold is not consulted and could not have been.**
   The obvious gate is "quieter than `notify_min_severity`", which makes
   the daemon a second reader of a policy the tray owns — and `AppConfig`
   parses `notifications.tray:` (`TrayNotificationsConfig`, "the slice
   the *backend* needs") while that key lives in the top-level `tray:`
   section the tray parses for itself. A config leaf added for a rule
   that does not need it is `SNAG-CFG-001`'s shape.

   **That rule is about the daemon, and a test is not the daemon** —
   stated because reading it the wider way cost a sitting. Session 118
   declined to guard `SNAG-ESTATE-009`'s ceiling on the grounds that
   `TrayNotificationsConfig` parses `mute_services` alone, so a test
   *"can only read `notifications.desktop.reminder_hours`, the
   understudy's copy"*. `TrayNotificationsConfig` is the backend's
   **model**, not the file: `sysadmin_tray/config.py` parses
   `notifications.tray.reminder_hours` out of the same `config.yaml`,
   ships in this wheel, and is already imported across the seam by
   `tests/test_desktop_notifier.py`. Measured — `load_tray_config` at a
   copy with the tray leaf set to 6 returns `6.0` while the understudy
   still reads `24.0`. So the leaf is unreadable *to the daemon*, by
   design, and readable to a guard;
   `tests/test_config_defaults.py::TestTheLoudRungEndsBeforeItIsRestated`
   is that guard, and `TestTheTwoSpeakersAgreeInTheShippedFile` is the
   shipped-file half of the pin whose existing copy compares two
   defaults constructed with no file at all.
4. **It is asked *before* the text gate, which is where the fix would
   otherwise have shipped green and inert.** `refresh_alert`'s existing
   gate is "has the text moved", and the founding case is a breach the
   estate republishes word-for-word every hour with only the rung
   changed. One test catches the ordering, falsified against exactly that
   mutation.
5. **The entry asks for a reason the new severity is *durable*, and the
   answer is that the transition is one-directional rather than that the
   rung is stable.** A wobbling producer cannot flip-flop: down is in
   place and silent, up is refused and belongs to `step_for`'s
   resolve-and-re-raise. No row is resolved, none re-raised, and the
   count of standing faults does not move.
6. **Two of the three callers have empty populations and are wired
   anyway.** `_raise_judged`'s is empty **by construction** — every
   family there pairs a rung with a *title kind*, so a disk breach at the
   warning and critical thresholds is two titles rather than one row at
   two rungs — and the port family's because its rung is a constant, now
   `PORT_ALERT_SEVERITY` rather than a literal in the raise and nothing
   at all in the held branch. The entry *is* what happens when a family
   gains a quieter rung and its held branch was never told what rung it
   judged.

**It reaches the second speaker, which nothing had noticed.** The tray is
fixed for free — the old pair leaves the poll and the new one is dropped
below `notify_min_severity` — but `monitor/desktop.py` speaks from
`_SpokenFault.severity`, the rung it *announced*, and `_still_open` asked
only which titles were open. So the understudy would have gone on
restating at `warning` a fault the judge had decided is `info`: the
founding entry surviving inside the fix for it, in the one component that
exists for the case where the tray is down. That read returns
`{title: severity}` now and the sweep takes the row's rung, **loudest
wins** for the beat in which an escalation has two rows open — and the
sync is unconditional rather than direction-tested, because an escalation
has already replaced the whole entry through `on_alert_raised` and reads
back the same value.

The check retired with the entry and the drive is re-homed as
`tests/test_quietened_judgement_live.py` (`FROZEN_TABLES`' rule), where
it is **stronger than the check**: that check asserted a *disjunction* on
purpose, since any of three shapes would have been a fix, and now that
the shape is known a resolve-and-re-raise would satisfy it while
rebuilding `monitor/collation.py`'s flip-flop. It asks which shape — the
rung moved in place, one row, still open, nothing raised and nothing
resolved — and the resolve-and-re-raise mutation turns three of its four
tests red where the check would have said `mismatch` and called it fixed.

**One falsification passed against deliberately broken code**, which is
the part worth carrying: the "loudest of two open rows wins" test yielded
its rows loud-*last*, so a last-one-wins implementation with no
`_loudest` call in it answered correctly by accident. The query has no
`ORDER BY` — which is the whole reason `_loudest` is there — so it drives
both orderings. Three stand-ins again modelled a database this code no
longer talks to: `FakeAlert` with no `severity` (the column is `NOT NULL`
behind `chk_alert_severity`), `_FakeSession` answering the open check
with titles alone, and a fail-closed test breaking one reader out of two.

Retention needs **both halves**: a row in the `retention_config` table and
an entry in `TABLE_TIMESTAMP_MAP`. `run_retention` iterates config rows and
looks each up in the map, so a table with one half is silently never purged
— `project_reviews` and `disk_reviews` had neither, `unit_audits` had only
the map. Review tables get **365 days**, not the 30 that check data gets: a
weekly narrative kept for 30 days is four rows, too few to see a trend.
`KEEP_LATEST_PER` protects the newest row per entity (`"true"` means "the
whole table is one entity"), because a purge that emptied a review table
would make its route 404 — which reads as "never generated" rather than
"none lately".

**The two halves fail in opposite directions, which is what decided how
migration 014 dropped the three frozen tables.** A `retention_config`
row the map cannot resolve is **silent** — `run_retention` iterates
config rows and looks each up, so a miss is skipped with no log line and
nothing is purged. A map entry for a table that no longer exists is
**loud**: its `DELETE` raises every night, contained to that table by its
savepoint. Both halves therefore move with the migration, and only the
silent one needed a new guard — `test_purge_statements_parse` already
refuses a map entry PostgreSQL cannot plan, and more strongly than an
existence check, so the existence check written beside it was measured
against the stronger guard and deleted rather than shipped as a second
statement of one fact. Nothing in the suite had ever read
`retention_config` itself.

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
4. **`summary` is deterministic.** The weekly disk review is LLM-narrated
   and pays for it with a figure-free prompt and a markdown stripper; a
   summary made only of numbers gains nothing from that and would take the
   06:00 path down with llama-server.

The briefing's **project half is gone** (2026-08-13, ADR-0005). "Project
Health", "Pick This Up" and "Weekly Project Review" come from the estate's
own producer (`GET :8400/api/estate/briefing`), which Alfred pulls
separately by its ADR-0070; `briefing/preview` keeps the machine sections
— Infrastructure, Overnight Logs, Filesystem, Weekly Disk Review — **and
the alert digest**, so the alerting path never routes through the estate.
`SNAG-BRIEF-001` (the two project sections disagreeing inside one payload,
26 rows against 5) and `SNAG-BRIEF-002` (a next action cut mid-word with
no marker) were both fixed here before the move and are the estate's to
keep fixed. `truncate_at_word`, which always marks the cut, went with them
to `estate.text`; `NEXT_ACTION_CHARS` still governs the alert messages
this service writes.

**Configuration is re-read on demand, and the honest half is what it
says it could not do** (Session 49, `SNAG-UNITS-005`). `sysadmin/reload.py`
re-reads config.yaml and services.yaml on `SIGHUP` or
`POST /api/sysadmin/reload`. It sits **beside `main.py`** rather than in
`core/`: it composes `core.config` with `monitor.services`, and
`tests/test_import_boundary.py` forbids `core` from importing a domain —
the rule that makes every other boundary real. `metadata.py` had already
settled that placement in writing (*"composition roots… no domain imports
them"*), and that test now enforces it for all three.

The blocker was privilege, not design. `sysadmin.service` is a **system
unit running `User=gaddi`**, so the owner may signal it without `sudo`
(verified with `kill -0`, which probes permission without delivering).
`systemctl reload` would additionally need an `ExecReload=` line, and
*that* edit needs `sudo` — so the raw signal is the half that removes the
blocker. Note the trap: Python's default `SIGHUP` action **terminates**,
so a HUP sent to a daemon running code that predates this module is a
restart wearing a reload's name.

Four rules, three of them the opposite of the obvious implementation:

1. **Both files are validated before either is installed.** `parse_config`
   and `load_services` were split out of their loaders so the failure lands
   before the swap. A reload that half-succeeds *across files* leaves the
   process running a combination nobody wrote — strictly worse than the
   restart it replaces, because the operator's model is "the files on disk
   are what is running" and a partial install breaks it silently. Verified
   live: a broken services.yaml beside a valid config.yaml installs
   **neither**.
2. **Fields a reload cannot deliver are applied-and-named, not refused.**
   Nearly everything an agent reads is already re-read per run — every
   `_execute` calls `get_config()` at its top, a consequence of
   SNAG-AGENT-003 forbidding agents a startup hook, which bought per-run
   configuration for free. What is read *once* is small and enumerable
   (`RESTART_ONLY`): since Session 50, **two prefixes** — `service` and
   `database`, covering the socket, the logging setup and the engine.
   Refusing the whole reload when one of those moves would
   block a threshold fix on an unrelated edit in the same file — and the
   operator restarts anyway, so the refusal delivers nothing the restart
   did not. Half-success is only dangerous when it is **silent**; this
   names the leaves, not the prefixes, in the body and in a `WARNING` log
   line (the only report the SIGHUP path has).
3. **The registry is rebuilt from the *new* config's `projects_root`.**
   Validating against the old root checks project ids against a directory
   the file being installed no longer names — a check that passes for the
   wrong reason, which is the failure keying services on ids exists to
   remove.
4. **Per-service in-memory state is pruned, never reset.** Clearing
   `_degraded_counts` would re-arm the three-poll streak that gates an
   alert, at the moment an operator is most likely to be reloading
   *because* something is failing. What must go is the other direction: a
   name removed and later re-added would resume a streak measured against
   a different declaration. The log aggregator's known set is **both
   files** — pruning on services.yaml alone would discard cursors
   config.yaml declares, and a dropped cursor is not a clean slate but a
   fallback to `_resume_floor()`, the per-restart duplication the cursor
   exists to remove.

`RESTART_ONLY` is hand-written, so **a test requires every config path
read at startup to be classified** — restart-only, listed in
`LIVE_AT_STARTUP` with the reason it is read again later (`api.auth_token`
per request; `projects_root` by the reload itself), or declared by a
`JobSpec`. A hand-maintained classification nothing checks is the
SNAG-CFG-001 shape, and this one decides what an operator is told about
their own edit.

Verified live rather than only against fixtures, on the instance that
motivated it: with Session 48's three new entries removed to stand in for
the running daemon, a reload of the real file reports them as `added`,
installs all three, and reports `requires_restart: []` — so the restart
owed since 2026-08-15 would not have been owed.

**The scheduler is re-timed too, and the third classification is the only
one that is derived** (Session 50, `SNAG-RELOAD-001`). Session 49 shipped
the reload without it, so an installed `AppConfig` read 999 while the job
went on firing every 300 s and `requires_restart` named it **once** — the
warning-fires-once shape Session 39 spent itself removing, and a cost the
reload *introduced*, since before it existed the config object and the
scheduler were built from one read and could never disagree.

`sysadmin/core/jobs.py` owns the plan: `plan_jobs(config)` maps an
`AppConfig` to the nine jobs it asks for and `apply_jobs` reconciles a
scheduler with it. It is `core` rather than a fourth composition root
because it imports no domain and knows no agent — `main.py` hands in
`JOB_TARGETS`, so that file owns *what* runs and this one owns *when*, and
`tests/test_jobs.py` asserts the two sets match exactly. The lifespan and
the reload call the same function, so the schedule at startup and the
schedule after a reload cannot be produced differently.

Five rules, three of them the opposite of the obvious implementation:

1. **A job whose trigger has not changed is not touched.**
   `reschedule_job` recomputes the next fire from *now*, so re-applying
   every job on every reload postpones every job by a full interval — a
   daily file organiser on a box reloaded daily never runs, which is
   `agent_first_run_delay_seconds`'s failure with a reload standing in
   for a restart. The comparison is against the **live** trigger, never a
   remembered plan: a remembered plan is a second statement of what the
   scheduler is doing, and two statements that can disagree is the defect
   being closed.
2. **A job being added gets the first-run delay; a job being re-timed does
   not.** Added means this process has never scheduled it — a cold start,
   or an agent just re-enabled — and `IntervalTrigger` alone puts the
   first fire at `now + interval`. Re-timed means it already has a next
   fire, and bringing that forward turns an unrelated threshold edit into
   a 118-second filesystem scan nobody asked for.
3. **The plan is total: a disabled job is emitted disabled, never
   omitted**, because only a plan that still names it can *remove* it.
   The other side is bounded by **only planned ids are removed** — a job
   this module did not schedule belongs to whoever added it, the estate
   judge's sweep-scoping rule.
4. **`JOB_CONFIG_PATHS` is derived from the plan**, and each `JobSpec`'s
   declared `config_paths` must equal what `plan_jobs` actually reads
   (`tests/test_reload.py`). Without a syncer the reload falls back to
   reporting those leaves as restart-only, which is Session 49's exact
   behaviour and must not fall behind the jobs it describes.
5. **`jobs_synced` says which of the two happened.** `jobs_retimed: []`
   is "nothing needed re-timing" when it is true and "the scheduler was
   never looked at" when it is false — `ports_checked`'s rule, one domain
   over.

Verified live against the real `config.yaml` and a real
`BackgroundScheduler`, in-process: 999 s became `interval[0:16:39]`,
`retention_purge` moved 03:00 → 04:00, a disabled `estate_judge` had its
job removed and re-enabling added it back with the first-run delay, and
`requires_restart` came back `[]` where Session 49 reported three leaves.

Adding a **new agent** touches four places, not one: the Python wiring in
`main.py`, a config class in `config.py`, the `chk_alert_agent` CHECK
constraint on `sysadmin.alerts` (a migration — the database rejects an
unknown agent name), and `self_monitor.AGENT_NAMES` (without which the
agent runs unwatched). `tests/test_units_api.py` pins the last two
together. If it is **scheduled**, that is two more: a `JobSpec` in
`core/jobs.py` and an entry in `main.py`'s `JOB_TARGETS` — planned and
unwired is a `KeyError` at startup, wired and unplanned never runs and
looks exactly like one that does.


Tray-only presentation (IconState, ICON_COLOURS, compute_icon_state) stays in
`sysadmin_tray/models.py`.

---

## Detailed Documentation

## Cross-repo friction is filed, not absorbed — a pointer

**The rule is estate-manager's and its canonical body is
`~/projects/estate-manager/docs/conventions/session-brief.md`**, section
"Cross-repo friction is filed, not absorbed" (owner's ruling 2026-08-25,
estate ADR-0041 and ADR-0042). It is deliberately **not** in the global
`~/.claude/CLAUDE.md`, whose estate section is a pointer and says in
writing not to re-expand it — so this is a pointer too, and the headline
is all that belongs here.

Headline: when a sitting hits friction crossing a repository boundary —
another repository's state it could not read, a decision it could not
find, a filing that collided, work it duplicated — it files a message
rather than working around it:

    POST http://127.0.0.1:8400/api/estate/messages
    {"sender": "sysadmin_assistant", "receiver": "<owner of the thing>",
     "summary": "one sentence", "detail": "optional"}

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
  first — and the `agents.project_organiser` config block that is still
  parsed and mostly unread. Estate side: their ADR-0004 (the decision) and ADR-0008
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

Guides: only **api_auth.md** (bearer-token auth setup) still lives in
this repository's `docs/guides/`. The four cross-repo guides —
`estate-map.md`, `monitorable-project.md` (which holds the port
registry), `alfred-briefing-integration.md`, `alfred-projects-page.md` —
**moved to `~/projects/estate-manager/docs/guides/` on 2026-08-11**;
pointers stand at the old paths. `monitorable-project.md` is still
enforced mechanically by this repository's Session 26 service-discovery
agent (`GET /api/units/actions`) — the document moved, the enforcement
did not.
