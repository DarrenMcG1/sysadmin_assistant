# Handoff — 2026-08-30

## Next action

Act on estate message `d1939cf7` before Monday 05:30 by pointing `judge_queue_invariants`'s wait predicate at `oldest_unexplained_wait_seconds` instead of `oldest_waiting_seconds` and keeping the 900-second threshold, because the estate's weekly review now takes a GPU lease and queues behind `venture-enrich-nightly` for a measured 915–1038 s every Monday — a third cause the "Estate queue starved" text does not name, namely the queue working as designed — and both new fields are already live on 8400 (verified 2026-08-30: `waiting_reason` and `oldest_unexplained_wait_seconds` both present on `GET :8400/api/queue/invariants`), so the change is a one-predicate edit plus its guard and the message is then closed with a note.

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
