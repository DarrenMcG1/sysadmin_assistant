# File organiser — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

The weekly disk review is **figure-free by construction**, not by
instruction, and uses `strip_markdown` from `sysadmin/core/text.py` —
which now re-exports `estate.text`, the mechanism having gone to the
library when the project review that shared it left. It lived in `core`
because neither domain could import the other; it stays there because the
signature stayed and every importer here is unchanged.

`GET /api/files/actions` was built as the file-organiser mirror of
`/api/projects/actions` — estate-manager's route since 2026-08-13 — with
one deliberate difference: its currency is
**reclaimable megabytes**, not health-score points, so it uses its own
`FileRecommendationInfo` rather than reusing `RecommendationInfo` — one
`points` field meaning two units decided by the producer would be unreadable
at the call site. Only duplicates, old downloads, stale caches and rebuildable
dependency directories price above 0.0 MB; tidiness items (misplaced files,
empty dirs, similar folders) rank by `item_count` beneath them. It is the only
`/api/files/*` route that reads `resource_snapshots`: disk **occupancy** is
what answers "when does the disk fill up", and a projected 80 %/90 % crossing
inside 30 days outranks every byte total. Counts come from the audit row's
columns, never from `findings` — the findings lists are truncated to 50–100
entries before storage, so sizes summed from them are a lower bound and say so.

**The occupancy fit is two fits, and the short one may only add urgency**
(Session 307, 2026-10-01). One least-squares line over 30 days stays flat
for a month after a big cleanup: usage fell 94.8 % → 61.5 % on 2026-07-27,
the 30-day slope stayed negative until 08-23, and usage was back past 80 %
on 08-31. `project_disk_thresholds` therefore also fits the last
`SECONDARY_WINDOW_DAYS` (7) and, per threshold, keeps the sooner projected
crossing. The asymmetry is the design: a short fit is the noisier one, so it
may bring a date forward and never push one back or turn a crossing into
`not_growing` — a quiet week must not hide a month's growth. Its cost is
over-urgency after a step: replayed, it read "80 % in 1 day" on 18–22 August
while usage sat at 77.4 %, and raised one spurious risk on 08-03 from the
rebound after the cleanup. Three days was rejected because its slope swings
by several pp/day on one download. The short fit is skipped when the series
spans under twice the window, which is why the weekly review — fitted over
its own 7-day period — is unchanged. A date the short fit decided carries
`window_days`, and the tray and the risk item say "last 7 days" so they do not
contradict the whole-series Growth rate beside them; `DiskThresholdInfo` on
the route was deliberately not widened.

**A fitted line already past a threshold the latest reading has not reached
is a crossing due now** (Session 340, 2026-10-04, `SNAG-FILES-001`). It is
reported `projected` with `days_from_now=0.0` and the latest sample's date,
never `not_growing`, which every reader takes to mean no crossing at all.
There is no fourth state because every reader already handles `projected`,
and `most_urgent_projection` ranks day 0 first without being told to.
Replayed, the whole-series fit took this case on five consecutive days
before 80 % was crossed on 2026-08-31, and until the fix it reported
"90 % in 18 days" on each of them. The short fit makes the case commoner,
because a step up inside its week lifts its line above the latest reading.

**The reclaimable-milestone forecast on `/api/files/trends` follows the same
rule** (Session 341, 2026-10-04). `_compute_reclaimable_forecast` in
`router.py` used to drop a milestone its fitted line had already passed.
It now dates the milestone at the latest scan. The case was measured
before the fix and never happened here: replaying all 215 stored audits
found it on 0 of 214 windows, because reclaimable space has never been
below 34,844 MB and the configured milestones stop at 10 GB. Every
milestone is skipped as already reached, so the tray's "Reaches N GB"
rows have never been shown on this box.

**Milestones are absolute sizes, set as a ladder, and never counted from
today's total** (Session 342, 2026-10-04). The ladder is 1, 5, 10, 25, 50
and 100 GB. The route already skips every rung at or below the latest
total, so the rungs shown are the ones above it, and a cleanup brings the
low ones back without anyone editing `config.yaml`. The 1/5/10 GB rungs
date from 2026-03-23 and were never measured against this box, which has
held 34,844 to 40,764 MB of reclaimable files since 2026-08-06.

Counting from today ("+5 GB from now") was rejected for two reasons.
Its date is `5120 / slope` days from the latest scan, so it restates the
"Junk growth" row beside it and tells the reader nothing new. And it is
re-anchored at every scan, so it moves away as fast as time passes and is
never reached. An absolute rung has a fixed meaning, its date can arrive,
and a reader can watch it get closer.

The ladder's dates are only as good as the slope, and that slope is
poor here. Replayed over all 214 stored windows, it is zero or negative
on 121 and runs up to 5,075 MB/day on the others. The rungs now show
whenever the slope is positive (93 windows). But on 2026-10-04 they read
50 GB in 2029 and 100 GB in 2040, from a 12.7 MB/day fit, while the
whole series grows 125.7 MB/day and reaches 50 GB in about 83 days. The
cause is that the fit window is the 10 newest scans rather than a span
of days, and scans cluster. That is `SNAG-FILES-002`, left for its own
session. The tray now orders the rows by date and then size. Before
this it sorted the labels as text, which put "100GB" above "50GB". No
one had seen that, because no row had ever shown.

**The junk-growth fit spans 30 days of audits, never the newest N scans**
(Session 343, 2026-10-04, `SNAG-FILES-002` closed). `get_trends` now
makes two queries. `limit` picks the newest scans for the `scans` list
and nothing else. The forecast reads every audit's `scanned_at` and
`total_reclaimable_mb` from the last `history_days` (default 30, the
same as the disk fit on `/actions`). It selects the two columns and not
the row, because each row carries a `findings` blob and the 30 days held
4 MB of them.

The window was measured before it was chosen, by replaying every stored
audit as "now":

| window | windows | slope > 0 | sign flips | 50 GB date |
|---|---|---|---|---|
| 10 newest scans | 214 | 93 | 13 | 3 days to 386 years out |
| 14 days | 189 | 188 | 1 | 2026-09-27 to 2254 |
| 30 days | 80 | 80 | 0 | 2026-11-23 to 2027-01-16 |
| 45 days | 44 | 44 | 0 | 2026-12-07 to 2026-12-21 |

The series moves in steps with flat stretches between them. A count of
scans can land inside one flat stretch and read no growth, or across one
step inside a day and read gigabytes a day. A span of days holds whole
steps and the flats between them, so its slope is the step rate averaged
over time, which is what a "reaches 50 GB" date needs. 14 days is still
short enough to sit between two steps. 30 days is the shortest window
measured that never changed sign, and its 50 GB date moved a median of
1 day per day and at most 12. 45 days is steadier still, but it was
measurable on only 44 windows and would answer more slowly after a
cleanup. On the live audits the 30-day fit reads 117.8 MB/day over 83
scans, 50 GB on 2026-12-29 and 100 GB on 2028-03-08, where the 10-scan
fit read 2029 and 2040. If the organiser stops scanning for a month the
window empties and the route says `insufficient_data`. It does not fall
back to older scans.

`GET /api/files/review` is the weekly disk review, stored in its own
`disk_reviews` table. It was built as the mirror of the project review
that has since moved to 8400. It is one of three LLM-narrated reviews this
service produces, beside the log review (`monitor/log_review.py`) and the
health review (`monitor/health_review.py`); this said "the only" one
until 2026-09-30, and was false for as long as either of the other two
had existed. Two rules govern any LLM-narrated
review here, both learned from live runs:

1. **Commit the read transaction before calling the LLM.** This host sets
   `idle_in_transaction_session_timeout=1min` and inference takes longer.
2. **Give the model no numbers — do not merely instruct it not to use them.**
   Verified 2026-08-06: handed "25.0 GB across 50 directories" plus an
   explicit "do not restate figures", dria-agent-a-3b restated them *and*
   published the quotient as "each consuming 5GB". `build_review_prompt` is
   now figure-free by construction (sizes → bands, categories → phrases,
   occupancy → a direction), guarded by a test asserting no digit reaches
   the model **from the data** — the narrow form, because every
   `REVIEW_INSTRUCTIONS` block numbers its sections and caps the model at
   150 words, and those digits are instructions to the model rather than
   measurements about the box. Two of the three Tier 3 docstrings claimed
   the wider "contains no digit by construction" until 2026-08-25
   (`SNAG-DOCS-004`); the rule is stated once now, in
   `tests/review_prompts.py`, and each of the three modules drives its own
   prompt against it. Every real figure lives in `build_facts_section`,
   which is prepended to the narrative deterministically. `strip_markdown` removes
   the headings and lists the model emits despite being told not to.

**The 150-word limit is held by code, not by the instruction**
(Session 293, 2026-09-29). The limit counts the model's prose alone,
never the facts block in front of it, which is why a word count of the
stored `narrative` says nothing about it. dria-agent-a-3b keeps the
limit about half the time, and the overrun is bimodal (about 100 words
or about 280), so `hold_to_word_limit` takes three steps: keep prose
that fits, ask once more for 120 words, then cut with
`core.text.trim_to_words`. The cut lands after the last `.`, `!` or `?`
inside the limit and appends the truncation marker. A bare line break
is deliberately not a sentence end, because `strip_markdown` leaves the
model's headings on lines of their own and a cut there publishes a
heading with nothing under it. Neither `n_predict` nor the second pass
alone guarantees the limit: the first stops mid-section, and the second
missed once in six. Which step does the work depends on the invocation;
see `SNAG-GPU-007`. The mechanism moved to `sysadmin/core/word_limit.py`
on 2026-09-30, when the log review adopted it; each review passes its
own condense prompt and log-event prefix.

The three `/api/files/*` action endpoints share one manifest shape and are
**dry runs unless the request body sets `confirm: true`** — see
`sysadmin/files/actions.py` for the safety rules (root confinement,
no symlink following, no overwriting, trash instead of delete).

`POST /api/projects/{name}/branches/prune` applied the same contract to
git branches and **moved with the domain** (ADR-0005). Its safety rules —
merged-into-the-default-branch eligibility, `include_unmerged` gated on
both the request and config, and the default/protected/checked-out/worktree
branches that are never deleted whatever the flags say — are
estate-manager's now. The `agents.project_organiser.branch_actions` block
was left parsed here and read by nothing, recorded as knowingly untidy in
ADR-0005 rather than trimmed in the same sitting because config classes
fan out into defaults tests. **It is gone since 2026-09-14** (Session
236), with `BranchActionsConfig` and the four other nested models behind
the organiser's unread leaves — the key in `config.yaml` and the field in
`config.py` deleted together, since dropping only the key is silent (the
model default takes over) and dropping only the field is loud
(`config_keys` names the orphan). What survives the block is
`projects_root` and `discovery_depth`, both measured to have live
readers.
