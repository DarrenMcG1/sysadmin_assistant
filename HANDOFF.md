# Handoff — 2026-08-17

## Next action

Take Session 27 — the log-aggregator tiers — because the snag it has been coupled to since 2026-08-05 was fixed on 2026-08-12 and closed on paper today, so the session is no longer "fix the pile-up, then build the tiers" but only the tiers, on an alerts table holding eight unresolved rows where one title held 547,814 six days ago.

## Two-minute job first, and it is not the session

Resolve the two `Estate port … registry breach` rows so the judge
re-raises them under Session 57's code:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

Session 57's `TRANSIENT_HOLDER_SEVERITY = "info"` **is live** — the
daemon restarted 2026-08-17 10:06:38, four minutes after that commit —
but both rows were raised 2026-08-16 12:07 and
`EstateJudgeAgent._execute` skips a judgement whose title is already open
before it reads severity or `details`. Both dev servers are still bound,
so this does not self-clear until the editor closes, and the tray will
restate them at `warning` on its 24-hour reminder. Left for the owner
rather than run from a documentation sitting: it is a write to the live
`alerts` table. Filed as `SNAG-ESTATE-010`.

## This session — Session 58, the document catches up with the box

**The recommendation, taken on the fourth attempt.** `SNAG-DOCS-001` was
named at the close of Session 55, re-stated by 56 and displaced twice on
merit by a detector's first live data. That argument was spent — all five
estate surfaces have now been driven against real payloads — and no
fourth such opportunity was queued.

### The entry was right about the fault and wrong about its size

Both numbers in the snag are wrong, and how they are wrong is the
finding rather than an erratum:

- The Contract Registry held **twelve** `/api/projects` rows, not
  fifteen.
- The narratives were **nine** blocks, not five — `snapshots.py`,
  `build_narrative_history`, `/next`, `momentum.py`, `nudges.py`,
  `/stale`, `status: archived`, the marker scan and `branch_actions.py`
  — found by grepping the tree rather than counting the paths the entry
  lists.
- **Six further sentences** compared a live thing to a departed one and
  each reads correctly in isolation: "the file-organiser mirror of
  `/api/projects/actions`", "the third scorer, after the project
  organiser's repositories", "the two weekly reviews" (there is one),
  "both project sections read **one** snapshot query" (there are none),
  the retention narrative's example route, and `sysadmin/registry/` named
  as the manifest parser in the Database Configuration block. That
  residue is what a block-level sweep leaves behind.

### The population splits three ways, and the entry's own remedy would have broken it

`GET /api/projects/managed` **is still served here** — ADR-0005 relocated
it *within* this repository because its substance is live
`service_health` wearing a project-shaped URL. `/overview` and `/{name}`
are **consumed** from 8400 and parsed with this repository's tolerant
models, guarded by `tests/test_estate_project_contracts.py`. Only the
remaining nine are neither served nor consumed. Applied literally,
"move each block behind a pointer to estate-manager" deletes a live
route's contract and relabels a live seam as absent.

### Decisions taken, and what was rejected

- **Two blocks rewritten, not pointed away**, because the argument is
  still this repository's. `SysAdminAgent._resolve_recovered` was the
  second half of "both scoring agents resolve alerts set-based": the
  project organiser made the case, we still run the statement, and
  pointing the whole block away leaves a borrowed rule looking invented.
- **`core/escalation.py`'s stated reason expired with the domain.** It
  lived in `core` because `monitor` may not import `projects`; that
  package cannot exist. Rejected: deleting the sentence, which leaves a
  correct conclusion resting on a dead premise — `SNAG-AGENT-006`'s trap
  arriving in a document. It now names the four climbers it has
  (`monitor/stalls.py`, `monitor/failures.py`, `units/agent.py`,
  `estate/judgements.py`) and says the boundary test guards against
  bringing the package back rather than constraining anything live.
- **The dead contract models were not deleted.** Eight have zero readers
  and four are re-exported by `sysadmin_tray/models.py`. Removing a
  re-exported name changes the tray's public surface, and this sitting
  touched no code. Filed as `SNAG-DOCS-002` with the decision it needs
  stated rather than taken.
- **ADR-0005 was not linked from `CLAUDE.md` at all** — the pointer
  target of the entire fix, missing from the index it points through.
  0003 and 0004 were missing too. All three added; ADR-0001's open
  question is marked answered against this repository.

### Found by measuring the box, not the tree

- **`SNAG-AGENT-002` was fixed on 2026-08-12.** Its stated remedy —
  group by unit plus a normalised signature, one alert carrying an
  occurrence count — is `log_signature.py` verbatim, shipped under
  `SNAG-AGENT-005`. `STATUS.md`'s runners-up had **already noticed** on
  2026-08-16; the observation never reached the entry or `tasks.md`, so
  the session stayed gated. The failure is a measurement that reached
  the document nobody acts from.
- **`SNAG-ESTATE-010`**: a judgement that gets *quieter* cannot reach an
  open row. Escalation has resolve-and-re-raise; nothing has the
  reverse, so any fix that quietens a family is silent on every fault
  standing when it ships. Not fixed here — the obvious remedy
  (resolve-and-re-raise on a severity mismatch) rebuilds
  `collation.py`'s flip-flop.
- **The snag parser went 36 → 38** across a sitting that closed two and
  opened two, because it cannot see a closure that stays in place under
  "Open". `SNAG-ROADMAP-002` demonstrating itself, and still filed here
  though the parser left for estate-manager on 2026-08-13.

### Verified

`GET :8500/openapi.json` serves **one** route under `/api/projects`.
Model readers measured by grep over `sysadmin/`, `sysadmin_tray/` and
`tests/` with `contracts.py` excluded. Snag count measured either side of
the edit by driving estate-manager's own `count_open_snags` over this
file. `CLAUDE.md` 1,774 → 1,684 lines. Suite **1866** green — a
documentation change cannot break it, which is the reason to run it
rather than not to.
