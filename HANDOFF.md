# Handoff — 2026-08-16

## Next action

Take `SNAG-ESTATE-003` — the five estate surfaces raise once at `warning` and then stay silent while the fault stands, and the session is a repeat-without-`critical` rung in `sysadmin/core/escalation.py` with three callers (the estate judge, `monitor/collation.py` and the service families), not a ladder invented to hold one family.

## This session — Session 52, judge_attention against data

`SNAG-ESTATE-002`'s half that needed nothing from estate-manager. Suite
**1792 passed** (from 1776), ruff and mypy clean, **no migration**, **no
new route**, and nothing the running daemon reads until it is restarted —
this is agent code, so it deploys on the restart already owed.

### The problem, stated as the entry left it

`judge_attention` had never been run against a payload with anything in
it. `GET :8400/api/projects/attention` has answered `{"health": [],
"nudges": []}` on all four occasions anyone has looked — including once
after an overnight scheduled scan of 26 projects with 0 parse failures,
which is the precondition that made the negative result worth recording,
and again today at the start of this sitting. So every rule in that
function was pinned against dict literals **written by the same hand
that wrote the consumer**, which is the strongest evidence available and
is not the same as an observation.

The failure mode that makes it matter: the consumer drops an entry whose
identity key is missing (`if not name: continue`). A producer renaming
`project_name` does not raise, does not log and does not half-work — it
returns `[]`, which is the answer this seam already gives. **Absence of
evidence and evidence of absence are the same string here.**

### How a populated payload was made, since the wire cannot supply one

The producer's own code, driven read-only in its own venv against the
live estate database, with two thresholds forced so live rows qualify:
`effective_threshold` → 101, and `nudges.evaluate(…, default_days=0)`.
Everything else is the estate's — 26 real snapshots through
`latest_snapshot_query`, 26 real manifests through `load_registry`, 5
real streaks through `load_action_streaks`, and `dataclasses.asdict`
over the producer's own `Nudge`, which is the point: the field names are
exactly what an unforced payload would carry. Committed as
`tests/fixtures/estate_projects_attention.json`; the two forced numbers
are visible in the data (`threshold: 101`, `threshold: 0`) rather than
hidden, and no assertion reads them as observations.

### Two defects, and neither rule had to be invented

- **31 rows from one poll** — 26 health breaches and 5 nudges, each its
  own alert row and its own tray `{severity}:{title}` fingerprint. The
  ports family has had `port_breach_max_rows` for exactly this since
  Session 26b-A; this one had nothing. Now `attention_max_rows` (5).
- **A 469-character message.** `alert.message` reaches a notification
  body verbatim, so the daemon was cutting the live next actions at a
  point nobody chose — `SNAG-BRIEF-002`, one domain over, in a repository
  that already owns the marked-cut helper and was not using it here.

### Decisions taken, and what each rejected

- **The two families collapse independently**, on one knob. They have
  separate producers inside the estate (a score against a threshold; a
  streak against a schedule) and fail separately, so collapsing the
  working half because the other broke would hide the half that still
  names its projects. Rejected: one count over both lists, which is
  simpler to write and makes 26 broken health rows swallow 5 real nudges.
- **A roll-up takes the loudest rung it swallows.** Rejected: raising it
  at `DEFAULT_SEVERITY` like the health roll-up. `info` is below
  `tray.notify_min_severity` here, so an escalated `warning` nudge folded
  into an `info` row would have made the fix for noise the reason the one
  entry that had earned a toast never got one. The inverse is pinned too
  — six `info` nudges stay `info`, because volume is not severity.
- **Five, and it is measured rather than chosen.** 26 projects are
  scored, 12 are `archived` and cannot breach at all (threshold 0 against
  a clamped score), leaving 14; the eligible nudge population is 5. So
  five sits just under "every project that could" for both families. The
  recording then lands on **both sides of the cap without being made
  to** — 26 collapses, 5 does not — which is the independence rule as
  data rather than as an argument.
- **The seam is guarded in `tests/test_estate_project_contracts.py`, not
  a new file.** That file already holds the two other 8400 routes and the
  two-half machinery (recorded for CI, live for producer drift). Its live
  half can only assert the envelope here, so the per-entry assertions are
  **pre-staged**: they start running by themselves the first day the
  estate publishes anything, which is also the first day they could catch
  anything. Rejected: an AST sweep over the producer's `nudges.py`, which
  fires sooner and pins another repository's file layout — a red gate
  reporting a fault in a repository that has none, which that file's own
  docstring argues against.
- **A test that fires when the estate fixes its half.**
  `PRODUCER_DROPPED_NUDGE_KEYS` asserts `title`/`message`/`details` are
  *absent* from a published nudge, with a failure message naming the next
  move. The pre-staged-trigger shape rather than a task parked on
  another repository.

### Verified live, because the family has never had a row

Three runs of the whole agent path against the real database in a rolled-
back transaction: raise (1 roll-up + 5 nudges) → hold (dedup, 0 raised) →
resolve (6 closed when the estate goes quiet), **0 rows of residue**.

### Two observations, filed rather than acted on

- The estate's `IdleNudgeConfig.days` has no lower bound, though its
  per-project sibling `idle_nudge_days` is validated `>= 1`. A global
  `days: 0` yields "unchanged for 0 days (nudges after 0)" — the
  `standing_days: 0.0` artefact Session 26b-A found one surface over.
  Noted in `SNAG-ESTATE-002` for the estate; this repository renders the
  producer's numbers faithfully and does not launder them.
- **The ports family has fired since Session 26b-A wrote that it never
  had.** `sysadmin.alerts` holds two `estate_judge` rows, both
  `Estate port … registry breach` raised 2026-08-15 11:21 and both since
  resolved. `judge_audit_findings` has now been exercised live; only
  `projects_invariants`, `audit_invariants` and `queue_invariants` remain
  unexercised by real data.

### Still owed, unchanged by this session

`sudo systemctl restart sysadmin.service` — re-measured at the close:
still PID 1410826, started 2026-08-15 14:32 BST, and
`POST /api/sysadmin/reload` still 404s. This session's code is agent
code, so it is on that restart too. **Do not send a HUP until it has
happened**: the running daemon predates `sysadmin/reload.py`, and
Python's default `SIGHUP` action terminates.
