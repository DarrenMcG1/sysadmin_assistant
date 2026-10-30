# Handoff — 2026-10-30 (Session 434)

## Next action

Free space on / by uninstalling a Steam game you no longer play, so the 88 % disk alert falls under its 80 % threshold and closes. *(For: owner, ~10 min)*

The feature freeze leaves no session work startable; the open disk row
is the one item waiting on the owner (STATUS.md, Alerts). Steam's
library was 891 GB of the 1.4 TB used when Session 362 measured it.

## Scheduled action

- 2026-11-04: the estate decides where a version and freeze date live;
  write this repository's there (tasks.md, Session 430 block).
- 2026-11-22, after 03:00: STATUS.md's timed prediction falls due.
  Measure the shared instants again, then rewrite or replace it.
- 2027-02-01: the owner reads the v2 list in `ideas.md`.

## Session 434: STATUS.md's Deploy and prediction claims re-measured

Opened on Session 433's Next action. Docs only.

- **Deploy:** the 2026-10-28 07:02:10 restart was the box booting after
  an overnight shutdown; the daemon still runs `3992b99`.
- **Chosen:** replace the spent prediction with the one the same test
  now depends on (3 shared instants, clearing 2026-11-22). Rejected:
  retiring it outright as the task said, because
  `test_the_block_states_at_least_one_prediction` then goes red; and
  relaxing that test, which is code the freeze does not admit and a
  guard deleted beside its last finding.

## What Session 433 handed on

Fix the two STATUS.md claims Session 432 found failing, the Deploy paragraph's restart and the 2026-10-27 expiry, per tasks.md's Session 432 block. *(For: session)*

## Session 433: the notification probe stops reaching the screen

Opened on Session 432's Next action, 1.0 item 1. Code in `901e12f`.

- **1.0 is done**: both items of the owner's ruling. The freeze holds
  from today. No version string or freeze date is written anywhere
  machine-readable; the estate decides where on 2026-11-04.
- **Chosen:** the served half of the hazard runs on a private bus with
  `test_failure_replay_live.py`'s stand-in owning the name, so the
  probe never reaches Plasma. Rejected: an opt-in mark on the live
  call, because the suite would then never run it; and a second close,
  because it cannot reach a cause nobody found.
- **Given up, knowingly:** the suite no longer shows that *Plasma*
  answers the announcer's call quickly. The hazard is about whether a
  server owns the name, not about which server it is.
  `test_it_admits_the_live_bus` still asks the live bus, by
  `NameHasOwner`.
- **Left on disk:** `~/.local/state/sysadmin_assistant/notify-probe.jsonl`,
  492 lines, all `closed`. Nothing writes to it any more.

## What Session 432 handed on

1.0, item 1: fix SNAG-TEST-014, the live notification test that leaves its probe on the owner's screen, per tasks.md's Session 430 block. *(For: session)*

## Session 432: STATUS.md's Alerts paragraph names the open rows

Opened on Session 431's Next action, 1.0 item 2. Docs only.

- **Measured live:** 2 rows open. `High disk usage on /` (88 %, since
  2026-10-19) and `Estate project next actions idle`, the roll-up the
  estate judge raises in place of a row each once more than five
  repositories are idle (six were). The audit rows and `Short journal
  window` closed on 2026-10-27.
- **Chosen:** name the roll-up in the paragraph. Rejected: widening the
  `rotating` check's family to cover it, which is code the freeze does
  not admit, and would hide a row that does count.
- **`SNAG-TEST-014` is now owed in the register.** The push-stage
  suite refused the new Next action because the entry still read
  "decided, no session owes work", which the owner's 1.0 ruling
  overturned and Session 430 had not carried into the register.
- **Left, as a task in Session 432's block:** the same check run fails
  the Deploy paragraph's restart time (the 2026-10-28 boot) and a
  prediction that fell due on 2026-10-27.

## What Session 431 handed on

1.0, item 2: rewrite STATUS.md's Alerts paragraph from the open rows, per the first unticked item in tasks.md's Session 430 block. *(For: session)*

## Session 431: the arc tests drive the suite's own interpreter

Opened on Session 430's Next action. Code in `34e918c`.

- **Cause, measured, and not the one recorded:** coverage 7.17.0 is
  innocent. The gate's blind half launches `.venv/bin/python -m pytest`,
  so no `VIRTUAL_ENV` reaches the fixture's `uv run --with
  coverage[toml]`. It runs in a temporary directory outside any project,
  so uv used its own default Python: 3.14.7 since 2026-10-28 17:34, when
  uv installed it. `uv run pytest` passes the variable on, gets 3.12.12,
  and was green on 7.17.0 throughout. Session 430 read 3.12.12 from the
  repository, where the project picks the interpreter.
- **Fixed:** the fixture passes `--python sys.executable`, so the drive
  runs on whatever interpreter runs the suite. Rejected: pinning
  coverage, which is not the cause; `UV_PYTHON` in the blind wrapper,
  which fixes one launcher and is a second version number to keep in
  step with `ci.yml`'s.
- **The recorded reach was wrong too:** `check-vacuous-guards.sh` runs
  from the repository root, where `.venv` decides, so it never saw 3.14.
- `ci.yml`'s `UV_PYTHON` comment says the variable reaches the ephemeral
  run; it still does, and is now redundant there but harmless. Left as
  is: config, and not this concern.

## What Session 430 handed on

Make the pre-push gate green: 7 arc tests fail on coverage.py 7.17.0, fetched unpinned, per SNAG-TEST-022 in tasks.md's Session 430 block. *(For: session)*

## Session 430: the owner rules on 1.0 and the feature freeze

Opened on estate message `256c64ad-041d-4a78-b136-b33e462bd62f`
(estate-manager, 2026-10-30), which asked every active repository to put
a 1.0 scope and a v2 date to the owner. Docs only.

- **Ruled:** 1.0 is `SNAG-TEST-014` fixed and STATUS.md's Alerts
  paragraph rewritten; after it, only bug fixes and what daily use
  forces; new ideas one line under *v2* in `ideas.md`; the owner reads
  that list on 2027-02-01. Recorded in `CLAUDE.md`, "1.0, then a
  feature freeze until 2027-02-01".
- **Rejected by the owner:** the session's recommendation, 1.0 as main
  stood with a v2 date of 2027-01-04 to match project-manager; and 1.0
  after all eleven of this repository's own P3 snags.
- **Measured:** both audit rows have closed, so Session 428's check is
  ticked and the scheduled action is gone. Open outside the idle family:
  `High disk usage on /` and `Estate project next actions idle`, a title
  the paragraph's family exemption does not match.
- **Not invented:** a machine-readable version or freeze date. The
  estate decides where they live on 2026-11-04; tasks.md carries the
  write.
- **The push-stage run is red, and not from this commit:** the
  `not box` half fails 7 tests in `tests/test_vacuous_guards_live.py`.
  They drive `uv run --with coverage[toml]` unpinned, which now
  resolves 7.17.0; the interpreter is unchanged at 3.12.12. Recorded as
  `SNAG-TEST-022` (P2) and the Next action, ahead of the STATUS.md
  rewrite, because the owner's push is refused until it is fixed. Not
  fixed here: a second concern.
- **HANDOFF.md was 505 lines**, over estate rule 2's 500-line bound:
  Sessions 419 back to 411 moved to the top of `HANDOFF-archive.md`,
  unedited.

## What Session 429 handed on

Nothing is startable: every open task waits on the scheduled audit run, a third missing `box` mark, or an interpreter change. *(For: none)*

## Session 429: the journal-head helper loses its unrun assert

Opened on Session 428's Next action. Code in `99be72b`.

- **Cause, measured:** coverage over `tests/test_services_registry.py`
  alone missed `_journal_head_epoch` whole, `_skip_if_rotated_out`'s
  body, and both call sites (755, 1043). The helper runs only after an
  empty journal read, and since the 03:25 boot every read has found
  records. The guard gate reports asserts only, so it named line 275.
- **Fixed rather than declared:** the assert narrowed `Popen`'s optional
  `stdout` for a type checker that excludes `tests/`, so it guarded
  nothing. `journalctl -n +1` returns the oldest record directly (the
  read `journal_horizon.read_head` already makes), the same record as
  the stream's first line in both scopes, in about 2 ms; `subprocess.run`
  replaces `Popen` and the assert goes. Rejected: a `# may-not-evaluate:`
  declaration, which would list a non-guard on every run; calling
  `read_head` itself, which is async and would tie a test premise to the
  module another file tests.
- **Driven:** the helper matches journalctl's head in both scopes;
  `_skip_if_rotated_out` skips at `@0` and not at now.
- **Postflight's gate:** every evaluable assert ran (8331). The same run
  settled Session 426's last item: the scan-timer test passed, and the
  gate listed its `:1035` and `:1046` declarations as turned and
  evaluated anyway. Both stay, since the journal will rotate the timer's
  lines out again. Nothing owner-facing is open in tasks.md, the snag
  list or ideas.md, so the line is `none`.

## What Session 428 handed on

Find why the postflight never evaluated `tests/test_services_registry.py:275`, then fix it or declare it `# may-not-evaluate:`, per tasks.md's Session 426 block. *(For: session)*

## Session 428: STATUS.md's alert paragraph names the audit's cause

Opened on Session 427's Next action. Docs only.

- **Close note on `f4075b05`** (estate-manager, 18:32 today): fixed in
  their `83bceb7`, logged as their Session 445. `read_startup_allocation`
  now reads exit 1 with stdout exactly `-- No entries --` and empty
  stderr as no start, which is a `residency_unreadable` warn; a bad
  pattern still exits 1 with stderr and stays an error. They ran it by
  hand: the check completes. The first unit run is 05:00 on 2026-10-27.
- **Rewrote** STATUS.md's Alerts paragraph. Measured open now: disk,
  short journal, and the two audit rows. `Unusual RAM usage` has
  resolved and is gone from the paragraph; the `critical` row is named.
  `check-ops-claims.sh` reads ok on both the count (4) and the named
  titles.
- **Added** the 2026-10-27 check that both audit rows close, as tasks.md's
  Session 428 item and the Scheduled action above. Rejected: removing the
  rows from the paragraph now on the strength of the fix, since the
  claim check would read wrong until 05:00.

## What Session 427 handed on

Rewrite STATUS.md's alert paragraph now the audit critical's cause is known (estate-manager's, filed `f4075b05`), per tasks.md's Session 426 block. *(For: session)*

## Session 427: the audit's failure is estate-manager's, and filed

Opened on Session 426's Next action. Docs only.

- **Measured:** `estate-manager-audit.service` has exited 1 every
  morning since 2026-10-22, each time for one reason: the `vram` check
  logged `could not read the journal for: … journalctl exited 1: no
  stderr`. Today only `venture-model-probe.service` was listed; on
  2026-10-23 to 25 `alfred-inference` and `venture-embed` were too.
- **Cause, reproduced:** `journalctl --grep` exits 1 when nothing
  matches, with empty stderr. The probe unit with the check's grep gave
  1; without `--grep` it gave 0; `venture-embed` with a grep that cannot
  match gave 1. The user journal starts 2026-10-20 18:14, so a unit
  that last started before then has nothing to match. The estate's
  `read_startup_allocation` raises on any non-zero exit, so its own
  documented "no start in the window" path is never reached.
- **Filed** at estate-manager as
  `f4075b05-62ac-4c08-9436-7d61988c5646`. Not worked around here: the
  unit really did fail, so the `critical` row is this daemon doing its
  job. It closes when a run succeeds. Rejected: excusing the unit in
  `services.yaml`, which would hide a real failure to quieten one
  caused elsewhere.

## What Session 426 handed on

Read why `estate-manager-audit.service` failed at 05:03 today and file at estate-manager if it is theirs, per tasks.md's Session 426 block. *(For: session)*

## Session 426: the mosquitto gate waited, and `SNAG-LOG-021` is closed

Opened on Session 425's Next action. Docs only.

- **Measured:** the 03:25:33 boot is the first since estate-manager's
  waiting gate (their ADR-0259, installed 2026-10-21). mosquitto logged
  `listener address assigned after 4 s; starting mosquitto` at
  03:25:51, `NRestarts=0`, and no line at warning or above.
- **Absence checked at the reader:** `sysadmin.alerts` holds no
  mosquitto row since 2026-10-18's, and `log_entries` holds none this
  boot. The aggregator was reading from 03:25:36, and it stores
  mosquitto only at warning and above, which the journal agrees is
  none.
- **Closed** `SNAG-LOG-021`, ticked Session 404's boot check, and added
  a dated note to `docs/design/logs.md`, whose "on every boot" sentence
  was no longer true.
- **Found, not worked:** the postflight named three things, now
  tasks in tasks.md's Session 426 block. The estate audit oneshot
  failed at 05:03:15 (exit 1), which holds an open `critical` row
  here; STATUS.md's alert claims are stale because of it and two new
  idle nudges; and `tests/test_services_registry.py:275` went
  unevaluated. The critical row is the Next action.
- **Not done:** the second boot check, formerly under Scheduled action.
  It is due now, so it moved to the same tasks block and the section
  is gone.

## What Session 425 handed on

Confirm the mosquitto gate's wait at the 2026-10-26 03:25 boot and close `SNAG-LOG-021`, per tasks.md's Session 404 block. *(For: session)*

## Session 425: a critical alert reaches the phone

Opened on Session 424's Next action, on the owner's go. Docs only.

- **Done:** one test `critical` alert published on
  `estate/alerts/raised` at 14:36:01 UTC, built by the daemon's own
  `build_payload` and sent with its `sysadmin-publisher` credential.
  Its id is `test-session-425`, so no alert row stands behind it.
- **Witnessed:** the broker logged the `sysadmin-publisher` login, and
  the owner received the alert in alfred-glance. The broker-to-phone
  path is now seen end to end. The channel it arrived on was not
  reported.
- **Not done:** the two boot checks became due at this morning's
  03:25 boot. They are a separate concern, so the first is the Next
  action and the second stays scheduled.

## What Session 424 handed on

Say go for a session to publish one test `critical` alert on `estate/alerts/raised`, then check glance shows it, per tasks.md's Session 424 block. *(For: owner, ~5 min)*

## Session 424: a failed GPU recovery opens a critical row

Opened on Session 423's Next action. Code in `3992b99`.

- **Found:** the 2026-10-25 `GPU Recovery Failed: -62` line was stored
  at `error` and raised nothing of its own. The incident fold put it
  inside the reset's `warning` row, so the MQTT gate never saw it.
- **Done:** it is a declared signature opening at `critical`, in both
  kernels' spellings. The fold now treats a louder declaration as
  standing rather than as a rival name, so the reset row still takes the
  fragments.
- **Measured, not seen:** the LTS spelling comes from 6.18.57's
  `amdgpu.ko` format string, because no LTS boot has failed a recovery.
- **Rejected:** escalating the reset row when its group holds a failure.
  Its title would still say "reset", and a failure landing in a later
  poll would form its own group and miss it.
- **Tested:** 5 new tests; undoing either half of the fix turns them
  red. Full suite 4,776 passed, 3 skipped.
- **Deployed:** daemon restarted 04:28:17 on `3992b99`; `/api/health`
  200 and two clean log-aggregator runs since.
- **Close note:** alfred-glance closed `e8d68ae3-c0a3-426f-b6c0-c5ad7c9a2b5d`,
  built as their `e6e7b1f` (their ADR-0036). Alerts show on a
  high-importance channel at glance's next foreground, not in real
  time. A real-time receiver waits on the watch's battery week,
  ~2026-11-01. Ticked in tasks.md's Session 423 block.

## What Session 423 handed on

Raise a failed GPU recovery (`GPU Recovery Failed`) as a `critical` alert so it is published to the phone, per tasks.md's Session 423 block. *(For: session)*

## Session 423: the dark screens were a GPU hang, not the sleep

Opened on the owner's report. Docs only.

- **Found:** at 21:39 on 2026-10-25, kernel 7.2.11, the dGPU's SMU
  stopped answering and the full-card reset failed
  (`GPU Recovery Failed: -62`). Zero `PSP is resuming` that boot, so
  the udev pin held and the runtime-sleep fault did not recur. The
  box stayed up until the owner cut the power at 03:24.
- **Found:** every alert raised was `warning`, so only the tray
  rendered them, on the dead screens.
- **Filed:** estate message `e8d68ae3-c0a3-426f-b6c0-c5ad7c9a2b5d` to
  alfred-glance, asking it to render `estate/alerts/raised`. Its
  detail names the gate key wrongly; tasks.md records the right one.
- **Advised, not configured:** two KDE Connect run commands for the
  phone, `kscreen-doctor --dpms on` and `systemctl reboot`. The second
  is the only way to recover from this kind of hang.
- **Noted:** the box booted at 2026-10-26 03:25, so both scheduled
  actions are now due.

## What Session 422 handed on

Nothing is startable: every open task waits on the next boot, a third missing `box` mark, or an interpreter change. *(For: none)*

## Session 422: the retention skip is declared to the guard gate

Opened on Session 421's Next action. Code in `f2ebbac`.

- **Done:** a `# may-not-turn:` on the scan-timer test's sum and a
  `# may-not-evaluate:` on its assert, now
  `tests/test_services_registry.py:1037` and `:1048`. `SNAG-TEST-021`
  closed.
- **Tested:** `check-vacuous-guards.sh` over the full suite exits 0
  and lists both among the declared sites.
- **Rejected:** making the assert always run by reading the skip as
  zero. It would then assert over nothing and hide the vacuity, as
  `SNAG-TEST-018` found.
- **Stated limit:** the witness is Session 413's recorded drive with the
  horizon forced to zero, not a test.

## What Session 421 handed on

Declare the journal-retention skip at `tests/test_services_registry.py:1033` and `:1041` to the vacuous-guard gate, per `SNAG-TEST-021`. *(For: session)*

## Session 421: CI is green with the blinded gate

Opened on Session 420's Next action. Docs only.

- **Seen:** GitHub run `40105529365` on `8ecb43c` passed in 4m17s. It
  is the first run to cover `29d67fc` (the blinded non-box half) and
  `c278c85` (uv offline inside it).
- **Noted:** the owner's `git push` reported `cannot lock ref` after its
  pre-push gate passed, because `origin/main` had already moved to
  `8ecb43c`. The commits had landed; nothing was lost.
- **Found, not worked:** postflight's vacuous-guard gate flags the
  journal-retention skip Session 413 added, `SNAG-TEST-021`. It clears
  by itself at the next boot.
- **Rejected as Next action:** `SNAG-TEST-020`, which is parked until a
  third missing `box` mark reaches GitHub.

## What Session 420 handed on

After the owner's push of `29d67fc` and `c278c85`, check the newest GitHub run on `main` is green with `gh run list --limit 1`, per tasks.md's Session 420 block. *(For: session)*

## Session 420: CI is green again

Opened on Session 419's Next action. Code in `c278c85`.

- **Seen:** GitHub run `40100822374` on `181523f` passed. `60872fe`
  is an ancestor of `origin/main`, so `SNAG-TEST-019`'s fix is
  confirmed on GitHub, not only on the box. The last red run was
  `40072243834` at 06:57.
- **Fixed:** the pre-push gate's blinded half failed 31 tests at this
  session's close, on a DNS error. Two files fetch coverage through
  `uv run --with`, which re-reads PyPI's index once uv's cached copy
  is stale, and the namespace has no route out. Session 419's run had
  fallen inside a fresh cache. `c278c85` sets `UV_OFFLINE=1` in the
  wrapper; the half then passed, 4547 tests.
- **Rejected:** marking those tests `box`. They need the network, not
  the box, and CI has the network, so the mark would only lose them.
- **Unseen:** no GitHub run has yet covered `29d67fc` or `c278c85`.
