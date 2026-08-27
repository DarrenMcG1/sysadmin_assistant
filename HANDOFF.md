# Handoff — 2026-08-27

## Next action

Write the eighteenth check against `SNAG-ESTATE-009` — a dev server started inside a sweep window is unattributed, so it is judged at `warning` rather than quietened — because its population is a timing accident nobody can arrange (rule 1 again, and the fourth entry running to it) while its mechanism is exactly what this sitting's new harness now drives: `quietened_judgement_reading` already inserts a `unit_audits` row inside a rolled-back transaction and judges a synthetic breach through the real `EstateJudgeAgent._execute`, so the check is the same drive with the probe port **left out of** the sweep blob, asserting that `_attribution` returns no holder for it and the judgement lands at `DEFAULT_SEVERITY` — with the witness the other way round this time, a second port that **is** in the blob and must come back `info`, since a run where nothing is quietened at all would otherwise look identical.

## Session 95 is complete — the seventeenth check, and the first that writes to the database

`SNAG-ESTATE-010` is **checked and stays open**. Checked entries
**14 → 15**, unchecked **10 → 9**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2570 tests pass, 0 skipped** (2551 + 19). Ruff clean, mypy
clean. `sysadmin/snag_claims.py` was edited, so the daemon was restarted
at **08:31:41** and all nine ops claims read green.

### The entry predicted its own population away

It is filed off two live rows — `Estate port 3110 registry breach` and
`Estate port 8110 registry breach`, both VS Code dev servers standing at
`warning` with `details['holder']` null while Session 57's fix ran three
lines away — and its **own third bullet** says it self-clears when the
editor closes. A check that counted those rows would therefore report
the entry refuted by somebody shutting a window. Measured: **zero open
`estate_judge` rows** on the box today, mechanism untouched. That is
Session 83's rule met by an entry that had already argued its own case.

### The instrument, and why it had to be `_execute`

The claim is a branch three statements into `EstateJudgeAgent._execute`
— a judgement whose title is already open is skipped *before* anything
reads its severity or its details — and every fix the entry contemplates
lands in that same loop, so a check that rebuilt the loop beside it would
report a landed fix as no change. Three things are supplied and nothing
else is touched: an `httpx.MockTransport` for the estate's answer (so the
real `pull_all` runs against it), a `unit_audits` row inside the
transaction for the sweep's attribution (which is what makes both ports
transient and therefore quiet — Session 57's own route), and one
already-open row at `warning` with `holder: null`.

### Two decisions that carry the verdict

**The assertion is the *reach*, never the rung.** The entry's fourth
bullet names resolve-and-re-raise as the obvious fix and refuses it, so a
fix may land as an in-place rung, as a resolved row plus a fresh one, or
as the `holder` blob alone with the severity unmoved — and a check
reading that one column would call two of those three no change. All
three are driven as stand-ins modelling the fix.

**The unmoved row is evidence only beside a row that moved.** The same
`_execute` call judges a second synthetic port with nothing open under
its title, and it must land at the quieter rung carrying a transient
holder before either verdict means anything. Driven as the falsification:
with `_attribution` returning an empty `PortAttribution` the standing row
is still unmoved and the verdict is `unknown`, not `match`.

### What writing to the live database cost, and what paid for it

Fifteen falsifications, fifteen fired. The one that justifies the write
replaces the rollback with a **commit**; the clean-run and failed-run
guards fire independently, the second proving the `finally` covers a
drive that raised.

**That falsification corrected the guard it was aimed at.**
`_surviving_rows` counted by the probe's own message — and the row the
probe *raises*, the witness and the more interesting write, carries the
estate's own `summary`, because `raise_alert` is handed the judgement's
message. The guard was blind to exactly the row the check exists to
produce; the committing stand-in leaked one past it. Found on the box,
deleted, guard now counts by title.

**One falsification passed against deliberately broken code, for the
fourth time here and in a new shape.** The restore of `logging.disable`
was asserted inside a `caplog.at_level` block, and pytest's
`catching_logs` sets `logging.disable(NOTSET)` on entry and restores the
previous level on exit — so the fixture put the global back whatever the
module did. Split into two tests, only one of which may touch `caplog`.
The three earlier instances asserted a *value* where they meant
provenance; this one asserts a *global* inside the context manager that
owns it.

### One documentation gap closed on the way

`snag_list.md`'s top preamble named **Session 93**, because Session 94
added a marker and wrote no preamble. Closed by writing this sitting's
rather than by re-dating the old one — the block that says what a sitting
did is the wrong place to be silently two sittings behind.

### Left deliberately

- **Nine open entries still carry no check**: `SNAG-ESTATE-004`, `-006`,
  `-007`, `-009`, `-012`, `-014`, `SNAG-SVC-001`, `-002`,
  `SNAG-TRAY-008`. Three are delegated to estate-manager and
  `SNAG-ESTATE-012` is explicitly not machine-checkable — deciding that an
  English sentence is a claim is a human's job, which is what that entry
  says.
- **`sysadmin-check-snags` exits 2**, and correctly: the convention
  finding about those nine is `unknown`, not a failure. All fifteen
  entry checks read `ok`.
- **Two readers still report two entry totals** — `load_entries` 68
  against `read_snags` 70, both reporting 24 open. Unchanged from Session
  94, recorded so it is not read as a regression.
