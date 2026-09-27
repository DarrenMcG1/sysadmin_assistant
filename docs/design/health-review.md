# Weekly health review — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**The week the box had is narrated now, and the number it nearly
reported was off by three orders of magnitude** (Session 79, Tier 3).
`GET /api/sysadmin/review` is the **fourth** Tier 3 here, after the
project review that left with its domain, the disk review and the log
review. `sysadmin/monitor/health_review.py` is the module and
`health_reviews` (migration 016) its own table — a third review table
beside `disk_reviews` and `log_reviews` for Session 24's reason: the
reviews answer different questions and no migration should be able to
disturb another's rows. It does **not** reuse `project_reviews`, which
its own roadmap entry named and migration 014 dropped on 2026-08-24.

The two rules every Tier 3 follows apply (commit the read transaction
before inference; give the model no numbers rather than instructing it
not to use them). Three more, each settled against the live tables:

1. **The alert delta counts distinct titles, never rows.** This
   repository has written down four times that `alerts` holds one row
   *per failed check* — `reliability.py`'s "123 rows for one internet
   outage", `SNAG-AGENT-002`, `SNAG-AGENT-005`'s 598,091 rows,
   `judgements.py` rule 1 — and had never applied it to a *count of
   alerts*, because nothing counted them. Measured across the two live
   comparison windows: **24 rows against 59,650**, a 2,485x fall, of
   which **59,200 share one title** and fell on a single day. The same
   windows hold **17 distinct titles against 39**, a 2.3x fall, which is
   the shape a reader recognises. Rows stay in `stats` as evidence —
   dropping them would make a week with many faults indistinguishable
   from a week with one loud one — and no sentence is written from them.
2. **A fall is refused when the monitor's own coverage fell**, which is
   `log_review.direction_phrase`'s asymmetry against a different
   mechanism. There the one-directional thing is read truncation; here
   it is agent-run coverage, and the logic is identical because a period
   the monitor did not watch can hide alerts it never recorded and can
   never invent one. So a **rise** is trustworthy at any coverage and a
   **fall** is not. Load-bearing rather than theoretical: the two live
   windows were observed at **17.01 %** and **96.33 %** of expected runs.
   **Both** windows are measured, because checking only the current one
   reports poor coverage on this box and still lets every delta through
   unqualified — the previous window is the complete one here.
   `coverage_confidence` imports `reliability.LOW_COVERAGE_FRACTION`
   rather than restating 0.5, so a review cannot call a window
   trustworthy while every score inside it says the opposite.
3. **Disk occupancy is deferred to the disk review by name.**
   `GET /api/files/review` already narrates occupancy, its direction and
   its projected threshold crossings into the **same** 06:00 briefing, so
   a second narrative is the second-owner defect this repository has
   found at six scales. `NARRATED_METRICS` is CPU, RAM, swap and load —
   which nothing else on this box narrates at all — and the disk figures
   stay under `stats['resources']['disk_evidence']` so the review remains
   auditable against the snapshots the disk review read. The fallback
   digest **names** the review that does cover it, because an omission a
   reader has to infer is one they will not infer.

**The route is under `/api/sysadmin`, not `/api/services`**, which is the
one place this tier departs from its three siblings' naming and the
departure is what keeps a guard honest. `/api/services` carries a test
asserting that no non-GET route exists anywhere beneath it — the promise
that the reliability score is not a control surface — so a
`POST .../review/generate` there could only ship by narrowing that test
to admit the route being added. The content agrees: three of the four
inputs are alert volume, resource anomalies and resource trend, all
already served from `/api/sysadmin`, and only the fourth is service
reliability.

**Three defects the live run found and no fixture would have**, which is
the fourth Tier 3 and the fourth time this has been the headline:

- **The model inverted the one sentence that must not invert.** Handed
  "The monitor was down for much of this period", dria-agent-a-3b
  published **"The machine was down for much of the week"** — an outage
  report about a box that was merely unwatched, in a review whose other
  sections describe genuine service outages. `confidence_phrase` now
  names the *monitoring service* and denies the inference in the next
  clause ("That says nothing about how the machine behaved"), and the
  re-run produced neither the inversion nor anything like it.
- **A conversational preamble reached the narrative verbatim.**
  `strip_markdown` removes formatting, not prose, so "I'll help you
  analyze the Linux workstation's health report. Let me break it down:"
  would have gone into the briefing. One clause in `REVIEW_INSTRUCTIONS`
  fixed it; a stripper was refused as a fifth heuristic to maintain.
- **The prompt dropped two faults the instant a third appeared.** Its
  first draft named only `unreliable`/`failing` services and fell back to
  the whole list when there were none, so `searxng` and `alfred-frontend`
  — both degraded, both with real outages — vanished at the exact moment
  `venture-chat` went unreliable. Every service that dropped out is named
  now and the **grade** does the ranking, which is what the model reads
  anyway and what the instruction block's cap already bounds.

`STEADY_FRACTION` is **invented and says so** (`NOISE_MIN_OCCURRENCES`'
and `flap_min_episodes`' status), and it is cheap to be wrong about
because it decides a *word* in a figure-free prompt while every figure it
describes is in `stats` and in the facts section regardless. The Monday
slot is **derived**: 06:00 is the briefing, 05:45 the disk review, 05:15
the log review, and 05:30 is `estate-manager-review.timer` — another
repository's generation on the same 24 GB card, verified with
`systemctl --user cat` rather than taken from the comment that asserted
it. So the chain grows at the front, to 05:00, keeping the 15-minute
spacing the existing three already assume is enough for one generation.

Two limits filed rather than implied. `SNAG-DOCS-004`: `log_review` and
`files.review` both document their prompt as "contains no digit by
construction" and both contain `1`, `2`, `3` and `150` from their own
instruction block — the claim was always about the *data* half, which
`tests/test_health_review.py::TestPromptIsFigureFree` now asserts for all
three by partitioning each prompt at its own `REVIEW_INSTRUCTIONS`.
`SNAG-CFG-002`: `schedules.review_hour`/`review_minute` had driven
nothing since the projects domain left, and the reload's classification
test could not see them, because a path nothing reads is not a path it
classifies. **Both leaves are gone (2026-08-30, Session 135)** —
`review_day_of_week` stays, read by all three weekly reviews, and its
name is generic because that is now accurate rather than vague.

**A check that answers the same way either side of its fix is not a
check**, which is what that closure is worth carrying for.
`check_review_schedule_unread` returned `match` whenever it found no
reader, and a deleted field has no reader — so it would have gone on
reporting *still holds* over a landed closure, indefinitely. The
regression guard is keyed on the **absence** of the fields instead, and
carries a second assertion that the three surviving `*_review_*` pairs
are present, because an empty intersection is satisfied by a model with
no fields at all. The rule generalises past this entry: a control must
be driven at a stand-in modelling the *fix*, not only at one modelling
the defect.

A **service name** is deliberately not filtered through the digit gate
`log_review` applies to a signature: a name is not a measurement, and a
service called `postgres15` would be deleted from the review entirely by
a gate that cannot tell the two apart. Empty population — 0 of 30
configured names carry a digit — so the rule is stated as policy rather
than dressed up as a measurement.
