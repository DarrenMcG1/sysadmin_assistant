# Handoff — 2026-08-10

## Next action

Restart `sysadmin.service` with `sudo systemctl restart sysadmin.service`, because the running process predates Session 37 and every stored snapshot carries neither `handoff_path` nor `handoff_duplicates`, so two sessions of project-side work are invisible on the live box until it happens.

## This session (Session 38): the unread handoff gets a reader

`handoff_duplicates` had been recorded by `scan_roadmap` since Session 37
and consumed by nothing. It is now a zero-point `kind: "roadmap"`
recommendation. Because all three surfaces call `recommendations_for`,
that one addition reaches `/api/projects/{name}/recommendations`,
`/api/projects/actions` and the weekly review — no route, no contract
change, no migration.

**Re-measuring the estate first changed what this session was.** The task
was written when four repos carried a generated `docs/sessions/handoff.md`
beside a real one. Commit `0d56081` cleared them: **seven repos hold a
handoff and every one holds exactly one** — root `HANDOFF.md` in `Alfred`,
`ImbaBots`, this repo, `apps/venture-assistant` and
`apps/SportsAnalyser`, plus `docs/sessions/handoff.md` in the two archived
`PersonalAssistant` repos, which the non-active waiver excludes anyway.
Nothing holds two, so this ships as a regression detector rather than a
report on a live mess, and it was verified against a constructed
two-handoff repository. The mtime branch is the one that fired — a
generated stub headed `# Session Handoff` carries no ISO date, which is
the realistic shape.

**The first survey was wrong, and the way it was wrong is worth keeping.**
It globbed `~/projects/*/` — 11 directories — while `discovery_depth: 2`
makes the scanned population 25 across `~/projects/`, `apps/` and
`archive/`. It therefore reported `venture-assistant` and `SportsAnalyser`
as holding no handoff at all, which **contradicts a Session 37 finding**
sitting in this repo's own tasks.md (venture-assistant's root `HANDOFF.md`
is in 8 of its 9 commits) and the contradiction was not noticed. The
conclusion survived the correction; the evidence given for it did not.
Enumerate the estate the way the scanner does, or read `estate-map.md` —
a top-level glob is not the estate.

**The live table could not have answered either way, and that is the next
action.** The newest snapshot (09:06 today) has neither of the two Session
37 keys, so 90 days of JSONB read `None` for both.

## Decisions and what was rejected

- **The field was widened from bare paths to
  `{path, date, date_source, days_older}`.** Two cases a reader must
  separate are indistinguishable as paths: a loser nine days behind the
  winner is migration debris and can be deleted, while one *sharing* the
  winner's date lost on tuple order alone. Advice that conflated them
  would recreate `SNAG-ROADMAP-003` from the deletion side — throwing away
  the real record to tidy up the stub. Rejected: keeping paths and hedging
  the wording (cheaper, but the advice can never license the deletion it
  exists to recommend); adding a parallel `handoff_duplicate_details` key
  (a redundant key in every future snapshot to protect readers that do not
  exist).
- **`days_older` measures the gap to the chosen handoff, not to today.**
  `handoff_age_days` already answers "how current is the record"; this
  answers "how far behind is the one nobody reads", and it must not move
  when the clock does. Pinned by a test that scans with `now` a year on.
- **`date_source` exists because `handoff_date` falls back to mtime.** A
  clone or a checkout rewrites every mtime on disk, so an age derived that
  way is the weaker claim. Selection still applies the fallback uniformly
  — that was Session 37's hard-won fix and is untouched. This constrains
  only what the *advice* asserts: mtime-derived gaps are marked "by file
  date" and the detail says why.
- **`days_older` of `0` or `None` never produces "delete".** Both mean
  this module cannot say which document is real — same-day lost on path
  preference, `None` is the pre-widening shape — so both take "confirm
  which is current".
- **The bare-string shape is still accepted**, on the `stale_branches`
  precedent: retention outlives a shape change, and a hand-written
  findings dict is a legitimate way to exercise the code.
- **`handoff_path` is consumed in the detail line only**, which was a
  deliberate call and leaves it unread in a repo with one handoff. Putting
  it on `ProjectBoardEntry` is the fuller answer to Session 37's
  provenance argument, and it touches `contracts.py`, the board builder,
  `alfred-projects-page.md` and Alfred's expectations — a sitting of its
  own, filed in tasks.md rather than ridden along here.

## Blocked / waiting on

- **The daemon restart is the next action and needs `sudo`.** It has been
  owed since 2026-07-24; what is new is a measurement of the cost rather
  than a reminder.
- **The detector fires for nothing today, by construction.** It cannot be
  confirmed against live data until a repo grows a second handoff. The
  constructed-repository check is in the session log above; there is no
  live proof and this handoff does not claim one.
- **The non-active waiver is inherited, not decided.** A duplicate handoff
  in a dormant repo raises nothing, because
  `_roadmap_recommendations` waives everything for non-active projects.
  Defensible, and a dormant repo mid-migration is where a stray handoff
  survives longest. Filed for revisit if one is ever found.
- **Session 30 remains unblocked and is work in Alfred's repo** —
  unchanged; nothing here touches it.
- `SNAG-ROADMAP-002` remains open: `count_open_snags` reports 7 for the 5
  open snags in this repo's own list.

## State

Branch `main`, suite 1690 → 1701 (11 new), ruff and mypy clean, 56 routes
unchanged. Uncommitted at the time of writing: `sysadmin/projects/roadmap.py`,
`sysadmin/projects/recommendations.py`, `tests/test_roadmap.py`,
`tests/test_project_board.py`, plus `docs/roadmap/STATUS.md`,
`docs/roadmap/tasks.md` and this file. `docs/guides/monitorable-project.md`
carried an unrelated uncommitted edit from before this session started and
was left alone.
