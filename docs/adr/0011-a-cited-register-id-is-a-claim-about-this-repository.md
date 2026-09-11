# ADR-0011: a cited register id is a claim this repository makes about itself, and only half of it is compelled

Decided 2026-09-11 by Session 214, taking the standing next action
recorded in [HANDOFF.md](../../HANDOFF.md) by Session 213 and closing
`SNAG-DOCS-016`, which had **decided against deciding** and was correct
to.

**The rule, in one sentence.** A commit that cites a cross-repo register
message id carries, in the same sentence, one clause saying what that
message said — and an id for a filing this sitting made is written
**whole**, while an id for a message this repository received stays
**short**.

Every figure below was derived in this tree at `5db07b8`, 2026-09-11,
by the method estate-manager published at
`estate-manager/docs/guides/citation-census.md`. Nothing here reads
their numbers: their figures are among the things being checked.

---

## 1. What changed, and what had not

The entry's refusal rested on three legs and **two of them still stand**.
Nothing is asked; nothing on this box reads a commit message as a
surface. The leg that moved is the third: the entry declined because
estate-manager had ruled ADR-0155 *binding its own sessions only* and had
recorded the estate-wide form in its §8 as **a recommendation for the
owner, not decided**. Declining against a pending input is a legitimate
position for exactly as long as the input is pending.

The owner ruled on 2026-09-10 (estate message
`47f22a6e-46a0-401d-968e-539840ae7c57`): **each repository decides for
itself, and the estate publishes the method rather than the answer.** So
the input arrived, and it arrived in the one direction that removes the
refusal's own reason — there will be no estate-wide answer to wait for.
The entry is not re-decided because it is small. It is decided because
what it was waiting for has happened.

Two things the entry could not have known:

- **The split by direction**, which this tree had only in aggregate.
- **This tree already contained one commit practising the form.**
  `3952058`, written the evening of 2026-09-10 by the sitting that handed
  this over, cites `fc6f769f-31a8-427a-b772-e4a0172b8d32` whole, glosses
  it in the same sentence, gives the reason — *"Cited whole because a
  short id resolves on no route (SNAG-DOCS-016)"* — and then declines to
  generalise: *"an instance, not an adopted convention."* This ADR
  ratifies an observed practice rather than inventing one, which is the
  cheapest kind of convention to adopt and the easiest to under-record.

## 2. The measurement reproduces, and the one disagreement is definitional

Re-derived independently rather than accepted — `verify-ops-claims-live`,
which reaches a figure filed **about** this repository as much as one
filed by it. At the boundary their sweep describes (351 commits):
**47 citing commits**, **43 received sites**, **0** of them whole — all
three exactly theirs. Two figures differ, and they differ for one reason:

| | theirs | here | at HEAD (357 commits) |
|---|---|---|---|
| citation sites | 74 | 73 | 78 |
| own filings | 31 | 30 | 31 |
| …by whole uuid | 1 | 0 | 1 |

**`ebd58df` cites one id in both forms** — `70377694` short in the
subject line, `70377694-c7e6-4cb8-9c92-7c9c3258f82b` whole in the body.
They count a site as *(commit, id, form)* and this sweep counted
*(commit, id)*, so the same commit is two sites there and one here. That
accounts for the whole difference and nothing else does.

It is worth stating because it changes what their headline **means**:
*1 of 31 by whole uuid* sounds like one sitting choosing the wide form.
It was a body line restating a short id the subject had already written.
**Before `3952058`, no commit in this tree had ever cited a register id
by whole uuid alone.**

## 3. The split cannot decide the question, because two readings of it disagree

The handoff named the split by direction as what decides whether one
convention covers both halves. It does not, and the reason is the
measurement estate-manager's own guide flags as having no honest
mechanical predicate — §4, *read the sentences*. Both parties did, on the
same corpus, and the aggregate agrees while the split inverts:

| | own filing | received |
|---|---|---|
| estate-manager's reading (74 sites) | 17 of 31 — **54.8%** | 22 of 43 — **51.2%** |
| this reading (78 sites) | 12 of 31 — **38.7%** | 27 of 47 — **57.4%** |

Aggregate gloss is **39** either way. Their reading finds no separation;
this one finds the own half markedly worse — which is the shape they
measured in *their* tree and did not find in ours. Two careful readers
inverted the one number a rule was to be built on.

**So the rule is not built on it.** The corpus reading establishes that
roughly half the citing sentences carry no substance — which both
readings agree on, and which is the whole case that something is owed —
and it is not asked to decide the form. That is a narrower use of a
soft measurement than the handoff proposed, and it is the use it can bear.

## 4. What decides it is compulsion, which is not a reading

The two directions are different acts, and the difference is mechanical:

- **31 sites cite a filing this sitting made.** Estate rule *a change to
  a surface a repository publishes is announced by a filing at its
  measured readers, before the commit that carries it, message id cited
  in the commit* **requires** the id. The sitting has no choice about the
  id; its only choice is the clause beside it.
- **47 sites cite a message this repository received.** No rule on this
  box requires any of them. estate-manager's `5ebe902b` corrected its own
  first draft on exactly this point, reading it off this tree: our
  `8727b77` is a receiver citing a message it acted on, *"which no rule
  on this box requires at all."*

That asymmetry decides the form, because the two citations are evidence
for different claims:

**An own filing's id is the only witness to a claim this repository makes
about its own compliance.** "Announced before this commit" is unfalsifiable
from inside this tree — the announcement lives in another process's
database. A reader auditing rule 3 has one route, and the short form
returns **422** on it. So the id is written whole: this repository's
claims about itself should be the ones it makes maximally checkable.

**A received message's id is provenance this repository volunteered**, and
the claim it supports — "they told us this" — is already witnessed by the
change the commit carries. The clause names the sender; sender and date
reach the row by list-and-match, which is the only path either form has
in practice. Widening it buys an on-box reader a route into a row **this
repository did not write**, at the cost of putting 28 characters of
another repository's identifier into a sentence whose job is to say what
*we* did. It stays short, on the
read/handed-over line estate-manager's ADR-0154 drew for the seam between
its session-start notice and the register's close route — cited by name
and deliberately not linked, for `SNAG-DOCS-020`'s reason.

This lands in the same place as estate-manager's ADR-0155 and Alfred's
ADR-0098 by a different route, and the agreement is worth recording as
agreement rather than as adoption. **Their stated reason does not
transfer**, and that is why it was not borrowed: they refuse the wide
form for received ids on the ground that *"a reader who cannot resolve
gains nothing from 28 more characters — the gloss is what reaches them,
not the width."* True, and equally true of an own filing — so it argues
for one form everywhere and cannot distinguish the halves. Compulsion can.

## 5. Disclosure is not a term, and the reason here is stronger than the estate's

estate-manager recommended this clause be stolen: a rule turning on
whether a tree is public *"will be applied wrongly and silently, the fact
it depends on changing in two clicks and leaving no trace in any tree."*
Taken — and this repository, being the tree the whole question was framed
around, can give a stronger reason than the one offered.

**The register is a live service, and no tree holds its rows.** Measured:
**136** messages, oldest `2026-08-25`, newest `2026-09-10`, in
`cross_repo_messages` in the `estate` database. estate-manager's tree
holds ADRs, migrations, drivers and reports *about* the register; it
holds none of its content. So a citation's resolvability turns on `:8400`
being up and the row still existing — not on who can read the tree.

That drains the publication framing out of the entry's own symptom. The
short id was never resolvable for anyone (**422**), `:8400` binds
`127.0.0.1`, and a sitting in this tree six months from now is in the
same position as a stranger on github the moment either the service or
the row is gone. All **57** distinct ids cited here still resolve today,
which is what the id is for and is a fact about today. The gloss is the
only copy of what was announced that lives in this repository at all —
and that is true of a private tree and a public one identically.

## 6. No format is to blame here, which is why the rule binds the sitting

estate-manager's §5 finding is that its own announcement blocks were its
worst category, because a house format written to name *audience,
instrument, receiver, count* has **no slot for the subject** — and it
recommends that a repository with such a format look there first rather
than at the sittings. Done, and the recommendation does not pay out here.
Three structural hypotheses, each formed while reading and then measured:

| hypothesis | glossed | refuted by |
|---|---|---|
| the `Filed at <receiver> as <id>` clause has no subject slot | 52.6% in format vs 47.5% in free prose | no signal |
| the id trailing a subject line has no room | 50.0% over 8 sites | no signal |
| a commit citing several ids has one slot and many subjects | 52.9% / 31.2% / 57.1% at 1 / 2 / 3+ ids | not monotone |
| an id sharing its sentence with another loses its clause | 50.0% vs 50.0% | exactly no signal |

The first was written down as a finding before it was measured, and the
cross-tab refuted it. It is recorded here as refuted rather than dropped,
because a plausible structural cause that is **not** the cause is worth
more to the next reader than silence: it says the remedy is not a
template.

Two consequences. **The rule binds per id, not per commit** — and needs no
exception for the multi-id case, since the 3+ bucket is not the worst one.
And **there is nothing to fix upstream of the sitting**: no block to
re-shape, no generator to amend. The obligation is on whoever writes the
sentence, which is the weakest kind of rule this repository has, and it is
what the evidence supports.

## 7. Considered and refused

- **A check, and a test.** Refused for the reason `SNAG-DOCS-016` already
  gave and for one more. `check-snag-claims.sh`'s `ok` means *the defect
  is still real*, so a check asserting this convention reports `still
  holds` over a landed decision for ever — `check_review_schedule_unread`'s
  defect. A test is refused on estate-manager's ADR-0155 §8 ground, which
  transfers exactly: it would have to read a commit that has not been
  written. **The artefact is this document**, and that is the honest shape.
- **Repairing the corpus.** Unreachable. The 32 bare sites are published
  commits, and editing them is the history rewrite
  [ADR-0009](0009-the-remote-is-two-questions.md) §4 refused over 116
  cited commit SHAs — a refusal ADR-0010 §2 then found to be stronger than
  it read, since a blob is served at its SHA for ever.
- **One form for both directions.** Refused on §4: the halves differ in
  whether any rule compels the citation, which is mechanical, where the
  gloss-rate split that would have argued the same case is a reading two
  readers inverted.
- **Conditioning any of it on disclosure.** Refused on §5, and with a
  reason of this repository's own rather than the estate's.
- **Extending the rule to foreign ADR citations.** Deferred, not refused,
  and filed as `SNAG-DOCS-020`. Measured here: **29** commits cite another
  repository's ADR number, comparable in scale to the 47 that cite a
  register id, and Alfred's `6d66bb55` reports the same class from its own
  side — *"3 of 5 citations point into trees that answer 404 to your new
  readers."* It is a different question and is not this one's to settle:
  `estate-manager ADR-0155` names a repository and a decision, where
  `25be77ba` names nothing. Widening scope unasked is how a decided
  question becomes an undecided one.

## 8. What this does not do, and what carries it

It does not reach a published commit, does not add a check, a test, a
route, a schema or a config leaf, and does not oblige any other
repository. **No filing announces it.** The measured reader of this
surface is estate-manager, whose census driver sweeps this tree's
`git log --all` — so the audience is not empty, and the channel is the
one they opened: `47f22a6e` is closed with a note carrying the decision,
and that close is cited in the commit. A second message announcing the
same thing to the same reader is a duplicate, which the register's own
withdrawal-and-refile history is already sharp about.

What carries the convention is that a sitting reads this file, or reads
`SNAG-DOCS-016`'s closing line, or copies the shape of the last commit
that did it. That is weaker than a guard and it is what the measurement
in §6 supports; pretending otherwise would be the kind of claimed control
this repository asks *what enforces it* about.
