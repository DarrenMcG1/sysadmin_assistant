# ADR-0001: Project identity lives in the repositories

- **Status**: accepted
- **Date**: 2026-08-08
- **Supersedes**: the `projects.yaml` registry, retired to
  [projects-registry-legacy.yaml](../projects-registry-legacy.yaml)
- **Session**: 35 (phases 1–6)

## Context

One file, `projects.yaml`, described every project on this box: where it
was, what it was for, whether it was still being worked on, and which
endpoints to health-check. It was keyed by absolute path.

Three failures came out of that shape, all of them observed rather than
predicted.

**A path can rot silently.** `sports_analyser` pointed at a lowercase
path against a CamelCase directory; on a case-sensitive filesystem the
entry matched nothing and was dead from whenever it was written until
2026-08-04. `PA-worktrees` pointed at a directory deleted during a
reorganisation and kept a board row with a health score and a next action
for two days afterwards. Neither produced an error. A lookup that matches
nothing returns nothing, and nothing is exactly what an absent project
looks like.

**Two endpoints was the wrong number.** The schema modelled one `backend`
and one `frontend`. Alfred has four services and venture-assistant five,
so seven units ended up in `config.yaml`'s `agents.sysadmin.services`
with comments explaining that they belonged to a project the file could
not express. The comments were correct, hand-maintained, and invisible to
the code.

**Rules lived in prose.** That a `Type=oneshot` service must be watched
through its timer was a paragraph in a YAML comment. It was right, and it
had to be reapplied by hand every time somebody added a schedule.

## Decisions

### Identity travels with the directory

Each repository carries a `.project.yaml` declaring its own `id`, `name`,
`category`, `status` and the `decisions` behind them. A rename or a move
cannot orphan a file that lives inside the thing it describes, and
filesystem case sensitivity stops being a correctness concern.

The registry (`sysadmin/registry/`) discovers repositories, validates the
manifests, and exposes an id → path map. It depends on neither the
monitor nor the organiser, and both depend on it — which removed the last
cross-domain import between them, since the two agents had previously
disagreed about what counted as a project by importing one definition
from the other.

**A repository with no manifest is `undeclared`, not `active`.** The old
default made an absent decision look like a decision to keep working, and
the board showed eighteen rows for a five-project estate as a result.
`undeclared` is a reportable state: it is scored exactly like `active`,
because nobody has said the project is resting, but it is counted and
named separately so the gap is visible.

### services.yaml holds no paths

Services are attached to projects by **id**, resolved through the
registry, and an id that names nothing **fails at load** with every bad
reference listed at once. That is the whole point: the previous failure
mode was silent, and this one stops the service.

There is no limit on how many services a project may have, and `kind`
decides the check — `http`, `tcp`, `systemd`, `timer`, `oneshot`,
`static` — so the oneshot-watch-the-timer rule is a field the checker
reads rather than a convention a comment explains. `monitor: false`
requires a `reason`, so "deliberately not watched" can never again look
like "nobody wired it up".

`systemd.scope` defaults to **user**, reversing the old `user: true`
opt-in. An omission used to send the check to the system bus, where the
unit is simply unknown and the failure is silent; a wrong `system` now is
loud, and a wrong `user` was not.

### Persistence was deliberately deferred

Nothing here added a database table, and that was a constraint rather
than an oversight. **Persistence is the decision that locks in
ownership**: a `projects` table in the `sysadmin` schema would make this
service the system of record for project state, and that question is not
settled (below). Files can be moved between repositories in an afternoon;
a table that other things have started reading cannot.

`estate.json` follows the same rule. It is a re-projection of each run,
versioned and written atomically, and its `health` block is derived from
the snapshot computed in the same run rather than stored — so the scoring
rubric can change without a migration and no stale score outlives the
rules that produced it.

The one migration this work did add (009, `'skipped'`) was to the
*monitor's* existing `service_health` table, for services services.yaml
declares as deliberately unchecked. It records a state that already
existed and had nowhere to go.

### Staleness is measured from the last commit that changed work

`last_commit` and `last_code_commit` are separate fields, and every
staleness figure downstream is computed from the second. Two estate-wide
sweeps — a pre-reorganisation snapshot and a fan-out that wrote a roadmap
document set into eleven repositories — touched every project without
being work in any of them, and left the whole estate looking active on
the same two days.

Both dates are published. Reporting only the adjusted one would hide that
a sweep happened; reporting only the raw one is what made a project last
worked on in February read as touched last week.

## Open question: who owns project state

**Unresolved, and deliberately so.** Whether project organising is a
domain of Alfred, a standalone service, or a permanent part of this one
has not been decided. The work above is staged so that the decision stays
cheap:

- project state is in files, inside the repositories it describes, so a
  future owner reads them without a data migration
- `sysadmin/projects/` is a package with a tested import boundary, so
  extracting it is a directory move rather than a rewrite
- the organiser runs from its own timer and its own entry point, so it
  already runs without the monitoring daemon

What is *not* staged: `alembic/versions/001_initial_schema.py` creates
both sides' tables in one revision, so `project_snapshots` and
`project_reviews` cannot be carried to a new database by moving files.
Extracting the project side into its own service still means a data
migration, and that remains the reason to leave it here for now.

## Consequences

- Adding a service is one entry in one file; adding a project is one file
  in that project.
- A typo in a project reference stops the service at startup instead of
  producing a check that never runs.
- `projects.yaml` cannot be deleted yet: one of its comments records the
  removal of a project that no longer exists, so there is no manifest to
  move it into.
- The estate's reasoning now lives in nineteen `decisions:` blocks across
  fifteen repositories rather than in one file's comments. That is harder
  to read end-to-end and harder to lose.
