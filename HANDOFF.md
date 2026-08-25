# Handoff — 2026-08-25

## Next action

Sweep all 30 entries the parser now reads as open in `docs/roadmap/snag_list.md` against the live box and add the machine-readable closure marker to every one already fixed, because five were measured dead in ten minutes this sitting — `SNAG-AGENT-003` (44 file-organiser runs, latest 16:01 today, against "run once in its life"), `SNAG-AGENT-004` (2 unresolved alert rows in the whole table, against 26,270), `SNAG-ESTATE-001` (zero `personalassistant*` unit files on the box), `SNAG-DB-002` (zero stale collations) and `SNAG-PROJ-013` (ImbaBots' handoff now heads `# Handoff — 2026-08-24`) — so the estate board is publishing three P1s and two P2s for this repository that do not exist, and `STATUS.md`'s own claim that "every known-fixed entry now reads `is_open=False`" is false for five entries it never checked.

## Session 81 is complete, and the entry it closed undercounted the thing it asked to be deduplicated

`SNAG-DOCS-004` is **fixed**. Two Tier 3 docstrings claimed their prompt
"contains no digit by construction" and both prompts carry `1`, `2`, `3`
and `150` — the section numbers and word cap in their own
`REVIEW_INSTRUCTIONS`. The behaviour was right and the sentence was not:
rule 2 was always about the *data* half, so both now state the narrow
claim and name the half they do not cover. `health_review`'s was
reworded too — it carried a present-tense description of the siblings'
defect, which becomes a stale sentence the moment the defect goes away.

## What was decided, and why

**The entry asked for *the* partition helper to be shared and there was
no such thing.** The rule was written three times and the three had
diverged, in two places, each with a right side:

| | strips API paths | asserts the boundary was found |
|---|---|---|
| `test_disk_review._data_lines` | ✅ | ❌ |
| `test_log_review._data_lines` | ✅ | ❌ |
| `test_health_review._data_half` | ❌ | ✅ |

So `tests/review_prompts.py` is the **union**, not any one of them.
Deduplicating onto whichever copy a reader opened first would have
silently dropped a live guard — which is the part of this shape the
handoff's framing could not see, because it had only looked at two of
the three.

**The API-path strip is a no-op today and is kept as policy.** Measured
across all three live fixtures: exactly one data half contains an API
path at all (`POST /api/files/clean/downloads`) and it is digit-free. It
earns its place the day a route is versioned. Stated as untriggered
rather than implied to fire.

**`split(instructions)[0]` was not a false green, and saying so is the
point.** With no instruction block there are no instruction digits to
exclude, so the digit test passes for a *stricter* reason. What it did
was return the whole prompt while being called "the facts half" —
`ports_checked`'s rule one directory over, where zero-because-clean must
not be served as zero-because-blind. `data_half` asserts the marker
instead, and `tests/test_review_prompts.py` pins the old form's
behaviour beside the new one so the reason survives the copy that
carried it.

**Nine tests exist so the shared assertion can be seen to fail**, one
per rule plus two boundary cases, each driven at something that must
break it before it was written down. A shared guard that never refuses
anything is worth less than the three copies it replaced, because a copy
at least had a reader.

**Deliberately not done**: no digit was stripped from any
`REVIEW_INSTRUCTIONS`. The model needs the section numbers to produce
sections and the word limit to stop — the entry's own instruction, and
still right.

## The correction this sitting made to itself

The note explaining why the API-path strip is left greedy first read
*"no route on this service takes a query string"*, written from
plausibility. One `grep Query(` refuted it — `/api/logs/recent` alone
takes five. That is `SNAG-DOCS-004` reproduced inside its own fix: a
sentence about behaviour written without measuring it. The note now
states what was measured — the executors that reach a prompt are
hand-written literals in `files/recommendations.py`, every one a bare
path followed by a space. `CLAUDE.md` carried the same wider claim one
document up and was corrected in the same sitting.

## Numbers, measured rather than carried forward

- Suite **2388 → 2398**, all green. Routes unmoved at 51, head unmoved
  at 016, ruff and mypy clean.
- Snag parser: **67 entries, 31 → 30 open**, measured either side of the
  edit by driving estate-manager's `read_snags` over the file. **Second
  consecutive sitting whose closure the parser can see**, the first two
  since estate-manager fixed `SNAG-ROADMAP-002` on 2026-08-24.
- Production diff is **docstrings only** across three files, so nothing
  a caller can observe moved. The daemon was restarted anyway at
  **16:21:01** — `check-ops-claims.sh` compares the daemon's start
  against the newest source mtime and cannot know a diff is prose, and
  the rule in `STATUS.md`'s own block is to correct whichever artefact
  the script names rather than hand-verify that it is wrong. All nine
  ops claims pass.

## What is blocked

**The Session 33 question is routed and unanswered.** Seam drift
detection cannot start here because its second task reads another
repository's fixture off the same disk. The question was written into
estate-manager on 2026-08-24 (commit `7171788` here); their roadmap
carries no answer as of this sitting, and they have committed five times
since. Named as blocked rather than dropped — this is the eighth
consecutive ranking it has appeared in.

## Next session, ranked

1. **The closure-marker sweep** (above). Cheap, and it is the only item
   whose cost is being paid by a *different* repository's published
   board every day it stands. Four confirmed dead in ten minutes of
   `psql`, `systemctl` and one `head -1`; twelve of the thirty have a
   body that already mentions a fix, so the five found are a floor and
   not the population. Note the fifth was found **by measuring something
   else** — checking item (2)'s population meant opening every handoff
   on the box, and one of them refuted a P2.
2. **`SNAG-ROADMAP-001`** — an unfilled handoff placeholder is published
   as a real next action. Same family as (1) and the same consumer, but
   **its population is zero today, measured rather than assumed**: all
   nine handoffs under `~/projects` were opened this sitting and every
   one carries a real heading and a real next action. It loses to (1) on
   being dormant, and the measurement is what makes that a ranking
   rather than a guess.
3. **`SNAG-ESTATE-002`** — the estate's `Nudge.title`/`.message` are
   `@property` and `asdict` drops them, so this repository builds a
   format the estate believes it owns. Loses to both because the fix is
   estate-manager's and the ask has to be routed, which is the position
   item (1)'s blocker is already in.
