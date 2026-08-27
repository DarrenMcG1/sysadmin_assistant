# Handoff — 2026-08-27

## Next action

Write the nineteenth check against `SNAG-TRAY-008` — the understudy forgets what it announced and never adopts what it did not — because it is the cheapest instrument left and the fifth consecutive entry rule 1 decides: its own last bullet says the population is zero today, filed as the stated cost of `SNAG-TRAY-007`'s rule 1 rather than by observation, while its mechanism needs no database, no subprocess and no outbound request, since `DesktopNotifier.sweep_reminders` already takes an injected clock and the reminder population is exactly the keys of an in-memory `_spoken`; the trap to write against is that the entry names **two** faces needing separate drives — a fault raised while the tray was up is never adopted, and a restart forgets everything — so a check driving only the second reports the first as fixed, which is the entry's own warning turned into an instruction for the checker, and the witness runs as the eighteenth's does: a row the instance **did** announce, swept in the same call, which must be restated, or a notifier that had stopped sweeping at all looks identical.

## Session 96 is complete — the eighteenth check, and the sweep window driven rather than counted

`SNAG-ESTATE-009` is **checked and stays open**. Checked entries
**15 → 16**, unchecked **9 → 8**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2591 tests pass, 0 skipped** (2570 + 21, and the arithmetic is
the check). Ruff clean, mypy clean. `sysadmin/snag_claims.py` was edited,
so the daemon was restarted at **09:49:45** and all nine ops claims read
green.

### The population is a timing accident, which is rule 1's fourth entry running

The entry is about a dev server started *between* sweeps — the sweep is
six-hourly, the judge hourly — so any count of today's rows measures
when somebody opened an editor. Its two founding rows are the two
`SNAG-ESTATE-010` was filed from, and they have since resolved.

What makes the mechanism drivable is one fact about the production
reader: `EstateJudgeAgent._attribution` reads **a single** stored
`unit_audits` row and argues in writing for reading no other. So **a
sweep naming one of two ports is a sweep taken before the second
listener started**, and one `_execute` call judges both. Live on the
first drive: 65008 named by the sweep → `info` with `transient: True`;
65009 not named → `_attribution` returns `None`, raised at `warning`
with `holder=None` and an identical detail key set.

### The witness inverts relative to the sitting before it

Session 95 needed an unmoved row beside a moved one. This needs a
**quiet** row beside a **loud** one, because a family whose quietening
had been reverted raises the unswept port loudly for a reason that has
nothing to do with the window and looks identical. Driven as the
falsification: with `_attribution` blind, every assertion the `match`
branch makes is still true and the verdict is `unknown`.

### Two verdict limbs were measured unreachable and deleted

Both found by falsifications **passing against deliberately broken
code** — the fourth and fifth time in this file.

`attributed_unswept` was a fourth limb of `reached`: it is
`_attribution`'s answer read directly, `unswept_holder` is the same
answer read off the raised row, and inside this probe they cannot
disagree. It stays in the report and out of the verdict, and the holder
limb gained a scenario that isolates it — a live look finding a **real
unit** comes back non-transient, so the rung is untouched and only
`details['holder']` moves. The second was a roll-up precheck that could
never fire once the first had passed; the titles now come from the
judgement already validated, one call fewer.

### Three things only running it could have said

- **Backdating the probe's sweep by one `scan_interval_hours` breaks
  it.** It models the entry's own arithmetic and puts the row behind the
  box's own newest sweep, which `_attribution` reads instead — the real
  sweep 1.21 h old won, the swept port came back unattributed, the
  witness refused. The probe must own the newest row or it is not
  holding the variable; `attribution_age_hours` makes that visible.
- **The falsification harness was blind to same-length edits.** `.pyc`
  invalidation is (source mtime, source size) at one-second granularity,
  so swapping `-` for `'` inside a constant within the same second runs
  the *unbroken* module. The injection guard fired on one sweep and
  passed on the next with the identical patch. Harness now clears
  `__pycache__` either side of every case.
- **The committing stand-in leaked exactly the two rows predicted.**
  This probe opens no row by hand, so its guard counts by title from the
  start — the sibling's had to be corrected to that after a leak. Rows
  deleted by id and re-verified at zero.

### The scaffolding is shared, not copied

`findings_transport`, `mounted_judge` and `rolled_back_drive` were
**extracted from** Session 95's probe. All 19 of its tests passed
unchanged across the extraction, which is what makes "identical
scaffolding" a measurement rather than a claim. The two probes share no
port and no holder string, so a survivor names which one left it.

**Fourteen falsifications, fourteen fired**, plus the committing
stand-in.

### Left deliberately

- **Eight open entries still carry no check**: `SNAG-ESTATE-004`, `-006`,
  `-007`, `-012`, `-014`, `SNAG-SVC-001`, `-002`, `SNAG-TRAY-008`. Three
  are delegated to estate-manager and `SNAG-ESTATE-012` is explicitly
  not machine-checkable.
- **`sysadmin-check-snags` exits 2**, correctly: the convention finding
  about those eight is `unknown`, not a failure. All sixteen entry checks
  read `ok`.
- **Two readers still report two entry totals** — `load_entries` 68
  against `read_snags` 70, both reporting 24 open. Unchanged since
  Session 94, recorded so it is not read as a regression.
- **`SNAG-SVC-002` was ranked and passed over**, and the reason is worth
  keeping: its two populations are disjoint only because no agent on
  this box is a systemd timer, which is a property of the box — so the
  obvious check is a *population* one and rule 1 refuses it. It would
  have to be driven at a synthetic timer-backed agent first.
