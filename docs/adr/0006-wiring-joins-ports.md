# ADR-0006: `wiring` joins `ports` — admitted, and the filter had to change shape first

Decided 2026-08-30, answering estate-manager's cross-repo message
`8462bcc5-8e35-41fc-acb1-8138f351e519` (`needs_ruling=true`, filed
2026-08-29) and the condition their
[ADR-0068](../../../estate-manager/docs/adr/0068-detection-is-not-delivery.md)
§4 attached to their `PreToolUse` inbox-notice carrier.

**Admitted.** The `wiring` check joins `ports` as a second audit check
whose findings this repository speaks for. `JUDGED_AUDIT_CHECKS` names
both, `judge_audit_wiring` is the family, and a dead `SessionStart` entry
now raises a `warning` at the owner within a day of the 05:00 audit.

The estate asked whether rule 3 admits a second exception. It does, on
the ground their message names. **What their message could not see is
that admitting it by name alone would have shipped green and inert** —
§2 — and that is the substance of this document, because a one-word yes
would have closed their row while delivering nothing.

---

## 1. The question, and why the answer is yes

*(Recorded by the session 2026-08-30.)*

`sysadmin/estate/judgements.py` rule 3 says the estate's findings are
mostly not this repository's alerts, and carves out `ports` on a test
that is about **ownership**, not severity:

> Ports are the exception because no repository owns a port. A port is
> estate-wide by construction, the estate may not alert (it files
> findings and never acts), and this service is the only party on this
> box permitted to speak — so the alternative to judging it here is that
> nobody says it at all.

Every clause transfers to `~/.claude/settings.json`, and the transfer was
checked rather than accepted:

| clause | `ports` | `wiring` |
|---|---|---|
| no repository owns it | no repository owns a port | the file is in **no repository at all**, not merely unowned within one |
| estate-wide by construction | any listener on the box | carries the hook entries binding all thirteen repositories |
| the estate may not alert | their ADR-0003 | unchanged |
| repairable only by the owner | — | their ADR-0024 divides `~/.claude/` by what reads the file: the estate can own the hook script and cannot wire it |
| this service raises nothing about it itself | it does not | **measured**: nothing under `sysadmin/` or `sysadmin_tray/` reads `~/.claude` at all, so there is no double-count |
| nobody says it at all | was true, Session 26b-A | **measured by them 2026-08-29**, and re-measured here |

The last clause is the one that decides it, and the estate measured it
honestly: the topic `estate/audit/findings/{check}` appears in no code in
any repository under `~/projects` outside their own publisher; the single
consumer of `GET /api/audit/findings` was this module, scoped out by a
single string. Ten of their twelve checks file into a surface nobody is
told to read.

So this is **Session 26b-A's founding defect one check over**: a finding
that is detected, correct, machine-readable and never said out loud. The
estate's hooks cannot say it themselves — all four fail open by design,
so a dead hook and a silent one are the same observation from inside a
session — and on 2026-08-25 a paste took every hook on this box down, the
blocking `Stop` one included, with nothing able to report it.

## 2. Why the answer could not be a one-word yes

*(Recorded by the session 2026-08-30. This is the part the estate's
message does not contain, and it is not a criticism of the message —
it is a fact about this repository's code that only reading it says.)*

The filter is a **conjunction**. `judge_audit_findings` tests
`check == JUDGED_AUDIT_CHECK` **and** `severity == JUDGED_AUDIT_SEVERITY`,
and `JUDGED_AUDIT_SEVERITY` was `"breach"`.

`wiring` **emits no `breach` at any code.** Their ADR-0067 §4 refuses one
in terms: *"A breach floors the board's grade through ADR-0013's shared
predicate, which is estate rule 2's instrument, and this is not rule 2."*
Its three codes are `hook_not_wired` (`warn`), `settings_unparseable`
(`warn`), `settings_not_an_object` (`warn`) and `hook_wired_undeclared`
(`info`).

So adding `"wiring"` to a check name alone judges nothing, for ever,
with a green suite behind it. That is the shape this repository has now
recorded several times — a fix that is *"correct, green and inert"* — and
it would have closed the estate's row on a promise nothing kept.

**The obvious repair is also wrong.** Widening the severity globally to
admit `warn` re-imports `ports`' `claimed_but_silent`, which is
**availability**, and availability on this box already has an owner:
`services.yaml` plus the sysadmin agent's `% unreachable` family. A
second owner closes a row while the first still holds it true — the
defect this package's docstrings name at several scales.

`JUDGED_AUDIT_CHECKS` is therefore a **mapping from check to the
producer's severity this repository speaks for**, and that shape is the
only one in which both facts stay true:

```python
JUDGED_AUDIT_CHECKS = {PORTS_CHECK: "breach", WIRING_CHECK: "warn"}
```

`tests/test_estate_judgements.py::TestTheWiringFamilyIsNarrow::test_a_ports_finding_at_warn_is_still_not_judged`
is the guard, and the global-widening mutation turns it red.

**The estate's stale observation is load-bearing, not a footnote.** Their
message offers as fact, deliberately not as a finding, that the comment
enumerates *"all four"* checks emitting `breach` while the audit now runs
twelve. It matters more than that framing: when every check emitted
`breach`, a single `JUDGED_AUDIT_SEVERITY` was unambiguously a deference
to the producer's rung. Across twelve checks at three rungs it had
quietly acquired a **second job nobody argued for** — it was also a check
filter. The constant was not merely describing a smaller world; it was
doing work its own comment did not claim.

`JUDGED_AUDIT_SEVERITY` survives as a name because the paragraph attached
to it is the argument for *why* `ports` is filtered at `breach`, and an
argument is worth reading at the point of use. Its **value** is now
derived — `JUDGED_AUDIT_CHECKS[PORTS_CHECK]` — never written beside the
mapping, which is `max_priority_for` against `PRIORITY_MAP`'s rule. That
is pinned by an AST test rather than by comparing it to `"breach"`:
CPython interns the string, so a value assertion is true whether the
constant is derived or retyped, and only the source can answer
provenance.

## 3. What the family does, and the four places it departs from `ports`

*(Recorded by the session 2026-08-30. The rules and their reasoning live
on `judge_audit_wiring`; this records the departures, because a reader
who knows the ports family will expect them to match.)*

1. **The identity is `subject` + `detail['event']` — the reverse of the
   ports family's rule 3.** There, `subject` is producer prose
   (`"port 3300"`) and the machine-stable half lives in `detail`. Here
   `subject` **is** the machine-stable half: the estate's `DeclaredHook`
   documents the filename as chosen precisely because it is *"stable
   across moves of the repository in a way an absolute path is not"*.
   Read off the producer rather than assumed to match the sibling.

2. **The kind is discriminated by the shape of `detail`, never by
   `code`.** `code` is computed by the producer, folded into
   `fingerprint`, and then dropped — `AuditFinding` has no column for it
   (`SNAG-ESTATE-006`), re-verified against the live endpoint on
   2026-08-30. A `warn` finding carrying `detail['event']` is about one
   hook; one without is about the file.

3. **There is no roll-up, and that is measured rather than omitted.**
   The ports roll-up exists because the port population is unbounded —
   any listener on the box — so many at once means the registry itself is
   wrong. This population is bounded by the estate's own `hooks/`
   directory: **four scripts, each declaring exactly one event**
   (measured 2026-08-30), so the ceiling is four rows. The collapse case
   is already the producer's: an unparseable `settings.json`
   short-circuits its check to a **single** finding rather than one per
   hook. What is left uncollapsed is the 2026-08-25 shape — a well-formed
   block pasted at the top level, which parses and wires nothing — and
   four rows naming four hooks is not the fifteen `SNAG-UNITS-002`
   refused to ship. A threshold here would be invented against a
   population that has never exceeded it.

4. **`critical` was considered and refused.** An unparseable
   `settings.json` takes the blocking `Stop` hook down, which is the one
   fault on these five surfaces that is genuinely about *this* box rather
   than about the estate being a day behind — so `DEFAULT_SEVERITY`'s
   *"nothing here is an outage of this box"* is narrower than it reads,
   and this is the exception. It still gets `warning`: `critical` breaks
   the DND windows by configuration and is what the tray leaves on
   screen, reserved for a fault costing something *now*, and a dead hook
   costs the **next** session rather than the running one. The estate
   refused `breach` for this check on exactly that shape of argument —
   not borrowing an instrument built for a different rule — and taking
   `critical` here would be that borrowing performed in this repository.

The `info` code is not judged, for **the producer's own stated reason**:
their check says *"an extra event is the owner's prerogative over their
own config, and the estate records it rather than judging it"*. A
consumer that judged it would be a second opinion on a policy the
producer declined to hold — `claimed_tool_default`'s treatment one check
over — and `info` is below `tray.notify_min_severity` here in any case.

## 4. What the live drive found that reading could not

*(Recorded by the session 2026-08-30.)*

The family ships with a **zero-row population** — four hooks declared,
four wired — which is `ports`' starting position exactly. So it was
driven against the real producer rather than only against literals:
estate-manager's `estate_service.audit.checks.wiring.run_check`, in their
venv, at their commit `003f3bc` with a clean tree, against four specimens
built from this box's live `~/.claude/settings.json`. Public symbols only
(`run_check`, `WiringConfig`, `Finding.as_payload`), because a private
helper's name is what their next fix renames. The recording is
`tests/fixtures/estate_audit_wiring.json`, and it models the **HTTP**
wire — `code` dropped — rather than the MQTT one.

Measured: clean → **0** findings; the 2026-08-25 top-level paste → **4**,
one per hook; the truncated paste → **1**; `SessionStart` removed → **1**.
Through this repository's judge: 0, 4, 1 and 1 rows respectively, the
last of them titled `Estate hook inbox-notice.sh not wired for
SessionStart` — which is the estate's ADR-0068 §4 condition, spoken.

Three things only the drive said:

- **`details['hook']` was wrong on one specimen in four.** The key was
  written as `hook` and reads correctly on three; on an unparseable
  `settings.json` the producer's subject is the **config file's path**,
  so the key promised a hook name and delivered a file. One field meaning
  two things by row shape is `UnitFinding.enabled`'s trap, caught before
  shipping. It is `subject` now — the producer's own field name — which
  makes the mismatch impossible rather than merely unlikely.

- **The partition guard was not a guard for this family.** All four of
  `TestTheSurfacePartition`'s tests passed *before* the wiring titles were
  added to `_every_title`, because nothing produced them — so
  `SURFACE_TITLE_PATTERNS` could have lacked `Estate hook %` and the suite
  would have stayed green while a row saying *every hook on this box is
  down* sat in `alerts` with nothing able to resolve it. The enumeration
  is hand-maintained, which is how a stray pattern ships;
  `TestEveryJudgeFunctionReachesThePartitionGuard` makes the omission an
  error.

- **One falsification passed against deliberately broken code**, which is
  the part worth carrying. `test_the_code_the_wire_drops_is_never_needed`
  asserted a true premise (no `code` on the wire) and a true consequence
  (the file-level row is still produced) and could distinguish nothing:
  the recorded findings carry no `code` at all, so a code-reading judge
  and a detail-reading one agree by accident. A constant observation is
  not evidence unless something in the population would have forced a
  different one. It is two tests now — the premise, and a **witness**
  where the two signals disagree (`code: settings_unparseable` beside
  `detail: {"event": "Stop"}`) — and the mutation dies on both
  parametrizations.

Twelve mutations were driven and twelve killed, one of them only after
the test above was strengthened.

## 5. The limit, stated rather than worked around

*(Recorded by the session 2026-08-30.)*

The producer's `fingerprint` is `<check>:<subject>:<code>` and **carries
no event**, so two events declared by one hook would share one
fingerprint and therefore one `standing_days`. Empty population on
2026-08-30 — all four hooks declare exactly one event — and it is the
estate's identity to change, not this module's to parse around
(`SNAG-ESTATE-002`'s rule: splitting a producer's format is this
repository parsing something the estate owns). `standing_days` is carried
as evidence and never as identity, so the row is correct either way. It
is reported back in the message's close note rather than filed as a
finding, because it is an observation about their format and not friction
this sitting hit.

## 6. What this does to the estate's row

*(Recorded by the session 2026-08-30.)*

Their ADR-0068 §4 states both outcomes. This is the **admitted** branch:
a dead `SessionStart` entry raises a judgement at the owner within a day,
the carrier's remaining value falls to the sub-day window, their ADR-0043
§1's *"interim"* resolves as **closed**, and withdrawal proceeds on their
12.3 ms arithmetic alone.

Two things this repository does **not** claim, so they are not read into
the ruling:

- **Whether to withdraw the carrier is theirs.** This ADR rules on which
  checks this repository speaks for. The 12.3 ms per write-shaped call in
  thirteen repositories is their measurement and their trade.
- **Detection is still not delivery, and the gap is now bounded rather
  than closed.** The audit runs daily at 05:00 and this agent polls
  hourly, so the worst case from a bad `settings.json` edit to a toast is
  a little over a day — not immediate, which the carrier is. Their §4
  accepts that bargain explicitly; it is restated here so a later session
  does not read "admitted" as "equivalent".

## 7. Rejected

*(Recorded by the session 2026-08-30.)*

- **Decline, and rule that nobody will ever say it.** A complete answer,
  and the estate said so. Refused because every clause of this
  repository's own stated test transfers, and declining would have been
  a ruling made against the test rather than by it — with the cost
  landing on the abnormal case the whole control exists for.
- **Widen `JUDGED_AUDIT_SEVERITY` to `{"breach", "warn"}`.** §2. It
  re-imports `claimed_but_silent`, whose lifecycle already has an owner.
- **Admit `wiring` by name and leave the severity alone.** §2. Green,
  inert, and it would have closed the estate's row on nothing.
- **Judge the `info` code too.** §3. A second opinion on a policy the
  producer declined to hold.
- **A sixth surface for the wiring family.** It arrives in the same
  payload from the same HTTP call, so it is one surface: read together,
  swept together, and a partial read darkens both honestly. A sixth
  entry would claim two independent reads where there is one.
- **A roll-up threshold of its own.** §3. Invented against a population
  bounded at four by the estate's own `hooks/` directory, and against a
  producer that already collapses the case a roll-up would be for.
- **Reading `~/.claude/settings.json` here to check the wiring
  directly.** The estate owns the hook scripts and the declaration; a
  second reader would give two answers to one question at two moments
  with neither surface saying which it used —
  `EstateJudgeAgent._attribution`'s refusal, one file over. The estate
  publishes; this repository judges. That is the swap ADR-0005 records
  and this ADR does not disturb it.
