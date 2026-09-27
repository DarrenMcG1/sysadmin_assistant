# Configuration — design reasoning

*Moved verbatim from `CLAUDE.md` on 2026-09-27 (Session 272), where it
sat under the Contract Registry heading. Where the text says "this
document", it meant `CLAUDE.md`. Session numbers are the records in
[`../roadmap/tasks.md`](../roadmap/tasks.md), `SNAG-…` ids are entries in
[`../roadmap/snag_list.md`](../roadmap/snag_list.md), and `ADR-nnnn` is
a record in [`../adr/`](../adr/). The other design documents are listed in
[`../README.md`](../README.md).*

What the deletion did **not** reach was `SNAG-CFG-004`, and the entry's
own headline fix was refuted by the file it was about (Session 136).
`config.yaml`'s models inherit `extra="ignore"` (**0 of 32**) while
`services.yaml`'s all set `extra="forbid"` (**5 of 5** since
2026-09-23's `HttpExpectation`; 4 of 4 when written), so
`briefing_hourr: 9` parses cleanly and the briefing stays at 6. **The
counts have not moved and must not** — *and the one that moved is not
one of them*: the denominator read **37** until 2026-09-14, when Session
236 trimmed `agents.project_organiser` to its two live leaves and deleted
the five nested models behind the rest (`HealthGradeBands`,
`BranchActionsConfig`, `CodeCommitIgnoreConfig`, `EstateConfig`,
`IdleNudgeConfig`). The claim is `0 of N` against `M of M`, so what must
not move is the **0** and the **all**; `N` and `M` are how many models
exist — the second read 4 until a fifth arrived forbidding like the rest
and a test pinning `== 4` went red on a change that kept the claim — and
five of them leaving for a reason with nothing to do with `extra=` says
nothing about the asymmetry. Re-measured rather than nudged, because
`tests/test_config_keys.py`'s floor is a *premise* — without it
`strict == 0` passes vacuously over an emptied module — and its own
failure message asks for exactly that. Walking the shipped `config.yaml`
against `AppConfig`'s field tree still finds **ten keys the backend does
not declare** — the top-level `tray:` section and nine leaves under
`notifications.tray:`, every one read by `sysadmin_tray/config.py`,
which parses the same file for itself, and the trim moved that figure
not at all because both halves of each deleted leaf went together.
`extra="forbid"` across the 32 is therefore not a trade-off to weigh
against `SNAG-DB-005`; it is a daemon that does not start on this box.

**The asymmetry is structural rather than an inconsistency.**
`services.yaml` can forbid because every key in it belongs to the
process holding the models; `config.yaml` cannot, because it carries a
region this process does not own. One file, two parsers, neither a
superset — and `schema_guard`'s posture runs the *other* way here for a
reason that is about the cost side rather than the shape: that guard
refuses because serving against the wrong schema is worse than not
serving, and serving with an ignored config key is demonstrably not,
having been this daemon's behaviour for its whole life at a cost of one
briefing at the wrong hour.

`sysadmin/core/config_keys.py` is what shipped, and it **reports**.
Five rules, three of them the opposite of the obvious implementation:

1. **It cannot refuse**, and that is settled by the shape of the
   mechanism rather than by a flag someone could flip — a walker returns
   a list. The lifespan warns and `ReloadReport.unknown_keys` carries it
   to `POST /api/sysadmin/reload`, which is the surface an operator who
   has just edited the file is actually holding.
2. **It derives from `model_fields`** rather than restating the schema.
   A second hand-written list of valid keys is `SNAG-DB-003`'s shape,
   and the entry is about a key nobody declared.
3. **A shape it cannot classify is reported, never skipped.**
   `unwalkable` names a subtree that went unread, so its zero unknown
   keys are zero-because-blind — `ports_checked`'s rule, and a silent
   skip is this module's own defect one level down.
4. **Foreign keys are exempted by leaf, with `tray:` the one deliberate
   subtree.** `notifications.tray.mute_services` is read *here*, so a
   subtree exemption would silence `mute_servicess` on the one key under
   that section the backend depends on — the defect rebuilt inside its
   own fix. The dividend is unasked-for and real: because the correct
   spelling is exempt and a typo is not, a misspelt *tray-owned* leaf is
   reported too. `tray:` is exempt whole because holding a model of
   another parser's section is the second-owner defect.
5. **The boundary is pinned, not asserted.** `sysadmin.core` may not
   import the tray, so `TRAY_SECTION_KEYS` and `NOTIFICATIONS_TRAY_KEYS`
   were lifted out of the loops consuming them and a test asserts they
   agree with `FOREIGN_KEYS` — import where you can, pin where you
   cannot. A second test refuses an exemption naming a key `AppConfig`
   declares, because a stale exemption stops describing a foreign key
   and starts hiding one of ours.

**The drop is unchanged and only the silence is gone**, which is the
pair a later reader needs both halves of: no model gained
`extra="forbid"`, so the typo is still accepted and still dropped, and
`tests/test_config_defaults.py` keeps the parse half while
`tests/test_config_keys.py` holds the report half, each naming the
other.

**The residue had its own owner, and the fix belongs on the other side
of the seam** (`SNAG-CFG-005`, closed 2026-08-30).
`sysadmin_tray/config.py`'s `tray_section_report` names the keys under
`tray:` this program does not read — a `WARNING`, never a refusal, for
`config_keys` rule 1's reason. Four rules, three of them the opposite of
the obvious implementation:

1. **The allowlist is the authority, never the model.** A walk of
   `tray:` against `TrayConfig` is the shape `config_keys` uses for
   `AppConfig`, is legal here (`sysadmin.core` must not import the tray;
   the reverse is fine and this module already does it for `defaults`)
   and **would have shipped green**. `TrayConfig` declares **19** fields
   and the section supplies **7** — the other twelve arrive from
   `notifications.tray:`, `api:` and `services.yaml` — so a model walk
   calls `tray.reminder_hours: 5` declared when setting it there does
   nothing. The model over-declares relative to the section;
   `TRAY_SECTION_KEYS` does not, which is what Session 136 lifting it
   out of the consuming loop made available.
2. **`notifications.tray:` is not reported here**, because that region
   is exempt by *leaf* and the backend already names a typo in it —
   driven, not assumed: `digest_modee` and `mute_servicess` both come
   back from `report_for_file`. One fact, one speaker. The test that
   named this rule drove the **backend**, which proves the other speaker
   exists and does nothing to stop this one becoming a second, so a
   mutation appending a `notifications.tray.*` path went red on an
   unrelated test by accident. The negative half is a separate test and
   exists because the mutation exposed its absence.
3. **A shape it cannot read is reported, and that closed a crash.**
   `tray: 5` raised `TypeError: argument of type 'int' is not iterable`
   out of `key in tray_section` — the one section this module
   hand-parses failing unhandled, while `_read_services` next door costs
   "a mute list, not a launch". `None` is clean and a non-mapping is
   `unwalkable`, and the split is only reachable because the caller
   stopped coercing: `raw.get("tray", {}) or {}` hands the report a
   clean `{}` for `tray: []`, which is falsy *and* malformed.
4. **The payload is in the message, not in `extra=`, and only a live
   drive said so.** The backend's idiom is readable because
   `JsonFormatter` folds `extra` into the line; the tray's formatter is
   `main()`'s `basicConfig(format="… %(message)s")`, so the first
   version reached the journal as the bare event name
   `tray_config_unknown_keys` — announcing a dropped key and unable to
   say which, this entry's own defect one level down. The retired check
   had recorded the *opposite* lesson (its first draft read
   `getMessage()` and missed the backend's `extra=`), so the wrong half
   of a two-sided lesson was copied. The convention is "use `extra=`
   where a formatter renders it", never "always".

Two things the sitting corrected in the module rather than around it.
**`tray.api_url` has never been read** and the loader docstring listed
the `tray:` section as its resolution priority 2 since `81b3bfb`, the
module's first commit; the `if "api_url" not in kwargs` guard beneath
was dead by construction and its comment is what the docstring copied.
Both went — a reader checking the new report against the old docstring
concludes the *report* is broken — and the key stays unread on purpose,
because `service.host`/`port` is the one home for the backend's address
while `estate_api_url` is read from `tray:` only because 8400 has no
`service:` block. `SNAG-TRAY-011` is the residue in turn: the warning
reaches `journalctl --user -u sysadmin-tray` and nothing else
(`composed_log_sources` returns 15 units and `sysadmin-tray.service` is
not among them) and fires once, at startup, where the backend
re-reports on every `POST /api/sysadmin/reload`.

The entry's check retired with it and **its meaning inverted**. It
counted `extra="forbid"` on both sides; this fix moves neither count, so
it would have gone on reporting *still holds* over a landed closure —
`check_review_schedule_unread`'s defect one entry earlier, and not a
flaw in how it was written, since the entry closed by a route the check
did not anticipate. `TestTheAsymmetryIsDeliberateAndStays` is the same
walk guarding the opposite claim.

**Configuration is re-read on demand, and the honest half is what it
says it could not do** (Session 49, `SNAG-UNITS-005`). `sysadmin/reload.py`
re-reads config.yaml and services.yaml on `SIGHUP` or
`POST /api/sysadmin/reload`. It sits **beside `main.py`** rather than in
`core/`: it composes `core.config` with `monitor.services`, and
`tests/test_import_boundary.py` forbids `core` from importing a domain —
the rule that makes every other boundary real. `metadata.py` had already
settled that placement in writing (*"composition roots… no domain imports
them"*), and that test now enforces it for all three.

The blocker was privilege, not design. `sysadmin.service` is a **system
unit running `User=gaddi`**, so the owner may signal it without `sudo`
(verified with `kill -0`, which probes permission without delivering).
`systemctl reload` would additionally need an `ExecReload=` line, and
*that* edit needs `sudo` — so the raw signal is the half that removes the
blocker. Note the trap: Python's default `SIGHUP` action **terminates**,
so a HUP sent to a daemon running code that predates this module is a
restart wearing a reload's name.

Four rules, three of them the opposite of the obvious implementation:

1. **Both files are validated before either is installed.** `parse_config`
   and `load_services` were split out of their loaders so the failure lands
   before the swap. A reload that half-succeeds *across files* leaves the
   process running a combination nobody wrote — strictly worse than the
   restart it replaces, because the operator's model is "the files on disk
   are what is running" and a partial install breaks it silently. Verified
   live: a broken services.yaml beside a valid config.yaml installs
   **neither**.
2. **Fields a reload cannot deliver are applied-and-named, not refused.**
   Nearly everything an agent reads is already re-read per run — every
   `_execute` calls `get_config()` at its top, a consequence of
   SNAG-AGENT-003 forbidding agents a startup hook, which bought per-run
   configuration for free. What is read *once* is small and enumerable
   (`RESTART_ONLY`): since Session 50, **two prefixes** — `service` and
   `database`, covering the socket, the logging setup and the engine.
   Refusing the whole reload when one of those moves would
   block a threshold fix on an unrelated edit in the same file — and the
   operator restarts anyway, so the refusal delivers nothing the restart
   did not. Half-success is only dangerous when it is **silent**; this
   names the leaves, not the prefixes, in the body and in a `WARNING` log
   line (the only report the SIGHUP path has).
3. **The registry is rebuilt from the *new* config's `projects_root`.**
   Validating against the old root checks project ids against a directory
   the file being installed no longer names — a check that passes for the
   wrong reason, which is the failure keying services on ids exists to
   remove.
4. **Per-service in-memory state is pruned, never reset.** Clearing
   `_degraded_counts` would re-arm the three-poll streak that gates an
   alert, at the moment an operator is most likely to be reloading
   *because* something is failing. What must go is the other direction: a
   name removed and later re-added would resume a streak measured against
   a different declaration. The log aggregator's known set is **both
   files** — pruning on services.yaml alone would discard cursors
   config.yaml declares, and a dropped cursor is not a clean slate but a
   fallback to `_resume_floor()`, the per-restart duplication the cursor
   exists to remove.

`RESTART_ONLY` is hand-written, so **a test requires every config path
read at startup to be classified** — restart-only, listed in
`LIVE_AT_STARTUP` with the reason it is read again later (`api.auth_token`
per request; `projects_root` by the reload itself), or declared by a
`JobSpec`. A hand-maintained classification nothing checks is the
SNAG-CFG-001 shape, and this one decides what an operator is told about
their own edit.

Verified live rather than only against fixtures, on the instance that
motivated it: with Session 48's three new entries removed to stand in for
the running daemon, a reload of the real file reports them as `added`,
installs all three, and reports `requires_restart: []` — so the restart
owed since 2026-08-15 would not have been owed.

**The scheduler is re-timed too, and the third classification is the only
one that is derived** (Session 50, `SNAG-RELOAD-001`). Session 49 shipped
the reload without it, so an installed `AppConfig` read 999 while the job
went on firing every 300 s and `requires_restart` named it **once** — the
warning-fires-once shape Session 39 spent itself removing, and a cost the
reload *introduced*, since before it existed the config object and the
scheduler were built from one read and could never disagree.

`sysadmin/core/jobs.py` owns the plan: `plan_jobs(config)` maps an
`AppConfig` to the nine jobs it asks for and `apply_jobs` reconciles a
scheduler with it. It is `core` rather than a fourth composition root
because it imports no domain and knows no agent — `main.py` hands in
`JOB_TARGETS`, so that file owns *what* runs and this one owns *when*, and
`tests/test_jobs.py` asserts the two sets match exactly. The lifespan and
the reload call the same function, so the schedule at startup and the
schedule after a reload cannot be produced differently.

Five rules, three of them the opposite of the obvious implementation:

1. **A job whose trigger has not changed is not touched.**
   `reschedule_job` recomputes the next fire from *now*, so re-applying
   every job on every reload postpones every job by a full interval — a
   daily file organiser on a box reloaded daily never runs, which is
   `agent_first_run_delay_seconds`'s failure with a reload standing in
   for a restart. The comparison is against the **live** trigger, never a
   remembered plan: a remembered plan is a second statement of what the
   scheduler is doing, and two statements that can disagree is the defect
   being closed.
2. **A job being added gets the first-run delay; a job being re-timed does
   not.** Added means this process has never scheduled it — a cold start,
   or an agent just re-enabled — and `IntervalTrigger` alone puts the
   first fire at `now + interval`. Re-timed means it already has a next
   fire, and bringing that forward turns an unrelated threshold edit into
   a 118-second filesystem scan nobody asked for.
3. **The plan is total: a disabled job is emitted disabled, never
   omitted**, because only a plan that still names it can *remove* it.
   The other side is bounded by **only planned ids are removed** — a job
   this module did not schedule belongs to whoever added it, the estate
   judge's sweep-scoping rule.
4. **`JOB_CONFIG_PATHS` is derived from the plan**, and each `JobSpec`'s
   declared `config_paths` must equal what `plan_jobs` actually reads
   (`tests/test_reload.py`). Without a syncer the reload falls back to
   reporting those leaves as restart-only, which is Session 49's exact
   behaviour and must not fall behind the jobs it describes.
5. **`jobs_synced` says which of the two happened.** `jobs_retimed: []`
   is "nothing needed re-timing" when it is true and "the scheduler was
   never looked at" when it is false — `ports_checked`'s rule, one domain
   over.

Verified live against the real `config.yaml` and a real
`BackgroundScheduler`, in-process: 999 s became `interval[0:16:39]`,
`retention_purge` moved 03:00 → 04:00, a disabled `estate_judge` had its
job removed and re-enabling added it back with the first-run delay, and
`requires_restart` came back `[]` where Session 49 reported three leaves.
