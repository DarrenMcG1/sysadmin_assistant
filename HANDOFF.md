# Handoff — 2026-08-28

## Next action

Decide whether anything should check the snag_list header paragraph, which Session 118 left open and Session 119 did not take: `check-snag-claims.sh` reads entry claims and `check-ops-claims.sh` reads STATUS.md's block, so the paragraph whose whole job is to record movement is read by neither, which is how it went six sittings without being written.

## Session 119 is complete — the model is not the file

The guard Session 118 offered is **built**:
`tests/test_config_defaults.py::TestTheLoudRungEndsBeforeItIsRestated`
asserts `agents.service_discovery.scan_interval_hours` +
`agents.estate_judge.poll_interval_hours` **<** the tray's
`reminder_hours` — the arithmetic that bounds `SNAG-ESTATE-009`'s loud
rung at **7 h** against a **24 h** restatement, and which nothing
protected. The lever is one config line: raising the sweep to daily puts
the sum at **25**.

**The reason it was offered as weak does not hold, and that is the part
worth carrying.** The handoff said a guard *"can only read
`notifications.desktop.reminder_hours`, the understudy's copy"* because
`TrayNotificationsConfig` parses `mute_services` alone. It does — and it
is the **backend's model, not the file**. `sysadmin_tray/config.py`
reads `notifications.tray.reminder_hours` out of the same `config.yaml`,
ships in this wheel, and is already imported across the seam by
`tests/test_desktop_notifier.py`. Driven at a copy with the tray leaf set
to 6, `load_tray_config` returns **6.0** while the understudy still reads
**24.0**. `may_quieten_in_place` rule 3 is untouched: it refuses the
*daemon* a policy the tray owns, and a test is not the daemon. CLAUDE.md
now says so beside that rule, because reading it the wider way cost a
sitting.

**A second gap closed with it, and it is the one already written down as
pinned.** `test_the_reminder_interval_matches_the_trays` compares
`DesktopNotificationsConfig()` against `NotificationSettings()` — two
objects constructed with **no file** — so the shipped copies can read 6
and 24 with that pin green and the two speakers restating one standing
fault four times a day apart.
`TestTheTwoSpeakersAgreeInTheShippedFile` is the half that can see an
edit, and it carries the witness the defaults pin cannot supply.

**Two rules the guard encodes that are not the obvious version.**
`reminder_hours: 0` is a **skip**, never a pass and never a failure —
both speakers gate on `interval <= 0`, so the claim is vacuous, and
`ports_checked`'s rule says a check that could not look must not be
served as one that looked and was happy. And the sweep being **enabled**
is asserted separately, because `_attribution` reads the newest *stored*
sweep with no age gate: a disabled `service_discovery` freezes it and the
loud rung is bounded by nothing at all, which the sum cannot see.
Disabling `estate_judge` is the opposite and needs no assertion.

**Three drafts of the detector test were wrong the same way**, each
keying on a *mutable value*. `ceiling == 25` is satisfied by a
`config.yaml` already reading 24 and a replacement that matched nothing;
`before == 7` pins a number the owner may change, so a sweep legitimately
retimed to 4 h read as a broken detector; and
`replace("scan_interval_hours: 6", …)` matches nothing the day that leaf
moves. What ships builds the mutation through parsed YAML — setting the
interval to `reminder_hours`, which violates by construction whatever
either leaf says — and asserts the **delta**. Falsified in both
directions: violations red (sweep 6 → 24, tray 24 → 6, sweep disabled,
judge poll 1 → 24), legitimate configurations green or visibly skipped
(sweep retimed 6 → 4, reminder raised to 48, both reminders 0).

**`SNAG-CFG-003` is filed** for what a test cannot reach: it runs when
the suite runs, `claude-precommit.sh` runs the schema check and lints
rather than pytest, and a `SIGHUP` installs a config from disk reporting
only whether each changed leaf could be *delivered* live. P4, empty
population, and the cheap fix is the one `may_quieten_in_place` rule 3
forbids — so it is a question for the owner rather than an obvious
repair.

**No restart owed and none taken** — no production code changed. Suite
**2838 → 2844**, six added and none retired; nine ops claims green; the
live snag parser reads **100 → 101 entries, 17 → 18 open** at
estate-manager's committed `0667f43`.

## What Session 119 got wrong, and what it cost

- **One `git checkout` on the uncommitted test file destroyed the whole
  addition mid-sitting**, used as a careless way to revert a temporary
  mutation. Recovered from context and re-driven from scratch, ~15
  minutes. The count arithmetic is what proved the rewrite was complete
  — 2838 + 6 = 2844 — and it is the first time that check has caught a
  live clobber here. Mutations belong in a scratchpad copy; `git
  checkout` is not an undo for work that is not committed.
- **`read_snags` takes the document's `text`, not a path**, and handed a
  path it answers `format: unrecognised` with **0 entries** — a shape
  that reads as an emptied register rather than as an error, which is
  `ports_checked`'s rule arriving in another repository's API. A
  consumer publishing movement figures off it reads 100 → 0 entries and
  17 → 0 open, i.e. every entry closed. The first count of this sitting
  was confidently wrong and silent about it. **Filed at the owner rather
  than absorbed**: cross-repo message `5a8bbc97`, carrying the cost (one
  wrong count, ~5 minutes to detect and re-derive). A message and not a
  finding — the signature is documented and the misuse was ours.
- **`uv run --active` inside estate-manager installed its dependencies
  into this repository's `.venv`**, uninstalling 22 packages and
  installing 29. Repaired with `uv sync --all-extras` and the suite
  re-run green. Drive another repository's code with `env -u
  VIRTUAL_ENV uv run`, never `--active`.

## What Session 119 left undone, and why

- **The snag_list header paragraph is still unchecked**, which is
  Session 118's second open decision carried forward unchanged. It was
  re-derived through the live parser again this sitting, which is the
  third consecutive sitting doing by hand what nothing verifies.
- **`SNAG-CFG-003` carries no check, and it is the only open entry that
  does not** — `check-snag-claims.sh` reports `17 of 18` and names it.
  The claim is cheaply checkable without a database: whether
  `claude-precommit.sh`'s executable lines invoke pytest
  (`test_schema_guard.py`'s idiom for the `upgrade` ban), and whether a
  violating config driven through `reload.py` still reports success with
  no semantic complaint. Not started because writing one to this
  registry's standard — docstring, discriminating witness, falsification
  against a stand-in *modelling the fix* — is a piece of work the size
  of this sitting's own, and one roadmap session per sitting.
- **`SNAG-CFG-003` is filed rather than fixed.** Its remedy is a design
  question — whether `reload.py` grows a *semantic* verdict beside its
  delivery report, and if so who may read the tray's leaf — and the
  population is empty. Left for the owner to rank.

## Session 118 is complete — a cost that fell is not a mechanism that closed

`SNAG-ESTATE-009` is **re-ranked and stays `P3`**. No code changed. The
live parser reads **100 entries / 17 open** either side of the edit
(estate-manager committed `b98f44d`), eighteen snag claims and all nine
ops claims are green, and no restart is owed.

**The bullet the re-rank replaces was wrong on the day it was
written**, which is the part worth carrying. It priced the failure at
*one extra toast at the start of a dev session*; the tray's
`reminder_hours` was committed at **2026-08-16 09:22:44** (`3752c78`)
and the understudy's at **11:59:53** (`a330e31`), against an entry
filed 2026-08-17. So a mid-window start cost one toast **and every
restatement due after it**.

**The family's whole life is six rows in three episodes and it settles
the point.** `3.13 h` and **`31.88 h`** at `warning`, then `11.23 h` at
`info`. The long episode began 2026-08-16 12:07:11 — **2 h 45 m** after
the tray's reminder was committed — and ran to 2026-08-17 20:00:05,
outliving `reminder_hours` by eight hours. And **both loud episodes
predate Session 57's quietening**, so this entry's own defect has never
produced a row here: a sharper statement of its check's "the population
is a timing accident".

**What Session 117 bought is a ceiling, not a narrower window.** The
loud rung ends at the first judge run after the next sweep — 6 + 1 =
**7 h worst case** against a `reminder_hours` of 24 — so the repeat is
unreachable by **arithmetic** where it was previously survived by luck,
and the old bullet's claim is true for the first time. `_attribution`
reads the newest stored sweep on every run and the held branch passes
`severity=` to `refresh_alert`, which is what makes the ceiling one
sweep interval plus one poll rather than anything longer.

**`P4` was refused on this file's only precedent for it.**
`SNAG-LOG-014` is `P4` for being *residue from a fixed entry, not a
live defect*; this mechanism is untouched, and `unswept_port_is_loud`
driven **after** the fix still reads `match` — port 65009 unnamed by
the stored sweep, judged `warning`, `holder=None`, identical detail key
set to the attributed 65008 beside it, `alerts_raised=2`. Moving the
number would say a mechanism closed when only a cost fell.

**The snag_list header paragraph was six sittings stale and is
re-derived rather than reconstructed.** It was last written for Session
111 at 99 entries / 22 open against today's 100 / 17 — one opened and
five closed across Sessions 112–117 with nothing recording it — which
is `SNAG-ESTATE-008`'s shape inside the document that exists to measure
movement. Per-sitting attribution was **not** invented; the two
measured figures are stated and the gap is named.


## What Session 118 left undone, and why

- **The margin is not asserted, and the leaf the inequality is really
  about is not readable from here.** `notifications.tray.reminder_hours`
  is the number a repeat is actually due on, and
  `TrayNotificationsConfig` parses `mute_services` alone —
  `may_quieten_in_place` rule 2, one leaf over. A guard would have to
  read `notifications.desktop.reminder_hours`, the understudy's copy,
  which is the same 24 and is held to the tray's by a **comment**. That
  is a real guard against the lever this sitting found (raising
  `scan_interval_hours` to daily puts the sum at 25) and it is a weaker
  one than it looks, so it was offered rather than built.
- **No snag was filed for the stale header paragraph**, because it was
  fixed in the sitting that found it. What is *not* fixed is that
  nothing checks it: `check-snag-claims.sh` reads entry claims and
  `check-ops-claims.sh` reads STATUS.md's block, and neither looks at
  the paragraph whose job is to record movement. Left for the owner to
  rank rather than filed unasked.



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
## What Session 117 left undone, and why

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
