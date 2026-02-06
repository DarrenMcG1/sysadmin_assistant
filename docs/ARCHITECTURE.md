# Architecture Overview

## System Architecture

_Describe the high-level architecture of your project here._

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend    │────▶│  Backend    │────▶│  Database   │
│             │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Directory Structure

```
sysadmin-assistant/
├── CLAUDE.md              # Claude Code configuration
├── .claude/               # Claude hooks and settings
│   └── hooks/             # Session lifecycle hooks
├── scripts/               # Development workflow scripts
├── docs/                  # Documentation
│   ├── roadmap/           # STATUS.md, tasks.md, snag_list.md, ideas.md
│   ├── guides/            # How-to guides
│   ├── insights/          # Session insights
│   ├── sessions/          # Session handoffs
│   ├── templates/         # Document templates
│   └── refactors/         # Active refactor tracking
├── backend/               # Backend source
├── frontend/              # Frontend source
└── tests/                 # Test files
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| _Example_ | _PostgreSQL over SQLite_ | _Need for concurrent access and JSON queries_ |

---

## Data Flow

_Describe how data flows through the system._

---

## API Contracts

_Document backend→frontend contracts here as the project grows._

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| _/api/example_ | _GET_ | _—_ | _{ items: [] }_ |

---

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | _None_ | |
| Backend | _FastAPI_ | |
| Database | _PostgreSQL_ | |
| LLM | _llama.cpp_ | |
