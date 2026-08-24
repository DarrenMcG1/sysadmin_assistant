# ADR-0005: Project state leaves — the scanner, the board and the briefing's project half move to the estate

- **Status**: accepted
- **Date**: 2026-08-12
- **Supersedes**: the project-state half of
  [ADR-0001](0001-project-registry.md) — its open question ("who owns
  project state") is answered *against* this repository, for a reason
  that ADR could not have weighed: the estate owns the roadmap document
  standard, and a parser living apart from its contract is the
  copy-drift shape. ADR-0001's staging (files as source of truth, the
  package's import boundary, the organiser's own timer and entry point)
  is what made the move a directory move; its warning that the interface
  is the expensive part was correct and was paid on the estate's side.
- **Executed under**: estate-manager Session 4 (the third and last
  founding extraction — the bounded exception in estate ADR-0002, which
  **closes with this landing**), recorded in this repository's own
  sequence per that same ADR
- **Estate side**: estate-manager ADR-0004 (the decision to move) and
  ADR-0008 (the migration's shape)

## What left

- **`sysadmin/projects/`** — all of it: scanner, roadmap parse, board,
  `/next`, momentum, recommendations, nudge arithmetic, weekly review,
  branch actions, estate.json emission. Now
  `estate_service/projects/` on port 8400.
- **`sysadmin/registry/`** — to the shared library as `estate.registry`
  (the `.project.yaml` standard is the estate's; the parse lives with
  the contract). This repository's `units`, `monitor` and `main`
  domains import it from `estate-lib`, which they already consume.
- **The briefing's project half**: "Project Health", "Pick This Up" and
  "Weekly Project Review" now come from the estate's own producer
  (`GET :8400/api/estate/briefing`). `briefing/preview` keeps the
  machine sections — Infrastructure, Overnight Logs, Filesystem, Weekly
  Disk Review — **and the alert digest**: Alfred pulls producers
  separately (its ADR-0070), so the alerting path never routes through
  the estate.
- **`project_snapshots` and `project_reviews` history** — copied once
  into database `estate` so streak and momentum series survived the
  cutover. The tables here were **frozen**, and the follow-up this
  paragraph named was **carried out on 2026-08-24 by migration 014**,
  which dropped both (and `log_summaries`) with their `metadata.py`
  exclusions, their retention rows and their `TABLE_TIMESTAMP_MAP`
  entries.

  Two things the follow-up settled that this ADR had left open. The copy
  was verified before the drop rather than trusted: compared on
  `(project_name, scanned_at)`, the estate holds **4,155** snapshots
  reaching back to **2026-05-10** against this schema's 3,447 from
  2026-05-20, and the only 26 rows it lacked — the final sweep at
  `2026-08-13 07:35:03` — are superseded by the estate's own next scan
  **43 seconds later**, in which all 26 projects appear. And *"the
  retention purge will thin them"* turned out to be the argument against
  waiting rather than for it: the purge deleted 292 of these rows
  between 2026-08-16 and the drop, so every sitting that deferred this
  lost history it believed it was preserving.
- **`sysadmin-organiser`** (console script, service, timer) — retired;
  `estate-manager-scan.timer` holds the 04:30 slot now. The weekly
  project review cron in `main.py` went with it; the disk review stays.
- **`strip_markdown` / `truncate_at_word`** — to `estate.text`
  (mechanism needed on both sides of the seam); `core/text.py`
  re-exports, so importers here are unchanged.

## What stayed, and what this repository gained

- **`GET /api/projects/managed` stayed** (relocated within this repo,
  path unchanged): its substance is live `service_health` — the
  monitor's data — joined to registry identity the library now
  supplies. The tray keeps its URL.
- **`GET /api/services/by-project` is new**: project id → service
  names, this repository's contribution to estate.json, pulled by the
  estate's scanner once per scan. Names only, deliberately.
- **The judging swap (estate ADR-0004 §6)**: this repository now judges
  the estate's scan from outside — `GET :8400/api/projects/invariants`
  (scan age, parse failures, repos skipped) and
  `GET :8400/api/projects/attention` (health breaches, idle nudges —
  data the estate publishes and may not act on). Wiring those
  judgements into checks and alerts is **this repository's own next
  session**; until it runs, nudges reach no tray toast. The estate
  never judges its own scan; we never judge our own briefing pull.

## Left honest

- The `agents.project_organiser` block in config.yaml and its config
  classes remain parsed-but-mostly-unread (the files domain still reads
  `projects_root` for its safety fence; `enabled` was already false).
  Trimming that is housekeeping for a later session — recorded rather
  than rushed, because config classes fan out into defaults tests.
- The tray still points at this service for `/overview` and `/{name}`
  detail; those routes now live on 8400 and the tray's client was
  repointed in the same sitting.
- This process serves the old routes until its next sudo-gated restart;
  the estate's routes are live already, so the only window is a stale
  `/api/projects/*` on 8500, not an outage.
