# Handoff — 2026-08-24

## Next action

Take `SNAG-DB-005` — make an unapplied Alembic migration impossible to leave unapplied — because a migration written and never applied took `sysadmin.service` down for 23 hours between 2026-08-23 08:39 and 2026-08-24 07:55, `schema_guard` correctly refused to serve and nothing on this box applies migrations, so the next sitting that writes one reproduces the outage exactly.

## Sub-session items

**None owed for the deploy.** The migration is applied (`alembic current`
reads **013**), the daemon is **active** and `/health` answers, and every
new surface was driven live: `GET /api/logs/review` → 200 with a stored
review, `POST /api/logs/review/generate` produced it against the real
llama-server, and `/api/sysadmin/briefing/preview` serves five sections
including **Weekly Log Review**.

**The restart needed two commands and neither needed `sudo`**, which
corrects last session's note by narrowing it. `systemctl kill` needs
polkit; `reset-failed` and `start` do not, because `sysadmin.service` is
a system unit running `User=gaddi`:

```
systemctl reset-failed sysadmin && systemctl start sysadmin
```

`kill -TERM "$(systemctl show sysadmin --property=MainPID --value)"` is
still the right verb for a *running* daemon. It is the wrong one here —
the unit was already `failed` with `start-limit-hit`, so TERM had nothing
to signal and systemd would not have restarted it anyway.

**The two `Estate port … registry breach` rows are still open and are now
`info`** — re-raised 2026-08-17 20:04, below
`tray.notify_min_severity`, so they are silent. Closing them is tidiness,
not noise removal. Two minutes:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

`SNAG-ESTATE-010`.

## This session — Session 69: the weekly log review

**Session 27 is complete.** Tier 3 is `sysadmin/monitor/log_review.py`,
`GET /api/logs/review`, `POST /api/logs/review/generate`, a Monday 05:15
job, a "Weekly Log Review" briefing section and a `log_reviews` table
(migration 013). First review stored, `llm_used: true`,
`confidence: medium`, ten input keys in `stats`, **zero figures from the
model**.

**2101 tests green** (+34), ruff and mypy clean.

## What the sitting found that nobody had written down

- **The row describing this tier was false.** It said the overnight LLM
  summary "already runs in the briefing — extend rather than duplicate".
  `LogAggregatorAgent.summarise()` had **no caller anywhere**;
  `log_summaries` held **one row**, dated 2026-07-24; the 12-hour
  freshness window meant the section had been absent from every briefing
  for **25 days**. `summarise_with_llm: true` was parsed by pydantic and
  read only by the uncalled method — `SNAG-CFG-001`'s shape.
- **That row is also the argument against extending it.** It covered
  **29 seconds** (13:16:47 → 13:17:16), reported
  `entry_count = error_count = 100` — both the query's own `LIMIT` — and
  answered a hundred raw timestamped lines with "1. Repeated failures 2.
  Pattern of failures" plus the invented rate "every 1-2 seconds". There
  is no edit that makes that a Tier 3: the direction of flow *is* the
  design.
- **Rule 3, which the other two Tier 3s could not have found.** The
  normalised signature may go into the prompt verbatim, because
  normalisation is the operation that makes it figure-free —
  `signature()` maps every digit run to `N`, and **0 of 46 live
  signatures contain a digit**. `_HEX` produces `0xN`, whose `0` is a
  digit by construction, so it is still filtered: an empty population
  today, reachable the moment a driver logs an address.
- **`direction_phrase` is asymmetric and that is the new rule.**
  Truncation only ever lowers a count, so a *rise* is trustworthy at any
  confidence and a *fall* is not. Session 63 used one-directionality to
  justify a threshold on the input; this decides what the narrative may
  claim on the way out.
- **A case-only edit of equal length is invisible to Python's bytecode
  cache.** `"Outstanding faults"` → `"OUTSTANDING FAULTS"` is the same 18
  bytes; landing in the same mtime second, the `.pyc` was reused and a
  falsification appeared to pass while the source said otherwise. Cost
  about fifteen minutes of chasing a contradiction between `grep` and the
  interpreter.

## What was decided against

**`log_summaries` is frozen, not dropped.** ADR-0005's treatment of
`project_snapshots` and `project_reviews`: nothing writes it, its
retention row still thins it, and dropping all three together is one
follow-up migration. A table is destroyed once.

**The migration interpolates its retention constant rather than binding
it.** Alembic's offline mode ignores the parameters dict, so migration
011 renders as `VALUES ('disk_reviews', NULL)` under
`alembic upgrade --sql` — a policy row with a NULL window, which
`run_retention` reads as no purge at all. Caught by previewing the SQL
before applying it. Not fixed in 011, because that migration has already
run correctly online and rewriting applied history is worse than the
inconsistency.

**No fix for `strip_markdown`.** It lives in `estate-lib`
(`~/projects/estate-manager/lib/estate/text.py`), so patching it here
would be the copy that drifts — the exact failure that module's own
comment records. Filed as `SNAG-LOG-012` and routed to the owner as a
recommendation.

## Next session — the ranking, and why the runners-up lost

1. **`SNAG-DB-005` — nothing applies migrations.** Wins on
   **recurrence**, not severity: it has already cost 23 hours of
   monitoring, and every future sitting that writes a migration
   reproduces it. This sitting's own migration would have done so again
   had the restart not been attempted for an unrelated reason. The design
   question is real rather than mechanical — a postflight check is cheap
   and honest, an `ExecStartPre=` needs `sudo`, and an `ExecStartPre` that
   *applies* rather than compares must be refused, because applying a
   migration unattended at boot is how a bad one reaches production with
   nobody watching.
2. **`SNAG-LOG-009` — every emitted `journalctl` command is an hour
   out.** Risen one place because Tier 3 is done, and it now affects the
   **fallback narrative** too, which quotes the same commands. Still
   loses on *consequence*: in BST the error widens the read, so nothing
   is missed here. First-ranked the day this code runs west of
   Greenwich.
3. **`SNAG-LOG-010` — two identical `noise` titles.** New today, and it
   loses on **population**: both eligible kernel signatures went `GONE`
   on 2026-08-24 as the Bluetooth storm ended, so the endpoint serves no
   `noise` rows and a fix could not be verified against anything. It is
   `SNAG-AGENT-005`'s own rule left unapplied one module over.

**`SNAG-LOG-008` expired rather than being fixed.** Its rows'
`logged_at` is 2026-08-17 and the 7-day window reached them today —
which Session 68 predicted to the day. Not closed: the underlying fact
recurs the next time this daemon logs an error. Session 69 bounded the
consequence, capping the signature at `SIGNATURE_DETAIL_CHARS` where it
reaches a prompt.

**Blocked or waiting on another repository.** `SNAG-LOG-012` is new and
**delegated**. `SNAG-ESTATE-002` and `SNAG-ESTATE-004` are
estate-manager's; `SNAG-ESTATE-006` and `SNAG-ESTATE-007` are delegated.
`SNAG-ESTATE-001`'s remaining half is a retirement checklist the entry
says in writing is not this repository's to enforce. `SNAG-LOG-006` and
`SNAG-UNITS-006` both still have a **population of zero**.

---

# Previous — Session 68

## This session — Session 68: one incident, one recommendation

`SNAG-LOG-001` is **fixed**. First sightings are one incident when they
share a unit **or a declared systemd dependency** inside
`INCIDENT_WINDOW_SECONDS`. Live: `GET /api/logs/actions` **24 → 11**, and
the 2026-08-12 mosquitto core dump is one row naming all six signatures
and emitting one `journalctl -u … -u …` that was run and works.

**The measurement the session existed to make came out cheaper than the
question assumed.** It was framed as declared-versus-effective graph,
with `scan.py`'s no-subprocess promise at risk. The real question was
*which directories*: `mosquitto.service` is packaged and its file lives
in `/usr/lib/systemd/system`, which the sweep never walks — so the
obvious move was to widen the walk. **Parsing `/usr/lib` reads 629
further unit files and yields zero further relations** among the fourteen
declared log sources, because a relation is declared by the unit that
*depends* and here that unit is always the hand-written one.

**The graph is the filter and the clock only bounds it.**
`alfred-backend.service` failed **1.2036 s** after the crash — inside any
usable window — because PostgreSQL was still starting up, and it is a
*user* unit against mosquitto's *system* one, so systemd could not order
them even if someone declared it. Driven as a counterfactual: forging one
edge admits it, removing the graph reproduces the entry's own proposal.

`INCIDENT_WINDOW_SECONDS = 5.0` is derived from a **gap** rather than
picked — every genuinely-one-incident pair is inside 349 ms, the nearest
genuinely-two-incidents pair is 64.4 s away, so every value between gives
identical output.

**2067 tests green** (+36), ruff and mypy clean. Ten guards falsified
deliberately; each broke exactly the tests written for it.

## What the specimen refuted beyond the rule

- **The entry's mechanism was backwards.** systemd started the oneshot
  **2 ms after** mosquitto had already failed, because the relation is
  `Wants=`, which does not propagate failure. The provisioner then failed
  on its own connect. One causal incident either way — but the mechanism
  written down was not the mechanism.
- **The whole window is a boot**, beginning twelve seconds earlier.
  Three sittings had looked at these rows and none had noticed, and it is
  exactly why a same-window rule is dangerous here.
- **A fixture of this session's own walked into `log_signature`'s trap.**
  `line 0/1/2` normalise to one signature, so the first anti-single-linkage
  test passed for the wrong reason. Caught by running it, not by reading it.

## What was decided against

**No timezone fix** (`SNAG-LOG-009`). Every emitted `journalctl --since`
is an hour early here — found by *running* the command the new row emits.
It is one `astimezone()`, but every existing `TestJournalCommand`
assertion pins the current rendering, so it changes what the tests call
correct rather than what sits underneath them. It is also latent here:
BST widens the read, so nothing is missed.

**No drop-in reading** (`SNAG-UNITS-006`). `discover_units` skips
`*.service.d/`, so `restart_bounded` and now `declared_relations` share
one blind spot. Fixing it changes the sweep that feeds the orphan
classification and two alert families, on the strength of a
log-correlation session, with **zero** of the 38 units the sweep sees
having a drop-in to verify against.

**`SNAG-LOG-008` not closed**, though the rule collapses its ten rows to
three. That entry is about the signatures being unreadable, not about how
many rows they occupy.

## Next session — the ranking, and why the runners-up lost

1. **Session 27 Tier 3 — the LLM narrative.** Wins because its standing
   objection has expired. It lost three sittings running to "the stack
   beneath it has not been observed"; that stack has now been verified
   (66), cleaned (67) and de-duplicated of meaning (68). It is also the
   last unbuilt tier in the area, so finishing it closes the session
   rather than extending it.
2. **`SNAG-LOG-009` — the hour-out `journalctl` commands.** Real, cheap,
   affects **9 of the 11** rows the endpoint serves. Loses on
   *consequence*: in BST the error widens the read, so nothing is missed
   on this box. It becomes first-ranked the day this code runs west of
   Greenwich, where the same arithmetic points five hours late and
   returns nothing.
3. **`SNAG-LOG-008` — the ten raw-JSON signatures.** Loses by more than
   last sitting. Session 68 took them from 10 rows to 3 without touching
   the data, and their `logged_at` is 2026-08-17, so the 7-day window
   drops them by **2026-08-24** whatever anyone does. Shrinking *and*
   expiring ranks below both of the above.

**Blocked or waiting on another repository.** `SNAG-ESTATE-002` and
`SNAG-ESTATE-004` are estate-manager's; `SNAG-ESTATE-006` and
`SNAG-ESTATE-007` are delegated. `SNAG-ESTATE-001`'s remaining half is a
retirement checklist the entry says in writing is not this repository's
to enforce. `SNAG-LOG-006` and `SNAG-UNITS-006` both have a **population
of zero** — neither can be verified until something on this box produces
a case.
