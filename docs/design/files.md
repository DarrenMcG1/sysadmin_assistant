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

`GET /api/files/review` is the weekly disk review, stored in its own
`disk_reviews` table. It was built as the mirror of the project review
that has since moved to 8400, and is now the only LLM-narrated review this
service produces. Two rules govern any LLM-narrated
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
