# Handoff — 2026-08-29

## Next action

Take the next open entry on its own terms and enumerate every surface its mechanism reaches before accepting the cost it states, since this sitting and the three before it each found the entry's own scoping to be the smaller or the wrong half.

## Session 122 is complete — a cut identity is not an identity

`SNAG-LOG-013`'s **alert half is fixed**; its roll-up half stays open and
its check still reads `still holds`, which is correct — that check drives
the two advice surfaces and nothing else.

**The entry prices its cost at *"a GET advice surface, no toast and no
row"*, and that is true of the module it names.** `log_signature.`
`alert_title` cuts the same signature at a budget of 196–221 characters
and **is** the dedup key, the set-based resolve's key and the tray's
`{severity}:{title}` fingerprint. Two faults agreeing past it are one
row, one fingerprint and one toast — `SNAG-AGENT-005`'s masking defect
at the surface that entry exists to protect, arriving from the other
side.

**Measured before anything was decided, on the entry's own population.**
`SNAG-LOG-008`'s backfill has rewritten `message`, but `raw_line` holds
the journalctl record verbatim, so the pre-backfill signatures are
recoverable exactly as `read_journal` composes them:

```
historic:  39 signatures -> 21 alert titles, 4 of them covering 2, 2, 2 and 16 faults
           (the sixteen are `warning`, stored not raised; one pair is `error` and raised)
after:     39 signatures -> 39 alert titles, 0 colliding
live:      50 signatures -> 50 titles, 2 cut, 0 colliding
```

**The live margin is one fault wide.** The surviving cut is a Python
traceback whose first 211 characters are starlette's `lifespan` frame —
boilerplate shared by *every* lifespan-time failure, which is the class
`schema_guard` raises.

**What ships is a discriminator, not a bigger cap.** Eight hex
characters of the whole signature's SHA-256, on cut titles only.
Raising `TITLE_MAX` moves where the cut falls and nothing else, which is
this entry's own argument; a digest over the part cut away is the only
**per-row pure function** that two records differing past the bound
cannot defeat — and per-row is exactly what the entry says its roll-up
half cannot have, so the fix that is impossible one level down is
available one level up and only there. `hashlib`, never builtin `hash`:
`PYTHONHASHSEED` salts that per process, so the aggregator and
`log_trends` would disagree about one fault across a restart.

**Deploy cost measured rather than argued**: only a *cut* title is
stamped, and **0** open rows carried one (3 all-time, all resolved), so
no fingerprint moved.

**The existing test is what pinned it.** `test_title_fits_the_column`
asserted the cut was *marked* and never that it stayed *distinguishing*.
Five tests replace it and only **one** goes red against the pre-fix code
— the other four are controls over the fix's own failure modes and were
falsified against mutations of it: digest-instead-of-text,
stamp-everything, digest-the-message, builtin `hash()`.

**estate-manager's message `99679328` closed in the same sitting.**
`read_snags` raises `UnreadableSnagText` where it returned
`([], "unrecognised")` — the shape our `5a8bbc97` filed. `parser_counts`
needed no code change; its docstring did, and the test stand-in gained
the raising shape. **Both guards stay**: the `except` owns the new shape
and the `if not rows` gate the old, which is not dead code because
`estate-lib` is an editable install and the parser is whichever revision
of their tree is checked out.

2,869 tests pass (2,863 + 6, none retired), ruff and mypy clean. Daemon
restarted at **15:11:44** — owed this time, `log_signature.py` is in the
import graph — and again at **2026-08-29 15:17:47** for a docstring in
`snag_claims.py`, which is `ops_claims` rule 4's documented false
positive taken rather than argued. `/health` 200, clean journal, and
`GET /api/logs/trends` serves both cut titles with a discriminator. One
alert is open and named in the block: `Unusual CPU usage`, raised by
this sitting's own suite run.

**What is still open on this entry**: the roll-up's divergence-aware cap,
which needs the sibling set and so cannot live in a per-row pure
function. Nothing about that changed.
