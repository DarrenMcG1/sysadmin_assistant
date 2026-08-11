# ADR-0002: Shared infrastructure gets an owner that is not an application

- **Status**: accepted, unbuilt
- **Date**: 2026-08-11, **amended the same day** — see
  [Amendment](#amendment-2026-08-11-the-estate-is-a-service) at the end.
  The amendment reverses "nothing new runs continuously"; the reversal is
  recorded rather than edited in, because the reasoning that was overturned
  is the part worth keeping.
- **Answers**: [ADR-0001](0001-project-registry.md)'s open question, "who
  owns project state", for the infrastructure half of it
- **Session**: raised during 39, scoped as 40

## Context

Session 39 set out to make a detected fault keep speaking. It fixed the
desktop and systemd halves and hit a wall on the third: pushing critical
alerts to the phone that already renders them. The wall was not the one
the scoping session predicted.

**The broker is shared and an application owns it.** Mosquitto carries
Alfred's event bus and, since 2026-08-11, is declared an estate bus. Two
pieces of it are sourced from Alfred's repository:

| Piece | Owner today | Where |
|---|---|---|
| dynsec identities, roles, ACLs | Alfred's backend, on startup | `Alfred/backend/alfred/events/dynsec.py` |
| boot-reliability drop-in | Alfred's repo, applied by hand | `Alfred/scripts/systemd/mosquitto.service.d`, its ADR-0046 |

**And the ownership has a sharp edge, found by reading rather than by an
outage.** `dynsec.reconcile()` deletes every client that is not Alfred's
admin, not Alfred's publisher, and not a live device token. That is
*correct* for a private bus — it is how a revoked device loses access even
if the revocation happened while the broker was down. On a shared bus it
means **a credential provisioned for any other app is deleted the next
time Alfred starts**: best-effort, logged at `info`, no alert.

For an alerting path that is the worst available failure mode, and it is
Session 39's own defect reinstalled inside Session 39's fix — a signal
that stops and nothing says so.

Two further observations made the scope of the problem clearer than "one
credential needs provisioning".

**Both dynsec roles are scoped to `_TOPIC_FILTER = alfred/events/#`.** The
namespace is not a naming preference; it is enforced by the broker. A
neutral root is *denied* until the roles change, so the decision to
promote the bus (estate-map.md, 2026-08-11) cannot be carried out
entirely inside the two apps that use it.

**Four of the five files in this repository's `docs/guides/` are not about
this repository.** `estate-map.md` and `monitorable-project.md` describe
the box; `alfred-briefing-integration.md` and `alfred-projects-page.md`
are contracts between two *other* codebases. Only `api_auth.md` is local.
ADR-0001's open question — is project organising a domain of Alfred, a
standalone service, or a permanent part of this one — is itself a
cross-repo question stored inside one of the candidates.

So the material for a cross-repo owner has been accumulating for months
in the repository that happened to be writing it down.

## Decisions

### An estate manager exists, extracted from here

Cross-repo concerns get a repository of their own, and it takes them
**from `sysadmin_assistant`** rather than starting empty beside it. The
alternative — a new repo holding only new concerns — leaves cross-repo
documentation in two places, which is the drift this repository has filed
three snags about.

This answers ADR-0001's open question for infrastructure and conventions.
It does **not** answer it for project state: `sysadmin/projects/` keeps
its tested import boundary and its own timer, so that decision stays as
cheap as ADR-0001 arranged for it to be.

### It owns the schema; each app still ensures its own identity

The distinction matters more than the ownership does. Alfred's
`bootstrap()` currently does two things in one function: it defines the
shared schema (roles, topic filters, who may publish where) and it
provisions Alfred's own credential.

**The estate manager owns the first. Each app keeps doing the second,
idempotently, at its own startup.** If both moved, Alfred's bus would be
dead whenever the estate provisioner had not run — a new boot-ordering
failure mode, in the alerting path, introduced by the change meant to
make the alerting path reliable.

The analogy is deliberate and is the one Alfred's own docstring reaches
for: **Alembic owns the schema, applications write their own rows.**

`reconcile()` then narrows to what Alfred actually created — subscriber-role
clients with no live token — rather than deleting everything it does not
recognise. That single predicate is what makes the bus safely shareable,
and it is worth doing *even if the rest of this ADR is never built*.

### Nothing new runs continuously

Provisioning is a `Type=oneshot` unit ordered `After=mosquitto.service`
and `Before=alfred-backend.service`, whose `ExecStart` is the same CLI a
human runs by hand. Two reasons for the shape and one for the duplication:

- **A daemon would be a new service to monitor**, which is the objection
  that killed the email option in Session 39 — the problem recursing.
  The estate's own recorded bias, from the 2026-08-06 orchestrator
  decisions, is *"systemd, not a lease service — try this before building
  any daemon"*.
- **A CLI alone depends on someone remembering.** That is the shape of
  `SNAG-DB-001`, where nothing applied migrations and the box served a
  version-behind schema for 39 hours. A oneshot reasserts the definitions
  at every boot without anyone deciding to.
- **The unit calls the CLI** rather than reimplementing it, so the boot
  path and the manual path are provably the same code. A oneshot with a
  timer is also exactly the shape `GET /api/units/actions` already knows
  how to watch, so the provisioner is monitorable by the thing it is
  provisioning for.

### The machine credential arrives via `LoadCredential=`

This repository has never held a secret and its conventions assume it
never will: `config.yaml` is tracked in git, `api.auth_token` is `""`, and
CLAUDE.md states flatly that **no environment variables are read**.
Alfred's answer — `EnvironmentFile=-%h/.config/alfred/mqtt.env` — is ruled
out here by that rule.

`LoadCredential=mqtt:/path` delivers the secret into
`$CREDENTIALS_DIRECTORY`, so it is never in git, never in the process
environment, and never in `config.yaml`. `sysadmin.service` is a system
unit, so systemd reads the source as root before dropping to `gaddi` and
no permission juggling is needed.

Rejected: a path *named* in `config.yaml` (workable, and makes file
permissions the whole of the protection), and relaxing the no-env-vars
rule (a convention worth removing deliberately if at all, not as a side
effect of one password).

### Documents move before authority does

The first change moves the four cross-repo guides and this ADR set,
updates the two hardcoded paths in `~/.claude/CLAUDE.md`, and **touches no
runtime**. The broker definitions follow in a second change.

Reversible, and it gives the repository a reason to exist before it is
given the power to delete credentials. The cost is that Session 39's MQTT
half stays blocked for one more session, which is acceptable because it is
already blocked on an Alfred-side change.

## Consequences

- **`~/.claude/CLAUDE.md` breaks on the first change and must be updated
  in the same commit.** It hardcodes `~/projects/sysadmin_assistant/docs/
  guides/monitorable-project.md` and `.../estate-map.md`, and every
  new-project session reads them. A stale pointer here silently stops the
  monitorable-project contract from being read.
- **The new repository is a project on this box** and will be scanned by
  the organiser. An undeclared project defaults to `active`, so it needs a
  `.project.yaml` on day one or it starts accruing staleness deductions
  and idle nudges about work nobody has committed to yet. It needs no port
  and no `/api/health`: nothing in it listens.
- **sysadmin gains an MQTT dependency it does not have.** `paho-mqtt` is
  not installed here; Alfred uses `aiomqtt`. Matching Alfred is probably
  right, and it is a real dependency decision rather than an import.
- **Alfred is changed by this, in a separate repository with its own ADR
  process.** Narrowing `reconcile()` and standing down role bootstrap are
  both Alfred-side, and Alfred's ADR-0033 §5 currently *assigns* it schema
  ownership. That ADR needs superseding on its side; this one cannot do it.
- **The estate manager owns the broker's drop-in too, eventually.** It is
  currently sourced from `Alfred/scripts/systemd/` with its reasoning in
  Alfred's ADR-0046. Not part of the first two changes, and named here so
  the second one does not read as complete.
- **Off-box alerting is still absent.** Listeners are `127.0.0.1` and
  `192.168.1.2`; nothing here survives the box being off. Recorded again
  because a bus promotion reads like it might have fixed it.

---

## Amendment 2026-08-11: the estate is a service

Raised by the estate owner within the hour, and it reverses the "nothing
new runs continuously" decision above. The reversal is recorded rather
than edited into place: the overturned reasoning is still correct about
what it was warning of, and a future session needs to see what was traded
for what.

### What changed the answer

The owner's proposal is broader than a document owner: **inference queued
centrally across the estate**, so GPU contention is arbitrated once rather
than per app, with the estate as the aggregation point that
venture-assistant and SportsAnalyser feed and Alfred renders.

An inference queue cannot be declarative. It arbitrates at request time,
so it is a runtime by definition, and "a boot oneshot, never a daemon" is
not available for it.

**The prerequisite for proposing this had already been satisfied**, which
is why it is not a shortcut. The 2026-08-06 decision was *"GPU arbitration
is systemd, not a lease service — try this before building any daemon"*,
and it **was** tried and shipped: `Conflicts=venture-chat.service` with
`After=` in `venture-chat-large`, `ExecStopPost` restoring the evicted
model, and `wait-for-dgpu` as `ExecStartPre` on four units.

It works, and it has a structural defect its own comments state:
*"Conflicts= does not put it back"*, *"nothing restarts it"*. Restoration
is hand-wired **in the evictor**, so every new GPU consumer must know
about every existing one — already duplicated across `venture-chat-large`
and `venture-enrich-nightly`, at four consumers. `Conflicts=` provides
preemption; it cannot provide a queue, fairness, or precedence beyond
whoever-started-last, and no amount of unit files will add them.

So the systemd approach was not rejected in favour of a daemon. It was
built, and its ceiling was found.

### The constraint the reversal creates, and how it is answered

**If the estate is a service and it owns the alerting path, then the
estate dying silences the alarm about the estate dying.** That is exactly
the shape Session 39 existed to remove, and it must not be reintroduced by
the fix for Session 39's blocker.

Therefore:

> **sysadmin holds its own broker credential and publishes alerts
> directly. The estate owns provisioning and schema — never delivery.**

Estate death then costs the GPU queue and the projects API, and does not
cost the alarm. This is the whole reason the credential arrives by
`LoadCredential=` on `sysadmin.service` rather than being requested from
an estate API at runtime: an alerting path with a live dependency on
another service is not an alerting path.

**And sysadmin does not move.** It stays the monitor, and it watches the
estate through `GET /api/units/status` and
`GET /api/services/reliability` like any other unit. The recursion
objection that killed the email option applies to a watcher that watches
itself; it does not apply to a monitored service. Stated positively:
**the monitor must not own the things it monitors**, which is the sharpest
available argument for the owner's instinct to leave sysadmin doing
sysadmin.

### Gaming arbitration is a ladder, and only the top rung needs the daemon

Terminology first, because it changes the mechanism: **`wait-for-dgpu` is
a driver-readiness probe, not a gaming check.** It exists because amdgpu
loses a boot race and llama.cpp silently falls back to CPU — `-ngl 99` is
a request, not a constraint, and granite-3.1-8b served from system RAM at
14.8 GB RSS for weeks. The only gaming logic on this box is
`venture-enrich-nightly` exiting 0 and waiting for the next night when the
GPU is busy. **Nothing detects a game starting, and nothing emits a signal
when one does.**

Three rungs, built in order, each independently useful:

1. **Don't start a model while a game runs** — a pre-flight probe, the
   shape that already exists. No signal, no daemon.
2. **Evict models when a game starts** — needs something to notice a
   launch and act. This is the first rung that requires a running
   component, and MQTT is the obvious carrier now the bus is an estate bus.
3. **Queue requests behind a game** — requests wait and drain rather than
   failing. A queue holding real work must not lose it on restart, so this
   rung implies persistence: a table, not a unit.

The ladder matters because it keeps the daemon honest. Rung 1 needs
nothing new; if rungs 2 and 3 are never reached, the service stays small.

### The briefing inverts, which closes a five-day-old loop

If the estate owns project state, **the briefing producer moves with it** —
the two headline sections of `GET /api/sysadmin/briefing/preview` *are*
project data, so leaving the briefing here would mean either an HTTP call
into the 06:00 path or two services owning one table.

sysadmin then exposes `GET /api/briefing` as one contributor among
several. That is precisely the per-app fan-out agreed on 2026-08-06 and
never built: **the estate aggregates, apps contribute, Alfred renders.**

The cost is explicit: Alfred's pulled URL changes, so this is a two-repo
contract migration and not a directory move. ADR-0001's claim that
extraction becomes "a directory move rather than a rewrite" is true of the
code layout and **false of the interface** — worth saying plainly, because
that sentence will otherwise be quoted as though the whole job were cheap.

### What this does to phase 1

Phase 1 stays documents-only and reversible. One thing about it was wrong
and is corrected here: it said the new repository *"needs no port and no
`/api/health`: nothing in it listens"*. It will listen. So the port is
claimed in the registry and the health endpoint is designed **on day one**,
per [monitorable-project.md](../guides/monitorable-project.md) — claiming a
port late is how two services end up guessing at the same number, and this
repository holds the registry that exists to stop that.

### Alfred's side, measured rather than assumed

The owner's "Alfred can assign tasks" means **Alfred's own workload
component**, not repo tasks. Checked against Alfred's ADR-0064, which
pre-authorises exactly that shape — *"any 'turn this recommendation into a
work item' write happens in Alfred, pulling"*, joined by a nullable
`sysadmin_name` — so it is not an override of that ADR.

Its triggers were evaluated live on 2026-08-11, both being queries costing
one `curl` by design:

| Trigger | Threshold | Measured | Fires |
|---|---|---|---|
| (a) stall returns | `stalled_count ≥ 2`, two consecutive weeks | **0** | no |
| (b) estate outgrows the cap | `count ≥ 12` active | **5** | no |

Neither fires. But ADR-0064's third reason for not designing against
`GET /api/projects/next` — *"it returns 404 today; its ranking policy is
undecided by its own author"* — has **expired**: it returns 200 and the
ranking is decided with its rejected alternatives recorded. That is a
legitimate reason for Alfred to re-examine, on Alfred's side, and not a
reason to build a consumer surface here for a consumer that has not asked.

The one guardrail that stands unchanged: **the board is never written into
`trackables.projects`.** Decoration by join, never a merge.
