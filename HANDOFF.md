# Handoff — 2026-11-26 (Session 468)

## Next action

Nothing here is startable until Sunday's WAL re-measure, listed under Scheduled action. *(For: none)*

## Scheduled action

- 2026-11-29 after 02:05 UTC: re-measure WAL against the baseline under
  Session 465 in tasks.md, once the Sunday expiry has run.
- 2026-12-20 03:00 UTC: STATUS.md's timed prediction comes due; the
  preflight reports it, then a session re-measures it.
- 2027-02-01: the owner reads the v2 list in `ideas.md`; the
  manifest's `freeze.until` carries the same date.

## Session 468: self-restart-three merged and live

Opened on Session 467's Next action. Merge `eb1dec5`.

- **The merge was the owner's word, asked for first.** The rulings make
  service control an always-review path that waits for his merge
  (`~/estate-audit/notes/working-weeks/rulings.md`, question 2). The
  Next action reached the session as its own text, so the session asked
  and he answered "merge".
- **Checked before the restart.** The push checks ran green on the
  merged main: 121 box tests and 4,525 others passed, ruff and mypy were
  clean. All five auto-restart units were active, so going live
  restarted nothing.
- **Restarted at 11:05:56 GMT**, PID 3205145, by `kill -TERM`. At boot
  the registry loaded 45 repositories and refused none, and the daemon
  loaded 53 services. The first sysadmin poll ran at 11:10:56 with no
  warning or error in the journal, and no service critical or
  unreachable.
- **Still owed:** a live `restart-failed`. None has been driven, because
  a deliberate failure would page the phone.
- **Close note** on `c61da678` (alfred-glance, 2026-11-26): logged in
  their ADR-0041 amendment, `1b6369c`. Nothing changes in glance. They
  note that the outage row and `restart-failed` come from one agent, so
  the second replaces the first in the same phone notification.
- **Told estate-manager** the parse is loaded: estate message
  `97e26582-58eb-4a71-a2bb-988fc6aa5bf9`, in reply to `97b41b41`.
- Left alone: Session 467's worktree, in that session's scratchpad, and
  the merged branch `self-restart-three`.

## Session 467: phone item 2 raised as its own critical, on the branch

Opened on Session 466's Next action. Code on branch `self-restart-three`
only (`356b6de`, `fdb9964`, `96a2515`, design docs `e2b04f3`, on merge
`d5f09c3`);
this entry and the task rows are on main.

- **A restart that did not bring a service back is now its own
  critical.** The title is `<service> restart-failed`, and the row
  carries `kind: "restart-failed"` on `estate/alerts/raised`. It is
  raised once a restarted service is still critical or unreachable a
  full streak after its restart: 3 polls, about 15 minutes. It is
  deduplicated, so it publishes once per outage. It closes on the
  first healthy poll, because the kind joined `SERVICE_ALERT_KINDS`.
- **Main merged into the branch first** (merge commit on the branch),
  because the `kind` field is on main only.
  - Rejected: a rebase, which would rewrite `27c3cc9` and `5e3dbee`,
    both cited by hash in this file and tasks.md.
- **Forks taken.**
  - Chosen: the same streak after the restart as before it, which is
    `auto_restart_after_checks`. Rejected: the first failed poll after
    the restart, 5 minutes on, because `alfred-inference` waits for the
    GPU before it starts and a slow start would page the phone.
  - Chosen: a row beside the outage row. Rejected: replacing it, which
    would let `_resolve_recovered` close the still-true outage row.
  - Chosen: `restart-failed` as a constant in `mqtt_alerts.py`, outside
    `OutageKind`. Rejected: widening `OutageKind`, which would let
    `services.yaml` declare a failed restart.
  - Not built: raising it at once when `systemctl` refuses to queue the
    restart. That case is still caught a streak later, and it already
    writes a warning saying "failed".
- **Tested in-process only**, with `raise_alert` and `restart_unit`
  mocked. Four new tests: the row on the right poll, none for an
  arbiter-stopped unit, none without a restart, and none written by a
  later run while it is open. The first goes red with the raise
  disabled. Branch suite in the worktree: 4,747 passed, 9 failed, all
  nine from its path or missing `.venv`. No real failed restart was
  driven, so the first live witness comes after the merge.
- **Announced first** to alfred-glance as estate message
  `c61da678-f6f8-426d-ba80-8d2dbd70e491`, in reply to `c2f77a4b`. The
  message says it is live only after the merge and a restart.
- **Close notes on this repository's filings**, both alfred-glance's,
  2026-11-26:
  - `c2f77a4b`: the owner ruled that glance keeps pushing every critical
    and decodes no `kind` yet (glance's ADR-0041, amended 2026-11-26).
    Glance keeps both units under "Alfred is down". It still wanted item
    2 announced, which `c61da678` does.
  - `caeb1df7`: logged in glance's handoff (their `64fbfd4`). Nothing in
    glance changes.
- **Logged** estate message `97b41b41` (estate-manager's `live_folder:`
  manifest key) as a task under Session 467. The daemon started 75 s
  before their parse landed, so the next restart is what loads it.
- **HANDOFF.md was 529 lines**: Sessions 449 to 454 moved to
  `HANDOFF-archive.md`, unedited.

## Session 466: Alfred's outages marked on the estate bus

Opened on Session 465's Next action. Code in `bbfd7e2`, a test fix in
`2783678`.

- **Every message on `estate/alerts/raised` now carries `kind`.** It is
  `"alfred-down"` for an outage of `alfred` or `alfred-frontend`, and
  null otherwise. Declared per entry as `outage_kind` in
  `services.yaml`, written to the row's `details.alert_kind`, read back
  by the publisher.
- **Forks taken.**
  - Chosen: a field on the existing payload. Rejected: a topic of its
    own, which breaks the module's one-topic rule and glance's
    topic-keyed renderers.
  - Chosen: carry the mark on the row. Rejected: threading it through
    `raise_alert`, which would touch `core/agent.py` too and leave the
    row without it.
  - Chosen: backend and frontend are "Alfred". Rejected: the backend
    alone, and every `project: alfred` entry, which would catch the
    non-critical bus and Telegram checks. alfred-glance or the owner
    may narrow it; it is one line.
- **Filed** estate message `c2f77a4b-48c6-4ee3-b403-51c9bd299588` to
  alfred-glance before the commit, in reply to `db66a2c0`. It tells
  glance to match `kind` together with `severity == "critical"`,
  because an arbiter-stopped row also carries the mark.
  Corrected in `caeb1df7-13a1-4b68-bc9e-0f200018397e`: live at the
  next restart, not after the owner's review.
- **Restarted by the owner at 10:00:16 UTC**, new PID 2069739,
  `/api/health` 200, 53 services loaded from the new file. The
  auto-mode classifier had refused the session's own restart, despite
  the standing permission of 2026-10-21.
  - Holding the restart was rejected: until it ran, a SIGHUP or
    `POST /api/sysadmin/reload` would have installed nothing. The old
    model rejects the `outage_kind` key, and a reload validates the
    whole file first (`sysadmin/reload.py`, rule 1).
  - STATUS.md's Deploy sentence carries the new start; the claims
    check reads every claim `ok`.
- **Read-back driven live**, read-only: `_committed` returned a dict
  for the newest real alert and `None` for a random UUID and for `x`.
  Not witnessed on the wire, which needs Alfred down.
- **Test fix, a second concern.** The game-spans route test fails on
  a fixed date: by arithmetic from 20:00 UTC on 2026-11-13. It now
  freezes the route's clock. Neither push half runs it, which is
  `SNAG-TEST-023`. The suite reads 4,772 collected, and STATUS.md says
  so.
- **Close notes on this repository's filings**, all 2026-11-26:
  - `555efccb` and `109f5867` (estate-manager): logged as their
    Session 516 open row, "decide whether the estate declares the
    cluster's settings". Their recommendation: write the two settings
    and their undo into `cluster-restore.md` now, and declaring them
    under `backup/` goes on their v2 list.
  - `bdca0861` (venture-assistant): the writer is their test suite
    against the live `venture` database. Their `f4612d6`, not yet
    pushed, cuts a run's WAL from 3.65 GB to 679 MB. Recorded under
    Session 465's re-measure task, since Sunday's figures now mix two
    causes.
- **Five commits are ahead of the upstream**, Session 465's docs among
  them, over the pre-push gate's two. They push in three goes.

## Session 465: checkpoints spaced, by the owner's hand

Opened on Session 464's Next action, the owner's WAL lever. Docs only.

- **The lz4 recommendation was withdrawn before the ask.** pgBackRest
  already compresses the archive at `compress-level=3`, about 5:1, so
  lz4 in the WAL would barely shrink it. Checkpoint spacing cuts
  full-page images at source instead.
  - 11,322 checkpoints in 31 days, one every 3.9 minutes.
  - PostgreSQL logged "checkpoints are occurring too frequently" 20
    times since 2026-11-25.
  - `venture` is 1,966 MB against about 86 GB of WAL in one day.
- **The owner chose** `checkpoint_timeout = 30min` and
  `max_wal_size = 16GB`, applied by `ALTER SYSTEM` from the owner's own
  prompt. It reloaded at 08:44:54 UTC, and a fresh connection reads both
  values from `postgresql.auto.conf`. That prompt's `SHOW` printed the
  old values, because a reload is asynchronous.
- **Forks taken.**
  - Rejected: `wal_compression`, for the reason above.
  - Rejected: applying the change through estate-manager. It would have
    waited for their session, and no repository declares
    `postgresql.conf` at all.
  - Rejected: waiting for venture-assistant to name the writer, which
    is still open as estate message `bdca0861`.
  - Rejected: lowering `repo1-retention-full`, the owner's ruling of
    2026-10-03.
- **Filed** estate message `555efccb-7090-444d-9b88-3c26dc85638b` to
  estate-manager: the cluster's settings have no declared owner, and a
  restore from their guide would lose these two. Corrected its time in
  `109f5867-b10e-4ba3-a6d4-c493c9828577`.
- **Logged** alfred-glance's `db66a2c0-1e58-42fc-ac40-ceddd7b9298d` and
  its correction `47410a04-c6e4-44b3-9b8d-f7bae8568ed2` as one task
  under Session 465 (mark the criticals that are phone items 1 and 2),
  and closed both. Item 1 is the Next action. Item 2 waits on Session
  459's own-event task.

## Session 464: estate-manager's live-folder timer declared

Opened on Session 463's Next action. Code in `f4298f1`.

- **Declared `estate-manager-live-timer`**, `kind: timer`, user scope,
  `controllable: false`, the shape of Session 462's dotfiles timer. A
  `SIGHUP` at 08:27:48 UTC added it (53 services); its first check
  read `ok` at 08:30:06.
- **Forks taken.**
  - No `log:` block, unlike the other estate-manager timers. Their
    blocks read Python JSON records; this unit is a shell script, and
    all 21 of its journal records are PRIORITY=6, so a `warning`
    filter would store none of its refusal reasons.
  - Watched the timer, not the service, as estate-manager's message
    asked and as for their scan timer.
- **Differs from dotfiles' timer**: a failed fetch exits 0 until the
  last good fetch is 24 hours old, so an offline afternoon reads `ok`.
  The comment says so.
- **Next action** is the owner's WAL lever from Session 463, because
  it is the one item in tasks.md waiting on the owner.

## Session 463: what fills `/`, named

Opened on Session 462's Next action. Docs only.

- **It is pgBackRest's WAL archive** in `/var/lib/pgbackrest`, inferred
  because that directory is unreadable here: `du` sees 76 GiB less
  than `df`. PostgreSQL wrote about 177 GB of WAL from 2026-11-22 to
  2026-11-26, nearly all of it full-page images. The archive is cut
  back each Sunday at about 02:03 (−37.7 GiB on 2026-11-22), so `/` is
  a sawtooth. The 2026-12-02 crossing was a trough-to-peak line, and it
  was wrong. Next peaks: about 88.4 % before 2026-11-29 and 89 to 90 %
  before 2026-12-06. The 25 GiB Stable Diffusion install of 2026-11-23
  is the one-off step.
- **The writer is attributed, not caught**: `venture` holds 422 M of the
  cluster's lifetime row updates, and only venture-assistant's backend
  connects to it. Filed to them as estate message
  `bdca0861-d677-43b2-ad05-9e5e504ff0dc` (which job makes the updates).
- **Forks taken.**
  - Did not read `pg_stat_user_tables` inside `venture`, which would
    have named the table. The estate's database rule bars it even
    read-only, so I filed the question to the owner of the database
    instead.
  - Did not change the cluster's WAL settings (`wal_compression` off,
    `max_wal_size` 1 GB). They are the owner's choice and
    estate-manager's config. `lz4` compression is recorded in tasks.md
    as a recommendation.
  - Did not bump STATUS.md's `Last Updated`, because only the disk
    paragraph was re-measured.
- **Logged** estate messages `ff20a6c0-cdf0-4976-b97a-ca438a645bde` and
  `ef523070-ffbd-46f3-b2c3-0863794a2b10` (estate-manager's live-folder
  timer, installed 06:58 on 2026-11-26) as one task under Session 463,
  and closed both. The task is the Next action.

## Session 462: dotfiles' live-folder timer declared; hook_wiring re-read

Opened on estate message `d6dab8bf-6734-42e9-8f2b-877709d3b6c6`
(dotfiles: their units exist, and `~/.claude/settings.json` is a regular
file, both 2026-11-26). Code in `279622d`.

- **Declared one entry, the timer.** The service is a oneshot, so
  `kind: timer` reads its `Result` and a failed fast-forward shows.
- **Forks taken.**
  - No `log:` block. The cert timer's block has a reason specific to
    renewal; `venture-manager-backup-timer`, the other 15-minute
    oneshot, has none.
  - Did not start `estate-manager-audit.service`. It is estate-manager's
    unit; the owner was asked to run it.
- **Restarted the daemon** at 06:25:06 to serve the docstring edit,
  under the owner's standing permission of 2026-10-21.
- **Stacked**: the cut-over opened `Estate wiring check and this
  monitor read different settings files` at 06:20, because the estate's
  05:04 audit still names the old symlink target. Recorded as
  `SNAG-CFG-009` and a task under Session 462. The owner re-ran the
  estate's audit at 06:28 and the warning closed at 07:26:06, in the
  same judge run that closed three idle nudges; STATUS.md's Alerts now
  names the 2 open rows.

## Session 461: STATUS.md's Deploy and Alerts, rewritten

Opened on Session 460's Next action. Docs only.

- **The 2026-11-19 08:19:18 start was a boot**, after a 325-package
  system upgrade and a clean `poweroff` at 22:12:05 on 2026-11-18. The
  journal names no person, only a `poweroff` client in the user
  session, so the paragraph names none.
- **Forks taken.**
  - Bumped `Last Updated` to 2026-11-25, which Session 460 declined.
    Every paragraph of the block was re-measured first, and the disk
    paragraph was false, so it was rewritten too.
  - Said the boot did not load `a68e608`. A reload at 16:53 UTC on
    2026-11-17 had already installed its `services.yaml` entries.
  - Left the pacman `python-*` upgrades out. The daemon runs from its
    own venv.
- **Stacked**: `/` is at 87.0 % and rising about 0.44 points a day. It
  is recorded in tasks.md under Session 461 and made the Next action.
- **Logged** estate message `0ff03232-df47-4577-9cd3-38d6f39477e6`
  (dotfiles' live folder) as two waiting tasks under Session 461 and
  closed it.

## Session 460: STATUS.md's timed prediction, re-measured and replaced

Opened on Session 459's Next action. Docs only.

- **The prediction held.** The 3 shared log instants of 2026-10-30
  cleared at retention. The test still has live specimens, because 9
  new ones were ingested on four days up to 2026-11-20. The sentence
  now names those 9 and the 2026-12-20 03:00 run that clears the
  newest.
- **Forks taken.**
  - Replaced the prediction rather than deleting it.
    `test_the_block_states_at_least_one_prediction` requires the block
    to carry one, so deleting it would red the suite.
  - Left STATUS.md's `Last Updated` at 2026-11-16. Its Deploy sentence
    is still stale, and a fresh date over it would read as checked.
- **Stacked**: the `daemon_start` and `open_titles` claims fail in the
  same block. Recorded in tasks.md under Session 460 and made the Next
  action.

## Session 459: the owner's working-week rulings, logged; self-restart on a branch

Opened on estate message `de46c7a3-b008-4425-b3ef-4de64615945b`
(estate-manager, the owner's rulings of 2026-11-25 on his working-weeks
review). The freeze exception he named that day covers it. Each ruling
is a task under Session 459 in `docs/roadmap/tasks.md`.

- **Self-restart is built on branch `self-restart-three` (`27c3cc9`,
  `5e3dbee`), unmerged.** The branch sits in its own worktree. Service
  control always waits for the owner's merge, and `sysadmin.service`
  runs this checkout, so main carries only docs. Five services set
  `auto_restart`. The GPU lease is read before a restart, which closes
  `SNAG-AGENT-013`. One restart per outage. 1,048 of the diff's lines
  are the retired check and its tests.
- **Forks taken.**
  - The auto-restart is queued with `--no-block`, so success means
    queued, not started. The tray's service-control route keeps the
    blocking call, so its result stays real. Rejected: a timeout on
    the blocking call, which would report a slow GPU start as a
    failure.
  - `llama-server` was first left off because the blocking restart
    could stall every check. The owner then ruled it in, and the
    non-blocking restart is what made that safe.
  - `sysadmin-service` is off. A monitor cannot restart itself, and
    `Restart=always` already does.
  - Once per outage rather than every third poll, because a broken
    unit would otherwise restart for ever.
  - Rejected: putting the flags on main and trusting a later review.
    The flags would go live at the next daemon restart.
- **Suite on the branch**: the six SNAG-AGENT-013 tests went with the
  check. Ten failures come from running in the worktree (its path, no
  `.venv`), and `test_game_spans_db` fails on main too. ruff and mypy
  are clean.
- **Not built, and why**:
  - Phone item 2 needs a fresh critical event.
  - Items 4 to 6 wait on other work.
  - The live folder follows dotfiles, estate-manager and Alfred.
  - The pull-request trial and the path list are estate-manager's rows.
- **Stacked**: STATUS.md's timed prediction, overdue since 2026-11-22.
  Recorded in tasks.md and made the Next action. The scheduled line
  for it moved there.

## Session 458: the publisher's grant narrows to estate/alerts/#, read and closed

Opened on estate message `00351947-1c64-48eb-b051-bc74c95e75d6`
(estate-manager, their bug review M15): `mqtt/dynsec.yaml` gives
`sysadmin-publisher` its own role, `sysadmin-alerts-publisher`, with
`publishClientSend` on `estate/alerts/#` only, in place of the shared
`estate-publisher` on `estate/#`. On their branch `m14-m15-review`
(`0b6cc2b`, read there); the broker changes when the owner reprovisions.

- **Two docstrings corrected** (`a71dd6c`): `MqttNotificationsConfig`
  in `sysadmin/core/config.py` and `sysadmin/monitor/mqtt_alerts.py`'s
  module docstring named the old grant. Both now name the new role, say
  the broker holds `estate/#` until the reprovision, and state the
  consequence: a `topic` outside `estate/alerts/` is dropped with a zero
  exit.
- **Behaviour unchanged**: `config.yaml` publishes on
  `estate/alerts/raised`, inside the new grant, and `mqtt_alerts.py` is
  the only `estate.bus` publish here. No validator added: the freeze
  admits fixes, and no configured topic is outside the subtree.
- **Left as history**: ADR-0003's Context (verified live 2026-08-11
  under `estate-publisher`) and `tasks.md`'s closed game-spans item.
- Acted on as the session's concern, so no tasks.md item; message
  closed.

## Session 457: audit ages pass over errored runs, read and closed

Opened on estate message `97e08455-ca3a-4e53-9712-de25622475d8`
(estate-manager, their bug review M4): `GET :8400/api/audit/findings`
will stop ending a finding's streak at a run whose check errored, so
`first_seen_at`, `standing_days` and `runs_observed` grow across such
runs. Keys unchanged; the change sits on their branch until merged and
the API restarted. No reply asked.

- **Nothing here changes.** `judgements.py` carries the three fields
  through as evidence and prints `standing_days` only in an alert's
  **message**, via `_with_standing`; alert identity is the title, which
  holds no age, so a larger figure rewrites a sentence and opens or
  closes nothing. No code or test here assumes `runs_observed` counts
  every run since `first_seen_at`.
- **Their measured live effect touches nothing judged here**: the
  `vram` finding on venture-embed is not in `JUDGED_AUDIT_CHECKS`
  (`ports` and `wiring` alone). Before their restart, at 2026-11-18,
  it read first seen 2026-10-26, 23.1 days, 30 runs; the one judged
  finding, `ports` on port 3400, read 0.1 days, 1 run.
- **Moved** Sessions 448 to 440 to `HANDOFF-archive.md`, unedited:
  this file was 520 lines, over estate rule 2's 500.
- Acted on as the session's concern, so no tasks.md item; message
  closed.

## Session 456: the estate's nudges skip *(For: none)* lines, read and closed

Opened on estate message `ba557f94-8c9c-4169-a8f8-e953204de816`
(estate-manager): `eligible_candidates`, behind both
`GET /api/projects/next` and the idle nudges on
`GET /api/projects/attention`, now skips an active row whose handoff
Next action is marked *(For: none)*, counted under a new skipped key,
`marked_for_none`. No action was asked.

- **Nothing here changes.** `judge_attention` in
  `sysadmin/estate/judgements.py` reads only `payload["nudges"]` (and
  `health`, `refused_manifests`); no code or test here reads a skipped
  key, and nothing here requests `/api/projects/next`.
- **Measured before their restart**: `/attention` publishes 4 nudges
  (InvestingAssistant, portfolio, kaggle, powerbi-ae) and its keys are
  `generated_at`, `health`, `nudges`, `refused_manifests`; the board's
  23 active rows read 11 `none`, 8 `owner`, 4 `session`, as filed.
- **This repository's own line is `none`**, so it leaves `/next`'s
  candidates; that is the freeze's intent, not a loss.
- Acted on as the session's concern, so no tasks.md item; message
  closed.

## Session 455: the estate's HTTPS units, declared

Worked tasks.md's Session 454 item, logged from estate message
`0e20eec6` with their commit corrected to `71d07c5`.

- **Two entries in `services.yaml`** (`a68e608`): `estate-manager-https`,
  `kind: http` on `http://127.0.0.1:8602/api/health` with `port: 8602`,
  and `estate-manager-cert-timer`, `kind: timer`, whose check reads the
  oneshot's `Result`, so a failed renewal is critical.
- **Chose 127.0.0.1 over localhost**, the file's usual spelling: Caddy
  binds 8602 on IPv4 loopback alone. **Left 443 undeclared**: an entry
  carries one port, and 8602 is the one the check reads.
- **No `format: json` on either log block.** Measured in the journals:
  Caddy's 81 and lego's 33 lines are all at PRIORITY=6, Caddy's 16 own
  "warn" documents included, so the `warning` filter stores only
  systemd's plain-text lines.
- **Driven live.** Reloaded at 16:53:12 with the tray's token
  (`services_added` names both); both rows read `ok` at 16:53:23. The
  sweep at 16:53:24 counts 43 monitored, 0 unmonitored, 0 port findings.
  `restart_unbounded` went 16 to 17: the HTTPS unit has
  `Restart=on-failure` with no start limit, like the 16 before it.
- **The cert timer has not fired yet.** Its `ok` reads the manual run of
  13:32:35 (`last_run_recorded: false`); the first timer-driven run is
  2026-11-18 03:18:59, and the check alerts if it fails.
- **Reading the served expiry was not built**: new code under the
  freeze, so it is a v2 line in `ideas.md`.
