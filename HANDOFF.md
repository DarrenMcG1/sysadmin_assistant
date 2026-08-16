# Handoff — 2026-08-16

## Next action

Take `SNAG-TRAY-007` and decide how `sysadmin/monitor/desktop.py` restates a standing fault while the tray is down, because Sessions 39, 53 and 54 have closed that arc everywhere except the one component that exists for the case where the tray is not running.

## This session — Session 54, the other three surfaces against data

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
