# Handoff — 2026-08-06

_Hand-written, replacing the SessionEnd hook's auto-generated version.
That one was stale: it listed files as uncommitted that Session 28 has
since committed, and its "Next action" was a truncated sentence
fragment. Note this file is now **machine-read** by
`sysadmin/services/roadmap.py` — the first line under `## Next action`
becomes this project's next action on `GET /api/projects/board`, so keep
it one concrete sentence and never a placeholder._

**Branch:** `main` · **HEAD:** `5d33c61` · **Working tree:** clean ·
**Suite:** 1276 passing, ruff clean, mypy clean, `alembic check` clean

## Next action

Start Session 26: build the unmonitored-unit detector, cross-referencing installed systemd units against projects.yaml.

<!-- Keep the line above as ONE line and a complete sentence:
     roadmap.py takes the first non-empty line verbatim, so a
     hard-wrapped sentence is published to the board truncated. -->

It is the one directly requested, the smallest of the remaining
sessions, and validating it needs nothing built first: `garmin-sync`,
`deadlock-api-ingest`, `ticktick-sync` and `offline-agents-dashboard`
are all uncovered right now, and the eight dead `personal-assistant-*`
units are still installed as orphans. `sportsanalyser-*` was wired by
hand on 2026-08-05, so it should come back clean — a good negative test.

## What landed today

Two independent sessions committed to `main` today. **They were written
separately and neither knows the other's detail** — if something looks
inconsistent between them, that is why.

**Session 24 (mine — `2edfe42`, `e0f612a`)** — file-organiser tiers, all
three complete. Detail in
[tasks.md](../roadmap/tasks.md).

**Session 28 (`5d33c61`, a different session)** — roadmap findings, the
estate board, `GET /api/projects/board`, and a projects.yaml triage that
declared seven projects dormant and archived two. It also introduced
`services/roadmap.py`, which is what now parses this file.

## Session 24 — the three things worth carrying forward

1. **Mocked tests could not see either real bug.** Both Tier 2 defects
   were invisible to the suite because mocks supply the findings dict
   directly and never exercise what *storage* did to it. The `findings`
   blob is truncated to 50–100 entries per category before it is written,
   so the endpoint reported 200 misplaced files against an actual 11,877
   — a 60× understatement — and duplicates/downloads recorded no sizes at
   all, making the reclaimable-megabytes currency uncomputable. Both
   fixed; the true counts were sitting unused in the audit row's own
   columns the whole time.

2. **"Never let the model produce numbers" is a constraint on the
   prompt, not an instruction to the model.** This is the correction to
   Session 23's rule and the most reusable thing here. Given a prompt
   listing "25.0 GB across 50 directories" *and* an explicit "do not
   restate any figure", dria-agent-a-3b restated them and then invented
   **"each consuming 5GB"** — a quotient derived from data the prompt
   itself had supplied. Instructing a model not to use a number it can
   see is a request; not showing it one is a constraint.
   `build_review_prompt` is now figure-free by construction, guarded by a
   test asserting no digit reaches the model outside API paths. **Any
   future Tier 3 should start from the figure-free prompt, not from the
   instruction.**

3. **Two tables, deliberately.** `filesystem_audits` measures junk
   accumulation; only `resource_snapshots` measures disk occupancy. A
   week where reclaimable junk grew 3 GB while occupancy fell is a
   different story from one where both rose, and neither table alone can
   tell them apart. That is why `/api/files/actions` and the disk review
   both read across the two.

## Known-imperfect, deliberately left

- [ ] **The disk-risk detector cannot currently fire.** July's cleanup
      took usage 92.8 % → 67.3 %, so the 30-day least-squares fit reads
      `not_growing` on both thresholds and no risk item is raised. The
      behaviour is *correct* for the maths as specified; the weakness is
      that one large cleanup blinds the detector for a month. A shorter
      secondary window, or fitting only since the last sharp drop, would
      catch a resumption sooner.
- [ ] **The 3B model ignores the 150-word limit** — the final live disk
      review ran ~350 words. Honest prose with no invented figures, so
      this is cosmetic, but the briefing section is longer than intended.
      Truncating mid-sentence would be worse; a smaller `n_predict` or a
      summarise-again pass is the fix.
- [ ] **`SNAG-AGENT-002`** (log aggregator raises one alert per error
      line) stays open on purpose — it is owned by Session 27, because
      the signature fingerprinting that fixes it is also that session's
      Tier 1. Patching it separately would do the work twice.

## Side effect you should know about

Live-testing the review endpoint started a scheduler on port 8599, whose
`file_organiser` first-run fired at **12:05 today** and wrote a fresh
audit row. Benign — a read-only walk of `~` — and useful, because that
row is the first to record sizes, which is why reclaim now prices at
**43.6 GB** rather than "unrecorded". The real service on `:8500` was
never touched. Both test servers are stopped.

## Verify before trusting any of the above

```bash
git log --oneline -3          # expect 5d33c61, e0f612a, 2edfe42
uv run pytest -q              # expect 1276 passed
curl -s localhost:8500/api/files/actions | head
curl -s localhost:8500/api/files/review | head
```
