# Handoff — 2026-10-18 (Session 383)

## Next action

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

## What Session 379 handed on (done by Session 380)

Amend ADR-0016 §4: Alfred keeps Downtime entries, not raw spans, so our 30 days are the only raw record; then close Alfred's message (tasks.md, Session 379). *(For: session)*

## Session 379: venture-embed declares holds_vram

Estate message `d2b70567-0cc4-42ba-916c-546f0540d94d` (estate-manager
found that `venture-embed` does hold VRAM). Re-measured from the journal
and confirmed. Code in `125bbc9`; the detail is in ADR-0007 §2.4 and
tasks.md, Session 379.

- **Zero offloaded layers keep the weights in RAM, not the compute
  buffer.** 10 of 10 starts after boot put 504 MiB on Vulkan0; 12 of 12
  boot starts ran CPU-only, because amdgpu was not ready yet.
- **`holds_vram: true` on `venture-embed`**, live by config reload at
  17:36 (`services_changed: ["venture-embed"]`); the 17:37:25 check
  recorded `gpu_context.evaluated: true`. Rejected: leaving it absent,
  which reads `ok` after a reset in the unit's usual state. Rejected:
  reading each start's log line, a new reader for a case never seen
  (`SNAG-GPU-008` holds the cost).
- **Not measured: a reset while it held the card.** None has happened.
  The 14 resets on record all hit CPU-only boot starts, so ADR-0007's
  old "267 of 823" figure measured processes no reset could touch.
- The start-order race is venture-assistant's. The estate already
  filed it there as message `d07f4176`.
- **Unstaged work in this tree was wiped twice by something outside
  the session**: at 17:35:43, by a `pre-commit` stash that was never
  restored (its patch is `~/.cache/pre-commit/patch1792168543-3830172`;
  the PID was not this session's), and at 17:38:32 with no patch. No
  hook in this repository or in `~/.claude/settings.json` stashes or
  restores. Reapplied both times. Eight peer sessions were running;
  the culprit was not found.
- Estate-manager closed our `2d24843e` (poll for games): they recorded
  polling as the route in their `ideas.md`; rung 2 is not built. Ticked
  in tasks.md, Session 378.
- Alfred's message `36903d39` (Alfred keeps Downtime entries, not
  spans) is the next action; it stays open until ADR-0016 says so.

## What Session 378 handed on (done by Session 379)

Nothing is owed: estate-manager rules on polling for games (our message 2d24843e-de87-481e-81a4-6a3ee72d675d); the scheduled checks wait on a boot and the owner. *(For: none)*

## Session 378: the estate should poll for games

Session 377's next action. Recommendation only; no code, ADR-0016
unchanged. The reasons are in tasks.md, Session 378.

- **Recommended: the estate polls `GET /api/games/spans`**, with no
  `estate/…` event. Filed at estate-manager as message
  `2d24843e-de87-481e-81a4-6a3ee72d675d`; rung 2 is theirs and the
  owner's to rule on.
- The detector's 60 s poll sets the latency either way. A poll
  re-derives the state each tick, which an event cannot survive a
  restart doing. The estate has no MQTT subscriber to build on.
- Checked live: 200 in 5 ms, Deadlock open.
- **Reopen when** something needs the push itself; then a retained
  topic with a last will.

## What Session 377 handed on (done by Session 378)

Recommend whether the game-start event publishes under estate/… or the estate polls GET /api/games/spans (ADR-0016 §6; tasks.md, Session 369). *(For: session)*

## Session 377: the memory index is 123 lines

Session 376's next action. The memory directory is not in git; the
detail is in tasks.md, Session 377.

- `MEMORY.md` went from 175 lines to 123: three lines dropped that its
  own rule excuses, and 34 memories folded into 16 family lines. No
  memory file was changed or deleted.
- The header now states a 140-line budget beside the byte one.

## What Session 376 handed on (done by Session 377)

Compact the memory index under 140 lines (tasks.md, Session 374). *(For: session)*

## Session 376: no PostgreSQL service for CI, yet

Session 375's next action. Recommendation only; `ci.yml` unchanged.
The rehearsal's numbers are in tasks.md, Session 376.

- **Recommended no.** The pre-push stage already runs both schema
  tests, and the full suite, against real PostgreSQL on every push.
- **The service is not a two-test change.** 14 test files skip on
  "no database" in CI. A bare service turned 36 tests red; a service
  migrated to head first left 2 red, both asserting the box's live
  rows, which would need the `box` mark.
- **The drift guard would pass in CI without guarding anything new**:
  against a freshly built database it repeats `test_schema_build.py`.
- **Reopen when** a push can come from somewhere other than this box.
- The owner may overrule. Meanwhile `ci.yml` stays as it is.

## What Session 375 handed on (done by Session 376)

Recommend whether ci.yml gets a PostgreSQL service so test_schema_build.py and test_schema_drift.py run in CI (tasks.md, Session 368). *(For: session)*

## Session 375: the card is pinned awake

Session 374's next action. No repository code; one system file.

- `/etc/udev/rules.d/80-dgpu-awake.rules` written and
  `power/control` set to `on` live, through `pkexec`: `sudo` needs a
  terminal password, and neither the session nor the owner's `!`
  prefix can supply one.
- **Changed from the recorded command:** the rule matches
  `ACTION=="add|bind"`. Rejected: `add` alone, which fires before
  amdgpu binds; the driver re-enables runtime PM while loading, so the
  write would likely be undone. Reasoned, not measured.
- Checked: `udevadm verify` passes; `power/control` reads `on`,
  `runtime_status` `active`.

## What Session 374 handed on (done by Session 375)

Pin the dGPU awake by running the two commands under Pin the card awake in tasks.md, Session 374. *(For: owner, ~5 min)*

## Session 374: the 05:41 power-off was the dark-screen wake again

Session 373's next action. Journal reading only; no code changed, no
restart owed. The evidence is in tasks.md, Session 374.

- **The box had not hung.** Everything logged normally until
  05:41:15, 27 s after the short press at 05:40:48. logind deferred
  the press to PowerDevil, nothing visible happened, and the key was
  then held until the power went (unclean-shutdown recovery on the
  next boot).
- **Why the owner pressed it:** the card had slept all night with
  Steam quit, woke at 05:19:10, and no DP monitor reconnected. This is
  Session 349's linux-lts failure, now on 7.2.9.
- **The 2026-10-08 ruling's premise broke on the kernel upgrade.**
  7.2.7 logged 0 card resumes in a week; 7.2.9 logged 1,797 in one
  boot. The ruling (a sleeping card is not wanted) still stands, so
  pinning the card awake implements it rather than reopening it.
- **Chosen:** a udev rule setting `power/control=on`. Rejected:
  `amdgpu.runpm=0`, which needs a boot-entry edit and a reboot.
- Until the owner runs it, any night with Steam quit can end the same
  way. With Steam running, as now, the card stays awake.

## What Session 373 handed on (done by Session 374)

Read the journal of the boot that ended 2026-10-14 05:41 from 05:30 on, to find whether the box hung before its power key was pressed. *(For: session)*

## Session 373: CLAUDE.md's two stale lines

Session 372's next action, task R43. Docs only.

- Removed the `**Current Phase:**` line, which still held the
  template's `_Update this as your project evolves_`.
- **Chosen:** remove it. Rejected: copying STATUS.md's phase
  ("Feature-complete — maintenance & future features") into it,
  which gives the phase two homes, and one of them would go stale.
- Dropped "~360 tests" from the `uv run pytest` line, without
  replacing it: pytest prints the count, and Session 372 counted 4,670.
- Nothing reads either string: a grep of `sysadmin/`, `tests/` and
  `scripts/` finds neither.

## What Session 372 handed on (done by Session 373)

Fix R43 in CLAUDE.md: remove the template placeholder at line 8 and drop the stale "~360 tests" count at line 104. *(For: session)*

## Session 372: idx_alerts_open_by_agent dropped

Session 371's next action. Code in `6f151e4`. Migration 021 drops the index, which
migration 019's `uq_alerts_open_agent_title` made redundant, and
migration 017's docstring now says where it went. Applied to the live
database the same day; no restart is owed, because the daemon checks
the schema head only at startup.

- **Measured first:** 100,000 open `log_aggregator` rows inserted and
  the index dropped, in one rolled-back transaction. `sysadmin`'s
  open-row read took `uq_alerts_open_agent_title` at 4 buffers,
  0.013 ms. Live state was checked unchanged afterwards.
- **Not filed at the estate**, though the handoff said to. Estate
  rule 5 (a dropped database object leaves a pointer) covers a schema
  or table holding data, and its filing names where the content lands.
  An index has no content, and the estate's inventory lists no indexes.
  Rejected: filing anyway, which hands the estate a message with
  nothing to record.
- **New test:** `test_an_open_index_leads_on_agent` asserts that some
  open-row index leads on `agent`, which is what made the drop safe.
  Reordering the unique index's columns turns it red.
- Moved Sessions 355 to 358 to `HANDOFF-archive.md`, to bring this
  file back under the estate's 500-line bound.
- **`check-ops-claims.sh` reads one `no` until the next restart**:
  the daemon started at 11:37:25, before this session's edits. Not
  restarted, because the change it lacks is the model no longer
  declaring the dropped index, which the running process never reads.
  STATUS.md's route and test counts were stale from Session 371 and
  are refreshed (53 routes, 4,670 tests).

## What Session 371 handed on (done by Session 372)

Drop idx_alerts_open_by_agent in its own migration, filing at the estate first and leaving a pointer in migration 017's docstring. *(For: session)*

## Session 371: ADR-0016's second half, live

Session 370's next action. Built `GET /api/games/spans`, its three
contract models and registry row, and the KWin focus probe. Code in
`7d3e50d`.

- **Live:** the owner restarted the daemon at 2026-10-15 11:37:25. The
  route answered 200 with `retained_from` at the detector's first run;
  a timestamp with no offset answered 422.
- **The probe in the real daemon:** a stand-in process carrying
  `SteamLaunch AppId=570` was seen as "Dota 2" on two polls, and both
  runs recorded `focus: known` with two probe lines in the journal. It
  had no window, so no focus row was written, which is correct. The
  stand-in's span was deleted by its id afterwards.
- **Found:** `sysadmin.service` is a system unit with no session bus in
  its environment. ADR-0016 §3 said it was a user unit. The probe sets
  `XDG_RUNTIME_DIR` through `build_env`, the helper `systemctl --user`
  already uses. Recorded in ADR-0016 §8.
- **Chosen:** each focus stretch is served with its `state`, and
  `focus_known` stays at span level. Rejected: serving only `focused`
  stretches, which would hide which minutes nobody could see.
- **Chosen:** `pid=0` (no active window) counts as unfocused, not
  unknown. Only a probe with no journal line is `unknown`.
- **Chosen:** a fixed plugin name, unloaded and reloaded when KWin says
  it is already loaded. Rejected: a fresh name per call, which leaks
  one script into KWin each time a probe is killed mid-call.
- **For Alfred:** a `+01:00` offset must be sent as `%2B01:00`, because
  a query string decodes `+` to a space. `Z` needs no encoding.
- **Rule 3 (announce a changed surface to its readers):** no repository
  reads `games/spans` yet, so nothing was filed before the commit, and
  the commit says so. `4dc2b8bc` was then closed with the shape.

## What Session 370 handed on (done by Session 371)

Build ADR-0016's second half: GET /api/games/spans with its contracts.py model and registry row, and the one-shot KWin focus probe; then close 4dc2b8bc. *(For: session)*

## Session 370: ADR-0016's first half, live

Session 369's next action. Built: migration 020 (`game_spans`,
`game_focus`, a 30-day retention row, `game_detector` admitted by the
alerts table's agent whitelist), `sysadmin/games/` (detector, agent,
models), the wiring, and 26 tests. No route.

- **Live:** the owner approved; migration 020 applied and the daemon
  restarted at 2026-10-15 08:52:12. Startup closed 0 open spans; the
  first poll at 08:53:12 completed with no game running. A stand-in
  process carrying `SteamLaunch AppId=570` was found by `scan()` on the
  live `/proc` and named "Dota 2" from the real manifest, without
  writing a row.
- **Not yet seen:** a real game span. The first evening of play is the
  first live positive; check `sysadmin.game_spans` after it.
- **For the second half:** the probe plugs into
  `GameDetectorAgent(focus_probe=…)`; it returns the active window's
  PID or `None`, and the bookkeeping already turns that into
  `focused`/`unknown` stretches.
- Commit plan: one code commit carrying `tasks.md` (the hook blocks 5+
  code files with no tracking doc, and this is 19), then one prose
  commit. Rejected: four 4-file code commits, which doubles the
  per-push review count for one concern.
- Departed from ADR-0016, both measured, recorded in its §7: a Steam span is keyed on the AppId, because Steam's console log
  shows the launch wrapper and the reaper both carry
  `SteamLaunch AppId=1422450`; `game_focus` has a `state` column
  (`focused`/`unknown`), because §3 needs "unknown" and §4 had nowhere
  to put it.
- Until the KWin probe (second half) exists, every gaming minute is
  recorded as an `unknown` focus stretch, never as unfocused.
- Added rule: a gap of more than 3 polls breaks a span, so a suspended
  box does not report the night as play.
- Found by the scratch-database test: with no ORM relationship, the
  unit of work inserted the focus row before its span and the foreign
  key refused it. Fixed with a never-read relationship on `GameFocus`.

## What Session 369 handed on (done by Session 370)

Build ADR-0016's first half: the game_spans and game_focus migration and the 60 s game detector job, with tests and no route yet. *(For: session)*

## Session 369 (2026-10-14): ADR-0016, game spans

Session 368's next action. Docs only, plus a reply to Alfred.

- Decided with the owner (ADR-0016): Steam `AppId=` plus a `games:`
  list in config.yaml; focus by a one-shot KWin script, only while a
  game runs; 30 days kept; raw spans, Alfred merges.
- Measured: KWin 6.7.5 has no D-Bus call for the active window. A KWin
  script reads it and prints it to the user journal.
- Rejected: a resident KWin script (this repository would own something
  inside the compositor); probing focus on every poll (1,440 journal
  lines a day into the log aggregator's own input).
- Open, at Alfred: whether Alfred keeps the spans it reads. Asked in
  message `4f851ae8-01c9-4656-bffa-3bc1547ab10e`. Until it answers, the
  30 days here are the only record (ADR-0016 §4).
- Second concern recorded in tasks.md, not worked: a game-start event
  for the estate's gaming ladder.

## What Session 368 handed on (done by Session 369)

Draft the ADR for Alfred's game-spans endpoint (message 4dc2b8bc) with the owner: detector, focus, retention, merged or raw spans. *(For: owner, ~20 min)*

The ADR is drafted with the owner because the detector choice (Steam's
`AppId=` in `/proc/<pid>/cmdline` against an owner-kept list) and
whether focus can be had from KWin are theirs. Constraints are in
tasks.md's Session 362 block.

## Older sessions

Sessions 368 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
