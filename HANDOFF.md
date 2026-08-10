# Handoff — 2026-08-10

## Next action

Surface `handoff_duplicates` as a `kind: "roadmap"` recommendation — `scan_roadmap` records it and nothing consumes it, so a repo left mid-migration with two handoffs stays invisible.

## This session (Session 29): the one-thing endpoint

`GET /api/projects/next` — one project, one action, one sentence saying why
it is that one. Feeds alfred-glance, whose premise is glance-then-act.

**The ranking was the feature, and it was decided before any code.**
tasks.md said so and the session honoured it. Chosen: **stuckness** — how
long the stated next action has stood unchanged — tie-broken by the most
recently committed project. The three rejected candidates each failed for a
different reason worth keeping:

- **Nearest-to-finishing** reads `done_tasks`/`open_tasks`, which are
  `None` for three of the five active projects here. It would have been
  blind to most of the population while looking authoritative.
- **Smallest-next-step** is unmeasurable. Nothing records the size of a
  step; every proxy (string length, task count) is invented rather than
  observed.
- **Longest-idle** is the guilt metric the roadmap already doubted, and the
  stated goal is momentum.

**The unit is elapsed days, not scans — this is the part that would have
shipped wrong.** Session 37 handed this session `next_action_changed`, so
counting consecutive unchanged snapshots is a one-line query and the
obvious implementation. It would have passed every fixture written with an
even cadence. On live data it ranks by how often the organiser happened to
run: 6-hourly until Session 35, daily from the timer since, plus every
manual scan — the table holds two scans 17 minutes apart on 2026-08-08 and
two more on 2026-08-10. `unchanged_scans` is still returned as the evidence
behind the number, and `at_window_edge` says when the run reaches the
oldest scan held so `days_unchanged` reads as "at least".

**Verified against the live database before the tests were written.** Both
candidates sat at 2 days; the tie broke on last commit (1 day vs 3) and the
reason sentence named the tie-break it actually used. The winner's next
action turned out to be stale text from the SessionEnd hook Session 37
retired — the endpoint doing its job on its first run.

## Decisions and what was rejected

- **A separate `NextProjectInfo`, not `ProjectBoardEntry`.** The board
  describes a project; this asserts something about it, and the four fields
  carrying the assertion have no meaning in a list where no row was chosen
  over the others. Reusing the board entry would have made `/next` read as
  `/board?limit=1`, which is the reading that loses the ranking.
- **Days from the snapshot series, not `handoff_age_days`.** The document's
  self-reported date says what it claims about itself; the series says what
  was observed, and `handoff_age_days` already decides `stalled`.
- **A `git`-sourced action is not a candidate.** A commit subject is a
  record of the past — honest on the board, where the source is rendered
  beside it, and not an instruction.
- **A handoff stating there is nothing queued is not a candidate either.**
  Two live handoffs read "No unchecked task found — set one before the next
  session". That is a *correct* handoff and still not something to show a
  reader whose whole interaction is one item.
  `roadmap.looks_like_no_action` is conservative in the same direction as
  `is_placeholder`: bare forms must match the whole line, so "None of the
  migrations are applied" survives as real work.
- **Empty is 200 with `project: null`, never 404.** A 404 collapses "every
  project is up to date" into "no scan has ever run", and a consumer cannot
  separate those from a status code.
- **The history query extracts one JSONB field in the database** rather
  than selecting `ProjectSnapshot` rows — the alternative drags kilobytes
  of `findings` per scan across a 90-day window to compute a run length.

## Blocked / waiting on

- **The eligible population is 2 of 23 fresh projects** — 20 inactive, 1
  with no stated action, 2 stating there is nothing queued. The endpoint is
  correct and the estate is the constraint. Whether `says_no_action` should
  itself become a nudge ("write a next action") belongs with Session 31,
  and is filed there rather than added here.
- `handoff_duplicates` and `handoff_path` are recorded by `scan_roadmap`
  and **still read by nothing**. This is the next action above, carried
  forward unchanged from Session 37.
- **Session 30 is unblocked and is work in Alfred's repo** — one
  `work_item` per active project, written by Alfred pulling, so sysadmin
  stays read-only. Nothing here blocks it.
- **`venture-assistant` still falls back to `tasks` for its next action**,
  because its handoff has no `## Next action` heading. Unchanged from
  Session 37; deliberately not edited here.
- `SNAG-ROADMAP-002` remains open: `count_open_snags` reports 7 for the 5
  open snags in this repo's own list.

## State

Branch `main`, suite 1690 passing (1645 → 1690, 45 new), ruff and mypy
clean, 55 → 56 routes. Uncommitted at the time of writing: the new
`sysadmin/projects/next_action.py`, `tests/test_projects_next.py`, and
edits to `snapshots.py`, `roadmap.py`, `router.py`, `contracts.py` plus the
four documents.
