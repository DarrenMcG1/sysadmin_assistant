# Handoff — 2026-08-17

## Next action

Take `SNAG-DOCS-001` and move `CLAUDE.md`'s fifteen project-endpoint contracts and five `sysadmin/projects/*` narratives behind pointers to estate-manager, because the file loaded into context at the start of every session describes a domain that left this repository on 2026-08-13 — and the argument that displaced it twice, that a detector's first live data beats the document backlog, is now spent with all five estate surfaces driven against real payloads.

## This session — Session 57, the holder decides how loud

**Not the recommendation**, and the second consecutive sitting to
displace `SNAG-DOCS-001`. The reason was live and time-limited: the
ports family produced its first rows ever on 2026-08-16 12:07, one
minute after the daemon last entered active, and Sessions 52 and 54 had
each found a real defect on a detector's first data. This makes three
for three.

### What was open, and why the remedy did not apply

`Estate port 3110` and `Estate port 8110`, both `warning`, both
standing. Both listeners are Alfred dev servers launched from VS Code —
`nuxt dev` and `uvicorn --reload`, all three pids in
`app-code-oss-26348.scope`. The estate's finding is **literally
correct**: no registry row claims either port. Its remedy is the half
that does not apply, because an editor's dev server is not a service the
next project could collide with and it leaves when the window closes.

### The defect was not a missing signal

`Listener.transient` has named these listeners since Session 26c. The
signal was collected, named, and then dropped twice over:
`PortReport.unit_ports` skips `attributed and transient` for
`recommendations.py`'s correct reason (a session scope is nobody's
service, and a `kind: http` snippet for one would invent a service), and
`unattributed_ports` never held them because a session scope *is*
attributed. The port fell out of the stored blob **entirely** — measured
on the real 2026-08-17 output, `unattributed_ports` came back `[]` — so
`details['holder']` was `None` and indistinguishable from 5432's genuine
unattributability. `ports_checked`'s rule one layer down.

### Decisions taken, and what was rejected

**Quietened, never suppressed.** `TRANSIENT_HOLDER_SEVERITY = "info"`.
Dropping the row was the obvious implementation and was rejected because
it rebuilds this family's founding defect — Session 26b-A exists because
a ports breach was detected, correct, machine-readable and never said
out loud — with the additional property that nothing records the
decision, which is `SNAG-CFG-001`'s shape. The rung is **derived**: it
is the only one below `tray.notify_min_severity` on this box, guarded by
a test that reads the live `config.yaml`.

**A separate blob key, not a flag inside `unit_ports`.** One field whose
two consumers want opposite safe defaults is Session 48's
`UnitFinding.enabled` trap; this is the same shape caught before
shipping rather than after.

**Rejected — running `ss` inside the judge** to close the sweep-window
gap. `EstateJudgeAgent._attribution` refuses it in writing: two calls at
two moments give two answers to one question with neither surface saying
which it used. **Rejected — an hourly sweep**, which narrows the same
gap with one config line and pays six times the sweep cost across every
consumer of `unit_ports` for one annotation. Filed as
`SNAG-ESTATE-009` instead.

### Blocked, and deliberately not fixed here

**The two rows standing today stay `warning`.** The agent deduplicates
on title, so a judgement that is now `info` is skipped while a `warning`
row with that title is open. They quieten on their next full cycle —
editor closes, rows resolve, editor opens, rows re-raise at `info`. A
de-escalation path (resolve the loud row, raise the quiet one) is the
inverse of `core/escalation.py`'s ladder, which `step_for` explicitly
refuses in that direction, and it is a design question rather than this
session's.

**Nothing is live until the daemon restarts.** Both halves are code, not
config, so `SIGHUP` does not deliver them. Order matters: restart, then
let `service_discovery` write a sweep carrying `transient_ports`, and
only then resolve the two standing rows — resolving them before the
sweep lands re-raises them at `warning`.

### Verified live, in-process

The real `ss` (37 listeners; the editor scope holds 7 ports, of which
only 3110 and 8110 are inside the audited ranges), the real
`:8400/api/audit/findings` (2 breaches plus the standing 3300 `warn`,
still correctly not judged), and the same two rows coming out `info`
with `holder=app-code-oss-26348.scope` where they came out `warning`
with `holder=None`.

Also measured while ranking: the estate's `count_open_snags` reports
**35 at HEAD → 36 now**, while `GET :8400/api/projects/board` said
**34** at the same moment, because a board row is a stored snapshot that
had not seen the last commit. The rule about not trusting a document's
summary of itself applies to the API that would correct it.

12 new tests (5 in `test_unit_ports.py` driving `ss` output → blob →
attribution end to end, 7 in `test_estate_judgements.py`). 1866 green,
ruff and mypy clean.
