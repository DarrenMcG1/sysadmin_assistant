# Handoff — 2026-08-24

## Next action

Take `SNAG-LOG-011` — `GET /api/logs/summary` still answers `200` with `{"source":"summary","entries":[],"count":0}` through the `/{source}` catch-all, telling a caller "no summaries" where it should tell them "gone", and its ranking argument is stronger than it was for two sittings because migration 014 has now destroyed the table that route was named for, so the route describes a schema object that does not exist.

## Sub-session items

**One is owed, and it is a question rather than a change.** Session 33
(seam drift detection) has been named as blocked in three consecutive
rankings without the blocking question being asked. Its second task reads
another repository's fixture off the same disk, and cross-repo concerns
have had an owner since 2026-08-13, so **ask estate-manager** before
ranking it. That is a sub-hour action, not a session.

**Nothing else is owed.** `sysadmin` was restarted at
**2026-08-24 22:15:09** (required, not cosmetic — see below), `/health`
answers `200`, `alembic current` reads **014 (head)**, the sysadmin
schema holds **11** tables, and `alerts` holds **2** unresolved rows,
both expected. Do not re-verify these by hand: run
`./scripts/check-ops-claims.sh`, which `claude-preflight.sh` runs for you
at the top of every sitting, and which reported all seven checks green
after this session's document edits.

## This session — Session 74: the three frozen tables dropped

**Migration 014.** `project_snapshots` (3,447 rows), `project_reviews`
(4) and `log_summaries` (1) are gone, together with the four mechanisms
that carried each of them: a `retention_config` row, a
`TABLE_TIMESTAMP_MAP` entry, the `FROZEN_TABLES` exclusion in
`sysadmin/metadata.py`, and — for the third — the `LogSummary` model.
Table count **14 → 11**, head **013 → 014**, suite **2195** green, ruff
and mypy clean.

### Decisions taken, and what they were taken against

- **The blocker recorded in `tasks.md` was wrong by four orders of
  magnitude, and measuring it is what unblocked this.** That entry said
  the 26 rows the estate's copy lacks cost "a day of history for 26
  projects", and it had held this task since 2026-08-16. Compared on
  `(project_name, scanned_at)` across both databases: this schema's
  final sweep is `2026-08-13 07:35:03`, the estate's next scan is
  **07:35:46** — **43 seconds** — and **all 26 projects appear in it**.
  Nothing was ever missing from the estate's series.
- **Waiting was destroying the history the entry was protecting.** The
  same entry counted **3,739** rows on 2026-08-16 and there were
  **3,447** today: the `retention_config` row was thinning a frozen
  table on a 90-day window every night. The estate holds **4,155**
  snapshots back to **2026-05-10** against this schema's 2026-05-20 —
  a superset at both ends.
- **No copy was requested from estate-manager**, which the ADR had left
  as the likely next step. The measurement showed there was nothing to
  copy, so the cross-repo write never became necessary.
- **The estate's database was read once, by hand, and never from code.**
  That comparison is the first estate rule's business, so it was done
  from a shell by a human deciding whether to destroy data, and recorded
  in the migration's docstring rather than left to be re-derived. The
  migration itself performs no cross-database read.

### Options rejected

- **A new test asserting every mapped table still exists.** Written,
  then measured against `test_purge_statements_parse`, which hands every
  `TABLE_TIMESTAMP_MAP` entry to PostgreSQL as `EXPLAIN` and so already
  refuses a dropped table — and more strongly, since it also catches a
  wrong column and invalid SQL. Two guards for one fact is the shape
  `sysadmin/metadata.py` exists to remove, so it was deleted. What
  shipped is the half nothing covered: a `retention_config` row the map
  cannot resolve is skipped **in silence**, purging nothing and saying
  nothing, and no test in the suite had ever read that table. Falsified
  before the migration ran — it named all three.
- **Deleting `FROZEN_TABLES` along with its last member.** An entry
  there is a *blindfold* over the drift guard, which compares whatever
  `include_object` admits — so emptying it is what proves the three
  tables are gone, and no new test was needed. Deleting the constant
  would take `tests/test_autogenerate_config.py`'s guard against a
  second copy with it, at exactly the moment nothing is exercising it.
  It stays, empty, with the rule that an entry must be paired with a
  *drop* entry on the roadmap: frozen is a stage, not a destination.
- **Taking `SNAG-DOCS-002` in the same sitting**, which the previous
  handoff proposed. It is a change to the tray's public surface (four of
  the eight unread models are re-exported by `sysadmin_tray/models.py`)
  and shares nothing mechanical with a migration. It stays open.

### What is blocked or left

- **The `agents.project_organiser` config block** is the last limb of
  the drop task and was deliberately not taken with it — it is a config
  change that fans out into the defaults tests, with no live
  consequence either way. Added to `tasks.md` as its own entry and
  ranked third.
- **Nothing was found and left unfixed**, so no SNAG entry was opened
  and none closed.

### Verification, and the one thing that was required rather than tidy

- **The downgrade reproduces the schema byte for byte and cannot
  reproduce the rows**, stated in the docstring rather than left to be
  discovered. Round-tripped against the live database and diffed against
  a `pg_dump -s` taken before the drop: identical, including both
  indexes, all three primary keys and all three retention rows with
  their original windows.
- **The names are interpolated, never bound** — migration 013's rule,
  verified by rendering `alembic upgrade --sql 013:014`, where a
  bindparam becomes `WHERE table_name = NULL` and deletes nothing.
- **The restart was required.** The daemon booted at 21:52:06 held the
  old `TABLE_TIMESTAMP_MAP` in memory, so its 03:00 purge would have
  raised for three tables that no longer exist. `kill -TERM`, back
  healthy in 3 s, no `sudo`, nothing above `INFO` in the journal since
  beyond the standing `api.auth_token` warning.

## Previous session — Session 73: the block that opens a sitting gets a reader

**`SNAG-ESTATE-008`'s machine-checkable half fixed.** Six consecutive
sittings had been spent on claims that had stopped being true. The
previous ranking demoted the fix for having "no obvious enforcement
point, since these claims live in prose" — and `claude-preflight.sh`
already ran every sitting and already printed those claims, from the
prose, with nothing between the document and the reader.

- **`sysadmin/ops_claims.py`, `sysadmin-check-claims`,
  `scripts/check-ops-claims.sh`**, wired into preflight (where a stale
  claim is caught) and postflight (where one is made). Seven checks:
  five *claims* parsed out of the block — routes, tables, the documented
  Alembic head, unresolved alerts, the daemon's start time — and two
  *state* checks, the live schema against the packaged head and whether
  the daemon serves the code on disk. A mismatch on the first kind means
  the document is stale; on the second, the box is.
- **Nothing blocks and nothing edits a document.** A check that corrects
  the file it reads becomes a second author of the claim.
- **`SNAG-ESTATE-011` opened** for what no pattern can reach: `/health`
  answers, "9 rows with 0 colliding titles", "clears at 03:32
  tomorrow" — the convention the entry proposed, which has no
  enforcement point yet and by its own argument should wait until the
  block has been written twice under the new rule.

### Session 73 — what the sitting found that nobody had written down

- **The entry understated its own defect by a whole surface.** Preflight
  was not failing to *check* the sub-session block — it had never
  *printed* it, because its extract is anchored on `## Quick Status` and
  the block is a blockquote above that heading. The one surface the
  global rules require to be read first was the one the banner omitted.
- **The obvious "is a restart owed" rule is wrong on this box, today.**
  Daemon start 09:58:28 against the newest commit touching `sysadmin/`
  at 10:05:22 reports a restart owed on identical content: this
  repository restarts to verify and commits afterwards. The newest `.py`
  on disk, 09:57:46, answers it correctly. Both were run before either
  was written down.
- **`systemctl show` answers for a unit that does not exist** — exit
  `0`, `ActiveState=inactive`, an empty timestamp read as epoch zero.
  "Nobody looked" rendered as a measurement, which is this snag's own
  shape found inside its own fix.
- **The check refuted its author within a minute of being wired up.**
  The first rewrite of the block under it wrapped `holds **2**` and
  `unresolved` across two lines with a `>` between, and the claim came
  back `unknown` — correct, and useless, because a paragraph reflow must
  not be able to retire a claim. The region is flattened to prose before
  matching. Nothing but running it would have found that.
- **`len(app.routes)` is 50, not 46.** FastAPI adds `/openapi.json`,
  `/docs`, `/docs/oauth2-redirect` and `/redoc` as routes of its own, so
  a sitting re-counting "live off `create_app()`" the obvious way would
  have declared the Quick Status table stale on its first run.
- **A *fall* in the alert count is the founding case**, and it is the
  direction nobody writes a rule for.

### Session 73's ranking, kept for the record

Its first-ranked item — *drop the three frozen tables* — is what Session
74 carried out above, and its estimate of the blocker is the thing worth
carrying: it repeated the "loses a day of history for 26 projects"
figure from `tasks.md` without re-measuring it, and the figure was 43
seconds. The live ranking for the next sitting is at the top of
`docs/roadmap/STATUS.md`, not here.
