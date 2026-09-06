# Handoff — 2026-09-06 (Session 183)

## Next action

Correct the register's one remaining unchecked entry — the live declaration guard that skips when the producer rewords its payload — by moving its disposition to `owed` before writing its check, because Session 182 drove that entry's refusal bullet in real SQL and found it costs only the population check rather than the defect, which is the same mis-costing the entry closed this sitting carried, and the published line cannot cite the id while the entry's own body still declares `decided`.

_**`SNAG-SYSD-008` has its check and the witness is the figure the entry
was wrong about.**_ _`check_memory_decomposition_unserved` is the
twenty-second check and reports `still holds`. It drives
`GET /api/sysadmin/services/sysadmin-service/details`, reads
`MemoryCurrent` back through `ServiceDetailInfo`, locates the cgroup by
the **`MainPID` in that same payload**, and asserts that nothing under
`sysadmin/` or `sysadmin_tray/` opens `memory.stat`. Live: **453.9 MB
served against a cgroup `memory.current` of 453.9 MB, of which 67 % is
page cache**, and no reader. Open entries carrying no check: **2 of
24 → 1**, by a check being written. Disposition `owed` → `decided` the
same day — the round trip is the record: `owed` was taken because that
word asserts a check is *unwritable*, and the check is written._

_**The served figure is the discriminating witness, and that is the
whole design rather than a guard bolted to it.**_ _A report that nothing
serves the decomposition, taken on a box where nothing serves anything,
is a dead surface wearing this entry's sentence — so an absent,
unusable or divergent figure is `unknown`, never `match`, and the drive
that pins it removes the figure while leaving the sweep untouched. Two
further roads to a false emptiness are closed separately: the sweep must
also find `MemoryCurrent` itself, and `memory.stat` must actually carry
`anon` and `file` before their absence from a route means anything._

_**The witness was self-supplied until it was measured, which is the
correction worth carrying.**_ _`snag_claims.py` names `MemoryCurrent` in
a constant and opens `memory.stat` to take the reading, so the first
version's anti-vacuity limb was satisfied by the check's own spelling —
it would have passed on the very morning `systemd.py` stopped asking for
the property. The module is excluded from **both** sweeps now, one
expression doing two different jobs: keeping the check out of its own
claim, and out of its own evidence. The witness reads exactly
`core/contracts.py:533` and `monitor/systemd.py:158`, and a test pins
that pair._

_**A source sweep answers a claim about routes, and the obvious
instrument is not weaker but blind.**_ _`systemctl show` publishes
`MemoryCurrent`, `MemoryPeak` and `MemoryAvailable` and not one of them
separates anon from cache, so a route serving the split has to open the
file — the entailment that makes the sweep sufficient. A walk over
`create_app()`'s response models cannot see the surface this entry is
about at all: `get_service_details` returns a raw dict and declares no
`response_model`, which the contract registry already files as
*parse-side only*. `RssAnon` is out of scope by the same discipline —
`/proc/<pid>/status` decomposes a *process*, which the entry's own first
bullet measures apart from the cgroup's._

_**Fourteen falsifications, eleven of them ways of not-knowing, each
landing on its own branch.**_ _The fix stand-in is a **real module** in a
synthetic `REPO_ROOT` rather than a finding injected into the sweep's
output, because a stand-in modelling only the defect cannot tell a check
that measures from one wired to a constant; the docstring-only twin
beside it is the detector's own falsification, and it is load-bearing
here because the entry, the roadmap and three docstrings all name
`memory.stat` in prose. A tree of its own rather than a module written
into `sysadmin/`: a test that drops a file into the package is one
interrupted run away from leaving a reader of `memory.stat` on disk,
which is the verdict this check exists to report._

_**One of those fourteen was vacuous and the gate said so, which is the
part worth carrying.**_ _`vacuous_guards` reported a comprehension under
`tests/` that turned zero times on a green suite: the assertion that this
module is absent from the **readers** list, which after the exclusion is
empty by construction and can therefore witness nothing. Moving it to the
*sweep* found the stronger statement underneath — the raw sweep returns
`['sysadmin/snag_claims.py:7671']`, so **without the readers-side
exclusion the check reports `mismatch` against its own entry on its first
run**, off its own constant. The exclusion is one expression preventing
two opposite failures and both have live populations; the first draft
asserted the weaker one where it could not fire._

_**The conftest fixture gave a drive away for free.**_ _The autouse
`services` fixture installs four synthetic services and none declares
`sysadmin.service`, so the check under it correctly answers `unknown`
rather than reading their silence about `memory.stat` as the entry
holding — `TestTheTrayReportCheck`'s `real_services` idiom borrowed
whole, and its second use is that same witness guard, asserted rather
than described._

_**The next action names no id and that is the finding, not evasion.**_
_`test_the_next_action_names_no_entry_that_is_owed_nothing` refuses a
published line naming an entry whose body declares `decided`, which is
right for work on a defect and wrong for a correction **to the
disposition itself** — the one thing that can only be owed while the
word still says otherwise. Reproduced this sitting in the other
direction: the full suite went red the moment `SNAG-SYSD-008` moved back
to `decided`, on nothing but the handoff line inherited from the sitting
that had moved it to `owed`. Not filed as a snag, because opening one
was not asked for; recorded here so the next sitting can decide whether
it is one._

_**Nothing else was widened.**_ _`SNAG-LOG-016` was left exactly as
Session 182 left it — one check per sitting, and its correction is the
line above. `./scripts/check-ops-claims.sh` carries the same three `no`
findings it carried before this sitting began: the unresolved count
(**3 against 4**, an `alfred-inference` core dump that arrived at 07:19
and is nobody here's doing) and the named-rows sentence beside it, both
of which are `check_alerts`' rise note working, and the deploy check.
**No restart was taken and the reading is the documented false
positive**: `create_app()` does not import `snag_claims`, measured, which
is the case that check's own docstring names as failing in the direction
that costs a needless `kill -TERM`._

_Suite **3679 passed**, `tests/test_snag_claims.py` **397 → 413** (+16,
the arithmetic checked so a clobber could not read as green), ruff clean,
mypy clean over 100 files, `sysadmin-check-snags` **22 checks, all
`ok`**._

# Handoff — 2026-09-06 (Session 182)

_**The question was decided and the answer is yes**, with a rule the
register had already half-written._ _An entry may declare `decided`
while carrying no check, because rule 6's counter and the disposition
vocabulary measure different things: the counter reports a fact about
**freshness** — these N claims are only as fresh as the last hand sweep
— and the disposition reports whether that staleness is **chosen or
pending**. `owed` + no check is *not yet*; `decided` + no check is
*never*. They were never in disagreement._

_**`SNAG-ESTATE-014` filed this exact gap on 2026-08-27 and could not
close it.**_ _Its words: "the finding counts entries with no check and
cannot tell 'not yet' from 'never' — `ports_checked`'s rule at the level
of the register rather than the reading", written after it had refused
`<!--check:none_yet-->` (a marker names a check, and "there is no check"
is not one) and refused a `covered-by` bullet as the same move with a
longer name. The disposition vocabulary landed on **2026-09-02**, five
days later, and is precisely the discriminator it asked for. Nobody had
connected them, which is why this morning read as a contradiction._

_**So the binding rule is not that every unchecked entry is `owed`.**_
_`SNAG-TEST-010` read `owed` because a check *was* owed and turned out
writable — that is *not yet* resolving correctly, not a precedent making
the counter a queue. What `decided` + no check asserts, beyond the
condition being settled, is that a check is **unwritable**; and
`SNAG-ESTATE-014`'s judgement already set the form that assertion takes
— named by the finding it is about, with no marker, **and with the
reason stated in the body**. Silence is not the argument, which is what
decided both entries._

_**The handoff offered two candidates and the true one was a third.**_
_`SNAG-SYSD-008` carried no check bullet at all, so it asserted
unwritability by silence while its own body said an absence "is what a
check should pin" — and that absence does not exist.
`GET /api/sysadmin/services/sysadmin-service/details` serves
`MemoryCurrent: 453611520` against the cgroup's own `memory.current` of
**453287936** at the same moment; `systemd.py` has asked for the
property since the route was written, `ServiceDetailInfo.memory_current`
is in the contract registry, and `services_tab.py` renders it — the tray
has been printing **`Memory: 433 MB`** on this daemon's own card the
whole time. The entry checked `/api/sysadmin/self` and
`/api/sysadmin/resources` and stopped; a claim of the form *nothing
serves X* is refuted by one route, and this one was filed from the two
surfaces a reader would think of rather than from `GET /openapi.json`._

_**What replaced it is sharper than what was filed, which is why the
entry stays open.**_ _The number that *is* served is `memory.current`,
which the entry's own first bullet proves cannot separate `anon 155 MB`
from `file 298 MB` with every byte of the file half cold and
reclaimable. So the surface served the figure that **opened** the entry
as a 462 MB "resident set" and not the decomposition that settled it.
The durable half is a **missing discriminator**, not a missing surface —
`memory.stat`'s `anon`/`file`, measured unserved across `sysadmin/` and
`sysadmin_tray/` — and it is checkable, so `decided` → `owed`. Register
either side: `decided 16` → `owed 1, decided 15`, unchecked unmoved at
**2 of 24**, open unmoved at 24._

_**`SNAG-LOG-016` is mis-costed the same way and was left alone
deliberately.**_ _Its refusal bullet costs only the *population* check —
"is the live population non-empty" — which is the identical mis-costing
`SNAG-TEST-010` made and Session 181 refuted: a check reproduces the
**defect**, not the discriminator. Driven in real SQL against a
synthetic corpus, no writes and no live reset: both genuine kernel
prefixes select under `WITNESS_LIKE` and a payload reword does not, so
the guard skips on exactly the row it exists to catch, and the check
would move when the entry's own stated closure — an event-keyed
population — lands. Its neighbours are the control: `SNAG-LOG-017` and
`SNAG-LOG-018` both sit on measured-empty populations and both carry
checks. Not written here, because the shape-of-fix rule is one check per
sitting and the correction was owed before the check was._

_**No code changed and nothing was deployed.**_ _Three documents and one
disposition; the suite and both gates were run to confirm the register
reads the change the way the decision intends rather than to certify an
edit. No migration, no restart owed._

# Handoff — 2026-09-06 (Session 181)

_**`SNAG-TEST-010` has its check and the entry's stated reason for
carrying none was wrong in the way that matters.**_ _It said a check
would have to reproduce the **discriminator** the arc measure lacks. It
does not — it reproduces the **defect**: a probe under the real
`coverage run --branch` in which two comprehensions turn their loop while
their element never evaluates, and `_loop_turned` answers `turned` for
both. `check_element_never_ran_reads_turned` is the twenty-first check,
costs **80 ms** warm against the sibling gate's ninety seconds, and
reports `still holds`. Open entries carrying no check: **3 of 24 → 2**,
by a check being written rather than by an entry closing._

_**The population is invisible, which is a second reason counting was
never available.**_ _`SNAG-LOG-017`'s *reproduced, never counted* rests
on a measured-empty population that refills; this rests on something
stronger. A blind site reads as **healthy** — the same string a site
whose element provably ran comes back with — so nothing reports it and
there is no set to sweep even in principle. The check asserts that
identity of answers rather than describing it, and Session 180's 311 of
881 is a bound on where the defect could hide, never a list of anywhere
it does._

_**Two controls, each forbidding a different verdict, and both are
`unknown` rather than a reading.**_ _An empty **outer** iterable must
still read `did NOT turn`, or a `_loop_turned` answering `turned` for
everything — the single worst regression the measure has — satisfies this
check perfectly and the entry reads as holding hardest on the morning its
own instrument broke. An element that provably ran must read `turned`,
because that is what makes `turned` the healthy answer the blind shapes
are indistinguishable **from**. Either failing is `SNAG-TEST-009`'s rules
having moved, a different fault, and no sentence about vacuity may absorb
it._

_**The instrument is `_loop_turned` and deliberately not `sweep()`.**_
_The entry's mechanism is stated about that function; `sweep()` folds in
the report join, the freshness test and the mtime test, so a moved
verdict could not say which layer moved — and its signal would be an
**absence**, a blind shape failing to appear among the findings, which is
the weakest shape a claim can take. Driving a private name is the trade
`check_incident_fold_splits_at_a_poll` already makes on
`LogAggregatorAgent._execute`._

_**The fix stand-in separates one shape only, which is the sharper
drive.**_ _The entry named the filter shape and Session 180 added the
multi-`for` one, so a check keyed on both moving together would report a
half-landed fix as though nothing had happened. Eleven drives, each
landing on its own branch, six under the real tool._

_**The premise marker was written and taken straight back out, and that
is the correction this sitting owes another convention.**_
_`@pytest.mark.premise` discharges `test_live_drive_premises.py`'s rule 2
for the **whole file**, and `test_snag_claims.py` is in that population
for its **database** reads — twenty-odd drives exempted in
`PRE_CONVENTION` on the habit that each asserts its own not-knowing
branch. A witness about a coverage subprocess would discharge all of
them, *"and this module could not tell"*, which is that constant's own
wording written about a different candidate mark and true of this one for
the same reason. Its tripwire named the file within one gate run. The
premise assertion stayed and is ordered first; only the marker went, and
`PRE_CONVENTION` now records that the argument is about **whose** witness
rather than about a static walk. A file needing both would be two files,
and this one is close to being that._

_**A next action that names no entry makes another guard vacuous, and
the guard said so within one gate run.**_
_`test_handoff_shape.py`'s refusal test filters the SNAG ids the
published line names, and this sitting's line names none — so
`check-vacuous-guards.sh` reported its comprehension as having run over
an empty population. Empty is the healthy reading there; what is
indistinguishable from it is a **reader that finds nothing in a line
that carries something**, and neither of that class's two premises
witnessed `read_named_entries` itself. Fixed rather than filed: a third
premise drives the reader at a synthetic line over the real register,
and the comprehension carries a `may-not-turn:` naming it. Falsified —
with that reader returning `[]` the premise goes **red and the refusal
test stays green**, which is exactly the blind pass it exists to catch._

_**Disposition `owed` → `decided`, and it emptied the queue.**_ _What was
owed was the check, by rule 6; the **discriminator** was refused and
ranked by Session 180, remains unattempted, and its honest candidate is
still an arc into the element line that is not the loop's back-jump. The
entry stays **open** because the measure is still blind, not because work
is queued. The register now reads **blocked 3, decided 16, delegated 5
and owed none** — the first sitting to leave it with nothing owed, which
is what the next action is about. All three `blocked` entries are blocked
on a population or on the owner, so none of them is a sitting's work
today._

_**Verification.**_ _`uv run ruff check .` clean; `uv run mypy sysadmin` clean — its one catch is worth carrying, `_COMPREHENSIONS` narrows harder
than `_loop_turned`'s parameter and `list` is invariant, so `siblings` is
annotated rather than inferred. `uv run pytest -q` **3663 passed**, the
recorded 3651 plus 12 exactly, so nothing was clobbered.
`./scripts/check-vacuous-guards.sh` exit 0 at **871 of 888** sites
turned with no undecidable block, and 16 declared `may-not-turn`, one
more than Session 180 left;
`./scripts/check-ops-claims.sh` **10 of 10 ok** after rewording the
daemon start, the unresolved count and the named-rows sentence — the
count moved **3 → 5 → 4 → 3** across the sitting and not one of the
moves was this sitting's doing, which the paragraph below finishes._

_**Restarted twice, and the second one is the memory observed live.**_
_07:06:01 (PID 1817 → 64269), then 07:17:52 (64269 → 79162) because a
falsification drive rewrote `sysadmin/snag_claims.py` with **identical
bytes** at 07:13:28 and the deploy check compares **mtimes** — the claim
a true reading of a false question, which is
`stash-pop-reports-a-restart-owed` exactly. Paid rather than argued
with, since resetting an mtime to satisfy a check is the wrong direction
even when the bytes prove it. Both were owed by that rule and by nothing
else: `snag_claims` is a console script `create_app()` never imports, so
this is `SNAG-SYSD-008`'s shape. No migration._

_**The block went stale five minutes after the commit that recorded it,
and the correction is a second commit rather than a note.**_ _`GPU was
reset — every client lost its VRAM` resolved at **07:29:55**, so the
sentence was true when written at 07:24:28 and wrong before the sitting
stopped — `SNAG-ESTATE-008`'s founding case reproduced twice in one
morning and caught both times by the **fall** note. The block reads
**3** now, naming the disk row and the two nudges, and all ten ops
claims are `ok` again. **The fourth reading was deliberately not written
down**: `Unusual CPU usage` was open at the re-measure, raised 07:37:54
by this sitting's own 115-second suite run under `coverage --branch` and
resolved by `_check_anomalies` at 07:42:58 one poll later, exactly as
its 06:51:52 → 06:56:56 twin had done an hour before. That is a figure
about the instrument rather than about the box — Session 175's
precedent — so the close waited a poll, which is what made it possible
to record the box instead of recording the measuring of it._

# Handoff — 2026-09-05 (Session 180)

_**The fourteen undecidable sites are closed and the gate's block is
gone.**_ _`scripts/check-vacuous-guards.sh` reports **865 of 881**
comprehension sites turned at exit 0, against `851 of 881` with fourteen
refused — the old count plus the fourteen exactly, so every refused site
now reads as having turned rather than quietly changing category. Suite
**3651 passed**, the recorded baseline unchanged._

_**Undecidability is a property of the tree, not of the run, and that is
what made the fix cheap.**_ _All three refusals in `_loop_turned` are
syntactic and read no arc, so driving the real function with an **empty**
arc set enumerates the same fourteen the ninety-second gate names. Every
candidate reformatting was settled statically before a test ran; the gate
run was spent confirming the answer rather than finding it._

_**Ten locations in two shapes, and the nested one is the trap.**_ _Six
carried the element on the comprehension's own first line with the
clauses spilling below; four were pairs sharing an element line, reported
twice each, which is why fourteen sites are ten places. In
`all(any(d in c for d in denials) for c in clauses)` the outer element
**is** the inner comprehension, so moving the outer element down lands it
on the inner's own line and trades one refusal for the other — measured,
not guessed, so both had to drop a line. The three adjacent pairs took a
bound name rather than a hanging bracket, which leaves each comprehension
alone on its line and reads as ordinary test code._

_**`SNAG-TEST-010`'s upper bound is 296 of 881 sites carrying an `if`
clause**, taken over the population `_comprehension_sites` itself walks —
imported rather than re-walked, because a second walker is a second
statement of what a site is._

_**The entry names one shape and there are two, which is the correction
this sitting owes it.**_ _A comprehension with more than one `for` whose
inner iterable is empty for every outer item is blind identically: no
filter is involved, the element never evaluates, and the detector answers
`turned`. That takes the bound to **311 of 881** and leaves **570** for
which the measure is exact — the number the entry could not state and the
one that ranks it. Established with a witness rather than read off the
arcs the detector reads: the fixture's element appends to a list and the
fixture asserts that list is empty **inside itself**, with an empty
*outer* iterable beside it answering `did NOT turn` as the control that
stops the drive agreeing with itself._

_**So the entry's reason for carrying no check is refuted, which is what
the next action is.**_ _It said a check would have to reproduce the
discriminator the measure lacks; the witness fixture reproduces the
**defect** instead, in about two seconds, which is `SNAG-LOG-017`'s
*reproduced, never counted* idiom. Not written here — one roadmap session
per sitting, and this one was asked to measure and to close the
fourteen._

_**Two documents disagreed and the register settled it.**_ _Session 179's
handoff says open entries with no check went `3 → 4`; its own entry says
`stays at 3`. `sysadmin-check-snags` reads **3 of 24**, naming
`SNAG-TEST-010`, `SNAG-LOG-016` and `SNAG-SYSD-008`, so the handoff is
the stale half. The entry's disposition also moved `owed`, not `decided`:
the discriminator is not owed and is not ranked, but the **check** is, by
rule 6 — and `decided` would publish "no work here" over an entry the
register's own counter is naming. Written first as `**owed**` and caught
by the check itself, which reads the disposition literally and put bold
markup outside the vocabulary._

_**Cost filed rather than implied**: nothing in this repository runs a
formatter, so the ten reformatted sites stand — but a comprehension has
no magic trailing comma, so adopting `ruff format` would collapse every
one of them back onto a single line and rebuild the fourteen in a commit
that changed no logic._

_**No restart is owed**: nothing under `sysadmin/` changed — the edits are
ten test files and four documents — and no migration was written._

# Handoff — 2026-09-05 (Session 179)

### The action Session 179 filed (done by Session 180)

Measure `SNAG-TEST-010`'s upper bound — the count of comprehension sites under `tests/` carrying an `if` clause, which is the only cheap figure here that is not the missing discriminator itself — and in the same sitting close the fourteen sites `scripts/check-vacuous-guards.sh` names as undecidable, by moving each element expression below its own first line, because both range over the one population that gate already walks.

_**`SNAG-TEST-009` is built and one of the three rules it left behind was
wrong.**_ _`scripts/check-vacuous-guards.sh` runs the suite with
`--branch` and hands the judge both files; `sysadmin/vacuous_guards.py`
reads the arcs out of the `.coverage` SQLite with stdlib `sqlite3` and
still never imports coverage. The gate is **exit 0** with **851 of 881**
comprehension sites turned, **15** loop declarations and **none stale**._

_**Rule 1 as the entry records it reports a loop that turned zero times
as having turned.**_ _*Some arc runs backwards inside the span* is
satisfied by a generator's **exhaustion return**, which arcs from the
`for` line to the frame's own first line whether or not the loop ever
turned — driven at the real tool, `all(\n x > 0\n for x in live\n)` over
an empty list gives `{(1, 3), (3, 1)}`. What discriminates is the
**element** line, because a comprehension is written element-first, with
the entry arc excluded and excluded **only** where the element sits below
the first line, since where they coincide no such arc exists and
excluding it would discard the self-arc that is the whole signal for
every single-line comprehension. Rules 2 and 3 stand as written._

_**Fourteen sites cannot be decided either way, which the entry does not
record and its detector counted as turned.**_ _An element on the
comprehension's own first line, and two comprehensions sharing an element
line — nested or merely adjacent — leave a turning loop and an empty one
**byte identical**. That is why the entry's site count is 858 against a
measured 865. They are named on every run and move no verdict; the live
drive asserts the **arc sets are equal** rather than that the answer is
`None`, with a decidable pair as the control._

_**`meta.has_arcs` is the fail-closed gate and the one this could most
easily have shipped without.**_ _A data file written without `--branch`
opens cleanly with an empty `arc` table, which read as evidence
fabricates a finding for **every** comprehension in the suite — and is
unreachable by a row count, which cannot tell it from a suite in which
nothing turned. Asked-for-and-unreadable is `unknown`; not asked for is a
narrower measure that says so, so `--report` alone still works._

_**The declaration anchor was wrong and it shipped green.**_ _Read from
the comprehension's **enclosing statement**, one comment covered all six
comprehensions in `tests/test_message_backfill_live.py`'s `return {…}`
and four came back *declared and turned anyway* — `UnitFinding.enabled`'s
trap for the third time in one sitting, at **exit 0**, because a stale
declaration moves no verdict and the only thing that named it was the
stale report this module's docstring argues for. Anchored on the
comprehension now, stopping at its own first line so a marker inside a
nested comprehension is not read as the outer's claim._

_**The verdict on the 17 is taken: one fix, fifteen declarations, one
excluded.**_ _`tests/test_tray/test_config.py:365`'s
`assert all(path == "tray" for path in report.unwalkable)` became
`assert report.unwalkable == []`, decidable **and** stronger. The 17th —
`tests/test_service_recommendations.py:1199` — is *unreached* rather than
vacuous, and the assert half already owns that, so reporting it here too
would give one fault two speakers._

_**Fourteen mutations driven and fourteen killed**, each on its intended
tests, including the entry's own rule 1 (four red, one of them the live
drive) and the declaration anchor (four red). **3590 + 61 = 3651**,
none retired — and the baseline was measured by stashing to HEAD, which
cost three self-inflicted reds: the stash ran **while the gate was
collecting**, so the gate ran the pre-edit file, and 3611 + 36 = 3647
reconciled it exactly. The `stash-pop-reports-a-restart-owed` hazard
arriving at collection rather than at mtime._

_**Register**: `SNAG-TEST-009` closed, `SNAG-TEST-010` opened — a filter
that rejects every member leaves the loop turning, so the measure answers
*did the loop turn* and not *did the predicate run*, measured rather than
reasoned about. It is filed where the fourteen undecidable sites are not,
because those are named by the gate on every run and this one is
**invisible**. Open entries with no check goes **3 → 4**._

_**A restart is owed**: `sysadmin/vacuous_guards.py` changed. Nothing
else under `sysadmin/` moved and no migration was written._

# Handoff — 2026-09-05 (Session 178)

### The action Session 178 filed (done by Session 179)

Build `SNAG-TEST-009`'s runtime half — add `--branch` to `scripts/check-vacuous-guards.sh`, read the loop back-edge out of the `.coverage` SQLite with stdlib `sqlite3` rather than from `coverage json`, which erases it, and implement the three arc rules the entry records, falsifying each against comprehensions driven at 0, 1 and 2 iterations and at `any()`/`next()`, because every wrong version of the detector returned a plausible number.

_**`SNAG-TEST-009` is decided and both limbs of the question were
false.**_ _It asked whether counting comprehension iterations at runtime
is worth **a second pass over an 86-second suite**, or whether the cheap
AST half is the whole of the fix. There is no second pass: coverage
records a loop **back-edge** as an arc, so `--branch` on the run the gate
already makes is the entire mechanism. Measured — plain **68.3 s**,
`coverage run` as the gate does it today **90.2 s**, `coverage run
--branch` **88.3 s**. `sys.monitoring` and `sys.settrace` are both
unnecessary, and the cost the whole question turned on does not exist._

_**The sentence saying otherwise is still in the tree, deliberately.**_
_`sysadmin/vacuous_guards.py`'s docstring and `check-vacuous-guards.sh`'s
header both say branch coverage cannot reach this, "because the
comprehension's own iteration is not a branch of the assert statement".
It is not a branch of the assert, and coverage records it regardless.
Left for the build sitting so that nothing under `sysadmin/` moved and no
restart is owed — this sitting touched four documents and no code._

_**`coverage json` erases the discriminator, which is the one real
constraint on the build.**_ _A file whose only loops are comprehensions
reports `num_branches: 0` with `executed_branches: []`, because
coverage's static analysis does not model a comprehension as a branch
point — and the report lists only *statement* lines, so a comprehension's
element expression never appears there either. **Line coverage therefore
answers 0 of them, not some.** The arcs survive in the `.coverage`
SQLite and read with stdlib `sqlite3`, so the module's "it reads a report
and never imports coverage" rule survives untouched._

_**The AST half is aimed at the wrong population, and the one live
finding proves it.**_ _`tests/test_tray/test_config.py:365` asserts
`all(path == "tray" for path in report.unwalkable)` at an input where
nothing is unwalkable, so it asserts nothing while the test below it
covers the real case. Its iterable is an `ast.Attribute` — one of the
**114** the proposed `Call` rule discards against the **37** it selects.
The hand sweep of 2026-09-05 concluded the finding set was empty and
there was one thing in it._

_**The entry's provenance claim is refuted and its population is the
wrong one.**_ _Session 173's handoff records a **hand sweep** of all 309,
not a `Call` filter; and two of the ten — `tests/test_ops_claims.py:1804`
and `:579` — bind the comprehension to a local and assert on the *name*,
so they sit outside `ast.Assert.test` and outside the 323 entirely. The
`323 of 6334 asserts across 53 files` the gate republishes on every run
reproduces exactly and counts only `ast.Assert.test`: the union with
assign-then-assert is **673 across 74 files**, and the arc measure ranges
over **858** sites._

_**Measured payoff, driven at the real suite**: **858** comprehension
sites, **835** turned, **23** did not — **6** in an assert *message*
firing only on failure, **9** negative asserts where empty is the
asserted-healthy state, **7** assign-then-assert, and **1** positive
assert. So the measure hands a human **17** sites and finds **1**._

_**The honest cost is the writing, not the running.**_ _The detector was
wrong three times before it was right — **110 → 43 → 26 → 23** findings —
and both surviving bugs are now rules: the back-edge of a multi-line
comprehension is a **two-line cycle** rather than a self-arc, because
`FOR_ITER` lives on the `for … in …` line and not on the comprehension's
own `lineno`; and a **short-circuited** genexp (`any`, `next`) is
abandoned mid-yield and emits **neither** back-edge **nor** exit arc, so
started-and-never-returned means it yielded at least once. Every wrong
version returned a plausible number, which is why the count cannot
falsify the detector and controlled fixtures must._

_**The entry stays `owed` rather than moving to `decided`.**_ _What is
owed changed from a decision to a build; `decided` is where
`SNAG-TEST-005` sits and means no sitting is queued on it, and the
board's next-action check refuses a line naming one. Register **138
entries, 24 open**, unmoved — nothing opened and nothing closed. Open
entries with no check stays at **3**._

_**No restart, and none owed.**_ _Four documents changed and no file
under `sysadmin/`, so the deploy check stays green at the 2026-09-05
16:24:42 start. All ten ops claims green, **and the alert block was
corrected twice**: **4 → 3 → 5 → 3** inside this sitting, the VRAM row
accounting for three of the four moves. It was open at preflight with
both halves of the pair firing — the count rose *and* the marked sentence
failed to name it — was written in, resolved for a fifth time, re-opened,
and had resolved again by the close. **The 5 is the reading that was
deliberately not written down**: it carried `Unusual CPU usage`, raised
by this sitting's own five full-suite runs and cleared by
`_check_anomalies` on the next poll, so it is a figure about the
instrument and not about the box — Session 175's precedent, held for its
reason rather than rediscovered. The suite was
run three times for the timing measurement and was green each time; no
test was added, because nothing was built._

# Handoff — 2026-09-05 (Session 177)

### The action Session 177 filed (done by Session 178)

Decide `SNAG-TEST-009` — whether counting comprehension iterations at runtime is worth a second pass over an 86-second suite, or whether the cheap AST half is the whole of the fix: a comprehension whose iterable is a *call* rather than a literal or a parameter is the only sub-population worth a human's time, and it is how the only ten worth reading were found.

_**`SNAG-TEST-006` is closed, and the gate it owed is three artefacts
rather than one.**_ _`scripts/check-vacuous-guards.sh` runs the suite,
`sysadmin/vacuous_guards.py` judges the result and `sysadmin-check-guards`
is the console script between them — `check-migrations.sh`'s split. Wired
at `claude-postflight.sh` as section 3.8, raising ISSUES on a finding
where the snag claims deliberately do not, because this is a defect in
the sitting's own work rather than a judgement about an entry._

_**The module never imports coverage, and that is load-bearing rather
than tidy.**_ _`coverage` is not a dependency here and arrives through an
ephemeral `uv run --with` overlay — `.venv` unmoved at **107** packages
and the lock clean either side, re-measured rather than borrowed, since
the entry's figure of 122 was taken against an environment that had
drifted 15 packages off the lock. A judge that imported it would be
untestable on every box in this estate; instead the join is a
`coverage json` report read with `json` against an AST walk of `tests/`,
and all **33** of its own tests run on synthetic trees._

_**Exit 0/1/2 for this run, and the comprehension half rides on every
report.**_ _The design Session 176 settled, shipped as written: **323 of
6334 asserts across 53 files** carry a comprehension whose truth over an
empty iterable is `True` with the line executing, so no line-coverage
measure can reach them and a status firing on it would fire for ever.
Three parametrised tests drive that line at all three verdicts._

_**All six live findings were legitimately unevaluable, so the gate ships
with six declarations rather than red for ever.**_ _Three branches on an
idle estate, one on a wiring check with no whole-file finding, and two
deadline guards a fast box satisfies before the loop turns once — that
last pair cannot be restructured into evaluating at all. Each carries a
`# may-not-evaluate: <reason>`: the reason is required, the declared set
is named on every run, and a declaration whose assert **did** evaluate is
reported too, because a stale exemption stops describing anything and
starts hiding the next finding._

_**The staleness rule was found by the fix on itself.**_ _Writing those
declarations moved every assert below them without changing one
statement — the shape a digest of the executed set cannot see — and the
sweep named all three edited files when driven against the report taken
twenty minutes earlier. A test file newer than the report is `unknown`.
The same edit found the ordering rule: counted **after** the skips the
standing declaration fell **314 → 312** the moment those files went
`moved`, which reads as a suite with fewer unjudgeable asserts rather
than as a sweep that stopped looking, so the blind count is taken before
all three skips._

_**Three of twenty-two falsifications passed against deliberately broken
code, and the three are distinct shapes.**_ _The ordering specimen nested
**downwards**, so breadth-first order came out `2, 4, 6` — already sorted
and asserting nothing; the live shape is a nested assert written first
and walked last, which is what produced `166, 167, 147`. The fail-open
test covered **one of two roads**: `str(None)` is `"None"`, truthy, so an
absent timestamp reached the *unparseable* branch and a mutation to the
absent branch passed cleanly — both are parametrised now and the coercion
is gone. And one "mutation" was a **different correct implementation**
rather than a break, which is a third way a drive reports green and means
nothing._

_**The first live run read one declaration of six, and nothing here could
have caught it.**_ _Five went in as multi-line comment blocks with the
marker at the **top**, and the reader looked one line above the assert —
so the gate refused five asserts whose author had just watched themselves
declare them, which is worse than having no declaration rule at all.
Every synthetic fixture used a single-line comment, the one shape that
cannot discriminate the rule. The reader takes the whole contiguous
comment block now and the reason continues onto its following lines; the
gate reports **6 of 6**, **6334** asserts, exit **0**. That fix gave the
empty-reason rule a second return path and the existing test covered one
of them — the two-roads shape for the second time in one sitting, after
`str(None)`._

_**The check retired with the entry and its detector did not.**_
_`check_vacuous_guard_ungated` is refuted by exactly the hop it was built
to see and is gone with its 226 lines of tests and five constants;
`TestTheGateIsOnTheClosePath` outlives it, holding the wiring, the
never-exit-1 rule and the temporary report. The gate's **first** live run
returned **2, not 1**, on a tree being edited underneath it, and its
second refused a suite the handoff guard had turned red for naming a
closed entry — both the red-suite rule working before anything depended
on it._

_**Suite 3566 → 3590**; ruff and mypy clean; all ten ops claims green.
Two restarts were owed and paid — PID 1898616 → 2077357 → 2085468,
counter **12 → 14** — and the second is the interesting one: the first
brought the box level, then the gate's own live run found the
declaration-block defect, so the deploy check went red again on a **real**
edit rather than an mtime artefact, which is the state it exists to
report. Register **138 entries, 24 open** — one closed, one filed — with open entries carrying no check
**2 → 3**, the whole of the rise being `SNAG-TEST-009` and none of it the
closure, which took both numbers down together._

---

# Handoff — 2026-09-05 (Session 176)

### The action Session 176 filed (done by Session 177)

Build the coverage gate `SNAG-TEST-006` still owes — a script running the suite under coverage, refusing a never-evaluated `assert` under `tests/`, exiting 0 / 1 / 2 for this run's clean / found / could-not-measure and naming on every run the comprehension population it cannot judge — wired at `claude-postflight.sh` beside `check-ops-claims.sh`, and close the entry with its check, which retires with it.

_**`SNAG-TEST-006`'s first move landed: `check_vacuous_guard_ungated`, the twenty-first check.**_ _It reads the **gate**, never the sweep — driving the sweep is what the entry rules out on cost, since the honest instrument is the suite under coverage (63 s becoming 83 s) and `check-snag-claims.sh` runs at both ends of every sitting. What is cheap and refutable is whether anything on the close path invokes `coverage` or `--cov` at all: `check_handoff_shape_unguarded`'s idiom one script over, for the same reason — a measure that is documented and not wired. Live, six scripts, 257 invocation lines, four guards, **0** coverage invocations. Open entries with no check **3 → 2**._

_**Three departures from the check it borrows from, each forced by this entry's fix having a different shape.**_ _**One hop, not one file**: the fix is a *new script* wired at `claude-postflight.sh`, whose own name carries no coverage token, so a sweep of the two roots alone reports `match` over exactly the thing it watches for — one test and only one is red without the hop. **Mentions are dropped as well as comments**: both roots name a guard on an `echo`, and `claude-postflight.sh` prints "Consider running your test suite" while running none, so a sweep over executable lines would be refuted by the sentence describing the gap. **Both roots are read**, because a gate wired at the commit closes the entry too, and a root that will not read is *named* rather than dropped so the sweep can go on reporting about the other._

_**The mention rule moves no verdict today and says so.**_ _Measured: it drops **132** of the two roots' lines, **2** naming a guard the script does not run and **0** naming a coverage token. Its population for the answer is empty, pinned by its own test rather than dressed up as a live catch; what it buys is the shape this file's idiom makes likely next, which is coverage added as advice._

_**The third verdict is decided, and it is not an exit status.**_ _Exit 0/1/2 keeps `check-migrations.sh`'s meaning, because each is a property of **this run** a sitting can act on. The comprehension blindness is a property of the **measure** and is permanent — re-measured at 3566 tests, **309** of the suite's **6275** asserts carry a comprehension across **53** files, unmoved from Session 173's count — so a status firing on it fires for ever, which is `SNAG-LOG-002`'s binary confidence and a permanent warning nothing can clear. The gate reports the count it cannot judge on **every** run whatever its exit status: `ports_checked` literally, a field on every payload carrying whether the measure looked._

_**The gate is deliberately not built here, and the reason is structural rather than budgetary.**_ _A check names an open entry, so a sitting that both writes the check and wires the gate closes `SNAG-TEST-006` and retires the check with it — the check would be born refuted. The entry therefore stays **owed**: this sitting wrote the instrument and settled the design question, and declined nothing._

_**Two of eight falsifications passed against deliberately broken code, and they are the two shapes this repository keeps finding.**_ _One mutation was a **no-op** — its replacement string did not match the source, so the test it was aimed at had nothing to be red about; the drive asserts its own edit before running now. The other asserted a **value** where it meant provenance: `PRECOMMIT_SCRIPT in CLOSE_PATH_SCRIPTS` is `==` on `Path`, so restating the path as a literal is indistinguishable from borrowing the constant — `is` discriminates, a fresh `Path` being a fresh object. Every other drive patches `CLOSE_PATH_SCRIPTS` wholesale, so no mutation **of** it is observable behaviourally at all, which is what the statement test exists for._

_**Suite 3553 → 3566**, arithmetic reconciled rather than re-measured; ruff and mypy clean; all ten ops claims green. Register **137 entries, 24 open**, unmoved. A restart was owed and paid — PID 1478358 → 1898616, counter **12**, `/health` 200 four seconds after the TERM — the **seventh** consecutive sitting and the first of the last four where the edit was **real**: `sysadmin/snag_claims.py` genuinely changed, and it is still a console script `create_app()` never imports, so the shape is `SNAG-SYSD-008`'s rather than the mtime family's._

---

# Handoff — 2026-09-05 (Session 175)

### The action Session 175 filed (done by Session 176)

Close `SNAG-TEST-006`'s first move by writing the gate-reading check the entry names — does anything on the close path run the suite under coverage — and then decide whether the coverage gate behind it ships with the third verdict the entry says it owes, because a gate reporting "no vacuous guards" while structurally blind to `assert all(f(x) for x in live)` is `ports_checked`'s rule broken inside its own fix.

_**`SNAG-TEST-008` is closed, and the choice the handoff framed as strong-versus-cheap turned out to have nothing to choose between.**_ _Both files stub `read_arbitrated_stops` at the **transport** and declare `_NO_ARBITRATION` as the reading their assertions hold under. Patching `_ensure_arbitration` out reaches the *same* reading through `or _NO_ARBITRATION` — the right answer spelled as an absence, which is `ports_checked`'s rule at the size of a stub — while stubbing the transport leaves the memo gate, the `estate_judge.base_url` leaf and `self._http.borrow()` real, so the only forged thing is the hop that would have left the box. **44 → 0** connections._

_**"Which reading tests more" was refuted by driving it, and the refutation is the sitting's headline.**_ _Six cells — unread, idle and a lease naming every unit spelling in sight, each with and without `ServiceEntry.systemd_unit` forced non-`None` — leave **19 of 19** passing in all six. A witness over `_raise_judged` proves the granted cell was not inert: **21** judgements moved `critical` → `info` carrying `stopped_by_estate: True`, and no assertion moved. So the entry's stated reason for the immunity — a `kind: http` entry having no unit for a lease to name — is **wrong**, and the immunity is a property of what those files assert on rather than of their fixtures. With no reading discriminating, the choice is which reading is *true of the run being driven*, and `_NO_ARBITRATION`'s own docstring settles it: "nobody asked" must never be spent as "the estate holds nothing"._

_**The constant is imported rather than rebuilt**, so neither file can declare a reading production would never start at — `max_priority_for` against `PRIORITY_MAP`'s rule — and two files building one forged reading would be one fact stated twice._

_**Pinned by identity, and the falsification is what settled that.**_ _The production reader builds a fresh `ArbitratedStops` on every call, so `is _NO_ARBITRATION` fails on any box while comparing `reading` does not. Measured while removing each stub in turn: 8400 is up here and the real read answered **`idle`**, so a value comparison is red here and **green while dialling** where the estate is down. Three mutations driven — each stub removed in turn, and the production gate widened to `if True` so the never-asks half had something to be red about — each red on its intended test, and with either stub removed the other 19 assertions stay green, which is what makes the two new guards the only thing holding the fix._

_**A second figure in the entry was wrong and the instrument was why.**_ _Its cost of **16** connections per suite run counted *distinct* addresses per nodeid; every connect is **44** across the eight tests, so the clock cost on a box that drops packets is 2.75x what was filed._

_**The blind spot it was filed under now has an empty population, recorded rather than deleted.**_ _A test file whose connection is made *for* it by production code carries no token and no sweep over `tests/` can reach it — still true; what changed is that nothing holds the property. Connecting files **14 → 12**, and the four holding no spelling to the **2** that were always reconciled. The entry closes with **no check**: its honest instrument is the suite under a socket probe, which `check-snag-claims.sh` runs at both ends of a sitting and cannot afford, so the per-file identity tests outlive the finding — `FROZEN_TABLES`' rule._

_**Nothing was re-owned.**_ _`tests/test_arbitrated_stops.py` already holds the readings, the rung, the once-per-run memo and the savepoint placement, so the two files assert only *which reading they are driven at*. The `/api/health` gap noticed while restarting was **already recorded** — `SNAG-UNITS-003` counted it a fortnight ago and names `sysadmin-service` itself among the seven — so nothing was filed twice — it is in the Backlog as a *decision* owed, with the two shapes separated: whether the snippet generator should probe rather than guess, and whether this service should serve `/api/health` beside `/health` so the party enforcing the contract conforms to it._

_**A restart was owed and paid, for the sixth sitting running and by a third route to one shape.**_ _This sitting edited nothing under `sysadmin/` — three test files, four roadmap documents — and `monitor/agent.py`'s mtime moved at 12:30:59 when the `if True` mutation was reverted by hand, bytes identical to `9558544`. Restoring the mtime would have been fabricating evidence, so the restart is the honest repair: PID 1097551 → 1478358, counter **10 → 11**, back in seconds. **The document's own convention caught a second statement of one figure** — writing the superseded restart as `restarted at **2026-09-04 22:49:11**` matched `daemon_start`'s pattern twice and the claim went `unknown`; history carries a bare wall clock for exactly that reason._

_**One document defect fixed in passing.**_ _`HANDOFF.md` carried two `## Next action` headings, Session 174 having prepended its block without demoting its predecessor's, so `test_the_document_has_exactly_one_next_heading` was **red at preflight** — a second claimant on the line the estate board publishes verbatim. Nothing on the commit path runs that guard, which is `SNAG-TEST-005`._

_**Suite 3550 → 3553**, the baseline reconciled against Session 174's own figure rather than re-measured; ruff and mypy clean. All ten ops claims green, two of them corrected here — the `alerts` count fell **4 → 3**, the VRAM row resolving for a fourth time and found by the **fall** note alone, `check_open_titles` reading `ok` because a named row that has since resolved is not an unnamed open row. A fifth row opened mid-sitting and was **not** written down: `Unusual CPU usage` at 12:44:47, CPU 28.5% against a 7-day mean of 5.3%, raised by this sitting's own two full-suite runs and resolved by `_check_anomalies` at 12:49:50 on the next poll — the block was held at 3 rather than corrected twice, because a figure about the instrument is not a figure about the box. Register **137 entries, 25 → 24 open**; open entries with no check **4 → 3**._

---

# Handoff — 2026-09-05 (Session 174)

### The action Session 174 filed (done by Session 175)

Close `SNAG-TEST-008` by deciding what `tests/test_alert_dedup.py` and `tests/test_service_write_isolation.py` should be driven at when `SysAdminAgent._execute` reads the estate's arbitration — a patched-out `_ensure_arbitration`, which is one line and asserts nothing, or a real `ArbitratedStops` handed in, which is the stronger fix and makes each file state which reading its nineteen assertions are true under — and then take whichever it is in both files rather than only in the noisier one.

_**`SNAG-TEST-007` is closed, and the widening the handoff called one line was one line about the wrong thing.**_ _The obvious HTTP rule is the DSN rule's own shape — match `http://localhost:<port>` as `_DSN_HINTS` matches a connection string — and it does not transfer. Nothing in this tree **models** a DSN, so a connection string is evidence; a loopback URL is exactly how a fake service is spelled here, in a `ServiceEntry`'s `url`, a config leaf's expected value, an `httpx.MockTransport`'s base. Measured over `tests/`: **14** files carry one with a port and **4** connect to it, so the literal rule reports ten stand-ins and would put most of the service tests into the rule's population. `_LIVE_HANDLES` names the things whose job is to dial instead — **6 of 6** connecting files, no false positive._

_**The instrument was a `socket.connect` probe per nodeid across a green full suite**, the shape Session 173 used coverage for and chosen for the same reason: it answers whether a connection happened rather than asking an AST walk to guess. **14** files connect. Four hold no token and all four are reconciled rather than counted — `test_async_http.py` dials a `ThreadingHTTPServer` it started itself on an ephemeral port and is correctly outside the property, `test_gpu_lease_live.py` is in scope by the glob and marked, and the other two are `SNAG-TEST-008`._

_**The six judgements went four ways and two, which the handoff's framing did not allow for.**_ _It asked for a premise or a `PRE_CONVENTION` name for each of six. Four hold the widened property and each owed a premise: `test_abandoned_runs.py` owed the marker and already had the premise (`test_the_database_really_rejects_a_fifth_status`, docstringed "The premise the pin rests on" a fortnight earlier); `test_estate_project_contracts.py` owed one its skip gate resembles and is not, since `_estate_available()` is evaluated once at **collection** and asks only whether `/api/health` answered; `test_ops_claims.py` owed one for the **document** and none for the box, because every assertion it makes about the box holds whether or not 8500 answered; and `test_estate_surface_payloads.py` owed the strongest, being the file that held `SNAG-TEST-006`'s one live finding with no guard able to ask it for anything._

_**That last premise closed a gap nobody had named.**_ _`_check_ran` is the discriminator that separates a check running clean from one that errored and from one the producer retired, and it ran **only in the branch where a filter came back empty** — measured 2026-09-05, the live audit carries a `ports` breach and no `wiring` finding, so the ports guard took its populated branch and never asked whether `ports` had run at all. A discriminator consulted only when it happens to be needed is one whose own failure is invisible on the days it is not, so it is asked unconditionally now._

_**Two of the six owe nothing, and it was driven rather than read.**_ _Both reach 8400 through `SysAdminAgent._ensure_arbitration`, an unstubbed fail-open call inside the method under test, so they carry no token and no sweep over `tests/` can reach them — deciding which drive reaches a connection is a call graph over `sysadmin/`, which is Session 131's own reason for refusing one. Forging the producer's `ArbitratedStops` three ways — unread, a lease holding nothing, a lease naming every unit spelling in sight — leaves **19 of 19** passing in all three, because a `kind: http` entry has no unit for a lease to name and the reading reaches only `details['arbitration']`, which neither file asserts on. Neither a premise nor a `PRE_CONVENTION` name is right: that set is for files that **hold** the property and its tripwire asserts exactly that, so a name there would trade a red test for a false statement about the population._

_**The first stand-in for that drive had no `reading` attribute and turned all 19 red**, which is a stand-in that cannot answer wearing the clothes of a result — and it is also what showed that the arbitration reading reaches the alert's `details` at all, one line further than `stopped()`. The second drive used the producer's own dataclass._

_**The handle tripwire refused a member within one test run.**_ _`query_one` was the obvious fourth handle — it is the reader every registered snag check goes through — and `test_every_handle_is_used_by_a_drive` reported it unused: it is named in exactly one file and named there only as the string inside `patch.object(snag_claims, "query_one", …)`. A name whose only appearance is a stub is the **opposite** of evidence, since it marks the connection being taken out. Recorded in the constant rather than quietly dropped._

_**Nine mutations driven, one survived and bought a test.**_ _Deleting the clause that reads a **qualified** use broke nothing, because every handle in this tree happens to be imported by name today — so the clause was carried by a coincidence in the current tree, and `import ops_claims` plus `ops_claims.check_all(...)` was a way out of the rule nobody would have chosen and nothing would have reported. Each of the four gained files was separately driven **unmarked**: each goes red post-fix and **green** pre-fix, which reproduces the blindness four times rather than asserting it once._

_**The exemption's stated reason improved without moving.**_ _`test_snag_claims.py` was documented as the one file reported for the **wrong hit** — matched on a `sync_url` read that asserts a DSN's shape and never connects, while the real connection was transitive. `check_all` is a handle now, so the file is reported for what it does; the exemption is unchanged, and what changes is that deleting that `sync_url` assertion no longer silently drops the file out of the population._

_**No restart, and none owed.**_ _This sitting touched no file under `sysadmin/` — five test files and four roadmap documents — so the deploy check stays green at the 2026-09-04 22:49:11 start. Suite **3542 → 3550**, the baseline measured by running it before anything was edited; ruff and mypy clean. All ten ops claims green: the `alerts` pair was **red at preflight** and is corrected here, the VRAM row having risen for the third crossing in three sittings, and this time **both** halves fired — the count rose and the marked sentence failed to name the new row, which is the direction the fall note is silent in. Register **136 → 137** entries, **25 open** unchanged: one closed, one opened._

---

# Handoff — 2026-09-05 (Session 173)

### The action Session 173 filed (done by Session 174)

Close `SNAG-TEST-007` by widening `tests/test_live_drive_premises.py`'s `_opens_a_live_connection` past the DSN literal it keys on today, so that a drive reaching the box over HTTP and a drive reaching PostgreSQL through a helper both hold the property, and then take the six per-file judgements that widening owes — a `@pytest.mark.premise` or a reasoned name in `PRE_CONVENTION` for each of `test_estate_surface_payloads.py`, `test_estate_project_contracts.py`, `test_alert_dedup.py`, `test_service_write_isolation.py`, `test_ops_claims.py` and `test_abandoned_runs.py`.

_**The sweep is done and its one live finding was not where the handoff pointed.**_ _`TestTheConventionAgainstTheRealDocument`'s prediction guard now runs, the block having gained its first `expires` member on 2026-09-04, so the hunt found the successor rather than the founder: `test_a_live_wiring_finding_still_separates_its_two_events` filters the estate's audit findings to the `wiring` check, which has filed **nothing** in its whole history, so its three assertions had never executed. Measured live at **0** wiring findings against 4 total._

_**Coverage was the instrument, chosen for what it can answer.**_ _An AST walk would have to guess which iterables are live; coverage answers directly whether an assertion ever executed, and so catches shapes nobody predicted. At 3538 tests: **8** `assert` statements under `tests/` never evaluated, **0** `for` loops never iterated, **282** unexecuted statements in total and every one categorised — 86 multi-line `with (` artefacts, 44 untaken skip gates, 41 helper early returns, 14 deliberate failure paths, and no further member of the class. Run through an ephemeral `uv run --with` overlay: **122** packages and an unchanged lock either side._

_**Direction is the whole discrimination, and reading the symbol without it inverts the answer.**_ _A `for` missing the arc into its body never iterated; one missing the arc out of it always returned early, which is the ordinary shape of a helper walking an AST and returning its match. Both are spelled "partial branch". Read without direction the sweep reports **13** findings and **12** are wrong._

_**The premise reports and never refuses, which is the opposite of the sibling live drive's.**_ _`test_arbitrated_stops_live.py` fails when no lease names `stopped_units`, because such a lease is expected to exist; zero wiring findings is the estate's hooks being correctly wired, so refusing an empty population would turn a healthy estate into a red suite. What must not pass unnoticed is the other road to zero — the producer **retiring** the check, identical at `/api/audit/findings` to a clean run — and `_check_ran` reads `last_audit.checks`, where the estate publishes both the membership and the `error`. `ports_checked`'s rule, asked of another repository's audit._

_**The sibling guard's docstring was wrong about itself, in the good direction.**_ _`test_a_live_ports_breach_still_carries_an_integer_port` read "the ports check has never reached `breach` on this box"; coverage says its assertion evaluates and the live audit carries `ports:port 3110:unclaimed_listener`. It can go back — 3110 is a transient dev-server holder and the finding set moved from 6 to 4 inside this sitting — so the branch was added there too rather than the sentence merely corrected._

_**Four tests added and stubbed rather than gated on the estate**, so both roads are driven on every run and on any box: the live class can only exercise whichever branch the box happens to be in, which is the empty one for `wiring` and the populated one for `ports`. Four mutations driven and four killed, each on its intended test — dropping the empty branch reproduces the pre-fix behaviour and turns two red, an unconditional return turns the populated-filter test red, and a premise that refuses an empty population turns the clean-check test red._

_**Two findings were recorded rather than changed.**_ _`test_arbitrated_stops_live.py`'s three unevaluated assertions are a documented both-ways contract with a marked premise companion — the model this fix followed. `test_sse.py`'s two are deadline guards inside polling helpers, where non-execution means the wait completed at once._

_**The instrument's own blind spots are stated, because two of them bit.**_ _The first socket probe tested `isinstance(address, tuple)` and so dropped every AF_UNIX address, reading zero-because-blind as zero-because-clean inside the tool written to find exactly that. And `socket.connect` is blind to psycopg2, whose libpq connects in C — which is why four files carrying premise markers report zero connections for connections they genuinely make. Line coverage is blind to the comprehension shape for a third reason: `assert all(f(x) for x in live)` is true over an empty `live` and the line executes, so the **309** asserts carrying a comprehension needed a hand sweep, ten of them over a live iterable and two over the real block, whose population is a measured **11** markers._

_**No restart, and none owed.**_ _This sitting touched no file under `sysadmin/` — only `tests/test_estate_surface_payloads.py` and the four roadmap documents — so the deploy check stays green at the 2026-09-04 22:49:11 start. Suite **3538 → 3542**, the baseline measured by running it before anything was edited rather than read off the STATUS cell; ruff and mypy clean; all ten ops claims green with **11** markers still read; register **134 → 136** entries, **23 → 25** open, nothing closed._

---

# Handoff — 2026-09-04 (Session 172)

### The action Session 172 filed (done by Session 173)

Sweep the suite for live-document guards whose loop body has never executed — the shape `TestTheConventionAgainstTheRealDocument`'s prediction test was in for eleven days, where what it asserted was that an empty `for` completes — by measuring, for every test that iterates over a live artefact's members rather than over a fixture's, whether that population is non-empty on this box, and deciding per finding whether the guard gains an anti-vacuity premise naming the emptiness or is honestly recorded as unreachable here.

_**The `expires` family has its first live member, and the sitting's headline is that measuring the boundary moved it by a day.**_ _`SNAG-LOG-014` states its own remedy as a **date**; retention purges `log_entries` on `ingested_at` at a **fixed** 03:00, and the newest of the four residue rows was ingested at **19:50:19** on 2026-08-17, so thirty days lands that evening — after the 09-16 run. Driven at the real `purge_statement` against the live table at four candidate cutoffs: **0 of 4** on 2026-09-16, **4 of 4** on 2026-09-17. The block now carries `2026-09-17T03:00+01:00` and `sysadmin-check-claims` reads `12 days to run`._

_**The rule 7 question the handoff asked was answerable by measurement rather than by judgement, and the answer is no restatement.**_ _All six `CLAIM_PATTERNS` are anchored on lexical context — `N routes`, `head N`, `holds N unresolved`, `restarted at …` — never on bold alone, so a bare wall clock matches none of them in either spelling and naming `03:00` in the prose adds no `unclaimed:` finding. The instant stays rule 9's single licensed exception: stated twice, pinned rather than trusted._

_**The first live member turned out to be exactly the case `SNAG-DOCS-008` closed, by a route that entry did not predict.**_ _Its measurement was that 28 of 88 distinct wall clocks are stated more than once, so an arbitrary instant had a 6 % chance of being pinned by an unrelated sentence. The region stated `03:00` **once** at `305152a` and it is **not a clock**: it is the PCI bus address in `amdgpu 0000:03:00.0`. Driven both ways with the marker on a sentence omitting the clock, the sentence-scoped pin returns `unknown` naming the remedy and the pre-`SNAG-DOCS-008` region-wide pin returns `match` against a device identifier. A five-character needle cannot tell a time from a bus address, so the hazard is wider than a count of clocks could see._

_**Two guards were broken and neither could have been found without a live marker.**_ _`TestTheConventionAgainstTheRealDocument`'s prediction test has stood since 2026-08-24 with its loop body never once executed, and driven at the first real marker it is half a guard — it keys on two note substrings, so a naive instant (`SNAG-ESTATE-013`'s own founding shape), an unparseable one and a marker carrying no instant **all passed**, verified at the real document before it was touched. And `TestThePinIsNarrowedToOneSentence._claim` took the **first** `expires` marker, which named its own planted one only because the block carried none — so the zone-fault drive silently began measuring this sitting's prediction and asserted `match` where it wanted `unknown`. `SNAG-LOG-004`'s ordering a fifth time, with a document edit as the widening and the suite as the reader._

_**The block is its own regression test and its first draft was wrong about that, which is the part worth carrying.**_ _The paragraph said "this block states `03:00` **once**" — true of the region measured and false of the region a reader holds, because writing it put the needle in five more times. A paragraph stating a property of a region it goes on editing can be falsified by its own author an hour later, so every figure in it is now attributed to a cause and dated to a commit; the sitting as a whole moved the collided set **28 → 31**, and only part of that is the prediction._

_**A concurrent sitting was working the same handoff and stood down without writing.**_ _`sysadmin-assistant-38` found the half-guard, which this session had missed by searching for `STATUS_PATH` where that test reaches the document through `load_region()`, and independently derived the same instant from six consecutive purge runs. Both of its findings were verified here before acting rather than taken on trust — the `03:00`-count claim it sent was measuring its own candidate prose, and its seven was six, `\b` finding no boundary inside `…T03:00…`, so the marker is invisible to the very needle it is pinned by._

_**The date was one cause stated five times and the correction is scoped deliberately.**_ _Fixed in the entry twice, in `message_backfill.py`, in `snag_claims.py` and in `tests/test_snag_claims.py`; the three statements inside the **closed** `SNAG-LOG-008` are left standing on this file's own precedent that rewriting a closed entry edits the record of the sitting that wrote it. The check is unaffected either way — its argument is that retention empties the population, and a day does not move that._

_**One restart, and it bought the box prose.**_ _PID 1055352 → 1097551 at **22:49:11**, restart counter **10**, the fifth consecutive sitting to pay for a restart that changes no behaviour: this sitting edited two docstrings under `sysadmin/`, and what actually raised the deploy check was `ops_claims.py`, byte-identical to `305152a` with an mtime moved at 22:43:32 by a mutation drive restoring it from its own `.bak`. The recorded `git stash pop` shape reached by a second route. A first attempt at the restart read `MainPID` from `systemctl --user` for a **system** unit, which answers `0` rather than failing, and `kill -TERM 0` signals the caller's own process group — it killed the tool's subshell, the daemon was untouched, and the retry guards on the pid being greater than 1._

_**Seven mutations driven and seven killed**, each on its intended test — four at the new `TestTheLiveBlockCarriesAPrediction` (marker deleted, offset dropped, marker moved off its sentence, a passed boundary reported as agreement) and three at the widened guard. Suite **3534 → 3538**, the baseline measured by stashing to `305152a` and re-collecting rather than read off the STATUS cell, which is **216** stale; ruff and mypy clean; all ten ops claims green and all **21** snag entry checks holding beside the register's three meta-checks — `check-snag-claims.sh` prints **24** `ok` lines and the three are disposition, next-action and movement, which is a distinction the first draft of this paragraph did not make; register unmoved at **134 entries, 23 open** — nothing closed, one date corrected._

---

# Handoff — 2026-09-04 (Session 171)

### The action Session 171 filed (done by Session 172)

Give the `expires` family its first live member by writing a prediction into the STATUS.md block for the 2026-09-16 retention boundary that clears the two journal rows a resume boundary duplicated, measuring first whether the prose can name the local wall clock the marker renders without restating a figure rule 7 forbids — the family has shipped untriggered since 2026-08-24 and every guarantee about it, this sitting's included, is driven at planted markers rather than at one the document actually carries.

_**`SNAG-DOCS-008` is closed, and Session 170's reason for leaving it open described one of the pin's two directions.**_ _That handoff asked whether rule 9's instant pin should follow rule 10 onto one sentence. It should: **not** finding the instant is `unknown` and loud, as rule 10 said, but finding it in an **unrelated** sentence is `match` and silent — rule 10's own defect with a five-character needle drawn from 1440 values._

_**Measured before deciding, and the curve is the one rule 10 closed on.**_ _The printed region states **86** distinct wall clocks, **28** of them more than once — 6.0 % of the day, up from **5** eight days and 150 kB earlier. The collision is not random: a prediction names this box's schedule and so does the block, so `05:45`, `05:15` and `03:00` are values both carry._

_**Driven at the live block, because the fixture cannot have the property under test.**_ _A marker reading `2026-09-05T04:45+00:00` beside a sentence saying `04:45` — a UTC stamp copied into a BST sentence, `SNAG-ESTATE-013`'s founding fault — came back **`match`**, swallowed by eleven unrelated mentions of `05:45`; against a block that does not happen to say `05:45` the same marker returns that entry's own diagnostic. The haystack is **187,933 → 167** characters._

_**`claim_sentence` could not be called, which is exactly what the handoff said to measure first.**_ _It finds a sentence by **key** and refuses a key stated twice; `expires` is the one family whose members the document declares, so two predictions are two markers with one key. `Marker` carries the sentence it stands in now — a question about the **occurrence** rather than the name — and `claim_sentence` became a key lookup over `read_markers`, so both narrowings share one locator by construction._

_**Two silent widenings were found by writing the fixture the new message asks for.**_ _The note tells an author to move the marker into the sentence naming the clock; written flush against the full stop, `SENTENCE_END_RE` saw no terminator (it wants whitespace after one, and a marker is neither) and the sentence ran **backwards** through the preceding paragraph. Blanking the marker then moved the anchor **past** the terminator and the sentence became the next one, which is empty. `_unmarked` and `_anchor` are the halves: what is a marker is not prose, and a marker belongs to the sentence it **closes**._

_**Filed in this repository's own namespace.**_ _`SNAG-ESTATE-017` would have been the fifteenth collision with estate-manager, who are at **131**; their message `153c1c96` records that namespace as having two minters and no owner, and this is the claims machinery rather than the estate._

_**Ten mutations driven, each red on the named test.**_ _Pinning the whole region again turns **12** red; routing the pin through `claim_sentence` turns the same 12 red; emptying the shared locator turns **31** red across *both* narrowings, which is the signature of a locator that is genuinely shared. Suite **3526 → 3534**, `ruff` and `mypy` clean, register **23** open and none opened._

_**The block's own claims moved while the sitting ran.**_ _`High VRAM usage on AMD Radeon RX 7900 XTX` resolved again — the second crossing in two sittings on a card four services share — so `alerts` went **4 → 3** and the named list lost a title in the same edit; `check_alerts`' fall note caught it, which is `SNAG-ESTATE-008`'s founding case for the third time this week._

_**No restart is owed in substance and the deploy check reports one anyway.**_ _`ops_claims.py` is a console script the daemon never imports, so this is rule 4's stated cost rather than stale code on the box — the fourth such report in three sittings, and `SNAG-SYSD-007`'s restart budget is the reason it was not paid reflexively._

---

# Handoff — 2026-09-04 (Session 170)

### The action Session 170 filed (done by Session 171)

Decide whether `check_expiry`'s instant pin should move to `claim_sentence` as well — rule 9 already admits searching the whole printed region is "the weaker half", a block naming one wall clock twice for two different reasons satisfies it, and the narrow reader now exists — measuring first whether a per-marker anchor is even expressible, since `expires` is the one family whose members the document declares and several markers may legitimately share one key, which is the shape `claim_sentence` refuses outright.

_**`SNAG-ESTATE-016` is closed, and the entry's stated fix was right about the rule and silent about the sentence.**_ _`claim_sentence` locates the sentence bearing the `open_titles` marker and matches each unresolved title against that alone: **178,301 → 290** characters at `9a3fe30`. Nothing about the substring test changed, and nothing about the reserved direction did either — a *name with no row* still belongs to `check_alerts`' fall note, which is what lets the block's parentheticals go on naming resolved titles without offending anything. Suite **3504 → 3526**, `ruff` and `mypy` clean, register 24 open → 23, none opened._

_**Falsified against the real commit, and the premise is asserted before either verdict is believed.**_ _`TestTheBlockThatOpenedTheEntry` reads `9a3fe30:docs/roadmap/STATUS.md` out of git rather than modelling its shape: it pins the flattened length first, because a specimen that had drifted would let both verdicts pass for the wrong reason, then shows the sentence named `GPU was reset — every client lost its VRAM` (resolved) while omitting `High VRAM usage on AMD Radeon RX 7900 XTX` (open), whose **one** occurrence in the region sits more than **5,000** characters below the marker._

_**The control is what makes the refutation mean anything.**_ _The **same** block still matches the four rows its own sentence describes — same 178 kB, same sentence, a different population — so the verdict moves with the population rather than with the change. The "can never match" mutation proved it load-bearing: it took eight tests down and left the refutation test standing, which is exactly the reading a check that had merely got louder would produce._

_**Rule 7 survives the marker becoming load-bearing, and rule 2 is the reason.**_ _A marker may never gate a check. Here it decides *where* to look rather than *whether*, since the population comes from the alert table and is read either way — so an absent marker is `unknown` with the remedy named and **never** `match`, driven at one block in both spellings. Two markers sharing one key are refused rather than resolved (`read_claim`'s rule), which is a live shape in this document: `migration_head` is marked in two places._

_**A test credited the wrong mechanism and was green when that mechanism was deleted.**_ _The quoted-title test names the lookahead; what actually saves `sysadmin.service` is the code-span veil, which blanks the span before any boundary is looked for. The lookahead's own population is a **bold decimal in prose** — and the figure has to sit *between* the titles and the marker, because a cut ahead of the list leaves every title inside the sentence and the fixture then agrees with the mutation it was written to kill. Both halves were wrong on the first attempt._

_**The terminator's trailing class came from a measurement nothing else would have made.**_ _The first pattern demanded whitespace immediately after the stop and agrees with the shipped one on **both** real blocks. The region carries **290** prose full stops with no space after them, overwhelmingly a full stop closing a bolded lead-in — how nearly every paragraph in the session block opens — so without the class the terminator is refused and the marked sentence runs backwards through the whole lead-in: this entry's defect at one paragraph instead of at 178 kB._

_**No check for the closed entry, and none was owed.**_ _It was one of the three open entries carrying none, so nothing had to be re-homed — and a check driven at a landed fix reports `still holds` for ever anyway (`check_review_schedule_unread`'s defect). The guard is a test, `FROZEN_TABLES`' rule._

_**Deployed, and this sitting's own STATUS.md block is a regression test.**_ _Writing it puts a fourth copy of `High VRAM usage on AMD Radeon RX 7900 XTX` into the printed region, above the sentence that claims it — under the old rule that is precisely how a name got written down for ever. The region grew **178,301 → 187,789** characters with the marked sentence unmoved at **289**. Thirteen mutations driven and thirteen killed, each by a test that names it._

---

# Handoff — 2026-09-04 (Session 169)

### The action Session 169 filed (done by Session 170)

Close `SNAG-ESTATE-016` by narrowing where `check_open_titles` looks — match each unresolved title against the sentence carrying `<!--check:open_titles-->` rather than against the whole 178 kB printed region, so a title written down by a past sitting stops satisfying the check for ever, and falsify it against the real `9a3fe30` block, where the sentence named a row that was not open and the check still reported `match`.

_**`SNAG-CFG-006` is closed, and it closed by derivation rather than by a verdict.**_ _`read_ceiling` widens `journalctl -p` to whatever the loudest `arrives_at` needs and `admits` lets a declared signature past the rung gate; both take the same `declared` mapping, so they cannot drift apart. `declared_rungs_for` supplies it, keyed on `stored_source_name` — the **unit** for a journal source, the **name** for a file one — where the old visibility test used `source.name` and was green only because `kernel`'s two identities coincide. Suite **3478 → 3504**, `ruff` and `mypy` clean, 20 pre-existing snag checks unmoved either side by stash-diff. Two entries opened: `SNAG-LOG-018` and `SNAG-ESTATE-016`._

_**The entry's own named fix was measurably inert, and only running it said so.**_ _It asks for the `-p` ceiling and `read_journal` has **two** severity gates — the second is the Python filter its own docstring calls the authority on what is stored. Driven against the live kernel journal with `severity_filter` at `error`, forcing `-p 6` returns the **same 32 entries** and the **same zero** `VRAM is lost due to GPU reset!` lines. Reading the entry gives you half a fix; running it gives you the other half._

_**Widened per signature, never wholesale, and the second number is what makes that honest.**_ _Live at the narrowed config the reader goes **32 → 35** stored with **0 → 3** VRAM lines, and **1,788** undeclared info lines are still dropped — so the operator's narrowing still governs everything nobody has spoken for. Dropping the floor to the declaration's rung instead would have stored all 1,823 and made the config edit a no-op, which is worse than the gap it closes._

_**Two of ten falsifications passed against deliberately broken code, and both were the wiring.**_ _`declared=None` at either call site left all 74 tests green, because every one of them handed `declared` to a reader itself — *"nothing drove `_record_start`"*, a fifth time. Two behavioural drives now go through the real `read_journal` and the real `_read_log_file` with a narrowed source and ask whether the declared line survived._

_**The new AST guard caught two things, one of them its own author.**_ _`TestNoReaderGatesOnSeverityByHand` refuses a third hand-rolled severity floor. Its first draft keyed on the **name** `SEVERITY_ORDER` and reported `sysadmin/core/escalation.py`, which owns a *different* constant — three alert rungs against five log severities, a collision the aggregator's own import comment already records as a trap — so it keys on **provenance**, the import from `sysadmin.monitor.journal`. It then went red on this sitting's **own new snag check**, which compared two configured rungs by hand; that check asks `admits` now, which is the gate's own question._

_**`SNAG-LOG-018` is the measured cost, and its first draft claimed no remedy existed.**_ _A narrowed declaring source reads at `-p 6` and stores at `error`, spending **1.9 %** of its read budget on entries it keeps — against the 40 % Session 62 named as the defect `-p` was added to remove. Checking for a remedy took a minute and found one: `journalctl --grep` filters *within* a priority selection and returns **3 lines of the 1,825**. It is refused on **cost rather than absence** — the declaration's key is the *normalised* signature, so the pattern would be a second implementation of `signature()` as a regex, and two reads fork the cursor `SNAG-AGENT-005` exists to keep single._

_**The new check found a defect in itself under falsification.**_ _One of its three mutations — a declaration arriving at a rung the narrowed filter already admits — passed against broken code, because the "no residue to observe" sentence went into the same list the verdict was computed from. Two lists now: `ports_checked`'s rule, broken inside a check written to honour it._

_**No check was added for the closed entry, deliberately.**_ _`check-snag-claims.sh`'s `ok` means *the bug is still real*, so a check driven at a landed fix reports `still holds` for ever — `check_review_schedule_unread`'s defect. The guard is a test, `FROZEN_TABLES`' rule: the AST sweep above, plus `test_a_narrowed_source_still_reads_its_declaration`, which drives the shipped source **narrowed to the value that used to disarm it** — a stand-in modelling the fix, since against the shipped `info` every assertion in it passes for free._

_**The handoff's "three open entries still lacking" was not reproducible, and this sitting's first attempt to re-measure it was wrong in its own hand.**_ _A marker scan written here read `<!--check:[a-z_]+-->` and so missed `estate_port_8500`, reporting `SNAG-ESTATE-005` as unchecked when it carries one — found by reading the entry rather than trusting the count. Re-measured: of the **23** entries whose `**Status:**` bullet says Open, exactly **one** lacks a marker (`SNAG-LOG-016`, which refuses one and gives the reason), unmoved either side. What `SNAG-CFG-006` lacked was **both** a `**Status:**` bullet and a marker, which is what kept it out of every count._

_**A green check disagreed with a hand-corrected block, and that is the second entry.**_ _`SNAG-ESTATE-016`: `check_open_titles` matches each unresolved title as a **substring of the printed region**, which is **178,301 characters** of accumulated history — so a name written down by any past sitting satisfies it for ever. At `9a3fe30` the sentence named `GPU was reset — every client lost its VRAM` while the row actually open carried `High VRAM usage on AMD Radeon RX 7900 XTX`, and the check reported `4 named, 4 open`, `match`. The fall note its docstring delegates the other direction to fires on a **count**, and the count was right — so nothing caught it until a row happened to resolve an hour later. The fix is a narrower haystack, not a new rule, and it is the next action._

_**`SNAG-CFG-003` is untouched and now carries why.**_ _It filed itself as the same class, and the two turn out to take **opposite** fixes: this entry's terms are both the reader's, so one derives from the other and the relation stops existing; that entry's terms straddle an ownership boundary — `may_quieten_in_place` rule 3 forbids the daemon reading the tray's `reminder_hours` — so no production code may hold both and a semantic verdict is the only shape available. Only the member whose terms share an owner can dissolve._

_**Deployed, and the fix's own branch is invisible on the box.**_ _Daemon restarted at 15:47:32, PID 621239 → 658806, `/health` 200, four clean `log_aggregator` runs. The shipped `severity_filter: info` already admits the declared line, so the daemon can only witness *no regression* — the branch's evidence is the in-process drive against the real `journalctl` at the narrowed config, which is where it was taken. Ops claims corrected too: unresolved alerts fell **4 → 3** when `High VRAM usage` resolved itself, and the block had been naming `GPU was reset` as its fourth while the row actually open carried the VRAM-usage title, which `check_open_titles` cannot see by design._

---

# Handoff — 2026-09-04 (Session 168)

### The action Session 168 filed (done by Session 169)

Take `SNAG-CFG-006`'s own named runtime fix in the sitting it asks for — derive `read_journal`'s read ceiling as the louder of `max_priority_for(source.severity_filter)` and the loudest `arrives_at` any `CRITICAL_SIGNATURES` entry declares for that source, so a `SIGHUP` narrowing the kernel source back to `error` cannot disarm a declaration while the suite stays green — and give the entry the disposition and the check it is one of three open entries still lacking.

_**`SNAG-DOCS-003` is closed, and the surface it protected had never been published.**_ _`sysadmin_tray/_deprecated_contracts.py`, the PEP 562 `__getattr__` in `sysadmin_tray/models.py` (with the `warnings` and `Any` imports it was the only reader of), `check_deprecated_contracts` with `DEPRECATED_MODULE`, `DEPRECATED_NAMES` and the `_names_used` helper, and four of the five guard tests are gone. Open entries **24 → 23**; nothing opened. The commit cites estate message `e045373e`, filed by Session 163 before the change it announces._

_**The blocker was re-measured on the day rather than quoted from the sitting that refuted it.**_ _**31** `sysadmin_service` wheels on this box and **0** carrying `sysadmin_tray/` code, checked by `unzip -l` rather than by name; **no git remote and no upstream** for `main`; and an AST sweep of **20,795** `.py` files outside this checkout across `~/projects`, `~/.claude`, `~/.local` and `~/.config` finds **0** importers. Keyed on the **import** and never on the name, because estate-manager defines all five names itself off its own `Contract` base — a name-keyed sweep answers 5/5 over there and names the wrong party. Falsified before it was believed: a planted `from sysadmin_tray.models import RecommendationInfo, PortfolioAction` beside a decoy **local** `class RecommendationInfo` gave importer reported, decoy ignored._

_**The removal moved a measurement nobody was aiming at, which is the part worth carrying.**_ _`test_contract_reachability`'s docstring recorded that the walker, driven at the **pre-fix** registry, could judge only **12** of the 15 unreachable models — `PortfolioAction` and `RecommendationInfo` leaking in as roots from the shim's own annotations and base class, and `PortfolioActionsResponse` from `models.PortfolioActionsResponse` in the shim tests. Both sources went with the fix, and the same drive at `2bfa5c8~1:sysadmin/core/contracts.py` now reports **15 of 15** — measured either side, not inferred from the deletion. So the entry's stated reason for keeping `test_none_of_them_are_defined_in_contracts` (*the only cover for three names reachability cannot judge*) **expired on the commit that closed it**; the test stays on a stronger claim, refusing a name that comes back **with a reader wired to it**, which reachability would pass._

_**Four tests went where the entry said three, and the discrepancy is instructive in both directions.**_ _`test_the_deprecated_set_is_closed_under_its_own_references` imports the deleted module, so it could not survive whatever one calls it; the three the entry counted are the ones exercising attribute access on `sysadmin_tray.models`. Two of those three **would have gone on passing** — after the removal, `test_a_live_re_export_does_not_warn` and `test_an_unknown_name_still_raises_attribute_error` assert a Python language guarantee about a module with no `__getattr__`, which is worse than a red test because a vacuous green reads as coverage of a mechanism that no longer exists._

_**A second empty population arrived with it and is stated rather than left as silence.**_ _`PortfolioAction` over `RecommendationInfo` was the registry's **only** subclassing pair, measured by walking every `ClassDef`'s bases in `contracts.py`, so rule 3's base-class edge now has no member there. The edge is still exercised — by the synthetic falsification, where `Contract` is reachable by that edge alone and named by no reader — and the docstring says so, because an untested rule and a rule with an empty population read identically from outside._

_**Writing the marker's own text into the closing bullet re-armed the guard the closure retires.**_ _The first draft of the snag entry's retirement bullet quoted `<!--check:deprecated_contracts-->` verbatim to say it was gone, and `test_no_marker_in_the_real_file_names_a_check_nobody_implements` went red: the marker vocabulary is **document-wide**, not entry-scoped, so a bullet reproducing one names a check nobody implements whatever the sentence around it says. The bullet names the check *key* instead — which is what `SNAG-ESTATE-013`'s own retirement bullet had already done, and reading it first would have saved the red._

_**The check retired and no detector needed re-homing**, which is the first closure here where `FROZEN_TABLES`' rule is satisfied by something that already existed: the guard against this class returning is `test_none_of_them_are_defined_in_contracts`, kept. Note it would **not** have gone on reporting `still holds` over a landed closure — its first branch answers `mismatch` naming the missing module — so it went because every member of `CHECKS` names an open entry, not because it had stopped discriminating._

_**One edit the previous sitting recorded as owed is discharged by deletion rather than correction.**_ _`check_deprecated_contracts`'s docstring still said the operational fact was one "this repository cannot check", which Session 161 refuted; the check is gone, so the wrong sentence went with it and none was written into a function nothing calls._

_**Measured either side.**_ _Suite **3485 → 3478**, which is the arithmetic and not a coincidence: 4 retired from `test_contract_reachability` and 3 from `test_snag_claims` (the check's two falsifications plus `test_the_deprecated_module_still_holds_the_five_names`). `ruff check .` and `mypy sysadmin` clean. Entry checks **21 → 20** with every survivor unmoved, ops claims green, and the daemon restarted so the deploy claim reads `ok` — nothing the daemon serves changed behaviourally, `snag_claims` being a console script, but the box matching the checkout is the claim that gets checked._

---

# Handoff — 2026-09-04 (Session 167)

### The action Session 167 filed (done by Session 168)

Delete the five deprecated contract models from `sysadmin_tray/_deprecated_contracts.py` and close `SNAG-DOCS-003`, whose removal has been unblocked since 2026-09-03 with the audience measured empty, every off-box route closed and the change already announced at estate-manager as `e045373e`, so what remains is two deletions and a test edit.

_**`SNAG-SYSD-008` is ranked P3 → P4 and measured, and both halves of the brief changed the entry.**_ _`memory.stat` answers the 462 MB in two lines: **`anon 155 MB` against `file 298 MB`**, with `inactive_file 298 MB` and `active_file 0`, so every byte of the file half is cold and reclaimable and `memory.current` was never the daemon's demand — the process itself reads `VmRSS 178 MB`. A cgroup counts page cache; "resident set" conflated the two._

_**The entry's own first suspect is refuted, and it was costed against a row count 8× too high.**_ _`GET /api/logs/trends` serves in **44–48 ms** with **zero** anon growth across five requests, because the `GROUP BY` runs in PostgreSQL and the collapse to ~44 signatures never enters Python. `log_entries` holds **84,265 rows**, not the 627k the entry cites — retention purged it — though the table is still **602 MB** of dead-tuple bloat and `alerts` is **374 MB for 13 live tuples**, which is PostgreSQL's resident set and structurally invisible to this cgroup._

_**The resident set is the file organiser, and it is a read the daemon never re-reads.**_ _`file_hash` reads the **first 1 MB of every file ≥ 1 KB** under the scan root for its duplicate fingerprint — **317,180 files**, a 16.45 GB upper bound, of which the daemon faulted **5.07 GB from disk** in one 97-second scan. Both the scan thread and `journalctl` (via `create_subprocess_exec`) run inside the cgroup, so the pages are charged here; the journal half is not the cause, its startup catch-up having reported `truncated_sources []`._

_**Steady state costs nothing and the scan was driven rather than reasoned about.**_ _Across 23 idle minutes `read_bytes` was **frozen** at 5,067,542,528, `memory.events max` frozen at 17,331, and `memory.pressure full` advanced **26 µs per 10 minutes**. A manual `POST /api/files/scan` (94.76 s, 25,483 findings) sampled at 2 s pinned `memory.current` at **511.6–512.0 MB for the whole scan**, took reclaim **17,331 → 34,804** at ~184/s and pressure **83,055 → 165,871 µs** — **82.8 ms of stall for the scan, against 83 ms for the 2.4 hours before it**._

_**There is no leak, and peak-against-uptime is what kills it.**_ _A **4 min 33 s** invocation peaked at **512M**; an **11 h 3 min** one at **230.5M**; 9 h 55 m → 224.9M and 12 h 28 m → 226.5M. A leak is monotonic in uptime and this is bimodal. What *does* ratchet is the **anon** half — the scan took it 146.4 → **230.8 MB** (the hash dicts, ~281 bytes per file) and it fell back only to **203.2 MB**, CPython not returning fragmented arenas — and that is the half that can OOM, since page cache is a compressible buffer. The margin is in the **file count**, at roughly **4×** today's 317k._

_**It has never been killed, and the rerank Session 165 proposed rests on a misread line.**_ _Every stop in the unit's whole recorded history is `Deactivated successfully`, with `oom 0`, `oom_kill 0` and zero `oom` matches for this unit anywhere in the journal. systemd prints `Consumed … 512M memory peak` on **every** stop as routine per-invocation accounting, so the 10:50:15 line read as an OOM restart is a postmortem statistic about a clean exit. That was the entry's whole case for outranking `SNAG-LOG-015`._

_**Raising `MemoryMax` is refused on measurement, which inverts the entry's own ranking of its two candidates.**_ _It was filed as the cheap option that treats the symptom; it treats nothing that costs. The box has **186 GB RAM, 166 GB available, 152 GB already in page cache and zero memory pressure** — the cap is **0.27 % of RAM**, so the reclaim is an artifact of the cap rather than of scarcity and a bigger number buys a bigger throwaway cache. The fix matching the cause is `os.posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` after each hash chunk, which is also what the historical **169–252 MB swap peaks** are: the cap paging out the working set to hold cache nothing will read again. Untaken here, because the brief was to rank and measure._

_**One residual is stated rather than explained.**_ _Across **2026-08-28 → 08-31** every invocation peaked at **222–246 MB**, including a 12 h 28 m one, while `file_organiser` ran **14 times on 08-28 alone** — so the scan ran and the ceiling was not reached. The transition is a continuum (08-27 21:00 → 453.9M, 22:26 → 231.6M), which is what "how much of the read set the daemon is *first* to fault in" would produce, and boot −3 spans both halves so uptime does not separate them. Nothing here measures what does, and guessing would be the third mechanism this entry has had asserted without measurement._

_**What survives, and why it stays open at P4**: the anon ratchet above, and that **no health surface reads the unit's own cgroup** — `/api/sysadmin/self` reports agent liveness and `/api/sysadmin/resources` reports the *box*, so the one number that would have ranked this in a minute is served nowhere. `SNAG-SYSD-008` is still **one of three open entries carrying no check**, with `SNAG-LOG-016` and `SNAG-CFG-006`; a check is now writable against the restated claim and was left for its own sitting rather than ridden in on a measurement that changed what the entry says._

_**The register caught the consequence of its own closure.**_ _Adding the disposition took `Open entries declaring no disposition` from 2 to 1, and `The next action names work nobody is owed` immediately flipped to `??` because the board's line still named a now-`decided` entry — which is why the action above names `SNAG-DOCS-003` instead — and naming it exposed that **that** entry was unreadable to the register too: `disposition_word` takes the first token after `Open — `, so its `**unblocked 2026-09-03**, removal owed…` yielded `**unblocked` and counted as declaring nothing, the word being in the sentence but not where the reader looks. Both are corrected, taking the tally to `owed 1, blocked 3, decided 14, delegated 5`. `test_the_document_has_exactly_one_next_heading` then caught the prepend before a human did, Session 166's heading needing its demotion. All 21 entry checks are `ok` and unmoved, all 9 ops claims stayed green either side of the STATUS.md edit, and the suite is **3485 passed** — Session 166's count exactly, which is the arithmetic that says a docs sitting clobbered no test file._

---

# Handoff — 2026-09-04 (Session 166)

### The action Session 166 filed (done by Session 167)

Rank `SNAG-SYSD-008` and then measure it — find where the monitoring daemon's 462 MB resident set actually goes before anyone touches `MemoryMax`, starting with the entry's own first suspect (`GET /api/logs/trends` grouping over a 660k-row table on every request) and with the live fact that `memory.events` recorded 18,374 forced reclaims inside this instance's first ninety minutes — because it is one of three open entries carrying no check, the only one whose fault is costing the box something every minute, and Session 165 left its ranking explicitly to the owner after it stopped being a forecast and restarted the daemon unprompted.

_**`SNAG-LOG-015` is closed, and its hardest question dissolved rather than got answered.**_ _One amdgpu MODE1 reset writes eleven distinct signatures in six seconds and this family opened a row for each — live on 2026-09-04, **ten `warning` rows at a single `created_at` instant**, ten tray fingerprints, and the declared row that names the fault arriving beside ten fragments of its own wreckage. The entry asks what resolves a swallowed member *"since each is a separate open row with its own dedup lifecycle"*. It does not need an answer: `fold_declared_incidents` runs over the `faults` dict **before** `_open_alerts`, so a swallowed member is never a row, has no lifecycle, and `monitor/collation.py`'s flip-flop needs two owners of one row where there is exactly one. `SNAG-AGENT-005` reached the same shape for the same reason — a log line cannot un-write itself, so this family's fixes are raise rules. Driven against the real chain read out of `log_entries`: **11 → 1**, every swallowed signature named in `details['members']`._

_**The relation was reused, and where it stayed mattered more than how it was reached.**_ _`log_actions.correlate` is `group_incidents`' machinery lifted out of it, with the first-sightings filter left behind at the advice caller — that filter is a property of *that* population and the alert family has to answer the rung question rather than inherit an exemption from it. It stays in `log_actions` **deliberately**: `snag_claims.check_check_interval_looks_away` measures `SNAG-SVC-001`'s second resolution by which modules `service_recommendations.py` imports, so rehoming the rule to a third module would let a later correlation fix satisfy that entry while its check went on reporting *still holds*. The ingest agent importing the advice module reads backwards and a backwards import is cheaper than a broken control. Stash-diffed either side: all 24 check verdicts identical._

_**The window is a second constant and the measurement is the whole argument.**_ _`INCIDENT_WINDOW_SECONDS` is 5.0, derived where one incident spans **349 ms** and the nearest two are **64.4 s** apart — three orders of magnitude, nothing sitting near it. This population is not that one. All five resets in the journal span **4.9579, 4.9597, 4.9599, 4.9614 and 4.9675 s** from first error line to `VRAM is lost` — a ten-millisecond spread, because it is amdgpu's fixed reset timeout schedule rather than anything about load — and the nearest genuinely-two-incidents separation among **81,509** kernel lines at `PRIORITY<=3` is **7.04 s**, with **zero** gaps anywhere in that population landing between 4.9 and 5.1 s. So 5.0 clears by **32 ms, 0.6 % of its own value**, and the knife edge was driven rather than reasoned about: at **4.9674 s** the real chain gives eleven rows and at **4.9676 s** it gives one. `ALERT_INCIDENT_WINDOW_SECONDS = 5.9` is the same derivation applied to this population — `sqrt(4.9675 × 7.04)`, 1.19x from each cluster against 1.007x and 1.408x — and a test pins it **against the measurement**, because the failure mode is silent in both directions: a slower reset reopens the entry with nothing going red._

_**The owner chose the shape.**_ _A second constant over reusing 5.0 or widening the shared one, and a fold anchored on a declaration rather than on any group of two. The second choice is also forced: the advice surface titles its roll-up after the anchor, which is free there because the row is recomputed live, and here the title **is** the dedup identity, the tray fingerprint and the resolve key — the 2026-09-04 chain opens on `ring gfx_0.0.0 timeout` and nothing guarantees the next one does. `CRITICAL_SIGNATURES` is the only place a line is given a stable name._

_**One roll-up rule was refused on correctness rather than cost.**_ _`judge_attention`'s "take the loudest rung you swallow" would let a fold **override a quietening** — a declared row an operator has put in `known_noise` dragged back up to `warning` by a fragment, a consumer's judgement beating an operator's, which is the exact ordering the raise block one function down already refuses. Leaving a louder sibling **standing** gets the same guarantee with no ordering question: nothing is ever made quieter and a quietened declaration silences only itself. Reachable rather than theoretical — `RDSEED32 is broken` arrives from this kernel at `PRIORITY=2` — and empty today, since every fragment of every observed reset is `warning` against a declared floor of `warning`._

_**Fifteen mutations driven, each red on exactly the intended test, and two were green on the first attempt.**_ _The ordering test reversed the chain and still folded to one row — correct output for the wrong reason, since every gap then goes negative and nothing exceeds the window; what an unsorted run actually gets wrong is **which fault is the anchor**, so it now uses a third fault inside a later member's window and outside the earliest one's. And nothing pinned that `_record_recurrence` calls `_merge_members` rather than replacing the list — the unit test drove the helper, which is the stubbed-collaborator shape, so a recurrence drive was added at a row that already names a member the second incident did not produce._

_**Deployed and verified, and the fold ships untriggered by construction.**_ _Restarted 12:23:38, `NRestarts` 3 → 4 with **zero** restarts inside the 600 s limiter window beforehand, schema 018, `/health` 200, 12 jobs. Three `log_aggregator` runs, all `completed`, no `log_incident_graph_unread` and no traceback — so the new per-poll `unit_relations()` read works in the daemon. It costs nothing measurable: steady-state duration **0.51 and 0.52 s** against a pre-deploy median of **0.52 s** over 142 runs, the 4.10 s and 1.19 s either side of it being the restart catch-up. The fold itself cannot fire until the next reset, which is `SNAG-LOG-004`'s ordering for the fourth time._

_**One opened, with a check, and its population is measured empty.**_ _`SNAG-LOG-017`: a chain astride a poll boundary folds only the half arriving with the declaration, because a fragment ingested by an earlier poll is already a row and a row is what the fold refuses to touch. Driven through `_execute` twice — one poll **1** row, split after the 4th line **5**, after the 7th **8**, after the 10th **11**, which is the pre-fix count exactly, so the worst case is never worse than the old behaviour. All five resets landed in one poll (5 of 5, one `created_at` instant apiece), and both candidate fixes are worse than the ~8 % they would buy: reaching back for open rows is the flip-flop this entry's parent warned about, and carrying the fold across polls in memory makes the rule depend on a median daemon life of 1.77 h. `incident_fold_splits_at_a_poll` reproduces the mechanism rather than counting the population, takes its declared line **out of `CRITICAL_SIGNATURES`** (`signature()` is idempotent on its own output, verified) so it cannot drift from the declaration it exercises, and reports `unknown` rather than either verdict when the un-split witness fails — that would mean `SNAG-LOG-015`'s fold has regressed, which is a different fault._

_**The registry's own sweep caught the check before a human did.**_ _`TestEveryCheckCanSayItDoesNotKnow` went red the moment the check was registered without a test class driving it to `unknown` — `SNAG-TEST-002`'s guard doing exactly what it was built for. Four drives were written: the entry as filed, a fold that **defers across polls** (the only shape a real fix can take, since un-raising an earlier poll's rows means resolving a swallowed member), a fold that has stopped working, and an empty `CRITICAL_SIGNATURES`._

_**Two claims in STATUS.md's block were corrected against the box.**_ _`Estate hook session-notice.sh not wired for Notification` had resolved itself, so the alert count went 4 → 3 and the named titles with it — `check_alerts`' fall note doing its job for the third sitting running. Suite **3485 passed**, which is 3453 plus 28 fold tests plus 4 check tests; `ruff` and `mypy` clean across 99 files; all 24 snag-claim verdicts unmoved._

---

# Handoff — 2026-09-04 (Session 165)

### The action Session 165 filed (done by Session 166)

Close `SNAG-LOG-015` by folding the eleven fragment rows a single amdgpu MODE1 reset opens into the one declared `VRAM is lost due to GPU reset!` row — a row that only began matching this box's kernel today — reusing `log_actions.group_incidents`' relation rather than re-implementing it, and settle before any code is written what resolves a swallowed member, since each is a separate open row with its own dedup lifecycle and `monitor/collation.py`'s flip-flop is what a careless answer rebuilds.

_**The declaration was written from the wrong kernel and the first real reset found it.**_ _At **10:35:32** the dGPU took a full amdgpu MODE1 reset — `Illegal opcode in command stream` blamed on `GameThread`/`vkd3d_queue`, the per-queue reset refused by firmware that does not implement it (`The CPFW hasn't support pipe reset yet.`), then `MODE1 reset` and `VRAM is lost due to GPU reset!`. Session 164's fix had been deployed since **22:49:29** the night before and the loudest thing the monitor said was **ten `warning` rows** and no declared row at all. The key carried amdgpu's device prefix, `6.18-lts` writes `amdgpu 0000:03:00.0: amdgpu: VRAM is lost…`, mainline dropped the redundant second `amdgpu:` by `7.2.2`, and the box was already on `7.2.2` when the key was typed from the LTS journal. The widened filter worked — **1** row, the first in this table's life — and delivered the event to a declaration that could not see it, which is the multiplicative shape arriving inside its own fix._

_**The guard was a value compared against itself.**_ _`DECLARED_KEY = ("kernel", signature(VRAM_LOST))` and the test asserted `DECLARED_KEY in CRITICAL_SIGNATURES`, which is green on every kernel including one that has reworded the line — it meant *provenance* and asserted a *value*. Driven at the pre-fix state, that assertion still returns `True` while the new `tests/test_critical_signature_live.py` goes red, which is the falsification that matters. Both spellings are declared now and **share one value object**, because two equal literals are two statements of one fact; neither is legacy, since `linux` and `linux-lts` are both installed and a `linux` upgrade invalidates `LoaderEntryDefault`._

_**The branch was never the fault, and the note saying it was is corrected.**_ _The identical signature — `gfx_v11_0_bad_op_irq`, soft reset refused, MODE1, VRAM lost — occurs on `7.1.9` mainline (2026-08-29, blaming **`kwin_wayland`**, not a game), on `6.18.48-lts` (2026-09-03, three times) and on `7.2.2` (today). So the boot-default flip did not cause the resets; what `7.2.2` changed is diagnostics. Wall-clock rates per boot are **not** comparable — the denominator is GPU-load hours and nothing records them._

_**The estate came through it clean, and the one survivor is the boring explanation.**_ _`alfred-inference` and `venture-chat` both died on `vk::DeviceLostError` **3m22s after** the reset — a lost Vulkan context is discovered on the next submit, not at the reset — and both restarted through their `wait-for-dgpu` gate onto the GPU, **37/37** and **41/41** layers offloaded, asserted from the startup log rather than from `-ngl 99`. `venture-embed` never restarted because it runs `-ngl 0` and was never on the card; that was checked rather than assumed, since a survivor of a VRAM-lost event is otherwise a silent-correctness hazard._

_**Four mutations driven, each red on the intended test**, and one deliberately green: dropping the LTS key leaves the live test passing, because this box has only ever stored the mainline spelling — the documented limit, confirmed rather than asserted. Suite **3453 passed**, which is HEAD's 3448 plus five; `test_critical_signatures.py` went 11 → 13, so nothing was clobbered. Opened `SNAG-LOG-016` (a payload reword empties the live population and it skips, which is "could not tell" and says so)._

_**The daemon OOM-restarted mid-sitting and that is `SNAG-SYSD-008` firing rather than sitting.**_ _`sysadmin.service` hit `MemoryMax=512M` at **10:50:15** ("512M memory peak") and systemd restarted it — `NRestarts` 1 → 2, unprompted and unrelated to this work. That entry was filed as *runs at 91.5 % of `MemoryMax`*; it has now exceeded it, which is new evidence nobody has costed and arguably reranks it above `SNAG-LOG-015`. Left for the owner to rank rather than reordered here._

_**Session 164's filed action was already done when this sitting opened, and the board had been told otherwise.**_ _The restart it asks for happened at **22:49:29** on 2026-09-03 — seventeen minutes after the commit that wrote the handoff line, and recorded in `457d011` — so the sentence `roadmap.py` publishes verbatim to the estate board asked for a `kill -TERM` that had already been sent, for nine hours. `check-ops-claims.sh` read **9 of 9 ok** throughout, including `daemon_start` and `deploy`, because it checks the STATUS.md block and nothing checks this line. Session 150's shape exactly, and the second instance._

_**The verification it asks for was outstanding, and it holds.**_ _Since the restart the kernel journal at `-p 6` offers **9** lines and `log_entries` holds **9** rows for source `kernel`, matching byte-for-byte on `x86/split lock detection: #DB: CJobMgr::m_Work/12232 took a …`. Nothing is behind: `journalctl -k -p 6 --since '2026-09-04 06:04:50'` returns **0** lines against a newest stored row of 06:04:49. **597** `log_aggregator` runs, **1** truncated — the startup catch-up, which stored exactly `max_entries_per_read` at 500 and reported it, `SNAG-LOG-002` working as written._

_**The probe as filed was measured empty, and the discriminating witness was a different line.**_ _`journalctl -k -p 6 --since -1h | grep -c amdgpu` returns **0**, and so does the database half — there has been no amdgpu line at any priority since the reboot onto mainline 7.2.2, which is the reboot working. `0 = 0` is not evidence. What discriminates is that **all 9** stored lines are `PRIORITY=4`, so the old `severity_filter: error` (`-p 3`) would have stored **none** of them; and the catch-up read stored **144 amdgpu `info` rows** from the 18:48–18:49 boot, a class that held 0 rows before the widening. The widening is proven twice and neither proof is the one the line named._

_**The declaration is deployed and cannot yet witness itself, by construction rather than by fault.**_ _`VRAM is lost due to GPU reset!` has **0 rows** in `log_entries` and `log_aggregator` has raised **no alert** since the restart. The only occurrences are the 11:24:55 resets, which predate `_resume_floor()` — the reader moves forward only, so those lines are in the journal permanently and in the table never. `CRITICAL_SIGNATURES`' population is empty until the next reset, which is the fix shipping untriggered rather than the fix not working, and `SNAG-LOG-004`'s ordering again._

_**One claim in Session 164's own account is narrower than it was written.**_ _"`critical` was unreachable" is true of **amdgpu** and not of the kernel source: `log_entries` holds **4** `critical` kernel rows — `RDSEED32 is broken. Disabling the corresponding CPUID bit.` at `PRIORITY=2`, from 08-23 and three times on 09-03. Read as the new declaration firing on the catch-up read at first, and refuted by looking at the messages; the rung was always reachable for a line the kernel actually stamps `crit`._

_**Alfred's message `8c6da00e` is closed, and the correction landed in five places here rather than in the note.**_ _They re-measured `alfred-career-mail.service` from systemd's per-invocation accounting and handed back two of their own numbers: **five** failures on 21 mornings, not twelve on twelve consecutive ones, with **13** successful runs inside the same window. SNAG-50's reproduction was `grep -c UniqueViolationError` and each failed run writes the traceback three times, so twelve lines were four runs — and the same grep was structurally blind to the two 08-22/08-23 failures, which had an unrelated cause. Taken here in good faith, so it had propagated into two shipped docstrings in `monitor/agent.py`, `STATUS.md` twice and `tasks.md`._

_**It makes this repository's finding stronger, which is why it was worth the edit rather than the note.**_ _A unit failing every morning is noticed by its owner eventually; one failing on **five mornings in twenty-one** is exactly what a monitor exists for, and the `kind: timer` check reported `ok` on all five — the 3,988-row figure is ours, was never in question, and now sits against an intermittent fault instead of a continuous one. `SNAG-SYSD-005`'s reasoning is unaffected: reading the timer's `Result` is blind to the triggered job whatever the job's duty cycle._

_**Two sites were deliberately left alone, and the test is whose voice the sentence is in.**_ _`STATUS.md:827` and `tasks.md:728` attribute the figure to SNAG-50 (*"Alfred's SNAG-50 reports…"*), which was **true as written** — their snag did say it — so the attribution stands and the correction is appended beside it. Session 147's HANDOFF block says the same thing in the same reported voice and is a dated record of what that sitting read, so it is corrected **here** rather than rewritten there, which is how this block treats Session 164 four paragraphs up. What changed is the two places this repository asserted the figure in its **own** voice._

_**The suite was red before this sitting opened, and the guard cannot see the edit that breaks it.**_ _`tests/test_handoff_shape.py::test_the_document_has_exactly_one_next_heading` fails at `457d011`, measured by running it against the pre-session file: Session 164 added a second `# Handoff` block with its own `## Next action` and left Session 163's in place, giving estate-manager's `next_action_from_handoff` two candidate headings. **Their handoff reports "3442 passed" and that was true when they ran it** — the handoff is written *after* the suite, `claude-precommit.sh` runs lint, schema and the docs gate but never pytest, and nothing between the two looks again. A guard on a document edited at the end of a sitting is structurally blind to the sitting that breaks it. Session 163's heading is demoted to `###` here and the suite is back to **3442 passed**; the mechanism is untouched and is filed as `SNAG-TEST-005`._

_**The entry's check reads the gate, never the guard, and that was the design decision.**_ _`check_handoff_shape_unguarded` is the twentieth registered check. Asserting the test still fails on a broken document measures the **detector**, which is not what is broken; asserting the real `HANDOFF.md` is clean would report the entry refuted the moment a sitting tidied the file — Session 83's reading of `SNAG-LOG-013` again. What is refutable is whether anything on the commit path runs it, so the sweep is over `claude-precommit.sh`'s **executable** lines (`test_schema_guard`'s idiom in the same directory, for the opposite claim), because a comment naming pytest is prose about the suite and this entry is about a guard that is documented and not wired. **The witness is the two guards it does run** — `lint_check.sh` and `check-migrations.sh` — so a sweep finding none answers `unknown` rather than borrowing `match`'s meaning, which is `ports_checked`'s rule. Three mutations driven, each red on exactly one test: dropping the no-guard branch, reading raw lines instead of executable ones, and emptying `SUITE_INVOCATIONS`._

_**The remedy is one line and the cheap half is not the obvious one.**_ _pytest in `claude-precommit.sh` is what anyone reaches for and it is the expensive half: 63 s on every commit, and **a commit is not what publishes the line** — the estate reads `HANDOFF.md` from disk, so the damage begins at the edit. `claude-postflight.sh` already runs at the close and already runs `check-ops-claims.sh` there, which is precisely why STATUS.md's markers do not have this defect; one more line beside it catches the handoff at the moment it is written. Advisory at the close beats blocking at the commit — `check-migrations.sh`'s exit-2 argument. Not taken here because it edits a script two other repositories' conventions describe._

_**Comment-only, and the deploy check will say otherwise.**_ _`monitor/agent.py` changed in a docstring and a `#:` comment and `snag_claims.py` gained a check; no behaviour in either, no existing test moved. `check-ops-claims`' deploy limb compares the newest `.py` mtime against daemon start, so it reports a restart owed for a file the running process would import identically — the false positive its own docstring names, failing in the direction that costs a needless `kill -TERM`. Not restarted: the daemon is 9 h into a life that has already spent 1 of `StartLimitBurst=5`, and `SNAG-SYSD-007` is the entry that priced this. Schema at head `018`; **23** open snag entries, +1 being `SNAG-TEST-005` itself, and the other nineteen checks unmoved at `still holds`. Suite **3448 passed** — 3442 plus the six new, which is the clobber check._

---

# Handoff — 2026-09-03 (Session 164)

### The action Session 164 filed (done by Session 165)

Restart `sysadmin.service` with `kill -TERM` so the widened kernel `severity_filter` and the new `CRITICAL_SIGNATURES` declaration take effect, then confirm info-level kernel lines are being stored by comparing `journalctl -k -p 6 --since -1h | grep -c amdgpu` against a count of `sysadmin.log_entries` rows for source `kernel`.

_**The GPU was resetting and the monitor watched it happen three times in silence.**_ _Investigating why the box crashed mid-game found an amdgpu fault chain — `Illegal opcode in command stream` wedging the shared `gfx_0.0.0` ring, the per-queue reset failing (`MES failed to respond to msg=RESET`, `The CPFW hasn't support pipe reset yet.`), and amdgpu escalating to a full `MODE1 reset` that destroys every client's VRAM. The root cause was a **boot default**, not this repository's: a `linux 7.1.9 → 7.2.2` upgrade deleted the entry `LoaderEntryDefault` named, systemd-boot fell back to sort-key order (`endeavouros-6.18.48-1-lts` sorts before `endeavouros-7.2.2-arch1-1`), and the box came up on the LTS branch unasked. Three resets in 8.2 h on `6.18.48-lts` against one in ~240 h on mainline, same game and same Mesa. Rebooted to 7.2.2: clean under load, 100 % GPU and 19.9 GB VRAM._

_**The monitoring gap is what this sitting fixed, and it was two gaps.**_ _`severity_filter: error` meant `journalctl -p 3` while every line naming the reset is `PRIORITY=6` — `log_entries` held 0 rows for `VRAM is lost`, `GPU reset begin`, `MODE1 reset` and `device wedged`, and 4 apiece for the two symptoms. Separately, `critical` was unreachable: `chk_alert_severity` admits three rungs, journal `error` maps to `warning`, and amdgpu never uses `PRIORITY` 0–2, so all 44 amdgpu rows on this box are `warning`. Widening without declaring adds 1,804 lines a day and still raises nothing louder; declaring without widening declares a signature the reader cannot see._

_**The owner chose the shape and the rung.**_ _A declared escalation list over a dedicated family or symptom-only escalation, and a toast **only on the second reset** — so `CRITICAL_SIGNATURES` opens at `DECLARED_FLOOR_SEVERITY` and escalates inside `critical_repeat_hours` (24 h, invented and says so; the live population separates at 3 h 31 m within a session against five days between sessions, so every value from 4 h to ~100 h is identical on it)._

_**The title carries no rung, and that was forced rather than chosen.**_ _`alert_title` builds its prefix from the journal rung, which would print `Log info:` on a `critical` toast; and the alert rung cannot go there instead, because `step_for` escalates by raising a fresh row under the **same** title, so a rung-derived title forks the dedup identity at the moment the ladder climbs it. A declared fault is named after the fault._

_**The narrow alternative was measured and refused.**_ _The reset lines carry `_KERNEL_DEVICE=+pci:0000:03:00.0`, so a second source matched on that field reads 214 lines against 1,845 — 8.6x cheaper — and overlaps on **27**, which journalctl has no negation for. One fault with two speakers under two `source` names, bought for 1,631 lines a day._

_**Falsified rather than merely green.**_ _Seven mutations driven and all seven land red on the intended test — the gate ignoring the declaration, `alert_title` used instead of the declared title, provenance only on the escalated row, the declaration overriding `known_noise`, the count filtered by `unresolved()`, escalation on the first incident, and the window hard-coded past config. The suite is **3442 passed** against a 3431 baseline plus 11 new, which is the clobber check. `ruff` and `mypy` clean._

_**And driven live, where the first probe was wrong.**_ _`_recent_incidents` was run against the real 667k-row `alerts` table: a title read from the table returns **4**, agreeing with it. The first attempt probed a `Log warning:` title and got `0` — the title carries the journal rung (`Log error:`) while the row's severity column reads `warning`, so the probe was wrong rather than the query, and a constant zero would not have been evidence either way._

_**Three opened, none closed.**_ _`SNAG-LOG-015`: one reset still occupies twelve alert rows, and `group_incidents` — which already folds this exact population for `GET /api/logs/actions` — operates on recommendations, not alerts. `SNAG-CFG-006`: `arrives_at` is pinned by a test against the shipped file, and `severity_filter` is not `RESTART_ONLY`, so a SIGHUP can disarm the declaration with the suite still green — `SNAG-CFG-003`'s class, second member. `SNAG-SYSD-008`: the daemon sits at 491 MB of a 512 MB `MemoryMax` with `memory.events` reading `max 59388`, found beside the work and not caused by it._

---

# Handoff — 2026-09-03 (Session 163)

### The action Session 163 filed (`SNAG-DOCS-003` — closed by Session 168 on 2026-09-04)

Carry out `SNAG-DOCS-003`'s removal — delete `sysadmin_tray/_deprecated_contracts.py` and the `__getattr__` in `sysadmin_tray/models.py`, drop `TestDeprecatedNamesLeftTheRegistry`'s three behaviour tests while keeping `test_none_of_them_are_defined_in_contracts`, and cite estate message `e045373e` in the commit — because the audience is now measured empty, every off-box route is closed and the announcement is already filed, so the entry's only remaining cost is the deletion nobody has made.

_**`SNAG-DOCS-003` is unblocked, and the blocker was the part that was wrong.**_ _The entry says closing it needs "an operational fact this repository cannot check" — where the wheel went. It was checkable here in one sitting, and the answer is that there is nowhere the artefact could have gone: **no git remote and no branch upstream**, so the repository has never been pushed; **not one of the 31** `sysadmin_service` wheels on this box contains `sysadmin_tray/` code, every one being a uv *editable* stub of a `.pth` and dist-info, checked by `unzip` rather than by name; CI has no publish step; `syncthing@gaddi` is running but shares only `/srv/seedvault-backups` and `~/Documents/DMDocs/Self`, neither covering `~/projects`; and `~/projects/.backups/sysadmin_assistant.git` is a leaf whose only remote is a local path and whose newest ref is 2026-08-04, three weeks before the module existed. The published surface the entry protects has never actually been published._

_**Zero importers box-wide, and the sweep keys on the import rather than the name.**_ _Not one `from`/`import` statement reaching `sysadmin` or `sysadmin_tray` exists outside this checkout, across `~/projects`, `~/.claude`, `~/.local` and `~/.config` — `test_contract_reachability`'s rule 2 applied to a whole box. The distinction decides the answer rather than decorating it: **estate-manager defines all five names itself** in `service/estate_service/projects/contracts.py` off its own local `Contract` base, so a **name**-keyed sweep finds 5/5 over there and names them the importer, plausibly and wrongly. They went across with ADR-0005; nothing of theirs breaks._

_**The negative was falsified before it was believed.**_ _A constant observation is not evidence unless something in the population would have forced a different one, so a planted `from sysadmin_tray.models import RecommendationInfo, PortfolioAction` was run through the same sweep beside a decoy **local** `class RecommendationInfo` — the importer reported, the decoy correctly ignored, the plant removed by a shell trap. Without it, zero-because-clean reads exactly like zero-because-the-pattern-never-matched._

_**Filed at estate-manager as `e045373e`, before the commit that will carry the removal.**_ _No filing was **owed** — the import audience is measured empty, and a measured-empty audience files nothing. It was sent because estate-manager holds the only two surviving references and is the party that wrote them down: their **ADR-0069** names this module inside its own rule-3 audience measurement, and `GET :8400/api/audit/readers` carries **two rows** for it (lines 3 and 47, `kind: authority`, `usage: docstring`, of 127 rows over 6 repositories). Neither breaks; both stop being true, and amending them is theirs to decide._

_**Their inventory is not a second opinion on the audience.**_ _`/api/audit/readers` is keyed on port and document authority references, never on Python imports — it reaches this module only because the docstring mentions `:8400` — and holds **zero** rows referencing 8500 from any repository. So the estate's instrument cannot answer the question the entry was blocked on, and saying which half an instrument measured is `ports_checked`'s rule turned on someone else's tool._

_**The removal was deliberately not carried out and one code edit is owed.**_ _The owner's call, asked and answered mid-sitting: record the answer, leave the deletion of a published surface to its own sitting. So `check_deprecated_contracts`'s docstring still says the operational fact is one "this repository cannot check", which the measurement above refutes — its **verdict** is unaffected and still `match`, so it is a wrong sentence rather than a wrong answer, and it is recorded in the entry rather than fixed here._

_**Measured either side, and nothing moved that should not have.**_ _Docs only, no code touched: the live parser reads **124 entries / 19 open** before and after the edit, `SNAG-DOCS-003` still open at `P3` with its body carrying the message id; **9 of 9** ops claims `ok`; the entry's own check still reports `still holds`, correctly, because the five are still defined and still unread. No restart owed._

---

## Session 162 — a marked cut said an identity was lost; now it gives one back

_**`SNAG-LOG-013` is closed, by the discriminator the entry said could not exist at this level.**_ _`capped_signature` stamps a cut signature with `signature_digest` of the **whole** signature — the eight characters `alert_title` has carried since Session 122 — so the roll-up's member lines, the incident title and the three single-signature titles all come apart. Open entries **20 → 19**; nothing opened, nothing else moved._

_**The obstacle was refuted by the entry's own alert half.**_ _It argues a divergence-aware cap "needs the sibling set and so cannot live in a per-row pure function" — true of that remedy, and the digest is per-row and pure, so `capped_signature` was simply where it had not been applied. The entry's "two candidate fixes, neither cheap" is now false in both limbs: the producer fix landed for a different entry (`SNAG-LOG-008`) and emptied the population without touching the class, and the second was never the only per-row option, only the only divergence-aware one._

_**Four rules, three of them the opposite of the obvious implementation.**_ _The digest is **imported, never restated** — `log_signature._digest` became public `signature_digest`, and a local `sha256(...)[:8]` gives the identical value, so all five value-asserting tests pass against the copy and only an AST walk catches it. It digests the **whole** signature and never the cut, because the colliding pair's cuts are one string and a digest of what survives would render as a discriminator and separate nothing. It is **appended past the bound**, deliberately the opposite of `alert_title`, which subtracts because `TITLE_MAX` is a column — so the cut point does not move and no existing member line lost a character. And **only a cut carries one**, asked of `truncate_at_word` rather than re-derived from the constant._

_**The weekly review takes the cut without the stamp, and the population deciding that is not empty.**_ _`log_review._quoted_signature` gates on `figure_free` because its render reaches a model under a prompt carrying no digit from the data by construction. Measured: **8 of 79** retained signatures are cut and **8 of 8** are figure-free, so gating on the rendered line — the tidier-looking shape — would have deleted every cut signature from the prompt rather than un-stamping it, leaving `sysadmin.service: a new fault appeared` on the one surface with nothing else to say what happened. Live, **two** such lines reach the real prompt today and its data half carries **zero** digits._

_**`figure_free`'s stated exception is unreachable, measured on the way past.**_ _Its docstring said `_HEX` leaves `0xN`, "digit-free in intent and not in fact"; `signature()` runs `_NUM` **after** `_HEX`, over its result, so the `0` is eaten and `0x1f` arrives as `NxN`. **79 of 79** live signatures pass the gate. The gate stays — its input is only *typed* as a signature, the caller reading `item["signature"]` out of a JSON facts blob — and the docstring is corrected._

_**A measurement bug nearly mis-ranked the fix, and it was in the reader rather than the code.**_ _The first sweep read `log_entries` with a `psql -F` separator and filtered rows on separator count, dropping every row whose `message` carries a newline — which is every core dump and every traceback, the exact class this entry is about — and reported **3** cut signatures against the true **8**. `row_to_json` puts each row on one line. A reader that silently discards its own hardest specimens reports a smaller population and a cleaner box._

_**Six mutations, each red on the right test, and the last is the one worth carrying.**_ _Never stamping takes 6 red, digesting the cut 7, stamping an uncut signature 2, subtracting the suffix from the bound 1, the review taking the stamp 2 — and a second digest of its own lands red on the AST walk **alone**, which is the value-versus-provenance trap this repository has now found for the third time._

_**The check retired with the entry and the detector did not.**_ _`check_capped_signature_collides`, `probe_signatures` and the five `PROBE_*` constants went; `TestACutSignatureCarriesItsDiscriminator` is the re-homed drive (`FROZEN_TABLES`' rule, eighth time here), carrying `probe_signatures`' derive-the-prefix-from-the-constant argument so a future `SIGNATURE_DETAIL_CHARS = 400` cannot read as a fix in the one remedy the entry rules out. `_marker` and `TestTheStandInDisambiguator` stayed: that class's AST sweep refuses the randomised builtin by name and names `_marker` as the alternative, so the helper has to exist for the refusal to be actionable._

_**Verified live at the HTTP surface after a restart.**_ _`GET /api/logs/actions` serves **3** cut titles and **2** cut member lines, every one stamped, **0** duplicate titles — and each title's eight characters are the same eight in that row's own `alert_title`, which is the whole of what the stamp buys. `/api/health` 404s and `/health` answers 200; that is `health:legacy` in estate-manager's §2.1 row for 8500, checked rather than filed._

_**The daemon was restarted twice and the second was owed to `git stash pop`.**_ _Counting the suite per file by stashing to HEAD and popping rewrites every `sysadmin/*.py` mtime with identical bytes, and `check-ops-claims` compares mtimes rather than content — its own stated cost, met by a technique this repository uses deliberately, and the pairing had not been recorded. NRestarts 5, both starts well outside each other's 600 s window after `SNAG-SYSD-007` cost 77 minutes this morning._

_**Measured either side.**_ _Suite **3430 → 3430**, and the unmoved total is a coincidence rather than a green: counted per file by stashing to HEAD, **9 added** (`test_log_actions` 57 → 65, `test_log_review` 35 → 36) against **9 retired with the check** (`test_snag_claims` 384 → 375). `ruff check .` and `mypy sysadmin` clean, **19 of 19** snag verdicts and the register's four conventions unmoved either side, **9 of 9** ops claims `ok` — the unresolved-alert count corrected 3 → 2 (`Unusual RAM usage` resolved across the restart, which is `check_alerts`' fall note doing its job) and the daemon-start stamp to 13:31:27._

---

## Session 161 — the entry with no disposition had a producible class and a refuted obstacle

_**The last entry with no disposition declares `owed`, and the measurement is why.**_ _`SNAG-LOG-013` was 1 of 20 open entries declaring nothing; the register now reads `owed 1, blocked 4, decided 10, delegated 5`. The next action asked whether the class is still **producible** rather than whether the collision is worth fixing, and it is — by a producer the entry does not name._

_**The producer changed and the entry still blames the fixed one.**_ _Driving the real `signature()` over all 80,380 retained rows: **8 of 79** distinct signatures are cut today against the **2 of 50** the entry last recorded, and **4 of the 8 are stack traces** — one Python traceback, three core dumps. `systemd-coredump` spends **70–73 characters** on `Process N (X) of user N dumped core. Stack trace of thread N:` before frame 1, and a frame renders `#N NxN <symbol> (<object> + NxN)` at 29–46 characters, so the 120-character cap admits **one and a half frames** and falls inside frame 2 of all three live dumps. Two `abort()`-path crashes of one binary (`n/a (libc.so.N)` → `raise` → `abort`) are identical to the cap by construction. A stack trace is boilerplate-first — the exact opposite of the JSON-envelope class `SNAG-LOG-008` closed._

_**The live margin is 43 characters and it is luck, not design.**_ _No pair shares a capped prefix; the closest is two `mosquitto.service` dumps agreeing over **77** of 120, and the survivor survives only because its frame 1 carries a symbol (`sub__clean_session`) where the other carries `n/a`. An empty population is not a closure, which is this entry's own rule twice over._

_**The residue is prose alone, and the entry's own check cannot see that.**_ _Driven at a colliding pair through the real `recommend()` with the **real** `alert_title` — `check_capped_signature_collides` stubs it with a fixed string, so it has never exercised this — the roll-up's structured members already come apart: `members[].alert_title` reads `… (truncated) [a028de53]` against `[d9aa53f0]`, `members[].signature` carries all 247 characters. Session 122's discriminator reaches the machine-readable half for free; what still collides is the rendered `detail` member lines and the row `title`, which is the whole of what the roll-up promises to name._

_**`owed` rather than `decided`, at the owner's call on that evidence.**_ _The entry says a divergence-aware cap "needs the sibling set and so cannot live in a per-row pure function" — true of that remedy, and its own alert half shipped one that **is** per-row and pure. `capped_signature` is simply where it has not been applied. Both readings were put to the owner with the measurement; `decided` would have rested on the residue being prose-only at P3._

_**No snag was fixed and none was refuted, checked rather than assumed.**_ _All **20** snag verdicts and the register's four conventions are unmoved across both halves of the sitting. The disposition half changed no code at all; the correction half changed two docstrings and added one test, and the totals are below._

_**One ops claim was stale and is corrected.**_ _`check-ops-claims` read `no` on the unresolved-alert count: the block said **2**, the box held **3** — `Unusual RAM usage` opened after Session 160 wrote the block. Corrected to 3 and all three named; all **9** claims now `ok`._

_**Then estate message `b96a337c`, acted on and closed.**_ _Their ADR-0102 makes a `wiring` finding's `fingerprint` `wiring:<hook>:<code>:<event>`, so the limit `judge_audit_wiring` filed — two events from one hook sharing one fingerprint and therefore one `standing_days` — is **closed at the producer**. Corrected there, and in `judge_audit_findings` rule 4, whose incidental "`code` is the fingerprint's last `:`-separated segment" is now true of twelve checks and false of one._

_**Read from their source, because the wire cannot show it.**_ _`wiring` has filed **zero** findings in 938 across 262 runs, and live `GET /api/audit/findings` served three, every one three-part (`ports` ×2, `docs` ×1). So the correction is verified in their tree at `65f7156` rather than taken from the message: `Finding.fingerprint` appends `aspect`, `checks/wiring.py` is its only setter, `as_payload` publishes no `aspect` key — **committed, which is not deployed on 8400**. `detail['event']` and `subject` are unchanged, so rule 1's identity and rule 2's discriminator are untouched, exactly as they measured._

_**The pin is pre-staged and was falsified against their real dataclass**_ _— a pin over an empty population is green whatever it asserts. Driving `Finding.as_payload` in this venv: the shipped shape passes, a rolled-back `aspect=None` goes red, an `aspect` disagreeing with `detail['event']` goes red, and the whole-file finding gaining one goes red on the colon count. `test_a_live_wiring_finding_still_separates_its_two_events` asserts nothing until the first wiring finding arrives, which is also the first moment it could catch anything._

_**The ADR was amended rather than rewritten, which their own message pointed at.**_ _They closed with "Yours: ADR-0006 §5", and that section carries the same sentence in the same present tense. §5 stands as recorded and **§5a** amends it — their ADR-0102's own treatment of their ADR-0067 §9. One asymmetry worth knowing: the close note on `b96a337c` names commit `e3d0eeb` and **predates** the amendment, so a reader diffing the two will find the ADR half in the commit after the one the estate was told about._

_**A restart was owed to a docstring and paid rather than argued with.**_ _`check-ops-claims` compares mtimes, not behaviour — its own stated cost — so a docstring edit to a file the daemon imports reads as a stale box. `kill -TERM` at 12:41:04, back in 20 s on `Restart=always`, PID 279728 → 329947, **0** `ERROR`/`CRITICAL` lines since, health `200`. NRestarts 3, well inside `StartLimitBurst` after `SNAG-SYSD-007` took 77 minutes this morning._

_**Measured either side.**_ _Suite **3429 → 3430** (one test added, none retired), `ruff check .` and `mypy sysadmin` clean, all **20** snag verdicts and the register's four conventions unmoved, and **9 of 9** ops claims `ok` — the unresolved-alert count corrected 2 → 3 and the daemon-start stamp to 12:41:04._

---

## Session 160 — the disjointness was a handover, not a property of the box


_**The box is up and the sitting took it down first, which is `SNAG-SYSD-007`.**_ _Five restarts in ten minutes — the guard's clean reload path, its breach path, the lifespan warning path either side of a mutated `services.yaml`, and the ops-claim restart — tripped `StartLimitBurst=5` inside `StartLimitIntervalSec=600`, and `sysadmin.service` was down **10:14:32 → 11:31:57**. The Session 39 machinery worked exactly as designed: `sysadmin-failed.service` fired, raised `critical | sysadmin.service failed`, and the lifespan resolved it on the next start. **What nobody had recorded is the limit on the documented "a restart needs no `sudo`" claim**: `kill -TERM` needs none while the daemon is *running*, `systemctl reset-failed` needs none, and the `start` from `inactive` that follows needs polkit `auth_admin_keep` — measured with `pkcheck --action-id org.freedesktop.systemd1.manage-units`, which `sudo -n` cannot supply and a session with no agent is refused for. Filed at P4 with the twenty-third check, which asks the **action id** rather than attempting the remedy: a check that ran `systemctl start` would change the state it measures, and exit status cannot see polkit anyway._

_**The disjointness was a handover, and enumerating it is what said so.**_ _`SNAG-SVC-002` is **decided**, not closed. The entry says the two families do not overlap here and calls that "a property of this box rather than of the design". Measured: **10** services are declared `kind: timer` and none intersects `AGENT_NAMES` (6) or `agent_schedules` (5) by service name, by unit stem, **or by `ExecStart` subject** — the third key being the one a name comparison cannot reach — and live the two families named **zero** common subjects, with `timer_stale` still at zero rows nine days on._

_**But the scenario it calls hypothetical already happened here.**_ _Commit `5cc04cc` (2026-08-08) declared `sysadmin-organiser.timer` as `kind: timer` for the same subject the daemon scheduled as `project_organiser` and set `agents.project_organiser.enabled: false` in the same sitting; its message states the rule — "Monitoring the timer **replaces** the self-monitor's stall watch over that agent." So the disjointness is a deliberate handover on the one subject that could ever have been both, and `estate-manager-scan.timer` runs that agent's work today. What is fragile is what carried it: `summarise_agent` gates on `schedule.enabled`, so one config flag was the whole separation — the fragility `agent_schedules`' own docstring names._

_**`sysadmin/monitor/handover.py` guards the handover rather than cross-referencing the families.**_ _An `agent:` key on a `kind: timer` entry; three rungs — `breached` (scheduled **and** enabled: the job runs twice), `flag_carried` (the `5cc04cc` state, silent and one edit away), `unknown_agents`. A link to a **retired** agent is silent, which is the key's purpose and why both sets are read. Reported by the lifespan and by four fields on `POST /api/sysadmin/reload`; **never refused** (`config_keys` rule 1), because a boot refused over a coherence finding is `SNAG-DB-005`'s twenty-three hours bought for a job that runs twice._

_**The cross-reference the entry recommends has a cost it does not price.**_ _`sysadmin-organiser-timer` and `project_organiser` share no string, so feeding `stalls.py` a timer-backed population needs the same declared link — a schema key, not a wiring change — and once the key exists the cheaper thing to spend it on is a config-time report rather than the alert-time machinery the entry itself calls "the second owner arriving with more machinery"._

_**It does not close the entry and the check correctly says so.**_ _The guard imports neither family, so all three instruments are unmoved: both still speak on the synthetic subject, `timer_stale` still owns no ladder, the importer sets are still disjoint. All **19** snag verdicts and the register's own three checks were driven before and after; the only movements are the ones this sitting made._

_**Verified live at both surfaces, and the loud path was driven on purpose.**_ _`POST /api/sysadmin/reload` against the real file reports `handover_breached: []` with `handover_walked: true`; against the same file with the link re-pointed at `file_organiser` it reports the breach and reverts cleanly. A **restart** in that state writes `handover_agent_still_scheduled` at `WARNING`, stored and counted and raising nothing. The first attempt at that read the journal in the wrong window and found nothing — a clean report proves nothing about the loud path, so it was re-driven rather than assumed._

_**The insert landed in the wrong entry first, which is the part worth carrying.**_ _`SNAG-SVC-001` and `SNAG-SVC-002` carry a **verbatim identical** "Found: 2026-08-25 by Session 78, raised before implementation and filed at the owner's explicit direction…" bullet, so anchoring on it put nine bullets into the neighbouring entry — silently, and the register still reported `SNAG-SVC-002` as declaring no disposition, which is what caught it. Anchor on the entry header and scan forward, never on a bullet two entries may share._

_**Measured either side.**_ _Suite **3406 → 3429**, arithmetic checked by stashing to HEAD rather than trusting the green: 12 added in `tests/test_handover.py` and 11 in `tests/test_snag_claims.py` for the two new checks, none retired. Note the previous block recorded **3410** and HEAD does not reproduce it. `ruff check .` and `mypy sysadmin` clean. All **20** snag verdicts and all **9** ops claims `ok`, driven before and after. Eight mutations were driven against the handover tests and each lands red on the right one; the two new checks' five falsifications give `mismatch` and `unknown` rather than a green silence. Every handover case is driven at the **real** `services.yaml` and `config.yaml` with one line edited in a copy, because this entry is precisely one where reasoning gave the wrong answer and measuring gave the right one._

_**A live test went red on an unchanged tree, and the fix is a differential probe.**_ _`test_refusing_something_is_not_finding_nothing` mints an isolated unstamped row and then asserts `closed == 0` over the **whole** live table, so a genuinely in-flight run belonging to the running daemon — stamped with another instance's id — is closed and the assertion fails with nothing wrong. Reproducible rather than theoretical: `agent_first_run_delay_seconds` re-runs every agent 60 s after each daemon start, so every restart opens a ~110 s window in which `file_organiser` is mid-scan, and this sitting restarted six times. A **baseline sweep runs first** now and the assertions are on the delta the minted row makes, which also sharpens `refused` from `>= 1` over a live population to exactly one more than the baseline. Driven at the breaking condition — a dead-instance `running` row added before the baseline — and the pair reads `closed=1 refused=7` then `closed=0 refused=8`; falsified by making the sweep stop counting refusals, which takes it and its sibling red._

_**The residue is `SNAG-SVC-005`**_ _— the key is a declaration, so an agent moved to a timer without one is invisible. Both closures were priced and refused: deriving the link needs a subprocess in a parse path and *recognises an application* where the key **honours a statement**, and a mandatory key puts `agent: null` on nine of ten entries as ceremony. Its check answers the same entry three times (as shipped, re-pointed, key removed), because the obvious observation — "an undeclared timer produces no finding" — is a constant equally consistent with a guard that was never wired._

---

## Session 159b — a constraint value nothing wrote had a referent

_Its next action, as published at the time:_

Take `SNAG-SVC-002` by measuring the overlap its check reports rather than by reasoning about the two families' populations, because the check already drives one synthetic timer agent into `stalls.py` at `critical` and `service_recommendations.py` at `advice` off the same three-day silence, and what nobody has counted is how often the two speak about the same real subject on this box — so enumerate every configured `kind: timer` service against `AGENT_NAMES` before deciding whether the fix is a cross-reference, a narrowing, or the entry's own observation that the populations are disjoint only by accident.

_**`SNAG-DB-006` is fixed, and the measurement it asked for chose a shape the entry does not name.**_ _`chk_run_status` has admitted `cancelled` since migration 001 with nothing writing one; the entry named two opposite fixes and left the choice open. Dating decides it: all seven live `running` rows are followed by a **clean** daemon death within **0.032–61.2 s**, and for each the next `agent_run_completed` for that agent comes from a **different PID**. The mechanism is `scheduler.shutdown(wait=False)`, read rather than inferred — the first row was inserted **19 ms before** `scheduler_shutdown`._

_**The control is what makes that evidence rather than a coincidence.**_ _Of 40,383 `completed` runs **162 (0.401 %)** started that close to a death and the separation is total: no run starting more than 61 s from a death has ever got stuck. `file_organiser` is the sharpest line — **0 of 112** completed against **3 of 3** stuck, the widest exposure of any agent at ~108 s a scan. Conditioning cuts the right way: a run killed at shutdown cannot be `completed`, so the depressed base rate is the argument rather than a bias against it. Live rate **4.9 %** of daemon deaths, 7 of 144._

_**The third shape is a startup sweep, and the discriminator is a race rather than coverage.**_ _A shutdown-path write is what anyone reaches for and `shutdown(wait=False)` returns while the worker thread is still in `_execute` — three of the seven had 30–60 s of scan left — so it can land after a `completed` the thread commits. `sysadmin/core/abandoned_runs.py` sweeps at startup instead, `unit_failure.py`'s argument one table over. **The SIGKILL and power-off advantage is stated as theoretical and is**: all ten crash deaths in the journal died 2.1–4.8 s in, before the scheduler could fire anything, so on the live population both shapes reach 7 of 7._

_**Forward-only by refusal, not by a constant.**_ _The seven predate the stamp, so the sweep cannot attribute them, refuses them and **counts** them — `ports_checked`'s rule — where the age cutoff the obvious version needs would be an invented constant expressing a fact the row already carries. The instance id is minted in-process rather than read from systemd's `INVOCATION_ID`, which is present and would work, because this service reads no environment variables and a lone exception is a convention that has stopped being one._

_**Verified live, twice, because the path had never run on this box.**_ _Restart 1: `abandoned_runs_unattributable count=7`, no closures. Then `POST /api/files/scan` killed 2 s in, and restart 2: `abandoned_runs_closed count=1 agents=['file_organiser']`, writing **the first `cancelled` row in this database's life**, carrying both the dead instance's id and `cancelled_by`. The seven are still at seven._

_**Measured either side.**_ _Suite **3388 → 3410**: 22 added in `tests/test_abandoned_runs.py`, 3 retired with the check, arithmetic checked rather than the green trusted. `ruff check .` and `mypy sysadmin` clean. All other **18** snag verdicts unmoved, driven before and after. All **9** ops claims `ok`; three moved during the sitting and all three were chased — the alert fall from 4 to 3 is the one the previous block **predicted**, so it is not `SNAG-ESTATE-008`'s founding case and says so._

_**Three of thirteen falsifications passed against deliberately broken code, which is the part worth carrying.**_ _Deleting the `IS NOT NULL` conjunct changed nothing at all — `NULL <> 'x'` is `NULL`, so the refusal rule 3 exists for was being carried by three-valued logic rather than by the clause written for it; the clause stays, because its visibility is what stops a `COALESCE` "fix" sweeping the seven silently, and it is pinned by compiling the statement since no behavioural test can see it go. `status == CANCELLED_STATUS` compared the module's constant to itself and passed with it set to `"failed"`. And **nothing drove `_record_start`**, so deleting the stamp passed all twenty tests — the sweep was proved correct about rows nothing in production would produce._

_**One thing this sitting nearly got wrong.**_ _Two of the seven sit beside `failed` rows reading `"induced failure to verify covered_by"`, a string in neither the repo nor its git history, which reads exactly like a session's throwaway drive and would have put two rows outside the population. `_PID` refuted it: every line came from PID 2623454, the daemon — a session had edited `units/agent.py:179` to raise and restarted to watch it. A premise needs a witness that is neither the subject nor the story about it._

## Session 159 — the register declared dispositions and nothing read one back

_Its next action, since carried out:_ _Decide `SNAG-DB-006` by measurement rather than by preference — the seven stuck `running` rows in `agent_runs`, up from the five the entry counted on 2026-08-25 and dated 2026-08-14 to 2026-08-28, are the evidence for whether `cancelled` was meant for a run killed mid-`_execute`, and the entry's two candidate fixes are opposite, so date those rows against the daemon's restarts before either dropping the constraint value or writing the path that would fill it._

_**The guard Session 157 pre-staged is built, and it is the register reading its own field back.**_ _`convention:next-action` resolves every `SNAG-` id in `HANDOFF.md`'s published next action against the register **as it is now**, and refuses one whose entry declares `decided` or `delegated`. `check_dispositions` makes a **missing** disposition loud and its own last paragraph named this half as the residue: nothing read a declared one. The failure is measured rather than imagined — Session 138 refused `SNAG-TRAY-011`'s remedy on 2026-08-30, Session 156 stopped one bullet short of the refusal and published it, and `roadmap.py` republished it to the estate board verbatim._

_**Every id, and both narrower rules were refuted by the corpus rather than rejected by taste.**_ _Driven over the **21** distinct next actions in this file's history, resolving each id against the live document: the broad rule fires **once**, on Session 156's line, with **zero** other refusals. *First id* is refuted by the line this guard was written under — its first id is `SNAG-SYSD-003`, cited as evidence rather than named as the work. *Ids before the first em-dash* catches the same single true positive, because the house form is "Verb `SNAG-ID` — reason", and is blind on **2 of 21** whose only id sits after one. Breadth therefore costs no measured false positive here and is the direction whose failure is not silence._

_**It reads the entry's value now, and a list written when the guard was built would have been wrong about it inside an hour.**_ _At `4d8a464`, the commit that took the disposition population from zero to seventeen, `SNAG-SYSD-003` declared `Open — decided`; at `3f5af0d` an hour later it closed and its `Status` line went with it. One line, one id, two registers, **opposite verdicts** — driven both ways as a test rather than asserted._

_**A closed entry is reported and never refused, at the owner's ruling.**_ _Nothing separates an id cited as evidence from one named as the work, the live line is the counterexample that makes the false refusal reachable rather than theoretical, and **12 of 21** historic lines name an entry that is closed today. An id this document does not hold is neither — it is `unsayable`, because `SNAG-ESTATE-*` has two minters on this box and every pair names a different defect, so resolving a foreign id here would answer plausibly and wrongly._

_**A line naming no id is `match`, which departs from the two sibling sweeps deliberately.**_ _There the population is the register's open entries and an empty one means the reader was blind; here the population is **the line**, which was read in full and could have named a `decided` entry — `check_convention`'s own test for `match`. It is reachable in **5 of 21** measured sittings, so reporting `??` would teach the reader to filter this line, which is `known_noise` rule 2's objection to a warning that fires whatever happened. The genuinely blind states — no line, an unreadable document, an unreadable register — stay `unknown` and say which._

_**Two consumers, one implementation, which is what makes the owner's "both" one owner rather than two.**_ _`check_next_action` reports at preflight and postflight, where a refusal is news to judge; `tests/test_handoff_shape.py` calls *that function* rather than restating the rule, and refuses the commit. `disposition_word` was lifted out of `check_dispositions` for the same reason — two readers of one parse is `SNAG-DB-003`'s shape and would fail green in both directions — and the test asserts **provenance** rather than the value, because a second copy that happens to agree passes a value test._

_**The pin skips on the tree, never on the import.**_ _`next_action_line` reads this document rather than importing their public `next_action_from_handoff`, because `estate_service` is on this checkout's path by an editable `.pth` that is in **no lockfile**: a production path that goes quiet when an undeclared install is pruned is worse than a local read pinned against the owner's parser. `pytest.importorskip` would have disarmed that pin on the one box where it matters, so the skip is gated on `~/projects/estate-manager/service` existing, and present-and-unimportable is a **red**. Falsified three ways; the two reads are byte-identical today._

_**Fourteen mutations driven, and two are worth carrying.**_ _Ten against the module and four against the tests, each red on the tests about its own rule. The first-id reader leaves `test_an_id_after_the_em_dash_is_read_too` **green** — correctly, because that specimen has no id before the dash, which is exactly what isolates the two rules from each other — and ignoring `is_open` cannot reach the now-versus-snapshot test, because its closed stand-in drops its `Status` line faithfully to `SNAG-SYSD-003`; the refuse-a-closed-entry mutation is what falsifies that one. The blocking half was driven at Session 156's real line and goes red naming `SNAG-TRAY-011` and quoting its own body._

_**Nothing was filed, for Session 157's reason and one of its own.**_ _The residue the pin left was **fixed rather than filed** — the tree-gated skip is the fix — and filing an entry for it would have taken `convention:unchecked` from 0 of 19 to 1 of 20 to record a limit that no longer exists. `convention:next-action` is a convention finding rather than a twenty-third check, because every member of `CHECKS` names an open entry and this one names none._

_**Measured either side.**_ _Suite **3363 → 3387**: 20 tests in `TestTheNextActionIsJudged` and 4 in `TestThePublishedLineNamesNoWorkNobodyIsOwed`, none retired, the arithmetic checked rather than the green trusted. `ruff check .` and `mypy sysadmin` clean. All **22** prior snag verdicts unmoved, driven by stash-diff rather than counted. All **9** ops claims `ok` and the claim set identical either side._

_**Three live claims moved and all three were chased.**_ _The box **rebooted** at 07:35:12 before this sitting opened, so the start-time claim was already `no`; editing `sysadmin/snag_claims.py` then made the deploy claim `no` too, and the daemon was restarted (`kill -TERM`, no `sudo`, PID 1654 → 85280, back in 12 s on `Restart=always`). Two alert rows opened and **both are expected to fall**, said in the block so the fall is not read as news: `Unusual RAM usage` is the reboot (`direction: below`, `z_score: -4.6`, 7.4 % against a 19.73 % mean over 1878 samples) and is written in rather than waited out, because at 24 minutes it was **4.7×** the 5m16s median lifetime of the 51 resolved `Unusual %` rows; `Estate port 8110 registry breach` is `SNAG-ESTATE-009` behaving exactly as filed, carrying `attribution.reading: unswept` against an `observed_at` of 06:37:33, so the six-hourly sweep predates Alfred's `uvicorn --reload` and the hourly judge could not know it is a dev server._

_**One thing this sitting nearly got wrong and one it did.**_ _`agent_runs` holds **8** `running` rows and one of them was **49 seconds old and genuinely in flight** when counted — a live `file_organiser` scan, which takes ~118 s — so the figure the next action rests on is **7**, not 8. And `git checkout tests/test_handoff_shape.py` was used to revert a mutation mid-sitting; it reverted the file to `HEAD` and destroyed the new test class with it, which had to be rewritten. The `.bak` rule exists for exactly that and was not followed._

## Session 158b — a `decided` entry closed by measuring the question it reserved

_Its next action, since carried out:_ _Build the guard Session 157 pre-staged and left unbuilt — read `HANDOFF.md`'s next action for a `SNAG-` id and refuse one whose entry declares `decided` or `delegated` — because annotating the seventeen took its population from zero to seventeen, and `SNAG-SYSD-003` closing an hour later is the case that shows the guard must read the entry's *current* value rather than a list written when it was built._

_**`SNAG-SYSD-003` is fixed, and the question it reserved was closed by measurement rather than decided.**_ _`sysadmin.service` ordered `After=… ollama.service` for a runtime retired on 2026-07-24. The entry called `alfred-inference.service` **the correct successor** and reserved *"whether this service should order against it at all"* as the question to settle first — and it is not a question about preference. That unit is a **user** unit at `~/.config/systemd/user/` and reads `LoadState=not-found` in the **system** manager, which is where `sysadmin.service` lives; a system unit cannot order against a user unit, so the named successor would have rebuilt this entry's own defect under a newer name. One name removed, nothing put in its place, and an eleven-line comment left in the unit so the next reader does not re-open it._

_**The closure is the disposition field working, not a contradiction of it.**_ _`SNAG-SYSD-003` was annotated `Open — decided` an hour before the owner re-opened it. A `decided` value records a **decision that can be re-opened**, never a closure, and the register naming it is what put the decision in front of someone who could take it. That is the intended direction of use and it is stated here because the opposite reading — that a `decided` entry is settled and need not be shown — is the one that would make the field worse than nothing._

_**The check retired and the detector did not, and the guard is deliberately wider than the entry.**_ _`check_sysd_ollama_ordering` left `CHECKS` — `test_every_checked_entry_is_open` makes that mandatory rather than tidy — and `tests/test_unit_ordering_live.py` is where its two limbs went. It asserts that **every** unit named in `After=` resolves, not that one string is absent, because the entry's stated cost was never the one name: it is that *"the unit file is read as the record of what this service depends on"* and that whoever derives a unit from it, which `monitorable-project.md` invites, copies the staleness forward. A guard keyed on `ollama.service` would have pinned the instance and said nothing about the next one._

_**`RETIRED_UNIT` outlived its check by acquiring a second job, which is the only thing that earns a constant its keep here.**_ _A sweep asserting every ordered unit resolves cannot tell a healthy answer from a `systemctl` that says `loaded` to everything — `systemctl show` answers for a unit that does not exist and exits `0`, which both `unit_load_state` and `ops_claims.UnitState` already record. So the guard reads `ollama.service` as its **negative control** and requires `not-found` back. That is the retired check's second limb surviving its first: the day Ollama is reinstalled the control resolves and the premise fails loudly, where the fault sweep would go on passing._

_**Five mutations driven, each red on the tests about its own rule, and two are worth carrying.**_ _The reader answering `loaded` to everything turns the **control** red alone while the sweep stays green — which is precisely the blindness the control exists for, and the shape a first draft would have shipped without. And naming `alfred-inference.service` in the line turns the sweep red, so the successor ruling above is demonstrated rather than asserted. The other three: `ollama.service` back in the line (sweep **and** instance test), the `After=` line emptied (the vacuity premise), and the reader answering nothing at all (control and sweep, because a unit nobody could ask about is reported and never skipped)._

_**`SNAG-ESTATE-006` keeps `delegated` and loses its handover clause, at the owner's direction.**_ _No filing is wanted. The reasoning is now in the entry rather than in this document: the cost here is measured at none, `details['fingerprint']` already carries the code where a human can read it, `judge_audit_findings` goes on reading the key so it starts working with no change here the day they publish one, and `check_audit_code_unpublished` reads their live route every sitting — so the delegation is **watched** rather than merely remembered, which is what a handover message would have bought._

_**Measured either side, and the cross-repo read is the witness that matters.**_ _`convention:disposition` reads **3 of 19**, `blocked 4, decided 7, delegated 5`, with the movement line reporting `-1 open`. estate-manager's own `read_snags` driven over the finished document agrees: **122 entries, 19 open**, `SNAG-SYSD-003` `is_open=False, fixed_at=2026-09-02`. Suite **3363** — 3362 + 4 added − 3 retired, the arithmetic checked rather than the green trusted — `ruff` and `mypy` clean. All remaining snag checks unmoved. `systemd-analyze verify` clean on the edited unit._

_**Two live claims moved and both were chased to `ok`.**_ _Editing `sysadmin/snag_claims.py` made the deploy claim read stale, so the daemon was restarted (`kill -TERM`, no `sudo`, PID 3412364 → 3524153, back in 10 s on `Restart=always`) and the start-time claim updated with it. `Unusual CPU usage` opened at 21:20 while the block was being written — a transient anomaly row with a **5m08s median lifetime across 37 historic rows** — and the block's own rule is to write the **steady** figure rather than chase a burst._

_**What the box still owes, said rather than left to be found.**_ _`/etc/systemd/system/sysadmin.service` was byte-identical to the repo copy before this edit and still carries the old `After=` line; the install is `sudo cp systemd/sysadmin.service /etc/systemd/system/ && sudo systemctl daemon-reload`, which this session could not run (`sudo -n` wants a password here). **No restart is implied by it** — `After=` decides ordering at start and nothing else — so the running daemon is unaffected either way, and the guard is green on the checkout regardless because it reads the repo copy, which is the file `monitorable-project.md`'s readers copy from._

## Session 158 — the seventeen entries owed nothing say so

_Its next action, since carried out — and the same sentence stands for the next sitting, sharpened by what happened after it:_ _Build the guard Session 157 pre-staged and left unbuilt — read `HANDOFF.md`'s next action for a `SNAG-` id and refuse one whose entry declares `decided` or `delegated` — because annotating the seventeen has just taken its population from zero to seventeen, and it is the one control that would have caught the failure which opened this two-sitting sequence._

_**`convention:disposition` reads 3 of 20, and what is left undeclared is exactly the work queue.**_ _The seventeen open entries Session 157 measured as owing nothing now carry `- **Status:** Open — <disposition>`: **decided 8, delegated 5, blocked 4**. The three still undeclared are the three measured `owed` — `SNAG-LOG-013`, `SNAG-SVC-002`, `SNAG-DB-006` — so the sweep's residue and the work queue are the same set. That is the property the sweep was built for and it is stated here rather than left to be noticed, because a number falling towards zero and a number falling **onto the owed set** are different results._

_**Each of the seventeen was read before it was classified, not taken off the tally.**_ _The four `blocked` divide into three different preconditions and the value says which: *a population* (`SNAG-AGENT-012` and `SNAG-AGENT-013`, both fixes one condition waiting for something to test against — 0 open rows in the `% unreachable` family, 0 of 31 services setting `auto_restart`), *an operational fact* (`SNAG-DOCS-003`, where the wheel went, which no check here can reach) and *the owner* (`SNAG-SVC-001`, whose two honest resolutions are both theirs and nothing measurable prefers either). Read off the bullet lead-ins those four are indistinguishable._

_**The word carries the verdict and the remainder carries the reason, which is what let one value be honest about a residue without moving its own bucket.**_ _`check_dispositions` reads only the first token after `Open — `, so `SNAG-ESTATE-006` declares `delegated` — the missing `code` column is the estate's, and the only workaround available would parse an identity format they own — while its own clause records that it was **never handed over in writing**. Measured: `GET :8400/api/estate/messages?sender=sysadmin_assistant` holds 19 messages and none of them is that handover. A filing is the one thing outstanding on this side, and it is named in the register rather than absorbed._

_**The cross-repo hazard was proved rather than trusted, twice and by two different routes.**_ _`check_dispositions` calls estate-manager's **public** `status_is_done` per value and reported no closure. Independently, their `read_snags` was driven over the finished document in their own tree: **122 entries, 20 open**, identical to `HEAD` — so none of the seventeen closed an entry in the reader that publishes this estate's movement figures. The second is the one that matters, because the first is this repository asking itself whether it got the anchor right._

_**Two live claims in `STATUS.md` were corrected, one of them this edit's own and one the checker found.**_ _The block's `20 of 20` figure is now `3 of 20` with the tally beside it. And `check_alerts` reported a **fall** four hours after Session 149's — `SNAG-ESTATE-008`'s founding case twice in one day: `alfred-career-mail-timer critical` resolved at **20:50:08** because `alfred-career-mail.service` was run by hand at 20:47:54 and finished `Result=success` with `ExecMainStatus=0`. The timer's `last_run` is **unchanged** at `Wed 2026-09-02 08:20:00 BST` — the timer never fired, and what the check reads since `SNAG-SYSD-005` is the service's result rather than the timer's, so the row behaved exactly as the block's own paragraph predicted when it said the critical was Alfred's to close._

_**Two classifications were re-opened on reading and both were left where Session 157 put them, with the reasoning recorded so a later sitting need not redo it.**_ _`SNAG-SYSD-003` is closable from this checkout — `check_sysd_ollama_ordering` reads the **repo** copy at `systemd/sysadmin.service`, not the root-owned `/etc/systemd/system` one, so the fix is a one-line edit needing no `sudo` — and it stays `decided`, because the entry's own **Deliberately left** bullet names an unsettled prior question (whether this service should order against an inference runtime at all) that sits inside the decision rather than blocking it. `SNAG-CFG-003` stays `decided` rather than `blocked` on the same line: `SNAG-AGENT-012` and `SNAG-AGENT-013` intend a fix and wait for a trigger, while that entry asks *"if one is ever wanted"* and ranks itself P4 against a coherent shipped file._

_**Nothing was added to the suite and that is the correct result, not an omission.**_ _The change is seventeen documentation lines; `check_dispositions` and its four falsification tests shipped with Session 157 and are what measure this. Suite **3362 passed, 1 skipped**, unmoved from the baseline. All **22** other snag checks unmoved, verified by diffing the full verdict list either side. All **9** ops claims read `ok` after the `STATUS.md` edit, and the claim *set* is identical either side — driven by stash rather than counted, because a disarmed marker removes a claim and a smaller list of `ok`s reads exactly like a clean one. The only verdict that moved is the alert count, `no` to `ok`. (Session 156's handoff said ten; nine is what the script emits today.) `ruff check .` and `mypy sysadmin` clean._

_**The residue is the one Session 157 put to the owner, and its population has just stopped being zero.**_ _The sweep makes a **missing** disposition loud and can say nothing about a **wrong or stale** one — an entry declared `blocked` whose precondition has since arrived still reads `blocked`. That is this repository's founding defect class inside the fix for it, and the next action above is the cheapest reachable part of it: not a staleness check, which would need to re-derive every precondition, but a refusal to *publish* a next action naming an entry that declares no work owed. No snag was filed, for Session 157's reason — filing an unchecked entry would take `convention:unchecked` from 0 of 20 to 1 of 21 to record a limit the new check already reports._

## Session 157 — the register measured the condition and never the disposition

_Its next action, since carried out:_ _Annotate the seventeen open snag entries that are not owed work with `- **Status:** Open — <disposition>` so `convention:disposition` falls from 20 of 20 towards zero, taking the eight `decided` entries first because that is the category the stale next action was drawn from._

_**The next action this sitting was handed had already been carried out, and the register could not say so.**_ _Session 138 measured `sysadmin-tray.service` and refused the `log:` block on 2026-08-30 at commit `7be7643`, 25 commits back; `SNAG-TRAY-011` has carried the refusal in a **Decided** bullet ever since. Session 156 read the entry's *"Shape of a fix as originally proposed"* bullet and stopped one bullet short of the `— refuted 2026-08-30, see the decision below` that follows it. The refused remedy was then published estate-wide: `GET :8400/api/projects/sysadmin_assistant` was serving it at `findings.roadmap.next_action` with `next_action_source: handoff` when this sitting looked._

_**Re-measured rather than taken from the entry**, three days and 48,325 records on: **725,892** journal records over **22.52 days**, 32,228/day, **every one `PRIORITY=6`**, `725,841` ` INFO ` tokens and **zero** at `WARNING`/`ERROR`/`CRITICAL`. `max_priority_for("warning")` is **4** and `FAULT_SEVERITIES` is `("error", "critical")`, so both of Session 138's gates are unmoved. `NRestarts=0` since 2026-08-30 17:04:35, so the once-at-startup warning has not fired since before the decision was written. The entry stays open, correctly — it is a deliberate non-fix and its check still reports `ok`._

_**The gap was never SNAG-TRAY-011's; it is that the register measures the condition and nothing measured the disposition.** Every open entry carries a check and a check answers *does this still hold* — so `check_tray_report_unheard` reporting `ok` is the entry working as designed. `priority` does not answer it either. Classified by hand across all twenty, with the four riskiest calls read in full rather than off their bullet lead-ins: **3 owed** (`SNAG-LOG-013`, `SNAG-SVC-002`, `SNAG-DB-006`), **4 blocked** (`SNAG-AGENT-012`, `SNAG-AGENT-013` on an empty population, `SNAG-DOCS-003` on an operational fact, `SNAG-SVC-001` on the owner's ruling), **5 delegated**, **8 decided**. A ranker picking off the open count alone had a **15 %** chance of landing on work._

_**Three of the classifications moved on reading and would have been wrong from the lead-ins alone.** `SNAG-AGENT-013`'s *"Not fixed in the same sitting, deliberately"* closes *"which is precisely why it should be written when there is something to test it against"* — blocked, not decided. `SNAG-DOCS-003` needs an operational fact rather than code. `SNAG-SVC-001` says in terms that *"the honest resolutions are two and both are the owner's"*, so it is waiting on the owner and not on a sitting._

_**The obvious marker was already refused by an entry in this document.** `SNAG-ESTATE-012` rejected `<!--check:none reason-->` as *"a marker whose absence is indistinguishable from forgetting it — the thing it is meant to detect"*, and a bare `<!--disposition:x-->` is that shape exactly. What ships is not a different spelling but a **sweep**: absence is reported over the whole open population in every state, so forgetting is a number rather than a silence — `ports_checked`'s rule, and `check_convention`'s `SNAG-DOCS-006` line one question along._

_**The field is Alfred's convention, not a new one**, which is why this is an adoption rather than an invention. Alfred writes **60** `Status:` fields in its own snag list and one reads *"Open — deliberately left unfixed, not missed"*; this repository wrote **none**, and `estate.snags` has parsed that field since it moved to the library._

_**The hazard is another repository's parser and it is made unreachable rather than documented.** `estate.snags._DONE_WORD_RE` contains `won't fix` — the natural English for the `decided` disposition — so a value opening with it **closes the entry** in the reader that publishes this estate's movement figures, silently and in their count rather than ours. Every value is anchored with `Open — `, and the check proves it per value by calling their **public** `status_is_done` rather than restating their word list: `max_priority_for` against `PRIORITY_MAP`'s rule across a repository boundary, and public because a private helper's name is what their next fix renames. Driven both ways — `"Won't fix — measured refusal"` closes, `"Open — decided, won't fix, measured"` does not._

_**`STATUS_FIELD_RE` is copied and the closure rule is imported, and the asymmetry is the argument.** Their status-field pattern is `_STATUS_FIELD_RE`, private, so it is written here instead — safe in both directions: narrower than theirs a declaration goes unseen and the entry is reported **undeclared**, which is loud and is the failure this check exists to make loud; wider than theirs, a line they do not read as a status is accepted here and their closure rule never sees it, so the hazard cannot arrive by that route either._

_**Check first, at the owner's direction.** The commit ships the checker alone, reporting **20 of 20 open entries declare no disposition**; entries gain the field as they are touched and the number falls on its own. The vocabulary — `owed`/`blocked`/`decided`/`delegated` — is **local and deliberately unpublished** (owner's ruling, *"fine only for me and you reading it"*), so nothing here derives from or offers an estate list._

_**Announce-by-filing, before the commit**, at a measured audience: estate-manager parses this document live in four modules and holds a frozen copy with goldens at `lib/tests/corpus/sysadmin-assistant.snag_list.md`. Message `70377694-c7e6-4cb8-9c92-7c9c3258f82b`, carrying the hazard, the corpus drift and the cost._

_**Measured either side.** Suite **3362 passed, 1 skipped** against a baseline of **3349 passed, 1 skipped** — 3349 + 13, none retired. Four mutations driven and each lands red on the tests about its own rule; the fully-declared stand-in returns `match`, so the check is not coupled to the unfixed document — `check_review_schedule_unread`'s defect refused in advance. All **22** existing checks unmoved, `convention:unchecked` still `0 of 20` and the movement read still `unmoved`. `ruff check .` and `mypy sysadmin` clean._

_**Residue, put to the owner rather than filed.** The sweep makes a **missing** disposition loud and can say nothing about a **wrong or stale** one — an entry declared `blocked` whose precondition has since arrived still reads `blocked`, which is this repository's founding defect class inside the fix for it. A check is writable and was scoped out: read `HANDOFF.md`'s next action for a `SNAG-` id and refuse one whose entry declares `decided` or `delegated`, which is exactly the failure that opened this sitting. Its population is zero until entries are annotated, so it is pre-staged work rather than a defect today, and no snag was filed — filing an unchecked entry would take `convention:unchecked` from `0 of 20` to `1 of 21` to record a limit the new check already reports._

## Session 156 — a red said the hazard was gone whatever had happened

_Its next action, since carried out — and it named work another sitting had already measured and refused; see Session 157 below:_ _Close `SNAG-TRAY-011` by first measuring what `sysadmin-tray.service` actually writes at `warning` and above, because the entry refuses its own originally-proposed `log:` block in `services.yaml` until that number exists — declaring a new log source widens what the monitor ingests, and `SNAG-LOG-004` is this repository's own record of a fix that widened a monitor's view becoming a regression surface for whatever consumes it — and then either declare the source or record the measured refusal in the entry._

_**`SNAG-TEST-003` is fixed, and it was the last open entry naming no check — 20 open, 0 unchecked.** Its claim was never about a mechanism (both candidate causes were refuted while it stood) but about a sentence: `test_notify_send_does_not_return_on_a_bus_with_nothing_listening` asserted that a red meant the D-Bus activation *"is gone from this box and the guard's urgency should be re-derived"*, so **any** red reported good news and the honest response to good news is to relax the control. It now asserts a **precondition before the block** — that `plasma_waitforname` started under this fixture's own bus at all._

_**Three states measured before the fix was written, not reasoned about.** Hazard intact, the control: activated, blocked, **8.03 s**. Reading disturbed by three scoped kills landing inside the window, which is `SNAG-TEST-004`'s own mechanism replayed: **activated**, returned at **3.06 s**, `StartServiceByName … exited with status 255`. Hazard genuinely gone, a `dbus-daemon` started against a config declaring no service directory so nothing activates the name: **not** activated, returned at **0.03 s**, `ServiceUnknown`. `returned` is common to both failing readings; the activation is the only thing that separates them, which is why a precondition works where a differential would still be measuring a box other sessions are perturbing._

_**The sampling had to move inside the call, and that is forced rather than a refinement.** The disturbed row's waiter is dead by the time `notify-send` returns — killing it is what errored the call — so a single check *afterwards* reports "no activation" for a disturbed box and a fixed one alike, reproducing the exact collapse being removed one line later. `subprocess.run(timeout=…)` hands back only what the process ended with, so `_notify_send` is a polled `Popen` now. `_ACTIVATION_POLL_SECONDS = 0.02` is derived: the waiter appears **48–50 ms** after the call, four trials for four, then persists for the whole 8 s block (124 consecutive sightings). Its failure direction is the unsafe one — a waiter started and reaped inside one poll would read as no activation, which is the reading the precondition exists to refuse — so the two orders of magnitude are the argument and the caveat is named in the assertion's own message._

_**The budget was not raised**, which the entry named as the thing that must not happen: a larger `BLOCK_PROBE_SECONDS` makes the red rarer without changing what it means. **`stderr` decides nothing** — the two failing shapes do carry distinct messages and both are quoted into the failure as evidence for whoever is triaging, but keying on them would be a second implementation of a judgement `activated` already states. **One argv serves both halves**: `watch_pid` is a parameter rather than a sibling function, because the module's whole evidence rests on the two observations differing in exactly one thing, and `NotifySendOutcome` replaced the tuple so the fields carry a docstring saying why they travel together._

_**`TestTheRedSaysWhichReadingItIs` is what outlives the finding**, and only the ordering could be pinned cheaply. Swap the two asserts and the block assertion's message — *"a waiter **was** started"* — becomes false on a box where the activation is gone, which is the original defect wearing the fix's clothes; delete the precondition and the entry is back. Both mutations land red on it. It reads each assert's **`test`** and never its `msg`, because both messages quote `outcome.elapsed` and a whole-node walk would report agreement whatever the order was — `test_live_drive_scoping.py`'s prose problem one AST node deeper, where the confusable thing is an f-string rather than a docstring._

_**No check, and the closure is what restores the register's own property** rather than a check being written to satisfy it. One would have to reproduce an intermittent fault on demand; the entry closes by the wording changing, and `check-snag-claims.sh`'s `??` line clears with it._

_**Measured either side.** Suite **3349 passed, 1 skipped**; the changed file went **7 → 8** tests and nothing else in the tree moved. All **22** existing checks driven before and after — none moved, and the `??` open-entries-with-no-check line is gone. `ruff check .` and `mypy sysadmin` clean; `ruff format --check` was **not** applied, because the file fails it at `HEAD` too and the repository does not enforce it. All **10** ops claims read `ok` after the STATUS.md block was extended, so no marker was disarmed. And `SNAG-TEST-004`'s scoping property was re-measured under the new probe rather than assumed to survive it: two offset concurrent runs at 5 s and 6 s, **4 for 4 green** at the full 8.7 s, **zero** stray waiters left on the box._


## Session 155 — the fold said whose step leads only in prose

_Its next action, since carried out:_ _Close `SNAG-TEST-003` by rewriting `test_notify_send_does_not_return_on_a_bus_with_nothing_listening`'s assertion so that a red separates *the hazard is gone* from *this reading was disturbed* — the entry names the cheapest form as a precondition rather than a differential, asserting the waiter was activated at all before asserting the call blocked, and it is the last open entry in the register carrying no check because a check would have to reproduce an intermittent fault on demand._


_**`SNAG-SVC-004` is fixed, and the decision the entry left open was whether to read the fact or work it out again.** `SNAG-SVC-003` let a `timer_failed` member's step supersede the anchor's and `_folded_row` rule 5 wrote *whose* step leads into the folded `detail`; `health_review._service_facts` projects `title` and `action` and **not** `detail`, so the weekly review printed one finding's remedy under another finding's title with nothing saying the subject had changed. `ServiceRecommendationInfo.action_from` is that fact as its own field — the promoted member's `kind`, empty when the step is the anchor's own._

_**`stands_for`'s treatment is a derivation, and copying it literally would have been the defect.** That field is `m.title for m in members if m.kind != r.kind` — a restatement of what *swallowed* means, which is structural and cannot disagree with the producer. The same shape here is `next(m.kind for m in members if m.kind in STEP_SUPERSEDES)`, which restates which member **won**: a judgement `_folded_row` already took, free to drift the day that tuple widens. `SNAG-DB-003`'s shape, and `judge_queue_invariants`' *"the mask is read, never recomputed"*. So the producer publishes it and every consumer reads it; a test drives a row whose `action_from` names a kind no derivation from its own `members` could produce, and that is the one mutation-and-test pair separating the two designs._

_**Empty is deliberately not `ports_checked`'s not-knowing, and the alternative was refused rather than overlooked.** The field reads `""` both for a row whose step is its own and for a producer that does not publish it; every other absent-vs-present collapse here hides a **blind** reading and this one cannot, since both mean "render nothing extra". Spelling it as the row's own `kind` — Session 128's *"uniform on every row"* — does not transfer: that rule is about a `details` **key** whose presence is the only signal, and a pydantic field is always present, so the uniform scalar fires the renderer's clause on every folded row and makes every consumer compare two fields to learn nothing._

_**Both fold shapes were live at the moment of the fix**, which a specimen of one could not have discriminated: `alfred-career-mail-timer` (`outage` + `timer_failed`) reads `action_from: "timer_failed"` and `venture-chat` (`outage` + `flapping`) reads `""`. The entry called the live line *correct by luck of one string* — `_timer_failed_row`'s step happens to explain its own subject — and it now says so in its own words instead._

_**The guard is a test rather than a twenty-first check, and the entry's own last bullet is the argument.** What one would drive asserts the **fix**, and `check-snag-claims.sh`'s `ok` means *the bug is still real*, so such a check reports a landed fix for ever — `check_review_schedule_unread`'s defect. `TestTheStepsProvenanceIsProjected` is `FROZEN_TABLES`' rule met from the other end. Open entries with no check goes **2 → 1** by the entry closing, not by a check being written._

_**The refused fix is pinned rather than merely avoided.** Projecting `detail` would carry the provenance *and* every swallowed row's own detail and step into the blob the review is built from, so `test_the_projection_still_carries_no_prose_body` asserts `detail` is absent from the projection._

_**Announce-by-filing: the audience was measured and is empty, so nothing was filed.** `GET /api/services/actions` gains a field, which is a change to a published surface. Outside this repository the route is named in exactly one place — estate-manager's `lib/tests/corpus/` copy of this repository's own `snag_list.md`, a parser fixture and not a reader — and `estate-map.md` records one consumed route from 8500, `/api/sysadmin/briefing/preview`. The tray reads the model and ships in this wheel._

_**Measured either side.** Suite **3348 passed, 1 skipped** against a baseline of **3342 passed, 1 skipped** — 3342 + 6, none retired. Seven mutations driven and each lands red on exactly the intended test, with every one of the six new tests killed by at least one; the recomputing-projection mutation lands on exactly one. Stash-diffing `check-snag-claims.sh` leaves all **20** checks unmoved, `SNAG-SVC-001`'s top-level scan and `SNAG-SVC-002`'s importer set included — the two whose instruments reach the modules this sitting edited. `ruff check .` and `mypy sysadmin` clean at head 018. The daemon restarted at **17:25:00** and served the field within a second; all **10** ops claims read `ok` after the block's start-time figure was corrected, which the checker caught rather than the sitting remembering._

## Session 154 — the check's instrument was also its safety catch

_Its next action, since carried out:_ _Fix `SNAG-SVC-004` — project the fold's step provenance into `health_review._service_facts` as its own field rather than by sending `detail` wholesale into a prompt that is figure-free by construction, which is `stands_for`'s treatment for a second fact, and that entry's own last bullet argues the check belongs with the sitting deciding the field's shape because it asserts the fix rather than the defect._

_**`SNAG-AGENT-013` has the twentieth check and stays open.** It is the first check here whose subject is an **action** rather than a row. Every other drive in the registry writes something and rolls it back; this one enters `_handle_status`'s auto-restart branch, whose whole point is that it starts a unit on this box, in a module `check-snag-claims.sh` runs at both ends of every sitting. So `restart_unit` is **patched rather than reached** and the probe's unit is minted per call — two guards, because the first one failing is the case the second exists for. Open entries with no check went **3 → 2**._

_**The instrument is also the safety catch, so it needed a second witness.** The patched call is the harness's observation and `_failure_counts` is the subject's — reset to zero three lines into the branch, by nothing the fixture supplies, which is `_suppressed`'s role one entry over. They can disagree only if the branch reaches systemd by a name the drive no longer patches, and that is `unknown`: without the counter, an instrument that stopped binding would have reported this entry **fixed** *and* let the restart through._

_**The obvious instrument would have shipped green.** `self._arbitration` **is** consulted a dozen lines below the branch, so a source walk finding it in `_handle_status` reports it consulted; and a walk asserting it is absent *above* the branch refutes the moment somebody moves a line, whether or not the gate changed. The claim is about the **order of two conditions** and only running the branch settles it._

_**Three arms, and the control holds a lease rather than holding none.** `unread` is the premise — `auto_restart`, `controllable`, a unit and the streak are four conditions and three are the harness's, so a restart that does not fire with nothing arbitrated is a broken fixture rather than a landed fix. `other` and `stopped` then differ in exactly one boolean, which is what separates a gate on the **unit** from a gate on *"a lease is granted"*; the second would stop restarting `alfred-backend` because the estate stopped `venture-chat`. Driven: moving the premise to a granted arm reddens exactly the lease-gate test and nothing else._

_**The population is reported and never scored, in the direction this entry makes easy to invert.** Its own `Why P3` is *"unreachable until somebody sets one leaf"*, so the leaf being set **raises** it — wiring the count to the verdict could only retire the entry at the moment it became live. Live: all three arms restarted, **0 of 31** services set `auto_restart` with a controllable unit, and `venture-chat.service` is the one unit this daemon has recorded the arbiter stopping, across **4** rows. The two halves have not met and the distance is one leaf._

_**Thirteen mutations driven and thirteen red, two of them worth carrying.** Removing the swap altogether let the real `restart_unit` run, aiming `systemctl --user restart` at the minted unit, which failed harmlessly — the second guard **demonstrated** rather than argued for. And re-recording the call while still delegating to the real one is the only mutation that lands on the sentinel assertion, which is what makes `reached == []` evidence rather than decoration; under the swap-removed mutation that test fails on its **premise** line instead._

_**mypy chose the stand-in's parameter name.** It rejected `target` against `restart_unit(unit, user)`: a stand-in that is not substitutable for the name it replaces is a control the next caller breaks, and the type checker is what says so — the parameter is spelled `unit` and the closure variable became `probe_unit`._

_**The population filter has no discriminating witness on this box.** Every assertion about it is satisfied by `()` whatever the filter does, since nothing sets the leaf, so `auto_restart and controllable and systemd_unit` is driven against a synthetic services file — a constant observation is not evidence unless something in the population would have forced a different one._

_**`rung_sql` became `schema_sql` and moved beside `query_one`.** The fault it prevents — no `search_path`, so an unqualified name resolves to `public` and fails as *"the database did not answer"* — is a property of that connection, not of the entry that first hit it, so the second caller borrows the rule instead of copying the fix. The sibling's 21 tests are unmoved._

_**Measured either side.** Suite **3342 passed, 1 skipped** against a stashed baseline of **3319 collected** — 3319 + 24, none retired. Stash-diffing `check-snag-claims.sh` gives exactly one new `ok` line and unchecked entries 3 → 2, with all **19** existing checks unmoved. `ruff check .` and `mypy sysadmin` clean, `check-migrations.sh` at head 018, and the daemon restarted at 16:53:22 answering `/health` 200 — the restart owed to the deploy **claim** rather than to the code, since the daemon does not import `snag_claims.py` and the check compares file mtimes and cannot know the difference. All nine ops claims read `ok`._

## Session 153 — the entry named its own trigger and had no instrument for it

_Its next action, since carried out:_ _Write the twentieth snag check, for `SNAG-AGENT-013` — it is the direct sibling of the entry this sitting checked, its mechanism is one missing condition in `_handle_status`'s auto-restart branch (which never consults `self._arbitration`), and the drive must patch `restart_unit` rather than reach it, because the whole point of that branch is that it really does start a unit._

_**`SNAG-AGENT-012` has the nineteenth check and stays open.** Its last bullet named a mechanical trigger nothing could answer — *"the first `alert_rung_left_stale` line that is not a test's"* — and that is a query now. The *"not a test's"* half needs no clause at all: `log_entries.source` holds the **unit**, and a test runs in the sitting's own process and never under `sysadmin.service`, so a row there is the running daemon's by construction. Live: **0** trigger rows against **135** `alert_raised` rows as the witness that the path works, and **0** open `% unreachable` rows. Open entries with no check went **4 → 3**._

_**The population is reported and never scored, and the direction is what makes that easy to get wrong here.** Rule 1 usually guards against an empty population reading as a refutation; this entry inverts it — a trigger line appearing *strengthens* the claim, so wiring the count to the verdict could only ever report a claim that had just become more true as a dead one. It goes in the detail with the open `% unreachable` count beside it, and the `alert_raised` witness is not optional: zero-because-quiet and zero-because-blind are the same zero and only one is evidence._

_**The obvious instrument would have shipped green and inert.** `may_quieten_in_place('critical', 'info')` is `False` and is the root of the whole mechanism — and it is exactly what `step_for`'s resolve-and-re-raise deliberately leaves alone, since that fix exists **because** an in-place escalation is inaudible. A check asserting the predicate answers `match` either side of the fix, which is `check_review_schedule_unread`'s defect. It is carried as a premise in the detail; the verdict is driven, entering at `_raise_judged` rather than at `_refresh_open` because the fix may land in either and a drive below the fork would read a fix above it as no fix._

_**The drive says something sharper than the entry does.** `SNAG-AGENT-009` made a held row's *sentence* correctable, so what a poll actually leaves behind is not a stale row but an **internally inconsistent** one: `message` reading *"the unit did not come back when the lease released"* at `severity: info`. A check reading `_refresh_open`'s boolean would have reported the row brought up to date._

_**One of fourteen mutations passed against every test in the class, and it is the one worth carrying.** A drive aimed at `_refresh_open` — one level below the fork — bypasses the dedup hold, and the author of such a drive writes the `raised = 0` in by hand because they put the standing row there. A premise read off a number the harness supplies is not a premise. `_suppressed` is the third-party witness **inside the subject**: `_raise_judged` increments it in the branch that holds and `_refresh_open` never touches it, so it says which entry point ran._

_**`_refreshed` was briefly in that repaired premise and the fix stand-in is what took it out.** That counter is incremented *inside* `_refresh_open`, so `step_for`'s shape — which replaces that method — leaves it at zero with the hold plainly fired, and the check reported `unknown` over a landed fix. A control the fix breaks, caught only because one stand-in models the **fix** rather than the defect; both directions are pinned now._

_**Two weak tests were repaired before anything was mutated.** One assertion existed only to make the class name the check key for the `unknown`-branch sweep and asserted nothing; and a before/after count of trigger rows across a check run is **constant here whatever the drive does**, since a test process cannot reach `log_entries` under `sysadmin.service` at all — a constant observation is not evidence. It asserts the observable mechanism instead: whether the record reaches a root handler, which is what severing `propagate` is really for._

_**The first draft's four statements were unqualified.** `query_one` opens a connection with no `search_path`, so `log_entries` resolved to `public` and every one answered `ProgrammingError` — reported as *"the database did not answer"*, a sentence about an unreachable database sitting under a green verdict and a silent population. `rung_sql` derives the schema at call time rather than at import, because a report run by a shell script imports this module before anything has chosen a config._

_**Two event names were lifted to constants at their emitters**, `RUNG_LEFT_STALE_EVENT` and `ALERT_RAISED_EVENT`. Not tidiness: a rename with the check spelling its own copy leaves the population query counting a name nothing writes, reporting *the trigger has never fired* for ever, which is the silent direction. Pinned by identity **and** by an AST walk asserting the import, because a literal and an import both read `alert_rung_left_stale`._

_**A pre-existing red was found and repaired, and it was a box-wide selector again.** `tests/test_quietened_judgement_live.py` asserted `result.details["resolved"] == 0` — the **whole run's** sweep — while meaning "no resolve-and-re-raise under this drive's own title". The judge's two live dev-server breaches on 3110 and 8110 made it 2, so the test was red on any box with an editor open and green otherwise: `SNAG-TEST-004`'s class one file over, and seasonal. Verified pre-existing at HEAD **by stashing before blaming this sitting's work**; the scoped count still turns red under a modelled resolve-and-re-raise, driven._

_**The unresolved-alert count flapped 5 → 3 inside this sitting** and STATUS.md was deliberately **not** corrected for the transient reading — the two `Estate port` rows open and close with an editor window, which that block already warns about in its own brackets. `check-ops-claims.sh` reads all nine claims `ok`._

_**Measured either side.** Suite **3318 passed, 1 skipped** against a stashed baseline of **3298 collected** — 3297 + 21, none retired, and the cell was right for the second sitting running. `ruff check .` and `mypy sysadmin` clean, `check-migrations.sh` at head 018, all **19** snag checks reporting, and the daemon restarted at 13:06:58 answering `/health` 200._

## Session 152 — the fix had been in the tree two days, and the control it claimed had never existed

_Its next action, since carried out:_ _Write the nineteenth snag check, for `SNAG-AGENT-012` — its own entry names a mechanical trigger it has no instrument for (*"the first `alert_rung_left_stale` line that is not a test's"*), it is one of only four open entries `check-snag-claims.sh` cannot speak for, and its failure mode is the silent one, a genuine `critical` held at the floor rung because the ladder that would raise it runs one way.

_**`SNAG-TEST-004` is closed and the code half had been in the tree for two days.** `2502dbc` scoped both escaping operations on 2026-08-31 and touched no document, so the entry read open over a fix that was already green. Establishing which half was outstanding was the sitting's first job and it was done by measurement: **7 passed in 8.68 s**, and **zero** waiters left on the box by either bus-starting live drive — counted by `comm`, because the obvious `pgrep -f` matched its own diagnostic shell on the first attempt, which is this entry's own defect class reproduced live._

_**What was genuinely outstanding is a control that was claimed and never built.** The entry said the taker count *"is now pinned by an `ast` walk"* and the shipped module docstring said *"pinned by an AST walk"*; nothing in this repository has ever walked that file. It is left **unbuilt** rather than written, because the number stopped deciding anything the moment the kills were scoped — four unscoped kills against a threshold of three was the whole argument, and four *scoped* kills reach four processes the fixture started, as would forty. Both sentences are corrected instead._

_**`tests/test_live_drive_scoping.py` is what replaced it, and it is wider than the entry deliberately.** It refuses a box-wide process selector in **any** `tests/test_*_live.py` drive, because the hazard belongs to starting a private resource and then selecting by a pattern the box shares. The population was re-measured rather than inherited: seven live drives, two of which start a `dbus-daemon`, and `test_failure_replay_live.py` never had the defect — it kills only the daemon and triggers no activation, verified at 5 passed and zero waiters._

_**A text sweep is the inverse of that walk, not a coarser version, and the measurement decided the detector's shape.** At `ec54ab8` — the revision carrying all three unscoped calls — the module docstring names neither `pkill` nor `pgrep`; at `2502dbc` it names both, because the fix explains itself, so a grep reports the file that is right and passes the file that is wrong. The walk reads argv and the `shell=True` string given to a runner and nothing else, so prose falls out by construction. **The selector is judged, never the read** — `_waiters_under` still lists every process on the box and is correct, because it selects by ppid chain afterwards._

_**Seven mutations driven and seven killed**, each on its intended test, the first two being the two real pre-fix calls put back into the guarded file. Two things only running it could have said: the detector **reports its own file**, not from its stand-in sources — those are strings, and a string is prose — but from its *expected values*, since `== ["pkill"]` and an argv list are spelled identically, which is the mirror of the prose problem arriving inside the fix for it; and the pre-fix specimen's assertion was written in the wrong order, because the walk sorts by line and the `pkill` sits at 138 while both `pgrep`s are at 372 and 383._

_**Measured either side, and nothing else moved.** The live parser reads 122 entries and open **23 → 22**, with `SNAG-TEST-004` carrying `fixed_at=2026-09-02`; all **18** registered checks report *still holds*; the suite is **3297 passed, 1 skipped** against a stashed baseline of 3286 collected, so 3285 + 12 with none retired. `ruff check` and `mypy sysadmin` are clean and `check-ops-claims.sh` reports every claim `ok`._

_**It does not close `SNAG-TEST-003`**, whose claim is about the assertion's wording and is unchanged. What moved is its evidence: the one **measured** cause of the red it describes is now gone, so the entry is hypothetical again rather than demonstrated — which makes it weaker, not stronger, and is why it is not the next action._

## Session 151 — the leading step named a remedy that cannot work, and the fix is one field wide

_**`SNAG-SVC-003` is closed and the fix is one field wide.** `_folded_row` took `action` from the anchor, so `alfred-career-mail-timer` led with *"POST /api/sysadmin/services/alfred-career-mail-timer/restart is the deliberate manual step"* — a remedy that re-arms a schedule that was never the problem — while the step reaching the failing job sat three lines below it in the row it had swallowed. `STEP_SUPERSEDES` names the kinds whose step reaches a unit the anchor's cannot, and `timer_failed` is the only one, because its step operates on the **triggered** service. Live either side: the timer leads with `journalctl --user -u alfred-career-mail.service -n 100`, `venture-chat` is unmoved, and the endpoint holds **6 rows and 83 points** both before and after._

_**Rule 4's refusal stands and the owner chose the shape.** Cause-first anchoring was refused in Session 149 for want of a declared cause-to-consequence pairing; the declared supersession set was put to the owner against a full `STEP_ORDER` and against a new contract field, and the title, points, rung, grade and evidence are all still the anchor's — driven field by field, because that was the whole objection._

_**The entry's discriminator was one it did not name.** It scopes the defect to "a timer fault", which points at repairing `_outage_row` whenever the subject is a timer. Two timers carried an `outage` row: `alfred-career-mail-timer`, folded, and `pgbackrest-backup-timer`, whose job had started succeeding the day before and which therefore produced no `timer_failed` row at all. **Both got the identical restart step and only the folded one's was wrong**, because for an armed timer whose unit went inactive the restart is right. The condition that refutes the step is exactly the condition that folds, which is what makes the rule local to `_folded_row`; the subject-keyed implementation is a driven mutation and `pgbackrest-backup-timer` is the only thing in the population that lands it red._

_**The promotion would have dropped the anchor's step**, which is `_folded_row` rule 4 facing the other way: the tray and `health_review` render `title`, `detail` and `action`, and `members` is none of the three. Rule 5 names the superseded step in the `detail` with the finding the leading step belongs to. The consumer half needed its own drive at the **timer** shape, because `venture-chat`'s fold has no superseding member and its projected action is the anchor's either way — `SNAG-SYSD-006` had to land twice for the same reason one entry earlier._

_**The step was run.** `journalctl --user -u alfred-career-mail.service -n 100` returns a SQLAlchemy insert error at 08:20:25 followed by `Failed with result 'exit-code'` — Alfred's to fix and already its SNAG-50; what is verified here is that the leading step now reaches it, where the superseded one would have re-armed a timer that was firing correctly._

_**One of the nine tests was written twice and the first could not have failed.** It drove a lone `timer_failed` row and asserted it kept its own step — true of every implementation, since `recommend` never calls `_folded_row` on a group of one. The discriminating form declares `outage` superseding and reads the **detail**, because `action` comes out identical either way. Nine mutations driven, each red on the right test; two of them exist only because a first pass left two tests unreached._

_**Also done**: `SNAG-SVC-004` filed as the stated residue — the provenance line lives in `detail`, and `health_review._service_facts` projects every other field, so it reads correctly today only by luck of `_timer_failed_row`'s action explaining its own subject. Suite **3285 passed, 1 skipped** against a baseline measured by stashing to HEAD (3276 + 9); ruff and mypy clean; **19 snag checks unmoved** by stash, which matters because this module carries two other entries' instruments. STATUS.md's Testing cell was **27 tests stale** across Sessions 147–149 and is re-measured. `./scripts/check-ops-claims.sh` green on all **nine**. The daemon was restarted twice, at 11:44:51 and 11:51:13. The inbox holds **one** message, `95027c07`, a correction to our own `cc5f26e7` that asks nothing and leaves our conclusion unchanged._

_**Refused a third time, not forgotten**: the pre-staged `started_units` assertion. It is cheap and it is not what the filed action asked for, and this repository's rule is one roadmap session per sitting._

## Session 150 — the filed action was already done, and the board had been told otherwise

### The action Session 150 filed (done by Session 151)

Close `SNAG-SVC-003` — the folded service row leads with the anchor's step, and for a timer fault that step names a restart the swallowed row's own detail explains cannot help — most likely by promoting the better step inside `_folded_row` rather than by moving the anchor, since cause-first anchoring was put to the owner in Session 149 and refused for want of a declared cause-to-consequence pairing this module has not got.

_**The action Session 149 filed was already done before this sitting opened.** Estate message `00b631ec` reads **closed** — closed at **07:11:24 local** by this repository, eighteen minutes after `11f9d33` landed — and its three corrections were sitting **uncommitted** in the working tree. So the handoff line published to the estate board was wrong on both of its claims: not open, and not untouched for three sittings. This sitting verified the work rather than trusting the close note and committed it as `47ae71f`._

_**Verified against the box, not the filing.** `last_audit.checks_run` reads **13** for the 05:35 UTC scheduled run of 2026-09-02. All three live sites read thirteen, and the two that also state the *excluded* count moved to "Eleven" — the excluded count is the total minus the two `JUDGED_AUDIT_CHECKS` admits, so moving only the numeral the message named would have traded a stale figure for a **wrong sum**. Suite **3276 passed, 1 skipped**; ruff and mypy clean; **19 snag checks unmoved**; schema at head `018`._

_**The inbox is empty for the first time in four sittings** — `b0d602e1`, `68ff9116` and `c3228a22` all closed with notes naming the artefact each verdict was read from, so a later sitting can re-derive them rather than trust them. Nothing was owed by any of the three. `sysadmin-review` was checked and is genuinely no-swap (`service/profiles.yaml` declares `{stop: [], start: []}`), so `started_units` is `()` here on every grant; our env already imports the new `Lease` from their `lib/` and `dataclasses.fields` reads the added field today._

_**One correction was filed back, and finding it needed the source rather than the wire.** `68ff9116` reassures us that `active_lease` "selects five columns explicitly … so the payload you judge is byte-identical". It does not: `arbiter.py:223` is `SELECT * FROM gpu_leases WHERE state='granted'`, `arbiter.py:174` assigns that row through unchanged, `api.py:55` `_public` is a datetime-serialising comprehension over `row.items()` that drops no key, the route carries no `response_model`, and `schema.sql:20` declares `started_units text[] NOT NULL DEFAULT '{}'` — the same `SELECT *` through `_public` path the same message correctly describes for `/api/queue/leases/{id}`. **`active_lease` reads `null` live and always has**, so the served payload cannot witness its own key set; the memory note *a field is per route, not per table* is what sent the reading to the handler. Filed as message `5c3258a4`._

_**It costs nothing here, which is why it was filed rather than fixed.** `judgements.py:1675` carries `active_lease` into `details` verbatim and parses none of it, nothing in this tree pins the key set, and `snag_claims.QUEUE_LEASE_STAMPS` names only `granted_at` and `hold_deadline` with a docstring already saying an unpublished field is an absence it reports rather than a `KeyError`. **Residue, deliberately not built**: nothing here asserts that `active_lease` gains `started_units` on the next grant, and a pre-staged assertion would be this repository's idiom for cross-repo work it cannot trigger — offered as a candidate and refused a sitting, not forgotten._

## Session 149 — one fault occupies one row, and the entry had measured half its population

_**`SNAG-SYSD-006` is fixed, deployed and verified live.** `group_faults` and `_folded_row` in `service_recommendations.py` fold a service's `EVENT_ARGUED` findings into one row that names every finding it swallows — `log_actions.group_incidents`' treatment applied at a relation with no clock and no systemd graph in it, and deliberately **not** imported from it. `GET /api/services/actions` went **8 rows → 6**; `alfred-career-mail-timer` occupies one row carrying both findings, and `total_recoverable_points` reads **78 before and 78 after** — the invariant that decided the arithmetic, since an anchor keeping only its own share would have taken the same box to 53 on the day the list got easier to read._

_**The entry had measured half of its own population.** It scopes the defect to timers; `venture-chat` has served `outage` at 26 points beside `flapping` at 25 since the endpoint shipped on 2026-08-25 — eight days, one service named twice, no timer in it anywhere. Reading the entry finds one instance; running the endpoint finds two. So the fold keys on the service plus `EVENT_ARGUED` rather than on the timer collision._

_**Two controls belonging to `SNAG-SVC-001` decided the design, and one of them nearly decided it wrongly.** That check finds its row with a **top-level** scan for `kind == "check_interval"` and its synthetic subject produces exactly `flapping` + `check_interval`, so the obvious "one row per service" would have made it `None` and reported a live entry refuted. Its third limb reads this module's **import set**, so reaching for `group_incidents` by importing it would have refuted the same entry from the other side. All 18 snag checks were driven before and after by stash and report `still holds`, unmoved._

_**The fix had to land twice.** `health_review._service_facts` projects the anchor's `title` and `action` into the weekly review, so the first version named one finding and never said the other existed — the roll-up that cannot name anything, rebuilt one consumer downstream of the fold that promised not to. `stands_for` carries the swallowed titles through, and the generated review now reads *"Also stands for: alfred-career-mail-timer: last scheduled run reported 'exit-code'."*_

_**Two of eleven falsifications passed against deliberately broken code and both were repaired.** Anchoring by points instead of `KIND_ORDER` broke nothing, because the live specimen cannot discriminate the rule — `outage` leads `KIND_ORDER` *and* carries all 6 of career-mail's points — so a subject with 1 point of downtime against 25 of instability had to be added before the anchor rule was tested at all. And emptying the review projection's `stands_for` passed cleanly, because the digest test injected the field into a fixture and pinned the renderer rather than the projection that fills it._

_**Two of the six rules are vacuous in opposite directions and both say so.** Loudest-rung-wins is implemented and cannot currently lose (`outage` is the only `risk`-capable kind and is `KIND_ORDER`'s first), so a test pins the coincidence the proof rests on; gate-before-fold is **unobservable**, driven both ways to identical output, so its test pins the disjointness that makes it vacuous rather than an ordering nothing could distinguish._

_**Also done**: `SNAG-SVC-003` filed as the stated residue — the folded row leads with the anchor's step, and for a timer fault that step names a restart the swallowed row's own detail explains cannot help. `HANDOFF.md` carried **two** `## Next action` headings since Session 148, so `tests/test_handoff_shape.py` had been red on arrival; Session 147's superseded heading is demoted and its duplicated `## Session 147` heading removed. STATUS.md's alert claims re-counted **5 → 3** — a *fall*, `SNAG-ESTATE-008`'s founding case — both departures `info` rows whose subject went away. `./scripts/check-ops-claims.sh` green on all eight. The daemon was restarted twice, at 06:41:37 and 06:46:10. **Four** inbox messages are open and untouched, two of them new today (`b0d602e1`, `68ff9116`)._

## Session 148 — the prediction landed and the instrument had a hole

### The action Session 148 filed (done by Session 149)

Design the roll-up that lets one fault occupy one row in `GET /api/services/actions` — `log_actions.group_incidents`' treatment applied to `KIND_ORDER`, where the swallowed row is **named** rather than dropped — because `SNAG-SYSD-006` is now confirmed by measurement and its cheap fix (suppressing the `outage` row for timers) is ruled out by the control that repaired itself.

_**`SNAG-SYSD-006` is confirmed and stays open.** The prediction Session 147 filed with a dated re-read as its instrument came true on schedule: `GET /api/services/actions` serves `alfred-career-mail-timer` **twice** — `outage` at 5 recoverable points beside `timer_failed` at 0 — off **101** `critical` checks in **1,988** measured, standing unbroken from **21:08:21 on 2026-09-01**, the first poll under `SNAG-SYSD-005`'s fix. At 21:08 there was one such check and downtime rounded to zero, which is exactly the arithmetic the entry named._

_**`pgbackrest-backup-timer` became a control nobody designed.** Repaired and auto-resolved at 22:33:29, it serves **one** row — and the survivor is the `outage` one (1 point, 17 failed checks), not `timer_failed`, because `_timer_rows` gates on the latest observation while `_service_rows` argues from the series. That is the entry's own argument against the cheap fix, demonstrated instead of asserted._

_**The instrument had a hole and only the split population exposed it.** Its refutation limb read "one row for both refutes it", and a repaired timer serves one row without refuting anything — so had the career-mail unit also been fixed, this re-read would have reported the entry dead over a live defect. The discriminating condition is a timer whose job is failing **at the moment of the read**. Recorded in the entry rather than quietly corrected._

_**No code changed.** STATUS.md's alert claims were re-counted: the block said 2 unresolved rows and the checker read 5, all three additions `info` and quietened by design (the arbitrated nightly swap, an estate idle nudge, a transient dev-server port holder), so the rise is the quietening families working rather than three new faults. `./scripts/check-ops-claims.sh` is green on all eight claims. The inbox messages `00b631ec` (check-count, 2026-08-31) and `c3228a22` (by-name project routes, 2026-09-01) are **both still open and untouched**, `00b631ec` for the third sitting running._

## Session 147 — the timer was armed and the job was dead

### The action Session 147 filed (answered by Session 148)

Decide whether `SNAG-SYSD-006` is real by re-reading `GET /api/services/actions` on or after 2026-09-02 and counting the rows for `alfred-career-mail-timer`: two rows (`outage` beside `timer_failed`) confirms the prediction that a failed job is now scored as a service and read as a timer, one row refutes it and the entry retires, and the population is down to that single service because the pgbackrest half was repaired and auto-resolved at 22:33:29 on 2026-09-01.

_`SNAG-SYSD-005` is fixed, deployed and **demonstrated end to end**: `pgbackrest-backup-timer` was raised `critical` at 21:08 off a fault standing since March, the owner repaired both units at 22:19–22:29, the backup ran in 16.4 s, and `_resolve_recovered` closed the row unaided at **22:33:29** on the first healthy poll — detect, alert, fix, observe, resolve, in 85 minutes. `alfred-career-mail-timer` stays `critical` and is Alfred's to close._

_Two estate messages filed at the owner's direction: **`e5d17a89`** to `alfred` (SNAG-50's *"nothing surfaces this"* was our blindness, not their missing surface; no action requested of them) and **`aacd7e33`** to `estate-manager` (the backup, routed there under the shared-infrastructure rule because `pg1-path=/var/lib/postgres/data` is the whole cluster while the stanza is merely *named* `alfred` — the message says so and invites reassignment). The register normalises names: `sysadmin_assistant` is stored as `sysadmin-assistant`, `Alfred` as `alfred`, with both spellings kept. The inbox message `00b631ec` (check-count, filed 2026-08-31) is **still open and still untouched**, for the second sitting running._

**Found by reading another repository's snag, which is the part worth
carrying.** Alfred's SNAG-50 says `alfred-career-mail.service` has failed
every morning for 20 days and *"nothing surfaces this"*. The unit **is**
declared in this repository's `services.yaml` as `kind: timer`, and this
monitor wrote **3,988 unbroken `ok` rows** across the outage. So the
finding was never Alfred's missing surface; it was ours reporting health.

**The mechanism, and the docstring asserted its opposite.**
`_check_systemd` queried `svc.systemd_unit`, which for `kind: timer` is
the `.timer`, and an armed timer is `active (waiting)` whatever its job
did. Worse than blind: `_timer_facts` mapped the **timer's** `Result` to
a field called `last_result`, so every one of those rows carried a
positive claim that the last run succeeded. The docstring read *"the
properties say which"* — they do not, and had not since the check was
written.

**Three layers, each sufficient alone**, and the third is the one that
explains the eight weeks. `service_recommendations._timer_failed_row`
(Session 78) exists precisely for this fault, states the mechanism
correctly in its own `detail`, and gates on `latest.last_result` — so its
population was **structurally empty**. Its drive built a *synthetic*
subject, which is why nobody noticed.

**The discriminating measurement.** `Result=success` on **10 of 10**
declared timers; one of the ten triggered services at `exit-code`. The
field the check read is constant over the whole population; the field it
did not read separates exactly the broken one.

**What shipped.** `get_unit_status` requests `Unit` and `ExecMainStatus`
(same subprocess, ~4 ms, measured). `_triggered_status` resolves the
started unit from systemd's own `Unit=` rather than rewriting `.timer` to
`.service` — systemd does not require the two to correspond, and the
rewrite was a second statement of a published fact, which
`_timer_failed_row`'s own `action` string was also doing.
`_timer_facts` takes `last_result`, `triggered_active_state` and
`triggered_exit_status` from that unit and records `triggered_unit`
beside them. `last_result` was **redefined in place** rather than
renamed, and the blast radius was measured first: the only reader is
`_timer_rows`, which reads `points[-1]`, so contamination from stored
rows is bounded to one poll interval and is dead within 300 s.

**An unreadable triggered unit is `error`, never `ok`** —
`ports_checked`'s rule, and `error` raises no alert and leaves the
reliability rates alone, which is SNAG-SYSD-001's decision for an
unqueryable unit. Reporting clean would rebuild the founding defect one
level down. A timer publishing no `Unit=` is a distinct reason and says
so in `triggered_error`.

**The stand-ins were the work.** Three existing tests patched
`get_unit_status` with one dict for every call, so the second question
was answered with the first unit's facts — the defect wearing a mock's
clothes — and they were green for the life of the bug. `two_units()`
dispatches on unit name. Five mutations driven, each red on the right
tests: pre-fix `Result` sourcing (4 red), `ok` on an unreadable job (2),
never consulting `last_result` (2), suffix-rewriting the unit (3),
dropping `Unit` from the request (1).

**The backup's real state is a half-state, and only `pg_stat_archiver`
says so.** WAL archiving *works* — `archived_count=5356, failed_count=0`,
last push minutes ago — so the repo grows, nothing errors, and there is
no base backup for any of it to restore onto; `repo1-retention-full=4`
expires during a backup, so it cannot shrink either. One authoring error
has **three instances across two files**, found by `systemd-analyze
verify` rather than by reading: `ExecStart=` loses `backup`,
`Description=` loses `Alfred`, and the **timer**'s `OnCalendar=*-*-*`
loses `02:00:00`, so a backup written to run off-peak at 02:00 has been
firing at **midnight**. Corrected in-sitting: the `pgbackrest.conf`
placeholder comment was read as a second defect and is cosmetic.

**Deployed, and the first live run raised two criticals rather than
one.** `pgbackrest-backup.service` — which `services.yaml`'s own comment
calls *the only database backup on the box* — has failed **28 times and
succeeded zero times since 2026-08-02**, under 4,697 `ok` rows. Its unit
file breaks `ExecStart=` across two lines with no trailing backslash, so
`/usr/bin/pgbackrest --stanza=alfred` runs with no command and exits 30,
`ERROR: [030]: no command found`. A fix that widens what a monitor can
see is a regression surface for whatever reads it — the fourth time this
repository has recorded that ordering, and the first time the widening
found something worse than what it was aimed at.

**The sitting's own claim was overstated twice and the fix refuted
both, which is the part to carry.** The estate message said *zero base
backups* and *nothing to restore onto*; the successful run printed
`last backup label = 20260307-141905F`. The repository held a full taken
**by hand** on 2026-03-07 at 14:19:05 — three minutes before the timer
was enabled and three and a half before the broken unit was written — so
recovery was possible throughout, to a 178-day-old base plus ~5,356 WAL
segments of replay. The error was inferring the *store's* contents from
the *caller's* failure count, because `/var/lib/pgbackrest` needs root:
`ports_checked`'s rule turned around and pointed at this repository.
Corrected at estate-manager as `cc5f26e7` rather than edited quietly.

**Left open, deliberately.** `SNAG-SYSD-006`: a failed job is now scored
as an outage *and* read as a timer, so one fault will produce two advice
rows once downtime rounds above zero. Filed as a **timed prediction, not
a measurement** — at 21:08 the endpoint served exactly two rows, both
`timer_failed`, and the entry names the date to re-read and what would
refute it. Not fixed here because the cheap fix (drop the `outage` row
for timers) deletes the only figure that ranks the two live findings
against each other.


## Scheduled action

_Dated work that is not the next thing to pick up. It lives here rather
than under "Next action" so a week-out measurement cannot stall the
pipeline, and so it is not lost by being the thing a sitting scrolled
past. **Nothing enforces this section** — it is read by whoever opens the
handoff and printed by `./scripts/claude-preflight.sh`, which flags an
item as due, overdue or *n* days out against today. Deliberately not
machine-read: a scheduled item published to the estate board would
compete with the next action for the same slot, which is the second shape
rule below happening on purpose._

_Two shape rules, both about the readers this file already has.
**Plain bullets, never `- [ ]`**: estate-manager's `roadmap.py` falls
back to `first_unchecked_task()` when a handoff has no "next" heading, so
a checkbox here would publish a week-out measurement to the estate board
as this repository's next action the day somebody deleted that section.
**No heading containing the word "next"**: `next_action_from_handoff`
returns the first meaningful line under the first such heading, so
"Scheduled action" is deliberately not "Next up" or "Coming next".
Verified by driving their parser either side of this edit — the published
line is unchanged — and guarded by `tests/test_handoff_shape.py`.
Announced to estate-manager as message `8e693e05` before the commit that
carried it, with the estate-wide convention offered as a recommendation
for them to rule on._

- **2026-09-07** — Read the first Monday under lease: `llm_used` on `health_reviews`, `log_reviews` and `disk_reviews` should be true, true, true, and `journalctl --user -u estate-manager-api.service` should show four grants after the drain releases in the order health, log, estate-review, disk — and if any row is still false, read the `review_lease_*` warning beside it, because the three refusals are logged apart precisely so that reading answers why.

## Session 146 is complete — the first night under the fix, and the check could not close its own entry

**`SNAG-AGENT-011` is closed.** The nightly `venture-chat unreachable`
row opened **2026-09-01 00:01:16** at `info` — not `critical` — resolved
at **05:51:19**, and carries `details['arbitration']` =
`{unit: venture-chat.service, profile: venture-nightly-24b,
reading: granted, lease_id: 48, stopped_by_estate: true}`. With
`tray.notify_min_severity` at `warning`, the persistent nightly toast
the entry was filed for no longer reaches a screen, while the row still
exists, still resolves and still reaches `GET /api/services/reliability`
— a quietening, which is the fix the entry asked for, and not a
suppression, which is what it forbade.

**The deploy question was answered before the data question, and the two
timestamps invert.** The fix's commit landed 09:44:50 and the daemon
started **09:36:14**, 8m36s *earlier*, because this repository restarts
to verify and commits afterwards. That is exactly why `ops_claims` rule
4 compares file mtimes rather than commit times; reading commit times
would have said a restart was owed and the night would have been
discarded as not-under-the-fix.

**The check reports `mismatch` and its reason is the wrong limb, which
is the conjunction working rather than failing.** `if readers:` returns
before any limb-1 branch can run, so the headline has said *"a reader of
`stopped_units` exists"* since the commit — a short-circuit gate hiding
what is behind it. Limb 1's verdict was taken by neutralising the outer
gate (`patch.object(snag_claims, "lease_discriminator_readers",
lambda: [])`), with the stand-in confirmed to move the output before its
verdict was believed, and it refutes by the third of three branches:
*the nightly row is still raised and is no longer critical*.

**The three readings the check says it cannot separate were separated by
hand.** A quiet population would equally follow from `mute_services`
gaining the service, from the estate retiring the swap, or from the
profile losing `stopped_units`. Live: `mute_services` is `[]`; the three
post-deploy rows each name a real granted lease; `stopped_by_estate` is
`true` on all three. So the population did not go quiet, and only the
rung moved — the one outcome that closes this entry rather than merely
emptying it.

**The check retired and the detector did not**, the sixth time this
repository has spent `FROZEN_TABLES`' rule.
`TestTheDeployedQuieteningLive` in `tests/test_arbitrated_stops_live.py`
reads the live `alerts` table and is stronger than the limb it replaces
in a **named** axis: limb 1 rebuilt its window from
`venture-enrich-nightly.timer`, which keys this repository's guard on
another project's schedule, and that timer moved 02:00 → 00:00 on
2026-08-25. The re-homed tests read `details['arbitration']`, the blob
the fix writes, so they hold at whatever hour the drain fires and would
witness the estate swapping a unit nobody has thought of yet. A live
read is needed at all because a recorded test cannot tell a fix that
works from one that has never executed — `_still_open` carried that
shape from Session 55 to Session 115 without running once on this box.

**Its anti-vacuity pin is the load-bearing half.** Driven at five
stand-ins: a pre-fix world with no blob reddens **only**
`test_the_deployed_path_has_annotated_at_least_one_row`, while the two
behavioural tests *skip* — so without the pin a box that never deployed
the fix reads green, which is `a-check-needs-a-discriminating-witness`
arriving inside the guard written for it. The other four cases redden
exactly one test each and nothing else, including the over-quietening
direction, where the **absence** of a quietening on an `unread` row is
what is asserted, because suppression is how a fix of this shape fails.

**An adjacent observation, recorded rather than filed.** The unresolved
count read 1 → 2 → 1 inside this sitting, which is exactly what Session
144 measured two days earlier and from the same source: `High VRAM usage
on AMD Radeon RX 7900 XTX` opened and resolved **5** times on 2026-09-01
between 16:06 and 20:31. It is not a snag — the row is correct each time
and `_resolve_recovered` closes it each time — but it means the block's
alert figure is only stable between GPU bursts, so the **steady** value
is what belongs in it and a sitting re-measuring mid-burst should not
"correct" the block. That is the falling direction `check_alerts` exists
to notice, arriving as a false alarm rather than as a stale claim.

**What was deliberately not done.** `SNAG-AGENT-012` and
`SNAG-AGENT-013` were filed by Session 145 with measured-zero
populations precisely so that a later sitting would not build them off
this closure, and the previous handoff said so by name; neither was
touched. The one open estate message (`00b631ec`, the audit's check
count) is left open for the next sitting rather than closed unactioned.

**Numbers.** 3264 − 19 retired + 4 added = **3249** = 3248 passed + 1
skipped, so the arithmetic witnesses that no file was clobbered.
`sysadmin-check-snags` reports no `no` verdicts and *-1 open since
9f73627*; `check-ops-claims.sh` is clean apart from the documented mtime
false positive — `snag_claims.py` was edited and `sysadmin.main` does
not import it, verified rather than asserted, so **no restart is owed**.
The register is 18 checks over 22 open entries, 18 of them checked.

## Session 145 is complete — the arbitrated stop is quiet, and the placement question was three questions

**`SNAG-AGENT-011`'s decided fix is built, deployed and verified live —
and the entry is still open on purpose.** Its check is a conjunction:
limb 2 (a source walk) flipped on this commit, limb 1 (the nightly
population) cannot flip until a night has passed under the deployed code.
The entry said so in advance and this sitting obeyed it rather than
closing on its own evidence.

**What shipped.** `read_arbitrated_stops` in `sysadmin/estate/client.py`
takes the two-call path: `active_lease.id` from
`GET :8400/api/queue/invariants`, then `stopped_units` from
`GET :8400/api/queue/leases/{id}`. `SysAdminAgent._handle_status`
quietens a unit the estate names to `ARBITRATED_STOP_SEVERITY` and
records `details['arbitration']` on **every** row of the family, not only
the quiet one.

**The placement question decomposed into three ownerships rather than
one, which is the thing worth carrying.** Transport belongs to
`estate/client.py` because it already owns every HTTP call to 8400; the
verdict belongs to `monitor/agent.py`, which also holds the
`services.yaml`-to-unit identity; and the *rung* belongs to neither
domain's judge, so it is derived from `core.escalation.QUIETEST_SEVERITY`
rather than imported from `judgements.TRANSIENT_HOLDER_SEVERITY` as the
handoff line proposed. Taking the judge's constant would have been the
right value from the wrong place — and the two are now asserted apart, a
pin for the value and an import guard for the provenance, which is the
distinction this repository has recorded itself failing to make three
times.

**Consulting `tests/test_import_boundary.py`, as the handoff asked, found
a gap older than the sitting**: `sysadmin.estate` was missing from the
domains `core` may not import. Nothing had breached it, so a guard was
added rather than a breach fixed.

**Two of the entry's own claims were refuted by measuring rather than
reading.** Its cost figure was taken off post-dedup rows, but
`_raise_judged` runs every poll and suppresses the *row*, not the call —
so the read is memoised per run and made **outside** the per-service
savepoint, two HTTP hops inside `begin_nested()` on a host with
`idle_in_transaction_session_timeout=1min` being `SNAG-AGENT-003` rebuilt
inside somebody else's fix. And the fix lands on machinery Session 117
wired for a population it believed was *"empty by construction"*;
`% unreachable` now carries two rungs under one title, so that docstring
is corrected rather than left to rot.

**Two costs filed, both with zero populations and both deliberately not
built.** `SNAG-AGENT-012` — the quietening is one-directional, so a fault
that begins under a lease and outlives it keeps the quiet rung; measured
at **0 open rows across 30,716 in the whole `% unreachable` family**, and
announced by an `alert_rung_left_stale` log line rather than left silent.
`SNAG-AGENT-013` — auto-restart does not consult the arbiter and would
fight it; 0 of 31 services enable it.

**Verified live, and it ships untriggered.** A real granted lease (its
`stopped_units` served by the real 8400) gives `info` naming the lease;
an unread estate gives `critical`; a standing `critical` row is quietened
**in place**, same row id, `created_at` unmoved, nothing raised and
nothing resolved; the reverse transition is refused and logged. **0 rows
of residue.** Nothing was unreachable at deploy time, so the deployed
path has not yet fired on its own — which is precisely what tomorrow
morning's read is for.

**One process note worth keeping.** A mutation restore was masked by the
bytecode cache: `stopped_units` → `units_stopped` is a **same-length**
rename, so the repaired tree went on failing until `__pycache__` was
cleared, and for several minutes that read as a live producer fault. The
fourteen kills are unaffected — a stale cache can hide a restore and can
never manufacture a red — but the minutes spent chasing the estate's
lease table were real.

## Session 144 is complete — the founding measurement died, and its death was the design working

**Both inbox messages are closed and neither needed the code changed.**
`76e0438b` asked for one line in `services.yaml`; `218d765a` asked for
nothing and was verified rather than believed.

**What shipped.** `estate-manager-api`'s log block gains `format: json`.
The estate's four entry points began emitting one JSON document per
record on 2026-08-31 (their ADR-0079), and without the declaration
`alert_title` builds the title out of the whole document — `SNAG-LOG-003`,
the defect the `sysadmin-service` entry twelve rows up already declares
against. Driven against the unit's real journal, paired record by record
with `logged_at` asserted as the premise: **166 of 600 records change**,
titles fall from **167–249 characters of JSON to 55–70 readable ones**,
`logger` goes to metadata and `raw_line` keeps the envelope. The other
**434** — uvicorn's access lines and systemd's own — pass through
untouched, which is `unwrap_json_message` failing open, not a shortfall.

**It ships untriggered, twice over, and the second reason is the one
worth carrying.** `FAULT_SEVERITIES` is `error` and `critical`, so the
`warning` filter's entire live population for this unit is systemd's own
28 stored `Failed with result 'exit-code'.` rows, which raise no alert
and are plain text anyway. And **no estate application line has yet
arrived above priority 6** — all 34 non-6 records in 14 days were written
by systemd — so the producer's new `<N>` prefix has no witness here
either. The declaration is a statement about what the application writes,
not a repair of an observed row. Verified in our own table: **0** stored
messages for that unit are JSON-shaped.

**The interesting half was a guard, and its claim was the design's
founding measurement.** `test_no_other_source_declares_a_format` asserted
`{"sysadmin-service"}` and read *"this daemon is the only JSON-writing
journal source on this box, which is the whole reason the fix went to a
per-source declaration rather than into the reader"*. That observation is
now false — **and its falsification is the design's vindication, not its
refutation.** A reader that had sniffed a leading `{` would now carry a
special case keyed on *two* applications' log formats; the per-source
declaration absorbed the second producer in one line of YAML and no code
at all. The guard is widened, not deleted: a third name appearing without
a measurement behind it still turns it red.

**The same dying claim was stated in a second file, and it had taken a
premise hostage.** `test_message_backfill_live.py`'s
`TestThePremises` asserted `declared == (PROBE_UNIT,)`, which stated the
anti-vacuity premise *and*, incidentally, the only-one-source fact. The
premise is **membership** — if the probe unit is undeclared the scan
cannot see the probe rows — and never depended on the rest of the estate.
Relaxed to `in`, and falsified by undeclaring the probe unit, where it
still goes red for its own reason.

**The two declarations are not equally well supported, and that asymmetry
earned a live witness.** This daemon's is pinned against
`service.log_format`, a fact this repository owns. The estate's cannot
be — a repository may not import another's config — and
`unwrap_json_message` **fails open**, so an estate rollback to plain text
would leave every record untouched, every test green and `services.yaml`
carrying a false statement about another repository indefinitely. This
repository has settled that shape once already, in the queue wait-gauge
fix: *a graceful degradation with no separate alarm degrades unnoticed*,
and the only place it can be loud is the live half.
`test_a_declared_source_really_writes_json` reads the raw `MESSAGE`
rather than going through `read_journal`, which would already have
unwrapped it and so could only agree with itself. Falsified by declaring
`format: json` on `estate-broker-provision`: **red at 13 records read and
0 JSON-shaped**, with the premise intact — which independently confirms
the estate's own measurement that the broker provisioner is a
`print()`-based script.

**The declaration widens a population nobody mentioned, and it was driven
rather than reasoned about.** `plan_backfill`'s candidate set is the
sources declaring `json` *today*, so it goes **256 → 284 rows scanned**.
The 28 added are systemd's plain-text lines, which fail open, so
`frozen`, `unwitnessed` and `unrecoverable` are all **0**.

**`218d765a` is a no-op and was verified as a differential, not a count.**
Their `dormant` marker must now be last in the Role cell. Our
`parse_port_registry` was run against their document either side of
`2b63122`: **19 rows both sides, ports identical and in order, projects
identical**. Three Role cells changed *text*, which their message did not
mention, so the last gap was closed by asking who consumes `role` —
exactly one caller, the `duplicate_claim` finding's detail blob — and
there are **no duplicate-claimed ports**, so the reworded cells reach
nothing.

**Deployed as a reload, not a restart.** `configuration_reloaded` reports
`changed: ["estate-manager-api"]`, `requires_restart: []`,
`jobs_synced: true`. The deploy check's "restart owed" is a **false
positive** and was checked rather than obeyed: it names
`sysadmin/snag_claims.py`, whose mtime moved with no content change
(`git diff HEAD` empty) — the documented failure direction of an
mtime comparison.

**Suite 3230**, measured by running rather than read off STATUS.md:
baseline **3228** at `263c160` plus the **2** added, so the arithmetic
witnesses no clobber. Ruff and mypy clean. Note the cell said **3209**
against a measured 3228 — stale by 19 from earlier sittings, this table's
own recurring defect, and corrected here.

**A parallel session was in this tree throughout, and it changed one of
this sitting's conclusions.** `sysadmin-assistant-fa` committed `9efef79`
to `tests/test_notify_guard_live.py` — and to nothing else, deliberately
leaving every document alone because these edits were mid-sitting. Its
subject: `test_notify_send_returns_at_once_on_the_live_bus` fires the
announcer's **real** `notify-send` at the live session bus with the
announcer's own flags, and `--expire-time=0` is *never expire* per the
freedesktop spec while `--urgency=critical` is never auto-dismissed by
Plasma either — so **every full suite run since 2026-08-29 parked one
more permanent toast** reading "SNAG-SYSD-004 probe" on the owner's
screen, reported as spam. The fix keeps the control intact rather than
weakening it: `--print-id` goes into `_notify_send` so **both** halves
stay flag-uniform (the pair must differ in exactly one thing — whether a
server owns the name — and `--expire-time=0` is the flag that docstring
names as the suspect cleared only by measurement, so it is the one that
must not vary), and the live half then calls `CloseNotification` on the
id. Softening the flags and dropping the live call were both refused in
writing. **The new assertion's limit is stated rather than implied**:
measured against Plasma 6.7.4, `CloseNotification` answers `rc=0` for an
id never issued (999999) and emits `NotificationClosed` reason 3, so
`assert closed` is evidence the call was made and answered and **not**
that a toast left the screen.

**That commit refuted this sitting's own snag, and then the peer refuted
the replacement, and the third answer was driven with a control.** The
sequence is the value here, so it is recorded rather than tidied.

The entry was filed blaming **load**. `9efef79` refuted that: a peer
session was running the same suite against the **shared** session bus
while its own never-expiring toasts accumulated. This sitting then
attributed **both** reds to that — and the peer pointed out that red 2
(`…does_not_return_on_a_bus_with_nothing_listening`) never opens the
shared bus at all, so the replacement mechanism structurally cannot reach
it. **The same one-fixture-two-tests error, made while correcting the
first instance of it.** They also had a candidate and eliminated it by
measurement: one unscoped `pkill` at a blocked `notify-send` leaves it
blocked, because the bus re-activates the waiter mid-call, PID-tracked.

**That elimination is correct and does not generalise, which is the
finding.** Driven here with a control: 0 kills and 1 kill both block the
full **8.01 s** at `rc=124` — reproducing the peer's result exactly — and
**three** kills, at 1.0 s and again at 1.5 s spacing, make the call
**return** at 3.88 s and 5.38 s with `rc=1` and `Error calling
StartServiceByName … Process org.freedesktop.Notifications exited with
status 255`. Two kills 0.4 s apart do not. So the bus re-activates after
one kill and stops after about three, erroring the pending call — which
is exactly `assert not returned` failing. **Four** tests take the
fixture — AST-pinned at lines 279/331/338/349, because the peer flagged
the figure as grep-fragile (a `def`-line grep returns **2**, two
signatures being multi-line) and 4 against a threshold of 3 is the whole
argument — so an ordinary file run fires four unscoped kills. Four is a
**floor**, not a best case: a body-level `pytest.skip` runs after fixture
setup, so its teardown still fires, verified with a two-test probe. That
is why red 2 needed no load: it was a *file-alone* run beside a peer
running the same file. The entry had twice said "two full-suite runs"; that is
corrected too.

So the entry **split by remedy**. `SNAG-TEST-003` keeps the half no
mechanism touches — the assertion's own text says a red means the hazard
is **gone**, so a flake there reads as good news and invites relaxing the
control, and `SNAG-TEST-004` now supplies a *measured* red that would
have said exactly that on a box where the hazard is intact.
`SNAG-TEST-004` is the cause: two operations escape the fixture's own bus
— the teardown's global `pkill` and a global `pgrep -c` in
`test_asking_does_not_start_the_waiter_that_calling_starts` (the second
reported by the peer, code-confirmed here and **not** driven, and
labelled so). Its remedy is **scoping**, not the differential the first
version named: bound both to the fixture's own `dbus-daemon`, whose child
the waiter is.

## Session 143 — `SNAG-AGENT-011`'s check, and a fix that cannot be written as filed (2026-08-31)

**What was asked**: write the check, then decide the fix. Both done; the
fix is decided and **not built** — the placement question was explicitly
deferred to the build sitting by the owner.

**The check.** `check_nightly_hold_is_loud`, the twenty-seventh in
`CHECKS`, taking the register to **19 of 19 open entries checked**. A
conjunction whose halves refute at different moments *on purpose*: limb 2
(an AST walk for `stopped_units` under `sysadmin/`, both the dict-key and
the attribute spelling) flips on the **commit**; limb 1 (the nightly
population off `alerts`) flips the first night after the **deploy**.
Neither is redundant — a source walk alone reports the entry dead over a
fix nobody restarted into, and a population read alone is blind to a fix
landing in `mute_services` or to the estate retiring the swap. Live:
`match`, 6 nightly rows in 30 days across 1 service, latest 2026-08-31 at
`critical`, no reader of the discriminator.

**Three things the sitting found by reading the producer rather than the
entry, and they change what gets built.**

- **`GET :8400/api/queue/invariants` does not publish `stopped_units`.**
  `Arbiter.invariants` selects an explicit column list and pops
  `hold_overdue`, so `active_lease` reaches the wire with five keys;
  their own `test_the_old_gauge_is_unchanged_and_still_published` pins
  that set. The entry's one-call fix — and the handoff line that sent
  this sitting — cannot be written.
- **The lease history *is* reachable, so the entry's other stated limit
  is wrong in the opposite direction.** `GET /api/queue/leases/{id}` is
  `_public(SELECT * …)` and answers for a **released** lease; leases 30,
  31 and 32 all name `["venture-chat.service"]` against grants at
  00:00:03–00:00:05, which are three of the six nightly rows' causes.
  The check deliberately does **not** use it: it would make a report
  printed at both ends of every sitting depend on another service being
  up, and enumerating lease ids is walking a key space the estate
  publishes no listing for.
- **The window is derived, which the owed shape did not ask for.** The
  bullet asked for a *duration and time-of-day* shape — two hand-picked
  numbers. Both halves come off the box instead: the drain's next firing
  from `systemctl --user show … --timestamp=unix`, and the grace from
  `agents.sysadmin.health_check_interval_seconds`. `--timestamp=unix` is
  load-bearing: the default rendering is a local wall clock with a zone
  abbreviation, `SNAG-LOG-009`'s trap, and `@1788217200` carries no zone
  at all. The `OnCalendar` spec is **not** parsed — that would be a
  second implementation of systemd's calendar grammar.

**Two of ten mutations passed against deliberately broken code, and they
were masking each other.** The docstring exclusion is inherited from
`SNAG-SCHED-002`, whose detector was a *substring* search; against an
*equality* match a docstring mentioning the name cannot match anyway, so
removing the exclusion changed nothing. Softening the equality to a
substring also changed nothing — because the docstring exclusion caught
what it let through. The prose specimen gained a **non-docstring**
mention and the exclusion gained a pathological witness of its own, after
which each mutation lands red on its own test. Suite 3209 → 3228, which
is the 19 added and nothing clobbered.

**Decisions taken, and what was rejected.** The two-call path here, over
filing at estate-manager for the field on `invariants`: that filing is
one call rather than two and is arguably the field's right home
(`waiting_reason` arrived by exactly that route after our `d1939cf7`),
but it parks a **nightly** `critical` behind another repository's
sitting, and nightly is why the entry is P2. Reading `gpu_leases` is
estate rule 1 and was never a candidate. The second call's cost was
measured rather than assumed: it fires on the **raise** path only, and
the family raised 23 rows in 17 days.

**Blocked / open.** Placement — the service family must consult a fact
while the estate judge must not acquire a say in a service's rung
(`judgements.py` rule 3 in reverse). `sysadmin/estate/client.py` owns
every HTTP call to 8400, so it is either a cross-domain read from
`SysAdminAgent` or a reader the service family owns outright, and
`tests/test_import_boundary.py` has not been consulted.

**No restart owed.** Nothing the daemon imports reaches `snag_claims.py`;
the deploy check compares file mtimes and cannot tell, which is a cost
its own entry states.


## Session 142 is complete — the reviews park now, and the budget is a deadline rather than a duration

**`SNAG-SCHED-003` and `SNAG-SCHED-001` both closed.** The three weekly
reviews take a GPU lease from the estate's arbiter through
`estate.queue` and wait for the grant. `sysadmin/core/gpu_lease.py` is
the module; `LLMClient.generate` gained `gpu_lease_held`, which is the
**absence** of a gate rather than a third sampler — estate-manager's
`GpuGate.HELD`, spelled as a `bool` because `SUSTAINED` was costed and
refused here in Session 134 and an enum would carry a member nothing can
reach. No slot moved: the entry's own ranking of its two candidate fixes
was right, and the lease is the one that holds wherever the boundary
lands.

**The owner settled the budget and the shape is what makes it work.**
One deadline — `briefing_hour` less `schedules.review_lease_margin_minutes`
(5) — with each review deriving `wait_seconds = deadline − now` at its
own dispatch: **3300, 2400 and 600 s**. Three independent leaves were
offered and refused, because they say the wrong thing about the
mechanism: `Arbiter.tick` returns early while **any** lease is granted
and `_oldest_waiter` orders by `requested_at` across every profile, so
the three reviews are not waiting three lengths — they are waiting for
**one instant**, the holder's release, from three starting points. The
deadline is derived from the briefing rather than written as `"05:55"`,
so a briefing moved to 07:00 carries the budget with it.

**estate-manager corrected the arithmetic and the correction does not
bite, which is the cleanest argument for that shape.**
`Arbiter._drop_overdue_waiters()` runs **first** in every tick, before
the grant, so a waiter past its `wait_deadline` is dropped even if the
card frees a second later — verified in their source rather than taken
from their message. Copying their `REVIEW_WAIT_SECONDS` of 1800 would
drop the 05:00 job at 05:30, fifteen minutes early, and the 05:15 job by
22–72 s, which is the nasty one because it fails by a margin small
enough to read as a fluke. Every deadline-derived budget ends at 05:55,
past the whole recorded release band of 05:45:15 → 05:47:18.

**The blocker was not in the handoff and it was another repository's to
clear.** `POST /api/queue/acquire` answers `404 unknown profile` and
`service/profiles.yaml` is estate-manager's by the estate rule that
shared infrastructure gets an owner that is not an application. Filed as
message **`dcae132c`** with the cost and the FIFO consequence stated
**before** the commit; the code shipped pre-staged behind a test gated on
the profile appearing, so the sitting was never parked. They landed
`sysadmin-review` (`stop: []` / `start: []`) the same sitting and closed
the message. Naming their `estate-review` was considered and refused —
that profile's own comment names their timer and their job — and their
note agreed for the same reason.

**Two things their note added that this repository had not computed.**
Our 05:45 disk review now queues *behind* estate-review, pushed back by
their measured 4.00 s hold plus up to one 5 s tick; and only **two** of
our generations are ahead of them rather than three, so their grant moves
by ~2–22 s rather than the 15–45 s we announced. They accepted it
explicitly and asked us **not** to re-slot behind them.

**Our own queue alert sees ~2700 s waits every Monday now and raises
nothing.** `judge_queue_invariants` has read
`oldest_unexplained_wait_seconds` since Session 139, and `behind_holder`
is masked out of it — so the gauge this fix moves is the one that had
already been taught to expect exactly this. Verified in
`sysadmin/estate/judgements.py` rather than assumed.

**The checks were briefly wrong in the direction this family is named
for, and that is the part worth carrying.** Both read source, and source
cannot see a `404`: the moment `gpu_lease.py` existed they reported
`mismatch` over a Monday that still cost three narratives. That is
`SNAG-SCHED-002`'s false retirement one sitting later and by the
**opposite** route — there the *symptom* was promoted to the remedy, here
the *remedy* would have been promoted before it worked.
`_review_profile_published` made the arbitration limb a conjunction with
the arbiter's own roster, every way of not-knowing returning `None`
rather than `False`, and both checks went back to `match` until the
profile landed an hour later. They retired then, having been correct
throughout.

**Driven live, and the drive caught the fix working at a moment nobody
arranged.** Lease 39 was requested at 06:39:30 with `wait 3300s, hold
600s`; the arbiter logged `lease 39 waits: GPU floor 26% over threshold
25%` and **parked it** — which is the whole entry in one line, because
the old gate raised `GpuBusy` at that same 26 % and served a digest.
`wait_deadline` came back `07:34:30`, the request plus exactly the
derived 3300 s, so the budget reaches the arbiter unchanged. Cancelled
rather than left to hold.

**Writing the live drive found a defect reading the code had not.**
`estate.queue.acquire` defaults `base_url` to its own
`http://127.0.0.1:8400` and this module passed none — a second spelling
of the estate's address inside a process that already reaches :8400
through `agents.estate_judge.base_url`. Right on this box today and free
to drift from the address the judging uses. `arbiter_url()` is the one
reader now.

**Both checks retired and the guard did not** — `FROZEN_TABLES`' rule,
for the eighth time here — and it is **stronger than what it replaces**.
Those checks swept `sysadmin/` for any mention of an arbitrating name,
weak enough that a docstring nearly satisfied one;
`TestTheWaiterlessInvocationTakesALease` asks, per review module, that
the job acquires, passes `gpu_lease_held`, and releases from a `finally`.
The middle assertion is load-bearing: a job that took a lease and let the
flag default to `False` would wait for the card and *then* give up on it,
which is strictly worse than not waiting and green in every behavioural
test, because both paths store a review. `tests/test_gpu_lease_live.py`
holds the other half — that the estate still publishes the profile, since
its removal would degrade every review silently and raise nothing here.

**3196 green** (3180 + 48 − 32, baseline measured by stashing rather than
read off STATUS.md, which was right for the first time in five sittings).
**Thirteen mutations driven and thirteen killed**, each on the intended
tests and none passing against broken code — but one new test is a
**recorded counterfactual rather than a guard and says so**: the
copied-1800 arithmetic is over two constants and no code change can break
it. Daemon restarted at 06:55:16, and **this restart was owed**, breaking
a run of three that were the mtime check's blind spot — `gpu_lease.py` is
imported by all three review entry points.

**Two things found after the lease work and recorded rather than fixed.**
`SNAG-AGENT-011` (P2) — the estate stops `venture-chat.service` under a
lease and this repository announces it as `critical`, standing ~5h45m
nightly, which is the drain's hold to the second; the discriminator is
`active_lease.stopped_units`, live on a surface `sysadmin/estate/client.py`
already reads. Its check is **owed rather than refused** and is the next
action. And `30bfbea` shipped `claude-preflight.sh` **without its execute
bit** — a falsification's Python-written backup was `mv`'d back over it,
and a mode is not content, so the suite, ruff and the pre-commit hook were
green over the one script every sitting starts with. Fixed and swept.

**What is not done.** The observation, and it is one reading — see Next
action. Nothing else was left: the estate's message is closed, both
entries are closed, and no new snag was opened.

## Session 141 is complete — the prediction held, the mechanism came with it, and the headline's ranking did not survive

**The reading `SNAG-SCHED-003` was dated on came back false, false,
false.** `health_reviews` 05:00:03.92, `log_reviews` 05:15:00.06 and
`disk_reviews` 05:45:00.43 all wrote `llm_used=false` on the first Monday
since `venture-enrich-nightly` moved to 00:00. **No code changed this
sitting** — the sitting was the measurement, and the three tracking
documents carry it.

**A false×3 is the prediction, not the mechanism, and the entry says so
itself.** Its quieter half is that nothing on those three surfaces
separates *skipped for contention* from *llama-server was down*, so the
stored flag alone would have licensed the fix on an ambiguity. The
journal is where the two part: each row is preceded by `llm_gpu_busy`
from `sysadmin.core.llm_client` carrying `busy_percent` **99, 97 and 98**
against `threshold: 25`, and followed within milliseconds by its own
`*_llm_unavailable_used_fallback`. `alfred-inference.service` was
`active` throughout with no start, stop or failure in the window, which
refutes the alternative cause rather than assuming it away, and
`venture-enrich-nightly.service` finished **05:46:11** — a sixth
consecutive night inside the recorded band.

**A third witness, independent of the daemon's own gate.**
`resource_snapshots` read over the dGPU — the card taken by
`max(vram_total_mb)`, never by key, which is the entry's own rule — gives
**2 of 2** samples above the gate at 05:00 (mean 100.0), **2 of 2** at
05:15 (99.0) and **1 of 2** at 05:45 (53.5). Three producers agree: the
gate's own reading, the snapshot table, and the drain's journal.

**The estate paid the identical fault the same morning and kept its
narrative.** `estate-manager-review.service` took lease 38, polled it for
**16 m 21 s**, was granted at **05:46:20** — nine seconds after the drain
released — and generated in about a second
(`weekly_project_review_generated`). Same card, same drain, same hour: it
waited and got its narrative while this repository read the card once at
each of three slots and served three digests into the 06:00 briefing. The
two nights the entry cites for them are 08-17 and 08-24, *before* they
changed; this is the first night the two designs have been observed side
by side under one holder. **The lease fix is licensed outright.**

**The claim that was refuted is ours, and the error is the instrument
rather than the slot.** The entry's headline says *two of the three*
reviews are worse off and ranks disk least affected at **5 of 12,
42.5 %** over a ±300 s window. `ensure_gpu_idle` reads at the **dispatch
instant**, which was 05:45:00.43 — **71 seconds** before the release — so
disk lost too and all three narratives went. A ±300 s mean straddles the
release and reports as half-clear a slot that was fully occupied when it
was actually sampled. The priority does not move: P2 was argued from
three narratives every Monday, never from which of them is worst.

**The check reproduces the refuted ranking and is still correctly
green.** Driven after the observation it reads `disk_review 6/14 busy`
and names `generating into a held card: health_review, log_review`, by
the same majority rule that produced the 5 of 12. The conjunction holds
through health and log, so the verdict is `match` and the entry stays
green for the right reason; what is wrong is the evidence sentence beside
the verdict. Left as measured rather than re-instrumented here, because
moving the sample to the dispatch instant changes the check's witness and
belongs with the fix. It did supply one cross-check on the way out: its
**6/14** is the previous **5/12** plus **1 busy of 2 new samples**, which
is independently what `resource_snapshots` gives for the 05:45 slot
today.

**What the next sitting must settle before writing code.** The estate
waits up to a single `REVIEW_WAIT_SECONDS` of 1800 against no downstream
boundary of its own. This chain has one: the 06:00 briefing publishes
what these three reviews write, and the slots sit 60, 45 and 15 minutes
ahead of it. One shared budget is therefore wrong for at least one of the
three, so the choice is between a per-review budget derived from each
slot's distance to 06:00 and a re-slotting that lets one budget serve all
three. That is a decision, not a number to invent — `queue_max_wait_seconds`
is already this repository's one **invented** threshold and says so, and a
second one would be the same debt at the surface the briefing publishes.

**Both checks are green and the tree is otherwise untouched.**
`./scripts/check-snag-claims.sh` exits 0 with 20 of 20 open entries
checked, `./scripts/check-ops-claims.sh` exits 0 on all nine claims, and
no `<!--check:-->` marker was disarmed — backtick parity was verified on
the amended regions of both `STATUS.md` and `snag_list.md`, which is the
failure mode that silently retires every marker after it.

## Session 140 is complete — the measurement named the wrong contender, and the box had already recorded the right one

**`SNAG-SCHED-001` owed one number and taking it re-ranked the entry.**
The entry asked for two concurrent generations timed against
llama-server. What the box says is that the two generations never
overlap, that the contender is a third party the entry does not name,
and that this repository has been gating on the card all along.

**This repository gates, and the entry's own check could not see it.**
`sysadmin/core/llm_client.py:134` calls `ensure_gpu_idle(...)` from
`estate.gpu` at threshold **25** — one pre-dispatch read, `GpuBusy` →
`return None` → `llm_used=False` → digest. The entry's AST walk searched
`estate_queue`, `wait_for_dgpu` and two literals, found none, and the
sentence it supported read *"neither party is gating"*. The walk was
correct about its four names; the generalisation was not, and
`sysadmin-check-snags` printed `gpu gates under sysadmin/: none` over a
repository that has gated since 2026-08-12. Filed and fixed as
**`SNAG-SCHED-002`**.

**The obvious repair is the harmful one, and that is why it is its own
entry.** Adding `ensure_gpu_idle` to the refuting set flips half 1 to
`mismatch` and reports `SNAG-SCHED-001`'s first named fix as landed — on
the strength of a gate that **predates the entry by eighteen days** and
fixes nothing. Worse, that gate is the *mechanism by which the entry
hurts*: without it the collision would cost a slow review, with it the
collision costs the narrative outright. The vocabulary is split by what
a gate **does** rather than by whether one exists —
`GPU_ARBITRATION_NAMES` wait and therefore refute,
`GPU_DEFERRAL_NAMES` read once and are reported beside them as evidence
that can never refute. `_gpu_gate_mentions` takes its vocabulary as a
parameter, since a second body is free to drift from the first about
what "binds" means. **The verdict does not move**, which is the point:
this repairs what the check *says*, not what it decides.

**The occupant at our dispatch instant is `venture-enrich-nightly`, and
this box's own journal is what says so.** The drain finished
**05:47:18, 05:45:15, 05:46:58, 05:45:22 and 05:45:26** on 08-26 →
08-30 — *the same five values the estate published as "the drain
released at"*, so their granted band **is** the drain's finish and their
review is granted after it. Every one is after our 05:45:00 dispatch, by
15 s to 2 min 18 s. `resource_snapshots` corroborate independently in
two signals at once: `gpu_percent` **99 at 05:44:45** on 08-30, and
`vram_used_mb` **19,870 → 11,112** across the release.

**A generation takes under six seconds, so the two never overlap at
all.** The real disk-review prompt (385 prompt tokens) dispatched raw —
no gate, no write — gives **80.0 tok/s** solo over three runs and
**62.4 tok/s** per stream with two in flight over four: **77.9 % of
solo, a 22.1 % cost**, both completing, nothing failing against a 120 s
timeout, worst single run **5.85 s**. A 05:45:00 dispatch is finished by
~05:45:06, before the earliest grant. Session 79's fifteen-minute
spacing was over-provisioned by roughly two orders of magnitude and was
never the scarce resource; the drain's **5 h 45 m** is.

**So the chain is the entry, not the slot — `SNAG-SCHED-003`, filed
P2.** Since the drain moved to 00:00, `resource_snapshots` in a ±300 s
window round each slot read health **12 of 12** samples over the gate's
own threshold, log **12 of 12**, disk **5 of 12**. The two reviews
`SNAG-SCHED-001` does not mention sit squarely inside an occupancy no
schedule leaf in that entry reaches, and there is no minute to move them
to: the hold runs 00:00 → ~05:45 and the 06:00 briefing is the fixed end
of the chain. **The estate meets the identical fault and does not pay
it** — `estate-manager-review.service` logged `llm_gpu_busy` →
`project_review_llm_unavailable_used_fallback` on 08-17 and 08-24,
finishing in **368 ms and 390 ms**, and responded by taking a lease and
**waiting** up to 1800 s. On the same fault they now wait and get their
narrative while we defer and lose ours. That inverts the entry's
ranking, which priced the lease as the expensive option.

**Why the entry's own named measurement was not run as written.** Run
now it answers the wrong question: the desktop holds the card at a
**66.2 %** mean with **97.3 %** of 150 samples over the threshold, so
both reviews would fall back for a reason that is not the collision —
and driving the estate's `POST /api/projects/review/generate` would have
written a `project_reviews` row into another repository's database to
buy that confounded reading. The contention half was driven raw against
llama-server instead, which is the faithful form of the same question
and writes nothing anywhere.

**Decided and not done, deliberately.** Neither fix is landed. The
measurement now says which one to take — a lease, because it arbitrates
against the holder wherever the boundary lands, and the boundary is
another repository's **workload**, whose wall clock has ranged **1 h
14 m to 5 h 47 m** across the recorded nights. Moving leaves chases a
4½-hour spread. But `SNAG-SCHED-003` has **not been observed once**: no
Monday has run in the new regime, so the fix waits on 08-31 rather than
on an argument.

**+20 tests, 3160 → 3180.** The baseline was measured by stashing to
HEAD and re-collecting rather than read off the STATUS row, which said
**3107** — a 53-test gap and `SNAG-ESTATE-008`'s shape in that cell for
the third time. Eleven mutations driven, each red on the intended tests,
and **one passed against deliberately broken code**: replacing the
majority rule with unanimity survived because the specimen for *"one
slot inside is enough"* had that slot at **6 of 6**, a reading both
rules agree about; it is **4 of 6** now with a boundary test at exactly
half. A second guard was strengthened before it could be driven — the
threshold pin compared the detail against `get_config()`, which passes
just as well over a hard-coded `25` while the shipped threshold happens
to be 25, so it now *moves* the threshold and requires the reading to
move with it.

**Nothing was filed at the estate.** Their published band is accurate
and their own review is correctly protected; what this sitting found is
that this repository read their band as *their review's* rather than as
*the drain's*, which is ours to have got wrong. No cross-repo friction
was incurred.

## Session 139 is complete — the gauge moved and the threshold deliberately did not

**Estate message `d1939cf7` is acted on and closed.** estate-manager's
weekly review now *takes* a GPU lease instead of sampling a counter
(their ADR-0076/0077, filed **before** the commit that carried it —
their rule 3), so it queues behind `venture-enrich-nightly` every Monday
05:30 and waits **915–1038 s** across the five nights they measured.
This repository judged `oldest_waiting_seconds > 900` with the message
*"Either a holder never released, or the arbiter's tick loop has stopped
granting"* — so the first alert would have arrived on a Monday morning,
said the queue was starved, and been **wrong**.
`judge_queue_invariants` reads `oldest_unexplained_wait_seconds` now,
which is the same number with that third cause masked out by the
producer. **`queue_max_wait_seconds` is unchanged at 900.**

**The message's own recommendation was taken as filed, and the reason
raising the threshold was refused is worth carrying.** At any larger
number the gauge still cannot separate a normal Monday from a stuck
queue, it only says so later — and the Monday wait is bounded by
*another repository's* timer, so the new number would be one schedule
change from being wrong again. `config.yaml` now carries that refusal
beside the leaf, because the leaf is where a future Monday false alarm
sends someone.

**Three rules, two of them the opposite of the obvious
implementation.**

1. **The mask is read, never recomputed.** `waiting_reason ==
   "behind_holder"` plus the raw gauge reconstructs the masked number,
   and reconstructing it makes this a second implementation of the
   producer's derivation — `SNAG-DB-003`'s shape. A test drives an
   *inconsistent* payload (`behind_holder` beside an unexplained wait)
   and asserts the field wins; it is the one mutation that lands on a
   single test.
2. **Absent is not masked** — `ports_checked`'s rule at the size of a
   dict key. `payload.get(...)` answers `None` both for a producer that
   explained the wait and for one that does not publish the field, and
   collapsing them retires this family in silence the day the estate
   rolls back. A payload without the key falls back to
   `oldest_waiting_seconds` and labels the row `wait_gauge: "total"` —
   deliberately the *pre-fix* behaviour rather than a refusal, because
   over-reporting on a Monday is the failure this module survives and
   going quiet is not.
3. **The reason is named, because the producer names it** —
   `SNAG-UNITS-004`'s defect otherwise. The two values that can still
   reach a row are exactly the old disjunction's two limbs, which is
   what makes the existing sentence true again. A value this repository
   has not been told about falls back to the disjunction rather than
   being rendered.

**The trade is stated rather than left to be discovered: a survivable
absence is a silent one.** The fallback makes the new field vanishing
invisible to every fixture-driven test, so the only place it can be loud
is the live half — `test_the_wait_discriminator_is_still_published`,
beside one asserting the masked gauge never exceeds the gauge it masks.

**The fixtures are the producer's.** The three states were built by
running `Arbiter.submit` → `tick` → `invariants` in estate-manager's own
venv against a **scratch** database created and dropped by the capture —
never the live `estate` one, which estate rule 1 forbids writing and
which two connections could not have been rolled back across anyway.
Only public symbols were touched. The 2026-08-16 fixture is kept
**unmodified** as the legacy-producer specimen and a test fails if it is
hand-edited into the new shape.

**It ships untriggered**: `alerts` holds **0** `Estate queue…` rows
all-time, so nothing standing needed reconciling and no fixture could
have said so. Restarted twice (19:41:36 on the merits, 19:54:44 for the
mtime check's blind spot — `snag_claims.py` has 0 importers under
`sysadmin/`); the estate judge ran at 19:42:39 and 19:55:46 against live
8400, all four surfaces read, no queue row, no error lines.

**No ADR, and that is a decision rather than an omission.** `8462bcc5`
got [ADR-0006](docs/adr/0006-wiring-joins-ports.md) because it carried
`needs_ruling=true` and asked a question this repository had to answer;
`d1939cf7` is recommendation-only, and the reasoning lives in
`judge_queue_invariants`'s docstring where a future reader of that
predicate will meet it.

**One snag opened beside the work — `SNAG-SCHED-001`.** Reading *why*
their review takes a lease showed it displaces **where it generates**
from 05:30 to the grant, which is this repository's disk-review slot.
Neither party gates: an AST walk over `sysadmin/` finds **zero**
bindings of `wait-for-dgpu`, `/api/queue/lease` or `estate_queue`, and
their lease arbitrates them against `venture-enrich-nightly` rather than
against us. The entry claims **less than it could** — nobody has
measured what two concurrent generations cost, llama-server serialises,
and their `estate-review` profile is no-swap — so what is claimed is
that Session 79's fifteen-minute spacing is now false and unmeasured,
with the deciding measurement named. Its check is a **conjunction**, so
either fix refutes it; watching one limb would report *still holds* over
the other, which is `check_review_schedule_unread`'s defect and one this
repository has already paid for.

**The falsification worth carrying is the one that passed.** The
check's first draft was a substring search and read
`estate_queue_invariants.json` **named in a docstring** as a landed gate
— a check that reads a *sentence about* a fix as the fix retires its own
entry. The detector excludes docstrings by node identity now; but the
test written for that regression **passed against the mutation**,
because `estate_queue` is matched as an identifier and a docstring
cannot produce an `ast.Name` — green for a reason it did not name. Only
a *literal* gate spelled in prose exercises the exclusion, which is what
the test builds now.

**Numbers.** +35 tests, **3125 → 3160**; `ruff` and `mypy` clean;
`check-ops-claims.sh` all green; `check-snag-claims.sh` reports 19 open
entries and **0** carrying no check. Ten mutations of the predicate,
eight of the fixture and live guards and six of the new check each land
red on the test that owns the rule.

## Session 138 is complete — the measurement refuted the remedy rather than sizing it

**`SNAG-TRAY-011` is decided, not fixed.** `sysadmin-tray` does **not**
gain a `log:` block. The sitting was told to measure the tray's
`warning`-and-above volume before declaring the source; the measurement
found the *mechanism* instead, and it refutes the entry's own shape of a
fix at **two independent gates**. **No code changed** — this is a
documented decision, and the entry stays **open** as a deliberate
non-fix with its reason measured, the idiom `SNAG-LOG-002` and
`SNAG-UNITS-002` already use.

**Gate one: the priority stamp — `SNAG-AGENT-008`'s priority half, one
program over.** `sysadmin-tray.service` has written **677,567 journal
records** between 2026-08-11 07:08:12 and 2026-08-30 18:56:05 (19.49
days) and **every one is `PRIORITY=6`**. `main()` configures
`logging.basicConfig(format="%(asctime)s %(levelname)-8s %(name)s — %(message)s")`
— a text formatter emitting no `<N>` prefix — so systemd stamps captured
stdout `6` whatever the level inside says, and the unit's
`SyslogLevelPrefix=yes` strips a prefix nothing writes.
`max_priority_for("warning")` is **4**, so the declared source would read
`journalctl -p 4` and ingest **nothing, ever**. Measured directly:
`journalctl --user -u sysadmin-tray -p warning` over the unit's whole
recorded life returns **no entries**. The block would have shipped
green, stored zero rows, and left the warning as inaudible as the entry
filed it.

**Gate two: the alert family, which fails even if gate one is fixed.**
The entry claims the block "makes the warning an alert row through the
family that already owns this source". It does not —
`FAULT_SEVERITIES = ("error", "critical")` (`log_aggregator.py:144`) and
the ingest loop `continue`s on anything else, so a `warning` line is
**stored and raises nothing**. A working prefix moves the line from
`info` to `warning`; both are below the family's floor.

**Decisions taken, and what was rejected.**

- **The prerequisite for gate one was rejected on this repository's own
  rule, not on cost.** Reusing `JournalLevelPrefixFormatter` is legal —
  `sysadmin_tray/config.py` already imports from `sysadmin.core` and the
  boundary forbids only the reverse. But that class extends
  `JsonFormatter` deliberately: **Session 61 rule 2** holds that the JSON
  gate is a precondition rather than a proxy for the destination, because
  only the JSON formatter guarantees one line per record, and under a
  text formatter a traceback's first line is stamped `ERROR` with its
  body left `info` — *"worse than the uniform 6 because it looks fixed"*.
  Making the tray's levels reach the journal means moving a GUI program
  to JSON logging, for one dead presentation knob.
- **`severity_filter: info` was rejected as the branch that pays
  everything and buys nothing.** It is the only non-inert branch:
  **34,762 rows a day**, ~**1.04 M** at the aggregator's 30-day
  retention, for a source with **zero** `WARNING`/`ERROR`/`CRITICAL`
  lines in its entire recorded life (677,516 ` INFO ` tokens in the
  message text and no others; the 51-record difference is systemd's own
  `Started SysAdmin Assistant - Tray.` lines, which carry no level
  token). And it still raises nothing, by gate two.
- **`SNAG-LOG-004`'s warning turned out to bound the wrong branch.** The
  entry weighed "a fix widening what the monitor sees is a regression
  surface" against declaring the source at `warning`. That branch is
  inert and has no regression surface at all; the warning applies only to
  the `info` branch, which is the reverse of how the entry weighed it.
- **The entry was corrected rather than only annotated.** Its shape-of-fix
  bullet is now marked refuted and points at the decision, because a
  later sitting reading the original would re-derive a remedy that cannot
  work.
- **P3 is confirmed rather than inherited.** The population is one
  warning about a dead presentation knob announced to an operator who is
  by definition at a terminal, and the three changes needed to make it
  audible — a JSON formatter in the tray, a `log:` block, and a widening
  of `FAULT_SEVERITIES` or a level bump — are each larger than the thing
  announced.

**What no amount of reading would have said**, which is why the entry
deferred this to a sitting that could measure: the priority stamp is
invisible in the tray's source, in `services.yaml` and in the unit file
— `SyslogLevelPrefix=yes` reads like the mechanism working. Only
`journalctl -o json --output-fields=PRIORITY` over the real unit
separates *the tray has nothing to say* from *nothing it says can be
heard*, and the answer here is **both** — `ports_checked`'s rule
arriving as a decision rather than as a field.

**Verification.** `sysadmin-check-snags` reports
`SNAG-TRAY-011 … still holds` with both channels unmoved (15 log
sources, tray absent, one `load_tray_config` call site), so the check
means what it says over a decided entry. `check-ops-claims.sh` is nine
green — the new STATUS.md block carries 60 backticks, an even count, so
no `<!--check:-->` marker after it was disarmed. **`uv run pytest`:
3125 passed**, unchanged, since no code moved.

## Blocked / open

- **Estate message `d1939cf7` is open and its trigger is tomorrow.**
  estate-manager's weekly review now takes a GPU lease and queues behind
  `venture-enrich-nightly` on Mondays at 05:30, waiting a measured
  915–1038 s over five nights — over this repository's
  `queue_max_wait_seconds: 900` every Monday. Their recommendation is
  explicitly *not* to raise 900, on the ground that the gauge itself
  stops distinguishing the conditions; point the predicate at the new
  `oldest_unexplained_wait_seconds` instead. **Both fields are already
  live** — verified 2026-08-30 against `GET :8400/api/queue/invariants`,
  which returns `waiting_reason` and `oldest_unexplained_wait_seconds`
  alongside the unchanged `oldest_waiting_seconds`. Nothing breaks if
  this is not done; the cost is one false `Estate queue starved`
  critical every Monday morning.
- `SNAG-TRAY-011` stays open by decision, not by neglect. Nothing further
  is owed on it unless the tray moves to JSON logging for an unrelated
  reason, at which point gate one dissolves and only gate two remains.

---

## Session 137 is complete — the allowlist is the authority, and the convention was copied without its formatter

**`SNAG-CFG-005` is closed.** `SNAG-CFG-004` gave every region of
`config.yaml` the backend owns a watcher and left the top-level `tray:`
section as the residue — exempt whole by `FOREIGN_KEYS` because holding
a model of another parser's section is the second-owner defect, and
dropped in silence by the tray because `load_tray_config` copies an
allowlist of seven keys out of the section and never looks at the
remainder. `tray_section_report` is that set difference, warned in the
loader and reported never refused. It ships **untriggered**: the shipped
`tray:` carries six keys, every one read, and the real tray was
restarted against the real file and said nothing.

**Decisions taken, and what was rejected.**

- **The audibility question was put to the owner and answered "warning
  only, file the gap".** The alternative on the table was giving
  `sysadmin-tray` a `log:` block so the aggregator ingests the line and
  it becomes an alert row. Rejected for this sitting because that is a
  decision about a **new log source** rather than about a set
  difference, and `SNAG-LOG-004` is this repository's own record of a
  fix widening a monitor's view becoming a regression surface. It is
  `SNAG-TRAY-011` and it is the next action.
- **A walk against `TrayConfig` was rejected on measurement, not
  taste.** It is the shape `core/config_keys.py` uses for `AppConfig`,
  it is legal here (the import boundary forbids only the reverse), and
  it would have shipped green: the model declares **19** fields where
  the section supplies **7**, so it calls `tray.reminder_hours: 5`
  declared when setting it there does nothing.
- **`notifications.tray:` is deliberately not reported here.** The
  backend already names a typo in it — driven, not assumed. One fact,
  one speaker.
- **`tray.api_url` stays unread**, and the docstring promising it since
  `81b3bfb` was corrected rather than the key being added. A second home
  for the backend's address is two statements of one fact;
  `service.host`/`port` is the one home, and `estate_api_url` is read
  from `tray:` only because 8400 has no `service:` block.

**What git cannot show.**

- **The live drive is what found the real defect.** The first version
  used `extra={"keys": …}` — this repository's logging idiom, readable
  only because the backend's `JsonFormatter` folds `extra` in. The
  tray's formatter is `basicConfig(format="… %(message)s")`, so the
  journal line was the bare event name `tray_config_unknown_keys`,
  announcing a dropped key and unable to say which. The retired check
  had recorded the *opposite* lesson, so the wrong half of a two-sided
  lesson got copied. Nothing in-process would have caught it.
- **`tray: 5` used to crash the tray** — `key in 5` raising `TypeError`,
  unhandled, in the one section this module hand-parses. Found by
  probing shapes rather than by reading.
- **An eighth mutation landed red by accident** and exposed a rule with
  no guard: the test named for "notifications.tray is not our business"
  drove the *backend*, proving the other speaker exists while doing
  nothing to stop this one becoming a second.
- **Two of the new check's own tests were false greens.** One aimed its
  stand-in past the decision; the other patched `load_services` when the
  check calls `get_services` — and that second one exposed the check
  reading `services.yaml` twice, two ways, free to disagree about which
  file it measured. One reader now.
- **`SNAG-TRAY-009` was already taken**, by an entry fixed 2026-08-29.
  The new one is `SNAG-TRAY-011`. Sweep the ids before minting.

**Nothing is blocked.** Suite 3125 green, ruff clean, mypy clean, all 9
ops claims and all 18 snag checks green. The daemon and the tray were
both restarted; the daemon restart was owed by the mtime check rather
than on the merits, since this sitting's only backend change is a
console script the running application never imports.

## Session 136 is complete — the headline fix does not boot, and the file said so first

**`SNAG-CFG-004` is closed by reporting, and the entry's own headline
fix was refuted before a line of it was written.** It asked whether
`sysadmin/core/config.py`'s 37 pydantic models should set
`extra="forbid"` as `sysadmin/monitor/services.py`'s four do. Walking
the shipped `config.yaml` against `AppConfig`'s field tree finds **ten
keys the backend does not declare** — the top-level `tray:` section and
nine leaves under `notifications.tray:`, every one read by
`sysadmin_tray/config.py`, which parses the same file for itself. So the
forbid is not a trade-off to weigh against `SNAG-DB-005`'s 23 hours; it
is a daemon that will not start on this box **today**.
`TestTheAsymmetryIsDeliberateAndStays::test_the_entrys_headline_fix_does_not_parse_the_shipped_file`
builds the strict subclass and asserts exactly that, so the refutation
is executed rather than argued.

**The asymmetry the entry read as an inconsistency is structural.**
`services.yaml` can forbid because every key in it belongs to the
process holding the models; `config.yaml` cannot, because it carries a
region this process does not own. One file, two parsers, neither model
set a superset of the other. And the `schema_guard` analogy the entry
reaches for runs the **other** way: that guard refuses because serving
against the wrong schema is worse than not serving, and serving with an
ignored config key is demonstrably not — it has been this daemon's
behaviour for its whole life at a cost of one briefing at the wrong
hour. Same posture, opposite answer, because the cost side differs.

**What shipped reports and cannot refuse**, and that is settled by the
shape of the mechanism rather than by a flag a later sitting could flip:
`sysadmin/core/config_keys.py` walks the raw YAML against the model tree
and **returns a list**. `unknown_config_keys()` is the entry point, the
lifespan warns, and `ReloadReport.unknown_keys` carries it to
`POST /api/sysadmin/reload` — the surface an operator who has just
edited the file is actually holding. `unwalkable` is kept apart from
`unknown` because a subtree the walker could not follow has zero unknown
keys for the wrong reason, which is `ports_checked`'s rule.

**The boundary is declared and pinned, never asserted.** `FOREIGN_KEYS`
is hand-written because `sysadmin.core` must not import the tray, so
`TRAY_SECTION_KEYS` and `NOTIFICATIONS_TRAY_KEYS` were lifted out of the
loops that consumed them and a test asserts the two agree — import where
you can, pin where you cannot. Exempted **by leaf, not by subtree**:
`notifications.tray.mute_services` is read here, so a subtree exemption
would silence `mute_servicess` on the one key under that section the
backend depends on. The dividend was not designed for — because the
correct spelling is exempt and a typo is not, a misspelt *tray-owned*
leaf is reported too.

**The check retired and its meaning inverted, which is the part worth
carrying.** It counted `extra="forbid"` on both sides and **this fix
moves neither count**, so it would have gone on reporting *still holds*
over a landed closure indefinitely — `check_review_schedule_unread`'s
defect from one entry earlier, and not a flaw in how it was written,
since the entry closed by a route the check did not anticipate. The
detector is re-homed as `TestTheAsymmetryIsDeliberateAndStays`, where
those two counts must now **stay** where they are.

**Two falsifications passed against deliberately broken code first.**
The subtree-exemption mutation changed nothing, because
`notifications.tray` is not itself in `FOREIGN_KEYS` — prefix matching
alone matches nothing, so the faithful mutation had to replace the
constant *and* the matcher. And adding `ConfigDict(extra="forbid")` to a
config model produced a **collection error** rather than a red test,
because that name is not imported in that module: a stand-in that cannot
compile is silence wearing a result, this repository's own recorded trap
met a second time. `SNAG-CFG-005`'s check had the same disease in its
first draft — it read `getMessage()` while this repository's logging
convention puts the key in `extra=`, so it did not move over a stand-in
fix.

**One slip cost work and is worth recording**: `git checkout
sysadmin/core/config.py` was used to revert a mutation and discarded
every edit to that file, which had to be rewritten. The `.bak` pattern
used everywhere else in the sitting is the one that survives being
wrong.

**Verified live rather than only against fixtures.** Daemon restarted
16:26:28, booted clean with no spurious warning; the warning line was
driven through the real `configure_logging` and emits
`<4>{… "message": "config_unknown_keys" …}`, so it carries Session 61's
level prefix and a short readable signature rather than
`SNAG-LOG-003`'s 252 characters of JSON. A real `briefing_hourr: 9`
written into the shipped file returned
`{"ok": true, "unknown_keys": ["schedules.briefing_hourr"]}` and the
file was restored byte-identical.

**Numbers.** Suite 3079 → 3107 (+33, −5 retired), twelve mutations each
red on the tests about its own rule. Snag list 108 → 109 entries, open
unmoved at 18 (one closed, one opened). Ruff and mypy clean. No route,
table or migration moved.

---

## Session 135 is complete — the leaves went, and the check could not have watched them go

**`SNAG-CFG-002` is closed.** `schedules.review_hour` and
`review_minute` are gone from `SchedulesConfig`. `review_day_of_week`
stays, read by all three weekly review jobs, and its comment now says
what is true: one leaf, three readers, generic because that is accurate
rather than vague.

**The handoff's question was closed by measurement rather than decided.**
It asked whether the two leaves should be wired to something or deleted.
Nothing was left to wire: every surviving review already carries its own
hour/minute pair (health 05:00, log 05:15, disk 05:45), the weekly
*project* review these two scheduled left for estate-manager under
ADR-0005, and the 05:30 their default named is another repository's —
`estate-manager-review.timer`, re-verified live with `systemctl --user
cat` as `OnCalendar=Mon *-*-* 05:30:00`, next firing Mon 2026-08-31. The
value the leaves carried had become a collision, not just a dead number.

**The entry's own check could not have witnessed its closure**, which is
the part worth carrying forward. `check_review_schedule_unread` answered
`match` whenever it found no reader — and a deleted field has no reader
— so it would have gone on reporting *still holds* over a landed fix
indefinitely. A control whose observation does not move across the fix
it guards is not a control. So the regression guard is keyed on
**absence** (`TestTheVacatedReviewLeavesStayGone`), and it carries a
second test asserting the three surviving `*_review_*` pairs are
present, because an empty intersection is satisfied by a model with no
fields at all. What survived the retirement is the *instrument*: rule
7's exact-versus-substring demonstration never depended on the deleted
leaves existing, so it is re-homed rather than deleted with the check —
`FROZEN_TABLES`' rule.

**Deleting a config field changes nothing for whoever edits the config
file.** `SchedulesConfig` inherits pydantic's `extra="ignore"`: **0 of
37** models in `sysadmin/core/config.py` forbid unknown keys against
**4 of 4** in `sysadmin/monitor/services.py`. Driven through the real
`parse_config` — never `load_config`, which is
`set_config(parse_config(...))` and would have installed the broken
specimen into the measuring process — `briefing_hourr: 9` parses cleanly
and `briefing_hour` reads its default 6. The operator has moved the
morning briefing and the briefing has not moved. Filed as
`SNAG-CFG-004` with a check reporting **which of two opposite
directions** the asymmetry closed in; not fixed here at the owner's
direction, because it is 37 models and it turns a stale key into a
refusal to boot, which is `SNAG-DB-005`'s trade taken without the
operator being ready for it.

**What was rejected, and why.** Renaming `review_day_of_week` to
something saying "shared" was considered and refused: it is a second
published-surface change in one sitting, `config.yaml` sets neither
today so the rename buys naming only, and the generic name is now
*correct* — the entry's complaint was about a generic name scheduling
one specific thing among three, which stopped being true when the leaf
gained three readers.

**The adjacent comment had the same disease and was fixed too** —
`disk_review_hour`'s said it was staggered *"after the project review"*,
gone seventeen days, and that the briefing carries *"both narratives"*,
which has been three since Session 79. Not scope creep: the same
stale-comment defect, in the block being edited.

**Numbers.** Suite 3070 → 3079 (+10, −1 retired), nine mutations driven
and each red on exactly one intended test. **The STATUS.md Testing row
read 3018 against a HEAD that collected 3070** — four sessions stale,
`SNAG-ESTATE-008`'s shape in that cell for the second time, corrected
here; it is also why the baseline is taken by *running* rather than by
reading, since trusting 3018 would have made `baseline + added == total`
report a clobber that never happened. Snag list 107 → 108 entries, open
unmoved at 18 (one closed, one opened). Daemon restarted 14:29:19, owed
on the merits and deploying nothing observable; all nine ops claims
green.

---

## Session 134 is complete — one gate, two answers, and the library's own tie-breaker decides it

**estate-manager's message `df4113cb` is closed.** It announced that
`estate.gpu.sustained_busy`'s docstring now states a **test** rather
than a category — spend the blocking ~1.5 s min-of-N window wherever
nobody waits on the answer, never where a request is held open — and
asked whether `core/llm_client.py`'s single `ensure_gpu_idle` read has a
waiter. Nothing was required; the decision was ours.

**It has both, at three gates rather than one.** Each of
`files/review.py`, `monitor/log_review.py` and `monitor/health_review.py`
exposes one `generate_review`, and each is reached by a Monday
`run_weekly_review` with nobody waiting **and** by a
`POST …/review/generate` that `await`s it inline and holds the request
open across the gate. That is estate-manager's own `SNAG-ESTATE-090`
shape, tripled. The library states its own tie-breaker — *a caller that
cannot answer the question for every one of its invocations keeps the
single read* — so the answer needed no judgement call, only the
enumeration.

**The split was costed and refused, and the arithmetic inverts the
obvious ranking three ways.** The window's entire benefit is the
~1-in-120 transient Alfred sampled. The waiterless path fires **three
times a week** — one dispatch per weekly review, confirmed live in the
restarted daemon's 12 scheduled jobs. And a false defer does not cost a
review, it costs **prose**: the caller falls back to
`build_fallback_narrative` and still stores, serves and briefs a
deterministic digest at `llm_used=False`. Roughly one narrative every
forty weeks, against a parameter threaded through three signatures and a
seventh caller free to default it wrongly. Filed in `ideas.md` as
available-and-not-taken, not declined — the argument for it is sound and
only the arithmetic is against it.

**The waiter is the majority invocation, and the docstring had it
backwards.** It called this service's inference *"deferrable
housekeeping"* — the one sentence that would have led the next reader
straight to adopting the window. Of the six reviews this box has
generated in its life, **five came from the routes and one from the
Monday job**: three disk reviews three minutes apart on 2026-08-06, a
log review at 07:54 on 08-24, a health review at 13:09 on 08-25, against
one at 05:45 on a Monday. **Reading the code confirms the announcement;
reading `health_reviews`/`log_reviews`/`disk_reviews` ranks it** — and
the ranking is the opposite of what the code says about itself. That
sentence is gone.

**Both halves of the decision are pinned, because it has two ways to go
stale.** `tests/test_gpu_gate_invocations.py` holds the **premise** —
each gate still reached from both classes, keyed on the route *awaiting*
rather than merely calling, since a handler that dispatched to a task
and answered 202 would make every invocation waiterless and re-open the
decision with nothing else to say so — and the **rule pre-staged** for
the day someone adopts the window: `sustained_busy` must go through
`asyncio.to_thread`, since every call site here runs inside an event
loop. The detector exempts by descent, so both correct spellings pass
(`to_thread(sustained_busy, slot)` never calls it; the lambda form calls
it inside the shelter).

**Its population is empty today, so the detector is driven at synthetic
sources in both directions.** A sweep finding nothing over a population
of zero is not evidence of anything — the lesson this repository has now
paid for several times. Four mutations were driven and each lands on the
**named** test: a route dispatching instead of awaiting, a job dropping
the call, the gate adopting the window bare (red on **both** window
guards), and a router renaming its alias. Test arithmetic **3060 → 3070**,
+10 and none retired, verified against the baseline with the new file
ignored rather than against a green suite.

**No production behaviour changed** — the edit is a docstring. The
daemon was restarted anyway so the box and the checkout agree
(`check-ops-claims.sh` reported the deploy check `no` after the mutation
harness moved four mtimes; all four files restored byte-exact, confirmed
by `git status`). Suite 3070 green, ruff and mypy clean, all 18 snag
checks still hold, and the snag register parses unmoved at 107 entries,
18 open.

**What would change the answer**, recorded so it is not re-derived: the
routes ceasing to hold the request open, or the transient's cost rising
above one narrative in forty weeks. `DEFAULT_BUSY_THRESHOLD` stays 25
and no power or clock term was adopted — both refused upstream on
measurement (the clock term is *inverted*), recorded here so neither is
re-proposed from this side.

## Session 133 is complete — twenty-four dead links were three classes, and the middle one is the trap

**estate-manager's message `25be77ba` is closed.** All 24 inward links
resolve — `docs/roadmap/snag_list.md` (14),
`docs/project-capability-audit.md` (8), `docs/roadmap/tasks.md` (2) —
and `tests/test_doc_links.py` is the guard that keeps them resolving.

**The instruments disagreed by one before a line was repaired, and mine
was the narrow one.** A first scan found **23**. `line.startswith("    ")`
reads a six-space *list continuation* as an indented code block, and
`tasks.md`'s 24th link sits on one; CommonMark makes indentation a code
block only when no list is open. Repairing on that reading leaves one
link behind while reporting twenty-four, so the disagreement was resolved
before anything was edited rather than after.

**Three fates, not the two the previous handoff named.** **5** targets
survived the 2026-08-08 split (`512af01`) and took a path repair. **16**
left under ADR-0005 and took a pointer to it. **3** are the class the
filing has no name for: the *file* survived and the *cited symbol* did
not. `config.py` is now `sysadmin/core/config.py` and holds no
`ProjectsConfig`; `briefing.py` is now `sysadmin/briefing/data.py` and
holds neither `_build_project_health_section` nor
`_build_next_actions_section`. A path repair there **resolves**, reads
correctly and points at code that does not carry the claim — worse than
the dead link, and exactly the "plausible path" fallback the message
declined to supply targets for.

**The true count is 27, and the estate said 24 was a floor.** Their
instrument is existence-only. Resolving `#L` anchors against the target
file found **3 more** links that resolve while their anchor has rotted:
`main.py:123-128` at a blank line, `agent.py:391` at an unrelated
docstring, `retention.py:85` at `"health_reviews": WHOLE_TABLE`. All
three repaired in the same sitting, so the class the filing could not
see is not left as the next reader's surprise.

**No new line anchors were minted**, which is a rule rather than an
omission. 13 of the 24 carried one and every rotted anchor above was
once correct, so re-pinning them manufactures more of the defect being
repaired — and nothing in this repository or the estate's could see it
happen. Each citation keeps its original line range as **text**, which
is the evidence the entry rests on, beside a live link to the file.

**The capability audit is dated and now says so.** It is an evidence
document written 2026-08-07, one day before the split, so its citations
were correct when made. It gained a note stating that its code
references describe that tree, rather than being quietly rewritten to
imply it describes today's.

**The detector outlives the finding** — `FROZEN_TABLES`' rule, the
seventh time here. `tests/test_doc_links.py` asserts every relative link
in a tracked `.md` resolves, and pins both sides of the block rule: a
link in a list continuation is seen, a link in a genuine indented or
fenced block is not. The estate refused this check under their ADR-0073
(the audit may falsify only a claim the *estate* makes, and how this
repository writes links is a claim it makes nowhere), which is precisely
what leaves it here.

**Two things deliberately not done.** No SNAG entry was filed: this
register requires every open entry to carry a check written to its own
standard, and the guard that would be that check is the test just added,
so an entry would be asking for what already exists. And no cross-repo
link points at estate-manager *source*: all 12 that exist here point at
documents, and a link into a tree governed by another repository's ADR
process is the next filing of this same message.

**3056 → 3060**, +4 and none retired. Two mutations, each red on exactly
the intended test — a broken link reddens the corpus test, and reverting
to the naive indentation rule reddens the continuation test and nothing
else. Docs only, no production behaviour changed; ruff and mypy clean,
and the snag register parses unmoved at **107 entries, 18 open**.

---

## Session 132 is complete — the habit that became a guard, and the two docstrings it refused

**`SNAG-TEST-002` is fixed.** `TestEveryCheckCanSayItDoesNotKnow` in
`tests/test_snag_claims.py` sweeps `CHECKS` and refuses a registered
check that no test class drives to an `unknown` verdict — the fourth
sweep over that registry, beside the three that ask whether the register
and the registry agree about *which* entries are measured. **18 of 18**
covered at the moment of the fix, and the register now reads **18 open**
with every entry carrying a check.

**The check retired with the entry and its walk did not**, which is
`FROZEN_TABLES`' rule for the sixth time here.
`check_unknown_branch_unenforced` was written to detect its own fix
landing — `_sweep_enforces_unknown` looks for a `test_` function
mentioning both `CHECKS` and the verdict — so the sweep could not be
written without retiring it. `_unknown_branch_coverage` and
`_unwritable_sentinel` moved into the drive; the check, its detector and
its registration went from `sysadmin/snag_claims.py`.

**The sweep's own class is one of the classes it walks, and that is the
part no reading would have found.** The walk counts a class that names a
key *and* asserts the verdict, so a docstring citing a check by key makes
the sweep vouch for that check — itself. It fired on the docstring
explaining the sweep, which cited `check_unmarked_sentence_invisible`,
and again on the docstring written to explain the first firing, for
naming the key while saying that naming it is what is forbidden.
`test_live_drive_premises.py` exempts its own owner for exactly this
reason; there is no exemption here, so the prose is written around the
key.

**Two guards passed against deliberately broken code and both were
repaired**, which is this repository's standing failure mode caught
twice in one sitting. The second witness asks whether the class pin is
green because the class is clean or because the walk is blind *there*:
its first draft spliced a key into the class's real source and
**failed**, since this class asserts no bare `unknown` constant and could
never have been seen — both halves are appended now. And the class's name
was restated as a `SWEEP_CLASS` constant, so pointing it at a *different*
clean class left all fourteen tests green; it reads
`type(self).__name__` instead, which makes that mutation impossible
rather than merely caught.

**`UNKNOWABLE` is the declaration the entry asked for**, and it is empty
by measurement rather than by omission. The entry forbids requiring an
`unknown` branch of the *producer*, so a check whose every input is local
discharges the sweep by a name and a stated reason — `PRE_CONVENTION`'s
shape one file over, with the same two tripwires (a declared name since
driven, a name no longer registered) plus one refusing a blank reason.
Driven at a stand-in, because a mechanism with no members is
`SNAG-UNITS-006`'s standing.

**The looseness of the walk is stated rather than tightened.** It keys on
the class, so a class naming a key only in passing while asserting the
verdict about a different one counts —
`TestChecksAgainstTheLiveBox` covers seven keys at once and
`TestTheQueueTimezoneCheck` names `sysd_ollama_ordering` incidentally.
Measured: **no key is covered only incidentally**, every one is also
reported by the class that owns it. So the sweep is a floor on the habit
and not a proof of it, which is the entry's measurement promoted rather
than a stronger claim invented in its place.

**Two mutations were wrong on the first attempt.** A comment naming a key
changed nothing, because `ast.unparse` drops comments and the walk
unparses too — inert mutation, not blind pin — and had to be respelled as
a docstring. And a literal sentinel fails the mint test while leaving the
coverage witness green, because a module-level literal sits outside every
class the walk reads; the historical defect needed the literal written
*into* a class, which is how it was originally found.

**One decision taken and deliberately not extended.**
`tests/test_snag_claims.py` stays the one name in `PRE_CONVENTION`. A
`@pytest.mark.premise` on the sweep would empty that set, and it was
refused: rule 1 is about a drive asserting *the box produced the state it
reads*, while the sweep is a static walk over a source file — so the mark
would discharge rule 2 with a witness about something else, and
`test_live_drive_premises.py` could not tell. Its docstring now says so,
and cites the sweep rather than the retired check as the reason the
exemption is safe.

**One drive-by, caused by the retirement.** Removing the now-unused
`import uuid` from `sysadmin/snag_claims.py` would have deleted a
`# noqa: S404` with it: `897355b` moved that comment off `import
subprocess` when it inserted `uuid` alphabetically on the same line. It
is back on the line it describes.

**Verification.** **3055 → 3056**, +14 and 13 retired with the check,
arithmetic checked against a stashed baseline rather than read off a
green suite. Eleven mutations, each red on exactly the intended test.
Ruff and mypy clean. `sysadmin-check-snags` exits 0 over 18 checks;
`check-ops-claims.sh` is green on all eight claims and reports the
**deploy** state check red — its documented false positive, since
`sysadmin/snag_claims.py` is a console-script module and nothing under
`sysadmin/` imports it, so the daemon serves identical behaviour and was
deliberately not restarted. No production behaviour changed.

**Not done, and not filed.** The estate's message `25be77ba` about 24
broken relative doc links is still open; it was re-measured here and is
accurate to the link (24, across 3 files) but repairing it is the next
action rather than this sitting's, because the fix is a per-link decision
about where each target went and belongs beside its own reasoning.

---

## Session 131b is complete — the exemption that was earned rather than granted

**The decision the handoff asked for was taken per file, and it went five
ways to one.** Four of the six owed a premise and had none; one owed the
**marker and never the premise**; one owes nothing. None of the three
shapes the task listed is what shipped.

**`test_schema_drift.py` is the strongest of the six, and reading it
would not have said so.** Its whole output is `diff == []`. Driven
rather than argued: with `FROZEN_TABLES` widened to cover all **13**
mapped tables — the blindfold that constant's own docstring warns about
— `compare_metadata` returns `[]` as well, so the guard could certify a
comparison it had stopped making and nothing in the file could tell.
`TestThePremises` is the discriminating witness: the same connection and
the same opts pointed at an **empty `MetaData`**, which must report every
live table as `remove_table` — **13 normally, nothing under the
blindfold**. A second, finer premise asserts every *mapped* table is
among them, because reaching one table is not reaching ours; a partial
blindfold turns only that one red, which is what makes the pair fail
apart rather than together.

**The other three, each cheap and each already half-written in its own
file.** `test_schema_guard.py`: both readers answer `None` for a schema
never migrated, so `async_answer == sync_answer` is agreement about
nothing — and `is not None` was already asserted by the sibling test in
the same class. `test_retention.py` owed two, both the silent direction
that module is about: an emptied `TABLE_TIMESTAMP_MAP` parses no
statement, and `configured <= map` holds over a `retention_config` with
no rows (measured: 12 rows against a 12-entry map, coinciding exactly).
`test_logs_routes.py`: `stored <= declared` is green over an emptied
`log_entries`, and the file already argues this way in its
`logging_services` fixture — measured 10 stored inside 15 declared, five
names of slack. `test_open_alert_predicate.py` owed **only the marker**;
its witness is docstringed *"A constant observation is not evidence"* and
predates the convention by a fortnight.

**What shipped is the shape the task did not list, and it is what makes
the decision recorded rather than remembered.** Rule 2's sweep now
accepts a file off the `_live` glob that **marks a premise**, exactly as
a glob member does — so `PRE_CONVENTION` shrank **6 → 1** by five files
holding the property instead of by five names being trusted. The task's
shape 1 without emptying the set; its shape 3 refuted for four of the six
by measurement rather than adopted. Falsified in both directions:
dropping the new clause reports exactly those five, and stripping one
file's marker reports exactly that file.

**Two of the seven mutations demonstrate the vacuous pass rather than
describing it**, which is the part worth carrying. Under the blindfold
the two new premise tests go red and `test_models_match_migrated_schema`
stays **green**. Over an emptied `log_entries` the new premise goes red
while `test_every_stored_source_is_declared` stays **green**. That is the
failure this whole convention is about, produced on demand twice.

**`SNAG-TEST-002` is the one opening and it is the exemption's stated
cost.** `test_snag_claims.py` owes no marker because its premises are
enforced at the **producer** — `query_one`'s every way of not-knowing
returns `unknown` rather than `match` — and every registered check is
driven to that branch by a test in the class that names it, 18 of 18 at
filing. Nothing enforces it. `unknown_branch_unenforced` measures both
halves, refuting the entry from either end (a sweep landing is the fix; a
check losing its `unknown` drive is the premise dying), and **caught its
own author on its first run** by reporting itself as the one check with
no such drive. 19 of 19 once its drive landed.

**Its witness needed the same lesson one level down.** Full coverage is
what the entry rests on and a walk that had stopped reading assertions
reports it too, so the same walk is driven with a verdict spelling
nothing returns. Written as a **literal**, the test asserting that wrote
the sentinel into `tests/test_snag_claims.py`, the walk found it, and two
checks were reported covered by a verdict that does not exist — the
witness refuted by the act of testing it. `_unwritable_sentinel()` mints
one per call, so the zero is by construction.

**One limit is stated rather than filed**, matching this repository's
precedent for a guard's own blind spot: `_opens_a_live_connection` is
syntactic, so a drive reaching the database only through a helper dodges
the property as well as the glob. Population measured at **one** —
`test_snag_claims.py` itself, whose detector hit is a `sync_url` read
that asserts a DSN's shape and never connects, so it is in the set right
by accident. Fixing it is a call graph over `sysadmin/`, which Session
131 refused for its own reasons.

**Verification.** **3033 → 3042 → 3055**, +22 and none retired, checked
against a stashed baseline rather than a green suite. Ruff and mypy
clean. Nine ops claims green after the restart. The daemon was restarted
at **11:48:16** and it was **not owed on the merits** — this sitting
changed tests and `sysadmin/snag_claims.py`, a console script the daemon
never imports — so it clears the mtime comparison and deploys nothing,
which is `ops_claims.py` rule 4's stated cost.

## Session 131 is complete — the sweep that could not have seen it, and the one that can

**The question was answered `no`, and the measurement that answers it is
the pre-fix file itself.** The handoff asked whether `tests/` should
carry an AST sweep refusing a live drive that reads an unsupplied
singleton clock. It cannot exist. `SNAG-TRAY-010` was an **absence**, and
at `62f8e09` — the commit that added the file — `test_desktop_store_live.py`
named `dnd` **zero times**. There is no token whose presence marks the
defect, so the sweep would be hunting a line nobody wrote.

**Three further measurements, each of which alone would have settled
it.** Inverted to *must supply*, the rule is **4 false positives out of
5**: only `test_desktop_store_live.py` touches any of the three
singletons (28 mentions against 0, 0, 0, 0), because two of the drives
are subprocess drives against a real bus with no Python singleton in the
process and two never reach `notifier.py`. Suppressing those needs a
per-file allowlist, which is the hand-maintained classification the rule
was supposed to remove. The read is **transitive** — `datetime.now()`
sits in `dnd.py:73` inside `is_active`, reached as `send` →
`should_suppress` → `is_active` — across **27** unsupplied clock reads in
production, so deciding which a drive reaches is a call-graph analysis
over `sysadmin/`, not a sweep over `tests/`. And `should_suppress`
**already takes a `now=`** it does not forward, so a signature-level
check reads it as injectable and passes.

**The premise assertion is the stronger control, not the weaker one.** A
sweep answers *did somebody write the supply line* and is green forever
once written, including the day the supply stops taking. The premise
answers *is the gate open now*, which is what the hour decides — and
`sent_total > 0` catches the whole class, since `min_severity`, `enabled`
and a future fourth gate silence the announce path identically and no
sweep over test files can enumerate them in advance.

**So what shipped is the narrower guard the decision named**, and it
guards the convention rather than the clocks: `tests/test_live_drive_premises.py`,
15 tests, requiring every `tests/test_*_live.py` to mark the test — or
class — holding its premise with `@pytest.mark.premise`. Seven markers
landed across the five drives at the level each premise actually lives.

**The marker names the check and never the value**, which is
`SNAG-ESTATE-011`'s rule. A name rule was measured first and reaches **3
of 5**: two files carry `test_the_premises_hold_or_nothing_below_means_anything`,
one carries `class TestThePremises`, and the other two neither do nor
should — `TestTheHazardIsReal` names what it *proves*, and
`test_failure_replay_live.py` asserts a different premise per test, so
there is no single test to name. A decorator attaches at the level the
premise lives, which is exactly the three shapes that exist.

**The glob is a convention, so it is backed by a property.**
`_opens_a_live_connection` finds the files that name this box's database
rather than modelling it; **6** hold it outside the glob and sit in
`PRE_CONVENTION`, whose members are re-asserted rather than trusted.
Without that half the premise rule is opt-in by filename — a seventh
drive against the live database called anything else would owe nothing.

**Three things measurement changed mid-build.** The detector **reported
itself**, because it must contain `postgresql+psycopg2://` in order to
hunt for it — `test_open_alert_predicate`'s owner problem one level up,
so the owner is exempted and then driven at, which proves the exemption
necessary rather than assuming it. `addopts = "--strict-markers"` is
**silently ignored on pytest 9.0.2**: the flag refuses a typo from the
command line and does nothing from `addopts`, so a comment claiming it
enforced anything was corrected to the ini option `strict_markers = true`
and pinned by a test that fails if a future edit moves it back. And a
falsification was **destroyed by its own revert** — `git checkout` on an
uncommitted marker reverted the fix rather than the mutation, so mutation
2 silently re-tested mutation 1's condition and a pass was read as a
pass; reverse-patching is what caught it, which is *a harness that cannot
survive the code it drives is a control the next fix breaks* met from the
revert side.

**Seven mutations, each red on exactly the intended test**: drop a
marker, typo a marker, unregister the marker, move `strict_markers` to
`addopts`, add a live-DSN file dodging the glob, break the glob, empty
the DSN hints. **3018 → 3033**, +15 and none retired — arithmetic checked
rather than assumed. No production change; ruff and mypy clean.

**What was deliberately not filed.** The six pre-convention files are a
**task and not a snag**: the convention was invented in this sitting, so
"these predate it" is a decision to take rather than a defect to record,
and filing it would have broken the register's *0 of 18 open entries
carry no check* property without adding a signal. It is the next action
above.

## Session 130 is complete — the leaf that did not look like a clock

**`SNAG-TRAY-010` is fixed, and the entry's own named measurement is what
found it.** The handoff asked for `len(notifier.sent)` in the reading
dict on the grounds that it separates *the sweep never ran* from *it ran
and found nothing due*. It does, and it read **0** — which is reachable
only above `_handle`, so the sweep was never the subject.

**The mechanism is a clock the drive could not see it was reading.**
`tests/test_desktop_store_live.py` supplies **two** leaves and says so in
its own docstring — the transport (a list rather than `notify-send`) and
the two clock readings — and misses a **third**. `DndManager.is_active`
calls `datetime.now()` *itself*, so `dnd_manager.should_suppress` reads
the **real** wall clock whatever clock the notifier was handed. The
shipped `notifications.dnd.schedule` is **`23:00 → 07:00`**, the probes
are raised at `warning`, and `allow_critical: true` does not exempt them.
Inside that window every send is refused.

**Which is why bisecting was a dead end rather than evidence.** The entry
drove it at `62f8e09`, the commit that added the file, and got the same
six — correctly, and that reading is the *reason* it looked like a dead
end. It is not a property of any revision. It is a property of the hour:
Session 129 committed at **05:27** and wrote its handoff at **05:23**.
Re-run at **09:37** on the same tree and the same commit, the file is
**7 passed** with nothing changed. The suite this sitting opened on was
already **3017 green, 0 red**.

**The contradiction in the symptom was the discriminator all along.**
*Silent, yet the rows are stored and adopted* looks impossible, because
`_remember` runs only after a successful `send` — except in `_adopt`,
which writes **unconditionally**. DND gates `_handle` before the send and
the `due` filter before `_restate`, and gates adoption **nowhere**. So
all three probe titles were adopted and stored by a notifier that had
never spoken, and `inherited_adopted: True` is the same fact stated a
second way.

**Proved against the real cause, not a proxy for it.** Three drives at
09:37 on an unchanged tree: `manual_override=True` reproduces the six
failures verbatim, including which six and which one survives;
`manual_override=False` gives seven green; and the **schedule itself**
widened to `00:00 → 23:59` — the actual mechanism — also gives the six.

**The fix is the third leaf, supplied the way the other two are.**
`_hold_dnd_off()` sits beside `standing = understudy.tray_presence` and
uses the manager's **public** `set_manual_override`, restoring **what it
found** rather than `None`. That is not fussiness: the two are different
states (`None` defers to the schedule, `False` overrides it), and a drive
that walked away leaving it forced-off would silence the window for every
test after it in the same process — invisibly, since the effect is a
notification nobody receives. Two repairs were refused: skipping
overnight hides a real regression for a third of every day, and failing
overnight is the entry.

**`sent_total` generalises past its own cause, which is why it is
asserted rather than merely recorded.** Every other "did it speak"
reading is a `bool` over a *slice* of `sent`, so all of them read `False`
whether the sweep found nothing due or a gate above it refused the lot;
the total can tell them apart, because a sweep that merely found nothing
due still leaves the announce-time sends behind it. Driven at
`min_severity: critical` with DND off — a **different** gate in the same
position — it fires. It is asserted non-zero and not as a figure, since
the figure is the roll-up's shape and `first_count` / `second_count`
already own that. `dnd_suppressing` is ordered **ahead** of it so a
failure names the gate: unfixed, the loudest line was `spoke_unwatched is
False`, a sentence about the sweep for a fault entirely above it.

**One thing only the falsification found.** At `min_severity: critical`
the drive **errored** rather than failing — `stored[ANNOUNCED_TITLE]`
raised `KeyError` while *building* the reading, because `_adopt` admits
no rung below the threshold either — so the premise test written to name
the cause never ran and seven errors said nothing at all. It is
`.get`-shaped now. Absent is a reading; a traceback is not, which is this
entry's own lesson arriving inside its fix.

**No production change, and that was checked rather than assumed.** The
daemon's behaviour in the window is correct: a fault raised during DND is
not announced, is adopted by the sweep (which anchors its clock), and
`desktop.py`'s own comment states that a suppressed reminder does not
move the clock — so it speaks when the window lifts at 07:00 rather than
a full interval later. The defect was entirely in what the harness
supplied.

**Numbers.** 3017 → **3018**, +1 and none retired, verified by stashing
to HEAD and re-collecting. Three mutations driven, three killed, each red
on exactly one intended guard. `ruff` clean, `mypy` clean over 95 source
files. All 20 snag checks `ok`, all ops claims `ok`, and closing the one
unchecked entry restores **18 open, 0 unchecked**.

**Not claimed.** No deploy was owed — nothing under `sysadmin/` changed,
so the daemon serves the same code and was not restarted. And the fix is
a harness one: it buys back the control over `SNAG-TRAY-008` that six
standing reds had cost, and changes nothing a user of this box can see.

---

*Previously —*

## Session 129 is complete — the second exception, and the filter it could not fit through

**Ruled: `wiring` joins `ports`.** estate-manager's message `8462bcc5`
(`needs_ruling=true`) put their ADR-0068 §4 condition to this
repository and said in terms that a decline was a complete answer
needing no justification. It is **admitted**, by
[ADR-0006](docs/adr/0006-wiring-joins-ports.md), because every clause of
this repository's own ownership test transfers to
`~/.claude/settings.json` — in **no repository at all** rather than
merely unowned within one, binding all thirteen, unalertable by the
estate, wirable only by the owner (their ADR-0024), read by nothing
here so there is no double-count, and measured by them on 2026-08-29 to
have no consumer anywhere. Declining would have been a ruling made
*against* the test rather than by it.

**The substance is that a one-word yes would have delivered nothing,
and their message could not see it.** The filter is a **conjunction** —
`check == ... and severity == ...` — and `wiring` emits **no `breach` at
any code**, which their own ADR-0067 §4 refuses in terms. So adding
`"wiring"` to a check name judges nothing, for ever, behind a green
suite. Widening `JUDGED_AUDIT_SEVERITY` instead re-imports `ports`'
`claimed_but_silent`, which is availability and already owned here by
`% unreachable`. `JUDGED_AUDIT_CHECKS` is a **mapping** now —
`{ports: breach, wiring: warn}` — the only shape in which both facts
stay true, and `JUDGED_AUDIT_SEVERITY` survives as a name whose value is
**derived** from it, pinned by AST because CPython interns the string
and a value assertion cannot tell derived from retyped.

**Their footnote was load-bearing.** They offered as fact, deliberately
not as a finding, that the comment says "all four" checks emit `breach`
while the audit runs **twelve**. It matters more than that: when every
check emitted `breach`, a single severity constant was unambiguously
deference to the producer's rung; across twelve checks at three rungs it
had acquired a **second job nobody argued for** — it was also a check
filter. The constant was not describing a smaller world, it was doing
undeclared work.

**Driven against the real producer, because the family ships with zero
rows.** `estate_service.audit.checks.wiring.run_check` in their venv, at
their commit `003f3bc` with a clean tree, public symbols only, against
four specimens built from this box's live `~/.claude/settings.json`:
clean → **0** findings; the 2026-08-25 top-level paste → **4**, one per
hook; the truncated paste → **1**; `SessionStart` removed → **1**.
Through this repository's judge: 0, 4, 1, 1 — the last titled `Estate
hook inbox-notice.sh not wired for SessionStart`, which is their §4
condition, spoken. The recording is
`tests/fixtures/estate_audit_wiring.json` and it models the **HTTP**
wire, `code` dropped, not the MQTT one.

**Three things only running it said.**

1. `details['hook']` was right on three specimens in four. On an
   unparseable `settings.json` the producer's subject is the **config
   file's path**, so the key promised a hook name and delivered a file —
   `UnitFinding.enabled`'s trap, caught before shipping. It is `subject`
   now, the producer's own field name.
2. **The partition guard was not a guard for this family.** All four of
   `TestTheSurfacePartition`'s tests passed *before* the wiring titles
   were added to `_every_title`, because nothing produced them — so
   `SURFACE_TITLE_PATTERNS` could have lacked `Estate hook %` while a row
   saying every hook on this box is down sat unresolvable in `alerts`.
   `TestEveryJudgeFunctionReachesThePartitionGuard` makes that omission
   an error rather than a silence.
3. **One falsification passed against deliberately broken code.** The
   `code`-is-never-read test asserted a true premise (no `code` on the
   wire) and a true consequence (the file-level row is still produced)
   and could distinguish nothing: the recorded findings carry no `code`
   at all, so a code-reading judge agrees with a detail-reading one by
   accident. A constant observation is not evidence unless something in
   the population would have forced a different one. It is two tests
   now, the second a **witness** where the signals disagree
   (`code: settings_unparseable` beside `detail: {"event": "Stop"}`),
   and the mutation dies on both parametrizations.

**No roll-up, and that is measured rather than omitted.** The ports
roll-up exists because the port population is unbounded; this one is
bounded by the estate's own `hooks/` directory — four scripts, one event
each — and the collapse case is already the producer's, which
short-circuits an unparseable file to a single finding. A threshold here
would be invented against a population that has never exceeded four.

**`critical` was refused.** An unparseable `settings.json` does take the
blocking `Stop` hook down — the one genuine this-box fault on these five
surfaces, so `DEFAULT_SEVERITY`'s "nothing here is an outage of this
box" is narrower than it reads. It still gets `warning`: `critical`
breaks the DND windows and is what the tray leaves on screen, reserved
for a fault costing something *now*, and a dead hook costs the **next**
session. The estate refused `breach` for this check on exactly that
shape of argument.

**Message `3f2a0e0a` closed too, after re-running its claim rather than
accepting it.** Their rule-3 announcement says this repository's parser
is unaffected by the §2.1/§2.2 edits; driven,
`parse_port_registry` reads **18** claimed rows against the edited
document, with the `health:` markers carried through as ordinary role
prose and the new marker-vocabulary table not mistaken for registry
rows. Their `health` check files nothing about 8500.

**Filed, not fixed — `SNAG-TRAY-010`.** `tests/test_desktop_store_live.py`
fails **6 of 7** here, the premise test among them, and it fails
**identically at `62f8e09`, the commit that added it** — so it is not
this sitting's regression and has never passed in this environment. Not
residue (zero `sysadmin-live-probe%` rows in either table) and not the
D-Bus transport (`send` is stubbed to a list, and the session bus is
live). The mechanism is deliberately not guessed; the entry names the
next measurement, which is the Next action above.

**Numbers.** 2984 → **3017** tests, +33 and none retired, verified by
stashing to HEAD and re-collecting — 90 → 123 in the file, both deltas
33, which is the only arithmetic that can witness a clobber. Twelve
mutations, twelve kills. `ruff` clean, `mypy` clean over 95 source
files. The six reds are `SNAG-TRAY-010`'s and predate the sitting.

**Not claimed, so a later session does not read "admitted" as
"equivalent".** Whether to withdraw their `PreToolUse` carrier is
theirs; and detection is still not delivery — the audit runs daily at
05:00 and this agent polls hourly, so the worst case from a bad
`settings.json` edit to a toast is a little over a day, where the
carrier is immediate. Their §4 accepts that bargain explicitly.

---

*Previously —*

## Session 128 is complete — the sweep knew, and nobody asked it

**`SNAG-ESTATE-009` was taken on its own terms and it stays open.** The
decision asked for was whether a narrower fix than the two refused
closures is worth it. It is — but not a fix for the loud rung, and the
distinction is the whole of this sitting.

**What was built.** `PortAttribution.reading()` answers *what the sweep
knew* beside `of()`'s *who held it*, splitting the four reasons `holder`
is `None` — `held`, `transient`, `unattributed` (the sweep looked
straight at the port and could not name a holder), `unswept` (the sweep
ran before this listener started, which is this entry), `unknown` (no
usable sweep). `judge_audit_findings` puts it in
`details['attribution']` on **every** breach row and in the roll-up.
Live: `of(5432)` and `of(8110)` were both `None` this morning and now
read `unattributed` and `unswept`.

**The discriminator had been in the blob for four months.** `as_blob`
has emitted `unattributed_ports` since Session 26c;
`attribution_from_blob` was written later, for a different consumer, and
never read it. This is the **sibling** of the collapse Session 57 fixed
one field over in the same function — that sitting separated a session
scope from an unattributable socket and left an unattributable socket
indistinguishable from a port nobody looked at.

**A third closure was refused, and on correctness rather than cost.**
Quietening an unattributed breach because the sweep predates it inverts
a posture `_attribution` states in writing: a failed `observe_listeners`
returns **no** listeners, so every port would read unswept and the whole
ports family would drop below `tray.notify_min_severity` — Session
26b-A's founding defect at full scale, arriving as the fix for a
seven-hour window. Both of the entry's named closures still stand.

**Two of the entry's own measurements were refuted by the box.** Its
four historic `warning` rows predate `transient_ports` in the blob by a
day, so they are a missing key rather than a stale sweep and **this
entry has never observed its own class**. And *"the window is six hours
wide"* is the **p90** — 83 inter-sweep gaps in 14 days give a median of
**1.30 h**, because `schedules.agent_first_run_delay_seconds: 60`
re-runs every added job on each daemon start and this daemon's median
life is 1.77 h, so the sweep runs 10–15 times a day against a nominal 4.
Both errors have one root: the mechanism was costed from `config.yaml`
and the code path rather than from `unit_audits`.

**The check was widened before its third limb could be removed, and the
order mattered.** `annotated` compared detail *key sets*, so it caught a
key added to the unswept row alone and was **blind** to the same key
added to every row with a varying value — which is the shape the fix
had to take, since a key present only sometimes is `ports_checked`'s
collapse one level down. Baselined before a line of the fix existed
(`both rows carry the same detail keys: True`), so the check would have
reported `match` over a landed fix, which is worse than flipping.
Widened it answered `mismatch`; the limb then left the **verdict**,
because a limb true from here on can never again say anything about the
window — `a-probe-keys-on-identity-not-a-mutable-field` for the second
consecutive sitting. Narrowed, the check reads `match`, and that is what
says the entry is still open. The test pinning the limb was **inverted
rather than deleted**.

**Options rejected.** Running `ss` in the judge (refused in writing by
`_attribution`) and an hourly sweep (six times the cost, and now doubly
pointless given the measured 1.30 h median) — both unchanged. A judge
that triggers a sweep on seeing an unattributed breach was considered
and refused: it makes the judge own the sweep's lifecycle, the
second-owner defect this repository has found at six scales, and a
genuinely unattributable listener would trigger one on every hourly poll
for ever. Closing the entry was refused because a cost that fell is not
a mechanism that closed, and neither is an annotation.

**What is blocked or owed.** Nothing here. Two estate messages are open
and untouched — `3f2a0e0a` (a `monitorable-project.md` health-path
marker and a new audit check reading this repository's `services.yaml`)
and `8462bcc5` (the `wiring` question above). Neither was absorbed into
this sitting.

**Verification.** 2984 green (2971 at HEAD + 13, none retired), ruff and
mypy clean, all 20 snag checks and the ops-claims checks `ok`. Daemon
restarted at 22:34 and healthy; the estate judge has run twice on the
new code, `completed`, five surfaces read, zero alerts raised — live and
untriggered, since the estate publishes no ports `breach` today. Ten
mutations driven, each red on exactly one intended test, **one having
passed against deliberately broken code first**: the missing-key test
drove a blob with no `ok` either, so the `ok` gate returned before the
branch it names was reached.

## Session 127 is complete — the grace period the box already knew

**`SNAG-TRAY-009` is fixed, and the number the entry called "the real
work" was already written down twice on this box.**

The tray now speaks about a backend it cannot reach, behind a **300-second**
grace: `NotificationPolicy.evaluate_backend_unreachable`, fed by a new
`ApiWorker.backend_unreachable(float)` tick and a tri-state
`_was_connected`. Both faces moved together, because the entry is right
that a fix for one is not half the benefit.

**The grace is `max(3 × status_poll_seconds, 300 s)` and both halves are
borrowed.** The 3 is `self_monitor.stall_grace_multiplier` — one missed
observation is merely late — which `notifications.desktop.tray_grace_seconds`
already applies to a tray poll. The 300 is `min_stall_grace_seconds`,
whose stated reason in `config.yaml` is literally *"so a restart doesn't
flag"* the fastest agent: this family's noise population, one domain over.

**The floor is what does the work, and that is the one decision the
derivation itself could have got wrong.** `status_poll_seconds` is **10**
in the tray's pydantic model and **30** in the shipped `config.yaml`, so
"3× the poll interval" spans 30–90 s — a 3× swing in a number whose job
is to clear a 13-second daemon startup that does not move with the poll
interval at all. The noise is bounded in *seconds* and the observation
counted in *polls*, so the threshold is stored in seconds and the polls
only wake it.

**Two instruments, and they disagree about nothing.** The daemon's journal
holds **104 deploy restarts of 2, 3, 12 or 13 s** in 30 days — max
**13 s**, with the one 276 s window carrying a `-- Boot --` marker inside
it and the six 8.9–12.5 h windows being the box off overnight. The tray's
own journal — its `httpx` line is logged only on a *successful* `/health`,
so a gap inside one tray life is a window in which it polled and got
nothing — holds **27** such windows across 36,240 polls, **every one
exactly 60.0 s**, one missed poll. Nearest real fault: **18,235 s**.
300 s sits *below* the geometric midpoint (487 s) deliberately, because
the cost curve is asymmetric.

**The entry's "multiplicative" was understated — the populations are
*disjoint*.** Both real outages were **arrivals** (tray started 18:34:46
and 14:44:57 against an already-dead daemon), so `connection_lost` never
fired; every window it *did* fire on was a 60 s deploy restart. The
transition signal fired **only on noise and never once on a fault**.

**The check was retired because it had stopped discriminating.** It
answered `match` — "still silent" — against the fixed code. Its Face 1
predicate asked whether the emit sits inside an `if` reading
`_was_connected`, which is `True` before *and* after: the fix keeps the
guard and corrects its polarity, so the defect was the guard's
*reachability*, never its existence. Its "initialised `False`" predicate
matched **two** assignments at HEAD — the initialiser and one inside
`_on_disconnected` — so it was right for the wrong reason and went on
matching the second. The **corrected** predicate is re-homed in
`tests/test_tray/test_backend_unreachable.py`.

**One falsification passed against deliberately broken code.**
`test_the_shipped_file_reaches_the_policy` compared
`load_tray_config(config.yaml)` to the value in `config.yaml` — and the
shipped 300 **is** the model default, so it was green whether or not the
loader ever read the file. Deleting the key from `config.py`'s parse loop
(`SNAG-CFG-001`'s exact shape) survived it. It drives a mutated copy
carrying a witness value now, and "the file and the model agree today" is
a second test rather than the same one. The other 16 of 17 mutations each
landed red on their intended test.

**Driven live, and Face 1 landed at 0.0 s.** Real `ApiClient`, `TrayIcon`,
policy at the shipped 300 s and real `DbusNotifier` on the real session
bus, pointed at a dead `127.0.0.1:8599` — an *arrival*, which is the
population. `connection_lost` emitted on the first failed poll, silence
held through 29.6 / 59.6 / 89.6 / 299.6 s, one non-transient `critical` at
329.6 s, nothing at 359.7 s. Then deployed
(`systemctl --user restart sysadmin-tray.service`) and a real **12.67 s**
daemon restart watched: its polls at 21:32:54 and 21:33:25 both succeeded,
so the window fell entirely between two polls and the tray never saw it —
which is why 122 restarts a month yield only 27 observed windows.

**One claim written in this sitting was wrong and `services.yaml`
refuted it.** The first draft of `tasks.md` filed the tray's own death as
an uncovered gap. It is covered and documented: `monitor: false` with a
stated reason, and the consequence held by `monitor/desktop.py`. All three
directions are now closed — daemon dead → the tray speaks; tray dead →
the understudy speaks; daemon dead at boot with nobody logged in →
`sysadmin-replay-failures` at login.

**Suite 2971** (2937 + 34, arithmetic against the baseline). Ruff and
mypy clean, all 9 ops claims green, 18 open snags each naming a check.

## Session 126 is complete — the room was not empty, it was silent

**`SNAG-SYSD-005` was taken on its own terms and the answer is yes — but
the entry understated its own benefit by two orders of magnitude, and its
framing of the loss was the wrong way round.**

`sysadmin-replay-failures.service` is a **user** unit wanted by
`graphical-session.target`, running `sysadmin/core/failure_replay.py`. It
is the third half of the lifecycle `unit_failure.py` owns: the handler
writes the row while the application is dead, the lifespan closes it when
the application returns, and this speaks the gap between them to the first
human who arrives.

**The entry priced the loss as the gap to the next login; the table prices
it as the life of the row.** It argued from firings — four of five at a
boot with nobody logged in, next login 24 min to 6.1 h away. But `alerts`
holds only **2** `systemd_onfailure` rows for those **5** firings, three
having hit `record_unit_failure`'s dedup branch, and the one row that was
not fixed at once stood open **37.73 hours** (`1 day 13:43:31`). The login
gap is 24 minutes of that. So the replay recovers **37.3 hours of
silence**, not 24 minutes of lateness. Reading the entry gives the
population; querying the table gives the cost.

**And the room was occupied for most of it, which is the finding worth
carrying.** Reconstructed minute by minute: `start-limit-hit` 18:11:15,
login 18:34:41, tray started 18:34:46 — polled 8500, got nothing, went to
`IconState.DISCONNECTED` and sat there. Across two sessions, **22.2 of the
37.7 hours** had a live graphical session with the tray running and
silent; only 15.5 were an empty room. "Four of five fired into an empty
room" is true about *firings* and misleading about *silence*. The real
fault is that nothing on this box interrupts about a dead daemon, occupied
or not — login is merely the cheapest moment to catch it.

**The blocker the entry deferred on turned out not to be one.** It asked
for `--unannounced` at the announcer first, refusing to add a flag with no
reader — correct for a *history* predicate. The replay needs a *state*
one, and the table already answers it: `resolve_unit_failures` has exactly
one production caller (the lifespan, `main.py:244`), `% failed` sits
outside `RESOLVABLE_TITLE_PATTERNS`, and retention purges resolved rows
only. So an unresolved `systemd_onfailure` row already *means* "this unit
has not come back". No flag, no announcer change, and the second-speaker
trap dissolves with it — a state predicate cannot speak about a fault that
is over.

**Waiting is permitted here and was refused in the announcer, and it is
the number that changed rather than the principle.** `SNAG-SYSD-004`
rejected it at notify-send's 60.08 s against a 24-minute gap. At login the
precondition arrives in seconds: measured at the 2026-08-23 session,
`plasma-plasmashell.service` active **14:44:55**, target reached
**14:44:57**, plasmashell still initialising **14:44:58**.
`WAIT_BUDGET_SECONDS` is therefore **derived** — notify-send's own
measured bound, so the replay spends exactly the patience one blocked call
would have spent anyway, on a mechanism that starts no
`plasma_waitforname`. The read comes **before** the wait, so a clean login
costs **0.34 s** and no D-Bus call at all.

**Driven live, three ways.** Clean box: exit 0 in 0.34 s. A real standing
row inserted and removed: the installed unit found it, announced it, exited
0, with the row's own `CAUSE:` line carried verbatim and `Failed 38 hours
ago` added. A private `dbus-daemon`: a server claiming the name at t+2 s is
caught at **3.02 s** and receives the notification intact — `urgency=2`,
`expire_timeout=0`. `alerts` back to **0** unresolved either side.

**Two falsifications passed against deliberately broken code, and the
second was in the harness rather than the subject.** Eleven mutations each
landed red on exactly one intended test. But the live stand-in notification
server printed `claimed` and **owned nothing a millisecond later** — a
`dbus.service.BusName` held only in a local is garbage-collected the moment
the function returns — so the wait reported `False` after a full budget,
which reads as a verdict about the module and was a verdict about the
harness. The first repair was insufficient in the same way: it asserted the
stand-in had *said* `claimed`, which the mutation satisfies. The premise now
asks the **bus** with `busctl` — independent of both the subject and the
harness — and the mutation fails naming the harness. Session 125's own trap
was avoided by construction: a guard mutated to refuse everything turns
**three** live tests red and skips none.

**`SNAG-TRAY-009` is opened at P2 and is the reason for the next action.**
The tray is silent for two *independent* reasons, and they are
multiplicative in `SNAG-AGENT-008`'s sense. `client.py:407`
`_on_disconnected` emits `connection_lost` only `if self._was_connected`,
and `_was_connected` initialises `False` — so a tray starting against a
backend that is *already* dead never emits, which is exactly the
population. And `tray_icon.py:151` `on_connection_lost` only recolours the
icon; there is no path from it to `notifications.py` at all. Fixing either
alone buys nothing. It was filed rather than folded into this sitting at
the owner's direction, because the real work is the noise question: 122
daemon starts in 30 days against one 37.7-hour outage.

**Every open entry names a check again** — 19 open, **0** unchecked. That
property was Session 124's and `SNAG-SYSD-005` broke it on opening;
closing it and opening a checked entry restores it. All 21 snag checks
green, all 9 ops claims green.

2937 tests pass (2899 + 38, none retired — 26 in
`tests/test_failure_replay.py`, 5 in the new
`tests/test_failure_replay_live.py`, 7 unit-file guards in
`tests/test_systemd_units.py`), ruff and mypy clean.

**Restarted at 20:58:45, and owed on the merits** — `unit_failure.py`
gained a reader and `create_app()` imports it. `/health` 200, `alembic
current` 018 at the packaged head, **0** unresolved alerts. The new user
unit is installed and enabled; it goes `inactive` after exit, so the next
login pulls it in again.

## Session 125 is complete — the wait was real and 24× too short

**`SNAG-SYSD-004` is fixed and its open question is settled by counting.**
The handoff asked whether the announcer should fail fast or wait, and that
was a genuine question rather than a rhetorical one: a *pending*
`notify-send` call really is delivered if a notification server appears.
Driven against a private `dbus-daemon`, a server claiming
`org.freedesktop.Notifications` at **t+4 s** received the notification
intact — right summary, right body, `urgency=2`, `expire_timeout=0` — and
the call returned **0**. `plasma_waitforname` does exactly what it is for.

**What kills waiting is the size of the window against the size of the
gap.** notify-send self-bounds at **60.08 s** on an unserved bus, then
fails with `StartServiceByName … Timeout was reached`. After the four
killed firings the next `class=user` login was **24 min 20 s**, **23 min
49 s**, **6.11 h** and **6.10 h** away. Nought of four could ever have
been delivered, and the nearest miss is **24×** the window. The control is
the fifth firing, 2026-08-11 — the only one that completed, with a human
already logged in.

**So the shipped behaviour was never "wait"; it was "hang, then be
killed".** Three bounds and the smallest is systemd's: `TimeoutStartSec=30`
< notify-send's **60 s** < the bus's **120 s** `service_start_timeout`. The
call could not resolve there at any point.

**The mechanism sits a level below what the entry states**, and that is
what made asking the wrong question expensive rather than merely wrong.
`/usr/share/dbus-1/services/org.kde.plasma.Notifications.service` declares
`Exec=/usr/bin/plasma_waitforname`, so a call to an unowned name is not
refused — the bus **starts a program whose whole job is to block until the
name appears**, and that waiter outlives the handler systemd kills.
`scripts/notification-server-present.sh` asks `NameHasOwner` at
`org.freedesktop.DBus` instead, which the bus answers itself: **3.1 ms**
served, **3.8 ms** unserved, and **five calls started zero waiters against
one notify-send's one**. Three verdicts and three exit statuses,
`check-migrations.sh`'s, which the announcer already consumes one function
up. `TimeoutStartSec` stays at 30 deliberately — once the activation path
is refused the only remaining call is `Notify` against a server that
exists, bounded at 25 s by GDBus, and raising the unit's timeout would
re-admit the wait.

Driven end to end against the real script, with only `venv=` stubbed onto
its own documented "alert row not written" branch: **exit 0 in 31 ms** with
the toast on screen, **exit 1 in 15 ms** on an unserved bus naming the
reason. No deploy was needed — the installed unit's `ExecStart` names the
repository path, so writing the file *is* the deployment.

**Two claims made during the sitting were wrong, and both are worth
carrying.** A falsification passed against deliberately broken code:
mutating the guard to refuse *everything* — the silent-forever failure,
which has no symptom because what it suppresses is itself a notification
nobody receives — left `test_it_admits_the_live_bus` **skipping** rather
than failing, since that test asked the guard under test whether a live
server existed. A control a broken subject can switch off is not a
control; it asks `busctl` directly now.

And **`systemctl reset-failed` returning exit 0 was written up here as a
third correction to this repository's `sudo` claims, and it was not.**
Polkit put an authentication dialog on the owner's screen and they
authorised it — invisibly to the session that ran the command, and
reported by the owner mid-sitting. `pkcheck` says `auth_admin_keep`:
admin authentication required *and retained*, which is why the retry
meant to confirm the finding confirmed nothing. **Exit status is evidence
about the result, never about the privilege.** The reads the toast tells a
human to run are still ungated — measured under `env -i` with no session,
`journalctl -u` exits 0 and `systemctl --no-pager status` exits 1 — so the
Session 70 finding stands; only the state-change claim was wrong.
