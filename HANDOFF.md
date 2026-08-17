# Handoff — 2026-08-17

## Next action

Take `SNAG-LOG-001` — the correlation rule that would collapse one crash's systemd narration into a single recommendation — because the purge has left the cleanest specimen this box has ever offered and it refutes the entry's own proposal: six of the twenty-four recommendations now served are one causal incident spanning two units inside 349 milliseconds, so the "same unit, same window" rule the entry proposes would collapse four of them and leave the other two standing as a phantom second fault.

## Sub-session items

**None owed.** No code changed, no restart is needed, no migration is
pending. The daemon is running the current commit and the purge was a
`DELETE` against data it re-reads on every poll.

The backup is at
`~/projects/.backups/sysadmin_assistant-data/`, with a README carrying the
restore SQL. The restore path was **run and rolled back**, not merely
written down: re-inserting the CSV gives back 626,976 rows and all 339
duplicate groups.

## This session — Session 67: the purge

Session 66's fix stopped new duplicates and deleted none of the old ones.
This sitting deleted them and measured both endpoints either side.

**497 rows deleted**, 626,976 → 626,479, duplicate groups 339 → **0**,
2,031 tests still green, no code changed.

**The identity had to be proved first, and the obvious evidence pointed the
wrong way.** `raw_line` differs in **all 339** groups, which reads as proof
they are distinct journal entries. It is journalctl's JSON key ordering
varying between reads. Settled against journald's own identity instead:
**338 of 339 groups carry exactly one distinct `__CURSOR`, and none carries
more than one.** The 339th is the mosquitto coredump, whose `raw_line` is
truncated at 2000 characters so the cursor fell off the end — its three
`ingested_at` stamps are the three restarts, the same evidence by another
route.

Two rules the purge needed that were not in the filed plan:

1. **The purge key must be the fix's key.** `(source, logged_at, message)`
   is what `_is_unstored()` uses to decide an entry is already stored, so
   the surviving table holds no shape the running code refuses to
   re-create. The plan's *tie-break* was wrong: it said "keep the earliest
   `id`", and `UUIDPrimaryKeyMixin` is `uuid.uuid4`, so ordering by `id` is
   arbitrary and would have kept a random copy — falsifying when the
   service first observed the entry while leaving `logged_at` correct.
2. **A purge can re-open the defect it is cleaning up after.**
   `_resume_floor()` reads `max(logged_at)` per source and the message set
   at it; deleting the last surviving row there moves the floor backwards
   and the next poll re-reads the window. Asserted 0 inside the
   transaction, and both guards were falsified deliberately — each aborts,
   and the `DELETE` never executes in either falsified run.

**The snag understated its own cost, which is the part worth carrying.** It
said counts were overstated by up to 19×. Four recommendations were
**fabricated rather than inflated**: both `alfred-backend` surges read 21
vs 5 (ratio 4.2) against a genuine **4 vs 5**, and both
`sportsanalyser-frontend` surges read 19 vs 6 (ratio 3.17) against a
genuine **1 vs 3** — a **decline that was being reported as a surge**.
Duplication inverted the direction, which a claim about magnitude cannot
predict. `GET /api/logs/actions` went **28 → 24** at unchanged
`confidence: medium` with no new rows; `GET /api/logs/trends` holds 47
signatures, `truncated: false`.

Worst surviving inflation: `estate-broker-provision` **18 → 1**, `kernel`
"failed to reset" **17 → 1**, `estate-manager-api` **23 → 11**,
`venture-assistant-backend` surge **48 → 27**, the mosquitto coredump
**3 → 1**. The two `noise` rows moved 39,922 → **39,885** — so the family
this month's work unblocked was the least distorted of the lot.

**The aggregator was confirmed alive before "no duplicates re-created" was
written down**: 91 completed `log_aggregator` runs since the restart, and
0 rows stored since 20:06:38. A dead agent produces the same zero.

## What was decided against

**No backfill of the ten raw-JSON rows**, though they were found in the
same breath — `SNAG-LOG-008`. It is a *second* data migration, and putting
an unrehearsed `UPDATE` behind a rehearsed `DELETE` in one sitting is how
the rehearsal stops meaning anything.

**No purge script committed to `scripts/`.** It is a one-off keyed to one
day's row counts, and a script in `scripts/` reads as something to run
again. The SQL, its guards and the restore path are in the backup README
where the data is.

## Open, and named rather than dropped

- **`SNAG-LOG-008`** — ten `sysadmin.service` signatures frozen as raw
  JSON. They are **10 of the 24** recommendations the endpoint now serves,
  which is the largest single share of it, but they **self-clear**: the
  trend window is 7 days and their `logged_at` is today. Doing nothing
  fixes this in a week; a backfill fixes it now and may not fully succeed,
  since `raw_line` is truncated at 2000 characters and how many of the ten
  are recoverable is unmeasured.
- **`SNAG-LOG-001`** does not self-clear, which is why it ranks above the
  larger share. It is structural and recurs on every multi-line crash.
- **The four permanent `running` rows are answered and closed** —
  measured while ranking, not as a session. `summarise_agent` reads
  `started_at` regardless of status and `_failure_streak` skips `running`
  rows deliberately, so they mask neither liveness nor a failure streak.

## Next session — the ranking, and why the runners-up lost

1. **`SNAG-LOG-001`, the correlation rule.** It wins on *durability*, not
   size: **6 of 24** recommendations today, and it returns on every
   multi-line crash for ever. The purge produced the specimen to measure a
   rule against — six rows, one occurrence each, no duplicate inflation
   confusing the counts — and the specimen **refutes the entry's own
   proposal**. All six fall inside 349 ms but span *two* units: mosquitto
   core-dumped and took the `estate-broker-provision` oneshot with it, so
   a "same unit, same window" rule collapses four and leaves two standing
   as a phantom second fault. The relation is systemd's dependency graph,
   and **nothing here reads it** — checked, not assumed: `scan.py` parses
   `Restart=`, `RestartSec=`, `ExecStart`, `WorkingDirectory` and
   `[Install]`, and no `Requires=`/`After=` anywhere. The declared graph is
   cheap (same files the sweep already opens); the effective graph costs
   the no-subprocess promise. Measuring which one suffices is the session.
2. **`SNAG-LOG-008`, the backfill.** Loses despite the larger share
   (10 of 24) because it is **time-boxed and self-clearing** — seven days
   and it is gone from the actions endpoint whatever anyone does — and
   because its feasibility is unmeasured: the source data is a
   2000-character truncation. Spending a sitting on something that expires
   by itself, and might only half-work, ranks below a defect that is
   permanent.
3. **`SNAG-UNITS-002`, the fifteen units that cannot reach `failed`.**
   Larger and genuinely open, but dormant — it costs nothing today, and it
   was deliberately not shipped as fifteen alert rows for a stated reason
   that has not changed. It loses to two items that are actively
   distorting a live endpoint.
