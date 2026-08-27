# Handoff — 2026-08-27

## Next action

Write the twenty-second check against `SNAG-ESTATE-004` — the fourth driven across a repository boundary and the first whose claim is entirely about another repository's *surface* rather than its code, so carry in Session 87's instrument rule: probe only public symbols, because a private helper's name is what their fix renames; record estate-manager's commit state beside the verdict, since a verdict about somebody else's tree means nothing without the state it was taken at; and report every way of not-running as `unknown` rather than as a skip, `ports_checked`'s rule at a boundary — with `SNAG-SVC-001` the other candidate and the harder judgement rather than the harder build, since its own body says both honest resolutions are the owner's, so a check there would be measuring a narrowing nobody has decided to keep.

## Session 99 is complete — the twenty-first check, and the entry that was runner-up three times

`SNAG-SVC-002` is **checked and stays open**. Checked entries
**18 → 19**, unchecked **6 → 5**, open unmoved at **24** (none opened,
none closed) — measured either side of the edit by driving
`estate.snags.read_snags`. Suite **2635 → 2653**,
`tests/test_snag_claims.py` **231 → 249**.

**The entry had been ranked runner-up three times and rule 1 is the whole
reason.** The obvious check measures the disjointness its own second
bullet reports — measured this sitting, **nine declared timers against
five scheduled agents, zero overlap** — and that is a property of *this
box*. One scheduled job moved to a `oneshot` + `.timer`, which
`monitorable-project.md` requires of every new one, and such a check
reports the entry fixed on a day nobody has touched either module.
`check_timer_agent_two_owners` builds the thing this box has not got: an
agent whose schedule is a timer.

### What the sitting settled

- **One fact, two vocabularies, and the shared name is not what makes it
  one subject.** A daily schedule with one last-run instant goes to
  `summarise_agent`/`stalls.evaluate` as an agent that has not run and to
  `recommend` as a timer whose `LastTriggerUSec` stopped moving. Both
  speak, and *simultaneously*, because `timer_stale_multiplier` **is**
  `stall_grace_multiplier` — the entry's own stated mitigation — so one
  elapsed value crosses both thresholds.
- **Three instruments, because the two fixes the entry names move
  different things.** A family going silent is the fix it asks for; a
  rung on `timer_stale` is the fix it **forbids by name** and is
  unreachable from the first instrument, since both families go on
  speaking either way. Its headline claim — neither knows the other
  exists — is measured as the *importer sets*, disjoint today
  (`monitor/agent.py` against `health_review.py`,
  `reliability_history.py`, `routers/services.py`), which is the one
  thing a composing caller feeding `_observed_fires` into the stall
  family could not avoid moving.
- **Rule 7 for the fourth time.** `service_recommendations.py` already
  carries the word `stalls`, in `_timer_stale_row`'s own docstring — the
  entry's sentence written into the module the entry is about — so a grep
  reports the cross-reference as already existing and an import walk
  never sees a docstring. Pinned by a test at the real file.
- **Two witnesses, and the second one's `unknown` names both readings.**
  A fresh schedule must read not stalled; a still-firing timer whose last
  run failed must yield a `timer_failed` row through the same call and
  the same confidence gate. When that second witness fails, the timer
  half having been *removed* is the entry's own fix and is named in the
  note, because a reader who does not go and look would otherwise never
  learn it may have landed.
- **The check is excluded from its own population, and it is not
  bookkeeping**: driving both families means importing both, so the only
  thing here that knows the two exist would otherwise refute the entry on
  every run.

### The falsification corrected the check, then corrected its reason

The first stand-in put a rung at six cadences and came back `match` — the
stand-in was wrong. The second clocked its rung off the box's one
escalation gap, the only shape available to a family recomputed per
request, and **also** passed. The two drives straddle a rung only when
its gap falls in `[overshoot, overshoot + 2 x escalate_after_hours)`; at
the draft's one-cadence overshoot that window is **24h to 72h** here, so
every rung shorter than a day read loud at both drives. The reason
written first — "the two numbers coincide, so it reads loud at both" —
was approximately right and imprecise, and only the arithmetic said
which. The overshoot is one check interval now, widening the window to
**5 minutes to 48 hours**, and a test drives both constants and asserts
the old one still hides a sub-cadence rung.

### Found on the way, without looking for it

**A count taken across a repository boundary moved underneath the
measurement, and the natural reading of it was wrong.**
`estate.snags.read_snags` returned **93** entries over this document
against the **70** three sittings had recorded — which reads as stale
prose, and is not. `estate-lib` is an **editable install resolving into
estate-manager's working tree**, so the figure was taken against
uncommitted work in another repository at 14:12; their commit `1e7a9a9`
landed at **14:21:59**, growing the reader a third dialect (their
ADR-0052). At the previous reader today's document reads **70 / 24** —
exactly what was recorded — and the *open* half is 24 under both, which
is the figure the board publishes and the one
`TestAgainstTheOwningParser` pins, so nothing here depended on it.

**What it cost is the lesson.** `cross-repo-instrument-must-be-public`
says record the other repository's commit state beside the verdict; not
doing so put a wrong correction into three documents before the timeline
was checked. Filed at estate-manager as friction rather than absorbed:
an editable install publishes a neighbour's *uncommitted* state with no
version stamp, and a consumer cannot tell that from a document of its own
going stale.

### State of the box

`sysadmin` restarted at **2026-08-27 14:20:53**, `/health` **200**,
`alembic current` **016** at the packaged head, `alerts` holds **1**
unresolved row (`info: Weekly disk review ready`). `check-ops-claims.sh`
green on all nine claims; `check-snag-claims.sh` reports all nineteen
checked entries still holding and names the five that carry no check.
The restart was taken rather than argued with for the reason Sessions 81
and 84–98 took theirs: only `sysadmin/snag_claims.py` moved, which the
daemon does not import, and correcting the artefact the script names
beats hand-verifying that it is wrong.
