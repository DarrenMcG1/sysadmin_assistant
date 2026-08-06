# The Estate Map

What runs on this box, how the pieces connect, and which resources they
share. Written 2026-08-06.

**Read this when a question spans more than one project** — picking a port,
loading a model onto the GPU, choosing where an app's data lives, or working
out who consumes what. Anything answerable from inside a single repo belongs
in that repo's own `CLAUDE.md`, not here.

This file is deliberately short and mostly pointers. It exists because
cross-repo facts are needed *precisely when you are standing in a repo that
does not contain them*, and it rots the moment it starts duplicating things
that have a better home.

---

## The apps

| Project | Path | What it is | Serves |
|---|---|---|---|
| **Alfred** | `~/projects/Alfred` | Personal assistant; replaced PersonalAssistant 2026-07-24 | backend :8100, Nuxt frontend :3100, llama-server :8081 |
| **alfred-glance** | `~/projects/apps/alfred-glance` | Android "act & glance" client for Alfred. A **render surface, not a data source** — everything it shows arrives via Alfred | nothing on this box |
| **sysadmin-service** | `~/projects/sysadmin_assistant` | Infrastructure monitoring, housekeeping, the morning briefing | backend :8500 |
| **SportsAnalyser** | `~/projects/apps/SportsAnalyser` | Fixture ingest → ELO → ML | backend :8200, Next.js frontend :3200, daily pipeline timer |
| **venture-assistant** | `~/projects/apps/venture-assistant` | Idea enrichment pipeline. Under construction 2026-08-06 | llama-servers :8080 / :8082 / :8083, nightly drain timer. **No app backend yet** — :8300 reserved |
| **daiy** | `~/projects/apps/daiy` | Scan-only, no service | — |

Everything else under `~/projects/apps/` is scan-only: no units, no ports,
discovered by the project organiser for health scoring alone.

**Ports are allocated in one place** — the registry in
[monitorable-project.md §2.1](monitorable-project.md). Do not copy the table
here; claim your row there.

---

## How they tie together

```
sysadmin-service :8500 ──briefing POST 06:00──▶ Alfred :8100 ──▶ alfred-glance
        │                                          (inbox route)
        │  health checks, journal reads
        ▼
   every unit below
```

- **The morning briefing is the only app-to-app data flow today.** sysadmin
  generates it on schedule and POSTs it to a single Alfred inbox route;
  Alfred renders it to alfred-glance. Currently switched off
  (`personal_assistant.enabled: false`) — see
  [alfred-briefing-integration.md](alfred-briefing-integration.md).
- **Everything else is one-directional observation**: sysadmin health-checks
  every app's endpoints and reads their journals. No app calls sysadmin.
- **Planned, not built**: a per-app `GET /api/briefing` that sysadmin fans
  out over, so each app contributes its own domain facts (stale data, failed
  jobs) instead of only up/down and a health score.

---

## Shared resources

### The GPU — one card, four claimants

AMD RX 7900 XTX, 24.5 GB, shared by every inference service. The residency
table and the rules for using it live in
[monitorable-project.md §2.5](monitorable-project.md). Three things to know
before touching it:

- `-ngl 99` is a request, not a constraint — it degrades to CPU silently.
  Gate on `~/.local/bin/wait-for-dgpu` and verify the startup log.
- VRAM is a real constraint. The 02:00 drain evicts `venture-chat` via
  `Conflicts=` because both do not fit.
- **Alfred takes precedence** by policy: it is small enough (~2.0 GB) to
  stay resident through everything else.

Model files are shared out of `~/models/` (~20 GB, provenance in its
README). Four units load from it; a model swap is an edit in the unit *and*
in the owning app's config.

### PostgreSQL — one instance, one convention going forward

**New apps get their own database.** `alfred` and `venture` already do; this
is the convention.

The `projects` database with a schema per app (`sysadmin`,
`sports_analyser`, `daiy`, `personal_assistant`) was an earlier attempt to
keep related things together. It is **grandfathered, not the pattern** —
same treatment as the non-canonical health paths in §2.2. What it actually
cost, concretely:

- Two separate `search_path` mechanisms in sysadmin alone — `server_settings`
  for asyncpg, an event listener for psycopg2/Alembic.
- `version_table_schema="sysadmin"` in Alembic, needed only to stop the
  migration version table colliding with PersonalAssistant's.
- **Zero cross-schema queries exist.** Nothing joins across the boundary, so
  none of the benefit was ever collected.

Migrating the three live schemas out is not worth it — the cost is paid, the
config works, and moving them buys nothing today. New apps simply take a
database.

> ⚠️ **`projects` is 16 GB, of which the retired `personal_assistant`
> schema is 15 GB across 821 tables.** PA was retired 2026-07-24 and its
> repos are archived deliberately, but the data is still live in the
> database sysadmin shares. Worth a decision — dump-and-drop would reclaim
> ~15 GB, more than the file organiser's entire reclaimable estimate. Not
> actioned; a schema drop is irreversible and needs an explicit call.

### MQTT — Alfred-internal

Mosquitto runs with an override under Alfred's systemd directory and carries
Alfred's chore/event bus. **It is not an estate bus**: no other app
publishes or subscribes, and nothing is planned. Treat it as Alfred's
private plumbing, and do not reach for it when connecting two other apps —
if a second consumer ever appears, decide then whether it is promoted.

---

## Conventions, and what is grandfathered against them

| Convention | Grandfathered exceptions |
|---|---|
| `GET /api/health`, 200, JSON, no auth | sysadmin (`/health`), SportsAnalyser (`/api/v1/health`) |
| One database per app | `projects` DB schemas: `sysadmin`, `sports_analyser`, `daiy` |
| Ports claimed in the registry, never a tool's default | venture-assistant on :8080 (llama.cpp's default) — should move to :8301 |
| User units `<project>-<role>.service` | `venture-chat` / `venture-embed` / `venture-chat-large` (role-only names) |

The full contract for new services — ports, health endpoint, unit naming,
oneshot→timer, same-day monitoring wiring — is
[monitorable-project.md](monitorable-project.md). This table only records
where existing apps sit outside it, so nobody copies an exception thinking
it is the rule.

---

## Keeping the seams aligned

Two seams carry data between apps: **sysadmin → Alfred** (Alfred pulls
`/api/sysadmin/briefing/preview`, and will pull the board) and **Alfred →
alfred-glance**. Both ends already guard their *internal* contracts —
`sysadmin/contracts.py` is imported by backend and tray with a round-trip
test; Alfred regenerates `openapi.json` + `frontend/types/api.ts` with a
commit hook. Neither guards the seam *between* them.

**What is already right, and is doing most of the work.** Alfred's adapter
degrades unknown section types to text, and sysadmin omits sections rather
than sending them empty. That tolerance is why the briefing grew from five
sections to seven with no coordination and no breakage. **Additive-only
changes plus a tolerant consumer is the alignment mechanism** — schema
tooling is a supplement to it, never a replacement.

**What is wrong.** Alfred's consumer test reads a *captured* fixture
(`backend/tests/fixtures/briefing_producers/sysadmin_preview.json`) and
asserts every section in it maps. A section that exists but was never
captured is invisible to it. On 2026-08-06 the fixture was recorded in the
morning and was two sections behind by the afternoon — "Pick This Up" and
"Weekly Disk Review" — with the test green throughout.

The fix is one word: the fixture should be **published by the producer**,
not captured by the consumer.

| | Effort | Catches |
|---|---|---|
| **sysadmin commits a canonical sample** regenerated by its own test suite, which Alfred's test reads | small | a new section the consumer cannot map, at the consumer's next commit |
| **sysadmin raises a finding when a consumer's fixture is behind** — it can read Alfred's fixture; both are on this disk | small | drift even when nobody commits, which is the case that actually bites |
| JSON Schema emitted from `contracts.py` and vendored | larger | field-level changes, not just section-level |

The second is the estate-monitor-flavoured version and fits what this
service is for: assert the integration rather than document it.

**Not worth doing: a shared contract package or a monorepo.** Three repos
in three languages (Python, Nuxt/TS, Kotlin) with two seams between them —
a shared library would couple three release cycles to solve a problem that
two files and a test already cover.

## Known gaps

- `garmin-sync.service` and `deadlock-api-ingest.service` run unmonitored
  and belong to no project entry. Eight orphaned `personal-assistant-*`
  units are still installed.
- Session 26 (`tasks.md`) is the mechanical backstop for both, plus port
  registry reconciliation. **Until it lands, this file is maintained by
  hand and will drift** — that is its main weakness, and the reason it
  points at generated sources wherever one exists.
