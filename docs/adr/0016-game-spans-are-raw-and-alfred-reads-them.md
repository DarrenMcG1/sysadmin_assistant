# ADR-0016 — Game spans are raw, and Alfred reads them

**Date:** 2026-10-14
**Status:** Accepted (the owner's rulings, Session 369). Built by
Sessions 370 and 371 (2026-10-15); amendments from both builds in §7
and §8. §4 amended from Alfred's answer on retention (Session 380,
2026-10-16).
**Context:** estate message `4dc2b8bc` (alfred → sysadmin-assistant, filed
2026-10-11). The owner asked for a read-only endpoint returning the time
spans in which a game was running over a date range, so Alfred's
plan-against-actual brief can log gaming as Downtime. The owner ruled the
same day that it is built here, not in Alfred: Alfred may not read this
repository's database, and process inspection belongs to this repository.
Nothing on the box records processes, command lines or the active window
today.

---

## 1. Decision

A new scheduled job polls every **60 s**. It records each game it sees
as a **span** in `sysadmin.game_spans`, and each stretch where the game
held focus as a row in `sysadmin.game_focus`. It serves both through
`GET /api/games/spans?start=<iso>&end=<iso>`, **raw**: one span per
unbroken run of polls, with no merging and no minimum length. Rows are
kept **30 days**.

The four rulings, each taken by the owner on this date:

| question | ruling | rejected |
|---|---|---|
| detector | Steam `AppId=` from the full command line, plus an owner-kept executable list | Steam only (misses non-Steam games); list only (makes the owner type every Steam game) |
| focus | a one-shot KWin script per poll, run only while a game is present | a resident KWin script (§3); presence only |
| retention | 30 days | 7 days (no slack beyond Alfred's minimum); 90 days (no reader) |
| merging | raw spans, Alfred merges | merged here; both behind a flag |

## 2. Detection

- **Steam.** A process whose full `/proc/<pid>/cmdline` carries
  `SteamLaunch AppId=<n>` is Steam's launcher (the "reaper") for app
  `<n>`. The executable name (`comm`) alone cannot see this, so the
  full command line is read. The span lasts as long as that process
  lives. The name comes from `steamapps/appmanifest_<n>.acf`'s `"name"`
  in each library listed by `libraryfolders.vdf` (47 manifests in the
  one library on 2026-10-14). An AppId with no manifest is served under
  the name `steam:<n>`, never dropped.
- **The owner's list.** `games:` in `config.yaml` maps an executable
  name to a game name. That file is where the owner already keeps this
  repository's settings, so the list lives in one place. A process
  matching the list gives `matched_by: "executable"`.
- **Excluded by never being listed.** Discord, and anything else that
  is neither a Steam launch nor on the list.
- **The Steam runtimes are not games.** The "Proton" and "Steam Linux
  Runtime" manifests name tools that Steam launches *under* a game's
  `AppId=`. They never carry `SteamLaunch AppId=` themselves, so they
  need no exclusion. A test pins this against a recorded command line.

## 3. Focus

KWin 6.7.5 has **no D-Bus call that returns the active window** (its
`/KWin` interface offers `queryWindowInfo`, which waits for a click, and
`getWindowInfo(uuid)`, which needs a window id first). A KWin script can
read `workspace.activeWindow`. Driven on 2026-10-14, a 2-line script
loaded through `org.kde.kwin.Scripting.loadScript`, run and unloaded,
printed `pid=2155487 class=project-manager` to the user journal.
`sysadmin.service` is a user unit, so it has the session bus.

- **On a poll that found a game**, the job loads the script, runs it,
  reads its one journal line by a marker, and unloads it. The game holds
  focus when the active window's PID is the game's process or one of
  its descendants. Proton runs the game as a child of the reaper, so the
  window's PID is never the reaper's own.
- **On a poll with no game, the probe does not run.** Running it every
  poll would write 1,440 lines a day into the journal this repository's
  log aggregator ingests. Gated on presence, it writes one line per
  gaming minute.
- **Rejected: a resident script** that calls back on every window change.
  It is more exact, but this repository would then install and keep
  something inside the compositor and claim a D-Bus name to receive the
  calls. A one-shot probe leaves KWin as it found it.
- **When the probe fails** (KWin not running, no session bus, no line
  read), the span carries `focus_known: false` for that stretch. It is
  never treated as unfocused, so Alfred can tell "not looking" from "not
  playing" and fall back to presence.

## 4. Storage and retention

`game_spans`: `id`, `game`, `matched_by`, `appid` (null for a listed
executable), `executable`, `pid`, `started_at`, `last_seen_at`,
`ended_at` (null while open). A poll extends `last_seen_at`. A poll that
no longer sees the game sets `ended_at = last_seen_at`, never the time of
the poll that noticed, so a span is never over-counted by up to 60 s.

`game_focus`: `span_id`, `started_at`, `last_seen_at`, with the same
rule.

- **A restart closes every open span at startup.** Its last sighting is
  the honest end. A game still running after the restart opens a new
  span, which Alfred's 10-minute merge joins.
- **30 days**, through `retention_config` and `TABLE_TIMESTAMP_MAP` like
  every other timed table here. 30 days covers Alfred's 7-day backfill
  four times over.
- **These 30 days are the only raw record of gaming on the box**
  (amended 2026-10-16, Session 380). Alfred answered the question put
  with the reply to `4dc2b8bc` in estate message `36903d39` (Alfred
  keeps what it builds from the spans, not the spans). After its merge,
  drop and unfocused cut, each run becomes one `Downtime: <game>`
  actual entry in Alfred's own table, kept with no expiry. The spans
  themselves are read and not stored. So the owner's expectation held
  for the *reading* and not for the rows: Alfred's entries are the
  history of record for Downtime, and a span older than 30 days is gone
  from the box.
  - Alfred never rebuilds a day older than this window, so an entry
    whose spans have expired is never deleted for want of them. Our
    retention cannot erase Alfred's history.
  - The retention ruling (§1) is unchanged. It rejected 90 days for
    having no reader, and Alfred's answer adds none. Keeping the raw
    spans longer, here or in Alfred, is a new ruling for the owner.
- Both tables come from an Alembic migration, the `sysadmin` schema's one
  owner (contract §2.7, Session 367).

## 5. The served shape

```
GET /api/games/spans?start=<iso>&end=<iso>
{
  "poll_seconds": 60,
  "retained_from": "<oldest timestamp still held>",
  "spans": [
    {"game": "ELDEN RING", "matched_by": "steam_appid", "appid": 1245620,
     "executable": null, "started_at": "...", "ended_at": null,
     "last_seen_at": "...",
     "focus": [{"started_at": "...", "ended_at": "..."}],
     "focus_known": true}
  ]
}
```

- A span is returned if it **overlaps** the range, not only if it starts
  inside it, so a session crossing midnight appears on both days.
- `ended_at: null` means the game is still running at the last poll.
- `retained_from` lets Alfred tell "no game" from "older than this
  service still holds".
- The model goes in `sysadmin/core/contracts.py` as `response_model=`,
  with a row in `CLAUDE.md`'s registry.

**Raw, and why.** Alfred's thresholds (merge gaps up to 10 minutes, drop
runs under 5 minutes, end a span after 15 minutes unfocused) are
Alfred's reading of *Downtime*. Applying them here would make that policy
the only view any second reader could get. The estate's gaming ladder
(below) needs the unmerged start. Alfred's message asked which; this is
the answer.

## 6. What this does not decide

- **Publishing a game-start event.** estate-manager's gaming ladder
  rung 2 (evict models when a game starts) is blocked on *"nothing on
  this box detects a game starting"*. After this ADR, something will.
  Whether it publishes an event (an MQTT topic under `estate/…`, which
  the estate's broker rules govern) or the estate polls this endpoint is
  a second concern. It is recorded in `docs/roadmap/tasks.md` and not
  decided here.
- **Alerting.** A game running is not a fault. Nothing in this ADR
  raises an alert.
- **Alfred's merge.** It is theirs, as stated above.

## 7. Amendments from the build (Session 370, 2026-10-15)

Both were found while building and neither changes a ruling.

- **A Steam span is keyed on the AppId, not on the reaper's PID** (§2).
  Steam's `console_log.txt` for Deadlock on 2026-10-14 shows two
  processes whose argv carries `SteamLaunch AppId=1422450`: the
  `steam-launch-wrapper`, which has the reaper's command line as its
  arguments, and the reaper. Keyed on a PID, one game opens two spans.
  The span lasts while any process carrying the AppId lives.
- **`game_focus` has a `state` column, `focused` or `unknown`** (§4).
  §3 says a stretch where the probe failed carries `focus_known: false`,
  and §4's columns had nowhere to record it. An unfocused stretch has no
  row. Until the KWin probe is built, every gaming minute is `unknown`.
- **Added: a gap of more than three polls ends a span** even if the game
  is still running. A suspended box resumes with the game open, and
  extending the span across the night would report it as play.

## 8. Amendments from the second half (Session 371, 2026-10-15)

None changes a ruling; the first was a false premise in §3.

- **The daemon is a system unit, not a user unit** (§3 said it "has the
  session bus"). `sysadmin.service` runs in the system slice as
  `User=gaddi`, and its environment has neither
  `DBUS_SESSION_BUS_ADDRESS` nor `XDG_RUNTIME_DIR`; `gdbus` there fails
  with "Cannot autolaunch D-Bus without X11 $DISPLAY". The probe sets
  `XDG_RUNTIME_DIR` with the helper `systemctl --user` already uses
  (`sysadmin/monitor/systemd.py`'s `build_env`), and with that alone
  `gdbus` reaches KWin and `journalctl --user` reads the line. Driven
  under a stripped environment: firefox's PID in 0.011 s, script
  unloaded, no file left.
- **Each served focus stretch carries its `state`** (§5's example had
  only `started_at`/`ended_at`), plus `last_seen_at`. `focus_known` is
  kept at span level and is `false` when any stretch is `unknown`, so a
  reader that ignores the list can still fall back to presence.
- **No active window is an answer.** The script prints `pid=0` when
  nothing holds focus, and that minute is recorded as unfocused. Only a
  probe that got no line is `unknown`.
- **A timestamp with no offset is refused (422)**, and a `+01:00`
  offset must be sent as `%2B01:00`, because a query string decodes `+`
  to a space. The refusal suggests the `Z` form.
- **`retained_from`** is the later of the detector's oldest held run and
  the `game_spans` retention cutoff, and `null` when the detector has
  never run.
