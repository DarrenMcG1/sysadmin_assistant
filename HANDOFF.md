# Handoff — 2026-08-27

## Next action

Write the twenty-fifth check against `SNAG-ESTATE-006` — the last open entry for which a check is neither a restatement of an existing guard nor a measurement of the weather, and a live candidate rather than an exempt one because Session 102 measured its pre-staged test reading a fixture this repository recorded rather than the wire — by driving `GET :8400/api/audit/findings` for the published key set the way `check_nudge_wording_unpublished` drives the nudge surface, refuted when `code` appears among them, respecting the entry's **not worked around here** bullet by reading only published keys and never splitting `fingerprint`, which is this repository parsing an identity format the estate owns; and once that lands, decide whether `convention:unchecked` reaching zero should retire `SNAG-ESTATE-014` or whether an entry whose claim is a count of nothing is one to close, which is a judgement its own last bullet has never had to face.

## Session 102 is complete — the twenty-fourth check, and two judgements about being unchecked

`SNAG-SVC-001` is **checked and stays open**. Checked entries **21 → 22**,
unchecked **3 → 2**, open unmoved at **24** (none opened, none closed) —
measured either side of the edit by driving `load_entries`, and by
estate-manager's `read_snags`, which reads **93 rows / 24 open** both
times. Suite **2713 → 2731**, `tests/test_snag_claims.py` **309 → 327**.

**The first check whose claim is a conflict between two rules rather than
a fact about one.** Every earlier entry in this registry claims something
about one artefact; this one claims that two rules in this repository
point opposite ways — `GET /api/services/actions` answering a flap by
observing it less often, against `known_noise` rule 3's *volume is what
makes a fault worth looking at, not evidence it is harmless*. So the
check drives **both** sides and reports only whether the conflict is
still live. Which of the two honest resolutions to take is the owner's,
which the entry's fourth bullet says in writing, and a test asserts that
no note this check can emit carries an imperative.

### What the sitting settled

- **The contention is built, because the population is the weather.** The
  entry states its own population — zero on this box, `searxng` being the
  only all-single-check service at 2 episodes against a threshold of 3 —
  so a check that looked for the row would report the entry refuted on
  every day the box behaved and live the first afternoon a health path
  went slow. The subject is a fully-covered 7-day window carrying exactly
  `flap_min_episodes` outages of one 300s check each, built from **health
  rows** rather than from a hand-set `ReliabilityScore`: the narrowing
  rests on `_outage_episodes` dating an episode to its last *failing*
  check, and asserting `longest_outage_minutes == 0` by hand would be the
  check agreeing with itself.
- **Three instruments, and the structural one is what a fix cannot
  avoid.** The row's own `evidence: rate` and `0 points recoverable` is
  the producer's statement; the advice module's **import set** is the
  second resolution's shape, since a correlation between the blips and
  the service's own logs cannot be computed by a module that has not got
  the data, whichever file the fix lands in.
- **Rule 7's fifth and sharpest instance.**
  `service_recommendations.py` names `log_actions` twice in its module
  docstring, `log_trends` in `_flapping_row`'s and `known_noise` in the
  very docstring that filed this snag — so a grep reports all three as
  already wired and would refute the entry on the day it was written. An
  `ast` import walk sees none, because a docstring is an `ast.Constant`.
- **Three witnesses, because on each side a rule removed and a producer
  the probe cannot reach report identically.** A two-check episode must
  produce **no** advice row; a loud old flat signature **must** be noise;
  a signature below the floor must **not** be — the third being what makes
  the second mean anything, since "rule 3 still refuses volume alone"
  would otherwise be true of a rule that no longer looks at volume.
- **The narrowing going is `unknown`, not either verdict.** If both drives
  produce a row, the entry's headline claim is *more* true and its own
  third bullet false — "still live" understates it and "refuted" is
  plainly wrong. A check cannot rewrite the entry it measures; it can
  decline to grade one that has moved underneath it.
- **A third way for this entry to stop being true, which it does not
  anticipate.** `known_noise` rule 3 relaxing dissolves the conflict with
  nobody having touched the row this entry is about, so the note names
  which side moved — a fix and a dissolution must not read alike.
- **One falsification passed against deliberately broken code**, the sixth
  here and a new shape. `_is_noise_candidate` carries rules 3 and 4 in its
  docstring and is the obvious place to model "rule 3 relaxed"; a stand-in
  aimed there leaves the verdict at `match`, because `recommend`'s loop
  does `if trend.change is ChangeKind.NEW: continue` **before** the
  predicate is called and takes `SURGED` in the branch above it. The
  change-kind rule is stated by the loop *and* by the predicate's admitted
  tuple, which is `SNAG-DB-003`'s shape inside a module nobody had driven
  from outside. The check was right; only the stand-in was aimed at the
  wrong function, and both are pinned.

### The two judgements, and the one that a live read decided

- **`SNAG-ESTATE-006` may not declare itself *checked by another guard*,
  and the reason is the guard rather than the precedent.** Its
  "pre-staged rather than parked" bullet says
  `test_the_producers_code_never_reaches_the_wire` fails "on the day
  estate-manager adds the column". It cannot: it reads
  `tests/fixtures/estate_audit_findings.json`, a payload **this
  repository recorded**, so it fires the day somebody re-captures the
  fixture and is silent for ever otherwise. What it pins is that
  `judgements.py`'s docstring agrees with our own recording — a different
  claim, worth having. A coverage declaration would therefore have been
  true-sounding and false on its first use, which is the silent
  retirement `ops_claims` rule 1 exists to refuse.
- **So the claim was measured live instead, and it holds.**
  `GET :8400/api/audit/findings` publishes **11** keys per finding —
  `age_truncated`, `check`, `detail`, `fingerprint`, `first_seen_at`,
  `observed_at`, `runs_observed`, `severity`, `standing_days`, `subject`,
  `summary` — across 3 live findings, and `code` is not among them. Only
  reading the route says that; reading the guard does not. The entry is a
  **live candidate** for the next check, and the ranking that put it
  behind `SNAG-SVC-001` on "a check would restate an existing guard" is
  refuted: the two would measure the fixture and the wire.
- **`SNAG-ESTATE-014` may not declare itself *unmeasurable by rule*
  either, and the refusal costs it nothing.** Its claim *is* the count
  `convention:unchecked` publishes, and that finding names it every
  sitting — being counted is what its own second bullet argues is the fix
  for invisibility. It would also be the first user of the category to
  subtract itself from its own subject, and would give the number a
  fourth way to move on top of the three it has already catalogued. The
  machinery had refused the weaker form of this once already, rejecting
  `<!--check:none_yet-->` within a minute.
- **The rule both judgements settle, so a later sitting does not
  re-derive it**: a declaration may move an entry between **published**
  buckets and may never remove it from the report — `ops_claims` rule 1
  at the level of the register. A `covered-by` bullet is legitimate only
  when the machinery *resolves the named guard*, exactly as
  `check_markers` refuses a marker naming no check, **and** the entry
  stays named every sitting in a category of its own, so `unchecked`
  falling by one shows up as `covered` rising by one. Left unbuilt: this
  sitting was asked for the judgement, and one live candidate is not
  enough population to design a category against.
- **A drift found while measuring, and filed rather than corrected line
  by line.** `SNAG-ESTATE-014`'s running series stops at Session 92 and
  reads 12 unchecked where the box reads 2, because Sessions 93–101 each
  wrote a check and none came back to the prose. That is the entry's own
  argument arriving at its own body: its second bullet says the live count
  is `convention:unchecked`'s to publish, so a total kept in prose beside
  it is a second statement of one fact that can disagree.

### One thing this sitting found and did not act on

**`SNAG-ESTATE-004`'s check went RED during this sitting's postflight.**
`check_default_port_uncontended` reports **refuted**: estate-manager's
audit now files `claimed_tool_default` for all five probed defaults —
3000, 5000, 8080, 8888, 9000 — which is the enforcement the entry says
nobody provides. Their live population is one row today, 8080
(`venture-assistant`). It is **recorded and not closed**: closure is a
judgement, this document's own convention says a red line in that family
is news rather than a fault, and a check leaves the registry with its
entry, which is a second decision nobody asked for in a sitting spent on
a different one. The record is in the entry itself, dated, so the next
sitting does not have to notice it twice.

### Deploy

`sysadmin` restarted at **16:21:13** — for the eighteenth sitting running,
nothing the daemon imports moved (`sysadmin/snag_claims.py`, one test file,
two documents), and the restart was taken because `check-ops-claims.sh`
compares the daemon's start against the newest source mtime and cannot know
that. All ten ops claims green afterwards; ruff and mypy clean; 2,731 tests.

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
`alerts` holds **1** unresolved row, the standing `info: Weekly disk
review ready`. A `warning: Unusual CPU usage` was raised at 15:48:28 by
this sitting's own full-suite run and **resolved itself within the
hour**, exactly as the block said it would — so `check-ops-claims.sh`
caught STATUS.md still asking for two, which is `SNAG-ESTATE-008`'s
founding case arriving against the document that records it. Another session committed `services.yaml` in this tree
at 15:40 (Alfred's five-minute evaluator timer) and left these files
alone.
