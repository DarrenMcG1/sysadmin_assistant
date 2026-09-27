# ADR-0015 — `pointers` has an owner, and the cause is here

**Date:** 2026-09-27
**Status:** Accepted
**Context:** estate message `d93a1882` (estate-manager → sysadmin-assistant,
filed 2026-09-09), which recommended — explicitly *not* ruling, on the
estate rule that the monitor decides what it judges — that the audit's
`pointers` check join `JUDGED_AUDIT_CHECKS` at `warn`. Their ADR-0142 had
moved the check's minter half out of their test gate that day, so its two
codes stopped reaching anyone. The question then stood unticked in
`tasks.md` for eighteen days.

---

## 1. Decision

**Refused.** `pointers` does not join `JUDGED_AUDIT_CHECKS`; the mapping
stays `{"ports": "breach", "wiring": "warn"}`.

The refusal is not a decision that nobody should say it. Every finding
the minter half can file is opened by a write to **this** repository's
snag list, so the speaker is placed there:
`tests/test_snag_estate_series_is_closed.py` pins this repository's
`SNAG-ESTATE-*` definitions to the fifteen the estate already marks, and
a sixteenth, a rename or a removal fails the suite before the estate's
05:00 run can read the working tree.

## 2. The test, clause by clause

ADR-0006 admits a check on **ownership, never severity**. `docs` was
refused at the first clause on 2026-09-12 (`judgements.py`, the
`JUDGED_AUDIT_CHECKS` block); `pointers` fails at the same place, and
that decides it — but the other clauses were measured rather than
skipped, because the handoff named two of them as open.

| clause | `ports` | `pointers` (minter half) |
|---|---|---|
| no repository owns it | no repository owns a port | **fails.** `check_snag_minters`' own docstring: *"The subject is this repository's document"* — estate-manager's `docs/roadmap/snag_list.md`, and the designed remedy is a marker in *their* entry (their ADR-0103) |
| estate-wide by construction | any listener | **fails.** Two repositories define `SNAG-ESTATE-*` ids, not the estate |
| the estate may not alert | their ADR-0003 | holds |
| this service raises nothing about it itself | it does not | holds today; **the cause is here** — §3 |
| nobody says it at all | was true | **holds.** No `SessionStart` hook and no estate preflight prints an audit finding; the board is a pull surface |

The handoff framed the first clause as *"the id is owned by whoever
minted it, but a collision spans repositories"*. Reading the producer
settles it more narrowly than that: the finding is not about the
collision in the abstract, it is about **one sentence missing from the
estate's own document**. That is the estate's conformance, and the estate
rules send a repository's conformance to its own ADR process.

## 3. Why judging it would be this service judging itself

Measured 2026-09-27, with the producer's own parser
(`estate.snags.read_snags`, which is what `check_snag_minters` reads
with):

- **Only two repositories on this box define a `SNAG-ESTATE-*` id** —
  estate-manager (206) and this one (15). Every other registry
  repository defines none.
- **This repository's fifteen are 001–014 and 016**, all below the
  estate's highest. The estate mints upward, so it cannot open a new
  collision with us by minting. Only a write here can: a new id opens
  `snag_id_collision_unmarked`; renaming or removing one opens
  `snag_id_marker_unfounded`, because their marker then names nothing.
- **Both windows their ADR-0142 driver found were opened by commits
  here** — `6330e40` (minting 016, 2026-09-04, closed by their marker)
  and `270e401` (minting 017, 2026-09-08, closed by our rename to
  `SNAG-CFG-007`).
- **Population today is zero.** `pointers.run_check` driven read-only in
  their venv against the live tree files nothing.

So an admitted `pointers` family would be an alert this service raises
about a fault only this service can cause, a day after it caused it.
That is the shape the estate rules forbid in *"neither judges itself"*,
arriving through a finding filed against a different repository. Neither
`ports` nor `wiring` could produce it.

## 4. What speaks instead, and why it is earlier

`tests/test_snag_estate_series_is_closed.py` holds `CLOSED_SERIES`, the
fifteen ids, and compares it with what `read_snags` finds in this
repository's snag list. **Exact-set equality covers both of the estate's
directions**, and both were falsified before shipping:

- at `270e401`'s text it reports `added ['SNAG-ESTATE-017']`;
- with 016's row renamed in memory it reports `removed ['SNAG-ESTATE-016']`.

It reads with the producer's parser and never with a regex, and that was
decided by measurement: the list-item sweep this repository's own memory
recommended counts **14**, because `SNAG-ESTATE-016` is a row in the
archive *table*. The estate had counted it and marked it on 2026-09-04.
A second implementation of *"which ids does this file define"* was wrong
on the day it was checked, and the one that decides whether a collision
exists is theirs.

Changing `CLOSED_SERIES` changes the truth of the estate's markers, so
the failure message says to file at estate-manager first rather than
edit the constant to go green.

## 5. Rejected

- **Admit `pointers` at `warn`**, the recommendation. §2 and §3: it
  fails ownership at the first clause, and every finding it can raise is
  this service's own act, reported after the fact.
- **Admit only `snag_id_collision_unmarked`, or only findings naming
  another repository.** Scoping by code or by `detail['repository']`
  changes which rows arrive, not whose document the subject is. And today
  every finding names this repository.
- **A preflight carrier**, as `docs` got in `scripts/check-estate-docs.sh`.
  It would print a finding about a collision that already exists. The
  guard stops the collision from being created, and running both would
  give one fact two speakers.
- **Leave it undecided.** That is the silence ADR-0006 exists to refuse,
  and it had been the state for eighteen days.

## 6. What this does to the estate's row

Nothing they must do. Their ADR-0142 §5 recorded *"a finding that alerts
nobody"* as the stated cost of their change and filed no follow-up either
way. This answer is sent to them anyway, because it changes what their
cost statement describes: the collision half is now prevented at the only
source that can open it. Their marker and their 05:00 check are unchanged
and still the authority. The other `pointers` codes (`pointer_missing`,
`link_unresolved`, `snag_id_defined_twice`, …) are about the estate's own
documents and were never in question here.
