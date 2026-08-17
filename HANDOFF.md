# Handoff — 2026-08-17

## Next action

Take `SNAG-LOG-003` and add a per-source `format: json` declaration to `services.yaml` so `read_journal` parses this daemon's own lines out of their JSON envelope, because the 14:10:58 restart made Session 61's priority half live and `log_entries` now holds real `warning` rows for `sysadmin.service` whose `MESSAGE` is the whole JSON document — so `alert_title` builds a 252-character title out of JSON that reaches a notification body verbatim, and this is the first sitting at which the fix can be tested against real rows rather than a reconstruction.

## One sub-session item, and the restart is no longer owed

**The restart happened at 14:10:58**, after Session 62's commit at
14:09:16, so all of Sessions 60/61/62 are live. Verified rather than
assumed: `log_entries` holds **10 `warning` rows for `sysadmin.service`**
since 14:11, against 0 across the previous nine nights, and the first
post-restart journal poll (14:12:00) truncated **nothing** where the
13:17:05 restart's poll truncated four sources.

**Still outstanding, still two minutes.** The two `Estate port … registry
breach` rows still need resolving so Session 57's `info` rung can reach
them (`SNAG-ESTATE-010`) — both confirmed still open at 14:20:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

`SNAG-DB-004`'s fix went live with the same restart, so **tonight's 03:00
is the first purge that will delete anything** since 2026-08-08, and it
happens by itself.

## This session — Session 63: the change was right and its stated reason was not

The handoff's `## Next action` line named proportional confidence and it
was the right change. **It was wrong about the mechanism**, and measuring
that before writing the gate is what turned a permitted change into a
safe one.

`log_trends._confidence` was `if coverage.runs_truncated > 0: return
LOW` — binary, so one catch-up read pinned the whole report for fourteen
days and `GET /api/logs/actions` served **zero** `noise` rows against two
signatures at 39,921 occurrences apiece. It now gates on
`truncated_fraction > TRUNCATION_LOW_FRACTION` (0.05) over the
**instrumented** reads. Driven against the live database after the
change: confidence **`medium`**, **25 recommendations including the 2
`noise` rows** — the falsification the sitting was set up around.

### Three things the measurement corrected

**`_resume_floor()` does not size the catch-up read by daemon downtime.**
It returns the newest stored `logged_at` **for that unit**, so it sizes
by *how long since that source last stored a row* — days for a quiet
source, against the two seconds a `systemctl restart` takes. That is why
16 of the 120 truncations each name **four or five sources at once**:
every one of them is the first `log_aggregator` poll after a restart,
~62 s after `Started SysAdmin…`. A source logging one warning a week is
read a week back on every restart.

**So Session 62's `-p` does reach the catch-up read**, against that
session's own expectation that no ceiling could. With `-p` the 500-entry
budget is spent on *storable* entries, and a week-long window on a quiet
source holds about one. Proof on the same box within one hour: the
13:17:05 restart's poll truncated 4 sources; the 14:10:58 restart's poll
truncated nothing. The population this gate was written for is therefore
smaller than either the entry or the handoff supposed — what the gate
now does is stop the *history* of it suppressing the family for a
fortnight.

**The denominator was wrong.** `_trend_coverage` counted the numerator
over runs carrying `details['truncated_sources']` and the denominator
over every run in the window. That field first appears 2026-08-12 17:31,
so 10,724 of the window's 17,730 runs could not have reported truncation:
**120 of 7,006 (1.71 %)**, not 120 of 17,730 (0.68 %). The artefact is
2.5x and self-correcting, which is exactly why it had to be fixed rather
than waited out — a number wrong today and right next week is one nobody
re-checks.

### Why a threshold is legitimate here and is not a lowered gate

The entry forbids lowering the gate "to unblock a demo", and that was
right. What makes this different is that **truncation is
one-directional**: a truncated read *drops* entries, so it can only make
a count too **low**, and a `noise` row argues that a signature is loud —
a floor the missing data cannot undercut. That is rule 4's own `NEW`
asymmetry ("a gap can hide a fault, never invent one") one step further.

What the threshold actually bounds is narrower and worth carrying
forward: a depressed *current* window can move a genuine `SURGED`
signature into the noise-eligible `STEADY` band. Both live rows are
`RETURNED` with `previous = 0`, so no ratio is computed for either and
nothing is distorted today — but that is the failure mode the number
exists for, not volume error.

`HIGH` is deliberately **untouched**: it still means nothing was lost and
nothing was missed. Only the floor beneath it moved, and `MEDIUM` was
already good enough for `_is_noise_candidate`, which only ever tested for
`LOW`.

### What made the guards suspect, and what was done about it

`truncated_fraction` **fails closed** — `schema_guard`'s posture rather
than `collation.py`'s — so a caller reporting truncation with no
`runs_instrumented` gets `1.0` and the binary behaviour back. That is
correct, and it meant **all 1,984 tests passed on the first run after the
change**, because every existing fixture sets no denominator. So the four
new tests were falsified deliberately: setting
`TRUNCATION_LOW_FRACTION = 0.0` restores the binary rule **exactly** —
it is the limit case, not a replacement — and breaks precisely those four
and nothing else.

### Files

- `sysadmin/monitor/log_trends.py` — `TRUNCATION_LOW_FRACTION`,
  `WindowCoverage.runs_instrumented` / `.truncated_fraction`, rewritten
  `_confidence`, rule 3 and the `Confidence` docstring
- `sysadmin/monitor/routers/logs.py` — `_trend_coverage` counts
  instrumented runs via `has_key`; both new fields serialised
- `sysadmin/core/contracts.py` — `LogTrendCoverageInfo` gains both,
  additive and defaulted
- `tests/test_log_trends.py` — five confidence tests; the old binary one
  kept as the not-knowing case
- `tests/test_log_actions.py` — the falsification pinned; the LOW gate
  test re-based on the storm day's real 7.3 %

Full suite **1,984 passed**, ruff clean, mypy clean.

## What was deliberately not done

**The name/unit seam is still open.** `details['truncated_sources']` keys
on the `services.yaml` **name** and `log_entries.source` on the **unit**,
and only `kernel` collides. Untouched because this gate is global by
*run* rather than by source, so it never performs the join — but anything
that later aggregates truncation per source must map first, and
`_log_source_scopes` carries the same warning one function over.

**`LOW_COVERAGE_FRACTION` still guards two branches that both return
`MEDIUM`.** Pre-existing, and collapsing them would leave an exported
constant nothing reads, which is `SNAG-CFG-001`'s shape. Left alone
rather than tidied inside a sitting about a different rule.

## Next session — ranked

1. **`SNAG-LOG-003`**, and it wins because the evidence arrived rather
   than because it grew. It lost the last two sittings on being
   unobservable; the restart made it observable and the rows exist now.
   The honest fix is a per-source `format: json` declaration, so the
   reader honours a *declaration* rather than recognises an application.
2. **Session 27 Tier 3** — extend the overnight LLM log summary. Tier 1
   produces the material it lacks, and as of today the `noise` family has
   rows to summarise for the first time. Loses for the fourth sitting on
   the same margin: additive work against a live gap.
3. **`SNAG-DOCS-002`** — eight project contract models with zero readers,
   four re-exported to the tray. Runner-up for the fifth time, on the
   same grounds: half an hour of deletion plus one decision about the
   tray's public surface.

**Named as blocked rather than dropped**: `SNAG-LOG-001` needs a
correlation rule nobody has measured, and the obvious cap rebuilds
`SNAG-ESTATE-001`'s roll-up defect. `SNAG-ESTATE-002` and
`SNAG-ESTATE-006` remain estate-manager's. `SNAG-ESTATE-009` waits on a
second consumer of `PortAttribution`.
