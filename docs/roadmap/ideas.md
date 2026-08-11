# Ideas & Feature Requests

> **Quick Reference**: See [STATUS.md](STATUS.md) for overall project status
>
> **Related**: [tasks.md](tasks.md) | [snag_list.md](snag_list.md)
>
> **Last Updated**: 2026-08-06

---

## Ideas Inbox

_Capture ideas here as they come up. Promote to tasks.md when ready to implement._

### 🧠 2026-08-11 — the estate as the estate's central nervous system

Raised by the estate owner while ADR-0002 was still being written, and it
enlarges that ADR rather than sitting beside it — the decisions taken are
in the **[ADR-0002 amendment](../adr/0002-estate-manager.md#amendment-2026-08-11-the-estate-is-a-service)**,
and this entry holds the programme and the numbers.

**The shape.** The estate manager becomes a service, not a document
repository: it arbitrates inference across the box, owns project state,
and aggregates the briefing. Apps (venture-assistant, SportsAnalyser,
sysadmin) contribute; Alfred is the frontend that renders. Alfred's own
workload component reads project state and turns items into its own work
items — pulling, which is the boundary its ADR-0064 already drew.

**Three tracks, and they are not equally ready.**

1. **Inference arbitration** — the motivating case, and the one with a
   found ceiling rather than an assumed one. `Conflicts=` + `After=` +
   `ExecStopPost` was built per the 2026-08-06 decision and works; what it
   cannot do is queue. Its measured defect is that **restoration is
   hand-wired in the evictor**, so every new GPU consumer must know about
   every existing one — already duplicated at four consumers. Ladder:
   probe (exists) → game-start signal (needs a runtime) → queue (needs
   persistence).
2. **Projects extraction** — answers ADR-0001's open question. Cheap for
   code (files in repos, tested import boundary, own timer), **not cheap
   for the interface**: 2 tables in the `sysadmin` schema, ~13 modules, a
   dozen endpoints, and Alfred pulling `briefing/preview` whose two
   headline sections *are* project data. Implies the briefing producer
   moves too, which closes the never-built per-app `GET /api/briefing`
   fan-out from 2026-08-06.
3. **Briefing inversion** — falls out of (2) rather than being chosen: the
   estate aggregates, sysadmin becomes one contributor among several.

**Numbers, so the scale is on the record rather than assumed.** Measured
2026-08-11: **5 active projects** on the board, **4 GPU consumers**
(`alfred-inference`, `venture-chat`, `venture-chat-large`,
`venture-assistant-backend`), one 24 GB card. `stalled_count: 0`. An estate
of five active projects is small, and a queue for four consumers is a
different proposition from a queue for forty — worth re-reading before the
service grows features.

**The constraint that governs all three**: sysadmin publishes alerts
directly with its own credential, and the estate owns provisioning only,
never delivery — otherwise the estate dying silences the alarm about the
estate dying, which is the Session 39 defect rebuilt inside its own fix.
**sysadmin does not move**, and watches the estate like any other unit.
The monitor must not own the things it monitors.

**Answered 2026-08-11, with what the measurements did to each answer.**

**Who watches the queue for correctness?** The owner's answer was "the
estate manager". That reinstates the recursion Session 39 rejected — a
watcher sharing fate with what it watches. It does not need a new
decision, because it follows from a rule already taken: **the estate emits
the invariants (queue depth, oldest waiting request, dropped count) and
sysadmin judges them.** The monitor must not own the things it monitors.
Note what this needs from the estate that liveness does not: an endpoint
whose *numbers* can be wrong while the service is perfectly up.

**The policy is "GPU usage above ~30% ⇒ no LLM activity, then by
priority", and the estate owns it.** Measured the same hour, and it does
not survive contact as stated:

| Measured 2026-08-11 | Reading |
|---|---|
| `GPU use (%)` | **29** |
| `GPU Memory Allocated (VRAM%)` | **84** |
| `rocm-smi --showpids` | *"No KFD PIDs currently running"* |
| DRM fdinfo, `llama-server` pid 1083 | no `drm-engine` fields |

1. **The threshold straddles the number depending on the metric.** 29%
   compute says go; 84% VRAM says stop. Which one is meant is the whole
   policy.
2. **VRAM is the wrong metric.** It reads 84% *because the estate's own
   models are resident*, so the rule would block LLM work on the grounds
   that LLM work is loaded.
3. **Per-process attribution does not exist on this box, by either
   route.** The models run through Vulkan rather than ROCm, so they are
   not KFD processes, and fdinfo exposes no `drm-engine` fields. Nothing
   can currently answer *"whose 29% is this?"*.

Point 3 cuts the other way once centralisation is assumed, and this is the
strongest argument for the queue that neither party started with: **if the
estate is the sole launcher, it knows what it started, so "usage not
attributable to me" is computable by subtraction.** Centralisation makes
the unmeasurable measurable — conditional on nothing bypassing it, where
today four units start models on their own. Whether the estate becomes the
sole launcher is therefore a load-bearing decision, not an implementation
detail.

Priority order also already has a recorded policy that the unit files
contradict: 2026-08-06 chose *"queue and wait, Alfred takes precedence"*,
while `Conflicts=` encodes **whoever started last wins**. Two policies,
one of them written down and not implemented.

**Has anyone asked venture-assistant or SportsAnalyser?** The owner's
evidence was `operator_profile` — believed to be data duplicated into
venture-assistant that Alfred already held. **Checked, and it is not
duplication**, which changes what it is evidence *for*. Alfred's own
ideas.md entry, captured the same day at venture's phase 7 sign-off,
concludes the two are adjacent but distinct — Alfred's skills data is
employment-facing (gaps vs role specs, market demand), venture's is
venture-fit-facing plus fields "Alfred will never own" (weekly hours, risk
appetite, growth interests) — and therefore **"a sync must map, not
mirror"**. `operator_profile` is migration 013 and was not built. No
schema was duplicated and no build was wasted.

**The finding is one line further in, and it is better evidence than
duplication would have been.** That entry cites *"estate rule: no cross-DB
queries"* — and **the rule exists nowhere central.** estate-map.md carries
"one database per app" as a convention with grandfathered exceptions,
which governs where data lives, not who may query across it. So a named
rule is invoked inside one app's roadmap with no canonical statement
anywhere, and the next app either rediscovers it or contradicts it without
either being visible.

That is a **documents** problem, fixed by phase 1, needing no runtime —
and it is the clearest justification yet for the estate manager existing
at all. The catch also depended entirely on the owner remembering at
sign-off; nothing on the box would have raised it.
- **`GET /api/projects/next` returning 200 has expired one of ADR-0064's
  three reasons for deferral.** That is a reason for Alfred to re-examine
  on its own side, not a reason to build here. Neither of its two counted
  triggers fires (`stalled_count` 0 of 2, `count` 5 of 12).

### ✅ Promoted 2026-08-05 — the project-manager tier pattern in other domains

Sessions 21–23's three-tier ladder (measure → advice as data → periodic LLM
narrative) generalises, and all four candidates captured here are now
**Sessions 24–27 in [tasks.md](tasks.md)**, where the full detail lives:

| Session | Domain | Note |
|---|---|---|
| 24 | File organiser tiers | Currency is reclaimable bytes; also promotes the forecast maths out of the tray |
| 25 | Service reliability scoring | Scores services from `health_checks`/`alerts` history, which nothing reads today |
| 26 | Service discovery — unmonitored-unit detector | Directly requested; the mechanical backstop for [guides/monitorable-project.md](../guides/monitorable-project.md) |
| 27 | Log aggregator tiers | Coupled to SNAG-AGENT-002 — signature fingerprinting fixes both |

The detector ideas parked below feed **Session 24** as new Tier 1 findings:
once a finding exists, the advice for it follows automatically, which is the
payoff of the advice-mirrors-findings design.

### Silent-degradation detection — a service that is up but not doing its job

Captured 2026-08-06, from a real case: `alfred-inference`, `venture-chat`
and `venture-embed` had every model loaded into system RAM instead of VRAM
since installation. Every signal this repo collects said healthy — the unit
was `active (running)`, `/health` returned 200, the GPU sat idle so both
apps' busy-% guards were satisfied. The fault is now fixed at source
(`~/.local/bin/wait-for-dgpu`), but **nothing here would have caught it**,
and it will not be the last of its kind.

The general shape: a service can be *up*, *responsive* and *wrong*. Health
checks answer "is it listening"; they never answer "is it doing what it was
configured to do". Candidate detectors, cheapest first:

- **GPU residency assertion** — cross-reference `rocm-smi` VRAM occupancy
  against the inference services that are supposed to be resident. Three
  llama-servers up and ~3 GB of VRAM in use is arithmetically impossible;
  that is a finding with no per-app cooperation needed. Complements the
  existing `gpu_vram_warning_percent` threshold, which only fires when VRAM
  is *too full* — the opposite failure
- **Startup-log assertions** — a per-service optional `expect_log:` /
  `forbid_log:` pattern checked once after start. `CPU_Mapped model buffer
  size` in a unit meant to be GPU-resident is a one-line rule. The log
  aggregator already reads these journals for errors; this reads them for
  *absence of an expected line*, which no current agent does
- **VRAM budget vs declared residency** — sum what the units claim they
  hold against card capacity and warn when a scheduled job cannot fit. The
  02:00 collision found on 2026-08-06 (24B needing ~14.8 GB against ~12.4 GB
  free with granite resident) was arithmetic anyone could have done, and
  nobody did, because no one place knew all three numbers

Overlaps Session 25 (service reliability scoring) — reliability history and
"up but wrong" are the same question asked over different windows — and
wants the same unit-parsing sweep as Session 26, so it is probably cheapest
taken alongside one of them rather than as its own session.

### Housekeeping follow-ups from the 2026-08-04 ~/projects reorganisation

The Tier 2 recommendations engine landed 2026-08-04 (Session 22:
`GET /api/projects/{name}/recommendations` + `GET /api/projects/actions`)
and now surfaces **missing remotes natively** — the six unbacked repos
appear as `risk` items in `/api/projects/actions` after every scan, so
that follow-up no longer needs a doc entry. The rest stay parked because
the scanner has no finding for them yet; each is really a *detector idea*:

- **apps/oanIt vs apps/habitTracker** — habitTracker contains
  `oanIt_Frontend`/`oanIt_backend` dirs; both trees have real content.
  Needs a manual look. (Detector idea: name-similarity duplicate flag.)
- **apps/BudgetApp venv clutter** — carries both `.venv` and `.venv1`
  (~290M, recreatable). (Detector idea: multiple/oversized venvs as a
  `hygiene` finding — the file organiser already hunts stale caches.)
- **Config loader could warn on nonexistent managed paths** — would have
  caught SNAG-CONF-001 immediately (also noted in snag_list.md).
- **Database occupancy is invisible to the file organiser** (found
  2026-08-06). The `projects` database is 16 GB, of which the **retired**
  `personal_assistant` schema is 15 GB across 821 tables — PA was retired
  2026-07-24. That is larger than the entire filesystem reclaim estimate,
  and the file organiser cannot see it: from the filesystem it is opaque
  bytes inside PostgreSQL's data directory, attributable to no project.
  A `pg_namespace`/`pg_database` size query joined to the archived-project
  list would surface it as a `reclaimable` finding in the Session 24
  currency. Dropping the schema itself stays a manual, confirmed action —
  irreversible, and the repos are archived on purpose.

### Rebuild the sysadmin web UI inside Alfred's frontend

The web dashboard was built in PersonalAssistant and died with it (2026-07-24);
the PyQt6 tray is currently the only UI. Alfred — PA's replacement — ships a
**Nuxt frontend on :3100**, which is the obvious host for a rebuild.

Nothing on the backend needs to change to make this possible:

- **The API is unchanged.** The same 25+ endpoints the PA dashboard consumed are
  still served on :8500, and their response shapes are now pinned by
  `sysadmin/contracts.py` (the tray's contracts) rather than hand-copied — so a
  web client and the tray can't drift apart the way they used to.
- **`GET /api/sysadmin/events`** (SSE, Session 17) means a browser client can
  subscribe with `EventSource` instead of polling, which the tray still doesn't
  do — the web UI could be the first real consumer.
- **Mutating routes are bearer-auth protected** (Session 12: service actions,
  alert ack, DND, scans, file/branch actions). A browser UI therefore needs the
  `api.auth_token` — and since it can't hold a shared secret safely, the sane
  shape is for Alfred's *backend* to proxy the mutating calls and hold the token
  server-side, leaving the browser to hit read-only GETs directly. Worth
  deciding before any UI work starts, not after.
- **CORS** already lists `http://localhost:3100` / `http://127.0.0.1:3100` in
  `service.cors_origins`, added during the PA→Alfred migration.

Scope worth having on day one: the Overview/resource charts, the alerts list with
ack, and the Projects tab — the parts that benefit most from a big screen. The
Files tab's action endpoints (Session 18) are the higher-risk surface and should
follow, not lead.

---

_Promoted 2026-08-05:_

- Tier pattern in other domains (file organiser, service reliability,
  service discovery, log aggregator) → **Sessions 24–27**

_Promoted 2026-07-24:_

- File organisation & cleanup → **Session 18**
- Dashboard enhancements → **Session 19**
- Project management (branch cleanup, per-project thresholds, TODO cap) → **Session 20**
- Developer experience (shared models, drift guard, smoke test) → folded into **Sessions 13–14**
- Self-monitoring (self endpoint, SSE, anomaly detection) → **Session 17**
- Notifications — less obtrusive → **Session 16**

### Explored & Rejected

- ~~**SSL cert expiry checks**~~ — not needed for localhost-only services
