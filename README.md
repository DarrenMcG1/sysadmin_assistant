# sysadmin-service

Infrastructure monitoring and housekeeping service for a single Arch/KDE
workstation, with a KDE system-tray client. It watches systemd units, disk
and RAM, the GPU, the journal, and the projects under `~/projects`, stores
what it sees in PostgreSQL, raises alerts, and recommends (and can perform)
tidy-up actions.

Version 0.1.0. UK English throughout the codebase and docs.

---

## What it does

Five agents run on an APScheduler timetable inside the FastAPI process,
one per domain package:

| Agent | Responsibility |
|-------|----------------|
| `SysAdminAgent` | systemd unit health, CPU/RAM/disk/GPU snapshots, alerting |
| `ProjectOrganiserAgent` | per-project health scores, git branch hygiene, TODO/FIXME counts |
| `FileOrganiserAgent` | filesystem audit — duplicates, misplaced files, large files, stale caches |
| `LogAggregatorAgent` | journal ingestion and error summarisation |

Supporting modules across those packages and `sysadmin/core/` add anomaly detection, disk-usage
forecasting, a recommendations engine for both the project portfolio and the
disk, a morning briefing, an SSE event bus, retention pruning, do-not-disturb
handling, and an LLM client used for weekly narrated reviews.

The tray client (`sysadmin_tray/`) is a PyQt6 status icon plus a native
dashboard with Overview, Services, Projects, Files and Logs tabs. It talks to
the backend over HTTP only, through the shared contract models.

## Stack

- Python ≥ 3.12, FastAPI + uvicorn
- PostgreSQL (`projects` database, `sysadmin` schema) via SQLAlchemy async +
  asyncpg; Alembic migrations use psycopg2
- APScheduler, psutil, GitPython, httpx
- PyQt6 for the tray (optional extra: `.[tray]`)
- llama.cpp (`llama-server`) for the optional LLM narration, reached over HTTP

Managed by `uv`; the lockfile is `uv.lock`.

## API

55 routes across eight routers, all mounted on the backend at port **8500**:

| Prefix | Router |
|--------|--------|
| `/health` | `sysadmin/core/health.py` |
| `/api/sysadmin/*` | services, resources, alerts, DND, SSE events, self-monitor |
| `/api/logs/*` | recent entries and stats |
| `/api/projects/*` | overview, per-project detail, recommendations, reviews |
| `/api/files/*` | audit results, trends, recommendations, clean/organise actions |
| `/api/*` | briefing/summary for external consumers |

Response shapes are pinned in `sysadmin/core/contracts.py` (pydantic only) and
re-exported by the tray, so backend and client cannot drift silently. The
mapping of endpoint → contract model is tabulated in `CLAUDE.md`.

Mutating endpoints require a bearer token; GETs are open. The three
`/api/files/*` action endpoints and the branch-prune endpoint are **dry runs
unless the request body sets `confirm: true`**.

## Configuration

Everything lives in `config.yaml` (validated by Pydantic models in
`sysadmin/core/config.py`), with per-service topology in `services.yaml` — keyed by project id, no paths in it — and project identity in a `.project.yaml` manifest inside each repository.
**No environment variables are read and there is no `.env` file** — including
the database URL, which sits under `database:` in `config.yaml`.

## Running it

```bash
./scripts/install.sh      # uv venv, editable install, alembic upgrade head
./scripts/run-dev.sh      # uvicorn on 127.0.0.1:8500 with --reload
```

Docs at <http://127.0.0.1:8500/docs> once running.

Production runs as a systemd unit — `systemd/sysadmin.service`, installed by
`./scripts/setup-systemd.sh`. The tray autostarts via
`systemd/sysadmin-tray.desktop`; the console script is `sysadmin-tray`.

## Tests and checks

```bash
uv run pytest            # backend + tray suites
uv run ruff check .      # lint (CI runs this)
uv run mypy sysadmin     # backend types only
./scripts/lint_check.sh  # combined pre-commit gate
./scripts/smoke_test.sh  # against a running instance
```

Tests build the real application via `create_app` with a stubbed lifespan, so
there is no synthetic test app to drift. `tests/test_schema_drift.py` guards
the database schema and `tests/test_contracts.py` guards the wire shapes.

## Repository layout

```
sysadmin/            backend package (agents, routers, services, models, utils)
sysadmin_tray/       PyQt6 tray + dashboard
alembic/             migrations (version_table_schema="sysadmin")
tests/               pytest suites, incl. tests/test_tray/
scripts/             install, run, lint, systemd, session pre/postflight
systemd/             unit and desktop files
docs/                ARCHITECTURE.md, guides/, roadmap/, sessions/, insights/
config.yaml          all runtime settings
projects.yaml        managed projects the organiser scans
home_audit.py        legacy standalone audit script, predates the service
SYSADMIN-SERVICE-SPEC.md   original specification (port 8100 there; 8500 in practice)
```

## State

Actively developed and running. The backend, API, database, agents, GPU
monitoring and tray dashboard are all in place; the Personal Assistant
integration is dormant (code and tests retained, disabled in config, since PA
was retired in favour of Alfred).

Current priorities live in `docs/roadmap/STATUS.md`; open sessions in
`docs/roadmap/tasks.md`; known bugs in `docs/roadmap/snag_list.md`. Working
conventions for Claude Code sessions are in `CLAUDE.md`.
