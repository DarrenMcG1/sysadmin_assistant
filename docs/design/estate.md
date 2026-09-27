# Judging the estate — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**Idle nudges are raised by the estate now, and judged here.** The nudge
— an `active` project whose human-written next action has not changed for
N days — was this repository's from Session 31 until the domain left on
2026-08-13 (ADR-0005). Its arithmetic, its per-project `idle_nudge_days`
override and the rule that eligibility is *borrowed* from the
next-project endpoint rather than restated are estate-manager's, and are
worth reading there.

What remains here is the consuming half, and it is the interesting half:
the estate publishes nudges on `GET :8400/api/projects/attention` and
**may not act on them**, so `judge_attention` turns them into alert rows
— taking the producer's severity verbatim rather than recomputing a rung,
because the ladder moved with the domain. Whether the quiet rung is
audible at all is still decided by **`tray.notify_min_severity`** — *not*
`notifications.desktop.min_severity`, which is parsed and read by nothing
(SNAG-CFG-001).

**The repository health score is the estate's.** `status: archived`'s two
waived deductions, the marker scan that excludes `*.md` so a repository's
own `snag_list.md` stops lowering its score, the whole-word `grep -w` and
the per-project truncation cap — every rule that turns a repository into a
number moved with `sysadmin/projects/` on 2026-08-13 (ADR-0005) and is
argued for there. What this repository does with the result is judge it
from outside: `judge_attention` reads the breaches the estate publishes
and never recomputes a score.

**The estate publishes and never acts; this repository judges — and the
judge owns every row it sweeps, which is what lets it do both** (Session
45). `sysadmin/estate/` is a package rather than a module in `monitor/`
because it is a domain: a client that pulls, a **pure** `judgements`
module holding every threshold, and an agent holding only the lifecycle.
It reads four surfaces on 8400 — the scan's invariants, `attention`, the
audit's invariants and the queue's — hourly, because the producers change
twice a day and `/api/projects/attention` re-walks ~26 `.project.yaml`
manifests from disk on every request.

`monitor/collation.py` records that dedup and a set-based resolve are
mutually exclusive. They are — *there*. That sweep's exclusion set is the
titles the run **raised**, so a deduplicating family (which raises
nothing on run two) has its still-true row resolved, re-raised, resolved,
and each flip clears the tray's `{severity}:{title}` fingerprint. This
agent's exclusion set is the titles the run **judged**, which is a
different set: dedup suppresses the raise, never the judgement. A fault
that persists is in `current` every run and is never swept; a fault that
clears leaves `current` once and resolves once. That is available only to
an agent that owns every row it sweeps — `_resolve_recovered` scopes on
`Alert.agent == self.name`, so `estate_judge` rows are unreachable from
the sysadmin agent by construction.

Five rules, three of them the opposite of the obvious implementation:

1. **A cumulative total is not a rate.** The queue publishes
   `dropped_total`, `expired_total` and `grants_total` as `count(*)` over
   the whole `gpu_leases` table. `dropped_total` is 1 today, so a `> 0`
   rule raises a row no future state can clear — `redis unreachable`'s
   6,283 and `Critical disk usage on /`'s 13,971 arriving by a fourth
   route. Only `depth` and the oldest-wait gauge are judged; the
   totals are carried in `details` as evidence.
2. **The sweep is scoped to the surfaces the run read.** Four independent
   surfaces come from one process, so three answering while one 500s is a
   real state; sweeping globally would close every health breach and idle
   nudge on the strength of a payload nobody received. Rows carry
   `details['estate_surface']` rather than being matched back by title —
   `COLLATION_DETAIL_KEY`'s rule.
3. **Unreachability is not judged at all.** `estate-manager-api` is an
   `http` entry in `services.yaml` polled every 300 s, with both estate
   timers beside it as `kind: timer`. A second owner of one lifecycle
   closes a row while the first still holds it true. 8400 being down
   costs a log line and `details['unread_surfaces']`, which **names** the
   surfaces.
4. **Nudge severity is the producer's; health severity is ours.** The
   estate computes a nudge's rung on the ladder that moved with the
   domain, so taking it verbatim keeps one implementation. `health`
   carries no severity — that machinery was deleted rather than ported —
   so a breach is `warning`, one rung, never `critical`. The audit's
   `findings_total` is never judged: 8 of today's 10 are the collation
   family this service already raises, and the rest are other
   repositories' conformance, which the estate rules send to their own
   ADR processes. What is judged is whether the audit **ran**.
5. **Variable text never enters a title.** `sources_unreachable` is free
   text ending in an exception class name, so a per-source title opens a
   second row the day the same dead seam fails with `ConnectError`
   instead of `HTTPStatusError`. One row; `details['sources']` names
   them. The title is also kept clear of `RESOLVABLE_TITLE_PATTERNS` by
   construction — `Estate scan could not reach sources`, not `… sources
   unreachable`, which `% unreachable` would match.

`scan_max_age_hours`/`audit_max_age_hours` are **derived** (both timers
are daily, plus the briefing's existing two-hour `stale_sources` margin);
`queue_max_depth`/`queue_max_wait_seconds` are **invented** and say so in
config, because until estate-manager's Session 3 there was no queue to
measure.

**The busy day arrived, and the gauge moved rather than the threshold**
(2026-08-30, Session 139, estate message `d1939cf7` / their ADR-0076 and
ADR-0077, filed *before* the commit that carried it — their rule 3).
estate-manager's weekly review now **takes** a GPU lease instead of
sampling a counter, so it queues behind `venture-enrich-nightly` every
Monday 05:30 and waits **915–1038 s** across the five nights they
measured — over this repository's 900 s threshold every time, for a
third cause the "Estate queue starved" message does not name and cannot:
*the queue working exactly as designed*. Their surface gained
`waiting_reason` (`null`/`behind_holder`/`holder_overdue`/
`nothing_granted`) and `oldest_unexplained_wait_seconds`, which is
`oldest_waiting_seconds` with `behind_holder` masked to `null`.
`judge_queue_invariants` reads the masked field now.

Four rules, three of them the opposite of the obvious implementation and
every one settled against the producer's own code rather than its prose:

1. **The threshold did not move, and raising it was the wrong half.**
   900 → 1200 is what anyone reaches for and it buys nothing: at a
   bigger number the gauge still cannot separate a normal Monday from a
   stuck queue, it only says so later — and the Monday wait is bounded
   by *another repository's* timer, so any number clearing it is one
   schedule change from being wrong again. `config.yaml` now carries
   that refusal beside the leaf, because the leaf is where a future
   Monday false alarm sends someone.
2. **The mask is read, never recomputed.** `waiting_reason ==
   "behind_holder"` plus the raw gauge reconstructs the masked number,
   and reconstructing it makes this a second implementation of the
   producer's derivation — `SNAG-DB-003`'s shape, `max_priority_for`
   against `PRIORITY_MAP`. A test drives an *inconsistent* payload
   (`behind_holder` beside an unexplained wait) and asserts the row is
   still raised: the estate owns that derivation and disagreeing with it
   silently is how two statements of one fact drift.
3. **Absent is not masked, which is `ports_checked`'s rule at the size
   of a dict key.** `payload.get(...)` answers `None` both for a
   producer that looked and explained the wait and for one that does not
   publish the field at all. Collapsing them retires this family in
   silence the day the estate rolls back, so a payload with no such key
   falls back to `oldest_waiting_seconds` and labels the row
   `details['wait_gauge'] = "total"` — deliberately the **pre-fix**
   behaviour rather than a refusal, because over-reporting on a Monday
   is the failure this module survives and going quiet is not. The
   fixture's 2026-08-16 `backlog` scenario is a *real* specimen of that
   shape and is kept unmodified rather than re-captured; hand-editing it
   into the new shape breaks a test.
4. **The reason is named, because the producer names it.** The old
   message posed a disjunction and `waiting_reason` answers it — leaving
   it unread is `SNAG-UNITS-004`'s defect, under-reading a field the
   producer had already filled in. The two values that can still reach a
   row are exactly the disjunction's two limbs, which is why the
   sentence stays true. A value this repository has not been told about
   falls back to the disjunction rather than being rendered:
   `_port_of`'s refusal to title a finding from `subject`.

The trade the fallback makes is that the new field's **absence** is
survivable and therefore silent everywhere — so the only place it can be
loud is the live half, where
`test_the_wait_discriminator_is_still_published` fails if 8400 stops
publishing it. A graceful degradation with no separate alarm degrades
unnoticed. The three states are pinned against payloads built by running
`Arbiter.submit` → `tick` → `invariants` in estate-manager's own venv
against a scratch database — never the live `estate` one, which estate
rule 1 forbids writing and which two connections could not have been
rolled back across anyway.

`active_lease.hold_deadline` was rejected here as a threshold in Session
45 and the estate has since made that same deadline its `holder_overdue`
discriminator — asked of the database against the clock that set it, and
published as a *classification* rather than as a column for a consumer
to threshold. The rejection stands and the condition is named anyway. `base_url` duplicates `services.yaml` deliberately — deriving it
would stop the judging silently when a service is renamed — and a test
asserts the two agree.

**`nothing_granted` names its limb now, and the verdict is ours by the
producer's design** (2026-09-22, Session 249, estate message `a3923a29`,
their ADR-0189). The queue surface carries `gpu_floor` — the arbiter's
last floor `percent`, `read_at`, its own `threshold_percent` and a
`reading` of `null`/`sampled`/`unreadable` — with both operands and no
verdict. `judgements._floor_verdict` compares with the arbiter's own
operator (`>`, strictly: at the boundary it grants) against the
**published** comparand, never `llm.gpu_busy_threshold`; only
`over_threshold` puts the fault on the card, and every other reading is
one the arbiter grants on, so a stranded waiter beside it is the tick
loop. An absent `gpu_floor` is not a `null` reading and keeps the
two-limb sentence; the reading's age is stated in the message and never
thresholded, because the tick cadence is not published. The title does
not move with the limb. `SNAG-GPU-003` carries the rest.

**And a third limb since their ADR-0202** (2026-09-26, Session 262,
`SNAG-GPU-006`, estate message `4ef705e8`): the arbiter also holds a waiter
while `vram_floor.state == "sampled"`, `need_mib > 0` and `free_mib <
need_mib + headroom_mib`. `judgements._vram_verdict` applies that predicate
to the published operands — `headroom_mib` read, never transcribed — and
`_nothing_granted_cause` follows the tick's order: `over_threshold` is
asked first and keeps its sentence, and anywhere else a holding VRAM floor
names itself. `_floor_verdict`'s absent-is-not-null and
unrecognised-is-not-guessed rules transfer unchanged, with one addition: a
`vram_floor` that is published and unreadable appends a caveat, because
*"its tick loop has stopped"* is no longer a conclusion the busy floor can
support alone.

**Rule 3 has one named exception, and `ports` is it** (Session 26b-A).
The estate's audit files findings and **never alerts**; this repository
is the only party on the box permitted to speak. Until now nothing
judged `/api/audit/findings`, so a `breach` was detected, correct,
machine-readable and never said out loud — the shape Session 46 spent
itself removing for units, reproduced one layer up. `judge_audit_findings`
judges it per finding.

The narrowing is exact, and both of rule 3's original reasons still
exclude what they excluded. **Scoped to `check == "ports"`, never to a
severity**: `ports` does not have `breach` to itself, so a severity-only
filter would re-import the collation family `monitor/collation.py`
already raises here (this service's own alerts arriving through a second
producer) and pull in `pointers`/`seams`, which are other repositories'
conformance. Neither reason reaches a port, because **no repository owns
one**. *That premise read "all four estate checks emit `breach`" until
2026-09-13 (`SNAG-DOCS-029`), which was the audit as it stood when the
rule was written. It is replaced rather than re-counted: a sentence
restating another repository's cardinality is the thing that went stale,
so it is not restated here. The figure's home is `JUDGED_AUDIT_CHECKS`,
which dates it and sources it to `checks_run` on
`GET :8400/api/audit/invariants`. *That home is where a reader should go
and it is not yet the only copy* — nine sentences in this tree restate
today's total, two of them inside `judgements.py` itself, which is
`SNAG-DOCS-030`. Every consequence the sentence names survives the
correction, re-read off their `audit/checks/`: `collation`, `pointers`
and `seams` all still emit `breach`, so what aged was the premise and
never the argument.*

Six rules, four of them the opposite of the first draft:

1. **Only `breach`, taking the producer's severity as the filter** — the
   deference `judge_attention` already gives a nudge's rung. The `warn`
   rung carries `claimed_but_silent`, which is *availability*, and
   availability has an owner here: `services.yaml` plus the sysadmin
   agent's `% unreachable` family. *The rung held that one code until
   2026-09-13 (`SNAG-DOCS-029` — this read "`warn` is
   `claimed_but_silent`"); it gained `claimed_by_more_than_one_row`,
   which is not an availability finding and is excluded for its own
   reason, this repository already serving its subject as
   `duplicate_claim` under `GET /api/units/actions`. Which codes sit at
   which rung is the producer's vocabulary and is not enumerated here;
   `JUDGED_AUDIT_SEVERITY` is where it is read, dated and sourced.* **This read "that today's one live `warn` (port 3300) happens
   not to overlap is luck — its registry row reads 'unit to follow'"
   until 2026-09-13**, when estate message `84d72698` measured their 430
   audit runs by presence streak: the overlap was already on **four**
   ports `services.yaml` carries — 8080, 8500, 3100, 3200 — holding 23
   of the 27 raise-events, and **19 of the 27 are one event**, the
   estate's arbiter swapping `venture-chat` (:8080) for
   `venture-chat-large` (:8083) on a lease grant. The exclusion is
   unmoved, because an overlap is the reason for it; see
   `judgements.JUDGED_AUDIT_SEVERITY` and `SNAG-PORT-007`.
2. **One row per port, port in the title.** Session 46's rule; a roll-up
   cannot name anything.
3. **Until the count says the fault is the registry itself.** Above
   `port_breach_max_rows` (5) it collapses to one row naming the ports in
   `details` — six simultaneous unclaimed listeners is a table moved or
   truncated, not six services, and six toasts train the reader to
   dismiss the family (`SNAG-UNITS-002`'s refusal to ship fifteen). The
   estate errors on an **empty** parse; a partial one is the gap that
   leaves.
4. **The port comes from `detail['port']`, never from `subject`.**
   `subject` is producer prose; a finding whose port will not parse is
   skipped rather than titled from the sentence, because that fallback is
   the forkable title rule 2 forbids. `isinstance(True, int)` is `True`,
   so bools are refused explicitly.
5. **The title carries no `code`.** A code in the title forks the row
   when a second one lands for the same port. The producer's `summary` is
   the message, so its wording can change without moving the identity.
   *This opened "`unclaimed_listener` is the only ports breach today"
   until 2026-09-13 (`SNAG-DOCS-029`), and the correction is the opposite
   of the obvious one: a second breach code has landed
   (`claimed_by_an_unregistered_tree`, estate ADR-0166) and the fork is
   **still** unreachable by code, because the two partition the ports
   between them — one is filed only for a port no registry row claims and
   the other only for a port some row does. What the count was standing
   in for is that partition, which is structural and does not age, so it
   is what the rule rests on now. The reachable path is two registry
   **rows**: their loop is per claim row, so one port claimed twice can
   file that breach twice — see `tests/test_estate_judge_agent.py`.*

`audit_invariants` and `audit_findings` are **two surfaces, not one**,
though they come from a single check run: they are two HTTP calls that
fail independently, and the sweep is scoped per surface — sharing an id
would let a successful read of "did the audit complete" close every port
row raised off a findings payload nobody received.

6. **A transient holder is quietened, never suppressed** (Session 57).
The family's first two live rows are Alfred dev servers launched from an
editor — `nuxt dev` on 3110, `uvicorn --reload` on 8110, all three pids
in `app-code-oss-26348.scope`. The estate's finding is *literally
correct* and its remedy does not apply, so the row is raised at
`TRANSIENT_HOLDER_SEVERITY` (`info`, the only rung below
`tray.notify_min_severity` here) rather than dropped. **Dropping was the
obvious implementation and rebuilds this family's founding defect** —
Session 26b-A exists because a ports breach was detected, correct,
machine-readable and never said out loud, and a consumer that silently
declines to judge a published finding is that shape with nothing
recording the decision, which is `SNAG-CFG-001`'s. The roll-up takes the
loudest rung it swallows, so one genuine breach among six dev servers
still speaks.

The defect was **not a missing signal**. `Listener.transient` has named
these listeners since Session 26c; `PortReport.unit_ports` drops them for
`recommendations.py`'s correct reason and `unattributed_ports` never held
them, because a session scope *is* attributed — so the port fell out of
the stored blob entirely and `holder` came back `None`,
indistinguishable from 5432's genuine unattributability. That is
`ports_checked`'s rule one layer down. `transient_ports` is a **separate
blob key**, not a flag inside `unit_ports`: one field whose two consumers
want opposite safe defaults is Session 48's `UnitFinding.enabled` trap,
caught before shipping this time. `PortAttribution.of()` returns
`transient` as a bool that is always present, so
`holder.get("transient")` cannot read every service on the box as
non-transient by accident, and the ambiguity rule spans both maps — a
port held by a dev server *and* a real service is attributed to neither.

`SNAG-ESTATE-009` is the gap: the sweep is six-hourly and the judge
hourly, so a dev server started inside a sweep window is unattributed and
speaks at `warning`. Both closures were refused — a second `ss` caller
(which `_attribution` forbids in writing) and an hourly sweep (six times
the cost, for one annotation).

7. **The row says what the sweep *knew*, beside who it named — and that
is an annotation, not a rung** (Session 128). `PortAttribution.of()`
answers *who held this port* and returns `None` for **four** different
reasons; `reading()` answers *what the evidence says* and never returns
nothing: `held`, `transient`, `unattributed` (the sweep looked straight
at the port and could not name a holder — 5432, 8601), `unswept` (the
sweep ran before this listener started, which is `SNAG-ESTATE-009`), and
`unknown` (no stored row, a failed observation, or a blob predating the
key). `details['attribution']` carries it on every breach row and in the
roll-up.

Four rules, three of them the opposite of the obvious implementation and
every one settled against the live sweep rather than by argument:

1. **The discriminator was already stored and no consumer read it.**
   `as_blob` has emitted `unattributed_ports` since Session 26c;
   `attribution_from_blob` was written later for a different consumer
   and ignored it. So this is not new evidence, it is the **sibling** of
   the collapse rule 6 fixed one field over in the same function —
   `ports_checked`'s rule, which that rule's own closing paragraph cites
   while leaving this half standing.
2. **It moves no rung, and the refusal is on correctness where the
   entry's two are on cost.** Quietening an unattributed breach because
   the sweep predates it inverts `_attribution`'s stated posture — *"the
   enrichment is not allowed to become a dependency of the alert"* — and
   a failed `observe_listeners` returns **no** listeners, so every port
   would read unswept and the whole family would fall below
   `tray.notify_min_severity`. Session 26b-A's founding defect at full
   scale, as the fix for a seven-hour window. Gating on `ok` removes
   that failure and not the objection: the default for an unknown port
   would still be *"probably a dev server"*, a guess
   `attribution_from_blob` already refuses where a port held by two
   units is **dropped** rather than attributed to whichever sorted first.
3. **`ok` gates the evidence, which is the half that is easy to miss.**
   A failed observation serialises `unattributed_ports` as `[]`, and an
   empty list read as evidence is a confident statement about a sweep
   that never looked — `ports_checked`'s rule rebuilt inside the fix for
   `ports_checked`'s rule. `unattributed` is therefore `None` rather
   than empty whenever the sweep cannot answer.
4. **Uniform on every row, never only the odd one.** A key present only
   sometimes is the absent-vs-present collapse one level down, so the
   *value* carries the news and the roll-up keeps a reading for every
   port even though `holders` is filtered to the ones it named.

**The entry stays open and its own check said so.** The annotation
removes the indistinguishability the check is keyed on and moves nothing
about the mechanism. Two of the entry's measurements were also refuted
by the box: its four historic `warning` rows **predate `transient_ports`
in the blob by a day**, so this entry has never observed its own class;
and *"the window is six hours wide"* is the **p90** — 83 inter-sweep gaps
give a median of **1.30 h**, because `agent_first_run_delay_seconds: 60`
re-runs every added job on each daemon start and this daemon's median
life is 1.77 h. Both errors have one root: the mechanism was costed from
`config.yaml` and the code path rather than from `unit_audits`.

The check needed **widening before its third limb could be removed
honestly**, and the baseline is what caught it: `annotated` compared
detail *key sets*, so it saw a key added to one row and was blind to the
same key added to every row with a varying value — which is the shape
rule 4 requires. Measured before a line of the fix existed, so the check
would have reported `match` over a landed fix, which is worse than
flipping. `_detail_shape` compares values with each row's **own** port
rendered opaque rather than by naming `port`/`fingerprint`/
`audit_summary`, the three spellings of one number.

Verified live rather than only against literals. This family **shipped
with zero rows until 2026-08-16**, which was exactly `SNAG-ESTATE-002`'s
starting position: the estate's own `run_check` was driven in-process
against the real registry document with a listener bound on 8888, giving
clean → `breach` → clean, with no write to the estate's database. It
caught one defect no literal would have — the estate stamps a first
sighting `standing_days: 0.0`, and "Standing 0 days" reads as a rounding
artefact. Session 57 then re-drove the whole path against the real `ss`
and the real findings payload, which is what caught rule 6.

Two gaps are filed rather than assumed settled: `SNAG-ESTATE-002` (the
producer's `Nudge.title`/`.message` are `@property` and `asdict` drops
them, so this repository builds a format the estate believes it owns) and
`SNAG-ESTATE-003` (no escalation; the loud rung would be `critical`,
which is reserved for faults on this box, and the family most in need
already arrives pre-escalated from the producer).

**`judge_attention` was written against literals and refuted by data the
first hour it saw any** (Session 52). `GET :8400/api/projects/attention`
has answered `{"health": [], "nudges": []}` on all four occasions anyone
has looked, so every rule in that function was pinned against dict
literals **written by the same hand that wrote the consumer** — which is
the strongest evidence available and is not the same as an observation.
A populated payload was made from the producer's own code, driven
read-only in its own venv against the live estate database with
`effective_threshold` forced to 101 and `nudges.evaluate(default_days=0)`
so live rows qualify; everything else is the estate's, including
`dataclasses.asdict` over the real `Nudge`, which is the point — the
field names are what an unforced payload would carry.

Two defects came out of it, and **neither is a rule this repository had
to invent**; both were already written down for other families and never
applied here.

1. **The row count is capped, per family.** The run produced **31 rows
   and 31 tray fingerprints from one hourly poll** — 26 health breaches
   and 5 nudges. Every breach is worth its own row while there are few
   of them, because a roll-up cannot name anything (Session 46); above
   `attention_max_rows` the count *is* the news, since twenty-six
   repositories do not go bad between two polls but a threshold moved in
   the estate's `config.yaml` does exactly that to all of them at once.
   The two families collapse **independently** — separate producers
   inside the estate (a score against a threshold; a streak against a
   schedule) that fail separately, and collapsing the working half
   because the other broke hides the half still naming its projects. The
   recording lands on both sides of the cap without being made to: 26
   collapses, 5 (the whole eligible nudge population) does not.
2. **A roll-up takes the loudest rung it swallows.** Collapsing rows
   must not also quieten them: `info` is below `tray.notify_min_severity`
   here, so an escalated `warning` nudge folded into an `info` row makes
   the fix for noise the reason the one entry that earned a toast never
   got one. Volume is not severity in the other direction either — a
   roll-up of six `info` nudges stays `info`.

The message is also cut with `truncate_at_word` at `NEXT_ACTION_CHARS`
and the full action kept in `details['next_action']`. The live actions on
this estate reach **469 characters** and `alert.message` reaches a
notification body verbatim, so the daemon was cutting them at a point
nobody chose — `SNAG-BRIEF-002` exactly, one domain over. That the
producer independently reached 120 for the same destination is not a copy
to deduplicate: its constant is private, behind a property `asdict` drops.

The seam itself is guarded where the other two 8400 routes already were,
in `tests/test_estate_project_contracts.py` rather than a new file. Its
live half can only assert the envelope, so the per-entry assertions are
**pre-staged** — they begin running by themselves the first day the
estate publishes a breach or a nudge, which is also the first day they
could catch anything. One of them asserts `title`/`message`/`details` are
*absent* from a nudge, so the day estate-manager closes its side the
suite says so and names the next move.

**The other three surfaces went the same way, and the defect is the one
a literal cannot hold** (Session 54). Every rule in
`judge_projects_invariants`, `judge_audit_*` and `judge_queue_invariants`
was pinned one condition at a time, because a keyword override to a test
helper produces one condition. **The producer cannot separate them.**
`ScanOutcome.estate_written` starts `False` and is set near the end of a
run, so *every* failing scan carries `error` and `estate_written: False`
together — two rows for one fault, the second reading "the last project
scan **completed** without rewriting estate.json" of a scan that did not
complete. The rule is now narrowed to a scan that did not error, which is
`failures.py`/`stalls.py`'s mutual-exclusion-by-construction one domain
over. What made a redundancy worth fixing is Session 53: a wrong row is
no longer one toast, it is a daily restatement.

The payloads are the producer's route functions, ORM models,
`_streak_starts` and `CheckResult.as_summary`, driven in estate-manager's
venv against the live `estate` database inside rolled-back transactions —
**one notch weaker than Session 52's** and it says so in the fixtures: the
unhappy *rows* are synthetic, because 0 of 7 `scan_runs` and 0 of 22
`audit_runs` have ever carried an error. The `ports` breaches are not:
real listeners on 3900–3905 through `ports.run_check` against the real
registry document.

Three further things it settled. **`EstateJudgeAgent._execute` claims a
title as it raises it** — `open_titles` was read once, so two judgements
sharing a title in one run inserted two rows, which
`judge_audit_findings` rule 4 makes reachable by keeping the finding's
`code` out of the title on purpose. **`details['code']` is `None` on
every payload the estate can serve** (`SNAG-ESTATE-006`): `AuditFinding`
has no `code` column, the value survives only inside `fingerprint`, and
splitting that is this repository parsing a format the estate owns — so
the field is still read, the absence is asserted, and the fix lands on
the producer's side with no change here. **Two rules are unreachable
against today's producer and are kept anyway** — the scan's
`finished_at is None` (the row is written once, after the scan) and the
audit's `error` (`_record` builds `AuditRun` without one) — named in the
docstrings so their silence is not read as health.
