# Handoff — 2026-08-25

## Next action

Give `SNAG-ROADMAP-001` a check and settle the question it forces — its subject is another repository's code path rather than a document, so decide before writing whether a check that skips when estate-manager's venv is absent is a check at all or a fourth way of reporting `unknown`.

## Session 85 is complete — the ninth check, for the entry the mechanism rule was named after

`sysadmin/snag_claims.py` gains `check_capped_signature_collides` and
`SNAG-LOG-013`'s body carries `<!--check:capped_signature_collides-->`.
Checked entries go **8 → 9**, unchecked **18 → 17**, and **all nine
claims still hold**. estate-manager's `read_snags` reads **69 entries, 26
open, dialect `bullet`** either side of the edit, so the marker moved
nothing the board publishes.

**2457 tests pass** (2449 + 8). Ruff clean, mypy clean. The daemon was
restarted at **22:14:04** and `/health` answers 200 — nothing it imports
changed, and the restart was taken rather than argued with for the reason
Sessions 81 and 84 took theirs.

## What was decided, and on what evidence

**This entry first, because a population-shaped check does the most
damage here.** `SNAG-LOG-013`'s own last bullet says its ten raw-JSON
rows left the seven-day `current` window the afternoon it was filed;
Session 82 measured that emptiness and kept the entry **open**, because
"population is currently zero" is exactly what mis-ranked its parent
`SNAG-LOG-010`. So the check drives the mechanism through the real
`recommend()` and never asks what the live table holds today.

**The probe's shared prefix is derived from `SIGNATURE_DETAIL_CHARS`, and
that is the load-bearing line.** The entry argues in writing that raising
the cap is not the fix — any bound is defeated by two records that differ
past it — so a hard-coded prefix would report that remedy as a fix and
have the check arguing against the entry it measures. Driven both ways:
pinned at 240 it breaks two of the eight new tests; derived, it still
reports *still holds* at `SIGNATURE_DETAIL_CHARS = 400` over a
540-character agreement.

**Two halves, because the entry's title is a conjunction** — capping
*can* put two rows back where `SNAG-LOG-010` found them, and inside one
roll-up it *already has*. The pair is driven inside
`INCIDENT_WINDOW_SECONDS`, where the roll-up's member lines are compared,
and outside it, where two rows' titles are.

**They are not independent in one direction, and the direction that
separates them is the entry's own fix.** `quoted_signature` delegates to
`capped_signature`, so one fix to the shared function closes both and the
note says so rather than naming a half. What closes the detail half alone
is a cap taken from where the group's members diverge — which needs the
sibling set and cannot live in the per-row pure function the titles are
built from. That is the entry's second candidate fix, and it is a test.

**The first draft of the second half was a false negative.** It used two
different sources, so the titles came apart because
`_new_recommendation` opens a title with the source name — the claim
reported refuted for a reason with nothing to do with the cap. A fixture
that moves two things at once cannot say which one it measured.

**Removing the cap altogether is `unknown`, never `mismatch`.** The two
signatures render apart and not because anything learned to tell them
apart; the mechanism under test is gone. Falsified by deleting the guard,
which turns that input into a reported fix.

**What the check cannot reach is stated rather than implied.** The
entry's first candidate fix is `SNAG-LOG-008`'s — readable signatures at
the producer — which removes the population and leaves the mechanism
untouched, so this check would go on reporting *still holds*. Rule 1
rather than a gap, and the reason the live table is not read here at all:
a database read would make the check `unknown` whenever PostgreSQL is
down, for a claim that has nothing to do with the database.

## Rejected, and why

- **A live-table population check.** The obvious implementation, and it
  closes the one entry two sittings argued must stay open.
- **A hard-coded probe prefix.** Simpler, and it reports the entry's own
  refused remedy as a fix.
- **One boolean over the two halves.** Cheaper, and it cannot tell the
  entry's second candidate fix from a title disambiguator — which is the
  only distinction worth reporting.
- **Rewriting `SNAG-ESTATE-014`'s title figure from eighteen to
  seventeen.** The title records what was true when the entry was opened
  and the live count is `convention:unchecked`'s to publish, which is
  that entry's whole argument. A dated progress bullet instead.

## Blocked / carried

- **Nothing is blocked.** 17 open entries still carry no check; the order
  is by what a wrong answer costs, which is what picked
  `SNAG-ROADMAP-001` next — the only unchecked entry whose wrong answer
  is *published* to the estate board.
- **A cross-repo slip worth not repeating.** A `git stash` intended for
  this repository ran in `~/projects/estate-manager` because a compound
  command left the shell in their tree; it stashed three uncommitted
  files and was popped within the minute, their tree verified back to the
  same three modifications. Another session may share that tree. Address
  another repository by absolute path, never by leaving `cd` behind.
