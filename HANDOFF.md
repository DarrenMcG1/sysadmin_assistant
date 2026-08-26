# Handoff — 2026-08-26

## Next action

Apply `SNAG-DOCS-005`'s three-line fix to `ops_claims.read_markers` using a code-span pattern that closes on a backtick run of its **own length**, because the twelfth check already distinguishes that fix from the naive one and reports `mismatch` only for the former, so the entry can be closed or narrowed on a run rather than on an argument.

## Session 88 is complete — the twelfth check, and the entry that was paying its own cost

`SNAG-DOCS-005` names a check now: `check_quoted_marker_reads_as_real`
in `sysadmin/snag_claims.py`, with `ops_probe`, `survey_quoted_markers`
and `MarkerSurvey` beside it. It is the twelfth written and the
**eleventh live**, and the first whose subject is this repository's
*other* claims-checker rather than the box or another repository.

Checked entries go **10 → 11** and unchecked **15 → 14**; all eleven
still hold. **2484 tests pass** (2470 + 14). Ruff clean, mypy clean.
estate-manager's `read_snags` reads **69 entries and 25 open** either
side of the edit. The daemon was restarted at **12:16:23** and `/health`
answers 200 — `snag_claims.py` is the composition root the daemon does
not import, so for the fifth sitting running nothing a caller can
observe moved, and the restart was taken rather than argued with for the
reason Sessions 81 and 84–87 took theirs.

### The mechanism is local, so it was reproduced rather than counted

`ops_claims.read_markers` matches its own syntax over the flattened
region with no regard for markdown code spans. The check builds a
`STATUS.md` in miniature and drives the real `printed_region` →
`read_markers` → `check_markers` over it — rule 1, because the entry's
population is empty and a check that looked for a live member would
report it refuted on the day it was filed.

Three shapes, because the defect is quiet in three ways: a quoted key
nothing implements **invents** a broken-marker finding; a quoted key
that *is* implemented **silences** the unclaimed-figure finding beside
it; and the same quotation inside a **doubled fence**. The first two are
opposite in sign, which is what the entry means by quiet in both
directions. A control region runs first, since direction two is read off
a *missing* finding — the same absence would follow from the pattern
moving, the region not parsing, or the convention being retired, and
only the control tells those apart.

### The third shape earned its place by measurement

Both obvious three-line fixes pass the single fence. Only a code-span
pattern closing on a backtick run of the same length survives the
doubled one — the shape `SNAG-DOCS-005`'s own body carries. Driven, the
naive alternative closes at the inner backtick and leaves the marker
bare, so a probe testing one fence would have reported that fix a
**clean closure**. `check_nudge_wording_unpublished`'s third field one
check over, for its reason.

Hence the verdict asymmetry, which is stated rather than inherited: any
shape still leaking is `match` with a narrowing note, never `mismatch`.
An entry is refuted when the defect is gone, not when some of it is, and
a half-fix reported as "candidate for closure" hands the next sitting a
closure it has not earned.

### The entry's account of its own empty population was wrong, and so was the first correction

The entry reads its emptiness as a property of how the block is written
— *"the block is written to be read, not to teach the convention"*. The
first correction drafted here said that was simply not the reason, on
the strength of STATUS.md teaching the convention four times. **Reading
the block refuted that before it shipped**: it carries *"One thing this
block deliberately does not do: quote a marker"*, names this entry, and
sends the reader to `sysadmin/ops_claims.py` *"where quoting it is
safe"*.

So the emptiness is an **avoidance**, and the cost the entry files as a
future sitting's confusion is already being paid — as a sentence the
dashboard cannot write. That is `verify-ops-claims-live` applied to a
document rather than to the box, and it is the reason this sitting's
correction is a refinement rather than a contradiction.

### Nine lines is the margin, and it named a check retired that morning

Beyond the block the printed region runs to 270 lines, and its far end
is empty only by placement. The nearest quoted marker sat **9 lines**
past the last line and named `handoff_apology_published` — the check
Session 87 correctly removed with `SNAG-ROADMAP-001` that morning. So
the *inventing* direction has a live member nine lines outside the
region, and a `## ` heading added above it closes that margin with
nobody intending to.

The figure is recorded as **history rather than as a claim**, in both
the entry and STATUS.md, because this sitting's own Recently Completed
section pushed it to **76** within the hour. The check prints the live
distance on every run, which is the only place that number belongs.

### What was falsified, and the one guard that is a blind spot

Four mutations were driven and every one fired: `_quoted_only` as a set
difference, the doubled-fence probe removed, and the survey's stripper
disabled on each of its two halves separately.

`test_the_live_region_carries_no_quoted_marker` is stated as a **blind
spot** instead of dressed up as a guard — a stripper that stopped
stripping produces its zero too, confirmed by driving exactly that edit
and watching it stay green. The falsifiable half is
`test_a_marker_inside_the_region_is_not_counted_as_outside`, built
rather than live for that reason, and each docstring says which.

### Filed rather than fixed

**Session 87 wrote no `### Session 87` section in STATUS.md's Recently
Completed.** Its record is `b454a50`, `HANDOFF.md` and the opening
block, so nothing is missing but the heading — and authoring another
sitting's entry retrospectively is not this one's to do. It is noted in
`tasks.md` and in the Session 88 section, which sits directly above
Session 86's for that reason.

**A first draft of this section called `SNAG-ESTATE-014`'s title stale**
for still reading "eighteen of the twenty-six", against a live 14 of 25.
The entry refuses that correction in its own body — *"the title's figure
is left as filed … the live count is `convention:unchecked`'s to
publish, which is this entry's whole argument"* — so what was added is a
**progress bullet**, 17 → 14 across Sessions 86, 87 and 88, and the
title is untouched. Two of those three were *delegated*, against that
entry's own ordering, which put a delegated claim last; the ordering
missed that being delegated is what makes a check worth having, since
the closing move happens in a tree nothing here watches.
