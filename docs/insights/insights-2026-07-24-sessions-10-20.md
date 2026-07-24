# Insights — Sessions 10–20 (2026-07-24)

Eleven backlog sessions run in one sitting, several in parallel worktrees.
What follows is the non-obvious stuff worth remembering.

---

## Bugs that only surfaced because something new looked for them

**The file organiser had never run — not once.** APScheduler's `IntervalTrigger`
schedules the first fire at `now + interval`, so a 24-hour job only executes if
the process stays up a full 24 hours. This machine restarts most days, so the
agent was permanently 24 hours away from its first run. Nothing errored, nothing
logged, no alert fired — the job was simply always in the future. Found by
Session 17's `/api/sysadmin/self` endpoint within hours of that endpoint existing,
fixed in Session 18 with an explicit `first_run_delay_seconds` for hours-scale
agents.

*Lesson:* "scheduled" is not "ran". A monitoring system that never checks whether
its own workers execute has a blind spot exactly where it hurts.

**The schema had drifted and nobody knew.** Migration 001 was hand-written, so
`alembic check` had never been clean. Session 13's drift-guard test found 22
columns that were nullable in PostgreSQL but `NOT NULL` in the models, plus
`idx_alerts_active` sorted `DESC` in the DB and ascending in the model. Migration
002 aligns them.

*Lesson:* hand-written migrations decouple the models from reality silently.
The guard is three lines of `compare_metadata` and should exist from day one.

**The tests were testing a model of the app, not the app.** `tests/conftest.py`
built a synthetic FastAPI app — noop lifespan, hand-mounted routes. Both
SNAG-API-001 (Flask-style tuple return) and SNAG-API-002 (`/api/health` vs the
real `/health`) were invisible because the synthetic app never wired the real
middleware or router prefixes. Session 13 introduced `create_app()` so tests and
production share one construction path; that immediately revealed
`/api/sysadmin/scan-all` had no test coverage at all — it wasn't even mounted.

*Lesson:* the fix for this class of bug is never "more tests". It's making the
tests and production build the same object.

**`claude-postflight.sh` always reported docs as un-updated.** `grep -c` prints
`0` *and* exits 1 when there are no matches, so `$(... | grep -c "x" || echo "0")`
appends a *second* zero, yielding `"0\n0"` — an arithmetic syntax error under
`$(( ))`. Every doc check silently failed the integer comparison. Fixed by
replacing `|| echo "0"` with `|| true` (grep already prints the zero).

*Lesson:* `|| echo "0"` after `grep -c` is always wrong. Same trap applies to
`grep -c` in any `set -e` script.

---

## Design decisions worth not relitigating

**Resolve-then-check is the only safe order for path confinement.**
`file_actions.resolve_within()` calls `Path.resolve()` *before* testing
containment, which collapses `..` traversal and symlink escapes into one
comparison. `str(p).startswith(str(root))` defeats neither. `Path.resolve()` is
non-strict in modern Python, so the same helper works for destination paths that
don't exist yet.

**Check-then-act races apply to the filesystem.** `if not dest.exists():
os.rename(...)` can clobber a file created in the window between the two calls.
Reserving the destination with `O_CREAT|O_EXCL` makes the claim atomic.

**Two independent flags for anything unrecoverable.** Permanent file deletion
needs `force_delete` on the request *and* `allow_permanent_delete` in config;
unmerged branch deletion needs `include_unmerged` *and* `allow_unmerged_delete`.
Either alone reports and does nothing. Config is re-read at execution time, so a
plan built while the flag was on will not run once it's off.

**Prefer refusing to falling back.** When the XDG trash can't accept a file
(different filesystem), we skip it rather than silently degrading to
copy-and-unlink. `send2trash` would have done the unrecoverable thing quietly —
that's why it wasn't adopted.

**Merged-ness comes from git, never from dates.** Branch eligibility uses
`repo.is_ancestor(branch.commit, default.commit)`. A stale date says nothing
about whether work would be lost.

**Events must not outrun their transaction.** `BaseAgent` buffers published
events until the run's DB transaction commits — otherwise a client receiving
`alert.raised` could `GET /api/sysadmin/alerts` and not find it. Push
architectures make this ordering bug easy to write and hard to reproduce.

**Cross-loop publishing needs `call_soon_threadsafe`.** Agents run on APScheduler
threads under `asyncio.run()`, each with its own event loop; the SSE queues belong
to the API loop. `EventBus.bind_loop()` at lifespan + `publish_threadsafe()`
marshals across. Getting this wrong yields events that vanish, or
"attached to a different loop" errors.

---

## Parallel-agent workflow notes

Sessions 16‖17 and 18‖19 ran concurrently in isolated git worktrees, partitioned
by **file ownership** (tray vs backend), not by feature.

- Worktree isolation matters at the *commit* boundary, not the file boundary.
  Two agents in one checkout running `git add -A` capture each other's work even
  when their edits don't overlap.
- Instructing agents to keep doc edits **append-only** (never reflow, never touch
  the shared "Next up" banner) meant every merge conflict was two adjacent
  insertions — mechanical to resolve, zero semantic disagreement.
- Reserving one shared field (the STATUS.md banner) for the coordinator avoided
  the one conflict that would have needed judgement.
- `sysadmin/contracts.py` was the only genuinely contended file; telling each
  agent to append a single clearly-commented block kept it trivial.

---

## Still open

- Log aggregator raises one alert per error line (SNAG-AGENT-002) — masked
  downstream by Session 16's coalescing and Session 17's bounded queue, but the
  `alerts` table still fills with near-duplicates.
- `api.auth_token` ships empty because config.yaml is committed; auth is disabled
  until a real token is set locally, and PA's calls need it wired.
- The new Files tab and trend charts were only ever rendered headless.
