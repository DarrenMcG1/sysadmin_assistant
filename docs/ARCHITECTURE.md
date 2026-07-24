# Architecture Overview

**Last rewritten**: 2026-07-24 (Session 14) — reflects the code as it exists now.

Infrastructure monitoring and housekeeping service for a single Linux workstation.
A FastAPI backend (port **8500**) runs four scheduled agents that watch services,
projects, files, and logs, persisting everything to PostgreSQL. A PyQt6 KDE tray
app polls the API and surfaces state via a tray icon, native dashboard, and D-Bus
notifications. The tray is the only UI: PersonalAssistant (PA), which consumed a
digest endpoint and received briefings/notifications, was retired on 2026-07-24
and its outbound integration is now dormant (see "PA integration" below).

---

## System Architecture

```
                            ┌─────────────────────────────────────────────┐
                            │        FastAPI backend  :8500               │
                            │        (sysadmin/main.py create_app)        │
 ┌──────────────┐  HTTP     │                                             │
 │ PyQt6 tray   │──────────▶│  Routers          Services                  │
 │ sysadmin_tray│  poll     │  ├ health         ├ scheduler (APScheduler) │
 │ ├ tray_icon  │           │  ├ sysadmin       ├ notifier ──────────┐    │
 │ ├ dashboard  │           │  ├ projects       ├ briefing (06:00) ──┤    │
 │ └ D-Bus      │           │  ├ files          ├ retention (03:00)  │    │
 │   notifs     │           │  ├ logs           ├ event_bus          │    │
 └──────┬───────┘           │  └ summary ───────├ dnd                │    │
        │ imports           │                   └ llm_client ───┐    │    │
        ▼                   │  Agents (BaseAgent)               │    │    │
 ┌──────────────┐           │  ├ SysAdminAgent                  │    │    │
 │ sysadmin/    │           │  ├ ProjectOrganiserAgent          │    │    │
 │ contracts.py │◀──────────│  ├ FileOrganiserAgent             │    │    │
 │ defaults.py  │ response_ │  └ LogAggregatorAgent             │    │    │
 │ (pydantic/   │ model=    └──────────┬───────────────────┬────┼────┼────┘
 │  stdlib only)│                      │ SQLAlchemy async   │    │    │
 └──────────────┘                      ▼                    │    ▼    ▼
                            ┌─────────────────────┐         │  ┌───────────────┐
                            │ PostgreSQL          │         │  │ PersonalAssist│
                            │ db: projects        │         │  │ :8000 (v2     │
                            │ schema: sysadmin    │         │  │ notify +      │
                            │ (Alembic-managed)   │         │  │ briefing)     │
                            └─────────────────────┘         │  └───────────────┘
                                                            ▼
                                                  ┌───────────────────┐
                                                  │ llama.cpp         │
                                                  │ llama-server :8081│
                                                  │ (OpenAI-compat)   │
                                                  └───────────────────┘
```

---

## Directory Structure

```
sysadmin_assistant/
├── config.yaml            # All runtime configuration (validated by sysadmin/config.py)
├── projects.yaml          # Managed projects — merged into agent configs at load
├── sysadmin/              # Backend package (PyPI name: sysadmin-service)
│   ├── main.py            # create_app() factory + lifespan + module-level app
│   ├── config.py          # Pydantic models for config.yaml/projects.yaml, singleton loader
│   ├── contracts.py       # Shared wire contracts (pydantic-only) — used by tray
│   ├── defaults.py        # Canonical API host/port defaults (stdlib-only) — used by tray
│   ├── auth.py            # require_auth bearer-token dependency
│   ├── database.py        # Async engine/session + NullPool scheduler sessions
│   ├── logging_setup.py   # Structured JSON (or text) logging
│   ├── middleware.py      # Request access-log middleware (excludes /health)
│   ├── agents/            # BaseAgent + the four agents
│   ├── routers/           # health, sysadmin, projects, files, logs, summary
│   ├── services/          # scheduler, notifier, briefing, retention, event_bus, dnd, llm_client
│   ├── models/            # SQLAlchemy models (9 tables)
│   └── utils/             # git, gpu, journal, systemd helpers
├── sysadmin_tray/         # PyQt6 KDE tray app (console script: sysadmin-tray)
│   ├── app.py             # Orchestrator: QTimers + ApiClient + TrayIcon + Dashboard
│   ├── client.py          # httpx API client (bearer token, connection-lost handling)
│   ├── config.py          # TrayConfig — reads the same config.yaml
│   ├── models.py          # Re-exports sysadmin.contracts + icon-state logic
│   ├── tray_icon.py       # Tray icon, menu, alert fingerprint tracking
│   ├── notifications.py   # D-Bus (org.freedesktop.Notifications) notifier
│   ├── dashboard/         # Native dashboard window: overview/services/projects/logs tabs
│   └── widgets/           # service_grid, resource_gauge, alert_badge
├── alembic/               # Migrations (version table inside sysadmin schema)
├── tests/                 # ~360 tests: backend (real-app fixture) + tray (headless Qt)
├── scripts/               # preflight/postflight, lint_check, smoke_test, worktrees
├── systemd/               # Unit files for running as a user service
└── docs/                  # roadmap/ (STATUS, tasks, snags, ideas), guides/, sessions/
```

---

## Backend

### App factory & lifespan

`sysadmin/main.py` exposes `create_app(lifespan_ctx=None)` which builds the real
application: CORS middleware (origins from `service.cors_origins` in config.yaml),
`RequestLoggingMiddleware`, a JSON 500 exception handler, all six routers, and the
`/api/sysadmin/scan-all` trigger endpoint. Tests build this same app with a stub
lifespan; production uses the module-level `app = create_app()`.

The production lifespan: loads config → configures logging → verifies the DB →
starts services/agents → registers scheduler jobs (agent intervals from each
agent's config; briefing/retention cron times from `schedules:` in config.yaml,
defaults 06:00/03:00) → exposes shared instances on `app.state` → clean shutdown.

### Routers (6)

| Router | Prefix | Purpose |
|--------|--------|---------|
| health | `/health` | Liveness (status, service, version) |
| sysadmin | `/api/sysadmin` | Service status/actions, resources (+history), alerts (+ack), ports, GPU, DND |
| projects | `/api/projects` | Health overview/grades, stale, report, managed (projects.yaml + live health), per-project detail/todos/branches, scan |
| files | `/api/files` | Filesystem audit status, quick-wins, duplicates, trends (+reclaimable forecast with configurable milestones), stale-cache clean, scan |
| logs | `/api/logs` | Recent entries, stats, summaries |
| summary | `/api/summary` | Single-call digest (services, alerts, resources, GPU, DND, project scores) — built for PA, now unconsumed |

### Agents — template-method pattern

`agents/base.py` defines `BaseAgent`: the public `run()` template method opens a
scheduler DB session, records a row in `agent_runs` (status/duration/findings),
calls the subclass's abstract `_execute(session)`, and handles failures. It also
provides `raise_alert()` / `resolve_alerts()` writing to the `alerts` table.

| Agent | Schedule (config) | Work |
|-------|-------------------|------|
| SysAdminAgent | every 300 s | HTTP/TCP/systemd health checks (system + user units), resource snapshots, threshold alerts (disk/RAM/CPU/GPU), optional auto-restart |
| ProjectOrganiserAgent | every 6 h | Scans `~/projects`: health score, stale branches, TODO/FIXME counts, README/CLAUDE.md presence |
| FileOrganiserAgent | every 24 h | Home-directory audit: duplicates, stale downloads, large files, reclaimable space |
| LogAggregatorAgent | every 60 s | Polls journalctl (system + `--user`) and files; LLM summaries via llama.cpp |

### Scheduler — APScheduler bridge

`services/scheduler.py` wraps APScheduler 3.x `BackgroundScheduler` (thread pool).
Agents are async, so jobs run through an `asyncio.run()` bridge (`_run_async`),
giving each scheduled run its own event loop in the scheduler thread — which is
why scheduler DB sessions use `NullPool` (see `database.py`). Interval triggers
for agents, cron triggers for briefing/retention; job defaults: coalesce,
`max_instances=1`, 300 s misfire grace.

### Services

- **notifier** — httpx client POSTing alerts/briefings to PA's v2 notification
  endpoint, with retry/backoff and DND-aware suppression; PA unreachable is
  non-fatal. **Dormant** — `personal_assistant.enabled: false` short-circuits
  both send paths before any HTTP call.
- **briefing** — builds the structured morning-briefing payload (infrastructure,
  overnight logs, filesystem, projects). Still generated daily; the send is
  suppressed by the flag above.
- **retention** — daily purge of old rows per the `retention_config` table.
- **event_bus** — in-process async pub/sub (callback list; failures logged, not raised).
- **dnd** — Do Not Disturb manager: config schedule + runtime manual override;
  critical alerts can break through.
- **llm_client** — `LLMClient` speaking llama-server's OpenAI-compatible API
  (`POST /v1/chat/completions`, health via `GET /health`); returns `None`
  gracefully when the server is down.

### Database

PostgreSQL, database `projects`, dedicated **`sysadmin` schema** (isolated from
PA in the same database — including its own `alembic_version` via
`version_table_schema`). Async access with `postgresql+asyncpg` (search_path via
`server_settings`); Alembic migrations use the sync `psycopg2` URL. 9 tables:
`service_health`, `resource_snapshots`, `alerts`, `project_snapshots`,
`filesystem_audits`, `log_entries`, `log_summaries`, `agent_runs`,
`retention_config`. A schema drift guard test runs `alembic compare_metadata`
against the live DB.

### Auth, logging, observability

- **Bearer-token auth** (`auth.py`): `api.auth_token` in config.yaml; enforced by
  a `require_auth` dependency on all mutating POST endpoints (constant-time
  compare). Read-only GETs stay open so dashboards work tokenless. Empty token →
  auth disabled with a startup warning.
- **Structured logging** (`logging_setup.py`): JSON (python-json-logger) for the
  systemd journal or plain text for development, chosen by `service.log_format`.
  `middleware.py` adds per-request access logs, excluding `/health` (tray polls it).

---

## Shared modules (backend ↔ tray)

Two deliberately **dependency-light** modules (pydantic/stdlib only — no FastAPI
or SQLAlchemy) are imported by both sides:

- **`sysadmin/contracts.py`** — wire contracts for every tray-consumed endpoint.
  Backend routers set them as `response_model=`; the tray parses responses with
  `Model.from_dict()` (tolerant: `extra="ignore"`, defaulted fields; parse
  failure raises `ValidationError` → tray marks connection lost).
- **`sysadmin/defaults.py`** — canonical API host/port defaults
  (`DEFAULT_API_HOST`/`DEFAULT_API_PORT`/`default_api_url()`), used by the
  backend's `ServiceConfig` and the tray's `TrayConfig` fallback.

This is the project's contract-drift firewall: shapes and endpoints live in one
place, enforced server-side and consumed client-side.

---

## Tray app (sysadmin_tray)

PyQt6 KDE system-tray monitor, installed as the `sysadmin-tray` console script.

- **app.py** wires QTimers (status/resource/alert polls at configurable
  intervals) to `ApiClient` and fans results out to the tray icon and dashboard.
- **client.py** — httpx client sending `Authorization: Bearer` from the shared
  config.yaml; catches network *and* parse errors to flag connection lost.
- **tray_icon.py** — icon state (ok/warning/critical/disconnected) computed from
  service + alert data; context menu with service actions, DND toggle, scan-all.
- **dashboard/** — native window with Overview, Services, Projects, and Logs
  tabs (widgets: service grid, resource gauges, alert badge).
- **notifications.py** — D-Bus `org.freedesktop.Notifications` desktop
  notifications with severity filtering and action buttons.
- **config.py** — reads the same `config.yaml` (tray section + `service`
  host/port fallback + `api.auth_token`); `--api-url` CLI flag overrides.

---

## PA integration (dormant since 2026-07-24)

PersonalAssistant was retired and replaced by **Alfred**, which exposes no inbox —
nothing in its API accepts notifications, briefings or digests. `personal_assistant.enabled`
is therefore `false` and the outbound paths below make no HTTP call. The code and
its tests are kept deliberately so the integration can be repointed by editing the
url/endpoints and flipping one flag.

- **`GET /api/summary`** — single-call digest, still served; nothing consumes it today.
- **Morning briefing** — was POSTed daily to PA's `briefing_endpoint` (config).
  The payload is still generated on schedule; only the send is suppressed.
- **Notifications** — critical alerts were forwarded to PA's v2 notification endpoint
  (`notify_endpoint`), severity-filtered and DND-aware.
- PA's frontend rendered the sysadmin web dashboard from the read-only GET endpoints
  (hence the open GETs + CORS origins). That UI died with PA; the PyQt6 tray is now
  the only one. Alfred's Nuxt frontend on :3100 is the candidate host for a rebuild —
  its origin is already in `service.cors_origins`. See ideas.md.

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Config | Single `config.yaml` + Pydantic validation, no env vars | One file for backend + tray; typed defaults; committed placeholder token |
| Schema isolation | `sysadmin` schema in the shared `projects` DB | Coexists with PA without collisions (own alembic_version) |
| Scheduler | APScheduler `BackgroundScheduler` + `asyncio.run()` bridge | Async agents on a sync scheduler; NullPool sessions per-run |
| Agent framework | Template method (`run()` → `_execute()`) | Uniform run recording, timing, and error handling in one place |
| Contracts | Shared pydantic module, `response_model=` + tray import | Kills silent drift (root cause of SNAG-TRAY-005) |
| Auth | Shared bearer token on mutating endpoints only | localhost binding doesn't stop CSRF-style POSTs; GETs stay open for dashboards |
| LLM | llama.cpp llama-server, OpenAI-compatible API | Local inference; graceful `None` degradation when down |
| Testing | Real-app fixture via `create_app()` | Tests exercise production routers/middleware/handlers, not a synthetic app |

---

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend | FastAPI + uvicorn | Port 8500, app factory pattern |
| Database | PostgreSQL (asyncpg / psycopg2) | SQLAlchemy 2 async + Alembic |
| Scheduling | APScheduler 3.x | BackgroundScheduler + asyncio bridge |
| Desktop | PyQt6 + D-Bus | KDE tray, native dashboard |
| LLM | llama.cpp (llama-server :8081) | OpenAI-compatible API, single model |
| Tooling | uv, ruff, mypy, pytest | CI: GitHub Actions (headless Qt) |
