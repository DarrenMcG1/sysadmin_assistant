# Insights — Session 35 (the project registry)

**Date:** 2026-08-08
**Scope:** phases 0–6, plus installing the organiser timer

---

## Silence is the failure mode this session kept finding

Three defects, one shape. A dead `projects.yaml` path matched nothing and
returned nothing, which is exactly what an absent project looks like. A
`kind: timer` check read properties `get_unit_status` never requested and
returned `ok` with an empty last-run, which is exactly what a timer with
nothing to report looks like. A `project:` id emitted by the unit sweep
would have named a directory instead of a manifest and produced a snippet
that fails on paste — worse than offering no snippet.

None of them raised anything. The fix in each case was **to give the
failure somewhere loud to land**: an unknown id stops the service at
startup, listing every bad reference at once. That is why keying on ids
rather than paths is the point of the whole exercise, not a tidiness
preference.

**Rule to carry forward:** when adding a lookup, ask what happens when it
matches nothing. If the answer is "the same as a legitimate empty
result", it needs a distinct outcome before it ships.

## The mock was acting as the specification

`kind: timer` shipped inert in Phase 3 and passed its unit tests. Those
tests mock `get_unit_status` and hand it exactly the properties the
assertions expect — so the mock encoded the contract, and the real
function had never been asked whether it met it.

The replacement test asserts the **coupling**: every property
`_timer_facts` reads must appear in `get_unit_status`'s request list. It
needs no live systemd and it checks the thing that was actually wrong.

**Rule to carry forward:** when a test mocks the collaborator whose
agreement is the risk, it is testing the mock. Assert the agreement
separately.

## Verify a derived rule against data somebody wrote by hand

The `last_code_commit` ignore rule could have been declared correct on
inspection. Instead it was checked against the "last code" dates recorded
by hand in `projects.yaml`'s comments months earlier — daiy 2026-02-06,
terrible 2026-03-25, BudgetApp 2025-05-14, SportsAnalyser 2026-03-23,
portfolionew never. All five matched.

That check also caught the rule being **wrong as briefed**: the seed
named one estate-wide sweep, and a second — newer — one shadowed it, so
eleven projects would have kept reading as touched last week. A rule that
"looks right" and a rule that reproduces known-good answers are different
claims.

## Derived identity must not be resolvable

Undeclared repositories get a provisional id for display and it never
enters the id map. This was load-bearing on day one: `apps/BSL-Translator`
and `archive/bsl-translator` derive the same id, as do `archive/Portfolio`
and `archive/portfolio` — two directories differing only in case. Had
derived ids been resolvable, the registry would have refused to load an
estate where nobody had done anything wrong.

The general form: a value the system invents to fill a gap must not be
usable as though the gap were filled.

## An absent decision is not a decision

`undeclared` had to be added as a real status because the old default —
absent means active — made "nobody has decided" indistinguishable from
"being worked on", and showed eighteen board rows for a five-project
estate. It is scored exactly like `active` (nobody said the project was
resting) but counted separately, so the gap is visible rather than
resolved by assumption.

## Tooling trap

`uv sync` without `--all-extras` removes the dev extras. `uv run pytest`
then silently falls back to `/usr/bin/pytest`, and the suite runs against
system Python with none of the project's dependencies. It presents as
`ModuleNotFoundError: pythonjsonlogger` — which reads like a broken
dependency rather than a broken environment, and cost about ten minutes.
Check `uv run which pytest` when an import fails for no reason.
