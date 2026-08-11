# Handoff — 2026-08-11

## Next action

Run `sudo systemctl restart sysadmin.service` so the daemon picks up the desktop notifier wired today, then take Session 36, the briefing envelope, which is unblocked and unstarted.

## The tray was not broken — nothing had ever started it

Reported as "no longer working". Diagnosed before building: **no
autostart entry, no unit**. It had only ever been launched by hand, and
the box booted 2026-08-10 06:37, which ended the last instance. Running
`.venv/bin/sysadmin-tray` directly proved the code was fine — it came up
and polled the API immediately.

So the estate's only notification surface had been dead for a day and
nothing said so. Same shape as SNAG-DB-001: what would have told you was
what was down.

`~/.config/systemd/user/sysadmin-tray.service` is installed, enabled and
running. **It is the first GUI unit on this box and the contract's
skeleton is wrong for one** — lingering is on for `gaddi`, so a
`WantedBy=default.target` unit would start at boot with no compositor and
restart-loop. It binds to `graphical-session.target` instead, which works
because KDE imports `DISPLAY`/`WAYLAND_DISPLAY` into the systemd user
manager (checked with `systemctl --user show-environment`, not assumed).
`Restart=on-failure` rather than `always`, because the tray's own Quit
action exits 0 and `always` would make it a no-op. Both rules are now in
[monitorable-project.md](docs/guides/monitorable-project.md) §2.3.

Wired into services.yaml with `monitor: false` and a reason: bound to the
graphical session, it is *correctly* inactive whenever nobody is logged
in, so a check would alert every night and train you to ignore the one
surface that shows you alerts. That is acceptable only because the
desktop notifier below landed hours earlier — a tray dying mid-session is
now covered rather than merely unwatched.

**The services.yaml entry needs the same restart the notifier does**: the
daemon loads services at startup.

## SNAG-CFG-001: the daemon could not speak, and nobody had noticed

Chased from a stale config key, found to be a dead limb.
`Notifier.send_notification` is fully implemented, DND-aware and
retry-capable, and **nothing outside its own tests has ever called it**.
`raise_alert`'s docstring says "the notifier service should be called
separately"; `monitor/agent.py` says criticals are "to be picked up by
notifier". Neither ever happened. Every alerting path ended at a database
row and waited for the tray to come and read it.

`sysadmin/monitor/desktop.py` now subscribes to `alert.raised` and sends
via `notify-send`. It is the tray's **understudy**, silent whenever
`/api/sysadmin/alerts` has been polled within 180s, so the two never both
toast one alert. The tray was **not running** while this was written
(`ps`, `ss` — no process, no connection to 8500), which is exactly the
case it covers.

**The gate that makes it survivable is one-notification-per-incident.**
The monitor writes one alert row per failed check: 186 rows for one
`venture-assistant` outage, 123 for one `internet` outage, 88 criticals a
day, and **547,814 unresolved `Log error: kernel` rows** sitting in the
table now. Verified against those live rows — `Log error: kernel` stays
silent, an unseen title speaks, both silent while the tray polls.

Both gates **fail closed**: an unreachable database returns "not new",
because the alternative turns a connection blip into a storm.

**Two things this needed that were not obvious.** `sysadmin.service` is a
*system* unit with no session-bus address, so a bare `notify-send` fails
with "Cannot autolaunch D-Bus without X11 $DISPLAY" — the address is
supplied in code from `/run/user/<uid>/bus`, only when the socket exists,
so no root-owned unit file has to be edited. And the subscription is on
the event bus rather than inside `raise_alert`, because `core` must not
import a domain and because `_queue_event` buffers until the
transaction commits — which is what stops the notifier's own query
racing the insert it is reacting to.

**Left open on purpose, in the Backlog**: recovery is never announced
(`alert.resolved` carries `"Project % health critical"`, a pattern, not a
subject); the presence signal cannot tell the tray from any other client
of the alerts route; and those 547,814 rows have never been purged,
because retention purges resolved rows only.

**This one needs the restart.** Unlike the organiser, it is daemon code.



## Session 31: idle nudges, and one wrong premise caught by grep

Shipped: an `active` project whose human-written next action has not
changed for **7 days** raises an `info` alert; at **14** it is escalated
to `warning`. Per-project override is `idle_nudge_days` in
`.project.yaml`, beside `alert_threshold` and deliberately separate from
it — a long-cycle repository should be able to relax the commitment clock
without also going unwatched for a missing README.

**No new endpoint, no migration, no restart.** Nudges are `alerts` rows
(`Project <name> next action idle`) raised by the organiser, which is a
oneshot timer, so this goes live on the next timer run. That is the
distinction the previous handoff had to work out the hard way and it held
again here: the daemon serves start-time code, the organiser does not.

### Decisions, and what was rejected

- **7 days, not 5 and not 14-as-first-rung.** The three eligible projects
  turn their actions over in 1–4 days, so 5 is inside normal turnover and
  would nag. 14 as the *first* rung was rejected because a feature that
  can never be observed firing cannot be trusted.
- **Eligibility was extracted, not re-implemented.**
  `next_action.eligible_candidates` now serves both `GET /api/projects/next`
  and the nudge. Two copies of "what counts as a commitment" drift in the
  invisible direction: the endpoint stops offering a project while the
  nudge goes on reminding you about it.
- **Raise once per open nudge, not once per scan.** `raise_alert` inserts
  unconditionally — the mechanism behind SNAG-PROJ-004's 1,664 rows — and
  the organiser runs daily. The health-alert pattern would write one row
  per day per stuck project: a nag in the database rather than the tray.
- **Escalation resolves the quiet row and raises a loud one**, rather than
  updating severity in place. The tray fingerprints on
  `"{severity}:{title}"`, so an in-place change keeps a fingerprint it has
  already suppressed and the escalation is recorded but never spoken.
- **The escalation is a gap, not a multiplier.** A project that relaxes
  its threshold to 21 escalates at 28, not 42.
- **Never `critical`.** Criticals break through DND by configuration;
  waking someone at 02:00 about a roadmap item is how a monitor gets
  muted wholesale.

### What was checked rather than assumed

A live organiser run over 25 repositories reported
`nudges: {raised: 0, escalated: 0, resolved: 0}` — correct, because all
three eligible projects changed their next action that morning. **A clean
run proves only that nothing crashed**, so the ladder was then run over
the real historical series for this repo: the "Session 24: File organiser
tiers" action, **9 scans across 2 days**, which `streak_days` folds to one
2-day run and the ladder scores `info` / `warning` / no-nudge at the
thresholds it should. That 9-to-2 ratio is Session 29's days-not-scans
argument holding on live data rather than in a fixture.

**The design was written three times around the wrong config knob.**
`notifications.desktop.min_severity` looks exactly like the setting that
decides whether an alert is spoken, and **nothing in `sysadmin/` reads
`config.notifications.desktop`** — the live gate is
`tray.notify_min_severity` in a different section, which the tray parses
itself. Both currently read `warning`, so the two have never disagreed
and the redundancy has never surfaced. Filed as **SNAG-CFG-001** and left
unfixed on purpose: it sits on the tray's configuration boundary and this
session changed no notification code.

### State

- 43 new tests, suite **1701 → 1744**; `ruff` and `mypy` clean.
- Alerts table untouched by this run — nothing on the estate is stuck for
  7 days, so there is nothing to see in the tray yet. The first thing that
  will ever fire is an `info` row with no toast behind it.
- `docs/roadmap/tasks.md` Session 31 is ticked with the rejected options
  recorded; `STATUS.md` "Next up" now names Session 36.
