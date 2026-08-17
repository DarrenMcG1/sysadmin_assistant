# Handoff — 2026-08-17

## Next action

Take `SNAG-DOCS-001` and move `CLAUDE.md`'s fifteen project-endpoint contracts and five `sysadmin/projects/*` narratives behind pointers to estate-manager, because the file loaded into context at the start of every session describes a domain that left this repository on 2026-08-13 — and this sitting is the second consecutive demonstration that a document nothing checks is read as fact.

## This session — Session 56, the snag that was already fixed

**Not the recommendation, and no code changed.** The sitting opened on
`SNAG-DB-002` and closed it by measuring the box before reading the
entry. The remedy half had been carried out by **estate-manager** on
2026-08-13 in two passes (`eb51ff6` 18:03, `52b312c` 20:29), via their
`scripts/refresh-collations.sh` — which encodes this entry's own trap:
never `REFRESH` unless that database's `REINDEX` has just succeeded.

### The verification is the deliverable, and the first method was wrong

Index file mtimes show the two bursts and prove **nothing** about an
actively-written index, whose file carries a recent mtime whether or not
its contents were rebuilt. The exact test is `pg_class.relfilenode`
against `pg_class.oid`: a rebuild draws a fresh relfilenode from the
cluster-wide counter, so an index never rewritten since creation retains
`relfilenode = oid`. **0 of 125** collation-sensitive user indexes across
the eight databases retains its original; `projects`' 58 sit in one band,
3,882,764–3,886,294, against creation OIDs from 46,010.

"Collation-sensitive" is `indcollation NOT IN (0, 950, 951)` and is the
filter the entry lacked — `0` is not collatable, `950`/`951` are
`C`/`POSIX`, byte-order, immune to a glibc change. The entry's "25
indexes in the `sysadmin` schema, several on text" overstated it; the
live figures are 58 in `projects`, 125 cluster-wide, **0** in
`pg_catalog`.

### What was found by not stopping at the item the session came in for

`SNAG-ESTATE-008` was filed for one stale ops action and **measured at
three of three within the hour**. Every item in the block that opens
every sitting had already been carried out, and none by the party
recording it:

1. **The restart** — done 2026-08-16 12:06:09, **seven minutes after
   Session 55's own commit** (`a330e31`, 11:59). PID 1410826 →
   1914354, `POST /api/sysadmin/reload` returns 200 where the block said
   404, and `desktop_reminder_sweep` is live at `interval[0:03:00]`.
2. **The five system-scope orphans** — all absent, all `not-found`.
3. **`SNAG-DB-002`'s remedy** — estate-manager, 2026-08-13.

That reframes the snag from a cross-repo seam to **the absence of a
check**, and widens it usefully: two of the three were plain `systemctl`
state this service already reads every 300 seconds. The narrow framing
came from the first item measured happening to be the cross-repo one.

### Decisions taken

**No fix was built, and the snag says why.** Three candidates: widen
`EstateJudgeAgent` to `check == "collation"` (re-imports this service's
own alerts through a second producer — precisely what rule 3 prevents);
have a document check read the estate's audit (a new consumer of a
surface that may 500); or **give this repository's own resolve a
reader**, since the collation case generated the right signal already.
The third adds no cross-repo dependency and is the one to price first —
but each of the three items above had its evidence in a *different*
place, so the real shape is a convention (every ops action names the
check that closes it), not one query.

**`STATUS.md`'s block is now empty and says so as a measurement.**
"Nothing owed" and "nothing checked" must not render identically —
`UnitScanResponse.ports_checked`'s rule arriving in a document.

### Also corrected while in the files

`snag_list.md`'s header claimed `count_open_snags` reports 47 (measured
2026-08-14). Driven against the current parser it reports **35** — the
function was rewritten around `read_snags` since, returning a detected
format and a per-row `is_open`. The number went stale because the code
that measures it moved: `SNAG-ESTATE-008` in miniature, and the third
time that header has been wrong.

## Blocked / owed

**Nothing, and this is the first handoff able to say so.** Verified
2026-08-16/17, not carried forward:

- **The restart is done** — PID 1914354 since 2026-08-16 12:06:09;
  Sessions 49, 50, 52, 54 and 55 are all live in the running process.
  **The HUP warning now applies in reverse**: the daemon has the handler,
  so `kill -HUP <MainPID>` picks up a `config.yaml` edit, re-times the
  scheduler, and needs no `sudo`. Do not ask for another restart without
  re-measuring `MainPID` first — that is how the last one came to be
  requested after it had happened.
- **The five system-scope orphan removals are done** — files absent from
  `/etc/systemd/system`, all `not-found`.
- **`SNAG-DB-002`'s remedy is done** — estate-manager, 2026-08-13.

Still genuinely open, but neither is owed *to* anything: `SNAG-TRAY-008`
(a fault raised while the tray was up is never adopted by the
understudy, and a restart forgets what it spoke) and the two delegated
estate entries `SNAG-ESTATE-006`/`-007`, which need an estate-manager
sitting to record and are not this repository's to fix.

## Previous session — Session 55, the understudy gets a clock

Session 54's recommendation, taken as written. Suite **1854 passed**
(from 1834), ruff and mypy clean, **no migration**, **no route**, one new
config leaf and one new scheduled job. `SNAG-TRAY-007` is closed;
`SNAG-TRAY-008` and `SNAG-DOCS-001` were opened.

### What was decided, which was the deliverable

The snag refused a patch and asked for a precedence ruling. It came in
two halves, and the first is the one that would have been got wrong.

**`tray_grace_seconds` is the same window on both paths, and the action
differs.** The raise path *skips* — the tray is about to show this. The
repeat path **stamps the clock forward**, because a skip leaves
`last_spoken_at` at the opening notification, so the first sweep after a
tray outage restates a fault the tray itself restated ten minutes
earlier. Session 54's doubt — "the two answers are not obviously the
same" — was right. The difference is observable **only** in the middle
window, and the first draft of that test asserted the wrong arithmetic
and passed for the wrong reason until the middle step was made 12 hours
rather than 24.

**The sweep is a `JobSpec`, not a call at the end of
`SysAdminAgent._execute`.** The agent version is three lines cheaper and
makes an agent responsible for a lifecycle `monitor/desktop.py` owns —
the second-owner defect this repository has now found at five scales,
and the reason the snag refused a patch in the first place.

### Rejected, and why

- **A leaf for the sweep's interval.** It is `max(60,
  tray_grace_seconds)`. The sweep asks the two questions that window
  already answers ("is a reminder due", "is the tray still absent"), so
  a second number beside it would be invented rather than derived. The
  floor exists so a grace window tuned to a few seconds cannot turn a
  derivation into a hot loop.
- **A different `reminder_hours` for the daemon.** It is the tray's 24,
  for the tray's reason, and because two speakers with different
  cadences make the interval depend on which happened to be running —
  the thing the understudy exists to hide. A test pins the two equal.
- **Adopting every open row.** That is `SNAG-AGENT-005`'s unbounded
  `SELECT` wired to a notification each, and it announces every standing
  fault at once the moment the tray dies. Filed as `SNAG-TRAY-008` with
  the shape of a fix recorded — adopt only after a full `reminder_hours`
  of tray absence, capped the way `attention_max_rows` caps the estate
  judge — so it is not re-derived from scratch.

### Verified live, because the unit tests mock every session

The `title IN (:titles)` clause had never reached PostgreSQL. Against the
real `alerts` table: `_still_open` selected the live title and refused
one never raised; the sweep restated once and then held; a synthetic row
was inserted, restated inside a roll-up of 2, resolved, and dropped from
the spoken set; **residue 0** after rollback. Against a real
`BackgroundScheduler` and the real config.yaml: added at
`interval[0:03:00]`, re-apply retimed nothing, grace 600 retimed it to
`interval[0:10:00]`, `enabled: false` removed it.

### Found sideways — `SNAG-DOCS-001`, and it is the next session

While reading the live state for the ranking rather than trusting the
documents. `GET /openapi.json` serves **one** route under
`/api/projects`; `CLAUDE.md`'s Contract Registry lists **fifteen**, each
claiming `response_model` enforcement. `sysadmin/projects/` does not
exist — the domain left on 2026-08-13 — and five of its modules are
still named by path as the present-tense owners of rules the file
states. `api/projects` appears 26 times. The estate section of that same
file records the migration correctly, so the document simultaneously
says the domain left and describes it as present.

Also found stale while ranking: **Session 33's second checkbox** points
at `~/projects/alfred/backend/tests/fixtures/briefing_producers/`, which
does not exist on disk. That session is blocked on a question for
Alfred's repository, not on judgement here.

## Previous session — Session 54, the other three surfaces against data

Session 53's recommendation, taken as written. Suite **1834 passed**
(from 1802), ruff and mypy clean, **no migration**, **no route**, **no
config change**. Both code changes are in `sysadmin/estate/`, which the
daemon serves from its start-time copy, so they deploy on the restart
already owed — no new blocker.

### The method, and where it is weaker than Session 52's

Session 52 forced two thresholds and pushed 26 real snapshots through
the producer; its fixture is an observation. The unhappy states on these
three surfaces have **never occurred** — 0 of 7 `scan_runs` and 0 of 22
`audit_runs` carry an error, no `ports` finding has ever reached
`breach`, the queue has never had a waiter — so the *rows* here are
synthetic and the fixtures say so. What is borrowed is everything
downstream: the ORM models (which reject a shape the estate cannot
store), `scan_invariants`, `audit_invariants`, `findings` including its
`_streak_starts` age walk, `CheckResult.as_summary`, `Arbiter.invariants`
and `api._public`. Run in estate-manager's venv against the live `estate`
database inside transactions that were rolled back; verified afterwards
at 7 / 22 / 92 rows unchanged.

The port breaches are not synthetic at all: real listeners on 3900–3905,
inside the registry's own audited range, through the estate's
`ports.run_check` against the real `monitorable-project.md`. Session
26b-A's method, which is why `detail['port']` and `fingerprint` in the
fixture are the producer's spelling rather than a guess at it.

### The finding, which is exactly what the framing predicted

Every rule was pinned one condition at a time, because a keyword
override to `_scan(...)` produces one condition. **The producer cannot
separate them.** `ScanOutcome.estate_written` starts `False` and is set
near the end of a run, so every failing scan carries `error` *and*
`estate_written: False` — and the judge raised two rows for one fault,
the second reading *"The last project scan completed without rewriting
estate.json"* of a scan that did not complete. One toast, once, before
Session 53; a false sentence restated every 24 hours after it. That is
the whole argument for the promotion, arriving as data.

The `estate_written` rule is now narrowed to a scan that did not error,
which makes the two mutually exclusive by construction —
`failures.py`/`stalls.py`'s shape, one domain over. **Not deleted**: a
scan that completed and skipped the write is the case its message
actually describes, and a test pins both sides.

### A second defect, fixed because it is invisible either way

`EstateJudgeAgent._execute` read `open_titles` once and never updated it,
so two judgements sharing a title in one run insert two rows and
deduplicate only from the second run onwards. Reachable through
`judge_audit_findings` rule 4, which keeps the finding's `code` out of
the title *on purpose* — two `breach` codes for one port are two findings
and one row. Unreachable on today's estate; pinned because a run that
raises twice looks exactly like one that raises once until somebody
counts the rows.

### Decisions taken, and what each rejected

- **The `estate_written` guard keys on `error`, not on a merged
  family.** Rejected: folding the two rules into one row with a longer
  message, which loses the distinction between "the scan broke" and "the
  scan ran and skipped its output contract" — different remedies, and
  the second is the case the wording was written for.
- **`SNAG-ESTATE-006` is delegated, not worked around.** The producer's
  `code` is recoverable from `fingerprint`'s last `:` segment, and
  parsing it here is this repository building a format the estate owns —
  `_port_of`'s rule 3 one field over. `judge_audit_findings` goes on
  reading `code`, so the producer's fix lands with no change here, and a
  test asserts the **absence** so the day it lands the suite says so.
- **Two rules recorded as unreachable rather than deleted.** The scan's
  `finished_at is None` (the row is written once, *after* the scan, so a
  mid-flight death writes no row and surfaces as staleness) and the
  audit's `error` (`_record` builds `AuditRun` with no `error=`).
  Rejected: removing them, which leaves nothing to notice that they
  went; their columns are nullable and the producer may yet fill them.
  Both are now named in the docstrings so their silence is not read as
  health.
- **The fixtures are scenario-keyed with a `_provenance` block**, and a
  test fails if a re-capture drops it. JSON carries no comment and these
  rows are synthetic; the block is what stops a hand-edit passing for an
  observation.

### Also corrected

`1 data sources were unreachable`, in a message that reaches a
notification body verbatim. And a `"code"` key an existing agent-test
literal had invented — the same defect this session was about, sitting
in the fixtures rather than the code.

### Verified live, as this family always is

The whole agent path against the real database in a rolled-back
transaction: raise 7 → hold (0 raised, 0 resolved — dedup holding) →
resolve 7, **0 rows of residue**, and the failed-scan payload producing
one row where it used to produce two.

### Two gaps filed rather than assumed settled

- **`SNAG-ESTATE-006`** — the audit publishes no finding `code`, so
  `details['code']` is `None` on every payload the estate can serve.
- **`SNAG-ESTATE-007`** — the arbiter's pool omits the `-c timezone=utc`
  its sibling engine sets and documents, so `active_lease` stamps render
  `+01:00` against three sibling surfaces' `+00:00`.

Both are delegated and **neither has a counterpart entry in
estate-manager yet**; recording them there is a cross-repo write,
committed on its own and announced, and is not a sysadmin session.

### State of the box, measured at the close

The tray restart owed since Session 53 is **done** (2026-08-16 10:29
BST), so `reminder_hours` is live. `sudo systemctl restart
sysadmin.service` is **still owed** — PID 1410826 from 2026-08-15 14:32
BST, `POST /api/sysadmin/reload` still 404s — and now carries Sessions 52
and 54 both. Two unresolved alert rows on the whole box: a new
`High VRAM usage on AMD Radeon RX 7900 XTX` (10:17 today) and
`Unmonitored systemd units: 8 findings`, open since 2026-08-15 14:33.

---

## Previous session — Session 53, a fault that stands keeps speaking

`SNAG-ESTATE-003`. Suite **1802 passed** (from 1792), ruff and mypy
clean, **no migration**, **no route**, and **no backend behaviour
change** — the fix is entirely in `sysadmin_tray/`, so it deploys on
`systemctl --user restart sysadmin-tray.service`, which needs no `sudo`.

### The finding, which came before the fix

The entry asked for "a third rung, or a `warning`-that-repeats mechanism
that is not `critical`", and STATUS.md sharpened that to *a third rung in
`sysadmin/core/escalation.py` with three callers*. **That rung cannot be
heard.** `NotificationPolicy.fingerprint` is `{severity}:{title}` and
`_FingerprintState.notified_this_episode` clears only when that pair is
absent from a poll — which a resolve-and-re-raise inside one agent run
never produces, since the tray sees only unresolved rows and the swap
happens between two of them.

Driven against the real policy rather than reasoned about:

| what the daemon writes | what the desktop does |
|---|---|
| same row, standing | speaks once, then silent (today) |
| resolved row → **fresh row, new message** | **nothing at all** |
| escalated to `critical` | speaks |
| same severity, **forked title** | speaks |

Two audible repeats, and a forked title is forbidden by four separate
rules here — the title is the identity key for dedup, for the resolve
and for the tray. So there is nothing for a third rung to be heard by.

### What was built instead

A repeat at an unchanged severity is a **notification** decision, so it
went where notification policy already lives: `reminder_hours` in
`sysadmin_tray/notifications.py`. It covers **every** deduplicating
family, not the estate's five surfaces — which matters, because
`estate_judge` has produced two rows in its life (both resolved) while
the live instance was `service_discovery`'s `Unmonitored systemd units:
8 findings`, the only unresolved row on the box, open 24 hours and
spoken once.

### Decisions taken, and what each rejected

- **24 hours is derived, not picked.** It matches
  `self_monitor.escalate_after_hours`, the only escalation gap on this
  box, so a family that owns a ladder escalates to a *different*
  fingerprint — a new episode, spoken at once — before any reminder of
  its quiet rung falls due. Rejected: a shorter interval, which makes the
  reminder the first thing you hear twice and demotes the loud rung from
  news to repetition.
- **The clock runs from when the tray last spoke**, not from
  `alert.created_at`. `stalls.py`'s rule — the thing that failed was the
  *telling* — and it keeps the single injected clock that makes every
  window in that module testable without sleeping. Rejected: the row's
  own age, which needs a second, uninjected wall clock.
- **Reminders fold apart from new alerts**, into `FP_REMINDER` with
  their own wording. Rejected: reusing `FP_COALESCED`, which would report
  a fault announced yesterday under a heading reading "N new alerts".
- **`humanise_hours` is imported from `sysadmin.core.escalation`** rather
  than re-worded locally, so the reminder says "still open 1 day" in the
  same words the stall escalation says "still stalled 1 day". Precedent:
  the tray already imports `format_mb` from `sysadmin.files.forecast` for
  exactly this reason, and that helper's own docstring asks for it.

### The defect the fixtures could not have caught

`state.first_notified_at or state.last_notified_at` reads a monotonic
clock reading of exactly `0.0` as absent and falls back to the field
every reminder resets — so each reminder reported the **interval** ("24
hours") rather than the **age** of a fault standing three days. Every
existing fixture uses `FakeClock`, which starts at `1000.0`. Found by a
probe whose clock starts at zero; the regression test now does too.

### Stated limits, not discovered later

- `digest_mode` never reminds below `critical`: that mode's contract is
  that warnings do not interrupt. Making the digest itself periodic is a
  separate question about a mode that is `false` here.
- Policy state is in memory, so a tray restart re-announces every open
  fault as new and restarts the cadence.
- **`SNAG-TRAY-007`** — `monitor/desktop.py`, the understudy that speaks
  when the tray is down, is event-driven off `alert.raised` and shares
  none of this. Not patched: a reminder there is a second owner of a
  lifecycle the tray holds whenever it is up, so it needs a precedence
  decision (`tray_grace_seconds` answers it for the raise path and would
  have to answer it for the repeat path), not a copy.

### Two docstrings corrected, because their premise had moved

`sysadmin/estate/agent.py` and `sysadmin/core/escalation.py` both said
the omission was deliberate and named `critical` as the obstacle. Both
now record that the alternative was **measured and refused**, and say not
to re-derive it — the failure mode this repository has already filed once
(SNAG-AGENT-006's "a correct conclusion drawn from a premise that has
since moved").
