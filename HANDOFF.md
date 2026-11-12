# Handoff — 2026-11-12 (Session 445)

## Next action

Read the kernel journal with `_TRANSPORT=kernel` so a reboot loses no lines: finding H3 in `docs/review/bug-review.md`. *(For: session)*

## Scheduled action

- 2026-11-22, after 03:00: STATUS.md's timed prediction falls due.
  Measure the shared instants again, then rewrite or replace it.
- 2027-02-01: the owner reads the v2 list in `ideas.md`; the
  manifest's `freeze.until` carries the same date.

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

## What Session 437 handed on

Re-measure STATUS.md's opening block (tasks.md, Session 436's last item); the daemon has since restarted again, at 2026-11-04 09:34. *(For: session)*

## Session 437: the freeze is declared in the manifest

Opened on estate message `94a1713e-4c05-4a14-8f29-1ba5b599ee70`
(estate-manager): the `freeze:` key was safe to write. Manifest in
`d59ffe8`. Both estate messages, it and `64a3782e`, are closed.

- **Checked both conditions first:** `sysadmin.service` started at
  09:34:18 GMT, and estate-manager's board row carries a `freeze`.
- **Dates chosen:** `since: 2026-10-30`, when 1.0's second item closed
  (`e983696`), and `until: 2027-02-01`, from the owner's ruling. I did
  not use the estate template's 2026-11-04 and 2027-01-04, which are
  its own dates.
- **Verified:** `load_registry` parses the key; `/api/projects/managed`
  still serves 42 projects. The board shows `null` for this row until
  its next scan (04:30, or when the registry changes).
- **Corrected:** Session 436 wrote *For: none* while its own
  STATUS.md re-measure task stood open and startable; it is now the
  Next action.

## What Session 436 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 436: the blinded push half hides the rest of the box

Opened on the owner's request: fix `SNAG-TEST-020`, a known issue under
the freeze. Code in `35c26f0`.

- **Confirmed first:** a probe of the four `box` resources passed 5 of
  5 inside `scripts/pytest-without-the-box.sh`.
- **Fix:** `unshare -rnm` and an empty tmpfs over six directories (the
  script's header lists them). The entry's reason for leaving it, that
  all of `/home/gaddi` had to go and so needed fresh clones, was wrong:
  only those six do.
- **Caught one:** `test_an_absent_unit_is_indistinguishable_from_an_untriggered_one`
  reads `systemctl --user`; marked `box`, like its sibling premise.
- **Rejected:** leaving `/run/user/<uid>` visible, because the box's
  running user manager would still answer; and starting a fresh
  `systemd --user` inside the namespace, too heavy for one test.
- **Stated limit:** the rest of `~/projects` stays visible; the `box`
  mark does not cover it. The blind is stricter than the runner, which
  has a journal and a user manager of its own.

## What Session 435 handed on

No work is startable: the feature freeze admits only a bug fix or what an incident forces, and the dated items wait under Scheduled action. *(For: none)*

## Session 435: the disk alert on / closes

Opened on Session 434's Next action, the owner's. No code.

- **The target was 139 GB, not one game.** The monitor reads psutil's
  percent, used ÷ (used + free), which leaves out root's reserved
  blocks: 88.3 % where `df` size gives 84 %. Under 80 % needed
  `/` at 1,328 GB used or less.
- **The owner uninstalled** War Thunder (91 GB), ELDEN RING (55 GB) and
  Pillars of Eternity (47 GB) through Steam; the `steam://uninstall`
  links errored. 260 KB of leftover files stay in two `common/`
  folders.
- **Measured:** the 15:27:10 snapshot read 76.5 %, and
  `High disk usage on /` resolved at 15:27:14, its first cycle.
  STATUS.md's Alerts paragraph now names one open row; the claim check
  reads 14 of 14 `ok`.
- **Left alone:** Baldur's Gate 3 and Oblivion Remastered have
  manifests but no game folder, so Steam lists them as installed;
  their shader caches hold about 6 GB.

## What Session 434 handed on

Free space on / by uninstalling a Steam game you no longer play, so the 88 % disk alert falls under its 80 % threshold and closes. *(For: owner, ~10 min)*

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
