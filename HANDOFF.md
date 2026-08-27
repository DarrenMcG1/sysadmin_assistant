# Handoff — 2026-08-27

## Next action

Write the twenty-fourth check against `SNAG-SVC-001` — the last of the three unchecked entries for which a check is neither a second statement of an existing guard nor a measurement of a population — by reproducing the mechanism its own narrowing describes (a `check_interval` row can fire only when every episode lasted a single check, so the contention is built rather than looked for) and reporting only whether the conflict with `known_noise` rule 3 is still live, never which of the two honest resolutions to take, since the entry's own body says that is the owner's; and then decide, as a judgement rather than a build, whether `SNAG-ESTATE-006` and `SNAG-ESTATE-014` can declare themselves *checked by another guard* and *unmeasurable by rule* without that becoming a way to retire a check in silence, which is `ops_claims` rule 1's warning one document over.

## Session 101 is complete — the twenty-third check, and a symptom that agrees with itself only in summer

`SNAG-ESTATE-007` is **checked and stays open**. Checked entries
**20 → 21**, unchecked **4 → 3**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **24 open** both times. Suite
**2682 → 2713**, `tests/test_snag_claims.py` **278 → 309**.

**The fifth check across a repository boundary, the second whose subject
is what another repository _publishes_, and the first where the fix could
land in three places.** The entry's cause bullet names one — the queue
pool's missing `connect_args={"options": "-c timezone=utc"}` — and the
surface would equally stop stamping local if `invariants()` or the
route's serialiser normalised. So an `ast` walk for that kwargs entry
reports *still holds* for two of the three; all three are driven as real
stand-ins. What is read is the **string on the wire**, taken by calling
the route object mounted at the queue's published path, which reaches the
private serialiser without ever naming it.

### What the sitting settled

- **The obvious instrument agrees with itself only in summer.** The entry
  quotes one rendered offset and `Europe/London` renders `+00:00` from
  late October to late March, so a one-instant check reports this entry
  refuted every winter and true again every spring, having measured the
  calendar. Two instants six months apart go through every surface and
  *stamps UTC* means **both** came back at zero — a property of the
  connection rather than of the month.
- **The cause is driven rather than read, and the same reading validates
  the stand-in.** `pg_settings.source` is `client` when the connection
  asked, which is exactly what the proposed fix produces, and
  `configuration file` when it inherited the cluster's — separating
  *their fix landed* from *the box's default moved to UTC*, which renders
  identically and leaves the mechanism intact. It is also what makes
  pointing their pool at **this** repository's database legitimate: a
  configuration-file source is cluster-wide, and a `database` or `user`
  source says it is not and stops the check answering.
- **Nothing of the estate's is opened.** `create_pool` is a factory
  taking a DSN, so it takes ours; the lease lives in a `TEMPORARY` table;
  `UserSystemd` gets a runner that raises. Estate rule 1 forbids one
  application reading another's database, and a check running at both
  ends of every sitting would be the most regular breach of it on the
  box.
- **Its population is empty by construction**, rule 1's shape for the
  fourth time. `active_lease` is re-read live every run as *evidence* and
  never as the verdict — a check waiting for a granted lease measures
  whether somebody is holding the GPU this afternoon.
- **The complaint and the premise are reported apart.** The sibling
  engine ceasing to stamp UTC is this entry dying at its premise, and a
  single boolean would file a deleted guarantee as a job well done.

### Two stand-ins corrected the check, and one falsification passed

A route that normalises above a still-local connection was read as *the
box's default moved*: the draft asked whether `invariants()` had handed
UTC up, where the question is whether the **connection** is in UTC — and
`zone_stamps_utc` now resolves the reported zone name rather than
comparing it to the string `UTC`, which `Etc/UTC` refutes. And a surface
publishing only `granted_at` satisfied *every offset is zero* through
`Europe/London`, which is the seasonal defect arriving by a dropped field
instead of by the calendar.

The falsification that passed is the fifth here and, unlike Session
100's, was **not** a gate to delete: removing the completeness half of
`stamps_utc` broke nothing because the verdict body refuses an incomplete
reading one gate earlier, but `complete` is defined once and consulted
twice, so it is not two statements of one fact — and the property is
public and would otherwise answer *yes, UTC* about a surface only ever
asked about January. The gate stayed and the observation moved to the
property, where it is reachable.

### One red arrived from another repository

estate-manager added a `1883` row to their port registry today under
their ADR-0054 — the shared MQTT broker, deliberately outside the ranges
this repository audits and recorded as their `SNAG-ESTATE-070` — and
`test_our_parser_and_the_estates_agree_on_the_live_document` pinned the
accepted-unaudited set at `[22000]`. Widening our ranges is their
decision to ask for, so the expectation is corrected and the reason
recorded beside it. Filed as friction (`9ed50215`) with the cost stated:
their row records that nothing checks it, and does not record that a
consumer pins the set, so a correct row is a breaking change downstream.

### State of the box

`sysadmin` restarted at **2026-08-27 15:50:48**, `/health` **200**,
`alembic current` **016** at the packaged head. `check-ops-claims.sh`
green on all nine claims; `check-snag-claims.sh` reports all twenty-one
checked entries still holding and names the three that carry no check.
`alerts` holds **2** unresolved rows — the standing `info: Weekly disk
review ready`, and a *fresh* `warning: Unusual CPU usage` raised at
15:48:28 inside this sitting's full-suite run, its predecessor having
resolved when the previous sitting's load fell away. Named rather than
resolved by hand, because `_check_anomalies` resolves it by id when the
condition clears. Another session committed `services.yaml` in this tree
at 15:40 (Alfred's five-minute evaluator timer) and left these files
alone.
