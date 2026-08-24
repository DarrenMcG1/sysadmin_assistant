# Handoff — 2026-08-24

## Next action

Take `SNAG-LOG-010` — put the signature into the `noise` recommendation's title, truncated with `truncate_at_word` at `SIGNATURE_DETAIL_CHARS` the way `log_review._quoted_signature` already does it — and do it before **2026-09-11**, because the two kernel signatures that make the pair indistinguishable stop at `logged_at` 2026-08-12 and `log_entries` has a 30-day retention, so that is the last day the fix can be driven through the real trend code against the 451,154 real rows rather than against a fixture.

## Sub-session items

**None owed.** `sysadmin` restarted at **2026-08-24 09:29:28** to serve
this sitting's change, `/health` answers, `alembic current` reads **013
(head)**, and `GET /api/logs/actions` serves all nine rows with `@<epoch>`
commands — checked by running one of them against the real journal, not
by reading the payload.

**The two-minute `UPDATE` that has opened every sitting since 2026-08-16
is finally out of the documents.** `alerts` holds **3** unresolved rows
and **0** matching `Estate port %registry breach`. Session 70's handoff
said this and `STATUS.md`'s block said the opposite in the same
repository on the same day; the query settled it. `SNAG-ESTATE-008`, at
least the fourth instance.

**One row is open and is an artefact, and the last handoff's test for it
was the wrong test.** `Estate scan could not reach sources` (`warning`,
07:54:54) names `services endpoint unreachable: ConnectError` under
`projects_invariants`. That handoff said "if it is still open next
sitting, it is a real finding rather than an artefact" — it is still open
and it is still an artefact. 8400 answers `200` **now**, but the judge
reads the estate's *last stored scan*, and that scan ran at **03:32
today**, inside the 23-hour outage. The estate's scan timer is daily, so
the row clears at 03:32 tomorrow with nothing done. Do not reach into the
estate to force a rescan — its scan is its own.

## This session — Session 71: the window journalctl actually opens

**`SNAG-LOG-009` fixed.** Nine of nine rows carried a UTC-rendered wall
clock into a `--since` journalctl reads as **local**.

- `journal_command` now takes a **`datetime`**, not a rendered string,
  and `journal.since_timestamp` owns the rendering — it has emitted
  `@<epoch>` and stated this exact reason since the module was written.
  The defect was never a missing conversion: three callers were each
  implementing a fact a fourth function already owned.
- `since_timestamp` **refuses a naive datetime**, because `timestamp()`
  reads one as local — the reading being removed — so accepting it would
  rebuild the defect inside its own fix with the right-looking type.
- The prose is **labelled `UTC`**, not converted to local, so the row no
  longer disagrees with its own command; the label agrees with
  `GET /api/logs/trends`, which serialises `first_seen` with a `+00:00`
  offset.
- Four new tests model the **consumer**: `_journalctl_reads` resolves the
  emitted argument the way journalctl does, in London, New York and UTC.
  All four falsified; the truncation-direction one needed `int` →
  `math.ceil` to break.
- 2150 tests green, ruff clean, mypy clean.

## What the sitting found that nobody had written down

**The entry's own proposed remedy was the weaker of two, and it would
have shipped green.** It called the fix "one `astimezone()`". That
renders a *local* wall clock: correct on this box, verifiable, and still
ambiguous — right only while the process writing the command and the
human running it share a zone, and an autumn-fold local time names two
instants. This document has recorded remedies being refuted before; it
has not recorded one that would have passed every check and still been
wrong in winter.

**The tests were what hid it for three sittings.** `TestJournalCommand`
asserted the *rendering* — the exact string — so a command that pointed
at the wrong hour was pinned as correct by the suite that existed to
protect it. Asserting what a thing renders is not asserting what it
means, and the fix is to model the consumer.

**The trap, measured rather than reasoned.** On this box the old command
lost exactly **one** line. Under `TZ=America/New_York` the same command
returns 48,946 lines against the epoch form's 57,695, opening `17:10:00
-04:00` — four hours past the incident, which is absent entirely. BST
makes the error benign, so the box that would notice is the one that
never runs the command. The entry's "five hours" is EST; the rule is *N*
hours late at UTC−*N*.

## Next session — ranked

**1. `SNAG-LOG-010` — the signature belongs in the noise title.** The
last unapplied instance of `SNAG-AGENT-005`'s rule, and the only open
item with a **deadline**. Session 69 ranked it last on "population is
zero", which is true of the live endpoint and false of the data:
`log_entries` holds 451,154 kernel rows for the pair through 2026-08-12,
retention is 30 days, so **2026-09-11** is the last day it can be
verified against real rows. Half a day.

**2. Session 33 — seam drift detection.** The largest genuinely-open
roadmap session, and its premise is this sitting's defect one repository
over: Alfred's consumer fixture was two sections behind on the day it was
captured with its contract test green throughout. It loses on
*readiness* — its second task reads another repository's fixture off the
same disk, and cross-repo concerns have had an owner since 2026-08-13, so
the first move is a question for estate-manager rather than code here.
Rank it first once that is answered.

**3. `SNAG-ESTATE-008` — nothing checks a documented ops action against
the box.** It cost this sitting real time and it cost Session 70 real
time. It loses because the cheap fix is what the global convention
already demands (re-measure at session start) and that is what caught it
today; the expensive one is a mechanism with no enforcement point,
because these claims live in prose.

**Lost, and why.** `SNAG-LOG-011` (P3) — a deleted route still answers
`200` through the `/api/logs/{source}` catch-all; real, cheap, and it has
**no consumer**. `SNAG-UNITS-006` (P3) — empty population, and its fix is
a sweep-wide change to `discover_units` on the strength of a
log-correlation sitting. `SNAG-LOG-008` is **expired, not fixed**.

**Blocked on another repository.** `SNAG-LOG-012` (`strip_markdown` is
`estate-lib`'s), `SNAG-ESTATE-002`, `-004`, `-006`, `-007`.
`SNAG-ESTATE-001`'s remaining half is a retirement checklist the entry
says in writing is not this repository's to enforce.
