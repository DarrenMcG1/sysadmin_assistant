# Handoff — 2026-08-27

## Next action

Write the twentieth check against `SNAG-ESTATE-012` — a block sentence that is neither a figure nor a marked prediction is still invisible — driving the mechanism rather than today's population by building a synthetic region carrying one sentence a pattern can reach and one that is a claim to a human and matches nothing, running the real `ops_claims.check_all` over it, and asserting the first is reported while the second is silently absent from every family, with the marked half as the witness because a reader that had stopped parsing the region at all reports the unmarked sentence exactly as a working reader does; the entry rules out both obvious remedies by name, so this is a check that the invisibility holds and never a marker built to close it, and it is promoted on evidence this sitting produced without looking for it — the dashboard's own "15 checked / 9 unchecked" was stale from Session 96 and no run could have named it, which is the entry's second live instance after Session 93's, while the Testing row's "166 tests" against a file holding 187 is the same failure deliberately not counted as one, since that row sits outside the region this checker reads at all.

## Session 97 is complete — the nineteenth check, and one entry with two faces

`SNAG-TRAY-008` is **checked and stays open**. Checked entries
**16 → 17**, unchecked **8 → 7**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2619 tests pass, 0 skipped** (2591 + 28, and the arithmetic is
the check). Ruff clean, mypy clean. `sysadmin/snag_claims.py` was
edited, so the daemon was restarted at **12:01:12** and all nine ops
claims read green.

### The verdict is a conjunction, and the entry wrote that rule itself

The entry names two faults with one root — the sweep's population is
what *this process* announced — and then says in its own body that *"a
fix that addresses only the second half leaves the first looking
fixed"*. So `reached` is `unheard_adopted and remembered`. Persisting
the spoken set is the fix the entry names; driven as a falsification it
closes the second face outright and comes back **`match`** with the
moved half in the note. A refuted claim is a candidate for closure; a
half-refuted one is not.

### The restart is a second instance, and its forgotten fault is the first one's witness

One timeline: the tray watching, then away; a sweep; a fresh
`DesktopNotifier` sharing the same clock and session; another sweep. The
fault the second instance has forgotten is the one the first announced
*and restated*, so "announced before the restart" is demonstrated rather
than asserted. Two leaves are supplied — the transport, and the tray's
elapsed time, since `TrayPresence` takes no clock — and `is_watching`
stays the module's own comparison against the live `tray_grace_seconds`.

### Three things only running it could have said

- **The transport falsification is unreachable.** The probe overrides
  `send`, so a stand-in patching `DesktopNotifier.send` never reaches
  it. Re-aimed at gate 2 declining, which is what a live box produces,
  and the shadowing is pinned by a test of its own.
- **Reading the roll-up body is load-bearing.** A fix adopting one
  further fault pushes the probe's own sweep over `_ROLLUP_THRESHOLD`;
  narrowed to titles alone, all three fix-shaped tests fail together.
- **Two dashboard figures were stale and invisible by construction** —
  15/9 against a live 16/8, which is `SNAG-ESTATE-012` exactly, and 166
  guard tests against 187, which is the same failure one table row
  *outside* the region the checker reads. Corrected to 17/7 and 215,
  re-counted rather than incremented.

### Decisions taken

- **Real rows, not a stub session.** A factory answering `IN (:spoken)`
  would be a control the fix breaks: the shape the entry sketches reads
  the *open* rows and caps them.
- **The quiet rung, not `critical`.** `critical` clears Do Not Disturb
  here whatever `min_severity` says, so picking it would arrange to pass
  gate 3 rather than measure it. Every way of not-knowing — a disabled
  understudy, `reminder_hours: 0`, an active DND window, a colliding
  live row — is `unknown` with its own sentence.
- **The refusal names the first premise that failed**, rather than the
  bare `witnessed` bool its two siblings carry: this probe has five
  distinguishable ways to measure nothing.

### Nothing is blocked
