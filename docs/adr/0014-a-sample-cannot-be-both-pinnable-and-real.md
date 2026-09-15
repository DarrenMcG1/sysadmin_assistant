# ADR-0014 — A sample cannot be both pinnable and real

**Date:** 2026-09-14
**Status:** Accepted
**Context:** the Session 33 roadmap group "Seam drift detection" (requested
2026-08-06), whose first task has stood unchecked since, and estate message
`d29929d7` (estate-manager → sysadmin-assistant, filed 2026-09-14), which
withdrew the second consumer of the artefact that task asks for and left the
remaining question here in its own words: *"whether it is still worth
publishing for that is yours, not ours"*.

---

## 1. The question that was asked

`docs/contracts/briefing_preview.sample.json` does not exist, and neither
does `docs/contracts/`. Three unchecked tasks in
[`tasks.md`](../roadmap/tasks.md) ask for it, the first being the one that
makes the rest cheap:

> **Producer publishes the sample.** A test here regenerates
> `docs/contracts/briefing_preview.sample.json` from `generate_briefing_data`
> and fails when it differs from the committed copy — so the sample cannot
> silently go stale, the same trick the schema-drift guard already uses for
> migrations.

It had two consumers. The first was estate-manager's seam-drift check — the
one this repository routed to them as message `6a330427` on 2026-08-25,
because reading Alfred's fixture off the shared disk *and* judging Alfred's
conformance are two estate rules rather than one. That check is **withdrawn
as of 2026-09-14, not deferred**: their message says in terms that it *"does
not reopen if the sample appears, because the refusal holds for any sample
you could publish"*. The second consumer is Alfred's own test suite, which
today reads a fixture Alfred captured for itself.

**The question left here: publish the sample for Alfred's test alone?**

**Decision: no.** Not deferred either — the three tasks are closed against,
and §7 records what that costs.

The reason is not the estate's reason. Theirs is that neither half of *their*
comparison is testable. Ours is narrower and lands one step earlier: **the
artefact task 1 could commit and the artefact Alfred's fixture directory
admits are not the same artefact**, and no amount of care makes them one.

## 2. Their measurement reproduces, on this repository's own instruments

Nothing in `d29929d7` is disputed. Both headline claims were re-taken here on
2026-09-14 rather than accepted:

- *"Five of your six sections are appended behind an `if`."* Reading
  `render_sections` in [`sysadmin/briefing/data.py`](../../sysadmin/briefing/data.py):
  `Infrastructure Status`, `Filesystem`, `Weekly Log Review`, `Weekly Disk
  Review` and `Weekly System Health Review` are each appended inside a
  conditional. `Overnight Logs` is the one unconditional section, and the
  code says why in a comment — *"a count is always available and zero is an
  answer"*.
- *"Alfred reads 3 of your 8 top-level keys … never `schema`."* An AST walk
  of `alfred/services/briefings.py` for subscripts and `.get()` calls on the
  adapter's payload finds `sections` and `facts`; `generated_at` is read
  through `_producer_timestamp`. `schema`, `period`, `alerts`, `summary` and
  `source` appear nowhere in that module. Three of eight, confirmed.

## 3. The stronger measurement is ours, because it is about the payload

estate-manager measured the **producer's code** across the 15 commits that
have touched it. That is a proxy. The thing a sample would pin is the
**payload**, and this repository can measure that directly.

Driven live on 2026-09-14, read-only, through `get_scheduler_session` against
the live `projects` database — `generate_briefing_data` called twice, 1.1
seconds apart, with nothing between the two calls:

```
top-level keys : alerts facts generated_at period schema sections source summary
sections       : Infrastructure Status, Overnight Logs, Filesystem,
                 Weekly Log Review, Weekly Disk Review, Weekly System Health Review
fields differing between the two runs: 3
  .generated_at          '…T20:03:21.256555+00:00' != '…T20:03:22.407301+00:00'
  .period.to             (the same two values)
  .facts.logs.measured_at (the same two values)
```

**Task 1 is unbuildable as written, and the database never moved.** A test
that regenerates the payload and *"fails when it differs from the committed
copy"* fails on the second call, because `generate_briefing_data` opens with
`now = datetime.now(UTC)` and stamps it into three places. The test can only
be built by normalising those away — and once it normalises, the counts
underneath are still live: service rows, log entries, disk occupancy, three
narrative bodies written by a language model.

## 4. And the section set is weather, measured on our own rows

Five of six sections are conditional, so *which* sections exist is decided by
data. Reconstructed from the three review tables against the 06:00 briefing
boundary and `_REVIEW_FRESH_DAYS = 8`, the presence triple
(`Weekly Log Review`, `Weekly Disk Review`, `Weekly System Health Review`)
took **five distinct shapes across the last 30 mornings**:

| mornings | log | disk | health |
|---|---|---|---|
| 2026-08-16 | – | – | – |
| 2026-08-17 → 08-24 (8) | – | ✓ | – |
| 2026-08-25 | ✓ | – | – |
| 2026-08-26 → 08-30 (5) | ✓ | – | ✓ |
| 2026-08-31 → 09-14 (15) | ✓ | ✓ | ✓ |

Its limit is stated rather than left to be found: this is reconstructed from
review generation times, not a record of payloads actually served, so it
bounds the variation from below — a morning the filesystem audit or the
service rows were also absent is invisible to it.

**Today is the most flattering morning in a month to take a sample**, and
that is the trap. All six sections are present for the fifteenth consecutive
day. A sample captured today would look complete, would be committed as
canonical, and would assert a shape this box did not hold on 14 of the last
30 mornings.

## 5. The consumer already absorbs the thing the sample was meant to catch

The estate map's table prices this option at *"small"* effort and claims it
catches *"a new section the consumer cannot map, at the consumer's next
commit"*. **There is no section this producer can serve that Alfred cannot
map**, and Alfred tests that as a requirement rather than enjoying it as an
accident:

- `test_unknown_section_type_degrades_to_text` asserts `normalise_type("timeline") == "text"`.
- `test_unknown_type_degrades_through_the_adapter` pushes a `sparkline`
  section through `adapt_sysadmin`, asserts it arrives as `text`, and asserts
  the data survives stringified — *"losing it silently is the failure mode
  this whole ADR is written against"*.

The mapping test is the other half. `test_sysadmin_adapter_maps_every_captured_section`
asserts `[s.title for s in sections] == [r["title"] for r in payload["sections"]]`
— the expectation is **derived from the payload it is handed**. estate-map
already says of the capture that this makes it *"structurally incapable of
failing on a stale capture"*. That property belongs to the assertion, not to
the file: it is equally incapable of failing against a published sample.
Publishing changes which file is asserted against itself. It does not change
whether the assertion can fail.

## 6. The fixture is a test double, not a contract pin

`sysadmin_preview.json` is read by **seven distinct test functions** in
Alfred's `tests/services/test_briefings.py`, nine call sites: the section
mapping, the four-type coverage assertion, the status-grid rename into
Alfred's vocabulary, the producer-ordering test, two glance-projection tests,
and the assertion that producer sections never carry a link. Several mock
`httpx` responses with it — it *is* Alfred's stand-in for a live producer.

So publishing does not replace that file. It adds a second file with no job,
unless Alfred repoints seven tests at it — which is Alfred's decision, in
Alfred's repository, and not something this repository can put there.

## 7. It would make this repository a second author of Alfred's convention

`test_every_capture_records_when_it_was_taken` walks every `*.json` in that
directory and requires a top-level `_captured` block carrying `at`, `from`
and `note`. All five fixtures have one. It exists for a good reason — a
capture's staleness was otherwise visible only by diffing mtime against a
live producer, and mtime does not survive a clone.

A published sample landing in that directory therefore either carries a key
defined by Alfred's ADR-0063, written by us — which is the second-owner
defect this repository has now found at six scales, arriving as a JSON key —
or Alfred exempts our file from its own provenance rule. Both are Alfred's
edit to make, and neither is improved by us making it first.

## 8. What is given up, and what is left undone

**One catch is genuinely surrendered.** `test_the_captures_together_exercise_all_four_types`
asserts the union of section types across Alfred's two envelope captures
equals `{status_grid, metrics, table, text}`. Against a live-regenerated
sample that assertion could fire on a morning this box stopped serving a
type. That is a real catch and it is refused on purpose: it fires as a **red
test in Alfred caused by our weather**, and a consumer's suite going red for
a producer's data is worse than the manual refresh it replaces. Today this
box serves `status_grid`, `metrics` and `text`; `table` has come from the
estate's producer since 2026-08-13 (ADR-0005), so a sample from here could
not carry the vocabulary whole in any case.

**Two things are left undone, deliberately, at the owner's direction.**

Alfred's `tests/fixtures/briefing_producers/README.md` says the sample is
*"blocked, not merely unbuilt"*, names `sysadmin_assistant/docs/contracts/briefing_preview.sample.json`
by path, and cites estate-manager `SNAG-ESTATE-066`. Both halves of that are
now stale — the check is withdrawn and the sample is refused — and no filing
was made to say so. Filed here as `SNAG-BRIEF-004` rather than absorbed.

Estate message `d29929d7` is **left open**. Nothing is owed to
estate-manager, they withdrew rather than asked, and the once-a-session inbox
notice is a more durable reminder than a checkbox, which would publish itself
to the board as this repository's next action.

## 9. What this does not decide

It does not touch the other two Session 33 tasks that were never about the
sample: the additive-only rule belongs in estate-manager's
`monitorable-project.md` and is theirs to write, and the refusal of a shared
contract package or a monorepo — *"three repos in three languages, two seams"*
— was taken on 2026-08-06 and is unaffected.

It does not say the seam is unguarded. It says what guards it is Alfred's
type-vocabulary assertion and coordination at migration time — which is what
carried the 2026-08-13 move of three sections to `:8400` — and that this was
already true before the tasks were written.

> **Both paragraphs above are corrected 2026-09-15 (Session 240), and the
> first was wrong when it was written rather than having aged.** The
> additive-only rule is **not** owed to `monitorable-project.md` by anybody:
> `estate-manager/docs/guides/alfred-briefing-integration.md` already states
> it almost verbatim — *"sections and fields are added, never renumbered or
> assumed complete. Build consumers that render what arrives and ignore what
> they do not recognise"* — under a parenthetical sourcing it to
> `a8cace4`, **inherited from this repository on 2026-08-06**, which is the
> day Session 33 was requested. The task named the general contract guide and
> the sentence landed in the guide that governs this particular seam; both
> were in this repository's `docs/guides/` that week and moved to
> estate-manager on 2026-08-11. So the task was discharged by its own sitting
> and stood unticked for 40 days, and §9 repeated its premise without checking
> it. estate-manager's own ADR-0123 §5 is about this failure exactly — a
> refutation a few paragraphs away in the same governed section — and filing
> it at them would have been that failure repeated at its author.
>
> The second paragraph was accurate on 2026-09-14 and is **superseded** rather
> than corrected: `tests/test_briefing_sections_are_additive.py` (2026-09-15)
> enforces the producing half, so coordination is no longer the only thing
> standing behind a section that stops arriving. Announced at estate-manager
> as `9b8e6f91-6022-4874-97b2-e6d3472b9fc5`, because the sentence that has
> aged is in *their* `estate-map.md` and is about *this* producer.
>
> **A figure this ADR does not carry, recorded here because its sibling
> documents do**: the producer's history holds **2** commits that removed a
> section title across **6** title-set changes, not 3. The walk built for the
> guard reports 3, the third being a 2026-08-06 parameterisation it cannot
> see through; estate-manager's `0179` driver recorded 2 on 2026-09-14 and is
> right. Corrected in the guard, in `STATUS.md`, and at Alfred as
> `202e3fa5-5854-428b-92d9-8582661a2abc`.
