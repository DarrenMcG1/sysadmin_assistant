# Handoff — 2026-08-30

## Next action

Decide whether the six pre-convention files that open the live database — `test_logs_routes.py`, `test_open_alert_predicate.py`, `test_retention.py`, `test_schema_drift.py`, `test_schema_guard.py` and `test_snag_claims.py` — owe premise assertions, because `tests/test_live_drive_premises.py` now measures that they hold the property the `_live` glob is a proxy for and exempts them by name in `PRE_CONVENTION`, so the exemption is a decision nobody has taken rather than one taken and recorded.

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
