# Handoff — 2026-08-28

## Next action

Fix `SNAG-ESTATE-010`'s surviving rung half — a judgement that gets quieter still cannot move a standing row's severity, and `SNAG-AGENT-009` closed only the blob half on 2026-08-28, so the sitting should read that entry's own check, which enumerates the three shapes a fix can take and refuses to watch the severity column alone.

## Session 116 is complete — the repair reads the column the reader read, not the one the entry named

`SNAG-LOG-008` is **fixed**. Ten `sysadmin.service` rows kept a raw JSON
envelope in `log_entries.message` because they were ingested before the
`format: json` declaration existed and `unwrap_json_message` applies at
*read* time, in `read_journal`, so no later read revisits a stored row.
`sysadmin/monitor/message_backfill.py` and the console script
`sysadmin-backfill-messages` are the repair.

**The instruction was to measure whether retention had already made the
entry moot. It had not, and it was three days away.** All ten rows were
intact, serving as 10 of the 24 `sysadmin.service` signatures on
`GET /api/logs/trends` at `change: gone, current: 0, previous: 1` —
exactly where the entry predicted. They would have left that endpoint on
**2026-08-31** as `previous_start` passed them, and `log_entries` at
retention on **2026-09-16**.

**The entry's proposed derivation was the wrong one, and the cost it
priced in is not on the path.** It asks for `message` to be re-derived
*from* `raw_line`, and files that column's 2000-character truncation as
the reason a backfill "is not free". `read_journal` composes
`message_text(MESSAGE)` **first** and unwraps *that*, so a
`text`-declared row's stored `message` **is** the unwrap's input, and
applying the unwrap to it reproduces the `json` read by construction.
Going through `raw_line` re-implements the reader's own parse. Driven
over the live ten, both derivations agree **10 of 10**.

**Decision taken: `raw_line` gets a different job — the *witness*.**
"Does this look like JSON" cannot separate a frozen envelope from a
correctly-unwrapped message that is itself a JSON document, and acting
on the guess destroys the second. Byte equality against the record's own
`MESSAGE` is exact in both directions. So the truncation the entry
feared lands on the **witness**, which is the weaker half: a row that
cannot be cleared is *refused and reported*, never corrupted.
Re-measured, Session 90's anti-correlation has grown and still holds —
**16** rows now carry a `raw_line` cut at 2000, intersecting the ten at
**zero**. Idempotence is that same witness read again, not a flag: a
repaired row's `message` no longer equals the record's `MESSAGE`.

**Option rejected: a data migration**, which was the obvious shape. An
Alembic revision moves the packaged head for no structural reason, so
the box would then owe `alembic upgrade head` **plus a restart** or
`schema_guard` refuses to boot — `SNAG-DB-005`'s twenty-three hours
bought for ten rows — and it would repair this population once where the
defect is a *class*: it recurs for every source whose declaration
arrives after its rows do. A console script is a dry run unless
`--confirm`, is never scheduled (a test pins that no job plan or agent
reaches it, `check-migrations.sh`'s rule), and keeps "nothing frozen"
apart from "could not measure".

**Live either side of the write**: `GET /api/logs/trends` went **60 → 50**
signatures, `sysadmin.service` **24 → 14**, raw-JSON **10 → 0**,
collapsing to two readable signatures (`alert_raised` ×9, one
`api.auth_token is not set …`) with `logger` recovered for all ten.
`GET /api/logs/actions` is **unmoved at 8** — the ten were
`previous`-only and never produced advice, so the whole live cost sat on
the trends endpoint.

**Applying it exposed something three sittings had not seen, and it is
not this fix's doing.** Two of the ten have a **readable twin**, same
`logged_at` to the microsecond, ingested at **19:50:19** — the restart
that deployed the declaration. The declaration was committed at
**17:53:33** and `SNAG-LOG-007`'s boundary close landed at **20:09:44**,
*nineteen minutes after that restart*, so `_resume_floor` re-admitted its
own inclusive second and both records at `14:21:03` were stored twice.
Invisible before the backfill, because the twins were different
signatures and hid each other. Filed as **`SNAG-LOG-014`** (P4) rather
than hand-deleted: two rows, ageing out 2026-09-16, and deleting rows
from a monitor's own history to correct an off-by-two is worse than the
two.

**`SNAG-LOG-013` is not closed but its live population is empty**, three
weeks early and by the first of the two fixes it names: **9 of 55 → 0 of
50** signatures sharing a capped prefix. Its check still reports *still
holds*, because it reproduces the mechanism on a synthetic specimen
rather than counting live rows — the instance closed, not the class.

**The check retired with the entry and the detector did not.**
`unwrap_is_read_time` and its marker are gone — every member of
`snag_claims.CHECKS` names an *open* entry — and its half 1, the
two-declaration drive against this daemon's own journal, is re-homed as
`tests/test_message_backfill_live.py`. Re-homing it walked into the
entry's own warning a second time: the drive paired the two reads on
`raw_line`, whose field order `journalctl -o json` does not fix, so it
silently compared nothing and **skipped**. It pairs on
`__REALTIME_TIMESTAMP` now and carries a premise test.
`duplicate_ingest_residue` was written for `SNAG-LOG-014` so no open
entry goes unchecked; its witness is the source still having rows,
because that population empties by retention and a check without the
witness reports the entry refuted by the calendar.

**Blocked**: nothing.

**State of the box.** Restarted at **2026-08-28 18:48:23** (PID 3875592
→ 3920712); neither edited module is reachable from `create_app()`, so
nothing functional was owed and the restart was taken because it is
cheaper than a special case in the mtime check. `/health` answers 200,
schema at 018 (head, unmoved — this session added no migration),
`alerts` holds 1 unresolved row (`High VRAM usage on AMD Radeon RX 7900
XTX`, the flapping breach the previous block already named as the least
stable claim). 2832 tests pass (2801 + 53 − 22), ruff and mypy clean,
both claim checks green.
