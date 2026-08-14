# Handoff — 2026-08-14

## Next action

Run `sudo systemctl restart sysadmin.service` to deploy the SNAG-AGENT-006 dedup and the unit-sweep string fixes together, then confirm on the first run 60 seconds later that `agent_runs.details->'standing'` carries `judged` and `suppressed` and that no service or threshold alert has written a second row for a fault that was already open.

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

### SearXNG — pre-staged the same day, and still unchecked

The paragraph above stands as written: the trigger has still not fired.
Re-verified before touching anything — no searxng unit under either
`~/.config/systemd/user` or `/etc/systemd/system`, nothing listening on a
plausible port (the only 80xx listener is `llama-server` on 8080), no row in
estate-manager's port registry, no directory under `~/projects`, and the
estate's own item still unchecked. The owner asked for the sysadmin half to
be pre-staged anyway, having been told the honest cost first: **the entry
cannot be written**, because `url` and `port` are the deploy's to decide and
guessing a port is the one thing `services.yaml` exists to prevent.

**What pre-staging turned out to be worth is not the commented block.** The
block is in `services.yaml` beside `mosquitto` and carries every decided
field, but a comment does not fix the failure this item was written against —
*a unit ships and nobody notices* — because nobody reads a comment until they
already know. `tests/test_searxng_wiring.py` does: it skips while no searxng
unit exists and fails from the moment one does, so the red arrives on the day
the gap opens rather than at whichever session next reads `tasks.md`.

Three decisions in it worth keeping. The gate is the **unit file, not a port
probe** — a probe flips the gate off exactly when SearXNG is down, which is
the state monitoring exists for. It matches the substring `searx` rather than
`searxng.service`, because a container deploy names its unit
`podman-searxng.service` and a gate that knows one spelling fails open on the
other two. And **nine ungated tests drive the gate against a fake estate under
`tmp_path`**, because everything else in the file skips on this box and will
keep skipping until another repository acts — a gate that has never fired and
a gate that cannot fire are indistinguishable from outside, and the second is
worse than no test.

**Part 3 turned out to be enforced already, and part 1 turned out to be at
risk from the thing enforcing it.** The Session 26 unit sweep catches a
hand-written searxng unit unaided, classifies it `host`, and emits a snippet
that correctly omits `project:` — so the `project:` decision needs nobody to
remember it. But that snippet says `kind: systemd`, documented in
`sysadmin/units/recommendations.py` as *"this scan does not know the unit's
port"*, and a unit check passes a SearXNG that is running while every search
errors. Following the sweep's advice would therefore have *appeared* to close
this item while leaving the only check worth having unwritten. Filed as
`SNAG-UNITS-001` — the general case, since it applies to every future HTTP
service — and pinned for this one service by the guard.

Fixed in passing, same defect class as the item's own note about stale
`projects.yaml` wording: an `unmonitored` finding's `reason` read *"no
projects.yaml or config.yaml entry monitors it"*, naming two deleted files in
a string the operator reads. Four category docstrings in
`sysadmin/units/scan.py` and two in `agent.py` said the same and now say
`services.yaml`.

One number was incremented rather than audited: `snag_list.md`'s header prose
said *"Eight open snags … reports 13"* and now says nine and 14. A raw count
of unmarked entries under that heading returns 14 open, not nine — the prose
and the markers have disagreed since before this session, which is
`SNAG-ROADMAP-002` describing itself. Not corrected here; a +1 to whatever
the number meant is faithful, re-auditing the document is its own sitting.

## Blocked / waiting on

- **Deploy.** The daemon serves start-time code, so none of the SNAG-AGENT-006
  change is live until `sysadmin.service` restarts. Nothing else is required —
  no migration, no config change.
- **`judge_attention` against a populated payload**, unchanged from Session 45
  and now with one more negative observation behind it. Needs an eligible
  project whose stated next action has stood 7 days unchanged.
- **The tray toast**, the same gap Sessions 43, 44 and 45 all left.
- **SearXNG's deploy**, which is estate-manager's. Nothing here is left to
  decide: fill in the port, confirm the health path against the deployed
  version (upstream serves `/healthz`, venture's seam calls
  `/search?q=…&format=json` — neither taken on trust), uncomment the block,
  restart. `tests/test_searxng_wiring.py` goes red the moment the unit lands
  and stays red until that is done, so this needs no remembering.
- **Nothing** — but one note on how the estate record landed. Two
  estate-manager sessions were live while its `snag_list.md` was edited from
  here, and one of them **committed the entry itself**, as `86f67d8`
  alongside an unrelated SearXNG correction. Content verified intact
  afterwards (all seven bullets, filed `P3`). The risk was foreseen and is
  worth stating as a rule rather than an anecdote: **a doc change left
  uncommitted in a repository with live sessions will be committed by one of
  them, under a message about something else.** Write and commit in the same
  breath, or hand the text over and let the owning session place it.
