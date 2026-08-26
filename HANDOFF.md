# Handoff — 2026-08-26

## Next action

Hunt `SNAG-TEST-001` rather than write the fifteenth check, by running `tests/test_snag_claims.py` in a loop under `-p no:cacheprovider` until the three guards fire again and taking `--lf -vv` for the third name the tail dropped, because every verdict this registry publishes flows through that suite and a guard that is red once in twenty runs makes twelve green checks worth less than they read — and if it will not reproduce, the honest close is a bound written into the entry rather than an argument.

## Session 91 is complete — the fourteenth check, and a probe that counted itself

`SNAG-LOG-012` is **checked and stays open**. Open entries **24 → 25**
(one opened), checked **11 → 12**, unchecked unmoved at **13**. **2511
tests pass** (2500 + 11). Ruff clean, mypy clean. The daemon was restarted
at **17:43:37** and `/health` answers 200 — `sysadmin/snag_claims.py` is
the only source edited and nothing under `sysadmin/` imports it, so for
the eighth sitting running nothing a caller can observe moved.

### The first check pre-staged against another repository's fix

The tenth and eleventh shell into estate-manager's venv to drive their
code. This one needs **no cross-repo access at all**: `estate-lib` is an
**editable** install here (`_editable_impl_estate_lib.pth`, `editable =
true` in `pyproject.toml`), so `strip_markdown` resolves to a file in
their working tree and the check flips to `mismatch` on the next run
after they commit — nothing synced, nobody told. That is measured and put
in the detail rather than assumed: a re-pin to a wheel would show up
there as a path this repository would then lag behind.

It refutes the `SNAG-ESTATE-014` note's stated reason for the second
time. "Delegated… so a check would be a cross-repo read" was never a
property of delegation — it was a property of the two instruments that
happened to be written first.

### The obvious probe reports `match` against a function that strips nothing

`` '`' in strip_markdown('a `x`') `` is `True` for the identity function,
so the specimen carries four **controls** the entry itself recorded as
removed (heading, bullet, ordered item, bold) beside the two code spans.
A surviving control is `unknown` — the probe has stopped isolating the
question, which is the mixture branch one check over.

### The residue already had a name here

The specimen carries a **doubled fence** because `SNAG-DOCS-005` closed
on exactly that distinction in this same module on 2026-08-26: the naive
`` `[^`]+` `` strips the single fence and *leaks* the doubled one. Both
candidate fixes are driven as **real patterns** — the naive gives
`mismatch` naming the leak, the same-length a clean `mismatch`. Dropping
that one line from the specimen breaks **both** fix tests, because it is
the only thing that discriminates them.

### What only a live run could say

The check's first drive reported **five** callers, two of them the
probe's own. Beyond an inflated count that made the "nothing calls it"
limb **unreachable**, since the check guaranteed a non-zero count — a
probe counting itself is `ops_claims` rule 3's pin searching a region
containing its own marker, reached from the other side. It is pinned from
both sides now: the raw walk is asserted to still contain what the filter
removes, so the exclusion cannot be deleted in silence.

The same run refuted the entry: it says "**Both** consumers here" and
there are **three** — `monitor/health_review.py` was written on
2026-08-25, the day *after* the entry was filed.

### A figure that went stale 52 minutes ago, and a wrong duration on it

`67 entries` against a live **69**. `estate.snags` landed in estate-lib
at **17:06:27** today — *after* Session 90's 16:14:24 commit — and counts
the two `### Session NN write-up` headings under `## Fixed Issues` that
the old reader did not.

**The first draft of this section said "stale for at least four
sittings"**, on the strength of driving **today's** reader over four past
commits of this document. That measures the *instrument* and says nothing
about what was published at the time — the exact error this repository
files snags about, made inside the sitting that files them, and caught
only by looking at the commit clock while filing the friction. The old
reader is gone from the box (`estate_service.snags` no longer imports),
so the historical figures cannot be re-checked at all.

Both new rows are `is_open: False`, so the open count never moved and the
figure the board publishes was right throughout. Two test docstrings
corrected, and the friction filed at 8400 as `1feea3c3` — the **second**
attempt. The first (`6ac95fa6`) stated the old reader's count as a
measurement when it is an inference, `estate_service.snags` having gone
with the move, which is the message's own second half. Withdrawn by the
sender and re-filed with the figure labelled.

### `SNAG-TEST-001` opened, offering no diagnosis on purpose

Three guards in `test_snag_claims.py` failed once and have not failed in
fifteen runs since. Both obvious causes are excluded by **reading the
path** rather than by assuming: the probe is pure (fixed anchor, no
database, no unit files — `log_actions.recommend` takes all three of its
inputs as arguments), and no randomising plugin is installed, so
collection order is stable. No third cause is offered. That is the entry.

Five falsifications were driven at the behaviour each detects, and one of
them fires two tests rather than one.
