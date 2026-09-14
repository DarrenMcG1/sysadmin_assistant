# ADR-0013 — A published key is necessary for a project-keyed reader and was never sufficient

**Date:** 2026-09-14
**Status:** Accepted
**Context:** estate message `a9ee6305` (estate-manager → sysadmin_assistant,
filed 2026-09-13), which re-took this repository's own measurement on a
larger denominator, refuted the conclusion drawn from it, and left the
scope decision here.

---

## 1. The question that was asked

`scripts/check-estate-docs.sh` is the carrier `SNAG-DOCS-022` built: the
estate's audit files findings about this tree, and until that script
existed a `docs` breach about our `HANDOFF.md` could sit in the register
for days and reach no sitting at all. The script reads
`GET :8400/api/audit/findings`, keeps the findings whose
`detail.project` is this checkout's path relative to the projects root,
and prints them at the top of every session.

It reads the `docs` check and nothing else. The justification it carried
was a **census** of the producer, taken 2026-09-12 by walking `Finding(`
against `"project":` across estate-manager's thirteen check modules:

```
docs         7 findings, 7 carry detail.project   ← total
pointers    12 findings, 0
consumers    9 findings, 2
readers      6 findings, 1
ports        4 findings, 3
wiring       2 findings, 0
```

— and the conclusion that `docs` is the only check whose findings *all*
carry the key, so it is the only check a project-keyed reader can read
without being blind on most of the population.

estate-manager's message re-took that count over **all 1,666 stored
findings across 430 audit runs** (2026-08-13 → 2026-09-13) and reported:

> your pointers figure reproduces on a larger denominator (0 of 18); the
> conclusion does not. docs is 603/603, ports is 803/929, and the 126
> misses are one code. […] The only code without it is
> `unclaimed_listener`, which by construction has no claimant to name:
> the absence is the finding. […] Whether to point the reader at ports is
> yours; this says only what the surface carries.

**The question left here: should the reader read `ports` as well as
`docs`?**

**Decision: no.** The reader stays on `docs`. The *reason* it stays does
not survive, and is replaced rather than repaired.

## 2. Their measurement is right, and ours had already aged

Nothing in §1 is disputed. Re-driven against their source on 2026-09-14
by this repository's own walker, every claimant-naming ports code carries
the key on every construction site:

| code | rung | `detail.project` |
|------|------|------------------|
| `claimed_but_silent` | `warn` | yes |
| `claimed_tool_default` | `info` | yes |
| `dormant_but_listening` | `info` | yes |
| `claimed_by_an_unregistered_tree` | **`breach`** | **yes** |
| `claimed_by_more_than_one_row` | `warn` | **no** |
| `unclaimed_listener` | `breach` | no, by construction |

What is worth more than the correction is **how fast the figure that was
corrected went stale**. The census read `ports  4 findings, 3` on
2026-09-12. Two days later the same walker reads **6 sites, 4 carrying
the key**, because two codes landed on 2026-09-13 — their ADR-0166
(`claimed_by_an_unregistered_tree`) and ADR-0168
(`claimed_by_more_than_one_row`). The `docs` row aged in the same window,
7 sites to 9.

So the instrument was wrong before the conclusion was. A census of
another repository's vocabulary cannot hold a scope decision, because it
ages silently and in a direction no test here was watching — their
ADR-0171, *a vocabulary that moves in the open does not need a gate*,
measures that movement from the producer's side. **The census is retired
rather than refreshed** (the treatment `SNAG-DOCS-029` established: swap
the count for the fact the argument needs), and what replaces it is a
property that does not move when a code is added.

## 3. What neither count could see: two codes that have filed nothing

Their measurement is over `audit_findings` — findings **filed**. Ours was
over `Finding(` — construction **sites**. The decision turns on two codes
that are invisible to the first and were not yet present in the second:

`claimed_by_an_unregistered_tree` and `claimed_by_more_than_one_row` have
each filed **zero findings** across the 430 runs, which is why neither
appears in the message's group-by. Both are live in the producer's source
today. And they break a project-keyed reader over `ports` **in opposite
directions, simultaneously**.

That is the transferable part of this record: *measure the vocabulary,
not the filings, when the question is what a reader will meet.* A code
with an empty population is exactly as capable of breaking a consumer as
a code with 465 filings; it simply has not done it yet.

## 4. Direction one — a code at the rung this repository already judges

`claimed_by_an_unregistered_tree` is `SEVERITY_BREACH`
(`audit/checks/ports.py`) and its `detail` carries `project` beside
`port`, `role`, `directory`, `projects_root` and `holders`.

`JUDGED_AUDIT_CHECKS[PORTS_CHECK]` is `"breach"`, and
`judge_audit_findings` drops every finding whose `severity` is not that
rung. So this code **already arrives here**, hourly, as an alert row the
tray speaks by name.

A preflight reader matching on `detail.project` would catch the same row
a second time, in a second voice, on a second cadence — one fault, two
speakers. That is the second-owner defect this repository has now found
at six scales, and it is the reason `ports` and `wiring` were excluded in
the original block *in addition to* the census. **That half of the
original reasoning survives intact**; what changed is that it now has to
carry the refusal alone, and it turns out to be able to.

Note the shape this produces, because it is the opposite of the
intuitive one: the ports findings that carry the key are mostly the ones
that **do not** arrive (`warn`/`info`), and the one that arrives and
*does* carry the key is the one with no filings. A reader scoped by the
key alone would have been correct about today's table and wrong about the
producer.

## 5. Direction two — a code that names claimants without publishing the key

`claimed_by_more_than_one_row` is `SEVERITY_WARN`
(`audit/checks/ports.py`) and its `detail` is `{"port", "rows"}`. It
names its claimants one level down, in `detail["rows"][].project` — one
entry per registry row claiming the port.

A reader keyed on `detail.project` matches nothing and prints *none for
`sysadmin_assistant`*. That is `ports_checked`'s rule, met from the
outside: zero-because-blind served as zero-because-clean, which is the
exact collapse the script's own `ORPHANS` branch exists to prevent for
`docs`.

It is also the one ports code that can name **this** repository without
naming a port this repository holds — two rows of
`monitorable-project.md` claiming one port, ours being either of them. A
carrier that is structurally blind to the one finding shape most likely
to be about us is worse than no carrier, because it reports health.

## 6. What is true of their sentence, and does not reach these two

> Every ports code that names a claimant publishes it on every finding it
> has ever filed.

This is true as written and remains true. It is quantified over findings
**ever filed**, and `claimed_by_more_than_one_row` names claimants and
has filed none — so it sits outside the quantifier rather than
contradicting it. Their message says in its own last clause that it
"says only what the surface carries", which is precisely the scope this
record does not exceed.

No correction is owed to estate-manager. The message was right, it
refuted something that needed refuting, and the decision it left here
turns on evidence it did not claim to cover.

## 7. What was refused as a reason

**"The population is currently zero."** Live on 2026-09-14 the audit
holds two `ports` findings, both naming `venture-assistant` (`port 3300
claimed_but_silent`, standing 18.8 d; `port 8080 claimed_tool_default`,
standing 17.8 d) and **none** naming this repository. So widening would
have delivered nothing today. That is not why it is refused: an empty
population is what mis-ranked `SNAG-LOG-010`'s parent, and a reason that
expires the first time a finding lands is not a reason.

**"It is cheap."** It is — one `select` in an existing `jq` filter. Cost
was the wrong axis on `SNAG-AGENT-007` and it is the wrong axis here.

**The residue's count.** The retired block said *eleven checks' findings
about this tree still reach no sitting, and closing that needs a key the
producer does not publish.* Both halves are now wrong: the key **is**
published for `ports`, and the number could not be reconstructed from its
own rule — 13 checks less `docs`, `ports` and `wiring` is ten, and
counting the partly-arriving checks either way gives ten or twelve, never
eleven. The residue is restated as a rule and not as a figure, which is
the treatment a hand classification gets when its population turns out to
be undecided.

## 8. What this changes

* `scripts/check-estate-docs.sh` — the census block is replaced by §4 and
  §5's property. No behaviour changes: the script read `docs` before and
  reads `docs` now, and its three exit statuses are untouched.
* `tests/test_estate_docs_notice.py` — gains
  `TestPortsIsRefusedOnAPropertyTheVocabularyCannotMove`, four tests that
  read the producer's **source** for the code, the rung and the detail
  keys, and compose the rung against this repository's own
  `JUDGED_AUDIT_CHECKS` rather than restating `"breach"` on both sides.
  Six mutations driven; four land on exactly one test, and renaming a
  `SEVERITY_*` constant lands on the premise as well as the overlap test,
  which is what the premise is for.
* The module's existing `test_the_detector_can_be_seen_to_fail` kept its
  assertion and **lost its inference**. Its docstring said that a sibling
  check starting to publish `detail.project` would mean the refusal to
  widen "has lost its reason". That is the reading this record retires:
  the key's presence is necessary and was never sufficient.
* `ESTATE_TREE` in that module became overridable by
  `ESTATE_TREE_OVERRIDE`, for the reason the script's own
  `ESTATE_PROJECTS_ROOT` is overridable — guards that assert things about
  a tree this repository does not own cannot otherwise be driven at a
  producer that has changed, and a no-op mutation is not a control.

Nothing moves in `JUDGED_AUDIT_CHECKS`, no severity moves on either side,
and no alert family gains or loses a member.

## 9. What would reopen it

Either direction ceasing to hold, and each has a test that says so by
name:

1. **No ports code at the judged rung carries `detail.project`.** Then
   the reader could not double-speak, and only §5 would stand.
2. **`claimed_by_more_than_one_row` starts publishing `detail.project`**
   (or stops naming claimants at all). Then the reader could not be
   blind, and only §4 would stand.

Both at once is what a widening needs. Neither test is a request to
widen when it fires — each says *re-read this record first*, because the
refusal is a conjunction and one limb falling leaves the other.

## 10. What is *not* decided here

* **ADR-0006's admission test is untouched and does not apply.** That
  test governs `JUDGED_AUDIT_CHECKS` — which findings this repository
  *speaks for*, an ownership question. This is a **reading** surface: a
  session banner that judges nothing, raises nothing and writes nothing.
  A check can be unreadable here and still judged, which is exactly what
  `ports` is.
* **Whether the residue should be closed at all.** Findings about this
  tree from the eight-or-so checks that neither arrive nor are read still
  reach no sitting. Closing that needs a carrier whose key is not
  `detail.project`, and this record does not design one.
* **Anything about `wiring`.** It is excluded by §4 alone and by ADR-0008,
  and nothing here re-examines either.
