# Handoff — 2026-08-28

## Next action

Re-rank `SNAG-ESTATE-009` against its new cost, which today's fix changed without touching its mechanism and which was measured rather than reasoned before this line was written: driven against the live database in a rolled-back transaction, a breach the sweep had not yet seen is raised `warning` on run 1 and the first judge run after the next sweep quietens that same row in place to `info` — one row, still open, nothing raised and one refresh — so the loud rung the entry is about now lasts one sweep window rather than the life of the listener.

## Session 117 is complete — the ban is asymmetric, and its reason is what permits the reverse

`SNAG-ESTATE-010` is **fixed**. Its blob half went on 2026-08-28 with
`SNAG-AGENT-009`; what stood was the rung. Every family that
deduplicates on an open title skips a judgement whose title is already
open *before* looking at its severity, so Session 57's
`TRANSIENT_HOLDER_SEVERITY` applied only to breaches raised afterwards —
the two rows it was written for sat at `warning` for the life of a VS
Code window and were restated at that rung by `reminder_hours`
throughout.

**The instruction was to read the entry's own check first, and it is
what shaped the fix.** That check's `reached` is a deliberate
*disjunction* — an in-place rung, a resolve-and-re-raise, or the
`holder` blob alone — because when it was written any of the three
would have been a fix. Driven live at the start of the sitting it
reported `still holds`, with the standing row unmoved at `warning` while
the same `_execute` judged the identical fault `info` and raised the
witness port at `info` carrying a transient holder.

**The rule was already in this repository, stated once and obeyed by one
family.** `log_aggregator._record_recurrence` has quietened a held row
in place since Session 66: **Session 39's ban on in-place severity
changes is asymmetric, and the reason it exists is what makes the
reverse safe.** The ban is about an escalation needing to be *heard* —
the tray fingerprints on `{severity}:{title}`, so bumping the column
keeps a fingerprint already suppressed — and a quietening wants exactly
that outcome. Four other deduplicating families needed the same answer
and had no way to ask for it. It is `core/escalation.may_quieten_in_place`
now, beside the ban it depends on, and `BaseAgent.refresh_alert` has an
optional `severity=` that asks it.

**"Downward is safe" is the obvious reading of that asymmetry and it is
too broad by one rung.** `critical` → `warning` in place hands the tray
a fingerprint it *will* speak, so the quietening arrives as a fresh,
less urgent notification about a fault that has not improved — which is
`escalation.step_for`'s own refusal, met from the other side. Only the
**floor** of `SEVERITY_ORDER` is inaudible-or-asked-for: it is below
`tray.notify_min_severity` on this box, and an operator who lowers that
knob to `info` has asked to hear reclassifications. `QUIETEST_SEVERITY`
is derived from the ordering rather than written as `"info"`, and a
source-reading test pins the provenance because a literal and a
derivation both *read* `info`.

**The tray's threshold is deliberately not consulted, and could not have
been.** The obvious gate is "quieter than `notify_min_severity`", which
makes the daemon a second reader of a policy the tray owns; measured,
the backend cannot see that key at all — `AppConfig` parses
`notifications.tray:` (`TrayNotificationsConfig`, "the slice the
*backend* needs") while `notify_min_severity` lives in the top-level
`tray:` section the tray parses for itself.

**The entry asks for a reason the new severity is durable; the answer is
that the transition is one-directional rather than that the rung is
stable.** Its fourth bullet refuses resolve-and-re-raise because a
producer wobbling between two rungs would clear and re-open the row each
time. Under an in-place, one-directional quietening that cannot happen:
down is silent, up is refused and belongs to `step_for`. No row is
resolved, none re-raised, and the count of standing faults does not
move.

**The gate order is where this would have shipped green and inert.**
`refresh_alert`'s existing gate is "has the text moved", and the
founding case is a breach the estate republishes word-for-word every
hour with only the rung changed. The quietening is asked **before** the
text comparison and can carry a write on its own —
`test_a_quietening_lands_even_when_the_sentence_has_not_moved` is the
one test that catches it, falsified against exactly that mutation.

**It reaches the second speaker too, which nothing had noticed.** The
tray is fixed for free — the old pair leaves the poll and the new one is
dropped below `notify_min_severity` before `_consider` can act.
`monitor/desktop.py` is not: `_SpokenFault.severity` is the rung it
*announced* and `_still_open` asked only which titles were open, so the
understudy would have gone on restating at `warning` a fault the judge
had decided is `info` — the founding entry surviving inside the fix for
it, in the one component that exists for the case where the tray is
down. That read returns `{title: severity}` now and the sweep takes the
row's rung, loudest wins for the beat in which an escalation has two
rows open.

**Populations, measured rather than assumed.** The estate judge is the
only family with a live one — its rung varies and it holds **131** held
judgements across 77 of 240 runs. `SysAdminAgent._raise_judged`'s is
empty **by construction**: every family there pairs a rung with a *title
kind*, so a disk breach at the warning and critical thresholds is two
titles rather than one row at two rungs. The port family's is empty
because its rung is a constant, now `PORT_ALERT_SEVERITY` rather than a
literal in the raise and nothing at all in the held branch. Both are
wired regardless — the entry *is* what happens when a family gains a
quieter rung and its held branch was never told what rung it judged.

**The check retired with the entry and the detector did not.** Its drive
is `tests/test_quietened_judgement_live.py` (`FROZEN_TABLES`' rule) and
is **stronger than the check**: the disjunction was right while the
shape was unknown and is wrong now, since a resolve-and-re-raise would
satisfy it while rebuilding `monitor/collation.py`'s flip-flop. The live
test asks which shape — rung moved in place, one row, still open,
nothing raised and nothing resolved — and the resolve-and-re-raise
mutation turns three of its four tests red where the check would have
said `mismatch` and called it fixed. The two-probe disjointness
assertion moved with it rather than retiring: both drives still write
ports and a holder string into the same two tables.

**One falsification passed against deliberately broken code**, which is
the part worth carrying. The "loudest of two open rows wins" test
yielded its rows loud-*last*, so a last-one-wins implementation with no
`_loudest` call in it answered correctly by accident. The query has no
`ORDER BY` — which is the whole reason `_loudest` is there — so it
drives both orderings now. Three stand-ins again modelled a database
this code no longer talks to: `FakeAlert` with no `severity` (the column
is `NOT NULL` behind `chk_alert_severity`), `_FakeSession` answering the
open check with titles alone, and a fail-closed test that broke one
reader out of two and so no longer tested a database that would not
answer. Session 110's lesson, arriving for the second sitting running.

**Verified on the box, not only in the tree.** Suite **2838** (2832 + 26
− 20, the twenty leaving with the retired check), `ruff` clean, `mypy
sysadmin` clean. Daemon restarted **20:53:24** with a clean journal —
the only warning is the standing `api.auth_token is not set`. All nine
`check-ops-claims` claims green; the snag sweep reads **17** open
entries with every one carrying a check. **The fix ships untriggered**:
the box holds 0 open alert rows, so nothing on it was reclassified by
the deploy, and the refutation is the retired check's own drive against
the live database in a rolled-back transaction — `warning → info`, one
row, unresolved, `alerts_raised=1` for the witness port alone.

## What was left undone, and why

- **A downward step that stops short of the floor still cannot reach a
  standing row**, and that is a design position rather than a residue.
  It is `step_for`'s refusal: the fault has not improved, and
  `warning:title` is a fingerprint the tray speaks. No family on this
  box can produce one today — `_raise_judged`'s rungs are paired with
  title kinds and the estate judge's two rungs are `warning` and the
  floor — so the population is empty and measured, not merely unfiled.
- **No `alert.refreshed` or `alert.quietened` event is queued.** The SSE
  stream has no consumer for one and an event nobody reads is
  `SNAG-CFG-001`'s shape. The corrected rung reaches the tray on its
  next poll of `GET /api/sysadmin/alerts`.
- **`SNAG-ESTATE-009` was re-measured rather than closed.** Its
  mechanism is untouched — the sweep is six-hourly and the judge hourly,
  so a dev server started inside a sweep window is still unattributed
  and still speaks at `warning` on the first run that sees it. Only the
  *duration* changed, and the entry has the measurement.
- **`monitor/desktop.py`'s new read is deployed but unexercised on this
  box**, because the tray is running and the tray gate returns before
  the sweep queries anything. It is driven against real PostgreSQL by
  `tests/test_desktop_store_live.py`, whose timeline has the tray away.
