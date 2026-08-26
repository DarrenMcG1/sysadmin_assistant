# Handoff — 2026-08-26

## Next action

Write the fifteenth check against `SNAG-ESTATE-013` — the `check:expires` claim that takes a naive instant — because it is the only unchecked entry whose subject is this repository's own claims machinery, so its instrument is `ops_claims.read_markers` and it needs no cross-repo read at all, and drive it at both an aware and a naive producer stamp so the hour it is out by is measured rather than argued, exactly as `SNAG-LOG-009` was.

## Session 92 is complete — the flake was `hash()`, and the loop could not have found it

`SNAG-TEST-001` is **reproduced deterministically and closed**. Open
entries **25 → 24** (one closed, none opened), unchecked **13 → 12**,
checked unmoved at **12**; 70 entries either side, measured with
estate-manager's `read_snags`. **2514 tests pass** (2511 + 3). Ruff
clean, mypy clean. Nothing under `sysadmin/` was edited — the fix is
`tests/test_snag_claims.py` and four documents — so **no restart is
owed** and `check-ops-claims.sh` reads all nine claims green.

### The cause, and why it is upstream of the path the entry read

Three falsification guards in `TestChecksAgainstTheLiveBox` patch in a
hypothetical fix whose only job is to render two signatures that agree
past `SIGNATURE_DETAIL_CHARS` **apart**, and all three built that
disambiguator as `` hash(s) % 997 ``. CPython seeds `str` hashing from
`PYTHONHASHSEED`, so the marker is stable inside a process and different
between them. When the probe pair collides mod 997 the stand-in
disambiguates nothing, `check_capped_signature_collides` correctly
reports the entry **unrefuted**, and all three guards fail together —
having measured the stand-in's luck rather than the check's sensitivity.

Both of the entry's exclusions are **correct**. The probe *is* pure — a
fixed anchor, no database, no unit files — and there *is* no randomising
plugin, so collection order *is* stable. The secret `hash` reads is
established before the interpreter imports anything, so it sits upstream
of the code path being read. That is the transferable half: **a defect
whose input is the process cannot be excluded by reading the process's
code.**

### The third name is recoverable, because the population is closed

Builtin `hash(` occurs **exactly three times in the repository**, at
`tests/test_snag_claims.py:618`, `:637` and `:657`, all inside one class
— so the third guard the tail dropped is
`test_a_divergence_aware_cap_refutes_both_halves`, adjacent to the two
the entry names. `PYTHONHASHSEED=282` reproduces **`3 failed, 104
passed`** and those three names: the entry's own symptom to the digit.

### The recommended method was run, as the control

40 whole-file runs under `-p no:cacheprovider`, **all green** — which is
what 1/997 predicts. Even odds need ~690 runs and 99 % confidence
~4,600, over seven hours at 6 s a run; the seed scan hit its first
collision at 282 in under a minute. **A per-process defect is hunted per
process, not per run**, because the thing that differs between two runs
is the one input a loop cannot vary.

The rate is **19 collisions over 20,000 seeds** — 1 in 1,053,
indistinguishable from the modulus — so the entry's own "once in twenty
runs" was **50x too high**. That makes the nuisance smaller and the
diagnostic worse: the fifteen green runs were never evidence, and
neither would the next nine hundred have been.

### The counter-intuitive result, and it decided what shipped

Driven at the old behaviour in **both** directions. At seed 282 all six
guards fire. At seed 0 **the three original guards are green** and only
the AST sweep and the purity pin fire. So
`test_it_separates_the_probe_pair` — which asserts the property directly
— inherits the same 1/997 and is green at 996 seeds in 997, while
`test_no_guard_here_reaches_for_the_randomised_builtin`, which merely
refuses the builtin, is red at **every** seed.

**Banning the instrument beats measuring the property**, and only
because the property is the thing being randomised. The sweep is AST
rather than textual because the docstrings around it are full of the
word — `RecommendationInfo`'s prose-in-a-docstring trap, answered on the
correct side.

`_marker()` is `blake2s(text.encode(), digest_size=4).hexdigest()`: the
same short marker with the randomisation removed, behind one helper
rather than three copies of an expression — `journal_command`'s three
callers formatting one fact, one file over.

### What was deliberately not written

**No registry check.** `SNAG-TEST-001`'s claim is about *this suite's own
instrument*, so a `sysadmin-check-snags` entry would read its own output
— `SNAG-ESTATE-014`'s stated reason for having none. The guard is a test
because the thing guarded is a test.

It nonetheless sat in `convention:unchecked` for a day as though a check
were owed. That finding counts entries with no check and **cannot tell
"not yet" from "never"** — `ports_checked`'s rule at the level of the
register rather than the reading. Recorded against `SNAG-ESTATE-014`,
together with the third way its number moves: an *unchecked* entry
closing moves it for the same reason a check does and buys nothing, so
the pair of counts still does not separate the three cases.

### Blocked

Nothing.
