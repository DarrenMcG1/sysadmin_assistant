# Handoff — 2026-08-25

## Next action

Judge `SNAG-ROADMAP-001` once estate-manager commits their in-flight fix — the tenth check already reports it refuted, and the trigger is mechanical: when `estate_module_state()` stops saying "uncommitted", close the entry and write the eleventh check against the sixteen that remain.

## Session 86 is complete — the tenth check, and the first that had to run another repository's code

`sysadmin/snag_claims.py` gains `check_handoff_apology_published`,
`hook_apology`, `estate_probe` and `estate_module_state`, and
`SNAG-ROADMAP-001`'s body carries
`<!--check:handoff_apology_published-->`. Checked entries go **9 → 10**,
unchecked **17 → 16**, and **nine of the ten still hold** — the tenth is
the first check in the registry to report **refuted** on the day it was
written. estate-manager's `read_snags` reads **69 entries, 26 open,
dialect `bullet`** either side of the edit, so the marker moved nothing
the board publishes.

**2465 tests pass** (2457 + 8). Ruff clean, mypy clean. The daemon was
restarted at **22:43:16** and `/health` answers 200 — nothing it imports
changed, and the restart was taken rather than argued with for the reason
Sessions 81, 84 and 85 took theirs.

### The question this sitting was handed, and why it needed no new answer

It asked whether a check that skips when estate-manager's venv is absent
is a check at all or a fourth way of reporting `unknown`. It is
**neither: it is the third verdict, used for what it was defined for.**
The `pytest.skip` in `TestAgainstTheOwningParser` does not transfer, and
the reason is what the two things are — a test asserting two readers agree
has nothing to assert when one is absent, while a check *reports on a
claim*, and "nobody managed to test it" is an answer `schema_guard`
already defines and this module already imports. So no checkout, no venv,
a renamed symbol and a tree caught mid-edit are all `unknown` with the
reason named.

### estate-manager was fixing it while this was being written

Their `roadmap.py` was modified at **22:34**, uncommitted, under their own
`SNAG-ESTATE-056`, and the fix is precisely this entry's proposed remedy:
`_first_meaningful` becomes `_meaningful_lines` yielding
`(marked, cleaned)`, and `next_action_from_handoff` tests
`is_placeholder(marked)`. The same module was therefore measured twice
four minutes apart and came back as two different modules, the second
refusing to import — a state no fixture would have produced, and the one
that made the paragraph above concrete rather than theoretical.

All three verdicts were driven at three real states of their tree, never
at fixtures alone: **committed `roadmap.py` → `match`** (reproducing
Session 82's reading exactly), **their working tree → `mismatch`**, **no
venv → `unknown`**.

### The entry stays open, and that is rule 2 rather than caution

A refuted claim is a candidate for closure and never a closure. The fix is
uncommitted, and the daemon on 8400 serves start-time code, so the entry
still holds against everything that is actually running. Because a
`mismatch` off a released fix and one off an edit in flight have opposite
remedies, `estate_module_state()` carries which was measured —
`ports_checked`'s rule applied to somebody else's repository, and needed
within the hour of being written.

### What the falsification caught in the check itself

Its first draft called `roadmap._first_meaningful` to evidence the strip —
a **private helper whose name is what their fix renames** — so driven at
the real fix it reported `unknown` and would have gone on reporting it for
ever, structurally unable to witness the closure it exists to notice. **A
check coupled to the implementation it measures is the shape of the bug it
measures.** The repair states the mechanism more sharply than the entry
ever did: `is_placeholder` says placeholder and the producer publishes it
anyway — no private symbol, and it survives any rename.
`test_the_probe_touches_nothing_private` is the guard, and nothing else
would have caught it coming back: the stub defines only public names, so a
probe reaching for a private one fails identically against every fixture
and reads as an environment problem.

### The reading that would have been wrong

`looks_like_no_action` exists in that module today, matches this exact
wording, and is wired into `/next` — but **not** into
`briefing._next_action_rows`, which is the surface the entry names. A
check asking *does any guard reject this line* answers "yes" while the
producer goes on returning it: rule 1's trap in a new dress, measuring
that a remedy **exists** rather than that the fault is **gone**. The
narrowing to what the producer returns is what avoids it, and the check
measures the producer rather than the publication for a second reason —
the entry is delegated, and judging which consumers estate-manager wired
their guard into is the second owner the estate rules exist to prevent.

### Nothing was filed cross-repo, deliberately

This sitting hit no friction: estate-manager's tree read cleanly, their
venv ran, and Session 82's reproduction is already with them as message
`e0461fe9` — which they are acting on. A note saying "your tree was
mid-edit" is not friction, it is noise.

