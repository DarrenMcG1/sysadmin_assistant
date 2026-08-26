# Handoff — 2026-08-26

## Next action

Write the twelfth check against `SNAG-DOCS-005` — `ops_claims` would read a quoted marker as a real one, its mechanism is local and reproducible by building a document that quotes one, and it is the highest-value of the fifteen unchecked entries because the module it accuses is the one every sitting opens with.

## Session 87 is complete — the first entry this registry ever closed, and the eleventh check

`SNAG-ROADMAP-001` is **closed**, open since 2026-08-07 and delegated
since 2026-08-25. The tenth check reported it **refuted** on the day it
was written, against an edit estate-manager had in flight; the trigger
Session 86 left was mechanical, and it fired. Their fix is `a9828dc`,
committed **22:42:29** on 2026-08-25 — *"the placeholder guard is given a
line it can judge, and the branch that had no guard at all gets one"* —
closing their `SNAG-ESTATE-056` and naming this repository's cross-repo
message `e0461fe9` in the commit body.

The live parser reads **69 entries and 26 → 25 open** either side of the
edit, checked entries hold at **ten**, unchecked falls **16 → 15**, and
**all ten still hold**. **2470 tests pass** (2465 − 8 + 13). Ruff clean,
mypy clean. The daemon was restarted at **09:51:59** and `/health`
answers 200 — nothing it imports changed, and the restart was taken
rather than argued with for the reason Sessions 81, 84, 85 and 86 took
theirs.

### Committed is not deployed, and the entry closed anyway

`estate-manager-api.service` last entered active at **11:35:25** on
2026-08-25 — **eleven hours before** the fix was committed — so the
daemon on 8400 is still serving the defective `_first_meaningful`.
Session 86 gave three reasons to hold the entry open and the daemon was
the third; it is **discharged rather than met**. This repository does not
own their deploy, and holding a *delegated* entry open on the owner's
restart state is the second owner the estate rules exist to prevent — the
same refusal that kept the check measuring the producer rather than the
publication. `estate_module_state()` now says `committed` where it said
`released`, because the first wording read as a claim about what is
running over there and it never was one.

The live board is also clean — 0 of 26 projects carries the apology line
— and that is **not** why it closed. An empty population is not a
closure, which is this document's rule twice over.

### The check left the registry with its entry, and a test made that a rule

`tests/test_snag_claims.py::test_every_checked_entry_is_open` already
asserted no check names a closed entry, so closure and removal are one
edit rather than a judgement: a check outliving its entry re-measures a
claim for ever with nobody reading the answer, and a refuted check on a
closed entry would say *go and judge this* for ever — `SNAG-ESTATE-008`'s
shape arriving inside the tool built to prevent it. `hook_apology`,
`HANDOFF_HOOK` and `APOLOGY_PROBE` went with it. `estate_probe` stayed,
because the eleventh check uses it rather than leaving it parsed and read
by nothing.

### The eleventh check, and why a delegated entry was the right target

`check_nudge_wording_unpublished` measures `SNAG-ESTATE-002`. The note
under `SNAG-ESTATE-014` gives *delegated* as the reason five entries
carry no check; `SNAG-ROADMAP-001` was delegated and was closed on
exactly such a read one sitting after the check that noticed. Being
delegated is what makes a check worth writing — the closing move happens
in a tree nothing here watches.

Its arguments come from `dataclasses.fields(Nudge)` rather than a field
list held here, which is the removed check's own defect avoided by having
been paid for once: converting the properties into fields changes the
constructor's signature, and a probe carrying its own copy would raise
`TypeError` and report `unknown` for ever. All three of the entry's
remedies are reachable — the delete is a **refutation**, not a failure to
measure — and a **partial** fix is `mismatch` with the residue named,
which is what the entry's own body asks for. Five mutations were driven
and every one goes red; hard-coding the field list breaks four tests.

### What writing it found, and what is filed rather than fixed

**`PRODUCER_DROPPED_NUDGE_KEYS` cannot fire.** `SNAG-ESTATE-002`'s body
says "a test now fires when the estate fixes its half"; the assertion
sits inside `for nudge in payload["nudges"]`, the live half runs
`require_populated=False` against a route that has answered
`{"nudges": []}` on every occasion anyone has looked, and the recorded
half runs against `tests/fixtures/estate_projects_attention.json`, static
since 2026-08-16. Neither half can witness the fix. The pre-staged
trigger was wired to the entry's *population* rather than its
*mechanism* — recorded on the entry rather than rewritten, because the
check now covers it and a second trigger would be a second owner.

Nothing was filed cross-repo: their tree read cleanly, their venv ran,
and the one message this sitting depended on was closed by them by name.
