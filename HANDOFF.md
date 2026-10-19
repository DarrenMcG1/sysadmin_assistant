# Handoff — 2026-10-19 (Session 388)

## Next action

Delete the older duplicate `**Last Updated**` line (2026-10-18) from docs/roadmap/STATUS.md line 3, as tasks.md Session 388 records. *(For: session)*

## Session 388: ops_claims.py stops calling the region append-only

Session 387's next action. Comments only; no restart owed.

- **`SNAG-DOCS-034` closed** in `f8ce7ce`. Three statements, not the
  two the snag listed: the third was `check_open_titles`' docstring.
  Each now says the region *was* append-only and names the archive.
- **Decided:** fix the third in the same commit, since it is the same
  file and the same defect. Rejected: also fixing the four in
  `tests/test_ops_claims.py`, which would widen the sitting past the
  file the snag named; they were done afterwards in the same session (four docstrings, test commit
  below in the log); `tests/test_claude_md_registry.py:402` stays.
- **Seen in passing:** STATUS.md has two `**Last Updated**` lines.
  Recorded as a task, not fixed.
- No estate message open.

## What Session 387 handed on

Fix SNAG-DOCS-034: put ops_claims.py's two present-tense "append-only" statements in the past tense, as tasks.md Session 387 records. *(For: session)*

## Session 387: STATUS.md's opening block is archived

Session 386's next action. Docs and tests; the detail is in tasks.md,
Session 387.

- **STATUS.md is 110 lines, down from 8,310.** The dated announcements
  went to `docs/roadmap/archive/status_opening_block_2026-10-19.md`,
  unedited but for 15 re-based links.
- **A current block holds the standing claims**, one paragraph each,
  with nine of the ten markers. The tenth (`migration_head`) sat on a
  sentence still saying head 019; the table states 021 with its own
  marker, so the sentence was archived, not restated.
- **Decided: rewrite claims in place from now on.** The block's first
  paragraph says so. Rejected: keeping a dated paragraph per sitting,
  which is how the block reached 8,242 lines.
- **Four tests assumed the block only grows.** They now read the archive
  as frozen history (`with_history` in `tests/test_ops_claims.py`).
  Rejected: lowering their thresholds, or `git show` of an old commit.
- **The alert claim was stale: 2 → 1.** `Unusual disk / usage` resolved
  at 11:33 today. `check-ops-claims.sh` reads all `ok`.
- **The first commit leaves four tests red until the second.** Prose and
  code are separate commits; the docs move lands first, the test change
  second, in the same push.
- No estate message open.

## What Session 386 handed on

Archive STATUS.md's opening block (lines 1 to 8,242), first moving its ten live check markers into a current block, as tasks.md Session 386 records. *(For: session)*

## Session 386: STATUS.md's Recently Completed is archived

Session 385's next action. Docs only; the detail is in tasks.md,
Session 386.

- **STATUS.md is 8,310 lines, down from 14,615.** Sessions 10 to 344
  went to `docs/roadmap/archive/status_completed_2026-10-19.md`,
  unedited but for 10 re-based links. Sessions 349 to 374 stay.
- **Safe because nothing reads that section.** `ops_claims.py` parses
  from the top of the file to the `## Recently Completed` heading,
  which stays. Everything above it is byte-identical, and
  `check-ops-claims.sh` reads all `ok`.
- **Decided:** a separate archive file. Rejected appending to
  `completed_2026-10-19.md`, whose header says it came from tasks.md
  and which already holds these sessions' task records.
- **Left: the opening block**, 8,242 lines of dated announcements. It
  is the parsed region and carries ten live markers spread through it,
  so it needs its own sitting.
- No estate message open.

## What Session 385 handed on

Archive STATUS.md's Recently Completed (lines 8,267 to 14,611) after reading docs/design/status-claims.md, as tasks.md Session 385 records. *(For: session)*

## Session 385: the roadmap and the handoff are archived

The owner asked for old tasks, snags and handoff items to be archived.
Docs only; the counts are in tasks.md, Session 385.

- **tasks.md is about 1,270 lines, down from 18,831.** Sessions 24 to
  344 went to `docs/roadmap/archive/completed_2026-10-19.md`, unedited
  but for 44 re-based links. Session 286 and the Backlog stay, because
  they hold the file's only two unticked items.
- **The snag list's open entries were not touched.** Closing one is a
  judgement about the box. Only the Session 34 and 37 write-ups moved;
  the fixed `SNAG-ESTATE-*` rows stay because estate-manager's markers
  read them in this file.
- **HANDOFF.md kept Sessions 380 to 385**; 369 to 379 are at the top of
  `HANDOFF-archive.md`.
- **Left: STATUS.md**, 14,615 lines. Its opening block is re-measured
  by `sysadmin/ops_claims.py`, so it gets its own sitting.
- No estate message open.

## What Session 384 handed on

Nothing is owed: estate message af170afe is closed, and alfred-inference was restarted at 22:05 and reads fully on the card. *(For: none)*

## Session 384: an evicted VRAM resident reads degraded

Estate message `af170afe-54d0-4997-8a10-42267c6a2214`. Code in
`08a2235`; the detail is in tasks.md, Session 384.

- **What it does.** A `holds_vram` service whose buffers a game or a
  HIP job pushed into GTT now reads `degraded`, with the fdinfo figures
  in `details['gpu_residency']`. The estate refused to publish the
  split, and the monitor is what says a service cannot do its job.
- **Decided:** the figure is `drm-total-vram` less `drm-resident-vram`.
  Rejected `amd-evicted-vram`, which read 0 KiB beside a 1.0 GiB
  shortfall. Rejected judging a declared service with no client on the
  card: that is `venture-embed`'s CPU-only boot start, and the CPU
  fallback is `wait-for-dgpu`'s question.
- **The 128 MiB floor is a judgement, not a measurement.** The live
  population is 0 KiB and 1,048,320 KiB with nothing between.
- **Deployed at 22:03:29 and read back.** `alfred-inference` was
  restarted at 22:05:33, not by this session, so the first stored row
  (22:08:29, service `llama-server`) reads `ok` with 2,349,364 KiB of
  2,349,364 on the card. That proves the system daemon can read a user
  unit's fdinfo. The `degraded` verdict was proved only by driving the
  same function from the session at the evicted process before the
  restart; no stored row carries it yet.
- **The suite was red at HEAD** on three handoff-shape tests that
  required `## Scheduled action`, which Session 383 rightly removed.
  They skip when it is absent; folded into `08a2235`.

## What Session 383 handed on


Nothing is owed: no estate message is open, the game detector check passed, and the owner's uninstalls took `/` to 79 % and closed the critical alert. *(For: none)*

## Session 383: both scheduled checks closed

Session 370's scheduled check. It had been waiting on "an evening of
play", and four evenings had passed (2026-10-15 to 18). No code; the
counts are in tasks.md, Session 383.

- **All three conditions held.** 24 spans, one per launch; 163
  `focused` stretches and no `unknown` row, so the KWin probe always
  answered; `focus` reads `known` on every run inside a span (1,483 of
  1,483).
- **Left as found:** three spans are single-poll sightings with no
  duration. That is what a launch closed within a minute looks like at
  a 1-minute poll, not a defect, so no snag entry.
- **The disk check closed too.** The owner uninstalled Steam games
  this evening: `/` went from 95 % (85 GB free) at 21:52 to 79 %
  (337 GB free) at 21:56, and the "Critical disk usage on /" alert,
  open since 2026-10-14, resolved itself at 21:56:56. No warning
  opened after it. `steamapps/common` now holds 546 GB.
- No estate message open.

## What Session 382 handed on

Nothing is owed: no estate message is open; the scheduled checks wait on the owner's Steam uninstalls and an evening of play. *(For: none)*

## Session 382: the card stayed awake across a boot

Session 381's scheduled check. No code.

- **The udev rule held against amdgpu.** Boot `b6bb4935` (10:16 BST)
  is the first since the rule was written on 2026-10-15 14:05, and
  `power/control` reads `on`, `runtime_status` `active`. So the
  `add|bind` match was enough; the `DRIVER=="amdgpu"` and
  `amdgpu.runpm=0` fallbacks are not needed. Ticked in tasks.md,
  Session 374.
- No estate message open.

## What Session 381 handed on

Nothing was owed: the estate's priority-digit message is closed and no message is open; the scheduled checks wait on a boot and the owner.

## Session 381: estate.snags reads an ASCII priority digit

Estate message `67138a9d-3adf-45a5-a409-f4f844b0b0d9`. No code; the
detail is in tasks.md, Session 381.

- **Our `PRIORITY_RE` keeps `\d`.** It sets only `Entry.priority`,
  which nothing reads and no database stores, so a full-width digit
  cannot fail anything here. Both patterns find the same 177 priorities
  in our snag list. Rejected: switching to `[0-9]`, because it changes
  a field with no reader. Copy the estate's pattern if one is ever
  added.
- Closed `67138a9d` with that note.
- **Close note on `4f851ae8` (Alfred):** the endpoint answers, with 12
  spans on 2026-10-16 22:50. Alfred's Part 6 is unblocked. Its focus
  stretches also carry `state` and `last_seen_at`.
- **Close note on `89d1c61c` (estate-manager, the 2026-10-16 wipes):**
  no session ran git or pre-commit here in that window. Their unconfirmed
  reading is the owner's push from project-manager's Review tab: one
  pre-commit stash, then a failed restore that ran `git checkout -- .`.

## What Session 380 handed on

Nothing was owed: Alfred was to close our 4f851ae8, which it did on 2026-10-16.

## Session 380: ADR-0016 §4 from Alfred's answer

Session 379's next action. No code; the detail is in tasks.md,
Session 380.

- **ADR-0016 §4 now says our 30 days are the only raw record of
  gaming.** Alfred keeps one `Downtime: <game>` entry per run, with no
  expiry, and stores no spans (estate message `36903d39`).
- Amended in place rather than in a new section, because §4's bullet
  waited on Alfred's answer and would otherwise still read
  "unconfirmed".
- Retention stays 30 days. Alfred never rebuilds a day older than the
  window, so our expiry cannot erase its entries.
- Closed `36903d39`. Its detail said Alfred's Part 6 still waits on
  the endpoint, which has been live since 2026-10-15; the close note
  says so. Our `4f851ae8` is Alfred's to close.

## Older sessions

Sessions 379 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
