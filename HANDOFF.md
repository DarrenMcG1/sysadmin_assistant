# Handoff — 2026-08-28

## Next action

Fix `SNAG-ESTATE-013` — make `ops_claims`' `check:expires` marker carry an explicit offset (or `@<epoch>`, as `journal.since_timestamp` already renders for the same reason) and refuse a naive instant, so a prediction copied off a UTC-stamped estate surface cannot be written as a local wall clock with nothing able to say so, which is `SNAG-LOG-009`'s defect one document over and whose fail-closed posture has a non-empty population here because every marker written so far is naive.

## Session 113 is complete — the register says nought instead of falling silent

`SNAG-DOCS-006` is **fixed**. `check_convention` appended its
`convention:unchecked` finding inside `if unchecked:`, so a register in
which every open entry carries a check reported **no line at all** — and
a reader of `sysadmin-check-snags` could not tell that from the finding
having been deleted, renamed, or failing to run. `ports_checked`'s rule
arriving at this repository's own claims register, which was the one
surface it had never reached, because until 2026-08-27 nobody had seen
the zero.

**The blocker the entry filed was a contract, and it is honoured rather
than changed.** `_convention` returned `unknown` unconditionally, so
publishing a zero line would have pinned `sysadmin-check-snags` at exit
**2** for ever — the status `claude-precommit.sh` and
`claude-postflight.sh` read. It takes a `verdict` now, defaulting to
`unknown`. That default is the design decision, not a convenience:
`marker:` and `pin:` are faults by construction — there is no state of
the world in which either line is good news — so only the family that
*can* hold gained the ability to say so, and
`scripts/check-snag-claims.sh`'s documented exit statuses needed no edit.

**Three states, and the third is the one the fix could most easily have
got wrong.** A non-empty set is `unknown`, unchanged. An empty set **over
a population** is `match`. An empty set over **no open entries at all**
is `unknown` again — a document whose entries are all closed parses
cleanly, because `load_entries` reports a problem only when it reads no
entries whatever, so it reaches the count with `open_total == 0` and a
nought nothing could have made non-zero. Served as `match` that is
zero-because-blind wearing zero-because-clean, one level inside the fix
for exactly that. Reachable and empty today.

**This entry was the last member of its own population**, so closing it
drove the new branch live in the same sitting rather than leaving it
theoretical: `?? … 1 of 21 open entries … SNAG-DOCS-006` became
`ok … 0 of 20 open entries carry no check`, and the report exited **0**
for the first time since the module shipped at 16 of 24 unchecked.

**Two of the five falsifications passed against deliberately broken
code**, which is the part worth carrying forward. `overall([])` is
`match` and exits `0`, so the exit-status test written as two status
assertions *agreed with the silence it exists to catch*; and the vacuous
fixture carried no marker, so `pin:fake_one` fired and supplied the `2`
the branch under test was meant to supply — green for a reason unrelated
to its subject. Both are repaired by asserting the finding's **presence**
before its status. Session 78's `waived=True` test and Session 80's
interned-string check, met a third time. A sixth passes against the old
code **by design** and says so: the regression pin that an unchecked
entry still reports `unknown`, which would be pinning the wrong thing if
it could fail against the behaviour it preserves.

**Options rejected.** Emitting the line only when the set is *empty* is
the cheap version and rebuilds the defect mirrored — a reader then
cannot tell a non-empty report from a missing finding; the entry named
it as a trap and it stays refused. Widening `_convention` to take a
verdict for all three families was refused for the same reason the
parameter has a default: what changed is what **one** family can report,
not what a convention finding means. And no check was added — the entry
never had one and is closing, so checks-in-registry is unmoved at **20**,
and its own `Check:` bullet called for a test driving `check_convention`'s
`Finding` objects, which `TestTheUncheckedLineIsPublishedInEveryState` is.

**Blocked**: nothing. **20 entries are open and all 20 claims still
hold.** The only P2 among them (`SNAG-ESTATE-002`) is the estate's to
fix, as are `SNAG-ESTATE-005`, `-006`, `-007` and — at estate-lib —
`SNAG-LOG-012`; three of those five say `delegated` in so many words and
two say it only in their bodies, so the split is stated by name rather
than as a count.

**Verified**: suite **2790 → 2795** (5 added, none retired), `ruff` clean,
`mypy` clean on 92 files, all nine ops claims green and all 20 snag claims
holding. Entry counts re-derived through `estate.snags.read_snags`
(estate-manager at `3c62563`, clean tree): **99 entries either side, open
21 → 20**, agreeing with this repository's own reader. Daemon restarted at
**14:44:14** (PID 3745842 → 3801574), `/health` **200**, schema checked at
head *before* the signal — owed for a file the served application does not
import, which the deploy check's own docstring names as the cost it pays
in the merely-wasteful direction.
