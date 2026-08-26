# Handoff — 2026-08-26

## Next action

Write the seventeenth check against `SNAG-ESTATE-010` — a judgement that gets quieter cannot reach a row that is already open — because its claim is a mechanism whose stated population (two dev-server port rows) has since resolved, so a check that looked for those rows would report the entry refuted by somebody closing an editor, and because the mechanism is drivable with an instrument this repository already owns: open a `warning` row against the live database in a rolled-back transaction, judge the same title at `info`, and assert the row's severity and `holder` are unmoved — asserting the **reach** rather than the rung, since the entry's own fourth bullet records that resolve-and-re-raise on a severity mismatch is the obvious fix and rebuilds `monitor/collation.py`'s flip-flop.

## Session 94 is complete — the sixteenth check, and the first that sends a request

`SNAG-UNITS-003` is **checked and stays open**. Checked entries
**13 → 14**, unchecked **11 → 10**, open unmoved at **24**. **2551 tests
pass, 0 skipped** (2532 + 19). Ruff clean, mypy clean.
`sysadmin/snag_claims.py` was edited, so the daemon was restarted at
**21:20:50** and all nine ops claims read green.

### Both claims are measured, because only one of them is a mechanism

The entry's body claims `_services_yaml_snippet` emits a health path it
never fetched; its **title** claims that on this box the guess is "wrong
more often than right", counted at 4 right and 7 wrong of 11 on
2026-08-15 by an author whose first draft said "two of twelve". Rule 1
says a check tests the mechanism rather than the population — and here
the population *is* the sentence in the title. The two refute the entry
for opposite reasons and the notes say which: the generator learning to
look is the **fix**; the box converging on the contract's path is the
**premise** dying with the generator unchanged.
`check_sysd_ollama_ordering`'s split, one entry over.

### The recount, and why the agreement is a measurement

Live, by outbound probe: **4 right, 7 wrong of 11, 0 unmeasured**. The
entry counted *declared urls in `services.yaml`*; this counts *what
answers on the port*. A service serving both paths would have separated
them and none does, so the two agreeing is a result rather than a
tautology — and the ranking could not have assumed it either way. None
of 4, 7 or 11 appears in the module; the recount is printed in `detail`
at both ends of every sitting, and a drift that keeps the direction is
deliberately not a mismatch.

### The two things a draft had to be talked out of

**The private function the recommendation named was the wrong target.**
The entry's candidate fix is "probe once when the snippet is generated",
which is a moment on the whole path — a probe in the *caller* fixes it
and leaves `_services_yaml_snippet` emitting the same literal, so a check
bound to it would report a landed fix as no change. The public
`recommendations_for_scan` is driven instead.

**A constant emitted path is not by itself evidence that nothing looked.**
An implementation that probed, found nothing and fell back emits the same
constant, which is exactly what the two frontends declaring no path at
all would produce. So the refutation needs a **witness**: a port where
the emitted path fails and the service's own answers. Five today; with
none the verdict is `unknown`, which is also how the check degrades
offline — the offline behaviour is a case of the rule rather than a
special case bolted onto it.

### The control that carries the whole verdict

Every guess-probe is paired with a probe of the service's own declared
url. A stopped service reports every path wrong, so without the control
this entry would read as **holding hardest on the morning the box came
up**. A service failing its own url is `unmeasured` and named, never
counted as evidence — `ports_checked`'s rule. The reading is the
monitor's own: `SysAdminAgent._check_http` under `_http.scoped()`,
classified by `is_fault` off the CHECK constraint's map, with an `ast`
sweep now refusing a hand-written comparison to `"ok"` here too.

### Nine falsifications, nine fired — and one found a report defect

The last break, joining the empty path away, exposed a note reading
`ports (, /api/health, /api/v1/health, /health)` — four paths named as
three, because two services declare a url with no path. `(no path)` now,
with a test that fails against the join. One control has a
**measured-empty population and says so**:
`test_the_probe_never_leaves_this_machine` stays green with `_loopback`
deleted, because the only off-box url in `services.yaml` declares neither
a port nor a unit; the falsification that fires drives a remote entry
through the prober directly, and the docstring names it.

### The unplanned find: two readers, two totals, one open count

`load_entries` reports **68** entries for `snag_list.md` where
estate-manager's `read_snags` reports **70** — measured either side of
this sitting's edit, so neither moved. Both report **24 open**, the
figure the banner and the report use; the difference is the local reader
skipping closed and template sections by construction. Session 93's
handoff published 70, which was the owning parser's number. Recorded so a
next sitting does not read 68 as a regression.

### Blocked

Nothing.
