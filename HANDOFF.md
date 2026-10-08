# Handoff — 2026-10-08 (Session 353)

## Next action

Find why our own sysadmin-failed.service and sysadmin-replay-failures.service are unmonitored, and declare them or say why not (tasks.md, Session 351). *(For: session)*

They are two of the four findings left in the unit sweep; the other two
are the system-scope `deadlock-api-ingest` units, filed `host`. Four is
under the roll-up's `alert_threshold: 5`, so no alert is open, and the
next new undeclared unit anywhere on the box re-raises it.

## Scheduled action

- Session 342's row-order fix in the tray still needs only
  `systemctl --user restart sysadmin-tray`, whenever convenient.

## Session 353: go-to-market's reply watcher is watched

Session 352's next action. `services.yaml` changed (`f3e7ffe`); no
restart owed.

`go-to-market-watch-replies-timer` is declared as go-to-market's
message `b00baf51` worded it, with a comment in the shape of the
draft-check copy's. Applied with `POST /api/sysadmin/reload`, which
reported that one entry added; the 21:04:11 UTC poll stored it `ok`
(last run 20:30:24 BST, success). The message is closed.

Checked before writing: `fold_timers` in `sysadmin/units/scan.py` folds
a oneshot under the timer that starts it, so declaring the timer is
what takes the service out of the findings. An in-process drive of
`scan_units` against the edited file showed it gone.

Decided: ran the sweep by hand (`POST /api/sysadmin/scan-all`, which
also starts the other three agents) rather than leave it to the
six-hourly schedule. The roll-up does not re-raise at four findings: it
resolves under `alert_threshold: 5`, so STATUS.md's marked count would
have gone stale at about 02:50. It resolved at 22:05:52 BST and the
block now reads 3, with a re-count note; `check-ops-claims.sh` all
`ok`. Full suite 4,540 passed, 2 skipped.

Found: Session 351's item named the two `deadlock-api-ingest` units as
unmonitored. The sweep files them `host` (system scope, under `/etc`);
the roll-up counts both categories. The item now says so.

## What Session 352 handed on (done by Session 353)

Declare go-to-market-watch-replies-timer in services.yaml as estate message b00baf51 asks; it is one of five unmonitored units (tasks.md, Session 351). *(For: session)*

go-to-market installed the timer on 2026-10-08 and names the entry it
wants (`kind: timer`, beside `go-to-market-draft-check-copy-timer`). Its
service, `go-to-market-watch-replies.service`, is one of the five units
in the open `Unmonitored systemd units: 5 findings` alert; the other
four are the rest of the tasks.md item.

## Session 352: the sports analyser's stopped units are no longer polled

Session 351's next action. `services.yaml` changed; no restart owed.

The three entries (`sports_analyser`, `sports_analyser-frontend`,
`sportsanalyser-pipeline-timer`) are `monitor: false`, each with a
reason citing the owner's 2026-10-07 ruling and estate message
`fd376758`. The section comment that said the services "are still
running … so they stay monitored" now says when and why that stopped,
and that re-enabling the units is when to delete the pairs.

Decided: applied with `POST /api/sysadmin/reload`, not the restart the
next action named. The reload exists for exactly this file, it needs no
`sudo` for the system unit, and a restart would have falsified
STATUS.md's marked daemon start for no gain. The reload reported only
those three entries as changed.

Decided: the entries stay rather than being deleted, because `name`
keys their `service_health` history and reliability scores. The `log:`
blocks stay too, since a disabled unit writes nothing to read.

Checked: the 21:39:11 poll stored all three `skipped` with the reason in
`details`, and their three critical alerts resolved at 21:39:14
(`_resolve_recovered` treats `skipped` as healthy). STATUS.md's marked
alert count went 7 → 4 with a re-count note; `check-ops-claims.sh`
all `ok`. Full suite 4,540 passed, 2 skipped. The message is closed
with a note naming the commit.

Found and left: the postflight's vacuous-guard gate flags
`tests/test_off_loop.py:99`, a set built from route dependencies that
are empty on both routes it reads since Session 333. Unrelated to
`services.yaml`; recorded as `SNAG-TEST-016` in snag_list.md.

## What Session 351 handed on (done by Session 352)

Set `monitor: false` with a reason on services.yaml's three sports analyser entries, restart, and close estate message fd376758 (tasks.md, Session 351). *(For: session)*

An estate session stopped those units on the owner's ruling of
2026-10-07, so three `critical` alerts stay open for units that are
down on purpose. The key and its required `reason` are documented at
the top of `services.yaml`; six entries already use it.

## Session 351: STATUS.md's opening block is current again

Session 350's next action. No code changed, no restart owed.

The daemon started four times since the block's 2026-10-05 06:20:53,
not twice: the owner restarted it by hand at 20:29:16 (`sudo`, `pts/4`,
home directory) and 21:33:50 (`pts/19`, this repository) on 5 October,
and no session transcript holds either; then the reboot into
`linux-lts` at 2026-10-07 21:42:10 and the boot after the hard reset at
2026-10-08 08:49:11. The new STATUS entry carries the last one in bold
with both check markers; Session 345's time is unbolded.

Open alerts are 7, not 6 as Session 350 measured: `Unmonitored systemd
units: 5 findings` reopened at 20:50:11 while this sitting worked. All
seven are named in the marked sentence with a re-count note.

The checker also read the 2026-10-08 03:00 prediction as passed. The
2026-09-07 row did clear, but
`test_a_shared_instant_is_two_records_and_not_one_stored_twice` still
passes on 53 newer shared instants. Removing the spent marker turned
`test_the_block_states_at_least_one_prediction` red, as it did for the
sitting before, so a new prediction was derived the same way: the real
`purge_statement`, run inside a rolled-back transaction, leaves 1 of 53
after the 2026-10-26 run and 0 after the 2026-10-27 one. Its marker
first failed the clock pin because a caveat sat between the 03:00
sentence and the marker; reordered.

Checked: every `check-ops-claims.sh` row `ok`, exit 0; the five test
files that read STATUS.md or the specimen, 709 passed. The full suite
was not run: nothing outside documents changed.

Decided: three of the seven alerts are a second concern (the stopped
sports analyser units), recorded in tasks.md and made the next action
rather than worked here. The recurring unit-sweep row is recorded and
not traced.

## What Session 350 handed on (done by Session 351)

Bring STATUS.md's opening block up to date: two daemon restarts (2026-10-05 21:33:50, the 2026-10-08 08:49 boot) and 6 open alerts against 2 (tasks.md, Session 347). *(For: session)*

It is the first startable item left in tasks.md, and it grew while it
waited: Session 350's postflight measured the daemon active since
2026-10-08 08:49:11, the boot after Session 349's hard reset, and 6
unresolved alerts where the block names 2. Session 345's block shows how
to record a restart.

## Session 350: the handoff is archived

Session 349's next action. Moved lines 188 to 14,361 of HANDOFF.md,
Session 343 and older, into `HANDOFF-archive.md` unedited and in order,
newest first, under a short header. HANDOFF.md went from 14,361 lines to
221. Checked: the kept top and the archive body reconstruct the
original byte for byte (`cmp`). No code changed, no restart owed.

Decided: keep Sessions 344 to 349, six sittings, because that is what
the last week of work needs to read; the cut falls on a section heading.
The archive's header follows `dotfiles`' archive of the same day, so the
estate has one shape. A later move adds its sections at the archive's
top, below the header.

Found and not worked: 10 live tests fail, all in
`tests/test_arbitrated_stops_live.py` and
`tests/test_estate_surface_payloads.py`, because estate-manager's
`/api/queue/invariants` on 8400 answers `503` with `queue not ready:
database unavailable`. They fail the same way with the original handoff
restored, so the move did not cause them. The other 4,530 pass.

## What Session 349 handed on (done by Session 350)

Move HANDOFF.md's sections older than the recent few into HANDOFF-archive.md, bringing it under estate rule 2's 500-line bound (tasks.md, Session 348). *(For: session)*

The dGPU hunt is closed on the owner's ruling of 2026-10-08, so the
first startable item in tasks.md is the archive move. HANDOFF.md is
over 14,000 lines against the estate's 500-line bound, and the
session-start hook says so every sitting.

## Session 349: on linux-lts the card sleeps, and the screens do not come back

Session 348's scheduled action, brought forward by the owner reporting
an overnight crash. No code changed.

Read the witness log (657 minutes) and the journal of the boot that
ended at 08:47:50. The card was `suspended` in 551 minutes; it woke
only for the hourly `llama-server` work. At 08:00:01 and 08:20:27 it
resumed cleanly but every connector stayed `disconnected` and nothing
drew. Services logged normally to the end, and the journal stops with
no shutdown sequence, so it was a hard reset, not a crash. The box came
back on `7.2.9-arch1-1`.

Decided: the kernel question is answered, and the result changes what
is being asked, so it went to the owner rather than to more measurement.
The owner saw the monitors wake to their logo and go black, and ruled
to close the hunt: the box stays on 7.2, where the card never sleeps
and the screens always wake. Rejected: chasing it as a kernel
display-wake bug, which would be upstream work, not this repository's.
`scripts/dgpu-pin-witness.py` stays as an instrument; nothing schedules
it. Not settled: whether the 27 to 28 September LTS night
failed the same way; it shows the same resumes, but that boot ended in
a clean shutdown three hours later.

## What Session 348 handed on (done by Session 349: the witness read; the archive move was not reached)

Move HANDOFF.md's sections older than the recent few into HANDOFF-archive.md, bringing it under estate rule 2's 500-line bound (tasks.md, Session 348). *(For: session)*

## Session 348: the linux-lts witness is scheduled

Session 347's next action, which was the owner's, done a day late. No
code changed.

The owner rebooted into `linux-lts` at 2026-10-07 21:41:53. The running
kernel is `6.18.55-1-lts`, not the 6.18.54 tasks.md named, which still
separates the LTS line from 7.2. Steam was not running at 21:43. At
21:43 the planned 21:30 start had passed, and a transient
`--on-calendar` timer set in the past never fires, so the owner
scheduled it for 21:50 instead. `sysadmin-dgpu-pin-witness-lts.timer`
fires at 2026-10-07 21:50:00 with `--duration 43200`, so the run ends
near 09:50 on 2026-10-08; `systemctl cat` shows the right command and
log path.

Learnt: `sudo` cannot be run through the prompt's `!` prefix, because
it has no terminal to read the password from. A command needing `sudo`
goes to the owner's own terminal.

Not acted on, each its own concern: HANDOFF.md is over the new 500-line
bound (now the next action), the STATUS.md restart record Session 347
left, and eleven open estate messages.

## What Session 347 handed on (done by Session 348)

Owner: tonight, quit Steam, reboot into linux-lts and schedule the root dGPU witness for 21:30 (command in tasks.md, Session 347). *(For: owner, ~5 min, at 2026-10-06 21:00)*

## Session 347: as root, kwin goes quiet with the monitors off

Session 346's scheduled action. No code changed.

Read the root log (720 minutes, 21:31 to 09:30). `unreadable` was 0 to
2 a minute, so root saw nearly every process. The monitors were off from
21:53 to 05:50, 477 minutes; the card was `active` in every second and
never suspended. `kwin_wayland` submitted only in the 21:53 minute.
`steamwebhelper` and `Xwayland` submitted in all but a few seconds of
the off window, because Steam had been started at 08:41 on 2026-10-05,
after Session 346's 07:52 check. Ticked the Session 338 item.

Decided: the two nights may be read together. The kwin fact comes from
a night with Steam running and the all-quiet fact from one without, but
kwin's idle work should not depend on Steam. Not checked: a reader that
holds the card's power reference without submitting (sensor reads
through sysfs, for one) is as invisible to fdinfo as the driver is.

Not acted on, each its own concern: the owner's clean restart at
2026-10-05 21:33:50 is not yet in STATUS.md (recorded as a task under
Session 347), and eight open estate messages, five of them new on
2026-10-05.

## What Session 346 handed on (done by Session 347)

Nothing is startable until the root dGPU witness finishes at 09:30 on 2026-10-06; tasks.md, snag_list.md and ideas.md hold nothing startable. *(For: none, until 2026-10-06)*

## Session 346: the root witness is scheduled

Session 345's next action, which was the owner's. No code changed.

The owner scheduled the root run. `sysadmin-dgpu-pin-witness-root.timer`
fires at 2026-10-05 21:30:00 with `--duration 43200` and the log path
above; `systemctl cat` shows the right command. Steam was not running at
07:52. The three open estate messages are still not acted on, as
Session 345 left them.

## What Session 345 handed on (done by Session 346)

Run the dGPU witness once as root overnight with Steam quit, using the command in tasks.md's Session 338 block. *(For: owner, ~3 min)*

## Session 345: the owner's deploy recorded, one restart

Session 344's next action. No code changed.

The 2026-10-04 20:50:41 restart was the owner's, run by hand from a
terminal: the system journal records `sudo ./scripts/setup-systemd.sh`
at 20:50:40 and `sudo systemctl restart sysadmin` at 20:50:41, both
`TTY=pts/19`, and no session transcript in any repository holds either.
The service went active at 20:50:43, which is when `READY=1` arrived
under `Type=notify`. The installed unit reads `Type=notify`,
`WatchdogUSec=1min`, `RestartMode=direct`, and it ran 9 h 30 m with
`NRestarts=0`, so the watchdog pings arrive. Ticked the owner's redeploy
and the `Type=notify` item in tasks.md.

Restarted once at 2026-10-05 06:20:53 (`kill -TERM`, 12 s down,
`/health` 200) after a green suite, 4,540 passed and 2 skipped.
`/api/files/trends` now serves Session 343's fit: 117.1 MB/day over 81
scans, 50 GB on 2026-12-30, 100 GB on 2028-03-11.

STATUS.md: a new entry carries the bold time and both check markers;
Session 339's entry keeps its time unbolded. Decided against rewriting
339's sentence, for the reason 339 gave about 323's. Every
`check-ops-claims.sh` row reads `ok`. The checker's start-time reader
needs the literal `restarted at **…**`; a first draft reading
"restarted once more, at" read `??` until reworded.

Not acted on: three open estate messages (pgbackrest-backup's new
declaration, the `at` time on the `For:` marker, and `publish_errors`).
Each is its own concern for a later session.

## What Session 344 handed on (done by Session 345)

Record the owner's 20:50:41 deploy in STATUS.md, then restart the daemon once so Session 343's junk-growth fit goes live (tasks.md, Session 344). *(For: session)*

The owner's owed deploy has already happened: `systemctl show sysadmin`
reads `Type=notify`, `WatchdogUSec=1min`, and the journal has a clean
stop and start at 2026-10-04 20:50:41 with `NRestarts=0`. Session 343
wrote `sysadmin/files/router.py` at 20:52, so its fix is not live, and
`check-ops-claims.sh` reports the daemon stale and the block's restart
record (2026-10-03 09:55:07) out of date. Whose restart it was is not
yet recorded; Session 339's block shows how to establish it.

### Owed by the owner (as Session 344 left it)

Run the dGPU witness once as root, overnight, with Steam quit
(tasks.md, Session 338 block, has the command) *(For: owner, ~3 min)*. This shows whether kwin or a root process keeps the
card awake. If everything is still quiet, the next step is one night on
`linux-lts`.

The unit-file deploy (`setup-systemd.sh` and a restart), owed since
Session 327, is done as of 20:50:41 and is no longer asked for.
Session 342's row-order fix in the tray needs only
`systemctl --user restart sysadmin-tray`.

## Session 344: an `expires` clock must stand alone

Session 343's next action, `SNAG-DOCS-032`, closed. `check_expiry`
pins a prediction through `states_clock`, which matches `HH:MM` only
with no digit or colon before it and no digit after. It is used for
both the pin and the different-zone note (SNAG-ESTATE-013's diagnostic),
which had the same substring test.

Decided: a colon *after* the clock is admitted. `15:03:00` names the
minute `15:03`, so a prediction stated to the second still pins; the
`03:00` inside it does not. Rejected: also refusing `+` or `-` before
the clock, which would stop the `01:00` in an offset `+01:00` from
pinning but would also refuse the second end of a range like
`10:00-11:00`. No sentence carries an offset today, so it was left.

Verified: 11 tests in `TestTheClockStandsAlone`; six red with the helper
reverted to `clock in prose`, the five correct-case ones green either
way. Full suite 4,540 passed and 2 skipped, ruff and mypy clean. The live
prediction still reads `match`. `ops_claims.py` is not imported by the
daemon, so no restart is owed by this change.


## Older sessions

Sessions 343 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
