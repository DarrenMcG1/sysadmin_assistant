# Service reliability — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

`GET /api/services/reliability` (Session 25, Tier 1) scores the *services*
— the third scorer, after the repository scoring that moved to the estate
on 2026-08-13 (ADR-0005) and the
file organiser's disk. Score is `100 − downtime − instability`, both
individually attributable:

- **downtime** = `round(100 − uptime_percent)`, capped at 60
- **instability** = 5 per outage *episode* from the first, capped at 25

They are separate terms because they are separate failures. Live proof
on this estate: `internet` lost only 7.5 % of its checks but across three
incidents (−15 instability, −8 downtime), while `venture-assistant` lost
27 % in one sustained outage (−27, −5). Retry logic survives one long
outage and dies on three short ones, so a repeated failure must not
outrank a longer single one merely because it was up more of the time.

Four things this endpoint does differently from its siblings, each
learned from the live data rather than assumed:

1. **Computed live, never read back.** `/api/units/status` serves the
   latest stored sweep; this recomputes on every request (~28 ms for the
   whole estate). A stored score would be up to 24 h stale and would 404
   before the first nightly job. The `reliability_scores` table is
   history for trending, written by the 02:00 cron —
   deliberately an hour *ahead* of the 03:00 retention purge so the day's
   score is written before the checks behind it can be deleted.
2. **Incidents come from `service_health` transitions, not `alerts`.**
   The session plan named `alerts`; that table records one row *per
   failed check* — 123 rows for one internet outage, 81 for one
   `venture-assistant` outage — so mean time between alerts would measure
   `health_check_interval_seconds`. Consecutive non-ok checks collapse
   into one episode by construction, and it avoids a join on the
   unindexed `details->>'service_name'`, the only link `alerts` has to a
   service.
3. **Restart frequency is absent, though the plan named it.** Nothing
   records restarts: `systemctl show -p NRestarts` is a live cumulative
   counter never sampled into the DB, and `agent_runs` records agent
   executions. Three measured metrics beat four where one is invented.
4. **A gap in the series never costs points.** It means the *monitor* was
   down — deducting would charge the service for this application's
   downtime — so it lowers `confidence` instead. `confidence: low` means
   under 2 days of history or under 50 % of expected checks; anything
   recommending action off this endpoint must read it. Ordering ignores
   it on purpose: a thinly-observed failing service is still the most
   interesting row on the page.

The population is **the configured services**, not the distinct names in
`service_health`. Both differences matter: retired services (`ollama`,
`personal-assistant`) keep rows for 30 days and must not be scored, and a
service just added to config.yaml has no rows at all — which is a
finding, not an absence, so it is scored 100 at low confidence rather
than omitted. An expected-down service (`mute: true`, **or** listed in
`notifications.tray.mute_services` — the only way to mark one contributed
by projects.yaml, since those entries have no `mute` field) has its
deductions computed and reported with `waived: true` but not applied.

**The services scorer had an advice half at last, and building it found
the score itself wrong by 60 points a service** (Session 78, Tier 2).
`GET /api/services/actions` is the fourth sibling of `/api/files/actions`,
`/api/logs/actions` and `/api/units/actions`, and
`sysadmin/monitor/service_recommendations.py` is its pure module. The
currency is **recoverable points**, straight off `Deduction.points` —
which is why this endpoint has a real one where `UnitRecommendationInfo`
deliberately has none.

**`skipped` was being scored as an outage, and only the advice endpoint
made it loud.** `services.yaml` declares `monitor: false` on three
services that are inactive by design; the agent writes those checks as
`skipped`; `score_service` excluded only `error` from its rates, so a
`skipped` row counted as measured-and-not-`ok`. All three scored **35**
and graded `failing` off 307 checks nobody had taken, from Session 25
(2026-08-07) until 2026-08-25. Live either side of the fix: **6 rows and
213 points → 3 and 33**, `failing` 3 → 0, mean 92.1 → 98.6, with 180 of
those points and every one of the endpoint's `risk` rows fabricated.

Five rules, four of them the opposite of the obvious implementation:

1. **Neither obvious reading of `skipped` is right, and the sibling rule
   does not transfer.** `SysAdminAgent._resolve_recovered` treats it as
   *healthy* — correctly, because an open critical nobody will look at
   again is a pile-up wearing a declaration as an excuse — but that
   decides whether to close an alert. Importing it here fabricates a
   **100** exactly as scoring it down fabricated a **35**. It joins
   `error` in `UNMEASURED_STATUSES` and `confidence` carries the truth:
   `ports_checked`'s rule, zero-because-blind never served as
   zero-because-clean. `skipped_checks` is counted apart from
   `error_checks` (migration 015) because "the check failed" and "nobody
   looked, by choice" are different claims with opposite remedies —
   `UnitFinding.enabled`'s trap, already paid for once.
2. **The confidence gate is asymmetric, or the endpoint ships empty.**
   All 30 services read `confidence: low` on the build day: the box was
   off 2026-08-18 → 08-22 and `SNAG-DB-005` killed the daemon a further
   22 h on 08-23, leaving `observed_days: 1.07` at `coverage_percent:
   15.13`. A `confidence == "high"` gate is the obvious implementation
   and is `SNAG-LOG-002`'s measured-empty population for the **third**
   time. The way out is what each row *argues from*, because a gap is
   one-directional — it can hide an outage and never invent one. So
   `outage`/`flapping`/`timer_failed` are floors under their own claims
   and survive a thin window; `check_interval`/`timer_stale` argue from
   a rate or an absence and require `high`. `log_trends.py` rule 4's
   `NEW` asymmetry, one domain over. `suppressed_by_confidence` counts
   what was withheld, so "nothing to do" and "we could not tell" stay
   distinguishable.
3. **The currency differs from its siblings in *tense*, and that is said
   on every row.** Reclaimable megabytes are freed when the duplicate is
   deleted; reliability points are charged for failures already inside
   the window and lapse only as those age out. So `recoverable_points`
   is a forecast — "what stops being deducted once the fix has held for
   `window_days`" — and each points-bearing `detail` says so in words.
   `FileRecommendationInfo`'s argument extended: a field whose *unit* is
   decided by the producer is unreadable at the call site, and so is one
   whose tense is.
4. **Timer staleness parses no clock**, because the obvious approach
   rebuilds `SNAG-LOG-009`. `service_health.details['last_run']` is
   systemd's `LastTriggerUSec` rendered as a **local wall clock with a
   zone abbreviation** — ambiguous between zones, two instants at an
   autumn fold. The token is treated as **opaque** and compared only for
   inequality; the clock is `checked_at`, a `timestamp with time zone`
   this application wrote itself. Live, that derives **24.0 h** for all
   five daily timers, `alfred-evaluate-timer` included despite 15 holes
   in its series. A hole under-reports staleness rather than
   over-reporting it — a fire before a gap is observed at the first check
   after it — so the failure direction is silence.
5. **The cadence has its own lookback and a 7-day window cannot hold
   one.** `timer_lookback_days` is 30 and deliberately not
   `reliability.window_days`: `estate-manager-review-timer` is weekly, so
   the scoring window observes **one** firing and therefore zero
   intervals, and a staleness rule built on it would be structurally
   blind to every weekly timer here. A gap-spanning interval is never a
   cadence sample — it measures the outage, not the schedule.

`timer_stale_multiplier` is **derived by reuse**: it is
`self_monitor.stall_grace_multiplier`'s 3.0, for that field's own
argument — a schedule that has missed one firing is merely late and
clears on the next tick. `flap_min_episodes` is **invented and says so**,
`NOISE_MIN_OCCURRENCES`'s status stated the same way.

The module is named `service_recommendations` rather than
`service_actions` because **the collision was real**: "service action"
already means start/stop/restart here, and `tests/test_service_actions.py`
has covered `POST /api/sysadmin/services/{name}/{action}` since the
tray's Phase 3. Two of the three siblings use `recommendations` anyway.
The route keeps `/actions`; only the module moved. GET-only and always
will be, asserted by a test, for `units/router.py`'s reason.

Two costs filed rather than implied, both at the owner's explicit
direction to build `tasks.md`'s scoped examples as written and record the
conflict rather than decide it. `SNAG-SVC-001`: advising a longer check
interval is advising that a fault be *seen* less often, which is
`known_noise` rule 3's opposite — narrowed so it can only fire when every
episode lasted a single check, and worded to refuse a remedy, which is a
narrowing and not a fix. `SNAG-SVC-002`: `timer_stale` asks `stalls.py`'s
"has it run?" about a timer rather than an agent, with no ladder and no
cross-reference — disjoint populations today only because no agent on
this box is a systemd timer, which is a property of the box and not of
the design.

**What the tests were doing is the part worth carrying.** The whole suite
passed either side of the `skipped` fix, so a wrong score was not merely
undetected but untestable-by-omission. And **two of eight falsifications
passed against deliberately broken code**: the `waived` test set
`muted=True`, so the muted skip returned before the filter it named was
ever reached, and the cadence test passed one firing where it claimed to
test two. A third — the episode-count assertion — passes against the
broken scorer for the wrong reason, since a `skipped` row also failed to
split an episode by counting as *down*. All three repaired, plus an
invariant test pinning `reliability._deductions`' `waived=muted` at its
owner, since this module leans on a fact another module holds.

**One fault occupies one row, and the entry asking for it had measured
half of its own population** (Session 149, `SNAG-SYSD-006`).
`recommend` runs `_service_rows` over every scored service and
`_timer_rows` over the subset that are timers, so a `kind: timer`
service is in **both** loops; once `SNAG-SYSD-005` let a failed job
reach `service_health.status`, `GET /api/services/actions` served
`alfred-career-mail-timer` twice — `outage` at 6 recoverable points
beside `timer_failed` at 0, one fault named twice. `group_faults` and
`_folded_row` are `log_actions.group_incidents`' treatment applied to a
relation with no clock and no systemd graph in it. Live either side:
**8 rows → 6**.

Six rules, four of them the opposite of the obvious implementation and
two of them settled by controls belonging to a different entry:

1. **The key is the service plus `EVENT_ARGUED`, and the entry's own
   scope was the smaller half.** It describes a timer collision;
   `venture-chat` had been serving `outage` 26 beside `flapping` 25
   since the endpoint shipped on 2026-08-25 — **eight days**, one
   service named twice, no timer in it. Reading the entry finds one
   instance, running the endpoint finds two. `RATE_ARGUED` rows never
   join: `check_interval` and `timer_stale` argue about how a service is
   *watched*, which `KIND_ORDER`'s docstring already separates, and
   fixing the service lapses neither.

2. **That narrowing was decided by a live control, not by taste.**
   `snag_claims.check_check_interval_looks_away` finds its row with
   `next(r for r in recommendations if r.kind == "check_interval")` — a
   **top-level** scan — and its synthetic subject produces exactly
   `flapping` + `check_interval`. The obvious "one row per service"
   makes that `None` and reports `SNAG-SVC-001` **refuted** by a change
   with nothing to say about it: a landed fix for one entry deleting
   another entry's instrument. Its third limb reads this module's
   **import set** as the instrument for *"the advice has the service's
   own log data now"*, so reaching for `group_incidents` by *importing*
   it refutes the same entry from the other side. The treatment is
   therefore applied and the module is not imported, pinned by an `ast`
   walk — a docstring mention is an `ast.Constant`, and this module
   names `log_actions` in prose four times. Driven by stash before and
   after: all 18 checks report `still holds`, unmoved.

3. **Points are summed, and the invariant is what decided it.** Every
   member shares one currency and one subject, so the sum is the
   service's applied deductions — exactly `100 - score` — and one fix
   lapses them together, which is the honesty
   `_incident_recommendation` says summing would *not* have across
   kinds. It is also what keeps `total_recoverable_points` **invariant**:
   78 before and 78 after, where an anchor keeping its own share alone
   would have reported the same box at 53 on the day the list got easier
   to read. `members` carries the anchor too, so the figure decomposes.

4. **The anchor is `KIND_ORDER`'s first surviving kind, doing one job
   rather than two.** That constant already answers "which claim is more
   urgent to read" for rows tying on points; which claim leads a fold is
   the same question. Cause-first anchoring was put to the owner and
   refused — `timer_failed` genuinely causes the checks the `outage` row
   is computed from, which is `group_incidents`' anchor rule read
   literally, but it needs a declared cause-to-consequence pairing this
   module has not got and would put the summed points on the row whose
   evidence did not compute them. `SNAG-SVC-003` is the cost, filed
   rather than implied: for a timer fault the anchor's step names a
   *restart* the swallowed row's own detail explains cannot help.

5. **The title stays the anchor's, where an incident row's does not.**
   `_incident_recommendation` rewrites its title because its members are
   *other units*; every member here is about the **same service**, so
   the anchor's sentence already has the right subject and appending a
   count to it is the count-that-names-nothing `SNAG-ESTATE-001`
   removed. What is named is named whole: each swallowed finding's kind,
   title, detail, action and points, in `members` **and** in the folded
   `detail`, because the steps differ in kind and cannot be merged the
   way six `journalctl` invocations can.

6. **Nothing is capped and it cannot need to be.** A service has at most
   three `EVENT_ARGUED` rows, so a fold names at most two members — the
   roll-up that cannot name what it swallowed is unreachable by
   construction rather than by a threshold, which every other roll-up
   here needed.

**Two of the six are vacuous, in opposite directions, and both say so.**
*Loudest-rung-wins* is implemented and cannot currently lose: `outage`
is the only `risk`-capable kind and is `KIND_ORDER`'s first, so the
anchor is always at least as loud as what it swallows — a proof about
today's five kinds that a sixth invalidates in silence, so the rule is
written and a test pins the coincidence. *Gate-before-fold* is
**unobservable**: driven both ways on one low-confidence subject the
output is identical, because rule 1 makes the suppressible set and the
foldable set disjoint — so the test pins the **disjointness that makes
it vacuous** rather than an ordering nothing could distinguish.

**The fix had to land twice, because a consumer flattened it back.**
`health_review._service_facts` projects `title` and `action` — both the
**anchor's** — into the weekly review's `top`, so the first version
named one finding and never told the reader the other existed: the
roll-up that cannot name anything, rebuilt one consumer downstream of
the fold that promised not to. `stands_for` carries the swallowed titles
through, keyed on the **kind** rather than on position, so it is not a
second statement of how `group_faults` sorts.

**Two of eleven falsifications passed against deliberately broken code.**
Anchoring by points instead of `KIND_ORDER` broke nothing, because the
live specimen cannot discriminate the rule — `outage` leads
`KIND_ORDER` *and* carries all 6 of career-mail's points — so a subject
with 1 point of downtime against 25 of instability had to be added
before the anchor rule was tested at all. And emptying the review
projection's `stands_for` passed cleanly, because the digest test
injected the field into a fixture and therefore pinned the renderer
while saying nothing about the projection that fills it; it drives the
real `recommend` at the folding shape now.

**That consumer had a second fact to flatten, and the question was
whether to read it or work it out again** (Session 155,
`SNAG-SVC-004`). `SNAG-SVC-003` let a `timer_failed` member's step
supersede the anchor's, and `_folded_row` rule 5 wrote *whose* step is
leading into the folded `detail` — which this projection does not carry,
so the review printed one finding's remedy under another finding's title
and nothing said the subject had changed.
`ServiceRecommendationInfo.action_from` is that fact as its own field:
the promoted member's `kind`, empty when the step is the anchor's own.

Four rules, three of them the opposite of the obvious implementation:

1. **`stands_for`'s treatment is a *derivation*, and copying it
   literally would have been the defect.** That field is
   `m.title for m in members if m.kind != r.kind` — a restatement of
   what *swallowed* means, which is structural and cannot disagree with
   the producer. The same shape here is
   `next(m.kind for m in members if m.kind in STEP_SUPERSEDES)`, which
   restates which member **won**: a judgement `_folded_row` already
   took, free to drift the day that tuple widens. `SNAG-DB-003`'s
   shape, and `judge_queue_invariants`' *"the mask is read, never
   recomputed"*. So the producer publishes it (`_folded_row` rule 6) and
   every consumer reads it. One mutation is exactly the recomputing
   projection and exactly one test is red on it.
2. **Empty is deliberately *not* `ports_checked`'s not-knowing.** The
   field reads `""` both for a row whose step is its own and for a
   producer that does not publish it at all. Every other absent-vs-present
   collapse in this repository hides a *blind* reading; this one cannot,
   because both spellings mean "render nothing extra" and no consumer
   can act on the difference. So the renderer gates on truthiness alone
   rather than on `action_from != kind`, which would restate the
   producer's rule and print `The step is the  finding's` for an
   unfolded row.
3. **Spelling it as the row's own `kind` was refused**, which is where
   Session 128's *"uniform on every row"* does not transfer: that rule
   is about a `details` **key** whose presence is the only signal, and a
   pydantic field is always present. The uniform-scalar version fires
   the renderer's clause on every folded row and makes every consumer
   compare two fields to learn nothing — `stands_for`'s empty list is
   the right analogue, not a value.
4. **The refused fix is pinned rather than merely avoided.** Projecting
   `detail` carries the provenance *and* every swallowed row's own
   detail and step into the blob the review is built from, so a test
   asserts `detail` is absent from the projection.

**Both fold shapes were live at the moment of the fix**, which is the
discrimination a specimen of one could not have supplied:
`alfred-career-mail-timer` (`outage` + `timer_failed`) reads
`action_from: "timer_failed"` and `venture-chat` (`outage` + `flapping`)
reads `""`, because `flapping` promotes nothing. The entry had described
the live line as *reading correctly by luck of one string* —
`_timer_failed_row`'s step happens to explain its own subject — and it
now says so in its own words instead.

**The guard is a test rather than a twenty-first snag check, and the
entry's own last bullet is why.** What one would drive asserts the
**fix**, and `check-snag-claims.sh`'s `ok` means *the bug is still
real*, so such a check can only report a landed fix for ever —
`check_review_schedule_unread`'s defect. `FROZEN_TABLES`' rule met from
the other end: `TestTheStepsProvenanceIsProjected` outlives the finding.

**A column read four ways has one classification, and it lives beside the
CHECK constraint** (Session 80, `SNAG-API-004`). `status != "ok"` was
written in four readers of `service_health.status` and was wrong in three
of them from the day migration 009 added `skipped` — a *declaration* not
to check, which every "not ok" reader silently reclassified as a fault on
the same day. `STATUS_READINGS` on `monitor/models/service_health.py`
classifies all seven admitted values as `well`/`fault`/`unwatched`, and
`is_fault()` / `is_unwatched()` are the readers.

Five rules, three of them the opposite of the obvious implementation and
all five settled against the live box:

1. **The population was three, and the entry named one.** `GET
   /api/sysadmin/status` is the route the snag names; `GET /api/summary`
   carries the identical phrasing and was never named by anyone; `GET
   /api/projects/managed` carries it too and is **the only one that was
   not masked** — measured 2026-08-25 it reported `venture-assistant` and
   `sysadmin_assistant` unhealthy with every real service `ok`, each
   having one `monitor: false` service beside its live ones. Reading the
   code finds the phrasing; only running the three routes ranks them.
2. **The classification sits beside the constraint, not beside a
   reader** — `max_priority_for` against `PRIORITY_MAP`. A test asserts
   it is **exactly total** over the constraint's own `sqltext`, parsed
   out rather than re-typed, so a status added by a migration fails the
   suite instead of falling silently to one side.
3. **`is_fault` fails closed and the totality guard is what makes that
   branch unreachable.** An unrecognised value reads as a fault, because
   a monitor going quiet about a state it does not understand is worse
   than a false alarm — `schema_guard`'s posture, not `collation.py`'s.
   The two guards are kept apart deliberately: one decides the direction,
   the other removes the case.
4. **`reliability.py` is pinned, never imported.** Its docstring promises
   purity ("no DB access, no FastAPI") and the vocabulary's owner is an
   ORM model, so its two status strings stay typed and a test drives both
   sides against the constraint — `syslog_priority` against
   `journal.PRIORITY_MAP`. Import where you can, pin where you cannot;
   the failure mode of neither is drift. It also stopped negating `ok`:
   `DOWN_STATUSES` names the four measured faults positively, which
   changes **no number today** — both readers run over `measured`, which
   has already dropped the unmeasurable rows — and changes the failure
   mode, since a newly-admitted status would otherwise be charged as an
   outage exactly as `skipped` was for eighteen days.
5. **A missing row is deliberately not a declaration.** On
   `/api/projects/managed` a service with no health row still reads
   unhealthy: a `skipped` row is a recorded *decision* not to look, and
   an absent row is nobody having decided anything, so there is no
   evidence to claim health from. Empty population today, pinned by a
   test so the fix is not generalised one step too far.

**The suite was green either side of all three defects**, which is the
part worth carrying: the tests covered a healthy box and an unhealthy one
and never a healthy box with a declaration on it, and
`/api/projects/managed` had **no test at all**, which is why its version
was the visible one. `TestNoReaderNegatesOkByHand` is an AST sweep over
every module that reads `ServiceHealth`, refusing a hand-written
comparison of a health status to `"ok"` — what made this the *third*
instance rather than the first is that the two earlier fixes each stopped
where somebody had noticed.

One falsification **passed against deliberately broken code**: `assert
SERVICES_SKIPPED is SKIPPED` is True whether `services.py` re-exports the
literal or retypes it, because CPython interns short strings. It asserts
a *value* where it means *provenance*, which is the shape recorded after
Session 59's guards, and only the source can answer provenance — it is an
AST check now.
