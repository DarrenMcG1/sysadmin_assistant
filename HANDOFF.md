# Handoff — 2026-08-12

## Next action

Start Session 42 on `SNAG-AGENT-005` and decide its one open question first — whether the log aggregator alerts on a burst and resolves when the source goes quiet, or stops raising per log entry altogether and lets `log_entries` be the record — because `rfkill block bluetooth` did not stop the kernel retry loop (812 messages in two minutes, `rfkill list` now empty), the table is taking on about 43,000 rows a day, and this is the only remaining defect that lets it grow without bound.

## Read this before restarting: the Bluetooth storm is live again

Checked at 15:52 on 2026-08-12, after `bluetooth.service` was disabled on
the assumption that it would quieten things. **It did not, and the reason
is worth keeping.** `bluetooth.service` is `bluetoothd`, a *userspace*
daemon. The retry loop is in the **kernel** — `btusb`/`btmtk`, both loaded
right now — which probes the adapter whether or not anything in userspace
wants it. Measured with the service `inactive`: **816 Bluetooth kernel
messages in two minutes, ~6.8 per second**, twice the July rate, 81,422
this boot. The adapter re-enumerated at 12:32:45 today after five boots
absent.

The kernel now states the diagnosis in its own words, which is as direct
as confirmation gets:

```
bluetooth hci0: Direct firmware load for
  mediatek/mt7927/BT_RAM_CODE_MT6639_2_1_hdr.bin failed with error -2
```

That is character-for-character the file `modinfo btmtk` declares and the
one file absent from `/lib/firmware/mediatek/mt7927/`.

**Why this blocks the restart.** `SNAG-AGENT-004`'s fix does not touch
`log_aggregator` rows — deliberately, they are events rather than states —
so with the storm running, restarting the daemon resumes writing roughly
175,000–580,000 alert rows a day into the table Session 41 just emptied.
`rfkill block bluetooth` is the one-line, reversible stop (`hci0` shows
`Soft blocked: no`, so it is available and untried); installing
`BT_RAM_CODE_MT6639_2_1_hdr.bin` from upstream linux-firmware is the real
fix. Blocking the adapter is treating the symptom: the structural defect
is `SNAG-AGENT-005`, and *any* recurring kernel error reproduces this.

## Session 41 (2026-08-12): both P1 agent snags, both with the filed cause wrong

**Neither snag's recorded cause survived contact with the box**, and in
both cases the correction came from data that had been sitting there for
days. Worth reading as a pair, because the shared lesson is that both
entries had been reasoned about from an endpoint's output rather than
from the thing the endpoint reads.

### SNAG-AGENT-003 — two candidates, and the answer was a third

The entry said the two candidates (a scheduler that never fires, an agent
that dies silently) needed separating before anything was changed. That
was right, and it took one `journalctl` call:

```
17:08:12  scheduled_interval_job  file_organiser_scan  {"hours": 24}
17:11:10  agent_run_completed     file_organiser  duration_s 117.71  findings 25317
17:11:10  scheduler_job_error     InterfaceError: connection is closed
          [SQL: UPDATE sysadmin.agent_runs SET status='completed' ...]
```

**The scheduler fires and the agent succeeds. The transaction is killed
underneath it.** `idle_in_transaction_session_timeout` is `1min` on this
host; `BaseAgent.run` inserted the `running` row, *flushed* it — opening
a transaction — and handed the same session to `_execute`, which then
spent 118 seconds in `asyncio.to_thread` touching no database.

Three things that explains which the entry had recorded as separate
puzzles. `agent_first_run_delay_seconds: 60` was never broken and has
been working since it was added. "Nothing has ever recorded a failure"
was not reassurance but the second symptom — the `except` branch writes
`status='failed'` to a row inside the transaction the failure destroyed.
And **the one surviving run is the proof rather than the exception**:
2026-08-06 took 29.63 s, the only run in the agent's life to finish
inside the timeout.

The rule already existed one layer up, in `files/review.py` — *"commit
the read transaction before calling the LLM"* — learned for inference and
never generalised to the framework beneath it. `run()` is now three
transactions; `tests/test_agent_run_recording.py` asserts the count,
because collapsing them back is the defect.

**Rejected: raising the timeout on scheduler connections.** One line, and
it suppresses the host's deliberate guard on the connection that idles
longest while still leaving a failed run unable to record itself.

### SNAG-AGENT-004 — right diagnosis, twenty times the population

The filed cause and fix pattern were both correct. What was understated
was how much of the table this covers. Counted live under
`agent='sysadmin'`, unresolved: **27,827** for five retired services
(five, not four — `nuxt-frontend` was missed, and `redis` is 6,283 not
4,950), and beside it **24,097** resource-threshold rows that have had
**no resolve path at any point in this application's life**.
`Critical disk usage on /` alone is 13,971 open rows, last raised
2026-07-26, against a disk at 68 % since. One statement closes both,
because a condition that recovered and could not be observed recovering
is the same defect as a service that was retired.

**The obvious implementation was written first and refuted before it
shipped.** Excluding only "titles this run raised" is the direct reading
of the project-side pattern and is wrong here: `_degraded_counts` is in
memory and resets on daemon restart, so the first run after one raises
nothing for a service degraded for hours, and the alert would be resolved
as *recovered* then re-raised two checks later — announcing a recovery to
the tray for a fault that never went away. Services are now resolved only
when a run measures them healthy; resource thresholds keep the
raised/not-raised test, because a mount either breached or did not.

Removing the old per-service `resolve_alerts(session, service_name)` took
a second, unfiled bug with it: it was a substring `ilike`, so
`venture-chat` recovering also closed `venture-chat-large`'s alerts.

**Verified against the live table before shipping**: the population is
51,924 rows, and the only `agent='sysadmin'` row the statement leaves
open is the file organiser's own stall, which is still true.

### Deliberately not swept up

`log_aggregator` holds **547,891** unresolved rows, 547,814 of them
`Log error: kernel` — 91 % of every unresolved alert in the table.
Widening the resolve to reach them would be the wrong mechanism: these
are **events, not states**, so there is no run at which "this would not
be raised" becomes true, and the alerts would live five minutes each. The
real defect is that the aggregator raises one alert row per log entry,
which is the mistake the reliability endpoint's docstring already
describes for `service_health`. Filed as `SNAG-AGENT-005` with two
options and neither chosen.

### Proven on the box, same day

The estate owner restarted the service and both fixes did exactly what
they were built to do.

| | before | after |
|---|---|---|
| `file_organiser` runs recorded, ever | **1** | 3 completed + 1 in flight, today alone |
| `filesystem_audits` rows | 1, dated 2026-08-06 | 4 — 08:59, 10:45, 12:36 added |
| unresolved `agent='sysadmin'` alerts | 51,925 | **43** |
| rows resolved by the first runs | — | **51,976** |

The `running` row is the new behaviour, not a fault: a run in flight is
now visible where it used to be indistinguishable from a run that never
happened.

**What did not work is the Bluetooth block.** `rfkill list` now returns
*nothing at all* and the kernel is still emitting **812 messages in two
minutes**, unchanged. `log_aggregator` added **43,209 unresolved rows
today** — so the table went 547,891 → 591,091 while the sysadmin agent's
own share fell to 43. Today removed 51,976 rows and the log aggregator
replaced 43,209 of them in the same day, which is `SNAG-AGENT-005`'s
whole argument stated in one line, and is why it is next.

## Same day: reading the unresolved table found a live fault

The 590,000 unresolved rows were **counted** in the morning and **read**
in the afternoon, and only the reading found anything. Two results.

**`SNAG-ESTATE-001`, fixed within the hour it was found.** Two retired
PersonalAssistant user units had restart-looped **52,178 times** since
2026-08-04 21:13 — the `~/projects` reorganisation, which moved the repo
to `archive/` and left five enabled units pointing at the old path. They
were still climbing at ~1.3 restarts/minute during the investigation, and
on **2026-08-08 04:10–04:14** they deadlocked against each other and
stalled the kernel: `(idle-watcher.) is blocked on a mutex likely owned
by (run-worker.sh)`, both >245 s, two wedged kworkers, RCU expedited
stalls. Disabled on the owner's instruction; nothing is in `activating`
on this box any more.

**What makes it worth the write-up is that the detector was never
wrong.** `GET /api/units/status`'s sweep had both classified
`category: "orphaned"`, with the `dead_path`, the archive location, and
the cause in plain English — *"WorkingDirectory … does not exist —
systemd fails the start job, so this unit cannot run"* — and an open
alert since 2026-08-11. Eight days of a complete, correct,
machine-readable diagnosis nobody fetched. It is also the exact
`activating (auto-restart)` state Session 39 proved is invisible, on two
units Session 39 did not fix, because nothing requires that pairing
anywhere but `sysadmin.service`.

**And the Bluetooth diagnosis was half wrong, in the direction that
matters.** The 546,579 rows (91 % of the table) are genuine distinct
kernel events, not a poller re-reading itself — checked, because that was
the attractive assumption. The owner's reading was "the motherboard is
unsupported by Linux drivers". `modinfo btmtk` on 7.1.6 declares
`firmware: mediatek/mt7927/BT_RAM_CODE_MT6639_2_1_hdr.bin`: **the driver
knows the chip and names the file**, and `linux-firmware-mediatek
20260622-1` ships that directory with the Wi-Fi blobs and not the
Bluetooth one, while every sibling chip has one. A **packaging gap, not a
driver gap** — a newer kernel fixes nothing, the missing file does. The
Wi-Fi half is the mirror image and genuinely unsupported: firmware
present, no driver bound at `09:00.0`. Dormant since 2026-07-30 and five
boots, but `bluetooth.service` is still enabled, so a reappearing adapter
resumes at ~175,000 rows/day.

## Late 2026-08-11: the MQTT half unblocked from the estate side

estate-manager's Session 2 ran (its founding MQTT extraction). Both walls
below are down: Alfred's `reconcile()` narrowed (its ADR-0068),
`estate/#` admitted, `sysadmin-publisher` provisioned estate-side and
verified to survive an alfred-backend restart. This repository gained
[ADR-0003](docs/adr/0003-mqtt-credential-by-loadcredential.md)
(`LoadCredential=mqtt:/etc/credstore/sysadmin-mqtt` on the unit, pinned
by a new `test_systemd_units.py` invariant), and `services.yaml` now
watches `estate-broker-provision.service` and — previously unmonitored —
`mosquitto.service` itself. **Publishing alerts is now purely this
repository's own work**: client dependency, config keys, severity gate,
topic scheme under `estate/…` (tasks.md row updated). Note the unit
install command below is superseded by the estate script above, which
copies both unit files and restarts the service after creating the
credential file the new unit requires — `sudo cp` alone would now fail
the unit on the missing `/etc/credstore/sysadmin-mqtt`.

## Session 40 ran on 2026-08-11, as estate-manager's Session 1

The document-only phase 1 scoped as Session 40 was executed in
`~/projects/estate-manager`. What changed in *this* repository: the four
cross-repo guides in `docs/guides/` and ADR-0002 were replaced with
pointer stubs (the documents now live in estate-manager, ADR-0002
renumbered to its ADR-0001; `api_auth.md` stays, being local), and
CLAUDE.md and tasks.md were updated to match. `~/.claude/CLAUDE.md`'s
two hardcoded paths now point at estate-manager — flipped in the same
sitting, after the destination files existed. The port registry
consumers are unaffected: it lives inside `monitorable-project.md`,
which travelled whole. Session 39's MQTT half stays blocked on the same
Alfred-side change as before (narrowing `reconcile()`), which is now
estate-manager's Session 2, first item.

## Session 39 (part 1): the alarm rings more than once

Two of the six scoped items shipped. **Detection was not touched** — not a
line of `self_monitor.py` changed, because it was never the fault. The
scope said so and the code confirmed it: the `file_organiser` stall was
detected correctly at interval × 3 and alerted at 09:07 on 2026-08-10.

What was broken is that the alarm rang **once, at the quietest severity,
and went silent while the fault persisted**. `_check_agent_liveness` skips
raising while an unresolved row with that title is open — correct, and
what stopped the 1,664-row pile-up — and the tray fingerprints on
`{severity}:{title}`. A warning that fires once is indistinguishable from
one that got fixed.

## The reuse instruction could not be followed as written

The scope said to reuse `sysadmin/projects/nudges.py` rather than copy it.
`sysadmin/monitor` may not import `sysadmin.projects`
(`tests/test_import_boundary.py`), so the shared half moved into
**`sysadmin/core/escalation.py`** first — `SEVERITY_ORDER`, `Ladder`,
`step_for`. Same move `strip_markdown` made into `core/text.py`, same
reason, and `nudges.py` now delegates rather than owning it. The
alternative was a copy, and a copied rule drifts in the direction nobody
notices: the escalation stops escalating on one side and nothing reports
the disagreement.

## Why the loud rung is `critical`, which is not the obvious reason

Not volume. `sysadmin_tray/notifications.py` sets `transient=effective ==
"info"` on a first notification and `transient=False` only inside
`_maybe_escalate`, which fires for `critical` alone — so **`critical` is
the only severity the tray renders as a notification that stays on
screen**. The owner's diagnosis was "I never saw the toast", away from the
machine; a `warning` toast expires whether or not anyone was in the room.
The second rung buys *persistence*, and persistence is the thing that was
missing.

This is the exact opposite of the rule `nudges.py` encodes — a nudge never
reaches `critical`, because criticals pierce DND and waking someone at
02:00 about a roadmap item is how a monitor gets muted wholesale. Both
docstrings now cite the other, so the difference reads as a decision
rather than an inconsistency. (`notifications.dnd.enabled` is `false` on
this host in any case, checked rather than assumed.)

## The clock starts when the alarm rang, not when the stall began

Both were computable — the stall began at `last_run_at + stall_window` —
and the obvious choice is wrong twice.

1. The thing that failed was the **telling**, so the telling is what the
   second rung should measure: "you were told yesterday and it is still
   true". A fault detected for the first time has had no chance to be
   seen, whatever its age, so it opens quiet.
2. Anchoring to the stall's own age makes **a daemon outage produce a wall
   of criticals on restart**. Nothing runs while the service is down, so
   every agent is stalled by hours and the first check back would escalate
   all five at once — charging the estate for this application's downtime.
   `GET /api/services/reliability` already encodes that rule as "a gap in
   the series never costs points".

The clock does keep running while the daemon is down, which is right: a
warning row two days old has genuinely stood unseen for two days.

**`escalate_after_hours: 24` is set against the slowest agent, not the
fastest.** `file_organiser` and `service_discovery` run daily, so a stall
of theirs that is merely late clears within one interval; a shorter gap
escalates faults that were about to fix themselves, and an alarm that
cries wolf stops being read. The config docstring states that this knob
cannot make *detection* faster, because `stall_grace_multiplier` is the
wrong knob someone will reach for.

## The crash case, and the measurement that de-risked the change

`sysadmin.service` was `Restart=always` with no limit, so a crash-loop
sits in `activating (auto-restart)` for ever and **never enters
`failed`** — the state every failure hook and every `systemctl is-failed`
watches. The silence-reads-as-health shape, sitting in the unit file.

The trade was real and was sized rather than assumed: infinite retry rides
out a dependency that is slow to appear, and this app *does* exit rather
than degrade without a database (`verify_connection` raises inside the
lifespan). Measured before the edit — **`NRestarts=0`, and zero
"Scheduled restart job" entries in 30 days of journal.** The retry has
never once fired on this box, so the resilience being traded away is
theoretical while the silence it causes is not. The window is 600s rather
than 300s to leave that headroom anyway.

`sysadmin-failed.service` runs `scripts/notify-unit-failed.sh`:
`--urgency=critical --expire-time=0`, and **journald first,
unconditionally**, that being the one destination which does not require
anyone to be logged in. It exits non-zero when it cannot reach the session
bus, because returning 0 there would record "the failure was reported"
when it was not. The handler was **rehearsed, not trusted** — run by hand,
journal line confirmed.

`tests/test_systemd_units.py` pins the two halves together: `Restart=always`
with a burst limit, a window that outlasts `burst × RestartSec`, an
`OnFailure=` naming a unit that exists, and a handler with no `OnFailure=`
of its own. Either half alone accomplishes nothing, which is the shape of
half-change this repo has shipped before (a retention row with no
`TABLE_TIMESTAMP_MAP` entry).

## Blocked: MQTT, on something the scoping session did not find

The premise checked while scoping was alfred-glance's closed renderer
registry. Real, but secondary. Mosquitto here is `allow_anonymous false`
running the **dynamic-security plugin**, and Alfred owns that plugin's
schema "the way Alembic owns a database schema"
(`Alfred/backend/alfred/events/dynsec.py`).

**`dynsec.reconcile()` deletes every client that is not Alfred's admin,
not Alfred's publisher, and not a live device token.** A
`sysadmin-publisher` added with `mosquitto_ctrl` works until Alfred next
restarts and is then deleted — best-effort, logged at `info`, no alert.
For an *alerting* path that is the worst available failure mode, and it is
this session's own bug reinstalled inside the fix.

**Decided**: Alfred provisions a protected non-device publisher, in its
code. Rejected: reusing `alfred-backend`'s credential (shared identity, no
separate revocation, and rotating Alfred's password silently kills the
alarm), and routing alerts through an Alfred HTTP ingest route (keeps the
bus private, but couples the alarm to Alfred's backend being up).

**The namespace decision costs more than scoped, too.** Both dynsec roles
are scoped to `_TOPIC_FILTER = alfred/events/#`, so the chosen neutral
root (`estate/…`) is **denied by the broker** until those roles gain a
filter — not "seven constants and both ends", but that plus the broker's
access control. The terms of the promotion are now written into
[estate-map.md](docs/guides/estate-map.md), which had reserved this
decision in writing for exactly this case.

## Raised after the commit: the estate manager (ADR-0002, Session 40)

The owner asked whether a cross-repo manager is worth making, with MQTT as
the first candidate. It is, and the reason is that **today's blocker is
architectural rather than incidental**: `reconcile()` is correct for a
private bus, and what is wrong is that an application owns shared
infrastructure. Patching Alfred's protected set fixes the instance and
leaves the category — the next app to want the bus finds out by its alarm
going quiet.

Two measurements carried the argument. **4 of 5 files in `docs/guides/`
are not about this repository.** And the *whole* shared broker is
app-owned: not only the dynsec schema but mosquitto's boot drop-in, from
`Alfred/scripts/systemd/mosquitto.service.d` per Alfred's ADR-0046 — a
sentence estate-map.md already carried without drawing the conclusion.

Decided: extracted from here rather than started empty; **the estate owns
the schema while each app still ensures its own identity** (Alembic owns
the schema, apps write their own rows — if both moved, Alfred's bus dies
whenever the provisioner has not run); a boot oneshot, never a daemon,
whose `ExecStart` is the same CLI a human runs; `LoadCredential=` for the
machine password, because `config.yaml` is tracked and this repo forbids
environment variables; and documents move before authority does.

**The cheap fix stands on its own and should probably go first**: narrowing
Alfred's `reconcile()` to delete only subscriber-role clients with no live
token unblocks the MQTT half without any of the above.

**Amended within the hour: the estate is a service.** The owner enlarged
the idea to central inference arbitration, project ownership and briefing
aggregation — a central nervous system, with Alfred as the frontend. A
queue cannot be declarative, so "nothing runs continuously" is reversed;
the reversal is recorded in ADR-0002 rather than edited in, because the
overturned reasoning is still right about what it warned of.

Two things make it a considered move rather than a shortcut. The
2026-08-06 instruction was *"try systemd before building any daemon"* and
it **was** tried and shipped — `Conflicts=`/`After=`/`ExecStopPost` across
`venture-chat-large` and `venture-enrich-nightly` — so what is being
proposed replaces something with a **found ceiling**: preemption works,
queueing is impossible, and restoration is hand-wired in each evictor so
every new GPU consumer must learn about every existing one.

**The constraint the reversal creates, and the answer to it**: if the
estate owns the alerting path, the estate dying silences the alarm about
the estate dying — Session 39's defect rebuilt inside its own fix. So
sysadmin keeps its own credential and publishes directly; the estate owns
provisioning, never delivery. **sysadmin does not move** and watches the
estate like any other unit. The monitor must not own the things it
monitors.

**Corrected from an hour earlier**: Session 40's first task said the new
repo needs no port and no `/api/health`. It will listen, so both are
claimed on day one.

**The GPU policy is already built, twice, and the copies have drifted —
which is the estate manager's case made concretely.** The metric is
`gpu_busy_percent` from sysfs **by PCI slot**, threshold **25**. Line 18 of
`Alfred/backend/alfred/inference/guard.py` and of
`venture-assistant/app/llm/guard.py` carry the same glob string and the
same log message: it was copied. Alfred takes the **minimum of four
samples over two seconds** and has `pause_until_idle` with a 600 s cap;
venture-assistant takes **one sample**. Alfred's docstring states the
defect the copy still has — *"a read taken immediately after our own call
still shows our work"*. One policy, two implementations, the weaker
carrying a failure mode the stronger documents.

That min-of-samples trick also **settles attribution by not needing it**:
it decides "is somebody else holding the GPU" without asking who. Just as
well — attribution is unavailable on this box (`rocm-smi --showpids` sees
no KFD processes, since the models run through Vulkan; DRM fdinfo exposes
no `drm-engine` fields).

Two things to carry rather than rediscover. **Resolve the device by PCI
slot, never `cardN`**: verified 2026-08-11, `card0` is slot
`0000:47:00.0` — the **idle iGPU** at 0% — while the dGPU is `card1`, slot
`0000:03:00.0`, reading 58% then 100% within a minute. Alfred's ADR-0052 F2
records that an index-based guard "would silently poll the wrong GPU and
never fire", and this session measured with `rocm-smi` indices and fell
into precisely that trap before checking. **And fail open**: an unreadable
counter dispatches with a warning, in both copies, deliberately.

The gaming case is real, not hypothetical: on 2026-07-23 an eval against a
live game took it **from 220 fps to 20**, and the harness *"had even
sampled `gpu_busy_percent` first — and written 80% into its own report
before running anyway"*. Observed and recorded instead of acted on, which
is the same sentence as Session 39's stall alert.

**sysadmin watches the queue** — "exactly what it's built for". The split:
the estate emits the invariants (queue depth, oldest waiting request,
dropped count) and sysadmin judges them, because the monitor must not own
the things it monitors. Note what that asks of the estate that liveness
does not — an endpoint whose *numbers* can be wrong while the service is up.

**`operator_profile` was checked and is not duplication**, which changes
what it is evidence for. Alfred's own ideas.md, captured the same day,
concludes the two are adjacent — employment-facing versus venture-fit
-facing, with fields "Alfred will never own" — and that "a sync must map,
not mirror"; migration 013 was never built, so no effort was wasted. **The
real finding is one line further in**: that entry cites *"estate rule: no
cross-DB queries"*, and the rule exists **nowhere central**. A named rule
invoked inside one app's roadmap is one the next app rediscovers or
contradicts invisibly. That is a documents problem, fixed by phase 1.

Evidence for the estate manager, ranked honestly: the **copied-and-drifted
GPU guard** first, the **rule cited with no canonical statement** second,
and `operator_profile` third — a near-miss resolved correctly rather than a
duplication.

## The estate manager is three things, and the queue already exists

The owner agreed the estate becomes the **sole launcher** of inference, and
asked what else is worth centralising. Surveyed, with line counts:

| Duplicated | Where | State |
|---|---|---|
| llama-server client | Alfred 163, venture 155, sysadmin 121 | **3 implementations, 439 lines**, one server |
| GPU guard | `inference/guard.py`, `llm/guard.py` | copied, **drifted** (min-of-4 vs single sample) |
| Queue / defer loop | venture `drain.py` 213 + 3×103 | exists in **one** repo |
| `TRUNCATION_MARKER` | Alfred `:50`, sysadmin `:47` | same name, **different value** |
| Health endpoints | all three | *not* duplication — the contract requires each |

**The queue is an extraction, not a design.** `drain.py` already carries
`gpu_is_busy()`, `wait_for_chat_server()` polling to 300 s, and
`DEFER_SLEEP_SECONDS`/`DEFER_LIMIT`, running nightly. Generalising it from
three workloads to N consumers inherits behaviour that has already survived
a live game.

**And "launching and guarding" wants two different shapes.** Alfred's guard
docstring makes the argument itself — *"not a window, not a daemon"* — and
it fails open, so routing it through the estate would mean a down estate
equals silently unguarded inference: the 220 fps → 20 incident restored.
Decided: **library for the guard and the LLM client, service for the
launcher and the queue.** Documents, library, service — the opening
question of ADR-0002 answered as all three, each assigned by a property of
the thing being centralised rather than by preference.

`TRUNCATION_MARKER` is the sharper of the two drifts: it was copied
*deliberately*, because this repo's CLAUDE.md says to match Alfred's marker
"so a cut made here and a cut made there read identically". They no longer
do. A convention maintained by copying has a half-life.

**Measured rather than assumed** (2026-08-11): 5 active projects, 4 GPU
consumers on one 24 GB card, `stalled_count: 0`. Alfred's ADR-0064
pre-authorises the workload-component read the owner meant, so it is no
override — but **neither of its counted triggers fires** (0 of 2, 5 of 12).
One of its three deferral reasons *has* expired: `GET /api/projects/next`
returns 200 now and its ranking is decided. That is Alfred's cue to
re-examine, not ours to build against. Terminology corrected on the way
through: `wait-for-dgpu` is a **driver-readiness probe**, not a gaming
check, and nothing on this box detects a game starting.

## A unit failure now leaves state, filed under a known agent

The owner chose `agent='sysadmin'` over a migration adding a sixth value to
`chk_alert_agent`. It reads oddly — the sysadmin agent did not raise this
row; it was dead, which is the news — so **`details.source` carries the
provenance `agent` cannot**: `systemd_onfailure`, plus `raised_by` naming
the script. Read that way `agent` is the ownership field the constraint
makes it, and nothing untrue is claimed. The migration was rejected because
a sixth value naming a *script* rather than an agent would also make
`self_monitor.AGENT_NAMES` wrong, and that list is pinned to the constraint
by `tests/test_units_api.py`.

**The write only makes sense because the daemon now clears it.** The
handler runs while the application is dead, so no agent can ever observe
the recovery — the service *starting* is the recovery, and the lifespan is
the only place that fact exists. Without that half this would be an alert
type that can only accumulate, which is how 1,664 orphaned rows happened.
Dedup on an open row is safe only because of the pairing.

`sysadmin/core/unit_failure.py` uses the **sync** engine that exists for
Alembic, because at handler time there is no event loop, no scheduler
session and nothing subscribed to the event bus. Recording never raises: a
dead database returns `False` and logs, since the handler's exit status is
reserved for whether it could tell a *human*.

**Verified end to end against the live database**, not just in tests: the
handler wrote `critical | sysadmin | sysadmin.service failed | source=
systemd_onfailure`, and `resolve_unit_failures` then closed it
(`resolved_at` set), which also cleared the false critical the rehearsal
had inserted.

## Why the estate manager exists, stated properly

The owner asked for the observation to go into ADR-0002. Writing it up
sharpened it: "this estate measures well and acts poorly" is too weak.
**The pattern is that the component doing the measuring is the component
whose interest is served by ignoring the measurement.** Six instances, all
surfaced in one day — the eval harness that sampled `gpu_busy_percent`,
*wrote 80% into its own report*, and ran anyway; Session 39's stall alert
choosing its own volume; `SNAG-DB-001`; `SNAG-CFG-001`; Alfred's staleness
check that cannot fire; retention needing both halves.

The harness is the purest case: the party asking "may I use the GPU?" was
the party that wanted the GPU. No improvement to the measurement fixes
that. What fixes it is the requester ceasing to be the decider — which is
what centralising the launcher and queue buys beyond removing 439
duplicated lines: **an arbiter with no stake in the answer**. Recorded with
its two honest limits, since a central arbiter can also ignore its own
numbers, and that is why sysadmin judging the queue's invariants is part of
the design rather than decoration.

## Left open on purpose

- **`Type=notify` + `WatchdogSec=`** was deliberately not attempted in the
  same sitting as the `StartLimit` change. It is the one item that can
  kill the service outright (a missing `READY=1` makes systemd treat
  startup as failed), and two unit changes with one rollback path is how
  a rollback becomes a guess.
- ~~**An `OnFailure=` firing leaves no alert row.**~~ **Closed** the same
  day — `agent='sysadmin'` with `details.source`, resolved by the daemon's
  lifespan. See above.
- **Off-box is still nothing.** Listeners are `127.0.0.1` and
  `192.168.1.2` only — nothing built today survives the box being off.
  Recorded as the known gap rather than pretended closed.
- **`SNAG-DB-002`, found sideways**: every database on this box has a
  stale collation version (glibc 2.44 against `datcollversion` 2.43; 25
  indexes in the `sysadmin` schema). Not fixed — a reindex touches two
  other apps' data — and the `REFRESH COLLATION VERSION` that clears the
  warning without rebuilding is the trap, since it turns a loud known
  risk into a silent one. A check for it belongs in the sysadmin agent.
- **`SNAG-SYSD-003`**: `After=ollama.service` on a runtime retired
  2026-07-24, spotted in the file being edited and left there so the unit
  change kept exactly one rollback path.
- ~~**`SNAG-AGENT-003`'s first half is untouched.**~~ **Closed 2026-08-12**
  — and neither candidate cause was right. See Session 41 above.
