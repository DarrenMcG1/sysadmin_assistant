# Handoff — 2026-08-25

## Next action

Write the next `snag_claims` check and pick it by what a wrong answer costs — `SNAG-LOG-013` first, because it is the entry whose whole argument is that an empty population is not a closure and so it is the one whose check most needs the mechanism rule applied, and because eighteen of twenty-six open entries still carry none.

## Session 84 is complete, and `snag_list.md` has the reader `STATUS.md` has

`sysadmin/snag_claims.py` is the fifth composition root. An open entry
names the check that would refute it — `check:<key>` as an HTML comment in
the entry's **body** — and `sysadmin-check-snags` runs it at the start and
the close of every sitting, beside the ops claims.

Measured live: **8 of 26** open entries are checked, **all eight claims
still hold**, and the other **18** are named and counted rather than left
silent. estate-manager's parser reads **69 entries, 26 open, dialect
`bullet`** either side of the edit, so the markers moved nothing the board
publishes.

**2449 tests pass** (2398 + 51). Ruff clean, mypy clean. The daemon was
restarted at **21:42:24** and `/health` answers 200 — nothing it imports
changed, and the restart was taken rather than argued with because
`check-ops-claims.sh` cannot know that.

## What was decided, and on what evidence

**A check tests the entry's *mechanism*, never its *population*.** This is
Session 83's residue/population rule read as an instruction to the check
author, and getting it wrong would have made the machinery close the one
entry the last two sittings argued must stay open. `SNAG-UNITS-006`'s
population is measured empty — zero of the 38 swept units carries a
drop-in — so a check that looked for one refutes it on the day it was
filed. `check_dropin_blind_spot` **builds** a synthetic unit whose drop-in
overrides `RestartSec=`, sweeps it, and compares: reproduced rather than
counted, which is Session 82's `SNAG-ROADMAP-001` treatment.

**A refuted claim is a candidate for closure and never a closure**, so
nothing in this family writes to a document and neither script blocks on
it. Session 83 spent a whole sitting on one such judgement; a check that
made it automatically would be the second author the convention exists to
keep out.

**The marker lives in the body and never in the title**, because the title
is estate-manager's input: `_trailing_parenthetical` requires it to end in
`)` before it will look for a closure clause at all. Verified rather than
argued — the board's parse is identical either side.

**The marker names a check and the check names its entry, pinned rather
than derived.** Before the eight markers were added, the pin reported all
eight checks orphaned, which is its falsification.

**The instrument decides more than the rule does.** `grep review_hour`
matches `log_review_hour`, `disk_review_hour` and `health_review_hour`,
all three of which *are* read, so a grep-shaped check reports
`SNAG-CFG-002` refuted on its first run. `ast.Attribute.attr` is the exact
final segment. The falsification points the same walk at `log_review_hour`
deliberately, where it finds the two real readers — third time here that a
substring has stood in for a measurement.

**The open set is read here and pinned against its owner.** `read_snags`
is in `estate_service` rather than `estate-lib`, so the closure rule is a
second implementation. Narrowed to under-report closure, so the error
direction is *more* entries reported unchecked; pinned by a test that
shells out to estate-manager's venv and skips when it is absent.

## What the live run found that no fixture would have

- **Two checks nobody implements, `helth` and `routes`**, both "named by
  `SNAG-ESTATE-011`" — an entry that names neither and merely **quotes**
  them, one deliberately misspelled. This document is the one place on the
  box that writes *about* markers. `strip_code_spans` is the fix;
  `SNAG-DOCS-005` is `ops_claims`' latent copy, measured empty (9 markers
  in its region, none quoted) and deliberately not fixed there.
- **The doubled fence.** `SNAG-DOCS-005`'s own body quotes a marker inside
  a two-backtick span, and a pattern closing on any backtick run stops at
  the inner single one. Markdown's same-length rule, learned by watching
  the check report the marker it was describing.
- **A marker used to state an absence.** `SNAG-ESTATE-014` was first filed
  with `check:none_yet`, refused within a minute: a marker names a check,
  and "there is no check" is not one.
- **The sitting's own defect.** The board pin was first written `assert
  theirs["total"] == 67` — a measured figure inside a test, stale the
  moment this sitting filed two entries, which is `SNAG-ESTATE-008`'s
  shape inside the guard built to answer it. It now pins the agreement
  between two readers instead.

## Filed rather than absorbed

- `SNAG-ESTATE-014` — eighteen of twenty-six open entries carry no check.
  Measured on every run by `convention:unchecked`, which is the thing it
  is about. Four are delegated and several are judgements rather than
  measurements, so the shape of a fix is one check per sitting.
- `SNAG-DOCS-005` — `ops_claims` would read a quoted marker as a real one.
  Empty population today, and stated in `STATUS.md`'s own block, which is
  why that block deliberately does not quote its own syntax.
- Estate message **`3986f323`** — `read_snags` is not importable.

## Blocked or waiting on another repository

Unchanged plus one. Session 33 is asked (`6a330427`) and awaits an answer;
`3986f323` is new and awaits one too. `SNAG-LOG-012` is delegated;
`SNAG-ESTATE-002`, `-004`, `-006` and `-007` remain estate-manager's.
