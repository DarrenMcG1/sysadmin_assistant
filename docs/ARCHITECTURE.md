# Architecture Overview

**Last rewritten**: 2026-07-24 (Session 14). **Membership re-measured
against the running box 2026-09-10** (Session 208, closing
`SNAG-DOCS-011`): the packages, the agents, the routes, the tables and
the tray's tabs below are what is there, not what was there before the
project domain left on 2026-08-13. The prose still describes the system's
*shape* rather than every module in it, and is thin in places; it should
no longer name anything absent or omit anything present.

Infrastructure monitoring and housekeeping service for a single Linux workstation.
A FastAPI backend (port **8500**) runs five scheduled agents that watch services,
files, logs, installed systemd units and the wider estate, persisting everything to
PostgreSQL. A PyQt6 KDE tray app polls the API and surfaces state via a tray icon,
native dashboard, and D-Bus notifications. The tray is the only UI: PersonalAssistant
(PA), which consumed a digest endpoint and received briefings/notifications, was
retired on 2026-07-24 and its outbound integration is now dormant (see "PA
integration" below).

**This service monitors and alerts; it does not scan repositories or score
them.** Project state — the scanner, the board, the health score, the
roadmap parse — moved to `estate-manager` on port 8400 on 2026-08-13
under [ADR-0005](adr/0005-project-state-leaves.md). What this repository
gained in the same swap is the *judging* half: the estate publishes and
never acts, and `EstateJudgeAgent` here turns its published surfaces into
alert rows. Neither side judges itself.

---

## System Architecture

```
                            ┌────────────────────────────────────────────┐
                            │        FastAPI backend  :8500              │
                            │        (sysadmin/main.py create_app)       │
 ┌──────────────┐  HTTP     │                                            │
 │ PyQt6 tray   │──────────▶│  Packages         core/                    │
 │ sysadmin_tray│  poll     │  ├ monitor        ├ scheduler (APScheduler)│
 │ ├ tray_icon  │           │  ├ estate         ├ agent (BaseAgent)      │
 │ ├ dashboard  │           │  ├ files          ├ jobs (12 scheduled)    │
 │ └ D-Bus      │           │  ├ units          ├ event_bus, retention   │
 │   notifs     │           │  └ briefing       ├ llm_client             │
 └──────┬───────┘           │                                            │
        │ imports           │  Agents (core.agent.BaseAgent)             │
        ▼                   │  ├ SysAdminAgent          every 300 s      │
 ┌──────────────┐           │  ├ LogAggregatorAgent     every 60 s       │
 │ sysadmin/    │           │  ├ EstateJudgeAgent       every 1 h        │
 │ core/        │◀──────────│  ├ ServiceDiscoveryAgent  every 6 h        │
 │ contracts.py │ response_ │  └ FileOrganiserAgent     every 24 h       │
 │ defaults.py  │ model=    │                                            │
 │ (pydantic/   │           │                                            │
 │  stdlib only)│           │                                            │
 └──────────────┘           └───┬───────────────────┬─────────────────┬──┘
                                │ SQLAlchemy        │ HTTP            │ HTTP
                                ▼ async             ▼                 ▼
                      ┌──────────────────┐ ┌────────────────┐ ┌──────────────┐
                      │ PostgreSQL       │ │ estate-manager │ │ llama.cpp    │
                      │ db: projects     │ │ :8400          │ │ :8081        │
                      │ schema: sysadmin │ │ five surfaces, │ │ llama-server │
                      │ (Alembic-managed)│ │ judged hourly  │ │ OpenAI-compat│
                      └──────────────────┘ └────────────────┘ └──────────────┘
```

---

## Directory Structure

```
sysadmin_assistant/
├── config.yaml            # All runtime configuration (validated by sysadmin/core/config.py)
├── services.yaml          # Every service, keyed by project id, no paths
│                          # (estate.json is written by estate-manager, not here)
│                          # (projects.yaml retired -> docs/projects-registry-legacy.yaml)
├── sysadmin/              # Backend package (PyPI name: sysadmin-service)
│   ├── main.py            # create_app() factory + lifespan + module-level app
│   ├── metadata.py        # Every mapped table in one import (Alembic + drift test)
│   ├── reload.py          # SIGHUP / POST reload: re-read both YAML files in place
│   ├── ops_claims.py      # Re-measures STATUS.md's opening claims against the box
│   ├── snag_claims.py     # Re-measures each open snag: does the defect still hold?
│   ├── vacuous_guards.py  # Refuses a test whose assertions cannot execute
│   ├── core/              # Depended on by every domain, depends on none
│   │   ├── config.py      # Pydantic models for config.yaml, singleton loader
│   │   ├── contracts.py   # Shared wire contracts (pydantic-only) — used by tray
│   │   ├── defaults.py    # Canonical API host/port defaults (stdlib-only) — used by tray
│   │   ├── agent.py       # BaseAgent template method
│   │   ├── auth.py        # require_auth bearer-token dependency
│   │   ├── database.py    # Async engine/session + NullPool scheduler sessions
│   │   ├── health.py      # GET /health
│   │   ├── scheduler.py   # APScheduler bridge
│   │   ├── jobs.py        # The schedule: 12 JobSpecs, applied at boot and on reload
│   │   ├── escalation.py  # The severity ladder shared by four domains
│   │   ├── llm_client.py, retention.py, event_bus.py, async_http.py
│   │   ├── logging_setup.py, middleware.py, abandoned_runs.py, unit_failure.py
│   │   ├── schema_guard.py    # Refuses to boot against an unexpected schema
│   │   └── models/        # agent_runs, alerts, retention_config
│   ├── monitor/           # Health checks, logs, alerting, reliability, reviews, SSE
│   ├── estate/            # Pulls estate-manager's surfaces and judges them
│   ├── files/             # Filesystem audit, reclaim advice, forecasting, actions
│   ├── units/             # Service discovery — units vs services.yaml vs the kernel
│   └── briefing/          # Cross-domain digests for external consumers
├── sysadmin_tray/         # PyQt6 KDE tray app (console script: sysadmin-tray)
│   ├── app.py             # Orchestrator: QTimers + ApiClient + TrayIcon + Dashboard
│   ├── client.py          # httpx API client (bearer token, connection-lost handling)
│   ├── config.py          # TrayConfig — reads the same config.yaml
│   ├── models.py          # Re-exports sysadmin.core.contracts + icon-state logic
│   ├── tray_icon.py       # Tray icon, menu, alert fingerprint tracking
│   ├── notifications.py   # D-Bus (org.freedesktop.Notifications) notifier
│   ├── dashboard/         # Native window: overview/services/logs/projects/files tabs
│   └── widgets/           # service_grid, resource_gauge, alert_badge
├── alembic/               # Migrations (version table inside sysadmin schema)
├── tests/                 # 3,900 tests: backend (real-app fixture) + tray (headless Qt)
├── scripts/               # preflight/postflight, lint_check, smoke_test, worktrees
├── systemd/               # Unit files for running as a user service
└── docs/                  # roadmap/ (STATUS, tasks, snags, ideas), guides/, sessions/
```

---

## Backend

### App factory & lifespan

`sysadmin/main.py` exposes `create_app(lifespan_ctx=None)` which builds the real
application: CORS middleware (origins from `service.cors_origins` in config.yaml),
`RequestLoggingMiddleware`, a JSON 500 exception handler, all eight routers, and the
`/api/sysadmin/scan-all` trigger endpoint. Tests build this same app with a stub
lifespan; production uses the module-level `app = create_app()`.

The production lifespan: loads config → configures logging → verifies the DB →
**refuses to start if `alembic_version` is behind the packaged head**
(`core/schema_guard.py` — serving against a schema this code was not written for
is worse than not serving) → closes any run abandoned by the previous process →
starts services/agents → applies the job plan (`core/jobs.py`, 12 jobs: five agent
intervals, a desktop reminder sweep, the 06:00 briefing, the 03:00 retention purge,
the 02:00 reliability snapshot and three weekly reviews) → exposes shared instances
on `app.state` → clean shutdown. The same `plan_jobs()`/`apply_jobs()` pair runs
again on reload, so the schedule at boot and the schedule after a `SIGHUP` cannot
be produced differently.

### Routers (8)

| Router | Prefix | Purpose |
|--------|--------|---------|
| health | `/health` | Liveness (status, service, version) |
| sysadmin | `/api/sysadmin` | Service status/actions/details, resources (+history), alerts (+ack), self-monitor, ports, DND, weekly health review, briefing preview, config reload, SSE event stream |
| projects | `/api/projects` | **`managed` only** — live `service_health` joined to registry identity that `estate-lib` supplies. Every other project route left for estate-manager under ADR-0005; `GET /openapi.json` is the check |
| files | `/api/files` | Filesystem audit status, duplicates, misplaced, large, trends (+reclaimable forecast), ranked reclaim advice, weekly disk review, scan, and dry-run-unless-confirmed clean/organise actions |
| logs | `/api/logs` | Recent entries, per-source reads, stats, signature trends, ranked advice, weekly log review |
| units | `/api/units` | Service-discovery sweep and its ranked advice (GET only) |
| services | `/api/services` | Per-service reliability scores over a rolling window, and their ranked advice (GET only) |
| summary | `/api/summary` | Single-call digest (services, alerts, resources) — built for PA, now unconsumed. It carries no project scores: those left with the domain |

Two more routes are **consumed** rather than served — the tray fetches
`/api/projects/overview` and `/api/projects/{name}` from estate-manager on
**:8400** and parses them with this repository's own tolerant models. Two models
for one payload is deliberate: collapsing them would make the tray's
defensiveness the producer's problem.

### Agents — template-method pattern

`core/agent.py` defines `BaseAgent`: the public `run()` template method opens a
scheduler DB session, records a row in `agent_runs` (status/duration/findings),
calls the subclass's abstract `_execute(session)`, and handles failures. It also
provides `raise_alert()` / `resolve_alerts()` writing to the `alerts` table.

There are **five**, and all five are listed here — the diagram above and this
table are the same set.

| Agent | Schedule (config) | Work |
|-------|-------------------|------|
| SysAdminAgent | every 300 s | HTTP/TCP/systemd health checks (system + user units), resource snapshots, threshold alerts (disk/RAM/CPU/GPU), optional auto-restart |
| LogAggregatorAgent | every 60 s | Polls journalctl (system + `--user`) and files from a durable cursor. One alert row per fault **signature**, never per line — the identity is the message with its variable parts removed |
| EstateJudgeAgent | every 1 h | Reads the five surfaces estate-manager publishes on :8400 (scan invariants, attention, audit invariants, audit findings, queue invariants) plus a sixth read locally from disk, and raises alerts from them. It judges; it never scans |
| ServiceDiscoveryAgent | every 6 h | Sweeps installed systemd units against `services.yaml` and against the ports the kernel reports, and ranks what it finds. Findings only — `/api/units` is GET-only by design |
| FileOrganiserAgent | every 24 h | Home-directory audit: duplicates, stale downloads, large files, reclaimable space |

`ProjectOrganiserAgent` is **not** in this table because it is not in this
repository: it moved to estate-manager on 2026-08-13
([ADR-0005](adr/0005-project-state-leaves.md)). Its name survives in
`self_monitor.AGENT_NAMES` and in a disabled `agents.project_organiser` config
block, both of which that ADR records as knowingly untidy.

### Scheduler — APScheduler bridge

`core/scheduler.py` wraps APScheduler 3.x `BackgroundScheduler` (thread pool).
Agents are async, so jobs run through an `asyncio.run()` bridge (`_run_async`),
giving each scheduled run its own event loop in the scheduler thread — which is
why scheduler DB sessions use `NullPool` (see `core/database.py`). Interval triggers
for agents, cron triggers for briefing/retention; job defaults: coalesce,
`max_instances=1`, 300 s misfire grace.

### Services

- **notifier** — httpx client POSTing alerts/briefings to PA's v2 notification
  endpoint, with retry/backoff and DND-aware suppression; PA unreachable is
  non-fatal. **Dormant** — `personal_assistant.enabled: false` short-circuits
  both send paths before any HTTP call.
- **briefing** — builds the structured morning-briefing payload (infrastructure,
  overnight logs, filesystem, the weekly disk review, and the alert digest).
  Still generated daily; the send is suppressed by the flag above. **Its project
  half is gone** — the estate serves its own briefing on :8400 and Alfred pulls
  the two separately, so the alerting path never routes through the estate.
- **retention** — daily purge of old rows per the `retention_config` table. A row
  there and an entry in `metadata.TABLE_TIMESTAMP_MAP` are **both** required: a
  table with only one half is silently never purged.
- **desktop notifier** — `monitor/desktop.py`, the tray's understudy. Subscribed
  to `alert.raised`, it stays silent while the tray has polled `/api/sysadmin/alerts`
  recently and speaks when the tray is not running. Two speakers, only one at a time.
- **event_bus** — in-process async pub/sub (callback list; failures logged, not raised).
- **dnd** — Do Not Disturb manager: config schedule + runtime manual override;
  critical alerts can break through.
- **llm_client** — `LLMClient` speaking llama-server's OpenAI-compatible API
  (`POST /v1/chat/completions`, health via `GET /health`); returns `None`
  gracefully when the server is down.

### Database

PostgreSQL, database `projects`, dedicated **`sysadmin` schema** (isolated from
the other application in the same database — including its own `alembic_version`
via `version_table_schema`). Async access with `postgresql+asyncpg` (search_path
via `server_settings`); Alembic migrations use the sync `psycopg2` URL.
**13 tables**, measured against the live schema 2026-09-10:

| Group | Tables |
|-------|--------|
| Framework | `agent_runs`, `alerts`, `retention_config` |
| Measurements | `service_health`, `resource_snapshots`, `log_entries`, `filesystem_audits`, `unit_audits` |
| Derived history | `reliability_scores`, `desktop_notifications` |
| LLM-narrated reviews | `disk_reviews`, `log_reviews`, `health_reviews` |

The three review tables are separate on purpose — they answer different
questions, and no migration should be able to disturb another's rows. They are
kept for **365 days** where check data is kept for 30: a weekly narrative kept
for a month is four rows, too few to see a trend.

`project_snapshots`, `project_reviews` and `log_summaries` were dropped by
migration 014 on 2026-08-24, after the estate's copy was verified a superset. A
schema drift guard test runs `alembic compare_metadata` against the live DB, and
`metadata.py` — not `alembic/env.py` — owns the one statement of what that
comparison covers.

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

- **`sysadmin/core/contracts.py`** — wire contracts for every tray-consumed endpoint.
  Backend routers set them as `response_model=`; the tray parses responses with
  `Model.from_dict()` (tolerant: `extra="ignore"`, defaulted fields; parse
  failure raises `ValidationError` → tray marks connection lost).
- **`sysadmin/core/defaults.py`** — canonical API host/port defaults
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
- **dashboard/** — native window with Overview, Services, Logs, Projects and Files
  tabs (widgets: service grid, resource gauges, alert badge). The Projects tab is
  fed from estate-manager on :8400, not from this backend. Tabs do no work while
  hidden: `isVisible()` is the gate, because a widget's own answer cannot disagree
  with Qt the way a second flag could.
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

**PA is deliberately absent from the diagram above.** It used to be drawn there as
an arrow out of the backend, and no such call is made: the diagram now carries only
the three peers this service really talks to. A dormant integration is prose, not
an edge.

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
| Schema isolation | `sysadmin` schema in the shared `projects` DB | Coexists with another application's tables without collisions (own alembic_version) |
| Scheduler | APScheduler `BackgroundScheduler` + `asyncio.run()` bridge | Async agents on a sync scheduler; NullPool sessions per-run |
| Agent framework | Template method (`run()` → `_execute()`) | Uniform run recording, timing, and error handling in one place |
| Contracts | Shared pydantic module, `response_model=` + tray import | Kills silent drift (root cause of SNAG-TRAY-005) |
| Auth | Shared bearer token on mutating endpoints only | localhost binding doesn't stop CSRF-style POSTs; GETs stay open for dashboards |
| LLM | llama.cpp llama-server, OpenAI-compatible API | Local inference; graceful `None` degradation when down |
| Testing | Real-app fixture via `create_app()` | Tests exercise production routers/middleware/handlers, not a synthetic app |
| Project state | Owned by estate-manager on :8400, consumed here | The monitor must not own the things it monitors; the estate publishes and never acts, this service judges and never scans ([ADR-0005](adr/0005-project-state-leaves.md)) |
| Alert identity | One row per *fault*, keyed on the title | A row per failed check reached 598,091 unresolved rows once. Dedup, the resolve sweep and the tray's `{severity}:{title}` fingerprint all key on the title, so none of them can disagree about what a fault is |
| Schema mismatch | Refuse to boot | Serving against a schema this code was not written for is worse than not serving — the failure mode of refusing is visible, the failure mode of degrading is not |

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
