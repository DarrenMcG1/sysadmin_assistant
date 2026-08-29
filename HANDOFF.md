# Handoff — 2026-08-29

## Next action

Take `SNAG-SYSD-005` on its own terms and decide whether a login-time replay is worth building at all, since this sitting measured that four of the five failures this handler has ever had fired into an empty room and that nothing which survives the daemon's death can currently speak for them.

## Session 125 is complete — the wait was real and 24× too short

**`SNAG-SYSD-004` is fixed and its open question is settled by counting.**
The handoff asked whether the announcer should fail fast or wait, and that
was a genuine question rather than a rhetorical one: a *pending*
`notify-send` call really is delivered if a notification server appears.
Driven against a private `dbus-daemon`, a server claiming
`org.freedesktop.Notifications` at **t+4 s** received the notification
intact — right summary, right body, `urgency=2`, `expire_timeout=0` — and
the call returned **0**. `plasma_waitforname` does exactly what it is for.

**What kills waiting is the size of the window against the size of the
gap.** notify-send self-bounds at **60.08 s** on an unserved bus, then
fails with `StartServiceByName … Timeout was reached`. After the four
killed firings the next `class=user` login was **24 min 20 s**, **23 min
49 s**, **6.11 h** and **6.10 h** away. Nought of four could ever have
been delivered, and the nearest miss is **24×** the window. The control is
the fifth firing, 2026-08-11 — the only one that completed, with a human
already logged in.

**So the shipped behaviour was never "wait"; it was "hang, then be
killed".** Three bounds and the smallest is systemd's: `TimeoutStartSec=30`
< notify-send's **60 s** < the bus's **120 s** `service_start_timeout`. The
call could not resolve there at any point.

**The mechanism sits a level below what the entry states**, and that is
what made asking the wrong question expensive rather than merely wrong.
`/usr/share/dbus-1/services/org.kde.plasma.Notifications.service` declares
`Exec=/usr/bin/plasma_waitforname`, so a call to an unowned name is not
refused — the bus **starts a program whose whole job is to block until the
name appears**, and that waiter outlives the handler systemd kills.
`scripts/notification-server-present.sh` asks `NameHasOwner` at
`org.freedesktop.DBus` instead, which the bus answers itself: **3.1 ms**
served, **3.8 ms** unserved, and **five calls started zero waiters against
one notify-send's one**. Three verdicts and three exit statuses,
`check-migrations.sh`'s, which the announcer already consumes one function
up. `TimeoutStartSec` stays at 30 deliberately — once the activation path
is refused the only remaining call is `Notify` against a server that
exists, bounded at 25 s by GDBus, and raising the unit's timeout would
re-admit the wait.

Driven end to end against the real script, with only `venv=` stubbed onto
its own documented "alert row not written" branch: **exit 0 in 31 ms** with
the toast on screen, **exit 1 in 15 ms** on an unserved bus naming the
reason. No deploy was needed — the installed unit's `ExecStart` names the
repository path, so writing the file *is* the deployment.

**Two claims made during the sitting were wrong, and both are worth
carrying.** A falsification passed against deliberately broken code:
mutating the guard to refuse *everything* — the silent-forever failure,
which has no symptom because what it suppresses is itself a notification
nobody receives — left `test_it_admits_the_live_bus` **skipping** rather
than failing, since that test asked the guard under test whether a live
server existed. A control a broken subject can switch off is not a
control; it asks `busctl` directly now.

And **`systemctl reset-failed` returning exit 0 was written up here as a
third correction to this repository's `sudo` claims, and it was not.**
Polkit put an authentication dialog on the owner's screen and they
authorised it — invisibly to the session that ran the command, and
reported by the owner mid-sitting. `pkcheck` says `auth_admin_keep`:
admin authentication required *and retained*, which is why the retry
meant to confirm the finding confirmed nothing. **Exit status is evidence
about the result, never about the privilege.** The reads the toast tells a
human to run are still ungated — measured under `env -i` with no session,
`journalctl -u` exits 0 and `systemctl --no-pager status` exits 1 — so the
Session 70 finding stands; only the state-change claim was wrong.

**The residue is filed rather than absorbed.** `SNAG-SYSD-005`: a
boot-time failure is now refused honestly and still reaches nobody. No
existing component can hold the wait, and the reason is structural — the
tray polls a route the dead daemon serves, and `monitor/desktop.py` with
its `desktop_notifications` store lives *inside* that daemon. The one
component able to speak is the one that has died. Its first requirement,
the announcer recording that it *could not* speak, is deferred to the
entry that will read it, because a flag with no consumer is
`SNAG-CFG-001` at the size of a flag. It is the only open entry naming no
check, and it says so.

## Session 124 is complete — the check found its entry's own trap in its own hand

`SNAG-CFG-003` **stays open at P4 and nothing about it was fixed.** Its
judgement was re-read and stands: the shipped file is coherent, every one
of the ~30 relations holds, and nothing has ever reloaded or booted a
violating configuration here. What moved is its **cost**, which was the
smaller half three times, and it gained the check Session 119 declined as
a piece of work the size of a sitting's own — which it was.

**The mechanism is exactly as filed.** Driven at the real
`reload_configuration` with a real `Scheduler` and an injected
`sync_jobs` — the daemon's shape, not the documented no-syncer fallback,
which would have reported the entry refuted by its own harness:

```
ok=True   requires_restart=[]   jobs_retimed=['service_discovery_scan']
scheduler moved to interval[1 day]; installed sum 25 against reminder_hours 24
shipped margin 7/24 = 3.43x, as the entry states
claude-precommit.sh runs check-migrations.sh and lints, no pytest
```

**The cost is the smaller half at three joints.** At the *installer*: the
journal's 30 days hold **2 reloads, 122 daemon starts and 7 tray starts**,
so a restart installs the same unjudged file 61× more often and the
entry's fix bullet — "does `reload.py` grow a semantic verdict" — is aimed
at 2 of 131; the lifespan's one verdict is `verify_schema_revision()`,
about the schema, and is the standing precedent the entry does not weigh.
At the *guard*: the one inequality it names is **1 of about thirty**
suite-only coherence assertions over the two shipped files across nine
test files, and breaking the sharpest of them (log format `json` against
`text`) reloads cleanly while returning `SNAG-LOG-003`'s 252-character
JSON titles. At the *input*: lowering the tray's `reminder_hours` breaks
the same ceiling and the reload reports **nothing at all**, `AppConfig`
holding `mute_services` alone under `notifications.tray`, with a tray
restart as its installer.

**`load_config` installs, and that is the entry's own defect at two more
scales.** It is `set_config(parse_config(…))`, so reading a specimen
writes the process-wide slot. In the new check it made the
installed-witness read back a value its own helper had written — found by
a mutation that swapped the two and changed nothing. In
`tests/test_config_defaults.py` it left the process holding
`scan_interval_hours: 24`, the configuration that class exists to refuse,
for every test behind it; invisible only because the class's third test
happens to reinstall a coherent copy, which `pytest-randomly` makes a
per-seed accident. Both read with `parse_config` now and both are pinned.

**Every open entry now names a check** — `SNAG-CFG-003` was the last of
the eighteen, against 16 of 24 unchecked when the registry shipped.

**`SNAG-SYSD-004` is opened and is the reason for the next action.**
`sysadmin-failed.service` has been `failed` since 2026-08-23 and **4 of 4**
firings since 08-22 were killed at `TimeoutStartSec=30` inside
`notify-send`, each having already written its journal line and its alert
row. `Linger=yes` starts `user@1000.service` at boot, so the script's
`[[ -S /run/user/1000/bus ]]` guard passes with nobody logged in and the
call waits instead of failing — the fast-fail its own comment describes is
defeated by lingering. Measured at the boot: **boot 08:37:10, bus
08:38:19, sddm greeter 08:38:22, firing 08:38:28, killed 08:38:58**, with
no human session at any point. It is therefore silent in the case Session
39 built it for, a daemon failing at boot, and `SNAG-DB-005`'s record that
this handler *"fired correctly, with a persistent critical toast"* that day
is refuted by the journal.

2,886 tests pass (2,872 + 14, none retired), ruff and mypy clean. Nine
mutations driven, each red on exactly one intended test — and **one passed
against deliberately broken code**: the installed-witness read back from
the specimen is the same number whenever the reload installs, and that
surviving mutation named the missing case, a reload reporting success
while installing nothing.

**No restart, and it is not owed.** The only production file changed is
`sysadmin/snag_claims.py`; `create_app()` does not import it, measured
rather than argued. The deploy check's `no` is `ops_claims` rule 4's
documented false positive for the fourth sitting running, and a restart
with no cause is the needless `kill -TERM` that rule already prices.
`/health` 200, all nine other ops claims green, **0** unresolved alerts.
