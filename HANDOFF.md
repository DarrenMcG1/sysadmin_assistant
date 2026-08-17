# Handoff — 2026-08-17

## Next action

Take the volume half of `SNAG-AGENT-008` — stop `sysadmin-service` flooding its own journal read — because 118 truncated runs in the trend window make `GET /api/logs/actions` report `confidence: low` and suppress its entire `noise` recommendation family for every source on the box, so a feature shipped today has an empty population because of a defect in a different component.

## Two sub-session items, neither of them a session

**One to run.** The two `Estate port … registry breach` rows still need
resolving so Session 57's `info` rung can reach them
(`SNAG-ESTATE-010`); unchanged from this morning, still a write to the
live `alerts` table, still left for the owner:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

Worth re-reading that entry first: this session solved the *general*
version of the problem for the log family, and the reasoning is not the
obvious one.

**One that happens by itself.** The retention purge will delete
**207,566 rows** at 03:00 — the first time it has deleted anything since
2026-08-08. `log_entries` drops 626,906 → 451,888. Nothing to do; it is
recorded so a row count read tomorrow is not a surprise.

## This session — Session 59: the tiers, and a purge that was lying

The handoff's own `## Next action` line stood, so Session 27 was taken
as written. It grew a prefix, and the prefix was worth more than it
looked.

### The retention purge had deleted nothing for nine days

Found by asking how far back `log_entries` reaches — a question about
Session 27's window, not an audit. It reaches 2026-07-09, which is 39
days into a declared 30-day retention.

`KEEP_LATEST_PER` used the literal `"true"` for "the whole table is one
entity", building `SELECT DISTINCT ON (true) … ORDER BY true`.
PostgreSQL reads a bare constant in `ORDER BY` as an **ordinal
position**, so this is a parse error rather than a runtime one, and
parenthesising does not help — the parser strips it.

Two things made it survive nine days, and either alone would have been
enough to catch it:

- **The failure was quieter than the success.** `run_retention` was one
  transaction over twelve tables, and each logs its rowcount *before*
  the commit — so the journal carried `deleted: 175018` for
  `log_entries` every night, none of which happened. The one honest
  signal was `last_purged_at` frozen at 2026-08-08, a column nothing
  reads.
- **1,866 green tests could not see it.** `tests/test_retention.py`
  mocked the session, so every statement was asserted as a *string*.
  One test asserted `KEEP_LATEST_PER["project_reviews"] == "true"` — it
  pinned the broken literal exactly. No stronger string assertion could
  have helped; what was wrong was SQL validity.

Fixed with three changes that are only jointly sufficient: `WHOLE_TABLE
= None` as a sentinel taking its own `ORDER BY … LIMIT 1` branch
(removing the construct rather than repairing it), statement
construction extracted to a pure `purge_statement()` so PostgreSQL can
`EXPLAIN` every statement in a test, and **one savepoint per table** —
`SysAdminAgent._execute`'s rule, one domain over — with `last_purged_at`
stamped inside it so a failed table keeps its old stamp and the column
finally means what its name says.

Both new guards were falsified against the restored pre-fix code path
before being trusted; both fail with production's exact message.

### Session 27, and what the live data refuted

Tiers 1 and 2. **Tier 3 is deferred and is now all that remains of
Session 27.**

The decision that shaped everything was measured rather than argued:
**626,906 rows collapse to 44 distinct messages in 91 ms.** That is what
makes it affordable to apply `log_signature.signature()` in Python over
SQL-grouped rows instead of re-implementing normalisation in
`regexp_replace` — a second implementation would drift from the identity
the *alert* family is keyed on, and the trend would name signatures the
`alerts` table has never heard of.

Three rules the live table settled and fixtures could not:

1. **"New" is a first sighting, not `previous == 0`.** One row refutes
   the obvious test: the Bluetooth firmware signature reads
   `current=39,919, previous=0` and has been storming since 2026-07-15.
   It comes out `returned`. The 8 genuinely-new signatures include
   `Bluetooth: hciN: failed to reset (-N)`, a distinct signature a
   source-level key would have masked.
2. **Truncation is the confidence signal; poll count is only the
   proxy.** A missed poll is caught up by the journal cursor, so data is
   lost only when a catch-up read hits `max_entries_per_read`. Counting
   polls would charge a fully-recovered gap as data loss.
3. **Three emitted `journalctl` commands did not work.** `-u kernel`
   (the kernel is not a unit — `read_journal` has always known this, so
   the same fact was stated twice and one was wrong), no `--user` for
   the **7 of 14** sources that are user units, and a `--grep` on the
   normalised signature whose `N` placeholders match no real line. Found
   by running them: 2,170 lines with `--user`, 1 without. The fixtures
   were green throughout.

### Decisions taken, and what was rejected

- **`known_noise` was built, not named.** Tier 2's scoped example said
  "add to known-noise or fix it" and no such mechanism existed — Session
  48's defect in advance. Rejected: making the recommendation anyway.
- **Quietened, never suppressed** (`info`, below
  `tray.notify_min_severity`), per Session 57. Rejected: dropping the
  row, which rebuilds `SNAG-CFG-001`'s shape.
- **Keyed on `(source, signature)`.** `Failed with result 'exit-code'.`
  is logged by six services here; the signature alone would silence a
  genuine failure in five of them.
- **The quietening changes an open row's severity in place**, which
  `SNAG-ESTATE-010` says nothing can do. Session 39's ban is
  **asymmetric**: an escalation must be *heard*, so an in-place bump
  keeps a fingerprint the tray has suppressed; a quietening must be
  *silenced*, and `info:…` is dropped before `_consider` notifies. The
  mechanism that makes escalation fail is what makes this work, so it is
  one-directional by construction. This family cannot wait for a resolve
  — a signature loud enough to declare never goes quiet.
- **Rule 4 was not relaxed to make the demo work.** `confidence: low`
  suppresses every `noise` row on this box today, including both
  Bluetooth signatures, which are Tier 2's headline case. Serving a
  volume argument off a count known to be incomplete is the opposite of
  what the gate is for. Filed as `SNAG-LOG-002` and it is the next
  session.

### Verified live, not only against fixtures

Retention: real statements against the real database inside a rolled-back
transaction — all twelve tables purge, 207,566 rows due, row counts
re-read after rollback unchanged; the keep-latest semantic forced
separately with `cutoff = now()` (4 rows, 3 deleted, survivor is the
newest, both tables). Session 27: both endpoints driven in-process
against the live DB (88 ms / 83 ms, 34 signatures, 8 new, 13
recommendations); the emitted commands executed; the noise loop closed
end to end — endpoint emits YAML → real `LogNoiseEntry` parses it → the
pair matches what the agent keys on → the signature is still counted in
the trend at 39,919. **1937 green** (from 1866), ruff and mypy clean, 46
application routes counted off `create_app()`.

### Filed rather than implied

`SNAG-DB-004` (fixed), `SNAG-AGENT-008` (this daemon cannot see its own
errors — every line is journald `PRIORITY=6`, so nine nights of `ERROR`
raised zero alerts), `SNAG-LOG-001` (one crash, four recommendations),
`SNAG-LOG-002` (the noise family's population is empty because of
`SNAG-AGENT-008`).
