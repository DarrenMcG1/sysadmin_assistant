# Handoff — 2026-08-11

## Next action

Restart `sysadmin.service` with `sudo systemctl restart sysadmin.service`, because the running process predates Session 37 and every stored snapshot carries neither `handoff_path` nor `handoff_duplicates`, so three sessions of project-side work stay invisible on the live box until it happens.

## This session (Session 39): Session 30 was closed unbuilt, by its consumer

The sitting opened to build Session 30 — Alfred creating one `work_item`
per active project from `/api/projects/next`. Checking the consumer
before writing anything ended it. **Alfred accepted ADR-0064 on
2026-08-07**, three days *before* Session 29 shipped, declining the whole
projects-page arc for v1 behind two named triggers. This repo's tasks.md
said "nothing here blocks it beyond Session 29". The block was never on
this side; the row was wrong the day it was written.

**Neither trigger fires, and one moved the wrong way.**

| Trigger | Fires at | Live 2026-08-11 |
|---|---|---|
| (a) Stall returns | `stalled_count ≥ 2` on `?sort=neglect`, sustained over two weekly reads | **0** |
| (b) Estate outgrows the five-row cap | `count ≥ 12` active | **5** (was 6 when the ADR was written) |

The board carries 3 stalled projects, all among the 20 **inactive** ones
the trigger deliberately excludes — declaring a project dormant *was* the
decision, so it cannot also count as a stall.

**The decline is not a rejection of the endpoints**, which matters for how
this is filed. ADR-0064 §1 finds the momentum data already reaches the
owner as the daily digest's `Pick This Up` section, rendered with this
repo's own honesty treatment, and §2 makes `alfred-projects-page.md` the
build instruction the moment a trigger fires — "good and should be
followed rather than redesigned". So the spec is deferred, not discarded,
and §§1–6 of it still describe live contract-pinned endpoints that any
other consumer reads as written.

**The real defect was that the decision lived in one repo and the work in
the other.** A declined-by-the-consumer state had no representation on the
producer's side, so this roadmap kept advertising the work as unblocked
while Alfred had refused it in writing four days earlier. Recorded now in
both places it gets read from: the tasks.md row carries the trigger table
and the one-line `curl` that re-checks it, and the guide gains a **§0
status block ahead of §1** so nobody reaches the spec without meeting the
decline first.

## Also fixed: a test that failed on a date, not on a change

`test_endpoint_filters_by_confidence` was red on arrival, and pre-existing
— confirmed by stashing the uncommitted Session 38 work and watching it
fail anyway, before anything was attributed to it.

`tests/test_reliability_api.py` held **two clocks**. Every direct-scorer
call pins `now=NOW` (2026-08-07 12:00) with the fixture rows anchored
there, while the nine endpoint calls go through the route, which reads
`datetime.now(UTC)` because that endpoint is computed live by design. As
real time drew away from `NOW`, the seven-day window slid off the fixture
data. The confidence test went first, at the 3.5-day mark reached on
2026-08-11, where a seven-day run of checks stops covering half the window
and `_confidence` correctly downgrades to `low` — **the scorer was right
and the test was wrong**. The other eight had until 2026-08-14, when the
run would have left the window outright and all nine would have failed at
once, in whichever session happened to be open.

An autouse fixture pins the route's clock to the same `NOW`. `datetime` is
used exactly once in that route module, so the patch is narrow, and the
route can no longer observe wall-clock time at all.

## Decisions and what was rejected

- **Session 30 was closed rather than built.** Rejected: building it in
  Alfred anyway (overrides an accepted ADR, jumps its row 134, and lands
  on a dirty tree carrying an unrelated career-correspondence feature);
  and re-opening ADR-0064 on the strength of the expired premise below
  (the premise is genuinely dead, but it is a *reason*, not a *trigger*).
- **The expired premise is recorded, not acted on.** ADR-0064 §3 declines
  to design against `GET /api/projects/next` because "it returns 404
  today" and its ranking is "undecided by its own author". Session 29
  shipped it on 2026-08-10 with a decided, documented ranking. That
  retires a stated reason and moves neither trigger — which is the whole
  discipline of a counted deferral: it is re-opened by the count, not by
  an argument. Written into the tasks.md row and guide §0 so the next
  reader of the ADR does not re-derive it.
- **The two commits were kept separate**, and the test fix went first. It
  is not Session 38's defect and dating it to Session 38's commit would
  put a wrong date on when the bomb was armed.
- **The clock was pinned rather than the fixtures re-anchored to real
  time.** Anchoring `_checks` to `datetime.now(UTC)` for endpoint tests
  would also have worked and is smaller, but it leaves the file with two
  clocks and a reader wondering why some calls pass `end=` and others do
  not. One clock is the fix; the drift was the symptom.

## Blocked / waiting on

- **The daemon restart is the next action and needs `sudo`.** Owed since
  2026-07-24. Session 38 measured the cost; this session added a third
  session's worth of invisible work to it.
- **Session 30 is closed until a trigger fires**, and nothing runs those
  triggers automatically. ADR-0064 §Consequences admits this: they are
  recorded on Alfred's monthly retro row (E-T4) as a named re-check, "no
  stronger than the retro habit itself". Nothing on *this* side checks
  them either, and a scheduled check is not obviously worth building for
  two numbers on an endpoint that already ships.
- **Alfred's ADR does not record its own expired premise.** Doing so is a
  one-paragraph amendment in Alfred's repo, which has an unrelated feature
  mid-flight and its own next action (row 134). Deliberately not done from
  here; it is the sibling repo's session to take.
- `SNAG-ROADMAP-002` remains open: `count_open_snags` reports 7 for the 5
  open snags in this repo's own list.
- Session 38's three follow-ups stand, including `handoff_path` on
  `ProjectBoardEntry`.

## State

Branch `main`, two commits pushed to nothing (no remote configured for
this work): `99fe1b6` the test clock fix, `8dc8759` Session 38. Suite
**1701 passed**, ruff and mypy clean, 56 routes unchanged. Uncommitted at
the time of writing: `docs/roadmap/tasks.md`, `docs/roadmap/STATUS.md`,
`docs/guides/alfred-projects-page.md` and this file — all documentation,
all this session's. `docs/guides/monitorable-project.md` still carries the
edit from before Session 38 that claims port 3300 for venture-assistant's
frontend and moves the free marker to 3400; it is a coherent complete
change, it belongs to whoever made it, and it has now survived two
sessions untouched — commit it or drop it.
