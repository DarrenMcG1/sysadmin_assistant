# Schema and storage — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

**Serving against a schema this code was not written for is worse than
not starting** (Session 43, SNAG-DB-001). `sysadmin/core/schema_guard.py`
compares `alembic_version` against the packaged head in the lifespan and
raises — deliberately **not** inside a `try`, unlike the unit-failure
resolve three lines below it, because a stale alert row is worth less
than a boot and a schema mismatch is the exact opposite trade. Migration
009 was written, committed and never applied; two minutes later the
daemon began writing a status the database rejected, and
`service_health` took **no rows for 39 hours** while the tray went on
rendering the last values it had. Nothing applies migrations here — no
script, no `ExecStartPre`, no CI step.

Refusing is the only option whose failure mode is visible: the unit
enters `failed`, `StartLimitBurst=5` makes the loop terminal, and
`sysadmin-failed.service` announces it — the Session 39 machinery's
second caller. Coming up degraded and raising a critical instead would
write that alert *through the schema that is wrong*.

Three rules. **The head comes from alembic's own `ScriptDirectory`**,
never a regex over `alembic/versions/*.py` — a second implementation of
the revision graph drifts from the command it exists to measure against.
**`alembic_version` is read schema-qualified**: `version_table_schema`
exists because the `projects` database holds another application's copy
in `public`, and resolving through `search_path` would compare this code
against a stranger's revision and pass. **Every way of not-knowing fails
closed with its own message** — unreadable scripts, a branched history
(two heads, which `alembic upgrade head` itself refuses), and a database
never migrated are three different faults and the operator needs to be
told which. Note what could *not* have caught this: `verify_connection`
proves the database answers, and the drift guard skips `alembic_version`
and does not diff CHECK constraints.

**The guard worked and the outage happened anyway, and the snag's own
ranking of the fix was wrong in two places** (Session 70,
`SNAG-DB-005`). Migration 013 was written, committed and never applied;
the daemon was restarted to serve a new route, this guard refused, and
`sysadmin.service` stayed dead **23 hours** — `SNAG-DB-001`'s cause with
the guard in the way, which is the better half of the trade and is still
an outage. `sysadmin-check-schema` is the same comparison as a console
script, wrapped by `scripts/check-migrations.sh`, **blocking** in
`claude-precommit.sh` and advisory in `claude-postflight.sh`.

Six rules, four of them the opposite of what the entry proposed:

1. **`ExecStartPre=` buys nothing, and cost was the wrong axis to rank
   on.** The entry put it first as the cheapest option that works. A
   check there fails *identically* to the lifespan guard — same refusal,
   same `failed`, same 23 hours, one process earlier. It is not a weaker
   version of the fix, it is the fix already in place, relocated. The
   entry's second candidate has the mirror defect: postflight would not
   have caught **this** outage, because the restart that triggered it
   happened *mid-sitting*, and a session-end check runs after the box is
   already down.
2. **The commit is the last scripted moment before the restart.** There
   is no deploy script on this box; the restart is a hand-typed `kill
   -TERM`. So the check lands at the commit, and it blocks **whatever is
   staged, not only a migration file** — the question is the state of
   the box rather than the content of the commit, and a database behind
   the checkout means the daemon is already dead or dies at its next
   restart.
3. **Three verdicts and three exit statuses, because `unknown` is not a
   flavour of failure.** `match`/`mismatch`/`unknown` → 0/1/2 —
   `ports_checked`'s rule promoted into a return type. Exit 2 **warns
   and never blocks**, which is the one place this family fails *open*:
   a commit refused because PostgreSQL happens to be down teaches the
   operator to reach for `--no-verify`, which disarms the check for the
   case it exists for, and a commit is not what breaks the box — the
   restart is. `schema_guard` still fails closed at boot, where the
   alternative is serving against the wrong schema.
4. **Only the connection is duplicated; never the rule.** Both new
   callers run *outside* a running application — a git hook, and a
   handler that fires when the daemon is dead — so `get_engine()` would
   raise and `live_revision_sync` is unavoidable. The schema-qualified
   table name, the none/one/many interpretation and the wording of a
   mismatch live in `_qualified`, `_interpret_version_rows` and
   `describe_mismatch`, and a test drives **both** readers against the
   live `alembic_version` and asserts they agree. Falsified by pointing
   the sync one at `public.alembic_version` — the other application's
   copy that rule 2 exists to keep out — and it fires.
5. **Nothing applies a migration, and a test enforces that.** Applying
   unattended at boot is how a bad migration reaches production with
   nobody watching, so `tests/test_schema_guard.py` asserts the word
   `upgrade` appears nowhere in `check-migrations.sh`'s executable
   lines — the only place a future edit would put it.

6. **The entry named only prevention, and prevention owns almost none of
   the 23 hours.** `sysadmin-failed.service` fired *correctly*, with a
   persistent critical toast, and said `result=exit-code, exit=1,
   restarts=5` — pointing at `systemctl status` and `journalctl`. The
   cause was one revision number and the remedy one command, and
   `_REMEDY` had held both all along and written them **only to the
   journal**, the surface nobody opens unprompted. `unit_failure.`
   `_schema_diagnosis()` puts the verdict in `details['schema']` and in
   the alert message, and `notify-unit-failed.sh` puts it in the toast:
   `monitor/collation.py`'s rule 4 — the remedy's trap is carried in the
   alert — applied to the fault that needed it most.

A healthy schema **adds nothing to the message and is still recorded**,
because "checked, and it was not this" is a different fact from "never
checked" and a reader of a stale row cannot tell them apart otherwise.
And the annotation **can never suppress the row it annotates** — the
regression this fix could most easily have introduced — so
`_schema_diagnosis` catches everything and a test drives `schema_status`
raising while asserting the row is still written.

Two things the sitting corrected on the box rather than on paper. The
toast said `sudo systemctl status`; measured as `gaddi` (wheel), both it
and `journalctl -u sysadmin` exit 0, so a reader was told a next step was
harder than it is — the missing remedy's defect one line up, and the
second `sudo` claim in two sittings to be wrong when checked. And the
counterfactual was driven by adding a temporary **migration file**, which
raises the packaged head and leaves `alembic_version` untouched: stamping
the database down would have put the box into the state the snag
describes for the duration of the test.

**What autogenerate compares has one statement, and it is production
configuration the test borrows** (`SNAG-DB-003`). `sysadmin/metadata.py`
owns `FROZEN_TABLES`, `include_object`, `include_name` and the
`COMPARISON_OPTS` dict; `alembic/env.py` splats it into
`context.configure` and `tests/test_schema_drift.py` into
`MigrationContext.configure(opts=…)`. It sits beside `Base` because that
module already makes the same argument for the *model set*, and which of
the live schema's tables the metadata is authoritative for is that
question one step further.

The two copies it replaced failed in **opposite directions**: an
exclusion present only in `env.py` makes the drift guard fail loudly,
while one present only in the guard is silent — green test, and the next
`alembic revision --autogenerate` writes `op.drop_table` into an
unrelated migration. Measured with the exclusion removed: `remove_table`
for both frozen tables, against 3,739 and 4 live rows.

**`FROZEN_TABLES` is empty since migration 014 and is deliberately
kept.** An entry there is a *blindfold* over the drift guard, which
compares whatever `include_object` admits — so dropping the three tables
needed the set emptied rather than a new test to prove them gone, and
every live table is mapped again. Deleting the constant with its last
member would take this guard against the copy coming back with it, at
the moment nothing is exercising it. A domain leaving and stranding its
tables is a shape this estate has produced once; an entry added here must
be paired with a *drop* entry on the roadmap, because frozen is a stage
and not a destination.

Three rules. **The flags travel with the exclusions**, because
`compare_type` set in `env.py` and absent from the guard leaves the
guard green while blind to the drift it certifies. **The search_path
does not travel**: it belongs to the connection (`env.py` pairs it with
`CREATE SCHEMA`, DDL the guard must never run) and its drift fails
loudly as double reflection. **`tests/test_autogenerate_config.py` is an
AST sweep, not an import** — `env.py` runs the migrations at module
scope and cannot be imported — asserting there is no *second* body
rather than that two bodies match, which would pin the copy instead of
removing it. Two of its five tests exist so the detector can be seen to
fail: one runs the walker at the owner, which must trip every rule.

Retention needs **both halves**: a row in the `retention_config` table and
an entry in `TABLE_TIMESTAMP_MAP`. `run_retention` iterates config rows and
looks each up in the map, so a table with one half is silently never purged
— `project_reviews` and `disk_reviews` had neither, `unit_audits` had only
the map. Review tables get **365 days**, not the 30 that check data gets: a
weekly narrative kept for 30 days is four rows, too few to see a trend.
`KEEP_LATEST_PER` protects the newest row per entity (`"true"` means "the
whole table is one entity"), because a purge that emptied a review table
would make its route 404 — which reads as "never generated" rather than
"none lately".

**The two halves fail in opposite directions, which is what decided how
migration 014 dropped the three frozen tables.** A `retention_config`
row the map cannot resolve is **silent** — `run_retention` iterates
config rows and looks each up, so a miss is skipped with no log line and
nothing is purged. A map entry for a table that no longer exists is
**loud**: its `DELETE` raises every night, contained to that table by its
savepoint. Both halves therefore move with the migration, and only the
silent one needed a new guard — `test_purge_statements_parse` already
refuses a map entry PostgreSQL cannot plan, and more strongly than an
existence check, so the existence check written beside it was measured
against the stronger guard and deleted rather than shipped as a second
statement of one fact. Nothing in the suite had ever read
`retention_config` itself.
