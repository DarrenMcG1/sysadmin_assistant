# Handoff — 2026-08-14

## Next action

Run `sudo systemctl restart sysadmin.service` to deploy the SNAG-AGENT-006 dedup, then confirm on the first run 60 seconds later that `agent_runs.details->'standing'` carries `judged` and `suppressed` and that no service or threshold alert has written a second row for a fault that was already open.

## This session

Three snags, taken as parallel workstreams. All three are done; one of them
turned out to contain bad advice, which is the part worth carrying forward.

### The two time-boxed checks from Session 45, taken and now closed

Both were only available this morning, so neither should be carried forward.

**The estate's timers fired** — scan 03:31 UTC and audit 05:03, both for the
first time. `scans_total` is 3 and the newest scan is `run_type: scheduled`
(it was `manual`), 26 projects, 0 parse failures, 0 skipped. So `estate_judge`
correctly stayed silent, and the hoped-for outcome — a first real judgement
raised off a stale scan — did not occur. **The agent has still never raised a
row in production.** Correct behaviour, and indistinguishable from a broken
one; nothing here re-proves it.

**`attention` is still empty**, this time *after* a real scheduled scan, which
was the precondition that made the check worth waiting for. That is a stronger
negative than the earlier ones: the payload is not empty merely because the
producer had never really run. `judge_attention` remains the one half of
`estate_judge` never exercised against real data.

### SNAG-AGENT-006 — the snag's own remedy was wrong

The entry said dedup and `RESOLVABLE_TITLE_PATTERNS` are mutually exclusive, so
the service and threshold families had to leave the tuple. **Following that
would have undone SNAG-AGENT-004**, which exists precisely because a set built
from configuration cannot contain a deconfigured service — `redis unreachable`
reached 6,283 immortal rows that way.

The mutual exclusion was true only of an exclusion set holding the titles a run
**raised**. `sysadmin/estate/agent.py` had already shown the third option and
Session 45's handoff named it: exclude what the run **judged**. Dedup
suppresses the raise, never the judgement — so a fault that persists is in the
protected set every run and is never swept, and a fault that clears leaves it
once and resolves once. **The patterns stayed.** The entry is flagged as
superseded in `snag_list.md` rather than quietly corrected, because the
superseded version reads as sound advice.

Three things found while making it:

- **`% auto-restarted` must not deduplicate**, and it is the only exemption.
  `_failure_counts` resets the moment `restart_unit` returns, so the title
  fires once per restart *cycle*; a second restart three hours later is a
  second piece of news. It is still judged, so the sweep leaves it alone.
  Carried as an explicit `dedup=False`, not a special case at the call site.
- **The recorded reason `collation` stays out of the sweep was itself wrong.**
  It said mutual exclusion. The real reason is that collation resolves its own
  rows by id and contributes nothing to the judged set. The old sentence was a
  correct conclusion drawn from a premise that has since moved — the dangerous
  kind, because the next person removes the guard when the premise changes and
  reintroduces the bug the real reason prevented.
- **Every side effect had to move above the raise decision**, and
  `_threshold_keys` was the one that would have broken quietly:
  `_check_anomalies` reads it to suppress a duplicate anomaly for a resource
  that already has a threshold row, so a suppressed raise that skipped the
  `add` would fire an anomaly for a resource whose threshold row was open.

Suppression is deliberately **not** folded into `raise_alert`: five families
already own their own lifecycles, and changing them all silently from one
override is the "second owner of one lifecycle" defect at a sixth scale — the
defect that produced this fix.

**Verified against the live database in a rolled-back transaction**, which was
necessary rather than ceremonial: the suite stands in for PostgreSQL's `LIKE`
with a Python matcher, so it cannot prove the patterns plus `NOT IN (judged)`
select the right rows in real SQL. Run 1 wrote; run 2 with the same fault wrote
nothing and resolved nothing (the flip-flop case); run 3 resolved on clearing;
run 4 re-raised. Ten sustained runs of one threshold fault left **1** row where
the old code wrote 10. Three auto-restarts left 3. Residue after rollback: 0.

**Two changes of meaning, stated rather than left to be discovered.**
`alerts_raised` in `agent_runs` now reads 0 on a run where a sustained fault is
still true — that is its intended meaning, but anything trending it will show a
step change at deploy, which is why `details['standing']` carries `judged` and
`suppressed` beside it. And a `critical` that fires once now genuinely fires
once: the volume that used to mask the absence of escalation is gone, making
these families the same shape as `SNAG-ESTATE-003`.

### SNAG-TRAY-006 — the design work was the vacuity, not the parse

A consumer-driven contract test: a recorded 8400 payload the suite always
parses, plus a reachability-gated live pair sharing one set of assertions so
the halves cannot drift. `estate-lib` was rejected — the two shapes are a
*tolerant consumer parse* and a *producer guarantee*, genuinely different jobs,
and one class would make the tray's defensiveness the producer's problem and
the producer's strictness a way for the tray to crash on an unknown field.

The trap is that **`from_dict({})` succeeds**: `extra="ignore"` plus universal
defaults means the obvious "does it parse" test goes green against a producer
that has stopped serving the routes' content entirely. So each half checks the
keys the consumer reads are present in the *raw* dict first.
`test_empty_payload_would_also_parse` pins that vacuity deliberately, as a note
to whoever is later tempted to simplify the module.

Found by diffing the real payload: `current["total_size_mb"]` arrives as an
**int** on the detail route and a float on overview — the column is `Integer`,
overview's `response_model=` coerces it, and `/api/projects/{name}` has **no
response model on either side**, so the raw value reaches the wire. Asserted as
*numeric*, not `float`; pinning the symmetry would freeze an accident of
serialisation and break the first time a size is fractional.

### SNAG-ESTATE-002 — recorded in estate-manager, fixed nowhere

Per its ADR-0002: a cross-repo requirement is recorded in the target repository
and executed there. Rejected: fixing it directly from a sysadmin sitting, which
crosses the boundary the ADR draws. The choice between publishing the two
properties as fields and deleting them with the "one place a nudge's title is
built" comment is left to that repository, with the argument for each recorded.

**It is filed there as `SNAG-ESTATE-010`, not `002`.** That repository already
has its own `SNAG-ESTATE-002` — a different, already-fixed defect — because the
ID scheme is per-repository. Do not quote the two interchangeably.

Reading the producer turned up three things the entry did not have, all
verified directly rather than taken on report:

- **The drift has already happened.** `Nudge.message` puts the action through
  `_shorten` at 120 chars; this side interpolates `next_action` whole. The two
  messages differ *today*, and neither side can see it.
- **`nudge_title` has no production caller in estate-manager at all** — one
  test reference and nothing else. The raise/escalate/resolve machinery it
  claims to serve stayed here at the Session 4 move.
- **Its justifying comment cites `_alert_title` in
  `estate_service.projects.agent`, and that symbol does not exist in that
  module.** The reasoning behind the claim left before the claim did.

That third point is the strongest evidence for the delete option, and none of
it was available when the snag was filed.

### Filed on the way

`SNAG-AGENT-007` — `_active_alerts` now runs four times per sysadmin run and
loads whole ORM rows. P3: it was already three, and the fourth caller is the
one shrinking the table it reads. Filed because it is the `SNAG-AGENT-005`
shape, where the same query pulled 593,814 objects and the fix fell over on the
backlog it existed to end. Not fixed mid-change: a titles-only projection costs
a second definition of "this agent's open rows", and splitting a shared query
in the same sitting as a lifecycle change makes both harder to verify.

### A delegated requirement arrived after this session's commit

`c890a52`, landed by a concurrent estate-manager session **after** `a472beb`:
**monitor SearXNG when the estate deploys it.** Documents only, 53 lines into
`tasks.md`, ADR-0002's pattern working — same shape as `fa51aac` the day
before. Verified here as documents-only with a clean tree; nothing it says
conflicts with this session's work.

It is **unactioned and correctly so** — its trigger is estate-manager
deploying SearXNG and claiming a port, which has not happened. Two of its
three parts are decisions that *block* that deploy rather than follow it,
which is why it was recorded before the deploy rather than after; the
`estate-manager-audit.timer` precedent shipped a unit that ran unmonitored
until this repository's next session. Noted here because the next session
reads this file before `tasks.md` and would otherwise meet it as a surprise.

Two of its findings were checked against `services.yaml` by its author and
agree with this side: `kind: http` polls whatever `url` says, so a service
without `/api/health` needs no shim; and SearXNG needs no `project:` id,
five entries already omitting one.

## Blocked / waiting on

- **Deploy.** The daemon serves start-time code, so none of the SNAG-AGENT-006
  change is live until `sysadmin.service` restarts. Nothing else is required —
  no migration, no config change.
- **`judge_attention` against a populated payload**, unchanged from Session 45
  and now with one more negative observation behind it. Needs an eligible
  project whose stated next action has stood 7 days unchanged.
- **The tray toast**, the same gap Sessions 43, 44 and 45 all left.
- **Nothing** — but one note on how the estate record landed. Two
  estate-manager sessions were live while its `snag_list.md` was edited from
  here, and one of them **committed the entry itself**, as `86f67d8`
  alongside an unrelated SearXNG correction. Content verified intact
  afterwards (all seven bullets, filed `P3`). The risk was foreseen and is
  worth stating as a rule rather than an anecdote: **a doc change left
  uncommitted in a repository with live sessions will be committed by one of
  them, under a message about something else.** Write and commit in the same
  breath, or hand the text over and let the owning session place it.
