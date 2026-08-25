# Handoff — 2026-08-25

## Next action

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
