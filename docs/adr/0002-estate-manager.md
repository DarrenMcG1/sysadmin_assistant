# ADR-0002: Shared infrastructure gets an owner that is not an application

- **Status**: accepted, unbuilt
- **Date**: 2026-08-11
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
