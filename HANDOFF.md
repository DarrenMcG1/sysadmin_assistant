# Handoff — 2026-08-24

## Next action

Take `SNAG-ESTATE-008` and give `scripts/claude-preflight.sh` a block that re-measures the four machine-checkable ops claims this repository keeps carrying forward wrong — `sysadmin-check-schema` for the schema head, the unresolved-alert count, the daemon's `ActiveEnterTimestamp`, and the live route count off `create_app()` — because the previous ranking demoted it for having "no obvious enforcement point" and preflight already runs at the start of every sitting and already prints priorities, just from prose.

## Sub-session items

**None owed.** `sysadmin` was restarted at **2026-08-24 09:58:28** to
serve this sitting's change, `/health` answers, `alembic current` reads
**013 (head)**, and `GET /api/logs/actions` serves **9 rows with 0
colliding titles** where the same route served 7 collisions among 9 one
minute earlier — checked on the route either side of the restart.

**One alert row is open and it is the artefact Session 71 named
correctly.** `Estate scan could not reach sources` (`warning`, 07:54:54)
reports the estate's *stored* scan of 03:32 today, taken inside the
23-hour outage; 8400 answers `200` now. The estate's scan timer is daily,
so the row clears at 03:32 tomorrow with nothing done. Do not reach into
the estate to force a rescan — its scan is its own. `alerts` holds **2**
unresolved rows in total, measured at 10:05.

## This session — Session 72: a row's identity is the fault

**`SNAG-LOG-010` fixed.** `GET /api/logs/actions` served two rows reading
exactly `kernel: 39885 occurrences, unchanged` — same source, same count,
same severity, same kind, two genuinely distinct signatures, because one
kernel retry loop emits both Bluetooth firmware messages at equal volume.

- **`quoted_signature()` on all four title builders**, not just the one
  the entry filed against. `capped_signature()` bounds the signature at
  `SIGNATURE_DETAIL_CHARS` with `truncate_at_word`;
  `log_review._quoted_signature` keeps only its `figure_free` gate and
  borrows cap, marker and quoting.
- **The entry's scope was wrong in both halves.** It filed against
  `noise` and ranked it last on "population is currently zero". Driven
  through the real `recommend()` against the live table: **14 of 21 rows
  collided in five groups** at the 2026-08-12 anchor, and **7 of 9** at
  the live anchor — where the `noise` population genuinely is zero and
  every colliding row is `severity: risk`.
- **12 member signatures per request were sliced mid-word with no
  marker**, one ending `"message": "alert_raised", "service"` — the
  unmarked cut `log_review._quoted_signature`'s own docstring calls
  `SNAG-BRIEF-002` and calls *worse* on a signature, in the module that
  lent it the constant. `SAMPLE_DETAIL_CHARS` names the second bare
  slice, which had been written twice.
- **The noise title no longer claims a direction.** `unchanged` was
  asserted for all four change kinds `_is_noise_candidate` admits, and
  the live pair classifies **`FALLING` — 39,885 this window against
  77,496 last**, contradicted by the row's own `detail`.
- **Nine tests, each falsified against the behaviour it replaces**, and
  one strengthened before it could be: it compared the two modules'
  quoting on a *short* signature, where a slice and a marked cut agree.
- Full suite **2,159 passed**, ruff clean, mypy clean.

## What the sitting found that nobody had written down

**Reading the entry would have confirmed it; running the producer
refuted it.** The defect was filed from one live payload and scoped to
the family that payload happened to show. Every rule in it was correct
about `noise` and wrong about the endpoint.

**A claim in `STATUS.md` was written ahead of the fact and was false when
checked.** It said `SNAG-LOG-008`'s rows "aged out of the 7-day trend
window on 2026-08-24". All 10 were ingested **2026-08-17
14:11:00–14:21:03**, so they leave that window at about **14:11 today** —
and at 09:58 four of them were still producing live titles.
`SNAG-ESTATE-008`, and the first instance of it this repository has
produced about its own dashboard.

**`SNAG-LOG-013` is filed with its own expiry in it.** 9 of 55 signatures
share their capped prefix and one live incident row lists **7 members
identical after capping** — the roll-up naming nothing, one level below
the titles. All nine are `SNAG-LOG-008`'s historic raw-JSON rows, so the
population empties by retention this afternoon and the cause cannot
recur, because the Session 64 declaration unwraps every row written
since. The entry says so, because "population is zero" is exactly what
mis-ranked its parent.

## Next session — ranked

**1. `SNAG-ESTATE-008` — make preflight re-measure the ops claims it
prints.** It has now cost six consecutive sittings: a stale `UPDATE`, a
restart method that needed no `sudo`, and today a retention boundary
asserted three hours before it happens. The previous ranking demoted it
for having "no obvious enforcement point, since these claims live in
prose" — and that is the part that is no longer true. `claude-preflight.sh`
runs at the start of every sitting; the machine-checkable subset is one
command each. Half a day, and it pays every sitting rather than once.

**2. Session 33 — seam drift detection. Blocked, and named as blocked
rather than dropped.** Still the largest genuinely-open roadmap session,
and this sitting is another argument for it: the module's titles were
pinned by one `startswith` that the defect passes intact. It cannot start
here — its second task reads another repository's fixture off the same
disk, and cross-repo concerns have had an owner since 2026-08-13, so the
first move is a **question to estate-manager**, which is a sub-hour
action rather than a session. Rank it first the day it is answered.

**3. `SNAG-LOG-011` — a deleted route still answers `200`.**
`GET /api/logs/summary` returns an empty payload through the `/{source}`
catch-all, so a caller is told "no summaries" where it should be told
"gone". Real and cheap; it loses because it has **no consumer**, so today
it costs nobody anything.

**Lost, and why.** `SNAG-LOG-013` **self-expires at about 14:11 today**
and its cause cannot recur. `SNAG-LOG-008` loses from the other side: the
remedy is a backfill of 10 rows that leave the window today and the table
on 2026-09-16, so the work outlives the data. `SNAG-UNITS-006` still has
an empty population. The **four permanent `running` rows in `agent_runs`**
stay filed rather than ranked — whether `summarise_agent` mistakes one
for liveness is unmeasured, and the measurement *is* the task, so it is
an hour rather than a session.

**Blocked on another repository.** `SNAG-ROADMAP-002` has now published
wrong board movement for **five consecutive sittings** (56 → 57 entries
for a sitting that closed one and opened one) and the parser moved to
estate-manager on 2026-08-13, so what is owed from here is a report, not
a fix. `SNAG-LOG-012` (`strip_markdown` is `estate-lib`'s),
`SNAG-ESTATE-002`, `-004`, `-006`, `-007` remain delegated.
`SNAG-ESTATE-001`'s remaining half is a retirement checklist the entry
says in writing is not this repository's to enforce.
