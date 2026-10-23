# Handoff — 2026-10-23 (Session 412)

## Next action

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

## What Session 408 handed on

Rewrite STATUS.md's Alerts paragraph to name all five open rows, so its alerts and open_titles claims read ok, per tasks.md's Session 408 item. *(For: session)*

## Session 408: the blip row reads the service's own log

No open snag could be started. `SNAG-SVC-001` (P3) waited only on the
owner, who ruled (b): give the `check_interval` row evidence rather than
delete it. Closed in `d604dfd`; daemon restarted onto it at 21:08:24
(PID 2577593, `/api/health` healthy).

- **What it does now:** the row reads the service's `error`/`critical`
  log lines within 60 s of each one-check blip. A fault at any blip
  says leave the check alone. Quiet at every blip, from a service that
  logs faults elsewhere, points at the check. No declared `log:` (28 of
  48 services), or no fault all window, keeps the old volume-only
  wording at `evidence: rate`.
- **Decided:** one `log_actions.correlate` call per blip. Rejected a
  single call over the window: its anchor rule lets a line 61 s early
  claim the line 5 s early and leave the blip uncorroborated. The test
  for this went red under the whole-window version.
- **Decided:** 60 s is invented and says so (six HTTP probe timeouts).
  A coincidence errs toward "leave the check alone", and a corroborated
  row prints the chance figure.
- **Measured:** the retired check reported `mismatch` on its import limb
  alone, with `known_noise` rule 3 unmoved. No service is blip-shaped
  today (alfred-telegram has 1 one-check outage, needs 3), so the live
  route serves what it did. Driven at a threshold of 1, alfred-telegram
  took the no-log branch on real data.
- **One commit mixes code and prose, on purpose:** `snag_list.md`'s
  closure is in `d604dfd`, because a test pins each check to its
  entry's marker both ways; precedent `b8e421f`.
- **Second concern, recorded in tasks.md, not worked:** STATUS.md's
  Alerts paragraph names 3 of 5 open rows. The other two are
  estate-manager's audit alerts, opened today. That is the next action.
- **Not mine, unchanged:** `SNAG-LOG-022`'s three red journal tests.

## What Session 407 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 407: the quotation instrument matches tokens

Fixed in `a68ab33`: `check_unmarked_sentence_invisible`, the check
behind `SNAG-ESTATE-012`, no longer reads `mismatch`. Its two red tests
in `tests/test_snag_claims.py` pass.

- **Cause:** the check subtracts the baseline report's words as tokens,
  then searched the second drive for the survivors as substrings. Alert
  `estate-manager-audit-timer critical`, open since 05:05 today, is one
  token, so the specimen's `estate-manager` survived and was found
  inside it. Both drives now compare token sets.
- **Measured:** the new test injects that title into both drives and
  goes red against the substring search. The check's 17 tests pass.
- **Rejected:** splitting words at hyphens. `estate-manager` is the
  first specimen's only distinctive word, and would split into two words
  the baseline already uses.
- **Second concern, recorded as `SNAG-LOG-022` and in tasks.md, not
  worked:** the full suite has three other reds, the same with or
  without this fix, in `tests/test_services_registry.py`. Each is a
  premise failure: no journal records for an estate-manager unit. The
  journal now starts 2026-10-19 08:06, because `baloo_file_extractor`
  crash-loops (172k core dumps today, 3.1M of 4.0M journal lines). The
  records do not come back when the loop stops: the timer's need the
  next boot, `estate-manager-review`'s its next run on 2026-10-26.
  Until then the pre-push suite is red on those three.
- **Owner's step, taken:** `balooctl6 disable` at about 15:55; the owner
  parked the rest as probably inconsequential. Their Deadlock stutter
  matches the loop only on 10-20's evening (bursts at 18:00 and 20:30).
  `SNAG-LOG-022` closes when the three tests pass again.
- **Not mine, unchanged:** the postflight's STATUS.md alerts figure, 3
  stated against 5 measured, recorded by Session 406.

## What Session 406 handed on

Find why check_unmarked_sentence_invisible now reads mismatch: two tests in tests/test_snag_claims.py have been red since before Session 406. *(For: session)*

## Session 406: the preflight reads only `## Scheduled action`

Fixed in `622cd92`: the awk in `scripts/claude-preflight.sh` matches
the heading whole instead of any heading containing "scheduled".

- **Measured:** this session's preflight printed no scheduled section;
  before the fix it printed Session 392's block. Both new tests in
  `tests/test_handoff_shape.py` go red with the old awk restored.
- **Rejected:** a case-insensitive match. The estate recommends the
  exact heading `## Scheduled action`, and a looser match is how this
  bug came in.
- **Second concern, recorded in tasks.md, not worked:** the postflight
  found the suite red. `check_unmarked_sentence_invisible` (the check
  behind `SNAG-ESTATE-012`) reads `mismatch`: an unmarked STATUS.md
  sentence now reaches the report. Its two tests in
  `tests/test_snag_claims.py` were already red at `2f98465`, before this
  session, so the pre-push suite is red on them.
- **Next action:** that red check. The mosquitto check (tasks.md,
  Session 404) still needs the next boot; the box has been up since
  2026-10-18 10:16.

## What Session 405 handed on

Fix the preflight's scheduled-section match in scripts/claude-preflight.sh to take only `## Scheduled action`, per tasks.md's Session 404 item. *(For: session)*

## Session 405: no open snag could be started

The published next action asked for the highest-ranked open snag a
session can start now. There was none, so the session fixed the one
register fault the preflight reported. No code changed.

- **Measured:** every open entry is decided, blocked or delegated.
  `SNAG-LOG-021` waits on a boot, and the box has not booted since
  2026-10-18, before estate-manager changed the gate. `SNAG-LOG-012`'s
  check still holds: estate-lib's `strip_markdown` keeps backticks.
  `SNAG-TEST-014`'s probe record holds 387 runs, all `closed`.
- **Fixed:** `SNAG-TEST-014`'s status read `Open — decided:`, and the
  disposition reader took `decided:` as the word, so the preflight
  counted it as declaring nothing. Now `Open — decided, P3:`.
- **Rejected:** letting `disposition_word` strip a trailing colon. Its
  docstring says the strict parse is deliberate, and the other 37
  entries already use the comma form.
- **Next action chosen from tasks.md:** the preflight's scheduled-section
  bug Session 404 recorded is the one item a session can start now; it
  made this session's preflight print Session 392's block as a
  scheduled action.

## What Session 404 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 404: venture-embed stops declaring holds_vram

Closed `SNAG-GPU-008` in `1687713` and restarted the daemon onto it at
2026-10-21 17:40:06 (PID 565829, `/api/health` healthy).

- **Why this one:** every open entry is decided, blocked or delegated
  except `SNAG-GPU-008` and `SNAG-LOG-021`, and both had moved.
  venture-assistant settled the start-order race on 2026-10-17 with
  `-dev none` (their `e05894c`, closing estate message `d07f4176`).
- **Measured:** both `venture-embed` starts since then, one after boot
  and one at boot, logged `CPU compute buffer size = 564.22 MiB`. The
  first poll after the restart, 17:45:06, wrote `venture-embed`'s row
  with no `gpu_context` term and the two declared servers' rows with it.
- **Decided:** drop the declaration. Rejected keeping it: a reset can
  no longer reach the process, so it would read `degraded` after every
  reset. Recorded, not filed (ADR-0007 §2.5): if `-dev none` is ever
  dropped, nothing here notices.
- **Estate message `571f2f12` closed** by estate-manager at 15:51,
  after Session 403 began: taken as asked (their `69b11db`, ADR-0259).
  The mosquitto gate now waits up to 15 s for the address. `SNAG-LOG-021`
  is blocked on the next boot, and tasks.md has the check.
- **Second concern, recorded in tasks.md:** the preflight takes any
  `##` heading containing "scheduled" as the scheduled section, so it
  prints Session 392's block as a scheduled action.

## What Session 403 handed on

Run the preflight and work the highest-ranked open snag it lists that a session can start now. *(For: session)*

## Session 403: the route's condense pass waits out its own first pass

Closed `SNAG-GPU-007` in `baa48ca`, and restarted the daemon onto it
at 2026-10-21 16:53:03 (PID 271346, `/api/health` healthy), so the
three `POST …/review/generate` routes now condense a long first pass
as the Monday jobs do.

- **Owner's standing ruling (2026-10-21):** a session may run the
  no-sudo daemon restart itself, `kill -TERM` on the main PID, without
  handing it on.

- **Why this one:** every P3 entry is still decided, blocked or
  delegated. `SNAG-API-006` is decided, `SNAG-GPU-008` waits on a
  restart and `SNAG-LOG-021` on the estate's answer to `571f2f12`.
- **Decided:** `generate(follows_own_inference=True)` on the condense
  call polls the busy counter every 0.05 s until it reads idle, for at
  most 1 s, then takes its usual single read. Our own tail lasts one
  50 ms sample (six of eight drives); another holder's 96–99 % does not
  drain and is still refused.
- **Rejected:** `gpu_lease_held=True` on the second call (it claims a
  hold nobody has), a lease on the route (a queue wait inside a
  request), and `sustained_busy` (a fixed ~1.5 s window, refused by its
  own docstring where a request is held open).
- **Live A/B** through `LLMClient` on the card: 0 of 5 unleased second
  calls answered without the wait, 5 of 5 with it.

## What Session 402 handed on

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

## Older sessions

Sessions 385 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
