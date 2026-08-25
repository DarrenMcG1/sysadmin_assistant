# Handoff — 2026-08-25

## Next action

Close `SNAG-DOCS-004` by rewording the two sibling docstrings in `log_review.build_review_prompt` and `files/review.build_review_prompt` to the narrow claim Session 79 already stated correctly in `health_review` — no digit reaches the prompt *from the data* — and move `tests/test_health_review.py::TestPromptIsFigureFree`'s partition helper somewhere all three test modules can share it, because it is the same one-rule-stated-three-ways shape Session 80 has just spent itself removing from a database column and the pin that makes it checkable already exists.

## Session 80 is complete, and the entry it closed understated its own population by two

`SNAG-API-004` is **fixed**. `status != "ok"` was written in four readers
of `service_health.status` and was wrong in three of them from the day
migration 009 added `skipped` to `chk_health_status`. The snag named one
route and recommended an audit; the audit is the whole of what mattered.

- `GET /api/sysadmin/status` — the route the entry names
- `GET /api/summary` — the identical phrasing, never named by anyone
- `GET /api/projects/managed` — **the sharpest, and the only one not
  masked.** Measured 2026-08-25 it reported `venture-assistant` and
  `sysadmin_assistant` unhealthy with every real service `ok`

The two the entry reasoned about were both false-for-the-right-reason on
the day it was written, because something was genuinely down. The one it
never looked for was wrong on the page. Reading the code would have found
the phrasing; only running the three routes ranked them.

`STATUS_READINGS` on `monitor/models/service_health.py` is the one
statement now — all seven admitted values classified `well`/`fault`/
`unwatched`, read through `is_fault()`/`is_unwatched()`, and asserted
**exactly total** over the CHECK constraint's own `sqltext` rather than
over a list re-typed beside it. Suite **2362 → 2388**, routes unmoved at
51, head unmoved at 016.

## What was decided, and why

**`reliability.py` is pinned rather than imported.** Its docstring
promises purity ("no DB access, no FastAPI") and the vocabulary's owner
is an ORM model, so importing would have bought one-statement-of-a-fact
at the price of a property the module advertises. A round-trip test
drives both sides against the constraint instead — `syslog_priority`
against `journal.PRIORITY_MAP`. It also stopped negating `ok`:
`DOWN_STATUSES` names the four measured faults positively, which changes
no number today and changes the failure mode.

**A missing health row is deliberately still not healthy.** On
`/api/projects/managed` a `skipped` row is a recorded decision not to
look and an absent row is nobody having decided anything, so the fix was
not generalised to absence. Empty population today, pinned by a test.

**Rejected**: adding `SKIPPED` to each of the three comparisons. Three
copies of one rule agreeing is what the last two sittings shipped, and it
is why this was the third instance.

## Two things the sitting found that no reading would have

**The suite was green either side of all three defects.** The tests
covered a healthy box and an unhealthy one and never a healthy box with a
declaration on it, and `/api/projects/managed` had **no test at all** —
which is exactly why its version of the defect was the visible one. Every
route now carries three cases, and all were falsified against the pre-fix
code.

**One falsification passed against deliberately broken code.** `assert
SERVICES_SKIPPED is SKIPPED` was meant to prove `services.py` re-exports
the literal rather than restating it, and CPython interns short string
literals, so it is True either way — a guard asserting a *value* where it
means *provenance*, for the third time in this repository. It is an AST
check now and was re-falsified.

## Verified live, and the counterfactual is what proves it

`/api/sysadmin/status` still reads `False` today and correctly:
`alfred-frontend` is genuinely unreachable, which is the masking the
entry describes. So the fix was driven over the live row set with that
one service removed — old `all(status == "ok")` → `False`, new
`not any(is_fault(...))` → `True`, across 29 services of which 3 are
declared. Over real HTTP after the restart, `/api/projects/managed` moved
two projects `False` → `True` with their `skipped` rows still in the
grid, and `Alfred` stayed `False` on the genuine outage.

The daemon was restarted at **15:59:58** and `./scripts/check-ops-claims.sh`
reports every claim in STATUS.md green.

## What opened, and the answer that was worth measuring

`SNAG-DB-006`: `chk_run_status` admits `cancelled` and **nothing has ever
written one** — 34,362 `completed`, 5 `running`, 2 `failed`, 0
`cancelled`. Found while pricing this handoff rather than while building:
the audit was extended one column over to see whether the defect
repeated, and **it does not**. `self_monitor._failure_streak` is written
positively, so an unexpected value ends a streak rather than being
charged as a failure — the allow-list shape, and a property of how that
function happens to be written rather than a guarantee. A recommendation
that says "I checked and there is nothing there" is what Session 78's
hypothesis cost Session 79 to establish.

## Ranked, if the next action is not taken

1. `SNAG-DOCS-004` (P3) — the next action above. Cheap, and closes a
   false sentence three modules rest on
2. `SNAG-DOCS-003` — remove `sysadmin_tray/_deprecated_contracts.py`.
   Named by Session 77's fix; it is a change to a published surface, so
   it wants a sitting of its own
3. `SNAG-DB-006` (P3) — needs a decision rather than a fix: drop
   `cancelled` from the constraint, or find the path that should write
   it. A run killed mid-execute leaves a permanent `running` row
   (Session 41's stated cost), and `cancelled` is plausibly what that row
   was meant to carry. Those are opposite fixes and nothing records which
   was intended
