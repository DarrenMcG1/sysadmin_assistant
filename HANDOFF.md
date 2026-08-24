# Handoff — 2026-08-24

## Next action

Take `SNAG-LOG-009` — make the emitted `journalctl --since` timestamp unambiguous by passing `@<epoch>` instead of UTC-rendered text — because every one of the nine recommendations `GET /api/logs/actions` serves right now carries `--since '2026-08-22 17:10'`, which journalctl reads as *local* time, so on this box the window opens an hour early and west of Greenwich it would open five hours late and miss the incident the row exists to explain.

## Sub-session items

**None owed for the deploy.** `sysadmin` restarted at **2026-08-24
08:50:53** (this sitting changed the boot path, so the restart is the
proof, not a formality), `/health` answers, and the guard logged
`schema_revision_verified: 013`. `alembic current` reads **013 (head)**.

**Two items the last handoff owed are already gone**, measured rather
than assumed:

- The `Estate port … registry breach` rows it left a 2-minute `UPDATE`
  for are **all six resolved** — nothing to run.
- `sysadmin-check-schema` now runs on every commit, so the migration
  half of that handoff's warning cannot recur silently.

**One row worth watching, not acting on.** `Estate scan could not reach
sources` (`warning`, raised 07:54:54 today) names `services endpoint
unreachable: ConnectError` under `projects_invariants` — the estate's
scan looking for **this** service during the 23-hour outage. 8400 answers
`200` now and the estate judge is hourly, so it should sweep itself. If
it is still open next sitting, it is a real finding rather than an
artefact.

## This session — Session 70: nothing applied migrations

**`SNAG-DB-005` is fixed.** `sysadmin-check-schema` is a console script
over `schema_guard.packaged_head()` and a new `live_revision_sync()`,
wrapped by `scripts/check-migrations.sh` and called **blocking** from
`claude-precommit.sh` and advisory from `claude-postflight.sh`. If it is
bypassed anyway, `unit_failure._schema_diagnosis()` and
`notify-unit-failed.sh` put the revision and the remedy into the alert
row and the toast.

**2146 tests green** (+45), ruff and mypy clean. Every one of the eleven
new guards was falsified against the behaviour it replaces.

## What the sitting found that nobody had written down

- **The snag ranked its three candidates by cost and never asked what
  each buys, and two of the three rankings are wrong.**
  `ExecStartPre=` was named cheapest-that-works and buys **nothing** — a
  check there fails identically to the lifespan guard, one process
  earlier: same refusal, same `failed`, same 23 hours. And postflight
  alone would **not have caught this outage**, because Session 69's
  restart happened *mid-sitting*; a session-end check runs after the box
  is already down.
- **Prevention owns almost none of the 23 hours, and the entry never
  mentions the half that does.** `sysadmin-failed.service` fired
  *correctly*, with a persistent critical toast, and said only
  `result=exit-code, exit=1, restarts=5`. The cause was one revision
  number and the remedy one command — both sitting in
  `schema_guard._REMEDY` since Session 43, written to the journal and
  nowhere a human looks unprompted.
- **`sudo systemctl status` in that toast was wrong**, and is the second
  `sudo` claim in two sittings to fail when checked. As `gaddi` (wheel),
  `systemctl status sysadmin` and `journalctl -u sysadmin` both exit 0.
- **The counterfactual was driven by moving the checkout, not the
  database.** A temporary migration file raises the packaged head and
  leaves `alembic_version` untouched, so a crash mid-test cannot leave
  the box in the state the snag describes. Stamping down would have.
- **`uv sync` prunes this repository's tooling.** `dev` and `tray` are
  `[project.optional-dependencies]`, not dependency groups, so a bare
  `uv sync` removed pytest, ruff, mypy and PyQt6 — and `uv run pytest`
  then fell through to `/usr/bin/pytest`, which dies on `import estate`.
  **`uv sync --all-extras`** is the command. This cost ten minutes and
  would cost the same again.

## Next session — ranked

**1. `SNAG-LOG-009` (P2) — the emitted `journalctl` command points at the
wrong hour.** Measured live this sitting: all **9** recommendations the
endpoint currently serves carry `--since '2026-08-22 17:10'`, UTC text
that journalctl reads as BST. Here that is an hour early and harmless;
five hours west it is five hours *late* and the reader sees an empty
journal for an incident that happened. It is the only open snag where
the product actively misleads someone following its advice, it is on
every row rather than an edge case, and the fix is one this codebase has
already made once — `_read_journal_source` passes `@<epoch>` for exactly
this reason. Half a day.

**2. `SNAG-LOG-010` (P2) — two `noise` rows can be word-for-word
identical.** Loses on **dormancy, not on size**: the endpoint serves
`{'new_signature'}` only right now, because both kernel signatures fell
to `GONE` when the storm ended, so the population is zero and stays zero
until the next storm. The fix is also already written one module over
(`SIGNATURE_DETAIL_CHARS` + `truncate_at_word`, as
`log_review._quoted_signature` does), which makes it cheap whenever it is
taken and means nothing is gained by taking it before it can be
observed.

**3. `SNAG-AGENT-006` (P2) — a sustained fault still writes one alert row
per run.** Loses on **being dormant and being the largest**. Measured:
**3 unresolved alert rows in the whole table**, and no title with more
than 3 rows in 24 hours — the mechanism is real and is costing nothing
today. It is also the one of the three where both halves (the service
family and the threshold family) must move together, so it is a full
sitting rather than half of one.

**Named as blocked rather than dropped.** `SNAG-LOG-012` is
`estate-lib`'s `strip_markdown` and cannot be fixed here — it is a
recommendation to the owner, committed on its own and announced.
`SNAG-UNITS-005`'s remaining half needs `sudo` and no agent session can
supply it.
