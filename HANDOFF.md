# Handoff — 2026-10-21 (Session 402)

## Next action

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 402: mosquitto's boot refusal is asked of the estate

Worked `SNAG-LOG-021`, the self-closing `Failed to start` warning that
estate-manager's mosquitto gate causes on every boot. Its preferred fix
is in their drop-in, so this session filed estate message
`571f2f12-f7fc-46d6-89ae-5d9488c67e5e` asking whether the gate could
wait for the address, bounded, instead of refusing. The snag stays open
on their answer. No code changed.

- **Why this one:** every P3 entry is still decided, blocked or
  delegated, and `SNAG-API-006` and `SNAG-GPU-008` are as Session 398
  left them.
- **Measured:** 5 boots under the gate, one `warning` row each, closing
  about 16 minutes later. `eno1` came up 3.9–4.6 s after the refusal on
  the four readable boots.
- **Found:** the shape as the snag wrote it would break the gate's
  promise. A wait inside each attempt spaces the attempts about 20 s
  apart, so the 30-in-180 s start limit never trips and a missing
  address retries for ever. The message says the limit would have to
  change with it.
- **Rejected:** shape (b) for now, pairing the two lines of one start
  job in the aggregator. It asks more of this side and is only needed
  if the estate declines.

## What Session 401 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 401: the daemon runs `e35fd40`

The owner's prompt asked for the restart Session 400 handed on, and this
session's own `kill -TERM` went through; Session 398's was refused. The
daemon came back at 2026-10-21 15:25:08 (PID 3315955, two restarts
counted). `/api/health` answers `healthy`, and `/api/services/reliability`
and `/api/services/actions` answer 200 in 1.0 s and 2.7 s. STATUS.md's
deploy sentence carries the new start time; every other ops claim
re-measured green. No code changed.

- **Archived:** Sessions 380–383 moved to HANDOFF-archive.md unedited,
  because this file stood at 501 lines against estate rule 2's 500.

## What Session 400 handed on

Restart the daemon onto `e35fd40`: `kill -TERM $(systemctl show -p MainPID --value sysadmin.service)`; Restart=always brings it back. *(For: owner, ~2 min)*

## Session 400: the advice reads stream in partitions

Closed `SNAG-SVC-008` in `e35fd40`, with a test stand-in in `7d61be7`.
**A restart is owed**: until then the daemon reads whole results, and a
request behind `/api/services/actions` can still wait up to 0.66 s.
After it, STATUS.md's daemon start time reads stale until a session
updates it, and the next session goes back to the highest-ranked open
snag.

- **Why this one:** every P3 entry is still decided, blocked or
  delegated, and `SNAG-API-006` and `SNAG-GPU-008` are as Session 398
  left them.
- **Decided:** a server-side cursor on the session's Core connection,
  2,000 rows a batch. Worst wait 0.66 → 0.27–0.35 s, measured in
  Session 333's probe rebuilt, pre-fix and fixed in the same harness.
- **Rejected:** `session.stream`. It halved the wait too, but the ORM's
  per-row loading wrapper was a quarter of the GIL samples and adds
  nothing to column reads. Partition size: 500 and 10,000 were within
  noise of 2,000.
- **Left, not filed:** the rest is the shared GIL itself. Pure-Python
  CPU on the same worker sets a 0.13 s floor under the quota, and 0.35 s
  is 85× below the 30 s watchdog ping.
- **Slip:** a zsh loop over an unsplit `$FILES` made the first green-cut
  check run against the fixed code. Nothing was lost; the check was
  re-run in a worktree at `7d61be7` (227 passed).

## What Session 399 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 399: the daemon runs `99f52ab`

The owner ran the restart Session 398 handed on, from this session's
prompt, after the permission check refused this session's own `kill
-TERM` again. The daemon came back at 2026-10-21 12:33:27 (PID 2250559,
one restart counted) and `/api/health` answers `healthy`, so a run of
an agent already running is now declined live. STATUS.md's deploy
sentence carries the new start time, and its alerts sentence drops
`venture-chat unreachable`, which resolved once the unit came back at
11:09: the preflight measured 3 open rows against the block's 4. Every
ops claim re-measures green. No code changed.

## What Session 398 handed on

Restart the daemon onto `99f52ab`: `kill -TERM $(systemctl show -p MainPID --value sysadmin.service)`; Restart=always brings it back. *(For: owner, ~2 min)*

## Session 398: a run of an agent already running is declined

Closed `SNAG-AGENT-014` in `99f52ab`. **A restart is owed**: the
daemon still runs the code it started with at 2026-10-20 20:25:27, so
until then a manual scan can still overlap a scheduled run, as before.
This session's `kill -TERM` was refused by the permission check, so it
is the owner's. No sudo is needed while the daemon is up. After it,
STATUS.md's daemon start time reads stale until a session updates it,
and the next session goes back to the highest-ranked open snag.

- **Also:** STATUS.md's alerts sentence now names a fourth open row,
  `venture-chat unreachable` (10:55, `info`; the unit is inactive). It
  is venture-assistant's unit, so it was named and not acted on.

- **Why this one:** every P3 entry is decided, blocked or delegated.
  `SNAG-API-006` is decided, and `SNAG-GPU-008` waits on a reset after
  a boot start.
- **Decided:** decline, not wait. The running run is already doing the
  work. A scheduled run is `asyncio.run` in a worker thread and a
  manual run is on the API loop, so the lock is a `threading.Lock`,
  taken without blocking. A blocking cross-thread wait could be left
  held by a cancelled waiter.
- **Rejected:** the snag's `asyncio.Lock`. It cannot serialise two
  event loops.
- **Found:** the overlap also shared `_pending_events` between threads,
  which the snag had not named. The same lock closes it.
- **Slip:** the first falsification ran without a bound and hung, and
  `pkill -f` then killed its own shell, leaving `agent.py` mutated for
  a minute. Restored from a scratch copy and checked by grep; the tests
  now bound every wait on a run that should not start.

## What Session 397 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 397: go-to-market's API on 8950 is watched

Acted on estate message `495f072e`. go-to-market had already committed
its `go-to-market-api` entry to `services.yaml` (`970ba50`, reviewed in
`f98d896`), so this session only applied and checked it.

- **Decided:** a hot reload instead of the restart the message
  expected. The reload re-reads `services.yaml`, and the restart needs
  the owner's `sudo`. It reported `services_added: go-to-market-api`
  and nothing needing a restart. The first poll stored the entry `ok`.
- **Token:** sent the reload with the copy systemd delivered to
  `/run/credentials/sysadmin.service/api-token`, the same file the
  tray reads.
- **Closed** the message with a note.

## What Session 396 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 396: the roll-up sat unread five days, not eight

Closed `SNAG-DOCS-033` in `2ec118d`. Docstrings and prose only, so no
restart is owed. The postflight's "daemon serves the code on disk"
check still reads ✗, because it compares file times, until the next
restart for any reason.

- **Why this one:** every P3 entry is decided, blocked or delegated.
  `SNAG-GPU-008`, the P4 above it, waits on a GPU reset after a boot
  start, which has not happened.
- **Decided:** "five days", not the snag's "a day". `sysadmin.alerts`
  holds the roll-up open from the detector's first run (2026-08-07
  10:20) to 2026-08-12 16:08, re-titled at each count change. "A day"
  was only the `17 findings` title's age.
- **Rejected:** fixing `scan.py:947` and `agent.py:839`. They speak of
  the loop's eight days, which is true, as the snag ruled.
- **Found:** two sites outside the snag's sweep, plus the design doc's
  copy of `agent.py`'s sentence. Also removed a stray `Status: Open`
  line under the closed `SNAG-TEST-017`.

## What Session 395 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 395: the idle-queue assert is declared

Closed `SNAG-TEST-017` in `74b919d`, test-only, so no restart is owed.

- **Decided:** a `# may-not-evaluate:` declaration above
  `tests/test_arbitrated_stops_live.py:210`, naming the recorded half's
  `test_no_active_lease_is_idle_and_not_unread` as the witness, which
  asserts the same predicate on every run.
- **Rejected:** a new projected-idle witness in the live file. It
  repeats the recorded test and leaves line 210 unevaluated under a
  lease, so it needs the declaration anyway. Session 394 rejected a
  declaration for `SNAG-TEST-016` because that assert could not fail;
  this one fails on any idle run, so the reason does not carry over.
- **Checked** at the gate's reader, not the full gate: the queue was
  idle, so a full run would have evaluated the line. With the line
  marked unexecuted, `74b919d~1` reads undeclared and `74b919d` declared.
- **All three entries of this shape are closed** (`SNAG-TEST-016`,
  `-017`, `-018`). The next pick is the preflight's.

## What Session 394 handed on

Give `SNAG-TEST-017`'s idle-queue assert a witness or a declaration, the same shape `SNAG-TEST-016` closed with in `7881ca3`. *(For: session)*

## Session 394: four alerts named, and the off-loop assert has a witness

Code in `7881ca3`, test-only, so no restart is owed.

- **Alerts sentence rewritten**: 4 open rows, all named; the new one is
  `Project clyde-automation-site next action idle`. The ProductHunt 429
  Session 393 saw had resolved. Every ops claim reads `ok`.
- **Closed `SNAG-TEST-016`**: the dependency reader in
  `tests/test_off_loop.py` is a helper now, also driven on
  `/api/units/status`, which takes the request session. Blinding the
  reader turns that test red. The vacuous-guard gate exits 0, for the
  first time since 2026-10-08.
- **Decided:** the witness alone. Rejected: a `# may-not-turn:`
  declaration, which silences the gate and leaves the assert unable to
  fail.
- **Why `SNAG-TEST-017` is next:** it is the last undecided entry of
  this shape. The gate reports it only while a GPU lease is held at
  close, so this session's clean run does not show it.

## What Session 393 handed on

Rewrite STATUS.md's alerts sentence to name every open row the preflight measures, then work the highest-ranked open snag a session can start now. *(For: session)*

## Session 393: the GPU-context reader fired on real resets

Closed `SNAG-GPU-001` (the P2 entry saying a poisoned inference server
reports `ok`) on measurement alone. Docs only, so no restart is owed.

- **Why this one:** Session 392 passed over the P2 entry as decided. Its
  rank was waiting on the first real reset since the 2026-09-08 fix, and
  three had landed on 2026-09-30 without any sitting reading them.
- **What the reading found:** both declared servers were flagged
  `degraded` one poll after each reset was ingested. `venture-chat`
  aborted on its first submission both times, and served nothing while
  flagged. The `degraded` alerts opened 53 minutes before the first
  abort. The full figures are in the entry.
- **Limit, recorded in the entry:** `llama-server` was never submitted to
  while flagged, so on its own it shows no false alarm rather than a
  confirmed poisoning. `venture-chat` is the same build and supplies the
  confirmation.
- **Not worked:** STATUS.md's alerts sentence is stale. The block names
  3 open rows; the preflight measured 4 at start and 5 at close, the new
  ones being `Project clyde-automation-site next action idle` and a
  ProductHunt 429 from `venture-assistant-backend`. Recorded in
  `tasks.md` under Session 393. It is the next action.
- **Postflight's vacuous-guard gate** still names only
  `tests/test_off_loop.py:99`, which is `SNAG-TEST-016`, open.

## What Session 392 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 392: the scheduled-section assert is declared

Closed `SNAG-TEST-018` in `0b5a39b`, test-only, so no restart is owed.

- **Decided:** a `# may-not-evaluate:` declaration, as the snag proposed.
  Rejected: treating an absent `## Scheduled action` section as an empty
  one, which makes the assert run over nothing and silences the gate
  without making it say anything.
- **The gate still exits 1**, now only on `tests/test_off_loop.py:99`
  (`SNAG-TEST-016`, open). No entry is declared owed any more;
  `SNAG-TEST-016` and `SNAG-TEST-017` are the same shape and carry no
  disposition yet.

## What Session 391 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 391: the API token is a systemd credential

Closed `SNAG-API-005`'s token half. Code in `4ef799f` and `17701c9`; the
owner installed the unit and the credential at 20:25:27, and the tray was
restarted onto its new code at 20:26:14.

- **Every POST to :8500 now needs a bearer token**, including a session's
  `POST /api/sysadmin/reload`: send
  `-H "Authorization: Bearer $(cat /run/credentials/sysadmin.service/api-token)"`.
  A 401 there means a missing header, not a missing handler. `kill -HUP`
  needs none.
- **Decided:** a fixed credential id `api-token` in `/etc/credstore`,
  with the tray reading systemd's delivered copy so the two cannot
  disagree. Rejected: a token file in the home directory (could drift
  from what the daemon loaded) and a config key for the id (a mismatch
  with the unit fails open).
- **Decided:** the tray reads the token per request and scoped to the
  daemon's origin. The old client-wide header would have sent a real
  token to the estate on 8400.
- **Not used:** `scripts/setup-systemd.sh` under `pkexec`. It takes the
  user from `SUDO_USER`, which `pkexec` does not set, so it would install
  the tray unit under `/home/root`.
- **Limit recorded:** `SNAG-API-006`, the owner's own processes can read
  the token as the tray does.

## What Session 390 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 390: the token surface becomes a standing rule

The owner asked for estate message
`21860cb6-753f-42f5-954c-7ea872a4be83` to be acted on. Docs only; no
restart owed.

- **CLAUDE.md now says how to mint, use and revoke** a
  `sysadmin-assistant` token for Alfred's planner (section "Writing to
  Alfred's planner"), driven once: whoami labelled, revoke 204, then 401.
- **Message closed.** Session 389 left it open because a close note would
  claim the surface was used; the note says it was recorded and driven,
  not used for a task, so it claims nothing false.
- **Decided:** mint-and-revoke to test the recipe. Rejected: writing a
  planner block, since no open task needs downtime or `sudo` (checked
  tasks.md and the open snags).

## What Session 389 handed on

Carry out a downtime or sudo task through Alfred's planner with a `sysadmin-assistant` token, then close estate message `21860cb6-753f-42f5-954c-7ea872a4be83`. *(For: none)*

## Session 389: Alfred's `sysadmin-assistant` token surface

Docs only; no restart owed.

- **Estate message `21860cb6-753f-42f5-954c-7ea872a4be83` read and
  logged** as a task in tasks.md Session 389. It is informational: the
  surface exists, nothing here had to change.
- **Decided:** leave the message open. Its close note would claim the
  surface was used, and it has not been; closing cannot be undone.
  Rejected: minting a token now to "act on" it, which would write to
  Alfred for no task.
- Also ticked the STATUS.md duplicate `Last Updated` task (done in
  `d75e751`).

## What Session 388 handed on

Delete the older duplicate `**Last Updated**` line from STATUS.md, done in `d75e751`.

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

## Older sessions

Sessions 383 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
