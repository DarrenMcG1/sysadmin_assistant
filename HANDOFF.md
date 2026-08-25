# Handoff — 2026-08-25

## Next action

Decide `SNAG-ESTATE-008` rather than measure it — its narrow half is fixed, its general case became `SNAG-ESTATE-011` which is fixed, and what is left of that is `SNAG-ESTATE-012` which is filed and open, so nothing of its own remains and the only open question is whether closing a chain counts as a closure.

## Session 82 is complete, and the board no longer publishes a P1 for this repository

**Five entries were dead on the box and the estate was publishing all
five** — three P1s and two P2s. All 30 open entries were measured against
the box rather than read:

| Entry | Claim | Measured |
|---|---|---|
| `SNAG-AGENT-003` (P1) | "run once in its life" | **45** runs, latest 16:22:03 |
| `SNAG-AGENT-004` (P1) | 26,270 unresolvable rows | **2** unresolved rows in the table |
| `SNAG-ESTATE-001` (P1) | two units restart-looping | **0** `personalassistant*` unit files |
| `SNAG-DB-002` (P2) | every database stale | **0** stale collations |
| `SNAG-PROJ-013` (P2) | handoff has no ISO date | `# Handoff — 2026-08-24` |

The live parser reads **30 → 25 open** with the entry count unmoved at
**67**, measured either side of the edit by driving estate-manager's
`read_snags`. Three of the five had been fixed for between nine and
thirteen days.

## What was decided, and why

**The closure goes in the title parenthetical, and only there.**
`read_snags` splits that parenthetical into clauses and requires a done
word at the **start** of one. `SNAG-DB-002` carried **three** closure
statements and still read open, because `check half **fixed
2026-08-13**` starts with "check" — it is the named example in the
parser's own docstring, so this was documented drift and not a parser
defect. Every closure here is also written as a body bullet carrying the
measurement, because the marker says *that* it closed and the bullet says
*what was measured*.

**The predictor behind this sitting's own ranking was wrong.** Session 81
called five a floor on the grounds that twelve of thirty bodies mention a
fix. There are **14**, and **eight of them are alive** — because this
repository's convention is that a new entry is *named by the fix that
created it*, so a fix-word usually points at the entry's **parent**
(`SNAG-LOG-006` names the fix that opened it, `SNAG-ESTATE-013` the check
it annotates). Five was the whole population. That is the second ranking
here built on a grep answering the adjacent question; `SNAG-DOCS-002` was
the first.

**Three entries were re-measured and stay open**, which is what makes the
five worth anything rather than a document tidied toward zero:

- `SNAG-SYSD-003` holds verbatim — `ollama.service` is
  `LoadState=not-found` and still named in `sysadmin.service`'s `After=`.
- `SNAG-ROADMAP-001` was **reproduced**, and the reproduction refutes its
  own stated cause. The detector *is* wired into the "next" heading path
  now, and it **cannot fire**: `_first_meaningful` strips the italic
  markers before testing and `is_placeholder` keys on them —
  `is_placeholder(raw)` **True**, `is_placeholder(naked)` **False**. A
  guard that runs on every candidate and can reject none is worse than
  the absent guard the entry describes, because a test written against
  the normalised string is green for ever.
- `SNAG-LOG-013`'s population is **empty** at the live endpoint and it
  **stays open**, because "population is currently zero" is precisely
  what mis-ranked its parent `SNAG-LOG-010`.

**`STATUS.md` carried a false verification and it is corrected.** It said
estate-manager's parser fix made *"every known-fixed entry read
`is_open=False`"* — true, and it tested the **mechanism** rather than the
**document**. Measuring a parser against entries you already believe are
fixed cannot find the entries you believe are open and are not.

## Blocked / owed

- **`SNAG-ROADMAP-001` is estate-manager's** since ADR-0005 and was
  **filed rather than absorbed**: message `e0461fe9`,
  `sysadmin-assistant → estate-manager`, carrying the reproduction and the
  suggested fix. This repository has been publishing an entry it cannot
  fix since 2026-08-13. Nothing here is blocked on the reply.
- **The Session 33 question** remains asked and unanswered — message
  `6a330427`, filed 2026-08-25.
- **`SNAG-ESTATE-008` is deliberately undecided.** Closing it is a
  judgement about a chain rather than a measurement of the box, and the
  parser's author wrote the trade down: an entry left visible costs a
  reader a glance, an entry closed by a misread manufactures a clean row.

## What this sitting did not build

**Nothing checks that a snag's claim still holds.** `ops_claims.py` does
exactly this for `STATUS.md`'s opening block — five figures, each naming
the check that closes it — and the five entries closed here are that same
defect one document over, at thirteen days and three P1s. The hard half
is the same one `SNAG-ESTATE-012` names: deciding that an English
sentence is a claim is a human's job, and most snag titles are prose. The
tractable half is the family this sweep actually used — an entry whose
claim is a **count** or the **existence of a file, unit or row** — which
is 5 of the 14 fix-mentioning entries and would have caught all five of
today's on the day they died.
