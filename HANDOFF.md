# Handoff — 2026-08-26

## Next action

Write the fourteenth check for `SNAG-LOG-012`, driving this repository's own `sysadmin/core/text.py` re-export of `strip_markdown` over a narrative carrying inline code spans to show the backticks survive — which makes it the first check that is *pre-staged* against another repository's fix rather than a cross-repo read, since it holds `match` while estate-lib's `estate.text` is unchanged and flips to `mismatch` the day they land it, and it refutes in passing the rule `SNAG-ESTATE-014`'s body states as "delegated entries cannot carry a check", which Session 88's `SNAG-ESTATE-002` check already broke once.

## Session 90 is complete — the thirteenth check, and the field order nobody had looked at

`SNAG-LOG-008` is **checked and stays open**. Open entries unmoved at
**24**, checked **10 → 11**, unchecked **14 → 13**. **2500 tests pass**
(2476 + 24). Ruff clean, mypy clean. The daemon was restarted at
**16:10:00** and `/health` answers 200 — `sysadmin/snag_claims.py` is the
only source edited and nothing under `sysadmin/` imports it, so for the
seventh sitting running nothing a caller can observe moved.

### Reproduced rather than counted, because the calendar would have closed it

The ten rows left the current 7-day window on 2026-08-24, leave
`GET /api/logs/trends` altogether on **2026-08-31** when `previous_start`
passes them, and leave `log_entries` at 30 days' retention on
**2026-09-16**. Today the endpoint serves all ten with `change: gone`,
`current: 0`, `previous: 1`.

The check has **two halves because only one of them can move**. Half 1
drives the real `read_journal` over this daemon's own journal twice in
one process, at `text` and at `json` — 50 of 50 enveloped records come
back shaped differently by the declaration alone. That reproduces the
*cause* and can never refute the entry, since no backfill lands in
`read_journal`. Half 2 pins that `unwrap_json_message` has exactly one
production call site and it is inside `read_journal`, which is where one
would. The call-site half is settled **first**, so a box where journalctl
will not answer still reports a landed backfill rather than an `unknown`
that hides one.

### The entry's open question is answered, and the fear lands on the other side

*"How many of the ten are recoverable is unmeasured"* — **10 of 10**,
stored lines 1396–1651 characters against a 2000 cap. The truncation the
entry feared is real and present in the same source: `sysadmin.service`
holds exactly **10 rows truncated at 2000**, and the intersection with
the ten is **zero** — those are the `SNAG-DB-005` lifespan tracebacks,
already unwrapped correctly. Recorded as a property of that ten-minute
window rather than a law, because a traceback arriving inside it would
have been both unrecoverable and in need of the backfill.

### What only a live run could say

The check's first draft paired the two reads on `raw_line` and argued for
it from the code under test — `unwrap_json_message`'s rule 3 promises
that field is kept **verbatim** — and it paired **0 of 50**.
`journalctl -o json` does not emit a record's fields in a fixed order, so
one record read twice is two byte-different lines that parse to the
identical dict. A content guarantee read as an identity guarantee.

**That is the backfill's problem too**, and it explains a case the entry
had only named: the same field order decides whether `__CURSOR` falls
inside the 2000-character cap, which is the mosquitto case. Checked for a
live consequence and there is none — `raw_line` is written and stored and
never used as a key.

### Also this sitting

`alfred-frontend unreachable` — a `critical` open since 2026-08-25
10:45:52 — resolved by itself at **15:37:41**, so the opening block's
alert count is corrected 2 → 1 rather than left asking about a row that
closed itself. That is `ops_claims.py` rule 5's founding case again.

Five falsifications were driven at the behaviour each detects, plus a
sixth for the *mixture* branch, which is `unknown` rather than a partial
match because the tempting reading is that most records diverged so the
mechanism holds.
