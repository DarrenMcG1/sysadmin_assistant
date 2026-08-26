# Handoff — 2026-08-26

## Next action

Write the thirteenth check for `SNAG-LOG-008` — reproduced rather than counted, since its ten rows leave the 7-day window by retention and the endpoint's population empties without anything being fixed — driving the real `read_journal` over one pre-declaration record and one post-declaration record to show that `unwrap_json_message` is read-time and cannot reach a stored row, and measure while there how many of the ten are recoverable from the 2000-character `raw_line`, which that entry records as unmeasured.

## Session 89 is complete — the entry closed on a run, not on the argument for it

`SNAG-DOCS-005` is **fixed and closed**, and it is the first entry this
registry has closed on a check measuring **this repository's own code**.
`sysadmin/ops_claims.py` gains `CODE_SPAN_RE` and `read_markers` strips
code spans before matching — three lines, which is exactly what the
entry's own "shape of a fix" bullet asked for.

Open entries **25 → 24**, checked **11 → 10**, unchecked unmoved at
**14**. **2476 tests pass** (2484 − 14 + 6). Ruff clean, mypy clean.
estate-manager's `read_snags` reads **69 entries** either side. The
daemon was restarted at **15:32:37** and `/health` answers 200 —
`ops_claims.py` and `snag_claims.py` are the two composition roots
nothing under `sysadmin/` imports, so for the sixth sitting running,
nothing a caller can observe moved.

### The check was written to separate two fixes, and it did

The pattern closes on a backtick run of its **own length** —
`` (`+)[\s\S]*?\1 `` — which is markdown's own rule for a span that
itself contains a span. That is the whole of why this closed rather than
narrowed. Both candidates were driven through the twelfth check **before
the entry was touched**:

- the naive `` `[^`]+` `` came back **`match`** — *"the single fence is
  handled and the doubled fence still leaks … a narrowing rather than a
  closure"*
- the same-length pattern came back **`mismatch`** — *"candidate for
  closure"*, all three probe lines reading `False` where they had read
  `True` twenty minutes earlier

A check written the previous sitting to tell two fixes apart did exactly
that, one day later. That is the difference between an entry closed on a
measurement and one closed on a plausible-looking diff.

### The check left the registry with its entry

`test_every_checked_entry_is_open` makes that a rule rather than a
choice: a refuted check on a closed entry says "go and judge this" for
ever. `check_quoted_marker_reads_as_real`, `ops_probe`,
`survey_quoted_markers`, `MarkerSurvey`, `QuotedMarker`, `_quoted_only`
and the six `OPS_PROBE_*` constants went with it, as
`handoff_apology_published`'s helpers did the sitting before.

The last measurement the survey ever took is recorded **on the entry**
rather than lost: 9 markers in the printed region with 0 quoted, 4 quoted
outside it, the nearest **76** lines past the region's end and naming the
retired `handoff_apology_published`. Session 88 measured that margin at
**9** lines; it was 76 the next afternoon. A number that never stops
moving was never a property of the document.

### What replaced it is a pin, not a gap

`snag_claims.strip_code_spans` is **still a copy rather than an import**
— two composition roots must not couple to share a regex, and a snag-list
parse must not move because the dashboard's reader was edited. So
`TestAQuotedMarkerIsAQuotation::test_the_sibling_s_copy_and_this_one_agree_shape_for_shape`
drives both over seven shapes and asserts they agree character for
character. Import where you can, pin where you cannot.

**The reason for keeping the copy was corrected mid-sitting.** The draft
argued that `survey_quoted_markers` measures `ops_claims` with its own
copy, so sharing would make the survey read the fix by definition — a
check agreeing with itself. True when written, and the same change
deleted that survey forty minutes later. An argument resting on machinery
the change itself removes is not an argument; what survives is the
coupling one the entry filed.

### The block writes the sentence it could not write

*"One thing this block deliberately does not do: quote a marker"* is
gone, replaced by a paragraph that quotes one inside a code span beside a
real marker. `check-ops-claims.sh` reports **no** `marker:` finding for
it and **no** unclaimed figure, so the fix is asserted by the artefact
the entry was about and not only by tests. A regression in `read_markers`
turns that sentence into a spurious finding at the top of the next
sitting, which is the loud direction.

### Found rather than fixed

The daemon had already been restarted at **14:48:31** by a party outside
this sitting — a clean `Stopping` → `Deactivated successfully` →
`Started`, not a crash — so the block's start time was stale before the
first edit. `check_daemon_start`'s note says *"nothing recorded why"*;
`tasks.md` and the block now do.

### Not done, and deliberately

- **No backfill, no migration, no route moved.** The change is three
  lines of production code, one constant, and the removal of a check that
  had done its job.
- **`SNAG-ESTATE-012` is untouched.** A block sentence that is neither a
  figure nor a marked prediction is still invisible, and deciding that an
  English sentence is a claim is still a human's job.
