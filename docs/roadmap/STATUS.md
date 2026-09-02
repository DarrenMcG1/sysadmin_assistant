# Project Status Dashboard

**Last Updated**: 2026-09-02
**Current Phase:** Feature-complete — maintenance & future features

> **A red now says which of two things happened, and the observation had
> to move inside the call to say it** (2026-09-02, Session 156).
> `SNAG-TEST-003` is **fixed**, and it was the last open entry naming no
> check: **0 of 20**, down from 1 — by the entry closing, not by a check
> being written, which is the only way that figure may fall for an entry
> whose claim is an assertion's wording. A check would have to reproduce
> an intermittent fault on demand.
>
> **The separator is a precondition, not a differential.**
> `test_notify_send_does_not_return_on_a_bus_with_nothing_listening` said
> a red meant the D-Bus activation *"is gone from this box"*, so any red
> read as good news and the honest response to good news is to relax the
> guard. It now asserts that `plasma_waitforname` was started under this
> fixture's own bus **before** it asserts the call blocked. Three states,
> measured rather than reasoned about: hazard intact — activated, blocked,
> **8.03 s**; reading disturbed by three kills, which is `SNAG-TEST-004`'s
> own mechanism replayed — **activated**, returned at **3.06 s** with
> `exited with status 255`; hazard genuinely gone on a bus whose config
> declares no service directory — **not** activated, returned at
> **0.03 s** with `ServiceUnknown`. `returned` is common to both failing
> readings; the activation is what tells them apart.
>
> **Sampling during the call is forced rather than a refinement.** The
> disturbed row's waiter is dead by the time the call returns, because
> killing it is what errored the call — so one check afterwards reports
> "no activation" for a disturbed box and a fixed one alike, which is the
> collapse being removed, one line later. `_notify_send` is a `Popen`
> polled at 20 ms, an interval derived from a measured 48–50 ms activation
> latency against a waiter that then persists for the whole block. Its
> failure direction is the unsafe one and is stated in the assertion
> itself. The budget was **not** raised, which the entry named as the
> thing that must not happen.
>
> **What outlives the finding is the ordering.**
> `TestTheRedSaysWhichReadingItIs` pins that the two asserts read
> `outcome.activated` then `outcome.returned` — swap them and the block
> assertion's message asserts a waiter was started on a box nobody looked
> at. It reads each assert's `test` and never its `msg`, because both
> messages quote the same fields and a whole-node walk would report
> agreement whatever the order was. Both mutations land red. And
> `SNAG-TEST-004`'s scoping property was re-measured under the new probe
> rather than assumed to survive it: two offset concurrent runs, **4 for 4
> green** at the full 8.7 s, zero stray waiters.

> **The fold's second fact was published rather than derived, and the
> difference is whether a consumer restates a judgement** (2026-09-02,
> Session 155). `SNAG-SVC-004` is **fixed**.
> `_folded_row` rule 5 wrote *whose* step is leading into the folded
> `detail`; `health_review._service_facts` projects `title` and
> `action` and not `detail`, so the weekly review printed one finding's
> remedy under another finding's title with nothing saying the subject
> had changed. `ServiceRecommendationInfo.action_from` is that fact as
> its own field. Open entries with no check: **1 of 21**, down from 2 —
> by the entry closing, not by a check being written.
>
> **The entry's own last bullet decided where the guard goes.** A check
> asserting the *fix* cannot serve a registry whose `ok` means *"the bug
> is still real"*, so the drive is `TestTheStepsProvenanceIsProjected`
> rather than a twenty-first check — `FROZEN_TABLES`' rule met from the
> other end, and `SNAG-SVC-003`'s own closure one sitting earlier.
>
> **`stands_for`'s treatment is a derivation, and copying it literally
> would have been the defect.** That field is
> `m.title for m in members if m.kind != r.kind` — a restatement of what
> *swallowed* means, which is structural. The same shape here is
> `next(m.kind for m in members if m.kind in STEP_SUPERSEDES)`, which
> restates which member **won**: a judgement `_folded_row` already took,
> free to drift the day that tuple widens. `SNAG-DB-003`'s shape, and
> `judge_queue_invariants`' *"the mask is read, never recomputed"*. So
> the producer publishes it. One of the seven mutations is exactly that
> recomputing projection and exactly one test is red on it.
>
> **Both fold shapes were live at the moment of the fix**, which is the
> discrimination a specimen of one could not have supplied.
> `alfred-career-mail-timer` (`outage` + `timer_failed`) reads
> `action_from: "timer_failed"`; `venture-chat` (`outage` + `flapping`)
> reads `""`, because `flapping` promotes nothing. The digest line the
> entry quoted as *reading correctly by luck of one string* now says so
> in its own words.
>
> **Empty is deliberately not `ports_checked`'s not-knowing.** The field
> is `""` both for a row whose step is its own and for a producer that
> does not publish it; every other absent-vs-present collapse here hides
> a *blind* reading, and this one cannot, because both spellings mean
> "render nothing extra". Spelling it as the row's own `kind` was
> refused — it fires the renderer's clause on every folded row and makes
> every consumer compare two fields to learn nothing.
>
> **The refused fix is pinned rather than merely avoided**, and the
> audience for a published surface was measured. Projecting `detail`
> would carry the provenance *and* every swallowed row's own body into
> the review's blob, so a test asserts `detail` is absent from the
> projection. Outside this repository the route is named in one place —
> estate-manager's parser corpus copy of `snag_list.md`, a fixture and
> not a reader — and `estate-map.md` records one consumed route from
> 8500. A measured-empty audience files nothing.

> **The instrument was also the safety catch, and the check that needed
> two witnesses is the one whose subject is an action** (2026-09-02,
> Session 154). `SNAG-AGENT-013` has the **twentieth** check. Every
> other drive in this registry writes something and rolls it back; this
> one enters `_handle_status`'s auto-restart branch, whose whole point
> is that it starts a unit on this box — in a module a shell script runs
> at both ends of every sitting. So `restart_unit` is **patched rather
> than reached**, and the probe's unit is minted per call, because a
> swap that silently failed to bind could then only aim `systemctl` at a
> unit that does not exist. Open entries with no check: **2 of 22**,
> down from 3.
>
> **The patched call is the harness's witness and `_failure_counts` is
> the subject's.** They can disagree only if the branch reaches systemd
> by a name the drive no longer patches — a blind instrument, not a fix.
> Without the second witness an instrument that stopped binding would
> have reported this entry fixed *and* let the restart through, so the
> two are read side by side and a disagreement is `unknown`.
>
> **The obvious instrument would have shipped green.**
> `self._arbitration` *is* consulted a dozen lines below the branch, so
> a source walk finding it in `_handle_status` reports it consulted; and
> a walk asserting it is absent *above* the branch refutes the moment
> somebody moves a line. What the entry claims is about the **order of
> two conditions**, and only running the branch can say which won.
>
> **Three arms, and the control holds a lease rather than holding
> none.** `unread` is the premise — four conditions guard that branch
> and three of them are the harness's — while `other` and `stopped`
> differ in exactly one boolean, which is what separates a gate on the
> *unit* from a gate on *"a lease is granted"*. The second would stop
> restarting `alfred-backend` because the estate stopped `venture-chat`.
> Driven: moving the premise to a granted arm reddens exactly the
> lease-gate test and nothing else.
>
> **The population is reported and never scored**, which is rule 1 in
> the direction this entry makes easy to invert — the leaf being set
> *raises* the entry, so wiring the count to the verdict could only
> retire it at the moment it became live. Live: all three arms
> restarted, **0 of 31** services set `auto_restart` with a controllable
> unit, and `venture-chat.service` is the one unit this daemon has
> recorded the arbiter stopping, across **4** rows. The two halves have
> not met and the distance between this box and the defect is one leaf.
>
> **Two things only driving it could have said.** Thirteen mutations
> were driven and all thirteen land red on their intended test — one of
> them removed the swap altogether, letting the real `restart_unit` run
> and `systemctl --user restart` fail harmlessly against the minted
> unit, which *demonstrated* the second guard rather than arguing for
> it; and re-recording the call while still delegating to the real one
> is the only mutation that lands on the sentinel assertion, which is
> what makes it evidence rather than decoration. **mypy chose the
> stand-in's parameter name**, rejecting `target` against
> `restart_unit(unit, user)`: a stand-in that is not substitutable for
> the name it replaces is a control the next caller breaks.
>
> **`rung_sql` became `schema_sql` and moved beside `query_one`.** The
> fault it prevents — no `search_path`, so an unqualified name resolves
> to `public` and fails as *"the database did not answer"* — is a
> property of that connection, not of the entry that first hit it, so
> the second caller borrows the rule rather than copying the fix.

> **The entry named its own trigger and had no instrument for it, and
> the instrument found the entry understating its own residue**
> (2026-09-02, Session 156). `SNAG-AGENT-012` has the **nineteenth**
> check. Its last bullet reads *"what would raise it is the first
> `alert_rung_left_stale` line that is not a test's"* — a mechanical
> trigger nothing could answer. It is a query now, and *"that is not a
> test's"* needs no clause: `log_entries.source` holds the **unit**, and
> a test runs in the sitting's own process and never under
> `sysadmin.service`. Live: **0** trigger rows against **135**
> `alert_raised` rows that witness the path works, and **0** open
> `% unreachable` rows. Open entries with no check: **3 of 22**, down
> from 4.
>
> **The obvious instrument would have shipped green and inert.**
> `may_quieten_in_place('critical', 'info')` is `False` and is the root
> of the whole mechanism — and it is exactly what `step_for`'s
> resolve-and-re-raise deliberately leaves alone, since that fix exists
> *because* an in-place escalation is inaudible. A check asserting the
> predicate answers `match` either side of the fix, which is
> `check_review_schedule_unread`'s defect. It is carried as a **premise**
> in the detail; the verdict is driven, entering at `_raise_judged`
> rather than at `_refresh_open` because the fix may land in either.
>
> **The drive says something sharper than the entry does.**
> `SNAG-AGENT-009` made a held row's *sentence* correctable, so what a
> poll leaves behind is not a stale row but an internally inconsistent
> one: `message` reading *"the unit did not come back when the lease
> released"* at `severity: info`. A check reading `_refresh_open`'s
> boolean would have reported the row brought up to date.
>
> **Two things only running it could have said.** The first draft's four
> statements were **unqualified**, so `query_one` — which opens a
> connection with no `search_path` — resolved `log_entries` to `public`
> and every one answered `ProgrammingError`, reported as *"the database
> did not answer"*: a sentence about an unreachable database over a
> wrong statement, green verdict, silent population. And **one of
> fourteen mutations passed against every test in the class**: a drive
> aimed at `_refresh_open`, one level below the fork, where the author
> supplies the `raised = 0` by hand because they put the standing row
> there. `_suppressed` is the third-party witness inside the subject —
> `_raise_judged` writes it and `_refresh_open` never does.
>
> **`_refreshed` was briefly in that premise and the fix stand-in is
> what removed it.** That counter is incremented *inside*
> `_refresh_open`, so `step_for`'s shape — which replaces that method —
> leaves it at zero with the hold plainly fired, and the check reported
> `unknown` over a landed fix. A control the fix breaks, caught by the
> one stand-in written to model the fix rather than the defect.
>
> **A pre-existing red was found and repaired, and it was a box-wide
> selector again.** `tests/test_quietened_judgement_live.py` asserted
> `result.details["resolved"] == 0` — the **whole run's** sweep — while
> meaning "no resolve-and-re-raise under this drive's own title". The
> judge's two live dev-server breaches (3110, 8110) made it 2, so the
> test was red on any box with an editor open and green otherwise:
> `SNAG-TEST-004`'s class one file over, and seasonal. Verified
> pre-existing at HEAD by stashing before blaming this sitting's work.
> The scoped count still turns red under a modelled resolve-and-re-raise.
>
> **The folded row led with a step that cannot work, and the thing that
> proved it was the timer nobody was looking at** (2026-09-02, Session
> 151). `SNAG-SVC-003` is **fixed**. `_folded_row` took `action` from
> the anchor, so `alfred-career-mail-timer` led with
> *"POST /api/sysadmin/services/alfred-career-mail-timer/restart"* — a
> remedy that re-arms a schedule that was never the problem, while the
> step reaching the failing job sat three lines below it in the row it
> had swallowed. `STEP_SUPERSEDES` names the kinds whose step reaches a
> unit the anchor's cannot, and today that is `timer_failed` alone,
> because its step operates on the **triggered** service.
>
> **Rule 4's refusal stands and only one field moved.** Cause-first
> anchoring was put to the owner in Session 149 and refused; the title,
> the points, the rung, the grade and the evidence are still the
> anchor's. Live either side: `alfred-career-mail-timer` leads with
> `journalctl --user -u alfred-career-mail.service -n 100`,
> `venture-chat` is unmoved, and the endpoint holds **6 rows and 83
> points** both before and after.
>
> **The entry's discriminator was one it did not name.** It scopes the
> defect to "a timer fault", which points at repairing the outage row
> whenever the subject is a timer. Two timers carried an outage row that
> morning — `alfred-career-mail-timer`, folded, and
> `pgbackrest-backup-timer`, whose job had started succeeding the day
> before and which therefore produced no `timer_failed` row at all.
> **Both got the identical restart step and only the folded one's was
> wrong**, because for an armed timer whose *unit* went inactive the
> restart is right. So the condition that refutes the step is exactly
> the condition that folds, and the subject-keyed implementation is a
> driven mutation that only `pgbackrest-backup-timer` lands red.
>
> **The promotion would have dropped the anchor's step**, which is
> `_folded_row` rule 4 facing the other way: the tray and
> `health_review` render `title`, `detail` and `action`, and `members`
> is none of the three. The superseded step is named in the `detail`
> with the finding the leading step belongs to. The step itself was
> **run** and reaches a SQLAlchemy insert error in Alfred's ingest at
> 08:20:25 — that repository's to fix, and already its SNAG-50.
>
> **One of the nine tests was written twice and the first could not have
> failed**: it drove a lone `timer_failed` row, which no implementation
> can get wrong, since `recommend` never folds a group of one. Nine
> mutations, each red on the right test; 19 snag checks unmoved by
> stash. `SNAG-SVC-004` is the filed residue — the provenance line lives
> in `detail`, and the weekly review projects every field but that one.

> **One fault occupies one row now, and the entry that asked for it had
> measured half of its own population** (2026-09-02, Session 149).
> `SNAG-SYSD-006` is **fixed**: `group_faults` and `_folded_row` in
> `service_recommendations.py` fold a service's `EVENT_ARGUED` findings
> into one row that **names** every finding it swallows —
> `log_actions.group_incidents`' treatment, applied at a relation that
> has no clock and no systemd graph in it. Live either side,
> `GET /api/services/actions` went **8 rows → 6** and
> `alfred-career-mail-timer` occupies one row carrying both its
> findings.
>
> **`total_recoverable_points` is 78 before and 78 after**, which is the
> invariant that decided the arithmetic rather than a happy result: an
> anchor keeping only its own share would have taken the same box's
> total to **53** on the day the list got easier to read.
>
> **The entry scoped the defect to timers, and running the endpoint
> found a second instance it never named.** `venture-chat` has served
> `outage` at 26 points beside `flapping` at 25 since the endpoint
> shipped on 2026-08-25 — eight days, one service named twice, no timer
> in it anywhere.
>
> **Two controls belonging to a *different* open entry decided the
> design.** `SNAG-SVC-001`'s check finds its row by a **top-level** scan
> for `kind == "check_interval"` and its subject produces exactly
> `flapping` + `check_interval`, so the obvious "one row per service"
> would have reported a live entry refuted; its third limb reads this
> module's **import set**, so reaching for `group_incidents` by
> importing it would have refuted the same entry from the other side.
> Driven by stash before and after: all 18 snag checks unmoved.
>
> **The fix had to land twice.** `health_review._service_facts` projects
> the anchor's `title` and `action` into the weekly review, so the first
> version named one finding and never said the other existed — the
> roll-up that cannot name anything, one consumer downstream of the fold
> that promised not to. `SNAG-SVC-003` was the filed residue — the
> folded row leading with the anchor's step, and for a timer fault the
> swallowed step being the better one — and it was **closed the same day
> by Session 151**, one field wide.

> **A `kind: timer` check read the wrong unit for its whole life, and
> two silent failures were standing behind it** (2026-09-01, Session
> 147). `SNAG-SYSD-005` is fixed and deployed. The check asserted the
> **timer** was armed and recorded the **timer's** `Result` under the
> name `last_result` — a timer's `Result` reports whether the timer unit
> started, so it read `success` on **10** of
> 10 declared timers while one of the ten jobs had failed on twelve
> consecutive mornings. It now resolves the started unit from systemd's
> own `Unit=` property and reads that unit's `Result`.
>
> **It was found by reading another repository's snag, and it found a
> second fault nobody had filed.** Alfred's SNAG-50 reports
> `alfred-career-mail.service` failing every morning for 20 days with
> *"nothing surfaces this"* — the unit is declared in this repository's
> `services.yaml` and this check wrote **3,988 unbroken `ok` rows**
> across the outage. The first live run under the fix raised two
> criticals, not one: `pgbackrest-backup.service`, which
> `services.yaml`'s own comment calls *the only database backup on the
> box*, has failed **28** times and
> succeeded **zero** times since 2026-08-02, under 4,697 `ok` rows.
>
> **The half-state is what made it invisible from every other angle.**
> `pg_stat_archiver` reads `archived_count=5356, failed_count=0` with the
> last push minutes ago — **WAL archiving works**. So the repository grew,
> nothing errored anywhere, and nothing could expire, because
> `repo1-retention-full=4` is applied *during a backup*. Disk at 85 %.
>
> ***Two claims this entry made were overstated and the successful run
> refuted both — recorded here rather than quietly edited.*** It said
> *zero base backups* and *nothing to restore onto*. The run printed
> `last backup label = 20260307-141905F`: the repository held a **full
> backup from 2026-03-07**, taken **by hand at 14:19:05** — three minutes
> before the timer was enabled and three and a half before the broken
> unit was written. So recovery was possible throughout, to a
> **178-day-old** base plus ~5,356 WAL segments of replay: slow and
> fragile, not impossible. The error was inferring an empty repository
> from 28 unit failures without being able to read `/var/lib/pgbackrest`,
> which needs root — a population measured from the *caller's* failures
> rather than from the store, which is `ports_checked`'s rule turned
> around and pointed at this repository. Corrected at estate-manager as
> message `cc5f26e7`. *The `pgbackrest.conf` placeholder comment was also
> read as a second defect and is cosmetic — 5,356 archive-pushes prove
> pgbackrest parses that file.*
>
> **One authoring error, three instances, two files** — a directive split
> across two lines with no trailing backslash, found by
> `systemd-analyze verify` rather than by reading. `ExecStart=` loses
> `backup` (hence `[030] no command found`); `Description=` loses
> `Alfred`; and in the **timer**, `OnCalendar=*-*-*` loses `02:00:00`, so
> systemd resolved it to `*-*-* 00:00:00` and the backup that was written
> to run off-peak at 02:00 — `IOSchedulingClass=idle`, `Nice=10` — has
> been firing at **midnight** all along.
>
> **Neither fault is this repository's to fix** — the monitor does not
> own what it monitors, the units need `sudo`, and both were spoken and
> filed: estate messages `e5d17a89` (Alfred, the career-mail record),
> `aacd7e33` (estate-manager, the backup, routed there because
> `pg1-path` is the whole cluster and the stanza is merely *named*
> `alfred`) and `cc5f26e7` (the correction above).
>
> **`SNAG-SYSD-006` is confirmed and stays open** (2026-09-02, Session
> 148). The entry opened as a *prediction* — that once a failed job's
> `critical` checks accumulated past a rounding boundary, one fault would
> produce two advice rows — and named the re-read that would settle it.
> It did: `GET /api/services/actions` now serves `alfred-career-mail-timer`
> **twice**, an `outage` row at 5 recoverable points beside a
> `timer_failed` row at 0, off 101 `critical` checks standing unbroken
> since the first poll under the fix. `pgbackrest-backup-timer` serves
> one row and the survivor is the `outage` one, which is the entry's
> argument for refusing the cheap fix demonstrated rather than asserted.
> The remedy is `group_incidents`' treatment — a roll-up that names what
> it swallows — and that is a `KIND_ORDER` design question, not a patch.
>
> **The backup half is resolved.** The owner applied
> `scripts/fix-systemd-continuations.py` to both units at 22:19 and
> reloaded at 22:29; the run took **16.4 s**, `Result=success`,
> `ExecMainStatus=0`, wrote `20260307-141905F_20260901-222905I` and ran
> `expire` for the first time since March. `next_elapse` is now **02:00**
> rather than midnight. The career-mail half is Alfred's and stands
> open.
>
> **`SNAG-AGENT-011` is closed, and it closed on the limb that needed a
> night rather than on the commit** (2026-09-01, Session 146). The
> nightly `venture-chat unreachable` row opened at **00:01:16** at
> `info` — not `critical` — resolved at **05:51:19**, and carries
> `details['arbitration']` naming the lease, the profile and
> `stopped_by_estate: true`. The box was not stale: the daemon has served
> the fix since 2026-08-31 09:36:14, which is **8m36s before** the commit
> that carried it, because this repository restarts to verify and commits
> afterwards.
>
> **The check's headline could not close it, which is the conjunction
> working.** `sysadmin-check-snags` returns on limb 2 — a reader of
> `stopped_units` now exists — before any limb-1 branch can run, so limb
> 1's verdict was taken by neutralising the outer gate, and it refutes by
> the right one of three branches: *a quietening rather than a
> suppression*. The three readings the check said it could not separate
> were separated by hand and all three refuted — `mute_services` is
> empty, three post-deploy rows each carry a real granted lease, and
> `stopped_by_estate` is true on every one. So the population did not go
> quiet; only the rung moved.
>
> **The check retired with the entry and the detector did not**, for the
> sixth time. `TestTheDeployedQuieteningLive` reads the live `alerts`
> table and is stronger than the limb it replaces: limb 1 rebuilt a
> window from another project's timer, which moved on 2026-08-25, while
> these read the blob the fix writes. Its anti-vacuity pin is the
> load-bearing half — driven at a pre-fix world the two behavioural
> tests **skip**, so without the pin a box that never deployed the fix
> reads green. The register is now **18 of 22 open entries checked**, and
> `SNAG-AGENT-012` and `SNAG-AGENT-013` were deliberately not built:
> both were filed with measured-zero populations precisely so that this
> closure would not spawn them.
>
> **No restart is owed**: nothing the daemon imports reaches
> `snag_claims.py`, and the deploy check compares mtimes and cannot tell.
>
> **The reviews park now, and the number the owner settled is a deadline
> rather than a duration — which is what makes it work** (2026-08-31,
> Session 142). `SNAG-SCHED-003` and `SNAG-SCHED-001` both **closed**.
> The three weekly reviews take a GPU lease from the estate's arbiter
> through `estate.queue` and wait for the grant; `sysadmin/core/gpu_lease.py`
> is the module, `LLMClient.generate` gained `gpu_lease_held`, and no slot
> moved. Both checks retired with their entries; the guard did not.
>
> **One deadline, three budgets derived from it.**
> `schedules.review_lease_margin_minutes` (5) puts the deadline at
> `briefing_hour` less the margin, and each review subtracts its own
> dispatch instant: **3300, 2400 and 600 s** from 05:00, 05:15 and 05:45.
> Three independent leaves were refused because they say the wrong thing
> about the mechanism — `Arbiter.tick` returns early while **any** lease
> is granted and `_oldest_waiter` orders by `requested_at` across every
> profile, so the three are not waiting three lengths, they are waiting
> for **one instant** from three starting points.
>
> **estate-manager's close note corrected the arithmetic and the
> correction does not bite.** `_drop_overdue_waiters()` runs **first** in
> every tick, before the grant, so copying their `REVIEW_WAIT_SECONDS` of
> 1800 drops the 05:00 job at 05:30 — fifteen minutes early — and the
> 05:15 job by 22–72 s, which is the nasty one because it fails by a
> fluke-sized margin. Every deadline-derived budget ends at 05:55, past
> the whole recorded release band of 05:45:15 → 05:47:18. Verified in
> their source rather than taken from their message.
>
> **The blocker was not in the handoff and it belonged to another
> repository.** `POST /api/queue/acquire` answers `404` for a profile not
> in their `service/profiles.yaml`. Filed as message **`dcae132c`** with
> the cost and the FIFO consequence stated **before** the commit; they
> landed `sysadmin-review` (`stop: []` / `start: []`) the same sitting.
> The code shipped pre-staged behind a test gated on the profile
> appearing, so the sitting was never parked.
>
> **The checks were briefly wrong in the direction this family is named
> for.** Both read source, and source cannot see a `404`: the moment
> `gpu_lease.py` existed they reported `mismatch` over a Monday that
> still cost three narratives — `SNAG-SCHED-002`'s false retirement one
> sitting later and by the opposite route, the *remedy* promoted before
> it worked rather than the symptom promoted to the remedy.
> `_review_profile_published` made the arbitration limb a conjunction
> with the arbiter's own roster, every way of not-knowing returning
> `None` rather than `False`, and both went back to `match` until the
> profile landed an hour later.
>
> **Driven live, and the drive caught the fix working at a moment nobody
> arranged.** Lease 39, `wait 3300s, hold 600s`; the arbiter logged
> `lease 39 waits: GPU floor 26% over threshold 25%` and **parked it** —
> the whole entry in one line, because the old gate raised `GpuBusy` at
> that same 26 % and served a digest. `wait_deadline` came back at
> request plus exactly the derived 3300 s. Writing that drive also found
> a defect reading the code had not: `estate.queue.acquire` defaults
> `base_url` to its own `127.0.0.1:8400` and this module passed none, a
> second spelling of the estate's address in a process that already
> reaches it through `agents.estate_judge.base_url`.
>
> **Two follow-ons in the same sitting.** `ideas.md`'s GPU-gate-split
> entry is **dead by premise rather than by arithmetic** — the waiterless
> callers no longer reach the gate, so the window's population is zero
> and no recalculation revives it; marked rather than deleted, because it
> records estate message `df4113cb` being declined. And `HANDOFF.md`
> gained a **`## Scheduled action`** section, so a dated measurement stops
> occupying the one line the estate board publishes. Its two shape rules
> come from estate-manager's `roadmap.py`, and the second was driven as a
> counterfactual and fires: a `- [ ]` there, with `## Next action`
> renamed, made their parser publish the 2026-09-07 reading as this
> repository's next action. Guarded by `tests/test_handoff_shape.py`;
> announced as message **`8e693e05`** before the commit.
>
> **Two findings after the work, recorded rather than fixed.**
> `SNAG-AGENT-011` (**P2**, and the only unchecked open entry): the
> estate's arbiter stops `venture-chat.service` under a lease and this
> repository announces it `critical` — the one rung the tray leaves on
> screen — standing **~5h45m nightly**, the drain's hold to the second.
> The discriminator is `active_lease.stopped_units`, live on a surface
> `sysadmin/estate/client.py` already reads. Re-measuring before filing
> is what made it accurate: the obvious figure is **181 rows all-time**
> and **161 fall on 2026-08-11 → 08-14**, before the estate's queue owned
> the swap, so the entry carries the current regime's **20 of 23**. And
> commit `30bfbea` shipped `claude-preflight.sh` **without its execute
> bit** — a falsification's Python-written backup `mv`'d back over it —
> so the one script every sitting starts with answered `permission
> denied` while the suite, ruff and the pre-commit hook stayed green,
> because a mode is not content. Both fixed or filed; a sweep over
> `scripts/*.sh` guards the second.
>
> **Still owed: one reading, on 2026-09-07** — `llm_used` on the three
> review tables and the four grants and their order in the estate's
> journal. Prediction: **true, true, true**, health granted first at
> ~05:46 and disk last, behind estate-review.
>
> ---
>
> **The prediction came true and the mechanism came with it — and the
> ranking in the entry's own headline did not survive the morning**
> (2026-08-31, Session 141). `SNAG-SCHED-003` predicted **false, false,
> false** for the three `llm_used` values this box writes on the first
> Monday since the drain moved to 00:00. All three are `false`:
> `health_reviews` 05:00:03.92, `log_reviews` 05:15:00.06,
> `disk_reviews` 05:45:00.43. **No code changed this sitting.**
>
> **A false is not by itself a confirmation, which is the entry's own
> quieter half.** Nothing on those three surfaces separates *skipped for
> contention* from *llama-server was down*, so the stored flag is the
> prediction and the journal is the mechanism: each row is preceded by
> `llm_gpu_busy` from `sysadmin.core.llm_client` carrying `busy_percent`
> **99, 97 and 98** against `threshold: 25`, and followed within
> milliseconds by its own `*_llm_unavailable_used_fallback`.
> `alfred-inference.service` was `active` throughout — the alternative
> cause is refuted rather than assumed away — and
> `venture-enrich-nightly.service` finished **05:46:11**, a sixth
> consecutive night inside the recorded band.
>
> **The estate paid the identical fault the same morning and kept its
> narrative.** It took lease 38, polled **16 m 21 s**, was granted at
> **05:46:20** — nine seconds after the drain released — and generated in
> about a second. Same card, same drain, same hour: it waited and got its
> narrative while this repository read the card once at each of three
> slots and served three digests into the 06:00 briefing. The two nights
> the entry cites for them are 08-17 and 08-24, *before* they changed;
> this is the first night the two designs have been seen side by side
> under one holder. **The lease fix is licensed outright.**
>
> **The refutation is of our own headline, and the error is the
> instrument.** That headline says *two of the three* reviews are worse
> off, ranking disk least affected at **5 of 12, 42.5 %** over ±300 s.
> `ensure_gpu_idle` reads at the **dispatch instant**, 05:45:00.43 —
> **71 seconds** before the release — so disk lost too. A ±300 s mean
> straddles the release and reports as half-clear a slot that was fully
> occupied when it was actually sampled. The priority does not move: it
> was argued from three narratives, never from which is worst.
>
> **The check reproduces the refuted ranking and its verdict is still
> right.** Driven after the observation it reads `disk_review 6/14 busy`
> and names `generating into a held card: health_review, log_review` — by
> the same majority rule that produced the 5 of 12. The conjunction holds
> through health and log, so the entry stays green for the right reason;
> what is wrong is the sentence beside the verdict. Left as measured,
> because moving the sample to the dispatch instant changes the check's
> witness and belongs with the fix.
>
> ---
>
> **The measurement named the wrong contender, and the box had already
> recorded the right one** — `SNAG-SCHED-001` owed one number before its
> two fixes could be ranked. Taking it re-ranked the entry instead.
> Three findings, each from this box rather than from the estate's prose:
>
> **This repository gates, and its own check could not see it.**
> `sysadmin/core/llm_client.py:134` calls `ensure_gpu_idle(...)` from
> `estate.gpu` at a threshold of **25** — one pre-dispatch read, then a
> digest. The entry's AST walk searched `estate_queue`, `wait_for_dgpu`
> and two literals, found none, and the sentence it supported read
> *"neither party is gating"*. The walk was right about its four names;
> the generalisation was not. Filed and fixed as `SNAG-SCHED-002`, and
> **the obvious repair is the harmful one**: promoting `ensure_gpu_idle`
> to the refuting set retires `SNAG-SCHED-001` on the strength of a gate
> that predates it by eighteen days and fixes nothing. The vocabulary is
> split by what a gate *does* — arbitrating gates refute, deferring ones
> are reported as evidence and never can.
>
> **The occupant at 05:45 is `venture-enrich-nightly`, not the estate.**
> This box's own journal: the drain finished **05:47:18, 05:45:15,
> 05:46:58, 05:45:22 and 05:45:26** on 08-26 → 08-30 — *the same five
> values the estate published as its granted band*, so their band is the
> drain's finish and their review is granted after it. Every one is
> after our 05:45:00 dispatch. `resource_snapshots` corroborate in two
> signals at once: **99 %** busy at 05:44:45 on 08-30, and
> `vram_used_mb` **19,870 → 11,112** across the release.
>
> **A generation takes under six seconds, so the two never overlap.**
> The real prompt dispatched raw gives **80.0 tok/s** solo and **62.4**
> with two in flight — a **22 %** per-stream cost, both completing,
> nothing failing against a 120 s timeout. Session 79's fifteen-minute
> spacing was over-provisioned by two orders of magnitude and was never
> the scarce thing. The drain's **5 h 45 m** is.
>
> **Which makes the chain the entry, not the slot** — `SNAG-SCHED-003`,
> filed P2. Since the drain moved to 00:00, health **12 of 12** samples
> busy and log **12 of 12**, against disk's **5 of 12**: the two reviews
> the entry does not mention sit squarely inside an occupancy no
> schedule leaf reaches, and only a lease reaches all three. The estate
> meets the identical fault and **waits** up to 1800 s for its
> narrative where we defer and lose ours — which is the ranking
> inverted, since the entry priced the lease as the expensive option.
> Unobserved so far: no Monday has run in the new regime, **2026-08-31
> is the first**, and the prediction is false, false, false.
>
> ---
>
> **The gauge moved and the threshold deliberately did not** — estate
> message `d1939cf7` is **acted on and closed**. estate-manager's
> weekly review now *takes* a GPU lease instead of sampling a counter
> (their ADR-0076/0077), so it queues behind `venture-enrich-nightly`
> every Monday 05:30 and waits **915–1038 s** across the five nights
> they measured. This repository judges `oldest_waiting_seconds > 900`
> and says *"Either a holder never released, or the arbiter's tick loop
> has stopped granting"* — so the first alert would have arrived on a
> Monday morning, said the queue was starved, and been **wrong**.
> `judge_queue_invariants` now reads
> `oldest_unexplained_wait_seconds`, the same number with that third
> cause masked out by the producer. **900 is unchanged.**
>
> **Raising the threshold was the obvious fix and buys nothing.** At a
> bigger number the gauge still cannot separate a normal Monday from a
> stuck queue, it only says so later — and the Monday wait is bounded by
> *another repository's* timer, so any number clearing it is one
> schedule change from being wrong again. `config.yaml` carries that
> refusal beside the leaf now, because the leaf is where a future Monday
> false alarm sends someone.
>
> **Three rules, two of them the opposite of the obvious
> implementation.** The mask is **read, never recomputed** —
> reconstructing it from `waiting_reason` would be a second
> implementation of the producer's derivation, `SNAG-DB-003`'s shape, so
> a test drives an *inconsistent* payload and asserts the field wins.
> **Absent is not masked** — `payload.get(...)` answers `None` both for a
> producer that explained the wait and for one that does not publish the
> field, and collapsing them retires this family in silence the day the
> estate rolls back, so a payload without the key falls back to the old
> gauge and labels the row `wait_gauge: "total"`. And **the reason is
> named because the producer names it**: the two values that can still
> reach a row are exactly the disjunction's two limbs, which is what
> makes the existing sentence true again.
>
> **The trade is stated: a survivable absence is a silent one.** The
> fallback means the new field vanishing is invisible to every
> fixture-driven test, so the only place it can be loud is the live half
> — `test_the_wait_discriminator_is_still_published`. The three states
> are pinned against payloads built by running the estate's own
> `Arbiter.submit` → `tick` → `invariants` in their venv against a
> **scratch** database, never the live `estate` one, which estate rule 1
> forbids writing. The 2026-08-16 fixture is kept unmodified as the
> **legacy-producer** specimen, and a test fails if anyone hand-edits it
> into the new shape.
>
> **One snag opened beside the work: `SNAG-SCHED-001`.** Reading *why*
> the estate's review now takes a lease showed that it displaces **where
> it generates** from 05:30 to the grant — 05:45:15–05:47:18 on their
> five measured nights, which is this repository's disk-review slot at
> **05:45**. Neither party gates: an AST walk over `sysadmin/` finds
> **zero** bindings of `wait-for-dgpu`, `/api/queue/lease` or
> `estate_queue`, and the estate's lease arbitrates it against
> `venture-enrich-nightly` rather than against us. The entry claims less
> than it could — nobody has measured what two concurrent generations
> cost, so what is claimed is that Session 79's fifteen-minute spacing is
> now **false and unmeasured**, with the one deciding measurement named.
> Its check is a conjunction, because either of the two fixes must refute
> it or it is a control that survives its own remedy.
>
> **It ships untriggered**, which is why it was driven rather than
> reasoned about: `alerts` holds **0** `Estate queue…` rows all-time, so
> nothing standing needed reconciling and no fixture could have told us
> so. Ten mutations of the predicate and eight of the fixture and live
> guards were each driven and each lands red on the test that owns the
> rule. **+23 tests, 3125 → 3148**, suite green, `ruff` and `mypy`
> clean. **No ADR** — the last estate message got one because it carried
> `needs_ruling=true` and asked a question; this one is
> recommendation-only and the reasoning lives in the docstring beside
> the predicate.
>
> *Previously —* **The measurement refuted the remedy rather than sizing it, and the
> entry stays open as a deliberate non-fix.** `SNAG-TRAY-011` asked
> whether `sysadmin-tray` should gain a
> `log: {type: journalctl, severity_filter: warning}` block so
> `SNAG-CFG-005`'s config-key warning becomes an alert row. **It should
> not.** The block is inert at **two independent gates**, and the sitting
> that was told to measure volume found the mechanism instead.
>
> **Gate one is the priority stamp — `SNAG-AGENT-008`'s priority half,
> one program over.** `sysadmin-tray.service` has written **677,567**
> journal records over **19.49 days** (2026-08-11 → 2026-08-30), and
> **every one is `PRIORITY=6`**. `main()` calls
> `basicConfig(format="… %(levelname)-8s …")` — a text formatter emitting
> no `<N>` prefix — so systemd stamps captured stdout `6` whatever the
> level inside says, and `SyslogLevelPrefix=yes` on the unit strips a
> prefix nothing writes. `max_priority_for("warning")` is **4**, so the
> declared source reads `journalctl -p 4` and ingests **nothing, ever**.
> `journalctl --user -u sysadmin-tray -p warning` over the unit's whole
> recorded life returns **no entries**.
>
> **Gate two is the alert family, and it fails even if gate one is
> fixed.** `FAULT_SEVERITIES = ("error", "critical")`, and the ingest
> loop `continue`s on anything else — so a `warning` line is **stored and
> raises nothing**. A working prefix moves the line from `info` to
> `warning`, and both sit below the family's floor. The entry reached
> neither gate because it reasoned from the tray's *Python* level rather
> than from the journal's stamp and the consumer's floor.
>
> **The prerequisite is refused by the rule that established the
> prefix.** Reusing `JournalLevelPrefixFormatter` is legal — the tray
> already imports from `sysadmin.core` and the boundary forbids only the
> reverse — but that class extends `JsonFormatter` deliberately: Session
> 61 rule 2 holds that only the JSON formatter guarantees one line per
> record, since under a text formatter a traceback's first line is
> stamped `ERROR` and its body left `info`, *"worse than the uniform 6
> because it looks fixed"*. Making the tray's levels reach the journal
> means moving a GUI program to JSON logging.
>
> **The only reachable branch pays the whole cost and buys none of the
> benefit.** `severity_filter: info` is not inert — it ingests
> everything: **34,762 rows a day**, ~**1.04 M** at 30-day retention, for
> a source with **zero** `WARNING`/`ERROR`/`CRITICAL` lines in its entire
> recorded life. And it still raises nothing, by gate two. So
> `SNAG-LOG-004`'s warning bounds the one branch that is not already
> inert, which is the reverse of how the entry weighed it.
>
> **Nothing was fixed and nothing was closed.** Both of the check's
> channels are unmoved, `check_tray_report_unheard` still reports
> `match`, and its P3 is now confirmed rather than inherited. No code
> changed this sitting.
>
> *Previously —* **The section neither program watched has a watcher, and the two
> defects worth carrying were found by running it rather than reading
> it.** `SNAG-CFG-005` is **closed**. `sysadmin_tray/config.py` reports
> the keys under `config.yaml`'s `tray:` that its own allowlist does not
> read — one set difference against `TRAY_SECTION_KEYS`, warned and never
> refused. It ships **untriggered**: the shipped `tray:` carries six keys
> and every one is read, verified by restarting the real tray.
>
> **The obvious fix shape would have shipped green.** A walk of `tray:`
> against `TrayConfig`, the way `core/config_keys.py` walks `config.yaml`
> against `AppConfig` — legal, since the import boundary only forbids the
> reverse — and wrong: `TrayConfig` declares **19** fields and the section
> supplies **7**, the other twelve arriving from `notifications.tray:`,
> `api:` and `services.yaml`. A model walk calls `tray.reminder_hours: 5`
> declared when setting it there does nothing. The model over-declares
> relative to the section; the allowlist does not.
>
> **Two defects the entry did not know about.** `tray: 5` **crashed the
> tray** — `key in 5` raised `TypeError` out of the one section this
> module hand-parses, unhandled, while `_read_services` next door costs
> "a mute list, not a launch"; it is `unwalkable` now. And
> `tray.api_url` has **never** been read while the loader docstring
> promised it since `81b3bfb`, the module's first commit — the
> `if "api_url" not in kwargs` guard beneath was dead by construction and
> its comment is what the docstring copied. Both went, because a reader
> checking the new report against the old docstring concludes the
> *report* is broken.
>
> **A convention copied without the formatter that makes it work.** The
> first version wrote `logger.warning("tray_config_unknown_keys",
> extra={"keys": …})` — the backend's idiom, readable only because
> `JsonFormatter` folds `extra` in. The tray's formatter is
> `basicConfig(format="… %(message)s")`, so the live journal line was the
> bare event name, announcing that a key was dropped and unable to say
> which: this entry's own defect one level down. Caught by driving it
> through the real formatter, not by reading it.
>
> **`SNAG-TRAY-011` is the residue, filed rather than absorbed**: the
> warning reaches `journalctl --user -u sysadmin-tray` and nothing else —
> `composed_log_sources` returns **15** units and `sysadmin-tray.service`
> is not among them — and fires once, at startup, where the backend
> re-reports on every `POST /api/sysadmin/reload`. **3109 → 3125**, +21
> and 5 retired. Seven mutations driven, each red on the test about its
> own rule; an eighth landed red **by accident** and exposed a rule with
> no guard, and two of the new check's own tests were false greens — one
> aimed its stand-in past the decision, the other patched a function the
> check no longer calls.
>
> *Previously —* **The entry's headline fix does not boot, and one walk of the shipped
> file said so before a line of it was written.** `SNAG-CFG-004` is
> **closed**. It asked whether `sysadmin/core/config.py`'s 37 models
> should set `extra="forbid"` as `sysadmin/monitor/services.py`'s four
> do. Walking `config.yaml` against `AppConfig`'s field tree finds **ten
> keys the backend does not declare** — the top-level `tray:` section and
> nine leaves under `notifications.tray:`, every one read by
> `sysadmin_tray/config.py`, which parses the same file for itself. So
> the forbid is not a trade-off to weigh against `SNAG-DB-005`; it is a
> daemon that will not start on this box **today**, and a test builds the
> strict subclass and asserts exactly that.
>
> **The asymmetry the entry read as an inconsistency is structural.**
> `services.yaml` can forbid because every key in it belongs to the
> process holding the models; `config.yaml` cannot, because it carries a
> region this process does not own. One file, two parsers, neither a
> superset — which is also why `schema_guard`'s posture runs the *other*
> way here: that guard refuses because serving against the wrong schema
> is worse than not serving, and serving with an ignored config key is
> demonstrably not, at a cost of one briefing at the wrong hour.
>
> **What shipped reports and cannot refuse**, settled by the shape of the
> mechanism rather than a flag someone could flip: `core/config_keys.py`
> walks the raw YAML against the model tree and **returns a list**. The
> boot warns and `ReloadReport.unknown_keys` carries it to
> `POST /api/sysadmin/reload` — the surface an operator who has just
> edited the file is actually holding. Live, a real `briefing_hourr: 9`
> in the shipped file came back as
> `{"ok": true, "unknown_keys": ["schedules.briefing_hourr"]}` and the
> reload still delivered everything else.
>
> **The boundary is declared and pinned, never asserted.** `FOREIGN_KEYS`
> names the tray's ten; `sysadmin.core` may not import the tray, so its
> two key lists were lifted to constants and a test asserts the pair
> agree. Exempted **by leaf, not by subtree** — `mute_services` is read
> here, so a subtree exemption would silence `mute_servicess` on the one
> key under that section the backend depends on — which pays a dividend
> nobody asked for: a misspelt *tray-owned* leaf is reported too.
>
> **The check retires and its meaning inverts.** It counted
> `extra="forbid"` on both sides and **this fix moves neither count**, so
> it would have reported *still holds* over a landed closure
> indefinitely — `check_review_schedule_unread`'s defect one entry
> earlier. The detector is re-homed as
> `TestTheAsymmetryIsDeliberateAndStays`, where those counts must now
> **stay** put.
>
> **3079 → 3107**, +28 and 5 retired. Twelve mutations driven, each red
> on the tests about its own rule — and **two passed against
> deliberately broken code first**: the subtree mutation changed nothing
> because `notifications.tray` is not itself in `FOREIGN_KEYS`, and
> adding `ConfigDict(extra="forbid")` to a config model gave a
> *collection error* rather than a red test, since that name is not
> imported there — a stand-in that cannot compile is silence wearing a
> result. `SNAG-CFG-005` is filed for the residue: a typo inside `tray:`
> is dropped by **both** parsers in silence, measured rather than
> assumed, since the tray half was expected to be strict and is not.
>
> *Previously —* **One gate, two answers, and the library's own
> tie-breaker decides it.** estate-manager's message `df4113cb` is
> closed: `core/llm_client.py`'s single `ensure_gpu_idle` read is reached
> by three gates that each have both a waiterless Monday job and a
> request-holding route, so the library's own rule — *a caller that
> cannot answer the question for every invocation keeps the single read*
> — settles it. The split was costed and refused (one narrative every
> forty weeks against a parameter threaded through three signatures) and
> filed in [ideas.md](ideas.md), not declined. Of the six reviews this
> box has generated, **five came from the routes and one from the Monday
> job**, so the docstring calling this inference "deferrable
> housekeeping" was backwards and is gone. 3060 → 3070.
>
> *Previously —* **Twenty-four dead links were three classes, not one, and the middle
> class is the one a plausible path would have made worse.**
> estate-manager's message `25be77ba` is **closed**: all 24 inward links
> in `snag_list.md` (14), `project-capability-audit.md` (8) and
> `tasks.md` (2) resolve, and `tests/test_doc_links.py` is the detector
> that outlives the finding — the estate refused the check under its
> ADR-0073, which is exactly what leaves it here.
>
> **The instruments disagreed by one before a line was repaired, and
> mine was the narrow one.** A first scan found **23**: `line.startswith("    ")`
> treats a six-space *list continuation* as an indented code block, and
> `tasks.md`'s 24th link sits on one. CommonMark makes indentation a code
> block only when no list is open. Repairing on the strength of the first
> reading would have left one behind and reported twenty-four.
>
> **Three fates, and the middle one has no name in the filing.** **5**
> targets survived the 2026-08-08 split and take a path repair. **16**
> left under [ADR-0005](../adr/0005-project-state-leaves.md) and take a
> pointer. **3** are the trap: the *file* survived and the *cited symbol*
> did not — `config.py` lives at `sysadmin/core/config.py` and holds no
> `ProjectsConfig`; `briefing.py` lives at `sysadmin/briefing/data.py`
> and holds neither section builder. Repathing those three would have
> produced links that **resolve**, look right, and point at code that
> does not contain the claim — invisible to every instrument in play.
>
> **The true count is 27, and the estate said so in advance.** Their
> message called 24 a floor because their check is existence-only. A
> superset scan resolving `#L` anchors against the target found **3
> more** that resolve while their anchor has rotted: `main.py:123-128`
> at a blank line, `agent.py:391` at an unrelated docstring,
> `retention.py:85` at `"health_reviews": WHOLE_TABLE`. All three
> repaired.
>
> **No new line anchors were minted**, which is the rule rather than an
> omission. 13 of the 24 carried one and every rotted anchor above was
> once correct; an anchor decays invisibly to an existence check, so
> re-pinning them manufactures more of the defect being repaired. Each
> citation keeps its original line range as *text* — it is the evidence
> the entry rests on — beside a live link to the file.
>
> **3056 → 3060**, +4 and none retired. Two mutations, each red on
> exactly the intended test: a broken link reddens the corpus test, and
> reverting to the naive indentation rule reddens the continuation test
> and nothing else. Docs only — no production behaviour changed; ruff and
> mypy clean, and the snag register parses unmoved at **107 entries, 18
> open**.
>
> *Previously —* **The habit is a guard now, and it caught its author twice before it
> caught anything else.** `SNAG-TEST-002` is **fixed**:
> `TestEveryCheckCanSayItDoesNotKnow` sweeps `CHECKS` and refuses a
> registered check that no test class drives to an `unknown` verdict —
> the fourth sweep over that registry, beside the three asking whether
> the register and the registry agree about *which* entries are
> measured. **18 of 18** covered at the moment of the fix.
>
> **The check retired with the entry and its walk did not**
> (`FROZEN_TABLES`' rule, the sixth time here).
> `check_unknown_branch_unenforced` was written to detect its own fix
> landing, so `_unknown_branch_coverage` and `_unwritable_sentinel` moved
> into the drive and the check, `_sweep_enforces_unknown` and the
> registration went. The register reads **18 open**, every one carrying
> a check.
>
> **The sweep's own class is one of the classes it walks**, which is the
> part no reading would have found. The walk counts a class that names a
> key *and* asserts the verdict, so a docstring citing a check by key
> makes the sweep vouch for that check — itself. It fired on the
> docstring explaining the sweep, and again on the docstring written to
> explain the first firing, for naming the key while saying that naming
> it is what is forbidden. `test_live_drive_premises.py` exempts its own
> owner for this reason; there is no exemption here, so the prose is
> written around the key.
>
> **Two guards passed against deliberately broken code and both were
> repaired.** The second witness — is the class pin green because the
> class is clean, or because the walk is blind *here* — spliced a key
> into the class's real source and **failed**, since this class asserts
> no bare `unknown` constant and could never have been seen; both halves
> are appended now. And the class's name was restated as a constant, so
> pointing it at a *different* clean class left all fourteen green: it
> is derived from `type(self).__name__` instead, which makes that
> mutation impossible rather than merely caught.
>
> **`UNKNOWABLE` is the declaration the entry asked for**, empty by
> measurement — a check whose every input is local discharges the sweep
> by a name and a stated reason rather than by a branch that cannot
> exist, `PRE_CONVENTION`'s shape one file over, with tripwires for a
> stale name, an orphaned one and one with no reason. Driven at a
> stand-in, because a mechanism with no members is `SNAG-UNITS-006`'s
> standing.
>
> **The looseness is stated rather than tightened.** The walk keys on the
> class, so a class naming a key in passing counts —
> `TestChecksAgainstTheLiveBox` covers seven at once. Measured: **no key
> is covered only incidentally**. It is a floor on the habit, which is
> the measurement the entry named being promoted rather than a stronger
> claim invented in its place.
>
> **3055 → 3056**, +14 and 13 retired with the check, arithmetic checked
> against a stashed baseline. Eleven mutations, each red on exactly the
> intended test. One drive-by: the previous sitting moved a
> `# noqa: S404` off `import subprocess` onto `import uuid`, and
> removing the now-unused import would have taken it with it — it is
> back on the line it describes. No production behaviour changed; ruff
> and mypy clean.
>
> *Previously —* **The six pre-convention files were decided one at a time, and it went
> five ways to one.** The handoff asked whether they owe premise
> assertions. **Four owed one and had none**; one owed **the marker and
> never the premise**; one owes nothing. `test_schema_drift.py` is the
> strongest and was settled by driving rather than reading — its whole
> output is `diff == []`, and with `FROZEN_TABLES` widened to cover all
> **13** mapped tables (the blindfold that constant's own docstring
> warns about) `compare_metadata` returns `[]` as well. The guard could
> certify a comparison it had stopped making.
>
> **The witness is the same comparison pointed at an empty `MetaData`**:
> 13 `remove_table` ops normally, **nothing** under the blindfold. The
> other three: `test_schema_guard.py`'s two readers both answer `None`
> for a schema never migrated, so `async_answer == sync_answer` is
> agreement about nothing — and the sibling test in the same class
> already asserted `is not None`. `test_retention.py` owed two, both the
> silent direction the module is about. `test_logs_routes.py`'s
> `stored <= declared` is green over an emptied `log_entries`; measured
> **10 stored inside 15 declared**, five names of slack.
> `test_open_alert_predicate.py` already carried its witness, docstringed
> *"A constant observation is not evidence"* a fortnight before the
> convention existed.
>
> **The exemption is earned now rather than granted**, which is what
> makes the decision recorded rather than remembered. Rule 2's sweep
> accepts a file off the `_live` glob that **marks a premise**, so
> `PRE_CONVENTION` shrank **6 → 1** by five files holding the property
> instead of by five names being trusted. Driven both ways: dropping the
> new clause reports exactly those five, and stripping one file's marker
> reports exactly that file.
>
> **Two falsifications demonstrate the vacuous pass rather than
> describing it.** Under the blindfold the two new premise tests go red
> and `test_models_match_migrated_schema` stays **green**; over an
> emptied `log_entries` the new premise goes red and
> `test_every_stored_source_is_declared` stays green. Seven mutations in
> all, each red on exactly the intended test.
>
> **`SNAG-TEST-002` is the one opening, and it is the exemption's stated
> cost.** `test_snag_claims.py` owes no marker because its premises are
> enforced at the producer — `query_one`'s every way of not-knowing is
> `unknown` rather than `match` — and every registered check is driven to
> that branch by a test in the class that names it. Nothing enforces it,
> so `unknown_branch_unenforced` measures both halves and **caught its
> own author on its first run**, reporting itself as the one check with
> no `unknown` drive. 18 of 18 at filing, **19 of 19** once its own drive
> landed. Its witness needed the same lesson: spelled as a literal, the
> test asserting it wrote the sentinel into the file under the walk and
> two checks were reported covered by a verdict that does not exist —
> `_unwritable_sentinel()` mints one per call.
>
> **3042 → 3055**, +13 and none retired; **3033 → 3042** for the premise
> work, arithmetic checked against a stashed baseline rather than a green
> suite. No production behaviour changed. Ruff and mypy clean.
>
> *Previously —* **The sweep the handoff asked for cannot exist, and the pre-fix file
> is the proof.** `SNAG-TRAY-010` was an **absence**: at `62f8e09`, the
> commit that added it, `tests/test_desktop_store_live.py` named `dnd`
> **zero times**. An AST sweep keys on the *presence* of a token, so this
> one would have been hunting a line nobody wrote.
>
> **Three further measurements, each of which alone settles it.**
> Inverted to *must supply*, the rule is **4 false positives out of 5** —
> only `test_desktop_store_live.py` touches any of the three singletons
> (28 mentions against 0, 0, 0, 0), two of the drives being subprocess
> drives against a real bus and two never reaching `notifier.py` — and
> suppressing those needs the per-file allowlist the rule existed to
> remove. The read is **transitive**, `datetime.now()` sitting in
> `dnd.py:73` inside `is_active` among **27** unsupplied clock reads in
> production, so deciding which a drive reaches is a call-graph analysis
> over `sysadmin/`. And `should_suppress` **already takes a `now=`** it
> does not forward, so a signature-level check reads it as injectable
> and passes.
>
> **The premise assertion is the stronger control, not the weaker one.**
> A sweep answers *did somebody write the supply line* and stays green
> the day the supply stops taking; the premise answers *is the gate open
> now*, which is what the hour decides. `sent_total > 0` catches the
> class, since `min_severity`, `enabled` and a future fourth gate
> silence the announce path identically.
>
> **So the narrower guard shipped instead.**
> `tests/test_live_drive_premises.py`, 15 tests: every
> `tests/test_*_live.py` marks the test — or class — holding its premise
> with `@pytest.mark.premise`, seven markers across the five drives. The
> marker **names the check and never the value**
> (`SNAG-ESTATE-011`'s rule); a name rule was measured first and reaches
> **3 of 5**, because `TestTheHazardIsReal` names what it *proves* and
> `test_failure_replay_live.py` asserts a different premise per test.
> **The glob is a convention, so it is backed by a property**:
> `_opens_a_live_connection` finds the **6** files naming this box's
> database outside the glob, held in `PRE_CONVENTION` and re-asserted
> rather than trusted — without it the premise rule is opt-in by
> filename.
>
> **Three things measurement changed mid-build.** The detector
> **reported itself**, holding the spellings it hunts for, so the owner
> is exempted and then driven at. `addopts = "--strict-markers"` is
> **silently ignored on pytest 9.0.2** — the flag works from the command
> line and does nothing from `addopts` — so a comment claiming it
> enforced something was corrected to the ini option and pinned. And a
> falsification was **destroyed by its own revert**: `git checkout` on an
> uncommitted marker reverted the fix rather than the mutation, so one
> mutation silently re-tested the previous one's condition.
>
> **Seven mutations, each red on exactly the intended test.**
> **3018 → 3033**, +15 and none retired, arithmetic checked rather than
> assumed. No production change; ruff and mypy clean. The six
> pre-convention files are filed as a **task, not a snag** — the
> convention was invented in this sitting, so their exemption is a
> decision to take rather than a defect to record.
>
> *Previously —* **The six reds were the hour, not the tree — `SNAG-TRAY-010` is
> fixed.** `tests/test_desktop_store_live.py` supplies two leaves and
> says so in its own docstring: the transport, and the two clock
> readings. It misses a **third**. `DndManager.is_active` calls
> `datetime.now()` *itself*, so `should_suppress` reads the **real** wall
> clock whatever clock the notifier was handed — and the shipped
> `notifications.dnd.schedule` is `23:00 → 07:00` while the probes are
> raised at `warning`, which `allow_critical` does not exempt.
>
> **Which is why bisecting was a dead end rather than evidence.** The
> entry drove it at `62f8e09`, the commit that added the file, and got
> the same six — correctly. It is not a property of any revision. It is a
> property of the hour: Session 129 committed at **05:27** and wrote its
> handoff at **05:23**. Re-run at **09:37** on the same tree and the same
> commit, the file is **7 passed**, nothing changed.
>
> **The contradiction in the symptom was the discriminator.** *Silent,
> yet the rows are stored and adopted* looks impossible, because
> `_remember` runs only after a successful `send` — except in `_adopt`,
> which writes unconditionally. DND gates `_handle` before the send and
> the `due` filter before `_restate`, and gates adoption **nowhere**, so
> all three probe titles were adopted by a notifier that had never
> spoken. Proved three ways at 09:37 on an unchanged tree: the override
> on gives the six verbatim, off gives seven green, and the **schedule
> itself** widened to `00:00 → 23:59` — the real mechanism rather than a
> proxy for it — also gives the six.
>
> **The measurement the entry named first was right and generalises past
> its own cause.** `sent_total` is in the reading and asserted non-zero.
> Every other speech reading is a `bool` over a **slice** of `sent`, so
> none can separate *the sweep found nothing due* from *a gate above it
> refused everything*; the total can, because a sweep that merely found
> nothing due still leaves the announce-time sends behind it. Driven at
> `min_severity: critical` with DND off — a different gate in the same
> position — it fires, so it catches the class and not the member.
> `dnd_suppressing` is ordered ahead of it so a failure names the gate:
> unfixed, the loudest line was `spoke_unwatched is False`, a sentence
> about the sweep for a fault entirely above it.
>
> **One thing only the falsification found.** At `min_severity:
> critical` the drive **errored** rather than failing — `stored[…]`
> raised `KeyError` while *building* the reading, so the premise test
> written to name the cause never ran and seven errors said nothing. It
> is `.get`-shaped now: absent is a reading, a traceback is not, which is
> this entry's own lesson arriving inside its fix.
>
> **No production change, and that was checked rather than assumed.**
> `desktop.py`'s own comment already states that a suppressed reminder
> does not move the clock, so a fault raised inside the window is
> adopted, anchored, and speaks when the window lifts at 07:00. The
> defect was entirely in what the harness supplied. **3017 → 3018**, +1
> and none retired; three mutations driven, each red on exactly the
> intended guard.
>
> *Previously —* **`wiring` joins `ports`, and admitting it by name alone
> would have
> shipped green and inert.** estate-manager's message `8462bcc5` asked
> whether their hook-wiring check joins `ports` as a second audit check
> this repository speaks for. **Ruled: admitted** —
> [ADR-0006](../adr/0006-wiring-joins-ports.md). Every clause of
> `JUDGED_AUDIT_CHECKS`' ownership test transfers to
> `~/.claude/settings.json`: it is in **no repository at all**, it binds
> all thirteen, the estate may not alert, only the owner can wire it
> (their ADR-0024), nothing here reads `~/.claude` so there is no
> double-count, and they measured on 2026-08-29 that **nobody says it at
> all**.
>
> **The filter is a conjunction, and their message argues about half of
> it.** `wiring` emits **no `breach` at any code** — their ADR-0067 §4
> refuses one — so `JUDGED_AUDIT_CHECK = "wiring"` would have judged
> nothing for ever behind a green suite. Widening
> `JUDGED_AUDIT_SEVERITY` instead re-imports `ports`'
> `claimed_but_silent`, which is availability and already owned here by
> `% unreachable`. `JUDGED_AUDIT_CHECKS` is a **mapping** now,
> `{ports: breach, wiring: warn}`, the only shape in which both stay
> true; `JUDGED_AUDIT_SEVERITY` survives as a name and is **derived**
> from it, pinned by AST because CPython interns the string and a value
> assertion cannot tell derived from retyped.
>
> **Their stale observation was load-bearing, not a footnote.** They
> offered as fact that the comment says "all four" checks emit `breach`
> while the audit runs **twelve**. When every check emitted `breach` a
> single severity constant was unambiguously deference to the producer;
> across twelve checks at three rungs it had acquired a **second job
> nobody argued for** — it was also a check filter.
>
> **Driven against the real producer, because the family ships with zero
> rows.** `estate_service.audit.checks.wiring.run_check` in their venv
> at their commit `003f3bc`, public symbols only, against four specimens
> built from this box's live `~/.claude/settings.json`: clean → **0**
> findings, the 2026-08-25 top-level paste → **4** (one per hook), the
> truncated paste → **1**, `SessionStart` removed → **1**. Through this
> repository's judge: 0, 4, 1, 1 — the last titled `Estate hook
> inbox-notice.sh not wired for SessionStart`, which is their ADR-0068
> §4 condition, spoken.
>
> **Three things only running it said.** `details['hook']` was right on
> three specimens in four and promised a hook name while delivering a
> **file path** on an unparseable `settings.json` — `UnitFinding.enabled`'s
> trap, caught before shipping and renamed to the producer's own
> `subject`. The partition guard **was not a guard for this family**: all
> four of its tests passed before the wiring titles were added to
> `_every_title`, so `SURFACE_TITLE_PATTERNS` could have lacked `Estate
> hook %` while a row saying every hook on the box is down sat
> unresolvable in `alerts`. And **one falsification passed against
> deliberately broken code** — the `code`-is-never-read test asserted a
> true premise and a true consequence and could distinguish nothing,
> because the recorded findings carry no `code` at all; it needed a
> witness where the two signals *disagree* before the mutation died.
>
> **No roll-up, and that is measured.** The population is bounded by the
> estate's own `hooks/` directory — four scripts, one event each — and
> the collapse case is already the producer's, which short-circuits an
> unparseable file to a single finding. A threshold would be invented
> against a population that has never exceeded four.
>
> **The suite is 3017**, from 2984: **33 added and none retired**, all in
> `tests/test_estate_judgements.py`. Arithmetic against a stashed HEAD
> rather than a green suite — 90 → 123 in the file and 2984 → 3017 in the
> tree, both deltas 33, which is the only thing that can witness a
> clobber. **6 are red and none are this sitting's**:
> `tests/test_desktop_store_live.py` fails identically at `62f8e09`, the
> commit that added it, so it has never passed here — `SNAG-TRAY-010`.
> *(Fixed 2026-08-30 by Session 130, and the "never passed here" was one
> word wrong: it had never passed **at that hour**. The file was green on
> the same tree at 09:37 — the DND window, above.)*
>
> *Previously —* **A port the sweep never saw and a port it looked
> straight at were one
> answer, and the discriminator had been in the blob for four months.**
> `SNAG-ESTATE-009` was taken on its own terms and **stays open** —
> deliberately, and decided by its own check rather than by argument.
> `PortAttribution.reading()` and `details['attribution']` split the
> **four** reasons `holder` is `None`: `held`, `transient`,
> `unattributed` (the sweep looked and could not name it), `unswept`
> (the sweep ran before this listener started — this entry), `unknown`
> (no usable sweep). Live: `of(5432)` and `of(8110)` are both `None`
> and now read `unattributed` and `unswept`.
>
> **`as_blob` has emitted `unattributed_ports` since Session 26c and no
> consumer read it** — `attribution_from_blob` was written later, for a
> different consumer. This is the **sibling** of the collapse Session 57
> fixed one field over in the same function: that sitting separated a
> session scope from an unattributable socket and left an
> unattributable socket indistinguishable from a port nobody looked at.
> The entry's own "Why P3" bullet has claimed since 2026-08-17 that
> `details['holder']['observed_at']` publishes the evidence's age; the
> check's docstring calls that **vacuous**, because `holder` is `None`
> on exactly the rows that need it. It is not vacuous now.
>
> **The rung did not move, and that refusal is the new one — on
> correctness, where both standing closures were refused on cost.**
> Quietening an unattributed breach because the sweep predates it
> inverts a posture `_attribution` states in writing (*"the enrichment
> is not allowed to become a dependency of the alert"*): a failed
> `observe_listeners` returns **no** listeners, so every port would read
> unswept and the whole family would drop below
> `tray.notify_min_severity` — Session 26b-A's founding defect at full
> scale, as the fix for a seven-hour window.
>
> **Two of the entry's own measurements were wrong and the box said so.**
> The four historic `warning` rows are **not** the mid-window class the
> entry is about: `transient_ports` first reaches a stored blob at
> 2026-08-17 10:07:41, a day after them, so this entry **has never
> observed its own class**. And *"the window is six hours wide"* is the
> **p90** — 83 inter-sweep gaps in 14 days give a **median of 1.30 h**,
> because `agent_first_run_delay_seconds: 60` re-runs every added job on
> each daemon start and this daemon's median life is 1.77 h. The sweep
> runs 10–15 times a day against a nominal 4. Both errors have one root:
> costed from `config.yaml` and the code path rather than from
> `unit_audits`.
>
> **The check had to be widened before its third limb could be removed
> honestly, and the baseline is what caught it.** `annotated` compared
> detail *key sets*, so it saw a key added to the unswept row alone and
> was **blind** to the same key added to every row with a varying value
> — the shape the fix took, since a key present only sometimes is
> `ports_checked`'s collapse one level down. Measured before a line of
> the fix existed: `both rows carry the same detail keys: True`. So the
> check would have reported `match` over a landed fix, which is worse
> than flipping. Widened, it answered `mismatch`; the limb then came
> **out of the verdict** — `a-probe-keys-on-identity-not-a-mutable-field`
> for the second consecutive sitting — and the narrowed check answers
> `match`, which is the honest reading and the answer to whether the
> entry closes.
>
> **13 tests, 10 mutations, one falsification passing against broken
> code.** `test_a_sweep_predating_the_key_cannot_answer` drove a blob
> with no `ok` either, so the `ok` gate returned before the missing-key
> branch it names was ever reached — right value, wrong reason, and the
> mutation survived. Repaired with a successful-sweep-with-no-key
> specimen; re-driven, all ten land red on exactly one intended test. A
> fixture in `test_estate_judge_agent.py` also had to stop modelling a
> database this code no longer talks to: one `execute` answers both the
> open-alert and the sweep query, and its `scalar_one_or_none` returned
> a bare `MagicMock` whose `scanned_at` reached `json.dumps` the moment
> `details` began carrying the evidence's age.
>
> *Previously —* **The tray speaks about a dead backend now, and the
> grace period the
> entry called "the real work" was decided by two instruments that
> disagree about nothing.** `SNAG-TRAY-009` is **fixed**:
> `NotificationPolicy.evaluate_backend_unreachable` behind a
> **300-second** grace, fed by a new `backend_unreachable(float)` tick
> and a tri-state `_was_connected`. Both faces moved together, because
> the entry is right that a fix for one is not half the benefit.
>
> **`max(3 × status_poll_seconds, 300 s)`, and both halves are
> borrowed.** The 3 is `self_monitor.stall_grace_multiplier` — one
> missed observation is merely late — which
> `notifications.desktop.tray_grace_seconds` already applies to a tray
> poll. The 300 is `min_stall_grace_seconds`, whose stated reason in
> `config.yaml` is literally *"so a restart doesn't flag"* the fastest
> agent: this family's noise population, one domain over. **The floor is
> what does the work**, because `status_poll_seconds` is **10** in the
> tray's model and **30** in the shipped file, so the multiple alone
> spans 30–90 s while the daemon startup it must clear does not move
> with the poll interval at all.
>
> **The two populations are 1,400× apart and there is nothing between
> them.** The daemon's journal holds **104 deploy restarts of 2, 3, 12
> or 13 s** in 30 days — max **13 s**, the one 276 s window having a
> `-- Boot --` marker inside it. The tray's own journal, whose `httpx`
> line is logged only on a *successful* `/health`, holds **27**
> unreachable windows across 36,240 polls and **every one is exactly
> 60.0 s** — one missed poll. Against a nearest real fault of **18,235 s**.
> 300 s sits *below* the geometric midpoint (487 s) on purpose: firing
> early costs a toast on each of 104 deploys a month, firing late costs
> minutes of an outage that ran hours.
>
> **"Multiplicative" was understated — the two populations are
> *disjoint*.** Both real outages were **arrivals** (tray started
> 18:34:46 and 14:44:57 against an already-dead daemon), so
> `connection_lost` never fired; every window it *did* fire on was a
> 60 s deploy restart. The transition signal fired **only on noise and
> never once on a fault**.
>
> **The retired check answered `match` against the fixed code**, which is
> the part worth carrying. Its Face 1 predicate asked whether the emit
> sits inside an `if` reading `_was_connected` — **`True` before and
> after**, since the fix keeps the guard and corrects its polarity. Its
> "initialised `False`" predicate matched **two** assignments at HEAD
> (the initialiser *and* one inside `_on_disconnected`), so it was right
> for the wrong reason and went on matching the second. A shape check
> about a defect whose essence is a *value*. Retired with the entry; the
> **corrected** predicate is re-homed in
> `tests/test_tray/test_backend_unreachable.py`.
>
> **17 mutations, 34 tests, one falsification wrong on the first
> attempt.** `test_the_shipped_file_reaches_the_policy` asserted
> `load_tray_config(config.yaml) == the value in config.yaml`, and the
> shipped 300 **is** the model default — green whether or not the loader
> read the file. Deleting the key from `config.py`'s parse loop,
> `SNAG-CFG-001`'s exact shape, survived it. It drives a mutated copy
> carrying a witness value now.
>
> **Driven live, and Face 1 landed at 0.0 s.** Real `ApiClient`,
> `TrayIcon`, policy at the shipped 300 s and real `DbusNotifier` on the
> real session bus, pointed at a dead `127.0.0.1:8599` — an *arrival*.
> `connection_lost` emitted on the first failed poll, silence held
> through 29.6 / 59.6 / 89.6 s, one non-transient `critical` after the
> grace.
>
> *Previously —* **A login-time replay was worth building, and the entry
> that asked for it understated its own benefit by two orders of
> magnitude.**
> `SNAG-SYSD-005` is **fixed**: `sysadmin-replay-failures.service`, a
> user unit wanted by `graphical-session.target`, announces at login
> every unit failure still open. The entry priced the loss as the gap to
> the next login — 24 min at best, 6.1 h at worst. The `alerts` table
> prices it as the life of the row, and only **2** rows exist for all
> **5** firings (three hit the dedup branch): the one row not fixed at
> once stood open **37.73 hours**, of which the login gap is 24 minutes.
> So the replay recovers **37.3 hours of silence**, not 24 minutes of
> lateness. Reading the entry gives the population; querying the table
> gives the cost.
>
> **The room was not empty for most of it, which reranks the entry's own
> framing.** Reconstructed minute by minute: `start-limit-hit` 18:11:15,
> login 18:34:41, tray started 18:34:46 — polled 8500, got nothing, went
> to `IconState.DISCONNECTED` and stayed there. **22.2 of the 37.7
> hours** carried a live graphical session with the tray running and
> silent; only 15.5 were an empty room. "Four of five fired into an
> empty room" is true about *firings* and misleading about *silence*.
> That is **`SNAG-TRAY-009`**, opened here at P2 with its check.
>
> **The blocker the entry deferred on was not one.** It wanted an
> `--unannounced` flag at the announcer first, refusing a flag with no
> reader — right for a *history* predicate. The replay needs a *state*
> one, and `resolve_unit_failures` has exactly one production caller
> (the lifespan), `% failed` sits outside `RESOLVABLE_TITLE_PATTERNS`,
> and retention purges resolved rows only. So an unresolved
> `systemd_onfailure` row already *means* "this unit has not come back".
>
> **Waiting is permitted here and was refused in the announcer; only the
> number changed.** At login the precondition arrives in seconds —
> plasmashell active 14:44:55, target reached 14:44:57, still
> initialising 14:44:58. `WAIT_BUDGET_SECONDS` is **derived**:
> notify-send's own measured 60.08 s bound, so the replay spends exactly
> the patience one blocked call would have, on a mechanism that starts
> no `plasma_waitforname`. Driven against a private bus, a server
> claiming the name at t+2 s is caught at **3.02 s** and the
> notification arrives intact, `urgency=2`, `expire_timeout=0`. The read
> comes **before** the wait, so a clean login costs 0.34 s and no D-Bus
> call at all.
>
> **Two falsifications passed against deliberately broken code and the
> second is the one worth carrying.** Eleven mutations each landed red
> on their intended test. But the live harness's stand-in server printed
> `claimed` and owned nothing a millisecond later — a `BusName` held
> only in a local is garbage-collected on return — and the wait duly
> reported `False`: a fact about the harness reported as a fact about
> the module. The first repair was insufficient the same way, asserting
> the stand-in had *said* `claimed`. The premise now asks the **bus**
> with `busctl`, independent of both subject and harness. Session 125's
> own trap is avoided by construction: a guard mutated to refuse
> everything turns **three** live tests red and skips none.
>
> **22 open, 3 unchecked** — `SNAG-SVC-004`, `SNAG-TEST-003` and
> `SNAG-AGENT-013`. *(2026-09-02, Session 153: 4 → 3 as `SNAG-AGENT-012`
> gained the nineteenth check. `SNAG-AGENT-013` is the sibling filed
> beside it with a measured-zero population — 0 of 31 services set
> `auto_restart` — and a check for it would have to build the leaf
> nobody has set, which is a different shape of drive from this one.)*
>
> *Previously —* **19 open, 1 unchecked** — `SNAG-AGENT-011`, and the check is **owed
> rather than refused**, which is the opposite of `SNAG-TRAY-010`'s
> reason for sitting here. A discriminating witness exists and its shape
> is named in the entry; what is missing is a sitting, and the owner
> directed that it be the next one. *(2026-08-31, Session 142: 20 → 18 as
> `SNAG-SCHED-001` and `SNAG-SCHED-003` closed together — both their
> checks retired with them, a check naming a closed entry being refused
> by the sweep that already guards `CHECKS`, so the count fell on both
> sides at once — then 18 → 19 as `SNAG-AGENT-011` opened. The sweep
> reports it by name at `unknown`, never at `match`, so an unchecked
> entry is visible rather than merely uncounted.)*
>
> *Previously —* **19 open, 1 unchecked** — `SNAG-TRAY-010`, and the check is
> deliberately not owed yet. A check needs a **discriminating witness**,
> and that entry's whole content is that the mechanism is unknown: every
> "did it speak" reading is `False` while the rows are stored, and until
> `len(notifier.sent)` separates *the sweep never ran* from *it ran and
> found nothing due*, any check written now would pin the symptom rather
> than the claim and answer `match` for the wrong reason. Session 119's
> precedent for `SNAG-CFG-003` stands beside it. *(Session 130: the
> deferral was right and the reason it gave was the fix. Adding
> `sent_total` did separate the two — it read **0**, which is only
> reachable above `_handle` — and the entry closed in the same sitting,
> so **18 open, 0 unchecked** and no check was ever owed. A check
> written at the symptom would have pinned the DND window as normal.)*
>
> *Previously —* **Every open entry names a check** — 18 open, **0**
> unchecked. The
> retired `tray_silent_on_arrival` takes the count with it: a check
> outliving its entry is the other half of that pin, and this one had
> stopped discriminating anyway.
>
> Daemon restarted at **2026-09-02 17:25:00**
> <!--check:deploy--> <!--check:daemon_start-->, clean journal — **0**
> `ERROR`/`CRITICAL` lines since. Once this sitting, to deploy Session
> 155's `action_from`, which the daemon *does* import: `GET
> /api/services/actions` served the field within a second of coming
> back, `timer_failed` on `alfred-career-mail-timer` and `""` on
> `venture-chat`. *(Session 154's restart was 16:53:22, and was owed to
> the claim rather than to the code — it touched
> `sysadmin/snag_claims.py`, which the daemon does not import, and the
> check compares file mtimes and cannot know the difference.)* `/health` answered 200 within 24 s, and the two reads
> taken *inside* that window (`MainPID 0`, a `ConnectError` on
> `/health`) are the restart gap and not a fault. *(Session 153's
> restart was 13:06:58.)* *(The unresolved count read **5** at 13:06 and **3** at 13:12
> inside this one sitting — the two `Estate port 311x`/`811x` dev-server
> breaches opening and closing with an editor window, which is the
> volatility this block already records. The block was **not** corrected
> for the transient reading, which is what those bracketed warnings
> above are for.)* *Previously 2026-09-02 11:51:13, twice that sitting,
> to deploy `SNAG-SVC-003`'s step promotion and then the docstrings that
> record why it is one field wide. Previously 2026-09-02 06:46:10, twice that
> sitting too, to deploy* `SNAG-SYSD-006`'s *fold and then the review
> projection that was flattening it back. Previously 2026-09-01 21:03:19, which was owed
> for the same kind of reason as the one before it:* `sysadmin/monitor/agent.py` and
> `sysadmin/estate/client.py` are both loaded by the running daemon, so
> until the restart it was polling `venture-chat` with no idea the
> estate had stopped it. *Previously 2026-08-31 06:55:16, where the
> owed restart broke a run of three:* `sysadmin/core/gpu_lease.py` is imported by all three
> `run_weekly_review` entry points, so the running process genuinely did
> not have the code the reviews now dispatch through. The three sittings
> before it were the mtime check's known blind spot on
> `sysadmin/snag_claims.py`, which the daemon never loads — worth
> recording that the rule's false positives and its true one look
> identical from the check and are separated only by asking what imports
> the changed file.
>
> *Previously — 2026-08-30 20:59:45, and 2026-08-30 19:54:44.* The **first** restart that sitting
> was owed on the merits — `sysadmin/estate/judgements.py` is imported by
> the running application and the predicate it serves changed — and the
> estate judge ran against live 8400 a minute later, reading all four
> surfaces and raising no queue row. The second was the same blind spot
> as above.
>
> *Previously — the restart before it was* **owed by the mtime check and
> not on
> the merits**, which is worth saying plainly: that sitting's only
> backend change is `sysadmin/snag_claims.py`, a console script the
> running application never imports, so nothing the daemon serves moved.
> `check-ops-claims.sh` compares mtimes and cannot know that, and the
> restart is free (`kill -TERM`, `Restart=always`, no `sudo`), so it was
> taken rather than argued about. **The tray restart is the one that
> mattered** — `sysadmin_tray/config.py` is only live once the unit
> restarts, and it came up clean against the real `config.yaml` with
> nothing said, which is this fix shipping untriggered on the box rather
> than in a fixture. *Previously 2026-08-30 16:26:28 — owed on the merits
> and it deployed a new surface*: `sysadmin/core/config_keys.py` and the
> lifespan's key report, so `POST /api/sysadmin/reload` carries
> `unknown_keys`.
> Boot was silent, which is the correct answer and not an absence of
> wiring — the shipped `config.yaml` declares every key it sets once the
> tray's region is exempt, and a live `briefing_hourr: 9` written into
> the real file came straight back from the route.
>
> *Previously —* restarted **2026-08-30 14:29:19**, clean journal — **0**
> `ERROR`/`CRITICAL` lines since. **Owed on the merits, and it deployed
> nothing observable** — which is a third case the previous two did not
> cover. `sysadmin/core/config.py` *is* in the daemon's import graph, so
> the restart was genuinely due; what it carried was the deletion of two
> `SchedulesConfig` fields no code read, so the running process behaves
> identically either side of it. The mtime check and the merits agree
> here for once, and the behaviour still does not move. `/health`
> answered 200 within 13 s on the new pid. *(The 404 seen first was the
> prober's error, not the daemon's: this service serves `/health`, while
> the estate's monitorable-project contract asks for `/api/health` —
> a difference worth not mistaking for an outage.)*
>
> *Previously —* restarted at 2026-08-30 13:53:01, **not owed on the
> merits**: that sitting changed tests and `sysadmin/snag_claims.py`, a
> console script the daemon never imports, so the restart cleared the
> mtime comparison and deployed nothing. That is the stated cost of
> `ops_claims.py` rule 4 — the check asks the state of the box rather
> than the content of the commit, and fails in the direction that costs
> a needless `kill -TERM`.
>
> *Previously —* the restart earlier the same day was **owed on the
> merits**, and it was the deploy (its timestamp is dropped rather than
> restated: two wall clocks inside the parsed region is `ops_claims.py`
> rule 2's *"one figure stated two ways"*, and the check said so within a
> minute of this paragraph being written): `sysadmin/estate/judgements.py` and
> `sysadmin/estate/agent.py` are both in the daemon's import graph, so
> the wiring family reaches the running process only here. 11.6 s of
> downtime. **Verified live and untriggered**, which is the ports
> family's shipping position exactly: the first post-restart
> `estate_judge` run at 05:25:45 completed with `by_surface`
> `audit_findings: 0` and `unread_surfaces: {}` — zero rows because all
> four hooks are wired, not because nothing looked.
> `/health` answers
> **200** <!--check:health-->, `alembic current` reads 018 at the
> packaged head <!--check:schema-->, and `alerts` holds **3** unresolved
> rows <!--check:alerts-->, `warning: High disk usage on /`,
> `critical: alfred-career-mail-timer critical` and
> `info: Project ImbaBots next action idle`, **3**
> named here <!--check:open_titles-->. *(Re-counted 2026-09-02 by Session
> 149; the block said 5 and the checker read 3 — `SNAG-ESTATE-008`'s
> founding case, a **fall**, which is the direction that reads as
> "an action this block asks for may already be done". Both departures
> are `info` rows whose subject went away rather than fixes: the
> nightly arbitrated `venture-chat` swap resolved at its usual hour, and
> the transient dev-server port holder closed when the editor window
> did. Session 148 counted 5 the same morning, so the two families that
> produced the rise it recorded are the two that produced this fall.)* *(The critical is Session 147's,
> and it is a **rise the monitor caused rather than a fault that
> began**: the job had been failing for 20 days and only became sayable
> when `SNAG-SYSD-005` was fixed. It is Alfred's to close, not ours. Its
> twin — `pgbackrest-backup-timer critical` — was raised at 21:08,
> the unit was repaired at 22:19–22:29, and `_resolve_recovered` closed
> the row unaided at **22:33:29** on the first healthy poll. That is the
> whole family demonstrated end to end in 85 minutes on a fault that had
> stood since March, which is the strongest evidence this sitting
> produced that the fix works.)* *(Session 146 saw the same
> volatility Session 144 recorded and from the same source: the count
> read 1, then 2, then 1 again inside one sitting, the second row being
> `High VRAM usage on AMD Radeon RX 7900 XTX` — **5** rows created on
> 2026-09-01 between 16:06 and 20:31, each opening and resolving. So the
> figure to write here is the **steady** one; a sitting that re-measures
> during a GPU burst will read 2 and should not correct the block for
> it. The falling half is the one that matters and is why the check
> notes a fall at all.)* *(Re-measured **three** times on
> 2026-08-31 by Session 144, which is the finding rather than any of the
> three readings: the count went 1 → 2 → 1 inside one sitting, and
> `venture-chat unreachable` has **4** rows created today. So the row is
> flapping, and a stated figure about it is stale within minutes by
> construction — which is why this sentence now names the **stable**
> member and treats the critical as a transition rather than a state.
> `check_open_titles` is what held still throughout: the count moved
> twice while the *names* stayed answerable, which is exactly the
> finer-half argument that check was written on. Previously
> re-measured twice on 2026-08-31
> by Session 142, and the second reading is `ops_claims.py` rule 5's
> founding **fall** case happening inside one sitting: the block was
> written saying 2 while `critical: venture-chat unreachable` stood, and
> the checker reported one fewer row half an hour later because it had
> resolved on the first healthy poll — exactly as the entry filed for it
> says all 181 of its predecessors did. The row is the **third**
> consecutive sitting to be narrated here, which is the signal rather
> than the state.
> It is a true observation of an arbitrated swap: lease 42
> (`venture-nightly-24b`) stopped `venture-chat.service` at 07:26:01 and
> restored it at 07:31:01, and this row will resolve on the next healthy
> poll as its 180 predecessors did. What makes it worth a snag rather
> than a fourth paragraph is the **nightly** instance: measured over five
> consecutive nights it opens just after 00:00 and resolves at ~05:48,
> open for **5h45m to the second** — the drain's hold — at `critical`,
> the one severity the tray leaves on screen. 181 rows all-time, every
> one `critical`, every one resolved. **Filed as `SNAG-AGENT-011`**
> rather than narrated a fourth time — and the figures in that entry are
> the current regime's 20 rows, not the all-time 181, because 161 of
> those fall on 2026-08-11 → 08-14 under a mechanism the estate's queue
> replaced.
> Previously re-measured 2026-08-30 by
> Session 137: this is a **swap** — the count held at 1 while the row
> changed, which is exactly what `check_open_titles` exists for and what
> `check_alerts` alone cannot see. `venture-chat unreachable` resolved
> and the disk row opened; the disk has been the standing figure on this
> box for weeks, so this is a threshold row rather than news. Previously
> re-measured by Session 136: the row was **open again** — another
> repository's service, reported correctly, and this is the **rise**
> case rather than
> `ops_claims.py` rule 5's fall. It is named rather than counted, which
> is what `check_open_titles` exists for: a swap holds the count still
> while the sentence about *which* row is open goes wrong. Previously
> **1**, `critical: venture-chat unreachable` — another repository's
> service, reported correctly and
> since recovered. Corrected 2026-08-30 by Session 130 off
> `check-ops-claims.sh`, which is the **fall** case `ops_claims.py` rule
> 5 exists for: equality or a rise is the rule anyone would write, and a
> row resolving itself while four documents go on asking about it is the
> founding case. It was already stale at `a2f8deb` — verified by
> stashing — so it is not this sitting's, and it is fixed here because
> the check named it and a document nobody corrects is `SNAG-ESTATE-008`
> reopening.)*
>
> **Alembic head is 018**<!--check:migration_head--> — unchanged. A user
> unit and a console script move no schema.
>
> **The suite is 2971**, from 2937: **34 added and none retired**, all in
> the new `tests/test_tray/test_backend_unreachable.py`. Arithmetic
> against the baseline rather than a green suite, which cannot witness
> tests that no longer exist — 2937 collected with the new file ignored.
>
> *Previously —* **The suite was 2937**, from 2899: 38 added and none
> retired, in `tests/test_failure_replay.py` (26),
> `tests/test_failure_replay_live.py` (5) and `tests/test_systemd_units.py` (7).


> *Previously —* **A check written for one entry found the entry's own trap in its own
> hand.** `SNAG-CFG-003` is measured and holds: driven at the real
> `reload_configuration` with the daemon's injected syncer, a violating
> configuration installs with `ok=True`, `requires_restart=[]` and
> `jobs_retimed`, at a sum of 25 against a `reminder_hours` of 24. Its
> **cost** is the smaller half three times over — **2 reloads against
> 122 daemon starts** in 30 days, so the fix bullet's question about
> `reload.py` is aimed at the rarest installer; **1 of about thirty**
> suite-only coherence guards over the two shipped files; and **one of
> three leaves**, the other two being invisible to the report and
> installed by a different process. The entry is the **last of the
> nineteen to gain a check**, and every open entry now names one.
>
> Building it hit `load_config` — which is `set_config(parse_config(…))`
> and therefore **installs** — so the drive's own helper was writing the
> value its witness read back, and a mutation swapping the two changed
> nothing. The same trap was live in the guard the entry is about:
> `_reminder_ceiling` left the process holding the configuration its own
> class exists to refuse. Both now read with `parse_config`, both pinned.
>
> **`SNAG-SYSD-004` opened**: `sysadmin-failed.service` has been `failed`
> since 2026-08-23, **4 of 4** firings killed at `TimeoutStartSec=30`
> inside `notify-send`. `Linger=yes` creates the session bus at boot, so
> the script's socket guard passes with nobody logged in. Silent in the
> case it exists for.

> *Previously —* **The cost an entry states is a claim like any other, and this one was
> the smaller half twice.** `SNAG-LOG-014` prices its whole cost at *"a
> count of `alert_raised` that is 2 too high for three days"* on
> `GET /api/logs/trends`. `build_trend_report`'s own docstring says the
> advice **must** be computed off the same report the trend serves, so
> that the two surfaces cannot disagree about whether a signature is new
> — which makes an error in the grouped counts reach both by
> construction. The entry names one of them. Nothing was deleted and the
> remedy judgement stands; what moved is what the register says the cost
> is.
>
> **Driven through the real pipeline against the live table in a
> rolled-back transaction, stored against true.** `/api/logs/trends`
> moves four figures rather than one — `previous` 23→21, `total` 91→89,
> `ratio` 2.96→3.24, `sources[].previous_warnings` 28→26. And
> `GET /api/logs/actions`, which the entry never mentions, carries the
> error in a **title**: the live row reads `sysadmin.service fault up
> 3.0x — "alert_raised"` against a true `3.2x`. `SNAG-LOG-010` is the
> entry that made a title this surface's row identity, so the same
> cap-and-count family has reached the field it was written to protect.
>
> **The duration is wrong in the field the entry offers as the
> mitigation.** `previous` is windowed and does converge on 2026-08-31
> as filed. `total` is `func.count()` with **no window filter**, so it
> stays 2 high until retention — on `ingested_at`, not `logged_at` —
> puts both copies at **2026-09-16**. Eighteen days, not three, in the
> one served figure the bullet points a reader at as evidence.
>
> **What it does not reach is measured, not assumed.** The alert family
> is untouched: both copies are `warning`, `FAULT_SEVERITIES` is
> `("error", "critical")`, and `details['occurrences']` is accumulated
> from what a run read rather than queried — so no row, no fingerprint,
> no toast. The weekly review and the 06:00 briefing are clean, the
> facts section and the prompt byte-identical either side of the
> counterfactual. `/api/logs/stats` and `/api/logs/recent` cap `hours`
> at 168 against rows twelve days old.
>
> **The instrument was keyed on the column the fix rewrote, and this
> entry is the best evidence against that.** `check_duplicate_ingest_`
> `residue` grouped on `(source, logged_at, message)` — and these two
> rows were invisible for eleven days precisely because `SNAG-LOG-008`'s
> backfill had not yet made the copies agree. The **verdict** stays on
> the narrow key, because a wider one admits a microsecond coincidence
> and would hold `match` open after the pair aged out, which is the
> calendar keeping an entry alive rather than closing one. The **"is it
> happening elsewhere"** limb reaches no verdict and moves to the
> record's own identity, `(source, logged_at)`, which is the limb whose
> blindness costs something: a second occurrence needs a restart, and a
> restart is when a declaration changes.
>
> **Measured before it was preferred**: **0 of 235,230 rows across 9
> sources** have two distinct records sharing a `(source, logged_at)`,
> so the `message` component is doing no work today — and the tightest
> gap between two genuinely distinct records is **3 µs, at `kernel`**,
> not the millisecond of `alert_raised` writes the entry's fix bullet
> named as the deciding population. That bullet was 333× wide and at
> the wrong source; it now carries the number.
>
> Session 122's `Unusual CPU usage` row resolved itself by id exactly as
> that block predicted it would, which is why that sitting opened
> reading `no`. The standing deploy, health, schema, alert and suite
> figures have moved to the current block above — stated once, because a
> block giving one figure two ways reads as `unknown`, which is
> `ops_claims` rule 2 and `SNAG-ESTATE-008`'s whole shape.


## Quick Status

| Area | Status | Notes |
|------|--------|-------|
| Backend | 🟢 Complete | FastAPI + 5 agents + scheduler + DB |
| API | 🟢 Complete | <!--check:routes-->**51 routes** *(re-counted live 2026-08-25 after Session 79 added `GET /api/sysadmin/review` and `POST /api/sysadmin/review/generate`: 49 → 51. Session 78 took 48 → 49 with `GET /api/services/actions`. Previously 46 → 48 on 2026-08-24 after Session 75, the two `410 Gone` tombstones for `/api/logs/summary` and `/summary/history`. They are `include_in_schema=False`, so `/docs` lists 46 — `measure_routes()` counts `APIRoute` objects rather than schema entries, which is the honest figure and the one that moves when a route is declared)* across 8 routers plus 2 defined in `create_app` (`scan-all` and `reload`, which need `app.state`); bearer-token auth on mutating endpoints (GETs open). *Counted live 2026-08-17 off `create_app()`; 44 before Session 27 added `GET /api/logs/trends` and `GET /api/logs/actions`* |
| Database | 🟢 Complete | <!--check:tables-->**13 tables** in sysadmin schema (14 counting `alembic_version`; re-counted live 2026-08-28), Alembic migrations (head **018**<!--check:migration_head-->, applied 2026-08-28 — `desktop_notifications`, the understudy's spoken set made durable so a 24-hour reminder is reachable by a daemon whose median life is 1.77 h, with its `retention_config` row in the same migration; see `SNAG-TRAY-008`. *017 on 2026-08-27*, applied 2026-08-27 — `idx_alerts_open_by_agent`, the partial index that bounds an agent's open-alert read by its *own* rows rather than by the whole open set; measured worthless on its own and decisive beside `unresolved()`, see `SNAG-AGENT-007`. *016 on 2026-08-25*, applied 2026-08-25 — `health_reviews`, the weekly system health review's own table, with its `retention_config` row in the same migration because the two halves fail in opposite directions. *015 the same day added `reliability_scores.skipped_checks`.*) *014 on 2026-08-24 dropped the three frozen tables.* *Was 14. `project_snapshots`, `project_reviews` and `log_summaries` had no writer since ADR-0005 or Session 69 and are gone with their retention rows, their `TABLE_TIMESTAMP_MAP` entries and the `LogSummary` model. `FROZEN_TABLES` is now empty and deliberately kept — an entry there is a blindfold over the drift guard, so emptying it is what proves the drop rather than a new test* |
| Agents | 🟢 Complete | SysAdmin, File Organiser, Log Aggregator, Service Discovery, **Estate Judge** (2026-08-13). Project Organiser left for the estate's 8400 service on 2026-08-13 and stays in `AGENT_NAMES` only because the constraint is add-only |
| GPU Monitoring | 🟢 Complete | AMD via rocm-smi + sysfs fallback, temp/VRAM alerts |
| Observability | 🟢 Complete | Structured JSON logging + request access logs. *`SNAG-LOG-004` found and fixed 2026-08-17: `read_journal` passed no `-a`, so every record over ~4096 bytes returned `MESSAGE: null` and the aggregator crashed on it — armed by the priority fix below, 0 errors and 146 clean runs away from a permanent blackout. `SNAG-LOG-003` closed the same sitting: `services.yaml` now carries a per-source `format: json` declaration and titles read `Log error: sysadmin-service — scheduler_job_error` rather than 252 characters of JSON.* *`SNAG-AGENT-008` closed 2026-08-17: uvicorn's duplicate access logger silenced (volume half), and every JSON line now carries a `<N>` syslog level prefix with `uvicorn.error` rerouted through the same formatter (priority half). **Live since the 14:10:58 restart** — verified, `log_entries` holds 10 `warning` rows for `sysadmin.service` where it held 0 across nine nights* *`SNAG-LOG-005` fixed 2026-08-17: making the daemon visible to itself gave one fault two speakers, so `COVERED_SIGNATURES` quietens `(sysadmin.service, agent_run_failed)` to `info` with `details['covered_by']` naming `failures.py`, which owns agent-run health and waits for two consecutive failures. Keyed on the producers' own constants; measured at 249 error incidents, of which 34 have no owning family and stay loud.* |
| KDE Tray App | 🟢 Phase 3 Complete | Tray icon + service grid + D-Bus notifications + native dashboard + DND mode + service actions (popup retired 2026-07-24) |
| PA Integration | ⚪ Dormant | Code + tests intact, `personal_assistant.enabled: false` — PA retired 2026-07-24, Alfred has no inbox to POST to |
| Testing | 🟢 **3318 green** | **3318 backend + tray** *(3297 + 21 on 2026-09-02, Session 153: all 21 in `tests/test_snag_claims.py::TestTheStaleRungCheck`, **none retired** — the nineteenth check, for `SNAG-AGENT-012`. **Fourteen mutations driven and fourteen killed, each on its intended test — but one passed against every test in the class before the premise was repaired**: a drive aimed at `_refresh_open`, one level below the fork where the fix may land, which supplies its own `raised = 0` because the author put the standing row there. `_suppressed` is the witness that separates the two entry points, and `_refreshed` had to come **out** of that premise — it lives inside `_refresh_open`, so `step_for`'s shape leaves it at zero with the hold plainly fired and the check reported `unknown` over a landed fix, which only the fix-modelling stand-in could have said. Two further weak tests were repaired before mutation: an assertion that existed only to name the check key, and a before/after count of trigger rows that is **constant here whatever the drive does**, since a test process cannot reach `log_entries` under `sysadmin.service` at all — replaced by the observable mechanism, whether the record reaches a root handler. **One pre-existing red was repaired and it is not counted as an addition**: `tests/test_quietened_judgement_live.py` asserted the run's **box-wide** resolve count where it meant its own two titles, so it was red exactly while an editor held 3110/8110 — verified pre-existing by stashing to HEAD before blaming this sitting, and the scoped form still turns red under a modelled resolve-and-re-raise. **The baseline was measured by stashing to HEAD and re-collecting**: 3298 collected, which reconciles with this cell's 3297 passed + 1 skipped, so the row was right for the second sitting running. 3318 passed + 1 skipped = 3319 collected. Previously 3297 backend + tray (3285 + 12 on 2026-09-02, Session 152: all 12 in the new `tests/test_live_drive_scoping.py`, **none retired** — the guard that outlives `SNAG-TEST-004`, refusing a box-wide process selector in any `tests/test_*_live.py` drive. **Seven mutations driven and seven killed**, each on its intended test, the first two being the two real pre-fix calls put back into `test_notify_guard_live.py`. Two things only running it could have said: the detector **reports its own file**, not from its stand-in sources — those are strings, and a string is prose — but from its *expected values*, since `== ["pkill"]` and an argv list are spelled identically, which is the mirror of the prose problem arriving inside the fix for it; and the pre-fix specimen's assertion was written in the wrong order, because the walk sorts by line and the `pkill` is at 138 while both `pgrep`s are at 372 and 383. **The baseline was measured by stashing to HEAD and re-collecting**: 3286 collected against this cell's 3285, which reconciles — 3285 passed + 1 skipped — so for once the row was right and the arithmetic says so rather than being trusted. 3297 passed + 1 skipped = 3298 collected. Previously 3285 backend + tray (3276 + 9 on 2026-09-02, Session 151: 8 in `tests/test_service_recommendations.py::TestTheStepCanBeSuperseded` and 1 in `tests/test_health_review.py`, none retired — one of the nine **written twice**, because the first version drove a lone `timer_failed` row and asserted it kept its own step, which no implementation can get wrong: `recommend` never calls `_folded_row` on a group of one. The discriminating form declares `outage` superseding and reads the **detail**, since `action` comes out identical either way. **Nine mutations driven and nine killed**, each on the intended test — and two of them exist only because a first pass left two tests unreached: the subject-keyed implementation the entry's own wording points at, killed solely by `pgbackrest-backup-timer`, and a `RATE_ARGUED` kind declared superseding, which is a rule with no path to it. **The baseline was measured by stashing to HEAD and re-collecting**: 3276 + 1 skipped, against **3249 in this cell** — 27 tests of Sessions 147–149 that never reached it, `SNAG-ESTATE-008`'s shape in this table's own cell again, and the reason the arithmetic is carried rather than the total alone. Previously 3249 backend + tray (3264 − 19 + 4 on 2026-09-01, Session 146: 4 added in `tests/test_arbitrated_stops_live.py::TestTheDeployedQuieteningLive`, **19 retired** — `TestTheNightlyHoldCheck`, whose check retired with `SNAG-AGENT-011`. The guard did not retire with them and is **stronger than what it replaces in a named axis**: limb 1 rebuilt its window from `venture-enrich-nightly.timer`, keying this repository's guard on another project's schedule — which moved 02:00 → 00:00 on 2026-08-25 — while the re-homed tests read `details['arbitration']`, the blob the fix writes, and hold at any hour. **Five stand-ins driven and each reddens exactly its own test**: an arbitrated stop left `critical`, an `unread` row quietened, an unclassifiable reading, the fix as deployed (reddening none) — and the pre-fix world, which reddens **only the anti-vacuity pin** while the two behavioural tests *skip*, so without that pin a box that never deployed the fix reads green. One test is skipped by design and says so: the over-quietening direction has an empty population on a healthy box, and asserting the *absence* of a quietening is the direction a fix of this shape fails in. Arithmetic checked against the measured baseline rather than the cell: 3264 − 19 + 4 = 3249 = 3248 passed + 1 skipped. Previously 3230 + 34 on 2026-08-31, Session 145: 25 in the new `tests/test_arbitrated_stops.py`, 7 in the new `tests/test_arbitrated_stops_live.py` and 2 in `tests/test_import_boundary.py`; **none retired**, and one existing test **inverted rather than deleted** — `TestTheNightlyHoldCheck`'s live drive, which asserted `match` and now asserts `mismatch` **plus the reason**, because `SNAG-AGENT-011`'s check refutes on the commit by its own design and a test still demanding `match` pins the defect as the contract. **Fourteen mutations driven and fourteen killed**, each on the intended tests, plus two against the live half — and the pair that matters is `ARBITRATED_STOP_SEVERITY`: swapping it for the judge's constant (right value, wrong provenance) reddens only the import guard, and setting it to `warning` (wrong value) reddens only the pin, which is the value-versus-provenance split this file has recorded three sittings failing to make. **One restore was masked by the bytecode cache** — `stopped_units` → `units_stopped` is a *same-length* rename, so a repaired tree went on failing until `__pycache__` was cleared; the kills are unaffected, since a stale cache can hide a restore and never manufacture a red. The baseline was **3230 and this row was right**, the second time in six sittings. Previously 3230 backend + tray (3228 + 2 on 2026-08-31, Session 144: both in `tests/test_services_registry.py` — the widened declaration set and the live witness that a declared source really writes JSON — plus one existing premise in `tests/test_message_backfill_live.py` **relaxed rather than deleted**, because it stated the anti-vacuity premise and the dying only-one-source fact in one assertion. Three falsifications driven, each red on its own test: removing the new name, declaring `format: json` on the `print()`-based `estate-broker-provision` (red at 13 records read, 0 JSON-shaped), and undeclaring the probe unit. **The row this replaces read 3209 and the tree collected 3228 at `263c160`** — measured by running before a line was edited, so the 19-test gap is earlier sittings' additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell again, and the reason the arithmetic is carried rather than the total alone. Previously 3209 backend + tray (3196 + 13 on 2026-08-31, Session 142's follow-on: all 13 in the new `tests/test_handoff_shape.py`, none retired. Twelve guard `HANDOFF.md`'s two shape rules against estate-manager's `roadmap.py` — asserted as properties of **this document** rather than as a copy of their parser's logic — and the thirteenth sweeps `scripts/*.sh` for the execute bit, written after `30bfbea` shipped `claude-preflight.sh` at mode 0644 and a **mode is not content**, so the suite, ruff and the pre-commit hook were all green over the one script every sitting starts with. Four falsifications driven, each red on the intended test. Previously 3196 backend + tray (3180 + 48 − 32 on 2026-08-31, Session 142: 33 in the new `tests/test_gpu_lease.py`, 6 in the new `tests/test_gpu_lease_live.py` and 9 in `tests/test_gpu_gate_invocations.py`; **32 retired** — `TestTheReviewSlotCollisionCheck` and `TestTheReviewChainDrainCheck`, whose two checks retired with `SNAG-SCHED-001` and `SNAG-SCHED-003`. The guard did not retire with them and is **stronger than what it replaces**: those checks swept `sysadmin/` for any mention of an arbitrating name — weak enough that a docstring nearly satisfied one — while `TestTheWaiterlessInvocationTakesALease` asks, per review module, that the job acquires a lease, passes `gpu_lease_held`, and releases from a `finally`. The middle assertion is the load-bearing one: a job that took a lease and let the flag default to `False` would wait for the card and *then* give up on it, which is strictly worse than not waiting and green in every behavioural test, because both paths store a review. **Thirteen mutations driven and thirteen killed**, each on the intended tests and none passing against broken code — but one new test is a **recorded counterfactual rather than a guard and says so**, the copied-1800 arithmetic being over two constants that no code change can break. The baseline was measured by stashing to HEAD and re-collecting rather than read off this cell: 3180, which is what this row said, the first time in five sittings it has been right. Previously 3180 backend + tray (3160 + 20 on 2026-08-30, Session 140: six in `tests/test_snag_claims.py::TestTheReviewSlotCollisionCheck` for `SNAG-SCHED-002` and fourteen in the new `TestTheReviewChainDrainCheck` for `SNAG-SCHED-003`, none retired. Eleven mutations driven, each red on exactly the intended tests — and **one passed against deliberately broken code**: replacing the majority rule with unanimity survived, because the specimen for *"one slot inside is enough"* had that slot at **6 of 6**, a reading a majority rule and a unanimity rule agree about, so it witnessed neither; it is **4 of 6** now with a boundary test at exactly half. A second guard had to be strengthened before it was driven — the threshold pin compared the detail against `get_config()`, which passes just as well over a hard-coded `25` while the shipped threshold happens to be 25, so it **moves** the threshold and requires the reading to move with it: a value asserted where provenance was meant, for the third time in this file. **The row this replaces read 3107 and the tree collected 3160 at HEAD** — measured by stashing before a line was edited, so the 53-test gap is four sittings of additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell for the **third** time, and the reason the arithmetic is carried rather than the total alone. Previously 3107 backend + tray (3079 + 33 − 5 on 2026-08-30, Session 136: 26 in the new `tests/test_config_keys.py`, 4 in `tests/test_reload.py` and 5 in `tests/test_snag_claims.py::TestTheTraySectionCheck`; **five retired** — `TestTheConfigExtrasCheck`, whose check retired with `SNAG-CFG-004`. Twelve mutations driven, each red on the tests about its own rule, and **two passed against deliberately broken code first**: the subtree-exemption mutation changed nothing because `notifications.tray` is not itself in `FOREIGN_KEYS`, so the faithful version had to replace the constant *and* the matcher; and adding `ConfigDict(extra="forbid")` to a config model gave a **collection error** rather than a red test, because that name is not imported in that module — a stand-in that cannot compile is silence wearing a result. Baseline taken by running, not by reading. Previously 3079 backend + tray (3070 + 10 − 1 on 2026-08-30, Session 135: five in `tests/test_config_defaults.py::TestTheVacatedReviewLeavesStayGone` and five in `tests/test_snag_claims.py::TestTheConfigExtrasCheck`; **one retired** — `test_review_schedule_holds_and_is_refuted_by_a_reader`, which drove the check that retired with `SNAG-CFG-002`. Nine mutations driven, each red on exactly one intended test. **The row this replaces read 3018 and the tree collected 3070 at HEAD** — measured before a line was edited, so the 52-test gap is four sessions of additions that never reached this cell: `SNAG-ESTATE-008`'s shape in this table's own cell for the second time, which is why the arithmetic is carried and not the total alone. The gap is *why* the baseline is taken by running rather than by reading — had 3018 been trusted, `baseline + added == total` would have reported a clobber that did not happen. Previously 3018 backend + tray (3017 + 1 on 2026-08-30, Session 130: one leak guard in `tests/test_desktop_store_live.py`, none retired — counted by stashing to HEAD and re-collecting, 3017 → 3018. **The six reds are gone and no code changed to remove them**: `SNAG-TRAY-010` was the drive leaving `dnd_manager` reading the real wall clock, so the file was red inside the shipped `23:00 → 07:00` window and green outside it — Session 129 ran at 05:27. Three mutations driven, each red on exactly one intended guard, and the third found the drive **erroring** rather than failing at a different gate, which takes the premise test down before it can name the cause. Previously 3017 backend + tray (2984 + 33 on 2026-08-30, Session 129: all 33 in `tests/test_estate_judgements.py` for the `wiring` family, none retired. Counted by stashing to HEAD and re-collecting — 2984 → 3017 in the tree and 90 → 123 in the file, both deltas 33, which is the only arithmetic that can witness a clobber. **Twelve mutations driven and twelve killed, one of them only after the test was strengthened**: the `code`-is-never-read test asserted a true premise and a true consequence and could distinguish nothing, because the recorded findings carry no `code` at all, so a code-reading judge agrees with a detail-reading one by accident — a constant observation is not evidence unless something in the population would have forced a different one. **Six are red and none of them are this sitting's**: `tests/test_desktop_store_live.py`'s adoption drive fails at HEAD too, verified by stashing, with its own premise test passing and no leaked probe rows in `alerts` or `desktop_notifications` — filed as `SNAG-TRAY-010` rather than fixed here. Previously 2984 backend + tray (2971 + 13 on 2026-08-29, Session 128: 5 in `tests/test_unit_ports.py`, 5 in `tests/test_estate_judgements.py` and 3 in `tests/test_snag_claims.py`, none retired — one existing test **inverted** rather than deleted, because it pinned the check limb this sitting removed. Ten mutations driven, each red on exactly one intended test, and **one falsification passed against deliberately broken code**: the missing-key test drove a blob carrying no `ok` either, so the `ok` gate returned before the branch it names was reached and the mutation survived; it asserts the right value for the wrong reason until a successful-sweep-with-no-key specimen isolates it. **The row this replaces read 2937 and the tree collected 2971** — measured by stashing to HEAD and re-collecting rather than trusting the green, since `baseline + added == total` is the only arithmetic that can witness a clobber; the 34-row gap is `SNAG-ESTATE-008`'s shape in this table's own cell, so the figure here is now the measured one. Previously 2937 backend + tray (2899 + 38 on 2026-08-29, Session 126: 26 in `tests/test_failure_replay.py`, 5 in the new `tests/test_failure_replay_live.py` and 7 unit-file guards in `tests/test_systemd_units.py`, none retired. Eleven mutations driven, each red on exactly one intended test — and **one falsification passed against deliberately broken code, in the harness rather than the subject**: the stand-in notification server printed `claimed` and owned nothing a millisecond later, because a `dbus.service.BusName` held only in a local is garbage-collected on return, so the wait reported `False` after a full budget and that read as a verdict about the module. The first repair was insufficient the same way — it asserted the stand-in had *said* `claimed`, which the mutation satisfies. The premise asks the **bus** with `busctl` now, independent of both the subject and the harness, and the mutation fails naming the harness. Session 125's trap was avoided by construction: a guard mutated to refuse everything turns three live tests red and skips none. The count was verified by arithmetic against the baseline rather than by the suite being green. Previously 2886 + 13 on 2026-08-29, Session 125: six static guards in `tests/test_systemd_units.py` and seven live ones in the new `tests/test_notify_guard_live.py`, none retired. Eight mutations driven, each red on exactly one intended test — and **one passed against deliberately broken code**: a guard mutated to refuse everything left `test_it_admits_the_live_bus` *skipping* rather than failing, because its own skip predicate asked the guard under test whether a live notification server existed. A control a broken subject can switch off is not a control; it asks `busctl` directly now, and re-driven the mutation turns it red. The count was verified by arithmetic against a stashed HEAD rather than by the suite being green. Previously 2872 + 14 on 2026-08-29, Session 124: `TestTheReloadCoherenceCheck`'s thirteen members in `tests/test_snag_claims.py` and the specimen-does-not-install pin in `tests/test_config_defaults.py`, none retired. Nine mutations driven, each red on exactly one intended test — and **one passed against deliberately broken code**: reading the installed-witness back from the specimen instead of the singleton is the same number whenever the reload installs, and the surviving mutation named the missing case, a reload that reports success and installs nothing. Four of the stand-ins had to be rewritten to call through to the real drive first, because a stand-in that reports a verdict without installing the configuration models no fix at all. Previously 2869 + 3 on 2026-08-29, Session 123: `TestTheDuplicateIngestCheck`'s three new members in `tests/test_snag_claims.py` — the verdict keyed on the entry's narrow key, a divergently-parsed duplicate named rather than silent, and the record identity asserted at the statement because today both keys agree over 235,230 rows. None retired; the four existing members were re-driven at a fourth `query_one` call. Four mutations, each red on one intended test, and one of them passed against broken code first time — the equal-count case was uncovered. Previously 2863 + 6 on 2026-08-29, Session 122: `TestACutTitleStaysAnIdentity` in `tests/test_log_alert_dedup.py` and the estate parser's new raise shape in `tests/test_snag_claims.py`, none retired — one falsified against the pre-fix title and four against mutations of the fix, because a test that passes against the broken code is a control over the fix's failure modes rather than over the defect's. Previously 2844 + 19 on 2026-08-29, Session 120: the derived movement line and the closure-aware banner reader in `tests/test_snag_claims.py`, none retired — nine mutations driven, each red on the intended test. Previously 2838 + 6 on 2026-08-28, Session 119: the reminder-ceiling guard in `tests/test_config_defaults.py`, none retired. **This row was a session stale when that was written** — it read 2832 while Session 117's block read 2838, so the row and the block disagreed about the same figure in one file, which is `SNAG-ESTATE-008`'s shape and the reason the arithmetic is carried rather than the total alone. Previously: 2801 + 53 − 22 on 2026-08-28 for `SNAG-LOG-008`, then 2832 + 26 − 20 for Session 117's `SNAG-ESTATE-010`.))))))))))* 
| CI | 🟢 Complete | GitHub Actions: ruff + mypy-clean codebase + full pytest (headless Qt) |
| LLM | 🟢 Complete | llama.cpp (llama-server :8081, OpenAI-compatible API) — migrated from Ollama 2026-07-24 |
| Frontend | 🔴 Retired | Web UI died with PA (2026-07-24). The PyQt6 tray dashboard is now the only UI — see ideas.md for rebuilding it in Alfred's Nuxt frontend |

---

## Recently Completed

### Session 156 — the red said the hazard was gone whatever had happened (2026-09-02)

**`SNAG-TEST-003` is closed by the wording changing, which is the only way
it could close.** Its claim was never about a mechanism — both candidate
causes were refuted while it stood — but about a sentence: the blocking
probe's assertion read *"the D-Bus activation that causes SNAG-SYSD-004 is
gone from this box and the guard's urgency should be re-derived"*, so
**any** red reported good news and the honest response to good news is to
relax the control.

**The fix is the precondition the entry named, and the three states were
driven before it was written.** A bus with no service directory gives
`activated=False` and `ServiceUnknown` in **0.03 s**; three scoped kills
landing inside the window give `activated=True` and
`exited with status 255` at **3.06 s**; the control blocks the full
**8.03 s**. Each falsification lands on its own assertion with its own
message. The activation had to be sampled **during** the call — the
disturbed row's waiter is dead by the time the call returns — so
`subprocess.run(timeout=…)` was replaced by a polled `Popen`, the 20 ms
interval derived from a measured 48–50 ms activation latency.

**One argv is kept for both halves and `stderr` decides nothing.**
`watch_pid` is a parameter rather than a sibling function, because the
module's evidence rests on the two observations differing in exactly one
thing; the two failing shapes do carry distinct messages and both are
quoted into the failure, but keying on them would restate a judgement
`activated` already makes. `TestTheRedSaysWhichReadingItIs` is the
durable half — an `ast` pin on the assertion order, killed by both a swap
and a deletion — and it reads each assert's `test` and never its `msg`,
which is `test_live_drive_scoping.py`'s prose problem one node deeper.

**The register's every-open-entry-names-a-check property is restored**:
20 open, **0** without a check. All 22 existing checks were driven before
and after and none moved. Suite **3349 passed, 1 skipped**; the changed
file went 7 → 8 tests.

### Session 152 — the fix had been in the tree for two days and the pin it claimed had never existed (2026-09-02)

**`SNAG-TEST-004` is closed, and the sitting's first job was working out
which half was outstanding.** The code fix landed at `2502dbc` on
2026-08-31, touched no document, and left the entry reading open. Measured
before anything was decided: `tests/test_notify_guard_live.py` is **7
passed in 8.68 s** and **zero** waiters remain on the box after running it
or its sibling — counted by `comm`, because the obvious `pgrep -f` matched
its own diagnostic shell on the first attempt, which is this entry's own
defect class reproduced live.

**What was genuinely outstanding is a control that was claimed and never
built.** The entry said the taker count *"is now pinned by an `ast` walk"*
and the shipped module docstring said *"pinned by an AST walk"*; nothing
in the repository has ever walked that file. It is left **unbuilt** rather
than written, because the number stopped deciding anything the moment the
kills were scoped — four unscoped kills against a threshold of three was
the whole argument, and four *scoped* kills reach four processes the
fixture started, as would forty. Both sentences are corrected instead.

**`tests/test_live_drive_scoping.py` is what replaced it, and it is wider
than the entry on purpose.** It refuses a box-wide process selector
(`pkill`, `pgrep`, `killall`, `pidof`) in **any** `tests/test_*_live.py`
drive, because the hazard belongs to starting a private resource and then
selecting by a pattern the box shares — `FROZEN_TABLES`' rule, and the
failure mode is the silent one: a reintroduced global `pkill` leaves the
file green in isolation and turns a **peer's** run red.

**A text sweep is the inverse of that walk rather than a coarser version,
and the measurement decided the shape.** At `ec54ab8` — the revision
carrying all three unscoped calls — the module docstring names neither
`pkill` nor `pgrep`; at `2502dbc` it names both, because the fix explains
itself. So a grep reports the file that is right and passes the file that
is wrong. The walk reads argv and the `shell=True` string given to a
runner and nothing else, so prose falls out by construction. **The
selector is judged, never the read**: `_waiters_under` still lists every
process on the box and is correct, because it selects by ppid chain
afterwards.

**The population was re-measured rather than inherited.** Seven live
drives, **two** of which start a `dbus-daemon`;
`test_failure_replay_live.py` never had the defect — it kills only the
daemon and triggers no activation — verified by running it at 5 passed and
zero waiters. **Seven mutations driven and seven killed**, each on its
intended test, the first two being the two real pre-fix calls put back.
The pre-fix specimen comes out of git rather than being reconstructed and
**skips** where history cannot reach the object, since a detector nobody
could drive is not one that saw nothing.

**It does not close `SNAG-TEST-003`**, whose claim is about the
assertion's wording. What changed is that its one *measured* cause is
gone, so its evidence is hypothetical again rather than demonstrated.

### Session 151 — the leading step named a remedy that cannot work, and the fix is one field wide (2026-09-02)

**`SNAG-SVC-003` is closed.** `_folded_row` took `action` from the
anchor, and the anchor is `KIND_ORDER`'s first surviving kind, so
`alfred-career-mail-timer` led with *"POST
/api/sysadmin/services/alfred-career-mail-timer/restart is the
deliberate manual step"* while the step that reaches the failing job —
`journalctl --user -u alfred-career-mail.service -n 100` — sat three
lines down in the row it had swallowed. Sharper than a weaker step: the
leading one names a remedy that **cannot work**, because restarting a
timer whose triggered service is failing re-arms a schedule that was
never the problem, which the swallowed row's own detail says in as many
words.

`STEP_SUPERSEDES` is the answer and it is one tuple wide. A kind
belongs to it when its step reaches a unit the anchor's step cannot;
`timer_failed`'s names the **triggered** service, one unit deeper than
the row's own subject, so no service-level step can reach it. The shape
was put to the owner against a full `STEP_ORDER` and against deriving
it from a new field on `ServiceRecommendationInfo`, and the declared set
was chosen.

**Rule 4's refusal stands.** Cause-first anchoring was refused in
Session 149 for want of a declared cause-to-consequence pairing, and
nothing here reverses it: the title, the points, the rung, the grade and
the evidence are all still the anchor's, and a test drives them field by
field because the whole objection was that anchoring would take them
along. Live either side of the deploy, `alfred-career-mail-timer` leads
with the `journalctl` step, `venture-chat` is unmoved, and the endpoint
holds **6 rows and 83 points** both before and after.

**The entry's discriminator was one it did not name, and the live table
supplied it.** It scopes the defect to "a timer fault", which points at
repairing `_outage_row` whenever the subject is a timer. Two timers
carried an `outage` row on 2026-09-02: `alfred-career-mail-timer`,
folded, and `pgbackrest-backup-timer`, whose job had started succeeding
the day before and which therefore produced no `timer_failed` row at
all. Both were handed the identical restart step and **only the folded
one's was wrong** — for an armed timer whose *unit* went inactive the
restart is the right step. The condition that refutes the step is
exactly the condition that folds, which is what makes the rule local to
`_folded_row`; the subject-keyed implementation is a driven mutation and
`pgbackrest-backup-timer` is the only thing in the population that lands
it red.

**The promotion would have dropped the anchor's step**, which is
`_folded_row` rule 4 facing the other way. That rule says a consumer
rendering one field must not lose a finding — the tray and
`health_review` read `title`, `detail` and `action`, and `members` is
none of the three — so the moment the anchor's step stops leading it is
a remedy no rendered field carries. Rule 5 names it in the `detail`,
with the finding the leading step belongs to.

**The consumer half needed its own drive, one entry after it needed one
last time.** `health_review._service_facts` projects `action`, so the
promoted step reaches the weekly review; the existing projection test
drives `venture-chat`'s shape, which **cannot discriminate**, because
that fold has no superseding member and its projected action is the
anchor's either way. Verified live in the digest: *"Look at first:
alfred-career-mail-timer: 91.24% uptime this window — journalctl --user
-u alfred-career-mail.service -n 100 …"*.

**The step was run.** It returns a SQLAlchemy insert error at 08:20:25
followed by `Failed with result 'exit-code'` — Alfred's fault to fix and
already its SNAG-50. What is verified here is that the leading step now
reaches it.

**One of the nine tests was written twice and the first could not have
failed.** It drove a lone `timer_failed` row and asserted it kept its
own step — true of every implementation, because `recommend` never calls
`_folded_row` on a group of one. The discriminating form declares
`outage` superseding and folds `outage` + `flapping`: scanning `group`
finds the anchor and scanning `others` does not, and the two agree about
`action`, so the **detail** is the only place the difference shows.
Nine mutations driven, each red on the right test; **19 snag checks
unmoved** by stash, which matters because this module carries two other
entries' instruments.

**Residue**: `SNAG-SVC-004` — the provenance line lives in `detail`, and
`_service_facts` projects every other field. It reads correctly today by
luck of one string, `_timer_failed_row`'s action ending *"the failure is
in the service the timer starts, not in the timer"*.

### Session 146 — the first night under the fix, read off the table rather than off the verdict (2026-09-01)

**`SNAG-AGENT-011` is closed**, on limb 1 and by the branch that
distinguishes a quietening from a suppression. The nightly
`venture-chat unreachable` row opened **2026-09-01 00:01:16** at `info`,
resolved at **05:51:19** — the drain's hold — and carries
`details['arbitration']` = `{unit: venture-chat.service, profile:
venture-nightly-24b, reading: granted, lease_id: 48, stopped_by_estate:
true}`. With `tray.notify_min_severity` at `warning`, the persistent
nightly toast the entry was filed for no longer reaches a screen, while
the row still exists, still resolves and still reaches
`GET /api/services/reliability`.

**The deploy question was answered before the data question.** The
commit landed at 09:44:50 and the daemon started at **09:36:14** — 8m36s
*earlier* — because this repository restarts to verify and commits
afterwards, which is precisely why `ops_claims` rule 4 compares file
mtimes rather than commit times. `check-ops-claims.sh` confirmed the
daemon was serving the code on disk, so the night was a night under the
fix.

**The check could not close its own entry, and that is the design.**
`sysadmin-check-snags` reports `mismatch` with limb 2's reason — a reader
of `stopped_units` exists — because `if readers:` returns before any
limb-1 branch runs: a short-circuit gate hiding what is behind it. Limb
1 was read by neutralising the outer gate with a stand-in, confirmed to
move the output before its verdict was believed, and it refutes by the
third of three branches: *"the nightly row is still raised and is no
longer critical — a quietening rather than a suppression"*.

**The three alternative readings were separated by hand, because the
check says it cannot separate them.** A quiet population would equally
be produced by `mute_services` gaining the service, by the estate
retiring the swap, or by the profile losing `stopped_units`. Live:
`mute_services` is `[]`; the three post-deploy rows each name a real
granted lease; `stopped_by_estate` is `true` on all of them. The
population did not go quiet — only the rung moved, which is the single
outcome that closes the entry.

**The check retired and the detector did not**, the sixth time this
repository has spent that rule. `TestTheDeployedQuieteningLive` in
`tests/test_arbitrated_stops_live.py` reads the live `alerts` table, and
is stronger than the limb it replaces in the axis that matters: limb 1
rebuilt its window from `venture-enrich-nightly.timer`, keying this
repository's guard on another project's schedule — which moved 02:00 →
00:00 on 2026-08-25 — whereas these read `details['arbitration']`, the
thing the fix writes, and would witness the estate swapping a unit
nobody has thought of yet. A live read is needed at all because a
recorded test cannot tell a fix that works from one that has never
executed; `_still_open` carried exactly that shape for sixty sessions.

**Its anti-vacuity pin is the load-bearing half.** Driven at five
stand-ins: a pre-fix world reddens **only** the pin, while the two
behavioural tests *skip* — so without it a box that never deployed the
fix reads green, which is `a-check-needs-a-discriminating-witness`
arriving inside the guard written for it. The other four cases redden
exactly one test each and nothing else, including the over-quietening
direction, where the *absence* of a quietening on an `unread` row is
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

**Nothing was built off the closure.** `SNAG-AGENT-012` and
`SNAG-AGENT-013` were filed by Session 145 with measured-zero
populations precisely so that a later sitting would not, and the handoff
said so by name. Test arithmetic balances — 3264 − 19 removed + 4 added
= 3249 = 3248 passed + 1 skipped — so no file was clobbered.

### Session 145 — the arbitrated stop is quietened, and the placement question was three questions (2026-08-31)

**`SNAG-AGENT-011`'s decided fix is built and deployed, and the entry is
deliberately still open.** `venture-chat.service` is stopped nightly by
estate-manager's arbiter under a GPU lease; this box answered by putting
a **persistent** critical toast on screen for most of every night — 6
nightly rows at a mean of 346 minutes open — about a service that is down
on purpose. `sysadmin/estate/client.py` gains `read_arbitrated_stops`,
which takes the two-call path the entry decided (`active_lease.id` from
`GET :8400/api/queue/invariants`, then `stopped_units` from
`GET :8400/api/queue/leases/{id}`), and `SysAdminAgent._handle_status`
quietens a unit the estate names to `ARBITRATED_STOP_SEVERITY`.

**The entry stays open by its own instruction, which is the part a later
reader needs.** Its check is a conjunction whose halves refute at
different moments: limb 2 is a source walk and has flipped on this
commit; limb 1 reads the nightly population off `alerts` and cannot flip
until a night has passed under the deployed code. So the confirmation for
**2026-09-01** is carried as a *Scheduled action* in `HANDOFF.md`, and
the check's live test was **inverted rather than deleted** — it asserts
`mismatch` *and* that the refutation came from limb 2, because a
`mismatch` arriving from an emptied population is a different fact
wearing the same verdict.

**The placement question the handoff asked to be settled first decomposed
into three ownerships.** Transport went to `estate/client.py`, which
already owns every HTTP call to 8400 — a second caller in `monitor/`
would be the second-owner defect at the size of an HTTP client, which
this repository has refused at six scales. The verdict stayed in
`monitor/agent.py`, which also holds the `services.yaml`-to-unit identity
nothing else has. The import edge is legal and mirrors the entry's own
named precedent, `estate/agent.py` importing `units.ports` so the judge
reads the sweep's attribution rather than running `ss`. **What was
missing is the guard**: `tests/test_import_boundary.py` now admits
`estate.client` and refuses `estate.judgements`, because *a verdict is
not a fact* was the entry's first prohibition and nothing enforced it.

**Consulting that test found a gap older than the sitting.**
`sysadmin.estate` was absent from the domains `core` may not import,
unguarded since the package was created — a domain by its own module
docstring's argument. Nothing had ever breached it, so this adds a guard
rather than fixing a breach.

**The rung is derived, not borrowed.** The handoff named
`judgements.TRANSIENT_HOLDER_SEVERITY`; taking it would have made the
estate judge the source of a service's rung, which is the thing the entry
forbids. `ARBITRATED_STOP_SEVERITY` comes from
`core.escalation.QUIETEST_SEVERITY` instead — genuinely derived from
`SEVERITY_ORDER` — with the *value* pinned equal to the judge's floor by
one test and the *provenance* by another, since a value assertion cannot
see provenance.

**Two of the entry's own claims were wrong and measuring is what said
so.** Its cost figure — *"once per incident, not once per poll"* — was
taken off 23 post-dedup rows; `_raise_judged` is entered on **every**
poll and suppresses the row rather than the call, so a read wired at the
raise is ~72 pairs of calls per nightly hold. `_ensure_arbitration`
memoises per run and is called **outside** `session.begin_nested()`,
because two HTTP hops inside a savepoint on a host with
`idle_in_transaction_session_timeout=1min` is `SNAG-AGENT-003` rebuilt
inside somebody else's fix. Once per poll is nevertheless the right
*cadence*, and that is a different question from cost: it is what lets a
row raised `critical` while 8400 was unreadable be corrected on the next
run.

**It falsifies a docstring Session 117 wrote, which is corrected rather
than left to rot.** `_refresh_open` claimed its severity-disagreement
population was *"empty by construction rather than merely today"*; this
gives `% unreachable` two rungs under one title, the title deliberately
not forking because forking it would take the row out of that family's
sweep. The claim was not wrong when written — it was one family from
wrong, and *"by construction"* is the phrase that made it sound
otherwise.

**Two costs filed rather than implied.** `SNAG-AGENT-012`: the
quietening is one-directional, so a fault that begins under a lease and
outlives it keeps the quiet rung — population **zero across the whole
family** (30,716 `% unreachable` rows, 11 titles, **0** open), announced
by an `alert_rung_left_stale` log line at `warning` rather than left
silent, with `step_for`'s resolve-and-re-raise named as the shape if it
stops being zero. `SNAG-AGENT-013`: auto-restart does not consult the
arbiter and would fight it — 0 of 31 services enable it, so the scope was
deliberately not widened to reach an empty population.

**Verified live and it ships untriggered.** Driven against the running
8400 and the live database in rolled-back transactions: a real granted
lease gives `info` naming the lease, an unread estate gives `critical`, a
standing `critical` row is quietened **in place** (same row id,
`created_at` unmoved, nothing raised, nothing resolved), and the reverse
transition is refused and logged — **0 rows of residue**. Only the
five-column `active_lease` projection was stood in for; `stopped_units`
came from the real producer throughout. No service was unreachable at
deploy time, so the deployed path has not yet fired on its own.

### Session 144 — the founding measurement died, and its death was the design working (2026-08-31)

**Both estate inbox messages closed; `services.yaml` gained one line and
no code changed.** `estate-manager-api` now declares `format: json`, on
estate-manager's announcement `76e0438b` (their ADR-0079): their four
entry points emit one JSON document per record from 2026-08-31, and
without the declaration `alert_title` builds the title out of the whole
document — `SNAG-LOG-003`, the defect the `sysadmin-service` entry
already declares against. Driven against the unit's real journal, paired
record by record: **166 of 600 records change**, titles fall from
**167–249 characters of JSON to 55–70 readable ones**, and the other 434
pass through untouched because `unwrap_json_message` fails open.

**It ships untriggered twice over.** `FAULT_SEVERITIES` is `error` and
`critical`, so the `warning` filter's whole live population for that unit
is systemd's own 28 stored `Failed with result 'exit-code'.` rows; and no
estate application line has yet arrived above priority 6, all 34 non-6
records in 14 days being systemd's, so the producer's new prefix has no
witness here either.

**The guard that broke was the design's founding measurement, and its
death vindicates the design.** `test_no_other_source_declares_a_format`
pinned *"this daemon is the only JSON-writing journal source on this
box, which is the whole reason the fix went to a per-source declaration
rather than into the reader"*. A reader that had sniffed a leading `{`
would now carry a special case keyed on two applications' formats; the
declaration absorbed the second producer in one line of YAML. The set is
widened, never deleted.

**The estate's declaration is unpinnable, so it earned a live witness.**
Ours is pinned against `service.log_format`; theirs cannot be, and a
rollback would degrade **silently** through the same fail-open path — the
queue wait-gauge rule, that a graceful degradation with no separate alarm
degrades unnoticed. `test_a_declared_source_really_writes_json` reads the
raw `MESSAGE` rather than going through `read_journal`, which would only
agree with itself, and was falsified against `estate-broker-provision`.

**`218d765a` verified as a differential, not believed.**
`parse_port_registry` run either side of their `2b63122`: 19 rows both
sides, ports and projects identical and in order. Three Role cells
changed text, which their message did not mention; the only consumer of
`role` is the `duplicate_claim` detail blob, and there are no
duplicate-claimed ports.

**Deployed by reload** — `changed: ["estate-manager-api"]`,
`requires_restart: []`. The deploy check's "restart owed" was a false
positive on an mtime with no content change.

**`SNAG-TEST-003` opened, rewritten twice, then split into
`SNAG-TEST-004`.** Filed blaming load; a parallel `sysadmin_assistant`
session refuted that; this sitting then attributed both reds to the
shared session bus, which one of them never opens — the same
one-fixture-two-tests error, made while correcting it. Settled by driving
with a control: 0 and 1 unscoped `pkill` both leave `notify-send` blocked
the full 8.01 s, and **3** make it return at `rc=1` with `Process
org.freedesktop.Notifications exited with status 255`. Four tests take
the fixture, so an ordinary run fires four. `SNAG-TEST-004` is the cause
(two calls escape the fixture's private bus; remedy is scoping);
`SNAG-TEST-003` keeps the wording defect, which no mechanism touches.

**`9efef79` is that session's, folded in here at its request** (it
committed one file by pathspec and left every document alone): the live
witness fired the announcer's real `notify-send` with `--expire-time=0
--urgency=critical`, so every suite run since 2026-08-29 parked a
permanent toast on the owner's screen. Fixed by adding `--print-id` to
**both** halves — keeping them flag-uniform, since the pair must differ
in exactly one thing — and closing the notification by id. The stated
limit: `CloseNotification` answers `rc=0` for an id never issued, so the
assertion proves the call was answered, not that a toast left the screen.

### Session 137 — the allowlist is the authority, and the convention was copied without its formatter (2026-08-30)

**`SNAG-CFG-005` is closed.** `SNAG-CFG-004` gave every region of
`config.yaml` the backend owns a watcher and left the top-level `tray:`
section as the residue — exempt whole by `FOREIGN_KEYS`, because holding
a model of another parser's section is the second-owner defect, and
dropped in silence by the tray, because `load_tray_config` copies an
allowlist of seven keys out and never looks at the remainder.
`tray_section_report` is that set difference, warned in the loader and
reported never refused.

**The obvious fix shape would have shipped green, and the entry listed
it as one of three.** A walk of `tray:` against `TrayConfig`, the way
`core/config_keys.py` walks `config.yaml` against `AppConfig`. It is
legal — `sysadmin.core` must not import the tray, and the reverse is
fine — and wrong: `TrayConfig` declares **19** fields while the section
supplies **7**, the other twelve arriving from `notifications.tray:`,
`api:` and `services.yaml`. A model walk therefore calls
`tray.reminder_hours: 5` declared, when the value is read from somewhere
else and setting it there does nothing. The model over-declares relative
to the section; `TRAY_SECTION_KEYS` does not, which is exactly what
Session 136 lifting it out of the consuming loop made available.

**`notifications.tray:` is deliberately not reported here, and the test
that named that rule did not enforce it.** That region is exempt by
*leaf*, so the backend already names a typo in it — driven rather than
asserted, `notifications.tray.digest_modee` and `mute_servicess` both
come back from `report_for_file`. One fact, one speaker. But the test
asserting it drove the **backend**, which proves the other speaker
exists and does nothing to stop this one becoming a second: the mutation
that appends a `notifications.tray.*` path to the report went red on an
unrelated test **by accident**. The negative half is
`test_this_module_never_speaks_outside_its_own_section`, and it exists
because the mutation exposed its absence rather than because anyone
noticed.

**Two defects the entry did not know about, both from measuring rather
than reading, and both widening the fix past "one set difference".**
`tray: 5` **crashed the tray**: `key in tray_section` raised
`TypeError: argument of type 'int' is not iterable`, so the one section
this module hand-parses failed unhandled while `_read_services` next
door catches its own errors and costs "a mute list, not a launch". It is
`unwalkable` now — `config_keys` rule 3 — and the honest consequence is
stated in the docstring: a malformed section silently reverts **every**
tray setting to its model default, a far wider blast radius than one
misspelt key. And **`tray.api_url` has never been read**, while the
loader docstring has listed the `tray:` section as resolution priority 2
for it since `81b3bfb`, the module's first commit. The
`if "api_url" not in kwargs` guard beneath was dead by construction and
its comment is what the docstring copied. Both went, because a reader
who checks the new report against the old docstring concludes the
*report* is broken. It stays unread on purpose: `service.host`/`port` is
the one home for the backend's address, and `estate_api_url` is read
from `tray:` only because 8400 has no `service:` block — one statement
each, in different places, rather than one fact in two.

**The live drive found what no fixture would: a convention copied
without the formatter that makes it work.** The first version wrote
`logger.warning("tray_config_unknown_keys", extra={"keys": …})` — this
repository's idiom, and readable only because the backend's
`JsonFormatter` folds `extra` into the line. The tray's formatter is
`main()`'s `basicConfig(format="… %(message)s")`, which renders `extra`
nowhere, so the journal line was the bare event name: a report
announcing that a key had been dropped and unable to say which. That is
this entry's own defect one level down, and the retired check had
recorded the *opposite* lesson (its first draft read `getMessage()` and
missed the backend's `extra=`) — so the wrong half of a two-sided lesson
was copied. The keys are in the message now, and the tests read
`getMessage()` because that models the consumer.

**The `None` / non-mapping split is the subtle half, and the first draft
collapsed it.** `tray:` with nothing indented under it and `tray: []`
both look empty and only the second is a mistake; `tray: []` and
`tray: 0` are falsy *and* malformed, so the loader's original
`raw.get("tray", {}) or {}` hands the report a clean `{}` and the shape
can never be reported. The value reaches `tray_section_report`
uncoerced, and one test separates them.

**Seven mutations were driven and each lands red on the test about its
own rule**; an eighth landed red by accident and forced the missing
guard above. **Two of the new check's own tests were false greens
first** — the witness test aimed its stand-in *past* the decision and
passed having never reached the guard it names, and the unreadable-file
test patched `load_services` when the check calls `get_services`, so
nothing raised and its `unknown` came from an unrelated branch. That
second one also found a defect in the check: it read `services.yaml`
twice, two ways, so its two halves could disagree about which file they
had measured. One reader now.

**Verified live rather than only in fixtures.** The tray was restarted
against the real `config.yaml` and came up saying **nothing**, which is
this fix shipping untriggered on the box. Driven through the real
`basicConfig` at a mutated copy it emits
`tray_config_unknown_keys: config.yaml sets tray.dashbord_url,
tray.status_poll_secondss under tray:, which the tray does not read —
ignored.` and starts anyway.

**`SNAG-TRAY-011` is the residue, filed rather than absorbed.** The
warning reaches `journalctl --user -u sysadmin-tray` and nothing else:
`composed_log_sources` returns **15** units and `sysadmin-tray.service`
is not among them, so nothing ingests it, no alert row is raised and no
endpoint serves it — and `load_tray_config` has one caller, at startup,
where the backend re-reports on every `POST /api/sysadmin/reload`. Its
check measures **both** channels, because a fix for either leaves the
other standing.

**The check retired with the entry and the detector did not.** It was
driven, never read, which is why it moved cleanly over a fix whose shape
it did not anticipate — where `SNAG-CFG-004`'s own check could not. Its
two stand-in drives are now the fix's tests. **3109 → 3125**: 21 added,
5 retired with the check.

### Session 136 — the headline fix does not boot, and the file said so first (2026-08-30)

**`SNAG-CFG-004` is closed by reporting**, and its own headline fix was
refuted before a line of it was written. The entry asked whether
`sysadmin/core/config.py`'s 37 models should set `extra="forbid"` as
`sysadmin/monitor/services.py`'s four do. Walking the shipped
`config.yaml` against `AppConfig`'s field tree finds **ten keys the
backend does not declare** — `tray:` and nine leaves under
`notifications.tray:`, every one read by `sysadmin_tray/config.py`,
which parses the same file for itself. `TrayNotificationsConfig` has
said so in its own docstring all along: those keys are *"deliberately
absent here and ignored on load"*.

**The asymmetry is structural, not an inconsistency.** `services.yaml`
can forbid because every key in it belongs to the process holding the
models; `config.yaml` cannot, because it carries a region this process
does not own. And `schema_guard`'s posture runs the *other* way here —
that guard refuses because serving against the wrong schema is worse
than not serving, and serving with an ignored config key is
demonstrably not.

**What shipped reports and cannot refuse.** `core/config_keys.py`
returns a list, so there is no path by which it fails a boot or a
reload; `unknown_config_keys()` is the entry point, the lifespan warns,
and `ReloadReport.unknown_keys` carries it to the reload response. Rule
3 keeps `unwalkable` apart from `unknown`, because a subtree the walker
could not follow has zero unknown keys for the wrong reason.

**The boundary is declared and pinned.** `FOREIGN_KEYS` is hand-written
because `sysadmin.core` may not import the tray, so `TRAY_SECTION_KEYS`
and `NOTIFICATIONS_TRAY_KEYS` were lifted out of the loops consuming
them and a test asserts the two agree — import where you can, pin where
you cannot. Exempted **by leaf, not subtree**: `mute_services` is read
here, so a subtree exemption would silence `mute_servicess` on the one
key under that section the backend depends on. The dividend is that a
misspelt *tray-owned* leaf is reported too.

**The check retires and its meaning inverts.** It counted
`extra="forbid"` on both sides, and this fix moves neither count — so it
would have gone on reporting *still holds* over a landed closure,
`check_review_schedule_unread`'s defect one entry earlier. The detector
is re-homed as `TestTheAsymmetryIsDeliberateAndStays`, guarding the
opposite claim: those counts must **stay** where they are.

**Verified live rather than only against fixtures.** The daemon was
restarted at 16:26:28 and booted clean with no spurious warning; the
warning was driven through the real `configure_logging` and emits
`<4>{… "message": "config_unknown_keys" …}`, so it carries Session 61's
level prefix and a short readable signature rather than
`SNAG-LOG-003`'s 252 characters. A real `briefing_hourr: 9` written into
the shipped file returned
`{"ok": true, "unknown_keys": ["schedules.briefing_hourr"]}` from
`POST /api/sysadmin/reload`, and the file was restored byte-identical.

**`SNAG-CFG-005` is filed for the residue** — a typo inside `tray:` is
dropped by **both** parsers in silence. Measured rather than assumed:
the tray half was expected to be strict and is not, because
`load_tray_config` filters the raw section through an allowlist before
`TrayConfig` is ever constructed. Its check is *driven* rather than
read, and its first draft did not move over a stand-in fix — it read
`getMessage()` while this repository's logging convention puts the key
in `extra=`.

**Numbers.** Suite 3079 → 3107 (+33, −5 retired). Twelve mutations,
each red on the tests about its own rule; two passed against
deliberately broken code first. Snag list 108 → 109 entries, open
unmoved at 18. Ruff and mypy clean. No route, table or migration moved.

### Session 135 — the leaves went, and the check could not have watched them go (2026-08-30)

**`SNAG-CFG-002` is closed.** `schedules.review_hour` and
`review_minute` are gone from `SchedulesConfig`; `review_day_of_week`
stays, read by all three weekly reviews, its comment now saying what is
true — one leaf, three readers, generic because that is accurate rather
than vague.

**The handoff's question was closed by measurement, not decided.** It
asked whether the two leaves should be wired to something or deleted.
All three surviving reviews already carry their own hour/minute pair
(health 05:00, log 05:15, disk 05:45); the weekly *project* review these
scheduled is estate-manager's since ADR-0005; and the 05:30 their default
named is `estate-manager-review.timer`'s — re-verified live with
`systemctl --user cat`, `OnCalendar=Mon *-*-* 05:30:00`, next firing Mon
2026-08-31. There was nothing left to wire and the slot belongs to
another repository.

**The entry's own check could not have witnessed its closure**, which is
the part worth carrying. `check_review_schedule_unread` answered `match`
whenever it found no reader — as true of a deleted field as of an unread
one — so it would have gone on reporting *still holds* over a landed fix
indefinitely. A control whose observation does not move across the fix it
guards is not a control. The regression guard is keyed on **absence**
instead, and carries a second test asserting the three surviving
`*_review_*` pairs are present, because an empty intersection is
satisfied by a model with no fields at all: a constant observation is not
evidence unless something in the population would have forced a different
one. What survived the retirement is the *instrument* — rule 7's
exact-versus-substring demonstration, which never depended on the deleted
leaves existing and is re-homed rather than deleted, `FROZEN_TABLES`'
rule.

**Deleting a config field changes nothing for the person who edits the
config file**, which is what the sitting found underneath the entry.
`SchedulesConfig` inherits pydantic's `extra="ignore"`: **0 of 37**
models in `sysadmin/core/config.py` forbid unknown keys, against **4 of
4** in `sysadmin/monitor/services.py`. Driven through the real
`parse_config` against a copy of the shipped file, `briefing_hourr: 9`
parses cleanly and `briefing_hour` stays at its default 6 — the operator
has moved the morning briefing and the briefing has not moved. So one
repository answers an unknown key two ways and the silent answer is on
the file an operator edits. Filed as `SNAG-CFG-004` with a check that
reports **which of two opposite directions** the asymmetry closed in,
rather than fixed here: it is 37 models and it turns a stale key into a
refusal to boot, which is `SNAG-DB-005`'s trade taken without the
operator being ready for it.

**The adjacent comment had the same disease.** `disk_review_hour`'s said
it was staggered *"after the project review"* — gone seventeen days — and
that the briefing carries *"both narratives"*, which has been three since
Session 79. Corrected in the same edit, since leaving it would have left
the file asserting a departed review still schedules something.

Nine mutations driven, each red on exactly one intended test.

### Session 131 — the sweep that could not have seen it, and the one that can (2026-08-30)

**The handoff's question was answered `no`.** An AST sweep refusing a
live drive that reads an unsupplied singleton clock cannot exist:
`SNAG-TRAY-010` was an absence, and the pre-fix file named `dnd` zero
times at the commit that added it. Inverted to *must supply* it is 4
false positives out of 5; the read is transitive through 27 unsupplied
clock reads in production; and `should_suppress` already takes a `now=`
it does not forward, so a signature check passes.

**`tests/test_live_drive_premises.py` shipped instead** — 15 tests
requiring every `tests/test_*_live.py` to mark the test or class holding
its premise with `@pytest.mark.premise`. Seven markers landed at the
level each premise actually lives, because a name rule reaches only 3 of
5: `TestTheHazardIsReal` names what it proves, and
`test_failure_replay_live.py` asserts a different premise per test.

**The glob is a convention, so a property backs it.**
`_opens_a_live_connection` names the 6 files that open this box's
database outside the glob; they sit in `PRE_CONVENTION` with their
property re-asserted, so the premise rule is not opt-in by filename.

**Three corrections from measurement.** The detector reported itself and
is exempted-then-driven-at. `addopts = "--strict-markers"` is silently
ignored on pytest 9.0.2 — the ini option `strict_markers = true` is what
enforces it, and a test now fails if that moves. And `git checkout`
destroyed a falsification by reverting an uncommitted marker, so one
mutation re-tested the previous one's condition.

**3018 → 3033**, seven mutations each red on the intended test, no
production change.


### Session 129 — the second exception, and the filter it could not fit through (2026-08-30)

**Ruled: `wiring` joins `ports`.** estate-manager's message `8462bcc5`
put their ADR-0068 §4 condition to this repository — does the hook-wiring
check join `ports` in `JUDGED_AUDIT_CHECK`? — and stated that a decline
was a complete answer needing no justification. It is **admitted**, by
[ADR-0006](../adr/0006-wiring-joins-ports.md), because every clause of
this repository's own ownership test transfers to
`~/.claude/settings.json` and declining would have been a ruling made
*against* the test rather than by it.

**The substance is that a one-word yes would have delivered nothing.**
The filter is a conjunction and their message argues about half of it:
`wiring` emits no `breach` at any code, so admitting it by name alone
judges nothing for ever behind a green suite; widening the severity
instead re-imports `claimed_but_silent`, whose lifecycle already has an
owner here. `JUDGED_AUDIT_CHECKS` became a mapping — the only shape in
which both facts stay true — and their own "all four checks emit
`breach`" observation, offered as a footnote, is what explains *why*: a
constant written against a four-check audit had silently become a check
filter across twelve.

Driven against the real producer in their venv at their commit
`003f3bc`, against four specimens of this box's live `settings.json`.
The 2026-08-25 paste's two shapes both reach a row now, and their §4's
named failure — a dead `SessionStart` entry — is spoken.

**Also closed:** message `3f2a0e0a`, their rule-3 announcement about
`monitorable-project.md` §2.1/§2.2. Their claim that this repository's
parser is unaffected was **re-run rather than accepted**:
`parse_port_registry` reads **18** claimed rows against the edited
document, with the `health:` markers carried through as ordinary role
prose and the new marker-vocabulary table not mistaken for registry
rows. Their `health` check files nothing about 8500.

**Filed, not fixed:** `SNAG-TRAY-010` — six red tests in
`tests/test_desktop_store_live.py`, pre-existing at HEAD and unrelated to
this sitting. *(Fixed the next morning by Session 130: the drive left the
DND gate reading the real wall clock, and this sitting ran at 05:27,
inside the shipped `23:00 → 07:00` window.)*

### Session 130 — the leaf that did not look like a clock (2026-08-30)

**`SNAG-TRAY-010` fixed.** `tests/test_desktop_store_live.py` supplies
the transport and two clock readings and misses a third leaf:
`DndManager.is_active` calls `datetime.now()` itself, so
`should_suppress` refuses every `warning` inside `23:00 → 07:00` however
the notifier's clock is set. Bisecting could not find it because it is
not a property of any revision — the same tree is six red at 05:27 and
seven green at 09:37.

**The symptom's contradiction was the discriminator.** Silent yet stored
and adopted is impossible unless the write is `_adopt`'s, which is the
one that DND does not gate. `_hold_dnd_off()` now supplies the leaf
through the manager's public API, restoring **what it found** rather than
`None`, since `None` and `False` are different states and a drive that
left it forced-off would silence the window for every later test in the
process, invisibly.

**`sent_total` is the entry's own named measurement and it generalises.**
Asserted non-zero, ordered behind `dnd_suppressing` so a failure names
the gate; driven at `min_severity: critical` it catches a different gate
in the same position. The falsification also found the drive *erroring*
rather than failing there, which killed the premise test before it could
speak — `.get`-shaped now. **No production change**; 3017 → 3018.

### Session 128 — the sweep knew, and nobody asked it (2026-08-29)

**`SNAG-ESTATE-009` taken on its own terms, and it stays open.** The
entry names two closures, both refused on cost. A third and narrower one
— quietening an unattributed breach because the sweep predates it — was
considered and refused on **correctness**: `_attribution` fails open in
writing, and a failed `observe_listeners` returns no listeners at all,
so every port would read unswept and the whole ports family would drop
below `tray.notify_min_severity`. That is Session 26b-A's founding
defect at full scale, arriving as the fix for a seven-hour window.

**What was worth building is the annotation the entry has claimed to
ship since Session 57 without having it.** `PortAttribution.reading()`
answers *what the sweep knew* beside `of()`'s *who held it*, splitting
the four reasons `holder` is `None` into `held` / `transient` /
`unattributed` / `unswept` / `unknown`, each carrying `observed_at`.
`judge_audit_findings` puts it on **every** breach row and in the
roll-up — uniform, because a key present only sometimes is
`ports_checked`'s collapse one level down. The discriminator,
`unattributed_ports`, has been in the stored blob since Session 26c and
`attribution_from_blob` — written later, for a different consumer —
never read it.

**Three measurements this sitting took that the entry had not.** The
entry has **never observed its own class**: its four historic `warning`
rows predate `transient_ports` in the blob by a day, so they are a
missing key rather than a stale sweep. The window is **1.30 h median**
over 83 gaps, not the six hours the entry costs it at, because a daemon
restart re-runs the sweep at 60 s and this daemon's median life is
1.77 h. And this table's own test-count row was **34 behind** the tree.

**The check was widened, then narrowed, and the order mattered.** Its
third limb compared detail *key sets* and was blind to the fix shape
that was actually right; widened to compare values with each row's own
port normalised out, it fired; the limb then left the verdict, because
one that is true from here on can never again say anything about the
window. Narrowed, the check reads `match` — which is what says the
entry is still open.

### Session 126 — the room was not empty, it was silent (2026-08-29)

**`SNAG-SYSD-005` is fixed and its own benefit was understated by two
orders of magnitude.** `sysadmin-replay-failures.service` is a **user**
unit wanted by `graphical-session.target` running
`sysadmin/core/failure_replay.py` — the third half of the lifecycle
`unit_failure.py` owns. The handler writes the row while the application
is dead, the lifespan closes it when the application returns, and this
speaks the gap between them to the first human who arrives.

**The measurement that reranked the entry.** It argued from firings: four
of five came at a boot with nobody logged in, next login 24 min to 6.1 h
away. But `alerts` holds only **2** rows for those 5 firings — three hit
`record_unit_failure`'s dedup branch — and the one row not fixed at once
stood open **37.73 hours**. The login gap is 24 minutes of that. So the
replay recovers 37.3 hours of silence, not 24 minutes of lateness.

**And 22.2 of those hours had somebody there.** Reconstructed minute by
minute: `start-limit-hit` 18:11:15, login 18:34:41, tray started
18:34:46 — polled 8500, got nothing, went to `IconState.DISCONNECTED`
and sat there across two sessions. Only 15.5 hours were an empty room.
The real fault is that nothing on this box interrupts about a dead
daemon, occupied or not; login is merely the cheapest moment to catch
it. Filed as **`SNAG-TRAY-009`** (P2, checked), whose two silences are
multiplicative: `connection_lost` is emitted only on a *transition* and
`_was_connected` starts `False`, so a tray starting against an
already-dead backend never emits it — and `on_connection_lost` only
recolours an icon.

**The deferred flag was not needed.** The entry wanted `--unannounced`
recorded at the announcer first. That is a *history* predicate; the
replay needs a *state* one, and `resolve_unit_failures` has exactly one
production caller while `% failed` sits outside
`RESOLVABLE_TITLE_PATTERNS` and retention purges resolved rows only — so
an unresolved `systemd_onfailure` row already *means* "this unit has not
come back". No flag, no announcer change, and the second-speaker trap
dissolves with it.

**Waiting is permitted here and was refused in the announcer, and only
the number changed.** `WAIT_BUDGET_SECONDS` is derived from notify-send's
own measured 60.08 s bound, so the replay spends exactly the patience one
blocked call would have — on a mechanism that starts no
`plasma_waitforname`. Driven against a private bus: a server claiming the
name at t+2 s is caught at 3.02 s and the notification arrives intact.
The read comes **before** the wait, so a clean login costs 0.34 s and no
D-Bus call.

**Every open entry names a check again** — 19 open, 0 unchecked, the
property `SNAG-SYSD-005` broke on opening and its closure restores.

### Session 122 — a cut identity is not an identity (2026-08-29)

**`SNAG-LOG-013`'s stated scope was the smaller half.** It prices the
defeat of a cap at *"a GET advice surface, no toast and no row"*;
`log_signature.alert_title` cuts the same signature and **is** the dedup
key, the resolve key and the tray fingerprint. Measured on the entry's
own population, recovered from `raw_line`: **39 signatures → 21 titles,
four covering 2, 2, 2 and 16 faults**, one pair at a raising severity.
A cut title now carries eight hex characters of the signature's SHA-256
— a per-row pure function, which is exactly what the entry says its
roll-up half cannot have. Live: **50 → 50** titles, 2 cut, 0 colliding;
**0** open rows carried a cut title, so no fingerprint moved. The entry
stays open on its roll-up half. estate-manager's message `99679328`
closed in the same sitting: `read_snags` raises where it returned an
empty read, and both guards in `parser_counts` stay.

### Session 121 — a gauge is not a ledger (2026-08-29)

Closed `SNAG-DOCS-007`, the cost Session 120 filed against its own
ruling. The entry asks to close *“by the paragraph dropping the
figures”*; the run says **one figure too many**, and the split is what
the sitting was for.

The paragraph states two things. Its **counts** (`102 entries, 19
open`) are derived live and printed at both ends of every sitting, so a
written copy is `SNAG-DB-003`'s shape — deleted. Its **movement**
(*“one opened and none closed … the entry is `SNAG-DOCS-007`”*) has no
second producer anywhere: `MOVEMENT_ANCHOR` is `HEAD` and
`measure_movement` compares the **working tree** against it, so the
delta is non-zero only between the edit and the commit, and no anchor
lets it name *which* entry moved. Deleting it leaves the register with
no ledger and nothing able to rebuild one.

**The entry overstated the derivation's reach at one of its two ends,
and the sitting's own opening run refuted it.** Its fourth bullet reads
*“Both moments the report is actually read — preflight, and postflight
before the docs commit — anchor correctly”*; preflight runs on a clean
tree, where the comparison is `unmoved` **by construction**, and it
printed `unmoved since bc43986` at 102 / 19 either side. Postflight
before the docs commit is the *only* correct moment, so the population
is every other run rather than a mid-sitting re-run.
`measure_movement`'s docstring carried the same claim at its owner and
is corrected in the same edit — reading the module confirms it, running
preflight refutes it, which is `verify-ops-claims-live` applied to a
correction rather than to a remedy.

Driven at three revisions through estate-manager's `read_snags`:
`639e594` reads 100 / 17, `c46872a` 101 / 18, `bc43986` 102 / 19. The
series is in git and no run of the derivation reports it — which is
precisely why the movement sentence survives the counts.

**Only the named paragraph lost its numbers.** The “Previously:” chain
keeps its own: those state what was current at a commit that has
passed, nothing prints them, and they cannot drift. Session 120's is
struck because 102 / 19 was still the register's *current* count on the
day it closed.

**No check is owed, and the shape the entry named is now unreachable.**
It asked for two specimens, one with the paragraph's figure altered —
there is no figure left to alter. `check_movement` keeps its own red
state (the two parsers disagreeing about the open count) and the nine
falsifications Session 120 drove at it.

### Session 120 — the figure a tool can derive is not a claim a human states (2026-08-29)

Took Session 118's second open decision, which Session 119 carried
forward unchanged. `snag_list.md`'s header paragraph records what moved
this sitting and **nothing read it** — `ops_claims` reads `STATUS.md`'s
block, `snag_claims` reads the entries' own claims, and the paragraph
fell between them, six sittings stale when Session 118 found it.

The ruling is to **derive rather than check**. `convention:movement` is
the last line of every `sysadmin-check-snags` run: entry and open counts
from estate-manager's own `read_snags`, and the delta against the anchor
commit, whose sha and subject it names. Three measurements refused the
obvious claim-check — the paragraph has no reader, the figure is
derivable from `git show`, and thirteen paragraphs write the sentence
seven ways.

It is a measurement rather than a decoration because it has a red state:
the two parsers disagreeing about the **open** count, which is the figure
this register sweeps parting from the figure the board publishes. Totals
are deliberately not compared. An empty read is `unknown` and never a
count — Session 119 published `100 → 0 entries` off exactly that — and a
failed anchor read is `unknown` and never `unmoved`.

Found and fixed with it: **the banner was stating the open count two
ways**, printing `76 open` eight lines below the checker's `18 open
entries`, its list opening with ten entries titled FIXED.
`sysadmin-check-snags --list-open` is the reader now, so
`closure_declared` has one implementation instead of a shell
approximation free to drift from the number above it.

`SNAG-DOCS-007` was the stated cost and **closed on 2026-08-29 by
Session 121**: the paragraph's counts are gone, its movement sentence
stays, and the derivation now reads `-1 open since bc43986` beside a
paragraph that states no count at all.

### Session 119 — the model is not the file (2026-08-28)

Built the guard Session 118 offered and did not build:
`tests/test_config_defaults.py::TestTheLoudRungEndsBeforeItIsRestated`
asserts `service_discovery.scan_interval_hours` +
`estate_judge.poll_interval_hours` **<** the tray's `reminder_hours`,
which is what bounds `SNAG-ESTATE-009`'s loud rung at 7 h against a 24 h
restatement.

**The stated weakness does not hold.** `TrayNotificationsConfig` parses
`mute_services` alone — and it is the *backend's* slice, not the file.
`sysadmin_tray/config.py` reads `notifications.tray.reminder_hours` out
of the same `config.yaml`, ships in this wheel, and is already imported
across the seam by `tests/test_desktop_notifier.py`. Driven at a copy
with the tray leaf set to 6 it returns `6.0` while the understudy reads
`24.0`.

**A second gap closed with it**: the existing pin compares two objects
constructed with **no file**, so the shipped copies could read 6 and 24
with the suite green. `TestTheTwoSpeakersAgreeInTheShippedFile` is the
half that can see an edit.

Reminders switched off are a **skip**, not a pass and not a failure; the
sweep being *enabled* is asserted separately, because a frozen sweep
bounds the loud rung by nothing at all and the sum cannot see it. Three
drafts of the detector test each keyed on a mutable value and each was
falsified out. `SNAG-CFG-003` is filed for what a test cannot reach: a
`SIGHUP` installs a config nothing has judged coherent.

### Session 118 — a cost that fell is not a mechanism that closed (2026-08-28)

**`SNAG-ESTATE-009` is re-ranked and stays `P3`**, and the number holds
for a different reason than the one it was given. No code changed; the
live parser reads **100 entries / 17 open** either side, the entry is
`P3` and open in both, and its body goes 5,538 → 8,286 characters.

**The bullet the re-rank replaces was wrong on the day it was
written.** It priced the failure at *one extra toast at the start of a
dev session*. `reminder_hours` had shipped the day before — the tray's
at **2026-08-16 09:22:44** (`3752c78`, `SNAG-ESTATE-003`) and the
understudy's at **11:59:53** (`a330e31`, `SNAG-TRAY-007`) — against an
entry filed 2026-08-17. So a mid-window start cost one toast **and
every restatement due after it**, unbounded in the listener's life.

**The family's whole life is six rows in three episodes, and it
settles the point.** `3.13 h` and **`31.88 h`** at `warning`
(2026-08-16 12:07:11 → 2026-08-17 20:00:05 — raised **2 h 45 m** after
the tray's reminder was committed), then `11.23 h` at `info`, the third
pair being the first raised after Session 57's quietening shipped. The
long one outlives `reminder_hours` by **eight hours**. Note what that
also says: **both loud episodes predate the quietening**, so this
entry's own defect — loud *because the sweep had not seen the port* —
has never produced a row on this box. A sharper statement of its
check's "the population is a timing accident".

**What Session 117 bought is a ceiling, not a narrower window.** The
loud rung now ends at the first judge run after the next sweep:
`service_discovery.scan_interval_hours` (6) +
`estate_judge.poll_interval_hours` (1) = **7 h worst case**, against a
`reminder_hours` of **24**. The repeat is unreachable by **arithmetic**
where it was previously survived by luck, and the old bullet's claim —
one transient toast, nothing after it — is true for the first time.

**`P4` was considered and refused on this file's only precedent for
it.** `SNAG-LOG-014` is `P4` because it is *residue from a fixed entry,
not a live defect*; this mechanism is untouched. Driven **after** the
fix, `unswept_port_is_loud` still reads `match` — port 65008 named by
the stored sweep and judged `info` holding `transient: True`, port
65009 not named and judged `warning` with `holder=None` and an
identical detail key set, `alerts_raised=2`. Moving the number would
say a mechanism closed when only a cost fell.

**The new ranking lever is arithmetical and unasserted.** The ceiling
is a *sum* measured against `reminder_hours`, so anything lifting it
past 24 h returns the entry to its pre-fix cost — raising
`scan_interval_hours` to daily, the opposite of the refused hourly
sweep and the cheap move the day the six-hourly sweep is costed, puts
the sum at **25**. The margin is **3.4×** and nothing asserts it,
because the inequality's right-hand side is
`notifications.tray.reminder_hours` and `TrayNotificationsConfig`
deliberately does not parse it (`mute_services` alone —
`may_quieten_in_place` rule 2, one leaf over). A guard could only read
`notifications.desktop.reminder_hours`, the understudy's copy, which is
the same 24 and is held to the tray's by a **comment** rather than a
test. Offered, not built.

**Checks green either side**: eighteen snag claims and all nine ops
claims. Alembic head 018, suite untouched, no restart owed.


### Session 115 — the understudy remembers, and adopts what it never announced (2026-08-28)

`SNAG-TRAY-008` is **fixed**, both faces. The reminder sweep's
population was the keys of an in-memory dict, so a fault raised while
the tray was watching was never adopted when the tray died, and a daemon
restart forgot everything. `desktop_notifications` (migration 018) holds
one row per fault the daemon is speaking for; `DesktopNotifier._adopt`
carries a standing fault it never announced.

**The measurement is the finding.** `sysadmin.service` started **111
times in 28.26 days**, median uptime **1.77 h**, and **5 of 110** lives
reached the 24 hours `reminder_hours` asks for — so the reminder was
unavailable on 95 % of this daemon's lives, which the entry did not know
because it filed the population as zero and stopped. The same number
refutes its shape-of-fix: `TrayPresence` is monotonic and in-memory, so
"the tray has been absent for a full `reminder_hours`" is observable
only by a process that has lived a day. The gate ships as an **anchor**
instead — the absence sets the adopted fault's clock back, capped at one
interval — which keeps the quiet-by-construction property and is
reachable here.

**The two faces are multiplicative**, which is the mechanism the entry
describes without naming: adoption alone re-adopts on every restart and
re-arms its own anchor, and the store alone leaves face 1 as filed.
`SNAG-AGENT-008`'s shape.

**Three consequences, each the opposite of the obvious version.** The
clock became a **wall** clock — no monotonic value survives a process,
and `CLOCK_MONOTONIC` does not survive a suspend either, which a 24-hour
interval about elapsed human time should count. The store records what
was **said** and never what the tray's presence implied, so rule 2's
stamp-forward stays in memory and writes are bounded at one per
notification. And the old cheapest gate — *"a sweep that has said
nothing issues no query at all"* — is exactly the entry, so it became
**one query per process**.

**The check retired with the entry and the detector did not.**
`tests/test_desktop_store_live.py` is the two-sweep timeline against the
real database, and it is stronger than the check: once adoption landed,
"the restarted instance restated its predecessor's fault" was producible
by adoption alone, so it asks *how* it was inherited.

**`rolled_back_drive` had to be hardened first, and the leak was real** —
three rows into `alerts` and three into `desktop_notifications` during
this session's own suite run, because `_remember` commits and a plain
session rollback holds only while nothing inside commits. The session
now joins the connection's transaction by savepoint.

### Session 114 — the prediction carries the zone it was copied from (2026-08-28)

`SNAG-ESTATE-013` is **fixed**. `ops_claims`' `check:expires` marker took
a bare wall clock, so the one marker ever written — copied off an estate
surface publishing `started_at: "2026-08-25T03:32:17.538288+00:00"` —
named an instant an hour before the thing it predicted, and the check
reported the passed boundary *correctly*, having nothing to disagree
with. `EXPIRY_FORMAT` is `%Y-%m-%dT%H:%M%z`, `EXPIRY_NAIVE_FORMAT`
recognises the old shape without accepting it, and `check_expiry`
refuses a naive `now`. `SNAG-LOG-009`'s defect one document over,
answered with `journal.since_timestamp`'s posture — refuse the ambiguity,
never resolve it by a default, because a default is right on the box that
wrote the marker and silently wrong by the offset everywhere else.

**The refusal names the fault rather than reporting a malformation.** A
naive stamp comes back as *"carries no offset, so it names two instants —
03:32+01:00 if the sentence is in this box's clock, 03:32+00:00 if it was
copied from a UTC-stamped surface"*. `schema_guard`'s rule that every way
of not-knowing fails closed **with its own message**: the generic form
would report this entry's own founding case as a typo, and the two
readings are exactly what the author has to choose between.

**The format was the smaller half; rule 9's pin is what makes this more
than a spelling change.** The pin renders the marker's instant into this
box's zone before looking for it in the prose. Naive, the entry's own
block satisfied it — marker `03:32`, sentence 03:32, both an hour from
the moment predicted — because two statements of one fact had nothing to
disagree *about*. With an offset they visibly disagree, and the note says
which of them is in which clock.

**`@<epoch>` was refused, and the reason is the reader rather than the
instant.** `since_timestamp` renders exactly that for this fault, and
correctly: journalctl's zone is the reader's and unknown, and its
`--since` has no offset syntax at all. Here the consumer is
`check_expiry` and the *author* is a human who must also write the
instant's wall clock into the sentence beside it. An epoch is
unambiguous and unreadable, so accepting one would buy rule 8 by deleting
rule 9 — the pin would become checkable by the checker alone.

**⚠️ The entry's "two hours" is two mechanisms and only one of them is the
marker's**, which its own Cause bullet contains without separating: the
timer fired at 04:32 local (the offset) and the hourly judge swept at
05:32 (the poll interval). Driven at the entry's own producer stamp
through the real `check_expiry` before the fix, the displacement is
**1 hour**, exactly this box's offset. A fix sized to two hours would
have gone looking for a second cause that is not there.

**The guard ships with an empty live population and a full historical
one**, measured rather than assumed either way. `git log -S
'check:expires'` finds **one** marker ever written to `STATUS.md` and it
is naive — 1 of 1 — and the block carries none today, so nothing in the
document is refused on the day the refusal lands. That is the reverse of
`since_timestamp`, whose population is empty *by construction*; here it
is empty by circumstance, and the next marker anyone writes is the one it
exists for.

**The check reported `mismatch` against the fix that closed its entry**,
naming both halves of the shape-of-fix the entry had written down. It
then retired, since every member of `CHECKS` names an open entry — but
the *detector* did not: the three-zone drive is re-homed as
`TestTheInstantCarriesItsZone`, `SNAG-LOG-006`'s treatment one sitting
on. Suite **2795 → 2792**: 12 added, 15 retired, and the total going down
is the whole reason the arithmetic is stated.

**Seven mutations, each red on exactly the right test, and one of them is
the entry's own blindness.** Dropping the `now` guard breaks the single
test that drives a marker carrying *no instant at all* — the path that
never reaches the subtraction, which is the whole argument for guarding
at the entry point rather than at the arithmetic. Rendering the pin in
the marker's own zone breaks the founding case at `Europe/London` and
`America/New_York` and **passes at UTC**, because at zero offset the two
renderings are the same string; so the parametrised zone test carries a
`displaced` flag naming which of its three rows are witnesses and which
is a control, rather than letting three green rows read as three pieces
of evidence.

### Session 113 — the register says nought instead of falling silent (2026-08-28)

`SNAG-DOCS-006` is **fixed**. `check_convention` appended its
`convention:unchecked` finding inside `if unchecked:`, so a register in
which every open entry carries a check said *nothing* about the
convention — indistinguishable, to a reader of `sysadmin-check-snags`,
from the finding having been deleted, renamed, or failing to run. The
line is published in every state now. `ports_checked`'s rule at this
repository's own claims register, which was the one surface it had never
reached, because nobody had seen the zero until 2026-08-27.

**The blocker was a contract and it is honoured rather than changed.**
`_convention` returned `unknown` unconditionally, so a zero line would
pin the tool at exit **2** for ever — which `claude-precommit.sh` and
`claude-postflight.sh` read. It takes a `verdict` now, defaulting to
`unknown`, so the two families that are faults by construction (`marker:`
and `pin:`) are untouched and only the family that *can* hold gained the
ability to say so.

**Three states.** A non-empty set is `unknown`, unchanged. An empty set
over a population is `match`. An empty set over **no open entries at
all** is `unknown` again — reachable, because a document whose entries
are all closed parses cleanly and `load_entries` reports a problem only
when it reads no entries whatever, so the count is vacuous rather than
good. Serving that as `match` would be zero-because-blind wearing
zero-because-clean, one level inside the fix for exactly that.

**This entry was the last member of its own population**, so closing it
drove the new branch live in the same sitting: `?? … 1 of 21 …
SNAG-DOCS-006` became `ok … 0 of 20 open entries carry no check`, and
the report exited **0** for the first time since the module shipped at
16 of 24 unchecked.

**Two of the five falsifications passed against deliberately broken
code.** `overall([])` is `match` and exits `0`, so an exit-status test
written as two status assertions agreed with the silence it exists to
catch; and the vacuous fixture carried no marker, so `pin:fake_one`
fired and supplied the `2` the branch under test was meant to supply.
Both repaired by asserting the finding's presence before its status. A
sixth passes against the old code by design and says so — the regression
pin that an unchecked entry still reports `unknown`.

No check was added and none retired: the entry never had one, so
checks-in-registry is unmoved at **20**. Suite 2790 → **2795**. Daemon
restarted at 14:44:14 for a file it does not import, which is the deploy
check's stated cost.

### Session 112 — the cheap fix reached one shape of four (2026-08-28)

`SNAG-LOG-006` is **fixed**, by the candidate its entry called honest,
and the costing the entry never did is what settles it. `BaseAgent.run`
swallows `_execute`'s exception, so what escapes it is the bookkeeping
around the work — four shapes, driven through the real `run()`. Only one
of them writes an `agent_run_failed` line, so the alternative fix
(narrow `COVERED_SIGNATURES` to `run_type == "scheduled"`) can speak for
one quarter of the fault while costing strictly more: it needs
`unwrap_json_message` to promote `run_type` out of the envelope, which
that function's own docstring refuses.

Three things only measurement could have said. The entry's second
trigger is **not** `POST /api/files/organise` — that is a synchronous
action route; the discarded task was in `POST /api/files/scan`, and the
check watching this counted files rather than routes so it stayed green
either side of the error. The asyncio fallback the entry filed as
unmeasured is **prompt rather than GC-deferred**, and *when* was never
the problem: it emits a 252-character signature and a 220-character
title naming `BaseAgent.run` and this module's path, so all five
triggers share one row, an unrelated move of `run()` forks it, and on a
shorter checkout path the exception text falls inside the cap and forks
a row per failure. And `exc_info` lands under its own envelope key, so
the shipped signal is `manual_run_failed` — 17 characters — with the
traceback kept in `raw_line`.

`spawn_manual_run` holds the reference; `_report_manual_run` speaks, to
the **journal and never the database**, because the exceptions that
reach it are database failures. Cancellation is recorded at `warning`,
which `FAULT_SEVERITIES` excludes — stored and counted without raising,
the rung doing the work no second suppression list would need to.

### Session 111 — the notice had no lifecycle because it should never have been a row (2026-08-28)

`SNAG-AGENT-010` is **fixed**, by the second of the two candidates its
entry named and against the framing that entry gave it. Three modules
wrote an identical `info` alert announcing a weekly review —
`files/review.py`, `monitor/log_review.py`, `monitor/health_review.py` —
and the entry named one, because only the disk review's scheduler path
has ever fired. All three writes are gone; nothing replaces them,
because `briefing/data.py` has been reading all three review tables
directly the whole time.

**What ruled out the lifecycle was arithmetic, not taste.** Resolving
the previous notice on the next generation anchors the fix to the next
run; the observed row was written 2026-08-17 05:45 and the next
generation was due 08-24 05:45, when the daemon was down. That fix
leaves the row open today, at 271 hours, saying the same wrong thing.

**The clinching observation was one payload disagreeing with itself**:
the briefing dropped the Weekly Disk Review as stale at 11 days
(`_REVIEW_FRESH_DAYS` is 8) and carried the alert announcing it in the
same envelope. And a notice was being counted as a *fault* by this
repository's own health review, whose alert-delta query takes no
severity filter — so the health review would have narrated its own
announcement in the next week's `new_titles`. The repo's fixture had
already normalised that, using `"Weekly disk review ready"` as its
example of a fault.

Verified live through the real commit path: all three entry points
driven against the real database, `alerts` at 665,937 before and after,
delta 0 each, 0 residue, 0 open rows. The standing row was resolved by
hand — nothing in the code could reach it once the writer was gone — and
is retention-reachable for the first time. Daemon restarted at 13:41:23.


### Session 110 — the fix landed in the ranked order, and half-closed a different entry (2026-08-28)

`SNAG-AGENT-009` is **fixed**, in Session 109's order: `_raise_judged`
(838), the estate judge (131), ports (0, and its docstring now says so).
`BaseAgent.refresh_alert` owns the comparison and the write; *finding*
the row stays with each caller, because the three reach it three
different ways. Three rules the build settled that the entry did not
name — `details` is compared through a **JSON round trip** or the gate
degenerates into "always"; the caller's dict is what is **stored**, so a
raise and a refresh write one row; and `_written_titles` splits from
`_open_titles`, so a title judged twice inside one run is suppressed
rather than rewritten.

**It half-closed `SNAG-ESTATE-010`**, which that entry's own check said
out loud: the `holder` blob now reaches a standing row while the rung
still does not, and the clause came **out** of `QuietenReading.reached` rather
than the verdict being accepted — a `reached` still reading the blob
answers `mismatch` whatever happens to the rung. The falsification is
kept and inverted.

Two things only running it could have said: the refresh read lands on
`idx_alerts_active`, not the agent-scoped index the docstring first
claimed (**84 buffers, 0.098 ms** at 665,937 rows), and **four
stand-ins modelled a database this code no longer talks to** — including
`conftest.mock_session`, whose bare `AsyncMock` returns a coroutine from
`.scalars()`. Suite **2750 → 2764**, 14 added and none removed; five
falsifications all fire. Parser reads **99 entries either side, open 24
→ 23** at estate-manager's committed `047eb8a`. Restart owed and taken,
13:03:15. No migration.

### Session 109 — the population was in the family the entry never named, and the one stale row was a different bug (2026-08-28)

`SNAG-AGENT-009` is **measured and decided**, not fixed: `P3` holds, the
scope moves to `SysAdminAgent._raise_judged` (**838** held events, which
the entry never names) ahead of the estate judge (**131**) and ports
(**0 in 65 runs**), and candidate 1 is taken with the other two refuted
on measurement. The drift is **42 of 42** held polls across the 23
post-dedup `High VRAM usage` rows, mean 8.15 pp. `SNAG-AGENT-010` opened
for the single open row on the box, which is stale by the opposite
mechanism — never held, never resolvable, never purged. Parser reads
**98 → 99 entries, open 23 → 24** at estate-manager's committed
`516116f`. Suite **2750**, unmoved. No migration, no restart, no
production code.

### Session 108 — the blocker was gone, the family was three times bigger, and the name never carried the fact (2026-08-28)

`SNAG-PORT-003` is **closed** and `SNAG-AGENT-009` opened; the live
parser reads **97 → 98 entries with open unmoved at 23**, re-derived
through `estate.snags.read_snags` at estate-manager's committed
`516116f`. Suite **2755 → 2750** (2755 − 18 + 13), ruff and mypy clean,
all nine ops claims ok. Daemon restarted **10:37:40** — owed this time,
`ports.py` being imported by `create_app()`. No migration.

The entry deferred itself for want of a second instance; the box had
eight, five of them a shape the entry never mentions and two of those
holding ports while it recorded a population of one. Both fixes it named
reach at most three. The fix is systemd's own answer — the two
`systemd/transient` directories, listed, the same class of signal
`discover_units` reads for enablement — **added** to the `.scope` suffix
and not substituted for it, because `init.scope` is `Transient=yes` in
both managers and in neither directory.

### Session 106 — the band moved, nothing was raised, and the parse underneath it was wrong (2026-08-27)

`SNAG-PORT-001` is **closed**, `SNAG-PORT-002` opened and closed in the
same sitting, and `SNAG-PORT-003` **opened**. The live parser reads
**95 → 97 entries with open unmoved at 23**, re-derived rather than
compared against any figure taken before 14:21:59 today (estate-manager's
message `8c1706d3`). Suite **2732 → 2737**, all green — the two that were
red on a clean tree are the two that closed.

**The widening raises nothing, measured rather than argued.** Driven
through `ServiceDiscoveryAgent._check_ports`' own path against the real
`ss`, `services.yaml` and registry document at both bands: findings
0 → 0. 1883 is root-owned and therefore `unattributed`, so it is
compared against nothing by construction; 1716's holder matches no
project on disk. The entry's stated reason for deferring had an **empty
population**, and the deferral was still right, because the only way to
know that is to drive it.

**The entry named four comparisons and `in_range` has two callers**, one
of which is not a comparison — the same overstatement estate-manager
made and corrected on their side of the same copy the same day.

**`SNAG-PORT-002` is what the drive found underneath.** The cgroup path
was read from its last colon, so every D-Bus activated unit lost its
`dbus-` prefix and the `/user@1000.service/` that decides scope: a user
unit stamped `system` since Session 26c, 1 of 30 listeners. Visible only
because 1716 is the first mis-parsed listener ever to fall inside an
audited band; hidden because no fixture had ever carried a colon in a
path. Three falsifications, and a fourth stand-in that passes because
`split(":", 2)[-1]` and `[2]` are the same code behind the guard.

**`SNAG-PORT-003` is filed rather than guessed.** A D-Bus unit's name
carries a per-session bus id — precisely what `Listener.transient` exists
for, and not what it tests. Both obvious fixes are rules tuned against
one observation, and this box has one.

### Session 103 — the twenty-fifth check, and the register runs out of entries (2026-08-27)

`SNAG-ESTATE-006` is **checked and stays open**; `SNAG-ESTATE-014` is
**closed** and `SNAG-DOCS-006` **opened** as its stated cost. Checked
entries **22 → 23**, unchecked **2 → 1**, open unmoved at **24** — one
closed, one opened — measured either side of the edit by driving
`load_entries`, and by estate-manager's `read_snags`, which reads
**93 → 94 rows / 24 open**. Suite **2731 → 2751**,
`tests/test_snag_claims.py` **327 → 347**.

**Two instruments, and the second exists because the first goes blind at
the finish line.** `audit_code_unpublished` reads the live wire through
`estate.client.pull_all` — the call the judge itself makes — and drives
the producer's own `findings()` route at a specimen in their
interpreter. Live: **11** published keys across 3 findings, no `code`,
and the two readings produced the *identical* key set, which makes the
wire a control on the specimen rather than only evidence. Across **135
audit runs the audit has never once been clean**, so rule 1's weather
problem does not bite here — but a clean audit publishes `"findings":
[]` and says nothing about its own key set, so a wire-only check would
report `unknown` on precisely the morning the estate succeeded.

**The verdict rule is that the wire can refute and cannot confirm**, and
**no database is opened in either repository**: the key set is decided by
a literal dict in their serialiser, so the session is a stand-in
dispatching on SQLAlchemy's public `column_descriptions` and
`get_db_session` is poisoned *before* their router is imported. Nothing
splits `fingerprint`, which is the entry's own **not worked around here**
bullet turned into a guard over this module's source and its probe
string.

**What the sitting found that the entry does not say**: `Finding.as_payload`
— the form published on the bus — **does** carry `code`. So it is not
computed-and-dropped everywhere, only on the one surface this repository
reads.

**Three falsifications passed against deliberately broken code**, and
each found something rather than merely needing a wider patch: the
substring one exposed `WireReading.detail_keys` as **collected and read
by nothing** (`SNAG-CFG-001`'s shape inside the check), and the two
fingerprint ones exposed a detector aimed at the shape the *producer*
uses rather than the shape *this module* would — a dict key, since it
reads JSON and never producer objects.

**`SNAG-ESTATE-014` closed on a reading its own bullets had not reached.**
The trigger it was handed — `convention:unchecked` reaching zero — does
not exist: the count reaches **one**, the one is the entry, and it cannot
reach zero while the entry is open. What closes it is that the entry is
about a **harm** rather than a count, and the number of entries whose
claims are only as fresh as the last hand sweep is now **nought**. Its
objection to exempting itself does reach the closure and is answered
rather than dodged: what separates them is whether the work is finished.
That the machinery survives was demonstrated by accident — filing
`SNAG-DOCS-006` in the same edit put the report straight back to
`1 of 24`.

### Session 102 — the twenty-fourth check, and two judgements about being unchecked (2026-08-27)

`SNAG-SVC-001` is **checked and stays open**. Checked entries
**21 → 22**, unchecked **3 → 2**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`load_entries`, and by estate-manager's `read_snags`, which reads
**93 rows / 24 open** both times. Suite **2713 → 2731**,
`tests/test_snag_claims.py` **309 → 327**.

**The first check whose claim is a conflict between two rules rather than
a fact about one**, so it drives both sides and reports only whether the
conflict is still live — never which of the two resolutions to take,
which the entry's own fourth bullet reserves to the owner.

- **The contention is built, because the population is the weather.**
  Zero services on this box produce the shape and the entry says so, so a
  check that looked for the row would report the entry refuted on every
  day the box behaved and live the first afternoon a health path went
  slow. The subject is a fully-covered 7-day window carrying exactly
  `flap_min_episodes` outages of one 300s check each — built from *health
  rows* rather than from a hand-set `ReliabilityScore`, since
  `longest_outage_minutes == 0` is the fact being reproduced and
  asserting it would be the check agreeing with itself.
- **Three instruments.** The row's own `evidence: rate` and `0 points
  recoverable`; the advice module's **import set**, since a correlation
  with the service's own logs cannot be computed by a module that has not
  got the data; and `known_noise` rule 3 **driven rather than read** —
  one signature at 200 occurrences offered four ways, noise when old and
  flat, `new_signature`/`surge` when it is not, silent below the floor.
- **Rule 7's fifth and sharpest instance.**
  `service_recommendations.py` names `log_actions` twice in its module
  docstring, `log_trends` in `_flapping_row`'s and `known_noise` in the
  very docstring that filed this snag, so a grep reports all three as
  already wired and an `ast` import walk sees none.
- **A third way for this entry to stop being true, which it does not
  anticipate**: rule 3 relaxing dissolves the conflict with nobody having
  touched the row. And the narrowing going is `unknown` rather than
  either verdict — the headline claim gets *more* true while the entry's
  own third bullet goes false, which is an entry to rewrite rather than a
  verdict to grade.
- **One falsification passed against deliberately broken code**, the
  sixth here and a new shape: the change-kind rule is stated by
  `recommend`'s loop *and* by `_is_noise_candidate`'s admitted tuple, so
  a stand-in aimed at the predicate — where the rule is *documented* —
  never reaches the decision.

**Two judgements, decided rather than built**, and the first turned on a
live read rather than on the argument it was expected to turn on.

- **`SNAG-ESTATE-006` may not declare itself *checked by another
  guard*.** Its pre-staged test reads a fixture this repository recorded,
  so it fires when somebody re-captures the payload and never on the day
  estate-manager adds the column, which is what its bullet claims.
  Measured against the wire instead: `GET :8400/api/audit/findings`
  publishes **11** keys across 3 live findings and `code` is not among
  them. So the claim holds, and the entry is a **live candidate** for the
  next check rather than an exempt one — the ranking that put it behind
  `SNAG-SVC-001` is refuted, because the two would measure the fixture
  and the wire.
- **`SNAG-ESTATE-014` may not declare itself *unmeasurable by rule*
  either**, and the refusal costs it nothing: it is already named every
  sitting by the finding it is about, which its own second bullet calls
  the fix for invisibility. Exempting it would let the entry about the
  count subtract itself from its own subject.
- **The rule both judgements settle**: a declaration may move an entry
  between *published* buckets and may never remove it from the report —
  `ops_claims` rule 1 at the level of the register. Unbuilt deliberately;
  one live candidate is not enough population to design against.

### Session 101 — the twenty-third check, and a symptom that agrees with itself only in summer (2026-08-27)

`SNAG-ESTATE-007` is **checked and stays open**. Checked entries
**20 → 21**, unchecked **4 → 3**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **24 open** both times. Suite
**2682 → 2713**, `tests/test_snag_claims.py` **278 → 309**.

**The fifth check across a repository boundary, the second whose subject
is what another repository _publishes_, and the first where the fix could
land in three places.** The entry's own cause bullet names one — the
queue pool's missing `connect_args={"options": "-c timezone=utc"}` — and
the surface would equally stop stamping local if `invariants()` or the
route's serialiser normalised. So an `ast` walk for that kwargs entry
reports *still holds* for two of the three, and all three are driven here
as real stand-ins. What is read is the **string on the wire**, taken by
calling the route object mounted at the queue's published path, which is
how the private serialiser is reached without ever naming it.

**The obvious instrument agrees with itself only in summer, and that is
the finding worth carrying.** The entry quotes one rendered offset and
`Europe/London` renders `+00:00` from late October to late March, so a
one-instant check reports this entry refuted every winter and true again
every spring, having measured nothing but the calendar. Two instants six
months apart go through every surface and *stamps UTC* means **both**
came back at zero — a property of the connection rather than of the
month.

**The cause is driven rather than read, and the same reading validates
the stand-in.** `pg_settings.source` says where the connection's
`TimeZone` came from: `client` when it asked, which is exactly what the
proposed fix produces, and `configuration file` when it inherited the
cluster's. That separates *their fix landed* from *the box's default
moved to UTC*, which renders identically and leaves the mechanism intact
— the second is `unknown`, because `match` would assert a rendering
nobody saw. It is also what makes pointing their pool at **this**
repository's database legitimate: a setting sourced from the
configuration file is cluster-wide, and a `database` or `user` source
says it is not, at which point the check stops answering. The estate
rules forbid one application reading another's database, and a check
running at both ends of every sitting would be the most regular breach of
that rule on the box — so nothing of theirs is opened, no socket is
bound, and the synthetic lease lives in a `TEMPORARY` table.

**Its population is empty by construction**, which is rule 1's shape for
the fourth time. `active_lease` has read `null` on every occasion anyone
has looked, so it is re-read live every run as *evidence* and never as
the verdict — a check waiting for a granted lease would be measuring
whether somebody happens to be holding the GPU this afternoon.

**Two stand-ins corrected the check before it shipped.** A route that
normalises while the connection stays local was read as *the box's
default moved*: the draft asked whether `invariants()` had handed UTC up,
where the question is whether the **connection** is in UTC — and
`zone_stamps_utc` now resolves the reported name rather than comparing it
to the string `UTC`, which `Etc/UTC` refutes. And a surface publishing
only `granted_at` satisfied *every offset is zero* through
`Europe/London`, which is the seasonal defect arriving by a dropped field
instead of by the calendar.

**A falsification passed against broken code for the fifth time here.**
Removing the completeness half of `stamps_utc` broke nothing, because the
verdict body refuses an incomplete reading one gate earlier. Unlike
Session 100's, this one was *not* a gate to delete: `complete` is defined
once and consulted twice, so it is not two statements of one fact, and
the property is public and would otherwise answer *yes, UTC* about a
surface only ever asked about January. The gate stayed and the
observation moved to the property, where it is reachable.

**One red came in from another repository and was repaired rather than
absorbed.** estate-manager added a `1883` row to their port registry
today under their ADR-0054 — the shared MQTT broker, deliberately outside
the ranges this repository audits and recorded as their
`SNAG-ESTATE-070` — and
`test_our_parser_and_the_estates_agree_on_the_live_document` pinned the
accepted-unaudited set at `[22000]`. Widening our ranges is their
decision to ask for, so the expectation is corrected and the reason
recorded beside it.

### Session 100 — the twenty-second check, and the first about somebody else's surface (2026-08-27)

`SNAG-ESTATE-004` is **checked and stays open**. Checked entries
**19 → 20**, unchecked **5 → 4**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **24 open** both times against
estate-manager at `1e7a9a9`, recorded because Session 99 learned that a
count taken over that boundary can move underneath the measurement.
Suite **2653 → 2682**, `tests/test_snag_claims.py` **249 → 278**.

**The fourth check driven across a repository boundary, and the first
whose claim is entirely about another repository's _surface_.** The three
before it ask what estate-manager's code *computes* — what a dataclass
offers, what a function returns, what a parser reads — and every one of
those is an answer a reader of their source could have reached. This
entry says their guide states *never take a tool's default port* in prose
and that **nothing enforces it**, which is a claim about what their audit
*publishes*. So the instrument is `CheckResult.findings`.

### What the sitting settled

- **The obvious probe is an `ast` walk and it is wrong in three
  directions at once.** The entry's own fix bullet names
  `WELL_KNOWN_DEFAULTS = {3000, 5000, 8080, 8888, 9000}`, so looking for
  that constant in `checks/ports.py` is the first thing anyone would
  write — and it reports *still holds* for a fix that inlines the set,
  one that renames it, and one that files the finding from a different
  check module. All three are driven here as real stand-ins, alongside a
  fourth that fills only the finding's `subject`; the findings surface is
  blind to every one of them.
- **The mechanism is asked and never the population, and this is where
  that is starkest.** The live violation is *one port*, and the guide's
  own annotation says it should move to 8301 when next touched — so a
  check that looked for a contended port on the box would report the
  entry refuted the day somebody moved one service, having measured
  nothing about whether the rule acquired an enforcer. The contention is
  **built**: a registry document claiming all five defaults, each
  answering, through their real public `run_check` with a stub `runner=`,
  so no privilege, no socket and nothing written into their tree. A test
  drives the same check with the population emptied and with it emptied
  *and* a branch present, and the verdict moves only with the branch.
- **The listener witness is load-bearing in the direction easiest to
  miss.** The fix would land in the claimed loop, so the witness that
  matters is in the *other* one: with the listener set empty every probed
  default is claimed-and-silent and their existing branch names all five,
  which a check asking "does a finding name a default port" reads as the
  fix having landed. That is driven as its own test off the raw probe, so
  the gate is shown to be standing in front of something rather than
  asserted to be.
- **The code vocabulary is learned from the witnesses and never typed
  here**, which is Session 87's rule read past the symbol names it was
  written about. A fix filing under any slug at all is seen; the test
  saying so had to be rewritten, because the obvious one — a renamed
  contention code — passes against a typed copy too, and only renaming
  *their* three codes tells the two implementations apart.
- **The rule half refutes the entry for the opposite reason to the
  enforcement half**, so they are reported apart —
  `check_sysd_ollama_ordering`'s shape. The sentence leaving §2.1 is the
  premise dying with the complaint intact, and a guide that cannot be
  read is `unknown`, because *still holds* asserts a rule exists to go
  unenforced. The handover half is deliberately **not** measured: the
  entry says their ids will not correspond, so matching a counterpart
  would be prose similarity dressed as a measurement, which is rule 7.

### A falsification passed against broken code, and deleted a gate

The draft carried the obvious symmetry — a witness row per loop — and a
stand-in with the claimed-half gate removed **broke nothing**. Deleting
that loop leaves every probed default unreached, so the reachability
drive always answers first and the symmetric gate was unreachable by
construction; the test naming it asserted a substring both notes carried,
which is how it stayed. The gate is gone rather than repaired, and the
silent row stays for what it actually supplies, which is vocabulary
rather than liveness.

That reachability drive is itself a correction. The first version asked
`parse_registry` directly whether their parser had read the probe's rows
— a second implementation of a fact `run_check` already establishes, and
a stub narrowing the parser to the audited ranges walked straight through
it: the standalone call saw five rows while the check saw three, and the
verdict came back *still holds* having put nothing in front of anything.
The document is driven **twice** now, once with the defaults answering
and once with them silent, so reachability is measured through the one
call whose reading matters.

Live at the close: the five probed defaults go unremarked, both witnesses
fire, the observed vocabulary is **three** codes where the entry names
two, `8080 (venture-assistant)` is the live population, §2.1 still states
the rule, and the verdict is taken against estate-manager's **committed**
tree — which is not the same as deployed on 8400, and the wording says so.

### Session 99 — the twenty-first check, and the entry that was runner-up three times (2026-08-27)

`SNAG-SVC-002` is **checked and stays open**. Checked entries
**18 → 19**, unchecked **6 → 5**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **24 open** both times. Suite
**2635 → 2653**, `tests/test_snag_claims.py` **231 → 249**.

**The entry had been ranked runner-up three times without being taken,
and rule 1 is the whole reason.** The obvious check measures the
disjointness its own second bullet reports — measured this sitting, nine
declared timers against five scheduled agents with **zero overlap** — and
that is a property of *this box*. One scheduled job moved to a `oneshot`
+ `.timer`, which `monitorable-project.md` requires of every new one, and
such a check reports the entry fixed on a day nobody has touched either
module. `check_timer_agent_two_owners` builds the thing this box has not
got instead: an agent whose schedule is a timer.

### What the sitting settled

- **One fact, two vocabularies, and the shared name is not what makes it
  one subject.** A daily schedule with one last-run instant goes to
  `summarise_agent`/`stalls.evaluate` as an agent that has not run and to
  `recommend` as a timer whose `LastTriggerUSec` stopped moving. Both
  speak, simultaneously: `snagcheck_timer_agent agent stalled` at
  `warning` escalating to `critical`, beside `armed but has not fired for
  3.0 days` at `advice`. They form the opinion at the same moment because
  `timer_stale_multiplier` **is** `stall_grace_multiplier` — the entry's
  own stated mitigation, so one elapsed value crosses both thresholds.
- **Three instruments, because the two fixes the entry names move
  different things.** A family going silent is the fix it asks for; a
  rung appearing on `timer_stale` is the fix it **forbids by name**, and
  both families go on speaking either way, so that half is unreachable
  from the first. Its headline claim — neither knows the other exists —
  is measured as the *importer sets*, disjoint today (`monitor/agent.py`
  against `health_review.py`, `reliability_history.py` and
  `routers/services.py`), which is the one thing a composing caller
  feeding `_observed_fires` into the stall family could not avoid moving.
- **Rule 7 for the fourth time.** `service_recommendations.py` already
  carries the word `stalls`, in `_timer_stale_row`'s own docstring — the
  entry's sentence written into the module the entry is about. A grep
  reports the cross-reference as already existing; an `ast` walk over
  imports never sees a docstring. Pinned by a test at the real file.
- **Two witnesses, because a family gone silent and a family the probe
  cannot reach report identically.** A schedule that ran one cadence ago
  must come back not stalled, and a still-firing timer whose last run
  failed must yield a `timer_failed` row through the same call and the
  same confidence gate. The second witness's `unknown` names *both*
  honest readings — the timer half removed is the entry's own fix and
  worth a look — because a reader who does not go and look would
  otherwise never learn the fix may have landed.
- **The check is excluded from its own population, and it is not
  bookkeeping.** Driving both families means importing both, so without
  the exclusion the only thing in this repository that knows the two
  exist would refute the entry on every run.

### The falsification corrected the check, and then corrected its reason

The first stand-in put a rung at six cadences and came back `match` —
the stand-in was wrong. The second clocked its rung off the box's one
escalation gap, the only shape available to a family recomputed per
request, and **also** passed: the fresh drive stood one cadence past the
threshold, and the two drives straddle a rung only when its gap falls in
`[overshoot, overshoot + 2 x escalate_after_hours)`. At one cadence that
window is **24h to 72h** here, so every rung shorter than a day read loud
at both drives and the check saw no movement. The stated reason written
first — "the two numbers coincide, so it reads loud at both" — was
approximately right and imprecise, and only the arithmetic said which.
The overshoot is one check interval now, widening the window to **5
minutes to 48 hours**; a test drives both constants and asserts the old
one still hides a sub-cadence rung, so the constant is load-bearing
rather than tidy.

### Found on the way, without looking for it

**A count taken across a repository boundary moved underneath the
measurement, and the natural reading of it was wrong.** Driving
`estate.snags.read_snags` over this document returned **93** entries
against the **70** three sittings had recorded, which reads as prose gone
stale — the class this block keeps producing. It is not.  `estate-lib` is
an **editable install resolving into estate-manager's working tree**, so
the figure was taken against uncommitted work in another repository at
14:12; their commit `1e7a9a9` landed at **14:21:59**, growing the reader
a third dialect (their ADR-0052, closing `SNAG-ESTATE-064`). Re-run at
the previous reader, today's document reads **70 entries / 24 open** —
exactly what was recorded, and the *open* half is 24 under both readers,
which is the figure the board publishes and the one
`TestAgainstTheOwningParser` pins. So no count in this sitting depended
on it. What it cost is the lesson: `cross-repo-instrument-must-be-public`
says record the other repository's commit state beside the verdict, and
not doing so put a wrong correction into three documents before the
timeline was checked. Filed at estate-manager as friction rather than
absorbed — an editable install publishes a neighbour's *uncommitted*
state with no version stamp, and a consumer cannot tell that from a
document of its own going stale.

### Session 98 — the twentieth check, and the first that measures a silence (2026-08-27)

**`SNAG-ESTATE-012` is checked and stays open.** Checked entries
**17 → 18**, unchecked **7 → 6**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`, which reads **70 entries / 24 open** both
times. The check re-measures the entry's mechanism; it does not fix it,
and it deliberately is not the marker convention the entry rules out.

**Every other check in this registry looks for something and reports
whether it is there. This one reports that a sentence reaches
nothing** — and an absence is exactly what a broken probe produces for
free. `check_unmarked_sentence_invisible` builds a printed region in the
shape of this block, carrying **two** sentences: one a pattern can reach
(`**7 routes**`, with its `<!--check:routes-->` beside it) and one of the
entry's own three unmarked instances. The real `ops_claims.check_all` is
driven over both documents, and the claim is that the second is silently
absent from every family.

**The marked half is the witness, and it is the whole design.** A reader
that had stopped cutting the region — a moved heading, a
`printed_region` returning `None`, a module that no longer opens the
file — reports the unmarked sentence *exactly* as a working reader does.
So the silence is evidence only when something in the same region would
have forced a different observation. Both halves of the convention are
witnessed because they fail apart: the figure coming back out of the
prose is `read_claim`, and the absence of an `unclaimed:routes` finding
beside it is `read_markers` having reached the marker — which is the half
both refused remedies would have had to extend.

**Two instruments, because the two shapes a fix can take are invisible
to each other.** A remedy reporting *"blockquote paragraph 2 carries no
marker"* names no sentence and slips past a word search; a remedy that
folds the sentence into an existing claim's note adds no key and slips
past a projection of the report. So the report is compared on what only
the document decides — which keys ran, and what each read out of the
region — **and** searched for words it could only have taken from the
sentence. Both were driven as real stand-ins wrapping the real
`check_all`, along with two further shapes: a `CLAIM_PATTERNS` entry
grown to reach a specimen, and a sentence that *collides* with the marked
figure. All four come back `mismatch` on the test that names them.

**A difference the sentence cannot explain is `unknown`, never
`mismatch`.** `open_titles` states its `documented` as "N named" over the
live alert table, so two drives 0.4 s apart can honestly disagree about
it, and reading that as a landed fix would be reporting this
repository's own traffic. What makes the split safe rather than a shrug
is a **direction** rule: a sentence added to a block can only change what
of it can be read, so `None → value` and `value → None` are attributable
to the sentence and `value → other value` is not.

Three things only running it could have said, and two of them corrected
the check rather than the entry:

- **A falsification corrected the check's own ordering.** The draft
  re-witnessed every drive, so the collision stand-in — `read_claim`
  refuses two distinct matches rather than resolving them — tripped the
  witness and came back `unknown` as *"the probe could not be driven"*.
  That is the wrong verdict in the dangerous direction for a sentence
  that had visibly been read. The two documents differ by the sentence
  and nothing else, so once the **baseline** has witnessed the reader, a
  witness that fails on the specimen *is* the sentence — and a remedy
  refusing a region that carries an unmarked paragraph lands there too.
- **A constant moved because an instrument was silently dead.** At a
  five-character floor the middle specimen yielded no distinctive word
  at all: `8400` is four characters and `answers` is already the subject
  of the `/health` claim, so one of the three specimens was covered by
  the projection alone and nothing said so. That is this entry's own
  symptom arriving inside its own check. The floor is four now, three is
  refused in the other direction, and a specimen with nothing left after
  the subtraction is **named** rather than left to be inferred.
- **The specimens are the entry's own three sentences**, verbatim from
  its `Symptom` bullet, and a test pins that they are still in it. They
  are three rather than one because they fail differently — an
  imperative with no figure in it, a bare number beside a port, and a
  snag id with a count spelled as a word — and a pattern family added
  later would plausibly reach the second and not the first.

**And the block produced a third live instance of the entry while the
check for it was being written.** *"sixteen written, fourteen in the
registry"* had been four sittings stale (it is twenty and eighteen), and
like Session 97's 15/9 and Session 93's 10/14 it carries no figure any
pattern holds and no marker any check can be pinned to. Corrected by
hand, because that is what `SNAG-ESTATE-012` says this class costs — and
the new check, by construction, cannot reach it.

### Session 97 — the nineteenth check, and one entry with two faces (2026-08-27)

**`SNAG-TRAY-008` is checked and stays open.** Checked entries
**16 → 17**, unchecked **8 → 7**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2619 tests pass, 0 skipped** (2591 + 28, and the arithmetic is
the check). Ruff clean, mypy clean. `sysadmin/snag_claims.py` was
edited, so the daemon was restarted at **12:01:12** and all nine ops
claims read green.

### The verdict is a conjunction, and the entry wrote that rule itself

`SNAG-TRAY-008` names **two** faults with one root — the reminder
sweep's population is what *this process* announced. A fault raised
while the tray was watching is never adopted, and a restart forgets
everything. The entry then says, in its own body, that *"a fix that
addresses only the second half leaves the first looking fixed"*.

So `reached` is `unheard_adopted and remembered`. Persisting the spoken
set is the fix the entry names and the obvious one to land; driven as a
falsification, it closes the second face outright and comes back
**`match`** with the moved half in the note. A refuted claim is a
candidate for closure (rule 2); a half-refuted one is not, and reporting
it as `mismatch` would close an entry that is still half true.

### The restart is a second instance, and its forgotten fault is the first one's witness

Both faces run on **one** timeline: the tray is watching, then away; one
sweep; a fresh `DesktopNotifier` sharing the same clock and the same
session; another sweep. The fault the second instance has forgotten is
the one the first announced *and restated* — so "announced before the
restart" is demonstrated rather than asserted, and no fourth title
differs in more than the thing being held.

Two leaves are supplied and everything above them is production. The
notifier already takes an injected `clock`; `TrayPresence` takes none —
deliberately, by its own docstring — so its single reading is
overridden and `is_watching` stays the module's own comparison against
the live `tray_grace_seconds`. `mark_seen()` is still called, because
the entry's first face is a tray that was *here and left* and the base
class keeps that apart from one never seen.

### Three real rows rather than a stub session

The rows are opened by `BaseAgent.raise_alert` — which also buffers the
`alert.raised` payload the bus carries, so the event handed to the
subscriber is the producer's rather than a literal — and the whole drive
is rolled back in a `finally`. A stub factory answering `IN (:spoken)`
would have been cheaper and would be **a control the fix breaks**: the
shape this entry sketches reads the *open* rows and caps them, which a
stub built around the unfixed query could not answer.

### Two things only running it could have said

- **The transport falsification is unreachable.** The probe overrides
  `send` to keep `notify-send` and the session bus out of a check that
  runs at both ends of every sitting — and that makes the module's own
  transport unreachable from a stand-in: patching
  `DesktopNotifier.send` leaves the probe landing every notification.
  Re-aimed at **gate 2** declining, which is the shape a live box
  produces, and the shadowing is now pinned by a test of its own rather
  than left for the next author of a falsification that passes.
- **Reading the roll-up body is load-bearing, not defensive.** A fix
  that adopts one further fault pushes the very sweep this probe drives
  over `_ROLLUP_THRESHOLD`, and a folded reminder is titled
  `"N faults still open"`. Narrowed to titles alone, all three
  fix-shaped tests fail together — so a check comparing titles would
  have read a landed fix as silence and lost its own witness with it.

Ten falsifications, each firing on exactly the test that names it, and
the two headline ones **are** the two fixes rather than stand-ins for
them.

### Two figures in this dashboard were stale, and neither could have been reported

The sub-session block claimed **15** checked snag entries and **9**
unchecked against a live 16 and 8 — Session 96 moved them and did not
correct the sentence. That is `SNAG-ESTATE-012`'s class exactly: a
figure `ops_claims` holds no pattern for is one `check_markers` cannot
see and one no marker can be pinned to. The entry's second live
instance, found without looking for it, and it is why it is this
dashboard's "Next up".

The Testing row's **166** tests against a file holding **187** is the
same failure and is **not** counted as an instance, which is the more
useful half: that row sits *outside* the region `ops_claims` reads at
all, so no marker convention reaches it and the gap is wider than the
one `SNAG-ESTATE-012` describes. Both corrected by re-counting rather
than incrementing — 17/7 and 215.

### Session 96 — the eighteenth check, and the sweep window driven rather than counted (2026-08-27)

**`SNAG-ESTATE-009` is checked and stays open.** Checked entries
**15 → 16**, unchecked **9 → 8**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2591 tests pass, 0 skipped** (2570 + 21, and the arithmetic is
the check: a green suite cannot witness tests that no longer exist).
Ruff clean, mypy clean. `sysadmin/snag_claims.py` was edited, so the
daemon was restarted at **09:49:45** and all nine ops claims read green.

### The fourth consecutive entry decided by rule 1

`SNAG-ESTATE-009` is about a dev server started *between* sweeps: the
sweep runs six-hourly and the judge hourly, so whether a listener is
attributed depends on which side of a six-hour boundary somebody opened
an editor. **No count can reach that** — it measures when a window was
opened, not whether the window exists — and the two rows it was filed
from are the same two `SNAG-ESTATE-010` was filed from, which have since
resolved.

What made the mechanism drivable is one fact about the production
reader: `EstateJudgeAgent._attribution` reads **a single** stored
`unit_audits` row and argues in writing for reading no other. So **a
sweep that names one of two ports is a sweep taken before the second
listener started**, and one `_execute` call judges both.

### The witness runs the other way round from Session 95's

There an unmoved row needed a moved row beside it. Here a **loud** row
needs a **quiet** one: a family whose quietening had been reverted —
Session 57 backed out, the blob key renamed, `attribution_from_blob`
broken — raises the unswept port loudly for a reason that has nothing to
do with the window, and looks identical. Driven as the falsification:
with `_attribution` returning an empty `PortAttribution`, every
assertion the `match` branch makes about the unswept port is still true
and the verdict is `unknown`.

### Two limbs were measured unreachable and deleted rather than shipped

Both were found by falsifications passing against deliberately broken
code, which is the fourth and fifth time in this file.

- **`attributed_unswept` was a fourth limb of `reached`.** It is
  `_attribution`'s answer read directly; `unswept_holder` is the same
  answer read off the row the run raised, and inside this probe the two
  cannot disagree. Removing it left
  `test_a_judge_that_runs_ss_itself_is_a_mismatch` **passing against the
  break**. It stays in the report and out of the verdict, and the holder
  limb got a scenario that isolates it: a live look that finds a *real
  unit* comes back non-transient, so the rung is untouched and only
  `details['holder']` moves.
- **A second roll-up precheck could never fire.** A roll-up depends on
  the breach count against `max_rows`, which is identical for both
  attributions, so the guard beside the first was unreachable — and the
  titles now come from the judgement already validated, one call fewer.

### Three things only running it could have said

- **Backdating the probe's sweep by one `scan_interval_hours` breaks
  it.** Stamping the row six hours old models the entry's own arithmetic
  and puts the row *behind the box's own newest sweep*, which
  `_attribution` then reads instead: the real sweep 1.21 h old won, the
  swept port came back unattributed, the witness failed and the verdict
  was `unknown`. The probe has to own the newest row or it is not
  holding the variable. `attribution_age_hours` is reported so that is
  visible rather than assumed.
- **The falsification harness was unsound for same-length edits.** `.pyc`
  invalidation is (source mtime, source size) at one-second mtime
  granularity, so swapping `-` for `'` inside a constant within the same
  second reuses stale bytecode and the falsification silently runs the
  *unbroken* module. The injection guard fired on one sweep and passed
  on the next with the identical patch applied. The harness now clears
  `__pycache__` either side of every case.
- **A committing stand-in leaked exactly the two rows the guard
  predicted**, and this probe's guard counts by title from the start —
  it opens no row by hand, so every row it can leak is one it *raised*,
  wearing the estate's own `summary`. Cleaned out by id and re-verified.

### The scaffolding is shared, not copied

`findings_transport`, `mounted_judge` and `rolled_back_drive` were
**extracted from** Session 95's probe rather than written beside it, so
the `httpx.MockTransport`, the client mounting and the unconditional
`finally` rollback have one statement between the two probes. All 19 of
Session 95's tests passed unchanged across the extraction, which is what
makes "identical scaffolding" a measurement rather than a claim.

**Fourteen falsifications, fourteen fired**, plus the committing
stand-in. The two probes share no port and no holder string, so a
survivor names which one left it.

### Session 95 — the seventeenth check, and the first that writes to the database (2026-08-27)

**`SNAG-ESTATE-010` is checked and stays open.** Checked entries
**14 → 15**, unchecked **10 → 9**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
estate-manager's `read_snags`, which reads **70 entries / 24 open** both
times. **2570 tests pass, 0 skipped** (2551 + 19). Ruff clean, mypy
clean. `sysadmin/snag_claims.py` was edited, so the daemon was restarted
at **08:31:41** and all nine ops claims read green.

### The entry predicted its own population away

It is filed off two live rows — `Estate port 3110 registry breach` and
`Estate port 8110 registry breach`, both VS Code dev servers standing at
`warning` with `details['holder']` null while Session 57's fix ran three
lines away — and its **own third bullet** says it self-clears when the
editor closes. So a check that counted those rows would report the entry
refuted by somebody shutting a window. Confirmed on the box: **zero open
`estate_judge` rows** today, and the mechanism is untouched. That is
rule 1's sharpest case so far, because the entry names its own expiry.

What is left is drivable end to end, and the instrument is the agent's
own `_execute` — the claim is a branch three statements in, where a
judgement whose title is already open is skipped *before* anything reads
its severity or its details, and every fix the entry contemplates lands
in that same loop.

### The assertion is the reach, never the rung

The entry's fourth bullet records that resolve-and-re-raise on a severity
mismatch is the obvious fix and rebuilds `monitor/collation.py`'s
flip-flop. So a real fix may land as an **in-place rung**, as a
**resolved row plus a fresh one**, or as the **`holder` blob alone with
the severity unmoved** — and a check reading that one column would call
two of those three no change. All three are driven as stand-ins modelling
the fix, each firing its own test.

### The unmoved row is evidence only beside a row that moved

The same `_execute` call judges a **second** synthetic port with nothing
open under its title, and that row must land at the quieter rung
carrying a transient holder before either verdict means anything: a judge
that had stopped computing `info`, or a sweep whose attribution no longer
reached this family, leaves the standing row exactly as untouched as the
dedup does. Driven as the falsification — with `_attribution` returning
an empty `PortAttribution` the standing row is still unmoved and the
verdict is `unknown`, not `match`.

Both rungs and both titles are read off `judge_audit_findings`, run
purely first on the same payload and attribution, so a reworded title
moves the probe with it instead of leaving it opening a row the run never
judges. Pinned by an `ast` sweep: no string constant outside a docstring
may carry the producer's title, and `TRANSIENT_HOLDER_SEVERITY` may not
be imported at all.

### Writing to the live database, and what pays for it

Fifteen falsifications, fifteen fired. The one that justifies the write
at all replaces the rollback with a **commit**: rows leak, and the
clean-run and failed-run guards fire independently, the second proving
the `finally` covers a drive that raised.

**That falsification corrected the guard it was aimed at.**
`_surviving_rows` counted by the probe's own message — and the row the
probe *raises*, the witness and the more interesting write, carries the
estate's own `summary`, because `raise_alert` is handed the judgement's
message. So the guard was blind to exactly the row the check exists to
produce, and the committing stand-in leaked one past it. Found on the
box, deleted, and the guard now counts by title.

**One falsification passed against deliberately broken code, for the
fourth time here and in a new shape.** The restore of `logging.disable`
was asserted inside a `caplog.at_level` block, and pytest's
`catching_logs` sets `logging.disable(NOTSET)` on entry and puts the
previous level back on exit — so the fixture restored the global whatever
the module did. Split into two tests, only one of which may touch
`caplog`. The three earlier instances all asserted a *value* where they
meant provenance; this one asserts a *global* inside the one context
manager that owns it.

### Session 94 — the sixteenth check, and the first that sends a request (2026-08-26)

**`SNAG-UNITS-003` is checked and stays open.** Checked entries
**13 → 14**, unchecked **11 → 10**, open unmoved at **24** (none opened,
none closed). **2551 tests pass, 0
skipped** (2532 + 19). Ruff clean, mypy clean. `sysadmin/snag_claims.py`
was edited, so the daemon was restarted at **21:20:50** and all nine ops
claims read green.

**The entry makes two claims and only one of them is a mechanism, which
is why both are measured.** Its body claims that `_services_yaml_snippet`
emits a health path it never fetched; its *title* claims that on this box
the guess is "wrong more often than right", counted at **4 right and 7
wrong of 11** on 2026-08-15 by an author whose own first draft said "two
of twelve". Rule 1 says a check tests the mechanism rather than the
population — and here the population **is** the sentence in the title, so
it is a claim like any other. The two refute the entry for opposite
reasons and the notes say which: the generator learning to *look* is the
**fix**, while the box's services converging on the contract's path is
the claim's **premise** dying with the generator unchanged.
`check_sysd_ollama_ordering`'s split, one entry over.

### The recount, and what it settled

Live, by outbound probe: **4 right, 7 wrong of 11, 0 unmeasured** — the
entry's own figure, reproduced eleven days later by a different
instrument. That is worth stating precisely because the ranking could not
have assumed it: the entry counted **declared urls in `services.yaml`**
and this counts **what answers on the port**, and the two agreeing is a
measurement rather than a tautology. A service serving both paths would
have separated them, and none does.

None of 4, 7 or 11 appears in the module. What stops the entry's figure
fossilising is not a constant to compare against but the recount printed
in `detail` at both ends of every sitting — and a drift that keeps the
*direction* is deliberately **not** a mismatch, or adding one service to
`services.yaml` would send a sitting to judge an entry whose substance
nothing had touched.

### Four rules, three of them the opposite of the obvious implementation

1. **The guess is read off the generator, never written down here.** The
   check probes the url the advice would have a human paste, so a rename
   of the default moves the probe with it. It also settles part of the
   mechanism half with **no network at all**: a generator emitting
   *different* paths for different ports is observing something, whatever
   those paths are.
2. **Every probe is paired with a control, and the control is the
   service's own declared url.** A guess that does not answer says
   nothing about the *path* when nothing answers on that port — a stopped
   service reports every path wrong, so a check without the control would
   report this entry **holding hardest on the morning the box came up**.
   A service failing its own url is `unmeasured` and named, never counted
   as evidence: `ports_checked`'s rule.
3. **A constant path is not by itself evidence that nothing looked.** An
   implementation that probed, found nothing answering and fell back to
   the same default emits the same constant — and the two frontends that
   declare no path at all are exactly that case, since no probing
   implementation would emit a bare url either. So the refutation needs a
   **witness**: a port where the emitted path fails and the service's own
   path answers. Five today (8080, 8081, 8082, 8200, 8500). With no
   witness the verdict is `unknown`, which is also how the check degrades
   when the box is offline — so the offline behaviour is a case of the
   rule and not a special case bolted onto it.
4. **The reading is the monitor's, not this module's.** The probe is
   `SysAdminAgent._check_http` under `_http.scoped()` as a real run does,
   and its verdict is classified by `is_fault` off the CHECK constraint's
   own map. Nothing here compares a status to `"ok"` by hand —
   `SNAG-API-004` is what that costs, and an `ast` sweep now refuses it
   in this module too.

### Two things the drafting had to be talked out of

**The private function the handoff named was the wrong target.** Driving
`_services_yaml_snippet` directly is what the recommendation said, and
the entry's own candidate fix is *"probe once when the snippet is
generated"* — a moment on the whole path. A probe in the **caller**,
passing the answering path down, fixes the entry and leaves that
innermost function emitting the same literal, so a check bound to it
would report a landed fix as no change at all. The public
`recommendations_for_scan` is driven instead:
`a-control-a-fix-breaks-is-not-a-control` met from its other side.

**Driving the generator at two ports and finding one path is not the
mechanism test it looks like**, which is rule 3 above and was the draft's
real defect. It needed the witness notion before the constant meant
anything.

### The falsifications, and the report defect one of them found

Nine breaks driven, nine fired, each on the test that names it: the
control removed, the tie boundary narrowed to `<`, the witness gate
removed, the url rebuilt here instead of read from the snippet, the
loopback guard dropped, `is_witness` stripped of its path requirement,
the population filter widened, the constancy branch removed, and the
empty path joined away. Two of them fire **two** tests, which is the
shape to expect when one rule carries two claims.

The last one is a defect a fixture would not have shown. Rendering the
per-port note with `", ".join` printed the two bare-url services as
nothing — `ports (, /api/health, /api/v1/health, /health)`, a note saying
four paths and naming three. `SNAG-BRIEF-002`'s rule at the size of a
list separator, and it is now `(no path)` with a test that fails against
the join.

One test is a **control with a measured-empty population and says so**:
`test_the_probe_never_leaves_this_machine` records every url the check
sends a request to and asserts each is loopback, and removing the
loopback guard entirely leaves it green — because `services.yaml`'s only
off-box url is `internet`, which declares neither a port nor a unit and
is filtered out one step earlier. The falsification that fires is the one
driving a remote entry through the prober directly, and the docstring
names it rather than letting the silence read as coverage.

### The unplanned find: two readers, two totals, one open count

`snag_claims.load_entries` reports **68** entries for `snag_list.md`
where estate-manager's `read_snags` reports **70** — measured either side
of this sitting's edit, so neither moved. Both report **24 open**, which
is the figure the banner and the report use, and the difference is the
local reader skipping closed and template sections by construction
(`open_sections`). Session 93's handoff published 70; that was the owning
parser's number, not a figure this sitting changed, and it is recorded
here so a next sitting does not read 68 as a regression.

### Session 93 — the fifteenth check, and the straddle that was hemisphere-blind (2026-08-26)

**`SNAG-ESTATE-013` is checked.** Checked entries **12 → 13**, unchecked
**12 → 11**, open unmoved at **24** (none opened, none closed). **2529
tests pass** (2514 + 15). Ruff clean, mypy clean. `sysadmin/snag_claims.py`
was edited, so the daemon was restarted at **20:30:36** and all nine ops
claims read green.

**The first check in this registry whose subject is this repository's own
claims machinery.** Every other one measures the box, another
repository's tree or a domain module; `check_expiry_naive_instant` drives
`sysadmin.ops_claims` — the sibling composition root
`check-ops-claims.sh` runs at both ends of a sitting. It needs no
database, no subprocess and no cross-repo read, which is why it was
written before the entries that need all three. The module is **imported
and driven, never reimplemented**: the claim *is* what `check_expiry`
does with a marker, so a copy of the parse would measure the copy.

### The hour, measured

`STATUS.md` carries **no live `expires` marker**, so rule 1 applies and
the mechanism is built rather than waited for. One producer stamp — the
one `SNAG-ESTATE-013` quotes, `2026-08-25T03:32:17.538288+00:00` —
rendered two ways, and the block that carries it names **both** wall
clocks so rule 9's pin passes whichever a fix would render back out.

Driven at `Europe/London`: judged one minute before the instant the
marker's own text names, the prediction is **`1 minute to run`**; judged
one minute before the predicted event *actually happens*, it has already
**`passed 59 minutes ago`**; judged at the event itself, **`passed 1 hour
ago`**. The offset-bearing stamp is not understood at all — and not as an
unsupported form but as a **malformed marker**.

**The entry's title is truer than it states.** It says the check "cannot
say so"; the naive reading and the unparsed offset are *both* `unknown`,
so the report prints `??` either way and nothing rendered distinguishes
them. Only `Claim.measured` does, which is why the probe classifies on
that field and never on the verdict.

### Two things a run refuted about the draft

**The obvious single straddle holds only east of Greenwich.** Written
first as *"judged a minute before the event, does it already say
expired"* — which is the defect exactly as this box shows it, and it is
half the world. At `America/New_York` the same marker names an instant
**four hours after** its subject, so the prediction *outlives* what it
predicted and the early-expiry test reports the module correct. That is
`SNAG-LOG-009`'s own *"N hours late at UTC−N"* arriving one document
over, and it was found by running the probe in three zones rather than by
reasoning about it. What is measured now is the **displacement of the
boundary**, whose sign the offset decides and whose existence it does
not.

**A control a landed fix breaks is not a control.** The draft asserted
the timer flips at the marker's own text, *or the probe has stopped
isolating the question*. A stand-in modelling the fix — a module reading
the zoneless stamp as the moment it was **stamped** — moves the boundary
onto the event, fails that control, and comes back `unknown` where it
should come back `mismatch`. So the boundary is *located* rather than
assumed, and three states get three verdicts: flipping at the producer's
instant is the defect gone by a route neither half of the entry's fix
names, flipping at the marker's text is the defect standing, flipping at
neither is the only reading the probe declines.

### It declines at UTC, and that is the point

The magnitude **is** the local offset. At `UTC+00:00` the two stamps name
one instant and a zone-blind reading is indistinguishable from a correct
one, so the check reports `unknown` — `ports_checked`'s rule,
zero-because-blind never served as zero-because-clean. Reporting
`mismatch` there would close an entry whose mechanism is untouched. CI
runs at UTC, so the check is honest there by construction and the tests
nominate their own zones rather than depending on the box.

### One falsification passed against the broken code

Seven breaks were driven. Six fired. The seventh — rendering the naive
stamp with the module's own `EXPIRY_FORMAT` — **passed**, because
`snag_claims` does `from sysadmin.ops_claims import EXPIRY_FORMAT` and
the test patched only the owner: the module's *behaviour* moved while the
probe's rendering did not. A guard asserting a **value** where it means
**provenance**, for the third time in this repository. Repaired twice
over — the patch now moves both names, which is what a landed fix does,
and an `ast` sweep refuses `EXPIRY_FORMAT` as an argument to any
`strftime` in the check, because only the source can answer provenance.
Session 92's rule — *banning the instrument beats measuring the
property* — met from a second direction one file over.

The coupling itself was the draft's real defect and only the
falsification named it: with the naive stamp rendered from the module's
accepted format, a fix that moves that format makes the "naive" drive
silently render `+0000`, so the probe's control moves with the thing it
is controlling for and a landed fix comes back looking like no fix at
all. `EXPIRY_NAIVE_FORMAT` is owned here now — what the *document* wrote
is not the same fact as what the module accepts.

### A guard that had gone silent rather than red

Measuring the entry count for the preamble — a routine step, not a
target — found `read_snags` gone: estate-manager moved it from
`estate_service` into `estate.snags` in `estate-lib` at **17:06:27**
today (their `a5c1834`). `TestAgainstTheOwningParser` is the only thing
keeping this repository's second implementation of their closure rule
honest, and it reached that function by shelling into their venv with
`if result.returncode != 0: pytest.skip(...)`. An `ImportError` exits 1,
so the class read a moved symbol as *"estate-manager's parser would not
run"* — a property of the box. It was not: their tree was present,
healthy and publishing the function somewhere better.

**Inert for 3h45m, across the whole of Session 92** — which shipped
reporting `2514 passed, 2 skipped` while the Testing row above says
nothing skips here, and which had itself filed a message about that very
move without noticing its own guard had gone quiet.

Two rules out of it. **The library is tried first**, because
`estate-lib` is an editable install and `estate.snags` resolves into
their tree with no subprocess and no venv — strictly better than what it
replaced, and the mechanism `SNAG-LOG-012`'s check already uses. Rule 8's
*"it cannot be imported"* was true when written and is why a fallback
exists, not a reason to keep preferring it. **Absence is a skip; a moved
symbol is a failure** — opposite remedies, so collapsing them is
`ports_checked`'s rule at the level of a test. An `ast` sweep pins that
exactly one `pytest.skip` remains, since a green run cannot witness a
branch it did not take. The suite reports **2532 passed, 0 skipped**.

Filed as cross-repo friction `2822dad4` with the cost stated, separately
from the two already open about the entry count, because those are about
a number and this is about a guard. No fix requested: the skip was this
repository's.

### Two corrections to this file, both found rather than reported

The sub-session block said `check-snag-claims.sh` re-measures **10**
entries and names **14** unchecked; the live figures were 12 and 12
before this sitting. Neither carries a pattern or a marker, so
`SNAG-ESTATE-012`'s class exactly and no run could have said so — the
second time this block has gone stale about the machinery it describes.
And the "Next up" line asked for `SNAG-TEST-001` through the whole of
Session 92, which closed it; that sitting left no section here either.
Both corrected above rather than quietly.

### Session 91 — the fourteenth check, and a probe that counted itself (2026-08-26)

`SNAG-LOG-012` is **checked and stays open**. Open entries **24 → 25**
(one opened), checked **11 → 12**, unchecked **13 → 13**. **2511 tests
pass** (2500 + 11). Ruff clean, mypy clean. The daemon was restarted at
**17:43:37** and `/health` answers 200 — `sysadmin/snag_claims.py` is the
only source edited and nothing under `sysadmin/` imports it, so for the
eighth sitting running nothing a caller can observe moved.

**The first check pre-staged against another repository's fix rather
than a read of their tree.** The tenth and eleventh shell into
estate-manager's venv; this one needs no cross-repo access at all,
because `estate-lib` is an **editable** install here — `strip_markdown`
resolves to a file in their working tree, so the check flips to
`mismatch` on the next run after they commit, with nothing synced and
nobody told. That is measured and put in the detail rather than assumed:
a re-pin to a wheel would show up there as a path this repository would
then lag behind.

**The obvious probe reports `match` against a function that strips
nothing.** `` '`' in strip_markdown('a `x`') `` is `True` for the identity
function, so the specimen carries four **controls** the entry itself
recorded as removed beside the two code spans. A control that survives is
`unknown` — the probe has stopped isolating the question — which is the
mixture branch one check over.

**The residue already had a name here.** The specimen carries a doubled
fence because `SNAG-DOCS-005` closed on exactly that distinction in this
same module on 2026-08-26: the naive `` `[^`]+` `` strips the single
fence and *leaks* the doubled one. Both candidate fixes are driven as
real patterns — the naive one gives `mismatch` naming the leak, the
same-length one a clean `mismatch` — and dropping the doubled fence from
the specimen breaks **both** tests, because it is the only line that
tells them apart.

**Two corrections the live run made, and one the calendar had made
quietly.** The entry says "**Both** consumers here" and there are
**three** — `monitor/health_review.py` was written on 2026-08-25, the day
*after* the entry was filed. The check's own first drive reported **five**
callers, two of them the probe itself, which inflated the count *and*
made the "nothing calls it" limb unreachable — a probe counting itself is
`ops_claims` rule 3's pin searching a region containing its own marker,
reached from the other side. And this repository's **67 entries**
went stale **52 minutes** before this commit, not over four sittings —
which is the correction this sitting had to make to itself. `estate.snags`
landed in estate-lib at **17:06:27** today, *after* Session 90's 16:14:24
commit, and the new reader counts the two `### Session NN write-up`
headings under `## Fixed Issues` that the old one did not. The first
draft said "stale for at least four sittings" on the strength of driving
**today's** reader over four of this document's past commits — which
measures the instrument and says nothing about what was published at the
time, the exact shape of error this repository files snags about. The
old reader is gone from the box (`estate_service.snags` no longer
imports), so the historical figures cannot be re-checked at all. Both new
rows are `is_open: False`, so the open count never moved and the figure
the board publishes was right throughout.

**`SNAG-TEST-001` opened**: three guards in `test_snag_claims.py` failed
once and have not failed in fifteen runs since. Both obvious causes are
excluded by reading the path — the probe is pure (fixed anchor, no
database, no unit files; `recommend` takes all three of its inputs as
arguments) and no randomising plugin is installed, so ordering is stable.
No third cause is offered, which is the entry.

### Session 90 — the thirteenth check, and the field order nobody had looked at (2026-08-26)

`SNAG-LOG-008` is **checked and stays open** — reproduced rather than
counted, because its population empties on a schedule nobody chose. The
ten rows left the current 7-day window on 2026-08-24, leave
`GET /api/logs/trends` altogether on **2026-08-31** when `previous_start`
passes them, and leave `log_entries` at 30 days' retention on
**2026-09-16**. Today the endpoint serves all ten with `change: gone`,
`current: 0`, `previous: 1`. A check that counted them would report the
entry fixed by the calendar, which is rule 1's case for the third time.

Open entries unmoved at **24**, checked **10 → 11**, unchecked **14 →
13**. **2500 tests pass** (2476 + 24). Ruff clean, mypy clean.

**The check has two halves because only one of them can move.** Half 1
drives the real `read_journal` over this daemon's own journal twice in
one process, at `text` and at `json` — the two declarations that bracket
the Session 64 deploy — and 50 of 50 enveloped records come back shaped
differently by the declaration alone. That reproduces the *cause*: a
row's `message` was settled by what `services.yaml` said when it was
ingested. It cannot refute the entry, because the remedy is a backfill
and no backfill lands in `read_journal`. Half 2 is where one would:
`unwrap_json_message` has exactly **one** production call site and it is
inside `read_journal`. A check built from the reproduction alone would be
one that can only ever say `match`.

The call-site half is settled **first**, so a box where journalctl will
not answer still reports a landed backfill rather than an `unknown` that
hides one — and the instrument reports the **enclosing function**, not a
line, because a fix that *relocated* the call to a query path leaves the
count at one and answers the entry.

#### The entry's open question is answered, and the fear it recorded lands on the other side

*"How many of the ten are recoverable is unmeasured"* — it is **10 of
10**. Every one parses out of its `raw_line` and unwraps, `logger`
recovered for all ten, stored lines **1396–1651 characters** against a
2000 cap that was never near them.

The truncation the entry feared is real and present in the same source:
`sysadmin.service` holds exactly **10 rows truncated at 2000** — and the
intersection with the ten needing a backfill is **zero**. Those are the
`SNAG-DB-005` lifespan tracebacks of 2026-08-22/23, whose `message` the
declaration already unwrapped, so they are the rows that need nothing and
could recover nothing. The anti-correlation has a mechanism — truncation
tracks record length, and the long records here are the 12.8 kB
tracebacks Session 61's level prefix made readable *after* the
declaration — but it is **a property of that ten-minute window rather
than a law**, and the entry says so: one traceback arriving inside it
would have been both unrecoverable and in need of the backfill.

#### The correction a live run had to supply

The check's first draft paired the two reads on `raw_line`, and argued
for it from the code under test: `unwrap_json_message`'s own rule 3
promises that field is kept **verbatim**, so the guarantee comes from the
thing being measured. Driven at the real journal it paired **0 of 50**.
`journalctl -o json` does not emit a record's fields in a fixed order, so
two reads of one record return two byte-different lines that parse to the
identical dict. The rule promises the record's *content* survives; the
draft read a content guarantee as an identity guarantee.

That is not only this check's problem. **A backfill keying on `raw_line`
would discover it late**, and the same field order decides whether
`__CURSOR` falls inside the 2000-character cap — which is the mechanism
behind the mosquitto case the entry already names and had not explained.
`record_identity` uses `__REALTIME_TIMESTAMP` + `MESSAGE` instead, which
also separates the eight `alert_raised` rows this daemon wrote inside
1.7 ms and a timestamp alone would fold together.

`envelope_message` is a **deliberate second implementation** of "is this
an envelope", admitted for the one reason that survives: deciding the
population with `unwrap_json_message` would make the probe agree with the
code under test by construction — `ops_claims.py` rule 3's broken pin,
one day old. It is narrowed to under-report, and a test drives both over
the shapes the real journal holds and asserts they agree.

#### The alert count fell during the sitting, with nobody doing anything

`alfred-frontend unreachable` — a `critical` open since 2026-08-25
10:45:52 — resolved by itself at **15:37:41**. That is `ops_claims.py`
rule 5's founding case arriving again: a *fall* is the signal, and the
opening block is corrected to 1 rather than left asking about a row that
closed itself.

### Session 89 — the entry closed on a run, not on the argument for it (2026-08-26)

**`SNAG-DOCS-005` is fixed and closed**, and it is the first entry this
registry has closed on a check measuring **this repository's own code** —
the two before it were delegated, and their closing move happened in a
tree nothing here watches. `sysadmin/ops_claims.py` gains
`CODE_SPAN_RE` and `read_markers` strips code spans before matching:
three lines, which is exactly what the entry's "shape of a fix" bullet
asked for. Open entries **25 → 24**, checked **11 → 10**, unchecked
unmoved at **14**. **2476 tests pass** (2484 − 14 + 6). Ruff clean, mypy
clean. estate-manager's `read_snags` reads **69 entries** either side.

**The pattern closes on a backtick run of its own length**, which is
markdown's own rule and the whole of why this closed rather than
narrowed. A span quoting a marker that itself contains backticks is
written with a doubled fence, and the naive `` `[^`]+` `` closes at the
*inner* backtick and leaves the marker bare. Both candidates were driven
through the twelfth check **before the entry was touched**: the naive one
came back `match` — *"the single fence is handled and the doubled fence
still leaks … a narrowing rather than a closure"* — and the same-length
one `mismatch`, *"candidate for closure"*. A check written the previous
sitting to tell two fixes apart did exactly that, one day later, which is
the difference between an entry closed on a measurement and one closed on
a plausible-looking diff.

**The check left the registry with its entry**, which
`test_every_checked_entry_is_open` makes a rule rather than a choice — a
refuted check on a closed entry says "go and judge this" for ever.
`check_quoted_marker_reads_as_real`, `ops_probe`,
`survey_quoted_markers`, `MarkerSurvey`, `QuotedMarker`, `_quoted_only`
and the six `OPS_PROBE_*` constants went with it, as
`handoff_apology_published`'s helpers did the sitting before. The last
measurement the survey ever took is recorded on the entry rather than
lost: **9** markers in the printed region with **0** quoted, **4** quoted
outside it, the nearest **76** lines past the region's end and naming the
retired `handoff_apology_published`. Session 88 measured that margin at
**9** lines; it was 76 the next afternoon. A number that never stops
moving was never a property of the document, which is what that entry's
correction was about.

**What replaced the check is a pin, not a gap.**
`snag_claims.strip_code_spans` is still a copy rather than an import —
two composition roots must not couple to share a regex, and a snag-list
parse must not move because the dashboard's reader was edited — so
`TestAQuotedMarkerIsAQuotation::test_the_sibling_s_copy_and_this_one_agree_shape_for_shape`
drives both over seven shapes and asserts they agree character for
character. Import where you can, pin where you cannot.

**The reason for keeping the copy was corrected mid-sitting, which is
worth recording because the first version was better and wrong.** The
draft argued that `survey_quoted_markers` measures this module *with its
own copy*, so sharing would make the survey read the fix by definition —
a check agreeing with itself. True when written, and the same sitting
deleted that survey forty minutes later as part of the closure. An
argument resting on machinery the same change removes is not an argument;
what survives is the coupling one the entry filed on 2026-08-25.

**The block now writes the sentence it could not write.** *"One thing
this block deliberately does not do: quote a marker"* is gone, replaced
by a paragraph that quotes one inside a code span beside a real marker.
`check-ops-claims.sh` reports **no** `marker:` finding for it and **no**
unclaimed figure, so the fix is asserted by the artefact the entry was
about and not only by tests. A regression in `read_markers` turns that
sentence into a spurious finding at the top of the next sitting, which is
the loud direction.

**One thing found rather than fixed**: the daemon had already been
restarted at **14:48:31** by a party outside this sitting — a clean
`Stopping` → `Deactivated successfully` → `Started`, not a crash — so the
block's start time was stale before the first edit was made.
`check_daemon_start`'s note says *"nothing recorded why"*; this does.

### Session 88 — the twelfth check, and the entry that was paying its own cost (2026-08-26)

**`SNAG-DOCS-005` names a check now**, and it is the first in the
registry whose subject is this repository's *other* claims-checker.
`sysadmin/snag_claims.py` gains `check_quoted_marker_reads_as_real`,
`ops_probe`, `survey_quoted_markers` and `MarkerSurvey`. Checked entries
go **10 → 11** and unchecked **15 → 14**; all eleven still hold.
**2484 tests pass** (2470 + 14). Ruff clean, mypy clean.
estate-manager's `read_snags` reads **69 entries and 25 open** either
side of the edit.

**The mechanism is local and was reproduced rather than reasoned about.**
`ops_claims.read_markers` matches its own syntax over the flattened
region with no regard for code spans, so the check builds a `STATUS.md`
in miniature and drives the real `printed_region` → `read_markers` →
`check_markers` over it. Three shapes, because the defect is quiet in
three ways: a quoted key nothing implements **invents** a broken-marker
finding, a quoted key that *is* implemented **silences** the
unclaimed-figure finding beside it — opposite in sign, which is what the
entry means by quiet in both directions — and the same quotation inside
a **doubled fence**. A control region runs first, since a finding's
absence is only evidence once its presence has been observed.

**The third shape earned its place by measurement, not by argument.**
Both obvious three-line fixes pass the single fence; only a code-span
pattern closing on a backtick run of the *same length* survives the
doubled one, which is the shape `SNAG-DOCS-005`'s own body carries.
Driven: the naive alternative closes at the inner backtick and leaves the
marker bare, so a probe testing one fence would report that fix a **clean
closure**. Hence the verdict asymmetry — a partial fix is `match` with a
narrowing note, never `mismatch`, because an entry is refuted when the
defect is gone rather than when some of it is.

**The entry's account of its own empty population was wrong in the
interesting direction, and the block said so all along.** The entry reads
the emptiness as a property of how the block is written. The block reads
*"One thing this block deliberately does not do: quote a marker"*, names
this entry, and sends the reader to `sysadmin/ops_claims.py` — so the
cost the entry files as a future sitting's confusion is **already being
paid**, as a sentence the dashboard cannot write. The first correction
drafted here said the entry's reason was simply not the reason; reading
the block refuted that before it shipped, which is
`verify-ops-claims-live` applied to a document rather than to the box.

**Nine lines is the margin, and it names a retired check.** Beyond the
block the printed region runs to 270 lines and its far end is empty only
by placement: the nearest quoted marker sat **9 lines** past the last
line, naming the check Session 87 correctly removed with
`SNAG-ROADMAP-001` that morning. So the *inventing* direction has a live
member nine lines outside the region, and a `## ` heading added above it
would close that margin with nobody intending to. The figure is recorded
as history, not restated as a claim: this very section pushed it further
out within the hour, and the check prints the live distance on every run.

**Four falsifications were driven and every one fired**: a set-difference
`_quoted_only`, the doubled-fence probe removed, and the survey's
stripper disabled on each of its two halves. One guard is stated as a
blind spot instead — `test_the_live_region_carries_no_quoted_marker`
asserts nothing is quoted in the region, which a broken stripper also
produces, so the falsifiable half is built rather than live and its
docstring says which.

**Session 87 wrote no section here**, which is why this one sits directly
above Session 86's. Its record is `b454a50`, `HANDOFF.md` and the block
above; nothing is missing but the heading, and authoring another
sitting's entry retrospectively is not this one's to do.

### Session 86 — the tenth check, and the first that had to run another repository's code (2026-08-25)

**`SNAG-ROADMAP-001` names a check now, and it is the first in the
registry to report *refuted* on the day it was written.**
`sysadmin/snag_claims.py` gains `check_handoff_apology_published`,
`hook_apology`, `estate_probe` and `estate_module_state`; the entry's
body carries `<!--check:handoff_apology_published-->`. Checked entries go
**9 → 10** and unchecked **17 → 16**; nine of the ten still hold, and
estate-manager's `read_snags` reads **69 entries and 26 open either side
of the edit** on an unchanged open set.

**The question the handoff posed was settled by rule 5 rather than by a
new verdict.** It asked whether a check that skips when estate-manager's
venv is absent is a check at all or a fourth way of reporting `unknown`.
It is neither: it is the **third** verdict, used for what it was defined
for. A test may `skip` — `TestAgainstTheOwningParser` does, because it
asserts two readers agree and has nothing to assert with one absent — but
a check *reports on a claim*, and "nobody managed to test it" is a
verdict this module already imports wholesale from `schema_guard`. No
checkout, no venv, a renamed symbol and a tree caught mid-edit are all
`unknown` with the reason named.

**That was not a hypothetical, and the box answered it inside the
hour.** estate-manager had an uncommitted edit in flight in the exact
file — `roadmap.py` modified at 22:34, under their own
`SNAG-ESTATE-056` — so the same module was measured twice four minutes
apart and came back as two different modules, the second refusing to
import. Their fix is precisely this entry's proposed remedy:
`_first_meaningful` becomes `_meaningful_lines` yielding
`(marked, cleaned)`, and `next_action_from_handoff` tests
`is_placeholder(marked)`.

Five things settled by driving the producer rather than reading it:

1. **All three verdicts are real and were driven at three real states of
   their tree**, never at fixtures alone: their committed `roadmap.py`
   gives **match** and reproduces Session 82's reading exactly
   (`is_placeholder(raw)` **True**, the producer returns the apology);
   their working tree gives **mismatch** with `next_action_from_handoff`
   returning `None`; a box with no venv gives **unknown**.
2. **The falsification caught a defect in the check itself, and it was
   the shape of the bug the check measures.** The first draft called
   `roadmap._first_meaningful` to evidence the strip — a **private helper
   whose name is what their fix renames** — so driven at the real fix it
   reported `unknown` and would have gone on reporting it for ever,
   structurally unable to witness the closure it exists to notice. The
   repair states the mechanism more sharply than the entry ever did:
   `is_placeholder` says placeholder and the producer publishes it
   anyway, which touches no private symbol and survives any rename.
   `test_the_probe_touches_nothing_private` is the guard, and nothing
   else would have caught it coming back — the stub defines only public
   names, so a probe reaching for a private one fails identically against
   every fixture and reads as an environment problem.
3. **The obvious wider reading would already have reported this
   refuted.** `looks_like_no_action` exists in that module today, matches
   this exact wording, and is wired into `/next` — but **not** into
   `briefing._next_action_rows`, which is the surface the entry names. A
   check asking *does any guard reject this line* answers "yes" while the
   producer goes on returning it: rule 1's trap in a new dress, measuring
   that a remedy **exists** rather than that the fault is **gone**.
4. **The verdict alone is not enough to act on**, so
   `estate_module_state()` names whether the measurement was taken
   against a released fix or an edit in flight — opposite remedies, close
   versus wait. `ports_checked`'s rule applied to somebody else's
   repository, and needed within the hour of being written.
5. **The probe is read from the hook, never typed into the module.** The
   entry's impact turns on the wording being emitted by a hook this box
   controls, so a literal here would go on measuring a sentence nothing
   writes — `check_capped_signature_collides`' derived-probe rule, from a
   second direction.

**The entry stays open, and that is rule 2 rather than caution.** A
refuted claim is a candidate for closure and never a closure; the fix is
uncommitted, and the daemon on 8400 serves start-time code. The trigger
for the next sitting is mechanical: when the evidence line stops saying
"uncommitted", close it.

Eight tests added (**2457 → 2465**), each falsified against the behaviour
it replaces — including one that had to be falsified *twice*, since
narrowing the comparison to the marked form is a different defect from
losing the `None` branch.

### Session 85 — the ninth check, and the entry the mechanism rule was written for (2026-08-25)

**`SNAG-LOG-013` names a check now, and it is rule 1's second case.**
`sysadmin/snag_claims.py` gains `check_capped_signature_collides`; the
entry's body carries `<!--check:capped_signature_collides-->`. Checked
entries go **8 → 9** and unchecked **18 → 17**; all nine still hold, and
estate-manager's `read_snags` reads **69 entries and 26 open either side
of the edit**, so the marker moved nothing the board publishes.
**2457 tests pass** (2449 + 8). Ruff clean, mypy clean. The daemon was
restarted at **22:14:04** and `/health` answers 200.

- **The population was the trap, and this is the entry the trap was named
  after.** `SNAG-LOG-013`'s own last bullet says its ten raw-JSON rows
  left the seven-day `current` window the afternoon it was filed, and
  Session 82 measured that population **empty** and kept the entry open.
  So the check never asks *does any pair collide today* — it drives the
  real `recommend()` over two signatures built to agree past the cap.
  `check_dropin_blind_spot`'s treatment, applied to the entry that
  taught it.
- **The probe's shared prefix is derived from `SIGNATURE_DETAIL_CHARS`,
  and that is the design's load-bearing line.** The entry argues in
  writing that raising the cap is *not* the fix — any bound is defeated
  by two records that differ past it. A hard-coded prefix would
  therefore report a fix the day somebody moved the constant to 400,
  which is the check arguing against the entry it measures. Falsified
  exactly that way: pinning the prefix at 240 breaks two of the eight
  new tests, and at `SIGNATURE_DETAIL_CHARS = 400` the derived probe
  still reports *still holds* over a 540-character agreement.
- **Two halves, because the entry's title is a conjunction** — capping
  *can* put two rows back where `SNAG-LOG-010` found them, and inside one
  roll-up it *already has*. The check drives the pair twice: inside
  `INCIDENT_WINDOW_SECONDS`, where the roll-up's own member lines are
  compared, and outside it, where two rows' titles are.
- **The halves are not independent in one direction, and the direction
  that separates them is the entry's own fix.** `quoted_signature`
  delegates to `capped_signature`, so a fix to the shared function closes
  both and the note says so rather than naming a half. What separates
  them is capping *from where the group's members diverge* — which needs
  the sibling set and so cannot live in the per-row pure function the
  titles are built from, which is precisely the entry's second candidate
  fix. That is the only reason reporting the halves apart is worth the
  code, and it is a test.
- **The first draft of the second half was a false negative, and it
  shipped green in the scratch run.** It used two *different* sources, so
  the two titles came apart — `_new_recommendation` opens a title with the
  source name — and the probe reported the claim refuted for a reason with
  nothing to do with the cap. A fixture that moves two things at once
  cannot say which one it measured. The repaired test now drives both
  fixtures and asserts the difference is the fixture.
- **Removing the cap altogether is `unknown`, never `mismatch`.** With
  `capped_signature` a no-op the two signatures render apart, and not
  because anything learned to tell them apart — the mechanism under test
  is simply gone. Falsified by deleting the guard clause, which turns
  that input into a reported fix.
- **What the check cannot reach is stated rather than implied.** The
  entry's *first* candidate fix — making the signature readable at the
  producer, which is `SNAG-LOG-008` — removes the population and leaves
  the mechanism exactly as it is, so this check would go on reporting
  *still holds*. That is rule 1 rather than a gap, and it is why the live
  table is deliberately not consulted here at all: a database read would
  make the check `unknown` whenever PostgreSQL is down, for a claim that
  has nothing to do with the database.
- **A cross-repo slip, recorded rather than quietly undone.** A `git
  stash` intended for this repository ran in `~/projects/estate-manager`
  because a compound command left the shell in their tree, and stashed
  three uncommitted files (an ADR and two roadmap documents). Popped
  within the minute and their tree verified back to the same three
  modifications — but another session may share that tree, and the
  lesson is the one already recorded for commits: address another
  repository by absolute path, never by leaving `cd` behind.

### Session 84 — `snag_list.md` gets the reader `STATUS.md` has (2026-08-25)

**The document that sets the agenda had never been checked.** Session 82
measured all thirty open entries by hand and found **five dead on the
box** — three of them `P1`, three fixed for between nine and thirteen
days. That is `SNAG-ESTATE-008` one document over and at five times the
size, and a hand sweep is stale the moment the next fix lands.
`sysadmin/snag_claims.py` is the fifth composition root; an entry names
the check that would refute it, in its **body**, and
`sysadmin-check-snags` runs it at the top and the close of every sitting.
Eight of the twenty-six open entries are checked and all eight still
hold; the other eighteen are named and counted, which is
`SNAG-ESTATE-014`.

**A check tests the entry's *mechanism*, never its *population*** —
Session 83's rule read as an instruction to the author, and the
difference between a useful sweep and one that closes the wrong entries.
`SNAG-UNITS-006`'s population is measured empty (zero of the 38 swept
units carries a drop-in), so a population check refutes it on the day it
was filed, which is exactly the reading Session 83 refused for
`SNAG-LOG-013`. `check_dropin_blind_spot` **builds** a unit with an
overriding `RestartSec=`, sweeps it and compares — reproduced rather than
counted.

**The instrument decides more than the rule.** `grep review_hour` matches
`log_review_hour`, `disk_review_hour` and `health_review_hour`, all three
read, so a grep-shaped check reports `SNAG-CFG-002` refuted on its first
run; `ast.Attribute.attr` is the exact segment and matches none. The
falsification points the same walk at `log_review_hour` deliberately,
where it finds the two real readers. Third time a substring has stood in
for a measurement here.

**Three defects only the live run gave.** The first run reported two
checks nobody implements — `helth` and `routes`, both "named by
`SNAG-ESTATE-011`", an entry that merely **quotes** them. This document
family is the one place on the box that writes *about* markers, so a
marker with no way to be quoted cannot be used in it; `SNAG-DOCS-005` is
`ops_claims`' latent copy of the same hazard, measured empty. Then the
doubled fence, which markdown's own same-length rule fixes. And the entry
filed for the unchecked residue was first written with a marker meaning
"there is no check", which the machinery refused within a minute — a
marker names a check, and an absence is not one.

**The sitting's own defect.** The board pin was first written `assert
theirs["total"] == 67`, a measured figure inside a test, stale the moment
this sitting filed two entries — `SNAG-ESTATE-008`'s shape arriving
inside the guard built to answer it. What is pinned now is the agreement
between two readers.

**Cross-repo message `3986f323`**: `read_snags` lives in
`estate_service` rather than `estate-lib`, so its closure rule is written
a second time here — narrowed to under-report closure, and pinned against
the owner by a test that skips when their venv is absent.

### Session 83 — the call Session 82 deferred, and the rule that decides it (2026-08-25)

**`SNAG-ESTATE-008` is closed, and it is closed on its own residue rather
than on its chain.** Session 82 measured thirty entries and left this one
deliberately, because its narrow half was fixed by Session 73, its general
case became `SNAG-ESTATE-011` (fixed by Session 76), and what remains of
*that* is `SNAG-ESTATE-012` — filed and open. Parser reads **25 → 24
open**, entries unmoved at **67**.

**The rule the sweep needed and did not have: an empty *residue* is a
closure, an empty *population* is not.** `SNAG-LOG-013` stays open on an
empty population, because its claim holds again the moment the population
refills. A residue cannot refill. So **closing a chain is not a closure** —
what closes an entry is having nothing left that it *uniquely* names and
nothing owns.

**The test is the entry's own three founding instances, driven live rather
than read off the docstrings.** Backdating the block's restart to
`2026-08-22 09:00:00` makes `check_daemon_start` fire; raising `holds
**2**` to `**9**` makes `check_alerts` fire with a note that **ends
`(SNAG-ESTATE-008's founding case)`** — the running code cites the entry it
closes. The third instance, the five orphan removals, is genuinely
uncovered: `measure_unit(unit: str = OWN_UNIT)` has **one** caller and it
passes the default, so no arbitrary unit is ever resolved. But that
sentence carries no figure and no marker, which is `SNAG-ESTATE-012`'s
symptom verbatim — so the residue has an owner and a narrower statement.

**Leaving it open had become an instance of itself.** The `P2` was kept for
the cost of *"sittings of ranking attention spent on settled items at the
top of the document that sets the agenda"*; named by eight consecutive
rankings with nothing of its own to do, it was paying that cost, and
ranking its own residue two rungs louder than `SNAG-ESTATE-012` ranks it.

**And the block demonstrated the residue while the entry was being
closed.** The sub-session header still read *"Owed … Named as the blocker
in seven consecutive rankings without being asked"* for the Session 33
question, which had been filed as message `6a330427` earlier the same day
and was already recorded as asked twice further down the same document.
One block, one fact, two ways, with the stale half the one
`claude-preflight.sh` prints first — and no pattern reaches it, because the
sentence carries no figure and no marker. Corrected by hand, which is what
ESTATE-012 says this class costs.

**No code changed**, so no restart is owed and no test was added.

### Session 82 — the closure-marker sweep: five entries dead on the box, and no P1 left (2026-08-25)

**The estate board was publishing three P1s and two P2s for this
repository that do not exist.** All 30 open entries were measured
against the box, not read: `SNAG-AGENT-003` (**45** file-organiser runs,
latest 16:22:03, against *"once in its life"*), `SNAG-AGENT-004` (**2**
unresolved alert rows against **26,270**, with `redis unreachable` at
2,017 rows / 0 open and `Critical disk usage on /` at 13,968 / 0),
`SNAG-ESTATE-001` (**0** `personalassistant*` unit files in either unit
directory), `SNAG-DB-002` (**11 of 12** databases at 2.44 = 2.44, the
twelfth `template0` with no recorded version and excluded by the check's
own non-NULL rule — **0 stale**) and `SNAG-PROJ-013` (ImbaBots heads
`# Handoff — 2026-08-24`). The live parser reads **30 → 25 open** with
the entry count unmoved at **67**, and **no P1 is published for this
repository for the first time**. Three of the five had been fixed for
between nine and thirteen days.

**The predictor that ranked this sitting was wrong, and the sweep came
out at exactly the number it called a floor.** Session 81 reasoned that
twelve of thirty bodies mention a fix, so five must be a floor.
Measured: **14** bodies mention one and **eight of the fourteen are
alive**, because this repository's convention is that a new entry is
*named by the fix that created it* — so a fix-word in a body usually
points at the entry's **parent**. Grepping for the word answers "does
this entry discuss a fix"; only the box answers whether *this* entry's
claim still holds. Second time a ranking here has been built on a grep
answering the adjacent question (`SNAG-DOCS-002` was the first).

**Three entries were re-measured and stay open, which is what makes the
five worth anything.** `SNAG-SYSD-003` holds as written
(`ollama.service` is `LoadState=not-found` and still in
`sysadmin.service`'s `After=`). `SNAG-ROADMAP-001` was **reproduced**,
and the reproduction refutes its own stated cause — the detector *is*
wired into the "next" heading path now and **cannot fire**, because
`_first_meaningful` strips the italics `is_placeholder` keys on before
testing (`is_placeholder(raw)` **True**, `is_placeholder(naked)`
**False**); the module is estate-manager's since ADR-0005, so it was
**filed** to their register as message `e0461fe9` rather than fixed
here. And `SNAG-LOG-013`'s population is **empty** at the live endpoint
and it **stays open**, because "population is currently zero" is exactly
what mis-ranked its parent `SNAG-LOG-010`.

`SNAG-DB-002` is the mechanical note worth keeping: it carried **three**
closure statements in its title and read open, because `read_snags`
needs a done word at the **start** of a clause and `check half **fixed
2026-08-13**` starts with "check". It is the named example in the
parser's own docstring — documented drift, not a parser defect.

### Session 81 — SNAG-DOCS-004, the rule three modules state and the three ways it was written (2026-08-25)

**Two docstrings claimed their prompt "contains no digit by
construction" and both prompts contain `1`, `2`, `3` and `150`.** The
behaviour was right and the sentence was not: rule 2 was always about
the *data* half, and the section numbers and word cap in each module's
own `REVIEW_INSTRUCTIONS` are instructions to the model rather than
measurements about the box. `log_review` and `files.review` now state
the narrow claim and name the half they do not cover; `health_review`'s
was reworded too, because it carried a present-tense description of the
siblings' defect that would have gone stale the moment the defect did.

**The entry asked for *the* partition helper to be shared, and there
was no such thing.** The rule was written three times and the three had
diverged, in two places, each with a right side:

| | strips API paths | asserts the boundary was found |
|---|---|---|
| `test_disk_review._data_lines` | ✅ | ❌ |
| `test_log_review._data_lines` | ✅ | ❌ |
| `test_health_review._data_half` | ❌ | ✅ |

So `tests/review_prompts.py` is the **union**, not any one of them —
deduplicating onto whichever copy a reader opened first would have
silently dropped a live guard. Two things it settled:

- **The API-path strip is a no-op today and is kept as policy.**
  Measured across all three live fixtures: exactly one data half
  contains an API path at all (`POST /api/files/clean/downloads`) and it
  is digit-free. It earns its place the day a route is versioned.
- **`split(instructions)[0]` was not a false green**, and saying so is
  the point. With no instruction block there are no instruction digits
  to exclude, so the digit test passes for a *stricter* reason. What it
  did was return the whole prompt while being called "the facts half" —
  `ports_checked`'s rule one directory over.

**Nine tests exist so the shared assertion can be seen to fail**, one
per rule plus two boundary cases, each driven at something that must
break it before it was written down. A shared guard that never refuses
anything is worth less than the three copies it replaced, because a copy
at least had a reader.

**One correction the sitting made to itself, and it is this entry's own
defect in miniature.** The note explaining why the strip is left greedy
first read *"no route on this service takes a query string"*, written
from plausibility. One `grep Query(` refuted it — `/api/logs/recent`
alone takes five. The note now states what was measured: the executors
that reach a prompt are hand-written literals in
`files/recommendations.py`, every one a bare path followed by a space.
`CLAUDE.md` carried the wider claim too and was corrected in the same
sitting.

Suite **2388 → 2398**, routes unmoved at 51, head unmoved at 016.

### Session 80 — SNAG-API-004, one classification of a column read four ways (2026-08-25)

**`status != "ok"` was written in four readers and was wrong in three of
them**, from the day migration 009 added `skipped` to
`chk_health_status`. The snag named one route and recommended an audit;
the audit is what mattered, because the population was **three** and two
of them had never been counted.

- `GET /api/sysadmin/status` — the route the entry names
- `GET /api/summary` — the identical `!= "ok"`, never named by anyone
- `GET /api/projects/managed` — **the sharpest, and the only one not
  masked**. Measured 2026-08-25, it reported `venture-assistant` and
  `sysadmin_assistant` unhealthy with every real service `ok`, because
  each has one `monitor: false` service beside its live ones. The other
  two were false-for-the-right-reason on the day the entry was written

**The vocabulary has one statement now, beside the constraint that
defines it.** `STATUS_READINGS` on `models/service_health.py` classifies
all seven admitted values as `well`/`fault`/`unwatched`, read through
`is_fault()` and `is_unwatched()`; `tests/test_service_health_status.py`
asserts it is **exactly total** over the constraint's own `sqltext`,
parsed out rather than re-typed. `briefing/data.py`, which fixed this
locally on 2026-08-07 and wrote down why, now asks the owner instead of
restating the rule; `monitor/services.py` re-exports `SKIPPED` rather
than typing the literal a fifth time.

**`reliability.py` is pinned rather than imported** — its docstring
promises purity and the owner is an ORM model, so a test drives both
sides against the constraint (`syslog_priority` against
`journal.PRIORITY_MAP`). It also stopped negating `ok`: `DOWN_STATUSES`
names the four measured faults positively, which changes no number today
and changes the failure mode.

**Verified live, and the counterfactual is what proves it.**
`/api/sysadmin/status` still reads `False` and correctly —
`alfred-frontend` is genuinely unreachable, which is the masking the
entry describes — so it was driven over the live rows with that one
service removed: old `False`, new `True`, across 29 services of which 3
are declared. Over real HTTP after the restart, `/api/projects/managed`
moved two projects `False` → `True` with their `skipped` rows still in
the grid.

**Two things worth carrying.** The suite was green either side of all
three defects, so the wrong flags were untestable by omission — the
tests covered a healthy box and an unhealthy one and never a healthy box
with a declaration on it, and `/api/projects/managed` had no test at
all. And one falsification **passed against deliberately broken code**:
`assert SERVICES_SKIPPED is SKIPPED` is True whether the literal is
re-exported or retyped, because CPython interns short strings — a guard
asserting a *value* where it means *provenance*, for the third time
here, now an AST check.

### Session 79 — the fourth Tier 3, and the delta it reports was nearly the wrong number (2026-08-25)

**Session 25's Tier 3 shipped as `GET /api/sysadmin/review`**, completing
Session 25 two and a half weeks after Tier 1.
`sysadmin/monitor/health_review.py` + `health_reviews` (migration 016) +
`HealthReviewResponse` + a Monday 05:00 job + a "Weekly System Health
Review" briefing section. Suite **2,299 → 2,362**, ruff and mypy clean,
routes **49 → 51**, head **015 → 016**. All four named inputs built:
flappiest services, alert volume delta, anomaly summary, resource trend
direction.

- **The alert delta counts distinct titles, and the row count would have
  been the most misleading figure this review could publish.** Across
  the two live comparison windows the `alerts` table holds **24 rows
  against 59,650** — a 2,485x fall — of which **59,200 share a single
  title** and fell on one day. The same windows hold **17 distinct
  titles against 39**. This repository has written down four times that
  the table records one row *per failed check* rather than one per
  incident and had never applied it to a *count* of alerts, because
  nothing counted them. Rows are kept in `stats` as evidence and never
  phrased.
- **A fall is refused when the monitor's own coverage fell.**
  `log_review.direction_phrase`'s asymmetry against a different
  mechanism: there a truncated read drops entries, here a monitor that
  was not running records none, and both can hide a fault and never
  invent one. The two windows were observed at **17.01 %** and
  **96.33 %** of expected agent runs, so this is load-bearing rather
  than theoretical. Both windows are measured, because checking only the
  current one reports poor coverage and still lets every delta through
  unqualified.
- **Two defects only the live LLM run found, both fixed and re-verified
  live.** Handed "The monitor was down for much of this period",
  dria-agent-a-3b published **"The machine was down for much of the
  week"** — an outage report about a box that was merely unwatched. And
  it opened with a conversational preamble that `strip_markdown` would
  not have removed, since that function strips formatting rather than
  prose. Naming the *monitoring service* and denying the inference in
  the next clause fixed the first; one clause in the instructions fixed
  the second; the re-run produced neither.
- **A third defect the fixtures could not have caught.** The prompt's
  first draft named only `unreliable`/`failing` services and fell back
  to the whole list when there were none — so it dropped `searxng` and
  `alfred-frontend`, both degraded with real outages, at the exact
  moment `venture-chat` went unreliable. Replaced by naming every
  service that dropped out and letting the grade rank them.
- **Disk is deferred to the disk review by name.** `GET /api/files/review`
  narrates occupancy into the same 06:00 briefing, so this narrates CPU,
  RAM, swap and load — which nothing else on this box narrates — and the
  fallback digest points at the review that does cover disk.
- **The route is under `/api/sysadmin` rather than `/api/services`**, the
  one departure from the three siblings' naming. `/api/services` promises
  no non-GET route beneath it and a test asserts it; a
  `POST .../review/generate` there could only ship by narrowing that
  guard to admit the route being added.
- **Nine falsifications driven, and one guard passed against the code it
  was written to break** — it asserted a string absent from both the
  pre-fix and the fixed wording, testing the model's output through a
  fixture that never contains it. Session 78's `waived`/cadence shape a
  third time; repaired to assert the property that actually
  distinguishes the two.
- **Three snags opened, two of them found while not building.**
  `SNAG-API-004` came out of *pricing the next session's recommendation*
  — `GET /api/sysadmin/status` reads `all_healthy = all(status == "ok")`,
  which is the `skipped` defect's **third** instance in one column.
  `SNAG-CFG-002` came out of looking for a free Monday slot.
  `SNAG-DOCS-004` came from printing the digits in a prompt rather than
  reading the docstring describing it.

### Session 78 — the fourth advice endpoint, and the score it consumes was wrong (2026-08-25)

**Session 25's Tier 2 shipped as `GET /api/services/actions`**, the
missing sibling of `/api/files/actions`, `/api/logs/actions` and
`/api/units/actions`. `sysadmin/monitor/service_recommendations.py` is
the pure module; `ServiceRecommendationInfo` is its own model rather than
a reuse of the `RecommendationInfo` Session 77 deleted the day before.
Suite **2,238 → 2,299**, ruff and mypy clean, routes **48 → 49**, head
**014 → 015**.

- **The endpoint found a defect in the scorer it reads, and it was 60
  points a service.** `services.yaml` declares `monitor: false` on three
  services that are inactive by design — `venture-chat-large` (pulled up
  by `venture-enrich-nightly` for the 02:00 drain and stopped by its
  `ExecStopPost`), `sysadmin-tray` and `searxng-upstream` — and the agent
  writes those checks as `skipped`. `score_service` excluded only
  `error` from its rates, so a `skipped` row counted as
  measured-and-not-`ok`: **all three scored 35 and graded `failing` off
  307 checks nobody had taken.** Live before and after: **6 rows / 213
  points → 3 rows / 33 points**, `failing` 3 → 0, mean score 92.1 → 98.6.
- **It survived from Session 25 because a wrong score is a number on a
  page.** Tier 2 turned each into a `risk` recommendation, which is what
  made it loud enough to find — and 180 of the endpoint's 213 headline
  points were fabricated, all three of its `risk` rows among them.
- **Neither obvious reading was right, and the sibling rule does not
  transfer.** `_resolve_recovered` treats `skipped` as *healthy*,
  correctly, because an open critical nobody will look at again is a
  pile-up wearing a declaration as an excuse — but that decides whether
  to close an alert, and importing it here fabricates a **100** exactly
  as scoring it down fabricated a **35**. `skipped` joins `error` in the
  unmeasured set and `confidence` carries the truth: `ports_checked`'s
  rule, zero-because-blind never served as zero-because-clean. Counted
  apart from `error_checks` because "the check failed" and "nobody
  looked, by choice" are different claims — `UnitFinding.enabled`'s trap,
  paid for once already.
- **The whole suite passed either side of that fix**, which is the part
  worth carrying: nothing pinned the behaviour in *either* direction, so
  a wrong score was not merely undetected, it was untestable-by-omission.
  Six tests now cover it and all six were falsified — one of them twice,
  because the episode-count assertion passes against the broken scorer
  for the wrong reason (a `skipped` row also failed to split an episode,
  by counting as *down*).
- **The confidence gate is asymmetric or the endpoint ships empty.** All
  30 services read `confidence: low` on the build day — the box was off
  08-18 → 08-22 and `SNAG-DB-005` killed the daemon a further 22 h on
  08-23, leaving `observed_days: 1.07` at `coverage_percent: 15.13`. A
  `confidence == "high"` gate is the obvious implementation and is
  `SNAG-LOG-002`'s measured-empty population for the **third** time.
  What rescues it is that a gap is one-directional — it can hide an
  outage and never invent one — so `outage`/`flapping`/`timer_failed`
  are floors and survive it, while `check_interval`/`timer_stale` argue
  from a rate or an absence and do not. Driven as a counterfactual
  against the live population: 7 rows / 1 suppressed at low confidence,
  8 / 0 with confidence forced high.
- **Timer staleness parses no clock, and the obvious approach rebuilds
  `SNAG-LOG-009`.** `details['last_run']` is `LastTriggerUSec` rendered
  as a local wall clock with a zone abbreviation. The token is treated
  as **opaque** and compared only for inequality, with `checked_at` as
  the clock — which derives **24.0 h** for all five daily timers live,
  `alfred-evaluate-timer` included despite 15 holes in its series. Both
  weekly timers correctly derive `None` at 2 firings each, and
  `timer_lookback_days` is 30 rather than the 7-day scoring window
  precisely because 7 days cannot hold a weekly cadence.
- **Two of eight guards passed against deliberately broken code**, both
  the failure the `falsify-guards-in-both-directions` memory names: the
  `waived` test set `muted=True` so the muted skip returned first, and
  the cadence test passed one firing where it claimed two. Both
  repaired, plus an invariant test pinning `reliability._deductions`'
  `waived=muted` at its owner, since this module leans on it.
- **`tasks.md`'s two scoped examples were built as written, at the
  owner's direction, with both conflicts filed rather than decided** —
  `SNAG-SVC-001` (advising a longer check interval is advising that a
  fault be seen less often, `known_noise` rule 3's opposite) and
  `SNAG-SVC-002` (`timer_stale` asks `stalls.py`'s question about a
  different subject, with no ladder and no cross-reference).
- **A module rename the test namespace forced.** `service_actions` was
  the first choice, by `log_actions`' convention — and
  `tests/test_service_actions.py` has covered `POST
  /api/sysadmin/services/{name}/{action}` since the tray's Phase 3.
  "Service action" already meant start/stop/restart here. Two of the
  three siblings are named `recommendations` anyway, so the name that
  avoids the collision is also the commoner one; only the module moved,
  the route keeps `/actions`.
- **`SNAG-ROADMAP-002` closed, by the owner, mid-sitting.**
  estate-manager fixed it at **09:12:22** as their `SNAG-ESTATE-048` —
  `read_snags` now reads an entry's own closure marker — and it was
  verified here by driving the new parser rather than by being told. The
  open count for `snag_list.md` drops **59 → 27** on an unchanged
  document. Nine sittings of owed report retired without being written.

### Session 77 — the registry describes only what it serves (2026-08-25)

**`SNAG-DOCS-002` fixed, and the entry was wrong a third time in a third
direction.** `contracts.py` carried eight project response models for
routes that left on 2026-08-13 (ADR-0005). It had been measured twice,
both times with a grep for the model's name — which answers "does
anything mention this", and that is not the question. The property is
**reachability from a reader**, and computing it moves the count in both
directions at once. **15** classes were unreachable, not eight: the 8
responses plus exactly their 7 exclusive members, sitting in two
contiguous regions. 83 classes → 68, 1,846 lines → 1,460. Suite **2229 →
2238**, ruff and mypy clean, restarted and verified live.

- **17 models have no mention anywhere and are load-bearing.** `RamInfo`
  is a field of `ResourceResponse`; nothing outside the file names it. A
  grep reports 32 models with no external reader and more than half are
  that shape. Session 76 put `ProjectHealthInfo` in the dead set on
  exactly that evidence — it is a field of `ManagedProjectInfo`, the
  `response_model` of the one `/api/projects` route this service still
  serves. In the other direction, `RecommendationInfo` looked alive off a
  single line of *prose* in `units/recommendations.py`.
- **A root is a name used, never a name imported** — the distinction
  Session 58 stated in prose ("a name in an import list and not a
  caller") and then measured with a tool that cannot draw it. So the
  detector is an **AST walk**: skipping `ast.Import`/`ast.ImportFrom`
  draws it exactly, docstrings are `ast.Constant` and fall out for free
  needing no prose heuristic, and `response_model=` needs no special case
  because it is already an `ast.Name` in a keyword — no second statement
  of one fact.
- **Five names left the registry without leaving the wheel.**
  `sysadmin_tray` ships in it, so removing a name from
  `sysadmin_tray/models.py` is a change to a published surface. They live
  in `_deprecated_contracts.py` behind a PEP 562 module `__getattr__`
  that warns on **access**, never at import — warning at import fires on
  every tray start whether or not anything touched a deprecated name,
  which teaches the reader to filter the category rather than act on it.
  The set is closed under its own field references, so the move cannot
  strand a served payload, and a test asserts that rather than a
  docstring claiming it.
- **Falsified at the real pre-fix file, which is the only way the guard's
  blind spot was visible.** A fresh unreachable model is reported
  exactly. Driven at the pre-fix registry the walker reports **12** of the
  15: `tests` is a consumer package on purpose, so the shim's own
  annotations and `models.PortfolioActionsResponse` in the new test make
  three of them roots. Those three are covered by
  `test_none_of_them_are_defined_in_contracts` instead — two tests
  composing rather than one doing both. The synthetic falsification
  passes cleanly and would have shipped the gap unseen.
- **Two costs filed rather than implied.** `SNAG-DOCS-003`: the five
  deprecated names are removable only once someone confirms nothing
  outside this repository imports them — an operational fact, not a code
  question. `SNAG-ESTATE-013`: found by **running** the sitting's opening
  check rather than reading it. `check:expires` takes a naive instant,
  the block copied `03:32` off a producer publishing `+00:00`, and the
  row cleared at 05:32 local. The check said `unknown`, correctly; what
  it cannot notice is a marker written in the wrong zone.

### Session 76 — every claim names the check that closes it (2026-08-24)

**`SNAG-ESTATE-011` fixed, and the entry's own contradiction was the
fix.** Session 73 made five figures in this block machine-checkable and
left the rest as prose; its follow-up entry named `<!-- check: … -->` as
the cheap next move and refused a marker in the very next clause. Both
are right about **different markers**. `<!-- routes=46 -->` can agree
with the box while the prose beside it disagrees and nothing notices —
`ops_claims.py` rule 1, `SNAG-DB-003` arriving in a document.
`<!--check:routes-->` states no fact at all, so the figure in the prose
stays the only statement of itself and there is nothing to drift from.
Suite **2194 → 2229**, ruff and mypy clean, verified live.

- **The marker is additive and cannot subtract.** Every pattern-bearing
  claim runs whether or not a line names it, so deleting a marker is a
  way to be *told*, never a way to retire a check — a gating marker would
  make "edit the document" a switch, which is rule 2's silent retirement
  arriving inside the fix for it.
- **`check_markers` is the enforcement point `SNAG-ESTATE-008` asked for
  and had no way to have.** A figure this module can test that no line
  claims is reported; so is a marker naming a check nobody implements. On
  its first run against the real block **five figures came back
  unclaimed**, every one a sentence that had been checked for a sitting
  and never claimed. A typo fires from **both** sides —
  `<!--check:helth-->` gave the unknown name *and* the now-unclaimed
  `health` beside it, which was not designed.
- **A prediction is timed, not measured.** The instance that opened the
  entry — "the row clears at 03:32", written at 00:30 — was not wrong
  when written and not measurable when written, so no pattern reaches it.
  `expires` is the one family whose members the **document** declares.
  After its moment the claim is `unknown`, never `mismatch`: the
  prediction may well have come true, and "nobody went back" is what rule
  2 reserves `unknown` for.
- **The pin was broken and only a live run said so.** The `expires`
  instant is the single fact stated twice, so it is pinned to its
  sentence rather than trusted. The first implementation searched the
  flattened region, **which contains the marker**, so `03:32` matched the
  marker's own copy and the pin passed whatever the prose said — a check
  agreeing with itself by construction. Three fixture tests of that pin
  were green either side of the fix.
- **`/health` is checked and 8400 deliberately is not**, with the reason
  in the block's own prose: `estate/judgements.py` rule 3 declines to
  judge estate-manager's reachability here, and a claims-checker that
  alerted on it would re-import the second owner that rule prevents.
- **19 new tests, five falsified** against the behaviour they replace —
  and the hand-written-`CHECK_KEYS` falsification fired **twice**, having
  forgotten `health`, which is the derived rule demonstrating itself.
  The whole check was then driven against a copy of the real document
  broken four ways at once: **four faults and exit 1**, against eleven
  `ok` and exit 0 on the real one.
- **Filed on the way**: `SNAG-ESTATE-012` — a sentence with no pattern
  *and* no marker is still invisible, because deciding that an English
  sentence is a claim is a human's job and always was.

### Session 75 — a deleted route stops answering 200 (2026-08-24)

**`SNAG-LOG-011` fixed, and the class it belonged to removed with it.**
`GET /api/logs/summary` answered `200` with `{"source":"summary",
"entries":[],"count":0}` through the `/{source}` catch-all — telling a
caller "no summaries" about a table migration 014 had destroyed the
sitting before. Two `410 Gone` tombstones now sit above the catch-all,
and `/{source}` validates its argument against the declared sources.
Suite **2195 → 2206** green, ruff and mypy clean, routes **46 → 48**.

- **The validator's key was the whole design, and it is not one field.**
  `log_entries.source` holds the **unit** for a journal source and the
  **name** for a file source, because `_read_journal_source` and
  `_read_log_file` stamp different things. The rule therefore lives in
  `services.stored_source_name`, written from the ingestion loop's own
  dispatch rather than from the live table — every declared source on
  this box is `type: journalctl`, so a rule derived from the data would
  have omitted the file branch and stayed green until the first file
  source was declared, at which point the route would 404 its own rows.
- **Both configuration files, and the measurement says why.** `kernel`
  is declared in `config.yaml` because it belongs to no service, and it
  is **451,319 of the 451,569 rows** in `log_entries`. A set built from
  `services.yaml` alone passes every fixture and rejects 99.9 % of the
  data. So the composition was lifted out of
  `LogAggregatorAgent._sources` into `services.composed_log_sources`
  rather than restated — the set the route admits must *be* the set the
  agent ingests, not merely agree with it.
- **`410` rather than `404` for the two retired paths**, because "was a
  route and was removed" and "never was a route" are different states
  and a caller cannot tell them apart otherwise — `ports_checked`'s rule
  one status code up. `/summary/history` already 404'd (the catch-all
  takes one segment) and is named anyway, so the pair answers with one
  voice; a client told `410` by one and `404` by the other would
  reasonably read the second as a typo.
- **The tombstones patch two paths; the validator removes the class.**
  Any single-segment path under `/api/logs` added and later removed
  acquired this behaviour, and `/{source}` has been last in the router
  since it was written — which is what makes it work at all, so it
  cannot simply move. An unknown segment is now a 404, so the next
  removal needs a tombstone only to be *specific*, never to be honest.
- **Passing a source *name* was the same defect one level down.**
  `/api/logs/alfred` used to return an empty list, indistinguishable
  from a quiet service; it now 404s and the detail names the fifteen
  declared units, so the caller learns to ask for
  `alfred-backend.service`.
- **The route had no tests at all before this sitting.** Nothing in the
  suite asserted `/{source}`'s behaviour, which is how a route
  describing a dropped table stayed green through the sitting that
  dropped it. All eleven new tests were falsified against the behaviour
  they replace; the one worth naming is the **ordering** falsification —
  declaring the tombstone *below* the catch-all produces the same `200`
  as deleting it, and only the behavioural test can see the difference.
- **Stated cost, empty population today.** A source removed from
  `services.yaml` keeps 30 days of rows this route will no longer serve.
  All 9 distinct values in `log_entries.source` are declared (measured),
  and the rows stay reachable through `GET /api/logs/recent?source=`,
  which has no validator because its job is history.

### Session 74 — the three frozen tables dropped (2026-08-24)

**Migration 014.** `project_snapshots` (3,447 rows), `project_reviews`
(4) and `log_summaries` (1) are gone, with the four mechanisms that
carried each of them: a `retention_config` row, a
`TABLE_TIMESTAMP_MAP` entry, the `FROZEN_TABLES` exclusion and — for
the third — a mapped model. Table count **14 → 11**, head **013 → 014**,
suite **2195** green, `check-ops-claims` re-run and clean.

- **The blocker in `tasks.md` was wrong by four orders of magnitude.**
  It said the 26 rows the estate's copy lacks cost "a day of history for
  26 projects". Compared on `(project_name, scanned_at)` across both
  databases: this schema's final sweep is `2026-08-13 07:35:03` and the
  estate's next scan is **07:35:46** — 43 seconds — and **all 26
  projects appear in it**. Nothing was ever missing from the estate's
  series, so no copy was requested and none was needed.
- **Waiting was costing the history the entry was protecting.** The same
  entry counted 3,739 rows on 2026-08-16 against 3,447 today: the
  `retention_config` row was thinning a frozen table on a 90-day window
  every night. The estate holds **4,155** snapshots back to
  **2026-05-10** against this schema's 2026-05-20 — a superset at both
  ends.
- **Emptying `FROZEN_TABLES` is the proof, not a tidy-up.** An entry
  there is a *blindfold*: the drift guard compares whatever
  `include_object` admits, so the three tables were exempt from the one
  test that would have noticed them. Dropping them needed the set
  emptied, not a new guard — and the constant is kept, because deleting
  it would take `test_autogenerate_config.py`'s single-copy guard with
  it at the moment nothing is exercising it.
- **One new test, and one written then deleted for being a second
  statement of one fact.** Retention's two halves fail in opposite
  directions and only one was uncovered: a `TABLE_TIMESTAMP_MAP` entry
  for a dropped table is **loud** and `test_purge_statements_parse`
  already refuses it (more strongly — it also catches a wrong column), so
  the existence check written beside it was measured against that guard
  and removed. A `retention_config` row the map cannot resolve is
  **silent** — skipped with no log line, purging nothing — and nothing in
  the suite read that table at all. Falsified before the migration ran:
  it named all three.
- **The downgrade reproduces the schema byte for byte and cannot
  reproduce the rows**, which the docstring says rather than leaving to
  be discovered. Round-tripped against the live database and diffed
  against a `pg_dump -s` taken before the drop: identical. The names are
  interpolated rather than bound, migration 013's rule — verified by
  rendering `alembic upgrade --sql 013:014`, where a bindparam would
  have become `WHERE table_name = NULL` and deleted nothing.
- **The restart was required, not cosmetic.** The daemon booted at
  21:52:06 held the old map in memory, so its 03:00 purge would have
  raised for three tables that no longer exist.


### The block that opens a sitting gets a reader (2026-08-24)

**`SNAG-ESTATE-008`'s machine-checkable half fixed.** Six consecutive
sittings were spent on claims that had stopped being true — an ops action
done three days earlier by another repository, a restart method that
needed no `sudo`, and yesterday this file asserting a retention boundary
three hours before it happened. `sysadmin/ops_claims.py`, the console
script `sysadmin-check-claims` and `scripts/check-ops-claims.sh` now
re-measure the block, run by `claude-preflight.sh` at the start of a
sitting and `claude-postflight.sh` at the close.

- **Seven checks in two kinds, and conflating them would have you edit
  the wrong artefact.** Five *claims* parsed out of the block itself —
  routes, tables, the documented Alembic head, unresolved alerts, the
  daemon's start time — where a mismatch means the **document** is stale;
  two *state* checks — the live schema against the packaged head, and
  whether the daemon is serving the code on disk — where it means the
  **box** is. Advisory at both ends; nothing blocks, and nothing edits a
  document, because a check that corrects the file it reads becomes a
  second author of the claim.
- **The entry understated its own defect by a whole surface.** It says
  preflight prints the priorities "without checking either against
  `sysadmin.alerts`". Measured: the extract is anchored on
  `## Quick Status`, and the sub-session block is a blockquote *above*
  it — so the banner was not failing to check that block, it had never
  printed it. The one surface the global rules require to be read first
  was the one the session-opening banner omitted.
- **The obvious deploy check is wrong on this box, and was wrong today.**
  Daemon start **09:58:28** against the newest commit touching
  `sysadmin/` at **10:05:22** reports a restart owed on identical
  content — this repository restarts to verify and commits afterwards.
  The newest `.py` on disk, **09:57:46**, answers the question actually
  being asked. Both rules were run before either was written down.
- **`systemctl show` answers for a unit that does not exist**, exits `0`
  and prints `ActiveState=inactive` — this snag's own shape found inside
  its own fix, and the reason `LoadState` is the gate. Its test drives
  the real binary, because a stub written by the same hand as the gate
  agrees with it by construction.
- **A *fall* in the alert count is the founding case**, and it is the
  direction nobody writes a rule for. Equality or a rise is the obvious
  comparison; this entry exists because eight collation rows resolved
  themselves at 18:01:48 and four documents went on asking for the
  `REINDEX` for three days. Both directions are reported, worded
  differently, with the open titles named rather than counted.
- **The check refuted its author within a minute of being wired up.** The
  first rewrite of the block under it wrapped `holds **2**` and
  `unresolved` across two lines with a `>` between, and the claim came
  back `unknown` — correct by the rule that not-knowing is never
  agreement, and useless, because a paragraph reflow must not be able to
  retire a claim. `flatten()` strips the decoration and matches against
  prose. Nothing but running it would have found that.
- **32 → 35 tests, six falsified against the behaviour they replace** —
  first-match parsing, `len(app.routes)` (which is **50** against the
  documented 46: FastAPI adds four docs routes of its own), no
  `LoadState` gate, `max()` over the exit map, an unbounded parse region,
  and the missing `flatten`. All six fired. Suite **2159 → 2194**, ruff
  and mypy clean, no new routes and no migration.
- **Driven against a document made false on purpose.** All five claims in
  today's real block hold; a copy with the route count set to 44, the
  alerts to 9 and the restart backdated produces three `no` lines, the
  alert one reading *"7 fewer unresolved rows … an action it asks for may
  already be done"* — this entry's founding case reproduced from the
  outside.
- **`SNAG-ESTATE-011` filed for what is left**: the block's other claims
  are prose no pattern can reach, and the *convention* the entry proposed
  — every ops action names the check that closes it — has no enforcement
  point yet.

### Two rows said the same thing about two different faults (2026-08-24)

**`SNAG-LOG-010` fixed.** `GET /api/logs/actions` served two rows reading
exactly `kernel: 39885 occurrences, unchanged` — same source, same count,
same severity, same kind, and two genuinely distinct signatures, because
one kernel retry loop emits both Bluetooth firmware messages at equal
volume. `SNAG-AGENT-005` moved the signature *into* `alert_title` on
2026-08-12 for precisely this reason; the advice endpoint never got the
same treatment.

**The entry's own account of its scope was wrong in both halves, and only
running the producer said so.** It filed the defect against `noise` and
ranked it last on "population is currently zero". Driven through the real
`recommend()` against the live table at the 2026-08-12 anchor: **14 of 21
rows collided, in five groups** — `New incident on sysadmin.service` ×4,
`New incident on kernel` ×3, `New fault from sysadmin.service` ×3,
`New fault from sportsanalyser-frontend.service` ×2, and the entry's own
pair ×2. At the live anchor the `noise` population *is* zero and **7 of 9
rows still collided**, every one of them `severity: risk`. So the rule
went to all four title builders, not to the one that had been noticed.

- **`quoted_signature()` / `capped_signature()`** in `log_actions.py`:
  bounded at `SIGNATURE_DETAIL_CHARS` with `truncate_at_word`, so the cut
  is marked. `log_review._quoted_signature` keeps only its `figure_free`
  gate and borrows the rest — one signature written one way on both
  surfaces.
- **12 member signatures per request were being sliced mid-word with no
  marker**, one ending `"message": "alert_raised", "service"`. That is
  the unmarked cut `log_review._quoted_signature`'s docstring calls
  `SNAG-BRIEF-002` and calls *worse* on a signature — in the module that
  lent it the constant. `SAMPLE_DETAIL_CHARS` names the other bare slice,
  which had been written twice.
- **The noise title no longer claims a direction.** `unchanged` was
  asserted for all four change kinds `_is_noise_candidate` admits, and
  both live rows classify **`FALLING` — 39,885 this window against
  77,496 last** — flatness asserted about a signature that had halved,
  contradicted by the row's own `detail`. The count stays: volume is the
  reason to act.
- **The cost is stated rather than hidden.** `sysadmin.service`'s
  signatures are whole JSON records (`SNAG-LOG-008`), so four of the nine
  live titles now open with `{"timestamp": "N-N-N …`. It is the trade
  `alert_title` already made and `SNAG-LOG-003` already paid for — an
  ugly title a reader can tell apart beats a tidy one they cannot.
- **The tests were what hid it.** Every title in the module was pinned by
  one assertion, `rows[0].title.startswith("New fault from")`, which the
  defect passes intact. Nine new tests, each falsified against the
  behaviour it replaces — and one had to be strengthened before it could
  be, because it compared the two modules' quoting on a *short*
  signature, where a slice and a marked cut agree.
- **Verified on the route**: 7 collisions among 9 rows at 09:57, **0
  among 9** after the restart at 09:58; the specimen pair reproduced
  through the real `build_report` → `recommend()` over the storm window,
  18 days before those rows age out.
- **`SNAG-LOG-013` filed** for what the cap leaves: 9 of 55 signatures
  share their capped prefix, and one live incident row already lists
  **7 members identical after capping** — the roll-up naming nothing, one
  level below the titles. Its population empties by retention at about
  14:11 today, which the entry says so nobody re-ranks it on a zero.

### The advice pointed at the wrong hour, and the fix was already in the repository (2026-08-24)

**`SNAG-LOG-009` fixed.** Every `journalctl` command
`GET /api/logs/actions` emitted carried a UTC-rendered wall clock —
`--since '2026-08-22 17:10'` for an event stored at
`2026-08-22 18:10:16.115268+01` — and journalctl reads a bare datetime as
**local**. Nine of nine live rows. On this box the window opened an hour
early, which is the trap: BST makes the error *widen* the read, so the
box that would notice is the one that never runs the command.

**Measured at two timezones rather than reasoned about.** The emitted
`--since '@1787418616'` resolves to exactly the stored moment and the
read opens on that line; the old form lost exactly **one** line here
(`Starting Mosquitto MQTT Broker daemon.` at 18:10:15). Re-run under
`TZ=America/New_York`, the epoch form is unmoved at **57,695 lines** and
the wall-clock form returns **48,946**, opening at `17:10:00 -04:00` —
**four hours past** the incident, which is absent from the output. The
rule is *N* hours late at UTC−*N*, so the entry's "five hours" is EST and
four is EDT; either way the row's whole purpose is lost.

**The entry's proposed remedy was the weaker of two, and this is a shape
not recorded here before.** It called the fix "one `astimezone()`", which
renders a **local wall clock** — correct on this box, verifiable, green,
and still ambiguous, because it holds only while the process writing the
command and the human running it share a zone, and an autumn-fold local
time names two instants. `journal_command` now takes a **`datetime`** and
the rendering belongs to `journal.since_timestamp`, which has emitted
`@<epoch>` and stated this exact reason since the module was written. So
the defect was never a missing conversion: it was three callers each
implementing a fact a fourth function already owned — the same shape as
the `-k` bullet in `journal_command`'s own docstring, met from a third
direction. Taking the type is what makes a fourth caller impossible
rather than merely unlikely.

**The tests were the thing hiding it.** `TestJournalCommand` pinned the
*rendering*, so a wrong command stayed green across three sittings.
`TestTheWindowJournalctlOpens` models the **consumer** instead —
`_journalctl_reads` resolves the emitted argument the way journalctl
does, in London, New York and UTC, and asserts it lands on the event. All
four new tests were falsified against the behaviour they replace; the
truncation-direction one needed its own falsification (`int` →
`math.ceil`, which opens the window 1 s *after* the event).
`since_timestamp` now **refuses a naive datetime** — `timestamp()` reads
one as local, which is the reading being removed, so accepting it would
rebuild the defect inside its own fix with the right-looking type. Empty
population by construction; the guard exists to keep it that way.

**The prose was labelled in the same sitting** so the fix does not leave
a row disagreeing with itself. `detail`'s "First seen …" and the incident
line's "within Ns of …" now say `UTC`. Deliberately *not* converted to
local: `@<epoch>` takes a timezone out of the command, and putting one
back into the prose beside it is the opposite direction — and the label
agrees with `GET /api/logs/trends`, which serialises `first_seen` with a
`+00:00` offset.

### Nothing applied migrations, so the guard's refusal was an outage (2026-08-24)

**`SNAG-DB-005` fixed.** Migration 013 was written, committed and never
applied; the daemon was restarted to serve a new route, `schema_guard`
refused (correctly), `StartLimitBurst=5` made the loop terminal, and
`sysadmin.service` stayed dead **23 hours**.

`sysadmin-check-schema` is a console script over the guard's own
`packaged_head()` and a new `live_revision_sync()`, wrapped by
`scripts/check-migrations.sh` and called **blocking** from
`claude-precommit.sh` and advisory from `claude-postflight.sh`. The commit
is the last scripted moment before the hand-typed `kill -TERM` — there is
no deploy script on this box.

**The snag's own ranking of its three candidates was wrong in two places,
and both errors are the same shape: cost weighed without asking what the
option buys.** `ExecStartPre=` was ranked cheapest-that-works and buys
nothing — a check there is the lifespan guard relocated one process
earlier, with the same refusal and the same 23 hours. Postflight alone
would not have caught *this* outage, because Session 69's restart happened
mid-sitting.

**And prevention owns almost none of the 23 hours.** The failure *was*
announced — a persistent critical toast reading `result=exit-code, exit=1,
restarts=5`, pointing at `systemctl status`. The cause was one revision
number and the remedy one command, both held in `schema_guard._REMEDY` and
written only to the journal. `unit_failure._schema_diagnosis()` now puts
the verdict in the alert row and `notify-unit-failed.sh` in the toast —
`collation.py`'s rule 4 applied to the fault that needed it most. A healthy
schema adds nothing to the message and is *still* recorded, because
"checked, and it was not this" is not "never checked".

Three verdicts and three exit statuses: `unknown` (exit 2) **warns and
never blocks**, the one place this family fails open, because a commit
refused by an unrelated PostgreSQL outage teaches the operator to reach for
`--no-verify`. **2146 tests** (+45); the counterfactual was driven by
adding a temporary migration file rather than stamping the database, so the
box was never put into the state the snag describes.

### The weekly log review, and a premise that was false (2026-08-24)

**Session 27 is complete.** Tier 3 is `sysadmin/monitor/log_review.py`,
`GET /api/logs/review`, `POST /api/logs/review/generate`, a Monday 05:15
job, a "Weekly Log Review" briefing section and a `log_reviews` table
(migration 013). The first review is stored: `llm_used: true`,
`confidence: medium`, all ten input keys in `stats`, and **zero figures
produced by the model**.

**The row that described this tier was wrong, which is the finding.** It
said the overnight LLM summary "already runs in the briefing — extend
rather than duplicate". Measured: `LogAggregatorAgent.summarise()` had
**no caller anywhere**, `log_summaries` held **one row** dated
2026-07-24, and the 12-hour freshness window meant the section had been
absent from every briefing for **25 days**. There was nothing to extend.
The single row is the argument: it covered **29 seconds**, reported
`entry_count = error_count = 100` (both the query's `LIMIT`), and
answered a hundred raw log lines with "1. Repeated failures 2. Pattern of
failures" plus the invented rate "every 1-2 seconds".

**Rule 3 is this tier's own, and the other two Tier 3s could not have
found it: the normalised signature may go into the prompt verbatim,
because normalisation is the operation that makes it figure-free.**
`signature()` maps every digit run to `N` — **0 of 46 live signatures
contain a digit**. The disk review had to invent `KIND_PHRASES`; here the
safe form already existed and is the same string the reader matches
against `GET /api/logs/actions`. `_HEX` produces `0xN`, whose `0` is a
digit by construction, so it is still filtered.

**`direction_phrase` is asymmetric.** Truncation only ever lowers a
count, so a rise is trustworthy at any confidence and a fall is not —
Session 63's one-directionality argument deciding what the narrative may
*claim* rather than what the input threshold may be. Verified reaching
the reader: the live generation wrote "the kernel service was reported
less frequently, which could be due to the reading rather than the actual
fault".

**Two defects only the live LLM run found**, both fixed and re-verified:
the model **invented `kernel.service`**, reproducing in prose the exact
`journalctl -u kernel` error Tier 2 removed from the emitted commands;
and it nominated two services for "look at first" that had no
recommendation, having merged the faults list with the movement list.
Every fixture was green throughout.

**The briefing's overnight block is a live count now**, and that closes
the mechanism that hid the defect: `_logs_clause` returns `None` for a
missing block, so a quiet night and a dead producer rendered identically
as nothing at all. It is unconditional and tells three outcomes apart —
no entries at all is a statement about the aggregator, not the box.

**2101 tests green** (+34). Six guards falsified deliberately and **two
failed to fail**: a band test asserting `NOISE_MIN_OCCURRENCES in
thresholds`, which a hardcoded `100` satisfies, and a prompt-label test
asserting `label in prompt`, which the instructions satisfy by quoting
themselves. Replaced by an AST sweep and a facts-half scope, then
re-falsified.

**Four snags opened, and one is a P1 that had already cost an outage.**
`SNAG-DB-005`: the daemon was `failed` with `start-limit-hit`, dead since
2026-08-23 08:39 — 23 hours — because a migration was written and not
applied. `schema_guard` did its job; nothing on this box applies
migrations. Also `SNAG-LOG-010` (two `noise` titles indistinguishable),
`SNAG-LOG-011` (a deleted route still answering 200 behind the
`/{source}` catch-all) and `SNAG-LOG-012` (`strip_markdown` leaves inline
backticks — estate-lib's, delegated).

### One incident, one recommendation — SNAG-LOG-001 closed (2026-08-18)

**The entry asked for a correlation rule and proposed the wrong one; the
purge had already produced the specimen that refutes it.** Session 68
built the rule the specimen supports: first sightings are one incident
when they share a unit **or a declared systemd dependency** inside
`INCIDENT_WINDOW_SECONDS`.

Live, `GET /api/logs/actions` went **24 → 11**. The 2026-08-12 mosquitto
core dump is now one row — *"New incident: mosquitto.service then
estate-broker-provision.service"* — naming all six signatures and
emitting one `journalctl -u … -u …` that was **run and works**.

**The measurement the session existed to make came out cheaper than the
question assumed.** The choice was framed as declared-versus-effective
graph, with `scan.py`'s no-subprocess promise at risk. The real question
was *which directories*: `mosquitto.service` is packaged and its file
lives in `/usr/lib/systemd/system`, which the sweep never walks — so the
obvious move was to widen the walk. **Parsing `/usr/lib` reads 629
further unit files and yields zero further relations** among the fourteen
declared log sources, because a relation is declared by the unit that
*depends* and here that unit is always the hand-written one. The sweep's
existing two directories suffice, at 16x less I/O.

**The graph is the filter; the clock only bounds it** — and the live
window proves it needs to be. `alfred-backend.service` failed **1.2036 s**
after the crash for an unrelated reason (PostgreSQL still starting up)
and `sportsanalyser-backend.service` failed **2.9 s before** it. Driven
as a counterfactual rather than argued: forging one edge admits
alfred-backend, and removing the graph reproduces the entry's own
proposal — mosquitto's four collapsed, the provisioner's two left
standing as a phantom second fault.

`INCIDENT_WINDOW_SECONDS = 5.0` is **derived from a gap, not picked**:
every genuinely-one-incident pair lands inside **349 ms** and the nearest
genuinely-two-incidents pair is **64.4 s** away, so every value between
gives identical output.

**Three things it corrected in what had been written down.** The entry's
mechanism was backwards — systemd started the oneshot **2 ms after**
mosquitto had already failed, because the relation is `Wants=`, which
does not propagate failure. The whole window is a **boot** beginning
twelve seconds earlier, which three sittings had not noticed. And a
fixture of the session's own walked into `log_signature`'s trap: `line
0/1/2` normalise to one signature, so the first version of the
anti-single-linkage test passed for the wrong reason.

**Byproduct**: the same rule collapses `sysadmin.service`'s raw-JSON rows
(`SNAG-LOG-008`) from **10 recommendations to 3** — seven of them one
agent run's alerts inside 1.7 ms. It does not close that entry, which is
about the signatures being unreadable rather than how many rows they fill.

**2067 tests green** (+36), ruff and mypy clean. Ten guards were each
falsified deliberately — ignoring the graph, single-linkage, dropping the
first-sighting filter, dropping the tie-break, bypassing the noise
filter, and five more on the graph builder — and each broke precisely the
tests written for it.

**Two costs filed rather than bundled**: `SNAG-LOG-009` (every emitted
`journalctl --since` is an hour early here and would be five hours *late*
west of Greenwich — found by running what the new row emits) and
`SNAG-UNITS-006` (drop-in directories are invisible to the sweep; empty
population today, measured).

### The 497 surplus log rows purged, and the cost was understated (2026-08-17)

**Session 66's fix stopped new duplicates and deleted none of the old
ones.** This sitting deleted them — reversibly, backed up, with the restore
path verified rather than claimed — and measured both endpoints either side.

**The identity was proved before anything was deleted, and the obvious
evidence pointed the wrong way.** `raw_line` differs in **all 339**
duplicate groups, which reads as proof they are distinct journal entries; it
is journalctl's JSON key ordering varying between reads. Settled against
journald's own identity instead: **338 of 339 groups carry exactly one
distinct `__CURSOR`, and none carries more than one.** The 339th is the
mosquitto coredump, whose `raw_line` is truncated at 2000 characters so the
cursor fell off the end — its three `ingested_at` stamps are the three
restarts, the same evidence by another route.

Two rules the purge itself needed, neither of them in the filed plan:

1. **The purge key must be the fix's key.** `(source, logged_at, message)`
   is what `_is_unstored()` uses to decide an entry is already stored, so
   the surviving table holds no shape the running code refuses to
   re-create. The plan's tie-break was wrong, though: it said "keep the
   earliest `id`", and `UUIDPrimaryKeyMixin` is `uuid.uuid4`, so ordering
   by `id` is arbitrary. The earliest `ingested_at` is kept instead —
   keeping a random copy falsifies when the service first observed the
   entry while leaving `logged_at` correct.
2. **A purge can re-open the defect it cleans up after.** `_resume_floor()`
   reads `max(logged_at)` per source and the message set at it; deleting
   the last surviving row there moves the floor backwards and the next
   poll re-reads the window. Asserted 0 inside the transaction, and both
   guards falsified deliberately — each aborts, and the `DELETE` never
   executes in either falsified run.

**497 rows deleted**, 626,976 → 626,479, duplicate groups 339 → **0**.
`GET /api/logs/actions` went **28 → 24** recommendations at unchanged
`confidence: medium` with **no new rows**; `GET /api/logs/trends` holds 47
signatures, `truncated: false`.

**The entry understated its own cost, which is the part worth carrying.**
It said counts were overstated by up to 19×; four recommendations were
**fabricated rather than inflated**. Both `alfred-backend` surges read 21
vs 5 (ratio 4.2) against a genuine **4 vs 5**, and both
`sportsanalyser-frontend` surges read 19 vs 6 (ratio 3.17) against a
genuine **1 vs 3** — a **decline that was being reported as a surge**.
Duplication inverted the direction, which a claim about magnitude does not
predict. Worst surviving inflation: `estate-broker-provision` **18 → 1**,
`kernel` "failed to reset" **17 → 1**, `estate-manager-api` **23 → 11**,
`venture-assistant-backend` surge **48 → 27**. The two `noise` rows moved
39,922 → **39,885** — so the family this month's work unblocked was the
least distorted of them.

`SNAG-LOG-008` opened: ten `sysadmin.service` rows are frozen as raw JSON
because `unwrap_json_message` applies at read time and cannot reach rows
stored before the Session 64 declaration. Historic and measured — all ten
ingested 14:12–14:22, the readable ones begin at the 19:50:19 restart.

### Four shipped-unrun claims verified, and SNAG-LOG-007 found underneath them (2026-08-17)

**Sessions 63, 64 and 65 shipped green and unrun; this sitting restarted
the daemon and measured what they claimed.** All four hold:

1. **`-p`'s read efficiency.** Reproduced against the real journal on the
   2026-08-12 storm window: **122,531 raw kernel lines carrying 49,012
   storable ones — 40.0 %**, so a 500-entry budget was carrying ~200
   usable entries and now carries 500. The first catch-up read after each
   of three restarts truncated **nothing**.
2. **`SNAG-LOG-002`'s gate.** `GET /api/logs/actions` returns
   `confidence: medium` and **2 `noise` rows** — the two Bluetooth
   signatures at **39,921** apiece — where it had served zero for the
   family's entire life. 25 recommendations total (18 `new_signature`,
   5 `surge`, 2 `noise`).
3. **`SNAG-LOG-003`'s declaration.** A new `log_entries` row reads as
   prose against the 10 raw-JSON rows beside it, and the alert title from
   a **700-character** JSON journal line is **46 characters**:
   `Log error: sysadmin.service — agent_run_failed`.
4. **`SNAG-LOG-005`'s `covered_by`.** Not observable from history — the
   215 historic `agent_run_failed` lines are all `PRIORITY=6`, so the
   reader's `-p 4` excludes them, and `agent_runs` held **0 failed rows
   across 48,452 runs**. Driven by inducing a controlled
   `service_discovery` failure: the row came back `severity: info` with
   `details['covered_by']` naming `failures.py`, `noise_reason` correctly
   `NULL`, and — the point of the fix — it fired on the **first** failure
   and was quietened rather than announced.

**`SNAG-LOG-007` was found by the verification rather than in it.** One
mosquitto coredump from 2026-08-12 had been raised as a fresh `critical`
three times, once per restart, and nothing in the four claims predicted
that. `_resume_floor()` opens the catch-up window at the newest stored
entry; `journalctl --since` is inclusive and `since_timestamp` truncates
to whole seconds, so the boundary entry came back every restart —
**339 duplicate groups, 497 surplus rows, worst case 19 copies of one
entry**. Fixed by closing the boundary against the stored rows rather
than by narrowing the window, because narrowing it trades a duplicate for
a gap. Before/after on the same box: the 19:49 restart re-ingested 26
entries reaching back five days; the 20:03 restart re-ingested **0**.

### SNAG-LOG-005 fixed — one owner for agent-run health (2026-08-17)

**The fix that made the monitor able to see its own errors gave one fault
two speakers.** `BaseAgent.run` states one fact twice, three lines apart:
`logger.exception("agent_run_failed")` to the journal, then a `failed`
row to `agent_runs`. Session 61's level prefix and Session 64's
`format: json` are what let the first copy reach the log aggregator, so
an agent failure raised a row here **and** a row from `failures.py` — two
tray fingerprints. Sharper than duplication: `failures.py` requires
**two** consecutive failures and argues the rule out in writing, while
the journal path raises on the **first** line.

`COVERED_SIGNATURES` maps `(source, signature)` to the family that owns
the fault, quietening to `info` with `details['covered_by']` **naming**
it. Both halves of the one entry are the producers' own constants —
`OWN_UNIT`, and the new `AGENT_RUN_FAILED_EVENT` that replaces the string
literal `BaseAgent.run` used to pass to `logger.exception`.

**Three things the measurement settled that the entry had not.** The
collision was **four** rows historically, not two — 215 of 215 incidents
fired `agent_run_failed`, `scheduler_job_error` and apscheduler's own
`Job "…" raised an exception` in the same second. The obvious wider fix
(exclude this daemon's unit from the alert half) is refuted: **34 of 249
error incidents carry no `agent_run_failed` at all**, and
`retention_purge` is not an agent, so nothing else covers it. And
quietening is safe because `_record_outcome` is awaited *outside*
`run()`'s `try` — the case where `failures.py` is blind is the case where
`scheduler_job_error` is still loud, which is why `agent_runs` holds
**zero** `failed` rows across 7,816 sysadmin runs.

Ships untriggered: all 215 lines fall in the 2026-08-08 → 08-10
`SNAG-DB-001` window. Driven live instead — real journal lines through
the real `unwrap_json_message` and `_execute` against the live database
in a rolled-back transaction, **0 rows of residue**. Six tests, each
falsified deliberately. `SNAG-LOG-006` filed for the one path the safety
argument does not reach: a manual run started with `asyncio.create_task`
has no scheduler listener behind it.

### SNAG-LOG-004 found and fixed, SNAG-LOG-003 closed — the line too long to read at all (2026-08-17)

**Two halves, and the one that was not on the plan is the P0.** Session 64
set out to give this daemon's journal source a `format: json` declaration
and could not test it, because `read_journal` never received the lines it
was meant to unwrap.

`journalctl -o json` substitutes `null` for any field over ~4096 bytes
unless `-a` is passed. `MESSAGE` therefore returned `None`,
`entry["message"][:5000]` in `LogAggregatorAgent._execute` raised
`TypeError`, and the whole run died — every source in it, not just the
one that produced the line. **Self-sustaining**: the failure is logged by
`logger.exception`, itself a >4096-byte line at `ERROR`, so the next poll
reads *that* and crashes again. All **215 historic `agent_run_failed`
lines are 12,837–12,845 bytes** and every one exceeds the cap.

Armed by the previous fix and not yet sprung: those lines were
`PRIORITY=6` until the 14:10:58 restart, so `-p 4` excluded them and
**40,228 `log_aggregator` runs have never failed**. Measured at the moment
of the fix: **0 error lines and 146 clean runs since the restart**.

Then the declaration itself. `LogFormat = Literal["text", "json"]` on
`LogSource` and `LogRef`; `read_journal` takes `log_format` and unwraps
only where declared. Over the **723 real `ERROR` lines** this daemon has
written, the title goes from **6 distinct values of 242–253 characters of
JSON to 5 of 46–151 readable characters**; `logger` goes to metadata
rather than into the title, because putting it back would restore the one
fork the old key produced by accident (`sysadmin.core.scheduler` and
`sysadmin.services.scheduler`, one fault under a renamed module).

It **fails open at every step**, and the reason is measured rather than
habitual: systemd writes its own plain-text error lines into a unit's
journal — `Failed to start SportsAnalyser - Frontend (Next.js).` appears
**668 times** live — so a declaration that discarded non-JSON would
silence exactly the line saying the service died.

**2017 tests** (was 1984), ruff and mypy clean. Both halves' guards
falsified independently.

### SNAG-LOG-002 closed — the gate was binary, and one read pinned a fortnight (2026-08-17)

`log_trends._confidence` returned `LOW` on `runs_truncated > 0`, so a
single catch-up read suppressed every volume argument for fourteen days
and `GET /api/logs/actions` served **zero** `noise` rows against two
signatures at 39,921 occurrences apiece. It now gates on
`truncated_fraction > TRUNCATION_LOW_FRACTION` (0.05) over the
**instrumented** reads. Live after the change: confidence `medium`, **25
recommendations including the 2 `noise` rows**.

Three things the measurement settled that the plan had wrong.
**`_resume_floor()` does not size the catch-up read by daemon downtime** —
it returns the newest stored `logged_at` for that unit, so a source
logging one warning a week is read a week back on every restart, which is
why the 16 non-storm truncations each name four or five sources at once.
**Session 62's `-p` therefore does reach them**, against the expectation
that no ceiling could: the 13:17:05 restart's poll truncated 4 sources,
the 14:10:58 restart's poll truncated nothing. And **the denominator was
wrong** — 120 of 7,006 instrumented runs (1.71 %), not 120 of 17,730
(0.68 %), a 2.5x artefact that would have self-corrected and so would
never have been re-checked.

The threshold is legitimate because **truncation is one-directional**: it
drops entries, so it can only make a count too low, and "this is loud" is
a floor missing data cannot undercut — rule 4's `NEW` asymmetry one step
further. What it bounds is a depressed *current* window moving a
`SURGED` signature into the noise-eligible `STEADY` band. `HIGH` is
untouched; only the floor beneath it moved. Falsified before being
trusted: `TRUNCATION_LOW_FRACTION = 0.0` restores the binary rule exactly
and breaks precisely the four new tests.

### SNAG-LOG-002, the ceiling half — the budget was 40 % useful (2026-08-17)

`read_journal` bounded the read with `-n 500` and then applied
`severity_filter` in **Python, over lines the ceiling had already
counted**. Across the 2026-08-12 kernel storm that is **203,042 raw
lines carrying 81,216 storable ones — 40 %**, a median of **510 raw a
minute against a ceiling of 500**, and **208 of 210 storm minutes
truncated**. The 100 instrumented storm minutes produced **103 truncated
reads: one per poll.**

Passing `-p` to journalctl, derived from `PRIORITY_MAP` rather than
written down beside it, makes the same 500 carry 500 storable entries.
Verified against the real journal: the stored multiset is **identical**,
budget efficiency **40 % → 100 %**, steady kernel polling **510 → 204**
lines a minute. `max_entries_per_read` is unchanged — raising it would
have bought the same headroom at 2.5× the memory and left the waste.

`read_journal` gained its **first direct tests** (`tests/test_journal.py`,
14): every existing test patches it out, which is how the ceiling came to
bound raw lines unasserted.

**It does not close `SNAG-LOG-002`.** Catch-up reads still truncate —
`_resume_floor()` sets the window to how long the daemon was down — and
`_confidence` is binary, so one such read pins the report `LOW` for
fourteen days. The **per-source** confidence fix the handoff named was
measured and **refuted**: it produces zero noise rows, because kernel
holds the only noise-eligible signatures and 103 of the 120 truncations.

### SNAG-AGENT-008, priority half — the daemon can see its own errors (2026-08-17)

Every line this service writes went to stdout, and systemd stamps
captured stdout `PRIORITY=6` whatever the `"level"` inside the JSON says
— so `read_journal`'s `severity_filter: warning` discarded the lot and
`log_entries` held **0 rows** for `sysadmin.service` across nine nights
of `ERROR` from the broken retention purge.

**The entry's own statement of the trade-off was wrong, and one
`systemctl show` settled it.** It said the two unit-file remedies both
need `sudo`. `SyslogLevelPrefix=` **defaults to true** in systemd and
already read `yes` on this unit — so the prefix remedy needs no unit
edit and no `sudo`, putting it on exactly the footing the entry credited
only to the reader-side hack while fixing the artefact rather than one
consumer's view of it. `journalctl -u sysadmin -p err` will work; so
will any `OnFailure=` hook.

`JournalLevelPrefixFormatter` prefixes each JSON line with `<N>`, gated
on `log_format == "json"` as a **precondition** rather than a proxy:
only JSON guarantees one line per record, so a traceback travels on the
line whose level describes it. `uvicorn.error` — which carries
`Exception in ASGI application` and every unhandled 500 — was
**rerouted, not silenced**, the opposite verb from its sibling three
lines up in the same function.

Verified live without the `sudo` the deploy needs: a transient user unit
running the real `configure_logging`, read back by the real
`read_journal` — **3 entries where it has always returned 0**. Filed on
the way: `SNAG-LOG-003`, and a correction to `SNAG-LOG-002`'s
composition (9 sources, not 2).

### SNAG-AGENT-008, volume half — the line that was written twice (2026-08-17)

`sysadmin.service` wrote **673 journal lines per 5 minutes**, and the two
causes were both invisible to the tests that existed. Every request was
logged **twice** — `configure_logging` clears the *root* handlers, which
never reaches `uvicorn.access`, because uvicorn attaches a handler to it
directly with `propagate = False`. 662 plain lines against 640 JSON in
ten minutes, and the difference is exactly the 22 `/health` polls the
middleware excludes: **`SNAG-API-002`'s exclusion has never worked**, and
its test patches the middleware's own logger. Separately, `ServicesTab`
fanned out one `/details` request per service on every status poll
whether or not the dashboard had ever been opened — **86 % of all
lines**, against its own window's promise of *"no background polling
when hidden"*.

Both fixed and both guards falsified against the pre-fix code; the
logging half additionally driven against uvicorn's real `LOGGING_CONFIG`.
The tray is deployed and measured at **`/details` = 0**; the backend
restart needs `sudo` and is owed.

**The justification for doing it was refuted in the same sitting.** The
118 truncated runs blocking `GET /api/logs/actions` are **kernel 103,
sysadmin-service 14** out of 10,064 — 1.2 %, with 104 on a single day —
and `_confidence` is binary, so `SNAG-LOG-002` did not close with this
and its cause has been corrected in place.

### Session 27 — the log-aggregator tiers (2026-08-17)

Tiers 1 and 2 built; Tier 3 deferred and is now all that remains.
`GET /api/logs/trends` (88 ms, live) and `GET /api/logs/actions` (13
recommendations on real data), off two pure modules. **626,906 rows
collapse to 44 distinct messages in 91 ms**, which is what lets the
signature be applied in Python rather than re-implemented in SQL.

Three things the live data settled that fixtures could not: "new" is a
first sighting and not `previous == 0` (the Bluetooth signature reads
`39,919 / 0` and is a month old); truncation rather than poll count is
the confidence signal, because the journal cursor catches a gap up; and
three of the emitted `journalctl` commands did not work until they were
actually run — the kernel is not a unit, and 7 of 14 sources are user
units. `known_noise` was **built rather than named**, quietening rather
than suppressing, and it reaches already-open rows because Session 39's
ban on in-place severity changes is asymmetric. 71 new tests.

### SNAG-DB-004 — the purge that logged success and rolled back (2026-08-17)

The nightly retention job had deleted **nothing since 2026-08-08** while
logging six successful purges a night: `ORDER BY true` is a syntax error
to PostgreSQL, and one transaction over twelve tables meant the twelfth
discarded the eleven before it. 1,866 green tests missed it because the
session was mocked and one test pinned the broken literal exactly. Fixed
with a sentinel taking its own branch, a pure `purge_statement()` that
PostgreSQL parses in a test, and one savepoint per table. 207,566 rows
due at the next 03:00.

### The document catches up with the box — SNAG-DOCS-001 (2026-08-17)

**The recommendation, taken on the fourth attempt, and wrong on both of
its numbers in a way worth keeping.** `CLAUDE.md` is loaded at the start
of every session here, and since 2026-08-13 it had described the project
domain — gone to estate-manager that day — in the present tense. The
entry said fifteen endpoints and five narratives. Measured: **twelve**
table rows and **nine** narrative blocks, plus six loose sentences that
each read correctly alone and wrongly together.

**The population splits three ways, not two, and that is what a literal
reading of the entry would have got wrong.** `GET /api/projects/managed`
is still **served here** — live `service_health` joined to registry
identity, relocated within this repository by ADR-0005 and keeping its
path. `/overview` and `/{name}` are **consumed** from 8400, parsed with
this repository's own tolerant models under
`tests/test_estate_project_contracts.py`. Only the remaining **nine** are
neither. "Move them all behind pointers" would have deleted a live
route's contract and relabelled a live seam as absent.

**Two blocks were rewritten rather than pointed away**, because the
argument is still ours: `SysAdminAgent._resolve_recovered` (the project
organiser made the case; we still run the statement), and
`core/escalation.py`'s placement — whose stated reason, *`monitor` may
not import `projects`*, **expired with the domain** and has been replaced
by the four climbers it actually has. Leaving a correct conclusion
resting on a dead premise is the trap `SNAG-AGENT-006` records; this is
that trap in a document.

**ADR-0005 was not linked from `CLAUDE.md` at all** — the pointer target
of the whole fix, missing from the index the fix points through. Nor were
0003 and 0004. All three are listed now, and ADR-0001's open question
("who owns project state") is marked answered against this repository.
1,774 lines → 1,684. Suite **1866** green.

**Three things came out of measuring the box rather than the tree.**
`SNAG-AGENT-002` was **fixed on 2026-08-12** and closed on paper here —
its stated remedy is `log_signature.py` verbatim, and the live table
holds 8 unresolved rows against 547,814 for one title six days ago, so
**Session 27 is now only the tiers**. `SNAG-ESTATE-010`: Session 57's
quietening is live and cannot reach the two rows it was written for,
because the family dedups on an open title and only *escalation* has a
resolve-and-re-raise path. `SNAG-DOCS-002`: eight project contract models
with zero readers, four re-exported to the tray. Closed two, opened two;
the snag parser reported 36 → 38, which is `SNAG-ROADMAP-002`
demonstrating itself on the sitting that fixed a documentation snag.

### The holder decides how loud — the ports family's first live rows (2026-08-17)

**The third detector in a row to be corrected by its own first data**,
after `judge_attention` (Session 52) and the other three estate surfaces
(Session 54). `Estate port 3110` and `Estate port 8110` had stood at
`warning` since 2026-08-16 12:07 — one minute after the daemon last
entered active, which is this family's first run ever to raise anything.
`CLAUDE.md` still described it as shipping with zero rows.

Both listeners are Alfred dev servers launched from VS Code —
`nuxt dev` and `uvicorn --reload`, all three pids in
`app-code-oss-26348.scope`. **The estate's finding is literally
correct** (no registry row claims either port) and its remedy is the
half that does not apply: an editor's dev server is not a service the
next project could collide with.

**The defect was not a missing signal.** `Listener.transient` has named
these listeners since Session 26c. `PortReport.unit_ports` skips
`attributed and transient` for `recommendations.py`'s correct reason — a
session scope is nobody's service and a `kind: http` snippet for one
would invent a service — and `unattributed_ports` never held them,
because a session scope *is* attributed. So the port fell out of the
stored blob entirely and `details['holder']` came back `None`,
indistinguishable from 5432's genuine unattributability. That is
`ports_checked`'s rule one layer down: zero-because-clean served as
zero-because-blind.

`transient_ports` is a **separate blob key**, not a flag inside
`unit_ports` — one field whose two consumers want opposite safe defaults
is Session 48's `UnitFinding.enabled` trap, caught this time before it
shipped rather than after.

**Quietened, never suppressed.** `TRANSIENT_HOLDER_SEVERITY = "info"`,
which is the only rung below `tray.notify_min_severity` here, so the row
stays in `GET /api/sysadmin/alerts` and leaves the notification path.
Dropping it was the obvious implementation and rebuilds this family's
founding defect — Session 26b-A exists because a ports breach was
detected, correct, machine-readable and never said out loud. The roll-up
takes the loudest rung it swallows, so six dev servers plus one genuine
unclaimed listener still speaks.

What it removes is a *recurrence*: the tray clears
`notified_this_episode` only on a `{severity}:{title}` pair being absent
from a poll, so closing the editor resolved both rows and re-opening it
raised two fresh `warning` rows with fresh fingerprints — two toasts per
dev session indefinitely, plus one restatement per row per day since
Session 53's `reminder_hours`.

Verified live in-process against the real `ss` (37 listeners) and the
real `:8400/api/audit/findings` (2 breaches, plus the standing 3300
`warn` that is still correctly not judged): the same two rows come out
`info` with `holder=app-code-oss-26348.scope` where they came out
`warning` with `holder=None`. 12 new tests, 1866 green.

`SNAG-ESTATE-009` filed for what it cannot reach — the sweep is
six-hourly and the judge hourly, so a dev server started inside a sweep
window is unattributed and speaks at `warning`. Fixing that means either
a second `ss` caller (which `_attribution` refuses in writing) or six
times the sweep cost for one annotation.

### The snag that was already fixed — SNAG-DB-002 (2026-08-17)

**Closed without a line of code, by measuring the box before reading the
entry.** `SNAG-DB-002`'s remedy half was carried out by **estate-manager**
on 2026-08-13 (`eb51ff6` 18:03, `52b312c` 20:29) using their
`scripts/refresh-collations.sh`, which encodes this entry's own trap:
never `REFRESH` unless that database's `REINDEX` has just succeeded.

**The verification, not the closure, is the content.** Index file mtimes
show the two bursts and prove nothing about an actively-written index,
whose file carries a recent mtime whether or not its contents were
rebuilt. The exact test is `pg_class.relfilenode` against
`pg_class.oid` — a rebuild draws a fresh relfilenode from the
cluster-wide counter, so an index never rewritten retains
`relfilenode = oid`. **0 of 125** collation-sensitive user indexes across
the eight databases retains its original; `projects`' 58 sit in one band,
3,882,764–3,886,294, against creation OIDs from 46,010. "Collation
sensitive" is `indcollation NOT IN (0, 950, 951)`, and it is the filter
the entry lacked — `950`/`951` are `C`/`POSIX`, byte-order, immune to a
glibc change.

**Four of the entry's numbers corrected, three of which were true when
written**: 16 GB (real, largely index bloat the reindex reclaimed, before
the estate dropped `personal_assistant` on 2026-08-14 taking the database
to 1,094 MB — so today's 1098 MB is a deletion, not a mistake); eight
databases (the estate audits eleven); 25 indexes "several on text" (58 in
`projects`, 125 cluster-wide, **0** in `pg_catalog`, whose text columns
are `name`); and a quiet window of hours that was **30 seconds**, because
`REINDEX` rebuilds indexes and 3,123 MB of them was the governing figure,
never the 16 GB.

**Filed on the way: `SNAG-ESTATE-008`** — four documents here restated a
finished ops action for three days and five sittings while this
application's own alert table had resolved all eight rows at 18:01:48 on
2026-08-13. An unread fault is a missed alarm; an unread **recovery** is
an instruction to redo finished work. The cause is structural rather than
careless: `EstateJudgeAgent` is narrowed to `check == "ports"` for two
sound reasons, and shared infrastructure remedied by the estate is the
case neither anticipated. Also corrected: `snag_list.md`'s header claimed
`count_open_snags` reports 47 (measured 2026-08-14); driven against the
current parser it reports **35**, the function having been rewritten
around `read_snags` since — the same defect, one document over.

### The understudy gets a clock — SNAG-TRAY-007 (2026-08-16)

**Session 54's recommendation, taken as written**, closing the last hole
in the arc Sessions 39, 53 and 54 built. `monitor/desktop.py` exists for
the case where the tray is not running, and in exactly that case a
standing fault was announced once and then never again.
`DesktopNotifier.sweep_reminders` gives it the clock it never had,
scheduled as `desktop_reminder_sweep`. Suite **1854** (from 1834), ruff
and mypy clean, no migration, no route.

**The deliverable was the decision the snag asked for, and it came in
two halves.** *Precedence*: `tray_grace_seconds` is the same window on
both paths and the action differs — the raise path skips, the repeat
path **stamps the clock forward**, because a skip leaves
`last_spoken_at` at the opening notification and the first sweep after a
tray outage would restate a fault the tray itself restated ten minutes
earlier. The difference is observable only in the middle window; the
first draft of that test had the arithmetic wrong and passed for the
wrong reason. *Ownership*: a `JobSpec`, not a call bolted to
`SysAdminAgent._execute`, because an agent reminding on the notifier's
behalf is the second-owner defect at a fifth scale.

**Neither number is invented.** `reminder_hours` is the tray's 24 for
the tray's reason, and because two speakers with different cadences make
the interval depend on which was running. The sweep's cadence has no
config leaf at all — `max(60, tray_grace_seconds)`.

**The narrowing is filed, not implied**: `SNAG-TRAY-008`. The population
is what this process announced, so a fault raised while the tray was up
is never adopted and a restart forgets everything — the alternative
being `SNAG-AGENT-005`'s unbounded `SELECT` wired to a notification each.

**Verified live**, because the unit tests mock every session and the
`title IN (…)` clause had never reached PostgreSQL. Against the real
table: the query selected the live title and refused one never raised;
the sweep restated once then held; a synthetic row was restated inside a
roll-up of 2, resolved, and dropped — residue **0** after rollback.
Against a real `BackgroundScheduler`: added at `interval[0:03:00]`,
re-apply retimed nothing, grace 600 retimed it to ten minutes,
`enabled: false` removed it.

**Found sideways**: `SNAG-DOCS-001`, while reading the live route table
for the next-session ranking rather than trusting the documents.

### The other three estate surfaces, against data (2026-08-16)

**Session 53's recommendation, taken as written, and it found what its
framing predicted.** `judge_projects_invariants`, `judge_audit_*` and
`judge_queue_invariants` had never been run against anything but
hand-written dicts. Payloads were built by the producer's own code —
estate-manager's route functions, ORM models, `_streak_starts` age walk,
`CheckResult.as_summary`, `Arbiter.invariants` and `api._public` — driven
in its venv against the live `estate` database inside transactions that
were rolled back (verified after at 7 `scan_runs` / 22 `audit_runs` / 92
`audit_findings`, unchanged). The `ports` breaches are real: listeners
bound on 3900–3905 inside the registry's own audited range, through
`ports.run_check` against the real `monitorable-project.md`.

**The defect a literal is structurally unable to show.** Each rule was
pinned one condition at a time, because that is what a keyword override
produces. The producer cannot separate them: `ScanOutcome.estate_written`
starts `False` and is set near the end of a run, so **every** failing
scan carries `error` *and* `estate_written: False`, and the judge raised
two rows for one fault — the second reading *"The last project scan
completed without rewriting estate.json"* of a scan that did not
complete. Under Session 53's `reminder_hours` that is a false sentence
restated every 24 hours, which is what turned a redundancy into a fix.
The rule is now narrowed to a scan that did not error, making the two
families mutually exclusive by construction.

**A second, latent defect, fixed because it is invisible either way**:
`EstateJudgeAgent._execute` read `open_titles` once, so two judgements
sharing a title in one run inserted two rows and deduplicated only from
the second run. Reachable through `judge_audit_findings` rule 4, which
keeps the `code` out of the title on purpose.

**Two producer-side gaps delegated rather than worked around** —
`SNAG-ESTATE-006` (`AuditFinding` has no `code` column, so
`details['code']` is `None` on every payload the estate can serve, and
the docstring said otherwise) and `SNAG-ESTATE-007` (the arbiter's pool
omits the `-c timezone=utc` its sibling engine sets and documents). Both
carry pre-staged tests or a stated cost rather than a parked task.

**Two rules measured and recorded as unreachable rather than deleted**:
the scan's `finished_at is None` and the audit's `error`, both of which
the producer cannot currently write. Kept, and named in the docstrings so
their silence is not read as health.

Suite **1834** (from 1802), ruff and mypy clean, no migration and no
route. Verified live on the real database in a rolled-back transaction:
raise 7 → hold (0 raised, 0 resolved) → resolve 7, **0 rows of residue**.

### A fault that stands keeps speaking — SNAG-ESTATE-003 (2026-08-16)

**The snag asked for a third rung; the session's first deliverable is
the measurement that a third rung cannot be heard.** Five families
deduplicate on an open row and own no ladder, so each rings once at the
quiet severity and is silent while the fault stands. STATUS.md
recommended *a third rung in `sysadmin/core/escalation.py` with three
callers*. Driven against the real `NotificationPolicy`: the tray
fingerprints on `{severity}:{title}` and clears an episode only when
that pair is **absent from a poll**, which a resolve-and-re-raise inside
one agent run never produces — a resolved row replaced by a fresh one
carrying a new message produced **no notification at all**, where the
same fault escalated to `critical` spoke and a forked title spoke. Two
audible repeats; the second is forbidden, the title being the identity
key for dedup, for the resolve and for the tray.

So a repeat at an unchanged severity is a **notification** decision and
went where notification policy already lives: `reminder_hours` in
`sysadmin_tray/notifications.py`, which covers every deduplicating
family rather than the estate's five surfaces alone. That breadth is the
point — `estate_judge` has produced **two rows in its life**, both
resolved, while the live instance on the day was `service_discovery`'s
`Unmonitored systemd units: 8 findings`, the **only** unresolved row on
the box, open 24 hours and spoken once.

**24 h is derived, not picked**: it matches
`self_monitor.escalate_after_hours`, so a family that owns a ladder
escalates to a different fingerprint — a new episode, spoken at once —
before any reminder of its quiet rung is due. The clock runs from **when
the tray last spoke**, not `alert.created_at` (`stalls.py`'s rule, and
it keeps the one injected clock). A reminder is never transient, shares
the fault's fingerprint and snooze key, and folds apart from new alerts
into `FP_REMINDER`.

**A defect the fixtures were structurally unable to catch**, found by a
probe: `state.first_notified_at or state.last_notified_at` reads a
monotonic `0.0` as absent and falls back to the field every reminder
resets, so each reminder reported the interval ("24 hours") rather than
the age of a fault that had stood three days. `FakeClock` starts at
`1000.0`; the new test starts at zero on purpose.

Both docstrings that had said the omission was deliberate — `estate/agent.py`
and `core/escalation.py` — now say why the alternative was **refused**, so
nobody re-derives the rung. Suite **1802** (from 1792), ruff and mypy clean,
no migration, no route, no backend behaviour change. Follow-up opened:
`SNAG-TRAY-007`.

### judge_attention, against data — SNAG-ESTATE-002's half (2026-08-16)

**An alert family that could not be shown to work.**
`GET :8400/api/projects/attention` has answered `{"health": [],
"nudges": []}` on all four occasions anyone has looked, so every rule in
`judge_attention` was pinned against dict literals written by the same
hand that wrote the consumer. A literal cannot express volume or length,
and both turned out to be wrong.

A populated payload was made from the producer's own code — driven
read-only in its own venv against the live estate database, with
`effective_threshold` forced to 101 and `default_days` to 0 so live rows
qualify, and `dataclasses.asdict` over the producer's own `Nudge`.
Committed as a fixture with its provenance, the two forced numbers
visible in the data.

**Two defects, both rules already written down elsewhere here.** The
family raised **31 rows from one poll** (26 health breaches + 5 nudges),
where the ports family has had `port_breach_max_rows` since Session
26b-A — now `attention_max_rows` (5), per family, since the two fail
independently. And the message ran to **469 characters** into a
notification body that a daemon cuts wherever it likes — now
`truncate_at_word` at 120, marked, with the full text kept in `details`.

`tests/test_estate_project_contracts.py` gains the route as its third,
with the per-entry assertions **pre-staged** to start running the first
day the estate publishes anything, and an assertion that fires when
estate-manager closes its side. Verified live and rolled back: raise →
hold → resolve across three runs, 0 rows of residue.

### One copy of the autogenerate rules — SNAG-DB-003 (2026-08-16)

**The only open item in this repository whose failure mode was data
loss, and it failed green.** `include_object()` in `alembic/env.py` and
`_include_object()` in `tests/test_schema_drift.py` were hand-copies of
each other. The two fail in opposite directions: an exclusion present
only in `env.py` makes the drift guard fail loudly, while one present
only in the *test* is silent — the guard stays green while the next
`alembic revision --autogenerate` writes `op.drop_table` into a
migration whose author was doing something else. Fired in a scratch
script before the fix: with the exclusion removed, autogenerate proposes
`remove_index`/`remove_table` for both frozen tables, against **3,739**
and **4** live rows.

**Session 43 filed it with the design question open, and it answers
itself once ownership is stated the right way round.** `env.py` cannot
import from `tests/`; a shared constant in `sysadmin/` looked like
pushing a testing concern into the shipped package. It is not —
`include_object` is what `alembic revision --autogenerate` uses whether
or not a test suite exists, so this is **production configuration the
drift guard borrows**, and the guard is the second caller.

**It went beside `Base` in `sysadmin/metadata.py`**, not into a new
module, because that file's docstring already argues this exact case for
the *model set*: "a table missing from one copy and not the other is
exactly the silent drift the drift test exists to catch". Which of the
live schema's tables the metadata is authoritative for is the same
question one step further. `COMPARISON_OPTS` travels as one dict, splat
by `env.py` into `context.configure` and by the guard into
`MigrationContext.configure(opts=…)`.

**Widened from the exclusion list to the whole comparison.** The flags
were hand-copied too, and they fail the same silent way: `compare_type`
set in `env.py` and absent from the guard leaves the guard green *while
blind to exactly the drift it certifies*. Six option names now have one
statement between them.

**Not moved, deliberately**: the `SET search_path TO public` both
callers issue. It belongs to the connection rather than to the
comparison — `env.py` pairs it with `CREATE SCHEMA IF NOT EXISTS`, DDL
the guard must never run — and its drift fails in the **loud**
direction, double reflection producing phantom diffs rather than a pass.

**`tests/test_autogenerate_config.py` (5 tests) stops the copy coming
back**, which is a live risk rather than a hypothetical one: the natural
way to add a table to the exclusion list is to edit whichever file you
are looking at. It is an AST sweep over every module — no second
`include_object`/`include_name`, no second `FROZEN_TABLES`, none of the
six option names passed by hand as a keyword or an `opts` key. Textual
because `env.py` **cannot be imported**; it runs the migrations at
module scope. This is the opposite of the assertion Session 43
considered and rejected — not "the two bodies are identical" (which pins
the copy) but "there is no second body".

**Two of the five tests exist so the detector can be seen to fail**, the
vacuity lesson `SNAG-TRAY-006` paid for: one runs the walker at the
owner, which must trip every rule, so a green sweep cannot quietly mean
the path was wrong; one feeds it the code this session deleted. A third
asserts both callers still *import* `COMPARISON_OPTS`, because a file
that configured nothing at all would pass an absence check while taking
alembic's defaults in silence.

**Verified live rather than only against literals.** `uv run alembic
check` reports "No new upgrade operations detected" — which exercises
`env.py` itself, the file no test can import — `alembic upgrade head
--sql` still renders offline mode, and re-adding a test-only exclusion
to the drift guard makes the new sweep fail naming file and line. Suite
**1776 passed** (from 1771), ruff and mypy clean, **no migration**, **no
new route**.

**Found while measuring, and it blocks the frozen-table drop**: the
estate's copy of `project_snapshots` holds **3,713** rows in the window
this repository's table covers, against **3,739** here. The 26 missing
are dated **2026-08-13** — one per project from the final organiser run
at 07:35, after the copy was taken. Recorded on the tasks.md drop entry,
whose own warning ("a copy verified once is not a copy verified twice")
is precisely what this measurement was.


### The reload re-times the scheduler — SNAG-RELOAD-001 (2026-08-15)

**Session 50**, Session 49's own follow-up, closed by **removing** the
divergence rather than reporting it better. The entry offered two
mitigations — store the last `ReloadReport` and serve it, or raise it as
an alert row — and named a third option in its last line. The third
shipped: the first is a field nobody polls (`SNAG-CFG-001`'s shape) and
the second needs a settled dedup and resolve lifecycle before it is
written, while still only *describing* something this repository can
simply not have.

`sysadmin/core/jobs.py` holds the plan — `plan_jobs(config)` maps an
`AppConfig` to the nine jobs it asks for, `apply_jobs` reconciles a
scheduler with it — and `Scheduler` gained `sync_interval`, `sync_cron`
and `remove_job`. The lifespan and the reload now call the **same**
function, so the schedule at startup and the schedule after a reload
cannot be produced differently. `RESTART_ONLY` went from **fifteen leaves
to two prefixes**: `service` and `database`, covering the socket, the
logging setup and the engine.

**The obvious implementation is a line shorter and breaks the schedule.**
`reschedule_job` recomputes the next fire from *now*, so re-applying every
job on every reload leaves a 24-hour job permanently 24 hours from the
most recent reload — which on a box being poked at is never. That is
`agent_first_run_delay_seconds`'s failure with a reload standing in for a
restart. An unchanged trigger is therefore left untouched, decided against
the **live** job rather than a remembered plan: a remembered plan is a
second statement of what the scheduler is doing, which is what the snag
was.

**The guard test was rescued rather than lost**, and rescuing it found a
defect in the guard itself. `tests/test_reload.py` walks the lifespan and
requires every config path it reads to be classified; moving fifteen of
those reads into `core/jobs.py` would have hollowed it out silently. It
now walks both and gained a second half — each `JobSpec`'s declared
`config_paths` must equal what `plan_jobs` actually reads. Writing that
showed the walker treats `delay = schedules.agent_first_run_delay_seconds`
as an alias assignment, which is syntactically identical to one and
semantically the opposite: it dropped a real leaf, silently, which is the
guard failing in exactly the direction it exists to catch.

**1771 tests pass** (from 1733), ruff and mypy clean, no migration.
**Verified live** against the real `config.yaml` and a real
`BackgroundScheduler`, in-process and touching neither the daemon nor the
file: 999 s became `interval[0:16:39]`, `retention_purge` moved 03:00 →
04:00, a disabled `estate_judge` had its job removed and re-enabling added
it back with the first-run delay, and `requires_restart` came back `[]`
where Session 49 reported three leaves.

### The reload path — removing the class, not the instance (2026-08-15)

**Session 49**, `SNAG-UNITS-005`'s durable half. Three sittings running had
handed a restart forward because the daemon reads `services.yaml` once, in
the lifespan. `sysadmin/reload.py` re-reads both configuration files on
`SIGHUP` or `POST /api/sysadmin/reload`.

**The design question was real and its premise was false**, which is the
sitting's finding. It was filed as *"config.yaml, which holds thresholds
the running agents have already read"*. They have not: every agent calls
`get_config()` inside `_execute`, because `SNAG-AGENT-003` forbade agents a
startup hook — a constraint written for event-loop safety that bought
per-run configuration for free. Only **fifteen** leaves are genuinely read
once, and they are enumerable.

**The blocker was privilege, not design.** `sysadmin.service` is a system
unit running `User=gaddi`, so the owner may signal it without `sudo` —
probed with `kill -0`, which tests permission without delivering.
`systemctl reload` would need an `ExecReload=` line and *that* edit does
need `sudo`; the raw signal does not.

**Three decisions taken.** Reload both files and **name what was ignored**
rather than refusing the config half — refusing blocks a threshold fix on
an unrelated edit and the operator restarts anyway. **Both triggers, one
function** — the signal needs no `sudo`, the endpoint is the only one that
can return the report. **Prune per-service state, never reset it** —
resetting re-arms the three-poll degraded streak at the moment an operator
is most likely to be reloading *because* something is failing.

**Verified live on the instance that motivated it**: with Session 48's
three entries removed to stand in for the running daemon, a reload of the
real file reports them `added`, installs all three, and reports
`requires_restart: []`. A broken `services.yaml` beside a valid
`config.yaml` installs **neither**.

**1733 tests pass** (from 1708), ruff and mypy clean, no migration. One
follow-up filed (`SNAG-RELOAD-001`) and one rule finally enforced: nothing
below a composition root may import one, which `metadata.py` had asserted
in prose since Phase 2.

### The execution sitting — the advice, carried out (2026-08-15)

**Session 48.** Three sittings (46, 47, 26c) went into making the
diagnosis speak. This one carried out what it says, and **two defects
surfaced inside an hour** — neither visible by reading the code, both the
same root cause: `recommendations.py` under-reading a `UnitFinding` the
sweep had already filled in.

**The advice never asked whether the unit is meant to be running.** Two
of five `host` snippets named units that are disabled and inactive.
Pasting them declares `kind: systemd`/`kind: timer` checks — which assert
*active* and *armed* — returning `critical` **every 300 s for ever**,
verified against the live box. The pile-up Sessions 41–45 spent
themselves deleting, arriving through this module's own remediation text.
The signal to prevent it was already measured, already stored, and
already trusted by the orphan family for `armed`.

**And `removal_command` left a folded oneshot's timer installed** —
`ticktick-sync.timer`, whose `Requires=` would have pointed at nothing,
and which is the half holding the enablement symlink the command's own
docstring exists to avoid orphaning.

Executed: `garmin-sync.service` removed (the armed orphan, enabled since
February — the emitted command ran **verbatim**), `sysadmin-tray.service`
start limit bounded (systemd's own reading matches the advice's
arithmetic exactly, and `restart_bounded` flips `False → True`), and
three host units wired into `services.yaml`, all checking **`ok`**.

Suite **1708 passed** (from 1701), ruff and mypy clean, no migration.
Blocked and named: five system-scope orphans and the deploy restart need
`sudo` (`SNAG-UNITS-005`); eleven restart-unbounded units belong to other
repositories and stay as advice.

**The collation half was already closed** — all 12 databases read
`datcollversion = 2.44` against a live 2.44, all 8 alert rows `resolved`,
one row each. "8 stale collations" was a stale reading.

### Port collision detection — the half the estate cannot do (2026-08-15)

**Session 26c.** `sysadmin/units/ports.py` reads `ss -H -ltnp` and
`/proc/<pid>/cgroup` and answers the question estate-manager's audit is
*structurally* unable to ask. Their `live_listeners()` runs `ss` without
`-p`, on the stated grounds that *"process names need privileges for
other users' sockets"* — true, and true only of *other users'*. Measured
as `gaddi`: **31 listeners, 24 attributed**, every registry-relevant port
on the box named with its unit **and its scope**, blank only for the
root-owned and containerised ones (5432, 1883, 631, 139/445, 8601).

Suite **1701 passed** (from 1653), ruff and mypy clean, **no migration**
— the block rides in `unit_audits.findings['ports']`.

**There are three port registries here and only one cannot lie.** The
estate's markdown table (18 rows, projects, no units); this repository's
`services.yaml` (11 entries carrying `port:` *and* `systemd: {unit,
scope}` — a hand-declared pair that has existed since Session 35 and had
**never been checked**); and the kernel. This is the only party on the
box holding all three, which is the whole argument for the session.

**Four comparisons in two families, and the split decides the surface.**
`wrong_unit` and `port_shared` are the box disagreeing with itself now —
one alert row per port, port in the title. `duplicate_claim` (invisible
to the estate because `claimed_ports` is a `set`) and `wrong_project` are
a document being wrong while the box is right — ranked advice, last in
`KIND_ORDER`. The armed-orphan split, applied a third time.

**Everything came back clean, which is the expected result and the
honest one.** All 11 declared port↔unit pairs agree with the live cgroup
map; no port has two holders; no registry row is duplicated. *"Nothing on
this box has ever collided"* is now **verified with attribution** rather
than asserted. The one thing the check did find is a registry row: 8500
is given to `sysadmin-service`, which is neither the manifest id
(`sysadmin-assistant`) nor the directory (`sysadmin_assistant`) —
recorded as evidence rather than a finding, because a row may
legitimately name a third-party daemon (`_syncthing_` holds 8384), and
filed as `SNAG-ESTATE-005` for its owner.

**Verified live rather than only against fixtures**, since the family
ships with zero rows — the estate judge's starting position. The whole
agent path ran against the real database in a rolled-back transaction:
the sweep stored the block, and a synthetic `wrong_unit` gave raise →
hold → resolve across three runs with **0 rows of residue**.

**One bug the tests caught that mypy could not.** `select(Alert.title)`
yields the titles themselves, and the dedup read them as `row.title` —
which on a `str` silently returns the bound `str.title` **method** rather
than raising. Every membership test failed, so the family would have
raised a duplicate row on every sweep. Found by the "a standing
collision writes one row" test on its first run.

**`SNAG-UNITS-001` folded in and fixed**, and its own premise is what
changed: it argued a comment was the only honest fix *because* "this scan
does not know the unit's port". True of the sweep; no longer true of its
siblings. The snippet now emits `kind: http` with a real url and port
when the unit holds exactly one audited port. Two limits, both measured:
its population is **empty today** (all 12 port-holding units are
`monitored`, which `classify_units` drops — SNAG-UNITS-002's shape
again), and `/api/health` is right for **4 of 11** declared entries and
wrong for 7. Kept anyway, as `SNAG-UNITS-003`, because a wrong url fails
loudly within one poll where `kind: systemd` under-monitors silently for
ever.

### The restart-limit family — 13 units advised on, none of them alerted (2026-08-15)

`SNAG-UNITS-002`. 17 of the 20 hand-written units on this box that
declare `Restart=` have a start limit their own restart cadence can never
reach, so a crash loop never enters `failed`, no `OnFailure=` hook can
fire, and `systemctl is-failed` reports nothing wrong. That is the
estate-wide form of `SNAG-ESTATE-001`, whose two PersonalAssistant units
restart-looped 52,178 times in exactly this state. Suite **1653 passed**
(from 1631), ruff and mypy clean, no migration — the family lives in the
audit's JSONB blob.

**The detection already existed and had done since Session 46.**
`restart_is_bounded` was written for the armed-orphan family and every
finding has carried `restart_bounded` since. What did not exist was any
surface naming the units, and the reason is the measurement nobody had
taken: **11 of the 13 are `monitored`**, and `classify_units` drops
monitored units before they become findings. The question "which units
here can loop for ever" was answerable for the six the sweep already
described and invisible for every live service on the box — the snag's
own entry costed the fix as "one line per unit" without noticing that
two thirds of the population had nothing to hang a line on.

**Measured live rather than inherited**, and the entry's figures moved
again: 17 of 20 unbounded, of which 11 `monitored` (`venture-*` ×4,
`sportsanalyser-*` ×2, `alfred-inference`, `estate-manager-api`,
`estate-manager-searxng{,-shim}`, `sysadmin-tray`), 4 `orphaned`, 2
`host`. The family ships with **13**, not 17.

**Orphans are excluded, which is the opposite of the obvious rule.** A
broken unit that also loops reads like the worst case and belongs here
twice over. It cannot: the orphan recommendation is *remove it*, and a
start limit on a file you should delete is two contradictory
instructions for one unit. Nothing is lost — an armed orphan that loops
is exactly what `armed_alert_severity` already promotes to `critical`.

**Advice-only, and the count rides in the roll-up's `details` as
evidence.** Deliberately *not* added to `scan.actionable`, which is the
roll-up alert's title and the number `alert_threshold` is compared
against: 13 latent risks there would trip the threshold on their own and
would read as 13 new units to wire up. No alert family of its own, for
the reason the armed split was worth making — one row per unit is right
for a fault in progress and wrong for a latent one.

**Ranked second, above `unmonitored`**, because the two are competing
safety nets and this is the stronger one: a wedged unit is seen as
`unreachable` only if something polls it, whereas a reachable start limit
makes systemd itself say so, to a hook, whether or not this service is
running.

**The suggested window is checked against the arithmetic that produced
the finding.** `suggested_start_limit_interval` picks the smallest round
value clearing `RestartSec x (burst - 1)` by 1.5x, and a test feeds every
live shape back through `restart_is_bounded` and requires `True` — a
remedy that clears a symptom without fixing the fault is the trap
`REFRESH COLLATION VERSION` set for the collation family. A second test
appends the emitted snippet to a real unit file and re-scans, which is
the only thing proving the two lines land in a section systemd reads
them from. Where no window would help (`RestartSec` beyond an hour,
`infinity`) it emits **no snippet at all** and says to lower `RestartSec`
instead.

**The first snippets this repository has emitted for a file another
repository owns.** `snippet_target` is the absolute unit path rather than
a filename so the two destinations cannot be confused, and the `detail`
names the owning project — 11 of the 13 belong to four other
repositories. It stops at text served over a GET, which is a pointer.

**`UnitFinding` now carries the three numbers the verdict was computed
from** (`restart_sec`, `start_limit_interval`, `start_limit_burst`).
Without them the boolean asks a reader to trust arithmetic they cannot
see, and the naive version of that arithmetic is wrong in both
directions.

**Verified live, end to end**: the real sweep written to `unit_audits`
and read back through the router's rehydration in a rolled-back
transaction — blob carries `restart_unbounded_count: 13`, the arithmetic
inputs survive JSONB, and `/actions` builds 25 recommendations (6 orphan,
13 restart, 1 unmonitored, 5 host). Residue 0.

**What is deliberately not done**: nothing here edits a unit file, and
the two `deadlock-api-ingest` twins get scope-suffixed titles because
they are two different binaries under one name — the `host` tier still
prints that pair with identical titles, which is pre-existing and
untouched.

### SearXNG wired — the deploy-triggered guard closed the same day it fired (2026-08-14)

`test_searxng_wiring.py` went red on 2026-08-14 when estate-manager
deployed SearXNG, which is precisely what it was built to do, and the
gap was closed the same day. `services.yaml` now carries the entry.
Suite **1631 passed, nothing skipped, nothing red** (was 1627 passed,
1 failed on purpose, 1 skipped); ruff and mypy clean; no migration.

**Every handed-over value was verified rather than copied**, and one of
them was wrong in the direction that would have mattered. The pre-staged
block named `/healthz`; the shim proxies unknown paths upstream, so
`http://localhost:8600/healthz` reaches SearXNG's own liveness ping and
returns **200 whenever the container is running — including when every
search fails**, which is the one case `kind: http` was chosen to catch.
It answers 200 today, so that wiring would have looked right on the day
and been blind on the day it mattered. The live entry polls
`/api/health`, the only path that knows whether searching works.

**The status ladder was driven, not read.** `_check_http` was run
against a real socket returning each code: 200 → `ok`, **424 →
`degraded`** (SearXNG up, searching broken — a fault off this box),
**503 → `critical`** (container dead). `_handle_status` already requires
three consecutive degraded checks before raising, so the estate's "worth
an alert only if it stands" needed no work: a captcha'd engine is silent
for 15 minutes, a standing outage is not. Live check against the running
shim: `ok` in **23 ms**, `status: healthy`, probe 153 s old, 20 results,
no unresponsive engines.

**A second entry the plan did not ask for.** `searxng-upstream` declares
the 8601 container `monitor: false` with a reason. Its health is already
covered by the shim's 503 and a second check would give one fault two
alert rows — but omitting it from the file put it in the unit sweep's
`host` findings *permanently*, unactionable, with "watched through the
shim on purpose" indistinguishable from "nobody wired it up".
`venture-chat-large` carries the same shape. Host findings 9 → 8.

**Item 3's rationale was narrowed, not inherited.** The no-`project:`
rule was written on "third-party software with no repository"; the shim
that actually serves the URL is estate-manager's code and *does* have a
manifest, so the field would now resolve. The omission stands on
narrower ground, decided by the owner: this entry judges whether
**searching** works, and a 424 is upstream engines failing off this box
— not the estate-manager repository's fault to carry.

**The guard changed shape rather than retiring.** Its gate now separates
environments rather than dates: CI has no searxng unit, so the three
assertions skip there and run here against the live box, where before
they skipped everywhere and the file was unfalsifiable. The `kind: http`
assertion is **stronger** — it asserts *exactly one* searx entry is
checked before asserting that one is HTTP, because merely skipping
unmonitored entries would let someone silence the family by muting the
shim and still pass. Both real unit names are pinned into the gate's
cases: **neither is any of the three spellings it guessed**, so the
substring match is the only reason it fired.

**Not deployed.** `sudo systemctl restart sysadmin.service` needs a
password this session could not supply; the daemon holds `services.yaml`
in a process-wide singleton, so the entry is inert until that runs.

### Session 26b-A: the estate's port findings get a voice (2026-08-14)

The estate has reconciled its port registry against the box's live
listeners since 2026-08-13, correctly, and **nothing on this box ever
said so**. `judge_audit_findings` now judges the audit's `ports` check
per finding. Suite **1626 passed, 1 skipped** (+29), ruff and mypy clean.
No migration.

**Most of the session was checking whether the plan was still true, and
it was not.** Session 26b was scoped on 2026-08-07; `estate-manager` was
created on 2026-08-11 and built its conformance audit on 2026-08-13.
Three of its four checkboxes had been overtaken:

- **Item 1 inverted.** "Move the registry into `config.yaml`, render the
  guide's table from it" — but the guide moved to estate-manager, and
  its audit now *parses that markdown table as its source of truth*, with
  a guard that errors rather than reporting zero findings on an empty
  parse. Mirroring the registry here would break their check and have the
  monitor own a cross-repo convention. **Killed, not deferred.**
- **Item 2 was already built** and has earned its keep — the
  `unclaimed_listener` breach is how syncthing's 8384 got a registry row
  on 2026-08-13.
- **Item 3 was delegated** to estate-manager as `SNAG-ESTATE-004`.
- **Item 4 is genuinely ours** and became Session 26c.

**What replaced them outranked all four.** The estate files findings and
never alerts; `judge_audit_invariants` deliberately judged only whether
the audit *ran*. So a `breach` was detected, correct, machine-readable,
served at `:8400/api/audit/findings` — and unread. That is precisely the
shape Session 46 spent itself removing for units one day earlier
(*"the diagnosis was complete, correct and machine-readable the entire
time; a count is not news"*), reproduced one layer up.

**The narrowing of rule 3 is exact, not a reversal.** Both of its
original reasons still exclude what they excluded, and the filter is
`check == "ports"` rather than a severity because **all four** estate
checks emit `breach`: a severity-only rule would re-import the collation
family this service already raises (its own alerts through a second
producer) and pull in `pointers`/`seams`, which are other repositories'
conformance. Ports are the exception because **no repository owns a
port** — and since the estate may not alert, the choice was never who
speaks but whether anyone does.

**Three rules that were the opposite of the first draft.** `warn` is not
judged — `claimed_but_silent` is availability, which `services.yaml` plus
the `% unreachable` family already owns, and that today's one live `warn`
(port 3300) does not overlap is luck, its registry row reading "unit to
follow". Above `port_breach_max_rows` the family **collapses to a
roll-up**, the inverse of Session 46's rule and its complement: six
unclaimed listeners at once is a table moved or truncated, not six
services. And `audit_invariants`/`audit_findings` are **two surfaces**
though they come from one check run — two HTTP calls that fail
independently, and the sweep is scoped per surface, so sharing an id
would let "the audit completed" close port rows raised off a payload
nobody received.

**Verified against the real detector, not only literals**, because this
family ships with **zero live rows** and that is `SNAG-ESTATE-002`'s
starting position. The estate's own `run_check` was driven in-process
against the live registry document with a listener bound on 8888:
clean → `breach` → clean, no write to the estate's database. It caught
one defect no literal would have — the estate stamps a first sighting
`standing_days: 0.0`, and "Standing 0 days" reads as a rounding artefact.

**Two corrections made in passing.** Session 26b's last checkbox named
`sysadmin/services/units.py`, gone since Session 35's module split (the
same stale-path defect as commit `ce71bef`); and this snag list's header
claimed `count_open_snags` reports 15 — it reports **47**, measured
against the estate's parser, which is also no longer in this repository.

### The unit sweep learns to speak — SNAG-ESTATE-001's durable half (2026-08-14)

An orphan finding no longer waits to be fetched. The sweep now measures
whether an orphan is **armed** — systemd will start it — and each armed
one gets its own alert row naming the unit and scope, beside the roll-up
rather than instead of it. Suite **1597 passed, 3 skipped**, ruff and
mypy clean. No migration.

**The failure was never detection.** Both PersonalAssistant units were
classified `orphaned` with the dead path and the cause in plain English
eight days before anyone looked, and `Unmonitored systemd units: 17
findings` was open the whole time. A count cannot name the thing that is
on fire.

**The obvious rule for "will it loop" was wrong in both directions**, and
the live units refuted it before it was written.
`personalassistant-backend.service` declares no start limit, so systemd's
defaults apply — one *does* exist. It also sets `RestartSec=10`, so five
starts can never fit inside the ten-second window: the limiter is
unreachable and it restarted 34,517 times without once entering `failed`.
Meanwhile a bare `Restart=always` restarts every 100ms, five starts fit
easily, and the loop terminates. The real test is arithmetic —
`RestartSec × (StartLimitBurst − 1) < StartLimitIntervalSec` — the same
sum Session 39 did by hand for `sysadmin.service`.

**Both signals are pure**, so `scan.py` keeps its no-subprocess promise:
an enablement symlink under a `*.wants/` directory it already walks, and
four keys of unit text it already parses. Agreed with `systemctl
is-enabled` on every unit on this box.

**Live: 1 armed orphan of 6** — `garmin-sync.service`, one `warning` row.
The four `Restart=always` orphans are harmless only because someone
disabled them, so they stay in the roll-up as debt. Verified in a
rolled-back transaction against the live database: five runs of one fault
wrote 2 rows (raise, dedup, escalate, hold, resolve), roll-up untouched,
residue 0.

**Filed, not fixed: `SNAG-UNITS-002`** — *fixed 2026-08-15, see the top
of this section.* 15 of the 18 units on this box with a `Restart=` policy
cannot reach `failed`, including every live service except `sysadmin`,
`alfred-backend` and `alfred-frontend`. Not alerted on — 15 rows on the
first run is the pile-up shape wearing a new hat. (Both figures moved
before the fix landed: 17 of 20 by the next morning, because the defect
is what a correctly-written unit gets by default here.)

### SearXNG pre-staged — a delegated requirement made mechanical (2026-08-14)

The estate's SearXNG task **stays unchecked**: the trigger is
estate-manager deploying it and claiming a port, and it has not fired —
no unit on either bus, nothing listening, no registry row. So the
`services.yaml` entry cannot be written, because `url` and `port` are
the deploy's to decide. Pre-staged at the owner's request. Suite **1546
passed, 3 skipped**, ruff and mypy clean.

**The commented block is the smaller half.** It sits in `services.yaml`
beside `mosquitto` with every decided field and `<PORT>` where the two
unknowns go. But the failure this item exists to prevent is *a unit
ships and nobody notices*, and a comment does not prevent it —
`tests/test_searxng_wiring.py` does. It skips while no searxng unit
exists and fails from the moment one does, gated on the **unit file**
rather than a port probe (a probe flips off exactly when the service is
down) and matching the substring `searx` rather than one spelling (a
container deploy names its unit `podman-searxng.service`). Nine ungated
tests drive the gate against a fake estate under `tmp_path`: a gate that
has never fired and a gate that cannot fire look identical from outside.

**One part of the task was already enforced; another was at risk from
the thing enforcing it.** The Session 26 unit sweep catches a
hand-written searxng unit unaided, files it `host`, and omits `project:`
— so that decision needs nobody to remember it. Its snippet says
`kind: systemd` though, because the scan cannot know a port, and a unit
check passes a SearXNG that is up while every search errors. Following
the sweep would have *appeared* to close the item. Filed as
`SNAG-UNITS-001`. Fixed in passing: an `unmonitored` finding's `reason`
named `projects.yaml` and `config.yaml`, two files that no longer exist,
in a string the operator reads.

### Session 46 — three snags, and one of them had bad advice in it (2026-08-14)

`SNAG-AGENT-006` fixed, `SNAG-TRAY-006` fixed, `SNAG-ESTATE-002` handed to
the repository that owns it. Suite **1537 passed**, ruff and mypy clean.

**The snag entry's own remedy was wrong, and following it would have
undone SNAG-AGENT-004.** It said dedup and `RESOLVABLE_TITLE_PATTERNS`
are mutually exclusive, so the service and threshold families had to
leave the tuple — which would have stranded every deconfigured service's
rows again, since a set built from configuration cannot contain a service
that has left it. That mutual exclusion held only of an exclusion set
made of the titles a run **raised**. `sysadmin/estate/agent.py` had
already shown the third option and Session 45's handoff named it: exclude
what the run **judged**. Dedup suppresses the raise, never the judgement.
The patterns stayed; `_raise_judged` is the whole fix.

Two corrections fell out of it. `% auto-restarted` is exempt via an
explicit `dedup=False` — `_failure_counts` resets the moment
`restart_unit` returns, so it fires once per restart *cycle* and a second
restart hours later is news that dedup would swallow. And the recorded
reason `collation` stays out of the sweep was itself wrong: the real
reason is that it resolves its own rows by id, not mutual exclusion — a
correct conclusion drawn from a premise that has since moved, which is
the kind that gets a guard removed later for the wrong reason.

**Verified against the live database, rolled back**, because the suite
stands in for PostgreSQL's `LIKE` with a Python matcher and cannot prove
the patterns select the right rows in real SQL: ten sustained runs of one
threshold fault left **1** row where the old code wrote 10; three
auto-restarts left 3; residue 0.

`SNAG-TRAY-006` got a consumer-driven contract test — a recorded 8400
payload plus a reachability-gated live pair sharing one set of
assertions. `estate-lib` was rejected: the two shapes are a *tolerant
consumer parse* and a *producer guarantee*, different jobs, and one class
would make the tray's defensiveness the producer's problem. The design
work was the vacuity — `from_dict({})` **succeeds**, so "does it parse"
would go green against a producer serving nothing.

`SNAG-ESTATE-002` was recorded in estate-manager (as its
**`SNAG-ESTATE-010`** — the IDs are per-repository and that repo already
has a different `002`) and fixed nowhere, per its ADR-0002. Reading the
producer turned up three things the entry did not have: the drift has
**already happened** (`Nudge.message` shortens the action to 120 chars,
this side interpolates it whole), `nudge_title` has **no production
caller** in that repository at all, and its justifying comment cites a
symbol that no longer exists there.

Also closed: Session 45's two time-boxed checks. Both estate timers fired
overnight, so `estate_judge` correctly stayed silent and **has still
never raised a row in production**; `/api/projects/attention` is still
empty even after a scheduled scan, so `judge_attention` remains
unexercised against real data. Filed on the way: `SNAG-AGENT-007`.

### Session 45 — the judging session (2026-08-13)

`estate_judge`, a fifth agent, closes the half of the Session 4 cutover
that was deliberately left behind: the estate manager publishes and never
acts, and until this ran it computed idle nudges every night into a
surface nothing read. **Four surfaces, not the two the task named** —
the scan's invariants and `attention` as planned, plus the audit's
invariants (estate ADR-0009 requires sysadmin to judge them: "the estate
never grades its own audit") and the queue's (ADR-0007; `services.yaml`'s
own comment already called that ours to judge). Hourly.

**The lifecycle is the interesting part.** `collation.py` records that
dedup and a set-based resolve are mutually exclusive, and they are —
*there*, because that sweep excludes the titles the run **raised**, so a
deduplicating family has its still-true row resolved and re-raised on
alternate runs, clearing the tray fingerprint each time. This agent
excludes the titles the run **judged**, which is a different set, and it
can do that only because it owns every row it sweeps.

**Three rules taken against the obvious implementation**: a cumulative
total is never judged (`dropped_total` is already 1, so a `> 0` rule
raises an immortal row — `redis unreachable`'s 6,283 by a fourth route);
the sweep is scoped to the surfaces the run actually read, so a partial
pull cannot announce a recovery from a payload nobody received; and
unreachability is not judged at all, because `estate-manager-api` is
already an `http` entry in `services.yaml` and a second owner of one
lifecycle closes a row while the first still holds it true.

**Verified live** in a rolled-back transaction against real 8400
payloads: run 1 raised 3, run 2 raised 0 and resolved 0 with all 3 still
open (the flip-flop that had to be avoided), restoring thresholds
resolved exactly 3, and a dark surface resolved nothing. Residue after
rollback: 0 rows.

Found on the way and fixed: `Alert.__table__`'s `chk_alert_agent` had
never gained `service_discovery` from migration 007 — alembic does not
diff CHECK constraints — and `test_units_api.py` pinned `AGENT_NAMES` to
migration **007** by set equality, so every new agent broke an unrelated
session's test. Split into a fact about 007 and a self-locating invariant
against the newest widening migration.

Filed rather than fixed: `SNAG-ESTATE-002` (the producer's `Nudge.title`
and `.message` are `@property`, so `asdict` drops them and this
repository builds a format the estate believes it owns) and
`SNAG-ESTATE-003` (no escalation for these families).


- **2026-08-13 — Session 44: the collation check (`SNAG-DB-002`).** A
  glibc upgrade moved this box from locale data 2.43 to 2.44; PostgreSQL
  has been printing a mismatch warning on every `psql` connection since,
  read by nobody, while any B-tree index on text sits built against the
  old ordering — a lookup can miss a row that is present.
  `sysadmin/monitor/collation.py` reads `pg_database` once per sysadmin
  run and raises `Stale collation version on <db>` at `warning`. The
  snag said three databases; the catalog says **eight of eleven**, because
  the original number came from the databases someone had opened a shell
  against. Four rules, three of them the opposite of the obvious
  implementation: it fails **open** on NULL (deliberately the reverse of
  `schema_guard` — `template0` records no version, and inventing an alert
  whose remedy does not exist is the worse error here); it raises **once
  per open row**, because 300-second polling against a fault that
  persists for weeks would write 2,304 rows a day; and it therefore stays
  **out of `RESOLVABLE_TITLE_PATTERNS`** — dedup and that sweep are
  mutually exclusive, and combining them makes a row flip-flop, clearing
  the tray fingerprint on every flip. The `REINDEX` remedy is
  deliberately not automated and the alert names it **before** `REFRESH`,
  which alone would silence the warning without rebuilding anything —
  *and estate-manager automated exactly that ordering in
  `scripts/refresh-collations.sh` and ran it the same evening, which is
  where the remedy half of `SNAG-DB-002` actually closed.*
  Verified live in rolled-back transactions, both raise and resolve,
  residue 0. Filed on the way: `SNAG-AGENT-006`, the raise-side twin of
  `SNAG-AGENT-004` — 60 rows for one dead timer in five hours.

- **2026-08-13 — Session 43: `SNAG-DB-001`'s detection gap, all three parts.**
  The un-applied migration that blacked out monitoring for 39 hours was
  fixed on 2026-08-10 by applying it; the reason nobody noticed was the
  real defect, and it is now closed. **(1)** `sysadmin/core/schema_guard.py`
  compares `alembic_version` against the packaged head at startup and
  **refuses to boot** on a mismatch — not wrapped in a `try`, so the unit
  enters `failed` and `sysadmin-failed.service` announces it, making this
  the Session 39 machinery's second caller. The head comes from alembic's
  own `ScriptDirectory` rather than a regex over the version files, and
  `alembic_version` is read schema-qualified because the `projects`
  database holds another application's copy in `public`. Verified live:
  passes at 011/011, refuses a forced mismatch naming both revisions and
  the remedy. **(2)** One `session.begin_nested()` per service in
  `SysAdminAgent._execute` — load-bearing *because leaving the block
  flushes*, since `session.add` never talks to the database and the
  rejection previously surfaced at the single commit ending the run. A
  rejected service is recorded as `status="error"` rather than costing
  the other eighteen their check. **(3)** `sysadmin/monitor/failures.py`,
  a **sibling** of `stalls.py` on the shared ladder, not an extension of
  it: "has not run" and "ran and failed" are different states with
  different remedies, and the suffix `agent failing` is chosen so
  `_resolve_recovered` cannot reach it. **The threshold is a count of
  runs, never a duration** — the opposite unit from `escalate_after_hours`
  in the same config section, because `agent_runs` records a run rather
  than a schedule. Part (3) **was not implementable when the snag was
  filed**: before Session 41 a failed run left no row, so there was
  nothing to read. 61 new tests. One new snag filed at the estate-manager
  session's request — `SNAG-DB-003`, the autogenerate exclusion list
  hand-copied across `alembic/env.py` and `tests/test_schema_drift.py`,
  where the dangerous direction is silent: an exclusion present only in
  the test leaves `--autogenerate` willing to write `op.drop_table` for
  frozen data.

  _Ran alongside estate-manager's project-state cutover, which was
  editing this repository concurrently under the founding-extraction
  exception. `docs/adr/0005-project-state-leaves.md` arrived from that
  session, not this one._

- **2026-08-12 — Session 42: the log storm, fixed as a raise rule.**
  `SNAG-AGENT-005` — **598,091 unresolved alert rows**, 91 % of every
  unresolved alert in the table, 99.8 % of them two Bluetooth firmware
  messages from a kernel retry loop running at ~8.5 lines a second. The
  agent raised one alert row per matching log line, which is the mistake
  this application had already written down once, in
  `GET /api/services/reliability`'s docstring: a log is not an incident.
  The `SNAG-AGENT-004` inversion does not apply — a log line that was
  written cannot un-write itself, so "which open alerts would this run not
  raise?" answers "all of them, one run later". **Alerts are now keyed on
  a normalised fault signature**, one open row per fault, repeats bumping
  `details['occurrences']`, resolved when the fault goes quiet for 15
  minutes. Plain dedup on the existing title was refuted by the live table
  before it was written: `Log error: kernel` is shared by every kernel
  error, so the storm would have masked the RCU stall and the USB
  enumeration failure sitting in the same 30-day window. Verified live:
  **2,000 kernel error lines in ten minutes → 2 alert rows**, and the
  titles finally name the fault. The 598,091 existing rows were resolved
  as `superseded`; table-wide unresolved alerts went to **2**. Two smaller
  defects went with it — journal reads now resume from `__CURSOR` rather
  than re-reading a 2-minute window on a 60-second poll (**96 entries then
  0** on back-to-back runs, where every entry used to be stored twice), and
  the silent `-n 500` cap is reported as `details['truncated_sources']`.
  **`sysadmin.service` still needs restarting to pick this up** — it is a
  system unit serving start-time code.

- **2026-08-12 — Session 41: the two P1 agent defects, both with the filed
  cause corrected.** `SNAG-AGENT-003` — the file organiser having run once
  in its life — was neither of the two candidates the entry named. The
  scheduler fires and the agent *succeeds*: `BaseAgent.run` opened a
  transaction (insert + flush of the `running` row) before handing the same
  session to `_execute`, and this host sets
  `idle_in_transaction_session_timeout=1min`, so a 117.71-second scan had
  its backend terminated at t+60s and lost every write **including its own
  failure record**. The one surviving run, 2026-08-06, took 29.63 s — the
  only one ever to finish inside the timeout. `run()` is now three
  transactions and a failed run records that it failed.
  `SNAG-AGENT-004` was diagnosed correctly and **understated by about twenty
  times**: 27,827 rows for five retired services (not four — `nuxt-frontend`
  was missed) *plus* 24,097 resource-threshold rows that had no resolve path
  at any point in this application's life, `Critical disk usage on /` alone
  holding 13,971 open rows against a disk at 68 % since July.
  `SysAdminAgent._resolve_recovered` closes both families set-based;
  **51,924 rows in the population**, verified against the live table, with
  the only `agent='sysadmin'` row left open being the file organiser's
  stall. **Both were deployed and proven the same day**: the file organiser
  recorded 3 completed runs against **one in its entire life** before today,
  `filesystem_audits` went 1 row → 4, and **51,976 alerts resolved**, taking
  `agent='sysadmin'` unresolved from 51,925 to **43**. 1,939 tests green (+35).

- **2026-08-11 — Session 39's MQTT half unblocked, from the other side.**
  estate-manager's Session 2 (its founding MQTT extraction, executed
  under estate ADR-0002's bounded exception) removed both walls recorded
  below: Alfred's `reconcile()` now deletes only subscriber-role clients
  with no live token (Alfred ADR-0068), and the neutral root is live —
  `sysadmin-publisher` exists with role `estate-publisher` (write
  `estate/#`), provisioned from `estate-manager/mqtt/dynsec.yaml`, and a
  publish on `estate/alerts/test` reached a subscriber-role client with
  the identity surviving an alfred-backend restart. This repository's
  side: `sysadmin.service` gained
  `LoadCredential=mqtt:/etc/credstore/sysadmin-mqtt`
  ([ADR-0003](../adr/0003-mqtt-credential-by-loadcredential.md) — why
  not `config.yaml`, not an `EnvironmentFile`), pinned by a new
  `test_systemd_units.py` invariant; `services.yaml` gained
  `estate-broker-provision` (the estate's boot oneshot, `scope: system`)
  and — found while wiring it — **`mosquitto.service` itself, which was
  unmonitored**: a dead broker means alerts publish nowhere while every
  consumer reconnect-loops silently. The publisher code stays this
  repository's own open task; the credential file and unit install land
  with estate-manager's `scripts/install-broker-system-units.sh` (one
  sudo run, which also covers the Session 39 unit install below).

- **2026-08-11 — Session 39 (part 1): the alarm now keeps ringing, and the crash case can reach `failed`.** Two of the six scoped items shipped; MQTT publishing is blocked on an Alfred-side change and is written up below. **Detection was not touched, deliberately** — not one line of `self_monitor.py` changed, because it was never broken.

  **The escalation ladder.** A stalled agent is raised at `warning` exactly as before, and re-raised as `critical` once that warning has stood unresolved for `self_monitor.escalate_after_hours` (24). The shared half — `SEVERITY_ORDER`, `Ladder`, `step_for` — went into **`sysadmin/core/escalation.py`**, because the scoped instruction "reuse `nudges.py` rather than copying it" was not possible as written: `sysadmin/monitor` may not import `sysadmin.projects` (`tests/test_import_boundary.py`). Same move `strip_markdown` made into `core/text.py`, same reason.

  **Why `critical` specifically, and it is not about volume.** `sysadmin_tray/notifications.py` sets `transient=effective == "info"` on a first notification and `transient=False` only inside `_maybe_escalate`, which fires for `critical` alone — so **`critical` is the only severity the tray leaves on screen**. The owner's diagnosis was "I never saw the toast", away from the machine; a `warning` toast expires whether or not anyone was in the room. The second rung buys *persistence*, which is exactly the failure described. This is the opposite of the rule `nudges.py` encodes (a nudge never reaches `critical`, because criticals pierce DND and waking someone about a roadmap item is how a monitor gets muted wholesale), and the two docstrings now cite each other so the difference cannot read as an oversight.

  **The clock starts when the alarm rang, not when the stall began** — the open row's `created_at`. Both were computable and the obvious one is wrong twice over: it is the *telling* that failed, so the telling is what should be measured; and anchoring to the stall's own age would make a daemon outage produce **a wall of criticals on restart**, since nothing runs while the service is down and the first check back would escalate all five agents at once. That charges the estate for this application's downtime — the rule `GET /api/services/reliability` already encodes as "a gap in the series never costs points". **24 hours is measured against the slowest agent, not the fastest**: `file_organiser` and `service_discovery` run daily, so a stall that is merely late clears within one interval and a shorter gap escalates faults about to fix themselves.

  **The crash case, and the number that de-risked it.** `sysadmin.service` was `Restart=always` with no limit, so a crash-loop sits in `activating (auto-restart)` for ever and **never enters `failed`** — the state every failure hook watches. `StartLimitBurst=5` / `StartLimitIntervalSec=600` makes a loop terminal; `sysadmin-failed.service` announces it via `scripts/notify-unit-failed.sh`, persistently (`--expire-time=0`, `--urgency=critical`) and **to journald first**, that being the one destination which does not need anyone logged in. The trade — infinite retry rides out a slow dependency, and this app does exit rather than degrade when the database is absent (`verify_connection` raises in the lifespan) — was **measured before the edit, not assumed: `NRestarts=0` and zero "Scheduled restart job" entries in 30 days of journal.** The retry has never once fired here. The rollback, including the `systemctl reset-failed` that is easy to forget, is written into the unit file rather than a session note, and the handler was rehearsed rather than trusted. `tests/test_systemd_units.py` pins the halves together — either alone accomplishes nothing, which is the shape of half-change this repo has shipped before.

  **MQTT is blocked on Alfred, and on something the scoping session did not find.** The premise checked then was alfred-glance's closed renderer registry — real, but secondary. Mosquitto here is `allow_anonymous false` running the **dynamic-security plugin**, whose schema Alfred owns, and **`dynsec.reconcile()` deletes every client that is not Alfred's admin, not Alfred's publisher, and not a live device token.** A `sysadmin-publisher` created by hand survives until Alfred next restarts and is then deleted — best-effort, logged at `info`, no alert. For an *alerting* path that is this session's own bug reinstalled inside the fix. Decided: **Alfred provisions a protected non-device publisher, in its code.** And the namespace decision costs more than scoped — both dynsec roles are scoped to `alfred/events/#`, so the chosen neutral root (`estate/…`) is **denied by the broker** until those roles gain a filter. Terms of the promotion are now in [estate-map.md](../guides/estate-map.md), which had reserved this decision in writing.

  **Verified in production the same day.** The units were installed at 17:08 and the ladder fired on the very stall that motivated it: the `warning` raised 2026-08-10 09:07 is now resolved, replaced by a `critical` at 17:13:12 carrying `escalated: true` and `hours_since_first_alert: 32.1` — which the tray renders as a notification that stays on screen instead of the toast that was missed. A **unit failure now also leaves state**: `sysadmin/core/unit_failure.py` writes a critical row through the sync engine (the application is dead by definition — no event loop, no scheduler session, nothing subscribed), filed under `agent='sysadmin'` with `details.source = systemd_onfailure` carrying the provenance the constraint's five allowed names cannot express. **Paired with a resolve in the lifespan**, because the service starting *is* the recovery and nothing inside ever observed the failure; without that half it is an alert type that can only accumulate. Both directions verified against the live database.

  Two snags found sideways and recorded rather than fixed: **`SNAG-DB-002`** (every database on this box has a stale collation version — glibc 2.44 against `datcollversion` 2.43, 25 indexes in the `sysadmin` schema, and the `REFRESH` that clears the warning without rebuilding is the trap) and **`SNAG-SYSD-003`** (`After=ollama.service` on a runtime retired 2026-07-24, left in so the unit change kept one rollback path). `SNAG-AGENT-003`'s **second half is addressed** — the alert would have gone persistent on 2026-08-11 09:07 instead of staying a single toast — while its first half, the file organiser that has run once in its life, is untouched and still has two unseparated candidate causes.

- **2026-08-11 — Session 36: the briefing envelope, and the staleness check that can never fire.** `GET /api/sysadmin/briefing/preview` now carries `schema`, `period`, `summary`, `alerts[]` and `facts{}` **alongside** the `sections` and `generated_at` it always had. Additive was the delivery decision and it was not a compromise: Alfred's `adapt_sysadmin` reads `payload["sections"]` and returns one red error section if it is missing, and the spec's literal shape had neither `sections` nor `generated_at`. The spec's own sentence resolves it — "prose is what Alfred surfaces, `facts` is the deterministic input the prose was written from" — because **`sections` are the prose**. Alfred owns the section contract by its ADR-0063; this service owns the envelope round it. Rejected: an envelope-native second endpoint (two payloads where one gets updated is the drift this repo keeps filing snags about) and a coordinated breaking change across two repos. No `generated` key was added beside `generated_at`; two stamps holding one value is a fork waiting to happen.

  **The measurement the session was asked to make turned out to be the feature.** Checkbox 6 asked whether Alfred enforces staleness on the generation stamp. It does — `_producer_timestamp` carries `generated_at` into `produced_at` and `DigestSection.vue` flags a 12-hour gap — and the check is **structurally incapable of firing here**, because this is a *pull* endpoint: the payload is stamped at the moment the request is answered. `generated_at` says when the phone was picked up, not how old the data recited into it is; a service whose organiser died three days ago serves a payload one second old. So every block in `facts` carries its own `measured_at`, `facts.stale_sources` names anything measured over 26 hours ago, and `summary` states it in words. **The first live run caught one**: `filesystem` last measured 2026-08-06, five days stale — independently corroborated by an open `file_organiser agent stalled` alert in the same payload, which is two routes to one fact and the argument for the field.

  **`period` is anchored to the schedule rather than the last pull**, because "since the previous briefing" has no anchor on a pulled route: two consumers polling would each shorten the other's window, and storing a row per pull turns the endpoint into a pull log and needs a migration. `schedules.briefing_hour` already declares the cadence, so the window runs from the most recent 06:00 boundary — one meaning for every caller, no storage. `anchor: "schedule"` is in the payload because the other reading is the one a consumer would otherwise assume. **`summary` is deterministic** — no LLM in the 06:00 path, since a summary made only of numbers gains nothing from narration and would take the briefing down with llama-server — and **`facts` is a projection, not a copy**: counts and identifiers, never the rows the sections render, because a facts block containing the whole payload cannot be diffed, which is the only reason it exists. A test asserts every list in it holds scalars.

  **Two P1 snags fixed underneath, and the ordering was forced by the snag list's own note**: *"building a briefing envelope on top of wrong data only makes the wrong data better formatted."* `SNAG-BRIEF-001` — Project Health published every project ever scanned, 26 rows including work retired in July, while "Pick This Up" in the same payload listed 5 and the board returned 6. Both project sections now render from **one** query and one `status == "active"` filter, ordered worst-first (descending plus a cap shows exactly the rows carrying no information) and capped at 5; live result **26 → 5**, and the two sections agree by construction. `SNAG-BRIEF-002` — a bare `[:180]` slice became `truncate_at_word` in `sysadmin/core/text.py`: word boundary, always the marker `… (truncated)`, matching what Alfred's own `sanitise_text` appends. The 180 is now documented rather than anonymous, and the board deliberately still serves the field uncapped. Also removed: the project snapshots were being fetched **twice** per briefing, differing only by an `ORDER BY` Python does for free. Suite 1824 → 1852, ruff and mypy clean. **Handed to the consumer the same day**: the envelope and the staleness limit are written into Alfred's own `docs/external/briefing_producers.md` — its stated re-open trigger covers a payload gaining fields — and re-opened as live **row 130c** rather than reverting the archived, shipped row 130 to `Planned`. Alfred needs no adapter change; what it must *decide* is whether to read `facts.stale_sources`, since `produced_at` will read green forever. The note also flags that the limit is not sysadmin-specific: **SportsAnalyser's stamp has never been checked**. Three stale claims in that file were corrected in passing, including a sections table missing two sections that had been rendering in Alfred for days — the additive contract that makes this boundary safe is the same property that lets its documentation drift with no symptom.

- **2026-08-11 — Session 32: start-versus-finish accounting, and the blocker that named the wrong evidence.** `GET /api/projects/momentum` counts how often a session starts in a repository and nothing ships. The recorded blocker was "the SessionEnd hook overwrites `docs/sessions/handoff.md`, so session history does not survive", with two proposed fixes — an append-only `log.jsonl`, **or** sysadmin recording handoff-date transitions per scan. The second had been true since 2026-08-06: `handoff_age_days` is written on every scan, so `scanned_at − handoff_age_days` reconstructs the date a handoff was written and a change in it between two scans *is* an observed session. No hook, no writer, no migration. The session record is a side effect of a Stop hook that blocks a code-changing session until `HANDOFF.md` carries today's date, which is why it exists at all.

  **The measurement rule was wrong first, and only the live series showed it.** The obvious formulation — did a commit exist by the time the scanner saw the new handoff? — reads as common sense and let scan timing decide the answer, because the handoff is written *before* the work is committed. The scan at `2026-08-10 09:06` saw this repository's new handoff while `last_commit_at` still read 2026-08-08; that day's six commits arrived afterwards and a productive day was scored as dropped. Landings are now matched by **date window** — a commit dated in `[session_date, next_session_date)` is that session's output — which no fixture with an even cadence would have forced. A second correction came from the same run: `observed_from` reported the first scan rather than the first *dated* scan, so this repo's series read as three months when only 22 of its 198 snapshots can carry a session, inviting a reader to divide five sessions by ninety days.

  **Two landings are reported, not one**, because they are different failures: `dropped_code` shipped no code, `dropped` shipped nothing at all, and `docs_only` is the gap — a session that wrote up what it decided is a better outcome than silence and must not be summed with it. That needed no scanner change: `findings['git']` is written only when a housekeeping commit was skipped (77 rows of 3,635), so its absence means the newest commit *is* the newest code commit and the fallback is exact. The one scanner change was recording `handoff_date_source` for the *chosen* handoff rather than only the also-rans — an undated handoff falls back to mtime and a checkout rewrites mtime, which would present a `git checkout` as a morning's work. It is prospective, so every session observed so far is `unverified` and the `reason` sentence hedges rather than quietly asserting.

  **Live, it disagrees with the health scores**: `alfred-glance` has opened 2 sessions and landed nothing since 2026-08-03; `venture-assistant` 3 sessions, 1 landed; this repo 5 sessions, 4 landed, and `git log` confirms the single drop (2026-08-09) had zero commits; `Alfred` is 4 of 4. `ImbaBots` measures **0 sessions**, which is correct and was checked rather than assumed: its last session (`edbd8c2`, 2026-08-07 12:03) changed 22 files *and* its handoff in one commit, and it lands on ImbaBots' baseline scan, so there is nothing older to compare it to. The residual finding is elsewhere and is now `SNAG-PROJ-013` — its heading carries no ISO date, so the Stop hook will block the next code session there. 48 new tests, suite 1776 → 1824, ruff and mypy clean. **No consumer renders it yet** — it is a GET built for a one-line surface, and Session 30's fate says to ask before assuming alfred-glance wants it.

- **2026-08-11 — the tray was not broken, it was never started.** Reported as "no longer working" and diagnosed before anything was built: there is no `~/.config/autostart` entry and there was no unit, so the tray had **only ever been launched by hand** — the box booted 2026-08-10 06:37 and took the last manual instance with it. The code was fine, proven by running `.venv/bin/sysadmin-tray` directly and watching it poll the API. **The estate's only notification surface had been dead for a day and nothing reported it**, which is the same shape as SNAG-DB-001: the thing that would have told you was the thing that was down. Now `~/.config/systemd/user/sysadmin-tray.service`, enabled and running. **It is the first GUI unit here and the contract's skeleton is wrong for one**: lingering is on for `gaddi`, so a `WantedBy=default.target` unit starts at boot with no compositor and restart-loops. It binds to `graphical-session.target` instead (start at login, stop cleanly at logout), which works because KDE imports `DISPLAY`/`WAYLAND_DISPLAY` into the systemd user manager — checked, not assumed. `Restart=on-failure` rather than `always`, because the tray has its own Quit action and `always` would make that menu item a no-op. [monitorable-project.md](../guides/monitorable-project.md) §2.3 gained both rules. Wired into services.yaml the same day as the contract requires, with `monitor: false` and a reason: "inactive" is its *correct* state whenever nobody is logged in, so a check would alert every night and teach the reader to ignore the one surface that shows them alerts. That is a hole only because a dead tray used to mean silence — which the desktop notifier below fixed hours earlier, so a tray dying mid-session is now covered rather than merely unmonitored.

- **2026-08-11 — the daemon can speak for itself (SNAG-CFG-001).** Chased from a stale config key and found to be a whole dead limb: `Notifier.send_notification` was fully implemented, DND-aware, retry-capable — and **called by nothing outside its own tests**. `Notifier` is built in `main.py`, started in the lifespan and hung on `app.state`; `raise_alert`'s docstring says "the notifier service should be called separately" and `monitor/agent.py` says criticals are "to be picked up by notifier". Neither ever happened. Every alerting path in the daemon ended at a database row and waited for the tray to come and read it, so `notifications.desktop` was not a stale key but the visible end of a notification path that had never been connected. **Now wired**: `sysadmin/monitor/desktop.py` subscribes to `alert.raised` on the existing event bus and sends through `notify-send`. Subscribed rather than called from `raise_alert` for two reasons — `core` must not import a domain, and `_queue_event` buffers events until the run's transaction commits, so the notifier's own database query cannot race the insert it is reacting to.

  **It is the tray's understudy, not its rival.** The daemon stays silent whenever `/api/sysadmin/alerts` has been polled within `tray_grace_seconds` (180s, three times the tray's poll), so the two can never both toast one alert; what it covers is the case that was previously silent, **the tray not running** — which was true on this box while the fix was being written, verified by `ps` and `ss`. **The gate that makes it survivable is one-notification-per-incident**, the same "raise once while open" rule the idle nudges use. The measurements are why: the monitor writes one alert row *per failed check* — 186 rows for one `venture-assistant` outage, 123 for one `internet` outage, 88 criticals a day at steady state, and **547,814 unresolved `Log error: kernel` rows** in the table right now. A notifier that spoke per row would be a denial of service against its own reader. Verified against exactly those live rows: `Log error: kernel` → silent, an unseen title → speaks, and both silent while the tray polls. Both gates **fail closed** — an unreachable database returns "not new", because the alternative turns a connection blip into a storm.

  **The transport is `notify-send`, and the daemon had no way to reach a desktop.** `sysadmin.service` is a *system* unit with a minimal `Environment=PATH` and no session-bus address, so a bare `notify-send` fails with "Cannot autolaunch D-Bus without X11 $DISPLAY" — confirmed by running it under `env -i`. The address is supplied in code from the well-known `/run/user/<uid>/bus` socket, only when that socket exists, which keeps the fix out of a root-owned unit file nobody would remember to copy. **Left open deliberately**: recovery is not announced, because `alert.resolved` carries a match pattern (`"Project % health critical"`) rather than a subject — filed in the Backlog rather than papered over. 32 new tests, suite 1744 → 1776. **Needs `sudo systemctl restart sysadmin.service`** to take effect: unlike the organiser, this is daemon code.

- **2026-08-11 — Session 31: idle nudges, a broken commitment rather than a dirty directory.** An `active` project whose human-written next action has not changed for 7 days raises an `info` alert; at 14 it is escalated to `warning`. No new endpoint, no new delivery path and no migration — it rides the alerts table, the tray poll and the DND windows that already exist, and because the organiser is a oneshot timer rather than the daemon, it goes live on the next timer run without a restart. Threshold overridable per project as `idle_nudge_days` in `.project.yaml`, beside `alert_threshold` and deliberately separate from it: a long-cycle repository should be able to relax the commitment clock without also going unwatched for a missing README. **Eligibility was extracted, not re-implemented** — `GET /api/projects/next`'s rules moved into `next_action.eligible_candidates` and both callers now share them, so the endpoint cannot stop offering a project while the nudge goes on reminding you about it. Same reasoning for `load_action_streaks`, which folds the history query the two of them read.

  **Three decisions where the obvious implementation was the wrong one.** (1) **Raise once per open nudge, not once per scan**: `BaseAgent.raise_alert` inserts unconditionally — the mechanism behind SNAG-PROJ-004's 1,664 rows — and the organiser runs daily, so the health-alert pattern would write one row per day per stuck project and turn a nudge into a nag inside the database. (2) **Escalation resolves the quiet row and raises a loud one** rather than updating severity in place, because the tray fingerprints notifications as `"{severity}:{title}"` and an in-place change keeps a fingerprint it has already suppressed — the escalation would be recorded and never spoken. (3) **The escalation is a gap, not a multiplier**: a project that relaxes its own threshold to 21 days escalates at 28, not 42, so the per-project knob moves when the clock starts and not how patient the escalation is. Never `critical` at any age — criticals break through DND by configuration, and waking someone at 02:00 about a roadmap item is how a monitor gets muted wholesale.

  **The feature ships firing nothing, and that is the intended shape.** All three eligible projects turn their next actions over in 1–4 days, so at 7 days the live estate produces zero nudges — a live organiser run over 25 repositories confirmed `{raised: 0, escalated: 0, resolved: 0}`. Since a clean run proves only that nothing crashed, the ladder was then exercised over the **real** historical series for this repo (the "Session 24: File organiser tiers" action, **9 scans across 2 days**): `streak_days` folded it to a single 2-day run and the ladder produced `info`, `warning` and no-nudge at the thresholds it should. That 9-to-2 ratio is Session 29's days-not-scans argument holding on live data. **A wrong claim was caught by checking it**: the design was written three times around `notifications.desktop.min_severity` as the knob deciding whether a nudge is audible, and nothing in `sysadmin/` reads `config.notifications.desktop` at all — the live gate is `tray.notify_min_severity` in a different section. Filed as `SNAG-CFG-001`, not fixed here, since it sits on the tray's configuration boundary and this session changed no notification code. 43 new tests, suite 1701 → 1744, ruff and mypy clean.

- **2026-08-11 — Session 30 closed unbuilt: the consumer had already declined it.** The session opened to build it and checked the consumer first, which ended it. Alfred accepted **ADR-0064** on 2026-08-07 — three days *before* Session 29 shipped — declining the whole projects-page arc for v1 behind two named, countable triggers. This repo's tasks.md said "nothing here blocks it beyond Session 29"; the block was never on this side, and the row had been wrong since the day it was written. **Neither trigger fires and one moved the wrong way**: `stalled_count ≥ 2` sustained over two weekly reads stands at **0**, and `count ≥ 12` active stands at **5**, down from the 6 the ADR was written against. The board does carry 3 stalled projects, all among the 20 inactive ones the trigger deliberately excludes — declaring a project dormant *was* the decision, so it cannot also be a stall. The decline is not a rejection of the endpoints: ADR-0064 §1 finds the momentum data already reaches the owner as the daily digest's `Pick This Up` section, built to this guide's own honesty treatment, and §2 makes `alfred-projects-page.md` the build instruction the moment a trigger fires — "good and should be followed rather than redesigned". **What was actually wrong was that the decision lived in one repo and the work in another.** A declined-by-the-consumer state had no representation on the producer's side, so this roadmap kept advertising the work as unblocked while Alfred had refused it in writing. Recorded now in both places it is read from: the tasks.md row carries the trigger table and the `curl` that re-checks it, and the guide gains a §0 status block ahead of §1 so nobody builds from the spec without meeting the decline first. **One premise of the ADR has expired and fires nothing** — §3 declines to design against `GET /api/projects/next` because it 404s with an undecided ranking, and Session 29 shipped it the next day with a decided, documented one. That retires a stated *reason* without moving either *trigger*, which is the distinction a counted deferral exists to hold: it is re-opened by the count, not by an argument. Alfred's own ADR does not record this yet.

- **2026-08-11 — a test that failed on a date, not on a change.** `test_endpoint_filters_by_confidence` went red in a session that had not touched the reliability scorer, and it was pre-existing — confirmed by stashing the uncommitted work and watching it fail anyway. The file held **two clocks**: every direct-scorer call pinned `now=NOW` (2026-08-07 12:00) with the fixture rows anchored there, while the nine endpoint calls went through the route, which reads `datetime.now(UTC)` because this endpoint is computed live by design. As real time drew away from `NOW` the seven-day window slid off the fixture data. The confidence test went first, at the 3.5-day mark on 2026-08-11, where a seven-day run of checks stops covering half the window and `_confidence` correctly downgrades the service to `low` — the scorer was right and the test was wrong. **The other eight had until 2026-08-14**, when the run would have left the window outright and all nine would have failed together. An autouse fixture pins the route's clock to the same `NOW`; `datetime` is used exactly once in that route module, so the patch is narrow and the route can no longer observe wall-clock time. Suite back to 1701, ruff and mypy clean.

- **2026-08-10 — Session 38: the unread handoff gets a reader.** `handoff_duplicates` had been recorded by `scan_roadmap` since Session 37 and consumed by nothing; it is now a zero-point `kind: "roadmap"` recommendation, which reaches `/api/projects/{name}/recommendations`, `/api/projects/actions` and the weekly review at once because all three call `recommendations_for`. **The estate was checked first and the finding changed the job.** Commit `0d56081` consolidated the migration: **seven repos hold a handoff and every one holds exactly one**, so this ships as a **regression detector**, not a report on a current mess — it fires the day someone re-creates a second handoff. Five carry a root `HANDOFF.md` (`Alfred`, `ImbaBots`, this repo, `apps/venture-assistant`, `apps/SportsAnalyser`) and the two archived `PersonalAssistant` repos still carry `docs/sessions/handoff.md`, which the non-active waiver excludes anyway. **The first survey was wrong and the estate map is why**: globbing `~/projects/*/` sees 11 directories, while `discovery_depth: 2` means the scanned population is 25 across `~/projects/`, `apps/` and `archive/` — the run reported `venture-assistant` and `SportsAnalyser` as holding no handoff when both hold a root one, contradicting a fact Session 37 had already established without that contradiction being noticed. The live table could not have shown it either way: the newest stored snapshot (09:06 today) predates Session 37's code and carries neither `handoff_path` nor `handoff_duplicates`, so 90 days of JSONB read `None` for both. Verified end-to-end against a constructed two-handoff repository instead, and the mtime branch is the one that fired — a generated stub headed `# Session Handoff` carries no ISO date, which is the realistic case. **The field was widened from a list of paths to `{path, date, date_source, days_older}`**, because the two cases a reader must separate are indistinguishable as paths: a loser nine days behind the winner is migration debris and can be deleted, while one *sharing* the winner's date lost on tuple order alone and deleting it unread is how SNAG-ROADMAP-003 would recur from the other side. The advice branches on exactly that — `days_older` of `0` or `None` takes the "confirm which is current" wording, never "delete". `date_source` records which clock produced the gap, since `handoff_date` falls back to mtime and a clone rewrites every mtime on disk; the recommendation marks those "by file date" and says why they are weaker rather than asserting a number it cannot stand behind. Selection still applies the fallback uniformly — this constrains the *advice*, not the choice. The bare-string shape is still accepted for the same reason `stale_branches` accepts strings: retention outlives a shape change. `handoff_path` is consumed in the detail line only, deliberately, so it remains unread in a repo with one handoff — filed as a follow-up rather than expanded into `ProjectBoardEntry` in the same sitting. 11 new tests, suite 1690 → 1701, ruff and mypy clean, no new routes and no migration.

- **2026-08-10 — Session 29: the one-thing endpoint.** `GET /api/projects/next` returns one project, one action and one sentence saying why it is that one. The session's own task list said the ranking policy was the whole feature and needed a decision before code, so the decision was taken first and against measured data rather than defaulted. **The ranking is stuckness** — how long the stated next action has stood unchanged — tie-broken by the most recently committed project. **Nearest-to-finishing was rejected on evidence**: it reads `done_tasks`/`open_tasks`, which are `None` for three of the five active projects on this estate, so it would have been blind to most of the population while looking authoritative. **Smallest-next-step was rejected as unmeasurable** — nothing records the size of a step, and every proxy for it (string length, task count) is invented rather than observed. **Longest-idle was rejected as the guilt metric** the roadmap already doubted.

  **The unit is elapsed days, not scans, and that is the finding worth keeping.** The obvious implementation counts consecutive snapshots carrying the same action — Session 37's `next_action_changed` makes it a one-line query. It would have passed every fixture written with an even cadence and been wrong on live data: the scan series is 6-hourly until Session 35, daily from the organiser's timer since, plus every manual `POST /api/projects/scan`, and the live table holds two scans 17 minutes apart on 2026-08-08 and two more on 2026-08-10. Ranking on scan count measures how often the organiser happened to run and reports it as the owner's behaviour. `unchanged_scans` is still returned as the evidence behind the number; `at_window_edge` marks a run reaching the oldest scan held, so `days_unchanged` is honestly a lower bound. Elapsed days come from the snapshot series rather than `handoff_age_days`, which says what the document claims about itself and already has the job of deciding `stalled`.

  **Eligibility is narrower than the board's, deliberately.** Active projects whose `next_action_source` is `handoff` or `tasks` — the board's `git` fallback is a commit subject, honest there because the source is rendered beside it, and not an instruction to act on. Nor is a handoff that states there is nothing queued: two live estate handoffs read "No unchecked task found — set one before the next session", which is a *correct* handoff and still not something to hand a consumer whose premise is glance-then-act. `roadmap.looks_like_no_action` is conservative in the same direction as `is_placeholder` — bare forms must be the whole line, so "None of the migrations are applied" survives as real work.

  **Empty is 200 with `project: null`**, never 404, because 404 would collapse "every project is up to date" into "no scan has ever run" and a consumer cannot tell those apart from a status code. `skipped` breaks the ruled-out population down by reason, which is what made the live shape legible: **2 candidates out of 23 fresh projects** — 20 inactive, 1 with no stated action, 2 stating there is nothing queued. Verified against the live database before the tests were written: both candidates sat at 2 days unchanged and the tie broke on last commit (1 day vs 3), with the reason sentence naming the tie-break it actually used. The winning action turned out to be stale output from the SessionEnd hook Session 37 retired — the endpoint doing its job on the first run. `action_history_query` extracts one JSONB field in the database rather than loading `ProjectSnapshot` entities, since the alternative drags kilobytes of `findings` per scan across the window to compute a run length. 45 new tests — suite 1645 → 1690, ruff and mypy clean, 55 → 56 routes.

- **2026-08-10 — Session 37: the handoff pipeline, both ends.** Raised as "the handoff hook isn't doing much in venture-assistant". Measuring first changed the diagnosis: across 15 repos, 5 carried a `docs/sessions/handoff.md` and **every one was hook output**, while exactly two repos had ever held a handoff someone wrote — and both lived at paths the scanner could not read. Root `HANDOFF.md` existed in **1 of 15**, not "most", which is why the location question was checked before it was acted on. **The writer**: `SessionEnd` cannot block — it is an observability event — so `generate-handoff.sh` could only ever emit what `git` already recorded (branch, porcelain, today's log). Retired, unwired, left on disk with its reasoning. `~/.claude/hooks/require-handoff.sh` is a **Stop** hook, which can block, and does: a session that changed code cannot finish until `HANDOFF.md` carries today's date, so the file is written by whoever knows what the session did. Three independent loop guards, because a blocking Stop hook that misfires hangs every session — `stop_hook_active`, a per-session+repo marker file (load-bearing: the field is no longer in the documented schema), and exit 0 on every failure path. Ten payload cases verified before wiring, including that `touch HANDOFF.md` does **not** satisfy it. **The reader**: `SNAG-ROADMAP-003` closed — four candidate paths, selection by the document's own heading date rather than tuple order, also-rans reported as `handoff_duplicates`. **The first fix was wrong and only the live estate showed it**: ranking every undated candidate below every dated one re-created the bug from the other side, because ImbaBots' 141 KB handoff heads itself "Handoff — M5 (Tier 2)" with no ISO date and lost to an 882-byte stub written an hour earlier. The mtime fallback has to apply uniformly, which is what `scan_roadmap` already did downstream — the module had been holding two contradictory rules at once. **The design lesson**: a file guaranteed to exist cannot also be the file whose absence means something; the hook filled the slot everywhere, so nothing ever signalled a real handoff was missing. **Session 32 is unblocked, and its premise was wrong twice.** Its recorded blocker was "the SessionEnd hook overwriting its handoff instead of appending a log" — but the hook no longer writes, *and the log already existed*. Session 28 has written the whole roadmap findings block into `project_snapshots` since 2026-08-06; the history list exposed `health_score` and `scanned_at` only, so ninety days of next actions sat in JSONB with no endpoint over them. `ProjectHistoryPoint` now carries `next_action`, `next_action_source` and `next_action_changed`, built by `build_narrative_history`. The change flag compares against the **older** neighbour, and the oldest point in the window is `None` rather than `False` — there is nothing older to compare it to, and calling that "unchanged" invents a streak whose length moves with `limit` while the data does not. Live proof: ImbaBots' `M5-T05` unchanged across 10 scans and 3 days, venture-assistant's next action unchanged since 2026-08-07 while the task it names is ticked `[x]` — a stuck run beside a completed task is the stale-handoff signal, and it is now visible without a hand-written SQL query. Suite 1629 → 1645, ruff and mypy clean.

- **2026-08-10 — Session 34: the twelve project-side defects, cleared.** Every one of them corrupted output Alfred already consumes, which is why they were ordered ahead of the briefing envelope. Two required a decision before any code was written, and both were taken deliberately rather than defaulted. **The 1,664 orphaned alert rows were resolved, not deleted** (migration 010): they are real history — the organiser did judge those projects unhealthy at those times — and marking them resolved hands them to the existing 180-day retention purge instead of routing around the mechanism that is supposed to own removal. `resolved_at` is *now*, not backdated, because the alerts really were open until the migration ran and backdating would have made the whole backlog instantly purgeable, destroying the history the migration chose not to delete. **`GET /api/projects/stale` got its `days` parameter implemented rather than deleted**: no consumer exists anywhere under `~/projects` — only this repo's own docs mention it — so this was a free choice, and the endpoint filtering on `health_score < needs_attention_min` had made it a duplicate of `/overview` wearing a name that promised idleness. A well-kept repository untouched for a year scored 90 and never appeared. It now filters on last-commit age, reports `days_idle` (null for never-committed, which is the strongest form of the question, not the weakest) and has a `StaleProjectsResponse` contract.

  **The audit said eight surfaces; there were nine.** That undercount is the argument for the fix's shape: a pattern copy-pasted across three packages cannot be counted reliably, including by the person auditing it. `sysadmin/projects/snapshots.py` now owns the latest-per-project join *and* the `newest_scan − 1h` cutoff, and `tests/test_project_snapshots_query.py` fails if any module builds its own — an AST walk for `func.max(ProjectSnapshot.scanned_at)` outside the owning module. The helper could not live in `projects/router.py`, since `briefing/data.py` would then import one router from another. **Freshness is anchored to the newest scan, never to `now()`**: anchoring to wall-clock would empty every project surface the moment the organiser's timer stopped, reporting a monitoring failure as an estate with no projects in it. **This carries a real cost, stated rather than glossed**: the suite mocks every session, so a `WHERE` clause is invisible to it and the two board tests that proved a deleted project was dropped can no longer prove it. What replaced them is stronger in coverage (all nine call sites, not the one that happened to have the filter written by hand) and weaker in kind (compiled SQL, not a round trip). A live-database test is filed as a follow-up rather than pretended.

  **Alert resolution is set-based, deliberately unlike the two reference agents.** `sysadmin/monitor/agent.py` and `sysadmin/units/agent.py` loop and call `BaseAgent.resolve_alerts` per recovered item; their populations are fixed by configuration. A project's is not — **a project deleted from disk never appears in a scan, so it can never be observed recovering**, so a per-project loop would have left its alert unresolved forever and the backlog would have regrown on the next deletion. Asking the inverse question ("which of my open alerts would this scan not raise?") closes recovery, deletion, rename and re-declaration as `archived` in one statement, and cannot drift from the raise path because both titles come from `_alert_title`. The rows raised moments earlier in the same transaction are excluded by title, not by timestamp — a title comparison is exact, where "created before now" races the clock the inserts were stamped with.

  **The marker scan's three defects were one job, and the measured effect is large.** `*.md` is no longer scanned (a repository's own `snag_list.md` counted towards its own penalty, so writing up a defect lowered the score of the project writing it up), patterns match whole words via `grep -w` (`TODO_STATES` and `TodoList` were both scored as markers), and the cap is a project total that records its own truncation rather than grep's per-file `-m 1000` behind a docstring claiming a global limit. Live: **PersonalAssistant 327 → 174 markers, sysadmin_assistant 87 → 56, PersonalAssistant-auto 290 → 150**; five projects dropped to zero because their only markers were in documentation. Most scores did not move because those projects sit at the 30-point cap, but **Alfred went 75 → 95 and `terrible` 95 → 100**. `HACK` and `XXX` still cost points — they are real code smells — but the recommendation now names them (`HACK 40. Every 10 markers cost 5 points`) instead of reporting "0 TODOs, 0 FIXMEs" beside an unexplained deduction.

  **The project review is figure-free by construction**, four days after the disk review was rebuilt the same way and a year after the same model taught the lesson on scores. Scores become bands, deltas become directions, and recommendation titles — which carry counts like "Prune 7 stale branches" — become `kind` phrases; every real figure lives in `build_facts_section`, prepended deterministically. `strip_markdown` moved to `sysadmin/core/text.py` so both reviews share it without either domain importing the other. A guard test asserts no digit reaches the model, with project names stripped first: a name is an identifier the model must quote back, not a quantity.

  **Retention gained three tables, not two.** `project_reviews` and `disk_reviews` were in neither `retention_config` nor `TABLE_TIMESTAMP_MAP`; **`unit_audits` was in the map with no config row**, so the code that would have purged it was never reached — found while adding the other two. Reviews get 365 days rather than the 30 that check data gets: they are weekly narratives, and 30 days keeps four of them, which is too few to see a trend. All three are in a new `KEEP_LATEST_PER` map so the newest row survives its window — a purge that emptied `project_reviews` would make `GET /api/projects/review` 404, which the tray renders as "no review has ever been generated" rather than "none lately".

  **And the session found a P0 that was not on the list — a live monitoring blackout, 39 hours old and still running.** While tracing why the schema drift guard had stayed green, `alembic current` turned out to report **008** against a repository head of 009. Migration 009 adds `'skipped'` to `chk_health_status`; it was written on 2026-08-08 in Session 35 Phase 3 and never applied, because **nothing applies migrations here** — no script, no `ExecStartPre`, no CI step, just a manual command a human has to remember. `sysadmin.service` restarted at 17:36 on 2026-08-08, two minutes after the last successful health check, and picked up the new `services.yaml`, in which `venture-chat-large` is `kind: static` with `monitor: false` and therefore records `skipped` — the exact value the un-applied migration was meant to permit. **Zero rows were written to `service_health` from 2026-08-08 17:34:54 until 2026-08-10 09:07:25**, when applying the migration resumed them.

  **One rejected row cost all nineteen services their check.** `SysAdminAgent._execute` adds every service's result to one session and `BaseAgent.run` commits once, so the `CheckViolationError` on a single deliberately-unmonitored service aborted the whole transaction — the failure mode was total, not partial, which is also why it left no partial data to notice. **Nothing noticed for a different reason each time it could have**: the daemon logged `agent_run_failed` every five minutes (29 times this morning alone) and nothing reads that; `verify_connection` proves the database answers, not that it is the schema this code was written for; and the drift guard — the one test that connects to the live database — explicitly skips `alembic_version` *and* runs `compare_metadata`, which does not diff CHECK constraints. That last point was verified rather than assumed: restoring the pre-009 constraint inside a rolled-back transaction produces an **empty diff**, with the model declaring `'skipped'` and the database rejecting it. The alerting path was itself the thing that broke, so it could not report its own failure. ~18 of the 39 hours were with the daemon up and failing; the box was asleep for the rest. Filed as **SNAG-DB-001 (P0)** — fixed, with all three detection gaps left open and specified in tasks.md, because applying the migration fixes this instance and none of the reasons it ran for 39 hours. 64 new tests — suite 1565 → 1629, ruff and mypy clean, 55 routes before and after.

- **2026-08-08 — Session 35 operational: the organiser timer is installed, and verifying it found a bug.** `sysadmin-organiser.timer` is installed into `~/.config/systemd/user`, enabled, and armed for 04:32 daily; a manual run under systemd exits 0 in 1.45 s at 88.5 MB peak against a 512 MB cap. The same-day wiring the contract requires is done: the timer is declared in services.yaml as `kind: timer`, and `agents.project_organiser.enabled` is now **false** — that flag gates the schedule *inside the daemon* and nothing else, so leaving it true would scan the estate twice, once every 6 h in-process and once daily from the timer. Endpoints, the manual `POST /api/projects/scan` and the weekly review are unaffected. Monitoring the timer is what **replaces** the self-monitor's stall watch over that agent: a disabled agent is correctly not flagged as stalled, so something else had to be able to tell whether the scan ran, and now the timer's own last-run is that signal. **Verifying rather than assuming immediately paid: `kind: timer` had been recording nothing since Phase 3** — see SNAG-SYSD-002. `_timer_facts` reads three `systemctl show` properties that `get_unit_status` never requested, so every timer check returned `ok` with an empty last-run and nothing said so. It passed its unit tests because those mock `get_unit_status` and supply the properties the assertions expect; the mock was the specification and the real function had never been asked. Fixed, with a test that asserts the *coupling* — every property `_timer_facts` reads must appear in `get_unit_status`'s request list — rather than only the behaviour on a cooperative mock. Live timers now report real data: `alfred-evaluate` last triggered 08:00:01, `pgbackrest-backup` 00:00:42. 3 new tests — suite 1562 → 1565. **Pending ops action**: `sudo systemctl restart sysadmin.service` — the daemon has been up since 2026-08-07 and still holds the old config, so it is both scanning on the retired 6-hourly schedule and unaware of the new timer.

- **2026-08-08 — Session 35 Phase 6: the organiser gets its own timer, and ADR-0001.** `sysadmin-organiser` is a console script and a `Type=oneshot` unit driven by a daily timer, so the scan and the monitor no longer share a fate: stop the timer and health checks carry on, stop the daemon and the scan still writes its snapshots and rewrites estate.json. Verified standalone — 25 projects in 1.46 s with no daemon running. The unit is **deliberately not `After=sysadmin.service`**: ordering them would make a stopped monitor delay a scan that does not need it. `Persistent=true` because a box asleep at 04:30 must still get its scan, which is the whole point of moving it out of an always-on process. `BaseAgent.run` now returns its `AgentResult` so a one-shot invocation has something to turn into an exit code rather than re-reading the row it just wrote; the scheduler ignores it. **[ADR-0001](../adr/0001-project-registry.md)** records the four things the brief asked for — identity in the repositories, no paths in services.yaml, persistence deferred because it is the decision that locks in ownership, and who owns project state left explicitly open — plus the one thing that is *not* staged for extraction: migration 001 creates both sides' tables in one revision, so moving the project side to its own service still means a data migration. `SYSADMIN-SERVICE-SPEC.md` is marked superseded-in-part with a difference table rather than rewritten; it is the February design record and rewriting it would lose that, the same reasoning that left the archived roadmap entries alone in Phase 2. **One trap worth recording**: `uv sync` without `--all-extras` removes the dev extras, after which `uv run pytest` silently falls back to `/usr/bin/pytest` and the suite runs against system Python with none of the project's dependencies — it presents as `ModuleNotFoundError: pythonjsonlogger`, which looks like a broken dependency rather than a broken environment. 6 new tests — suite 1556 → 1562, ruff and mypy clean. **Pending ops action**: install the timer with `systemctl --user enable --now sysadmin-organiser.timer`, then add it to services.yaml as `kind: timer` and set `agents.project_organiser.enabled: false` so the scan is not run twice.

- **2026-08-08 — Session 35 Phase 5: estate.json.** The organiser writes a versioned `estate.json` on every run, **atomically** — temp file in the destination directory, then `os.replace`, because a consumer polling it must never catch it half-written and `/tmp` is frequently a different filesystem. `health` is derived from the snapshot computed in the same run rather than being a second scorer: two numbers called "health" that disagreed would be a bug nobody could adjudicate. `services` is a list of **names** resolved from services.yaml by project id, not embedded topology, so a port move does not have two places to edit. Undeclared repositories appear with `"status": "undeclared"` and whatever can be derived, because omitting them would make the file agree with itself and disagree with the disk. **The brief's seed for the commit-ignore rule was incomplete, and the feature would not have worked with it.** It named the 2026-08-04/05 reorganisation snapshot; this estate has *two* sweeps, and the second — the fan-out that wrote a roadmap document set into eleven repositories on 2026-08-06 — is **newer**. With only the first pattern the walk stops at the newest commit having skipped nothing, so eleven projects would still have read as touched last week. The rule is therefore a **list** of patterns rather than the single regex sketched, and a test pins the failure mode. Correctness is checkable rather than asserted: the automated rule reproduces every hand-recorded "last code" date in the legacy registry file exactly — daiy 2026-02-06, terrible 2026-03-25, BudgetApp 2025-05-14, SportsAnalyser 2026-03-23, portfolionew never. **Staleness now comes from `last_code_commit` everywhere**, achieved without a migration by putting the code date in `ProjectSnapshot.last_commit_at` (so every downstream reading is derived from it) and recording both raw dates in `findings["git"]` when they differ. **Measured impact: 12 projects' staleness figures change, and zero health scores do** — the corrected projects are all dormant or archived, whose staleness is not penalised, so the numbers get fixed without moving a score or tripping an alert. The largest correction is 1 day → 472 days. 32 new tests — suite 1524 → 1556, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 4: projects.yaml retired.** The file is now `docs/projects-registry-legacy.yaml` and **nothing reads it**. `ManagedProject`, `ProjectEndpoint`, `ProjectsConfig` and `_merge_projects_config` are gone from `core/config.py`; `AppConfig` has no `projects` section. Project state — declared status and per-project alert floors — is read from the `.project.yaml` manifests through the registry, and services from services.yaml. **The registry dissolved the last cross-domain import**: `units → projects` was two imports (`discover_projects`, `_infer_status`) and is now zero, because both agents call `load_registry` instead of one importing the other's discovery. That was the exact drift the registry was built to remove, and its symptom would have been units reported as orphans because one sweep could not see a project the other could. `GET /api/units/actions` now emits **services.yaml** snippets rather than the old config.yaml/projects.yaml pair, and a bug found while converting it is worth recording: the sweep matches units against the *directory* name while services.yaml keys on the *manifest id*, so the first version emitted `project: Alfred` where `alfred` was needed — a snippet that would have failed to load, which is worse than no snippet. A test now parses each generated snippet as a real `ServiceEntry`. `_effective_threshold` reads the manifest instead of doing a three-key lookup by path, name and basename; **`undeclared` is scored exactly like `active`** rather than falling through the `status == "active"` guards by accident, because an absent decision is not a decision to waive anything. The migration script gained the services emission the brief specified, used as a **completeness check** rather than a generator: it reports anything projects.yaml declared that services.yaml does not carry, and flagged the one deliberate difference (the `sysadmin-assistant` id) rather than letting it pass silently. **The reasoning transfer was done by hand, one project at a time** — 20 decisions across 15 manifests, with a test asserting no manifest silently loses its block, since the legacy file is the only other copy. Estate now reads 5 active, 7 dormant, 12 archived, 1 undeclared. 55 routes before and after. Suite 1521 → 1524, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 3 (second half): services.yaml wired in.** `config.yaml` now holds **no per-service topology at all** — `agents.sysadmin.services` is gone, and `agents.log_aggregator.sources` is down to `kernel`, the one source with no service to hang off. `MonitoredService` and `ManagedProject.to_monitored_services`/`to_log_sources` were deleted outright: projects.yaml contributes nothing to monitoring any more. **Startup validates every `project:` reference against the registry**, so an id naming no manifest stops the service with every bad reference listed at once; a path naming nothing failed silently and did, twice. **Four measured behaviour changes**, all flagged before the wiring landed. (1) `kind: http` now asserts the unit is active as well as polling the url — a 200 says *something* answered, not that the unit this estate believes serves it is what answered. It **fails open** on a systemd query error, which is SNAG-SYSD-001's rule: without it one user-bus hiccup would turn every http service on the box degraded at once. (2) Five systemd checks became `kind: timer` and now record `last_run`/`next_run`/`last_result`, because an armed timer is `active (waiting)` and the active test alone cannot tell a schedule about to fire from one whose last run failed. (3) `venture-chat-large` is declared for the first time, as `kind: static` with `monitor: false` and a required `reason`, recorded as `skipped` — previously it was absent from every config file, which made "deliberately not watched" indistinguishable from "nobody wired it up". (4) **A duplicate log ingestion was removed**: `sysadmin.service` was read twice, as `sysadmin` from config.yaml and `sysadmin-service` from projects.yaml, and neither file said so — the merge now drops a config source that duplicates a service by name *or* by unit, and logs which it kept. Service count is unchanged at 17 checked; log sources went 10 → 9. `GET /api/projects/managed` resolves services by id instead of generating them, so it can finally report all four of Alfred's rather than the two projects.yaml could model. The tray reads `mute:` from services.yaml, and a missing file costs it a mute list rather than a launch. 55 routes before and after, every path identical. 12 new wiring tests plus the test-suite migration off `MonitoredService` — suite 1560 → 1553 net (the projects.yaml endpoint tests went with the feature), ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 3 (first half): the manifests and services.yaml.** Phase 3 could not start as briefed: it keys services on project id and demands that an unknown id fail at load, but **zero manifests existed** — writing them is Phase 4. So Phase 4's writer came first. `scripts/migrate_registry.py` (dry run by default, never overwrites without `--force`, never reads projects.yaml's comments) wrote **16 `.project.yaml` manifests** into the project directories themselves, where identity travels with the directory and a rename cannot orphan it. Registry now loads 16 declared ids, 9 undeclared. **Two collisions the derived-id design predicted, both resolved by declaring**: `apps/BSL-Translator` and `archive/bsl-translator` both derive `bsl-translator`, and only the first is declared, so the second stays a provisional id that resolves to nothing; `archive/Portfolio` and `archive/portfolio` — two directories differing only in case — remain a reported finding, which is correct, since nobody has decided anything about either. `services.yaml` folds both sources into one file with **no paths at all**: the six projects.yaml endpoints plus the eleven units exiled to `agents.sysadmin.services`, seven of which were only there because projects.yaml modelled exactly one backend and one frontend and could not express a third unit. `kind` now decides the check, so the rule that `alfred-evaluate` is a oneshot to be watched through its timer — previously a config.yaml comment, correct and hand-maintained and invisible to the code — is a field. **Service names were deliberately kept, against the brief's example**: `service_name` keys `service_health`, reliability scores and the tray's mute list, so renaming `alfred` to `alfred-backend` would orphan a month of history; `role:` carries the tidier label instead. Migration 009 adds `'skipped'` to `chk_health_status` — `kind: static`, `kind: oneshot` and `monitor: false` all mean "deliberately not checked", which no existing status expresses: `error` means the check failed, `critical` is a claim about the service, and recording nothing would make a declared service vanish from `/api/sysadmin/status` and the tray grid, reading as forgotten rather than as decided. Two naming faults fixed before anything consumed the ids: the project id derived from projects.yaml's `name` came out as `sysadmin-service`, identical to a service name in the same file, so it is `sysadmin-assistant`; and the five projects projects.yaml left blank — `alfred`, `alfred-glance`, `sysadmin-assistant`, `athenaeum`, `venture-assistant` — were declared `active` rather than inheriting the new `undeclared` default, since blank previously *meant* active. **Nothing reads services.yaml yet**: the wiring changes monitoring behaviour and is the second half. 48 new tests — suite 1512 → 1560, ruff and mypy clean.

- **2026-08-08 — Session 35 Phase 2: the module boundary.** 62 modules relocated with `git mv` into seven packages — `core/` (config, database, contracts, `BaseAgent`, scheduler, retention, LLM client, `/health`), `registry/` (Phase 1, unchanged), and one package each for `monitor/`, `projects/`, `files/`, `units/` and `briefing/`. Imports rewritten in 98 files; **55 routes before, 55 after, every path identical**. `tests/test_import_boundary.py` asserts `sysadmin/monitor` never imports `sysadmin.projects`, and it passes without a detour: monitor imports **only** `core` (31 edges) and nothing else. **The brief named four packages and the estate has six concerns** — file organising (3,296 lines) and service discovery (1,633) fit neither `monitor` nor `projects`, and putting them in `core` would have made the shared layer larger than the domains it serves, so each got its own package. A seventh, `briefing/`, holds the two endpoints that join three domains each: they cannot live in `monitor` without breaking the boundary, cannot live in `projects` without lying, and cannot live in `core`, which must not depend on a domain. **`GET /api/sysadmin/briefing/preview` moved package but kept its path**, because monitor importing `briefing.data` would have reached `projects` transitively — a violation the textual test cannot see. Four cross-domain imports survive and are deliberate: `projects → monitor` for `ServiceHealth` on `/api/projects/managed`, `files → monitor` (×2) for `ResourceSnapshot` disk occupancy, and `units → projects` (×2) for `discover_projects`, which Phase 1's registry is built to absorb. **Three couplings route through `core.config` and so stay invisible to the boundary test** — `self_monitor` reading `agents.project_organiser.{enabled,scan_interval_hours}`, the file actions reading `projects_root` for the `~/projects` safety fence, and the unit sweep reading both sides; a second test now forbids `core/` and `registry/` from importing any domain, without which core becomes the smuggling route and every boundary above it is fiction. `sysadmin/metadata.py` replaces the old `models/__init__.py` aggregator, so Alembic and the schema-drift test share one list instead of two that can diverge. The only real breakage was `load_config`'s `Path(__file__).parent.parent`, which gained a directory level and resolved to `sysadmin/config.yaml` — 198 test errors from one expression, now a named `REPO_ROOT`. 3 new tests — suite 1509 → 1512, ruff and mypy clean.

- **2026-08-07 — Session 25 Tier 1: per-service reliability scoring.** The third scorer, after the project organiser's repositories and the file organiser's disk — the services this application exists to watch had no number attached to them. `GET /api/services/reliability`, a pure `sysadmin/services/reliability.py` (scores a list of `HealthPoint`, no DB or FastAPI) plus a `reliability_history.py` adapter, a `reliability_scores` table (migration 008) and an 02:00 daily snapshot cron. Score is `100 − downtime − instability`, both individually attributable so Tier 2 can price them separately: downtime is `round(100 − uptime%)` capped at 60, instability is 5 per outage **episode** from the first, capped at 25. **They are separate terms because they are separate failures**, and the live data proves it: `internet` lost only 7.5 % of its checks but across *three* incidents (−15 instability, −8 downtime) while `venture-assistant` lost 27 % in *one* sustained outage (−27, −5) — retry logic survives the second shape and dies on the first, so a repeatedly-dropping service must not outrank a longer single outage merely because it was up more of the time. **Three of the plan's four metrics survived contact with the data; the fourth had no data at all.** (1) "Mean time between alerts" was uncomputable as specified: the `alerts` table records one row *per failed check*, so a single internet outage wrote **123 rows in 7 days** and one `venture-assistant` outage wrote **81** — the mean of those measures `health_check_interval_seconds` and nothing else. Incidents now come from consecutive non-ok runs in `service_health`, which collapse into episodes by construction, carry the same information, and avoid a join on `details->>'service_name'` — the only, unindexed, link `alerts` has to a service. (2) **Restart frequency was dropped**: nothing on this host records restarts (`NRestarts` is a live cumulative counter never sampled into the DB; `agent_runs` records *agent* executions), and three measured metrics beat four where one is invented. (3) Coverage became a **confidence flag, not a deduction** — the estate records ~81 % of expected checks and services added on 2026-08-06 have ~1 day of history against a 7-day window, but a gap means the *monitor* was down, so deducting would charge the service for this application's downtime. Ordering deliberately ignores confidence: a thinly-observed failing service is still the most interesting row on the page. **Computed live, never read back** — unlike `/api/units/status`, which serves the latest stored sweep, this recomputes on every request (~28 ms for the whole estate), because a stored score would be up to 24 h stale and would 404 before the first nightly job ran; the table is history for trending, written at 02:00 an hour *ahead* of the 03:00 retention purge so the day's score lands before the checks behind it can be deleted. The population is **the configured services**, not the distinct names in `service_health`, and both differences matter: retired services (`ollama`, `personal-assistant`) keep rows for 30 days and must not be scored, while `venture-chat` and `pgbackrest-backup-timer` are in config.yaml with **zero checks ever** — scored 100 at low confidence rather than omitted, because "configured but never checked" is a finding, not an absence. The mute waiver landed as specified and required modelling `notifications.tray` backend-side for the first time: a projects.yaml-contributed service has no `mute` field, so that list is the only way to declare one expected-down. **Live result: 17 services scored, mean 96.5 — `venture-assistant` 68, `internet` 77, `alfred-frontend` 95, 14 others 100, 8 low-confidence.** 82 new tests — suite 1359 → 1441.

- **2026-08-07 — Session 26: the unmonitored-unit detector.** The mechanical backstop for [guides/monitorable-project.md](../guides/monitorable-project.md): sweep every installed systemd unit, cross-reference it against the projects on disk and the units already wired into projects.yaml/config.yaml, and report the gaps both ways. Tiers 1 and 2 only — and the **absence of a Tier 3 is a decision, not an omission**. Sessions 22 and 24 rank by health-score points and reclaimable megabytes, both directly measurable; nothing here makes two host units meaningfully "twice" one orphan, so `UnitRecommendationInfo` carries **no score field at all** rather than inventing a currency the reader cannot check, and a weekly LLM narrative over findings that change monthly would be prose about nothing. Matching is **path first, name second**, and both earn their place on real data: `alfred-inference` prefix-matches `alfred` but not `alfred-glance` (so longest-wins never has to guess), while `sportsanalyser-pipeline.service` runs `/usr/bin/curl` against an HTTP endpoint and has *no* project path, so only the name fallback catches it. A **third category the plan did not have** proved necessary: `pgbackrest-backup` (the estate's only database backup) and `ethernet-optimise` are hand-written, real, unmonitored, and map to no project — the spec's path-match filter would have dropped them alongside genuine distro units. They get a config.yaml `services:` snippet, not a projects.yaml one, because a projects.yaml endpoint **without a `url` is inert**: `to_monitored_services` skips it, so the entry would look wired and check nothing. **Four things only the live run found.** (1) The planned `pacman -Qo` ownership query is unnecessary — every distro unit in `/etc/systemd/system` is a symlink into `/usr/lib` (that is what `systemctl enable` installs) and every hand-written one is a real file, so `is_symlink()` is the same test with no subprocess and works off Arch. (2) **Three of the four named validation targets are orphans, not uncovered units**: `~/projects/MCP` and `~/Documents/Programming/MCP` no longer exist, so `ticktick-sync`, `ticktick-sync-db` and `offline-agents-dashboard` have dead `WorkingDirectory` paths, as does `garmin-sync` — all failing every start, silently, for as long as nothing watched them. (3) `sportsanalyser-pipeline` was **already wired**, in config.yaml rather than projects.yaml, so SportsAnalyser comes back clean exactly as predicted. (4) **Adding an agent touches four places**: `sysadmin.alerts` has a `chk_alert_agent` CHECK constraint enumerating the four known agents, so the first live run was rejected by the database *after* the scan succeeded (migration 007 widens it; a test now pins the constraint list to `self_monitor.AGENT_NAMES`), and the self-monitor's own hardcoded registry is the fourth — without it the new agent would run entirely unwatched by the service whose job is watching agents. The alert is **one rolled-up warning re-raised only when the count changes**, because `raise_alert` inserts unconditionally and a 6-hourly sweep would otherwise add four rows a day forever — SNAG-AGENT-002 in a new costume. Counts are exhaustive by construction (`scanned = monitored + folded + findings`) after the first draft *inferred* "monitored" and reported 20 where the truth was 12. **Live result: 44 units seen, 6 excluded, 38 scanned → 12 monitored, 8 timers folded into their oneshot service, 11 orphaned, 0 unmonitored, 7 host.** Zero unmonitored findings is the headline: every live project's units are already wired, and the estate's real debt is 11 dead units plus 7 unwatched host services. 109 new tests — suite 1276 → 1385.

- **2026-08-06 — Estate triage: the board is now 6 rows instead of 18.** The status declarations that make the roadmap machinery worth having. `PupilProgressTracker` and `customer-churn-model` **moved to `~/projects/archive/`, not deleted** — the estate's existing convention, reversible, and anything under `archive/` is inferred archived without a projects.yaml edit. The distinction mattered: PupilProgressTracker is fully pushed to GitHub (0 unpushed) so deleting it would have been safe, but **customer-churn-model has no remote and its single commit is unpushed** — `rm -rf` would have destroyed 7 files that exist nowhere else, which is exactly the risk `no_remote` is ranked above everything to prevent. Seven projects declared `dormant` (staleness unpenalised, roadmap advice waived, still scored on everything else): `sports_analyser`, `daiy`, `BSL-Translator`, `BudgetApp`, `InvestingAssistant`, `terrible`, `portfolionew` — each annotated with the last commit that changed **code**, ignoring the bulk `~/projects` reorganisation commit that touched every repo. Declaring SportsAnalyser dormant *is* the resume-or-park decision its 152-day stalled flag was asking for; its endpoints stay monitored because the services are still running. `Athenaeum` is deliberately left **active** despite being idle: marking it dormant would waive the advice while 2.9 MB of real source still has zero commits and no remote. Board: 18 rows → **6** (Alfred, ImbaBots, sysadmin-service, venture-assistant, alfred-glance, Athenaeum), 0 stalled; 25 with `include_inactive=true`.

- **2026-08-06 — Estate init: 14 repos given the standard document set by a 14-agent fan-out, and the run found two more bugs in the scanner.** One agent per repo, each followed by an independent verifier — 28 agents, 0 errors, ~4 minutes, ~1M subagent tokens. Guardrails: create-only (never overwrite), never write `handoff.md` (the hook owns it), never touch git state, nothing invented. Independently confirmed afterwards by `git status --porcelain` across all 14: **no pre-existing file was modified anywhere** — the ` M` entries in ImbaBots (`.gd` source) and venture-assistant (reddit/producthunt fetchers) are the owner's in-progress work, which the verifiers correctly attributed by mtime rather than blaming the agents. 3 repos correctly received nothing (Alfred, alfred-glance, SportsAnalyser already conform); 11 gained 1–5 documents. **Two real bugs surfaced, both fixed.** (1) `first_unchecked_task` accepted unedited template scaffolds, so InvestingAssistant's board entry read `_Task 1_` — a syntactically perfect, semantically empty task list. `is_placeholder` now skips `_Task 1_`/`_Description_`/`TODO:`-style items and falls through to git, deliberately conservative because a false positive silently hides real work. (2) `_latest_snapshot_query` has no freshness test, so **a project deleted from disk keeps its final snapshot forever**: `PA-worktrees` was removed during the reorganisation and still held a board row two days later with a health score and a next action. The board now drops rows more than an hour behind the newest scan stamp. Board went 18 rows → 15, all with real next actions. Also archived three empty shells (`DotaImprover`, `TeacherPlanner` — a `.git` and nothing else) and removed a `projects.yaml` entry pointing at a path that does not exist, which was SNAG-CONF-001 being reintroduced by hand. **Not fixed, flagged only** (the no-overwrite rule held): Alfred's README still says "Ollama (local)" and "no application code yet" — both false since ADR-0052 and seven shipped domains — and alfred-glance's says "Pre-skeleton. No Android code yet." 26 new tests — suite 1250 → 1276. Nothing is committed anywhere; every agent-written file is untracked and reviewable.

- **2026-08-06 — Session 28 follow-up: the board's first real use found two presentation faults.** Asked why ImbaBots (ongoing) "didn't get flagged", when it had been — `top_action: "Write a README.md"`, plus a roadmap item, plus a genuinely useful git-derived next action (`M5-T04: tier-matched garage sparring dummies`). It was invisible for two separate reasons, both now fixed. **The board defaulted to neglect order**, putting an actively-developed project at row 12 of 18 while abandoned ones led — correct for "what have I let slide", exactly backwards for a page opened to see current work. `?sort=` now takes `activity` (default) or `neglect`; ImbaBots is row 2. **`GET /api/projects/actions` is saturated by a single systemic finding**: 11 projects share one `no_remote` risk, risk sorts before everything, and roadmap advice is worth 0 points by design — so the default limit of 10 returned nothing but "Add a git remote", and `total_available: 68` did not say *what kind* of advice had been cut. The response now carries `dropped_by_kind`, because a list that silently drops a whole category reads as "there is nothing else". Roadmap docs and basic hygiene were also written into Contract 1 of [guides/monitorable-project.md](../guides/monitorable-project.md) as the estate standard — waived for dormant/archived, with the note that **declaring `status:` is the higher-leverage move than writing any document**: an undeclared project defaults to active, which is the whole reason the board showed 18 for a four-project estate. 5 new tests — suite 1250 → 1255. **Open decision**: whether missing roadmap docs should cost health-score points (currently not — it would move every active project at once and could fire alerts as a side effect).

- **2026-08-06 — Session 28: Roadmap findings + the estate board.** The scanner has always answered "how tidy is this directory" and never "what was I doing and what comes next"; the only document it read was `README.md`, and only to check the file existed. Four pieces, built so Alfred can show the estate **without ever reading a directory** — sysadmin does the filesystem work and hands over JSON. (1) A global **SessionEnd hook** writes `docs/sessions/handoff.md` in whatever repo the session ran in. This replaces an instruction that was never true: `CLAUDE.md` has said "postflight generates handoff" for months, `claude-preflight.sh:20` dutifully looked for the file, and `claude-postflight.sh` contains no handoff code at all — hence an empty `docs/sessions/` after four months of sessions. The hook refuses to write when a session changed nothing, so asking one read-only question can't overwrite a real handoff with "no changes". (2) `sysadmin/services/roadmap.py`, a pure parser resolving a **next action** in preference order handoff → tasks → git: the plan says what was intended, the handoff says where work actually stopped, and when they disagree the record wins. (3) `findings["roadmap"]` recorded by the organiser with **no score deduction** — deducting would move every active project's score at once and could trip alert thresholds as a side effect of adding a feature, so roadmap advice ships at 0 points using the `no_remote` precedent, waived entirely for dormant/archived projects (nagging a deliberately parked repo to write a session handoff is busywork dressed as progress). (4) `GET /api/projects/board` — one call, contract-pinned, pre-sorted stalled-first then longest-idle, plus a capped `"Pick This Up"` briefing section. **Age qualifies content**: a next action from a handoff older than 30 days is not today's task but a resume-or-park decision, and `next_action_source` (`handoff`/`tasks`/`git`) tells the consumer how much is actually known — a git commit subject standing in for a next action must not render like a handoff-authored step. **Two faults only the live run caught**, both invisible to the fixtures: Alfred keeps its handoff at `docs/roadmap/handoff.md`, not `docs/sessions/`, so the estate's busiest project returned nothing; and its tasks file tracks sessions in a status **table** rather than checkboxes, so a box count returned `0` open tasks for it — `open_tasks` is now `None` ("not measurable") versus `0` ("measured, empty"), the same unchanged-vs-unknown distinction the disk review already draws. Verified against the live DB: 18 active projects, SportsAnalyser correctly flagged stalled at 136 days. Consumer side specced in [guides/alfred-projects-page.md](../guides/alfred-projects-page.md). 48 new tests — suite 1202 → 1250.

- **2026-08-06 — Maintenance: venture-assistant wired into monitoring; three llama-servers found running on CPU.** Config-only in this repo, but the wiring exposed a live estate fault. venture-assistant had four unmonitored user units and no projects.yaml entry: `venture-chat.service` (granite-3.1-8b, :8080) is now its `backend` — llama.cpp's own `/health`, not an app API, because the project has no backend yet (8300 stays reserved for one) — with `venture-embed` (:8082) and `venture-enrich-nightly.timer` in config.yaml's service list per the one-backend-per-project limit and the oneshot→timer rule. `venture-chat-large.service` is deliberately unmonitored: it is `static`, up only during the 02:00 drain, and would alert 23 hours a day. **The fault**: `alfred-inference`, `venture-chat` and `venture-embed` had all been loading their models into system RAM since installation — `-ngl 99` is a request, not a constraint, and at boot they start before amdgpu is ready, so llama.cpp logs `no devices with dedicated memory found` and falls back to CPU while the unit stays `active (running)` and `/health` returns 200. Granite was doing CPU inference at 14.8 GB RSS. Nothing in the estate could see it: the health check curls a port, and both Alfred's and venture's pre-dispatch GPU guards sample busy-% — which reads *idle* precisely because nothing is on the card. **`After=dev-dri-renderD128.device` does not fix this** and was tried first: udev does not TAG the DRM render node with `systemd`, so that device unit is permanently `inactive (dead)` and ordering against it is a no-op (`systemctl --user show dev-dri-renderD128.device -p ActiveState`). The working gate is `~/.local/bin/wait-for-dgpu`, a 45 ms `ExecStartPre` that polls `llama-server --list-devices` for the adapter *by name* — not by `Vulkan0`, since the index is positional and the iGPU can be the only device enumerated early in boot — and exits non-zero on timeout so `Restart=on-failure` self-heals rather than serving silently from RAM. A second fault surfaced from the VRAM arithmetic: the 02:00 drain (first ever run scheduled tonight) needs ~14.8 GB while granite holds ~6.1 GB of the ~18.5 GB free, so `venture-chat-large` now `Conflicts=`/`After=` `venture-chat` to evict it, and `venture-enrich-nightly` gained a second `ExecStopPost` to start granite again — `Conflicts=` does not put it back, and without that line the daytime trickle would have stopped after the first night. `venture-embed` gained `-ngl 0` to make its documented CPU-only intent enforced rather than accidental. Verified live end to end: all three now show `Vulkan0 model buffer size`, the eviction cycle was replayed by hand (11.9 → 20.4 → 11.9 GiB, all endpoints 200), and Alfred's in-repo unit template was updated to match so the installer does not undo it. Session 26 gained **port-registry reconciliation** (unregistered listeners, contended defaults like the 8080 venture holds, and real collisions), and the port registry in the monitorable-project guide gained the three llama-server rows plus a "never take a tool's default port" rule. 123 config tests green. **Needs `sudo systemctl restart sysadmin.service` to take effect.**

- **2026-08-06 — Session 24 Tier 3: weekly LLM-narrated disk review.** `sysadmin/services/disk_review.py` plus a `disk_reviews` table (migration 005 — a separate table from `project_reviews` rather than a shared one with a discriminator, so neither migration can disturb the other's rows). Its facts come from **two tables on purpose**: occupancy delta from `resource_snapshots`, junk deltas and per-kind reclaim from `filesystem_audits` via Tier 2. A week where reclaimable junk grew 3 GB while occupancy fell is a different story from one where both rose, and a review built on either table alone cannot tell them apart. Baselines are the oldest row inside the window, and a lone audit is explicitly *not* its own baseline — deltas come back `None` rather than 0, because "unchanged" and "unknown" are different answers. Four surfaces mirroring the portfolio review: `GET /api/files/review`, `POST /api/files/review/generate`, a Monday 05:45 cron (staggered after the 05:30 project review so only one llama-server generation is in flight) and a "Weekly Disk Review" briefing section — `_build_review_section` is now parameterised by model, so the 8-day freshness rule exists once instead of per review kind. **The Session 23 numbers rule turned out to need strengthening, not just obeying.** The first live generation reproduced the failure in a worse form: handed a prompt listing "25.0 GB across 50 directories" *and* an explicit "do not restate any figure", dria-agent-a-3b restated them and then invented **"each consuming 5GB"** — a quotient derived from data the prompt itself had supplied. Instructing a model not to use a number it can see is a request; not showing it one is a constraint. `build_review_prompt` is now figure-free by construction — sizes become bands ("very large"), categories become named phrases (`KIND_PHRASES`, because Tier 2 titles like "Clear 11400 stale downloads" carry counts in the title itself), occupancy becomes a direction plus a horizon — and a test asserts no digit reaches the model outside API paths. Re-verified live against llama-server: zero figures in the model's prose. It also ignored "no markdown, no headings, no lists" on both attempts, so `strip_markdown` removes headings, bullets, ordered-list markers and bold emphasis deterministically. Read transaction is committed before inference (the other Session 23 rule — this host's `idle_in_transaction_session_timeout` is 1 min), asserted by an ordering test. 55 new tests — suite 1147 → 1202.

- **2026-08-06 — Session 24 (Tiers 1–2): File organiser recommendations + forecast promotion.** The file organiser's mirror of Sessions 21–23, with a different currency: **reclaimable megabytes**, not health-score points. That difference drove the design. The new pure `sysadmin/services/file_recommendations.py` gets its own `FileRecommendationInfo` contract rather than reusing `RecommendationInfo` — one `points` field meaning "score recovered" or "megabytes" depending on which producer filled it would be unreadable at the call site. And the currency turns out to apply to only three of the finding types: duplicates, old downloads and stale caches free space, while misplaced files, empty dirs and similar folders free **nothing** (moving a file reclaims no bytes), so those price at 0.0 MB and rank by `item_count` beneath anything with real megabytes rather than being given an invented currency to compete on. Large files are a fourth case — measurable but not reclaimable, since only the user knows which are junk. Stale project dirs split in two: caches (the existing endpoint removes them) and **rebuildable** dirs (`node_modules`, `.venv` — 25 GB on this box, no executor, so the advice names the manual step, Session 22's convention). New `GET /api/files/actions` mirrors `GET /api/projects/actions` and is the only `/api/files/*` route that reads a second table: `filesystem_audits` tracks junk *accumulation*, only `resource_snapshots` knows disk *occupancy*, and occupancy is what answers "when does the disk fill up" — so a projected 80 %/90 % crossing inside 30 days outranks every byte total, the way `no_remote` outranks score arithmetic. The forecast maths moved out of the tray to `sysadmin/services/forecast.py`; not a pure move, because `disk_series()` took a `ResourceHistoryResponse` the backend never has — the primitive is now `disk_series_from(entries, mount)` over `(timestamp, disk_usage)` pairs, which an ORM row and a parsed contract both produce, with the contract version a one-line adapter. `_compute_reclaimable_forecast`'s hand-rolled least-squares was deduped against the promoted `linear_fit`. **Two bugs only the live run caught**, both invisible to the mocked tests (the Session 23 lesson repeating): the `findings` blob is truncated to 50–100 entries per category before storage, so the endpoint reported 200 misplaced files against an actual **11,877** and 100 downloads against **11,400** — now fixed by passing the audit row's own count columns, with sizes summed from a truncated list labelled a lower bound ("at least 25 GB") and the note saying "largest N" only for the lists the agent really sorts by size; and duplicates/old downloads recorded no sizes **at all**, making the currency uncomputable, so `FileOrganiserAgent._scan` now stores `size_mb` per download and `size_mb`/`reclaimable_mb` per duplicate group (priced at "delete all but one copy") and sorts both before truncating so the cap keeps the biggest wins — pre-existing rows read tolerantly and say "sizes were not recorded — rescan to price it" instead of claiming 0 MB. Verified against the live DB. **Tier 3 (the weekly disk review) is deferred to a second sitting.** 48 new tests — suite 1099 → 1147.

- **2026-08-05 — Maintenance: SportsAnalyser fully wired into monitoring + tier-pattern ideas captured.** Config-only session. The `sports_analyser` projects.yaml entry had URL-only health checks while three live *user* units sat unmonitored: backend and frontend now carry `systemd_unit` + `user: true` + journal log sources (warning filter), and a new `frontend` block covers Next.js on :3200. The daily pipeline is `Type=oneshot`, so per the alfred-evaluate rule its **timer** (`sportsanalyser-pipeline.timer`) is monitored via config.yaml's service list instead — projects.yaml can only model backend/frontend. Verified: config parses, merge produces the three services + two log sources, all units live and endpoints healthy, 118 config tests green. **Needs `sudo systemctl restart sysadmin.service` to take effect** (running since before the edit). Noted in passing: `sportsanalyser-backend.service` is `disabled`, alive only via the frontend's `Requires=` — worth enabling. ideas.md also gained a "repeat the project-manager tier pattern" section with four candidates (file organiser tiers, service reliability scoring, **unmonitored-unit detector** — which would have caught today's gap automatically, plus `garmin-sync`/`deadlock-api-ingest`/`ticktick-sync`/`offline-agents-dashboard` still uncovered and eight orphaned PA units — and log aggregator tiers folded into SNAG-AGENT-002). Follow-up the same day: **`docs/guides/monitorable-project.md`** writes the shape down as a contract — scanner rubric (automatic) vs service integration (manual: port registry with 8300/3300 reserved next, canonical `GET /api/health` for new projects, `<project>-<role>.service` user units, oneshot→timer, same-day projects.yaml wiring with `user: true`, verify via `/api/sysadmin/status`) — and `~/.claude/CLAUDE.md` now points every future new-project Claude session at it, so conformance is enforced at creation time rather than remembered. Roadmap housekeeping closed the day: Sessions 10–23, the 2026-07-24 maintenance work and nine fixed SNAGs moved verbatim to `archive/completed_2026-08-05.md` (snag_list.md keeps a one-line index per fix), the live follow-ups those sessions had buried were hoisted into the tasks.md Backlog before archiving, and the four tier-pattern ideas became **Sessions 24–27**.

- **2026-08-04 — Session 23: Project-manager Tier 3 — weekly LLM portfolio review.** The last tier: llama-server narrates the portfolio weekly. `sysadmin/services/project_review.py` gathers structured facts — latest score per project, week-on-week delta (latest vs the *oldest snapshot inside the window*, so no scan cadence is assumed), and each project's top three recommendations — builds a bounded prompt (250-word limit; a 3B model rambles unconstrained), and asks `LLMClient` for a four-section narrative (what moved / what's decaying / archive candidates / next week's focus). **The LLM is optional at every step**: unavailable inference falls back to a deterministic digest of the same facts with `llm_used: false` — built this way because the GPU was busy during development, which forced the right design: GPU-busy is a normal state, not an error. Reviews persist in the new `project_reviews` table (migration 004 — whose first draft the schema-drift guard rejected for a nullability/index mismatch between model and migration, exactly its job) with the structured inputs stored in `stats` so the prose stays auditable against its data. Surfaced three ways: `GET /api/projects/review` (latest) and `POST /api/projects/review/generate` (on demand, auth), a Monday-05:30 cron (`schedules.review_*`, before the briefing, gated by `agents.project_organiser.weekly_review`), an `info` alert on generation, and a "Weekly Project Review" briefing section while under 8 days old. All 20 new tests mock inference — the GPU was never touched — but a live fallback-path run against the real DB stored review #1 and caught a real bug the mocks missed: Session 22's recommendations read `stale_branches` findings as strings when the scanner stores dicts; fixed with the real shape pinned in tests. The deferred live-inference check ran the same day once the GPU freed and caught two mock-invisible issues, both fixed: the review held a DB transaction across minutes of inference and this host's `idle_in_transaction_session_timeout=1min` killed the connection (now commits the read transaction before calling the LLM); and the 3B model fabricated the numeric "what moved" section under two different prompts, so the narrative is now **hybrid** — `build_movers_section` computes movement deterministically and the model writes only the qualitative sections, which it grounds accurately. Suite 1076 → 1099.

- **2026-08-04 — Session 22: Project-manager Tier 2 — recommendations engine.** The organiser stops at "this project scores 45"; the new engine answers "and here is how to get the points back". `sysadmin/services/recommendations.py` is a pure module (no DB, no FastAPI) that maps a snapshot's findings to ranked advice where **every item mirrors exactly one scorer deduction** — `points` is the score recovered by acting on it, cross-checked by tests against the analyser's arithmetic — and status-awareness matches the scorer too: a waived deduction (dormant staleness, archived branch rot) produces no advice, because there are no points behind it. The deliberate exception is `no_remote`: it never cost points (the scorer only records it) but surfaces as a 0-point `risk` item ranked above everything, because "the only copy of this repo is on this disk" outranks score arithmetic. Where a safe executor already exists the `action` field points at it (branch prune's dry-run endpoint, the todos listing); otherwise it names the config change or command. Two endpoints, both `response_model`-enforced with tray re-exports: `GET /api/projects/{name}/recommendations` (advice + `potential_score`, clamped to 100) and `GET /api/projects/actions` (portfolio-wide top wins, risk-first then points-desc, `limit` honest via `total_available`) — the latter declared **before** `/{name}` so it isn't captured as a project named "actions", with a regression test pinning that. The ideas.md housekeeping section from the reorganisation migrated as promised: the missing-remote follow-up is now served natively by `/actions` after every scan; the un-detectable items were reframed as detector ideas. 25 new tests — suite 1051 → 1076.

- **2026-08-04 — Session 21: Project-manager Tier 1 — deep discovery + project status.** Prompted by the same-day reorganisation of `~/projects` into category folders (`apps/`, `web/`, `ml/`, `games/`, `learning/`, `archive/` — see `docs/roadmap/ideas.md` for the follow-ups it parked), which the organiser's top-level-only discovery couldn't see into: it found 3 projects where 24 exist. Discovery is now depth-aware (`agents.project_organiser.discovery_depth`, default 2): a directory with a project marker IS a project and is never descended into (vendored sub-repos stay invisible, e.g. habitTracker's inner repos), while a marker-less directory is a *category* searched one level further. Projects also carry a **status** — `active | dormant | archived` — declared per entry in projects.yaml (`status:`, matched by the same path → name → basename lookup as `alert_threshold`, now shared as `ProjectsConfig._setting_for`) or inferred from location: anything under `<projects_root>/archive/` is archived, all else active. Status shapes the rubric rather than gating the scan: dormant waives the staleness deduction (resting on purpose is not a defect), archived also waives branch hygiene, and both still score docs/TODOs/locks so the number keeps meaning "how tidy is this directory"; the waived facts are still *recorded* in findings, which also gain the status itself (JSONB — deliberately no DB migration or contract change). Alerting: archived projects suppress the default floor via `_effective_threshold` (extracted from `_execute` precisely so it could be tested pure) but an explicit `alert_threshold:` still wins — the PA entries switched from `alert_threshold: 0` to `status: archived` as the worked example. Verified against the real tree: 24 projects discovered, all 8 archive/ residents inferred archived. 28 new tests — suite 1023 → 1051.

- **2026-07-24 — Maintenance: two runtime-environment bugs found by running for real.** Both surfaced the moment the live `sysadmin.service` picked up the Alfred config, and both had passed verification because verification happened in an interactive shell on the API's event loop — neither condition holds inside the daemon. **SNAG-SYSD-001**: `systemctl --user` locates the session bus through `XDG_RUNTIME_DIR`, and a system unit's environment holds only `PATH`, so *every* `user: true` systemd check failed — and because the old helper ignored the exit code and read the empty output as "no ActiveState → not active", a live `alfred-evaluate.timer` was reported `critical`. `sysadmin/utils/systemd.py` now builds the subprocess environment in one place and injects `XDG_RUNTIME_DIR` (default `/run/user/<uid>`) for user-scope calls, fixing the status check, the details endpoint and start/stop/restart together; `DBUS_SESSION_BUS_ADDRESS` is deliberately not derived, having been proven unnecessary against the live bus. Crucially a failed *query* is no longer a verdict about the *unit*: it raises `SystemdQueryError`/`UserBusUnavailableError` → status `"error"`, which raises no alert and touches no streak counter, while a genuinely inactive unit stays `critical`. Migration 003 widens `chk_health_status` to permit `'error'`, a value `_check_service` could always return but the DB had never allowed. **SNAG-AGENT-003**: `SysAdminAgent.startup()` built one `httpx.AsyncClient` on the API loop, but agent runs happen on APScheduler threads under `asyncio.run()`, which closes its loop afterwards — so pooled keep-alive connections outlived their loop and `llama-server` reported `unreachable / "Event loop is closed"` while curl answered in a millisecond, intermittently and per-host depending on which pooled connections had already been dropped. New `sysadmin/utils/async_http.py` (`LoopBoundClient`) lends a long-lived client out only on the loop that built it and hands anywhere else a short-lived one closed on exit; the agent now opens a run-scoped pool inside `_execute` and has no startup hook at all. The audit for the same pattern found `LLMClient` (identical live exposure via the log aggregator) and `Notifier` (latent), both converted. The regression test drives a real loopback server across two successive `asyncio.run()` calls — a mock transport holds no sockets and cannot reproduce this — and includes a guard asserting a naively shared client still fails, so the harness is known to be able to catch it. Both fixes verified against the live system with the daemon's environment simulated. 33 new tests — suite 990 → 1023. **The running `sysadmin.service` needs a restart (system unit, requires sudo) to pick this up.**
- **2026-07-24 — Maintenance: PersonalAssistant → Alfred migration.** PA is dead and Alfred replaced it, so everything the service pointed at PA was repointed or retired. **projects.yaml**: the `personal-assistant` entry (whose `path` — `/home/gaddi/projects/personal-assistant` — had *never existed*, the real directory being `PersonalAssistant`, so its health check had been silently broken) is replaced by `alfred` → `/api/health` on :8100 and :3100 for the Nuxt frontend, both `alfred-backend.service`/`alfred-frontend.service` **user** units; `alfred-glance` added scan-only (Android/Gradle, no service, no port) alongside `daiy`. This exposed a real gap: Session 15 added `user: true` to `MonitoredService`/`LogSource` but **never plumbed it through the projects.yaml path** — `ProjectEndpoint`/`ProjectEndpointLog` had no such field and `to_monitored_services()`/`to_log_sources()` dropped it. Now added (log blocks inherit their endpoint's scope unless they override it), because the failure mode is silent and permanent: proved live that `read_journal("alfred-backend.service", user=True)` returns 500 entries where `user=False` returns 0, which is exactly how the old PA entries rotted unnoticed. **alfred-evaluate** is monitored via `alfred-evaluate.timer`, not its service — the service is `Type=oneshot` and therefore inactive-by-design between its daily 08:00 runs, whereas a timer holds `ActiveState=active` (`SubState=waiting`) while armed, so the ordinary systemd check reads it correctly and an inactive timer genuinely means the schedule has stopped; no special-casing needed. The dead PA repos (`PersonalAssistant`, `PersonalAssistant-auto`, `PA-worktrees`) are **retired but retained** with `alert_threshold: 0` — they stay visible in the dashboard and remain branch-pruning targets, and since scores are clamped at 0 and the test is `score < threshold`, 0 is mathematically never-alert (they score 15/10/80 against the global floor of 40, so they *would* otherwise alert on every scan). **PA integration disabled** via a new `personal_assistant.enabled` flag (model default `True`, so configs predating it are unchanged): `Notifier.send_notification` and `send_briefing_data` now short-circuit before any HTTP call, logging once per process at INFO rather than warning per attempt, and the briefing's daily "delivery failed" warning drops to DEBUG when the integration is off. Kept deliberately as a dormant feature flag, not deleted, so it can be repointed if Alfred grows an inbox — Alfred's full 67-path OpenAPI schema has no notification/briefing/digest route today. Also: Alfred's :3100 origin added to `service.cors_origins` and the `mute_services` comment re-exampled off PA. All nine monitored services verified `ok` against the live config. 12 new tests — suite 978 → 990.
- **2026-07-24 — Session 20: Project scoring & branch hygiene.** The project organiser can now act on the branch rot it reports: `POST /api/projects/{name}/branches/prune` (`sysadmin/services/branch_actions.py`) follows Session 18's safety model — POST behind `require_auth`, **dry run unless the body sets `confirm: true`**, and the same manifest either way, one row per local branch with its last commit date + sha, merge state, upstream/ahead counts and the reason it is (in)eligible. Eligibility is "merged into the default branch **and** stale for `stale_days`+ days", with merged-ness taken from git (`repo.is_ancestor`), never inferred from dates; deletion uses `git branch -d` so git re-checks it independently. The dangerous case needs **two flags** (`include_unmerged` on the request *and* `branch_actions.allow_unmerged_delete` in config, both default off, re-checked at execution), and the default branch, `protected_branches` globs, the checked-out branch, worktree branches and anything ahead of its upstream are never deleted regardless. The default branch is **detected** (remote HEAD → `init.defaultBranch` → conventional names → sole branch) and when it can't be, nothing is planned. Paths confined to `projects_root`, `max_deletions` capped at 20 per call (a request may only lower it), `min_stale_days: 7` floors the window. On the real PA-auto (224 branches, all merged) a dry run plans 20 and reports the rest as capped. Scoring also got two fixes: the hardcoded `< 40` health alert became `agents.project_organiser.alert_threshold` with a **per-project override in projects.yaml** (`alert_threshold:`, matched by path → managed name → path basename, absent = global, so existing files behave identically), and the TODO deduction is **capped at 30 points** (`max_todo_penalty`, `null` = uncapped) with the raw figure kept in `findings.todo_penalty_capped` — PersonalAssistant (327 TODO + 38 FIXME) and PA-auto (290 + 18) were being docked 185/154 and pinned at 0, so nothing they improved could show. New contracts `BranchCleanupResponse`/`BranchInfo` with `response_model=`. 107 new tests, all against throwaway `git init` repos under `tmp_path` — suite 871 → 978.
- **2026-07-24 — Session 18: File organisation & cleanup actions.** First endpoints that move and delete real files, so the safety model led the design and lives in one dependency-light module (`sysadmin/services/file_actions.py`): **dry run by default** (body must carry `confirm: true`), POST-only behind `require_auth`, source *and* destination resolved before the root check so `..`/symlinks cannot escape `scan_root`, symlinks never followed, `.git`/`node_modules`/dot-dirs/`projects_root` never entered, existing destinations skipped rather than overwritten (with an `O_CREAT|O_EXCL` reservation closing the rename race), and **delete means the XDG trash** — a minimal freedesktop implementation instead of a new dependency, which refuses (rather than silently copy+deletes) when the file is on another filesystem; overriding needs `force_delete` *and* `actions.allow_permanent_delete`. Three endpoints, one shared manifest contract: `POST /api/files/organise` (new **books** and **archives** categories, loose code in `~/` flagged never moved, PDFs routed Books/ vs Documents/ by filename markers then a bounded `/Type /Pages` page-count probe — unknown always means Documents), `POST /api/files/clean/duplicates` (reuses the agent's fingerprint via a promoted `file_hash()`, keeps newest or largest, retain-one-per-group asserted in code and re-checked before execution), and `POST /api/files/clean/downloads` (archive or trash past a configurable age). Category → folder mapping is now config-driven in the new `agents.file_organiser.actions:` block. Also fixed Session 17's finding that **file_organiser had never run**: APScheduler's `IntervalTrigger` puts the first fire at `now + interval`, so a 24h job never fires on a box that restarts daily — hours-scale agents now get an explicit first run 60s after startup. 118 new tests, all on `tmp_path` trees — suite 576 → 694.
- **2026-07-24 — Session 19: Dashboard enhancements.** The file organiser's audit finally has a UI: a new **Files tab** (`sysadmin_tray/dashboard/files_tab.py`) shows the `GET /api/files/status` summary and reclaimable total, a **Quick Wins** card (empty dirs, stale caches, cache size) and a **Disk Growth Forecast** card, plus a findings table switchable between duplicates, misplaced files and large files. Charting stayed dependency-free — `sysadmin_tray/widgets/trend_chart.py` generalises the `QPainter` approach already used by the Overview tab's resource chart, and drives both the new **per-project health trend** (Projects tab cards are now clickable; `GET /api/projects/{name}` already served the stored score history, which arrives newest-first and is reversed for plotting) and the forecast card. Forecast maths lives Qt-free in `sysadmin_tray/forecast.py`: `/api/files/trends`'s regression is formatted as-is for reclaimable growth, while disk-threshold crossing dates (80 %/90 %) come from a tray-side least-squares fit over 30 days of `resources/history` — junk accumulation and disk occupancy are different series. **Read-only by design**, since the file-action endpoints were being written in parallel; the one wired action is the pre-existing stale-cache clean, behind a confirmation dialog that names `__pycache__`/`.pytest_cache`, states the megabytes, and caps the promised empty-dir count at the 50 the endpoint really removes. `/api/files/*` and project-detail shapes appended to `sysadmin/contracts.py` (parse-side only); a 404 there means "no scan yet" and renders as an empty state, not an error. 177 new tests — suite 576 → 753.
- **2026-07-24 — Session 16: Notification calm.** New `NotificationPolicy` (sysadmin_tray/notifications.py) owns the shared per-fingerprint state and decides what the tray says: D-Bus `replaces_id` reuse so a state change replaces its popup instead of stacking (verified live), a 30-minute flap cooldown that rolls repeats into "X flapped N×", one "3 new alerts" summary when several arrive in a poll, "Snooze 1h" action button plus per-service `mute: true` for expected-down services, progressive escalation (quiet opener → persistent critical after 3 failing polls), `transient` hints so feedback toasts skip KDE's history, desktop DND via the `Inhibited` property (more restrictive of app-DND/desktop-DND wins; app DND still decides criticals), and an opt-in hourly warning digest. All tunables live in the new `notifications.tray:` config block. 93 new tests — suite 364 → 459.
- **2026-07-24 — Session 17: Self-monitoring.** New `GET /api/sysadmin/self` (`sysadmin/services/self_monitor.py`) reads `agent_runs` back for the first time: per-agent last run/status, duration trend, consecutive failures, and a *stalled* flag whose window is derived from each agent's configured interval (`interval × self_monitor.stall_grace_multiplier`, floored at `min_stall_grace_seconds`) rather than hardcoded — never-run agents are deliberately not flagged. The SysAdmin agent raises/auto-resolves `"<agent> agent stalled"` alerts from the same report. New SSE endpoint `GET /api/sysadmin/events` (`sysadmin/services/sse.py`, `StreamingResponse`, no new dep) turns the dormant `event_bus.py` into the push path — agents publish `alert.raised`/`alert.resolved`/`agent.run`/`service.status` (buffered until their transaction commits, handed to the API loop via `EventBus.publish_threadsafe` since agents run on scheduler threads), heartbeat comments keep idle streams alive, disconnects unwind cleanly, and the path is access-log-excluded like `/health`. Resource anomaly detection (`sysadmin/services/anomaly.py`) adds z-scores over 7 days of `resource_snapshots` for CPU/RAM/each mount with cold-start and flat-series guards, suppressed when a fixed-threshold alert already covers the resource. New `self_monitor:`/`events:`/`anomaly:` config sections; no schema change. Verified live against the real service and DB. 117 new tests — suite 364 → 481.
- **2026-07-24 — Session 14: Config consolidation + docs.** New `sysadmin/defaults.py` (stdlib-only) is the single source of the API host/port — backend `ServiceConfig` and tray `TrayConfig` both import it. Magic numbers lifted to config.yaml with unchanged defaults: project grade bands (`agents.project_organiser.grade_bands` 80/60/40), reclaimable-space milestones (`agents.file_organiser.reclaimable_milestones_mb` 1/5/10 GB), briefing/retention cron times (new `schedules:` section, 06:00/03:00), CORS origins (`service.cors_origins`). docs/ARCHITECTURE.md rewritten from the real code (was an untouched template) with component diagram. pydantic-settings dropped (unused); confirmed zero env-var reads so CLAUDE.md now says "config.yaml only" instead of referencing a nonexistent .env.example; CLAUDE.md Step 4 test commands filled in. claude-preflight.sh now lists open SNAG count + titles from the Open Issues section only (Fixed Issues no longer inflate counts). 9 new tests — suite 355 → 364.
- **2026-07-24 — Session 13: Test hardening + CI.** Tests now run against the REAL app: `sysadmin/main.py` exposes `create_app()` and conftest builds it with only the lifespan stubbed (routers, middleware, exception handlers, auth deps all production). New shared contracts module `sysadmin/contracts.py` (pydantic-only) is the single source of truth for tray-consumed response shapes — set as `response_model=` on 13 backend routes and imported by `sysadmin_tray/models.py` (hand-copied dataclasses deleted; root cause of SNAG-TRAY-005 gone); Contract Registry in CLAUDE.md filled in. Schema drift guard (`tests/test_schema_drift.py`) found real drift: fixed alembic/env.py double-reflection and added migration 002 (NOT NULL alignment on 22 columns + idx_alerts_active direction) — `alembic check` now clean. New tests for briefing, event bus, app factory, contract round-trips. `scripts/smoke_test.sh` curls the live service (4 checks, fail-fast). GitHub Actions CI (ruff + pytest, headless PyQt6). mypy adopted (8 errors found and fixed, now clean); repo-wide ruff cleanup (191 issues). Suite 327 → 355.
- **2026-07-24 — Session 15: LLM migrated Ollama → llama.cpp.** New `sysadmin/services/llm_client.py` (`LLMClient`) speaks llama-server's OpenAI-compatible API (`POST /v1/chat/completions`, health via `GET /health`); config `ollama:` → `llm:` (url `http://localhost:8081`, model informational — single loaded model). Monitored service + log source renamed to llama-server / `alfred-inference.service`, with new `user: true` support so systemd/journalctl helpers can address *user* units (`systemctl --user`, `journalctl --user`). Verified live end-to-end: real completion, `summarise_with_llm` stored a genuine summary, briefing Overnight Log Summary section populated. 13 new transport-mocked tests — suite now 327.
- **2026-07-24 — Session 12: API authentication.** Shared bearer token (`api.auth_token` in config.yaml) enforced via a FastAPI dependency (`sysadmin/auth.py`, `secrets.compare_digest`) on all seven mutating POST endpoints — service actions, alert ack, DND, scan-all, project/file scans, stale-cache clean. Read-only GETs stay open so tray + PA dashboards keep working. Tray client sends the token automatically (same config.yaml). Unset/empty token → auth disabled with a startup warning (config.yaml is committed, so the committed value is a placeholder — see [guides/api_auth.md](../guides/api_auth.md)). PA-side token wiring is a follow-up in the PA repo. 24 new tests — suite now 314.
- **2026-07-24 — Session 11: Verified bug fixes.** Alert ack returns a real 404 (SNAG-API-001), access-log exclusion fixed to the real `/health` path with the real router under test (SNAG-API-002), blocking psutil calls moved off the event loop via `asyncio.to_thread` in `/ports` and `_take_resource_snapshot` (SNAG-API-003), tray marks connection lost on malformed/skewed API responses and `from_dict` parsing is defensive (SNAG-TRAY-005). 12 new tests — suite now 290.
- **2026-07-24 — Session 10: Resolved uncommitted loose ends.** Removed unreachable StatsPopup (dashboard won; SNAG-TRAY-004), `get_last_commit_date` now checks all branches (SNAG-AGENT-001), removed dead `count_stale_branches` and unused `orphan_detection` flag, narrowed `get_repo` exception handling with logging. Promoted codebase-review backlog to Sessions 10-20 in tasks.md.

_See [archive/completed_2026-03-23.md](archive/completed_2026-03-23.md) for full history._

---

## Notes

- Port 8500 (overridden from spec's 8100)
- Schema isolation: sysadmin.alembic_version avoids collision with PA
