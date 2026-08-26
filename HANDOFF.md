# Handoff — 2026-08-26

## Next action

Write the sixteenth check against `SNAG-UNITS-003` — the generated `kind: http` url that guesses the health path — because its claim is a counted population against a file that changes (`/api/health` correct for 4 of 11 entries and wrong for 7, measured once on 2026-08-15 and never since, by an author whose first draft said "two of twelve"), and because it needs a fourth instrument nothing here has yet: an outbound request that asks whether a path actually answers, with the pure half — driving `_services_yaml_snippet` and asserting what path it emits — kept separate so the check degrades to `unknown` rather than to nothing when the box is offline.

## Session 93 is complete — the fifteenth check, and the straddle that was hemisphere-blind

`SNAG-ESTATE-013` is **checked and stays open**. Checked entries
**12 → 13**, unchecked **12 → 11**, open unmoved at **24**; 70 entries
either side, measured with the reader — which has itself moved, see
below. **2532 tests pass, 0 skipped** (2514 + 15 + 1, plus the 2 that
had been skipping). Ruff clean, mypy clean. `sysadmin/snag_claims.py`
was edited, so the daemon was restarted at **20:30:36** and all nine ops
claims read green.

### The first check whose subject is this repository's own claims machinery

`check_expiry_naive_instant` imports `sysadmin.ops_claims` and drives
`read_markers` into `check_expiry` — one composition root driving
another, which the import-boundary test permits because neither is
*below* the other. No database, no subprocess, no cross-repo read. The
module is imported and driven rather than reimplemented: the claim *is*
what `check_expiry` does with a marker.

`STATUS.md` carries no live `expires` marker, so rule 1 applies and the
mechanism is built. The synthetic block names **both** wall clocks, so
rule 9's pin passes whichever a zone-aware fix would render back out and
a landed fix cannot come back as a pin failure.

### The hour, measured

One producer stamp — the one the entry quotes — rendered naive and
offset-bearing. At `Europe/London`: **`1 minute to run`** a minute
before the marker's own instant; **`passed 59 minutes ago`** a minute
before the predicted event actually happens; **`passed 1 hour ago`** at
the event itself. The offset-bearing form is not understood, and not as
an unsupported form but as a **malformed marker**.

The entry's title is truer than it states. A mis-timed prediction and an
unparsable marker are **both `unknown`**, so the report prints `??`
either way; only `Claim.measured` separates them, which is why the probe
classifies on that field and never on the verdict.

### Two things a run refuted about the draft

**The obvious single straddle holds only east of Greenwich.** At
`America/New_York` the same marker names an instant four hours *after*
its subject, so the prediction outlives what it predicted and an
early-expiry test reports the module correct. `SNAG-LOG-009`'s *"N hours
late at UTC−N"* one document over — in the entry that names
`SNAG-LOG-009` as its own parent. What is measured now is the
**displacement of the boundary**, whose sign the offset decides and
whose existence it does not.

**A control a landed fix breaks is not a control.** The draft asserted
the timer flips at the marker's own text; a stand-in reading the
zoneless stamp as the moment it was *stamped* moves the boundary onto
the event, fails that control, and returns `unknown` where `mismatch` is
right. The boundary is located rather than assumed, so three states get
three verdicts.

It reports `unknown` at `UTC+00:00`, where the two stamps name one
instant and a zone-blind reading is indistinguishable from a correct
one — `ports_checked`'s rule. CI runs there, so the check is honest by
construction and the tests nominate their own zones.

### One falsification passed against the broken code

Seven breaks driven, six fired. The seventh — rendering the naive stamp
with the module's own `EXPIRY_FORMAT` — passed, because `snag_claims`
imports that name into its own namespace and the test patched only the
owner: the module's *behaviour* moved while the probe's rendering did
not. A guard asserting a **value** where it means **provenance**, the
third time here. Repaired twice: the patch moves both names, and an
`ast` sweep refuses `EXPIRY_FORMAT` as an argument to any `strftime` in
the check. The coupling was the draft's real defect —
`EXPIRY_NAIVE_FORMAT` is owned locally now, because what the *document*
wrote is not the same fact as what the module accepts.

### The unplanned find: a guard that had gone silent rather than red

Measuring the entry count found `read_snags` gone — estate-manager moved
it into `estate.snags` in `estate-lib` at **17:06:27** today
(`a5c1834`). `TestAgainstTheOwningParser` shelled into their venv and
read the resulting `ImportError` as *"their parser would not run"*, a
property of the box. **Inert for 3h45m, across the whole of Session
92**, which shipped `2514 passed, 2 skipped` against a Testing row
saying nothing skips here — and which had filed a message about that
very move. Repaired: `estate.snags` imported first (editable install, no
subprocess), **absence is a skip and a moved symbol is a failure**, one
`pytest.skip` pinned by an `ast` sweep. Filed as friction `2822dad4`
with the cost, separately from the two already open about the entry
count.

### Two corrections to STATUS.md, both found rather than reported

The sub-session block claimed 10 checked and 14 unchecked against a live
12 and 12 — neither figure carries a pattern or a marker, so
`SNAG-ESTATE-012`'s class and no run could have said so. And "Next up"
asked for `SNAG-TEST-001` throughout Session 92, which closed it; that
sitting also left no `### Session 92` section.

### Blocked

Nothing.
