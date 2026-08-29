# Handoff — 2026-08-29

## Next action

Take `SNAG-SYSD-004` on its own terms and settle whether the announcer should fail fast or wait, since this sitting measured that its guard tests for the bus socket rather than for a notification server on it and that lingering makes those two different things at exactly the boot where the daemon most often dies.

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
