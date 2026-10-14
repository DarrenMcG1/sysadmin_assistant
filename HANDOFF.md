# Handoff — 2026-10-14 (Session 367)

## Next action

Write the §2.7 test: build a scratch database to head with alembic upgrade head, assert the head and zero drift, drop it (tasks.md, Session 362 block). *(For: session)*

Session 367's probe is the test's body, so this is small. Alfred's
gaming-spans endpoint (`4dc2b8bc`) is bigger and wants an ADR drafted
with the owner.

## Scheduled action

- Uninstall Steam games until `/` is under 90 %, which closes the
  critical alert. Steam is 891 GB of the 1.4 TB used; Path of Exile 2
  (151 GB) arrived 2026-09-22 and was the biggest single step.

## Session 367: contract §2.7 applies to the sysadmin schema

Session 366's next action. Docs only: the ruling is the ticked item in
tasks.md's Session 362 block.

- Decided: §2.7 (one schema owner, and a test building an empty
  database to head on real PostgreSQL) applies, scoped to the `sysadmin`
  schema. The contract names this repository; the shared `projects`
  database is grandfathered on where a schema lives, not on who builds it.
- One owner is met: the Alembic chain, nothing else creates tables.
- The test is owed and the chain would pass it: a scratch database
  reached `019` from empty in 0.1 s, 0 drift against the models, the
  witness identical to live. Scratch database dropped.
- Rejected: counting `test_schema_drift.py` as the test, because it
  diffs the live schema and cannot see a chain that fails from empty.

## What Session 366 handed on (done by Session 367)

Decide whether contract §2.7's empty-database test applies to this repository's sysadmin schema, and record the ruling (tasks.md, Session 362 block). *(For: session)*

## Session 366: the MT7927 host fault is gone

Session 365's next action. Docs only: a dated amendment under
`SNAG-AGENT-005` in snag_list.md, the tick in tasks.md.

- Re-measured, not copied from the message: firmware hash matches,
  0 firmware errors in each of the last three boots, `hci0` up, rule
  parked as `.disabled`.
- Found two things the message did not say: the Wi-Fi half is now
  bound to `mt7925e`, and the adapter is on USB port `8-11`, not `1-11`.
- The task line named the wrong entry (`SNAG-ESTATE-001`); the
  paragraphs are `SNAG-AGENT-005`'s, as the message said. Corrected.
- Amended rather than rewritten: the August paragraphs stay as history,
  with an italic pointer to the amendment.

## What Session 365 handed on (done by Session 366)

Re-measure the MT7927 Bluetooth firmware and amend SNAG-ESTATE-001's host-fault paragraphs with a dated note (tasks.md, Session 362 block). *(For: session)*

## Session 365: publish_errors is not judged

Session 364's next action. Docs only: the reasoning is the last
paragraph of `docs/design/estate.md`, the tick is in tasks.md.

- Decided: no sixth surface in `SURFACE_PATHS`. 0 of 750 register
  messages have ever failed to publish, a failure costs a phone buzz
  and not a message (sessions read the register over HTTP), and a
  broker outage is already the `mosquitto` entry's.
- Rejected judging an increase between reads: it needs per-run state
  the judge does not keep, and a counter that never falls gives a row
  no honest way to close.
- Reopen when the count is first seen above 0, or when an MQTT
  consumer becomes something a session depends on.

## What Session 364 handed on (done by Session 365)

Decide whether to judge publish_errors on :8400's messages-invariants surface: add it to SURFACE_PATHS or record why not (tasks.md, Session 362 block). *(For: session)*

## Session 364: Steam filled /, not the backups

Session 363's next action. Docs only: STATUS.md's ops block, now 12 of
12 `ok` under `check-ops-claims.sh`.

- pgBackRest ruled out: its 2026-10-11 run expired the March chain and
  `/` fell 116 GB that morning. The 0 ms expires since had nothing to
  remove, so nothing is filed to the estate.
- Found in `resource_snapshots`: +142 GB on 2026-09-22 17:00–19:00 BST
  (Path of Exile 2 installed) and +21.5 GB today 06:07–06:17 (Steam
  updating Last Epoch), which opened the critical row at 06:12:46.
- Decided: name Steam and leave the alert open. Rejected deleting
  anything: what to uninstall is the owner's, and the alert is true.
- The tray and monitor restarts the handoff scheduled happened with
  that boot, so both items are gone from it.
- Stacked and recorded, not worked: the box was powered off by its key
  at 05:40:48 with no clean shutdown (tasks.md, Session 364 block).

## What Session 363 handed on (done by Session 364)

Find what filled / (91 %, critical alert open since 05:12 UTC on 2026-10-14), starting with pgbackrest's 0 ms expire, then refresh STATUS.md's ops block. *(For: session)*

## Session 363: clydeautomation.co.uk is watched

Session 362's next action. One `services.yaml` entry, commit `3331312`.

- Declared `clyde-automation-site` as `kind: http` on the https root,
  no unit, exactly as the message suggested. Reloaded live; the first
  poll read `ok` in 170 ms. Message `6db6bf4c` closed saying so.
- Accepted rather than built: losing this box's connection opens two
  rows (`internet` and the site) for one fault. Rejected adding a
  dependency key to suppress the second: nothing here has one, and one
  extra row in a rare outage does not earn a new mechanism.

## What Session 362 handed on (done by Session 363)

Add clyde-automation-site's kind: http entry for https://clydeautomation.co.uk/ to services.yaml, reload, and close estate message 6db6bf4c. *(For: session)*

## Session 362: the thirteen estate messages triaged

Session 361's next action. Docs only; recorded in tasks.md's Session
362 block and `SNAG-DOCS-033`.

- Closed 11. Eight were done or asked nothing: `6aa1fbc7`, `0db3617a`,
  `8e1e23bb`, `8c5d026c`, `5faf8e47`, `9c40b495`, `1ed64da3`,
  `99f11c1f` (`0db3617a` also left the §2.7 task). Each was
  checked against the tree or the live status, not taken on trust.
  Three left a decision of ours, recorded, then closed: `653e9ae9`
  (judge `publish_errors`), `c86f83f9` (amend `SNAG-ESTATE-001`'s
  Bluetooth paragraphs), `a56e0bc4` (`SNAG-DOCS-033`).
- Kept open 2: `6db6bf4c` (clyde's site) and `4dc2b8bc` (Alfred's
  gaming spans). Both senders asked for a close note when the work is
  done, so closing now would tell them it was.
- Decided: an announcement whose leftover is our own choice is closed
  once the task carries its id. Rejected keeping it open as a reminder:
  the inbox is the sender's channel, and tasks.md is where this
  repository keeps its work.
- One slip: `a56e0bc4`'s close note says nine sites; the snag lists
  ten. A close cannot be edited; the snag is the record.

## What Session 361 handed on (done by Session 362)

Triage the 13 open estate messages: close those already acted on, and record each remaining ask as a task or snag citing its message id. *(For: session)*

## Session 361: the suite runs at push

Session 360's next action. Config in `1848546`; estate message
`732a62cb` closed.

- `.pre-commit-config.yaml` declares pytest, ruff check and mypy at
  `pre-push`, each `verbose: true`. Measured 2026-10-14 at 149.6 s, all
  passed; pytest 149.32 s of it. CLAUDE.md "Step 4: Test" states this.
- Decided: all three gates, not the suite alone. Rule 7 asks only for
  the suite, but ruff and mypy cost under 0.3 s and nothing held them at
  push. Rejected `uv run` in the entries: `.venv/bin` directly, so a push
  never syncs the environment and cannot prune the extras.
- Decided: the full suite, `box` tests included. CI deselects them
  because they read this machine; a push runs on this machine.
- `default_install_hook_types: [pre-push]` keeps a bare `pre-commit
  install` from replacing `.git/hooks/pre-commit`, which is
  `scripts/claude-precommit.sh` and written by hand.
- Installed by the owner 2026-10-14 13:11. The installed
  `.git/hooks/pre-push`, driven with a simulated push of `main`, ran all
  three green (pytest 157.56 s) and exited 0. A real push now runs the
  review gate, then this stage.
- Sessions 346 to 354 moved to `HANDOFF-archive.md`: the file was 524
  lines, over estate rule 2's 500-line bound.

## What Session 360 handed on (done by Session 361)

Backfill estate Rule 7: declare the pytest suite at pre-push in a new .pre-commit-config.yaml (verbose), time it, record it in CLAUDE.md (message 732a62cb). *(For: session)*

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

## Older sessions

Sessions 354 and earlier are in [HANDOFF-archive.md](HANDOFF-archive.md).
