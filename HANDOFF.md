# Handoff — 2026-08-17

## Next action

Purge the 497 historic surplus rows `SNAG-LOG-007` left in `log_entries` and then re-read `GET /api/logs/trends` and `GET /api/logs/actions`, because the fix stops new duplicates but deletes none of the old ones, and until they go the occurrence counts behind every `noise` and `surge` recommendation this service now serves are overstated by up to 19× for the nine affected signatures.

## Sub-session items

**None owed.** The restart is done, both Session 63 alert rows are
resolved, and the daemon is running the current commit.

Worth carrying, because two documents claimed otherwise: **the restart
needed no `sudo`.** `sysadmin.service` is a system unit running
`User=gaddi` with `Restart=always` and `RestartSec=10`, so
`kill -TERM <MainPID>` is a deploy path the owner can perform —
`systemctl restart` needs `sudo`, a *restart* does not. Two tasks in
`tasks.md` had recorded the blocker as `sudo` and were wrong.

Check `alembic current` against the packaged head **before** any restart.
`schema_guard` refuses to boot on a mismatch, and that is the one failure
a restart can introduce with no warning. It read `012 (head)` here.

## This session — Session 66: the four claims, and the defect underneath them

Sessions 63, 64 and 65 shipped green and unrun. This sitting restarted the
daemon and measured all four. **All four hold**, and the numbers are the
deliverable:

1. **`-p`'s read efficiency.** Reproduced against the real journal on the
   2026-08-12 storm window: **122,531 raw kernel lines carrying 49,012
   storable ones — 40.0 %**, matching the docstring's claim exactly. The
   first catch-up read after each of three restarts truncated **nothing**.
2. **`SNAG-LOG-002`'s gate.** `GET /api/logs/actions` returns
   `confidence: medium` and **2 `noise` rows** — the two Bluetooth
   signatures at **39,921** apiece, precisely the pair Session 63
   predicted — where the family had served zero for its entire life.
3. **`SNAG-LOG-003`'s declaration.** A **700-character** JSON journal line
   became a **46-character** title:
   `Log error: sysadmin.service — agent_run_failed`.
4. **`SNAG-LOG-005`'s `covered_by`.** `severity: info`,
   `details['covered_by']` naming `failures.py`, `noise_reason` `NULL` —
   and it fired on the **first** failure and stayed quiet, which is the
   whole point of the fix.

**Claim 4 was not observable and had to be induced.** The 215 historic
`agent_run_failed` lines are all `PRIORITY=6`, so the reader's `-p 4`
excludes them — Session 64's claim, verified — and `agent_runs` held
**0 failed rows across 48,452 runs**. A temporary `raise` was installed in
`ServiceDiscoveryAgent._execute`, deployed, triggered via
`POST /api/sysadmin/scan-all`, observed, then reverted with
`git checkout` and the daemon restarted on clean code. The manual path was
the right one to use: `SNAG-LOG-006` notes a manual run has no scheduler
listener, so it produced `agent_run_failed` **alone** rather than the
three-signature pile Session 65 counted — the cleanest possible view.

**`SNAG-LOG-007` was found by the verification rather than in it**, which
is `SNAG-LOG-004`'s ordering again. One mosquitto coredump from 2026-08-12
12:32:51 had been raised as a fresh `critical` **three times** — 12:34:15,
14:12:00, 19:50:20 — once per restart, and nothing in the four claims
predicted that. `_resume_floor()` opens the catch-up window at the newest
stored entry; `journalctl --since` is **inclusive** and `since_timestamp`
renders `@<int>`, truncating sub-second precision, so the boundary entry
and everything in its second came back every restart. Live before the fix:
**339 duplicate groups, 497 surplus rows, worst case 19 copies** of one
entry — and every duplicated entry was the newest stored one for its
source, which is the boundary the off-by-one predicts and a pattern no
other cause explains.

**The obvious fix was refused.** Opening at `floor + 1s` trades the
duplicate for a **gap**, and this module chose a cursor over a narrower
window precisely because a gap is the worse failure for a monitor. So the
window stays wide and the boundary is closed against the stored rows:
`_is_unstored` keeps anything strictly newer than the floor, and at the
floor's own microsecond keeps only messages not already stored. The
message is compared and not only the timestamp because the Bluetooth pair
sits **29 µs** apart — close enough to make "one timestamp is one entry"
unsafe rather than untidy.

`STORED_MESSAGE_CHARS` exists so the truncation and the comparison cannot
drift. The row holds `message[:5000]`; comparing the untruncated line
against it would make every long message unequal to itself and re-ingest
on every restart — the defect rebuilt by its own fix. A test pins it, and
that test is one of the three deliberate falsifications.

**Verified as a before/after on the same box**, not against fixtures: the
19:49 restart re-ingested **26 entries reaching back five days**; the
20:03 restart, with the fix, re-ingested **0** and created **0** new
duplicate groups, taking only 6 genuinely-new rows all stamped after the
restart.

## What was decided against

**The 497 surplus rows were not purged.** The fix is preventive; deleting
historic data is a separate, reversible operation nobody has costed, and
widening a verification sitting into a data migration is the wrong call to
make unasked. It is the next action above.

**`failures.py` was not left to raise about an induced fault.** The two
`service_discovery` failures would have tripped its two-consecutive
threshold on the next sysadmin poll, producing a real alert about a fault
that no longer exists and would have sat for up to 24 h (the agent is
daily). The streak was broken by triggering a **successful** run instead
of by editing the table — the agent genuinely works, so proving it is
honest where a `UPDATE` would not be.

## Open, and named rather than dropped

- **The 497 surplus rows** inflate `details['occurrences']` and the trend
  counts by up to 19× for nine signatures. Everything
  `GET /api/logs/actions` currently ranks is computed off them.
- **Four permanent `running` rows in `agent_runs`.** Two from 2026-08-14
  predate this sitting; two `file_organiser` rows were created *by* it, in
  the documented Session 41 way — the organiser's scan outlives a restart.
  Whether `summarise_agent` mistakes a permanent `running` row for
  liveness is **unmeasured**, which is why it is filed rather than
  dismissed.
- **`SNAG-LOG-006` is untouched** and its population is still zero.
