# SysAdmin Service — Specification

**Date:** 06-02-2026
**Status:** Planning — **superseded in part**; kept as the original design record
**Type:** Standalone FastAPI service with systemd integration
**Database:** `projects` database, `sysadmin` schema + `dev_meta` schema

> **What has changed since this was written (last checked 2026-08-08).**
> The body below is the February plan and is left as written — it is the
> record of what was intended, and rewriting it would lose that. Where it
> disagrees with the code, the code is right. The differences that matter:
>
> | This spec says | Where it actually is now |
> |---|---|
> | One flat `sysadmin/` package (`config.py`, `models/`, `routers/`, `services/`) | Six domain packages — `core/`, `registry/`, `monitor/`, `projects/`, `files/`, `units/`, plus `briefing/`. `monitor` may not import `projects`, enforced by `tests/test_import_boundary.py` |
> | Four agents | Five — service discovery was added in Session 26 |
> | Managed projects and their endpoints in `config.yaml`/`projects.yaml` | Project identity in a `.project.yaml` manifest per repository; services in `services.yaml`, keyed by project id with no paths. `projects.yaml` is retired to [docs/projects-registry-legacy.yaml](docs/projects-registry-legacy.yaml) |
> | Project scanning runs inside the daemon | Also available as its own oneshot unit and timer (`sysadmin-organiser`), so the scan and the monitor no longer share a fate |
> | 9 tables | 13, with `estate.json` as a derived, unpersisted projection alongside them |
>
> The reasoning behind the registry work is in
> [ADR-0001](docs/adr/0001-project-registry.md); the current shape of the
> code is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Overview

A standalone infrastructure monitoring and housekeeping service that runs independently of PersonalAssistant but communicates with it via HTTP API and shared PostgreSQL database. Manages dev environment health, service monitoring, log aggregation, filesystem organisation, and project hygiene.

Runs as a systemd service — starts on boot, always available, no manual intervention.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        sysadmin-service (FastAPI)                        │
│                         http://localhost:8100                            │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  SysAdmin    │  │  Project    │  │    File     │  │     Log      │  │
│  │   Agent      │  │  Organiser  │  │  Organiser  │  │  Aggregator  │  │
│  │             │  │   Agent     │  │   Agent     │  │    Agent     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  │
│         │                │                │                │           │
│         └────────────────┴────────────────┴────────────────┘           │
│                                   │                                     │
│                          ┌────────┴────────┐                           │
│                          │  Internal Event  │                           │
│                          │      Bus         │                           │
│                          └────────┬────────┘                           │
│                                   │                                     │
│         ┌─────────────────────────┼─────────────────────────┐          │
│         │                         │                         │          │
│  ┌──────┴──────┐  ┌──────────────┴──────────┐  ┌──────────┴────────┐ │
│  │  Scheduler   │  │  PostgreSQL (sysadmin)  │  │  Config (YAML)   │ │
│  │  (APScheduler)│  │  + dev_meta schema     │  │                  │ │
│  └─────────────┘  └─────────────────────────┘  └──────────────────┘ │
│                                                                        │
└────────────────────────────────┬───────────────────────────────────────┘
                                 │
                    ┌────────────┴────────────────┐
                    │  PersonalAssistant (8000)    │
                    │  • Receives alerts via POST  │
                    │  • Event bus bridge           │
                    │  • Morning briefing data      │
                    └─────────────────────────────┘
```

---

## Service Configuration

### Port & Identity

| Setting | Value |
|---------|-------|
| Port | 8100 |
| Service name | `sysadmin-service` |
| systemd unit | `sysadmin.service` |
| Working directory | `/home/gaddi/projects/SysAdminService` |
| Python venv | `/home/gaddi/projects/SysAdminService/.venv` |
| Config file | `config.yaml` |
| Log directory | `/home/gaddi/projects/SysAdminService/logs/` |

### config.yaml Structure

```yaml
service:
  name: sysadmin-service
  port: 8100
  host: 127.0.0.1
  log_level: info

database:
  url: postgresql+asyncpg://sysadmin:password@localhost:5432/projects
  schema: sysadmin

personal_assistant:
  url: http://localhost:8000
  api_prefix: /api
  notify_endpoint: /api/notifications
  briefing_endpoint: /api/briefing/data

ollama:
  url: http://localhost:11434
  model: qwen2.5:14b
  night_model: qwen3:72b

agents:
  sysadmin:
    enabled: true
    health_check_interval_seconds: 300
    services:
      - name: personal-assistant
        type: http
        url: http://localhost:8000/health
        systemd_unit: personal-assistant.service
      - name: nuxt-frontend
        type: http
        url: http://localhost:3000
        systemd_unit: null
      - name: postgresql
        type: systemd
        systemd_unit: postgresql.service
      - name: ollama
        type: http
        url: http://localhost:11434/api/tags
        systemd_unit: ollama.service
      - name: redis
        type: tcp
        host: localhost
        port: 6379
        systemd_unit: redis.service
    thresholds:
      disk_warning_percent: 80
      disk_critical_percent: 90
      ram_warning_percent: 85
      cpu_sustained_percent: 90
      cpu_sustained_minutes: 10

  project_organiser:
    enabled: true
    scan_interval_hours: 6
    projects_root: /home/gaddi/projects
    stale_branch_days: 30
    orphan_detection: true
    track_todos: true
    todo_patterns:
      - "TODO"
      - "FIXME"
      - "HACK"
      - "XXX"

  file_organiser:
    enabled: true
    scan_interval_hours: 24
    scan_root: /home/gaddi
    output_dir: /home/gaddi/Documents/DMDocs/Self/Briefings/Audits
    stale_days: 180
    downloads_stale_days: 30
    large_file_mb: 100
    similarity_threshold: 0.75
    skip_dirs:
      - .git
      - .cache
      - .local
      - .config
      - .var
      - .mozilla
      - .steam
      - node_modules
      - __pycache__
      - .venv

  log_aggregator:
    enabled: true
    poll_interval_seconds: 60
    sources:
      - name: personal-assistant
        type: journalctl
        unit: personal-assistant.service
        severity_filter: warning
      - name: postgresql
        type: journalctl
        unit: postgresql.service
        severity_filter: error
      - name: ollama
        type: journalctl
        unit: ollama.service
        severity_filter: warning
      - name: fastapi-app
        type: file
        path: /home/gaddi/projects/MCP/logs/app.log
        severity_filter: warning
    retention_days: 30
    summarise_with_llm: true
```

---

## Agent Specifications

### 1. SysAdmin Agent

**Purpose:** Infrastructure health monitoring, service status, resource tracking.

**Capabilities:**

| Capability | Mechanism | Frequency |
|------------|-----------|-----------|
| Service health checks | HTTP ping / TCP connect / systemd status | Every 5 min |
| Disk usage monitoring | `shutil.disk_usage()` per mount | Every 15 min |
| RAM/CPU monitoring | `psutil` snapshots | Every 5 min |
| PostgreSQL health | Connection pool stats, active queries, DB size | Every 10 min |
| Ollama status | Model loaded, VRAM/RAM usage, inference queue | Every 5 min |
| Port conflict detection | `psutil.net_connections()` | On startup + hourly |
| SSL cert expiry | Check local dev certs if applicable | Daily |
| systemd unit tracking | `systemctl is-active` for registered units | Every 5 min |

**Alerting Logic:**

```
health_check_result → 
  if CRITICAL → immediate POST to PersonalAssistant /api/notifications (urgency: critical)
  if WARNING  → log to sysadmin.alerts table, include in next briefing digest
  if OK       → update sysadmin.service_health, no notification
  if DEGRADED → 3 consecutive degraded = escalate to WARNING
```

**Key Endpoints:**

```
GET  /api/sysadmin/status              → All service statuses
GET  /api/sysadmin/status/{service}    → Single service detail
GET  /api/sysadmin/resources           → CPU, RAM, disk summary
GET  /api/sysadmin/resources/history   → Time-series resource data
GET  /api/sysadmin/alerts              → Active alerts
POST /api/sysadmin/alerts/{id}/ack     → Acknowledge an alert
GET  /api/sysadmin/ports               → Port usage map
```

---

### 2. Project Organiser Agent

**Purpose:** Tracks project health across `/home/gaddi/projects/`, detects staleness, orphans, and hygiene issues.

**Capabilities:**

| Capability | What it does |
|------------|-------------|
| Project discovery | Scans projects root, identifies projects by markers (package.json, pyproject.toml, Cargo.toml, .git) |
| Staleness detection | Last commit date, last file modification, days since activity |
| Branch hygiene | Lists branches per repo, flags merged/stale branches (>30 days no commits) |
| Dependency audit | Checks for outdated lock files, missing .venv, stale node_modules |
| TODO/FIXME scanner | Grep across source files for tracked patterns, counts per project |
| README/CLAUDE.md check | Flags projects missing key documentation files |
| Size tracking | Total size per project, largest directories, growth over time |
| Orphan detection | Projects with no git remote, or remotes that 404 |
| Dev environment check | Missing .env files, broken symlinks, incorrect Python versions |

**Key Endpoints:**

```
GET  /api/projects/overview            → All projects with health scores
GET  /api/projects/{name}              → Single project detail
GET  /api/projects/{name}/todos        → TODOs/FIXMEs in project
GET  /api/projects/{name}/branches     → Branch status
GET  /api/projects/stale               → Projects with no activity > N days
GET  /api/projects/report              → Full markdown report
POST /api/projects/scan                → Trigger immediate rescan
```

**Health Score Calculation:**

```
score = 100
score -= 10 if no_readme
score -= 10 if no_claude_md
score -= 5  per stale branch
score -= 15 if last_commit > 60 days
score -= 10 if last_commit > 30 days
score -= 5  if node_modules exists and stale
score -= 5  per 10 unresolved TODOs
score -= 10 if no .env and .env.example exists
score -= 5  if .git/index.lock exists (stale lock)
```

Grading: 80-100 = Healthy, 60-79 = Needs Attention, 40-59 = Neglected, <40 = Abandoned

---

### 3. File Organiser Agent

**Purpose:** Evolved version of the existing `home_audit.py` — runs as a persistent agent with trending, scheduling, and integration.

**Capabilities:**

Inherits all existing home_audit.py checks:

| Check | Description |
|-------|------------|
| Similar folders | Normalised name comparison + fuzzy match at 75% |
| Misplaced files | Images/videos/docs/audio outside expected directories |
| Old downloads | ~/Downloads items older than 30 days |
| Large files | Files exceeding 100 MB |
| Duplicates | MD5 of first 1 MB + file size |
| Empty directories | Recursive detection |
| Stale project dirs | node_modules, __pycache__, .venv, build, dist with sizes |
| Stale files | Not modified in 180+ days |

**New capabilities as an agent:**

| Capability | Description |
|------------|-------------|
| Trending | Tracks findings over time — are issues growing or shrinking? |
| Disk usage forecasting | Based on growth rate, estimates when thresholds hit |
| Actionable suggestions | Groups findings into "quick wins" (empty dirs, stale caches) vs "needs review" (duplicates, misplaced) |
| Auto-clean (opt-in) | Can auto-remove __pycache__, .pytest_cache, empty dirs with approval |
| Report generation | Saves to vault path, references previous reports for delta |

**Key Endpoints:**

```
GET  /api/files/status                 → Current findings summary
GET  /api/files/report                 → Latest full audit report
GET  /api/files/report/delta           → Changes since last scan
GET  /api/files/duplicates             → Duplicate file groups
GET  /api/files/large                  → Large files list
GET  /api/files/misplaced              → Misplaced files by category
GET  /api/files/trends                 → Historical finding counts
POST /api/files/scan                   → Trigger immediate scan
POST /api/files/clean/stale-caches     → Auto-remove __pycache__ etc (requires confirm param)
```

---

### 4. Log Aggregator Agent

**Purpose:** Collects, filters, and summarises logs from all services into a single queryable store.

**Sources:**

| Source | Type | Method |
|--------|------|--------|
| PersonalAssistant | journalctl | `journalctl -u personal-assistant.service --since` |
| PostgreSQL | journalctl | `journalctl -u postgresql.service --since` |
| Ollama | journalctl | `journalctl -u ollama.service --since` |
| FastAPI app logs | File tail | Tail log file, parse structured JSON lines |
| SysAdmin service (self) | Internal | Direct logging pipeline |
| Night Worker | journalctl/file | If running as service or writing logs |

**Processing Pipeline:**

```
raw log line
  → parse (timestamp, severity, source, message)
  → filter (ignore below configured severity)
  → store in sysadmin.log_entries
  → if error/critical: create alert
  → every N minutes: batch summarise with LLM
  → summary stored in sysadmin.log_summaries
  → summaries fed into morning briefing
```

**LLM Summarisation:**

Batches the last N minutes of warnings/errors, sends to Ollama with a prompt like:

```
You are a sysadmin reviewing logs. Summarise the following log entries.
Group by service. Highlight: recurring errors, new errors not seen before,
patterns suggesting degradation, and anything requiring immediate attention.
Be concise and direct.
```

Uses the daytime model (14B) for periodic summaries. Night Worker can run deeper analysis with the 72B model on the full day's logs.

**Key Endpoints:**

```
GET  /api/logs/recent                  → Last N log entries (filterable by source, severity)
GET  /api/logs/errors                  → Errors/criticals only
GET  /api/logs/{source}                → Logs for specific service
GET  /api/logs/stats                   → Error rates, volume by source
GET  /api/logs/trends                  → Week-on-week trends by fault signature (Tier 1)
GET  /api/logs/actions                 → Ranked, executable advice (Tier 2)
GET  /api/logs/review                  → Latest weekly LLM-narrated review (Tier 3)
POST /api/logs/review/generate         → Generate a review now (auth)
```

`GET /api/logs/summary` and `/api/logs/summary/history` were **removed in
Session 69** with the producer behind them — `LogAggregatorAgent.summarise()`
had no caller anywhere and left one row, dated 2026-07-24, covering 29
seconds. `GET /api/logs/review` replaces them.

Note the removal is *shadowed rather than clean*: `GET /api/logs/{source}`
is a catch-all, so `/api/logs/summary` still answers `200` with
`{"source": "summary", "entries": [], "count": 0}` rather than `404`. No
consumer calls it (the tray never did), but a caller that does gets "no
summaries" where it should get "gone" — `SNAG-LOG-011`.

---

## Database Schema

All tables in the `sysadmin` schema within the `projects` database. Dev tracking uses the shared `dev_meta` schema.

```sql
CREATE SCHEMA IF NOT EXISTS sysadmin;

-- Service health check results
CREATE TABLE sysadmin.service_health (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    details JSONB DEFAULT '{}',
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_health_status CHECK (status IN ('ok', 'degraded', 'warning', 'critical', 'unreachable'))
);

CREATE INDEX idx_service_health_name_time ON sysadmin.service_health(service_name, checked_at DESC);

-- Resource snapshots (CPU, RAM, disk)
CREATE TABLE sysadmin.resource_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cpu_percent NUMERIC(5,2),
    ram_used_mb INTEGER,
    ram_total_mb INTEGER,
    ram_percent NUMERIC(5,2),
    swap_used_mb INTEGER,
    swap_total_mb INTEGER,
    disk_usage JSONB DEFAULT '{}',
    gpu_usage JSONB DEFAULT '{}',
    load_avg_1m NUMERIC(5,2),
    load_avg_5m NUMERIC(5,2),
    load_avg_15m NUMERIC(5,2),
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resource_snapshots_time ON sysadmin.resource_snapshots(recorded_at DESC);

-- Alerts
CREATE TABLE sysadmin.alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT,
    details JSONB DEFAULT '{}',
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_at TIMESTAMPTZ,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_alert_severity CHECK (severity IN ('info', 'warning', 'critical')),
    CONSTRAINT chk_alert_agent CHECK (agent IN ('sysadmin', 'project_organiser', 'file_organiser', 'log_aggregator'))
);

CREATE INDEX idx_alerts_active ON sysadmin.alerts(created_at DESC) WHERE resolved = FALSE;

-- Project health snapshots
CREATE TABLE sysadmin.project_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(200) NOT NULL,
    project_path TEXT NOT NULL,
    health_score INTEGER NOT NULL,
    last_commit_at TIMESTAMPTZ,
    branch_count INTEGER,
    stale_branch_count INTEGER,
    todo_count INTEGER,
    fixme_count INTEGER,
    has_readme BOOLEAN,
    has_claude_md BOOLEAN,
    total_size_mb INTEGER,
    findings JSONB DEFAULT '{}',
    scanned_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_project_snapshots_name_time ON sysadmin.project_snapshots(project_name, scanned_at DESC);

-- Filesystem audit results
CREATE TABLE sysadmin.filesystem_audits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_root TEXT NOT NULL,
    similar_folders_count INTEGER DEFAULT 0,
    misplaced_files_count INTEGER DEFAULT 0,
    old_downloads_count INTEGER DEFAULT 0,
    large_files_count INTEGER DEFAULT 0,
    duplicate_groups_count INTEGER DEFAULT 0,
    empty_dirs_count INTEGER DEFAULT 0,
    stale_project_dirs_count INTEGER DEFAULT 0,
    stale_files_count INTEGER DEFAULT 0,
    total_reclaimable_mb INTEGER DEFAULT 0,
    findings JSONB DEFAULT '{}',
    report_path TEXT,
    scanned_at TIMESTAMPTZ DEFAULT NOW()
);

-- Log entries
CREATE TABLE sysadmin.log_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    raw_line TEXT,
    metadata JSONB DEFAULT '{}',
    logged_at TIMESTAMPTZ NOT NULL,
    ingested_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_log_severity CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical'))
);

CREATE INDEX idx_log_entries_source_time ON sysadmin.log_entries(source, logged_at DESC);
CREATE INDEX idx_log_entries_severity ON sysadmin.log_entries(severity, logged_at DESC) WHERE severity IN ('warning', 'error', 'critical');

-- LLM-generated log summaries
CREATE TABLE sysadmin.log_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    model_used VARCHAR(100),
    summary TEXT NOT NULL,
    entry_count INTEGER,
    error_count INTEGER,
    sources JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent run history (tracks when each agent last ran and outcome)
CREATE TABLE sysadmin.agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent VARCHAR(50) NOT NULL,
    run_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    duration_seconds NUMERIC(10,2),
    findings_count INTEGER DEFAULT 0,
    alerts_raised INTEGER DEFAULT 0,
    details JSONB DEFAULT '{}',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    CONSTRAINT chk_run_status CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_agent_runs_agent_time ON sysadmin.agent_runs(agent, started_at DESC);

-- Retention policy: auto-purge old data
-- service_health: 7 days
-- resource_snapshots: 30 days (downsample to hourly after 7 days)
-- log_entries: 30 days
-- log_summaries: 90 days
-- alerts: 90 days (resolved), indefinite (unresolved)
-- project_snapshots: 90 days (keep latest per project indefinitely)
-- filesystem_audits: 90 days (keep latest indefinitely)
-- agent_runs: 30 days

CREATE TABLE sysadmin.retention_config (
    table_name VARCHAR(100) PRIMARY KEY,
    retention_days INTEGER NOT NULL,
    downsample_after_days INTEGER,
    downsample_interval VARCHAR(20),
    last_purged_at TIMESTAMPTZ
);

INSERT INTO sysadmin.retention_config (table_name, retention_days, downsample_after_days, downsample_interval) VALUES
    ('service_health', 7, NULL, NULL),
    ('resource_snapshots', 30, 7, 'hourly'),
    ('log_entries', 30, NULL, NULL),
    ('log_summaries', 90, NULL, NULL),
    ('alerts', 90, NULL, NULL),
    ('project_snapshots', 90, NULL, NULL),
    ('filesystem_audits', 90, NULL, NULL),
    ('agent_runs', 30, NULL, NULL);
```

---

## Project Structure

```
SysAdminService/
├── pyproject.toml
├── config.yaml
├── alembic.ini
├── alembic/
│   └── versions/
├── sysadmin/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app, lifespan, startup
│   ├── config.py                  # Pydantic settings from config.yaml
│   ├── database.py                # Async SQLAlchemy engine + session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── service_health.py
│   │   ├── resource_snapshot.py
│   │   ├── alert.py
│   │   ├── project_snapshot.py
│   │   ├── filesystem_audit.py
│   │   ├── log_entry.py
│   │   ├── log_summary.py
│   │   └── agent_run.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseAgent class with scheduling, logging, run tracking
│   │   ├── sysadmin_agent.py
│   │   ├── project_organiser.py
│   │   ├── file_organiser.py
│   │   └── log_aggregator.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py              # /health endpoint
│   │   ├── sysadmin.py
│   │   ├── projects.py
│   │   ├── files.py
│   │   └── logs.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scheduler.py           # APScheduler wrapper
│   │   ├── ollama_client.py       # Shared Ollama HTTP client
│   │   ├── notifier.py            # POST alerts to PersonalAssistant
│   │   ├── retention.py           # Data purge/downsample jobs
│   │   └── event_bus.py           # Internal pub/sub
│   └── utils/
│       ├── __init__.py
│       ├── systemd.py             # systemctl wrappers
│       ├── journal.py             # journalctl parsing
│       └── git.py                 # git repo inspection helpers
├── tests/
│   ├── __init__.py
│   ├── test_sysadmin_agent.py
│   ├── test_project_organiser.py
│   ├── test_file_organiser.py
│   └── test_log_aggregator.py
├── scripts/
│   ├── install.sh                 # Create venv, install deps, run migrations
│   └── setup-systemd.sh           # Install + enable systemd unit
└── systemd/
    └── sysadmin.service
```

---

## systemd Unit

```ini
# /etc/systemd/system/sysadmin.service
[Unit]
Description=SysAdmin Infrastructure Monitoring Service
After=network.target postgresql.service ollama.service
Wants=postgresql.service

[Service]
Type=simple
User=gaddi
Group=gaddi
WorkingDirectory=/home/gaddi/projects/SysAdminService
Environment=PATH=/home/gaddi/projects/SysAdminService/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=/home/gaddi/projects/SysAdminService/.venv/bin/uvicorn sysadmin.main:app --host 127.0.0.1 --port 8100 --workers 1
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sysadmin-service

# Resource limits
MemoryMax=512M
CPUQuota=25%

[Install]
WantedBy=multi-user.target
```

---

## BaseAgent Pattern

All agents inherit from a common base:

```python
class BaseAgent:
    name: str
    enabled: bool
    scheduler: AsyncScheduler

    async def startup(self) -> None
    async def shutdown(self) -> None
    async def run(self, run_type: str) -> AgentRunResult
    async def record_run(self, result: AgentRunResult) -> None
    async def raise_alert(self, severity: str, title: str, message: str, details: dict) -> None
    async def notify_pa(self, notification: dict) -> None
```

Each agent registers its own scheduled jobs during `startup()`. The scheduler persists job state so missed runs (e.g. service was down) can be detected and caught up.

---

## PersonalAssistant Integration

### Outbound (SysAdmin → PA)

| Trigger | Endpoint | Payload |
|---------|----------|---------|
| Critical alert | `POST /api/notifications` | `{source: "sysadmin", urgency: "critical", title, message}` |
| Morning briefing data | `POST /api/briefing/data` | `{source: "sysadmin", sections: [...]}` |
| Service down | `POST /api/notifications` | `{source: "sysadmin", type: "service_down", service, details}` |

### Inbound (PA → SysAdmin)

| Trigger | Endpoint | Purpose |
|---------|----------|---------|
| On-demand scan | `POST /api/files/scan` | User requests filesystem audit via PA chat |
| Project check | `GET /api/projects/{name}` | PA agents query project health before creating tasks |
| Resource check | `GET /api/sysadmin/resources` | Night Worker checks resources before starting heavy jobs |

### Morning Briefing Contribution

The SysAdmin service pushes a structured block to PA's briefing system:

```json
{
  "source": "sysadmin-service",
  "generated_at": "2026-02-06T06:00:00Z",
  "sections": [
    {
      "title": "Infrastructure Status",
      "type": "status_grid",
      "data": {
        "all_services_healthy": false,
        "services": [
          {"name": "postgresql", "status": "ok"},
          {"name": "ollama", "status": "ok"},
          {"name": "personal-assistant", "status": "degraded", "note": "High memory usage (82%)"}
        ]
      }
    },
    {
      "title": "Overnight Log Summary",
      "type": "text",
      "data": "3 PostgreSQL slow queries detected (>5s). Ollama model swap failed at 02:14 — retried successfully at 02:15. No critical errors."
    },
    {
      "title": "Filesystem",
      "type": "metrics",
      "data": {
        "disk_used_percent": 67,
        "reclaimable_mb": 4200,
        "new_issues_since_last": 3,
        "quick_wins": "12 empty dirs, 3 stale __pycache__ (890 MB)"
      }
    },
    {
      "title": "Project Health",
      "type": "table",
      "data": [
        {"project": "PersonalAssistant", "score": 82, "change": -3, "note": "2 new stale branches"},
        {"project": "SysAdminService", "score": 95, "change": 0},
        {"project": "DaIY", "score": 70, "change": +5, "note": "README added"}
      ]
    }
  ]
}
```

---

## Night Worker Integration

The SysAdmin service exposes data that the Night Worker can consume for deeper analysis:

| Night Worker Job | SysAdmin Data Used |
|------------------|--------------------|
| Deep log analysis | `GET /api/logs/recent?hours=24&severity=all` — full day's logs for pattern analysis with 72B model |
| Infrastructure trending | `GET /api/sysadmin/resources/history?days=7` — resource usage trends for capacity forecasting |
| Project health deep dive | `GET /api/projects/overview` — identify projects needing attention, generate recommended actions |
| Storage forecasting | `GET /api/files/trends` — predict when disk thresholds will be hit based on growth rate |

---

## Nuxt Frontend Pages

New pages to add to the PersonalAssistant frontend (or serve from SysAdmin's own static files):

### /infrastructure

Full dashboard showing:
- Service status grid (green/amber/red tiles)
- CPU/RAM/disk gauges with 24h sparklines
- Active alerts list
- Recent log errors

### /infrastructure/projects

Project health table with scores, sortable, clickable to detail view showing branches, TODOs, dependency status.

### /infrastructure/storage

Filesystem audit findings — duplicates, large files, misplaced items, trends chart, quick-action buttons for safe cleanups.

### /infrastructure/logs

Searchable log viewer — filter by source, severity, time range. LLM summary panel at top.

---

## Implementation Order

| Phase | What | Agents Involved | Estimated Effort |
|-------|------|----------------|-----------------|
| 1 | Project skeleton, config, DB schema, systemd unit, health endpoint | Core | 1-2 days |
| 2 | BaseAgent, scheduler, SysAdmin agent (health checks + resources) | SysAdmin | 2-3 days |
| 3 | Alert system, PA notification integration | SysAdmin | 1 day |
| 4 | File Organiser agent (port home_audit.py, add trending + DB storage) | File Organiser | 2 days |
| 5 | Project Organiser agent (git inspection, health scoring, TODO scanning) | Project Organiser | 2-3 days |
| 6 | Log Aggregator (journalctl + file parsing, storage, basic filtering) | Log Aggregator | 2 days |
| 7 | LLM log summarisation | Log Aggregator | 1 day |
| 8 | Morning briefing integration | All | 1 day |
| 9 | Retention/purge jobs | Core | 0.5 days |
| 10 | Nuxt dashboard pages | Frontend | 3-4 days |
| 11 | Night Worker integration endpoints | All | 1 day |
| 12 | Dev meta schema setup + self-tracking | Core | 0.5 days |

**Total estimate: ~17-20 days**

---

## Dependencies

```toml
[project]
name = "sysadmin-service"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0",
    "psutil>=5.9.0",
    "httpx>=0.27.0",
    "apscheduler>=3.10.0",
    "gitpython>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.5.0",
]
```

---

## Open Questions

1. **Shared dev-meta package** — Should this service use the extracted `dev-meta` package discussed earlier, or duplicate the schema for now and extract later?
2. **Frontend hosting** — Should the infrastructure pages live in the PA Nuxt app (consuming SysAdmin API), or should SysAdmin serve its own minimal dashboard?
3. **Auto-remediation** — Should the SysAdmin agent be able to restart failed systemd services automatically, or only alert? If auto-restart, what's the limit before it stops trying?
4. **Enforcer integration** — Should disk usage warnings feed into the Enforcer's gate logic? (e.g. disk >85% = block new project creation until cleanup)
