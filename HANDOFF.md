# Handoff — 2026-11-13 (Session 448)

## Next action

Nothing is startable under the feature freeze; the scheduled items below carry the next work. *(For: none)*

## Scheduled action

- 2026-11-22, after 03:00: STATUS.md's timed prediction falls due.
  Measure the shared instants again, then rewrite or replace it.
- 2027-02-01: the owner reads the v2 list in `ideas.md`; the
  manifest's `freeze.until` carries the same date.

## Session 448: the idle-nudge rows are named, not set aside

Opened on Session 447's Next action.

- **Withdrawn:** the `<!--check:rotating-->` set-aside of
  `Project % next action idle` in STATUS.md's Alerts paragraph. Two
  members are at `warning`, and the check reads those as asking for
  action. The paragraph now names all four open rows and counts 4.
  Kaggle's `info` row is counted too, because without the set-aside
  every row counts.
- **Retired** (`8ce8732`): the live class
  `TestTheRealBlockDeclaresTheNudgeFamily` in
  `tests/test_ops_claims.py`. Its two tests asserted that the real
  block declares the family, so they could not pass once the
  declaration was gone. The rule stays tested by the synthetic
  `TestTheFamilyIsJudgedBySeverity`. The collected count went from
  4765 to 4763.
- **Decision reversed:** Session 438 kept the declaration instead,
  so as not to delete a guard under the freeze. Its reasons, and the
  answer to each, are under the ticked task in `tasks.md`.
- **Cost accepted:** these rows turn over most mornings, so the count
  and the names will drift, and the preflight will report each drift.
  That cadence is what the set-aside was added to avoid
  (`SNAG-DOCS-035`).
- **Also fixed:** `config.yaml`'s comment on `api.auth_token` said
  "stale-cache clean", a route finding H1 removed; it now says "file
  cleans".
- **Tested:** `check-ops-claims.sh` reads `ok` on every claim, and
  `tests/test_ops_claims.py` passes, 228 tests.

## What Session 447 handed on

Name the two idle-nudge rows above `info` in STATUS.md's Alerts paragraph and drop that family's set-aside: the open task in `docs/roadmap/tasks.md`. *(For: session)*

## Session 447: the toast's Restart and Snooze buttons fire (finding H4)

Opened on Session 446's Next action.

- **Fixed** (`bcfec3c`) `DbusNotifier`'s two slots in
  `sysadmin_tray/notifications.py`. They are declared `"uint"` instead
  of `int`. The freedesktop signals are `ActionInvoked(us)` and
  `NotificationClosed(uu)`, and QtDBus calls a slot only when its
  signature matches, so the `int` slots were never called.
- **Tested:** a new test, `tests/test_tray/test_notification_signals_live.py`,
  starts a private `dbus-daemon`, runs a stand-in notification server
  in its own process, and has it send both signals with `uint` ids to
  the real `DbusNotifier`. It passes in 0.17 s, and fails at its first
  verdict with `int` put back. It also passes inside the no-box
  namespace the push runs in.
- **Option rejected:** a stand-in in the same process as the tray, on
  the main thread or on a `QThread`. Constructing the notifier then
  waited out the 25 s D-Bus timeout, because `QDBusInterface`
  introspects the server with a blocking call.
- **Live:** `sysadmin-tray.service` restarted at 08:17:16 and runs the
  fix. Not driven against Plasma's own server, because that needs a
  real toast on the owner's screen. When one next appears, clicking
  Snooze should log `snooze requested via notification` in
  `journalctl --user -u sysadmin-tray`.
- **H-series done:** all four high findings of the bug review are
  fixed, so its task in `tasks.md` is ticked. The medium and low
  findings stay known issues under the freeze.
- **Archived:** Sessions 430 to 437 moved to `HANDOFF-archive.md`,
  unedited, to bring this file under the 500-line bound.

## What Session 446 handed on

Declare the tray's two D-Bus slots with `"uint"` so the toast's Restart and Snooze buttons fire: finding H4 in `docs/review/bug-review.md`. *(For: session)*

## Session 446: the kernel journal is read across boots (finding H3)

Opened on Session 445's Next action.

- **Fixed** (`212dd5b`) `read_journal` in `sysadmin/monitor/journal.py`.
  The kernel source is read by the match `_TRANSPORT=kernel` instead of
  `-k`. `-k` implies the current boot, so after a reboot the read
  `--since @floor` could not reach the lines logged before the crash.
- **Also fixed:** `journal_command` in `sysadmin/monitor/log_actions.py`,
  the command a log recommendation prints, had the same `-k`. Its
  docstring says the two must state the same fact, so both changed.
- **Tested:** one new test pins that neither the cursor read nor the
  window read carries `-k`, `--dmesg`, `-b` or `--boot`; it fails with
  `-k` put back. Two `journal_command` tests updated. Suite: 4,762
  passed, 2 skipped; ruff and mypy clean.
- **Live:** the real `read_journal` over the 2026-10-31 14:42 reboot
  returns 47 error and critical lines from before it, ending with
  `watchdog did not stop!`. `-k` returned none of them. The daemon
  restarted at 11:20:36 and `/api/health` answers 200.
- **Not backfilled:** the 2026-10-31 lines are still not in
  `log_entries`, because the resume floor is past them. The fix covers
  the next reboot.
- **Limit, unchanged:** the first read after a reboot is still bounded
  by `-n` (500), which keeps the newest lines. A boot that logs more
  than 500 error lines before the first poll would push out the
  pre-crash lines, and `log_read_truncated` would say so. The current
  boot has logged 12 in twelve days.
- **Seen, not worked:** `check-ops-claims.sh` reads "no" on the
  idle-nudge family (two rows above `info`). That is the open
  Alerts-paragraph task in `tasks.md`.

## What Session 445 handed on

Read the kernel journal with `_TRANSPORT=kernel` so a reboot loses no lines: finding H3 in `docs/review/bug-review.md`. *(For: session)*

## Session 445: duplicate groups are confirmed by full content (finding H2)

Opened on Session 444's Next action.

- **Fixed** (`a31c077`) `plan_duplicate_cleanup` in
  `sysadmin/files/actions.py`. The fingerprint (size plus MD5 of the
  first 1 MB) now only pre-filters. Each group is split by a
  full-content SHA-256, hashed once per inode. A group needs two
  distinct inodes, and links to the keeper are not planned.
- **Also guarded:** a keeper that vanishes between hashing and planning
  skips its group. Without that, the rest of the group would be planned
  with no copy kept; a test proves it by disabling the guard.
- **Tested:** five new tests. All five fail against the pre-fix
  planner. Suite: 4,761 passed, 2 skipped; ruff and mypy clean.
- **Live:** a dry run of the old and new planners against the real
  config plans the same 12,279 operations (2.1 GB). The five misgrouped
  sets the review found are under `~/projects`, which the action
  excludes, so the fix guards against a case that has not happened yet
  and changes no current plan. The daemon restarted at 08:07:34 and
  `/api/health` answers 200.
- **Fork:** the planner is fixed and the scan's report is not.
  `/api/files/duplicates` and the "frees at least 7.9 GB" figure still
  group by fingerprint and count hardlinks. They only display; the task
  named the planner.
- **Fork:** the full hash runs at plan time, not again at execute time.
  The route plans and executes in one request, so the gap is
  milliseconds.
- **Push:** `main` is 4 ahead of `origin/main`, and the pre-push gate
  allows 2. Session 444's two (`b371eb4`, `a8b4a75`) go first, then
  this session's two.

## What Session 444 handed on

Confirm a duplicate group with a full hash before `/clean/duplicates` plans it: finding H2 in `docs/review/bug-review.md`. *(For: session)*

## Session 444: the stale-cache clean is removed (finding H1)

Opened on Session 443's Next action.

- **Removed** (`b371eb4`) `POST /api/files/clean/stale-caches`, its
  contract model `CleanResultResponse`, the tray's "Clean stale caches"
  button with its dialog and client path, and the "Remove N empty
  directories" recommendation. The quick-wins card is display-only.
- **Live:** the daemon restarted at 21:34:56 and the route answers 404;
  the tray restarted at 21:35:01. Suite: 4,756 passed, 2 skipped.
- **Fork:** I kept the stale-caches recommendation and changed its
  action to "delete by hand". Deleting it too is the fix for finding
  M10 (the scan can never find a cache), which the task did not ask for.
- **Fork:** one code commit of 14 code files, carrying a three-line
  note in `tasks.md`, because the pre-commit hook refuses five or more
  code files without a tracking document. Splitting at four files each
  would have taken four commits, past the two a push allows.
- **Fork:** no announcement was filed. A sweep of `~/projects` outside
  this checkout found no reader of the route, the client method or the
  model.
- **Not done:** the directories the route could have removed were
  never removed by this session or the last; nothing needed restoring.
- **Stacked, recorded in `tasks.md`:** STATUS.md's Alerts paragraph
  names 1 of 2 open rows, and a stale comment in `config.yaml`.

## What Session 443 handed on

Remove `POST /api/files/clean/stale-caches`, its tray button and its recommendation: finding H1 in `docs/review/bug-review.md`. *(For: session)*

## Session 443: a bug review and v2 proposals

Opened on the owner's request for a two-phase review. No code, config
or existing document was changed by the review itself; the owner then
asked for this entry and the task below.

- **Wrote** `docs/review/bug-review.md` (`d1785f2`): 43 findings, 0
  critical, 4 high, 19 medium, 20 low, each with how it was verified.
  The suite was green beforehand (4,777 passed, 2 skipped).
- **Wrote** `docs/review/v2-proposals.md`: six proposals and an order.
  They are not yet lines under *v2* in `ideas.md`; the owner reads the
  file and decides which become lines.
- **Most serious (H1):** `POST /api/files/clean/stale-caches` removes
  the first 50 stored empty directories with no confinement, and 14 of
  them are inside the running PostgreSQL data directory under
  `~/projects/web/cv/private/funnel/pgdata`. The tray's "Clean stale
  caches" button calls it. Not executed. Avoid the button until fixed.
- **Fork:** rated H1 high and not critical, because the directories are
  empty and recreating them recovers the cluster.
- **Fork:** the four high findings are bug fixes, which the freeze
  admits, so they are one task in `tasks.md` and not v2 lines. Mediums
  and lows stay in the report as known issues until one bites.
- **Not done:** no finding was fixed. I re-ran the evidence for H1 and
  H3 only; the rest stand as the six slice reviewers verified them, and
  the report marks what is latent or unconfirmed.

## What Session 442 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 442: STATUS.md's opening block names the disk alert

Opened on Session 441's Next action.

- **Rewrote** the Alerts paragraph: 1 unresolved row,
  `High disk usage on /`, named in the `open_titles` sentence beside
  InvestingAssistant's idle warning. `check-ops-claims.sh` went from 3
  `no` lines to 1.
- **Measured the cause** from `resource_snapshots`: `/` stepped about
  75 GB between 16:24 on 2026-11-04 and 02:54 on 2026-11-05, 76 % to
  81 %. Files born at the first step are a World of Warcraft install
  under `~/Games/battlenet` (35 GB in its `Data/data` alone; the
  directory is 104 GB). `/` has sat at 79.8 to 82 % since, against an
  80 % warning line, so the row has opened three times since
  2026-11-05.
- **Fork:** I named the disk row rather than declaring it flapping.
  Declaring it would set aside a real disk-space warning; the cost is
  that each close turns the alert count into a mismatch again.
- **Fork:** I kept the idle-nudge family set aside, so the `rotating`
  check still reads `no` while InvestingAssistant's row is `warning`.
  Withdrawing the declaration, as the check suggests, would put five
  rows that turn over most mornings back into the count, the problem
  the declaration was made to solve.
- **Left for the owner:** whether to free space on `/`. Meanwhile the
  row stays open and the block names it.

## What Session 441 handed on

Re-measure STATUS.md's opening block: `scripts/check-ops-claims.sh` reads 3 mismatches, an unnamed alert and InvestingAssistant's idle warning. *(For: session)*

## Session 441: the freeze admits what an outside date requires

Opened on estate message `0c5ffb81-fbb1-4dd8-9643-b0567e7ada82`
(estate-manager), carrying the owner's 2026-11-08 ruling.

- **Added** to `CLAUDE.md`'s freeze rule 2: beside a bug fix and an
  incident's fix, work a date someone else set requires (an interview,
  an application deadline, an assessment), when the task or commit
  names the date and who set it and the work does no more than that
  date needs. A date the owner or an agent set does not count, and
  *moves an aim* alone exempts nothing.
- **Fork:** I wrote the clause in brief with a pointer to
  estate-manager's `monitorable-project.md` §2.4, not a pointer alone,
  so rule 2 still reads whole where a session meets it. The cost is a
  second wording that can drift; §2.4 is named as canonical.
- **Not touched:** `.project.yaml`'s `freeze:` key, which the ruling
  leaves as it is. No outside date bears on this repository today, so
  nothing is startable under the new clause.
- **Second concern, recorded not worked:** `check-ops-claims.sh` reads
  STATUS.md's opening block stale (3 `no` lines, the same before this
  session's edits). A task in `tasks.md` under Session 441, and the
  Next action.
- **Closed** the message, its note naming this entry.

## What Session 440 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 440: the session-end hooks go, and a docs-only push skips the box

Opened on estate message `efcd2dab-f2f3-4682-80f1-27f00a70e91e`
(estate-manager), carrying the owner's 2026-11-04 rulings on their
estate audit's control review.

- **Under the freeze:** both rulings are the owner's, and the push
  ruling answers an incident in daily use: the audit read 5 docs-only
  pushes here held by box tests failing on the journal's state.
- **Deleted** `.claude/hooks/session-end-insights.sh` (it read
  `.user_prompt`, which Claude Code never sends) and
  `session-end-cleanup.sh`, with the hooks directory's README, which
  documented only those two, and the `hooks` key in
  `.claude/settings.local.json` that wired them. All of `.claude/` is
  gitignored, so none of this is in a commit. Left in place:
  `docs/insights/.session-log` (1,150 lines, gitignored), the cleanup
  hook's output. Nothing reads it, and it no longer grows.
- **The push skip** (`30c7230`): the `pytest-box` hook in
  `.pre-commit-config.yaml` now has `always_run: false` and
  `exclude: '\.md$'`, so pre-commit skips it when every file the push
  changes is Markdown. Driven with `pre-commit run pytest-box
  --hook-stage pre-push`: `81aaf32` (three .md files) skips; `ba5788e`
  (`config.yaml`) and `35c26f0^..77045f2` (.md with .py and .sh) run
  all 135 box tests.
- **Fork:** I keyed docs on `\.md$`, not on `docs/`. `docs/` holds a
  YAML file, and five Markdown files sit at the root. A push that only
  deletes code passes no file to pre-commit, so it too skips the box
  half; the not-box half, ruff and mypy still run.
- **Cost, accepted under the ruling:** a docs-only push that rewords
  STATUS.md's declarations is no longer checked against the alerts
  table at push (`TestTheRealBlockDeclares*` in
  `tests/test_ops_claims.py`). `scripts/check-ops-claims.sh` still
  reads it at each end of a sitting.
- **No ruling, nothing done:** the audit's 4 forced failures of the
  counter kind ("Sixteen" where a test wants "16").
- **Alfred's close note** on message
  `7ae19707-e932-451f-af4e-466be82fac18` (sent by Session 439): the
  09:43:18 poll opened a WoW span with `focus_known: true`, so the
  Wine/KWin pid question is answered yes and nothing is owed. Session
  439's entry already records the same reading; nothing to tick.
- **Moved** Sessions 420 to 429 to `HANDOFF-archive.md`, unedited:
  this file was 523 lines, over estate rule 2's 500.

## What Session 439 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 439: World of Warcraft joins the game detector's list

Opened on estate message `3e91e0d7-52cd-4368-8f28-5fd19ddc0d1e`
(Alfred): add `Wow.exe: WoW` to `agents.game_detector.games` so
Alfred's Downtime lane gets WoW's sessions. Config only.

- **Under the freeze:** a configuration entry the owner asked for,
  read by the detector that already exists (ADR-0016). No code.
- **Name:** I used "WoW", Alfred's default, not "World of Warcraft".
  Alfred's hold (their ADR-0164 §4) matches the game name as a whole
  word in the owner's `Gaming|WoW` label, so the long name would count
  each session twice. It is not an owner ruling. If the owner names it
  otherwise, change the value.
- **Corrected the message:** it said a restart was needed. The agent
  reads `get_config()` on every poll (`sysadmin/games/agent.py:163`),
  and `game_detector` is in neither `RESTART_ONLY` nor any other
  restart-only list, so a reload delivers it. I sent SIGHUP to the
  daemon (pid 3283250) at 09:40:18. The reload logged
  `requires_restart: []`, and the next `game_detector` poll ran on it.
  `POST /api/sysadmin/reload` answered 401, because the daemon holds
  a token from systemd.
- **Verified live:** the owner started WoW during the session. The
  09:43:18 poll opened a `WoW` span (`matched_by: executable`) with
  `focus_known: true` and a `focused` stretch, so KWin's probe ties
  the Wine window to `Wow.exe`'s pid, the one thing Alfred's message
  had left unchecked.
- **Closed** the message, the note naming this entry.
- **go-to-market's close note** (message `f9784d62-cbdd-4b93-ac23-d6c7fb4ec478`,
  sent by Session 438): already recorded above in Session 438's entry
  and its tasks.md item; nothing new to tick.

## What Session 438 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 438: STATUS.md's opening block re-measured

Opened on the handoff's Next action. Docs only.

- **Measured first:** 4 of 13 claims read `no`: the daemon's start
  time, the alert count, the unnamed rows, and the rotating family.
- **The restart:** at 09:34:16 an estate-manager session ran
  `sudo systemctl restart sysadmin.service`, so the daemon would load
  the library that parses `freeze:`. Read from the journal's `sudo`
  line.
- **Waited for four `usb 7-1` kernel rows to close.** They opened when
  the headset receiver re-enumerated at 10:01, and closed at 10:17 as
  their kind always has. The block was written after that, so it does
  not name rows that were already closing.
- **Filed** go-to-market's failing copy job at go-to-market, estate
  message `f9784d62-cbdd-4b93-ac23-d6c7fb4ec478`; their handoff did not
  mention it. **Closed by the receiver:** go-to-market fixed the job in
  their `1a465b2` at 10:20, and the critical row closed at 10:24, so the
  block now counts 0 unresolved rows.
- **Fork:** I kept the `rotating` declaration and named
  InvestingAssistant's `warning` row. I rejected withdrawing the
  declaration, as the check advises: that reds two premise tests, and
  relaxing them would be code under the freeze. Cost: `rotating` reads
  `mismatch` at every preflight until InvestingAssistant's next action
  moves. The other 12 claims read `ok`.
- **Found, not worked:** a nudge row never rises to the estate's
  `warning` rung (kaggle's), because a held row is never escalated in
  place. Recorded in tasks.md as a known issue.
