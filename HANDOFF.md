# Handoff — 2026-08-18

## Next action

Take Session 27's Tier 3 — the log aggregator's LLM narrative — because the objection that has beaten it three sittings running is now spent: Session 66 verified the four shipped-unrun claims, Session 67 deleted the duplicate rows distorting their counts, and Session 68 removed the last structural distortion, so `GET /api/logs/actions` serves 11 distinct things where it served 24 and a narrative built on it would no longer describe one crash six times.

## Sub-session items

**None owed for the deploy — the restart was done in this sitting and
verified.** `sysadmin` restarted at **2026-08-18 06:17:53** (NRestarts
3 → 4), `/health` answers, and `GET /api/logs/actions` serves **11**
recommendations with the mosquitto incident as one row. `alembic current`
reads **012 (head)** — checked, not assumed — so no migration was
pending.

**One correction to the recorded restart method, because the first
attempt failed.** `systemctl kill -s TERM sysadmin` needs polkit
authorisation and times out in a non-interactive shell. The raw signal
does not, because `sysadmin.service` is a system unit running
`User=gaddi` and the owner may signal their own process — the same fact
`sysadmin/reload.py`'s docstring relies on for SIGHUP:

```
kill -TERM "$(systemctl show sysadmin --property=MainPID --value)"
```

**The two `Estate port … registry breach` rows are still open** — checked
live during this sitting rather than copied forward. Two minutes:

```sql
UPDATE sysadmin.alerts SET resolved = true, resolved_at = now()
 WHERE resolved IS false AND title LIKE 'Estate port %registry breach';
```

`SNAG-ESTATE-010`.

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
