# Handoff — 2026-08-25

## Next action

Give `snag_list.md` the reader `STATUS.md` already has — an entry's claim names the check that would refute it, and something runs it — because Session 82 measured all 30 open entries by hand and found five dead on the box, three of them P1 and three fixed for nine to thirteen days, which is `SNAG-ESTATE-008` one document over.

## Session 83 is complete, and `SNAG-ESTATE-008` is closed

The call Session 82 deferred is taken. The live parser reads **25 → 24
open** with the entry count unmoved at **67**, measured either side of the
edit by driving estate-manager's `read_snags` over the file.

**No code changed.** Nothing under `sysadmin/` was touched, so no restart
is owed and no test was added. `tests/test_ops_claims.py` (58) and the
four other suites that read the roadmap documents were run because the
`STATUS.md` block was reworded — 189 passed.

## What was decided, and on what evidence

**The rule: an empty *residue* is a closure; an empty *population* is
not.** That is the distinction Session 82's sweep needed and did not have.
`SNAG-LOG-013` stays open on an empty population, because its claim holds
again the moment the population refills. A residue cannot refill. So
**closing a chain is not a closure** — what closes an entry is having
nothing left that it *uniquely* names and nothing owns.

**The test is the entry's own three founding instances, driven live.**
Not the state of `SNAG-ESTATE-011`, which is somebody else's evidence.

| Founding instance | Caught by | Falsified how |
|---|---|---|
| The restart already done | `check_daemon_start` | Backdated the block to `2026-08-22 09:00:00` → *"it has restarted since the block was written, and nothing recorded why"* |
| The `REINDEX` already done | `check_alerts` | Raised `holds **2**` to `**9**` → *"7 fewer unresolved row(s) than the block accounts for…"*, a note that **ends `(SNAG-ESTATE-008's founding case)`** |
| The five orphan removals | **nothing** | `measure_unit(unit: str = OWN_UNIT)` has **one** caller and it passes the default |

**The third instance is `SNAG-ESTATE-012`'s class exactly, and that is
what makes the residue empty rather than merely small.** No check resolves
an arbitrary unit — but the sentence that would carry that action has no
figure and no marker, which is ESTATE-012's symptom verbatim. The residue
has an owner, and a narrower statement than ESTATE-008's.

**Leaving it open had become an instance of itself**, which is what
decides a judgement when no measurement will. The `P2` was kept for the
cost of *"sittings of ranking attention spent on settled items at the top
of the document that sets the agenda"*. Named by eight consecutive
rankings with nothing of its own to do, it was paying that cost — and
ranking its own residue two rungs louder than `SNAG-ESTATE-012` ranks it.

**Two entries describing one open defect is refused everywhere else
here**, and these two already disagreed about severity.

**The counter-argument, rejected rather than ignored.** Session 82
deferred on the parser author's trade — *an entry left visible costs a
reader a glance, an entry closed by a misread manufactures a clean row.*
That governs a **misread**, and this is not one. Session 82's reasoning is
left in place in the header and marked as taken, not rewritten.

## What the sitting found while closing it

**The block demonstrated the residue mid-closure.** `STATUS.md`'s
sub-session header still read *"Owed … Named as the blocker in seven
consecutive rankings without being asked"* for the Session 33 question,
which had been filed as estate message `6a330427` earlier the same day and
was already recorded as asked **twice** further down the same document.
One block, one fact, two ways — and the stale half is the one
`claude-preflight.sh` prints first. No pattern reaches it, so it is
ESTATE-012's class; corrected by hand, which is what that entry says this
class costs. Verified against the live register on `:8400`, not against
the commit message.

## Blocked or waiting on another repository

Unchanged. Session 33 is asked (`6a330427`) and awaits estate-manager's
answer. `SNAG-LOG-012` is delegated; `SNAG-ESTATE-002`, `-004`, `-006` and
`-007` remain estate-manager's.
