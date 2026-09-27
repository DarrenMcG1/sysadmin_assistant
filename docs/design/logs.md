# Log aggregation — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**A log is not an incident, and the alert's identity is the fault, not the
source** (Session 42, SNAG-AGENT-005). `LogAggregatorAgent` raised one alert
row per matching log line: **598,091 unresolved rows**, 91 % of every
unresolved alert in the table, of which 99.8 % were two Bluetooth firmware
messages emitted by a kernel retry loop at ~8.5 lines a second. This
application had already recorded the mistake once — *"that table records one
row per failed check — 123 rows for one internet outage"*, in
`GET /api/services/reliability`'s docstring — and not generalised it.

`sysadmin/monitor/log_signature.py` owns the identity: the message with its
variable parts removed (digit runs → `N`, hex → `0xN`, whitespace collapsed).
Four rules, the first of which was the obvious implementation and was refuted
by the live table before it was written:

1. **The key is the signature, not the source.** `Log error: kernel` is
   shared by every kernel error whatever it says, so deduplicating on the
   existing title would have let the Bluetooth storm hold the single open row
   while an RCU stall and a USB enumeration failure — **both in the same live
   30-day window** — went unannounced. Half a million rows traded for a mask
   over every other kernel fault is not a fix. Normalisation does lose
   `error -110` versus `error -71`; nothing is actually lost, because
   `message` carries the last verbatim line and `details['occurrences']`
   carries the count that used to be expressed as row volume.
2. **The signature lives in the title**, not in `details`. Dedup, the resolve
   and the tray's `{severity}:{title}` fingerprint all key on title already,
   so no new machinery is needed and none of them can disagree about
   identity — and four open rows all reading `Log error: kernel` are
   indistinguishable to whoever is looking at the tray.
3. **Silence is the only recovery signal an event has.** `_resolve_quiet`
   closes a row unobserved for `alert_quiet_minutes` (15, i.e. 15 polls),
   excluded by exact title as well as by age because an exclusion set cannot
   race the clock that stamped the row. `COALESCE(details->>'last_seen_at',
   created_at)` is what made the pre-existing backlog reachable at all.
   `details` is *reassigned*, never mutated in place: SQLAlchemy does not
   track mutation inside a plain JSONB dict, so an in-place bump looks like
   it worked, writes nothing, and freezes `last_seen_at` while the fault
   fires.
4. **`_open_alerts` is bounded by the titles the run raised.** Written first
   as "every unresolved row this agent owns" — 593,814 ORM objects on the
   first live run, the fix falling over on the backlog it exists to end. An
   unbounded `SELECT` over the table whose unboundedness is the bug is easy
   to write and nasty to ship.

**Journal reads resume from a cursor, and it must advance over what the
filter discards.** `read_journal` was called with `since="2m ago"` on a
60-second poll, so every unit-journal event was stored **exactly twice**.
`__CURSOR` rather than a narrower window, because narrowing trades the
duplicate for a *gap* whenever a run runs long — the worse failure for a
monitor. The cursor is taken **before** the severity filter: advancing only
past kept entries leaves the resume point behind a run of info-level noise
and rebuilds the defect one layer down. It is in memory, so a restart falls
back to the newest `logged_at` already stored for that source, passed as
`--since @<epoch>` because journalctl reads a bare datetime as **local**
time. The `-n 500` ceiling stays — 8.5 messages a second makes one
unavoidable — but hitting it is now `details['truncated_sources']`, which
**names** the sources rather than counting them, because which one is at its
ceiling decides whether it matters. It was invisible before: `findings_count`
sat at exactly 200 on every run.

**A monitor that only speaks in the present tense makes every recurring
fault look like today's news** (Session 27, Tier 1). `log_signature.py`
gave the aggregator one open row per distinct fault and ended a
598,091-row pile-up; what it could not say is whether a fault is *new*.
`sysadmin/monitor/log_trends.py` is the pure module that can —
`reliability.py`'s shape, for its reason — and `GET /api/logs/trends`
computes it live in **88 ms**.

Four rules, three of them the opposite of the obvious implementation and
all four settled by the live table rather than by argument:

1. **The signature is applied in Python, over rows the database has
   already grouped.** Normalising in SQL with `regexp_replace` is a
   second implementation of the identity the *alert* family is keyed on,
   and it drifts exactly as a regex over `alembic/versions/*.py` drifts
   from the revision graph. What makes the honest version affordable is
   measured: **626,906 rows collapse to 44 distinct messages in 91 ms**.
   The reduction is a property of this data, not a bound — a service
   embedding a request id in every line has one group per line — so the
   caller caps the set and reports `truncated`. Note the
   anti-correlation: the messages that do *not* collapse under `GROUP BY
   message` are the ones the signature helps most.
2. **"New" is a first sighting, measured against all retained history.**
   `previous == 0` was the obvious test and one live row refutes it: the
   Bluetooth firmware signature reads `current=39,919, previous=0` and
   has been storming since 2026-07-15, so it would have headed "new
   errors this week" on its fifth outbreak. It comes out `returned`. The
   8 genuinely-new signatures include `Bluetooth: hciN: failed to reset
   (-N)` — a *distinct* signature a source-level key would have masked.
3. **A gap lowers confidence and never becomes a trend** —
   `reliability.py`'s rule 4 — but **truncation is the signal and poll
   count only the proxy**, which is the reverse of the obvious ordering.
   A missed poll is caught up by the journal cursor, so data is lost only
   when a catch-up read hits `max_entries_per_read`, which the agent
   already records as `details['truncated_sources']`. Counting polls
   alone charges a fully-recovered gap as data loss. **Decisive in
   proportion, not as a flag** (Session 63): the gate is
   `TRUNCATION_LOW_FRACTION` over the *instrumented* reads, and it can
   exist at all because truncation is **one-directional** — it drops
   entries, so it only ever makes a count too low. `HIGH` is untouched
   and still means nothing was lost; only the floor beneath it moved.
4. **Counts are never scaled by coverage.** The cursor makes ingestion
   non-proportional to poll count, so a rate computed from observed time
   looks precise and has a divisor wrong in an unknown direction.

The population is **wider than the alert family's** — `warning` too,
because Tier 2's whole question is about a warning.

**Advice has to be executable, and this is the first sitting here to
build the mechanism a recommendation names** (Session 27, Tier 2).
`sysadmin/monitor/log_actions.py` ranks `new_signature` → `surge` →
`noise`, kind before volume, with no invented number merging them —
`FileRecommendationInfo`'s ordering, and its currency argument one step
further: `occurrences` is a third unit, so it is a third model rather
than a third meaning for `points`.

Tier 2's scoped example — *"this warning appeared 400× — add to
known-noise or fix it"* — named a list that did not exist, which is
Session 48's defect in advance: a row saying "paste the snippet below"
with no snippet is an item no execution sitting can close.
`agents.log_aggregator.known_noise` is that list. Four rules:

1. **Keyed on `(source, signature)`, never the signature alone.**
   `Failed with result 'exit-code'.` is logged by six services on this
   box; declaring it noise on the strength of one silences a genuine
   failure in five.
2. **Quietened, never suppressed** — `info`, the only rung below
   `tray.notify_min_severity` here, the same derivation as
   `judgements.TRANSIENT_HOLDER_SEVERITY`. The row still exists, still
   counts occurrences, still appears in the trend. Dropping it rebuilds
   `SNAG-CFG-001`'s shape: a decision taken by a consumer with nothing
   recording that it was taken. `reason` is a required *field* rather
   than a YAML comment, because an endpoint serves it back.
3. **Nothing is recommended as noise on volume alone, and a `LOW`
   confidence report recommends none at all.** Volume is what makes a
   fault worth looking at, not evidence it is harmless — so a `noise`
   row also requires the signature to be old and flat, or the endpoint
   recommends silencing an outage on its second day. The confidence gate
   is asymmetric: `new` rows survive a gappy series, because a gap can
   hide a fault and never invent one.
4. **The quietening reaches a row that is already open**, which
   `SNAG-ESTATE-010` said nothing did until this rule was lifted out of
   here into `core/escalation.may_quieten_in_place` on 2026-08-28 — and
   this family cannot wait it
   out, since a signature loud enough to declare is by definition one
   that never goes quiet, so its row never resolves. Session 39's ban on
   in-place severity changes is **asymmetric and that is what rescues
   it**: an escalation must be *heard*, so an in-place bump keeps a
   fingerprint the tray has suppressed; a quietening must be *silenced*,
   and `{severity}:{title}` becoming `info:…` is dropped by `_consider`
   before it can notify. The mechanism that makes escalation fail is what
   makes this work, so it is one-directional by construction.

**Three of the emitted commands did not work, and only a live run said
so.** The draft emitted `journalctl -u kernel` (the kernel is not a
unit — `read_journal` has always known that, so the same fact was stated
twice and one was wrong), omitted `--user` for the **7 of 14** declared
sources that are user units (measured by running both: 2,170 lines with
the flag, 1 without), and grepped on the *normalised* signature, whose
`N` placeholders match no real line and whose first token is usually the
unit's own name. `journal_command` fixes all three and the docstring
carries why, because the fixtures were green throughout.

Two limits were filed rather than implied. `SNAG-LOG-001`: one mosquitto
crash produced four recommendations, because systemd narrates it in four
lines that are four genuine signatures — a cap would hide the fourth
without saying the four were one thing, so the real fix was a correlation
rule nobody had measured. `SNAG-LOG-002`: the `noise` family had an
**empty population on this box**, because 118 truncated runs made
confidence `LOW`.

**The correlation rule exists now, and the relation it keys on is
systemd's, not the clock's** (Session 68, `SNAG-LOG-001` closed).
`log_actions.group_incidents` collapses first sightings that share a unit
**or a declared systemd dependency** inside `INCIDENT_WINDOW_SECONDS`,
and `units/scan.py` supplies the graph: `UnitFile.relations` and
`declared_relations()`, off the same files the sweep already opens. Live,
`GET /api/logs/actions` went **24 → 11** and the specimen's six rows
became one, naming all six signatures and emitting one `journalctl -u … -u …`
that was run and works.

Five rules, four of them the opposite of the obvious implementation and
every one settled against the live box rather than by argument:

1. **The declared graph is enough, and the interesting measurement was
   *which directories*.** `mosquitto.service` is packaged, so
   `discover_units` excludes it as distro-owned and its file sits in
   `/usr/lib/systemd/system`, which the sweep never walks — so the
   obvious move was to widen the walk. **Parsing `/usr/lib` as well reads
   629 further unit files and yields zero further relations** between the
   fourteen declared log sources, because a relation is declared by the
   unit that *depends* and on this estate that unit is always the
   hand-written one. `scan.py`'s no-subprocess promise was never in
   question; the effective graph `systemctl list-dependencies` resolves
   was not needed.
2. **The graph is the filter and the window only bounds it.**
   `alfred-backend.service` failed **1.2036 s** after the crash — inside
   any usable window — because PostgreSQL was still starting up, and
   `sportsanalyser-backend.service` failed **2.9 s before** it. Neither
   is reachable by a clock and both are excluded by the graph. Driven as
   a counterfactual rather than asserted: forging one edge admits
   alfred-backend, and removing the graph reproduces the entry's own
   proposal exactly.
3. **One hop, never transitive closure.** Six user units here declare
   `After=network-online.target`, so a second hop makes every
   network-using service one incident and the rule degenerates into
   "same window", which rule 2 has just refused.
4. **Every member is measured against the anchor, never the group.**
   Single-linkage lets a chain walk arbitrarily far from where it
   started, so a service retrying every 5 s would grow one incident
   across a whole outage. The anchor is the earliest first sighting,
   which is also what an incident *is*.
5. **First sightings only, so the roll-up's rung arithmetic is
   vacuous and says so.** `first_seen` is an incident moment only for a
   first sighting; a `SURGED` signature's is weeks old, and grouping
   surges on `last_seen` instead would put every active surge in one
   "incident". Every member therefore shares one kind, so
   `judge_attention`'s "take the loudest rung you swallow" has nothing to
   decide — absent because vacuous, not because forgotten. The rule is
   observable only at the window's edge, and that is where it is tested.

`INCIDENT_WINDOW_SECONDS = 5.0` is **derived, and what was derived is a
gap rather than a number**. Across the 21 live first sightings the
separations are bimodal with nothing between them: every
genuinely-one-incident pair lands inside **349 ms**, and the nearest
genuinely-two-incidents pair is **64.4 s** apart. Every value between
produces identical output, so the geometric midpoint sits three orders of
magnitude from anything it could get wrong — unlike
`NOISE_MIN_OCCURRENCES`, which is invented and says so.

The roll-up **names every signature it swallows** and truncates each to
`SIGNATURE_DETAIL_CHARS` instead — `SNAG-ESTATE-001`'s rule, since
dropping a member rebuilds the count that cannot name anything, while
shortening one does not. `LogRecommendationInfo.source`/`.signature` stay
the **anchor's** rather than becoming lists, so a consumer ignoring
`members` still gets a correct row about the fault that happened first.

Three things the sitting corrected in what was written down. The entry's
stated **mechanism was backwards**: systemd started the oneshot **2 ms
after** mosquitto had already failed, because the relation is `Wants=`,
which does not propagate failure — the provisioner then failed on its own
connect. The whole window is a **boot** beginning twelve seconds earlier,
which nothing in three sittings had noticed and which is exactly why a
same-window rule is dangerous here. And the rule collapses
`sysadmin.service`'s raw-JSON rows from **10 recommendations to 3**
(`SNAG-LOG-008`), seven of them one agent run's alerts inside 1.7 ms —
a byproduct that does not close that entry, which is about the signatures
being unreadable rather than about how many rows they occupy.

Two costs are filed rather than implied. `SNAG-LOG-009`: `journal_command`
formats a UTC-rendered timestamp into a `--since` journalctl reads as
**local**, so every command is an hour early here and would be five hours
*late* — missing the incident entirely — west of Greenwich; found by
running what the new row emits, Session 27's rule catching a fourth
command. `SNAG-UNITS-006`: `discover_units` skips `*.service.d/`
directories, so a relation added by drop-in would silently fail to
correlate — empty population today, measured, since neither of this box's
two drop-in directories belongs to a unit the sweep sees.

**The first of those is fixed, and the fix was already in the repository
one module over** (Session 71, `SNAG-LOG-009`). `journal_command` now
takes a **`datetime`** rather than a rendered string, and
`journal.since_timestamp` — which has emitted `@<epoch>` and stated this
exact reason since the module was written — owns the rendering. So the
defect was never a missing conversion: three callers each formatted
`f"{first_seen:%Y-%m-%d %H:%M}"`, implementing a fact a fourth function
already owned, which is the `-k` bullet in `journal_command`'s own
docstring met from a third direction. Taking the *type* is what makes a
fourth caller impossible rather than merely unlikely.

Four rules, three of them corrections to what the entry proposed:

1. **`astimezone()` was the weaker fix and would have shipped green.**
   It renders a *local* wall clock — correct on this box, verifiable,
   and still ambiguous: right only while the process writing the command
   and the human running it share a zone, and an autumn-fold local time
   names two instants. `@<epoch>` carries no zone at all, so it is
   unambiguous rather than merely correct here.
2. **The tests were what hid it, so they now model the consumer.**
   `TestJournalCommand` pinned the *rendering*, which is how a wrong
   command stayed green across three sittings; `_journalctl_reads`
   resolves the emitted argument the way journalctl does — `@<n>` as an
   instant, anything else as the reader's local clock — and the same
   assertion runs in London, New York and UTC. All four new tests were
   falsified against the behaviour they replace, the truncation-direction
   one needing its own (`int` → `math.ceil`, which opens the window 1 s
   *after* the event).
3. **`since_timestamp` refuses a naive datetime.** `timestamp()` reads
   one as local, which is precisely the reading being removed, so
   accepting it would rebuild the defect inside its own fix with the
   right-looking type — `schema_guard`'s fail-closed posture, not
   `collation.py`'s. Empty population by construction: every caller
   reads `logged_at`, a `timestamp with time zone`.
4. **The prose is labelled, never converted.** `detail`'s "First seen …"
   and the incident line's "within Ns of …" render the same instant the
   command points at and now say `UTC`, so the fix leaves no row
   disagreeing with itself. Rendering them *local* was refused: the
   command had a timezone taken out of it, and putting one back beside it
   is the opposite direction — and the label agrees with
   `GET /api/logs/trends`, which serialises `first_seen` with a `+00:00`
   offset.

Measured at two timezones rather than reasoned about. The specimen is
stored `2026-08-22 18:10:16.115268+01`; the emitted `--since
'@1787418616'` resolves to exactly that. On this box the old form lost
**one** line, which is the trap stated precisely — BST makes the error
*widen* the read, so the box that would notice is the one that never runs
the command. Re-run under `TZ=America/New_York` the epoch form is unmoved
at **57,695 lines** and the wall-clock form returns **48,946**, opening
`17:10:00 -04:00`, four hours past the incident and without it. The rule
is *N* hours late at UTC−*N*, so the entry's "five hours" is EST and four
is EDT.

**A row's identity is the fault, not the source — and the advice endpoint
was the last surface where it was not** (Session 72, `SNAG-LOG-010`).
`SNAG-AGENT-005` moved the signature *into* `alert_title` because four
open rows reading `Log error: kernel` are indistinguishable to whoever is
looking at them. Every title in `log_actions.py` was still built from
`source` and a number, and sibling rows share both: live, `GET
/api/logs/actions` served two rows reading exactly `kernel: 39885
occurrences, unchanged`. `quoted_signature()` now appends the signature
to all four, bounded by `capped_signature()` at `SIGNATURE_DETAIL_CHARS`
with `truncate_at_word`, and `log_review._quoted_signature` keeps only
its `figure_free` gate and borrows the rest — so a review line and an
advice title cannot write one signature two ways.

Four things settled by driving the producer rather than reading it:

1. **The family the entry named is the smallest of the three affected.**
   It scoped the defect to `noise` and ranked it last on "population is
   currently zero". At the 2026-08-12 anchor **14 of 21 rows collided in
   five groups**; at the live anchor the `noise` population genuinely
   *is* zero and **7 of 9 rows still collided**, all `severity: risk`.
   Reading the code confirms the entry; running `recommend()` against
   the live table refutes it.
2. **The cut is marked now, and it was the module lending the constant
   that was slicing.** `log_review._quoted_signature`'s docstring says
   an unmarked cut is `SNAG-BRIEF-002` and is *worse* on a signature,
   because a reader may try to match it against `GET /api/logs/actions`
   — which is this module, which was cutting **12 member signatures
   per request** mid-word, one ending `"message": "alert_raised",
   "service"`. `SAMPLE_DETAIL_CHARS` names the second bare slice, which
   had been written twice.
3. **The noise title claimed a direction it could not know.**
   `unchanged` was asserted for all four change kinds
   `_is_noise_candidate` admits, and the live pair classifies `FALLING`
   — 39,885 this window against 77,496 last — so the title asserted
   flatness about a signature that had halved while its own `detail`
   printed the contradiction. The count stays, because Tier 2's question
   is about volume; the direction goes, because `detail` states it and
   `change` decides it.
4. **The cost is `SNAG-LOG-008` becoming visible, and it is the trade
   `alert_title` already made.** Four of the nine live titles now open
   with `{"timestamp": "N-N-N …`, and an ugly title a reader can tell
   apart beats a tidy one they cannot — `SNAG-LOG-003` paid this exact
   price for the alert family. What the cap leaves is `SNAG-LOG-013`: 9
   of 55 signatures share their capped prefix and one live incident row
   lists **7 members identical after capping**, which is the roll-up
   naming nothing one level below the titles. Its population empties by
   retention the same afternoon it was filed, and the entry says so —
   because "population is zero" is what mis-ranked its parent.

Note what was pinning the titles: one assertion,
`rows[0].title.startswith("New fault from")`, which the defect passes
intact — `TestJournalCommand` one sitting over. All nine new tests were
falsified against the behaviour they replace, and one had to be
strengthened before it could be: it compared the two modules' quoting on
a *short* signature, where a slice and a marked cut agree, so it passed
against the broken code.

*That entry named the wrong culprit and Session 60 corrected it against
`agent_runs`: the 118 are **kernel 103, sysadmin-service 14** out of
**10,064 runs**, and **104 of them fell on one day**, 2026-08-12. Since
`_confidence` is `runs_truncated > 0` — binary, not proportional — the
family is available only between kernel storms, and the volume fix below
did not close it.*

**The ceiling counted the wrong lines, and the number was never the
problem** (Session 62, `SNAG-LOG-002` ceiling half). `read_journal`
bounded the read with `-n 500` and then applied `severity_filter` in
**Python, over lines the ceiling had already counted**. Across the
2026-08-12 storm: **203,042 raw kernel lines carrying 81,216 storable
ones — 40 %**, a median of **510 raw a minute against a ceiling of
500**, so **208 of 210 storm minutes truncated** and the 100
instrumented storm minutes produced **103 truncated reads, one per
poll**. Passing `-p` to journalctl makes the same 500 carry 500 storable
entries: verified against the real journal, the stored multiset is
**identical** and efficiency goes 40 % → 100 %, so the effective ceiling
rose 2.5× with **no edit to `max_entries_per_read`** — raising it would
have bought the same headroom at 2.5× the memory and left the waste.

Four rules, three of them the opposite of the obvious implementation:

1. **`max_priority_for` is derived from `PRIORITY_MAP`**, never written
   beside it — `syslog_priority`'s rule and `chk_alert_agent` against
   `AGENT_NAMES`. `journalctl -p N` admits `0..N`, which is
   `SEVERITY_ORDER`'s "this rung and every louder one" read the other
   way, so the two compose with no conversion anyone has to remember.
2. **The Python filter stays and is still the authority.** `-p` exists
   to make the *ceiling* count entries that matter; deleting the filter
   would make journalctl's reading of a record the only one, and an
   unknown filter string must narrow both sides identically or a typo in
   `services.yaml` silences a source for a reason nothing reports.
3. **The cursor rule is kept as written although `-p` dissolves it.**
   Advancing over every entry *read* now coincides with advancing over
   every entry kept, because the noise is no longer returned — so
   collapsing them would make dropping `-p` silently rebuild the
   duplicate-ingest defect.
4. **The ceiling was not raised.** The catch-up path is what remains,
   and no ceiling reaches it: `_resume_floor()` sets the window to how
   long the daemon was down, so one restart behind a backlog truncates
   at any limit. `truncated` now means *relevant* data was lost rather
   than "the read was busy", which is the stronger signal it was
   claiming to be.

**This does not close `SNAG-LOG-002`, and the fix that was going to was
refuted by measurement.** Per-source confidence produces **zero** noise
rows — driven through the real `_build_trend_report` → `recommend()`
against the live database — because the entire noise-eligible population
is two kernel signatures at 39,920 apiece and kernel holds **103 of the
120** truncated runs, while the eight sources it liberates have a
loudest signature of **54** against `NOISE_MIN_OCCURRENCES = 100`. It
would also have failed **silently**: `details['truncated_sources']` keys
on the `services.yaml` **name** and `log_entries.source` on the **unit**,
and `kernel` is the only string in both — so the obvious join reads the
eight as untruncated and kernel as truncated, wrong in both directions
and green. `_log_source_scopes` carries that same warning one function
over. What remained was the **binary** flag, not the global one.

**That flag is gone, and the mechanism everyone had written down for it
was wrong** (Session 63, `SNAG-LOG-002` closed). One catch-up read pinned
the report `LOW` for fourteen days, so `GET /api/logs/actions` served
zero `noise` rows against two signatures at 39,921 apiece.
`_confidence` now gates on `truncated_fraction >
TRUNCATION_LOW_FRACTION` (0.05) over the **instrumented** reads; live,
that is 120 of 7,006 — `medium`, and the two rows appear.

Four rules, three of them corrections to what was believed before the
measurement:

1. **`_resume_floor()` sizes a catch-up read by how long since that
   source last *stored* a row, not by daemon downtime.** A source
   logging one warning a week is read a week back on every restart,
   which is why 16 of the 120 truncations each name four or five sources
   at once — every one of them the first poll after a restart, ~62 s
   after `Started SysAdmin…`.
2. **So the ceiling fix does reach them**, against the entry's claim
   that no ceiling could: `-p` spends the 500-entry budget on storable
   entries, and a week-long window on a quiet source holds about one.
   Measured on one box in one hour — the 13:17:05 restart's poll
   truncated 4 sources, the 14:10:58 restart's poll truncated nothing.
3. **The denominator is the instrumented runs, never the observed
   ones.** `details['truncated_sources']` first appears 2026-08-12
   17:31, so 10,724 of the window's 17,730 runs could not have reported
   truncation; dividing by all of them reads 0.68 % against a true
   1.71 %. It self-corrects as those runs age out, which is precisely
   why leaving it was not an option — a number wrong today and right
   next week is one nobody re-checks.
4. **A threshold is legitimate because truncation is
   one-directional.** It drops entries, so a `noise` row's "this is
   loud" is a floor the missing data cannot undercut — rule 4's `NEW`
   asymmetry one step further. What the threshold bounds is not the
   volume error but the chance a depressed *current* window moves a
   `SURGED` signature into the noise-eligible `STEADY` band. Both live
   rows were `RETURNED` with `previous = 0` when this was written, so no
   ratio was computed for either. **That is a property of the window,
   not of the pair, and it has already moved**: at a window covering the
   2026-08-12 storm they are `FALLING`, 39,885 against 77,496 (measured
   2026-08-24). The argument is unaffected — a `FALLING` row is
   noise-eligible too — but a sentence in the present tense about which
   rung two live rows sit on goes stale faster than the rule it
   supports.

`truncated_fraction` **fails closed** — `schema_guard`'s posture, not
`collation.py`'s — so a caller with no denominator gets `1.0` and the
binary behaviour back. That is why all 1,984 tests passed on the first
run after the change, and why the guards were falsified deliberately:
`TRUNCATION_LOW_FRACTION = 0.0` restores the old rule *exactly* (it is
the limit case, not a replacement) and breaks precisely the four new
tests.

`read_journal` also gained its **first direct tests**. Every existing
test patches it out, or asserts `journal_command` — the invocation a
recommendation tells a *human* to run — so the command this module
actually executes was unasserted, which is how the ceiling came to bound
raw lines for the life of the module.

**A logger that is not the one you configured writes the line anyway**
(Session 60, `SNAG-AGENT-008` volume half). `configure_logging` clears
the **root** handlers, which does not reach `uvicorn.access`: uvicorn's
dictConfig attaches a handler to that logger *directly* and sets
`propagate = False`, so it sat outside every switch this module throws
and wrote a plain-text copy of every request beside the middleware's
JSON one. Measured over ten minutes: **662 plain against 640 JSON**, and
662 − 640 is exactly the **22 `/health` polls** `_EXCLUDED_PATHS`
suppresses — so `SNAG-API-002`'s fix had never once worked. Note what
could not have caught it: `test_excludes_health_endpoint` patches
`sysadmin.core.middleware.logger`, the emitter that was already
honouring the exclusion.

Three rules. **The structured copy is the one kept** — only it carries
`method`/`path`/`status`/`duration_ms` as fields rather than prose to be
parsed back. **Disabled, not re-levelled**: uvicorn logs access at INFO
and nothing else, so `setLevel(WARNING)` is silence spelled indirectly
and starts emitting again the day uvicorn adds a warning-level access
line. **Silenced, not redirected** — removing the handler and letting
the record propagate keeps the duplicate and merely re-dresses it as
JSON, which is the same line count in the journal and the line count is
the number being moved. A test drives uvicorn's real `LOGGING_CONFIG`
rather than a reconstruction of it.

**The other half of the same blindness is the level, and the trade-off
this repository had written down was wrong** (Session 61,
`SNAG-AGENT-008` priority half). systemd stamps captured stdout
`PRIORITY=6` whatever the `"level"` inside the JSON says, so
`read_journal`'s `severity_filter: warning` discarded every line this
daemon has ever written and `log_entries` held **0 rows** for
`sysadmin.service` across nine nights of `ERROR`. The snag said the two
unit-file remedies both need `sudo`, leaving a reader-side parse as the
only cheap option. `SyslogLevelPrefix=` **defaults to true** in systemd
and already read `yes` here — so the prefix costs no unit edit and no
`sudo` either. A trade-off written from documentation rather than from
the box had sent the choice toward the weakest of three.

`JournalLevelPrefixFormatter` prefixes each JSON line with `<N>`.
Journald strips it, so `MESSAGE` is byte-identical and `log_signature`,
`alert_title` and `raw_line` need no change — verified against a
transient unit before the code was written.

Four rules, three of them the opposite of the obvious implementation:

1. **The producer, not the reader.** Parsing `"level"` in
   `read_journal` fixes this repository's view and leaves the artefact
   lying: `journalctl -u sysadmin -p err` still prints nothing, and so
   does any `OnFailure=` hook. It also puts a special case for **one**
   source into a reader serving fourteen — and `sysadmin.service` is the
   only JSON-writing journal source on this box, measured, so the branch
   could never pay for itself.
2. **The JSON gate is a precondition, not a proxy for the destination.**
   A level prefix marks one line, and only the JSON formatter guarantees
   one line per record. Under the text formatter a traceback's first
   line would be stamped `ERROR` and its body left at `info` — one fault
   across two priorities, worse than the uniform `6` because it *looks*
   fixed.
3. **`uvicorn.error` is rerouted, not silenced** — deliberately the
   opposite verb from `uvicorn.access` three lines up in the same
   function. It has no handler and propagates only as far as `uvicorn`,
   which keeps a plain-text handler with `propagate = False`: the access
   logger's shape exactly, carrying `Exception in ASGI application` and
   every unhandled 500. The access line duplicates a structured line the
   middleware already writes, so the second copy is waste; uvicorn's
   error line has no second copy anywhere, so silencing it would delete
   the only record an ASGI crash leaves.
4. **`syslog_priority` is pinned to `journal.PRIORITY_MAP` by a
   round-trip test**, not asserted alone on each side — two maps that
   can disagree about one fact is `SNAG-DB-003`'s shape and
   `chk_alert_agent` against `AGENT_NAMES`.

Note what was asserting the opposite and passing.
`test_only_the_access_logger_is_silenced` (Session 60) claims
`uvicorn.error` reaches the root handler; its fixture rebuilds
`uvicorn.access` and **not** its parent, so the record fell through to
root in the test and went to uvicorn's own handler on the box. True in
CI, false in production — `test_excludes_health_endpoint`'s defect one
logger over, shipped by the session that found it.

`SNAG-LOG-003` was the cost, filed rather than bundled: `MESSAGE` for
this source is the whole JSON line, so `alert_title` yielded a
252-character title made of JSON that reaches a notification body
verbatim.

**Trying to test that fix against real rows found a P0 underneath it**
(Session 64, `SNAG-LOG-004`). `journalctl -o json` substitutes `null`
for any field over ~4096 bytes unless **`-a`** is passed, and
`read_journal` never passed it — so `MESSAGE` came back `None`,
`entry["message"][:5000]` raised `TypeError`, and the whole
`log_aggregator` run died, every source in it. **Self-sustaining**: the
failure is written by `logger.exception`, itself a >4096-byte line at
`ERROR`, so the next poll reads *that* and crashes again. All **215
historic `agent_run_failed` lines are 12,837–12,845 bytes**.

Four things worth carrying forward:

1. **The previous fix armed it.** These lines were `PRIORITY=6` until
   the 14:10:58 restart, so `-p 4` excluded them and 40,228 runs had
   never failed. Measured at the moment of the fix: **0 error lines and
   146 clean runs since the restart** — live and untriggered. A fix that
   widens what a monitor can see is a regression surface for whatever
   consumes it.
2. **Reachable only for a source that puts a long record on one line.**
   A Python traceback from any other service arrives as many short
   journal entries; `JsonFormatter` folds `exc_info` into a single
   `MESSAGE`. Same "only JSON-writing journal source on this box" fact
   Session 61 used, read the other way.
3. **It is the JSON serialiser's cap, not journalctl's reading.** The
   same records print in full under the default text output (11,572 and
   12,164 characters), so `journal_command` — the invocation a
   recommendation hands a human — needed no change, and that was checked
   rather than assumed.
4. **No fixture could have caught it.** Every existing test patches
   `_run` with a stub returning hand-written JSON, so `MESSAGE` was
   always a string somebody had typed. `test_excludes_health_endpoint`'s
   defect one module over.

`message_text()` sits behind `-a` for the one shape `-a` introduces — a
non-UTF-8 field, rendered as an array of byte values rather than as
`null`. Empty population here (205,298 kernel records over seven days,
all `str`), kept because the shape is journalctl's to choose.

**Then the declaration, which is the reader honouring a statement rather
than recognising an application.** `LogFormat = Literal["text", "json"]`
sits on `sysadmin/core/config.py`'s `LogSource` — one vocabulary, since
both files funnel into it — and `read_journal` applies
`unwrap_json_message` only where a source declares it. Measured over the
**723 real `ERROR` lines**: 6 distinct titles of 242–253 characters of
JSON become **5 of 46–151 readable characters**.

Four rules, three of them the opposite of the obvious implementation:

1. **It fails open at every step, and the reason is measured rather
   than cautious.** systemd writes its **own** plain-text lines into a
   unit's journal at error level — `Failed to start SportsAnalyser -
   Frontend (Next.js).` appears **668 times** live, nine distinct such
   messages exist — so a declaration that discarded non-JSON would
   silence exactly the line saying the service died. A declaration
   describes what the *application* writes; it can never describe
   everything in the journal it writes to.
2. **Severity is not taken from the envelope.** `"level": "ERROR"` sits
   beside the message and is ignored, because the level prefix already
   put it in `PRIORITY` — two statements of one fact that can disagree,
   `max_priority_for`'s rule — and only the prefix reaches `journalctl
   -p err` and `OnFailure=`.
3. **`logger` goes to metadata, never into the title.** The old key's
   sixth title was a *fork*, not a distinction: `sysadmin.core.scheduler`
   and `sysadmin.services.scheduler` emit the same
   `scheduler_job_error` and were split only because the module path
   fell inside the 252 characters truncation left. Putting `logger` back
   in the title would rebuild that by design.
4. **The two declarations are pinned, not restated.**
   `service.log_format` decides what this process emits and
   `log.format` how the reader parses it; they live in different files,
   so a test asserts they agree — keyed on `OWN_UNIT` rather than the
   historical `name`, and paired with one asserting no other source
   declares a format, which is the measured claim the whole design rests
   on.

`raw_line` still holds the journalctl record verbatim, so the unwrap
moves what identity is built from and never what is retained. The stated
limit: `agent_run_failed` is written by all five agents, so five
failures share one signature — not a regression, since the truncated
JSON title cut at `"servic` and never reached the `agent` field either.

The fixture was the thing that had to change. Twelve tests built a
`SimpleNamespace` stand-in for `LogSource` and broke on `source.format`;
`getattr(source, "format", "text")` would have made them pass while
swallowing a genuine wiring failure, so the fixture constructs the real
model instead — `UnitFinding.enabled`'s trap answered on the correct
side.

**A declaration applied at read time cannot reach a row already stored,
and the repair reads the column the reader read** (Session 116,
`SNAG-LOG-008`). Ten `sysadmin.service` rows kept the raw envelope in
`message` because they were ingested before the declaration existed;
`signature()` and `alert_title()` are both computed from `message`, so
`GET /api/logs/trends` served ten unreadable signatures.
`sysadmin/monitor/message_backfill.py` is the second caller of
`unwrap_json_message` — the one the entry named as its own refutation —
and `sysadmin-backfill-messages` the console script over it.

Six rules, four of them the opposite of what the entry proposed and every
one settled against the live table rather than by argument:

1. **The new message is derived from `message`, never from `raw_line`.**
   The entry asks for the reverse and prices in `raw_line`'s
   2000-character truncation as the reason a backfill "is not free".
   Read what `read_journal` composes: `message = message_text(MESSAGE)`
   **first**, then `unwrap_json_message` on that same string only where
   the source declares it. A `text`-declared row's stored `message` is
   therefore exactly the unwrap's input, so applying the unwrap to it
   reproduces the `json` read by construction, while going through
   `raw_line` re-implements `message_text(json.loads(line)["MESSAGE"])`
   — a second statement of the reader's own parse, free to drift from
   it. The two derivations agree **10 of 10**, so the cheaper route is
   also the exact one.
2. **`raw_line` earns a different job instead: the *witness*.** "Does
   this look like JSON" cannot separate a frozen envelope from a
   correctly-unwrapped message that is itself a JSON document, and
   acting on the guess destroys the second. Byte equality against the
   record's own `MESSAGE` is exact in both directions — a row nothing
   unwrapped holds it verbatim, an unwrapped row holds the fragment. So
   the truncation the entry feared is real and lands on the **witness**,
   which is the weaker half: a row that cannot be cleared is *refused
   and reported* rather than corrupted. Re-measured, Session 90's
   anti-correlation has grown and still holds — **16** rows now carry a
   `raw_line` cut at 2000, intersecting the ten at **zero**.
3. **The population is the declaration's, never the shape's.** A
   candidate is a row whose source declares `format: json` *today*; a
   sweep for JSON-looking messages would rewrite a plain-text service
   that happened to log a document, which is recognising an application
   rather than honouring a statement — `unwrap_json_message`'s own rule.
   The set is `composed_log_sources` resolved through
   `stored_source_name`, because `log_entries.source` holds the **unit**
   while the declaration is keyed on the **name**: `log_source_scopes`
   records that trap from the other side, where the wrong key yields an
   empty map that reads as success.
4. **Idempotence is a property, not a flag.** A repaired row's `message`
   no longer equals the record's `MESSAGE`, so rule 2's witness answers
   `False` on the next run. A `backfilled` column would be a second
   statement of a fact the data already carries.
5. **A console script, not a data migration**, which inverts the obvious
   ranking. An Alembic revision moves the packaged head for no structural
   reason, so the box owes `alembic upgrade head` plus a restart or
   `schema_guard` refuses to boot — `SNAG-DB-005`'s twenty-three hours
   bought for ten rows — and it repairs this population once where the
   defect is a *class*. Dry run unless `--confirm` (`files/actions.py`'s
   contract), and **never scheduled**: `check-migrations.sh`'s rule, with
   a test pinning that no job plan or agent reaches it.
6. **Every way of not-knowing is reported and none is success.** A row
   that cannot be witnessed and a row whose envelope will not parse are
   distinct from "nothing to do" and both push the exit status to `2` —
   `ports_checked`'s rule at the size of a return code.

Measured before deciding, which is what the sitting was for: the
population was **intact and three days from moot**. The ten left the
trend's current window on 2026-08-24 and would have left the endpoint on
2026-08-31; live either side of the write, `GET /api/logs/trends` went
**60 → 50** signatures, `sysadmin.service` **24 → 14** and raw-JSON
**10 → 0**. `GET /api/logs/actions` is **unmoved at 8** — the ten were
`previous`-only and never produced advice — which corrects this
document's own "four of the nine live titles now open with
`{"timestamp"`": that population had already aged out.

**Applying it exposed a duplicate nobody had seen, and dating the commits
is what settled the mechanism.** Two of the ten have a readable twin
ingested at **19:50:19**, the restart that deployed the declaration; the
declaration was committed at **17:53:33** and `SNAG-LOG-007`'s boundary
close (`_is_unstored`, `stored_at_floor`) landed at **20:09:44** —
*nineteen minutes after that restart* — so `_resume_floor` re-admitted
its own inclusive second. Invisible before the backfill, because the
twins were different signatures and hid each other; `SNAG-LOG-004`'s
ordering a fourth time, a fix that widens what a monitor can see being a
regression surface for whatever reads it. Filed as `SNAG-LOG-014`.

The check retired with the entry and **the detector did not** — its
two-declaration drive is `tests/test_message_backfill_live.py`,
`FROZEN_TABLES`' rule. Re-homing it walked into the entry's own warning
a second time: the drive paired the two reads on `raw_line`, whose field
order `journalctl -o json` does not fix, so it compared nothing and
**skipped**. It pairs on `__REALTIME_TIMESTAMP` now, with a premise test
asserting the reads shared a record at all. Two of fourteen mutations
were wrong on the first attempt — removing the declaration filter gave a
*collection error* rather than a red test, and breaking the confirm gate
was caught only by an AST sweep until a live drive through `run()`
itself was added.

**Making the monitor able to see its own errors gave one fault two
speakers, and the second-owner defect existed at a sixth scale by this
repository's own hand** (Session 65, `SNAG-LOG-005`). `BaseAgent.run`
states one fact twice, three lines apart: `logger.exception` writes
`agent_run_failed` to the journal, then `_record_outcome` writes a
`failed` row to `agent_runs`. Session 61's level prefix and Session 64's
`format: json` are what let the first copy reach the log aggregator — so
an agent failure raised a row here **and** a row from `failures.py`, two
tray `{severity}:{title}` fingerprints, two toasts. Sharper than
duplication: `failures.py` requires **two** consecutive failures and
argues the rule out in writing (*"One failure resolves itself on the next
run… which is noise"*), while the journal path raises on the **first**
line. A deliberate threshold was not overridden, it was bypassed.

`COVERED_SIGNATURES` maps `(source, signature)` to the family that owns
the fault. Five rules, three of them the opposite of the obvious
implementation and all five settled by counting the journal rather than
by argument:

1. **Quietened, never dropped** — `known_noise`'s rule 2 for its reason.
   The row still counts occurrences, still reaches `GET /api/logs/trends`
   and still resolves on silence; `details['covered_by']` **names** the
   owning family, `details['truncated_sources']`'s rule. `noise_reason`
   and `covered_by` are separate keys because an operator's judgement
   that a fault is harmless and a structural fact that another family
   owns it are different claims — one field holding both is
   `UnitFinding.enabled`'s trap.
2. **Both halves of the key are constants the producers already own.**
   `OWN_UNIT` is the unit `read_journal` stamps into
   `log_entries.source`; `AGENT_RUN_FAILED_EVENT` replaces the string
   literal `BaseAgent.run` passed to `logger.exception`. Copying either
   would be a second statement of somebody else's fact —
   `max_priority_for` against `PRIORITY_MAP`, `chk_alert_agent` against
   `AGENT_NAMES`. The signature is matched *after* normalisation, and
   `signature()` maps digit runs to `N`, so a test pins that the event
   name still survives it: the failure mode of a rename is silence, not
   an error.
3. **Scoped to the one signature, never to this daemon's unit.** The
   obvious wider fix — excluding `OWN_UNIT` from the alert half — was
   refused on measurement. 713 `ERROR`/`CRITICAL` lines resolve to **249
   incidents**, and **34 carry no `agent_run_failed` at all**
   (`file_organiser_scan` ×27, `retention_purge` ×7). `retention_purge`
   is not an agent, so no family covers it anywhere; excluding the unit
   deletes the only witness those have.
4. **Quietening is safe because the case where `failures.py` is blind is
   the case where a different signature is still loud.** That family
   reads `agent_runs`, so it cannot see a failure `_record_outcome`
   failed to record — but `_record_outcome` is awaited *outside*
   `run()`'s `try`, so its failure propagates into APScheduler and raises
   `scheduler_job_error`, still at `warning`. Measured: 215 of 215
   historic incidents carry both lines in the same second, and
   `agent_runs` holds **zero** `failed` rows across 7,816 sysadmin runs —
   the same fact stated twice. `SNAG-LOG-006` is the one path it misses:
   a manual run is started with `asyncio.create_task` and has no
   scheduler listener behind it.
5. **The quietening reaches a row raised by the previous release.**
   `known_noise` arrives by a config edit the next poll re-reads; a
   covered signature arrives at a **deploy**, so the open row it must
   reach is one this daemon raised loudly under the old code — and this
   family's rows do not resolve while the fault keeps firing. Session
   39's ban on in-place severity changes is asymmetric, and this is the
   direction it permits.

**The entry understated its own symptom, which is the part worth
carrying.** It said one fault produced two rows; the journal says
**four** — 215 of 215 incidents fired `agent_run_failed`,
`scheduler_job_error` and apscheduler's own `Job "…" raised an exception`
in the same second. Only two of those can recur, because Session 41 made
`_record_outcome` survive a failed run, so the entry was right by
accident. It also quoted the title as `Log error: sysadmin-service — …`;
`log_entries.source` is the **unit**, so it is `sysadmin.service`. A snag
filed from reasoning about a mechanism rather than from counting its
output is the failure `verify-ops-claims-live` names, one document over.

The fix ships **untriggered**: all 215 lines fall on 2026-08-08 → 08-10,
the `SNAG-DB-001` window, and there have been none since. So it was
driven live rather than only against fixtures — real historic lines
through the real `unwrap_json_message` and the real `_execute` against
the live database in a rolled-back transaction, giving `info` +
`covered_by` for one signature and `warning` for the other with **0 rows
of residue**. Each of the six tests was falsified deliberately: emptying
`COVERED_SIGNATURES` breaks five, and re-keying the lookup on the
signature alone breaks the sixth — the one asserting a *negative*, which
an empty set can never break.

**Rule 5's one uncovered path is closed, and costing the two candidates
inverted the ranking the entry implied** (Session 112, `SNAG-LOG-006`).
That rule rests on `_record_outcome` being awaited *outside* `run()`'s
`try`, so a failure to record a failure propagates into APScheduler and
raises `scheduler_job_error`. A manual run has no scheduler behind it:
`POST /api/sysadmin/scan-all` and `POST /api/files/scan` started agents
with a bare `asyncio.create_task(agent.run(...))` and kept no reference.
`spawn_manual_run` and `_report_manual_run` in `core/agent.py` are the
supervisor; all five triggers go through them.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the running loop rather than by argument:

1. **`run()` escapes in four shapes and the cheap fix reaches one.**
   `_execute`'s exception is swallowed, so what escapes is the
   bookkeeping around the work. Driven through the real `run()`:
   `_execute` **and** `_record_outcome` raising (journal holds
   `agent_run_failed`), `_record_outcome` alone (`agent_run_completed`),
   `_record_start` (**no line at all**) and `_flush_events`
   (`agent_run_completed`). Narrowing `COVERED_SIGNATURES` to
   `run_type == "scheduled"` can speak only where an `agent_run_failed`
   line **exists** — shape 1, and nothing else. It is also the *more*
   expensive: `unwrap_json_message` returns `{"logger": …}` and its own
   docstring refuses to promote further envelope fields into the
   identity, and the map would gain a third key component `known_noise`
   does not share.
2. **The report goes to the journal and never to the database.** The
   exceptions that reach here come from `_record_start` and
   `_record_outcome`, which are database writes, so a report needing a
   session would need the thing that has just failed —
   `core/unit_failure.py`'s argument (it runs while the application is
   dead) arriving one layer in. The journal is already wired: since the
   level prefix and the `format: json` declaration an `error` line from
   this daemon is ingested and raises through the family that owns this
   source. No new alert family, no new table, no session.
3. **It cannot double-report an ordinary failure, which is what makes
   rule 2 safe.** A normal agent failure *returns normally*, so the
   callback sees no exception at all — `failures.py`/`stalls.py`'s
   mutual-exclusion-by-construction one layer down, and the
   healthy-run-says-nothing test is what keeps it honest.
4. **The residual signal the entry filed as unmeasured is prompt, and
   *when* was never the problem.** asyncio's fallback fires at `ERROR` on
   the loop turn **after** the task completes — the loop drops its
   reference, CPython collects the task, `Task.__del__` calls the handler
   synchronously; no `gc.collect()` is needed or helps. **What** it emits
   is the defect: a **252-character signature** and a **220-character
   title** reading `Task exception was never retrieved future: <Task
   finished name='Task-N' coro=<BaseAgent.run() done, defined at
   …/core/agent.py:N> …` — `SNAG-LOG-003`'s shape by the one route
   `unwrap_json_message` cannot help, since the *unwrapped* message is
   itself the repr. It names `BaseAgent.run`, so all five triggers share
   one signature and the row cannot say which agent died; it carries the
   module path, so moving `run()` forks the row on a commit that changed
   nothing; and the exception's own text sits inside the repr, so on a
   checkout path shorter than this one it falls inside the cap and forks
   a row per distinct failure — `SNAG-AGENT-005`'s pile-up rebuilt inside
   the family built to end it. What ships instead is
   `manual_run_failed`: a **17-character** signature and a
   **46-character** title, with `exc_info` measured landing under its own
   envelope key so the traceback stays out of the identity and one query
   away in `raw_line`.
5. **Cancellation is tested first, recorded, and never announced.**
   `Task.exception()` *raises* on a cancelled task, so the order is
   forced; what is not forced is the response. A cancellation leaves
   precisely the residue a failure leaves — an `agent_runs` row stuck at
   `running` — so it is written rather than dropped (`known_noise`'s rule
   2), and written at `warning`, which `FAULT_SEVERITIES` excludes:
   stored, counted, carried into `GET /api/logs/trends`, raising nothing.
   That tuple was extracted from an inline literal in
   `LogAggregatorAgent._execute` so the rung is derived rather than
   restated — `max_priority_for` against `PRIORITY_MAP`'s rule. The rung
   *is* the mechanism; a second suppression list would restate what the
   severity already says.
6. **There is no `run_type` parameter.** A scheduled run must not arrive
   here, because APScheduler's listener is what makes
   `scheduler_job_error` loud for those and a second supervisor gives one
   fault two speakers — the second-owner defect arriving inside the fix
   for a case of it. Hard-coding `"manual"` makes that impossible rather
   than discouraged, which is `since_timestamp`'s argument for taking a
   `datetime`.

**The entry named the wrong second trigger and its own check could not
have said so.** `POST /api/files/organise` is a *synchronous* action
route returning `FileActionResponse`; the discarded task was in
`POST /api/files/scan`. `check_manual_run_unawaited` counted five
discards across two *files* and never named a route, so it reported
`match` — the right number about the wrong thing. The check retires with
the entry (every member of `CHECKS` names an open one) and the detector
does **not**: the AST walk is re-homed as `TestNoTriggerDiscardsItsTask`,
`FROZEN_TABLES`' rule, since deleting a guard along with its last finding
takes the guard against the defect coming back.

Ten mutations were driven against the twenty new tests and each lands red
on the right one — **two of them wrong on the first attempt, which is the
part worth carrying**: removing the `finally` produced a `SyntaxError`
rather than a leak (a stand-in that cannot compile is silence wearing a
result), and the priority round-trip test read `PRIORITY_MAP` with an
`int` key when the map is keyed on the **string** journalctl emits.
Verified live and untriggered: the real `POST /api/sysadmin/scan-all` on
the restarted daemon produced four `agent_run_completed` lines and zero
`manual_run_failed`.

The other 86 % was the tray. `sysadmin_tray/dashboard/services_tab.py`
is built eagerly at startup and wired to `status_updated`
unconditionally, so it issued one `/details` per systemd-backed service
on **every** status poll, dashboard open or not — **1,160 of 1,347
lines** in ten minutes, against `DashboardWindow`'s own docstring
promising *"no background polling when hidden"*. `LogsTab` stops its
timer in `hideEvent`; this tab had no timer to stop, so the polling was
never scheduled, it was inherited from a signal that fires anyway.
`isVisible()` is false both when the window is hidden and when another
tab is selected — both cases where nobody is looking — so the widget's
own answer is used and no second flag is kept, a flag being free to
disagree with Qt about the same fact. `refresh()` fetches details for
cards already held, because the gate's visible cost is a warm tab
opening blank for a poll interval and it is paid there rather than by
widening the gate. `ServicesTab` was the **only** tab issuing a request
from a client signal handler, so it is fixed in place rather than
abstracted.

**The two halves of `SNAG-AGENT-008` are multiplicative, not
independent**, which is the part worth carrying forward.
`_read_journal_source` falls back to a five-minute window only when
there is no cursor **and** `_resume_floor` is `None`. For
`sysadmin-service` the floor is *always* `None` — the priority half
means no rows are ever stored — so the durable resume mechanism is
permanently disabled, every restart re-reads five minutes, and five
minutes at 673 lines overflows the 500-line ceiling. Fixing **either**
half stops the truncation; only the priority half stops the re-read.
