# Handoff — 2026-11-25 (Session 459)

## Next action

Re-measure STATUS.md's timed prediction, overdue since 2026-11-22, then rewrite or replace its sentence. *(For: session)*

## Scheduled action

- 2027-02-01: the owner reads the v2 list in `ideas.md`; the
  manifest's `freeze.until` carries the same date.

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

## What Session 454 handed on

Declare estate-manager-https.service and estate-manager-cert.timer with its oneshot in services.yaml (tasks.md, Session 454). *(For: session)*

## Session 454: a corrected commit id, and the units it names logged

Opened on estate message `4d87ff6b-aab7-42e7-8733-fb04925a7d89`
(estate-manager): the HTTPS origin's code is their commit `71d07c5`,
not `6b5bc29` as message `0e20eec6-5cb8-448e-80e0-7a15873adfcd` said.

- **Checked in estate-manager's checkout.** `71d07c5` is *"the estate
  serves HTTPS on the home network"* and adds the three unit files;
  `6b5bc29` is still an object in their store but on no branch.
- **Nothing here cited either hash** (`git grep`, the archive included),
  so no correction was owed in this repository.
- **Logged `0e20eec6`** as tasks.md's Session 454 item, with `71d07c5`
  written in so the wrong hash in that message's detail is not copied
  into `services.yaml`. Both messages closed. Not worked: the
  declaration is the next session's concern.
- **The push suite went red on the estate's new row.**
  `test_our_parser_and_the_estates_agree_on_the_live_document` pins the
  live port table's rows outside the audited ranges, and 443 joined
  22000 there today. Both are a daemon on its own port, so the pin
  widened to `[443, 22000]`; the ranges stay matched to the estate's.
- **Moved** Sessions 438 and 439 to `HANDOFF-archive.md`, unedited:
  this file was 508 lines, over estate rule 2's 500.

## What Session 453 handed on

Nothing is startable under the freeze until a bug or an incident in daily use calls for work. *(For: none)*

## Session 453: the queue library's cancel fix, loaded by a restart

Opened on estate message `5d5c92ce-39f1-4ddf-8cd4-16c663e7dab6`:
`estate.queue.acquire` now releases a still-waiting lease when its
caller is cancelled (their `6d274a5`).

- **Our side needs no code.** `acquire_review_lease` catches only the
  three queue exceptions, so a cancel still propagates after the
  library's release. The lease tests pass (39).
- **Restarted** at 19:15:37 by SIGTERM, the owner's standing ruling of
  2026-10-21, so the daemon runs the fix now rather than at its next
  start. Health answers 200. Message closed.
- **Close note on `d340c4ff`** (estate-manager, 15:29): logged as their
  Session 475's open task, *bring the provisioner back when the broker
  comes back*, with our two shapes as a recommendation, and the one-off
  rerun put to the owner. The unit was rerun at 15:37:30 and found
  *"schema already asserted; no changes"*, which answers Session 452's
  unmeasured question: the dynsec store matched the yaml. The critical
  row closed at 15:38, and STATUS.md now names 5 rows.

## What Session 452 handed on

Nothing is startable under the freeze until a bug or an incident in daily use calls for work. *(For: none)*

## Session 452: why estate-broker-provision failed, filed at the estate

Opened on Session 451's Next action.

- **Cause, from the journal:** on the 2026-11-14 boot `eno1` had no link
  for 27.5 minutes (15:06:05 to 15:33:38; 4 s on the three boots
  before). mosquitto's gate gave up at 15:08:26. The provisioner started
  at 15:06:20, because `After=` only orders it, waited its 150 s and
  exited 1 at 15:08:50. Why the link was late is not measured: the
  kernel logged nothing about `eno1` in between.
- **What was new:** the estate already fixed the broker half (ADR-0260,
  on Alfred's `5ee683ac`). Its dispatcher restarts mosquitto only, and
  neither the ADR nor their Session 471 mentions the provisioner, still
  `failed` 30 hours after the broker came up.
- **Filed** as `d340c4ff-0047-4b93-88da-92ec57ff420a`, with two shapes
  for a fix as a recommendation: the dispatcher also starts the
  provisioner, or the provisioner gains `WantedBy=mosquitto.service`.
  The one-off rerun needs `sudo` and was not run here.
- **Not measured:** whether the dynsec store matches `mqtt/dynsec.yaml`.
  Every client seen since 21:20 authenticated, except two
  `alfred-backend-health` refusals at 14:57 today, which are not linked
  to this and were left out of the filing's cause.
- **STATUS.md** names all 6 open rows; both Alerts checks read `ok`.
  When the estate reruns the unit the row closes and the count drifts
  to 5, which the preflight reports.

## What Session 451 handed on

Measure why estate-broker-provision failed at the 2026-11-14 boot, file it at estate-manager, and name its row in STATUS.md's Alerts paragraph. *(For: session)*

## Session 451: home-manager's frontend entry, logged and checked

Opened on estate message `03b92b7c-be7d-419a-a560-4b96348de555`, in
which home-manager said it had added `home-manager-frontend` to
`services.yaml` (`18f9309`, their commit).

- **Done:** checked that the entry is live. The service has been polled
  `ok` since the 11:33:02 restart. The services tests pass, and the unit
  sweep raises only the `advice` nine other units carry. STATUS.md's
  Deploy sentence now names the restart, and the message is closed.
- **Attribution, as measured:** the journal shows a systemd stop job at
  11:32:59, not a kill. home-manager's transcript `2019669c` asked the
  owner for `sudo systemctl restart sysadmin.service`, so the sentence
  says the restart was asked for and does not say who ran it.
- **Second concern, recorded and not worked:** two alert rows the
  Alerts paragraph does not name, among them `estate-broker-provision
  critical`, open since the 2026-11-14 boot. They are the task at the
  top of `tasks.md` and the Next action above. The two Alerts checks in
  `check-ops-claims.sh` stay `no` until then.

## What Session 450 handed on

Nothing is startable under the freeze until a bug or an incident in daily use calls for work. *(For: none)*

## Session 450: the memory index under 17.1 KB, by its titles

Opened on Session 449's Next action. The memory directory is outside
the repository, so only this block and `tasks.md` are committed.

- **Done:** `MEMORY.md` went from 20,393 bytes to 16,784, still 131
  lines. Every one of its 157 links is kept, in the same order, and
  each resolves.
- **How:** the titles were 6.1 KB of the 20.4 and spelt out the same
  words as their filenames, so each became a two-to-three-word tag.
  The header now states the 17,100-byte budget and puts "shorten a
  title" first among the levers.
- **Rejected:** dropping about 20 memories, Session 449's estimate.
  Eleven were checked against the box by their specific claim, and
  none was falsified whole: agent_runs' held-branch keys, the
  arbiter's FIFO, the first-run delay, the pre-commit five-file rule,
  the `estate_service` editable, the daemon's system unit, the deploy
  check's mtimes, ruff's config, the pre-push gates, and the two
  below. The other 146 had their cited files checked for existence
  only. A dropped line would hide a true memory with nothing left
  pointing at it.
- **Headroom:** 17,100 − 16,784 leaves about 300 bytes, two or three
  new lines, and the title lever is spent. The next compaction has to
  fold families or drop lines.
- **Corrected in two memory files:** `stack-facts-not-in-claude-md`
  gave the wheel `packages` as `sysadmin` alone (now `sysadmin` and
  `sysadmin_tray`). `enumerate-the-estate-at-depth-2` counted 27
  repositories in six tiers; there are 39 in nine.
- **Backup:** the whole memory directory as it was is at
  `/tmp/claude-1000/-home-gaddi-projects-sysadmin-assistant/ec6b7453-89d2-4be4-8470-ff2fc9f05b7a/scratchpad/membak/`
  until a reboot clears it.
- **Not this session's:** `18f9309`, home-manager's own
  `services.yaml` declaration, landed from that session meanwhile.

## What Session 449 handed on

Compact the memory index `MEMORY.md` from 20.4 KB to under 17.1 KB, checking each dropped memory against the box first. *(For: session)*

## Session 449: Easy Effects, on the owner's request

Desktop configuration outside this repository; nothing here changed.

- **Fixed:** Easy Effects' autostart. The Flatpak segfaulted every
  time; Arch's 8.3.2 now runs with `--service-mode -w`, and the owner
  installed the plugin packs it needs (`lsp-plugins-lv2`, `calf`).
- **Rejected:** a WirePlumber `stream.rules` file to route Spotify. In
  WirePlumber 0.5 those rules only reach its bookkeeping copy, and a
  target set there stops the remembered one being restored. Spotify is
  routed by restore-target instead.
- **Raised, not worked:** the memory index at 20.4 KB against the
  hook's 17.1 KB target, now the Next action and a `tasks.md` item.
