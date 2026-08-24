# Handoff — 2026-08-24

## Next action

Drop `project_snapshots`, `project_reviews` and `log_summaries` in one Alembic migration, removing their `retention_config` rows, their `TABLE_TIMESTAMP_MAP` entries and their `metadata.py` `FROZEN_TABLES` exclusions with them, and take `SNAG-DOCS-002`'s decision about the contract models nothing reads in the same sitting — because nothing has written any of those three tables since 2026-08-13 or Session 69, four mechanisms still carry them, and it is the first structural change this repository can verify by machine rather than assert.

## Sub-session items

**One is owed, and it is a question rather than a change.** Session 33
(seam drift detection) has been named as blocked in two consecutive
rankings without the blocking question being asked. Its second task reads
another repository's fixture off the same disk, and cross-repo concerns
have had an owner since 2026-08-13, so **ask estate-manager** before
ranking it. That is a sub-hour action, not a session.

**Nothing else is owed, and this is the first handoff whose ops claims are
machine-checked.** `sysadmin` was restarted at **2026-08-24 21:52:06**,
`/health` answers `200`, `alembic current` reads **013 (head)**, and
`alerts` holds **2** unresolved rows — both expected (`Estate scan could
not reach sources` clears at 03:32 when the estate's daily timer runs;
`Weekly disk review ready` is below `tray.notify_min_severity`). Do not
re-verify these by hand: run `./scripts/check-ops-claims.sh`, which
`claude-preflight.sh` now runs for you at the top of every sitting.

## This session — Session 73: the block that opens a sitting gets a reader

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

## What the sitting found that nobody had written down

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

## Next session — ranked

1. **Drop the three frozen tables.** Unblocked, bounded, and the only
   ranked item whose cost is being paid today: `retention_config`,
   `TABLE_TIMESTAMP_MAP`, `FROZEN_TABLES` and the drift guard all carry
   tables nothing has written for eleven days or more. ADR-0005 names
   the migration as the follow-up. The table count moves **14 → 11**,
   which `sysadmin-check-claims` will check and `sysadmin-check-schema`
   will block the commit over if the migration is written and not
   applied — the two failures `SNAG-DB-001` and `SNAG-DB-005` are made
   of, now with machinery in the way of both.
2. **`SNAG-LOG-011` — a deleted route still answers `200`.** Re-measured
   tonight and unchanged: `GET /api/logs/summary` returns
   `{"source":"summary","entries":[],"count":0}` through the `/{source}`
   catch-all. Loses on cost-of-not-doing-it — measured, it has no
   consumer, so it is a regression detector rather than a repair.
3. **`SNAG-ESTATE-011`.** Loses by its own argument: a marker beside the
   prose is a second statement of one fact that can disagree with it,
   and that trade is only worth taking once the block has been written
   twice under the new rule.

**Runners-up.** `SNAG-LOG-013`'s population is **measured empty tonight**
— `GET /api/logs/actions` serves 5 rows with 0 colliding capped prefixes,
its historic raw-JSON signatures having left the 7-day window at about
14:11 as the entry predicted. It is **not** closed on that: "the
population is zero" is the reasoning that mis-ranked its own parent one
sitting ago. `SNAG-UNITS-006` and `SNAG-LOG-006` are empty too. The four
permanent `running` rows in `agent_runs` stay filed rather than ranked —
the measurement *is* the task, so it is an hour.

**Blocked or delegated.** Session 33 on the question above.
`SNAG-ROADMAP-002` has now published wrong board movement for six
consecutive sittings (57 → 58 entries for a sitting that closed one and
opened one), and the parser is estate-manager's, so what is owed from
here is a report. `SNAG-LOG-012` is delegated to `estate-lib`;
`SNAG-ESTATE-002`, `-004`, `-006` and `-007` remain estate-manager's.
