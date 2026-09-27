# Alert lifecycle — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**`SysAdminAgent._resolve_recovered` resolves alerts set-based**, and it
arrived by an argument being reused rather than rediscovered. The project
organiser made it first: a project deleted from disk never appears in a
scan, so it can never be observed *recovering*, a per-project loop leaves
its alert unresolved for ever, and retention purges resolved rows only —
which is how 1,664 rows accumulated by 2026-08-07, 326 of them sharing one
title. The fix was to ask the inverse question: which open alerts would
this run *not* raise. That agent left with the projects domain on
2026-08-13 (ADR-0005) and its own account of the rule is estate-manager's;
the statement it argued for is still here, on the service side (Session
41, SNAG-AGENT-004), where the same defect had reached **51,924 rows** —
twenty times the scale, and in two families rather than one:

- **27,827 for five services that no longer exist** in either config file.
  Recovery was observed inside the loop over the *configured* services, so a
  deconfigured service was never checked, never seen to recover, and never
  resolvable. `redis unreachable` held 6,283 rows last raised 2026-03-07.
- **24,097 for resource thresholds**, which had **no resolve path at any
  point in this application's life**. `Critical disk usage on /` alone is
  13,971 open rows last raised 2026-07-26, against a disk that has been at
  68 % since. A condition that recovered and could not be observed
  recovering is the same defect as a service that was retired, so one
  statement closes both.

Four rules it encodes, two of which are the opposite of the obvious version:

1. **The population is `RESOLVABLE_TITLE_PATTERNS`, not the configured
   service list.** A set built from configuration cannot contain a
   deconfigured service, which is the entire defect. Patterns are the only
   shape that can reach a row whose subject is gone.
2. **Services and resource thresholds take different exclusions.** A mount
   either breached this run or did not, so "titles this run raised" decides
   it exactly. A service's alert is governed by a *streak* — three
   consecutive degraded checks — held in `_degraded_counts`, which is in
   memory and **resets on daemon restart**. The same test would therefore
   close a genuinely-degraded service's alert on the first run after every
   restart and re-raise it two checks later: a recovery announced to the
   tray for a fault that never went away. Services are resolved only when
   this run measured them *healthy*.
3. **Three families are excluded because each has a lifecycle owner
   already**, and a second owner closes a row while it is still true:
   `% agent stalled` (`stalls.py` escalates *off* the quiet row staying
   open), `% failed` (`unit_failure.py` writes it dead and the lifespan
   resolves it alive), `Unusual % usage` (`_check_anomalies` resolves by id).
4. **`skipped` counts as healthy; `error` does not.** Both mean nothing was
   measured, and the difference is who decided. `error` is the check
   failing — the state is unknown and resolving on unknown announces a
   recovery nobody observed. `skipped` is `services.yaml` declaring
   `monitor: false`, and an open critical nothing will ever look at again is
   the pile-up wearing a declaration as an excuse.

The per-service `resolve_alerts(session, service_name)` it replaced was also
a substring `ilike`, so `venture-chat` recovering closed
`venture-chat-large`'s alerts — a second bug nobody had filed, removed by
having one owner of the lifecycle instead of one per item.

What it does **not** cover is `log_aggregator`'s rows (SNAG-AGENT-005, fixed
Session 41's successor). Those are **events, not states** — a log line that
was written cannot un-write itself — so there is no run at which "this would
not be raised" becomes true, and the fix was a *raise* rule.

**Dedup and the set-based resolve are mutually exclusive, and the
collation family is where that got written down** (Session 44,
SNAG-DB-002). A glibc upgrade moved this box from locale data 2.43 to
2.44; PostgreSQL records the version each database was created with so
it can say it no longer matches, and had been printing that on every
`psql` connection, read by nobody. Any B-tree index on text was built
against the old ordering, so a lookup can miss a row that is present —
which here would present as an alert that never deduplicates or never
resolves. `sysadmin/monitor/collation.py` reads `pg_database` once per
sysadmin run; the catalog is **cluster-wide**, so the existing
connection to `projects` sees all eleven databases without a second
engine. Eight are stale. The snag said three, because three is how many
someone had opened a shell against.

Four rules, three of them the opposite of the obvious implementation:

1. **Not-knowing is not a mismatch, and this fails _open_** —
   deliberately the reverse of `core/schema_guard.py`, which refuses to
   boot on every way of not-knowing. `template0` records no version and
   a `C`-locale database has no actual version to compare against, so
   both sides are required non-NULL **in SQL**; `IS DISTINCT FROM` is
   rejected for reporting `2.43` against `NULL` as a difference. The
   guard fails closed because serving against the wrong schema is worse
   than not serving; here a false positive is an operator reindexing a
   16 GB database that is fine.
2. **Raised once per open row, never once per run.** The agent polls
   every 300 s and a stale collation persists until someone reindexes,
   so the `_check_thresholds` pattern would write 2,304 rows a day for
   one fault.
3. **Therefore the family stays out of `RESOLVABLE_TITLE_PATTERNS` and
   owns its own lifecycle.** That sweep closes every owned row the run
   did not raise, which is sound *only* for a family that re-raises
   every run — which is why `_check_thresholds` can be in the tuple and
   this cannot. Dedup plus sweep makes a row flip-flop, resolved on the
   run that holds and re-raised on the next, and each flip clears the
   tray's `{severity}:{title}` fingerprint so it notifies again. A
   pile-up is loud; that is loud *and* reads as recovery. The database
   name sits last in the title, keeping it clear of the five
   `% <kind>` patterns by construction.
4. **The remedy's trap is carried in the alert.** `ALTER DATABASE …
   REFRESH COLLATION VERSION` alone clears the warning by asserting the
   versions now match without rebuilding anything — a loud known risk
   turned into a silent one — so the message names `REINDEX` first and
   `details['remedy']` is an ordered two-element list.

The gap this leaves is `SNAG-AGENT-006`: the *service* and *threshold*
families still raise unconditionally, so a sustained fault writes one
row per run — 60 for one dead timer in five hours. Bounded rather than
immortal since Session 41's resolve, and not fixed here because both
halves must move together.

**An index a reader cannot reach is not an index, and the two were eight
lines apart** (Session 105, `SNAG-AGENT-007`). `alerts` has carried
`idx_alerts_active … WHERE resolved = FALSE` since it was created.
Nineteen readers asked for their open rows as
`Alert.resolved.is_(False)`, which renders `resolved IS false`;
PostgreSQL matches a partial index **structurally**, and a `BooleanTest`
is not an `OpExpr`. Every one of them fell to a sequential scan.
`unresolved()` on `sysadmin/core/models/alert.py` is the one statement of
*open*, and it renders the index's own predicate literally.

Five rules, four of them the opposite of what the entry proposed:

1. **The entry costed the read by its result and the cost is its scan.**
   It ranked itself P3 on "the table is small"; the table is **666,936
   rows** and what is small is the answer — **zero** open `sysadmin`
   rows. Live: **41,644 buffers and 33.3 ms** against **13 buffers and
   0.03 ms**, four times per 300-second run. Reading the code confirms
   the entry's count; running `EXPLAIN` refutes its ranking, which is
   `verify-ops-claims-live` for a claim about performance.
2. **A projection is not a definition, which is what dissolves the
   tension the entry filed itself around.** It refused
   `select(Alert.title)` for the dedup caller as *"a second definition of
   this agent's open rows"*. What a caller wants **back** may differ per
   caller; which rows it is **asking about** may not. So the predicate is
   stated once and `SysAdminAgent._open_alert_criteria` composes the
   agent scope on top — a third projection tomorrow adds no third
   definition. `Alert.agent == self.name` deliberately stays at the
   agent: a scope one caller applies is not a vocabulary anyone can
   disagree about.
3. **Migration 017 alone would have been a no-op**, which is worth
   knowing because the obvious reading of a performance snag is that the
   database is missing something. `idx_alerts_open_by_agent` bounds an
   agent's read by *its own* open rows rather than by the whole open set
   — `SNAG-AGENT-005` reached 598,091 in one family — and driven at
   100,000 synthetic open rows in a rolled-back transaction the old
   spelling **with the new index present** still seq-scanned at 41,644
   buffers. Only the pair gives 2 buffers. Today the planner still
   prefers the older index, one open row making either free, so the new
   one is insurance that engages when the entry's worry materialises —
   stated rather than implied, since an index nothing chooses looks
   exactly like an index that does not work.
4. **The substitution is provable, not merely safe-looking.** `IS false`
   and `= false` differ on exactly one input and `resolved` is `NOT
   NULL`, which is why the definition lives beside the column: the column
   is the proof. A test asserts the nullability rather than remembering
   it, because nineteen call sites were rewritten on that one fact.
5. **The sweep is driven at its own owner.** `unresolved()` *is* the
   hand-written form — that is what makes it the one definition — so the
   AST guard exempts the model and then runs at it, which must trip every
   rule. `test_autogenerate_config.py`'s idiom, reused.

Note what was pinning the defect: `test_it_is_scoped_to_this_agents_unresolved_rows`
asserted the string `alerts.resolved IS false` and was green for the life
of the module — `TestJournalCommand` in a second family. It composes from
`unresolved()` now, so it pins **provenance** (the resolve uses the
shared predicate) while `tests/test_open_alert_predicate.py` pins the
**value** (that predicate renders the index's string). And
`test_alert_dedup.py`'s stand-in could not tell a projection from a row
read, so the fix arrived as four red dedup tests — the defect they exist
to catch, wearing the fix's clothes; it discriminates on
`selected_columns` now, modelling the database rather than the one call
site that happens to project.

**A row is deduplicated on its title, and until 2026-08-28 that froze
its sentence with it** (Session 110, `SNAG-AGENT-009`). Every family
that dedups takes a `held` branch and `continue`s, so `alert.message`
stayed whatever the *first* run wrote — and `details` with it, which the
entry did not say. `Alert.title` is the identity and must not move
(Session 42), but the message is what a reader acts on.
`BaseAgent.refresh_alert` rewrites both, and only when the recomputed
text differs. Measured before it was built: **1,360 held events
all-time** — threshold+service **838**, collation 386, estate judge
**131**, armed orphans 5, ports **0** — and across the 23 post-dedup
`High VRAM usage` rows **42 of 42** polls inside a hold carried a
different figure, 19 of them *below* the threshold the frozen sentence
was asserting.

Six rules, four of them the opposite of the obvious implementation:

1. **The base class owns the comparison and the write; finding the row
   stays with each caller.** The three reach it three ways for reasons of
   their own — the estate judge already holds the ORM rows,
   `_maintain_port_alerts` bounds its read by a title prefix, and
   `_raise_judged` keeps the title-only snapshot `SNAG-AGENT-007` gave
   it — so a base class taking a *title* would own a predicate its
   subclasses state three ways. `_open_alert_criteria`'s split of
   projection from predicate, read from the other end.
2. **The 838's row is read at the hold, never carried in the
   snapshot.** A snapshot widened to hold `message` and `details` is
   bounded by *the table*, and this agent's families reached 51,924 open
   rows before `SNAG-AGENT-004`; a read at the hold is bounded by *the
   judgements the run made*. Live at 665,937 rows it is **84 buffers,
   0.098 ms** — and lands on `idx_alerts_active`, **not** the
   agent-scoped index the first docstring claimed: one open row makes
   either partial index free and the planner takes the older one, which
   is exactly `SNAG-AGENT-007`'s own reading. `EXPLAIN` corrected the
   prose; reading the code would have shipped it.
3. **`details` is compared through a JSON round trip, or the gate
   degenerates into "always".** `JSONB` has no tuple, so a caller
   building `details` with one gets a list back next run and a plain
   `!=` reports a difference no write can settle — the gate switched off
   by a type, with the counter reporting corrections that corrected
   nothing. What is *stored* is the caller's dict, because a raise and a
   refresh handed one input must write one row.
4. **Only a row open before this run is refreshed**, which is why
   `_written_titles` is a second set rather than more entries in
   `_open_titles`. A title judged twice inside one run — two identically
   named GPUs, the case that put the `add` there — would otherwise have
   the *last* judgement overwrite the first, and which of the two is
   current is undefined. The run must not answer that twice.
5. **The gate is a floor, not a promise of quiet.** For a family whose
   `details` is a live measurement — the service family carries the
   check's own response time — every held poll differs and every held
   poll writes. Bounded anyway at ~**0.26 per run**, and it is an
   `UPDATE` to a row that already exists: `SNAG-AGENT-006`'s objection
   was about `INSERT`s accumulating and does not transfer.
6. **Nothing is announced, and that is not an oversight.** Session 39
   bans an in-place *severity* change because the tray fingerprints on
   `{severity}:{title}` and would keep a fingerprint it has already
   suppressed. A message change is invisible to that fingerprint, so it
   is safe in the direction that ban is about and, for the same reason,
   silent — no `alert.refreshed` event is queued, because an event
   nobody reads is `SNAG-CFG-001`'s shape. The corrected sentence reaches
   the tray on its next poll, and reaches a reader out loud only when
   `reminder_hours` re-speaks the row, which is the surface this exists
   for.

**It half-closes `SNAG-ESTATE-010`, and that entry's own check is what
said so.** That check enumerates three shapes a fix could take and
refuses to watch the severity column alone; the third — *the `holder`
blob arriving with the severity unmoved* — is this fix, so the blob now
reaches a standing row on every run. The clause came **out** of
`QuietenReading.reached` rather than the verdict being accepted: a
`reached` still reading the blob answers `mismatch` whatever happens to
the rung, which is a control this fix broke. The rung half stood at the
time, by Session 39's design, and **closed the same day** — see the
`may_quieten_in_place` section below, where that design turns out to
permit exactly this direction. The blob is still carried in the
*detail*, because "the correction reached the row and the rung stayed
put" was a stronger statement of the then-surviving claim than "nothing
happened".

**Four stand-ins modelled a database this code no longer talks to**, and
that was most of the work. `tests/test_unit_ports.py` answered the dedup
read with *titles*; `test_estate_judge_agent.py`'s `FakeAlert` had no
`message`; `test_alert_dedup.py`'s fake ignored the WHERE clause and
could not answer `.first()`; and `conftest.mock_session`'s bare
`AsyncMock` returns a coroutine from `.scalars()`, which fails in a way
no database produces and reads as a bug in the code under it.
`SNAG-ESTATE-010`'s probe located its standing row by
`message == PROBE_MESSAGE` — the value this fix rewrites — and keys on
the title now, which is the identity the entry it checks turns on.

**The rung moves too now, in one direction and only to the floor**
(Session 117, `SNAG-ESTATE-010`). The half `SNAG-AGENT-009` left is a
judgement that gets *quieter*: every dedup skips a title that is already
open before it looks at severity, so Session 57's
`TRANSIENT_HOLDER_SEVERITY` applied only to breaches raised afterwards
and the two rows it was written for sat at `warning` for the life of a
VS Code window. `core/escalation.may_quieten_in_place` is the rule and
`BaseAgent.refresh_alert`'s optional `severity=` asks it.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the running code rather than by argument:

1. **The rule was already here, stated once and obeyed by one family.**
   `log_aggregator._record_recurrence` has quietened a held row in place
   since Session 66, because **Session 39's ban is asymmetric and the
   reason it exists is what makes the reverse safe**: the ban is about an
   escalation needing to be *heard*, and the tray's suppressed
   `{severity}:{title}` fingerprint is exactly what a quietening wants.
   Four other deduplicating families needed the same answer and had no
   way to ask for it, which is how a copied rule drifts — `escalation`'s
   own opening argument for living in `core`.
2. **"Downward is safe" is too broad by one rung, and that is the whole
   narrowing.** `critical` → `warning` in place hands the tray a
   fingerprint it *will* speak, so the write arrives as a fresh, less
   urgent notification about a fault that has not improved — which is
   `step_for`'s refusal met from the other side. Only `QUIETEST_SEVERITY`
   is inaudible-or-asked-for, and it is **derived** from `SEVERITY_ORDER`
   rather than written as `"info"`: `max_priority_for` against
   `PRIORITY_MAP`'s rule, pinned by reading the source, because a literal
   and a derivation both *read* `info` and only provenance separates
   them.
3. **The tray's threshold is not consulted and could not have been.**
   The obvious gate is "quieter than `notify_min_severity`", which makes
   the daemon a second reader of a policy the tray owns — and `AppConfig`
   parses `notifications.tray:` (`TrayNotificationsConfig`, "the slice
   the *backend* needs") while that key lives in the top-level `tray:`
   section the tray parses for itself. A config leaf added for a rule
   that does not need it is `SNAG-CFG-001`'s shape.

   **That rule is about the daemon, and a test is not the daemon** —
   stated because reading it the wider way cost a sitting. Session 118
   declined to guard `SNAG-ESTATE-009`'s ceiling on the grounds that
   `TrayNotificationsConfig` parses `mute_services` alone, so a test
   *"can only read `notifications.desktop.reminder_hours`, the
   understudy's copy"*. `TrayNotificationsConfig` is the backend's
   **model**, not the file: `sysadmin_tray/config.py` parses
   `notifications.tray.reminder_hours` out of the same `config.yaml`,
   ships in this wheel, and is already imported across the seam by
   `tests/test_desktop_notifier.py`. Measured — `load_tray_config` at a
   copy with the tray leaf set to 6 returns `6.0` while the understudy
   still reads `24.0`. So the leaf is unreadable *to the daemon*, by
   design, and readable to a guard;
   `tests/test_config_defaults.py::TestTheLoudRungEndsBeforeItIsRestated`
   is that guard, and `TestTheTwoSpeakersAgreeInTheShippedFile` is the
   shipped-file half of the pin whose existing copy compares two
   defaults constructed with no file at all.
4. **It is asked *before* the text gate, which is where the fix would
   otherwise have shipped green and inert.** `refresh_alert`'s existing
   gate is "has the text moved", and the founding case is a breach the
   estate republishes word-for-word every hour with only the rung
   changed. One test catches the ordering, falsified against exactly that
   mutation.
5. **The entry asks for a reason the new severity is *durable*, and the
   answer is that the transition is one-directional rather than that the
   rung is stable.** A wobbling producer cannot flip-flop: down is in
   place and silent, up is refused and belongs to `step_for`'s
   resolve-and-re-raise. No row is resolved, none re-raised, and the
   count of standing faults does not move.
6. **Two of the three callers have empty populations and are wired
   anyway.** `_raise_judged`'s is empty **by construction** — every
   family there pairs a rung with a *title kind*, so a disk breach at the
   warning and critical thresholds is two titles rather than one row at
   two rungs — and the port family's because its rung is a constant, now
   `PORT_ALERT_SEVERITY` rather than a literal in the raise and nothing
   at all in the held branch. The entry *is* what happens when a family
   gains a quieter rung and its held branch was never told what rung it
   judged.

**It reaches the second speaker, which nothing had noticed.** The tray is
fixed for free — the old pair leaves the poll and the new one is dropped
below `notify_min_severity` — but `monitor/desktop.py` speaks from
`_SpokenFault.severity`, the rung it *announced*, and `_still_open` asked
only which titles were open. So the understudy would have gone on
restating at `warning` a fault the judge had decided is `info`: the
founding entry surviving inside the fix for it, in the one component that
exists for the case where the tray is down. That read returns
`{title: severity}` now and the sweep takes the row's rung, **loudest
wins** for the beat in which an escalation has two rows open — and the
sync is unconditional rather than direction-tested, because an escalation
has already replaced the whole entry through `on_alert_raised` and reads
back the same value.

The check retired with the entry and the drive is re-homed as
`tests/test_quietened_judgement_live.py` (`FROZEN_TABLES`' rule), where
it is **stronger than the check**: that check asserted a *disjunction* on
purpose, since any of three shapes would have been a fix, and now that
the shape is known a resolve-and-re-raise would satisfy it while
rebuilding `monitor/collation.py`'s flip-flop. It asks which shape — the
rung moved in place, one row, still open, nothing raised and nothing
resolved — and the resolve-and-re-raise mutation turns three of its four
tests red where the check would have said `mismatch` and called it fixed.

**One falsification passed against deliberately broken code**, which is
the part worth carrying: the "loudest of two open rows wins" test yielded
its rows loud-*last*, so a last-one-wins implementation with no
`_loudest` call in it answered correctly by accident. The query has no
`ORDER BY` — which is the whole reason `_loudest` is there — so it drives
both orderings. Three stand-ins again modelled a database this code no
longer talks to: `FakeAlert` with no `severity` (the column is `NOT NULL`
behind `chk_alert_severity`), `_FakeSession` answering the open check
with titles alone, and a fail-closed test breaking one reader out of two.
