# sysadmin-service

**A monitoring and housekeeping service for one Linux workstation — and a
written record of how every rule in it was arrived at.**

On a machine with an operations team, a service that dies gets noticed. On a
single-user workstation running thirty-odd background services for a dozen
personal projects, it does not: nothing pages anyone, and the interesting
failures are the quiet ones. A systemd unit that was never wired up looks
exactly like one that is working. A migration written and committed but never
applied lets the daemon serve against a schema it was not built for. A fault
that recurs every night announces itself once and is then deduplicated into
silence. This service exists to make that class of failure loud — it watches
systemd units, disk, RAM, the GPU and the journal, stores what it sees in
PostgreSQL, raises alerts a KDE tray client surfaces, and recommends (and can
carry out) tidy-up actions.

It is built for exactly one box and does not try to be Prometheus, so the code
is unlikely to be useful to you directly. **The written record might be.** The
roadmap alone runs to about 24,500 lines — of roughly 39,800 lines of Markdown
in the repository altogether, measured 2026-09-10 — and it exists because most
repositories keep their reasoning in someone's head and ship only the result.
This one keeps the reasoning: what each change was measured against, which
options were rejected and why, which guards were deliberately falsified, which
of them passed against broken code anyway, and — repeatedly — which of the
previous session's confident conclusions turned out to be wrong. It is published
as-is for that reason
([ADR-0010](docs/adr/0010-publication-was-one-option-wearing-three.md)).

If you want to see what that looks like before reading any Python, open
[`docs/roadmap/snag_list.md`](docs/roadmap/snag_list.md) at any entry and read
the bullets underneath it.

---

## Contents

| | |
|---|---|
| [What it does](#what-it-does) | the five agents and the tray |
| [How it is built](#how-it-is-built) | stack, API, configuration |
| [Running it](#running-it) | install, dev server, systemd |
| [Tests and checks](#tests-and-checks) | what the suite guarantees |
| [Reading the record](#reading-the-record) | the roadmap, ADRs and where to start |
| [Repository layout](#repository-layout) | |
| [Scope and status](#scope-and-status) | what this is not |

---

## What it does

Five agents run on an APScheduler timetable inside the FastAPI process, one per
domain package, each writing to PostgreSQL and raising alerts through a shared
base class:

| Agent | Every | Responsibility |
|-------|-------|----------------|
| `SysAdminAgent` | 5 min | service health (HTTP/TCP/systemd), CPU, RAM, disk, swap, load, GPU; threshold and anomaly alerting |
| `LogAggregatorAgent` | 60 s | journal ingestion, fault signatures, trend and incident correlation |
| `EstateJudgeAgent` | 1 h | reads the estate manager's published surfaces and judges them |
| `ServiceDiscoveryAgent` | 6 h | finds systemd units nothing is monitoring, and orphans that will restart-loop |
| `FileOrganiserAgent` | 24 h | filesystem audit — duplicates, misplaced files, large files, stale caches |

Scheduled jobs beside them cover a morning briefing, retention pruning, a
nightly reliability snapshot, and three weekly LLM-narrated reviews (health,
disk, logs). Supporting modules add disk-usage forecasting, recommendation
endpoints for each domain, an SSE event bus, and do-not-disturb handling.

**Project state is not here.** The scanner, health scores, roadmap parsing and
project board moved to a sibling repository, `estate-manager`, on 2026-08-13 —
see [ADR-0005](docs/adr/0005-project-state-leaves.md). What this service kept is
the judging half: the estate publishes and never acts, this repository judges
and never scans, and neither judges itself.

The tray client (`sysadmin_tray/`) is a PyQt6 status icon plus a native
dashboard with Overview, Services, Projects, Files and Logs tabs. It talks to
the backend over HTTP only, through shared contract models, and owns the
desktop notification policy — deduplication, flap cooldown, coalescing and
digests. A backend-side notifier stands in when the tray is not running.

## How it is built

- Python ≥ 3.12, FastAPI + uvicorn, backend on port **8500**
- PostgreSQL (`projects` database, `sysadmin` schema, 13 tables) via SQLAlchemy
  async + asyncpg; Alembic migrations use psycopg2
- APScheduler, psutil, GitPython, httpx
- PyQt6 for the tray (optional extra: `.[tray]`)
- llama.cpp (`llama-server`) for the optional narrated reviews, over HTTP

Managed by `uv`; the lockfile is `uv.lock`. Note that `dev` and `tray` are
optional dependencies rather than dependency groups, so a bare `uv sync` prunes
them — use `uv sync --all-extras`.

### API

51 application routes across eight routers (55 including the four FastAPI
generates for its own documentation):

| Prefix | Routes | What is there |
|--------|--------|---------------|
| `/health` | 1 | liveness, unauthenticated |
| `/api/sysadmin/*` | 17 | services, resources, alerts, DND, SSE events, self-monitor, health review |
| `/api/files/*` | 15 | audit results, trends, recommendations, clean/organise actions |
| `/api/logs/*` | 10 | recent entries, stats, trends, ranked advice |
| `/api/services/*` | 3 | reliability scores and ranked advice (GET-only, enforced by a test) |
| `/api/units/*` | 2 | the systemd sweep as measured, and as ranked advice (GET-only) |
| `/api/projects/*` | 1 | `managed` only — live service health wearing a project-shaped path |
| `/api/summary` | 1 | briefing envelope for external consumers |

Response shapes are pinned in `sysadmin/core/contracts.py` (pydantic only) and
re-exported by the tray, so backend and client cannot drift silently. The full
endpoint → contract mapping is tabulated in [`CLAUDE.md`](CLAUDE.md).

Mutating endpoints require a bearer token; GETs are open. The `/api/files/*`
action endpoints are **dry runs unless the request body sets `confirm: true`**,
and operate under root confinement, no symlink following, no overwriting, and
trash rather than delete.

### Configuration

Everything lives in `config.yaml` (validated by Pydantic models in
`sysadmin/core/config.py`), with per-service topology in `services.yaml` — 32
declared services, keyed by project id, no paths in it — and project identity in
a `.project.yaml` manifest inside each repository.

**No environment variables are read and there is no `.env` file**, including the
database URL, which sits under `database:` in `config.yaml`. Both files are
re-read on `SIGHUP` or `POST /api/sysadmin/reload`, which also re-times the
scheduler; the handful of settings that genuinely need a restart are named in
the reload's response rather than silently ignored.

## Running it

```bash
./scripts/install.sh      # uv venv, editable install, alembic upgrade head
./scripts/run-dev.sh      # uvicorn on 127.0.0.1:8500 with --reload
```

Interactive API docs at <http://127.0.0.1:8500/docs> once running.

Production runs as a systemd unit — `systemd/sysadmin.service`, installed by
`./scripts/setup-systemd.sh`, with `systemd/sysadmin-failed.service` announcing
a terminal restart loop. The tray autostarts via `systemd/sysadmin-tray.desktop`;
the console script is `sysadmin-tray`.

The daemon **refuses to start** if the database schema does not match the
migration head it was packaged with. That is deliberate: serving against the
wrong schema is worse than not serving, and the alternative once cost this box a
39-hour monitoring blackout that nothing reported. `./scripts/check-migrations.sh`
answers the same question before you commit.

## Tests and checks

```bash
uv sync --all-extras     # dev and tray extras; a bare `uv sync` prunes them
uv run pytest            # backend + tray suites — 3,900 tests
uv run ruff check .      # lint (CI runs this)
uv run mypy sysadmin     # backend types only
./scripts/lint_check.sh  # combined pre-commit gate
./scripts/smoke_test.sh  # against a running instance
```

There is more test code than source: **68,536 lines of tests** against 51,427 of
backend and 6,150 of tray. Tests build the real application via `create_app`
with a stubbed lifespan, so there is no synthetic test app to drift.

Several suites guard things a normal test cannot reach — `test_schema_drift.py`
compares the live schema against the models using production Alembic
configuration, `test_contracts.py` guards the wire shapes, and a set of AST
sweeps refuse patterns rather than assert behaviour (a second hand-written copy
of a rule, a health status compared to `"ok"` by hand, an `IS false` predicate
that cannot reach a partial index). A recurring practice in this repository is
to **falsify a new guard** — break the code deliberately and confirm the guard
goes red — because guards that pass against broken code have been found here
repeatedly, and the roadmap records each one.

## Reading the record

This is the part that is unusual, and it is meant to be read.

| Document | What it is |
|----------|-----------|
| [`docs/README.md`](docs/README.md) | index of everything below, with suggested entry points |
| [`docs/adr/`](docs/adr/) | 10 architecture decision records — the decisions and, more usefully, the options measured and rejected |
| [`docs/roadmap/snag_list.md`](docs/roadmap/snag_list.md) | known defects, each with what was measured, what the fix cost, and what the entry itself got wrong |
| [`docs/roadmap/STATUS.md`](docs/roadmap/STATUS.md) | current priorities and recently completed work |
| [`docs/roadmap/tasks.md`](docs/roadmap/tasks.md) | session-by-session working record |
| [`docs/roadmap/ideas.md`](docs/roadmap/ideas.md) | unbuilt features, no commitment implied |
| [`CLAUDE.md`](CLAUDE.md) | working conventions, and the densest single account of why the code is shaped as it is |

A few conventions run through all of it, and knowing them makes the entries
readable:

- **A claim is re-measured before it is repeated.** Snag entries are corrected
  in place when the box refutes them, including entries this repository wrote
  itself; several record that reading the code confirmed a claim while running
  it refuted the claim's *ranking*.
- **Not-knowing is never success.** Where a check cannot answer, it says so
  rather than returning the healthy value — zero-because-blind must not be
  served as zero-because-clean.
- **Whether a guard fails open or closed is argued, not assumed.** The schema
  guard refuses to boot; the collation check fails open. The reasoning for each
  direction is written beside it.
- **A count that cannot name what it swallowed is not news.** Roll-ups name
  their members; alert identity is the fault, not the source.

## Repository layout

```
sysadmin/            backend package
  core/              config, agent base, scheduler, contracts, escalation, jobs
  monitor/           health checks, resources, logs, alerts, reliability, reviews
  files/             filesystem audit, recommendations, actions
  units/             systemd unit sweep, port attribution
  estate/            reads and judges the estate manager's surfaces
  briefing/          morning briefing envelope
sysadmin_tray/       PyQt6 tray icon + dashboard
alembic/             19 migrations (version_table_schema="sysadmin")
tests/               pytest suites, incl. tests/test_tray/
scripts/             install, run, lint, systemd, session pre/postflight, checks
systemd/             unit and desktop files
docs/                adr/, roadmap/, guides/, insights/, ARCHITECTURE.md
config.yaml          runtime settings
services.yaml        per-service monitoring topology
home_audit.py        standalone audit script that predates the service
```

## Scope and status

Actively developed, and running on the machine it was written for. Backend, API,
database, agents, GPU monitoring and tray dashboard are all in place.

**What this is not.** It is not a general-purpose monitoring system, it assumes
a single-user Arch/KDE workstation with PostgreSQL on it, and it is not packaged
for anyone else's box — ports, unit names and paths are this estate's. The
Personal Assistant integration is dormant (code and tests retained, disabled in
config, since PA was retired in favour of a sibling project). Version 0.1.0.
UK English throughout code and documentation.

Some conventions referenced here — the estate map, the monitorable-project
contract, the shared port registry — are owned by `estate-manager`, a sibling
repository that is not public. Where a document here points at one of those, the
pointer will not resolve for you; the reasoning quoted alongside it should still
stand on its own.
