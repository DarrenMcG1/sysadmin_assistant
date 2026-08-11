# Handoff — 2026-08-11

## Next action

Run `sudo systemctl restart sysadmin.service` so the daemon stops serving the pre-envelope briefing — it currently answers `/api/sysadmin/briefing/preview` with 25 Project Health rows and no `facts` block — then take Session 39, the watcher escalation ladder, whose scope, two decisions and two blocking constraints are already written into tasks.md.

## Session 36: the briefing envelope, and half of it was already built

`GET /api/sysadmin/briefing/preview` now carries `schema`, `period`,
`summary`, `alerts[]` and `facts{}` alongside the `sections` and
`generated_at` it always had.

Three of the session's six checkboxes had landed on 2026-08-08 as Session
35 Phase 5 — `estate.json`, `last_code_commit` and the atomic write — and
were verified in the code rather than taken from the notes before being
ticked. What remained was the envelope, the prose over it, and one
question that turned out to be the interesting part of the session.

## The delivery decision, taken before any code

Alfred's `adapt_sysadmin` reads `payload["sections"]` and returns a single
red error section if that key is absent, and reads `generated_at` into
`produced_at`. The envelope as specified had **neither** — it named
`generated` and listed no `sections` — so shipping it literally would have
replaced Alfred's whole Infrastructure group with one error box every
morning, in a separate repository with its own ADR governing the contract.

**Additive, and it is not a compromise.** The spec's own sentence settles
it: "prose is what Alfred surfaces; `facts` is the deterministic input the
prose was written from". `sections` *are* the prose. Alfred owns the
section contract (ADR-0063) and normalises producers into it; this service
owns the envelope round it, and both stay true at once.

**Rejected**: an envelope-native second endpoint with `/preview` frozen —
two payloads where one gets updated is the exact drift this repository has
filed three snags about; and a breaking change with a coordinated Alfred
edit — two repos in one sitting, digest red between deploys.

**No `generated` key was added beside `generated_at`.** Two stamps holding
the same value are a fork waiting to happen, and the existing name is the
one a live consumer already reads.

## Checkbox 6 was a measurement, and it found the hole

"Confirm Alfred enforces staleness on `generated`."

It does. `_producer_timestamp` carries the stamp into `produced_at`, and
`DigestSection.vue` flags a producer whose payload predates digest
composition by more than 12 hours. Correctly implemented, and **it can
never fire for this service** — because Alfred *pulls*, and
`generate_briefing_data` stamps `datetime.now(UTC)` at request time. The
stamp says when the phone was picked up. It says nothing about the age of
the data recited into it: a service whose organiser died three days ago
serves a payload one second old containing three-day-old projects.

That is the pull-versus-push asymmetry. For a pushed artefact, generation
time and measurement time coincide and one stamp serves both. For a pulled
one they diverge silently, and the consumer's freshness check quietly
degrades into a liveness check on the HTTP handler.

So every `facts` block carries its own `measured_at`,
`facts.stale_sources` names anything measured more than 26 hours ago, and
`summary` states it in a sentence. **It caught one on the first live run**:
`filesystem` last measured 2026-08-06, five days stale — and independently
corroborated by an open `file_organiser agent stalled` alert sitting in the
same payload. Two routes to one fact is the argument for the field.

## Decisions taken, and what was rejected

**`period` is anchored to the schedule, not the last pull.** "Since the
previous briefing" has no anchor on a pulled route: two consumers polling
would each shorten the other's window, and storing a row per pull turns the
endpoint into a pull log and needs a migration. `schedules.briefing_hour`
already declares the cadence, so the window runs from the most recent 06:00
boundary — one meaning for every caller, no storage, no table.
`anchor: "schedule"` is in the payload because the other reading is the one
a consumer would otherwise assume. The stored-history alternative was put
back to the estate owner and is still available if a real diff of
consecutive briefings is ever wanted.

**`summary` is deterministic.** Chosen over LLM narration: the two weekly
reviews are narrated and pay for it with a figure-free prompt, a
deterministic facts prepend and a markdown stripper, because the 3B model
restates numbers it was told not to. A summary made *only* of numbers has
nothing to gain from any of that, and a 06:00 path has llama-server being
down to lose.

**`facts` is a projection, not a copy** — counts and identifiers, never the
rows the sections render. A facts block containing the whole payload cannot
be diffed, which is the only reason the block exists. A test asserts every
list inside it holds scalars.

**Both project sections now read one query and one filter.** They were
issuing the same `latest_snapshot_query` separately, differing only by an
`ORDER BY` Python does for free — two reads of one table in one payload,
which is also two chances to disagree, which is precisely what
SNAG-BRIEF-001 was.

## The two snags underneath, and why they came first

The snag list argued the ordering itself: *"building a briefing envelope on
top of wrong data only makes the wrong data better formatted."*

**SNAG-BRIEF-001** — Project Health published every project ever scanned:
26 rows including work retired in July and four near-duplicate casings of
one repository, while "Pick This Up" in the same payload listed 5 and the
board returned 6. Now `status == "active"` (the line the board and
`/api/projects/next` both draw), ordered **ascending** because descending
plus a cap shows exactly the rows carrying no information, capped at 5,
with `facts.projects.omitted` reporting the cut. Live: **26 rows became
5**, and the two sections agree by construction rather than by matching
filters.

**SNAG-BRIEF-002** — a bare `[:180]` slice cut a next action mid-word with
nothing to say so. `truncate_at_word` now lives in `sysadmin/core/text.py`:
word boundary, and **always** the marker `… (truncated)`, deliberately the
same string Alfred's own `sanitise_text` appends so a cut made either side
reads identically. The cap is documented rather than anonymous. It was
**not** moved upstream into `roadmap.next_action_from_handoff`: the board
serves the field uncapped on purpose, so capping at source would shorten a
surface that had no defect.

## What it says about this estate

The alert grouping had to be built to make `alerts[]` readable at all, and
what it measured is the case for the next session: **599,794 open alert
rows across 21 incidents**, 557,832 of them warnings. One unresolved
`Log error: kernel` accounts for most of it. Grouping by incident in the
envelope is a workaround sitting on top of `SNAG-AGENT-002`, which is Tier
1 of Session 27.

## Blocked, and left open on purpose

- **Nothing consumes the new keys yet.** Alfred is unchanged and unaffected
  by design; whether it should read `facts.stale_sources` instead of
  relying on `produced_at` is a question for Alfred's side, and Session
  30's fate says to ask before assuming a consumer wants something.
- **`facts.stale_sources` reported a real problem it did not cause**, and
  the follow-up measurement made it worse than it looked: `agent_runs`
  holds **one** `file_organiser` row, ever, against `log_aggregator`'s
  31,431. Filed as `SNAG-AGENT-003` and deliberately not chased here —
  a scheduler that never fires and an agent that dies silently need
  opposite fixes, and nothing recorded has ever been a failure. The
  second half of that snag is that a `file_organiser agent stalled`
  alert had been open since 2026-08-10 and nobody read it; detection was
  never the missing piece.
- **The 180-character cap and the board's uncapped field are now a
  documented disagreement** rather than an accidental one. If a consumer
  ever needs the full action in a briefing, the fix is to raise the cap,
  not to remove the marker.
