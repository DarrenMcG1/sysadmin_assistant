# Handoff — 2026-08-11

## Next action

Install the two unit files with `sudo cp systemd/sysadmin.service systemd/sysadmin-failed.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl restart sysadmin.service`, then rehearse the failure path once with `sudo systemctl start sysadmin-failed.service` to confirm a persistent critical toast appears.

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
- **`SNAG-AGENT-003`'s first half is untouched.** The alert would now go
  persistent, but the file organiser has still run once in its life and
  the two candidate causes are still unseparated.
