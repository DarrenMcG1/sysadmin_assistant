# Handoff — 2026-08-29

## Next action

Take `SNAG-TRAY-009` on its own terms and decide the grace period before wiring the tray to speak about an unreachable backend, since this sitting measured 122 daemon starts in 30 days against a single 37.7-hour outage and a naive rule would fire on every deploy while the real fault went 22.2 hours unspoken.

## Session 126 is complete — the room was not empty, it was silent

**`SNAG-SYSD-005` was taken on its own terms and the answer is yes — but
the entry understated its own benefit by two orders of magnitude, and its
framing of the loss was the wrong way round.**

`sysadmin-replay-failures.service` is a **user** unit wanted by
`graphical-session.target`, running `sysadmin/core/failure_replay.py`. It
is the third half of the lifecycle `unit_failure.py` owns: the handler
writes the row while the application is dead, the lifespan closes it when
the application returns, and this speaks the gap between them to the first
human who arrives.

**The entry priced the loss as the gap to the next login; the table prices
it as the life of the row.** It argued from firings — four of five at a
boot with nobody logged in, next login 24 min to 6.1 h away. But `alerts`
holds only **2** `systemd_onfailure` rows for those **5** firings, three
having hit `record_unit_failure`'s dedup branch, and the one row that was
not fixed at once stood open **37.73 hours** (`1 day 13:43:31`). The login
gap is 24 minutes of that. So the replay recovers **37.3 hours of
silence**, not 24 minutes of lateness. Reading the entry gives the
population; querying the table gives the cost.

**And the room was occupied for most of it, which is the finding worth
carrying.** Reconstructed minute by minute: `start-limit-hit` 18:11:15,
login 18:34:41, tray started 18:34:46 — polled 8500, got nothing, went to
`IconState.DISCONNECTED` and sat there. Across two sessions, **22.2 of the
37.7 hours** had a live graphical session with the tray running and
silent; only 15.5 were an empty room. "Four of five fired into an empty
room" is true about *firings* and misleading about *silence*. The real
fault is that nothing on this box interrupts about a dead daemon, occupied
or not — login is merely the cheapest moment to catch it.

**The blocker the entry deferred on turned out not to be one.** It asked
for `--unannounced` at the announcer first, refusing to add a flag with no
reader — correct for a *history* predicate. The replay needs a *state*
one, and the table already answers it: `resolve_unit_failures` has exactly
one production caller (the lifespan, `main.py:244`), `% failed` sits
outside `RESOLVABLE_TITLE_PATTERNS`, and retention purges resolved rows
only. So an unresolved `systemd_onfailure` row already *means* "this unit
has not come back". No flag, no announcer change, and the second-speaker
trap dissolves with it — a state predicate cannot speak about a fault that
is over.

**Waiting is permitted here and was refused in the announcer, and it is
the number that changed rather than the principle.** `SNAG-SYSD-004`
rejected it at notify-send's 60.08 s against a 24-minute gap. At login the
precondition arrives in seconds: measured at the 2026-08-23 session,
`plasma-plasmashell.service` active **14:44:55**, target reached
**14:44:57**, plasmashell still initialising **14:44:58**.
`WAIT_BUDGET_SECONDS` is therefore **derived** — notify-send's own
measured bound, so the replay spends exactly the patience one blocked call
would have spent anyway, on a mechanism that starts no
`plasma_waitforname`. The read comes **before** the wait, so a clean login
costs **0.34 s** and no D-Bus call at all.

**Driven live, three ways.** Clean box: exit 0 in 0.34 s. A real standing
row inserted and removed: the installed unit found it, announced it, exited
0, with the row's own `CAUSE:` line carried verbatim and `Failed 38 hours
ago` added. A private `dbus-daemon`: a server claiming the name at t+2 s is
caught at **3.02 s** and receives the notification intact — `urgency=2`,
`expire_timeout=0`. `alerts` back to **0** unresolved either side.

**Two falsifications passed against deliberately broken code, and the
second was in the harness rather than the subject.** Eleven mutations each
landed red on exactly one intended test. But the live stand-in notification
server printed `claimed` and **owned nothing a millisecond later** — a
`dbus.service.BusName` held only in a local is garbage-collected the moment
the function returns — so the wait reported `False` after a full budget,
which reads as a verdict about the module and was a verdict about the
harness. The first repair was insufficient in the same way: it asserted the
stand-in had *said* `claimed`, which the mutation satisfies. The premise now
asks the **bus** with `busctl` — independent of both the subject and the
harness — and the mutation fails naming the harness. Session 125's own trap
was avoided by construction: a guard mutated to refuse everything turns
**three** live tests red and skips none.

**`SNAG-TRAY-009` is opened at P2 and is the reason for the next action.**
The tray is silent for two *independent* reasons, and they are
multiplicative in `SNAG-AGENT-008`'s sense. `client.py:407`
`_on_disconnected` emits `connection_lost` only `if self._was_connected`,
and `_was_connected` initialises `False` — so a tray starting against a
backend that is *already* dead never emits, which is exactly the
population. And `tray_icon.py:151` `on_connection_lost` only recolours the
icon; there is no path from it to `notifications.py` at all. Fixing either
alone buys nothing. It was filed rather than folded into this sitting at
the owner's direction, because the real work is the noise question: 122
daemon starts in 30 days against one 37.7-hour outage.

**Every open entry names a check again** — 19 open, **0** unchecked. That
property was Session 124's and `SNAG-SYSD-005` broke it on opening;
closing it and opening a checked entry restores it. All 21 snag checks
green, all 9 ops claims green.

2937 tests pass (2899 + 38, none retired — 26 in
`tests/test_failure_replay.py`, 5 in the new
`tests/test_failure_replay_live.py`, 7 unit-file guards in
`tests/test_systemd_units.py`), ruff and mypy clean.

**Restarted at 20:58:45, and owed on the merits** — `unit_failure.py`
gained a reader and `create_app()` imports it. `/health` 200, `alembic
current` 018 at the packaged head, **0** unresolved alerts. The new user
unit is installed and enabled; it goes `inactive` after exit, so the next
login pulls it in again.

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
