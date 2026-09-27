# Notifications — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**Two things speak on this box, and only one of them at a time.** The tray
polls `GET /api/sysadmin/alerts` and owns the notification policy (dedup,
flap cooldown, coalescing, digest — `sysadmin_tray/notifications.py`).
`sysadmin/monitor/desktop.py` is its **understudy**: subscribed to
`alert.raised`, it stays silent whenever that route has been polled within
`notifications.desktop.tray_grace_seconds`, and speaks when the tray is not
running — which was silent altogether until 2026-08-11 (SNAG-CFG-001:
`notifications.desktop` was parsed by pydantic and read by nothing, and
`Notifier.send_notification` had no production caller at all).

Three rules it encodes, each measured rather than assumed:

1. **One notification per incident, not per alert row.** The monitor
   writes one row *per failed check* — 186 for one `venture-assistant`
   outage, 88 criticals a day, 547,814 unresolved `Log error: kernel`
   rows in the table. The daemon speaks only when no other alert with
   that title is open.
2. **Both gates fail closed.** An unreachable database returns "not a new
   incident", because the alternative turns a blip into a storm.
3. **Subscribed, never called from `raise_alert`.** `core` must not import
   a domain, and `_queue_event` buffers until the run's transaction
   commits — so the notifier's query cannot race the insert it reacts to.

Recovery is deliberately **not** announced: `alert.resolved` carries a
match pattern (`"Project % health critical"`), not a subject.

**A detected fault has to keep speaking, and the ladder that makes it do
so lives in `core`** (Session 39). `sysadmin/core/escalation.py` owns
`SEVERITY_ORDER`, `Ladder` and `step_for`. It was put there for the reason
`strip_markdown` was — the two climbers sat on opposite sides of the rule
that `monitor` may not import `projects`
(`tests/test_import_boundary.py`), so "reuse rather than copy" required
the move first. **That reason has since expired and the placement gained
better ones**: the projects domain left on 2026-08-13 and four domains
climb the ladder now — `monitor/stalls.py`, `monitor/failures.py`,
`units/agent.py` and `estate/judgements.py`, with `monitor/desktop.py`
taking `humanise_hours`. The boundary test still names a package that
cannot exist, which makes it a guard against bringing it back rather than
a live constraint.

The failure it fixes is **not** a detection failure.
`self_monitor.build_self_report` caught SNAG-AGENT-003 correctly and
`_check_agent_liveness` raised one row; the raise is then deduplicated
while that row is open (correct — it is what stopped the 1,664-row
pile-up) and the tray fingerprints on `{severity}:{title}`. Net effect:
**the alarm rings once, at the quietest severity, and is silent while the
fault persists.** A warning that fires once is indistinguishable from one
that got fixed.

Four rules, three of them the opposite of the obvious implementation:

1. **Escalation resolves the quiet row and raises a louder one**, never
   updates severity in place — an in-place change keeps the fingerprint
   the tray has already suppressed, so the escalation is recorded and
   never spoken.
2. **The loud rung for a stall is `critical`, and that is about
   persistence, not volume.** `sysadmin_tray/notifications.py` sets
   `transient=False` for `critical` alone, making it the only severity
   the tray leaves on screen. The owner's reported failure was "I never
   saw the toast" — away from the machine — and a transient toast in an
   empty room is the miss, whatever its severity. A nudge, by contrast,
   never reaches `critical`; the two modules' docstrings cite each other
   so the difference reads as deliberate.
3. **The escalation clock starts when the alarm rang, not when the stall
   began.** Anchoring to the stall's own age makes a daemon outage
   produce a wall of criticals on restart — nothing runs while the
   service is down, so every agent is stalled — which charges the estate
   for this application's downtime, the rule
   `GET /api/services/reliability` already encodes as "a gap in the
   series never costs points".
4. **`escalate_after_hours: 24` is measured against the slowest agent.**
   `file_organiser` and `service_discovery` run daily, so a stall that is
   merely late clears within one interval; a shorter gap escalates faults
   about to fix themselves. It cannot make detection faster — that is
   `stall_grace_multiplier`, which is the wrong knob someone will reach
   for, so the config docstring says so.

`Restart=always` made the **crash** case silent the same way:
`sysadmin.service` never entered `failed`, so an `OnFailure=` hook could
not fire. `StartLimitBurst=5` / `StartLimitIntervalSec=600` makes a loop
terminal and `sysadmin-failed.service` announces it, persistently
(`--expire-time=0`) and to journald first — the one destination that does
not need anyone logged in. `tests/test_systemd_units.py` pins the two
halves together, because either alone accomplishes nothing.

**The ladder has two rungs and a third was measured and refused**
(Session 53, `SNAG-ESTATE-003`). Five families deduplicate on an open
row and own no ladder — the estate judge, `monitor/collation.py`, the
unit sweep's roll-up and the two `_raise_judged` covers — so each rings
once at the quiet severity and is silent while the fault stands, which
is Session 39's defect one layer over. The obvious next move is a rung
that repeats without reaching `critical`. **It cannot be heard.** The
tray fingerprints on `{severity}:{title}` and clears
`notified_this_episode` only when that pair is **absent from a poll**,
which a resolve-and-re-raise inside one agent run never produces:
measured against the real policy, a resolved row replaced by a fresh one
carrying a new message produced **no notification at all**, where the
same fault escalated to `critical` spoke and a forked title spoke. The
title is the identity key, so the second is forbidden — leaving nothing
for a third rung to be heard by.

A repeat at an unchanged severity is therefore a **notification**
decision, and it lives where notification policy already does:
`reminder_hours` in `sysadmin_tray/notifications.py`. Four rules.
**The clock runs from when the tray last spoke**, not from
`alert.created_at` — `stalls.py`'s rule, the thing that failed being the
*telling*, and it keeps the one injected clock that makes every window
in that module testable without sleeping. **24 hours is derived, not
picked**: it matches `self_monitor.escalate_after_hours`, the only
escalation gap on this box, so a family that owns a ladder escalates to
a different fingerprint — a new episode, spoken at once — before any
reminder of its quiet rung is due; shorten it and the loud rung becomes
the second thing you hear rather than news. **A reminder is never
transient**, because the failure it fixes is a toast in an empty room
and `transient=False` is what keeps it in the notification history
(`flush_digest`'s rule). **Reminders fold apart from new alerts**, into
`FP_REMINDER` with their own wording: a fault announced yesterday inside
a summary headed "N new alerts" is the one thing a reminder is not.

Two limits, both stated in the code. `digest_mode` never reminds below
`critical` — that mode's contract is that warnings do not interrupt, and
making the digest itself periodic is a separate question about a mode
that is off here. And the policy state is in memory, so a tray restart
re-announces every open fault as new. The third is `SNAG-TRAY-007`:
`monitor/desktop.py` is event-driven off `alert.raised` and shares none
of this, so while the tray is down — the only case the understudy exists
for — a standing fault is still announced once.

**The understudy has a clock now, and the precedence answer is the same
window used the other way round** (Session 55, `SNAG-TRAY-007`).
`monitor/desktop.py` speaks once per incident and is subscribed to
`alert.raised`, so it had no moment at which it could notice that a
fault it announced six hours ago was still open — Session 39's defect
surviving in the one component that exists for the case where the tray
is *down*, which is precisely where Session 53's `reminder_hours` cannot
reach. `DesktopNotifier.sweep_reminders` is that moment, scheduled as
`desktop_reminder_sweep` in `core/jobs.py`.

It is a **job**, not a call at the end of `SysAdminAgent._execute`: an
agent reminding on the notifier's behalf owns a lifecycle
`monitor/desktop.py` holds, which is the second-owner defect this
repository has now found at five scales.

Four rules, three of them the opposite of the obvious implementation:

1. **A watching tray stamps the clock forward; it does not skip the
   sweep.** `tray_grace_seconds` decides precedence on both paths and
   the *action* differs. Skipping leaves `last_spoken_at` at the opening
   notification, so the first sweep after a tray outage restates a fault
   the tray itself restated ten minutes earlier. While something polls
   the route, the last thing said was said by it — and the difference is
   observable **only** in the middle window, which is what the test pins
   and where the first draft of that test had the arithmetic wrong.
2. **The population is what this process announced, never the open
   rows.** A sweep over `resolved IS false` adopts every fault the tray
   was speaking for and announces the lot the moment the tray dies —
   `SNAG-AGENT-005`'s unbounded `SELECT` wired to a notification each.
   The spoken set is in memory, so the query is `title IN (:titles)` and
   a sweep that has said nothing issues no query at all. The cost is
   `SNAG-TRAY-008`, filed rather than implied: a fault raised while the
   tray was up is never adopted, and a restart forgets everything.
3. **Neither number is invented.** `reminder_hours` is the tray's 24 for
   the tray's reason, and because two speakers with different cadences
   make the interval depend on which happened to be running — the thing
   the understudy exists to hide. The sweep's own cadence has **no leaf
   at all**: `max(60, tray_grace_seconds)`, since the sweep asks the two
   questions that window already answers.
4. **A reminder that did not land does not move the clock**, and nothing
   is recorded as spoken until the opening notification has actually
   landed. `send` returns whether it reached a screen, so a missing
   session bus delays a reminder by one sweep rather than by a full
   interval.

A roll-up folds at two and takes the **loudest** rung it swallows
(Session 52's rule): `notify-send` has no `replaces_id`, so six due
reminders would otherwise be six toasts.

**The understudy remembers now, and the reminder it could not reach was
a restart-cadence problem nobody had measured** (Session 115,
`SNAG-TRAY-008`). `DesktopNotifier._spoken` was in memory and the sweep's
population was exactly its keys, so the entry's two costs stood: a fault
raised while the tray was watching was never adopted when the tray died,
and a restart forgot everything. `desktop_notifications` (migration 018)
is the store and `DesktopNotifier._adopt` the scope.

Six rules, four of them the opposite of the obvious implementation and
every one settled against the box rather than by argument:

1. **The number reranks the entry, and the entry could not see it
   because it filed its population as zero.** `sysadmin.service` started
   **111 times in 28.26 days** — median uptime **1.77 h**, mean 6.17 h,
   **5 of 110** lives reaching the 24 h `reminder_hours` asks for. So
   `SNAG-TRAY-007`'s reminder was structurally unavailable on **95 %**
   of this daemon's lives: not a slow reminder, silence with a number
   beside it.
2. **The entry's own shape-of-fix is unreachable as written, and the
   same measurement is why.** It asks for adoption *"only when the tray
   has been absent for a full `reminder_hours`"*; `TrayPresence` is
   monotonic and in-memory by deliberate design, so a process observes
   24 h of absence only by living 24 h. Shipped as a **refusal** the fix
   would have been correct, green and inert. It ships as an **anchor** —
   `absent_for()` sets the adopted fault's `last_spoken_at` back, capped
   at one interval — which keeps the quiet-by-construction property the
   entry wanted and is reachable here. `absent_for()` falls back to
   process uptime, an under-count that delays an adoption and can never
   hasten one.
3. **The two faces are multiplicative, not independent** —
   `SNAG-AGENT-008`'s shape, and the mechanism the entry describes
   without naming. Adoption alone re-adopts on every restart and re-arms
   its own anchor, so on a 1.77-hour daemon it never speaks; the store
   alone leaves face 1 exactly as filed. A fix for one half is not half
   the benefit, it is none.
4. **The clock became a wall clock, which is a change of *reading***.
   No monotonic value survives a process — and on Linux
   `CLOCK_MONOTONIC` does not survive a **suspend** either, so a
   workstation asleep overnight paid nothing towards an interval that is
   precisely about elapsed human time. `TrayPresence` keeps monotonic
   for its own 180-second question, where a suspended box correctly
   counts nothing because neither process was running.
5. **The store records what was *said*, never what the tray's presence
   implied.** Rule 2's stamp-forward stays in memory, which bounds writes
   at one per notification and is safe because a restored stale stamp
   cannot act — a reminder needs the tray absent, and that same gate
   corrects it on the first sweep after a restart, inside one grace
   window. The stated cost is one early toast if the daemon restarts
   while the tray is up and the tray dies inside that window.
6. **The old cheapest gate could not survive persistence and was
   replaced rather than kept.** *"A sweep that has said nothing issues
   no query at all"* **is** the entry — not knowing what the last
   process said is indistinguishable from it having said nothing. The
   bound moved from per sweep to **one query per process**, and where
   the tray runs the tray gate returns before anything else is read.
   Adoption is bounded in SQL (`GROUP BY title`, `LIMIT`) and across
   sweeps by `MAX_ADOPTED_TITLES`, which is `_MAX_LISTED_TITLES` reused:
   adopting more than a roll-up can name is adopting a fault nobody will
   hear named, Session 46's rule. It orders by `MIN(created_at)`,
   because a family re-raising every poll has a fresh newest row and a
   deduplicating one — the families `SNAG-ESTATE-003` is about — has a
   single old row, so newest-first ranks exactly backwards.

Three things only running it could have said. **A test asserted the
defect as correct behaviour** — `test_a_fault_the_tray_announced_is_never_adopted`,
green since Session 55 — and had to be inverted rather than deleted.
**Six of twenty-eight falsifications passed against deliberately broken
code**, four of them upsert columns no fake can witness, because a fake
replaces the whole row on conflict and therefore agrees with an `ON
CONFLICT` that keeps the old value; the guard is a statement test
asserting every mutable column is set from `excluded`. And
**`rolled_back_drive` leaked** before it was hardened: `_remember`
commits, that harness rolled back a plain session, and this session's own
suite run committed three rows into `alerts` and three into
`desktop_notifications`. It now joins the connection's transaction by
savepoint — a harness that cannot survive the code it drives is a control
the next fix breaks.

**Deploying it found a second, independent reason the reminder path was
inert.** `DesktopNotifier` resolved `get_session_factory()` — the
*application's* pooled engine — while every call it makes runs on a loop
that is not the application's: the sweep is an APScheduler job and
`scheduler._run_async` wraps each firing in its own `asyncio.run`, and
`on_alert_raised` is published from inside an agent's run, which is
another. A pooled asyncpg connection belongs to the loop that opened it,
so the first query out of a restarted daemon raised `RuntimeError: got
Future … attached to a different loop` and asyncpg followed with
`InternalClientError: got result for unknown protocol state 3`.

**`_still_open` has carried that defect since Session 55 and never once
executed on this box**, because the sweep's old first gate returned
before reaching it — so `SNAG-TRAY-007`'s reminder could not have worked
here even for a fault the daemon *had* announced, and this entry's own
symptom was what hid it. `_factory()` returns `get_scheduler_session`
now (`NullPool`, an engine per call, what every agent already does) and
the commit belongs to that context manager rather than being restated
beside it. Found by restarting and reading three `Log error:
sysadmin.service` rows out of the live table, which is
`verify-ops-claims-live` for a claim about a code path nothing had ever
run.

The check retired with the entry and the drive is re-homed as
`tests/test_desktop_store_live.py` (`FROZEN_TABLES`' rule), where it is
**stronger than the check**: once adoption landed, "the restarted
instance restated its predecessor's fault" was producible by adoption
alone, so the live test asks *how* it was inherited — a restored episode
carries a reminder already sent and is not marked adopted. Live
population here is zero by design: the tray runs, so the tray gate
returns before adoption ever queries.
