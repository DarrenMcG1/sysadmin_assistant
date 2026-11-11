# Bug review, 2026-11-11

Reviewed at commit `751d1fc` on `main`. Nothing in the repository was
changed by this review; the only writes are this file and
`v2-proposals.md` beside it.

## 1. Overall health

The monitoring core is in good condition: the full suite is green
(4,777 passed, 2 skipped, 175 s), models, migrations and the live schema
agree, every one of the 13 mutating routes carries the auth dependency,
and the last 30 days hold no failed run of the service-health or log
agents. The defects cluster at the edges that are rarely exercised: the
file-cleaning actions, the tray's buttons and colours, and failure paths
(a reboot, a rolled-back run, a hung subprocess) that the box has not
met often enough to expose. Several of those are latent today and are
marked so; four are live and worth fixing under the freeze's bug-fix
rule.

**Counts:** critical 0, high 4, medium 19, low 20.

**How this was done.** Six reviewers read one slice each and reported
findings with their evidence; I re-ran the evidence for H1 and H3 myself
and read the cited code for H4, M5, M9 and M12. The rest are reported as
the slice reviewer verified them, and each entry says how. "Latent"
means the code is wrong but no input on this box reaches it today.
"Recorded" names the entry in `docs/roadmap/snag_list.md` (the
repository's register of known defects) where one exists.

## 2. Findings

### High

**H1. `POST /api/files/clean/stale-caches` deletes directories inside a
running PostgreSQL data directory**

- **Where:** `sysadmin/files/router.py:447-504`; the empty-directory
  loop is lines 489-497.
- **What is wrong:** the route shares none of the safety model of
  `sysadmin/files/actions.py`. It acts on the stored audit instead of
  the live filesystem, has no root confinement and no projects-root
  exclusion, ignores the `actions.enabled` switch, deletes with
  `rmtree`/`rmdir` instead of the trash, and its dry run lists no
  paths. The README's four safety claims for `/api/files/*` actions are
  false for this route.
- **In practice:** the tray's "Clean stale caches" button
  (`sysadmin_tray/dashboard/files_tab.py:333-355`) calls it with
  `confirm=true` after a dialog that shows counts only. It removes the
  first 50 stored empty directories. In the two latest audits, positions
  14 to 27 are `pg_tblspc`, `pg_twophase`, `pg_notify`, `pg_replslot`,
  `pg_wal/archive_status` and nine more under
  `~/projects/web/cv/private/funnel/pgdata`, which a live `postgres -D`
  process is serving. PostgreSQL needs those directories to checkpoint
  and to start. Positions 2 and 3 are `~/Templates` and `~/Public`.
- **Verified:** read-only query of the latest two `filesystem_audits`
  rows; `pgrep -af funnel/pgdata` shows the server; the directories are
  owned by the daemon's user and the unit sets `ProtectHome=no`. Not
  executed. Rated high and not critical because the directories are
  empty, so recreating them recovers the cluster.
- **Recorded:** no.
- **Fix:** delete the route, the tray button and the "Remove N empty
  directories" recommendation (`files/recommendations.py:340-357`), or
  rebuild it on `actions.py` with a live walk and the projects-root
  exclusion.

**H2. The duplicate fingerprint calls different files identical, and
`/clean/duplicates` trashes on it**

- **Where:** `sysadmin/files/agent.py:70-84` (`file_hash` is size plus
  MD5 of the first 1 MB); used by `sysadmin/files/actions.py:552-586`
  with no full-content check.
- **In practice:** two same-size files that share their first megabyte
  form a "duplicate group" and all but one go to the trash. Recoverable
  until the trash is emptied.
- **Verified:** a temp tree with two files sharing a 1 MiB head and
  different tails was planned and executed as a duplicate. On live data,
  a full SHA-256 of 49 stored groups found 5 with different content
  (dated `pa-companion-*.apk` builds, two `libonnxruntime.so` groups).
  Those sit under `~/projects`, which the action excludes, so nothing
  has been lost. At least 14 of the 49 are hardlink pairs, which free
  nothing when removed, so the "frees at least 7.9 GB" figure is
  inflated.
- **Recorded:** no.
- **Fix:** confirm each group with a full hash before planning, and
  drop members that share an inode with the keeper.

**H3. Kernel lines from the end of the previous boot are never
ingested**

- **Where:** `sysadmin/monitor/journal.py:405-406` (`-k`), reached from
  `log_aggregator.py:1141-1162`.
- **What is wrong:** `journalctl -k` implies the current boot. After a
  reboot the read is `journalctl -k --since @floor`, which cannot see
  what the kernel logged between the last poll and the crash.
- **In practice:** those are the lines of the fault that caused the
  reboot. On 2026-10-31 the box rebooted at 14:42:53; three `err` lines
  (`MES failed to respond`, `failed to unmap legacy queue`, `failed to
  halt cp gfx`) and one `crit` (`watchdog did not stop!`) between
  14:42:12 and 14:42:25 are in the journal and not in `log_entries`, so
  no alert was raised.
- **Verified (by me):** `journalctl -k` over that window returns 0
  lines; `journalctl _TRANSPORT=kernel -p 3` returns the four; the
  table holds 0 kernel rows for the window.
- **Recorded:** not for the aggregator. The same trap is recorded for
  the GPU-context sweep, which already reads with `_TRANSPORT=kernel`.
- **Fix:** read the kernel source with `_TRANSPORT=kernel` so `--since`
  and the cursor cross boots.

**H4. The toast buttons "Restart" and "Snooze 1h" never fire**

- **Where:** `sysadmin_tray/notifications.py:1304` and `:1319`.
- **What is wrong:** the slots are declared `@pyqtSlot(int, str)` and
  `@pyqtSlot(int, int)`, but the freedesktop signals carry unsigned ids
  (`ActionInvoked(us)`, `NotificationClosed(uu)`). Qt D-Bus matches on
  signature, so the slots are never called; `connect()` still returns
  true and nothing is logged.
- **In practice:** every toast offers two buttons that do nothing, and
  snoozing is unreachable from the desktop.
- **Verified:** a probe on a private, made-up D-Bus interface under the
  repository's PyQt 6.10.2 showed an `int` slot does not receive a
  `uint` signal while a `"uint"` slot does. Not driven against Plasma's
  notification daemon, because that needs a real notification. The
  tests call the method directly, so they cannot see it.
- **Recorded:** no.
- **Fix:** declare the slots `@pyqtSlot("uint", str)` and
  `@pyqtSlot("uint", "uint")`, and add a test that delivers the signal
  over a private bus.

### Medium

**M1. An idle nudge the estate escalates to `warning` stays `info` for
ever**

- **Where:** `sysadmin/estate/agent.py:216-224` with
  `sysadmin/core/agent.py:628-632` (`refresh_alert`).
- **What is wrong:** severity is taken from the estate only when the row
  is first raised. A later, louder judgement with the same title goes
  down the "held" branch, where `refresh_alert` refuses an upward move
  by design, and this agent has no resolve-and-re-raise step.
- **In practice:** `info` is below the tray's `notify_min_severity:
  warning`, so the nudge is never spoken. Rows resolved still at `info`
  include ImbaBots at 45 days idle (threshold 7) and Athenaeum at 46
  (threshold 21).
- **Verified:** read-only query of `alerts` for `agent='estate_judge'`;
  a snippet showing `refresh_alert(..., severity='warning')` leaves the
  row at `info`.
- **Recorded:** no.
- **Fix:** when the judged severity is louder than the standing row's,
  resolve the row and raise a new one.

**M2. The incident fold misses most fragments of a GPU reset that
starts with a page-fault burst**

- **Where:** `sysadmin/monitor/log_aggregator.py:437`
  (`ALERT_INCIDENT_WINDOW_SECONDS = 5.9`) and `:559-707`.
- **In practice:** the 2026-10-31 reset spanned 7.02 s, so one incident
  raised 16 `warning` rows plus the `critical` one instead of one row
  naming its members.
- **Verified:** the 17 `alerts` rows at 14:41:10; a pure call of
  `fold_declared_incidents` with those offsets raised 9 of 12.
- **Recorded:** no; it is the symptom of the closed entry
  `SNAG-LOG-015` returning.
- **Fix:** fold around the declared line, before and after it, instead
  of anchoring on the earliest fault.

**M3. The journal cursor advances before the ingest transaction commits
(latent)**

- **Where:** `sysadmin/monitor/log_aggregator.py:1163-1164` and `:1494`.
- **What is wrong:** a run that rolls back drops its rows, but the
  in-memory cursor has already moved past them, so they are lost until a
  restart. The base class has a hook for this (`_work_committed`); the
  service-health agent uses it and the log agent does not.
- **Verified:** by trace; `grep _work_committed` shows no override in
  `log_aggregator.py`. No failed log run in 30 days, so not observed.
- **Recorded:** no.
- **Fix:** stage cursors per run and copy them in `_work_committed`.

**M4. A failing `journalctl` is read as "no entries"**

- **Where:** `sysadmin/monitor/journal.py:537`.
- **What is wrong:** exit code 1 is accepted as "empty", but on this
  systemd an empty read exits 0 and 1 is the generic failure.
- **In practice:** a rejected cursor returns nothing on every poll with
  no log line; `journal_horizon` turns a failed read into "zero core
  dumps".
- **Verified:** `journalctl -k --after-cursor garbage` exits 1;
  `read_journal('kernel', after_cursor='garbage-cursor')` returned no
  entries and logged nothing.
- **Recorded:** no.
- **Fix:** treat non-zero exit with stderr as a failure and return
  `None`.

**M5. The tray icon reads service status `critical` and `warning` as
healthy**

- **Where:** `sysadmin_tray/models.py:114-120`.
- **In practice:** timers are stored as `critical` (582 rows in 14
  days). Their icon colour rests on the alert row alone.
- **Verified:** `compute_icon_state` returns HEALTHY for both; I read
  the two tuples.
- **Recorded:** same class as the closed `SNAG-TRAY-012`, which fixed
  the dot colours and not this map.
- **Fix:** derive the icon rung from the same status vocabulary the
  dots use.

**M6. The Services tab dot is overwritten by systemd state**

- **Where:** `sysadmin_tray/dashboard/services_tab.py:167-170`.
- **In practice:** `llama-server` is `degraded` and shows green; a unit
  that is `skipped` and inactive by design shows red. Lines 151-152
  offer Start, not Stop, for a degraded running service.
- **Verified:** live GETs of `/status` and `/details` for both.
- **Recorded:** no.
- **Fix:** leave the dot to the health status; show systemd state as
  text.

**M7. Advice for a failed timer hard-codes `--user`**

- **Where:** `sysadmin/monitor/service_recommendations.py`,
  `_timer_failed_row` (1077) and `_timer_stale_row` (1125).
- **In practice:** `pgbackrest-backup-timer`, the box's only database
  backup, is a system unit. If it fails, the advice and the weekly
  review hand over a command that prints "No entries".
- **Verified:** snippet output and running the command.
- **Recorded:** no.
- **Fix:** carry the scope on `TimerSeries`.

**M8. A non-UTF-8 `settings.json` crashes the whole estate-judge run**

- **Where:** `sysadmin/estate/hook_wiring.py:191-193`.
- **What is wrong:** only `OSError` is caught; `UnicodeDecodeError` is a
  `ValueError`. A broken file is what this surface exists to announce,
  and here it silences the other five surfaces too.
- **Verified:** `read_settings` on a temp file with a `\xe9` byte
  raised.
- **Recorded:** no.
- **Fix:** catch it beside `JSONDecodeError`.

**M9. Four audit counts are caps presented as totals**

- **Where:** `sysadmin/files/agent.py:292,298-301,348` truncate the
  lists before `len()` is taken.
- **In practice:** `/api/files/status` has read `duplicate_groups: 200,
  empty_dirs: 200, stale_files: 500, similar_folders: 100` for at least
  three audits, so week-on-week deltas always read "unchanged".
- **Verified:** live GET and the three latest rows; my own query showed
  the stored `empty_dirs` list at its cap on each.
- **Recorded:** no.
- **Fix:** count before truncating.

**M10. The scan can never find a cache, so "stale caches" is dead**

- **Where:** `sysadmin/files/agent.py:170-173` prunes `skip_dirs` and
  dot-directories before line 187 tests for them.
- **Verified:** across every stored audit the types are only `build`,
  `venv`, `target`, `dist`; live `stale_caches` is 0. The tests that
  cover caches build a config that does not skip them.
- **Recorded:** no.
- **Fix:** remove the cache concept with H1, or test before pruning.

**M11. `/api/files/organise` flattens files from anywhere under the
home directory (design hazard)**

- **Where:** `sysadmin/files/actions.py:457-518`.
- **In practice:** `~/Music/Album/cover.jpg` becomes
  `~/Pictures/cover.jpg`; a game's `LICENSE.txt` moves to
  `~/Documents`. Confined, non-overwriting and dry-run by default, but
  it discards the source structure, 200 files per confirmed call.
- **Verified:** on a temp tree.
- **Recorded:** no; `docs/design/files.md` does not say it is intended.
- **Fix:** organise only files loose in named source directories.

**M12. A stalled agent is declared healthy once its last run ages out**

- **Where:** `sysadmin/monitor/self_monitor.py:244-258`;
  `sysadmin/core/retention.py:78-92`.
- **What is wrong:** an agent with no `agent_runs` rows is "not
  stalled". Rows are purged at 30 days, so an agent stalled for longer
  flips to healthy and its critical row resolves.
- **Verified:** `summarise_agent(..., [], ...)` returns `stalled False`;
  `agent_runs` retention is 30 and it is not in `KEEP_LATEST_PER`.
- **Recorded:** no.
- **Fix:** keep the newest run per agent through the purge.

**M13. A second auto-restart collides with the open-alert unique index
(latent)**

- **Where:** `sysadmin/monitor/agent.py:1710-1726` against migration
  019's `uq_alerts_open_agent_title`.
- **What is wrong:** the "auto-restarted" row is raised with
  `dedup=False`; the index forbids a second open row with that title.
  The restart also runs inside a savepoint with no timeout, under a
  60 s idle-in-transaction limit.
- **Verified:** index definition and call path. No service declares
  `auto_restart`, so never hit. A mock-based test pins the behaviour the
  database refuses.
- **Recorded:** no.
- **Fix:** resolve the previous row first, and move the restart out of
  the transaction.

**M14. A failed collation read aborts the run it claims to spare
(latent)**

- **Where:** `sysadmin/monitor/agent.py:2522-2531`.
- **What is wrong:** the error is caught without a savepoint, so the
  transaction is aborted and every later statement fails.
- **Verified:** the PostgreSQL behaviour in `psql`; the function exists
  on this server, so the path is not hit.
- **Recorded:** no.
- **Fix:** wrap the read in `begin_nested()`, as the GPU read does.

**M15. `systemctl` and `rocm-smi` calls have no timeout (unconfirmed as
an occurrence)**

- **Where:** `sysadmin/monitor/systemd.py:97-107`;
  `sysadmin/monitor/gpu.py`, `_from_rocm_smi`.
- **What is wrong:** a hung child holds the agent's transaction and,
  with one instance allowed, stops the agent that detects stalls.
- **Verified:** by reading only. Longest run in 30 days is 26.7 s.
- **Fix:** `wait_for` with a kill on timeout.

**M16. A non-Steam shortcut would fail every game-detector poll (partly
unconfirmed)**

- **Where:** `sysadmin/games/models.py:21` (`appid` is `Integer`);
  `sysadmin/games/detect.py:36,77`.
- **What is wrong:** Steam gives shortcuts ids above 2^31. The owner's
  `shortcuts.vdf` holds two (2707234149, 2509677542).
- **Verified:** column type; `select 2707234149::int` errors.
  **Unconfirmed:** that the launcher's command line carries that id;
  neither shortcut has been launched since the detector started.
- **Fix:** make the column `BIGINT`, or ignore ids at or above 2^31.

**M17. The daemon sits at its memory ceiling with part of its heap in
swap**

- **Where:** `systemd/sysadmin.service` (`MemoryMax=512M`).
- **Verified:** cgroup files after 7 days up: `memory.current` 490 MB,
  swap 217 MB, anonymous 296 MB, 365,872 `max` events, no OOM kill.
- **Recorded:** `SNAG-SYSD-008`, ranked low on a measurement of 155 MB
  anonymous that no longer holds. Whether this is a leak is unconfirmed.
- **Fix:** re-measure and re-rank the entry; free the scan's hash
  tables after each audit.

**M18. `setup-systemd.sh` does not install the failure handler its unit
names**

- **Where:** `scripts/setup-systemd.sh:28,40` against
  `systemd/sysadmin.service:50` (`OnFailure=sysadmin-failed.service`).
  `scripts/install.sh:14` also installs only the `dev` extra while the
  tray unit needs PyQt6.
- **In practice:** on a fresh install a terminal restart loop is
  announced by nothing. This box has all four units, installed by hand.
- **Verified:** by reading the scripts.
- **Recorded:** no.
- **Fix:** install all four units and use `uv sync --all-extras`.

**M19. Interval settings accept zero and negative values; a negative
one hangs the scheduler (latent)**

- **Where:** `sysadmin/core/config.py:296,367,467,544,647,1114`, plain
  `int` fields consumed at `sysadmin/core/scheduler.py:98`.
- **In practice:** `scan_interval_hours: 0`, written to mean "off",
  becomes a one-second interval. A negative value validates, reports no
  failed job, and then hangs `get_jobs()`, at boot before the unit is
  ready, or on a reload while holding the reload lock.
- **Verified:** a scratch script on a real `Scheduler()` under
  `timeout 15`: 0 gave `interval[0:00:01]`; -5 hung. The reload case is
  inferred from the same hang. No such value is in `config.yaml`.
- **Recorded:** no.
- **Fix:** `Field(ge=1)` on the interval leaves.

### Low

- **L18.** `sysadmin/core/event_bus.py:63`: the error handler reads
  `callback.__name__`, which a `functools.partial` lacks, and the SSE
  broadcaster subscribes one (`monitor/sse.py:100`). If it raised, later
  subscribers would be skipped silently. Reproduced with a snippet;
  latent. Fix: `getattr(callback, "__name__", repr(callback))`.
- **L19.** `sysadmin/core/agent.py:443-458`: if recording a run's
  outcome fails after its work committed, the buffered `alert.raised`
  events are dropped, so the backend notifier and MQTT never hear of a
  committed alert. By reading only. The stuck `running` row is recorded
  under `SNAG-LOG-005`; the dropped events are not.
- **L20.** `sysadmin/main.py:174`: the SIGHUP reload is a bare
  `asyncio.create_task`, unreferenced and unsupervised, so an exception
  in it surfaces only as asyncio's generic warning. By reading only.
- **L1.** `scripts/lint_check.sh:25-74`: `((ERRORS++))` under `set -e`
  exits at the first finding, so the summary and the "warnings only"
  exit are unreachable. Reproduced on a copy. Latent: no file trips it.
  Fix: `ERRORS=$((ERRORS+1))`.
- **L2.** `alembic/versions/001_initial_schema.py:254`: `downgrade
  base` drops the schema that holds Alembic's own version table, so it
  can never complete. Shown from `alembic downgrade 001:base --sql`;
  no test runs a downgrade. Fix: delete the `DROP SCHEMA` line.
- **L3.** `log_entries` is 1,881 MB of heap for 251 MB of rows, and the
  nightly purge filters on `ingested_at`, which has no index. Partly
  noted in `SNAG-SYSD-008`. Fix: a one-off `VACUUM FULL` in a downtime
  window.
- **L4.** `docs/guides/api_auth.md`: says the token goes in
  `config.yaml` (it is a systemd credential), names a route that is not
  served, and omits 7 of the 13 protected routes.
- **L5.** `sysadmin/monitor/log_actions.py:542`: the `known_noise`
  snippet uses Python `repr`, which is not YAML quoting. 5 of 198 live
  signatures produce a block that fails to parse. Fix: `json.dumps`.
- **L6.** `/api/logs/trends` and `/actions` accept `days` up to 30
  against 30 days of retention; at `days=30`, 189 of 196 signatures
  read "new". Fix: clamp to half the retention.
- **L7.** A negative `limit` returns HTTP 500 on `/api/logs/recent`,
  `/errors`, `/{source}`, `/api/sysadmin/alerts` and `/status/{x}`; a
  non-UUID alert id on the ack route is a 500, not a 404. Reproduced
  with GETs. Fix: `ge=1` and a `uuid.UUID` path type.
- **L8.** `sysadmin/monitor/journal.py:529-532`: a timed-out
  `journalctl` is never killed. By reading only.
- **L9.** `sysadmin/monitor/routers/sysadmin.py:224-239,278-281`:
  `float(x) if x else None` serves a genuine zero as `null` (9 of the
  history's points live). Fix: test `is not None`.
- **L10.** `resource_snapshots.load_avg_*` is `Numeric(5,2)`; a load of
  1000 would fail the run. Unconfirmed, never approached (max 77.6).
- **L11.** `sysadmin/files/agent.py:187-199`: nested stale directories
  are counted twice, about 2.5 GB of the 41.6 GB headline.
- **L12.** `strategy: "largest"` on `/clean/duplicates` can do nothing,
  because size is part of the group key (`actions.py:592-604`).
- **L13.** `/clean/downloads` ages files by modification time, which
  extraction preserves from the archive, so a file downloaded today can
  be planned for the trash (`actions.py:663-675`).
- **L14.** Projects tab: "Trigger Scan" starts four unrelated agents
  and no project scan, and the default view shows "Not scanned" for all
  43 projects because `projects_managed.py:92` hard-codes
  `project_health: None`. Left over from the 2026-08-13 move.
- **L15.** `sysadmin_tray/notifications.py:650-655`: in digest mode a
  warning first seen during do-not-disturb is never reported. Latent:
  digest mode is off.
- **L16.** Estate judge: a 200 from the estate whose body lacks the
  expected key is read as "no findings" and standing rows resolve
  (`judgements.py:1413-1415`, `:1797`, `:627-656`); and alert titles
  built from producer strings are uncapped against `String(255)`. By
  reading only.
- **L17.** Stale statements in prose, code being the truth:
  `docs/ARCHITECTURE.md` says five agents (six), 12 jobs (13), eight
  routers (nine), 3,900 tests (4,779), and places `TABLE_TIMESTAMP_MAP`
  in `metadata.py` (it is in `core/retention.py`); `README.md` lists
  GitPython (not installed, not imported) and "~4,100 tests";
  `CLAUDE.md` says CI runs mypy (the workflow runs ruff and pytest
  only) and names two auto-generated files nothing generates;
  `scripts/smoke_test.sh:33` names a user unit that does not exist. The
  tray also has no control that acknowledges an alert, though the icon
  branches on it: 0 of 646,166 alert rows were ever acknowledged.

### Tests that pass without testing the thing

No vacuous tests were found by sampling (no always-true skips, no
assertion-free bodies). The gaps are tests that model the wrong layer:

- `tests/test_tray/test_notifications.py:457-496` calls the action slot
  directly, so H4 is invisible.
- `tests/test_alert_dedup.py`, `test_a_second_restart_writes_a_second_row`,
  asserts on a mock the insert the real index refuses (M13).
- `tests/test_collation_check.py:316-332` uses a mock session that
  cannot model an aborted transaction (M14).
- `tests/test_file_organiser.py:220-235` finds a cache only with a
  config production never uses (M10); the only test of
  `/clean/stale-caches` is its auth check (H1).
- `tests/test_log_incident_fold.py:400-416` pins the window to five
  early resets (M2).
- No test runs a migration downgrade, and four tray modules
  (`overview_tab`, `logs_tab`, `resource_gauge`, `alert_badge`) are
  named by no test.

## 3. Not reviewed, or not assessable

- **Docstrings and design documents.** Several slices read code with
  docstrings stripped and consulted `docs/design/*.md` by search, so a
  code-versus-design disagreement in `log_trends`, `log_review`,
  `reliability*`, `health_review`, `gpu*`, `stalls`, `failures` and
  `handover` could have been missed.
- **Read by inspection only, nothing driven:** `core/failure_replay.py`,
  `gpu_lease.py`, `llm_client.py`, `word_limit.py`, `schema_guard.py`,
  and the `estate.*` library calls they depend on, which live in
  another repository.
- **Partly read:** `sysadmin/units/ports.py` (parsers only),
  `units/recommendations.py`, `units/agent.py` alert maintenance,
  `units/scan.py` outside lines 150-1295, `core/contracts.py` from
  line 610, `monitor/desktop.py`'s cross-thread state,
  `message_backfill.py`, `journal_horizon.py`.
- **Not read:** `sysadmin/snag_claims.py`, `ops_claims.py` and
  `vacuous_guards.py` (13,300 lines that check the documents, not the
  box), `home_audit.py` beyond one function, most of the session
  scripts (`claude-*.sh`, `dgpu-*.py`, `migrate_registry.py`).
- **Not driven:** anything needing a POST, a notification, a daemon
  restart or a database write, so the LLM review paths, the file
  actions against real directories, H4 against Plasma, and the 20
  migration downgrades after the first were checked by reading or on
  temp trees only.
- **CI:** the schema tests skip on GitHub's runner, which has no
  database; they run on the box at push.
- **The 149 test files** were sampled for vacuity, not read in full.
