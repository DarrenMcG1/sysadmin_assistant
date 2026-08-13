# Handoff — 2026-08-13

## Next action

Restart `sysadmin.service` (a **system** unit — `sudo systemctl restart sysadmin.service`, not `--user`) to deploy Sessions 43 and 44 together, then confirm three things in one pass: the journal carries `schema_revision_verified` at revision 011 rather than a refusal, the 60 open `sysadmin-organiser-timer critical` rows resolve themselves as a deconfigured service, and `agent_runs.details->'collation'` reads `mismatched: 8` on the first run.

## This session

Session 44 landed `SNAG-DB-002`'s **check** half as `63ed848`. The
`REINDEX` half is open, stays open and stays manual.

**The deploy step from the last handoff did not happen** — `sudo` needs a
password this session cannot supply. It is still the next action, and it
now carries two sessions rather than one.

### The daemon is running code from before the estate cutover, and it is costing something

`sysadmin.service` has been up since 2026-08-12 19:16, which is before
`7467d2c`. It loaded `services.yaml` at that moment, and that file still
declared `sysadmin-organiser.timer`. The cutover replaced that entry with
the estate's two timers; the running process never saw the change, so it
has been checking a unit `systemctl` reports as `LoadState: not-found`
and raising a `critical` every five minutes. **60 unresolved rows between
07:41 and 12:36 today.**

The restart cleans up after itself, and the mechanism is worth knowing.
On restart `sysadmin-organiser-timer` is a **deconfigured** service: it
is in neither `_raised_titles` nor `unhealthy`, because it is not in the
loop at all. So all 60 rows fall through `_resolve_recovered`'s inverse
question and close in one statement — SNAG-AGENT-004's pattern-based
population handling a fault created after it shipped. Nothing needs to be
done by hand; it is worth *watching* happen, because it is the cheapest
confirmation available that the fix works on the case it was designed for.

### The snag's own count was wrong, and the shape of the error is the finding

`SNAG-DB-002` records three stale databases. There are **eight of
eleven**: the five `alfred*` copies, `postgres`, `projects` and
`template1`. Three is how many databases someone had opened a `psql`
session against — the warning is printed per connection, so reading the
symptom samples wherever the hand happened to be. `pg_database` is a
cluster-wide catalog and one query from the existing connection answers
for the whole box.

`estate`, `estate_test` and `venture` are clean at 2.44. That is not luck
and it is the useful half: they were created after the upgrade, which
proves `CREATE DATABASE` stamps the **current** OS version rather than
inheriting the template's. So `template1` sitting at 2.43 is not a trap
for future databases, only for its own indexes.

### Decisions taken, with the rejected option and why

- **The check fails _open_ on NULL** — deliberately the reverse of
  `schema_guard`, which was written three days ago and fails closed on
  every way of not-knowing. `template0` records no version, and a
  `C`-locale database has no actual version to compare against. Rejected:
  `recorded != actual` in Python, and `IS DISTINCT FROM` in SQL, both of
  which report `2.43` against `NULL` as a fault and invent an alert whose
  remedy does not exist. The two rules are not in conflict: the guard
  fails closed because serving against the wrong schema is worse than not
  serving, and here a false positive is an operator asked to reindex a
  16 GB database that is fine.
- **One row per database, and the list is not filtered.** Rejected: a
  cluster-wide single row (the remedy names one database, and one row
  stays open until the last of eight is done, saying nothing in between),
  and an allowlist of "databases that matter" (five of the eight are
  Alfred's dev and test copies, but deciding which matter needs a second
  registry of estate facts living here — the duplication estate-manager
  exists to remove, and a test database is where a wrong-ordering bug is
  cheapest to find).
- **Raised once per open row, never once per run.** Rejected: the
  `_check_thresholds` pattern, which was the natural thing to copy. At
  300-second polling against a fault that persists until someone
  reindexes, eight databases cost **2,304 rows a day**.
- **The remedy is not automated.** `REINDEX DATABASE` on eight
  databases, two of them another application's, one of them 16 GB, wants
  a quiet window and a human — the same judgement the snag took, kept.

### The thing this session learned that the codebase did not say

**Dedup and `RESOLVABLE_TITLE_PATTERNS` are mutually exclusive.** That
sweep closes every owned row the run did not re-raise, which is sound
*only* for a family that re-raises every run — which is exactly why
`_check_thresholds` can be in the tuple. Adding a deduplicating family to
it makes its row flip-flop: resolved on the run that holds, re-raised on
the next. And because the tray fingerprints on `{severity}:{title}`, each
flip clears the suppression and notifies again — **a pile-up that also
reads as recovery**, which is worse than either alone.

It is now written against `RESOLVABLE_TITLE_PATTERNS`, in
`collation.py`'s rule 4, and pinned by
`tests/test_collation_check.py::TestTitleIsNotSweptByTheServiceResolve`,
which emulates SQL `LIKE` against every pattern in the tuple. The
database name sits last in the title so the collision is impossible by
construction rather than avoided by luck.

### Found on the way, filed rather than fixed

`SNAG-AGENT-006` — the raise-side twin of `SNAG-AGENT-004`. The service
and threshold families still call `raise_alert` unconditionally, so a
sustained fault writes one row per run: the 60 above, plus
`venture-chat unreachable` at 85 rows across 36 hours. Session 41 fixed
the *resolve*, which bounds the leak at retention where it used to be
immortal; it did not touch the *raise*, which is what produced
`redis unreachable`'s 6,283 rows one poll at a time.

**P2 rather than P1, and the reason is measured**: the tray does not
re-notify, because it fingerprints on `{severity}:{title}`, so 60 rows
produce one toast. The cost is that `GET /api/sysadmin/alerts` and every
count on `resolved = false` read sixty times high.

**Not fixed here because both halves must move together** — adding dedup
without removing those families from `RESOLVABLE_TITLE_PATTERNS`
reintroduces the flip-flop above, on the families that carry `critical`.
`collation.py` is the worked example of the pattern to copy.

### What is verified, and what is not

Both halves were exercised against the **live** database inside
transactions that were rolled back, following Session 43's practice:

```
run 1: raised=8    exactly the 8 stale databases, all `warning`
run 2: raised=0    mismatched=8, still open, no duplicate rows
narrowed as if 2 reindexed and 1 dropped:
       raised=0    resolved=3 — exactly alfred_e2e, alfred_test_cc,
                   template1; the other 5 left open
residue after rollback: 0 rows
```

**Unproven: the tray toast**, the same gap Session 43 left. Forcing it
means committing a synthetic alert row to the live table, which is the
pollution three previous sessions spent their time clearing. The path is
shared with every other `warning` family and unchanged.

## Open, in order

1. **The restart above**, which is now the prerequisite for everything —
   nothing from Sessions 43 or 44 is live until it happens.
2. **`SNAG-AGENT-006`** (new) — the raise-side pile-up. Both halves move
   together; see above.
3. **The judging session** — wire `GET :8400/api/projects/invariants` and
   `/attention` into checks and alerts. Both endpoints answer 200 today.
   **Until this runs, idle nudges reach no tray toast**: the estate
   computes them and nothing here reads them.
4. **`SNAG-ESTATE-001`** — looks already resolved; verify and close
   rather than work.
5. **`SNAG-TRAY-006`** — a consumer-driven contract test against the 8400
   producer, *not* a shared class in estate-lib.
6. **`SNAG-DB-003`**, **`SNAG-SYSD-003`**, and the fourth
   `SNAG-DB-001` item (a live-database test path for the shared snapshot
   query) remain as the previous handoff left them.

## State at close

Working tree clean at `63ed848`. All three gates green and checked
directly rather than reported: `uv run pytest` **1455 passed** (1422 +
33 new), `uv run ruff check .` clean, `uv run mypy sysadmin` clean across
76 source files. `./scripts/lint_check.sh` clean. **Not yet deployed** —
the daemon serves start-time code from 2026-08-12 19:16.
