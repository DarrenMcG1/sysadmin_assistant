# ADR-0003: The broker credential arrives by LoadCredential

- **Status**: accepted
- **Date**: 2026-08-11
- **Session**: executed by estate-manager Session 2 under its founding-
  extraction exception (estate ADR-0002); recorded here because the unit
  is this repository's
- **Answers**: Session 39's blocked MQTT half — how this service holds a
  broker identity without breaking its own conventions
- **Counterparts**: estate-manager ADR-0001 (the reasoning), ADR-0005
  (the provisioner that creates `sysadmin-publisher`); Alfred ADR-0068
  (the `reconcile()` narrowing that lets the credential survive)

## Context

Session 39 wanted to publish critical alerts to MQTT and hit two walls:
Alfred's `dynsec.reconcile()` deleted any hand-provisioned client on its
next start, and both dynsec roles were scoped to `alfred/events/#` so a
neutral topic root was denied by the broker. Both walls are now down
(Alfred ADR-0068; estate-manager's `mqtt/dynsec.yaml` widened the roles
and provisions `sysadmin-publisher` with role `estate-publisher`,
verified live 2026-08-11 — publish on `estate/alerts/test` reached a
subscriber-role client, and the identity survived an Alfred restart).

What remained was where this service keeps the password. The constraint
that decides it: **an alerting path with a live dependency on another
service is not an alerting path** — the credential must be held locally,
not requested from the estate at runtime. And this repository's own
rules close two doors: `config.yaml` is tracked in git and has never
held a secret, and no environment variables are read (CLAUDE.md), which
rules out Alfred's `EnvironmentFile=` pattern.

## Decision

`sysadmin.service` carries
`LoadCredential=mqtt:/etc/credstore/sysadmin-mqtt`. systemd reads the
root-owned 600 source file before dropping to `gaddi` and exposes it to
the process as `$CREDENTIALS_DIRECTORY/mqtt` — never in git, never in
the environment, never in the process list. The source file is generated
by estate-manager's `scripts/install-broker-system-units.sh`; the same
file feeds the estate provisioner's password re-sync, so the broker and
this unit cannot disagree about the password after a rotation plus
restart.

The publisher code (the still-open "Publish alerts to MQTT" task) reads
`Path(os.environ["CREDENTIALS_DIRECTORY"]) / "mqtt"` at startup. The
one environment variable involved is set by systemd itself as part of
the credential mechanism, not by configuration — the no-env-vars rule is
about where *settings* live, and the setting (host, port, username,
topic) will live in `config.yaml` as always; only the secret rides the
credential.

Rejected:

- **A path named in `config.yaml`** — workable, but file permissions
  become the entire protection and the config would half-describe a
  secret it must not contain.
- **Relaxing the no-env-vars rule** with an `EnvironmentFile=` — a
  convention worth removing deliberately if at all, not as a side effect
  of one password.
- **Requesting the credential from the estate at runtime** — reinstates
  the live dependency this whole design removes.

## Consequences

- If `/etc/credstore/sysadmin-mqtt` is absent the unit **fails to
  start** — deliberate: a monitor silently running without its alerting
  credential is the silence-reads-as-health shape again. The install
  script creates the file before installing the unit.
- `tests/test_systemd_units.py` pins the credential id (`mqtt`) and the
  absence of any `EnvironmentFile=`.
- The MQTT username (`sysadmin-publisher`) and broker address are not
  secrets and will be ordinary `config.yaml` settings when the publisher
  lands.
