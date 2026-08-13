# Handoff — 2026-08-13

## Next action

Take the judging session — wire `GET :8400/api/projects/invariants` and `GET :8400/api/projects/attention` into checks and alerts here, since both endpoints answer 200 today and until something in this repository reads them the estate's idle nudges reach no tray toast at all.

## This session

Session 44 landed `SNAG-DB-002`'s **check** half as `63ed848`. The
`REINDEX` half is open, stays open and stays manual.

**Sessions 43 and 44 are both deployed and verified in production**, at
`14:22:09` today. Everything below was observed on the running daemon,
not inferred from tests.

### The stale daemon had been costing something, and the restart cleaned it up itself

`sysadmin.service` had been up since 2026-08-12 19:16 — before `7467d2c`
— so it was still serving `services.yaml` as loaded at that moment, which
declared `sysadmin-organiser.timer`. The cutover replaced that entry with
the estate's two timers; the running process never saw it, so it spent
19 hours checking a unit `systemctl` reports as `LoadState: not-found`
and raising a `critical` every five minutes. **81 unresolved rows by the
time it was restarted.**

**All 81 resolved on the first post-restart run, in one statement.** On
restart `sysadmin-organiser-timer` is a **deconfigured** service: it is
in neither `_raised_titles` nor `unhealthy`, because it is not in the
loop at all, so its rows fall straight through `_resolve_recovered`'s
inverse question. That is SNAG-AGENT-004's pattern-based population
handling a fault created *after* it shipped — the cheapest confirmation
available that the fix works on the case it was designed for, and it
cost nothing to obtain.

The board is now clean: **every unresolved `agent='sysadmin'` row is one
of the eight collation alerts**, and nothing else.

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

**Then confirmed in production**, which the rolled-back runs could not
show — these rows are committed and are the live state:

```
14:22:09  restart; schema_revision_verified revision=011 (not a refusal)
          scheduler started with 8 jobs, was 9 — project_organiser_scan
          gone with the cutover, as intended
14:27:11  run 1  details->'collation' = {raised: 8, resolved: 0, mismatched: 8}
                 8 open `warning` rows, one per stale database
                 81 `sysadmin-organiser-timer critical` rows resolved
14:32:11  run 2  details->'collation' = {raised: 0, resolved: 0, mismatched: 8}
                 total collation rows in the table: still 8
```

Run 2 is the one that mattered: under the `_check_thresholds` pattern it
would have written eight more. `mismatched` is the standing number and
`raised` is 0 on every run after the first, which is why both are
reported rather than one.

**Note the sysadmin agent is the only agent with no
`agent_first_run_delay_seconds`** — that knob is for the hours-scale
agents — so its first run is restart + `health_check_interval_seconds`,
i.e. five minutes. Nothing is wrong during that window; it looks like a
dead agent if you go looking too early.

**Still unproven: the tray toast**, the same gap Session 43 left. The
eight rows are `warning`, above `tray.notify_min_severity`, and the path
is shared with every other `warning` family and unchanged — but nobody
watched a toast appear.

## Open, in order

1. **The judging session** — wire `GET :8400/api/projects/invariants` and
   `/attention` into checks and alerts. Both endpoints answer 200 today.
   **Until this runs, idle nudges reach no tray toast**: the estate
   computes them and nothing here reads them. This is the only item on
   the list where a whole capability is dark rather than a defect being
   open, which is why it is first.
2. **`SNAG-AGENT-006`** (new) — the raise-side pile-up. Both halves move
   together; see above. `sysadmin/monitor/collation.py` is the worked
   example and is fresh, so this is cheaper now than it will be later.
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
76 source files. `./scripts/lint_check.sh` clean. **Deployed and verified in
production** at 14:22:09 — the daemon serves Session 44's code, the
schema guard passed at 011, and the collation family has raised its eight
rows and held at eight across two runs.
