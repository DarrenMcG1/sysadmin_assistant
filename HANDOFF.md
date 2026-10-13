# Handoff — 2026-10-13 (Session 360)

## Next action

Backfill estate Rule 7: declare the pytest suite at pre-push in a new .pre-commit-config.yaml (verbose), time it, record it in CLAUDE.md (message 732a62cb). *(For: session)*

The message's detail gives the install line the owner must run, which
the agent's own hooks refuse to run. The session writes the config,
measures the stage, and asks the owner for that one command.

## Scheduled action

- `systemctl --user restart sysadmin-tray`, whenever convenient. It
  deploys Session 342's row-order fix and Session 357's status colours.
- The monitor, whenever convenient: `kill -TERM $(systemctl show
  sysadmin -p MainPID --value)`. Session 359 changed only declarations
  on `core/models/alert.py`, so the running daemon behaves the same, but
  postflight's deploy check reads it as stale until it restarts.

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

## What Session 358 handed on (done by Session 359)

Fix SNAG-DB-007: settle the open-alert identity from docs/design/alerts.md, then add its partial unique index and the flag/timestamp CHECKs in one migration. *(For: session)*

## Session 358: Alfred's Telegram health is watched from the day the bot exists

The owner asked for estate message `d01b0798`: Alfred's `GET
/api/health` gains a `telegram` field (`ok`, `degraded` or `disabled`),
and whether to watch it was left to this repository. Session 357's next
action stays open, unchanged.

Code in `ba81bb2` (the gated test) and `c056ee9` (the entry).

**The gate fired the same evening.** The owner installed
`~/.config/alfred/telegram.env` at 20:58 BST and said the bot was live; the
test went red, `alfred-telegram` was declared beside `alfred-bus`, and
`POST /api/sysadmin/reload` added it without a restart. Its first poll,
at 21:17:34 BST, read `ok`.

Decided:

- **Watched, but not today.** The field reads `disabled` until the
  owner creates the bot, and was absent from the live body this
  evening. An `equals: ok` entry would alert from its first poll about
  a state the owner chose.
- **A test fires the day it is time, rather than a task waiting to be
  read.** It skips while `~/.config/alfred/telegram.env` is absent
  (the prod token file, Alfred ADR-0139's amendment) and fails from
  the moment it exists until `services.yaml` has a monitored
  `alfred-telegram` entry. Gated on the file, not the body, because the
  body's value is what flips when the bot is in trouble. Falsified with
  the gate forced open: red against today's file, green against a copy
  holding the recommended entry, and the loader accepts that entry.
- **Its own entry, `alfred-bus`'s shape**, by the owner's 2026-09-25
  ruling for `bus`: the bot is non-critical, so its faults must not
  charge the `alfred` entry's reliability score. `equals: ok` is
  strict, because with the token file present `disabled` is a fault.
- **Rejected: an entry with `mute: true` now.** It ends only when
  someone remembers to unmute it, the same weakness as a note.

## Session 357: a critical service draws a red dot

Session 356's next action, `SNAG-TRAY-012`. Code in `902176a` (the map
and its tests) and `8fb5564` (the two tabs call the helper). Full suite
4,599 passed and 2 skipped; ruff and mypy are clean.

`STATUS_COLOURS` in `sysadmin_tray/styles.py` holds exactly the seven
`chk_health_status` values, and `status_colour()` is the one grey
fallback the three dot sites call. `tests/test_tray/test_status_colours.py`
pins the keys to the constraint in both directions and drives every
site through every value. Against the pre-fix map, 13 of its 25 tests
turn red.

Decided:

- **The keys equal the constraint; they do not merely include it.**
  `active`, `inactive`, `failed` and `unknown` went: no producer sends
  any of them to these sites. `/api/projects/managed` does send
  `unknown`, for a service with no health row, and it still draws grey
  through the fallback. A superset test would have let dead keys
  accumulate, as these four had since February.
- **`skipped` is grey, and the map now says so.** It means nobody
  looked, by declaration. It is neither well nor a fault, and a new
  colour would be a design decision this fix had no grounds for.
- **The colours are not derived from `STATUS_READINGS`.** That map
  sits in a SQLAlchemy model module the tray does not import. Its three
  readings also cannot give `degraded` amber and `critical` red, since
  both are `fault`.
- **Split into two code commits** at a green point, because the
  pre-commit hook blocks five or more code files without docs, and code
  and prose go in separate commits.

## What Session 356 handed on (done by Session 357)

Fix SNAG-TRAY-012: one status-colour map in sysadmin_tray/styles.py, read by all three sites, with a test pinning its keys to chk_health_status. *(For: session)*

## Session 356: a web page can no longer fire the monitor's actions

Session 355's next action. Code in `381cfdb`. The owner restarted
`sysadmin.service` at 16:52:34, and the probes passed live.

`require_auth` now refuses with 403 a request whose `Origin` is set and
not in `service.cors_origins`. It applies to all 13 mutating routes,
before the token is checked, whether or not a token is set.
`SNAG-API-005` stays open at P3 for the token half: another local
process sends no `Origin` and still gets through.

Decided:

- **The check is in `require_auth`, not in a middleware.** That gives it
  exactly the routes already guarded, and the census test holds that set
  equal to every non-`GET` route.
- **The allowed list is read from `app.state`, not `get_config()`.**
  `CORSMiddleware` captures it once and `service` is restart-only, so a
  reload must not let the two readers disagree.
- **A foreign origin is refused even with the right token.** That is
  simpler than ordering the two checks around each other, and a page
  cannot hold the token anyway.
- **The match is exact, as `CORSMiddleware`'s is**, and `"*"` allows
  everything. `Origin: null` is refused.

What went wrong: the first live probe ran before the restart, because
the restart was aimed at `--user`, where no `sysadmin.service` exists:
it is a system unit. That probe's `POST /api/sysadmin/scan-all` started
all four agents' scans once, out of schedule. Harmless, but recorded.
`sudo` does not work through the `!` prefix, so the owner restarts from
a terminal.

Second concern, recorded: `SNAG-TEST-017`. Postflight flagged an
idle-queue-only live assert while the GPU queue held a lease.
`SNAG-TEST-016` was flagged again too, as before.

## What Session 355 handed on (done by Session 356)

Close the cross-site half of SNAG-API-005: refuse a mutating request whose Origin header is set and not in cors_origins, with a test per route. *(For: session)*

## Session 355: the October design review's five defects are recorded

Session 354's next action. Roadmap and handoff only; no code changed,
no restart owed.

Estate message `dca21976` carried five readings from the owner's
October design review (run 2026-10-07 from an estate-manager session).
Each was re-read at its file and line, and measured where the box could
answer:

- R4, the empty API token: **`SNAG-API-005`, P2.** All 13 mutating
  routes are open, as quoted. Added by measurement: 9 of them take no
  body, so a browser can send them cross-site without a preflight. The
  old task "set a real token in config.yaml" is marked superseded,
  because the repository is public and a token in that file would be
  published.
- R5, the tray palette: **`SNAG-TRAY-012`, P2.** Confirmed, and there
  are three readers, not two. 311 `critical` rows in the last 7 days
  showed as grey dots.
- R35, duplicate open alerts: **`SNAG-DB-007`, P3.** The schema allows
  it, and the live table has none: 0 duplicate open pairs and 0 flags
  that disagree with their timestamps.
- R36, a unit that never applies migrations: **no entry.** This is the
  design `SNAG-DB-005` chose, and the commit-time check still runs
  (`scripts/claude-precommit.sh:95`). Recorded as a ticked item in
  tasks.md.
- R43, the placeholder and "~360 tests" in `CLAUDE.md`: **a `- [ ]`
  task** in Session 355's block in tasks.md.

Decided: the next action is SNAG-API-005's Origin check rather than the
tray colours, because it is the only finding that lets something outside
the box act on it. Rejected: fixing any of them here, which would be a
second concern.

Not recorded: the review's two closing remarks (direct database calls in
`files/router.py`, and the 48% docstring and comment share), which the
message lists outside the five and calls neither a defect.

## What Session 354 handed on (done by Session 355)

Read estate message dca21976, the October design review's five defects in this tree, and record each as a snag or a task with its file and line. *(For: session)*

It is the largest of the eleven open messages in this repository's
inbox. Recording them is one sitting; fixing any of them is its own.

## Session 354: this repository's two failure units are declared

Session 353's next action. `services.yaml` changed; no restart owed.

Why they were unmonitored: both units live in this repository's
`systemd/` and never had an entry. Each is a oneshot started by an
event, not a timer: `sysadmin-failed.service` by `sysadmin.service`'s
`OnFailure=`, `sysadmin-replay-failures.service` by each login. No kind
in `services.yaml` polls such a unit, and the sweep offers no snippet
for one, so nothing ever proposed an entry.

Decided: `kind: static`, `monitor: false`, each with its reason, the
shape the arbiter-started inference units use. Both
`controllable: false`, because starting `sysadmin-failed` by hand sends
a "sysadmin.service has failed" notice when it has not.

Rejected: a polled check. `kind: systemd` asserts `active`, so it would
alert all the time on both, and no kind asserts "not `failed`". A
failed handler would still show in `systemctl --failed`; nothing here
reads that box-wide, and that was not this sitting's question.

Applied with `POST /api/sysadmin/reload` (reported exactly the two
added). A sweep run by hand at 13:34:16 UTC reads 0 unmonitored and the
two `host` `deadlock-api-ingest` system units, which are disabled and
have been the owner's enable-or-remove decision in `services.yaml`
since Session 48. Full suite 4,540 passed, 2 skipped; ruff clean.

Found: STATUS.md's block was one alert behind
(`Project InvestingAssistant next action idle`, opened 2026-10-08
22:50:11). Re-counted 3 → 4; `check-ops-claims.sh` all `ok`.

## What Session 353 handed on (done by Session 354)

Find why our own sysadmin-failed.service and sysadmin-replay-failures.service are unmonitored, and declare them or say why not (tasks.md, Session 351). *(For: session)*

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

## Older sessions

Sessions 345 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
