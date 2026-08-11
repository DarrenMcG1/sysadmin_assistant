# Handoff — 2026-08-11

## Next action

Take Session 31, idle nudges, which is the one item in the projects arc that today's ADR-0064 finding leaves untouched because it is a sysadmin-side notification over severity thresholds, DND windows and the tray that all already exist, and which needs nothing from Alfred.

## Done at the end of this session: the restart, and what it was actually owed for

`sysadmin.service` was restarted at 05:44 and is healthy. Session 37's
`build_narrative_history` is live — `GET /api/projects/ImbaBots` now
returns history points carrying `next_action` and `next_action_changed`.

**Half of the next action this session inherited was already false when it
was written, and the unit file says why.** It asserted that stored
snapshots lacked `handoff_path` and `handoff_duplicates` *because* the
running daemon predated Session 37. Those are independent facts:

- `sysadmin.service` is long-running uvicorn. Python binds imports at
  start, so the editable install still serves whatever code existed when
  the process began — this genuinely needed the restart.
- `sysadmin-organiser.service` is `Type=oneshot` off a daily timer, from
  the same editable venv, so it picks up new code on its **next run**. It
  ran at 04:33 today and wrote both keys for every project — about an hour
  before the restart, and without needing one.

`sysadmin-organiser.service` carries the comment "Needs the database, not
the monitoring daemon... the two are independent by design", which is
exactly the fact the next action welded into a single causal claim. The
snapshot half resolved itself overnight; only the API half was ever
waiting on a human with `sudo`.

**A wrong probe nearly hid this.** The first check was
`findings ? 'handoff_path'`, which is false for every row because the keys
nest under `findings->'roadmap'`. Session 38's handoff reports the same
absence and may rest on the same mistake — its claim was true of the
snapshot it named, which predated the code, so the conclusion held and the
evidence may not have. **Probe the nested path**:
`findings->'roadmap' ? 'handoff_path'`.

Also committed: `docs/guides/monitorable-project.md`, venture-assistant's
own claim on port 3300, verified against `dashboard/package.json`
(`nuxt dev --port 3300`) before landing. Nothing listens on it yet, which
matches the row's "dev server for now; unit to follow".

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

- **The daemon restart is done** (05:44 today, owed since 2026-07-24) —
  see the section above for what it was and was not owed for.
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

Branch `main`, four commits: `99fe1b6` the test clock fix, `8dc8759`
Session 38, `6774eaf` the Session 30 decline, `d50004d` the port-3300
claim. Suite **1701 passed**, ruff and mypy clean, 56 routes unchanged.
`sysadmin.service` restarted 05:44 and healthy; `sysadmin-organiser.timer`
next fires 04:30 tomorrow. Working tree clean apart from this file.
