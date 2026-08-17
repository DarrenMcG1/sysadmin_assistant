# Handoff — 2026-08-17

## Next action

Take the remaining half of `SNAG-LOG-002` and make `log_trends._confidence` proportional rather than binary, because after today's ceiling fix the only truncation left is the post-restart catch-up read — `_resume_floor()` sets the window to how long the daemon was down, so no ceiling can reach it — and a single such read still pins the whole report `LOW` for fourteen days, which is now the one thing standing between the `noise` family and the two live rows it was written to produce.

## Two sub-session items, neither of them a session

**One to run, and it is now owed for two sittings rather than one.**

```bash
sudo systemctl restart sysadmin
```

The daemon started **13:17:05** today, which is after Session 60's
volume half (13:11) and **before** Session 61's priority half (13:34).
So the duplicate access line is already gone — the journal shows JSON
`sysadmin.access` lines with no plain-text twin — and the level prefix
is not: every line is still `PRIORITY=6` and `log_entries` holds **0
rows** for `sysadmin-service`. Session 62's `-p` change is waiting on the
same restart. Two minutes, and it needs `sudo`.

**One still outstanding from yesterday morning.** The two `Estate port …
registry breach` rows still need resolving so Session 57's `info` rung
can reach them (`SNAG-ESTATE-010`) — both confirmed still open today:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

The 03:00 retention purge still has not deleted anything —
`log_entries` reads **626,917** with a floor of 2026-07-09, 39 days
back. `SNAG-DB-004`'s fix is live as of the 13:17 start, so tomorrow's
03:00 is the first run that will act, and it happens by itself.

## This session — Session 62: the plan was refuted before it was written

The handoff's `## Next action` line named per-source confidence. **It was
measured and it produces zero rows**, so the session went elsewhere and
the entry now says so.

Driven through the real `_build_trend_report` → `recommend()` against
the live database: the entire noise-eligible population on this box is
**two kernel signatures at 39,920 apiece**, and kernel carries **103 of
the 120** truncated runs. Per-source confidence gates the only
candidates on the only heavily-truncating source. The eight sources it
liberates have a loudest signature of **54**, against
`NOISE_MIN_OCCURRENCES = 100` — under the gate across the whole 40-day
retained history.

It would also have failed **silently**, on a seam this repository has
already written down one function over.
`agent_runs.details['truncated_sources']` keys on the `services.yaml`
**name** (`alfred`, `sports_analyser`); `log_entries.source` and
`SignatureTrend.source` key on the **unit**
(`alfred-backend.service`). `kernel` is the only string in both, so the
obvious join reads all eight non-kernel sources as untruncated and
kernel as truncated — wrong in both directions, and green.

**The denominator was wrong as well.** `details['truncated_sources']`
first appears on the run at **2026-08-12 17:31**; 33,090 earlier runs
have no such key. It is 120 truncated of **6,974 instrumented** runs,
not 119 of 10,063, and "kernel truncated in only one week" is an
artefact of when the field landed rather than a fact about kernel.

### What was actually wrong

`read_journal` bounded the read with `-n 500` and then applied
`severity_filter` in **Python, over lines the ceiling had already
counted**. Across the 2026-08-12 storm (12:33–19:11): **203,042 raw
kernel lines carrying 81,216 storable ones — 40 %**. Per minute, a
median of **510 raw against a ceiling of 500**, so **208 of 210 storm
minutes truncated**, and the 100 instrumented storm minutes produced
**103 truncated reads — one per poll**, which is the 103 exactly.

Passing `-p` to journalctl makes the same 500 carry 500 storable
entries. Verified against the real journal rather than a fixture: the
stored multiset is **identical** (81,216 either way, compared message by
message), efficiency goes **40 % → 100 %**, and steady kernel polling
drops **510 → 204** lines a minute.

`max_entries_per_read` is **unchanged**, deliberately. Raising it would
have bought the same headroom at 2.5× the memory and left the waste in
place — and it cannot reach the catch-up path at any value.

`max_priority_for` derives the `-p` number from `PRIORITY_MAP` rather
than restating it, the rule `syslog_priority` already follows. The
Python filter **stays** and is still the authority; `-p` bounds the
ceiling, it does not decide what is stored.

### What this leaves

`read_journal` had **no direct tests** — every existing test patches it
out, or asserts `journal_command`, which is the invocation a
recommendation tells a *human* to run. That is how the ceiling came to
bound raw lines for the life of the module. `tests/test_journal.py` is
its first, 14 of them, and the suite is **1,979 passed**, ruff clean,
mypy clean.

`SNAG-LOG-002` stays open on its binary flag, which is the next action
above. `SNAG-LOG-003` (a 252-character JSON title reaching a
notification body) is untouched and becomes visible the moment the
restart lands, but detection is unaffected and it is legibility only.

### Next session, ranked

1. **`SNAG-LOG-002`, proportional confidence.** It wins because today
   changed what it means. The entry says the gate must not be lowered
   "to unblock a demo", and while 99 % of storm minutes were genuinely
   truncating that was right. They are not any more, so a proportional
   gate is no longer papering over missing data — it is recognising that
   the data is now complete except for a bounded, nameable, post-restart
   case. Small, measurable: two noise rows appear or the reasoning was
   wrong.
2. **`SNAG-LOG-003`.** Loses on being legibility-only with detection
   proven unaffected, and because its honest fix is a `format: json`
   declaration per source in `services.yaml` — a change to the reader's
   contract, which is a design question rather than a fix.
3. **`SNAG-LOG-001`.** Loses because it needs a correlation rule nobody
   has measured: one mosquitto crash yields four recommendations because
   systemd narrates it in four genuine signatures, and a cap would hide
   the fourth without saying the four were one thing.
