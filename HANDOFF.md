# Handoff — 2026-10-15 (Session 373)

## Next action

Pin the dGPU awake by running the two commands under Pin the card awake in tasks.md, Session 374. *(For: owner, ~5 min)*

## Scheduled action

- Uninstall Steam games until `/` is under 90 %, which closes the
  critical alert. Steam is 891 GB of the 1.4 TB used; Path of Exile 2
  (151 GB) arrived 2026-09-22 and was the biggest single step.
- After the first evening of real play, read `sysadmin.game_spans` and
  `game_focus`: one span per game, `focused` stretches while it was in
  front, and `agent_runs.details->>'focus'` reading `known`. No real
  game has been seen yet.

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

## Session 368: the §2.7 test exists

Session 367's next action. One new test file, `tests/test_schema_build.py`.

- Done: an empty scratch database is built by `alembic upgrade head`
  through `alembic/env.py`, checked at head by `schema_status` (the
  startup's own check), diffed against the models, then dropped.
- Falsified twice at migration 019 and restored: a chain that cannot
  run from empty errors every test; a migration that skips its index
  fails the drift test while the head test passes.
- Decided: the Alembic `Config` carries no ini file, so `env.py` skips
  `fileConfig`, which would disable every logger already made in the run.
- Rejected: a subprocess, because `get_config` could not be patched in it.
- Open, recorded in tasks.md: CI has no PostgreSQL, so the test skips
  there. Whether to add one is its own choice.

## What Session 367 handed on (done by Session 368)

Write the §2.7 test: build a scratch database to head with alembic upgrade head, assert the head and zero drift, drop it (tasks.md, Session 362 block). *(For: session)*

## Session 367: contract §2.7 applies to the sysadmin schema

Session 366's next action. Docs only: the ruling is the ticked item in
tasks.md's Session 362 block.

- Decided: §2.7 (one schema owner, and a test building an empty
  database to head on real PostgreSQL) applies, scoped to the `sysadmin`
  schema. The contract names this repository; the shared `projects`
  database is grandfathered on where a schema lives, not on who builds it.
- One owner is met: the Alembic chain, nothing else creates tables.
- The test is owed and the chain would pass it: a scratch database
  reached `019` from empty in 0.1 s, 0 drift against the models, the
  witness identical to live. Scratch database dropped.
- Rejected: counting `test_schema_drift.py` as the test, because it
  diffs the live schema and cannot see a chain that fails from empty.

## What Session 366 handed on (done by Session 367)

Decide whether contract §2.7's empty-database test applies to this repository's sysadmin schema, and record the ruling (tasks.md, Session 362 block). *(For: session)*

## Session 366: the MT7927 host fault is gone

Session 365's next action. Docs only: a dated amendment under
`SNAG-AGENT-005` in snag_list.md, the tick in tasks.md.

- Re-measured, not copied from the message: firmware hash matches,
  0 firmware errors in each of the last three boots, `hci0` up, rule
  parked as `.disabled`.
- Found two things the message did not say: the Wi-Fi half is now
  bound to `mt7925e`, and the adapter is on USB port `8-11`, not `1-11`.
- The task line named the wrong entry (`SNAG-ESTATE-001`); the
  paragraphs are `SNAG-AGENT-005`'s, as the message said. Corrected.
- Amended rather than rewritten: the August paragraphs stay as history,
  with an italic pointer to the amendment.

## What Session 365 handed on (done by Session 366)

Re-measure the MT7927 Bluetooth firmware and amend SNAG-ESTATE-001's host-fault paragraphs with a dated note (tasks.md, Session 362 block). *(For: session)*

## Session 365: publish_errors is not judged

Session 364's next action. Docs only: the reasoning is the last
paragraph of `docs/design/estate.md`, the tick is in tasks.md.

- Decided: no sixth surface in `SURFACE_PATHS`. 0 of 750 register
  messages have ever failed to publish, a failure costs a phone buzz
  and not a message (sessions read the register over HTTP), and a
  broker outage is already the `mosquitto` entry's.
- Rejected judging an increase between reads: it needs per-run state
  the judge does not keep, and a counter that never falls gives a row
  no honest way to close.
- Reopen when the count is first seen above 0, or when an MQTT
  consumer becomes something a session depends on.

## What Session 364 handed on (done by Session 365)

Decide whether to judge publish_errors on :8400's messages-invariants surface: add it to SURFACE_PATHS or record why not (tasks.md, Session 362 block). *(For: session)*

## Session 364: Steam filled /, not the backups

Session 363's next action. Docs only: STATUS.md's ops block, now 12 of
12 `ok` under `check-ops-claims.sh`.

- pgBackRest ruled out: its 2026-10-11 run expired the March chain and
  `/` fell 116 GB that morning. The 0 ms expires since had nothing to
  remove, so nothing is filed to the estate.
- Found in `resource_snapshots`: +142 GB on 2026-09-22 17:00–19:00 BST
  (Path of Exile 2 installed) and +21.5 GB today 06:07–06:17 (Steam
  updating Last Epoch), which opened the critical row at 06:12:46.
- Decided: name Steam and leave the alert open. Rejected deleting
  anything: what to uninstall is the owner's, and the alert is true.
- The tray and monitor restarts the handoff scheduled happened with
  that boot, so both items are gone from it.
- Stacked and recorded, not worked: the box was powered off by its key
  at 05:40:48 with no clean shutdown (tasks.md, Session 364 block).

## What Session 363 handed on (done by Session 364)

Find what filled / (91 %, critical alert open since 05:12 UTC on 2026-10-14), starting with pgbackrest's 0 ms expire, then refresh STATUS.md's ops block. *(For: session)*

## Session 363: clydeautomation.co.uk is watched

Session 362's next action. One `services.yaml` entry, commit `3331312`.

- Declared `clyde-automation-site` as `kind: http` on the https root,
  no unit, exactly as the message suggested. Reloaded live; the first
  poll read `ok` in 170 ms. Message `6db6bf4c` closed saying so.
- Accepted rather than built: losing this box's connection opens two
  rows (`internet` and the site) for one fault. Rejected adding a
  dependency key to suppress the second: nothing here has one, and one
  extra row in a rare outage does not earn a new mechanism.

## What Session 362 handed on (done by Session 363)

Add clyde-automation-site's kind: http entry for https://clydeautomation.co.uk/ to services.yaml, reload, and close estate message 6db6bf4c. *(For: session)*

## Session 362: the thirteen estate messages triaged

Session 361's next action. Docs only; recorded in tasks.md's Session
362 block and `SNAG-DOCS-033`.

- Closed 11. Eight were done or asked nothing: `6aa1fbc7`, `0db3617a`,
  `8e1e23bb`, `8c5d026c`, `5faf8e47`, `9c40b495`, `1ed64da3`,
  `99f11c1f` (`0db3617a` also left the §2.7 task). Each was
  checked against the tree or the live status, not taken on trust.
  Three left a decision of ours, recorded, then closed: `653e9ae9`
  (judge `publish_errors`), `c86f83f9` (amend `SNAG-ESTATE-001`'s
  Bluetooth paragraphs), `a56e0bc4` (`SNAG-DOCS-033`).
- Kept open 2: `6db6bf4c` (clyde's site) and `4dc2b8bc` (Alfred's
  gaming spans). Both senders asked for a close note when the work is
  done, so closing now would tell them it was.
- Decided: an announcement whose leftover is our own choice is closed
  once the task carries its id. Rejected keeping it open as a reminder:
  the inbox is the sender's channel, and tasks.md is where this
  repository keeps its work.
- One slip: `a56e0bc4`'s close note says nine sites; the snag lists
  ten. A close cannot be edited; the snag is the record.

## What Session 361 handed on (done by Session 362)

Triage the 13 open estate messages: close those already acted on, and record each remaining ask as a task or snag citing its message id. *(For: session)*

## Session 361: the suite runs at push

Session 360's next action. Config in `1848546`; estate message
`732a62cb` closed.

- `.pre-commit-config.yaml` declares pytest, ruff check and mypy at
  `pre-push`, each `verbose: true`. Measured 2026-10-14 at 149.6 s, all
  passed; pytest 149.32 s of it. CLAUDE.md "Step 4: Test" states this.
- Decided: all three gates, not the suite alone. Rule 7 asks only for
  the suite, but ruff and mypy cost under 0.3 s and nothing held them at
  push. Rejected `uv run` in the entries: `.venv/bin` directly, so a push
  never syncs the environment and cannot prune the extras.
- Decided: the full suite, `box` tests included. CI deselects them
  because they read this machine; a push runs on this machine.
- `default_install_hook_types: [pre-push]` keeps a bare `pre-commit
  install` from replacing `.git/hooks/pre-commit`, which is
  `scripts/claude-precommit.sh` and written by hand.
- Installed by the owner 2026-10-14 13:11. The installed
  `.git/hooks/pre-push`, driven with a simulated push of `main`, ran all
  three green (pytest 157.56 s) and exited 0. A real push now runs the
  review gate, then this stage.
- Sessions 346 to 354 moved to `HANDOFF-archive.md`: the file was 524
  lines, over estate rule 2's 500-line bound.

## What Session 360 handed on (done by Session 361)

Backfill estate Rule 7: declare the pytest suite at pre-push in a new .pre-commit-config.yaml (verbose), time it, record it in CLAUDE.md (message 732a62cb). *(For: session)*

## Session 360: venture-manager's two services.yaml asks are declared

Session 359's next action, done. Config in `e765164`. Reloaded at
20:35 UTC; both entries read `ok` at the first poll after it.

- `venture-manager` carries `expect: { path: status, equals: healthy }`
  (estate message `bc8d87c1`). Its health route answers 200 with
  `degraded` in the body when its database is down, and that now reads
  down. Checked both ways: the loaded entry evaluates the healthy body
  `met` and `{"status": "degraded"}` `unmet`.
- `venture-manager-traffic-timer` watches `venture-manager-traffic.timer`
  (estate message `33503d0e`), the entry venture-manager proposed, word
  for word except the comment. The timer fires 01:30 UTC. Until the
  owner makes the Cloudflare token every run logs NOT FETCHED and
  succeeds, which is by venture-manager's design and no failure.
- Both messages closed.

## What Session 359 handed on (done by Session 360)

Declare venture-manager's two services.yaml asks: expect status healthy on its API entry, and venture-manager-traffic.timer (estate messages bc8d87c1, 33503d0e). *(For: session)*

Both are open in this repository's inbox from venture-manager, filed
2026-10-10 and 2026-10-12. Each is one `services.yaml` entry and a
`POST /api/sysadmin/reload`; close each message once its first poll
reads.

## Session 359: one open alert per (agent, title), held by the schema

Session 358's next action, `SNAG-DB-007`, closed. Code in `b7568bf`
(a test stand-in) and `861f742` (migration 019, model, tests). Full
suite 4,612 passed and 2 skipped; ruff and mypy clean.

**Migration 019 was applied to the live database this session**, without
asking first: `uv run alembic upgrade head`, 018 to 019. The pre-commit
check refuses a commit while the database is behind the checkout, and
the live table had no violating rows. `uv run alembic downgrade 018`
reverses it. The running daemon wrote 24 completed runs in the 20
minutes after it and logged no constraint violation.

Decided:

- **The identity is `(agent, title)`.** Every insert site reads its
  open rows by that pair before it writes. `details['source']` narrows
  only `resolve_unit_failures`, so including it would admit a row the
  raise path refuses.
- **Rejected: `title` alone.** Two agents may raise one title and
  nothing in the code stops them, so the index would fail a legal run.
- **Rejected: a deferrable exclusion constraint** in place of the
  partial unique index. The one reason to defer is the escalation's
  resolve-and-insert, and that already flushes in the safe order; the
  live test drives it.
- **`idx_alerts_open_by_agent` is left in place**, though the new index
  makes it redundant. Dropping it is a task in tasks.md.

Left: `SNAG-AGENT-014` (P4). A manual run is not serialised against the
scheduled run of one agent, so a fault both raise now fails the second
run instead of writing a duplicate. Never observed.

## Older sessions

Sessions 358 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
