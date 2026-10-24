# Handoff — 2026-10-24 (Session 417)

## Next action

Re-pin STATUS.md's Alerts paragraph per tasks.md's Session 416 block, and check the newest GitHub run on `main` is green. *(For: session)*

## Session 417: CI deselects the nudge family's live half

Opened on Session 416's Next action. Code in `60872fe`, docs in the
commit after it.

- **Fixed:** `TestTheRealBlockDeclaresTheNudgeFamily` carries
  `@pytest.mark.box`, as its sibling does. CI runs `-m "not box"` with
  no database, and these were its only 2 failures.
- **Rejected:** retiring `ci.yml`. It is the only run without the box's
  database, so it is the one place a missing mark shows.
- **Unseen:** the next GitHub run. It follows the owner's push; the
  Next action checks it.
- **Found, not worked:** nothing catches a missing `box` mark before
  push. Recorded in tasks.md's Session 417 block.

## What Session 416 handed on

Fix or retire the failing GitHub CI per `SNAG-TEST-019`: recommended, mark `TestTheRealBlockDeclaresTheNudgeFamily` `box` and see the next run green. *(For: session)*

## Session 416: journald's cap is 8G

Opened on Session 415's Next action; the owner ruled 8G. Docs only in
this repository; the change is in `/etc`.

- **Applied:** `/etc/systemd/journald.conf.d/size.conf` with
  `SystemMaxUse=8G`, written through `pkexec`, then journald restarted
  at 11:52:22. Its own log line reads `3.9G, max 8G, 4G free`.
- **Forecast:** no vacuum for about two weeks, so the window grows a
  full day a day, then settles near 30 days at about 260 MB a day.
- **Unchanged:** the `Short journal window` row (7-day floor) should
  resolve itself around 2026-10-27, as before; the cap does not move it
  sooner, because it only stops deleting.
- **Found, not worked:** GitHub CI has been red since 2026-10-23,
  because two live tests read the database CI lacks. Recorded as
  `SNAG-TEST-019`; the owner asked that the next session fix or retire
  CI, so that is the Next action.
- **Rejected:** setting `SystemKeepFree=` as well. Its default keeps
  4G free (15 % of the disk, capped at 4G); with 189G free, the 8G cap
  binds first.

## What Session 415 handed on

Rule on journald's cap in tasks.md's Session 414 block: recommended, `SystemMaxUse=8G` in a `journald.conf.d` drop-in, then restart journald. *(For: owner, ~5 min)*

## Session 415: the journal's window is watched

Opened on Session 414's Next action. Code in `07e0e7e`, tests in
`3581299`, docs in the commit after them.

- **Built:** `sysadmin/monitor/journal_horizon.py` and
  `_check_journal_horizon` in the sysadmin agent. Two `warning`
  families, each resolving its own rows by id, as collation's does:
  `Short journal window` under 7 days, and `Core dump loop in <exe>` at
  10 dumps an hour from one executable.
- **Chosen:** the window is the newer of the two heads (system 12:16,
  user 12:21), because a reader of either scope relies on the shorter.
  Rejected: the system head alone, which overstates the user journal's.
- **Chosen:** a 7-day floor, so a weekly timer's last run survives.
  Rejected: a floor the live 3.4-day window would pass; the row is true
  now and resolves itself in about four days.
- **Chosen:** dumps counted per executable. Rejected: a total, which
  would sum unrelated crashes into a false loop.
- **Driven:** the 22:04:35 run raised the window row at 3.41 days and
  no loop; the 22:09:35 run held it, raising nothing. The daemon restarted at 21:59:35 (owner ruling of
  2026-10-21: a session may run the no-sudo restart).
- **Default kept:** journald's 4G cap stands until the owner rules.

## What Session 414 handed on

Build the journal-horizon watch in tasks.md's Session 414 block, so a core-dump loop or a collapsed journal window alerts here. *(For: session)*

## Session 414: the journal window is measured and logged

Opened on estate message `4a35a2e7-46b5-40cc-a964-1adec1aee528` from
venture-assistant: the journal reached back only to 2026-10-20 12:16.
Docs only. The message is closed, naming tasks.md's Session 414 block.

- **Cause:** journald runs on defaults, so system and user files share
  one 4G cap, and it is full. baloo's crash loop wrote about 207k core
  dumps from 10-20 to 10-22 15:55, when the owner disabled it.
- **Recovery:** about 260 MB a day since then. The window lengthens by
  most of a day per day and settles near 15 days in about two weeks.
- **Left for the owner:** whether to raise the cap to 8G, recorded in
  tasks.md with a recommendation. Default meanwhile: 4G stands.
- **Rejected:** writing the drop-in this session. It is `/etc`, needs
  `sudo`, and how much history the box keeps is the owner's call.
- **Rejected:** building the horizon watch now. It is a feature, a
  second concern, so it is the Next action instead.

## What Session 413 handed on

Run the preflight and work the highest-ranked open snag a session can start now, or record that none can, as Session 410 did. *(For: session)*

## Session 413: the push gate no longer depends on log volume

Opened on the owner's failed `git push`. Closes `SNAG-LOG-022`. Code in
`a3aeb4b`, docs in the commit after it.

- **Cause:** the three red tests were `SNAG-LOG-022`'s. The user
  journal reached back only to 2026-10-20 12:21. The records they read
  were older: searxng's shim and the scan timer started 10-18, the
  review last fired 10-19.
- **Changed:** in `tests/test_services_registry.py`, an empty read is
  checked against the journal's oldest retained record. If the wanted
  records predate it, the test skips and names both instants. A
  non-empty read is asserted as before. With the horizon forced to
  zero, the same three tests fail.
- **Rejected:** taking the box tests out of the pre-push stage. They
  are the only witness that the estate still writes JSON. Also
  rejected: waiting for the records to return at the next boot and on
  10-26. The next flood would redden them again.
- **Still true, not filed:** with baloo off, the journal still spans
  about three days. In the day to 17:35, llama-server wrote 157k lines
  (91k of them `venture-chat-large`'s `GET /api/health 404`) and Steam
  95k. `venture-chat-large` is `kind: static` in `services.yaml`, so
  the polling is not ours, and it had stopped by 17:36.
- **Housekeeping:** Sessions 408 to 393 moved to `HANDOFF-archive.md`,
  bringing this file under estate rule 2's 500-line bound.

## What Session 412 handed on

Run the preflight and work the highest-ranked open snag a session can start now, or record that none can, as Session 410 did. *(For: session)*

## Session 412: the idle-nudge rows no longer stale STATUS.md

Closes `SNAG-DOCS-035`. Code in `cfef2c8`, docs in the commit after it.

- **Changed:** `sysadmin/ops_claims.py` gains rule 13. A sentence
  carrying `<!--check:rotating-->` quotes a SQL `LIKE` pattern, and the
  open rows it matches are set aside from the `alerts` count and the
  `open_titles` sentence. `check_rotating` reads `mismatch` if a member
  is above `info`. STATUS.md now pins 3 stable rows and declares
  `Project % next action idle`; `sysadmin-check-claims` reads all ok.
- **Rejected:** declaring the nudges flapping. Each is open most of
  the week, so rule 12's half-the-window test would refuse it.
- **Limit, in the snag entry:** the estate's roll-up row,
  `Estate project next actions idle`, is not matched by the pattern.
- **Suite:** 4737 passed, 4 skipped; the 3 reds are `SNAG-LOG-022`'s,
  unchanged.

## What Session 411 handed on

Fix SNAG-DOCS-035 so the daily idle-nudge rows stop staling STATUS.md's Alerts paragraph, per tasks.md's Session 411 item. *(For: session)*

## Session 411: STATUS.md names all six open alerts

Docs only. The Alerts paragraph now names the six open rows, and
`sysadmin-check-claims` reads all 13 claims `ok`.

- **Changed:** added `Project Athenaeum next action idle` and
  `Project portfolio next action idle` (both 05:09 today), dropped the
  resolved clyde-automation-site row, and refreshed the disk to 87.3 %.
  The estate's `vram` check now fails on three journals
  (`alfred-inference`, `venture-embed`, `venture-model-probe`), not
  one. The alert is estate-manager's own, so nothing was filed.
- **Second concern, recorded, not worked:** `SNAG-DOCS-035`. The
  idle-nudge rows rotate most mornings, so this paragraph goes stale
  daily. Sessions 408, 409 and 411 each spent their sitting re-pinning
  it. The snag names a candidate fix, unruled: set the family aside by
  title pattern, as rule 12 already does for flapping titles.
- **Not mine, unchanged:** `SNAG-LOG-022`'s three red journal tests.

## What Session 410 handed on

Rewrite STATUS.md's Alerts paragraph for the six open rows, so its alerts and open_titles claims read ok, per tasks.md's Session 410 item. *(For: session)*

## Session 410: no open snag can be started

Docs only. The preflight's 38 open entries are 31 decided, 4 blocked
and 3 delegated, and none of the events they wait on has happened.

- **Measured:** no reboot since 2026-10-18 10:16 (`SNAG-LOG-021`,
  `SNAG-LOG-022`); `SNAG-TEST-014`'s probe record is 405 of 405
  `closed`; `SNAG-AGENT-012`'s family is empty and
  `SNAG-AGENT-013`'s `auto_restart` count is 0. `SNAG-GPU-003` is
  P3 but the owner ruled it not built on 2026-09-23.
- **Ticked:** Session 402's item to act on estate message `571f2f12`
  (the mosquitto gate). Session 404 had logged the answer; the next-boot
  check is its own open item.
- **Second concern, recorded in tasks.md, not worked:** STATUS.md's
  Alerts paragraph says 5 open rows and the box holds 6. The idle-nudge
  rows moved at 05:09:24 today, seven hours after Session 409 rewrote
  it. That is the next action.
- **Not mine, unchanged:** `SNAG-LOG-022`'s three red journal tests.

## What Session 409 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 409: STATUS.md names all five open alerts

Docs only. STATUS.md's Alerts paragraph named 3 of the 5 open rows; it
now names all five, and `sysadmin-check-claims` reads every claim `ok`.

- **Added:** `estate-manager-audit-timer critical` (05:05 today) and
  `Estate audit checks errored` (05:41 today; the estate's `vram` check
  could not read `venture-model-probe.service`'s journal). Both are
  estate-manager's alerts on their own audit, so nothing was filed.
- **Refreshed:** the disk row now reads 87.2 %, its live message, in
  place of 81.4 %.
- **Dropped:** the two resolutions from 2026-10-21 (`llama-server
  degraded`, `venture-chat unreachable`). They are history, and the
  paragraph states what is open.
- **Not mine, unchanged:** `SNAG-LOG-022`'s three red journal tests.

## Older sessions

Sessions 408 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
