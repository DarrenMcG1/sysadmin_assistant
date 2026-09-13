# ADR-0012 — A transient holder has no project, so `wrong_project` has nothing to compare

**Date:** 2026-09-13
**Status:** Accepted
**Context:** estate message `11cf5113` (estate-manager → sysadmin_assistant,
filed 2026-09-12), which drove the case on the live box and left the
judgement here.

---

## 1. The question that was asked

estate-manager bound `127.0.0.1:3300` — the port their registry gives to
`venture-assistant` — from `~/projects/web/portfolionew` inside
`app-code-oss-5162.scope`, and observed that `observe_listeners()`
attributed it fully (pid set, unit set, `attributed=True`,
`transient=True`) while `judge_ports()` filed **zero** findings, because
`holders` skips `listener.transient`.

Their argument for reopening it: the transient exclusion is plainly right
for `port_shared` and `wrong_unit`, **whose remedies name a unit**, and a
comparison against a *document* has no unit in its remedy — so should
`wrong_project` read `transient_ports` the way `PortAttribution.reading()`
already does?

**No.** The exclusion is right for `wrong_project` too, and for a reason
that is not the one the question assumes.

## 2. The argument is about the remedy; the obstacle is the operand

`wrong_project` does not compare a *unit name* against the registry. It
compares the **project that owns the unit**:

```python
owner = unit_projects.get(keys[0])
if not owner:
    continue
```

So the family has a unit in its *question* even though it has none in its
*answer*. The remedy-shaped test the message proposes does not reach the
thing that is actually blocking the finding.

## 3. The proposed fix is inert, and structurally so

`unit_projects` is `scan_units`' answer to *who owns this unit*, and it is
built from `discover_units`, which walks `~/.config/systemd/user` and
`/etc/systemd/system` admitting entries whose name ends in
`UNIT_SUFFIXES = (".service", ".timer")` **and which are real files**.
systemd has no persistent scope files — which is exactly why
`Listener.transient` treats a `.scope` as per-launch *by construction* —
so a `.scope` key can never appear in `unit_projects`. Measured on the
live box, 2026-09-13: **0 of 30** `unit_projects` keys end in `.scope`.

Driven as a counterfactual rather than argued, with a real squatter in a
real transient scope holding 3300:

| `holders` map | `wrong_project` rows | 3300's fate |
|---|---|---|
| transient **excluded** (today) | 0 | skipped at `if not seen` |
| transient **included** (proposed) | 0 | skipped at `if not owner` |

The port moves from one `continue` to a different `continue`. Nothing
else in the report moves. **The fix would have shipped green and inert**
— `SNAG-TRAY-008`'s shape, where a correct-looking change is unreachable
on the box it was written for.

## 4. Had it been reachable, the population refutes it

The scenario is not hypothetical and did not need driving: it is already
in `unit_audits`. Across the **190** stored sweeps carrying a ports blob,
**129** carry a transient holder on a registry-claimed audited port.
Three ports account for all of them, and **not one is a fault**:

| Port | Sweeps | Registry says | Why it is not a fault |
|---|---|---|---|
| 1716 | 107 | `_kdeconnectd_` | the row's own cell says it is *"not a `~/projects` project"* and is *"tied to the desktop session rather than a unit"* — a transient `dbus-…@0.service` holding it is the row working as written |
| 3300 | 22 | `venture-assistant` | the row reads *"dev server for now; unit to follow"* — held by `app-code-oss-112152.scope` on 22 sweeps, 2026-08-24 → 08-26 |
| 8700 | 7 | `InvestingAssistant` | same shape, `app-code-oss-673629.scope`, 2026-09-02 → 09-05 |

So the family the message proposes would fire on **68 %** of all sweeps,
permanently, and its founding specimen — a VS Code scope on 3300 — is
what two of the three registry rows *predict*. That is
`SNAG-UNITS-002`'s refusal to ship fifteen rows on the first run, at a
worse ratio, and `known_noise` rule 3 met from the other side: volume is
what makes a fault worth looking at, never evidence that one exists.

## 5. It could only ever remove findings, never add one

Worth stating because it inverts the direction the message assumes.
`wrong_project` skips a port with more than one holder — with two,
`port_shared` is the finding and attributing the row to either would be a
guess. Widening `holders` can therefore take a port from one holder to
two and **suppress a `wrong_project` row that fires today**; it can never
create one, for §3's reason.

**Empty population, measured**: no claimed audited port has ever carried
a stable *and* a transient holder in the same sweep — 0 across all 190.
Stated rather than implied, as `SNAG-UNITS-006` states its own.

## 6. The fault they drove is real, and its discriminator is not the unit

`portfolionew` squatting `venture-assistant`'s 3300 is a genuine problem
and neither repository can currently see it. The reason is that the
discriminator is not the holder's *unit* — there isn't one worth having —
but the holder's **working directory**, and that route dies too:

- `/proc/1911934/cwd` resolved to `/home/gaddi/projects/web/portfolionew`,
  which carries **no `.project.yaml`** and is not a registered project.
- So a cwd-based attribution lands in *"the row names something that is
  not a project here at all"* — `unknown_registry_projects`, which is
  `SNAG-ESTATE-005`'s bucket — rather than in a finding.
- The loose test that *appeared* to match it (`startswith(ref.path)`)
  matched the sibling project `portfolio` on a lexical prefix.
  `scan.py`'s `_under`, which requires the `/` separator, matched
  nothing. The module's own rule caught the false positive.

Filed as `SNAG-PORT-005` rather than absorbed or fixed here: the fix
needs `/proc/<pid>/cwd`, which is a new impure read, on an operand a
process can `chdir` away from, for a population whose only live specimen
is unregistered.

## 7. The decision is already recorded, and that half needed nothing

This repository's standing objection to a consumer that silently declines
to judge — *"a consumer that silently declines to judge a published
finding is `SNAG-CFG-001`'s shape, with nothing recording the decision"*
— is already answered here, by Session 128's rule 7 and not by this
sitting. `PortAttribution.reading()` returns `transient` for exactly this
case, and `PortReport.as_blob()` publishes `transient_ports` beside
`unit_ports`. Verified live against the squatter:

```
of(3300):      {'unit': 'repro-squat-3300.scope', 'scope': 'user', 'transient': True}
reading(3300): {'reading': 'transient'}
```

So the port is not silently dropped: a reader of `GET /api/units/status`
or of an estate-judge row's `details['attribution']` is told that the
sweep looked, named a holder, and declined to treat it as an identity.
**Nothing is added**, because the field a later sitting would reach for
already exists and already answers.

## 8. What this changes

Nothing in production. What ships is:

- this record;
- `tests/test_unit_ports.py::TestATransientHolderIsNotAProject` — three
  tests pinning §2, §3 and §5, so a later sitting implementing the
  obvious fix goes red rather than green-and-inert;
- `SNAG-PORT-005` for §6.

## 9. What is *not* decided here

The message's second half — *"our `run_check()` filed nothing either, and
worse: it published `claimed_but_silent/warn` before the bind and nothing
during it"* — is estate-manager's check and estate-manager's judgement.
A squat cancelling the one warning that existed is a real polarity
problem and it is theirs; recording a recommendation about it here would
be the ruling the estate rules forbid.

The message's aside — `unknown_registry_projects == ['sysadmin-service']`
— is **not a second finding**. It is `SNAG-ESTATE-005`, open and
delegated since 2026-08-15, watched every sitting by
`check_estate_port_8500`: the registry's 8500 row names `sysadmin-service`
where the manifest id is `sysadmin-assistant` and the directory is
`sysadmin_assistant`, so neither matches and the name lands in the
evidence bucket by design.
