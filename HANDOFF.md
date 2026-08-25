# Handoff — 2026-08-25

## Next action

Fix `SNAG-API-004` — `GET /api/sysadmin/status` computes `all_healthy` as `all(r.status == "ok")`, which reads false on every healthy day because three services are declared `monitor: false` and stored as `skipped` — and audit the remaining readers of `service_health.status` in the same pass, because this is the third instance of that defect in one column and the first two were each fixed only where they were noticed.

## Session 25 is complete, and the number its last tier nearly published was off by three orders of magnitude

Tier 3 shipped as `GET /api/sysadmin/review` —
`sysadmin/monitor/health_review.py`, `health_reviews` (migration 016),
`HealthReviewResponse`, a Monday 05:00 job and a "Weekly System Health
Review" briefing section. 63 new tests, suite **2,299 → 2,362**, routes
**49 → 51**, head **015 → 016**. All four named inputs built: flappiest
services, alert volume delta, anomaly summary, resource trend direction.
Session 25 has been two-thirds done since 2026-08-07 and is now closed.

**The alert delta counts distinct titles, not rows, and the difference is
2,485x against 2.3x.** Across the two live comparison windows `alerts`
holds **24 rows against 59,650** — of which **59,200 share one title**
and fell on a single day — and **17 distinct titles against 39**. This
repository has written that its `alerts` table records one row *per
failed check* four separate times and had never applied it to a *count*
of alerts, because nothing counted them until now. Rows stay in `stats`
as evidence; no sentence is written from them.

**A fall is refused when the monitor's own coverage fell.** The two
windows were observed at **17.01 %** and **96.33 %** of expected agent
runs, so an unqualified headline would have described a box that was
merely switched off. This is `log_review.direction_phrase`'s asymmetry
against a different mechanism — read truncation there, monitor downtime
here, both able to hide a fault and neither able to invent one. Both
windows are measured, because checking only the current one reports poor
coverage on this box and still lets every delta through.

## What was decided, and by whom

The three design calls were put to the owner before any code was written
and all three recommendations were taken: the route under
`/api/sysadmin` rather than `/api/services` (so the GET-only guard
beneath `/api/services` is not narrowed to admit the route being added),
the resource half narrating CPU/RAM/swap/load with **disk deferred by
name** to `GET /api/files/review`, and the coverage question answered
with a refusal phrase rather than a suppression gate.

## Three defects only the live run found

Handed "The monitor was down for much of this period", dria-agent-a-3b
published **"The machine was down for much of the week"** — the exact
inversion the rule exists to prevent. It also opened with a
conversational preamble `strip_markdown` would not have removed, since
that function strips formatting rather than prose. And the prompt's first
draft named only `unreliable`/`failing` services, so it dropped `searxng`
and `alfred-frontend` — both degraded with real outages — at the moment
`venture-chat` went unreliable. All three fixed and re-driven live.

**Nine falsifications were driven and one guard passed against the code
it was written to break**: it asserted a string absent from both the
pre-fix and the fixed wording, testing the model's output through a
fixture that never contains it. Session 78's `waived`/cadence shape a
third time, repaired to assert the property that actually distinguishes
the two wordings.

## What the docs did not know

**The `skipped` audit Session 78 recommended on a hypothesis has a
measured population, and it is not empty.** Pricing that recommendation
honestly meant measuring it: `GET /api/sysadmin/status` reads
`all_healthy = all(r.status == "ok")` and `briefing/data.py` fixed the
identical defect one router over, with a comment explaining why. That is
the third instance in one column and the reason it is ranked first.

**05:30 is not a free Monday slot**, though `jobs.py`'s own comment
implies the estate's review holds it elsewhere.
`systemctl --user cat estate-manager-review.timer` reads
`OnCalendar=Mon *-*-* 05:30:00` on this box — another repository's
llama-server generation on the same 24 GB card — so the chain grew at the
front to 05:00 rather than filling a gap that was not there.

**The card was at 98 % against a 25 % threshold** when the first live
generation ran, so the review was written by its deterministic fallback.
The ADR-0004 idle-gate working as designed, and worth knowing: four Tier
3-class generations now compete for one card inside a 45-minute Monday
window and nothing measures how often the gate declines.

## Three snags opened, none closed

`SNAG-API-004` (P2, the `all_healthy` blind spot), `SNAG-CFG-002` (P3,
two schedule leaves parsed and read by nothing since ADR-0005) and
`SNAG-DOCS-004` (P3, two Tier 3 docstrings claiming their prompt carries
no digit when both do). Parser measured either side: **63 → 66 entries,
28 → 31 open**. Two of the three were found while *not* building — one
while ranking the next session, one while looking for a free slot.

## The state of the box

Restarted 13:11:35, schema at 016, `/health` 200, all nine ops claims
`ok`. Three unresolved alert rows, all named in STATUS.md.

---


## Next action (Session 78's, superseded)

Build Session 25's Tier 3 as the weekly system health review — flappiest services, alert volume delta, anomaly summary and resource trend direction — reading `GET /api/services/actions` for the first of those now that Tier 2 exists, and mirroring `disk_reviews`/`log_reviews` rather than the `project_reviews` table its written design names, which migration 014 dropped on 2026-08-24.

## The endpoint found the score it reads to be wrong, and that is the sitting

Tier 2 shipped as `GET /api/services/actions` —
`sysadmin/monitor/service_recommendations.py`, `ServiceRecommendationInfo`,
`ServiceActionsConfig`, 61 new tests, suite **2,238 → 2,299**, routes
**48 → 49**, head **014 → 015**. Live on first run it served **6 rows and
213 recoverable points**; after the fix below it serves **3 and 33**.

**Three of those six rows were false and all three were `risk`.**
`services.yaml` declares `monitor: false` on `venture-chat-large`,
`sysadmin-tray` and `searxng-upstream` — all inactive by design — and the
agent stores those checks as `skipped`. `score_service` excluded only
`error` from its rates, so a `skipped` row counted as
measured-and-not-`ok`: each scored **35** and graded `failing` off 307
checks nobody had taken. That has been true since Session 25 on
2026-08-07 and nothing noticed, because **a wrong score is a number on a
page**. Tier 2 turned each into a 60-point `risk` recommendation, which
is what made it loud enough to find. `failing` 3 → 0, mean score
92.1 → 98.6.

**The fix was not the sibling rule, and importing it would have been just
as wrong in the other direction.** `_resolve_recovered` reads `skipped`
as *healthy* — correctly, for alert closure — and that fabricates a 100
here exactly as scoring it down fabricated a 35. `skipped` joins `error`
in `UNMEASURED_STATUSES`, counted apart as `skipped_checks` (migration
015) because "the check failed" and "nobody looked, by choice" are
different claims with opposite remedies.

**The whole suite passed either side of that fix**, which is the finding
under the finding: nothing pinned the behaviour in *either* direction.

## What was decided, and by whom

The three design calls were put to the owner before any code was written.
**Asymmetric confidence gate** and **forecast-framed `recoverable_points`**
were the recommendations and were taken. On the third — `tasks.md`'s two
scoped examples, both of which look like rules this repository would
refuse — the concern was raised, the request was **reaffirmed as written**,
and both were built with the conflicts filed rather than decided:
`SNAG-SVC-001` (a longer check interval is a fault seen less often) and
`SNAG-SVC-002` (`timer_stale` asks `stalls.py`'s question about a
different subject). Neither is this repository's to settle alone.

## Two things measured that the documents did not know

**`SNAG-ROADMAP-002` is fixed, by estate-manager, at 09:12:22 this
morning** — an hour into this sitting, as their `SNAG-ESTATE-048`.
`read_snags` now reads an entry's own closure marker. Verified here by
driving the new parser rather than by being told: every known-fixed entry
reads `is_open=False`, every known-open one `True`, and the open count for
`snag_list.md` drops **59 → 27** on a document nobody had edited. Nine
sittings of owed report retired without being written, and the entry's
own two proposed fixes were both parser-*shape* fixes that would not have
helped — the miscount was that a closure this document states in prose had
no machine-readable form, and the owner added the form.

**The 7-day window currently holds a six-day hole and every service reads
`confidence: low`.** The box was powered off 2026-08-18 08:09 → 08-22
18:10, and `SNAG-DB-005` kept the daemon dead a further 22 hours on
08-23. Both are the *monitor* being down, so `reliability.py` correctly
charges nothing for it — but it means the endpoint would have shipped a
measured-empty population under the obvious confidence gate, which is why
the gate is asymmetric. Coverage should cross 50 % around 2026-08-28 and
the rate-argued rows begin appearing then; nothing needs doing.

## Sub-session items

**One is owed, and it is a cross-repo ask rather than a session.** Ask
estate-manager the **Session 33 question** — seam drift detection's second
task reads another repository's fixture off the same disk, and cross-repo
concerns have had an owner since 2026-08-13. Now unasked for **seven**
consecutive rankings, and it is the reason Session 33 cannot be ranked at
all. Committed on its own and announced, per the estate rules.

**Not owed, and not this repository's.** `High VRAM usage on AMD Radeon
RX 7900 XTX` opened at 10:08 today and was still true at the close —
23,114 MB of 24,560 (94.1 %), `gpu_percent` 100, 340 W. Four services
share that one card and this repository monitors it without owning
anything on it, so attributing the hold is estate-manager's arbitration
question, not a monitoring change here. Named rather than left in a count.

## What was deliberately not done

**The stored `reliability_scores` history was not recomputed.** Every
nightly snapshot since 2026-08-07 holds a 35 for those three services. A
migration that corrected them would invent measurements never taken, so
the rows stand and migration 015's docstring says why. Whether that is
right is a decision for a later sitting, and it is ranked second on the
board as part of auditing the other readers of `service_health.status`
for the same `skipped` blind spot — `_resolve_recovered` is known
correct, the anomaly path and the briefing's `facts` projection are
unexamined.

**`sysadmin/services/` is gone, and it went by accident.** The modules it
held moved to `sysadmin/monitor/` in Session 35 Phase 2, leaving an empty
untracked directory that git did not know about — it is why the first two
commands of this sitting failed while locating `reliability.py`. It was
removed mid-sitting as a side effect of a `git stash push
--include-untracked` / `pop` round-trip run to diff test counts, because
git does not restore empty directories. Nothing referenced it and nothing
broke; recorded because an unintended deletion should be stated even when
it is the outcome someone would have chosen.

*Two claims in earlier drafts of this paragraph were wrong and are
corrected here rather than quietly dropped*, since both are the failure
this sitting spent itself on. It claimed `CLAUDE.md` points at
`sysadmin/services/reliability.py` — it does not; every
`/api/services/…` string in that file is a route path. And it claimed the
directory still existed — it did not, by then. Both were inferred rather
than measured.

**One file was clobbered and restored.** `tests/test_service_actions.py`
already existed, covering `POST /api/sysadmin/services/{name}/{action}`,
and was overwritten by a `cat >` before the collision was noticed. It was
restored from `HEAD` intact and the new tests went to
`tests/test_service_recommendations.py`; the module was renamed to match.
The way it surfaced is worth keeping: the suite total came out **+45**
where 55 tests had been added, and the ten missing were the ten
destroyed. An arithmetic check on a number nobody had asked for is what
caught it.
