# Handoff — 2026-08-27

## Next action

Write the twenty-first check against `SNAG-SVC-002` — the `timer_stale` recommendation asks `stalls.py`'s "has it run?" about a timer, with no ladder and no cross-reference — and note that rule 1 is the whole difficulty and the reason this entry has been runner-up three times without being taken: the two families are disjoint today only because no agent on this box is a systemd timer, which is a property of the box rather than of the design, so a check measuring the disjointness would report the entry fixed on a day nobody had touched the code; the mechanism is the claim that a timer-backed agent would be judged by both families at once, which needs a synthetic agent whose schedule is a timer — the treatment `check_dropin_blind_spot` gives a drop-in and `check_unmarked_sentence_invisible` gives a block sentence, now three checks built the same way and the shape to copy.

## Session 98 is complete — the twentieth check, and the first that measures a silence

`SNAG-ESTATE-012` is **checked and stays open**. Checked entries
**17 → 18**, unchecked **7 → 6**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **70 entries / 24 open** both
times. Suite **2619 → 2635**, `tests/test_snag_claims.py` **215 → 231**.

**Every other check in this registry looks for something and reports
whether it is there. This one reports that a sentence reaches nothing.**
`check_unmarked_sentence_invisible` builds a printed region in the shape
of the sub-session block, carrying **two** sentences — one a pattern can
reach (`**7 routes**`, with `<!--check:routes-->` beside it) and one of
the entry's own three unmarked instances — and drives the real
`ops_claims.check_all` over both documents.

### What the sitting settled

- **The marked half is the witness, and that is the whole design.** An
  absence is what a broken probe produces for free: a reader that had
  stopped cutting the region reports the unmarked sentence *exactly* as
  a working one does. Both halves of the convention are witnessed
  because they fail apart — the figure coming back out of the prose is
  `read_claim`, the absence of an `unclaimed:` finding beside it is
  `read_markers` reaching the marker, and the marker half is the one
  both refused remedies would have had to extend.
- **It is a check that the invisibility holds, never a marker built to
  close the entry.** The entry names both obvious remedies and refuses
  both by name; rule 2 forbids this module authoring the document in any
  case.
- **Two instruments, because the two shapes a fix can take are invisible
  to each other.** A finding reading *"blockquote paragraph 2 carries no
  marker"* names no sentence and slips past a word search; a fix folded
  into an existing claim's note adds no key and slips past a projection
  of the report. Both are driven as real stand-ins wrapping the real
  `check_all`, with two further shapes — a `CLAIM_PATTERNS` entry grown
  to reach a specimen, and a colliding sentence.
- **A difference the sentence cannot explain is `unknown`, never
  `mismatch`.** `open_titles` states its `documented` over the live
  alert table, so two drives 0.4 s apart can honestly disagree.
  The direction rule is what makes that safe rather than a shrug: a
  sentence can only change what of a block is readable, so `None →
  value` and `value → None` are the sentence and `value → other value`
  is the box.

### Two falsifications corrected the check rather than the entry

- **The collision stand-in found the draft's ordering wrong.** It
  re-witnessed every drive, so a sentence restating the block's figure
  differently — `read_claim` refuses two distinct matches rather than
  resolving them — tripped the witness and came back `unknown` as *"the
  probe could not be driven"*, which is the wrong verdict in the
  dangerous direction for a sentence that had visibly been read. Once
  the baseline has witnessed the reader, a witness that fails on the
  specimen **is** the sentence, and a remedy refusing a region with an
  unmarked paragraph lands there too.
- **A constant moved because an instrument was silently dead.** At a
  five-character floor the middle specimen yielded no distinctive word
  at all — `8400` is four characters, and `answers` is already the
  subject of the `/health` claim — so one of the three was covered by
  the projection alone and nothing said so. That is this entry's own
  symptom arriving inside its own check. The floor is four now, three is
  refused in the other direction, and an unquotable specimen is named.

### Found on the way, without looking for it

The block's *"sixteen written, fourteen in the registry"* had been four
sittings stale — it is **twenty** and **eighteen** — which is the
**third** live instance of `SNAG-ESTATE-012` this dashboard has produced
in three sittings, after Session 97's 15/9 and Session 93's 10/14. Like
both of those it carries no figure any pattern holds and no marker any
check can be pinned to, so the check written this sitting cannot reach
it by construction. Corrected by hand, because that is what the entry
says this class costs.

### State of the box

`sysadmin` restarted at **2026-08-27 13:49:21**, `/health` **200**,
`alembic current` **016** at the packaged head, `alerts` holds **1**
unresolved row (`info: Weekly disk review ready`). `check-ops-claims.sh`
green on all nine claims; `check-snag-claims.sh` reports all eighteen
checked entries still holding and names the six that carry no check.
The restart was taken rather than argued with for the reason Sessions 81
and 84–97 took theirs: only `sysadmin/snag_claims.py` moved, which the
daemon does not import, and correcting the artefact the script names
beats hand-verifying that it is wrong.
